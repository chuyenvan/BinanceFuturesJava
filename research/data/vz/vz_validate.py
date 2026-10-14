"""B4 - validate one ds/month (V1-V6). Usage: vz_validate.py <ds> <YYYY-MM>
"""
import argparse
import glob
import json
import os
import random
import struct
import sys
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from vz_common import (
    MANIFEST_DIR,
    OUT_DIR,
    REPORT_DIR,
    STATE_DIR,
    TMP_DIR,
    VISION_BASE,
    setup_logging,
    sha256_file,
    TYPES,
)

log = setup_logging("validate")
NEEDED = {"kline1m": ["kline1m"], "basis1m": ["premiumIndex1m", "markPrice1m", "indexPrice1m"],
          "metrics5m": ["metrics"], "funding": ["fundingRate"]}
CLOSES_BIN = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
SYMBOL_MAP = "/home/ubuntu/selector_pred_out/symbol_map.csv"
REC = 14


def rowgroup_iter(path, columns=None):
    pf = pq.ParquetFile(path)
    for i in range(pf.num_row_groups):
        t = pf.read_row_group(i, columns=columns)
        yield t.to_pandas()


def v1(ds, ym):
    bad = 0
    ok = 0
    missing = 0
    for st in NEEDED[ds]:
        p = os.path.join(STATE_DIR, st, ym + ".json")
        if not os.path.exists(p):
            return {"status": "FAIL", "reason": "no fetch state %s" % st}
        d = json.load(open(p))
        bad += d.get("n_bad", 0)
        ok += d.get("n_ok", 0)
        missing += d.get("n_missing", 0)
    return {"status": "PASS" if bad == 0 and ok > 0 else "FAIL",
            "n_ok": ok, "n_bad": bad, "n_missing": missing}


GAP_MIN = 60  # report continuous gaps longer than this many minutes


