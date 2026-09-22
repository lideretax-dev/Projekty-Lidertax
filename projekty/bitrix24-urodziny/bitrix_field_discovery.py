#!/usr/bin/env python3
"""Discover Bitrix24 contact fields relevant for self assessment audits.

This script is read-only. It fetches CRM contact field metadata and writes a
small report with fields whose labels look relevant to service agreements,
self assessment, comments, or document checks.
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


DEFAULT_KEYWORDS = [
    "self",
    "assessment",
    "sa",
    "24",
    "25",
    "agreement",
    "service",
    "docu",
    "docusign",
    "contract",
    "umow",
    "comment",
    "komentar",
    "cis",
    "utr",
]


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


def normalize(value: Any) -> str:
    return str(value or "").strip()


def field_label(field_code: str, meta: dict[str, Any]) -> str:
    labels = [
        meta.get("title"),
        meta.get("formLabel"),
        meta.get("listLabel"),
        meta.get("filterLabel"),
        meta.get("settings", {}).get("LABEL") if isinstance(meta.get("settings"), dict) else "",
    ]
    cleaned = [normalize(label) for label in labels if normalize(label)]
    return cleaned[0] if cleaned else field_code


def relevant_fields(fields: dict[str, Any], keywords: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    lowered_keywords = [keyword.lower() for keyword in keywords]
    for code, meta in sorted(fields.items()):
        if not isinstance(meta, dict):
            continue
        label = field_label(code, meta)
        haystack = " ".join(
            [
                code,
                label,
                normalize(meta.get("title")),
                normalize(meta.get("formLabel")),
                normalize(meta.get("listLabel")),
                normalize(meta.get("filterLabel")),
            ]
        ).lower()
        if not any(keyword in haystack for keyword in lowered_keywords):
            continue
        rows.append(
            {
                "field_code": code,
                "label": label,
                "type": normalize(meta.get("type")),
                "is_required": normalize(meta.get("isRequired")),
                "is_read_only": normalize(meta.get("isReadOnly")),
                "is_multiple": normalize(meta.get("isMultiple")),
            }
        )
    return rows


def write_reports(rows: list[dict[str, str]], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    txt_path = output_dir / f"bitrix-pola-kontaktu-{today}.txt"
    csv_path = output_dir / f"bitrix-pola-kontaktu-{today}.csv"

    lines = [
        f"Rozpoznanie pol kontaktu Bitrix24: {today}",
        "Tryb: tylko odczyt, bez zmian w CRM",
        "",
        f"Liczba pasujacych pol: {len(rows)}",
        "",
    ]
    for row in rows:
        lines.extend(
            [
                f"- {row['field_code']}",
                f"  Nazwa: {row['label']}",
                f"  Typ: {row['type']}",
                f"  Multiple: {row['is_multiple']}",
                f"  Required: {row['is_required']}",
                "",
            ]
        )
    txt_path.write_text("\n".join(lines), encoding="utf-8")

    fieldnames = ["field_code", "label", "type", "is_required", "is_read_only", "is_multiple"]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return [txt_path, csv_path]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Discover relevant Bitrix24 contact fields.")
    parser.add_argument("--output-dir", default="reports/bitrix24-audyt", help="Directory for TXT and CSV output.")
    parser.add_argument("--keyword", action="append", default=[], help="Extra keyword to search for.")
    args = parser.parse_args()

    base_url = load_env_value("BITRIX_WEBHOOK_URL")
    if not base_url:
        print("Brak BITRIX_WEBHOOK_URL w pliku .env.", file=sys.stderr)
        return 2

    try:
        fields = bitrix_call(base_url, "crm.contact.fields").get("result", {})
    except (urllib.error.URLError, RuntimeError) as error:
        print("Nie udalo sie pobrac pol kontaktu z Bitrix24.", file=sys.stderr)
        print(f"Szczegoly techniczne: {error}", file=sys.stderr)
        return 1

    keywords = DEFAULT_KEYWORDS + args.keyword
    rows = relevant_fields(fields, keywords)
    paths = write_reports(rows, Path(args.output_dir))

    print("Rozpoznanie pol kontaktu zakonczone.")
    print(f"Liczba pasujacych pol: {len(rows)}")
    print("Zapisano pliki:")
    for path in paths:
        print(f"- {path}")
    print()
    print("Wklej mi zawartosc pliku TXT albo zrob zrzut ekranu listy pol.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
