#!/usr/bin/env python3
"""GATE_BAGFIX_NULL (Pha C chuong trinh GATE). Pre-reg docs/prereg/PREREG_GATE_BAGFIX_NULL.md (chot TRUOC).

Arm: BAG8M (quantile-map TB p15 tho 8 seed ve phan phoi p15 seed 42 tren DEV), RBAG8 (quantile-map TB rank-pct
8 seed), NULL1..NULL4 (hoan vi khoi 30 ngay p15 goc, rng 1..4; nhu NULLB cu). So voi A1 + dai 8 seed (GATE_SEEDBAND)
+ phan phoi 5 null (NULLB cu + 4 moi).
Usage: python3 gate_bagfix_null_driver.py gen [ARM..] | g0 | upload ARM.. | dsstatus | submit ARM.. --code-sha SHA
       | status | fetch ARM.. | parity | score --workers 3 | df
"""
import argparse
import json
import logging
import math
import os
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
HERE = os.path.join(REPO, "research/analysis")
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
import gate_seedband_driver as GSB  # noqa: E402  (import -> GA.D = gsb; ghi de ben duoi)

GA = GSB.GA
log = logging.getLogger("gbn")
D = "/home/ubuntu/claude_master/1004/gbn"
GSB_D = "/home/ubuntu/claude_master/1004/gsb"
GSB.D = D
GA.D = D                                    # pred_*/, ds_*/, g1.json, parity.json cua vong nay
NULL_SEEDS = [1, 2, 3, 4]
NULLS_NEW = ["NULL%d" % k for k in NULL_SEEDS]
ARMS = ["BAG8M", "RBAG8"] + NULLS_NEW
TAG_NEW = {a: "gbn-" + a.lower() for a in ARMS}
DSN_NEW = {a: "gate-bn-" + a.lower() for a in ARMS}
TAG = dict(GSB.TAG)                         # A1, S7, S13.., BAG8, NULLB (vong truoc)
TAG.update(TAG_NEW)
GA.TAG.update(TAG_NEW)
GA.DSN.update(DSN_NEW)
GA.ARMS = ARMS                              # GA.parity / GA.g1 lap tren GA.ARMS
BAND = list(GSB.BAND)                       # A1, S7, S13, S21, S99, S123, S777, S2024
OLD = BAND + ["BAG8", "NULLB"]
NULL_ALL = ["NULLB"] + NULLS_NEW
BAGS = ["BAG8M", "RBAG8"]
K_INFL = 6
INFL = math.sqrt(2.0 * math.log(K_INFL))
N_DEV_WANT = 2_500_260 - 420
JSON_OUT = os.path.join(REPO, "docs/result/gate_bagfix_null.json")
GSB_MTM = GSB_D + "/mtm.json"
W23 = pd.Timestamp("2022-12-31")
SEED_ORDER = [42, 7, 13, 21, 99, 123, 777, 2024]   # dung thu tu cong cua GSB.bag
disk = GSB.disk
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)


def seed_srcs():
    out = [(42, GA.PRED0, GA.PRED0_MD5), (7, GSB.SEED7_PRED, GSB.SEED7_PRED_MD5)]
    for s in SEED_ORDER[2:]:
        m = json.load(open(GSB_D + "/pred_S%d/meta.json" % s))
        out.append((s, GSB_D + "/pred_S%d/pred.bin" % s, m["md5"]))
    return out


def dev_idx(ts):
    idx = np.where(ts < GA.SEAL)[0]
    assert idx[-1] == len(idx) - 1, "DEV khong phai tien to lien tuc"
    assert len(idx) == N_DEV_WANT, len(idx)
    return idx


def qmap(x, p0, idx):
    """Anh xa don dieu (= GA.gen nhanh MAPPED, gioi han DEV): hoan vi tap gia tri p0[DEV] theo thu tu x[DEV]."""
    y = p0.copy()
    order = idx[np.argsort(x[idx], kind="stable")]
    y[order] = np.sort(p0[idx])
    return y


