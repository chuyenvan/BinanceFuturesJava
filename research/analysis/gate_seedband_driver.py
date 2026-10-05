#!/usr/bin/env python3
"""GATE_SEEDBAND (Pha B chuong trinh GATE). Pre-reg docs/prereg/PREREG_GATE_SEEDBAND.md (f79670a9, chot TRUOC).

Arm: S13,S21,S99,S123,S777,S2024 (retrain dung recipe GA.retrain, chi doi random_state; p15 tho),
BAG8 (TB so hoc p15 tho 8 seed: 42 = pred.bin goc/A1, 7 = gabl SEED7, 6 seed moi), NULLB (p15 goc hoan vi
theo khoi 30 ngay, rng 20261004). So voi A1 (n700-a1) + dai 8 seed (42=A1, 7=gabl-seed7, 6 moi).
TIET KIEM DIA: retrain khong ghi npy (chan np.save -> RAM), moi arm chi 1 pred.bin; dataset = hardlink.
Usage: python3 gate_seedband_driver.py retrain S13 ... | bag | nullb | g0 | upload ARM | submit ARM --code-sha SHA
       | status | fetch ARM | parity | score --workers 3
"""
import argparse
import json
import logging
import math
import os
import shutil
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
HERE = os.path.join(REPO, "research/analysis")
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
import gate_ablation_driver as GA  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("gsb")

D = "/home/ubuntu/claude_master/1004/gsb"
GA.D = D                                   # retrain_*.json, g1.json, parity.json, pred_*/, ds_*/ cua vong nay
SEEDS_NEW = [13, 21, 99, 123, 777, 2024]
NEW = ["S%d" % s for s in SEEDS_NEW]
ARMS = NEW + ["BAG8", "NULLB"]
SEEDK = {42: "A1", 7: "S7", **{s: "S%d" % s for s in SEEDS_NEW}}   # 8 seed cua dai
BAND = list(SEEDK.values())
for _s in SEEDS_NEW:
    GA.RETRAIN["S%d" % _s] = dict(feats=GA.V3FULL, label="label_oldbasket", purge=15, seed=_s)
TAG = {"A1": "n700-a1", "S7": "gabl-seed7", **{a: "gsb-" + a.lower() for a in ARMS}}
DSN = {a: "gate-sb-" + a.lower() for a in ARMS}
GA.TAG.update(TAG)
GA.DSN.update(DSN)
GA.ARMS = ARMS                              # GA.parity lap tren GA.ARMS
SEED7_PRED = "/home/ubuntu/claude_master/1004/gabl/pred_SEED7/pred.bin"
SEED7_PRED_MD5 = "b737fb6d64d198c14654ea9c92510b36"
GABL_MTM = "/home/ubuntu/claude_master/1004/gabl/mtm.json"
NULL_SEED = 20261004
BLOCK_MS = 30 * 86_400_000
K_INFL = 8
INFL = math.sqrt(2.0 * math.log(K_INFL))
DISK_MIN_MB = 500
JSON_OUT = os.path.join(REPO, "docs/result/gate_seedband.json")
W22, W26 = pd.Timestamp("2022-01-01"), pd.Timestamp("2026-01-01")
A1_N_YEAR, A1_GATE_MIN = 732.0, 146.5


def disk(tag=""):
    mb = shutil.disk_usage("/home/ubuntu").free // (1 << 20)
    log.info("DF %s avail=%d MB", tag, mb)
    if mb < DISK_MIN_MB:
        log.error("DIA < %d MB -> DUNG (khong ghi them), bao MASTER", DISK_MIN_MB)
        sys.exit(3)
    return mb


def write_pred(arm, p15, extra=None):
    """Ghi 1 pred.bin duy nhat: header + (ts, p15 moi, risk4h) - ts/risk byte-identical pred.bin goc."""
    raw, a = GA.read_pred()
    assert GA.md5f(GA.PRED0) == GA.PRED0_MD5
    p15 = np.asarray(p15, np.float32)
    assert p15.shape == (len(a),) and np.isfinite(p15).all()
    b = a.copy()
    b["p15"] = p15.astype(">f4")
    out_dir = D + "/pred_%s" % arm
    os.makedirs(out_dir, exist_ok=True)
    p = out_dir + "/pred.bin"
    with open(p, "wb") as f:
        f.write(raw[:4])
        f.write(b.tobytes())
    md5 = GA.md5f(p)
    meta = dict(arm=arm, md5=md5, n=int(len(b)), n_nan_x=0, mapped=False, **(extra or {}))
    json.dump(meta, open(out_dir + "/meta.json", "w"), indent=1)
    log.info("PRED %s -> %s md5=%s n=%d", arm, p, md5, len(b))
    return meta


