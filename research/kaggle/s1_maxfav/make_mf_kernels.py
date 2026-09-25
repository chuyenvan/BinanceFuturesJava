#!/usr/bin/env python3
"""make_mf_kernels.py — sinh kernel Kaggle `mf-train-gpu` cho PREREG_S1_MAXFAV (KHONG push o day).

  mf-train-gpu : BUOC NANG = train 3 ung vien nhan ho `maxFav` tren CUNG 45 feature / 16 fold /
                 seed 42 (PREREG_S1_MAXFAV §2,§3) — CHI doi NHAN so voi duong S1 hien hanh.
                   MFC72 = y = maxFav_72h LIEN TUC   (--label-mode maxfav --label-h 72 --label-kind cont)
                   MFB72 = y = (maxFav_72h >= 0.07)  (--label-mode maxfav --label-h 72 --label-kind bin --thr 0.07)
                   MFC4  = y = maxFav_4h  LIEN TUC   (--label-mode maxfav --label-h 4  --label-kind cont)

Code repo duoc nhung base64 (dung nguyen ban trong repo) de kernel chay DUNG code da commit.
"""
import base64
import json
import os

REPO = "/home/ubuntu/src/BinanceFuturesJava"
DST = "/home/ubuntu/kaggle_sim"
TRAINER = ("research/pipeline/g015_net_train_add.py", "mrcode/research/pipeline/g015_net_train_add.py")

FEAT_DS = ["chuyendinh/funding-tool1-15m", "chuyendinh/funding-label-15m",
           "chuyendinh/funding-oi-percoin", "chuyendinh/sel1m-code"]


def b64(p):
    return base64.b64encode(open(os.path.join(REPO, p), "rb").read()).decode()


TRAIN_KERNEL = '''# KERNEL: mf-train-gpu (sinh boi research/kaggle/s1_maxfav/make_mf_kernels.py)
# BUOC NANG: train 3 ung vien NHAN ho `maxFav` (PREREG_S1_MAXFAV §2) tren 45 feature, 16 fold DEV.
#  MFC72 = y = maxFav_72h LIEN TUC  (XGBRegressor)
#  MFB72 = y = (maxFav_72h >= 0.07) (XGBClassifier)
#  MFC4  = y = maxFav_4h  LIEN TUC  (XGBRegressor)
import base64, glob, json, os, sys, time, hashlib
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

_TP = "/kaggle/working/mrcode/research/pipeline/g015_net_train_add.py"
_SRC = open(_TP).read()
print("trainer sha256:", hashlib.sha256(_SRC.encode()).hexdigest(), flush=True)

FOLDS16 = "20220101,20220401,20220701,20221001,20230101,20230401,20230701,20231001,20240101,20240401,20240701,20241001,20250101,20250401,20250701,20251001"
OUT = "/kaggle/working/mf"
RUNS = [
    ("MFC72", ["--label-mode", "maxfav", "--label-h", "72", "--label-kind", "cont"], FOLDS16),
    ("MFB72", ["--label-mode", "maxfav", "--label-h", "72", "--label-kind", "bin", "--thr", "0.07"], FOLDS16),
    ("MFC4", ["--label-mode", "maxfav", "--label-h", "4", "--label-kind", "cont"], FOLDS16),
]
_rep = {}
for tag, extra, folds in RUNS:
    ns = {"__name__": "trainer_mod", "__file__": _TP}
    _O = "/kaggle/working/ownout"
    os.makedirs(_O, exist_ok=True)
    for f in glob.glob(os.path.join(_O, "*")):
        os.remove(f)
    sys.argv = ["g015_net_train_add.py", "--fold", folds, "--device", "cuda", "--save-model",
                "--out-dir", _O, "--scratch", "/tmp", "--njobs", "-1", "--seed", "42"] + extra
    t0 = time.time()
    exec(compile(_SRC, _TP, "exec"), ns)
    ns["main"]()
    _rep[tag] = {"minutes": round((time.time() - t0) / 60, 1), "folds": folds,
                 "argv_extra": extra, "out_dir": _O}
    _D = os.path.join(OUT, tag); os.makedirs(_D, exist_ok=True)
    for p in glob.glob(os.path.join(_O, "predict_wf_*.bin")) + glob.glob(os.path.join(_O, "model_*.json")) + \
             glob.glob(os.path.join(_O, "net_train_summary.json")):
        os.replace(p, os.path.join(_D, os.path.basename(p)))
    _s = json.load(open(os.path.join(_D, "net_train_summary.json")))
    _rep[tag]["objective"] = _s["objective"]; _rep[tag]["label_kind"] = _s["label_kind"]
    _rep[tag]["n_oos"] = {k: v["n_oos"] for k, v in _s["folds"].items()}
    _rep[tag]["n_train"] = {k: v["n_train"] for k, v in _s["folds"].items()}
    _rep[tag]["sha_bin"] = {k: v["sha_bin"] for k, v in _s["folds"].items()}
    print("RUN %s DONE %.1f phut objective=%s label_kind=%s" % (
        tag, _rep[tag]["minutes"], _s["objective"], _s["label_kind"]), flush=True)
json.dump(_rep, open("/kaggle/working/mf_train_report.json", "w"), indent=1)
print("MF_TRAIN_DONE " + json.dumps({k: v["minutes"] for k, v in _rep.items()}), flush=True)
'''


def main():
    os.makedirs(DST, exist_ok=True)
    fset2 = {dst: open(os.path.join(REPO, rel)).read() for rel, dst in [TRAINER]}
    fb2 = base64.b64encode(json.dumps(fset2).encode()).decode()
    d2 = os.path.join(DST, "mf-train-gpu")
    os.makedirs(d2, exist_ok=True)
    src = TRAIN_KERNEL.replace("__FILES_B64__", fb2)
    open(os.path.join(d2, "mf_train_gpu.py"), "w").write(src)
    json.dump({"id": "chuyendinh/mf-train-gpu", "title": "mf-train-gpu",
               "code_file": "mf_train_gpu.py", "language": "python",
               "kernel_type": "script", "is_private": True, "enable_gpu": True,
               "enable_tpu": False, "enable_internet": False, "keywords": ["gpu"],
               "dataset_sources": FEAT_DS,
               "kernel_sources": [], "competition_sources": [], "model_sources": []},
              open(os.path.join(d2, "kernel-metadata.json"), "w"), indent=1)
    print("wrote %s (%d B)" % (d2, len(src)))


if __name__ == "__main__":
    main()
