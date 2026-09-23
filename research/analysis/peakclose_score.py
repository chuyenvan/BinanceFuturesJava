"""PEAK-CLOSE scorer — cham chan F3 (dinh trailing do bang CLOSE) theo docs/PREREG_PEAK_CLOSE.md.

Doc output KAGGLE (/home/ubuntu/kaggle_sim/out/<tag>/). Dung lai may do cua `traillad_score.py`
(cung don vi LEG / cung block-72h / cung seed) — KHONG viet lai cong thuc.

Bao cao (theo pre-reg §3-4):
  (0) CONG PARITY: md5 printDone cua par & part phai == efb793e2468ca3a7318da0f0ad23d4fc
  (a) 5 rate chat luong (theo LEG) F3 vs parity + CI block-72h 2000 rep seed 20260905 o CA HAI
      do rong: x1.21 (legacy, brief) va inflate(1)=1.0 (chuan hoa). "Ngoai CI" = ngoai o CA HAI.
  (b) rang buoc cung RISK_APPETITE (maxDD<=30/nam, UW<=200, quy>=-15, khong nam am, conc<=15%) + theo nam
  (c) capture ratio nhom dinh >= 20/50/100% (tu trailTrace.csv, mau so = maePeak HIGH ca 2 chan):
      n, % bi cat som (exit reason), capture trung vi/trung binh/agg, SumPnL, meanP
  (d) PnL/equity bao RIENG (KHONG dung de chon)

Usage: python3 peakclose_score.py PARITY_TRACE_TAG VARIANT_TAG [--json OUT.json]
"""
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import traillad_score as T          # trades/equity/summary/levels/trace/bigmove/ci_pair/RATES
import c3_rates as C

KOUT = "/home/ubuntu/kaggle_sim/out"
MD5_REF = "efb793e2468ca3a7318da0f0ad23d4fc"
INFLATE_K1 = C.inflate(1)           # k=1 ung vien => 1.0 (khong no rong)
PEAK_LEVELS = (0.20, 0.50, 1.00)


