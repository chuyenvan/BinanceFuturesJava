# NUP3 — Pha 1: chấm V0/V1/V2 × 4 seed DEV (G1–G3) — 2026-10-27

Prereg `docs/prereg/PREREG_NUP3.md` (c2b4c462, sha256 `f600be0a…` — đã kiểm lại khớp), ADDENDUM_TECH (ab2391e4), cổng `docs/result/nup3/GATES.md` (PASS).
Run `~/kaggle_sim/out/nup3-v{0,1,2}-{a1,s7,s21,s99}` (12/12 `ok`, jar `b269f96b…`), B0 = `tsx-x14-<seed>`.
Code chấm: `research/nup3/score_p1.py` (check → mtm → score), `research/nup3/indep_p1.py` (kiểm tay độc lập), `research/nup3/p1_cmp.py`,
`research/nup3/g3_offset_sens.py`. Số máy: `docs/result/nup3/p1_*.csv`, `p1_validate.json`, `p1_check.json`.

## 0. Kết luận (risk-first)

| arm | G1 lệnh | G2 PnL | G3 DD/U | Pha 1 |
|---|---|---|---|---|
| V0 | PASS | PASS | **FAIL** (maxDD median −37,81 %, tệ −38,17 %) | TRƯỢT |
| V1 | PASS | PASS | **FAIL** (−36,49 % / −36,89 %) | TRƯỢT |
| V2 | **FAIL** (2023 = 1,147× < 1,15) | PASS | **FAIL** (median −34,38 % < −32; tệ −34,65 % ≥ −36 đạt) | TRƯỢT |

- **Đề xuất Pha 2 theo luật §4.3: KHÔNG có arm nào** (không arm nào qua đủ G1–G3). Không push gì.
- Sleeve có edge thật trên DEV: ROI/lệnh khoảng +2,3–2,6 %, 4/4 seed dương, 3/4 năm dương. Nhưng nó **dồn rủi ro vào đúng cú sập của
  nền**: maxDD của cả 12 run đều nằm ở cùng một đoạn, đỉnh 2022-05-05, đáy 2022-05-12 (LUNA), giống B0. DD tăng từ −22,5 % lên
  −34…−38 %, Calmar giảm từ 1,72 xuống 1,35–1,41. Tương quan PnL ngày giữa sleeve và nền là 0,40–0,55. Năm 2022, ΣPnL_stress của sleeve
  ≈ 0 hoặc âm ở cả 3 arm.
- **⚠ Độ nhạy G3 theo luật loại 2021H2 (xem §5).** DD %, U, CAGR được tính trên một equity KHÔNG chứa PnL thực hiện của sleeve
  2021H2 (bị loại theo diễn giải MASTER). Trong khi đó, sim đã size sleeve từ 2022 trở đi trên equity chung CÓ khoản đó.
  - Nếu khoản này dương X USD, maxDD thật sẽ nhẹ hơn. Ngưỡng X để G3 lật, chưa ai biết X (không tính):
    - V0 cần X ≈ 8,6k (20 % equity đầu 2022) để median đạt −32 %.
    - V1 cần ≈ 6,6k (16 %).
    - V2 cần ≈ 3,4k (8 %), nhưng V2 vẫn trượt G1 nên không đổi kết luận.
  - Phần "seed tệ ≥ −36 %" lật với X nhỏ hơn nhiều: V0 cần 2,9k, V1 cần 1,1k (tính cho seed khó nhất).
  - ⇒ **Verdict G3 của V0/V1 phụ thuộc vào một số đang bị bịt.** MASTER cần quyết, xem §8.

## 1. Diễn giải MASTER đã chốt (áp dụng nguyên văn)

