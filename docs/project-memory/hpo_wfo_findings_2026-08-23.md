# HPO/WFO mechanism + ROLLING WFO run (2026-08-23)

## WFO framework CÓ SẴN HPO per-fold (không phải build mới)
- FROZEN mode (baseline 22687): env `WFO_FROZEN_GENOME` + `WFO_N_SAMPLES=1` → genome cố định, không search.
- HPO/SEARCH mode: KHÔNG frozen + `WFO_N_SAMPLES=N` → mỗi window sample N genome, fit TRAIN (IS), chọn bestGenome (HPOFitnessCalculatorV4), test OOS. Report: `IS_fit|OOS_fit|WFE|OOS_pnl|OOS_maxDD|OOS_calmar|trades`. **WFE=OOS_fit/IS_fit; WFE<0.3=overfit**.
- Tool 1 window: `com.binance.chuyennd.ai_ml.wfo.VerifyOneWindow <winIdx>`.
- Recipe: `WFO_N_SAMPLES=30 WFO_SEED_BASE=42 WFO_DISABLE_DCA=1`, ranges MOM15/TSMULT default.

## Genome = 16 gene
tsMult[1.0,8.0]. Genes: MIN_MOMENTUM_15M, PREDICT_SYMBOL_RATE_MAX_THRESHOLD, AI_DYNAMIC_MULTIPLIER, AI_DYNAMIC_MIN, HARD_RISK_LIMIT_4H, MS_DOWN_BIG_AVG, DCA_LOSS_BIG_DOWN, DCA_TIME_BIG_DOWN, RATE_PROFIT_STOP_MARKET, TS_PROFIT_MULTIPLIER, TS_DYNAMIC_K, TS_MIN_GAP, TS_GIVEBACK_RATIO, BUDGET_MARGIN_RATIO_1/2, BUDGET_DIVIDER_2. N=30 THƯA cho 16-dim (best-of-30 random) — đủ tín hiệu WFE, không đủ tuning production.

## RÀNG BUỘC: HPO không fit được trên 2021
- Window 0 train 2021 → CẢ 30 sample ZERO_TRADES (2021 không có prediction, leakFreeFrom=2022-01-01). w04 (train 2022) OK: sample cho 234 trades.
- Fittable windows = train hoàn toàn ≥2022 → w04..w17 (OOS 2023-2026). w00-w03 (train chạm 2021) degenerate/partial — BỎ QUA khi đọc kết quả.
- FROZEN 18-window baseline vẫn hợp lệ (train không fit).

## Chi phí: 1 sample ≈ 6-8 phút; N=30/window ≈ 2-3h (SMART_CACHE=1). Rolling toàn bộ bất khả thi Oracle → chạy Kaggle parallel.

## ĐANG CHẠY: Rolling WFO trên Kaggle (xval4_rolling, launch 2026-08-23 13:46 UTC)
- `_xval4_rolling.sh`: patch 5 run_worker.py thêm `WFO_N_SAMPLES=30 WFO_SEED_BASE=42 WFO_DISABLE_DCA=1 WFO_LEASE_MIN=240 WFO_MAX_IDLE_LOOPS=6` (lease 240m vì 1 window HPO ~2-3h, tránh reclaim giữa chừng). Reset non-frozen 18 window N=30. Fanout 5 worker, retry 8 attempt tới PENDING=0.
- Output: /home/ubuntu/xval4_rolling/{RES.txt, progress.log, REPORT_rolling.md}.
- Kỳ vọng: w04-w17 có WFE + OOS_pnl thật. Đọc: bao nhiêu window WFE>=0.3 (không overfit), OOS_total so arm26 22687.
- Caveat: Kaggle ticker cũ 2023-2025 hơi stale (pre-clean 07-07) → HPO 2023-2025 hơi nhiễu; geo-block giết worker restricted (retry bù). Đủ cho tín hiệu edge lần đầu; muốn exact thì re-upload ticker clean sau.
- Lịch tự kiểm: trigger sau ~4h đọc kết quả + phân tích WFE.

## exchange_info offline fix — ĐÃ COMMIT (chưa build/deploy)
- Source repo có ở device: E:\educa\source\github\20260415\BinanceFuturesJava (git). Branch `module` HEAD 311bb29 = build ra live jar.
- Commit **b09f52e** branch `fix/exchange-info-offline-env`: `ClientSingleton.initClient()` đọc EXCHANGE_INFO_PATH từ env/sysprop → fallback hardcoded. Chưa push remote.
- Chưa build: build của user chạy Windows (build_fontfix.bat → mvn -DskipTests package → shade). Claude không chạy .bat Windows; build cloud được nhưng jar bytes lệch (verify bằng reproduce). Kích hoạt fix cần: build jar branch này + set EXCHANGE_INFO_PATH env + đặt exchange_info.data (md5 4ef9f42d, có trong java-run-lc) cho Oracle + Kaggle run_worker.py.

## Baseline chốt: local 22687.6 (18w) == Kaggle 22595.0 (0.4%, residual ticker cũ). Xem baseline_seal_jar_rootcause_2026-08-23.md.
