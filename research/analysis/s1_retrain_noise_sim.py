#!/usr/bin/env python3
"""S1_RETRAIN_NOISE — prep/map/model-score/sim/score. Pre-reg docs/prereg/PREREG_S1_RETRAIN_NOISE.md (14409eb4).
Tai dung duong sim LABEL_FIRSTHIT (label_firsthit_sim.template = SELECTOR_ABLATION, kaggle_sim HEAD md5 8b60b00a),
CHI doi nguon 16 bins arm = map s1a2x1 cua pred S1 retrain (G015 giu nguyen g015x26_regen).
Usage: python3 s1_retrain_noise_sim.py mapparity | prep ARM.. | model | shas | upload ARM.. | submit ARM.. | b0ref
       | wait ARM.. | fetch ARM.. | parity | score
"""
import argparse, glob, hashlib, json, logging, math, os, shutil, subprocess, sys
import numpy as np
import pandas as pd
REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
import selector_ablation_driver as SAD  # noqa: E402
import selector_ablation_scores as SAS  # noqa: E402
import label_firsthit_sim as LFS  # noqa: E402
from tools import kaggle_sim as ks  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("s1rn")
D = "/home/ubuntu/claude_master/1003/s1rn"
ARMS = ["K42", "S7", "S13", "S21"]
SEEDS = ["S7", "S13", "S21"]
TAGS = {a: "s1rn-" + a.lower() for a in ARMS}
DSN = {a: "s1rn-bins-" + a.lower() for a in ARMS}
B0REF3 = "s1rn-b0ref3"
B0_TAG, B0_MD5 = "selab-p0", "ff3ce513edf2316088a4b5ac464f76dc"
ORIG_PRED = "/home/ubuntu/ledger/pred_s1a2x1.parquet"
ORIG_SHA = "2618fe1a0235d8ed3602f7b4bf37d8ba611e4e6c923854e10184d036065309fe"
F0MAP = "/home/ubuntu/predwf_map_s1a2_x1"   # A1: bins deploy B0 (sha P0 407e2aba)
G015 = F0MAP   # A1: nguon G015 = bins deploy (map luy dang tren nhom co diem S1, xem PREREG A1)
MOC21 = "/home/ubuntu/claude_master/1003/fh/moc21"
CUTS16 = ("20220101 20220401 20220701 20221001 20230101 20230401 20230701 20231001 20240101 20240401 20240701 "
          "20241001 20250101 20250401 20250701 20251001")
SHA_JSON = D + "/sim_sha256.json"
MTM_CACHE = D + "/sim_mtm.json"
MODEL_JSON = D + "/model_score.json"
JSON_OUT = os.path.join(REPO, "docs/result/s1_retrain_noise.json")
W0 = pd.Timestamp("2021-12-31")
TZ = 7 * 3600000
Z80 = 1.959964 + 0.841621


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def md5dir(d):
    return {os.path.basename(f): hashlib.md5(open(f, "rb").read()).hexdigest()
            for f in sorted(glob.glob(d + "/predict_wf_*.bin"))}


