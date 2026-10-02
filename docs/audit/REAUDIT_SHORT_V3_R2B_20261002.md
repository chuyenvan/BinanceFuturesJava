# REAUDIT SHORT_V3_R2B (LISTING, SL +15% trên HIGH 1m) — 2026-10-02

Đối tượng: `53a2479f result(SHORT_V3_R2B): NO-GO` (`docs/result/RESULT_SHORT_V3_R2B.json`, script
`research/analysis/short_v3_r2b_listing1m.py`). Hai agent audit trước bị chặn SSH → chỉ có báo cáo text,
chưa tái lập trên dữ liệu thô. Doc này = (1) báo cáo text của vòng trước + (2) bổ sung tái lập thô do auditor
vòng 3 làm trên Oracle (chỉ đọc, DEV ≤ 2025-12-31, không Java/không Kaggle/không chạm 242).

## 0. Trạng thái nguồn — ĐỌC TRƯỚC

- **Báo cáo text R2B của vòng trước KHÔNG có trong brief giao việc cho auditor vòng 3**: brief bị cắt ngay sau
  dòng tiêu đề `=== BÁO CÁO TEXT CẦN GHI THÀNH DOC ===`, không có nội dung. Auditor vòng 3 **không tự dựng lại**
  văn bản đó (yêu cầu "giữ nguyên nội dung" → không được bịa). Mục 1 để trống, MASTER cần dán nguyên văn.
- Những gì biết về claim vòng trước chỉ đến từ: (a) brief (danh sách 9 symbol nghi stale, 20 mẫu listing,
  "16 symbol nhiễm", "D0 1m sau loại = +1,98"); (b) script của auditor trước ở Windows
  `_claude_tmp/audit_SHORT_V3_R2B/{repro.py,adv.py,adv2.py}` — `adv2.py` định nghĩa 16 symbol nhiễm =
  REN 8 (`RENDER POL KAIA S A SKY G FORM`) + IDX 4 (`FOOTBALL BLUEBIRD PAXG XAU`) + REL 4
  (`1000LUNC USTC BSV RAYSOL`). Mục 2(iii) dùng đúng danh sách này.

## 1. Báo cáo audit vòng trước (nguyên văn)

> **CHƯA CÓ — chờ MASTER dán nguyên văn báo cáo text R2B.** Không có kết luận nào của auditor vòng 3 được
> viết vào mục này.

## 2. Bổ sung tái lập trên dữ liệu thô (auditor vòng 3)

Script: `research/analysis/reaudit_short_v3_r2b_raw.py` (import nguyên `short_v3_r2_listing`, `short_v3_r2_slcheck`,
`short_v3_r2b_listing1m`; không sửa). Output: `docs/audit/REAUDIT_SHORT_V3_R2B_20261002.json`. Chạy 16 s, lock
`oracle_heavy.lock`. `CLOSES_1H.bin`: 10 322 386 dòng, 0 dòng sau DEV, 627 symbol, lưới 2021-01-01 01:00 → 2026-01-01 00:00 UTC.

### (i) Stale / ffill cuối chuỗi trong `CLOSES_1H` (giờ UTC; "phẳng" = close bằng hệt giá trị cuối, bỏ qua NaN)

