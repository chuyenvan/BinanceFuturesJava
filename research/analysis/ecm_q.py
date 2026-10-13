#!/usr/bin/env python3
"""ECMEAS queue (PREREG_ENTRYCOST_MEASURE 48ff35a5). Mau ~/claude_master/1012/ecost/ec_parity.py.
D: ecm-d-s<seed> (7 seed, s42 dung lai ec-s-s42) = PARITY["ho4p1-c2"] + bucket thuc, SIM_END 20251231, khong unseal.
H: ecm-h-s<seed> (8 seed) = cung ov, SIM_END 20261001, HOLDOUT_UNSEAL trong extra_env (y ho4p1_queue pha 1 k24-b).
Jar sim-jar-ecost sha 246087fb (code b58e05c9). <= 2 kernel song song TOAN tai khoan; poll 300 s.
Usage: setsid nohup python3 ecm_q.py > ecm_q.out 2>&1 < /dev/null &
"""
import csv, hashlib, json, logging, os, sys, time

W = "/home/ubuntu/claude_master/1013/ecm"
EC = "/home/ubuntu/claude_master/1012/ecost"
JAR = EC + "/jar/binance-java-sdk-1.2.4.jar"
JAR_DS = "sim-jar-ecost"
WANT_JAR = "246087fb606c5307c407a442062d677832ef29fd3bfb81d6eb7516aa075754cf"
CODE_SHA = open(EC + "/jar/COMMIT").read().strip()[:8]
BUCKET = {"SIM_ENTRY_COST_MODE": "bucket", "SIM_ENTRY_COST_NC": "0.0007", "SIM_ENTRY_COST_C1": "0.0018",
          "SIM_ENTRY_COST_C2": "0.0019", "SIM_ENTRY_COST_C4": "0.0032"}
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
POLL, MAXPAR = 300, 2
os.makedirs(W + "/res", exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ecmq")
fh = logging.FileHandler(W + "/ecm_q.log")
fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(fh)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def Q():
    sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
    import ho4p1_queue as q  # noqa: E402
    logging.getLogger().removeHandler(q._fh)
    q.JAR_DS = JAR_DS
    q.JAR_SHA = sha256(JAR)
    assert q.JAR_SHA == WANT_JAR, q.JAR_SHA
    return q


def specs():
    out = []
    for s in SEEDS:
        out.append(("ecm-h-s%d" % s, s, "20261001", True))
        if s != 42:
            out.append(("ecm-d-s%d" % s, s, "20251231", False))
    return out


def ov_of(q):
    ov = dict(q.PARITY["ho4p1-c2"][0])
    assert "SIM_CRASH_ENTRY_PENALTY" not in ov and ov == q.CFGS["k24"]
    ov.update(BUCKET)
    return ov


def push(q, ks, tag, seed, end, unseal):
    ov = ov_of(q)
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": tag, "profile": q.GA.PROFILE, "overrides": ov, "sim_end_date": end, "xmx": "22g",
           "timeout_s": 10800, "code_sha": CODE_SHA, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": q.CHAIN,
           "market_align": False, "extra_env": ({"HOLDOUT_UNSEAL": q.UNSEAL} if unseal else {}),
           "ticker_min_days": 2099, "pred_ds": "pred_s%d" % seed, "want_pred_md5": q.ARTS["preds"][str(seed)],
           "want_pred_base": q.PRED_BASE, "tk_ho4p1": {"src": q.TKK, "md5": q.ARTS["tk_md5"]},
           "fund_rebuild_ho4p1": q.FUND}
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(q.template().replace("__CFG_JSON__", repr(json.dumps(cfg))))
    dss = [ks.USER + "/" + q.BUNDLE] + ks.TICKER_DS + [ks.USER + "/" + JAR_DS]
    md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
          "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": dss, "competition_sources": [],
          "kernel_sources": [ks.USER + "/" + q.CHAIN, ks.USER + "/" + q.TKK]}
    json.dump(md, open(os.path.join(folder, "kernel-metadata.json"), "w"), indent=1)
    r = ks._api().kernels_push(folder)
    err = getattr(r, "error", None)
    log.info("PUSHED %s url=%s ver=%s err=%s seed=%d end=%s unseal=%s ov=%s jar=%s code=%s", tag, getattr(r, "url", r),
             getattr(r, "version_number", getattr(r, "versionNumber", None)), err, seed, end, unseal, json.dumps(ov),
             q.JAR_SHA[:8], CODE_SHA)
    return not err, getattr(r, "version_number", getattr(r, "versionNumber", None))


