"""B4 - validate one ds/month (V1-V6). Usage: vz_validate.py <ds> <YYYY-MM>
"""
import argparse
import csv
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


# --- V3 (revised 2026-10-15 after a FAIL on kline1m 2023-09) ---
# 1. taker_buy_quote <= quote_volume: tolerance loosened from 1e-9 to 1e-6 RELATIVE.
#    Binance's own quote_volume carries rounding noise; a 1e-9 bound false-FAILs on it.
# 2. Any row that still violates (or matches the source-glitch exception below) is
#    written to the dataset's anomalies.csv. Data rows are NEVER edited or dropped
#    here; downstream consumers skip the listed rows.
# 3. V3 PASSes when a month has <= V3_MAX_ROWS violating rows AND
#    violations/rows <= V3_MAX_FRAC.
V3_TAKER_RTOL = 1e-6
V3_MAX_ROWS = 10
V3_MAX_FRAC = 1e-6
V3_REASON = {
    "lo": "ohlc_low_gt_min_open_close",
    "hi": "ohlc_high_lt_max_open_close",
    "taker": "taker_buy_quote_gt_quote_volume(rtol=%g)" % V3_TAKER_RTOL,
    "ntrades": "n_trades_negative",
    "glitch": "taker_buy_quote_gt_quote_volume(source_quote_volume_glitch)",
}


def anomalies_path(ds, year):
    """Canonical per-dataset-year anomalies.csv (shipped with the Kaggle dataset)."""
    return os.path.join(OUT_DIR, ds, year, "anomalies.csv")


def write_anomalies(ds, year, rows):
    """Merge (sym, ts, reason) rows into <out>/<ds>/<year>/anomalies.csv (sorted, deduped)."""
    path = anomalies_path(ds, year)
    seen = {}
    if os.path.exists(path):
        with open(path) as fh:
            for r in csv.DictReader(fh):
                seen[(r["sym"], int(r["ts"]), r["reason"])] = True
    for (sym, ts, reason) in rows:
        seen[(str(sym), int(ts), reason)] = True
    if not seen:
        return path, 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sym", "ts", "reason"])
        for (sym, ts, reason) in sorted(seen, key=lambda k: (k[1], k[0], k[2])):
            w.writerow([sym, ts, reason])
    return path, len(seen)


def v3_check(parquet, ds=None, ym=None):
    """OHLC ordering + 0 <= taker_buy_quote <= quote_volume(1+rtol) + n_trades >= 0.

    A row whose quote_volume is corrupt at the source (inconsistent with
    volume*close by orders of magnitude, Binance single-minute glitch) is logged
    as an EXCEPTION, not a violation: the lake keeps the row verbatim and every
    consumer skips it via anomalies.csv.
    """
    viol = 0
    n_exc = 0
    checked = 0
    flagged = []
    for df in rowgroup_iter(parquet, columns=["sym", "ts", "open", "high", "low", "close",
                                              "volume", "quote_volume", "taker_buy_quote",
                                              "n_trades"]):
        if df.empty:
            continue
        d = df
        lo_ok = (d["low"] <= np.minimum(d["open"], d["close"]) + 1e-12).to_numpy()
        hi_ok = (np.maximum(d["open"], d["close"]) <= d["high"] + 1e-12).to_numpy()
        tq = d["taker_buy_quote"].to_numpy("float64")
        qv = d["quote_volume"].to_numpy("float64")
        t_ok = (tq >= -V3_TAKER_RTOL * np.abs(qv)) & (tq <= qv * (1 + V3_TAKER_RTOL) + V3_TAKER_RTOL)
        n_ok = (d["n_trades"] >= 0).to_numpy()
        bad = ~(lo_ok & hi_ok & t_ok & n_ok)
        checked += len(d)
        if not bad.any():
            continue
        syms = d["sym"].astype(str).to_numpy()
        tss = d["ts"].to_numpy("int64")
        notional = d["volume"].to_numpy("float64") * d["close"].to_numpy("float64")
        glitch = (qv <= 0.5 * np.abs(notional)) & (notional > 0)
        for i in np.where(bad)[0]:
            reasons = []
            if not lo_ok[i]:
                reasons.append(V3_REASON["lo"])
            if not hi_ok[i]:
                reasons.append(V3_REASON["hi"])
            if not n_ok[i]:
                reasons.append(V3_REASON["ntrades"])
            if not t_ok[i]:
                if glitch[i]:
                    n_exc += 1
                    reasons.append(V3_REASON["glitch"])
                else:
                    viol += 1
                    reasons.append(V3_REASON["taker"])
            for r in reasons:
                flagged.append((syms[i], int(tss[i]), r))
    frac = (viol / checked) if checked else 0.0
    res = {"status": "PASS" if (viol <= V3_MAX_ROWS and frac <= V3_MAX_FRAC) else "FAIL",
           "violations": viol, "rows": checked, "viol_frac": round(frac, 12),
           "max_rows": V3_MAX_ROWS, "max_frac": V3_MAX_FRAC,
           "taker_rtol": V3_TAKER_RTOL, "exception_rows": n_exc}
    if ds and ym:
        path, n = write_anomalies(ds, ym[:4], flagged)
        res["anomalies_n"] = len({(s, t) for (s, t, _) in flagged})
        res["anomalies_csv"] = path if n else None
        res["anomalies_csv_total"] = n
    return res


