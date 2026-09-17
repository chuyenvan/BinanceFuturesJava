"""PREREG_PUMPDUMP_OHLCV (commit df60077): do 4 detector "pump xong chuan bi dump" bang OHLCV 1m + OI.

MO TA (descriptive) — KHONG chay sim, KHONG sua .java, KHONG push.
Thuc hien DUNG docs/PREREG_PUMPDUMP_OHLCV.md. Xem header day du o file goc (pumpdump_detect.py).
Pipeline: sinh manifest -> chay PumpDumpOhlcvExtract (Java doc-only) -> doc CSV -> tinh feature.
Du lieu trung gian chi trong /tmp (KHONG commit).
"""
import json
import logging
import os
import subprocess
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "out")
os.makedirs(OUT_DIR, exist_ok=True)
LOGFILE = os.path.join(OUT_DIR, "pumpdump_ohlcv.log")
logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler(LOGFILE, "w"), logging.StreamHandler()])
L = logging.getLogger("pumpdump_ohlcv")

TZ = "Asia/Ho_Chi_Minh"
H_MS = 3600 * 1000
MIN_MS = 60 * 1000

CSV = "/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv"
OI_MAP = "/home/ubuntu/claudedata/oi/symbol_map.csv"
TICKER_DIR = "/home/ubuntu/kaggle_data_hpo/"
OI_FILE = "/home/ubuntu/claudedata/oi/oi_percoin_full.bin"

REPO = "/home/ubuntu/src/BinanceFuturesJava"
JAR = os.path.join(REPO, "target/binance-java-sdk-1.2.4.jar")
JAVA_SRC = os.path.join(REPO, "src/main/java/com/binance/chuyennd/research/PumpDumpOhlcvExtract.java")
JAVA_CLASSES = "/tmp/pumpdump_classes"
WORK = "/tmp/pumpdump_ohlcv"

SEED_DC = 20260917
SEED_BOOT = 20260905
NREP = 2000
CI_INFLATE = 1.21
BLOCK_H = 72

FEATURES = ["wick60", "volblow", "oi_px_div", "stall"]


