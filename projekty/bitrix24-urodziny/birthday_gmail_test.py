"""Preview or send one birthday test for contact 5564 to the fixed internal inbox."""
from __future__ import annotations

import argparse
from email.message import EmailMessage
import smtplib
import ssl
import sys

from bitrix_activity_test import get_contact
from bitrix_birthdays import LANGUAGE_ENGLISH_FIELD, clean_greeting_name, is_english, message_template
from gmail_smtp_test import load_env_value, require_env

CONTACT_ID = 5564
TEST_RECIPIENT = "pm@lidertax.co.uk"


def build_message(contact: dict, sender: str, reply_to: str = "") -> tuple[EmailMessage, str, str]:
    if str(contact.get("ID")) != str(CONTACT_ID):
        raise ValueError("Unexpected contact ID")
    language = "EN" if is_english(contact.get(LANGUAGE_ENGLISH_FIELD)) else "PL"
    name = clean_greeting_name(str(contact.get("NAME") or ""), str(contact.get("LAST_NAME") or ""), language)
    subject = "Happy Birthday from Lidertax" if language == "EN" else "Wszystkiego najlepszego od Lidertax"
    message = EmailMessage()
    message["Subject"] = f"[TEST 5564] {subject}"
    message["From"] = sender
    message["To"] = TEST_RECIPIENT
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(message_template(name, language))
    return message, language, name


def send_test(message: EmailMessage, smtp_user: str, password: str) -> None:
    if message.get_all("To") != [TEST_RECIPIENT] or message.get_all("Cc") or message.get_all("Bcc"):
        raise ValueError("Test recipient validation failed")
    # Google displays app passwords in groups separated by spaces.
    password = "".join(password.split())
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context(), timeout=30) as server:
        server.login(smtp_user, password)
        server.send_message(message, from_addr=smtp_user, to_addrs=[TEST_RECIPIENT])


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send", action="store_true", help="Send exactly one test to pm@lidertax.co.uk")
    args = parser.parse_args()
    stage = "configuration"
    try:
        webhook = require_env("BITRIX_WEBHOOK_URL")
        smtp_user = load_env_value("GMAIL_SMTP_USER")
        stage = "Bitrix read"
        contact = get_contact(webhook, CONTACT_ID)
        stage = "message preparation"
        message, language, name = build_message(contact, load_env_value("GMAIL_FROM") or smtp_user or TEST_RECIPIENT, load_env_value("GMAIL_REPLY_TO"))
        print(f"Contact: {CONTACT_ID}; greeting name: {name}; language: {language}")
        print(f"To: {TEST_RECIPIENT}")
        print(f"Subject: {message['Subject']}")
        print(message.get_content())
        if args.send:
            stage = "SMTP send"
            send_test(message, require_env("GMAIL_SMTP_USER"), require_env("GMAIL_SMTP_APP_PASSWORD"))
            print("SMTP accepted one test message to pm@lidertax.co.uk.")
        else:
            print("Preview only; nothing sent.")
    except Exception as error:
        # Avoid exposing webhook URLs or credentials through exception text.
        print(f"Failed at {stage}: {type(error).__name__}. No automatic retry.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
