#!/usr/bin/env python3
"""GOLIVE_QUARTERLY buoc A (DEV): MTM phut legacy (gia close 1m Vision) cho 8 run X14 DEV (tsx-x14-*), ghi equity phut.
gvz_mtm import TRUOC reset_rule_score (patch nguon gia) -> assert R._work is MT._work_vision; assert missing == 0 moi run.
Tai lap CAGR22/DD22 (n700.arm_metrics, = TSX_V3_JAVA score.py) de doi chieu so cong bo. So voi cache deep_cache/eq_dev.npz.
Out: ~/claude_master/golive_quarterly_wk/{eq_dev.npz, mtm_dev.json}. KHONG chay lai sim.
"""
import json
import logging
import os
import sys

import numpy as np

sys.path.insert(0, "/home/ubuntu/claude_master/tsx")
import tsx_driver as T  # noqa: E402,F401  (path src/research/analysis cho n700/F3)
sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402  (PHAI truoc R)
import reset_rule_score as R  # noqa: E402
import flat3_crashpen_driver as F3  # noqa: E402
import n700_driver as N  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("gq_mtm_dev")
WK = "/home/ubuntu/claude_master/golive_quarterly_wk"
SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
KEYS = {"X14_" + s: "tsx-x14-" + s.lower() for s in SEEDS}
REG = []


class Rec(MT.MTMStateD):
    def __init__(self):
        super().__init__()
        self.rec = {}
        REG.append(self)

    def feed(self, m_global, eq):
        super().feed(m_global, eq)
        self.rec[int(m_global)] = np.asarray(eq["legacy"], np.float32).copy()


def main():
    assert R._work is MT._work_vision, "gvz_mtm chua patch R (thu tu import sai)"
    os.makedirs(WK, exist_ok=True)
    R.MTMState = Rec
    legs = {k: R.load_legs(t) for k, t in KEYS.items()}
    daily = {k: R.load_daily(t) for k, t in KEYS.items()}
    out = R.run_mtm(legs, workers=3, chunk=30)
    assert len(REG) == len(KEYS), (len(REG), len(KEYS))
    miss = {k: int(out[k]["legacy"]["missing"]) for k in KEYS}
    log.info("MISSING %s", miss)
    assert all(v == 0 for v in miss.values()), "MTM thieu gia: %s" % miss
    for k, t in KEYS.items():
        N.TAG[k], N.DESC[k] = t, "GOLIVE_QUARTERLY " + k
    M = {k: N.arm_metrics(R, F3, k, legs[k], daily[k], out[k]["legacy"]) for k in KEYS}
    ref = json.load(open("/home/ubuntu/claude_master/tsx/mtm_vision.json"))
    cache = np.load("/home/ubuntu/claude_master/tsx/deep_cache/eq_dev.npz")
    arrs, chk = {}, {}
    for k, st in zip(legs, REG):
        t = KEYS[k]
        ms = sorted(st.rec)
        assert all(b - a == 1440 for a, b in zip(ms, ms[1:])), "ngay khong lien tuc"
        e = np.concatenate([st.rec[m] for m in ms]).astype(np.float64)
        arrs[k] = e
        arrs[k + "__m0"] = np.array([ms[0]], np.int64)
        sp = float(legs[k]["pnl"].sum())
        c, m0c = cache[k].astype(np.float64), int(cache[k + "__m0"][0])
        cdif = float(np.abs(c - e).max()) if (m0c == ms[0] and len(c) == len(e)) else float("inf")
        lg, rr = out[k]["legacy"], ref[k]["legacy"]
        chk[k] = dict(tag=t, md5=R.md5_of(t), md5_ref=ref[k].get("md5"), missing=int(lg["missing"]), n_legs=int(len(legs[k])),
                      m0=int(ms[0]), n_min=int(len(e)), eq_last=float(e[-1]), cap0_plus_sumpnl=float(R.CAP0) + sp,
                      dd_total=float(lg["dd_total"]), dd_win=float(lg["dd_win"]),
                      ref_diff=float(max(abs(lg["dd_total"] - rr["dd_total"]), abs(lg["dd_win"] - rr["dd_win"]))),
                      cache_maxabs=cdif, cagr22=float(M[k]["cagr22"]), dd22=float(M[k]["dd_mtm22"]), sum_pnl=float(M[k]["sum_pnl"]),
                      calmar22=float(M[k]["calmar22"]))
        log.info("CHK %s %s", k, chk[k])
    np.savez(WK + "/eq_dev.npz", **arrs)
    c22 = [v["cagr22"] for v in chk.values()]
    d22 = [v["dd22"] for v in chk.values()]
    res = dict(day0=str(R.DAY0), cap0=float(R.CAP0), check=chk, cagr22_mean=float(np.mean(c22)), cagr22_median=float(np.median(c22)),
               dd22_mean=float(np.mean(d22)), dd22_median=float(np.median(d22)),
               ok=bool(all(v["missing"] == 0 and v["ref_diff"] < 1e-6 and v["md5"] == v["md5_ref"] and v["cache_maxabs"] < 1e-3
                           and abs(v["eq_last"] - v["cap0_plus_sumpnl"]) < 0.1 for v in chk.values())))
    json.dump(res, open(WK + "/mtm_dev.json", "w"), indent=1)
    log.info("DONE ok=%s CAGR22 mean %.3f med %.3f DD22 mean %.3f med %.3f", res["ok"], res["cagr22_mean"], res["cagr22_median"],
             res["dd22_mean"], res["dd22_median"])


if __name__ == "__main__":
    main()
