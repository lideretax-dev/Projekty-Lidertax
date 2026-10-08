# Urodziny Lidertax — stan i odtworzenie procesu

Stan zapisany: 8 października 2026.

## Co działa

- Odczyt kontaktów Bitrix24, daty urodzin, imienia i języka.
- Raporty dzienne i tygodniowe; opcjonalne podsumowanie Telegram.
- Gmail SMTP z konta `automation@lidertax.co.uk`.
- Test dla kontaktu **5564**, który podczas testu miał imię `Test` i język PL.
- Dwa osobne testy HTML PL i EN przyjęte przez Gmail SMTP; dostarczenie i wygląd tych dwóch wersji wymagają sprawdzenia w skrzynce.
- Wcześniejszy test tekstowy został potwierdzony na zrzucie skrzynki odbiorczej.

## Zasada wysyłki testowej

Jedynym odbiorcą skryptów `birthday_gmail_test.py` i `send_bilingual_birthday.py` jest **pm@lidertax.co.uk**. Adres jest ustawiony na stałe, również w kopercie SMTP. Cc i Bcc blokują wysyłkę. Nie wysyłamy testów na adres kontaktu; nie modyfikujemy kontaktu ani nie tworzymy aktywności CRM.

Dwujęzyczny test celowo przygotowuje oba języki dla tego samego kontaktu bez zmieniania jego języka w Bitrix. Raport i pojedynczy test wybierają język przez `is_english`: yes/y/true/1 i boolean true oznaczają EN, inne wartości PL.

## Wygląd

- Główna zieleń: **#368949**.
- Font: **Montserrat**, zgodny ze stroną Lidertax. Font zastępczy: Arial/Helvetica/sans-serif; program pocztowy może nie załadować fontu internetowego.
- Logo z publicznego adresu `https://lidertax.co.uk/wp-content/uploads/lidertax.png`.
- Białe tło, zielony nagłówek, pomarańczowy akcent, życzenia z imieniem i stopka firmowa.
- Logo i font są zasobami zewnętrznymi; ich wyświetlenie zależy od programu pocztowego i dostępności źródła.

## Pliki

W katalogu `projekty/bitrix24-urodziny/`:

- `bitrix_birthdays.py` — raporty i reguły personalizacji/języka.
- `gmail_smtp_test.py` — pierwotny test połączenia SMTP; używa odbiorcy z `GMAIL_TEST_TO`.
- `birthday_gmail_test.py` — jeden test tekstowy dla kontaktu 5564, odbiorca stały.
- `send_bilingual_birthday.py` — przygotowanie i wysyłka dwóch testów HTML.
- `templates/birthday-preview-pl.html` — źródło wyglądu i treści; dwujęzyczny skrypt z niego generuje HTML i stosuje tłumaczenia.
- `templates/birthday-email-pl.html` i `birthday-email-en.html` — zapis wersji HTML użytych w testach, ze stylami inline.

## Konfiguracja po pobraniu repozytorium

1. Zainstaluj Python 3.10 lub nowszy. Skrypty używają biblioteki standardowej, bez dodatkowych pakietów.
2. Skopiuj `.env.example` do `.env` w głównym katalogu repozytorium.
3. Wpisz lokalnie `BITRIX_WEBHOOK_URL`, `GMAIL_SMTP_USER` i `GMAIL_SMTP_APP_PASSWORD`. Hasło aplikacji Google musi należeć do konta SMTP. Skrypty urodzinowe pomijają spacje między grupami znaków hasła.
4. Opcjonalnie ustaw `GMAIL_FROM` i `GMAIL_REPLY_TO`. `GMAIL_TEST_TO` ustaw wyłącznie na `pm@lidertax.co.uk` dla pierwotnego testu SMTP.
5. Nie zapisuj `.env`, haseł, webhooków ani raportów klientów w Git. Samo repozytorium nie zawiera sekretów potrzebnych do uruchomienia — przechowuj je oddzielnie w menedżerze haseł.

Z głównego katalogu repozytorium, podgląd bez wysyłki i bez połączenia z Bitrix:

```powershell
python projekty/bitrix24-urodziny/send_bilingual_birthday.py
```

Podglądy zapisują się w ignorowanym przez Git katalogu `reports/bitrix24-urodziny/html-tests/`.

Wysłanie dwóch testów (PL i EN) do pm:

```powershell
python projekty/bitrix24-urodziny/send_bilingual_birthday.py --send
```

Wysyłka odczytuje kontakt 5564 z Bitrix. Po przyjęciu każdej wiadomości przez SMTP powstaje lokalny plik `birthday-html-pl-receipt.json` lub `birthday-html-en-receipt.json`. Istnienie pliku blokuje ponowne wysłanie odpowiedniej wersji. Potwierdzenia nie są przechowywane na GitHubie, więc nowy klon nie zna wcześniejszych wysyłek. Celowe ponowienie wymaga zachowania i przeniesienia odpowiedniego potwierdzenia poza ten katalog. Przy błędzie połączenia nie ponawiaj automatycznie: sprawdź skrzynkę odbiorczą i folder Wysłane, aby uniknąć duplikatu.

## Ograniczenia i dalsze kroki

Testy były uruchamiane ręcznie. Automatyczna wysyłka do klientów nie została uruchomiona. Przed jej wdrożeniem trzeba potwierdzić wygląd PL/EN na komputerze i telefonie oraz dodać trwałą historię wysyłek, ochronę przed duplikatami i osobny tryb produkcyjny.

Dokumentacja języka w starszych plikach mówi o `yes`; faktyczna implementacja akceptuje też wartości boolean/API wskazane wyżej. Tłumaczenia HTML są obecnie dokładnymi zamianami tekstu; zmiana źródłowego tekstu PL wymaga aktualizacji mapy `TRANSLATIONS`.

## Codex na Windows — rozwiązany problem środowiska

Polecenia nie uruchamiały się z błędem `helper_unknown_error: setup refresh had errors`. W tym środowisku zmiana w lokalnym pliku `%USERPROFILE%\.codex\config.toml` pomogła:

```toml
[windows]
sandbox = "unelevated"
```

Po ponownym uruchomieniu Codex test `Get-Date` przeszedł. To lokalne ustawienie Codex, nie wymóg działania skryptów. Tryb zastępczy ma słabszą izolację niż `elevated`; nie zmieniaj konfiguracji innego komputera, jeśli polecenia działają.