1. Kỳ chấm DEV 2022-01-01 → 2025-12-31. Lệnh gán theo giờ ĐÓNG +07, giống NUP.
2. 2021H2 là kỳ xác nhận V2.
   - Dòng sleeve có giờ đóng < 2022-01-01 +07 bị **loại ngay khi đọc** (`parse(..., drop_before=DEV_A)`). Không có PnL nào của chúng
     được tính hay in ra.
   - Số dòng bị loại (chỉ đếm): V0 418–442, V1 336–361, V2 169–216.
   - Leg sleeve vắt qua mốc (mở trước 2022, đóng từ 2022): **0** ở cả 12 run. Vì vậy không có giá trị MTM sleeve nào trước phút
     2021-12-31 23:59 +07. Code vẫn kẹp `m0` để chắc chắn.
   - Sổ nền là B0 byte-identical (số đã công bố) ⇒ giữ nguyên cả 2021H2 để tái lập số B0.
3. G3 U tổng = Σ notional@mark (nền + sleeve) / equity MTM toàn danh mục. Notional@mark = Σq·e + unrealized = Σq·close.
   Báo thêm margin@entry / equity, và số leg sleeve được mở lúc Σ margin@entry > equity.
4. maxDD = MTM toàn danh mục, một equity chung = eq_nền + eq_sleeve − vốn.
   - Pipeline NUP `research/nup/mtm_parquet.py` (ADDENDUM B), gọi y nguyên. Chỉ thay nguồn leg qua monkeypatch `R.load_legs`.
   - missing = 0 (assert).
5. Overlap = số cụm nền MỚI (t0 trong DEV) mở trên symbol mà sleeve đang giữ.
6. "K sleeve 24/đợt" hiểu là top-24 mỗi tick (D2). Ứng viên bị nền từ chối vì sổ đầy vẫn được xét (D1). Chấp nhận cả hai.

## 2. Toàn danh mục (median 4 seed, ghép cặp B0 cùng seed)

| chỉ số | B0 | V0 | V1 | V2 |
|---|---|---|---|---|
| cụm/năm | 721,1 | 1 310,9 (×1,815) | 1 233,5 (×1,712) | 1 007,8 (×1,384) |
| ×B0 2022 / 2023 / 2024 / 2025 | 1 | 1,745 / 1,739 / 1,958 / 1,731 | 1,639 / 1,650 / 1,827 / 1,649 | 1,557 / **1,147** / 1,438 / 1,450 |
| ΣPnL USD | 112 467 | 180 505 (×1,620) | 176 537 (×1,580) | 148 823 (×1,321) |
| stress −20 bps | 106 509 | 168 657 (×1,599) | 165 080 (×1,560) | 139 990 (×1,314) |
| CAGR22 % | 38,56 | 51,85 | 51,17 | 46,22 |
| maxDD MTM median / tệ % | −22,47 / −24,66 | −37,81 / −38,17 | −36,49 / −36,89 | −34,38 / −34,65 |
| Calmar | 1,716 | 1,369 | 1,407 | 1,351 |
| U tổng max notional@mark (median / tệ) | 0,512 / 0,519 | 0,782 / 0,795 | 0,763 / 0,787 | 0,723 / 0,767 |
| U margin@entry / equity max (median / tệ) | — | 1,189 / 1,209 | 1,131 / 1,204 | 1,050 / 1,093 |
| số vị thế max (median / max) | 69 | 121,5 / 126 | 107 / 111 | 94,5 / 96 |

Ghi chú:
- Tỷ lệ là median của tỷ lệ từng seed.
- Từng seed xem `p1_runs.csv`; theo năm xem `p1_years.csv`; theo quý (2022Q1–2025Q4) xem `p1_quarters.csv`.

## 3. Riêng sleeve (DEV, gán theo giờ đóng +07; median 4 seed)

