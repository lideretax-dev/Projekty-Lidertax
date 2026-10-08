# Bitrix24 - urodziny klientów

## Aktualny zapis procesu

Stan testów, szablony HTML PL/EN, konfiguracja i instrukcja odtworzenia:
[Proces urodzin Lidertax](../../docs/bitrix24/proces-urodzin.md).

Testy Gmail SMTP są dostępne. Wysyłka testów urodzinowych odbywa się wyłącznie
na `pm@lidertax.co.uk`; automatyczna wysyłka do klientów nie jest uruchomiona.

Od 8 do 14 października 2026 działa siedmiodniowa próba podglądów przez
`birthday_pilot.py`. Istniejący autostart `raport-dzienny.bat` uruchamia ją po
zalogowaniu do Windows. Podglądy HTML PL/EN i jeden raport dzienny trafiają tylko
na pm; lokalna historia SQLite blokuje duplikaty. Po próbie podglądy są wstrzymane.
Szczegóły i obsługa błędów są w podlinkowanej instrukcji procesu.

## Cel

Codziennie sprawdzić kontakty w Bitrix24 i znaleźć klientów, którzy mają urodziny danego dnia. Na początku agent ma przygotować raport i propozycję wiadomości do sprawdzenia przez człowieka. Dopiero po testach można rozważyć automatyczne wysyłanie maili.

## Założenia startowe

- Źródłem danych jest lista kontaktów w Bitrix24.
- Data urodzenia jest zapisana w polu kontaktu widocznym jako `DOB`, technicznie `UF_CRM_1603538271`.
- Język komunikacji wynika z pola `Language - English`, technicznie `UF_CRM_1664831304`.
- Jeśli `Language - English = yes`, wiadomość ma być po angielsku.
- Jeśli `Language - English` ma dowolną inną wartość niż `yes`, wiadomość ma być po polsku.
- Na starcie nie wysyłamy wiadomości automatycznie.

## Bezpieczna wersja pierwsza

1. Agent uruchamia się codziennie o ustalonej godzinie.
2. Pobiera z Bitrix24 kontakty, które mają urodziny dziś.
3. Sprawdza pole językowe kontaktu.
4. Przygotowuje raport:
   - imię i nazwisko klienta,
   - data urodzenia,
   - język wiadomości,
   - adres e-mail, jeśli jest dostępny,
   - gotowa propozycja życzeń.
5. Raport trafia do człowieka, np. na Telegram.
6. Człowiek zatwierdza, poprawia albo ignoruje wiadomości.

## Szablony wiadomości

### Polski

```text
Dzień dobry {first_name},

z okazji urodzin życzymy wszystkiego najlepszego, dużo zdrowia, spokoju i samych dobrych decyzji w nadchodzącym roku.

Zespół Lidertax
```

### Angielski

```text
Dear {first_name},

wishing you a very happy birthday, good health, peace of mind and all the best for the year ahead.

Lidertax Team
```

## Informacje, które musimy jeszcze ustalić

- Czy wiadomości mają być wysyłane z Bitrix24, Outlooka, Gmaila czy innego systemu.
- O której godzinie ma powstawać codzienny raport.
- Czy w pierwszej wersji wystarczy raport na Telegram, czy potrzebny jest też plik CSV/Excel.
- Czy do urodzin używamy wyłącznie pola `DOB`, czy awaryjnie także standardowego `BIRTHDATE`.

## Etapy

1. Zmapować pola kontaktu w Bitrix24.
2. Zrobić odczyt kontaktów w trybie tylko do odczytu.
3. Przygotować codzienny raport urodzin.
4. Dodać zatwierdzanie wiadomości przez człowieka.
5. Dopiero na końcu dodać wysyłkę automatyczną, jeśli testy będą bezpieczne.

## Uruchamianie raportów

Raport dzienny na dziś, z pełnymi danymi i zapisem do plików:

```cmd
C:\Users\kento\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe projekty\bitrix24-urodziny\bitrix_birthdays.py --show-pii --output-dir reports\bitrix24-urodziny
```

Raport na wybraną datę:

```cmd
C:\Users\kento\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe projekty\bitrix24-urodziny\bitrix_birthdays.py --date 2026-07-21 --show-pii --output-dir reports\bitrix24-urodziny
```

Raport tygodniowy od wybranej daty:

```cmd
C:\Users\kento\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe projekty\bitrix24-urodziny\bitrix_birthdays.py --date 2026-07-21 --days 7 --show-pii --output-dir reports\bitrix24-urodziny
```

Skrypt tworzy dwa pliki lokalne: `.txt` do czytania i `.csv` do Excela. Folder `reports/` jest ignorowany przez Git, bo może zawierać dane klientów.

## Pliki do dwukliku

W głównym folderze repozytorium są dwa pliki:

```text
raport-dzienny.bat
raport-tygodniowy.bat
```

`raport-dzienny.bat` tworzy raport urodzin na dziś.

`raport-tygodniowy.bat` tworzy raport urodzin na najbliższe 7 dni.

Oba pliki zapisują wyniki w:

```text
reports\bitrix24-urodziny
```

Żeby utworzyć skróty na pulpicie, uruchom w głównym folderze repozytorium:

```text
utworz-skroty-na-pulpicie.bat
```

Po uruchomieniu na pulpicie pojawią się:

```text
Raport urodzin dzienny
Raport urodzin tygodniowy
```

## Autostart po zalogowaniu

Żeby raport dzienny uruchamiał się automatycznie po zalogowaniu do Windows, uruchom:

```text
wlacz-autostart-raportu-dziennego.bat
```

Żeby wyłączyć autostart, uruchom:

```text
wylacz-autostart-raportu-dziennego.bat
```

Autostart działa tylko wtedy, gdy laptop jest włączony i użytkownik zaloguje się do Windows.

## Telegram

Raport dzienny może wysłać krótkie podsumowanie na Telegram. Wiadomość nie zawiera listy klientów ani adresów e-mail.

W lokalnym pliku `.env` dodaj:

```text
TELEGRAM_BOT_TOKEN=tu_wklej_token_bota
TELEGRAM_CHAT_ID=tu_wpisz_swoj_telegram_id
```

Nie zapisuj tokenu w repozytorium i nie wklejaj go na czacie.

Po dodaniu tych wartości `raport-dzienny.bat` wyśle krótkie podsumowanie po wygenerowaniu raportu.
