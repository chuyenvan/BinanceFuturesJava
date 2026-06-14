# TASK-033: Deploy đợt 2 lên 242 — gộp 027+028+029+030+031 [CCD4]

- **status:** DOING (CCD-024). Giao CCD4.
- ▶️ **CCD4 LÀM NGAY (KHÔNG chờ user):** build jar + soát Configs chung 027/030 + **chạy lấp-gap 15m/4h@242** (Aggregate đọc 1m@242, chạy TRÊN 226 — là job DATA, không phải deploy) + soạn lệnh deploy+restart + checklist verify + backup `.bak`. CHỈ bước **deploy jar mới + restart 2 process live** mới giao user tay. Đừng ngồi chờ.
- **owner:** CCD-024 · **updated:** 2026-06-14
- Theo runbook `docs/DEPLOY_242.md` (đã có từ 023) + bổ sung dưới.

## Phạm vi — 5 fix (đều REVIEW, sửa live)
- **027** entry: #6 gỡ V4 dead (giữ V3), #7 size theo price_realtime+tuổi, #8 aiBrain null→alert+fail-fast, NPE BTC. File: `OnnxInferenceManager`, `DetectEntry`, `Configs` (field PRICE_REALTIME_MAX_AGE_MS).
- **028** ingest: funding guard, watchdog bật lại+fix counter, HttpRequest classifyError.
- **029** concurrency (`409ab7e`): striped-lock writeMinuteBatch, ForkJoinPool chung, swap-map+finally.
- **030** parity/config (`b2728db`): sim reject pred==null (**CONFIG_VERSION v9**), assertLiveRuntime ở 2 live main, document-only DIED.
- **031** forward kline_15m/4h ghi 242 (`dd883f9`).
- ⚠️ **016/019/gỡ-crawl ĐÃ deploy đợt 1 (live) — KHÔNG gồm lại.**

## Build (1 jar, soát kỹ)
- Build từ working tree gồm CẢ 5 fix. **Soát `Configs.java` dùng chung 027+030**: phải có cả `PRICE_REALTIME_MAX_AGE_MS` (027) lẫn CONFIG_VERSION v9 (030). Soát file riêng 027 (`OnnxInferenceManager`/`DetectEntry`) có trong jar (đừng cherry-pick sót).
- Compile javac11 PASS. Tự test riêng từng phần nếu được (029 đã có Task029ConcurrencyCheck 4/4).

## ⚠️ TIỀN ĐỀ bật 031 — LẤP GAP 15m/4h@242 TRƯỚC
- kline_15m/4h@242 dừng 06-07; gap ~7 ngày > catch-up roller (200 khung 15m ≈ 50h).
- Trước khi bật forward: chạy lại `Aggregate15m4hBtcEth` **ĐỌC `kline_1m_opt`@242** (KHÔNG 226 — 1m@226 cũng dừng 06-07) → ghi 15m/4h@242 lấp 06-07→nay. Rồi 031 forward giữ realtime (4h tự lấp vì 200×4h > 7d).

## Deploy + verify
- **CCD4 tự làm (qua 226, không cần user):** lấp-gap 15m/4h@242 (Aggregate đọc 1m@242) — job DATA, chạy trên 226.
- **CHỈ USER tay:** deploy jar mới + restart 2 process live `BinanceDataIngestor` (016/028/029-ingest/031) + `BinanceOrderTradingManager`/`DetectEntry` (027/030/029-trading) theo **pid-file** (KHÔNG killall). CCD4 soạn sẵn lệnh + checklist cho user.
- **CONFIG_VERSION v9:** nếu đang có HPO chạy → điểm cache cũ thành vô nghĩa. BÁO user trước restart.
- **Verify sau restart:**
  - 031: `kline_15m/4h`@242 ts TIẾN sau biên 15m (sau lấp gap).
  - 028: funding-poll qua guard; watchdog sống (counter tiến); HttpRequest log lỗi thay vì câm.
  - 027: log entry size dùng price_realtime; V4 dead đã gỡ; (aiBrain null→alert khó test, soi log init).
  - 030: live khởi động qua `assertLiveRuntime()` không exit (IS_KAGGLE_MODE=false).
  - chung: `-1130` vẫn hết, FundingFee-Refresh chạy, price_realtime/OI/kline/funding ghi 242, Reporter/Telegram sống.
