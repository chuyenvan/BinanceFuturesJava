#!/usr/bin/env python3
"""LABEL_FIRSTHIT — SIM 2 arm (FH, CTRL) tren nen G2+FLAT3 (pre-reg docs/prereg/PREREG_LABEL_FIRSTHIT.md §4).

Tai dung DUONG SELECTOR_ABLATION (research/analysis/selector_ablation_driver.py: kernel tools/kaggle_sim.py HEAD
NOWRITE242 md5 8b60b00a + SA_BLOCK dung lai funding.bin bang s3_funding.py), CHI doi nguon bins arm:
16 bins map s1a2x1 cua arm (dataset rieng fh-sim-bins-<arm>) + 2 fold 2021H2 cua MOC (s3-moc-2021bins) ->
SAS.gen_arm("P0") (= sao chep nguyen) -> assert sha256 == ban Oracle -> funding.bin -> sim. jar/profile/gate/exit/
sizing GIU NGUYEN B0. KHONG Java tren Oracle, khong sua .java.
Usage: python3 label_firsthit_sim.py shas | upload FH CTRL | submit FH CTRL | wait FH CTRL | fetch FH CTRL | score
"""
import argparse, glob, json, logging, math, os, shutil, sys
import numpy as np
import pandas as pd
REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
import selector_ablation_driver as SAD  # noqa: E402
import selector_ablation_scores as SAS  # noqa: E402
from tools import kaggle_sim as ks  # noqa: E402
log = logging.getLogger("fh_sim")
D = "/home/ubuntu/claude_master/1003/fh"
TAGS = {"FH": "fhsim-fh", "CTRL": "fhsim-ctrl"}
DSN = {"FH": "fh-sim-bins-fh", "CTRL": "fh-sim-bins-ctrl"}
MOC21 = D + "/moc21"
SHA_JSON = D + "/sim_sha256.json"
JSON_OUT = os.path.join(REPO, "docs/result/label_firsthit.json")
MTM_CACHE = D + "/sim_mtm.json"
W0 = pd.Timestamp("2021-12-31")      # equity ngay 2021-12-31 -> cua so so 2022+
SAD.TAG.update({"FH": TAGS["FH"], "CTRL": TAGS["CTRL"], "B0": "selab-p0"})


def shas():
    os.makedirs(MOC21, exist_ok=True)
    for f in ("predict_wf_20210701.bin", "predict_wf_20211001.bin"):
        if not os.path.exists(os.path.join(MOC21, f)):
            shutil.copy2(os.path.join("/home/ubuntu/claude_master/1003/sa/bins/P0", f), MOC21)
    s0 = SAS.sha256_concat(SAS.src_files(["/home/ubuntu/predwf_map_s1a2_x1", MOC21]))
    want0 = json.load(open(SAD.SHA_JSON))["P0"]
    assert s0 == want0, ("moc21 + deploy16 khong tai lap sha P0", s0, want0)
    out = {"B0_check": s0}
    for a in TAGS:
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


def template():
    t = SAD.build_template()
    old1 = '    _b16 = sorted(glob.glob(DS + "/predict_wf_*.bin"))\n'
    new1 = ('    # [LABEL_FIRSTHIT] nguon 16 bins = dataset arm (map s1a2x1 cua model FH/CTRL), KHONG phai bins bundle\n'
            '    _fhc = [c for c in sorted(glob.glob(IN + "/**/predict_wf_20220101.bin", recursive=True))\n'
            '            if ("/" + CFG["fh_ds"] + "/") in c]\n'
            '    _FHD = os.path.dirname(_fhc[0]) if _fhc else DS + "/__khong_co_fh_ds__"\n'
            '    LOG.info("FH bins dir %s", _FHD)\n'
            '    _b16 = sorted(glob.glob(_FHD + "/predict_wf_*.bin"))\n')
    old2 = '    _files = SAS.src_files([DS, os.path.dirname(_c21[0])])\n'
    new2 = '    _files = SAS.src_files([_FHD, os.path.dirname(_c21[0])])\n'
    for o, n in ((old1, new1), (old2, new2)):
        assert t.count(o) == 1, o
        t = t.replace(o, n)
    return t


