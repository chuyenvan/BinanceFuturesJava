#!/usr/bin/env python3
# Kaggle kernel: train funding selector WFO (4 horizon) tren dataset da upload.
# Kaggle GIAI NEN .gz -> file .bin/.csv (khong .gz). Dataset tai /kaggle/input/funding-selector-wfo-data/
# Output: wfo_selector_results.json + model_wfo_last_{H}.ubj -> /kaggle/working/ (tai ve sau).
import os, sys, subprocess

DS = "/kaggle/input/funding-selector-wfo-data"
os.environ["TOOL1_GLOB"] = f"{DS}/features_*.bin"
os.environ["OI_FILE"]    = f"{DS}/oi_percoin_20210101_to_20260624.bin"
os.environ["LABEL_CSV"]  = f"{DS}/funding_label.csv"
os.environ["MAP_CSV"]    = f"{DS}/symbol_map.csv"
os.environ["OUT_DIR"]    = "/kaggle/working"
os.environ["SAVE_LAST_MODEL"] = "1"
os.environ["FIRST_OOS"]  = "202301"
os.environ["LAST"]       = "202606"
os.environ["OOS_MONTHS"] = "3"
# SMOKE khong set -> chay full WFO

CANDS = ["/kaggle/working/train_funding_selector_wfo.py",
         "train_funding_selector_wfo.py",
         f"{DS}/train_funding_selector_wfo.py"]
script = next((c for c in CANDS if os.path.exists(c)), None)
if script is None:
    print("KHONG thay train script"); sys.exit(2)
print("Chay:", script, flush=True)
subprocess.run([sys.executable, script], check=True)
print("KERNEL DONE", flush=True)
