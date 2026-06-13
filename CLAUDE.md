# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Ngôn ngữ
**Luôn luôn trả lời người dùng bằng tiếng Việt.**

---

## ⛔ LUẬT BẤT DI BẤT DỊCH (đọc trước khi sửa bất cứ gì)

Đây là các bài học đã trả giá bằng nhiều vòng phân tích. Vi phạm = sai kết quả backtest một cách âm thầm.

1. **KHÔNG look-ahead nội-nến.** Trong backtest, một nến đã đóng KHÔNG được vừa dùng `maxPrice` (đỉnh) để kích hoạt/đặt SL vừa khớp lệnh theo `minPrice`/`lastPrice` trong cùng nến đó — vì không ai biết đỉnh hay đáy đến trước trong một nến. Quy tắc: **đặt SL ở nến này, chỉ cho khớp ở nến sau.** Guard `Configs.BLOCK_INTRABAR_LOOKAHEAD` mặc định `true`. Đã sửa trong `OrderTargetInfoTest.updateStatusNew` (nhánh `priceSL==null`). Nhánh `priceSL!=null` (SL có từ nến trước, khớp theo `minPrice`) là ĐÚNG, không đụng.

2. **Mọi backtest "thật" phải gọi `BacktestIntegrityGuard.assertProductionGrade()`** ở đầu. Nó chặn chạy nếu look-ahead bật lại, slippage=0, hoặc fee=0. Đã cắm sẵn ở NÚT CHẶN DUY NHẤT `SimulatorMarketLevelTicker1MStopLoss.simulatorWithInitEntry()` — mọi engine (Master/AIMarket/BudgetRatio/Combined/DynamicFilter/TrailingStop/MarketThresholds/BenchmarkSpeed) đều đi qua đây nên không ai bypass được; KHÔNG cần gọi lại ở từng engine. KHÔNG bỏ lời gọi này. Chỉ nới (`assertProductionGrade(true)`) khi CỐ Ý chạy đối chứng look-ahead/slippage.

3. **Mô phỏng chi phí phải luôn bật:** `RATE_FEE` (2 chân phí sàn) + `SLIPPAGE_RATE` (2 chân trượt giá, `APPLY_SLIPPAGE=true`). Tắt = lợi nhuận ảo.

4. **MỘT BỘ NÃO sim/product.** Mọi quyết định vào/ra lệnh phải nằm trong hàm lõi THUẦN dùng chung cho cả backtest và live. Pattern đúng đã có: `DcaUtils.shouldDca`, `MarketBigChangeDetector.evaluateCircuitBreakerCore`. Nếu thấy `xxx` và `xxxProd`/`xxxProduction` lệch nhau về LUẬT quyết định → đó là BUG cần gom về một hàm, không phải tính năng. Hai nhánh hiện còn lệch: `createOrderBUY` (sim) vs `createOrderBuyRequest` (product) — xem ROADMAP bước 5.

5. **Bump `CONFIG_VERSION` trong `RunHpoMaster_Distributed`** mỗi khi đổi BẤT KỲ thứ gì ảnh hưởng kết quả backtest mà KHÔNG nằm trong genome HPO: `RATE_FEE`, `SLIPPAGE_RATE`, logic trailing (`calRateLossDynamicBuy`), budget divider, circuit breaker, look-ahead guard, **đổi model AI**, số/loại gene. Quên bump = cache Aerospike trả điểm cũ tính bằng cấu hình cũ → toàn bộ run vô nghĩa.

6. **`taskId` của HPO phải băm ĐỦ mọi gene trong genome.** Thêm gene mà quên đưa vào `buildTaskId` = các cá thể khác nhau trùng key = HPO vô nghĩa. (Đã từng dính với 4 gene DCA.)

7. **KHÔNG random-split dữ liệu chuỗi thời gian.** Khi train model AI hoặc chia tập, luôn cắt theo MỐC THỜI GIAN, không `train_test_split(shuffle=True)`/`stratify`. Và scaler chỉ `fit` trên TRAIN, không `fit` trên toàn bộ rồi mới chia (leak phân phối test). Hai lỗi này đang tồn tại trong code train Python (xem CẠM BẪY).

