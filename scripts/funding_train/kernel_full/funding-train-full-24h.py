#!/usr/bin/env python3
"""
TASK-130 FULL train (Kaggle GPU) — funding-train-full-24h.
Toan ky ff_*.bin + OI full + label full, train script UNMODIFIED, time-split cuoi ky.
Provenance data = ban export san co (pre-TASK130); re-gen HEAD tren Oracle = PENDING (ghi ro).
So sanh baseline TASK-128: rankIC 0.344 / hit_SEL 65.8% (model cu, do per-fold toan ky) — so
THAM KHAO vi nen do khac (per-fold vs holdout cuoi ky); phep so chinh thuc lam sau khi co model.
KHONG thay model production.
"""
import os, glob, json, hashlib, subprocess, sys, traceback

WORK = "/kaggle/working"

def find1(pat):
    m = sorted(glob.glob(pat, recursive=True))
    assert m, "KHONG tim thay: " + pat
    return m[0]

def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def main():
    try:
        print("=== nvidia-smi ===\n" + subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout[:600], flush=True)
    except Exception as e:
        print("nvidia-smi loi:", e, flush=True)

    ff_all = sorted(glob.glob("/kaggle/input/**/ff_*.bin", recursive=True))
    assert ff_all, "khong thay ff_*.bin"
    ff_dir = os.path.dirname(ff_all[0])
    oi_full = find1("/kaggle/input/**/oi_percoin_full.bin")
    label_full = find1("/kaggle/input/**/funding_label.csv")
    map_csv = find1("/kaggle/input/**/symbol_map.csv")
    train_py = find1("/kaggle/input/**/train_funding_selector.py")
    prov_txt = find1("/kaggle/input/**/PROVENANCE.txt")
    print(f"ff files: {len(ff_all)} ({os.path.basename(ff_all[0])}..{os.path.basename(ff_all[-1])})", flush=True)

    os.environ.update({
        "TOOL1_GLOB": f"{ff_dir}/ff_*.bin",
        "OI_FILE": oi_full,
        "LABEL_CSV": label_full,
        "MAP_CSV": map_csv,
        "OUT_DIR": WORK,
        "HORIZON": "24h",
        "XGB_DEVICE": "cuda",
        "N_ESTIMATORS": "600",
        "TEST_MONTHS": "6",
        "VAL_MONTHS": "6",
        "SAVE_MODEL": "1",
        "REPORT_QUARTERS": "1",
    })
    print("=== EXEC train_funding_selector.py (GPU FULL 24h) ===", flush=True)
    code = open(train_py).read()
    exec(compile(code, train_py, "exec"), {"__name__": "__main__", "__file__": train_py})

    prov = {
        "task": "TASK-130 FULL funding-train-full-24h (GPU)",
        "train_script_md5": md5(train_py),
        "provenance_txt": open(prov_txt).read(),
        "data_note": "data = ban Java-export san co (pre-TASK130 stamp); re-gen HEAD = PENDING truoc khi can nhac production",
        "ff_files": len(ff_all),
        "hyperparams_env": {k: os.environ[k] for k in ["HORIZON","XGB_DEVICE","N_ESTIMATORS","TEST_MONTHS","VAL_MONTHS"]},
        "baseline_TASK128": {"rankIC": 0.344, "hit_SEL": 0.658, "note": "per-fold toan ky — so tham khao, nen do khac holdout"},
    }
    json.dump(prov, open(f"{WORK}/provenance.json", "w"), indent=2)
    mp = f"{WORK}/metrics_24h.json"
    if os.path.exists(mp):
        print("=== metrics_24h.json ===\n" + open(mp).read(), flush=True)
    print("FULL_TRAIN_DONE", flush=True)

if __name__ == "__main__":
    try:
        main(); sys.exit(0)
    except Exception:
        traceback.print_exc(); sys.exit(1)
