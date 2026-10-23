# LOB_VERIFY — kiểm + sàng dataset LOB Kaggle `alpha000x/crypto-lob-data`

Ngày 2026-10-23. Kernel: **`chuyendinh/lob-verify-a`** (script kernel, CPU, private, internet ON chỉ để tải kline tĩnh `data.binance.vision`). Toàn bộ dữ liệu nặng chạy trên Kaggle; Oracle không tải dataset về (0 byte).

- Thời gian kernel: **263.0 s** (A1 0.2 s, A2 234.4 s, A3 17.7 s, A4 10.5 s)

## A1. Metadata

| file | GB | dòng (không kể header) | cột |
|---|---|---|---|
| BNBUSDT.csv | 14.39 | 3,851,648 *(đếm ở run v3, file byte-identical)* | 403 |
| BTCUSDT.csv | 27.25 | 6,018,702 *(đếm ở run v3, file byte-identical)* | 403 |
| ETHUSDT.csv | 24.00 | 5,926,882 *(đếm ở run v3, file byte-identical)* | 403 |
| SOLUSDT.csv | 16.28 | 4,510,657 *(đếm ở run v3, file byte-identical)* | 403 |
| XRPUSDT.csv | 13.09 | 3,827,972 *(đếm ở run v3, file byte-identical)* | 403 |

Tổng **95.01 GB**, 403 cột = 3 meta (`event_ts_ms`, `recv_ts_ns`, `update_id`) + **100 level** mỗi bên (`bid_px_i`, `bid_qty_i`, `ask_px_i`, `ask_qty_i`, i = 1..100). Không có cột thời gian dạng ngày: thời gian chỉ có trong `event_ts_ms` (ms UTC) và `recv_ts_ns` (ns).

## A2. Toàn vẹn — quét TOÀN BỘ `BNBUSDT.csv`

| kiểm | giá trị |
|---|---|
| số dòng | 3851648 |
| bắt đầu (UTC) | 2026-10-06T06:22:26Z |
| kết thúc (UTC) | 2026-10-13T06:22:25Z |
| `event_ts` không tăng | 0 |
| `event_ts` trùng | 0 |
| `update_id` giảm | 0 |
| `update_id` trùng | 0 |
| bid1 > ask1 (crossed) | 0 |
| bid1 = ask1 (locked) | 0 |
| qty âm | 0 |
| px ≤ 0 | 0 |
| bid không giảm dần theo level | 0 |
| ask không tăng dần theo level | 0 |
| ô NaN trong 20 level | 0 |
| thời gian quét (s) | 232.4 |

- Spread (bps): median **0.1332**, p5 0.1277, p95 0.1364, p99 0.1382, max 5.637 → đúng 1 tick 0,01 USDT trên giá ~750 (0,01/750 = 0,133 bps).
- Nhịp update: median **100 ms**, p95 400, p99 800, p99,9 1,400, max 17,500 ms; ~380 dòng/phút.
- Trễ `recv_ts_ns − event_ts_ms`: median **59.4 ms**, p95 100.0, p99 115.6, min 12.12 ms, **tỉ lệ âm 0.0000** (không có record nào nhận trước khi xảy ra).
- Phủ phút: **10,081 phút** liên tục 2026-10-06T06:22:00Z → 2026-10-13T06:22:00Z, lỗ hổng > 1 phút: **0** (gap lớn nhất 1 phút).
- Độ sâu L1: bid median 17.624, ask median 16.976 (đơn vị BNB).

## A3. Toàn vẹn mẫu 4 symbol còn lại (3 cửa sổ byte đầu/giữa/cuối)

| file | cửa sổ | dòng | crossed | locked | nonmono_ts | dup_ts | bid_mono_bad | ask_mono_bad |
|---|---|---|---|---|---|---|---|---|
| BTCUSDT.csv | head | 14,685 | 0 | 0 | 0 | 0 | 0 | 0 |
| BTCUSDT.csv | mid | 14,948 | 0 | 0 | 0 | 0 | 0 | 0 |
| BTCUSDT.csv | tail | 14,597 | 0 | 0 | 0 | 0 | 0 | 0 |
| ETHUSDT.csv | head | 16,666 | 0 | 0 | 0 | 0 | 0 | 0 |
| ETHUSDT.csv | mid | 16,704 | 0 | 0 | 0 | 0 | 0 | 0 |
| ETHUSDT.csv | tail | 16,528 | 0 | 0 | 0 | 0 | 0 | 0 |
| SOLUSDT.csv | head | 18,604 | 0 | 0 | 0 | 0 | 0 | 0 |
| SOLUSDT.csv | mid | 18,536 | 0 | 0 | 0 | 0 | 0 | 0 |
| SOLUSDT.csv | tail | 18,590 | 0 | 0 | 0 | 0 | 0 | 0 |
| XRPUSDT.csv | head | 19,610 | 0 | 0 | 0 | 0 | 0 | 0 |
| XRPUSDT.csv | mid | 19,517 | 0 | 0 | 0 | 0 | 0 | 0 |
| XRPUSDT.csv | tail | 19,674 | 0 | 0 | 0 | 0 | 0 | 0 |

