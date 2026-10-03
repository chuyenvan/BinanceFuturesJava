# REAUDIT_FLAT3_20261003 — FLAT3 có thật là cấu hình thoát tốt nhất không? (audit đối kháng, 0-sim)

- **Ngày:** 2026-10-03 (GMT+7). **Vai:** auditor đối kháng, CHỈ ĐỌC. 0 sim mới, 0 Kaggle, 0 Java, 0 chạm 242/shadow, 0 dữ liệu 2026.
- **Script:** `research/analysis/reaudit_flat3.py` (0-sim, đọc printDone + `logs/sim.out` của artifact Kaggle có sẵn; MTM phút lấy từ cache `run_mtm` các vòng trước + `docs/result/exit_time_b0.json`). **JSON:** `docs/audit/REAUDIT_FLAT3_20261003.json`.
- **Thước:** (i) ΔPnL ghép cặp theo lệnh (khớp `sym|start|level`, size-neutral = Δprofit × notional REF, lệnh lệch ± PnL của chính nó; logic y hệt `long_levers_paired_ruler.py`), CI block-72h theo giờ vào, NREP 2000, seed 20260905, **inflate quanh điểm × √(2 ln 11) = 2,19** (k = 11 arm khác FLAT3); (ii) MTM **ngày** (b+unP) paired moving-block 10 ngày, cùng chỉ số khối mọi arm, cùng inflate; (iii) theo năm; (iv) phân phối ROI. **Mọi thứ ở đây là hậu kiểm trên DEV đã dùng nhiều lần — KHÔNG dùng để chọn arm mới.**

## KẾT LUẬN (rủi ro trước)

1. **VERDICT: FLAT3 = "ngang nhất + đơn giản nhất" trong họ trailing, KHÔNG phải "tốt nhất".** Không arm nào hơn FLAT3 ngoài CI (inflate) trên bất kỳ thước nào; nhưng FLAT3 cũng không đứng đầu mọi thước: theo ΔPnL ghép cặp **T0 (G2) hơn FLAT3 về điểm +1,06k** và PROP50 +0,71k; theo Calmar (MTM phút và MTM ngày) **LAD hơn FLAT3 về điểm** (1,949 vs 1,940; 3,48 vs 3,43). FLAT3 đứng **top-3 trên mọi thước, top-1 ở CAGR/ΣPnL/UW** — không arm trailing nào trội FLAT3 trên tất cả các thước, cũng không arm nào hơn FLAT3 ở **mọi năm** 2022–25.
2. **LỖI-NHỎ (đổi diễn giải, không đổi verdict): dấu sai trong `AUDIT_LONG_LEVERS_20261002` §KẾT LUẬN 3 — "FLAT3 − T0 = +1,06k".** Script `long_levers_paired_ruler.py` tính **arm − B0** (B0 = FLAT3) ⇒ hàng T0 +1,06k nghĩa là **T0 − FLAT3 = +1,06k** (T0 hơn về điểm). Tôi tái lập byte-số: T0−FLAT3 = +1 064, CI raw [−3 380; +6 216] (khớp JSON audit). Phân rã: phần lệnh **khớp** FLAT3 hơn T0 (+1,58k), phần **lệch tập lệnh** (182/174 lệnh) kéo ngược −2,64k. Câu "kết luận chọn FLAT3 đứng vững và nay có nghĩa" là **nói quá**: đúng phải là "FLAT3 ≈ T0, khác biệt ±1k nằm trong nhiễu ±5k". Brief vòng này chép lại dấu sai.
3. **FLAT3 KHÔNG post-hoc theo nghĩa hẹp** (có trong `PREREG_TRAIL2_G2.md`, commit `3969bc84` 19:34:19, md5 `9f791a25` = khai trong RESULT; kernel ra 20:20; result `5b32f517` 20:29; 0 arm thêm sau khi thấy số ở cả 2 vòng). **Nhưng là thiết kế thích nghi**: TRAIL2 được viết **43 phút sau** khi thấy kết quả TRAIL_G2 (`fc4c4113` 18:51), mỗi vòng chỉ inflate k=4 (thực tế 8 arm trailing qua 2 vòng), và được **chọn theo điểm** của thước vô lực (ΔCalmar block-72h ±25…±55) ⇒ winner's curse nhẹ. Luật chọn trong pre-reg ("Calmar_MTM điểm cao nhất nhóm pure; hoà → FLAT") **được tuân thủ đúng**.
4. **Cấu hình thoát "tốt nhất về điểm" đã từng chạy KHÔNG phải FLAT3 mà là FLAT3 + time-stop 72h (EXIT_TIME_B0 A1/A2):** hơn FLAT3 về điểm ở **mọi** thước tổng (ΔPnL ghép cặp +1,8k/+1,2k; ΔCAGR ngày +2,0/+1,8 pp; ΔCalmar ngày +0,44/+0,43, P>0 = 0,85/0,86; Calmar_MTM phút 2,33/2,32 vs 1,94; UW 71/84 vs 87) — nhưng CI chứa 0 rộng và **2023, 2024 âm** ⇒ NO-GO đúng luật đã khoá; ~80 % chênh ΣPnL là trôi size. Không phải "bị bỏ sót", là **bị bác đúng luật**.
5. **Thước MTM ngày ghép cặp (block-10d) có lực hơn hẳn thước ΔCalmar block-72h đã dùng**: nửa-độ-rộng ΔCalmar ngày (raw) ≈ 0,2–0,35 trên Calmar ≈ 3,4 (6–10 %) so với ±25…±100 điểm. Trên thước này P(arm − FLAT3 > 0) của FLAT5 / GV3 / PROP30 chỉ 0,05 / 0,04 / 0,06 (FLAT3 hơn ở mức raw sát biên, KHÔNG qua inflate) ⇒ **đường cong theo gap phẳng-tới-giảm hai phía quanh 3 pp**; không có tín hiệu "nới hơn" hay "siết hơn" tốt hơn.
6. **Vùng chưa phủ (§3) không có ô nào có kỳ vọng vượt MDE**: MDE80 của thước ghép cặp ở inflate k=11 ≈ 3,1 × nửa-độ-rộng ≈ **7–17k** (7–17 % ΣPnL), mọi ô chưa chạy đều có bằng chứng gián tiếp ≤ ±2k hoặc âm ⇒ **KHÔNG đề xuất pre-reg mới** (đóng trục exit-trailing trên DEV).
7. **Live: FLAT3 trên 242/shadow CHƯA đo được** (0 lệnh; gate warm-up tới ~10-07). Công thức gap khớp (chung `TradeUtils.trailFromCap`, key 1,0/0,03/0,03 từ 10-01), **nhưng sổ giấy `ShadowBookC3` lệch sim ở 4 điểm cơ chế** (đỉnh/arm theo giá snapshot thay vì HIGH 1m, khớp đúng SL không haircut open, time-stop tại giá hiện tại, không phí/funding) — gap phẳng 3 pp là dạng **nhạy wick nhất** ⇒ parity exit phải đo forward, chưa thể giả định.