def v2_v3(parquet, ds=None, ym=None, do_v2=True, do_v3=True):
    v2, info = v2_stats(parquet)
    return {"v2": v2, "v3": v3_check(parquet, ds, ym), "v2_info": info}


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
    got_path = os.path.join(tmp_out, ym + ".parquet")
    got = sha256_file(got_path)
    # the rebuild is throwaway (20 GB accumulated here on the 2026-10-14 run): drop it
    try:
        import shutil as _sh
        if got == gold:
            _sh.rmtree(os.path.join(TMP_DIR, "_v6", ds), ignore_errors=True)
    except Exception:  # noqa: BLE001
        pass
    return {"status": "PASS" if got == gold else "FAIL", "sha_orig": gold, "sha_rebuild": got}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ds")
    ap.add_argument("month")
    ap.add_argument("--only", default=None,
                    help="comma list of checks to RE-RUN, e.g. V3; other checks are "
                         "reused from the existing per-month report (no rebuild)")
    args = ap.parse_args()
    ds, ym = args.ds, args.month
    year = ym[:4]
    parquet = os.path.join(OUT_DIR, ds, year, ym + ".parquet")
    out = os.path.join(REPORT_DIR, "%s-%s.validate.json" % (ds, ym))
    only = [c.strip().upper() for c in args.only.split(",")] if args.only else None
    res = {}
    if only:
        if not os.path.exists(out):
            raise RuntimeError("--only %s needs an existing report %s" % (args.only, out))
        with open(out) as fh:
            res = json.load(fh)

    def want(c):
        return only is None or c in only

    res.update({"ds": ds, "month": ym, "parquet": parquet})
    t0 = time.time()
    if want("V1"):
        res["V1"] = v1(ds, ym)
    if ds == "kline1m":
        if want("V2") or want("V3"):
            v23 = v2_v3(parquet, ds, ym)
            if want("V2"):
                res["V2"] = v23["v2"]
                res["V2_info"] = v23["v2_info"]
            if want("V3"):
                res["V3"] = v23["v3"]
        if want("V4"):
            if year == "2020":  # sealed reservoir: V4 internal CLOSES_1H starts 2021
                res["V4"] = {"status": "SKIP", "reason": "sealed 2020 (no internal CLOSES_1H)"}
            else:
                res["V4"] = v4(parquet, ym)
    if ds == "basis1m" and want("V5"):
        res["V5"] = v5(parquet, os.path.join(OUT_DIR, "kline1m", year, ym + ".parquet"))
    if want("V6"):
        res["V6"] = v6(ds, ym)
    res["parquet_sha256"] = sha256_file(parquet)
    res["parquet_bytes"] = os.path.getsize(parquet)
    res["seconds"] = round(time.time() - t0, 1)
    os.makedirs(REPORT_DIR, exist_ok=True)
    # per-month report
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
    if res.get("V3"):
        cur["months"][ym]["V3_violations"] = res["V3"].get("violations")
        cur["months"][ym]["V3_anomalies"] = res["V3"].get("anomalies_n", 0)
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
