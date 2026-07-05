#!/usr/bin/env python3
"""
TASK-130 SMOKE kernel (Kaggle GPU) — funding-train-v1.

Muc tieu: CHUNG MINH pipeline retrain funding selector chay end-to-end tren GPU + provenance sach.
KHONG phai ra model tot. Lat nho = H1-2021 (6 thang) de chay nhanh.

Nguon (tat ca Java-export — thoa hang rao TASK-130 #1):
  chuyendinh/funding-train-code      -> train_funding_selector.py (git-stamped) + PROVENANCE.txt
  chuyendinh/funding-tool1-features  -> ff_YYYYMM.bin (40 feat, 170B/record)
  chuyendinh/funding-oi-percoin      -> oi_percoin_full.bin (5 feat, 30B) + symbol_map.csv
  chuyendinh/funding-label-full      -> funding_label.csv (label path-tho, TASK-024)

Harness: cat OI+label ve ts-window cua 6 thang ff (bound RAM), roi goi train script UNMODIFIED
qua env (XGB_DEVICE=cuda, N_ESTIMATORS=60, TEST_MONTHS=2, VAL_MONTHS=2, SAVE_MODEL=1).
Output /kaggle/working: model_24h.ubj + metrics_24h.json + train_meta_24h.json + provenance.json.
"""
import os, glob, json, hashlib, subprocess, sys, traceback
import numpy as np
import pandas as pd

WORK = "/kaggle/working"
FF_MONTHS = [1, 2, 3, 4, 5, 6]          # H1-2021 lat nho
OI_TOL_MS = 2 * 60 * 60 * 1000
TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])   # 170B
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])      # 30B


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
    # 0. GPU check (bang chung device)
    try:
        smi = subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout
        print("=== nvidia-smi ===\n" + smi[:800], flush=True)
    except Exception as e:
        print("nvidia-smi loi (van chay tiep, train se bao device):", e, flush=True)

    # 1. locate inputs (glob recursive — layout mount co the doi, KAGGLE_RULES §3b)
    ff = [find1(f"/kaggle/input/**/ff_2021{m:02d}.bin") for m in FF_MONTHS]
    oi_full = find1("/kaggle/input/**/oi_percoin_full.bin")
    label_full = find1("/kaggle/input/**/funding_label.csv")
    map_csv = find1("/kaggle/input/**/symbol_map.csv")
    train_py = find1("/kaggle/input/**/train_funding_selector.py")
    prov_txt = find1("/kaggle/input/**/PROVENANCE.txt")
    print("ff:", ff, flush=True)
    print("oi_full:", oi_full, "| label_full:", label_full, "| map:", map_csv, flush=True)
    print("train_py:", train_py, flush=True)
    print("=== code PROVENANCE.txt ===\n" + open(prov_txt).read(), flush=True)

    # 2. ts-window tu ff (6 thang)
    lo, hi = None, None
    for fp in ff:
        a = np.fromfile(fp, dtype=TOOL1_DT)
        assert a.nbytes % 170 == 0
        tlo, thi = int(a["ts"].min()), int(a["ts"].max())
        lo = tlo if lo is None else min(lo, tlo)
        hi = thi if hi is None else max(hi, thi)
    print(f"ts window ff = [{lo} .. {hi}] = "
          f"{pd.to_datetime(lo, unit='ms')} .. {pd.to_datetime(hi, unit='ms')}", flush=True)

    # 3. copy ff months -> working (glob rieng, tranh nam khac trong mount)
    ff_dir = f"{WORK}/ff_smoke"
    os.makedirs(ff_dir, exist_ok=True)
    import shutil
    for fp in ff:
        shutil.copy(fp, ff_dir)

    # 4. slice OI (numpy big-endian) ve [lo-tol, hi]
    oi = np.fromfile(oi_full, dtype=OI_DT)
    print("OI full rows:", len(oi), flush=True)
    mask = (oi["ts"] >= lo - OI_TOL_MS) & (oi["ts"] <= hi)
    oi_slice = np.ascontiguousarray(oi[mask])
    oi_out = f"{WORK}/oi_smoke.bin"
    oi_slice.tofile(oi_out)
    print("OI slice rows:", len(oi_slice), "->", oi_out, flush=True)
    del oi, oi_slice

    # 5. slice label (chunked) ve [lo, hi]
    lab_out = f"{WORK}/label_smoke.csv"
    first, kept = True, 0
    for chunk in pd.read_csv(label_full, chunksize=3_000_000, on_bad_lines="skip"):
        c = chunk[(chunk["tEpochMs"] >= lo) & (chunk["tEpochMs"] <= hi)]
        if len(c):
            c.to_csv(lab_out, mode="w" if first else "a", header=first, index=False)
            first, kept = False, kept + len(c)
    print("label slice rows:", kept, "->", lab_out, flush=True)
    assert kept > 0, "label slice rong — kiem ts alignment ff vs label"

    # 6. env cho train script (lat nho + GPU)
    os.environ.update({
        "TOOL1_GLOB": f"{ff_dir}/ff_*.bin",
        "OI_FILE": oi_out,
        "LABEL_CSV": lab_out,
        "MAP_CSV": map_csv,
        "OUT_DIR": WORK,
        "HORIZON": "24h",
        "XGB_DEVICE": "cuda",
        "N_ESTIMATORS": "60",
        "TEST_MONTHS": "2",
        "VAL_MONTHS": "2",
        "SAVE_MODEL": "1",
        "REPORT_QUARTERS": "1",
    })

    # 7. chay train script UNMODIFIED (exec as __main__)
    print("=== EXEC train_funding_selector.py (GPU smoke) ===", flush=True)
    code = open(train_py).read()
    g = {"__name__": "__main__", "__file__": train_py}
    exec(compile(code, train_py, "exec"), g)

    # 8. provenance block
    prov = {
        "task": "TASK-130 SMOKE funding-train-v1 (GPU)",
        "purpose": "chung minh pipeline + GPU; KHONG phai model production",
        "train_script": {"path_on_kaggle": train_py, "md5": md5(train_py),
                         "source_dataset": "chuyendinh/funding-train-code",
                         "provenance_txt": open(prov_txt).read()},
        "data_sources_java_export": {
            "tool1_features": "chuyendinh/funding-tool1-features (ExportFeaturesForPythonTool)",
            "oi_percoin": "chuyendinh/funding-oi-percoin (ExportFundingOiPerCoin)",
            "label": "chuyendinh/funding-label-full (ExportFundingLabel)"},
        "ff_months_md5": {os.path.basename(f): md5(f) for f in ff},
        "oi_slice_md5": md5(oi_out), "label_slice_md5": md5(lab_out),
        "slice_window_ms": [lo, hi],
        "hyperparams_env": {k: os.environ[k] for k in
                            ["HORIZON", "XGB_DEVICE", "N_ESTIMATORS", "TEST_MONTHS", "VAL_MONTHS"]},
        "note": "Train FULL clean-provenance (re-run gen_train_data.sh tren Oracle, HEAD stamp) = PENDING.",
    }
    json.dump(prov, open(f"{WORK}/provenance.json", "w"), indent=2)
    print("=== PROVENANCE ===\n" + json.dumps(prov, indent=2), flush=True)

    # echo metrics neu co
    mp = f"{WORK}/metrics_24h.json"
    if os.path.exists(mp):
        print("=== metrics_24h.json ===\n" + open(mp).read(), flush=True)
    print("SMOKE_DONE", flush=True)


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
