# TASK-010: Lifecycle metadata coin (set symbol_lifecycle + SymbolLifecycleManager)

- **status:** CODE-DONE (2 class compile PASS; CHỜ chạy builder trên 226 + validate). prerequisite export feature mới H1.
- **owner:** CCD · **updated:** 2026-06-13 (implement Builder+Manager, compile PASS)
- **Liên hệ:** REBUILD_ROADMAP (mục Lifecycle) + ADR-0011. **Kế thừa TASK-008** (logic exchangeInfo + phân loại sống/chết đã viết). Là nền giải dần cái "vênh config DIED 3 nguồn" mà 008 nêu.

## Mục tiêu
Một **nguồn sự thật về vòng đời từng coin** (thay cách ad-hoc: cột `drawdownToBottom` sai, hardcode list rải rác). Phục vụ: loại **zombie** khi tính feature/basket (P2 export), **check-delist** trong backtest (P3), mốc-live.

## ⚠️ AN TOÀN
- Chỉ TẠO set mới + đọc-only (`kline_1m_opt`, exchangeInfo). KHÔNG đụng `DIED_SYMBOLS`/config/trading. KHÔNG tự thay list DIED bằng lifecycle (đó là bước sau, task riêng). SLF4J.

## Thiết kế
### Set Aerospike
- `symbol_lifecycle` (namespace `ticker`), key = symbol UPPERCASE.
- Value: `{firstSeen:long, lastSeen:long, status:String, delistTs:long?}`. (Snappy/JSON — bắt chước cách `writeFundingMap` ghi, hoặc record bins.)

### 3 trạng thái (KHÔNG phải 2 — nối bài học 13 coin sống-chưa-track)
- **LIVE** = trong exchangeInfo `status==TRADING` **và** data-ta còn mới (lastSeen gần `now`, vd ≤ 2 ngày).
- **DATA-INCOMPLETE** = exchangeInfo TRADING **nhưng** data-ta thủng (lastSeen cũ / gap giữa đời) — coin sống mà ta thiếu data (vd 8 coin vừa gỡ DIED ở 008, hoặc coin còn TRADING mà lastSeen lùi xa).
- **DEAD** = KHÔNG trong TRADING (delist thật) → `delistTs ≈ lastSeen`.
- ⚠️ Phân biệt DEAD vs DATA-INCOMPLETE **bắt buộc đối chiếu exchangeInfo** (tái dùng logic 008), KHÔNG suy từ mỗi data-ta (kẻo đánh chết oan coin sống → tái lập survivorship).

### 2 phần
1. **Builder (batch, chạy định kỳ)** — `SymbolLifecycleBuilder`:
   - Scan `kline_1m_opt` per-coin lấy `firstSeen`/`lastSeen` (mẫu quét phút tồn tại như `CheckGapTicker`; lấy phút đầu + cuối CÓ data). Cẩn thận RAM: quét theo chunk.
   - Lấy `LIVE_SET` từ exchangeInfo (tái dùng 008: PERPETUAL+USDT+TRADING).
   - Gán status theo quy tắc 3-trạng-thái trên → ghi set `symbol_lifecycle`. Ghi **242** (+226 nếu train/backtest cần đọc — xác nhận read client của H1/sim).
   - Chạy lại định kỳ (vòng đời đổi chậm; vd 1 lần/ngày hoặc thủ công khi cần).
2. **Manager (runtime)** — `SymbolLifecycleManager` (load-cache 1 lần như `SimpleSymbolMapper`):
   - API: `isAlive(symbol, t)` (firstSeen ≤ t ≤ lastSeen), `getFirstSeen/getLastSeen/getStatus(symbol)`, `getStatus(symbol, t)`.
   - Dùng ở feature/basket (lọc `isAlive(t)` → bỏ coin chưa sinh/đã chết/zombie) + backtest (không mở/giữ sau lastSeen) — TÍCH HỢP ở task export feature (H1), KHÔNG đụng live trong task này.

## Validate (recompute-compare)
- Lấy mẫu coin (gồm 30 core die + vài LIVE + vài DATA-INCOMPLETE) → recompute firstSeen/lastSeen từ scan độc lập → so set.
- Đối chiếu status vs exchangeInfo (coin TRADING không được gán DEAD).
- Biên: coin die (lastSeen ≈ mốc delist thực, khớp dữ liệu backfill).

## Acceptance
- [ ] Set `symbol_lifecycle` đủ coin (universe + 30 core die), 3 trạng thái gán đúng (đối chiếu exchangeInfo).
- [ ] `SymbolLifecycleManager` load-cache + API `isAlive`/status chạy; mẫu kiểm tay đúng.
- [ ] Validate recompute-compare PASS; KHÔNG coin TRADING nào bị gán DEAD oan.
- [ ] KHÔNG đụng DIED_SYMBOLS/config/trading/live.

