#!/usr/bin/env python3
"""R1 A3 (S1FULL + A1 ha hang = B0') driver Kaggle. Prereg PREREG_R1_S1_ABLATION (44acf9cd) + ADDENDUM 1.
Cau hinh = DUNG run tham chieu tsx-x14-<seed> (X14 DEV: jar sim-jar-tsx, profile GA.PROFILE, OV_BASE + TS_EXT cung
flags DEV); CHI doi bins selector: 16 file A3 (dataset r1-a3-bins) + 2 file 2021 (s3-moc-2021bins) -> s3_funding.py
(byte-faithful) trong kernel -> WFO_DATA_DIR moi. Seed != A1: chen them PATCH pred_ds cua gate_ablation (nhu tsx).
Usage: upload | check <seed> | push <seed> [--dry]
"""
import argparse
import base64
import hashlib
import json
import logging
import os
import sys

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
sys.path.insert(0, "/home/ubuntu/claude_master/iso")
import gate_ablation_driver as GA  # noqa: E402
import gate_skipfull_driver as G  # noqa: E402
import burst_cooldown_driver as B  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("r1a3")
D = "/home/ubuntu/claude_master/res1109/r1_s1"
BINS = D + "/a3_bins"
A3_DS = "r1-a3-bins"
MOC21_DS = "s3-moc-2021bins"
JAR_DS = "sim-jar-tsx"
CODE_SHA = open("/home/ubuntu/claude_master/tsx/code_sha.txt").read().strip()
FLAGS = json.load(open("/home/ubuntu/claude_master/tsx/flags.json"))
OV = dict(B.OV_BASE, SIM_LOSER_TS_EXT_HOURS=336, SIM_LOSER_TS_EXT_DAYS=FLAGS["ranges"])
HELPERS = {"s3_funding.py": os.path.join(REPO, "research/pipeline/x1/s3_funding.py")}
SEEDS = G.SEEDS

