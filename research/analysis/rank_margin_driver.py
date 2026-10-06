#!/usr/bin/env python3
"""RANK-MARGIN (size leg SELECTOR giam theo rank k, tren C2 = K24 + skipFull).
Pre-reg docs/prereg/PREREG_RANK_MARGIN.md (8b6c902d, chot TRUOC).

Jar branch feat/rank-margin (dataset sim-jar-rm). P0 = C2 alpha=0 (byte-identical gqsf-a1, md5 ad26fd55).
ON = 3 arm alpha in {0.3, 0.5, 0.7} x seed A1 (pred.bin goc bundle). Base C2 = B0OV + TOPK=24 + skipFull=true.
Usage: jards | p0 --code-sha SHA | submit --code-sha SHA | status | fetch | parity | score
"""
import argparse
import hashlib
import json
import logging
import math
import os
import shutil
import sys
import time

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
HERE = os.path.join(REPO, "research/analysis")
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
import gate_ablation_driver as GA  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("rm")

D = "/home/ubuntu/claude_master/1005/rm"
JAR_DS = "sim-jar-rm"
JAR_SHA = "d9be91111c7d214ebcc200b1cb50a54e7a57e58a91a9a3328edbeaa56c55fc3f"
PROF = "/home/ubuntu/kaggle_sim/jar_gdv2/prof_r4_kg0_k16_f015_g155.properties"
PROF_MD5 = "0e0caef09e47931b706c696d587a5184"
P0_TAG, P0_WANT = "rm-p0", "ad26fd55"
ALPHAS = [0.3, 0.5, 0.7]
TAGS = {a: "rm-a1-%03d" % int(a * 1000) for a in ALPHAS}
KEY = "SIM_RANK_MARGIN_ALPHA"
OV_ON = dict(GA.B0OV, SELECTOR_RANK_TOPK=24, GATE_QUOTA_SKIP_WHEN_FULL="true")
DISK_MIN_MB = 500
JSON_OUT = os.path.join(REPO, "docs/result/rank_margin.json")
MTM_FILE = D + "/mtm.json"
# C2 baseline (gqsf-a1) = alpha=0, seed 42, K24+skipFull. md5 printDone ad26fd55.
BASE_TAG = "gqsf-a1"


def disk(tag=""):
    mb = shutil.disk_usage("/home/ubuntu").free // (1 << 20)
    log.info("DF %s avail=%d MB", tag, mb)
    if mb < DISK_MIN_MB:
        log.error("DIA < %d MB -> DUNG", DISK_MIN_MB)
        sys.exit(3)
    return mb


def jards(a=None):
    ks = GA.ks_mod()
    disk("truoc jards")
    fol = D + "/ds_" + JAR_DS
    os.makedirs(fol, exist_ok=True)
    assert GA.md5f(PROF) == PROF_MD5
    dst = fol + "/sim.jar"
    shutil.copy(os.path.join(REPO, "target/binance-java-sdk-1.2.4.jar"), dst)
    sha = hashlib.sha256(open(dst, "rb").read()).hexdigest()
    assert sha == JAR_SHA, (sha, JAR_SHA)
    shutil.copy(PROF, fol + "/" + os.path.basename(PROF))
    json.dump({"title": JAR_DS, "id": ks.USER + "/" + JAR_DS, "licenses": [{"name": "CC0-1.0"}]},
              open(fol + "/dataset-metadata.json", "w"))
    r = ks._api().dataset_create_new(fol, public=False, quiet=True, dir_mode="skip")
    log.info("dataset %s -> %s (jar %s)", JAR_DS, getattr(r, "url", r), sha)
    for _ in range(60):
        try:
            st = ks._api().dataset_status(ks.USER + "/" + JAR_DS)
        except Exception as e:  # noqa: BLE001
            st = "err:%s" % e
        log.info("dataset status %s", st)
        if str(st).lower() == "ready":
            return
        time.sleep(30)


def p0(a):
    ks = GA.ks_mod()
    disk("truoc p0")
    r = ks.submit(P0_TAG, GA.PROFILE, dict(OV_ON), jar_ds=JAR_DS, bundle_ds=GA.BUNDLE,
                  sim_end_date="20251231", xmx="22g", timeout_s=5400, code_sha=a.code_sha)
    log.info("PUSHED P0 %s ov=%s", r, json.dumps(OV_ON))


