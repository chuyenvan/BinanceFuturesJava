"""TICKBLK — cham diem bien the "chan ca LUOT khi luot YEU" (docs/prereg/PREREG_TICK_BLOCK.md).

Doc lap voi selcut_score.py (chi tai dung may block-72h cua c3_rates.py, KHONG import lai file kia).
Doc output KAGGLE (/home/ubuntu/kaggle_sim/out/<tag>/) va dung inflate(k) theo
docs/audit/AUDIT_CI_INFLATE_STANDARDIZATION.md.

Bao cao:
  (a) 5 rate chat luong toan bo leg + n, moi bien the vs PARITY; CI block-72h 2000 rep seed 20260905
      o CA HAI do rong: x1.21 (brief yeu cau — rong hon) va inflate(3)=1,4822 (chuan hoa cho k=3).
      "Ngoai CI" chi tinh khi ngoai o CA HAI.
  (b) bang theo LEVEL (n, SumPnL, meanP, win%, TSloss%) — tra loi "BIG_DOWN/DCA co bi anh huong khong".
  (c) rang buoc cung theo RISK_APPETITE: maxDD/nam <=30, UW <=200, quy >=-15, khong nam am,
      tap trung 1 coin <=15%, do tu sim.out + printDone.csv.
  (d) PnL/equity RIENG (KHONG dung de chon).
  (e) EXPOSURE: % luot bi chan ([TICKBLK] SUMMARY trong sim.out) + so lenh mat (net + gross).

Usage: python3 tickblk_score.py PARITY_TAG VARIANT_TAG [VARIANT_TAG ...] [--k 3] [--json OUT.json]
"""
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

BLOCK_H = C.BLOCK_H            # 72
NREP = C.NREP                  # 2000
SEED = C.SEED                  # 20260905
LEGACY = 1.21                  # he so CU trong brief (rong hon inflate(3) => PRIMARY chat hon)
KOUT = "/home/ubuntu/kaggle_sim/out"
# Moc neo block-72h CO DINH cho MOI arm (cua so DEV 2021-07-01..2025-12-31) — giong selcut_score.py.
ANCHOR = pd.Timestamp("2021-07-01")

DD_MAX, UW_MAX, Q_MIN, CONC_MAX = 30.0, 200, -15.0, 15.0

RATES = [("win%", +1), ("TSloss%", -1), ("mP|SM", +1), ("mP|SL", +1), ("meanP", +1)]


def _paths(tag):
    base = os.path.join(KOUT, tag)
    return os.path.join(base, "storage", "printDone.csv"), os.path.join(base, "logs", "sim.out")


def equity(tag):
    _, sout = _paths(tag)
    rx = C.RX
    rows = []
    with open(sout, errors="ignore") as fh:
        for line in fh:
            m = rx.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "equity"]).drop_duplicates("d", keep="last")
    e["d"] = pd.to_datetime(e.d, format="%Y%m%d")
    return e.set_index("d").equity


def trades(tag):
    pdone, _ = _paths(tag)
    d = pd.read_csv(pdone, on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    for c in ("profit", "margin", "pnl", "symbolPred", "entry", "quantity"):
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["profit"]).copy()
    d["ts"] = pd.to_datetime(d["start"].astype(str), format="%Y%m%d %H:%M", errors="coerce")
    d = d.dropna(subset=["ts"])
    d = d.sort_values(["sym", "end", "ts"], kind="mergesort")
    d["leg"] = d.groupby(["sym", "end"]).cumcount()
    d["blk"] = ((d.ts - ANCHOR) / pd.Timedelta(hours=BLOCK_H)).astype(int)
    return d.reset_index(drop=True)


