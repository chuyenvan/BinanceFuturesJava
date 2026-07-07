# db/index — Kiến trúc dữ liệu (router) — nguồn sự thật "data nào ở đâu, ghi/đọc/chạy đâu"

> Mọi task mới + refactor PHẢI theo nhánh này. Mâu thuẫn file khác → nhánh này thắng (trừ khi user đổi). Chốt 2026-06-14.

## Nguyên lý cốt lõi
1. **242 = SOURCE OF TRUTH mọi MARKET data** (realtime + lịch sử). Không market data "chính chủ" nào sống ngoài 242.
2. **242 PRIVATE** — chỉ **226** tới được. Kaggle/dev KHÔNG tới 242.
3. **226** = (a) replicate 242 theo SETNAME, ON-DEMAND + (b) kho COMPUTE (backtest/train/wfo/hpo). KHÔNG sync all↔all.
4. **226 internet mở** (Kaggle/dev tới); tài nguyên YẾU → tránh dồn job nặng.
5. **Kaggle nhiều CPU nhưng chỉ tới 226** → việc chỉ-đụng-226 đẩy Kaggle; việc cần-242 bắt buộc 226.


6. **Oracle VPS (161.118.212.3)** = node COMPUTE chính (heavy: train/export/WFO) + Aerospike LOCAL (127.0.0.1:3222 ns=test) làm kho DATA-TEST. Config Oracle trỏ AEROSPIKE_HOST_226=127.0.0.1 → "226" trong code = Aerospike local Oracle. Ticker đầy đủ 1886 ngày sống ở FILE kaggle_data_hpo/daily/ + (2026-07-07) nạp vào Aerospike local. ⚠️ Oracle TỚI ĐƯỢC 242:3222 → tool ghi phải trỏ localhost tường minh, KHÔNG dùng getClient242. Trạng thái dữ liệu chi tiết: [../DATA_STATE](../DATA_STATE.md).

> Nhớ nhanh: **dữ liệu THỊ TRƯỜNG → 242 gốc; TÍNH TOÁN/TRAIN → 226; COMPUTE nặng + DATA-TEST (WFO/backtest) → Oracle (Aerospike local + file).**

## Chi tiết theo loại
- [aerospike-242](aerospike-242.md) — source market, private, backup repl=1.
- [aerospike-226](aerospike-226.md) — replicate + compute, open internet.
- [redis](redis.md) — order queue live + messaging.

## Nơi chạy job (suy ra từ kết nối)
| Job đụng tới | Chạy ở đâu |
|---|---|
| GHI 242 (realtime / historical market) | **226** (hoặc 242). KHÔNG Kaggle |
| Chỉ ĐỌC/GHI 226 (train/backtest/compute) | **Kaggle** (ưu tiên, nhiều CPU) hoặc dev/226 |
| Tải internet nặng | **Kaggle** → 226 (→ đẩy 242 nếu là market) |
| Sửa code thuần | máy nào cũng được |

> ⚠️ **Bẫy chí mạng:** job chạy Kaggle mà code lỡ `getClient242()` → lỗi/treo (Kaggle không tới 242). Trước khi launch Kaggle phải chắc job chỉ touch 226.

## Luồng
LIVE→242 (ingest/trading ghi realtime thẳng 242) · CÀO LỊCH SỬ→242 (job cào chạy TRÊN 226, đích 242; tải nặng thì Kaggle→226→đẩy 242) · REPLICATE 242→226 theo setname on-demand (tool `ReplicateSet242To226`, TASK-034, chạy 226 đọc-242 ghi-226) · TRAIN/BACKTEST đọc market (replicate) + compute từ 226, ghi compute vào 226.
