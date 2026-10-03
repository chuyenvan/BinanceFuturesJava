#!/usr/bin/env python3
"""S1_FIRSTHIT_RANK — prep/map/model-score/sim/score. Pre-reg docs/prereg/PREREG_S1_FIRSTHIT_RANK.md.
Duong sim = S1_RETRAIN_NOISE (s1_retrain_noise_sim.py: kaggle_sim HEAD NOWRITE242 md5 8b60b00a, template LABEL_FIRSTHIT),
CHI doi nguon 16 bins arm = map s1a2x1 (tren bins DEPLOY, A1) cua pred S1 target first-hit (FHP/FHL x seed 42/7).
CTRL = K42 + S7 cua S1_RETRAIN_NOISE (sim s1rn-k42/s1rn-s7, cung dot GPU). B0 = selab-p0 (parity B0REF4).
Usage: python3 s1_fhrank_sim.py mapparity | prep ARM.. | model | shas | upload ARM.. | submit ARM.. | b0ref
       | wait ARM.. | fetch ARM.. | parity | score
"""
import argparse, glob, hashlib, json, logging, os, shutil, subprocess, sys
import numpy as np
import pandas as pd
REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
import selector_ablation_driver as SAD  # noqa: E402
import selector_ablation_scores as SAS  # noqa: E402
import label_firsthit_sim as LFS  # noqa: E402
import s1_retrain_noise_sim as RN  # noqa: E402
from tools import kaggle_sim as ks  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("fhr")
D = "/home/ubuntu/claude_master/1003/fhr"
RND = "/home/ubuntu/claude_master/1003/s1rn"
ARMS = ["FHP42", "FHP7", "FHL42", "FHL7"]
FAM = {"FHP": ["FHP42", "FHP7"], "FHL": ["FHL42", "FHL7"], "CTRL": ["K42", "S7"]}
TAGS = {a: "fhr-" + a.lower() for a in ARMS}
TAGS.update({"K42": "s1rn-k42", "S7": "s1rn-s7"})
DSN = {a: "fhr-bins-" + a.lower() for a in ARMS}
B0REF4 = "fhr-b0ref4"
SHA_JSON = D + "/sim_sha256.json"
MTM_CACHE = D + "/sim_mtm.json"
MODEL_JSON = D + "/model_score.json"
JSON_OUT = os.path.join(REPO, "docs/result/s1_fhrank.json")
YFH = D + "/kds/yfh_x1.parquet"
SAD.INFL, SAD.K_INFL = 1.18, 2   # pre-reg: k = 2 arm (FHP, FHL) => CI inflate 1,18
GAP_R50 = 14.71                   # B0 - mean R50 CAGR pp (b7fedef4)


def mapparity():
    assert RN.sha256f(RN.ORIG_PRED) == RN.ORIG_SHA, "pred_s1a2x1 goc da doi"
    chk = D + "/map_ORIGchk"
    RN.build_map("s1a2x1", chk)
    a, b = RN.md5dir(chk), RN.md5dir(RN.F0MAP)
    ok = len(a) == 16 and a == b
    json.dump(dict(ok=ok, n=len(a), md5=a), open(D + "/map_parity.json", "w"), indent=1)
    shutil.rmtree(chk)
    log.info("MAP_PARITY_%s (%d/16 file)", "PASS" if ok else "FAIL", sum(a.get(k) == v for k, v in b.items()))
    return ok


def load_pred(arm):
    if arm == "ORIG":
        p = RN.ORIG_PRED
    elif arm in ("K42", "S7"):
        p = RND + "/kout/pred_%s.parquet" % arm
    else:
        p = D + "/kout/pred_%s.parquet" % arm
    return pd.read_parquet(p, columns=["ts", "sym", "score"])


def prep(arm):
    P, O = load_pred(arm), load_pred("ORIG")
    assert np.isfinite(P.score).all(), "score NaN/Inf"
    assert not P.duplicated(["ts", "sym"]).any()
    J = O[["ts", "sym"]].merge(P[["ts", "sym"]], on=["ts", "sym"], how="inner")
    fo, fp = np.bincount(RN.fold_of(O.ts), minlength=16), np.bincount(RN.fold_of(P.ts), minlength=16)
    ok = len(P) == len(O) == len(J) and (fo == fp).all() and RN.fold_of(P.ts).min() >= 0
    log.info("PREP %s rows %d orig %d join %d fold_eq %s -> %s", arm, len(P), len(O), len(J), (fo == fp).all(),
             "OK" if ok else "*** FAIL ***")
    assert ok
    os.makedirs(D + "/pred", exist_ok=True)
    name = "s1a2x1fhr" + arm
    dst = D + "/pred/pred_%s.parquet" % name
    P.astype({"ts": "int64", "sym": "int64", "score": "float32"}).to_parquet(dst, index=False)
    lk = "/home/ubuntu/ledger/pred_%s.parquet" % name
    if not os.path.lexists(lk):
        os.symlink(dst, lk)
    out = D + "/map_" + arm
    RN.build_map(name, out)
    assert len(RN.md5dir(out)) == 16