| symbol | first ts | last ts | đoạn phẳng cuối (giờ) | bắt đầu phẳng | chạm cuối DEV? |
|---|---|---|---|---|---|
| FTMUSDT | 2021-01-01 01:00 | 2026-01-01 00:00 | **8 630** (8 606 quan sát) | 2025-01-06 10:00 | có |
| KLAYUSDT | 2021-10-12 04:00 | 2026-01-01 00:00 | **10 455** (10 439 qs) | 2024-10-22 09:00 | có |
| ALPACAUSDT | 2024-08-22 11:00 | 2026-01-01 00:00 | **5 894** (5 878 qs) | 2025-04-30 10:00 | có |
| MKRUSDT | 2021-01-01 01:00 | 2026-01-01 00:00 | **2 751** (2 735 qs) | 2025-09-08 09:00 | có |
| GALUSDT | 2022-05-05 15:00 | 2024-07-30 06:00 | 452 | 2024-07-11 10:00 | không |
| RNDRUSDT | 2023-02-03 03:00 | 2024-07-30 06:00 | 333 | 2024-07-16 09:00 | không |
| MATICUSDT | 2021-01-01 01:00 | 2024-09-11 00:00 | 159 | 2024-09-04 09:00 | không |
| EOSUSDT | 2021-01-01 01:00 | 2024-11-22 00:00 | 0 (run phẳng dài nhất 4 h) | — | không |
| BNXUSDT | 2023-02-22 15:00 | 2024-11-22 00:00 | 0 (run phẳng dài nhất 4 h) | — | không |

Đọc: 4/9 (FTM, KLAY, ALPACA, MKR) là **ffill tới cuối file** — `last_ts` = 2026-01-01 dù coin đã ngừng giao dịch
(đoạn phẳng 115–436 ngày); 3/9 (GAL, RNDR, MATIC) có đuôi phẳng 7–19 ngày trước khi chuỗi dừng; EOS, BNX
**không stale** (dừng sạch 2024-11-22). Hệ quả cơ học: `find_listings` lấy `last_day` = ô hữu hạn cuối → với 4
symbol ffill, "ngày chết" bị đẩy tới 2025-12-31, nên mọi phép ghép "coin cũ chết ↔ coin mới niêm yết" dựa trên
`last_day` không thể bắt được S/KAIA/SKY (các mã kế nhiệm có mặt trong 16 symbol nhiễm). Auditor vòng 3 **không**
kiểm `rename_like` dòng-theo-dòng; đây là cơ chế khả dĩ, không phải chứng minh.

### (ii) `listing_day` (D0) của 20 mẫu vs phút đầu tiên trong Aerospike `test.kline_1m_opt`

Cách đọc y hệt `short_v3_r2_slcheck.fetch` (key `YYYYMMDD-HHMM` theo giờ UTC+7, giải nén snappy, `extract`
theo pattern protobuf của symbol). Quét thô mỗi 10 phút từ D0−45 ngày → D0+3 ngày, rồi quét tinh 1 phút
trong 10 phút trước hit đầu. Cột "1m đầu" là UTC.

| mẫu | D0 (R2B) | 1m đầu | 1h đầu (`CLOSES_1H`) | cùng ngày? | 1m trước D0 |
|---|---|---|---|---|---|
| JASMY | 2022-04-20 | 03:30 | 04:00 | ✓ | 0 |
| HOOK | 2023-01-23 | 03:00 | 04:00 | ✓ | 0 |
| AMB | 2023-03-30 | 12:00 | 13:00 | ✓ | 0 |
| HFT | 2023-04-06 | 12:00 | 13:00 | ✓ | 0 |
| MAV | 2023-06-29 | 12:00 | 13:00 | ✓ | 0 |
| ORDI | 2023-11-07 | 12:30 | 13:00 | ✓ | 0 |
| ILV | 2023-11-10 | 16:30 | 17:00 | ✓ | 0 |
| LSK | 2024-01-25 | 14:15 | 15:00 | ✓ | 0 |
| STRK | 2024-02-20 | 17:00 | 18:00 | ✓ | 0 |
| BANANA | 2024-08-15 | 02:00 | 03:00 | ✓ | 0 |
| SAFE | 2024-10-25 | 12:30 | 13:00 | ✓ | 0 |
| VTHO | 2025-01-22 | 09:30 | 10:00 | ✓ | 0 |
| BID | 2025-03-20 | 09:30 | 10:00 | ✓ | 0 |
| SXT | 2025-05-02 | 08:30 | 09:00 | ✓ | 0 |
| OBOL | 2025-05-07 | 10:30 | 11:00 | ✓ | 0 |
| AIN | 2025-07-10 | 10:45 | 11:00 | ✓ | 0 |
| EVAA | 2025-10-03 | 10:32 | 11:00 | ✓ | 0 |
| BLUAI | 2025-10-21 | 11:30 | 12:00 | ✓ | 0 |
| MMT | 2025-11-04 | 12:00 | 13:00 | ✓ | 0 |
| WET | 2025-12-10 | 07:00 | 08:00 | ✓ | 0 |

