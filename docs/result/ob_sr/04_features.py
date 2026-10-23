#!/usr/bin/env python3
"""OB_SR 04: features A_k, B_k, R_k, wall at entry / arm / 168h decision points."""
import os

import numpy as np
import pandas as pd

OUT = os.path.dirname(os.path.abspath(__file__))
BD = "/home/ubuntu/vz_bd/ob_sr"
BANDS = [1, 2, 3, 5]
COLS = ["n-5", "n-3", "n-2", "n-1", "n1", "n2", "n3", "n5"]
DAY_MS = 24 * 3600 * 1000
STALE_MS = 5 * 60 * 1000


def load_book(sym):
    p = "%s/%sUSDT.parquet" % (BD, sym)
    if not os.path.exists(p):
        return None
    d = pd.read_parquet(p)
    N = d[COLS].to_numpy(np.float64)
    valid = (N > 0).all(1)
    valid &= (N[:, 0] >= N[:, 1] - 1e-6) & (N[:, 1] >= N[:, 2] - 1e-6) & (N[:, 2] >= N[:, 3] - 1e-6)
    valid &= (N[:, 7] >= N[:, 6] - 1e-6) & (N[:, 6] >= N[:, 5] - 1e-6) & (N[:, 5] >= N[:, 4] - 1e-6)
    valid &= np.isfinite(d["mid"].to_numpy())
    d["valid"] = valid
    return d


def feats(d, t_ms, lo_arr, hi_arr):
    ts = d["ts"].to_numpy(np.int64)
    i = int(np.searchsorted(ts, t_ms, side="right")) - 1
    out = dict(snap_ts=np.nan, lag_s=np.nan, ok=0, why="", nsnap24=0, mid=np.nan)
    if i < 0:
        out["why"] = "nobook"
        return out
    j = i
    while j >= 0 and t_ms - ts[j] <= STALE_MS:
        if d["valid"].iat[j]:
            break
        j -= 1
    if j < 0 or t_ms - ts[j] > STALE_MS:
        out["why"] = "stale"
        return out
    row = d.iloc[j]
    out["mid"] = float(row["mid"])
    lo_arr = np.asarray(lo_arr, dtype=float); hi_arr = np.asarray(hi_arr, dtype=float)
    if len(lo_arr) and len(hi_arr):
        m0 = int(t_ms // 60000)
        ms = int(row["ts"] // 60000)
        idx = len(lo_arr) - 1 + (ms - m0)
        if idx < 0:
            out["why"] = "mid_out"
            return out
        lo = float(np.nanmin(lo_arr[max(0, idx - 1):idx + 1]))
        hi = float(np.nanmax(hi_arr[max(0, idx - 1):idx + 1]))
        if not (lo * 0.995 <= row["mid"] <= hi * 1.005):
            out["why"] = "mid_out"
            return out
    a = int(np.searchsorted(ts, t_ms - DAY_MS, side="right"))
    v = d.iloc[a:i + 1]
    v = v[v["valid"]]
    out.update(snap_ts=int(ts[j]), lag_s=float((t_ms - ts[j]) / 1000), ok=1, nsnap24=len(v))
    for k in BANDS:
        A = float(row["n%d" % k]); B = float(row["n-%d" % k])
        out["A%d" % k] = A; out["B%d" % k] = B
        out["R%d" % k] = (B - A) / (B + A)
        if len(v) >= 720:
            out["wA%d" % k] = int(A >= 3 * np.median(v["n%d" % k].to_numpy(np.float64)))
            out["wB%d" % k] = int(B >= 3 * np.median(v["n-%d" % k].to_numpy(np.float64)))
        else:
            out["wA%d" % k] = np.nan; out["wB%d" % k] = np.nan
    return out


def main():
    G = pd.read_parquet(OUT + "/anchor.parquet")
    R = pd.read_parquet(OUT + "/price_out.parquet")
    G["t0"] = pd.to_datetime(G["t0"])
    R["t0"] = pd.to_datetime(R["t0"])
    M = G.merge(R, on=["sym", "t0"], how="left", suffixes=("", "_r"))
    rows = []
    for sym, g in M.groupby("sym", sort=False):
        d = load_book(sym)
        for r in g.itertuples():
            t0ms = int(r.t0.value // 10 ** 6)
            pts = [("entry", t0ms, r.pre_lo0, r.pre_hi0)]
            if pd.notna(r.arm_j) and r.arm_j > 0:
                pts.append(("arm", t0ms + int(r.arm_j) * 60000, r.pre_loa, r.pre_hia))
            if r.age_max >= 10081:
                pts.append(("h168", t0ms + 10081 * 60000, r.pre_lo6, r.pre_hi6))
            for p, tms, lo, hi in pts:
                base = dict(sym=sym, t0=r.t0, year=r.year, episode=r.episode, point=p)
                if d is None:
                    base.update(ok=0, why="nofile", nsnap24=0)
                else:
                    base.update(feats(d, tms, lo, hi))
                rows.append(base)
    F = pd.DataFrame(rows)
    F.to_parquet(OUT + "/features.parquet", index=False)
    print(F.groupby(["point", "year"])["ok"].agg(["size", "mean"]).to_string())
    print("why:", F[F.ok == 0]["why"].value_counts().to_dict())
    print("lag median/p95", F.loc[F.ok == 1, "lag_s"].median(), F.loc[F.ok == 1, "lag_s"].quantile(.95))


if __name__ == "__main__":
    main()
