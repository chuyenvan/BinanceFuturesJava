#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PASS 2 — PHAN BO p15 THEO FEATURE (causal, AUDIT-ONLY).

Dung model fold_20 `Model_Regressor_Return15M.onnx` (33 feature, dung thu tu V3FULL — nhu PASS1 §3).
Voi moi dong live: y_live = f(X_live); y_dev_i = f(X_live nhung THAY feature i bang gia tri DEV cung phut).
  delta_i = y_dev_i - y_live  => dong gop cua feature i vao chenh p15 live vs DEV.
Voi momentum1M/15M/acceleration: DEV goc = 0 (thieu nguon) => dung gia tri TAI TAO INLINE (md_inline) — xem
`RESULT_FEATDIFF_PASS2.md` §1.2 (da kiem corr 0.995/0.9995 voi live).
"""
import sys, json
import numpy as np
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import featdiff_pass2 as P
import devexport_202609 as dx
from md_inline import InlineMD
import datetime

TZ7 = dx.TZ7
DAY = dx.DAY
MODEL = "/home/ubuntu/claudedata/wfo_models/fold_20/Model_Regressor_Return15M.onnx"


def inline_md_day(cluster, day_ms):
    store = dx.Store(cluster)
    gen = InlineMD(P.load_died())
    kl = store.get_kline_day(day_ms)
    parsed = {}
    for k, v in kl.items():
        try:
            ts = int(datetime.datetime.strptime(k, "%Y%m%d-%H%M").replace(tzinfo=TZ7).timestamp() * 1000)
        except Exception:
            continue
        parsed[ts] = v
    out = {}
    for ts in sorted(parsed.keys()):
        syms, arr = dx.parse_minute(parsed[ts])
        if not syms:
            continue
        snap = {s: (float(arr[i, 0]), float(arr[i, 1]), float(arr[i, 2]), float(arr[i, 3]))
                for i, s in enumerate(syms)}
        md = gen.update(snap)
        if md is not None:
            out[ts // 60000 * 60000] = md
    store.close()
    return out


def main():
    live = P.load_live()
    dev = P.load_dev("/home/ubuntu/claudedata/devexport_202609/devexport_20260701_20260928_FULL.csv.gz")
    F = P.FEATS
    dev_of_min = {}
    for i, m in enumerate(dev["min"]):
        dev_of_min[int(m)] = i
    # inline md cho ngay cua live
    t0 = min(r["min"] for r in live)
    md = inline_md_day("242", t0 // DAY * DAY)
    print("inline md minutes=%d (day %s)" % (len(md), datetime.datetime.fromtimestamp(t0 // DAY * DAY / 1000, TZ7).date()))

    import onnxruntime as ort
    sess = ort.InferenceSession(MODEL, providers=["CPUExecutionProvider"])
    nm = sess.get_inputs()[0].name

    Xl, Xd = [], []
    used = 0
    for r in live:
        mi = dev_of_min.get(r["min"], -1)
        mdi = md.get(r["min"])
        if mi < 0 or mdi is None:
            continue
        xl = np.array([r[n] for n in F], dtype=np.float32)
        xd = xl.copy()
        # 30 feature: lay tu export
        for j, n in enumerate(F):
            if n in ("momentum1M", "momentum15M", "momentumAcceleration"):
                continue
            xd[j] = np.float32(dev[n][mi])
        # momentum: tai tao inline
        xd[F.index("momentum1M")] = np.float32(mdi[0])
        xd[F.index("momentum15M")] = np.float32(mdi[2])
        xd[F.index("momentumAcceleration")] = np.float32(dev["momentum5M"][mi] - mdi[2])
        Xl.append(xl); Xd.append(xd); used += 1
    Xl = np.array(Xl); Xd = np.array(Xd)
    print("rows used=%d" % used)
    yl = sess.run(None, {nm: Xl})[0].reshape(-1).astype(np.float64)
    yd = sess.run(None, {nm: Xd})[0].reshape(-1).astype(np.float64)
    print("p15 live  mean=%.4f%% max=%.4f%%" % (yl.mean() * 100, yl.max() * 100))
    print("p15 dev-r mean=%.4f%% max=%.4f%%" % (yd.mean() * 100, yd.max() * 100))
    print("GAP(mean)=%.4f pp" % ((yd.mean() - yl.mean()) * 100))
    contrib = []
    for j, n in enumerate(F):
        Xs = Xl.copy(); Xs[:, j] = Xd[:, j]
        ys = sess.run(None, {nm: Xs})[0].reshape(-1).astype(np.float64)
        dl = ys - yl
        contrib.append((n, float(dl.mean() * 100), float(np.mean(Xl[:, j]) - np.mean(Xd[:, j]))))
    contrib.sort(key=lambda t: -abs(t[1]))
    print("\n%-24s %12s %14s" % ("feature", "d_p15(pp)", "dmean_live-dv"))
    for n, d, dm in contrib[:12]:
        print("%-24s %12.4f %14.3e" % (n, d, dm))
    RES = {"n": used, "p15_live_mean_pct": float(yl.mean() * 100), "p15_dev_mean_pct": float(yd.mean() * 100),
           "gap_pp": float((yd.mean() - yl.mean()) * 100),
           "contrib": [{"feature": n, "d_p15_pp": d, "dmean": dm} for n, d, dm in contrib]}

    # --- SO SANH momentum×3: LIVE vs TAI TAO INLINE (moi dong live co md) ---
    lm1, li1, lm15, li15, lma, lia = [], [], [], [], [], []
    for r in live:
        mdi = md.get(r["min"])
        if mdi is None:
            continue
        mi = dev_of_min.get(r["min"], -1)
        lm1.append(r["momentum1M"]); li1.append(mdi[0])
        lm15.append(r["momentum15M"]); li15.append(mdi[2])
        if mi >= 0:
            lma.append(r["momentumAcceleration"]); lia.append(dev["momentum5M"][mi] - mdi[2])
    lm1 = np.array(lm1); li1 = np.array(li1); lm15 = np.array(lm15); li15 = np.array(li15)
    print("\nMOMENTUM×3 LIVE vs INLINE (n=%d):" % len(lm1))
    print("  1M  meanAbsDiff=%.3e corr=%.4f (live_mean=%.6f inline=%.6f)" % (
        np.mean(np.abs(lm1 - li1)), np.corrcoef(lm1, li1)[0, 1], lm1.mean(), li1.mean()))
    print("  15M meanAbsDiff=%.3e corr=%.4f (live_mean=%.6f inline=%.6f)" % (
        np.mean(np.abs(lm15 - li15)), np.corrcoef(lm15, li15)[0, 1], lm15.mean(), li15.mean()))
    if lma:
        lma = np.array(lma); lia = np.array(lia)
        print("  ACC meanAbsDiff=%.3e corr=%.4f (live_mean=%.6f inline=%.6f)" % (
            np.mean(np.abs(lma - lia)), np.corrcoef(lma, lia)[0, 1], lma.mean(), lia.mean()))

    RES["momentum_inline"] = {
        "n": int(len(lm1)),
        "m1_meanAbsDiff": float(np.mean(np.abs(lm1 - li1))), "m1_corr": float(np.corrcoef(lm1, li1)[0, 1]),
        "m1_live_mean": float(lm1.mean()), "m1_inline_mean": float(li1.mean()),
        "m15_meanAbsDiff": float(np.mean(np.abs(lm15 - li15))), "m15_corr": float(np.corrcoef(lm15, li15)[0, 1]),
        "m15_live_mean": float(lm15.mean()), "m15_inline_mean": float(li15.mean())}
    if lma:
        lma = np.array(lma); lia = np.array(lia)
        RES["momentum_inline"].update({"acc_meanAbsDiff": float(np.mean(np.abs(lma - lia))),
                                       "acc_corr": float(np.corrcoef(lma, lia)[0, 1])})

    # --- SANITY: y_live vs cot p15_out cua dump ---
    p15o = np.array([r.get("p15_out", np.nan) for r in live], dtype=np.float64)
    keep = []
    for r in live:
        if dev_of_min.get(r["min"], -1) >= 0 and md.get(r["min"]) is not None:
            keep.append(True)
        else:
            keep.append(False)
    keep = np.array(keep)
    p15k = p15o[keep]
    ok = np.isfinite(p15k)
    print("SANITY y_live vs p15_out: n=%d maxAbsDiff_pp=%.3e corr=%.6f" % (
        int(ok.sum()), float(np.max(np.abs(yl[ok] - p15k[ok])) * 100),
        float(np.corrcoef(yl[ok], p15k[ok])[0, 1])))

    # --- p15 tren cua so EXPORT (2026-07->09) + mau gate15m (2021->2026-06) ---
    Xe = np.column_stack([dev[n] for n in F]).astype(np.float32)
    ye = sess.run(None, {nm: Xe})[0].reshape(-1).astype(np.float64)
    print("p15 EXPORT 2026-07..09 (n=%d): p50=%.3f%% p90=%.3f%% p99=%.3f%% max=%.3f%%" % (
        len(ye), np.percentile(ye, 50) * 100, np.percentile(ye, 90) * 100,
        np.percentile(ye, 99) * 100, ye.max() * 100))
    RES["p15_export_2026Q3"] = dict(n=int(len(ye)), p50=float(np.percentile(ye, 50) * 100),
                                    p90=float(np.percentile(ye, 90) * 100),
                                    p99=float(np.percentile(ye, 99) * 100), mx=float(ye.max() * 100))
    try:
        import pandas as pd
        fn = "/home/ubuntu/claudedata/gate15m_v2_full.csv"
        g = pd.read_csv(fn, usecols=F, nrows=None, skiprows=lambda i: i > 0 and i % 20 != 0)
        Xg = g[F].to_numpy(dtype=np.float32)
        yg = sess.run(None, {nm: Xg})[0].reshape(-1).astype(np.float64)
        print("p15 gate15m 2021..2026-06 (sample n=%d): p50=%.3f%% p99=%.3f%% max=%.3f%%" % (
            len(yg), np.percentile(yg, 50) * 100, np.percentile(yg, 99) * 100, yg.max() * 100))
        RES["p15_gate15m_sample"] = dict(n=int(len(yg)), p50=float(np.percentile(yg, 50) * 100),
                                         p99=float(np.percentile(yg, 99) * 100), mx=float(yg.max() * 100))
    except Exception as e:
        print("gate15m skip", str(e)[:80])

    with open("/tmp/pass2_p15.json", "w") as fh:
        json.dump(RES, fh, indent=1)
    print("\nwrote /tmp/pass2_p15.json")


if __name__ == "__main__":
    main()
