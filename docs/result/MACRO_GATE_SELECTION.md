# MACRO_GATE Pha 0 — SELECTION (khoá TRƯỚC khi đọc Y CONFIRM 2024–25)

Prereg vz_e1_wt **24104dd6** (`docs/prereg/PREREG_MACRO_GATE.md`, md5 4e45a1bb). Code `research/macro_gate/macro.py` (`data`, `explore`), số liệu `docs/result/macro_gate_p0/{data,selection}.json`.

## 1. Dữ liệu ngoài (§1)
- Nguồn: (A) Yahoo chart v8 (adjclose + close + volume), (B) Nasdaq api `/quote/<T>/historical` (close + volume, KHÔNG điều chỉnh). Stooq bị chặn bởi JS challenge (Oracle) và proxy (cloud) ⇒ không dùng. Không dùng API key. Raw ~1,9 MB.
- 10/10 mã có cả 2 nguồn. Nasdaq chỉ trả từ 2021-11-15 (đủ cho return 20 phiên từ 2022-01). Yahoo 2021-10-01..2026-06-30.
- Đối chiếu return 20 phiên CÙNG CƠ SỞ (close chưa điều chỉnh cổ tức, cả 2 nguồn): tỉ lệ ngày lệch ≤ 0,5 pp — QQQ 100 %, XLP 100 %, GLD 99,82 % (max 0,93 pp), UUP 100 %, IBIT 100 %, FBTC 99,67 % (max 1,70 pp), ARKB/BITB/HODL/BRRR ≥ 99 %. ⇒ đạt ngưỡng ≥ 99 % mọi mã, không cờ `LECH_2NGUON` / `MOT_NGUON`.
- **Giới hạn khai báo**: Nasdaq không có lịch sử cổ tức cho mã không niêm yết Nasdaq (XLP, UUP, GLD: "Dividend History for Non-Nasdaq symbols is not available") ⇒ bản ĐIỀU CHỈNH (adjclose) chỉ có 1 nguồn (Yahoo). Tín hiệu dùng Yahoo adjclose đúng prereg. Độ nhạy: tín hiệu tính từ close Nasdaq chưa điều chỉnh trùng trạng thái với bản chính S2 99,9 %, S3 97,2 %, S4 98,6 %, V4 98,2 %, V3 98,3 % số ngày 2022–2026H1.
- BTC ngày: store `OHLCV_1H_v2.bin` (gộp 24 nến 1h UTC, ngày đủ 24 giờ) 2021-01..2025-12; thiếu 1 ngày (⇒ S1/V4 NaN 8 ngày quyết định, xếp vào N). 2026H1: store không có, IND_COMBO cũng không giữ nến 2026 ⇒ nối nến 1d BTCUSDT UM từ data.binance.vision (cùng nguồn Vision, checksum sha256 OK), trùng store 60 ngày lệch tối đa 3,7e-8. Chỉ ảnh hưởng HO (mô tả).
- E (ETF flow): ngày quyết định có dữ liệu đầu tiên 2024-01-20.

## 2. Causal + kiểm tay
- Ngày quyết định dd (UTC): phiên Mỹ dùng = phiên cuối cùng có ngày < dd (phiên D chỉ dùng từ 00:00 UTC D+1); BTC dùng nến ngày dd−1 đã đóng. Assert toàn bộ: `sess < dd` đúng 100 %, `btc_day = dd − 1` đúng 100 %.
- Leg: printDone `start` (+07) − 7 h = phút UTC (ind_build.load_legs của IND_COMBO); trạng thái gán theo phút ĐẦU của cụm → ngày UTC của phút đó.
- Kiểm tay 10 ngày ngẫu nhiên (rng 20261115), tính lại bằng vòng lặp riêng từ JSON raw + store: 10/10 khớp (giá trị S1v–S4v sai số < 1e-9, trạng thái S1–S4/V4/V3, phiên dùng): 2022-08-17, 2023-05-07, 2023-05-27, 2023-06-10, 2024-01-07, 2024-03-31, 2024-08-19, 2025-02-19, 2025-08-29, 2025-09-21.