8. **Tiền/giá đang dùng `Float`** (rủi ro sai số tích lũy). Nếu refactor sang `double`/`BigDecimal` phải làm ĐỒNG BỘ cả sim lẫn product và bump `CONFIG_VERSION`.

9. **KHÔNG đổi công thức `finalFitness` (`HPOFitnessCalculatorV3`) khi đang có HPO chạy dở.** `profitFactor`/`worstSingleLoss`/`payoffRatio` là guardrail báo cáo, cố ý KHÔNG nằm trong fitness.

10. **Khi đụng logic quyết định, luôn nêu rõ nó tác động SIM và PRODUCT thế nào.** Sửa nhỏ, mỗi thay đổi một mục đích. Không refactor hàng loạt khi chưa hỏi user — codebase ~250 class, nhiều ràng buộc ngầm.

---

## ⚠️ CẠM BẪY ĐÃ BIẾT (đừng "sửa" nhầm, đừng tin nhầm)

- **`predReturn24H` + MOM24 đã BỎ HẲN khỏi hệ** (ablation A=C: nhánh `predReturn24H` không bao giờ kích hoạt). Đã xoá: field `AiPredictionData.predReturn24H`, model 24H trong `OnnxInferenceManager`, nhánh MOM24 + config `MIN_MOMENTUM_24H`/`FILTER_USE_MOM24`, **gene MIN_MOMENTUM_24H khỏi genome HPO** (14→13 gene, CONFIG_VERSION v5→**v6**), và **label `futureReturn24H`** khỏi export CSV + target python (→ schema export đổi, phải RE-EXPORT market data trước khi train lại). Filter giờ chỉ còn RISK(DD4H)+MOM15+EARLY. Lá chắn chống sập THẬT không nằm ở entry filter (worstLoss/maxDD bất biến qua mọi mode) — phải xây ở tầng DCA/margin.
- **Tên biến nói dối:** `getMaxRateIn90MForTradingStop` / tham số `maxChange90M` thực ra trả về `predReturn15M` của AI, KHÔNG phải biến động 90M. Đang dần đổi tên cho đúng (`calRateMinWithPredReturn15MForTradingStop`). Đừng suy luận theo tên cũ.
- **Circuit breaker gần như không kích hoạt:** `CIRCUIT_LOOKBACK_MINUTES=4` quá ngắn so với `MAX_CONCURRENT_ORDERS=40`. Biết rồi, cần bàn trước khi chỉnh.
- **DCA pro-cyclical:** trong `BIG_DOWN`, DcaUtils bật `isAll=true` → nhồi KHÔNG trần margin đúng lúc thị trường sập mạnh nhất. Rủi ro lớn đã ghi nhận, KHÔNG sửa lặt vặt — xem ROADMAP bước 3.
- **Sizing không biết equity:** budget tính trên `balanceBasic` cố định, không nén khi drawdown, không có margin call/cháy tài khoản trong sim.
- **Win rate VÔ NGHĨA với chiến lược này.** Martingale luôn cho win rate ~99% giả tạo. Đo `profitFactor`, `worstSingleLoss`, `payoffRatio`, và đặc biệt chất lượng RIÊNG của leg đầu (xem `EdgeAttributionReport`) — vì một cụm thắng có thể do DCA cứu chứ không do AI vào đúng.
- **Backtest đẹp KHÔNG chứng minh model AI tốt.** P&L đẹp có thể do: model khớp dữ liệu train, HPO che lỗi model (vặn ngưỡng né vùng model sai), hoặc martingale cõng. Phải đo model ĐỘC LẬP (IC trên holdout chưa train) trước khi tin.
- **Worker HPO chạy tuần tự 1 task/JVM nên ghi `static Configs` an toàn.** ĐỪNG song song hóa nhiều trial trong cùng JVM mà vẫn dùng static Configs — sẽ giẫm tham số chéo.
- **Bug perf:** `preprocessFundingData` chạy lại MỖI trial, sort lại cùng mảng đã sort (Lomuto pivot → O(n²) worst case). Nên sort 1 lần lúc load. Spike GC ~270ms/tick trong HPO là do JVM sống lâu + data tĩnh lớn, không phải logic — cấp heap + ZGC/G1 + tách worker khỏi máy master.

---