| chỉ số | V0 | V1 | V2 |
|---|---|---|---|
| cụm/năm | 585,9 | 511,5 | 276,8 |
| ROI/lệnh (ΣPnL/Σnotional) | +2,34 % | +2,35 % | +2,65 % |
| ROI_stress | +2,14 % | +2,15 % | +2,45 % |
| ΣPnL / ΣPnL_stress USD | 69 597 / 63 642 | 65 079 / 59 531 | 35 935 / 33 248 |
| ΣPnL_stress 2022 / 23 / 24 / 25 | **−1 265** / 17 146 / 21 176 / 25 158 | **−82** / 16 088 / 18 788 / 23 021 | **−429** / 2 814 / 18 201 / 10 507 |
| số năm stress > 0 (median theo năm; từng seed) | 3/4 (3,3,4,3) | 3/4 (3,4,4,3) | 3/4 (4,3,4,3) |
| số seed ΣPnL_stress > 0 | 4/4 | 4/4 | 4/4 |
| overlap: cụm nền mở trên symbol sleeve đang giữ | 1 380,5 (47,8 % cụm nền) | 1 195 (40,8 %) | 703,5 (24,1 %) |
| đợt (t0 cách < 6h)/năm; đợt không giao đợt nền/năm (%) | 48,3; 18,8 (39 %) | 48,0; 20,4 (43 %) | 21,6; 7,5 (35 %) |
| ngày có lệnh/năm; % ngày nền không có lệnh | 45,0; 29,7 % | 44,6; 30,5 % | 20,3; 22,2 % |
| corr PnL ngày sleeve–nền | 0,555 | 0,522 | 0,403 |
| top-10 ngày % ΣPnL sleeve | 45,0 % | 44,5 % | 68,9 % |

Overlap từng seed (a1/s7/s21/s99):
- V0: 1386 / 1371 / 1375 / 1427
- V1: 1225 / 1175 / 1175 / 1215
- V2: 682 / 694 / 713 / 723
- Số của sim cho toàn kỳ, gồm cả 2021H2 (`overlap_base_opens_sleeve_sym`): V0 1646–1736, V1 1403–1473, V2 826–919. Mức này nhất quán:
  số của sim lớn hơn số DEV vì có thêm 2021H2.

⇒ Giới hạn live one-way ở §7 rất nặng: 24–48 % cụm nền rơi vào symbol sleeve đang giữ.

## 4. Luật §6 (Pha 1: ngưỡng seed ≥ 3/4)

- **G1** (cụm/năm ≥ 1,30× VÀ mỗi năm ≥ 1,15×):
  - V0 PASS: 1,815; min năm 1,731.
  - V1 PASS: 1,712; min năm 1,639.
  - V2 **FAIL**: tổng 1,384 đạt, nhưng 2023 = 1,147. Từng seed 1,133 / 1,133 / 1,162 / 1,161, median 1,147 < 1,15.
- **G2** (ΣPnL toàn danh mục ≥ 1,00× VÀ sleeve ΣPnL_stress > 0 ở ≥ 3/4 năm VÀ ≥ 3/4 seed):
  - V0 PASS: 1,620; 3/4 năm; 4/4 seed.
  - V1 PASS: 1,580; 3/4; 4/4.
  - V2 PASS: 1,321; 3/4; 4/4.
  - "≥ 3/4 năm" đọc trên median-seed của từng năm. Đọc theo từng seed thì mọi seed đều ≥ 3/4, kết quả như nhau.
- **G3** (maxDD median ≥ −32 %, seed tệ ≥ −36 %, U tổng max ≤ 1,0):
  - Cả 3 arm FAIL vì DD median. V0, V1 trượt cả vế seed tệ.
  - U notional@mark max tệ nhất 0,795 ≤ 1,0, đạt. Áp ngưỡng U cho seed tệ nhất, chặt hơn median.
  - Vế U của G3 sẽ trượt nếu đo bằng margin@entry: 1,05–1,21 > 1,0. MASTER đã chọn cách đo notional@mark.

## 5. U / margin / leg bị từ chối

- Notional@mark / equity: max 0,708–0,795. Không phút nào > 1,0. Sim tự đo cho toàn kỳ (gồm 2021H2): max 0,777–0,821,
  `u_total_fail_ticks = 0` ở cả 12 run.
