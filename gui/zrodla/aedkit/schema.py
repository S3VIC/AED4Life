FIELDS = [
    "id_aed", "nazwa_obiektu", "etykieta", "lat", "lon", "miejscowosc", "kod_pocztowy",
    "cecha_adresu", "ulica", "numer_budynku", "kod_teryt_gminy", "stacjonarny",
    "umiejscowienie", "poziom_pietro", "opis_dojscia", "opis_dojscia_en", "zdjecie_url",
    "kategoria_dostepu", "calodobowo", "godziny_dostepu", "sposob_otwarcia",
    "status_sprawnosci", "elektrody_dzieciece", "producent", "model", "data_przegladu",
    "data_waznosci_elektrod", "data_waznosci_baterii", "dysponent_nazwa", "dysponent_typ",
    "kontakt_telefon", "kontakt_email", "data_weryfikacji", "sposob_weryfikacji", "zrodlo",
    "id_zrodla", "data_aktualizacji", "wskaznik_jakosci",
    "status_rekordu", "sposob_geokodowania", "licencja_zrodla", "data_dodania_w_zrodle",
]

STATUS_REKORDU = ("zgloszony", "zweryfikowany", "wymaga_sprawdzenia", "usuniety")

LICENSES = {
    "osm": "ODbL-1.0",
    "dysponent": "CC0-1.0",
    "potwierdzenie_qr": "CC0-1.0",
    "zgloszenie_mieszkanca": "CC0-1.0",
    "dane_miasta": "do_ustalenia",
    "organizacja_pozarzadowa": "do_ustalenia",
    "inne": "do_ustalenia",
}

CITY_CENTROIDS = {
    "warszawa": (52.2297, 21.0122), "kraków": (50.0647, 19.9450), "łódź": (51.7592, 19.4560),
    "wrocław": (51.1079, 17.0385), "poznań": (52.4064, 16.9252), "gdańsk": (54.3520, 18.6466),
    "szczecin": (53.4285, 14.5528), "bydgoszcz": (53.1235, 18.0084), "lublin": (51.2465, 22.5684),
    "białystok": (53.1325, 23.1688), "katowice": (50.2649, 19.0238), "gdynia": (54.5189, 18.5305),
    "częstochowa": (50.8118, 19.1203), "radom": (51.4027, 21.1471), "toruń": (53.0138, 18.5984),
    "rzeszów": (50.0412, 21.9991), "kielce": (50.8661, 20.6286), "olsztyn": (53.7784, 20.4801),
    "opole": (50.6751, 17.9213), "zielona góra": (51.9356, 15.5062),
}

MINIMUM = [
    "id_aed", "lat", "lon", "miejscowosc", "stacjonarny", "umiejscowienie",
    "kategoria_dostepu", "calodobowo", "sposob_otwarcia", "status_sprawnosci",
    "dysponent_nazwa", "data_weryfikacji", "zrodlo",
]

RECOMMENDED = [
    "nazwa_obiektu", "kod_pocztowy", "cecha_adresu", "ulica", "numer_budynku",
    "poziom_pietro", "opis_dojscia", "data_przegladu", "dysponent_typ", "kontakt_telefon",
    "kontakt_email", "sposob_weryfikacji", "id_zrodla",
]

DICTS = {
    "umiejscowienie": {"w_budynku", "na_zewnatrz_budynku", "w_pojezdzie", "inne"},
    "kategoria_dostepu": {"publiczny", "dla_klientow", "za_zgoda", "prywatny", "brak_dostepu", "nieznany"},
    "sposob_otwarcia": {"swobodny", "kod_od_dyspozytora", "klucz_u_pracownika", "pomoc_pracownika", "nieznany"},
    "status_sprawnosci": {"sprawny", "niesprawny", "w_serwisie", "nieznany"},
    "dysponent_typ": {"jst", "sluzby_ratownicze", "oswiata", "ochrona_zdrowia", "transport",
                      "handel_i_uslugi", "organizacja_pozarzadowa", "inny"},
    "sposob_weryfikacji": {"kontrola_dysponenta", "potwierdzenie_qr", "zdjecie",
                           "zgloszenie_spolecznosci", "brak_weryfikacji"},
    "zrodlo": {"dysponent", "osm", "dane_miasta", "organizacja_pozarzadowa", "potwierdzenie_qr", "zgloszenie_mieszkanca", "inne"},
    "cecha_adresu": {"ul.", "al.", "pl.", "os.", "rondo", "brak"},
}

DICT_FALLBACK = {
    "umiejscowienie": "inne",
    "kategoria_dostepu": "nieznany",
    "sposob_otwarcia": "nieznany",
    "status_sprawnosci": "nieznany",
    "dysponent_typ": "inny",
    "sposob_weryfikacji": "brak_weryfikacji",
    "zrodlo": "inne",
    "cecha_adresu": None,
}

BOOL_FIELDS = ["stacjonarny", "calodobowo", "elektrody_dzieciece"]
DATE_FIELDS = ["data_przegladu", "data_waznosci_elektrod", "data_waznosci_baterii",
               "data_weryfikacji", "data_aktualizacji"]

LAT_RANGE = (48.99, 54.84)
LON_RANGE = (14.11, 24.16)
