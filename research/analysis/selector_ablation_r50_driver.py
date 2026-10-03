#!/usr/bin/env python3
"""SELECTOR_ABLATION_R50 driver — submit/wait/fetch/parity/score. Pre-reg docs/prereg/PREREG_SELECTOR_ABLATION_R50.md.

Arm KHOA: P0 = B0REF2 = B0 thuan (tools/kaggle_sim.py HEAD md5 8b60b00a, KHONG SA block, cau hinh y selab-b0ref) chay
CUNG DOT; R50s42/R50s7/R100s42/R100s7 = hoan vi bo-4 diem selector CHI trong top-M moi ts (selector_ablation_topm.py).
Kernel R = SA_BLOCK cua selector_ablation_driver.py (vong truoc, khong doi) voi helper selector_ablation_topm.py
(import duoi ten SAS). R16 = R42/R7/R13 vong truoc (out selab-r42/-r7/-r13) — CHI lam diem tham chieu duong cong,
khong vao luat. Khong sua .java, khong build, khong Java sim tren Oracle.

Usage: python3 selector_ablation_r50_driver.py submit [ARM ...] --code-sha X | wait | fetch | parity | score
"""
import argparse
import json
import logging
import os
import sys

import numpy as np

REPO = "/home/ubuntu/src/BinanceFuturesJava"
HERE = os.path.join(REPO, "research/analysis")
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
from tools import kaggle_sim as ks  # noqa: E402
import selector_ablation_driver as D  # noqa: E402
import selector_ablation_topm as T  # noqa: E402

log = logging.getLogger("sel_abl_r50")
RM = {"R50": ["R50s42", "R50s7"], "R100": ["R100s42", "R100s7"]}
RNEW = RM["R50"] + RM["R100"]
R16 = ["R42", "R7", "R13"]
GROUPS = {"B0": ["P0"], "R50": RM["R50"], "R100": RM["R100"], "R16": R16}
TAG = {"P0": "selab-b0ref2", "R50s42": "selab-r50s42", "R50s7": "selab-r50s7", "R100s42": "selab-r100s42",
       "R100s7": "selab-r100s7", "R42": "selab-r42", "R7": "selab-r7", "R13": "selab-r13"}
ARMS = ["P0"] + RNEW + R16
P0OLD = "selab-p0"                                   # P0 vong truoc (md5 ff3ce513, anh Kaggle hien tai)
K_INFL, INFL = 2, 1.18                               # 2 phep thu chinh (M=50, M=100)
SHA_JSON = os.path.join(T.CACHE, "bins/sha256.json")
MTM_CACHE = os.path.join(T.CACHE, "mtm.json")
JSON_OUT = os.path.join(REPO, "docs/result/selector_ablation_r50.json")
GO_YEARS = D.GO_YEARS
CAGR_DEAD = 3.0

# kernel: helper topm thay cho scores (scores van nhung vi topm import no)
D.HELPERS = {"selector_ablation_scores.py": os.path.join(HERE, "selector_ablation_scores.py"),
             "selector_ablation_topm.py": os.path.join(HERE, "selector_ablation_topm.py"),
             "s3_funding.py": os.path.join(REPO, "research/pipeline/x1/s3_funding.py")}
assert D.SA_BLOCK.count("import selector_ablation_scores as SAS") == 1
D.SA_BLOCK = D.SA_BLOCK.replace("import selector_ablation_scores as SAS", "import selector_ablation_topm as SAS")
D.TAG = TAG
D.INFL, D.K_INFL = INFL, K_INFL


def submit(arm, code_sha):
    if arm == "P0":
        r = ks.submit(TAG["P0"], D.PROFILE, dict(D.B0OV), jar_ds=D.JAR_DS, bundle_ds=D.BUNDLE,
                      sim_end_date="20251231", xmx="22g", timeout_s=5400, code_sha=code_sha)
        log.info("PUSHED %s %s", arm, r)
        return
    shas = json.load(open(SHA_JSON))
    tag = TAG[arm]
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": tag, "profile": D.PROFILE, "overrides": dict(D.B0OV), "sim_end_date": "20251231", "xmx": "22g",
           "timeout_s": 7200, "code_sha": code_sha, "bins_ds": "", "jar_ds": D.JAR_DS, "market_ds": "",
           "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
           "sel_arm": arm, "want_bins_sha": shas[arm], "src_bins_sha": shas["P0"],
           "moc21_ds": D.MOC21_DS, "liq_ds": "", "orig_md5_funding": "8e57d900d5c54c744bfcaf5c9b27fc93"}
    code = D.build_template().replace("__CFG_JSON__", repr(json.dumps(cfg)))
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(code)
    meta = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
            "dataset_sources": [ks.USER + "/" + D.BUNDLE] + ks.TICKER_DS
                               + [ks.USER + "/" + D.JAR_DS, ks.USER + "/" + D.MOC21_DS],
            "competition_sources": [], "kernel_sources": []}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    r = ks._api().kernels_push(folder)
    log.info("PUSHED %s %s -> %s", arm, ref, getattr(r, "url", r))


