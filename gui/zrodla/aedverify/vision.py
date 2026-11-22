import hashlib
import io
import json
import os

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None

_model = None
MODEL_PATH = os.environ.get("AED_MODEL", "")
API_URL = os.environ.get("AED_MODEL_URL", "")
API_KEY = os.environ.get("AED_MODEL_KEY", "")
API_CLASSES = {c.strip().lower() for c in os.environ.get("AED_MODEL_CLASSES", "aed,defibrillator,defibrylator,aed-sign,aed_sign").split(",") if c.strip()}


def _api(data):
    import base64
    import urllib.parse
    import urllib.request
    url = API_URL + ("&" if "?" in API_URL else "?") + urllib.parse.urlencode({"api_key": API_KEY, "confidence": 10})
    body = base64.b64encode(_small(data))
    req = urllib.request.Request(url, body, {"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=float(os.environ.get("AED_MODEL_TIMEOUT", "8"))) as r:
        j = json.loads(r.read())
    preds = j.get("predictions") or []
    if isinstance(preds, dict):
        preds = [{"class": k, "confidence": v.get("confidence", 0)} for k, v in preds.items()]
    hits = [p for p in preds if str(p.get("class", "")).lower() in API_CLASSES] if API_CLASSES else preds
    best = max((float(p.get("confidence", 0)) for p in hits), default=0.0)
    return round(best, 3), {"metoda": "model_yolo", "wykrycia": len(hits)}


def _small(data):
    if Image is None:
        return data
    try:
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
        im.thumbnail((1280, 1280))
        b = io.BytesIO()
        im.save(b, "JPEG", quality=85)
        return b.getvalue()
    except Exception:
        return data


def _load():
    global _model
    if _model is None and MODEL_PATH and os.path.exists(MODEL_PATH):
        try:
            import onnxruntime as ort
            _model = ort.InferenceSession(MODEL_PATH)
        except Exception:
            _model = False
    return _model or None


def _img(data):
    if Image is None:
        return None
    try:
        im = Image.open(io.BytesIO(data))
        im = ImageOps.exif_transpose(im).convert("RGB")
        return im
    except Exception:
        return None


def phash(data):
    im = _img(data)
    if im is None:
        return "sha:" + hashlib.sha256(data).hexdigest()[:16]
    g = im.convert("L").resize((9, 8))
    p = list(g.get_flattened_data())
    bits = 0
    for r in range(8):
        for c in range(8):
            bits = (bits << 1) | (p[r * 9 + c] > p[r * 9 + c + 1])
    return f"d:{bits:016x}"


def hash_distance(a, b):
    if a[:2] != "d:" or b[:2] != "d:":
        return 0 if a == b else 64
    return bin(int(a[2:], 16) ^ int(b[2:], 16)).count("1")


def _heuristic(im):
    im = im.resize((192, 192))
    hsv = im.convert("HSV").get_flattened_data()
    green = white = 0
    for h, s, v in hsv:
        if 85 <= h <= 115 and s >= 120 and v >= 80:
            green += 1
        elif s < 40 and v > 200:
            white += 1
    n = 192 * 192
    gr, wr = green / n, white / n
    score = min(1.0, gr / 0.06) * (0.85 + 0.15 * min(1.0, wr / 0.05))
    return round(score, 3), {"zielony_znak": round(gr, 4)}


def _onnx(sess, im):
    import numpy as np
    x = np.asarray(im.resize((224, 224)), dtype="float32") / 255.0
    x = ((x - [0.485, 0.456, 0.406]) / [0.229, 0.224, 0.225]).transpose(2, 0, 1)[None].astype("float32")
    out = sess.run(None, {sess.get_inputs()[0].name: x})[0].ravel()
    e = np.exp(out - out.max())
    return float((e / e.sum())[-1])


def aed_score(data):
    if API_URL and API_KEY:
        try:
            return _api(data)
        except Exception as e:
            fallback = type(e).__name__
        else:
            fallback = None
    else:
        fallback = None
    im = _img(data)
    if im is None:
        return None, {"metoda": "brak"}
    sess = _load()
    if sess:
        try:
            return round(_onnx(sess, im), 3), {"metoda": "model"}
        except Exception:
            pass
    s, info = _heuristic(im)
    info["metoda"] = "heurystyka_znaku_ilcor"
    if fallback:
        info["blad_modelu"] = fallback
    return s, info
