# AUDIT lệnh trade WFO vs Binance & Aerospike — 2026-08-12

## Kết luận: ĐẠT — sim khớp giá THẬT
Lấy random **15 lệnh entry** của WFO trong khúc OOS 2023–2025 (từ `entry_universe_g008.csv`, seed=42), đối chiếu giá `priceClose` sim ghi với **Binance fapi 1m kline** và **Aerospike ticker**:
- **15/15 khớp TUYỆT ĐỐI** giữa `priceClose` sim dùng và **close kline 1m Binance** tại đúng timestamp. Sai số 0.0000%.
- Timestamp mapping đúng (tsHuman UTC+7 → epoch → đúng nến Binance).
- Aerospike lưu cùng dữ liệu: giải mã `kline_1m_opt` (protobuf OHLCV/symbol) — mẫu CGPTUSDT close=0.11452 khớp cấu trúc; giá sim = Aerospike = Binance.

## Bảng đối chiếu (15 lệnh, priceClose sim vs Binance 1m close)

| Symbol | Thời điểm entry (UTC+7) | priceClose (sim) | Binance close | Khớp |
|---|---|---|---|---|
| AEVOUSDT | 2025-03-04 08:59 | 0.12680 | 0.12680 | ✓ |
| PERPUSDT | 2024-03-15 16:19 | 1.64900 | 1.64900 | ✓ |
| FETUSDT | 2023-08-18 05:21 | 0.18120 | 0.18120 | ✓ |
| ORDIUSDT | 2024-08-05 13:27 | 22.0200 | 22.0200 | ✓ |
| AUCTIONUSDT | 2024-08-05 09:27 | 12.6220 | 12.6220 | ✓ |
| MYROUSDT | 2024-08-05 08:29 | 0.07666 | 0.07666 | ✓ |
| MYROUSDT | 2024-04-13 01:48 | 0.14322 | 0.14322 | ✓ |
| RIFUSDT | 2024-03-08 22:32 | 0.23790 | 0.23790 | ✓ |
| AIUSDT | 2025-04-07 13:46 | 0.10814 | 0.10814 | ✓ |
| ETHWUSDT | 2025-02-03 09:05 | 1.61550 | 1.61550 | ✓ |
| 1000LUNCUSDT | 2024-03-06 03:07 | 0.18551 | 0.18551 | ✓ |
| DYDXUSDT | 2025-02-03 11:54 | 0.65400 | 0.65400 | ✓ |
| BANUSDT | 2024-12-10 10:22 | 0.08880 | 0.08880 | ✓ |
| BLZUSDT | 2023-10-24 23:34 | 0.23310 | 0.23310 | ✓ |
| WLDUSDT | 2023-10-24 22:37 | 1.63280 | 1.63280 | ✓ |

## Ý nghĩa
- **Không có giá bịa/lệch/lookahead**: mỗi lệnh vào đúng bằng close nến 1m thật của Binance tại phút tín hiệu. `entryPrice` = close của nến gate-trigger (vào cuối nến, hợp lý).
- Vì `priceClose` sim đọc TỪ Aerospike, và nó = Binance → **market data trong Aerospike = Binance thật** → backtest chạy trên giá đúng. Đây là điều kiện cần để tin PnL của WFO.

## Cách làm (tái lập được)
- Nguồn lệnh: `/home/ubuntu/claudedata/entry_universe_g008.csv` (cột ts, tsHuman, symbol, score, priceClose) — entry qua gate.
- Aerospike ns=test, port 3222, set `kline_1m_opt` key `YYYYMMDD-HHMM` (UTC+7), bin `data` = protobuf: header 3 byte + lặp {0a<len> 0a<slen>SYMBOL 12 19 <5 float o/h/l/c/v tag 0d/15/1d/25/2d>}.
- Binance: `GET https://fapi.binance.com/fapi/v1/klines?symbol=&interval=1m&startTime=<ts>&limit=1` (Oracle ra internet được).
- Script: `/tmp/audit.py` (Binance, đã chạy 15/15), `/tmp/audit2.py` (thêm cột Aerospike close — decoder quét pattern, chưa chạy xong do rớt bridge; sẽ hoàn tất bảng 3 cột khi kết nối lại).

## Còn lại (khi bridge Oracle nối lại)
- Chạy nốt `audit2.py` để in cột Aerospike close cạnh Binance (xác nhận trực tiếp Aerospike==Bin==sim cho cả 15, thay vì chỉ 1 mẫu CGPT).
- Mở rộng: đối chiếu cả EXIT (dùng `EntryPathTrackProbe` với `TICKER_SOURCE`, hoặc mfe/mae trong `entry_paths.csv`) nếu Uni muốn audit cả điểm thoát chứ không chỉ entry.
