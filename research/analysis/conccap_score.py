"""CONC-CAP-HIGHN scorer — cham 4 chan cua docs/prereg/PREREG_CONC_CAP_HIGHN.md.

  (0) CO CHE  : guard [CONC-PC] MODE + SUMMARY blocked= + so dong SKIP; [GATE-ROLL] BAT; md5 printDone
  (1) CONC    : tap trung 1 coin max theo thoi gian (OFF vs ON)
  (2) 5 RATE  : win% / TSloss% / mP|SM / mP|SL / meanP — ON vs OFF CUA CHINH NEN,
                CI block-72h 2000 rep seed 20260905 anchor 2021-07-01 o CA HAI do rong
                (legacy x1.21 + chuan hoa inflate(k)=sqrt(2 ln k))
  (3) RAO CUNG: conc<=15 / UW<=200 / maxDD<=30 (S1) VA <=40 (S2) / quy>=-15 / ko nam am
                — CA theo nam LAN toan ky
  (4) PnL THEO NAM: OFF vs ON tung cap => chan tap trung MAT BAO NHIEU PnL (%)
  (5) n / meanP-leg / hold_med / turnover / Sum funding / Sum PnL

Usage: python3 conccap_score.py [--k 3] [--json OUT.json]
"""
import gzip
import json
import os
import re
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import numpy as np
import pandas as pd
import gd92xexit_score as G
import c3_rates as C

KOUT = "/home/ubuntu/kaggle_sim/out"
BLOCK_H, NREP, SEED = G.BLOCK_H, G.NREP, G.SEED
LEGACY = G.LEGACY
UW_MAX, Q_MIN, CONC_MAX = G.UW_MAX, G.Q_MIN, G.CONC_MAX
DD_S1, DD_S2 = 30.0, 40.0

# (tag ON, tag OFF, nhan nen, baseline chung de so tham chieu)
PAIRS = [
    ("cc-t100", "hn-t100", "T100 (x1_c3_full)", "hn-par1"),
    ("cc-g92", "hn-g92", "GD92 (+rolling 0.92/90d)", "hn-par1"),
    ("cc-g-cp", "hn-g-cp", "GD92+CAP10/30", "hn-par1"),
]
PAR = "hn-par1"


def _sout(tag):
    p = os.path.join(KOUT, tag, "logs", "sim.out")
    if not os.path.exists(p):
        gz = p + ".gz"
        if os.path.exists(gz):
            with gzip.open(gz, "rt", errors="ignore") as f, open(p, "w") as o:
                o.write(f.read())
    return p


def guard(tag):
    """Doc log: so lan guard BIND + so dong SKIP + MODE + GATE-ROLL."""
    p = _sout(tag)
    o = dict(mode=None, summary=None, skip=0, gate_roll=None, before_first_warn=0, exists=os.path.exists(p))
    if not o["exists"]:
        return o
    rx_mode = re.compile(r"\[CONC-PC\] MODE pct=([0-9.]+)")
    rx_sum = re.compile(r"\[CONC-PC\] SUMMARY blocked=(\d+)")
    with open(p, errors="ignore") as fh:
        for ln in fh:
            if "[CONC-PC] SKIP" in ln:
                o["skip"] += 1
            elif "[CONC-PC] MODE" in ln:
                m = rx_mode.search(ln)
                if m:
                    o["mode"] = m.group(1)
            elif "[CONC-PC] SUMMARY" in ln:
                m = rx_sum.search(ln)
                if m:
                    o["summary"] = int(m.group(1))
            elif "[GATE-ROLL] BAT" in ln:
                o["gate_roll"] = ln.split("***")[1].strip() if "***" in ln else ln.strip()
            elif "[GATE-ROLL] truy van" in ln and "TRUOC moc gio dau tien" in ln:
                o["before_first_warn"] += 1
    return o


