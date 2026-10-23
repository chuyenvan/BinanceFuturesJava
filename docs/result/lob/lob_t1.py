#!/usr/bin/env python3
print("BOOT lob-t1 v2", flush=True)
"""Phase B: LOB T1 signal test on Kaggle (BNBUSDT, 100-level book).

Pre-registered in docs/prereg/PREREG_LOB_T1.md (commit hash printed at runtime
from an env var KERNEL_SHA; the numbers below are frozen constants).

Pass 1: stream the CSV once, build a 1-second grid of book features.
Pass 2: in-memory evaluation, 60 % discovery / 40 % test split, out-of-sample
IC / R² / decile returns vs cost, regime split, validation checks.
"""
import glob
import json
import os
import time

import warnings

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

T0 = time.time()

SYMBOL = "BNBUSDT"
MARKET = "spot"                    # Phase A: book = spot BNBUSDT (corr 0.9989 vs spot klines)
PREREG_COMMIT = "7ff68af57f6cfd761da623bc29d4721022610dee"
SPLIT = 0.60                       # first 60 % of seconds = discovery
HORIZONS_1S = [1, 10, 60]          # sampled on the 1-s grid
HORIZONS_60S = [300, 900]          # sampled on the 60-s grid
FEE_TAKER_BPS = 5.0                # per side
FEE_MAKER_BPS = 2.0                # per side
LEVELS = 5
WORK = "/kaggle/working"
INP = "/kaggle/input"
CHUNK = 250_000

SIGNALS = ["imb1", "imb5", "ofi1", "micro_bps", "slope_imb", "depth_bps5"]


def log(*a):
    print(f"[{time.time()-T0:8.1f}s]", *a, flush=True)


def find_csv():
    pats = [f"{INP}/**/{SYMBOL}.csv"]
    for p in pats:
        f = sorted(glob.glob(p, recursive=True))
        if f:
            return f[0]
    raise SystemExit("csv not found")


COLS = (["event_ts_ms", "update_id"]
        + [f"bid_px_{i}" for i in range(1, LEVELS + 1)]
        + [f"bid_qty_{i}" for i in range(1, LEVELS + 1)]
        + [f"ask_px_{i}" for i in range(1, LEVELS + 1)]
        + [f"ask_qty_{i}" for i in range(1, LEVELS + 1)])
DT = {c: "float64" for c in COLS}


