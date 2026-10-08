"""Seven-day internal birthday preview pilot. No customer sending mode exists."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
import html
import json
import logging
import os
from pathlib import Path
import sqlite3
import sys
import time
from zoneinfo import ZoneInfo

from birthday_gmail_test import send_test, TEST_RECIPIENT
from bitrix_birthdays import (
    birthday_for_contact, clean_greeting_name, is_english, iter_contacts,
    LANGUAGE_ENGLISH_FIELD, write_report_files,
)
from gmail_smtp_test import load_env_value, require_env
from send_bilingual_birthday import render

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / 'reports/bitrix24-urodziny/pilot'
LOG = logging.getLogger('birthday-pilot')


def london_today() -> date:
    return datetime.now(ZoneInfo('Europe/London')).date()


def initialize(directory: Path, today: date) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'pilot-config.json'
    config = {'mode': 'internal-preview-only', 'recipient': TEST_RECIPIENT,
              'start': today.isoformat(), 'end_exclusive': (today + timedelta(days=7)).isoformat(),
              'timezone': 'Europe/London'}
    try:
        with path.open('x', encoding='utf-8') as handle:
            json.dump(config, handle, ensure_ascii=False, indent=2)
    except FileExistsError:
        config = json.loads(path.read_text(encoding='utf-8'))
    if config.get('mode') != 'internal-preview-only' or config.get('recipient') != TEST_RECIPIENT:
        raise ValueError('Unsupported pilot configuration; customer sending is not implemented')
    start, end = date.fromisoformat(config['start']), date.fromisoformat(config['end_exclusive'])
    if end - start != timedelta(days=7):
        raise ValueError('Pilot must last exactly seven calendar days')
    return config


@contextmanager
def run_lock(directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'run.lock').open('a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'0')
            handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def open_ledger(directory: Path) -> sqlite3.Connection:
    db = sqlite3.connect(directory / 'delivery.sqlite3')
    db.execute('PRAGMA synchronous=FULL')
    db.execute('''CREATE TABLE IF NOT EXISTS deliveries (
        delivery_key TEXT PRIMARY KEY, status TEXT NOT NULL,
        message_id TEXT NOT NULL, updated TEXT NOT NULL, error_type TEXT)''')
    db.commit()
    return db


def send_once(db: sqlite3.Connection, key: str, message: EmailMessage, sender) -> str:
    if message.get_all('To') != [TEST_RECIPIENT] or message.get_all('Cc') or message.get_all('Bcc'):
        raise ValueError('Only the fixed internal recipient is allowed')
    try:
        db.execute('INSERT INTO deliveries VALUES (?, ?, ?, ?, ?)',
                   (key, 'reserved', str(message['Message-ID']), datetime.now().isoformat(), None))
        db.commit()  # Persist BEFORE SMTP: even a process crash cannot cause automatic re-send.
    except sqlite3.IntegrityError:
        return 'skipped'
    try:
        sender(message)
    except Exception as error:
        db.execute('UPDATE deliveries SET status=?, error_type=?, updated=? WHERE delivery_key=?',
                   ('uncertain', type(error).__name__, datetime.now().isoformat(), key))
        db.commit()
        LOG.error('Delivery uncertain: %s (%s); automatic retry blocked', key, type(error).__name__)
        return 'uncertain'
    db.execute('UPDATE deliveries SET status=?, updated=? WHERE delivery_key=?',
               ('accepted', datetime.now().isoformat(), key))
    db.commit()
    LOG.info('SMTP accepted: %s -> %s', key, TEST_RECIPIENT)
    return 'accepted'


def message_base(subject: str) -> EmailMessage:
    m = EmailMessage()
    m['From'] = load_env_value('GMAIL_FROM') or require_env('GMAIL_SMTP_USER')
    m['To'] = TEST_RECIPIENT
    m['Subject'] = subject
    m['Message-ID'] = make_msgid()
    m['Date'] = formatdate(localtime=True)
    if load_env_value('GMAIL_REPLY_TO'):
        m['Reply-To'] = load_env_value('GMAIL_REPLY_TO')
    return m


def select_today(contacts: list[dict], today: date) -> list[dict]:
    selected = {}
    for contact in contacts:
        birthday = birthday_for_contact(contact)
        contact_id = str(contact.get('ID') or '')
        if contact_id and birthday and (birthday.month, birthday.day) == (today.month, today.day):
            selected[contact_id] = contact
    return list(selected.values())


def preview_message(contact: dict, today: date) -> EmailMessage:
    contact_id = str(contact['ID'])
    if not contact_id.isdigit():
        raise ValueError('Invalid contact ID')
    language = 'EN' if is_english(contact.get(LANGUAGE_ENGLISH_FIELD)) else 'PL'
    name = clean_greeting_name(str(contact.get('NAME') or ''), str(contact.get('LAST_NAME') or ''), language)
    markup, text = render(language, name)
    notice = (f'PODGLĄD — tylko dla pm@lidertax.co.uk. Kontakt Bitrix {contact_id}; '
              f'urodziny: {today.isoformat()}; język: {language}. Klient nie otrzymał wiadomości.')
    banner = '<div style="padding:16px;font:13px Arial,sans-serif;background:#fff3df;color:#42351c">' + html.escape(notice) + '</div>'
    # Insert immediately after the opening body tag, including its inline style.
    import re
    markup = re.sub(r'(<body\b[^>]*>)', lambda match: match.group(1) + banner, markup, count=1)
    subject = 'Happy Birthday from Lidertax' if language == 'EN' else 'Wszystkiego najlepszego od Lidertax'
    m = message_base(f'[PODGLĄD {language} {today.isoformat()} ID {contact_id}] {subject}')
    m['Content-Language'] = language.lower()
    m.set_content(notice + '\n\n' + text)
    m.add_alternative(markup, subtype='html')
    return m


def run_day(contacts, today, config, db, sender, directory):
    if config.get('mode') != 'internal-preview-only' or config.get('recipient') != TEST_RECIPIENT:
        raise ValueError('Customer sending is not implemented')
    start, end = date.fromisoformat(config['start']), date.fromisoformat(config['end_exclusive'])
    if today < start:
        raise ValueError('Pilot date is before start')
    if today >= end:
        m = message_base('[Lidertax] Próba urodzin zakończona — potrzebna ocena')
        m.set_content(f'Próba podglądów trwała od {start} do {end - timedelta(days=1)}.\n'
                      'Podglądy zostały wstrzymane. Wysyłka do klientów jest wyłączona.\n'
                      'Oceń podglądy i ustal kolejny etap. Nic nie przełączy się automatycznie.\n')
        result = send_once(db, 'pilot-ended:' + end.isoformat(), m, sender)
        return {'mode': 'paused-after-trial', 'notice': result}
    due = select_today(contacts, today)
    write_report_files(contacts, today, 1, True, directory / 'daily-reports')
    stats = {'mode': 'internal-preview-only', 'birthdays': len(due), 'accepted': 0, 'skipped': 0, 'uncertain': 0}
    for contact in due:
        m = preview_message(contact, today)
        result = send_once(db, f'preview:{today.isoformat()}:{contact["ID"]}', m, sender)
        stats[result] += 1
    rows = db.execute('SELECT status, count(*) FROM deliveries WHERE delivery_key LIKE ? GROUP BY status',
                      (f'preview:{today.isoformat()}:%',)).fetchall()
    statuses = dict(rows)
    attention = statuses.get('uncertain', 0) + statuses.get('reserved', 0)
    m = message_base(f'[Lidertax] Raport próby urodzin — {today.isoformat()}')
    m.set_content('\n'.join([
        f'Dzień próby: {(today-start).days + 1}/7; strefa: Europe/London.',
        f'Urodziny dziś: {len(due)}.',
        f'Podglądy przyjęte przez SMTP: {statuses.get("accepted", 0)}.',
        f'Wymagają ręcznego sprawdzenia: {attention}.',
        'Brak urodzin oznacza brak podglądów; ten raport potwierdza wykonanie procesu.',
        'Odbiorca wszystkich wiadomości: pm@lidertax.co.uk.',
        'Wysyłka do klientów: WYŁĄCZONA. Nie ma automatycznego przełączenia.',
        f'Ostatni dzień próby: {end - timedelta(days=1)}.',
        'Restart lub ponowne logowanie nie ponawia podglądów ani raportu z tego samego dnia.',
        'Niepewne wysyłki są blokowane: sprawdź skrzynkę i historię lokalną przed ręcznym ponowieniem.',
    ]))
    stats['summary'] = send_once(db, 'summary:' + today.isoformat(), m, sender)
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initialize', action='store_true', help='Initialize once without sending')
    parser.add_argument('--run', action='store_true', help='Run the internal pilot for today in London')
    args = parser.parse_args()
    os.chdir(REPO)
    STATE.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=STATE / 'pilot.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s', encoding='utf-8')
    today = london_today()
    try:
        with run_lock(STATE):
            config = initialize(STATE, today)
            if not args.run:
                print(json.dumps(config, ensure_ascii=False))
                return 0
            user = require_env('GMAIL_SMTP_USER')
            password = require_env('GMAIL_SMTP_APP_PASSWORD')
            contacts = []
            if today < date.fromisoformat(config['end_exclusive']):
                for attempt in range(3):
                    try:
                        contacts = iter_contacts(require_env('BITRIX_WEBHOOK_URL'))
                        break
                    except Exception:
                        if attempt == 2:
                            raise
                        time.sleep(10)
            db = open_ledger(STATE)
            try:
                stats = run_day(contacts, today, config, db,
                                lambda m: send_test(m, user, password), STATE)
                (STATE / 'last-run.json').write_text(json.dumps({'date':today.isoformat(), **stats}, indent=2), encoding='utf-8')
                LOG.info('Run result: %s', stats)
                print(json.dumps(stats, ensure_ascii=False))
                return 1 if stats.get('uncertain') or stats.get('summary') == 'uncertain' or stats.get('notice') == 'uncertain' else 0
            finally:
                db.close()
    except Exception as error:
        LOG.error('Run failed: %s; no credentials logged', type(error).__name__)
        (STATE / 'last-error.json').write_text(json.dumps({'date':today.isoformat(), 'error_type':type(error).__name__}), encoding='utf-8')
        print(f'Pilot failed: {type(error).__name__}. See reports/bitrix24-urodziny/pilot/pilot.log.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
