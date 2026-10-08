#!/usr/bin/env python3
"""HO1 B8 hieu chuan net015 (pre-reg 35d03784 §4) — CHI tren DEV 2025Q4.
sp' = bins fold 20251001 dung lai bang x1_build_map tu net015 f18-retrain (cung kernel GPU cut20251231, OOS 2025Q4)
+ S1 DEV (pred_s1a2x1); sp = bins DEV goc (predwf_map_s1a2_x1_2021). M-cal1 mo ta; funding_cal.bin cho kernel CAL (M-cal2).
Usage: python3 ho1_cal.py"""
import glob
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import ho1_funding_build as FB  # noqa: E402

H = "/home/ubuntu/claude_master/1003/ho1"
C = H + "/cal"
KGB = "/home/ubuntu/kg015x26_cut20251231/g015x26-cut20251231-gpu/out/predict_wf_20251001.bin"
DT = FB.DT
X1 = "/home/ubuntu/src/BinanceFuturesJava/research/pipeline/x1"


def factor(sp):
    return np.maximum(0.26787, sp / 0.15 * 1.28760)


def main():
    os.makedirs(C + "/g015", exist_ok=True)
    os.makedirs(C + "/bins", exist_ok=True)
    if not os.path.lexists(C + "/g015/predict_wf_20251001.bin"):
        os.symlink(KGB, C + "/g015/predict_wf_20251001.bin")
    env = dict(os.environ, X1_CUTS="20251001", X1_G015_DIR=C + "/g015")
    r = subprocess.run(["python3", "-u", X1 + "/x1_build_map.py", "s1a2x1", C + "/bins"], env=env, capture_output=True, text=True)
    assert "MAP_OK" in r.stdout, r.stdout[-2000:] + r.stderr[-2000:]
    o = np.fromfile(FB.DEV_BINS + "/predict_wf_20251001.bin", dtype=DT)
    n = np.fromfile(C + "/bins/predict_wf_20251001.bin", dtype=DT)
    same = len(o) == len(n) and np.array_equal(o["ts"], n["ts"]) and np.array_equal(o["sym"], n["sym"])
    m1 = dict(keys_equal=bool(same), n=int(len(o)))
    if same:
        p, q = o["p0"].astype(np.float64), n["p0"].astype(np.float64)
        sp, sq = 1 - p, 1 - q                       # symbolPred = score = 1 - P(win) (encode funding.bin)
        qs = [5, 25, 50, 75, 95]
        m1.update(pwin_q_orig=list(np.round(np.percentile(p, qs), 5)), pwin_q_cal=list(np.round(np.percentile(q, qs), 5)),
                  share_sp_le_029_orig=float((sp <= 0.29).mean()), share_sp_le_029_cal=float((sq <= 0.29).mean()),
                  hinge029_flip=float(((sp <= 0.29) != (sq <= 0.29)).mean()),
                  share_sp_le_kink_orig=float((sp <= 0.031207).mean()), share_sp_le_kink_cal=float((sq <= 0.031207).mean()),
                  median_abs_log_factor=float(np.median(np.abs(np.log(factor(sq) / factor(sp))))),
                  p90_abs_log_factor=float(np.percentile(np.abs(np.log(factor(sq) / factor(sp))), 90)),
                  spearman_all=float(__import__("scipy.stats").stats.spearmanr(p, q).correlation))
    json.dump(m1, open(C + "/m_cal1.json", "w"), indent=1)
    print("M-cal1", json.dumps(m1))
    fs = sorted(glob.glob(FB.DEV_BINS + "/predict_wf_*.bin"))
    fs = [C + "/bins/predict_wf_20251001.bin" if f.endswith("20251001.bin") else f for f in fs]
    u, cnt, blocks, meta = FB.load_bins(fs)
    grid = FB.market_keys(FB.DEV_DS + "/market.bin")
    out = C + "/funding_cal.bin"
    with open(out, "wb") as f:
        nrec, nb, ns, off7 = FB.emit(u, cnt, blocks, grid, FB.SEAL_UTC, f.write, seal7_track=True)
    res = dict(n=nrec, md5=FB.md5f(out), bytes=os.path.getsize(out), bins=[m["name"] + ":" + m["md5"] for m in meta])
    json.dump(res, open(out + ".json", "w"), indent=1)
    d = H + "/kaggle/ho26-cal-funding"
    os.makedirs(d, exist_ok=True)
    if os.path.lexists(d + "/funding.bin"):
        os.remove(d + "/funding.bin")
    os.link(out, d + "/funding.bin")
    json.dump({"title": "ho26-cal-funding", "id": "chuyendinh/ho26-cal-funding", "licenses": [{"name": "CC0-1.0"}]},
              open(d + "/dataset-metadata.json", "w"))
    print("CAL funding", json.dumps({k: v for k, v in res.items() if k != "bins"}))


if __name__ == "__main__":
    main()
