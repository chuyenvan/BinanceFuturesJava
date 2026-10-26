# NUP — TĂNG SỐ LỆNH cho gói go-live X14 — KẾT QUẢ

Ngày 2026-10-26. Prereg `docs/prereg/PREREG_NUP.md` (commit **fcdf04f2**, sha256
`e1236f48…`), ADDENDUM A (hiệu chuẩn A6) **20428d2e**, ADDENDUM B (nguồn giá MTM)
**1ce1962e**, ADDENDUM C (sửa hiệu năng A7) **301e32f8**.
Code chấm `research/nup/` (`run.py`, `mtm_parquet.py`, `score.py`, `summarize.py`,
`independent_check.py`). Số máy `docs/result/nup/{runs.csv,arms.csv,frontier.csv,match.csv,score.json}`.

## VERDICT: **NO-GO** — không arm nào qua đủ G1–G4.

- **Pha 1:** chỉ **A2** qua G1–G3 (cụm ×2,56; ΣPnL ×0,927; stress ×0,863; maxDD −27,8 %).
  A1, A4, A6 qua G1/G3 nhưng trượt G2; A3 trượt G1 rất sát (×1,28 < 1,30); A5 là **no-op**
  (byte-identical B0); A7 **không có số** (xem §6).
- **Pha 2 (A2):** DEV 8 seed **qua G1–G3** (cụm ×2,574; ΣPnL ×0,953; stress ×0,886; maxDD
  median −27,68 %, tệ nhất −27,96 %). **HO 2026 trượt G4 nặng**: ΣPnL median **0,543× B0**
  (8 seed: 0,407 / 0,585 / 0,726 / 0,501 / 0,461 / 0,454 / 1,383 / 1,198), maxDD realized
  −13,65 % ở seed tệ nhất (MTM sẽ sâu hơn). 6/8 seed < 0,73 ⇒ G4 FAIL.
- Kết luận theo luật: **NO-GO**. Frontier để owner tự cân ở §4. A2 là điểm tốt nhất trên DEV
  nhưng đánh đổi sang HO quá lớn — đúng cảnh báo N_DEEP: lệnh mới ROI thấp, tương quan cao,
  không đa dạng hoá.

## 1. Pha 1 — 7 arm × 4 seed DEV (A1–A6; A7 không có số)

| Arm | cụm/năm | ×B0 | ΣPnL | ×B0 | stress ×B0 | CAGR22 | maxDD med / tệ | Calmar | U max | G1 | G2 | G3 | KL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 pct 0.99990 | 1 330,8 | 1,839 | 89 413 | 0,789 | 0,748 | 34,67 | −25,86 / −26,78 | 1,334 | 65,0 | ✓ | ✗ | ✓ | TRƯỢT |
| **A2 pct 0.99985** | **1 855,6** | **2,564** | **110 786** | **0,927** | **0,863** | **38,30** | **−27,79 / −27,96** | **1,375** | **68,4** | ✓ | ✓ | ✓ | **QUA** |
| A3 K32 | 924,3 | 1,280 | 118 158 | 1,023 | 1,016 | 40,31 | −25,29 / −26,22 | 1,571 | 65,7 | ✗ | ✓ | ✓ | TRƯỢT |
| A4 K32+pct | 1 717,8 | 2,370 | 99 247 | 0,886 | 0,838 | 36,98 | −27,00 / −27,21 | 1,369 | 67,4 | ✓ | ✗ | ✓ | TRƯỢT |
| A5 dyn 1.30 | 721,1 | 1,000 | 112 467 | 1,000 | 1,000 | 38,56 | −22,47 / −24,66 | 1,716 | 61,5 | ✗ | ✓ | ✓ | **NO-OP** |
| A6 A4×size0,67 | 1 720,1 | 2,378 | 63 037 | 0,557 | 0,532 | 27,77 | −23,07 / −23,34 | 1,204 | 59,2 | ✓ | ✗ | ✓ | TRƯỢT |
| A7 TIER2 | — | — | — | — | — | — | — | — | — | — | — | — | **KHÔNG CÓ SỐ** |

