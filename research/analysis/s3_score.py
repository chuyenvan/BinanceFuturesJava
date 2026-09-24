#!/usr/bin/env python3
"""S3_SCORE — cham 4 kenh cua vong Stage 3 SIM (docs/prereg/PREREG_STAGE3_SIM.md).

Doi tuong so CI/rao cung = MOC (bins 45-feature, = kg0-g170). Cau hoi: cat 45->21 co lam he
thong te di khong; V1/V5 vs V0 co phan biet duoc feature that voi nhieu khong.

  [0] CONG PARITY: P1 (md5/n/equity cua MOC) + P2 (funding/bins sha cua MOC) + jar sha
  [1] CO CHE: n / win% / TSloss% / mP|SM / mP|SL / meanP / hold / turn / SumFunding, SumPnL
  [2] 5 RATE + CI block-72h 2000 rep seed 20260905 GHÉP CẶP vs MOC (CA HAI do rong: 1.21 + inflate(3))
      va phu: V1 vs V0, V5 vs V0
  [3] RAO CUNG (RISK_APPETITE §7) theo NAM + TOAN KY: maxDD/UW tren MTM MOC PHUT (JSON tu kernel);
      qmin/conc/nam am tren chuoi NGAY
  [4] BANG PnL THEO NAM (n + PnL USDT) cho 4 kenh + TOTAL + equity cuoi
  [5] KET LUAN theo luat §4 pre-reg

Usage: python3 s3_score.py [--k 3] [--out /path/result.json]
"""
import glob
import gzip
import json
import logging
import math
import os
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import numpy as np
import pandas as pd
import gd92xexit_score as G
import c3_rates as C

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOG = logging.getLogger("s3_score")

KOUT = "/home/ubuntu/kaggle_sim/out"
ARMS = ["moc", "V0", "V1", "V5"]
TAGS = {a: "s3-" + a.lower() for a in ARMS}
LEGACY = 1.21
KEEP_MD5 = "99e42b75cf1a2142f9cd14dc72e371ba"
MOC_FUND_MD5 = "8e57d900d5c54c744bfcaf5c9b27fc93"
MOC_BINS_SHA = "407e2abab3053a39a51dcb9f331d063b3e67196bf608ae061aee444cd2841ca5"
DD_MAX, UW_MAX, Q_MIN, CONC_MAX = 40.0, 250, -20.0, 15.0
NAM = {2021: "2021H2"}


def find_run_dir(arm):
    """Thu muc chua storage/printDone.csv trong output da keo ve."""
    root = os.path.join(KOUT, TAGS[arm])
    for dp, _dn, fn in os.walk(root):
        if any("printdone" in f.lower().replace(" ", "") for f in fn):
            return dp
    return None


def find_json(arm, name):
    root = os.path.join(KOUT, TAGS[arm])
    hits = [p for p in glob.glob(root + "/**/" + name, recursive=True)]
    return sorted(hits)[0] if hits else None


def parse_manifest(p):
    d = {}
    if not p or not os.path.exists(p):
        return d
    for ln in open(p):
        if "=" in ln:
            k, v = ln.rstrip("\n").split("=", 1)
            d[k.strip()] = v.strip()
    return d


def fence_year(py_min, py_daily):
    """(ok, list ly do) — rao cung §7 theo TUNG NAM (maxDD/UW = MTM phut; qmin/nam am = chuoi ngay)."""
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


