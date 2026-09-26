"""GATE-RECAL scorer — cham cac chan cua docs/prereg/PREREG_GATE_RECAL.md.

Doi tuong so = baseline TAT tren nen KEEPLEG0 (`gr-par-kg0`) — CHINH LA chan do "TAT = y nguyen".
  [0] CONG PARITY: gr-par-t170 md5 efb793e2/n1089/eq111070 · gr-par-kg0 md5 99e42b75/n1085/eq103083
  [1] BANG CHINH: n · entry/ngay · entry/thang · equity · CAGR · maxDD · UW · qmin · conc · meanP/leg
  [2] 5 RATE + CI khoi-72h (2000 rep, seed 20260905) vs baseline, CA HAI do rong (x1.21 legacy + inflate(k))
  [3] EQUITY: paired block-bootstrap ngay (block 21/10/42, 2000 rep, seed 20260903) + nguong 1.4823*sd_boot
  [4] RAO CUNG theo nam (R-MOI: maxDD<=40 / UW<=250 / qmin>=-20 / ko nam am / conc<=15)
  [5] NHIP: entry/ngay & entry/thang cua nhip 1 phut vs nhip 15 phut
Usage: python3 gate_recal_score.py [--k 3] [--json OUT.json]
"""
import argparse
import hashlib
import json
import math
import os
import re
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import numpy as np
import pandas as pd
import gd92xexit_score as G

KOUT = "/home/ubuntu/kaggle_sim/out"
SEED_EQ, NREP_EQ, BLOCKS_EQ, CAP0 = 20260903, 2000, [21, 10, 42], 35000.0

BASE = "gr-par-kg0"                 # baseline TAT (= trunk KEEPLEG0, cung la cong parity)
PAR = "gr-par-t170"
ARMS = ["gr-kg0-q995", "gr-kg0-q998", "gr-kg0-q999"]
PACE = "gr-kg0-q998-15m"
EXPECT = {
    PAR: ("efb793e2468ca3a7318da0f0ad23d4fc", 1089, 111070),
    BASE: ("99e42b75cf1a2142f9cd14dc72e371ba", 1085, 103083),
}
TARGET_LO, TARGET_HI = 5.0, 30.0   # pre-reg §4(iii): ty le entry/thang ky vong trong [5, 30]


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def md5(tag):
    p = os.path.join(KOUT, tag, "storage", "printDone.csv")
    return md5f(p) if os.path.exists(p) else None


def gate_lines(tag):
    """Doc cac dong [GATE] / [GATE-RECAL] cua sim.out (khong giai nen lai neu da co .gz)."""
    p = os.path.join(KOUT, tag, "logs", "sim.out")
    if not os.path.exists(p):
        gz = p + ".gz"
        if os.path.exists(gz):
            import gzip
            with gzip.open(gz, "rt", errors="ignore") as f, open(p, "w") as o:
                o.write(f.read())
    out = {"gate": [], "recal": [], "built": []}
    if not os.path.exists(p):
        return out
    for ln in open(p, errors="ignore"):
        if "[GATE-RECAL] built" in ln:
            out["built"].append(ln.strip())
        elif "[GATE-RECAL]" in ln:
            out["recal"].append(ln.strip())
        elif "[GATE] " in ln:
            out["gate"].append(ln.strip())
    return out


def rate(d, s):
    if s > 0:
        return (s >= d).groupby((s < d).cumsum()).sum().max()
    return 0


def eq_series(tag):
    return G.equity(tag)