G1 yêu cầu cụm/năm ≥1,30× và **mỗi năm** ≥1,15×. A1 và A2 đạt mọi năm (A2: 2,08 / 2,34 / 2,86 /
2,83). A3 đạt từng năm 1,27–1,29 nhưng tổng 1,28 < 1,30 ⇒ trượt. A5 = B0 tuyệt đối (md5 trùng
cả 4 seed) nên 1,00.

G2: A2 4/4 seed có ΣPnL ≥0,85×B0; A1 1/4; A4 2/4; A6 0/4.

## 2. Pha 2 — A2 (arm duy nhất qua Pha 1)

### 2.1 DEV 8 seed (2022–25)

| chỉ số | A2 | B0 | tỷ lệ |
|---|---|---|---|
| cụm/năm | 1 853,9 | 720,5 | **2,574** |
| ΣPnL | 112 525 | 118 106 | **0,953** |
| ΣPnL_stress (20 bps) | 99 373 | 112 160 | **0,886** |
| CAGR22 | 38,85 % | 39,06 % | 0,995 |
| maxDD MTM median | −27,68 % | −22,83 % | — |
| maxDD tệ nhất | −27,96 % | −24,66 % | — |
| Calmar | 1,398 | 1,715 | 0,815 |
| U max | 68,3 % | 60,8 % | — |
| vị thế đồng thời max | 118 | 69 | — |
| seed ΣPnL ≥0,85×B0 | 7/8 | — | — |

G1 ✓ (2,574; các năm 2,08 / 2,34 / 2,86 / 2,83), G2 ✓ (0,953; 7/8; stress 0,886), G3 ✓
(−27,68; tệ −27,96). **Qua Pha 2 DEV.**

### 2.2 HO 2026 — G4 FAIL

8 seed đã hoàn tất (CSV `ho_a2.csv`):

| seed | A2 ΣPnL | cụm | B0 ΣPnL | B0 cụm | ×PnL | maxDD realized |
|---|---|---|---|---|---|---|
| 42 | 7 723 | 1 053 | 18 996 | 398 | 0,407 | −13,65 % |
| 7 | 9 702 | 1 085 | 16 596 | 476 | 0,585 | −11,60 % |
| 13 | 15 348 | 977 | 21 147 | 441 | 0,726 | −10,60 % |
| 21 | 10 049 | 1 064 | 20 057 | 468 | 0,501 | −10,74 % |
| 99 | 10 461 | 1 054 | 22 674 | 414 | 0,461 | −9,06 % |
| 123 | 7 822 | 899 | 17 216 | 435 | 0,454 | −11,55 % |
| 777 | 17 837 | 1 026 | 12 894 | 441 | 1,383 | −6,17 % |
| 2024 | 18 280 | 957 | 15 264 | 473 | 1,198 | −10,79 % |
| **median** | **10 255** | **1 040** | **18 106** | **442** | **0,543** | **−10,77 %** |

- **G4 ΣPnL:** median 0,543 < 0,80 ⇒ **FAIL**. 6/8 seed <0,73; hai seed 777/2024 >1,0 nhưng
  không kéo được median. **G4 DD:** median −10,77 % (đạt −12 %) nhưng seed 42 −13,65 %; MTM phút
  sẽ sâu hơn realized. Dù DD đạt, ΣPnL đã fail ⇒ **G4 FAIL**.
- **G4 maxDD:** realized (chưa MTM) đã −13,65 % ở seed 42, vượt ngưỡng −12 %; MTM phút sẽ sâu hơn.
  Không thể tính MTM đầy đủ cho HO A2: cache `ecm_px` thiếu 370 file tháng 2026 (10,4 % leg-minutes),
  và luật cấm tải kline 2026 về Oracle. Vì G4 ΣPnL đã fail, không cần DD để kết luận.

## 3. Vì sao thất bại — chi phí cơ hội (match ±1 phút, DEV 2022–25, median qua seed)

