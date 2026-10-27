# NUP3b — Pha 1: S0b / S1b / S1x × 4 seed DEV (G1–G3) — 2026-10-27

**Căn cứ.**
- Prereg `docs/prereg/PREREG_NUP3B.md` (9b49f7a9, sha256 `c544278c…`, đã kiểm). ADDENDUM_TECH dd9a92fe. Cổng PASS
  (`~/claude_master/nup3b_wk/gates.json`).
- Run `~/kaggle_sim/out/nup3b-{s0b,s1b,s1x}-{a1,s7,s21,s99}`. Riêng s0b-s99 lấy từ `nup3b-s0b-s99r`. 12/12 `ok`, jar `8aba4090…`.
- B0 = `tsx-x14-<seed>`.

**Cách chấm.**
- Thước đo và luật = PREREG_NUP3 §5–6 + diễn giải MASTER (như NUP3 P1).
- Equity tính từ 2021-07, **gồm PnL sleeve 2021H2** (giống ADDENDUM (c); NUP3b không có V2).
- Kỳ chấm DEV 2022–25, gán theo giờ đóng +07.
- S1x: sổ nền ≠ B0, nên MTM riêng; mọi "×B0" so với B0 cùng seed.

**Code / số máy.**
- Code `research/nup3/score_p1b.py` (check → map → mtm → score), `research/nup3/p1b_cmp.py`, kiểm tay `research/nup3/indep_p1.py`.
- Số máy `docs/result/nup3/p1b_{runs,years,quarters,arms}.csv`, `p1b_validate.json`, `p1b_check.json`.

## 0. Kết luận (risk-first)

| arm | G1 lệnh | G2 PnL | G3 DD/U | iso-DD (−30 % ± 3 pp) | Pha 1 |
|---|---|---|---|---|---|
| S0b (V0 × 0,525) | PASS | PASS | **FAIL**: median −34,05 % | **không giữ** (−4,05 pp) | TRƯỢT |
| S1b (V1 × 0,574) | PASS | PASS | **FAIL**: median −32,20 % (trượt 0,20 pp) | giữ (−2,20 pp) | TRƯỢT |
| S1x (S1b + nền bỏ symbol sleeve) | PASS | **FAIL**: ΣPnL ×0,941 | **FAIL**: median −33,41 % | **không giữ** (−3,41 pp) | TRƯỢT |

- **Đề xuất Pha 2 theo prereg §3: KHÔNG có arm nào.** Không push gì.
- **S1b trượt G3 chỉ 0,20 pp.**
  - maxDD từng seed: a1 −31,44, s7 −32,96, s21 −30,89, s99 −34,57. Median −32,199 < −32.
  - Số này chắc chắn, không phải sai số đo: bản sửa bug pipeline cho cùng maxDD; U của tôi khớp số sim tự đo tới 5e-7.
  - Theo luật, không làm tròn, không đổi s.
- **Giảm size không giảm DD tuyến tính.** Sleeve ΣPnL chỉ giảm còn ×0,71 (S0b) / ×0,72 (S1b), trong khi s = 0,525 / 0,574.
  - Cơ chế: throttle `1 − U_s/0,35` bớt chặn khi size nhỏ, nên size hiệu dụng > s (giới hạn đã khai ở prereg §5).
  - Hệ quả: DD chỉ cải thiện 1,9–2,8 pp so với size 1,0, thay vì 6,3 / 5,0 pp như ước lượng tuyến tính.
- **S1x (biến thể triển khai được trên one-way) phá sổ nền.**
  - Nền còn ×0,915 số cụm nhưng chỉ ×0,586 PnL (median). Nghĩa là nền mất khoảng 41 % PnL B0.
  - Cụm B0 rơi vào cửa sổ sleeve S1x đang giữ: khoảng 1 233 cụm/seed, mang 47,2k PnL B0 (≈ 42 % PnL B0) — đúng các lệnh crash-buy tốt.
  - ⇒ Luật symbol độc quyền làm sleeve ăn vào alpha nền. Toàn danh mục chỉ còn ΣPnL ×0,94.
  - Muốn triển khai được trên one-way, cần một luật khác: ví dụ nền được ưu tiên và sleeve nhường, như S1b.