def retrain(arm):
    disk("truoc retrain " + arm)
    cap = {}
    orig = GA.np.save
    GA.np.save = lambda p, x: cap.__setitem__("x", np.array(x, np.float32))   # chan npy ra dia (giu RAM)
    try:
        res = GA.retrain(arm)
    finally:
        GA.np.save = orig
    write_pred(arm, cap["x"], dict(seed=GA.RETRAIN[arm]["seed"], min_pearson=res["min_pearson"]))
    disk("sau retrain " + arm)


def bag(a=None):
    disk("truoc BAG8")
    _, a0 = GA.read_pred()
    acc = a0["p15"].astype(np.float64)                       # seed 42 = pred.bin goc (chuoi A1 dung)
    comps = {"42": GA.PRED0_MD5}
    srcs = [(7, SEED7_PRED, SEED7_PRED_MD5)]
    for s in SEEDS_NEW:
        m = json.load(open(D + "/pred_S%d/meta.json" % s))
        srcs.append((s, D + "/pred_S%d/pred.bin" % s, m["md5"]))
    for s, p, want in srcs:
        assert GA.md5f(p) == want, (s, p)
        _, b = GA.read_pred(p)
        assert (b["ts"] == a0["ts"]).all()
        acc += b["p15"].astype(np.float64)
        comps[str(s)] = want
    assert len(comps) == 8
    acc /= 8.0
    write_pred("BAG8", acc.astype(np.float32), dict(components=comps))
    disk("sau BAG8")


def nullb(a=None):
    disk("truoc NULLB")
    _, a0 = GA.read_pred()
    ts = a0["ts"].astype(np.int64)
    p0 = a0["p15"].astype(np.float32)
    assert (np.diff(ts) > 0).all(), "pred.bin khong tang dan theo ts"
    idx = np.where(ts < GA.SEAL)[0]
    assert idx[-1] == len(idx) - 1                           # phan < 2026 la tien to lien tuc
    blk = (ts[idx] - ts[idx[0]]) // BLOCK_MS
    nb = int(blk.max()) + 1
    perm = np.random.default_rng(NULL_SEED).permutation(nb)
    vals = np.concatenate([p0[idx][blk == k] for k in perm])
    assert len(vals) == len(idx)
    y = p0.copy()
    y[idx] = vals
    sizes = np.bincount(blk, minlength=nb)
    log.info("NULLB n_khoi=%d (khoi cuoi %d phut) perm[:10]=%s corr(y,p0)=%.4f", nb, int(sizes[-1]),
             perm[:10].tolist(), float(np.corrcoef(y[idx], p0[idx])[0, 1]))
    write_pred("NULLB", y, dict(n_blocks=nb, perm=perm.tolist(), block_minutes=sizes.tolist(), seed=NULL_SEED))
    disk("sau NULLB")


def g0(a=None):
    """G0 format (GA.g1 tren cac arm vong nay) + G1 pearson/fold vs seed 42 tu retrain_*.json."""
    res = GA.g1(ARMS)
    g1 = {}
    for arm in NEW:
        r = json.load(open(D + "/retrain_%s.json" % arm))
        pf = [f["pearson"] for f in r["folds"]]
        low = [(f["fold"], f["cutoff"], round(f["pearson"], 5)) for f in r["folds"] if f["pearson"] < 0.97]
        g1[arm] = dict(min=min(pf), median=float(np.median(pf)), max=max(pf), n_fold=len(pf), below_097=low,
                       min_spearman=r["min_spearman"], ok=not low)
        log.info("G1 %-6s pearson min/med/max %.5f/%.5f/%.5f folds<0.97 %s", arm, min(pf), np.median(pf), max(pf), low)
    out = dict(g0={k: dict(ok=v["ok"], md5=v["md5"], spearman_vs_orig=v["spearman_vs_orig"], checks=v["checks"])
                   for k, v in res.items()}, g1=g1)
    json.dump(out, open(D + "/g0g1.json", "w"), indent=1)
    log.info("G0 %s", {k: v["ok"] for k, v in res.items()})