def parity():
    """Cong parity: B0REF2 n/eq/jar/mapper khop VA printDone giong de-p1 TUNG O theo gia tri float32. md5 ghi lai
    (ff3ce513 = anh vong truoc; 650c386f = anh cu). Moi R: jar/mapper/bins_sha/src_sha khop."""
    import reset_rule_score as R
    rj = D.result_json("P0")
    md5, md5_old = R.md5_of(TAG["P0"]), R.md5_of(P0OLD)
    legs = R.load_legs(TAG["P0"])
    eq = float(R.load_daily(TAG["P0"])["equity"].iloc[-1])
    ve = D.printdone_valeq(TAG["P0"], "de-p1")
    ve_old = D.printdone_valeq(TAG["P0"], P0OLD)
    chk = {"n": len(legs) == D.PARITY_N, "eq": round(eq) == D.PARITY_EQ, "jar": rj.get("jar_sha256") == D.JAR_SHA,
           "mapper": (rj.get("symbol_mapper") or 0) >= 800,
           "printdone_value_identical_vs_de-p1": ve["cells_val_diff"] == 0 and ve["rows_a"] == ve["rows_b"]}
    arms = {}
    for a in RNEW:
        x = D.result_json(a)
        sel = x.get("sel") or {}
        arms[a] = dict(jar=x.get("jar_sha256") == D.JAR_SHA, mapper=(x.get("symbol_mapper") or 0) >= 800,
                       bins_ok=sel.get("bins_ok") is True, src_sha_ok=sel.get("src_bins_sha256") == T.SHA_P0,
                       funding_md5=sel.get("funding_md5"), md5=R.md5_of(TAG[a]) if x else None)
    arms_ok = all(v["jar"] and v["mapper"] and v["bins_ok"] and v["src_sha_ok"] for v in arms.values())
    info = {"md5_b0ref2": md5, "md5_selab_p0": md5_old, "same_image_as_prev_round": md5 == md5_old,
            "md5_eq_650c386f": md5 == D.PARITY_MD5, "valeq_vs_de-p1": ve, "valeq_vs_selab-p0": ve_old}
    ok = all(chk.values()) and arms_ok
    log.info("PARITY B0REF2 md5=%s n=%d eq=%.0f %s arms=%s info=%s -> %s", md5, len(legs), eq, chk, arms,
             {k: v for k, v in info.items() if not k.startswith("valeq")}, "PASS" if ok else "*** FAIL => VOID ***")
    json.dump(dict(ok=ok, md5=md5, n=len(legs), eq=eq, checks=chk, arms=arms, info=info),
              open(JSON_OUT + ".parity", "w"), indent=1)
    return ok


def gmean(d, g, m):
    return np.mean([d[k][m] for k in GROUPS[g]], axis=0)


def verdict_M(c):
    """Luat khai truoc §7: tren B0 - mean(R_M), Calmar CI inflate 1,18 (k=2)."""
    lo, hi = c["calmar"]["ci_infl"]
    dc = c["cagr"]["d"]
    if lo > 0:
        return "XEP HANG MIN CO GIA TRI"
    if hi < 0:
        return "XEP HANG MIN CO HAI"
    if abs(dc) < CAGR_DEAD:
        return "LOC THO"
    return "CHUA KET LUAN"


def combined(v50, v100):
    """Dien giai ket hop khai truoc §7 (R50 la phep thu CHINH; R100 cho duong cong)."""
    if v50 == "LOC THO" and v100 == "LOC THO":
        return "GIA TRI = LOC THO universe->100: xep hang trong top-100 khong quan trong; huong = tranh duoi (coin ngoai top-100)"
    if v50 == "LOC THO":
        return "GIA TRI = LOC THO universe->50: xep hang trong top-50 khong quan trong; huong = chat luong loc universe->50 (tranh duoi lo)"
    if v50 == "XEP HANG MIN CO GIA TRI":
        return "XEP HANG MIN CO GIA TRI (trong top-50): huong = ranking (top-50 -> 16)"
    if v50 == "XEP HANG MIN CO HAI":
        return "XEP HANG MIN CO HAI: random trong top-50 TOT HON B0 => thu tu top-16 hien tai la nhieu/hai"
    return "CHUA KET LUAN (R50): bao cao huong + do lon, khong nang cap"


