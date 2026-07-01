# ml/training - Code train model (NGUON provenance cho tang A)

> Truoc 2026-07-01, code train model chi nam tren Oracle (claudedata/), KHONG trong git
> -> mat provenance ("khong biet model sinh tu code nao"). Dua vao git de dong GAP #4
> (docs/PIPELINE_PROVENANCE.md muc 5). Snapshot lay tu Oracle 2026-07-01.

## Cac script

### train_funding_selector.py  (TASK-039 - funding SELECTOR)
- Train XGBoost du doan P(cham +6% trong horizon H) tung coin (selector "coin nao sap bom").
- Input (env): TOOL1_GLOB (ff_*.bin.gz, 40 feat) + OI_FILE (oi_percoin, 5 feat) + LABEL_CSV
  (funding_label.csv) + MAP_CSV (symId,symbol). Horizon: 4h|12h|24h|72h.
- Split: time-split, KHONG shuffle, purge=horizon, assert chong leak. TEST = 12 THANG CUOI.
- Output: models_v2/model_{H}.ubj + train_meta_{H}.json + metrics_{H}.json.
- LUU Y (leakage): script nay chi TRAIN + eval tren test. Sinh prediction full-history la buoc
  RIENG (script inference chua co trong git - GAP #4). Vi 1 model train<=2024-12 dung predict ca
  2021-2026 -> pred <2025-06 in-sample. Xem docs/PIPELINE_PROVENANCE.md muc 4.

### train_gate_fold.py  (WFO fold trainer - gate/market)
- Train XGBoost gate (Return15M) toi CUTOFF (expanding) -> ONNX. Goi boi WFOGateRunner (Java).
- LEAK-FREE (per-fold): moi fold train <= cutoff, predict OOS fold do. Day la MAU per-fold DUNG.
- Feature theo thu tu V3FULL khoa cung (33 feat), copy tay tu OnnxInferenceManager (leak L2).
- Output: wfo_models/fold_N/Model_Regressor_Return15M.onnx.

### gen_train_data.sh  (lap dataset train, chay tren Oracle)
- Regenerate 3 input cho funding train: ff (ExportFeaturesForPythonTool) + OI (ExportFundingOiPerCoin)
  + label (ExportFundingLabel). Range 2021-01-01 -> nay. Java export, ~vai gio (ff 5 nam nang).

### convert_ubj_to_onnx.py
- Chuyen model XGBoost .ubj -> .onnx cho inference Java (OnnxInferenceManager doc ONNX).

## Nguyen tac provenance (bat buoc di toi)
- Moi lan train: giu train_meta.json + ghi git SHA cua ml/training luc train + md5 input.
- Model = code + data sinh ra no. Mat 1 trong 3 -> coi nhu mat provenance, phai train lai (Direction A).
- KHONG sua model/prediction bang tay; data/model drift -> regenerate tu code+data co vet.
