"""[V12 §2.2] Phan loai A1 = port nguyen van UniverseA1Classifier (tradecore.selector, r4n) + PIT onboardDate."""
import gzip
import json

TRADFI_UNDERLYING = {"EQUITY", "HK_EQUITY", "KR_EQUITY", "CN_EQUITY", "COMMODITY", "FX"}


def kind(contract_type, underlying_type):
    c = (contract_type or "").strip().upper()
    if "TRADIFI" in c or "TRADFI" in c:
        return "TRADFI"
    u = (underlying_type or "").strip().upper()
    if u in TRADFI_UNDERLYING:
        return "TRADFI"
    if u == "INDEX":
        return "INDEX"
    return "UNCLASSIFIED" if u == "" else "CRYPTO"


def load(path):
    return json.load(gzip.open(path) if path.endswith(".gz") else open(path))


def excluded(path, t_ms):
    """tap symbol bi A1 loai tai thoi diem t_ms (TRADFI/INDEX va onboardDate <= t_ms)."""
    out = set()
    for s in load(path)["symbols"]:
        if kind(s.get("contractType"), s.get("underlyingType")) in ("TRADFI", "INDEX") and int(s.get("onboardDate", 0)) <= t_ms:
            out.add(s["symbol"])
    return out


def fail_closed(path, syms, t_ms):
    """[V12 ADD8] port UniverseA1Filter.excludedIn: symbol KHONG co trong snapshot va t_ms > serverTime => loai."""
    d = load(path)
    known = {x["symbol"] for x in d["symbols"]}
    st = int(d["serverTime"])
    return set() if t_ms <= st else {s for s in syms if s not in known}
