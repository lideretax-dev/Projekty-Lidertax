# Bitrix24 - pola kontaktu do procesu urodzin

Ten plik służy do zapisania mapowania pól z widoku Bitrix24 na pola techniczne używane przez API.

Nie wpisujemy tutaj danych klientów. Zapisujemy tylko nazwy pól i sposób ich użycia.

## Pola wymagane

| Znaczenie | Nazwa widoczna w Bitrix24 | Nazwa techniczna/API | Uwagi |
| --- | --- | --- | --- |
| Imię | do ustalenia | do ustalenia | potrzebne do personalizacji życzeń |
| Nazwisko | do ustalenia | do ustalenia | do raportu i kontroli |
| E-mail | do ustalenia | do ustalenia | potrzebny dopiero przy wysyłce |
| Data urodzenia | Data urodzenia / Date of birth | do ustalenia | porównujemy dzień i miesiąc |
| Język klienta | English / English or Polish | do ustalenia | `yes` oznacza wiadomość po angielsku |

## Reguła językowa

| Wartość pola `English` | Język wiadomości |
| --- | --- |
| yes / tak / true / 1 | angielski |
| no / nie / false / 0 | polski |
| puste | polski |
| nieznane | polski i oznaczenie w raporcie do sprawdzenia |

## Notatki do uzupełnienia po zrzucie ekranu

- Gdzie dokładnie w kontakcie znajduje się data urodzenia.
- Jak wygląda pole `English`.
- Czy pole językowe jest checkboxem, listą wyboru, tekstem czy polem własnym.
- Czy każdy kontakt z datą urodzenia ma adres e-mail.

