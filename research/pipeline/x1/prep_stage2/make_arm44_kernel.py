#!/usr/bin/env python3
"""make_arm44_kernel.py — dung kernel Kaggle TRAIN cho vong ARM44 (docs/prereg/PREREG_ARM44.md).

Khong train o day. Chi ghep 1 kernel Kaggle tu:
  (1) shim tim input (KHONG co prefeat: vong nay khong them cot),
  (2) toan bo `research/pipeline/g015_net_train_add.py` (base64, chay NGUYEN BAN, KHONG --add-feats
      => NF=45, hanh vi goc),
  (3) TRAIN 2 arm tren CUNG mot lan dung ma trận: `A45:` (control, 45 cot) + `A44:36` (bo dung cot 36
      = rvol15m) => trainer tu in CROSS_ARM_OK / CROSS_ARM_MISMATCH,
  (4) buoc DO metric OOS TRONG KERNEL (rank-IC cross-section + top-8 lift theo tung tick) cho CA HAI arm
      -> chi tai ve duoi dang parquet NHO (~30 MB/arm), KHONG tai bins (~0,93 GB/arm).

ARMS doc tu `research/pipeline/featuresets/fs_v1_44.json` (khoa `stage2.drop_cols_arg`) => KHONG go tay.
16 fold DEV (khong cham 2026/HoldoutSeal). Pre-reg: docs/prereg/PREREG_ARM44.md (commit 7eb4c2b).

Dung:
  python3 make_arm44_kernel.py <out_dir>
  cd <out_dir> && kaggle kernels push -p .
"""
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
TRAINER = os.path.join(REPO, "research", "pipeline", "g015_net_train_add.py")
FS_FILE = os.path.join(REPO, "research", "pipeline", "featuresets", "fs_v1_44.json")
SLUG = "g015p2-arm44-gpu"

FOLDS = ["20220101", "20220401", "20220701", "20221001", "20230101", "20230401", "20230701",
         "20231001", "20240101", "20240401", "20240701", "20241001", "20250101", "20250401",
         "20250701", "20251001"]

