"""Cham diem chuan: block-72h paired bootstrap + he so multiplicity DUNG sqrt(2 ln k),
+ rang buoc cung THEO NAM (maxDD<=15, UW<=120, return nam>=0, return quy>=-5).

Usage: python3 score_k.py --k 2 --base TAG_BASE TAG_VAR [TAG_VAR ...]
KHONG sua c3_rates.py (giu 1.21 cho cac doc cu tai lap duoc).
"""
import argparse, math, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

QUALITY = ("win", "tsloss", "meanP")
GOOD = {"win": +1, "tsloss": -1, "meanP": +1}     # huong TOT cho variant (hieu = var - base)

def raw_ci(da, db):
    blocks = np.union1d(da.blk.unique(), db.blk.unique())
    ga = {k: v for k, v in da.groupby("blk")}; gb = {k: v for k, v in db.groupby("blk")}
    rng = np.random.default_rng(C.SEED)
    obs = {k: C.rates(da)[k] - C.rates(db)[k] for k in C.KEYS}
    draws = {k: [] for k in C.KEYS}
    for _ in range(C.NREP):
        pick = rng.choice(blocks, size=len(blocks), replace=True)
        la = [ga[b] for b in pick if b in ga]; lb = [gb[b] for b in pick if b in gb]
        ra = C.rates(pd.concat(la) if la else da.iloc[:0])
        rb = C.rates(pd.concat(lb) if lb else db.iloc[:0])
        for k in C.KEYS: draws[k].append(ra[k] - rb[k])
    out = {}
    for k in C.KEYS:
        arr = np.asarray(draws[k], float); arr = arr[np.isfinite(arr)]
        lo, hi = np.percentile(arr, [2.5, 97.5]); out[k] = (obs[k], lo, hi)
    return out

def per_year(tag):
    s = C.equity(tag); d = C.trades(tag); rows = []
    for y, seq in s.groupby(s.index.year):
        dd = (seq / seq.cummax() - 1) * 100
        uw = seq < seq.cummax()
        uwmax = int(uw.groupby((~uw).cumsum()).sum().max()) if len(uw) else 0
        qe = seq.resample("QE").last()
        q0 = pd.concat([pd.Series([seq.iloc[0]], index=[seq.index[0]]), qe]).iloc[:-1]
        qr = (qe.values / q0.values - 1) * 100
        sub = d[d.ts.dt.year == y]
        r = C.rates(sub) if len(sub) else None
        rows.append(dict(year=y, n=len(sub),
            win=r["win"] if r else float('nan'), tsloss=r["tsloss"] if r else float('nan'),
            meanP=r["meanP"] if r else float('nan'),
            ret=(seq.iloc[-1]/seq.iloc[0]-1)*100, maxDD=dd.min(), uw=uwmax,
            qmin=float(np.min(qr)) if len(qr) else float('nan'), eq=seq.iloc[-1]))
    return pd.DataFrame(rows)

def constraints(df):
    bad = []
    for _, r in df.iterrows():
        v = []
        if r.maxDD < -15: v.append(f"maxDD={r.maxDD:.2f}")
        if r.uw > 120:    v.append(f"UW={int(r.uw)}")
        if r.ret < 0:     v.append(f"ret={r.ret:.2f}")
        if r.qmin < -5:   v.append(f"qmin={r.qmin:.1f}")
        if v: bad.append(f"{int(r.year)}: " + " ".join(v))
    return bad

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--k", type=int, required=True)
    ap.add_argument("--base", required=True); ap.add_argument("tags", nargs="+")
    a = ap.parse_args()
    F = math.sqrt(2 * math.log(a.k))
    print(f"### CI_INFLATE = sqrt(2 ln {a.k}) = {F:.6f} | block={C.BLOCK_H}h nrep={C.NREP} seed={C.SEED}")
    print(f"### baseline = {a.base}\n")
    db = C.trades(a.base)
    for t in [a.base] + a.tags:
        df = per_year(t); bad = constraints(df)
        print(f"===== {t} =====")
        print(df.to_string(index=False, float_format=lambda x: f"{x:8.2f}"))
        print(f"RANG BUOC CUNG ({len(df)} nam): " + ("PASS" if not bad else "FAIL -> " + " | ".join(bad)))
        print()
    for t in a.tags:
        da = C.trades(t); r = raw_ci(da, db)
        print(f"===== CI: ({t}) - ({a.base}) | n_var={len(da)} n_base={len(db)} =====")
        print(f"{'rate':<10}{'hieu':>10}{'lo':>10}{'hi':>10}  {'ngoai_CI':>9}  huong")
        ngood = nbad = 0
        for k in QUALITY:
            o, lo, hi = r[k]; c = (lo+hi)/2.0
            lo, hi = c-(c-lo)*F, c+(hi-c)*F
            sig = not (lo <= 0.0 <= hi)
            dirn = "-"
            if sig:
                dirn = "TOT" if o*GOOD[k] > 0 else "XAU"
                ngood += int(dirn == "TOT"); nbad += int(dirn == "XAU")
            print(f"{k:<10}{o:>10.3f}{lo:>10.3f}{hi:>10.3f}  {'CO' if sig else '-':>9}  {dirn}")
        print(f"=> {ngood} rate NGOAI CI huong TOT, {nbad} huong XAU (luat thang: >=2 TOT + rang buoc cung PASS)\n")
