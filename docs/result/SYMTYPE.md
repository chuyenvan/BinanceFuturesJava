# SYMTYPE — PnL attribution theo LOẠI CẤU TRÚC symbol (MASTER 2026-10-28)

Phạm vi: MÔ TẢ. Không chạy sim mới, không đổi universe/threshold, không gọi Binance REST, không ssh 242.
Prereg (commit trước khi đo): `docs/prereg/PREREG_SYMTYPE.md` @ `3d890188`, md5 `8023cdbe40ce8d49a96005c3a1cf7863`.

## 0. TL;DR

| Bucket | DEV 2022–25 (8 seed) | HO 2026 W9 (k24-s / x14) | Đọc |
|---|---|---|---|
| B1 TRADFI | **0 leg** (không có TradFi perp trước 2025-12) | 238 / 236 leg (6,6 / 6,5 %), PnL −6 084 / −6 367, **−25,56 / −26,98 mỗi leg**, win 52,5 % | thua lỗ, nhưng **DEV không có mẫu** |
| B2 INDEX/hàng hoá/stable | 56 leg, +23,66/leg, win 67,9 %, hold 182 h | 0 leg | N nhỏ |
| B3 PERP-KHÔNG-SPOT | 5 291 leg (22,4 %), **+60,23/leg**, win 89,8 % | 2 170 / 2 161 leg (59,7 %), +25,53 / +46,08 mỗi leg | **tốt hơn B5**, không phải nguồn lỗ |
| B4 MỚI NIÊM YẾT <30d | 2 497 leg (10,6 %), +35,40/leg | 29 / 28 leg, +110,46 / +150,62 mỗi leg | xấp xỉ/tốt hơn B5 |
| B5 crypto-native | 15 739 leg (66,7 %), +32,86/leg, win 84,8 % | 1 198 / 1 210 leg, +18,02 / +39,18 mỗi leg | mốc so sánh |

**Luật quyết đã chốt: KHÔNG bucket nào đủ điều kiện đề xuất loại. Cả B1–B4 = "GIỮ, chỉ theo dõi".**
Riêng B1: điều kiện (ii) của luật **không thể** thoả vì TradFi perp chưa tồn tại trong 2022–2025 (N=0) — xem §6.2; cần MASTER quyết bằng prereg riêng, không tự sửa luật.

## 1. Prereg và các quyết định hiện thực (chốt trước khi đo)

1. **B1** = đúng `TradFiClassifier` của HO2026_TRADFI_AUDIT: `contractType` chứa `TRADIFI`/`TRADFI` **hoặc** `underlyingType` ∈ {EQUITY, HK_EQUITY, KR_EQUITY, CN_EQUITY, COMMODITY, FX}. Văn bản prereg ghi "underlyingType≠COIN"; đọc nguyên văn thì INDEX cũng rơi vào B1 và B2 sẽ rỗng, nên dùng định nghĩa classifier mà audit đã dùng — nêu rõ để MASTER bác nếu muốn khác. `PREMARKET` (PREDICTUSDT) = crypto như audit.
2. **Ticker tái sử dụng (PIT guard):** nếu giờ vào lệnh < `onboardDate` của symbol trong exchangeInfo 10-27 thì KHÔNG áp nhãn snapshot (instrument thời đó là contract khác). Đúng 1 trường hợp: `MDTUSDT` 35 leg DEV (2023-06..2023-10, +1 345,90) — ticker MDT cũ (crypto, đã delist) được dùng lại 2026-10 cho một cổ phiếu TradFi. 35 leg này rơi B4/B5.
3. **B3 oracle spot PIT:** presence theo tháng từ **spot monthly klines** trên data.binance.vision (liệt kê S3 XML, không REST). Tháng biên (first/last month giao với tháng vào lệnh): tải zip 1m, so **phút đầu/cuối chính xác** với giờ vào lệnh (146 cặp symbol-tháng, 0 lỗi).
4. **B4 tuổi hợp đồng** = giờ vào lệnh − phút giao dịch đầu tiên trên Vision UM (`symlife/lifecycle_usdt.csv`), phủ 100 % symbol có leg (0 thiếu).
5. Giờ: printDone `start` = UTC+7 → `t_entry_utc = start − 7h`. DEV lọc `t_entry_utc ∈ [2022-01-01, 2026-01-01)`; HO `∈ [2025-12-31 17:00, 2026-10-01)`.

