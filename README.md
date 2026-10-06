# Insignia Tracker

[Otwórz panel](https://kuaq.github.io/insignia-tracker/)

## Dane przywrócone z rozmowy

Panel obejmuje **53 śledzone samochody** odtworzone z raportów 30.09–06.10.2026: 51 ostatnio opisywanych jako aktywne, 1 sprzedany według użytkownika i 1 zniknięty bez potwierdzenia sprzedaży. To historyczny stan raportów, **nie nowa weryfikacja ofert**. Zapis obejmuje parametry, znane kopie portalowe, notatki, deklarowane wyposażenie i 65 zdarzeń (w tym pierwsze obserwacje). Nie wszystkie szczegółowe opisy, linki i galerie były wcześniej zachowane.

Źródło odzyskanej historii: [`data/recovered_history_2026-10-06.json`](data/recovered_history_2026-10-06.json). Nie nadpisywać tej migawki nowym przebiegiem. Dawne demonstracyjne 6 rekordów usunięto z kodu panelu.

## Jak powstaje strona

Workflow `.github/workflows/pages.yml` uruchamia testy i generator przy zmianach `data/**`, `dashboard/**` lub generatora. Generator łączy trwałą migawkę z nowszymi zweryfikowanymi obserwacjami. Publikuje `dashboard/data.js` i `dashboard/data.json` wraz z panelem; tych dwóch wygenerowanych plików nie utrzymujemy ręcznie w Git.

Nie uruchamia scrapera, płatnych API ani zewnętrznej bazy danych. Pozostawiony scraper to wyłącznie ręczny test z niepełnym pokryciem; jego wyniki nie są automatycznie źródłem aktualnych statystyk.

Lokalnie:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/build_dashboard_data.py
python3 dashboard/serve.py
```

## Kontrakt kolejnych aktualizacji

`data/listings.json` może zawierać nowsze rekordy jako mapę lub listę. Dla każdego: `key`, `data_source: "chat_tracker_run"` (lub `"verified_run"`), `observed_at` w ISO 8601, status, znane parametry i `copies` z osobnymi ID/URL/cenami/statusami. Puste pliki nie usuwają odzyskanej historii. Starszy odczyt nie nadpisuje nowszego. Nie przywracać sprzedanego auta do aktywnych bez `return_evidence`.

Do `data/events.jsonl` dopisywać zdarzenia z `key`, `at`, `type` i `source: "chat_tracker_run"` albo `"verified_run"`. Nie kasować poprzednich linii. Korekty odczytów oznaczać `data_correction`, nie zmianami ceny. `first_seen` nie może być zerowane. Brak danych o wyposażeniu nie oznacza `false`.

Pełny nowy samochód wymaga również pól `title`, `year`, `mileage_km`, `price_pln`, `gearbox`, `first_seen`, `equipment`, `description`, `problematic`, `defects` i `copies`; nieznane wartości pozostają null lub puste z wyjaśnieniem, a status dostępności musi być zgodny z dowodami.

## Archiwa i ograniczenia

Istniejące katalogi `archive/` pozostają nietknięte. Generator wiąże je z kartami wyłącznie po pasującym ID/URL, nie po podobnym VIN. Link opisany jako „archiwum testowe” nie oznacza kompletnej i zweryfikowanej galerii. Nie używać licznika 404/410 z testowego scrapera jako dowodu sprzedaży samochodu.

Wykresy i mediany korzystają z tej samej filtrowanej próby: ofert aktywnych według raportów bez opisanych usterek. Nie są to auta sprawdzone technicznie. Zgłoszone uszkodzenia blacharskie oraz lampa/klapa nie znikają z tabeli; są oznaczone i wyłączone z tej próby.

Testy chronią komplet 53 historycznych rekordów, rozdzielenie korekt i obniżek, kopie portalowe, niepewną skrzynię, brak wyposażenia vs brak danych oraz zachowanie pierwszych dat obserwacji.
