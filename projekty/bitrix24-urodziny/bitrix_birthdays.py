#!/usr/bin/env python3
"""Read-only Bitrix24 birthday report.

This script does not send emails and does not modify Bitrix24 data.
It reads contacts, finds birthdays for a given day, and prints a review report.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DOB_FIELD = "UF_CRM_1603538271"
LANGUAGE_ENGLISH_FIELD = "UF_CRM_1664831304"
FALLBACK_BIRTHDAY_FIELD = "BIRTHDATE"


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
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = response.read().decode("utf-8")
    data = json.loads(payload)
    if "error" in data:
        raise RuntimeError(f"Bitrix error: {data.get('error_description') or data['error']}")
    return data


def parse_date(value: Any) -> dt.date | None:
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None

    candidates = [text[:10], text.replace(".", "-")[:10]]
    formats = ["%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"]
    for candidate in candidates:
        for fmt in formats:
            try:
                return dt.datetime.strptime(candidate, fmt).date()
            except ValueError:
                pass
    return None


def is_english(value: Any) -> bool:
    if value is True:
        return True
    text = str(value or "").strip().lower()
    return text in {"yes", "y", "true", "1"}


def first_email(contact: dict[str, Any]) -> str:
    emails = contact.get("EMAIL") or []
    if isinstance(emails, list) and emails:
        return str(emails[0].get("VALUE") or "")
    return ""


def birthday_for_contact(contact: dict[str, Any]) -> dt.date | None:
    return parse_date(contact.get(DOB_FIELD)) or parse_date(contact.get(FALLBACK_BIRTHDAY_FIELD))


def masked(value: str, show_pii: bool) -> str:
    if show_pii:
        return value or "-"
    if not value:
        return "-"
    return value[:1] + "***"


def clean_greeting_name(first_name: str, last_name: str, language: str) -> str:
    raw_name = (first_name or "").strip()
    name = raw_name.strip(",")
    surname = (last_name or "").strip().strip(",")

    if raw_name.endswith(",") and surname:
        return surname

    if "," in name:
        parts = [part.strip() for part in name.split(",") if part.strip()]
        name = parts[-1] if parts else ""

    if language == "EN":
        fallback = "there"
    else:
        fallback = "Kliencie"

    return name or surname or fallback


def message_template(first_name: str, language: str) -> str:
    name = first_name or ("there" if language == "EN" else "Kliencie")
    if language == "EN":
        return (
            f"Dear {name}, wishing you a very happy birthday, good health, "
            "peace of mind and all the best for the year ahead. Lidertax Team"
        )
    return (
        f"Dzień dobry {name}, z okazji urodzin życzymy wszystkiego najlepszego, "
        "dużo zdrowia, spokoju i samych dobrych decyzji w nadchodzącym roku. "
        "Zespół Lidertax"
    )


def contact_report_row(contact: dict[str, Any], birthday: dt.date, target_date: dt.date, show_pii: bool) -> dict[str, str]:
    first_name = str(contact.get("NAME") or "").strip()
    last_name = str(contact.get("LAST_NAME") or "").strip()
    language = "EN" if is_english(contact.get(LANGUAGE_ENGLISH_FIELD)) else "PL"
    email = first_email(contact)
    template_name = clean_greeting_name(first_name, last_name, language) if show_pii else "{first_name}"

    return {
        "report_date": target_date.isoformat(),
        "contact_id": str(contact.get("ID") or ""),
        "first_name": masked(first_name, show_pii),
        "last_name": masked(last_name, show_pii),
        "birthday": birthday.strftime("%d.%m.%Y"),
        "language": language,
        "email": masked(email, show_pii),
        "message": message_template(template_name, language),
    }


def iter_contacts(base_url: str, max_pages: int | None = None) -> list[dict[str, Any]]:
    contacts: list[dict[str, Any]] = []
    start = 0
    pages = 0
    while True:
        params: list[tuple[str, Any]] = [
            ("order[ID]", "ASC"),
            ("select[]", "ID"),
            ("select[]", "NAME"),
            ("select[]", "LAST_NAME"),
            ("select[]", "EMAIL"),
            ("select[]", DOB_FIELD),
            ("select[]", FALLBACK_BIRTHDAY_FIELD),
            ("select[]", LANGUAGE_ENGLISH_FIELD),
            ("start", start),
        ]
        data = bitrix_call(base_url, "crm.contact.list", params)
        contacts.extend(data.get("result", []))
        pages += 1
        if max_pages and pages >= max_pages:
            break
        next_start = data.get("next")
        if next_start is None:
            break
        start = int(next_start)
    return contacts


def collect_birthdays(
    contacts: list[dict[str, Any]],
    start_date: dt.date,
    days: int,
    show_pii: bool,
) -> list[dict[str, str]]:
    target_dates = [start_date + dt.timedelta(days=offset) for offset in range(days)]
    rows: list[dict[str, str]] = []

    for target_date in target_dates:
        for contact in contacts:
            birthday = birthday_for_contact(contact)
            if not birthday:
                continue
            if (birthday.month, birthday.day) != (target_date.month, target_date.day):
                continue
            rows.append(contact_report_row(contact, birthday, target_date, show_pii))

    return rows


def build_report(
    contacts: list[dict[str, Any]],
    target_date: dt.date,
    show_pii: bool,
    days: int = 1,
) -> list[str]:
    rows = collect_birthdays(contacts, target_date, days, show_pii)
    date_label = target_date.isoformat()
    if days > 1:
        end_date = target_date + dt.timedelta(days=days - 1)
        date_label = f"{target_date.isoformat()} - {end_date.isoformat()}"

    lines = [
        f"Raport urodzin Bitrix24 dla: {date_label}",
        "Tryb: tylko odczyt, bez wysyłki e-mail",
        "",
    ]

    lines.append(f"Liczba znalezionych kontaktów z urodzinami: {len(rows)}")
    lines.append("")

    for idx, row in enumerate(rows, start=1):
        display_name = f"{row['first_name']} {row['last_name']}".strip()
        lines.extend(
            [
                f"{idx}. Kontakt ID: {row['contact_id']}",
                f"   Dzień raportu: {row['report_date']}",
                f"   Imię i nazwisko: {display_name}",
                f"   Data urodzenia: {row['birthday']}",
                f"   Język: {row['language']}",
                f"   E-mail: {row['email']}",
                f"   Propozycja: {row['message']}",
                "",
            ]
        )

    return lines


def write_report_files(
    contacts: list[dict[str, Any]],
    target_date: dt.date,
    days: int,
    show_pii: bool,
    output_dir: Path,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "dzienny" if days == 1 else f"{days}-dni"
    base_name = f"raport-urodziny-{target_date.isoformat()}-{suffix}"
    text_path = output_dir / f"{base_name}.txt"
    csv_path = output_dir / f"{base_name}.csv"

    lines = build_report(contacts, target_date, show_pii, days)
    text_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    rows = collect_birthdays(contacts, target_date, days, show_pii)
    fieldnames = ["report_date", "contact_id", "first_name", "last_name", "birthday", "language", "email", "message"]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return [text_path, csv_path]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Generate a read-only Bitrix24 birthday report.")
    parser.add_argument("--date", default=dt.date.today().isoformat(), help="Target date, format YYYY-MM-DD.")
    parser.add_argument("--days", type=int, default=1, help="Number of days to include, for example 7.")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit pages for testing.")
    parser.add_argument("--output-dir", default="", help="Optional directory for TXT and CSV report files.")
    parser.add_argument("--show-pii", action="store_true", help="Show names and emails in the report.")
    args = parser.parse_args()

    base_url = load_env_value("BITRIX_WEBHOOK_URL")
    if not base_url:
        print("Brak BITRIX_WEBHOOK_URL w pliku .env.", file=sys.stderr)
        return 2

    target_date = dt.date.fromisoformat(args.date)
    if args.days < 1:
        print("--days musi być większe lub równe 1.", file=sys.stderr)
        return 2

    try:
        contacts = iter_contacts(base_url, max_pages=args.max_pages)
    except urllib.error.URLError as error:
        print("Nie udało się połączyć z Bitrix24.", file=sys.stderr)
        print(f"Szczegóły techniczne: {error}", file=sys.stderr)
        print("Sprawdź połączenie internetowe, webhook w .env albo uruchom skrypt poza ograniczoną sesją Codex.", file=sys.stderr)
        return 1

    for line in build_report(contacts, target_date, args.show_pii, args.days):
        print(line)

    if args.output_dir:
        paths = write_report_files(contacts, target_date, args.days, args.show_pii, Path(args.output_dir))
        print("Zapisano pliki raportu:")
        for path in paths:
            print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