## 2. Dữ liệu và đường dẫn

| Thành phần | Đường dẫn |
|---|---|
| DEV legs | `~/kaggle_sim/out/tsx-x14-{a1,s7,s13,s21,s99,s123,s777,s2024}/storage/printDone.csv` (a1 = seed 42, xem GOLIVE_QUARTERLY dòng 31) |
| HO legs | `~/kaggle_sim/out/tsx-ho-x14-s{42,7,13,21,99,123,777,2024}/storage/printDone.csv`; `~/kaggle_sim/out/ho4-k24-s-s*/storage/printDone.csv` |
| Phân loại | `~/claude_master/ho_tradfi_wk/classes.json` (từ exchangeInfo_20261027_1140.json.gz, 936 symbol) |
| Tuổi hợp đồng | `docs/result/symlife/lifecycle_usdt.csv` (912 USDT perp, first/last phút trade) |
| Spot PIT | kernel Kaggle `chuyendinh/spotpit-1028` v4 (complete, 88 s) → `docs/result/symtype/spot_sym_months.csv` (757 USDT spot, 754 có dữ liệu), `spot_edge.csv` (146 cặp) |
| Script | `~/claude_master/symtype_wk/{prep_legs,assign_bucket,measure,validate,build_doc}.py`, kernel `kg_spot/spotpit.py` |
| Artefact | `buckets.parquet` (30 853 leg có nhãn), `symtype_metrics.json`, `validate.json` |

Không tải dữ liệu lớn về Oracle: kernel chỉ liệt kê S3 và tải zip trong bộ nhớ, output 256 KB.

## 3. DEV (X14 chuẩn, 8 seed, 2022-01..2025-12) — 23 583 leg, PnL +925 538,48

| bucket | leg | % leg | PnL (USD) | PnL/leg | win | hold (h) | %PnL |
|---|---|---|---|---|---|---|---|
| B1 | 0 | 0,0 % | 0,0 | — | — | — | 0,0 % |
| B2 | 56 | 0,2 % | 1 325,0 | 23,66 | 67,9 % | 182,3 | 0,1 % |
| B3 | 5 291 | 22,4 % | 318 655,0 | 60,23 | 89,8 % | 27,0 | 34,4 % |
| B4 | 2 497 | 10,6 % | 88 397,1 | 35,40 | 86,5 % | 44,3 | 9,6 % |
| B5 | 15 739 | 66,7 % | 517 161,3 | 32,86 | 84,8 % | 61,6 | 55,9 % |

### Theo năm

### DEV 2022

| bucket | leg | % leg | PnL (USD) | PnL/leg | win | hold (h) | %PnL |
|---|---|---|---|---|---|---|---|
| B1 | 0 | 0,0 % | 0,0 | — | — | — | 0,0 % |
| B2 | 32 | 0,7 % | 241,0 | 7,53 | 50,0 % | 263,8 | 0,6 % |
| B3 | 13 | 0,3 % | 602,8 | 46,37 | 100,0 % | 11,0 | 1,4 % |
| B4 | 311 | 6,4 % | 4 641,5 | 14,92 | 86,2 % | 84,2 | 11,0 % |
| B5 | 4 500 | 92,7 % | 36 557,9 | 8,12 | 84,0 % | 99,9 | 87,0 % |

### DEV 2023

