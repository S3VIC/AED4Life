import struct
from datetime import datetime


def _segments(data):
    if data[:2] != b"\xff\xd8":
        return
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            return
        m = data[i + 1]
        if m in (0xD9, 0xDA):
            return
        ln = struct.unpack(">H", data[i + 2:i + 4])[0]
        yield m, i, ln + 2, data[i + 4:i + 2 + ln]
        i += 2 + ln


def _ifd(t, off, e):
    n = struct.unpack(e + "H", t[off:off + 2])[0]
    out = {}
    sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8}
    for k in range(n):
        p = off + 2 + 12 * k
        tag, typ, cnt = struct.unpack(e + "HHI", t[p:p + 8])
        sz = sizes.get(typ, 1) * cnt
        vo = p + 8 if sz <= 4 else struct.unpack(e + "I", t[p + 8:p + 12])[0]
        raw = t[vo:vo + sz]
        if typ == 2:
            v = raw.split(b"\0")[0].decode("ascii", "ignore")
        elif typ == 3:
            v = struct.unpack(e + "H" * cnt, raw)
        elif typ == 4:
            v = struct.unpack(e + "I" * cnt, raw)
        elif typ in (5, 10):
            f = "I" if typ == 5 else "i"
            v = tuple(a / b if b else 0.0 for a, b in zip(*[iter(struct.unpack(e + f * 2 * cnt, raw))] * 2))
        else:
            v = raw
        out[tag] = v[0] if isinstance(v, tuple) and len(v) == 1 and tag not in (2, 4) else v
    return out


def _dms(v, ref):
    d = v[0] + v[1] / 60 + v[2] / 3600
    return -d if ref in ("S", "W") else d


def read(data):
    res = {"lat": None, "lon": None, "czas": None, "gps_czas": None, "model": None, "jest_exif": False}
    for m, _, _, body in _segments(data):
        if m != 0xE1 or not body.startswith(b"Exif\0\0"):
            continue
        t = body[6:]
        try:
            e = "<" if t[:2] == b"II" else ">"
            ifd0 = _ifd(t, struct.unpack(e + "I", t[4:8])[0], e)
            res["jest_exif"] = True
            res["model"] = ifd0.get(0x0110)
            if 0x8769 in ifd0:
                sub = _ifd(t, ifd0[0x8769], e)
                s = sub.get(0x9003) or ifd0.get(0x0132)
                if s:
                    try:
                        res["czas"] = datetime.strptime(s, "%Y:%m:%d %H:%M:%S")
                    except ValueError:
                        pass
            if 0x8825 in ifd0:
                g = _ifd(t, ifd0[0x8825], e)
                if 2 in g and 4 in g:
                    res["lat"] = _dms(g[2], g.get(1, "N"))
                    res["lon"] = _dms(g[4], g.get(3, "E"))
                if 29 in g and 7 in g:
                    h, mi, se = g[7]
                    try:
                        res["gps_czas"] = datetime.strptime(g[29], "%Y:%m:%d").replace(hour=int(h), minute=int(mi), second=int(se))
                    except ValueError:
                        pass
        except (struct.error, IndexError, KeyError, TypeError, ZeroDivisionError):
            pass
        break
    return res


def strip(data):
    if data[:2] != b"\xff\xd8":
        return data
    out = bytearray(b"\xff\xd8")
    end = 2
    for m, i, ln, _ in _segments(data):
        end = i + ln
        if m == 0xE1 or (0xE2 <= m <= 0xEF and m != 0xEE) or m == 0xFE:
            continue
        out += data[i:i + ln]
    out += data[end:]
    return bytes(out)
