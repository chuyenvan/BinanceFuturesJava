# HPO/WFO mechanism + ROLLING WFO run (2026-08-23)

## ⭐ KẾT QUẢ ROLLING WFO (per-fold HPO N=30, non-frozen) — DONE 2026-08-23 15:21 UTC
DONE=18/18 FAILED=0. Per-window (win | WFE | OOS_pnl | trades | note):
```
w0  WFE=0     pnl=438   tr=108  CAPITAL_LOCK   (train 2021 – degenerate, bỏ)
w1  WFE=1.11* pnl=486   tr=318  CAPITAL_LOCK   (train chạm 2021 – bỏ)
w2  WFE=0     pnl=0     tr=0    ZERO_TRADES
w3  WFE=0.34  pnl=124   tr=53   CAPITAL_LOCK
w4  WFE=0     pnl=0     tr=0    ZERO_TRADES
w5  WFE=0.18  pnl=296   tr=32   CAPITAL_LOCK
w6  WFE=0.24  pnl=131   tr=22   TOO_FEW_TRADES
w7  WFE=0.20  pnl=47    tr=16   TOO_FEW_TRADES
w8  WFE=0.59  pnl=1827  tr=43   ✅ SUCCESS
w9  WFE=0.24  pnl=1147  tr=55   CAPITAL_LOCK
w10 WFE=0.20  pnl=62    tr=34   CAPITAL_LOCK
w11 WFE=0.29  pnl=265   tr=32   CAPITAL_LOCK
w12 WFE=0.33  pnl=23    tr=24   TOO_FEW_TRADES
w13 WFE=0.06  pnl=27    tr=6    TOO_FEW_TRADES
w14 WFE=0.06  pnl=46    tr=9    TOO_FEW_TRADES
w15 WFE=2.32* pnl=3542  tr=217  CAPITAL_LOCK
w16 WFE=0.015 pnl=17    tr=35   CAPITAL_LOCK
w17 WFE=0     pnl=0     tr=0    ZERO_TRADES
```
(*WFE>1 = cả IS_fit lẫn OOS_fit đều nằm trong vùng penalty/reject sentinel −100000 → tỉ số VÔ NGHĨA, không phải "tốt".)

### VERDICT (thận trọng, có caveat)
- **Chỉ 1/18 fold SUCCESS thật (w8, WFE=0.59).** Fittable windows (w4-w17) đa số `TOO_MUCH_CAPITAL_LOCK` / `TOO_FEW_TRADES` / `ZERO_TRADES`, WFE phần lớn **<0.3** (ngưỡng overfit).
- **Tổng OOS_pnl per-fold ≈ 8.5k vs frozen baseline 22.7k → frozen cao gấp ~2.7×.** Khi HPO trung thực trên train-only, hiệu năng SỤP so với bộ param cố định arm26.
- **Kết luận:** đây là **tín hiệu tiêu cực mạnh về "edge robust"** — bộ frozen arm26 (22687) nhiều khả năng là điểm may/curve-fit ở tầng meta, không sống sót khi tối ưu per-fold trung thực. Corroborate nghi ngờ của user ("đang leak/sai", "edge gì có thực").
- **CAVEAT (không over-claim "vô edge"):**
  1. N=30 THƯA cho 16-dim → có thể search chưa đủ để tìm config tốt (không phải chắc chắn không tồn tại).
  2. Fitness sentinel −100000 (capital-lock/reject) làm IS_fit/OOS_fit/WFE nhiễu → WFE ratio nhiều fold vô nghĩa; tín hiệu đáng tin hơn là **phân bố NOTE** (đa số capital-lock/few-trades) + tổng pnl thấp.
  3. Chạy trên label **1-chiều cũ + chưa vá overlap** → đây là đo pipeline HIỆN TẠI, chưa phải bản rebuild 2-chiều.
- **Hệ quả hành động:** (a) shadow forward = nguồn sự thật, không tin 22687; (b) rebuild 2-chiều leak-free là đúng hướng — và phải đo lại rolling trên bản rebuild để so; (c) vấn đề `TOO_MUCH_CAPITAL_LOCK` lặp lại khắp fold = đúng bệnh "bóp vốn" project đã biết.

---