A3_BLOCK = r'''
# [R1 A3 2026-11-10] bins S1FULL+A1 (dataset a3_ds, 16 file) + 2 file 2021 (moc21_ds) -> s3_funding.py -> WFO_DATA_DIR moi.
A3_INFO = {}
if CFG.get("a3_ds"):
    import base64 as _b64m
    import hashlib as _h5
    _HELP = os.path.join(WORK, "a3_helpers")
    os.makedirs(_HELP, exist_ok=True)
    for _nm, _bb in __A3_HELPERS__.items():
        with open(os.path.join(_HELP, _nm), "wb") as _f:
            _f.write(_b64m.b64decode(_bb))
    _a3 = sorted(c for c in glob.glob(IN + "/**/predict_wf_*.bin", recursive=True) if ("/" + CFG["a3_ds"] + "/") in c)
    _m21 = sorted(c for c in glob.glob(IN + "/**/predict_wf_2021*.bin", recursive=True)
                  if ("/" + CFG["moc21_ds"] + "/") in c)
    if len(_a3) != 16 or len(_m21) != 2:
        LOG.error("A3_FAIL so file: a3=%d (can 16) moc21=%d (can 2)", len(_a3), len(_m21))
        sys.exit(7)
    _hh = _h5.sha256()
    for _p in _a3:
        with open(_p, "rb") as _f:
            for _b in iter(lambda: _f.read(1 << 20), b""):
                _hh.update(_b)
    _sha = _hh.hexdigest()
    LOG.info("A3 bins sha=%s want=%s", _sha, CFG["want_a3_sha"])
    if _sha != CFG["want_a3_sha"]:
        LOG.error("A3_FAIL sha bins lech -> DUNG")
        sys.exit(7)
    A3_BINS = os.path.join(WORK, "a3_bins")
    os.makedirs(A3_BINS, exist_ok=True)
    for _p in _a3 + _m21:
        _d = os.path.join(A3_BINS, os.path.basename(_p))
        if not os.path.lexists(_d):
            os.symlink(_p, _d)
    A3_DSD = os.path.join(WORK, "a3_ds")
    os.makedirs(A3_DSD, exist_ok=True)
    for _nm in ("market.bin", "pred.bin"):
        if not os.path.lexists(os.path.join(A3_DSD, _nm)):
            os.symlink(os.path.join(DS, _nm), os.path.join(A3_DSD, _nm))
    _fj = os.path.join(WORK, "a3_funding.json")
    _t0 = time.time()
    _rc = subprocess.call([sys.executable, os.path.join(_HELP, "s3_funding.py"), "--bins", A3_BINS, "--data", DS,
                           "--out", os.path.join(A3_DSD, "funding.bin"), "--json", _fj])
    LOG.info("A3 s3_funding rc=%s %.0fs", _rc, time.time() - _t0)
    if _rc != 0:
        sys.exit(7)
    _F = json.load(open(_fj))
    _base, _order = {}, []
    for _ln in open(os.path.join(DS, "manifest.txt")):
        _s = _ln.rstrip("\n")
        _k = _s.split("=", 1)[0].strip()
        if _k and "=" in _s and not _k.startswith("predictWf."):
            if _k not in _base:
                _order.append(_k)
            _base[_k] = _s.split("=", 1)[1].strip()
    import datetime as _dt
    _mn = min(m["minTs"] for m in _F["predictWf"])
    _base.update({"fundingPredDir": A3_BINS, "binsSha256": _F["binsSha256"], "foldCount": str(_F["foldCount"]),
                  "maxFoldSpanDays": str(_F["maxFoldSpanDays"]), "fundingCount": str(_F["fundingCount"]),
                  "fundingRaw15mCount": str(_F["fundingRaw15mCount"]), "md5_funding": _F["md5_funding"],
                  "leakFreeFrom": _dt.datetime.utcfromtimestamp(_mn / 1000 + 7 * 3600).strftime("%Y-%m-%d"),
                  "selAblationArm": "R1_A3"})
    for _k in ("fundingPredDir", "binsSha256", "foldCount", "maxFoldSpanDays", "fundingCount",
               "fundingRaw15mCount", "md5_funding", "leakFreeFrom", "selAblationArm"):
        if _k not in _order:
            _order.append(_k)
    with open(os.path.join(A3_DSD, "manifest.txt"), "w") as _f:
        for _k in _order:
            _f.write("%s=%s\n" % (_k, _base[_k]))
        for _m in sorted(_F["predictWf"], key=lambda x: x["name"]):
            _span = (_m["maxTs"] - _m["minTs"]) // 86400000
            _f.write("predictWf.%s=md5:%s;ts:%d..%d;span:%dd;rec:%d\n"
                     % (_m["name"], _m["md5"], _m["minTs"], _m["maxTs"], _span, _m["nrec"]))
    A3_INFO.update(bins_sha256=_sha, funding_md5=_F["md5_funding"], funding_count=_F["fundingCount"],
                   fold_count=_F["foldCount"], leak_free_from=_base["leakFreeFrom"])
    LOG.info("A3 dataset ok: funding md5=%s count=%d fold=%d", _F["md5_funding"], _F["fundingCount"], _F["foldCount"])
    DS = A3_DSD
    PREDWF = A3_BINS
'''

A3_CLEAN = r'''# [R1 A3] md5 printDone + don file lon truoc khi Kaggle luu output
if os.path.exists(PDONE):
    import hashlib as _h6
    A3_INFO["md5_printdone"] = _h6.md5(open(PDONE, "rb").read()).hexdigest()
    with open(WORK + "/result.json", "w") as f:
        res["r1_a3"] = A3_INFO
        json.dump(res, f, indent=1)
for _p in (os.path.join(WORK, "a3_ds"), os.path.join(WORK, "a3_bins")):
    shutil.rmtree(_p, ignore_errors=True)
'''


def _patch(t, old, new):
    assert t.count(old) == 1, ("anchor", t.count(old), old[:60])
    return t.replace(old, new)