def pass1(path):
    """One streaming pass -> per-second grid arrays."""
    ts_l, uid_l = [], []
    b1_l, a1_l, bq1_l, aq1_l = [], [], [], []
    sbq_l, saq_l, db_l, da_l = [], [], [], []
    nrows = 0
    with open(path, "rb") as _fh:
        _first = _fh.readline()
    if not _first.startswith(b"event_ts_ms"):
        raise SystemExit("expected header row in " + path)
    # parse BY NAME (the file has 403 columns; positional mapping would misalign)
    reader = pd.read_csv(path, header=0, usecols=COLS, chunksize=CHUNK,
                         on_bad_lines="warn", dtype=DT, low_memory=False)
    for df in reader:
        n = len(df)
        if n == 0:
            continue
        nrows += n
        ts = df["event_ts_ms"].to_numpy()
        b1 = df["bid_px_1"].to_numpy(); a1 = df["ask_px_1"].to_numpy()
        bq1 = df["bid_qty_1"].to_numpy(); aq1 = df["ask_qty_1"].to_numpy()
        bp = df[[f"bid_px_{i}" for i in range(1, LEVELS + 1)]].to_numpy()
        bq = df[[f"bid_qty_{i}" for i in range(1, LEVELS + 1)]].to_numpy()
        ap = df[[f"ask_px_{i}" for i in range(1, LEVELS + 1)]].to_numpy()
        aq = df[[f"ask_qty_{i}" for i in range(1, LEVELS + 1)]].to_numpy()
        mid = (b1 + a1) / 2.0
        with np.errstate(invalid="ignore", divide="ignore"):
            db = np.nansum(bq * (mid[:, None] - bp) / mid[:, None], axis=1) * 1e4
            da = np.nansum(aq * (ap - mid[:, None]) / mid[:, None], axis=1) * 1e4
        ts_l.append(ts); uid_l.append(df["update_id"].to_numpy())
        b1_l.append(b1); a1_l.append(a1); bq1_l.append(bq1); aq1_l.append(aq1)
        sbq_l.append(np.nansum(bq, axis=1)); saq_l.append(np.nansum(aq, axis=1))
        db_l.append(db); da_l.append(da)
        if nrows % 2_000_000 < CHUNK:
            log("pass1 rows", nrows, f"{os.path.getsize(path)/1e9:.2f} GB file")
    log("pass1 rows total", nrows)

    ts = np.concatenate(ts_l); uid = np.concatenate(uid_l)
    b1 = np.concatenate(b1_l); a1 = np.concatenate(a1_l)
    bq1 = np.concatenate(bq1_l); aq1 = np.concatenate(aq1_l)
    sbq = np.concatenate(sbq_l); saq = np.concatenate(saq_l)
    db = np.concatenate(db_l); da = np.concatenate(da_l)
    del ts_l, uid_l, b1_l, a1_l, bq1_l, aq1_l, sbq_l, saq_l, db_l, da_l

    # integrity summary of the columns used by B
    meta = {
        "rows": int(nrows),
        "first_ms": float(ts[0]), "last_ms": float(ts[-1]),
        "nan_b1": int(np.isnan(b1).sum()), "nan_q1": int(np.isnan(bq1).sum()),
        "crossed": int((b1 > a1).sum()), "locked": int((b1 == a1).sum()),
        "nonmono_ts": int((np.diff(ts) < 0).sum()),
        "dup_ts": int((np.diff(ts) == 0).sum()),
    }

    mid = (b1 + a1) / 2.0
    with np.errstate(invalid="ignore", divide="ignore"):
        imb1 = (bq1 - aq1) / (bq1 + aq1)
        imb5 = (sbq - saq) / (sbq + saq)
        micro = (b1 * aq1 + a1 * bq1) / (aq1 + bq1)
        micro_bps = (micro - mid) / mid * 1e4
        slope_imb = (db - da) / (db + da)
        depth_bps5 = db + da
        # OFI (Cont, Kukanov & Stoikov 2014), level 1
        pb1 = np.concatenate([[b1[0]], b1[:-1]]); pa1 = np.concatenate([[a1[0]], a1[:-1]])
        pbq = np.concatenate([[bq1[0]], bq1[:-1]]); paq = np.concatenate([[aq1[0]], aq1[:-1]])
        ofi_e = (np.where(b1 >= pb1, bq1, 0.0) - np.where(b1 <= pb1, pbq, 0.0)
                 - np.where(a1 <= pa1, aq1, 0.0) + np.where(a1 >= pa1, paq, 0.0))
        ofi_e[0] = 0.0

    sec = (ts // 1000).astype("int64")
    frame = pd.DataFrame({
        "sec": sec, "mid": mid, "b1": b1, "a1": a1, "bq1": bq1, "aq1": aq1,
        "imb1": imb1, "imb5": imb5, "micro_bps": micro_bps,
        "slope_imb": slope_imb, "depth_bps5": depth_bps5, "ofi_e": ofi_e,
        "lvl1": bq1 + aq1,
    })
    g = frame.groupby("sec", sort=True)
    agg = g.agg(last_mid=("mid", "last"), imb1=("imb1", "last"), imb5=("imb5", "last"),
                micro_bps=("micro_bps", "last"), slope_imb=("slope_imb", "last"),
                depth_bps5=("depth_bps5", "last"), lvl1=("lvl1", "last"),
                ofi_sum=("ofi_e", "sum"), b1=("b1", "last"), a1=("a1", "last"),
                bq1=("bq1", "last"), aq1=("aq1", "last"), nev=("mid", "size"))
    agg["ofi1"] = agg["ofi_sum"] / agg["lvl1"].replace(0, np.nan)
    log("seconds observed", len(agg))
    return agg, meta, int(sec[0]), int(sec[-1])


def build_grid(agg, s0, s1):
    idx = np.arange(s0, s1 + 1, dtype="int64")
    out = pd.DataFrame(index=idx)
    out.index.name = "sec"
    out = out.join(agg, how="left")
    out["mid"] = out["last_mid"].ffill()
    for c in SIGNALS:
        out[c] = out[c].ffill()
    out["obs"] = out["last_mid"].notna()
    out["spread_bps"] = (out.a1 - out.b1) / out.mid * 1e4
    out["nev"] = out["nev"].fillna(0)
    return out


def fwd_ret(mid, h):
    r = np.full(len(mid), np.nan)
    r[:-h] = (mid[h:] - mid[:-h]) / mid[:-h] * 1e4
    return r


def nw_tstat(x, y, lag):
    """t-stat of Pearson corr with Newey-West effective sample size."""
    m = np.isfinite(x) & np.isfinite(y)
    x = x[m]; y = y[m]
    n = len(x)
    if n < 50:
        return float("nan"), float("nan"), n
    xs = (x - x.mean()) / (x.std() + 1e-12)
    ys = (y - y.mean()) / (y.std() + 1e-12)
    r = float(np.mean(xs * ys))
    z = xs * ys
    zc = z - z.mean()
    den = np.dot(zc, zc)
    s = 0.0
    for k in range(1, min(lag, n // 10) + 1):
        rho = float(np.dot(zc[:-k], zc[k:]) / den) if den > 0 else 0.0
        s += (1 - k / (lag + 1)) * rho
    neff = n / max(1e-9, (1 + 2 * s))
    neff = min(max(neff, 10), n)
    t = r * np.sqrt(neff - 2) / np.sqrt(max(1e-12, 1 - r * r))
    return r, float(t), n


def evaluate(gr, h, signals, disc_mask, test_mask):
    """IC (Spearman + Pearson/NW), OLS R^2 out-of-sample, decile returns."""
    r = fwd_ret(gr["mid"].to_numpy(), h)
    res = {}
    for s in signals:
        x = gr[s].to_numpy()
        d = disc_mask & np.isfinite(r) & np.isfinite(x)
        t = test_mask & np.isfinite(r) & np.isfinite(x)
        if d.sum() < 1000 or t.sum() < 500:
            res[s] = {"skip": "insufficient samples", "n_disc": int(d.sum()), "n_test": int(t.sum())}
            continue
        ic_d = stats.spearmanr(x[d], r[d]).statistic
        ic_t = stats.spearmanr(x[t], r[t]).statistic
        pear, tstat, n_t = nw_tstat(x[t], r[t], lag=max(1, h))
        # OLS fit on discovery only -> out-of-sample R^2 on test
        xd = x[d]; rd = r[d]
        beta = float(np.cov(xd, rd)[0, 1] / (np.var(xd) + 1e-18))
        alpha = float(rd.mean() - beta * xd.mean())
        pred = alpha + beta * x[t]
        ss_res = float(np.sum((r[t] - pred) ** 2))
        ss_tot = float(np.sum((r[t] - r[t].mean()) ** 2))
        r2_oos = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
        # decile edges from discovery only
        edges = np.nanquantile(xd, np.linspace(0, 1, 11))
        edges = np.unique(edges)
        if len(edges) < 3:
            res[s] = {"skip": "degenerate signal"}
            continue
        bins = np.clip(np.digitize(x[t], edges[1:-1]), 0, len(edges) - 2)
        rt = r[t]
        means = [float(np.nanmean(rt[bins == b])) if (bins == b).sum() > 20 else float("nan")
                 for b in range(len(edges) - 1)]
        counts = [int((bins == b).sum()) for b in range(len(edges) - 1)]
        spread_bps = means[-1] - means[0] if np.isfinite(means[-1] + means[0]) else float("nan")
        direction = 1.0 if ic_d >= 0 else -1.0
        strat = direction * spread_bps
        res[s] = {
            "n_disc": int(d.sum()), "n_test": int(t.sum()),
            "ic_disc": float(ic_d), "ic_test": float(ic_t),
            "pearson_test": pear, "nw_t": tstat, "nw_lag": max(1, h),
            "r2_oos": float(r2_oos), "beta": beta,
            "decile_means_bps": means, "decile_counts": counts,
            "spread_top_minus_bottom_bps": float(spread_bps),
            "direction_from_disc": direction,
            "strat_gross_bps": float(strat),
            "strat_net_taker_bps": float(strat - 2 * FEE_TAKER_BPS),
            "strat_net_maker_bps": float(strat - 2 * FEE_MAKER_BPS),
            "turnover_per_trade": 2,
        }
    return res, r


def main():
    path = find_csv()
    log("input", path, f"{os.path.getsize(path)/1e9:.2f} GB")
    agg, meta, s0, s1 = pass1(path)
    gr = build_grid(agg, s0, s1)
    n = len(gr)
    i_split = int(n * SPLIT)
    disc_mask = np.zeros(n, bool); disc_mask[:i_split] = True
    test_mask = np.zeros(n, bool); test_mask[i_split:] = True
    sec = gr.index.to_numpy()

    # regime variables (strictly backward looking)
    r1m = pd.Series(gr["mid"]).pct_change(60) * 1e4
    vol15 = r1m.rolling(15 * 60).std()
    vol15_med = float(np.nanmedian(vol15[disc_mask[:len(vol15)]]))
    hi_vol = (vol15 > vol15_med).to_numpy()
    absr1m = np.abs(r1m.to_numpy())
    crash_thr = float(np.nanquantile(absr1m[disc_mask], 0.999))
    crash = absr1m >= crash_thr

    out = {
        "prereg_commit": PREREG_COMMIT, "kernel_sha": os.environ.get("KERNEL_SHA", "unset"),
        "symbol": SYMBOL, "market": MARKET, "levels": LEVELS,
        "input_gb": round(os.path.getsize(path) / 1e9, 3),
        "pass1_meta": meta,
        "grid": {"n_seconds": int(n), "first_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                                 time.gmtime(sec[0])),
                 "last_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(sec[-1])),
                 "obs_frac": float(gr["obs"].mean()),
                 "split_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(sec[i_split])),
                 "n_seconds_disc": int(disc_mask.sum()), "n_seconds_test": int(test_mask.sum())},
        "costs_bps_roundtrip": {"taker": 2 * FEE_TAKER_BPS, "maker": 2 * FEE_MAKER_BPS},
        "spread_bps": {"p50": float(np.nanmedian(gr["spread_bps"])),
                       "p10": float(np.nanpercentile(gr["spread_bps"], 10)),
                       "p90": float(np.nanpercentile(gr["spread_bps"], 90))},
        "results": {}, "regime": {},
    }

    for h in HORIZONS_1S:
        res, r = evaluate(gr, h, SIGNALS, disc_mask, test_mask)
        out["results"][f"{h}s"] = res
        log("done horizon", h, "s")
    # 60-s grid for long horizons
    gr60 = gr.iloc[::60]
    disc60 = disc_mask[::60]; test60 = test_mask[::60]
    for h_min in HORIZONS_60S:
        h = h_min // 60
        res, r = evaluate(gr60, h, SIGNALS, disc60, test60)
        out["results"][f"{h_min}s"] = res
        log("done horizon", h_min, "s")

    # regime split on the 10 s horizon (primary)
    h = 10
    r10 = fwd_ret(gr["mid"].to_numpy(), h)
    for name, mask in [("vol_hi", hi_vol), ("vol_lo", ~hi_vol)]:
        m = test_mask & mask
        out["regime"][name] = {}
        for s in SIGNALS:
            x = gr[s].to_numpy()
            ok = m & np.isfinite(r10) & np.isfinite(x)
            if ok.sum() > 500:
                out["regime"][name][s] = {"ic": float(stats.spearmanr(x[ok], r10[ok]).statistic),
                                          "n": int(ok.sum())}
        out["regime"][name]["_n_seconds"] = int(m.sum())
    out["regime"]["crash"] = {"threshold_abs_1m_bps": crash_thr,
                              "frac_test": float(crash[test_mask].mean())}
    for s in SIGNALS:
        x = gr[s].to_numpy()
        ok = test_mask & crash & np.isfinite(r10) & np.isfinite(x)
        if ok.sum() > 100:
            out["regime"]["crash"][s] = {"ic": float(stats.spearmanr(x[ok], r10[ok]).statistic),
                                         "n": int(ok.sum())}

    # ---------------- validation checks
    v = {}
    rng = np.random.default_rng(20261023)
    x = gr["imb1"].to_numpy(); ok = test_mask & np.isfinite(r10) & np.isfinite(x)
    v["V1_placebo_shuffled_returns"] = {
        "ic_observed": float(stats.spearmanr(x[ok], r10[ok]).statistic),
    }
    sh = x.copy(); idxs = np.nonzero(ok)[0]
    day = (sec // 86400)
    ics = []
    for rep in range(3):
        sh2 = sh.copy(); vals = sh2[idxs]
        perm = rng.permutation(len(vals))
        # shuffle returns instead of the signal: preserves signal autocorrelation,
        # destroys any genuine contemporaneous link
        rr = r10[idxs][perm]
        ics.append(float(stats.spearmanr(vals, rr).statistic))
    v["V1_placebo_shuffled_returns"]["ic_shuffled_returns"] = ics
    v["V1_placebo_shuffled_returns"]["max_abs"] = float(np.max(np.abs(ics)))

    v["V2_random_signal"] = {}
    rnd_ics = []
    for rep in range(10):
        z = rng.standard_normal(ok.sum())
        rnd_ics.append(float(stats.spearmanr(z, r10[ok]).statistic))
    v["V2_random_signal"] = {"mean": float(np.mean(rnd_ics)), "sd": float(np.std(rnd_ics)),
                             "theoretical_sd": float(1 / np.sqrt(ok.sum())),
                             "n": int(ok.sum())}
    v["V3_daywise_ic_imb1_h10"] = [
        {"day_utc": time.strftime("%Y-%m-%d", time.gmtime(d * 86400)),
         "ic": float(stats.spearmanr(x[ok & (day == d)], r10[ok & (day == d)]).statistic),
         "n": int((ok & (day == d)).sum())}
        for d in np.unique(day[ok])]
    v["V4_cost_arithmetic"] = {
        "check": abs((100.0 - 2 * FEE_TAKER_BPS) - 90.0) < 1e-9
                 and abs((100.0 - 2 * FEE_MAKER_BPS) - 96.0) < 1e-9}
    q = np.zeros(len(gr), int)
    q[test_mask] = np.minimum(3, ((np.arange(test_mask.sum()) * 4) // test_mask.sum()))
    v["V7_quarter_stability_imb1_h10"] = [
        {"quarter": int(k),
         "ic": float(stats.spearmanr(x[ok & (q == k)], r10[ok & (q == k)]).statistic),
         "n": int((ok & (q == k)).sum())}
        for k in range(4) if (ok & (q == k)).sum() > 500]
    v["V5_counts"] = {"n_1s": int(len(gr)), "n_60s": int(len(gr60)),
                      "expected_1s": int(gr.index[-1] - gr.index[0] + 1)}
    # V6: pure-python csv parse of a slice vs pandas parse of the same rows
    # (checks column alignment / header handling, not just the algebra)
    import csv as _csv
    b1s, a1s, bqs, aqs = [], [], [], []
    with open(path, newline="") as fh2:
        rd = _csv.reader(fh2)
        hdr = next(rd)
        i_b1, i_a1 = hdr.index("bid_px_1"), hdr.index("ask_px_1")
        i_bq, i_aq = hdr.index("bid_qty_1"), hdr.index("ask_qty_1")
        for i, row in enumerate(rd):
            # i is 0-based over data lines = file line i+1; pandas keeps line 0 as header
            # and skips lines 1..9999, so its first data row is file line 10000 = i 9999
            if i < 9_999:
                continue
            if i >= 11_999:
                break
            b1s.append(float(row[i_b1])); a1s.append(float(row[i_a1]))
            bqs.append(float(row[i_bq])); aqs.append(float(row[i_aq]))
    b1s = np.array(b1s); a1s = np.array(a1s); bqs = np.array(bqs); aqs = np.array(aqs)
    d = pd.read_csv(path, skiprows=range(1, 10_000), nrows=2000, header=0,
                    usecols=["bid_px_1", "ask_px_1", "bid_qty_1", "ask_qty_1"])
    imb_loop = (bqs - aqs) / (bqs + aqs)
    micro_loop = (b1s * aqs + a1s * bqs) / (aqs + bqs)
    imb_vec = ((d["bid_qty_1"] - d["ask_qty_1"]) / (d["bid_qty_1"] + d["ask_qty_1"])).to_numpy()
    micro_vec = ((d["bid_px_1"] * d["ask_qty_1"] + d["ask_px_1"] * d["bid_qty_1"])
                 / (d["bid_qty_1"] + d["ask_qty_1"])).to_numpy()
    v["V6_recompute"] = {"max_abs_diff_imb": float(np.nanmax(np.abs(imb_loop - imb_vec))),
                         "max_abs_diff_micro": float(np.nanmax(np.abs(micro_loop - micro_vec))),
                         "n": int(len(d))}
    out["validation"] = v

    # extra diagnostics for the report
    out["distribution"] = {
        s: {"p1": float(np.nanpercentile(gr[s], 1)), "p50": float(np.nanmedian(gr[s])),
            "p99": float(np.nanpercentile(gr[s], 99)),
            "autocorr_1s": float(pd.Series(gr[s]).autocorr(1))}
        for s in SIGNALS}
    out["r1m_bps"] = {"sd": float(np.nanstd(r1m)), "p999_abs": crash_thr}
    out["timing_sec"] = round(time.time() - T0, 1)

    with open(f"{WORK}/t1.json", "w") as f:
        json.dump(out, f, indent=1)
    log("wrote t1.json", out["timing_sec"])


if __name__ == "__main__":
    main()