def write_pred(arm, raw, a0, p15, extra):
    p15 = np.asarray(p15, np.float32)
    assert p15.shape == (len(a0),) and np.isfinite(p15).all()
    b = a0.copy()
    b["p15"] = p15.astype(">f4")
    out_dir = D + "/pred_%s" % arm
    os.makedirs(out_dir, exist_ok=True)
    p = out_dir + "/pred.bin"
    with open(p, "wb") as f:
        f.write(raw[:4])
        f.write(b.tobytes())
    md5 = GA.md5f(p)
    meta = dict(arm=arm, md5=md5, n=int(len(b)), **extra)
    json.dump(meta, open(out_dir + "/meta.json", "w"), indent=1)
    log.info("PRED %s -> %s md5=%s n=%d", arm, p, md5, len(b))
    return meta


def gen(a):
    arms = a.arms or ARMS
    for x in arms:
        assert x in ARMS, x
    disk("truoc gen")
    raw, a0 = GA.read_pred()
    assert GA.md5f(GA.PRED0) == GA.PRED0_MD5
    ts = a0["ts"].astype(np.int64)
    assert (np.diff(ts) > 0).all()
    p0 = a0["p15"].astype(np.float32)
    idx = dev_idx(ts)
    if any(x in BAGS for x in arms):
        P, comps = {}, {}
        for s, p, want in seed_srcs():
            assert GA.md5f(p) == want, (s, p)
            _, b = GA.read_pred(p)
            assert (b["ts"] == a0["ts"]).all()
            P[s], comps[str(s)] = b["p15"].astype(np.float64), want
        assert list(P) == SEED_ORDER
        if "BAG8M" in arms:
            x = np.zeros(len(p0))
            for s in SEED_ORDER:
                x += P[s]
            x /= 8.0
            _, ob = GA.read_pred(GSB_D + "/pred_BAG8/pred.bin")     # kiem: x float32 == BAG8 cu (chi bao cao)
            same = bool((x.astype(np.float32) == ob["p15"].astype(np.float32)).all())
            y = qmap(x, p0, idx)
            sp = float(pd.Series(x[idx]).corr(pd.Series(p0[idx].astype(np.float64)), method="spearman"))
            log.info("BAG8M x==BAG8cu(float32) %s spearman(x,p0)_DEV %.5f", same, sp)
            write_pred("BAG8M", raw, a0, y, dict(mapped=True, method="QM(mean p15 tho 8 seed)", n_dev=len(idx),
                                                 components=comps, x_eq_bag8_old=same, spearman_x_p0_dev=sp))
            del x, y
        if "RBAG8" in arms:
            r = np.zeros(len(p0))
            for s in SEED_ORDER:
                r[idx] += pd.Series(P[s][idx]).rank(method="average", pct=True).to_numpy()
            r /= 8.0
            y = qmap(r, p0, idx)
            sp = float(pd.Series(r[idx]).corr(pd.Series(p0[idx].astype(np.float64)), method="spearman"))
            log.info("RBAG8 spearman(x,p0)_DEV %.5f", sp)
            write_pred("RBAG8", raw, a0, y, dict(mapped=True, method="QM(mean rank-pct 8 seed, DEV)",
                                                 n_dev=len(idx), components=comps, spearman_x_p0_dev=sp))
            del r, y
        del P
    for arm in [x for x in arms if x in NULLS_NEW]:
        k = int(arm[4:])
        blk = (ts[idx] - ts[idx[0]]) // GSB.BLOCK_MS
        nb = int(blk.max()) + 1
        perm = np.random.default_rng(k).permutation(nb)
        vals = np.concatenate([p0[idx][blk == j] for j in perm])
        assert len(vals) == len(idx)
        y = p0.copy()
        y[idx] = vals
        sizes = np.bincount(blk, minlength=nb)
        log.info("%s rng=%d n_khoi=%d perm[:10]=%s corr(y,p0)=%.4f", arm, k, nb, perm[:10].tolist(),
                 float(np.corrcoef(y[idx], p0[idx])[0, 1]))
        write_pred(arm, raw, a0, y, dict(mapped=False, method="hoan vi khoi 30 ngay (nhu NULLB cu)", seed=k,
                                         n_blocks=nb, perm=perm.tolist(), block_minutes=sizes.tolist()))
    disk("sau gen")


