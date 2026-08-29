# Track 2 — Tối ưu GATE (tiến trình chi tiết, baseline → cải tiến dần) 2026-08-17

Bắt đầu SAU khi v1 baseline live (selector+gate WFO + feature parity 45/45). Mục tiêu: gate tốt hơn baseline
theo 3 hướng Uni nêu — **label, threshold, OI feature** — nhưng KHÔNG lặp lỗi HPO-trên-OOS.

## 0. Ràng buộc bao trùm (methodology — quan trọng nhất)
Theo `wfo_methodology_hpo_in_wfo`: chọn label/threshold/feature trên OOS gộp = selection bias → số đẹp là trần
lạc quan. LUẬT:
- Train/chọn trên **≤2025** (inner-validation), **cold-test 2026** (holdout sạch, KHÔNG dùng để chọn).
- Chọn bằng 1-SE / worst-window / vùng phẳng, không phải max-total.
- KHÔNG re-sweep trên 2026. Mỗi cải tiến chỉ lên live nếu **thắng baseline trên cold-test 2026**.

## 1. Baseline (mốc phải vượt)
- Gate hiện: `label_oldbasket` = `basketMaxGain 15m` trên `findPotentialLosers(ts)` (MAX/lướt), feature 33 market-level
  (`ComprehensiveMarketFeatureExtractor`, V3Full), model fold_20 đã live. Threshold `MIN_MOMENTUM_15M=0.008`.
- **Bệnh nền đã biết** (`wfo_diff_15m_vs_1m`): max/lướt label → đoán "chạm đỉnh" không phải "giữ được"; pump ngắn dump dài.
- Đo baseline: (a) IC(pred, realized) OOS, (b) LIFT@thr, (c) **net-PnL contribution** qua backtest gate A/B (gate on/off
  trên cùng selector+sim canonical), (d) worst-window, cold-test 2026.

## 2. PHASE 1 — LABEL (đòn bẩy cao nhất, làm trước)
Định nghĩa label ứng viên (thêm cột vào `ExportGate15mV2`, xuất 1 lần đủ mọi label để so công bằng cùng feature):
- **L0 baseline**: `label_oldbasket` (maxGain 15m) — giữ.
- **L1 `label_ret15m`**: `basketRetEnd 15m` = avg (closeExit@t+15m − close@t)/close@t — NET, chống lướt trực tiếp.
- **L2 `label_ret60m`**: `basketRetEnd 60m` — net horizon dài hơn (nuôi-leaning, timing sóng bền).
- (giữ `label_selector` maxGain làm biến thể rổ.)
Code: thêm `basketRetEnd(data,ts,basket,horizon)` (song song `basketMaxGain`) + 2 cột header/row trong `ExportGate15mV2`.
Train: env-param `LABEL` trong `train_gate_fold.py` (hiện hardcode `label_oldbasket`); WFOGateRunner train mỗi label
expanding ≤2025 → predict OOS → cold-test 2026. So IC/LIFT/net-PnL/worst-window. Chọn label thắng baseline trên 2026.

## 3. PHASE 2 — THRESHOLD (sau khi chốt label)
- 0.008 hiện chọn trên OOS gộp (bias). Grid quanh vùng bằng `Mom15SweepProbe`/`GatePassCountProbe` (đã có) trên
  **inner-val ≤2025**, chọn 1-SE/tâm vùng phẳng, rồi cold-test 2026 đúng 1 giá trị. KHÔNG sweep trên 2026.
- Lưu ý gate động: threshold thực = `MIN_MOMENTUM_15M × scale(symbolPred)` → sweep phải giữ nguyên công thức động.

## 4. PHASE 3 — OI FEATURE cho gate
- Gate hiện KHÔNG có OI (33 market feature). Thêm **OI aggregate market-level** (tổng OI delta thị trường, LS toàn cục
  trung bình, taker-buy market) — KHÔNG phải OI per-coin (gate là 1 pred/timestamp).
- Nguồn: aggregate từ set OI raw (226/242) theo timestamp. Thêm vào `ComprehensiveMarketFeatureExtractor` (hoặc 1 extractor
  gate-mở-rộng) → retrain gate → A/B có/không OI trên cold-test 2026 (giữ label đã chốt phase 1).

## 5. Sequencing + guardrail
1. Phase 1 label (export dual+ret labels → train per-label → cold-test → chốt). 
2. Phase 2 threshold (probe inner-val → cold-test).
3. Phase 3 OI feature (extractor → retrain → cold-test).
- Mỗi phase: chỉ deploy live nếu thắng baseline cold-test 2026, theo runbook `deploy_v1_gate.md` (swap fold-cuối ONNX + verify).
- KHÔNG đụng live giữa chừng; baseline hiện giữ nguyên chạy.

## 6. Trạng thái code (đã bắt đầu)
- `ExportGate15mV2`: thêm label ứng viên `basketRetEnd` (commit sắp tới) — bước 1 Phase 1.
- Compute (export→train→cold-test) chạy Oracle/Kaggle, KHÔNG đụng 242.
