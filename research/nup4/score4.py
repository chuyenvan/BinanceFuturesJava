#!/usr/bin/env python3
"""NUP4 scorer (PREREG_NUP4 feac2d5e). Doc printDone + leg_owner.csv + merge_log.csv + equity_day/summary.

Ky DEV = 2022-01-01..2025-12-31 (giao dich dong theo gio +07, nhu NUP3).
Ky HO 2026 = 2026-01-01..2026-09-30.
Khong doc gia ngoai: maxDD lay tu sim (equity_summary.json, MTM @bar.low) va equity_day.csv.

  python3 score4.py runs     # bang tung run
  python3 score4.py gates    # cham G1-G5
"""
import hashlib
import io
import json
import os
import sys

import numpy as np
import pandas as pd

KS = "/home/ubuntu/kaggle_sim/out/%s/"
W = "/home/ubuntu/claude_master/nup4_wk"
OUTD = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/nup4"
os.makedirs(OUTD, exist_ok=True)
DEV_A, DEV_B = pd.Timestamp("2022-01-01"), pd.Timestamp("2026-01-01")
HO_A, HO_B = pd.Timestamp("2026-01-01"), pd.Timestamp("2026-10-01")
YEARS = [2022, 2023, 2024, 2025]
SEED_NAME = {42: "a1", 7: "s7", 13: "s13", 21: "s21", 99: "s99", 123: "s123", 777: "s777", 2024: "s2024"}
ARMS = ["b0union", "s1b", "m1a", "m1b", "m2a", "m2b", "m3a", "m3b"]
P1 = [42, 7, 21, 99]
CAP0 = 35000.0
SB = b"book=sleeve"


def tag(a, s):
    return "n4b-%s-%s" % (a, SEED_NAME[s])


def split_run(t):
    raw = open(KS % t + "storage/printDone.csv", "rb").read()
    lines = raw.splitlines(keepends=True)
    hdr, body = lines[0], lines[1:]
    isS = [ln.rstrip(b"\r\n").split(b",")[-1] == SB for ln in body]
    base = [ln for ln, s in zip(body, isS) if not s]
    slv = [ln for ln, s in zip(body, isS) if s]
    return hdr, base, slv


def parse(blob, book, owner_default):
    d = pd.read_csv(io.BytesIO(blob), index_col=False)
    d.columns = [c.strip() for c in d.columns]
    for c in ("quantity", "entry", "tp", "pnl", "margin", "funding"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["pnl", "quantity", "entry", "margin"]).copy()
    d["sym"] = d["sym"].astype(str).str.strip()
    d["ts"] = pd.to_datetime(d["start"].astype(str).str.strip(), format="%Y%m%d %H:%M")
    d["te"] = pd.to_datetime(d["end"].astype(str).str.strip(), format="%Y%m%d %H:%M")
    d["notional"] = d["quantity"] * d["entry"]
    d["book"] = book
    d["owner"] = owner_default
    return d.reset_index(drop=True)


def owners_of(t):
    p = KS % t + "storage/leg_owner.csv"
    if not os.path.exists(p):
        return {}
    d = pd.read_csv(p)
    d.columns = [c.strip() for c in d.columns]
    return {(str(r.sym).strip(), int(r.tOpen)): str(r.owner).strip() for r in d.itertuples()}