| bucket | leg | % leg | PnL (USD) | PnL/leg | win | hold (h) | %PnL |
|---|---|---|---|---|---|---|---|
| B1 | 0 | 0,0 % | 0,0 | — | — | — | 0,0 % |
| B2 | 18 | 0,3 % | 844,1 | 46,90 | 88,9 % | 80,6 | 0,3 % |
| B3 | 288 | 4,7 % | 8 477,9 | 29,44 | 90,3 % | 29,8 | 3,3 % |
| B4 | 917 | 15,1 % | 32 178,6 | 35,09 | 87,7 % | 41,8 | 12,6 % |
| B5 | 4 848 | 79,9 % | 214 086,3 | 44,16 | 83,5 % | 54,9 | 83,8 % |

### DEV 2024

| bucket | leg | % leg | PnL (USD) | PnL/leg | win | hold (h) | %PnL |
|---|---|---|---|---|---|---|---|
| B1 | 0 | 0,0 % | 0,0 | — | — | — | 0,0 % |
| B2 | 6 | 0,1 % | 239,9 | 39,98 | 100,0 % | 52,8 | 0,1 % |
| B3 | 1 040 | 15,4 % | 65 310,4 | 62,80 | 92,8 % | 37,6 | 21,3 % |
| B4 | 769 | 11,4 % | 41 046,5 | 53,38 | 88,2 % | 34,0 | 13,4 % |
| B5 | 4 921 | 73,1 % | 199 367,0 | 40,51 | 87,1 % | 41,7 | 65,2 % |

### DEV 2025

| bucket | leg | % leg | PnL (USD) | PnL/leg | win | hold (h) | %PnL |
|---|---|---|---|---|---|---|---|
| B1 | 0 | 0,0 % | 0,0 | — | — | — | 0,0 % |
| B2 | 0 | 0,0 % | 0,0 | — | — | — | 0,0 % |
| B3 | 3 950 | 66,7 % | 244 264,0 | 61,84 | 89,0 % | 24,0 | 75,9 % |
| B4 | 500 | 8,5 % | 10 530,6 | 21,06 | 81,8 % | 39,8 | 3,3 % |
| B5 | 1 470 | 24,8 % | 67 150,1 | 45,68 | 84,0 % | 33,0 | 20,9 % |



Chú ý: B3 chiếm 0,3 % leg năm 2022 nhưng 66,7 % năm 2025 — phản ánh việc Binance niêm yết perp không kèm spot ngày càng nhiều, không phải lỗi dữ liệu (xem §8-3).

## 4. HO 2026 (8 seed mỗi cấu hình) — W9 3 635 leg: x14 +144 843,83; k24-s +74 096,39

### tsx-ho-x14 W9

| bucket | leg | % leg | PnL (USD) | PnL/leg | win | hold (h) | %PnL |
|---|---|---|---|---|---|---|---|
| B1 | 236 | 6,5 % | -6 367,0 | -26,98 | 52,5 % | 109,9 | -4,4 % |
| B2 | 0 | 0,0 % | 0,0 | — | — | — | 0,0 % |
| B3 | 2 161 | 59,5 % | 99 587,6 | 46,08 | 86,6 % | 40,9 | 68,8 % |
| B4 | 28 | 0,8 % | 4 217,4 | 150,62 | 100,0 % | 9,1 | 2,9 % |
| B5 | 1 210 | 33,3 % | 47 405,8 | 39,18 | 83,1 % | 40,0 | 32,7 % |

### tsx-ho-x14 H1

| bucket | leg | % leg | PnL (USD) | PnL/leg | win | hold (h) | %PnL |
|---|---|---|---|---|---|---|---|
| B1 | 220 | 9,5 % | -8 458,4 | -38,45 | 50,0 % | 111,0 | -6,2 % |
| B2 | 0 | 0,0 % | 0,0 | — | — | — | 0,0 % |
| B3 | 1 431 | 61,5 % | 89 823,5 | 62,77 | 88,8 % | 40,6 | 65,4 % |
| B4 | 28 | 1,2 % | 4 217,4 | 150,62 | 100,0 % | 9,1 | 3,1 % |
| B5 | 647 | 27,8 % | 51 844,0 | 80,13 | 89,5 % | 28,2 | 37,7 % |