def load_trades():
    d = pd.read_csv(CSV)
    d = d.loc[:, ~d.columns.str.startswith("Unnamed")].copy()
    for c in ("profit", "pnl"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["ts"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M").dt.tz_localize(TZ)
    d["entry_ts_ms"] = d["ts"].astype("int64") // 10**6
    d["full_sym"] = d["sym"] + "USDT"
    oi_map = pd.read_csv(OI_MAP)
    oi_symid = dict(zip(oi_map.symbol, oi_map.symId))
    assert d["full_sym"].isin(oi_symid).all(), "co sym khong co trong OI map"
    d["oi_symId"] = d["full_sym"].map(oi_symid).astype(int)
    d["sup"] = (d["profit"] <= -20).astype(int)
    d["win"] = (d["pnl"] > 0).astype(int)
    return d


def build_sample(d):
    sup = d[d["sup"] == 1]
    dc = d[d["sup"] == 0].sample(n=200, replace=False, random_state=SEED_DC)
    sel = pd.concat([sup, dc]).sort_values("entry_ts_ms").reset_index(drop=True)
    sel["tid"] = np.arange(len(sel))
    manifest = sel[["tid", "full_sym", "oi_symId", "entry_ts_ms", "sup"]].rename(
        columns={"full_sym": "sym", "sup": "group"})
    os.makedirs(WORK, exist_ok=True)
    manifest.to_csv(os.path.join(WORK, "manifest.csv"), index=False)
    L.info("n_total=%d n_SUP=%d n_DC_sampled=%d (seed %d)", len(d), len(sup), len(dc), SEED_DC)
    return sel


def run_extractor():
    subprocess.run(["javac", "-cp", JAR, "-d", JAVA_CLASSES, JAVA_SRC], check=True)
    cmd = ["java", "-Xmx4g", "-cp", f"{JAVA_CLASSES}:{JAR}",
           "com.binance.chuyennd.research.PumpDumpOhlcvExtract",
           os.path.join(WORK, "manifest.csv"), WORK, TICKER_DIR, OI_FILE]
    L.info("RUN EXTRACTOR: %s", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    sys.stderr.write(r.stderr)
    L.info("extractor stdout: %s", r.stdout.strip())
    assert r.returncode == 0, f"extractor fail rc={r.returncode}"


def feat_for_trade(g, oi_by_tid):
    ts = g["ts_ms"].values.astype(np.int64)
    o = g["o"].values.astype(np.float64)
    h = g["h"].values.astype(np.float64)
    lo = g["l"].values.astype(np.float64)
    c = g["c"].values.astype(np.float64)
    v = g["v"].values.astype(np.float64)
    entry = int(g["entry_ts_ms"].iloc[0])
    N = len(ts)
    out = {}

    # D1 wick60
    if N >= 60:
        so, sh, sl, sc = o[N - 60:], h[N - 60:], lo[N - 60:], c[N - 60:]
        rng = sh - sl
        with np.errstate(divide="ignore", invalid="ignore"):
            uwr = np.where(rng > 0, (sh - np.maximum(so, sc)) / rng, 0.0)
        out["wick60"] = float(uwr.max())
    else:
        out["wick60"] = np.nan

    # D2 volblow
    if N >= 1500:
        csum = np.concatenate([[0.0], np.cumsum(v)])
        recent = np.array([csum[i + 1] - csum[i - 4] for i in range(N - 60, N)])
        baseline = np.array([csum[i + 1] - csum[i - 4] for i in range(N - 1500, N - 60)])
        med = float(np.median(baseline))
        out["volblow"] = float(recent.max() / med) if med > 0 else np.nan
    else:
        out["volblow"] = np.nan

    # D3 + D4 share close-at-time
    ce = c[N - 1]

    def ret(kms):
        i = int(np.searchsorted(ts, entry - kms, side="right")) - 1
        if i < 0 or c[i] <= 0 or ce <= 0:
            return np.nan
        return ce / c[i] - 1.0

    # D4 stall = ret6h - ret15m
    r6 = ret(6 * H_MS)
    r15 = ret(15 * MIN_MS)
    out["stall"] = (r6 - r15) if (np.isfinite(r6) and np.isfinite(r15)) else np.nan

    # D3 oi_px_div = oiDelta24h - ret24h
    r24 = ret(24 * H_MS)
    rows = oi_by_tid.get(int(g["tid"].iloc[0]))
    oid = np.nan
    if rows is not None and len(rows) > 0:
        oid = rows["oi_delta24h"].iloc[-1]
    out["oi_px_div"] = float(oid - r24) if (np.isfinite(oid) and np.isfinite(r24)) else np.nan

    return out


def compute_features(sel, ohlcv, oi):
    oi = oi.sort_values(["tid", "ts_ms"]).reset_index(drop=True)
    oi_by_tid = {int(t): g.reset_index(drop=True) for t, g in oi.groupby("tid")}
    feats = {f: [] for f in FEATURES}
    for _, r in sel.iterrows():
        g = ohlcv[ohlcv["tid"] == int(r["tid"])].sort_values("ts_ms").copy()
        g["entry_ts_ms"] = r["entry_ts_ms"]
        fv = feat_for_trade(g, oi_by_tid)
        for f in FEATURES:
            feats[f].append(fv[f])
    for f in FEATURES:
        sel[f] = feats[f]
    return sel


def analyze(sel):
    n_total = len(sel)
    n_sup = int(sel["sup"].sum())
    res = {"n_total": n_total, "n_sup": n_sup, "n_dc": n_total - n_sup,
           "seed_dc": SEED_DC, "seed_boot": SEED_BOOT, "features": {}}

    for f in FEATURES:
        L.info("\n===== FEATURE %s =====", f)
        n_nan = int(sel[f].isna().sum())
        L.info("(d) NaN = %d / %d (%.1f%%)", n_nan, n_total, 100.0 * n_nan / n_total)
        fr = {"n_nan": n_nan}

        valid = sel[sel[f].notna()].copy().reset_index(drop=True)
        valid["decile"] = pd.qcut(valid[f].rank(method="first"), 10, labels=False).astype(int)
        dec_rows = []
        for k in range(10):
            gg = valid[valid["decile"] == k]
            nsup = int(gg["sup"].sum())
            dec_rows.append({
                "decile": k + 1, "feat_lo": float(gg[f].min()), "feat_hi": float(gg[f].max()),
                "n": int(len(gg)), "n_sup": nsup,
                "sup_rate_pct": 100.0 * nsup / len(gg) if len(gg) else np.nan,
                "mean_pnl_usdt": float(gg["pnl"].mean()) if len(gg) else np.nan,
                "total_pnl_usdt": float(gg["pnl"].sum()) if len(gg) else np.nan,
            })
        dec = pd.DataFrame(dec_rows)
        rho = spearmanr(dec["decile"].values, dec["sup_rate_pct"].values).correlation
        d10 = dec.loc[dec.decile == 10, "sup_rate_pct"].iloc[0]
        d1 = dec.loc[dec.decile == 1, "sup_rate_pct"].iloc[0]
        monotone = bool((rho >= 0.7) and (d10 > d1))
        fr["a"] = {"spearman_rho": float(rho), "monotone": monotone,
                   "d10_sup_rate": float(d10), "d1_sup_rate": float(d1), "deciles": dec_rows}
        L.info("(a) decile: rho=%.3f D1=%.1f%% D10=%.1f%% monotone=%s", rho, d1, d10, monotone)

        v_sup = valid.loc[valid["sup"] == 1, f].values
        v_dc = valid.loc[valid["sup"] == 0, f].values
        diff_mean = float(np.mean(v_sup) - np.mean(v_dc)) if (len(v_sup) and len(v_dc)) else np.nan
        fr["b"] = {"sup_mean": float(np.mean(v_sup)) if len(v_sup) else np.nan,
                   "sup_median": float(np.median(v_sup)) if len(v_sup) else np.nan,
                   "sup_n": int(len(v_sup)),
                   "dc_mean": float(np.mean(v_dc)) if len(v_dc) else np.nan,
                   "dc_median": float(np.median(v_dc)) if len(v_dc) else np.nan,
                   "dc_n": int(len(v_dc)), "diff_mean": diff_mean}

        t0 = int(valid["entry_ts_ms"].min())
        valid["blk"] = ((valid["entry_ts_ms"] - t0) // (BLOCK_H * H_MS)).astype(int)
        blk_list = np.sort(valid["blk"].unique())
        blk_to_idx = {b: np.array(g.index) for b, g in valid.groupby("blk")}
        feat_arr = valid[f].values
        sup_arr = valid["sup"].values
        rng = np.random.default_rng(SEED_BOOT)
        diffs = np.full(NREP, np.nan)
        for rep in range(NREP):
            pick = rng.integers(0, len(blk_list), size=len(blk_list))
            idx = np.concatenate([blk_to_idx[blk_list[p]] for p in pick])
            m = feat_arr[idx]; s = sup_arr[idx]
            a = m[s == 1]; b = m[s == 0]
            if len(a) > 0 and len(b) > 0:
                diffs[rep] = a.mean() - b.mean()
        diffs = diffs[np.isfinite(diffs)]
        lo, hi = np.percentile(diffs, [2.5, 97.5])
        ctr = (lo + hi) / 2.0
        lo_i = ctr - (ctr - lo) * CI_INFLATE
        hi_i = ctr + (hi - ctr) * CI_INFLATE
        excludes0 = bool(lo_i * hi_i > 0)
        fr["b"]["ci95_mean_raw"] = [float(lo), float(hi)]
        fr["b"]["ci95_mean_inflated"] = [float(lo_i), float(hi_i)]
        fr["b"]["bootstrap_sd"] = float(np.std(diffs, ddof=1))
        fr["b"]["n_rep_valid"] = int(len(diffs))
        fr["b"]["excludes_zero"] = excludes0
        L.info("(b) diff_mean=%.4f SUP mean=%.4f (n=%d) DC mean=%.4f (n=%d) CI infl [%.4f, %.4f] excl0=%s sd=%.4f",
               diff_mean, np.mean(v_sup), len(v_sup), np.mean(v_dc), len(v_dc), lo_i, hi_i, excludes0,
               fr["b"]["bootstrap_sd"])

        feat_valid = valid[f].values
        tradeoff = []
        any_net_ge0 = False
        for q in ("p75", "p90", "p95"):
            thr = float(np.percentile(feat_valid, int(q[1:])))
            rm = valid[valid[f] > thr]
            rm_sup = rm[rm["sup"] == 1]
            rm_win = rm[rm["pnl"] > 0]
            rm_other = rm[(rm["profit"] < 0) & (rm["profit"] > -20)]
            usd_lo_tranh = float(-rm_sup["pnl"].sum())
            usd_lai_mat = float(rm_win["pnl"].sum())
            net = float(-rm["pnl"].sum())
            if net >= 0:
                any_net_ge0 = True
            tradeoff.append({
                "threshold": q, "thr_value": thr, "n_removed": int(len(rm)),
                "n_sup_removed": int(len(rm_sup)), "usd_lo_tranh": usd_lo_tranh,
                "n_win_removed": int(len(rm_win)), "usd_lai_mat": usd_lai_mat,
                "n_otherloss_removed": int(len(rm_other)), "pnl_rong_thay_doi": net,
            })
        fr["c"] = tradeoff
        fr["c_any_net_ge0"] = bool(any_net_ge0)
        L.info("(c) danh doi what-if (KHONG re-run), any net>=0 = %s:", any_net_ge0)
        for row in tradeoff:
            L.info("  %s (feat>%.4f): removed=%d SUP=%d(lo tranh %+.0f) win=%d(lai mat %+.0f) other=%d => PnL rong %+.0f",
                   row["threshold"], row["thr_value"], row["n_removed"], row["n_sup_removed"],
                   row["usd_lo_tranh"], row["n_win_removed"], row["usd_lai_mat"],
                   row["n_otherloss_removed"], row["pnl_rong_thay_doi"])

        concl = "DANG_THEO" if (monotone and excludes0 and any_net_ge0) else "NULL"
        fr["conclusion"] = concl
        fr["criteria"] = {"a_monotone": monotone, "b_excludes_zero": excludes0,
                          "c_any_net_ge0": any_net_ge0}
        L.info("=> KET LUAN %s: monotone=%s excl0=%s net_ge0=%s => %s",
               f, monotone, excludes0, any_net_ge0, concl)
        res["features"][f] = fr

    return res


def main():
    d = load_trades()
    sel = build_sample(d)
    run_extractor()
    ohlcv = pd.read_csv(os.path.join(WORK, "ohlcv_1m.csv"))
    oi = pd.read_csv(os.path.join(WORK, "oi_5m.csv"))
    L.info("ohlcv rows=%d oi rows=%d", len(ohlcv), len(oi))
    sel = compute_features(sel, ohlcv, oi)
    res = analyze(sel)
    json_path = os.path.join(OUT_DIR, "pumpdump_ohlcv.json")
    with open(json_path, "w") as fh:
        json.dump(res, fh, indent=2, default=float)
    L.info("\nDONE_PUMPDUMP_OHLCV json=%s", json_path)


if __name__ == "__main__":
    main()