## SECURITY (xử lý cẩn trọng)
`config/PrivateConfig.java` và `runAider.bat` chứa **API key/secret LIVE commit thẳng vào repo** (Binance key/secret, Gemini key). Khi đụng các file này: KHÔNG echo secret ra commit/log/chat, và nhắc user rằng các key này đã lộ trong git history, cần xoay (rotate) + chuyển sang config không track.

---

## Project conventions
- New methods phải có Javadoc đầy đủ (mô tả, params, return).
- `CONVENTIONS.md` nói Java 21 nhưng `pom.xml` đang pin **Java 11** (`<source>/<target>`, `<java.version>`). Build hiện compile theo Java 11 — xác nhận với user trước khi dùng cú pháp Java 21, và bump `pom.xml` nếu thật sự muốn Java 21.

## Build & run
Maven (no wrapper). Tên artifact trong README là legacy/upstream — đây là app private, không phải SDK published.
```bash
mvn install     # compile + protobuf codegen + shade fat jar
mvn package     # build shaded jar trong target/ (không install)
mvn -o package  # offline build (deps đã cache)
```
- `maven-shade-plugin` ra một fat jar (launch theo main-class).
- `protobuf-maven-plugin` gen Java từ `src/main/proto/*.proto` lúc build bằng `protoc` tải về (cần mạng lần đầu). `os-maven-plugin` resolve platform classifier.

### Tests
**KHÔNG có unit-test suite** (`src/test` không tồn tại; `mvn test` là no-op). "Test" ở đây là các class `main()` đứng riêng dùng làm công cụ/thí nghiệm thủ công (`bigchange/test/*`, `*Validator`, `*Checker`, `*Comparator`, `Benchmark*`). Chạy bằng cách gọi `main` trực tiếp:
```bash
java -cp target/binance-java-sdk-1.2.4.jar com.binance.chuyennd.aerospike.validate_data.ticker.CheckGapTicker
```
60+ class có `main()` — phần lớn là tool vận hành/validate một lần, KHÔNG phải entry point hệ thống live.

## ⚙️ Chạy job java trên 226 — DỌN JOB CŨ CỦA MÌNH TRƯỚC KHI CHẠY

Mỗi lần run java trên 226 (backtest/sim/tool), job nặng (`-Xmx*g`) còn sót từ lần trước sẽ ăn RAM, chạy chồng làm sai/chậm metric, đụng đọc Aerospike, hoặc lẫn log (như vụ TASK-001 grep nhầm log tưởng treo). Quy tắc:

1. **Job nền Code spawn PHẢI ghi PID + log riêng** vào thư mục định danh, ví dụ `~/java/simulator/outputs/.run/<job>.pid` và `<job>.log` (job = tên class, vd `GoldenBacktest`). Chạy `nohup ... & echo $! > .run/<job>.pid`.
2. **TRƯỚC khi chạy lại cùng job:** đọc `.run/<job>.pid` → nếu PID còn sống (`ps -p`) VÀ `cmdline` đúng là java tool/backtest của mình (khớp main-class) → `kill` → đợi chết → xóa pid-file. Chỉ kill **đúng PID mình đã ghi**.
3. **Orphan (pid-file mất nhưng job cũ còn chạy):** liệt java process khớp main-class backtest/tool của mình (`GoldenBacktest`, `Simulator*`, `SurvivorshipBac0`, `AerospikeCoverageMap`, `*Validator/*Checker/Benchmark*`). Nếu RÕ là tool của mình → dọn; **nghi ngờ chủ → KHÔNG kill, BÁO user**.
4. **⛔ TUYỆT ĐỐI KHÔNG kill:** `BinanceOrderTradingManager` (trading live), `BinanceDataIngestor` (ingest live), Aerospike, Redis, và **HPO đang chạy của user** (`RunHpoMaster_Distributed`/`RunWorkerKaggle`). Live ghi PID riêng qua `Utils.writePid2File` (`APP_PID_DIR`) — KHÔNG đụng pid-file đó. Không dùng `pkill java` / `killall java`.
5. **Trước golden/determinism:** đảm bảo KHÔNG có instance backtest khác của mình chạy song song (chia sẻ tài nguyên → có thể làm chậm/sai). Dọn xong mới chạy.