### tsx-ho-x14 Q3

| bucket | leg | % leg | PnL (USD) | PnL/leg | win | hold (h) | %PnL |
|---|---|---|---|---|---|---|---|
| B1 | 16 | 1,2 % | 2 091,3 | 130,71 | 87,5 % | 94,5 | 28,2 % |
| B2 | 0 | 0,0 % | 0,0 | — | — | — | 0,0 % |
| B3 | 730 | 55,8 % | 9 764,2 | 13,38 | 82,3 % | 41,6 | 131,6 % |
| B4 | 0 | 0,0 % | 0,0 | — | — | — | 0,0 % |
| B5 | 563 | 43,0 % | -4 438,2 | -7,88 | 75,7 % | 53,4 | -59,8 % |

### ho4-k24-s W9

| bucket | leg | % leg | PnL (USD) | PnL/leg | win | hold (h) | %PnL |
|---|---|---|---|---|---|---|---|
| B1 | 238 | 6,6 % | -6 083,5 | -25,56 | 52,5 % | 101,2 | -8,2 % |
| B2 | 0 | 0,0 % | 0,0 | — | — | — | 0,0 % |
| B3 | 2 170 | 59,7 % | 55 391,9 | 25,53 | 85,8 % | 36,2 | 74,8 % |
| B4 | 29 | 0,8 % | 3 203,4 | 110,46 | 100,0 % | 10,2 | 4,3 % |
| B5 | 1 198 | 33,0 % | 21 584,6 | 18,02 | 82,1 % | 41,9 | 29,1 % |

### ho4-k24-s H1

| bucket | leg | % leg | PnL (USD) | PnL/leg | win | hold (h) | %PnL |
|---|---|---|---|---|---|---|---|
| B1 | 221 | 9,5 % | -7 529,8 | -34,07 | 49,8 % | 101,7 | -9,8 % |
| B2 | 0 | 0,0 % | 0,0 | — | — | — | 0,0 % |
| B3 | 1 442 | 61,8 % | 52 095,8 | 36,13 | 87,7 % | 32,9 | 67,9 % |
| B4 | 29 | 1,2 % | 3 203,4 | 110,46 | 100,0 % | 10,2 | 4,2 % |
| B5 | 641 | 27,5 % | 28 973,8 | 45,20 | 87,7 % | 28,8 | 37,8 % |

### ho4-k24-s Q3

| bucket | leg | % leg | PnL (USD) | PnL/leg | win | hold (h) | %PnL |
|---|---|---|---|---|---|---|---|
| B1 | 17 | 1,3 % | 1 446,3 | 85,07 | 88,2 % | 93,8 | -54,6 % |
| B2 | 0 | 0,0 % | 0,0 | — | — | — | -0,0 % |
| B3 | 728 | 55,9 % | 3 296,1 | 4,53 | 82,0 % | 42,7 | -124,5 % |
| B4 | 0 | 0,0 % | 0,0 | — | — | — | -0,0 % |
| B5 | 557 | 42,8 % | -7 389,2 | -13,27 | 75,8 % | 56,9 | 279,2 % |


## 5. Hai cột mô tả chéo (không phải bucket)

| Cột | DEV (n / PnL / PnL/leg / win / hold) | HO x14 W9 | HO k24-s W9 |
|---|---|---|---|
| tuổi 30–90 ngày | 3 299 / 148 141,3 / 44,90 / 88,8 % / 37,1 h | 202 / 15 987,2 / 79,14 / 85,2 % / 49,9 h | 202 / 11 285,6 / 55,87 / 85,2 % / 51,3 h |
| hợp đồng hệ số 1000x | 808 / 49 476,7 / 61,23 / 91,1 % / 31,0 h | 1 / 70,9 / 70,91 / 100,0 % / 0,9 h | 1 / 50,7 / 50,71 / 100,0 % / 0,9 h |

