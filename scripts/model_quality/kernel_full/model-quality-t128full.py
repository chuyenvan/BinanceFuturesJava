#!/usr/bin/env python3
"""
TASK-128 kernel FULL — nhu model-quality-1 nhung chay TOAN KY (khong dat START/END => Java dung range pred).
Chay sau khi validate-small (model-quality-1, 2024Q1) PASS. Xuat market_realized.csv + funding_realized.csv.
Rule KAGGLE §3b-bis: glob recursive, copy config.properties vao CWD, System.exit(0) trong java.
"""
import glob, os, subprocess, shutil, sys

IN, WORK = "/kaggle/input", "/kaggle/working"
SAMPLE = os.environ.get("T128_SAMPLE_MIN", "60")

def rglob(pat):
    return sorted(glob.glob(f"{IN}/**/{pat}", recursive=True))

jar = rglob("binance-java-sdk-*.jar")
cfg = rglob("config.properties")
mani = rglob("manifest.txt")
tick = rglob("ticker_*.bin") or rglob("ticker_*.bin.gz")
print("jar", jar[:1], "cfg", cfg[:1], "wfo", mani[:1], "tick", len(tick))
assert jar and cfg and mani and tick, "THIEU MOUNT"

wfo_dir = os.path.dirname(mani[0]); ticker_dir = os.path.dirname(tick[0])
out = os.path.join(WORK, "t128_out"); os.makedirs(out, exist_ok=True)
shutil.copy(cfg[0], os.path.join(WORK, "config.properties"))

env = dict(os.environ, WFO_DATA_DIR=wfo_dir, TICKER_DIR=ticker_dir, OUT_DIR=out,
           FUNDING_SAMPLE_MIN=SAMPLE, WARMUP_DAYS="2")   # KHONG dat START/END => full range
rc = subprocess.call(["java", "-Duser.timezone=Asia/Ho_Chi_Minh", "-Xmx26g",
                      "-cp", jar[0], "com.binance.chuyennd.ai_ml.validation.Task128ModelQuality"],
                     cwd=WORK, env=env)
print("java rc =", rc)
for fn in ["market_realized.csv", "funding_realized.csv"]:
    p = os.path.join(out, fn)
    print(fn, "lines", sum(1 for _ in open(p)) if os.path.exists(p) else "MISSING")
sys.exit(0 if rc == 0 else 1)
