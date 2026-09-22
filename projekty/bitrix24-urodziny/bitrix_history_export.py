#!/usr/bin/env python3
"""Read-only Bitrix24 contact history export for migration tests.

Exports selected contacts, their CRM activities, and timeline comments to local
JSON/TXT/CSV files. It does not modify Bitrix24 data.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


CONTACT_OWNER_TYPE_ID = 3
ACTIVITY_TYPE_LABELS = {
    "1": "meeting",
    "2": "call",
    "3": "task",
    "4": "email",
    "5": "action",
    "6": "rest",
}


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


def bitrix_list(base_url: str, method: str, params: list[tuple[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    start = 0
    while True:
        page_params = [*params, ("start", start)]
        data = bitrix_call(base_url, method, page_params)
        result = data.get("result", [])
        if isinstance(result, list):
            items.extend(item for item in result if isinstance(item, dict))
        next_start = data.get("next")
        if next_start is None:
            break
        start = int(next_start)
    return items


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return cleaned.strip("-") or "bez-nazwy"


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


def get_activities(base_url: str, contact_id: int) -> list[dict[str, Any]]:
    return bitrix_list(
        base_url,
        "crm.activity.list",
        [
            ("order[START_TIME]", "ASC"),
            ("filter[OWNER_TYPE_ID]", CONTACT_OWNER_TYPE_ID),
            ("filter[OWNER_ID]", contact_id),
            ("select[]", "*"),
            ("select[]", "COMMUNICATIONS"),
        ],
    )


def get_timeline_comments(base_url: str, contact_id: int) -> list[dict[str, Any]]:
    try:
        return bitrix_list(
            base_url,
            "crm.timeline.comment.list",
            [
                ("filter[ENTITY_TYPE]", "contact"),
                ("filter[ENTITY_ID]", contact_id),
            ],
        )
    except RuntimeError as error:
        message = str(error)
        if "ERROR_METHOD_NOT_FOUND" in message or "Unknown method" in message:
            return []
        raise


def activity_summary(activity: dict[str, Any]) -> str:
    type_id = str(activity.get("TYPE_ID") or "")
    type_label = ACTIVITY_TYPE_LABELS.get(type_id, type_id or "?")
    subject = str(activity.get("SUBJECT") or "").strip()
    start_time = str(activity.get("START_TIME") or activity.get("CREATED") or "").strip()
    description = str(activity.get("DESCRIPTION") or "").strip()
    return "\n".join(
        [
            f"[{start_time}] Activity #{activity.get('ID')} ({type_label})",
            f"Subject: {subject or '-'}",
            f"Completed: {activity.get('COMPLETED') or '-'}",
            f"Description: {description or '-'}",
        ]
    )


def comment_summary(comment: dict[str, Any]) -> str:
    created = str(comment.get("CREATED") or comment.get("CREATED_TIME") or "").strip()
    text = str(comment.get("COMMENT") or comment.get("TEXT") or "").strip()
    return "\n".join(
        [
            f"[{created}] Timeline comment #{comment.get('ID')}",
            text or "-",
        ]
    )


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def export_contact_history(base_url: str, contact_id: int, output_dir: Path) -> dict[str, Any]:
    contact = get_contact(base_url, contact_id)
    activities = get_activities(base_url, contact_id)
    timeline_comments = get_timeline_comments(base_url, contact_id)

    name = full_name(contact)
    contact_dir = output_dir / f"contact-{contact_id}-{safe_name(name)}"
    contact_dir.mkdir(parents=True, exist_ok=True)

    write_json(contact_dir / "contact.json", contact)
    write_json(contact_dir / "activities.json", activities)
    write_json(contact_dir / "timeline-comments.json", timeline_comments)

    txt_lines = [
        f"Historia Bitrix24 kontaktu: {name}",
        f"Kontakt ID: {contact_id}",
        f"E-mail: {first_email(contact) or '-'}",
        "",
        f"Aktywnosci CRM: {len(activities)}",
        f"Komentarze timeline: {len(timeline_comments)}",
        "",
        "=== Aktywnosci CRM ===",
        "",
    ]
    for activity in activities:
        txt_lines.append(activity_summary(activity))
        txt_lines.append("")
    txt_lines.extend(["", "=== Komentarze timeline ===", ""])
    for comment in timeline_comments:
        txt_lines.append(comment_summary(comment))
        txt_lines.append("")
    (contact_dir / "historia.txt").write_text("\n".join(txt_lines), encoding="utf-8")

    csv_path = contact_dir / "activities.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        fieldnames = ["ID", "TYPE_ID", "SUBJECT", "START_TIME", "END_TIME", "COMPLETED", "RESPONSIBLE_ID", "DESCRIPTION"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(activities)

    return {
        "contact_id": contact_id,
        "name": name,
        "email": first_email(contact),
        "activities": len(activities),
        "timeline_comments": len(timeline_comments),
        "folder": str(contact_dir),
    }


def parse_contact_ids(values: list[str]) -> list[int]:
    ids: list[int] = []
    for value in values:
        for part in value.split(","):
            text = part.strip()
            if not text:
                continue
            ids.append(int(text))
    return ids


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Export Bitrix24 history for selected contacts.")
    parser.add_argument("--contact-id", action="append", required=True, help="Contact ID. Can be repeated or comma-separated.")
    parser.add_argument("--output-dir", default="exports/bitrix-historia-test", help="Output directory.")
    args = parser.parse_args()

    base_url = load_env_value("BITRIX_WEBHOOK_URL")
    if not base_url:
        print("Brak BITRIX_WEBHOOK_URL w pliku .env.", file=sys.stderr)
        return 2

    contact_ids = parse_contact_ids(args.contact_id)
    if not contact_ids:
        print("Podaj przynajmniej jeden contact ID.", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir) / dt.date.today().isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[dict[str, Any]] = []
    for contact_id in contact_ids:
        print(f"Eksportuje kontakt ID {contact_id}...")
        try:
            summaries.append(export_contact_history(base_url, contact_id, output_dir))
        except (urllib.error.URLError, RuntimeError, ValueError) as error:
            print(f"Nie udalo sie wyeksportowac kontaktu {contact_id}: {error}", file=sys.stderr)

    summary_path = output_dir / "podsumowanie.json"
    write_json(summary_path, summaries)

    txt_path = output_dir / "podsumowanie.txt"
    lines = [
        f"Testowy eksport historii Bitrix24: {dt.date.today().isoformat()}",
        f"Liczba kontaktow: {len(summaries)}",
        "",
    ]
    for item in summaries:
        lines.extend(
            [
                f"- {item['contact_id']} {item['name']}",
                f"  Aktywnosci: {item['activities']}",
                f"  Komentarze timeline: {item['timeline_comments']}",
                f"  Folder: {item['folder']}",
                "",
            ]
        )
    txt_path.write_text("\n".join(lines), encoding="utf-8")

    print()
    print("Zakonczono testowy eksport historii.")
    print(f"Folder: {output_dir}")
    print(f"Podsumowanie: {txt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
