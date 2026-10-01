"""BD_DEEP_steer — kiem chung STEER owner 11:32 ("doi DownAvg15M tu MAX -> HIGH") + do counterfactual.

0-sim, Python. Tra loi:
  (1) `symbol2PriceMax` hien tai lay tu dau (MAX HIGH hay MAX CLOSE) - bang so.
  (2) Counterfactual NGƯỢC (HIGH->CLOSE): so lan BD/DCA doi trang thai + nguong phai noi bao nhieu.

Chay: python3 research/analysis/bd_deep_steer.py [n_days]
Ghi: research/analysis/out/bd_deep_steer.json
"""
import gzip
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jbin  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("bd_deep_steer")

TICKDIR = "/home/ubuntu/java/simulator/kaggle_data_hpo"
OUT = os.path.join(HERE, "out")
DT = np.dtype([("ts", ">i8"), ("down", ">f4"), ("up", ">f4"), ("down15", ">f4")])
THR = -0.03157
WIN = 15
N = 100
SEED = 20261001


def market_lookup():
    with open("/home/ubuntu/wfo_ds_x1_2021/market.bin", "rb") as f:
        n = int(np.frombuffer(f.read(4), dtype=">i4")[0])
        a = np.frombuffer(f.read(n * 20), dtype=DT)
    ts = a["ts"].astype(np.int64)
    return {int(t): (float(d), float(u), float(x)) for t, d, u, x in zip(ts, a["down"], a["up"], a["down15"])}


def pick_days(nd):
    ts, down = None, None
    with open("/home/ubuntu/wfo_ds_x1_2021/market.bin", "rb") as f:
        n = int(np.frombuffer(f.read(4), dtype=">i4")[0])
        a = np.frombuffer(f.read(n * 20), dtype=DT)
    ts = a["ts"].astype(np.int64)
    down = a["down"].astype(float)
    lo = int(pd.Timestamp("2021-07-01", tz="Asia/Saigon").timestamp() * 1000)
    hi = int(pd.Timestamp("2025-12-31", tz="Asia/Saigon").timestamp() * 1000)
    k = (ts >= lo) & (ts < hi)
    ts, down = ts[k], down[k]
    day = pd.to_datetime(ts, unit="ms", utc=True).strftime("%Y%m%d").values
    bd = sorted(set(day[down < THR]))
    allc = sorted(set(day))
    rng = np.random.RandomState(SEED)
    rest = [d for d in allc if d not in set(bd)]
    extra = [rest[i] for i in rng.choice(len(rest), size=max(0, nd - len(bd)), replace=False)]
    have = {p[7:15] for p in os.listdir(TICKDIR) if p.startswith("ticker_") and p.endswith(".bin.gz")}
    return [d for d in sorted(set(bd) | set(extra)) if d in have][:nd]


def cal_avg(keys, period):
    n = len(keys)
    if n == 0:
        return 0.0
    p = int(period)
    if p > n * 4 // 5:
        p = n * 4 // 5
    if p <= 0:
        return 0.0
    return sum(keys[:p]) / p


def day_rows(day):
    """Tra (ms, d15_high, d15_close) cho tung phut - cung N=100, WIN=15."""
    with gzip.open(os.path.join(TICKDIR, "ticker_%s.bin.gz" % day), "rb") as g:
        b = g.read()
    hh, hc = {}, {}
    out = []
    for ms, m in jbin.iter_minutes(b):
        rmaxH, rmaxC = [], []
        for sym, v in m.items():
            st, maxP, minP, close, op, vol = v
            if not op or not close:
                continue
            a = hh.setdefault(sym, [])
            a.append(maxP)
            if len(a) > WIN:
                del a[0:len(a) - WIN]
            rmaxH.append(close / max(a) - 1.0)
            c = hc.setdefault(sym, [])
            c.append(close)
            if len(c) > WIN:
                del c[0:len(c) - WIN]
            rmaxC.append(close / max(c) - 1.0)
        rmaxH.sort()
        rmaxC.sort()
        out.append((int(ms), cal_avg(rmaxH, N), cal_avg(rmaxC, N)))
    return out