def cut_ms():
    return np.array([int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value // 10 ** 6) - TZ for c in CUTS16.split()])


def fold_of(ts):
    return np.searchsorted(cut_ms(), np.asarray(ts), side="right") - 1


def build_map(name, out):
    env = dict(os.environ, X1_CUTS=CUTS16, X1_G015_DIR=G015)
    with open(out + ".out", "w") as f:
        r = subprocess.run(["nice", "-n", "10", "/usr/bin/python3", REPO + "/research/pipeline/x1/x1_build_map.py",
                            name, out], env=env, stdout=f, stderr=subprocess.STDOUT)
    tail = open(out + ".out").read().strip().splitlines()[-2:]
    log.info("map %s rc=%d %s", name, r.returncode, tail)
    assert r.returncode == 0 and tail[-1] == "MAP_OK", tail


def mapparity():
    assert sha256f(ORIG_PRED) == ORIG_SHA, "pred_s1a2x1 goc da doi"
    chk = D + "/map_ORIGchk"
    build_map("s1a2x1", chk)
    a, b = md5dir(chk), md5dir(F0MAP)
    ok = len(a) == 16 and a == b
    json.dump(dict(ok=ok, n=len(a), md5=a), open(D + "/map_parity.json", "w"), indent=1)
    shutil.rmtree(chk)
    log.info("MAP_PARITY_%s (%d/16 file)", "PASS" if ok else "FAIL", sum(a.get(k) == v for k, v in b.items()))
    return ok


def load_pred(arm):
    p = ORIG_PRED if arm == "ORIG" else D + "/kout/pred_%s.parquet" % arm
    return pd.read_parquet(p, columns=["ts", "sym", "score"])


def prep(arm):
    """Sanity §5.2 (tap (ts,sym) == ORIG, so dong/fold bang, score huu han) -> pred tam -> map s1a2x1 (G015 goc)."""
    P, O = load_pred(arm), load_pred("ORIG")
    assert np.isfinite(P.score).all(), "score NaN/Inf"
    assert not P.duplicated(["ts", "sym"]).any()
    J = O[["ts", "sym"]].merge(P[["ts", "sym"]], on=["ts", "sym"], how="inner")
    fo, fp = np.bincount(fold_of(O.ts), minlength=16), np.bincount(fold_of(P.ts), minlength=16)
    ok = len(P) == len(O) == len(J) and (fo == fp).all() and fold_of(P.ts).min() >= 0
    log.info("PREP %s rows %d orig %d join %d fold_eq %s -> %s", arm, len(P), len(O), len(J), (fo == fp).all(),
             "OK" if ok else "*** FAIL ***")
    assert ok
    os.makedirs(D + "/pred", exist_ok=True)
    name = "s1a2x1rn" + arm
    dst = D + "/pred/pred_%s.parquet" % name
    P.astype({"ts": "int64", "sym": "int64", "score": "float32"}).to_parquet(dst, index=False)
    lk = "/home/ubuntu/ledger/pred_%s.parquet" % name
    if not os.path.lexists(lk):
        os.symlink(dst, lk)
    out = D + "/map_" + arm
    build_map(name, out)
    assert len(md5dir(out)) == 16


def model():
    """Tang model OOS 16 fold: xs-rank-corr Spearman per tick (tick >=10 coin), overlap top-16 (tick >16 coin),
    edge5 g1lite. Cap: moi arm vs ORIG + tung cap seed. Ghi model_score.json."""
    arms = ["ORIG"] + [a for a in ARMS + ["KC42"] if os.path.exists(D + "/kout/pred_%s.parquet" % a)]
    M = load_pred("ORIG").rename(columns={"score": "ORIG"})
    for a in arms[1:]:
        M = M.merge(load_pred(a).rename(columns={"score": a}), on=["ts", "sym"], how="inner")
    L = pd.read_parquet("/home/ubuntu/ledger/cand_dev_x1.parquet", columns=["ts", "sym", "g1lite"])
    M = M.merge(L, on=["ts", "sym"], how="left")
    assert M.g1lite.notna().all()
    M["fold"] = fold_of(M.ts)
    g = M.groupby("ts")
    M["n"] = g.ts.transform("size")
    R, T = {}, {}
    for a in arms:
        R[a] = g[a].rank(method="average").to_numpy()
        T[a] = g[a].rank(method="first").to_numpy()
    tick = M.ts.to_numpy()
    out = {"arms": arms, "edge5": {}, "pairs": {}}
    mu = g.g1lite.transform("mean").to_numpy()
    for a in arms:
        e = pd.Series(np.where(T[a] <= 5, M.g1lite.to_numpy() - mu, np.nan)).groupby(tick).mean()
        fo = pd.Series(fold_of(e.index.to_numpy()), index=e.index)
        out["edge5"][a] = dict(all=float(100 * e.mean()), by_fold=[float(100 * v) for v in e.groupby(fo).mean()])
    pairs = [(a, "ORIG") for a in arms[1:]] + [(x, y) for i, x in enumerate(arms[1:]) for y in arms[i + 2:]]
    n = M.n.to_numpy()
    for x, y in pairs:
        rx, ry = R[x], R[y]
        df = pd.DataFrame({"t": tick, "x": rx, "y": ry, "xx": rx * rx, "yy": ry * ry, "xy": rx * ry})
        s = df.groupby("t").sum()
        k = df.groupby("t").size()
        cov = s.xy - s.x * s.y / k
        vx, vy = s.xx - s.x ** 2 / k, s.yy - s.y ** 2 / k
        rho = (cov / np.sqrt(vx * vy))[k >= 10]
        top = pd.Series((T[x] <= 16) & (T[y] <= 16), index=tick).groupby(level=0).sum() / 16.0
        top = top[k.reindex(top.index).to_numpy() > 16]
        fr, ft = fold_of(rho.index.to_numpy()), fold_of(top.index.to_numpy())
        out["pairs"]["%s~%s" % (x, y)] = dict(
            xs_corr_mean=float(rho.mean()), xs_corr_median=float(rho.median()), xs_corr_p10=float(rho.quantile(0.1)),
            xs_corr_by_fold=[float(v) for v in rho.groupby(fr).mean()], top16_overlap=float(top.mean()),
            top16_by_fold=[float(v) for v in top.groupby(ft).mean()], n_ticks=int(len(rho)))
        log.info("PAIR %-10s xs %.4f (med %.4f) top16 %.3f", x + "~" + y, rho.mean(), rho.median(), top.mean())
    del n
    for a in arms:
        log.info("EDGE5 %-5s %+.3f%%", a, out["edge5"][a]["all"])
    k42 = out["pairs"].get("K42~ORIG", {}).get("xs_corr_mean", float("nan"))
    out["gate_K42_xs_ge_080"] = bool(k42 >= 0.80)
    log.info("CONG K42~ORIG xs %.4f >= 0,80: %s", k42, out["gate_K42_xs_ge_080"])
    json.dump(out, open(MODEL_JSON, "w"), indent=1)
    return out["gate_K42_xs_ge_080"]


def shas():
    s0 = SAS.sha256_concat(SAS.src_files([F0MAP, MOC21]))
    want0 = json.load(open(SAD.SHA_JSON))["P0"]
    assert s0 == want0, ("moc21 + deploy16 khong tai lap sha P0", s0, want0)
    out = {"B0_check": s0}
    for a in ARMS:
        if os.path.isdir(D + "/map_" + a):
            out[a] = SAS.sha256_concat(SAS.src_files([D + "/map_" + a, MOC21]))
    json.dump(out, open(SHA_JSON, "w"), indent=1)
    log.info("sha %s", out)


def upload(arm):
    fol = D + "/ds_sim_" + arm
    os.makedirs(fol, exist_ok=True)
    fs = sorted(glob.glob(D + "/map_" + arm + "/predict_wf_*.bin"))
    assert len(fs) == 16, len(fs)
    for f in fs:
        dst = os.path.join(fol, os.path.basename(f))
        if not os.path.exists(dst):
            os.link(f, dst)
    json.dump({"title": DSN[arm], "id": ks.USER + "/" + DSN[arm], "licenses": [{"name": "CC0-1.0"}]},
              open(os.path.join(fol, "dataset-metadata.json"), "w"))
    r = ks._api().dataset_create_new(fol, public=False, quiet=False, dir_mode="skip")
    log.info("upload %s -> %s", arm, getattr(r, "url", r))


def submit(arm, code_sha):
    sh = json.load(open(SHA_JSON))
    tag = TAGS[arm]
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": tag, "profile": SAD.PROFILE, "overrides": dict(SAD.B0OV), "sim_end_date": "20251231", "xmx": "22g",
           "timeout_s": 7200, "code_sha": code_sha, "bins_ds": "", "jar_ds": SAD.JAR_DS, "market_ds": "",
           "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
           "sel_arm": "P0", "fh_arm": arm, "fh_ds": DSN[arm], "want_bins_sha": sh[arm], "src_bins_sha": sh[arm],
           "moc21_ds": SAD.MOC21_DS, "liq_ds": SAD.LIQ_DS, "orig_md5_funding": "8e57d900d5c54c744bfcaf5c9b27fc93"}
    code = LFS.template().replace("__CFG_JSON__", repr(json.dumps(cfg)))
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(code)
    meta = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
            "dataset_sources": [ks.USER + "/" + SAD.BUNDLE] + ks.TICKER_DS
                               + [ks.USER + "/" + SAD.JAR_DS, ks.USER + "/" + SAD.MOC21_DS, ks.USER + "/" + DSN[arm]],
            "competition_sources": [], "kernel_sources": []}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    r = ks._api().kernels_push(folder)
    log.info("push %s -> %s", ref, getattr(r, "url", r))


