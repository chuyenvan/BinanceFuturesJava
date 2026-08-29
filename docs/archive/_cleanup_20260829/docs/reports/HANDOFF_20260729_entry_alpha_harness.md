# HANDOFF 2026-07-29 — Entry-alpha: VERDICT M (edge THẬT, bottleneck = WFO/HPO harness)

> Nối tiếp `HANDOFF_20260727_entry_alpha.md`. Chuỗi bằng chứng đầy đủ §A–§O ở
> `reports/gate_freq_ablation_20260727.md`. File này = bản nối-mạch 30 giây.

## TL;DR
- **Nhánh entry-alpha KHÔNG đóng.** Selector rank-skill là THẬT và **trải rộng** (không chỉ quý w15).
- **Bottleneck KHÔNG phải gate, KHÔNG phải selector, KHÔNG phải regime** → là **WFO/HPO HARNESS tự bóp chính nó**.
- **NEXT = sửa 3 chỗ harness (rẻ→đắt) rồi N=30 confirm. KHÔNG build gate/model mới.**

## Verdict M — bằng chứng chốt (step-2 frozen leakage-free)
Genome đóng băng train CHỈ trên 2022 (không thể leak), apply forward, rank-K8, MOM15=0.010, funding-fee ON:
- **11/13 window OOS non-w15**: vừa winRate>50% vừa net dương sau phí.
- **net/trade non-w15 = 8.59 ≥ w15 = 7.97**; w15 chỉ chiếm **28%** Σnet → w15-dominance là **artifact**, không phải bản chất.
- Nhánh A (frozen) **thắng** B (production) 2.34× Σnet → breadth **KHÔNG phải leakage**; genome production đang dưới tối ưu.
- Window fail ăn đúng `TOO_MUCH_CAPITAL_LOCK` (7) + `TOO_FEW_TRADES` (4) → **harness loại bỏ chính window ĐANG LÃI**.

## Đã GIẾT dọc đường (đừng thử lại)
- hard-SL/TP first-touch, short bottom-decile, endpoint (alpha~0).
- **oi_z** mọi dạng (veto-chồng + thay-gate): frequency destroyer, loại.
- **offset-sweep**: bỏ top-rank chỉ MẤT edge → top-K CHÍNH LÀ edge, không phải fake-pump. Lever chết.
- **gate**: sweet-spot 0.010; <0.010 tệ hơn; gate→0 = BURN −55k. Đã quét kỹ.
- **HPO N=30 argmax = overfit w15** (lặp 3 lần: WFE 0.24 gate-artifact §J; K5 re-tune TỆ hơn fixed; K8 breadth sụp §L). → fixed/frozen genome generalize tốt hơn HPO.

## Config tốt nhất hiện tại
gate `MIN_MOMENTUM_15M=0.010` · oi_z OFF · selector **rank-K8** (top-8/timestamp) · trailing · DCA off · funding-fee ON · `TICKER_SOURCE=file`.

## NEXT (thứ tự, mỗi bước có gate dừng — đừng làm cả 3 rồi mới test)
1. **[đọc trước] Audit constraint `TOO_MUCH_CAPITAL_LOCK` + `TOO_FEW_TRADES`** — CHƯA ai đọc logic/ngưỡng, mới chỉ dùng như label. Đây là thứ loại nhầm window lãi → target trực tiếp nhất, rẻ nhất. Nới có nguyên tắc.
2. **Fix fitness mismatch (§K):** HPO chọn genome bằng `Calmar×factor` nhưng CHẤM bằng `raw-PnL-WFE` → align chọn=chấm; cân nhắc bật lại `posYearRatio` (đang tắt cho window 12 tháng).
3. **(chỉ nếu 1+2 chưa đủ)** bỏ per-window HPO argmax → genome gần-cố-định/regularized (argmax là nguồn w15-overfit).
4. **Sau MỖI bước: N=30 full 13-window non-w15 confirm.** Mọi số M hiện tại là **N=1 shape** → chưa production-ready cho tới khi N=30 pass trên harness đã sửa.

## Uncommitted — cần review rồi commit hoặc bỏ (KẺO MẤT/LẪN)
- `SELECTOR_RANK_TOPK` + `SELECTOR_RANK_OFFSET`: `Configs.java` + `SimulatorMarketLevelTicker1MStopLoss.java` (~L294–309).
- `GATE_COUNT_ONLY`: `StrategyWfoTask.java`.
- frozen-genome inject + 6 metric mới (winRate/avgWin/avgLoss/profitFactor/cost/medianTradePnl) + `SIM_APPLY_FUNDING`: `StrategyWfoTask` / `HPOFitnessCalculatorV4` / `Configs` → jar `binance-lf-frozen-1.0.0.jar` (deployed Oracle).
- driver: `orchestrator/tools/stage1_frozen_derive.sh` + `stage2_frozen_ab.sh` (đã sửa regex `RESULT_JSON (\{.*\})`).

## Caveat / lỗ hổng còn treo
- **Mọi PnL TRƯỚC step-2 chưa trừ funding-FEE** (chỉ có funding-selector feature). Step-2 đã bật fee thật (`SIM_APPLY_FUNDING`).
- **w16 / 2026 forward chưa có evidence** (Kaggle geo-block Binance API; Oracle cũng zero-trade). Lỗ hổng out-of-sample gần nhất.
- avgLoss nhánh A khá béo (đuôi rủi ro, DCA-like) — phải nhìn kỹ khi N=30 confirm.

## Nguồn đầy đủ
- `docs/reports/gate_freq_ablation_20260727.md` §A–§O (toàn chuỗi 15 experiment).
- `D:\claudedata\`: `probe_a_report.md` (entry=HYBRID absolute), `probe_b_fitness.md` (fitness 3-tầng mismatch), `probe_c_w15_dissection.md` (bác regime), `step2_final_verdict.md` (verdict M), `gonogo_results.md`, `rank_k_sweep.md`, `freq_probe_table.md`.
- `docs/INFRA_FACTS.md` (Oracle ce / Kaggle clean-venv / gotchas / fire-and-forget).

## Quyết định thuộc Uni
Chưa commit gì. Hướng (sửa harness) đã rõ từ verdict M; chọn bắt đầu bước 1/2/3 + có commit code uncommitted không = quyết của Uni.
