#!/usr/bin/env python3
"""HELD_RERANK (thu hoi waste held-symbol 4.5%). Pre-reg docs/prereg/PREREG_HELD_RERANK.md (103b0f93).

Jar branch feat/rank-margin@103b0f93 (dataset sim-jar-heldrerank). P0 = B0@K16 OFF (cong ff3ce513);
ON = 8 seed @K24 + SELECTOR_HELD_RERANK=true, ghep cap voi run OFF da co (n700-a1, gabl-seed7, gsb-s*).
Usage: jards | p0 --code-sha SHA | submit --off --arms A1,S7... --code-sha SHA | status [ARM..] | parity
"""
import argparse, hashlib, json, logging, os, re, shutil, sys, time
import numpy as np, pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
HERE = os.path.join(REPO, "research/analysis")
sys.path.insert(0, REPO); sys.path.insert(0, HERE)
import gate_ablation_driver as GA  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("hldrr")

D = "/home/ubuntu/claude_master/1006/hldrr"
JAR_DS = "sim-jar-heldrerank"
JAR_SHA = open(D + "/jar.sha256").read().split()[0] if os.path.exists(D + "/jar.sha256") else None
PROF = "/home/ubuntu/kaggle_sim/jar_gdv2/prof_r4_kg0_k16_f015_g155.properties"
PROF_MD5 = "0e0caef09e47931b706c696d587a5184"
P0_TAG, P0_WANT = "hldrr-p0", "ff3ce513"
SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
OFF = {"A1": "n700-a1", "S7": "gabl-seed7", **{s: "gsb-" + s.lower() for s in SEEDS[2:]}}
ON = {s: "hldrr-" + s.lower() for s in SEEDS}
KEY = "SELECTOR_HELD_RERANK"
OV_ON = dict(GA.B0OV, SELECTOR_RANK_TOPK=24, **{KEY: "true"})
DISK_MIN_MB = 500


def pred_of(s):
    if s == "A1":
        return None, GA.PRED0_MD5
    if s == "S7":
        return "gate-abl-seed7", json.load(open("/home/ubuntu/claude_master/1004/gabl/pred_SEED7/meta.json"))["md5"]
    return "gate-sb-" + s.lower(), json.load(open("/home/ubuntu/claude_master/1004/gsb/pred_%s/meta.json" % s))["md5"]


def disk(tag=""):
    mb = shutil.disk_usage("/home/ubuntu").free // (1 << 20)
    log.info("DF %s avail=%d MB", tag, mb)
    if mb < DISK_MIN_MB:
        log.error("DIA < %d MB -> DUNG", DISK_MIN_MB); sys.exit(3)
    return mb


def jards(a=None):
    ks = GA.ks_mod()
    disk("truoc jards")
    fol = D + "/ds_" + JAR_DS
    assert os.path.exists(fol + "/sim.jar") and GA.md5f(PROF) == PROF_MD5
    sha = hashlib.sha256(open(fol + "/sim.jar", "rb").read()).hexdigest()
    assert sha == JAR_SHA, (sha, JAR_SHA)
    shutil.copy(PROF, fol + "/" + os.path.basename(PROF))
    json.dump({"title": JAR_DS, "id": ks.USER + "/" + JAR_DS, "licenses": [{"name": "CC0-1.0"}]},
              open(fol + "/dataset-metadata.json", "w"))
    r = ks._api().dataset_create_new(fol, public=False, quiet=True, dir_mode="skip")
    log.info("dataset %s -> %s (jar %s)", JAR_DS, getattr(r, "url", r), sha)
    for _ in range(60):
        try:
            st = ks._api().dataset_status(ks.USER + "/" + JAR_DS)
        except Exception as e:
            st = "err:%s" % e
        log.info("dataset status %s", st)
        if str(st).lower() == "ready":
            return
        time.sleep(30)


def p0(a):
    ks = GA.ks_mod()
    disk("truoc p0")
    r = ks.submit(P0_TAG, GA.PROFILE, dict(GA.B0OV), jar_ds=JAR_DS, bundle_ds=GA.BUNDLE, sim_end_date="20251231",
                  xmx="22g", timeout_s=5400, code_sha=a.code_sha)
    log.info("PUSHED P0 %s ov=%s", r, json.dumps(GA.B0OV))


