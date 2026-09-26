#!/usr/bin/env python3
"""make_ofi_ext_kernel.py — sinh kernel Kaggle `ofi-ext-labelb-cpu` (KHONG push o day).

PREREG_OFI_MONEY §6 (B2): build nhan luat thoat cho tap coin MOI
  pool_ext_moi = (candidate top-8 ∪ baseline_fresh top-8 ∪ noise top-8) \ P32
de do GIA TRI TIEN cua OFI candidate ngoai pool P32 (P32 do S1 dinh nghia => B1 = 99,99 % ngoai P32).

Dung NGUYEN `mr_label_build.py` (da commit) + exit_engine (parity PASS) — chi doi:
  - file ung vien = `ofi_ext_trades.parquet` (dataset `chuyendinh/ofi-money-ext-trades`),
  - KMAX 32 -> 64 (giu NGUYEN thu tu trong tick; <= 43 dong/tick),
  - ten kernel/out. Moi tham so khac GIU NGUYEN (CHUNK_DAYS, MAX_INTERVAL_SEC=7200, TS_MAX_MS).
Cong chi phi §4.3 (2h/fold) van do trong kernel (cost_report.json).

Dung: python3 make_ofi_ext_kernel.py
"""
import base64
import json
import os

REPO = "/home/ubuntu/src/BinanceFuturesJava"
DST = "/home/ubuntu/kaggle_ofi_ext"
FILES = [
    ("research/pipeline/mr_label_build.py", "mrcode/research/pipeline/mr_label_build.py"),
    ("research/analysis/jbin.py", "mrcode/research/analysis/jbin.py"),
    ("research/exitfit/exit_engine.py", "mrcode/research/exitfit/exit_engine.py"),
]
TICKER_DS = ["chuyendinh/wfo-ticker-2021", "chuyendinh/wfo-ticker-2022",
             "chuyendinh/wfo-ticker-2023", "chuyendinh/wfo-ticker-2024h1",
             "chuyendinh/wfo-ticker-2024h2", "chuyendinh/wfo-ticker-2025h1",
             "chuyendinh/wfo-ticker-2025h2"]
FEAT_DS = ["chuyendinh/funding-tool1-15m", "chuyendinh/funding-label-15m",
           "chuyendinh/funding-oi-percoin", "chuyendinh/sel1m-code"]
EXT_DS = ["chuyendinh/ofi-money-ext-trades"]

KERNEL = '''# KERNEL: ofi-ext-labelb-cpu (sinh boi research/kaggle/ofi_money/make_ofi_ext_kernel.py)
# PREREG_OFI_MONEY §6 (B2): build NHAN luat thoat cho tap coin MOI (ngoai P32).
# GOI THANG research/exitfit/exit_engine.py (harness PARITY PASS). KHONG chay Java/sim o day.
import base64, glob, json, os, sys, time
_F = json.loads(base64.b64decode("__FILES_B64__").decode())
for rel, src in _F.items():
    p = os.path.join("/kaggle/working", rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(src)
print("CODE_FILES", {k: len(v) for k, v in _F.items()}, flush=True)

# ---- tim input ----
S1 = PIN = MAP = None
_tick = []
for b, d, fs in os.walk("/kaggle/input", followlinks=True):
    for fn in fs:
        p = os.path.join(b, fn)
        if fn == "ofi_ext_trades.parquet": S1 = p
        elif fn == "exchange_info_pin.json": PIN = p
        elif fn == "symbol_map.csv": MAP = p
        elif fn.startswith("ticker_") and (fn.endswith(".bin") or fn.endswith(".bin.gz")):
            _tick.append(p)
assert S1 and PIN and MAP and _tick, (S1, PIN, MAP, len(_tick))
_tick.sort()
TD = "/kaggle/working/tick"
os.makedirs(TD, exist_ok=True)
for p in _tick:
    dst = os.path.join(TD, os.path.basename(p))
    if not os.path.exists(dst):
        os.symlink(p, dst)
print("TICKER n=%d %s .. %s | dirs=%d" % (len(_tick), os.path.basename(_tick[0]),
      os.path.basename(_tick[-1]), len(set(os.path.dirname(x) for x in _tick))), flush=True)
print("CAND_FILE", S1, flush=True)

os.environ.update(dict(
    S1_PARQUET=S1, TICKER_DIR=TD, MAP_CSV=MAP, EXITFIT_PIN=PIN,
    OUT_DIR="/kaggle/working/mrout", EXITFIT_OUT="/kaggle/working/mrout/exitfit",
    KMAX="64", CHUNK_DAYS="90", MAX_INTERVAL_SEC="7200",
    TS_MAX_MS="1758992400000",   # 2025-10-01 00:00 GMT+7 (giong kernel mr-labelb-cpu)
))
_t = time.time()
_src = open("/kaggle/working/mrcode/research/pipeline/mr_label_build.py").read()
exec(compile(_src, "/kaggle/working/mrcode/research/pipeline/mr_label_build.py", "exec"),
     {"__name__": "__main__", "__file__": "/kaggle/working/mrcode/research/pipeline/mr_label_build.py"})
print("OFI_EXT_LABELB_DONE min=%.1f" % ((time.time() - _t) / 60), flush=True)
for f in sorted(glob.glob("/kaggle/working/mrout/*")):
    print("OUT", os.path.basename(f), os.path.getsize(f), flush=True)
'''


def main():
    fset = {dst: open(os.path.join(REPO, rel)).read() for rel, dst in FILES}
    fb = base64.b64encode(json.dumps(fset).encode()).decode()
    d1 = os.path.join(DST, "ofi-ext-labelb-cpu")
    os.makedirs(d1, exist_ok=True)
    src = KERNEL.replace("__FILES_B64__", fb)
    open(os.path.join(d1, "ofi_ext_labelb_cpu.py"), "w").write(src)
    json.dump({"id": "chuyendinh/ofi-ext-labelb-cpu", "title": "ofi-ext-labelb-cpu",
               "code_file": "ofi_ext_labelb_cpu.py", "language": "python",
               "kernel_type": "script", "is_private": True, "enable_gpu": False,
               "enable_tpu": False, "enable_internet": False, "keywords": [],
               "dataset_sources": ["chuyendinh/money-ranker-inputs"] + TICKER_DS + FEAT_DS + EXT_DS,
               "kernel_sources": [], "competition_sources": [], "model_sources": []},
              open(os.path.join(d1, "kernel-metadata.json"), "w"), indent=1)
    print("wrote %s (%d B)" % (d1, len(src)))


if __name__ == "__main__":
    main()