def idxmat(n, blen, nrep, seed):
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / blen))
    starts = rng.integers(0, n, size=(nrep, nb))
    off = np.arange(blen)
    return ((starts[:, :, None] + off[None, None, :]) % n).reshape(nrep, nb * blen)[:, :n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=3, help="so bien the duoc so (inflate)")
    ap.add_argument("--json", default="/home/ubuntu/kaggle_sim/out/gate_recal_score.json")
    a = ap.parse_args()
    kmult = math.sqrt(2.0 * math.log(a.k))

    tags = [PAR, BASE] + ARMS + [PACE]
    print("=" * 96)
    print("CONG 0 — PARITY (TAT = y nguyen)")
    parity = {}
    for t in (PAR, BASE):
        m = md5(t)
        e, n, eq = EXPECT[t]
        res = None
        try:
            res = G.summary(t)
        except Exception as ex:
            print("  %-18s KHONG DOC DUOC: %s" % (t, ex))
        ok = (m == e) and res and res["n"] == n and round(res["end"]) == eq
        parity[t] = dict(md5=m, want_md5=e, n=res["n"] if res else None, want_n=n,
                         eq=round(res["end"]) if res else None, want_eq=eq, pass_=bool(ok))
        print("  %-18s md5=%s %s | n=%s(want %d) eq=%s(want %d) => %s" % (
            t, m, "OK" if m == e else "LECH", res["n"] if res else "?", n,
            round(res["end"]) if res else "?", eq, "PASS" if ok else "FAIL"))

    print("\n" + "=" * 96)
    print("BANG CHINH — KEEPLEG0 (DEV 2021-07-01..2025-12-31), baseline = %s" % BASE)
    rows = {}
    for t in tags:
        s = G.summary(t)
        nd = s["ndays"]
        rows[t] = dict(
            n=s["n"], ndays=nd, eq=s["end"], cagr=s["cagr"], maxdd=s["maxDD"], uw=s["uw"],
            qmin=s["qmin"], conc=s["conc"], hold_med=s["hold_med"], turn=s["turn"],
            sumpnl=s["sumpnl"], meanP=s["sumpnl"] / s["n"] if s["n"] else float("nan"),
            entry_day=s["n"] / nd, entry_month=s["n"] / nd * 365.25 / 12.0,
            d_cagr_pp=s["cagr"] - G.summary(BASE)["cagr"])
    hdr = "%-18s %6s %9s %7s %8s %7s %6s %7s %9s %9s %8s"
    print(hdr % ("chan", "n", "eq", "CAGR%", "maxDD%", "UW", "qmin", "conc%", "entry/ngay", "entry/thang", "meanP"))
    for t in tags:
        r = rows[t]
        print(hdr % (t, r["n"], "%.0f" % r["eq"], "%+.2f" % r["cagr"], "%.2f" % r["maxdd"],
                     r["uw"], "%.2f" % r["qmin"], "%.2f" % r["conc"], "%.3f" % r["entry_day"],
                     "%.1f" % r["entry_month"], "%.3f" % r["meanP"]))

    print("\n" + "=" * 96)
    print("CI 5 RATE (block-72h, 2000 rep, seed 20260905) vs baseline %s — legacy x1.21 + inflate(k=%d)=%.4f"
          % (BASE, a.k, kmult))
    ci = {}
    for t in ARMS + [PACE]:
        for wname, w in (("legacy1.21", 1.21), ("inflate%d" % a.k, kmult)):
            r = G.ci_pair(t, BASE, w)
            ci.setdefault(t, {})[wname] = {k: [round(v[0], 4), round(v[1], 4), round(v[2], 4), bool(v[3])]
                                           for k, v in r.items()}
            outd = [k for k, v in r.items() if v[3] and v[0] > 0]
            outw = [k for k, v in r.items() if v[3] and v[0] < 0]
            print("  %-18s %-11s TOT=%s | XAU=%s" % (t, wname, outd or "-", outw or "-"))

    print("\n" + "=" * 96)
    print("EQUITY — paired block-bootstrap ngay (block 21/10/42, 2000 rep, seed 20260903), nguong %.4f*sd_boot"
          % kmult)
    Emap = {t: eq_series(t) for t in tags}
    N = len(Emap[BASE])
    LR = {}
    for t in tags:
        v = np.concatenate([[CAP0], Emap[t].values.astype(float)])
        LR[t] = np.diff(np.log(v))
    cagr = lambda lr: (np.exp(lr.sum() * 365.0 / N) - 1.0) * 100

    def maxdd(s):
        return float(((s / s.cummax() - 1) * 100).min())

    eq_ci = {}
    print("  n ngay=%d (%.2f nam) %s..%s" % (N, N / 365.25, Emap[BASE].index[0].date(),
                                              Emap[BASE].index[-1].date()))
    hdr2 = "  %-18s %10s %10s %10s %10s %8s %10s"
    print(hdr2 % ("chan", "dCAGR(pp)", "lo95_21", "hi95_21", "sd_21", "P(d>0)", "nguong"))
    for t in ARMS + [PACE]:
        d = cagr(LR[t]) - cagr(LR[BASE])
        row = {}
        for b in BLOCKS_EQ:
            ix = idxmat(N, b, NREP_EQ, SEED_EQ)
            da = (np.exp(LR[t][ix].sum(axis=1) * 365.0 / N)
                  - np.exp(LR[BASE][ix].sum(axis=1) * 365.0 / N)) * 100
            row[b] = dict(lo=float(np.percentile(da, 2.5)), hi=float(np.percentile(da, 97.5)),
                          sd=float(da.std(ddof=1)), p=float((da > 0).mean()))
        eq_ci[t] = dict(d=float(d), blocks=row, thr=kmult * row[21]["sd"],
                        pass_=bool(d > kmult * row[21]["sd"]))
        r21 = row[21]
        print(hdr2 % (t, "%+.3f" % d, "%+.3f" % r21["lo"], "%+.3f" % r21["hi"],
                      "%.3f" % r21["sd"], "%.3f" % r21["p"], "+%.3f" % (kmult * r21["sd"])))

    print("\n" + "=" * 96)
    print("RAO CUNG theo nam (R-MOI: maxDD<=40 / UW<=250 / qmin>=-20 / khong nam am)")
    rail = {}
    for t in tags:
        yd = G.yearly_detail(t)
        bad = []
        for y, v in sorted(yd.items()) if isinstance(yd, dict) else []:
            if isinstance(v, dict):
                if v.get("ret", 0) <= 0:
                    bad.append("%s:ret<=0" % y)
                if v.get("uw", 0) > 250:
                    bad.append("%s:UW%d" % (y, v["uw"]))
                if v.get("maxDD", 0) < -40:
                    bad.append("%s:DD%.1f" % (y, v["maxDD"]))
                if v.get("qmin", 0) < -20:
                    bad.append("%s:qmin%.1f" % (y, v["qmin"]))
        rail[t] = bad
        print("  %-18s %s" % (t, "PASS" if not bad else "VI PHAM: " + ",".join(bad)))

    print("\n" + "=" * 96)
    print("NHIP — entry/ngay & entry/thang: 1 phut vs 15 phut (nhip live 96/ngay)")
    b_r, p_r = rows[BASE], rows[PACE]
    print("  nhip  1 phut (%s): n=%d entry/ngay=%.4f entry/thang=%.2f" % (BASE, b_r["n"], b_r["entry_day"], b_r["entry_month"]))
    print("  nhip 15 phut (%s): n=%d entry/ngay=%.4f entry/thang=%.2f" % (PACE, p_r["n"], p_r["entry_day"], p_r["entry_month"]))
    print("  ty le 15m/1m = %.4f (pre-reg §4(iii): >= 0.60 moi 'chuyen doi duoc')" % (p_r["n"] / b_r["n"]))
    pace = dict(n_1m=b_r["n"], n_15m=p_r["n"], entry_day_1m=b_r["entry_day"],
                entry_day_15m=p_r["entry_day"], entry_month_1m=b_r["entry_month"],
                entry_month_15m=p_r["entry_month"], ratio=p_r["n"] / b_r["n"],
                d_cagr_pp=p_r["cagr"] - b_r["cagr"], d_maxdd=p_r["maxdd"] - b_r["maxdd"])

    gl = {t: gate_lines(t) for t in tags}
    print("\n" + "=" * 96)
    print("LOG [GATE] (n_cand/n_pass) + [GATE-RECAL]")
    for t in tags:
        for ln in gl[t]["built"] + gl[t]["recal"] + gl[t]["gate"]:
            print("  %-18s %s" % (t, ln))

    # ----- KET LUAN theo quy tac CHOT TRUOC (pre-reg §4) -----
    verdict = {}
    for t in ARMS + [PACE]:
        r = rows[t]
        ok_cagr = eq_ci[t]["pass_"]
        ok_rail = not rail[t]
        ok_rate = TARGET_LO <= r["entry_month"] <= TARGET_HI
        ok_pace = (r["n"] / rows[BASE]["n"]) >= 0.60
        verdict[t] = dict(cagr=ok_cagr, rail=ok_rail, rate=ok_rate, pace=ok_pace,
                          PASS=bool(ok_cagr and ok_rail and ok_rate and ok_pace))
    print("\n" + "=" * 96)
    print("PHAN QUYET (pre-reg §4: PASS <=> dCAGR>thr VA qua rao cung VA entry/thang trong [5,30] VA nhip>=0.60)")
    for t in ARMS + [PACE]:
        v = verdict[t]
        print("  %-18s cagr=%s rail=%s rate=%s pace=%s => %s" % (
            t, v["cagr"], v["rail"], v["rate"], v["pace"], "PASS" if v["PASS"] else "KHONG PASS"))

    out = dict(parity=parity, rows=rows, ci=ci, eq_ci=eq_ci, rail=rail, pace=pace,
               verdict=verdict, kmult=kmult, k=a.k, n_days=N,
               gate_logs={t: gl[t] for t in tags},
               md5={t: md5(t) for t in tags})
    with open(a.json, "w") as f:
        json.dump(out, f, indent=1)
    print("\nJSON: %s" % a.json)


if __name__ == "__main__":
    main()
