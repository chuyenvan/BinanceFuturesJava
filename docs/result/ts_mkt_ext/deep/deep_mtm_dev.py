#!/usr/bin/env python3
"""TS_MKT_EXT DEEP - buoc A: MTM phut (legacy, gia Vision) cho 16 run DEV, GHI LAI chuoi equity phut.
gvz_mtm import TRUOC (patch R -> Vision). Tu kiem: ket qua dd_total/dd_win/dd_year == tsx/mtm_vision.json.
Out: ~/claude_master/tsx/deep_cache/eq_dev.npz (eq[tag] float32 theo phut UTC tu DAY0) + mtm_check_dev.json
"""
import json
import logging
import os
import sys

import numpy as np

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402  (PHAI truoc R)
import reset_rule_score as R  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("deep_mtm_dev")
C = "/home/ubuntu/claude_master/tsx/deep_cache"
SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
KEYS = {}
for s in SEEDS:
    KEYS["OFF_" + s] = "gqsf-" + s.lower()
    KEYS["X14_" + s] = "tsx-x14-" + s.lower()
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
    assert R._work is MT._work_vision, "gvz_mtm chua patch R"
    os.makedirs(C, exist_ok=True)
    R.MTMState = Rec
    legs = {k: R.load_legs(t) for k, t in KEYS.items()}
    md5 = {k: R.md5_of(t) for k, t in KEYS.items()}
    out = R.run_mtm(legs, workers=3, chunk=30)
    assert len(REG) == len(KEYS)
    ref = json.load(open("/home/ubuntu/claude_master/tsx/mtm_vision.json"))
    chk = {}
    arrs = {}
    for (k, t), st in zip(legs.items(), REG):
        lg = out[k]["legacy"]
        r = ref[k]
        dif = max(abs(lg["dd_total"] - r["legacy"]["dd_total"]), abs(lg["dd_win"] - r["legacy"]["dd_win"]),
                  max(abs(lg["dd_year"][int(y)] - v) for y, v in r["legacy"]["dd_year"].items()))
        chk[k] = dict(tag=KEYS[k], md5=md5[k], md5_ref=r.get("md5"), md5_ok=md5[k] == r.get("md5"),
                      missing=lg["missing"], dd_total=lg["dd_total"], dd_win=lg["dd_win"], max_abs_diff_vs_ref=dif)
        ms = sorted(st.rec)
        assert all(b - a == 1440 for a, b in zip(ms, ms[1:])), "ngay khong lien tuc"
        arrs[k] = np.concatenate([st.rec[m] for m in ms])
        arrs[k + "__m0"] = np.array([ms[0]], np.int64)
        log.info("CHK %s %s", k, chk[k])
    assert all(c["missing"] == 0 for c in chk.values()), "MTM thieu gia"
    np.savez(C + "/eq_dev.npz", **arrs)
    json.dump(dict(day0=R.DAY0, cap0=R.CAP0, check=chk, ok=all(c["md5_ok"] and c["max_abs_diff_vs_ref"] < 1e-6
                                                             for c in chk.values())),
              open(C + "/mtm_check_dev.json", "w"), indent=1)
    log.info("DONE ok=%s", all(c["md5_ok"] and c["max_abs_diff_vs_ref"] < 1e-6 for c in chk.values()))


if __name__ == "__main__":
    main()
