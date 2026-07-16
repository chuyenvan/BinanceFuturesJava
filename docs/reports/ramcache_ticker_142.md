# TASK-142 — RAM-cache ticker theo ngày (bỏ gunzip lặp mỗi sample, đường TICKER_SOURCE=file)

## 1. Chỗ IO thừa (đo được từ code)
- `StrategyWfoTask.runJob` chạy **N=30 sample** cho mỗi window: mỗi sample gọi `backtest(ctx, trainStart, trainEnd)`
  → `SimulatorMarketLevelTicker1MStopLoss.simulatorWithInitEntry(start,end)` **lặp per-day**
  (`SimulatorMarketLevelTicker1MStopLoss.java` vòng `while` ~dòng 105-124).
- Nhánh `"file"` (dòng cũ 116-120) gọi `KaggleDataLoader.loadDailyTickersShort(startTime)` MỖI ngày MỖI sample.
  `loadDailyTickersShort` → `loadObject` mở `ticker_YYYYMMDD.bin[.gz]`, **GZIPInputStream + ObjectInputStream.readObject**
  (deserialize cả `TreeMap<Long, Map<String,KlineObjectSimple>>`) → rồi convert sang short-array.
- ⇒ Cùng 1 file ngày bị **đọc + gunzip + deserialize lại ~30 lần/window** (train 12 tháng ≈ 365 ngày × 30 = ~10.950 lần đọc
  cho ~365 ngày duy nhất). Đây là ~77'/window quan sát được. `[PROFILE] readMs/simMs` (dòng ~353) tách rõ phần read.

## 2. Cơ chế cache đã thêm (file/method)
Tái dùng flag `Configs.USE_SMART_CACHE` (đã có; worker bật qua env `WFO_SMART_CACHE=1`). Trước đây `USE_SMART_CACHE`
CHỈ hợp lệ với `aerospike` (file thì `throw`). Nay mở cho `file`.

- **`HPOSmartCache.java`** — thêm cache RIÊNG cho file:
  - `FILE_STORE : ConcurrentHashMap<Long, TreeMap<Long, KlineObjectSimple[]>>` — lưu **short-array đã giải nén Y NGUYÊN**.
  - `getDataShortFromFile(long dayStart)` — miss → gọi loader (mặc định `KaggleDataLoader::loadDailyTickersShort`) 1 lần,
    cache lại; hit → trả **CHÍNH object** (null/empty KHÔNG cache → giữ FAIL-FAST đường cũ).
  - `clearFileCache()` / `fileCachedDays()`; `clearCache()` giờ xoá cả `FILE_STORE`.
  - Seam test `DayTickerLoader` + `setFileLoaderForTest(...)` (chỉ test dùng).
- **`SimulatorMarketLevelTicker1MStopLoss.java`** — nhánh `"file"`: `USE_SMART_CACHE ? HPOSmartCache.getDataShortFromFile(startTime) : KaggleDataLoader.loadDailyTickersShort(startTime)`.
  Bỏ `throw`. **Mặc định (cache off) đường đọc cũ NGUYÊN VẸN.**
- **`StrategyWfoTask.java`** — `clearFileCache()` sau vòng TRAIN, TRƯỚC OOS (ngày train không tái dùng ở OOS) → giới hạn RAM
  ~1 cửa sổ train; `finally` sẵn có (`clearCache()`) dọn sạch cuối job.

### Vì sao KHÔNG dùng CompactDayData (như đường aerospike)
`CompactDayData` **LOSSY**: bỏ `totalUsdt` (dựng lại = 0f) và **dựng lại `startTime` = dayStart+idx·60000**.
Mà `Utils.isTickerAvailable()` (dòng 457-463) dùng `totalUsdt != 0` → nén sẽ **ĐỔI quyết định vào lệnh** ở các phút
`minPrice==maxPrice` nhưng có volume → **lệch kết quả**. Cache exact-object trả đúng object gốc ⇒ **kết quả Y HỆT**.
An toàn chia sẻ object qua N sample vì sim **chỉ ĐỌC** ticker (mọi `.minPrice=/.maxPrice=...` trong sim là trên
`OrderTargetInfoTest`, không phải ticker; `HistoryManager.updateHistoryArray` chỉ đọc).

## 3. Ước tính RAM (clear cuối window)
KlineObjectSimple ≈ 56 B (header + Long startTime + 5 float). Mỗi phút: mảng[1000] (~8 KB) + ~400 coin×56 B ≈ 30 KB.
- 1 ngày ≈ 1440×30 KB ≈ **~43 MB/ngày** (2024 nhiều coin có thể tới ~65 MB/ngày ~700 coin).
- 1 cửa sổ train 12 tháng ≈ 365 ngày → **~16 GB (tối đa ~24 GB)**. → **cần `-Xmx` rộng** (khuyến nghị ≥ 20-28 GB cho node
  chạy file-cache 2024+; hoặc chạy ít window song song/node). `clearFileCache` trước OOS + `clearCache` cuối job giữ đỉnh ≈ 1 window.
  (So sánh: đường aerospike nén ~4.5 GB/window — file exact-object tốn RAM hơn nhưng ĐỔI LẤY "kết quả y hệt".)