def contrasts(obs, bs):
    out = {}
    pairs = [("B0", "R50"), ("B0", "R100"), ("R100", "R50"), ("R50", "R16"), ("R100", "R16"), ("B0", "R16")]
    for m in ("cagr", "mdd", "calmar", "sharpe"):
        for a, b in pairs:
            out.setdefault("%s-%s" % (a, b), {})[m] = D.ci_of(gmean(obs, a, m) - gmean(obs, b, m),
                                                              gmean(bs, a, m) - gmean(bs, b, m))
        for k in RNEW:
            out.setdefault("B0-" + k, {})[m] = D.ci_of(obs["P0"][m] - obs[k][m], bs["P0"][m] - bs[k][m])
    gap = {}
    for g in ("R50", "R100"):
        for m in ("calmar", "cagr"):
            den_o, num_o = gmean(obs, "B0", m) - gmean(obs, "R16", m), gmean(obs, "B0", m) - gmean(obs, g, m)
            den_b, num_b = gmean(bs, "B0", m) - gmean(bs, "R16", m), gmean(bs, "B0", m) - gmean(bs, g, m)
            ok = np.isfinite(den_b) & np.isfinite(num_b) & (den_b > 0)
            fr = num_b[ok] / den_b[ok]
            gap["%s_%s" % (g, m)] = dict(frac=float(num_o / den_o), ci=[float(np.percentile(fr, 2.5)),
                                         float(np.percentile(fr, 97.5))], n_ok=int(ok.sum()))
    return out, gap


