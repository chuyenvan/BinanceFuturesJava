"""KG0 scorer — cham 8 chan cua docs/PREREG_GATESCALE_KEEPLEG0.md.

Nen = PRODUCTION FLATGRID KEEPLEG0. Doi tuong so CI = moc KEEPLEG0 (`kg0-g170`).
  [0] CONG PARITY: P1 t170-x1-2021 md5 efb793e2 | P2 kg0-g170 = 1,085 leg / 103,083
  [1] CO CHE: n / meanP-leg / win% / TSloss% / hold / turnover + kiem n DON DIEU theo scale
  [2] 5 RATE + CI block-72h 2000 rep seed 20260905 vs moc, CA HAI do rong (x1.21 legacy + inflate(k))
  [3] RAO CUNG: R-MOI (maxDD<=40 / UW<=250 / qmin>=-20 / ko nam am / conc<=15) va R-CU (30/200/-15)
      — CA theo nam LAN toan ky
  [4] DO VENH THEO NAM (SD + range ret%)
  [5] BANG PnL CHI TIET THEO NAM cho MOI chan
  [6] Sum funding / Sum PnL
  [7] drop-top-K (1 leg / top1% / top5%) => dPnL%
  [8] KET LUAN (a)(b)(c)(d)

Usage: python3 kg0_score.py [--k 6] [--json OUT.json]
"""
import gzip
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
import c3_rates as C

KOUT = "/home/ubuntu/kaggle_sim/out"
BLOCK_H, NREP, SEED = G.BLOCK_H, G.NREP, G.SEED
LEGACY = G.LEGACY                      # 1.21
# khau vi MOI (RISK_APPETITE §6-§7)
DD_NEW, UW_NEW, Q_NEW, CONC_MAX = 40.0, 250, -20.0, 15.0
# khau vi CU (§1, phu)
DD_OLD, UW_OLD, Q_OLD = 30.0, 200, -15.0

BASE = "kg0-g170"                      # moc = cau hinh production dang chay
T170 = "t170-x1-2021"
T170_MD5 = "efb793e2468ca3a7318da0f0ad23d4fc"
KEEP_MD5 = "99e42b75cf1a2142f9cd14dc72e371ba"
KEEP_N, KEEP_EQ = 1085, 103083

# (tag, scale, nhom)  scale=None => khong thuoc thang gate-scale
ARMS = [
    ("kg0-g170", 1.70, "moc"),
    ("kg0-cap", 1.70, "cap"),
    ("kg0-g155", 1.55, "scale"),
    ("kg0-g140", 1.40, "scale"),
    ("kg0-g125", 1.25, "scale"),
    ("kg0-g110", 1.10, "scale"),
    ("kg0-g100", 1.00, "scale"),
]
SCALE_ARMS = ["kg0-g170", "kg0-g155", "kg0-g140", "kg0-g125", "kg0-g110", "kg0-g100"]
CAP_ARMS = ["kg0-cap"]


