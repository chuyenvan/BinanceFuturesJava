#!/usr/bin/env python3
"""make_mr_kernels.py — sinh 2 kernel Kaggle cho PREREG_MONEY_RANKER (KHONG push o day).

  mr-labelb-cpu : BUOC NANG #1 = build NHAN (b) (PnL that theo luat thoat) — CPU, 12h.
  mr-train-gpu  : BUOC NANG #2 = train 4 bien the ranker (a/4h, a/72h, b/K8, b/K32) — GPU.

Code repo duoc nhung base64 (dung nguyen ban trong repo) de kernel chay DUNG code da commit.
"""
import base64
import json
import os

REPO = "/home/ubuntu/src/BinanceFuturesJava"
DST = "/home/ubuntu/kaggle_sim"
FILES = [
    ("research/pipeline/mr_label_build.py", "mrcode/research/pipeline/mr_label_build.py"),
    ("research/analysis/jbin.py", "mrcode/research/analysis/jbin.py"),
    ("research/exitfit/exit_engine.py", "mrcode/research/exitfit/exit_engine.py"),
]
TRAINER = ("research/pipeline/g015_net_train_add.py", "mrcode/research/pipeline/g015_net_train_add.py")

TICKER_DS = ["chuyendinh/wfo-ticker-2021", "chuyendinh/wfo-ticker-2022",
             "chuyendinh/wfo-ticker-2023", "chuyendinh/wfo-ticker-2024h1",
             "chuyendinh/wfo-ticker-2024h2", "chuyendinh/wfo-ticker-2025h1",
             "chuyendinh/wfo-ticker-2025h2"]
FEAT_DS = ["chuyendinh/funding-tool1-15m", "chuyendinh/funding-label-15m",
           "chuyendinh/funding-oi-percoin", "chuyendinh/sel1m-code"]


def b64(p):
    return base64.b64encode(open(os.path.join(REPO, p), "rb").read()).decode()


LABEL_KERNEL = '''# KERNEL: mr-labelb-cpu (sinh boi research/kaggle/money_ranker/make_mr_kernels.py)
# BUOC NANG: build NHAN (b) = PnL THAT theo luat thoat (PREREG_MONEY_RANKER §4). CPU-only.
# GOI THANG research/exitfit/exit_engine.py (harness da PARITY PASS). KHONG chay Java/sim o day.
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
        if fn == "pred_s1a2x1.parquet": S1 = p
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

os.environ.update(dict(
    S1_PARQUET=S1, TICKER_DIR=TD, MAP_CSV=MAP, EXITFIT_PIN=PIN,
    OUT_DIR="/kaggle/working/mrout", EXITFIT_OUT="/kaggle/working/mrout/exitfit",
    KMAX="32", CHUNK_DAYS="90", MAX_INTERVAL_SEC="7200",
    TS_MAX_MS="1758992400000",   # 2025-10-01 00:00 GMT+7 (= tr_cut fold cuoi + purge)
))
_t = time.time()
_src = open("/kaggle/working/mrcode/research/pipeline/mr_label_build.py").read()
exec(compile(_src, "/kaggle/working/mrcode/research/pipeline/mr_label_build.py", "exec"),
     {"__name__": "__main__", "__file__": "/kaggle/working/mrcode/research/pipeline/mr_label_build.py"})
print("MR_LABELB_KERNEL_DONE min=%.1f" % ((time.time() - _t) / 60), flush=True)
for f in sorted(glob.glob("/kaggle/working/mrout/*")):
    print("OUT", os.path.basename(f), os.path.getsize(f), flush=True)
'''


