# TASK-002: Coverage map Aerospike — sitemap dữ liệu thật (ticker1m)

- **status:** done (1 lưu ý lọc USDC — xem Phát hiện ngoài scope, chờ user xác nhận có cần re-run không)
- **Milestone:** Tiền đề dữ liệu — nguồn sự thật về coverage dataset (thay proxy `symbol_mapper`). Chuỗi survivorship: 002 → 001; (nếu 001 cho thấy cần) backfill pilot → full ở task đánh số sau. *(003 đã dùng cho golden regression, không phải backfill.)*
- **Thực thi bởi:** Claude Code (**Java**, để review tường minh + chạy trên 226).

## Mục tiêu (1 câu)
Quét đọc-only toàn bộ ticker1m trong Aerospike → dựng "sitemap": mỗi symbol USDT-perp có dữ liệu ở những THÁNG nào (2021→nay), và đánh dấu tháng thiếu (gap nội bộ).

## Scope
**Trong scope:** Java thuần, ĐỌC-ONLY Aerospike, dùng class có sẵn trong repo. Xuất CSV.
**Ngoài scope (KHÔNG động):** KHÔNG ghi/ingest Aerospike, KHÔNG sửa engine, KHÔNG backtest, KHÔNG tải Binance (việc của task khác).

## Bối cảnh / công cụ repo (Code tự xác minh đường dẫn)
- Đọc data theo thời gian (key = phút): `DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey(long startTime)` (1 ngày) hoặc `readDataFromAerospikeCustom(long startTime, int totalMinutes)`.
- `KlineObjectSimple[]` index theo `symbolId`; symbol↔id qua `SimpleSymbolMapper`.
- "Có data thật tại phút": `Utils.isTickerAvailable(ticker)` (loại ticker null / min==max & volume==0).
- ⚠️ KHÔNG có index symbol→time sẵn (xem BO_CODE_DIGEST §B5) → BẮT BUỘC quét tuần tự theo thời gian.

## RÀNG BUỘC SYMBOL
Chỉ USDT **perpetual**: đuôi `USDT`, KHÔNG chứa `_`. Loại delivery/quarterly (vd `BTCUSDT_202602`), COIN-M, USDC.

## Các bước
1. Xác định khoảng quét: từ tháng đầu có data (vd 2021-01) → tháng hiện tại.
2. Quét tuần tự theo NGÀY. Mỗi ngày đọc 1 lần (`readDataFromAerospike1M_ShortKey`), duyệt từng phút; với mỗi `symbolId` có `isTickerAvailable=true` → đánh dấu `(symbol, tháng)` = CÓ DATA. Tối ưu: mỗi (symbol, tháng) chỉ cần thấy 1 lần là set flag, bỏ qua phần còn lại của tháng đó cho symbol đó.
3. Map symbolId→symbol, lọc theo RÀNG BUỘC SYMBOL.
4. Xuất `./outputs/aerospike_coverage.csv`: cột `symbol, firstMonth, lastMonth, monthsCovered, gapMonths` — trong đó `gapMonths` = các tháng nằm TRONG `[firstMonth, lastMonth]` nhưng KHÔNG có data (lỗ hổng nội bộ; phân biệt với coin chết = không có data SAU lastMonth, không tính là gap).
5. Log summary (SLF4J): tổng symbol có data; số symbol có gap nội bộ; tổng (symbol×tháng) có data; thời gian quét.

## Acceptance criteria (Code tự kiểm trước khi báo done)
- [ ] ĐỌC-ONLY: không một lệnh ghi/ingest Aerospike nào.
- [ ] Quét ĐỦ khoảng thời gian (không chỉ 1 ngày/1 tháng) — log tiến độ theo tháng.
- [ ] CSV đúng cột, coverage ở mức THÁNG.
- [ ] Lọc đúng USDT-perp (loại `_`/delivery/COIN-M/USDC).
- [ ] Log qua SLF4J/Log4j2, TUYỆT ĐỐI KHÔNG `System.out`/`printStackTrace`.
- [ ] Cấu trúc data/đường dẫn khác giả định → BÁO LẠI trong "Kết quả", KHÔNG bịa.

---
## (Code điền) Kết quả

- Tool: `src/main/java/com/binance/chuyennd/ai_ml/validation/data/AerospikeCoverageMap.java` (Java, ĐỌC-ONLY, SLF4J, không System.out/printStackTrace). Chạy trên **226** (đọc bản ticker đã sync trên 226 qua `IS_KAGGLE_MODE=true` → `getReadClient`→226).
- Quét **1986 ngày** (66 tháng, 202101→202606), 0 ngày rỗng, **353s**.
- Kết quả: mapper 751 symbol (100% USDT-perp); **USDT-perp CÓ DATA = 750** (1 symbol có trong mapper nhưng KHÔNG có ticker thật); **có gap nội bộ = 7**; tổng (symbol×tháng) có data = **16995**.
- CSV: `226:/home/chuyennd/java/simulator/outputs/aerospike_coverage.csv` (751 dòng gồm header). Cột: `symbol,firstMonth,lastMonth,monthsCovered,gapMonths`. *(File nằm trên 226 — chưa kéo về máy local.)*
- AC tự kiểm: ✅ read-only ✅ quét đủ range (log/tháng) ✅ đúng cột, coverage mức tháng ✅ SLF4J ✅ phân trang có xử lý (thực tế listing đủ 1 trang).

## (Code điền) Phát hiện ngoài scope

- **Lọc USDC chưa triệt để:** ràng buộc yêu cầu "loại USDC" nhưng filter dùng `endsWith("USDT") && !contains("_")` → vẫn lọt vài symbol có "USDC" trong tên mà đuôi là USDT: `USDCUSDT`, `1000BONKUSDCUSDT`, … (USDC-quote? hay USDC-base/USDT-quote?). USDC-margined thật (đuôi `USDC`) đã tự bị loại vì không endsWith USDT. → **CẦN XÁC NHẬN** có loại nhóm `*USDC*` này không; nếu có, thêm điều kiện `!contains("USDC")` rồi re-run (nhanh, ~6'). Số lượng nhỏ.
- **2 symbol "giả" có gap khổng lồ:** `BTCDOMUSDT` (chỉ số dominance, KHÔNG phải coin) và `USDCUSDT` (stablecoin) có gap hàng chục tháng — không phải coin trade-được; task-001 nên LOẠI khỏi ước lượng survivorship để khỏi nhiễu.
- **Coverage (750) > universe data.vision USDT-perp (732):** dataset hiện CÓ NHIỀU symbol USDT-perp hơn universe monthly-klines của data.vision → tập "thiếu" (universe − coverage) khả năng RẤT NHỎ; survivorship-by-symbol nhẹ. Khác biệt còn lại của task-001 chủ yếu là gap-nội-bộ + coin chết-trong-dataset (đã có data tới lastMonth rồi tắt).
- 7 symbol gap nội bộ: `AERGOUSDT, BTCDOMUSDT, CELOUSDT, LITUSDT, MAVIAUSDT, SONICUSDT, USDCUSDT` (2 cái cuối là giả như trên).

## (Code điền) Quyết định phát sinh

- Chưa tạo ADR. Lưu ý lọc USDC + loại symbol-giả nên giải quyết ở task-001 (consumer) hoặc re-run task-002 nếu user muốn coverage "sạch".