## 1. Lưới đã chạy trên CÙNG nền entry G2 (jar `sim-jar-gdv2` 7368be46, DEV 2021-07-01→2025-12-30) — mục 1: **ĐÚNG** (đủ, khớp pre-reg)

Nguồn số: script này (tính lại từ artifact). CAGR từ CAP0 35 000; maxDD/UW MTM-phút = cache `run_mtm` (đã công bố); Calmar_d = CAGR / |maxDD MTM ngày (b+unP)|; SL% = tỉ lệ `STOP_LOSS_DONE`; TS = time-stop (giữ ≥167h).

| arm | vòng (pre-reg) | cấu hình | md5 printDone | n | ΣPnL | CAGR % | maxDD MTM-phút % | UW (ngày) | Calmar_MTM | maxDD ngày % | Calmar_d | SL % | TS n / ΣPnL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **FLAT3 (B0)** | TRAIL2 | arm 7, gap phẳng 3 pp | `650c386f` | 2 517 | 96 909 | **34,31** | −17,68 | **87** | 1,940 | −10,02 | 3,425 | 14,30 | 339 / −55 914 |
| T0 (G2) | TRAIL+TRAIL2 | arm 7, min(0,5p, 8 % / 3 % theo pNoPump) | `853aaa08` | 2 509 | 96 375 | 34,18 | −17,99 | 129 | 1,900 | −10,55 | 3,241 | 14,15 | 334 / −52 862 |
| A5 | TRAIL | arm 5 + gap T0 | `655dd46b` | 2 564 | 74 826 | 28,95 | −17,18 | 129 | 1,685 | −10,46 | 2,768 | 8,50 | 202 / −31 595 |
| GV3 | TRAIL | arm 7, min(0,3p, 8/3 %) | `c2b4691e` | 2 501 | 92 837 | 33,37 | −17,50 | 87 | 1,907 | −10,32 | 3,233 | 14,43 | 337 / −54 552 |
| LAD | TRAIL | arm 7, ladder 2/4/8 pp @5/10/20 % | `adfebe0c` | 2 494 | 95 178 | 33,91 | −17,40 | 101 | **1,949** | **−9,74** | **3,483** | 14,27 | 335 / −53 274 |
| A5LAD | TRAIL | arm 5 + ladder | `e4083e29` | 2 583 | 78 074 | 29,78 | −16,74 | 106 | 1,779 | −9,98 | 2,983 | 8,44 | 202 / −31 154 |
| PROP50 | TRAIL2 | arm 7, gap 0,5p không trần | `0f685f7f` | 2 488 | 96 839 | 34,29 | −18,66 | 138 | 1,837 | −11,37 | 3,017 | 14,43 | 338 / −55 815 |
| PROP30 | TRAIL2 | arm 7, gap 0,3p không trần | `3fd38fb9` | 2 503 | 92 525 | 33,30 | −17,57 | 87 | 1,895 | −10,40 | 3,203 | 14,42 | 337 / −54 264 |
| FLAT5 | TRAIL2 | arm 7, gap phẳng 5 pp | `e252d50c` | 2 491 | 94 372 | 33,73 | −18,04 | 139 | 1,869 | −11,23 | 3,004 | 14,41 | 336 / −53 855 |
| HTD1 | HOLDTODIE | FLAT3 + **bỏ** time-stop | `b00f344f` | 2 314 | 3 426 | 2,18 | −28,15 | 1 472 | 0,077 | −26,84 | 0,081 | 0,35 | 7 / −1 533 |
| ET_A1 | EXIT_TIME_B0 | FLAT3 + time-stop **72h** | `ff434051` | 2 540 | 105 807 | 36,27 | −15,56 | 71 | 2,331 | −9,37 | 3,869 | 19,06 | (cắt 72h) |
| ET_A2 | EXIT_TIME_B0 | FLAT3 + cond-exit 72h × MFE<5 % | `7f585b7f` | 2 527 | 105 009 | 36,10 | −15,56 | 84 | 2,320 | −9,37 | 3,852 | 16,78 | 120 / −19 409 |