Cả hai cột đều **không tệ hơn B5** (B5 DEV +32,86/leg). Không có lý do cấu trúc để tách.

## 6. Luật quyết (chốt trong prereg) — áp nguyên văn

Điều kiện: (i) lý do cấu trúc; (ii) DEV N≥300 **và** PnL/leg < 50 % của B5 ở ≥3/4 năm có N≥50; (iii) HO 2026 cùng chiều.

Tỷ lệ PnL/leg(bucket) / PnL/leg(B5) theo năm DEV (n = số leg của bucket trong năm):

| Năm | B1 | B2 | B3 | B4 | B5 (USD/leg) |
|---|---|---|---|---|---|
| 2022 | — | 0,93 (n=32) | 5,71 (n=13) | 1,84 (n=311) | 8,12 |
| 2023 | — | 1,06 (n=18) | 0,67 (n=288) | 0,79 (n=917) | 44,16 |
| 2024 | — | 0,99 (n=6) | 1,55 (n=1 040) | 1,32 (n=769) | 40,51 |
| 2025 | — | — | 1,35 (n=3 950) | 0,46 (n=500) | 45,68 |

HO cùng chiều? (W9, PnL/leg so với B5): B1 −25,56 < +18,02 (k24-s) và −26,98 < +39,18 (x14) → **đúng chiều**; B3 +25,53 > +18,02 và +46,08 > +39,18 → **ngược chiều**; B4 +110,46 > +18,02 và +150,62 > +39,18 → **ngược chiều**; B2 không có leg HO.

### 6.1 Quyết theo từng bucket

| Bucket | (i) lý do cấu trúc | (ii) DEV | (iii) HO | Kết luận |
|---|---|---|---|---|
| B1 TRADFI | Có: không có spot/hedge, giờ theo sàn equity, thanh khoản mỏng; win 52,5 % so 83–85 % của B5 | **KHÔNG ĐO ĐƯỢC**: N=0 (TradFi perp bắt đầu 2025-12, DEV kết thúc 2025-12) | Có (âm hơn B5 ở W9 và H1, cả 2 cấu hình) | **GIỮ, chỉ theo dõi** — luật không cho loại |
| B2 INDEX/hàng hoá/stable | Có: động lực và giờ giao dịch khác crypto | Không (N=56 < 300; tỷ lệ 0,93–1,06× B5, không < 0,5) | Không có leg | **GIỮ, chỉ theo dõi** |
| B3 PERP-KHÔNG-SPOT | Có (không có neo spot/funding arb) — nhưng **không cho thấy bất lợi** | Không: PnL/leg **cao hơn** B5 (5,71 / 0,67 / 1,55 / 1,35×) | Ngược chiều (tốt hơn B5) | **GIỮ, chỉ theo dõi** |
| B4 MỚI NIÊM YẾT <30d | Có (listing pump/dump, thanh khoản chưa ổn định) | Không: chỉ 1/4 năm < 50 % B5 (2025: 0,46) → cần ≥3 | Ngược chiều (tốt hơn B5) | **GIỮ, chỉ theo dõi** |

### 6.2 Ghi chú buộc MASTER quyết về B1

Luật (ii) giả định bucket tồn tại trong DEV. TradFi perp chỉ có từ 2025-12 nên B1 **vĩnh viễn** không đạt N≥300 ở DEV ⇒ luật hiện tại không thể kết luận B1 dù HO xấu. Bằng chứng HO (mô tả, không dùng để loại): 236–238 leg (6,5 %), −6,1..−6,4k gộp, −25,56..−26,98/leg, win 52,5 %, 69 % leg dồn 06-02..06-05 (audit T3). Muốn xử lý B1 cần prereg riêng (ví dụ điều kiện thay thế cho loại không tồn tại trong DEV, hoặc dùng HO + live shadow), **không sửa luật sau khi đã thấy số**.

## 7. Validate