def g0(a=None):
    res = GA.g1(ARMS)                       # format + spot 3 moc + spearman vs goc -> D/g1.json
    _, a0 = GA.read_pred()
    p0 = a0["p15"].astype(np.float32)
    idx = dev_idx(a0["ts"].astype(np.int64))
    q = np.arange(10, 100, 10)
    s0 = np.sort(p0[idx])
    dec0 = np.percentile(p0[idx].astype(np.float64), q)
    out = {}
    for arm in ARMS:
        if arm not in res:
            continue
        _, b = GA.read_pred(D + "/pred_%s/pred.bin" % arm)
        y = b["p15"].astype(np.float32)
        dec = np.percentile(y[idx].astype(np.float64), q)
        c = dict(fmt=res[arm]["ok"], multiset_dev=bool(np.array_equal(np.sort(y[idx]), s0)),
                 tail2026_eq_p0=bool(np.array_equal(y[len(idx):], p0[len(idx):])),
                 decile_maxdiff_le_1e6=bool(np.abs(dec - dec0).max() <= 1e-6))
        out[arm] = dict(ok=all(c.values()), checks=c, md5=res[arm]["md5"], spot=res[arm]["spot"],
                        spearman_vs_orig=res[arm]["spearman_vs_orig"], decile=dec.tolist(),
                        decile_maxdiff=float(np.abs(dec - dec0).max()))
        log.info("G0 %-6s %s %s maxdiff=%.2e spearman=%.4f", arm, "PASS" if out[arm]["ok"] else "*** FAIL ***", c,
                 out[arm]["decile_maxdiff"], res[arm]["spearman_vs_orig"])
    json.dump(dict(decile_p0=dec0.tolist(), g0=out), open(D + "/g0.json", "w"), indent=1)
    return out


def m23(daily):
    """Ban KHONG 2022: equity MTM cuoi ngay (b+unP), rebase 2022-12-31 .. ngay cuoi (2025-12-30)."""
    e = daily["equity"].astype(float)
    e = e[e.index >= W23]
    assert e.index[0] == W23, e.index[0]
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    cagr = ((e.iloc[-1] / e.iloc[0]) ** (1.0 / yrs) - 1.0) * 100.0
    mdd = float((e / e.cummax() - 1.0).min() * 100.0)
    return dict(cagr23=float(cagr), mdd23=mdd, calmar23=float(cagr / abs(mdd)) if mdd < 0 else float("nan"),
                end=str(e.index[-1].date()))


def pctl(band_vals, v):
    return 100.0 * sum(1 for b in band_vals if b <= v) / len(band_vals)


def load_all(keys, R):
    legs, daily, md5 = {}, {}, {}
    for k in keys:
        legs[k], daily[k], md5[k] = R.load_legs(TAG[k]), R.load_daily(TAG[k]), R.md5_of(TAG[k])
    return legs, daily, md5