TEMPLATE = r'''# KERNEL: @SLUG@ -- vong ARM44: train A45 (control) + A44 (bo dung cot 36 rvol15m).
# Pre-reg: docs/prereg/PREREG_ARM44.md (commit 7eb4c2b). 16 fold DEV 20220101..20251001.
# KHONG cham 2026/HoldoutSeal. KHONG cham ONNX/NUM_FEATURES/LIVE. KHONG sim.
import os as _os, sys as _sys, json, hashlib, base64, time, glob as _glob
import numpy as np, pandas as pd

_ROOT = "/kaggle/input"
_feat15, _labels, _oi, _map, _code = [], [], None, None, None
for _b, _d, _fs in _os.walk(_ROOT, followlinks=True):
    for _fn in _fs:
        _p = _os.path.join(_b, _fn)
        if _fn.startswith("features_") and (".t1c" in _fn or ".bin" in _fn):
            if "15m" in _p:
                _feat15.append(_p)
        elif _fn.startswith("funding_label_") and _fn.endswith(".pb"):
            _labels.append(_p)
        elif _fn == "oi_percoin_full.bin":
            _oi = _p
        elif _fn == "symbol_map.csv":
            _map = _p
        elif _fn == "tool1_col.py":
            _code = _b
assert _feat15 and _labels and _oi and _map and _code, (len(_feat15), len(_labels), _oi, _map, _code)
_feat15.sort(); _labels.sort()
_os.environ["T1_DIR"] = _os.path.dirname(_feat15[0])
_os.environ["LB_DIR"] = _os.path.dirname(_labels[0])
_os.environ["OI_FILE"] = _oi
_os.environ["MAP_CSV"] = _map
_os.environ["SEL1M_CODE"] = _code
print("FEAT15:", len(_feat15), "| LABEL:", len(_labels), "| OI:", _oi, flush=True)

_SRC = base64.b64decode("@B64@").decode()
_TP = "/kaggle/working/g015_net_train_add.py"
open(_TP, "w").write(_SRC)
print("trainer sha256:", hashlib.sha256(_SRC.encode()).hexdigest(), flush=True)
_NS = {"__name__": "trainer_mod", "__file__": _TP}
exec(compile(_SRC, _TP, "exec"), _NS)

FOLDS = "@FOLDS@".split(",")
ARMS = "@ARMS@"
TAGS = [a.split(":")[0] for a in ARMS.split(";")]
OUT = "/kaggle/working/stage2"
_os.makedirs(OUT, exist_ok=True)

# ---------------- (1) TRAIN 2 ARM x 16 FOLD (mot lan dung ma tran) ----------------
_sys.argv = ["g015_net_train_add.py", "--fold", ",".join(FOLDS), "--device", "cuda",
             "--save-model", "--out-root", OUT, "--scratch", "/tmp", "--njobs", "-1",
             "--seed", "42", "--arms", ARMS]
_t0 = time.time()
_NS["main"]()
print("TRAIN_MINUTES %.1f" % ((time.time() - _t0) / 60), flush=True)
_SUM = json.load(open(_os.path.join(OUT, "stage2_summary.json")))
print("CROSS_ARM " + json.dumps({k: v for k, v in _SUM["cross_arm"].items() if k != "add_hits"}),
      flush=True)
print("CROSS_ARM_OK " + json.dumps(_SUM["cross_arm"]["mismatch"] == {}), flush=True)
_NF = {t: _SUM["arms"][t]["num_feature"] for t in TAGS}
print("NUM_FEATURE " + json.dumps(_NF), flush=True)

# ---------------- (2) DO METRIC OOS THEO TUNG TICK (rank-IC + top-8 lift) ----------------
# GIONG NGUYEN doan do cua research/pipeline/x1/prep_stage2/make_stage2_kernel.py (Stage 2).
import funding_label_pb as FLPB
_smap = pd.read_csv(_map)
_s2i = dict(zip(_smap.symbol, _smap.symId.astype(np.int32)))
_fs = sorted(f for f in _os.listdir(_os.environ["LB_DIR"])
             if f.startswith("funding_label_") and f.endswith(".pb") and f.split("_")[2] < "20260101")
_tl, _sl, _vl = [], [], []
for _fn in _fs:
    _d = FLPB.read_label(_os.path.join(_os.environ["LB_DIR"], _fn),
                         usecols=["tEpochMs", "symbol", "retEnd_4h"])
    _sid = _d.symbol.map(_s2i)
    _k = _sid.notna().to_numpy()
    _ts = _d.tEpochMs.to_numpy(np.int64)[_k]
    _v = _d.retEnd_4h.to_numpy(np.float64)[_k]
    _ok = np.isfinite(_v)
    _sv = _sid.to_numpy()[_k]
    _tl.append(_ts[_ok]); _sl.append(_sv[_ok].astype(np.int32)); _vl.append(_v[_ok])
    del _d
_tl = np.concatenate(_tl); _sl = np.concatenate(_sl); _vl = np.concatenate(_vl)
_ord = np.argsort(_tl * 1024 + _sl, kind="stable")
_LK = (_tl * 1024 + _sl)[_ord]; _LV = _vl[_ord]
del _tl, _sl, _vl, _ord
print("label rows (retEnd_4h notna):", len(_LK), flush=True)

BIN_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p", ">f4"), ("z", ">f4", 3)])
THR = 0.015
res = {}
for _tag in TAGS:
    _rows = []
    for _f in FOLDS:
        _bp = _os.path.join(OUT, _tag, "predict_wf_%s.bin" % _f)
        _a = np.fromfile(_bp, dtype=BIN_DT)
        _ts = _a["ts"].astype(np.int64); _sy = _a["sym"].astype(np.int64); _p = _a["p"].astype(np.float32)
        _key = _ts * 1024 + _sy
        _ip = np.clip(np.searchsorted(_LK, _key), 0, len(_LK) - 1)
        _hit = _LK[_ip] == _key
        _y = np.full(len(_key), np.nan)
        _y[_hit] = _LV[_ip[_hit]]
        _m = np.isfinite(_y)
        _d = pd.DataFrame({"ts": _ts[_m], "p": _p[_m], "y": _y[_m]})
        _nn = _d.groupby("ts").size()
        _d["_g"] = _d["ts"].map(_nn)
        _d = _d[_d["_g"] >= 2]
        _r1 = _d.groupby("ts")["p"].rank(method="average")
        _r2 = _d.groupby("ts")["y"].rank(method="average")
        _m1 = _r1.groupby(_d.ts).transform("mean"); _m2 = _r2.groupby(_d.ts).transform("mean")
        _num = ((_r1 - _m1) * (_r2 - _m2)).groupby(_d.ts).sum()
        _ss1 = ((_r1 - _m1) ** 2).groupby(_d.ts).sum(); _ss2 = ((_r2 - _m2) ** 2).groupby(_d.ts).sum()
        _ic = _num / np.sqrt(_ss1 * _ss2).replace(0, np.nan)
        _d["hit"] = (_d.y > THR).astype(float)
        _base = _d.groupby("ts")["hit"].mean()
        _top = _d.sort_values(["ts", "p"], ascending=[True, False]).groupby("ts").head(8)
        _t8 = _top.groupby("ts")["hit"].mean()
        _n8 = _top.groupby("ts").size()
        _n = _d.groupby("ts").size()
        _r = pd.DataFrame({"ic": _ic, "base": _base, "t8": _t8, "n8": _n8, "n_coin": _n})
        _r["lift8"] = _r["t8"] - _r["base"]
        _r["fold"] = _f
        _rows.append(_r.reset_index())
        del _a, _d, _r
    _A = pd.concat(_rows, ignore_index=True)
    _A.to_parquet(_os.path.join(OUT, "%s_perfold_ticks.parquet" % _tag), index=False)
    _g = _A.groupby("fold")
    res[_tag] = {"n_tick": int(len(_A)), "ic_mean": float(_A.ic.mean()),
                 "lift8_mean": float(_A.lift8.mean()),
                 "ic_by_fold": {k: float(v) for k, v in _g["ic"].mean().items()},
                 "lift8_by_fold": {k: float(v) for k, v in _g["lift8"].mean().items()}}
    print("METRIC %s n_tick=%d ic=%.6f lift8=%.6f" % (_tag, len(_A), res[_tag]["ic_mean"],
                                                      res[_tag]["lift8_mean"]), flush=True)
    del _A
json.dump(res, open(_os.path.join(OUT, "arm44_metrics.json"), "w"), indent=1)

# ---------------- (3) bao cao NHO + don file lon khong can ----------------
_folds_check = {f: {t: {k: _SUM["arms"][t]["folds"][f][k] for k in ("fold_idx", "n_train", "pos",
                                                                     "spw", "n_oos", "p_mean", "p_std",
                                                                     "sha_bin")} for t in TAGS}
                for f in FOLDS}
_rep = {"pre_reg": "docs/prereg/PREREG_ARM44.md", "trainer_sha256":
        hashlib.sha256(_SRC.encode()).hexdigest(), "tags": TAGS, "num_feature": _NF,
        "cross_arm_ok": _SUM["cross_arm"]["mismatch"] == {},
        "cross_arm_mismatch": _SUM["cross_arm"]["mismatch"],
        "metrics": res, "folds": _folds_check,
        "minutes_total": round((time.time() - _t0) / 60, 1)}
json.dump(_rep, open("/kaggle/working/arm44_train_report.json", "w"), indent=1)
du = _os.popen("du -sm /kaggle/working").read().split()[0]
print("ARM44_DONE ok=%s num_feature=%s min=%.1f work=%sMB" % (
    _rep["cross_arm_ok"], _NF, _rep["minutes_total"], du), flush=True)
'''

