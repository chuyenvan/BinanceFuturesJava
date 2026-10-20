# UP_TRIG2 — Tầng A (offline): kết quả — 2026-10-20

Prereg: `docs/prereg/PREREG_UP_TRIG2.md` @ 90be57a5 (JSON ghi `prereg = PREREG_UP_TRIG2.md@90be57a5`). Script/JSON: `docs/result/up_trig2/ut2_a.py`, `docs/result/up_trig2/ut2_a.json` (bản gốc `~/claude_master/up_trig/ut2_a.*`, chạy 2026-10-20 14:25–14:33, 468 s).

**Verdict theo prereg: ĐẠT tầng A với V2 RISE10 ⇒ chỉ đề xuất forward paper log (không sim, không đưa vào hệ).** HO 2026 đã cháy cho họ này (tìm kiếm hậu kiểm) nên 2026 chỉ là mô tả; 2026 của RISE10 là −0,09 % (không dùng để quyết định, nhưng là tín hiệu cảnh báo).

## Validate (theo prereg)

| Kiểm | Kết quả |
|---|---|
| V1 giỏ đúng (in 3 sự kiện mỗi biến thể) | Có, `V1_print3` cho cả 5 biến thể; nsel = nval = K ở mọi mẫu in |
| V2 S1 REX dùng ngày t−1 | `all_s1day_eq_tday_minus1 = True` (n 1 320 lượt) |
| V3 tập sự kiện x_r ≥ 0,99 = UP_TRIG gốc | `n_E99 856 = n_orig 856, same_set = True`; RISE24 tính lại vs gốc max |Δ| 9,0e-5 |
| V4 không dùng C/2026 khi chọn | `selection_uses = TAB[*]['D'] only`; C chỉ cho biến thể đã chọn; 2026 chỉ mô tả |

Ghi chú: S1 REX (`rex/pred_s1.parquet`) phủ 2022-01-01 → 2025-12-31 ⇒ D của V3/V4 = 2022-01..2023-12 (đúng prereg), và V3/V4 không có số 2026 (n = 0). E95 (V5): 1 499 sự kiện (K=24: 262, K=5: 1 237).

## Bảng 5 biến thể (net TB/sự kiện sau phí 0,10 %; t_cl theo ngày)

| Biến thể | Tầng | n | net TB | median | win | t_cl | TB giỏ−BTC (gross) | bỏ top-5 | theo năm (net) |
|---|---|---|---|---|---|---|---|---|---|
| V1 RISE5 | D | 382 | +0,436 % | +0,175 % | 50,8 % | 1,09 | +0,412 % | +0,089 % | 2021 +0,89 · 2022 +0,23 · 2023 +0,43 |
| | C | 341 | +1,076 % | −0,039 % | 49,9 % | 1,82 | +0,850 % | +0,311 % | 2024 +1,32 · 2025 +0,83 |
| | 2026 | 133 | −0,280 % | −1,405 % | 45,1 % | −0,40 | −0,332 % | −1,135 % | |
| **V2 RISE10** | D | 382 | **+0,447 %** | +0,439 % | 54,5 % | 1,31 | +0,416 % | +0,127 % | 2021 +0,84 · 2022 +0,06 · 2023 +0,60 |
| | C | 341 | **+1,081 %** | +0,292 % | 51,9 % | **2,48** | **+0,855 %** | +0,617 % | 2024 +1,12 · 2025 +1,05 |
| | 2026 | 133 | −0,088 % | −0,411 % | 45,9 % | −0,16 | −0,140 % | −0,812 % | |
| V3 S1REX10 | D (2022–23) | 319 | +0,202 % | +0,070 % | 51,1 % | 0,81 | +0,129 % | −0,032 % | 2022 −0,08 · 2023 +0,41 |
| | C | 341 | +0,286 % | +0,205 % | 52,5 % | 1,15 | +0,059 % | +0,093 % | 2024 +0,60 · 2025 −0,03 |
| V4 S1REX24 | D (2022–23) | 319 | +0,180 % | +0,188 % | 51,4 % | 0,70 | +0,102 % | −0,052 % | 2022 −0,14 · 2023 +0,41 |
| | C | 341 | +0,283 % | +0,295 % | 54,0 % | 1,10 | +0,057 % | +0,090 % | 2024 +0,59 · 2025 −0,02 |
| V5 RISE_SCALED | D | 706 | +0,051 % | −0,020 % | 49,7 % | 0,24 | +0,122 % | −0,089 % | 2021 +0,32 · 2022 −0,46 · 2023 +0,43 |
| | C | 576 | −0,321 % | −0,638 % | 46,0 % | −0,95 | −0,309 % | −0,673 % | 2024 −0,11 · 2025 −0,53 |
| | 2026 | 217 | −0,244 % | −0,201 % | 47,0 % | −0,48 | −0,228 % | −0,774 % | |

## Áp luật prereg

**Chọn trên D** (≥ 50 sự kiện và net TB > 0): cả 5 đủ điều kiện. Net TB lớn nhất: V2 RISE10 +0,447 % > V1 RISE5 +0,436 % > V3 +0,202 % > V4 +0,180 % > V5 +0,051 % ⇒ **chọn V2 RISE10**. Prereg không đặt điều kiện t trên D (t_cl D = 1,31).

**Xác nhận C cho V2 RISE10:**

| Điều kiện | Ngưỡng | Giá trị | |
|---|---|---|---|
| net TB | > 0 | +1,081 % | ĐẠT |
| t_cl ngày | > 2 | 2,48 | ĐẠT |
| dương 2024 và 2025 | cả hai > 0 | +1,12 % / +1,05 % | ĐẠT |
| số sự kiện | ≥ 30 | 341 | ĐẠT |
| TB (giỏ − BTC, gross) | > 0 | +0,855 % | ĐẠT |

⇒ **ĐẠT** (`rule.verdict = DAT -> chi de xuat forward paper log`; tính tay từ bảng cho cùng kết quả).

## Đọc kết quả (rủi ro trước)

- Chọn RISE10 hơn RISE5 chỉ 0,011 điểm % trên D: lựa chọn gần như ngẫu nhiên giữa hai biến thể; RISE5 trên C sẽ trượt (t 1,82).
- D yếu (t 1,31; 2022 chỉ +0,06 %); bỏ top-5 sự kiện còn +0,13 % (D) / +0,62 % (C) ⇒ phần lớn lợi nhuận D nằm ở đuôi.
- 2026 (mô tả, HO đã cháy): RISE10 −0,09 %, median −0,41 %, win 45,9 %, bỏ top-5 −0,81 % — không ủng hộ edge còn sống ở regime hiện tại.
- K theo độ mạnh (V5) âm ở C và 2026 ⇒ giả thuyết "rateUp yếu thì K nhỏ" không được dữ liệu ủng hộ. Selector S1 REX (V3/V4) tệ hơn giỏ RISE ở cả D và C, và gần bằng BTC ở C (+0,06 %).
- Đây là tìm kiếm hậu kiểm 5 biến thể sau khi HO trượt; ĐẠT tầng A không phải bằng chứng xác nhận. Khuyến nghị tối đa: forward paper log RISE10 (luật cố định như prereg), không tune thêm K/giỏ/q/H.

## File

- `docs/result/up_trig2/ut2_a.py` — script (tái dùng `ut_a.py`).
- `docs/result/up_trig2/ut2_a.json` — bảng, validate, luật, verdict.
