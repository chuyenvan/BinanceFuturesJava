#!/usr/bin/env python3
"""fee_invariance_check.py — PREREG_CAP70_FEE06 §6/§6b.

(a) KIEM TINH BAT BIEN cua delta theo phi (bang SO, khong chi noi):
    phi la HANG SO tren cung mot ro => trong moi so sanh model-vs-model tren CUNG tap (tick, coin),
    delta PHAI gan nhu TRUNG NHAU o f=0.006 va f=0.008. Tinh TUONG MINH:
        net_round = gross8 - f  (moi arm)  ->  delta(f) = mean_{t chung}[(net_a) - (net_c)]
    (neu mo hinh phi SAI — vd nhan f theo K hoac theo so lenh — thi delta se lech theo f => ROT)

(b) VIEC 3: delta vs 2 doi chung BAT BUOC (A45 - 45deploy buoc RETRAIN; V5 - V1 buoc NHIEU) o f=0.006:
    phai ~0 va TRONG CI (thuoc hop le). Co muc KINH TE DUONG ngoai CI nao khong?

Dung NGUYEN MR.ci_mean (block 72h, NREP=2000, SEED=20260905) + inflate(k=5)=1.7941.
Chay: python3 fee_invariance_check.py --out docs/result/fee_invariance.json
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import model_ruler as MR                        # noqa: E402

CACHE = "/tmp/mrpnp/cache"
ARMS = ["MRA4", "MRB8", "MRB32"]
CTLS = ["45deploy", "A45", "V5", "A44"]
FEES = [0.004, 0.006, 0.008]
INFL5 = float(np.sqrt(2.0 * np.log(5.0)))


def load(arm, K):
    fs = sorted(glob.glob(os.path.join(CACHE, "%s_%d_*.parquet" % (arm, K))))
    if not fs:
        return None
    d = pd.concat([pd.read_parquet(f, columns=["ts", "gross8"]) for f in fs], ignore_index=True)
    d = d.dropna(subset=["ts", "gross8"])
    d["ts"] = d.ts.astype(np.int64)
    return d.groupby("ts", as_index=False).gross8.mean()


def mk(v, ts):
    ci = MR.ci_mean(np.asarray(v, np.float64), np.asarray(ts, np.int64), inflate=INFL5)
    mu = float(ci["mean"])
    raw = [float(x) for x in ci["raw"]]
    b5 = [float(x) for x in ci["honest_infl"]]
    return {"mean": round(mu, 10), "k5": [round(x, 10) for x in b5],
            "out_both": bool((raw[0] > 0 or raw[1] < 0) and (b5[0] > 0 or b5[1] < 0)),
            "dir": 1 if mu > 0 else -1, "n": int(ci["n"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/result/fee_invariance.json")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    out = {"cache": CACHE, "arms": ARMS, "controls": CTLS, "fees": FEES,
           "inflate_k5": round(INFL5, 6), "invariance": {}, "rule": {},
           "controls_validity": {}, "levels": {}}

    for K in (8, 32):
        for arm in ARMS:
            da = load(arm, K)
            for ctl in CTLS:
                dc = load(ctl, K)
                if da is None or dc is None:
                    continue
                m = da.merge(dc, on="ts", suffixes=("_a", "_c"))
                ts = m.ts.to_numpy(np.int64)
                ga = m.gross8_a.to_numpy(np.float64)
                gc = m.gross8_c.to_numpy(np.float64)
                rec = {"n_common": int(len(m))}
                deltas = {}
                for f in FEES:
                    # TUONG MINH: net moi vong = gross - f, roi moi ghep cap
                    na, nc = ga - f, gc - f
                    rec["d_net|c|%.3f" % f] = mk(na - nc, ts)
                    deltas[f] = rec["d_net|c|%.3f" % f]["mean"]
                # kiem bat bien: |d(0.006)-d(0.008)| va |d(0.006)-d(0.004)|
                rec["absdiff_006_008"] = abs(deltas[0.006] - deltas[0.008])
                rec["absdiff_006_004"] = abs(deltas[0.006] - deltas[0.004])
                rec["invariant"] = bool(rec["absdiff_006_008"] < 1e-12 and
                                        rec["absdiff_006_004"] < 1e-12)
                out["invariance"]["%s|%s|P%d" % (arm, ctl, K)] = rec

    for a1, a2 in (("A45", "45deploy"), ("V5", "V1")):
        rec = {}
        for K in (8, 32):
            d1 = load(a1, K)
            dc = load(a2, K)
            if d1 is None or dc is None:
                continue
            m = d1.merge(dc, on="ts", suffixes=("_a", "_c"))
            ts = m.ts.to_numpy(np.int64)
            f = 0.006
            dd = (m.gross8_a.to_numpy(np.float64) - f) - (m.gross8_c.to_numpy(np.float64) - f)
            r = mk(dd, ts)
            r["n_common"] = int(len(m))
            rec["P%d" % K] = r
        out["controls_validity"]["%s-%s" % (a1, a2)] = rec

    # muc gross8 theo arm (thuoc P32, K=32)
    for arm in ARMS + CTLS:
        d = load(arm, 32)
        if d is not None:
            out["levels"][arm] = round(float(d.gross8.mean()), 6)

    json.dump(out, open(a.out, "w"), indent=1, default=str)

    print("### KIEM TINH BAT BIEN cua delta theo phi (phai ~0)")
    print("  (d(f) = mean ghep cap [net_a(f) - net_c(f)] ; net = gross - f)")
    rows = []
    for k, r in out["invariance"].items():
        rows.append({"cap|thuoc": k, "n": r["n_common"],
                     "d@0.004": "%+.3e" % r["d_net|c|0.004"]["mean"],
                     "d@0.006": "%+.3e" % r["d_net|c|0.006"]["mean"],
                     "d@0.008": "%+.3e" % r["d_net|c|0.008"]["mean"],
                     "max|d006-d008|": "%.2e" % r["absdiff_006_008"],
                     "bat_bien": r["invariant"]})
    print(pd.DataFrame(rows).to_string(index=False))
    allinv = all(r["invariant"] for r in out["invariance"].values())
    print("\n  => TAT CA bat bien: %s (max |d(0.006)-d(0.008)| = %.2e)" % (
        allinv, max(r["absdiff_006_008"] for r in out["invariance"].values())))

    print("\n### VIEC 3 — delta vs 2 doi chung BAT BUOC o f=0,006 ('*' = ngoai CI k=5)")
    for k, r in out["controls_validity"].items():
        for pk, v in r.items():
            print("  %-18s %-4s n=%d d_net=%.3e CI5=[%.3e,%.3e] ngoai=%s" % (
                k, pk, v["n_common"], v["mean"], v["k5"][0], v["k5"][1], v["out_both"]))
    print("\n### MUC gross8 (K=8, P32) theo arm:", out["levels"])

    print("\n### KINH TE: delta glift8/gross8 (model-vs-model) o f=0.006 tren thuoc P32 (ngoai CI?)")
    any_out = False
    for k, r in out["invariance"].items():
        if not k.endswith("P32"):
            continue
        v = r["d_net|c|0.006"]
        tag = "OUT" if v["out_both"] else "trong CI"
        if v["out_both"]:
            any_out = True
        print("  %-20s n=%d d=%+.4e CI5=[%+.4e,%+.4e] %s" % (
            k, r["n_common"], v["mean"], v["k5"][0], v["k5"][1], tag))
    print("\n  => co muc KINH TE duong NGOAI CI nao (P32, f=0.006)? %s" % any_out)


if __name__ == "__main__":
    main()