def score(workers):
    import reset_rule_score as R
    import feat_add_v1_score as F  # noqa: F401  (side effect: MTMState cua so 2022+)
    import flat3_crashpen_driver as F3
    R.MTM_COSTS = {"legacy": R.LEGACY}
    if not parity():
        log.info("VOID: parity FAIL -> khong cham")
        sys.exit(3)
    legs, daily, md5 = {}, {}, {}
    for k in ARMS:
        legs[k], daily[k], md5[k] = R.load_legs(TAG[k]), R.load_daily(TAG[k]), R.md5_of(TAG[k])
        log.info("%s n=%d eq=%.0f md5=%s", k, len(legs[k]), daily[k]["equity"].iloc[-1], md5[k])
    raw = json.load(open(MTM_CACHE)) if os.path.exists(MTM_CACHE) else {}
    old = json.load(open(D.MTM_CACHE)) if os.path.exists(D.MTM_CACHE) else {}
    by_md5 = {v.get("md5"): v for v in old.values()}
    for k in ARMS:
        if (k not in raw or raw[k].get("md5") != md5[k]) and md5[k] in by_md5:
            raw[k] = by_md5[md5[k]]                  # MTM phut cua printDone byte-identical (vong truoc)
            log.info("MTM reuse %s tu cache vong truoc (md5 %s)", k, md5[k][:8])
    miss = {k: legs[k] for k in ARMS if k not in raw or raw[k].get("md5") != md5[k]}
    if miss:
        new = R.run_mtm(miss, workers=workers, chunk=30)
        for k, vv in new.items():
            vv["md5"] = md5[k]
            raw[k] = vv
        json.dump(raw, open(MTM_CACHE, "w"))
    M = {k: D.arm_metrics(R, F3, k, legs[k], daily[k], raw[k]["legacy"]) for k in ARMS}
    obs, bs = D.daily_boot({k: daily[k]["equity"] for k in ARMS})
    for k in ARMS:
        M[k].update(md5=md5[k], calmar_boot_obs=float(obs[k]["calmar"]), cagr_boot_obs=float(obs[k]["cagr"]),
                    mdd_daily_mtm_obs=float(obs[k]["mdd"]), overlap_vs_B0=D.overlap(legs["P0"], legs[k]))
    con, gap = contrasts(obs, bs)
    v = {g: verdict_M(con["B0-" + g]) for g in ("R50", "R100")}
    yrs = {}
    for g in ("R50", "R100", "R16"):
        yrs[g] = {yy: M["P0"]["roi_year"].get(str(yy), np.nan)
                  - np.mean([M[k]["roi_year"].get(str(yy), np.nan) for k in GROUPS[g]]) for yy in [2021] + GO_YEARS}
    rule = dict(verdict_R50=v["R50"], verdict_R100=v["R100"], combined=combined(v["R50"], v["R100"]),
                years_B0_minus=yrs, years_pos_R50=int(sum(1 for y in GO_YEARS if yrs["R50"][y] > 0)),
                years_pos_R100=int(sum(1 for y in GO_YEARS if yrs["R100"][y] > 0)), gap_fraction=gap)
    agg = {}
    for g in ("R50", "R100", "R16"):
        agg[g] = {}
        for f in ("n", "sum_pnl", "equity", "cagr", "dd_mtm", "calmar_mtm", "uw_mtm", "win", "mean_roi", "median_roi",
                  "tsloss", "sharpe_daily", "calmar_boot_obs", "cagr_boot_obs", "mdd_daily_mtm_obs"):
            vv = [M[k][f] for k in GROUPS[g]]
            agg[g][f] = dict(mean=float(np.mean(vv)), sd=float(np.std(vv, ddof=1)))
        agg[g]["overlap_pct_of_b0"] = float(np.mean([M[k]["overlap_vs_B0"]["pct_of_b0"] for k in GROUPS[g]]))
    R.K_INFL, R.INFL = K_INFL, INFL
    rates_ci = {k: R.ci_pair(legs[k], legs["P0"]) for k in RNEW}
    log.info("%-8s %5s %8s %8s %6s %7s %6s %6s %6s %6s %6s %6s %6s", "arm", "n", "SumPnL", "equity", "CAGR", "ddMTM",
             "Calm", "CalB", "UW", "win%", "mROI", "SL%", "ovl")
    for k in ARMS:
        x = M[k]
        log.info("%-8s %5d %8.0f %8.0f %6.2f %7.2f %6.3f %6.2f %6.0f %6.2f %6.2f %6.2f %6.1f", k, x["n"], x["sum_pnl"],
                 x["equity"], x["cagr"], x["dd_mtm"], x["calmar_mtm"], x["calmar_boot_obs"], x["uw_mtm"], x["win"],
                 x["mean_roi"], x["tsloss"], x["overlap_vs_B0"]["pct_of_b0"])
    for c, d in con.items():
        log.info("%-10s %s", c, {m: (round(z["d"], 2), [round(q, 2) for q in z["ci_infl"]]) for m, z in d.items()})
    log.info("ROI nam %s", {k: {y: round(z, 1) for y, z in M[k]["roi_year"].items()} for k in ARMS})
    log.info("GAP %s", gap)
    log.info("VERDICT R50=%s | R100=%s | %s | years %s", v["R50"], v["R100"], rule["combined"], yrs)
    js = dict(prereg="docs/prereg/PREREG_SELECTOR_ABLATION_R50.md", k_infl=K_INFL, inflate=INFL, nrep=D.NREP,
              seed=D.SEED, block_days=D.BLOCK_D, jar_sha256=D.JAR_SHA, kaggle_sim_md5=D.KS_MD5_WANT, tags=TAG,
              bins_sha256=json.load(open(SHA_JSON)), parity=json.load(open(JSON_OUT + ".parity")),
              sanity=json.load(open(os.path.join(T.CACHE, "sanity.json"))).get("checks"),
              universe=json.load(open(os.path.join(T.CACHE, "sanity.json"))).get("universe"),
              boot_obs=obs, contrasts=con, rule=rule, agg=agg, rates_ci_vs_B0=rates_ci, metrics=M)
    json.dump(js, open(JSON_OUT, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", JSON_OUT)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["template", "submit", "wait", "fetch", "parity", "score"])
    ap.add_argument("arms", nargs="*")
    ap.add_argument("--code-sha", default="head")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    arms = a.arms or (["P0"] + RNEW)
    if a.cmd == "template":
        t = D.build_template()
        open(os.path.join(T.CACHE, "kernel_template.py"), "w").write(t)
        log.info("template ok %d bytes, topm=%s", len(t), "selector_ablation_topm as SAS" in t)
    elif a.cmd == "submit":
        log.info("free_slots=%d", ks.free_slots())
        for x in arms:
            submit(x, a.code_sha)
    elif a.cmd == "wait":
        log.info("%s", ks.wait([ks.kernel_ref(TAG[x]) for x in arms], poll_s=120, timeout_s=5 * 3600))
    elif a.cmd == "fetch":
        for x in arms:
            o = ks.fetch(TAG[x])
            log.info("%s %s", x, json.dumps(o.get("result"), default=str)[:600])
    elif a.cmd == "parity":
        sys.exit(0 if parity() else 3)
    else:
        score(a.workers)


if __name__ == "__main__":
    main()