- Parity: `trail2-g2-flat3` = `de-p1` = `htd-h0` = `exit-time-p0` = `flat3-cp-p0` = `g2flat3-val` (md5 `650c386f`); `selab-p0/b0ref*` `ff3ce513` (ảnh Kaggle mới, giá trị trùng — đã kiểm ở SELECTOR_ABLATION). T0: `trail-g2-t0` = `trail2-g2-t0` = `gdv2-g2` (`853aaa08`).
- Pre-reg ↔ result: TRAIL_G2 5/5 arm, TRAIL2_G2 5/5 arm, **0 arm thêm**; md5 pre-reg khớp RESULT (`5fc4c485`, `9f791a25`); thứ tự thời gian: prereg 18:10 → output 18:42 → result 18:51 → **prereg TRAIL2 19:34** → output 20:20 → result 20:29 (29-09).
- `flat3-cp-p1/p2` (crash-penalty) KHÔNG phải arm exit (đổi giá khớp) — không đưa vào so sánh.
- Vòng trailing cũ trên nền KHÁC (T170, n≈1 089, thước rate): TRAIL_HINGE (cap 5/12, weak-thr 0,17), TRAIL_LADDER (3 biến thể), TRAIL_CAP_1030 (10/30), GIVEBACK_RATIO (1/2/5 trên KEEPLEG0 — ratio 1 = "trần phẳng 3/8"), PEAK_CLOSE, ARM3, SL_7_TO_3, CLOSE_BIGGAP — **tất cả NULL theo thước rate** (thước lệch/vô lực, xem AUDIT_LONG_LEVERS §3); không ghép cặp được với B0 (khác entry) ⇒ chỉ là bằng chứng hướng.
- Tiểu tiết docs (LỖI-NHỎ): RESULT_TRAIL2 ghi "ΣPnL FLAT3−T0 +469" — artifact cho **+534** (96 909 − 96 375, = Δequity); AUDIT_G2FLAT3 F4 ghi "UW 87 vs 138 của G2" — G2 là **129** (MTM phút) / 137 (ngày); 138 là PROP50.

## 2. Tái lập việc chọn FLAT3 — mục 2: **ĐÚNG theo luật pre-reg; diễn giải "tốt nhất" SAI** (LỖI-NHỎ)

