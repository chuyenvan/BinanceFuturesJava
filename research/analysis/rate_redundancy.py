#!/usr/bin/env python3
"""RATE_REDUNDANCY — kiem trung lap thang do tang B + test rao moi (a)/(b).

Thuc thi docs/prereg/PREREG_RATE_REDUNDANCY.md (chot truoc, commit 330811a).
THUAN PYTHON OFFLINE tren printDone.csv DA CO. KHONG chay sim/Java, khong train,
khong cham 242/ONNX/LIVE, khong push. DEV only <= 2025-12-31.

Usage: python3 rate_redundancy.py [--json docs/result/RATE_REDUNDANCY.json]
"""
import json
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

KOUT = "/home/ubuntu/kaggle_sim/out"
DEVRUN = "/home/ubuntu/java/devrun"
DEV_END = pd.Timestamp("2025-12-31 23:59")
NMIN = 30
RATE0 = ["n", "win", "tsloss", "mp_sm", "mp_sl", "meanP", "margin"]
LBL = {"n": "n", "win": "win%", "tsloss": "TSloss%", "mp_sm": "mP|SM",
       "mp_sl": "mP|SL", "meanP": "meanP", "margin": "mMargin"}

# doi tuong do rao (chot truoc §5)
TARGETS = [
    ("KEEPLEG0", os.path.join(KOUT, "gr-par-kg0")),
    ("T100", os.path.join(KOUT, "hn-t100")),
    ("GD92", os.path.join(KOUT, "hn-g92")),
    ("kg0-q995", os.path.join(KOUT, "gr-kg0-q995")),
    ("kg0-q998", os.path.join(KOUT, "gr-kg0-q998")),
    ("kg0-q999", os.path.join(KOUT, "gr-kg0-q999")),
    ("T170", os.path.join(KOUT, "t170-x1-2021")),
    ("kg0-q998-15m", os.path.join(KOUT, "gr-kg0-q998-15m")),
]
OPT = ["sel15", "sel15-q998", "sel15-q999", "all15"]
NEED = ("sym", "status", "profit", "pnl", "margin", "start", "end")


