# Baseline chốt + cross-harness seal + lỗ hổng exchange_info (2026-08-23)

## TL;DR
- **Baseline local = FULL 22687.6 / 18 window / 89% dương** (2022-01 → 2026-07), jar `binance-fresh-20260809` (khớp live 96%, StrategyWfoTask identical live), corpus ticker mở rộng tới 2026-07-01.
- **Kaggle tái hiện = 22595.0 / 18w** sau khi thay jar cũ→fresh + upload ticker Q2. Lệch aggregate 0.4% (trước fix jar: 17060 vs 20240 = 16%). w15/w16/w17 IDENTICAL.
- **NHƯNG chưa byte-exact**: per-window lệch không đều (w03: 113.4 Kaggle vs 159.6 local = 29%!, w01 lệch 107) — triệt tiêu nhau nên aggregate khớp. Nguyên nhân = lỗ hổng exchange_info live-call (dưới).
- 2 fold 3-tháng 2026 (mới, đều dương): w16 (2026-01→04)=1888.7/302, w17 (2026-04→07)=558.0 local / 559.1 Kaggle /127.

## Lỗ hổng reproducibility: LIVE Binance exchangeInfo trong backtest (CHƯA FIX)
- Stack: `StrategyWfoTask.backtest → SimulatorMarketLevelTicker1MStopLoss.createOrder → Utils.calQuantityTest → ClientSingleton.initClient → getExchangeInformation` = **gọi LIVE Binance REST** lấy stepSize/precision/quantity.
- Kaggle region bị chặn → `BinanceApiException: Service unavailable from a restricted location` → job fail → reclaim → worker region khác chạy lại.
- Worker dùng `exchange_info.data` cached → khớp local; worker fetch live (region không chặn, exchangeInfo mới) → precision/coin-universe khác → PnL window lệch (nặng ở window cũ 2022-2023 vì coin delisted/precision đổi). → kết quả phụ thuộc "region lottery" = **non-deterministic**.
- **Local 22687 CŨNG dính**: Oracle fetch live exchangeInfo lúc chạy → không tái lập 100% nếu Binance đổi info.
- **FIX cần làm**: ép backtest dùng exchangeInfo OFFLINE cố định (`exchange_info.data` đã có trong java-run-lc), cấm REST trong calQuantityTest → hết geo-error + Kaggle==local exact + baseline reproducible thật.

## Bằng chứng jar (class-level md5)
| | own_classes | vs LIVE identical |
|---|---|---|
| LIVE `binance-java-sdk-1.2.4.jar` (6a8b322a) | 509 | — |
| LOCAL_fresh `binance-fresh-20260809.jar` (01574328) | 503 | 481/503 (96%) |
| KAGGLE cũ `1.2.4-shaded` (0195314e) | 461 | 0/461 (0%) — jar stale, đã thay |

## Baseline 18-window per-window (local vs Kaggle)
| w | OOS | local | Kaggle | trades |
|---|---|---|---|---|
w00|2022-01→04|854.6|855.8|115
w01|2022-04→07|2681.7|2574.6|388
w02|2022-07→10|419.1|413.6|39
w03|2022-10→2023-01|159.6|113.4|165
w04|2023-01→04|463.7|464.4|49
w05|2023-04→07|198.7|190.7|95
w06|2023-07→10|663.9|659.9|52
w07|2023-10→2024-01|1429.5|1436.2|98
w08|2024-01→04|2659.3|2695.4|212
w09|2024-04→07|1223.3|1235.6|256
w10|2024-07→10|2248.2|2231.1|146
w11|2024-10→2025-01|1356.3|1370.1|248
w12|2025-01→04|-371.9|-350.3|468 BURN
w13|2025-04→07|1356.5|1357.0|172
w14|2025-07→10|-963.2|-961.8|64 BURN
w15|2025-10→2026-01|5861.5|5861.5|758
w16|2026-01→04|1888.7|1888.7|302
w17|2026-04→07|558.0|559.1|127
FULL|—|**22687.6**|**22595.0**|—

## Param / HPO — trạng thái & khuyến nghị (câu hỏi cốt lõi: edge có thực?)
- **Hiện tại param FIX CỨNG** (frozen genome qua env: arm26/K5/DCA-off/thresholds). KHÔNG có HPO per-fold. Cái đang chạy = "fixed-param walk-forward EVALUATION", KHÔNG phải walk-forward OPTIMIZATION.
- Param cố định sinh từ HPO experiment trước (kgrid/arm_sweep/gate_ab). **Nếu tune trên bất kỳ phần nào của 2022-2026 (kỳ OOS) → leak in-sample → 22687 lạc quan, KHÔNG chứng minh edge.** Rủi ro #1.
- 3 cách: (A) fix cứng [hiện tại, chỉ hợp lệ nếu freeze từ data trước toàn bộ OOS]; (B) anchored WFO [HPO 1 lần trên train đầu → freeze → eval OOS, bước tối thiểu để tin edge]; (C) rolling WFO [HPO train-only mỗi fold → test OOS kế → roll, gold standard, đắt].
- Khuyến nghị: (1) fix exchange_info offline TRƯỚC; (2) chạy (B) làm mốc; (3) nếu ổn → (C) chốt edge; (4) đổi SL/TP "nuôi lãi cắt lỗ" cũng phải qua WFO discipline, không tune tay trên OOS.

## Data
- ticker corpus: 2008 file, 2021-01-01→2026-07-01, corpus_md5=b329fa06. funding_md5=779e2f8e. predwf 20260101+20260401 phủ Q1/Q2. market→2026-10, pred→2026-11. Selector pred nằm TRONG funding.bin (ds_base không có predwf riêng; run_worker không mount predwf → w16/w17 chạy được chỉ với ds_base).
- 2021 không có prediction (leakFreeFrom=2022-01-01); 2021 chỉ dùng làm TRAIN fold đầu → đúng, WFO không cần.
- Kaggle datasets (không version-pin, worker lấy latest): java-run-lc (jar fresh + exchange_info.data), wfo-ticker-2021..2026pf, wfo-ds-xval. jobstore = aerospike 161.118.212.3:3222 ns=test (worker WFO_STATE).

## Next
1. Fix exchange_info offline (gỡ geo-error + seal exact). 2. Anchored HPO (B). 3. Rolling WFO (C) chứng minh edge. 4. Redesign SL/TP qua WFO.

## HARD RULES
- Oracle chỉ 1 job. Local WFO: WFO_SMART_CACHE=0 + -Xmx16g, KHÔNG 4yr-train (thrash).
