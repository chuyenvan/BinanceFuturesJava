# RESULT_K32_CONFIRM — xác nhận arm `l2-k32` (K32, pct 0,999915, skipFull ON) trên seed 7/21

Pre-reg: docs/prereg/PREREG_K32_CONFIRM.md (**39729383**, commit trước khi đẩy kernel). Thước: research/analysis/gkf_rescore.py
(1f9e0e2f) qua research/analysis/k32_confirm.py; JSON: docs/result/k32_confirm.json. k = 1, CI95 raw (block-10d, NREP 2000, seed 20260905).

## Kết luận: **NO-GO** — giữ nền K24 (pct 0,999950829, skipFull ON)
Trượt 4/5 điều kiện (chỉ đạt maxDD ≤ 40%). Seed 7 trượt cả bản base (ΔPnL −406) lẫn stress (ΔPnL −10,8k, Calmar stress 0,72× nền);
seed 21 đạt ΔPnL base/stress > 0 nhưng 1 seed không đủ. So với kỳ vọng khai trước: mean ΔCAGR22 base +3,56pp (vượt nhẹ
dải +0…+3), stress +0,70pp (trong dải −1…+1); không CI nào loại 0. Lợi CAGR của K32 bị phí sập ăn mất phần lớn (ΔCAGR22 base→stress
giảm 2,6–3,2pp/seed), đổi lại maxDD22 base sâu hơn 2,5–4,1pp và UW22 gấp 1,4–2,1×.

## Parity
| seed | arm | md5 printDone | n | eq | jar | pred_md5_used | pass gate | skipFull | parity |
|---|---|---|---|---|---|---|---|---|---|
| S7 | k32c-s7 | 25d1f41207e9b5e9fa5727d62045681a | 7382 | 136571 | 20d412e8 | b737fb6d | 7046 | 6308 | PASS |
| S21 | k32c-s21 | 641479a9a9e6ac97c0861b099dd112a7 | 7332 | 156934 | 20d412e8 | 0b541d22 | 7000 | 6741 | PASS |
| S42 | gkf-l2-k32 | f2a4503ffc77b241df40246cd352e19d | 7489 | 156807 | 20d412e8 | gốc bund | 7154 | 5341 | PASS |
| nền | gqsf-s7 | eca3d5da69c9755ada80b34559508c4e | 3557 | 139828 | 0944841c | — | — | — | ok |
| nền | gqsf-s21 | c3b73549898d6216d85321df7cc241f3 | 3550 | 141766 | 0944841c | — | — | — | ok |
| nền | gqsf-a1 | ad26fd55f0bb5db32038ec8b357cf8e7 | 3541 | 146078 | 0944841c | — | — | — | ok |

- Tất cả check của gkf_rescore (jar 20d412e8, ok, date_last 20251230, mapper ≥ 800, TOPK=32 + log, pct 0.999915000 + log f32
  `BAT: mode=ratio pct=0.99991500`, `SKIP_WHEN_FULL=ON`, B0OV, dòng `md5 verified` khớp nền cùng seed, pred md5) = PASS.
- Lag nến quyết định = 0 ở cả 3 nền (khớp entry==close 100%); no_bar = 0 mọi run.
- Tự kiểm thước: seed 42 tái tạo đúng AUDIT_GKF_PHASE1_20261007.json (gkf-l2-k32, gkf-nen; base + stress) và nền
  gqsf-s7/gqsf-s21 khớp docs/result/gate_skipfull.json ON_S7/ON_S21 (8 trường): 0 lệch.
- Tất định: kernel `gkf2-l2k32-s7` / `gkf2-l2k32-s21` do claw chạy song song (cùng jar/override/pred) cho md5 trùng
  k32c-s7 / k32c-s21 ⇒ sim lặp lại bit-exact.
- Giới hạn: nền seed 7/21 chạy jar sim-jar-gqsf (0944841c), arm jar sim-jar-shadow2 (20d412e8); tương đương đã kiểm ở seed 42
  (gkf-nen md5 == gqsf-a1 == ad26fd55), chưa kiểm trực tiếp ở seed 7/21.

## Bảng 3 seed (MTM phút; b = base phí legacy as-is, s = stress COST_TRUTH +1,675%/chân vào nến 1m ≤ −1%)
| seed | run | md5 | n | n/năm | CAGR22 b→s | maxDD22 b→s | maxDD all b | Calmar22 b→s | UW22 | 0h% | sập% |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S7 | k32c-s7 | 25d1f412 | 7382 | 1588 | 37,27→29,68 | -26,71→-31,72 | -30,23 | 1,395→0,936 | 244 | 45,7 | 35,5 |
| S7 | gqsf-s7 | eca3d5da | 3557 | 741 | 35,64→31,20 | -22,75→-24,15 | -22,75 | 1,566→1,292 | 116 | 44,1 | 42,3 |
| S21 | k32c-s21 | 641479a9 | 7332 | 1571 | 41,35→34,34 | -27,18→-30,35 | -31,43 | 1,521→1,131 | 189 | 43,6 | 35,8 |
| S21 | gqsf-s21 | c3b73549 | 3550 | 742 | 35,88→31,43 | -24,67→-26,19 | -24,67 | 1,454→1,200 | 136 | 43,7 | 42,4 |
| S42 | gkf-l2-k32 | f2a4503f | 7489 | 1602 | 41,05→33,88 | -26,34→-29,34 | -30,05 | 1,558→1,155 | 244 | 43,5 | 35,8 |
| S42 | gqsf-a1 | ad26fd55 | 3541 | 736 | 36,90→32,53 | -22,21→-23,77 | -22,21 | 1,662→1,369 | 117 | 43,6 | 41,6 |

