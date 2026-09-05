"""X1 GATES — cong byte-identical G1..G4 cua docs/PREREG_X1.md muc 2.
usage: x1_gates.py {g1|g2|g3|g4}
Moi cong in PASS/FAIL. FAIL => exit 1 (dung pipeline, khong chay sim)."""
import hashlib
import logging
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOG = logging.getLogger("x1gates")

TZ = 7 * 3600000
T_OLD_UTC = 1719792000000                 # 2024-07-01 UTC (mep T_END cu cua featv2)
T_OLD_LOC = int(pd.Timestamp("2024-07-01").value // 10 ** 6) - TZ   # mep T1 cu cua ledger
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d",
        "rk_ret_3d", "ret_14d", "ls_global", "rk_oi_delta24h"]
OLD_CUTS = ["20220101", "20220401", "20220701", "20221001", "20230101",
            "20230401", "20230701", "20231001", "20240101", "20240401"]


def verdict(ok, name):
    LOG.info("%s: %s", name, "PASS" if ok else "**FAIL**")
    if not ok:
        sys.exit(1)


def eq(a, b):
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    return bool(np.array_equal(a, b, equal_nan=True))


def g1():
    cols = ["ts", "sym"] + KEEP
    o = pd.read_parquet("/home/ubuntu/featv2/feat_v2.parquet", columns=cols)
    n = pd.read_parquet("/home/ubuntu/featv2/feat_v2_x1.parquet", columns=cols)
    LOG.info("featv2 cu %d dong (max ts %s) | x1 %d dong (max ts %s)", len(o),
             pd.to_datetime(o.ts.max(), unit="ms"), len(n), pd.to_datetime(n.ts.max(), unit="ms"))
    n = n[n.ts <= T_OLD_UTC]
    LOG.info("x1 cat toi 2024-07-01: %d dong", len(n))
    o = o.sort_values(["ts", "sym"], kind="stable").reset_index(drop=True)
    n = n.sort_values(["ts", "sym"], kind="stable").reset_index(drop=True)
    if len(o) != len(n):
        LOG.info("**so dong LECH** cu=%d x1=%d", len(o), len(n))
        so, sn = set(map(tuple, o[["ts", "sym"]].values)), set(map(tuple, n[["ts", "sym"]].values))
        LOG.info("chi trong cu=%d chi trong x1=%d", len(so - sn), len(sn - so))
        verdict(False, "G1 featv2")
    key = eq(o.ts, n.ts) and eq(o.sym, n.sym)
    bad = [c for c in KEEP if not eq(o[c], n[c])]
    for c in bad:
        d = (~(pd.isna(o[c]) & pd.isna(n[c]))) & (o[c] != n[c])
        LOG.info("  cot %s lech %d dong, max|d|=%s", c, int(d.sum()),
                 float(np.nanmax(np.abs((o[c] - n[c])[d]))) if d.any() else 0.0)
    verdict(key and not bad, "G1 featv2 (9 cot KEEP, ts<=2024-07-01)")


def g2():
    o = pd.read_parquet("/home/ubuntu/ledger/cand_dev.parquet")
    n = pd.read_parquet("/home/ubuntu/ledger/cand_dev_x1.parquet")
    LOG.info("ledger cu %d dong | x1 %d dong (max %s)", len(o), len(n),
             pd.to_datetime(n.ts.max(), unit="ms"))
    n = n[n.ts < T_OLD_LOC].reset_index(drop=True)
    LOG.info("x1 cat toi T1 cu: %d dong", len(n))
    if len(o) != len(n) or list(o.columns) != list(n.columns):
        LOG.info("**lech so dong/cot** %d/%d cols %s vs %s", len(o), len(n),
                 list(o.columns), list(n.columns))
        verdict(False, "G2 ledger")
    bad = []
    for c in o.columns:
        if o[c].dtype.kind in "fiub":
            if not eq(o[c], n[c]):
                bad.append(c)
        elif not o[c].equals(n[c]):
            bad.append(c)
    for c in bad:
        LOG.info("  cot %s LECH", c)
    verdict(not bad, "G2 ledger (moi cot, ts<T1 cu, cung thu tu)")


def g3():
    o = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2.parquet")
    n = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2x1.parquet")
    LOG.info("pred cu %d dong | x1 %d dong", len(o), len(n))
    n = n[n.ts <= o.ts.max()].reset_index(drop=True)
    o = o.sort_values(["ts", "sym"], kind="stable").reset_index(drop=True)
    n = n.sort_values(["ts", "sym"], kind="stable").reset_index(drop=True)
    if len(o) != len(n):
        LOG.info("**so dong LECH** cu=%d x1(cat)=%d", len(o), len(n))
        verdict(False, "G3 pred_s1a2")
    ok = eq(o.ts, n.ts) and eq(o.sym, n.sym) and eq(o.score, n.score)
    if not ok:
        d = o.score != n.score
        LOG.info("  score lech %d/%d dong, max|d|=%s", int(d.sum()), len(o),
                 float(np.abs(o.score - n.score).max()))
    verdict(ok, "G3 pred_s1a2 (10 fold cu, score bang tuyet doi)")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def g4():
    bad = []
    for c in OLD_CUTS:
        a = sha256("/home/ubuntu/predwf_map_s1a2/predict_wf_%s.bin" % c)
        b = sha256("/home/ubuntu/predwf_map_s1a2_x1/predict_wf_%s.bin" % c)
        LOG.info("  %s cu=%s x1=%s %s", c, a[:16], b[:16], "OK" if a == b else "**LECH**")
        if a != b:
            bad.append(c)
    verdict(not bad, "G4 bins map 10 fold cu (sha256)")


{"g1": g1, "g2": g2, "g3": g3, "g4": g4}[sys.argv[1]]()
