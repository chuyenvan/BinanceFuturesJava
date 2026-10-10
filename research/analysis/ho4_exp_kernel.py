#!/usr/bin/env python3
"""HO4-P3 (ADDENDUM-5 §5.3, 31e3c9e7): kernel Kaggle `ho4-dev-x` dung lai lat DEV tu Binance Vision bang CONG CU GOC.
Trong kernel: tai Vision klines 1m monthly (universe USDT, khong '_', trong mapper 863) -> ticker file (ho3b_jwrite, byte-format
ExportTickerDaily) -> Java IngestTickerFileToAerospike vao Aerospike CE RIENG (127.0.0.1:3222); funding_data = Vision fundingRate
(format record local); mapper/lifecycle = ban sao local (ho3b-asdata). Java goc jar b7c89f09: ExportMarketData2File (TIME_RUN rieng)
-> dump set -> market.bin lat; ExportGateDataset; ExportFeaturesForPythonTool FF_UNFILTERED=1 (mep file DEV); ExportFundingLabel.
Cong F (funding) va M (market) do NGAY trong kernel (so voi asdata local / market.bin bundle DEV). KHONG cham Aerospike Oracle/242.
Usage: ho4_exp_kernel.py submit <cfg.json> | status <tag> | fetch <tag>"""
import json, logging, os, re, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho4_exp")
USER = "chuyendinh"
WD = "/home/ubuntu/claude_master/1010/ho4/kaggle"
JW = "/home/ubuntu/src/BinanceFuturesJava/research/analysis/ho3b_jwrite.py"
KX = r'''"""HO4 exporter kernel — SINH TU ho4_exp_kernel.py (ADDENDUM-5 31e3c9e7)"""
import glob, gzip, hashlib, io, json, logging, os, pickle, re, shutil, socket, struct, subprocess, sys, time, datetime
import urllib.request, urllib.parse, zipfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
LOG = logging.getLogger("ho4-X")
CFG = json.loads(__CFG_JSON__)
IN, WORK = "/kaggle/input", "/kaggle/working"
OUTD = WORK + "/out"
for _d in (OUTD, WORK + "/logs", OUTD + "/ticker"):
    os.makedirs(_d, exist_ok=True)
open(WORK + "/ho3b_jwrite.py", "w").write(__JW_SRC__)
sys.path.insert(0, WORK)
import ho3b_jwrite as JWR
RES = dict(tag=CFG["tag"], prereg="ADDENDUM-5 31e3c9e7", steps={}, tasks=[])
def save():
    json.dump(RES, open(WORK + "/result.json", "w"), indent=1)
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
RES["jar_sha256"] = JSHA
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "aerospike", "cramjam"])
import cramjam
TZ7 = datetime.timezone(datetime.timedelta(hours=7))
UTC = datetime.timezone.utc
S_LO, S_HI = int(CFG["S"][0]), int(CFG["S"][1])
# ---------------- Vision helpers ----------------
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
def http(u):
    for a in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "ho4"}), timeout=90) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 + 3 * a)
        except Exception:
            time.sleep(2 + 3 * a)
    raise IOError("HTTP_FAIL " + u)
def list_syms(pref):
    out, marker = set(), ""
    while True:
        x = http(S3 + "?delimiter=/&prefix=" + pref + ("&marker=" + urllib.parse.quote(marker) if marker else "")).decode()
        ps = re.findall(r"<Prefix>(.*?)</Prefix>", x)
        for p in ps:
            s = p[len(pref):].strip("/")
            if s:
                out.add(urllib.parse.unquote(s))
        if "<IsTruncated>true</IsTruncated>" not in x:
            break
        m = re.search(r"<NextMarker>(.*?)</NextMarker>", x)
        marker = m.group(1) if m else ps[-1]
    return sorted(out)
MAPPER = set(CFG["mapper"])
def in_uni(s):
    return s.endswith("USDT") and "_" not in s and s in MAPPER
# ---------------- B1: Vision klines -> ticker files (UTC day) ----------------
KURL = "https://data.binance.vision/data/futures/um/monthly/klines/{s}/1m/{s}-1m-{m}.zip"
def kl(sym, m):
    b = http(KURL.format(s=urllib.parse.quote(sym), m=m))
    if b is None:
        return sym, None
    z = zipfile.ZipFile(io.BytesIO(b))
    rows = [ln.split(",") for ln in z.read(z.namelist()[0]).decode().splitlines()]
    rows = [r for r in rows if r and r[0].strip().isdigit()]
    if not rows:
        return sym, None
    ts = np.array([int(r[0]) for r in rows], np.int64)
    # o,h,l,c,quote_volume -> float32 (parse double roi ep float32 nhu Java (float) Double.parseDouble)
    v = np.array([[float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[7])] for r in rows], np.float64).astype(np.float32)
    return sym, (ts, v)
t0 = time.time()
DEVTK = CFG.get("dev_ticker_ds") or []          # CHAN DOAN D1: dung ticker DEV (dataset) thay Vision
ksyms = [] if DEVTK else [s for s in list_syms("data/futures/um/monthly/klines/") if in_uni(s)]
LOG.info("Vision klines listing: %d symbol trong universe (mapper %d)", len(ksyms), len(MAPPER))
day_stats, uni_month = {}, {}
for m in ([] if DEVTK else CFG["months"]):
    with ThreadPoolExecutor(CFG.get("dl_threads", 24)) as ex:
        D = {s: r for s, r in ex.map(lambda s: kl(s, m), ksyms) if r is not None}
    uni_month[m] = sorted(D)
    LOG.info("thang %s: %d symbol co du lieu (%.0fs)", m, len(D), time.time() - t0)
    y, mo = int(m[:4]), int(m[5:7])
    d = datetime.datetime(y, mo, 1, tzinfo=UTC)
    while d.month == mo:
        lo = int(d.timestamp() * 1000); hi = lo + 86400000
        per = {}
        for s in sorted(D):
            ts, v = D[s]
            k = np.nonzero((ts >= lo) & (ts < hi))[0]
            for i in k:
                per.setdefault(int(ts[i]), []).append((s, float(v[i, 0]), float(v[i, 1]), float(v[i, 2]), float(v[i, 3]), float(v[i, 4])))
        mins = [(t, per[t]) for t in sorted(per)]
        if mins:
            raw = JWR.encode_day(mins)
            with gzip.open(OUTD + "/ticker/ticker_%s.bin.gz" % d.strftime("%Y%m%d"), "wb", 6) as fo:
                fo.write(raw)
        day_stats[d.strftime("%Y%m%d")] = dict(n_min=len(mins), n_cells=sum(len(x[1]) for x in mins), n_sym=len({e[0] for x in mins for e in x[1]}))
        d += datetime.timedelta(days=1)
    del D
TKDIR = OUTD + "/ticker/"
if DEVTK:
    TKDIR = "/tmp/tkdev/"
    os.makedirs(TKDIR, exist_ok=True)
    _d0 = datetime.datetime.strptime(CFG["ingest"][0], "%Y%m%d"); _d1 = datetime.datetime.strptime(CFG["ingest"][1], "%Y%m%d")
    _tk = {}
    for _p in glob.glob(IN + "/**/ticker_2*.bin*", recursive=True):
        if any(("/" + _ds + "/") in _p for _ds in DEVTK):
            _tk[re.search(r"ticker_(\d{8})", _p).group(1)] = _p
    _d, _miss = _d0, []
    while _d <= _d1:
        _s = _d.strftime("%Y%m%d"); _p = _tk.get(_s)
        if _p is None:
            _miss.append(_s)
        elif _p.endswith(".gz"):
            os.symlink(_p, TKDIR + "ticker_%s.bin.gz" % _s)
        else:
            with open(_p, "rb") as _fi, gzip.open(TKDIR + "ticker_%s.bin.gz" % _s, "wb", 1) as _fo:
                shutil.copyfileobj(_fi, _fo, 1 << 22)
        _d += datetime.timedelta(days=1)
    day_stats["dev_ticker_missing"] = _miss
    LOG.info("D1: ticker DEV %d ngay, thieu %s", len(_tk), _miss)
RES["steps"]["klines"] = dict(secs=round(time.time() - t0), n_listing=len(ksyms), uni_month={k: len(v) for k, v in uni_month.items()}, days=day_stats)
json.dump(uni_month, open(OUTD + "/universe_by_month.json", "w"))
save()
# ---------------- B2: funding Vision -> funding_data; cong F vs ban sao local DEV ----------------
FURL = "https://data.binance.vision/data/futures/um/monthly/fundingRate/{s}/{s}-fundingRate-{m}.zip"
def fr(sym):
    out = {}
    for m in CFG["fund_months"]:
        b = http(FURL.format(s=urllib.parse.quote(sym), m=m))
        if b is None:
            continue
        z = zipfile.ZipFile(io.BytesIO(b))
        for ln in z.read(z.namelist()[0]).decode().splitlines():
            p = ln.split(",")
            if len(p) >= 3 and p[0].strip().isdigit():
                out[int(p[0])] = float(np.float32(float(p[2])))
    return sym, out
t0 = time.time()
fsyms = [s for s in list_syms("data/futures/um/monthly/fundingRate/") if in_uni(s)]
with ThreadPoolExecutor(16) as ex:
    V = {s: v for s, v in ex.map(fr, fsyms) if v}
AS = pickle.load(open(pick(CFG["asdata_file"], CFG["asdata_ds"]), "rb"))
loc = {}
for k, b in AS["funding_data"]:
    mp = json.loads(bytes(cramjam.snappy.decompress_raw(bytes(b["f_data"])))) if b.get("f_data") else {}
    loc[k] = {int(t): float(x) for t, x in mp.items()}
F = dict(dev_pts=0, found=0, equal=0, dev_sym=0, dev_sym_no_vision=[], vis_extra_pts=0, bad_examples=[])
for s, mp in sorted(loc.items()):
    if not in_uni(s):
        continue
    pts = {t: x for t, x in mp.items() if S_LO <= t < S_HI}
    if not pts:
        continue
    F["dev_sym"] += 1
    vv = V.get(s, {})
    if not vv:
        F["dev_sym_no_vision"].append(s)
    for t, x in pts.items():
        F["dev_pts"] += 1
        if t in vv:
            F["found"] += 1
            if np.float32(vv[t]) == np.float32(x):
                F["equal"] += 1
            elif len(F["bad_examples"]) < 20:
                F["bad_examples"].append([s, t])
        elif len(F["bad_examples"]) < 20:
            F["bad_examples"].append([s, t, "missing"])
    F["vis_extra_pts"] += sum(1 for t in vv if S_LO <= t < S_HI and t not in pts)
F["vis_sym_not_local"] = sorted(s for s in V if s not in loc and any(S_LO <= t < S_HI for t in V[s]))[:100]
F["frac"] = F["equal"] / max(1, F["dev_pts"])
F["pass"] = F["dev_pts"] > 0 and F["equal"] == F["dev_pts"]
F["secs"] = round(time.time() - t0)
RES["steps"]["funding_F"] = F
LOG.info("CONG F: dev_pts=%d equal=%d frac=%.6f pass=%s", F["dev_pts"], F["equal"], F["frac"], F["pass"])
fund_rows = []
for s in sorted(V):
    js = json.dumps({str(t): V[s][t] for t in sorted(V[s])}, separators=(",", ":")).encode()
    fund_rows.append((s, {"f_data": bytes(cramjam.snappy.compress_raw(js))}))
if CFG.get("funding_local"):                    # CHAN DOAN D1: funding_data = ban sao local DEV
    fund_rows = list(AS["funding_data"])
    LOG.info("D1: funding_data = ban sao local (%d)", len(fund_rows))
pickle.dump({"funding_data": fund_rows}, open(OUTD + "/funding_vision.pkl", "wb"), protocol=4)
save()
# ---------------- B3: Aerospike CE rieng trong kernel ----------------
_osr = open("/etc/os-release").read()
_vid = "24.04" if 'VERSION_ID="24' in _osr else "22.04"
deb = pick("aerospike-server-community_7.2.0.6-1ubuntu%s_amd64.deb" % _vid, CFG["as_ds"])
subprocess.check_call(["dpkg", "-x", deb, "/opt/as"])
asd = [p for p in glob.glob("/opt/as/**/asd", recursive=True) if os.path.isfile(p)][0]
for _d in ("/tmp/aswork/smd", "/tmp/aswork/usr/udf/lua", "/opt/aerospike/usr/udf/lua", "/opt/aerospike/smd", "/opt/aerospike/sys/udf/lua"):
    os.makedirs(_d, exist_ok=True)
conf = """service {
    cluster-name ho4
    proto-fd-max 15000
    work-directory /tmp/aswork
}
logging {
    file /tmp/aswork/asd.log {
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
""" % CFG.get("as_mem_gb", 14)
open("/tmp/aswork/as.conf", "w").write(conf)
asp = subprocess.Popen([asd, "--config-file", "/tmp/aswork/as.conf", "--foreground"], stdout=open(WORK + "/logs/asd.out", "w"), stderr=subprocess.STDOUT)
ok = False
for i in range(60):
    try:
        with socket.create_connection(("127.0.0.1", 3222), timeout=2):
            ok = True; break
    except Exception:
        time.sleep(2)
LOG.info("ASD up=%s", ok)
if not ok:
    LOG.error("ASD_FAIL %s", open(WORK + "/logs/asd.out").read()[-3000:]); sys.exit(1)
time.sleep(5)
import aerospike
CL = aerospike.client({"hosts": [("127.0.0.1", 3222)], "policies": {"timeout": 20000}}).connect()
WP = {"key": aerospike.POLICY_KEY_SEND}
NLOAD = {}
for st, rows in AS.items():
    if st == "funding_data":
        continue  # thay bang Vision (ADDENDUM-5 nguyen tac 1)
    for k, bins in rows:
        CL.put(("test", st, k), bins, policy=WP)
    NLOAD[st] = len(rows)
for k, bins in fund_rows:
    CL.put(("test", "funding_data", k), bins, policy=WP)
NLOAD["funding_data"] = len(fund_rows)
LOG.info("nap set nho: %s (asdata sets=%s)", NLOAD, list(AS))
# ---------------- B4: config + ingest kline (Java goc) ----------------
RAWCFG = open(pick("config.properties", CFG["cfg_ds"])).read().splitlines()
def write_cfg(extra):
    ov = dict(CFG["cfg_override"]); ov.update(extra or {})
    ov.update({"AEROSPIKE_HOST": "127.0.0.1", "AEROSPIKE_HOST_226": "127.0.0.1", "AEROSPIKE_PORT_226": "3222",
               "AEROSPIKE_PORT": "3222", "AEROSPIKE_READ_CLUSTER": "226"})
    seen, outl = set(), []
    for ln in RAWCFG:
        mm = re.match(r"\s*([A-Z0-9_]+)\s*=", ln)
        if mm and mm.group(1) in ov:
            ln = "%s=%s" % (mm.group(1), ov[mm.group(1)]); seen.add(mm.group(1))
        outl.append(ln)
    for k, v in ov.items():
        if k not in seen:
            outl.append("%s=%s" % (k, v))
    hosts = [l for l in outl if re.match(r"\s*AEROSPIKE_HOST", l)]
    if any("127.0.0.1" not in h for h in hosts):
        LOG.error("NOWRITE_FAIL host khac localhost %s", hosts); sys.exit(2)
    open(WORK + "/config.properties", "w").write("\n".join(outl) + "\n")
write_cfg({})
os.chdir(WORK)
JAVA = ["java", "-Duser.timezone=Asia/Ho_Chi_Minh", "-Xmx%dg" % CFG.get("xmx_gb", 11), "-cp", jar]
t0 = time.time()
rc = subprocess.call(JAVA + ["com.binance.chuyennd.ai_ml.validation.data.IngestTickerFileToAerospike", CFG["ingest"][0],
                             CFG["ingest"][1], "127.0.0.1", "3222", "test", TKDIR],
                     stdout=open(WORK + "/logs/ingest.out", "w"), stderr=subprocess.STDOUT)
RES["steps"]["ingest"] = dict(rc=rc, secs=round(time.time() - t0), tail=open(WORK + "/logs/ingest.out", errors="ignore").read()[-600:])
LOG.info("INGEST rc=%s %ss", rc, RES["steps"]["ingest"]["secs"])
save()
if rc != 0:
    sys.exit(1)
# ---------------- B5: market dump + cong M ----------------
def dump_market(path):
    recs = {}
    def cb(rec):
        b = rec[2]
        t, dat = b.get("time"), b.get("data")
        if t is not None and dat is not None and len(dat) == 12:
            recs[int(t)] = bytes(dat)
    CL.scan("test", "market_data_object").foreach(cb)
    ts = sorted(recs)
    with open(path, "wb") as f:
        f.write(struct.pack(">i", len(ts)))
        for t in ts:
            f.write(struct.pack(">q", t) + recs[t])
    return len(ts)
def read_market(path):
    with open(path, "rb") as f:
        n = struct.unpack(">i", f.read(4))[0]
        a = np.frombuffer(f.read(20 * n), dtype=np.dtype([("ts", ">i8"), ("v", ">f4", 3)]))
    return a["ts"].astype(np.int64), a["v"].astype(np.float64)
def gate_M(newp):
    nt, nv = read_market(newp)
    dt, dv = read_market(pick("market.bin", CFG["dev_market_ds"]))
    kn = (nt >= S_LO) & (nt < S_HI); kd = (dt >= S_LO) & (dt < S_HI)
    nt, nv, dt, dv = nt[kn], nv[kn], dt[kd], dv[kd]
    com, ia, ib = np.intersect1d(dt, nt, return_indices=True)
    okc = (np.abs(dv[ia] - nv[ib]) <= 1e-6)
    union = len(dt) + len(nt) - len(com)
    r = dict(dev_min=int(len(dt)), new_min=int(len(nt)), common=int(len(com)), dev_only=int(len(dt) - len(com)),
             new_only=int(len(nt) - len(com)), cells=3 * union, ok_cells=int(okc.sum()),
             common_cell_frac=float(okc.mean()) if len(com) else None, common_row_all3=float(okc.all(1).mean()) if len(com) else None,
             max_abs_common=float(np.abs(dv[ia] - nv[ib]).max()) if len(com) else None)
    r["frac"] = r["ok_cells"] / max(1, r["cells"]); r["pass"] = r["frac"] >= 0.999
    mon = {}
    for name, arr in (("dev_only", np.setdiff1d(dt, nt)), ("new_only", np.setdiff1d(nt, dt)), ("bad_common", com[~okc.all(1)])):
        for t in arr:
            k = datetime.datetime.fromtimestamp(t / 1000, TZ7).strftime("%Y-%m")
            mon.setdefault(k, {}).setdefault(name, 0); mon[k][name] += 1
    r["by_month"] = mon
    return r
# ---------------- B6: cac exporter Java goc ----------------
for t in CFG["tasks"]:
    write_cfg(t.get("cfg"))
    env = dict(os.environ); env.update({k: str(v) for k, v in t.get("env", {}).items()})
    for p in t.get("mkdirs", []):
        os.makedirs(p.replace("@OUT", OUTD), exist_ok=True)
    cmd = JAVA + [t["cls"]] + [a.replace("@OUT", OUTD) for a in t["args"]]
    LOG.info("TASK %s CMD %s ENV %s CFG %s", t["name"], " ".join(cmd), t.get("env"), t.get("cfg"))
    t0 = time.time(); lf = WORK + "/logs/%s.out" % t["name"]
    try:
        rc = subprocess.call(cmd, env=env, stdout=open(lf, "w"), stderr=subprocess.STDOUT, timeout=t.get("timeout_s", 14400))
    except subprocess.TimeoutExpired:
        rc = "timeout"
    r = dict(name=t["name"], rc=rc, secs=round(time.time() - t0, 1), tail=open(lf, errors="ignore").read()[-1500:])
    if t.get("post") == "market" and rc == 0:
        n = dump_market(OUTD + "/market_rebuilt.bin")
        r["market_dump_n"] = n
        try:
            RES["steps"]["market_M"] = gate_M(OUTD + "/market_rebuilt.bin")
            LOG.info("CONG M: %s", {k: v for k, v in RES["steps"]["market_M"].items() if k != "by_month"})
        except Exception as e:
            RES["steps"]["market_M"] = dict(error=repr(e))
    outs = {}
    for p in sorted(glob.glob(OUTD + "/" + t.get("out_glob", t["name"] + "*"), recursive=True)):
        if os.path.isfile(p):
            outs[os.path.relpath(p, OUTD)] = dict(md5=md5f(p), bytes=os.path.getsize(p))
    r["outputs"] = outs
    RES["tasks"].append(r)
    LOG.info("TASK %s rc=%s %.0fs outputs=%s", t["name"], rc, r["secs"], list(outs))
    save()
try:
    CL.close()
except Exception:
    pass
asp.terminate()
tk = sorted(glob.glob(OUTD + "/ticker/*.bin.gz"))
json.dump({os.path.basename(p): md5f(p) for p in tk}, open(OUTD + "/ticker_md5.json", "w"), indent=0)
RES["ok"] = all(r["rc"] == 0 for r in RES["tasks"])
save()
LOG.info("EXP_DONE ok=%s", RES["ok"])
'''


