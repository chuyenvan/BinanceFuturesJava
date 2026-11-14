#!/usr/bin/env python3
"""IND_COMBO P0 cham (prereg vz_e1_wt 14ed6c00 + IND_COMBO_P0_PLAN). Usage: ind_score.py explore | confirm
explore: CHI doc Y EXPLORE (2022-23) -> explore.json + SELECTION.md (+ MDE80 tu so cum CONFIRM, khong doc Y CONFIRM).
confirm: CHI chay ung vien trong selection.json -> confirm.json. HO 2026 chi mo ta."""
import json
import logging
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm, rankdata

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("inds")
W = "/home/ubuntu/claude_master/ind1114/"
NB, RNG = 2000, 20261114
CN = ["C%d" % i for i in range(1, 21)]
MN = ["M%d" % i for i in range(1, 7)]
M1, H = 60000, 3600000
GAP = 60 * M1
YB = {2022: 1640970000000, 2023: 1672506000000, 2024: 1704042000000, 2025: 1735664400000, 2026: 1767200400000}
SEEDS = ["S42", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]


def rk(x):
    return rankdata(x, method="average")


# ---------------- track S ----------------
def usable(L, per, need_y=True):
    m = (L.per == per) & np.isfinite(L.symbolPred) & (L.margin > 0)
    if per != "H":
        m &= np.isfinite(L["rank"])
    if need_y:
        m &= np.isfinite(L.y)
    return L[m].reset_index(drop=True)


def cov(df, with_rank=True, with_year=True):
    cols = [np.ones(len(df))]
    if with_rank:
        cols.append(rk(df["rank"].to_numpy()))
    cols.append(rk(df.symbolPred.to_numpy()))
    if with_year:
        ys = sorted(df.yr.unique())
        for y in ys[1:]:
            cols.append((df.yr.to_numpy() == y).astype(float))
    return np.column_stack(cols)


def resid(Z, v):
    b, *_ = np.linalg.lstsq(Z, v, rcond=None)
    return v - Z @ b


def pic(x, y, Z):
    return pic_r(rk(x), rk(y), Z)


def pic_r(rx0, ry0, Z):
    rx, ry = resid(Z, rx0), resid(Z, ry0)
    d = np.sqrt((rx * rx).sum() * (ry * ry).sum())
    return float((rx * ry).sum() / d) if d > 0 else np.nan


class Boot:
    """bootstrap cum: ve 1 lan bo cum (seed RNG), dung chung cho moi chi so trong ky."""

    def __init__(self, clu):
        u, inv = np.unique(clu, return_inverse=True)
        self.u, self.inv, self.nc = u, inv, len(u)
        self.rows = [np.nonzero(inv == k)[0] for k in range(len(u))]
        rng = np.random.default_rng(RNG)
        self.draws = [rng.integers(0, len(u), len(u)) for _ in range(NB)]
        self.W = np.stack([np.bincount(d, minlength=len(u)) for d in self.draws]).astype(np.float64)

    def idx(self, b):
        return np.concatenate([self.rows[k] for k in self.draws[b]])


def ic_boot(df, xcol, BT, with_rank=True, with_year=True):
    x = df[xcol].to_numpy(float)
    ok = np.isfinite(x)
    y = df.y.to_numpy(float)
    Z = cov(df, with_rank, with_year)
    rx, ry = np.full(len(x), np.nan), np.full(len(x), np.nan)
    rx[ok], ry[ok] = rk(x[ok]), rk(y[ok])
    pt = pic_r(rx[ok], ry[ok], Z[ok]) if ok.sum() > 50 else np.nan
    bs = np.empty(NB)
    for b in range(NB):
        ii = BT.idx(b)
        ii = ii[ok[ii]]
        bs[b] = pic_r(rx[ii], ry[ii], Z[ii]) if len(ii) > 50 else np.nan
    se = float(np.nanstd(bs))
    lo, hi = np.nanpercentile(bs, [5, 95])
    return dict(ic=round(pt, 4), se=round(se, 4), ci90=[round(float(lo), 4), round(float(hi), 4)], n=int(ok.sum()),
                p2=float(2 * norm.sf(abs(pt) / se)) if se > 0 else np.nan)


def bh(p, q=0.10):
    p = np.asarray(p)
    o = np.argsort(p)
    m = len(p)
    thr = q * (np.arange(1, m + 1)) / m
    ok = p[o] <= thr
    k = np.max(np.nonzero(ok)[0]) if ok.any() else -1
    out = np.zeros(m, bool)
    if k >= 0:
        out[o[:k + 1]] = True
    return out


