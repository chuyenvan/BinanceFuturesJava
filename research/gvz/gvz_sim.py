#!/usr/bin/env python3
"""GATE_VZ sim Kaggle (PREREG_GATE_VZ.md ee97237b muc 4). Jar/profile/override = gqsf ON; chi doi pred.bin.
Usage: python3 gvz_sim.py upload RUN.. | orch RUN.. | parity RUN.. ; RUN = B_S42 | VA_S<seed> | VB_S<seed>
"""
import json
import logging
import os
import re
import sys
import time

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/research/analysis")
import gate_skipfull_driver as G  # noqa: E402
GA = G.GA

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("gvzs")
D = "/home/ubuntu/claude_master/gvz"
CODE_SHA = "128290af"
SIM_WAIT = 60


def tag(run):
    return "gvz-" + run.lower().replace("_", "-")


def dsn(run):
    return "gvzp-" + run.lower().replace("_", "-")


def meta(run):
    return json.load(open(D + "/pred_%s/meta.json" % run))


def upload(runs):
    ks = GA.ks_mod()
    for r in runs:
        m = meta(r)
        fol = D + "/ds_" + r
        os.makedirs(fol, exist_ok=True)
        dst = fol + "/pred.bin"
        if not os.path.exists(dst):
            os.link(D + "/pred_%s/pred.bin" % r, dst)
        assert GA.md5f(dst) == m["md5"]
        json.dump({"title": dsn(r), "id": ks.USER + "/" + dsn(r), "licenses": [{"name": "CC0-1.0"}]},
                  open(fol + "/dataset-metadata.json", "w"))
        res = ks._api().dataset_create_new(fol, public=False, quiet=True, dir_mode="skip")
        log.info("UPLOAD %s -> %s md5=%s", r, getattr(res, "url", res), m["md5"])
    for r in runs:
        for _ in range(40):
            try:
                st = str(ks._api().dataset_status(ks.USER + "/" + dsn(r))).lower()
            except Exception as e:  # noqa: BLE001
                st = "err %s" % e
            if st == "ready":
                break
            time.sleep(30)
        log.info("DS %s %s", dsn(r), st)


def submit(r):
    ks = GA.ks_mod()
    assert G.JAR_SHA
    m = meta(r)
    t = tag(r)
    folder = os.path.join(ks.WORKDIR, ks.slug(t))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": t, "profile": GA.PROFILE, "overrides": dict(G.OV_ON), "sim_end_date": "20251231", "xmx": "22g",
           "timeout_s": 7200, "code_sha": CODE_SHA, "bins_ds": "", "jar_ds": G.JAR_DS, "market_ds": "",
           "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
           "pred_ds": dsn(r), "want_pred_md5": m["md5"], "want_pred_base": GA.PRED0_MD5}
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(GA.template().replace("__CFG_JSON__", repr(json.dumps(cfg))))
    md = {"id": ks.kernel_ref(t), "title": ks.kernel_ref(t).split("/")[1], "code_file": "run.py", "language": "python",
          "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": [ks.USER + "/" + GA.BUNDLE] + ks.TICKER_DS + [ks.USER + "/" + G.JAR_DS,
                                                                            ks.USER + "/" + dsn(r)],
          "competition_sources": [], "kernel_sources": []}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(md, f, indent=1)
    res = ks._api().kernels_push(folder)
    log.info("PUSHED %s %s pred=%s md5=%s ov=%s", t, getattr(res, "url", res), dsn(r), m["md5"], json.dumps(G.OV_ON))


def done(r):
    return os.path.exists(GA.OUT % tag(r) + "storage/printDone.csv")


def orch(runs, maxrun=2):
    ks = GA.ks_mod()
    queue = [r for r in runs if not done(r)]
    running = []
    while queue or running:
        while queue and len(running) < maxrun:
            if ks.free_slots() < 1:
                break
            r = queue.pop(0)
            G.disk("truoc submit " + r)
            submit(r)
            running.append(r)
            time.sleep(SIM_WAIT)
        time.sleep(120)
        for r in list(running):
            try:
                st = ks._status(ks.kernel_ref(tag(r)))
            except Exception as e:  # noqa: BLE001
                log.info("status %s loi %s", r, e)
                continue
            if st in ks.TERMINAL:
                log.info("%s -> %s", r, st)
                G.disk("truoc fetch " + r)
                o = ks.fetch(tag(r))
                log.info("FETCH %s %s", r, json.dumps(o.get("result"), default=str)[:400])
                running.remove(r)
    parity(runs)
    log.info("ORCH XONG")


def parity(runs):
    import reset_rule_score as R
    p = D + "/parity.json"
    res = json.load(open(p)) if os.path.exists(p) else {}
    for r in runs:
        t = tag(r)
        if not done(r):
            log.info("PARITY %s chua co output", r)
            continue
        rj, pr, txt = GA.result_json(t), GA.prof_run(t), G.logtxt(t)
        sk = re.findall(r"skipFull=(\d+)", txt)
        m = meta(r)
        chk = dict(jar=rj.get("jar_sha256") == G.JAR_SHA, mapper=(rj.get("symbol_mapper") or 0) >= 800,
                   topk24=pr.get("SELECTOR_RANK_TOPK") == "24", key_on=pr.get(G.KEY) == "true", ok=rj.get("ok") is True,
                   b0ov=all(pr.get(k) == str(v) for k, v in GA.B0OV.items()),
                   log_key="[GATE-QUOTA] SKIP_WHEN_FULL=ON" in txt, skip_count=bool(sk),
                   pred=rj.get("pred_md5_used") == m["md5"] and rj.get("pred_md5_base") == GA.PRED0_MD5,
                   end=str(rj.get("date_last", "")).startswith("202512"))
        res[r] = dict(ok=all(chk.values()), checks=chk, md5=R.md5_of(t), n=rj.get("n_trades"), eq=rj.get("equity_final"),
                      skip_full=int(sk[-1]) if sk else None, secs=rj.get("secs"), date_last=rj.get("date_last"))
        log.info("PARITY %-8s %s n=%s eq=%s skip=%s %s", r, "PASS" if res[r]["ok"] else "*** VOID ***", res[r]["n"],
                 res[r]["eq"], res[r]["skip_full"], chk)
    json.dump(res, open(p, "w"), indent=1)
    return res


if __name__ == "__main__":
    c, runs = sys.argv[1], sys.argv[2:]
    mx = 2
    if runs and runs[0].startswith("--max="):
        mx, runs = int(runs[0][6:]), runs[1:]
    {"upload": upload, "orch": lambda x: orch(x, mx), "parity": parity}[c](runs)
