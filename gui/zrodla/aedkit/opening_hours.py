import re
from datetime import datetime

DAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
_DAY_TOKEN = re.compile(r"^(Mo|Tu|We|Th|Fr|Sa|Su)(?:-(Mo|Tu|We|Th|Fr|Sa|Su))?$")
_TIME = re.compile(r"^(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})\+?$")


class OHParseError(ValueError):
    pass


def _days(spec: str) -> set[int]:
    out: set[int] = set()
    for part in spec.split(","):
        m = _DAY_TOKEN.match(part.strip())
        if not m:
            raise OHParseError(part)
        a = DAYS.index(m[1])
        b = DAYS.index(m[2]) if m[2] else a
        i = a
        while True:
            out.add(i)
            if i == b:
                break
            i = (i + 1) % 7
    return out


def _ranges(spec: str) -> list[tuple[int, int]]:
    out = []
    for part in spec.split(","):
        m = _TIME.match(part.strip())
        if not m:
            raise OHParseError(part)
        h1, m1, h2, m2 = map(int, m.groups())
        start, end = h1 * 60 + m1, h2 * 60 + m2
        if not (0 <= start <= 1440 and 0 <= end <= 1440):
            raise OHParseError(part)
        out.append((start, end))
    return out


def parse(oh: str) -> dict[int, list[tuple[int, int]]] | None:
    """Return {weekday: [(start_min, end_min)]}; None for 24/7. Raises OHParseError."""
    s = oh.strip()
    if not s:
        raise OHParseError("empty")
    if s in ("24/7", "Mo-Su 00:00-24:00", "00:00-24:00"):
        return None
    table: dict[int, list[tuple[int, int]]] = {d: [] for d in range(7)}
    for rule in filter(None, (r.strip() for r in s.split(";"))):
        if rule.startswith("PH"):
            continue
        tokens = rule.split(None, 1)
        if _TIME.match(tokens[0].split(",")[0]):
            days, times = set(range(7)), tokens[0] if len(tokens) == 1 else rule
        elif len(tokens) == 2:
            days, times = _days(tokens[0]), tokens[1].strip()
        else:
            raise OHParseError(rule)
        for d in days:
            if times in ("off", "closed"):
                table[d] = []
            else:
                table[d] = _ranges(times)
    return table


_PL_DAYS = [
    (r"poniedzia[łl]ek|pon\.?|pn\.?", "Mo"), (r"wtorek|wt\.?", "Tu"), (r"[śs]roda|[śs]r\.?", "We"),
    (r"czwartek|czw\.?|cz\.?", "Th"), (r"pi[ąa]tek|pi[ąa]\.?|pt\.?", "Fr"), (r"sobota|sob\.?|so\.?", "Sa"),
    (r"niedziela|niedz\.?|ndz\.?|nd\.?|nie\.?", "Su"),
]
_EN_DAYS = {"mon": "Mo", "tue": "Tu", "wed": "We", "thu": "Th", "fri": "Fr", "sat": "Sa", "sun": "Su"}
_RANGE = re.compile(r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?\s*-\s*(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?", re.I)
_ALWAYS = re.compile(r"^(24/7|24h|24 ?h/7|ca[łl]odobowo|ca[łl]a doba|non[- ]?stop|0-24|00:00-24:00|mo-su 00:00-24:00)$", re.I)


def _hm(h: str, m: str | None, ap: str | None) -> str:
    hh, mm = int(h), int(m or 0)
    if ap:
        ap = ap.lower().replace(".", "")
        if ap == "pm" and hh < 12:
            hh += 12
        if ap == "am" and hh == 12:
            hh = 0
    if not (0 <= hh <= 24 and 0 <= mm < 60):
        raise OHParseError(f"{h}:{m}")
    return f"{hh:02d}:{mm:02d}"


def normalize(s: str) -> str:
    """Polish/12h/loose notation → OSM opening_hours. Raises OHParseError if still unparseable."""
    t = re.sub(r"[–—−]", "-", s.strip())
    t = re.sub(r"\s*-\s*", "-", t)
    if _ALWAYS.match(t):
        return "24/7"
    t = re.sub(r"\b(od|do|godz\.?|w godz\.?)\b", " ", t, flags=re.I)
    for rx, code in _PL_DAYS:
        t = re.sub(rf"(?<![A-Za-z]){rx}(?![a-ząćęłńóśźż])", code, t, flags=re.I)
    for en, code in _EN_DAYS.items():
        t = re.sub(rf"\b{en}[a-z]*\.?", code, t, flags=re.I)
    t = re.sub(r"\b(zamkni[ęe]te|nieczynne|closed)\b", "off", t, flags=re.I)

    def rng(m):
        ap1 = m[3]
        if not ap1 and m[6]:
            ap1 = m[6] if int(m[1]) <= int(m[4]) else "am"
        return f"{_hm(m[1], m[2], ap1)}-{_hm(m[4], m[5], m[6])}"

    t = _RANGE.sub(rng, t)
    t = re.sub(r"\s*,\s*(?=[A-Z][a-z])", "; ", t)
    t = re.sub(r"(\d{2}:\d{2})\s*,\s*(?=[A-Z][a-z])", r"\1; ", t)
    t = re.sub(r"\s+", " ", t).strip(" ;")
    t = re.sub(r"(Mo|Tu|We|Th|Fr|Sa|Su)\s*:\s*", r"\1 ", t)
    parse(t)
    return t


def is_open(oh: str, at: datetime) -> bool | None:
    """True/False if computable, None if syntax is not supported."""
    try:
        table = parse(oh)
    except OHParseError:
        return None
    if table is None:
        return True
    wd, minute = at.weekday(), at.hour * 60 + at.minute
    for start, end in table[wd]:
        if start <= end and start <= minute < end:
            return True
        if start > end and minute >= start:
            return True
    for start, end in table[(wd - 1) % 7]:
        if start > end and minute < end:
            return True
    return False


def weekly_minutes(oh: str) -> int | None:
    try:
        table = parse(oh)
    except OHParseError:
        return None
    if table is None:
        return 7 * 1440
    return sum((e - s) if e >= s else (1440 - s + e) for rs in table.values() for s, e in rs)