def template(seed):
    t = GA.template() if seed != "A1" else GA.ks_mod().KERNEL_TEMPLATE
    helpers = {nm: base64.b64encode(open(p, "rb").read()).decode() for nm, p in HELPERS.items()}
    blk = A3_BLOCK.replace("__A3_HELPERS__", repr(helpers))
    t = _patch(t, "PREDWF = os.path.dirname(_cand[0])\n", "PREDWF = os.path.dirname(_cand[0])\n" + blk)
    t = _patch(t, 'subprocess.call(["gzip", "-f", LOGP])', A3_CLEAN + 'subprocess.call(["gzip", "-f", LOGP])')
    assert "NOWRITE_HOST" in t and "SYMBOL_MAPPER_PREFLIGHT_FAIL" in t
    return t


def a3_sha():
    rep = json.load(open(BINS + "/a3_report.json"))
    assert rep["G_NET0"] and rep["G_FULL"] and rep["G_SAN"], "cong A3 chua dat"
    h = hashlib.sha256()
    for fn in sorted(f for f in os.listdir(BINS) if f.startswith("predict_wf_") and f.endswith(".bin")):
        with open(os.path.join(BINS, fn), "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
    assert h.hexdigest() == rep["a3_bins_sha256_concat"]
    return h.hexdigest()


def upload():
    ks = GA.ks_mod()
    meta = {"title": A3_DS, "id": ks.USER + "/" + A3_DS, "licenses": [{"name": "CC0-1.0"}]}
    with open(os.path.join(BINS, "dataset-metadata.json"), "w") as f:
        json.dump(meta, f)
    a3_sha()
    r = ks._api().dataset_create_new(BINS, public=False, quiet=True, dir_mode="skip")
    log.info("dataset create -> %s", getattr(r, "url", r))
    B.wait_ds(ks.USER + "/" + A3_DS) if hasattr(B, "wait_ds") else None


def build(seed):
    ks = GA.ks_mod()
    tag = "r1-a3-" + seed.lower()
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": tag, "profile": GA.PROFILE, "overrides": dict(OV), "sim_end_date": "20251231", "xmx": "22g",
           "timeout_s": 7200, "code_sha": CODE_SHA, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": "",
           "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
           "a3_ds": A3_DS, "moc21_ds": MOC21_DS, "want_a3_sha": a3_sha()}
    dss = [ks.USER + "/" + GA.BUNDLE] + ks.TICKER_DS + [ks.USER + "/" + JAR_DS, ks.USER + "/" + MOC21_DS,
                                                         ks.USER + "/" + A3_DS]
    dsn, md5 = G.pred_of(seed)
    if dsn is not None:
        cfg.update(pred_ds=dsn, want_pred_md5=md5, want_pred_base=GA.PRED0_MD5)
        dss.append(ks.USER + "/" + dsn)
    code = template(seed).replace("__CFG_JSON__", repr(json.dumps(cfg)))
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(code)
    md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
          "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": dss, "competition_sources": [], "kernel_sources": []}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(md, f, indent=1)
    return ks, folder, ref, cfg


def check(seed):
    """So cau hinh voi run tham chieu tsx-x14-<seed> (overrides, jar)."""
    ks, folder, ref, cfg = build(seed)
    rj = json.load(open("/home/ubuntu/kaggle_sim/out/tsx-x14-%s/result.json" % seed.lower()))
    same_ov = {str(k): str(v) for k, v in rj["overrides"].items()} == {str(k): str(v) for k, v in cfg["overrides"].items()}
    log.info("check %s: ref=%s overrides_same_as_tsx=%s profile_same=%s folder=%s", seed, ref, same_ov,
             rj.get("profile") == cfg["profile"], folder)
    if not same_ov:
        log.info("tsx=%s", json.dumps(rj["overrides"], sort_keys=True)[:600])
        log.info("a3 =%s", json.dumps(cfg["overrides"], sort_keys=True)[:600])
    return same_ov


def push(seed):
    assert check(seed), "overrides khac run tham chieu -> DUNG"
    ks, folder, ref, cfg = build(seed)
    r = ks._api().kernels_push(folder)
    log.info("PUSHED %s -> %s", ref, getattr(r, "url", r))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("seed", nargs="?", default="A1")
    a = ap.parse_args()
    {"upload": lambda: upload(), "check": lambda: check(a.seed), "push": lambda: push(a.seed)}[a.cmd]()