## 1. Toàn danh mục (median 4 seed, ghép cặp B0), so cạnh NUP3 size 1,0 (số ADDENDUM (c))

| chỉ số | B0 | NUP3 V0 (s=1) | **S0b** (0,525) | NUP3 V1 (s=1) | **S1b** (0,574) | **S1x** |
|---|---|---|---|---|---|---|
| cụm/năm (×B0) | 721 | ×1,815 | 1 320,5 (×1,822) | ×1,712 | 1 238,6 (×1,712) | 1 581 (×2,176) |
| ×B0 các năm 22/23/24/25 | 1 | 1,75/1,74/1,96/1,73 | 1,79/1,74/1,96/1,73 | 1,64/1,65/1,83/1,65 | 1,64/1,65/1,83/1,65 | 1,91/2,00/2,41/2,31 |
| ΣPnL ×B0 | 112 467 | ×1,620 | 159 962 (×1,442) | ×1,580 | 157 738 (×1,420) | 109 063 (×**0,941**) |
| stress −20 bps ×B0 | — | ×1,599 | ×1,431 | ×1,560 | ×1,409 | ×0,900 |
| CAGR22 % | 38,6 | 50,4 | 48,0 | 49,5 | 47,1 | 39,2 |
| maxDD median / tệ % | −22,5 / −24,7 | −36,33 / −36,62 | **−34,05 / −35,33** | −34,99 / −36,20 | **−32,20 / −34,57** | **−33,41 / −34,04** |
| Calmar | 1,716 | 1,388 | 1,397 | 1,426 | 1,469 | 1,168 |
| U notional@mark max (median / tệ) | 0,51 | 0,764 / 0,781 | 0,741 / 0,754 | 0,743 / 0,773 | 0,714 / 0,726 | 0,710 / 0,734 |
| U margin@entry max (median / tệ) | — | 1,113 / 1,187 | 1,032 / 1,142 | 1,060 / 1,169 | 0,974 / 1,110 | 0,992 / 1,042 |
| leg sleeve mở khi Σ margin > equity (a1/s7/s21/s99) | — | 2/2/0/0 | 0/10/0/4 (≤ 0,41 %) | 0/0/0/3 | 0/0/0/2 (≤ 0,10 %) | 0/0/0/0 |
| số vị thế max | 69 | 126 | 126 | 111 | 111 | 103 |

maxDD toàn kỳ 2021-07 → 2025-12 = maxDD 2022–25 ở mọi run: đáy là 2022-05.

## 2. Riêng sleeve (DEV, median 4 seed)

| chỉ số | NUP3 V0 | **S0b** | NUP3 V1 | **S1b** | **S1x** |
|---|---|---|---|---|---|
| cụm/năm | 585,9 | 592,1 | 511,5 | 512,0 | 921,6 |
| ROI/lệnh; ROI_stress | 2,34 %; 2,14 % | 2,57 %; 2,37 % | 2,35 %; 2,15 % | 2,51 %; 2,31 % | 1,72 %; 1,52 % |
| ΣPnL; ΣPnL_stress | 69 597; 63 642 | 49 649; 45 782 | 65 079; 59 531 | 47 180; 43 421 | 41 000; 36 115 |
| ΣPnL_stress 2022/23/24/25 | −1 265/17 146/21 176/25 158 | 367/11 011/16 549/16 703 | −82/16 088/18 788/23 021 | 821/10 755/14 865/15 858 | **−1 978**/9 715/15 049/13 705 |
| năm dương; seed dương | 3/4; 4/4 | 4/4; 4/4 | 3/4; 4/4 | 4/4; 4/4 | 3/4; 4/4 |
| overlap: cụm nền mở trên symbol sleeve đang giữ | 1 380,5 (48 %) | 1 389,5 (48 %) | 1 195 (41 %) | 1 200,5 (41 %) | **0** |
| đợt (< 6h)/năm; không giao đợt nền | 48,3; 39 % | 48,8; 39 % | 48,0; 43 % | 48,5; 43 % | 83,3; 56 % |
| ngày có lệnh/năm; % ngày nền không có lệnh | 45,0; 30 % | 45,5; 30 % | 44,6; 31 % | 45,0; 31 % | 75,1; 39 % |
| corr PnL ngày với nền | 0,555 | 0,568 | 0,522 | 0,541 | 0,419 |
| top-10 ngày % ΣPnL | 45 % | 42 % | 45 % | 42 % | 39 % |