def score(a):
    import reset_rule_score as R
    import feat_add_v1_score as F  # noqa: F401  (side effect: MTMState cua so 2022+)
    import flat3_crashpen_driver as F3
    import selector_ablation_driver as SAD
    import n700_driver as N
    R.MTM_COSTS = {"legacy": R.LEGACY}
    SAD.INFL = INFL
    N.INFL = INFL
    N.TAG.update(TAG)
    N.DESC.update({k: "GATE_BAGFIX_NULL " + k for k in TAG})
    par = GSB.parity()
    void = [k for k in ARMS if k in par and not par[k]["ok"]]
    keys = OLD + [k for k in ARMS if k in par and par[k]["ok"]]
    legs, daily, md5 = load_all(keys, R)
    assert md5["A1"] == GA.A1_MD5, md5["A1"]
    raw = json.load(open(D + "/mtm.json")) if os.path.exists(D + "/mtm.json") else {}
    gm = json.load(open(GSB_MTM)) if os.path.exists(GSB_MTM) else {}
    for k in OLD:                                      # MTM vong GATE_SEEDBAND (md5 printDone phai khop)
        if k not in raw and gm.get(k, {}).get("md5") == md5[k]:
            raw[k] = gm[k]
    miss = {k: legs[k] for k in keys if k not in raw or raw[k].get("md5") != md5[k]}
    log.info("MTM cache %s; can tinh %s", sorted(raw), sorted(miss))
    if miss:
        new = R.run_mtm(miss, workers=a.workers, chunk=30)
        for k, vv in new.items():
            vv["md5"] = md5[k]
            raw[k] = vv
        json.dump(raw, open(D + "/mtm.json", "w"))
    M = {k: N.arm_metrics(R, F3, k, legs[k], daily[k], raw[k]["legacy"]) for k in keys}
    for k in keys:
        M[k]["md5"] = md5[k]
        M[k]["gate_minutes"] = GA.gate_minutes(TAG[k])
        M[k]["q_mtm"] = GSB.q_mtm(daily[k])
        M[k].update(m23(daily[k]))
    eqs = {("P0" if k == "A1" else k): daily[k]["equity"][daily[k]["equity"].index >= GA.W0] for k in keys}
    idx = eqs["P0"].index
    for k in eqs:
        assert len(eqs[k]) == len(idx) and (eqs[k].index == idx).all(), ("lech chi so ngay", k)
    obs, bs = SAD.daily_boot(eqs)
    obs["A1"], bs["A1"] = obs.pop("P0"), bs.pop("P0")
    pairs = [(k, "A1") for k in keys if k != "A1"]
    if "RBAG8" in keys and "BAG8M" in keys:
        pairs.append(("RBAG8", "BAG8M"))
    con = {x + "-" + y: {m: SAD.ci_of(obs[x][m] - obs[y][m], bs[x][m] - bs[y][m]) for m in ("cagr", "mdd", "calmar")}
           for x, y in pairs}
    dp = N.pnl_boot(legs, idx, keys, pairs)
    for x, y in pairs:
        con[x + "-" + y]["pnl"] = dp[x + "-" + y]
    mins = {k: GSB.gate_sets_min(TAG[k]) for k in keys}
    trs = {k: GSB.trade_set(legs[k]) for k in keys}
    finish(M, obs, con, par, keys, void, mins, trs)


METS = ["cagr22", "calmar22", "dd_mtm22", "uw_mtm22", "dpnl", "cagr23", "calmar23", "mdd23"]


