#!/usr/bin/env python3
"""TSX_V2_SIM (PREREG_TSX_V2_SIM bfa59d4a) - day + parity 4 bien the x 8 seed DEV va HO W9, + 2 run ctl (tham so = X14).
Tai dung tsx_driver (B.push / B.push_gpu, jar sim-jar-tsx) va ho4p1_queue (q.push / q.check). Gioi han: CPU <= 5 (dem ca
kernel ngoai cua tai khoan), GPU <= 2 cua driver. HO chi dung GPU neu ctl HO tren GPU bit-exact tsx-ho-x14-s7.
State: ~/claude_master/tsx2sim/state.json. Usage: python3 run.py run | post
"""
import hashlib
import json
import logging
import os
import re
import sys
import time

import pandas as pd

W = "/home/ubuntu/claude_master/tsx2sim"
sys.path.insert(0, "/home/ubuntu/claude_master/tsx")
import tsx_driver as T  # noqa: E402  (cau hinh B: jar sim-jar-tsx, CODE_SHA a8690d46)

B, GA = T.B, T.GA
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tsx2run")
FL = json.load(open(W + "/flags_variants.json"))["arms"]
ARMS = ["v336", "v420", "vt25", "vl45"]
DEV_SEEDS = T.SEEDS  # A1 S7 ... S2024
HO_SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
CPU_MAX, GPU_MAX, POLL = 5, 2, 180
OUT = "/home/ubuntu/kaggle_sim/out/%s/"
JAR = "/home/ubuntu/src_wt_bcd/target/binance-java-sdk-1.2.4.jar"
WANT_JAR = open("/home/ubuntu/claude_master/tsx/jar.sha256").read().split()[0]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def Q():
    sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
    import ho4p1_queue as q
    logging.getLogger().removeHandler(q._fh)
    q.JAR_DS = "sim-jar-tsx"
    q.JAR_SHA = sha256(JAR)
    assert q.JAR_SHA == WANT_JAR, (q.JAR_SHA, WANT_JAR)
    return q


def specs(q):
    k24 = dict(q.CFGS["k24"])
    assert k24 == q.PARITY["ho4p1-c2"][0]
    x = FL["X14"]
    sp = {"tsx2-ctl-a1": dict(scope="DEV", seed="A1", arm="X14", ext=x["ext_hours"], nd=x["dev"]["n_days"],
                              ov=dict(B.OV_BASE, SIM_LOSER_TS_EXT_HOURS=x["ext_hours"], SIM_LOSER_TS_EXT_DAYS=x["dev"]["ranges"]),
                              ref="tsx-x14-a1"),
          "tsx2-ho-ctl-s7": dict(scope="HO", seed=7, arm="X14", ext=x["ext_hours"], nd=x["ho"]["n_days"], gpu_only=True,
                                 ov=dict(k24, SIM_LOSER_TS_EXT_HOURS=x["ext_hours"], SIM_LOSER_TS_EXT_DAYS=x["ho"]["ranges"]),
                                 ref="tsx-ho-x14-s7")}
    assert sp["tsx2-ctl-a1"]["ov"] == T.OV_ON
    for s in DEV_SEEDS:
        for a in ARMS:
            v = FL[a.upper()]
            sp["tsx2-%s-%s" % (a, s.lower())] = dict(scope="DEV", seed=s, arm=a.upper(), ext=v["ext_hours"], nd=v["dev"]["n_days"],
                                                     ov=dict(B.OV_BASE, SIM_LOSER_TS_EXT_HOURS=v["ext_hours"],
                                                             SIM_LOSER_TS_EXT_DAYS=v["dev"]["ranges"]))
    for s in HO_SEEDS:
        for a in ARMS:
            v = FL[a.upper()]
            sp["tsx2-ho-%s-s%d" % (a, s)] = dict(scope="HO", seed=s, arm=a.upper(), ext=v["ext_hours"], nd=v["ho"]["n_days"],
                                                 ov=dict(k24, SIM_LOSER_TS_EXT_HOURS=v["ext_hours"],
                                                         SIM_LOSER_TS_EXT_DAYS=v["ho"]["ranges"]))
    return sp