## (Code điền) — IMPLEMENT 2026-06-13 (đã compile PASS javac 11; CHỜ chạy trên 226)

### Builder — `ai_ml/validation/data/SymbolLifecycleBuilder.java`
- Đọc-only market data: `IS_KAGGLE_MODE=true` → đọc ticker **226** (bản synced), quét NGÀY bằng `readDataFromAerospike1M_ShortKey(d)` từ `20210101` → nay (mẫu y hệt `AerospikeCoverageMap`).
- Lấy `firstSeen`/`lastSeen` THẬT per `symbolId`: 1 pass forward, TreeMap phút ASC + ngày ASC ⇒ firstSeen set 1 lần, lastSeen tự kết thúc đúng max. Lọc ticker bằng `Utils.isTickerAvailable`.
- `LIVE_SET` từ exchangeInfo (tái dùng TASK-008): `ClientSingleton...getExchangeInformation()` lọc đuôi `USDT` + không `_` (loại delivery) + `quoteAsset=USDT` + `status` chứa `TRADING`. ⚠️ `ExchangeInfoEntry` KHÔNG có `contractType` → loại perp bằng đuôi/`_` (xấp xỉ PERPETUAL, khớp `isUsdtPerp` của coverage map). Guard: LIVE_SET rỗng → DỪNG (tránh gán DEAD oan toàn bộ).
- Gán 3 trạng thái (universe = symbol-có-data ∪ LIVE_SET):
  - **LIVE** = trong LIVE_SET & `now-lastSeen ≤ 2 ngày`.
  - **DATA_INCOMPLETE** = trong LIVE_SET nhưng lastSeen cũ/`=0` (gồm coin TRADING chưa có data — vd 8 coin gỡ-DIED 008).
  - **DEAD** = không trong LIVE_SET → `delistTs = lastSeen`.
- Ghi set `symbol_lifecycle` (ns `ticker`) lên **CẢ 242 và 226**, key=symbol UPPERCASE, bins `sym/first/last/status/delist` (record bins, không Snappy — record nhỏ; sendKey=true).
- Log: `#LIVE / #DATA_INCOMPLETE / #DEAD` + sample 38 coin (30 core-die + 4 gỡ-DIED-008 + 4 LIVE) in `status | firstSeen → lastSeen`.

### Manager — `ai_ml/data/SymbolLifecycleManager.java`
- Singleton Holder + `init()` load-cache 1 lần: `scanAll(symbol_lifecycle)` (mẫu `AerospikeTaskCoordinator`/`SimpleSymbolMapper`). Read client = 226 nếu Kaggle/HPO, else 242 (replicate `getReadClient`).
- API: `isAlive(symbol,t)` (`firstSeen≤t≤lastSeen`), `getFirstSeen/getLastSeen(symbol)`, `getStatus(symbol)` (LIVE/DATA_INCOMPLETE/DEAD/UNKNOWN), `getStatus(symbol,t)` point-in-time (PRE_LIST/LIVE/DEAD) cho backtest. Đầy đủ Javadoc.

### Thống kê / sample — CHỜ chạy 226
Builder chưa chạy (job nặng quét nhiều năm + ghi set production → **phải chạy trên 226** theo CLAUDE.md, KHÔNG chạy từ máy local qua mạng). Lệnh chạy:
```bash
# trên 226, sau khi build jar mới (mvn -o package). Ghi PID + log riêng theo luật "DỌN JOB CŨ".
nohup java -cp target/binance-java-sdk-1.2.4.jar \
  com.binance.chuyennd.ai_ml.validation.data.SymbolLifecycleBuilder \
  > ~/java/simulator/outputs/.run/SymbolLifecycleBuilder.log 2>&1 & \
  echo $! > ~/java/simulator/outputs/.run/SymbolLifecycleBuilder.pid
```
Số liệu #LIVE/#DATA_INCOMPLETE/#DEAD + sample điền sau khi chạy.

### Validate (recompute-compare) — CHỜ chạy 226
1. Lấy mẫu (30 core-die + vài LIVE + 4 coin gỡ-DIED-008) → recompute firstSeen/lastSeen từ scan độc lập (vd 1 tool đọc `readDataFromAerospike1M_ShortKey` riêng) → so set.
2. Đối chiếu status vs exchangeInfo: KHÔNG coin nào `TRADING` mà bị gán DEAD.
3. Biên coin die: `lastSeen ≈ mốc delist`, khớp dữ liệu backfill (đợt B).

### Trạng thái build
- ✅ `javac 11` compile PASS cả 2 class (cp = fat jar). KHÔNG đụng DIED_SYMBOLS/config/trading/live.
- ⏳ Chưa tích hợp vào export feature (H1) — đúng phạm vi (task riêng, KHÔNG đụng live ở 010).
