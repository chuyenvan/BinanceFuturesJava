#!/usr/bin/env python3
"""NUP3 Pha 1 — cham theo PREREG_NUP3.md (c2b4c462) §5/§6 (G1-G3, KHONG G4) + ADDENDUM_TECH (ab2391e4).

Dien giai MASTER (chot, ghi trong result):
- Ky cham DEV 2022-01-01 -> 2025-12-31, gan lenh theo gio DONG +07 (nhu NUP).
- 2021H2 (ky xac nhan V2): dong sleeve co gio dong < 2022-01-01 +07 bi LOAI NGAY KHI DOC (khong tinh/in PnL).
  Leg sleeve mo truoc 2022 nhung dong >= 2022 duoc giu (gan theo gio dong) va MTM chi tinh tu phut 2021-12-31 23:59 +07
  (m0 bi kep) => khong co gia tri MTM sleeve nao truoc moc dau doan DD.
  So nen = B0 byte-identical (da cong bo) => giu nguyen ca 2021H2 de tai lap so B0.
- G3 U tong = Σ notional@mark (nen+sleeve) / equity MTM toan danh muc; bao them margin@entry / equity.
- maxDD MTM toan danh muc = pipeline NUP (research/nup/mtm_parquet.py, ADDENDUM B), missing = 0.
Stage: check | mtm | score
"""
import hashlib
import io
import json
import os
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/claude_master/vz_e1_wt"
sys.path.insert(0, REPO + "/research/nup")
sys.path.insert(0, REPO + "/research/golive_quarterly")
import mtm_parquet as M  # noqa: E402  (pipeline NUP ADDENDUM B)
import quarterly as Q  # noqa: E402

