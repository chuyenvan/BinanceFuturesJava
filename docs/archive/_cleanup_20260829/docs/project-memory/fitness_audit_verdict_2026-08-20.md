# Audit fitness (kiểm chứng thuần, chưa đổi gì) — VERDICT (2026-08-20)

## Câu hỏi user
"Làm mịn fitness và kiểm chứng thật cẩn thận" → chọn: audit fitness trước khi đổi gì.

## VERDICT: Fitness ĐÚNG và ĐÁNG TIN. Không cần "làm mịn" để sửa sai. Verdict FAIL/capital-lock là chẩn đoán THẬT của config, không phải lỗi thước đo.

## Bằng chứng

### 1. Fitness logic verified — TestFitnessV41 5/5 PASS
Chạy `java -cp binance-fresh-20260809.jar ...hpo.TestFitnessV41` (cwd có config.properties):
- Case A: 60 lệnh 90d → SUCCESS, fitness=calmar=3.0 ✓
- Case B: 8 lệnh → TOO_FEW ramp −72413.79, totalProfit thật 160 ✓
- Case C: window-days fix (10<29 → TOO_FEW) ✓
- Case D: profit≤0 → BURN, fitness −100060, ddPct điền thật ✓
- Case E: pctHeld=6.667% → CAPITAL_LOCK, fitness −100006.664 ✓ (khớp REJECT_BASE − pctHeld×100)
→ Công thức + thứ tự constraint + đơn vị đều đúng. Case E xác nhận công thức decode IS_fit.

### 2. Constraint/ngưỡng sane (HPOFitnessCalculatorV4)
MAX_DD_PCT=0.65, MAX_PCT_HELD_OVER_7D=0.02, MIN_POS_YEAR_RATIO=0.80 (chỉ áp khi ≥2 năm), minTrades=max(5, windowDays×0.33). calmar=totalProfit/maxDrawdown. Thứ tự: TOO_FEW → BURN → OVER_MAXDD → CAPITAL_LOCK → UNSTABLE → SUCCESS(calmar×freq-factor). freq-factor chỉ đổi finalFitness (chọn genome), KHÔNG đổi note/PnL/calmar → verdict pre-registered giữ nghĩa.

### 3. pctHeldOver7d KHÔNG phải artifact biên window — verified
Fitness đọc `orders = allOrderDone.values()` (chỉ lệnh đã đóng). Simulator (`SimulatorMarketLevelTicker1MStopLoss` dòng 479-495): lệnh mở cuối kỳ → mark-to-market ở giá đóng, `timeUpdate` = tick cuối → hold-time = entry→cuối-window = thời gian ride THẬT. Lệnh mở <7d gần biên KHÔNG bị đếm; sai lệch biên (nếu có) là UNDERcount (truncate lệnh sắp đóng ở window sau), không inflate. → 17-38% held>7d là THẬT, do lệnh không-có-exit ride cả window.

### 4. Caveat nhỏ (không phải bug fitness): WFE dưới N=1 khi BURN
`wfe = bestIsPnl != 0 ? oosPnl/bestIsPnl : 0`. Comment nói "bestGenome luôn isPnl>0" — ĐÚNG khi N>1 (chọn best loại BURN), nhưng SAI khi N=1 (bestGenome=baseline bất kể). 2 window BURN (w12,w14) có isPnl≤0 → WFE lật dấu/vô nghĩa. 16 window capital-lock thì isPnl>0 (capital-lock ≠ profit≤0) → WFE hợp lệ. Ảnh hưởng: WFE median (0.325) hơi nhiễu bởi 2 giá trị rác. Minor.

## Hệ quả
- Thước đo (fitness) chuẩn → tin được verdict → **vấn đề thật nằm ở config chiến lược**, không ở fitness.
- Capital-lock = config thiếu disaster-exit (HARD_STOP_LOSS_RATE=0, HARD_SL_PCT=0, TIME_STOP_HOURS=0) → lệnh không pump đủ arm 26% thì ride vô hạn (xem doc capital_lock_rootcause). "Làm mịn fitness" KHÔNG cần cho tính đúng đắn; chỉ cần nếu sau này bật HPO-search (N>1) để có gradient + robustness.
- Đề xuất bước tiếp (chờ user): fix disaster-exit (TIME_STOP_HOURS/SIM_HARD_SL_PCT, env, không rebuild) → chạy lại frozen-eval N=1 → xác minh pctHeldOver7d<2% + verdict/WFE cải thiện. Sửa WFE-under-N=1-BURN nếu muốn (guard isPnl>0).

## Infra
java-run-lc = pristine Aug2 (sạch), run_worker=K5, không process chạy. Anchor arm=26 đã reconcile K-grid (FULL 20281 vs 20247).
