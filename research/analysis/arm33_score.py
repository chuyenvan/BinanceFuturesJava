"""ARM3-3NEN scorer — cham 6 chan cua docs/prereg/PREREG_ARM3_3NEN.md.

  3 nEN x 2 MUC arm: A=KEEPLEG0, B=T100, C=GD92; MOC=0.07, ARM3=0.03.
  CHI doi SIM_RATE_PROFIT_STOP_MARKET (khong SIM_PRE_ARM_SL, khong key khac).

  [0] CONG PARITY 3 MOC (md5 + n + equity + [GATE-ROLL] cho C)
  [1] KIEM "chi 1 key doi": diff prof_run.properties giua (Xi, X2) tru SIM_RATE_PROFIT_STOP_MARKET
  [2] CO CHE: n / win% / TSloss% / mP|SM / mP|SL / meanP / hold / turnover / Sum funding
  [3] *** BANG 6 CHAN *** n + PnL theo nam 2021..2025 + TONG n + TOTAL PnL + equity cuoi
  [4] 5 rate + CI block-72h 2000 rep seed 20260905 vs MOC CUA CHINH NEN (A2-A1, B2-B1, C2-C1),
      CA HAI do rong (legacy x1.21 + inflate(k=3)=1.482304)
  [5] RAO CUNG RISK_APPETITE §7 (maxDD<=40%, quy>=-20%, UW<=250, conc<=15%, ko nam am)
      theo nam LAN toan ky; maxDD/UW = MTM MOC PHUT (json tu arm33_intraday.py)
  [6] KET LUAN theo luat pre-reg §6

Usage: python3 research/analysis/arm33_score.py [--minute JSON] [--k 3] [--json OUT.json]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import kg0_score as K    # noqa: E402
import gd92xexit_score as G  # noqa: E402
import c3_rates as C     # noqa: E402

KOUT = K.KOUT
MINUTE_DEFAULT = "/home/ubuntu/arm33/intraday/intraday_dd.json"

# (tag, nEN, muc ARM, nhan)
CH = [
    ("kg0-g170",     "KEEPLEG0", "0.07", "A1 KEEPLEG0 moc"),
    ("sl3-v1-arm03", "KEEPLEG0", "0.03", "A2 KEEPLEG0 arm3"),
    ("hn-t100",      "T100",     "0.07", "B1 T100 moc"),
    ("hn-t100-arm3", "T100",     "0.03", "B2 T100 arm3"),
    ("hn-g92",       "GD92",     "0.07", "C1 GD92 moc"),
    ("hn-g92-arm3",  "GD92",     "0.03", "C2 GD92 arm3"),
]
PAIRS = [("A", "kg0-g170", "sl3-v1-arm03"), ("B", "hn-t100", "hn-t100-arm3"),
         ("C", "hn-g92", "hn-g92-arm3")]
MD5_WANT = {"kg0-g170": "99e42b75cf1a2142f9cd14dc72e371ba",
            "hn-t100": "dc16e4da6ff6cb7b8d41c592bc3d9c45",
            "hn-g92": "cd913759ecd4bf50adab2b818eaf9525"}
NEQ_WANT = {"kg0-g170": (1085, 103083), "hn-t100": (2559, 121770), "hn-g92": (2632, 133944)}
YEARS = [2021, 2022, 2023, 2024, 2025]


def proftxt(tag):
    p = os.path.join(KOUT, tag, "prof_run.properties")
    if not os.path.exists(p):
        return None
    d = {}
    with open(p, errors="ignore") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, v = ln.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def main():
    jout, k, mj = None, 3, MINUTE_DEFAULT
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--json":
            jout = sys.argv[i + 1]; i += 2; continue
        if sys.argv[i] == "--k":
            k = int(sys.argv[i + 1]); i += 2; continue
        if sys.argv[i] == "--minute":
            mj = sys.argv[i + 1]; i += 2; continue
        i += 1
    W = C.inflate(k)

    print("=== ARM 7%% -> 3%% TREN 3 NEN (6 CHAN) — block-%dh %d rep seed %d | legacy %.2f / "
          "inflate(%d)=%.6f ===" % (K.BLOCK_H, K.NREP, K.SEED, K.LEGACY, k, W))
    print("    nEN: KEEPLEG0 (A) · T100 (B) · GD92 (C) | MOC 7%% vs ARM3 3%% | CHI doi "
          "SIM_RATE_PROFIT_STOP_MARKET")
    have = [t for t, _, _, _ in CH if os.path.exists(os.path.join(KOUT, t, "storage", "printDone.csv"))]
    miss = [t for t, _, _, _ in CH if t not in have]

    # ---- [0] parity ----
    print("\n[0] CONG PARITY 3 MOC")
    pok = True
    for tag in ("kg0-g170", "hn-t100", "hn-g92"):
        if tag not in have:
            print("    %-14s THIEU run => FAIL" % tag); pok = False; continue
        m = K.md5(tag); n, eq = NEQ_WANT[tag]
        s = G.summary(tag)
        ok = (m == MD5_WANT[tag]) and s["n"] == n and abs(s["end"] - eq) < 0.5
        print("    %-14s md5=%s n=%d(want %d) eq=%.0f(want %d) => %s" % (
            tag, (m or "-")[:16], s["n"], n, s["end"], eq, "PASS" if ok else "FAIL"))
        pok = pok and ok
    # [GATE-ROLL] BAT cho C
    sout = K._sout("hn-g92")
    gate = 0
    with open(sout, errors="ignore") as fh:
        for ln in fh:
            if "[GATE-ROLL] BAT" in ln:
                gate += 1
    print("    hn-g92 [GATE-ROLL] BAT = %d dong => %s" % (gate, "OK" if gate else "*** FAIL ***"))
    pok = pok and gate > 0
    if miss:
        print("    [!] THIEU chan: %s" % ", ".join(miss))
    if not pok or miss:
        print("*** PARITY/THIEU => DUNG, bao RO. ***")
        return 3

    # ---- [1] chi 1 key doi ----
    print("\n[1] KIEM 'CHI 1 KEY DOI' (prof_run.properties giua moc va arm3)")
    keydiff = {}
    for lab, off, on in PAIRS:
        a, b = proftxt(off), proftxt(on)
        if a is None or b is None:
            print("    %s: THIEU prof_run" % lab); continue
        keys = sorted(set(a) | set(b))
        diffs = {kk: (a.get(kk), b.get(kk)) for kk in keys if a.get(kk) != b.get(kk)}
        # tag/note rieng biet duoc phep
        extra = {kk: v for kk, v in diffs.items()
                 if kk not in ("SIM_RATE_PROFIT_STOP_MARKET",)}
        keydiff[lab] = diffs
        print("    %s  %s -> %s : %d key khac | ngoai ARM: %d %s" % (
            lab, off, on, len(diffs), len(extra), extra if extra else ""))
        for kk, (x, y) in sorted(diffs.items()):
            print("        %-32s %s -> %s" % (kk, x, y))
    if any(len({kk for kk in d if kk != "SIM_RATE_PROFIT_STOP_MARKET"}) for d in keydiff.values()):
        print("    *** CANH BAO: co key khac ngoai SIM_RATE_PROFIT_STOP_MARKET => ghi RO ***")

    # ---- data ----
    S = {t: G.summary(t) for t in have}
    Y = {t: G.yearly_detail(t) for t in have}
    R = {t: K.rates_row(t) for t in have}
    F = {t: K.funding_term(t) for t in have}
    res = {"k": k, "inflate": W, "legacy": K.LEGACY, "md5": {t: K.md5(t) for t in have},
           "keydiff": {a: {kk: list(v) for kk, v in d.items()} for a, d in keydiff.items()},
           "summary": S, "yearly": {t: {str(y): v for y, v in Y[t].items()} for t in have},
           "mech": R, "funding": F, "ci": {}}

    # ---- [2] co che ----
    print("\n[2] CO CHE + chat luong lenh (toan bo leg)")
    print("%-14s %-9s %5s %6s %8s %8s %9s %9s %9s %8s %8s %11s" % (
        "tag", "nEN", "arm", "n", "win%", "TSloss%", "mP|SM", "mP|SL", "meanP", "hold_h",
        "turn", "fund/PnL%"))
    for t, nen, arm, _ in CH:
        if t not in have:
            continue
        r, s, f = R[t], S[t], F[t]
        print("%-14s %-9s %5s %6d %8.2f %8.2f %9.3f %9.3f %9.3f %8.1f %8.3f %10.2f%%" % (
            t, nen, arm, r["n"], r["win"], r["tsloss"], r["mp_sm"], r["mp_sl"], r["meanP"],
            s["hold_med"], s["turn"], f["funding_over_pnl"]))

    # ---- [3] BANG 6 CHAN ----
    print("\n" + "=" * 120)
    print("*** BANG 6 CHAN — n VA PnL THEO NAM (USDT) ***")
    print("=" * 120)
    hdr = "%-9s %-5s |" % ("nEN", "arm") + "".join(
        " %8d n |%13s |" % (y, "PnL") for y in YEARS) + " %7s |%12s |%11s" % (
        "TONG n", "TOTAL PnL", "equity cuoi")
    print(hdr)
    tbl = {}
    for t, nen, arm, _ in CH:
        if t not in have:
            continue
        row = ""
        tn = 0; tp = 0.0
        cells = {}
        for y in YEARS:
            r = Y[t].get(y)
            if not r:
                row += " %8s n |%13s |" % ("-", "-"); cells[y] = None; continue
            row += " %8d n |%13.0f |" % (r["n"], r["pnl_usdt"])
            tn += r["n"]; tp += r["pnl_usdt"]
            cells[y] = r
        print("%-9s %-5s |%s %7d |%12.0f |%11.0f" % (nen, arm, row, tn, tp, S[t]["end"]))
        tbl["%s_%s" % (nen, arm)] = dict(total_n=tn, total_pnl=tp, eq=S[t]["end"],
                                         years={str(y): (r["n"], r["pnl_usdt"]) if r else None
                                                for y, r in cells.items()})
    res["table"] = tbl

    print("\n--- cot phu bat buoc (moc vs arm3 moi nEN) ---")
    print("%-14s %-9s %5s %6s %8s %8s %9s %8s %10s %11s" % (
        "tag", "nEN", "arm", "n", "win%", "TSloss%", "meanP", "hold_h", "maxDD(ngay)%", "equity"))
    for t, nen, arm, _ in CH:
        if t not in have:
            continue
        print("%-14s %-9s %5s %6d %8.2f %8.2f %9.3f %8.1f %12.2f %11.0f" % (
            t, nen, arm, R[t]["n"], R[t]["win"], R[t]["tsloss"], R[t]["meanP"],
            S[t]["hold_med"], S[t]["maxDD"], S[t]["end"]))

    # ---- [4] CI vs moc cua chinh nen ----
    print("\n[4] 5 RATE + CI vs MOC CUA CHINH NEN (ngoai CA HAI do rong)")
    ci_sum = {}
    for lab, off, on in PAIRS:
        if off not in have or on not in have:
            continue
        print("\n[nEN %s] %s  (-  %s)" % (lab, on, off))
        rr = K.ci_block(on, off, k)
        ci_sum[lab] = dict(off=off, on=on, good=rr["good"], bad=rr["bad"], e_pass=rr["e_pass"])
        res["ci"]["%s_%s_vs_%s" % (lab, on, off)] = rr["detail"]
    print("\n  TOM TAT: " + " | ".join(
        "%s: TOT=%d/5 XAU=%d/5 E-PASS=%s" % (lab, v["good"], v["bad"], v["e_pass"])
        for lab, v in ci_sum.items()))
    res["ci_summary"] = ci_sum

    # ---- [5] rao cung (MTM PHUT) ----
    print("\n[5] RAO CUNG RISK_APPETITE §7 (maxDD<=%.0f%%/nam, quy>=%.0f%%, UW<=%d, conc<=%.0f%%, "
          "ko nam am) — maxDD/UW = MTM MOC PHUT" % (
              K.DD_NEW, K.Q_NEW, K.UW_NEW, K.CONC_MAX))
    idj = json.load(open(mj)) if os.path.exists(mj) else None
    if idj is None:
        print("    [!] thieu %s => chua cham duoc rao maxDD/UW" % mj); 
    else:
        mp = idj["out"]
        Sx, Yx = {}, {}
        print("%-14s %12s %10s %12s %10s" % ("tag", "maxDD NGAY", "UW NGAY", "maxDD PHUT", "UW PHUT"))
        for t in have:
            o = mp.get(t)
            if o is None:
                print("%-14s THIEU trong minute json" % t); continue
            Sx[t] = dict(S[t]); Sx[t]["maxDD"] = o["dd_min"]; Sx[t]["uw"] = int(round(o["uw_min_days"]))
            Yx[t] = {}
            for y, yy in Y[t].items():
                z = dict(yy)
                z["maxDD"] = o["py_min"][str(y)][0]
                z["uw"] = int(round(o["py_min"][str(y)][1] / 1440.0))
                Yx[t][y] = z
            print("%-14s %12.2f %10d %12.2f %10.1f" % (
                t, o["dd_daily"], o["uw_daily"], o["dd_min"], o["uw_min_days"]))
        print("\n  THEO NAM (maxDD% / UW / ret% / qmin%; P/F theo rao §7):")
        print("  %-14s %s" % ("tag", " ".join("%-26d" % y for y in YEARS)))
        for t in have:
            if t not in Yx:
                continue
            cells = []
            for y in YEARS:
                r = Yx[t].get(y)
                if not r:
                    cells.append("%-26s" % "-"); continue
                ok = (r["maxDD"] >= -K.DD_NEW and r["uw"] <= K.UW_NEW and r["qmin"] >= K.Q_NEW
                      and r["ret"] >= 0)
                cells.append("%7.2f/%4d/%+7.2f/%+6.2f %s" % (
                    r["maxDD"], r["uw"], r["ret"], r["qmin"], "P" if ok else "F"))
            print("  %-14s %s" % (t, " ".join(cells)))
        print("\n  TOAN KY:")
        G5 = {}
        for t in have:
            if t not in Sx:
                continue
            ok, bad, yb = K.fence(Sx[t], Yx[t], K.DD_NEW, K.UW_NEW, K.Q_NEW)
            G5[t] = dict(ok=ok, bad=bad)
            print("  %-14s n=%5d %s" % (t, S[t]["n"], "PASS" if ok else "FAIL (" + ", ".join(bad) + ")"))
        res["gates"] = G5
        res["minute"] = {t: dict(dd_min=Sx[t]["maxDD"], dd_daily=mp[t]["dd_daily"],
                                 uw_min=Sx[t]["uw"], uw_daily=mp[t]["uw_daily"],
                                 py_min=mp[t]["py_min"]) for t in have if t in Sx}

    # ---- [6] ket luan ----
    print("\n[6] KET LUAN theo luat pre-reg §6 (>=2 rate TOT ngoai CI + 0 XAU + khong lam FAIL rao)")
    verdict = {}
    for lab, off, on in PAIRS:
        v = ci_sum.get(lab)
        if not v:
            continue
        rails = res.get("gates", {}).get(on, {}).get("ok")
        rails_moc = res.get("gates", {}).get(off, {}).get("ok")
        hon = bool(v["good"] >= 2 and v["bad"] == 0 and (rails is True or rails is None))
        verdict[lab] = dict(good=v["good"], bad=v["bad"], rails=rails, rails_moc=rails_moc,
                            hon=hon)
        print("  nEN %s: TOT=%d/5 XAU=%d/5 | rao §7 arm3=%s moc=%s | => %s" % (
            lab, v["good"], v["bad"], rails, rails_moc,
            "HON (arm3 tot hon)" if hon else "NULL (khong hon)"))
    res["verdict"] = verdict
    if jout:
        with open(jout, "w") as f:
            json.dump(res, f, indent=1, default=str)
        print("\n[json] %s" % jout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