## 3. Bảng leg/cụm (tái dùng IND_COMBO)
- `ind_build.load_legs` (commit 96f74733) + cụm ≤ 60′ trên hợp 8 seed: EXPLORE 10 256 leg / 117 cụm; CONFIRM 11 298 / 113; HO 2 275 / 29 — KHỚP IND_COMBO; trùng tuyệt đối `ind1114/legs_x.parquet` (M, y, cụm).
- Track G: `ind1114/g2_S*.npz` (r/q theo phút, đã khớp sig_meta R5 trong IND_COMBO) + Y72 `r5q_y.parquet`; E 17 613 dòng (2 428 pass), C 17 009 (2 479 pass); Y72 NaN 0.

## 4. Tần suất trạng thái defensive theo năm (X-only) — % ngày quyết định / % leg
| Kiểm | 2022 | 2023 | 2024 | 2025 | 2026H1 |
|---|---|---|---|---|---|
| S1 btc_trend | 32,3 / 72,0 | 12,9 / 7,0 | 20,8 / 22,7 | 20,8 / 34,5 | 29,3 / 88,7 |
| S2 qqq_trend | 52,1 / 54,6 | 14,5 / 8,0 | 8,7 / 5,7 | 17,5 / 12,5 | 18,2 / 4,4 |
| S3 qqq_vs_xlp | 62,5 / 72,3 | 12,9 / 16,9 | 22,7 / 15,9 | 22,2 / 15,6 | 30,9 / 39,4 |
| S4 safe_haven | 41,6 / 47,4 | 32,9 / 36,1 | 43,2 / 44,1 | 55,1 / 77,4 | 40,3 / 39,6 |
| V4 | 49,6 / 59,9 | 12,3 / 16,9 | 15,3 / 15,4 | 23,0 / 24,4 | 29,8 / 40,8 |
| V3 | 48,5 / 55,9 | 11,5 / 12,7 | 15,0 / 15,9 | 21,9 / 13,2 | 28,2 / 30,8 |
| E outflow (mô tả) | – | – | 15,6 / 22,8 | 20,8 / 26,1 | 21,0 / 76,3 |

## 5. EXPLORE 2022–23 (D = defensive; m1 pp/leg, CI90 bootstrap khối tháng 2 000 lần seed 20261115; m2 USD = ΣPnL leg D / 8 seed)
Khối tháng = tháng lịch (+07) CÓ leg: EXPLORE 21 khối.

| Kiểm | m1 | CI90 | m2 (2022 / 2023) | % leg | % cụm | episode (2022/2023) | seed42 m1 | ứng viên |
|---|---:|---|---|---:|---:|---|---:|:-:|
| S1 | +0,94 | [−1,60; +3,94] | +8 321 (+7 266 / +1 055) | 36,0 | 52,1 | 9 (7/2) | +1,10 | – |
| S2 | −3,42 | [−6,55; +2,50] | +1 295 (−794 / +2 089) | 28,8 | 35,9 | 7 (5/2) | −4,34 | – |
| S3 | −4,42 | [−6,92; +0,09] | +2 053 (−1 879 / +3 932) | 41,6 | 48,7 | 12 (8/4) | −5,19 | – |
| S4 | −0,54 | [−4,55; +5,31] | +11 844 (−1 382 / +13 226) | 41,1 | 37,6 | 14 (5/9) | −0,93 | – |
| V4 | −2,66 | [−5,73; +2,14] | +3 965 (+33 / +3 932) | 36,1 | 45,3 | 11 (7/4) | −3,56 | – |
| V3 | −2,75 | [−5,74; +2,64] | +3 466 (−176 / +3 642) | 32,0 | 34,2 | 9 (6/3) | −3,64 | – |

