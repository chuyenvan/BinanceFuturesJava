#!/usr/bin/env python3
"""ARM44_SCORE — cham vong ARM44 (docs/prereg/PREREG_ARM44.md, commit 7eb4c2b).

3 kenh tren nen KEEPLEG0: MOC (45 deploy) | A45 (retrain 45, doi chung chan doan) | A44 (UNG VIEN, 44 cot).

  [0] CONG PARITY: P1 (md5/n/equity MOC) + P2 (funding/bins sha MOC) + jar sha + P3 (market/pred)
  [1] CO CHE: n / win% / TSloss% / mP|SM / mP|SL / meanP / hold / turn / SumFunding, SumPnL
  [2] 5 RATE + CI block-72h 2000 rep seed 20260905 vs MOC, o CA HAI do rong:
        `c3_rates.inflate(k=1) = 1.0` (CI GOC, khong no rong) va `legacy 1.21` (hang so repo `G.LEGACY`).
        Do rong QUYET DINH = 1.21; "ngoai CI" = ngoai CA HAI (= ngoai 1.21). KHONG bia he so.
      So chinh: A44 - MOC. Chan doan: A45 - MOC va A44 - A45 (hieu ung thuan cua viec bo 1 cot).
  [3] RAO CUNG (RISK_APPETITE §7) theo NAM + TOAN KY (maxDD/UW tren MTM MOC PHUT tu kernel sim-a44-mtm)
  [4] BANG PnL THEO NAM (n + PnL USDT) + TOTAL + equity cuoi cho CA 3 kenh
  [5] RULER CUA SELECTOR: rank-IC cross-section OOS + top-8 lift@8 (A44/A45 tu kernel; 45 deploy offline)
  [6] KET LUAN theo luat §5 pre-reg

Usage: python3 arm44_score.py [--k 1] [--out /path/arm44_score.json]
"""
import glob
import json
import logging
import os
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import numpy as np
import pandas as pd
import gd92xexit_score as G
import c3_rates as C
import stage2_score as S2

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOG = logging.getLogger("arm44_score")

KOUT = "/home/ubuntu/kaggle_sim/out"
SLUG = "sim-a44"
ARMS = ["moc", "A45", "A44"]
TAGS = {a: "%s-%s" % (SLUG, a.lower()) for a in ARMS}
LEGACY = G.LEGACY                     # 1.21 — hang so CO SAN trong repo, KHONG phai he so moi
KEEP_MD5 = "99e42b75cf1a2142f9cd14dc72e371ba"
MOC_FUND_MD5 = "8e57d900d5c54c744bfcaf5c9b27fc93"
MOC_BINS_SHA = "407e2abab3053a39a51dcb9f331d063b3e67196bf608ae061aee444cd2841ca5"
MARKET_MD5 = "4ab691c908fc545c26243e8328d7a0a6"
PRED_MD5 = "5dd6bb4c3f98d89d58770005c0001526"
JAR_SHA = "2c2f8aef78c98470fdc3b0d464edd7ec2c604a7589985b1f4211c1da05fcdca0"
DD_MAX, UW_MAX, Q_MIN, CONC_MAX = 40.0, 250, -20.0, 15.0
NAM = {2021: "2021H2"}
RULER_DIR = "/tmp/a44out"


def find_run_dir(arm):
    root = os.path.join(KOUT, TAGS[arm])
    for dp, _dn, fn in os.walk(root):
        if any("printdone" in f.lower().replace(" ", "") for f in fn):
            b = os.path.basename(dp)
            return os.path.dirname(dp) if b in ("storage", "logs") else dp
    return None


def find_json(arm, name):
    hits = glob.glob(os.path.join(KOUT, TAGS[arm]) + "/**/" + name, recursive=True)
    return sorted(hits)[0] if hits else None


def fence_year(py_min, py_daily):
    bad = []
    for y in sorted(py_min):
        m = py_min[y]
        if m["maxDD"] < -DD_MAX:
            bad.append("%d maxDD_phut %.2f" % (y, m["maxDD"]))
        if m["uw_days"] > UW_MAX:
            bad.append("%d UW_phut %.1f" % (y, m["uw_days"]))
        d = py_daily.get(y)
        if d and d.get("qmin") is not None and d["qmin"] < Q_MIN:
            bad.append("%d qmin %.2f" % (y, d["qmin"]))
        if d and d.get("ret", 0.0) < 0:
            bad.append("%d nam am %.2f" % (y, d["ret"]))
    return (len(bad) == 0), bad