## WFO framework CÓ SẴN HPO per-fold (không phải build mới)
- FROZEN mode (baseline 22687): env `WFO_FROZEN_GENOME` + `WFO_N_SAMPLES=1` → genome cố định, không search.
- HPO/SEARCH mode: KHÔNG frozen + `WFO_N_SAMPLES=N` → mỗi window sample N genome, fit TRAIN (IS), chọn bestGenome (HPOFitnessCalculatorV4), test OOS. Report: `IS_fit|OOS_fit|WFE|OOS_pnl|OOS_maxDD|OOS_calmar|trades`. **WFE=OOS_fit/IS_fit; WFE<0.3=overfit**.
- Tool 1 window: `com.binance.chuyennd.ai_ml.wfo.VerifyOneWindow <winIdx>`.
- Recipe: `WFO_N_SAMPLES=30 WFO_SEED_BASE=42 WFO_DISABLE_DCA=1`, ranges MOM15/TSMULT default.

## Genome = 16 gene
tsMult[1.0,8.0]. Genes: MIN_MOMENTUM_15M, PREDICT_SYMBOL_RATE_MAX_THRESHOLD, AI_DYNAMIC_MULTIPLIER, AI_DYNAMIC_MIN, HARD_RISK_LIMIT_4H, MS_DOWN_BIG_AVG, DCA_LOSS_BIG_DOWN, DCA_TIME_BIG_DOWN, RATE_PROFIT_STOP_MARKET, TS_PROFIT_MULTIPLIER, TS_DYNAMIC_K, TS_MIN_GAP, TS_GIVEBACK_RATIO, BUDGET_MARGIN_RATIO_1/2, BUDGET_DIVIDER_2. N=30 THƯA cho 16-dim.

## RÀNG BUỘC: HPO không fit được trên 2021
- Window 0 train 2021 → ZERO_TRADES (2021 không prediction, leakFreeFrom=2022-01-01). Fittable = train ≥2022 → w04..w17. w00-w03 bỏ.
- FROZEN 18-window baseline vẫn hợp lệ (train không fit).

## Chi phí: 1 sample ≈ 6-8 phút; N=30/window ≈ 2-3h (SMART_CACHE=1). Rolling toàn bộ chạy Kaggle parallel (~1.5h wall, 5 worker).

## Rolling WFO harness (xval4_rolling, 2026-08-23)
- `_xval4_rolling.sh`: patch 5 run_worker.py `WFO_N_SAMPLES=30 WFO_SEED_BASE=42 WFO_DISABLE_DCA=1 WFO_LEASE_MIN=240 WFO_MAX_IDLE_LOOPS=6`. Reset non-frozen 18 window N=30. Fanout 5 worker retry.
- Output: /home/ubuntu/xval4_rolling/{RES.txt, progress.log, REPORT_rolling.md}.
- Caveat: Kaggle ticker cũ 2023-2025 hơi stale (pre-clean 07-07); geo-block giết worker restricted (retry bù).

## exchange_info offline fix — ĐÃ COMMIT (chưa build/deploy)
- Repo device: E:\educa\source\github\20260415\BinanceFuturesJava. Commit **b09f52e** branch `fix/exchange-info-offline-env`: ClientSingleton.initClient() đọc EXCHANGE_INFO_PATH env/sysprop → fallback hardcoded. Chưa push, chưa build.

## Rebuild leak-free 2-chiều — Phase-1 code XONG (branch `feat/leakfree-2sided-rebuild`, chưa push, chưa compute)
- `ee4e0b0` gate embargo (GATE_PURGE_MS+GATE_LABEL) — vá L1 leak live.
- `b11c737` selector label 2-chiều triple-barrier (fav vs adv, env-param; maxAdv là ratio ÂM → adv_hit=maxAdv≤−SEL_ADV_PCT).
- `b062a4c` selector grid configurable (SELECTOR_GRID_MIN + SEL_SAMPLE_MODE nonoverlap) + tách purge.
- `f7658eb` selector predwf nonoverlap downsample TRAIN-only, giữ OOS dày + purge.
- Số CẦN CHỐT (Phase-2): SEL_ADV_PCT (SL, placeholder 0.03), SEL_FAV_PCT (0.06?), SEL_SAMPLE_MODE, gate 2-chiều?
- Phase-2 đề xuất: A/B 1 fold (label mới vs cũ) trước khi regen full.

## Baseline chốt: local 22687.6 (18w) == Kaggle 22595.0 (0.4%). Xem baseline_seal_jar_rootcause_2026-08-23.md.
