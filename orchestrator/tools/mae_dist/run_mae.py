#!/usr/bin/env python3
# Kernel Kaggle: do PHAN PHOI MAE (day sau nhat) tren tap entry ma selector chon.
# Muc dich: Uni chi ra selector chon coin bien dong manh -> co the DUMP 3-4 lan (-67%..-75%).
# Dat moc DCA bang phan doan la hong ca cau truc => phai DO thuc te coin di sau bao nhieu.
import glob, os, shutil, subprocess, sys

IN, WORK = "/kaggle/input", "/kaggle/working"

def find_one(pat):
    m = sorted(glob.glob(pat, recursive=True))
    if not m:
        print("MISSING glob:", pat, flush=True); sys.exit(1)
    return m[0]

jar = find_one(IN + "/**/binance-java-sdk-*.jar")
cfg = find_one(IN + "/**/config.properties")
manifest = find_one(IN + "/**/manifest.txt")      # dataset _ff (market/pred/funding.bin)
ds_dir = os.path.dirname(manifest)

shutil.copy(cfg, os.path.join(WORK, "config.properties"))

# ticker: uu tien tar, khong thi symlink thu muc per-file
link = os.path.join(WORK, "kaggle_data_hpo")
if os.path.islink(link): os.remove(link)
elif os.path.exists(link): shutil.rmtree(link, ignore_errors=True)

tar_hits = sorted(glob.glob(IN + "/**/ticker_all.tar", recursive=True))
if tar_hits:
    os.makedirs(link, exist_ok=True)
    rc = subprocess.call(["tar", "xf", tar_hits[0], "-C", link])
    if rc != 0: print("tar FAILED", flush=True); sys.exit(1)
    print("TICKER extracted %d files" % len(glob.glob(os.path.join(link, "ticker_2*.bin*"))), flush=True)
else:
    tk = sorted(glob.glob(IN + "/**/ticker_2*.bin*", recursive=True))
    if not tk: print("MISSING ticker", flush=True); sys.exit(1)
    os.symlink(os.path.dirname(tk[0]), link)
    print("TICKER symlink %d files" % len(tk), flush=True)

print("jar=%s\nds_dir=%s" % (jar, ds_dir), flush=True)
os.chdir(WORK)

env = dict(os.environ)
env.update({
    "WFO_DATA_DIR": ds_dir,
    "MAE_FROM": "20210101",
    "MAE_TO": "20260501",
    "SIM_APPLY_FUNDING": "true",
    # rate-min >= 3% theo Uni chot. Khong doi gi khac -> do dung tap entry hien tai.
    "SIM_RATE_PROFIT_STOP_MARKET": "0.03",
})

rc = subprocess.call(["java", "-Xmx20g", "-cp", jar,
                      "com.binance.chuyennd.ai_ml.wfo.framework.tasks.MaeDistributionProbe"], env=env)
print("MaeDistributionProbe rc=%d" % rc, flush=True)
sys.exit(0 if rc == 0 else 1)
