# ROUND 4g — v1.2/c3-live: bỏ tự reset 12h (process strategy/trade) + MINOR-A/B (A1 4f) + K5 firstSentMs

Nhánh `v1.2/c3-live`, trên `d035a086` (4f). Chưa push. Script deploy **không** đổi (vẫn pin jar r4f) — MASTER quyết sau A1.

## 1. Bỏ cơ chế tự reset 12h cho process strategy/trade

### 1.1 Cơ chế hiện có (đọc code)
- `Utils.reset(String)` (`utils/Utils.java`): chờ giây 30–45, re-exec `java -cp <classpath> <sun.java.command>` với env sao chép
  (nên `JAVA_TOOL_OPTIONS` -Xmx3g/GC log giữ được — sửa 10-17), `System.exit(0)`. Nơi gọi:
  1. `BinanceOrderTradingManager.startThreadAutoRestartProgram` — **reset định kỳ** `LIVE_PERIODIC_RESET_HOURS` (mặc định 12).
  2. `Reporter.buildReport` (30′/lần, `executorServiceOrderNew`) — **watchdog** khi `REDIS_KEY_LAST_TIME_CHECK_MARKET` trễ > 15′.
     GIỮ (là cơ chế phục hồi khi vòng thị trường chết, không phải làm mới định kỳ).
  3. `BinanceDataIngestor` (collectData, process riêng): 12h + "Too many symbol price errors" > 50. **KHÔNG đổi** (ingestor
     không đọc `LIVE_PERIODIC_RESET_HOURS`).

### 1.2 Kiểm kê những gì restart "vô tình" làm mới (process strategy/trade)
| mục | trước r4g | cần làm mới? | r4g |
|---|---|---|---|
| model ONNX (gate p15, net015, S1) | nạp 1 lần | không — chỉ đổi khi deploy (restart) | giữ |
| exchangeInfo R7 + UNIVERSE_A1 | `UniverseA1Filter` / `C3LiveRuntime` reload theo mtime (≤ 1 lần/phút), cron 242 15′ | đã tự làm mới | giữ |
| `ClientSingleton` (minQty/tick/notional) | nạp 1 lần | không — không có consumer live (grep 0) | giữ |
| **symbol mapper** (`SimpleSymbolMapper`) | nạp 1 lần lúc init; `getId` symbol mới đọc store (process ghi được) | **CÓ**: id do process KHÁC (collectData/tool) cấp sau init ⇒ `getSymbol(id)` = `UNKNOWN-id` tới restart; process chỉ đọc (shadow Oracle) cấp id CỤC BỘ | **làm mới tại chỗ**: `refreshFromStore()` mỗi `LIVE_MAPPER_REFRESH_MIN` (10′) + `getSymbol` trượt tự đọc lại ≤ 1 lần/phút; KHÔNG BAO GIỜ đổi id đã có trong JVM |
| **ngân sách `LIVE_FEAT_DUMP`** | tổng tick từ lúc khởi động (10-25: env 3000 ⇒ tắt sau 50 h) | **CÓ** | khi reset TẮT: ngân sách theo **ngày UTC**, ngày mới mở lại sau DU TICK / CHAM TRAN / lỗi IO (không mở lại khi JVM đang tắt); `LIVE_FEAT_DUMP_DAILY=0/1` ghi đè |
| `S1FeatDump` | file theo giờ, trần/file | không | giữ |
| TS-EXT ALT_EW | scheduler `TS-EXT` refresh | đã tự làm mới | giữ |
| funding | `LIVE_FUNDING_REFRESH_HOURLY=1` (env 242) | đã tự làm mới | giữ |
| LEGACY | reconcile mỗi tick (`updatePositionInfo`) + file | đã tự làm mới | giữ |
| user-data WS / listenKey (c3_live) | `UserStream`: keepAlive 30′, `listenKeyExpired`/đóng/hết hạn 24h ⇒ kết nối lại backoff 1–60 s, fallback REST | đã tự làm mới; **chưa từng chạy > 12 h liền trong production** (restart 12h che) ⇒ theo dõi ở dry: `[C3-LIVE] … reconnect`, `lastMsgAgoS` | giữ |
| Aerospike / Redis | client singleton tự kết nối lại; `blpop` lỗi ⇒ vòng lặp bắt lỗi | không | giữ |
| sổ c3 / killsw peak / latch / gate buffer | persist file, nạp lúc khởi động | không (restart không cần) | giữ |
| bộ đếm thống kê (`AIRejectFilter`, `DcaProcessor` round-cap) | chỉ log | không | giữ |
| heap | — | xem 1.4 (không rò) | — |