- Luật ứng viên (m1 < 0 VÀ CI90 không chứa 0 VÀ m2 ≤ 0 VÀ D 5–50 % leg VÀ ≥ 4 episode): **0/6 đạt**. Mọi kiểm có CI90 chứa 0 và m2 > 0 (leg trong regime defensive vẫn LÃI ròng — đúng bài học IND_COMBO). Bảng năm cộng đúng tổng (assert). Seed 42 cùng dấu gộp 6/6. Bootstrap chạy 2 lần trùng tuyệt đối.
- ⇒ **Track R ĐÓNG tại EXPLORE.** Không có ứng viên ⇒ không chạy kiểm CONFIRM track R.

## 6. CONFIRM (X-only, trước khi đọc Y) — số khối tháng, episode, MDE80
| Kiểm | khối tháng | % leg D | % cụm D | episode (2024/2025) | MDE80 m1 (pp) | MDE80 Holm m=2 |
|---|---:|---:|---:|---|---:|---:|
| S1 | 22 | 28,1 | 32,7 | 16 (7/9) | 3,55 | 4,15 |
| S2 | 22 | 8,8 | 11,5 | 3 (1/2) — KHÔNG ĐỦ MẪU | 5,96 | 6,98 |
| S3 | 22 | 15,8 | 20,4 | 7 (5/2) | 4,34 | 5,08 |
| S4 | 22 | 59,2 | 54,0 | 15 (7/8) — D > 50 % | 6,20 | 7,26 |
| V4 | 22 | 19,5 | 23,0 | 9 (3/6) | 5,10 | 5,97 |
| V3 | 22 | 14,7 | 18,6 | 7 (5/2) | 5,57 | 6,53 |
MDE80 = (z0,90 + z0,80) × se_EXPLORE × √(21/22): cần chênh ≥ 3,5–6,2 pp/leg mới có power 80 % — rất thiếu power (episode ít, regime tự tương quan).

## 7. Track G (V4/V3 thay ngũ phân vị; định nghĩa IND_COMBO; bootstrap khối tháng)
| Kiểm | relax 0,85 Δ [CI90] (Y72 nm∩bullish) | relax 0,70 Δ [CI90] | veto Δ [CI90] |
|---|---|---|---|
| V4 | +2,66 [+0,32; +4,90] (5,62) | +1,15 [−1,11; +3,02] (4,10) | +3,14 [+0,63; +6,87] |
| V3 | +2,17 [−1,76; +4,65] (5,12) | +1,14 [−2,16; +2,85] (4,10) | +3,23 [+0,45; +11,66] |
- Relax cần CI90 dưới > −1 pp ở CẢ 2 band: V4 band 0,70 = −1,11, V3 −1,76/−2,16 ⇒ trượt. Veto: Δ DƯƠNG (phút pass trong defensive có Y72 TỐT hơn) ⇒ không ứng viên.
- ⇒ **Track G ĐÓNG tại EXPLORE.**

## 8. Ứng viên chốt
- Track R: **không có**. Track G: **không có**. ⇒ Theo prereg §3, verdict dự kiến ĐÓNG; phần sau commit này chỉ chạy MÔ TẢ (E, chiều bullish, 6 kiểm defensive ở CONFIRM/HO để tham khảo, KHÔNG dùng quyết định).

## 9. Sai lệch so với prereg (tới bước này)
1. Stooq không tới được ⇒ nguồn 2 = Nasdaq api; Nasdaq không có cổ tức XLP/UUP/GLD ⇒ đối chiếu trên close chưa điều chỉnh (cùng cơ sở); adjclose chỉ 1 nguồn (Yahoo).
2. BTC 2026H1 từ data.binance.vision 1d (store hết 2025-12).
3. Khối tháng = 21 tháng có leg (EXPLORE), 22 (CONFIRM) — không phải 24 tháng lịch.
4. Track G dùng bootstrap khối tháng (theo §3 prereg này) thay vì cụm của IND_COMBO; Holm G cố định m = 4 (2 kiểm × 2 band).
5. Năm/kỳ theo mốc +07 như IND_COMBO (tái dùng load_legs).
