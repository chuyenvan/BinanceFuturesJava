#!/usr/bin/env python3
"""leadlag_add1.py -- PREREG_LEADLAG_EXIST_ADD1 (commit d3683a72): H1c + H2 + V3, ap luat par.D.

H1c: IC_t cua H1 (tinh lai bang chinh ham leadlag_exist.py @9e63a754, khong sua) gioi han tap gio "BTC dao chieu"
     sign(r_BTC(t,t+h]) != sign(r_BTC(t-k,t]) (bo gio r_BTC = 0); bao kem tap "cung chieu". Bootstrap/CI no nhu H1.
H2:  ledger chan EXEC khoi phuc (exec_legs.py -> legs.pkl md5 c55224e7, close_M = close nen 1m mo tai s_ms tu kline
     data.binance.vision qua exec_fetch.py kl, dung cach exec_measure.run_sym lay cM). g_k tai gio dong gan nhat <= t_dec,
     tercile theo nam; Delta = mean ret_h(top) - mean ret_h(bottom), ret_h = log(close_1H(ceil(t_dec+h)) / close_M).
     Chinh k=3h h=4h; phu k=1h h=1h (khong quyet). CI95 block bootstrap theo ngay (10 ngay, 2000, seed 20261013).
V3:  so chan ghep duoc (close_M + g + ret) >= 95 % cua 23 654.
0 sim, 0 Java, 0 Binance REST, 0 du lieu 2026, 0 kho backcast.

Usage: python3 leadlag_add1.py OUT.json LEDGER.csv.gz          (lan cham)
       python3 leadlag_add1.py OUT.json LEDGER.csv.gz smoke    (CHI DE DEBUG: 2022-01)
"""
import glob
import hashlib
import json
import logging
import math
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import leadlag_exist as L  # noqa: E402  (scorer H1 @9e63a754)

log = logging.getLogger("leadlag_add1")
PREREG_ADD = "d3683a72"
LH2 = "/home/ubuntu/claude_master/1013/ll_h2"
LEGS = LH2 + "/legs.pkl"
LEGS_MD5 = "c55224e7bbc82cf5be83e9c2217d6b8e"
N_LEGS = 23654
N_EV = 5284
V3_MIN = 0.95
PEN, CRASH = 0.01675, -0.01
TZ = 7 * L.H
H2_MAIN = (3, 4)
H2_SUB = (1, 1)
DELTA_MIN = 0.003           # +0,30 % (don vi log-return)
SMOKE = len(sys.argv) > 3 and sys.argv[3] == "smoke"   # CHI DE DEBUG: t / chan trong 2022-01
JSON1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../docs/result/leadlag_exist.json")
JSON1_MD5 = "ea16fd5cf8237ba3edd32aa22379c1d3"   # lan cham 1 (H1) -- doi chieu tai lap


def md5f(p):
    return L.md5f(p)


