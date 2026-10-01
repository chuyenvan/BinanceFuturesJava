#!/usr/bin/env python3
"""make_sm_pw_kernels.py — sinh 1 kernel Kaggle cho PREREG_SHORT_PATHEXIT_PSOFT.

  sm-pw: train nhan P-SOFT (TRONG SO, KHONG xoa dong) `PW_t15_E10` seed{42,7,13}
         (`--label-mode pw --thr 1,5% --label-e +10%`) tren NGUYEN ma tran 45 feature selector
         (NEST=400), 16 fold. GIU `predict_wf_*.bin` (slot 3 = head 72h) de TAI VE do bang
         thoat-theo-duong-gia 1m (khong push du lieu). KHONG chay scoring in-kernel.

KHAC sm-pathexit: nhan P-SOFT (giu MOI dong, trong so) thay vi P-hard (xoa dong); 3 seed.
"""
import base64
import json
import os

REPO = "/home/ubuntu/src/BinanceFuturesJava"
DST = "/home/ubuntu/kaggle_sim"
EMBED = [
    ("research/pipeline/g015_net_train_add.py", "smcode/research/pipeline/g015_net_train_add.py"),
]
FEAT_DS = ["chuyendinh/funding-tool1-15m", "chuyendinh/funding-label-15m",
           "chuyendinh/funding-oi-percoin", "chuyendinh/sel1m-code"]

_KHEAD = '''# KERNEL: __KNAME__ (sinh boi research/kaggle/short_model/make_sm_pw_kernels.py)
# PREREG_SHORT_PATHEXIT_PSOFT: train 3 arm P-soft (PW_t15_E10_S42/S7/S13), GIU bins.
import base64, glob, json, os, sys, time
_F = json.loads(base64.b64decode("__FILES_B64__").decode())
for rel, src in _F.items():
    p = os.path.join("/kaggle/working", rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(src)
print("CODE_FILES", {k: len(v) for k, v in _F.items()}, flush=True)

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
RUNS = __RUNS__

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
    def _cached_ll(mode, thr, hi_ms, e=float("inf"), _real=_real_ll, _c=CACHE):
        k = ("L", mode, round(float(thr), 5), round(float(e), 5))
        if k not in _c:
            _c[k] = _real(mode, thr, hi_ms, e)
        return _c[k]
    ns["load_labels"] = _cached_ll
    _O = os.path.join(OUT, tag); os.makedirs(_O, exist_ok=True)
    sys.argv = ["g015_net_train_add.py", "--fold", FOLDS16, "--device", "cuda",
                "--out-dir", _O, "--scratch", "/tmp", "--njobs", "-1", "--seed", str(seed),
                "--keep-scratch"] + extra
    t0 = time.time()
    ns["main"]()
    _s = json.load(open(os.path.join(_O, "net_train_summary.json")))
    print("RUN %s DONE %.1f phut mode=%s thr=%s e=%s" % (tag, (time.time()-t0)/60,
          _s["label_mode"], _s["thr"], _s.get("label_e")), flush=True)
    del ns
    import gc; gc.collect()

# KHONG xoa bins (khac sm-label2): bin can cho do thoat duong gia o nha.
nb = 0
for f in glob.glob(OUT + "/**/*.bin", recursive=True):
    nb += os.path.getsize(f)
print("BINS_TOTAL_BYTES", nb, flush=True)
print("OUT_JSONS", [os.path.basename(f) for f in glob.glob(OUT + "/**/*.json", recursive=True)][:6], flush=True)
'''


def _mk(name, desc, runs):
    d = os.path.join(DST, name)
    os.makedirs(d, exist_ok=True)
    kernel = (_KHEAD.replace("__KNAME__", name.replace("-", "_"))
                    .replace("__KDESC__", desc)
                    .replace("__RUNS__", json.dumps(runs, indent=4)))
    fset = {dst: open(os.path.join(REPO, rel)).read() for rel, dst in EMBED}
    fb = base64.b64encode(json.dumps(fset).encode()).decode()
    kernel = kernel.replace("__FILES_B64__", fb)
    open(os.path.join(d, name.replace("-", "_") + ".py"), "w").write(kernel)
    json.dump({"id": "chuyendinh/" + name, "title": name,
               "code_file": name.replace("-", "_") + ".py", "language": "python",
               "kernel_type": "script", "is_private": True, "enable_gpu": True,
               "enable_tpu": False, "enable_internet": False, "keywords": ["gpu"],
               "dataset_sources": FEAT_DS, "kernel_sources": [],
               "competition_sources": [], "model_sources": []},
              open(os.path.join(d, "kernel-metadata.json"), "w"), indent=1)
    print("wrote %s (%d arm)" % (d, len(runs)))


def main():
    os.makedirs(DST, exist_ok=True)
    pw = ["--label-mode", "pw", "--label-h", "72", "--thr", "0.015",
          "--label-e", "0.100", "--label-kind", "bin"]
    runs = [["PW_t15_E10_S42", pw, 42], ["PW_t15_E10_S7", pw, 7],
            ["PW_t15_E10_S13", pw, 13]]
    _mk("sm-pw", "PSOFT: PW_t15_E10 s{42,7,13} (nhan trong so, giu moi dong), GIU bins", runs)


if __name__ == "__main__":
    main()
