# aedkit: normalizacja i walidacja danych AED dla dane.gov.pl

Wymaga Pythona 3.10+. Bez zależności zewnętrznych, tylko biblioteka standardowa. Do testów potrzebny jest `pytest`.

## Użycie

```bash
python -m aedkit osm aed_poland.csv -o wynik
python -m aedkit osm aed_poland.geojson -o wynik
python -m aedkit validate plik_dysponenta.csv -o wynik
python -m pytest -q tests
```

- `osm` importuje dane z OpenStreetMap i mapuje tagi na 38 pól schematu. Braki pól z poziomu minimum zgłasza jako ostrzeżenia.
- `validate` sprawdza plik dysponenta w trybie ścisłym. Brak pola z poziomu minimum to błąd, a taki rekord jest odrzucany.

## Wyniki (`-o wynik`)

| Plik | Zawartość |
|---|---|
| `aed_dane.csv` | Przyjęte rekordy. Kodowanie UTF-8, separator przecinek, końce linii CRLF (RFC 4180), kolumny zgodne ze schematem. |
| `aed_dane.geojson` | Te same rekordy jako punkty, gotowe dla mapy. |
| `problemy.csv` | Każdy problem w osobnym wierszu: wiersz, id_zrodla, numer reguły, poziom, pole, komunikat. |
| `raport.json` / `raport.html` | Podsumowanie i liczba rekordów dla każdej reguły (slajd, wideo). |

## Zasada nadrzędna

Walidator nigdy nie usuwa AED samodzielnie, bo usunięcie działającego urządzenia jest szkodliwe. Problem obniża wskaźnik jakości albo ustawia `status_rekordu`:

- `zgloszony`: rekord z OSM albo od mieszkańca, jeszcze nie zatwierdzony,
- `zweryfikowany`: zatwierdzony i sprawdzony w ostatnich 12 miesiącach,
- `wymaga_sprawdzenia`: współrzędne poza Polską, geokodowanie tylko z dokładnością do miejscowości, przeterminowane elektrody albo zgłoszenie „nie ma”,
- `usuniety`: wyłącznie decyzją człowieka.

Rekordy bez współrzędnych trafiają do `do_sprawdzenia.csv`.

W trybie `validate` (dysponent) błędy blokują publikację formularza, dopóki dysponent ich nie poprawi.

## Reguły

| Nr | Poziom | Reguła |
|---|---|---|
| 1 | ostrzeżenie | brak `zrodlo`, ustawiane jest `inne` |
| 2, 3 | ostrzeżenie (w trybie `validate`: błąd) | brak współrzędnych albo współrzędne poza zakresem 48,99–54,84 N i 14,11–24,16 E, nieliczbowe |
| 28 | naprawa | brak współrzędnych przy znanej miejscowości: wstawiany jest środek miejscowości, `sposob_geokodowania=miejscowosc`, wskaźnik −15 |
| 4 | naprawa | zduplikowana para `zrodlo` + `id_zrodla`: rekordy są scalane, a zduplikowany `id_aed` dostaje nowy numer |
| 5 | naprawa | telefon po normalizacji ma inną liczbę cyfr niż 9. Usuwane są `+48`, `0048` i początkowe `0` (np. `052…`) |
| 6 | naprawa | kod pocztowy nie pasuje do `NN-NNN` (`61001` zamieniane na `61-001`; zero na początku, np. `00-950`, jest poprawne) |
| 7 | naprawa | wartość spoza słownika zamieniana na `nieznany`, oryginał trafia do logu |
| 8 | informacja | data niezgodna z kalendarzem (np. 30.02) traktowana jako brak danych, bez kary |
| 27 | naprawa | `dd.mm.rrrr`, `dd-mm-rrrr`, `rrrr/mm/dd` zamieniane na `rrrr-mm-dd` |
| 9 | naprawa | prywatny e-mail albo komórka z nieznanego źródła usuwane i nie zapisywane w logu |
| 10, 11, 14, 16, 17 | ostrzeżenie | jak w specyfikacji zespołu |
| 12 | ostrzeżenie | elektrody lub bateria po terminie, rekord dostaje status `wymaga_sprawdzenia` |
| 13 | ostrzeżenie | data przeglądu lub weryfikacji z przyszłości jest usuwana |
| 15 | ostrzeżenie | mniej niż 3 miejsca po przecinku albo środek miejscowości |
| 18 | naprawa | `TAK`/`1`/`yes`/`x` zamieniane na `true` |
| 24 | naprawa | przecinek dziesiętny, minus, zamienione lat/lon, zapis w stopniach (`54°50'N`) |
| 26 | naprawa | godziny `pn-pt 8-16`, `8AM-1PM` (1PM = 13:00), `całodobowo`/`0-24` zamieniane na składnię OSM. Godziny przez północ, np. 22:00–06:00, są poprawne |