### 2.1 Mọi arm vs FLAT3 (Δ = arm − FLAT3; inflate k=11 ×2,19)

| arm | ΔPnL ghép cặp | CI raw | CI inflate | Δ khớp / Δ lệch tập | ΔPnL theo năm vào 21/22/23/24/25 (k) | ΔCAGR ngày pp [infl] | ΔmaxDD ngày pp [infl] | ΔCalmar ngày [infl] · P(Δ>0) |
|---|---|---|---|---|---|---|---|---|
| T0 | **+1,06k** | [−3,4; +6,2] | [−8,7; +12,3] | −1,58 / +2,64 | −0,0/−0,3/−0,9/+0,5/+1,9 | −0,12 [−3,6; +3,7] | −0,53 [−1,3; +1,2] | −0,18 [−0,79; +0,57] · 0,21 |
| A5 | −14,70k | [−27,1; −3,1] | [−41,8; +10,7] | −13,32 / −1,38 | −1,5/−1,4/−4,7/−6,5/−0,6 | −5,36 [−14,7; +2,6] | −0,44 [−2,2; +4,0] | −0,66 [−2,06; +1,33] · 0,06 |
| GV3 | −2,40k | [−4,8; −0,1] | [−7,7; +2,7] | −1,16 / −1,25 | −0,1/−0,3/−0,1/−1,5/−0,5 | −0,93 [−3,0; +0,9] | −0,31 [−1,5; +0,8] | −0,19 [−0,64; +0,28] · 0,04 |
| LAD | −0,72k | [−4,7; +3,9] | [−9,5; +9,4] | −0,82 / +0,11 | +0,2/+0,2/−0,9/−1,6/+1,5 | −0,39 [−3,3; +2,4] | +0,28 [−1,5; +1,1] | **+0,06** [−0,79; +0,49] · 0,43 |
| A5LAD | −13,03k | [−26,0; −0,9] | [−41,4; +13,5] | −12,83 / −0,20 | −1,0/−0,6/−4,6/−6,9/+0,1 | −4,52 [−14,3; +3,8] | +0,03 [−1,6; +3,9] | −0,44 [−1,74; +1,80] · 0,14 |
| PROP50 | +0,71k | [−9,6; +12,2] | [−21,8; +25,9] | −2,88 / +3,59 | +1,7/−0,0/−3,5/−2,2/+4,7 | −0,02 [−8,5; +9,9] | −1,35 [−4,5; +1,6] | −0,41 [−1,89; +1,07] · 0,11 |
| PROP30 | −2,16k | [−5,2; +1,0] | [−8,9; +4,8] | −1,36 / −0,80 | −0,0/−0,2/−1,2/−1,1/+0,2 | −1,01 [−3,8; +1,5] | −0,38 [−1,7; +0,9] | −0,22 [−0,78; +0,42] · 0,06 |
| FLAT5 | −0,21k | [−5,3; +5,5] | [−11,3; +12,3] | +0,04 / −0,25 | −0,2/−0,8/+0,5/−0,6/+0,9 | −0,58 [−4,8; +4,2] | −1,21 [−2,9; +1,5] | −0,42 [−1,04; +0,70] · 0,05 |
| HTD1 | −29,41k | [−47,8; −11,1] | [−69,6; +10,7] | −8,93 / −20,49 | −3,2/−7,0/−0,1/−13,5/−5,6 | −32,1 [−68,3; +1,2] | −16,8 [−67,0; +9,2] | −3,34 [−14,3; +0,6] · 0,00 |
| ET_A1 | +1,76k | [−7,2; +12,1] | [−17,9; +24,4] | +0,23 / +1,54 | +1,5/+1,5/−2,5/−0,7/+2,0 | +1,96 [−8,2; +13,9] | +0,64 [−1,9; +12,6] | +0,44 [−1,38; +5,35] · 0,85 |
| ET_A2 | +1,17k | [−6,2; +10,3] | [−14,9; +21,1] | +1,29 / −0,12 | +1,1/+1,5/−1,8/−0,2/+0,5 | +1,79 [−6,4; +12,5] | +0,64 [−1,4; +12,6] | +0,43 [−1,09; +5,30] · 0,86 |