## Δ ghép cặp theo seed (arm − nền cùng seed): điểm [CI95 raw] {inflate k=1 ≡ raw}
| seed | bản | ΔPnL22–25 [CI raw] | ΔCAGR22 [CI raw] | Cal×nền | ΔCAGR23 | ΔROI 22/23/24/25 |
|---|---|---|---|---|---|---|
| S7 | base | -406 [-40849; +37502] {-40849; +37502} | +1,64 [-11,08; +17,81] {-11,08; +17,81} | 0,891 | +4,73 | -4,92 / +24,66 / +8,65 / -13,49 |
| S7 | stress | -10834 [-49534; +26119] {-49534; +26119} | -1,52 [-15,08; +16,27] {-15,08; +16,27} | 0,724 | +1,26 | -7,24 / +20,46 / +5,88 / -17,28 |
| S21 | base | +17446 [-24921; +60699] {-24921; +60699} | +5,48 [-7,40; +21,09] {-7,40; +21,09} | 1,046 | +7,67 | +0,74 / +22,98 / +9,14 / -5,12 |
| S21 | stress | +4739 [-36887; +44980] {-36887; +44980} | +2,91 [-11,41; +20,04] {-11,41; +20,04} | 0,943 | +4,83 | -1,10 / +19,03 / +6,72 / -7,68 |
| S42 | base | +12689 [-31283; +56261] {-31283; +56261} | +4,14 [-8,83; +20,32] {-8,83; +20,32} | 0,938 | +7,50 | -2,98 / +25,82 / +0,81 / -0,03 |
| S42 | stress | -157 [-42781; +41685] {-42781; +41685} | +1,35 [-13,05; +19,07] {-13,05; +19,07} | 0,844 | +4,50 | -5,13 / +20,90 / -2,59 / -1,30 |

mean ΔROI stress S7/S21: 2022 -4,17 / 2023 +19,75 / 2024 +6,30 / 2025 -12,48
mean ΔCAGR22 S7/S21: base +3,56, stress +0,70
Luật: c1_dPnL_stress_gt0=✗, c2_cal22_stress_ge090=✗, c3_maxDD_le40=✓, c4_mean_dROI_stress_3of4=✗, c5_dPnL_base_gt0=✗ ⇒ **NO-GO**

## Luật GO (quyết trên seed 7 + 21)
| # | điều kiện | S7 | S21 | kết quả |
|---|---|---|---|---|
| 1 | ΔPnL22–25 stress > 0 cả 2 seed | −10 834 | +4 739 | ✗ |
| 2 | Calmar22 stress ≥ 0,90× nền cả 2 seed | 0,724 | 0,943 | ✗ |
| 3 | maxDD MTM ≥ −40% (toàn kỳ + 22+, base + stress) | -33,69 (tệ nhất) | -34,81 (tệ nhất) | ✓ |
| 4 | mean ΔROI stress ≥ 0 ở ≥ 3/4 năm | 2022 −4,17 / 2023 +19,75 / 2024 +6,30 / 2025 −12,48 | 2/4 | ✗ |
| 5 | ΔPnL22–25 base > 0 cả 2 seed | −406 | +17 446 | ✗ |

## Diễn giải / rủi ro
- K32 + pct 0,999915 gấp ~2,1× số lệnh (≈1 570–1 600/năm vs ≈740); phần lợi thêm tập trung ở 2023
  (ΔROI +19…+26pp mọi seed, base và stress), còn 2022 và 2025 chủ yếu âm (2025 stress −1,3…−17,3pp) ⇒ phụ thuộc chế độ thị trường, không ổn định theo năm.
- Tỷ lệ chân vào nến sập thấp hơn nền (~35,5–35,8% vs ~42%) nhưng số chân gấp đôi ⇒ tổng phạt stress 22–25 ~31–34k vs ~21k.
- Stress là xấp xỉ bậc 1 post-hoc (không mô phỏng lại đường đi) — cùng thước với GKF Phase 1, không đổi kết luận vì seed 7
  trượt cả ở bản base.
- Seed 42 (nhiễm chọn lọc) cũng trượt luật 1, 2, 4 ở bản stress — nhất quán với seed 7/21.
- Mẫu xác nhận chỉ 2 seed; CI ΔPnL rộng ±40k ⇒ không đủ lực phát hiện hiệu ứng nhỏ; NO-GO là theo luật đã khoá, không phải
  bằng chứng arm tệ hơn có ý nghĩa thống kê.
