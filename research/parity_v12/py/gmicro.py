#!/usr/bin/env python3
"""[ADD11 fbe9c4cf] Cong G-MICRO: (i) >= 7 ngay SACH tu 2026-11-04 (r4n + r4q); (ii) >= 1 ngay SACH tron r4q (khong phai ngay swap)
+ smoke 24 h sau swap (0 ERROR, 0 LATCH trong log app 242). Ngay TRUOT bat ky => DUNG dem (MASTER chan doan).
SACH <=> ket_luan == "DAT" va ngay_sach == "SACH". Ham thuan count() de test; collect()/smoke() doc file (chi doc)."""
import datetime as dt
import glob
import gzip
import json
import os
import re

START = "2026-11-04"
N_SACH = 7


def is_sach(v):
    return v.get("ket_luan") == "DAT" and v.get("ngay_sach") == "SACH"


def is_count(v):
    """[ADD12] SACH hoac SACH-T deu dem cho G-MICRO."""
    return is_sach(v) or bool(v.get("SACH_T"))


def count(days, smoke_ok):
    """days: {D: {ket_luan, ngay_sach, jar, swap_day}} ; smoke_ok: True/False/None (None = chua do)."""
    out = {"sach": [], "khong_tinh": {}, "dung_vi_truot": None}
    for d in sorted(days):
        if d < START:
            continue
        v = days[d]
        if (v.get("ket_luan") or "").startswith("TRUOT"):
            out["dung_vi_truot"] = d
            break
        if is_count(v):
            out["sach"].append(d)
        else:
            out["khong_tinh"][d] = "%s | %s" % (v.get("ket_luan"), v.get("ngay_sach"))
    r4q_full = [d for d in out["sach"] if days[d].get("jar") not in (None, "r4n") and not days[d].get("swap_day")]
    out["n_sach"] = len(out["sach"])
    out["sach_T"] = [d for d in out["sach"] if not is_sach(days[d])]
    out["needs_M_regrade"] = [d for d in out["sach"]]   # [ADD12 §3] dieu kien G-PILOT, khong phai G-MICRO
    out["i"] = out["n_sach"] >= N_SACH
    out["r4q_sach_tron"] = r4q_full
    out["smoke_24h"] = smoke_ok
    out["ii"] = bool(r4q_full) and smoke_ok is True
    if out["dung_vi_truot"]:
        out["G_MICRO"] = "DUNG (TRUOT %s) - MASTER chan doan" % out["dung_vi_truot"]
    elif out["i"] and out["ii"]:
        out["G_MICRO"] = "DAT"
    else:
        out["G_MICRO"] = "CHUA DU (i=%s %d/%d, ii=%s)" % (out["i"], out["n_sach"], N_SACH, out["ii"])
    return out


TS = re.compile(rb"^(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):(\d\d)\.(\d{3}) ")
ERR = re.compile(rb"^\d\d/\d\d/\d{4} \d\d:\d\d:\d\d\.\d{3} ERROR ")
LATCH = re.compile(rb"LATCH")


def ms_of(m):
    d, mo, y, h, mi, s, ms = (int(x) for x in m.groups())
    return int((dt.datetime(y, mo, d, h, mi, s) - dt.timedelta(hours=7) - dt.datetime(1970, 1, 1)).total_seconds() * 1000) + ms


def smoke(root, start_ms, hours=24):
    """0 ERROR va 0 LATCH trong [start_ms, start_ms + hours] tren log_window.gz da pull. None neu log chua phu het cua so."""
    end = start_ms + hours * 3600000
    days = sorted({dt.datetime.utcfromtimestamp(t / 1000).strftime("%Y-%m-%d") for t in (start_ms, end)})
    n_err = n_latch = 0
    lo = hi = None
    for d in days:
        p = "%s/d/%s/live/log_window.gz" % (root, d)
        if not os.path.exists(p):
            return None, {"thieu_log": d}
        with gzip.open(p, "rb") as f:
            for ln in f:
                m = TS.match(ln)
                if not m:
                    continue
                t = ms_of(m)
                lo = t if lo is None else min(lo, t)
                hi = t if hi is None else max(hi, t)
                if start_ms <= t <= end:
                    n_err += bool(ERR.match(ln))
                    n_latch += bool(LATCH.search(ln))
    info = {"ERROR": n_err, "LATCH": n_latch, "log_from": lo, "log_to": hi, "win": [start_ms, end]}
    if hi is None or hi < end:
        return None, info
    return (n_err == 0 and n_latch == 0), info


def collect(repo):
    """gop ket qua tung ngay tu docs/result/parity_v12_d*/parity_v12_d*.json (ban moi nhat moi ngay)."""
    days = {}
    for p in sorted(glob.glob(repo + "/docs/result/parity_v12_d*/parity_v12_d*.json"), key=os.path.getmtime):
        try:
            for d, v in json.load(open(p))["days"].items():
                days[d] = v
        except Exception:
            continue
    return days
