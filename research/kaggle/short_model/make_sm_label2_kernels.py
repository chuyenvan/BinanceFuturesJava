#!/usr/bin/env python3
"""make_sm_label2_kernels.py — sinh 2 kernel Kaggle cho PREREG_SHORT_LABEL2 (KHONG push o day).

  sm-label2  : BUOC NANG = train nhan PATH-AWARE P-hard (`--label-mode pa`, y=1[retEnd_72h<=-thr &
               maxFav_72h<=E]) tren NGUYEN ma tran 45 feature selector: thr{1,5%,7%} x E{+3%,+10%}
               x seed{42,7,13} = 12 arm; roi CHAM in-kernel (rank-IC/cut-rate/cat cung/CI/nam).
  sm-label2b : doi chieu (b) TRONG SO `pw` va (c) NOISE `pn` tai (thr=1,5%, E=+10%) x 3 seed = 6 arm.

Code repo duoc nhung base64 (dung nguyen ban da commit). Ma tran build 1 LAN (cache) + nhan cache
theo (mode,thr,E) -> tiet kiem GPU. KHONG --save-model. Xoa bins sau khi cham -> output nho.
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

_KHEAD = '''# KERNEL: __KNAME__ (sinh boi research/kaggle/short_model/make_sm_label2_kernels.py)
# PREREG_SHORT_LABEL2: __KDESC__
# KHONG chay Java/sim o day. Ma tran build 1 lan (cache).
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
    _REP[tag] = {"minutes": round((time.time() - t0) / 60, 1), "seed": seed, "argv": extra,
                 "objective": _s["objective"], "label_mode": _s["label_mode"], "thr": _s["thr"],
                 "label_e": _s.get("label_e"), "n_oos": _s["folds"][list(_s["folds"])[0]]["n_oos"],
                 "n_train": _s["folds"][list(_s["folds"])[0]]["n_train"],
                 "pos": _s["folds"][list(_s["folds"])[0]]["pos"]}
    print("RUN %s DONE %.1f phut mode=%s thr=%s e=%s" % (tag, _REP[tag]["minutes"],
          _s["label_mode"], _s["thr"], _s.get("label_e")), flush=True)
    del ns
    import gc; gc.collect()
json.dump(_REP, open("/kaggle/working/__KNAME___report.json", "w"), indent=1)
print("__KNAME___TRAIN_DONE " + json.dumps({k: v["minutes"] for k, v in _REP.items()}), flush=True)

_arms = ",".join("%s:%s:%s" % (r[0], r[0], "short") for r in RUNS)
os.system("python3 /kaggle/working/smcode/research/analysis/short_model_score.py "
          "--bins-root %s --arms %s --map-csv %s --labels-dir %s --cuts 0.20,0.30,0.50,0.90 "
          "--out /kaggle/working/__KNAME___score.json" % (OUT, _arms, _map, os.path.dirname(_lab[0])))
print("__KNAME___SCORE_DONE", flush=True)

# DON output: xoa bins/model (khong push du lieu) -> chi con JSON nho
import shutil
try:
    shutil.rmtree(OUT)
    print("CLEANED bins", flush=True)
except Exception as e:
    print("CLEAN_ERR", e, flush=True)
for f in sorted(glob.glob("/kaggle/working/*.json")):
    print("OUT", os.path.basename(f), os.path.getsize(f), flush=True)
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
    seeds = [42, 7, 13]
    main_grid = [("PA_t15_E3", 0.015, 0.03), ("PA_t15_E10", 0.015, 0.10),
                 ("PA_t70_E3", 0.070, 0.03), ("PA_t70_E10", 0.070, 0.10)]
    runs_a = []
    for nm, thr, e in main_grid:
        for s in seeds:
            runs_a.append(["%s_S%d" % (nm, s),
                           ["--label-mode", "pa", "--label-h", "72", "--thr", "%.3f" % thr,
                            "--label-e", "%.3f" % e, "--label-kind", "bin"], s])
    _mk("sm-label2", "P-hard pa thr{1.5,7%} x E{3,10%} x seed{42,7,13} = 12 arm", runs_a)

    ctrl = [("PW_t15_E10", "pw", 0.015, 0.10), ("PN_t15_E10", "pn", 0.015, 0.10)]
    runs_b = []
    for nm, mode, thr, e in ctrl:
        for s in seeds:
            runs_b.append(["%s_S%d" % (nm, s),
                           ["--label-mode", mode, "--label-h", "72", "--thr", "%.3f" % thr,
                            "--label-e", "%.3f" % e, "--label-kind", "bin"], s])
    _mk("sm-label2b", "control pw(weight) + pn(noise) at thr=1.5%, E=10% x seed{42,7,13} = 6 arm",
        runs_b)


if __name__ == "__main__":
    main()