META = {
    "id": "chuyendinh/%s" % SLUG,
    "title": SLUG,
    "code_file": "%s.py" % SLUG,
    "language": "python",
    "kernel_type": "script",
    "is_private": True,
    "enable_gpu": True,
    "enable_tpu": False,
    "enable_internet": False,
    "keywords": ["gpu"],
    "dataset_sources": ["chuyendinh/funding-tool1-15m", "chuyendinh/funding-label-15m",
                        "chuyendinh/funding-oi-percoin", "chuyendinh/sel1m-code"],
    "kernel_sources": [],
    "competition_sources": [],
    "model_sources": [],
}


def build_arms():
    d = json.load(open(FS_FILE))
    dc = d["stage2"]["drop_cols_arg"]
    assert d["n_features"] == d["stage2"]["so_cot"] == 44, d["n_features"]
    assert dc == "36", dc
    parts = ["A45:", "A44:%s" % dc]           # A45 TRUOC => la base_arm cua CROSS_ARM
    return ";".join(parts)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    arms = build_arms()
    b64 = base64.b64encode(open(TRAINER, "rb").read()).decode()
    src = (TEMPLATE.replace("@SLUG@", SLUG).replace("@B64@", b64)
           .replace("@ARMS@", arms).replace("@FOLDS@", ",".join(FOLDS)))
    assert "@B64@" not in src and "@SLUG@" not in src and "@ARMS@" not in src and "@FOLDS@" not in src
    open(os.path.join(out, "%s.py" % SLUG), "w").write(src)
    json.dump(META, open(os.path.join(out, "kernel-metadata.json"), "w"), indent=2)
    print("wrote", out, "| kernel bytes", len(src))
    print("ARMS:", arms)


if __name__ == "__main__":
    main()