TRAIN_KERNEL = '''# KERNEL: mr-train-gpu (sinh boi research/kaggle/money_ranker/make_mr_kernels.py)
# BUOC NANG: train 4 bien the ranker (PREREG_MONEY_RANKER §5) tren 45 feature, fold DEV.
#  MRA4  = nhan (a) y = retEnd_4h  LIEN TUC (XGBRegressor)
#  MRA72 = nhan (a) y = retEnd_72h LIEN TUC
#  MRB8  = nhan (b) PnL that, pool top-8  (--label-custom)
#  MRB32 = nhan (b) PnL that, pool top-32 (--label-custom)
import base64, glob, json, os, sys, time
_F = json.loads(base64.b64decode("__FILES_B64__").decode())
for rel, src in _F.items():
    p = os.path.join("/kaggle/working", rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(src)
print("CODE_FILES", {k: len(v) for k, v in _F.items()}, flush=True)
_CUST = {}
_feat, _lab, _oi, _map, _code = [], [], None, None, None
for b, d, fs in os.walk("/kaggle/input", followlinks=True):
    for fn in fs:
        p = os.path.join(b, fn)
        if fn.startswith("features_") and (".t1c" in fn or ".bin" in fn):
            if "15m" in p: _feat.append(p)
        elif fn.startswith("funding_label_") and fn.endswith(".pb"): _lab.append(p)
        elif fn == "oi_percoin_full.bin": _oi = p
        elif fn == "symbol_map.csv": _map = p
        elif fn == "tool1_col.py": _code = b
        elif fn in ("label_b_K8.parquet", "label_b_K32.parquet"): _CUST[fn] = p
assert _feat and _lab and _oi and _map and _code, (len(_feat), len(_lab), _oi, _map, _code)
_feat.sort(); _lab.sort()
os.environ.update(dict(T1_DIR=os.path.dirname(_feat[0]), LB_DIR=os.path.dirname(_lab[0]),
                       OI_FILE=_oi, MAP_CSV=_map, SEL1M_CODE=_code))
print("FEAT15:", len(_feat), "| LABEL:", len(_lab), "| CUSTOM:", sorted(_CUST), flush=True)

_TP = "/kaggle/working/mrcode/research/pipeline/g015_net_train_add.py"
_SRC = open(_TP).read()
print("trainer sha256:", __import__("hashlib").sha256(_SRC.encode()).hexdigest(), flush=True)

FOLDS16 = "20220101,20220401,20220701,20221001,20230101,20230401,20230701,20231001,20240101,20240401,20240701,20241001,20250101,20250401,20250701,20251001"
FOLDS15 = ",".join(FOLDS16.split(",")[1:])
OUT = "/kaggle/working/mr"
__RUNS__
_rep = {}
for tag, extra, folds in RUNS:
    if extra[1] == "" and extra[0] == "--label-custom":
        print("SKIP %s (khong co nhan custom)" % tag, flush=True); continue
    ns = {"__name__": "trainer_mod", "__file__": _TP}
    _O = "/kaggle/working/ownout"
    os.makedirs(_O, exist_ok=True)
    sys.argv = ["g015_net_train_add.py", "--fold", folds, "--device", "cuda", "--save-model",
                "--out-dir", _O, "--scratch", "/tmp", "--njobs", "-1", "--seed", "42"] + extra
    t0 = time.time()
    exec(compile(_SRC, _TP, "exec"), ns)
    ns["main"]()
    _rep[tag] = {"minutes": round((time.time() - t0) / 60, 1), "folds": folds,
                 "argv_extra": extra, "out_dir": _O}
    # chuyen bins + model + summary sang thu muc rieng cua tag
    _D = os.path.join(OUT, tag); os.makedirs(_D, exist_ok=True)
    for p in glob.glob(os.path.join(_O, "predict_wf_*.bin")) + glob.glob(os.path.join(_O, "model_*.json")) + \
             glob.glob(os.path.join(_O, "net_train_summary.json")):
        os.replace(p, os.path.join(_D, os.path.basename(p)))
    _s = json.load(open(os.path.join(_D, "net_train_summary.json")))
    _rep[tag]["objective"] = _s["objective"]; _rep[tag]["label_kind"] = _s["label_kind"]
    _rep[tag]["n_oos"] = {k: v["n_oos"] for k, v in _s["folds"].items()}
    _rep[tag]["n_train"] = {k: v["n_train"] for k, v in _s["folds"].items()}
    _rep[tag]["sha_bin"] = {k: v["sha_bin"] for k, v in _s["folds"].items()}
    print("RUN %s DONE %.1f phut objective=%s" % (tag, _rep[tag]["minutes"], _s["objective"]), flush=True)
json.dump(_rep, open("/kaggle/working/mr_train_report.json", "w"), indent=1)
print("MR_TRAIN_DONE " + json.dumps({k: v["minutes"] for k, v in _rep.items()}), flush=True)
'''