- **Không Δ nào ngoài CI inflate** (cả hai thước). Ngoài CI **raw** (không inflate): A5, A5LAD, HTD1 (kém), GV3 (kém, sát biên) — khớp kết luận audit trước "hạ arm / bỏ time-stop kém rõ".
- **Không arm nào hơn FLAT3 ở mọi năm 2022–25** (ghép cặp lẫn ROI MTM ngày): cột cờ `all_years_*` = False cho cả 11 arm.
- Xếp hạng FLAT3 trong 9 arm trailing: ΣPnL #1 · CAGR #1 · UW #1 (đồng hạng GV3/PROP30) · Calmar_MTM-phút #2 (sau LAD) · Calmar ngày #2 (sau LAD) · ΔPnL ghép cặp #3 (sau T0, PROP50) · maxDD MTM-phút #6. ⇒ **"tốt nhất" không được thước nào ủng hộ một cách nhất quán; "không kém phát hiện được + đơn giản nhất" thì có.**
- vs T0 (ref = T0, JSON `*-T0`): FLAT3−T0 = **−0,95k** [−6,0; +3,4] raw (khớp phần +1,69k / lệch −2,64k); ΔCalmar ngày **+0,18** [−0,57; +0,79] infl, P>0 0,79. Hai thước cho dấu ngược nhau ⇒ **FLAT3 ≈ T0**.

### 2.2 Phân phối ROI (profit %) — mục (iv)

| arm | armed q10/25/50/75/90/95/99 | %ΣPnL theo ROI lúc thoát: <0 / 0–4 / 4–6 / 6–8 / 8–12 / 12–25 / ≥25 |
|---|---|---|
| FLAT3 | 4,0 / 5,0 / 6,0 / 8,5 / 11,5 / 14,4 / 53,3 | −67,9 / 7,4 / 45,6 / 37,0 / 36,2 / 24,9 / 16,7 |
| T0 | 3,5 / 4,0 / 5,5 / 7,5 / 13,0 / 18,5 / 51,3 | −65,2 / 19,3 / 39,5 / 24,8 / 21,8 / 31,6 / 28,2 |
| LAD | 5,0 / 5,5 / 6,5 / 7,5 / 9,5 / 13,0 / 55,0 | −66,2 / 1,2 / 51,6 / 62,1 / 17,3 / 15,8 / 18,2 |
| GV3 / PROP30 | 5,0 / 5,5 / 6,0 / 7,5 / 10,5 / 13,7–14,0 / 52–54 | −69 / 1,2 / 60,1 / 42–43 / 29–30 / 16–18 / 18–19 |
| FLAT5 | 2,5 / 3,5 / 5,5 / 9,5 / 14,5 / 19,0 / 53,7 | −67,6 / 22,3 / 22,7 / 21,0 / 37,5 / 41,6 / 22,6 |
| PROP50 | 3,5 / 4,0 / 5,0 / 7,5 / 12,5 / 18,9 / 63,0 | −67,7 / 22,7 / 38,4 / 20,4 / 21,4 / 25,2 / 39,6 |

Đọc: mọi dạng chỉ **dời lợi nhuận giữa thân và đuôi**; tổng gần bất biến (Σ PnL armed 147,9–153,6k cho 7 arm arm-7). Siết vùng thấp (gap ~2 pp: GV3/PROP30/LAD) nâng sàn 4→5 % nhưng cắt đuôi 12–25 %; nới (FLAT5/PROP50/T0) giữ đuôi nhưng thoát sớm ở 2,5–4 %. FLAT3 nằm giữa — đúng hình ảnh "đỉnh bằng phẳng" của mặt đáp ứng.

## 3. Phủ lưới — mục 3 (CHỈ liệt kê, KHÔNG chạy)

Neo cơ chế (B0, `AUDIT_LONG_LEVERS` §2, tái lập ở bảng §1): 2 157 lệnh armed **+153,6k**; 339 time-stop **−55,9k** (giá trung vị trôi đơn điệu −5,5 % @24h → −13,6 % lúc cắt); excess sau thoát TS ≈ 0 (không có "tiền bỏ quên" sau trailing); 46 % ΣPnL từ lệnh thoát ROI 4–6 %. MDE80 thước ghép cặp (inflate k=11) ≈ 3,1 × nửa-độ-rộng ≈ **7–17k**.

