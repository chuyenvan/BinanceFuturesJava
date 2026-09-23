"""TRAIL-LADDER — cham diem bien the gap BAC THANG (docs/PREREG_TRAIL_LADDER.md).

Doc output KAGGLE (/home/ubuntu/kaggle_sim/out/<tag>/) — khong doc devrun Oracle (o day khong chay Java).

Bao cao (theo pre-reg §4):
  (a) 5 rate chat luong (theo LEG, toan bo) + n, moi bien the vs PARITY; CI block-72h 2000 rep
      seed 20260905 o CA HAI do rong: x1.21 (legacy, muc brief yeu cau) va inflate(3)=1.482304
      (chuan hoa, trung tien le RESULT_TRAIL_HINGE). "Ngoai CI" chi tinh khi ngoai o CA HAI.
  (b) rang buoc cung RISK_APPETITE: maxDD/nam <=30, UW <=200, quy >=-15, khong nam am,
      tap trung 1 coin <=15% (conc_max) — do tu sim.out + printDone.csv; + bang theo nam.
  (c) DO RIENG "bat song lon" (§3.2) tu storage/trailTrace.csv: lenh co peak >= +20/50/100%:
      n, % bi cat som (STOP_MARKET_DONE / gap thuc pp / phan bo exit reason), capture ratio.
  (d) PnL/equity rieng (KHONG dung de chon).

Usage: python3 traillad_score.py PARITY_TAG VARIANT_TAG [VARIANT_TAG ...] [--k 3] [--json OUT.json]
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
LEGACY = 1.21                  # he so CU (brief yeu cau; rong hon inflate(3))
KOUT = "/home/ubuntu/kaggle_sim/out"
ANCHOR = pd.Timestamp("2021-07-01")     # moc neo block CO DINH cho MOI arm

DD_MAX, UW_MAX, Q_MIN, CONC_MAX = 30.0, 200, -15.0, 15.0
PEAK_LEVELS = (0.20, 0.50, 1.00)        # nguong "song lon" (pre-reg §3.2)


def _paths(tag):
    base = os.path.join(KOUT, tag)
    pdone = os.path.join(base, "storage", "printDone.csv")
    sout = os.path.join(base, "logs", "sim.out")
    for p in (pdone, sout):
        if not os.path.exists(p):
            raise FileNotFoundError(p)
    return pdone, sout


def trace_path(tag):
    return os.path.join(KOUT, tag, "storage", "trailTrace.csv")


def equity(tag):
    _, sout = _paths(tag)
    rows = []
    with open(sout, errors="ignore") as fh:
        for line in fh:
            m = C.RX.search(line)
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
    d["blk"] = ((d.ts - ANCHOR) / pd.Timedelta(hours=BLOCK_H)).astype(int)
    return d.reset_index(drop=True)


def trace(tag):
    """Bang DO LUONG trailing (peak) — file rieng, xem pre-reg §3.2."""
    p = trace_path(tag)
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p, on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    for c in ("entry", "tp", "ratePct", "peak", "peakPct", "quantity", "margin", "pnl"):
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    return d.dropna(subset=["ratePct", "peakPct"]).reset_index(drop=True)


# ---------- 5 rate chat luong (vector hoa theo block) ----------------------
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
RATES = [("win%", +1), ("TSloss%", -1), ("mP|SM", +1), ("mP|SL", +1), ("meanP", +1)]


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


def _mat(tag):
    if tag in _CACHE:
        return _CACHE[tag]
    d = trades(tag)
    s = blk_stats(d)
    blocks = np.sort(d.blk.unique())
    M = s.reindex(blocks).fillna(0.0)[["n", "nwin", "nsl", "nsm", "sumSM", "sumSL", "sumP"]].to_numpy(float)
    _CACHE[tag] = (blocks, M)
    return _CACHE[tag]


def ci_pair(ta, tb, width):
    ba, Ma = _mat(ta)
    bb, Mb = _mat(tb)
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
        ra, rb = rate_from(SA, name), rate_from(SB, name)
        ra, rb = ra[np.isfinite(ra)], rb[np.isfinite(rb)]
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
    """max % equity 1 coin: max over cum (sym,end) cua sum(margin) / equity NGAY CUA LEG CUOI.

    (Quy uoc trung tien le selcut_score/bd_sel_score: dong 'last' cua cum theo thu tu file.)
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
    years = (s.index[-1] - s.index[0]).days / 365.25
    yr = yearly(s)
    qr = quarters(s)
    return dict(
        tag=tag, n=len(d), end=float(s.iloc[-1]),
        cagr=float((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100,
        maxDD=float((s / s.cummax() - 1).min() * 100),
        uw=int((s < s.cummax()).groupby((s >= s.cummax()).cumsum()).sum().max()),
        yr=yr, qmin=min(qr.values()), nq=len(qr), conc=conc_max(tag),
        neg_year=[y for y, v in yr.items() if v["ret"] < 0],
        first=str(s.index[0].date()), last=str(s.index[-1].date()),
    )


def levels(d):
    out = {}
    for lv, g in d.groupby("level"):
        out[lv] = dict(n=int(len(g)), sumPnL=float(g.pnl.sum()), meanP=float(g.profit.mean()),
                       win=100.0 * (g.profit > 0).mean(),
                       tsloss=100.0 * (g.status == "STOP_LOSS_DONE").mean())
    out["ALL"] = dict(n=int(len(d)), sumPnL=float(d.pnl.sum()), meanP=float(d.profit.mean()),
                      win=100.0 * (d.profit > 0).mean(),
                      tsloss=100.0 * (d.status == "STOP_LOSS_DONE").mean())
    return out


# ---------- (c) DO RIENG "bat song lon" ------------------------------------
def bigmove(t, lv):
    """Thong ke nhom lenh co peakPct >= lv (theo LEG, tu trailTrace.csv)."""
    if t is None:
        return None
    g = t.loc[t.peakPct >= lv * 100.0]
    if len(g) == 0:
        return dict(n=0)
    st = g.status.value_counts(normalize=True) * 100.0
    return dict(
        n=int(len(g)),
        pct_trailing=float(st.get("STOP_MARKET_DONE", 0.0)),
        pct_sl=float(st.get("STOP_LOSS_DONE", 0.0)),
        reason={k: float(v) for k, v in st.items()},
        med_gap_pp=float((g.peakPct - g.ratePct).median()),
        mean_gap_pp=float((g.peakPct - g.ratePct).mean()),
        med_capture=float((g.ratePct / g.peakPct).median()),
        mean_capture=float((g.ratePct / g.peakPct).mean()),
        agg_capture=float(g.ratePct.mean() / g.peakPct.mean()) if g.peakPct.mean() else float("nan"),
        sumPnL=float(g.pnl.sum()),
        meanP=float(g.profit.mean()) if "profit" in g.columns else float("nan"),
        med_peakPct=float(g.peakPct.median()),
        med_ratePct=float(g.ratePct.median()),
    )


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

    print("=== TRAIL-LADDER SCORE — parity=%s | k=%d | inflate(k)=%.6f | legacy=%.2f" % (
        parity, k, W_STD, LEGACY))
    print("    CI block-%dh, %d rep, seed %d, anchor %s. 'NGOAI CI' = ngoai o CA HAI do rong." % (
        BLOCK_H, NREP, SEED, ANCHOR.date()))

    D = {t: trades(t) for t in argv}
    S = {t: summary(t) for t in argv}
    L = {t: levels(D[t]) for t in argv}
    T = {t: trace(t) for t in argv}
    for t in argv:
        print("    trace[%s] = %s dong" % (t, "KHONG CO" if T[t] is None else len(T[t])))

    print("\n=== (a) 5 RATE CHAT LUONG toan bo leg (theo printDone.csv) ===")
    print("%-9s %6s %8s %8s %10s %10s %10s" % ("tag", "n", "win%", "TSloss%", "mP|SM", "mP|SL", "meanP"))
    for t in argv:
        d = D[t]
        lv = L[t]["ALL"]
        print("%-9s %6d %8.2f %8.2f %10.3f %10.3f %10.3f" % (
            t, len(d), lv["win"], lv["tsloss"],
            float(d.loc[d.status == "STOP_MARKET_DONE", "profit"].mean()),
            float(d.loc[d.status == "STOP_LOSS_DONE", "profit"].mean()), lv["meanP"]))

    res = {"k": k, "inflate_k": W_STD, "legacy": LEGACY, "summary": {}, "rates": {},
           "levels": {}, "bigmove": {}}
    for t in argv:
        res["summary"][t] = S[t]
        res["levels"][t] = L[t]

    print("\n=== (a2) CI cua hieu (bien the - parity), CA HAI do rong block-72h ===")
    print("%-9s %9s %24s %30s %6s %6s %6s" % ("tag", "rate", "CI @%.2f (legacy)" % LEGACY,
                                              "CI @%.6f (inflate k)" % W_STD, "outL", "outS", "HUONG"))
    verdict = {}
    for v in variants:
        c1 = ci_pair(v, parity, LEGACY)
        c2 = ci_pair(v, parity, W_STD)
        c3 = ci_pair(v, parity, W_STD)
        assert all(abs(c2[r][0] - c3[r][0]) < 1e-12 and abs(c2[r][1] - c3[r][1]) < 1e-12
                   for r in c2), "bootstrap khong tai lap duoc voi cung seed!"
        n_good = n_bad = n_out_std = 0
        det = {}
        for name, dirc in RATES:
            obs = c1[name][0]
            lo1, hi1, o1 = c1[name][1], c1[name][2], c1[name][3]
            lo2, hi2, o2 = c2[name][1], c2[name][2], c2[name][3]
            out = o1 and o2
            good = out and ((dirc > 0 and obs > 0) or (dirc < 0 and obs < 0))
            bad = out and not good
            n_good += int(good)
            n_out_std += int(o1)
            n_bad += int(bad)
            det[name] = dict(obs=obs, lo_legacy=lo1, hi_legacy=hi1, lo_std=lo2, hi_std=hi2,
                             out_both=bool(out), good=bool(good), bad=bool(bad),
                             dir="up" if dirc > 0 else "down")
            print("%-9s %9s %11.3f [%9.3f,%9.3f] %11.3f [%9.3f,%9.3f] %6s %6s %6s" % (
                v, name, obs, lo1, hi1, obs, lo2, hi2, "Y" if o1 else "-", "Y" if o2 else "-",
                "TOT" if good else ("XAU" if bad else "-")))
        verdict[v] = dict(n_good=n_good, n_out_legacy=n_out_std, n_bad=n_bad, detail=det)
        print("   >>> %-6s rate NGOAI CI (ca 2 do rong) CUNG HUONG TOT = %d/5 | XAU ngoai CI = %d/5" % (
            v, n_good, n_bad))
    res["rates"] = verdict

    print("\n=== (b) RANG BUOC CUNG (RISK_APPETITE) + theo nam ===")
    print("%-9s %10s %8s %7s %6s %8s %9s %s" % ("tag", "equity", "CAGR%", "maxDD%", "UW",
                                                "quy min%", "conc%", "PASS"))
    for t in argv:
        s = S[t]
        ok = (s["maxDD"] >= -DD_MAX and s["uw"] <= UW_MAX and s["qmin"] >= Q_MIN
              and not s["neg_year"] and s["conc"] <= CONC_MAX)
        print("%-9s %10.0f %8.2f %7.2f %6d %8.2f %9.2f %s" % (
            t, s["end"], s["cagr"], s["maxDD"], s["uw"], s["qmin"], s["conc"],
            "PASS" if ok else "FAIL"))
    print("\n  theo nam (maxDD% / UW / ret%):")
    yrs = sorted({y for t in argv for y in S[t]["yr"]})
    print("    %-9s %s" % ("tag", " ".join("%22d" % y for y in yrs)))
    for t in argv:
        print("    %-9s %s" % (t, " ".join(
            "%7.2f/%5d/%7.2f" % (S[t]["yr"][y]["dd"], S[t]["yr"][y]["uw"], S[t]["yr"][y]["ret"])
            for y in yrs if y in S[t]["yr"])))

    print("\n=== (c) BAT SONG LON: lenh co peak >= 20% / 50% / 100% (trailTrace.csv) ===")
    for lv in PEAK_LEVELS:
        print("\n  -- peak >= +%d%% --" % int(lv * 100))
        print("  %-9s %6s %11s %11s %12s %11s %11s %12s" % (
            "tag", "n", "%trailing", "med_gap_pp", "mean_gap_pp", "med_capture", "mean_capture",
            "SumPnL"))
        for t in argv:
            r = bigmove(T[t], lv)
            if r is None or r.get("n", 0) == 0:
                print("  %-9s %6s %11s %11s %12s %11s %11s %12s" % (t, 0, "-", "-", "-", "-", "-", "-"))
                continue
            print("  %-9s %6d %11.1f %11.2f %12.2f %11.3f %11.3f %12.1f" % (
                t, r["n"], r["pct_trailing"], r["med_gap_pp"], r["mean_gap_pp"],
                r["med_capture"], r["mean_capture"], r["sumPnL"]))
            res["bigmove"].setdefault(t, {})["%d" % int(lv * 100)] = r

    print("\n=== (d) PnL / EQUITY (KHONG dung de chon) + theo LEVEL ===")
    print("%-9s %-22s %7s %14s %10s %8s %8s" % ("tag", "level", "n", "SumPnL", "meanP", "win%", "TSloss%"))
    for t in argv:
        for lv in sorted(set(L[t].keys()) - {"ALL"}) + ["ALL"]:
            r = L[t][lv]
            print("%-9s %-22s %7d %14.1f %10.3f %8.2f %8.2f" % (
                t, lv, r["n"], r["sumPnL"], r["meanP"], r["win"], r["tsloss"]))

    if jout:
        with open(jout, "w") as f:
            json.dump(res, f, indent=1, default=str)
        print("\n[json] %s" % jout)


if __name__ == "__main__":
    main()