Mỗi cửa sổ 64 MB (≈ 15–20 nghìn dòng) — đủ để phát hiện lỗi cấu trúc; **không** quét toàn bộ 4 file lớn (80,6 GB) để tiết kiệm thời gian kernel.

## A4. Đối chiếu mid với Binance Vision (kline 1m, file tĩnh)

| thị trường | phút khớp | dev median (bps) | |dev| p50 | |dev| p95 | |dev| p99 | |dev|>1bps | demeaned |dev| p50 | corr return 1m |
|---|---|---|---|---|---|---|---|---|
| futures/um | 10,081 | -2.604 | 3.186 | 6.248 | 7.219 | 93.8 % | 1.3561 | 0.98869 |
| spot | 10,081 | -0.065 | 0.067 | 0.069 | 0.619 | 0.5 % | 0.0027 | 0.99887 |

`dev` = (mid cuối phút − close kline 1m)/close·1e4. `demeaned` = dev trừ median (loại basis không đổi). `corr return 1m` = tương quan log-return phút của mid và của close kline — đại lượng **nhận diện thị trường** vì basis hằng số bị triệt tiêu.

## A5. Kết luận Phase A

| điều kiện chạy B | đạt |
|---|---|
| không NaN ở L1–L5 | ✅ |
| crossed + locked = 0 | ✅ |
| ts tăng, không trùng | ✅ |
| khớp Vision ≤ 1 bps / p95 ≤ 5 bps | ✅ |
| phủ phút ≥ 90 %, không lỗ hổng | ✅ |

Thị trường khớp nhất: **spot** (|dev| p50 0.067 bps). `run_B_allowed` = **True**.

## A6. Kết luận Phase A — dùng được cho gì

**Đạt.** Dataset là **order book spot** (không phải futures) 100 level, snapshot ~100 ms, 7,0 ngày (2026-10-06 → 2026-10-13), 5 symbol, 95,01 GB. Trên BNBUSDT (3,85 M dòng, 10.081 phút liên tục, 0 lỗ hổng): **0 lỗi cấu trúc** (0 crossed/locked/NaN/ts-dup/level-đảo), spread = 1 tick, và mid phút khớp kline spot Vision tới **0,067 bps tuyệt đối / 0,0027 bps sau khi trừ basis**, corr return 1m 0,9989. 4 symbol còn lại sạch trên 12 cửa sổ mẫu (≈ 0,20 M dòng).

**Dùng được cho:**

- Nghiên cứu microstructure spot: imbalance L1–L5, OFI, microprice, depth slope; horizon 1 s – 15 phút.
- Sinh feature/label cho ML trên book 100 level (độ sâu đủ để tính slope tới 100 bậc).
- So sánh 5 symbol (BNB/BTC/ETH/SOL/XRP) cùng khung thời gian, cùng định dạng.
- Kiểm tra tính khả thi kinh tế của market-making/mean-reversion tần suất cao ở mức **sàng lọc**.

**KHÔNG dùng được cho:**

- Backtest chiến lược cần **book futures** (USDT-M) — book ở đây là spot; basis futures ~2,6 bps.
- Mô phỏng **queue position / fill của maker**: chỉ có snapshot cách nhau ~100 ms, không có từng event add/cancel/trade, không có số thứ tự hàng đợi.
- Phân tích **trade flow / adverse selection** (không có trade prints, không có aggressor side).
- Kết luận về mùa vụ/regime dài hạn: **7 ngày** là mẫu ngắn, chỉ gồm 1 tuần tháng 10/2026.
- Bất kỳ so sánh với dữ liệu 2020 (niêm phong) hay suy rộng sang thanh khoản 2021–2024.