def tick_corr(t, x, y, kmin=10):
    """Pearson per tick tren (x, y) (dua vao hang => Spearman). Tra Series theo tick (tick co >= kmin dong)."""
    df = pd.DataFrame({"t": t, "x": x, "y": y, "xx": x * x, "yy": y * y, "xy": x * y})
    s = df.groupby("t").sum()
    k = df.groupby("t").size()
    cov = s.xy - s.x * s.y / k
    vx, vy = s.xx - s.x ** 2 / k, s.yy - s.y ** 2 / k
    r = cov / np.sqrt(vx * vy)
    return r[(k >= kmin) & (vx > 0) & (vy > 0)]


def agg(s):
    """mean toan ky + theo fold + theo nam cua Series index = tick."""
    fo = RN.fold_of(s.index.to_numpy())
    yr = pd.to_datetime(s.index.to_numpy(), unit="ms").year
    return dict(all=float(s.mean()), n_ticks=int(s.notna().sum()),
                by_fold=[float(v) for v in s.groupby(fo).mean().reindex(range(16)).to_numpy()],
                by_year={int(k): float(v) for k, v in s.groupby(yr).mean().items()})


def model():
    """Tang model OOS 16 fold (chi bao cao): rank-IC vs y_FH & vs g1lite (nhan S1 cu), lift@16, precision@16 leg xau
    (hit SL/tie truoc), NDCG@16 nhi phan, xs-rank-corr & top-16 overlap vs ORIG. Ghi model_score.json."""
    arms = ["ORIG", "K42", "S7"] + [a for a in ARMS if os.path.exists(D + "/kout/pred_%s.parquet" % a)]
    M = load_pred("ORIG").rename(columns={"score": "ORIG"})
    for a in arms[1:]:
        M = M.merge(load_pred(a).rename(columns={"score": a}), on=["ts", "sym"], how="inner")
    Lg = pd.read_parquet("/home/ubuntu/ledger/cand_dev_x1.parquet", columns=["ts", "sym", "g1lite"])
    M = M.merge(Lg, on=["ts", "sym"], how="left").merge(pd.read_parquet(YFH), on=["ts", "sym"], how="left")
    assert M.g1lite.notna().all() and M.yfh.notna().all()
    M = M.sort_values(["ts", "sym"]).reset_index(drop=True)
    g = M.groupby("ts")
    tick = M.ts.to_numpy()
    lab = (M.yfh >= 0).to_numpy()
    y = M.yfh.to_numpy().astype(float)
    bad = M.hit.isin([2, 3]).to_numpy().astype(float)
    Ml = M[lab].copy()
    gl = Ml.groupby("ts")
    ry = gl.yfh.rank(method="average").to_numpy()
    rg = g.g1lite.rank(method="average").to_numpy()
    nl = gl.ts.transform("size").to_numpy()
    npos = gl.yfh.transform("sum").to_numpy()
    out = {"arms": arms, "coverage_oos_rows": float(lab.mean()), "metrics": {}, "pairs": {}}
    base_y = pd.Series(np.where(lab, y, np.nan)).groupby(tick).mean()
    base_bad = pd.Series(np.where(lab, bad, np.nan)).groupby(tick).mean()
    out["ALL"] = dict(yfh=agg(base_y), bad=agg(base_bad))
    disc = 1.0 / np.log2(np.arange(2, 18))
    for a in arms:
        Rf = g[a].rank(method="average", ascending=False).to_numpy()   # cao = tot
        T = g[a].rank(method="first").to_numpy()                   # 1 = tot nhat
        ic_y = tick_corr(Ml.ts.to_numpy(), gl[a].rank(method="average", ascending=False).to_numpy(), ry)
        ic_g = tick_corr(tick, Rf, rg)
        top = (T <= 16) & lab
        mid = (T > 16) & (T <= 50) & lab
        t16 = pd.Series(np.where(top, y, np.nan)).groupby(tick).mean()
        m50 = pd.Series(np.where(mid, y, np.nan)).groupby(tick).mean()
        lift = (t16 - m50).dropna()
        pbad = pd.Series(np.where(top, bad, np.nan)).groupby(tick).mean().dropna()
        Tl = gl[a].rank(method="first").to_numpy().astype(int)
        dcg = pd.Series(np.where(Tl <= 16, Ml.yfh.to_numpy() * disc[np.minimum(Tl, 16) - 1], 0.0)).groupby(
            Ml.ts.to_numpy()).sum()
        ip = pd.Series(np.minimum(npos, 16).astype(int), index=Ml.ts.to_numpy()).groupby(level=0).first()
        cdisc = np.concatenate(([0.0], np.cumsum(disc)))
        idcg = pd.Series(cdisc[ip.to_numpy()], index=ip.index)
        kk = pd.Series(nl, index=Ml.ts.to_numpy()).groupby(level=0).first()
        okt = (idcg > 0) & (kk > 16)
        sel = okt.index[okt.to_numpy()]
        ndcg = (dcg.reindex(sel) / idcg.reindex(sel)).dropna()
        out["metrics"][a] = dict(ic_yfh=agg(ic_y), ic_g1lite=agg(ic_g), lift16=agg(lift), yfh_top16=agg(t16.dropna()),
                                 yfh_17_50=agg(m50.dropna()), prec_bad16=agg(pbad), ndcg16=agg(ndcg))
        log.info("MODEL %-5s IC_yFH %+.4f IC_g1 %+.4f lift16 %+.4f top16 yFH %.4f bad@16 %.4f NDCG@16 %.4f", a,
                 ic_y.mean(), ic_g.mean(), lift.mean(), t16.mean(), pbad.mean(), ndcg.mean())
        if a != "ORIG":
            T0 = g["ORIG"].rank(method="first").to_numpy()
            R0 = g["ORIG"].rank(method="average", ascending=False).to_numpy()
            xs = tick_corr(tick, Rf, R0)
            ov = pd.Series((T <= 16) & (T0 <= 16)).groupby(tick).sum() / 16.0
            n = g.ts.size()
            ov = ov[n.reindex(ov.index).to_numpy() > 16]
            out["pairs"][a + "~ORIG"] = dict(xs=agg(xs), top16_overlap=agg(ov))
            log.info("PAIR %-5s~ORIG xs %.4f top16 %.3f", a, xs.mean(), ov.mean())
    json.dump(out, open(MODEL_JSON, "w"), indent=1)
    return True