| trục | đã chạy trên nền G2 (ghép cặp vs FLAT3) | CHƯA chạy | bằng chứng gián tiếp | kỳ vọng |
|---|---|---|---|---|
| gap phẳng (arm 7) | 3 (FLAT3), 5 (FLAT5 −0,2k; Calmar_d −0,42, P>0 0,05) | **2; 2,5; 4** | gap ≈2–2,1 pp ở vùng đỉnh 7–10 % (nơi ~80 % lệnh armed) đã có qua GV3 (−2,4k, CI raw <0), PROP30 (−2,2k), LAD (−0,7k) ⇒ siết dưới 3 không lợi; 4 kẹp giữa 3 và 5 (cả hai ≈) | 2/2,5: ≤0; 4: ≈0 ± <2k ⇒ **dưới MDE** |
| gap tỉ lệ | 0,3 / 0,5 không trần; min(0,3/0,5·p, 8/3 %) | 0,4 | nằm giữa PROP30 (−2,2k) và PROP50 (+0,7k, CI ±11k) | ≈0, **dưới MDE** |
| ladder | 2/4/8 pp @5/10/20 % (LAD −0,7k, Calmar ≈) | ladder neo 3 pp (vd 3→5 pp sau 20 %) | TRAIL_LADDER (T170): nới đuôi tăng PnL nhóm sóng lớn nhưng **tổng không đổi**, capture/lệnh giảm; đuôi ≥25 % chỉ 16–40 % ΣPnL và do vài chục lệnh | ≈0, **dưới MDE** |
| arm | 5 (A5 −14,7k, A5LAD −13,0k), 7 | **6; 8** (và arm 5 + FLAT3) | đường arm 5 → 7: −14,7k; arm 8–9: ước lượng audit −10…−30k (874 lệnh thoát 4–6 % có đỉnh 7–9 % mất bảo vệ) | arm 6: kỳ vọng âm (nội suy −5…−8k); arm 8: âm ⇒ **không đáng** |
| time-decay arm | — | X = 24/48/72h hạ arm còn 3 % | counterfactual 0-sim +0,4 / +1,8 / +1,3k (CI chứa 0) | **dưới MDE** |
| time-stop (lệnh chưa arm) | 72h (+1,8k), cond 72h×MFE<5 % (+1,2k), 168h (B0), ∞ (HTD1 −29,4k) | **96, 120, 240h** | 96/120h: CF +4,0 / +2,0k (cận trên) & −3,1 / −1,6k (cận dưới); 240h: giữa 168h và ∞ trên đường trôi đơn điệu ⇒ âm | 96/120: \|Δ\| < 4k; 240: âm ⇒ **không đáng** |
| tổ hợp gap × time-stop | FLAT3 × {72, cond72, 168, ∞} | T0/LAD × 72h | hai trục gần cộng tính (time-stop chỉ đụng lệnh **chưa** arm, trailing chỉ đụng lệnh **đã** arm; tương tác chỉ qua vốn/slot) ⇒ tổ hợp ≈ tổng hai Δ nhỏ | **dưới MDE** |
| đỉnh theo CLOSE (PEAK_CLOSE) | chỉ trên T170 (NO-GO: mP\|SM tốt, TSloss xấu ngoài CI) | trên G2 | — | dời phân phối, không đổi tổng; **có giá trị cho parity live (§5), không phải lever** |

⇒ **Không ô nào có kỳ vọng ≥ MDE.** Chỗ duy nhất "về lý thuyết có thể hơn" là trục **thời gian sống lệnh chưa arm** — đã đo (EXIT_TIME_B0) và đóng đúng luật; chạy lại 96/120h là quét tham số trên DEV đã nhìn ⇒ forking path.

## 4. Code vs pre-reg — mục 4