- Margin@entry / equity: max 1,03–1,21. Số phút > 1,0 trong DEV: V0 1 747–2 065, V1 338–1 855, V2 8–452.
- **Leg sleeve mở lúc Σ margin@entry > equity** (trên sàn thật sẽ bị từ chối):
  - V0: 5 / 4 / 3 / 0, tức 0,00–0,21 % số leg sleeve mở trong DEV.
  - V1: 4 / 2 / 9 / 5, tức 0,09–0,43 %.
  - V2: 3 / 5 / 4 / 0, tức 0,00–0,44 %.
  - Lệnh bị từ chối không nhiều. Nhưng margin vượt equity hàng nghìn phút ⇒ trên CROSS 1x thật, sàn sẽ từ chối cả lệnh DCA của
    nền trong các phút đó. Điểm này sim không mô phỏng.
- Sim đếm toàn kỳ: ứng viên lúc sổ nền đầy 14–624/run, trong đó mở 0–17.
- **Độ nhạy theo PnL sleeve 2021H2 (X, bị bịt).**
  - Mọi leg sleeve 2021H2 đóng trước 2022 ⇒ X là một hằng số cộng vào equity từ 2022 trở đi. Khi đó
    DD %(X) = (đáy − đỉnh)/(đỉnh + X).
  - X cần để G3 lật (`p1_g3_offset_sens.csv`, median seed; equity đầu 2022 ≈ 41,8k):

    | arm | median đạt −32 % | seed tệ đạt −36 % |
    |---|---|---|
    | V0 | ≥ 8,6k | ≥ 2,9k (s21) |
    | V1 | ≥ 6,6k | ≥ 1,1k (s99) |
    | V2 | ≥ 3,4k | đã đạt |

  - U và CAGR22 cũng lệch cùng chiều: X > 0 thì U thật thấp hơn, CAGR thật thấp hơn.
  - Có dấu hiệu gián tiếp là X ≠ 0. Margin-U max toàn kỳ do sim tự đo (0,98–1,19) thấp hơn max DEV của tôi (1,03–1,21) ở 8/12 run
    (cả 8 run V0/V1), trong khi DEV nằm trong toàn kỳ. Cách giải thích khả dĩ: mẫu số của tôi thiếu X. **CHƯA kiểm (cố ý)**: muốn kiểm phải suy ngược
    ra X, tức là nhìn PnL 2021H2.

## 6. Validate

| kiểm | kết quả |
|---|---|
| Bất biến nền: lọc `book=sleeve` ⇒ md5 = B0, **cả 12 run** | PASS: a1 `dc62609b`, s7 `622b03e2`, s21 `6f15b4d7`, s99 `53fa789d`. Mọi dòng sleeve nằm sau mọi dòng nền. Số dòng sleeve = `printdone_sleeve_rows`. `n_trades` = nền + sleeve. jar/arm đúng. |
| Tái lập B0 bằng sổ nền riêng (cụm, cụm/năm, ΣPnL, stress, CAGR22, maxDD) | PASS, khớp `quarterly_x14_by_seed.csv`. s7: 2891 cụm, ΣPnL 108 906,7, CAGR22 37,872 %, maxDD −22,744 %. |
| Σ PnL quý = tổng; Σ năm = tổng (toàn danh mục + sleeve, 12 run) | PASS (lệch tuyệt đối < 1e-6) |
| Kiểm tay độc lập `indep_p1.py` (chỉ csv/datetime), V1 × s21 | PASS, lệch 0. Sleeve cụm 376/472/774/463, ΣPnL 69 966,24. Toàn danh mục cụm 963/1231/1612/1157, ΣPnL 179 131,79. |
| MTM missing | 0 ở cả 16 sổ (4 B0 + 12 sleeve) |
| Phút phẳng của sleeve (eq − số dư thực hiện) | Sau khi sửa bug pipeline (dưới): ≤ 0,004 USD |

