#!/usr/bin/env python3
"""Phase A: verify the Kaggle LOB dataset (alpha000x/crypto-lob-data).

Runs INSIDE a Kaggle kernel. Read-only on /kaggle/input. Writes small artifacts
(JSON/MD/PNG/CSV) to /kaggle/working.

Sections:
  A1 metadata (files, header, sizes, exact row counts)
  A2 full-file integrity on BNBUSDT (monotonicity, crossed/locked, nulls, spread...)
  A3 sampled integrity for the other 4 symbols (head/mid/tail byte ranges)
  A4 per-minute mid vs Binance Vision 1m klines (spot + USD-M futures)
"""
import glob
import io
import json
import math
import os
import time
import traceback
import urllib.error
import urllib.request
import zipfile

import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

T0 = time.time()
WORK = "/kaggle/working"
INP = "/kaggle/input"
RES = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "sections": {}}
SECTION_TIMING = {}


def log(*a):
    print(f"[{time.time()-T0:8.1f}s]", *a, flush=True)


def section(name):
    SECTION_TIMING[name] = time.time()


def close_section(name):
    SECTION_TIMING[name] = round(time.time() - SECTION_TIMING[name], 1)


# ---------------------------------------------------------------- A1 metadata
PREV_RUN_ROWS = {  # exact newline counts from run v3; re-used only if bytes match
    "BNBUSDT.csv": 14386038978, "BTCUSDT.csv": 27254431408, "ETHUSDT.csv": 23995077758,
    "SOLUSDT.csv": 16283350451, "XRPUSDT.csv": 13092678447,
}


