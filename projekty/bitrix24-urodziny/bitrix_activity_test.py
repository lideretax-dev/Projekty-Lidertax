#!/usr/bin/env python3
"""Create one safe test CRM activity for a Bitrix24 contact.

The default mode is read-only. Use --create-activity to create exactly one
test e-mail activity on the selected contact. This does not mass-send anything.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


CONTACT_OWNER_TYPE_ID = 3
EMAIL_ACTIVITY_TYPE_ID = 4
OUTGOING_DIRECTION = 2
TEXT_DESCRIPTION_TYPE = 1


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


def bitrix_call(base_url: str, method: str, params: list[tuple[str, Any]] | None = None) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/" + method + ".json"
    encoded = urllib.parse.urlencode(params or [], doseq=True).encode("utf-8")
    request = urllib.request.Request(url, data=encoded, method="POST")
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read().decode("utf-8")
    data = json.loads(payload)
    if "error" in data:
        raise RuntimeError(f"Bitrix error: {data.get('error_description') or data['error']}")
    return data


def first_email(contact: dict[str, Any]) -> str:
    emails = contact.get("EMAIL") or []
    if isinstance(emails, list) and emails:
        return str(emails[0].get("VALUE") or "").strip()
    return ""


def full_name(contact: dict[str, Any]) -> str:
    first_name = str(contact.get("NAME") or "").strip()
    last_name = str(contact.get("LAST_NAME") or "").strip()
    return " ".join(part for part in [first_name, last_name] if part).strip() or "(bez nazwy)"


def get_contact(base_url: str, contact_id: int) -> dict[str, Any]:
    data = bitrix_call(base_url, "crm.contact.get", [("ID", contact_id)])
    contact = data.get("result")
    if not isinstance(contact, dict):
        raise RuntimeError(f"Nie znaleziono kontaktu ID {contact_id}.")
    return contact


def create_test_email_activity(base_url: str, contact_id: int, contact: dict[str, Any]) -> int:
    email = first_email(contact)
    if not email:
        raise RuntimeError("Kontakt testowy nie ma adresu e-mail.")

    now = dt.datetime.now().replace(microsecond=0).isoformat()
    name = full_name(contact)
    subject = "TEST Lidertax - zyczenia urodzinowe"
    body = (
        "To jest TESTOWA aktywnosc e-mail utworzona przez automatyzacje Lidertax.\n\n"
        "Na tym etapie sprawdzamy tylko, czy Bitrix pozwala utworzyc aktywnosc przy kontakcie.\n"
        "Nie uruchamiaj tego dla prawdziwych klientow bez osobnej akceptacji."
    )

    params: list[tuple[str, Any]] = [
        ("fields[OWNER_ID]", contact_id),
        ("fields[OWNER_TYPE_ID]", CONTACT_OWNER_TYPE_ID),
        ("fields[TYPE_ID]", EMAIL_ACTIVITY_TYPE_ID),
        ("fields[DIRECTION]", OUTGOING_DIRECTION),
        ("fields[SUBJECT]", subject),
        ("fields[DESCRIPTION]", body),
        ("fields[DESCRIPTION_TYPE]", TEXT_DESCRIPTION_TYPE),
        ("fields[START_TIME]", now),
        ("fields[END_TIME]", now),
        ("fields[COMPLETED]", "N"),
        ("fields[COMMUNICATIONS][0][TYPE]", "EMAIL"),
        ("fields[COMMUNICATIONS][0][VALUE]", email),
        ("fields[COMMUNICATIONS][0][ENTITY_ID]", contact_id),
        ("fields[COMMUNICATIONS][0][ENTITY_TYPE_ID]", CONTACT_OWNER_TYPE_ID),
    ]
    data = bitrix_call(base_url, "crm.activity.add", params)
    activity_id = data.get("result")
    if not activity_id:
        raise RuntimeError(f"Bitrix nie zwrocil ID aktywnosci: {data}")

    print(f"Utworzono testowa aktywnosc e-mail dla kontaktu: {name}")
    print(f"Kontakt ID: {contact_id}")
    print(f"Aktywnosc ID: {activity_id}")
    print("Sprawdz teraz karte kontaktu w Bitrix24 i jego timeline/historie.")
    return int(activity_id)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Test one Bitrix24 CRM e-mail activity.")
    parser.add_argument("--contact-id", type=int, required=True, help="Bitrix24 contact ID, e.g. 5564.")
    parser.add_argument("--create-activity", action="store_true", help="Create exactly one test CRM activity.")
    args = parser.parse_args()

    base_url = load_env_value("BITRIX_WEBHOOK_URL")
    if not base_url:
        print("Brak BITRIX_WEBHOOK_URL w pliku .env.", file=sys.stderr)
        return 2

    try:
        contact = get_contact(base_url, args.contact_id)
    except (urllib.error.URLError, RuntimeError) as error:
        print("Nie udalo sie pobrac kontaktu testowego z Bitrix24.", file=sys.stderr)
        print(f"Szczegoly techniczne: {error}", file=sys.stderr)
        return 1

    print("Bitrix24 - test aktywnosci e-mail")
    print("Kontakt testowy:")
    print(f"- ID: {args.contact_id}")
    print(f"- Nazwa: {full_name(contact)}")
    print(f"- E-mail: {first_email(contact) or '(brak)'}")
    print()

    if not args.create_activity:
        print("Tryb tylko do odczytu: nie utworzono aktywnosci.")
        print("Aby utworzyc jedna testowa aktywnosc, uruchom z --create-activity.")
        return 0

    try:
        create_test_email_activity(base_url, args.contact_id, contact)
    except (urllib.error.URLError, RuntimeError) as error:
        print("Nie udalo sie utworzyc testowej aktywnosci.", file=sys.stderr)
        print(f"Szczegoly techniczne: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
