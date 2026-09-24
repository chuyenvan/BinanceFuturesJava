"""EXIT-HIGH-N scorer — cham diem 9 chan cua docs/prereg/PREREG_EXIT_HIGH_N.md.

  - 5 rate chat luong vs BASELINE CUA CHINH NEN (nen G: hn-g92; nen T: hn-t100)
  - CI block-72h, 2000 rep, seed 20260905, anchor 2021-07-01, CA HAI do rong
    (legacy x1.21 + chuan hoa inflate(k=3)=1.482304)
  - rao cung RISK_APPETITE: CA theo nam LAN toan ky
  - BANG PnL CHI TIET THEO NAM (9 chan)
  - n / hold / turnover / capture ratio (nhom dinh >=20/50/100%)

Usage: python3 exithighn_score.py [--k 3] [--json OUT.json]
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import gd92xexit_score as G
import c3_rates as C

# (tag, nhan, nen) — nen: 'G' (GD92), 'T' (T100), 'Z' (moc T170)
ARMS = [
    ("hn-par1", "par1 T170 (moc)", "Z"),
    ("hn-t100", "T100 base", "T"),
    ("hn-g92", "GD92 base", "G"),
    ("hn-g-hi", "GD92 + HINGE V3", "G"),
    ("hn-g-la", "GD92 + LADDER L1", "G"),
    ("hn-g-cp", "GD92 + CAP 10/30", "G"),
    ("hn-t-hi", "T100 + HINGE V3", "T"),
    ("hn-t-la", "T100 + LADDER L1", "T"),
    ("hn-t-cp", "T100 + CAP 10/30", "T"),
]
BASE_OF = {"G": "hn-g92", "T": "hn-t100", "Z": "hn-par1"}
EXIT_ARMS = [a for a in ARMS if a[2] in ("G", "T") and not a[0].endswith("92") and "base" not in a[1]]


def ci_table(v, par, k):
    """In 1 khoi CI cua (v - par) o CA HAI do rong; tra ve (n_good, n_bad)."""
    c1 = G.ci_pair(v, par, G.LEGACY)
    c2 = G.ci_pair(v, par, C.inflate(k))
    ng = nb = 0
    print("  -- %s  (-  %s) --" % (v, par))
    print("  %-9s %11s %24s %28s %5s %5s %5s" % (
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
        det[name] = dict(obs=obs, lo=lo2, hi=hi2, out_legal1=bool(o1), out_both=bool(out),
                         good=bool(good), bad=bool(bad))
        print("  %-9s %+11.3f [%9.3f,%9.3f] [%9.3f,%9.3f] %5s %5s %5s" % (
            name, obs, lo1, hi1, lo2, hi2, "Y" if o1 else "-", "Y" if o2 else "-",
            "TOT" if good else ("XAU" if bad else "-")))
    print("  >>> %s vs %s: TOT ngoai CI (ca hai do rong) = %d/5 | XAU = %d/5" % (v, par, ng, nb))
    return ng, nb, det


def main():
    k = 3
    jout = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--k":
            k = int(sys.argv[i + 1]); i += 2; continue
        if sys.argv[i] == "--json":
            jout = sys.argv[i + 1]; i += 2; continue
        i += 1
    tags = [a[0] for a in ARMS]
    W = C.inflate(k)
    res = {"k": k, "inflate_k": W, "legacy": G.LEGACY, "ci": {}}

    print("=== EXIT-HIGH-N — 9 chan | block-%dh %d rep seed %d anchor %s | legacy %.2f / inflate(%d)=%.6f" % (
        G.BLOCK_H, G.NREP, G.SEED, G.ANCHOR.date(), G.LEGACY, k, W))
    D = {t: G.trades(t) for t in tags}
    S = {t: G.summary(t) for t in tags}
    Y = {t: G.yearly_detail(t) for t in tags}
    T = {t: G.trace(t) for t in tags}
    for t in tags:
        print("    trace[%-8s] = %s" % (t, "KHONG CO" if T[t] is None else "%d dong" % len(T[t])))

    print("\n=== (a) 5 RATE CHAT LUONG (toan bo leg) ===")
    print("%-10s %-20s %6s %8s %8s %10s %10s %10s" % (
        "tag", "nhan", "n", "win%", "TSloss%", "mP|SM", "mP|SL", "meanP"))
    for t, lab, _ in ARMS:
        d = D[t]
        sm = d.loc[d.status == "STOP_MARKET_DONE", "profit"]
        sl = d.loc[d.status == "STOP_LOSS_DONE", "profit"]
        print("%-10s %-20s %6d %8.2f %8.2f %10.3f %10.3f %10.3f" % (
            t, lab, len(d), 100.0 * (d.profit > 0).mean(),
            100.0 * (d.status == "STOP_LOSS_DONE").mean(),
            sm.mean() if len(sm) else float("nan"),
            sl.mean() if len(sl) else float("nan"), d.profit.mean()))

    print("\n=== (b) CI — MOC 1: exit arm vs BASELINE CUA CHINH NEN (cau hoi trung tam) ===")
    summ = {}
    for t, lab, basis in ARMS:
        if basis == "Z" or t in ("hn-g92", "hn-t100"):
            continue
        par = BASE_OF[basis]
        print("\n[nen %s] %s (%s)" % (basis, t, lab))
        ng, nb, det = ci_table(t, par, k)
        summ[t] = dict(vs=par, good=ng, bad=nb)
        res["ci"]["%s_vs_%s" % (t, par)] = det

    print("\n=== (b2) CI — MOC 2: tach rieng TAC DUNG GATE (GD92 base vs T100 base) ===")
    ng, nb, det = ci_table("hn-g92", "hn-t100", k)
    summ["hn-g92"] = dict(vs="hn-t100", good=ng, bad=nb)
    res["ci"]["hn-g92_vs_hn-t100"] = det

    print("\n=== (b3) CI — MOC 3: moi chan vs T170 (moc incumbent; 'T170 = 0/5' la tham chieu) ===")
    for t, lab, _ in ARMS:
        if t == "hn-par1":
            continue
        print("\n%s (%s)" % (t, lab))
        ng, nb, det = ci_table(t, "hn-par1", k)
        res["ci"]["%s_vs_hn-par1" % t] = det

    print("\n=== (c) RAO CUNG RISK_APPETITE (maxDD<=%.0f%%/nam VA toan ky, UW<=%d, quy>=%.0f%%, ko nam am, conc<=%.0f%%) ===" % (
        G.DD_MAX, G.UW_MAX, G.Q_MIN, G.CONC_MAX))
    print("%-10s %10s %7s %8s %6s %8s %8s %7s %7s %6s %8s" % (
        "tag", "equity", "CAGR%", "maxDD%", "UW", "qmin%", "conc%", "n", "hold_h", "turn", "SumPnL"))
    for t, lab, _ in ARMS:
        s = S[t]
        print("%-10s %10.0f %7.2f %8.2f %6d %8.2f %8.2f %7d %7.1f %6.3f %8.0f" % (
            t, s["end"], s["cagr"], s["maxDD"], s["uw"], s["qmin"], s["conc"],
            s["n"], s["hold_med"], s["turn"], s["sumpnl"]))
    print("\n  RAO CUNG THEO NAM:")
    yrs = sorted({y for t in tags for y in Y[t]})
    print("  %-10s %s" % ("tag", " ".join("%-26d" % y for y in yrs)))
    for t, lab, _ in ARMS:
        cells = []
        for y in yrs:
            r = Y[t].get(y)
            if not r:
                cells.append("%-26s" % "-")
                continue
            ok = (r["maxDD"] >= -G.DD_MAX and r["uw"] <= G.UW_MAX and r["qmin"] >= G.Q_MIN and r["ret"] >= 0)
            cells.append("%7.2f/%4d/%+7.2f %s" % (r["maxDD"], r["uw"], r["ret"], "P" if ok else "F"))
        print("  %-10s %s" % (t, " ".join("%-26s" % c for c in cells)))
    print("\n  RAO CUNG TOAN KY:")
    for t, lab, _ in ARMS:
        s = S[t]
        bad = []
        if s["maxDD"] < -G.DD_MAX:
            bad.append("maxDD %.2f" % s["maxDD"])
        if s["uw"] > G.UW_MAX:
            bad.append("UW %d" % s["uw"])
        if s["qmin"] < G.Q_MIN:
            bad.append("qmin %.2f" % s["qmin"])
        if s["conc"] > G.CONC_MAX:
            bad.append("conc %.2f" % s["conc"])
        neg = [y for y, r in Y[t].items() if r["ret"] < 0]
        if neg:
            bad.append("nam am %s" % neg)
        print("  %-10s %s" % (t, "PASS" if not bad else "FAIL (" + ", ".join(bad) + ")"))

    print("\n*** (d) BANG PnL CHI TIET THEO NAM ***")
    for t, lab, _ in ARMS:
        s = S[t]
        print("\n  == %s (%s) == equity cuoi %.0f | toan ky: maxDD %.2f%% UW %d qmin %.2f conc %.2f SumPnL %.0f" % (
            t, lab, s["end"], s["maxDD"], s["uw"], s["qmin"], s["conc"], s["sumpnl"]))
        print("  %-5s %6s %8s %8s %9s %12s %9s %9s %5s %8s %11s" % (
            "nam", "n", "win%", "TSloss%", "meanP", "PnL(USDT)", "ret%", "maxDD%", "UW", "qmin%", "equity"))
        for y in sorted(Y[t]):
            r = Y[t][y]
            print("  %-5d %6d %8.2f %8.2f %9.3f %12.0f %+9.2f %9.2f %5d %8.2f %11.0f" % (
                y, r["n"], r["win"], r["tsloss"], r["meanP"], r["pnl_usdt"], r["ret"],
                r["maxDD"], r["uw"], r["qmin"], r["eq_end"]))

    print("\n=== (e) BAT SONG LON (capture tu trailTrace.csv) ===")
    for lv in G.PEAK_LEVELS:
        print("\n  -- peak >= +%d%% --" % int(lv * 100))
        print("  %-10s %6s %11s %11s %12s %11s %12s" % (
            "tag", "n", "%trailing", "med_gap_pp", "med_capture", "mean_capture", "SumPnL"))
        for t, lab, _ in ARMS:
            r = G.bigmove(T[t], lv)
            if r is None or r.get("n", 0) == 0:
                print("  %-10s %6s" % (t, "KHONG CO TRACE" if r is None else 0))
                continue
            print("  %-10s %6d %11.1f %11.2f %12.3f %11.3f %12.1f" % (
                t, r["n"], r["pct_trailing"], r["med_gap_pp"], r["med_capture"],
                r["mean_capture"], r["sumPnL"]))
        res.setdefault("bigmove", {})["%d" % int(lv * 100)] = {t: G.bigmove(T[t], lv) for t, _, _ in ARMS}
    # moc T170 (tl-part) cho capture
    print("\n  (moc T170 co trailTrace: thu muc %s)" % G.base("T170T"))

    res["summary"] = S
    res["yearly"] = Y
    res["ci_summary"] = summ
    if jout:
        with open(jout, "w") as f:
            json.dump(res, f, indent=1, default=str)
        print("\n[json] %s" % jout)


if __name__ == "__main__":
    main()
