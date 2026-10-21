#!/usr/bin/env python3
"""B15_V11 orchestrator (PREREG_B15_V11 6cf67a58). V3 (size=1,0 qua co) truoc, S15 sau khi V3 cung nhanh PASS.
DEV: burst_cooldown_driver.push/push_gpu (patch boi tsx_driver: jar sim-jar-tsx). HO: ho4p1_queue.push (end 20261001, unseal).
Usage: python3 b15_run.py run | status
"""
import hashlib
import json
import logging
import os
import re
import sys
import time

sys.path.insert(0, "/home/ubuntu/claude_master/tsx")
import tsx_driver as T  # noqa: E402  (patch B -> sim-jar-tsx)

B, GA = T.B, T.GA
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("b15")
W = "/home/ubuntu/claude_master/b15"
OUT = "/home/ubuntu/kaggle_sim/out/%s/"
F15 = "0.0225"
HO_SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
CPU_MAX, GPU_MAX, POLL = 5, 2, 240


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def Q():
    sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
    import ho4p1_queue as q
    logging.getLogger().removeHandler(q._fh)
    q.JAR_DS = "sim-jar-tsx"
    q.JAR_SHA = sha256("/home/ubuntu/src_wt_bcd/target/binance-java-sdk-1.2.4.jar")
    assert q.JAR_SHA == open("/home/ubuntu/claude_master/tsx/jar.sha256").read().split()[0]
    return q


def jobs(q):
    fl = json.load(open("/home/ubuntu/claude_master/tsx/ho/ho_flags.json"))
    k24 = dict(q.CFGS["k24"])
    hx = dict(k24, SIM_LOSER_TS_EXT_HOURS=336, SIM_LOSER_TS_EXT_DAYS=fl["ranges"])
    J = {"b15-f015-a1": dict(kind="DEV", seed="A1", ov=dict(T.OV_ON, SIM_F_BASE="0.015"), gate=None, ref="tsx-x14-a1"),
         "b15-ho-f015-s42": dict(kind="HO", seed=42, ov=dict(hx, SIM_F_BASE="0.015"), gate=None, ref="tsx-ho-x14-s42")}
    for s in T.SEEDS:
        J["b15-x14-%s" % s.lower()] = dict(kind="DEV", seed=s, ov=dict(T.OV_ON, SIM_F_BASE=F15), gate="b15-f015-a1")
    for s in HO_SEEDS:
        J["b15-ho-x14-s%d" % s] = dict(kind="HO", seed=s, ov=dict(hx, SIM_F_BASE=F15), gate="b15-ho-f015-s42")
    return J


def tsx_line(txt):
    m = re.findall(r"\[TSX\] extHours=(\d+) extDays=(\d+) deferTicks=(\d+) deferClusters=(\d+) cutAfterDefer=(\d+)", txt)
    return [int(x) for x in m[-1]] if m else None


def pc_line(txt):
    m = re.findall(r"\[CONC-PC\] SUMMARY blocked=(\d+)", txt)
    return int(m[-1]) if m else None


def post(q, t, j):
    r = dict(tag=t, kind=j["kind"], seed=j["seed"])
    pdp = OUT % t + "storage/printDone.csv"
    if not os.path.exists(pdp):
        r.update(passed=False, why="no printDone")
        return r
    r["md5"] = md5f(pdp)
    if j["kind"] == "DEV":
        rj, pr, txt = GA.result_json(t), GA.prof_run(t), B.logtxt(t)
        chk = dict(jar=rj.get("jar_sha256") == B.jar_sha(), ok=rj.get("ok") is True,
                   keys=all(str(pr.get(k)) == str(v) for k, v in j["ov"].items()),
                   fbase=pr.get("SIM_F_BASE") == j["ov"]["SIM_F_BASE"])
        r["n"] = rj.get("n_trades")
    else:
        ok, chk, md5, n = q.check(t, j["ov"], j["seed"], True)
        txt = q.kernel_text(t)
        r["n"] = n
        fp = OUT % t + "prof_run.properties"
        rj = json.load(open(OUT % t + "result.json"))
        chk["fbase"] = str((rj.get("overrides") or {}).get("SIM_F_BASE")) == j["ov"]["SIM_F_BASE"]
        if os.path.exists(fp):
            chk["fbase_prof"] = ("SIM_F_BASE=" + j["ov"]["SIM_F_BASE"]) in open(fp).read().split("\n")
    tl = tsx_line(txt)
    chk["tsx"] = tl is not None and tl[0] == 336
    r.update(chk=chk, tsx=tl, pc_blocked=pc_line(txt))
    if j.get("ref"):
        r["ref_md5"] = md5f(OUT % j["ref"] + "storage/printDone.csv")
        chk["bitexact"] = r["md5"] == r["ref_md5"]
    r["passed"] = all(chk.values())
    log.info("POST %s passed=%s n=%s md5=%s tsx=%s pc=%s chk=%s", t, r["passed"], r["n"], r["md5"], tl, r["pc_blocked"], chk)
    json.dump(r, open(W + "/res_%s.json" % t, "w"), indent=1)
    return r


