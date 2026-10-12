#!/usr/bin/env python3
"""LIVEFIX2 L5 — parity sim jar fix/live-1011 voi gqsf-a1 (= ho4p1-c2, md5 printDone ad26fd55...).

Cau hinh Y HET ho4p1-c2 (ho4p1_queue.push: K24+skipFull, seed 42, phi goc, SIM_END 20251231, artefact HO4-P1),
chi khac: jar dataset (sim-jar-livefix2 = jar LIVEFIX2) + extra_env SYMBOL_MAPPER_DUP_POLICY=WARN
(mapper Kaggle = ban sao 863 co 8 id trung -> jar moi mac dinh FAIL-FAST; WARN = chay tiep, xem LIVE_DEPLOY_1011.md L5).

Usage (Oracle):
  python3 lf2_parity.py gate     # chi kiem: orchestrator HO4 xong 32 kernel? so kernel dang chay?
  python3 lf2_parity.py jards    # tao dataset Kaggle sim-jar-livefix2 (sim.jar hardlink + profile cua sim-jar-nsel)
  python3 lf2_parity.py push     # tu choi neu gate chua dat (32 ho4-* xong VA < 2 kernel dang chay)
  python3 lf2_parity.py check    # fetch + kiem (ok/jar/mapper/ov/pred/tk/fund) + md5 printDone == ad26fd55
"""
import csv, hashlib, json, logging, os, shutil, sys, time

LF = "/home/ubuntu/claude_master/1011/livefix"
JAR = LF + "/jar/binance-java-sdk-1.2.4.jar"
JAR_DS = "sim-jar-livefix2"
PROF = "/home/ubuntu/claude_master/1008/nsel_impl/ds_sim-jar-nsel/prof_r4_kg0_k16_f015_g155.properties"
TAG = "lf2-c2-s42"
WANT_MD5 = "ad26fd55f0bb5db32038ec8b357cf8e7"
QTSV = "/home/ubuntu/claude_master/1011/ho4p1/q/queue_status.tsv"
EXTRA = {"SYMBOL_MAPPER_DUP_POLICY": "WARN"}
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("lf2")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def Q():
    """import ho4p1_queue (dung chung push/check/ARTS) nhung GO file handler de khong ghi vao log orchestrator."""
    sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
    import ho4p1_queue as q  # noqa: E402
    logging.getLogger().removeHandler(q._fh)
    q.JAR_DS = JAR_DS
    q.JAR_SHA = sha256(JAR)
    return q


def gate(ks=None, q=None):
    rows = list(csv.DictReader(open(QTSV), delimiter="\t"))
    done = [r for r in rows if r["slug"].startswith("ho4-") and r["status"] in ("COMPLETE", "ERROR")]
    ok32 = len({r["slug"] for r in done}) >= 32
    nrun = None
    if ks is not None:
        nrun = len(q.running(ks))
    log.info("GATE ho4-* xong=%d/32 dang_chay=%s", len({r['slug'] for r in done}), nrun)
    return ok32 and (nrun is None or nrun < 2)


def jards():
    q = Q()
    ks = q.GA.ks_mod()
    fol = LF + "/l5/ds_" + JAR_DS
    os.makedirs(fol, exist_ok=True)
    if not os.path.exists(fol + "/sim.jar"):
        os.link(JAR, fol + "/sim.jar")           # hardlink: khong ton dia
    shutil.copy(PROF, fol + "/" + os.path.basename(PROF))
    json.dump({"title": JAR_DS, "id": ks.USER + "/" + JAR_DS, "licenses": [{"name": "CC0-1.0"}]},
              open(fol + "/dataset-metadata.json", "w"))
    r = ks._api().dataset_create_new(fol, public=False, quiet=True, dir_mode="skip")
    log.info("dataset %s -> %s (jar sha %s)", JAR_DS, getattr(r, "url", r), q.JAR_SHA)


def push():
    q = Q()
    ks = q.GA.ks_mod()
    if not gate(ks, q):
        log.error("CHUA TOI LUOT: orchestrator HO4 chua xong 32 kernel hoac da co >= 2 kernel chay — KHONG push")
        sys.exit(3)
    ov = dict(q.PARITY["ho4p1-c2"][0])
    ref = ks.kernel_ref(TAG)
    folder = os.path.join(ks.WORKDIR, ks.slug(TAG))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": TAG, "profile": q.GA.PROFILE, "overrides": ov, "sim_end_date": "20251231", "xmx": "22g",
           "timeout_s": 10800, "code_sha": q.CODE_SHA, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": q.CHAIN,
           "market_align": False, "extra_env": dict(EXTRA),
           "ticker_min_days": 2099, "pred_ds": "pred_s42", "want_pred_md5": q.ARTS["preds"]["42"],
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
    log.info("PUSHED %s %s ov=%s extra_env=%s jar=%s", TAG, getattr(r, "url", r), json.dumps(ov), EXTRA, q.JAR_SHA)


def check():
    q = Q()
    ks = q.GA.ks_mod()
    st = ks._status(ks.kernel_ref(TAG))
    log.info("status %s", st)
    if st not in ks.TERMINAL:
        return
    ks.fetch(TAG)
    ok, chk, md5, n = q.check(TAG, dict(q.PARITY["ho4p1-c2"][0]), 42, False)
    txt = q.kernel_text(TAG)
    chk["warn_policy"] = "[MAPPER-DUP]" in txt and "WARN" in txt
    verdict = "PASS" if (ok and md5 == WANT_MD5) else "FAIL"
    log.info("L5 %s md5=%s (want %s) n=%s chk=%s", verdict, md5, WANT_MD5, n, chk)
    json.dump({"verdict": verdict, "md5": md5, "want": WANT_MD5, "n": n, "chk": chk, "jar_sha": q.JAR_SHA,
               "at": time.strftime("%F %T")}, open(LF + "/l5/lf2_parity_result.json", "w"), indent=1)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "gate"
    {"gate": lambda: gate(), "jards": jards, "push": push, "check": check}[cmd]()