Poprawne dane, które walidator ma przepuścić bez zmian:
- wieś bez ulicy,
- numer budynku `12A`, `12/14` albo brak numeru,
- polskie znaki, cudzysłowy, przecinki i entery w cudzysłowie CSV,
- BOM na początku pliku,
- separator `;`.

Wszystkie te przypadki są w testach złotych (`tests/`).

Licencja źródła trafia do kolumny `licencja_zrodla`: OSM to ODbL-1.0, dysponent i mieszkaniec to CC0-1.0.

## Deduplikacja

Dwa rekordy bliżej niż 25 m z podobną nazwą (współczynnik podobieństwa ≥ 0,6):
- z **różnych źródeł** są scalane w jeden rekord, który dostaje premię za potwierdzenie w wielu źródłach,
- z **tego samego źródła** trafiają do ostrzeżenia nr 16, bo w jednym budynku mogą być dwa AED.

## Wskaźnik jakości (0–100)

| Składnik | Punkty |
|---|---|
| Kompletność pól z poziomu minimum | 40 |
| Kompletność pól zalecanych | 20 |
| Świeżość weryfikacji: poniżej 6 mies. / 12 mies. / 24 mies. | 25 / 15 / 5 |
| Liczba źródeł: 1 / 2 i więcej | 5 / 10 |
| Brak ostrzeżeń | do 5 |
| Kara za `kategoria_dostepu=nieznany` | −5 |

## Godziny „dostępny teraz”

`aedkit.opening_hours.is_open(spec, datetime)` obsługuje:
- `24/7`,
- zakresy i listy dni,
- kilka przedziałów godzin w jednym dniu,
- godziny przechodzące przez północ,
- `off`.

Dla nieobsługiwanej składni zwraca `None`.

## Zmiana w słowniku

Zmiany w schemacie względem `aed_wzorcowy_zakres_danych.xlsx`, które trzeba dopisać w xlsx:
- nowe pola: `status_rekordu`, `sposob_geokodowania`, `licencja_zrodla`, `data_dodania_w_zrodle` (razem 42 pola),
- nowe wartości słowników: `sposob_weryfikacji=zgloszenie_spolecznosci` oraz `zrodlo=zgloszenie_mieszkanca`.

## Krajowa lista z wielu dostawców

Działa w dwóch poziomach:
1. **Każdy dostawca publikuje własny zbiór** w dane.gov.pl, we wzorcowym schemacie. Mogą to być gmina, straż pożarna, uczelnia, zarządca obiektu albo OpenStreetMap. Portal pobiera aktualizacje automatycznie ze stałego adresu dostawcy.
2. **Koordynator buduje z nich jedną krajową listę.** Polecenie:

```bash
python -m aedkit aggregate gmina-bydgoszcz=bydgoszcz.csv psp-bydgoszcz=psp.csv osm=aed_poland.csv -o wynik_krajowy
```

Co się dzieje z danymi:
- Rekordy różnych dostawców leżące bliżej niż 25 m i mające podobną nazwę są scalane w jeden rekord.
- Każdy rekord zachowuje informację o pochodzeniu: kolumny `dostawcy`, `identyfikatory_zrodlowe` i `licencje_zrodel`.

Pliki wynikowe:
- `krajowa_lista_aed.csv` i `.geojson` – wybrane pola (`AGG_FIELDS` w `aggregate.py`),
- `raport_agregacji.json` – liczba rekordów od każdego dostawcy i liczba problemów,
- `metadane_dcat.jsonld` – szkic metadanych DCAT-AP-PL. Nazwy pól trzeba sprawdzić w Przewodniku dla dostawców danych.
