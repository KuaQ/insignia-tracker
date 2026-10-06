# Homelab: najpierw test odbiorowy dostępu

**Status: narzędzie diagnostyczne. To NIE jest jeszcze kompletny scraper działający rano i wieczorem.**
Nie zmienia obecnej bazy, nie publikuje na Pages i nie uruchamia harmonogramu. Poprzedni scraper nie jest w tym trybie uruchamiany.

## Dlaczego ten etap

Dostęp z domowej VM to inne źródło ruchu niż runner GitHuba. Może usunąć problem konkretnego IP, ale nie naprawia selektorów, paginacji, niepoprawnej klasyfikacji ani wyzwań antybotowych. Najpierw wymagamy dowodu z właściwego hosta. Zielony kod zakończenia tego testu oznacza tylko odczyt próbki na każdym portalu, NIE kompletne pokrycie rynku.

## Uruchomienie na Twojej VM z Dockerem pod Proxmoxem

Wymagane: Git, curl, Docker Engine i Docker Compose v2. Uruchamiaj jako zwykły użytkownik VM. Skrypt użyje sudo dla Dockera, kiedy bieżący użytkownik nie ma dostępu. Nie uruchamiaj przez Gluetun/VPN ani na hoście Proxmox — test ma korzystać ze zwykłego połączenia VM.

W istniejącej kopii repo:

```sh
git pull --ff-only
bash homelab/run-probe.sh
```

Bez lokalnej kopii:

```sh
git clone https://github.com/KuaQ/insignia-tracker.git
cd insignia-tracker
bash homelab/run-probe.sh
```

Jedno uruchomienie: budowa obrazu, lokalne testy kodu, przeglądarka, maksymalnie 2 strony wyników i 3 konkretne oferty na portal, próba zapisania do 2 obrazów na ofertę. Znane adresy bierze z `config/tracked_urls.json` i `data/listings.json`. Część próbek może już być wycofana — test zapisze to jako sygnał usunięcia adresu, nie sprzedaż.

Raport do przekazania asystentowi:

```text
homelab/.local/output/report-share.json
```

Pełne materiały, tylko lokalnie:

```text
homelab/.local/output/<czas-UTC>/<portal>/<pozycja>/
  result.json     # URL, HTTP, wynik, daty, diagnostyka, wyniki prób obrazów
  source.html     # oryginalny HTML / DOM z tej próby
  screen.png     # widok przeglądarki, także gdy portal zwrócił błąd
  <sha>.jpg/png/webp  # obrazy faktycznie pobrane
```

Nie wrzucaj `.local/` do publicznego repo. HTML może zawierać dane kontaktowe i informacje sesji. Podziel się `report-share.json`, nie całym katalogiem. Nie otwieraj `source.html` jako zaufanej aplikacji; do oceny wystarczy screenshot i tekst raportu.

## Co rozróżnia test

- błąd DNS / timeout / inny błąd nawigacji;
- 401, 403 i 429 zwrócone przez HTTP;
- stronę wyzwania antybotowego zwróconą nawet jako 200;
- HTML 200 bez rozpoznanych danych oferty;
- wybraną ofertę z JSON-LD (jeszcze bez pełnej walidacji wszystkich kryteriów);
- znalezione linki, faktycznie odwiedzone strony i niedokończoną paginację;
- adresy obrazów vs obrazy naprawdę zapisane.

Przy HTTP 401/403/429, wyzwaniu lub zakazie robots zatrzymuje kolejne żądania do tego portalu. Nie stosuje proxy, stealth, spoofowanego User-Agent ani rozwiązywania CAPTCHA. `robots.txt` nie zastępuje oceny dozwolonego korzystania z serwisu. Jeśli nie uda się go pobrać, raportuje tę przeszkodę, nie udaje sprawdzenia ofert.

Izolacja: przeglądarka jako użytkownik nie-root, sandbox Chromium włączony, profil seccomp Playwright z weryfikacją hasha, brak `privileged`, docker.sock, host network i wystawionych portów. Repo zamontowane read-only; jedynym trwałym zapisem jest `.local/output`. Żądania przeglądarki do localhost/LAN są blokowane, a ich nazwy są raportowane. Jeśli sandbox nie uruchomi się na VM, test zapisze `browser_start_failed` — nie wyłącza zabezpieczeń automatycznie.

## Stan weryfikacji

Sprawdzono składnię Pythona i Bash oraz 17 testów jednostkowych na syntetycznych danych. Nie wykonano testu Dockera ani odczytu portali z Twojego domowego łącza. W środowisku przygotowania nie ma Docker Engine i nie ma dostępu do Twojej VM. Dane testowe nie są wynikami realnego skanu.

## Docelowy system — kryteria odbioru, jeszcze nie wdrożone przez ten katalog

1. Kolektor na VM (Docker), szeregowe przeglądanie z normalnego połączenia domowego. Harmonogram do uzgodnienia; proponowane 08:00 i 20:00 Europe/Warsaw, obsługa zmiany czasu i blokada nakładających się przebiegów.
2. Oddzielne adaptery OTOMOTO/OLX/Autoplac i kontrola paginacji. Lista wszystkich znanych kopii sprawdzana niezależnie od tego, czy nadal jest w wynikach wyszukiwania. Licznik: znane, próbowane, odczytane, nieodczytane, celowo pominięte, niedokończone strony. Brak wyników nie oznacza pustego rynku.
3. SQLite i wersjonowane kopie na lokalnym dysku. Dane, opis, zrzut, prawdziwe zdjęcia, daty i źródła. Deduplikacja plików po hashach, zachowanie poprzednich wersji i limit dysku. Osobno wynik odczytu i wynik archiwizacji.
4. Kwalifikacja tylko z danych konkretnej oferty, nigdy z listy rekomendowanych aut. Osobno błędny parser, nieznane pole i jawny brak wyposażenia. Cena, paliwo, nadwozie, generacja i moc mają dowody w treści.
5. Każda kopia ma własny ID/URL/status/cenę. Całe auto znika dopiero po sprawdzeniu kompletu znanych kopii; błędy sieci i blokady nie są usunięciem. Sprzedaż wymaga osobnego potwierdzenia.
6. Obecny panel i punktacja zachowane jako frontend; lokalne dane są źródłem prawdy. Historia cen i dopasowanie uwzględniają kompletność danych oraz wiek odczytu. Dane historyczne nie są oznaczane jako aktualne przy samej budowie strony.
7. GitHub przechowuje kod, Pages może być opcjonalną publikacją oczyszczonego eksportu. Surowy HTML, ciasteczka, prywatne materiały i tokeny nie wychodzą z VM. Automatyczna synchronizacja publicznego eksportu wymaga osobnego wdrożenia i testu; test jej nie konfiguruje.
8. Odbiór: ręczne porównanie kilku ofert i galerii na każdym portalu, udany pełny przebieg i następny przebieg porównawczy. Dopiero potem włączenie harmonogramu. Ten test nie wystarcza do ogłoszenia gotowego narzędzia.

Brak płatnych API, proxy, OpenAI API i nowych abonamentów. Pozostają zasoby i energia własnego serwera.

Dokumentacja użytych mechanizmów: https://playwright.dev/python/docs/docker i https://playwright.dev/python/docs/api/class-response . Profil seccomp pochodzi z microsoft/playwright v1.63.0, Git blob `fddc05fb520affb145404e6f6f647ca96af8087d`.