def upload(a):
    for arm in a.arms:
        disk("truoc upload " + arm)
        GA.upload(argparse.Namespace(arms=[arm]))
        disk("sau upload " + arm)


def gate_sets_min(tag):
    """Tap phut gate-mo (PREDICT_SYMBOL_TRADE, phut vao) cua so 2022-2025."""
    d = pd.read_csv(GA.OUT % tag + "storage/printDone.csv", on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    st = d["start"].astype(str).str.strip()
    t = pd.to_datetime(st, format="%Y%m%d %H:%M", errors="coerce")
    w = (t >= W22) & (t < W26)
    lv = d["level"].astype(str).str.strip() == "PREDICT_SYMBOL_TRADE"
    mins = set(st[w & lv])
    return mins


def jac(x, y):
    return len(x & y) / max(1, len(x | y))


def trade_set(legs):
    L = legs[(legs["ts"] >= W22) & (legs["ts"] < W26)]
    return set(L["sym"].astype(str) + "|" + L["start"].astype(str).str.strip())


def md5_verified(tag):
    """Log Java 'WfoDataset LOAD offline OK ... (md5 verified)' trong out cua run."""
    root = GA.OUT % tag
    for dp, _, fs in os.walk(root):
        for fn in fs:
            if fn.endswith(".log") or fn.endswith(".txt"):
                try:
                    with open(os.path.join(dp, fn), errors="ignore") as f:
                        for ln in f:
                            if "md5 verified" in ln and "pred=" in ln:
                                return ln.strip()[-160:]
                except OSError:
                    pass
    return None


def parity(a=None):
    par = GA.parity()
    for arm in list(par):
        v = md5_verified(GA.TAG[arm])
        par[arm]["checks"]["java_md5_verified"] = v is not None
        par[arm]["java_line"] = v
        par[arm]["ok"] = all(par[arm]["checks"].values())
        log.info("PARITY+ %-6s %s java=%s", arm, "PASS" if par[arm]["ok"] else "*** VOID ***", v)
    json.dump(par, open(D + "/parity.json", "w"), indent=1)
    return par


def q_mtm(daily):
    return GA.q_mtm(daily)


def stats(v):
    v = np.asarray(v, float)
    return dict(mean=float(v.mean()), sd=float(v.std(ddof=1)), min=float(v.min()), max=float(v.max()),
                median=float(np.median(v)), n=int(len(v)))


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
    N.DESC.update({k: "GATE_SEEDBAND " + k for k in TAG})
    par = parity()
    void = [k for k in ARMS if k in par and not par[k]["ok"]]
    keys = ["A1", "S7"] + [k for k in ARMS if k in par and par[k]["ok"]]
    legs, daily, md5 = {}, {}, {}
    for k in keys:
        legs[k], daily[k], md5[k] = R.load_legs(TAG[k]), R.load_daily(TAG[k]), R.md5_of(TAG[k])
    assert md5["A1"] == GA.A1_MD5, md5["A1"]
    raw = json.load(open(D + "/mtm.json")) if os.path.exists(D + "/mtm.json") else {}
    if os.path.exists(GABL_MTM):                                  # A1 + SEED7 da cham o vong GATE_ABLATION
        gm = json.load(open(GABL_MTM))
        for src, dst in (("A1", "A1"), ("SEED7", "S7")):
            if dst not in raw and gm.get(src, {}).get("md5") == md5[dst]:
                raw[dst] = gm[src]
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
        M[k]["q_mtm"] = q_mtm(daily[k])
    eqs = {("P0" if k == "A1" else k): daily[k]["equity"][daily[k]["equity"].index >= GA.W0] for k in keys}
    idx = eqs["P0"].index
    for k in eqs:
        assert len(eqs[k]) == len(idx) and (eqs[k].index == idx).all(), ("lech chi so ngay", k)
    obs, bs = SAD.daily_boot(eqs)
    obs["A1"], bs["A1"] = obs.pop("P0"), bs.pop("P0")
    pairs = [(k, "A1") for k in keys if k != "A1"]
    con = {x + "-" + y: {m: SAD.ci_of(obs[x][m] - obs[y][m], bs[x][m] - bs[y][m]) for m in ("cagr", "mdd", "calmar")}
           for x, y in pairs}
    dp = N.pnl_boot(legs, idx, keys, pairs)
    for x, y in pairs:
        con[x + "-" + y]["pnl"] = dp[x + "-" + y]
    mins = {k: gate_sets_min(TAG[k]) for k in keys}
    trs = {k: trade_set(legs[k]) for k in keys}
    finish(M, obs, con, par, keys, void, mins, trs)


METS = ["cagr22", "calmar22", "dd_mtm22", "uw_mtm22", "dpnl"]


def finish(M, obs, con, par, keys, void, mins, trs):
    from itertools import combinations
    A = M["A1"]
    band = [k for k in BAND if k in keys]
    val = lambda k, m: (0.0 if k == "A1" else con[k + "-A1"]["pnl"]["d"]) if m == "dpnl" else M[k][m]  # noqa: E731
    st = {m: stats([val(k, m) for k in band]) for m in METS}
    z = {m: ((val("A1", m) - st[m]["mean"]) / st[m]["sd"] if st[m]["sd"] > 0 else float("nan")) for m in METS}
    g2 = {}
    for k in keys:
        if k == "A1":
            continue
        rn = M[k]["n_per_year"] / A["n_per_year"]
        rg = M[k]["gate_minutes"]["mean"] / A["gate_minutes"]["mean"]
        g2[k] = dict(ok=bool(0.75 <= rn <= 1.25 and 0.75 <= rg <= 1.25), ratio_n=rn, ratio_gate_min=rg)
    pr = list(combinations(band, 2))
    jac_pair_min = float(np.mean([jac(mins[x], mins[y]) for x, y in pr]))
    jac_pair_tr = float(np.mean([jac(trs[x], trs[y]) for x, y in pr]))
    jac_mat = {x + "~" + y: [round(jac(mins[x], mins[y]), 4), round(jac(trs[x], trs[y]), 4)] for x, y in pr}
    J = dict(pair_seed_min=jac_pair_min, pair_seed_trade=jac_pair_tr, n_pairs=len(pr), matrix_min_trade=jac_mat)
    for x in ("BAG8", "NULLB"):
        if x in keys:
            J[x + "_vs_seed_min"] = float(np.mean([jac(mins[x], mins[k]) for k in band]))
            J[x + "_vs_seed_trade"] = float(np.mean([jac(trs[x], trs[k]) for k in band]))
            J[x + "_vs_A1"] = [jac(mins[x], mins["A1"]), jac(trs[x], trs["A1"])]
    ans = {}
    zc = z["cagr22"]
    ans["Q1"] = ("A1/B0 may man o tang gate; ky vong recipe = mean" if zc >= 1 else
                 "A1 kem hon ky vong recipe" if zc <= -1 else "A1 dien hinh cua recipe (|z|<1)")
    ans["Q1_z"] = z
    pct = {}
    if "BAG8" in keys:
        B = M["BAG8"]
        pct = {m: 100.0 * sum(1 for k in band if val(k, m) <= val("BAG8", m)) / len(band) for m in METS}
        stable = J["BAG8_vs_seed_min"] > jac_pair_min
        dep = dict(c_cagr=B["cagr22"] >= st["cagr22"]["median"],
                   c_dd=abs(B["dd_mtm"]) <= 40 and abs(B["dd_mtm22"]) <= 40,
                   c_calmar=B["calmar22"] >= 0.9 * st["calmar22"]["median"],
                   c_jac=stable, c_g2=g2["BAG8"]["ok"])
        ans["Q2"] = dict(stable=bool(stable), percentile=pct, deploy_candidate=bool(all(dep.values())),
                         **{k: bool(v) for k, v in dep.items()})
    if "NULLB" in keys:
        c, lo, hi, sd = M["NULLB"]["cagr22"], st["cagr22"]["min"], st["cagr22"]["max"], st["cagr22"]["sd"]
        if not g2["NULLB"]["ok"]:
            ans["Q3"] = "khong dien giai duoc (NULLB truot G2)"
        else:
            ans["Q3"] = ("gate co gia tri timing" if c < lo - sd else "timing khong do duoc" if lo <= c <= hi
                         else "khong ket luan")
        ans["Q3_val"] = dict(cagr22=c, thr=lo - sd, band_min=lo, band_max=hi)
    dy = {k: {y: (M[k]["roi_year"].get(y, np.nan) - A["roi_year"].get(y, np.nan)) for y in GA.YEARS} for k in keys}
    dq = {k: {q: M[k]["q_mtm"][q] - A["q_mtm"].get(q, np.nan) for q in M[k]["q_mtm"]} for k in keys}
    log.info("%-6s %5s %6s %7s %6s %7s %7s %5s %6s %8s %7s", "arm", "n", "n/nam", "gateMin", "CAGR22", "dd22",
             "ddAll", "UW22", "Cal22", "dPnL", "dCAGR")
    for k in keys:
        x = M[k]
        log.info("%-6s %5d %6.0f %7.1f %6.2f %7.2f %7.2f %5.0f %6.3f %8.0f %7.2f", k, x["n"], x["n_per_year"],
                 x["gate_minutes"]["mean"], x["cagr22"], x["dd_mtm22"], x["dd_mtm"], x["uw_mtm22"], x["calmar22"],
                 val(k, "dpnl"), 0.0 if k == "A1" else con[k + "-A1"]["cagr"]["d"])
    for m in METS:
        log.info("BAND %-9s %s z(A1)=%+.2f", m, {kk: round(v, 3) for kk, v in st[m].items()}, z[m])
    for cc, v in con.items():
        log.info("CON %-9s dCAGR %+.2f raw[%+.2f;%+.2f] infl[%+.2f;%+.2f] dPnL %+.0f infl[%+.0f;%+.0f]", cc,
                 v["cagr"]["d"], *v["cagr"]["ci_raw"], *v["cagr"]["ci_infl"], v["pnl"]["d"], *v["pnl"]["ci_infl"])
    for k in keys:
        if k != "A1":
            log.info("YEAR %-6s dROI %s | G2 %s", k, {y: round(v, 2) for y, v in dy[k].items()}, g2[k])
    log.info("JAC %s", json.dumps({k: v for k, v in J.items() if k != "matrix_min_trade"}))
    log.info("ANS %s", json.dumps(ans, ensure_ascii=False, default=str))
    js = dict(prereg="docs/prereg/PREREG_GATE_SEEDBAND.md", prereg_commit="f79670a9", k_infl=K_INFL, inflate=INFL,
              nrep=2000, seed=20260905, block_days=10, window="2022-01-01..2025-12-30 (rebase 2021-12-31)",
              jar_sha256=GA.JAR_SHA, kaggle_sim_md5=GA.KS_MD5_WANT, tags=TAG, band_keys=band, void=void,
              parity=par, g2=g2, band=st, z_A1=z, jaccard=J, boot_obs=obs, contrasts=con, d_roi_year=dy,
              d_q_mtm=dq, answers=ans, metrics=M)
    for nm in ["g0g1"] + ["retrain_" + x for x in NEW]:
        p = D + "/%s.json" % nm
        if os.path.exists(p):
            js[nm] = json.load(open(p))
    for x in ("BAG8", "NULLB"):
        p = D + "/pred_%s/meta.json" % x
        if os.path.exists(p):
            js["meta_" + x] = json.load(open(p))
    json.dump(js, open(JSON_OUT, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", JSON_OUT)


def fetch(a):
    for arm in a.arms:
        disk("truoc fetch " + arm)
        GA.fetch(argparse.Namespace(arms=[arm]))
        disk("sau fetch " + arm)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("arms", nargs="*")
    ap.add_argument("--code-sha", default="")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(D, exist_ok=True)
    if a.cmd == "retrain":
        for x in a.arms:
            assert x in NEW, x
            retrain(x)
    elif a.cmd in ("bag", "nullb", "g0", "upload", "fetch", "parity", "score"):
        globals()[a.cmd](a)
    elif a.cmd == "submit":
        disk("truoc submit")
        GA.submit(a)
    elif a.cmd == "status":
        GA.status(a)
    elif a.cmd == "df":
        disk("df")
    else:
        raise SystemExit("cmd?")


if __name__ == "__main__":
    main()
