# RUNBOOK - Dung STRATEGY-WFO leak-free (san sang chay, cho Uni greenlight)

> Muc tieu: strategy-WFO ma MOI window OOS dung prediction (funding + gate) chua tung thay
> luc train model -> phep thu joint (model + chien luoc) hop le moi window, khong chi ~3 window
> cuoi. Doi chieu: docs/PIPELINE_PROVENANCE.md muc 7 + WFO_LEAKS_TODO L0/L1/L4.
> Trang thai 2026-07-01: CHUA chay. Day la viec DA-PHIEN (nhieu gio), co diem can Uni quyet.
> KHONG tu chay unattended vi phai VIET code inference moi (script sinh predict full-history
> KHONG co trong git = phan "code mat") -> rui ro tao artifact "sach gia" neu sai ngam.

## 0. Vi sao chua the tu dong hoa 100%
- train_funding_selector.py chi TRAIN + eval (khong export prediction per-ts theo format predict_*.bin).
- Script INFERENCE sinh predict_*.bin (Python) KHONG co trong git -> phai viet lai buoc export prediction.
- => can code moi + Uni xac nhan vai diem phuong phap (muc 5). Do do de o dang runbook.

## 1. Tien quyet - du lieu (regenerate neu thieu)
Chay tren Oracle (ml/training/gen_train_data.sh): sinh ff (Tool1 40 feat) + OI + funding_label.csv
range 2021-01 -> nay. ~vai gio (ff 5 nam nang). Output: ~/claudedata/train_ff/, oi, train_label.csv.
Kiem: ff phu 2021-2026, label co cot maxFav_{H}/nBars_{H}, map symId->symbol day du.

## 2. Funding per-fold (BU GAP CHINH) - can VIET code
Sua ml/training/train_funding_selector.py -> them che do per-fold:
- Nhan env TRAIN_CUTOFF (yyyymmdd) + OOS_LEN_MONTHS (3).
- Train tren ts < TRAIN_CUTOFF - purge (purge = H_STEPS[H]*GRID_MS, dai nhat 72h).
- PREDICT tren [TRAIN_CUTOFF, TRAIN_CUTOFF + OOS_LEN) -> GHI predict_*.bin (26B: >q h 4f = ts,symId,p4h..p72h).
  (buoc ghi bin nay la CODE MOI - copy format tu ExportSelectorPred1mToAerospike doc nguoc lai.)
- Loop 14 fold (cutoff = bien IS moi window WFO, khop buildWindows StrategyWfoTask). Ghep -> chuoi leak-free
  phu [first-OOS .. end]. ~14 fold x 4 horizon = 56 fit XGBoost (~2M rows/fit) -> nhieu gio tren Oracle.

## 3. Gate per-fold (DA CO khung)
Gate da co train_gate_fold.py + WFOGateRunner + wfo_models/fold_* (leak-free). Sinh chuoi gate prediction
leak-free ghep (WFOGateRunner da co logic per-fold predict OOS). Kiem embargo quanh cutoff (leak L1).

## 4. Ghep -> set moi -> dataset -> chay WFO
- Nap 2 chuoi leak-free vao set version moi: funding_selector_pred_1m_v3wf, ai_pred_market_gate_v3wf
  (kem sidecar provenance: producedByCodeSha, modelProvenance per-fold, leakFreeFrom=per-fold).
- Sua WfoDataset.SET_PRED/SET_FUNDING -> set v3wf (HOAC tham so hoa qua env).
- Export wfo_dataset_wf: chay ExportWfoDataset voi env WFO_CODE_SHA=<sha>, WFO_PROV_FUNDING="per-fold v3wf",
  WFO_LEAKFREE_FROM="per-fold" (stamping da ho tro - commit f37e325).
- Chay StrategyWfoTask tren wfo_dataset_wf, CUNG nguong pre-registered (WFE>=0.5, %OOS-duong>=70%, maxDD<=50%).
- So verdict leak-free vs ban ro ri (docs/reports/wfo_strategy_window.md + commit cb0032b).

## 5. DIEM CAN UNI QUYET (khong tu quyet - PnL/phuong phap)
1. Tham so model per-fold funding: dung y het ban single (n_est=400, depth=5, lr=0.05...) - MAC DINH AN TOAN.
2. Purge/embargo IS<->OOS = horizon dai nhat 72h - mac dinh an toan.
3. Co dung set gate leak-free (v3wf) thay full_basket_v2 trong strategy-WFO khong (nen: CO, de joint sach).
4. Chap nhan verdict leak-free lam CHUAN thay ban ro ri (ky vong: WFE/pnl thap hon vi tin hieu that te hon).

## 6. Uoc luong cong
- B1 data regen: ~vai gio (Java export, detached tren Oracle).
- B2 viet code per-fold + export bin: ~1-2h code + smoke 1 fold.
- B2 chay 56 fit: ~vai gio (detached).
- B3 gate: reuse, ~1h.
- B4 ghep+nap+export+WFO: ~3h.
=> tong ~1-2 phien. Nen lam tuan tu, smoke moi buoc truoc khi full (nguyen tac Uni).
