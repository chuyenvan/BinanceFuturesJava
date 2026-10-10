#!/usr/bin/env python3
"""HO3b Kernel A (ADDENDUM-4 §4b, 62c0cd67): market.bin tu ticker file bang Java GOC ExportMarketBinFromTicker
(MarketDataInlineGenerator) trong jar b7c89f09 (dataset sim-jar-nsel), config = config.properties bundle sim-ho26a-bundle
(ban copy AEROSPIKE_HOST->127.0.0.1). Mau tools/kaggle_bd_chain.py KERNEL_A.
Usage: ho3b_kernel_a.py submit <tag> <start> <end> <ticker_ds,...> <min_tickers> | status <tag> | fetch <tag>"""
import json, logging, os, re, subprocess, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho3b_ka")
USER = "chuyendinh"
WD = "/home/ubuntu/claude_master/1003/ho3b/kaggle"
JAR_DS, CFG_DS = "sim-jar-nsel", "sim-ho26a-bundle"
JAR_SHA = "b7c89f097241763bb240c24b411a66531b41dad12b1716f13237537386de62c2"
KA = r'''"""HO3b Kernel A — market.bin tu ticker (Java goc ExportMarketBinFromTicker). SINH TU ho3b_kernel_a.py"""
import glob, gzip, hashlib, json, logging, os, re, shutil, struct, subprocess, sys, time
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
LOG = logging.getLogger("ho3b-A")
CFG = json.loads(__CFG_JSON__)
IN, WORK = "/kaggle/input", "/kaggle/working"
def pick(name, ds):
    c = [p for p in sorted(glob.glob(IN + "/**/" + name, recursive=True)) if ("/" + ds + "/") in p]
    if not c:
        LOG.error("MISSING %s trong %s", name, ds); sys.exit(1)
    return c[0]
jar = pick("sim.jar", CFG["jar_ds"])
h = hashlib.sha256(open(jar, "rb").read()).hexdigest()
LOG.info("JAR_SHA256=%s", h)
if h != CFG["jar_sha"]:
    LOG.error("JAR_SHA_MISMATCH"); sys.exit(1)
cfgp = pick("config.properties", CFG["cfg_ds"])
os.makedirs(WORK + "/logs", exist_ok=True)
os.chdir(WORK)
raw = open(cfgp, "rb").read().splitlines(True)
out, nrep = [], 0
for ln in raw:
    if re.match(rb"\s*AEROSPIKE_HOST\s*=", ln):
        ln = b"AEROSPIKE_HOST=127.0.0.1\n"; nrep += 1
    out.append(ln)
if nrep != 1:
    LOG.error("NOWRITE242_FAIL %d", nrep); sys.exit(2)
open(WORK + "/config.properties", "wb").write(b"".join(out))
LOG.info("NOWRITE242 AEROSPIKE_HOST -> 127.0.0.1 (ban copy)")
link = os.path.join(WORK, "kaggle_data_hpo")
os.makedirs(link, exist_ok=True)
tk = [p for p in sorted(glob.glob(IN + "/**/ticker_2*.bin*", recursive=True))
      if any(("/" + d + "/") in p for d in CFG["ticker_ds"])]
for t in tk:
    dst = os.path.join(link, os.path.basename(t))
    if not os.path.lexists(dst):
        os.symlink(t, dst)
LOG.info("ticker=%d range=%s..%s", len(tk), CFG["start"], CFG["end"])
if len(tk) < CFG["min_tickers"]:
    LOG.error("chi %d ticker < %d", len(tk), CFG["min_tickers"]); sys.exit(1)
outbin = WORK + "/market.bin"
cmd = ["java", "-Duser.timezone=Asia/Ho_Chi_Minh", "-Xmx20g", "-cp", jar,
       "com.binance.chuyennd.ai_ml.wfo.framework.ExportMarketBinFromTicker", CFG["start"], CFG["end"], outbin]
LOG.info("CMD %s", " ".join(cmd))
t0 = time.time()
with open(WORK + "/logs/kernelA.out", "w") as lf:
    rc = subprocess.call(cmd, stdout=lf, stderr=subprocess.STDOUT)
if rc != 0 or not os.path.exists(outbin):
    LOG.error("KERNEL_A_FAIL rc=%s", rc); sys.exit(1)
with open(outbin, "rb") as f:
    cnt = struct.unpack(">i", f.read(4))[0]
    first = struct.unpack(">q", f.read(8))[0]
    f.seek(4 + (cnt - 1) * 20); last = struct.unpack(">q", f.read(8))[0]
res = dict(tag=CFG["tag"], rc=rc, secs=round(time.time() - t0, 1), rows=cnt, first_ts=first, last_ts=last,
           md5=hashlib.md5(open(outbin, "rb").read()).hexdigest(), size=os.path.getsize(outbin), jar_sha256=h,
           report=[l.strip()[-200:] for l in open(WORK + "/logs/kernelA.out", errors="ignore") if "MarketData gen" in l][-1:])
json.dump(res, open(WORK + "/result.json", "w"), indent=1)
for p in glob.glob(link + "/*"):
    os.remove(p)
os.rmdir(link)
LOG.info("KERNEL_A_DONE %s", json.dumps(res))
'''


def api():
    from kaggle.api.kaggle_api_extended import KaggleApi
    a = KaggleApi()
    a.authenticate()
    return a


def slug(tag):
    return re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")


def submit(tag, start, end, tds, mint):
    ref = "%s/%s" % (USER, slug(tag))
    fol = os.path.join(WD, slug(tag))
    os.makedirs(fol, exist_ok=True)
    cfg = dict(tag=tag, start=start, end=end, ticker_ds=tds, min_tickers=int(mint), jar_ds=JAR_DS, jar_sha=JAR_SHA,
               cfg_ds=CFG_DS)
    open(os.path.join(fol, "run.py"), "w").write(KA.replace("__CFG_JSON__", repr(json.dumps(cfg))))
    md = {"id": ref, "title": slug(tag), "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": False,
          "dataset_sources": [USER + "/" + JAR_DS, USER + "/" + CFG_DS] + [USER + "/" + d for d in tds],
          "competition_sources": [], "kernel_sources": []}
    json.dump(md, open(os.path.join(fol, "kernel-metadata.json"), "w"), indent=1)
    r = api().kernels_push(fol)
    log.info("PUSHED %s %s", ref, getattr(r, "url", r))


def status(tag):
    r = api().kernels_status("%s/%s" % (USER, slug(tag)))
    log.info("STATUS %s %s", tag, r.get("status") if isinstance(r, dict) else getattr(r, "status", r))


def fetch(tag):
    out = os.path.join(WD, "out", slug(tag))
    os.makedirs(out, exist_ok=True)
    api().kernels_output("%s/%s" % (USER, slug(tag)), out)
    log.info("FETCHED -> %s: %s", out, os.listdir(out))


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "submit":
        submit(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5].split(","), sys.argv[6])
    elif c == "status":
        status(sys.argv[2])
    elif c == "fetch":
        fetch(sys.argv[2])
