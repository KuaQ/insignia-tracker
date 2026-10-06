# Linki, archiwa, odległości i dopasowanie

Panel: https://kuaq.github.io/insignia-tracker/

## Dane i linki
Przy każdej ofercie pokazujemy wszystkie znane kopie z osobnymi linkami i ID. Brak pełnego adresu oznaczamy; nie wymyślamy slugów OLX/Autoplac. Generator może odzyskać URL z zapisanej wersji po dokładnym dopasowaniu ID. Numery kategorii CID5 nie są ID oferty.

## Podgląd archiwum
`prepare_portal.py` czyta wyłącznie istniejące pliki, bez odpytywania portali. Zdjęcia muszą należeć do głównej galerii/JSON-LD właściwej oferty lub być jej obrazem og:image. Logotypy, małe ikony i obrazy podobnych ofert odrzucamy. Pliki są weryfikowane przez Pillow i publikowane jako zoptymalizowane WebP z miniaturami. Podgląd ma wybór zapisanej wersji, duże zdjęcie, miniatury, opis, odnośnik do oryginału i plików źródłowych. Oryginalnego JavaScriptu ze scrapów nie wykonujemy. Nie twierdzimy, że archiwum jest pełne. Ceny/wyposażenie błędnego parsera nie nadpisują raportów.

## Odległości
Punkt miasta Włocławek 52.66530, 19.06080 (GeoNames: https://www.geonames.org/7532956/wloclawek.html). Wzór haversine, promień 6371.0088 km; dystans w linii prostej, nie samochodem. Kategorie: do 50, powyżej 50–150, powyżej 150–300, ponad 300 km i brak lokalizacji. Znamy tylko część lokalizacji; współrzędne ze starego archiwum nie dowodzą aktualnego miejsca auta. Konflikty pozostają nieustalone. Trasa jest zwykłym linkiem Google Maps z origin=Włocławek; nie korzysta z płatnego API ani geolokalizacji urządzenia. Dokumentacja: https://developers.google.com/maps/documentation/urls/get-started

## Dopasowanie (propozycja wag, nie ocena techniczna)
Domyślna suma 100: wyposażenie 70, skrzynia 20, zgodność ceny z limitem 65000 zł 10. Kamera/grzane fotele po 12, CarPlay 10, grzana kierownica 6; pozostałe wagi są jawne w `dashboard/match.js`. Manual jest dopuszczony (12/20), automat preferowany (20/20). Każda cena mieszcząca się w limicie daje ten sam wynik; cena sama nie dowodzi stanu. Nieznane wyposażenie tworzy zakres: wynik z zapisanych danych i maksymalny potencjalny wynik. Pokrycie jest ważone, nie liczbą wszystkich pól. Znany brak to 0 bez zwiększania potencjału. Usterki, przekroczenie budżetu i status inny niż aktywne wyłączają z grupy kandydatów, nie usuwając rekordu. Wiek/przebieg/odległość są osobnymi parametrami, nie ukrytą oceną ryzyka. Ustawienia budżetu, preferencji skrzyni i wag można zmienić lokalnie; zapis w localStorage nie synchronizuje się między urządzeniami.

## Aktualizacje
Generator najpierw buduje całą historię, potem wzbogaca widok. Nowe dane mogą dodawać `location: {city, lat, lon, source, observed_at, precision}` oraz `copies[].url` z dowodem. Nie wpisywać współrzędnych ze zgadywania pochodzenia/VIN. Nie nadpisywać `first_seen` ani `last_seen` przy samym przeliczeniu odległości. Nowe galerie wymagają rzeczywistych zdjęć, source.html, listing.json i manifest.json; stary format jest wspierany. Testy: unittest + tests/test_match.cjs. Pages nie uruchamia scrapera.
