#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PASS 2 — DIFF 33 FEATURE LIVE vs EXPORT DEV, **REGIME-MATCHED** (AUDIT-ONLY).

Pre-reg: docs/prereg/PREREG_FEATDIFF_PASS2.md (chot TRUOC). Chi DOC file local.
Khong cham host, khong chay Java/sim. 2026 = AUDIT-ONLY (holdout).

Phuong phap:
  P0  ghep cap CHINH XAC (ts,symbol) live<->export  -> shift_sd_paired, spearman  (khoa regime TU DONG)
  P1  rank/percentile TRONG cua so (khong so tuyet doi)             -> rank_shift
  P2  ghep cung decile volatility24H (pool chung)                   -> d_dec_sd, n_dec
  P3  ghep cung decile + cung hourOfDay                             -> d_hour_sd, n_hour
"""
import gzip, glob, os, sys, json
import numpy as np

FEATS = [
    "momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H",
    "momentumAcceleration", "trendStrengthETH", "trendConsistency",
    "volatility1M", "volatility15M", "volatility1H", "volatility24H", "volatilityTermStructure",
    "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength",
    "btcDominance", "rsi14", "volumeSpike", "distMA20",
    "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
    "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
    "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike",
]
assert len(FEATS) == 33


def load_live():
    rows = []
    files = sorted(glob.glob("/home/ubuntu/shadow_c3/app/feat_dump/*.csv.gz")) + \
            sorted(glob.glob("/tmp/mdval_242/*.csv.gz"))
    for f in files:
        try:
            fh = gzip.open(f, "rt")
            hdr = fh.readline().strip().split(",")
            idx = {n: i for i, n in enumerate(hdr)}
            while True:
                try:
                    ln = fh.readline()
                except Exception:
                    break
                if not ln:
                    break
                p = ln.rstrip("\n").split(",")
                if len(p) < len(hdr) or p[idx["symbol"]] != "BTCUSDT":
                    continue
                ms = int(float(p[idx["ts"]]))
                if ms > 10**14:
                    ms //= 1000
                elif ms < 10**11:
                    ms *= 1000
                rec = {"ts": ms, "min": ms // 60000 * 60000}
                for n in FEATS:
                    try:
                        rec[n] = float(p[idx[n]])
                    except Exception:
                        rec[n] = np.nan
                try:
                    rec["p15_out"] = float(p[idx["p15_out"]])
                except Exception:
                    rec["p15_out"] = np.nan
                rows.append(rec)
            fh.close()
        except Exception as e:
            print("  warn live", os.path.basename(f), str(e)[:60])
    return rows


def load_died():
    txt = open("/home/ubuntu/shadow_c3/app/config.properties").read()
    ln = [l for l in txt.splitlines() if l.startswith("DIED_SYMBOLS=")][0]
    out = set()
    for s in ln.split("=", 1)[1].split(","):
        s = s.strip()
        if s:
            out.add(s if "USDT" in s else s + "USDT")
    return out


def load_dev(path):
    fh = gzip.open(path, "rt")
    hdr = fh.readline().strip().split(",")
    idx = {n: i for i, n in enumerate(hdr)}
    cols = {n: [] for n in FEATS}
    mdsrc, mins = [], []
    for ln in fh:
        p = ln.rstrip("\n").split(",")
        if len(p) < len(hdr):
            continue
        for n in FEATS:
            cols[n].append(float(p[idx[n]]))
        mdsrc.append(int(p[idx["md_src"]]))
        mins.append(int(p[idx["ts"]]) // 60000 * 60000)
    fh.close()
    d = {n: np.asarray(v, dtype=np.float64) for n, v in cols.items()}
    d["md_src"] = np.asarray(mdsrc, dtype=np.int64)
    d["min"] = np.asarray(mins, dtype=np.int64)
    return d


def pct_within(x):
    x = np.asarray(x, dtype=np.float64)
    fin = np.isfinite(x)
    out = np.full(len(x), np.nan)
    n = int(fin.sum())
    if n < 2:
        return out
    r = np.argsort(np.argsort(x[fin]))
    out[fin] = r / (n - 1)
    return out


def ecdf_pos(sorted_dev, x):
    """Vi tri trung binh cua x trong CDF cua dev (0..1). 0.5 = trung tam dev."""
    x = np.asarray(x, dtype=np.float64)
    fin = np.isfinite(x)
    if len(sorted_dev) == 0 or fin.sum() == 0:
        return float('nan')
    pos = np.searchsorted(sorted_dev, x[fin], side="right") / len(sorted_dev)
    return float(np.mean(pos))


def mstats(lv, dv):
    lv = lv[np.isfinite(lv)]; dv = dv[np.isfinite(dv)]
    if len(lv) == 0 or len(dv) == 0:
        return None
    sd = float(np.std(dv))
    return dict(n_live=int(len(lv)), n_dev=int(len(dv)), mean_live=float(np.mean(lv)),
                mean_dev=float(np.mean(dv)), sd_dev=sd,
                d_sd=(abs(float(np.mean(lv)) - float(np.mean(dv))) / sd) if sd > 0 else float('nan'))


def matched(live_vals, dev_vals, live_key, dev_key, min_n=30):
    tot = 0.0; w = 0; nm = 0; used = 0; skip = 0
    for k in np.unique(live_key):
        lm = live_key == k
        dm = dev_key == k
        if dm.sum() < min_n:
            skip += 1; continue
        md = mstats(live_vals[lm], dev_vals[dm])
        if md is None or not np.isfinite(md["d_sd"]):
            skip += 1; continue
        nl = int(lm.sum())
        tot += md["d_sd"] * nl; w += nl; nm += nl; used += 1
    return (tot / w if w else float('nan')), nm, used, skip


def main():
    live = load_live()
    dev = load_dev("/home/ubuntu/claudedata/devexport_202609/devexport_20260701_20260928_FULL.csv.gz")
    mins_live = {r["min"] for r in live}
    print("live rows=%d distinct_min=%d | dev rows=%d" % (len(live), len(mins_live), len(dev["min"])))
    LV = {n: np.array([r[n] for r in live], dtype=np.float64) for n in FEATS}
    lv_min = np.array([r["min"] for r in live], dtype=np.int64)
    lv_hour = LV["hourOfDay"].astype(int)
    dv_hour = dev["hourOfDay"].astype(int)

    # --- P0: ghep cap CHINH XAC theo phut ---
    dev_of_min = {}
    for i, m in enumerate(dev["min"]):
        dev_of_min[int(m)] = i
    dmatch = np.array([dev_of_min.get(int(m), -1) for m in lv_min])
    okp = dmatch >= 0
    print("P0 pairs(ts exact)=%d / live=%d" % (int(okp.sum()), len(lv_min)))

    # --- regime decile ---
    pool = np.concatenate([LV["volatility24H"], dev["volatility24H"]])
    qs = np.quantile(pool[np.isfinite(pool)], np.linspace(0, 1, 11))
    qs[0] = -np.inf; qs[-1] = np.inf
    lv_bin = np.clip(np.digitize(LV["volatility24H"], qs[1:-1]), 0, 9)
    dv_bin = np.clip(np.digitize(dev["volatility24H"], qs[1:-1]), 0, 9)
    print("vol24H decile bounds:", np.round(qs[1:-1], 9).tolist())
    print("live rows/decile:", {int(b): int((lv_bin == b).sum()) for b in np.unique(lv_bin)})
    print("dev  rows/decile:", {int(b): int((dv_bin == b).sum()) for b in np.unique(dv_bin)})
    lv_key_d = lv_bin
    dv_key_d = dv_bin
    lv_key_h = lv_bin * 100 + lv_hour
    dv_key_h = dv_bin * 100 + dv_hour

    out = {}
    print("\n%-24s %8s %8s %8s %7s %8s %8s %8s %8s %7s %10s" %
          ("feature", "rankShfP", "cdfDev", "sd_pair", "sp_pair", "madP", "maxdP", "d_dec", "d_hour", "n_hour", "mean_live"))
    for n in FEATS:
        lv = LV[n].astype(np.float64); dv = dev[n].astype(np.float64)
        # P0 paired
        mad = mx = float('nan')
        if okp.sum() > 30:
            a = lv[okp]; b = dv[dmatch[okp]]
            fin = np.isfinite(a) & np.isfinite(b)
            a = a[fin]; b = b[fin]
            sd = float(np.std(b))
            sd_pair = (abs(float(np.mean(a)) - float(np.mean(b))) / sd) if sd > 0 else float('nan')
            sp = float(np.corrcoef(np.argsort(np.argsort(a)), np.argsort(np.argsort(b)))[0, 1]) if len(a) > 3 else float('nan')
            d = np.abs(a - b)
            mad = float(np.mean(d)); mx = float(np.max(d))
        else:
            sd_pair, sp = float('nan'), float('nan')
        # P1 rank theo 2 kieu (regime-normalized)
        dev_sorted = np.sort(dv[np.isfinite(dv)])
        cdf_dev = ecdf_pos(dev_sorted, lv)              # live nam o dau trong phan bo DEV
        if okp.sum() > 30:
            p_l = pct_within(lv)[okp]
            p_d_full = pct_within(dv)
            p_d = p_d_full[dmatch[okp]]
            fin2 = np.isfinite(p_l) & np.isfinite(p_d)
            rank_shift_paired = float(np.mean(p_l[fin2] - p_d[fin2]))
        else:
            rank_shift_paired = float('nan')
        # P2/P3
        d_dec, n_dec, u_dec, s_dec = matched(lv, dv, lv_key_d, dv_key_d)
        d_hr, n_hr, u_hr, s_hr = matched(lv, dv, lv_key_h, dv_key_h)
        # ti le scale
        ml = float(np.nanmean(lv)); mdv = float(np.nanmean(dv))
        ratio = (ml / mdv) if mdv not in (0.0,) and np.isfinite(mdv) else float('nan')
        out[n] = dict(rank_shift_paired=rank_shift_paired, cdf_dev=cdf_dev,
                      sd_paired=sd_pair, spear_paired=sp, mean_abs_delta_paired=mad, max_abs_delta_paired=mx,
                      d_dec=d_dec, n_dec=int(n_dec), n_dec_bins_used=u_dec, n_dec_bins_skip=s_dec,
                      d_hour=d_hr, n_hour=int(n_hr), n_hour_bins_used=u_hr, n_hour_bins_skip=s_hr,
                      mean_live=ml, mean_dev=mdv, ratio=ratio)
        print("%-24s %8.4f %8.4f %8.3f %7.3f %8.1e %8.1e %8.3f %8.3f %7d %10.3e" %
              (n, rank_shift_paired, cdf_dev, sd_pair, sp, mad, mx, d_dec, d_hr, n_hr, ml))
    with open("/tmp/pass2.json", "w") as fh:
        json.dump(out, fh, indent=1)
    print("\nwrote /tmp/pass2.json")


if __name__ == "__main__":
    main()
