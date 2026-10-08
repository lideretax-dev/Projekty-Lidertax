"""Prepare or send two internal HTML birthday tests. See docs/bitrix24/proces-urodzin.md."""
from pathlib import Path
import argparse
import html
from html.parser import HTMLParser
import json
import os
import sys
from email.message import EmailMessage
from email.utils import make_msgid, formatdate

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]
REPORTS = REPO / 'reports/bitrix24-urodziny/html-tests'
sys.path.insert(0, str(REPO / 'projekty/bitrix24-urodziny'))
from birthday_gmail_test import send_test, TEST_RECIPIENT
from gmail_smtp_test import require_env, load_env_value
from bitrix_activity_test import get_contact
from bitrix_birthdays import clean_greeting_name

FONT = "font-family:'Montserrat',Arial,Helvetica,sans-serif;"
CLASS_STYLES = {
    'outer': 'padding:32px 16px;',
    'card': 'width:100%;max-width:600px;',
    'pad': 'padding:38px 48px;',
    'title': 'font-size:44px;line-height:1.15;letter-spacing:-1.6px;margin:18px 0 22px;',
    'copy': 'font-size:17px;line-height:1.8;margin:0 0 18px;',
}
TRANSLATIONS = {
    'lang="pl"': 'lang="en"',
    'Lidertax — kartka urodzinowa': 'Lidertax — birthday wishes',
    'Dużo radości, spełnionych marzeń i dobrych chwil — życzy zespół Lidertax.': 'Wishing you joy, dreams fulfilled and wonderful moments — from the Lidertax Team.',
    'DZIŚ JEST TWÓJ DZIEŃ': 'TODAY IS YOUR DAY',
    'Wszystkiego<br>najlepszego,': 'Happy<br>Birthday,',
    'Niech kolejny rok przyniesie Ci wiele powodów do uśmiechu.': 'May the year ahead bring you plenty of reasons to smile.',
    'Dzień dobry Test,': 'Dear Test,',
    'z okazji urodzin przesyłamy Ci serdeczne życzenia od całego zespołu Lidertax.': 'On your birthday, we send you our warmest wishes from everyone at Lidertax.',
    'Życzymy Ci przede wszystkim zdrowia, spokoju i czasu na to, co sprawia Ci największą radość. Niech każdy dzień przynosi dobre chwile, życzliwych ludzi i energię do realizowania marzeń.': 'Above all, we wish you good health, peace of mind and time for the things that bring you joy. May each day be filled with happy moments, kind people and the energy to follow your dreams.',
    'Niech nadchodzący rok będzie pełen pomyślności — zarówno w życiu osobistym, jak i zawodowym. A dziś znajdź chwilę dla siebie i świętuj tak, jak lubisz najbardziej.': 'May the year ahead bring you happiness and success in your personal and professional life. And today, take some time for yourself and celebrate in whatever way makes you happiest.',
    'Dobrego roku.<br>Pięknych chwil.<br>Spełnionych marzeń.': 'A wonderful year.<br>Beautiful moments.<br>Dreams fulfilled.',
    'Dziękujemy za zaufanie.': 'Thank you for your trust.',
    'Zespół Lidertax': 'The Lidertax Team',
    'Londyn &amp; Chatham': 'London &amp; Chatham',
}


class EmailHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []
        self.text = []

    def handle_decl(self, decl): self.parts.append('<!' + decl + '>')
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        css = ''.join(CLASS_STYLES.get(c, '') for c in attrs.get('class', '').split())
        if tag in {'body', 'table', 'td', 'p', 'h1', 'a', 'strong', 'span'}:
            css = FONT + css
        if tag == 'body': css += 'margin:0;background:#f1f4f1;color:#24372d;'
        if tag == 'table': css += 'border-collapse:collapse;'
        attrs['style'] = css + attrs.get('style', '')
        if 'card' in attrs.get('class', '').split(): attrs['width'] = '600'
        if tag == 'a': attrs['style'] += 'color:inherit;'
        self.parts.append('<' + tag + ''.join(' ' + k + '="' + html.escape(v or '', quote=True) + '"' for k, v in attrs.items()) + '>')
        if tag == 'br': self.text.append('\n')

    def handle_endtag(self, tag):
        self.parts.append('</' + tag + '>')
        if tag in {'p', 'h1', 'td'}: self.text.append('\n\n')
    def handle_data(self, data): self.parts.append(data); self.text.append(data)
    def handle_entityref(self, name): self.parts.append('&' + name + ';'); self.text.append(html.unescape('&' + name + ';'))
    def handle_charref(self, name): self.parts.append('&#' + name + ';'); self.text.append(html.unescape('&#' + name + ';'))


