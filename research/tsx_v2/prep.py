#!/usr/bin/env python3
"""TSX_V2 Phase A - prep: cum cham moc 168h (X14 tsx-x14-* va P0 gqsf-*, DEV 8 seed) + cua so gia 1m Vision + funding Vision.
Out (~/claude_master/tsx_v2/cache): clusters.pkl, win.npy (memmap float32 [Nw, W+1, 4] O/H/L/C, NaN = khong co nen),
win_meta.pkl (sym, t0_ms), fund.pkl (window -> (ts_ms, rate)). Khong REST; chi file tinh Vision da co tren Oracle.
"""
import logging
import os
import pickle
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("prep")
KS = "/home/ubuntu/kaggle_sim/out/"
OUT = "/home/ubuntu/claude_master/tsx_v2/cache"
SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
RUNS = {("X14", s): "tsx-x14-" + s.lower() for s in SEEDS}
RUNS.update({("P0", s): "gqsf-" + s.lower() for s in SEEDS})
MARK = 168 * 60 + 1          # tick dau tien tuoi > 168h
W = 30241 + 14 * 1440        # 504h+1' + 14 ngay (cho trailing sau 504h)
H7 = pd.Timedelta(hours=7)


def kp(ym):
    return os.path.join("/home/ubuntu/claude_master/gvz/k2021" if ym < "2021-12" else "/home/ubuntu/vz_e1/raw",
                        "kline1m-%s.parquet" % ym)


def load(tag):
    d = pd.read_csv(KS + tag + "/storage/printDone.csv", index_col=False)
    d.columns = [c.strip() for c in d.columns]
    for c in ("quantity", "entry", "pnl", "tp", "funding"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["pnl"]).copy()
    d["sym"] = d["sym"].astype(str).str.strip()
    d["status"] = d["status"].astype(str).str.strip()
    d["level"] = d["level"].astype(str).str.strip()
    d["ts"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M")
    d["te"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M")
    return d.reset_index(drop=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for (arm, s), tag in RUNS.items():
        d = load(tag)
        g = d.groupby(["sym", "te"], sort=False)
        for (sym, te), x in g:
            x = x.sort_values("ts", kind="mergesort")
            t0 = x["ts"].min()
            age = int((te - t0) // pd.Timedelta(minutes=1))
            if age < MARK:
                continue
            assert x["status"].nunique() == 1
            legs = [(int((a - t0) // pd.Timedelta(minutes=1)), float(e), float(q)) for a, e, q in
                    zip(x["ts"], x["entry"], x["quantity"])]
            rows.append(dict(arm=arm, seed=s, sym=sym, te=te, t0=t0, age=age, st=x["status"].iloc[0], n=len(x),
                             pnl=float(x["pnl"].sum()), tp=float(x["tp"].iloc[0]), fund=float(x["funding"].fillna(0).sum()),
                             legs=legs, levels=list(x["level"])))
        log.info("%s %s: %d cum cham moc", arm, s, sum(1 for r in rows if r["arm"] == arm and r["seed"] == s))
    C = pd.DataFrame(rows)
    C["t0_ms"] = ((C["t0"] - H7).astype("int64") // 10 ** 6).astype(np.int64)
    keys = sorted(set(zip(C["sym"], C["t0_ms"])))
    wid = {k: i for i, k in enumerate(keys)}
    C["wid"] = [wid[(a, b)] for a, b in zip(C["sym"], C["t0_ms"])]
    log.info("cum: %d, cua so duy nhat: %d, W=%d", len(C), len(keys), W)
    C.to_pickle(OUT + "/clusters.pkl")
    pickle.dump(keys, open(OUT + "/win_meta.pkl", "wb"))
    arr = np.lib.format.open_memmap(OUT + "/win.npy", mode="w+", dtype=np.float32, shape=(len(keys), W + 1, 4))
    arr[:] = np.nan
    K = pd.DataFrame(keys, columns=["sym", "t0_ms"])
    K["t1_ms"] = K["t0_ms"] + W * 60000
    K["s"] = K["sym"] + "USDT"
    m0 = pd.to_datetime(K["t0_ms"].min(), unit="ms").strftime("%Y-%m")
    m1 = pd.to_datetime(K["t1_ms"].max(), unit="ms").strftime("%Y-%m")
    months = [p.strftime("%Y-%m") for p in pd.period_range(m0, m1, freq="M")]
    for ym in months:
        fn = kp(ym)
        if not os.path.exists(fn):
            log.warning("thieu file gia %s", fn)
            continue
        a = int(pd.Timestamp(ym + "-01").value // 10 ** 6)
        b = int((pd.Timestamp(ym + "-01") + pd.offsets.MonthBegin(1)).value // 10 ** 6)
        sub = K[(K["t0_ms"] < b) & (K["t1_ms"] >= a)]
        if not len(sub):
            continue
        t = pq.read_table(fn, columns=["ts", "sym", "open", "high", "low", "close"],
                          filters=[("sym", "in", sorted(set(sub["s"])))]).to_pandas()
        t["sym"] = t["sym"].astype(str)
        t = t.drop_duplicates(["sym", "ts"], keep="last")
        by = {k: v for k, v in t.groupby("sym")}
        nf = 0
        for i, r in sub.iterrows():
            v = by.get(r["s"])
            if v is None:
                continue
            j = (v["ts"].to_numpy(np.int64) - r["t0_ms"]) // 60000
            ok = (j >= 0) & (j <= W) & ((v["ts"].to_numpy(np.int64) - r["t0_ms"]) % 60000 == 0)
            arr[i, j[ok], :] = v[["open", "high", "low", "close"]].to_numpy(np.float32)[ok]
            nf += int(ok.sum())
        log.info("gia %s: %d cua so, %d nen", ym, len(sub), nf)
        del t, by
    arr.flush()
    # funding Vision
    F = []
    for ym in months:
        fn = "/home/ubuntu/vz/out/funding/%s/%s.parquet" % (ym[:4], ym)
        if os.path.exists(fn):
            x = pd.read_parquet(fn, columns=["ts", "sym", "rate"])
            x["sym"] = x["sym"].astype(str)
            F.append(x[x["sym"].isin(set(K["s"]))])
        else:
            log.warning("thieu funding %s", fn)
    F = pd.concat(F).drop_duplicates(["sym", "ts"]).sort_values(["sym", "ts"])
    fb = {k: (v["ts"].to_numpy(np.int64), v["rate"].to_numpy(np.float64)) for k, v in F.groupby("sym")}
    fund = {}
    for i, r in K.iterrows():
        z = fb.get(r["s"])
        if z is None:
            fund[i] = (np.zeros(0, np.int64), np.zeros(0))
            continue
        m = (z[0] > r["t0_ms"]) & (z[0] <= r["t1_ms"])
        fund[i] = (z[0][m], z[1][m])
    pickle.dump(fund, open(OUT + "/fund.pkl", "wb"))
    cov = np.isfinite(arr[:, :MARK + 1, 3]).mean(axis=1)
    log.info("phu gia 0..168h: median %.4f, p1 %.4f, so cua so <0.9: %d", np.median(cov), np.percentile(cov, 1), int((cov < 0.9).sum()))
    log.info("XONG prep")


if __name__ == "__main__":
    main()
