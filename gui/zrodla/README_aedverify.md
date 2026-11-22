# aedverify – autonomiczna weryfikacja AED zdjęciem + GPS

Każdy zaimportowany AED (gov, OSM, dysponenci) startuje jako `niezweryfikowany`.
Status zmienia wyłącznie silnik na podstawie zgłoszeń ze zdjęciem albo decyzja człowieka w panelu.

## Elementy
| Plik | Rola |
|---|---|
| `aedverify/engine.py` | `verify()` – werdykt dla 1 zgłoszenia; `status()` – status AED z wszystkich zgłoszeń |
| `aedverify/exif.py` | odczyt GPS/czasu z EXIF (bez zależności), usuwanie EXIF przed zapisem |
| `aedverify/vision.py` | wykrywanie oznaczenia AED (heurystyka znaku ILCOR lub model ONNX z `AED_MODEL`), pHash do duplikatów |
| `aedverify/server.py` | referencyjne API (stdlib + SQLite) – wzór dla docelowego backendu |
| `static/foto.js` | aparat + GPS w chwili zdjęcia + wysyłka (do wpięcia w aplikację) |
| `static/weryfikuj.html` | ekran „Potwierdź AED” (mobile, WCAG: kontrast, fokus, aria-live) |
| `static/panel.html` | kolejka do ręcznej weryfikacji + eksport CSV/JSON |

## Sygnały w werdykcie (`verify`)
1. **GPS urządzenia w chwili zdjęcia** vs pozycja w bazie, tolerancja `max(25 m, 1,5×dokładność)`, maks. 75 m.
2. **EXIF**: GPS w zdjęciu vs GPS urządzenia (> 100 m → podejrzane), data zdjęcia (stare → podejrzane). Brak EXIF nie karze (przeglądarki go wycinają).
3. **Świeżość**: lokalizacja starsza niż 15 min albo z przyszłości.
4. **Duplikat**: pHash ≤ 6 bitów różnicy od dowolnego wcześniejszego zdjęcia → odrzucenie.
5. **Obraz**: czy widać zielony znak AED (≥ 0,6 → +, < 0,15 → do człowieka).

Werdykty: `potwierdzony_auto`, `korekta_lokalizacji` (25–150 m, z proponowaną pozycją), `do_sprawdzenia`, `brak_aed`, `odrzucony`.

## Status AED (`status`) – konsensus
| Status | Warunek |
|---|---|
| `niezweryfikowany` | brak zgłoszeń |
| `wstepnie_potwierdzony` | 1 urządzenie z `potwierdzony_auto` |
| `potwierdzony` | ≥ 2 **różne** urządzenia albo decyzja człowieka |
| `do_korekty` | ≥ 2 urządzenia proponują pozycję w promieniu 40 m od siebie (mediana) |
| `prawdopodobnie_brak` | ≥ 2 urządzenia zgłosiły brak z miejsca i nikt nie potwierdził później |
| `do_sprawdzenia` | są zgłoszenia, ale żadne nie przeszło automatu |
| `wygasly` | ostatnia weryfikacja starsza niż 365 dni |

## Kontrakt API (propozycja dla backendu)
```
GET  /api/aed/najblizsze?lat&lon&n            → [{id,lat,lon,nazwa,status,odleglosc_m}]
POST /api/weryfikacje   multipart: aed_id, typ(jest|nie_ma), lat, lon, accuracy, ts(ISO), urzadzenie, zdjecie
                        → 201 {id, werdykt, wynik, odleglosc_m, powody[], flagi[], status_aed{...}}
GET  /api/kolejka                 (Bearer)    → zgłoszenia do_sprawdzenia / korekta / brak_aed
POST /api/kolejka/{id} {"decyzja": potwierdzony|korekta|odrzucony|prawdopodobnie_brak}   (Bearer)
GET  /api/zdjecie/{plik}          (Bearer)    → zdjęcie bez EXIF
GET  /api/eksport.csv | .json                 → zbiór z polami weryfikacji (dla dane.gov.pl)
```
Docelowy backend może zamiast własnej logiki wołać `aedverify.verify(zdjecie, gps, aed, znane_hashe=...)` i `aedverify.status(lista)`.

## Uruchomienie (demo)
```bash
cd zrodla
python3 -m aedverify import ../aplikacja/aed.json --zrodlo osm      # wszystko jako niezweryfikowane
AED_ADMIN_TOKEN=tajne python3 -m aedverify serve --port 8090
# http://localhost:8090/weryfikuj.html   http://localhost:8090/panel.html?token=tajne
python3 -m aedverify check zdjecie.jpg --aed 52.4069,16.9254 --gps 52.4068,16.9255,12
python3 -m pytest -q tests                                          # 93 testy
```
Na VM w Caddy: `handle /api/* { reverse_proxy 127.0.0.1:8090 }`. Aparat i GPS działają tylko na HTTPS.
Zależności: Python 3.10+, opcjonalnie Pillow (wykrywanie znaku, pHash), opcjonalnie onnxruntime + numpy (model).

## Pola do schematu xlsx
`status_rekordu` (słownik jak wyżej), `data_weryfikacji`, `sposob_weryfikacji` (dysponent / foto_gps / recznie / osm), `liczba_potwierdzen`.
Zdjęcia, ID urządzeń i dokładne pozycje zgłaszających **nie** trafiają do otwartego zbioru.

## Model AI (YOLO przez API)
Jeśli ustawione są `AED_MODEL_URL` i `AED_MODEL_KEY`, ocena „czy na zdjęciu jest AED” pochodzi z modelu YOLO
(format odpowiedzi Roboflow: `predictions[].class/confidence`), a liczy się najwyższa pewność dla klas z `AED_MODEL_CLASSES`.
Zdjęcie przed wysłaniem jest zmniejszane do 1280 px. Gdy API nie odpowie w 8 s, silnik wraca do heurystyki znaku.
Konfiguracja: skopiuj `aplikacja/model.env.przyklad` do `aplikacja/model.env`, wpisz dane i uruchom `WDROZ.cmd`
– klucz trafia tylko do `/etc/punktzycia/env` na VM (nie do gita, plik jest usuwany po wdrożeniu).

## Model AI – plan (własny model)
Heurystyka znaku ILCOR działa od razu. Każde zgłoszenie ocenione przez człowieka w panelu staje się etykietą
(jest AED / nie ma). Po ok. 500–1000 zdjęciach fine-tuning MobileNetV3 / YOLOv8n, eksport do ONNX i podmiana
przez `AED_MODEL=model.onnx` bez zmian w kodzie. System sam buduje sobie zbiór treningowy.

## Ograniczenia
- Spoofing GPS na zrootowanym telefonie jest możliwy. Bronimy się konsensusem ≥ 2 urządzeń, duplikatami i kolejką ręczną.
- Heurystyka koloru może dać fałszywy wynik dla zielonych obiektów, dlatego tylko podnosi lub obniża wynik i sama nie zatwierdza.
- Identyfikator urządzenia z `localStorage` da się zresetować. W produkcji: limit zgłoszeń na IP i konto / mObywatel.