# ---- 5 rate chat luong (toan bo leg) -------------------------------------
# Moi rate la TY SO cua cac tong theo block => bootstrap block-72h chi can sufficient statistics
# tung block, tinh vector hoa. Cot: n, nwin, nsl, nsm, sumSM, sumSL, sumP.
def blk_stats(d):
    dm = d.loc[d.status == "STOP_MARKET_DONE"]
    dl = d.loc[d.status == "STOP_LOSS_DONE"]
    s = pd.DataFrame({
        "n": d.groupby("blk").size(),
        "nwin": d.assign(_w=(d.profit > 0).astype(int)).groupby("blk")["_w"].sum(),
        "nsl": dl.groupby("blk").size(),
        "nsm": dm.groupby("blk").size(),
        "sumSM": dm.groupby("blk")["profit"].sum(),
        "sumSL": dl.groupby("blk")["profit"].sum(),
        "sumP": d.groupby("blk")["profit"].sum(),
    })
    return s.fillna(0.0)


COL = {c: i for i, c in enumerate(["n", "nwin", "nsl", "nsm", "sumSM", "sumSL", "sumP"])}


def rate_from(S, which):
    n = S[:, COL["n"]]
    with np.errstate(invalid="ignore", divide="ignore"):
        if which == "win%":
            return 100.0 * S[:, COL["nwin"]] / n
        if which == "TSloss%":
            return 100.0 * S[:, COL["nsl"]] / n
        if which == "mP|SM":
            return S[:, COL["sumSM"]] / S[:, COL["nsm"]]
        if which == "mP|SL":
            return S[:, COL["sumSL"]] / S[:, COL["nsl"]]
        if which == "meanP":
            return S[:, COL["sumP"]] / n
    raise ValueError(which)


_CACHE = {}


def _stats_and_draws(tag):
    if tag in _CACHE:
        return _CACHE[tag]
    d = trades(tag)
    s = blk_stats(d)
    blocks = np.sort(d.blk.unique())
    M = s.reindex(blocks).fillna(0.0)[["n", "nwin", "nsl", "nsm", "sumSM", "sumSL", "sumP"]].to_numpy(float)
    _CACHE[tag] = (blocks, M)
    return _CACHE[tag]


def ci_pair(ta, tb, width):
    """CI paired block-72h cua hieu 5 rate giua 2 tag, tren UNION block cua hai ben."""
    ba, Ma = _stats_and_draws(ta)
    bb, Mb = _stats_and_draws(tb)
    blocks = np.union1d(ba, bb)
    A = pd.DataFrame(Ma, index=ba).reindex(blocks).fillna(0.0).to_numpy(float)
    B = pd.DataFrame(Mb, index=bb).reindex(blocks).fillna(0.0).to_numpy(float)
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(blocks), size=(NREP, len(blocks)))
    SA = A[idx].sum(axis=1)
    SB = B[idx].sum(axis=1)
    obsA = A.sum(axis=0, keepdims=True)
    obsB = B.sum(axis=0, keepdims=True)
    out = {}
    for name, dirc in RATES:
        ra = rate_from(SA, name)
        rb = rate_from(SB, name)
        ra = ra[np.isfinite(ra)]
        rb = rb[np.isfinite(rb)]
        m = min(len(ra), len(rb))
        arr = (ra[:m] - rb[:m]) if m else np.array([])
        obs = float(rate_from(obsA, name)[0] - rate_from(obsB, name)[0])
        if len(arr) == 0:
            out[name] = (obs, float("nan"), float("nan"), False)
            continue
        lo, hi = np.percentile(arr, [2.5, 97.5])
        c = (lo + hi) / 2.0
        lo, hi = c - (c - lo) * width, c + (hi - c) * width
        out[name] = (obs, float(lo), float(hi), not (lo <= 0.0 <= hi))
    return out


def yearly(s):
    out = {}
    for y, sy in s.groupby(s.index.year):
        dd = (sy / sy.cummax() - 1) * 100
        uw = sy < sy.cummax()
        uwmax = int(uw.groupby((~uw).cumsum()).sum().max()) if len(uw) else 0
        out[int(y)] = dict(dd=float(dd.min()), uw=uwmax,
                           ret=float(sy.iloc[-1] / sy.iloc[0] - 1) * 100)
    return out


def quarters(s):
    qe = s.resample("QE").last()
    q0 = pd.concat([pd.Series([s.iloc[0]], index=[s.index[0]]), qe]).iloc[:-1]
    return {str(p): float(v) * 100 for p, v in zip(qe.index.to_period("Q"), qe.values / q0.values - 1)}