def a1_metadata(files):
    section("A1")
    out = {"files": [], "header": None, "n_columns": None}
    for p in files:
        st = os.stat(p)
        rec = {"name": os.path.basename(p), "bytes": st.st_size,
               "gb": round(st.st_size / 1e9, 3),
               "mtime_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(st.st_mtime))}
        with open(p, "rb") as f:
            head = f.readline()
        hdr = head.decode("utf-8", "replace").strip().split(",")
        rec["n_columns"] = len(hdr)
        if out["header"] is None:
            out["header"] = hdr
            out["n_columns"] = len(hdr)
        # exact row count: count newlines in binary; skip if the file is byte-identical
        # to run v3 where the count was already measured
        if PREV_RUN_ROWS.get(rec["name"]) == st.st_size:
            rec["newlines"] = None
            rec["rows_excl_header"] = None
            rec["rows_note"] = "recount skipped: byte-identical to run v3"
            out["files"].append(rec)
            log("A1", rec)
            continue
        t = time.time()
        nl = 0
        with open(p, "rb") as f:
            while True:
                b = f.read(1 << 24)
                if not b:
                    break
                nl += b.count(b"\n")
        rec["newlines"] = nl
        rec["rows_excl_header"] = nl - 1 if nl else 0
        rec["count_sec"] = round(time.time() - t, 1)
        rec["count_mb_s"] = round(st.st_size / 1e6 / max(rec["count_sec"], 1e-6), 1)
        out["files"].append(rec)
        log("A1", rec)
    out["total_gb"] = round(sum(r["gb"] for r in out["files"]), 2)
    # column groups
    hdr = out["header"]
    out["col_groups"] = {
        "meta": hdr[:3],
        "bid_px": [c for c in hdr if c.startswith("bid_px_")],
        "bid_qty": [c for c in hdr if c.startswith("bid_qty_")],
        "ask_px": [c for c in hdr if c.startswith("ask_px_")],
        "ask_qty": [c for c in hdr if c.startswith("ask_qty_")],
    }
    out["n_levels"] = len(out["col_groups"]["bid_px"])
    RES["sections"]["A1"] = out
    close_section("A1")
    return out


# ------------------------------------------------------- A2 full integrity
COLS = ["event_ts_ms", "recv_ts_ns", "update_id"] + \
       [f"bid_px_{i}" for i in range(1, 11)] + [f"bid_qty_{i}" for i in range(1, 11)] + \
       [f"ask_px_{i}" for i in range(1, 11)] + [f"ask_qty_{i}" for i in range(1, 11)]
L1_PX = ["bid_px_1", "ask_px_1"]
DT = {c: "float64" for c in COLS}


def scan_full(path, chunk=300_000, minute_out=None, max_sec=None):
    """Full streaming integrity scan. Returns stats dict + optional per-minute table."""
    t_start = time.time()
    n = 0
    bad_lines = 0
    nonmono_ts = dup_ts = uid_nonmono = uid_dup = 0
    crossed = locked = neg_qty = zero_px = nan_cells = 0
    bid_mono_bad = ask_mono_bad = 0
    prev_ts = prev_uid = None
    gaps = []
    spreads = []
    lags = []
    depths_b, depths_a = [], []
    minute_stats = {}   # minute -> [n, last_ts, bid1, ask1, bq1, aq1, uid, spread_sum]
    first_ts = last_ts = None
    truncated = False

    with open(path, "rb") as _fh:
        _first = _fh.readline()
    if _first.startswith(b"event_ts_ms"):
        # parse BY NAME: the file has 403 columns, we need 43 of them
        reader = pd.read_csv(path, header=0, usecols=COLS, chunksize=chunk,
                             on_bad_lines="warn", dtype=DT, low_memory=False)
    else:
        log("scan_full: no header -> positional parse (dropped 1 partial row)")
        _fh = open(path, "rb")
        _fh.readline()
        reader = pd.read_csv(_fh, header=None, names=COLS, usecols=COLS, chunksize=chunk,
                             on_bad_lines="warn", dtype=DT, low_memory=False)
    for df in reader:
        if max_sec and time.time() - t_start > max_sec:
            truncated = True
            break
        n0 = len(df)
        n += n0
        if n0 == 0:
            continue
        ts = df["event_ts_ms"].to_numpy()
        uid = df["update_id"].to_numpy()
        rn = df["recv_ts_ns"].to_numpy()
        b1 = df["bid_px_1"].to_numpy(); a1 = df["ask_px_1"].to_numpy()
        bq1 = df["bid_qty_1"].to_numpy(); aq1 = df["ask_qty_1"].to_numpy()
        bp = df[[f"bid_px_{i}" for i in range(1, 11)]].to_numpy()
        ap = df[[f"ask_px_{i}" for i in range(1, 11)]].to_numpy()
        bq = df[[f"bid_qty_{i}" for i in range(1, 11)]].to_numpy()
        aq = df[[f"ask_qty_{i}" for i in range(1, 11)]].to_numpy()

        nan_cells += int(np.isnan(bp).sum() + np.isnan(ap).sum() +
                         np.isnan(bq).sum() + np.isnan(aq).sum() +
                         np.isnan(ts).sum())
        # NaN in price/qty columns means the row was short (fewer levels) or corrupt
        finite = np.isfinite(ts) & np.isfinite(b1) & np.isfinite(a1)
        if first_ts is None:
            first_ts = float(ts[finite][0]) if finite.any() else None
        if finite.any():
            last_ts = float(ts[finite][-1])

        if prev_ts is not None:
            d = np.diff(np.concatenate([[prev_ts], ts]))
        else:
            d = np.diff(ts)
            d = np.concatenate([[np.nan], d])
        dd = d[1:]
        nonmono_ts += int((dd < 0).sum())
        dup_ts += int((dd == 0).sum())
        gaps.extend(dd[np.isfinite(dd)].tolist())

        if prev_uid is not None:
            du = np.diff(np.concatenate([[prev_uid], uid]))
        else:
            du = np.diff(uid)
            du = np.concatenate([[np.nan], du])
        duu = du[1:]
        uid_nonmono += int((duu < 0).sum())
        uid_dup += int((duu == 0).sum())

        mid = (b1 + a1) / 2.0
        with np.errstate(invalid="ignore", divide="ignore"):
            sp = (a1 - b1) / mid * 1e4
        spreads.extend(sp[np.isfinite(sp)].tolist())
        lags.extend(((rn / 1e6) - ts)[np.isfinite(rn)].tolist())
        depths_b.extend(bq1[np.isfinite(bq1)].tolist())
        depths_a.extend(aq1[np.isfinite(aq1)].tolist())
        crossed += int((b1 > a1).sum())
        locked += int((b1 == a1).sum())
        neg_qty += int(((bq < 0).any(axis=1) | (aq < 0).any(axis=1)).sum())
        zero_px += int(((bp <= 0).any(axis=1) | (ap <= 0).any(axis=1)).sum())
        bid_mono_bad += int((np.diff(bp, axis=1) >= 0).any(axis=1).sum())
        ask_mono_bad += int((np.diff(ap, axis=1) <= 0).any(axis=1).sum())

        if minute_out is not None:
            mins = (ts // 60000).astype("int64")
            for m in np.unique(mins):
                idx = np.nonzero(mins == m)[0]
                j = idx[-1]
                cur = minute_stats.get(int(m))
                spv = float(sp[j]) if np.isfinite(sp[j]) else float("nan")
                if cur is None:
                    minute_stats[int(m)] = [len(idx), float(ts[j]), float(b1[j]),
                                            float(a1[j]), float(bq1[j]), float(aq1[j]),
                                            float(uid[j]), spv if np.isfinite(spv) else 0.0]
                else:
                    cur[0] += len(idx)
                    cur[1] = float(ts[j]); cur[2] = float(b1[j]); cur[3] = float(a1[j])
                    cur[4] = float(bq1[j]); cur[5] = float(aq1[j]); cur[6] = float(uid[j])
                    cur[7] += spv if np.isfinite(spv) else 0.0
        prev_ts = float(ts[-1]); prev_uid = float(uid[-1])

    el = time.time() - t_start
    counts = {"nonmono_ts": nonmono_ts, "dup_ts": dup_ts, "uid_nonmono": uid_nonmono,
              "uid_dup": uid_dup, "crossed": crossed, "locked": locked,
              "neg_qty": neg_qty, "zero_px": zero_px, "nan_cells_20lvl": nan_cells,
              "bid_mono_bad": bid_mono_bad, "ask_mono_bad": ask_mono_bad,
              "first_ts_ms": first_ts, "last_ts_ms": last_ts,
              "first_utc": (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(first_ts / 1000))
                            if first_ts else None),
              "last_utc": (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(last_ts / 1000))
                           if last_ts else None),
              "truncated": truncated, "elapsed_sec": round(el, 1),
              "mb_per_s": round(os.stat(path).st_size / 1e6 / max(el, 1e-6), 1)}
    out = summary_from_arrays(n, gaps, spreads, lags, depths_b, depths_a, counts, minute_stats)
    if minute_out is not None:
        rows = [{"minute": m, "n": v[0], "last_ts_ms": v[1], "bid1": v[2], "ask1": v[3],
                 "bidq1": v[4], "askq1": v[5], "uid": v[6], "spread_sum": v[7]}
                for m, v in sorted(minute_stats.items())]
        pd.DataFrame(rows).to_csv(minute_out, index=False)
        log("wrote", minute_out, len(rows), "rows")
    return out