# ---------------- H1c ----------------
def run_h1c(lp, excl):
    T = lp.shape[0]
    rows = np.arange((L.T_EVAL0 - L.T_GRID0) // L.H, T - L.POST)
    if SMOKE:
        rows = rows[L.T_GRID0 + rows * L.H < L.T_SMOKE1]
    univ, sig, R = L.prep_common(lp, rows, excl)
    lpB = lp[:, L.BTC].copy()
    real, _ = L.core(lp, R, lpB, rows, univ, sig, samp=False)
    del univ, sig, R
    repro = {}
    out = {"rev": {}, "same": {}}
    nh = {}
    for (k, h), v in real.items():
        key = "k%d_h%d" % (k, h)
        repro[key] = float(np.nanmean(v["ic"][np.isfinite(v["ic"])]))
        rbk = lpB[rows] - lpB[rows - k]
        rbh = lpB[rows + h] - lpB[rows]
        sk, sh = np.sign(rbk), np.sign(rbh)
        valid = np.isfinite(rbk) & np.isfinite(rbh) & (sk != 0) & (sh != 0)
        sets = dict(rev=valid & (sk != sh), same=valid & (sk == sh))
        for nm, m in sets.items():
            ic = np.where(m, v["ic"], np.nan)
            ok = np.isfinite(ic)
            sub = {(k, h): dict(ic=ic, cnt=v["cnt"], ncoin=-1, coinhours=int(v["cnt"][ok].sum()))}
            out[nm][key] = L.summarize(sub, rows)[key]
            nh["%s_%s" % (nm, key)] = int(ok.sum())
        nh["btc0_or_nan_%s" % key] = int((~valid & np.isfinite(v["ic"])).sum())
        log.info("H1c %s: rev mean %.5f lo_dec %.5f (%d gio) | same mean %.5f (%d gio)", key,
                 out["rev"][key]["full"]["mean"], out["rev"][key]["full"]["lo_dec"], nh["rev_" + key],
                 out["same"][key]["full"]["mean"], nh["same_" + key])
    return out, repro, nh


# ---------------- H2 ----------------
def load_cm(ev):
    """cM/oM nhu exec_measure.run_sym: nen 1m mo tai s_ms trong kl/{sym}USDT_*.npz (ghep, sap xep stable)."""
    rec = []
    for sym, g in ev.groupby("sym", sort=True):
        fs = sorted(glob.glob(LH2 + "/kl/%sUSDT_*.npz" % sym))
        if not fs:
            for e in g.itertuples():
                rec.append((e.eid, "nokl", np.nan, np.nan))
            continue
        Z = [np.load(f) for f in fs]
        kt = np.concatenate([z["t"] for z in Z])
        kx = np.concatenate([z["x"] for z in Z])
        o = np.argsort(kt, kind="stable")
        kt, kx = kt[o], kx[o]
        for e in g.itertuples():
            s = int(e.s_ms)
            im = int(np.searchsorted(kt, s))
            if im >= len(kt) or kt[im] != s:
                rec.append((e.eid, "nobarM", np.nan, np.nan))
            else:
                rec.append((e.eid, "ok", float(kx[im, 0]), float(kx[im, 3])))
    return pd.DataFrame(rec, columns=["eid", "cm_st", "oM", "cM"])


def g_at(lp, rows, cols, k):
    """g_k (dinh nghia par.2, giong core cua leadlag_exist) tai (row, col) tung diem."""
    R = L.ret1(lp)
    rb = R[:, L.BTC]
    ur, inv = np.unique(rows, return_inverse=True)
    V = np.isfinite(R) & np.isfinite(rb)[:, None]
    x = np.where(V, rb[:, None], 0.0)
    y = np.where(V, R, 0.0)
    n = L.wsum(V.astype(np.float64), ur, -(L.W_BETA - 1), -k)
    sx = L.wsum(x, ur, -(L.W_BETA - 1), -k)
    sy = L.wsum(y, ur, -(L.W_BETA - 1), -k)
    sxx = L.wsum(x * x, ur, -(L.W_BETA - 1), -k)
    sxy = L.wsum(x * y, ur, -(L.W_BETA - 1), -k)
    del x, y, V
    beta = (sxy - sx * sy / n) / (sxx - sx * sx / n)
    beta[~(n >= L.MIN_BETA)] = np.nan
    Vs = np.isfinite(R)
    ys = np.where(Vs, R, 0.0)
    ns = L.wsum(Vs.astype(np.float64), ur, -(L.W_SIG - 1), 0)
    s1 = L.wsum(ys, ur, -(L.W_SIG - 1), 0)
    s2 = L.wsum(ys * ys, ur, -(L.W_SIG - 1), 0)
    del ys, Vs, R
    sig = np.sqrt(np.maximum((s2 - s1 * s1 / ns) / (ns - 1), 0.0))
    sig[(ns < L.MIN_SIG) | ~(sig > 0)] = np.nan
    b = beta[inv, cols]
    sg = sig[inv, cols]
    rik = lp[rows, cols] - lp[rows - k, cols]
    rbk = lp[rows, L.BTC] - lp[rows - k, L.BTC]
    return (b * rbk - rik) / sg, b, sg


def mbb_delta(day, ret, top, bot):
    D = int(day.max()) + 1
    sT = np.bincount(day[top], weights=ret[top], minlength=D)
    cT = np.bincount(day[top], minlength=D).astype(np.float64)
    sB = np.bincount(day[bot], weights=ret[bot], minlength=D)
    cB = np.bincount(day[bot], minlength=D).astype(np.float64)
    m = float(sT.sum() / cT.sum() - sB.sum() / cB.sum())
    rng = np.random.default_rng(L.SEED)
    nb = int(math.ceil(D / L.BLOCK))
    st = rng.integers(0, D - L.BLOCK + 1, size=(L.NREP, nb))
    idx = (st[:, :, None] + np.arange(L.BLOCK)[None, None, :]).reshape(L.NREP, -1)[:, :D]
    stat = sT[idx].sum(1) / np.maximum(cT[idx].sum(1), 1e-12) - sB[idx].sum(1) / np.maximum(cB[idx].sum(1), 1e-12)
    sd = float(np.std(stat, ddof=1))
    plo, phi = (float(v) for v in np.percentile(stat, [2.5, 97.5]))
    r = dict(delta=m, sd=sd, lo=m - 1.96 * sd, hi=m + 1.96 * sd, plo=plo, phi=phi, n_days=D)
    r["lo_dec"] = min(r["lo"], r["plo"])
    return r


def run_h2(lp, names, ledger_out):
    assert md5f(LEGS) == LEGS_MD5, "legs.pkl md5 sai"
    d = pd.read_pickle(LEGS)
    Lg, ev = d["L"].copy(), d["ev"]
    assert len(Lg) == N_LEGS and len(ev) == N_EV, (len(Lg), len(ev))
    if SMOKE:
        ev = ev[ev["s_ms"] < L.T_SMOKE1]
        Lg = Lg[Lg["s_ms"] < L.T_SMOKE1].reset_index(drop=True)
    cm = load_cm(ev)
    Lg = Lg.merge(cm, on="eid", how="left")
    Lg["br"] = Lg["cM"] / Lg["oM"] - 1.0
    Lg["ent_ok"] = (np.abs(Lg["entry"] / (Lg["cM"] * (1 + PEN * (Lg["br"] <= CRASH))) - 1) < 1e-6)
    inv = {v: k for k, v in names.items()}
    Lg["sid"] = [inv.get(s + "USDT", -1) for s in Lg["sym"]]
    t_dec = Lg["t_dec"].to_numpy(np.int64)
    tstar = t_dec // L.H * L.H
    Lg["t_star"] = tstar
    row = (tstar - L.T_GRID0) // L.H
    sid = Lg["sid"].to_numpy()
    okc = (Lg["cm_st"] == "ok").to_numpy() & (sid >= 0)
    Lg["year07"] = pd.to_datetime(Lg["s_ms"] + TZ, unit="ms").dt.year
    dayu = t_dec // L.DAY
    dayi = (dayu - dayu.min()).astype(np.int64)
    res = {}
    for (k, h) in (H2_MAIN, H2_SUB):
        key = "k%d_h%d" % (k, h)
        g = np.full(len(Lg), np.nan)
        b = np.full(len(Lg), np.nan)
        ii = np.flatnonzero(okc)
        g[ii], b[ii], _ = g_at(lp, row[ii], sid[ii], k)
        te = -(-(t_dec + h * L.H) // L.H) * L.H
        ret = np.full(len(Lg), np.nan)
        okte = okc & (te <= L.T_END)
        jj = np.flatnonzero(okte)
        ret[jj] = lp[(te[jj] - L.T_GRID0) // L.H, sid[jj]] - np.log(Lg["cM"].to_numpy()[jj])
        match = np.isfinite(g) & np.isfinite(ret) & okc
        Lg["g_" + key], Lg["ret_" + key], Lg["match_" + key] = g, ret, match
        terc = np.full(len(Lg), -1)
        yrs = Lg["year07"].to_numpy()
        cuts = {}
        for y in sorted(set(yrs[match].tolist())):
            m = match & (yrs == y)
            q1, q2 = np.quantile(g[m], [1 / 3, 2 / 3])
            cuts[str(y)] = [float(q1), float(q2)]
            terc[m & (g <= q1)] = 0
            terc[m & (g > q1) & (g <= q2)] = 1
            terc[m & (g > q2)] = 2
        Lg["terc_" + key] = terc
        top, bot, mid = terc == 2, terc == 0, terc == 1
        r = dict(boot=mbb_delta(dayi, np.nan_to_num(ret), top, bot), cuts=cuts,
                 n=dict(bottom=int(bot.sum()), mid=int(mid.sum()), top=int(top.sum()), matched=int(match.sum())),
                 mean_ret=dict(bottom=float(ret[bot].mean()), mid=float(ret[mid].mean()), top=float(ret[top].mean())),
                 n_events_matched=int(Lg.loc[match, "eid"].nunique()), years={})
        for y in sorted(set(yrs[match].tolist())):
            my = yrs == y
            r["years"][str(y)] = dict(delta=float(ret[top & my].mean() - ret[bot & my].mean()),
                                      n_top=int((top & my).sum()), n_bot=int((bot & my).sum()))
        miss = dict(nosym=int((sid < 0).sum()), nokl=int((Lg["cm_st"] == "nokl").sum()),
                    nobarM=int((Lg["cm_st"] == "nobarM").sum()), g_nan=int((okc & ~np.isfinite(g)).sum()),
                    te_after_end=int((okc & (te > L.T_END)).sum()), ret_nan=int((okte & ~np.isfinite(ret)).sum()))
        r["missing"] = miss
        res[key] = r
        log.info("H2 %s: Delta %.5f CI [%.5f, %.5f] pct [%.5f, %.5f] n %s mean %s miss %s", key, r["boot"]["delta"],
                 r["boot"]["lo"], r["boot"]["hi"], r["boot"]["plo"], r["boot"]["phi"], r["n"], r["mean_ret"], miss)
    cols = ["seed", "row", "eid", "sym", "level", "s_ms", "t_dec", "t_star", "year07", "entry", "cm_st", "oM", "cM", "br",
            "ent_ok", "sid"] + [c + "_" + kk for kk in ("k3_h4", "k1_h1") for c in ("g", "ret", "match", "terc")]
    Lg[cols].to_csv(ledger_out, index=False, compression="gzip", float_format="%.10g")
    ent = dict(n_ok=int(Lg["ent_ok"].sum()), n_cm=int((Lg["cm_st"] == "ok").sum()),
               cm_st=Lg["cm_st"].value_counts(dropna=False).to_dict())
    nm = res["k%d_h%d" % H2_MAIN]["n"]["matched"]
    v3 = dict(matched=nm, total=N_LEGS, frac=nm / N_LEGS, ok=bool(nm >= V3_MIN * N_LEGS),
              missing=res["k%d_h%d" % H2_MAIN]["missing"])
    return res, v3, ent


def decide(j1, repro, h1c, h2, v3):
    k = "k%d_h%d" % L.MAIN
    c_h1 = bool(j1["decision"]["h1_pass"])
    c_repro = all(abs(repro[x] - j1["h1"][x]["full"]["mean"]) < 1e-9 for x in repro)
    rv = h1c["rev"][k]["full"]
    c_h1c = bool(rv["mean"] > 0 and rv["lo_dec"] > 0)
    b = h2["k%d_h%d" % H2_MAIN]["boot"]
    c_h2 = bool(b["delta"] > DELTA_MIN and b["lo_dec"] > 0)
    c_v3 = bool(v3["ok"])
    go = c_h1 and c_repro and c_h1c and c_h2 and c_v3
    return dict(c_h1=c_h1, c_h1_repro=c_repro, c_h1c=c_h1c, c_h2=c_h2, c_v3=c_v3, verdict="GO" if go else "DONG",
                h1c_main=dict(mean=rv["mean"], lo_infl=rv["lo_infl"], plo_infl=rv["plo_infl"], lo_dec=rv["lo_dec"]),
                h2_main=dict(delta=b["delta"], lo=b["lo"], plo=b["plo"], lo_dec=b["lo_dec"]))


def main():
    t0 = time.time()
    outp, ledger_out = sys.argv[1], sys.argv[2]
    assert md5f(JSON1) == JSON1_MD5, "json lan cham 1 sai md5"
    with open(JSON1) as f:
        j1 = json.load(f)
    lp, excl, names, _, meta = L.load()
    h1c, repro, nh = run_h1c(lp, excl)
    log.info("H1 tai lap: %s", repro)
    h2, v3, ent = run_h2(lp, names, ledger_out)
    dec = decide(j1, repro, h1c, h2, v3)
    js = dict(prereg="e0e7bd54", addendum=PREREG_ADD, script="research/analysis/leadlag_add1.py",
              h1_scorer="research/analysis/leadlag_exist.py@9e63a754", json1_md5=JSON1_MD5,
              data=dict(bin_md5=md5f(L.BIN), map_md5=md5f(L.MAP), legs_pkl=LEGS, legs_md5=LEGS_MD5,
                        n_legs=N_LEGS, n_events=N_EV, excluded=meta["excluded"]),
              h1_repro=repro, h1c=h1c, h1c_hours=nh, h2=h2, v3=v3, entry_check=ent,
              ledger=dict(path=os.path.basename(ledger_out), md5=md5f(ledger_out)),
              decision=dec, runtime_s=round(time.time() - t0, 1))
    with open(outp, "w") as f:
        json.dump(js, f, indent=1, sort_keys=True, default=float)
    log.info("ghi %s md5 %s ledger md5 %s; V3 %s; quyet dinh %s; %.0fs", outp, md5f(outp), js["ledger"]["md5"], v3,
             dec, time.time() - t0)


if __name__ == "__main__":
    main()
