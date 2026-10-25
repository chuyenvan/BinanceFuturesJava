#!/usr/bin/env python3
"""GOLIVE_QUARTERLY buoc B: bang chi so theo QUY (CHI MO TA, khong chon/tune) cho goi go-live v1.1
= crash-buy K24 + skipFull + TS_MKT_EXT X14 (shadow 242). Nguon DUY NHAT: printDone sim Java X14 8 seed da co
(DEV tsx-x14-{a1,s7,s13,s21,s99,s123,s777,s2024}; HO tsx-ho-x14-s{42,7,13,21,99,123,777,2024}) + equity MTM phut tu buoc A
(mtm_dev.py: gvz_mtm, mtm_ho.py: ecm_mtm_h; missing = 0 da assert o buoc A, assert lai o day).
Quy uoc: quy theo gio +07 (= gio printDone, = cua so W9 HO, = PER_DEV cua DEEP); truc MTM UTC = gio +07 - 7h.
Lenh/cum gan vao quy theo gio DONG (PnL thuc hien); dot vao theo phut anchor t0. Khong import pipeline cu (chi numpy/pandas).
Out: docs/result/golive_quarterly/{quarterly_x14.csv, quarterly_x14_by_seed.csv, summary.json, validate.json, tables.md}
"""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("gq")
REPO = "/home/ubuntu/claude_master/vz_e1_wt"
OUTD = REPO + "/docs/result/golive_quarterly"
WK = "/home/ubuntu/claude_master/golive_quarterly_wk"
KS = "/home/ubuntu/kaggle_sim/out/"
TSX = "/home/ubuntu/claude_master/tsx"
H7 = pd.Timedelta(hours=7)
MIN = pd.Timedelta(minutes=1)
TS_MIN = 168 * 60
CAP0 = 35000.0
DAY0 = pd.Timestamp("2021-07-01")  # truc UTC eq DEV (R.DAY0)
HO_L0 = pd.Timestamp("2026-01-01")  # local +07; truc eq HO bat dau 2025-12-31 17:00 UTC
DEV_SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
HO_SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
ST_SL, ST_TR = "STOP_LOSS_DONE", "STOP_MARKET_DONE"


