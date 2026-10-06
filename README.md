# Insignia Tracker

Prywatny, bezobsługowy tracker rynku **Opel Insignia B Sports Tourer** w Polsce.

## Zakres
- benzyna
- cena do 65 000 PLN
- automat lub manual
- OTOMOTO, OLX, Autoplac
- historia cen/statusów
- deduplikacja po VIN (gdy VIN jest jawny)
- wersjonowane archiwum HTML/JSON i dostępnych zdjęć
- GitHub Actions raz dziennie

## Koszt
Projekt nie korzysta z płatnych API, proxy ani zewnętrznej bazy. Workflow używa standardowego runnera GitHub Actions i `GITHUB_TOKEN` repozytorium. Przy prywatnym repo obowiązuje miesięczny limit minut Actions wynikający z Twojego planu GitHub; workflow jest celowo krótki i uruchamia właściwy scraper raz dziennie.

## Jak działa archiwum
Każda pierwsza obserwacja i wykryta zmiana tworzy nową wersję w:

`archive/<vehicle-id>/<timestamp>/`

Wersja zawiera:
- `source.html` — HTML zwrócony przez portal,
- `listing.json` — ustrukturyzowane dane,
- `manifest.json` — kompletność archiwum,
- `index.html` — offline karta oferty,
- `media/` — zdjęcia, które rzeczywiście udało się pobrać.

Tracker **nie obchodzi CAPTCHA/403/429**. Jeśli portal blokuje GitHub Actions, zapisuje błąd zamiast udawać poprawny odczyt.

## Statusy
Brak oferty na listingu nie oznacza sprzedaży. Samo 404/410 pojedynczej kopii oznacza tylko zniknięcie tej kopii. Status całego auta trzeba potwierdzić na wszystkich znanych portalach; sprzedaż wymaga dodatkowego potwierdzenia.

## Uruchomienie lokalne
```bash
python -m pip install -r requirements.txt
python -m src.main
```

## GitHub Actions
Workflow jest uruchamiany o 06:00 i 07:00 UTC, ale guard `Europe/Warsaw` pozwala wykonać scraper tylko w runie przypadającym na lokalną 08:00. Dzięki temu zmiana CET/CEST nie wymaga ręcznej edycji crona.

Można też uruchomić go ręcznie w zakładce **Actions → Daily Insignia tracker → Run workflow**.


## Panel webowy

Panel znajduje się w katalogu `dashboard/`.

Uruchomienie:

```bash
python scripts/build_dashboard_data.py
python dashboard/serve.py
```

Następnie otwórz:

`http://127.0.0.1:8080/dashboard/`

Panel działa bez Node, bez npm i bez zewnętrznego backendu. Czyta wygenerowany plik `dashboard/data.js` i pokazuje:
- KPI rynku,
- filtry i sortowanie ofert,
- wykres cena vs przebieg,
- rozkład roczników i skrzyń,
- wyposażenie,
- historię zmian,
- zniknięte/sprzedane auta,
- linki do oryginału i zachowanych kopii, jeśli istnieją.

### Hosting

Repozytorium jest prywatne. Na GitHub Free GitHub Pages wymaga publicznego repozytorium, dlatego panel domyślnie działa lokalnie i nie wymaga żadnych opłat.