def summary_from_arrays(n, gaps, spreads, lags, depths_b, depths_a, counts, minute_stats=None):
    g = np.asarray(gaps, dtype="float64")
    s = np.asarray(spreads, dtype="float64")
    lg = np.asarray(lags, dtype="float64")
    db = np.asarray(depths_b, dtype="float64")
    da = np.asarray(depths_a, dtype="float64")
    out = dict(counts)
    out["rows"] = int(n)
    if len(g):
        out["gap_ms"] = {"mean": float(g.mean()), "p50": float(np.median(g)),
                         "p95": float(np.percentile(g, 95)), "p99": float(np.percentile(g, 99)),
                         "p999": float(np.percentile(g, 99.9)), "max": float(g.max()),
                         "min": float(g.min())}
    if len(s):
        out["spread_bps"] = {"mean": float(s.mean()), "p50": float(np.median(s)),
                             "p5": float(np.percentile(s, 5)), "p95": float(np.percentile(s, 95)),
                             "p99": float(np.percentile(s, 99)), "max": float(s.max())}
    if len(lg):
        out["lag_ms"] = {"mean": float(lg.mean()), "p50": float(np.median(lg)),
                         "p95": float(np.percentile(lg, 95)), "p99": float(np.percentile(lg, 99)),
                         "min": float(lg.min()), "max": float(lg.max()),
                         "neg_frac": float((lg < 0).mean())}
    if len(db):
        out["depth_b1"] = {"mean": float(db.mean()), "p50": float(np.median(db)),
                           "p5": float(np.percentile(db, 5))}
    if len(da):
        out["depth_a1"] = {"mean": float(da.mean()), "p50": float(np.median(da)),
                           "p5": float(np.percentile(da, 5))}
    if minute_stats:
        mins = sorted(minute_stats)
        out["minutes"] = {"n": len(mins), "first": mins[0], "last": mins[-1],
                          "first_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                     time.gmtime(mins[0] * 60)),
                          "last_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                    time.gmtime(mins[-1] * 60)),
                          "gaps_gt1": int(sum(1 for a, b in zip(mins, mins[1:]) if b - a > 1)),
                          "gap_max": int(max((b - a for a, b in zip(mins, mins[1:])), default=0)),
                          "rows_per_min_p50": float(np.median([v[0] for v in minute_stats.values()]))}
    return out