def check(q, ks, tag, seed, unseal, st):
    ks.fetch(tag)
    ov = ov_of(q)
    ok, chk, md5, n = q.check(tag, ov, seed, unseal)
    txt = q.kernel_text(tag)
    ec = sorted(set(ln.strip()[24:].strip()[:400] for ln in txt.splitlines() if "[ENTRY-COST]" in ln))
    res = {"tag": tag, "seed": seed, "status": st, "md5_printDone": md5, "n": n, "chk": chk, "chk_ok": ok,
           "n_chk_true": sum(1 for v in chk.values() if v is True), "n_chk": len(chk), "jar_sha": q.JAR_SHA,
           "code_sha": CODE_SHA, "ov": ov, "unseal": unseal, "entry_cost_lines": ec,
           "summary_bucket": any("SUMMARY mode=bucket" in x for x in ec), "at": time.strftime("%F %T")}
    o = q.OUT % tag
    try:
        rj = json.load(open(o + "result.json"))
        for k in ("equity_final", "java_rc", "date_last", "secs", "jar_sha256", "pred_md5_used"):
            res[k] = rj.get(k)
    except Exception as e:  # noqa: BLE001
        res["result_json_err"] = str(e)[:80]
    log.info("RESULT %s ok=%s %d/%d md5=%s n=%s bucket=%s", tag, ok, res["n_chk_true"], res["n_chk"], md5, n,
             res["summary_bucket"])
    json.dump(res, open(W + "/res/%s.json" % tag, "w"), indent=1)
    return res


def main():
    q = Q()
    ks = q.GA.ks_mod()
    sp = {t: (s, e, u) for t, s, e, u in specs()}
    stp = W + "/state.json"
    st = json.load(open(stp)) if os.path.exists(stp) else {t: {"state": "TODO"} for t in sp}
    while True:
        for t in sp:
            if st[t]["state"] == "PUSHED":
                try:
                    k = ks._status(ks.kernel_ref(t))
                except Exception as e:  # noqa: BLE001
                    log.warning("status %s loi %s", t, str(e)[:100])
                    continue
                st[t]["last"] = k
                if k in ks.TERMINAL:
                    s, e, u = sp[t]
                    r = check(q, ks, t, s, u, k)
                    st[t].update(state="DONE", ok=r["chk_ok"], md5=r["md5_printDone"], n=r["n"], done_at=time.strftime("%F %T"))
        try:
            run = set(r for r, _ in q.running(ks))
        except Exception as e:  # noqa: BLE001
            log.warning("running() loi %s", str(e)[:100])
            json.dump(st, open(stp, "w"), indent=1)
            time.sleep(POLL)
            continue
        mine = set(ks.kernel_ref(t) for t in sp if st[t]["state"] == "PUSHED")
        busy = run | mine
        todo = [t for t in sp if st[t]["state"] == "TODO"]
        log.info("POLL run_acct=%d mine_inflight=%d busy=%d todo=%d done=%d", len(run), len(mine), len(busy), len(todo),
                 sum(1 for t in sp if st[t]["state"] == "DONE"))
        while todo and len(busy) < MAXPAR:
            t = todo.pop(0)
            s, e, u = sp[t]
            try:
                ok, ver = push(q, ks, t, s, e, u)
            except Exception as ex:  # noqa: BLE001
                ok, ver = False, None
                log.error("push %s exception %s", t, str(ex)[:200])
            if ok:
                st[t].update(state="PUSHED", ver=ver, pushed_at=time.strftime("%F %T"))
                busy.add(ks.kernel_ref(t))
            else:
                log.error("push %s FAIL -> de TODO, thu lai vong sau", t)
                break
        json.dump(st, open(stp, "w"), indent=1)
        if all(st[t]["state"] == "DONE" for t in sp):
            log.info("ALLDONE")
            return
        time.sleep(POLL)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "dry":
        q = Q()
        ks = q.GA.ks_mod()
        log.info("specs %s", specs())
        log.info("ov %s", json.dumps(ov_of(q)))
        log.info("running %s", q.running(ks))
        log.info("template ok len=%d", len(q.template()))
    else:
        main()