def finish(M, obs, con, par, keys, void, mins, trs):
    from itertools import combinations
    A = M["A1"]
    band = [k for k in BAND if k in keys]
    assert len(band) == 8, band
    val = lambda k, m: (0.0 if k == "A1" else con[k + "-A1"]["pnl"]["d"]) if m == "dpnl" else M[k][m]  # noqa: E731
    st = {m: GSB.stats([val(k, m) for k in band]) for m in METS}
    g2 = {}
    for k in keys:
        if k == "A1":
            continue
        rn = M[k]["n_per_year"] / A["n_per_year"]
        rg = M[k]["gate_minutes"]["mean"] / A["gate_minutes"]["mean"]
        g2[k] = dict(ok=bool(0.75 <= rn <= 1.25 and 0.75 <= rg <= 1.25), ratio_n=rn, ratio_gate_min=rg,
                     gate_min_2022=M[k]["gate_minutes"]["per_year"].get(2022))
    jac = GSB.jac
    pr = list(combinations(band, 2))
    J = dict(pair_seed_min=float(np.mean([jac(mins[x], mins[y]) for x, y in pr])),
             pair_seed_trade=float(np.mean([jac(trs[x], trs[y]) for x, y in pr])), n_pairs=len(pr))
    for x in BAGS + ["BAG8"] + NULL_ALL:
        if x in keys:
            J[x] = dict(vs_seed_min=float(np.mean([jac(mins[x], mins[k]) for k in band])),
                        vs_seed_trade=float(np.mean([jac(trs[x], trs[k]) for k in band])),
                        vs_A1=[jac(mins[x], mins["A1"]), jac(trs[x], trs["A1"])])
    for x, y in (("BAG8M", "BAG8"), ("RBAG8", "BAG8M"), ("RBAG8", "BAG8")):
        if x in keys and y in keys:
            J[x + "~" + y] = [jac(mins[x], mins[y]), jac(trs[x], trs[y])]
    ans = {}
    for x in BAGS + ["BAG8"]:
        if x not in keys:
            ans[x] = "VOID (parity)"
            continue
        B, c = M[x], M[x]["cagr22"]
        pos = "duoi dai" if c < st["cagr22"]["min"] else "tren dai" if c > st["cagr22"]["max"] else "trong dai"
        cond = dict(c_cagr=c >= st["cagr22"]["median"], c_calmar=B["calmar22"] >= 0.9 * st["calmar22"]["median"],
                    c_dd=abs(B["dd_mtm"]) <= 40 and abs(B["dd_mtm22"]) <= 40,
                    c_jac=J[x]["vs_seed_min"] > J["pair_seed_min"])
        interp = g2[x]["ok"]
        ans[x] = dict(position=pos, percentile={m: pctl([val(k, m) for k in band], val(x, m)) for m in METS},
                      interpretable=bool(interp), candidate_var_reduction=bool(interp and all(cond.values())),
                      **{k: bool(v) for k, v in cond.items()})
    ans["Q1"] = ans.get("BAG8M")
    if "RBAG8-BAG8M" in con and g2.get("RBAG8", {}).get("ok") and g2.get("BAG8M", {}).get("ok"):
        lo, hi = con["RBAG8-BAG8M"]["cagr"]["ci_infl"]
        ans["Q2"] = dict(verdict="khac" if (lo > 0 or hi < 0) else "khong phan biet duoc",
                         d_cagr=con["RBAG8-BAG8M"]["cagr"]["d"], ci_infl=[lo, hi],
                         d_pnl=con["RBAG8-BAG8M"]["pnl"]["d"], ci_pnl_infl=con["RBAG8-BAG8M"]["pnl"]["ci_infl"])
    else:
        ans["Q2"] = dict(verdict="khong dien giai (VOID/G2)")
    nul_ok = [k for k in NULL_ALL if k in keys and g2[k]["ok"]]
    nul_all = [k for k in NULL_ALL if k in keys]

    def dstat(ns, m):
        v = [M[k][m] for k in ns]
        if len(v) < 2:
            return dict(n=len(v))
        mu, sd = float(np.mean(v)), float(np.std(v, ddof=1))
        return dict(n=len(v), mean=mu, sd=sd, vals={k: M[k][m] for k in ns},
                    d=(st[m]["mean"] - mu) / sd if sd > 0 else float("nan"))
    nd = {m: dstat(nul_ok, m) for m in ("cagr22", "calmar22", "cagr23", "calmar23")}
    nd_all = {m: dstat(nul_all, m) for m in ("cagr22", "calmar22", "cagr23")}
    if len(nul_ok) < 3:
        ans["Q3"] = dict(verdict="khong dien giai duoc (< 3 null hop le)", nulls=nul_ok)
    else:
        d = nd["cagr22"]["d"]
        ans["Q3"] = dict(verdict="gate co gia tri timing ro" if d >= 3 else "co nhung mong" if d >= 1
                         else "khong do duoc", d=d, nulls=nul_ok, null=nd["cagr22"], seed_mean=st["cagr22"]["mean"])
    dy = {k: {y: (M[k]["roi_year"].get(y, np.nan) - A["roi_year"].get(y, np.nan)) for y in GA.YEARS} for k in keys}
    dq = {k: {q: M[k]["q_mtm"][q] - A["q_mtm"].get(q, np.nan) for q in M[k]["q_mtm"]} for k in keys}
    log.info("%-6s %5s %6s %7s %5s %6s %7s %7s %5s %6s %8s %7s %6s %6s", "arm", "n", "n/nam", "gateMin", "gm22",
             "CAGR22", "dd22", "ddAll", "UW22", "Cal22", "dPnL", "dCAGR", "CAGR23", "Cal23")
    for k in keys:
        x = M[k]
        log.info("%-6s %5d %6.0f %7.1f %5s %6.2f %7.2f %7.2f %5.0f %6.3f %8.0f %7.2f %6.2f %6.3f", k, x["n"],
                 x["n_per_year"], x["gate_minutes"]["mean"], x["gate_minutes"]["per_year"].get(2022), x["cagr22"],
                 x["dd_mtm22"], x["dd_mtm"], x["uw_mtm22"], x["calmar22"], val(k, "dpnl"),
                 0.0 if k == "A1" else con[k + "-A1"]["cagr"]["d"], x["cagr23"], x["calmar23"])
    for m in METS:
        log.info("BAND %-9s %s", m, {kk: round(v, 3) for kk, v in st[m].items()})
    for cc, v in con.items():
        if cc.split("-")[0] in ARMS:
            log.info("CON %-12s dCAGR %+.2f raw[%+.2f;%+.2f] infl[%+.2f;%+.2f] dPnL %+.0f infl[%+.0f;%+.0f]", cc,
                     v["cagr"]["d"], *v["cagr"]["ci_raw"], *v["cagr"]["ci_infl"], v["pnl"]["d"], *v["pnl"]["ci_infl"])
    for k in keys:
        if k != "A1" and k not in BAND:
            log.info("YEAR %-6s dROI %s | G2 %s", k, {y: round(v, 2) for y, v in dy[k].items()}, g2[k])
    log.info("JAC %s", json.dumps(J))
    log.info("NULL ok=%s %s | all=%s", nul_ok, json.dumps(nd, default=str), json.dumps(nd_all, default=str))
    log.info("ANS %s", json.dumps(ans, ensure_ascii=False, default=str))
    js = dict(prereg="docs/prereg/PREREG_GATE_BAGFIX_NULL.md", k_infl=K_INFL, inflate=INFL, nrep=2000,
              seed=20260905, block_days=10, window="2022-01-01..2025-12-30 (rebase 2021-12-31)",
              window_no2022="2022-12-31..2025-12-30 (equity MTM cuoi ngay)", jar_sha256=GA.JAR_SHA,
              kaggle_sim_md5=GA.KS_MD5_WANT, tags=TAG, band_keys=band, void=void, parity=par, g2=g2, band=st,
              jaccard=J, null_ok=nd, null_all=nd_all, boot_obs=obs, contrasts=con, d_roi_year=dy, d_q_mtm=dq,
              answers=ans, metrics=M)
    for nm in ("g0", "g1"):
        p = D + "/%s.json" % nm
        if os.path.exists(p):
            js[nm] = json.load(open(p))
    for x in ARMS:
        p = D + "/pred_%s/meta.json" % x
        if os.path.exists(p):
            js["meta_" + x] = json.load(open(p))
    json.dump(js, open(JSON_OUT, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", JSON_OUT)


def dsstatus(a):
    GA.dsstatus(argparse.Namespace(arms=a.arms or ARMS))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("arms", nargs="*")
    ap.add_argument("--code-sha", default="")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(D, exist_ok=True)
    for x in a.arms:
        assert x in ARMS, x
    if a.cmd in ("gen", "g0", "score", "dsstatus"):
        globals()[a.cmd](a)
    elif a.cmd in ("upload", "fetch"):
        getattr(GSB, a.cmd)(a)
    elif a.cmd == "parity":
        GSB.parity()
    elif a.cmd == "submit":
        disk("truoc submit")
        GA.submit(a)
    elif a.cmd == "status":
        GA.status(argparse.Namespace(arms=a.arms or ARMS))
    elif a.cmd == "df":
        disk("df")
    else:
        raise SystemExit("cmd?")


if __name__ == "__main__":
    main()
