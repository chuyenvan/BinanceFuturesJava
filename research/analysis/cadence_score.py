"""CADENCE scorer — docs/prereg/PREREG_GATE_RECAL.md AMENDMENT §7.

Tra loi: (1) SIM dang 15' hay 1'?  (2) sel15 (selector 15' + BIG_DOWN/DCA 1') khac all-1' bao nhieu?
          (3) cau hinh nao go-live duoc?

Doi tuong:
  all-1'  = cd-par-kg0   (KEEPLEG0, khong khai key; = cong parity)  -> md5 99e42b75 / n1085 / eq103083
  all-15' = gr-kg0-q998-15m  (chan TAT CA leg o 15', KEM Q=0.998 — ket qua cu, giu lam doi chieu)
  sel15   = cd-sel15     (SIM_ENTRY_SAMPLE_MIN=15, gate TAT)  <- CAI CAN BIET
  + cd-sel15-q998 / cd-sel15-q999 (them nguong phan vi cuon)
Usage: python3 cadence_score.py [--k 3] [--json OUT.json]
"""
import argparse
import hashlib
import json
import math
import os
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import numpy as np
import gd92xexit_score as G

KOUT = "/home/ubuntu/kaggle_sim/out"
SEED_EQ, NREP_EQ, BLOCKS_EQ, CAP0 = 20260903, 2000, [21, 10, 42], 35000.0

BASE = "cd-par-kg0"          # all-1' (baseline)
PAR = "cd-par-t170"
ALL15 = "gr-kg0-q998-15m"    # all-15' (ket qua cu, doi chieu)
ARMS = ["cd-sel15", "cd-sel15-q998", "cd-sel15-q999"]
EXPECT = {
    PAR: ("efb793e2468ca3a7318da0f0ad23d4fc", 1089, 111070),
    BASE: ("99e42b75cf1a2142f9cd14dc72e371ba", 1085, 103083),
}
TARGET_LO, TARGET_HI = 5.0, 30.0


def md5(tag):
    p = os.path.join(KOUT, tag, "storage", "printDone.csv")
    if not os.path.exists(p):
        return None
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def leg_counts(tag):
    """Dem leg theo cot `level` cua printDone.csv."""
    import csv
    p = os.path.join(KOUT, tag, "storage", "printDone.csv")
    c = {}
    if not os.path.exists(p):
        return c
    with open(p, newline="") as f:
        for r in csv.DictReader(f):
            c[r.get("level")] = c.get(r.get("level"), 0) + 1
    return c


def gate_line(tag):
    p = os.path.join(KOUT, tag, "logs", "sim.out")
    if not os.path.exists(p) and os.path.exists(p + ".gz"):
        import gzip
        with gzip.open(p + ".gz", "rt", errors="ignore") as f, open(p, "w") as o:
            o.write(f.read())
    out = []
    if os.path.exists(p):
        for ln in open(p, errors="ignore"):
            if "[GATE-RECAL] OFF" in ln or "[GATE-RECAL]" in ln or ("[GATE] " in ln and "scale=" in ln):
                out.append(ln.strip().split("1MStopLoss: ")[-1])
    return out