def submit(arm, push=True):
    sh = json.load(open(SHA_JSON))
    tag = TAGS[arm]
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": tag, "profile": SAD.PROFILE, "overrides": dict(SAD.B0OV), "sim_end_date": "20251231", "xmx": "22g",
           "timeout_s": 7200, "code_sha": "head", "bins_ds": "", "jar_ds": SAD.JAR_DS, "market_ds": "",
           "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
           "sel_arm": "P0", "fh_arm": arm, "fh_ds": DSN[arm], "want_bins_sha": sh[arm], "src_bins_sha": sh[arm],
           "moc21_ds": SAD.MOC21_DS, "liq_ds": SAD.LIQ_DS, "orig_md5_funding": "8e57d900d5c54c744bfcaf5c9b27fc93"}
    code = template().replace("__CFG_JSON__", repr(json.dumps(cfg)))
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(code)
    meta = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
            "dataset_sources": [ks.USER + "/" + SAD.BUNDLE] + ks.TICKER_DS
                               + [ks.USER + "/" + SAD.JAR_DS, ks.USER + "/" + SAD.MOC21_DS, ks.USER + "/" + DSN[arm]],
            "competition_sources": [], "kernel_sources": []}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    if push:
        r = ks._api().kernels_push(folder)
        log.info("push %s -> %s", ref, getattr(r, "url", r))
    return ref