def shas():
    s0 = SAS.sha256_concat(SAS.src_files([RN.F0MAP, RN.MOC21]))
    want0 = json.load(open(SAD.SHA_JSON))["P0"]
    assert s0 == want0, ("moc21 + deploy16 khong tai lap sha P0", s0, want0)
    out = {"B0_check": s0}
    rn = json.load(open(RND + "/sim_sha256.json"))
    out["K42"], out["S7"] = rn["K42"], rn["S7"]
    for a in ARMS:
        if os.path.isdir(D + "/map_" + a):
            out[a] = SAS.sha256_concat(SAS.src_files([D + "/map_" + a, RN.MOC21]))
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
    r = ks.submit(B0REF4, SAD.PROFILE, dict(SAD.B0OV), jar_ds=SAD.JAR_DS, bundle_ds=SAD.BUNDLE,
                  sim_end_date="20251231", xmx="22g", timeout_s=5400, code_sha=code_sha)
    log.info("PUSHED b0ref4 %s", r)


def parity():
    """B0REF4 (cung dot) vs selab-p0. PASS => B0 = selab-p0; FAIL => B0 = B0REF4 (va CTRL cu nghi ngo anh doi)."""
    import reset_rule_score as R
    out = SAD.OUT % B0REF4
    if not os.path.exists(out + "storage/printDone.csv"):
        log.info("B0REF4 chua co printDone")
        return None
    md5 = R.md5_of(B0REF4)
    legs = R.load_legs(B0REF4)
    eq = float(R.load_daily(B0REF4)["equity"].iloc[-1])
    ve = SAD.printdone_valeq(B0REF4, RN.B0_TAG)
    same_val = ve["cells_val_diff"] == 0 and ve["rows_a"] == ve["rows_b"]
    ok = (md5 == RN.B0_MD5 or same_val) and len(legs) == SAD.PARITY_N and round(eq) == SAD.PARITY_EQ
    res = dict(ok=bool(ok), md5_b0ref4=md5, md5_eq_ff3ce513=md5 == RN.B0_MD5, n=len(legs), eq=eq,
               valeq_vs_selab_p0=ve, b0_tag=RN.B0_TAG if ok else B0REF4)
    json.dump(res, open(JSON_OUT + ".parity", "w"), indent=1)
    log.info("PARITY B0REF4 %s", res)
    return res