Kết quả: **20/20 D0 khớp ngày của phút 1m đầu tiên**; 0 record 1m nào của 20 mã trong 45 ngày trước D0
(record Aerospike thiếu trong cửa sổ quét: 0). Phút 1m đầu luôn đi trước dòng 1h đầu 15–60 phút (hàng 1h đầu
là giờ tròn kế tiếp) → không lệch ngày. Với 20 mẫu này `listing_day` đúng; không suy rộng cho 16 mã nhiễm
(nhiễm do *bản chất* mã — rename/index/relist — không do lệch ngày).

### (iii) D0/D1 net 1m sau khi loại 16 symbol nhiễm

Dùng `arm_stats` của `short_v3_r2b_listing1m.py` (summ/CI block-tháng 48 khối, seed 20260905, NREP 2000,
INFL 1,18, G5 = drop-top-10%) trên trades trong `RESULT_SHORT_V3_R2B.json`; `mi` dựng như `build_arms`.
Cả 16 symbol đều có mặt trong D0 và D1 (mỗi mã 1 lệnh). Tái lập "all" khớp JSON (D0 +2,0969% vs +2,0969%).

| nhánh / loại | n | mean | CI raw | CI infl lo | năm + | drop-top10 | excess | SL | GO |
|---|---|---|---|---|---|---|---|---|---|
| D0 all | 489 | +2,10% | [−0,10; +4,69] | −0,49 | 4/4 | −2,81% | +2,45% | 51,7% | ✗ |
| D0 −REN8 | 481 | +2,05% | [−0,10; +4,56] | −0,49 | 4/4 | −2,96% | +2,45% | 52,0% | ✗ |
| D0 −REN8−IDX4 | 477 | +2,00% | [−0,16; +4,54] | −0,55 | 4/4 | −2,97% | +2,53% | 52,4% | ✗ |
| **D0 −16** | **473** | **+1,98%** | **[−0,22; +4,54]** | **−0,62** | 4/4 | **−3,04%** | +2,48% | 52,4% | ✗ |
| D1 all | 489 | +1,74% | [−0,35; +4,18] | −0,72 | 3/4 | −2,94% | +1,88% | 50,7% | ✗ |
| D1 −16 | 473 | +1,54% | [−0,55; +3,91] | −0,93 | 3/4 | −3,25% | +1,83% | 51,8% | ✗ |

→ **Khớp claim "+1,98"** (D0 −16 = +1,9836%). Loại 16 mã nhiễm làm mọi chỉ số xấu đi nhẹ (CI lo −0,10 → −0,22,
G5 −2,81 → −3,04%): nhiễm **không** phải nguồn của thất bại, và cũng không cứu được nó. G1 (CI raw lo > 0) và G5
(drop-top10 > −0,5%) vẫn trượt ở cả hai nhánh.

### Kết luận tái lập thô (auditor vòng 3)

- Verdict R2B **NO-GO giữ nguyên**; ba điểm tái lập thô (stale, listing_day, loại 16) không đổi hướng nào.
- Dữ liệu: `CLOSES_1H` có ffill/stale thật ở cuối chuỗi các mã đã migrate/delist (FTM 360 ngày, KLAY 436 ngày,
  ALPACA 245 ngày, MKR 115 ngày tới cuối DEV) — ảnh hưởng mọi nghiên cứu dùng `last finite` làm ngày chết.
  `listing_day` của mã niêm yết mới đáng tin (20/20).