def main():
    nd = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    days = pick_days(nd)
    log.info("days=%d", len(days))
    ml = market_lookup()
    ms_l, hi_l, cl_l = [], [], []
    for i, d in enumerate(days):
        for ms, ah, ac in day_rows(d):
            ms_l.append(ms)
            hi_l.append(ah)
            cl_l.append(ac)
        if (i + 1) % 20 == 0:
            log.info("days done %d/%d", i + 1, len(days))
    ms_l = np.array(ms_l)
    hi_l = np.array(hi_l)
    cl_l = np.array(cl_l)

    # (1) PARITY: gia tri HIGH-max phai khop market.bin; CLOSE-max thi KHONG.
    ref = np.array([ml.get(int(m), (np.nan, np.nan, np.nan))[2] for m in ms_l])
    dh = np.abs(hi_l - ref)
    dc = np.abs(cl_l - ref)
    res = {"days": len(days), "n_min": int(len(ms_l)),
           "parity_HIGHmax": dict(maxabs=float(np.nanmax(dh)), pct_lt_1e3=float((dh < 1e-3).mean() * 100)),
           "parity_CLOSEmax": dict(maxabs=float(np.nanmax(dc)), pct_lt_1e3=float((dc < 1e-3).mean() * 100))}
    log.info("PARITY HIGH-max: maxabs=%.2e  %%<1e-3=%.2f", res["parity_HIGHmax"]["maxabs"], res["parity_HIGHmax"]["pct_lt_1e3"])
    log.info("PARITY CLOSE-max: maxabs=%.2e  %%<1e-3=%.2f", res["parity_CLOSEmax"]["maxabs"], res["parity_CLOSEmax"]["pct_lt_1e3"])

    # (2) Counterfactual NGƯỢC: HIGH -> CLOSE
    onh = hi_l < THR
    onc = cl_l < THR
    union = int((onh | onc).sum())
    res["cf"] = dict(
        n_on_high=int(onh.sum()), n_on_close=int(onc.sum()),
        ep_high=int(np.count_nonzero(onh & ~np.concatenate([[False], onh[:-1]]))),
        ep_close=int(np.count_nonzero(onc & ~np.concatenate([[False], onc[:-1]]))),
        jaccard=round(float((onh & onc).sum() / union), 4) if union else None,
        corr=round(float(np.corrcoef(hi_l, cl_l)[0, 1]), 4),
        mean_high=round(float(hi_l.mean()), 6), mean_close=round(float(cl_l.mean()), 6),
        turned_off=int((onh & ~onc).sum()), turned_on=int((onc & ~onh).sum()),
    )
    # nguong phai noi bao nhieu de giu NGUYEN so phut ON nhu HIGH-max@-0.03157
    k = int(onh.sum())
    if k > 0:
        srt = np.sort(cl_l)
        thr_match = float(srt[k - 1])
        res["cf"]["thr_close_to_match_n_on"] = round(thr_match, 6)
        res["cf"]["thr_shift"] = round(thr_match - THR, 6)
        log.info("CLOSE-max can nguong %.5f (lech %.5f) moi giu dung %d phut ON", thr_match, thr_match - THR, k)
    log.info("cf: high_on=%d close_on=%d jac=%s corr=%s off=%d on=%d",
             res["cf"]["n_on_high"], res["cf"]["n_on_close"], res["cf"]["jaccard"], res["cf"]["corr"],
             res["cf"]["turned_off"], res["cf"]["turned_on"])
    json.dump(res, open(os.path.join(OUT, "bd_deep_steer.json"), "w"), indent=1)
    log.info("-> %s", os.path.join(OUT, "bd_deep_steer.json"))


if __name__ == "__main__":
    main()