def ci_block(ta_tag, tb_tag, W, quiet=False, label=None):
    """5 rate + CI ghep cap (block-72h) o CA HAI do rong. Tra dict good/bad/e_pass/detail."""
    c1 = G.ci_pair(ta_tag, tb_tag, LEGACY)
    c2 = G.ci_pair(ta_tag, tb_tag, W)
    ng = nb = 0
    det = {}
    lab = label or ("%s - %s" % (ta_tag, tb_tag))
    if not quiet:
        print("  -- %s --" % lab)
        print("  %-8s %10s %26s %26s %4s %4s %-4s" % (
            "rate", "hieu", "CI @1.21", "CI @%.4f" % W, "outL", "outS", "HUONG"))
    for name, dirc in G.RATES:
        obs = c1[name][0]
        lo1, hi1, o1 = c1[name][1], c1[name][2], c1[name][3]
        lo2, hi2, o2 = c2[name][1], c2[name][2], c2[name][3]
        out = o1 and o2
        good = out and ((dirc > 0 and obs > 0) or (dirc < 0 and obs < 0))
        bad = out and not good
        ng += int(good); nb += int(bad)
        det[name] = dict(obs=float(obs), lo=float(lo2), hi=float(hi2), out_legacy=bool(o1),
                         out_both=bool(out), good=bool(good), bad=bool(bad))
        if not quiet:
            print("  %-8s %+10.4f [%9.4f,%9.4f] [%9.4f,%9.4f] %4s %4s %-4s" % (
                name, obs, lo1, hi1, lo2, hi2, "Y" if o1 else "-", "Y" if o2 else "-",
                "TOT" if good else ("XAU" if bad else "-")))
    if not quiet:
        print("  >>> %s: TOT ngoai CI (ca hai do rong) = %d/5 | XAU = %d/5" % (lab, ng, nb))
    return dict(good=ng, bad=nb, e_pass=bool(ng >= 2 and nb == 0), detail=det)