def submit(a):
    ks = GA.ks_mod()
    assert a.code_sha
    disk("truoc submit")
    log.info("free_slots=%d", ks.free_slots())
    for alpha in ALPHAS:
        tag = TAGS[alpha]
        ov = dict(OV_ON, **{KEY: str(alpha)})
        r = ks.submit(tag, GA.PROFILE, ov, jar_ds=JAR_DS, bundle_ds=GA.BUNDLE,
                      sim_end_date="20251231", xmx="22g", timeout_s=7200, code_sha=a.code_sha)
        log.info("PUSHED %s %s ov=%s", tag, r, json.dumps(ov))


def status(a):
    ks = GA.ks_mod()
    for t in [P0_TAG] + list(TAGS.values()):
        try:
            log.info("%s %s", t, ks._status(ks.kernel_ref(t)))
        except Exception as e:  # noqa: BLE001
            log.info("%s chua co (%s)", t, str(e)[:80])


def fetch(a):
    ks = GA.ks_mod()
    for t in [P0_TAG] + list(TAGS.values()):
        disk("truoc fetch " + t)
        o = ks.fetch(t)
        log.info("%s %s", t, json.dumps(o.get("result"), default=str)[:500])


def logtxt(tag):
    out = ""
    for fn in ("logs/full.log", "logs/sim.out"):
        p = GA.OUT % tag + fn
        if os.path.exists(p):
            with open(p, errors="ignore") as f:
                out += f.read()
    return out


def parity(a=None):
    import reset_rule_score as R
    res = {}
    if os.path.exists(GA.OUT % P0_TAG + "storage/printDone.csv"):
        rj = GA.result_json(P0_TAG)
        m = R.md5_of(P0_TAG)
        res["P0"] = dict(ok=bool(m.startswith(P0_WANT) and rj.get("jar_sha256") == JAR_SHA and rj.get("ok") is True),
                         md5=m, n=rj.get("n_trades"), eq=rj.get("equity_final"), jar=rj.get("jar_sha256"))
        log.info("PARITY P0 %s", res["P0"])
    for alpha in ALPHAS:
        tag = TAGS[alpha]
        if not os.path.exists(GA.OUT % tag + "storage/printDone.csv"):
            continue
        rj, pr, txt = GA.result_json(tag), GA.prof_run(tag), logtxt(tag)
        chk = dict(jar=rj.get("jar_sha256") == JAR_SHA, mapper=(rj.get("symbol_mapper") or 0) >= 800,
                   topk24=pr.get("SELECTOR_RANK_TOPK") == "24", skipfull=pr.get("GATE_QUOTA_SKIP_WHEN_FULL") == "true",
                   alpha=pr.get(KEY) == str(alpha), ok=rj.get("ok") is True,
                   b0ov=all(pr.get(k) == str(v) for k, v in GA.B0OV.items()),
                   # A1 = pred.bin goc trong bundle (khong pred_ds) => result.json pred_md5_* = None.
                   # Kiem bang dong log Java "LOAD offline OK ... (md5 verified)" + P0 da byte-identical bundle.
                   pred=bool("md5 verified" in txt))
        res[tag] = dict(ok=all(chk.values()), checks=chk, md5=R.md5_of(tag), n=rj.get("n_trades"),
                        eq=rj.get("equity_final"), secs=rj.get("secs"))
        log.info("PARITY %-6s %s %s", tag, "PASS" if res[tag]["ok"] else "*** VOID ***", chk)
    json.dump(res, open(D + "/parity.json", "w"), indent=1)
    return res


def rank_band_pnl(tag):
    """ΣPnL theo rank-band 1-8 / 9-16 / 17-24 tu selRank trong printDone (neu co)."""
    import reset_rule_score as R
    legs = R.load_legs(tag)
    if legs is None or len(legs) == 0:
        return {}
    df = legs
    if "selRank" not in df.columns and "rank" not in df.columns:
        return {}
    col = "selRank" if "selRank" in df.columns else "rank"
    pnlcol = "pnl" if "pnl" in df.columns else ("Pnl" if "Pnl" in df.columns else None)
    if pnlcol is None:
        return {}
    r = df[col].astype(float)
    p = df[pnlcol].astype(float)
    out = {}
    for lo, hi in ((1, 8), (9, 16), (17, 24)):
        m = (r >= lo) & (r <= hi)
        out["%d-%d" % (lo, hi)] = dict(n=int(m.sum()), pnl=float(p[m].sum()))
    out["gt24"] = dict(n=int((r > 24).sum()), pnl=float(p[r > 24].sum()))
    return out


