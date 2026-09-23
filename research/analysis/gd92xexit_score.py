"""GD92 x EXIT — cham diem (docs/PREREG_GD92_X_EXIT.md).

Doc output KAGGLE (/home/ubuntu/kaggle_sim/out/<tag>/) — KHONG doc devrun Oracle cho cac chan moi
(chi doc devrun cho HANG THAM CHIEU HINGE V3, da co san tu truoc).

Bao cao:
  (a)  5 rate chat luong toan bo + n, moi chan vs PARITY (mac dinh gx-par1 = T170)
  (a2) CI block-72h o CA HAI do rong: legacy 1.21 + chuan hoa inflate(k) (pre-reg §5.2)
  (b)  rao cung RISK_APPETITE — CA toan ky LAN theo nam (bai hoc GD92)
  (b2) *** BANG PnL CHI TIET THEO NAM *** (n/win%/TSloss%/meanP/PnL USDT/ret%/maxDD%/UW/qmin%/equity)
  (c)  bat song lon: nhom dinh >=20/50/100% tu trailTrace.csv (capture ratio)
  (d)  n / hold / turnover / PnL / equity

Usage: python3 gd92xexit_score.py [--par gx-par1] [--k 3] [--json OUT.json] TAG [TAG ...]
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
LEGACY = 1.21                  # he so CU (brief owner yeu cau; rong hon inflate(k))
KOUT = "/home/ubuntu/kaggle_sim/out"
DEVRUN = "/home/ubuntu/java/devrun"
ANCHOR = pd.Timestamp("2021-07-01")     # moc neo block CO DINH cho MOI arm

DD_MAX, UW_MAX, Q_MIN, CONC_MAX = 30.0, 200, -15.0, 15.0
PEAK_LEVELS = (0.20, 0.50, 1.00)

# Tag dac biet -> thu muc goc (Kaggle out hoac devrun tham chieu da co san).
DIRS = {
    "T170": os.path.join(KOUT, "t170-x1-2021"),
    "HINGEV3": os.path.join(DEVRUN, "X1_TH_WEAK17_2021"),
    "LADDERL1": os.path.join(KOUT, "tl-l1"),
    # T170 + SIM_TRAIL_TRACE=1: printDone byte-identical efb793e2 => moc do CAPTURE cua T170
    # (run nay da co san tu vong TRAIL-LADDER, khong chay lai).
    "T170T": os.path.join(KOUT, "tl-part"),
}


def base(tag):
    return DIRS.get(tag, os.path.join(KOUT, tag))


def _paths(tag):
    b = base(tag)
    pdone = os.path.join(b, "storage", "printDone.csv")
    sout = os.path.join(b, "logs", "sim.out")
    if not os.path.exists(sout):
        gz = sout + ".gz"
        if os.path.exists(gz):
            import gzip
            with gzip.open(gz, "rt", errors="ignore") as f, open(sout, "w") as o:
                o.write(f.read())
    for p in (pdone, sout):
        if not os.path.exists(p):
            raise FileNotFoundError(p)
    return pdone, sout


def trace_path(tag):
    return os.path.join(base(tag), "storage", "trailTrace.csv")


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
    d["t_end"] = pd.to_datetime(d["end"].astype(str), format="%Y%m%d %H:%M", errors="coerce")
    d = d.sort_values(["sym", "end", "ts"], kind="mergesort")
    d["blk"] = ((d.ts - ANCHOR) / pd.Timedelta(hours=BLOCK_H)).astype(int)
    return d.reset_index(drop=True)


def trace(tag):
    p = trace_path(tag)
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p, on_bad_lines="skip", index_col=False)
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


def quarterly(s):
    qe = s.resample("QE").last()
    q0 = pd.concat([pd.Series([s.iloc[0]], index=[s.index[0]]), qe]).iloc[:-1]
    return {str(p): float(v) * 100 for p, v in zip(qe.index.to_period("Q"), qe.values / q0.values - 1)}


def conc_max(tag):
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
    dd = (s / s.cummax() - 1) * 100
    uw = (s < s.cummax()).groupby((s >= s.cummax()).cumsum()).sum()
    qr = quarterly(s)
    # hold (gio) giua start va end; neu end khong co gio thi bo qua
    hold = (d["t_end"] - d["ts"]).dt.total_seconds() / 3600.0
    hold = hold[np.isfinite(hold) & (hold >= 0)]
    ndays = len(np.unique(s.index.date))
    return dict(
        tag=tag, n=len(d), end=float(s.iloc[-1]),
        cagr=float((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100,
        maxDD=float(dd.min()),
        uw=int(uw.max()) if len(uw) else 0,
        qmin=min(qr.values()) if qr else float("nan"), nq=len(qr), conc=conc_max(tag),
        hold_med=float(hold.median()) if len(hold) else float("nan"),
        hold_mean=float(hold.mean()) if len(hold) else float("nan"),
        turn=float(len(d) / ndays) if ndays else float("nan"),
        sumpnl=float(d["pnl"].sum()) if "pnl" in d.columns else float("nan"),
        first=str(s.index[0].date()), last=str(s.index[-1].date()),
        ndays=ndays,
    )


def yearly_detail(tag):
    """Bang chi tiet theo nam: rate + PnL + rui ro (dung chung cho §b2)."""
    d = trades(tag)
    s = equity(tag)
    out = {}
    d["yr"] = d["ts"].dt.year
    for y in sorted(set(s.index.year)):
        sy = s[s.index.year == y]
        dy = d[d.yr == y]
        dd = (sy / sy.cummax() - 1) * 100
        uw = (sy < sy.cummax()).groupby((sy >= sy.cummax()).cumsum()).sum()
        qr = quarterly(sy)
        sm = dy.loc[dy.status == "STOP_MARKET_DONE", "profit"]
        sl = dy.loc[dy.status == "STOP_LOSS_DONE", "profit"]
        out[int(y)] = dict(
            n=int(len(dy)),
            win=100.0 * (dy.profit > 0).mean() if len(dy) else float("nan"),
            tsloss=100.0 * (dy.status == "STOP_LOSS_DONE").mean() if len(dy) else float("nan"),
            mp_sm=float(sm.mean()) if len(sm) else float("nan"),
            mp_sl=float(sl.mean()) if len(sl) else float("nan"),
            meanP=float(dy.profit.mean()) if len(dy) else float("nan"),
            pnl_usdt=float(dy["pnl"].sum()) if len(dy) else 0.0,
            ret=float(sy.iloc[-1] / sy.iloc[0] - 1) * 100,
            maxDD=float(dd.min()),
            uw=int(uw.max()) if len(uw) else 0,
            qmin=min(qr.values()) if qr else float("nan"),
            eq_end=float(sy.iloc[-1]),
        )
    return out


def bigmove(t, lv):
    if t is None:
        return None
    g = t.loc[t.peakPct >= lv * 100.0]
    if len(g) == 0:
        return dict(n=0)
    st = g.status.value_counts(normalize=True) * 100.0
    return dict(
        n=int(len(g)), pct_trailing=float(st.get("STOP_MARKET_DONE", 0.0)),
        med_gap_pp=float((g.peakPct - g.ratePct).median()),
        mean_gap_pp=float((g.peakPct - g.ratePct).mean()),
        med_capture=float((g.ratePct / g.peakPct).median()),
        mean_capture=float((g.ratePct / g.peakPct).mean()),
        sumPnL=float(g.pnl.sum()),
    )


def main():
    pos, k, jout, par = [], 3, None, "gx-par1"
    i = 1
    while i < len(sys.argv):
        a = sys.argv[i]
        if a == "--k":
            k = int(sys.argv[i + 1]); i += 2; continue
        if a == "--json":
            jout = sys.argv[i + 1]; i += 2; continue
        if a == "--par":
            par = sys.argv[i + 1]; i += 2; continue
        if a.startswith("--"):
            i += 1; continue
        pos.append(a); i += 1
    argv = pos
    W_STD = C.inflate(k)

    print("=== GD92 x EXIT SCORE — parity=%s | k=%d | inflate(k)=%.6f | legacy=%.2f" % (
        par, k, W_STD, LEGACY))
    print("    CI block-%dh, %d rep, seed %d, anchor %s. 'NGOAI CI' = ngoai o CA HAI do rong." % (
        BLOCK_H, NREP, SEED, ANCHOR.date()))

    D = {t: trades(t) for t in argv}
    S = {t: summary(t) for t in argv}
    Y = {t: yearly_detail(t) for t in argv}
    T = {t: trace(t) for t in argv}
    for t in argv:
        print("    trace[%s] = %s dong (%s)" % (
            t, "KHONG CO" if T[t] is None else len(T[t]), base(t)))

    print("\n=== (a) 5 RATE CHAT LUONG toan bo leg (printDone.csv) ===")
    print("%-10s %6s %8s %8s %10s %10s %10s" % ("tag", "n", "win%", "TSloss%", "mP|SM", "mP|SL", "meanP"))
    for t in argv:
        d = D[t]
        sm = d.loc[d.status == "STOP_MARKET_DONE", "profit"]
        sl = d.loc[d.status == "STOP_LOSS_DONE", "profit"]
        print("%-10s %6d %8.2f %8.2f %10.3f %10.3f %10.3f" % (
            t, len(d), 100.0 * (d.profit > 0).mean(),
            100.0 * (d.status == "STOP_LOSS_DONE").mean(),
            sm.mean() if len(sm) else float("nan"),
            sl.mean() if len(sl) else float("nan"), d.profit.mean()))

    res = {"k": k, "inflate_k": W_STD, "legacy": LEGACY, "summary": S, "yearly": Y, "ci": {}}

    print("\n=== (a2) CI cua hieu (chan - parity), CA HAI do rong block-72h ===")
    variants = [t for t in argv if t != par]
    for v in variants:
        c1 = ci_pair(v, par, LEGACY)
        c2 = ci_pair(v, par, W_STD)
        n_good = n_bad = 0
        print("  -- %s (-%s) --" % (v, par))
        print("  %-9s %11s %24s %28s %5s %5s %5s" % (
            "rate", "hieu", "CI @1.21", "CI @%.4f" % W_STD, "outL", "outS", "HUONG"))
        det = {}
        for name, dirc in RATES:
            obs = c1[name][0]
            lo1, hi1, o1 = c1[name][1], c1[name][2], c1[name][3]
            lo2, hi2, o2 = c2[name][1], c2[name][2], c2[name][3]
            out = o1 and o2
            good = out and ((dirc > 0 and obs > 0) or (dirc < 0 and obs < 0))
            bad = out and not good
            n_good += int(good); n_bad += int(bad)
            det[name] = dict(obs=obs, lo=lo2, hi=hi2, out_both=bool(out), good=bool(good), bad=bool(bad))
            print("  %-9s %+11.3f [%9.3f,%9.3f] [%9.3f,%9.3f] %5s %5s %5s" % (
                name, obs, lo1, hi1, lo2, hi2, "Y" if o1 else "-", "Y" if o2 else "-",
                "TOT" if good else ("XAU" if bad else "-")))
        res["ci"][v] = det
        print("  >>> %s: rate ngoai CI CA HAI do rong CUNG HUONG TOT = %d/5 | XAU = %d/5" % (
            v, n_good, n_bad))

    print("\n=== (b) RAO CUNG RISK_APPETITE (maxDD<=%.0f%%/nam VA toan ky, UW<=%d, quy>=%.0f%%, ko nam am, conc<=%.0f%%) ===" % (
        DD_MAX, UW_MAX, Q_MIN, CONC_MAX))
    print("%-10s %10s %7s %8s %6s %8s %8s %7s %7s %6s %8s" % (
        "tag", "equity", "CAGR%", "maxDD%", "UW", "qmin%", "conc%", "n", "hold_h", "turn", "SumPnL"))
    for t in argv:
        s = S[t]
        print("%-10s %10.0f %7.2f %8.2f %6d %8.2f %8.2f %7d %7.1f %6.3f %8.0f" % (
            t, s["end"], s["cagr"], s["maxDD"], s["uw"], s["qmin"], s["conc"],
            s["n"], s["hold_med"], s["turn"], s["sumpnl"]))
    print("\n  RAO CUNG THEO NAM (PASS/FAIL tung nam):")
    print("  %-10s %s" % ("tag", " ".join("%-26d" % y for y in sorted({y for t in argv for y in Y[t]}))))
    for t in argv:
        cells = []
        for y in sorted(Y[t]):
            r = Y[t][y]
            ok = (r["maxDD"] >= -DD_MAX and r["uw"] <= UW_MAX and r["qmin"] >= Q_MIN and r["ret"] >= 0)
            cells.append("%7.2f/%4d/%+7.2f %s" % (r["maxDD"], r["uw"], r["ret"], "P" if ok else "F"))
        print("  %-10s %s" % (t, " ".join("%-26s" % c for c in cells)))
    print("\n  RAO CUNG TOAN KY (rào cung theo NAM o tren KHONG du — bai hoc GD92):")
    for t in argv:
        s = S[t]
        bad = []
        if s["maxDD"] < -DD_MAX:
            bad.append("maxDD %.2f" % s["maxDD"])
        if s["uw"] > UW_MAX:
            bad.append("UW %d" % s["uw"])
        if s["qmin"] < Q_MIN:
            bad.append("qmin %.2f" % s["qmin"])
        if s["conc"] > CONC_MAX:
            bad.append("conc %.2f" % s["conc"])
        neg = [y for y, r in Y[t].items() if r["ret"] < 0]
        if neg:
            bad.append("nam am %s" % neg)
        print("  %-10s %s" % (t, "PASS" if not bad else "FAIL (" + ", ".join(bad) + ")"))

    print("\n*** (b2) BANG PnL CHI TIET THEO NAM ***")
    for t in argv:
        s = S[t]
        print("\n  == %s == equity cuoi %s = %.0f | toan ky: maxDD %.2f%% UW %d qmin %.2f conc %.2f SumPnL %.0f" % (
            t, s["last"], s["end"], s["maxDD"], s["uw"], s["qmin"], s["conc"], s["sumpnl"]))
        print("  %-5s %6s %8s %8s %9s %12s %9s %9s %5s %8s %11s %5s" % (
            "nam", "n", "win%", "TSloss%", "meanP", "PnL(USDT)", "ret%", "maxDD%", "UW", "qmin%",
            "equity", "P/F"))
        for y in sorted(Y[t]):
            r = Y[t][y]
            ok = (r["maxDD"] >= -DD_MAX and r["uw"] <= UW_MAX and r["qmin"] >= Q_MIN and r["ret"] >= 0)
            print("  %-5d %6d %8.2f %8.2f %9.3f %12.0f %+9.2f %9.2f %5d %8.2f %11.0f %5s" % (
                y, r["n"], r["win"], r["tsloss"], r["meanP"], r["pnl_usdt"], r["ret"],
                r["maxDD"], r["uw"], r["qmin"], r["eq_end"], "P" if ok else "F"))

    print("\n=== (c) BAT SONG LON (peak >= 20/50/100%) tu trailTrace.csv ===")
    for lv in PEAK_LEVELS:
        print("\n  -- peak >= +%d%% --" % int(lv * 100))
        print("  %-10s %6s %11s %11s %12s %11s %12s" % (
            "tag", "n", "%trailing", "med_gap_pp", "med_capture", "mean_capture", "SumPnL"))
        for t in argv:
            r = bigmove(T[t], lv)
            if r is None or r.get("n", 0) == 0:
                print("  %-10s %6s" % (t, "KHONG CO TRACE" if r is None else 0))
                continue
            print("  %-10s %6d %11.1f %11.2f %12.3f %11.3f %12.1f" % (
                t, r["n"], r["pct_trailing"], r["med_gap_pp"], r["med_capture"],
                r["mean_capture"], r["sumPnL"]))
        res.setdefault("bigmove", {})["%d" % int(lv * 100)] = {
            t: bigmove(T[t], lv) for t in argv}

    if jout:
        with open(jout, "w") as f:
            json.dump(res, f, indent=1, default=str)
        print("\n[json] %s" % jout)


if __name__ == "__main__":
    main()