def holm(p, a=0.10):
    p = np.asarray(p)
    o = np.argsort(p)
    m = len(p)
    out = np.zeros(m, bool)
    for j, i in enumerate(o):
        if p[i] <= a / (m - j):
            out[i] = True
        else:
            break
    return out


def dedupe(E):
    keep = []
    rho = {}
    for c in CN + MN:
        bad = None
        for k in keep:
            ok = np.isfinite(E[c]) & np.isfinite(E[k])
            r = float(pd.Series(rk(E[c][ok])).corr(pd.Series(rk(E[k][ok])))) if ok.sum() > 100 else 0.0
            if abs(r) > 0.80:
                bad = (k, round(r, 3))
                break
        if E[c].notna().sum() < 100:
            bad = ("NaN", 0)
        if bad is None:
            keep.append(c)
        else:
            rho[c] = bad
    return keep, rho


def ecdf_score(Eref, df, cols, sign):
    S = []
    for c in cols:
        ref = np.sort(Eref[c].dropna().to_numpy())
        x = df[c].to_numpy(float)
        p = np.searchsorted(ref, x, "right") / len(ref)
        p = np.where(np.isfinite(x), p, np.nan)
        S.append(sign[c] * (p - 0.5))
    S = np.column_stack(S)
    with np.errstate(all="ignore"):
        return np.nanmean(S, axis=1)


def ml_fit(E, feats):
    import xgboost as xgb
    Z = np.column_stack([np.ones(len(E)), rk(E["rank"].to_numpy())] + [(E.yr.to_numpy() == y).astype(float) for y in sorted(E.yr.unique())[1:]])
    t = resid(Z, rk(E.y.to_numpy()))
    m = xgb.XGBRegressor(max_depth=3, n_estimators=200, learning_rate=0.05, subsample=0.8, random_state=RNG, n_jobs=4,
                         tree_method="hist")
    m.fit(E[feats].to_numpy(float), t)
    m.save_model(W + "ml.json")
    return m


def ml_pred(feats, df):
    import xgboost as xgb
    m = xgb.XGBRegressor()
    m.load_model(W + "ml.json")
    return m.predict(df[feats].to_numpy(float))


def wmean_diff(yA, cA, yB, cB, nc, Wm):
    """mean(A)-mean(B) + CI90 bootstrap cum bang trong so dem cum."""
    sA, nA = np.bincount(cA, yA, nc), np.bincount(cA, minlength=nc).astype(float)
    sB, nB = np.bincount(cB, yB, nc), np.bincount(cB, minlength=nc).astype(float)
    pt = sA.sum() / nA.sum() - sB.sum() / nB.sum()
    with np.errstate(all="ignore"):
        bs = (Wm @ sA) / (Wm @ nA) - (Wm @ sB) / (Wm @ nB)
    lo, hi = np.nanpercentile(bs, [5, 95])
    return float(pt), [float(lo), float(hi)], float(np.nanstd(bs))


# ---------------- track G ----------------
def g_load(kept_m):
    Y = pd.read_parquet("/home/ubuntu/claude_master/res1109/r5_quality/out/r5q_y.parquet", columns=["ts", "y72"])
    MK = pd.read_parquet(W + "mkt_h.parquet")
    rows = []
    for s in SEEDS:
        z = np.load(W + "g2_%s.npz" % s)
        rows.append(pd.DataFrame(dict(seed=s, ts=z["ts"], pas=z["pas"], mrq=z["mrq"])))
    G = pd.concat(rows, ignore_index=True)
    G = G.merge(Y, on="ts", how="left")
    G["y72"] *= 100.0
    j = np.searchsorted(MK.th.to_numpy(), G.ts.to_numpy(), "right") - 1
    for c in MN:
        G[c] = np.where(j >= 0, MK[c].to_numpy()[np.clip(j, 0, len(MK) - 1)], np.nan)
    G["yr"] = np.select([G.ts < YB[y + 1] for y in (2022, 2023, 2024, 2025)], [2022, 2023, 2024, 2025], 0)
    G["per"] = np.where(G.ts < YB[2024], "E", "C")
    u = np.unique(G.ts.to_numpy())
    cid = np.cumsum(np.r_[True, np.diff(u) > GAP])
    G["clu"] = cid[np.searchsorted(u, G.ts.to_numpy())] - 1
    return G


