"""VIEC 3 cua docs/prereg/PREREG_GATE_ROOTCAUSE.md — cham chan phuong an A tren DEV.

Doi chieu = cd-sel15 (nhip selector 15', gate cu). Chan moi: rc-a-q995/q998/q999 (pa A: thay dyn
bang phan vi cuon, = SIM_GATE_P15_Q + SIM_GATE_DYN_SCALE=0.001).

Ra: docs/result/RESULT_GATE_ROOTCAUSE.json (gop phan VIEC 1 do analyze sinh ra) + JSON rieng nghiem thu.
Usage: python3 gate_rootcause_score.py [--k 3]
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
SEED_EQ, NREP_EQ, CAP0 = 20260903, 2000, 35000.0
BASE = "cd-sel15"            # doi chieu: nhip 15' + gate incumbent
ARMS = ["rc-a-q995", "rc-a-q998", "rc-a-q999"]
PAR = {"rc-par-kg0": ("99e42b75cf1a2142f9cd14dc72e371ba", 1085, 103083),
       "rc-par-t170": ("efb793e2468ca3a7318da0f0ad23d4fc", 1089, 111070)}
OUT = "/home/ubuntu/src/BinanceFuturesJava/docs/result/RESULT_GATE_ROOTCAUSE.json"
TARGET_LO, TARGET_HI = 5.0, 30.0
CONC_MAX, QMIN_MIN = 15.0, -20.0


def md5(tag):
    p = os.path.join(KOUT, tag, "storage", "printDone.csv")
    if not os.path.exists(p):
        return None
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def gate_line(tag):
    p = os.path.join(KOUT, tag, "logs", "sim.out")
    out = []
    if os.path.exists(p):
        for ln in open(p, errors="ignore"):
            if "[GATE-RECAL]" in ln or ("[GATE] " in ln and "scale=" in ln):
                out.append(ln.strip().split("1MStopLoss: ")[-1])
    return out


def leg_counts(tag):
    import csv
    p = os.path.join(KOUT, tag, "storage", "printDone.csv")
    c = {}
    if not os.path.exists(p):
        return c
    with open(p, newline="") as f:
        for r in csv.DictReader(f):
            c[r.get("level")] = c.get(r.get("level"), 0) + 1
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3)
    a = ap.parse_args()
    kmult = math.sqrt(2.0 * math.log(a.k))

    out = {}
    if os.path.exists(OUT):
        out = json.load(open(OUT))

    print("PARITY (jar sim-jar-cadence, TAT = y nguyen)")
    par = {}
    for t, (e, n, eq) in PAR.items():
        m = md5(t)
        s = None
        try:
            s = G.summary(t)
        except Exception as ex:
            print("  %-14s KHONG DOC DUOC %s" % (t, ex))
        ok = bool(s) and m == e and s["n"] == n and round(s["end"]) == eq
        par[t] = dict(md5=m, want=e, n=s["n"] if s else None, eq=round(s["end"]) if s else None, pass_=ok)
        print("  %-14s md5=%s %s n=%s eq=%s => %s" %
              (t, m, "OK" if m == e else "LECH", s["n"] if s else "?", round(s["end"]) if s else "?", "PASS" if ok else "FAIL"))
    out["parity"] = par

    tags = [BASE] + ARMS
    rows = {}
    print("\nBANG CHINH (DEV 2021-07-01..2025-12-31), nhip selector 15', doi chieu %s" % BASE)
    hdr = "%-12s %6s %9s %8s %8s %5s %7s %7s %10s %10s %8s"
    print(hdr % ("chan", "n", "eq", "CAGR%", "maxDD%", "UW", "qmin", "conc%", "entry/ngay", "entry/thang", "meanP"))
    for t in tags:
        try:
            s = G.summary(t)
        except Exception as ex:
            print("  %-12s BO (khong doc duoc: %s)" % (t, ex))
            continue
        r = dict(n=s["n"], ndays=s["ndays"], eq=s["end"], cagr=s["cagr"], maxdd=s["maxDD"], uw=s["uw"],
                 qmin=s["qmin"], conc=s["conc"], sumpnl=s["sumpnl"],
                 meanP=s["sumpnl"] / s["n"] if s["n"] else float("nan"),
                 entry_day=s["n"] / s["ndays"], entry_month=s["n"] / s["ndays"] * 365.25 / 12.0)
        rows[t] = r
        print(hdr % (t, r["n"], "%.0f" % r["eq"], "%+.2f" % r["cagr"], "%.2f" % r["maxdd"], r["uw"],
                     "%.2f" % r["qmin"], "%.2f" % r["conc"], "%.4f" % r["entry_day"],
                     "%.2f" % r["entry_month"], "%.3f" % r["meanP"]))
    out["rows"] = rows

    print("\nLEG theo cot level + [GATE] log:")
    for t in tags:
        lc = leg_counts(t)
        gl = gate_line(t)
        g = [x for x in gl if "[GATE] " in x]
        print("  %-12s sel=%s bd=%s dca=%s | %s" % (
            t, lc.get("PREDICT_SYMBOL_TRADE"), lc.get("BIG_DOWN"), lc.get("DCA_LEVEL1"),
            g[-1] if g else "?"))
    out["legs"] = {t: leg_counts(t) for t in tags}
    out["gate_log"] = {t: gate_line(t) for t in tags}

    print("\nCI 5 RATE (block-72h, 2000 rep, seed 20260905) vs %s, inflate k=%d = %.4f" % (BASE, a.k, kmult))
    ci = {}
    for t in ARMS:
        if t not in rows:
            continue
        r = G.ci_pair(t, BASE, kmult)
        ci[t] = {k: [round(v[0], 4), round(v[1], 4), round(v[2], 4), bool(v[3])] for k, v in r.items()}
        nout = sum(1 for v in ci[t].values() if v[3])
        print("  %-12s ngoaiCI=%d/5 %s" % (t, nout, {k: [v[0], v[1], v[2], v[3]] for k, v in ci[t].items()}))
    out["ci_rates"] = ci

    print("\nEQUITY paired block-bootstrap ngay (block 21/10/42, 2000 rep, seed %d), nguong %.4f*sd" % (SEED_EQ, kmult))
    Emap = {t: G.equity(t) for t in tags if t in rows}
    N = len(Emap[BASE])
    LR = {t: np.diff(np.log(np.concatenate([[CAP0], Emap[t].values.astype(float)]))) for t in Emap}
    rng = np.random.default_rng(SEED_EQ)
    eqci = {}
    for t in ARMS:
        if t not in Emap:
            continue
        cagr = lambda lr: (np.exp(lr.sum() * 365.0 / N) - 1.0) * 100  # noqa: E731
        d0 = cagr(LR[t]) - cagr(LR[BASE])
        for blen in (21, 10, 42):
            nb = int(np.ceil(N / blen))
            starts = rng.integers(0, N, size=(NREP_EQ, nb))
            off = np.arange(blen)
            idx = ((starts[:, :, None] + off[None, None, :]) % N).reshape(NREP_EQ, nb * blen)[:, :N]
            dlr = LR[t][idx].sum(1) - LR[BASE][idx].sum(1)
            d = (np.exp(dlr * 365.0 / N) - 1.0) * 100
            lo, hi = np.percentile(d, [2.5, 97.5])
            sd = float(d.std())
            eqci.setdefault(t, {})[str(blen)] = dict(dCAGR=round(float(d0), 3), lo=round(float(lo), 3),
                                                     hi=round(float(hi), 3), sd=round(sd, 3),
                                                     thr=round(kmult * sd, 3), dat=bool(d0 > kmult * sd))
            print("  %-12s block%-3d dCAGR=%+.3f [%+.3f,%+.3f] sd=%.3f nguong=%.3f DAT=%s" %
                  (t, blen, d0, lo, hi, sd, kmult * sd, d0 > kmult * sd))
    out["ci_equity"] = eqci

    print("\nKY VONG DA CHOT (pre-reg §3/§4):")
    for t in ARMS:
        if t not in rows:
            continue
        r = rows[t]
        loose = (r["entry_month"] > TARGET_HI) or (r["conc"] > CONC_MAX) or (r["qmin"] < QMIN_MIN)
        nout = sum(1 for v in out["ci_rates"].get(t, {}).values() if v[3])
        eq21 = out["ci_equity"].get(t, {}).get("21", {})
        print("  %-12s entry/thang=%.2f in[5,30]=%s quaRong=%s rateNgoaiCI=%d/5 dCAGR21=%+.2f(DAT=%s)" %
              (t, r["entry_month"], TARGET_LO <= r["entry_month"] <= TARGET_HI, loose, nout,
               eq21.get("dCAGR", float("nan")), eq21.get("dat")))
    out["kmult"] = kmult
    out["k"] = a.k
    json.dump(out, open(OUT, "w"), indent=1)
    print("\nJSON ->", OUT)


if __name__ == "__main__":
    main()
