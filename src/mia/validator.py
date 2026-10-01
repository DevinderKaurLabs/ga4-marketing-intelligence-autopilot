"""The number guard: every number the AI writes must exist in the payload."""
import re

MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
DATE_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTHS}\b", re.I),
    re.compile(rf"\b{MONTHS}\s+\d{{1,2}}(?:st|nd|rd|th)?\b", re.I),
    re.compile(r"\b(?:19|20)\d{2}\b"),
]
NUMBER = re.compile(r"(?<![\w.])[-+]?[$£€]?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*(%|k\b|K\b|m\b|M\b)?")


def _walk_numbers(obj, out: set):
    if isinstance(obj, bool) or obj is None:
        return
    if isinstance(obj, (int, float)):
        out.add(abs(float(obj)))
    elif isinstance(obj, str):
        for n in _extract(obj):
            out.add(n["value"])
    elif isinstance(obj, dict):
        for v in obj.values():
            _walk_numbers(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_numbers(v, out)


def allowed_numbers(payload: dict) -> set:
    out: set = set()
    _walk_numbers(payload, out)
    return out


def _strip_dates(text: str) -> str:
    for pat in DATE_PATTERNS:
        text = pat.sub(" ", text)
    return text


def _extract(text: str) -> list:
    text = text.replace("\u2212", "-").replace("\u2013", "-")
    clean = _strip_dates(text)
    found = []
    for m in NUMBER.finditer(clean):
        whole, frac, suffix = m.group(1), m.group(2) or "", (m.group(3) or "").lower()
        value = float(whole.replace(",", "") + frac)
        found.append({"text": m.group(0).strip(), "value": abs(value), "decimals": len(frac) - 1 if frac else 0,
                      "suffix": suffix, "start": m.start(), "context": clean[max(0, m.start() - 40):m.end() + 20]})
    return found


def _matches(n: dict, allowed: set) -> bool:
    x, d, suffix = n["value"], n["decimals"], n["suffix"]
    scale = {"k": 1e3, "m": 1e6}.get(suffix, 1)
    for a in allowed:
        a_scaled = a / scale
        if abs(a_scaled - x) < 1e-9 or abs(round(a_scaled, d) - x) < 1e-9:
            return True
        if d == 0 and scale == 1 and x >= 100:  # "about 33,000" for 32,560
            for r in (-1, -2, -3):
                if x % (10 ** -r) == 0 and abs(round(a, r) - x) < 1e-9:
                    return True
    return False


def _texts(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _texts(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _texts(v, f"{path}[{i}]")


def validate(brief: dict, allowed: set) -> dict:
    invalid, checked = [], 0
    for path, text in _texts(brief):
        for n in _extract(text):
            is_small_count = n["decimals"] == 0 and not n["suffix"] and n["value"] <= 10
            if is_small_count:
                continue  # "three actions", "2 weeks"
            checked += 1
            if not _matches(n, allowed):
                invalid.append({"text": n["text"], "field": path, "context": n["context"].strip()})
    return {"passed": not invalid, "numbers_checked": checked, "invalid": invalid}