def declust(df):
    """giu phut DAU moi chuoi (<=60') theo tung seed trong tap df."""
    out = []
    for s, g in df.sort_values(["seed", "ts"]).groupby("seed"):
        t = g.ts.to_numpy()
        out.append(g[np.r_[True, np.diff(t) > GAP]])
    return pd.concat(out) if out else df.iloc[:0]


def g_eval(G, Eref, c, sign, cut, nc, Wm, per_mask):
    """tra relax (2 band) va veto cho chi bao c tren tap G[per_mask]."""
    X = G[per_mask]
    sx = sign * X[c].to_numpy(float)
    fav, adv = sx >= cut[1], sx <= cut[0]
    okx = np.isfinite(sx)
    P = X[X.pas.to_numpy()]
    Pd = declust(P[np.isfinite(P.y72)])
    res = {}
    for b in (0.85, 0.70):
        nm = (~X.pas.to_numpy()) & (X.mrq.to_numpy() >= b) & (X.mrq.to_numpy() < 1.0) & fav & okx
        A = declust(X[nm & np.isfinite(X.y72.to_numpy())])
        if len(A) < 5 or len(Pd) < 5:
            res["relax_%.2f" % b] = dict(n_nm=len(A), note="qua it")
            continue
        d, ci, se = wmean_diff(A.y72.to_numpy(), A.clu.to_numpy(), Pd.y72.to_numpy(), Pd.clu.to_numpy(), nc, Wm)
        res["relax_%.2f" % b] = dict(delta=round(d, 3), ci90=[round(ci[0], 3), round(ci[1], 3)], se=round(se, 3),
                                    y_nm_fav=round(float(A.y72.mean()), 3), y_pass=round(float(Pd.y72.mean()), 3),
                                    n_nm=len(A), n_pass=len(Pd), p_ni=float(norm.sf((d + 1.0) / se)) if se > 0 else np.nan)
    pa = X.pas.to_numpy() & okx & np.isfinite(X.y72.to_numpy())
    A = declust(X[pa & adv])
    B = declust(X[pa & ~adv])
    if len(A) >= 5 and len(B) >= 5:
        d, ci, se = wmean_diff(A.y72.to_numpy(), A.clu.to_numpy(), B.y72.to_numpy(), B.clu.to_numpy(), nc, Wm)
        res["veto"] = dict(delta=round(d, 3), ci90=[round(ci[0], 3), round(ci[1], 3)], se=round(se, 3), n_adv=len(A), n_rest=len(B),
                           p=float(norm.cdf(d / se)) if se > 0 else np.nan)
    else:
        res["veto"] = dict(n_adv=len(A), note="qua it")
    return res


def g_prepare(G, kept_m):
    E = G[G.per == "E"]
    U = declust(E[(E.pas | (E.mrq >= 0.70)) & np.isfinite(E.y72)])
    sign, cut = {}, {}
    for c in kept_m:
        ok = np.isfinite(U[c])
        r = float(pd.Series(rk(U[c][ok])).corr(pd.Series(rk(U.y72[ok]))))
        sign[c] = 1.0 if r >= 0 else -1.0
        sx = sign[c] * U[c][ok].to_numpy()
        cut[c] = [float(np.quantile(sx, 0.2)), float(np.quantile(sx, 0.8))]
    # C_ALL_M
    G["CALLM"] = ecdf_score(U, G, kept_m, sign)
    E2 = G[G.per == "E"]
    UU = declust(E2[(E2.pas | (E2.mrq >= 0.70)) & np.isfinite(E2.y72)])
    UU = UU[np.isfinite(UU.CALLM)]
    sign["CALLM"] = 1.0 if float(pd.Series(rk(UU.CALLM)).corr(pd.Series(rk(UU.y72)))) >= 0 else -1.0
    sx = sign["CALLM"] * UU.CALLM.to_numpy()
    cut["CALLM"] = [float(np.nanquantile(sx, 0.2)), float(np.nanquantile(sx, 0.8))]
    return sign, cut, U


def g_boot(G):
    nc = int(G.clu.max()) + 1
    rng = np.random.default_rng(RNG)
    Wm = np.stack([np.bincount(rng.integers(0, nc, nc), minlength=nc) for _ in range(NB)]).astype(np.float64)
    return nc, Wm


