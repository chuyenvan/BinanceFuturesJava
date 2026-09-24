# PHA 1 — CÔNG THỨC (NHÁP, CHƯA HASH) — cập nhật 2026-08-24 (lượt 2)

> 🟢 chốt · 🟡 còn hở cần Uni · 🔴 rủi ro/phải xử trước khi code. CHƯA đóng băng.

## CỜ
- 🟡 DCA_GRID = ON (suy từ câu 10) — xác nhận.
- 🟢 Trailing weak/strong: BỎ nhánh cũ, thay bằng công thức liên tục theo selector (xem EXIT).
     ⇒ TS_GIVEBACK_FLOOR / TS_MIN_GAP / TS_GIVEBACK_RATIO trở nên vô nghĩa (bỏ).
- 🟡 OFF_FLAT_HARD = ? (chưa trả lời) — nhưng budget redesign (câu 14) sẽ định lại phần này.

## LABEL
- 🟢 2-sided triple-barrier.
- 🟢 SL (adv) = **0.40** (câu 6: giảm 40% khó hồi; dưới 40% còn hồi ngắn hạn). Hợp với DCA-tolerant.
- 🟡 TP (fav) = 0.06 (giữ nguyên) — xác nhận? (bất đối xứng TP 6% / SL 40% là CỐ Ý cho strategy nhồi-giữ?)
- 🟡 horizon = 4h (giữ) — xác nhận.
- 🔴 Lấy mẫu (câu 2): chưa chốt 1h hay 4h non-overlap. PHẢI chốt (grid 15m cũ = overlap = leak L1).

## GATE / ENTRY
- 🟢 MIN_MOMENTUM_15M: [0.005, 0.02]  (Uni xác nhận range cũ 0.0168→0.008 là leak, nới lại rộng).
- 🟢 PREDICT_SYMBOL_RATE_MAX_THRESHOLD: [0.1, 0.3]. (Đã verify: backtest DÙNG biến này trong
     checkSignalDynamic — dù tên prod có thể là SELECTOR_SCORE_MAX, backtest đọc đúng biến này.)
- 🟢 AI_DYNAMIC_MULTIPLIER: [1.0, 3.0].
- 🟢 AI_DYNAMIC_MIN: [0.1, 1.0].

## MARKET
- 🟢 MS_DOWN_BIG_AVG: [-0.06, -0.025].

## DCA (grid ON) — nới [0.5×, 1.5×] hiện tại
- 🟢 DCA_GRID_L1 (-0.50) → [-0.25, -0.75]
- 🟢 DCA_GRID_STEP (0.20) → [0.10, 0.30]
- 🟢 DCA_GRID_LEGS (3) → [2, 4] int
- 🟢 DCA_GRID_W_RATIO (2.0) → [1.0, 3.0]
- 🟡 DCA_GRID_SCALE → cần giá trị GỐC (đang set qua env, không default hardcode) để nới.

## EXIT / trailing
- 🟢 RATE_PROFIT_STOP_MARKET: grid {0.05, 0.06, 0.07, 0.08} (sàn phủ fee+funding+slip).
- 🟢 TS_PROFIT_MULTIPLIER: grid {2, 3, 4, 5} (nhân ngưỡng ratchet trong updateTPSL).
- 🟢 TS_MAX_GAP: grid [0.08 .. 0.20] step 0.02 (chưa động ở WFO cũ → sạch).
- 🟢 CÔNG THỨC TRAILING MỚI (câu 5, câu 12): thay branch weak/strong bằng gap LIÊN TỤC theo
     selector pred CỦA CHÍNH COIN. BỎ: TS_MAX_GAP_WEAK, TS_WEAK_MOMENTUM_THRES.
     🔴 HƯỚNG DẤU chưa chốt: gap phải RỘNG cho coin TỐT (nuôi winner), HẸP cho coin XẤU (chốt sớm).
        Đại số ×pred hay ×(1-pred) tuỳ orientation của selector score (code có chỗ ghi "thấp=tốt",
        symbolPred=1-p6) — dễ code NGƯỢC. Chốt bằng SEMANTIC ở trên, pin đại số lúc code (verify orientation).
- 🟡 TS_DYNAMIC_K (0.29774): chưa cho range — cần (nó nâng ngưỡng dời SL theo predReturn15M×K).

## BUDGET — câu 14: REDESIGN toàn bộ TradeUtils.managerBudget (code task, DEV)
- 🟢 BỎ genes cũ: BUDGET_MARGIN_RATIO_1 (đã chết), BUDGET_MARGIN_RATIO_2, BUDGET_DIVIDER_2.
- 🟡 Logic mới = ? (chưa thiết kế) — phải xong + đóng băng TRƯỚC phase 2.

## OBJECTIVE / EVAL
- 🟢 O = median − 0.5·std(Calmar), phạt 2 chiều (câu 4, giữ).
- 🟢 n_trials = 200. Stopping = hết 200 HOẶC 50 trial liền không cải thiện O.
- 🟡 CPCV N=8 k=2 gap=purge+embargo — xác nhận.

## GENE BỎ (chết / thay)
- 🟢 HARD_RISK_LIMIT_4H (chết) · BUDGET_MARGIN_RATIO_1 (chết) · TS_MAX_GAP_WEAK · TS_WEAK_MOMENTUM_THRES
     · TS_GIVEBACK_FLOOR/MIN_GAP/GIVEBACK_RATIO (thay bằng công thức mới).