## Runtime config (đọc từ CWD, không phải classpath)
Ba file config plaintext đọc **từ thư mục làm việc của process** lúc static-init, phải có mặt nơi chạy jar:
- `config.properties` — `tradecore/Configs.java` load. Aerospike hosts/ports, capital, symbol lists, paths dưới `../storage/`. Thiếu file → `System.exit(0)`.
- `redis.config` — `redis/RedisConst.java` load. Redis cluster.
- `config/PrivateConfig.java` — Binance API key/secret + base URL, **hardcode commit trong source** (xem Security).

`tradecore/Configs.java` là bề mặt tinh chỉnh trung tâm: hyper-params giao dịch (leverage, fee, budget divider, circuit breaker, dynamic trailing, AI filter, DCA threshold) là các `static` field, nhiều cái do HPO set. Đọc comment từng section trước khi đổi magic number.

## Process entry points (hệ thống live)
Hai process sống lâu, mỗi cái một `main()`:
1. **Data ingestion** — `websocket/BinanceDataIngestor.main()`. Stream funding + ticker từ Binance websocket vào Aerospike. Có watchdog tự restart.
2. **Trading** — `trading/BinanceOrderTradingManager.main()`. Wire `new DetectEntrySignal2TradeNormal().start()` (signal + AI inference) với order manager.
   Process tự restart bằng re-`exec` command line qua `Utils.reset(...)`, ghi PID qua `Utils.writePid2File()` (driven bởi env `APP_PID_DIR`/`APP_MAIN_CLASS` từ `daemon.sh` ngoài repo).

## Architecture (bức tranh lớn)
Toàn bộ app code dưới `com.binance.chuyennd.*`. Package `com.binance.client.*` là Binance REST/websocket client vendored — coi như thư viện, sửa chủ yếu ở `chuyennd`.

Luồng dữ liệu: **Binance → ingestors → Aerospike/Redis → feature extraction → ONNX inference → signal/trade decisions**, kèm vòng offline backtest+HPO tune chính các tham số `Configs` mà live dùng.

- **Storage** — `aerospike/DataManagerAerospikeFloatSim` là kho market-data chính (binary float-packed). `utils/Storage`/`StorageProto`/`StorageSnappy` là kho file (Snappy/protobuf). `redis/` (Jedis cluster) cho order queue live + messaging. Proto schema ở `src/main/proto/`.
- **AI/ML** (`ai_ml/`) — ONNX qua `onnxruntime` (`ai_ml/onnx/`, entry-signal + funding classifier; model ở `../storage/ai_ml*/...`). `ai_ml/features/` trích feature. `ExportFeaturesForPythonTool` + `python/` cầu nối train Python. `ai_ml/data/` cache data backtest (`HPOSmartCache`, `CompactDayData`).
- **HPO** (`ai_ml/hpo/`) — Jenetics GA evolve tham số `Configs`. Phân tán master/worker: `hpo/master/RunHpoMaster_Distributed` đẩy population vào Aerospike queue set (`hpo_queue_<CONFIG_VERSION>`), đọc kết quả từ cache set vĩnh viễn (`hpo_results_<CONFIG_VERSION>`); `RunWorkerKaggle` tiêu thụ task. `ai_ml/wfo/` walk-forward.
- **Trade core** (`tradecore/`) — logic giao dịch thuần dùng chung live + backtest: `MarketBigChangeDetector`, `DcaProcessor`/`DcaUtils`, `CoinRankManager`, `TradeUtils`, `Configs`.
- **Trading** (`trading/`) — execution live: `DetectEntrySignal2TradeNormal`, `BinanceOrderTradingManager`, `BudgetManager`, `SymbolOrderLockingManager`, `trading/monitor/`.
- **Data validation** (`aerospike/validate_data/`, `ai_ml/validation/`, `websocket/checkdata/`) — tool đứng riêng phát hiện gap, sửa data, so production-vs-backtest. Dùng khi chẩn đoán chất lượng data.

## Logging
SLF4J → Logback (`src/main/resources/logback.xml`). Logs ở `logs/` (`full.log`, `error.log`, `archived/`). `logs/`, `storage/`, `target/`, `*.data`/`*.csv`/`*.log` đều git-ignored.

