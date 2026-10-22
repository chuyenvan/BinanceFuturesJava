#!/usr/bin/env python3
"""TSX_V3 (PREREG_TSX_V3) - day + parity cac kernel MOI cua TSX_V3: tsx3-ctl-s13 (V0 = X14, kiem md5 = tsx-x14-s13) va
tsx3-v2-{8 seed DEV} (V2 = B3b r0.20). V1/V3/V4 TAI DUNG run tsx2-{v420,vt25,vl45}-* (overrides byte-identical, PREREG_TSX_V3 §0);
HO V2 = tsx-ho-x14-s* (khong ngay HO nao bi tat). Chi CPU. Chia slot voi pipeline TSX_V2_SIM dang chay: day khi
(so kernel RUNNING/QUEUED cua tai khoan) - (so GPU dang PUSHED cua tsx2sim) < 5.
Parity = research/tsx_v2_sim/run.py post_dev. State: ~/claude_master/tsx_v3/state.json. Usage: python3 run.py run|specs
"""
import hashlib
import json
import logging
import os
import re
import sys
import time

sys.path.insert(0, "/home/ubuntu/claude_master/tsx")
import tsx_driver as T  # noqa: E402  (jar sim-jar-tsx, CODE_SHA a8690d46)

B, GA = T.B, T.GA
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tsx3run")
W = "/home/ubuntu/claude_master/tsx_v3"
FL = json.load(open(W + "/flags_v3.json"))["arms"]
OUT = "/home/ubuntu/kaggle_sim/out/%s/"
CPU_MAX, POLL = 5, 180
WANT_JAR = open("/home/ubuntu/claude_master/tsx/jar.sha256").read().split()[0]


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def specs():
    x, v = FL["V0"], FL["V2"]
    sp = {"tsx3-ctl-s13": dict(seed="S13", arm="V0", ext=x["ext_hours"], nd=x["dev"]["n_days"], ref="tsx-x14-s13",
                               ov=dict(B.OV_BASE, SIM_LOSER_TS_EXT_HOURS=x["ext_hours"], SIM_LOSER_TS_EXT_DAYS=x["dev"]["ranges"]))}
    assert sp["tsx3-ctl-s13"]["ov"] == T.OV_ON
    for s in T.SEEDS:
        sp["tsx3-v2-" + s.lower()] = dict(seed=s, arm="V2", ext=v["ext_hours"], nd=v["dev"]["n_days"],
                                          ov=dict(B.OV_BASE, SIM_LOSER_TS_EXT_HOURS=v["ext_hours"], SIM_LOSER_TS_EXT_DAYS=v["dev"]["ranges"]))
    return sp


def tsx_line(txt):
    m = re.findall(r"\[TSX\] extHours=(\d+) extDays=(\d+) deferTicks=(\d+) deferClusters=(\d+) cutAfterDefer=(\d+)", txt)
    return [int(x) for x in m[-1]] if m else None


def post_dev(tag, sp):
    """= research/tsx_v2_sim/run.py post_dev."""
    p = OUT % tag + "storage/printDone.csv"
    if not os.path.exists(p):
        return dict(tag=tag, passed=False, why="khong co printDone", chk={})
    rj, pr, txt = GA.result_json(tag), GA.prof_run(tag), B.logtxt(tag)
    tl = tsx_line(txt)
    chk = dict(jar=rj.get("jar_sha256") == B.jar_sha() == WANT_JAR, ok=rj.get("ok") is True,
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


def foreign_gpu():
    try:
        st = json.load(open("/home/ubuntu/claude_master/tsx2sim/state.json"))
    except Exception:  # noqa: BLE001
        return 0
    return sum(1 for k, v in st.items() if not k.startswith("__") and v.get("state") == "PUSHED" and v.get("gpu"))


def running(ks):
    out = []
    for k in ks._api().kernels_list(mine=True, page_size=50):
        try:
            s = ks._status(k.ref)
        except Exception:  # noqa: BLE001
            continue
        if s in ("RUNNING", "QUEUED"):
            out.append(k.ref)
    return out


def run():
    assert B.jar_sha() == WANT_JAR
    ks = GA.ks_mod()
    sp = specs()
    stp = W + "/state.json"
    st = json.load(open(stp)) if os.path.exists(stp) else {}
    for t in sp:
        st.setdefault(t, dict(state="TODO", pushes=0))
    order = ["tsx3-ctl-s13"] + [t for t in sp if t != "tsx3-ctl-s13"]
    while True:
        for t in order:
            if st[t]["state"] != "PUSHED":
                continue
            try:
                k = ks._status(ks.kernel_ref(t))
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
            r = post_dev(t, sp[t])
            r["kstatus"] = str(k)
            json.dump(r, open(W + "/res_%s.json" % t, "w"), indent=1)
            log.info("POST %s passed=%s md5=%s n=%s tsx=%s chk=%s", t, r["passed"], r.get("md5"), r.get("n"), r.get("tsx"), r.get("chk"))
            if not r["passed"] and st[t]["pushes"] < 2 and (str(k) != "COMPLETE" or not r.get("chk", {}).get("ok", False)):
                log.warning("LOI HA TANG %s -> retry (cfg y het)", t)
                st[t]["state"] = "TODO"
                continue
            st[t].update(state="DONE", kstatus=str(k), passed=r["passed"])
            if t == "tsx3-ctl-s13" and not r["passed"]:
                log.error("V0 ctl FAIL -> DUNG (VA2)")
                json.dump(st, open(stp, "w"), indent=1)
                sys.exit(3)
        try:
            acct = running(ks)
        except Exception as e:  # noqa: BLE001
            log.warning("running %s", str(e)[:100])
            time.sleep(POLL)
            continue
        fg = foreign_gpu()
        used = len(acct) - fg
        for t in order:
            if st[t]["state"] != "TODO" or used >= CPU_MAX:
                continue
            s = sp[t]
            try:
                B.push(t, s["ov"], s["seed"])
            except Exception as e:  # noqa: BLE001
                log.error("push %s loi %s", t, str(e)[:300])
                break
            st[t].update(state="PUSHED", at=time.strftime("%F %T"), pushes=st[t]["pushes"] + 1)
            used += 1
            time.sleep(40)
        json.dump(st, open(stp, "w"), indent=1)
        n_done = sum(1 for t in sp if st[t]["state"] == "DONE")
        log.info("POLL acct=%d tsx2gpu=%d used_cpu~%d todo=%d pushed=%d done=%d/%d", len(acct), fg, used,
                 sum(1 for t in sp if st[t]["state"] == "TODO"), sum(1 for t in sp if st[t]["state"] == "PUSHED"), n_done, len(sp))
        if n_done == len(sp):
            log.info("RUN XONG pass=%d/%d", sum(bool(st[t].get("passed")) for t in sp), len(sp))
            return
        time.sleep(POLL)


if __name__ == "__main__":
    if sys.argv[1] == "run":
        run()
    elif sys.argv[1] == "specs":
        for t, s in specs().items():
            log.info("%s %s ext=%s nd=%s ref=%s keys=%s", t, s["seed"], s["ext"], s["nd"], s.get("ref"), sorted(s["ov"]))
