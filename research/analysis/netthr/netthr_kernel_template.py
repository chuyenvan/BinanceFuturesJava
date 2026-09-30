import os, sys, glob, base64, hashlib, subprocess, logging, time, shutil
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("netthr")
ARM = "__ARM__"
THR = __THR__
SRC_MD5 = "__MD5__"
CUTS = "20220101,20220401,20220701,20221001,20230101,20230401,20230701,20231001," \
       "20240101,20240401,20240701,20241001,20250101,20250401,20250701,20251001"
B64 = """__B64__"""
W = "/kaggle/working"

src = base64.b64decode(B64)
assert hashlib.md5(src).hexdigest() == SRC_MD5, "trainer md5 mismatch"
open(W + "/g015_net_train.py", "wb").write(src)
log.info("ARM=%s THR=%s trainer md5=%s", ARM, THR, SRC_MD5)

feat, labs, oi, smap, code = [], [], None, None, None
for base, dirs, files in os.walk("/kaggle/input", followlinks=True):
    for fn in files:
        p = os.path.join(base, fn)
        if fn.startswith("features_") and (fn.endswith(".bin") or ".t1c" in fn):
            feat.append((fn, p))
        elif fn.startswith("funding_label_15m_") and fn.endswith(".pb"):
            labs.append((fn, p))
        elif fn == "oi_percoin_full.bin":
            oi = p
        elif fn == "symbol_map.csv":
            smap = p
        elif fn == "tool1_col.py":
            code = base
assert feat and labs and oi and smap and code, (len(feat), len(labs), oi, smap, code)
os.makedirs(W + "/t1", exist_ok=True)
os.makedirs(W + "/lb", exist_ok=True)
nf = nl = 0
for fn, p in sorted(feat):
    start = fn.split("_")[1]
    if start < "20260101":          # HOLDOUT SEAL: khong link file 2026
        os.symlink(p, W + "/t1/" + fn)
        nf += 1
for fn, p in sorted(labs):
    parts = fn.replace(".pb", "").split("_")     # funding_label_15m_A_to_B
    start, end = parts[3], parts[5]
    if start < "20260101":
        os.symlink(p, W + "/lb/funding_label_%s_to_%s.pb" % (start, end))
        nl += 1
log.info("linked features=%d labels=%d (pre-2026 only) code=%s", nf, nl, code)
assert not [f for f in os.listdir(W + "/t1") if f.split("_")[1] >= "20260101"]
for f in ("tool1_col.py", "funding_label_pb.py"):
    log.info("%s md5=%s", f, hashlib.md5(open(os.path.join(code, f), "rb").read()).hexdigest())
subprocess.call("nvidia-smi -L", shell=True)
import xgboost
log.info("xgboost %s", xgboost.__version__)

env = dict(os.environ, T1_DIR=W + "/t1", LB_DIR=W + "/lb", OI_FILE=oi, MAP_CSV=smap, SEL1M_CODE=code)
out = W + "/out_" + ARM
cmd = [sys.executable, W + "/g015_net_train.py", "--fold", CUTS, "--device", "cuda",
       "--label-mode", "net", "--thr", str(THR), "--seed", "42", "--out-dir", out,
       "--scratch", W + "/scratch"]
log.info("RUN %s", " ".join(cmd))
t0 = time.time()
rc = subprocess.call(cmd, env=env)
log.info("rc=%s %.1f min", rc, (time.time() - t0) / 60)
shutil.rmtree(W + "/scratch", ignore_errors=True)
shutil.rmtree(W + "/t1", ignore_errors=True)
shutil.rmtree(W + "/lb", ignore_errors=True)
assert rc == 0
