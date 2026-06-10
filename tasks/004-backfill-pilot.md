# TASK-004: Backfill PILOT 1 coin (ticker + funding) — validate format, trên 226

- **status:** closed (deferred) — khảo sát 0-0c XONG (`docs/insights/INGEST_FORMAT.md`); user chốt **HOÃN backfill [C]** (ADR-0007 mục CẬP NHẬT). KHÔNG ingest. TASK-005 không mở.
- **Milestone:** Backfill survivorship (ADR-0007). PILOT → TASK-005 (full 38 coin).
- **Thực thi bởi:** Claude Code (**Java**, chạy trên 226). ⚠️ RỦI RO — ghi namespace `ticker`. Pilot ingest vào **226** (node test, re-sync được từ 242 nếu hỏng), KHÔNG đụng 242.
- **Quyết định nền:** ADR-0007 (vì sao backfill) · ADR-0006 (đo impact bằng golden) · BO_CODE_DIGEST §B5 (format đọc ticker).

## Kiến trúc dữ liệu (đã xác nhận)
- **242 = nguồn ticker chân lý** (production). **226 = bản sync TỪ 242**.
- ⇒ Cả 242 và 226 đều thiếu 39 coin → phải **tải từ Binance** (không sync được vì cả hai cùng thiếu).
- Chiến lược 2 node: **pilot ingest 226** (test/audit) → khi format PASS, **full (005) ingest 242 → sync 242→226**.

## Mục tiêu (1 câu)
Ingest LUNAUSDT (**ticker 1m + funding rate**) từ data.binance.vision vào **226** đúng format hiện hành, chứng minh đọc-lại-khớp + KHÔNG đụng coin khác — mở đường full 38 coin (005).

## Scope
**Trong scope:** Java; ingest vào **226**; đúng 1 symbol pilot; ticker 1m + funding rate; đối chiếu code save hiện có.
**Ngoài scope:** KHÔNG đụng 242; KHÔNG đụng symbol khác; KHÔNG sửa engine; KHÔNG full 38 (005); KHÔNG gen funding pred (chỉ kiểm ở Bước 0c).

## Bối cảnh đã biết
- Namespace `ticker`; ticker đọc qua `readDataFromAerospike1M_ShortKey` — value = **mảng `KlineObjectSimple[]` theo symbolId** (BO_CODE §B5). Thêm coin = **read-modify-write từng phút** → nguy cơ đụng coin khác.
- `config.properties`: `DIED_SYMBOLS` (30 symbol, trùng nhiều coin thiếu). Funding pred set `funding_pred_1m_v5`. **Funding RATE (fee thực) lưu ở đâu → Code xác định (Bước 0a).**
- data.binance.vision có cả `klines/` (ticker) và `fundingRate/` (funding rate history).

## Các bước
0. **Khảo sát FORMAT GHI ticker** (đọc code thật, không bịa): set ticker · key phút · encode `KlineObjectSimple[]` → bin `data` (Snappy?) · `SimpleSymbolMapper` cấp id. → `docs/insights/INGEST_FORMAT.md`.
0a. **Khảo sát FORMAT funding rate:** funding rate (fee) lưu set/node nào, key/value gì, engine đọc bằng hàm nào. → ghi cùng `INGEST_FORMAT.md`.
0b. **`DIED_SYMBOLS` — ĐÃ XÁC NHẬN + ĐÃ DỌN:** Code xác nhận `Constants.diedSymbol` là bộ lọc loại-trừ ở lõi dùng chung (SIM+LIVE: `MarketBigChangeDetector`, ingestor, `DetectEntrySignal`). User đã xóa còn mỗi `BTCDOMUSDT` ⇒ coin chết KHÔNG còn bị loại → sau backfill backtest sẽ thấy chúng. ⚠️ CÒN PHẢI XỬ LÝ: (1) **LIVE** giờ có thể thử entry coin delist — kiểm live xử lý sao khi đặt lệnh coin không còn (lý tưởng: tách SIM bỏ-loại / LIVE giữ-loại). (2) Coin trong DIED_SYMBOLS CŨ mà dataset **đã có data** (vd `USDCUSDT`) giờ được trade → soi có coin không-nên-trade nào lọt không.
0c. **Engine khi coin THIẾU funding pred:** bỏ qua hay lỗi? → quyết funding pred có cần gen cho coin backfill không (việc nặng, để riêng). BÁO LẠI.
1. Tải LUNAUSDT từ data.binance.vision: **ticker monthly 1m + funding rate** (toàn vòng đời tới delist); verify `.CHECKSUM`.
2. Cấp symbolId cho LUNAUSDT (mapper trên 226), KHÔNG đụng mapper 242.
3. Ingest vào **226**: ticker (read-modify-write mảng phút, chỉ set `symbolId_LUNA`) + funding rate đúng format.
4. **AUDIT (CỔNG GÁC — chỉ PASS mới mở 005):**
   - Đọc lại 226 → LUNA ticker đủ tháng + giá trị khớp CSV gốc (mẫu OHLCV); funding rate khớp.
   - Vài phút mẫu: symbol KHÁC trong mảng GIỐNG HỆT trước khi ingest (không bị đụng).
   - Số phút LUNA ingested khớp số dòng gốc.