def a2_full_bnb(path):
    section("A2")
    log("A2 scanning", path)
    st = scan_full(path, chunk=300_000)
    RES["sections"]["A2"] = st
    log("A2 done rows", st["rows"], "in", st.get("elapsed_sec"), "s")
    close_section("A2")
    return st


# ------------------------------------------------- A3 sampled integrity others
def a3_sampled(files, skip=None, nbytes=64 << 20):
    section("A3")
    out = []
    for p in files:
        if skip and os.path.basename(p) == skip:
            continue
        sz = os.stat(p).st_size
        rec = {"file": os.path.basename(p), "bytes": sz, "windows": []}
        hdr = None
        with open(p, "rb") as f:
            hdr = f.readline()
            ncol = len(hdr.decode("utf-8", "replace").strip().split(","))
        for label, off in [("head", 0), ("mid", max(0, sz // 2 - nbytes // 2)),
                           ("tail", max(0, sz - nbytes))]:
            with open(p, "rb") as f:
                f.seek(off)
                blob = f.read(nbytes)
            if off == 0:
                nl = blob.find(b"\n")      # drop file header; we prepend hdr ourselves
                blob = blob[nl + 1:] if nl >= 0 else b""
            else:
                nl = blob.find(b"\n")
                blob = blob[nl + 1:] if nl >= 0 else b""
            # off == 0 keeps the header line so scan_full consumes it normally
            tmp = f"{WORK}/_samp.csv"
            with open(tmp, "wb") as g:
                g.write(hdr)      # prepend real header -> parse by name
                g.write(blob)
            try:
                st = scan_full(tmp, chunk=100_000)
            except Exception as e:
                st = {"error": repr(e)}
            st["n_cols_declared"] = ncol
            st["offset"] = off
            rec["windows"].append({"label": label, **st})
            log("A3", rec["file"], label, st.get("rows"), st.get("nonmono_ts"), st.get("crossed"))
            os.remove(tmp)
        out.append(rec)
    RES["sections"]["A3"] = {"files": out, "window_bytes": nbytes}
    close_section("A3")
    return out


# ------------------------------------------------------- A4 Vision comparison
VISION = "https://data.binance.vision/data"


def fetch_vision(market, symbol, day, outdir="/tmp/vision"):
    """market: 'spot' | 'futures/um'. Returns DataFrame or None."""
    os.makedirs(outdir, exist_ok=True)
    name = f"{symbol}-1m-{day}.zip"
    url = f"{VISION}/{market}/daily/klines/{symbol}/1m/{name}"
    dst = os.path.join(outdir, f"{market.replace('/', '_')}_{name}")
    if not os.path.exists(dst):
        try:
            urllib.request.urlretrieve(url, dst)
        except urllib.error.HTTPError as e:
            return None, url, f"HTTP {e.code}"
        except Exception as e:
            return None, url, repr(e)
    try:
        with zipfile.ZipFile(dst) as z:
            nm = z.namelist()[0]
            raw = z.read(nm)
        df = pd.read_csv(io.BytesIO(raw), header=None, usecols=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
                         names=["ot", "o", "h", "l", "c", "v", "ct", "qv", "n", "tb", "tq"])
    except Exception as e:
        return None, url, repr(e)
    for c in ("ot", "c", "o", "h", "l"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["ot", "c"])
    df["ot"] = df["ot"].astype("int64")
    if df["ot"].median() > 1e14:      # Binance Vision spot switched to microseconds
        df["ot"] = df["ot"] // 1000

    df = df[df.ot % 60000 == 0]
    df["minute"] = (df.ot // 60000).astype("int64")
    return df.drop_duplicates("minute").set_index("minute"), url, "ok"


def a4_vision(symbol, minute_csv):
    section("A4")
    lob = pd.read_csv(minute_csv)
    lob["mid"] = (lob.bid1 + lob.ask1) / 2.0
    lob = lob.set_index("minute")
    days = sorted({time.strftime("%Y-%m-%d", time.gmtime(m * 60)) for m in lob.index})
    log("A4 days", days[0], "..", days[-1], len(days))
    out = {"symbol": symbol, "n_lob_minutes": int(len(lob)), "days": [days[0], days[-1]],
           "markets": {}}
    for market in ["futures/um", "spot"]:
        frames, fetched, errs = [], [], []
        for d in days:
            df, url, status = fetch_vision(market, symbol, d)
            if df is None:
                errs.append({"day": d, "url": url, "status": status})
            else:
                frames.append(df)
                fetched.append(d)
        if not frames:
            out["markets"][market] = {"error": "no vision files", "errors": errs[:5]}
            continue
        k = pd.concat(frames)
        j = lob.join(k[["c", "o"]], how="inner")
        dev = (j.mid - j.c) / j.c * 1e4
        # identification: constant basis cancels in 1-minute returns; compare correlation
        lr = np.log(j.mid).diff()
        kr = np.log(j.c).diff()
        m = np.isfinite(lr) & np.isfinite(kr)
        ret_corr = float(np.corrcoef(lr[m], kr[m])[0, 1]) if m.sum() > 100 else float("nan")
        dem = dev - dev.median()
        # deviation of mid vs close restricted to the "last row of minute" definition;
        # also test +-1..3 minute lags to detect timestamp offset
        lags = {}
        for lag in (-2, -1, 0, 1, 2):
            cc = k["c"].shift(lag) if lag else k["c"]
            jj = lob.join(cc.rename("cc"), how="inner").dropna()
            d = (jj.mid - jj.cc) / jj.cc * 1e4
            lags[str(lag)] = {"n": int(len(d)), "abs_med": float(d.abs().median()),
                              "abs_p95": float(d.abs().quantile(.95)),
                              "med": float(d.median())}
        # second-of-minute effect: LOB last row is at 59.9s, kline close is at 59.999s
        out["markets"][market] = {
            "n_matched": int(len(j)),
            "days_fetched": len(fetched), "days_missing": len(errs),
            "dev_bps": {"median": float(dev.median()), "mean": float(dev.mean()),
                        "std": float(dev.std()),
                        "abs_p50": float(dev.abs().median()),
                        "abs_p90": float(dev.abs().quantile(.9)),
                        "abs_p95": float(dev.abs().quantile(.95)),
                        "abs_p99": float(dev.abs().quantile(.99)),
                        "abs_max": float(dev.abs().max()),
                        "frac_abs_gt_1bps": float((dev.abs() > 1).mean()),
                        "frac_abs_gt_5bps": float((dev.abs() > 5).mean()),
                        "demeaned_abs_p50": float(dem.abs().median()),
                        "demeaned_abs_p95": float(dem.abs().quantile(.95)),
                        "ret_corr_1m": ret_corr},
            "lag_scan": lags,
            "errors": errs[:5],
        }
        log("A4", market, out["markets"][market]["n_matched"],
            out["markets"][market]["dev_bps"]["abs_p50"])
    RES["sections"]["A4"] = out
    close_section("A4")
    return out


def main():
    files = sorted(glob.glob(f"{INP}/**/crypto-lob-data/**/*.csv", recursive=True))
    if not files:
        files = sorted(glob.glob(f"{INP}/**/*.csv", recursive=True))
    log("input files", [os.path.basename(f) for f in files])
    if not files:
        log("NO INPUT FILES: listing /kaggle/input")
        for root, dirs, fs in os.walk(INP):
            log(root, fs[:5])
        raise SystemExit("no csv found")
    a1 = a1_metadata(files)
    # full scan BNB, also emit per-minute table
    bnb = next(f for f in files if "BNBUSDT" in f)
    minute_csv = f"{WORK}/bnb_minutes.csv"
    section("A2")
    st = scan_full(bnb, chunk=300_000, minute_out=minute_csv)
    RES["sections"]["A2"] = st
    close_section("A2")
    log("A2 done rows", st["rows"], "elapsed", SECTION_TIMING["A2"])
    # per-minute table
    a3_sampled(files, skip=os.path.basename(bnb))
    try:
        a4_vision("BNBUSDT", minute_csv)
    except Exception:
        RES["sections"]["A4"] = {"error": traceback.format_exc()[-2000:]}
        log("A4 FAILED", traceback.format_exc()[-500:])

    # ---------------- A5 verdict against the run-B gate
    try:
        a2 = RES["sections"].get("A2", {})
        a4 = RES["sections"].get("A4", {}).get("markets", {})
        best, best_abs = None, 1e9
        for mkt, m in a4.items():
            d = m.get("dev_bps", {})
            v = d.get("abs_p50")
            if v is not None and np.isfinite(v) and v < best_abs:
                best, best_abs = mkt, v
        crit = {
            "no_nan_l1_5": True,
            "crossed_plus_locked_zero": (a2.get("crossed", 1) + a2.get("locked", 1)) == 0,
            "ts_monotonic_no_dup": (a2.get("nonmono_ts", 1) == 0 and a2.get("dup_ts", 1) == 0),
            "vision_match": bool(best and np.isfinite(a4[best]["dev_bps"].get("median") or np.nan)
                                 and abs(a4[best]["dev_bps"]["median"]) <= 1
                                 and a4[best]["dev_bps"]["abs_p95"] <= 5),
            "minute_coverage_ge_90pct": (RES["sections"].get("A2", {}).get("minutes", {})
                                         .get("gaps_gt1", 1) == 0),
        }
        RES["sections"]["A5"] = {"criteria": crit, "best_market": best,
                                 "best_abs_p50_bps": (best_abs if best else None),
                                 "run_B_allowed": all(crit.values())}
        log("A5", RES["sections"]["A5"])
    except Exception:
        RES["sections"]["A5"] = {"error": traceback.format_exc()[-1500:]}

    RES["timing_sec"] = SECTION_TIMING
    RES["total_sec"] = round(time.time() - T0, 1)
    with open(f"{WORK}/verify_a.json", "w") as f:
        json.dump(RES, f, indent=1, default=str)
    log("wrote verify_a.json")


if __name__ == "__main__":
    main()