def push_ho(ks, q, tag, ov, seed, gpu):
    """= q.push(ks, tag, ov, seed, '20261001', True); gpu=True chi bat enable_gpu (sim van chay CPU)."""
    if not gpu:
        return q.push(ks, tag, ov, seed, "20261001", True)
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": tag, "profile": GA.PROFILE, "overrides": dict(ov), "sim_end_date": "20261001", "xmx": "22g",
           "timeout_s": 10800, "code_sha": q.CODE_SHA, "bins_ds": "", "jar_ds": q.JAR_DS, "market_ds": q.CHAIN,
           "market_align": False, "extra_env": {"HOLDOUT_UNSEAL": q.UNSEAL},
           "ticker_min_days": 2099, "pred_ds": "pred_s%d" % seed, "want_pred_md5": q.ARTS["preds"][str(seed)],
           "want_pred_base": q.PRED_BASE, "tk_ho4p1": {"src": q.TKK, "md5": q.ARTS["tk_md5"]}, "fund_rebuild_ho4p1": q.FUND}
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(q.template().replace("__CFG_JSON__", repr(json.dumps(cfg))))
    dss = [ks.USER + "/" + q.BUNDLE] + ks.TICKER_DS + [ks.USER + "/" + q.JAR_DS]
    md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
          "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
          "dataset_sources": dss, "competition_sources": [], "kernel_sources": [ks.USER + "/" + q.CHAIN, ks.USER + "/" + q.TKK]}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(md, f, indent=1)
    r = ks._api().kernels_push(folder)
    err = getattr(r, "error", None)
    log.info("PUSHED-GPU-HO %s %s err=%s seed=%d", tag, getattr(r, "url", r), err, seed)
    if err:
        raise RuntimeError(str(err))


def tsx_line(txt):
    m = re.findall(r"\[TSX\] extHours=(\d+) extDays=(\d+) deferTicks=(\d+) deferClusters=(\d+) cutAfterDefer=(\d+)", txt)
    return [int(x) for x in m[-1]] if m else None


def pd_rows(tag, cut="20251224"):
    d = pd.read_csv(OUT % tag + "storage/printDone.csv", index_col=False, dtype=str)
    return d[d["start"] < cut].sort_values(list(d.columns)).reset_index(drop=True)


def post_dev(tag, sp):
    p = OUT % tag + "storage/printDone.csv"
    if not os.path.exists(p):
        return dict(tag=tag, passed=False, why="khong co printDone")
    rj, pr, txt = GA.result_json(tag), GA.prof_run(tag), B.logtxt(tag)
    tl = tsx_line(txt)
    chk = dict(jar=rj.get("jar_sha256") == B.jar_sha(), ok=rj.get("ok") is True,
               topk24=pr.get("SELECTOR_RANK_TOPK") == "24", skipfull=pr.get(B.G.KEY) == "true",
               key=pr.get("SIM_LOSER_TS_EXT_HOURS") == str(sp["ext"]) and pr.get("SIM_LOSER_TS_EXT_DAYS") == sp["ov"]["SIM_LOSER_TS_EXT_DAYS"],
               log=tl is not None and tl[0] == sp["ext"] and tl[1] == sp["nd"],
               b0ov=all(pr.get(k) == str(v) for k, v in GA.B0OV.items()))
    r = dict(tag=tag, chk=chk, md5=md5f(p), n=rj.get("n_trades"), eq=rj.get("equity_final"), tsx=tl)
    if sp.get("ref"):
        r["ref_md5"] = md5f(OUT % sp["ref"] + "storage/printDone.csv")
        chk["bitexact_ref"] = r["md5"] == r["ref_md5"]
    r["passed"] = bool(all(chk.values()))
    return r