def ci_block(ta, tb, W, label=None):
    """5 rate + CI ghep cap o CA HAI do rong. `out` (quyet dinh) = ngoai CA HAI."""
    c1 = G.ci_pair(ta, tb, LEGACY)
    c2 = G.ci_pair(ta, tb, W)
    ng = nb = 0
    det = {}
    lab = label or ("%s - %s" % (ta, tb))
    print("  -- %s --" % lab)
    print("  %-8s %10s %26s %26s %4s %4s %-4s" % (
        "rate", "hieu", "CI @%.2f (legacy)" % LEGACY, "CI @%.4f (inflate k=1)" % W, "outL", "outS", "HUONG"))
    for name, dirc in G.RATES:
        obs = c1[name][0]
        lo1, hi1, o1 = c1[name][1], c1[name][2], c1[name][3]
        lo2, hi2, o2 = c2[name][1], c2[name][2], c2[name][3]
        out = o1 and o2
        good = out and ((dirc > 0 and obs > 0) or (dirc < 0 and obs < 0))
        bad = out and not good
        ng += int(good); nb += int(bad)
        det[name] = dict(obs=float(obs), lo=float(lo1), hi=float(hi1),
                         lo_raw=float(lo2), hi_raw=float(hi2),
                         out_legacy=bool(o1), out_both=bool(out), good=bool(good), bad=bool(bad))
        print("  %-8s %+10.4f [%9.4f,%9.4f] [%9.4f,%9.4f] %4s %4s %-4s" % (
            name, obs, lo1, hi1, lo2, hi2, "Y" if o1 else "-", "Y" if o2 else "-",
            "TOT" if good else ("XAU" if bad else "-")))
    print("  >>> %s: TOT = %d/5 | XAU = %d/5" % (lab, ng, nb))
    return dict(good=ng, bad=nb, e_pass=bool(ng >= 2 and nb == 0), detail=det)


def find_mtm():
    hits = glob.glob(os.path.join(KOUT, "%s-mtm" % SLUG) + "/**/mtm_result.json", recursive=True)
    return json.load(open(sorted(hits)[0])) if hits else None


def find_tick(tag):
    for p in (os.path.join(RULER_DIR, "%s_perfold_ticks.parquet" % tag),):
        if os.path.exists(p):
            d = pd.read_parquet(p, columns=["ts", "fold", "ic", "lift8", "n_coin", "n8"])
            d["ts"] = d.ts.astype(np.int64)
            return d
    return None


