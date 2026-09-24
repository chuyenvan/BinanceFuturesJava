"""Cong REPRO cua docs/prereg/PREREG_G1.md muc 2: so bins G4_repro voi predwf_G015_v2.

usage: python3 g1_repro_check.py <dir_moi> <dir_goc>
PRIMARY: spearman(pred_moi, pred_goc) tren toan bo ban ghi 10 fold, khop theo (ts,symId).
< 0.99 => DUNG TOAN BO.
"""
import glob
import hashlib
import json
import logging
import os
import sys

import numpy as np
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    stream=sys.stdout)
log = logging.getLogger("repro")
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"),
               ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def main():
    dn, dg = sys.argv[1], sys.argv[2]
    fs = sorted(os.path.basename(f) for f in glob.glob(dg + "/predict_wf_*.bin"))
    fs = [f for f in fs if f[11:19] <= "20240401"]
    assert len(fs) == 10, "khong phai 10 fold: %d" % len(fs)
    pn, pg, same, rows = [], [], 0, {}
    for b in fs:
        fa, fb = dn + "/" + b, dg + "/" + b
        assert os.path.exists(fa), "thieu %s" % fa
        ha, hb = sha256(fa), sha256(fb)
        ok = ha == hb
        same += int(ok)
        a = np.fromfile(fa, dtype=DT)
        g = np.fromfile(fb, dtype=DT)
        assert len(a) == len(g), "%s lech so rec %d vs %d" % (b, len(a), len(g))
        assert np.array_equal(a["ts"], g["ts"]) and np.array_equal(a["sym"], g["sym"]), \
            "%s lech (ts,symId)" % b
        va, vg = a["p0"].astype(np.float64), g["p0"].astype(np.float64)
        r = float(spearmanr(va, vg).correlation)
        mx = float(np.abs(va - vg).max())
        rows[b] = {"rec": int(len(a)), "sha_khop": ok, "spearman": r, "max_abs_dp": mx,
                   "sha_moi": ha, "sha_goc": hb}
        log.info("%s rec=%d sha_khop=%s spearman=%.8f max|dp|=%.3e", b, len(a), ok, r, mx)
        pn.append(va)
        pg.append(vg)
        del a, g
    va, vg = np.concatenate(pn), np.concatenate(pg)
    del pn, pg
    rho = float(spearmanr(va, vg).correlation)
    ident = bool(np.array_equal(va, vg))
    log.info("TONG %d ban ghi | spearman=%.8f | byte-identical %d/10 | array_equal=%s",
             len(va), rho, same, ident)
    out = {"spearman_all": rho, "n": int(len(va)), "sha_identical_folds": same,
           "array_equal": ident, "pass": bool(rho >= 0.99), "folds": rows}
    json.dump(out, open("/home/ubuntu/g72/g1_repro.json", "w"), indent=1)
    log.info("CONG REPRO: %s (nguong 0.99)", "PASS" if rho >= 0.99 else "FAIL - DUNG TOAN BO")


if __name__ == "__main__":
    main()
