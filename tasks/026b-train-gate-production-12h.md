---
id: 026b
status: TODO
depends_on: [025, 026]
touches_live_process: false
writes_242_data: false
resource: kaggle
checkpoint: false
max_retry: 2
report: docs/reports/026b.md
require_review: true
---

# TASK-026b: Train GATE production — horizon 12h + ONNX (tang 1: ML pass)

> 026 = chan doan (chot huong filter mem 12h). 026b = TRAIN RA MODEL DUNG DUOC + xuat ONNX
> de cam backtest. Tin hieu gate = **P_up - P_down** (KHONG hard argmax).

## Input
- `gate_dataset_v1.csv` (190.271 dong x 46 cot, md5 `58d451c6218043fbadf2471e1d701339`).
  - Tren 226: `/home/chuyennd/java/simulator/outputs/gate_dataset_v1.csv`.
  - Tren Kaggle: ĐA co (kernel `chuyendinh/gate-train-026` da doc tu /kaggle/input). Tai dung dataset do.
- Script: `python/tool/train_gate_production.py` (da viet, syntax PASS).

## Viec (CCD — chay Kaggle)
1. Kernel Kaggle: input = dataset chua `gate_dataset_v1.csv` (dataset cu cua 026) + add script production.
   Chay: `python train_gate_production.py <commit_hash_HEAD>`.
2. Doc log, bao lai cac so: CV macro-F1, n_est, **rank-IC OOS + t**, decile spread CV vs OOS,
   DOWN base/prec/rec/lift, RULE precision vs model precision@k (BEAT/KHONG), va dong
   `===== PRE-REGISTERED PASS =====`.
3. Output (de lai Kaggle + tai ve repo `models/gate/` neu PASS): `gate_model_12h.onnx`,
   `gate_model_12h.json`, `gate_features.json`, `gate_manifest.json`.
4. Neu ONNX export FAIL (onnxmltools/NaN) — bao lai, KHONG tu sua; xu o buoc tich hop.

## Pre-registered pass (tang 1 — ML; CHOT voi user, KHONG doi sau khi xem ket qua)
- [ ] rank-IC(P_up-P_down, ret_12h) tren OOS 12 thang cuoi **> 0 va |t| >= 2**.
- [ ] decile spread OOS **giu dau** voi CV.
- [ ] model **BEAT rule baseline** ("breadth thap AND funding cao -> block") o precision lop DOWN.
- 3/3 PASS -> sang tang 2 (backtest). FAIL -> bao user, KHONG tu doi nhan/threshold roi train lai.

## Buoc sau (tang 2 — KHONG thuoc task nay)
- Cam `gate_model_12h.onnx` vao backtest **thay gate cu**, chay **chung funding model ban cu** ->
  do PnL/maxDD/Sharpe + IC thuc vs gate cu tren cung golden range. Đat -> production. Funding moi (037/038/039) sau.

## An toan
- Chi chay Kaggle (KHONG dung 226 process). Doc-thuan v1. SLF4J khong ap dung (Python).

## (CCD dien)
- **Cac so tu log:** …
- **PASS/FAIL 3 tieu chi:** …
- **Output + duong dan:** …
