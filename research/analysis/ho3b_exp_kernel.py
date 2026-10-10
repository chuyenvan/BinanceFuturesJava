#!/usr/bin/env python3
"""HO3b cong 5: kernel Kaggle chay EXPORTER JAVA GOC (jar b7c89f09) tren Aerospike CE 7.2 RIENG trong kernel (127.0.0.1:3222),
nap: kline_1m_opt (Java IngestTickerFileToAerospike tu ticker file), market_data_object (tu market.bin), funding_data /
symbol_mapper / symbol_lifecycle (pickle ban sao). KHONG cham Aerospike Oracle/242 (config: moi host -> 127.0.0.1).
Usage: ho3b_exp_kernel.py submit <cfg.json> | status <tag> | fetch <tag>"""
import json, logging, os, re, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho3b_exp")
USER = "chuyendinh"
WD = "/home/ubuntu/claude_master/1003/ho3b/kaggle"
KX = r'''"""HO3b exporter kernel — SINH TU ho3b_exp_kernel.py"""
import glob, gzip, hashlib, json, logging, os, pickle, re, shutil, socket, struct, subprocess, sys, time, datetime
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
LOG = logging.getLogger("ho3b-X")
CFG = json.loads(__CFG_JSON__)
IN, WORK = "/kaggle/input", "/kaggle/working"
OUTD = WORK + "/out"
os.makedirs(OUTD, exist_ok=True); os.makedirs(WORK + "/logs", exist_ok=True)
def pick(name, ds):
    c = [p for p in sorted(glob.glob(IN + "/**/" + name, recursive=True)) if ("/" + ds + "/") in p]
    if not c:
        LOG.error("MISSING %s trong %s", name, ds); sys.exit(1)
    return c[0]
def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()
jar = pick("sim.jar", CFG["jar_ds"])
JSHA = hashlib.sha256(open(jar, "rb").read()).hexdigest()
if JSHA != CFG["jar_sha"]:
    LOG.error("JAR_SHA_MISMATCH %s", JSHA); sys.exit(1)
# config exporter: moi host Aerospike -> 127.0.0.1 (khong the cham Oracle/242)
raw = open(pick("config.properties", CFG["cfg_ds"])).read().splitlines()
ov = dict(CFG["cfg_override"])
ov.update({"AEROSPIKE_HOST": "127.0.0.1", "AEROSPIKE_HOST_226": "127.0.0.1", "AEROSPIKE_PORT_226": "3222",
           "AEROSPIKE_PORT": "3222", "AEROSPIKE_READ_CLUSTER": "226"})
seen, outl = set(), []
for ln in raw:
    m = re.match(r"\s*([A-Z0-9_]+)\s*=", ln)
    if m and m.group(1) in ov:
        ln = "%s=%s" % (m.group(1), ov[m.group(1)]); seen.add(m.group(1))
    outl.append(ln)
for k, v in ov.items():
    if k not in seen:
        outl.append("%s=%s" % (k, v))
open(WORK + "/config.properties", "w").write("\n".join(outl) + "\n")
hosts = [l for l in outl if re.match(r"\s*AEROSPIKE_HOST", l)]
LOG.info("CONFIG hosts=%s", hosts)
if any("127.0.0.1" not in h for h in hosts):
    LOG.error("NOWRITE_FAIL host khac localhost"); sys.exit(2)
os.chdir(WORK)
# ---- Aerospike CE rieng trong kernel ----
_osr = open("/etc/os-release").read()
_vid = "24.04" if 'VERSION_ID="24' in _osr else "22.04"
LOG.info("OS %s", [l for l in _osr.splitlines() if l.startswith(("PRETTY_NAME", "VERSION_ID"))])
deb = pick("aerospike-server-community_7.2.0.6-1ubuntu%s_amd64.deb" % _vid, CFG["as_ds"])
subprocess.check_call(["dpkg", "-x", deb, "/opt/as"])
asd = [p for p in glob.glob("/opt/as/**/asd", recursive=True) if os.path.isfile(p)][0]
os.makedirs("/tmp/aswork/smd", exist_ok=True); os.makedirs("/tmp/aswork/usr/udf/lua", exist_ok=True)
for _d in ("/opt/aerospike/usr/udf/lua", "/opt/aerospike/smd", "/opt/aerospike/sys/udf/lua"):
    os.makedirs(_d, exist_ok=True)
conf = """service {
    cluster-name ho3b
    proto-fd-max 15000
    work-directory /tmp/aswork
}
logging {
    file /tmp/aswork/asd.log {
        context any info
    }
    console {
        context any info
    }
}
network {
    service {
        address 127.0.0.1
        port 3222
    }
    heartbeat {
        mode mesh
        address 127.0.0.1
        port 3002
    }
    fabric {
        address 127.0.0.1
        port 3001
    }
}
namespace test {
    replication-factor 1
    default-ttl 0
    storage-engine memory {
        data-size %dG
    }
}
""" % CFG.get("as_mem_gb", 12)
open("/tmp/aswork/as.conf", "w").write(conf)
asp = subprocess.Popen([asd, "--config-file", "/tmp/aswork/as.conf", "--foreground"], stdout=open(WORK + "/logs/asd.out", "w"),
                       stderr=subprocess.STDOUT)
ok = False
for i in range(60):
    try:
        with socket.create_connection(("127.0.0.1", 3222), timeout=2):
            ok = True; break
    except Exception:
        time.sleep(2)
LOG.info("ASD up=%s pid=%s", ok, asp.pid)
if not ok:
    LOG.error("ASD_FAIL rc=%s out=%s", asp.poll(), open(WORK + "/logs/asd.out").read()[-3000:])
    for _c in (["ldd", asd], ["bash", "-c", "tail -50 /tmp/aswork/asd.log; ulimit -n; cat /proc/meminfo | head -3"]):
        try:
            LOG.error("DIAG %s:\n%s", _c[0], subprocess.run(_c, capture_output=True, text=True, timeout=30).stdout[-3000:])
        except Exception as _e:
            LOG.error("DIAG %s loi %s", _c, _e)
    sys.exit(1)
time.sleep(5)
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "aerospike"])
import aerospike
CL = aerospike.client({"hosts": [("127.0.0.1", 3222)], "policies": {"timeout": 20000}}).connect()
WP = {"key": aerospike.POLICY_KEY_SEND}
TZ7 = datetime.timezone(datetime.timedelta(hours=7))
# ---- nap set nho (pickle ban sao) ----
AS = pickle.load(open(pick(CFG["asdata_file"], CFG["asdata_ds"]), "rb"))
if CFG.get("funding_pkl"):
    FD = pickle.load(open(pick(CFG["funding_pkl"]["file"], CFG["funding_pkl"]["ds"]), "rb"))
    AS["funding_data"] = FD["funding_data"]
    LOG.info("funding_data thay bang %s (%d rec)", CFG["funding_pkl"]["file"], len(FD["funding_data"]))
if CFG.get("lifecycle_pkl"):
    LC = pickle.load(open(pick(CFG["lifecycle_pkl"]["file"], CFG["lifecycle_pkl"]["ds"]), "rb"))
    AS["symbol_lifecycle"] = LC["symbol_lifecycle"]
    LOG.info("symbol_lifecycle thay bang %s (%d rec)", CFG["lifecycle_pkl"]["file"], len(LC["symbol_lifecycle"]))
NLOAD = {}
for st, rows in AS.items():
    for k, bins in rows:
        CL.put(("test", st, k), bins, policy=WP)
    NLOAD[st] = len(rows)
LOG.info("nap set nho: %s", NLOAD)
# ---- market_data_object tu market.bin ----
mb = pick(CFG["market"]["file"], CFG["market"]["ds"])
with open(mb, "rb") as f:
    n = struct.unpack(">i", f.read(4))[0]
    buf = f.read(20 * n)
lo, hi = int(CFG["market"]["lo"]), int(CFG["market"]["hi"])
nm = 0
for i in range(n):
    t = struct.unpack_from(">q", buf, 20 * i)[0]
    if t < lo or t >= hi:
        continue
    k = datetime.datetime.fromtimestamp(t / 1000, TZ7).strftime("%Y%m%d-%H%M")
    CL.put(("test", "market_data_object", k), {"time": t, "data": bytearray(buf[20 * i + 8:20 * i + 20])}, policy=WP)
    nm += 1
LOG.info("nap market_data_object %d phut tu %s [%d,%d)", nm, os.path.basename(mb), lo, hi)
NLOAD["market_data_object"] = nm
# ---- kline_1m_opt: Java IngestTickerFileToAerospike tu ticker file (.bin Kaggle -> gzip lai) ----
os.makedirs("/tmp/tk", exist_ok=True)
d0 = datetime.datetime.strptime(CFG["ingest"][0], "%Y%m%d"); d1 = datetime.datetime.strptime(CFG["ingest"][1], "%Y%m%d")
tk = {}
for p in glob.glob(IN + "/**/ticker_2*.bin*", recursive=True):
    if any(("/" + d + "/") in p for d in CFG["ticker_ds"]):
        tk[re.search(r"ticker_(\d{8})", p).group(1)] = p
d, nt, miss = d0, 0, []
while d <= d1:
    s = d.strftime("%Y%m%d"); p = tk.get(s)
    if p is None:
        miss.append(s)
    elif p.endswith(".gz"):
        os.symlink(p, "/tmp/tk/ticker_%s.bin.gz" % s); nt += 1
    else:
        with open(p, "rb") as fi, gzip.open("/tmp/tk/ticker_%s.bin.gz" % s, "wb", 1) as fo:
            shutil.copyfileobj(fi, fo, 1 << 22)
        nt += 1
    d += datetime.timedelta(days=1)
LOG.info("ticker ingest: %d file, thieu %s", nt, miss)
JAVA = ["java", "-Duser.timezone=Asia/Ho_Chi_Minh", "-Xmx%dg" % CFG.get("xmx_gb", 20), "-cp", jar]
rc = subprocess.call(JAVA + ["com.binance.chuyennd.ai_ml.validation.data.IngestTickerFileToAerospike", CFG["ingest"][0],
                             CFG["ingest"][1], "127.0.0.1", "3222", "test", "/tmp/tk/"],
                     stdout=open(WORK + "/logs/ingest.out", "w"), stderr=subprocess.STDOUT)
LOG.info("INGEST rc=%s tail=%s", rc, open(WORK + "/logs/ingest.out").read()[-300:])
if rc != 0:
    sys.exit(1)
shutil.rmtree("/tmp/tk")
# ---- chay cac exporter Java goc ----
RES = dict(tag=CFG["tag"], jar_sha256=JSHA, load=NLOAD, tasks=[])
for t in CFG["tasks"]:
    env = dict(os.environ)
    env.update({k: str(v) for k, v in t.get("env", {}).items()})
    cmd = JAVA + [t["cls"]] + [a.replace("@OUT", OUTD) for a in t["args"]]
    for p in t.get("mkdirs", []):
        os.makedirs(p.replace("@OUT", OUTD), exist_ok=True)
    LOG.info("TASK %s CMD %s ENV %s", t["name"], " ".join(cmd), t.get("env"))
    t0 = time.time()
    lf = WORK + "/logs/%s.out" % t["name"]
    rc = subprocess.call(cmd, env=env, stdout=open(lf, "w"), stderr=subprocess.STDOUT)
    outs = {}
    for p in sorted(glob.glob(OUTD + "/" + t.get("out_glob", t["name"] + "*"), recursive=True)):
        if os.path.isfile(p):
            outs[os.path.relpath(p, OUTD)] = dict(md5=md5f(p), bytes=os.path.getsize(p))
    r = dict(name=t["name"], rc=rc, secs=round(time.time() - t0, 1), outputs=outs,
             tail=open(lf, errors="ignore").read()[-1500:])
    RES["tasks"].append(r)
    LOG.info("TASK %s rc=%s %.0fs outputs=%s", t["name"], rc, r["secs"], list(outs))
    json.dump(RES, open(WORK + "/result.json", "w"), indent=1)
try:
    CL.close()
except Exception:
    pass
asp.terminate()
shutil.copy("/tmp/aswork/asd.log", WORK + "/logs/asd.log") if os.path.exists("/tmp/aswork/asd.log") else None
RES["ok"] = all(r["rc"] == 0 for r in RES["tasks"])
json.dump(RES, open(WORK + "/result.json", "w"), indent=1)
LOG.info("EXP_DONE ok=%s", RES["ok"])
'''