def score(a):
    import reset_rule_score as R
    import feat_add_v1_score as F  # noqa: F401  (side effect: MTMState 2022+)
    import flat3_crashpen_driver as F3
    import n700_driver as N
    R.MTM_COSTS = {"legacy": R.LEGACY}
    par = parity()
    assert par.get("P0", {}).get("ok"), "P0 chua PASS -> khong cham"
    keys = [BASE_TAG] + [TAGS[a] for a in ALPHAS]
    for k in keys:
        N.TAG[k], N.DESC[k] = k, "RANK-MARGIN " + k
    legs, daily, md5 = {}, {}, {}
    for k in keys:
        legs[k], daily[k], md5[k] = R.load_legs(k), R.load_daily(k), R.md5_of(k)
    raw = json.load(open(MTM_FILE)) if os.path.exists(MTM_FILE) else {}
    miss = {k: legs[k] for k in keys if k not in raw or raw[k].get("md5") != md5[k]}
    log.info("MTM cache %s; can tinh %s", sorted(raw), sorted(miss))
    if miss:
        new = R.run_mtm(miss, workers=a.workers, chunk=30)
        for k, vv in new.items():
            vv["md5"] = md5[k]
            raw[k] = vv
        disk("truoc ghi mtm")
        json.dump(raw, open(MTM_FILE, "w"))
    M = {}
    for k in keys:
        M[k] = N.arm_metrics(R, F3, k, legs[k], daily[k], raw[k]["legacy"])
        M[k]["md5"] = md5[k]
        M[k]["rank_band"] = rank_band_pnl(k)
    base = M[BASE_TAG]
    rows = {}
    for alpha in ALPHAS:
        t = TAGS[alpha]
        m = M[t]
        rows[t] = dict(alpha=alpha,
                       cagr22=[base["cagr22"], m["cagr22"]], dd22=[base["dd_mtm22"], m["dd_mtm22"]],
                       dd_all=[base["dd_mtm"], m["dd_mtm"]], cal22=[base["calmar22"], m["calmar22"]],
                       uw22=[base["uw_mtm22"], m["uw_mtm22"]], n_yr=[base["n_per_year"], m["n_per_year"]],
                       rank_band_base=base["rank_band"], rank_band=m["rank_band"])
        log.info("ROW alpha=%.1f CAGR22 %6.2f->%6.2f (%+5.2f) dd22 %6.2f->%6.2f Cal %5.3f->%5.3f "
                 "UW %4.0f->%4.0f n/y %4.0f->%4.0f",
                 alpha, *rows[t]["cagr22"], rows[t]["cagr22"][1] - rows[t]["cagr22"][0],
                 *rows[t]["dd22"], *rows[t]["cal22"], *rows[t]["uw22"], *rows[t]["n_yr"])
        log.info("RANK-BAND base=%s arm=%s", json.dumps(base["rank_band"]), json.dumps(m["rank_band"]))
    js = dict(prereg="docs/prereg/PREREG_RANK_MARGIN.md", prereg_commit="8b6c902d", jar_ds=JAR_DS,
              jar_sha256=JAR_SHA, base_tag=BASE_TAG, alphas=ALPHAS, tags=TAGS, parity=par,
              rows=rows, metrics={k: {kk: vv for kk, vv in v.items() if kk != "rank_band"} for k, v in M.items()})
    disk("truoc ghi json")
    json.dump(js, open(JSON_OUT, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", JSON_OUT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("--code-sha", default="")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    fn = {"jards": jards, "p0": p0, "submit": submit, "status": status,
          "fetch": fetch, "parity": parity, "score": score}
    if a.cmd not in fn:
        sys.exit("unknown cmd " + a.cmd)
    fn[a.cmd](a)


if __name__ == "__main__":
    main()
