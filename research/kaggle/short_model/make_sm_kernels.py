#!/usr/bin/env python3
"""make_sm_kernels.py — sinh 1 kernel Kaggle cho PREREG_SHORT_MODEL (KHONG push o day).

  sm-train-gpu : BUOC NANG = train arm SHORT (nhan NGUOC `ndown`, 3 seed) + arm LONG (doi chung
                 guong, 1 seed) tren NGUYEN ma tran 45 feature selector, roi CHAM in-kernel
                 (rank-IC/decile/cat cung/CI) — xuat 1 JSON nho.

Code repo duoc nhung base64 (dung nguyen ban trong repo) de kernel chay DUNG code da commit.
Ma tran 45 feature CHI BUILD 1 LAN (cache `build_matrix` giua cac arm) -> tiet kiem GPU.
"""
import base64
import json
import os

REPO = "/home/ubuntu/src/BinanceFuturesJava"
DST = "/home/ubuntu/kaggle_sim"
EMBED = [
    ("research/pipeline/g015_net_train_add.py", "smcode/research/pipeline/g015_net_train_add.py"),
    ("research/analysis/short_model_score.py", "smcode/research/analysis/short_model_score.py"),
]
FEAT_DS = ["chuyendinh/funding-tool1-15m", "chuyendinh/funding-label-15m",
           "chuyendinh/funding-oi-percoin", "chuyendinh/sel1m-code"]

KERNEL = '''# KERNEL: sm-train-gpu (sinh boi research/kaggle/short_model/make_sm_kernels.py)
# BUOC NANG: PREREG_SHORT_MODEL — train nhan NGUOC (y=1[retEnd_72h<=-0,015]) tren ma tran 45
# feature selector, 3 seed; + arm LONG guong (y=1[retEnd_72h>=+0,015]); roi cham in-kernel.
# KHONG chay Java/sim o day. Ma tran build 1 lan (cache).
import base64, glob, json, os, sys, time
_F = json.loads(base64.b64decode("__FILES_B64__").decode())
for rel, src in _F.items():
    p = os.path.join("/kaggle/working", rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(src)
print("CODE_FILES", {k: len(v) for k, v in _F.items()}, flush=True)

# ---- tim input ----
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
assert _feat and _lab and _oi and _map and _code, (len(_feat), len(_lab), _oi, _map, _code)
_feat.sort(); _lab.sort()
os.environ.update(dict(T1_DIR=os.path.dirname(_feat[0]), LB_DIR=os.path.dirname(_lab[0]),
                       OI_FILE=_oi, MAP_CSV=_map, SEL1M_CODE=_code))
print("FEAT15:", len(_feat), "| LABEL:", len(_lab), flush=True)

_TP = "/kaggle/working/smcode/research/pipeline/g015_net_train_add.py"
_SRC = open(_TP).read()
print("trainer sha256:", __import__("hashlib").sha256(_SRC.encode()).hexdigest(), flush=True)

FOLDS16 = "20220101,20220401,20220701,20221001,20230101,20230401,20230701,20231001,20240101,20240401,20240701,20241001,20250101,20250401,20250701,20251001"
OUT = "/kaggle/working/sm"
SEEDS = [42, 7, 13]
RUNS = [("SHORT%d" % s, ["--label-mode", "ndown", "--label-h", "72", "--thr", "0.015",
                         "--label-kind", "bin"], s) for s in SEEDS]
RUNS += [("LONG42", ["--label-mode", "net", "--label-h", "72", "--thr", "0.015",
                     "--label-kind", "bin"], 42)]

CACHE = {}
_REP = {}
for tag, extra, seed in RUNS:
    ns = {"__name__": "trainer_mod", "__file__": _TP}
    exec(compile(_SRC, _TP, "exec"), ns)
    _real_bm = ns["build_matrix"]
    def _cached_bm(years, scratch, _real=_real_bm, _c=CACHE):
        if "X" not in _c:
            _c["X"], _c["ts"], _c["sym"], _c["mm"] = _real(years, scratch)
        return _c["X"], _c["ts"], _c["sym"], _c["mm"]
    ns["build_matrix"] = _cached_bm
    _real_ll = ns["load_labels"]
    def _cached_ll(mode, thr, hi_ms, _real=_real_ll, _c=CACHE):
        k = ("L", mode)
        if k not in _c:
            _c[k] = _real(mode, thr, hi_ms)
        return _c[k]
    ns["load_labels"] = _cached_ll
    _O = os.path.join(OUT, tag); os.makedirs(_O, exist_ok=True)
    sys.argv = ["g015_net_train_add.py", "--fold", FOLDS16, "--device", "cuda", "--save-model",
                "--out-dir", _O, "--scratch", "/tmp", "--njobs", "-1", "--seed", str(seed),
                "--keep-scratch"] + extra
    t0 = time.time()
    ns["main"]()
    _s = json.load(open(os.path.join(_O, "net_train_summary.json")))
    _REP[tag] = {"minutes": round((time.time() - t0) / 60, 1), "seed": seed, "argv": extra,
                 "objective": _s["objective"], "label_kind": _s["label_kind"],
                 "label_mode": _s["label_mode"], "thr": _s["thr"],
                 "n_oos": {k: v["n_oos"] for k, v in _s["folds"].items()}}
    print("RUN %s DONE %.1f phut obj=%s mode=%s" % (tag, _REP[tag]["minutes"], _s["objective"],
          _s["label_mode"]), flush=True)
    del ns
    import gc; gc.collect()
json.dump(_REP, open("/kaggle/working/sm_train_report.json", "w"), indent=1)
print("SM_TRAIN_DONE " + json.dumps({k: v["minutes"] for k, v in _REP.items()}), flush=True)

# ---- CHAM in-kernel ----
_arms = ",".join("%s:%s:%s" % (r[0], r[0], "short" if r[0].startswith("SHORT") else "long")
                 for r in RUNS)
os.system("python3 /kaggle/working/smcode/research/analysis/short_model_score.py "
          "--bins-root %s --arms %s --map-csv %s --labels-dir %s "
          "--out /kaggle/working/sm_score.json" % (OUT, _arms, _map, os.path.dirname(_lab[0])))
print("SM_SCORE_DONE", flush=True)
for f in sorted(glob.glob("/kaggle/working/*.json")):
    print("OUT", os.path.basename(f), os.path.getsize(f), flush=True)
'''


def main():
    os.makedirs(DST, exist_ok=True)
    fset = {dst: open(os.path.join(REPO, rel)).read() for rel, dst in EMBED}
    fb = base64.b64encode(json.dumps(fset).encode()).decode()
    d = os.path.join(DST, "sm-train-gpu")
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "sm_train_gpu.py"), "w").write(KERNEL.replace("__FILES_B64__", fb))
    json.dump({"id": "chuyendinh/sm-train-gpu", "title": "sm-train-gpu",
               "code_file": "sm_train_gpu.py", "language": "python", "kernel_type": "script",
               "is_private": True, "enable_gpu": True, "enable_tpu": False,
               "enable_internet": False, "keywords": ["gpu"],
               "dataset_sources": FEAT_DS, "kernel_sources": [],
               "competition_sources": [], "model_sources": []},
              open(os.path.join(d, "kernel-metadata.json"), "w"), indent=1)
    print("wrote %s" % d)


if __name__ == "__main__":
    main()