# ---------------- main ----------------
def explore():
    L = pd.read_parquet(W + "legs_x.parquet")
    E = usable(L, "E")
    Cn = usable(L, "C", need_y=False)
    log.info("EXPLORE leg %d cum %d (loai: %d)", len(E), E.clu.nunique(), int((L.per == "E").sum() - len(E)))
    keep, rho = dedupe(E)
    log.info("khu trung giu %d: %s; bo %s", len(keep), keep, rho)
    BT = Boot(E.clu.to_numpy())
    R = dict(prereg="14ed6c00", n_leg_E=len(E), n_clu_E=int(E.clu.nunique()), n_leg_C=len(Cn), n_clu_C=int(Cn.clu.nunique()),
             legs_yr={int(k): int(v) for k, v in E.groupby("yr").size().items()}, keep=keep, dropped=rho, single={})
    for c in keep:
        R["single"][c] = ic_boot(E, c, BT)
        for y in (2022, 2023):
            Ey = E[E.yr == y].reset_index(drop=True)
            x, ok = Ey[c].to_numpy(float), np.isfinite(Ey[c].to_numpy(float))
            R["single"][c]["ic_%d" % y] = round(pic(x[ok], Ey.y.to_numpy()[ok], cov(Ey, True, False)[ok]), 4)
        log.info("%s %s", c, R["single"][c])
    ps = [R["single"][c]["p2"] for c in keep]
    fdr = bh(ps)
    for c, f in zip(keep, fdr):
        R["single"][c]["fdr"] = bool(f)
    keepC = [c for c in keep if c.startswith("C")]
    sign = {c: (1.0 if R["single"][c]["ic"] >= 0 else -1.0) for c in keep}
    top5 = sorted(keepC, key=lambda c: -abs(R["single"][c]["ic"]))[:5]
    E["CALL"] = ecdf_score(E, E, keepC, sign)
    E["CTOP5"] = ecdf_score(E, E, top5, sign)
    feats = keep + ["rank", "symbolPred"]
    ml_fit(E, feats)
    E["ML"] = ml_pred(feats, E)
    for c in ("CALL", "CTOP5", "ML"):
        R["single"][c] = ic_boot(E, c, BT)
        R["single"][c]["note"] = "in-sample EXPLORE (chi bao, khong kiem)"
        log.info("%s %s", c, R["single"][c])
    # repro check
    BT2 = Boot(E.clu.to_numpy())
    chk = ic_boot(E, keep[0], BT2)
    assert chk == {k: v for k, v in R["single"][keep[0]].items() if k in chk}, "bootstrap khong tai lap"
    surv = sorted([c for c in keep if R["single"][c]["fdr"]], key=lambda c: -abs(R["single"][c]["ic"]))[:3]
    closeS = (len(surv) == 0) and (R["single"]["CALL"]["p2"] >= 0.20)
    cands = [] if closeS else surv + ["CALL", "CTOP5", "ML"]
    # MDE80 (truoc khi doc Y CONFIRM): chi dung so cum CONFIRM
    se_med = float(np.median([R["single"][c]["se"] for c in keep]))
    seC = se_med * np.sqrt(R["n_clu_E"] / R["n_clu_C"])
    m = max(1, len(cands))
    R["mde80"] = dict(se_E_median=round(se_med, 4), se_C=round(seC, 4), mde_unadj=round((norm.ppf(0.90) + norm.ppf(0.80)) * seC, 4),
                      mde_holm=round((norm.ppf(1 - 0.10 / m) + norm.ppf(0.80)) * seC, 4), m=m)
    R["mde80"]["warn"] = bool(R["mde80"]["mde_unadj"] > 0.08)
    # seed 42 mo ta
    E42 = E[E.seed == 42].reset_index(drop=True)
    BT42 = Boot(E42.clu.to_numpy())
    R["seed42_E"] = {c: ic_boot(E42, c, BT42)["ic"] for c in cands}
    # cutpoint ngu phan vi xau (EXPLORE)
    cutS = {}
    sgn_all = dict(sign)
    for c in ("CALL", "CTOP5", "ML"):
        sgn_all[c] = 1.0 if R["single"][c]["ic"] >= 0 else -1.0
    for c in cands:
        v = E[c].dropna().to_numpy()
        cutS[c] = float(np.quantile(v, 0.2)) if sgn_all[c] > 0 else float(np.quantile(v, 0.8))
    # ---- track G ----
    kept_m = [c for c in keep if c.startswith("M")]
    G = g_load(kept_m)
    sg, cutg, U = g_prepare(G, kept_m)
    nc, Wm = g_boot(G)
    RG = dict(n_min=dict(G[G.per == "E"].groupby("pas").size().rename(lambda b: "pass" if b else "nm70").to_dict()),
              n_clu=nc, sign=sg, cut=cutg, ind={})
    for c in kept_m + ["CALLM"]:
        RG["ind"][c] = g_eval(G, U, c, sg[c], cutg[c], nc, Wm, (G.per == "E").to_numpy())
        log.info("G %s %s", c, RG["ind"][c])
    gc = []
    for c, r in RG["ind"].items():
        a, b = r.get("relax_0.85", {}), r.get("relax_0.70", {})
        if "delta" in a and "delta" in b and min(a["delta"], b["delta"]) >= 0 and a["ci90"][0] > -1 and b["ci90"][0] > -1 \
                and a["y_nm_fav"] > 0 and b["y_nm_fav"] > 0:
            gc.append(("relax", c, min(a["delta"], b["delta"])))
        v = r.get("veto", {})
        if "delta" in v and v["delta"] < 0 and v["ci90"][1] < 0:
            gc.append(("veto", c, abs(v["delta"])))
    gc = sorted(gc, key=lambda t: -t[2])[:2]
    RG["cands"] = [[k, c] for k, c, _ in gc]
    R["G"] = RG
    sel = dict(prereg="14ed6c00", keep=keep, sign=sgn_all, top5=top5, feats=feats, closeS=closeS, candS=cands, cutS=cutS,
               mde80=R["mde80"], G=dict(kept_m=kept_m, sign=sg, cut=cutg, cands=RG["cands"]))
    json.dump(R, open(W + "explore.json", "w"), indent=1, default=float)
    json.dump(sel, open(W + "selection.json", "w"), indent=1, default=float)
    log.info("SELECTION %s", json.dumps(sel, default=float))


