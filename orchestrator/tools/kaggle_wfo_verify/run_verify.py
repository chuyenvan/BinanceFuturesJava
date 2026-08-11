#!/usr/bin/env python3
# run_verify.py - kernel Kaggle SMOKE-TEST: VerifyOneWindow 1 window, N=30, JOBSTORE-FREE.
# Muc dich: test jar/config/data nhanh (~vai phut, 1 window) THAY VI WfoWorker full 16-window
# (~1h). Cung dung de A/B 1 bien (vd TS_RATCHET_DECOUPLED) tren CUNG 1 window, cung seed,
# khong dinh 30 sample random-search WFO thay doi vi jobstore claim khac lan.
# TOGGLE bien can test o RATCHET_DECOUPLED duoi day - sua roi push lai qua `ce kaggle_push <dir>`.
import glob, os, shutil, subprocess, sys

IN = "/kaggle/input"
WORK = "/kaggle/working"
WIN_IDX = os.environ.get("VERIFY_WIN_IDX", "15")
RATCHET_DECOUPLED = "true"   # <-- TOGGLE: "true" | "false"

def find_one(pat):
    m = sorted(glob.glob(pat, recursive=True))
    if not m:
        print("MISSING glob:", pat, flush=True); sys.exit(1)
    return m[0]

jar = find_one(IN + "/**/binance-java-sdk-*.jar")
cfg = find_one(IN + "/**/config.properties")
manifest = find_one(IN + "/**/manifest.txt")
ds_dir = os.path.dirname(manifest)

shutil.copy(cfg, os.path.join(WORK, "config.properties"))
link = os.path.join(WORK, "kaggle_data_hpo")
if os.path.islink(link):
    os.remove(link)
elif os.path.exists(link):
    shutil.rmtree(link, ignore_errors=True)

tar_hits = sorted(glob.glob(IN + "/**/ticker_all.tar", recursive=True))
if tar_hits:
    os.makedirs(link, exist_ok=True)
    rc = subprocess.call(["tar", "xf", tar_hits[0], "-C", link])
    if rc != 0:
        print("tar extract FAILED rc=%d" % rc, flush=True); sys.exit(1)
else:
    tk = sorted(glob.glob(IN + "/**/ticker_2*.bin*", recursive=True))
    if not tk:
        print("MISSING ticker", flush=True); sys.exit(1)
    os.symlink(os.path.dirname(tk[0]), link)

print("jar=%s\nds_dir=%s\nwinIdx=%s\nTS_RATCHET_DECOUPLED=%s" % (jar, ds_dir, WIN_IDX, RATCHET_DECOUPLED), flush=True)
os.chdir(WORK)

env = dict(os.environ)
env.update({
    "WFO_DATA_DIR": ds_dir,
    "WFO_N_SAMPLES": "30",
    "WFO_SEED_BASE": "42",
    "WFO_MAX_OOS_DATE": os.environ.get("WFO_MAX_OOS_DATE", "20260101"),
    "TS_RATCHET_DECOUPLED": RATCHET_DECOUPLED,
})

rc = subprocess.call(["java", "-Xmx8g", "-cp", jar,
                      "com.binance.chuyennd.ai_ml.wfo.VerifyOneWindow", WIN_IDX], env=env)
print("VerifyOneWindow rc=%d" % rc, flush=True)
sys.exit(0 if rc == 0 else 1)
