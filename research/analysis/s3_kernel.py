#!/usr/bin/env python3
"""S3_KERNEL — day kernel SIM cua vong Stage 3 len Kaggle (4 kenh: moc | V0 | V1 | V5).

Moi kenh = 1 kernel doC LAP, tu lam het trong 1 lan chay:
  1. chuan bi BINS (moc = bins 18 fold cua bundle; arm = s3_build_map.py s1a2x1 + 2 fold 2021 cua moc)
  2. dung lai funding.bin tu BINS (research/pipeline/x1/s3_funding.py — ban dich Python byte-faithful
     cua WfoDataset.buildFundingFromWfFiles + forwardFillToGrid; da qua cong tai lap local)
  3. dataset = market.bin/pred.bin NGUYEN BYTE cua bundle + funding.bin moi + manifest sua dung dong
  4. chay sim KEEPLEG0 (SIM_END_DATE=20251231) -> printDone.csv / sim.out
  5. tinh maxDD/UW tren chuoi equity MTM MOC PHUT (research/analysis/s3_intraday.py, can du lieu 1m)
  6. xoa file lon (funding.bin / bins / market.pred) truoc khi ket thuc

Xem docs/prereg/PREREG_STAGE3_SIM.md (chot TRUOC). KHONG push git. Khong Java/sim tren Oracle.

API cho agent khac:
    from research.analysis import s3_kernel as K
    ref = K.submit("V0"); K.wait([ref]); out = K.fetch("V0")
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import time

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks  # noqa: E402  (dung lai: USER, TICKER_DS, wait/fetch/status)

LOG = logging.getLogger(__name__)

BUNDLE = "sim-x1-2021-bundle"
STAGE2_KERNEL = "chuyendinh/g015p2-stage2-featvar-gpu"
SC_DS = "s3-s1-sc"                      # dataset chua pred_s1a2x1.parquet
MOC21_DS = "s3-moc-2021bins"            # dataset chua 2 fold 2021 cua moc (predict_wf_2021*.bin)
MOC_BINS_SHA = "407e2abab3053a39a51dcb9f331d063b3e67196bf608ae061aee444cd2841ca5"
END = "20251231"
JAR_SHA_WANT = "2c2f8aef78c98470fdc3b0d464edd7ec2c604a7589985b1f4211c1da05fcdca0"
KEEP_MD5 = "99e42b75cf1a2142f9cd14dc72e371ba"
MOC_FUND_MD5 = "8e57d900d5c54c744bfcaf5c9b27fc93"
MD5_MARKET = "4ab691c908fc545c26243e8328d7a0a6"
MD5_PRED = "5dd6bb4c3f98d89d58770005c0001526"
MOC_18 = ["20210701", "20211001"]      # 2 fold 2021 lay nguyen ban cua moc
ARMS = ("moc", "V0", "V1", "V5")
WORKDIR = "/home/ubuntu/kaggle_sim"
OUTDIR = "/home/ubuntu/kaggle_sim/out"

KERNEL_TEMPLATE = r'''"""S3 sim-runner kernel — SINH TU research/analysis/s3_kernel.py, KHONG sua tay."""
import glob
import hashlib
import gzip
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    stream=sys.stdout)
LOG = logging.getLogger("s3-runner")
CFG = json.loads(__CFG_JSON__)
# Helper (map/funding/intraday/jbin) NHUNG THANG vao script duoi dang base64 -> khong phu thuoc
# viec Kaggle co push file phu trong folder kernel hay khong.
import base64
HELPDIR = "/kaggle/working/helpers"
os.makedirs(HELPDIR, exist_ok=True)
for _nm, _b64 in json.loads(__HELPERS__).items():
    with open(os.path.join(HELPDIR, _nm), "wb") as _f:
        _f.write(base64.b64decode(_b64))
sys.path.insert(0, HELPDIR)
ARM = CFG["arm"]
IN, WORK = "/kaggle/input", "/kaggle/working"
TRADING_PREFIX = ("SIM_", "DCA_", "TS_", "SELECTOR_", "TIER_", "CONF_SIZE_", "TRAIL_",
                  "GATE_", "LIVE_", "SIZE_MULT", "MAX_CONCURRENT", "TIME_STOP_HOURS",
                  "ENABLE_SHORT", "ABLATION_MODE", "SHORT_")
TRADING_KEYS = ("NUMBER_ORDER_BUDGET", "HARD_STOP_LOSS_RATE", "DISABLE_PREDICT_SYMBOL",
                "CAPITAL_START", "SEL_BACKTEST_SET", "SEL_BACKTEST_HORIZON_IDX",
                "WFO_FUNDING_PRED_DIR")
H = _H = hashlib.sha256

def md5f(p, chunk=1 << 22):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def sha256f(p, chunk=1 << 22):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def find_glob(pat):
    m = sorted(glob.glob(IN + "/**/" + pat, recursive=True))
    return m


# ---------------- 0. dau vao ----------------
bundle = None
for c in find_glob("sim.jar"):              # bundle = thu muc co sim.jar + manifest.txt + market.bin
    d = os.path.dirname(c)
    if os.path.exists(os.path.join(d, "manifest.txt")) and os.path.exists(os.path.join(d, "market.bin")):
        bundle = d
        break
if bundle is None:
    LOG.error("MISSING bundle (can sim.jar + manifest.txt + market.bin)")
    sys.exit(1)
jar = os.path.join(bundle, "sim.jar")
JAR_SHA = sha256f(jar)
prof_base = os.path.join(bundle, "prof_" + CFG["profile"] + ".properties")
cfg_src = os.path.join(bundle, "config.properties")
exinfo = os.path.join(bundle, "exchange_info_pin.json")
for p in (prof_base, cfg_src, exinfo, os.path.join(bundle, "market.bin"),
          os.path.join(bundle, "pred.bin")):
    if not os.path.exists(p):
        LOG.error("MISSING %s", p)
        sys.exit(1)
sc_pq = find_glob("pred_s1a2x1.parquet")
sc_pq = sc_pq[0] if sc_pq else None
map_py = os.path.join(HELPDIR, "s3_build_map.py")
fund_py = os.path.join(HELPDIR, "s3_funding.py")
intra_py = os.path.join(HELPDIR, "s3_intraday.py")
for p in (map_py, fund_py, intra_py, os.path.join(HELPDIR, "jbin.py")):
    if not os.path.exists(p):
        LOG.error("MISSING helper %s", p)
        sys.exit(1)

# ticker -> /kaggle/working/kaggle_data_hpo (loader doc RELATIVE)
link = os.path.join(WORK, "kaggle_data_hpo")
os.makedirs(link, exist_ok=True)
tk = find_glob("ticker_2*.bin*")
for t in tk:
    dst = os.path.join(link, os.path.basename(t))
    if not os.path.lexists(dst):
        os.symlink(t, dst)
LOG.info("bundle=%s jar_sha=%s ticker=%d sc=%s", bundle, JAR_SHA[:16], len(tk), sc_pq)
SC_SHA = sha256f(sc_pq) if sc_pq else None
if sc_pq:
    LOG.info("SC_SHA256=%s", SC_SHA)
if len(tk) < CFG["ticker_min_days"]:
    LOG.error("CHI thay %d ticker, can >= %d", len(tk), CFG["ticker_min_days"])
    sys.exit(1)

# ---------------- 1. BINS (moi kenh: 16 fold 2022+ + 2 fold 2021 cua moc = 18) ----------------
c21 = None
for c in find_glob("predict_wf_20210701.bin"):
    if "/s3-moc-2021bins/" in c:
        c21 = c
        break
if c21 is None:
    LOG.error("MISSING predict_wf_20210701.bin (dataset s3-moc-2021bins)")
    sys.exit(1)
C21 = os.path.dirname(c21)
if len(glob.glob(C21 + "/predict_wf_2021*.bin")) != 2:
    LOG.error("s3-moc-2021bins phai co 2 file 2021")
    sys.exit(1)
BINS = WORK + "/bins_" + ARM
os.makedirs(BINS, exist_ok=True)
if ARM == "moc":
    for f in sorted(glob.glob(bundle + "/predict_wf_*.bin")) + sorted(glob.glob(C21 + "/predict_wf_*.bin")):
        shutil.copy(f, os.path.join(BINS, os.path.basename(f)))
else:
    arm_bins = None
    for c in find_glob("predict_wf_20220101.bin"):
        if "/stage2/%s/" % ARM in c.replace("\\", "/"):
            arm_bins = os.path.dirname(c)
            break
    if arm_bins is None or sc_pq is None:
        LOG.error("MISSING arm bins (stage2/%s) hoac pred_s1a2x1.parquet", ARM)
        sys.exit(1)
    env = dict(os.environ, G015_BINS_DIR=arm_bins, S1_SC=sc_pq, X1_CUTS=CFG["x1_cuts"])
    t0 = time.time()
    rc = subprocess.call([sys.executable, map_py, "s1a2x1", BINS], env=env)
    LOG.info("build_map rc=%s %.0fs -> %s", rc, time.time() - t0, BINS)
    if rc != 0:
        sys.exit(4)
    for f in sorted(glob.glob(C21 + "/predict_wf_2021*.bin")):
        shutil.copy(f, os.path.join(BINS, os.path.basename(f)))
bins_files = sorted(glob.glob(BINS + "/predict_wf_*.bin"))
if len(bins_files) != 18:
    LOG.error("BINS phai co 18 fold, co %d", len(bins_files))
    sys.exit(1)
bins_sha = hashlib.sha256()
for f in bins_files:
    with open(f, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 22), b""):
            bins_sha.update(b)
BINS_SHA = bins_sha.hexdigest()
LOG.info("BINS=%s files=%d sha256=%s", BINS, len(bins_files), BINS_SHA)

# ---------------- 2/3. DATASET ----------------
DS = WORK + "/ds_" + ARM
os.makedirs(DS, exist_ok=True)
for f in ("market.bin", "pred.bin"):
    shutil.copy(os.path.join(bundle, f), os.path.join(DS, f))
# guard: market/pred copy tu bundle phai DUNG md5 trong manifest (khong thi sim se throw, nhung bao som)
MD5_M = md5f(os.path.join(DS, "market.bin"))
MD5_P = md5f(os.path.join(DS, "pred.bin"))
LOG.info("market/pred copy md5=%s / %s (want %s / %s)", MD5_M[:12], MD5_P[:12],
         CFG["md5_market"][:12], CFG["md5_pred"][:12])
if MD5_M != CFG["md5_market"] or MD5_P != CFG["md5_pred"]:
    LOG.error("MARKET/PRED KHAC bundle manifest -> DUNG")
    sys.exit(6)
fjson = WORK + "/funding_%s.json" % ARM
t0 = time.time()
rc = subprocess.call([sys.executable, fund_py, "--bins", BINS, "--data", DS,
                      "--out", os.path.join(DS, "funding.bin"), "--json", fjson])
LOG.info("s3_funding rc=%s %.0fs", rc, time.time() - t0)
if rc != 0:
    sys.exit(5)
F = json.load(open(fjson))
base_mani = {}
order = []
for ln in open(os.path.join(bundle, "manifest.txt")):
    s = ln.rstrip("\n")
    k = s.split("=", 1)[0].strip()
    if k and "=" in s and not k.startswith("predictWf."):
        if k not in base_mani:
            order.append(k)
        base_mani[k] = s.split("=", 1)[1].strip()
upd = {"exportedAt": time.strftime("%a %b %d %H:%M:%S GMT+07:00 %Y"),
       "fundingPredDir": BINS, "binsSha256": F["binsSha256"],
       "foldCount": str(F["foldCount"]), "maxFoldSpanDays": str(F["maxFoldSpanDays"]),
       "fundingCount": str(F["fundingCount"]), "fundingRaw15mCount": str(F["fundingRaw15mCount"]),
       "md5_funding": F["md5_funding"], "md5_market": CFG["md5_market"],
       "md5_pred": CFG["md5_pred"], "s3Channel": ARM}
import datetime
mn = min(m["minTs"] for m in F["predictWf"])
upd["leakFreeFrom"] = datetime.datetime.utcfromtimestamp(mn / 1000 + 7 * 3600).strftime("%Y-%m-%d")
base_mani.update(upd)
with open(os.path.join(DS, "manifest.txt"), "w") as f:
    for k in order:
        f.write("%s=%s\n" % (k, base_mani[k]))
    for m in sorted(F["predictWf"], key=lambda x: x["name"]):
        span = (m["maxTs"] - m["minTs"]) // 86400000
        f.write("predictWf.%s=md5:%s;ts:%d..%d;span:%dd;rec:%d\n"
                % (m["name"], m["md5"], m["minTs"], m["maxTs"], span, m["nrec"]))
LOG.info("dataset ok: funding md5=%s count=%d fold=%d leakFreeFrom=%s",
         F["md5_funding"], F["fundingCount"], F["foldCount"], upd["leakFreeFrom"])

# ---------------- profile ----------------
pairs, order_p = {}, []
for ln in open(prof_base):
    s = ln.strip()
    if not s or s.startswith("#") or "=" not in s:
        continue
    k, v = s.split("=", 1)
    k = k.strip()
    if k not in pairs:
        order_p.append(k)
    pairs[k] = v.strip()
ov = dict(CFG["overrides"])
ov["WFO_FUNDING_PRED_DIR"] = BINS
for k, v in ov.items():
    if k not in pairs:
        order_p.append(k)
    pairs[k] = "true" if v is True else "false" if v is False else str(v)
prof = WORK + "/prof_run.properties"
with open(prof, "w") as f:
    for k in order_p:
        f.write("%s=%s\n" % (k, pairs[k]))

# ---------------- 4. SIM ----------------
RUN = WORK + "/run_" + ARM
os.makedirs(RUN + "/storage", exist_ok=True)
os.makedirs(RUN + "/logs", exist_ok=True)
shutil.copy(cfg_src, RUN + "/config.properties")
shutil.copy(cfg_src, WORK + "/config.properties")
if not os.path.lexists(os.path.join(RUN, "kaggle_data_hpo")):
    os.symlink(link, os.path.join(RUN, "kaggle_data_hpo"))
env = dict(os.environ)
for k in list(env):
    if k in TRADING_KEYS or k.startswith(TRADING_PREFIX):
        del env[k]
env.update({"WFO_DATA_DIR": DS, "WFO_SMART_CACHE": "1", "WFO_SET_PRED": "ai_pred_market_gate_wfo",
            "WFO_SEL_HORIZON_IDX": "0", "WFO_CODE_SHA": CFG["code_sha"],
            "SIM_END_DATE": CFG["sim_end_date"], "EXCHANGE_INFO_PATH": exinfo,
            "TRADING_PROFILE": prof})
LOGP = RUN + "/logs/sim.out"
t0 = time.time()
os.chdir(RUN)
try:
    with open(LOGP, "w") as lf:
        rc = subprocess.call(["java", "-Duser.timezone=Asia/Ho_Chi_Minh", "-Xmx" + CFG["xmx"],
                              "-cp", jar,
                              "com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss"],
                             env=env, stdout=lf, stderr=subprocess.STDOUT,
                             timeout=CFG["timeout_s"])
except subprocess.TimeoutExpired:
    rc = -9
secs = round(time.time() - t0, 1)
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")
last = first = None
phash, mapper_n = "", 0
for ln in open(LOGP, errors="ignore"):
    m = RX.search(ln)
    if m:
        v = (m.group(1), int(m.group(2)) + int(m.group(3)), int(m.group(2)))
        first = first or v
        last = v
    if not phash:
        mh = re.search(r"PROFILE_HASH=(\w+)", ln)
        if mh:
            phash = mh.group(1)
    if not mapper_n:
        mm = re.search(r"Loaded Symbol Mapper: (\d+) symbols", ln)
        if mm:
            mapper_n = int(mm.group(1))
pdone = os.path.join(RUN, "storage", "printDone.csv")
if not os.path.exists(pdone):
    for c in glob.glob(RUN + "/storage/*rint*one*"):
        pdone = c
n_trades = 0
if os.path.exists(pdone):
    with open(pdone, errors="ignore") as f:
        f.readline()
        n_trades = sum(1 for ln in f if ln.strip())
MD5 = md5f(pdone) if os.path.exists(pdone) else None
LOG.info("SIM rc=%s secs=%.0f mapper=%d n=%d eq=%s md5=%s", rc, secs, mapper_n, n_trades,
         last[1] if last else None, MD5)
if mapper_n < 800:
    LOG.error("SYMBOL_MAPPER_FAIL n=%d", mapper_n)
    sys.exit(2)
res = dict(arm=ARM, rc=rc, secs=secs, mapper=mapper_n, n_trades=n_trades,
           equity_final=last[1] if last else None, b_final=last[2] if last else None,
           date_first=first[0] if first else None, date_last=last[0] if last else None,
           md5_printdone=MD5, profile_hash=phash, jar_sha256=JAR_SHA,
           funding_md5=F["md5_funding"], funding_count=F["fundingCount"],
           bins_sha256=BINS_SHA, fold_count=F["foldCount"], sc_sha256=SC_SHA,
           md5_market=MD5_M, md5_pred=MD5_P,
           leak_free_from=upd["leakFreeFrom"], checks={}, intraday=None)
if ARM == "moc":
    res["checks"]["P1_md5"] = MD5 == CFG["keep_md5"]
    res["checks"]["P1_n"] = n_trades == 1085
    res["checks"]["P1_eq"] = (last is not None and last[1] == 103083)
    res["checks"]["P2_funding"] = F["md5_funding"] == CFG["moc_fund_md5"]
    res["checks"]["P2_bins_sha"] = BINS_SHA == CFG["moc_bins_sha"]
res["checks"]["jar_sha"] = JAR_SHA == CFG["jar_sha_want"]

# ---------------- 5. MTM MOC PHUT ----------------
ij = WORK + "/intraday_%s.json" % ARM
t0 = time.time()
rc2 = subprocess.call([sys.executable, intra_py, "--run", "%s=%s" % (ARM, RUN),
                       "--ticker", link, "--workers", str(CFG["workers"]),
                       "--json", ij])
LOG.info("intraday rc=%s %.0fs", rc2, time.time() - t0)
if rc2 == 0 and os.path.exists(ij):
    I = json.load(open(ij))
    res["intraday"] = dict(checks=I["checks"], stats=I["stats"][ARM],
                           day0=I["day0"], day1=I["day1"], secs=I["secs"])
with open(WORK + "/result.json", "w") as f:
    json.dump(res, f, indent=1)
if os.path.exists(LOGP):
    subprocess.call(["gzip", "-f", LOGP])

# ---------------- 6. don file lon ----------------
for p in (os.path.join(DS, "funding.bin"),):
    if os.path.exists(p):
        os.remove(p)
shutil.rmtree(BINS, ignore_errors=True)
shutil.rmtree(DS, ignore_errors=True)
for p in glob.glob(WORK + "/kaggle_data_hpo/*"):
    if os.path.islink(p):
        os.unlink(p)
du = subprocess.check_output(["du", "-sm", WORK]).decode().split()[0]
LOG.info("S3_DONE arm=%s eq=%s n=%s md5=%s checks=%s | work=%sMB",
         ARM, res["equity_final"], res["n_trades"], res["md5_printdone"],
         json.dumps(res["checks"]), du)
'''


def _cfg(arm):
    return {"arm": arm, "profile": "x1_gs_t170",
            "overrides": {"DCA_GRID_WEIGHTS": "1,1,1,1", "DCA_GRID_SCALE": 6.0},
            "sim_end_date": END, "xmx": "22g", "timeout_s": 7200,
            "code_sha": _head_sha(), "ticker_min_days": 1826, "workers": 4,
            "moc_2021": MOC_18, "keep_md5": KEEP_MD5, "moc_fund_md5": MOC_FUND_MD5,
            "moc_bins_sha": MOC_BINS_SHA,
            "md5_market": MD5_MARKET, "md5_pred": MD5_PRED, "jar_sha_want": JAR_SHA_WANT,
            "x1_cuts": "20220101 20220401 20220701 20221001 20230101 20230401 20230701 "
                       "20231001 20240101 20240401 20240701 20241001 20250101 20250401 "
                       "20250701 20251001"}


def _head_sha():
    import subprocess
    return subprocess.check_output(["git", "-C", "/home/ubuntu/src/BinanceFuturesJava",
                                    "rev-parse", "--short", "HEAD"]).decode().strip()


def _ref(arm):
    return "%s/%s-s3-%s" % (ks.USER, ks.KERNEL_PREFIX, ks.slug(arm))


def _helpers():
    """File phu (map/funding/intraday/jbin) copy tu repo vao folder kernel."""
    R = "/home/ubuntu/src/BinanceFuturesJava"
    return {os.path.join(R, "research/pipeline/x1/s3_build_map.py"): "s3_build_map.py",
            os.path.join(R, "research/pipeline/x1/s3_funding.py"): "s3_funding.py",
            os.path.join(R, "research/analysis/s3_intraday.py"): "s3_intraday.py",
            os.path.join(R, "research/analysis/jbin.py"): "jbin.py"}


def _helpers_b64():
    """Noi dung helper -> base64 (nhung vao run.py)."""
    import base64
    out = {}
    for src, nm in _helpers().items():
        with open(src, "rb") as f:
            out[nm] = base64.b64encode(f.read()).decode()
    return out


def submit(arm, push=True):
    assert arm in ARMS, arm
    ref = _ref(arm)
    folder = os.path.join(WORKDIR, "s3-" + ks.slug(arm))
    os.makedirs(folder, exist_ok=True)
    for src, nm in _helpers().items():
        with open(src) as f:
            body = f.read()
        with open(os.path.join(folder, nm), "w") as f:
            f.write(body)
    code = (KERNEL_TEMPLATE.replace("__CFG_JSON__", repr(json.dumps(_cfg(arm))))
            .replace("__HELPERS__", repr(json.dumps(_helpers_b64()))))
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(code)
    meta = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py",
            "language": "python", "kernel_type": "script", "is_private": True,
            "enable_gpu": False, "enable_internet": True,
            "dataset_sources": [ks.USER + "/" + BUNDLE, ks.USER + "/" + SC_DS,
                                ks.USER + "/" + MOC21_DS] + ks.TICKER_DS,
            "competition_sources": [], "kernel_sources": [STAGE2_KERNEL]}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    if push:
        r = ks._api().kernels_push(folder)
        LOG.info("push %s -> %s", ref, getattr(r, "url", r))
    return ref


def wait(refs, poll_s=60, timeout_s=6 * 3600):
    return ks.wait(refs, poll_s=poll_s, timeout_s=timeout_s)


def fetch(arm, out_dir=None):
    dest = out_dir or os.path.join(OUTDIR, "s3-" + arm)
    os.makedirs(dest, exist_ok=True)
    ks._api().kernels_output(_ref(arm), path=dest, force=True, quiet=True)
    hits = glob_free(dest, "result.json")
    res = json.load(open(hits[0])) if hits else None
    return {"ref": _ref(arm), "dir": dest, "result": res}


def glob_free(root, name):
    out = []
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            if f == name:
                out.append(os.path.join(dp, f))
    return sorted(out)


def _cli():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["submit", "wait", "fetch", "all"])
    ap.add_argument("--arm", action="append", default=None)
    a = ap.parse_args()
    arms = a.arm or list(ARMS)
    if a.cmd == "submit":
        for x in arms:
            submit(x)
    elif a.cmd == "wait":
        LOG.info("%s", wait([_ref(x) for x in arms]))
    elif a.cmd == "fetch":
        for x in arms:
            LOG.info("%s", json.dumps(fetch(x), indent=1))
    else:
        refs = [submit(x) for x in arms]
        LOG.info("%s", wait(refs))
        for x in arms:
            LOG.info("%s", json.dumps(fetch(x)["result"], indent=1))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    _cli()