## 4. Compile / test
- Sandbox agent KHÔNG có JDK-compiler/Maven → **chưa chạy `mvn`** ở đây. Code đã review khớp chữ ký interface
  (`WfoTask.buildJobs/runJob`, `WfoDataset.loadAuto`, `CoinRankManager.loadStaticTier`, `ExportCoinTierStatic.load`).
- **NGƯỜI chạy trên máy Windows (Git Bash):**
  ```bash
  mvn -o -q compile
  mvn -o -q -Dtest=HPOSmartCacheFileCacheTest test    # unit test cache: hit trả đúng object, clear, miss không cache
  ```
- Unit test: `src/test/java/.../ai_ml/data/HPOSmartCacheFileCacheTest.java` — kiểm cache HIT (loader chạy 1 lần, trả
  chính object, `totalUsdt` giữ nguyên), `clearFileCache/clearCache`, ngày miss không cache.

## 5. Build jar tên riêng + đo BEFORE/AFTER trên Oracle (NGƯỜI làm — agent không có SSH/JDK)
Entrypoint đo 1 window read-only đã tạo: **`com.binance.chuyennd.ai_ml.wfo.VerifyOneWindow`** (arg: winIdx, mặc định 10).
In `[TIMING] ... ms` + `RESULT_JSON {...}` (oosPnl/wfe/oosTrades/oosNote) để đối chiếu.

```bash
# build jar TÊN KHÁC (KHÔNG đè binance-futures-preflight.jar đang deploy)
mvn -o -q -DskipTests package
cp target/binance-java-sdk-1.2.4.jar target/preflight-ramcache.jar
scp -i ~/.ssh/id_rsa_chuyennd target/preflight-ramcache.jar ubuntu@161.118.212.3:/home/ubuntu/java/simulator/preflight-ramcache.jar

# trên Oracle — CÙNG window w10, seed cố định (SEED_BASE+10), dataset _ff ret2, ticker_regen file:
COMMON="-Xmx28g -cp preflight-ramcache.jar com.binance.chuyennd.ai_ml.wfo.VerifyOneWindow 10"
# BEFORE (cache OFF) — chính là hành vi jar chính hiện tại trên đường file:
WFO_DATA_DIR=/path/ff_ret2 WFO_STATIC_RANK=1 WFO_COINTIER_FILE=/path/tier.bin \
  java $COMMON | tee /tmp/w10_before.log
# AFTER (cache ON):
WFO_SMART_CACHE=1 WFO_DATA_DIR=/path/ff_ret2 WFO_STATIC_RANK=1 WFO_COINTIER_FILE=/path/tier.bin \
  java $COMMON | tee /tmp/w10_after.log
# So: grep RESULT_JSON /tmp/w10_before.log /tmp/w10_after.log   → oosPnl/wfe/oosTrades PHẢI TRÙNG
#     grep '\[TIMING\]' ...                                     → thời gian/window before vs after
#     grep '\[PROFILE\]' ...                                    → read% (để tính đúng mức tăng tốc)
```
> ⚠️ `config.properties` phải `TICKER_SOURCE=file`; đặt `ticker_YYYYMMDD.bin[.gz]` trong `kaggle_data_hpo/`.
> Xác minh AN TOÀN: `RESULT_JSON` before == after (cache không đổi số). Nếu lệch → DỪNG, không deploy.

## 6. Ước tính tăng tốc fan-out (chờ read% thực từ PROFILE)
Gọi f = tỉ lệ thời gian READ trong 77'/window. Cache bỏ ~29/30 read của vòng train:
`after ≈ 77·(1−f) + 77·f/30`.
| f (read%) | after/window | 16 window / 7 node (≈) |
|---|---|---|
| 0.5 | ~40' | ~90'/node |
| 0.65 | ~28' | ~64'/node |
| 0.8 | ~17' | ~39'/node |
(Before: 16×77 = 1232' → ~176'/node nếu chia đều.) **Chốt số sau khi có `[PROFILE] read%` từ log BEFORE.**

## 7. Cần gì để deploy chính thức
- Jar: `target/preflight-ramcache.jar` (build tên riêng) → Oracle `/home/ubuntu/java/simulator/preflight-ramcache.jar`.
- Bật cache: worker WFO thêm env **`WFO_SMART_CACHE=1`** (đã sẵn ở `WfoWorker`). `TICKER_SOURCE=file`.
- `-Xmx` đủ rộng theo §3 (≥ ~20-28 GB cho window 2024+ nhiều coin) — hoặc giảm số window song song/node.
- Sau khi VerifyOneWindow xác nhận số TRÙNG + thời gian giảm → mới cân nhắc gộp vào jar chính (NGƯỜI quyết, không đè jar đang deploy).
