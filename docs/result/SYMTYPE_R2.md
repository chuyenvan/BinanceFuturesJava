# SYMTYPE_R2 — chạy lại bảng sau khi sửa bug chuẩn hoá `base()` (2026-10-30)

Bản R1 giữ nguyên: `docs/result/SYMTYPE.md`. Addendum prereg: `docs/prereg/PREREG_SYMTYPE_ADDENDUM1.md`.
Phạm vi vẫn là MÔ TẢ: không chạy sim mới, không đổi universe/ngưỡng, không gọi Binance REST, không ssh 242.
Script: `~/claude_master/symtype_wk/{prep_legs,assign_bucket,measure,validate}.py` (đã sửa); bản R1 của
`prep_legs.py` lưu tại `prep_legs_r1.py`.

## 0. TL;DR

| | R1 (10-28) | R2 (10-30) | Δ |
|---|---|---|---|
| DEV leg / PnL | 23 583 / +925 538,48 | **23 583 / +925 538,48** | 0 / 0,00 |
| B3 PERP-KHÔNG-SPOT | 5 291 leg / +318 655,0 / +60,23 mỗi leg | **5 196 / +311 737,1 / +60,00** | **−95 leg** |
| B4 MỚI NIÊM YẾT | 2 497 / +88 397,1 / +35,40 | **2 505 / +88 769,7 / +35,44** | +8 leg |
| B5 crypto-native | 15 739 / +517 161,3 / +32,86 | **15 826 / +523 706,7 / +33,09** | +87 leg |
| HO (x14, k24-s) | như cũ | **như cũ, 0 leg đổi** | 0 |
| Quyết định | B1–B4 "GIỮ, chỉ theo dõi" | **B1–B4 "GIỮ, chỉ theo dõi"** | không đổi |

Chỉ **95/126** leg bị ảnh hưởng **thực sự đổi bucket** (87 B3→B5, 8 B3→B4); 31 leg còn lại **vẫn B3 đúng** vì spot
1000X tương ứng **chưa niêm yết** tại giờ vào lệnh (PIT).

## 1. Bug và cách sửa

`prep_legs.py` cũ:

```python
def base(sym):                      # sym = "1000SATSUSDT"
    b = sym[:-4]                    # "1000SATS"
    m = re.match(r"^(1000000|1000)(.+)$", b)
    return m.group(2) if ...        # -> "SATS"   (LUÔN cắt)
```

`base()` được dùng làm khoá tra spot PIT. Với 3 symbol mà **tên perp chính là tên spot thật**:

| perp | base cũ (sai) | spot thật | base R2 |
|---|---|---|---|
| 1000SATSUSDT | SATS | **1000SATSUSDT** (2023-12 → 2026-09) | 1000SATS |
| 1000CATUSDT | CAT | **1000CATUSDT** (2024-12 → 2026-09) | 1000CAT |
| 1000CHEEMSUSDT | CHEEMS | **1000CHEEMSUSDT** (2025-02 → 2026-09) | 1000CHEEMS |

⇒ tra `SATSUSDT/CATUSDT/CHEEMSUSDT` (không tồn tại) ⇒ `spot_alive=false` ⇒ **B3 sai**.

Sửa:

```python
SPOT_SYMS = {r["symbol"] for r in csv.DictReader(open(W + "/spot_out/spot_sym_months.csv"))}
def base(sym):
    b = sym[:-4]
    if b + "USDT" in SPOT_SYMS:      # ten spot khop nguyen van duoc uu tien
        return b
    m = re.match(r"^(1000000|1000)(.+)$", b)
    return m.group(2) if m and len(m.group(2)) >= 2 else b
```

Sửa kèm: `legs_all.parquet` trước đây được ghi **trước** khi thêm cột `base` (pipeline R1 chỉ chạy được nhờ file
parquet còn sót từ một lần chạy khác) — nay ghi **sau** khi có `base`.

Không cần chạy lại kernel `spotpit-1028`: `spot_sym_months.csv` đã có đủ 755 symbol spot (gồm cả 3 tên 1000X);
lỗi nằm ở **cách tra**, không ở dữ liệu spot.

## 2. Leg đổi bucket

126 leg DEV nằm trên 3 symbol này (không có leg HO nào — xem §4). Phân bố sau khi sửa:

| symbol | leg | → B5 | → B4 | vẫn B3 (spot chưa niêm yết tại giờ vào) | PnL (B3 → B5/B4) |
|---|---|---|---|---|---|
| 1000SATSUSDT | 55 | 47 | 8 | 0 | +6 045,6 (toàn bộ vào B5/B4) |
| 1000CATUSDT | 31 | 24 | 0 | 7 | −3 078,5 (B3) → +1 804,3 (B5) |
| 1000CHEEMSUSDT | 40 | 16 | 0 | 24 | +2 927,6 (B3) → −931,9 (B5) |
| **tổng** | **126** | **87** | **8** | **31** | |

- 8 leg thành B4 là các leg 1000SATS vào trong 30 ngày đầu sau khi spot 1000SATSUSDT niêm yết (2023-12).
- 31 leg "vẫn B3" là các leg 1000CAT (7) / 1000CHEEMS (24) vào **trước** tháng spot đầu tiên — đúng PIT, không phải bug.
- Phân bố theo seed: mỗi seed có **14–18 leg** thuộc 3 symbol này, trong đó **11–14 leg thực sự đổi bucket**; không seed nào bị dồn bất thường.

## 3. Bảng DEV sau sửa (R2) và so R1

### DEV all (8 seed, 2022-01..2025-12) — 23 583 leg, +925 538,48 (không đổi)

