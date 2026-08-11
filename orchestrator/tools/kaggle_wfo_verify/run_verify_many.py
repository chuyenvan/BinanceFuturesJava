#!/usr/bin/env python3
# run_verify_many.py - kernel Kaggle: VerifyOneWindow cho NHIEU window (danh sach WINDOWS,
# vd "3,10"), TUAN TU trong 1 kernel, JOBSTORE-FREE. Thay the duong WfoWorker/fanout dang co
# bug khong nhan TS_RATCHET_DECOUPLED (xem EXIT_MACHINE PHAN 5). Moi window in 1 dong RESULT_JSON.
import glob, os, shutil, subprocess, sys

IN = "/kaggle/input"
WORK = "/kaggle/working"
WINDOWS = os.environ.get("VERIFY_WINDOWS", "15").split(",")
RATCHET_DECOUPLED = "true"   # <-- TOGGLE truoc khi push: "true" | "false"

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

print("jar=%s\nds_dir=%s\nwindows=%s\nTS_RATCHET_DECOUPLED=%s" % (jar, ds_dir, WINDOWS, RATCHET_DECOUPLED), flush=True)
os.chdir(WORK)

env = dict(os.environ)
env.update({
    "WFO_DATA_DIR": ds_dir,
    "WFO_N_SAMPLES": "30",
    "WFO_SEED_BASE": "42",
    "WFO_MAX_OOS_DATE": os.environ.get("WFO_MAX_OOS_DATE", "20260101"),
    "TS_RATCHET_DECOUPLED": RATCHET_DECOUPLED,
})

fails = 0
for w in WINDOWS:
    w = w.strip()
    if not w:
        continue
    print("=== BAT DAU window %s ===" % w, flush=True)
    rc = subprocess.call(["java", "-Xmx8g", "-cp", jar,
                          "com.binance.chuyennd.ai_ml.wfo.VerifyOneWindow", w], env=env)
    print("=== KET THUC window %s rc=%d ===" % (w, rc), flush=True)
    if rc != 0:
        fails += 1

print("DONE_ALL windows=%s fails=%d" % (WINDOWS, fails), flush=True)
sys.exit(0 if fails == 0 else 1)
