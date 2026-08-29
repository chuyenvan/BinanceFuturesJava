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

## 1. Tien quyet - du lieu: DA DU, KHONG can export lai (kiem 2026-07-01)
Feature/label/OI train full-history DA co san tren Oracle (export 1 lan, dung roadmap "export 1 lan dung chung"):
- ~/claudedata/train_ff/ : 22 file quy ff (2021-01 -> ~2026, Tool1 40 feat).
- ~/claudedata/train_label.csv : 9.37 GB (cot maxFav_{H}/nBars_{H} moi horizon).
- ~/claudedata/feat/oi_percoin_full.bin : 3.4 GB OI + symbol_map.csv.
=> TAI DUNG nguyen, KHONG chay lai gen_train_data.sh. (Chi regen neu file bi xoa/thieu - hien KHONG thieu.)
LEAK KHONG o feature; no o cho 1 model predict ca history. Feature giu nguyen; chi doi PREDICTION.

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

## 6. Uoc luong cong (da bo B1 - data da du)
- B1 data regen: KHONG can (data feature/label/OI da du - kiem 2026-07-01).
- B2 viet code per-fold + export bin: ~1-2h code + smoke 1 fold.
- B2 chay 56 fit (14 fold x 4 horizon): ~vai gio (detached).
- B3 gate: reuse wfo_models/fold_*, ~1h.
- B4 rebuild dataset (chi doi pred/funding, market giu nguyen) + nap + chay WFO: ~3h.
=> tong ~1 phien. Smoke moi buoc truoc khi full (nguyen tac Uni).

---
## STATE 2026-07-02 (dem autonomous): BUOC 1-2 XONG, BUOC 3-4 GAP INFRA

DA XONG (validate + commit):
- BUOC 1-2: funding leak-free per-fold. Generator gen_funding_wf_predictions.py (commit 57ddb49),
  smoke PASS (leak-assert giu, bin 26B dung, prob[0,1]). Full 17-fold chay tren Oracle -> predict_wf_*.bin
  (~104MB, 17 block phu 2022-01..2026-03). Fix OOM: grid-filter OI 5m->15m (lossless).
- BUOC 3 gate: gate leak-free DA co dang wfo_gate_pred.csv (1.79M rows, predReturn15M+predRisk4H, tu 2023-01).

BLOCKER BUOC 3-4 (can Uni quyet - infra/PnL, KHONG tu quyet):
1. **226 disk 97% day** (88G/92G, 3.3G trong). Nap set v3wf (~1.2GB) + export dataset len server giu data
   -> rui ro lap day dia. Giai phong dia (xoa set cu: funding_selector_pred_v1 224MB, cac _java_test/_smoke,
   funding_selector_pred_1m cu 3.1GB?) la hanh dong PHA HUY tren server co du lieu -> can Uni duyet.
2. **Gate set ai_pred_market_gate_wfo CHUA nap Aerospike** - chi co _smoke (45k obj). Full set o CSV. Can:
   nap wfo_gate_pred.csv -> set (can loader CSV market-level, chua co) HOAC chay lai WFOGateRunner (replay nang).
3. Namespace = ticker. jar 226 (binance-futures-java.jar) cu, chua co env-config WFO_SET_* -> can build+deploy jar moi.

DUONG DI KHUYEN NGHI (khi Uni duyet):
- Option A (qua Aerospike 226): giai phong dia 226 -> nap funding v3wf -> nap gate CSV -> build+deploy jar env-config
  -> ExportWfoDataset (WFO_SET_FUNDING=v3wf, WFO_SET_PRED=gate_wfo) tren 226 -> scp dataset ve Oracle -> WFO.
- Option B (bypass Aerospike, an toan dia): viet tool doc predict_wf bins + wfo_gate_pred.csv + market.bin cu
  -> ghi thang funding.bin/pred.bin theo format WfoDataset (tranh 226 hoan toan). Can khop format packing long[].
- Scope: window fully-leak-free (ca IS+OOS 2 tin hieu) = OOS >= 2024-01 (~10 window). Khuyen nghi dung scope nay.