def push(q, ks, t, j, gpu):
    if j["kind"] == "HO":
        q.push(ks, t, j["ov"], j["seed"], "20261001", True)
    elif gpu:
        B.push_gpu(t, j["ov"], j["seed"])
    else:
        B.push(t, j["ov"], j["seed"])


def run():
    assert open(W + "/prereg_commit.txt").read().startswith("6cf67a58")
    assert B.P0_TAG == "tsx-p0" and B.p0_check()["ok"]
    q = Q()
    ks = GA.ks_mod()
    J = jobs(q)
    gok = B.gpu_ok()
    log.info("GPU_OK=%s jobs=%d", gok, len(J))
    stp = W + "/state.json"
    st = json.load(open(stp)) if os.path.exists(stp) else {t: {"state": "TODO"} for t in J}
    while True:
        for t, j in J.items():
            if st[t]["state"] == "PUSHED":
                try:
                    k = ks._status(ks.kernel_ref(t))
                except Exception as e:  # noqa: BLE001
                    log.warning("status %s %s", t, str(e)[:100])
                    continue
                if k in ks.TERMINAL:
                    log.info("%s -> %s", t, k)
                    try:
                        ks.fetch(t)
                    except Exception as e:  # noqa: BLE001
                        log.error("fetch %s %s", t, str(e)[:200])
                    r = post(q, t, j)
                    if not r["passed"] and st[t].get("retry", 0) < 1 and not j.get("ref"):
                        st[t].update(state="TODO", retry=st[t].get("retry", 0) + 1)
                        log.warning("RETRY %s", t)
                    else:
                        st[t].update(state="DONE", kstatus=str(k), passed=r["passed"])
        for t, j in J.items():
            g = j["gate"]
            if st[t]["state"] == "TODO" and g and st[g]["state"] == "DONE" and not st[g].get("passed"):
                st[t]["state"] = "BLOCKED"
                log.error("BLOCKED %s: gate %s FAIL", t, g)
        try:
            busy = [r for r, _ in q.running(ks)]
        except Exception as e:  # noqa: BLE001
            log.warning("running %s", str(e)[:100])
            time.sleep(POLL)
            continue
        mine_gpu = [t for t in J if st[t]["state"] == "PUSHED" and st[t].get("gpu")]
        ncpu = len(busy) - len([t for t in mine_gpu if ks.kernel_ref(t) in busy])
        for t, j in J.items():
            if st[t]["state"] != "TODO":
                continue
            g = j["gate"]
            if g and not (st[g]["state"] == "DONE" and st[g].get("passed")):
                continue
            use_gpu = bool(gok and j["kind"] == "DEV" and j["seed"] != "A1" and len(mine_gpu) < GPU_MAX)
            if not use_gpu and ncpu >= CPU_MAX:
                continue
            try:
                push(q, ks, t, j, use_gpu)
            except Exception as e:  # noqa: BLE001
                log.error("push %s %s", t, str(e)[:200])
                break
            st[t].update(state="PUSHED", at=time.strftime("%F %T"), gpu=use_gpu)
            if use_gpu:
                mine_gpu.append(t)
            else:
                ncpu += 1
            time.sleep(30)
        json.dump(st, open(stp, "w"), indent=1)
        cnt = {s: sum(v["state"] == s for v in st.values()) for s in ("TODO", "PUSHED", "DONE", "BLOCKED")}
        log.info("POLL busy=%d cpu=%d gpu=%d %s", len(busy), ncpu, len(mine_gpu), cnt)
        if cnt["TODO"] == 0 and cnt["PUSHED"] == 0:
            log.info("B15 RUN XONG pass=%d/%d", sum(bool(v.get("passed")) for v in st.values()), len(st))
            return
        time.sleep(POLL)


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run()
    elif sys.argv[1] == "dry":
        q = Q()
        for t, j in jobs(q).items():
            o = {k: v for k, v in j["ov"].items() if k != "SIM_F_BASE"}
            if j["kind"] == "DEV":
                ref = "tsx-x14-%s" % j["seed"].lower()
                pr = GA.prof_run(ref)
                same = all(str(pr.get(k)) == str(v) for k, v in o.items()) and "SIM_F_BASE" not in json.load(open(OUT % ref + "result.json")).get("overrides", {})
            else:
                ref = "tsx-ho-x14-s%d" % j["seed"]
                ro = json.load(open(OUT % ref + "result.json")).get("overrides") or {}
                same = set(ro) == set(o) and all(str(ro[k]) == str(v) for k, v in o.items())
            log.info("DRY %-18s %s seed=%s F=%s gate=%s ov_eq_ref(%s)=%s", t, j["kind"], j["seed"], j["ov"]["SIM_F_BASE"], j["gate"], ref, same)
    else:
        print(json.dumps(json.load(open(W + "/state.json")), indent=1))