- **V0**: 30 853 leg, 0 NaN, mỗi leg đúng 1 nhãn ∈ {B1..B5} (B1 474, B2 56, B3 9 622, B4 2 554, B5 18 147).
- **V1 (khớp tổng)**: mọi run Δleg = 0 và ΔPnL = 0,00 so printDone gốc; tổng **30 853 leg / +1 144 478,70** khớp tuyệt đối.

| run | leg (bucket) | leg (printDone) | Δleg | PnL bucket | PnL printDone | ΔPnL |
|---|---|---|---|---|---|---|
| ho4-k24-s-s123 | 441 | 441 | 0 | 9 519,48 | 9 519,48 | 0,00 |
| ho4-k24-s-s13 | 449 | 449 | 0 | 10 265,97 | 10 265,97 | 0,00 |
| ho4-k24-s-s2024 | 484 | 484 | 0 | 8 070,08 | 8 070,08 | 0,00 |
| ho4-k24-s-s21 | 482 | 482 | 0 | 10 723,62 | 10 723,62 | 0,00 |
| ho4-k24-s-s42 | 406 | 406 | 0 | 11 247,22 | 11 247,22 | -0,00 |
| ho4-k24-s-s7 | 482 | 482 | 0 | 7 898,23 | 7 898,23 | -0,00 |
| ho4-k24-s-s777 | 446 | 446 | 0 | 5 694,60 | 5 694,60 | 0,00 |
| ho4-k24-s-s99 | 445 | 445 | 0 | 10 677,19 | 10 677,19 | -0,00 |
| tsx-ho-x14-s123 | 445 | 445 | 0 | 17 216,11 | 17 216,11 | -0,00 |
| tsx-ho-x14-s13 | 453 | 453 | 0 | 21 147,04 | 21 147,04 | -0,00 |
| tsx-ho-x14-s2024 | 486 | 486 | 0 | 15 264,08 | 15 264,08 | 0,00 |
| tsx-ho-x14-s21 | 481 | 481 | 0 | 20 056,81 | 20 056,81 | 0,00 |
| tsx-ho-x14-s42 | 403 | 403 | 0 | 18 995,61 | 18 995,61 | 0,00 |
| tsx-ho-x14-s7 | 488 | 488 | 0 | 16 596,29 | 16 596,29 | 0,00 |
| tsx-ho-x14-s777 | 452 | 452 | 0 | 12 893,87 | 12 893,87 | -0,00 |
| tsx-ho-x14-s99 | 427 | 427 | 0 | 22 674,03 | 22 674,03 | -0,00 |
| tsx-x14-a1 | 2 934 | 2 934 | 0 | 115 767,99 | 115 767,99 | 0,00 |
| tsx-x14-s123 | 2 959 | 2 959 | 0 | 108 244,79 | 108 244,79 | -0,00 |
| tsx-x14-s13 | 2 929 | 2 929 | 0 | 119 151,26 | 119 151,26 | 0,00 |
| tsx-x14-s2024 | 2 936 | 2 936 | 0 | 111 052,70 | 111 052,70 | 0,00 |
| tsx-x14-s21 | 2 940 | 2 940 | 0 | 109 165,55 | 109 165,55 | 0,00 |
| tsx-x14-s7 | 2 951 | 2 951 | 0 | 108 906,73 | 108 906,73 | -0,00 |
| tsx-x14-s777 | 2 900 | 2 900 | 0 | 129 889,43 | 129 889,43 | 0,00 |
| tsx-x14-s99 | 3 034 | 3 034 | 0 | 123 360,02 | 123 360,02 | 0,00 |
| **ALL** | **30 853** | **30 853** | **0** | **1 144 478,70** | **1 144 478,70** | **0,00** |

- **V2 (3 leg random, tính lại bằng hàm `derive()` độc lập đọc thẳng CSV spot + lifecycle, không dùng lại code gán nhãn)**: khớp 3/3.