**Bug pipeline phát hiện khi chấm (pipeline có từ trước; báo trước/sau, không sửa `research/nup/`):**
- Hiện tượng: trong `mtm_parquet.build`, leg đóng ĐÚNG 00:00 UTC ngày 1 đầu tháng (`m1 == ms`) bị loại ở cả hai phía. Tháng trước
  loại vì `m1 < me` sai; tháng sau loại vì `m1 > ms` sai. Kết quả là PnL thực hiện của leg đó không bao giờ vào eq.
- Quy mô: 3–6 leg nền/seed, 0–4 leg sleeve/run. Eq lệch một hằng số 20–144 USD, bắt đầu từ 2022-12-01.
- Con số "flat_maxabs 97,5 USD" của B0 s7 ghi trong ADDENDUM B chính là bug này, không phải "ranh giới một phút" như ADDENDUM B viết.
- **Tác động lên chấm điểm: 0.** maxDD trước/sau khi sửa trùng nhau tới 1e-9 (4 B0 + 12 danh mục), vì đáy DD (2022-05-12) nằm trước phút đầu
  tiên bị lệch. Cột `P_dd_fix`, `B0_dd_fix`, `G3_dd_fix` giữ trong CSV.
- Số chính vẫn dùng pipeline NUP như chỉ định.

## 7. Lệch thiết kế / diễn giải bổ sung (của agent)

1. Theo luật loại 2021H2, equity toàn danh mục đầu 2022 = equity B0 (thiếu X). Đây là mẫu số của DD %, U, CAGR22. Đã định lượng ở §5.
2. G2 "≥ 3/4 năm" tính trên median-seed theo năm. Đọc theo từng seed cũng cho cùng kết quả.
3. Vế U của G3 áp cho seed tệ nhất, chặt hơn median. Kết luận không đổi.
4. Quy ước N_eff:
   - Ngày tính theo +07. PnL ngày gán theo ngày đóng, nhất quán với gán kỳ. Khác S0, vốn dùng ngày UTC theo t0.
   - Đợt = các t0 liên tiếp cách nhau < 6h. "Không giao" là theo đúng định nghĩa S0.
   - Ngày/đợt chỉ lấy cụm sleeve có t0 trong DEV. Corr tính trên 1 461 ngày, ngày không có lệnh = 0.
5. Overlap đếm khi t0_sleeve < t0_nền ≤ te_sleeve, vì pha sleeve chạy cuối tick, sau nền. Chỉ đếm cụm nền có t0 trong DEV.
6. Tiết lộ:
   - Khi đọc schema, trước khi viết code chấm, tôi đã in `storage/sleeve_summary.json` của **nup3-v0-s7**. File này có trường gộp
     toàn kỳ (2021H2 + DEV): `sleeve_profit`, `sleeve_fee`, `comb_maxdd_*`. Không tách được 2021H2 từ đó.
   - Chỉ có V0 s7. Không có file nào của V2. Không dùng trường nào trong số đó để chấm.
   - Từ đó trở đi chỉ đọc các trường đếm/U.

## 8. Việc cần MASTER quyết

- G3 của V0/V1 hiện FAIL, nhưng nhạy với X (PnL sleeve 2021H2, đang bị bịt). Có 3 phương án:
  - **(a)** Giữ nguyên ⇒ NO-GO Pha 1, NUP3 dừng.
  - **(b)** Cho phép tính G3 "niêm phong" cho V0/V1 với X thật: chỉ in boolean và DD %, không in X/PnL 2021H2. Rủi ro: V2 gần như là
    tập con của V0 (cùng ứng viên q2), nên X của V0/V1 vẫn rò thông tin về kỳ xác nhận của V2.
  - **(c)** Chấp nhận rằng V2 đã trượt G1 (không phụ thuộc X) ⇒ kỳ 2021H2 không còn cần bảo vệ cho NUP3 ⇒ mở 2021H2 cho V0/V1.
- Ngoài ra, kể cả khi G3 lật, Calmar vẫn giảm (1,72 → ~1,4), DD dồn đúng vào cú sập, và margin@entry vượt equity. Đây là các rủi ro
  live mà G1–G3 không bắt được.