def b0ref(code_sha):
    assert hashlib.md5(open(REPO + "/tools/kaggle_sim.py", "rb").read()).hexdigest() == SAD.KS_MD5_WANT
    r = ks.submit(B0REF3, SAD.PROFILE, dict(SAD.B0OV), jar_ds=SAD.JAR_DS, bundle_ds=SAD.BUNDLE,
                  sim_end_date="20251231", xmx="22g", timeout_s=5400, code_sha=code_sha)
    log.info("PUSHED b0ref3 %s", r)


def parity():
    """§2.3: B0REF3 (cung dot) vs selab-p0. PASS => B0 = selab-p0; FAIL => B0 = B0REF3."""
    import reset_rule_score as R
    out = SAD.OUT % B0REF3
    if not os.path.exists(out + "storage/printDone.csv"):
        log.info("B0REF3 chua co printDone")
        return None
    md5 = R.md5_of(B0REF3)
    legs = R.load_legs(B0REF3)
    eq = float(R.load_daily(B0REF3)["equity"].iloc[-1])
    ve = SAD.printdone_valeq(B0REF3, B0_TAG)
    same_val = ve["cells_val_diff"] == 0 and ve["rows_a"] == ve["rows_b"]
    ok = (md5 == B0_MD5 or same_val) and len(legs) == SAD.PARITY_N and round(eq) == SAD.PARITY_EQ
    res = dict(ok=bool(ok), md5_b0ref3=md5, md5_eq_ff3ce513=md5 == B0_MD5, n=len(legs), eq=eq, valeq_vs_selab_p0=ve,
               b0_tag=B0_TAG if ok else B0REF3)
    json.dump(res, open(JSON_OUT + ".parity", "w"), indent=1)
    log.info("PARITY B0REF3 %s", res)
    return res


