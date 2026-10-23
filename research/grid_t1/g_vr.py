#!/usr/bin/env python3
"""Step 0: Lo-MacKinlay variance ratio + lag-1 autocorrelation per asset/period."""
import json
import os
import sys
import numpy as np

WK = os.path.expanduser("~/claude_master/grid_t1_wk")
CACHE = os.path.join(WK, "cache")
TS0 = 1638316800000
MIN = 60000
QS = [5, 15, 60, 240, 1440]


def delta_arr(r1, qmax):
    x = r1 - r1.mean()
    x2 = x * x
    T = len(x)
    nfft = 1 << (2 * T - 1).bit_length()
    F = np.fft.rfft(x2, nfft)
    ac = np.fft.irfft(F * np.conj(F), nfft)[:qmax]
    return ac / (x2.sum() ** 2)


def vr_z(r1, q, delta):
    """r1: 1m log returns. Returns VR(q), z (Lo-MacKinlay robust)."""
    x = r1 - r1.mean()
    T = len(x)
    var1 = np.dot(x, x) / (T - 1)
    c = np.concatenate([[0.0], np.cumsum(x)])
    rq = c[q:] - c[:-q]
    mq = q * r1.mean()
    varq = np.sum((rq - mq) ** 2) / (len(rq) - 1)
    VR = varq / (q * var1)
    j = np.arange(1, q)
    theta = np.sum((2.0 * (q - j) / q) ** 2 * delta[1:q])
    z = (VR - 1.0) / np.sqrt(theta) if theta > 0 else 0.0
    return float(VR), float(z)


def ac1(r):
    if len(r) < 10:
        return float("nan")
    a, b = r[:-1], r[1:]
    if a.std() == 0:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def main():
    u = json.load(open(os.path.join(WK, "universe.json")))
    out = {}
    for per, a, b in (("E", "2022-01-01", "2024-01-01"), ("C", "2024-01-01", "2026-01-01")):
        i0 = int((np.datetime64(a, "ms").astype("int64") - TS0) // MIN)
        i1 = int((np.datetime64(b, "ms").astype("int64") - TS0) // MIN)
        syms = ["BTCUSDT", "ETHUSDT"] + u[per]["union"]
        res = {}
        for s in syms:
            f = os.path.join(CACHE, s + ".npz")
            if not os.path.exists(f):
                continue
            z = np.load(f)
            lo = max(i0, int(z["first"])); hi = min(i1, int(z["last"]) + 1)
            if hi - lo < 30 * 1440:
                continue
            c = z["c"][lo:hi].astype(np.float64)
            r1 = np.diff(np.log(c))
            rec = {"n_min": int(len(c)), "vr": {}, "ac1": {}}
            dl = delta_arr(r1, max(QS) + 1)
            for q in QS:
                v, zz = vr_z(r1, q, dl)
                rec["vr"][str(q)] = [round(v, 5), round(zz, 3)]
            for q in (5, 15, 60, 240, 1440):
                cc = c[::q]
                rec["ac1"][str(q)] = round(ac1(np.diff(np.log(cc))), 4)
            res[s] = rec
        out[per] = res
        sig = {q: np.mean([1 if res[s]["vr"][str(q)][1] < -1.96 else 0 for s in res]) for q in QS}
        med = {q: float(np.median([res[s]["vr"][str(q)][0] for s in res])) for q in QS}
        print(per, "n", len(res), "median VR", med, "frac sig<1", sig)
        out[per + "_summary"] = {"frac_z_lt_196": sig, "median_vr": med, "n_assets": len(res)}
    os.makedirs(os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/grid_t1"), exist_ok=True)
    json.dump(out, open(os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/grid_t1/vr.json"), "w"), indent=1)
    print("wrote vr.json")


if __name__ == "__main__":
    main()