def main():
    k = 1
    jout = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--k":
            k = int(sys.argv[i + 1]); i += 2; continue
        if sys.argv[i] == "--out":
            jout = sys.argv[i + 1]; i += 2; continue
        i += 1
    W = C.inflate(k)
    print("=== ARM44 SCORE — 3 kenh (moc | A45 retrain-control | A44 = bo cot 36 rvol15m) tren KEEPLEG0 ===")
    print("=== CI: block-%dh, %d rep, seed %d | inflate(k=%d)=%.6f (= CI goc) va legacy %.2f "
          "(do rong QUYET DINH) ===" % (G.BLOCK_H, G.NREP, G.SEED, k, W, LEGACY))
    have = {}
    for a in ARMS:
        d = find_run_dir(a)
        if d:
            have[a] = d
            G.DIRS[TAGS[a]] = d
    miss = [a for a in ARMS if a not in have]
    if miss:
        print("[!] thieu run dir: %s => DUNG" % ", ".join(miss))
        return 3

    RES = {}
    print("\n[0] CONG PARITY")
    for a in ARMS:
        rj = find_json(a, "result.json")
        R = json.load(open(rj)) if rj else {}
        RES[a] = dict(result=R)
        print("    %-4s md5=%s n=%s eq=%s | funding_md5=%s bins_sha=%s fold=%s | mapper=%s jar=%s "
              "market=%s pred=%s | sc=%s" % (
                  a, (R.get("md5_printdone") or "-")[:18], R.get("n_trades"), R.get("equity_final"),
                  (R.get("funding_md5") or "-")[:16], (R.get("bins_sha256") or "-")[:16],
                  R.get("fold_count"), R.get("mapper"), (R.get("jar_sha256") or "-")[:12],
                  (R.get("md5_market") or "-")[:12], (R.get("md5_pred") or "-")[:12],
                  (R.get("sc_sha256") or "-")[:12]))
    M = RES["moc"]["result"]
    p1 = (M.get("md5_printdone") == KEEP_MD5 and M.get("n_trades") == 1085 and M.get("equity_final") == 103083)
    p2 = M.get("funding_md5") == MOC_FUND_MD5 and M.get("bins_sha256") == MOC_BINS_SHA
    p3 = all(RES[a]["result"].get("md5_market") == MARKET_MD5 and
             RES[a]["result"].get("md5_pred") == PRED_MD5 for a in ARMS)
    p5 = all(RES[a]["result"].get("jar_sha256") == JAR_SHA for a in ARMS)
    print("    P1 (moc = moc Kaggle 99e42b75/1085/103083): %s" % ("PASS" if p1 else "*** FAIL ***"))
    print("    P2 (funding 8e57d900 + bins 407e2aba):        %s" % ("PASS" if p2 else "*** FAIL ***"))
    print("    P3 (market/pred nguyen byte cua bundle):     %s" % ("PASS" if p3 else "*** FAIL ***"))
    print("    P5 (jar sha 2c2f8aef):                       %s" % ("PASS" if p5 else "*** FAIL ***"))
    if not (p1 and p2):
        print("*** P1/P2 FAIL => DUNG, khong doc so kinh te. ***")
        return 4

    print("\n[1] CO CHE + chat luong lenh")
    print("%-4s %6s %7s %8s %8s %8s %8s %8s %7s %7s %11s %11s" % (
        "kenh", "n", "win%", "TSloss%", "mP|SM", "mP|SL", "meanP", "hold_med", "turn", "n_days",
        "SumFunding", "SumPnL"))
    D, S, Y = {}, {}, {}
    for a in ARMS:
        t = TAGS[a]
        D[a] = G.trades(t); S[a] = G.summary(t); Y[a] = G.yearly_detail(t)
        d = D[a]
        sm = d.loc[d.status == "STOP_MARKET_DONE", "profit"].mean()
        sl = d.loc[d.status == "STOP_LOSS_DONE", "profit"].mean()
        fs = float(pd.to_numeric(d.get("funding", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
        print("%-4s %6d %7.2f %8.2f %8.3f %8.3f %8.3f %8.1f %7.3f %7d %11.0f %11.0f" % (
            a, len(d), 100.0 * (d.profit > 0).mean(), 100.0 * (d.status == "STOP_LOSS_DONE").mean(),
            sm, sl, d.profit.mean(), S[a]["hold_med"], S[a]["turn"], S[a]["ndays"], fs, S[a]["sumpnl"]))
        RES[a]["funding_sum"] = fs

    print("\n[2] 5 RATE + CI (GHÉP CẶP, block-%dh) — so chinh vs MOC; chan doan A45" % G.BLOCK_H)
    RES["ci"] = {}
    RES["ci"]["A44_vs_MOC"] = ci_block(TAGS["A44"], TAGS["moc"], W, label="A44 - MOC (CHINH)")
    RES["ci"]["A45_vs_MOC"] = ci_block(TAGS["A45"], TAGS["moc"], W, label="A45 - MOC (nen nhieu retrain)")
    RES["ci"]["A44_vs_A45"] = ci_block(TAGS["A44"], TAGS["A45"], W, label="A44 - A45 (hieu ung thuan bo 1 cot)")

    print("\n[3] RAO CUNG — MTM MOC PHUT (maxDD/UW) + chuoi NGAY (qmin/nam am/conc)")
    MTM = find_mtm() or {}
    if not MTM:
        print("    [!] KHONG thay mtm_result.json (%s-mtm) => maxDD/UW chi con chuoi NGAY" % SLUG)
    else:
        print("    MTM phut: rc=%s | md5 khop? %s" % (
            MTM.get("rc"),
            {a: ((MTM.get("md5") or {}).get(a, "")[:16] ==
                 (RES[a]["result"].get("md5_printdone") or "")[:16]) for a in ARMS}))
    print("%-4s %10s %9s %8s %8s %8s %8s %9s %8s %9s %11s" % (
        "kenh", "equity", "CAGR%", "maxDD_d", "UW_d", "maxDD_m", "UW_m(d)", "maxDD_mL", "qmin%", "conc%", "SumPnL"))
    FENCE = {}
    for a in ARMS:
        I = (MTM.get("stats") or {}).get(a)
        s = S[a]
        mn = I.get("minute", {}) if I else {}
        py_min = {int(y): v for y, v in ((I.get("py_min") or {}) if I else {}).items()}
        yy = {}
        for y, r in Y[a].items():
            yy[y] = dict(maxDD=py_min.get(y, {}).get("maxDD", r["maxDD"]),
                         uw=py_min.get(y, {}).get("uw_days", r["uw"]),
                         qmin=r["qmin"], ret=r["ret"])
        ok, bad = fence_year(py_min, Y[a])
        okw = (mn.get("maxDD", s["maxDD"]) >= -DD_MAX and mn.get("uw_days", s["uw"]) <= UW_MAX
               and s["conc"] <= CONC_MAX and all(v["ret"] >= 0 for v in Y[a].values()))
        FENCE[a] = dict(ok_year=ok, bad_year=bad, ok_whole=bool(okw), per_year=yy,
                        checks=(MTM.get("checks") or {}), minute=mn)
        print("%-4s %10.0f %9.2f %8.2f %8d %8.2f %8.1f %8.2f %9.2f %9.2f %11.0f  %s%s" % (
            a, s["end"], s["cagr"], s["maxDD"], s["uw"], mn.get("maxDD", float("nan")),
            mn.get("uw_days", float("nan")), mn.get("maxDD_low", float("nan")), s["qmin"], s["conc"],
            s["sumpnl"], "PASS" if (ok and okw) else "FAIL", (" [" + ", ".join(bad) + "]") if bad else ""))
    print("\n  THEO NAM — maxDD_phut% / UW_phut(ngay) / ret% / qmin% / Ok?")
    yrs = sorted({y for a in ARMS for y in FENCE[a]["per_year"]})
    print("  %-4s %s" % ("kenh", " ".join("%-34s" % NAM.get(y, y) for y in yrs)))
    for a in ARMS:
        cells = []
        for y in yrs:
            r = FENCE[a]["per_year"].get(y)
            if not r:
                cells.append("%-34s" % "-"); continue
            ok = (r["maxDD"] >= -DD_MAX and r["uw"] <= UW_MAX and r["qmin"] >= Q_MIN and r["ret"] >= 0)
            cells.append("%8.2f/%6.1f/%+7.2f/%+7.2f %s" % (
                r["maxDD"], r["uw"], r["ret"], r["qmin"], "P" if ok else "F"))
        print("  %-4s %s" % (a, " ".join("%-34s" % c for c in cells)))
    print("\n  Cong nghiem thu MTM phut (V1/V2rel/V3/V5):")
    for a in ARMS:
        ck = FENCE[a]["checks"]
        if not ck:
            print("    %-4s (khong co MTM)" % a); continue
        print("    %-4s V1 diff=%.2f | V2rel=%.4f%% | V3=%.3f%% | V5=%.3f pp" % (
            a, ck.get("V1_" + a, {}).get("diff", float("nan")),
            ck.get("V2rel_" + a, {}).get("rel_pct", float("nan")),
            ck.get("V3_" + a, {}).get("rel_pct", float("nan")),
            ck.get("V5_" + a, {}).get("d_pp", float("nan"))))

    print("\n[4] *** BANG PnL THEO NAM (n + PnL USDT) ***")
    print("%-4s %s %s" % ("kenh", " ".join("%-19s" % NAM.get(y, y) for y in yrs), "%-22s" % "TOTAL"))
    for a in ARMS:
        cells, tn, tp = [], 0, 0.0
        for y in yrs:
            r = Y[a].get(y)
            if not r:
                cells.append("%-19s" % "-"); continue
            cells.append("%6d/%+11.0f" % (r["n"], r["pnl_usdt"]))
            tn += r["n"]; tp += r["pnl_usdt"]
        print("%-4s %s %-22s equity=%.0f" % (a, " ".join("%-19s" % c for c in cells),
                                             "%6d/%+11.0f" % (tn, tp), S[a]["end"]))

    print("\n[5] RULER CUA SELECTOR — rank-IC cross-section + lift@8 (16 fold OOS, theo tung tick)")
    TK = {t: find_tick(t) for t in ("A45", "A44", "45deploy")}
    RUL = {}
    if all(v is not None for v in TK.values()):
        based = TK["45deploy"].set_index("ts")
        for t in ("A45", "A44"):
            x = TK[t]
            v = x.ic.dropna()
            lo, hi = S2.block_boot_mean(v.values, x.loc[v.index, "ts"].values)
            lv = x.lift8.dropna()
            lo2, hi2 = S2.block_boot_mean(lv.values, x.loc[lv.index, "ts"].values)
            RUL[t] = dict(n_tick=int(len(x)), ic=float(x.ic.mean()), ic_ci=[lo, hi],
                          lift8=float(x.lift8.mean()), lift8_ci=[lo2, hi2],
                          n_coin_mean=float(x.n_coin.mean()))
            print("    %-8s n_tick=%-7d rank-IC=%+.6f [%+.6f,%+.6f] | lift@8=%+.6f [%+.6f,%+.6f]" % (
                t, RUL[t]["n_tick"], RUL[t]["ic"], lo, hi, RUL[t]["lift8"], lo2, hi2))
        for t in ("A45", "A44"):
            X = TK[t].set_index("ts")
            idx = X.index.intersection(based.index)
            for m in ("ic", "lift8"):
                dl = (X.loc[idx, m] - based.loc[idx, m]).dropna()
                lo, hi = S2.block_boot_mean(dl.values, dl.index.values)
                me = float(dl.mean())
                RUL["%s_minus_45deploy_%s" % (t, m)] = dict(mean=me, ci=[lo, hi],
                                                            n=int(len(dl)), ngoai_0=bool(lo > 0 or hi < 0))
                print("    %-8s DELTA_%-5s vs 45-deploy: %+.6f [%+.6f,%+.6f] %s" % (
                    t, m, me, lo, hi, "NGOAI 0" if (lo > 0 or hi < 0) else "-"))
        X = TK["A44"].set_index("ts"); Yb = TK["A45"].set_index("ts")
        idx = X.index.intersection(Yb.index)
        for m in ("ic", "lift8"):
            dl = (X.loc[idx, m] - Yb.loc[idx, m]).dropna()
            lo, hi = S2.block_boot_mean(dl.values, dl.index.values)
            me = float(dl.mean())
            RUL["A44_minus_A45_%s" % m] = dict(mean=me, ci=[lo, hi], n=int(len(dl)),
                                               ngoai_0=bool(lo > 0 or hi < 0))
            print("    A44 - A45 DELTA_%-5s: %+.6f [%+.6f,%+.6f] %s" % (
                m, me, lo, hi, "NGOAI 0" if (lo > 0 or hi < 0) else "-"))
    else:
        print("    [!] thieu per-fold-ticks: %s" % {t: (TK[t] is not None) for t in TK})

    print("\n[6] KET LUAN (luat §5 pre-reg: >=2 rate TOT ngoai CI + het rao §7 + 0 rate XAU + "
          "khong XAU hon maxDD/UW MTM phut)")
    VERD = {}
    for a in ("A44", "A45"):
        ci = RES["ci"]["%s_vs_MOC" % a]
        fence_ok = FENCE[a]["ok_year"] and FENCE[a]["ok_whole"]
        dd_ok = (FENCE[a]["minute"].get("maxDD", -1e9) >= FENCE["moc"]["minute"].get("maxDD", -1e9)
                 and FENCE[a]["minute"].get("uw_days", 1e9) <= FENCE["moc"]["minute"].get("uw_days", 1e9))
        good = (ci["good"] >= 2 and ci["bad"] == 0 and fence_ok and dd_ok)
        VERD[a] = dict(good=bool(good), tot=ci["good"], xau=ci["bad"], fence_year=FENCE[a]["ok_year"],
                       fence_whole=FENCE[a]["ok_whole"], dd_uw_ok=bool(dd_ok))
        print("    %-4s n=%d TOT=%d/5 XAU=%d/5 rao_nam=%s rao_toanky=%s dd/uw<=moc=%s => %s" % (
            a, S[a]["n"], ci["good"], ci["bad"], "PASS" if FENCE[a]["ok_year"] else "FAIL",
            "PASS" if FENCE[a]["ok_whole"] else "FAIL", "Y" if dd_ok else "N",
            "THAY DUOC MOC (GIU 44)" if a == "A44" and good else "NULL (giu 45)"))
    print("    (A45 la DOI CHUNG CHAN DOAN — khong bao gio duoc 'GIU/DOI')")
    out = dict(k=k, inflate=W, legacy=LEGACY, gates=dict(P1=bool(p1), P2=bool(p2), P3=bool(p3), P5=bool(p5)),
               summary=S, yearly=Y, ci=RES["ci"], fence=FENCE, verdict=VERD, ruler=RUL,
               results={a: RES[a]["result"] for a in ARMS},
               funding={a: RES[a].get("funding_sum") for a in ARMS},
               mtm={a: (MTM.get("stats") or {}).get(a) for a in ARMS})
    if jout:
        with open(jout, "w") as f:
            json.dump(out, f, indent=1, default=str)
        print("\nJSON -> %s" % jout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