### 1.3 Vì sao v_t_m (shadow v1.1, PID 8468) không tự restart từ 10-27 13:26
- `conf/env.sh` dòng 159 `export LIVE_PERIODIC_RESET_HOURS=0` — thêm lúc deploy v11d+exec-probe **10-23 09:37** (khối
  "[v11d+exec-probe 20261023_0937] chi van hanh (ADDENDUM d)"). Log: `[OPS-RESET] LIVE_PERIODIC_RESET_HOURS=0 => TAT reset dinh ky`
  ở 10-23 09:37:42, 10-27 11:44:01, 10-27 13:26:45. Lần tự restart cuối: 10-23 07:55:42 ("Reset by Schedule").
- 10-27 11:43 (fix featdump) và 13:26 (fix mapper WARN) là restart **tay** do script owner. Nghĩa là v1.1 đã chạy liền
  4 ngày 2 h (10-23 09:37 → 10-27 11:43, PID 18743) trước đó — reset đã tắt từ 10-23, không phải "khác trước" từ 10-27.
- Watchdog Reporter (> 15′) không kích hoạt lần nào từ 10-23.

### 1.4 Rò rỉ bộ nhớ: KHÔNG thấy rò heap
- GC log 242 (`logs/gc_<pid>_*.log`, G1, `-Xlog:gc`); `System.gc()` mỗi 30′ (`Utils.printMemoryUsage` trong Reporter) ⇒ heap sau
  Full GC = tập sống. Theo khối 6 h (min…max, MB):
  - PID 8468 (10-27 13:26 → 10-30 21:50): khởi động 492 → 584 (6 h đầu, nạp cache) → 10-28 06h 553–559 → 10-29 559–563 →
    10-30 18h 558–561. Độ dốc 10-28 06h → 10-30 21h ≈ +4 MB / 63 h (≈ 1,5 MB/ngày, trong nhiễu).
  - PID 18743 (10-23 09:37 → 10-27 11:43, 4 ngày): 595 → 548 (10-24) → 548–559 tới 10-27 — phẳng/giảm.
  - Log "RAM SAU KHI [Total ram used]": 650 (10-20) … 554 (10-27) … 563 (10-30).
- RSS 2,76 GB (VmHWM 3,14 GB) với -Xmx3g -Xms1g: heap committed 1,8–2,3 GB (G1 không trả bớt) + native (ONNX Runtime,
  metaspace, 51 thread, 27 fd). Chỉ có 1 ảnh chụp RSS ⇒ **không loại trừ được rò native**; đề xuất dry ghi RSS/giờ
  (`c3live_status.sh`) — chưa làm (ngoài phạm vi, không đụng 242).

### 1.5 Thiết kế r4g
- `OpsConfig.resolveResetHours(raw, LIVE_PROFILE)`: khai hợp lệ ⇒ dùng; không khai / sai ⇒ **0 cho c3_live/c3_shadow**, 12 cho
  profile khác (HEAD). Log nguồn (`env`/`profile`). Env 242 hiện đã `=0` ⇒ hành vi 242 không đổi.
- `ops/InPlaceRefresh` (chỉ process trading gọi): mapper refresh định kỳ.
- `LiveFeatureDump`: ngân sách theo ngày UTC khi reset tắt.
- `Utils.reset`: `printStackTrace` → SLF4J.

