"""VIEC 1/2 cua docs/prereg/PREREG_GATE_ROOTCAUSE.md — DO LECH NGUON/THANG DO p15 + uoc ty le pass.

- S_dev  = /home/ubuntu/wfo_ds_x1_2021/pred.bin cot predReturn15M (FIT, <=2025-12-31)
- S_live = /tmp/live242_p15.txt  (242 full.log market[15M:x%], 12/08-27/09/2026)  -> CHI CHAN DOAN
- S_sh  = /tmp/liveshadow_p15.txt (Oracle shadow)                                 -> CHI CHAN DOAN

Ra JSON: docs/result/RESULT_GATE_ROOTCAUSE.json (phan phan bo).  Output tool rat nho.
"""
import json
import math
import os
import sys

import numpy as np

RESULTS = "/home/ubuntu/src/BinanceFuturesJava/docs/result/RESULT_GATE_ROOTCAUSE.json"
QS = [1, 5, 25, 50, 75, 95, 99]
THR = [0.8, 1.705, 2.947, 3.76]
QSET = [0.995, 0.998, 0.999]


def load_pred_dev():
    with open("/home/ubuntu/wfo_ds_x1_2021/pred.bin", "rb") as f:
        f.read(4)
        b = f.read()
    dt = np.dtype([("t", ">i8"), ("a", ">f4"), ("b", ">f4")])
    arr = np.frombuffer(b, dtype=dt)
    return arr["a"].astype("f8") * 100.0, arr["t"].astype("i8")


def load_txt(p):
    out = []
    with open(p) as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(float(ln))
            except ValueError:
                pass
    return np.array(out, dtype="f8")


def nr_quantile(v, q):
    """nearest-rank: chi so 1-based = ceil(q*n), giong EntryGate.buildP15Rolling."""
    n = v.size
    rank = int(math.ceil(q * n))
    rank = max(1, min(n, rank))
    return float(np.sort(v)[rank - 1])


def summ(v):
    d = {"n": int(v.size), "min": round(float(v.min()), 4), "max": round(float(v.max()), 4)}
    for q in QS:
        d["p%d" % q] = round(nr_quantile(v, q / 100.0), 4)
    for q in QSET:
        d["q%g" % q] = round(nr_quantile(v, q), 4)
    d["ge"] = {str(t): int(np.count_nonzero(v >= t)) for t in THR}
    return d


def main():
    dev, ts = load_pred_dev()
    live = load_txt("/tmp/live242_p15.txt")
    sh = load_txt("/tmp/liveshadow_p15.txt")
    res = {"S_dev": summ(dev), "S_live": summ(live), "S_shadow": summ(sh)}
    res["S_dev"]["days"] = round((int(ts[-1]) - int(ts[0])) / 86400000.0, 1)
    res["S_dev"]["per_day"] = round(dev.size / res["S_dev"]["days"], 1)

    # thuong so scale theo tung phan vi + chi so hinh dang
    r = {}
    for q in QS:
        r["p%d" % q] = round(res["S_live"]["p%d" % q] / res["S_dev"]["p%d" % q], 4)
    r["max"] = round(res["S_live"]["max"] / res["S_dev"]["max"], 4)
    r["min"] = round(res["S_live"]["min"] / res["S_dev"]["min"], 4)
    rr = [v for k, v in r.items()]
    res["ratio_live_dev"] = r
    res["ratio_D_max_over_min"] = round(max(rr) / min(rr), 3)
    res["ratio_median"] = round(float(np.median(rr)), 4)

    # fit affine y = a + b*x tren THAN (p5..p95), kiem tra duoi
    xs = np.array([res["S_dev"]["p5"], res["S_dev"]["p25"], res["S_dev"]["p50"],
                   res["S_dev"]["p75"], res["S_dev"]["p95"]])
    ys = np.array([res["S_live"]["p5"], res["S_live"]["p25"], res["S_live"]["p50"],
                   res["S_live"]["p75"], res["S_live"]["p95"]])
    b, a = np.polyfit(xs, ys, 1)
    res["affine_body"] = {"a_pp": round(float(a), 4), "b": round(float(b), 4)}
    pred = a + b * np.array([res["S_dev"][k] for k in
                             ["p1", "p5", "p25", "p50", "p75", "p95", "p99", "max"]])
    act = np.array([res["S_live"][k] for k in
                    ["p1", "p5", "p25", "p50", "p75", "p95", "p99", "max"]])
    res["affine_resid"] = {k: round(float(p - ac), 4) for k, p, ac in
                           zip(["p1", "p5", "p25", "p50", "p75", "p95", "p99", "max"], pred, act)}

    # ky vong so mau live >= thr neu live theo dung phan bo dev (Poisson)
    nlive = res["S_live"]["n"]
    po = {}
    for t in THR:
        fd = res["S_dev"]["ge"][str(t)] / dev.size
        mu = fd * nlive
        obs = res["S_live"]["ge"][str(t)]
        # P(X <= obs) voi Poisson(mu)
        if mu <= 0:
            p = 1.0
        else:
            p = math.exp(-mu)
            c = math.exp(-mu)
            for i in range(1, obs + 1):
                c *= mu / i
                p += c
        po[str(t)] = {"frac_dev": round(fd, 6), "mu_live": round(mu, 2), "obs_live": obs,
                      "P_X_le_obs": float("%.6g" % p)}
    res["poisson"] = po

    # VIEC 2: nguong phan vi cuon cua CHINH nguon live (chan doan) + pass/ngay ky vong
    days_live = 46.0
    perday = nlive / days_live
    pr = {}
    for q in QSET:
        thr = nr_quantile(live, q)
        cnt = int(np.count_nonzero(live >= thr))
        pr["q%g" % q] = {"thr_live_pct": round(thr, 4), "n_ge": cnt,
                         "pass_per_day_live": round(cnt / days_live, 3),
                         "pass_per_day_dev15m": round((1 - q) * 96, 3),
                         "dev_thr_pct": round(nr_quantile(dev, q), 4)}
    res["rolling_rule_projection"] = pr
    res["live_window_days"] = days_live

    os.makedirs(os.path.dirname(RESULTS), exist_ok=True)
    with open(RESULTS, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: res[k] for k in
                      ["S_dev", "S_live", "S_shadow", "ratio_live_dev", "ratio_D_max_over_min",
                       "ratio_median", "affine_body", "affine_resid", "poisson",
                       "rolling_rule_projection"]}, indent=1))


if __name__ == "__main__":
    main()
