"""Prepare immutable customer messages; send only a freshly approved daily batch.

This command is manual and is never called by the daily internal report.
Approval specs, messages and receipts belong in the ignored reports directory.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import formatdate, make_msgid, parseaddr
import hashlib
import json
import os
from pathlib import Path
import smtplib
import ssl
import sys

from birthday_pilot import STATE, london_today, open_ledger, run_lock
from bitrix_activity_test import get_contact
from bitrix_birthdays import (
    LANGUAGE_ENGLISH_FIELD, birthday_for_contact, first_email, is_english,
)
from gmail_smtp_test import load_env_value, require_env
from send_bilingual_birthday import render

REPO = Path(__file__).resolve().parents[2]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def batch_digest(batch: dict) -> str:
    return digest(json.dumps(batch, ensure_ascii=False, sort_keys=True).encode('utf-8'))


def verify_contact(item: dict, today, webhook: str) -> None:
    contact = get_contact(webhook, int(item['contact_id']))
    birthday = birthday_for_contact(contact)
    language = 'EN' if is_english(contact.get(LANGUAGE_ENGLISH_FIELD)) else 'PL'
    if (str(contact.get('ID')) != str(item['contact_id'])
            or not birthday or (birthday.month, birthday.day) != (today.month, today.day)
            or first_email(contact).strip().lower() != item['recipient'].lower()
            or language != item['language']
            or str(contact.get('NAME') or '').strip() != item['first_name']
            or str(contact.get('LAST_NAME') or '').strip() != item['last_name']):
        raise ValueError('Contact changed or is outside the approved scope: ' + str(item['contact_id']))


def validate_message(message, recipient: str) -> None:
    address = parseaddr(recipient)[1]
    if (address != recipient or not address or '@' not in address
            or any(c in recipient for c in '\r\n,;')
            or message.get_all('To') != [recipient]
            or message.get_all('Cc') or message.get_all('Bcc')
            or message.get_all('Resent-To') or message.get_all('Resent-Cc')
            or message.get_all('Resent-Bcc')):
        raise ValueError('Exactly one approved recipient is required')


def prepare(spec_path: Path) -> None:
    spec = json.loads(spec_path.read_text(encoding='utf-8-sig'))
    today = london_today()
    if spec['date'] != today.isoformat() or not spec.get('approval_reference'):
        raise ValueError('A dated approval reference is required')
    if not spec['messages']:
        raise ValueError('Empty batch')
    ids, emails = set(), set()
    for item in spec['messages']:
        if item['contact_id'] in ids or item['recipient'].lower() in emails:
            raise ValueError('Duplicate contact or mailbox in batch')
        ids.add(item['contact_id'])
        emails.add(item['recipient'].lower())
        verify_contact(item, today, require_env('BITRIX_WEBHOOK_URL'))
    directory = STATE / 'approved-batches' / today.isoformat()
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / 'manifest.json'
    if manifest_path.exists():
        raise ValueError('Prepared batch already exists; inspect it instead of overwriting')
    batch = {'date': spec['date'], 'approval_reference': spec['approval_reference'], 'messages': []}
    for item in spec['messages']:
        markup, text = render(item['language'], item['greeting_name'])
        message = EmailMessage()
        message['From'] = load_env_value('GMAIL_FROM') or require_env('GMAIL_SMTP_USER')
        message['To'] = item['recipient']
        message['Subject'] = item['subject']
        message['Date'] = formatdate(localtime=True)
        message['Message-ID'] = make_msgid()
        message['Content-Language'] = item['language'].lower()
        if load_env_value('GMAIL_REPLY_TO'):
            message['Reply-To'] = load_env_value('GMAIL_REPLY_TO')
        message.set_content(text)
        message.add_alternative(markup, subtype='html')
        validate_message(message, item['recipient'])
        raw = message.as_bytes(policy=policy.SMTP)
        filename = str(int(item['contact_id'])) + '.eml'
        with (directory / filename).open('xb') as handle:
            handle.write(raw)
        batch['messages'].append({**item, 'file': filename, 'sha256': digest(raw)})
    with manifest_path.open('x', encoding='utf-8') as handle:
        json.dump(batch, handle, ensure_ascii=False, indent=2)
    print('Prepared messages:', len(batch['messages']))
    print('Batch SHA256:', batch_digest(batch))
    print('Nothing sent.')


def read_approved(directory: Path, approved_digest: str):
    batch = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
    if batch['date'] != london_today().isoformat() or batch_digest(batch) != approved_digest:
        raise ValueError('Batch approval is expired or does not match')
    prepared = []
    for item in batch['messages']:
        if item['file'] != str(int(item['contact_id'])) + '.eml':
            raise ValueError('Invalid message path')
        raw = (directory / item['file']).read_bytes()
        if digest(raw) != item['sha256']:
            raise ValueError('Prepared message changed')
        message = BytesParser(policy=policy.default).parsebytes(raw)
        validate_message(message, item['recipient'])
        if str(message['Subject']) != item['subject']:
            raise ValueError('Subject changed')
        prepared.append((item, message))
    return batch, prepared


def deliver_once(db, key, message, sender):
    if db.execute('SELECT 1 FROM deliveries WHERE delivery_key=?', (key,)).fetchone():
        return 'skipped'
    db.execute('INSERT INTO deliveries VALUES (?,?,?,?,?)',
               (key, 'reserved', str(message['Message-ID']), datetime.now().isoformat(), None))
    db.commit()
    try:
        sender(message)
    except Exception as error:
        db.execute('UPDATE deliveries SET status=?,error_type=?,updated=? WHERE delivery_key=?',
                   ('uncertain', type(error).__name__, datetime.now().isoformat(), key))
        db.commit()
        return 'uncertain'
    db.execute('UPDATE deliveries SET status=?,updated=? WHERE delivery_key=?',
               ('accepted', datetime.now().isoformat(), key))
    db.commit()
    return 'accepted'


def send_approved(approved_digest: str) -> int:
    today = london_today()
    directory = STATE / 'approved-batches' / today.isoformat()
    batch, prepared = read_approved(directory, approved_digest)
    # Recheck every recipient before opening SMTP or reserving any deliveries.
    for item, message in prepared:
        verify_contact(item, today, require_env('BITRIX_WEBHOOK_URL'))
    with run_lock(STATE):
        db = open_ledger(STATE)
        try:
            pending = []
            for item, message in prepared:
                key = f'customer:{batch["date"]}:{item["contact_id"]}'
                legacy = STATE / f'approved-customer-{item["contact_id"]}-{batch["date"]}-receipt.json'
                if legacy.exists() or db.execute('SELECT 1 FROM deliveries WHERE delivery_key=?', (key,)).fetchone():
                    print('Skipped existing delivery:', item['contact_id'])
                    continue
                pending.append((item, message, key))
            if not pending:
                print('No new deliveries. Duplicates blocked.')
                return 0
            user = require_env('GMAIL_SMTP_USER')
            password = ''.join(require_env('GMAIL_SMTP_APP_PASSWORD').split())
            with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ssl.create_default_context(), timeout=30) as server:
                server.login(user, password)
                for item, message, key in pending:
                    if london_today() != today:
                        raise ValueError('Approval date expired during delivery')
                    def sender(m):
                        refused = server.send_message(m, from_addr=user, to_addrs=[item['recipient']])
                        if refused:
                            raise RuntimeError('Recipient refused')
                    status = deliver_once(db, key, message, sender)
                    receipt = {'date': batch['date'], 'contact_id': item['contact_id'],
                               'recipient': item['recipient'], 'subject': item['subject'],
                               'message_id': str(message['Message-ID']), 'status': status,
                               'batch_sha256': approved_digest, 'message_sha256': item['sha256'],
                               'approval_reference': batch['approval_reference']}
                    with (directory / (str(item['contact_id']) + '-receipt.json')).open('x', encoding='utf-8') as handle:
                        json.dump(receipt, handle, ensure_ascii=False, indent=2)
                    print('Contact', item['contact_id'], status, flush=True)
                    if status == 'uncertain':
                        print('Stopped. Inspect Sent before any manual retry.')
                        return 1
        finally:
            db.close()
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--prepare', type=Path, help='Local spec recording approval for reviewed recipients/content')
    group.add_argument('--send-approved', help='Exact SHA256 of the reviewed prepared batch; valid today only')
    args = parser.parse_args()
    os.chdir(REPO)
    if args.prepare:
        prepare(args.prepare)
        return 0
    return send_approved(args.send_approved)


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        raise SystemExit(main())
    except Exception as error:
        print('Stopped:', type(error).__name__, '; no automatic retry; no credentials logged.', file=sys.stderr)
        raise SystemExit(1)
