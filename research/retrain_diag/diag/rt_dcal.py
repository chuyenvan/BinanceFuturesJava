#!/usr/bin/env python3
"""rt_dcal.py - PREREG_RETRAIN_DIAG 436977c1 muc 2.2 D-cal (KHONG PnL, KHONG nhan). HOLDOUT_UNSEAL_2026_1121 (U4a).
p15 T1 (rt-chain-n26 pred26 c1b00ba9, ca nam 2026; Q1-Q2 la IN-SAMPLE cua T1) vs p15 live fold_20 (Lane L pred_2026) - cung file pred sim dung.
Phan vi duoi theo cua so; r-proxy = p15 / (max(0.26787, sp_best/0.15*1.28760) * 1.55), sp_best = 1 - max p0 cua tick 15' (ffill), bins
L (0101/0401/0701 Lane L) cho live va (0101/0401 L + 0701 Lane N) cho T1 - MO TA, khong phai bo dem gate that."""
import hashlib, json, logging, struct, sys
import numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
LG = logging.getLogger("dcal"); LG.info("HOLDOUT_UNSEAL_REF HOLDOUT_UNSEAL_2026_1121 (U4a)")
S0, S3, S4 = 1767200400000, 1782838800000, 1790787600000
Q2 = 1775034000000  # 2026-04-01 +07
D = 86400000
DSL = "/home/ubuntu/claude_master/w3/ho5/a3/data26/ds"
PN = "/home/ubuntu/claude_master/w3/retrain/out/k/rt-chain-n26/out/pred26/pred_2026.bin"
BN = "/home/ubuntu/claude_master/w3/retrain/out/a3n/ds/predict_wf_20260701.bin"
REC = np.dtype([("ts", ">i8"), ("p15", ">f4"), ("risk", ">f4")])
BR = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()
def rp(p):
    raw = open(p, "rb").read(); n = struct.unpack(">i", raw[:4])[0]; return np.frombuffer(raw[4:4 + 16 * n], dtype=REC)
def spbest(files):
    out = []
    for f in files:
        b = np.fromfile(f, dtype=BR)
        d = pd.DataFrame({"ts": b["ts"].astype("i8"), "p": b["p0"].astype("f8")})
        out.append(d.groupby("ts").p.max())
    s = pd.concat(out); s = s[~s.index.duplicated(keep="last")].sort_index()
    return 1.0 - s
QS = {"q99": .99, "q999": .999, "q9999": .9999, "q99995": .99995, "max": 1.0}
def qs(x):
    return {k: float(np.quantile(x, v)) for k, v in QS.items()}
assert md5(PN) == "c1b00ba995d26df2641e89180f96c204" and md5(DSL + "/pred_2026.bin") == "64f66a15e0c6d7268da805e3df428760"
n, l = rp(PN), rp(DSL + "/pred_2026.bin")
assert (n["ts"] == l["ts"]).all()
ts = n["ts"].astype(np.int64)
spL = spbest([DSL + "/predict_wf_2026%s01.bin" % m for m in ("01", "04", "07")])
spN = spbest([DSL + "/predict_wf_20260101.bin", DSL + "/predict_wf_20260401.bin", BN])
def ff(sp):
    idx = np.searchsorted(sp.index.values, ts, "right") - 1
    v = np.where(idx >= 0, sp.values[np.clip(idx, 0, None)], np.nan); return v
def r(p, sp):
    return p / (np.maximum(0.26787, sp / 0.15 * 1.28760) * 1.55)
rL, rN = r(l["p15"].astype("f8"), ff(spL)), r(n["p15"].astype("f8"), ff(spN))
W = {"2026Q1": (S0, Q2), "2026Q2_DEV_B1": (Q2, S3), "pre_S3_90d": (S3 - 90 * D, S3), "2026Q3": (S3, S4)}
res = {"inputs": {"p15_T1_md5": md5(PN), "p15_live_md5": md5(DSL + "/pred_2026.bin"), "note": "Q1-Q2 in-sample cho T1 (train toi S3-15')"}, "win": {}}
for k, (a, b) in W.items():
    m = (ts >= a) & (ts < b) & np.isfinite(rL) & np.isfinite(rN)
    pT, pL = n["p15"][m].astype("f8"), l["p15"][m].astype("f8")
    e = {"n_min": int(m.sum()), "p15_T1": qs(pT), "p15_live": qs(pL), "r_T1": qs(rN[m]), "r_live": qs(rL[m])}
    e["ratio_p15_T1_over_live"] = {q: e["p15_T1"][q] / e["p15_live"][q] for q in QS}
    e["ratio_r_T1_over_live"] = {q: e["r_T1"][q] / e["r_live"][q] for q in QS}
    # dem vuot nguong: so phut r_T1 > q99995(r_live cua cua so) (mo ta muc tran)
    thr = e["r_live"]["q99995"]
    e["exceed_live_q99995"] = {"T1": int((rN[m] > thr).sum()), "live": int((rL[m] > thr).sum())}
    res["win"][k] = e
w = res["win"]["2026Q2_DEV_B1"]
res["B1_cal"] = {"ratio_q9999_p15_Q2": w["ratio_p15_T1_over_live"]["q9999"], "ratio_q9999_r_Q2": w["ratio_r_T1_over_live"]["q9999"],
                 "ratio_q9999_p15_Q3": res["win"]["2026Q3"]["ratio_p15_T1_over_live"]["q9999"],
                 "cond_Q2_p15": bool(w["ratio_p15_T1_over_live"]["q9999"] >= 1.2 or w["ratio_p15_T1_over_live"]["q9999"] <= 0.83)}
json.dump(res, open(sys.argv[1], "w"), indent=1)
LG.info("DCAL %s", json.dumps(res["B1_cal"]))