def conc_max(tag):
    """max % equity 1 coin = max over cum (sym,end) cua sum(margin) / equity NGAY CUA LEG CUOI."""
    d = trades(tag)
    eq = equity(tag)
    d["day"] = d["start"].astype(str).str.slice(0, 8)
    d["eq"] = d["day"].map(eq)
    g = d.groupby(["sym", "end"])
    cm = pd.DataFrame({"tot": g["margin"].sum(), "eq0": g["eq"].last()}).reset_index()
    cm["pct"] = cm.tot / cm.eq0 * 100
    return float(cm.pct.max()) if len(cm) else float("nan")


def summary(tag):
    d = trades(tag)
    s = equity(tag)
    years = (s.index[-1] - s.index[0]).days / 365.25
    return dict(tag=tag, n=len(d), end=float(s.iloc[-1]),
                cagr=float((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100,
                maxDD=float((s / s.cummax() - 1).min() * 100),
                uw=int((s < s.cummax()).groupby((s >= s.cummax()).cumsum()).sum().max()),
                yr=yearly(s), qmin=min(quarters(s).values()), conc=conc_max(tag),
                sumP=float(d.profit.sum()))


def level_table(d):
    out = {}
    for lv, g in d.groupby("level"):
        out[lv] = dict(n=int(len(g)), sumPnL=float(g.pnl.sum()), meanP=float(g.profit.mean()),
                       win=100.0 * (g.profit > 0).mean(),
                       tsloss=100.0 * (g.status == "STOP_LOSS_DONE").mean())
    out["ALL"] = dict(n=int(len(d)), sumPnL=float(d.pnl.sum()), meanP=float(d.profit.mean()),
                      win=100.0 * (d.profit > 0).mean(),
                      tsloss=100.0 * (d.status == "STOP_LOSS_DONE").mean())
    return out


# ---- (e) EXPOSURE: % luot bi chan + so lenh mat ---------------------------
def tickblk_summary(tag):
    _, sout = _paths(tag)
    for line in open(sout, errors="ignore"):
        if "[TICKBLK] SUMMARY" in line:
            return line.strip().split("SUMMARY", 1)[1].strip()
    return None


def blocked_minutes(tag):
    p = os.path.join(KOUT, tag, "storage", "tickblk_blocked_min.csv")
    if not os.path.exists(p):
        return None
    m = pd.read_csv(p)["minute"].astype(str)
    return set(m)


def exposure(ptag, vtag):
    """So lenh mat: net (n_par - n_var) + gross (lenh cua parity mo tai phut bi chan) + theo level."""
    dp, dv = trades(ptag), trades(vtag)
    bl = blocked_minutes(vtag)
    if bl is None:
        return {"blocked_file": None, "net": len(dp) - len(dv)}
    mins = dp["start"].astype(str)
    hit = mins.isin(bl)
    o = {"blocked_file": True, "blocked_minutes": len(bl), "net": int(len(dp) - len(dv)),
         "gross": int(hit.sum()), "gross_pct_orders": float(100.0 * hit.sum() / len(dp))}
    o["gross_by_level"] = {str(k): int(v) for k, v in dp.loc[hit].groupby("level").size().items()}
    # kiem tra: moi lenh "gross" phai KHONG con trong bien the o cung phut/sym/level
    keyp = set(zip(dp.loc[hit, "start"].astype(str), dp.loc[hit, "sym"], dp.loc[hit, "level"]))
    keyv = set(zip(dv["start"].astype(str), dv["sym"], dv["level"]))
    o["gross_van_con_trong_bien_the"] = len(keyp & keyv)
    return o


def main():
    pos, k, jout = [], 3, None
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--k":
            k = int(sys.argv[i + 1]); i += 2; continue
        if a == "--json":
            jout = sys.argv[i + 1]; i += 2; continue
        if a.startswith("--"):
            i += 1; continue
        pos.append(a); i += 1
    argv = pos
    W_STD = C.inflate(k)
    parity, variants = argv[0], argv[1:]

    print("=== TICKBLK SCORE — parity=%s | k=%d | inflate(k)=%.4f | legacy=%.2f" % (
        parity, k, W_STD, LEGACY))
    print("    CI block-%dh, %d rep, seed %d, neo %s. 'NGOAI CI' = ngoai o CA HAI do rong." % (
        BLOCK_H, NREP, SEED, ANCHOR.date()))

    D = {t: trades(t) for t in argv}
    S = {t: summary(t) for t in argv}
    L = {t: level_table(D[t]) for t in argv}

    print("\n=== (a) 5 RATE CHAT LUONG toan bo leg ===")
    print("%-16s %6s %8s %8s %10s %10s %10s" % ("tag", "n", "win%", "TSloss%", "mP|SM", "mP|SL", "meanP"))
    for t in argv:
        d = D[t]
        lv = L[t]["ALL"]
        print("%-16s %6d %8.2f %8.2f %10.3f %10.3f %10.3f" % (
            t, len(d), lv["win"], lv["tsloss"],
            float(d.loc[d.status == "STOP_MARKET_DONE", "profit"].mean()),
            float(d.loc[d.status == "STOP_LOSS_DONE", "profit"].mean()), lv["meanP"]))

    res = {"k": k, "inflate_k": W_STD, "legacy": LEGACY, "summary": {}, "rates": {},
           "levels": {}, "levels_parity": L[parity], "exposure": {}, "tickblk": {}}

    print("\n=== (a2) CI cua hieu (bien the - parity), CA HAI do rong 72h ===")
    print("%-16s %9s %30s %30s %6s %6s" % ("tag", "rate", "CI @%.2f (legacy)" % LEGACY,
                                           "CI @%.4f (inflate k)" % W_STD, "outL", "outS"))
    verdict = {}
    for v in variants:
        c1 = ci_pair(v, parity, LEGACY)
        c2 = ci_pair(v, parity, W_STD)
        c2b = ci_pair(v, parity, W_STD)   # cung seed/du lieu => phai TRUNG (tu-kiem)
        assert all(abs(c2[r][0] - c2b[r][0]) < 1e-12 and abs(c2[r][1] - c2b[r][1]) < 1e-12
                   for r in c2), "bootstrap khong tai lap duoc voi cung seed!"
        n_good = n_out = n_bad = 0
        det = {}
        for name, dirc in RATES:
            obs = c1[name][0]
            lo1, hi1, o1 = c1[name][1], c1[name][2], c1[name][3]
            lo2, hi2, o2 = c2[name][1], c2[name][2], c2[name][3]
            out = o1 and o2
            good = out and ((dirc > 0 and obs > 0) or (dirc < 0 and obs < 0))
            bad = out and not good
            n_good += int(good)
            n_out += int(o1)
            n_bad += int(bad)
            det[name] = dict(obs=obs, lo_legacy=lo1, hi_legacy=hi1, lo_std=lo2, hi_std=hi2,
                             out_both=out, good=bool(good), bad=bool(bad),
                             dir="up" if dirc > 0 else "down")
            print("%-16s %9s %11.3f [%9.3f,%9.3f] %11.3f [%9.3f,%9.3f] %6s %6s" % (
                v, name, obs, lo1, hi1, obs, lo2, hi2, "Y" if o1 else "-", "Y" if o2 else "-"))
        verdict[v] = dict(n_good=n_good, n_out_legacy=n_out, n_bad=n_bad, detail=det)
        print("   >>> %-10s rate NGOAI CI (ca 2 do rong) CUNG HUONG TOT = %d/5 | XAU ngoai CI = %d/5" % (
            v, n_good, n_bad))
    res["rates"] = verdict

    print("\n=== (b) SO LENH / PnL THEO LEVEL ===")
    print("%-16s %-22s %7s %14s %10s %8s %8s" % ("tag", "level", "n", "SumPnL", "meanP", "win%", "TSloss%"))
    for t in argv:
        for lv in ("PREDICT_SYMBOL_TRADE", "BIG_DOWN", "DCA_LEVEL1", "ALL"):
            r = L[t].get(lv)
            if r is None:
                print("%-16s %-22s %7s %14s %10s %8s %8s" % (t, lv, 0, "-", "-", "-", "-"))
                continue
            print("%-16s %-22s %7d %14.1f %10.3f %8.2f %8.2f" % (
                t, lv, r["n"], r["sumPnL"], r["meanP"], r["win"], r["tsloss"]))
    print("\n  DELTA vs parity (dn, dSumPnL, dmeanP):")
    for v in variants:
        for lv in ("PREDICT_SYMBOL_TRADE", "BIG_DOWN", "DCA_LEVEL1", "ALL"):
            a, b = L[v].get(lv), L[parity].get(lv)
            if not a or not b:
                continue
            print("   %-10s %-22s dn=%+5d dPnL=%+12.1f dmeanP=%+9.3f" % (
                v, lv, a["n"] - b["n"], a["sumPnL"] - b["sumPnL"], a["meanP"] - b["meanP"]))

    print("\n=== (c) RANG BUOC CUNG (RISK_APPETITE) ===")
    print("%-16s %10s %6s %8s %8s %8s %8s %8s %10s" % (
        "tag", "end", "CAGR", "maxDD", "UW", "qmin", "conc%", "sumP", "PASS?"))
    for t in argv:
        s = S[t]
        ok = (s["maxDD"] >= -DD_MAX and s["uw"] <= UW_MAX and s["qmin"] >= Q_MIN
              and all(v["ret"] > 0 for v in s["yr"].values()) and s["conc"] <= CONC_MAX)
        print("%-16s %10.0f %6.2f %8.2f %8d %8.2f %8.2f %8.0f %10s" % (
            t, s["end"], s["cagr"], s["maxDD"], s["uw"], s["qmin"], s["conc"], s["sumP"],
            "PASS" if ok else "FAIL"))
    print("\n  theo NAM (dd / uw / ret%):")
    for t in argv:
        print("   %-16s" % t + " | ".join(
            "%d:%.2f/%d/%+.2f" % (y, v["dd"], v["uw"], v["ret"]) for y, v in sorted(S[t]["yr"].items())))

    print("\n=== (e) EXPOSURE: % luot bi chan + SO LENH MAT ===")
    for t in argv:
        line = tickblk_summary(t)
        res["tickblk"][t] = line
        print("  %-16s %s" % (t, line if line else "(khong co dong [TICKBLK] — chan OFF)"))
    print("\n  %-16s %7s %8s %10s %8s %26s" % ("tag", "net", "gross", "gross%ord", "con_lai", "gross theo level"))
    for v in variants:
        e = exposure(parity, v)
        res["exposure"][v] = e
        if e.get("blocked_file") is None:
            print("  %-16s %7d %8s %10s %8s %26s" % (v, e["net"], "-", "-", "-", "(khong co file phut chan)"))
            continue
        print("  %-16s %7d %8d %10.2f %8d %26s" % (
            v, e["net"], e["gross"], e["gross_pct_orders"], e["gross_van_con_trong_bien_the"],
            json.dumps(e["gross_by_level"])))

    print("\n=== (d) KET LUAN (theo quy tac pre-reg muc 5) ===")
    for v in variants:
        vd = verdict[v]
        s = S[v]
        hard = (s["maxDD"] >= -DD_MAX and s["uw"] <= UW_MAX and s["qmin"] >= Q_MIN
                and all(x["ret"] > 0 for x in s["yr"].values()) and s["conc"] <= CONC_MAX)
        if vd["n_good"] >= 2 and hard and vd["n_bad"] == 0:
            print("   %-10s => DAT cong chat luong cua vong nay (>=2 rate ngoai CI cung huong tot, "
                  "0 rate xau ngoai CI, het chan cung)" % v)
        else:
            print("   %-10s => KHONG DAT (rate_tot=%d/5, rate_xau=%d/5, chan_cung=%s)" % (
                v, vd["n_good"], vd["n_bad"], "PASS" if hard else "FAIL"))

    if jout:
        with open(jout, "w") as f:
            json.dump(res, f, indent=1, default=str)
        print("\njson -> %s" % jout)


if __name__ == "__main__":
    main()