def api():
    from kaggle.api.kaggle_api_extended import KaggleApi
    a = KaggleApi()
    a.authenticate()
    return a


def slug(tag):
    return re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")


def submit(cfgp):
    cfg = json.load(open(cfgp))
    tag = cfg["tag"]
    ref = "%s/%s" % (USER, slug(tag))
    fol = os.path.join(WD, slug(tag))
    os.makedirs(fol, exist_ok=True)
    code = KX.replace("__CFG_JSON__", repr(json.dumps(cfg)))
    compile(code, "k", "exec")
    open(os.path.join(fol, "run.py"), "w").write(code)
    dss = sorted(set([cfg["jar_ds"], cfg["cfg_ds"], cfg["as_ds"], cfg["asdata_ds"], cfg["market"]["ds"]] + cfg["ticker_ds"]
                     + ([cfg["funding_pkl"]["ds"]] if cfg.get("funding_pkl") else [])
                     + ([cfg["lifecycle_pkl"]["ds"]] if cfg.get("lifecycle_pkl") else [])))
    md = {"id": ref, "title": slug(tag), "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": [USER + "/" + d for d in dss], "competition_sources": [], "kernel_sources": []}
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
    {"submit": submit, "status": status, "fetch": fetch}[sys.argv[1]](sys.argv[2])