def load(t):
    hdr, base, slv = split_run(t)
    B = parse(hdr + b"".join(base), "B", "B")
    S = parse(hdr + b"".join(slv), "S", "S")
    own = owners_of(t)
    if own:
        for d in (B, S):
            d["owner"] = [own.get((r.sym, int(r.ts.value // 10 ** 6)), r.owner) for r in d.itertuples()]
    d = pd.concat([B, S], ignore_index=True)
    d["cl"] = d["book"] + "|" + d["sym"] + "|" + d["start"].astype(str)
    return d


def stress(x):
    return float((x["pnl"] - 0.002 * x["notional"]).sum())


def win(d, a, b):
    return d[(d["te"] >= a) & (d["te"] < b)]


def clusters(x):
    g = x.groupby("cl", sort=False)
    return pd.DataFrame({"sym": g["sym"].first(), "ts": g["ts"].min(), "te": g["te"].max(),
                         "pnl": g["pnl"].sum(), "notional": g["notional"].sum(), "book": g["book"].first()})


def equity_day(t):
    p = KS % t + "storage/equity_day.csv"
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p)
    d["t"] = pd.to_datetime(d["tMs"], unit="ms", utc=False) + pd.Timedelta(hours=7)
    return d


def dd_window(t, a, b):
    """maxDD (%) trong [a,b). Uu tien maxDD CHINH XAC cua sim neu moc nam trong cua so; khong thi chuoi NGAY."""
    e = equity_day(t)
    p = KS % t + "storage/equity_summary.json"
    if not os.path.exists(p):
        return dict(dd=np.nan, dd_t=None, src="missing")
    s = json.load(open(p))
    try:
        ts = pd.Timestamp(s["maxdd_t"])          # 'yyyyMMddHHmm' (UTC)
        if a <= ts < b:
            return dict(dd=float(s["maxdd_mtm_low_pct"]) * 100, dd_t=s["maxdd_t"], src="sim-exact")
    except Exception:  # noqa: BLE001
        pass
    if e is None:
        return dict(dd=float(s["maxdd_mtm_low_pct"]) * 100, dd_t=s["maxdd_t"], src="sim-full")
    e = e[(e["t"] >= a) & (e["t"] < b)].reset_index(drop=True)
    if len(e) == 0:
        return dict(dd=np.nan, dd_t=None, src="empty")
    peak, mdd, mt = -np.inf, 0.0, None
    for r in e.itertuples():
        peak = max(peak, r.eq_low)
        q = (peak - r.eq_low) / peak if peak > 0 else 0.0
        if q > mdd:
            mdd, mt = q, r.t
    return dict(dd=-100 * mdd, dd_t=str(mt), src="day-low")


def cagr(t, a, b):
    e = equity_day(t)
    if e is None:
        return np.nan
    e = e[(e["t"] >= a) & (e["t"] < b)]
    if len(e) < 10:
        return np.nan
    x = e["eq_close"].to_numpy(float)
    yrs = (b - a).days / 365.25
    return 100 * ((x[-1] / x[0]) ** (1 / yrs) - 1)


def stats(t):
    d = load(t)
    dv = win(d, DEV_A, DEV_B)
    cD = clusters(dv)
    ho = win(d, HO_A, HO_B)
    cH = clusters(ho)
    out = dict(tag=t, n_leg=len(dv), n_cl=len(cD),
               pnl=float(dv["pnl"].sum()), stress=stress(dv),
               cagr22=cagr(t, DEV_A, DEV_B),
               dd_dev=dd_window(t, DEV_A, DEV_B),
               dd_2026=dd_window(t, HO_A, HO_B),
               n_cl_2026=len(cH), pnl_2026=float(ho["pnl"].sum()))
    yr = {}
    for y in YEARS:
        a, b = pd.Timestamp("%d-01-01" % y), pd.Timestamp("%d-01-01" % (y + 1))
        s = win(dv, a, b)
        cy = clusters(s)
        yr[str(y)] = dict(n_cl=int(len(cy)), pnl=float(s["pnl"].sum()), stress=stress(s))
    out["yr"] = yr
    # sleeve rieng
    sl = dv[dv["book"] == "S"]
    cS = clusters(sl)
    syp = {}
    for y in YEARS:
        a, b = pd.Timestamp("%d-01-01" % y), pd.Timestamp("%d-01-01" % (y + 1))
        sy = win(sl, a, b)
        syp[str(y)] = dict(n_cl=int(len(clusters(sy))), stress=stress(sy), pnl=float(sy["pnl"].sum()))
    out["sl"] = dict(n_cl=int(len(cS)), pnl=float(sl["pnl"].sum()), stress=stress(sl),
                     roi=100 * float(sl["pnl"].sum()) / float(sl["notional"].sum()) if len(sl) else np.nan,
                     roi_stress=100 * stress(sl) / float(sl["notional"].sum()) if len(sl) else np.nan,
                     yr=syp)
    # phan NEN theo owner (M*). Funding cua cum duoc chia pro-rata notional (PREREG_NUP4 §3):
    #   pnl_ex_fund = pnl + funding_leg; owner -= share funding cua cum theo notional.
    fo = dv.copy()
    fo["pnl_ex"] = fo["pnl"] + fo["funding"].fillna(0.0)
    g = fo.groupby("cl", sort=False)
    fo["fund_cl"] = g["funding"].transform("sum")
    fo["ns"] = g["notional"].transform("sum")
    fo["pnl_own"] = fo["pnl_ex"] - fo["fund_cl"] * fo["notional"] / fo["ns"].replace(0, np.nan).fillna(1.0)
    bs = fo[fo["owner"] == "B"]
    out["base_owner_pnl"] = float(bs["pnl_own"].sum())
    out["sleeve_owner_pnl"] = float(fo[fo["owner"] == "S"]["pnl_own"].sum())
    out["n_owner_B"] = int(len(bs))
    out["n_owner_S"] = int(len(fo[fo["owner"] == "S"]))
    out["n_owner_B"] = int(len(bs))
    out["n_owner_S"] = int(len(dv[dv["owner"] == "S"]))
    # 2026 sleeve
    hs = ho[ho["book"] == "S"]
    out["sl_2026"] = dict(n_cl=int(len(clusters(hs))), pnl=float(hs["pnl"].sum()), stress=stress(hs),
                          roi_stress=100 * stress(hs) / float(hs["notional"].sum()) if len(hs) else np.nan)
    p = KS % t + "storage/merge_log.csv"
    out["merges"] = int(len(pd.read_csv(p)) - 0) if os.path.exists(p) else 0
    p = KS % t + "storage/sleeve_summary.json"
    if os.path.exists(p):
        sm = json.load(open(p))
        out["sim"] = {k: sm.get(k) for k in ("u_total_max", "u_total_margin_max", "max_pos_total", "overlap_base_opens_sleeve_sym",
                                             "merge_mode", "merge_count", "merge_m3_ticks", "skip_held_base", "skip_held_sleeve")}
    return out


def b0_refs(seeds):
    """B0 tham chieu theo ky: DEV = tsx-x14-<seed>, 2026 = nt-x14-s<seed>."""
    out = {}
    for s in seeds:
        nn = SEED_NAME[s]
        dev = stats_dev_only("tsx-x14-" + nn) if os.path.exists(KS % ("tsx-x14-" + nn) + "storage/printDone.csv") else None
        out[s] = dev
    return out


def stats_dev_only(t):
    d = parse(open(KS % t + "storage/printDone.csv", "rb").read(), "B", "B")
    dv = win(d, DEV_A, DEV_B)
    cD = clusters(dv)
    o = dict(tag=t, n_cl=len(cD), pnl=float(dv["pnl"].sum()), stress=stress(dv), yr={})
    for y in YEARS:
        a, b = pd.Timestamp("%d-01-01" % y), pd.Timestamp("%d-01-01" % (y + 1))
        s = win(dv, a, b)
        o["yr"][str(y)] = dict(n_cl=int(len(clusters(s))), pnl=float(s["pnl"].sum()), stress=stress(s))
    return o


def b0_2026(seeds):
    out = {}
    for s in seeds:
        t = "nt-x14-s%d" % s
        p = KS % t + "storage/printDone.csv"
        if not os.path.exists(p):
            continue
        d = parse(open(p, "rb").read(), "B", "B")
        ho = win(d, HO_A, HO_B)
        out[s] = dict(pnl=float(ho["pnl"].sum()), n_cl=int(len(clusters(ho))), stress=stress(ho),
                      dd=dd_window(t, HO_A, HO_B))
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "runs"
    rows = {}
    for a in ARMS:
        for s in P1 + [13, 123, 777, 2024]:
            t = tag(a, s)
            if not os.path.exists(KS % t + "storage/printDone.csv"):
                continue
            rows[t] = stats(t)
    b0 = {}
    for s in P1 + [13, 123, 777, 2024]:
        b0[s] = stats_dev_only("tsx-x14-" + SEED_NAME[s])
    b26 = b0_2026(P1 + [13, 123, 777, 2024])
    json.dump(dict(runs=rows, b0=b0, b0_2026=b26), open(W + "/scored.json", "w"), indent=1, default=str)
    if mode == "runs":
        for t, r in rows.items():
            s = [k for k, v in SEED_NAME.items() if v == t.split("-")[-1]][0]
            print("%-14s cl=%5d pnl=%9.0f xB0=%5.3f dd=%6.2f%% dd26=%6.2f%% sl_cl=%4d sl_pnl=%8.0f merges=%d" % (
                t, r["n_cl"], r["pnl"], r["pnl"] / b0[s]["pnl"], r["dd_dev"]["dd"], r["dd_2026"]["dd"],
                r["sl"]["n_cl"], r["sl"]["pnl"], r["merges"]))
    return rows, b0, b26


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------- gates
def _med(x):
    return float(np.nanmedian(x))


def gates(rows, b0, seeds):
    """Cham G1-G5 theo PREREG_NUP4 §5-6 (median seed; B0 DEV = tsx-x14-<seed>)."""
    res = {}
    for a in [x for x in ARMS if x != "b0union"]:
        ts = [tag(a, s) for s in seeds if tag(a, s) in rows]
        if len(ts) < 3:
            continue
        r = [rows[t] for t in ts]
        ss = [s for s in seeds if tag(a, s) in rows]
        xcl = [rows[tag(a, s)]["n_cl"] / b0[s]["n_cl"] for s in ss]
        xpnl = [rows[tag(a, s)]["pnl"] / b0[s]["pnl"] for s in ss]
        xyr = {str(y): _med([rows[tag(a, s)]["yr"][str(y)]["n_cl"] / b0[s]["yr"][str(y)]["n_cl"] for s in ss])
               for y in YEARS}
        dd = [rows[tag(a, s)]["dd_dev"]["dd"] for s in ss]
        u = [rows[tag(a, s)]["sim"]["u_total_max"] for s in ss if rows[tag(a, s)].get("sim")]
        slst = [rows[tag(a, s)]["sl"]["stress"] for s in ss]
        slyr = {str(y): _med([rows[tag(a, s)]["sl"]["yr"][str(y)]["stress"] for s in ss]) for y in YEARS}
        base_ratio = [rows[tag(a, s)]["base_owner_pnl"] / b0[s]["pnl"] for s in ss]
        g1 = _med(xcl) >= 1.30 and all(xyr[str(y)] >= 1.15 for y in YEARS)
        g2 = _med(xpnl) >= 1.00 and sum(1 for y in YEARS if slyr[str(y)] > 0) >= 3 and \
            sum(1 for v in slst if v > 0) >= (3 if len(ss) <= 4 else 6)
        g3 = _med(dd) >= -32.0 and min(dd) >= -36.0 and (not u or max(u) <= 1.0)
        g5 = _med(base_ratio) >= 0.97
        g4 = None
        if len(ss) >= 8:
            h = [rows[tag(a, s)]["sl_2026"] for s in ss]
            g4 = (sum(1 for x in h if x["stress"] > 0) >= 6 and _med([x["roi_stress"] for x in h]) >= 0.5
                  and _med([rows[tag(a, s)]["dd_2026"]["dd"] for s in ss]) >= -15.0)
        res[a] = dict(n_seed=len(ss), seeds=[SEED_NAME[s] for s in ss],
                      g1=bool(g1), g2=bool(g2), g3=bool(g3), g5=bool(g5), g4=g4,
                      xcl=_med(xcl), xpnl=_med(xpnl), xyr=xyr,
                      dd_med=_med(dd), dd_worst=min(dd), u_max=max(u) if u else None,
                      sl_stress_pos=sum(1 for v in slst if v > 0),
                      sl_yr=slyr, base_ratio=_med(base_ratio),
                      calmar=_med([rows[t]["cagr22"] / abs(rows[t]["dd_dev"]["dd"]) for t in ts
                                   if rows[t]["cagr22"] == rows[t]["cagr22"]]),
                      cagr22=_med([rows[t]["cagr22"] for t in ts]))
        res[a]["pass_all"] = bool(g1 and g2 and g3 and g5 and (g4 is not False))
    return res


def quarters_2026(rows):
    out = {}
    for t, r in rows.items():
        d = load(t)
        h = win(d, HO_A, HO_B)
        if not len(h):
            continue
        q = (h[["pnl", "notional", "cl"]].assign(q=h["te"].dt.quarter.values).groupby("q")
             .agg(pnl=("pnl", "sum"), n_cl=("cl", "nunique"), notional=("notional", "sum")))
        out[t] = {int(k): dict(pnl=float(v.pnl), n_cl=int(v.n_cl)) for k, v in q.iterrows()}
    return out