def fam_mean(d, members):
    return {m: np.mean([d[k][m] for k in members], axis=0) for m in ("cagr", "mdd", "calmar", "sharpe")}


def score(workers):
    import reset_rule_score as R
    import feat_add_v1_score as F  # noqa: F401  (side effect: MTMState cua so 2022+)
    import flat3_crashpen_driver as F3
    R.MTM_COSTS = {"legacy": R.LEGACY}
    par = json.load(open(JSON_OUT + ".parity"))
    SAD.TAG.update(TAGS)
    SAD.TAG["B0"] = par["b0_tag"]
    arms = ARMS + ["K42", "S7", "B0"]
    legs, daily, md5, rjs = {}, {}, {}, {}
    sh = json.load(open(SHA_JSON))
    for k in arms:
        legs[k], daily[k], md5[k] = R.load_legs(SAD.TAG[k]), R.load_daily(SAD.TAG[k]), R.md5_of(SAD.TAG[k])
        rjs[k] = SAD.result_json(k)
        sel = rjs[k].get("sel") or {}
        log.info("%s n=%d eq=%.0f md5=%s jar_ok=%s mapper=%s bins_ok=%s", k, len(legs[k]), daily[k]["equity"].iloc[-1],
                 md5[k], rjs[k].get("jar_sha256") == SAD.JAR_SHA, rjs[k].get("symbol_mapper"), sel.get("bins_ok"))
        if k != "B0":
            assert rjs[k].get("jar_sha256") == SAD.JAR_SHA and (rjs[k].get("symbol_mapper") or 0) >= 800, k
            assert sel.get("bins_ok") is True and sel.get("bins_sha256") == sh[k], k
    raw = json.load(open(MTM_CACHE)) if os.path.exists(MTM_CACHE) else {}
    rn = json.load(open(RN.MTM_CACHE)) if os.path.exists(RN.MTM_CACHE) else {}
    for k in ("K42", "S7", "B0"):
        if k not in raw and rn.get(k, {}).get("md5") == md5[k]:
            raw[k] = rn[k]
    miss = {k: legs[k] for k in arms if k not in raw or raw[k].get("md5") != md5[k]}
    if miss:
        new = R.run_mtm(miss, workers=workers, chunk=30)
        for k, vv in new.items():
            vv["md5"] = md5[k]
            raw[k] = vv
        json.dump(raw, open(MTM_CACHE, "w"))
    mtm = {k: raw[k]["legacy"] for k in arms}
    M = {k: SAD.arm_metrics(R, F3, k, legs[k], daily[k], mtm[k]) for k in arms}
    eqs = {("P0" if k == "B0" else k): daily[k]["equity"][daily[k]["equity"].index >= RN.W0] for k in arms}
    obs, bs = SAD.daily_boot(eqs)
    obs["B0"], bs["B0"] = obs.pop("P0"), bs.pop("P0")
    for f, mem in FAM.items():
        obs[f], bs[f] = fam_mean(obs, mem), fam_mean(bs, mem)
    mets = ("cagr", "mdd", "calmar", "sharpe")
    pairs = [("FHP", "CTRL"), ("FHL", "CTRL"), ("FHL", "FHP"), ("FHP", "B0"), ("FHL", "B0"), ("CTRL", "B0")]
    pairs += [(a, "CTRL") for a in ARMS] + [(a, "B0") for a in ARMS]
    con = {x + "-" + y: {m: SAD.ci_of(obs[x][m] - obs[y][m], bs[x][m] - bs[y][m]) for m in mets} for x, y in pairs}
    finish(legs, daily, M, obs, con, sh, par, md5)


