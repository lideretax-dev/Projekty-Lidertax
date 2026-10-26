# Uniwersalne życzenia Lidertax

Ustalenie właściciela z 26 października 2026:

- Życzenia obejmują obecnych i byłych klientów z datą urodzin w CRM.
- Zachowujemy zatwierdzony wygląd HTML: logo Lidertax, zieleń #368949, pomarańczowy akcent i stopkę firmową.
- PL: „Serdeczne pozdrowienia, Zespół Lidertax”. EN: „Warm regards, The Lidertax Team”. Nie sugerujemy bieżącej współpracy ani nie dodajemy oferty.
- Language – English = yes oznacza EN; pozostałe wartości zgodnie z istniejącą regułą projektu oznaczają PL.
- Codzienny raport nadal trafia tylko do właściciela. Wysyłka życzeń do klientów pozostaje ręczna, po aktualnej akceptacji konkretnych odbiorców, tematu i treści.

Źródło wyglądu i treści: `projekty/bitrix24-urodziny/templates/birthday-preview-pl.html`.
Wersję EN generuje `send_bilingual_birthday.render` z tego samego źródła.

## Ręczna zatwierdzona partia

`send_approved_birthdays.py --prepare <lokalny-plik-specyfikacji.json>` sprawdza aktualne dane kontaktów w Bitrix i zapisuje gotowe wiadomości EML oraz manifest w ignorowanym katalogu `reports/bitrix24-urodziny/pilot/approved-batches/YYYY-MM-DD/`.

Specyfikacja zawiera datę, odniesienie do aktualnej zgody właściciela i zatwierdzone wiadomości: ID kontaktu, adres, imię i nazwisko z CRM, język, imię do powitania i temat. Nie zapisuj danych klientów w repozytorium.

`--send-approved <SHA256-partii>` wysyła tylko wskazaną, zatwierdzoną partię z bieżącego dnia Europe/London. Kontroluje zgodność zapisanych wiadomości i ponownie sprawdza dane CRM. Skrót wiąże zgodę z konkretną treścią; sam skrót nie zastępuje zgody człowieka.

Historia używa dotychczasowej bazy `delivery.sqlite3`, kluczy `customer:data:ID` i wcześniejszych potwierdzeń `approved-customer-ID-data-receipt.json`. Rezerwacja jest zapisywana przed SMTP. Wysyłki niepewne i zarezerwowane nie są automatycznie ponawiane. Nie kasuj historii przy migracji.

Ten skrypt nie jest podłączony do autostartu. Odbiorca każdej wiadomości jest pojedynczy, bez Cc/Bcc. Status `accepted` oznacza przyjęcie przez SMTP, nie dowód doręczenia.

Testy offline: `python -m unittest discover -s projekty/bitrix24-urodziny -p test_approved_birthdays.py -v`.