### ⛔ KHÔNG nuốt exception câm (BẮT BUỘC)
CẤM `catch` trống hoặc chỉ có comment (`// Ignore`, `// bỏ qua lỗi 1 coin, tiếp coin khác`, …): đó là lỗi data/ingest/backtest **âm thầm không ai biết** (đã trả giá: spam `-1130` ở ingest bị giấu, gap data im lặng). Mọi `catch` PHẢI:
- `LOG.warn`/`LOG.error` kèm **exception + ngữ cảnh** (symbol/key/timestamp), KHÔNG `printStackTrace`/`System.out`.
- Cố ý bỏ qua 1 phần tử để tiếp vòng lặp vẫn phải log (LOG.warn, hoặc LOG.debug nếu thật sự nhiễu + có lý do ghi rõ) — **không bao giờ để rỗng/comment-suông**.
- Nếu lỗi là bất biến cần dừng (config/look-ahead/data nền) → ném tiếp / `System.exit`, đừng nuốt.
Sửa luôn khi đụng vào file có pattern này.

## 👥 Điều phối nhiều CCD (đọc TRƯỚC khi nhận task)
Nhiều CCD chạy song song KHÔNG thấy nhau. **`docs/AGENTS.md` là nguồn sự thật về CCD nào đang làm task nào** — đọc trước khi nhận bất kỳ task nào, để không hai CCD đụng một việc và reset máy không mất vết.
1. **CLAIM:** task trống/STALE → ghi `owner` + `status: DOING` + `updated` vào CẢ `docs/AGENTS.md` VÀ header `tasks/<id>.md` rồi mới làm. Task đã có owner KHÁC + DOING + updated còn mới → KHÔNG đụng, báo user.
2. **HEARTBEAT:** cập nhật `updated` mỗi commit/đổi bước. DOING mà `updated` quá cũ (≳2h) + nghi reset → STALE, có thể reclaim.
3. **ĐÓNG:** `DONE` + commit hash; cần user soát → `REVIEW`. Một task = một owner.

## 🗺️ Tài nguyên & nơi chạy task (đọc khi giao/nhận — tránh lệch pha + dồn tải)
- **Aerospike 242 = LIVE, dữ liệu TẬP TRUNG** (nguồn chính cho live, ưu tiên giữ sạch). **PRIVATE**: chỉ 226 thông tới; máy dev/Kaggle KHÔNG kết nối 242 trực tiếp. ⇒ task **GHI 242 phải chạy TRÊN 226** (226 thông 242) hoặc trên chính 242 — không ghi 242 từ dev/Kaggle.
- **Aerospike 226 = kho BACKTEST/TRAIN** (lịch sử, feature, dataset). **Open internet** (Kaggle/dev tới được). Job đọc/ghi Aerospike nặng → chạy **trên VPS 226** (gần data).
- **VPS 226** = nơi chạy job nặng Aerospike + open internet (tải `data.binance.vision` trực tiếp được). Job nền phải ghi PID/log (xem luật dọn job 226).
- **Kaggle** = CPU + internet, cho: tải/xử data ngoài KHÔNG cần Aerospike (vd khảo sát/parse `data.binance.vision`), train/HPO (RUNBOOK_kaggle).
- **Chọn nơi chạy:** ghi-242 → 226/242 bắt buộc · Aerospike-226-nặng → 226 · tải-ngoài + CPU không-Aerospike → Kaggle (phân tải khỏi 226) · train/HPO → Kaggle.
- **Lưu data (CHỐT):** 226 chỉ để **backtest/train**; **242 luôn là live tập trung** (ưu tiên). Job build/backfill ghi 226 (train) là chính; ghi 242 chỉ khi live cần + qua 226. KHÔNG để 226 và 242 "mỗi nơi một kiểu" — schema phải thống nhất (vd OI: TASK-013 chốt schema chung cho cả history + forward).
- **Tránh dồn:** đừng để nhiều job NẶNG chạy ĐỒNG THỜI trên 226 (đụng RAM/Aerospike/đọc-ghi) — phân: tải-ngoài đẩy Kaggle, Aerospike-nặng trên 226 tuần tự. Hai task KHÔNG cùng đọc/ghi một nguồn cùng lúc. Bản đồ ai-đang-chạy-gì ở `docs/AGENTS.md`.

---
Xem `ROADMAP.md` cho thứ tự ưu tiên công việc kiểm chứng mô hình.