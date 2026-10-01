"""kaggle_bd_chain - HARNESS Kaggle cho DAY CHUYEN BD (buoc 1-3 cua PREREG_BD_CHAIN).

Mo khoa blocker (B) cua `docs/result/RESULT_BD_CHAIN.md` §3: buoc 1-3 cua day chuyen doi
`rateDown15MAvg` theo ty le universe `f` (market.bin -> gate store -> pred.bin -> bins) truoc
day KHONG co duong chay tren Kaggle (deu la job Java doc Aerospike). Module nay dung lai harness
do, CHI dung du lieu co san tren Kaggle (ticker file) + sim jar, KHONG can Aerospike.

Kien truc (moi stage = 1 Kaggle kernel; xem RESULT_BD_CHAIN §7):
  A. market-bin   : ticker file -> MarketDataInlineGenerator -> market.bin (Java, SIM_BD_FRACTION)
  B. gate-store   : PATCH cot rate-derived (momentum1M/momentum15M/momentumAcceleration) cua
                    gate store tinh bang market.bin moi (Python thuan — xem `patch_gate_store`)
  C. gate-train   : run_cycle WFO tren store da patch -> p15 -> pred.bin
  D. s1-bins      : s1_rank + build_map -> predict_wf_*.bin
  E. sim          : tools/kaggle_sim.py voi bundle moi

API:
    from tools import kaggle_bd_chain as kb
    ref = kb.submit_market("f000", 0.0)     # Kernel A, f=0 (parity)
    kb.wait([ref]); out = kb.fetch_market("f000")
    out["market_bin"]  # duong dan file da keo ve
    out["result"]      # {"md5","size","rows","first_ts","last_ts",...}
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import struct
import time

LOG = logging.getLogger(__name__)

USER = "chuyendinh"
KERNEL_PREFIX = "bdchain"
JAR_DS = "bdchain-jar"                      # dataset moi: sim.jar (HEAD) + config.properties
BUNDLE_DS = "sim-x1-2021-bundle"            # bundle du lieu chinh (market/pred/funding/bins)
TICKER_DS = [USER + "/wfo-ticker-2021",
             USER + "/wfo-ticker-2022", USER + "/wfo-ticker-2023",
             USER + "/wfo-ticker-2024h1", USER + "/wfo-ticker-2024h2",
             USER + "/wfo-ticker-2025h1", USER + "/wfo-ticker-2025h2"]
TICKER_MIN_DAYS = 1826
MAX_CONCURRENT = 5
WORKDIR = os.environ.get("KAGGLE_BDCHAIN_WORKDIR", "/home/ubuntu/kaggle_bdchain")
OUTDIR = os.environ.get("KAGGLE_BDCHAIN_OUTDIR", "/home/ubuntu/kaggle_bdchain/out")
DEFAULT_XMX = "22g"
TERMINAL = ("COMPLETE", "ERROR", "CANCEL_ACKNOWLEDGED", "CANCELLED")

_API = None


def _api():
    global _API
    if _API is None:
        from kaggle.api.kaggle_api_extended import KaggleApi
        _API = KaggleApi()
        _API.authenticate()
    return _API


def slug(tag: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(tag).lower()).strip("-")
    if not s:
        raise ValueError("tag rong sau khi slug hoa: %r" % tag)
    return s


def kernel_ref(tag: str) -> str:
    return "%s/%s-%s" % (USER, KERNEL_PREFIX, slug(tag))


def _status(ref: str) -> str:
    r = _api().kernels_status(ref)
    st = r.get("status") if isinstance(r, dict) else getattr(r, "status", None)
    return str(st).split(".")[-1].upper()


def free_slots() -> int:
    used = 0
    for k in _api().kernels_list(mine=True, page_size=50):
        try:
            if _status(k.ref) in ("RUNNING", "QUEUED"):
                used += 1
        except Exception:
            continue
    return max(0, MAX_CONCURRENT - used)


# ============================================================================ #
# KERNEL A — market.bin tu ticker file
# ============================================================================ #
KERNEL_A = r'''"""BD-CHAIN Kernel A — market.bin tu ticker file (SINH TU tools/kaggle_bd_chain.py)."""
import glob, hashlib, json, logging, os, struct, subprocess, sys, time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    stream=sys.stdout)
LOG = logging.getLogger("bdchain-A")
CFG = json.loads(__CFG_JSON__)
IN, WORK = "/kaggle/input", "/kaggle/working"


def f1(pat):
    m = sorted(glob.glob(pat, recursive=True))
    if not m:
        LOG.error("MISSING %s", pat); sys.exit(1)
    return m[0]


jar = f1(IN + "/**/sim.jar")
cfgp = f1(IN + "/**/config.properties")
os.makedirs(WORK + "/storage", exist_ok=True)
os.makedirs(WORK + "/logs", exist_ok=True)
os.chdir(WORK)
import shutil
shutil.copy(cfgp, WORK + "/config.properties")

# ticker: loader doc RELATIVE "kaggle_data_hpo/" tu CWD
link = os.path.join(WORK, "kaggle_data_hpo")
os.makedirs(link, exist_ok=True)
tk = sorted(glob.glob(IN + "/**/ticker_2*.bin*", recursive=True))
for t in tk:
    dst = os.path.join(link, os.path.basename(t))
    if not os.path.lexists(dst):
        os.symlink(t, dst)
LOG.info("jar=%s ticker=%d bd_fraction=%s range=%s..%s", jar, len(tk), CFG["bd_fraction"],
         CFG["start"], CFG["end"])
if len(tk) < CFG["ticker_min_days"]:
    LOG.error("chi thay %d ticker, can >= %d", len(tk), CFG["ticker_min_days"]); sys.exit(1)

env = dict(os.environ)
env["SIM_BD_FRACTION"] = str(CFG["bd_fraction"])     # khong TRADING_PROFILE => Cfg doc env
outbin = WORK + "/market.bin"
cmd = ["java", "-Duser.timezone=Asia/Ho_Chi_Minh", "-Xmx" + CFG["xmx"], "-cp", jar,
       "com.binance.chuyennd.ai_ml.wfo.framework.ExportMarketBinFromTicker",
       CFG["start"], CFG["end"], outbin]
LOG.info("CMD %s", " ".join(cmd))
t0 = time.time()
with open(WORK + "/logs/kernelA.out", "w") as lf:
    rc = subprocess.call(cmd, env=env, stdout=lf, stderr=subprocess.STDOUT)
secs = round(time.time() - t0, 1)
if rc != 0 or not os.path.exists(outbin):
    LOG.error("KERNEL_A_FAIL rc=%s exists=%s", rc, os.path.exists(outbin)); sys.exit(1)

h = hashlib.md5(); n = os.path.getsize(outbin)
with open(outbin, "rb") as f:
    for b in iter(lambda: f.read(1 << 20), b""):
        h.update(b)
with open(outbin, "rb") as f:
    cnt = struct.unpack(">i", f.read(4))[0]
    first = struct.unpack(">q", f.read(8))[0]
    f.seek(4 + (cnt - 1) * 20)
    last = struct.unpack(">q", f.read(8))[0]
res = {"tag": CFG["tag"], "bd_fraction": CFG["bd_fraction"], "rc": rc, "secs": secs,
       "md5": h.hexdigest(), "size": n, "rows": cnt, "first_ts": first, "last_ts": last,
       "ok": cnt > 0}
with open(WORK + "/result.json", "w") as f:
    json.dump(res, f, indent=1)
LOG.info("RESULT %s", json.dumps(res))

import gzip
with open(outbin, "rb") as fi, gzip.open(WORK + "/market.bin.gz", "wb", 6) as fo:
    shutil.copyfileobj(fi, fo, 1 << 20)
LOG.info("KERNEL_A_DONE rows=%s md5=%s secs=%s", cnt, h.hexdigest(), secs)
sys.exit(0)
'''


def submit_market(tag, bd_fraction, *, start="20210101", end="20251231", jar_ds=None,
                  ticker_min_days=TICKER_MIN_DAYS, xmx=DEFAULT_XMX, code_sha="head",
                  timeout_s=10800, enable_internet=False, push=True) -> str:
    """Day Kernel A (sinh market.bin) len Kaggle. Tra ve kernel ref."""
    ref = kernel_ref(tag)
    folder = os.path.join(WORKDIR, slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": str(tag), "bd_fraction": float(bd_fraction), "start": start, "end": end,
           "xmx": xmx, "ticker_min_days": int(ticker_min_days), "code_sha": code_sha}
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(KERNEL_A.replace("__CFG_JSON__", repr(json.dumps(cfg))))
    meta = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py",
            "language": "python", "kernel_type": "script", "is_private": True,
            "enable_gpu": False, "enable_internet": enable_internet,
            "dataset_sources": [(USER + "/" + (jar_ds or JAR_DS))] + TICKER_DS,
            "competition_sources": [], "kernel_sources": []}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    if push:
        r = _api().kernels_push(folder)
        LOG.info("push %s -> %s", ref, getattr(r, "url", r))
    return ref


def wait(refs, poll_s=60, timeout_s=13 * 3600):
    refs = list(refs)
    out, t0 = {}, time.time()
    while len(out) < len(refs):
        for ref in refs:
            if ref in out:
                continue
            try:
                st = _status(ref)
            except Exception as e:
                LOG.warning("status %s loi: %s", ref, e)
                continue
            if st in TERMINAL:
                out[ref] = st
                LOG.info("%s -> %s", ref, st)
        if len(out) == len(refs):
            break
        if time.time() - t0 > timeout_s:
            for ref in refs:
                out.setdefault(ref, "TIMEOUT")
            break
        time.sleep(poll_s)
    return out


def fetch_market(tag, out_dir=None):
    ref = kernel_ref(tag)
    dest = out_dir or os.path.join(OUTDIR, slug(tag))
    os.makedirs(dest, exist_ok=True)
    _api().kernels_output(ref, path=dest, force=True, quiet=True)
    import glob as _g
    import gzip

    def _one(pat):
        m = sorted(_g.glob(os.path.join(dest, "**", pat), recursive=True))
        return m[0] if m else None

    gzb = _one("market.bin.gz")
    binp = _one("market.bin")
    if gzb and not binp:
        binp = gzb[:-3]
        with gzip.open(gzb, "rb") as fi, open(binp, "wb") as fo:
            fo.write(fi.read())
    rj = _one("result.json")
    res = json.load(open(rj)) if rj else None
    return {"ref": ref, "dir": dest, "market_bin": binp, "result": res,
            "log": _one("kernelA.out"), "klog": _one("%s.log" % slug(tag))}


# ============================================================================ #
# KERNEL B — PATCH gate store: cot rate-derived theo market.bin moi
# ============================================================================ #
# Chi 3 cot phu thuoc market-rate (ComprehensiveMarketFeatureExtractor.java:93-100):
#   momentum1M = rateDownAvg (=market.down) ; momentum15M = rateDown15MAvg (=market.down15)
#   momentumAcceleration = momentum5M - momentum15M   (momentum5M = return BTC, KHONG doi)
# Cac cot khac (momentum5M/1H/4H/24H, volatility*, breadth*, rsi*, basket*, time*) la ham cua
# gia tung coin / lich => KHONG doi theo f. => patch du 3 cot nay.
KERNEL_B = r'''"""BD-CHAIN Kernel B — patch cot rate-derived cua gate store bang market.bin (SINH TU harness)."""
import glob, gzip, json, logging, os, struct, sys, time
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
LOG = logging.getLogger("bdchain-B")
CFG = json.loads(__CFG_JSON__)
IN, WORK = "/kaggle/input", "/kaggle/working"


def f1(pat):
    m = sorted(glob.glob(pat, recursive=True))
    if not m:
        LOG.error("MISSING %s", pat); sys.exit(1)
    return m[0]


mk = CFG.get("market_ds") or ""
_c = sorted(glob.glob(IN + "/**/market.bin", recursive=True))
if mk:
    _c = [c for c in _c if ("/" + mk + "/") in c]
if not _c:
    LOG.error("MISSING market.bin (market_ds=%r)", mk); sys.exit(1)
mb = _c[0]
LOG.info("market.bin=%s", mb)
rate = {}
with open(mb, "rb") as f:
    n = struct.unpack(">i", f.read(4))[0]
    buf = f.read(n * 20)
for i in range(n):
    o = i * 20
    ts = struct.unpack_from(">q", buf, o)[0]
    d, u, d15 = struct.unpack_from(">fff", buf, o + 8)
    rate[ts] = (d, d15)
LOG.info("market.bin rows=%d", len(rate))

store = f1(IN + "/**/" + CFG["store_file"])
LOG.info("store=%s", store)
OUT = WORK + "/gate_store_patched.csv.gz"
n_rows = n_hit = n_miss = 0
with gzip.open(store, "rt") as fi, gzip.open(OUT, "wt", 6) as fo:
    hdr = fi.readline().rstrip("\n").split(",")
    fo.write(",".join(hdr) + "\n")
    i_ts = hdr.index("timestamp"); i_m1 = hdr.index("momentum1M")
    i_m5 = hdr.index("momentum5M"); i_m15 = hdr.index("momentum15M")
    i_mac = hdr.index("momentumAcceleration")
    for line in fi:
        p = line.rstrip("\n").split(",")
        ts = int(p[i_ts])
        r = rate.get(ts)
        if r is None:
            n_miss += 1
        else:
            n_hit += 1
            p[i_m1] = "%.8f" % r[0]
            p[i_m15] = "%.8f" % r[1]
            p[i_mac] = "%.8f" % (float(p[i_m5]) - r[1])
        fo.write(",".join(p) + "\n")
        n_rows += 1
        if n_rows % 500000 == 0:
            LOG.info("... rows=%d hit=%d", n_rows, n_hit)
res = {"tag": CFG["tag"], "store": os.path.basename(store), "out": os.path.basename(OUT),
       "rows": n_rows, "hit": n_hit, "miss": n_miss, "ok": n_rows > 0}
with open(WORK + "/result.json", "w") as f:
    json.dump(res, f, indent=1)
LOG.info("RESULT %s", json.dumps(res))
LOG.info("KERNEL_B_DONE rows=%d hit=%d", n_rows, n_hit)
sys.exit(0)
'''

STORE_DS = "bdchain-gate-store"
STORE_FILE = "gate_dataset_full.csv.gz"


def stage_store_dataset(src="/home/ubuntu/claudedata/gate_dataset_full.csv.gz",
                        stage_dir="/home/ubuntu/bdchain_store"):
    """Stage + push gate store CSV (356MB) thanh dataset rieng (KHONG vao git)."""
    import shutil
    os.makedirs(stage_dir, exist_ok=True)
    dst = os.path.join(stage_dir, STORE_FILE)
    if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
        shutil.copy(src, dst)
    meta = {"title": STORE_DS, "id": USER + "/" + STORE_DS, "licenses": [{"name": "unknown"}]}
    with open(os.path.join(stage_dir, "dataset-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    api = _api()
    try:
        api.dataset_create_new(folder=stage_dir, public=False, dir_mode="skip")
        LOG.info("dataset_create_new %s OK", STORE_DS)
    except Exception as e:
        LOG.info("create_new loi (%s) -> create_version", e)
        api.dataset_create_version(folder=stage_dir, version_notes="gate store", dir_mode="skip")
    return USER + "/" + STORE_DS


def stage_market_dataset(market_bin_src, ds_name, stage_dir=None):
    """Stage 1 market.bin (51MB) thanh dataset rieng cho tung f."""
    import shutil
    stage_dir = stage_dir or os.path.join(WORKDIR, "ds_" + slug(ds_name))
    os.makedirs(stage_dir, exist_ok=True)
    shutil.copy(market_bin_src, os.path.join(stage_dir, "market.bin"))
    meta = {"title": ds_name, "id": USER + "/" + ds_name, "licenses": [{"name": "unknown"}]}
    with open(os.path.join(stage_dir, "dataset-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    api = _api()
    try:
        api.dataset_create_new(folder=stage_dir, public=False, dir_mode="skip")
    except Exception as e:
        LOG.info("create_new loi (%s) -> create_version", e)
        api.dataset_create_version(folder=stage_dir, version_notes="market.bin", dir_mode="skip")
    return USER + "/" + ds_name


def submit_patch_store(tag, *, market_ds, store_ds=STORE_DS, code_sha="head", push=True) -> str:
    ref = kernel_ref(tag)
    folder = os.path.join(WORKDIR, slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": str(tag), "market_ds": market_ds, "store_file": STORE_FILE, "code_sha": code_sha}
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(KERNEL_B.replace("__CFG_JSON__", repr(json.dumps(cfg))))
    meta = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py",
            "language": "python", "kernel_type": "script", "is_private": True,
            "enable_gpu": False, "enable_internet": False,
            "dataset_sources": [USER + "/" + store_ds, USER + "/" + market_ds],
            "competition_sources": [], "kernel_sources": []}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    if push:
        r = _api().kernels_push(folder)
        LOG.info("push %s -> %s", ref, getattr(r, "url", r))
    return ref


# ============================================================================ #
# STAGE JAR — dataset sim.jar (HEAD) + config.properties
# ============================================================================ #
def stage_jar_dataset(jar_path="target/binance-java-sdk-1.2.4.jar",
                      config_path="/home/ubuntu/simbundle_x1_t170/config.properties",
                      stage_dir="/home/ubuntu/bdchain_jar", notes="BD-CHAIN harness jar"):
    """Stage + (tao|cap nhat) dataset `chuyendinh/bdchain-jar`. KHONG push file du lieu vao git."""
    import shutil
    os.makedirs(stage_dir, exist_ok=True)
    shutil.copy(jar_path, os.path.join(stage_dir, "sim.jar"))
    shutil.copy(config_path, os.path.join(stage_dir, "config.properties"))
    meta = {"title": JAR_DS, "id": USER + "/" + JAR_DS, "licenses": [{"name": "unknown"}]}
    with open(os.path.join(stage_dir, "dataset-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    api = _api()
    try:
        api.dataset_create_new(folder=stage_dir, public=False, dir_mode="skip")
        LOG.info("dataset_create_new %s OK", JAR_DS)
    except Exception as e:
        LOG.info("create_new loi (%s) -> thu create_version", e)
        api.dataset_create_version(folder=stage_dir, version_notes=notes, dir_mode="skip")
    return USER + "/" + JAR_DS


def _cli():
    import argparse
    ap = argparse.ArgumentParser(description="BD-CHAIN harness (Kaggle)")
    ap.add_argument("cmd", choices=["slots", "stage-jar", "market", "wait", "fetch"])
    ap.add_argument("--tag")
    ap.add_argument("--f", type=float, default=0.0)
    ap.add_argument("--start", default="20210101")
    ap.add_argument("--end", default="20251231")
    ap.add_argument("--jar-path", default="target/binance-java-sdk-1.2.4.jar")
    ap.add_argument("--config", default="/home/ubuntu/simbundle_x1_t170/config.properties")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if a.cmd == "slots":
        LOG.info("free_slots=%d", free_slots())
    elif a.cmd == "stage-jar":
        LOG.info("%s", stage_jar_dataset(a.jar_path, a.config))
    elif a.cmd == "market":
        LOG.info("ref=%s", submit_market(a.tag, a.f, start=a.start, end=a.end))
    elif a.cmd == "wait":
        LOG.info("%s", wait([kernel_ref(a.tag)]))
    else:
        LOG.info("%s", json.dumps(fetch_market(a.tag), indent=1))


if __name__ == "__main__":
    _cli()