| hạng mục | kết quả | bằng chứng |
|---|---|---|
| FLAT3 = gap cố định 3 pp sau arm 7 % cả nhánh weak/strong | **ĐÚNG** | `TradeUtils.trailFromCap`: `gap = min(peak·TS_GIVEBACK_RATIO, maxGap)`, RATIO = 1,0 & peak ≥ 0,07 ⇒ gap = maxGap = 0,03; `calRateLossDynamicBuyPNoPump` chọn `TS_MAX_GAP_WEAK` hoặc `TS_MAX_GAP`, cả hai 0,03 ⇒ nhánh pNoPump vô hiệu; `OrderTargetInfoTest.trailRate` (372–393): `TS_LADDER_ON=false`, `TS_CAP_STRONG_RANK=0` ⇒ rơi vào nhánh pNoPump. Key đọc ở `Configs.java:900-901` (không phải 894-895 — đã nêu AUDIT_G2FLAT3 F9) |
| Làm tròn 0,5 % | **ĐÚNG, ảnh hưởng nhỏ** | `rate = round((peak−0,03)/0,005)·0,005` ⇒ gap hiệu dụng ∈ [2,75; 3,25] pp, trung bình 3,0 (không lệch). "3 pp" là **điểm % theo giá entry** (ở đỉnh +50 % stop chỉ cách đỉnh 2 % giá). SL đầu tiên ≥ +4 % (armed q10 = 4,0 %) |
| SL cứng trước arm | **KHÔNG CÓ trong B0** | `PRE_ARM_SL` mặc định 0, profile `g2_flat3` không khai; nhánh cũ `calRateLossDynamicBuy` đã xoá 2026-09-03 (comment `TradeUtils`). Lối ra lệnh chưa arm duy nhất: **time-stop 168h** (đóng tại min(open, close) nến vượt 168h kể từ leg đầu) + delist (không update 2 ngày ⇒ đóng tại lastPrice) — B0: 339 TS + 21 SL khác. Trong TRAIL/TRAIL2 time-stop **giữ nguyên 168h** ⇒ các vòng đó chỉ so **phần trailing**; trục thời gian được đo riêng (HOLDTODIE, EXIT_TIME_B0) — tách đúng |
| Thứ tự ưu tiên cùng nến 1m | **ĐÚNG, bảo thủ** với 1 mơ hồ | `startUpdateOldOrderTrading`: pre-arm SL (tắt) → time-stop → cond-exit (tắt) → TP cố định (tắt) → arm/trailing. Nến arm: SL đặt từ HIGH, `BLOCK_INTRABAR_LOOKAHEAD` ⇒ không khớp cùng nến. Nến có SL: kiểm khớp bằng `minPrice` (đáy từ lần dời SL trước) **trước** khi dời SL theo HIGH nến này; khớp tại min(SL, open). **Mơ hồ:** khi SL được dời lên từ HIGH nến t, `minPrice` reset = close_t ⇒ LOW nến t (nếu xảy ra SAU đỉnh) bị bỏ qua — giả định "đáy trước đỉnh". Với gap hẹp 3 pp, giả định này lạc quan hơn gap rộng; quan trọng nhất ở 521 lệnh đóng trong giờ vào (42 % ΣPnL, nến sập). Độ lớn không đo được từ printDone |
| Bất nhất nhỏ | LỖI-NHỎ (vô hại) | cổng simulator dùng `peak >= entry·1,07`, `updateStatusNew` dùng `rateLoss > 0,07` (strict) — chỉ khác khi HIGH đúng bằng 1,07·entry |

## 5. Live — mục 5 (chỉ tổng hợp docs + đọc code, không chạm 242/shadow)

- **Key/công thức: KHỚP.** `DEPLOY242_G2FLAT3_READINESS_20261002` §7: arm 0,07; `TS_GIVEBACK_RATIO`/`SIM_TS_MAX_GAP`/`_WEAK` = 1,0/0,03/0,03 trên 242; đường live `tsGap` và sổ giấy `ShadowBookC3.trailRate` đều gọi `TradeUtils.calRateLossDynamicBuyPNoPump → trailFromCap` (chung sim). `TRAIL_HINGE_NET015=true`/`TS_PRED_GAP=1` chỉ đổi nguồn pNoPump ⇒ vô hiệu khi hai cap bằng nhau. (`PARITY_242_VS_G2FLAT3` 10-01 ghi 242 chạy T0 — **trước** fix 10-01; đã lỗi thời.)
- **Thực nghiệm: CHƯA CÓ.** 0 lệnh giấy/thật kể từ deploy (gate warm-up tới ~10-07 17:01) ⇒ chưa có một sự kiện arm/TS nào để so.
- **Lệch cơ chế sổ giấy vs sim** (`ShadowBookC3.tick` 338–383, đọc code):
  1. đỉnh và arm theo **giá snapshot** mỗi nhịp (`getAllPriceRealtimeLegacy`), sim theo **HIGH nến 1m** ⇒ giấy arm muộn/ít hơn, SL thấp hơn (PEAK_CLOSE trên T170 cho thấy đổi HIGH→CLOSE dời phân phối thoát có ý nghĩa: mP|SM ↑, TSloss ↑);
  2. khớp **đúng tại SL** (`closeAt(c, c.priceSL)`), sim khớp min(SL, open) ⇒ giấy lạc quan khi gap-down;
  3. time-stop tại giá hiện tại (sim: min(open, close));
  4. ledger giấy không trừ phí/slippage/funding (~0,11 %/vòng + funding).
  ⇒ Với gap phẳng 3 pp (dạng hẹp nhất ở vùng đỉnh cao, nhạy wick nhất), **PnL giấy của FLAT3 không phải ước lượng không lệch của sim**. Vị thế LEGACY thật dùng `tsGap` với dead-zone ×5,21847 (không liên tục) — không phải FLAT3 như sim (đã nêu AUDIT_G2FLAT3 F2).