def s_eval_period(L, per, c, sgn, cut, years, with_rank=True):
    D = usable(L, per)
    BT = Boot(D.clu.to_numpy())
    r = ic_boot(D, c, BT, with_rank, True)
    r["p1"] = float(norm.sf(sgn * r["ic"] / r["se"])) if r["se"] > 0 else np.nan
    for y in years:
        Dy = D[D.yr == y].reset_index(drop=True)
        x, ok = Dy[c].to_numpy(float), np.isfinite(Dy[c].to_numpy(float))
        r["ic_%d" % y] = round(pic(x[ok], Dy.y.to_numpy()[ok], cov(Dy, with_rank, False)[ok]), 4)
    x = D[c].to_numpy(float)
    ok = np.isfinite(x)
    bad = (x <= cut) if sgn > 0 else (x >= cut)
    bad &= ok
    keepm = ok & ~bad
    cl = np.unique(D.clu.to_numpy(), return_inverse=True)[1]
    d, ci, se = wmean_diff(D.y.to_numpy()[bad], cl[bad], D.y.to_numpy()[keepm], cl[keepm], BT.nc, BT.W)
    r["veto"] = dict(n_bad=int(bad.sum()), n_keep=int(keepm.sum()), d=round(d, 3), ci90=[round(ci[0], 3), round(ci[1], 3)],
                     mean_bad=round(float(D.y.to_numpy()[bad].mean()), 3), mean_keep=round(float(D.y.to_numpy()[keepm].mean()), 3))
    for y in years:
        my = D.yr.to_numpy() == y
        r["veto"]["sum_pnl_bad_%d" % y] = round(float(D.pnl.to_numpy()[bad & my].sum()), 1)
        r["veto"]["sum_pnl_keep_%d" % y] = round(float(D.pnl.to_numpy()[keepm & my].sum()), 1)
    r["n_clu"] = int(D.clu.nunique())
    return r


