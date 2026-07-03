# Bitrix24 - urodziny klientów

## Cel

Codziennie sprawdzić kontakty w Bitrix24 i znaleźć klientów, którzy mają urodziny danego dnia. Na początku agent ma przygotować raport i propozycję wiadomości do sprawdzenia przez człowieka. Dopiero po testach można rozważyć automatyczne wysyłanie maili.

## Założenia startowe

- Źródłem danych jest lista kontaktów w Bitrix24.
- Data urodzenia jest zapisana w polu kontaktu widocznym jako `DOB`.
- Język komunikacji wynika z pola `Language - English`.
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

- Dokładna nazwa pola API dla `DOB` w Bitrix24.
- Dokładna nazwa pola API dla `Language - English`.
- Czy wiadomości mają być wysyłane z Bitrix24, Outlooka, Gmaila czy innego systemu.
- O której godzinie ma powstawać codzienny raport.
- Czy w pierwszej wersji wystarczy raport na Telegram, czy potrzebny jest też plik CSV/Excel.

## Etapy

1. Zmapować pola kontaktu w Bitrix24.
2. Zrobić odczyt kontaktów w trybie tylko do odczytu.
3. Przygotować codzienny raport urodzin.
4. Dodać zatwierdzanie wiadomości przez człowieka.
5. Dopiero na końcu dodać wysyłkę automatyczną, jeśli testy będą bezpieczne.