def finish(legs, daily, M, obs, con, sh, par, md5):
    arms = ARMS + ["K42", "S7", "B0"]
    win = {}
    for k in arms:
        Lg = legs[k][legs[k]["ts"] >= pd.Timestamp("2022-01-01")]
        st = Lg["status"].astype(str)
        e = daily[k]["equity"][daily[k]["equity"].index >= RN.W0]
        ov = SAD.overlap(legs["B0"], legs[k])
        win[k] = dict(n=int(len(Lg)), sum_pnl=float(Lg["pnl"].sum()), win=float(100 * (Lg["profit"] > 0).mean()),
                      sl_pct=float(100 * st.str.contains("STOP_LOSS").mean()), eq0=float(e.iloc[0]),
                      eq1=float(e.iloc[-1]), cagr=float(obs[k]["cagr"]), mdd=float(obs[k]["mdd"]),
                      calmar=float(obs[k]["calmar"]), uw_mtm_days_full=M[k]["uw_mtm"],
                      dd_mtm_min_full=M[k]["dd_mtm"], overlap_b0=ov["pct_of_b0"], jaccard_b0=ov["jaccard"],
                      roi_year={y: M[k]["roi_year"].get(y, float("nan")) for y in ("2022", "2023", "2024", "2025")})
    keys = ("n", "sum_pnl", "win", "sl_pct", "cagr", "mdd", "calmar", "uw_mtm_days_full", "dd_mtm_min_full",
            "overlap_b0", "jaccard_b0")
    for f, mem in FAM.items():
        win[f] = {q: float(np.mean([win[k][q] for k in mem])) for q in keys}
        win[f]["roi_year"] = {y: float(np.mean([win[k]["roi_year"][y] for k in mem])) for y in ("2022", "2023", "2024", "2025")}
    rule = {}
    for f in ("FHP", "FHL"):
        c, cb = con[f + "-CTRL"], con[f + "-B0"]
        yrs = {y: win[f]["roi_year"][y] - win["CTRL"]["roi_year"][y] for y in ("2022", "2023", "2024", "2025")}
        c1 = c["cagr"]["d"] >= 3.3
        c2 = c["calmar"]["ci_infl"][0] > 0
        c3 = sum(v > 0 for v in yrs.values()) >= 3
        c4 = win[f]["sl_pct"] <= win["CTRL"]["sl_pct"]
        c5 = cb["cagr"]["ci_infl"][1] > 0
        rule[f] = dict(dcagr_vs_ctrl=c["cagr"]["d"], c1_dcagr_ge_3_3=bool(c1),
                       dcalmar_vs_ctrl=c["calmar"]["d"], dcalmar_ci_infl=c["calmar"]["ci_infl"], c2_calmar_ci_gt0=bool(c2),
                       years_vs_ctrl=yrs, c3_years_ge3=bool(c3), c4_sl_le_ctrl=bool(c4),
                       dcagr_vs_b0_ci_infl=cb["cagr"]["ci_infl"], c5_b0_ci_not_below0=bool(c5),
                       frac_gap_r50=c["cagr"]["d"] / GAP_R50, GO=bool(c1 and c2 and c3 and c4 and c5))
    verdict = "GO" if any(r["GO"] for r in rule.values()) else "NO-GO"
    log.info("WIN %s", json.dumps({k: {q: (round(v, 3) if isinstance(v, float) else v) for q, v in w.items()}
                                    for k, w in win.items()}, default=str))
    log.info("CON %s", {cc: {m: (round(v["d"], 3), [round(z, 3) for z in v["ci_infl"]]) for m, v in d.items()
                             if m in ("cagr", "calmar", "mdd")} for cc, d in con.items()})
    log.info("RULE %s", json.dumps(rule, default=str))
    log.info("VERDICT %s", verdict)
    js = dict(prereg="docs/prereg/PREREG_S1_FIRSTHIT_RANK.md", nrep=SAD.NREP, seed=SAD.SEED, block_days=SAD.BLOCK_D,
              k_infl=SAD.K_INFL, inflate=SAD.INFL, jar_sha256=SAD.JAR_SHA, kaggle_sim_md5=SAD.KS_MD5_WANT,
              bins_sha256=sh, parity=par, tags=dict(SAD.TAG), md5=md5,
              window="2022-01-01..2025-12-30 (equity ngay tu 2021-12-31)", win=win, contrasts=con, rule=rule,
              verdict=verdict, boot_obs=obs, metrics=M,
              model=json.load(open(MODEL_JSON)) if os.path.exists(MODEL_JSON) else None,
              coverage=json.load(open(D + "/coverage.json")),
              map_parity=json.load(open(D + "/map_parity.json")) if os.path.exists(D + "/map_parity.json") else None)
    json.dump(js, open(JSON_OUT, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", JSON_OUT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["mapparity", "prep", "model", "shas", "upload", "submit", "b0ref", "wait",
                                    "fetch", "parity", "score"])
    ap.add_argument("arms", nargs="*")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--code-sha", default="")
    a = ap.parse_args()
    arms = a.arms or list(ARMS)
    if a.cmd == "mapparity":
        sys.exit(0 if mapparity() else 3)
    elif a.cmd == "prep":
        for x in arms:
            prep(x)
    elif a.cmd == "model":
        model()
    elif a.cmd == "shas":
        shas()
    elif a.cmd == "upload":
        for x in arms:
            upload(x)
    elif a.cmd == "submit":
        assert a.code_sha
        log.info("free_slots=%d", ks.free_slots())
        for x in arms:
            submit(x, a.code_sha)
    elif a.cmd == "b0ref":
        assert a.code_sha
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
