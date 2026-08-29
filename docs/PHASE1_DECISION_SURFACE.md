# PHA 1 — BẢNG QUYẾT ĐỊNH (worksheet cho STEP 1.2)

> Sinh bởi STEP 1.1 (Claude đọc code, decision-neutral). Cột "GIÁ TRỊ HIỆN TẠI" chỉ để bạn THẤY
> đang có gì + cái nào đã nhiễm; **KHÔNG phải khuyến nghị**. Cột "QUYẾT (1.2)" bạn tự điền trên DEV.
> ⚠️ = đã nhiễm (range/giá trị rút ra từ nhìn kết quả) hoặc CHƯA chốt → phải quyết lại có ý thức.
> Điền xong bảng này → chép sang Phụ lục A của DATA_GOVERNANCE_PROTOCOL.md → hash → đóng băng.

## A. TẦNG SELECTOR (thượng nguồn — pred là feature của sim)

| ID | Quyết định | Giá trị HIỆN TẠI | Nguồn | QUYẾT (1.2) |
|----|-----------|------------------|-------|-------------|
| A1 | Feature set | 45 feat = f0..f39 (Tool1 export Java; biết: f20 fundingRateTrend, f24 fundingSum24h, f26 volumeZCoin, còn lại opaque) + 5 OI (oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy). ⚠️ đã từng feature-select (featsel_gate15m.py) | tool1_col.py, train_funding_selector_wfo.py:FEAT | |
| A2a | Label — kiểu | 2-sided triple-barrier: y=1 nếu chạm TP trước SL trong horizon | train_..._wfo.py:load_labels | |
| A2b | Label — TP (fav) | **0.06** (SEL_FAV_PCT) | idem | |
| A2c | Label — SL (adv) | **0.03** ⚠️ ghi rõ "SL placeholder, user chot sau" — **CHƯA TỪNG CHỐT** | idem | |
| A2d | Label — horizon | train cả {4h,12h,24h,72h}; strategy DÙNG 4h (WFO_SEL_HORIZON_IDX=0) ⚠️ chọn 4h là 1 quyết định | runbook D2 | |
| A2e | Label — lấy mẫu | grid 15 phút (SELECTOR_GRID_MIN=15) ⚠️ **OVERLAP** với horizon>15m = L1 leak; có mode nonoverlap nhưng default grid | train_..._wfo.py:GRID_MS | |
| A3a | Selector model + hp | XGBoost n_est=400, depth=5, lr=0.05, subsample=0.8, colsample=0.8, min_child_weight=20, scale_pos_weight=(1-pos)/pos, seed=42 | train_..._wfo.py:run | |
| A3b | Selector — purge | H_STEPS×15m wall-clock (4h→16 bước; 72h→288) | idem | |
| A3c | Selector — Optuna? | có biến thể Optuna riêng (optuna_trials.json) ⚠️ nếu dùng, mọi Optuna-trial phải đếm vào n_trials | ml/training, train_market_xgboost_optuna.py | |
| A4 | Universe + survivorship | CoinRank tier (WFO_STATIC_RANK + ExportCoinTierStatic), survivorship_bac0.py. ⚠️ cần xác định: symbol nào, tier tĩnh/động, xử lý delist | WfoWorker, survivorship_bac0.py | |

## B. TẦNG STRATEGY

| ID | Quyết định | Giá trị HIỆN TẠI | Nguồn | QUYẾT (1.2) |
|----|-----------|------------------|-------|-------------|
| B5 | Gate | AIRejectFilter = predReturn15M ≥ MIN_MOMENTUM_15M (worker 0.008); risk4h ĐÃ BỎ (leaky); market-level | runbook §4 | |
| B6 | Selector rank-K | top-K = 8 (SELECTOR_RANK_TOPK) | runbook D5 | |
| B7 | 17 gene + range | **TẤT CẢ range ⚠️ đã sweep-thu-hẹp** (comment "sweep cho thấy...", "TASK-139"). Phải vẽ lại RỘNG theo lý thuyết. Danh sách 17 gene: xem StrategyWfoTask.GENOME | StrategyWfoTask.java | |
| B8 | Cost model | SIM_APPLY_FUNDING=true, breaker OFF, CAPITAL_START=35000. ⚠️ fee/slippage cần xác nhận giá trị | runbook D5, Configs | |

## C. TẦNG ĐÁNH GIÁ

| ID | Quyết định | Giá trị HIỆN TẠI | Nguồn | QUYẾT (1.2) |
|----|-----------|------------------|-------|-------------|
| C9 | Objective O | median(Calmar_net) − 0.5·std(Calmar_net) qua fold ⚠️ std 2 chiều phạt cả fold tốt bất thường | StrategyWfoTask.aggregate | |
| C10 | Ngưỡng pass | PBO<0.2 · DSR>0.95 · %fold+≥0.80 (PASS_POS_RATIO_V1) · maxDD-cap (SURVIVAL_MAX_DD_PCT) | preregistration_frame_v1 | |
| C11 | CPCV setup | N=8 block, k=2, 28 path, gap=purge+embargo=max(horizon,MAX_HOLD) | cpcv_harness.py | |
| C12 | Budget n_trials + stopping | ⚠️ CHƯA định — bắt buộc chốt trước Pha 2 | — | |

## Tổng kết cái CHƯA/ĐÃ-NHIỄM phải quyết lại có ý thức (đừng để trôi)
1. **A2c label SL** — chưa từng chốt (placeholder 0.03).
2. **A2e lấy mẫu grid 15m** — overlap = L1 leak; cân nhắc nonoverlap.
3. **B7 range 17 gene** — toàn bộ đã sweep hẹp; vẽ lại rộng.
4. **A3c Optuna selector** — nếu dùng, trial phải đếm vào n_trials.
5. **A4 survivorship** — chưa xác định rõ universe.
6. **C12 budget/stopping** — chưa có.
7. **C9 objective** — cân nhắc downside-std thay std 2 chiều (nhưng đổi = pre-register v2).

## Ô CHƯA ĐỌC (nếu 1.2 cần, Claude đọc tiếp — vẫn decision-neutral)
- Tên đầy đủ f0..f39: Tool1ColSink.java (bên exporter Java).
- Giá trị fee/slippage chính xác: Configs.java.
- Bộ dựng maxFav/maxAdv (nguồn LABEL_CSV): ml/lib/funding_label_pb.py.
