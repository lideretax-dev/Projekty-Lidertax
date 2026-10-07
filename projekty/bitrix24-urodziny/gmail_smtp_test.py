#!/usr/bin/env python3
"""Send one Gmail SMTP test message.

The script reads SMTP settings from the local .env file. It sends only one
test message to GMAIL_TEST_TO and does not contact Bitrix24.
"""

from __future__ import annotations

import email.message
import os
import smtplib
import ssl
import sys
from pathlib import Path


def find_repo_root() -> Path:
    current = Path.cwd().resolve()
    for path in [current, *current.parents]:
        if (path / ".git").exists():
            return path
    return current


def load_env_value(name: str) -> str:
    env_path = find_repo_root() / ".env"
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == name:
                return value.strip()
    return os.environ.get(name, "").strip()


def require_env(name: str) -> str:
    value = load_env_value(name)
    if not value:
        raise RuntimeError(f"Brak {name} w pliku .env.")
    return value


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    try:
        smtp_user = require_env("GMAIL_SMTP_USER")
        smtp_password = require_env("GMAIL_SMTP_APP_PASSWORD")
        sender = load_env_value("GMAIL_FROM") or smtp_user
        reply_to = load_env_value("GMAIL_REPLY_TO")
        test_to = require_env("GMAIL_TEST_TO")
    except RuntimeError as error:
        print(error, file=sys.stderr)
        return 2

    message = email.message.EmailMessage()
    message["Subject"] = "[Automation Test] Lidertax Gmail SMTP"
    message["From"] = sender
    message["To"] = test_to
    if reply_to:
        message["Reply-To"] = reply_to
    message.set_content(
        "\n".join(
            [
                "To jest test wysylki z konta automatyzacji Lidertax.",
                "",
                "Jesli widzisz te wiadomosc, konfiguracja Gmail SMTP dziala.",
                "Ten test nie pobiera danych z Bitrixa i nie wysyla nic do klientow.",
            ]
        )
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context, timeout=30) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(message)
    except Exception as error:  # noqa: BLE001 - user-facing diagnostics for setup.
        print("Nie udalo sie wyslac testowego e-maila przez Gmail SMTP.", file=sys.stderr)
        print(f"Szczegoly techniczne: {type(error).__name__}: {error}", file=sys.stderr)
        return 1

    print("Wyslano testowego e-maila przez Gmail SMTP.")
    print(f"Od: {sender}")
    print(f"Do: {test_to}")
    if reply_to:
        print(f"Reply-To: {reply_to}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
