"""Offline checks: approval scope, exact content and duplicate blocking."""
from datetime import timedelta
from email.message import EmailMessage
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import send_approved_birthdays as approved
from send_bilingual_birthday import render


class ApprovedBirthdayTests(unittest.TestCase):
    def message(self):
        message = EmailMessage()
        message['To'] = 'example@example.com'
        message['Subject'] = 'Birthday'
        message['Message-ID'] = '<offline-test@example.com>'
        message.set_content('Offline birthday test')
        return message

    def ledger(self):
        db = sqlite3.connect(':memory:')
        db.execute('CREATE TABLE deliveries (delivery_key TEXT PRIMARY KEY, status TEXT, message_id TEXT, updated TEXT, error_type TEXT)')
        self.addCleanup(db.close)
        return db

    def test_render_universal_pl_en(self):
        for language, closing in [('PL', 'Serdeczne pozdrowienia,'), ('EN', 'Warm regards,')]:
            markup, text = render(language, 'Example')
            self.assertIn(closing, text)
            self.assertIn('#368949', markup)
            self.assertIn('lidertax.png', markup)
            self.assertNotIn('Dziękujemy za zaufanie', text)
            self.assertNotIn('Thank you for your trust', text)
            self.assertNotIn('PODGLĄD', text)
            self.assertIn('Example', text)

    def test_html_name_escaped(self):
        markup, _ = render('PL', '<script>bad</script>')
        self.assertNotIn('<script>', markup)
        self.assertIn('&lt;script&gt;', markup)

    def test_cc_and_wrong_recipient_blocked(self):
        message = self.message()
        approved.validate_message(message, 'example@example.com')
        with self.assertRaises(ValueError):
            approved.validate_message(message, 'other@example.com')
        message['Cc'] = 'other@example.com'
        with self.assertRaises(ValueError):
            approved.validate_message(message, 'example@example.com')

    def test_send_once_and_duplicate(self):
        db = self.ledger()
        sent = []
        self.assertEqual(approved.deliver_once(db, 'customer:date:1', self.message(), sent.append), 'accepted')
        self.assertEqual(approved.deliver_once(db, 'customer:date:1', self.message(), sent.append), 'skipped')
        self.assertEqual(len(sent), 1)

    def test_uncertain_not_retried(self):
        db = self.ledger()
        def fail(message):
            raise TimeoutError()
        self.assertEqual(approved.deliver_once(db, 'key', self.message(), fail), 'uncertain')
        self.assertEqual(approved.deliver_once(db, 'key', self.message(), fail), 'skipped')

    def test_reserved_blocks_retry(self):
        db = self.ledger()
        db.execute('INSERT INTO deliveries VALUES (?,?,?,?,?)', ('key', 'reserved', 'id', 'date', None))
        db.commit()
        def fail(message):
            self.fail('Reserved delivery was retried')
        self.assertEqual(approved.deliver_once(db, 'key', self.message(), fail), 'skipped')

    def test_manifest_hash_and_expiry(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            raw = self.message().as_bytes()
            (directory / '1.eml').write_bytes(raw)
            batch = {'date': approved.london_today().isoformat(), 'messages': [
                {'contact_id': '1', 'file': '1.eml', 'sha256': approved.digest(raw),
                 'recipient': 'example@example.com', 'subject': 'Birthday'}]}
            manifest = directory / 'manifest.json'
            manifest.write_text(json.dumps(batch), encoding='utf-8')
            _, prepared = approved.read_approved(directory, approved.batch_digest(batch))
            self.assertEqual(len(prepared), 1)
            with self.assertRaises(ValueError):
                approved.read_approved(directory, 'wrong-hash')
            (directory / '1.eml').write_bytes(raw + b'changed')
            with self.assertRaises(ValueError):
                approved.read_approved(directory, approved.batch_digest(batch))
            batch['date'] = (approved.london_today() - timedelta(days=1)).isoformat()
            manifest.write_text(json.dumps(batch), encoding='utf-8')
            with self.assertRaises(ValueError):
                approved.read_approved(directory, approved.batch_digest(batch))

    def test_changed_contact_blocked(self):
        item = {'contact_id': '1', 'recipient': 'example@example.com', 'language': 'PL',
                'first_name': 'Example', 'last_name': 'Surname'}
        with patch.object(approved, 'get_contact', return_value={'ID': '1'}):
            with self.assertRaises(ValueError):
                approved.verify_contact(item, approved.london_today(), 'unused')


if __name__ == '__main__':
    unittest.main()