def api():
    from kaggle.api.kaggle_api_extended import KaggleApi
    a = KaggleApi()
    a.authenticate()
    return a


def slug(tag):
    return re.sub(r"[^a-z0-9]+", "-", tag.lower()).strip("-")


def active():
    a, act = api(), []
    for k in a.kernels_list(mine=True, page_size=20, sort_by="dateRun"):
        try:
            r = a.kernels_status(k.ref)
            st = str(r.get("status") if isinstance(r, dict) else getattr(r, "status", r)).split(".")[-1].upper()
        except Exception:  # noqa: BLE001
            st = "ERR"
        if st in ("RUNNING", "QUEUED"):
            act.append(k.ref)
    return act


def submit(cfgp):
    cfg = json.load(open(cfgp))
    act = active()
    if len(act) >= 2:
        log.error("DA CO %d kernel dang chay %s — khong day", len(act), act)
        sys.exit(3)
    tag = cfg["tag"]
    ref = "%s/%s" % (USER, slug(tag))
    fol = os.path.join(WD, slug(tag))
    os.makedirs(fol, exist_ok=True)
    code = KX.replace("__CFG_JSON__", repr(json.dumps(cfg))).replace("__JW_SRC__", repr(open(JW).read()))
    compile(code, "k", "exec")
    open(os.path.join(fol, "run.py"), "w").write(code)
    dss = sorted({cfg["jar_ds"], cfg["cfg_ds"], cfg["as_ds"], cfg["asdata_ds"], cfg["dev_market_ds"]} | set(cfg.get("dev_ticker_ds") or []))
    md = {"id": ref, "title": slug(tag), "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": [USER + "/" + d for d in dss], "competition_sources": [], "kernel_sources": []}
    json.dump(md, open(os.path.join(fol, "kernel-metadata.json"), "w"), indent=1)
    r = api().kernels_push(fol)
    log.info("PUSHED %s %s (active truoc: %s)", ref, getattr(r, "url", r), act)


