"""SL3 scorer — cham 5 chan cua docs/prereg/PREREG_SL_7_TO_3.md.

Nen = PRODUCTION FLATGRID KEEPLEG0. Doi tuong so CI = moc `sl3-base`.
  [0] CONG PARITY: base md5 99e42b75 / n 1,085 / eq 103,083 (+ so dong PREARM_SL tung chan)
  [1] CO CHE: n / win% / TSloss% / mP|SM / mP|SL / meanP / hold / turnover / SumFunding
  [2] 5 RATE + CI block-72h 2000 rep seed 20260905 vs moc, CA HAI do rong (x1.21 legacy +
      inflate(k=4)=1.665109)
  [3] RAO CUNG §7 (40/250/-20/khong nam am/conc 15) — maxDD/UW lay tu MTM MOC PHUT
      (research/analysis/sl3_intraday.py) cho CA theo nam LAN toan ky; quy/conc/ret theo daily
  [4] BANG PnL CHI TIET THEO NAM cho moi chan
  [5] KET LUAN theo luat pre-reg §4 (GO / NULL)

Usage: python3 research/analysis/sl3_score.py [--json OUT.json]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import kg0_score as K   # noqa: E402  (dung lai helper da nghiem thu)
import gd92xexit_score as G  # noqa: E402

KOUT = K.KOUT
BASE = "sl3-base"
ARMS = ["sl3-base", "sl3-v1-arm03", "sl3-v2-sl3", "sl3-v3-both", "sl3-v4-sl7"]
LAB = {"sl3-base": "moc/parity", "sl3-v1-arm03": "V1 arm3", "sl3-v2-sl3": "V2 SL-3",
       "sl3-v3-both": "V3 both", "sl3-v4-sl7": "V4 SL-7"}
KVAR = 4                       # 4 ung vien V1..V4 => inflate(4)=1.665109
KEEP_MD5 = "99e42b75cf1a2142f9cd14dc72e371ba"
KEEP_N, KEEP_EQ = 1085, 103083
INTRADAY_JSON = "/home/ubuntu/sl3/intraday/intraday_dd.json"


def prearm_count(tag):
    p = K._sout(tag)
    if not os.path.exists(p):
        return None
    n = 0
    with open(p, errors="ignore") as f:
        for ln in f:
            if "PREARM_SL sym=" in ln:
                n += 1
    return n


def main():
    jout = None
    if "--json" in sys.argv:
        jout = sys.argv[sys.argv.index("--json") + 1]
    W = K.C.inflate(KVAR)
    have = [t for t in ARMS if os.path.exists(os.path.join(KOUT, t, "storage", "printDone.csv"))]
    print("=== SL3 (nen KEEPLEG0) — %d/5 chan | block-72h 2000 rep seed 20260905 | "
          "x1.21 legacy / inflate(4)=%.6f ===" % (len(have), W))
    print("    rao MOI 40/250/-20/khong nam am/conc 15 — maxDD+UW do tren MTM MOC PHUT")

    # [0] parity
    print("\n[0] CONG PARITY")
    mb = K.md5(BASE)
    S = {t: G.summary(t) for t in have}
    ok = (mb == KEEP_MD5) and S[BASE]["n"] == KEEP_N and abs(S[BASE]["end"] - KEEP_EQ) < 0.5
    print("    base n=%d (want %d) eq=%.0f (want %d) md5=%s => %s" % (
        S[BASE]["n"], KEEP_N, S[BASE]["end"], KEEP_EQ, (mb or "-")[:16],
        "PASS" if ok else "FAIL"))
    if not ok:
        print("*** PARITY FAIL => DUNG, khong doc tiep. ***")
        return 3
    print("    PREARM_SL lines: " + " ".join("%s=%s" % (LAB[t], prearm_count(t)) for t in have))

    # [1] co che
    print("\n[1] CO CHE + chat luong lenh")
    print("%-10s %6s %8s %8s %9s %9s %9s %8s %8s %11s" % (
        "chan", "n", "win%", "TSloss%", "mP|SM", "mP|SL", "meanP", "hold_h", "turn", "fund/PnL%"))
    R = {}
    for t in have:
        r = K.rates_row(t); s = S[t]; f = K.funding_term(t)
        R[t] = r
        print("%-10s %6d %8.2f %8.2f %9.3f %9.3f %9.3f %8.1f %8.3f %10.2f%%" % (
            LAB[t], r["n"], r["win"], r["tsloss"], r["mp_sm"], r["mp_sl"], r["meanP"],
            s["hold_med"], s["turn"], f["funding_over_pnl"]))

    # [4] PnL theo nam (truoc CI cho de doc)
    Y = {t: G.yearly_detail(t) for t in have}
    print("\n[4] BANG PnL CHI TIET THEO NAM (maxDD/UW: NGAY; MTM PHUT o [3])")
    print("%-10s %-5s %6s %9s %11s %9s %8s %6s %9s %11s" % (
        "chan", "nam", "n", "PnL(USDT)", "ret%", "maxDD%", "UW", "qmin%", "TSloss%", "equity"))
    for t in have:
        for y in sorted(Y[t]):
            r = Y[t][y]
            print("%-10s %-5d %6d %9.0f %+9.2f %9.2f %8d %6.2f %9.2f %11.0f" % (
                LAB[t], y, r["n"], r["pnl_usdt"], r["ret"], r["maxDD"], r["uw"], r["qmin"],
                r["tsloss"], r["eq_end"]))

    # [2] CI
    print("\n[2] 5 RATE + CI vs MOC (%s) — quyet dinh = ngoai CA HAI do rong" % BASE)
    res = {"parity_md5": mb, "inflate_k": W, "summary": S, "yearly": {}, "ci": {}, "mech": {},
           "prearm": {t: prearm_count(t) for t in have}}
    for t in have:
        res["yearly"][t] = {str(k): v for k, v in Y[t].items()}
        res["mech"][t] = dict(R[t], hold_med=S[t]["hold_med"], turn=S[t]["turn"],
                              fund=K.funding_term(t))
        if t == BASE:
            continue
        res["ci"][t] = K.ci_block(t, BASE, KVAR)

    # [3] rao cung — maxDD/UW tu MTM PHUT
    print("\n[3] RAO CUNG §7 — maxDD/UW = MTM MOC PHUT (ngay chi de doi chieu)")
    idj = json.load(open(INTRADAY_JSON)) if os.path.exists(INTRADAY_JSON) else None
    if idj is None:
        print("    [!] thieu %s => chua cham duoc rao cung maxDD/UW" % INTRADAY_JSON)
        return 4
    mp = idj["out"]
    mmap = {"base": "base", "v1": "v1", "v2": "v2", "v3": "v3", "v4": "v4"}
    key_of = {"sl3-base": "base", "sl3-v1-arm03": "v1", "sl3-v2-sl3": "v2",
              "sl3-v3-both": "v3", "sl3-v4-sl7": "v4"}
    Sx, Yx = {}, {}
    print("%-10s %13s %11s %13s %11s" % ("chan", "maxDD NGAY", "UW NGAY", "maxDD PHUT", "UW PHUT"))
    for t in have:
        k = key_of[t]; o = mp[k]
        Sx[t] = dict(S[t]); Sx[t]["maxDD"] = o["dd_min"]; Sx[t]["uw"] = int(round(o["uw_min_days"]))
        Yx[t] = {}
        for y, yy in Y[t].items():
            z = dict(yy)
            z["maxDD"] = o["py_min"][str(y)][0]
            z["uw"] = int(round(o["py_min"][str(y)][1] / 1440.0))
            Yx[t][y] = z
        print("%-10s %13.2f %11d %13.2f %11.1f" % (
            LAB[t], o["dd_daily"], o["uw_daily"], o["dd_min"], o["uw_min_days"]))
    gates = {}
    print("\n    theo nam (maxDD% / UW / ret% / qmin%; P/F theo rao MOI, maxDD+UW = phut):")
    yrs = sorted({y for t in have for y in Yx[t]})
    print("    %-10s %s" % ("chan", " ".join("%-26d" % y for y in yrs)))
    for t in have:
        cells = []
        for y in yrs:
            r = Yx[t].get(y)
            if not r:
                cells.append("%-26s" % "-"); continue
            okk = (r["maxDD"] >= -K.DD_NEW and r["uw"] <= K.UW_NEW and r["qmin"] >= K.Q_NEW
                   and r["ret"] >= 0)
            cells.append("%7.2f/%4d/%+7.2f/%+6.2f %s" % (
                r["maxDD"], r["uw"], r["ret"], r["qmin"], "P" if okk else "F"))
        print("    %-10s %s" % (LAB[t], " ".join(cells)))
    for t in have:
        gates[t] = {"new": K.fence(Sx[t], Yx[t], K.DD_NEW, K.UW_NEW, K.Q_NEW),
                    "old": K.fence(Sx[t], Yx[t], K.DD_OLD, K.UW_OLD, K.Q_OLD)}
    print("")
    for lab, key in (("MOI 40/250/-20/nam>=0/conc15", "new"), ("CU 30/200/-15", "old")):
        print("    RAO %s:" % lab)
        for t in have:
            okk, bad, yb = gates[t][key]
            print("    %-10s %s" % (LAB[t], "PASS" if okk else "FAIL (" + ", ".join(bad) + ")"))
    res["gates"] = {t: {"new_ok": gates[t]["new"][0], "new_bad": gates[t]["new"][1],
                        "old_ok": gates[t]["old"][0], "old_bad": gates[t]["old"][1]}
                    for t in have}
    res["minute"] = {t: dict(dd_min=mp[key_of[t]]["dd_min"], dd_daily=mp[key_of[t]]["dd_daily"],
                             uw_min=mp[key_of[t]]["uw_min_days"],
                             uw_daily=mp[key_of[t]]["uw_daily"],
                             dd_low=mp[key_of[t]]["dd_low"], uw_low=mp[key_of[t]]["uw_low_days"],
                             py_min=mp[key_of[t]]["py_min"], py_daily=mp[key_of[t]]["py_daily"])
                     for t in have}

    # [5] ket luan
    print("\n[5] KET LUAN theo luat pre-reg §4")
    verdict = {}
    for t in have:
        if t == BASE:
            continue
        ci = res["ci"][t]
        rn = gates[t]["new"][0]
        go = ci["e_pass"] and rn and ci["bad"] == 0
        verdict[t] = dict(good=ci["good"], bad=ci["bad"], rails=rn, go=go)
        print("    %-10s TOT=%d/5 XAU=%d/5 | rao MOI %s | E-PASS %s | => %s" % (
            LAB[t], ci["good"], ci["bad"], "PASS" if rn else "FAIL",
            "PASS" if ci["e_pass"] else "FAIL", "GO" if go else "NULL"))
    res["verdict"] = verdict
    if jout:
        with open(jout, "w") as f:
            json.dump(res, f, indent=1, default=str)
        print("\n[json] %s" % jout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
