#!/usr/bin/env python3
# Kaggle kernel worker — chay CpcvBatchRunner tren 1 SHARD cells (KHONG jobstore, KHONG WFO_STATE_HOST).
# Theo ORCH_PARITY.md: 3 guard bat buoc SELECTOR_RANK_TOPK=8 + timezone Asia/Ho_Chi_Minh + ticker file-mode.
# Kernel script -> print ra stdout de xem log Kaggle (chap nhan duoc; khong phai production code).
import glob, os, shutil, subprocess, sys

IN, WORK = "/kaggle/input", "/kaggle/working"


def one(pat):
    m = sorted(glob.glob(pat, recursive=True))
    if not m:
        print("MISSING", pat, flush=True); sys.exit(1)
    return m[0]


jar = one(IN + "/**/cpcv.jar")
cfg = one(IN + "/**/config.properties")
manifest = one(IN + "/**/manifest.txt")
cells = one(IN + "/**/cells.jsonl")
ds_dir = os.path.dirname(manifest)

# ticker file-mode: symlink tung file ticker_2*.bin* vao ./kaggle_data_hpo (relative CWD)
link = os.path.join(WORK, "kaggle_data_hpo")
if os.path.islink(link) or os.path.exists(link):
    try: os.remove(link)
    except Exception: shutil.rmtree(link, ignore_errors=True)
os.makedirs(link, exist_ok=True)
tk = sorted(glob.glob(IN + "/**/ticker_2*.bin*", recursive=True))
if not tk:
    print("MISSING ticker", flush=True); sys.exit(1)
for t in tk:
    d = os.path.join(link, os.path.basename(t))
    if not os.path.lexists(d):
        os.symlink(t, d)
shutil.copy(cfg, os.path.join(WORK, "config.properties"))
os.chdir(WORK)
print("ticker files:", len(tk), "| ds_dir:", ds_dir, "| cells:", cells, flush=True)

out = os.path.join(WORK, "out.jsonl")
env = dict(os.environ)
env.update({
    "CPCV_CELLS": cells,
    "CPCV_OUT": out,
    "WFO_DATA_DIR": ds_dir,
    "WFO_SMART_CACHE": "1",
    "SELECTOR_RANK_TOPK": "8",          # GUARD 1 — quen = -1 = SAI recipe
    "TZ": "Asia/Ho_Chi_Minh",
})
rc = subprocess.call(
    ["java", "-Duser.timezone=Asia/Ho_Chi_Minh", "-Xmx24g", "-cp", jar,  # GUARD 2 timezone
     "com.binance.chuyennd.ai_ml.wfo.CpcvBatchRunner"],
    env=env)
print("CpcvBatchRunner rc=%d | out=%s" % (rc, out), flush=True)
n = sum(1 for _ in open(out)) if os.path.exists(out) else 0
print("out rows:", n, flush=True)
sys.exit(0 if rc == 0 and n > 0 else 1)
