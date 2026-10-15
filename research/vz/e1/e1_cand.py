#!/usr/bin/env python3
"""QUEUE_1015 P4 — layer join: gan feature E1 (as-of, CAUSAL) vao tap UNG VIEN 2024.

Khong tinh outcome (de MASTER pre-reg sau). Chi:
  1. doc CSV ung vien do kernel `SIM_EXPORT_CANDIDATES` xuat
     (ts,symbol,bar_ret,p15,thr_base,q_t,gate_pass,gate_reason,s1,rank,topk,entered);
  2. gan feature E1 as-of CAUSAL tu nen kline 1m: chi dung NEN DA DONG truoc ts
     (ret_5m/ret_15m/ret_1h + range_15m) => khong nhin tuong lai;
  3. smoke + kiem V-a causal: them mot nen TUONG LAI => feature qua khu KHONG doi.

Nguon kline: ham `bar_provider(symbol, ts)` (test dung synthetic). Production truyen
ham doc tu lake VZ (`research/vz/e1/e1_data.py`) — KHONG fetch trong script nay.

Usage:
  python3 e1_cand.py --cand /path/cands.csv --out /path/cands_e1.csv
  python3 e1_cand.py --smoke
"""
import argparse
import csv
import logging
import sys

log = logging.getLogger("e1_cand")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    stream=sys.stderr)

MIN_MS = 60_000
FEATS = ("ret_5m", "ret_15m", "ret_1h", "range_15m")


def _close_before(bars, ts):
    """Chi lay nen DA DONG truoc ts: close_time <= ts. bars = list[(open_ms, close_ms, high, low, close)] sorted."""
    out = []
    for b in bars:
        if b[1] <= ts:
            out.append(b)
        else:
            break
    return out


def features(bars, ts):
    """Feature as-of tai ts (causal). bars: list[(open_ms, close_ms, high, low, close)] sorted by open_ms."""
    past = _close_before(bars, ts)
    if not past:
        return {k: None for k in FEATS}
    c_last = past[-1][4]

    def ret(n):
        if len(past) < n:
            return None
        c0 = past[-n][4]
        return (c_last - c0) / c0 if c0 else None

    win15 = past[-15:] if len(past) >= 15 else past
    lo = min(b[3] for b in win15)
    hi = max(b[2] for b in win15)
    return {"ret_5m": ret(5), "ret_15m": ret(15), "ret_1h": ret(60),
            "range_15m": (hi - lo) / lo if lo else None}


def join(cands, bars_by_sym, bar_provider=None):
    """cands: list[dict] co 'ts','symbol'. bars_by_sym: dict sym->bars (hoac dung bar_provider)."""
    out = []
    for c in cands:
        sym = c["symbol"]
        ts = int(c["ts"])
        bars = bar_provider(sym) if bar_provider else bars_by_sym.get(sym, [])
        f = features(bars, ts)
        row = dict(c)
        row.update(f)
        out.append(row)
    return out


def load_candidates(path):
    rows = []
    with open(path, newline="") as fh:
        for r in csv.DictReader(fh):
            if r.get("ts") and r.get("symbol"):
                rows.append(r)
    return rows


def smoke():
    """Smoke + V-a causal: them nen tuong lai => feature qua khu KHONG doi."""
    ts = 1791472860000  # 1 moc bat ky
    bars = [(ts - (60 - i) * MIN_MS, ts - (60 - i) * MIN_MS + MIN_MS - 1,
             100.0 + i, 99.0 + i, 100.0 + i) for i in range(60)]
    f1 = features(bars, ts)
    # them 5 nen TUONG LAI (close_time > ts)
    bars2 = list(bars) + [(ts + k * MIN_MS, ts + k * MIN_MS + MIN_MS - 1, 999.0, 1.0, 999.0)
                          for k in range(5)]
    f2 = features(bars2, ts)
    assert f1 == f2, ("CAUSAL VIOLATION: them nen tuong lai doi feature qua khu", f1, f2)
    assert f1["ret_5m"] is not None and f1["ret_1h"] is not None, f1
    # ts truoc moi du lieu => tat ca None
    assert all(v is None for v in features(bars, bars[0][0]).values())
    cands = [{"ts": str(ts), "symbol": "BTCUSDT", "s1": "0.2", "rank": "3", "entered": "1"}]
    joined = join(cands, {"BTCUSDT": bars})
    assert joined[0]["ret_5m"] == f1["ret_5m"]
    log.info("smoke OK: causal (them nen tuong lai khong doi feature) + join %d dong", len(joined))
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cand")
    ap.add_argument("--out")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if a.smoke or not a.cand:
        return 0 if smoke() else 1
    raise SystemExit("production join can bar_provider tu lake VZ (chua wire trong script nay)")


if __name__ == "__main__":
    sys.exit(main())