5. Ghi kết quả + format tài liệu hóa + audit pass/fail + kết luận `DIED_SYMBOLS`/funding-pred + đường rollback (re-sync 226 từ 242).

## Acceptance criteria
- [ ] Format ghi ticker + funding rate tài liệu hóa từ CODE THẬT (`docs/insights/INGEST_FORMAT.md`).
- [ ] `DIED_SYMBOLS` + engine-thiếu-funding-pred được kiểm + báo rõ.
- [ ] Ingest vào 226, KHÔNG đụng 242; có rollback.
- [ ] Audit PASS: LUNA ticker+funding đọc lại khớp + symbol khác không đổi + đếm phút khớp.
- [ ] Java, SLF4J/Log4j2, KHÔNG System.out/printStackTrace.
- [ ] Khác giả định → BÁO LẠI, KHÔNG bịa.

## Ghi chú cho TASK-005 (full, mở sau khi 004 PASS)
Tải 38 coin (ticker + funding rate) → ingest **242** (nguồn) → sync 242→226 → chạy FULL golden (003) so baseline đo impact → bump `CONFIG_VERSION` (ADR-0004).

---
## (Code điền) Kết quả

### Bước 0–0c (khảo sát read-only) — XONG, tài liệu: `docs/insights/INGEST_FORMAT.md`
Format ticker/funding/mapper đã xác minh từ code thật (file:line trong doc). 3 phát hiện LỆCH giả định → DỪNG chờ quyết:

1. **Helper ghi hardcode 242, không theo mode** (`writeMinuteBatch` L154, `getExistingTickersMap` L378, `saveSymbolMapping` L134, `getId`→242). ⇒ pilot "ghi 226" KHÔNG tái dùng được helper → cần code client226 riêng + cấp id thủ công. Và sim GoldenBacktest (flags=false) đọc ticker qua getReadClient→**242** ⇒ LUNA ghi 226 **không hiển thị với sim** (pilot-226 chỉ validate FORMAT, không đo được gì).

2. **Backfill ticker ĐƠN LẺ không làm sim trade coin** (0c): entry do AI prediction (`ai_pred_market_full_basket_v2` + funding_pred) lái, không phải ticker. LUNA chỉ có giá mà thiếu prediction 2022 ⇒ sim không có tín hiệu vào → không trade → ΔPnL/ΔDD = 0. Muốn đo survivorship phải SINH prediction cho coin backfill (model inference trên 2022) — việc nặng, vượt 004/005 hiện hữu.

3. **Funding fee TẮT trong backtest** (`updateFundingFee` comment toàn bộ, L222-241) ⇒ ingest funding rate **vô nghĩa với PnL sim**. Chỉ ticker giá có tác dụng (nếu có prediction).

### Hệ quả → cần user chọn hướng (chưa ghi gì vào Aerospike)
- (A) Vẫn chạy pilot-226 **chỉ để validate FORMAT** read-modify-write (code client226 riêng) — chứng minh ghi không hỏng coin khác, nhưng không đo impact.
- (B) Nhận ra muốn đo survivorship THẬT phải: ticker + market-prediction (+ có thể bật funding fee) cho coin chết trên **242** → đây là pipeline lớn hơn 004/005 hiện tả. Cần định nghĩa lại task.
- (C) Tạm gác backfill: vì baseline CRASH (003.1) đã định lượng survivorship gián tiếp (2022 lãi giả do thiếu coin chết) — có thể đủ cho mục tiêu "biết edge có thật không" mà không cần dựng lại prediction.

## (Code điền) Phát hiện ngoài scope

## (Code điền) Quyết định phát sinh

- Khảo sát lộ 3 phá-vỡ giả định (sim đọc **242**≠226 / entry lái bằng prediction nên ticker đơn lẻ không làm sim trade / funding fee đang tắt) → user chốt **C: HOÃN backfill**. Không ghi Aerospike. Chi tiết + điều kiện làm lại [B] ở ADR-0007 (mục CẬP NHẬT). Quay lại ruin/breaker (ROADMAP bước 3).