R = M.R
KS = "/home/ubuntu/kaggle_sim/out/"
WK = "/home/ubuntu/claude_master/nup3_p1_wk"
OUTD = REPO + "/docs/result/nup3"
ARMS = ["v0", "v1", "v2"]
SEEDS = ["a1", "s7", "s21", "s99"]
CAP0 = 35000.0
MIN = pd.Timedelta(minutes=1)
L0 = pd.Timestamp("2021-07-01")          # goc truc +07 (= Q ubase + 7h)
DEV_A, DEV_B = pd.Timestamp("2022-01-01"), pd.Timestamp("2026-01-01")
NDEV = int((DEV_B - L0) // MIN)
OFF = 420
I0, I1 = int((DEV_A - L0) // MIN), NDEV
CLIP_UTC = I0 - 1 - OFF                  # chi so truc UTC-DAY0 cua phut I0-1 (2021-12-31 16:59 UTC)
YEARS = [2022, 2023, 2024, 2025]
B0MD5 = {"a1": "dc62609b", "s7": "622b03e2"}
SB = b"book=sleeve"
JAR = "b269f96b782275a8089bbae1532f8c68e1aab18cba602bf02ee2a64b3adda051"


def tag(a, s):
    return "nup3-%s-%s" % (a, s)


def md5b(b):
    return hashlib.md5(b).hexdigest()


def split_run(t):
    raw = open(KS + t + "/storage/printDone.csv", "rb").read()
    lines = raw.splitlines(keepends=True)
    hdr, body = lines[0], lines[1:]
    isS = [ln.rstrip(b"\r\n").split(b",")[-1] == SB for ln in body]
    assert not any((b"book=" in ln) and not s for ln, s in zip(body, isS)), t
    idx = [i for i, s in enumerate(isS) if s]
    nb = [i for i, s in enumerate(isS) if not s]
    assert idx and (not nb or min(idx) > max(nb)), (t, "sleeve khong nam sau moi dong nen")
    base = [ln for ln, s in zip(body, isS) if not s]
    slv = [ln for ln, s in zip(body, isS) if s]
    return hdr, base, slv


def parse(blob, book, drop_before=None):
    d = pd.read_csv(io.BytesIO(blob), index_col=False)
    d.columns = [c.strip() for c in d.columns]
    for c in ("quantity", "entry", "tp", "pnl", "margin", "funding"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    n0 = len(d)
    d = d.dropna(subset=["pnl", "quantity", "entry", "margin"]).copy()
    assert len(d) == n0
    d["sym"] = d["sym"].astype(str).str.strip()
    d["status"] = d["status"].astype(str).str.strip()
    d["ts"] = pd.to_datetime(d["start"].astype(str).str.strip(), format="%Y%m%d %H:%M")
    d["te"] = pd.to_datetime(d["end"].astype(str).str.strip(), format="%Y%m%d %H:%M")
    ndrop = 0
    if drop_before is not None:          # LOAI 2021H2 ngay khi doc (theo gio dong +07)
        keep = d["te"] >= drop_before
        ndrop = int((~keep).sum())
        d = d[keep].copy()
    d["notional"] = d["quantity"] * d["entry"]
    d["book"] = book
    d["si"] = ((d["ts"] - L0) // MIN).astype(np.int64)
    d["ei"] = ((d["te"] - L0) // MIN).astype(np.int64)
    return d.reset_index(drop=True), ndrop


def load_sleeve(t):
    hdr, _, slv = split_run(t)
    return parse(hdr + b"".join(slv), "S", DEV_A)


def load_b0(s):
    return parse(open(KS + "tsx-x14-%s/storage/printDone.csv" % s, "rb").read(), "B")[0]


# ------------------------------------------------------------------ check
def stage_check():
    V = {}
    b0m = {s: md5b(open(KS + "tsx-x14-%s/storage/printDone.csv" % s, "rb").read()) for s in SEEDS}
    for s, p in B0MD5.items():
        assert b0m[s].startswith(p)
    for a in ARMS:
        for s in SEEDS:
            t = tag(a, s)
            hdr, base, slv = split_run(t)
            rj = json.load(open(KS + t + "/result.json"))
            sm = json.load(open(KS + t + "/storage/sleeve_summary.json"))
            mb = md5b(hdr + b"".join(base))
            V[t] = dict(md5_base=mb, md5_b0=b0m[s], inv_ok=mb == b0m[s], n_base_rows=len(base), n_sleeve_rows=len(slv),
                        sleeve_rows_vs_summary=len(slv) == sm["printdone_sleeve_rows"], ok=rj["ok"], jar_ok=rj["jar_sha256"] == JAR,
                        arm_ok=sm["arm"] == a.upper(), n_trades_ok=rj["n_trades"] == len(base) + len(slv),
                        # chi dem (khong PnL); toan ky sim, gom 2021H2
                        sim_counts={k: sm[k] for k in ("cand", "cand_book_full", "opened", "opened_book_full", "skip_held_base",
                                                       "skip_held_sleeve", "skip_burst", "skip_noflag", "not_opened",
                                                       "clusters_sleeve", "clusters_base", "overlap_base_opens_sleeve_sym",
                                                       "u_total_max", "u_total_margin_max", "u_total_fail_ticks", "max_pos_total",
                                                       "flag_intervals", "flag_minutes")})
    allok = all(v["inv_ok"] and v["sleeve_rows_vs_summary"] and v["ok"] and v["jar_ok"] and v["arm_ok"] and v["n_trades_ok"]
                for v in V.values())
    json.dump(dict(runs=V, ALL_OK=allok), open(WK + "/check.json", "w"), indent=1)
    for t, v in V.items():
        print(t, v["inv_ok"], v["n_base_rows"], v["n_sleeve_rows"], v["sleeve_rows_vs_summary"], v["ok"], v["jar_ok"], v["n_trades_ok"])
    print("CHECK ALL_OK", allok)
    assert allok


# ------------------------------------------------------------------ mtm
def stage_mtm():
    FR = {}
    for a in ARMS:
        for s in SEEDS:
            d, nd = load_sleeve(tag(a, s))
            x = d[["sym", "quantity", "entry", "margin", "pnl", "ts", "te", "notional"]].copy()
            x["clip_m0"] = CLIP_UTC
            FR[tag(a, s) + "#S"] = x
            print("sleeve", tag(a, s), "rows_kept", len(x), "rows_dropped_2021H2", nd, "cross_boundary_legs", int((x.ts < DEV_A).sum()))
    o_ll, o_lm = R.load_legs, R.load_legs_minute

    def ll(t):
        return FR[t].copy() if t in FR else o_ll(t)

    def lm(d):
        out = o_lm(d)
        if "clip_m0" in out.columns:
            out["m0"] = np.maximum(out["m0"].to_numpy(np.int64), out["clip_m0"].to_numpy(np.int64))
        return out
    R.load_legs, R.load_legs_minute = ll, lm
    b0 = ["tsx-x14-" + s for s in SEEDS]
    ver = b0 if os.path.exists("/home/ubuntu/claude_master/tsx/deep_cache/eq_dev.npz") else None
    out, miss = M.build(b0 + sorted(FR), ver)
    print("missing", miss)
    assert all(v == 0 for v in miss.values()), miss
    np.savez(WK + "/eq.npz", **{k.replace("#", "__"): v for k, v in out.items()})
    json.dump(dict(missing=miss, verify_deep_cache=ver is not None), open(WK + "/mtm.json", "w"), indent=1)


def dev_full(e):
    n = min(len(e), NDEV - OFF)
    full = np.empty(NDEV)
    full[:OFF] = CAP0
    full[OFF:OFF + n] = e[:n]
    full[OFF + n:] = e[n - 1]
    return full


# ------------------------------------------------------------------ score
def clusters(d):
    c = d.groupby(["book", "sym", "te"], sort=False).agg(t0=("ts", "min"), si=("si", "min"), ei=("ei", "first"),
                                                        pnl=("pnl", "sum"), notional=("notional", "sum"), n=("sym", "size")).reset_index()
    return c


def realized_bal(d, n):
    real = np.zeros(n)
    ok = (d["ei"] >= 0) & (d["ei"] < n)
    np.add.at(real, d.loc[ok, "ei"].to_numpy(), d.loc[ok, "pnl"].to_numpy(float))
    return CAP0 + float(d.loc[d["ei"] < 0, "pnl"].sum()) + np.cumsum(real)


def ywin(y):
    return int((pd.Timestamp("%d-01-01" % y) - L0) // MIN), int((pd.Timestamp("%d-01-01" % (y + 1)) - L0) // MIN)


def qwins():
    out = []
    for y in YEARS:
        for q in range(4):
            a = pd.Timestamp(year=y, month=3 * q + 1, day=1)
            b = a + pd.DateOffset(months=3)
            out.append(("%dQ%d" % (y, q + 1), int((a - L0) // MIN), int((b - L0) // MIN)))
    return out


def stress(L):
    return float((L["pnl"] - 0.002 * L["notional"]).sum())


def core(d, eq):
    """chi so toan ky DEV cho tap leg d (1 hoac 2 so) tren equity eq (truc +07)."""
    n = len(eq)
    L = d[(d["ei"] >= I0) & (d["ei"] < I1)]
    c = clusters(d)
    K = c[(c["ei"] >= I0) & (c["ei"] < I1)]
    bal0 = CAP0 + float(d.loc[d["ei"] < I0, "pnl"].sum())
    pnl = float(L["pnl"].sum())
    roi = pnl / bal0
    nd = (DEV_B - DEV_A).days
    ann = (1 + roi) ** (365.25 / nd) - 1
    dd = Q.ddx(eq[I0 - 1:I1])
    yr = {}
    for y in YEARS:
        a, b = ywin(y)
        yr[y] = dict(n_cl=int(((K["ei"] >= a) & (K["ei"] < b)).sum()),
                     pnl=float(L.loc[(L["ei"] >= a) & (L["ei"] < b), "pnl"].sum()),
                     stress=stress(L[(L["ei"] >= a) & (L["ei"] < b)]))
    qs = {qn: float(L.loc[(L["ei"] >= a) & (L["ei"] < b), "pnl"].sum()) for qn, a, b in qwins()}
    return dict(n_cl=int(len(K)), n_leg=int(len(L)), pnl=pnl, stress=stress(L), bal0=bal0, cagr=100 * ann, dd=dd,
                calmar=100 * ann / abs(dd) if dd < 0 else np.nan, yr=yr, q=qs, c=c, K=K, L=L)


def expo(d, c, eq, bal):
    n = len(eq)
    on = Q.sweep(d["si"].to_numpy(), d["ei"].to_numpy(), d["notional"].to_numpy(float), n)
    mg = Q.sweep(d["si"].to_numpy(), d["ei"].to_numpy(), d["margin"].to_numpy(float), n)
    npos = Q.sweep(c["si"].to_numpy(), c["ei"].to_numpy(), np.ones(len(c)), n)
    unr = eq - bal
    um = (on + unr) / eq
    ug = mg / eq
    w = slice(I0, I1)
    return dict(on=on, mg=mg, npos=npos, unr=unr, um=um, ug=ug,
                u_mark_max=float(um[w].max()), u_mark_argmax=int(I0 + um[w].argmax()), u_marg_max=float(ug[w].max()),
                u_mark_gt1_min=int((um[w] > 1.0).sum()), u_marg_gt1_min=int((ug[w] > 1.0).sum()),
                npos_max=int(npos[w].max()), exp_entry_max=float((on / eq)[w].max()))


def episodes(t):
    t = np.sort(np.asarray(t, np.int64))
    if not len(t):
        return []
    br = np.where(np.diff(t) >= 360)[0]          # phut: >= 6h la dot moi
    st = np.concatenate([[0], br + 1])
    en = np.concatenate([br, [len(t) - 1]])
    return list(zip(t[st], t[en]))


def neff(KS_, cB_all, KB):
    """KS_: cum sleeve dong trong DEV; cB_all: moi cum nen; KB: cum nen dong trong DEV. Ngay = ngay +07."""
    x = KS_[KS_["si"] >= I0]
    xe = episodes(x["si"].to_numpy())
    be = episodes(cB_all["si"].to_numpy())
    bs = np.array([e[0] for e in be], np.int64)
    bE = np.array([e[1] for e in be], np.int64)
    nonov = 0
    for s, e in xe:
        k = np.searchsorted(bs, e, "right")
        nonov += not bool(k > 0 and np.any(bE[:k] >= s))
    xd = np.unique(x["si"].to_numpy() // 1440)
    bdays = set((cB_all["si"].to_numpy() // 1440).tolist())
    nob0 = np.array([dd not in bdays for dd in xd], bool)
    days = np.arange(I0 // 1440, I1 // 1440)
    ps = pd.Series(KS_["pnl"].to_numpy(), index=KS_["ei"].to_numpy() // 1440).groupby(level=0).sum().reindex(days, fill_value=0.0)
    pb = pd.Series(KB["pnl"].to_numpy(), index=KB["ei"].to_numpy() // 1440).groupby(level=0).sum().reindex(days, fill_value=0.0)
    tot = float(KS_["pnl"].sum())
    return dict(ep=len(xe), ep_y=len(xe) / 4, ep_nonov=nonov, ep_nonov_y=nonov / 4, pct_ep_nonov=100 * nonov / len(xe) if xe else np.nan,
                days=int(len(xd)), days_y=len(xd) / 4, pct_days_nob0=float(100 * nob0.mean()) if len(xd) else np.nan,
                corr_daily=float(np.corrcoef(ps.to_numpy(), pb.to_numpy())[0, 1]),
                top10_day_pct=float(100 * np.sort(ps.to_numpy())[::-1][:10].sum() / tot) if tot else np.nan,
                n_days_axis=int(len(days)))


def overlap(cB_all, KS_):
    """cum nen mo (t0 trong DEV) tren symbol ma sleeve dang giu: t0_s < t0_b <= te_s (sleeve chay cuoi tick)."""
    b = cB_all[(cB_all["si"] >= I0) & (cB_all["si"] < I1)]
    g = {s: (x["si"].to_numpy(), x["ei"].to_numpy()) for s, x in KS_.groupby("sym")}
    n = 0
    for sym, t0 in zip(b["sym"], b["si"]):
        if sym in g:
            a, e = g[sym]
            n += bool(np.any((a < t0) & (t0 <= e)))
    return n, int(len(b))


MONTH_UTC0 = set(int((pd.Timestamp(year=y, month=m, day=1) - L0) // MIN) + OFF for y in range(2021, 2026) for m in range(1, 13))


def month_fix(d, eq):
    """Bug pipeline mtm_parquet (phat hien khi cham NUP3 P1): leg dong DUNG 00:00 UTC ngay 1 dau thang (m1 == ms) bi loai
    khoi ca thang truoc (m1 < me sai) lan thang sau (m1 > ms sai) => PnL thuc hien khong bao gio vao eq. Ban sua: cong PnL
    cac leg nay tu phut dong toi het truc. Chi dung lam so doi chung (so chinh = pipeline NUP, tai lap so B0 cong bo)."""
    z = d["ei"].isin(MONTH_UTC0).to_numpy()
    n = len(eq)
    corr = Q.sweep(d.loc[z, "ei"].to_numpy(), np.full(int(z.sum()), n), d.loc[z, "pnl"].to_numpy(float), n)
    return eq + corr, int(z.sum())


def stage_score():
    z = np.load(WK + "/eq.npz")
    chk = json.load(open(WK + "/check.json"))
    BS = pd.read_csv(REPO + "/docs/result/golive_quarterly/quarterly_x14_by_seed.csv")
    sys.path.insert(0, REPO + "/research/nup")
    import score as S  # noqa: E402
    runs, years, quarts, V = [], [], [], dict(b0_repro={}, quarter_sum={}, sleeve_flat={}, sleeve_end={}, base_flat={})
    B = {}
    for s in SEEDS:
        dB = load_b0(s)
        eqB = dev_full(z["tsx-x14-" + s])
        balB = realized_bal(dB, NDEV)
        cb = core(dB, eqB)
        xb = expo(dB, cb["c"], eqB, balB)
        r = BS[(BS.phase == "DEV") & (BS.seed.str.lower() == s) & (BS.period == "DEV_2022_25")].iloc[0]
        ry = {y: int(BS[(BS.phase == "DEV") & (BS.seed.str.lower() == s) & (BS.period == str(y))].iloc[0].n_cl) for y in YEARS}
        st_pub = S.stress_sum("tsx-x14-" + s, "2022-01-01", "2026-01-01")
        V["b0_repro"][s] = dict(n_cl=[cb["n_cl"], int(r.n_cl)], pnl=[cb["pnl"], float(r.pnl)], cagr=[cb["cagr"], float(r.cagr_ann)],
                                dd=[cb["dd"], float(r.dd_cum)], stress=[cb["stress"], st_pub],
                                yr_ncl=[[cb["yr"][y]["n_cl"] for y in YEARS], [ry[y] for y in YEARS]])
        flat = xb["npos"] < 0.5
        eqBf, nfb = month_fix(dB, eqB)
        V["base_flat"][s] = dict(pipeline=float(np.abs(xb["unr"][flat]).max()), fixed=float(np.abs((eqBf - balB)[flat]).max()),
                                 n_fix_legs=nfb, dd_fix=Q.ddx(eqBf[I0 - 1:I1]))
        B[s] = dict(d=dB, eq=eqB, eqf=eqBf, bal=balB, core=cb, x=xb, nfix=nfb)
    for a in ARMS:
        for s in SEEDS:
            t = tag(a, s)
            dS, _ = load_sleeve(t)
            eqS = dev_full(z[t + "__S"])
            balS = realized_bal(dS, NDEV)
            b = B[s]
            dP = pd.concat([b["d"], dS], ignore_index=True)
            eqP = b["eq"] + eqS - CAP0
            balP = b["bal"] + balS - CAP0
            cp = core(dP, eqP)
            xp = expo(dP, cp["c"], eqP, balP)
            cs = core(dS, eqS)
            cS_all = clusters(dS)
            xs_npos = Q.sweep(cS_all["si"].to_numpy(), cS_all["ei"].to_numpy(), np.ones(len(cS_all)), NDEV)
            fl = (xs_npos < 0.5)
            fl[:I0 - 1] = False
            eqSf, nfs = month_fix(dS, eqS)
            eqPf = b["eqf"] + eqSf - CAP0
            dd_fix = Q.ddx(eqPf[I0 - 1:I1])
            V["sleeve_flat"][t] = dict(pipeline=float(np.abs((eqS - balS)[fl]).max()), fixed=float(np.abs((eqSf - balS)[fl]).max()),
                                       n_fix_legs=nfs)
            V["sleeve_end"][t] = dict(eq_end_minus_bal_end=float(eqS[-1] - balS[-1]), open_at_end=int(xs_npos[-1]))
            LS = cs["L"]
            KS_ = cs["K"]
            cB_all = b["core"]["c"]
            KB = b["core"]["K"]
            ne = neff(KS_, cB_all, KB)
            ov, nbw = overlap(cB_all, cS_all)
            # leg sleeve mo khi Σ margin@entry > equity
            sl_open = dS[(dS["si"] >= I0) & (dS["si"] < I1)]
            ug_at = xp["ug"][sl_open["si"].to_numpy()]
            um_at = xp["um"][sl_open["si"].to_numpy()]
            n_rej = int((ug_at > 1.0).sum())
            qsum_p = sum(cp["q"].values()) - cp["pnl"]
            qsum_s = sum(cs["q"].values()) - cs["pnl"]
            V["quarter_sum"][t] = dict(port=qsum_p, sleeve=qsum_s, years_port=sum(cp["yr"][y]["pnl"] for y in YEARS) - cp["pnl"],
                                       years_sleeve=sum(cs["yr"][y]["pnl"] for y in YEARS) - cs["pnl"])
            cb = b["core"]
            row = dict(tag=t, arm=a, seed=s,
                       P_n_cl=cp["n_cl"], P_ncl_y=cp["n_cl"] / 4, B0_n_cl=cb["n_cl"], r_ncl=cp["n_cl"] / cb["n_cl"],
                       P_pnl=cp["pnl"], B0_pnl=cb["pnl"], r_pnl=cp["pnl"] / cb["pnl"],
                       P_stress=cp["stress"], B0_stress=cb["stress"], r_stress=cp["stress"] / cb["stress"],
                       P_cagr=cp["cagr"], B0_cagr=cb["cagr"], P_dd=cp["dd"], B0_dd=cb["dd"], P_calmar=cp["calmar"], B0_calmar=cb["calmar"],
                       P_dd_fix=dd_fix, B0_dd_fix=V["base_flat"][s]["dd_fix"], n_fix_legs_base=b["nfix"], n_fix_legs_sleeve=nfs,
                       P_u_mark_max=xp["u_mark_max"], P_u_mark_t=str(L0 + xp["u_mark_argmax"] * MIN), P_u_marg_max=xp["u_marg_max"],
                       P_u_mark_gt1_min=xp["u_mark_gt1_min"], P_u_marg_gt1_min=xp["u_marg_gt1_min"],
                       P_npos_max=xp["npos_max"], B0_npos_max=b["x"]["npos_max"], B0_u_mark_max=b["x"]["u_mark_max"],
                       S_legs_open_dev=int(len(sl_open)), S_legs_open_marg_gt1=n_rej,
                       S_pct_legs_marg_gt1=100 * n_rej / len(sl_open) if len(sl_open) else np.nan,
                       S_legs_open_mark_gt1=int((um_at > 1.0).sum()),
                       S_n_cl=cs["n_cl"], S_ncl_y=cs["n_cl"] / 4, S_n_leg=cs["n_leg"], S_pnl=cs["pnl"], S_stress=cs["stress"],
                       S_notional=float(LS["notional"].sum()),
                       S_roi_leg=100 * cs["pnl"] / float(LS["notional"].sum()), S_roi_stress=100 * cs["stress"] / float(LS["notional"].sum()),
                       S_pnl_per_cl=cs["pnl"] / cs["n_cl"], S_cross_boundary_cl=int((KS_["si"] < I0).sum()),
                       S_years_stress_pos=int(sum(cs["yr"][y]["stress"] > 0 for y in YEARS)),
                       overlap=ov, base_cl_open_dev=nbw, pct_overlap=100 * ov / nbw,
                       sim_overlap_fullperiod=chk["runs"][t]["sim_counts"]["overlap_base_opens_sleeve_sym"],
                       **{"S_" + k: v for k, v in ne.items()})
            for y in YEARS:
                row["P_ncl_%d" % y] = cp["yr"][y]["n_cl"]
                row["B0_ncl_%d" % y] = cb["yr"][y]["n_cl"]
                row["r_ncl_%d" % y] = cp["yr"][y]["n_cl"] / cb["yr"][y]["n_cl"]
                years.append(dict(tag=t, arm=a, seed=s, year=y, P_n_cl=cp["yr"][y]["n_cl"], B0_n_cl=cb["yr"][y]["n_cl"],
                                  r_ncl=cp["yr"][y]["n_cl"] / cb["yr"][y]["n_cl"], P_pnl=cp["yr"][y]["pnl"], B0_pnl=cb["yr"][y]["pnl"],
                                  S_n_cl=cs["yr"][y]["n_cl"], S_pnl=cs["yr"][y]["pnl"], S_stress=cs["yr"][y]["stress"]))
            for qn in cp["q"]:
                quarts.append(dict(tag=t, arm=a, seed=s, quarter=qn, P_pnl=cp["q"][qn], S_pnl=cs["q"][qn]))
            runs.append(row)
            print(t, "done")
    Rn, Y = pd.DataFrame(runs), pd.DataFrame(years)
    Rn.to_csv(OUTD + "/p1_runs.csv", index=False)
    Y.to_csv(OUTD + "/p1_years.csv", index=False)
    pd.DataFrame(quarts).to_csv(OUTD + "/p1_quarters.csv", index=False)
    arms = []
    for a in ARMS:
        g = Rn[Rn.arm == a]
        gy = Y[Y.arm == a]
        med = lambda c: float(g[c].median())  # noqa: E731
        yr_r = {y: float(gy[gy.year == y].r_ncl.median()) for y in YEARS}
        yr_s = {y: float(gy[gy.year == y].S_stress.median()) for y in YEARS}
        o = dict(arm=a, n_seed=len(g), P_ncl_y=med("P_ncl_y"), B0_ncl_y=float((g.B0_n_cl / 4).median()), r_ncl=med("r_ncl"),
                 **{"r_ncl_%d" % y: yr_r[y] for y in YEARS},
                 P_pnl=med("P_pnl"), B0_pnl=med("B0_pnl"), r_pnl=med("r_pnl"), P_stress=med("P_stress"), r_stress=med("r_stress"),
                 P_cagr=med("P_cagr"), B0_cagr=med("B0_cagr"), P_dd_med=med("P_dd"), P_dd_worst=float(g.P_dd.min()),
                 B0_dd_med=med("B0_dd"), P_calmar=med("P_calmar"), B0_calmar=med("B0_calmar"),
                 P_dd_fix_med=med("P_dd_fix"), P_dd_fix_worst=float(g.P_dd_fix.min()), B0_dd_fix_med=med("B0_dd_fix"),
                 P_u_mark_max_med=med("P_u_mark_max"), P_u_mark_max_worst=float(g.P_u_mark_max.max()),
                 P_u_marg_max_med=med("P_u_marg_max"), P_u_marg_max_worst=float(g.P_u_marg_max.max()),
                 P_npos_max=int(g.P_npos_max.max()), P_npos_max_med=med("P_npos_max"),
                 S_legs_marg_gt1_med=med("S_legs_open_marg_gt1"), S_pct_legs_marg_gt1_med=med("S_pct_legs_marg_gt1"),
                 S_legs_marg_gt1_max=int(g.S_legs_open_marg_gt1.max()),
                 S_ncl_y=med("S_ncl_y"), S_roi_leg=med("S_roi_leg"), S_roi_stress=med("S_roi_stress"), S_pnl=med("S_pnl"),
                 S_stress=med("S_stress"), **{"S_stress_%d" % y: yr_s[y] for y in YEARS},
                 S_years_stress_pos_med=int(sum(yr_s[y] > 0 for y in YEARS)),
                 S_seeds_stress_pos=int((g.S_stress > 0).sum()),
                 overlap_med=med("overlap"), pct_overlap_med=med("pct_overlap"),
                 S_ep_y=med("S_ep_y"), S_ep_nonov_y=med("S_ep_nonov_y"), S_pct_ep_nonov=med("S_pct_ep_nonov"), S_days_y=med("S_days_y"),
                 S_pct_days_nob0=med("S_pct_days_nob0"), S_corr_daily=med("S_corr_daily"), S_top10_day_pct=med("S_top10_day_pct"))
        o["G1"] = bool(o["r_ncl"] >= 1.30 and all(yr_r[y] >= 1.15 for y in YEARS))
        o["G2"] = bool(o["r_pnl"] >= 1.00 and o["S_years_stress_pos_med"] >= 3 and o["S_seeds_stress_pos"] >= 3)
        o["G3"] = bool(o["P_dd_med"] >= -32 and o["P_dd_worst"] >= -36 and o["P_u_mark_max_worst"] <= 1.0)
        o["G3_dd_fix"] = bool(o["P_dd_fix_med"] >= -32 and o["P_dd_fix_worst"] >= -36 and o["P_u_mark_max_worst"] <= 1.0)
        o["PASS_P1"] = bool(o["G1"] and o["G2"] and o["G3"])
        arms.append(o)
    A = pd.DataFrame(arms)
    A.to_csv(OUTD + "/p1_arms.csv", index=False)
    br = V["b0_repro"]
    V["b0_repro_ok"] = bool(all(x["n_cl"][0] == x["n_cl"][1] and abs(x["pnl"][0] - x["pnl"][1]) < 1e-3 and abs(x["cagr"][0] - x["cagr"][1]) < 1e-6
                                and abs(x["dd"][0] - x["dd"][1]) < 0.005 and abs(x["stress"][0] - x["stress"][1]) < 1e-3
                                and x["yr_ncl"][0] == x["yr_ncl"][1] for x in br.values()))
    V["quarter_sum_ok"] = bool(all(abs(v) < 1e-6 for x in V["quarter_sum"].values() for v in x.values()))
    V["check_ALL_OK"] = chk["ALL_OK"]
    V["mtm"] = json.load(open(WK + "/mtm.json"))
    V["mtm_missing_ok"] = bool(all(v == 0 for v in V["mtm"]["missing"].values()))
    json.dump(V, open(OUTD + "/p1_validate.json", "w"), indent=1, default=float)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 80)
    print(A.T.to_string())
    print(json.dumps({k: V[k] for k in ("b0_repro_ok", "quarter_sum_ok", "check_ALL_OK", "mtm_missing_ok")}))
    print("b0_repro", json.dumps(br))
    print("sleeve_flat", V["sleeve_flat"])
    print("base_flat", V["base_flat"])
    print("sleeve_end", V["sleeve_end"])
    cols = ["tag", "P_ncl_y", "r_ncl", "r_ncl_2022", "r_ncl_2023", "r_ncl_2024", "r_ncl_2025", "r_pnl", "r_stress", "P_cagr", "P_dd",
            "P_dd_fix", "B0_dd", "P_calmar", "P_u_mark_max", "P_u_mark_t", "P_u_marg_max", "P_npos_max", "S_legs_open_dev",
            "S_legs_open_marg_gt1", "S_pct_legs_marg_gt1", "S_legs_open_mark_gt1", "S_ncl_y", "S_roi_leg", "S_roi_stress", "S_stress",
            "S_years_stress_pos", "overlap", "pct_overlap", "sim_overlap_fullperiod", "S_ep_y", "S_ep_nonov_y", "S_days_y",
            "S_pct_days_nob0", "S_corr_daily", "S_top10_day_pct", "n_fix_legs_base", "n_fix_legs_sleeve"]
    print(Rn[cols].T.to_string())
    print(Y.pivot_table(index=["arm", "seed"], columns="year", values="S_stress").round(0).to_string())


if __name__ == "__main__":
    os.makedirs(WK, exist_ok=True)
    {"check": stage_check, "mtm": stage_mtm, "score": stage_score}[sys.argv[1]]()