| ds | symbol | giờ vào (UTC) | spot first_month | spot sống? | tuổi (ngày) | bucket tính lại | bucket gán | khớp |
|---|---|---|---|---|---|---|---|---|
| DEV | OGNUSDT | 2022-05-09 23:58:00 | 2020-01 | có | 404,0 | B5 | B5 | ✓ |
| HO_x14 | NKNUSDT | 2026-02-05 15:23:00 | 2019-10 | có | 1 763,6 | B5 | B5 | ✓ |
| HO_k24s | AKEUSDT | 2026-08-22 05:10:00 | — | không | 329,7 | B3 | B3 | ✓ |

- **V3 (PIT)**: 495 leg B3 có spot first_month > tháng vào lệnh; 5 ví dụ:

| run | symbol | giờ vào (UTC) | spot first_month | spot last_month | PnL |
|---|---|---|---|---|---|
| tsx-x14-a1 | SENTUSDT | 2025-11-21 07:36:00 | 2026-01 | 2026-09 | 83,04 |
| tsx-x14-a1 | METUSDT | 2025-10-16 16:03:00 | 2025-11 | 2026-09 | 76,61 |
| tsx-x14-a1 | SAPIENUSDT | 2025-10-11 04:01:00 | 2025-11 | 2026-09 | 35,55 |
| tsx-x14-a1 | BANKUSDT | 2025-10-10 22:05:00 | 2025-11 | 2026-09 | 28,04 |
| tsx-x14-a1 | BANKUSDT | 2025-10-10 21:36:00 | 2025-11 | 2026-09 | 24,53 |

## 8. Giới hạn / CHƯA XÁC MINH

1. **CHƯA ĐO MAE**: printDone không có MAE (`maxmin15m` rỗng); cần chuỗi giá 1m cho 30 853 leg ⇒ chưa làm.
2. **CHƯA ĐO đóng góp maxDD**: scorer MTM chỉ có equity run-level, không có MTM per-leg; tách theo bucket phải chạy lại MTM có gắn nhãn ⇒ ngoài phạm vi "không chạy sim mới".
3. **CHƯA XÁC MINH oracle spot**: presence lấy từ Vision monthly. Đã kiểm một chiều (symbol delist vẫn giữ dữ liệu: SRMUSDT 2020-08..2022-11) và listing khớp TGE đã biết (PEPE 2023-05, BONK 2023-12, ENA/JUP/STRK 2024); nhưng **không có nguồn thứ hai** chứng minh Vision không thiếu file cho cặp đang niêm yết. 8 739/9 622 leg B3 thuộc base **không có bất kỳ** file spot nào (không phân biệt được "chưa từng có spot" với "Vision thiếu"). Vì B3 **lãi hơn** B5 ở mọi cửa sổ, sai số này không đổi kết luận "giữ".
4. **Độ phân giải tháng** cho phần giữa (không phải tháng biên): spot có file tháng ⇒ coi là đang giao dịch cả tháng; tháng biên dùng phút chính xác.
5. **PIT phân loại TradFi**: exchangeInfo là ảnh chụp 2026-10-27; đã chặn ticker tái sử dụng bằng `onboardDate`, nhưng nếu một symbol TradFi bị delist trước 10-27 thì không có trong snapshot (audit đã kiểm 2026: 0 thiếu). Với DEV, TradFi perp chưa tồn tại nên rủi ro = 0.
6. **Không tách sector L1/L2/meme/AI** (không có phân loại PIT khách quan ⇒ data-mining), đúng prereg.
7. HO 2026 đã nhìn nhiều lần; mọi số ở đây là mô tả, không phải holdout mới.

## 9. Tài nguyên

Kernel Kaggle `chuyendinh/spotpit-1028` v4: 88 s CPU, output 256 KB, không ghi dataset.
Oracle: thêm ~9 MB trong `~/claude_master/symtype_wk` (parquet + json + 2 CSV); không tải dữ liệu lớn; không sudo, không ssh 242, không REST API.