def load(tag):
    d = pd.read_csv(KS + tag + "/storage/printDone.csv", index_col=False)
    d.columns = [c.strip() for c in d.columns]
    for c in ("quantity", "entry", "tp", "pnl", "profit", "funding", "margin"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    n0 = len(d)
    d = d.dropna(subset=["pnl", "quantity", "entry", "tp", "funding"]).copy()
    assert len(d) == n0, (tag, n0, len(d))
    d["sym"] = d["sym"].astype(str).str.strip()
    d["status"] = d["status"].astype(str).str.strip()
    d["ts"] = pd.to_datetime(d["start"].astype(str).str.strip(), format="%Y%m%d %H:%M")
    d["te"] = pd.to_datetime(d["end"].astype(str).str.strip(), format="%Y%m%d %H:%M")
    d["notional"] = d["quantity"] * d["entry"]
    d["fee"] = d["quantity"] * (d["tp"] - d["entry"]) - d["funding"] - d["pnl"]  # phi ngam (pnl = q(tp-e) - phi - funding)
    return d.sort_values(["ts", "sym"], kind="mergesort").reset_index(drop=True)


def clusters(d):
    """cum = (sym, te): cac leg DCA dong cung phut; t0 = leg dau (anchor)."""
    c = d.groupby(["sym", "te"], sort=False).agg(t0=("ts", "min"), st=("status", "first"), nst=("status", "nunique"),
                                                 n=("sym", "size"), pnl=("pnl", "sum"), notional=("notional", "sum")).reset_index()
    assert (c["nst"] == 1).all()
    c["age_min"] = (c["te"] - c["t0"]) // MIN
    c["mark_day"] = (c["t0"] - H7 + pd.Timedelta(minutes=TS_MIN + 1)).dt.normalize()  # ngay UTC cua tick tuoi > 168h
    return c


def deferred(c, c0, fl):
    """cum X14 duoc HOAN (= quy uoc DEEP/TSX_V3_JAVA): tuoi > 168h+1', moc 168h roi vao ngay co (UTC), tru cum da arm trailing
    truoc 168h (P0 cung sym+anchor giu > 168h ma khong bi cat SL)."""
    p0 = {}
    for s, t, a, st in zip(c0["sym"], c0["t0"], c0["age_min"], c0["st"]):
        p0.setdefault((s, t), bool(a > TS_MIN + 1 and st != ST_SL))
    cand = c[(c["age_min"] > TS_MIN + 1) & c["mark_day"].isin(fl)]
    return {(s, te) for s, t, te in zip(cand["sym"], cand["t0"], cand["te"]) if not p0.get((s, t), False)}


def flagset(rng):
    out = set()
    for r in rng.split(","):
        x, y = r.split("-")
        out |= set(pd.date_range(pd.Timestamp(x), pd.Timestamp(y), freq="D"))
    return out


def sweep(a, b, w, n):
    a, b = np.clip(a, 0, n), np.clip(b, 0, n)
    x = np.zeros(n + 1)
    np.add.at(x, a, w)
    np.add.at(x, b, -np.asarray(w, float) * np.ones(len(a)))
    return np.cumsum(x)[:n]


def ddx(e):
    pk = np.maximum.accumulate(e)
    return float(100 * (e / pk - 1.0).min())


def build(tag, p0tag, eq, ubase, fl, fix_off=None):
    """ubase = moc UTC cua eq[0]. Chi so phut i = (t_local - 7h - ubase) / 1'.
    fix_off (chi DEV): eq gvz/reset_rule_score.run_mtm BO SOT PnL cua leg dong DUNG 00:00 UTC suot ngay UTC do
    (_work_vision lay sub m1 > base nen leg m1 == base khong vao sp; prefix chi tinh te_day < day). Sua: cong pnl cua cac leg
    nay vao [m1, m1 + 1440). eq_leg = ban goc (= so cong bo), eq = ban da sua (dung cho bang)."""
    d, c = load(tag), None
    c = clusters(d)
    dset = deferred(c, clusters(load(p0tag)), fl)
    n = len(eq)

    def ix(s):
        return ((s - H7 - ubase) // MIN).to_numpy(np.int64)

    d["si"], d["ei"] = ix(d["ts"]), ix(d["te"])
    c["si"], c["ei"] = ix(c["t0"]), ix(c["te"])
    c["x14"] = [(s, t) in dset for s, t in zip(c["sym"], c["te"])]
    fixchk = {}
    eq_leg = eq
    if fix_off is not None:
        z = (((d["ei"] - fix_off) % 1440) == 0) & (d["ei"] >= 0) & (d["ei"] < n)
        cr = np.zeros(n + 1)
        np.add.at(cr, d.loc[z, "ei"].to_numpy(), d.loc[z, "pnl"].to_numpy(float))
        np.add.at(cr, np.minimum(d.loc[z, "ei"].to_numpy() + 1440, n), -d.loc[z, "pnl"].to_numpy(float))
        corr = np.cumsum(cr)[:n]
        eq = eq_leg + corr
        kz = set(zip(d.loc[z, "sym"], d.loc[z, "te"]))
        fixchk = dict(utc0_legs=int(z.sum()), utc0_days=int(d.loc[z, "ei"].nunique()), utc0_pnl=float(d.loc[z, "pnl"].sum()),
                      utc0_pnl_min=float(d.loc[z, "pnl"].min()) if z.any() else 0.0, corr_absmax=float(np.abs(corr).max()),
                      utc0_x14_clusters=int(sum(1 for k in kz if k in dset)), utc0_clusters=len(kz))
    on = sweep(d["si"].to_numpy(), d["ei"].to_numpy(), d["notional"].to_numpy(float), n)
    npos = sweep(c["si"].to_numpy(), c["ei"].to_numpy(), np.ones(len(c)), n)
    ok = (d["ei"] >= 0) & (d["ei"] < n)
    real = np.zeros(n)
    np.add.at(real, d.loc[ok, "ei"].to_numpy(), d.loc[ok, "pnl"].to_numpy(float))
    bal = CAP0 + float(d.loc[d["ei"] < 0, "pnl"].sum()) + np.cumsum(real)
    flat = npos < 0.5
    # kiem truc thoi gian: luc khong co vi the, equity MTM phai = so du thuc hien; lam lai voi truc SAI (khong tru 7h) de doi chung
    ew = ((d["te"] - ubase) // MIN).to_numpy(np.int64)
    okw = (ew >= 0) & (ew < n)
    rw = np.zeros(n)
    np.add.at(rw, ew[okw], d["pnl"].to_numpy(float)[okw])
    balw = CAP0 + float(d["pnl"].to_numpy(float)[ew < 0].sum()) + np.cumsum(rw)
    chk = dict(flat_maxabs=float(np.abs(eq[flat] - bal[flat]).max()), flat_minutes=int(flat.sum()),
               flat_maxabs_wrong_axis=float(np.abs(eq[flat] - balw[flat]).max()),
               flat_maxabs_legacy=float(np.abs(eq_leg[flat] - bal[flat]).max()),
               flat_minutes_bad_legacy=int((np.abs(eq_leg[flat] - bal[flat]) > 0.1).sum()), n_defer=len(dset),
               fee_over_notional_med=float((d["fee"] / d["notional"]).median()), **fixchk)
    return dict(tag=tag, d=d, c=c, eq=eq, eq_leg=eq_leg if fix_off is not None else None, ubase=ubase, on=on, npos=npos, n=n, chk=chk)


def metrics(r, A, B, kind, ph0, fl):
    ub, eq, d, c = r["ubase"], r["eq"], r["d"], r["c"]

    def ix(t):
        return int((pd.Timestamp(t) - H7 - ub) // MIN)

    i0, i1, p0 = ix(A), ix(B), ix(ph0)
    assert 0 <= p0 <= i0 < i1 <= r["n"], (r["tag"], A, B, i0, i1, r["n"])
    L = d[(d["ei"] >= i0) & (d["ei"] < i1)]
    K = c[(c["ei"] >= i0) & (c["ei"] < i1)]
    bal0 = CAP0 + float(d.loc[d["ei"] < i0, "pnl"].sum())
    pnl = float(L["pnl"].sum())
    roi = pnl / bal0
    nd = (pd.Timestamp(B) - pd.Timestamp(A)).days
    ann = (1 + roi) ** 4 - 1 if kind == "Q" else (1 + roi) ** (365.25 / nd) - 1
    s0 = max(i0 - 1, 0)
    seg = eq[s0:i1]
    ddq, ddc = ddx(seg), ddx(eq[max(p0 - 1, 0):i1])
    ret = seg[-1] / seg[0] - 1
    el = r.get("eq_leg")
    if el is not None:
        sl = el[s0:i1]
        leg = dict(dd_q_legacy=ddx(sl), dd_cum_legacy=ddx(el[max(p0 - 1, 0):i1]), ret_mtm_legacy=float(100 * (sl[-1] / sl[0] - 1)))
    else:
        leg = dict(dd_q_legacy=np.nan, dd_cum_legacy=np.nan, ret_mtm_legacy=np.nan)
    ex = r["on"][i0:i1] / eq[i0:i1]
    npo = r["npos"][i0:i1]
    assert (i1 - i0) % 1440 == 0
    flat_days = int((npo.reshape(-1, 1440).max(axis=1) < 0.5).sum())
    si = d.loc[(d["si"] >= i0) & (d["si"] < i1), "si"].to_numpy()
    noentry_days = int((np.bincount((si - i0) // 1440, minlength=nd) == 0).sum())
    x14 = K["x14"].to_numpy()
    ts168 = (~x14) & (K["st"] == ST_SL).to_numpy() & K["age_min"].between(TS_MIN - 1, TS_MIN + 2).to_numpy()
    trail = (~x14) & (K["st"] == ST_TR).to_numpy()
    fdays = sum(1 for x in fl if pd.Timestamp(A) <= x < pd.Timestamp(B))
    return dict(n_entry=int(c.loc[(c["si"] >= i0) & (c["si"] < i1), "t0"].nunique()), n_cl=int(len(K)), n_leg=int(len(L)),
                n_leg_open=int(len(si)), win_cl=float(100 * (K["pnl"] > 0).mean()) if len(K) else np.nan,
                pnl_per_cl=float(K["pnl"].mean()) if len(K) else np.nan, pnl=pnl, bal0=bal0, roi=100 * roi, cagr_ann=100 * ann,
                ret_mtm=100 * ret, dd_q=ddq, dd_cum=ddc, calmar=float(100 * ann / abs(ddq)) if ddq < 0 else np.nan,
                exp_mean=float(100 * ex.mean()), exp_max=float(100 * ex.max()), npos_max=int(npo.max()),
                hold_med_h=float(np.median(K["age_min"]) / 60) if len(K) else np.nan,
                ex_trail=int(trail.sum()), ex_ts168=int(ts168.sum()), ex_x14=int(x14.sum()),
                ex_other=int(len(K) - trail.sum() - ts168.sum() - x14.sum()), fee=float(L["fee"].sum()),
                funding=float(L["funding"].sum()), notional=float(L["notional"].sum()), days=nd, flat_days=flat_days,
                noentry_days=noentry_days, flag_days=fdays, **leg)


def quarters(a, b):
    out, q = [], pd.Timestamp(a)
    while q < pd.Timestamp(b):
        nx = q + pd.DateOffset(months=3)
        out.append(("%dQ%d" % (q.year, (q.month - 1) // 3 + 1), q, nx))
        q = nx
    return out


DEV_PER = [(n, a, b, "Q") for n, a, b in quarters("2021-07-01", "2026-01-01")] + \
          [("2021H2", pd.Timestamp("2021-07-01"), pd.Timestamp("2022-01-01"), "Y")] + \
          [(str(y), pd.Timestamp("%d-01-01" % y), pd.Timestamp("%d-01-01" % (y + 1)), "Y") for y in range(2022, 2026)] + \
          [("DEV_2022_25", pd.Timestamp("2022-01-01"), pd.Timestamp("2026-01-01"), "T"),
           ("DEV_ALL_2021H2_25", pd.Timestamp("2021-07-01"), pd.Timestamp("2026-01-01"), "T")]
HO_PER = [(n, a, b, "Q") for n, a, b in quarters("2026-01-01", "2026-10-01")] + \
         [("HO_2026_W9", pd.Timestamp("2026-01-01"), pd.Timestamp("2026-10-01"), "T")]


def ph0_of(name, a):
    if a >= HO_L0:
        return HO_L0
    return pd.Timestamp("2021-07-01") if a < pd.Timestamp("2022-01-01") else pd.Timestamp("2022-01-01")


def main():
    os.makedirs(OUTD, exist_ok=True)
    V = {}
    md, mh = json.load(open(WK + "/mtm_dev.json")), json.load(open(WK + "/mtm_ho.json"))
    V["mtm_dev_missing"] = {k: v["missing"] for k, v in md["check"].items()}
    V["mtm_ho_miss"] = md_h = mh["mtm_check"]["miss"]
    assert all(v == 0 for v in V["mtm_dev_missing"].values()) and md_h == 0, "MTM missing != 0"
    V["mtm_dev_ok"], V["mtm_ho_ok"] = md["ok"], mh["ok"]
    V["published_dev"] = dict(cagr22_mean=md["cagr22_mean"], cagr22_median=md["cagr22_median"], dd22_mean=md["dd22_mean"],
                              dd22_median=md["dd22_median"])
    V["V_published_cagr_dd"] = bool(abs(md["cagr22_mean"] - 39.49) <= 0.1 and abs(md["dd22_mean"] + 22.55) <= 0.1
                                    and abs(md["dd22_median"] + 22.83) <= 0.1)
    fdev = json.load(open(TSX + "/flags.json"))
    fho = json.load(open(TSX + "/ho/ho_flags.json"))
    FD, FH = flagset(fdev["ranges"]), flagset(fho["ranges"])
    assert len(FD) == 214 and len(FH) == 15
    par = json.load(open(TSX + "/parity.json"))
    zd, zh = np.load(WK + "/eq_dev.npz"), np.load(WK + "/eq_ho.npz")
    ub_dev = pd.Timestamp("2021-07-01") - H7  # truc phut DEV cua bang nay: 2021-07-01 00:00 +07 = 2021-06-30 17:00 UTC
    off = int((DAY0 - ub_dev) // MIN)  # = 420: eq gvz bat dau DAY0 UTC
    ndev = int((pd.Timestamp("2026-01-01") - pd.Timestamp("2021-07-01")) // MIN)
    nho = 273 * 1440
    assert int(zh["__T0"][0]) == int((HO_L0 - H7).value // 10 ** 6)
    rows, CHK = [], {}
    for s in DEV_SEEDS:
        tag = "tsx-x14-" + s.lower()
        rj = json.load(open(KS + tag + "/result.json"))
        assert rj["overrides"]["SIM_LOSER_TS_EXT_DAYS"] == fdev["ranges"] and rj["equity_start"] == CAP0
        e, m0 = zd["X14_" + s], int(zd["X14_" + s + "__m0"][0]) + off
        assert m0 + len(e) <= ndev
        full = np.empty(ndev)
        full[:m0] = CAP0
        full[m0:m0 + len(e)] = e
        full[m0 + len(e):] = e[-1]
        r = build(tag, "gqsf-" + s.lower(), full, ub_dev, FD, fix_off=off)
        assert r["d"]["si"].min() >= m0 and r["d"]["ei"].max() < m0 + len(e), "co vi the ngoai mien eq DEV"
        r["chk"].update(defer_java=par[tag]["tsx"][1], eq_end_vs_bal=float(full[-1] - CAP0 - r["d"]["pnl"].sum()))
        CHK[tag] = r["chk"]
        for name, a, b, k in DEV_PER:
            rows.append(dict(phase="DEV", seed=s, period=name, kind=k, start=str(a.date()), end=str(b.date()),
                             **metrics(r, a, b, k, ph0_of(name, a), FD)))
        log.info("DEV %s %s", s, r["chk"])
    for s in HO_SEEDS:
        tag = "tsx-ho-x14-s%d" % s
        rj = json.load(open(KS + tag + "/result.json"))
        assert rj["overrides"]["SIM_LOSER_TS_EXT_DAYS"] == fho["ranges"] and rj["equity_start"] == CAP0
        eq = zh[tag][:nho]
        r = build(tag, "ho4-k24-b-s%d" % s, eq, HO_L0 - H7, FH)
        assert np.array_equal(np.sort(r["d"]["ei"].to_numpy()), np.sort(zh[tag + "__e"])), "truc HO lech ecm_mtm_h"
        assert r["d"]["si"].max() < nho
        hres = json.load(open(TSX + "/ho/res_%s.json" % tag))
        r["chk"].update(defer_java=hres["tsx"][3])
        CHK[tag] = r["chk"]
        for name, a, b, k in HO_PER:
            rows.append(dict(phase="HO", seed=str(s), period=name, kind=k, start=str(a.date()), end=str(b.date()),
                             **metrics(r, a, b, k, HO_L0, FH)))
        log.info("HO %s %s", s, r["chk"])
    df = pd.DataFrame(rows)
    df.to_csv(OUTD + "/quarterly_x14_by_seed.csv", index=False)
    V["axis_check"] = CHK
    V["V_axis"] = bool(all(v["flat_maxabs"] < 0.1 for v in CHK.values()))
    V["V_defer_vs_java"] = {t: [v["n_defer"], v["defer_java"]] for t, v in CHK.items()}
    V["V_defer_ok"] = bool(all(a == b for a, b in V["V_defer_vs_java"].values()))
    # V1: tong quy = tong giai doan
    v1 = {}
    for ph, seeds in (("DEV", DEV_SEEDS), ("HO", [str(x) for x in HO_SEEDS])):
        for s in seeds:
            g = df[(df["phase"] == ph) & (df["seed"] == s)].set_index("period")
            q = g[g["kind"] == "Q"]
            if ph == "DEV":
                q22 = q[q.index >= "2022"]
                tag = "tsx-x14-" + s.lower()
                tot = float(load(tag)["pnl"].sum())
                v1[tag] = dict(q22_vs_dev22=float(q22["pnl"].sum() - g.loc["DEV_2022_25", "pnl"]),
                               qall_vs_printDone=float(q["pnl"].sum() - tot),
                               years_vs_dev22=float(g.loc[["2022", "2023", "2024", "2025"], "pnl"].sum() - g.loc["DEV_2022_25", "pnl"]),
                               entries_q_vs_all=int(q["n_entry"].sum() - g.loc["DEV_ALL_2021H2_25", "n_entry"]),
                               cl_q_vs_all=int(q["n_cl"].sum() - g.loc["DEV_ALL_2021H2_25", "n_cl"]),
                               logret_q_vs_all=float(np.log1p(q["ret_mtm"] / 100).sum() - np.log1p(g.loc["DEV_ALL_2021H2_25", "ret_mtm"] / 100)))
            else:
                tag = "tsx-ho-x14-s" + s
                v1[tag] = dict(q_vs_w9=float(q["pnl"].sum() - g.loc["HO_2026_W9", "pnl"]),
                               cl_q_vs_w9=int(q["n_cl"].sum() - g.loc["HO_2026_W9", "n_cl"]),
                               logret_q_vs_w9=float(np.log1p(q["ret_mtm"] / 100).sum() - np.log1p(g.loc["HO_2026_W9", "ret_mtm"] / 100)))
    V["V1_sum"] = v1
    V["V1_ok"] = bool(all(abs(x) <= 1.0 for t in v1.values() for k, x in t.items() if k.startswith(("q", "years"))) and
                      all(t.get("entries_q_vs_all", 0) == 0 and t.get("cl_q_vs_all", 0) == 0 and t.get("cl_q_vs_w9", 0) == 0 for t in v1.values()))
    # V2: so cum / dot / leg DEV toan ky vs so cong bo (TSX_V3_JAVA dev_rows.csv, X14)
    pub = pd.read_csv(REPO + "/docs/result/tsx_v3_java/dev_rows.csv")
    pub = pub[pub["arm"] == "C420"].set_index("seed")
    v2 = {}
    for s in DEV_SEEDS:
        g = df[(df["phase"] == "DEV") & (df["seed"] == s) & (df["period"] == "DEV_ALL_2021H2_25")].iloc[0]
        cagr_pub = md["check"]["X14_" + s]["cagr22"]
        q4 = df[(df["phase"] == "DEV") & (df["seed"] == s) & (df["period"] == "2025Q4")].iloc[0]
        v2[s] = dict(n_cl=[int(g["n_cl"]), int(pub.loc[s, "n_cl_x14"])], n_entry=[int(g["n_entry"]), int(pub.loc[s, "n_batch_x14"])],
                     n_leg=[int(g["n_leg"]), int(pub.loc[s, "n_leg_x14"])], pnl=[float(g["pnl"]), float(pub.loc[s, "pnl_x14"])],
                     dd_cum_2025Q4=[float(q4["dd_cum_legacy"]), float(pub.loc[s, "dd22_x14"])],
                     dd22_fixed=float(q4["dd_cum"]),
                     cagr22_rerun=[cagr_pub, float(pub.loc[s, "cagr22_x14"])])
    V["V2_counts"] = v2
    V["V2_ok"] = bool(all(x["n_cl"][0] == x["n_cl"][1] and x["n_entry"][0] == x["n_entry"][1] and x["n_leg"][0] == x["n_leg"][1]
                          and abs(x["pnl"][0] - x["pnl"][1]) < 1e-3 and abs(x["dd_cum_2025Q4"][0] - x["dd_cum_2025Q4"][1]) <= 0.05
                          and abs(x["cagr22_rerun"][0] - x["cagr22_rerun"][1]) < 1e-6 for x in v2.values()))
    V["V2_medians"] = dict(n_cl=float(np.median([x["n_cl"][0] for x in v2.values()])),
                           n_entry=float(np.median([x["n_entry"][0] for x in v2.values()])),
                           n_leg=float(np.median([x["n_leg"][0] for x in v2.values()])),
                           dd22_legacy=float(np.median([x["dd_cum_2025Q4"][0] for x in v2.values()])),
                           dd22_fixed=float(np.median([x["dd22_fixed"] for x in v2.values()])),
                           dd22_fixed_mean=float(np.mean([x["dd22_fixed"] for x in v2.values()])),
                           dd22_fixed_worst=float(np.min([x["dd22_fixed"] for x in v2.values()])))
    # V4: HO tung quy vs ho_mtm.json (scorer HO4/ecm_mtm_h)
    hm = json.load(open(TSX + "/ho/ho_mtm.json"))["runs"]
    v4 = {}
    for s in HO_SEEDS:
        tag = "tsx-ho-x14-s%d" % s
        for qn, wk in (("2026Q1", "Q1"), ("2026Q2", "Q2"), ("2026Q3", "Q3"), ("HO_2026_W9", "W9")):
            g = df[(df["phase"] == "HO") & (df["seed"] == str(s)) & (df["period"] == qn)].iloc[0]
            v4["%s_%s" % (tag, wk)] = dict(d_pnl=float(g["pnl"] - hm[tag][wk]["sum_pnl"]), d_ret=float(g["ret_mtm"] - hm[tag][wk]["roi"]),
                                         d_dd=float(g["dd_q"] - hm[tag][wk]["maxdd"]))
    V["V4_ho_vs_ho_mtm"] = v4
    V["V4_max"] = {k: float(max(abs(x[k]) for x in v4.values())) for k in ("d_pnl", "d_ret", "d_dd")}
    V["V4_ok"] = bool(V["V4_max"]["d_pnl"] < 1e-3 and V["V4_max"]["d_ret"] < 0.05 and V["V4_max"]["d_dd"] < 0.05)
    V["ALL_OK"] = bool(V["V_published_cagr_dd"] and V["V_axis"] and V["V_defer_ok"] and V["V1_ok"] and V["V2_ok"] and V["V4_ok"]
                       and V["mtm_dev_ok"] and V["mtm_ho_ok"])
    log.info("VALIDATE pub %s axis %s defer %s V1 %s V2 %s V4 %s %s mtm %s/%s -> ALL %s", V["V_published_cagr_dd"], V["V_axis"],
             V["V_defer_ok"], V["V1_ok"], V["V2_ok"], V["V4_ok"], V["V4_max"], V["mtm_dev_ok"], V["mtm_ho_ok"], V["ALL_OK"])
    json.dump(V, open(OUTD + "/validate.json", "w"), indent=1, default=str)
    # tong hop median [min, max] qua 8 seed
    MET = [c for c in df.columns if c not in ("phase", "seed", "period", "kind", "start", "end")]
    agg = []
    for (ph, per), g in df.groupby(["phase", "period"], sort=False):
        row = dict(phase=ph, period=per, kind=g["kind"].iloc[0], start=g["start"].iloc[0], end=g["end"].iloc[0], n_seed=len(g))
        for m in MET:
            v = g[m].astype(float)
            row[m + "_med"], row[m + "_min"], row[m + "_max"] = float(v.median()), float(v.min()), float(v.max())
        agg.append(row)
    A = pd.DataFrame(agg)
    A.to_csv(OUTD + "/quarterly_x14.csv", index=False)
    # tap trung PnL DEV 2022-25 theo seed
    conc = {}
    for s in DEV_SEEDS:
        q = df[(df["phase"] == "DEV") & (df["seed"] == s) & (df["kind"] == "Q") & (df["period"] >= "2022")]
        p = q.sort_values("pnl", ascending=False)
        tot = q["pnl"].sum()
        conc[s] = dict(top3=list(p["period"].iloc[:3]), top3_share=float(p["pnl"].iloc[:3].sum() / tot),
                       top1_share=float(p["pnl"].iloc[0] / tot), n_neg=int((q["pnl"] < 0).sum()),
                       neg_q=list(q.loc[q["pnl"] < 0, "period"]), worst_q=str(q.loc[q["pnl"].idxmin(), "period"]),
                       worst_ddq=str(q.loc[q["dd_q"].idxmin(), "period"]), pos_share_top3=float(p["pnl"].iloc[:3].sum() / q.loc[q["pnl"] > 0, "pnl"].sum()))
    S = dict(conc=conc, top3_share_med=float(np.median([c["top3_share"] for c in conc.values()])),
             top3_share_min=float(min(c["top3_share"] for c in conc.values())), top3_share_max=float(max(c["top3_share"] for c in conc.values())),
             n_neg_med=float(np.median([c["n_neg"] for c in conc.values()])))
    json.dump(S, open(OUTD + "/summary.json", "w"), indent=1, default=str)
    log.info("CONC %s", {k: v for k, v in S.items() if k != "conc"})
    write_md(A)
    log.info("DONE ALL_OK=%s", V["ALL_OK"])
    if not V["ALL_OK"]:
        sys.exit(4)


def f(x, p=0):
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else ("{:,.%df}" % p).format(x).replace(",", " ").replace(".", ",")


def write_md(A):
    o = ["# GOLIVE_QUARTERLY — bảng tự sinh (median 8 seed [min … max])", ""]
    o.append("## A. Hiệu quả")
    o.append("| Quý | Đợt vào | Cụm | Leg | Win % cụm | PnL/cụm | ΣPnL USD | ROI % | CAGR quy năm % | maxDD quý % | DD lũy kế % | Calmar | DD quý legacy % | DD lũy kế legacy % |")
    o.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in A.iterrows():
        o.append("| %s | %s | %s | %s | %s | %s | %s [%s … %s] | %s [%s … %s] | %s | %s [%s … %s] | %s | %s | %s | %s |" % (
            r["period"], f(r["n_entry_med"]), f(r["n_cl_med"]), f(r["n_leg_med"]), f(r["win_cl_med"], 1), f(r["pnl_per_cl_med"], 1),
            f(r["pnl_med"]), f(r["pnl_min"]), f(r["pnl_max"]), f(r["roi_med"], 2), f(r["roi_min"], 2), f(r["roi_max"], 2),
            f(r["cagr_ann_med"], 1), f(r["dd_q_med"], 2), f(r["dd_q_min"], 2), f(r["dd_q_max"], 2), f(r["dd_cum_med"], 2),
            f(r["calmar_med"], 2), f(r["dd_q_legacy_med"], 2), f(r["dd_cum_legacy_med"], 2)))
    o += ["", "## B. Phơi nhiễm / thoát / chi phí"]
    o.append("| Quý | Phơi nhiễm TB % | max % | Vị thế đồng thời max | Giữ trung vị h | Trailing | Time-stop 168h | X14 gia hạn | Khác | Phí USD | Funding USD | Ngày không vị thế | Ngày không vào lệnh | Ngày cờ X14 | ret MTM % |")
    o.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in A.iterrows():
        o.append("| %s | %s | %s [%s … %s] | %s | %s | %s | %s | %s | %s | %s | %s | %s / %s | %s | %s | %s |" % (
            r["period"], f(r["exp_mean_med"], 2), f(r["exp_max_med"], 1), f(r["exp_max_min"], 1), f(r["exp_max_max"], 1),
            f(r["npos_max_med"]), f(r["hold_med_h_med"], 1), f(r["ex_trail_med"]), f(r["ex_ts168_med"]), f(r["ex_x14_med"]),
            f(r["ex_other_med"]), f(r["fee_med"]), f(r["funding_med"]), f(r["flat_days_med"]), f(r["days_med"]), f(r["noentry_days_med"]),
            f(r["flag_days_med"]), f(r["ret_mtm_med"], 2)))
    open(OUTD + "/tables.md", "w").write("\n".join(o) + "\n")


if __name__ == "__main__":
    main()