def main():
    os.makedirs(DST, exist_ok=True)
    fset = {}
    for rel, dst in FILES:
        fset[dst] = open(os.path.join(REPO, rel)).read()
    fb = base64.b64encode(json.dumps(fset).encode()).decode()
    d1 = os.path.join(DST, "mr-labelb-cpu")
    os.makedirs(d1, exist_ok=True)
    open(os.path.join(d1, "mr_labelb_cpu.py"), "w").write(LABEL_KERNEL.replace("__FILES_B64__", fb))
    json.dump({"id": "chuyendinh/mr-labelb-cpu", "title": "mr-labelb-cpu",
               "code_file": "mr_labelb_cpu.py", "language": "python", "kernel_type": "script",
               "is_private": True, "enable_gpu": False, "enable_tpu": False,
               "enable_internet": False, "keywords": [],
               "dataset_sources": ["chuyendinh/money-ranker-inputs"] + TICKER_DS + FEAT_DS,
               "kernel_sources": [], "competition_sources": [], "model_sources": []},
              open(os.path.join(d1, "kernel-metadata.json"), "w"), indent=1)

    fset2 = {dst: open(os.path.join(REPO, rel)).read() for rel, dst in [TRAINER]}
    fb2 = base64.b64encode(json.dumps(fset2).encode()).decode()
    for suffix, runs, extra_ds in (
            ("a", 'RUNS = [("MRA4", ["--label-kind", "cont", "--label-h", "4"], FOLDS16),\n'
                  '        ("MRA72", ["--label-kind", "cont", "--label-h", "72"], FOLDS16)]', []),
            ("b", 'RUNS = [("MRB8", ["--label-custom", _CUST.get("label_b_K8.parquet", ""), '
                  '"--label-h", "4", "--min-train", "2000"], FOLDS15),\n'
                  '        ("MRB32", ["--label-custom", _CUST.get("label_b_K32.parquet", ""), '
                  '"--label-h", "4", "--min-train", "2000"], FOLDS15)]',
             ["chuyendinh/money-ranker-labels"])):
        d2 = os.path.join(DST, "mr-train-%s-gpu" % suffix)
        os.makedirs(d2, exist_ok=True)
        src = TRAIN_KERNEL.replace("__FILES_B64__", fb2).replace("__RUNS__", runs)
        open(os.path.join(d2, "mr_train_%s_gpu.py" % suffix), "w").write(src)
        json.dump({"id": "chuyendinh/mr-train-%s-gpu" % suffix,
                   "title": "mr-train-%s-gpu" % suffix,
                   "code_file": "mr_train_%s_gpu.py" % suffix, "language": "python",
                   "kernel_type": "script", "is_private": True, "enable_gpu": True,
                   "enable_tpu": False, "enable_internet": False, "keywords": ["gpu"],
                   "dataset_sources": FEAT_DS + extra_ds,
                   "kernel_sources": [], "competition_sources": [], "model_sources": []},
                  open(os.path.join(d2, "kernel-metadata.json"), "w"), indent=1)
        print("wrote %s (%d B)" % (d2, len(src)))


if __name__ == "__main__":
    main()
