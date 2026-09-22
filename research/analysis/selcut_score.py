"""SELCUT — cham diem bien the cat/gioi han leg SELECTOR (docs/PREREG_SELECTOR_LEG_CUT.md).

Doc lap voi bd_sel_score.py (file do doc CHET tu /home/ubuntu/java/devrun va dung C.CI_INFLATE
da bi go). File nay doc output KAGGLE (/home/ubuntu/kaggle_sim/out/<tag>/) va dung inflate(k)
theo docs/AUDIT_CI_INFLATE_STANDARDIZATION.md.

Bao cao:
  (a) 5 rate chat luong toan bo leg + n, moi bien the vs PARITY, CI block-72h 2000 rep seed 20260905
      o CA HAI do rong: x1.21 (legacy, rong hon) va inflate(2)=1,1774 (chuan hoa). "Ngoai CI" chi tinh
      khi ngoai o CA HAI.
  (b) bang theo LEVEL (n, SumPnL, meanP, win%, TSloss%) — tra loi cau hoi "BIG_DOWN/DCA co tang khong".
  (c) rang buoc cung theo RISK_APPETITE: maxDD/nam <=30, UW <=200, quy >=-15, khong nam am,
      tap trung 1 coin <=15%, do tu sim.out + printDone.csv.
  (d) PnL/equity rieng (KHONG dung de chon).

Usage: python3 selcut_score.py PARITY_TAG VARIANT_TAG [VARIANT_TAG ...] [--k 2] [--json OUT.json]
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

BLOCK_H = C.BLOCK_H            # 72
NREP = C.NREP                  # 2000
SEED = C.SEED                  # 20260905
LEGACY = 1.21                  # he so CU (rong hon inflate(2))
KOUT = "/home/ubuntu/kaggle_sim/out"
# [SELCUT] Moc neo block-72h CO DINH cho MOI arm (cua so DEV 2021-07-01..2025-12-31).
#   c3_rates.trades() neo block vao ts.min() CUA TUNG BANG => neu 2 arm co lenh dau tien lech
#   gio thi so hieu block lech nhau => ghep cap "paired" SAI. O day neo cung mot moc lich.
ANCHOR = pd.Timestamp("2021-07-01")

DD_MAX, UW_MAX, Q_MIN, CONC_MAX = 30.0, 200, -15.0, 15.0


def _paths(tag):
    base = os.path.join(KOUT, tag)
    pdone = os.path.join(base, "storage", "printDone.csv")
    sout = os.path.join(base, "logs", "sim.out")
    for p in (pdone, sout):
        if not os.path.exists(p):
            raise FileNotFoundError(p)
    return pdone, sout


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
# Moi rate la TY SO cua cac tong theo block => bootstrap block-72h chi can
# du-lieu-du (sufficient statistics) tung block, tinh vector hoa (nhanh ~1000x, ket qua Y HET
# cach pd.concat tung rep). Cot: n, nwin, nsl, nsm, sumSM, sumSL, sumP.
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
    """Rate tu vector tong (7 phan tu) — vector hoa, nhan ca ma tran [ndraw, 7]."""
    n = S[:, COL["n"]]
    with np.errstate(invalid="ignore", divide="ignore"):
        if which == "win%":
            return 100.0 * S[:, COL["nwin"]] / n
        if which == "TSloss%":
            return 100.0 * S[:, COL["nsl"]] / n
        if which == "mP|SM":
            m = S[:, COL["nsm"]]
            return S[:, COL["sumSM"]] / m
        if which == "mP|SL":
            m = S[:, COL["nsl"]]
            return S[:, COL["sumSL"]] / m
        if which == "meanP":
            return S[:, COL["sumP"]] / n
    raise ValueError(which)


RATES = [("win%", +1), ("TSloss%", -1), ("mP|SM", +1), ("mP|SL", +1), ("meanP", +1)]
_CACHE = {}


def _stats_and_draws(tag, width, rep_seed=SEED):
    """Tra ve ma tran rate [NREP, 5] cua tag tren cung mot tap block (cache theo tag)."""
    if tag in _CACHE:
        return _CACHE[tag]
    d = trades(tag)
    s = blk_stats(d)
    blocks = np.sort(np.union1d(d.blk.unique(), d.blk.unique()))
    M = s.reindex(blocks).fillna(0.0)[["n", "nwin", "nsl", "nsm", "sumSM", "sumSL", "sumP"]].to_numpy(float)
    _CACHE[tag] = (blocks, M)
    return _CACHE[tag]


def ci_pair(ta, tb, width):
    """CI paired block-72h cua hieu 5 rate giua 2 tag, tren UNION block cua hai ben."""
    ba, Ma = _stats_and_draws(ta, width)
    bb, Mb = _stats_and_draws(tb, width)
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
        arr = arr[np.isfinite(arr)]
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
    return {str(p): float(v) * 100
            for p, v in zip(qe.index.to_period("Q"), qe.values / q0.values - 1)}


def conc_max(tag):
    """max % equity 1 coin = max over cum (sym,end) cua sum(margin) / equity NGAY CUA LEG CUOI.

    Quy uoc nay lay dung tien le da cong bo (bd_sel_score.py: `eq0=("eq","first")` tren file
    printDone doc theo THU TU FILE = end giam dan => dong "first" cua cum la LEG CUOI; parity
    9.77%, DROP/MIX/DROP_TOP8 9.76/9.79/9.79). Neu lay theo NGAY LEG DAU thi parity = 8.71%
    (do lai trong vong nay, ca hai deu duoi tran 15% nen khong doi ket luan).
    """
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
    yr = yearly(s)
    qr = quarters(s)
    years = (s.index[-1] - s.index[0]).days / 365.25
    return dict(
        tag=tag, n=len(d), end=float(s.iloc[-1]),
        cagr=float((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100,
        maxDD=float((s / s.cummax() - 1).min() * 100),
        uw=int((s < s.cummax()).groupby((s >= s.cummax()).cumsum()).sum().max()),
        yr=yr, qmin=min(qr.values()), nq=len(qr), conc=conc_max(tag),
        spread_days=(s.index[-1] - s.index[0]).days,
        first=str(s.index[0].date()), last=str(s.index[-1].date()),
    )


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


def main():
    pos, k, jout = [], 2, None
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

    print("=== SELCUT SCORE — parity=%s | k=%d | inflate(k)=%.4f | legacy=%.2f" % (
        parity, k, W_STD, LEGACY))
    print("    CI block-%dh, %d rep, seed %d. 'NGOAI CI' = ngoai o CA HAI do rong." % (
        BLOCK_H, NREP, SEED))

    D = {t: trades(t) for t in argv}
    S = {t: summary(t) for t in argv}
    L = {t: level_table(D[t]) for t in argv}

    print("\n=== (a) 5 RATE CHAT LUONG toan bo leg ===")
    print("%-10s %6s %8s %8s %10s %10s %10s" % ("tag", "n", "win%", "TSloss%", "mP|SM", "mP|SL", "meanP"))
    for t in argv:
        d = D[t]
        lv = L[t]["ALL"]
        print("%-10s %6d %8.2f %8.2f %10.3f %10.3f %10.3f" % (
            t, len(d), lv["win"], lv["tsloss"],
            float(d.loc[d.status == "STOP_MARKET_DONE", "profit"].mean()),
            float(d.loc[d.status == "STOP_LOSS_DONE", "profit"].mean()), lv["meanP"]))

    res = {"k": k, "inflate_k": W_STD, "legacy": LEGACY, "summary": {}, "rates": {},
           "levels": {}, "levels_parity": L[parity]}
    for t in argv:
        res["summary"][t] = S[t]
        res["levels"][t] = L[t]

    print("\n=== (a2) CI cua hieu (bien the - parity), CA HAI do rong 72h ===")
    print("%-10s %9s %28s %28s %7s %7s" % ("tag", "rate", "CI @%.2f (legacy)" % LEGACY,
                                           "CI @%.4f (inflate k)" % W_STD, "outL", "outS"))
    verdict = {}
    for v in variants:
        c1 = ci_pair(v, parity, LEGACY)
        c2 = ci_pair(v, parity, W_STD)
        c2_fresh = ci_pair(v, parity, W_STD)   # cung seed/du lieu => phai TRUNG (tu-kiem)
        assert all(abs(c2[r][0] - c2_fresh[r][0]) < 1e-12 and abs(c2[r][1] - c2_fresh[r][1]) < 1e-12
                   for r in c2), "bootstrap khong tai lap duoc voi cung seed!"
        n_good = n_outstd = n_bad = 0
        det = {}
        for name, dirc in RATES:
            obs = c1[name][0]
            lo1, hi1, o1 = c1[name][1], c1[name][2], c1[name][3]
            lo2, hi2, o2 = c2[name][1], c2[name][2], c2[name][3]
            out = o1 and o2
            good = out and ((dirc > 0 and obs > 0) or (dirc < 0 and obs < 0))
            bad = out and not good
            n_good += int(good)
            n_outstd += int(o1)
            n_bad += int(bad)
            det[name] = dict(obs=obs, lo_legacy=lo1, hi_legacy=hi1, lo_std=lo2, hi_std=hi2,
                             out_both=out, good=bool(good), bad=bool(bad),
                             dir="up" if dirc > 0 else "down")
            print("%-10s %9s %11.3f [%9.3f,%9.3f] %11.3f [%9.3f,%9.3f] %7s %7s" % (
                v, name, obs, lo1, hi1, obs, lo2, hi2, "Y" if o1 else "-", "Y" if o2 else "-"))
        verdict[v] = dict(n_good=n_good, n_out_legacy=n_outstd, n_bad=n_bad, detail=det)
        print("   >>> %-8s rate NGOAI CI (ca 2 do rong) CUNG HUONG TOT = %d/5 | XAU ngoai CI = %d/5" % (
            v, n_good, n_bad))
    res["rates"] = verdict

    print("\n=== (b) SO LENH / PnL THEO LEVEL (cau hoi chinh: BIG_DOWN & DCA co tang khong) ===")
    print("%-10s %-22s %7s %14s %10s %8s %8s" % ("tag", "level", "n", "SumPnL", "meanP", "win%", "TSloss%"))
    for t in argv:
        for lv in ("PREDICT_SYMBOL_TRADE", "BIG_DOWN", "DCA_LEVEL1", "ALL"):
            r = L[t].get(lv)
            if r is None:
                print("%-10s %-22s %7s %14s %10s %8s %8s" % (t, lv, 0, "-", "-", "-", "-"))
                continue
            print("%-10s %-22s %7d %14.1f %10.3f %8.2f %8.2f" % (
                t, lv, r["n"], r["sumPnL"], r["meanP"], r["win"], r["tsloss"]))
    print("\n  DELTA vs parity (n, SumPnL, meanP):")
    for v in variants:
        for lv in ("PREDICT_SYMBOL_TRADE", "BIG_DOWN", "DCA_LEVEL1", "ALL"):
            a, b = L[v].get(lv), L[parity].get(lv)
            if not a or not b:
                continue
            print("   %-8s %-22s dn=%+5d dPnL=%+12.1f dmeanP=%+9.3f" % (
                v, lv, a["n"] - b["n"], a["sumPnL"] - b["sumPnL"], a["meanP"] - b["meanP"]))

    print("\n=== (c) RANG BUOC CUNG (RISK_APPETITE) ===")
    print("%-10s %10s %6s %8s %8s %8s %8s %10s" % (
        "tag", "end", "CAGR", "maxDD", "UW", "qmin", "conc%", "PASS?"))
    for t in argv:
        s = S[t]
        ok = (s["maxDD"] >= -DD_MAX and s["uw"] <= UW_MAX and s["qmin"] >= Q_MIN
              and all(v["ret"] > 0 for v in s["yr"].values()) and s["conc"] <= CONC_MAX)
        print("%-10s %10.0f %6.2f %8.2f %8d %8.2f %8.2f %10s" % (
            t, s["end"], s["cagr"], s["maxDD"], s["uw"], s["qmin"], s["conc"],
            "PASS" if ok else "FAIL"))
    print("\n  theo NAM (dd / uw / ret%):")
    for t in argv:
        print("   %-10s" % t + " | ".join(
            "%d:%.2f/%d/%+.2f" % (y, v["dd"], v["uw"], v["ret"]) for y, v in sorted(S[t]["yr"].items())))

    print("\n=== (d) KET LUAN (theo quy tac pre-reg muc 5) ===")
    for v in variants:
        vd = verdict[v]
        s = S[v]
        hard = (s["maxDD"] >= -DD_MAX and s["uw"] <= UW_MAX and s["qmin"] >= Q_MIN
                and all(x["ret"] > 0 for x in s["yr"].values()) and s["conc"] <= CONC_MAX)
        if vd["n_good"] >= 2 and hard and vd["n_bad"] == 0:
            print("   %-8s => GO (>=2 rate ngoai CI cung huong tot + het chan cung + 0 rate xau ngoai CI)" % v)
        else:
            print("   %-8s => NO-GO/NULL (rate_tot=%d/5, rate_xau=%d/5, chan_cung=%s)" % (
                v, vd["n_good"], vd["n_bad"], "PASS" if hard else "FAIL"))
    if jout:
        with open(jout, "w") as f:
            json.dump(res, f, indent=1, default=str)
        print("\njson -> %s" % jout)


if __name__ == "__main__":
    main()