- **Rollback:** backup jar `.bak` trước; ingest/trade gap bất thường → restore + restart.

## An toàn (luật CLAUDE.md)
- **Deploy jar + restart 2 process live = CHỈ user tay.** CCD KHÔNG tự deploy/restart Ingestor/TradingManager.
- **Ghi DATA 242 (lấp gap qua 226) = CCD làm được** (job data, không phải deploy). Theo luật dọn-job 226. SLF4J.

## Acceptance
- [x] Jar gồm đủ 5 fix (soát Configs chung). — `mvn -o package` PASS (94.2MB); xác nhận 7 class chủ chốt trong jar; Configs có assertLiveRuntime(030)+PRICE_REALTIME_MAX_AGE_MS(027), RunHpoMaster v9.
- [~] Lấp gap 15m/4h@242 xong trước bật 031. — **CHƯA chạy được từ dev** (242 unreachable; job phải chạy TRÊN 226). ĐÃ chuẩn bị: thêm arg `242` cho Aggregate (đọc 1m@242) + runbook + check an toàn độ sâu 1m@242.
- [x] Checklist verify từng fix sẵn sàng. — `docs/DEPLOY_242_dot2.md §3` (027/028/029/030/031 + chung).
- [x] KHÔNG tự deploy; chờ user. — runbook để user bấm; CCD chỉ build+chuẩn bị.

## (Code điền) — TASK-033
- **Build jar (soát Configs):** `mvn -o package` PASS, `target/binance-java-sdk-1.2.4.jar` (94.2MB, build 13:06). `jar tf` xác nhận đủ: OnnxInferenceManager/DetectEntry (027 working-tree), BinanceOrderTradingManager/TickerIngestor (029), Simulator/Configs/RunHpoMaster-v9 (030), Kline15m4hForwardRoller (031). Configs chung: `assertLiveRuntime`+`PRICE_REALTIME_MAX_AGE_MS`. ⚠️ 027 (OnnxInferenceManager/DetectEntry) CHƯA commit (working tree CCD-audit) — build từ working tree GỒM 027; CCD-audit nên commit trước build chính thức.
- **Lấp gap Aggregate@242:** Aggregate cũ hardcode `IS_KAGGLE_MODE=true`→đọc 226 (1m@226 dừng 06-07, KHÔNG lấp được). Thêm **arg `242`** → `IS_KAGGLE_MODE=false` → `getReadClient`→242 đọc 1m LIVE; mặc định (không arg) giữ 226 (backtest TASK-009). Lệnh + ⚠️ KIỂM TRA độ sâu 1m@242 trước (tránh ghi đè tháng-biên mất data) ở `docs/DEPLOY_242_dot2.md §1a`. **CHƯA chạy** (dev không tới 242 — phải chạy TRÊN 226).
- **Verify sau restart:** `docs/DEPLOY_242_dot2.md §3` — per-fix (027 size/price_realtime+V4-gỡ+aiBrain; 028 guard/watchdog/HttpRequest; 029 không mất-nến/không-kẹt-lock; 030 #12 fail-fast lên-được; 031 ts 15m/4h tiến) + chung (-1130 hết, refresh N>0, ghi 242, Reporter). + ⚠️ CONFIG_VERSION v9 invalidate cache HPO v8 (báo user nếu HPO chạy).
- **CHẶN còn lại (giao user/226):** (1) chạy lấp-gap `Aggregate15m4hBtcEth 242` TRÊN 226 (sau khi verify độ sâu 1m@242); (2) deploy jar + restart 2 process live theo runbook (user tay).
