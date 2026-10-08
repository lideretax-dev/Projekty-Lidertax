# Urodziny Lidertax — stan i odtworzenie procesu

Stan zapisany: 8 października 2026.

## Co działa

- Odczyt kontaktów Bitrix24, daty urodzin, imienia i języka.
- Raporty dzienne i tygodniowe; opcjonalne podsumowanie Telegram.
- Gmail SMTP z konta `automation@lidertax.co.uk`.
- Test dla kontaktu **5564**, który podczas testu miał imię `Test` i język PL.
- Dwa osobne testy HTML PL i EN przyjęte przez Gmail SMTP; użytkownik potwierdził dostarczenie i zaakceptował wygląd obu wersji.
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

Wdrożona próba opisana poniżej automatyzuje podglądy wyłącznie do pm. Automatyczna wysyłka do klientów nie została uruchomiona i wymaga osobnej decyzji oraz implementacji. Nie istnieje tryb automatycznego przełączenia na klientów.

Dokumentacja języka w starszych plikach mówi o `yes`; faktyczna implementacja akceptuje też wartości boolean/API wskazane wyżej. Tłumaczenia HTML są obecnie dokładnymi zamianami tekstu; zmiana źródłowego tekstu PL wymaga aktualizacji mapy `TRANSLATIONS`.

## Wdrożona próba 7 dni — 8–14 października 2026

Użytkownik zatwierdził wdrożenie. `birthday_pilot.py` uruchamia się przez istniejący skrót autostartu `Raport urodzin dzienny - autostart.lnk`, który wskazuje na `raport-dzienny.bat` w tym repozytorium. Po zalogowaniu do Windows:

1. Ustala dzisiejszą datę w `Europe/London` (Python wymaga dostępnej bazy stref, np. pakietu `tzdata`; obecne środowisko ją ma).
2. Pobiera kontakty Bitrix i wybiera osoby z urodzinami tego dnia. Podglądy powstają w języku kontaktu.
3. Zapisuje lokalny raport TXT/CSV i wysyła osobny podgląd HTML dla każdego kontaktu **wyłącznie na pm@lidertax.co.uk**. Podgląd ma etykietę z ID kontaktu, datą i językiem; nie trafia do klienta.
4. Wysyła jeden raport zbiorczy na pm, również gdy nie ma urodzin. Podczas próby ten e-mail zastępuje poprzednie automatyczne podsumowanie Telegram; ręczne narzędzia Telegram pozostają w repozytorium.
5. Przy kolejnym logowaniu tego dnia nie ponawia podglądów ani raportu.

Próba zaczęła się 8 października i trwa do 14 października włącznie. Od 15 października skrypt wstrzymuje podglądy i wysyła jednorazową wiadomość o zakończeniu próby przy najbliższym uruchomieniu. Nie uruchamia wysyłki do klientów i nie odnawia okresu próby.

Komputer musi być włączony, użytkownik zalogowany, a internet dostępny. Codex nie musi działać. Brak połączenia z Bitrix jest ponawiany do trzech razy w odstępach 10 sekund, potem błąd zostaje zapisany w logu. Autostart pokazuje błąd i pozostawia okno do przeczytania. Nie ma uruchamiania w trakcie wyłączenia komputera, nadrabiania poprzednich dat ani automatycznego wznowienia w trakcie tej samej sesji po późniejszym podłączeniu internetu. W takiej sytuacji po przywróceniu sieci można uruchomić `raport-dzienny.bat` ręcznie.

### Historia i blokowanie duplikatów

Lokalny katalog `reports/bitrix24-urodziny/pilot/` zawiera:

- `pilot-config.json` — nieodnawialny okres próby i stały odbiorca.
- `delivery.sqlite3` — historia z kluczem kontakt+data dla podglądu i data dla raportu; nie wolno jej kasować, jeśli chcemy zachować ochronę przed ponowną wysyłką.
- `pilot.log`, `last-run.json`, opcjonalnie `last-error.json` — diagnostyka bez haseł/webhooków; stary plik błędu może pozostać po późniejszym sukcesie, porównuj daty z logiem.
- `daily-reports/` — lokalne raporty zawierające dane kontaktów.

Plik blokady zapobiega równoległemu uruchomieniu. Rezerwacja wiadomości jest zapisywana w bazie **przed** SMTP. Status `accepted` oznacza przyjęcie przez SMTP, nie potwierdzenie doręczenia. Status `uncertain` lub pozostawiony `reserved` oznacza konieczność ręcznego sprawdzenia skrzynki; skrypt nie ponowi takiej wiadomości samodzielnie. Chroni to przed duplikatem przy przerwaniu procesu w trakcie wysyłki, kosztem konieczności ręcznej obsługi błędu.

Ten katalog jest ignorowany przez Git. Kopia repozytorium nie zawiera historii wysyłek, konfiguracji okresu próby ani sekretów. Przy przenoszeniu na inny komputer przenieś ten katalog osobno bezpiecznym kanałem; samo sklonowanie repozytorium i uruchomienie skryptu utworzy nową próbę bez starej historii.

Ręczne uruchomienie: `python projekty/bitrix24-urodziny/birthday_pilot.py --run` z katalogu repozytorium. Autostart korzysta ze skonfigurowanego lokalnego Pythona Hermes, co należy dostosować na innym komputerze.

Testy offline: `python -m unittest discover -s projekty/bitrix24-urodziny -p test_birthday_pilot.py -v`. Sprawdzają PL/EN, odbiorcę/Cc, deduplikację po ponownym otwarciu bazy, blokadę procesu, zero urodzin, niepewny SMTP i zatrzymanie po 7 dniach.

## Codex na Windows — rozwiązany problem środowiska

Polecenia nie uruchamiały się z błędem `helper_unknown_error: setup refresh had errors`. W tym środowisku zmiana w lokalnym pliku `%USERPROFILE%\.codex\config.toml` pomogła:

```toml
[windows]
sandbox = "unelevated"
```

Po ponownym uruchomieniu Codex test `Get-Date` przeszedł. To lokalne ustawienie Codex, nie wymóg działania skryptów. Tryb zastępczy ma słabszą izolację niż `elevated`; nie zmieniaj konfiguracji innego komputera, jeśli polecenia działają.