def md5(tag):
    import hashlib
    p = os.path.join(KOUT, tag, "storage", "printDone.csv")
    if not os.path.exists(p):
        return None
    h = hashlib.md5()
    with open(p, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def funding_term(tag):
    d = G.trades(tag)
    if "funding" not in d.columns:
        return dict(n=len(d), funding_sum=float("nan"), funding_mean=float("nan"),
                    funding_over_pnl=float("nan"))
    f = pd.to_numeric(d["funding"], errors="coerce").fillna(0.0)
    s = float(d["pnl"].sum()) if "pnl" in d.columns else float("nan")
    return dict(n=len(d), funding_sum=float(f.sum()), funding_mean=float(f.mean()),
                funding_over_pnl=float(f.sum() / s * 100) if s else float("nan"))


def rates_row(tag):
    d = G.trades(tag)
    sm = d.loc[d.status == "STOP_MARKET_DONE", "profit"]
    sl = d.loc[d.status == "STOP_LOSS_DONE", "profit"]
    return dict(n=len(d), win=100.0 * (d.profit > 0).mean(),
                tsloss=100.0 * (d.status == "STOP_LOSS_DONE").mean(),
                mp_sm=float(sm.mean()) if len(sm) else float("nan"),
                mp_sl=float(sl.mean()) if len(sl) else float("nan"),
                meanP=float(d.profit.mean()))


def ci_block(v, par, k):
    c1 = G.ci_pair(v, par, LEGACY)
    c2 = G.ci_pair(v, par, C.inflate(k))
    ng = nb = 0
    print("  -- %s  (-  %s) --" % (v, par))
    print("  %-9s %11s %24s %28s %5s %5s %-4s" % (
        "rate", "hieu", "CI @1.21", "CI @%.4f" % C.inflate(k), "outL", "outS", "HUONG"))
    det = {}
    for name, dirc in G.RATES:
        obs = c1[name][0]
        lo1, hi1, o1 = c1[name][1], c1[name][2], c1[name][3]
        lo2, hi2, o2 = c2[name][1], c2[name][2], c2[name][3]
        out = o1 and o2
        good = out and ((dirc > 0 and obs > 0) or (dirc < 0 and obs < 0))
        bad = out and not good
        ng += int(good); nb += int(bad)
        det[name] = dict(obs=float(obs), lo=float(lo2), hi=float(hi2),
                         out_legacy1=bool(o1), out_both=bool(out), good=bool(good), bad=bool(bad))
        print("  %-9s %+11.3f [%9.3f,%9.3f] [%9.3f,%9.3f] %5s %5s %-4s" % (
            name, obs, lo1, hi1, lo2, hi2, "Y" if o1 else "-", "Y" if o2 else "-",
            "TOT" if good else ("XAU" if bad else "-")))
    print("  >>> %s vs %s: TOT ngoai CI (ca hai do rong) = %d/5 | XAU = %d/5" % (v, par, ng, nb))
    return ng, nb, det


def main():
    k, jout = 3, None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--k":
            k = int(sys.argv[i + 1]); i += 2; continue
        if sys.argv[i] == "--json":
            jout = sys.argv[i + 1]; i += 2; continue
        i += 1
    W = C.inflate(k)
    tags = [PAR] + [t for p in PAIRS for t in p[:2]]
    tags = list(dict.fromkeys(tags))

    print("=== CONC-CAP-HIGHN | block-%dh %d rep seed %d anchor %s | legacy %.2f / inflate(%d)=%.6f" % (
        BLOCK_H, NREP, SEED, G.ANCHOR.date(), LEGACY, k, W))

    D = {t: G.trades(t) for t in tags}
    S = {t: G.summary(t) for t in tags}
    Y = {t: G.yearly_detail(t) for t in tags}
    Gd = {t: guard(t) for t in tags}
    F = {t: funding_term(t) for t in tags}
    res = {"k": k, "inflate_k": W, "legacy": LEGACY, "guard": Gd,
           "md5": {t: md5(t) for t in tags}, "summary": S, "yearly": Y,
           "funding": F, "ci": {}}

    print("\n=== (0) CO CHE — guard co bind THAT khong? (docs/PREREG §3 P3) ===")
    print("%-9s %-14s %-9s %-8s %-9s %-8s %-32s" % (
        "tag", "md5 printDone", "n", "equity", "blocked", "SKIP", "GATE-ROLL"))
    for t in tags:
        g = Gd[t]; s = S[t]
        print("%-9s %-14s %-9d %-8.0f %-9s %-8d %-32s" % (
            t, (md5(t) or "-")[:14], s["n"], s["end"],
            g["mode"] and ("MODE pct=" + g["mode"]) or "-", g["skip"],
            (g["gate_roll"] or ("off/beforeFirst_warn=%d" % g["before_first_warn"]))[:32]))
    for t in tags:
        g = Gd[t]
        assert g["summary"] is None or g["summary"] == g["skip"], \
            "SUMMARY blocked=%s != so dong SKIP=%s o %s" % (g["summary"], g["skip"], t)

    print("\n=== (1) TAP TRUNG 1 COIN MAX (theo thoi gian) — OFF vs ON ===")
    print("%-9s %-30s %9s %9s %9s %s" % ("cap", "nen", "conc OFF%", "conc ON%", "delta", "<=15%?"))
    for on, off, lab, _ in PAIRS:
        co, cn = S[off]["conc"], S[on]["conc"]
        print("%-9s %-30s %9.2f %9.2f %+9.2f %s" % (
            on + "/" + off, lab, co, cn, cn - co, "OK" if cn <= CONC_MAX else "FAIL"))

    print("\n=== (2) 5 RATE — ON vs OFF CUA CHINH NEN (CI ca hai do rong) ===")
    tot_bad = 0
    for on, off, lab, _ in PAIRS:
        print("\n[nen %s] %s vs %s" % (lab, on, off))
        ro, rn = rates_row(off), rates_row(on)
        print("  %-9s %8s %8s %10s %10s %10s" % ("", "n", "win%", "TSloss%", "mP|SM", "meanP"))
        for nm, r in (("OFF " + off, ro), ("ON  " + on, rn)):
            print("  %-9s %8d %8.2f %8.2f %10.3f %10.3f" % (
                nm, r["n"], r["win"], r["tsloss"], r["mp_sm"], r["meanP"]))
        ng, nb, det = ci_block(on, off, k)
        tot_bad += nb
        res["ci"]["%s_vs_%s" % (on, off)] = dict(det=det, good=ng, bad=nb)

    print("\n=== (2b) THAM CHIEU: moi chan vs T170 (%s) — KHONG phai tieu chi ===" % PAR)
    for on, off, lab, _ in PAIRS:
        ci_block(on, PAR, k)

    print("\n=== (3) RAO CUNG RISK_APPETITE — theo nam (DD<=30 S1 | DD<=40 S2) VA toan ky ===")
    hdr = "%-9s %9s %7s %8s %6s %8s %8s %7s %8s" % (
        "tag", "equity", "CAGR%", "maxDD%", "UW", "qmin%", "conc%", "n", "SumPnL")
    print(hdr)
    for t in tags:
        s = S[t]
        print("%-9s %9.0f %7.2f %8.2f %6d %8.2f %8.2f %7d %8.0f" % (
            t, s["end"], s["cagr"], s["maxDD"], s["uw"], s["qmin"], s["conc"], s["n"], s["sumpnl"]))
    print("\n  THEO NAM (o = maxDD%/uw/ret% ; P/F theo S1=30% va S2=40%):")
    yrs = sorted({y for t in tags for y in Y[t]})
    print("  %-9s %s" % ("tag", " ".join("%-30d" % y for y in yrs)))
    for t in tags:
        cells = []
        for y in yrs:
            r = Y[t].get(y)
            if not r:
                cells.append("%-30s" % "-"); continue
            ok1 = (r["maxDD"] >= -DD_S1 and r["uw"] <= UW_MAX and r["qmin"] >= Q_MIN and r["ret"] >= 0)
            ok2 = (r["maxDD"] >= -DD_S2 and r["uw"] <= UW_MAX and r["qmin"] >= Q_MIN and r["ret"] >= 0)
            cells.append("%7.2f/%4d/%+7.2f %s/%s" % (
                r["maxDD"], r["uw"], r["ret"], "P" if ok1 else "F", "P" if ok2 else "F"))
        print("  %-9s %s" % (t, " ".join("%-30s" % c for c in cells)))
    print("\n  TOAN KY (S1 = maxDD<=30%%; S2 = maxDD<=40%%; UW<=%d; qmin>=%.0f; conc<=%.0f; ko nam am):" % (
        UW_MAX, Q_MIN, CONC_MAX))
    for t in tags:
        s = S[t]
        neg = [y for y, r in Y[t].items() if r["ret"] < 0]
        def verdict(dd):
            bad = []
            if s["maxDD"] < -dd: bad.append("maxDD %.2f" % s["maxDD"])
            if s["uw"] > UW_MAX: bad.append("UW %d" % s["uw"])
            if s["qmin"] < Q_MIN: bad.append("qmin %.2f" % s["qmin"])
            if s["conc"] > CONC_MAX: bad.append("conc %.2f" % s["conc"])
            if neg: bad.append("nam am %s" % neg)
            return "PASS" if not bad else "FAIL (" + ", ".join(bad) + ")"
        print("  %-9s S1: %-46s S2: %s" % (t, verdict(DD_S1), verdict(DD_S2)))

    print("\n*** (4) BANG PnL CHI TIET THEO NAM — OFF vs ON ***")
    lost = {}
    for on, off, lab, _ in PAIRS:
        print("\n  == %s (%s / %s) ==" % (lab, off, on))
        print("  %-8s %-6s %6s %8s %8s %9s %12s %9s %9s %5s %8s %11s" % (
            "chan", "nam", "n", "win%", "TSloss%", "meanP", "PnL(USDT)", "ret%", "maxDD%", "UW", "qmin%", "equity"))
        for tag in (off, on):
            for y in sorted(Y[tag]):
                r = Y[tag][y]
                print("  %-8s %-6d %6d %8.2f %8.2f %9.3f %12.0f %+9.2f %9.2f %5d %8.2f %11.0f" % (
                    tag, y, r["n"], r["win"], r["tsloss"], r["meanP"], r["pnl_usdt"], r["ret"],
                    r["maxDD"], r["uw"], r["qmin"], r["eq_end"]))
        po, pn = S[off]["sumpnl"], S[on]["sumpnl"]
        try:
            pd_ = G.trades(off)["pnl"].sum(); pn_ = G.trades(on)["pnl"].sum()
            lose = (pd_ - pn_) / pd_ * 100
        except Exception:
            lose = float("nan")
        lost[on] = lose
        print("  >> SumPnL OFF(realized)=%.0f  ON=%.0f  |  MAT %.0f USDT = %.2f%% cua OFF  |  equity OFF %.0f -> ON %.0f (%+.2f%%)" % (
            po, pn, po - pn, lose, S[off]["end"], S[on]["end"],
            (S[on]["end"] / S[off]["end"] - 1) * 100))
    res["pnl_lost_pct"] = lost

    print("\n=== (5) n / meanP-leg / hold / turnover / Sum funding / Sum PnL ===")
    print("%-9s %7s %11s %9s %8s %12s %12s %11s %11s" % (
        "tag", "n", "meanP/leg", "hold_med", "turn", "Sum funding", "funding/leg", "SumPnL", "fund/PnL%"))
    for t in tags:
        s, f = S[t], F[t]
        print("%-9s %7d %11.3f %9.1f %8.3f %12.1f %12.2f %11.0f %10.2f%%" % (
            t, f["n"], s["sumpnl"] / max(f["n"], 1), s["hold_med"],
            s["turn"], f["funding_sum"], f["funding_mean"], s["sumpnl"], f["funding_over_pnl"]))
    print("\n  (funding/PnL% = Sum funding / Sum PnL — hang SO HOC theo n, RESULT_FRAGILITY_N §6.3)")

    print("\n*** KET LUAN SO BO ***")
    for on, off, lab, _ in PAIRS:
        g = Gd[on]
        print("  %-9s blocked=%-5d conc %.2f -> %.2f  | mat PnL %.2f%% | XAU ngoai CI = %d" % (
            on, g["skip"], S[off]["conc"], S[on]["conc"], lost[on],
            res["ci"]["%s_vs_%s" % (on, off)]["bad"]))
        if g["skip"] == 0:
            print("            *** CANH BAO: blocked=0 => ket qua chan nay la TAM THUONG (cap no-op) ***")
    print("  TONG XAU ngoai CI (ca hai do rong) tren moi cap = %d" % tot_bad)

    if jout:
        with open(jout, "w") as f:
            json.dump(res, f, indent=1, default=str)
        print("\n[json] %s" % jout)


if __name__ == "__main__":
    main()