def load(path):
    p = os.path.join(path, "storage", "printDone.csv")
    if not os.path.exists(p):
        return None
    try:
        d = pd.read_csv(p, on_bad_lines="skip")
    except Exception:
        return None
    d.columns = [c.strip() for c in d.columns]
    if any(c not in d.columns for c in NEED):
        return None
    for c in ("profit", "pnl", "margin"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["ts"] = pd.to_datetime(d["start"].astype(str), format="%Y%m%d %H:%M", errors="coerce")
    d["te"] = pd.to_datetime(d["end"].astype(str), format="%Y%m%d %H:%M", errors="coerce")
    d = d.dropna(subset=["ts", "profit", "pnl", "margin"]).copy()
    n0 = len(d)
    d = d[d.ts <= DEV_END].copy()
    return d, n0 - len(d)


def rates_of(d):
    """7 rate tang B (dung chung dinh nghia c3_rates.rates) + phu tro H1/H5."""
    r = C.rates(d)
    sm = d.status == "STOP_MARKET_DONE"
    sl = d.status == "STOP_LOSS_DONE"
    r["n_sm"] = int(sm.sum())
    r["n_sl"] = int(sl.sum())
    r["n_other"] = int((~sm & ~sl).sum())
    r["n_profit_pos"] = int((d.profit > 0).sum())
    r["n_pnl_pos"] = int((d.pnl > 0).sum())
    r["sum_profit"] = float(d.profit.sum())
    r["sum_pnl"] = float(d.pnl.sum())
    r["mp_sm_pnl"] = float(d.loc[sm, "pnl"].mean()) if sm.any() else float("nan")
    r["mp_sl_pnl"] = float(d.loc[sl, "pnl"].mean()) if sl.any() else float("nan")
    r["meanPnl"] = float(d.pnl.mean())
    return r


# ---------------------------------------------------------------- H1-H5
def ident_checks(tags, R):
    """Tra ve bang sai so tung dong nhat thuc ung vien tren mo i run."""
    rows = []
    for t in tags:
        r = R[t]
        n = r["n"]
        # H1: status chi 2 gia tri
        h1 = r["n_other"]
        # H2: win% == 100 - TSloss%
        h2 = abs(r["win"] - (100.0 - r["tsloss"]))
        # H3: meanP == (1-tsloss/100)*mp_sm + (tsloss/100)*mp_sl
        if np.isfinite(r["mp_sm"]) and np.isfinite(r["mp_sl"]):
            p_sl = r["tsloss"] / 100.0
            h3 = abs(r["meanP"] - ((1 - p_sl) * r["mp_sm"] + p_sl * r["mp_sl"]))
        else:
            h3 = float("nan")
        # H5: n_sm + n_sl == n
        h5 = abs(r["n_sm"] + r["n_sl"] - n)
        rows.append(dict(tag=t, n=n, h1_n_other=h1, h2_gap_pp=h2, h3_gap=h3,
                         h5_gap=h5,
                         gap_win_pos=abs(r["win"] - 100.0 * r["n_profit_pos"] / n),
                         n_profit_pos=r["n_profit_pos"], n_sm=r["n_sm"]))
    return pd.DataFrame(rows)


def corr_block(lab, D, out):
    """Ma tran Pearson + Spearman cho 6 rate (bo 'n') tren bang D (moi dong = 1 quan sat)."""
    cols = [c for c in RATE0 if c != "n"]
    X = D[cols].apply(pd.to_numeric, errors="coerce")
    # bo cot hang so / toan nan
    cols = [c for c in cols if X[c].notna().sum() >= max(6, int(0.5 * len(X))) and X[c].std() > 0]
    X = X[cols]
    pe = X.corr(method="pearson")
    sp = X.corr(method="spearman")
    n = len(X)
    pairs = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            a, b = cols[i], cols[j]
            pev, spv = float(pe.loc[a, b]), float(sp.loc[a, b])
            pairs.append(dict(a=LBL[a], b=LBL[b], pearson=round(pev, 4),
                              spearman=round(spv, 4), n=n,
                              ge90=bool(abs(pev) >= 0.9 and abs(spv) >= 0.9),
                              ge99=bool(abs(pev) >= 0.99 and abs(spv) >= 0.99)))
    out[lab] = dict(n_obs=n, cols=[LBL[c] for c in cols], pairs=pairs)
    return pe, sp


def money_rulers(d):
    """Rao (a) share top-1% + rao (b) tail-free bo 5/10/20% (tren cot pnl USDT)."""
    P = d["pnl"].to_numpy(float)
    tot = P.sum()
    n = len(P)
    o = np.sort(P)[::-1]
    res = dict(n=n, sum_pnl=float(tot), sum_profit=float(d["profit"].sum()))

    def tf(q):
        k = max(1, int(math.ceil(q * n)))
        return dict(k=k, tail_sum=float(o[k:].sum()),
                    dropped=float(o[:k].sum()),
                    pct_of_total=float(o[k:].sum() / tot * 100) if tot else float("nan"))

    k1 = max(1, int(math.ceil(0.01 * n)))
    res["share_top1_pct"] = float(o[:k1].sum() / tot * 100) if tot else float("nan")
    res["share_top5_pct"] = float(o[:max(1, int(math.ceil(.05 * n)))].sum() / tot * 100) if tot else float("nan")
    res["top1_usdt"] = float(o[:k1].sum())
    for q in (0.05, 0.10, 0.20):
        res["tf%d" % int(q * 100)] = tf(q)
    res["pass_a"] = bool(res["share_top1_pct"] <= 15.0)
    res["pass_b20"] = bool(res["tf20"]["tail_sum"] > 0)
    # q* = ty le bo-top NHO NHAT (buoc 0,5%) lam tail-free sum <= 0
    qs = np.arange(0.005, 0.5055, 0.005)
    qs_ = None
    for q in qs:
        if o[max(1, int(math.ceil(q * n))):].sum() <= 0:
            qs_ = float(q)
            break
    res["q_breakeven"] = qs_
    # kiem do nhay: do tren cot `profit` (% gia) thay vi `pnl` (USDT)
    G = d["profit"].to_numpy(float)
    gt = G.sum()
    go = np.sort(G)[::-1]
    if gt:
        res["share_top1_pct_profit"] = float(go[:k1].sum() / gt * 100)
        res["tf20_profit"] = float(go[max(1, int(math.ceil(.20 * n))):].sum())
        res["pass_a_profit"] = bool(res["share_top1_pct_profit"] <= 15.0)
        res["pass_b20_profit"] = bool(res["tf20_profit"] > 0)
    return res


def main():
    ap = sys.argv[1:]
    jout = "docs/result/RATE_REDUNDANCY.json"
    if "--json" in ap:
        jout = ap[ap.index("--json") + 1]
    tmp = "/tmp/rr"
    os.makedirs(tmp, exist_ok=True)

    # ---- discover runs
    runs = {}
    skipped = dict(no_csv=0, bad_cols=0, too_small=0)
    for root in (KOUT, DEVRUN):
        if not os.path.isdir(root):
            continue
        for tag in sorted(os.listdir(root)):
            p = os.path.join(root, tag)
            if not os.path.isdir(p):
                continue
            got = load(p)
            if got is None:
                skipped["no_csv"] += 1
                continue
            d, ncut = got
            if len(d) < NMIN:
                skipped["too_small"] += 1
                continue
            runs[tag] = dict(path=p, dir=os.path.basename(root), d=d, ncut=ncut)
    print("runs eligible:", len(runs), "skipped:", skipped, file=sys.stderr)

    R = {t: rates_of(v["d"]) for t, v in runs.items()}
    meta = {t: dict(dir=v["dir"], n_cut_2026=v["ncut"]) for t, v in runs.items()}

    # ---- H1-H5
    IC = ident_checks(list(runs), R)
    IC.to_csv(os.path.join(tmp, "ident.csv"), index=False)

    # ---- Panel A: run-level rates
    cols = RATE0
    A = pd.DataFrame({t: {c: R[t][c] for c in cols} for t in runs}).T
    A.index.name = "tag"
    A["dir"] = [meta[t]["dir"] for t in A.index]
    A.to_csv(os.path.join(tmp, "panelA.csv"))

    A_big = A[A["n"] >= 200]

    # ---- Panel B: run x year
    rowsB = []
    for t, v in runs.items():
        d = v["d"].copy()
        d["yr"] = d["te"].dt.year
        for y, g in d.groupby("yr"):
            if len(g) < NMIN:
                continue
            r = rates_of(g)
            r["tag"] = t
            r["yr"] = int(y)
            rowsB.append(r)
    B = pd.DataFrame(rowsB)
    B.to_csv(os.path.join(tmp, "panelB.csv"), index=False)

    out = dict(prereg="docs/prereg/PREREG_RATE_REDUNDANCY.md",
               n_runs=len(runs), skipped=skipped,
               n_panelB=len(B), n_panelA_big=len(A_big),
               tags=sorted(runs), meta=meta)
    corr = {}
    corr_block("A_all_runs", A, corr)
    corr_block("A_runs_n_ge200", A_big, corr)
    corr_block("B_run_year", B, corr)
    out["corr"] = {}
    for lab, v in corr.items():
        out["corr"][lab] = dict(n_obs=v["n_obs"],
                                ge90=[p for p in v["pairs"] if p["ge90"]],
                                ge99=[p for p in v["pairs"] if p["ge99"]],
                                all_pairs=v["pairs"])

    # ---- H1-H5 verdicts
    h2 = IC["h2_gap_pp"]
    h3 = IC["h3_gap"].dropna()
    zero_other = IC[IC["h1_n_other"] == 0]
    cond_h3 = zero_other["h3_gap"].dropna()
    out["ident"] = dict(
        n_runs=len(IC),
        h1_max_n_other=int(IC["h1_n_other"].max()),
        h1_n_runs_with_other=int((IC["h1_n_other"] > 0).sum()),
        h2_max_gap_pp=float(h2.max()), h2_med_gap_pp=float(h2.median()),
        h2_frac_le_1e4_pp=float((h2 <= 1e-2).mean()),  # 1e-4 tuong doi -> pp
        h2_frac_le_1e6_pp=float((h2 <= 1e-4).mean()),
        h3_max_gap=float(h3.max()), h3_med_gap=float(h3.median()),
        h3_frac_le_1e6=float((h3 <= 1e-6).mean()),
        h5_max_gap=float(IC["h5_gap"].max()),
        n_runs_n_other0=int(len(zero_other)),
        h3_frac_le_1e6_if_nother0=float((cond_h3 <= 1e-6).mean()) if len(cond_h3) else float("nan"),
    )
    # ---- khoi PHU (thăm dò, KHONG thuoc luat chot truoc): chi run n_other=0
    out["corr_sub"] = {}
    A0 = A[A.index.isin(zero_other.tag)]
    corr_block("A_runs_n_other0", A0, out["corr_sub"])
    B0 = B[B.tag.isin(zero_other.tag)]
    corr_block("B_run_year_n_other0", B0, out["corr_sub"])
    # ---- khoi PHU: trong-run (tru trung binh theo run) tren o run x nam
    Bx = B[[c for c in RATE0 if c != "n"] + ["tag"]].copy()
    for c in RATE0:
        if c == "n":
            continue
        Bx[c] = Bx[c] - Bx.groupby("tag")[c].transform("mean")
    corr_block("B_within_run_demeaned", Bx, out["corr_sub"])

    # ---- VIEC 4: rao (a)/(b)
    rut = {}
    for name, path in TARGETS:
        d = runs.get(os.path.basename(path), {}).get("d")
        if d is None:
            # co the tag nam o devrun
            for t, v in runs.items():
                if v["path"] == path:
                    d = v["d"]
                    break
        if d is None:
            rut[name] = dict(missing=True, path=path)
            continue
        full = money_rulers(d)
        yrs = {}
        dd = d.copy()
        dd["yr"] = dd["te"].dt.year
        for y, g in dd.groupby("yr"):
            if len(g) < 5:
                yrs[int(y)] = dict(n=len(g), insufficient=True)
                continue
            yrs[int(y)] = money_rulers(g)
        rut[name] = dict(path=path, full=full, years=yrs,
                         n_cut_2026=int(d["ts"].gt(DEV_END).sum()))
    # optional sel15*
    opt = {}
    for nm in OPT:
        hit = None
        for t, v in runs.items():
            if nm in t:
                hit = (t, v)
                break
        if hit:
            opt[nm] = dict(tag=hit[0], **money_rulers(hit[1]["d"]))
    out["rao"] = rut
    out["rao_optional"] = opt

    with open(jout, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("wrote", jout, os.path.getsize(jout), "bytes", file=sys.stderr)


if __name__ == "__main__":
    main()