def score(workers):
    import reset_rule_score as R
    import feat_add_v1_score as F  # noqa: F401  (side effect: MTMState cua so 2022+)
    import flat3_crashpen_driver as F3
    R.MTM_COSTS = {"legacy": R.LEGACY}
    arms = ["FH", "CTRL", "B0"]
    legs, daily, md5, rjs = {}, {}, {}, {}
    for k in arms:
        legs[k], daily[k], md5[k] = R.load_legs(SAD.TAG[k]), R.load_daily(SAD.TAG[k]), R.md5_of(SAD.TAG[k])
        rjs[k] = SAD.result_json(k)
        sel = rjs[k].get("sel") or {}
        log.info("%s n=%d eq=%.0f md5=%s jar_ok=%s mapper=%s bins_ok=%s bins=%s funding=%s", k, len(legs[k]),
                 daily[k]["equity"].iloc[-1], md5[k], rjs[k].get("jar_sha256") == SAD.JAR_SHA,
                 rjs[k].get("symbol_mapper"), sel.get("bins_ok"), str(sel.get("bins_sha256"))[:12],
                 str(sel.get("funding_md5"))[:12])
        if rjs[k].get("jar_sha256") != SAD.JAR_SHA or (rjs[k].get("symbol_mapper") or 0) < 800 \
                or sel.get("bins_ok") is not True:
            log.info("*** arm %s sai jar/mapper/bins => DUNG", k)
            sys.exit(4)
    sh = json.load(open(SHA_JSON))
    for k in ("FH", "CTRL"):
        assert (rjs[k].get("sel") or {}).get("bins_sha256") == sh[k], k
    raw = json.load(open(MTM_CACHE)) if os.path.exists(MTM_CACHE) else {}
    sa = json.load(open(SAD.MTM_CACHE)) if os.path.exists(SAD.MTM_CACHE) else {}
    if "B0" not in raw and sa.get("P0", {}).get("md5") == md5["B0"]:
        raw["B0"] = sa["P0"]
    miss = {k: legs[k] for k in arms if k not in raw or raw[k].get("md5") != md5[k]}
    if miss:
        new = R.run_mtm(miss, workers=workers, chunk=30)
        for k, vv in new.items():
            vv["md5"] = md5[k]
            raw[k] = vv
        json.dump(raw, open(MTM_CACHE, "w"))
    mtm = {k: raw[k]["legacy"] for k in arms}
    M = {k: SAD.arm_metrics(R, F3, k, legs[k], daily[k], mtm[k]) for k in arms}
    # cua so 2022+: equity ngay tu 2021-12-31; lenh vao >= 2022-01-01
    eqs = {}
    for k in arms:
        e = daily[k]["equity"]
        eqs["P0" if k == "FH" else k] = e[e.index >= W0]
    obs, bs = SAD.daily_boot(eqs)
    obs["FH"], bs["FH"] = obs.pop("P0"), bs.pop("P0")
    con = {}
    for x, y in (("FH", "CTRL"), ("FH", "B0"), ("CTRL", "B0")):
        con["%s-%s" % (x, y)] = {m: SAD.ci_of(obs[x][m] - obs[y][m], bs[x][m] - bs[y][m])
                                 for m in ("cagr", "mdd", "calmar", "sharpe")}
    win = {}
    for k in arms:
        L = legs[k][legs[k]["ts"] >= pd.Timestamp("2022-01-01")]
        st = L["status"].astype(str) if "status" in L.columns else None
        sl = float(100 * st.str.contains("STOP_LOSS").mean()) if st is not None else float("nan")
        win[k] = dict(n=int(len(L)), sum_pnl=float(L["pnl"].sum()), win=float(100 * (L["profit"] > 0).mean()),
                      mean_roi=float(L["profit"].mean()), median_roi=float(L["profit"].median()), sl_pct=sl,
                      eq0=float(eqs["P0" if k == "FH" else k].iloc[0]), eq1=float(eqs["P0" if k == "FH" else k].iloc[-1]),
                      calmar_mtm_daily=float(obs[k]["calmar"]), cagr=float(obs[k]["cagr"]), mdd=float(obs[k]["mdd"]))
    yrs = {yy: M["FH"]["roi_year"].get(str(yy), np.nan) - M["CTRL"]["roi_year"].get(str(yy), np.nan)
           for yy in SAD.GO_YEARS}
    npos = int(sum(1 for v in yrs.values() if v > 0))
    c = con["FH-CTRL"]["calmar"]
    go = bool(c["ci_raw"][0] > 0 and npos >= 3 and win["FH"]["sl_pct"] < win["CTRL"]["sl_pct"])
    rule = dict(GO_sim=go, calmar_ci_lo_gt0=c["ci_raw"][0] > 0, years_fh_minus_ctrl=yrs, years_pos=npos,
                sl_fh_lt_ctrl=win["FH"]["sl_pct"] < win["CTRL"]["sl_pct"],
                rule="dCalmar_MTM(ngay, 2022+) FH-CTRL CI95 block-10d >0 VA >=3/4 nam ROI FH>CTRL VA SL% FH<CTRL")
    for k in arms:
        M[k]["md5"] = md5[k]
        M[k]["overlap_vs_B0"] = SAD.overlap(legs["B0"], legs[k])
    log.info("WIN2022+ %s", json.dumps(win, indent=0))
    log.info("CON %s", {cc: {m: (round(v["d"], 3), [round(z, 3) for z in v["ci_raw"]]) for m, v in d.items()}
                        for cc, d in con.items()})
    log.info("ROI nam %s", {k: {y: round(v, 1) for y, v in M[k]["roi_year"].items()} for k in arms})
    log.info("GO_sim %s %s", go, rule)
    js = dict(prereg="docs/prereg/PREREG_LABEL_FIRSTHIT.md", nrep=SAD.NREP, seed=SAD.SEED, block_days=SAD.BLOCK_D,
              k_infl=1, jar_sha256=SAD.JAR_SHA, kaggle_sim_md5=SAD.KS_MD5_WANT, bins_sha256=sh,
              window="2022-01-01..2025-12-30 (equity ngay tu 2021-12-31)", win=win, boot_obs=obs,
              contrasts=con, rule=rule, metrics=M)
    json.dump(js, open(D + "/sim_score.json", "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s/sim_score.json", D)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["shas", "template", "upload", "submit", "wait", "fetch", "score"])
    ap.add_argument("arms", nargs="*")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    arms = a.arms or list(TAGS)
    if a.cmd == "shas":
        shas()
    elif a.cmd == "template":
        t = template()
        open(D + "/sim_kernel_template.py", "w").write(t)
        log.info("template ok %d bytes", len(t))
    elif a.cmd == "upload":
        for x in arms:
            upload(x)
    elif a.cmd == "submit":
        log.info("free_slots=%d", ks.free_slots())
        for x in arms:
            submit(x)
    elif a.cmd == "wait":
        log.info("%s", ks.wait([ks.kernel_ref(TAGS[x]) for x in arms], poll_s=120, timeout_s=5 * 3600))
    elif a.cmd == "fetch":
        for x in arms:
            o = ks.fetch(TAGS[x])
            log.info("%s %s", x, json.dumps(o.get("result"), default=str)[:800])
    else:
        score(a.workers)


if __name__ == "__main__":
    main()