def status(tag):
    r = api().kernels_status("%s/%s" % (USER, slug(tag)))
    log.info("STATUS %s %s", tag, r.get("status") if isinstance(r, dict) else getattr(r, "status", r))


def fetch(tag, pat=r"^(?!out/ticker/)"):
    """Chi tai file khop regex `pat` (mac dinh: BO ticker ~2,8 GB — dia Oracle chi ~2 GB trong)."""
    import requests
    out = os.path.join(WD, "out", slug(tag))
    os.makedirs(out, exist_ok=True)
    a = api()
    resp = a.process_response(a.kernel_output_with_http_info(USER, slug(tag)))
    got, skip = [], 0
    for it in resp["files"]:
        fn = it["fileName"]
        if not re.search(pat, fn):
            skip += 1
            continue
        p = os.path.join(out, fn)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with requests.get(it["url"], stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(p, "wb") as f:
                for b in r.iter_content(1 << 22):
                    f.write(b)
        got.append(fn)
    if resp.get("log"):
        open(os.path.join(out, slug(tag) + ".log"), "w").write(resp["log"])
    log.info("FETCHED -> %s: %d file, bo qua %d: %s", out, len(got), skip, got[:20])


if __name__ == "__main__":
    if sys.argv[1] == "fetch" and len(sys.argv) > 3:
        fetch(sys.argv[2], sys.argv[3])
    else:
        {"submit": submit, "status": status, "fetch": fetch}[sys.argv[1]](sys.argv[2])