## 2. MINOR-A (A1 4f): userTrades lỗi ⇒ cụm đóng ngay mất realized
- `C3MergedGuard.recoverC3Exit`: userTrades lỗi (một phần hoặc hết) ⇒ trả `Reconciler.RECOVER_RETRY`, thử lại tối đa
  `TRADES_MAX_TRY=5` lần cách `TRADES_RETRY_MS=30 s` (cổng thời gian không gọi API); lần 5 vẫn lỗi ⇒ hành vi 4f (KHẨN, không
  ghi kết quả một phần, chốt cụm). Trạng thái thử lại > 10′ ⇒ bỏ.
- `Reconciler`: `RECOVER_RETRY` ⇒ giữ cụm + stop (`flatPending`), hẹn đối chiếu lại; lần sau không đếm lại 3 lần đọc phẳng;
  vị thế xuất hiện lại ⇒ huỷ hẹn. `confirmPendingFlat` kích khi tới hẹn. Stream tới trong lúc chờ vẫn đóng cụm bình thường.

## 3. MINOR-B: giá BNB (assetUsdPx, Aerospike) trong khoá FillAccounting
- `onOrderUpdate` / `bookRecoveredExit` thành wrapper KHÔNG synchronized: prefetch giá asset phí NGOÀI khoá (cache 60 s),
  rồi vào phần synchronized; `commissionUsd` dưới khoá chỉ đọc cache (giá cũ ≤ 6 h vẫn dùng; không có ⇒ thận trọng 0,05 %
  + cảnh báo như 4f).

## 4. Test race A1 4e/4f
- `src/test/.../c3live/scope/A1R4eRaceTest.java` chép nguyên (md5 `d3c8df70433e474d2137842065a4edc0`). Ghi chú: file A1 dùng
  `System.out.println` trong test — giữ byte-identical theo yêu cầu, không sửa.

## 5. K5 firstSentMs
- Canary: `CanaryEngine.k5Since` — mốc "sau lệnh đóng" = `firstSentMs(cid c3x-)`, không có ⇒ ts ACK (cũ).
- Production cùng lỗi gốc (ALGO_UPDATE EXPIRED tới trước sự kiện khớp c3x- ⇒ Telegram "STOP MAT" nhầm): `FillAccounting.
  closingAfterSend` — cụm đang đóng (`closeCid`, `closeSentMs` = mốc GỬI, ghi trước khi gửi), stop closePosition, sự kiện ≥ mốc gửi
  ⇒ vẫn bỏ stop khỏi sổ nhưng không báo "STOP MAT" (log INFO).

## 6. Kiểm
- Code commit `b616f86a` (trên `d035a086`). `mvn -o -T 1 package` qua `flock oracle_heavy.lock` + `nice -n 10`, MAVEN_OPTS=-Xmx2g:
  **869 test, 0 fail, 0 error, 1 skip** (851 cũ + 18 mới: OpsResetR4gTest 6, SymbolMapperRefreshR4gTest 3,
  LiveFeatureDumpDailyR4gTest 2, C3MainAccountR4gTest 4, CanaryK5SinceR4gTest 2, A1R4eRaceTest 1). `C3MainAccountR4fTest` sửa
  đúng 1 dòng (vòng lặp 6 → 9 bước 35 s cho 3 lần đọc phẳng + 5 lần thử) — kết quả kỳ vọng không đổi.
- fake242: **TEST PASS 217/217** (script ops không đổi).
- Jar `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4g` md5 **fd08ff2ca246119da8148dc81b65587b**. Script deploy
  `deploy_v12_dry_r4.sh` VẪN pin r4f `dbe20705…` (MASTER quyết sau A1).
- Prereg parity dry v1.2: repo nghiên cứu `research/vz-e1` commit `3c7dae05`, `docs/prereg/PREREG_PARITY_V12_DRY.md`
  sha256 `7f864a7aef59e1be54fe5f208ee9bfb58da30bb5a100b5c16d79c63db3726825`.
