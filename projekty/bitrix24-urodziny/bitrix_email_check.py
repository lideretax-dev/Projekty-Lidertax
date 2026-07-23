#!/usr/bin/env python3
"""Read-only Bitrix24 e-mail capability check.

This script does not create activities, send e-mails, or modify Bitrix24 data.
It only checks which REST methods are visible for the configured webhook.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


KEYWORDS = (
    "crm.activity",
    "crm.timeline",
    "mail",
    "message",
    "notify",
)

INTERESTING_METHODS = (
    "crm.activity.add",
    "crm.activity.fields",
    "crm.activity.communication.fields",
    "crm.timeline.comment.add",
    "im.notify.system.add",
)


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
        raise RuntimeError(data.get("error_description") or data["error"])
    return data


def print_method_result(base_url: str, method: str) -> bool:
    try:
        bitrix_call(base_url, method)
    except urllib.error.HTTPError as exc:
        if exc.code == 400:
            print(f"- {method}: WIDOCZNA (Bitrix zwrocil 400, bo test nie podaje wymaganych pol)")
            return True
        print(f"- {method}: NIE ({type(exc).__name__}: HTTP {exc.code})")
        return False
    except Exception as exc:  # noqa: BLE001 - diagnostics should print any API/network issue.
        print(f"- {method}: NIE ({type(exc).__name__}: {str(exc)[:120]})")
        return False
    print(f"- {method}: TAK")
    return True


def main() -> int:
    base_url = load_env_value("BITRIX_WEBHOOK_URL")
    if not base_url:
        print("Brak BITRIX_WEBHOOK_URL w pliku .env.")
        return 1

    print("Sprawdzenie Bitrix24 e-mail/API")
    print("Tryb: tylko odczyt, bez wysylania e-maili i bez zmian w Bitrix24")
    print()

    try:
        profile = bitrix_call(base_url, "profile").get("result", {})
        user_id = profile.get("ID") or profile.get("id") or "?"
        user_name = " ".join(str(profile.get(key) or "").strip() for key in ("NAME", "LAST_NAME")).strip()
        print(f"Polaczenie z Bitrix24: OK (uzytkownik ID: {user_id}, {user_name or 'bez nazwy'})")
    except Exception as exc:  # noqa: BLE001
        print(f"Polaczenie z Bitrix24: BLAD ({type(exc).__name__}: {exc})")
        return 1

    print()
    try:
        scopes = bitrix_call(base_url, "scope").get("result", [])
        print("Zakresy webhooka:")
        if scopes:
            for scope in scopes:
                print(f"- {scope}")
        else:
            print("- brak informacji o zakresach")
    except Exception as exc:  # noqa: BLE001
        print(f"Nie udalo sie pobrac zakresow webhooka: {type(exc).__name__}: {exc}")

    print()
    print("Bezpieczny test wybranych metod:")
    available = {method: print_method_result(base_url, method) for method in INTERESTING_METHODS}

    print()
    try:
        methods = bitrix_call(base_url, "methods").get("result", [])
        matching = sorted(
            method for method in methods if any(keyword in method.lower() for keyword in KEYWORDS)
        )
        print(f"Liczba metod widocznych przez webhook: {len(methods)}")
        print("Metody zwiazane z CRM/e-mail/wiadomosciami:")
        if matching:
            for method in matching[:120]:
                print(f"- {method}")
            if len(matching) > 120:
                print(f"... i jeszcze {len(matching) - 120} metod")
        else:
            print("- nie znaleziono podobnych metod")
    except Exception as exc:  # noqa: BLE001
        print(f"Nie udalo sie pobrac listy metod: {type(exc).__name__}: {exc}")

    print()
    if available.get("crm.activity.add"):
        print("Wniosek wstepny: webhook widzi CRM activity.")
        print("Mozemy przygotowac kolejny test, najpierw bez wysylania do klientow.")
        print("Uwaga: to jeszcze nie potwierdza, ze Bitrix wysle e-mail z office@lidertax.co.uk.")
    else:
        print("Wniosek wstepny: webhook prawdopodobnie nie ma pelnych uprawnien CRM activity.")
        print("Trzeba bedzie rozszerzyc uprawnienia webhooka w Bitrix24 albo uzyc innej metody wysylki.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