Ghi chú:
- S1x so với nền của chính nó.
- S1x: overlap = 0, `base_skip_backstop` = 0 ở cả 4 seed, đúng thiết kế.

## 3. S1x: cụm nền bị bỏ và chi phí cơ hội (chỉ mô tả)

| seed | nền S1x cụm DEV (×B0) | PnL nền S1x DEV (×B0) | (C) cụm B0 có t0 trong cửa sổ giữ của sleeve S1x: số; ΣPnL B0 | (A) cụm B0 mở đúng phút chặn đầu tiên trong log: số; ΣPnL B0 |
|---|---|---|---|---|
| a1 | 2 627 (×0,915) | 56 067 (×0,484) | 1 170; 46 858 | 98; 2 687 |
| s7 | 2 681 (×0,927) | 63 738 (×0,585) | 1 236; 47 533 | 107; 2 414 |
| s21 | 2 635 (×0,916) | 69 876 (×0,640) | 1 230; 46 365 | 134; −2 367 |
| s99 | 2 624 (×0,880) | 72 388 (×0,587) | 1 341; 54 146 | 149; 6 162 |
| median | ×0,915 | ×0,586 | 1 233; 47 196 | 120,5; 2 551 |

**Cách ghép.**
- Log `BASE-SKIP-SLEEVE sid tMs lvl sleeveT0` có 4 069–4 285 dòng/run (PREDICT 96–98 %, BIG_DOWN 2–3 %), mỗi cụm sleeve một dòng
  ở lần chặn đầu tiên.
- `sid → sym` dựng từ chính dữ liệu run: dòng OPEN của `sleeve_cand.csv` khớp cụm sleeve mở cùng phút, 100 % khớp phút.
  - Map được duy nhất 573 sid; 14 sid còn mơ hồ (các coin mới niêm yết cùng đợt). Không có sid trùng.
  - 3–11 dòng log/run (≤ 0,26 %) không map được ⇒ chỉ ảnh hưởng (A).
  - Mọi dòng đã map đều tìm thấy cụm sleeve (sym, t0 = sleeveT0) tương ứng trong printDone S1x.
- (C) dùng mọi cụm sleeve S1x (không cần map) và cho cùng số với cửa sổ chỉ dựng từ log (B), lệch ≤ 3 cụm.
- (C) là số phản thực: cụm mà B0 sẽ mở nhưng S1x cấm. (A) là cận dưới chặt: chỉ cụm trùng đúng phút log.

**Diễn giải.**
- Nền S1x không mất hết 1 233 cụm. Nó mở thay ~990 cụm khác, gần như không lãi.
- Tổng PnL nền giảm 45–60k, xấp xỉ ΣPnL B0 của (C).
- Giả thuyết **CHƯA KIỂM** vì sao sleeve S1x mở nhiều hơn S1b (4 270 so với 2 372 cụm sim): symbol sleeve đang giữ không vào
  gate/buffer nền nữa, nên ứng viên bị gate từ chối đến sleeve toàn là symbol trống (`skip_held_sleeve` 0 so với 5 599).