def confirm():
    sel = json.load(open(W + "selection.json"))
    L = pd.read_parquet(W + "legs_x.parquet")
    E = usable(L, "E")
    keep, sgn, top5, feats = sel["keep"], sel["sign"], sel["top5"], sel["feats"]
    keepC = [c for c in keep if c.startswith("C")]
    L["CALL"] = ecdf_score(E, L, keepC, sgn)
    L["CTOP5"] = ecdf_score(E, L, top5, sgn)
    L["ML"] = ml_pred(feats, L)
    R = dict(prereg="14ed6c00", S={}, G={}, HO={})
    cands = sel["candS"]
    for c in cands:
        R["S"][c] = s_eval_period(L, "C", c, sgn[c], sel["cutS"][c], (2024, 2025))
        D42 = usable(L, "C")
        D42 = D42[D42.seed == 42].reset_index(drop=True)
        R["S"][c]["seed42_ic"] = ic_boot(D42, c, Boot(D42.clu.to_numpy()))["ic"]
        log.info("CONFIRM %s %s", c, R["S"][c])
    if cands:
        hp = holm([R["S"][c]["p1"] for c in cands])
        for c, h in zip(cands, hp):
            r = R["S"][c]
            s = sgn[c]
            c1 = (np.sign(r["ic"]) == s) and (r["ci90"][0] > 0 if s > 0 else r["ci90"][1] < 0) and bool(h)
            c2 = (np.sign(r["ic_2024"]) == s) and (np.sign(r["ic_2025"]) == s)
            v = r["veto"]
            c3 = (v["d"] < 0) and (v["ci90"][1] < 0) and v["sum_pnl_bad_2024"] <= 0 and v["sum_pnl_bad_2025"] <= 0
            r.update(holm=bool(h), crit1=bool(c1), crit2=bool(c2), crit3=bool(c3), PASS=bool(c1 and c2 and c3))
    # HO mo ta (khong co hang S1 -> khu theo diem S1)
    for c in cands:
        try:
            R["HO"][c] = s_eval_period(L, "H", c, sgn[c], sel["cutS"][c], (2026,), with_rank=False)
        except Exception as e:  # noqa
            R["HO"][c] = dict(err=str(e)[:200])
    # track G
    if sel["G"]["cands"]:
        kept_m = sel["G"]["kept_m"]
        G = g_load(kept_m)
        sg, cutg, U = g_prepare(G, kept_m)
        assert all(abs(sg[k] - sel["G"]["sign"][k]) < 1e-9 for k in sg), "dau G lech EXPLORE"
        nc, Wm = g_boot(G)
        for kind, c in sel["G"]["cands"]:
            out = dict(all=g_eval(G, U, c, sg[c], cutg[c], nc, Wm, (G.per == "C").to_numpy()))
            for y in (2024, 2025):
                out[str(y)] = g_eval(G, U, c, sg[c], cutg[c], nc, Wm, (G.yr == y).to_numpy())
            R["G"]["%s:%s" % (kind, c)] = out
            log.info("G CONFIRM %s %s %s", kind, c, out["all"])
        # Holm m=14 (gia thuyet khong kiem = p 1)
        hyp = []
        for key, out in R["G"].items():
            kind, c = key.split(":")
            a = out["all"]
            if kind == "relax":
                hyp += [(key, b, a[b].get("p_ni", 1.0)) for b in ("relax_0.85", "relax_0.70")]
            else:
                hyp.append((key, "veto", a["veto"].get("p", 1.0)))
        pv = [h[2] if h[2] == h[2] else 1.0 for h in hyp] + [1.0] * (14 - len(hyp))
        rej = holm(pv)[:len(hyp)]
        rejd = {(h[0], h[1]): bool(r) for h, r in zip(hyp, rej)}
        for key, out in R["G"].items():
            kind, c = key.split(":")
            a = out["all"]
            if kind == "relax":
                ok = rejd[(key, "relax_0.85")] and rejd[(key, "relax_0.70")]
                cond = all(("delta" in a[b]) and a[b]["delta"] >= 0 and a[b]["ci90"][0] > -1 and a[b]["y_nm_fav"] > 0 for b in ("relax_0.85", "relax_0.70"))
                yrs = all(("delta" in out[y][b]) and out[y][b]["delta"] >= 0 for y in ("2024", "2025") for b in ("relax_0.85", "relax_0.70"))
            else:
                v = a["veto"]
                ok = rejd[(key, "veto")]
                cond = ("delta" in v) and v["delta"] < 0 and v["ci90"][1] < 0
                yrs = all(("delta" in out[y]["veto"]) and out[y]["veto"]["delta"] < 0 for y in ("2024", "2025"))
            out["verdict"] = dict(holm=bool(ok), cond=bool(cond), years=bool(yrs), PASS=bool(ok and cond and yrs))
    json.dump(R, open(W + "confirm.json", "w"), indent=1, default=float)
    log.info("CONFIRM XONG")


if __name__ == "__main__":
    {"explore": explore, "confirm": confirm}[sys.argv[1]]()
