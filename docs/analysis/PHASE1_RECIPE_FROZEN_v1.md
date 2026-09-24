# CÔNG THỨC PHA 1 — v1 (ĐÃ ĐÓNG BĂNG) — 2026-08-24

> ĐÃ KÝ. author=chuyennd, ngày=2026-08-24. Theo DATA_GOVERNANCE_PROTOCOL. Quyết trên DEV (2021-01→2024-06),
> KHÔNG lấy từ VALIDATION/HOLDOUT. Sau dòng này KHÔNG sửa — sửa = v2 (hash mới, đếm lại trial). Hash SHA256
> của file này lưu ở governance §6 + configs/data_tiers.json.

## CỜ CẤU HÌNH
- DCA_GRID_ENABLED = true, DCA_GRID_SCALAR = true
- OFF_FLAT_HARD = true · FILTER_MODE = "A" · BREAKER_MODE = OFF · SIM_APPLY_FUNDING = true
- Trailing = công thức liên tục per-coin MỚI (bỏ weak/strong + floor cũ)
- LEVERAGE = 1x

## LABEL (selector)
- 2-sided triple-barrier: y=1 nếu chạm TP trước SL trong horizon.
- TP = 0.06 · SL = 0.40 · horizon = 4h · lấy mẫu = 4h NON-OVERLAP.
- Tường selector: train-cutoff ≤ biên trái tầng (VALIDATION ≤2024-07-15; HOLDOUT ≤2025-12-31).

## FEATURE / UNIVERSE / SELECTOR
- Feature 45 = 40 Tool1 + 5 OI. GIỮ. · Universe: CoinRank tier tĩnh. GIỮ.
- Selector: XGBoost WFO rolling (n_est400/depth5/lr0.05/sub0.8/col0.8/mcw20), purge=horizon, KHÔNG Optuna.

## SEARCH SPACE (14 gene)
GATE:
- MIN_MOMENTUM_15M            ∈ [0.005, 0.020]     reject entry nếu pred15M < ngưỡng
- PREDICT_SYMBOL_RATE_MAX_THRESHOLD ∈ [0.10, 0.30] baseline prob gate động per-coin
- AI_DYNAMIC_MULTIPLIER       ∈ [1.0, 3.0]         hệ số scale gate động
- AI_DYNAMIC_MIN              ∈ [0.1, 1.0]         cận dưới clamp scale
MARKET:
- MS_DOWN_BIG_AVG             ∈ [-0.060, -0.025]   ngưỡng BIG_DOWN (entry + mở DCA)
DCA (grid):
- DCA_GRID_L1                 ∈ [-0.75, -0.25]     mốc nhồi bậc 1
- DCA_GRID_STEP               ∈ [0.10, 0.30]       giãn bậc: level[i]=L1−STEP×i
- DCA_GRID_LEGS               ∈ [2, 4] int         trần số bậc
- DCA_GRID_W_RATIO            ∈ [1.0, 3.0]         tỉ trọng: w[i]=W_RATIO^i
EXIT:
- RATE_PROFIT_STOP_MARKET     ∈ {0.05,0.06,0.07,0.08}  ngưỡng arm + dời SL tối thiểu
- TS_PROFIT_MULTIPLIER        ∈ {2,3,4,5}          nhân ngưỡng ratchet (dead-zone)
- TS_MAX_GAP                  ∈ [0.05, 0.20] step 0.02  trần gap trailing (đầu vào per-coin)
BUDGET (mới):
- F_BASE                      ∈ [0.01, 0.05]       % equity mỗi lệnh gốc
- U_MAX                       ∈ [0.40, 0.80]       trần tổng margin/equity

## HẰNG CỐ ĐỊNH (không search)
- DCA_GRID_SCALE = 1.0
- Cost: RATE_FEE=0.002(×2), SLIPPAGE_RATE=0.003(×2), APPLY_SLIPPAGE=true (~0.8% RT)

## LOGIC MỚI phải code
1. Trailing per-coin: quy ước DUY NHẤT pGood = 1 − pNoPump (cao=tốt).
   gap = pGood × TS_MAX_GAP. BỎ weak/strong + floor. Arm = RATE_PROFIT_STOP_MARKET thuần (bỏ TS_DYNAMIC_K).
2. Budget mới (thay managerBudget):
   U = marginDùng/equity; if U≥U_MAX → 0; throttle = clamp(1 − U/U_MAX, 0, 1);
   budget = equity × F_BASE × throttle / dcaGridTotalWeight()
3. GENOME = đúng 14 gene trên.

## FITNESS v2 (rebuild — HPOFitnessCalculatorV4 → nhánh/ v5)
- Calmar = netPnl / **maxDD_mark-to-market** (đổi từ realized → mtm, honest: tính cả DCA treo âm).
- Chỉ 3 chốt sinh-tử: ZERO_TRADES · BURN (pnl≤0) · OVER_MAXDD (**ddPct_mtm > 0.85**).
- BỎ 3 phạt kiểu-IS: TOO_FEW_TRADES, TOO_MUCH_CAPITAL_LOCK, UNSTABLE_ACROSS_YEARS (+ ramp freq-floor).
  (độ ổn định do O `median−0.5·std` + CPCV/PBO/DSR lo.)
- Guard MỀM: fold < 5 lệnh → Calmar = 0 (low-confidence), KHÔNG reject cứng.

## OBJECTIVE + PASS + SEARCH
- O = median(Calmar_mtm) − 0.5·std(Calmar_mtm) qua fold (phạt 2 chiều).
- PASS: PBO < 0.20 · DSR > 0.95 · %fold dương ≥ 0.80 · ddPct_mtm ≤ 0.85 (cap 1x).
- n_trials = 200. Stopping = hết 200 HOẶC 50 trial liền không cải thiện O. Ledger đếm config THỰC thử.
- CPCV: N=8 block, k=2 (28 path), gap = purge+embargo = max(horizon 4h, MAX_HOLD).

## GENE BỎ (không vào GENOME v1)
HARD_RISK_LIMIT_4H · TS_DYNAMIC_K · TS_MAX_GAP_WEAK · TS_WEAK_MOMENTUM_THRES · TS_GIVEBACK_FLOOR/MIN_GAP/RATIO ·
DCA_GRID_SCALE(cố định 1) · DCA_LOSS_BIG_DOWN/DCA_TIME_BIG_DOWN(grid ON) · BUDGET_MARGIN_RATIO_1/2 · BUDGET_DIVIDER_1/2.

## HẠN CHẾ ĐÃ BIẾT (pre-register)
- VALIDATION 2024-2025 đã bị nhìn → DSR là CẬN TRÊN. 2026 là trọng tài thật.
- Cấu trúc DCA-grid + feature + universe là prior thiết kế (không search).
- TP/horizon giữ từ cũ (anchor nhẹ) — lật lại = v2.

## SEAL
author = chuyennd · ngày = 2026-08-24 · trạng thái = FROZEN v1