def md5(tag):
    p = os.path.join(KOUT, tag, "storage", "printDone.csv")
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    pos, jout = [], None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--json":
            jout = sys.argv[i + 1]; i += 2; continue
        if sys.argv[i].startswith("--"):
            i += 1; continue
        pos.append(sys.argv[i]); i += 1
    parity, variant = pos[0], pos[1]
    tags = [parity, variant]

    print("=== PEAK-CLOSE SCORE — parity(trace)=%s | F3=%s" % (parity, variant))
    print("    CI block-%dh, %d rep, seed %d, anchor %s. Do rong: x1.21 (legacy) + inflate(1)=%.4f." % (
        C.BLOCK_H, C.NREP, C.SEED, T.ANCHOR.date(), INFLATE_K1))

    print("\n=== (0) CONG PARITY (printDone md5 phai == %s) ===" % MD5_REF)
    md5s = {}
    for t in tags + ["par"] if "par" not in tags else tags:
        if not os.path.exists(os.path.join(KOUT, t, "storage", "printDone.csv")):
            continue
        md5s[t] = md5(t)
        print("    %-10s %s  %s" % (t, md5s[t], "PASS" if md5s[t] == MD5_REF else "**FAIL**"))
    print("    (par = chan KHONG override TS_PEAK_MODE — neu co mat)")

    D = {t: T.trades(t) for t in tags}
    S = {t: T.summary(t) for t in tags}
    L = {t: T.levels(D[t]) for t in tags}
    TR = {t: T.trace(t) for t in tags}
    for t in tags:
        print("    trace[%s] = %s dong" % (t, "KHONG CO" if TR[t] is None else len(TR[t])))

    res = {"md5": md5s, "rates": {}, "summary": {}, "levels": {}, "bigmove": {}, "capture": {}}

    print("\n=== (a) 5 RATE CHAT LUONG toan bo leg (theo printDone.csv) ===")
    print("%-10s %6s %8s %8s %10s %10s %10s" % ("tag", "n", "win%", "TSloss%", "mP|SM", "mP|SL", "meanP"))
    for t in tags:
        d = D[t]; lv = L[t]["ALL"]
        print("%-10s %6d %8.2f %8.2f %10.3f %10.3f %10.3f" % (
            t, len(d), lv["win"], lv["tsloss"],
            float(d.loc[d.status == "STOP_MARKET_DONE", "profit"].mean()),
            float(d.loc[d.status == "STOP_LOSS_DONE", "profit"].mean()), lv["meanP"]))

    for t in tags:
        res["summary"][t] = S[t]; res["levels"][t] = L[t]

    print("\n=== (a2) CI cua hieu (F3 - parity), block-72h, CA HAI do rong ===")
    print("%-9s %24s %26s %6s %6s %7s" % ("rate", "CI @1.21 (legacy)", "CI @%.4f (inflate k=1)" % INFLATE_K1,
                                          "outL", "outS", "HUONG"))
    c1 = T.ci_pair(variant, parity, 1.21)
    c2 = T.ci_pair(variant, parity, INFLATE_K1)
    n_good = n_bad = n_out = 0
    det = {}
    for name, dirc in T.RATES:
        obs = c1[name][0]
        lo1, hi1, o1 = c1[name][1], c1[name][2], c1[name][3]
        lo2, hi2, o2 = c2[name][1], c2[name][2], c2[name][3]
        out = o1 and o2
        good = out and ((dirc > 0 and obs > 0) or (dirc < 0 and obs < 0))
        bad = out and not good
        n_good += int(good); n_out += int(o1); n_bad += int(bad)
        det[name] = dict(obs=obs, lo_legacy=lo1, hi_legacy=hi1, lo_std=lo2, hi_std=hi2,
                         out_both=bool(out), good=bool(good), bad=bool(bad),
                         dir="up" if dirc > 0 else "down")
        print("%-9s %10.3f [%8.3f,%8.3f] %10.3f [%8.3f,%8.3f] %6s %6s %7s" % (
            name, obs, lo1, hi1, obs, lo2, hi2, "Y" if o1 else "-", "Y" if o2 else "-",
            "TOT" if good else ("XAU" if bad else "-")))
    res["rates"] = dict(n_good=n_good, n_out_legacy=n_out, n_bad=n_bad, detail=det)
    print("   >>> rate NGOAI CI (ca 2 do rong) CUNG HUONG TOT = %d/5 | XAU ngoai CI = %d/5" % (n_good, n_bad))

    print("\n=== (b) RANG BUOC CUNG (RISK_APPETITE) + theo nam ===")
    print("%-10s %10s %8s %8s %6s %9s %9s %6s" % ("tag", "equity", "CAGR%", "maxDD%", "UW",
                                                  "quy min%", "conc%", "PASS"))
    for t in tags:
        s = S[t]
        ok = (s["maxDD"] >= -T.DD_MAX and s["uw"] <= T.UW_MAX and s["qmin"] >= T.Q_MIN
              and not s["neg_year"] and s["conc"] <= T.CONC_MAX)
        print("%-10s %10.0f %8.2f %8.2f %6d %9.2f %9.2f %6s" % (
            t, s["end"], s["cagr"], s["maxDD"], s["uw"], s["qmin"], s["conc"], "PASS" if ok else "FAIL"))
        res["summary"][t]["hard_pass"] = bool(ok)
    print("\n  theo nam (maxDD% / UW / ret%):")
    yrs = sorted({y for t in tags for y in S[t]["yr"]})
    print("    %-10s %s" % ("tag", " ".join("%22d" % y for y in yrs)))
    for t in tags:
        print("    %-10s %s" % (t, " ".join(
            "%7.2f/%5d/%7.2f" % (S[t]["yr"][y]["dd"], S[t]["yr"][y]["uw"], S[t]["yr"][y]["ret"])
            for y in yrs if y in S[t]["yr"])))

    print("\n=== (c) CAPTURE RATIO: lenh co dinh (maePeak HIGH) >= 20%% / 50%% / 100%% ===")
    print("    (peak = maePeak = dinh HIGH GIA THAT tu leg dau — CUNG mau so cho ca 2 chan)")
    print("    %trailing = thoát bằng trailing (STOP_MARKET_DONE); %SL = cat lo (STOP_LOSS_DONE);")
    print("    med_gap_pp = con cach dinh bao nhieu diem % luc thoat; capture = ratePct/peakPct")
    for lv in PEAK_LEVELS:
        print("\n  -- peak >= +%d%% --" % int(lv * 100))
        print("  %-10s %6s %9s %8s %11s %11s %11s %11s %11s %12s %10s" % (
            "tag", "n", "%trailing", "%SL", "med_cap", "mean_cap", "agg_cap", "med_gap_pp",
            "med_peak%", "SumPnL", "meanP"))
        for t in tags:
            r = T.bigmove(TR[t], lv)
            if r is None or r.get("n", 0) == 0:
                print("  %-10s %6s %9s %8s %11s %11s %11s %11s %11s %12s %10s" % (
                    t, 0, "-", "-", "-", "-", "-", "-", "-", "-", "-"))
                continue
            print("  %-10s %6d %9.1f %8.1f %11.3f %11.3f %11.3f %11.2f %11.2f %12.1f %10.3f" % (
                t, r["n"], r["pct_trailing"], r["pct_sl"], r["med_capture"], r["mean_capture"],
                r["agg_capture"], r["med_gap_pp"], r["med_peakPct"], r["sumPnL"],
                float(TR[t].loc[TR[t].peakPct >= lv * 100.0].pnl.mean())))
            r["meanP"] = float(TR[t].loc[TR[t].peakPct >= lv * 100.0].pnl.mean())
            print("             exit reason: %s" % json.dumps(r["reason"], default=str))
            res["capture"].setdefault(t, {})["%d" % int(lv * 100)] = r
            res["bigmove"].setdefault(t, {})["%d" % int(lv * 100)] = r

    print("\n  (c2) [POST-HOC — chi de doc] CI block-72h cho nhom dinh (d_capture, d_SumPnL)")
    for lv in PEAK_LEVELS:
        r = T.bigmove_ci(variant, parity, lv, INFLATE_K1)
        if r is None:
            continue
        print("  peak>=+%3d%%  n_var=%4d n_base=%4d | d_capture %+.3f [%+.3f,%+.3f]%s | d_SumPnL %+9.1f [%+9.1f,%+9.1f]%s" % (
            int(lv * 100), r["n_var"], r["n_base"],
            r["d_capture"][0], r["d_capture"][1], r["d_capture"][2], " *" if r["d_capture"][3] else "",
            r["d_sumPnL"][0], r["d_sumPnL"][1], r["d_sumPnL"][2], " *" if r["d_sumPnL"][3] else ""))
        res.setdefault("capture_ci", {})["%d" % int(lv * 100)] = r

    print("\n=== (d) PnL / EQUITY (KHONG dung de chon) + theo LEVEL ===")
    print("%-10s %-22s %7s %14s %10s %8s %8s" % ("tag", "level", "n", "SumPnL", "meanP", "win%", "TSloss%"))
    for t in tags:
        for lv in sorted(set(L[t].keys()) - {"ALL"}) + ["ALL"]:
            r = L[t][lv]
            print("%-10s %-22s %7d %14.1f %10.3f %8.2f %8.2f" % (
                t, lv, r["n"], r["sumPnL"], r["meanP"], r["win"], r["tsloss"]))
    for t in tags:
        print("    %-10s equity cuoi %.0f | SumPnL(leg) %.1f | meanP %.3f | CAGR %.2f%% | maxDD %.2f%% | UW %d | conc %.2f%%" % (
            t, S[t]["end"], float(D[t].pnl.sum()), L[t]["ALL"]["meanP"],
            S[t]["cagr"], S[t]["maxDD"], S[t]["uw"], S[t]["conc"]))

    if jout:
        with open(jout, "w") as f:
            json.dump(res, f, indent=1, default=str)
        print("\n[json] %s" % jout)


if __name__ == "__main__":
    main()
