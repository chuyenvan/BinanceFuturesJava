# scripts/funding_train — TASK-130 pipeline retrain funding selector (GPU)

Dung + SMOKE pipeline retrain funding selector tren Kaggle GPU voi provenance sach.
KHONG thay model production — chi chung minh pipeline chay end-to-end + GPU duoc dung.

## Ban train script DUNG (khao sat git log — KHONG doan)
`ml/training/train_funding_selector.py` (commit 66341cd, git-blessed provenance; == ban
`ml/funding_selector/` legacy). `_wfo.py` = WFO per-fold, khac muc dich. Chi tiet: `tasks/130`.

## Data (tat ca Java-export — thoa hang rao CORE "TRAIN data DUY NHAT tu Java")
| Dataset Kaggle | Tool Java | Record |
|---|---|---|
| chuyendinh/funding-tool1-features | fundingv2.ExportFeaturesForPythonTool | ff_YYYYMM.bin 170B/40feat |
| chuyendinh/funding-oi-percoin | fundingv2.ExportFundingOiPerCoin | oi_percoin_full.bin 30B/5feat + symbol_map.csv |
| chuyendinh/funding-label-full | export.ExportFundingLabel | funding_label.csv (path-tho) |
| chuyendinh/funding-train-code | (git snapshot) | train_funding_selector.py + PROVENANCE.txt |

## Kernel SMOKE
- `kernel/funding-train-v1.py` + `kernel/kernel-metadata.json` (enable_gpu=true, enable_internet=false).
- Lat nho H1-2021 (6 thang): harness cat OI+label ve ts-window ff (bound RAM) -> goi train script
  UNMODIFIED qua env `XGB_DEVICE=cuda N_ESTIMATORS=60 TEST_MONTHS=2 VAL_MONTHS=2 SAVE_MODEL=1 HORIZON=24h`.
- PASS smoke = log `device=cuda` + train het khong crash + ra model_24h.ubj + provenance.json.

### Push / poll
```bash
cd scripts/funding_train/kernel && kaggle kernels push -p .
kaggle kernels status chuyendinh/funding-train-v1
kaggle kernels output chuyendinh/funding-train-v1 -p /d/claudedata/ftv1-out
```

## PENDING (train FULL clean-provenance — can Oracle ranh, ve D xong)
Re-run `ml/training/gen_train_data.sh` tren Oracle (HEAD stamp + md5) -> push 3 dataset moi ->
train FULL GPU 4 horizon -> so rankIC/hit_SEL vs baseline TASK-128 (rankIC 0.344 / hit_SEL 65.8%).
Thay model = quyet dinh Uni, KHONG phai CCD. `DumpSymbolMapper` chua co trong git src (chi .class tren
Oracle/java-run-lc) — provenance GAP can dong khi export FULL.