def post_ho(q, tag, sp):
    ok, chk, md5, n = q.check(tag, sp["ov"], sp["seed"], True)
    tl = tsx_line(q.kernel_text(tag))
    r = dict(tag=tag, ok=ok, chk=chk, md5=md5, n=n, tsx=tl)
    try:
        a, b = pd_rows(tag), pd_rows("ho4-k24-b-s%d" % sp["seed"])
        r["pre2026_same"], r["pre_rows"] = bool(a.equals(b)), [len(a), len(b)]
    except Exception as e:  # noqa: BLE001
        r["pre2026_same"], r["err"] = False, str(e)[:200]
    r["log_ok"] = tl is not None and tl[0] == sp["ext"] and tl[1] == sp["nd"]
    if sp.get("ref"):
        r["ref_md5"] = json.load(open("/home/ubuntu/claude_master/tsx/ho/res_%s.json" % sp["ref"]))["md5"]
        r["bitexact_ref"] = md5 == r["ref_md5"]
    r["passed"] = bool(ok and r["pre2026_same"] and r["log_ok"] and r.get("bitexact_ref", True))
    return r


def run():
    q = Q()
    ks = GA.ks_mod()
    sp = specs(q)
    stp = W + "/state.json"
    st = json.load(open(stp)) if os.path.exists(stp) else {}
    for t in sp:
        st.setdefault(t, dict(state="TODO", pushes=0))
    gchk_dev = md5f(OUT % "tsx-gpuchk-s7" + "storage/printDone.csv") == md5f(OUT % "gqsf-s7" + "storage/printDone.csv")
    log.info("GPU-CHK DEV (tsx-gpuchk-s7 = gqsf-s7, jar nay): %s", gchk_dev)
    gpu_ho = st.get("__gpu_ho")  # None = chua biet, True/False
    gpu_dead = bool(st.get("__gpu_dead"))
    while True:
        mine = {ks.kernel_ref(t): t for t in sp if st[t]["state"] == "PUSHED"}
        for ref, t in list(mine.items()):
            try:
                k = ks._status(ref)
            except Exception as e:  # noqa: BLE001
                log.warning("status %s %s", t, str(e)[:100])
                continue
            if k not in ks.TERMINAL:
                continue
            log.info("%s -> %s", t, k)
            try:
                ks.fetch(t)
            except Exception as e:  # noqa: BLE001
                log.error("fetch %s %s", t, str(e)[:200])
            r = post_dev(t, sp[t]) if sp[t]["scope"] == "DEV" else post_ho(q, t, sp[t])
            r["kstatus"] = str(k)
            json.dump(r, open(W + "/res_%s.json" % t, "w"), indent=1)
            log.info("POST %s passed=%s md5=%s n=%s tsx=%s chk=%s", t, r["passed"], r.get("md5"), r.get("n"), r.get("tsx"), r.get("chk"))
            if not r["passed"] and st[t]["pushes"] < 2 and (str(k) != "COMPLETE" or not r.get("chk", {}).get("ok", False)):
                log.warning("LOI HA TANG %s -> retry (cfg y het)", t)
                st[t]["state"] = "TODO"
                st[t]["gpu"] = False
                st[t]["no_gpu"] = True
                continue
            st[t].update(state="DONE", kstatus=str(k), passed=r["passed"])
            if t == "tsx2-ho-ctl-s7":
                gpu_ho = bool(r["passed"])
                st["__gpu_ho"] = gpu_ho
                log.info("HO ctl GPU bit-exact = %s -> HO dung GPU: %s", r.get("bitexact_ref"), gpu_ho)
                if not gpu_ho and "tsx2-ho-ctlc-s7" not in sp:
                    log.error("HO ctl GPU FAIL -> them ctl CPU tsx2-ho-ctlc-s7")
            if t == "tsx2-ctl-a1" and not r["passed"]:
                log.error("DEV ctl FAIL -> DUNG (V2)")
                json.dump(st, open(stp, "w"), indent=1)
                sys.exit(3)
        if gpu_ho is False and "tsx2-ho-ctlc-s7" not in sp:
            c = dict(sp["tsx2-ho-ctl-s7"])
            c.pop("gpu_only")
            sp["tsx2-ho-ctlc-s7"] = c
            st.setdefault("tsx2-ho-ctlc-s7", dict(state="TODO", pushes=0))
        try:
            acct = set(r for r, _ in q.running(ks))
        except Exception as e:  # noqa: BLE001
            log.warning("running %s", str(e)[:100])
            time.sleep(POLL)
            continue
        mine = {ks.kernel_ref(t): t for t in sp if st[t]["state"] == "PUSHED"}
        my_gpu = sum(1 for t in mine.values() if st[t].get("gpu"))
        my_cpu = len(mine) - my_gpu
        foreign = len(acct - set(mine))
        ho_ctl_ok = st.get("tsx2-ho-ctl-s7", {}).get("passed") or st.get("tsx2-ho-ctlc-s7", {}).get("passed")
        todo = [t for t in sp if st[t]["state"] == "TODO"]
        for t in todo:
            s = sp[t]
            if s["scope"] == "HO" and not s.get("ref") and not ho_ctl_ok:
                continue  # bien the HO cho ctl HO PASS
            if s.get("gpu_only") and (gpu_dead or st[t].get("no_gpu")):
                st[t].update(state="DONE", passed=False, kstatus="GPU_DEAD_OR_RETRY")
                st["__gpu_ho"] = gpu_ho = False
                continue
            can_gpu = (not gpu_dead) and (not st[t].get("no_gpu")) and my_gpu < GPU_MAX and (
                (s["scope"] == "DEV" and s["seed"] != "A1" and gchk_dev) or (s["scope"] == "HO" and (s.get("gpu_only") or gpu_ho)))
            can_cpu = (not s.get("gpu_only")) and my_cpu + foreign < CPU_MAX
            use = "gpu" if can_gpu else ("cpu" if can_cpu else None)
            if use is None:
                continue
            try:
                if s["scope"] == "DEV":
                    (B.push_gpu if use == "gpu" else B.push)(t, s["ov"], s["seed"])
                else:
                    push_ho(ks, q, t, s["ov"], s["seed"], use == "gpu")
            except Exception as e:  # noqa: BLE001
                log.error("push %s (%s) loi %s", t, use, str(e)[:300])
                if use == "gpu":
                    gpu_dead = True
                    st["__gpu_dead"] = True
                    log.error("GPU push loi -> tat GPU cho phan con lai")
                    continue
                break
            st[t].update(state="PUSHED", gpu=use == "gpu", at=time.strftime("%F %T"), pushes=st[t]["pushes"] + 1)
            if use == "gpu":
                my_gpu += 1
            else:
                my_cpu += 1
            time.sleep(40)
        json.dump(st, open(stp, "w"), indent=1)
        n_done = sum(1 for t in sp if st[t]["state"] == "DONE")
        log.info("POLL cpu=%d gpu=%d foreign=%d todo=%d done=%d/%d", my_cpu, my_gpu, foreign,
                 sum(1 for t in sp if st[t]["state"] == "TODO"), n_done, len(sp))
        if n_done == len(sp):
            log.info("RUN XONG pass=%d/%d", sum(bool(st[t].get("passed")) for t in sp), len(sp))
            return
        time.sleep(POLL)


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run()
    elif sys.argv[1] == "specs":
        q = Q()
        for t, s in specs(q).items():
            log.info("%s %s %s ext=%s nd=%s keys=%s", t, s["scope"], s["seed"], s["ext"], s["nd"], sorted(s["ov"]))
