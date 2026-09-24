#!/usr/bin/env python3
"""make_prep_kernel.py — dung kernel Kaggle cho buoc DE-RISK Stage 2 (S1 45-feature retrain).

KHONG train o day. Script nay chi GHEP 1 kernel Kaggle tu 2 manh co san:
  (1) shim tim input (giong kernel `chuyendinh/g015ablv0-stage0-gpu` da chay 2026-09-08),
  (2) toan bo noi dung `research/pipeline/g015_net_train.py` (base64) de chay NGUYEN BAN.
Kernel do chay 2 arm tren CUNG fold 20240101 (fold 8):
  A45 = 45 cot (khong doi gi)      -> cong tai lap so voi model_f8 goc
  B40 = 40 cot (--drop-cols 9,26,33,37,38) -> chung minh subset hoa chay duoc, khong loi

Dung:
  python3 make_prep_kernel.py <out_dir>      # -> <out_dir>/{<slug>.py,kernel-metadata.json}
  cd <out_dir> && kaggle kernels push -p .   # (KHONG chay o day; can quyen Kaggle)
"""
import base64
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
TRAINER = os.path.join(REPO, "research", "pipeline", "g015_net_train.py")
SLUG = "g015p2-prep-trial-gpu"

TEMPLATE = '''# KERNEL: @SLUG@ -- DE-RISK Stage 2: chung minh duong train S1 (45 feature, net015).
# A45 = retrain day du 45 cot fold 20240101 (cong tai lap vs model_f8 goc);
# B40 = subset 40 cot (--drop-cols 9,26,33,37,38) -> chung minh subset hoa chay duoc.
# Pre-reg lien quan: docs/prereg/PREREG_G015ABL.md, docs/prereg/PREREG_FEAT_ABLATION.md.
import os as _os, sys as _sys, json, hashlib, base64, time, glob as _glob

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
print("FEAT15:", len(_feat15), "@", _os.environ["T1_DIR"], flush=True)
print("LABEL:", len(_labels), "@", _os.environ["LB_DIR"], flush=True)
print("OI:", _oi, "| MAP:", _map, "| CODE:", _code, flush=True)

_SRC = base64.b64decode("@B64@").decode()
_TP = "/kaggle/working/g015_net_train.py"
open(_TP, "w").write(_SRC)
print("trainer sha256:", hashlib.sha256(_SRC.encode()).hexdigest(), flush=True)

_NS = {"__name__": "trainer_mod", "__file__": _TP}
exec(compile(_SRC, _TP, "exec"), _NS)
_main = _NS["main"]

# So THAM CHIEU (deterministic) tu docs/experiment/G015_RECIPE.md muc 3+5 cho fold 8 = 20240101.
REF = {"n_train": 14834006, "pos": 0.1864, "spw": 4.365823, "n_oos": 2140992,
       "p_mean": 0.46416, "p_std": 0.12771,
       "sha_bin_gpu_retrain": "53750a944acdb10594af20a40ae7f64bfe6d4ebdcdcba34cacfb0559ca13931d"}
ARMS = [("A45", "20240101", ""), ("B40", "20240101", "9,26,33,37,38")]
_out = {}
for _tag, _fold, _drop in ARMS:
    _od = "/kaggle/working/%s" % _tag
    _os.makedirs(_od, exist_ok=True)
    _sys.argv = ["g015_net_train.py", "--fold", _fold, "--device", "cuda", "--save-model",
                 "--out-dir", _od, "--scratch", "/tmp", "--njobs", "-1", "--seed", "42",
                 "--drop-cols", _drop]
    _t0 = time.time()
    _main()
    _sp = _os.path.join(_od, "net_train_summary.json")
    _bp = _os.path.join(_od, "predict_wf_%s.bin" % _fold)
    _j = json.load(open(_sp)) if _os.path.exists(_sp) else {}
    _f = (_j.get("folds") or {}).get(_fold, {})
    _rec = {"arm": _tag, "drop_cols": _drop, "num_feature": _j.get("num_feature"),
            "cutoff": _fold, "fold_idx": _f.get("fold_idx"),
            "model_files": [_os.path.basename(x) for x in _glob.glob(_os.path.join(_od, "model_f*_4h.json"))],
            "minutes": round((time.time() - _t0) / 60, 1),
            "bin_exists": _os.path.exists(_bp),
            "n_train": _f.get("n_train"), "pos": _f.get("pos"), "spw": _f.get("spw"),
            "n_oos": _f.get("n_oos"), "p_mean": _f.get("p_mean"), "p_std": _f.get("p_std"),
            "sha_bin": _f.get("sha_bin")}
    if _tag == "A45":
        _rec["repro_n_train_ok"] = (_rec["n_train"] == REF["n_train"])
        _rec["repro_pos_ok"] = (_rec["pos"] == REF["pos"])
        _rec["repro_n_oos_ok"] = (_rec["n_oos"] == REF["n_oos"])
        _rec["sha_matches_gpu_retrain"] = (_rec["sha_bin"] == REF["sha_bin_gpu_retrain"])
    _out[_tag] = _rec
    print("ARM_RESULT " + json.dumps(_rec), flush=True)
_both = all(_out[_t].get("bin_exists") for _t, _, _ in ARMS)
print("PREP_VERDICT " + json.dumps({"arms": _out, "both_bins_written": _both}), flush=True)
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


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    b64 = base64.b64encode(open(TRAINER, "rb").read()).decode()
    src = TEMPLATE.replace("@SLUG@", SLUG).replace("@B64@", b64)
    assert "@B64@" not in src and "@SLUG@" not in src
    open(os.path.join(out, "%s.py" % SLUG), "w").write(src)
    json.dump(META, open(os.path.join(out, "kernel-metadata.json"), "w"), indent=2)
    print("wrote", out, "| kernel bytes", len(src))


if __name__ == "__main__":
    main()