| Arm | chung | mới | mất | ROI chung | ROI mới | ROI mất |
|---|---|---|---|---|---|---|
| A1 | 1 335 | 4 098 | 1 630 | 2,99 % | **1,67 %** | 3,93 % |
| A2 | 993 | 6 524 | 1 946 | 3,67 % | **1,41 %** | 3,48 % |
| A3 | 2 453 | 1 349 | 516 | 3,67 % | 2,91 % | 3,64 % |
| A4 | 1 060 | 5 925 | 1 890 | 2,93 % | **1,72 %** | 3,77 % |
| A6 | 1 094 | 5 914 | 1 855 | 3,38 % | **1,85 %** | 3,75 % |

Lệnh MỚI có ROI/lệnh thấp hơn lệnh B0 bị đẩy ra 1,8–2,5 lần. A3 (K32, gate giữ nguyên) là ngoại lệ:
lệnh mới ROI 2,91 % gần lệnh mất 3,64 %, nhưng chỉ thêm 1,28× cụm — không đủ G1. A2 thêm 2,56× cụm
nhưng gần như toàn bộ là lệnh chất lượng thấp; HO 2026 còn tệ hơn (0,50× PnL).

## 4. Frontier (DEV; A2 dùng 8 seed, còn lại 4 seed)

| Arm | cụm/năm | ×B0 | ΣPnL | ×B0 | stress×B0 | CAGR22 | maxDD med | Calmar | U max |
|---|---|---|---|---|---|---|---|---|---|
| A3 K32 | 924 | 1,280 | 118 158 | 1,023 | 1,016 | 40,31 | −25,29 | 1,571 | 65,7 |
| A5 no-op | 721 | 1,000 | 112 467 | 1,000 | 1,000 | 38,56 | −22,47 | 1,716 | 61,5 |
| A2 pct .99985 | 1 854 | 2,574 | 112 525 | 0,953 | 0,886 | 38,85 | −27,68 | 1,398 | 68,3 |
| A1 pct .99990 | 1 331 | 1,839 | 89 413 | 0,789 | 0,748 | 34,67 | −25,86 | 1,334 | 65,0 |
| A4 K32+pct | 1 718 | 2,370 | 99 247 | 0,886 | 0,838 | 36,98 | −27,00 | 1,369 | 67,4 |
| A6 A4×0,67 | 1 720 | 2,378 | 63 037 | 0,557 | 0,532 | 27,77 | −23,07 | 1,204 | 59,2 |

Nếu owner chỉ quan tâm số lệnh và chấp nhận PnL giảm: A2 là điểm đánh đổi tốt nhất trên DEV
(2,57× cụm, −4,7 % PnL, DD −27,7 %). Nhưng HO 2026 nói không: cùng cơ chế cho 0,50× PnL.

## 5. A5 là NO-OP (phát hiện thiết kế)

`SIM_GATE_DYN_SCALE` **triệt tiêu** khi gate rolling ratio bật: `r = p15/(factor·gs)` và buffer
phân vị chính là `r`, nên ngưỡng `q·factor·gs` không đổi khi đổi `gs`. Kết quả: A5 md5 printDone
**trùng B0 cả 4 seed** (a1/s7/s21/s99), chỉ khác 1 key trong `prof_run.properties`. Arm hợp lệ
nhưng không tác dụng; không dùng để kết luận gì về "nới ngưỡng động".

## 6. A7 — TIER2: code đúng, sim không xong trong 7200 s

- Byte-identical khi TẮT: jar đầu `66740305` chạy B0 a1 = `dc62609b…` (PASS). Jar sửa hiệu năng
  `ce4bcc17` chạy lại B0 a1 = `dc62609b…` (PASS, `nup-a7off2-a1`).
- Lần chạy A7 bật (jar `66740305`, commit `39c98525`): Kaggle kill ở 7200 s, `java_rc=-9`,
  `n_trades=0`, `date_last=20210823` — chỉ 54 ngày/2 h. Nguyên nhân: `tier2Pass` gọi quickselect
  O(m) trên buffer ~2,7 triệu mẫu cho **mỗi** candidate bị reject (~20/tick).
- Đã sửa (ADDENDUM C, commit code **a221bf80**): tính q1/q2 **một lần mỗi giờ** trong
  `addAndQuery2`, `tier2Pass` còn O(1). Unit test 8/8 PASS; jar `ce4bcc17`.
