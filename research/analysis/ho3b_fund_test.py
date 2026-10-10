#!/usr/bin/env python3
"""Thu khoi FUND_REBUILD tren du lieu nho (3 ngay 2022-01) truoc khi day kernel: funding cu = ho1_funding_build.emit
tren luoi cu (bo ~2% phut), luoi moi = du phut. Ky vong: FUND_REBUILD_OK; va 1 lan co tinh lam hong -> FAIL."""
import glob, hashlib, json, logging, os, shutil, struct, sys
import numpy as np
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import ho1_funding_build as F
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
LOG = logging.getLogger("t")
T = "/tmp/ho3b_ftest"
shutil.rmtree(T, ignore_errors=True); os.makedirs(T + "/bins"); os.makedirs(T + "/ds")
a = np.fromfile("/home/ubuntu/predwf_map_s1a2_x1_2021/predict_wf_20220101.bin", dtype=F.DT)
lo = int(a["ts"].min()); hi = lo + 3 * 86400000
a[(a["ts"] >= lo) & (a["ts"] < hi)].tofile(T + "/bins/predict_wf_20220101.bin")
grid_new = np.arange(lo, hi, 60000, dtype=np.int64)
rng = np.random.default_rng(1)
grid_old = grid_new[rng.random(len(grid_new)) > 0.02]
def wm(p, g):
    with open(p, "wb") as f:
        f.write(struct.pack(">i", len(g)))
        for t in g:
            f.write(struct.pack(">qfff", int(t), 0.1, 0.2, 0.3))
wm(T + "/ds/market_old.bin", grid_old); wm(T + "/ds/market.bin", grid_new)
u, cnt, blocks, meta = F.load_bins([T + "/bins/predict_wf_20220101.bin"])
seal7 = lo + 86400000
with open(T + "/ds/funding.bin", "wb") as f:
    F.emit(u, cnt, blocks, grid_old, hi + 1, f.write)
md = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
open(T + "/ds/pred.bin", "wb").write(b"x")
open(T + "/ds/manifest.txt", "w").write("predictWf.predict_wf_20220101.bin=md5:%s;ts:1..2\nmarketCount=1\nfundingCount=1\nmd5_market=a\nmd5_pred=b\nmd5_funding=%s\n" % (md(T + "/bins/predict_wf_20220101.bin"), md(T + "/ds/funding.bin")))
def _md5(p): return md(p)
for mode in ("ok", "bad"):
    if mode == "bad":
        b = bytearray(open(T + "/ds/funding.bin", "rb").read()); b[-3] ^= 1; open(T + "/ds/funding.bin", "wb").write(bytes(b))
    g = dict(CFG={"fund_rebuild": {"need_bins": ["predict_wf_20220101.bin"], "end": hi + 1, "seal7": seal7}}, PREDWF=T + "/bins", DS=T + "/ds",
             _md5=_md5, LOG=LOG, glob=glob, os=os, sys=sys, WORK=T + "/work_" + mode)
    os.makedirs(g["WORK"], exist_ok=True)
    src = open("/home/ubuntu/claude_master/1003/ho3b/ho3b_fund_block.py").read().split("    if not _pre_ok or _miss or _diff:")[0]
    src += open("/home/ubuntu/claude_master/1003/ho3b/ho3b_fund_block2.py").read()
    try:
        exec(compile(src, "fund_block", "exec"), g)
        print(mode, "RESULT: OK DS=", g["DS"], open(g["DS"] + "/manifest.txt").read().strip().splitlines()[-4:])
    except SystemExit as e:
        print(mode, "RESULT: SystemExit", e.code)
