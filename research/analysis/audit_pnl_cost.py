#!/usr/bin/env python3
"""audit_pnl_cost.py — VIỆC 2 của PREREG_AUDIT_PNL: audit MÔ HÌNH PHÍ + ĐỘ NHẠY THEO PHÍ.

Chấm LẠI từ bins thô (không dùng lại JSON của vòng trước) ở các mức phí CHỐT TRƯỚC
`f ∈ {0,001 · 0,002 · 0,004 · 0,006 · 0,008 · 0,012}`:
  `y(f) = gross − f`  ·  `yb(f) = (y(f) > 0)`  ·  dùng NGUYÊN `model_ruler.tick_metrics/summarize/delta/ci_mean`
  (khối 72h, NREP=2000, SEED=20260905; chuẩn CHẶT 1,21 — KHÔNG nới).
Thước: `P32` = pool top-32 S1 (chọn thật top-8).
Chỉ ĐỌC. Không train/sim/push.
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import model_ruler as MR                        # noqa: E402
import audit_pnl_lib as A                       # noqa: E402

os.makedirs(A.OUT, exist_ok=True)
T0 = time.time()
FEES = [0.001, 0.002, 0.004, 0.006, 0.008, 0.012]
ARMS = {"45deploy": "/home/ubuntu/claudedata/predwf_G015x26",
        "A45": "/home/ubuntu/ruler_bins/g015p2-arm44-gpu/stage2/A45",
        "V5": "/home/ubuntu/ruler_bins/g015p2-stage2-featvar-gpu/stage2/V5",
        "V1": "/home/ubuntu/ruler_bins/g015p2-stage2-featvar-gpu/stage2/V1",
        "MRA4": "/tmp/mrbins/MRA4", "MRB8": "/tmp/mrbins/MRB8", "MRB32": "/tmp/mrbins/MRB32"}
CTL = ["45deploy", "A45", "V5"]
M = ["ic", "pacc", "dec_mono", "glift8", "gross8", "gross_all", "netm8", "netbase", "auc8c", "n8"]
K = 32
LABEL_REF = A.LABEL


def label_keys(K):
    d = pd.read_parquet(LABEL_REF, columns=["ts", "symId", "rank", "gross"])
    if K:
        d = d[d["rank"] < K]
    key = d.ts.to_numpy(np.int64) * 1024 + d.symId.to_numpy(np.int64)
    o = np.argsort(key, kind="stable")
    return key[o], d.gross.to_numpy(np.float64)[o]


LK, YV = label_keys(K)


def fold_frame(bd, f):
    bp = os.path.join(bd, "predict_wf_%s.bin" % f)
    if not os.path.exists(bp):
        return None
    arr = np.fromfile(bp, dtype=MR.BIN_DT)
    ts = arr["ts"].astype(np.int64)
    sy = arr["sym"].astype(np.int64)
    p = arr["p"].astype(np.float32).astype(np.float64)
    key = ts * 1024 + sy
    ip = np.clip(np.searchsorted(LK, key), 0, len(LK) - 1)
    hit = LK[ip] == key
    y = np.full(len(key), np.nan)
    y[hit] = YV[ip[hit]]
    m = hit & np.isfinite(p) & np.isfinite(y)
    return ts[m], p[m], y[m]


def main():
    res = {"meta": {"fees": FEES, "K": K, "arms": list(ARMS), "controls": CTL,
                    "ci": "block72h NREP=2000 SEED=20260905, chuan CHAT 1.21 (khong noi)",
                    "y": "gross - f ; yb = (gross - f) > 0", "n_label_rows": int(len(YV))},
           "per_fee": {}}
    for f in FEES:
        T = {}
        for arm, bd in ARMS.items():
            rows = []
            for fo in MR.FOLDS:
                fr = fold_frame(bd, fo)
                if fr is None:
                    continue
                ts, p, y = fr
                yy = y - f
                R, _ = MR.tick_metrics(ts, p, yy, (yy > 0).astype(np.float64))
                R["fold"] = fo
                rows.append(R)
            T[arm] = pd.concat(rows, ignore_index=True) if rows else None
            A.log("f=%.3f %-9s n_tick=%s (%.0fs)", f, arm,
                  None if T[arm] is None else len(T[arm]), time.time() - T0)
            del rows
        ent = {"summary": {}, "delta": {}}
        for arm, d in T.items():
            if d is None:
                continue
            s = MR.summarize(d, arm, M, MR.C.inflate(3))
            # LUU Y: `tick_metrics` da cham tren `y = gross - f` => `d.gross8` CHINH LA net@f
            # (KHONG duoc tru f lan nua — loi nay da bi bat khi kiem cheo voi RESULT_PNL_RULER).
            g8 = float(d.gross8.mean())
            p8 = MR.ci_mean(d.gross8.to_numpy(), d.ts.to_numpy(), MR.C.inflate(3))
            ent["summary"][arm] = {
                "n_tick": int(len(d)),
                "metrics": {m: dict(mean=round(float(s["metrics"][m]["mean"]), 6),
                                    raw=[round(float(x), 6) for x in s["metrics"][m]["raw"]],
                                    infl=[round(float(x), 6) for x in s["metrics"][m]["infl"]])
                            for m in M if m in s["metrics"]},
                "gross8_at_f0": round(g8 + f, 6),
                "netm8_mean": round(g8, 6),
                "netm8_ci_raw": [round(float(p8["raw"][0]), 6), round(float(p8["raw"][1]), 6)],
                "netm8_ci_121": [round(float(p8["infl"][0]), 6), round(float(p8["infl"][1]), 6)],
                "netm8_outside_raw": bool(p8["raw"][0] > 0 or p8["raw"][1] < 0),
                "netm8_outside_121": bool(p8["infl"][0] > 0 or p8["infl"][1] < 0),
            }
        for arm in [x for x in ARMS if x not in CTL]:
            for c in CTL:
                if T.get(arm) is None or T.get(c) is None:
                    continue
                dl = MR.delta(T[arm], T[c], M, "%s-%s" % (arm, c))
                ent["delta"]["%s-%s" % (arm, c)] = {
                    "n_tick_common": dl["n_tick_common"],
                    "metrics": {m: dict(mean=round(float(v["mean"]), 6),
                                        raw=[round(float(x), 6) for x in v["raw"]],
                                        infl=[round(float(x), 6) for x in v["infl"]],
                                        out_both=bool(v["out_both"]), dir=int(v["direction"]))
                                for m, v in dl["metrics"].items()},
                }
        res["per_fee"]["%.3f" % f] = ent
        A.log("f=%.3f XONG (%.0fs)", f, time.time() - T0)
        del T

    # ---- kiểm cấu trúc: Δglift8 có BẤT BIẾN theo f không ----
    inv = {}
    for pair in sorted(set(k for ff in res["per_fee"].values() for k in ff["delta"])):
        vals = [res["per_fee"]["%.3f" % f]["delta"][pair]["metrics"]["glift8"]["mean"]
                for f in FEES if pair in res["per_fee"]["%.3f" % f]["delta"]]
        inv[pair] = dict(values=vals, spread=round(max(vals) - min(vals), 9),
                         invariant=bool(max(vals) - min(vals) < 1e-9))
    res["invariance_dglift8"] = inv
    res["invariance_dpacc"] = {
        pair: [res["per_fee"]["%.3f" % f]["delta"][pair]["metrics"]["pacc"]["mean"]
               for f in FEES if pair in res["per_fee"]["%.3f" % f]["delta"]]
        for pair in sorted(set(k for ff in res["per_fee"].values() for k in ff["delta"]))}
    # ---- netm8 theo phí + ngưỡng f* ----
    net = {}
    for arm in ARMS:
        ser = []
        for f in FEES:
            s = res["per_fee"]["%.3f" % f]["summary"].get(arm)
            if s:
                ser.append(dict(f=f, mean=s["netm8_mean"], raw=s["netm8_ci_raw"],
                                c121=s["netm8_ci_121"], out_raw=s["netm8_outside_raw"],
                                out121=s["netm8_outside_121"]))
        net[arm] = ser
    res["netm8_by_fee"] = net
    json.dump(res, open(os.path.join(A.OUT, "cost.json"), "w"), indent=1, default=str)
    A.log("WRITE %s/cost.json (%.0fs)", A.OUT, time.time() - T0)


if __name__ == "__main__":
    main()