def submit(a):
    ks = GA.ks_mod()
    assert a.code_sha and JAR_SHA
    disk("truoc submit")
    log.info("free_slots=%d", ks.free_slots())
    for s in a.arms:
        tag = OFF[s] if a.off else ON[s]
        ov = dict(GA.B0OV) if a.off else dict(OV_ON)
        dsn, md5 = pred_of(s)
        if dsn is None:
            r = ks.submit(tag, GA.PROFILE, ov, jar_ds=JAR_DS, bundle_ds=GA.BUNDLE, sim_end_date="20251231",
                          xmx="22g", timeout_s=7200, code_sha=a.code_sha)
            log.info("PUSHED %s %s ov=%s", tag, r, json.dumps(ov))
            continue
        ref = ks.kernel_ref(tag)
        folder = os.path.join(ks.WORKDIR, ks.slug(tag))
        os.makedirs(folder, exist_ok=True)
        cfg = {"tag": tag, "profile": GA.PROFILE, "overrides": ov, "sim_end_date": "20251231", "xmx": "22g",
               "timeout_s": 7200, "code_sha": a.code_sha, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": "",
               "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
               "pred_ds": dsn, "want_pred_md5": md5, "want_pred_base": GA.PRED0_MD5}
        with open(os.path.join(folder, "run.py"), "w") as f:
            f.write(GA.template().replace("__CFG_JSON__", repr(json.dumps(cfg))))
        md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
              "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
              "dataset_sources": [ks.USER + "/" + GA.BUNDLE] + ks.TICKER_DS + [ks.USER + "/" + JAR_DS, ks.USER + "/" + dsn],
              "competition_sources": [], "kernel_sources": []}
        with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
            json.dump(md, f, indent=1)
        r = ks._api().kernels_push(folder)
        log.info("PUSHED %s %s pred=%s md5=%s ov=%s", tag, getattr(r, "url", r), dsn, md5, json.dumps(ov))


def status(a):
    ks = GA.ks_mod()
    for t in ([ON[s] for s in a.arms] if a.arms else [P0_TAG] + list(ON.values())):
        try:
            log.info("%s %s", t, ks._status(ks.kernel_ref(t)))
        except Exception as e:
            log.info("%s chua co (%s)", t, str(e)[:80])


def logtxt(tag):
    out = ""
    for fn in ("logs/full.log", "logs/sim.out"):
        p = GA.OUT % tag + fn
        if os.path.exists(p):
            with open(p, errors="ignore") as f:
                out += f.read()
    return out


def offline_line(tag):
    v = [ln for ln in logtxt(tag).splitlines() if "md5 verified" in ln and "pred=" in ln]
    return v[-1].split("LOAD offline OK")[-1] if v else None


def parity(a=None):
    import reset_rule_score as R
    res = {}
    if os.path.exists(GA.OUT % P0_TAG + "storage/printDone.csv"):
        rj = GA.result_json(P0_TAG)
        m = R.md5_of(P0_TAG)
        res["P0"] = dict(ok=bool(m.startswith(P0_WANT) and rj.get("jar_sha256") == JAR_SHA and rj.get("ok") is True),
                         md5=m, n=rj.get("n_trades"), eq=rj.get("equity_final"), jar=rj.get("jar_sha256"))
        log.info("PARITY P0 %s", res["P0"])
    for s in SEEDS:
        tag = ON[s]
        if not os.path.exists(GA.OUT % tag + "storage/printDone.csv"):
            continue
        rj, pr, txt = GA.result_json(tag), GA.prof_run(tag), logtxt(tag)
        dsn, md5 = pred_of(s)
        ver = [ln for ln in txt.splitlines() if "md5 verified" in ln and "pred=" in ln]
        chk = dict(jar=rj.get("jar_sha256") == JAR_SHA, mapper=(rj.get("symbol_mapper") or 0) >= 800,
                   topk24=pr.get("SELECTOR_RANK_TOPK") == "24", key_on=pr.get(KEY) == "true", ok=rj.get("ok") is True,
                   b0ov=all(pr.get(k) == str(v) for k, v in GA.B0OV.items()),
                   log_key="[GATE] SELECTOR_HELD_RERANK" in txt or "SELECTOR_HELD_RERANK" in txt,
                   pred=(bool(ver) and ver[-1].split("LOAD offline OK")[-1] == offline_line(OFF[s])) if dsn is None else
                   (rj.get("pred_md5_used") == md5 and rj.get("pred_md5_base") == GA.PRED0_MD5))
        res[s] = dict(ok=all(chk.values()), checks=chk, md5=R.md5_of(tag), n=rj.get("n_trades"),
                      eq=rj.get("equity_final"), pred_md5=md5, secs=rj.get("secs"), date_last=rj.get("date_last"))
        log.info("PARITY %-6s %s n=%s eq=%s %s", s, "PASS" if res[s]["ok"] else "*** VOID ***",
                 res[s]["n"], res[s]["eq"], chk)
    json.dump(res, open(D + "/parity.json", "w"), indent=1)
    return res


def _cli():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["jards", "p0", "submit", "status", "parity"])
    ap.add_argument("--arms", default="")
    ap.add_argument("--off", action="store_true")
    ap.add_argument("--code-sha", default="head")
    a = ap.parse_args()
    a.arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    if a.cmd == "jards": jards(a)
    elif a.cmd == "p0": p0(a)
    elif a.cmd == "submit": submit(a)
    elif a.cmd == "status": status(a)
    elif a.cmd == "parity": parity(a)


if __name__ == "__main__":
    _cli()