def idxmat(n, blen, nrep, seed):
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / blen))
    starts = rng.integers(0, n, size=(nrep, nb))
    off = np.arange(blen)
    return ((starts[:, :, None] + off[None, None, :]) % n).reshape(nrep, nb * blen)[:, :n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--json", default="/home/ubuntu/kaggle_sim/out/cadence_score.json")
    a = ap.parse_args()
    kmult = math.sqrt(2.0 * math.log(a.k))

    tags = [PAR, BASE, ALL15] + ARMS
    print("=" * 100)
    print("CONG 0 — PARITY (TAT = y nguyen)")
    parity = {}
    for t in (PAR, BASE):
        e, n, eq = EXPECT[t]
        m = md5(t)
        try:
            s = G.summary(t)
        except Exception as ex:
            s = None
            print("  %-16s KHONG DOC DUOC: %s" % (t, ex))
        ok = bool(s) and (m == e) and s["n"] == n and round(s["end"]) == eq
        parity[t] = dict(md5=m, want_md5=e, n=s["n"] if s else None, want_n=n,
                         eq=round(s["end"]) if s else None, want_eq=eq, pass_=ok)
        print("  %-16s md5=%s %s | n=%s(want %d) eq=%s(want %d) => %s" % (
            t, m, "OK" if m == e else "LECH", s["n"] if s else "?", n,
            round(s["end"]) if s else "?", eq, "PASS" if ok else "FAIL"))

    print("\n" + "=" * 100)
    print("BANG CHINH (DEV 2021-07-01..2025-12-31), baseline = %s (all-1')" % BASE)
    rows, legs = {}, {}
    for t in tags:
        s = G.summary(t)
        legs[t] = leg_counts(t)
        rows[t] = dict(n=s["n"], ndays=s["ndays"], eq=s["end"], cagr=s["cagr"], maxdd=s["maxDD"],
                       uw=s["uw"], qmin=s["qmin"], conc=s["conc"], sumpnl=s["sumpnl"],
                       meanP=s["sumpnl"] / s["n"] if s["n"] else float("nan"),
                       entry_day=s["n"] / s["ndays"], entry_month=s["n"] / s["ndays"] * 365.25 / 12.0)
    hdr = "%-16s %6s %9s %8s %8s %5s %7s %7s %10s %11s %9s"
    print(hdr % ("chan", "n", "eq", "CAGR%", "maxDD%", "UW", "qmin", "conc%", "entry/ngay", "entry/thang", "meanP"))
    for t in tags:
        r = rows[t]
        print(hdr % (t, r["n"], "%.0f" % r["eq"], "%+.2f" % r["cagr"], "%.2f" % r["maxdd"], r["uw"],
                     "%.2f" % r["qmin"], "%.2f" % r["conc"], "%.4f" % r["entry_day"],
                     "%.2f" % r["entry_month"], "%.3f" % r["meanP"]))
    print("\nSO LEG theo cot level (chung minh lay mau CHI anh huong selector):")
    print("  %-16s %10s %10s %10s %8s %6s" % ("chan", "selector", "BIG_DOWN", "DCA_L1", "other", "tong"))
    for t in tags:
        lc = legs[t]
        sel = lc.get("PREDICT_SYMBOL_TRADE", 0)
        bd = lc.get("BIG_DOWN", 0)
        dc = lc.get("DCA_LEVEL1", 0)
        oth = sum(v for k, v in lc.items() if k not in ("PREDICT_SYMBOL_TRADE", "BIG_DOWN", "DCA_LEVEL1"))
        print("  %-16s %10d %10d %10d %8d %6d" % (t, sel, bd, dc, oth, sum(lc.values())))

    print("\n" + "=" * 100)
    print("CI 5 RATE (block-72h, 2000 rep, seed 20260905) vs %s — legacy x1.21 + inflate(k=%d)=%.4f" % (BASE, a.k, kmult))
    ci = {}
    for t in ARMS:
        for wname, w in (("legacy1.21", 1.21), ("inflate%d" % a.k, kmult)):
            r = G.ci_pair(t, BASE, w)
            ci.setdefault(t, {})[wname] = {k: [round(v[0], 4), round(v[1], 4), round(v[2], 4), bool(v[3])]
                                           for k, v in r.items()}
            print("  %-16s %-11s %s" % (t, wname, {k: [round(v[0], 3), round(v[1], 3), round(v[2], 3), bool(v[3])]
                                                   for k, v in r.items()}))

    print("\n" + "=" * 100)
    print("EQUITY — paired block-bootstrap ngay (block 21/10/42, 2000 rep, seed 20260903), nguong %.4f*sd_boot" % kmult)
    Emap = {t: G.equity(t) for t in tags}
    N = len(Emap[BASE])
    LR = {}
    for t in tags:
        LR[t] = np.diff(np.log(np.concatenate([[CAP0], Emap[t].values.astype(float)])))
    cagr = lambda lr: (np.exp(lr.sum() * 365.0 / N) - 1.0) * 100
    print("  n ngay=%d (%.2f nam) %s..%s" % (N, N / 365.25, Emap[BASE].index[0].date(), Emap[BASE].index[-1].date()))
    hdr2 = "  %-16s %10s %10s %10s %10s %8s %10s"
    print(hdr2 % ("chan", "dCAGR(pp)", "lo95_21", "hi95_21", "sd_21", "P(d>0)", "nguong"))
    eq_ci = {}
    for t in ARMS:
        d = cagr(LR[t]) - cagr(LR[BASE])
        row = {}
        for b in BLOCKS_EQ:
            ix = idxmat(N, b, NREP_EQ, SEED_EQ)
            da = (np.exp(LR[t][ix].sum(axis=1) * 365.0 / N) - np.exp(LR[BASE][ix].sum(axis=1) * 365.0 / N)) * 100
            row[b] = dict(lo=float(np.percentile(da, 2.5)), hi=float(np.percentile(da, 97.5)),
                          sd=float(da.std(ddof=1)), p=float((da > 0).mean()))
        eq_ci[t] = dict(d=float(d), blocks=row, thr=kmult * row[21]["sd"], pass_=bool(d > kmult * row[21]["sd"]))
        r21 = row[21]
        print(hdr2 % (t, "%+.3f" % d, "%+.3f" % r21["lo"], "%+.3f" % r21["hi"], "%.3f" % r21["sd"],
                      "%.3f" % r21["p"], "+%.3f" % (kmult * r21["sd"])))

    print("\n" + "=" * 100)
    print("RAO CUNG theo nam (maxDD<=40 / UW<=250 / qmin>=-20 / khong nam am)")
    rail = {}
    for t in tags:
        yd = G.yearly_detail(t)
        bad = []
        for y, v in sorted(yd.items()):
            if v.get("ret", 0) <= 0:
                bad.append("%s:ret<=0" % y)
            if v.get("uw", 0) > 250:
                bad.append("%s:UW%d" % (y, v["uw"]))
            if v.get("maxDD", 0) < -40:
                bad.append("%s:DD%.1f" % (y, v["maxDD"]))
            if v.get("qmin", 0) < -20:
                bad.append("%s:qmin%.1f" % (y, v["qmin"]))
        rail[t] = bad
        print("  %-16s %s" % (t, "PASS" if not bad else "VI PHAM: " + ",".join(bad)))

    print("\n" + "=" * 100)
    print("LOG [GATE] n_cand/n_pass + [GATE-RECAL]")
    gl = {t: gate_line(t) for t in tags}
    for t in tags:
        for ln in gl[t]:
            print("  %-16s %s" % (t, ln))

    print("\n" + "=" * 100)
    print("TRA LOI (2): sel15 vs all-1' (so cu the)")
    for t in ARMS:
        r, b = rows[t], rows[BASE]
        print("  %-16s dn=%d (%.1f%%) dCAGR=%+.2fpp dmaxDD=%+.2f dUW=%+d dentry/ngay=%+.4f (%.4f vs %.4f)" % (
            t, r["n"] - b["n"], 100.0 * (r["n"] - b["n"]) / b["n"], r["cagr"] - b["cagr"],
            r["maxdd"] - b["maxdd"], r["uw"] - b["uw"], r["entry_day"] - b["entry_day"],
            r["entry_day"], b["entry_day"]))

    out = dict(parity=parity, rows=rows, legs=legs, ci=ci, eq_ci=eq_ci, rail=rail,
               gate_logs=gl, md5={t: md5(t) for t in tags}, kmult=kmult, k=a.k, n_days=N)
    with open(a.json, "w") as f:
        json.dump(out, f, indent=1)
    print("\nJSON: %s" % a.json)


if __name__ == "__main__":
    main()