def dist(vals_b0, vals):
    v = np.array(vals, float)
    mu, sd = float(v.mean()), float(v.std(ddof=1))
    return dict(mean=mu, sd=sd, z=float((vals_b0 - mu) / sd) if sd > 0 else float("nan"))


def mde(sd):
    return dict(vsMean=Z80 * sd, one_v_one=Z80 * math.sqrt(2) * sd,
                mxm={str(m): Z80 * sd * math.sqrt(2.0 / m) for m in (1, 2, 3, 5)})


def classify(z):
    if abs(z) < 1:
        return "B0 la realization binh thuong"
    if z > 1.5:
        return "B0 may man"
    if z >= 1:
        return "B0 tren trung binh, chua du goi may man (bien)"
    return "B0 duoi trung binh retrain"


def score(workers):
    import reset_rule_score as R
    import feat_add_v1_score as F  # noqa: F401  (side effect: MTMState cua so 2022+)
    import flat3_crashpen_driver as F3
    R.MTM_COSTS = {"legacy": R.LEGACY}
    par = json.load(open(JSON_OUT + ".parity"))
    b0tag = par["b0_tag"]
    SAD.TAG.update({a: TAGS[a] for a in ARMS})
    SAD.TAG["B0"] = b0tag
    arms = ARMS + ["B0"]
    legs, daily, md5, rjs = {}, {}, {}, {}
    sh = json.load(open(SHA_JSON))
    for k in arms:
        legs[k], daily[k], md5[k] = R.load_legs(SAD.TAG[k]), R.load_daily(SAD.TAG[k]), R.md5_of(SAD.TAG[k])
        rjs[k] = SAD.result_json(k)
        sel = rjs[k].get("sel") or {}
        log.info("%s n=%d eq=%.0f md5=%s jar_ok=%s mapper=%s bins_ok=%s funding=%s", k, len(legs[k]),
                 daily[k]["equity"].iloc[-1], md5[k], rjs[k].get("jar_sha256") == SAD.JAR_SHA,
                 rjs[k].get("symbol_mapper"), sel.get("bins_ok"), str(sel.get("funding_md5"))[:12])
        if k != "B0":
            assert rjs[k].get("jar_sha256") == SAD.JAR_SHA and (rjs[k].get("symbol_mapper") or 0) >= 800, k
            assert sel.get("bins_ok") is True and sel.get("bins_sha256") == sh[k], k
    raw = json.load(open(MTM_CACHE)) if os.path.exists(MTM_CACHE) else {}
    fh = json.load(open(LFS.MTM_CACHE)) if os.path.exists(LFS.MTM_CACHE) else {}
    if "B0" not in raw and fh.get("B0", {}).get("md5") == md5["B0"]:
        raw["B0"] = fh["B0"]
    miss = {k: legs[k] for k in arms if k not in raw or raw[k].get("md5") != md5[k]}
    if miss:
        new = R.run_mtm(miss, workers=workers, chunk=30)
        for k, vv in new.items():
            vv["md5"] = md5[k]
            raw[k] = vv
        json.dump(raw, open(MTM_CACHE, "w"))
    mtm = {k: raw[k]["legacy"] for k in arms}
    M = {k: SAD.arm_metrics(R, F3, k, legs[k], daily[k], mtm[k]) for k in arms}
    eqs = {}
    for k in arms:
        e = daily[k]["equity"]
        eqs["P0" if k == "B0" else k] = e[e.index >= W0]
    obs, bs = SAD.daily_boot(eqs)
    obs["B0"], bs["B0"] = obs.pop("P0"), bs.pop("P0")

    mets = ("cagr", "mdd", "calmar", "sharpe")
    con = {}
    for k in ARMS:
        con[k + "-B0"] = {m: SAD.ci_of(obs[k][m] - obs["B0"][m], bs[k][m] - bs["B0"][m]) for m in mets}
    mS_obs = {m: np.mean([obs[k][m] for k in SEEDS]) for m in mets}
    mS_bs = {m: np.mean([bs[k][m] for k in SEEDS], axis=0) for m in mets}
    con["meanS-B0"] = {m: SAD.ci_of(mS_obs[m] - obs["B0"][m], mS_bs[m] - bs["B0"][m]) for m in mets}
    con["K42-meanS"] = {m: SAD.ci_of(obs["K42"][m] - mS_obs[m], bs["K42"][m] - mS_bs[m]) for m in mets}
    win = {}
    for k in arms:
        Lg = legs[k][legs[k]["ts"] >= pd.Timestamp("2022-01-01")]
        st = Lg["status"].astype(str) if "status" in Lg.columns else None
        e = eqs["P0" if k == "B0" else k]
        win[k] = dict(n=int(len(Lg)), sum_pnl=float(Lg["pnl"].sum()), win=float(100 * (Lg["profit"] > 0).mean()),
                      sl_pct=float(100 * st.str.contains("STOP_LOSS").mean()) if st is not None else float("nan"),
                      eq0=float(e.iloc[0]), eq1=float(e.iloc[-1]), cagr=float(obs[k]["cagr"]),
                      mdd=float(obs[k]["mdd"]), calmar_mtm_daily=float(obs[k]["calmar"]),
                      cagr_full=M[k]["cagr"], dd_mtm_min_full=M[k]["dd_mtm"], calmar_mtm_min_full=M[k]["calmar_mtm"],
                      uw_mtm_days_full=M[k]["uw_mtm"], n_full=M[k]["n"], sum_pnl_full=M[k]["sum_pnl"])
        M[k]["md5"] = md5[k]
        M[k]["overlap_vs_B0"] = SAD.overlap(legs["B0"], legs[k])
    eq0s = {k: round(win[k]["eq0"], 2) for k in arms}
    keys = ("cagr", "mdd", "calmar_mtm_daily", "sum_pnl", "sl_pct", "n", "cagr_full", "dd_mtm_min_full",
            "calmar_mtm_min_full", "uw_mtm_days_full")
    D3, D4 = {}, {}
    for q in keys:
        b = win["B0"][q]
        D3[q] = dist(b, [win[k][q] for k in SEEDS])
        D4[q] = dist(b, [win[k][q] for k in ARMS])
        pool = np.array([b] + [win[k][q] for k in SEEDS], float)
        D3[q]["z_pool"] = float((b - pool.mean()) / pool.std(ddof=1)) if pool.std(ddof=1) > 0 else float("nan")
        D3[q]["rank_b0_desc"] = int((pool > b).sum() + 1)
    sdc, sdk = D3["cagr"]["sd"], D3["calmar_mtm_daily"]["sd"]
    rule = dict(z3_cagr=D3["cagr"]["z"], verdict=classify(D3["cagr"]["z"]),
                z3_calmar=D3["calmar_mtm_daily"]["z"], verdict_calmar=classify(D3["calmar_mtm_daily"]["z"]),
                env_gap_cagr=win["K42"]["cagr"] - win["B0"]["cagr"],
                env_gt_2sd=bool(abs(win["K42"]["cagr"] - win["B0"]["cagr"]) > 2 * sdc),
                mde80_cagr=mde(sdc), mde80_calmar=mde(sdk),
                sd_ci95_factor=[math.sqrt(2 / 7.377759), math.sqrt(2 / 0.050636)])

    log.info("EQ 2021-12-31 %s", eq0s)
    log.info("WIN2022+ %s", json.dumps({k: {q: round(v, 3) if isinstance(v, float) else v for q, v in w.items()}
                                        for k, w in win.items()}))
    log.info("CON %s", {cc: {m: (round(v["d"], 3), [round(z, 3) for z in v["ci_raw"]]) for m, v in d.items()
                             if m in ("cagr", "calmar")} for cc, d in con.items()})
    log.info("DIST3 %s", {q: {a: round(b, 3) for a, b in v.items()} for q, v in D3.items()})
    log.info("ROI nam %s", {k: {y: round(v, 1) for y, v in M[k]["roi_year"].items()} for k in arms})
    log.info("OVERLAP %s", {k: round(M[k]["overlap_vs_B0"]["pct_of_b0"], 1) for k in arms})
    log.info("RULE %s", rule)
    js = dict(prereg="docs/prereg/PREREG_S1_RETRAIN_NOISE.md", prereg_commit="14409eb4", nrep=SAD.NREP,
              seed=SAD.SEED, block_days=SAD.BLOCK_D, k_infl=1, jar_sha256=SAD.JAR_SHA,
              kaggle_sim_md5=SAD.KS_MD5_WANT, bins_sha256=sh, parity=par, tags=dict(SAD.TAG),
              window="2022-01-01..2025-12-30 (equity ngay tu 2021-12-31)", eq_20211231=eq0s, win=win,
              dist_seeds3=D3, dist_kaggle4=D4, contrasts=con, rule=rule, boot_obs=obs, metrics=M,
              model=json.load(open(MODEL_JSON)) if os.path.exists(MODEL_JSON) else None,
              map_parity=json.load(open(D + "/map_parity.json")) if os.path.exists(D + "/map_parity.json") else None)
    json.dump(js, open(JSON_OUT, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", JSON_OUT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["mapparity", "prep", "model", "shas", "upload", "submit", "b0ref", "wait",
                                    "fetch", "parity", "score"])
    ap.add_argument("arms", nargs="*")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--code-sha", default="14409eb4")
    a = ap.parse_args()
    arms = a.arms or list(ARMS)
    if a.cmd == "mapparity":
        sys.exit(0 if mapparity() else 3)
    elif a.cmd == "prep":
        for x in arms:
            prep(x)
    elif a.cmd == "model":
        sys.exit(0 if model() else 3)
    elif a.cmd == "shas":
        shas()
    elif a.cmd == "upload":
        for x in arms:
            upload(x)
    elif a.cmd == "submit":
        log.info("free_slots=%d", ks.free_slots())
        for x in arms:
            submit(x, a.code_sha)
    elif a.cmd == "b0ref":
        b0ref(a.code_sha)
    elif a.cmd == "wait":
        refs = [ks.kernel_ref(TAGS[x]) if x in TAGS else ks.kernel_ref(x) for x in arms]
        log.info("%s", ks.wait(refs, poll_s=120, timeout_s=5 * 3600))
    elif a.cmd == "fetch":
        for x in arms:
            o = ks.fetch(TAGS[x] if x in TAGS else x)
            log.info("%s %s", x, json.dumps(o.get("result"), default=str)[:600])
    elif a.cmd == "parity":
        r = parity()
        sys.exit(0 if r and r["ok"] else 3)
    else:
        score(a.workers)


if __name__ == "__main__":
    main()