def md5f(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def md5(tag):
    p = os.path.join(KOUT, tag, "storage", "printDone.csv")
    return md5f(p) if os.path.exists(p) else None


def _sout(tag):
    p = os.path.join(KOUT, tag, "logs", "sim.out")
    if not os.path.exists(p):
        gz = p + ".gz"
        if os.path.exists(gz):
            with gzip.open(gz, "rt", errors="ignore") as f, open(p, "w") as o:
                o.write(f.read())
    return p


def guard(tag):
    """Doc log cua chan CAP: [CONC-PC] MODE / SUMMARY blocked= / so dong SKIP."""
    p = _sout(tag)
    o = dict(mode=None, summary=None, skip=0, exists=os.path.exists(p))
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
    return o


def funding_term(tag):
    d = G.trades(tag)
    if "funding" not in d.columns:
        return dict(funding_sum=float("nan"), funding_over_pnl=float("nan"))
    f = pd.to_numeric(d["funding"], errors="coerce").fillna(0.0)
    s = float(d["pnl"].sum()) if "pnl" in d.columns else float("nan")
    return dict(funding_sum=float(f.sum()),
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


def ci_block(v, par, k, quiet=False):
    """5 rate: CI o CA HAI do rong; 'NGOAI CI' (quyet dinh) = ngoai ca hai."""
    W = C.inflate(k)
    c1 = G.ci_pair(v, par, LEGACY)
    c2 = G.ci_pair(v, par, W)
    ng = nb = 0
    det = {}
    if not quiet:
        print("  -- %s  (-  %s) --" % (v, par))
        print("  %-9s %11s %24s %28s %5s %5s %-4s" % (
            "rate", "hieu", "CI @1.21", "CI @%.4f" % W, "outL", "outS", "HUONG"))
    for name, dirc in G.RATES:
        obs = c1[name][0]
        lo1, hi1, o1 = c1[name][1], c1[name][2], c1[name][3]
        lo2, hi2, o2 = c2[name][1], c2[name][2], c2[name][3]
        out = o1 and o2
        good = out and ((dirc > 0 and obs > 0) or (dirc < 0 and obs < 0))
        bad = out and not good
        ng += int(good); nb += int(bad)
        det[name] = dict(obs=float(obs), lo=float(lo2), hi=float(hi2),
                         out_legacy=bool(o1), out_both=bool(out), good=bool(good), bad=bool(bad))
        if not quiet:
            print("  %-9s %+11.3f [%9.3f,%9.3f] [%9.3f,%9.3f] %5s %5s %-4s" % (
                name, obs, lo1, hi1, lo2, hi2, "Y" if o1 else "-", "Y" if o2 else "-",
                "TOT" if good else ("XAU" if bad else "-")))
    if not quiet:
        print("  >>> %s vs %s: TOT ngoai CI (ca hai do rong) = %d/5 | XAU = %d/5" % (v, par, ng, nb))
    return dict(good=ng, bad=nb, e_pass=bool(ng >= 2 and nb == 0), detail=det)


def fence(S, Y, dd, uw, q):
    """Qua het rao? tra ve (ok_toanky, ly_do, ok_theo_nam)."""
    bad = []
    if S["maxDD"] < -dd:
        bad.append("maxDD_ky %.2f" % S["maxDD"])
    if S["uw"] > uw:
        bad.append("UW_ky %d" % S["uw"])
    if S["qmin"] < q:
        bad.append("qmin_ky %.2f" % S["qmin"])
    if S["conc"] > CONC_MAX:
        bad.append("conc_ky %.2f" % S["conc"])
    yb = {}
    for y, r in sorted(Y.items()):
        b = []
        if r["maxDD"] < -dd:
            b.append("maxDD %.2f" % r["maxDD"])
        if r["uw"] > uw:
            b.append("UW %d" % r["uw"])
        if r["qmin"] < q:
            b.append("qmin %.2f" % r["qmin"])
        if r["ret"] < 0:
            b.append("nam am %.2f" % r["ret"])
        yb[y] = b
        if b:
            bad.append("%d(%s)" % (y, ",".join(b)))
    return (len(bad) == 0), bad, yb


def dropk(d, frac=None, k=None, side="best"):
    """Bo K leg tot nhat; tra ve dPnL% (am = bo di lam MAT bay nhieu % PnL)."""
    n = len(d)
    kk = k if k is not None else max(1, int(math.ceil(frac * n)))
    kk = min(kk, n - 1) if n > 1 else 0
    if kk <= 0:
        return 0.0, 0
    o = d["pnl"].sort_values(ascending=(side == "worst")).index[:kk]
    tot0 = d["pnl"].sum()
    tot1 = d.drop(index=o)["pnl"].sum()
    return float((tot1 - tot0) / tot0 * 100.0), int(kk)


def main():
    k, jout = 6, None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--k":
            k = int(sys.argv[i + 1]); i += 2; continue
        if sys.argv[i] == "--json":
            jout = sys.argv[i + 1]; i += 2; continue
        i += 1
    W = C.inflate(k)
    have = [t for t, _, _ in ARMS if os.path.exists(
        os.path.join(KOUT, t, "storage", "printDone.csv"))]
    miss = [t for t, _, _ in ARMS if t not in have]
    print("=== KG0 (nen PRODUCTION FLATGRID KEEPLEG0) — %d chan | block-%dh %d rep seed %d "
          "| legacy %.2f / inflate(%d)=%.6f ===" % (
              len(have), BLOCK_H, NREP, SEED, LEGACY, k, W))
    print("    rao MOI: maxDD<=%.0f%% | UW<=%d | qmin>=%.0f%% | ko nam am | conc<=%.0f%%" % (
        DD_NEW, UW_NEW, Q_NEW, CONC_MAX))
    if miss:
        print("    [!] thieu: %s" % ", ".join(miss))

    # ---- [0] parity ----
    print("\n[0] CONG PARITY")
    p1 = md5(T170)
    print("    P1 %-12s md5=%s want=%s => %s" % (T170, p1, T170_MD5,
                                                 "PASS" if p1 == T170_MD5 else "FAIL"))
    if p1 != T170_MD5:
        print("*** P1 FAIL => DUNG, khong doc tiep. ***")
        return 3
    m_keep = md5(BASE)
    S0 = G.summary(BASE) if BASE in have else None
    n_ok = S0 and S0["n"] == KEEP_N
    eq_ok = S0 and abs(S0["end"] - KEEP_EQ) < 0.5
    md5_ok = (m_keep == KEEP_MD5)
    print("    P2 %-12s n=%s (want %d) equity=%s (want %d) md5=%s => %s" % (
        BASE, S0["n"] if S0 else "-", KEEP_N, ("%.0f" % S0["end"]) if S0 else "-", KEEP_EQ,
        (m_keep or "-")[:16], "PASS(n/eq)" if (n_ok and eq_ok) else "FAIL(n/eq)"))
    print("       byte-identical voi Oracle FG_KEEPLEG0 (md5 %s)? %s" % (
        KEEP_MD5[:16], "CO" if md5_ok else "KHONG (n/eq van la cong chinh)"))
    if not (n_ok and eq_ok):
        print("*** P2 FAIL => DUNG, khong doc tiep. ***")
        return 3
    if not md5_ok:
        print("       [!] md5 khac Oracle: n/equity khop => cung cau hinh, chi khac byte-level "
              "(vd ticker file vs aerospike). Ghi ro trong RESULT.")

    D = {t: G.trades(t) for t in have}
    S = {t: G.summary(t) for t in have}
    Y = {t: G.yearly_detail(t) for t in have}
    Gd = {t: guard(t) for t in have}
    F = {t: funding_term(t) for t in have}
    sc_of = {t: sc for t, sc, _ in ARMS}
    res = {"k": k, "inflate": W, "legacy": LEGACY, "parity": dict(p1=p1, p2_md5=m_keep),
           "md5": {t: md5(t) for t in have}, "guard": Gd, "summary": S, "yearly": Y,
           "funding": F, "ci": {}}

    # ---- [1] co che ----
    print("\n[1] CO CHE + chat luong lenh")
    print("%-9s %6s %7s %9s %9s %9s %9s %9s %8s %8s" % (
        "tag", "scale", "n", "win%", "TSloss%", "mP|SM", "mP|SL", "meanP", "hold_h", "turn"))
    for t in have:
        r = rates_row(t); s = S[t]
        print("%-9s %6.2f %7d %9.2f %9.2f %9.3f %9.3f %9.3f %8.1f %8.3f" % (
            t, sc_of[t], r["n"], r["win"], r["tsloss"], r["mp_sm"], r["mp_sl"], r["meanP"],
            s["hold_med"], s["turn"]))
    pairs = [(sc_of[t], S[t]["n"]) for t in SCALE_ARMS if t in have]
    pairs.sort()
    ns = [n for _, n in pairs]
    mono = all(ns[i] <= ns[i + 1] for i in range(len(ns) - 1))
    print("    thang gate-scale: %s => n %s => %s" % (
        ["%.2f:%d" % p for p in pairs],
        "GIAM DAN theo scale" if mono else "*** KHONG DON DIEU ***",
        "OK (co che dung chieu)" if mono else "ghi ro bat thuong"))
    if "kg0-cap" in have:
        g = Gd["kg0-cap"]
        print("    CAP: MODE pct=%s | SUMMARY blocked=%s | dong SKIP=%d | md5 %s" % (
            g["mode"], g["summary"], g["skip"], (md5("kg0-cap") or "-")[:12]))
        if (g["summary"] or 0) == 0 and g["skip"] == 0:
            print("    *** CANH BAO: blocked=0 => chan CAP nay la TAM THUONG (no-op tren nen nay) ***")
        if "kg0-g170" in have:
            print("    CAP bind? so leg bi chan (OFF %d -> ON %d), md5 OFF %s vs ON %s" % (
                S["kg0-g170"]["n"], S["kg0-cap"]["n"],
                (md5("kg0-g170") or "-")[:12], (md5("kg0-cap") or "-")[:12]))

    # ---- [2] CI ----
    print("\n[2] 5 RATE + CI vs MOC KEEPLEG0 (%s) — quyet dinh = ngoai CA HAI do rong" % BASE)
    for t in have:
        if t == BASE:
            continue
        rr = ci_block(t, BASE, k)
        res["ci"][t] = rr
    print("\n  [phu, KHONG quyet dinh] moi chan vs T170 (%s):" % T170)
    for t in have:
        rr = ci_block(t, T170, k, quiet=True)
        res["ci"]["%s_vs_T170" % t] = rr
        print("  %-9s TOT=%d/5 XAU=%d/5" % (t, rr["good"], rr["bad"]))

    # ---- [3] rao cung ----
    print("\n[3] RAO CUNG (MOI: dd<=40/uw<=250/q>=-20 | CU: 30/200/-15) — theo nam VA toan ky")
    print("%-9s %6s %10s %7s %9s %6s %8s %8s %7s %11s" % (
        "tag", "scale", "equity", "CAGR%", "maxDD%", "UW", "qmin%", "conc%", "n", "SumPnL"))
    for t in have:
        s = S[t]
        print("%-9s %6.2f %10.0f %7.2f %9.2f %6d %8.2f %8.2f %7d %11.0f" % (
            t, sc_of[t], s["end"], s["cagr"], s["maxDD"], s["uw"], s["qmin"], s["conc"],
            s["n"], s["sumpnl"]))
    gates = {}
    for t in have:
        gates[t] = dict(
            new=fence(S[t], Y[t], DD_NEW, UW_NEW, Q_NEW),
            old=fence(S[t], Y[t], DD_OLD, UW_OLD, Q_OLD))
    print("\n  THEO NAM (o = maxDD% / UW / ret% / qmin%; P/F theo rao MOI):")
    yrs = sorted({y for t in have for y in Y[t]})
    print("  %-9s %s" % ("tag", " ".join("%-28d" % y for y in yrs)))
    for t in have:
        cells = []
        for y in yrs:
            r = Y[t].get(y)
            if not r:
                cells.append("%-28s" % "-"); continue
            ok = (r["maxDD"] >= -DD_NEW and r["uw"] <= UW_NEW and r["qmin"] >= Q_NEW
                  and r["ret"] >= 0)
            cells.append("%7.2f/%4d/%+7.2f/%+7.2f %s" % (
                r["maxDD"], r["uw"], r["ret"], r["qmin"], "P" if ok else "F"))
        print("  %-9s %s" % (t, " ".join("%-28s" % c for c in cells)))
    print("\n  TOAN KY + theo nam:")
    for lab, key in (("MOI", "new"), ("CU", "old")):
        print("  RAO %s:" % lab)
        for t in have:
            ok, bad, yb = gates[t][key]
            print("  %-9s scale %.2f n=%5d %s" % (
                t, sc_of[t], S[t]["n"], "PASS" if ok else "FAIL (" + ", ".join(bad) + ")"))
    res["gates"] = gates

    # ---- [4] do venh ----
    print("\n[4] DO VENH THEO NAM (ret% nam): SD / range / min / max")
    print("%-9s %6s %9s %9s %9s %9s" % ("tag", "scale", "SD_pp", "range_pp", "min_pp", "max_pp"))
    disp = {}
    for t in have:
        rr = np.array([Y[t][y]["ret"] for y in sorted(Y[t])])
        disp[t] = dict(sd=float(np.std(rr, ddof=1)), rng=float(rr.max() - rr.min()),
                       mn=float(rr.min()), mx=float(rr.max()))
        print("%-9s %6.2f %9.2f %9.2f %9.2f %9.2f" % (
            t, sc_of[t], disp[t]["sd"], disp[t]["rng"], disp[t]["mn"], disp[t]["mx"]))
    res["disp"] = disp

    # ---- [5] PnL theo nam ----
    print("\n[5] *** BANG PnL CHI TIET THEO NAM (moi chan) ***")
    for t in have:
        s = S[t]
        print("\n  == %s (scale %.2f) == equity %.0f | toan ky: maxDD %.2f%% UW %d qmin %.2f "
              "conc %.2f SumPnL %.0f" % (
                  t, sc_of[t], s["end"], s["maxDD"], s["uw"], s["qmin"], s["conc"], s["sumpnl"]))
        print("  %-5s %6s %8s %8s %9s %12s %9s %9s %5s %8s %11s" % (
            "nam", "n", "win%", "TSloss%", "meanP", "PnL(USDT)", "ret%", "maxDD%", "UW", "qmin%",
            "equity"))
        for y in sorted(Y[t]):
            r = Y[t][y]
            print("  %-5d %6d %8.2f %8.2f %9.3f %12.0f %+9.2f %9.2f %5d %8.2f %11.0f" % (
                y, r["n"], r["win"], r["tsloss"], r["meanP"], r["pnl_usdt"], r["ret"],
                r["maxDD"], r["uw"], r["qmin"], r["eq_end"]))

    # ---- [6] funding ----
    print("\n[6] Σfunding / ΣPnL (do theo n)")
    print("%-9s %7s %13s %13s %11s" % ("tag", "n", "Sum funding", "SumPnL", "fund/PnL%"))
    for t in have:
        f = F[t]
        print("%-9s %7d %13.1f %13.0f %10.2f%%" % (
            t, S[t]["n"], f["funding_sum"], S[t]["sumpnl"], f["funding_over_pnl"]))

    # ---- [7] drop-top-K ----
    print("\n[7] drop-top-K (bo K leg TOT NHAT => dPnL%) — moc + diem scale tot nhat (xem [8])")
    dk = {}
    for t in have:
        row = {}
        for lab, frac in (("top1leg", None), ("top1pct", 0.01), ("top5pct", 0.05)):
            if lab == "top1leg":
                v, kk = dropk(D[t], k=1)
            else:
                v, kk = dropk(D[t], frac=frac)
            row[lab] = dict(dpnl=v, k=kk)
        dk[t] = row
    res["dropk"] = dk
    print("%-9s %6s %14s %14s %14s" % ("tag", "n", "top1leg", "top1%", "top5%"))
    for t in have:
        r = dk[t]
        print("%-9s %6d %13.2f%% %13.2f%% %13.2f%%" % (
            t, len(D[t]), r["top1leg"]["dpnl"], r["top1pct"]["dpnl"], r["top5pct"]["dpnl"]))
    mv = np.median([D[t]["pnl"].max() for t in have])
    print("    (moc: leg tot nhat %.0f USDT; 5%% leg tot nhat giu bao nhieu PnL)" % mv)

    # ---- [8] ket luan ----
    print("\n[8] KET LUAN (theo luat §4 pre-reg)")
    print("  %-9s %6s %7s %10s %10s %13s" % ("tag", "scale", "n", "R-MOI", "R-CU", "E-PASS(vs moc)"))
    for t in have:
        rn = gates[t]["new"][0]
        ro = gates[t]["old"][0]
        ep = res["ci"].get(t, {}).get("e_pass", False)
        print("  %-9s %6.2f %7d %10s %10s %13s" % (
            t, sc_of[t], S[t]["n"], "PASS" if rn else "FAIL", "PASS" if ro else "FAIL",
            "PASS" if ep else "FAIL"))
    cand = [(S[t]["n"], sc_of[t], t) for t in have if t != BASE and gates[t]["new"][0]]
    cand.sort(reverse=True)
    print("\n  (a) n theo scale: %s" % ("; ".join("%.2f -> %d" % p for p in pairs)))
    if cand:
        n_best, sc_best, t_best = cand[0]
        print("  (c) n CAO NHAT ma PASS TOAN BO rao khau vi MOI: scale %.2f (n=%d, %s) | R-CU %s | "
              "E-PASS %s" % (sc_best, n_best, t_best, "PASS" if gates[t_best]["old"][0] else "FAIL",
                             "PASS" if res["ci"].get(t_best, {}).get("e_pass") else "FAIL"))
        res["best_new"] = dict(tag=t_best, scale=sc_best, n=n_best)
    else:
        print("  (c) KHONG diem nao ngoai moc PASS rao khau vi MOI => tra loi 'khong co'")
        res["best_new"] = None
    res["arms"] = [dict(tag=t, scale=sc_of[t], n=S[t]["n"], equity=S[t]["end"], cagr=S[t]["cagr"],
                        maxDD=S[t]["maxDD"], uw=S[t]["uw"], qmin=S[t]["qmin"], conc=S[t]["conc"],
                        sumpnl=S[t]["sumpnl"]) for t in have]
    if jout:
        with open(jout, "w") as f:
            json.dump(res, f, indent=1, default=str)
        print("\n[json] %s" % jout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
