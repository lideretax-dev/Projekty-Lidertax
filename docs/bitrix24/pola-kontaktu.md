# Bitrix24 - pola kontaktu do procesu urodzin

Ten plik służy do zapisania mapowania pól z widoku Bitrix24 na pola techniczne używane przez API.

Nie wpisujemy tutaj danych klientów. Zapisujemy tylko nazwy pól i sposób ich użycia.

## Pola wymagane

| Znaczenie | Nazwa widoczna w Bitrix24 | Nazwa techniczna/API | Uwagi |
| --- | --- | --- | --- |
| Imię | First Name | do ustalenia | potrzebne do personalizacji życzeń |
| Nazwisko | Last Name | do ustalenia | do raportu i kontroli |
| E-mail | E-mail / Add e-mail | do ustalenia | potrzebny dopiero przy wysyłce |
| Telefon | Phone | do ustalenia | pomocniczo do identyfikacji kontaktu |
| Firma | Company / Contact company | do ustalenia | pomocniczo do raportu |
| Data urodzenia | DOB | do ustalenia | porównujemy dzień i miesiąc |
| Język klienta | Language - English | do ustalenia | lista wyboru; `yes` oznacza wiadomość po angielsku |

## Reguła językowa

Najważniejsza zasada: tylko wyraźna wartość `yes` w polu `Language - English` oznacza język angielski. Każda inna wartość oznacza język polski.

| Wartość pola `English` | Język wiadomości |
| --- | --- |
| yes | angielski |
| no / nie / false / 0 | polski |
| puste | polski |
| brak zaznaczenia | polski |
| nieznane | polski i oznaczenie w raporcie do sprawdzenia |

## Ustalone ze zrzutów ekranu

- Kontakty są dostępne w Bitrix24 w sekcji `CRM` -> `Customers` -> `Contacts`.
- Widok listy kontaktów pokazuje m.in. kolumny `Contact`, `First Name`, `Last Name`, `Source`, `Company`, `Contact Type`, `Responsible`, `Created`, `Last updated on`.
- W widoku szczegółów kontaktu pole daty urodzenia nazywa się `DOB`.
- Pole języka nazywa się `Language - English`.
- `Language - English` wygląda jak lista wyboru z wartością `yes` albo `no`.
- W tym samym widoku widać pole `E-mail / Add e-mail`, więc adres e-mail powinien być dostępny przy kontakcie.

## Do ustalenia technicznie

- Dokładna nazwa API dla `DOB`.
- Dokładna nazwa API dla `Language - English`.
- Dokładna nazwa API dla e-maila kontaktu.
- Czy Bitrix pozwala filtrować kontakty po dniu i miesiącu `DOB` po stronie API, czy trzeba pobrać kontakty i filtrować lokalnie.