- **Khuyến nghị đo (không chạy ở đây):** khi có ≥ 30 lệnh giấy đã arm, replay chính các lệnh đó qua `trailFromCap` trên nến 1m (HIGH/LOW) và so ROI thoát từng lệnh (paired) — tách lệch "đường giá" khỏi lệch "luật".

## 6. Verdict — mục 6

**FLAT3 = ngang nhất + đơn giản nhất, KHÔNG phải tốt nhất; không có cấu hình trailing nào bị bỏ sót đáng chạy.**
- Trong 8 biến thể trailing đã chạy trên G2: không arm nào hơn FLAT3 ngoài CI (inflate), không arm nào hơn ở mọi năm; T0/PROP50 hơn về ΔPnL điểm (+1,1k/+0,7k), LAD hơn về Calmar điểm (+0,06) — tất cả trong nhiễu. Lý do giữ FLAT3 hợp lệ là **1 tham số, bỏ nhánh pNoPump** — không phải hiệu năng.
- Cấu hình thoát tốt nhất **về điểm** từng chạy là FLAT3 + time-stop 72h (ET_A1) — đã NO-GO đúng luật (CI chứa 0, 2/4 năm, ~80 % chênh là trôi size); không mở lại trên DEV.
- **Không đề xuất pre-reg mới**: mọi ô chưa phủ (gap 2/2,5/4, ratio 0,4, arm 6/8, time-decay, time-stop 96/120/240, ladder neo 3 pp) có kỳ vọng < MDE 7–17k hoặc âm. Chạy thêm chỉ tăng multiplicity trên DEV đã dùng ~40 lần. Nguồn thông tin còn lại cho exit là **forward** (parity §5).
- **Sửa tài liệu (không cần chạy):** (a) `AUDIT_LONG_LEVERS_20261002` §KẾT LUẬN 3: "FLAT3 − T0 = +1,06k" → "**T0 − FLAT3 = +1,06k** [−3,4; +6,2] (FLAT3 ≈ T0)"; (b) bỏ mọi diễn giải "FLAT3 tốt nhất" → "không kém phát hiện được, đơn giản nhất" (trùng AUDIT_G2FLAT3 P2); (c) RESULT_TRAIL2 "+469" → +534; AUDIT_G2FLAT3 F4 "UW G2 138" → 129.

## 7. Giới hạn
- Thước ghép cặp: lệnh lệch (4–24 %) cộng/trừ nguyên PnL ⇒ phần "lệch tập" mang nhiễu entry (vd T0−FLAT3 do phần này quyết định dấu). Size-neutral theo notional REF nên ΔPnL ≠ Δequity (trôi lãi kép bị loại có chủ đích).
- MTM ngày từ `sim.out` (b+unP cuối ngày) — maxDD ngày −10,0 % vs MTM phút −17,7 %; dùng cho Δ paired, không thay số MTM phút đã công bố. MTM phút lấy từ cache `/tmp/*_mtm.json` (có thể bị xoá; số đã chép vào JSON).
- Inflate k=11 gộp cả arm time-stop (HTD, ET) — bảo thủ hơn k=8 (chỉ trailing, ×2,04); không đổi kết luận vì không Δ nào gần biên inflate.
- Seed: mỗi contrast dùng rng mới seed 20260905 (contrast T0−FLAT3 trùng tuyệt đối với `AUDIT_LONG_LEVERS_20261002_paired.json`); các contrast khác lệch CI vài trăm USDT so với audit cũ do thứ tự rng — không đổi kết luận.
- 1 đường lịch sử DEV; mọi mô tả ở đây hậu kiểm.

## Artifact
`research/analysis/reaudit_flat3.py` · `docs/audit/REAUDIT_FLAT3_20261003.json` (arms, contrasts vs FLAT3 và vs T0, năm, ROI) · nguồn: `~/kaggle_sim/out/{trail-g2-*, trail2-g2-*, htd-h1, exit-time-a1/a2}`.