def v2_stats(parquet):
    """V2 (2026-10-14 definition): for each symbol the expected number of minutes
    in the month is every minute between its first and last data ts (inclusive).
    missing = span - rows. Info only (never FAIL): minutes cut on the first/last
    day (listing/delisting) and continuous gaps > GAP_MIN inside the span."""
    sym_stats = []
    for df in rowgroup_iter(parquet, columns=["ts", "sym"]):
        if df.empty:
            continue
        sym = str(df["sym"].iloc[0])
        ts = np.sort(df["ts"].to_numpy().astype("int64"))
        n = int(len(ts))
        if n == 0:
            continue
        first, last = int(ts[0]), int(ts[-1])
        span = (last - first) // 60000 + 1
        missing = int(span - n)
        step = np.diff(ts)
        gi = np.where(step > (GAP_MIN + 1) * 60000)[0]
        gaps = [(sym, int(ts[i]) + 60000, int(step[i] // 60000 - 1)) for i in gi]
        cut_first = int((first % 86400000) // 60000)
        cut_last = 1440 - 1 - int((last % 86400000) // 60000)
        sym_stats.append((sym, n, int(span), missing, cut_first, cut_last, gaps))
    tot_missing = sum(s[3] for s in sym_stats)
    tot_span = sum(s[2] for s in sym_stats)
    miss_frac = (tot_missing / tot_span) if tot_span else 0.0
    worst = sorted(((s[3], s[0]) for s in sym_stats), reverse=True)
    gaps_all = [g for s in sym_stats for g in s[6]]
    gaps_all.sort(key=lambda g: g[2], reverse=True)
    cuts = sorted(((s[4] + s[5], s[0], s[4], s[5]) for s in sym_stats), reverse=True)
    v2 = {
        "status": "PASS" if miss_frac <= 0.001 else "FAIL",
        "def": "expected=every minute between first and last data ts (per symbol,month)",
        "missing_min_frac": round(miss_frac, 6),
        "n_symbols": len(sym_stats),
        "total_missing_min": tot_missing,
        "total_expected_min": tot_span,
        "top_missing": worst[:10],
    }
    info = {
        "cut_first_last_total_min": sum(s[4] + s[5] for s in sym_stats),
        "cut_first_last_top": cuts[:10],
        "n_gaps_gt60": len(gaps_all),
        "gaps_gt60": gaps_all[:200],
    }
    return v2, info


def v3_check(parquet):
    viol = 0
    checked = 0
    for df in rowgroup_iter(parquet, columns=["open", "high", "low", "close",
                                              "quote_volume", "taker_buy_quote", "n_trades"]):
        if df.empty:
            continue
        d = df
        lo_ok = d["low"] <= np.minimum(d["open"], d["close"]) + 1e-12
        hi_ok = np.maximum(d["open"], d["close"]) <= d["high"] + 1e-12
        tq = d["taker_buy_quote"]
        qv = d["quote_volume"]
        t_ok = (tq >= -1e-9 * qv.abs()) & (tq <= qv * (1 + 1e-9) + 1e-9)
        n_ok = d["n_trades"] >= 0
        viol += int((~lo_ok).sum() + (~hi_ok).sum() + (~t_ok).sum() + (~n_ok).sum())
        checked += len(d)
    return {"status": "PASS" if viol == 0 else "FAIL", "violations": viol, "rows": checked}


def v2_v3(parquet):
    v2, info = v2_stats(parquet)
    return {"v2": v2, "v3": v3_check(parquet), "v2_info": info}


def load_closes(year, sample_n=2000, seed=42):
    import datetime
    rnd = random.Random(seed)
    symname = {}
    with open(SYMBOL_MAP) as fh:
        next(fh)
        for line in fh:
            a, b = line.strip().split(",")
            symname[int(a)] = b
    picked = []
    seen = 0
    with open(CLOSES_BIN, "rb") as fh:
        while True:
            rec = fh.read(REC)
            if len(rec) < REC:
                break
            ts, sid, close = struct.unpack(">qhf", rec)
            if datetime.datetime.utcfromtimestamp(ts / 1000).year != year:
                continue
            seen += 1
            if len(picked) < sample_n:
                picked.append((sid, ts, close))
            else:
                j = rnd.randint(0, seen - 1)
                if j < sample_n:
                    picked[j] = (sid, ts, close)
    return picked, symname


def v4(parquet, ym, sample_n=2000):
    year = int(ym[:4])
    picked, symname = load_closes(year, sample_n)
    if not picked:
        return {"status": "FAIL", "reason": "internal CLOSES has no rows for %d" % year}
    wanted = {}
    for (sid, ts, close) in picked:
        sym = symname.get(sid)
        if sym is None:
            continue
        wanted.setdefault(sym, {})[ts - 60000] = close  # last minute open_time
    ok = tot = 0
    max_rel = 0.0
    for df in rowgroup_iter(parquet, columns=["ts", "sym", "close"]):
        if df.empty:
            continue
        sym = str(df["sym"].iloc[0])
        w = wanted.get(sym)
        if not w:
            continue
        sub = df[df["ts"].isin(w)]
        for ts, got in zip(sub["ts"].to_numpy(), sub["close"].to_numpy()):
            target = w[int(ts)]
            tot += 1
            rel = abs(float(got) - float(target)) / abs(float(target)) if target else abs(float(got))
            max_rel = max(max_rel, rel)
            if rel <= 1e-6:
                ok += 1
    rate = ok / tot if tot else 0.0
    return {"status": "PASS" if tot > 0 and rate >= 0.999 else "FAIL",
            "matched": ok, "sampled": tot, "match_rate": round(rate, 6),
            "max_rel": max_rel, "year": year, "note": "pilot month has only %s klines" % ym}


def v5(basis_parquet, kline_parquet):
    # global p99 over the month on ACTIVE rows; stale rows/symbols reported separately.
    def p99(arr):
        # ignore non-finite values (a few NaN mark/prem rows must not NaN the p99)
        a = np.asarray(arr, dtype="float64")
        a = a[np.isfinite(a)]
        if a.size == 0:
            return float("nan")
        return float(np.nanpercentile(a, 99))

    kb = {}
    for df in rowgroup_iter(kline_parquet, columns=["ts", "sym", "close", "quote_volume"]):
        if df.empty:
            continue
        kb[str(df["sym"].iloc[0])] = df.set_index("ts")[["close", "quote_volume"]]
    act_m, act_p, all_m, all_p = [], [], [], []
    stale = []
    sym_max = []
    n_active_rows = 0
    n_stale_rows = 0
    for df in rowgroup_iter(basis_parquet, columns=["ts", "sym", "prem_close", "mark_close"]):
        if df.empty:
            continue
        sym = str(df["sym"].iloc[0])
        kc = kb.get(sym)
        if kc is None:
            continue
        j = df.set_index("ts").join(kc, how="inner")
        j = j[j["close"] > 0]
        if len(j) == 0:
            continue
        mr = (j["mark_close"] / j["close"] - 1).abs()
        all_m.append(mr.values)
        all_p.append(j["prem_close"].abs().values)
        a = j[j["quote_volume"] > 0]
        n_stale_rows += len(j) - len(a)
        if len(a) == 0:
            stale.append(sym)
            continue
        n_active_rows += len(a)
        amr = (a["mark_close"] / a["close"] - 1).abs()
        act_m.append(amr.values)
        act_p.append(a["prem_close"].abs().values)
        sym_max.append((round(p99(amr.values), 5), sym))
    am = np.concatenate(act_m) if act_m else np.array([0.0])
    ap = np.concatenate(act_p) if act_p else np.array([0.0])
    olm = np.concatenate(all_m) if all_m else np.array([0.0])
    n_nan_active = int(np.size(am) - np.isfinite(am).sum())
    gmark = p99(am)
    gprem = p99(ap)
    sym_max.sort(reverse=True)
    return {
        "status": "PASS" if gmark < 0.01 and gprem < 0.02 else "FAIL",
        "global_mark_p99_active": round(gmark, 6),
        "global_prem_p99_active": round(gprem, 6),
        "global_mark_p99_allrows": round(p99(olm), 6),
        "n_rows_active": int(n_active_rows),
        "n_nan_active_rows": n_nan_active,
        "n_stale_rows": int(n_stale_rows),
        "n_stale_syms_excluded": len(stale),
        "stale_syms": sorted(stale),
        "sym_mark_p99_top": sym_max[:10],
    }


def v6(ds, ym):
    # rebuild from zips to temp and compare sha
    import importlib.util
    mod_path = os.path.join(os.path.dirname(__file__), "vz_build.py")
    spec = importlib.util.spec_from_file_location("vz_build_v6", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    year = ym[:4]
    orig = os.path.join(OUT_DIR, ds, year, ym + ".parquet")
    if not os.path.exists(orig):
        return {"status": "FAIL", "reason": "orig missing"}
    gold = sha256_file(orig)
    # rebuild
    sys.argv = ["vz_build.py", ds, ym]
    # redirect OUT to a temp dir
    tmp_out = os.path.join(TMP_DIR, "_v6", ds, year)
    os.makedirs(tmp_out, exist_ok=True)
    mod.OUT_DIR = os.path.join(TMP_DIR, "_v6")
    mod.KLINE_DIR = OUT_DIR  # basis V6 rebuild reads the real kline parquet
    mod.COUNT = {"micro_fixed": 0, "dupes": 0, "files": 0, "rows_in": 0}
    import io
    old = sys.stdout
    try:
        sys.stdout = io.StringIO()
        mod.main()
    finally:
        sys.stdout = old
    got = sha256_file(os.path.join(tmp_out, ym + ".parquet"))
    return {"status": "PASS" if got == gold else "FAIL", "sha_orig": gold, "sha_rebuild": got}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ds")
    ap.add_argument("month")
    args = ap.parse_args()
    ds, ym = args.ds, args.month
    year = ym[:4]
    parquet = os.path.join(OUT_DIR, ds, year, ym + ".parquet")
    res = {"ds": ds, "month": ym, "parquet": parquet}
    t0 = time.time()
    res["V1"] = v1(ds, ym)
    if ds == "kline1m":
        v23 = v2_v3(parquet)
        res["V2"] = v23["v2"]
        res["V3"] = v23["v3"]
        res["V2_info"] = v23["v2_info"]
        if year == "2020":  # sealed reservoir: V4 internal CLOSES_1H starts 2021
            res["V4"] = {"status": "SKIP", "reason": "sealed 2020 (no internal CLOSES_1H)"}
        else:
            res["V4"] = v4(parquet, ym)
    if ds == "basis1m":
        res["V5"] = v5(parquet, os.path.join(OUT_DIR, "kline1m", year, ym + ".parquet"))
    res["V6"] = v6(ds, ym)
    res["parquet_sha256"] = sha256_file(parquet)
    res["parquet_bytes"] = os.path.getsize(parquet)
    res["seconds"] = round(time.time() - t0, 1)
    os.makedirs(REPORT_DIR, exist_ok=True)
    # per-month report
    out = os.path.join(REPORT_DIR, "%s-%s.validate.json" % (ds, ym))
    with open(out, "w") as fh:
        json.dump(res, fh, indent=1)
    # per-year aggregate (status per month, no bulk data)
    agg = os.path.join(REPORT_DIR, "%s-%s.validate.json" % (ds, year))
    cur = {"ds": ds, "year": year, "months": {}}
    if os.path.exists(agg):
        with open(agg) as fh:
            cur = json.load(fh)
    cur.setdefault("months", {})[ym] = {
        k: res.get(k, {}).get("status")
        for k in ["V1", "V2", "V3", "V4", "V5", "V6"] if k in res
    }
    cur["parquet_bytes"] = cur.get("parquet_bytes", 0) + res["parquet_bytes"]
    with open(agg, "w") as fh:
        json.dump(cur, fh, indent=1)
    log.info("ds=%s month=%s -> %s (+%s)", ds, ym, out, agg)
    for k in ["V1", "V2", "V3", "V4", "V5", "V6"]:
        if k in res:
            log.info("  %s %s", k, res[k].get("status"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
