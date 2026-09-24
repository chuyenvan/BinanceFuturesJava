"""GB scorer — cham 4 chan cua docs/PREREG_GIVEBACK_RATIO.md (TS_GIVEBACK_RATIO 0.5/1/2/5).

Nen = PRODUCTION FLATGRID KEEPLEG0. Doi tuong so CI = moc `kg0-g170` (TS_GIVEBACK_RATIO=0.5).
  [0] CONG PARITY moc (md5 99e42b75 / n 1,085 / eq 103,083) + "chi 1 key doi"
  [1] BANG 4 CHAN: n / win% / TSloss% / mP|SM / mP|SL / meanP / hold / equity + maxDD/UW MTM PHUT
  [2] *** SO LEG THUC SU KHAC NHAU *** giua cac chan (kiem du doan "1/2/5 gan nhu trung nhau")
  [3] BANG PnL THEO NAM + TOTAL PnL cho ca 4 chan
  [4] 5 rate + CI block-72h 2000 rep seed 20260905 vs MOC, CA HAI do rong
      (x1.21 legacy + inflate(k=3)=1.482304)
  [5] RAO CUNG RISK_APPETITE §7 (40/250/-20/khong nam am/conc 15) — maxDD/UW = MTM MOC PHUT
  [6] KET LUAN theo luat pre-reg §6

Usage: python3 research/analysis/gb_score.py [--json OUT.json]
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import kg0_score as K      # noqa: E402
import gd92xexit_score as G  # noqa: E402

KOUT = K.KOUT
BASE = "kg0-g170"                       # moc = TS_GIVEBACK_RATIO 0.5
ARMS = ["kg0-g170", "gb-r1", "gb-r2", "gb-r5"]
LAB = {"kg0-g170": "0.5 (moc)", "gb-r1": "1", "gb-r2": "2", "gb-r5": "5"}
KVAR = 3                                # 3 ung vien moi => inflate(3)=1.482304
KEEP_MD5 = "99e42b75cf1a2142f9cd14dc72e371ba"
KEEP_N, KEEP_EQ = 1085, 103083
INTRADAY_JSON = "/home/ubuntu/gbr/intraday/intraday_dd.json"
ID_MAP = {"kg0-g170": "base", "gb-r1": "r1", "gb-r2": "r2", "gb-r5": "r5"}


def legs_key(tag):
    """Multiset khoa leg day du (sym,start,end,status,pnl) tu printDone.csv."""
    import pandas as pd
    p = os.path.join(KOUT, tag, "storage", "printDone.csv")
    d = pd.read_csv(p, on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    ks = []
    for _, r in d.iterrows():
        ks.append((str(r["sym"]).strip(), str(r["start"]).strip(), str(r["end"]).strip(),
                   str(r["status"]).strip(), "%.6f" % float(r["pnl"])))
    return collections.Counter(ks), d


def leg_diff(ta, tb):
    ca, da = legs_key(ta)
    cb, db = legs_key(tb)
    only_a, only_b = ca - cb, cb - ca
    na, nb = sum(only_a.values()), sum(only_b.values())
    # khop (sym,start) nhung khac (end|status|pnl)
    ja = {}
    for _, r in da.iterrows():
        ja[(str(r["sym"]).strip(), str(r["start"]).strip())] = (
            str(r["end"]).strip(), str(r["status"]).strip(), "%.6f" % float(r["pnl"]))
    same_key_diff = 0
    for _, r in db.iterrows():
        k = (str(r["sym"]).strip(), str(r["start"]).strip())
        if k in ja and ja[k] != (str(r["end"]).strip(), str(r["status"]).strip(),
                                 "%.6f" % float(r["pnl"])):
            same_key_diff += 1
    return dict(na=na, nb=nb, sym_diff=na + nb, same_start_diff=same_key_diff,
                n_a=sum(ca.values()), n_b=sum(cb.values()))


def main():
    jout = None
    if "--json" in sys.argv:
        jout = sys.argv[sys.argv.index("--json") + 1]
    W = K.C.inflate(KVAR)
    have = [t for t in ARMS if os.path.exists(os.path.join(KOUT, t, "storage", "printDone.csv"))]
    print("=== TS_GIVEBACK_RATIO 0.5 / 1 / 2 / 5 (nen KEEPLEG0) — %d/4 chan | block-72h 2000 rep "
          "seed 20260905 | x1.21 legacy / inflate(3)=%.6f ===" % (len(have), W))
    print("    rao MOI 40/250/-20/khong nam am/conc 15 — maxDD+UW do tren MTM MOC PHUT")

    # [0] parity
    print("\n[0] CONG PARITY (moc)")
    mb = K.md5(BASE)
    S = {t: G.summary(t) for t in have}
    ok = (mb == KEEP_MD5) and S[BASE]["n"] == KEEP_N and abs(S[BASE]["end"] - KEEP_EQ) < 0.5
    print("    %s n=%d (want %d) eq=%.0f (want %d) md5=%s => %s" % (
        BASE, S[BASE]["n"], KEEP_N, S[BASE]["end"], KEEP_EQ, (mb or "-")[:16],
        "PASS" if ok else "FAIL"))
    if not ok:
        print("*** PARITY FAIL => DUNG, khong doc tiep. ***")
        return 3
    print("\n[0b] 'CHI 1 KEY DOI' (prof_run.properties moi chan vs moc)")
    pbase = kg0_proftxt(BASE)
    for t in have:
        if t == BASE:
            continue
        p = kg0_proftxt(t)
        keys = sorted(set(pbase) | set(p))
        diffs = {k: (pbase.get(k), p.get(k)) for k in keys if pbase.get(k) != p.get(k)}
        extra = {k: v for k, v in diffs.items() if k != "TS_GIVEBACK_RATIO"}
        print("    %-8s %d key khac | ngoai TS_GIVEBACK_RATIO: %d %s" % (
            LAB[t], len(diffs), len(extra), extra if extra else ""))
        for k, (x, y) in sorted(diffs.items()):
            print("        %-24s %s -> %s" % (k, x, y))

    # [1] bang 4 chan
    R = {t: K.rates_row(t) for t in have}
    F = {t: K.funding_term(t) for t in have}
    idj = json.load(open(INTRADAY_JSON)) if os.path.exists(INTRADAY_JSON) else None
    print("\n[1] *** BANG 4 CHAN ***")
    print("%-9s %6s %8s %8s %9s %9s %9s %8s %11s %11s %9s %9s" % (
        "ratio", "n", "win%", "TSloss%", "mP|SM", "mP|SL", "meanP", "hold_h", "equity",
        "maxDD_phut", "UW_phut", "fund/PnL%"))
    Mx = {}
    for t in have:
        r, s = R[t], S[t]
        o = idj["out"][ID_MAP[t]] if idj else None
        Mx[t] = dict(dd_min=(o or {}).get("dd_min"), uw_min=(o or {}).get("uw_min_days"),
                     dd_daily=(o or {}).get("dd_daily"), uw_daily=(o or {}).get("uw_daily"),
                     py_min=(o or {}).get("py_min"))
        print("%-9s %6d %8.2f %8.2f %9.3f %9.3f %9.3f %8.1f %11.0f %11s %9s %9.2f%%" % (
            LAB[t], r["n"], r["win"], r["tsloss"], r["mp_sm"], r["mp_sl"], r["meanP"],
            s["hold_med"], s["end"],
            ("%.2f" % Mx[t]["dd_min"]) if Mx[t]["dd_min"] is not None else "-",
            ("%.1f" % Mx[t]["uw_min"]) if Mx[t]["uw_min"] is not None else "-",
            F[t]["funding_over_pnl"]))
    if idj is None:
        print("    [!] thieu %s => chua co maxDD/UW PHUT" % INTRADAY_JSON)

    # [2] so leg khac nhau
    print("\n[2] *** SO LEG THUC SU KHAC NHAU *** (khoa (sym,start,end,status,pnl))")
    print("%-22s %8s %8s %9s %9s" % ("cap", "n_A", "n_B", "leg khac", "cung start khac end/status/pnl"))
    res_diff = {}
    pairs = [(BASE, "gb-r1"), (BASE, "gb-r2"), (BASE, "gb-r5"),
             ("gb-r1", "gb-r2"), ("gb-r1", "gb-r5"), ("gb-r2", "gb-r5")]
    for a, b in pairs:
        if a not in have or b not in have:
            continue
        dd = leg_diff(a, b)
        res_diff["%s|%s" % (a, b)] = dd
        print("%-22s %8d %8d %9d %9d" % ("%s vs %s" % (LAB[a], LAB[b]), dd["n_a"], dd["n_b"],
                                         dd["sym_diff"], dd["same_start_diff"]))

    # [3] PnL theo nam
    Y = {t: G.yearly_detail(t) for t in have}
    print("\n[3] *** BANG PnL THEO NAM + TOTAL PnL *** (PnL = realized `pnl` USDT)")
    yrs = [2021, 2022, 2023, 2024, 2025]
    print("%-9s %s %12s %12s" % ("ratio",
                                    " ".join("%13s" % ("%d n/PnL" % y) for y in yrs),
                                    "TONG n", "TOTAL PnL"))
    for t in have:
        cells = []
        for y in yrs:
            r = Y[t].get(y)
            cells.append("%13s" % ("%d / %.0f" % (r["n"], r["pnl_usdt"]) if r else "-"))
        tot_n = sum(Y[t][y]["n"] for y in Y[t])
        tot_p = sum(Y[t][y]["pnl_usdt"] for y in Y[t])
        print("%-9s %s %12d %12.0f" % (LAB[t], " ".join(cells), tot_n, tot_p))

    # [4] CI
    print("\n[4] 5 RATE + CI vs MOC (%s=0.5) — quyet dinh = ngoai CA HAI do rong" % LAB[BASE])
    res = {"parity_md5": mb, "inflate_k": W, "summary": S, "mech": R, "funding": F,
           "legdiff": res_diff, "yearly": {t: {str(k): v for k, v in Y[t].items()} for t in have},
           "ci": {}}
    for t in have:
        if t == BASE:
            continue
        res["ci"][t] = K.ci_block(t, BASE, KVAR)

    if idj is None:
        print("\n*** THIEU MTM MOC PHUT => chua cham duoc rao cung. DUNG. ***")
        if jout:
            with open(jout, "w") as f:
                json.dump(res, f, indent=1, default=str)
        return 4

    # [5] rao cung
    print("\n[5] RAO CUNG §7 — maxDD/UW = MTM MOC PHUT (ngay chi de doi chieu)")
    print("%-9s %13s %11s %13s %11s" % ("ratio", "maxDD NGAY", "UW NGAY", "maxDD PHUT", "UW PHUT"))
    Sx, Yx = {}, {}
    for t in have:
        o = idj["out"][ID_MAP[t]]
        Sx[t] = dict(S[t])
        Sx[t]["maxDD"] = o["dd_min"]
        Sx[t]["uw"] = int(round(o["uw_min_days"]))
        Yx[t] = {}
        for y, yy in Y[t].items():
            z = dict(yy)
            z["maxDD"] = o["py_min"][str(y)][0]
            z["uw"] = int(round(o["py_min"][str(y)][1] / 1440.0))
            Yx[t][y] = z
        print("%-9s %13.2f %11d %13.2f %11.1f" % (
            LAB[t], o["dd_daily"], o["uw_daily"], o["dd_min"], o["uw_min_days"]))
    print("\n    theo nam (maxDD% / UW / ret% / qmin%; P/F theo rao MOI, maxDD+UW = phut):")
    print("    %-9s %s" % ("ratio", " ".join("%-25d" % y for y in yrs)))
    for t in have:
        cells = []
        for y in yrs:
            r = Yx[t].get(y)
            if not r:
                cells.append("%-25s" % "-"); continue
            okk = (r["maxDD"] >= -K.DD_NEW and r["uw"] <= K.UW_NEW and r["qmin"] >= K.Q_NEW
                   and r["ret"] >= 0)
            cells.append("%6.2f/%4d/%+6.2f/%+6.2f %s" % (
                r["maxDD"], r["uw"], r["ret"], r["qmin"], "P" if okk else "F"))
        print("    %-9s %s" % (LAB[t], " ".join(cells)))
    gates = {}
    for lab, key in (("MOI 40/250/-20/nam>=0/conc15", "new"), ("CU 30/200/-15", "old")):
        print("\n    RAO %s:" % lab)
        for t in have:
            dd, uw, q = ((K.DD_NEW, K.UW_NEW, K.Q_NEW) if key == "new"
                         else (K.DD_OLD, K.UW_OLD, K.Q_OLD))
            g = K.fence(Sx[t], Yx[t], dd, uw, q)
            gates.setdefault(t, {})[key] = g
            print("    %-9s %s" % (LAB[t], "PASS" if g[0] else "FAIL (" + ", ".join(g[1]) + ")"))
    res["gates"] = {t: {"new_ok": gates[t]["new"][0], "new_bad": gates[t]["new"][1],
                        "old_ok": gates[t]["old"][0], "old_bad": gates[t]["old"][1]} for t in have}
    res["minute"] = {t: dict(dd_min=idj["out"][ID_MAP[t]]["dd_min"],
                             dd_daily=idj["out"][ID_MAP[t]]["dd_daily"],
                             uw_min=idj["out"][ID_MAP[t]]["uw_min_days"],
                             uw_daily=idj["out"][ID_MAP[t]]["uw_daily"],
                             py_min=idj["out"][ID_MAP[t]]["py_min"]) for t in have}

    # [6] ket luan
    print("\n[6] KET LUAN theo luat pre-reg §6")
    verdict = {}
    for t in have:
        if t == BASE:
            continue
        ci = res["ci"][t]
        rn = gates[t]["new"][0]
        go = ci["e_pass"] and rn and ci["bad"] == 0
        verdict[t] = dict(good=ci["good"], bad=ci["bad"], rails=rn, go=go)
        print("    ratio %-3s TOT=%d/5 XAU=%d/5 | rao MOI %s | E-PASS %s | => %s" % (
            LAB[t], ci["good"], ci["bad"], "PASS" if rn else "FAIL",
            "PASS" if ci["e_pass"] else "FAIL", "GO" if go else "NULL"))
    res["verdict"] = verdict
    if jout:
        with open(jout, "w") as f:
            json.dump(res, f, indent=1, default=str)
        print("\n[json] %s" % jout)
    return 0


def kg0_proftxt(tag):
    p = os.path.join(KOUT, tag, "prof_run.properties")
    if not os.path.exists(p):
        return {}
    d = {}
    with open(p, errors="ignore") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, v = ln.split("=", 1)
            d[k.strip()] = v.strip()
    return d


if __name__ == "__main__":
    sys.exit(main())