def main():
    k = 3
    jout = None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--k":
            k = int(sys.argv[i + 1]); i += 2; continue
        if sys.argv[i] == "--out":
            jout = sys.argv[i + 1]; i += 2; continue
        i += 1
    W = C.inflate(k)
    print("=== S3 SCORE — 4 kenh (moc | V0 | V1 | V5) tren nen KEEPLEG0 | block-%dh %d rep seed %d "
          "| legacy %.2f / inflate(%d)=%.6f ===" % (G.BLOCK_H, G.NREP, G.SEED, LEGACY, k, W))
    have = {}
    for a in ARMS:
        d = find_run_dir(a)
        if d:
            have[a] = d
            G.DIRS[TAGS[a]] = d
    miss = [a for a in ARMS if a not in have]
    if miss:
        print("[!] thieu: %s => DUNG" % ", ".join(miss))
        return 3

    # ---------------- [0] parity ----------------
    RES = {}
    print("\n[0] CONG PARITY (dieu kien doc so)")
    for a in ARMS:
        rj = find_json(a, "result.json")
        R = json.load(open(rj)) if rj else {}
        RES[a] = dict(result=R)
        if a != "moc":
            continue
        ok_md5 = R.get("md5_printdone") == KEEP_MD5
        ok_n = R.get("n_trades") == 1085
        ok_eq = R.get("equity_final") == 103083
        print("    P1 md5=%s (want %s) %s | n=%s (want 1085) %s | eq=%s (want 103083) %s" % (
            (R.get("md5_printdone") or "-")[:16], KEEP_MD5[:16], "PASS" if ok_md5 else "*** FAIL ***",
            R.get("n_trades"), "PASS" if ok_n else "*** FAIL ***",
            R.get("equity_final"), "PASS" if ok_eq else "*** FAIL ***"))
        print("    P2 funding md5=%s (want %s) %s | bins sha=%s (want %s) %s" % (
            (R.get("funding_md5") or "-")[:16], MOC_FUND_MD5[:16],
            "PASS" if R.get("funding_md5") == MOC_FUND_MD5 else "*** FAIL ***",
            (R.get("bins_sha256") or "-")[:16], MOC_BINS_SHA[:16],
            "PASS" if R.get("bins_sha256") == MOC_BINS_SHA else "*** FAIL ***"))
        print("    jar sha=%s | mapper=%s | foldCount=%s | leakFreeFrom=%s | market/pred=%%s/%%s" % (
            (R.get("jar_sha256") or "-")[:16], R.get("mapper"), R.get("fold_count"),
            R.get("leak_free_from")) % ((R.get("md5_market") or "-")[:12], (R.get("md5_pred") or "-")[:12]))
        if not (ok_md5 and ok_n and ok_eq):
            print("*** P1 FAIL => DUNG, khong doc so kinh te. ***")
            return 4
    print("    (3 kenh con lai: cung market/pred NGUYEN BYTE + cung jar; chi khac BINS)")
    for a in ARMS:
        R = RES[a]["result"]
        print("      %-3s bins_sha=%s funding_md5=%s fold=%s sc_sha=%s" % (
            a, (R.get("bins_sha256") or "-")[:16], (R.get("funding_md5") or "-")[:16],
            R.get("fold_count"), (R.get("sc_sha256") or "-")[:12]))

    # ---------------- [1] co che ----------------
    print("\n[1] CO CHE + chat luong lenh")
    print("%-4s %6s %7s %8s %8s %8s %8s %8s %7s %7s %11s %11s" % (
        "kenh", "n", "win%", "TSloss%", "mP|SM", "mP|SL", "meanP", "hold_med", "turn",
        "n_days", "SumFunding", "SumPnL"))
    D, S, Y = {}, {}, {}
    for a in ARMS:
        t = TAGS[a]
        D[a] = G.trades(t)
        S[a] = G.summary(t)
        Y[a] = G.yearly_detail(t)
        d = D[a]
        sm = d.loc[d.status == "STOP_MARKET_DONE", "profit"].mean()
        sl = d.loc[d.status == "STOP_LOSS_DONE", "profit"].mean()
        fs = float(pd.to_numeric(d.get("funding", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
        print("%-4s %6d %7.2f %8.2f %8.3f %8.3f %8.3f %8.1f %7.3f %7d %11.0f %11.0f" % (
            a, len(d), 100.0 * (d.profit > 0).mean(), 100.0 * (d.status == "STOP_LOSS_DONE").mean(),
            sm, sl, d.profit.mean(), S[a]["hold_med"], S[a]["turn"], S[a]["ndays"], fs, S[a]["sumpnl"]))
        RES[a]["funding_sum"] = fs

    # ---------------- [2] rates + CI ----------------
    print("\n[2] 5 RATE + CI GHÉP CẶP (quyet dinh: ngoai CA HAI do rong)")
    RES["ci"] = {}
    for a in ("V0", "V1", "V5"):
        RES["ci"]["%s_vs_MOC" % a] = ci_block(TAGS[a], TAGS["moc"], W)
    print("\n  [phu — cau hoi 2: feature that vs nhieu]")
    RES["ci"]["V1_vs_V0"] = ci_block(TAGS["V1"], TAGS["V0"], W, label="V1 - V0")
    RES["ci"]["V5_vs_V0"] = ci_block(TAGS["V5"], TAGS["V0"], W, label="V5 - V0")
    print("\n  [phu — doi chieu 2 kenh 'thua' ngoai CI: V1 vs V5]")
    RES["ci"]["V1_vs_V5"] = ci_block(TAGS["V1"], TAGS["V5"], W, label="V1 - V5")

    # ---------------- [3] rao cung ----------------
    print("\n[3] RAO CUNG — MTM MOC PHUT (maxDD/UW) + chuoi NGAY (qmin/nam am/conc)")
    print("%-4s %10s %9s %8s %8s %8s %8s %8s %9s %11s" % (
        "kenh", "equity", "CAGR%", "maxDD_d", "UW_d", "maxDD_m", "UW_m(d)", "qmin%", "conc%", "SumPnL"))
    FENCE = {}
    for a in ARMS:
        I = RES[a]["result"].get("intraday")
        s = S[a]
        mn = I["stats"]["minute"] if I else {}
        py_min = I["stats"]["py_min"] if I else {}
        pad = {int(y): v for y, v in (py_min or {}).items()}
        yy = {}
        for y, r in Y[a].items():
            yy[y] = dict(maxDD=pad.get(y, {}).get("maxDD", r["maxDD"]),
                         uw=pad.get(y, {}).get("uw_days", r["uw"]),
                         qmin=r["qmin"], ret=r["ret"])
        ok, bad = fence_year(pad, Y[a])
        okw = (mn.get("maxDD", s["maxDD"]) >= -DD_MAX and mn.get("uw_days", s["uw"]) <= UW_MAX
               and s["conc"] <= CONC_MAX and all(v["ret"] >= 0 for v in Y[a].values()))
        FENCE[a] = dict(ok_year=ok, bad_year=bad, ok_whole=bool(okw), per_year=yy,
                        checks=(I or {}).get("checks", {}))
        print("%-4s %10.0f %9.2f %8.2f %8d %8.2f %8.1f %8.2f %9.2f %11.0f  %s%s" % (
            a, s["end"], s["cagr"], s["maxDD"], s["uw"], mn.get("maxDD", float("nan")),
            mn.get("uw_days", float("nan")), s["qmin"], s["conc"], s["sumpnl"],
            "PASS" if (ok and okw) else "FAIL", (" [" + ", ".join(bad) + "]") if bad else ""))
    print("\n  THEO NAM — maxDD_phut% / UW_phut(ngay) / ret% / qmin% / Ok?")
    yrs = sorted({y for a in ARMS for y in FENCE[a]["per_year"]})
    print("  %-4s %s" % ("kenh", " ".join("%-34s" % (NAM.get(y, y)) for y in yrs)))
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
    print("\n  Cong nghiem thu MTM phut (V1/V2rel/V3/V5) cua tung kenh:")
    for a in ARMS:
        ck = FENCE[a]["checks"]
        if not ck:
            print("    %-4s (khong co JSON intraday)" % a); continue
        v1 = ck.get("V1_" + a, {}).get("diff")
        v2 = ck.get("V2rel_" + a, {}).get("rel_pct")
        v3 = ck.get("V3_" + a, {}).get("rel_pct")
        v5 = ck.get("V5_" + a, {}).get("d_pp")
        print("    %-4s V1 diff=%.2f | V2rel=%.4f%% | V3=%.3f%% | V5=%.3f pp | low maxDD=%.2f%%" % (
            a, v1, v2, v3, v5, RES[a]["result"]["intraday"]["stats"]["minute"].get("maxDD_low", float("nan"))))

    # ---------------- [4] PnL theo nam ----------------
    print("\n[4] *** BANG PnL THEO NAM (n + PnL USDT) ***")
    print("%-4s %s %s" % ("kenh", " ".join("%-19s" % NAM.get(y, y) for y in yrs),
                          "%-22s" % "TOTAL"))
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
    for a in ARMS:
        print("    %-4s chi tiet: %s" % (a, " | ".join(
            "%s n=%d PnL=%+.0f ret=%+.2f%% maxDD=%+.2f%%" % (
                NAM.get(y, y), Y[a][y]["n"], Y[a][y]["pnl_usdt"], Y[a][y]["ret"], Y[a][y]["maxDD"])
            for y in sorted(Y[a]))))

    # ---------------- [5] ket luan ----------------
    print("\n[5] KET LUAN (luat §4 pre-reg: >=2 rate TOT ngoai CI + het rao + 0 rate XAU)")
    print("%-4s %6s %8s %8s %10s %10s %14s" % ("kenh", "n", "TOT/5", "XAU/5", "rao_nam", "rao_toanky", "PHAN QUYET"))
    VERD = {}
    for a in ARMS:
        if a == "moc":
            continue
        ci = RES["ci"]["%s_vs_MOC" % a]
        good = ci["good"] >= 2 and ci["bad"] == 0 and FENCE[a]["ok_year"] and FENCE[a]["ok_whole"]
        VERD[a] = dict(good=good, tot=ci["good"], xau=ci["bad"],
                       fence_year=FENCE[a]["ok_year"], fence_whole=FENCE[a]["ok_whole"])
        print("%-4s %6d %8d %8d %10s %10s %14s" % (
            a, S[a]["n"], ci["good"], ci["bad"],
            "PASS" if FENCE[a]["ok_year"] else "FAIL", "PASS" if FENCE[a]["ok_whole"] else "FAIL",
            "GIU/DOI" if good else "NULL"))
    # V1/V5 vs V0 (cau hoi 2)
    for a in ("V1", "V5"):
        ci = RES["ci"]["%s_vs_V0" % a]
        print("    phan biet duoc khong: %s vs V0 => TOT=%d/5 XAU=%d/5 %s" % (
            a, ci["good"], ci["bad"], "CO khac biet" if (ci["good"] + ci["bad"]) else "KHONG (ngoai CI)"))
    out = dict(k=k, inflate=W, legacy=LEGACY, summary=S, yearly=Y, ci=RES["ci"],
               fence=FENCE, verdict=VERD, results={a: RES[a]["result"] for a in ARMS},
               funding={a: RES[a].get("funding_sum") for a in ARMS})
    if jout:
        with open(jout, "w") as f:
            json.dump(out, f, indent=1, default=str)
        print("\nJSON -> %s" % jout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