- Do cửa sổ Kaggle còn lại, A7 **chưa chạy lại đủ 4 seed** sau khi sửa ⇒ **A7 KHÔNG CÓ SỐ**,
  không dùng trong quyết định. Không được phép suy đoán A7 từ code.

## 7. Validate

- **V1:** A1–A6: 24/24 run `java_rc=1`, `ok=true`, jar `cc0f9d11`; `prof_run` khác B0 **đúng**
  tập key của arm (A1/A2: pct; A3: K; A4: K+pct; A5: dyn; A6: K+pct+F_BASE). PASS.
  A7: run bật fail (`java_rc=-9`, jar 66740305); off-parity 2/2 PASS.
- **V2:** ΣPnL theo quý 2022–25 = Σ giai đoạn, max |Δ| = **2,9e-11 USD**. PASS.
- **V3:** B0 8 seed chấm lại bằng nguồn giá parquet: n_cl **2 878 median**, ΣPnL **113 410**,
  CAGR22 median **39,027** (công bố 39,06), maxDD **−22,833** (công bố −22,83), missing = 0.
  PASS.
- **V4:** `independent_check.py nup-a2-s13` (chỉ csv/datetime): n_cl 7 398, n_leg 7 508,
  n_entry 1 775, ΣPnL 116 478,81 — lệch pipeline **0/0/0/1,2e-10**. PASS.
- **V5:** A6 median notional leg0 A6/A4 = **0,6444** (a1 0,6432; s7 0,6590; s21 0,6457;
  s99 0,6395) ∈ [0,64; 0,70]. PASS (sát biên dưới). A7 tier2: **không có số** (N/A).

## 8. Lệch thiết kế / sự cố (đã ghi ADDENDUM)

1. **Nguồn giá MTM DEV** (ADDENDUM B): `~/kaggle_data_hpo` (ticker bins) đã bị xoá khỏi Oracle;
   dùng kline1m parquet 2021–2025, tái tạo đúng công thức legacy + PnL leg đóng 00:00 UTC.
   Kiểm chứng B0 8 seed khớp số công bố (CAGR 39,027 vs 39,06; DD −22,833).
2. **A6 size** (ADDENDUM A): `SIM_F_BASE=0,007495` hiệu chuẩn để notional leg0 = 0,67×A4
   (không phải F_BASE×0,67), theo công thức bisection trên U của A4 a1/s7; không dùng PnL.
3. **A7** (ADDENDUM C): bug hiệu năng, đã sửa; chưa có số 4 seed.
4. **Pha 2 A2** bắt đầu ngay sau khi A2 qua Pha 1, chạy song song với đuôi A7/A6; không đổi
   tiêu chí chọn (A2 là arm duy nhất qua G1–G3; A3 trượt G1).
5. **A5 no-op** như §5 — không phải lỗi thi hành, là hệ quả toán học của gate ratio.
6. HO MTM đầy đủ không chạy được: cache `ecm_px` thiếu 370 file 2026 (10,4 % leg-minutes), cấm
   tải kline 2026 về Oracle. G4 dùng ΣPnL realized + maxDD realized; G4 ΣPnL đã fail rõ (6/8 seed <0,73, median 0,543).

## 9. Trial ledger / giới hạn

- Họ NUP = **7 arm**. Phase 1 = A1–A6 ×4 seed + A7 (không có số). Phase 2 = A2 ×8 DEV + 8 HO
  (8 HO xong). DEV đã bị nhìn nhiều lần; X14 là in-sample.
- Sim không mô hình trượt giá; DD/ROI là cận lạc quan. HO 2026 chỉ 1 đợt sập.
- A6 size sát biên dưới band (0,6444) — nếu chạy lại có thể rơi <0,64; đây là arm fail G2 nên
  không ảnh hưởng verdict.

## 10. Vận hành

- Kernel đã push: xem `docs/result/nup/kernels.txt`.
- Trung gian `~/claude_master/nup_wk/` (dataset jar 100 MB, eq npz, state, log) sẽ xoá sau khi
  lưu kết quả; `~/src_nup/dist/sim.jar` (100 MB) xoá; giữ source branch `research/nup-tier2`.
- Đĩa Oracle: ~18,5 GB trống tại thời điểm chốt.