def render(language, name):
    import re
    source = (BASE / 'templates/birthday-preview-pl.html').read_text(encoding='utf-8')
    source = re.sub(r'<p[^>]*>PODGLĄD PROJEKTU.*?</p>', '', source)
    source = re.sub(r'<p[^>]*>Imię „Test”.*?</p>', '', source)
    if language == 'EN':
        for before, after in TRANSLATIONS.items():
            assert before in source, before
            source = source.replace(before, after)
        source = source.replace('https://lidertax.co.uk/pl/polskie-biuro-ksiegowe-w-uk', 'https://lidertax.co.uk/')
    source = source.replace('Test!', html.escape(name) + '!').replace('Test,', html.escape(name) + ',')
    # Keep responsive CSS in the head; plain text contains only the actual email body.
    head, body = source.split('<body>', 1)
    parser = EmailHTML()
    parser.feed('<body>' + body)
    markup = head + ''.join(parser.parts)
    text = re.sub(r'\n\s*\n(?:\s*\n)+', '\n\n', ''.join(parser.text)).strip()
    assert '#368949' in markup and 'PODGLĄD' not in markup and 'nie została wysłana' not in markup
    return markup, text


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--send', action='store_true')
    args = parser.parse_args()
    os.chdir(REPO)
    smtp_user = require_env('GMAIL_SMTP_USER')
    contact = get_contact(require_env('BITRIX_WEBHOOK_URL'), 5564) if args.send else {'ID': '5564', 'NAME': 'Test'}
    assert str(contact.get('ID')) == '5564'
    REPORTS.mkdir(parents=True, exist_ok=True)
    messages = []
    for language in ['PL', 'EN']:
        name = clean_greeting_name(str(contact.get('NAME') or ''), str(contact.get('LAST_NAME') or ''), language)
        markup, text = render(language, name)
        (REPORTS / f'birthday-email-{language.lower()}.html').write_text(markup, encoding='utf-8')
        m = EmailMessage()
        m['Subject'] = '[TEST HTML PL 5564] Wszystkiego najlepszego od Lidertax' if language == 'PL' else '[TEST HTML EN 5564] Happy Birthday from Lidertax'
        m['From'] = load_env_value('GMAIL_FROM') or smtp_user
        m['To'] = TEST_RECIPIENT
        m['Date'] = formatdate(localtime=True)
        m['Message-ID'] = make_msgid()
        m['Content-Language'] = language.lower()
        if load_env_value('GMAIL_REPLY_TO'): m['Reply-To'] = load_env_value('GMAIL_REPLY_TO')
        m.set_content(text)
        m.add_alternative(markup, subtype='html')
        assert m['To'] == 'pm@lidertax.co.uk' and not m['Cc'] and not m['Bcc']
        assert m.get_body(preferencelist=('html',)).get_content_type() == 'text/html'
        messages.append((language, m))
        print('Prepared:', language, m['Subject'], 'To:', m['To'])
    if not args.send:
        print('Validation passed; nothing sent.')
        return
    for language, m in messages:
        receipt = REPORTS / f'birthday-html-{language.lower()}-receipt.json'
        if receipt.exists():
            raise RuntimeError('Receipt already exists; duplicate blocked')
        send_test(m, smtp_user, require_env('GMAIL_SMTP_APP_PASSWORD'))
        receipt.write_text(json.dumps({'language':language, 'to':TEST_RECIPIENT, 'subject':str(m['Subject']), 'message_id':str(m['Message-ID']), 'status':'SMTP accepted'}, ensure_ascii=False), encoding='utf-8')
        print('SMTP accepted:', language, 'To:', TEST_RECIPIENT, flush=True)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        main()
    except Exception as error:
        print('Stopped:', type(error).__name__, '; no automatic retry.', file=sys.stderr)
        raise SystemExit(1)
