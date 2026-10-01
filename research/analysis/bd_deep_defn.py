"""BD_DEEP_defn — quet N / cua so / dinh nghia tren MAU NGAY (0-sim, Python).

Chay: python3 research/analysis/bd_deep_defn.py [n_days]
Ghi: research/analysis/out/bd_deep_defn.json
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
log = logging.getLogger("bd_deep_defn")

TICKDIR = "/home/ubuntu/java/simulator/kaggle_data_hpo"
OUT = os.path.join(HERE, "out")
DT = np.dtype([("ts", ">i8"), ("down", ">f4"), ("up", ">f4"), ("down15", ">f4")])
THR = -0.03157
N_LIST = [20, 50, 100, 200, 400]
WIN_LIST = [5, 15, 30, 60]
Q_LIST = [0.10, 0.33, 0.50]
SEED = 20261001


def load_market():
    with open("/home/ubuntu/wfo_ds_x1_2021/market.bin", "rb") as f:
        n = int(np.frombuffer(f.read(4), dtype=">i4")[0])
        a = np.frombuffer(f.read(n * 20), dtype=DT)
    ts = a["ts"].astype(np.int64)
    return ts, a["down"].astype(float), a["up"].astype(float), a["down15"].astype(float)


def pick_days():
    ts, down, up, d15 = load_market()
    lo = int(pd.Timestamp("2021-07-01", tz="Asia/Saigon").timestamp() * 1000)
    hi = int(pd.Timestamp("2025-12-31", tz="Asia/Saigon").timestamp() * 1000)
    k = (ts >= lo) & (ts < hi)
    ts, down = ts[k], down[k]
    day = pd.to_datetime(ts, unit="ms", utc=True).strftime("%Y%m%d").values
    bd_days = sorted(set(day[down < THR]))
    all_days = sorted(set(day))
    rng = np.random.RandomState(SEED)
    rest = [d for d in all_days if d not in set(bd_days)]
    extra = [rest[i] for i in rng.choice(len(rest), size=min(46, len(rest)), replace=False)]
    days = sorted(set(bd_days) | set(extra))
    have = {p.split("ticker_")[1][:8] for p in os.listdir(TICKDIR) if p.startswith("ticker_") and p.endswith(".bin.gz")}
    days = [d for d in days if d in have]
    log.info("days=%d (bigdown=%d extra=%d)", len(days), len(bd_days), len(extra))
    return days


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


def day_series(day):
    """Tra list (ms, sorted_rateDown_keys, {win: sorted_rateMax_keys}, n_sym)."""
    p = os.path.join(TICKDIR, "ticker_%s.bin.gz" % day)
    with gzip.open(p, "rb") as g:
        b = g.read()
    out = []
    hist = {w: {} for w in WIN_LIST}
    for ms, m in jbin.iter_minutes(b):
        btc = m.get("BTCUSDT")
        rbtc = (btc[3] / btc[4] - 1.0) if (btc is not None and btc[4]) else 0.0
        rd, rmax = [], {w: [] for w in WIN_LIST}
        for sym, v in m.items():
            st, maxP, minP, close, op, vol = v
            if not op or not close:
                continue
            rc = close / op - 1.0
            if rbtc > -0.004 and rc < -0.15:
                continue
            if rc > 0.3:
                continue
            rd.append(rc)
            for w in WIN_LIST:
                h = hist[w].setdefault(sym, [])
                h.append(maxP)
                if len(h) > w:
                    del h[0:len(h) - w]
                rmax[w].append(close / max(h) - 1.0)
        rd.sort()
        for w in WIN_LIST:
            rmax[w].sort()
        out.append((ms, rd, rmax, len(rd)))
    return out


def main():
    nd = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    days = pick_days()[:nd]
    res = {"days": days, "thr": THR, "variants": {}}
    base_on_down, base_on_d15 = set(), set()
    series = {}   # variant -> (list values, list ms)
    nsym = []
    for di, day in enumerate(days):
        ds = day_series(day)
        for ms, rd, rmax, n in ds:
            nsym.append(n)
            rd = np.array(rd)
            r15 = np.array(rmax[15])
            def put(tag, val):
                series.setdefault(tag, ([], []))
                series[tag][0].append(val)
                series[tag][1].append(ms)
            put("base_down", cal_avg(rd, 100))
            put("base_d15", cal_avg(r15, 100))
            for N in N_LIST:
                put("down_N%d" % N, cal_avg(rd, N))
                put("d15_N%d" % N, cal_avg(r15, N))
            for w in WIN_LIST:
                put("d15_win%d" % w, cal_avg(np.array(rmax[w]), 100))
            for q in Q_LIST:
                n = len(rd)
                p = max(1, int(np.ceil(q * n)))
                put("down_frac%.2f" % q, float(rd[:p].mean()))
                n = len(r15)
                p = max(1, int(np.ceil(q * n)))
                put("d15_frac%.2f" % q, float(r15[:p].mean()))
        if (di + 1) % 10 == 0:
            log.info("days done %d/%d", di + 1, len(days))

    def stats(tag, base_tag):
        vals = np.array(series[tag][0])
        bv = np.array(series[base_tag][0])
        on = vals < THR
        bon = bv < THR
        inter = int((on & bon).sum())
        union = int((on | bon).sum())
        ep = int(np.count_nonzero(on & ~np.concatenate([[False], on[:-1]])))
        return dict(n_on=int(on.sum()), episodes=ep,
                    jaccard=round(inter / union, 4) if union else None,
                    corr=round(float(np.corrcoef(vals, bv)[0, 1]), 4),
                    mean=round(float(vals.mean()), 6),
                    p1=round(float(np.percentile(vals, 1)), 6))

    res["universe"] = dict(mean_sym=round(float(np.mean(nsym)), 1), min_sym=int(min(nsym)), max_sym=int(max(nsym)))
    for tag in sorted(series):
        base_tag = "base_down" if tag.startswith("down") else "base_d15"
        res["variants"][tag] = stats(tag, base_tag)
    res["base_down"] = res["variants"].pop("base_down")
    res["base_d15"] = res["variants"].pop("base_d15")
    json.dump(res, open(os.path.join(OUT, "bd_deep_defn.json"), "w"), indent=1)
    log.info("universe: %s", res["universe"])
    log.info("BASE down  : %s", res["base_down"])
    log.info("BASE d15   : %s", res["base_d15"])
    for tag in sorted(res["variants"]):
        v = res["variants"][tag]
        if v["jaccard"] is not None and v["jaccard"] < 0.8 or tag.endswith(tuple("N20 N400".split())) and False:
            pass
        log.info("%-14s n_on=%5d ep=%5d jac=%s corr=%s mean=%.6f", tag, v["n_on"], v["episodes"], v["jaccard"], v["corr"], v["mean"])
    log.info("-> %s", os.path.join(OUT, "bd_deep_defn.json"))


if __name__ == "__main__":
    main()
