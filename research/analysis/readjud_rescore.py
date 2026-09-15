"""AUDIT: cham LAI vong re-adjudication goc bang cac he so CI khac nhau.

KHONG chay sim moi, KHONG sua c3_rates.py. Dung DUNG printDone.csv cu (md5 khop doc goc),
dung DUNG may bootstrap block-72h/2000rep/seed cua x1_rates.ci_pair_df; CHI doi buoc cuoi
(he so noi rong CI) de xem ket luan co ben khong.
"""
import math, sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

BASE = "X1_C3_FULL_2021"
VARIANTS = ["X1_GS_T170_2021", "X1_GS_T130_2021"]
QUALITY = ("win", "tsloss", "meanP")            # luat thang cua du an
# huong TOT cho VARIANT, voi hieu = variant - baseline
GOOD = {"win": +1, "tsloss": -1, "meanP": +1, "mp_sm": +1, "mp_sl": +1}

def raw_ci(da, db):
    """Tra ve (obs, lo_raw, hi_raw) CHUA nhan he so — y het x1_rates.ci_pair_df truoc buoc inflate."""
    blocks = np.union1d(da.blk.unique(), db.blk.unique())
    ga = {k: v for k, v in da.groupby("blk")}
    gb = {k: v for k, v in db.groupby("blk")}
    rng = np.random.default_rng(C.SEED)
    obs = {k: C.rates(da)[k] - C.rates(db)[k] for k in C.KEYS}
    draws = {k: [] for k in C.KEYS}
    for _ in range(C.NREP):
        pick = rng.choice(blocks, size=len(blocks), replace=True)
        la = [ga[b] for b in pick if b in ga]
        lb = [gb[b] for b in pick if b in gb]
        ra = C.rates(pd.concat(la) if la else da.iloc[:0])
        rb = C.rates(pd.concat(lb) if lb else db.iloc[:0])
        for k in C.KEYS:
            draws[k].append(ra[k] - rb[k])
    out = {}
    for k in C.KEYS:
        arr = np.asarray(draws[k], float); arr = arr[np.isfinite(arr)]
        lo, hi = np.percentile(arr, [2.5, 97.5])
        out[k] = (obs[k], lo, hi)
    return out

FACTORS = [("1.000 (khong multiplicity)", 1.0),
           ("1.177 = sqrt(2 ln 2)  k=2 [PREREG goc]", math.sqrt(2*math.log(2))),
           ("1.210 = HANG SO DA DUNG (~k=2.08)", 1.21),
           ("1.482 = sqrt(2 ln 3)  k=3", math.sqrt(2*math.log(3))),
           ("1.665 = sqrt(2 ln 4)  k=4", math.sqrt(2*math.log(4))),
           ("2.039 = sqrt(2 ln 8)  k=8", math.sqrt(2*math.log(8)))]

db = C.trades(BASE)
for v in VARIANTS:
    da = C.trades(v)
    r = raw_ci(da, db)
    print("=" * 96)
    print("%s  -  %s   (hieu = variant - baseline; n_var=%d n_base=%d)" % (v, BASE, len(da), len(db)))
    print("  Sanity vs doc goc (he so 1.21):")
    for k in ("win", "tsloss", "mp_sl", "meanP"):
        o, lo, hi = r[k]
        c = (lo+hi)/2.0
        print("    %-8s hieu %+8.3f  CI [%+8.3f, %+8.3f]" % (k, o, c-(c-lo)*1.21, c+(hi-c)*1.21))
    print()
    print("  %-42s | %s | %s" % ("he so noi rong CI", "rate CHAT LUONG ngoai CI huong TOT", "chi tiet"))
    for name, f in FACTORS:
        good = []; bad = []
        for k in QUALITY:
            o, lo, hi = r[k]
            c = (lo+hi)/2.0; l2, h2 = c-(c-lo)*f, c+(hi-c)*f
            if not (l2 <= 0 <= h2):
                (good if o*GOOD[k] > 0 else bad).append("%s=%+.3f[%+.3f,%+.3f]" % (k, o, l2, h2))
        print("  %-42s |  %d TOT / %d XAU %-14s | %s" % (
            name, len(good), len(bad),
            "=> THANG" if len(good) >= 2 else "=> duoi nguong",
            "; ".join(good) if good else "-"))
    print()
