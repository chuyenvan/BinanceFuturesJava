#!/usr/bin/env python3
"""short_state_defs.py — CO SO DU LIEU THAT cho dinh nghia STATE short (SHORT_STATE_DEFS).

Do phan bo THOI LUONG chu ky (daily, ticker ≤2025) bang ZigZag(theta co dinh):
  up-leg  = day->dinh ; bleed-leg = dinh->day.  Tach theo TIER (notional 30d).
Nguon: CLOSES_1H.bin (daily close) + /tmp/short_state_tier.parquet (notional).
Output: research/analysis/out/short_state_defs.json
"""
import json, os
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
H = 3600000
DAY = 86400000
DEV_END_MS = 1767225600000
CLOSES = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
MAP = "/home/ubuntu/claudedata/oi/symbol_map.csv"
TIER = "/tmp/short_state_tier.parquet"
OUT = os.path.join(REPO, "research/analysis/out/short_state_defs.json")
THETA = 0.25          # nguong swing ZigZag co dinh


def daily_close():
    DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
    a = np.fromfile(CLOSES, dtype=DT)
    ts = a["ts"].astype(np.int64); sym = a["sym"].astype(np.int64); c = a["c"].astype(float)
    m = (ts % DAY) == 0
    ts, sym, c = ts[m], sym[m], c[m]
    day = pd.to_datetime(ts, unit="ms", utc=True).normalize().tz_localize(None) - pd.Timedelta(days=1)
    df = pd.DataFrame({"date": day, "sym": sym, "close": c})
    return df.dropna().sort_values(["sym", "date"])


def zigzag(p, thr):
    ext = []; dirn = 0
    hi = lo = p[0]; hi_i = lo_i = 0
    for i in range(len(p)):
        x = p[i]
        if dirn >= 0:
            if x > hi:
                hi = x; hi_i = i
            elif x <= hi * (1 - thr):
                ext.append((hi_i, 1)); dirn = -1; lo = x; lo_i = i
        if dirn <= 0:
            if x < lo:
                lo = x; lo_i = i
            elif x >= lo * (1 + thr):
                ext.append((lo_i, -1)); dirn = 1; hi = x; hi_i = i
    return ext


def pct(v, q):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return float(np.percentile(v, q)) if len(v) else float("nan")


def main():
    print("=== SHORT_STATE_DEFS: do thoi luong chu ky (ZigZag %.0f%%) ===" % (100 * THETA), flush=True)
    df = daily_close()
    tr = pd.read_parquet(TIER)
    tmean = tr.groupby("sym")["notional"].median()
    rank = tmean.rank(pct=True)
    big = set(rank[rank >= 0.70].index.tolist())
    rac = set(rank[rank <= 0.30].index.tolist())
    up = []; bl = []; up_ret = []; bl_ret = []
    upb = []; blb = []; upr = []; blr = []
    upr_ = []; blr_ = []; uprr = []; blrr = []
    ncoin = 0
    for s, g in df.groupby("sym", sort=False):
        if len(g) < 120:
            continue
        ncoin += 1
        p = g["close"].to_numpy()
        ext = zigzag(p, THETA)
        for (i1, t1), (i2, t2) in zip(ext, ext[1:]):
            dur = i2 - i1
            ret = p[i2] / p[i1] - 1
            if t1 == -1 and t2 == 1:      # trough -> peak = up-leg
                up.append(dur); up_ret.append(ret)
                if s in big:
                    upb.append(dur); upr.append(ret)
                elif s in rac:
                    upr_.append(dur); uprr.append(ret)
            elif t1 == 1 and t2 == -1:    # peak -> trough = bleed-leg
                bl.append(dur); bl_ret.append(ret)
                if s in big:
                    blb.append(dur); blr.append(ret)
                elif s in rac:
                    blr_.append(dur); blrr.append(ret)
    res = {"theta": THETA, "n_coin": ncoin,
           "up_leg_days": {"n": len(up), "median": pct(up, 50), "mean": float(np.mean(up)),
                           "p75": pct(up, 75), "p90": pct(up, 90)},
           "bleed_leg_days": {"n": len(bl), "median": pct(bl, 50), "mean": float(np.mean(bl)),
                              "p75": pct(bl, 75), "p90": pct(bl, 90)},
           "up_leg_ret": {"median_pct": 100 * pct(up_ret, 50), "p75_pct": 100 * pct(up_ret, 75),
                          "p90_pct": 100 * pct(up_ret, 90)},
           "bleed_leg_ret": {"median_pct": 100 * pct(bl_ret, 50), "p75_pct": 100 * pct(bl_ret, 75),
                             "p90_pct": 100 * pct(bl_ret, 90)},
           "bigalt": {"up_days": {"n": len(upb), "median": pct(upb, 50), "p75": pct(upb, 75),
                                  "p90": pct(upb, 90)},
                      "bleed_days": {"n": len(blb), "median": pct(blb, 50), "p75": pct(blb, 75),
                                     "p90": pct(blb, 90)},
                      "up_ret_median_pct": 100 * pct(upr, 50),
                      "bleed_ret_median_pct": 100 * pct(blr, 50)},
           "rac": {"up_days": {"n": len(upr_), "median": pct(upr_, 50), "p75": pct(upr_, 75),
                                "p90": pct(upr_, 90)},
                   "bleed_days": {"n": len(blr_), "median": pct(blr_, 50), "p75": pct(blr_, 75),
                                  "p90": pct(blr_, 90)},
                   "up_ret_median_pct": 100 * pct(uprr, 50),
                   "bleed_ret_median_pct": 100 * pct(blrr, 50)}}
    # "rac" = complement of big within ranked
    print(json.dumps(res, indent=1), flush=True)
    json.dump(res, open(OUT, "w"), indent=1, default=str)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