## 4. Luật §6 (Pha 1, ngưỡng seed ≥ 3/4)

- **G1** (≥ 1,30× và mỗi năm ≥ 1,15×): S0b PASS (1,822), S1b PASS (1,712), S1x PASS (2,176).
- **G2** (ΣPnL ≥ 1,00× B0, sleeve stress > 0 ở ≥ 3/4 năm và ≥ 3/4 seed):
  - S0b PASS: 1,442; 4/4 năm; 4/4 seed.
  - S1b PASS: 1,420; 4/4 năm; 4/4 seed.
  - S1x **FAIL**: ΣPnL ×0,941. Phần sleeve thì đạt (3/4 năm, 4/4 seed).
- **G3** (maxDD median ≥ −32 %, seed tệ ≥ −36 %, U ≤ 1,0):
  - S0b FAIL (−34,05).
  - S1b FAIL (−32,20).
  - S1x FAIL (−33,41).
  - Vế seed tệ và vế U (notional@mark, tệ nhất 0,754) đạt ở cả 3 arm.
- **Kiểm s\*** (prereg §4): maxDD median sim so với −30 % là S0b −4,05 pp ⇒ **"iso-DD tuyến tính không giữ"**; S1b −2,20 pp ⇒ giữ;
  S1x −3,41 pp ⇒ **"iso-DD tuyến tính không giữ"**. KHÔNG chỉnh s.

## 5. Validate

| kiểm | kết quả |
|---|---|
| G-INV S0b/S1b cả 4 seed: lọc `book=sleeve` ⇒ md5 = B0 | PASS 8/8 (a1 `dc62609b`, s7 `622b03e2`, s21 `6f15b4d7`, s99 `53fa789d`) |
| Cấu hình từng run | PASS: jar `8aba4090`, ok, arm, size, cờ `BASE_SKIP_SLEEVE_SYMBOLS` đúng arm, `n_trades` = nền + sleeve, sleeve nằm sau nền. S1x: overlap sim = 0, backstop = 0. |
| B0 tái lập (cụm, PnL, maxDD) | PASS (assert) |
| Σ quý = tổng, Σ năm = tổng | PASS (lệch tuyệt đối < 1e-6), 12 run |
| Kiểm tay độc lập (`indep_p1.py`, chỉ csv/datetime) S1x × s7 | PASS, lệch 0. Sleeve 619/786/1 247/1 053 cụm, ΣPnL 41 621,62. Nền 504/730/805/642, ΣPnL 63 738,42. Toàn danh mục 1 123/1 516/2 052/1 695, ΣPnL 105 360,04. |
| MTM missing | 0 ở cả 20 sổ (4 B0 + 12 sleeve + 4 nền S1x) |
| Kiểm chéo với sim (toàn kỳ) | U margin@entry max và số vị thế max trùng số sim tự đo (≤ 7e-7). U notional@mark lệch ≤ 0,0014 ở 5 run, do bug pipeline month-boundary (NUP3_P1 §6). Với equity đã sửa thì trùng sim ≤ 5e-7 ở cả 12 run. maxDD trước/sau sửa trùng nhau (đáy 2022-05, trước phút lệch đầu tiên). |

## 6. Lệch / diễn giải / rủi ro của agent

1. U trong bảng là số pipeline NUP (chưa sửa bug). Bản đã sửa thấp hơn ≤ 0,0014 ở 5 run. Kết luận không đổi.
2. `sid → sym` không có file mapper của sim, nên phải dựng lại từ dữ liệu run (nêu ở §3). Số chi phí cơ hội chính dùng (C), không cần map.
3. N_eff, overlap và quy ước ngày giữ như NUP3_P1 §7. S1x tính N_eff so với nền của chính nó.
4. Trial ledger họ NUP: +3 (prereg).
