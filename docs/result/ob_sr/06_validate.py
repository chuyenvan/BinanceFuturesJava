#!/usr/bin/env python3
"""OB_SR 06: V4 - replay our 264h windows against printDone (clusters with age 168h..264h)."""
import json
import os
import sys
from decimal import Decimal

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/tsx_v2")
import engine as EN  # noqa: E402
import common as CM  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
KRAW = "/home/ubuntu/vz_e1/raw"
FUND = "/home/ubuntu/vz/out/funding"
HOR = 264 * 60
MARK = 168 * 60 + 1


def kfile(ym):
    return KRAW + "/kline1m-%s.parquet" % ym


def ticks():
    ex = json.load(open("/home/ubuntu/java/exchange_info_pin.json"))
    return {s["symbol"]: Decimal(EN.jstr(np.float32(float(f["tickSize"]))))
            for s in ex["symbols"] for fl in s["filters"] for f in fl if f.get("tickSize") is not None}


def main():
    A = pd.read_parquet(OUT + "/anchors.parquet")
    A["t0"] = pd.to_datetime(A["t0"])
    A = A[A["t0"].dt.year.isin([2023, 2024, 2025])]
    A = A[(A["age_min"] >= MARK) & (A["age_min"] <= HOR)].copy()
    A["ym"] = A["t0"].dt.strftime("%Y-%m")
    TK = ticks()
    eod = CM.ew_eod()
    days, fok = CM.base_flags_check(eod)
    assert fok
    dset = CM.dayints(days)
    rows = []
    for m, g in A.groupby("ym"):
        nxt = str((pd.Timestamp(m + "-01") + pd.offsets.MonthBegin(1)))[:7]
        syms = set(g["sym"] + "USDT")
        frames = {}
        for ym in (m, nxt):
            fn = kfile(ym)
            if not os.path.exists(fn):
                continue
            t = pd.read_parquet(fn, columns=["ts", "sym", "open", "high", "low", "close"])
            t = t[t["sym"].isin(syms)]
            for s, v in t.groupby("sym", sort=False):
                v = v.sort_values("ts")
                frames.setdefault(s, []).append((v["ts"].to_numpy(np.int64), v["open"].to_numpy(np.float32),
                                                 v["high"].to_numpy(np.float32), v["low"].to_numpy(np.float32),
                                                 v["close"].to_numpy(np.float32)))
        fund = {}
        for ym in (m, nxt):
            fn = "%s/%s/%s.parquet" % (FUND, ym[:4], ym)
            if os.path.exists(fn):
                x = pd.read_parquet(fn, columns=["ts", "sym", "rate"])
                for s, v in x[x["sym"].isin(syms)].groupby("sym"):
                    fund.setdefault(s, []).append((v["ts"].to_numpy(np.int64), v["rate"].to_numpy(np.float64)))
        for r in g.itertuples():
            s = r.sym + "USDT"
            if s not in frames:
                continue
            fs = frames[s]
            ts = np.concatenate([z[0] for z in fs])
            O = np.concatenate([z[1] for z in fs]); H = np.concatenate([z[2] for z in fs])
            L = np.concatenate([z[3] for z in fs]); C = np.concatenate([z[4] for z in fs])
            i0 = int(np.searchsorted(ts, r.t0_ms, "left"))
            if i0 >= len(ts) or ts[i0] != r.t0_ms:
                continue
            n = min(HOR + 1, len(ts) - i0)
            arr = np.stack([O[i0:i0 + n], H[i0:i0 + n], L[i0:i0 + n], C[i0:i0 + n]], axis=1)
            fz = fund.get(s, [(np.zeros(0, np.int64), np.zeros(0))])
            fts = np.concatenate([z[0] for z in fz]); frt = np.concatenate([z[1] for z in fz])
            k = (fts > r.t0_ms) & (fts <= r.t0_ms + n * 60000)
            w = EN.Win(arr, r.t0_ms, (fts[k], frt[k]), TK.get(s))
            legs = [(int(j), float(e), float(q)) for j, e, q in r.legs]
            res = EN.replay(w, legs, dayset=dset, cap_j=CM.CAP504)
            err = abs(res["pnl"] - r.pnl) if np.isfinite(res["pnl"]) else np.inf
            rows.append(dict(seed=r.seed, sym=r.sym, t0=r.t0, age=r.age_min, st=r.status,
                             r_st=res["st"], pnl=r.pnl, r_pnl=res["pnl"], err=err,
                             ok=bool(res["st"] == r.status and err <= 1e-3 * max(abs(r.pnl), 1.0))))
    R = pd.DataFrame(rows)
    R.to_pickle(OUT + "/v4.pkl")
    d = dict(n=len(R), ok=float(R["ok"].mean()) if len(R) else None,
             err_med=float(R["err"].median()) if len(R) else None,
             err_p99=float(R["err"].quantile(.99)) if len(R) else None,
             fail=int((~R["ok"]).sum()) if len(R) else 0)
    json.dump(d, open(OUT + "/v4.json", "w"), indent=1)
    print(d)
    if len(R) and (~R["ok"]).any():
        print(R[~R["ok"]].head(10).to_string())


if __name__ == "__main__":
    main()
