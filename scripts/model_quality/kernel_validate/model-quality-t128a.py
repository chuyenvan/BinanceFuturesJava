#!/usr/bin/env python3
"""
TASK-128 kernel — chay Task128ModelQuality (Java) tren Kaggle CPU.
Doc WfoDataset (wfo-dataset-wf-leakfree) + ticker file (hpo-ticker-daily) + jar (t128-model-quality-jar).
Xuat market_realized.csv + funding_realized.csv -> /kaggle/working/t128_out (kernel output).

Mode: env T128_START/T128_END dat range (validate-small = 1 quy). Bo trong = toan ky (full).
Rule KAGGLE §3b-bis: glob recursive /kaggle/input, copy config.properties vao CWD, System.exit(0) trong java.
"""
import glob, os, subprocess, shutil, sys

IN = "/kaggle/input"
WORK = "/kaggle/working"
START = os.environ.get("T128_START", "20240101")   # validate-small 2024Q1
END   = os.environ.get("T128_END", "20240401")
SAMPLE = os.environ.get("T128_SAMPLE_MIN", "60")

def rglob(pat):
    return sorted(glob.glob(f"{IN}/**/{pat}", recursive=True))

jar_hits = rglob("binance-java-sdk-*.jar")
cfg_hits = rglob("config.properties")
mani_hits = rglob("manifest.txt")          # wfo dataset dir marker
tick_hits = rglob("ticker_*.bin")          # ticker daily (uncompressed .bin)
if not tick_hits:
    tick_hits = rglob("ticker_*.bin.gz")

print("jar :", jar_hits[:2])
print("cfg :", cfg_hits[:2])
print("mani:", mani_hits[:2])
print("tick:", len(tick_hits), "files; sample:", tick_hits[:1], tick_hits[-1:])
assert jar_hits and cfg_hits and mani_hits and tick_hits, "THIEU MOUNT (delay dataset moi? cho vai phut roi push lai)"

jar = jar_hits[0]
wfo_dir = os.path.dirname(mani_hits[0])
ticker_dir = os.path.dirname(tick_hits[0])
out = os.path.join(WORK, "t128_out")
os.makedirs(out, exist_ok=True)

# Configs doc config.properties tu CWD
shutil.copy(cfg_hits[0], os.path.join(WORK, "config.properties"))

env = dict(os.environ,
           WFO_DATA_DIR=wfo_dir, TICKER_DIR=ticker_dir, OUT_DIR=out,
           START=START, END=END, FUNDING_SAMPLE_MIN=SAMPLE, WARMUP_DAYS="2")
print(f"RUN range {START}->{END} sample={SAMPLE}m | wfo={wfo_dir} ticker={ticker_dir}")

rc = subprocess.call(
    ["java", "-Duser.timezone=Asia/Ho_Chi_Minh", "-Xmx26g",
     "-cp", jar, "com.binance.chuyennd.ai_ml.validation.Task128ModelQuality"],
    cwd=WORK, env=env)
print("java rc =", rc)

for fn in ["market_realized.csv", "funding_realized.csv"]:
    p = os.path.join(out, fn)
    if os.path.exists(p):
        n = sum(1 for _ in open(p))
        print(f"--- {fn}: {n} lines ---")
        with open(p) as fh:
            for i, line in enumerate(fh):
                if i < 6: print(line.rstrip())
                else: break
    else:
        print("MISSING", p)

sys.exit(0 if rc == 0 else 1)