| bucket | leg R1 → R2 | PnL R1 → R2 | PnL/leg R1 → R2 | win R2 | hold (h) R2 |
|---|---|---|---|---|---|
| B1 TRADFI | 0 → 0 | 0,0 → 0,0 | — | — | — |
| B2 INDEX/hàng hoá/stable | 56 → 56 | 1 325,0 → 1 325,0 | 23,66 → 23,66 | 67,9 % | 182,3 |
| **B3 PERP-KHÔNG-SPOT** | **5 291 → 5 196** | **318 655,0 → 311 737,1** | **60,23 → 60,00** | 89,8 % | 26,6 |
| B4 MỚI NIÊM YẾT <30d | 2 497 → 2 505 | 88 397,1 → 88 769,7 | 35,40 → 35,44 | 86,5 % | 44,1 |
| B5 crypto-native | 15 739 → 15 826 | 517 161,3 → 523 706,7 | 32,86 → **33,09** | 84,8 % | 61,5 |

### Theo năm — chỉ B3/B4/B5 đổi (2022 không đổi)

| năm | B3 (n / PnL/leg) | B4 (n / PnL/leg) | B5 (n / PnL/leg) |
|---|---|---|---|
| 2022 | 13 / 46,37 (không đổi) | 311 / 14,92 | 4 500 / 8,12 |
| 2023 | 288→**280** / 29,44→**28,95** | 917→**925** / 35,09→**35,19** | 4 848 / 44,16 |
| 2024 | 1 040→**985** / 62,80→**62,67** | 769 / 53,38 | 4 921→**4 976** / 40,51→**40,79** |
| 2025 | 3 950→**3 918** / 61,84→**61,59** | 500 / 21,06 | 1 470→**1 502** / 45,68→**46,68** |

Tỷ lệ PnL/leg so B5 theo năm (dùng cho luật): B3 5,71 / 0,66 / 1,54 / 1,32; B4 1,84 / 0,80 / 1,31 / 0,46.
**Không năm nào B3/B4 < 50 % của B5 ở ≥3/4 năm** ⇒ điều kiện (ii) vẫn không đạt.

## 4. HO 2026 — không đổi (kể cả khi kiểm thêm k24-b)

Trong 3 nguồn HO (tsx-ho-x14 8 seed, ho4-k24-s 8 seed, **ho4-k24-b 8 seed**), **0 leg** trên
1000SATSUSDT/1000CATUSDT/1000CHEEMSUSDT. Vì vậy nhận định trong audit ("một số leg HO bị gán sai B3") **không tái lập
được** với 3 cấu hình đang dùng — ghi rõ để MASTER kiểm lại nguồn audit. Bảng HO R2 = R1 từng số:

| cấu hình | B1 | B3 | B4 | B5 |
|---|---|---|---|---|
| tsx-ho-x14 W9 | 236 / −6 367,0 | 2 161 / +99 587,6 | 28 / +4 217,4 | 1 210 / +47 405,8 |
| ho4-k24-s W9 | 238 / −6 083,5 | 2 170 / +55 391,9 | 29 / +3 203,4 | 1 198 / +21 584,6 |

## 5. Quyết định theo luật (áp nguyên văn, không đổi)

| bucket | (ii) DEV | (iii) HO cùng chiều? | Kết luận |
|---|---|---|---|
| B1 | N=0 (định nghĩa classifier; literal: 17 leg — xem ADD-1 §C) | có (âm hơn B5) | GIỮ, chỉ theo dõi |
| B2 | N=56 < 300 | không có leg | GIỮ, chỉ theo dõi |
| B3 | PnL/leg **cao hơn** B5 (0,66–5,71×) | ngược chiều | GIỮ, chỉ theo dõi |
| B4 | chỉ 1/4 năm < 50 % B5 | ngược chiều | GIỮ, chỉ theo dõi |

**Không bucket nào đủ điều kiện đề xuất loại.** Sửa bug **không đổi kết luận** — nhưng làm B3 bớt bị thổi phồng
95 leg (PnL −6 918) và minh bạch hơn ở B5.

## 6. Validate R2

- **V0**: 30 853 leg, 0 NaN, mỗi leg đúng 1 nhãn. Phân bố: B1 474, B2 56, **B3 9 527** (R1 9 622), B4 2 562, B5 18 234.
- **V1 (khớp tổng)**: 30 853 leg / **+1 144 478,70**, Δleg = 0, ΔPnL = 0,00 với printDone gốc.
- **V2** (3 leg tính lại độc lập bằng `derive()`): 3/3 khớp (PENGU B5, GWEI B3, AVAAI B3).
- **V3** (PIT): 526 leg B3 có `spot first_month` **sau** tháng vào lệnh (R1: 495) — tăng vì 31 leg 1000CAT/CHEEMS
  vẫn B3 đúng lý do PIT; không phải lỗi.

## 7. Ghi chú / giới hạn

- Nhãn B3 phụ thuộc **oracle spot Vision theo tháng**; 8 700+ leg B3 thuộc base không có bất kỳ file spot nào
  (không phân biệt "chưa từng có spot" với "Vision thiếu") — giữ nguyên như R1 §8.3, không đổi kết luận vì B3 vẫn lãi hơn B5.
- Không tách sector, không dùng MAE (printDone không có), không đo đóng góp maxDD — như R1.
- Tài nguyên: chỉ đọc `~/kaggle_sim/out` (48+8 `printDone.csv` đã có) + CSV spot/lifecycle; không tải mới, không Kaggle
  kernel mới, không sudo, không ssh 242.
