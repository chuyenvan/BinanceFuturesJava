# TASK-014: Khảo sát data.binance.vision — rà data types còn giá trị (dump mẫu → phân tích sau)

- **status:** DONE (khảo sát xong trên Kaggle; output → Desktop user). KHÔNG ingest, KHÔNG quyết.
- **owner:** CCD · **updated:** 2026-06-13 (kernel chuyendinh/vision-survey COMPLETE)
- **Lý do:** vừa suýt bỏ lỡ `metrics` (OI/LS/taker) vì chỉ nhìn API. Rà 1 lần toàn bộ `data.binance.vision/futures/um/` xem còn data nào đáng dùng cho model (gate/funding/risk) mà chưa khai thác. Dump mẫu + coverage ra file, **để Desktop/user phân tích một thể sau** (task này KHÔNG tự quyết dùng gì).

## Phạm vi
Liệt kê MỌI loại data dưới `data.binance.vision/.../futures/um/` (cả `daily` và `monthly`). Các loại đã biết (CCD xác nhận + bổ sung nếu thiếu): `aggTrades, bookDepth, bookTicker, fundingRate, indexPriceKlines, klines, liquidationSnapshot, markPriceKlines, metrics, premiumIndexKlines, trades`.

Ưu tiên chú ý (tiềm năng cao cho hệ): **liquidationSnapshot** (thanh lý — squeeze/risk), **markPriceKlines / premiumIndexKlines** (basis = perp−spot, bổ trợ funding), **bookDepth/bookTicker** (microstructure), **aggTrades** (taker flow chi tiết).

## Chạy ở đâu
**Kaggle** (CPU + internet — tải + giải nén nhiều file). Theo `docs/RUNBOOK_kaggle_multi_cpu.md`. KHÔNG chạy nặng trên 226/local.

## Yêu cầu — chỉ KHẢO SÁT, KHÔNG ingest
Với MỖI loại data:
1. **Path + đơn vị file** (daily/monthly, theo symbol hay toàn sàn).
2. **Coverage:** từ năm nào (lấy BTC làm mốc + 1 alt) + granularity (1m/5m/event...).
3. **Schema:** header/cột + ý nghĩa (đoán nếu Binance không ghi rõ).
4. **Sample nhỏ:** 5–10 dòng đầu mỗi loại.
5. **Nhận xét sơ 1 dòng:** loại này có thể dùng cho gì (gate/funding/risk) — gợi ý, không kết luận.

→ Gom TẤT CẢ vào **1 file** (md/txt) + vài file sample → đặt nơi Desktop/user đọc. Hết nhiệm vụ (không backfill, không quyết).

## An toàn
- Chỉ tải + đọc + dump mẫu. KHÔNG ghi Aerospike, KHÔNG đụng ingest/live. Throttle tải.

## Acceptance
- [ ] File tổng hợp: mọi data type + path + coverage + granularity + schema + sample + nhận xét sơ.
- [ ] Đủ để Desktop/user quyết loại nào đáng làm task ingest riêng (sau).

## (Code điền) — KHẢO SÁT XONG trên Kaggle (2026-06-13)

- **Chạy:** kernel `chuyendinh/vision-survey` (script Python, internet on, CPU), liệt kê bucket S3 `data.binance.vision` (daily+monthly) + tải sample mới nhất mỗi loại. PASS (status COMPLETE).
- **Output đầy đủ → Desktop user:** `C:\Users\pc\Desktop\TASK-014-vision-survey\`
  - `SURVEY_REPORT.md` (báo cáo 1 file: path/coverage/granularity/schema/sample mỗi loại)
  - `samples/*.head.txt` (17 sample, BTCUSDT, 10 dòng đầu + key)
  - `survey.json` (dữ liệu thô cho Desktop parse lại), `vision-survey.log`
  - Script gốc: `C:\Users\pc\kaggle-jobs\vision-survey\survey.py`

### ⚠️ Phát hiện quan trọng
- **`liquidationSnapshot` KHÔNG còn trên vision** (không có ở cả daily lẫn monthly) — dù task đánh dấu ưu tiên cao. Binance đã ngừng publish loại này lên data.binance.vision. Muốn thanh lý → phải lấy nguồn khác (API `allForceOrders`/websocket `!forceOrder@arr`, không có history sâu).
- **`bookTicker` chỉ có ~1 năm:** daily 2023-05-16→2024-03-30, monthly 2023-05→2024-04 rồi DỪNG. Không còn cập nhật → chỉ dùng làm mẫu microstructure quá khứ, không live-continuous.

### Bảng data types (BTCUSDT làm mốc)
| period/type | coverage BTC | granularity | đơn vị file | tiềm năng |
|---|---|---|---|---|
| klines | 2019-12-31→nay | 1m | symbol/interval | đã dùng (ticker1m) |
| premiumIndexKlines | 2019-12-24→nay | 1m | symbol/interval | **CAO** — basis (perp−spot) phút, bổ trợ funding (funding chỉ 8h) |
| markPriceKlines | 2019-12-23→nay | 1m | symbol/interval | mark price (PnL/thanh lý), thành phần basis |
| indexPriceKlines | 2019-12-23→nay | 1m | symbol/interval | index spot, thành phần basis |
| metrics | 2020-09-01→nay | 5m | symbol | **RẤT CAO** — OI + LS ratio (top/all) + taker buy/sell vol ratio (gate/risk) |
| fundingRate | 2020-01→2026-05 | 8h | symbol (monthly) | đã dùng — đối chiếu nguồn fee |
| aggTrades | 2019-12-31→nay | event | symbol | taker flow (CVD/imbalance), nặng |
| trades | 2019-09-08→nay | event | symbol | trade thô, rất nặng (aggTrades thường đủ) |
| bookDepth | 2023-01-01→nay | snapshot (~10s, ±%) | symbol | thanh khoản/áp lực sổ lệnh (risk) |
| bookTicker | 2023-05→2024-04 (DỪNG) | event | symbol | top-of-book spread/imbalance — chỉ history cũ |

Lưu ý đơn vị: daily = 1 file/ngày, monthly = 1 file/tháng (gộp). Loại có `interval` subdir (klines & 3 dòng *Klines) lấy `1m`.

### Nhận xét sơ — loại tiềm năng (gợi ý, KHÔNG kết luận; Desktop/user quyết task ingest sau)
1. **metrics** — OI + long/short ratio + taker ratio, 5m, từ 2020-09. Trực tiếp cho gate/risk chống sập. Ứng viên số 1 cho task ingest riêng.
2. **premiumIndexKlines** (+ mark/index) — basis phút, bổ trợ/thay proxy funding ở granularity cao.
3. **aggTrades** — taker order-flow (CVD) nếu cần tín hiệu vi cấu trúc; chi phí ingest lớn.
4. **bookDepth** — đo thanh khoản, hữu ích cho sizing/risk; từ 2023.
- **liquidationSnapshot bỏ khỏi danh sách** (không có nguồn vision).

### Acceptance
- [x] File tổng hợp đủ: type + path + coverage + granularity + schema + sample + nhận xét sơ.
- [x] Đủ để Desktop/user quyết loại nào đáng làm task ingest riêng.
