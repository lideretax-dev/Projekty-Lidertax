"""Offline safety and lifecycle checks; never contacts Bitrix or SMTP."""
from datetime import date
import json
from pathlib import Path
import shutil
import uuid
import unittest
from unittest.mock import patch

import birthday_pilot as p
from bitrix_birthdays import DOB_FIELD, LANGUAGE_ENGLISH_FIELD


def contact(contact_id='100', language='no', birthday='1990-10-08', name='Anna'):
    return {'ID': contact_id, 'NAME': name, 'EMAIL': [{'VALUE': 'customer@example.com'}],
            DOB_FIELD: birthday, LANGUAGE_ENGLISH_FIELD: language}


class PilotTests(unittest.TestCase):
    def setUp(self):
        self.test_root = (p.REPO / 'reports/pilot-tests').resolve()
        self.directory = self.test_root / str(uuid.uuid4())
        self.directory.mkdir(parents=True)
        self.today = date(2026, 10, 8)
        self.config = p.initialize(self.directory, self.today)
        self.db = p.open_ledger(self.directory)
        self.patched = patch.object(p, 'load_env_value', return_value='automation@lidertax.co.uk')
        self.patched.start()

    def tearDown(self):
        self.patched.stop()
        self.db.close()
        if not self.directory.resolve().is_relative_to(self.test_root):
            raise ValueError('Test cleanup path escaped test directory')
        shutil.rmtree(self.directory)

    def test_pl_en_safe_recipient_and_name_escaping(self):
        for value, language, greeting in [('no', 'PL', 'Dzień dobry'), ('1', 'EN', 'Dear')]:
            m = p.preview_message(contact(language=value, name='A&B <tag>'), self.today)
            self.assertEqual(m.get_all('To'), ['pm@lidertax.co.uk'])
            self.assertIsNone(m['Cc'])
            self.assertIsNone(m['Bcc'])
            self.assertIn(language, m['Subject'])
            self.assertIn(greeting, m.get_body(preferencelist=('plain',)).get_content())
            markup = m.get_body(preferencelist=('html',)).get_content()
            self.assertIn('A&amp;B &lt;tag&gt;', markup)
            self.assertNotIn('customer@example.com', m.as_string())
            self.assertIn('#368949', markup)

    def test_restart_and_duplicate_contacts_do_not_resend(self):
        sent = []
        contacts = [contact(), contact(), contact('101', 'yes'), contact('102', birthday='1990-10-09')]
        result = p.run_day(contacts, self.today, self.config, self.db, sent.append, self.directory)
        self.assertEqual(result['accepted'], 2)
        self.assertEqual(len(sent), 3)  # Two previews, one summary.
        self.db.close()
        self.db = p.open_ledger(self.directory)
        result = p.run_day(contacts, self.today, self.config, self.db, sent.append, self.directory)
        self.assertEqual(result['skipped'], 2)
        self.assertEqual(result['summary'], 'skipped')
        self.assertEqual(len(sent), 3)

    def test_zero_birthdays_sends_only_one_summary(self):
        sent = []
        p.run_day([], self.today, self.config, self.db, sent.append, self.directory)
        p.run_day([], self.today, self.config, self.db, sent.append, self.directory)
        self.assertEqual(len(sent), 1)
        self.assertIn('Urodziny dziś: 0', sent[0].get_content())

    def test_smtp_failure_and_crash_reservation_block_retries(self):
        m = p.preview_message(contact(), self.today)
        calls = []
        def broken(message):
            calls.append(message)
            raise TimeoutError('fake timeout')
        self.assertEqual(p.send_once(self.db, 'uncertain', m, broken), 'uncertain')
        self.assertEqual(p.send_once(self.db, 'uncertain', m, broken), 'skipped')
        self.db.execute('INSERT INTO deliveries VALUES (?, ?, ?, ?, ?)', ('crashed', 'reserved', 'id', 'now', None))
        self.db.commit()
        self.assertEqual(p.send_once(self.db, 'crashed', m, broken), 'skipped')
        self.assertEqual(len(calls), 1)

    def test_cc_or_client_recipient_is_rejected_before_smtp(self):
        m = p.preview_message(contact(), self.today)
        m['Cc'] = 'customer@example.com'
        with self.assertRaises(ValueError):
            p.send_once(self.db, 'bad-cc', m, lambda _: self.fail('SMTP called'))
        del m['Cc']
        m.replace_header('To', 'customer@example.com')
        with self.assertRaises(ValueError):
            p.send_once(self.db, 'bad-to', m, lambda _: self.fail('SMTP called'))

    def test_seven_days_then_pause_no_customer_mode(self):
        sent = []
        last = date(2026, 10, 14)
        result = p.run_day([contact(birthday='1990-10-14')], last, self.config, self.db, sent.append, self.directory)
        self.assertEqual(result['accepted'], 1)
        sent.clear()
        for day in [date(2026, 10, 15), date(2026, 10, 16)]:
            result = p.run_day([contact(birthday='1990-10-15')], day, self.config, self.db, sent.append, self.directory)
            self.assertEqual(result['mode'], 'paused-after-trial')
        self.assertEqual(len(sent), 1)
        self.assertIn('zakończona', sent[0]['Subject'])

    def test_initialization_does_not_restart_trial_and_tampering_blocks(self):
        self.assertEqual(p.initialize(self.directory, date(2026, 11, 1))['start'], '2026-10-08')
        path = self.directory / 'pilot-config.json'
        self.config['recipient'] = 'customer@example.com'
        path.write_text(json.dumps(self.config), encoding='utf-8')
        with self.assertRaises(ValueError): p.initialize(self.directory, self.today)

    def test_process_lock(self):
        with p.run_lock(self.directory):
            with self.assertRaises(OSError):
                with p.run_lock(self.directory):
                    self.fail('Second process acquired active lock')
        with p.run_lock(self.directory):
            pass


if __name__ == '__main__':
    unittest.main()
