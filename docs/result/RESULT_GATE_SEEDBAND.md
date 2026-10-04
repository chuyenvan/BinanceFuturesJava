# RESULT — GATE_SEEDBAND (Pha B chương trình GATE)

- **Pre-reg:** `docs/prereg/PREREG_GATE_SEEDBAND.md` commit **f79670a9** (chốt TRƯỚC retrain), md5 8 pred.bin + driver commit **11b61a9d** (TRƯỚC khi đẩy kernel; = code_sha của 8 kernel). Driver `research/analysis/gate_seedband_driver.py`. Số đầy đủ: `docs/result/gate_seedband.json`.
- **Ràng buộc đã giữ:** 0 sửa .java, 0 build, 0 Java/sim trên Oracle (retrain thuần Python, `GA.retrain` nguyên recipe, chỉ đổi `random_state`; RAM đỉnh 1,88G retrain / 0,60G chấm). 8 kernel Kaggle (≤ 2 song song), template = `tools/kaggle_sim.py` HEAD (md5 8b60b00a, NOWRITE242) + khối chèn `pred_ds` của GATE_ABLATION. 2026 không dùng. Lock `oracle_heavy.lock` khi retrain/chấm (đã gỡ). 0 lệnh xoá.
- **Đĩa:** trước 1 394 MB → sau 6 341 MB (owner dọn giữa vòng, lúc ~17:38). Ghi mới của vòng: 306 MB (`~/claude_master/1004/gsb`, 8 pred.bin × 38 MB, không npy) + 30 MB Kaggle out (8 × 3,6–4,3 MB). Dataset Kaggle = hardlink, upload từng file (`dir_mode=skip`, không zip, df không đổi). Không lần nào chạm ngưỡng 500 MB.
- **Tham chiếu A1** = B0@K24 (`n700-a1`, printDone d9abf35f, n 3526) = seed 42 của dải. Seed 7 = `gabl-seed7` (có sẵn).

## 0. KẾT LUẬN (rủi ro trước)
1. **Dải nhiễu seed của gate recipe (8 seed, K24): CAGR22 mean 34,18 / sd 3,58 / min 29,24 / median 33,54 / max 39,34** (rộng 10,1pp). Calmar22 1,53 ± 0,25 (1,19–1,96); maxDD22 −22,5 ± 1,4 (−24,7…−20,0); UW22 101–349 ngày. ⇒ mọi khác biệt gate < ~7pp CAGR22 (≈ 2 sd) không phân biệt được với đổi seed.
2. **Q1:** z(A1) CAGR22 = **+0,69** ⇒ theo luật **"A1 điển hình của recipe (|z| < 1)"**. Nhưng kỳ vọng recipe = 34,2, thấp hơn A1 2,5pp; 5/7 seed khác cho CAGR22 thấp hơn A1.
3. **Q2:** BAG8 **ổn định hơn** theo luật (Jaccard phút gate-mở TB vs seed 0,696 > cặp đôi seed 0,656; lệnh 0,639 > 0,586) **nhưng tệ nhất về hiệu suất**: CAGR22 29,11 (percentile 0 — dưới mọi seed), Calmar22 1,134 (percentile 0), maxDD22 −25,68 (sâu nhất), ΔPnL vs A1 −30,5k (CI inflate [−60,4k; −3,1k] — toàn âm). **Ứng viên deploy: KHÔNG** (trượt c_cagr, c_calmar; đạt c_dd, c_jac, G2).
4. **Q3:** NULLB (p15 hoán vị khối 30 ngày, G2 ĐẠT 1,10×/1,10×) CAGR22 **19,70 < min(seed) − sd = 25,66** ⇒ theo luật **"gate có giá trị timing"**. Cảnh báo: 1 lần hoán vị duy nhất; CI paired NULLB−A1 rất rộng (inflate [−63,9; +30,1]); thua dồn ở 2023 (−65,3 điểm ROI) và 2024 (−20,9), còn 2025 thắng +14,3 và maxDD nông hơn (−15,3).
5. **Phương sai do 2022 chi phối:** ROI 2022 theo seed −9,9…+22,6 (sd 10,7) so với 2023/24/25 sd 5,3/3,2/2,8; riêng **22Q2** Δ vs A1 từ −9,2 (S21) tới +13,9 (S777). corr(phút gate-mở/năm, CAGR22) trên 8 seed = **0,80**; phút gate-mở 2022 dao động 106–170 theo seed, BAG8 chỉ 101.

## 1. Cổng
| cổng | kết quả |
|---|---|
| **G0 format** (n 2 500 260, header/size, `ts`+`risk4h` byte-identical, p15 hữu hạn) | **PASS 8/8**. md5: S13 `cd6d7b2e…`, S21 `0b541d22…`, S99 `5ef90e92…`, S123 `9b1dad90…`, S777 `25f738f7…`, S2024 `3be4fac4…`, BAG8 `8bad71a4…`, NULLB `0939a4cb…` (đủ 32 ký tự trong pre-reg §6). |
| **G1** pearson p15 vs seed 42 theo fold (19 fold) ≥ 0,97 | **PASS 6/6**, 0 fold < 0,97. min/median: S13 0,9836/0,9935 · S21 0,9786/0,9932 · S99 0,9766/0,9938 · S123 0,9788/0,9935 · S777 0,9797/0,9936 · S2024 0,9888/0,9933. Spearman toàn chuỗi vs gốc: 0,995–0,997; BAG8 0,998; NULLB 0,033. |
| **G2 quota** (±25% A1: 732 lệnh/năm; 146,5 phút/năm) | **PASS 8/8** (n×/phút×): S13 0,95/0,96 · S21 0,90/0,88 · S99 1,04/1,01 · S123 0,97/0,92 · S777 1,00/0,98 · S2024 0,96/0,91 · BAG8 0,91/0,90 · NULLB 1,10/1,10. |
| **Parity Kaggle** | **PASS 8/8**: jar 7368be46, mapper 863, `SELECTOR_RANK_TOPK=24` + B0OV trong prof_run, `pred_md5_base`=5dd6bb4c, `pred_md5_used`=md5 arm, Java `WfoDataset LOAD offline OK … pred=2500260 (md5 verified)`; date_last 20251230; java_rc 1 như A1/gabl. |

## 2. Bảng arm (cửa sổ 2022–2025; MTM ngày rebase 2021-12-31). Δ vs A1 = bootstrap MTM ngày ghép cặp block 10d, NREP 2000, seed 20260905; inflate √(2 ln 8) = 2,039
| arm | seed | n | n/năm | phút mở/năm | CAGR22 | maxDD22 | maxDD all | Calmar22 | UW22 | PnL 22–25 | ΔCAGR22 [CI infl] | ΔPnL [CI infl] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A1** | 42 | 3526 | 732 | 146,5 | 36,65 | −22,21 | −22,21 | 1,650 | 117 | 103 357 | — | — |
| S7 | 7 | 3413 | 705 | 143,0 | 31,34 | −22,75 | −22,75 | 1,377 | 334 | 81 587 | −5,31 [−16,2; +4,2] | −21 770 [−45 049; +1 308] |
| S13 | 13 | 3374 | 693 | 140,2 | 34,10 | −22,92 | −22,92 | 1,488 | 301 | 92 092 | −2,55 [−12,7; +6,7] | −11 264 [−32 265; +9 151] |
| S21 | 21 | 3208 | 657 | 129,0 | 29,24 | −24,67 | −24,67 | 1,185 | 349 | 74 433 | −7,40 [−22,1; +4,6] | −28 924 [−62 069; +1 601] |
| S99 | 99 | 3654 | 760 | 148,0 | 38,23 | −21,41 | −22,06 | 1,785 | 117 | 109 183 | +1,58 [−6,6; +9,9] | +5 826 [−19 723; +31 574] |
| S123 | 123 | 3409 | 708 | 135,2 | 31,56 | −23,17 | −23,17 | 1,362 | 334 | 82 217 | −5,09 [−16,3; +5,4] | −21 140 [−49 807; +7 987] |
| S777 | 777 | 3464 | 729 | 143,8 | 39,34 | −20,05 | −20,05 | 1,962 | 101 | 112 643 | +2,70 [−13,6; +22,7] | +9 286 [−27 692; +49 881] |
| S2024 | 2024 | 3386 | 704 | 133,8 | 32,98 | −23,19 | −23,24 | 1,422 | 322 | 86 321 | −3,66 [−13,3; +4,9] | −17 036 [−40 557; +2 576] |
| **BAG8** | TB 8 | 3261 | 666 | 132,5 | 29,11 | −25,68 | −25,68 | 1,134 | 349 | 72 874 | −7,53 [−20,7; +3,1] | −30 482 [−60 350; −3 125] |
| **NULLB** | hoán vị | 4104 | 802 | 161,0 | 19,70 | −15,33 | −15,88 | 1,285 | 619 | 42 898 | −16,94 [−63,9; +30,1] | −59 030 [−159 223; +32 959] |

md5 printDone: S13 eb77f309, S21 1e7c88ae, S99 989de0ba, S123 b9d52701, S777 bf91d854, S2024 349d36b4, BAG8 a344960b, NULLB de45859e (đủ trong json).

## 3. Dải seed (n = 8: A1, S7, S13, S21, S99, S123, S777, S2024)
| chỉ số | mean | sd | min | median | max | A1 | z(A1) | BAG8 | pct BAG8 | NULLB |
|---|---|---|---|---|---|---|---|---|---|---|
| CAGR22 | 34,18 | 3,58 | 29,24 | 33,54 | 39,34 | 36,65 | **+0,69** | 29,11 | 0 | 19,70 |
| Calmar22 | 1,529 | 0,254 | 1,185 | 1,455 | 1,962 | 1,650 | +0,48 | 1,134 | 0 | 1,285 |
| maxDD22 | −22,55 | 1,37 | −24,67 | −22,83 | −20,05 | −22,21 | +0,25 | −25,68 | 0 | −15,33 |
| UW22 (ngày) | 247 | 113 | 101 | 312 | 349 | 117 | −1,15 | 349 | 88* | 619 |
| ΔPnL vs A1 | −10 628 | 14 097 | −28 924 | −14 150 | +9 286 | 0 | +0,75 | −30 482 | 0 | −59 030 |

\*percentile = % seed ≤ BAG8; với UW cao hơn = tệ hơn (BAG8 349 ngày ≈ max dải).

## 4. Ổn định (Jaccard, cửa sổ 2022–2025)
| cặp | phút gate-mở | lệnh (sym+phút vào) |
|---|---|---|
| seed–seed, TB 28 cặp | **0,656** | **0,586** |
| BAG8–seed_i, TB 8 | **0,696** | **0,639** |
| BAG8–A1 | 0,629 | 0,600 |
| NULLB–seed_i, TB 8 | 0,030 | 0,025 |
| A1–seed_i (S7/S13/S21/S99/S123/S777/S2024) | 0,652/0,620/0,593/0,669/0,667/0,656/0,646 | 0,583/0,577/0,549/0,584/0,607/0,583/0,602 |

Đọc: chỉ đổi seed ⇒ ~35% phút gate-mở và ~42% lệnh khác nhau. BAG8 là "tâm" của các seed (Jaccard với từng seed cao hơn seed–seed) nhưng mở ÍT phút hơn (132,5/năm; 2022 chỉ 101 so với 106–170 của seed).

## 5. Theo năm và theo quý
**ROI năm % (ΔROI vs A1) · phút gate-mở năm 22/23/24/25**

| arm | 2022 | 2023 | 2024 | 2025 | phút mở 22/23/24/25 |
|---|---|---|---|---|---|
| A1 | 5,7 | 69,0 | 47,7 | 32,0 | 170/106/130/180 |
| S7 | −6,0 (−11,7) | 62,4 (−6,6) | 43,7 (−4,0) | 35,5 (+3,5) | 138/112/144/178 |
| S13 | −2,8 (−8,5) | 66,3 (−2,7) | 49,8 (+2,1) | 33,5 (+1,5) | 137/114/128/182 |
| S21 | −9,9 (−15,6) | 56,7 (−12,3) | 47,5 (−0,2) | 34,0 (+2,0) | 106/105/133/172 |
| S99 | 7,3 (+1,6) | 70,0 (+1,0) | 47,8 (+0,1) | 35,3 (+3,2) | 163/105/138/186 |
| S123 | −5,9 (−11,6) | 65,5 (−3,5) | 42,3 (−5,4) | 35,2 (+3,1) | 131/108/124/178 |
| S777 | 22,6 (+16,9) | 58,6 (−10,4) | 52,3 (+4,6) | 27,1 (−4,9) | 160/111/131/173 |
| S2024 | −5,2 (−10,9) | 70,9 (+1,9) | 46,8 (−0,9) | 31,5 (−0,6) | 126/110/122/177 |
| BAG8 | −12,3 (−18,0) | 60,6 (−8,4) | 48,9 (+1,3) | 32,4 (+0,3) | 101/113/133/183 |
| NULLB | 6,7 (+1,0) | 3,7 (−65,3) | 26,7 (−20,9) | 46,3 (+14,3) | 112/140/187/205 |

sd ROI theo seed (8 seed): 2022 **10,7** · 2023 5,3 · 2024 3,2 · 2025 2,8.

**Δ lợi suất MTM theo quý vs A1 (điểm %)** — 22Q1..25Q4:
- S7: −1,6 −6,9 −2,5 −0,2 | −2,0 −2,6 −1,8 +2,0 | −2,0 +0,2 +0,9 −2,5 | +1,1 −0,2 −0,2 +2,4
- S13: −1,3 −5,7 −2,4 +1,2 | −1,4 −2,1 +0,5 +1,2 | +2,7 −0,3 +1,0 −1,8 | −0,3 −0,3 −0,6 +2,5
- S21: −0,8 −9,2 −6,0 +0,6 | −5,6 −0,9 −2,6 +0,9 | +1,8 −1,3 +1,3 −2,0 | +1,9 +0,1 −0,4 +0,1
- S99: −2,2 +2,7 +2,8 −1,7 | +1,1 +0,8 −1,5 +0,3 | +0,8 +1,3 −0,0 −2,2 | −0,8 +0,3 −0,1 +3,4
- S123: −0,8 −6,6 −3,8 −0,2 | +0,4 −1,2 −2,2 +0,6 | −0,8 −1,2 +1,0 −3,3 | +2,4 −0,4 −0,5 +1,3
- S777: −1,1 +13,9 +2,8 −0,4 | −2,0 −1,9 −3,0 −0,2 | +3,4 +2,0 +0,0 −2,1 | −1,5 −0,4 −1,8 −0,3
- S2024: −1,8 −6,7 −0,2 −1,7 | −0,3 +0,6 +0,1 +0,9 | −0,8 +0,5 +0,8 −1,4 | −0,7 −0,0 +0,1 +0,1
- BAG8: −1,2 −10,8 −5,8 +0,0 | −3,6 −1,8 −1,6 +1,4 | +2,5 −0,3 +0,7 −1,9 | −0,3 −0,3 −0,0 +0,9
- NULLB: −0,6 +17,6 −13,9 −1,8 | −13,3 −8,7 −16,0 −14,1 | −9,7 −1,6 −3,9 −1,4 | −4,3 +6,5 +6,6 +1,8

Đọc: 22Q2 (LUNA/3AC) quyết định thứ hạng seed (−9,2…+13,9); từ 2023Q1 trở đi |Δ quý| của seed hầu hết ≤ 3,5 điểm. NULLB thắng 22Q2 (+17,6) rồi thua liên tục 22Q3–24Q4.

## 6. Trả lời Q1–Q3 theo luật pre-reg
| Q | luật | kết quả |
|---|---|---|
| Q1 dải seed | z(A1) CAGR22 ≥ +1 ⇒ may mắn; \|z\| < 1 ⇒ điển hình | **z = +0,69 ⇒ "A1 điển hình của recipe"**. (z Calmar22 +0,48, maxDD22 +0,25, UW22 −1,15, ΔPnL +0,75 — báo cáo) |
| Q2 BAG8 | ổn định ⇔ Jaccard phút BAG8–seed > seed–seed; ứng viên deploy = 5 điều kiện | **"BAG8 ổn định hơn 1 seed"** (0,696 > 0,656). **Không phải ứng viên deploy**: c_cagr ✗ (29,11 < median 33,54), c_calmar ✗ (1,134 < 0,9×1,455 = 1,310), c_dd ✓ (−25,7), c_jac ✓, G2 ✓. Vị trí: dưới mọi seed về CAGR22/Calmar22/maxDD22/ΔPnL. |
| Q3 timing | NULLB < min − sd ⇒ có timing; trong [min, max] ⇒ không đo được | **"gate có giá trị timing"** (19,70 < 29,24 − 3,58 = 25,66; NULLB G2 đạt). |

## 7. Lệch pre-reg / ghi chú
- Không đổi arm, luật, thước, seed, trọng số bag sau khi thấy số. 0 arm thêm.
- Chấm sớm từng phần (score chạy 3 lần khi mới có 2/4/6 arm mới, chỉ để nạp cache MTM `gsb/mtm.json`); đã nhìn số trung gian nhưng không đổi gì — luật/cửa sổ cố định từ f79670a9.
- `fetch` tải toàn bộ output kernel (3,6–4,3 MB/run, gồm sim log cần cho kiểm "md5 verified"), không chỉ printDone/result/MTM — tổng 30 MB.
- 1 lần fetch BAG8 lỗi mạng (ConnectTimeout kaggleusercontent) → fetch lại thủ công, output đủ, parity PASS.
- MTM A1/S7 lấy từ cache `gabl/mtm.json` (md5 printDone khớp) — cùng hàm `run_mtm`.
- Dải dùng seed 42 = pred.bin gốc (A1), không dùng bản retrain G0 (không byte-identical) — như pre-reg §2.
- Dòng trailer commit dùng model thật đang chạy (Opus 5.5), không dùng tên trong brief.

## 8. Rủi ro + đề xuất cho MASTER (không tự quyết)
**Rủi ro:**
1. **Kỳ vọng recipe ≠ A1**: CAGR22 mean 34,2 (median 33,5) vs A1 36,65; Calmar22 mean 1,53 vs 1,65; UW22 median 312 ngày vs A1 117. Kế hoạch rủi ro dựa trên A1/B0 đang lạc quan ~2,5pp CAGR22 và rất lạc quan về UW.
2. **sd chỉ từ 8 seed** (sai số tương đối của sd ~±25%); ngưỡng "≈ 2 sd ≈ 7pp" là xấp xỉ.
3. **Q3 dựa trên 1 lần hoán vị**: không có phân phối null; NULLB có maxDD nông hơn mọi seed và thắng 2025 (+14,3) — kết luận "có timing" đúng luật nhưng mỏng.
4. **Bagging dịch chuyển, không giảm, rủi ro hiệu suất**: lấy trung bình 8 p15 làm co đuôi ⇒ ít phút vượt quota (2022: 101 phút so với 106–170) ⇒ hụt 22Q2 (−10,8 điểm). Tập phút ổn định hơn nhưng kết quả nằm ngoài (dưới) dải seed. corr(phút gate-mở, CAGR22) = 0,80 trên 8 seed ⇒ hiệu suất gate chủ yếu đi qua "mở bao nhiêu phút ở crash 2022", không phải chất lượng xếp hạng chung.
5. 1 quý (22Q2) quyết định thứ hạng; mẫu DEV hiệu dụng cho tầng gate rất nhỏ.

**Đề xuất:**
- (P1) Chuẩn hoá band: mọi lever tầng gate về sau so với **dải 8 seed** (mean 34,18, sd 3,58), không so với A1 đơn lẻ; lever chỉ "có tác dụng" nếu nằm ngoài [min; max] dải hoặc được chạy ≥ 3 seed/arm. Cần pre-reg riêng.
- (P2) Không deploy BAG8 (luật trượt). Nếu muốn theo đuổi giảm phương sai: vòng riêng hiệu chỉnh lại quota (PCT) cho phân phối p15 bag sao cho phút gate-mở = A1, pre-reg trước; không tune trong vòng này.
- (P3) Củng cố Q3: NULL-BLOCK với ≥ 5 hoán vị (seed rng chốt trước) để có phân phối null; giữ luật min − sd.
- (P4) Báo cáo mọi lever gate có/không 2022 (hoặc có/không 22Q2) như chỉ số phụ, vì sd ROI 2022 = 10,7 so với ≤ 5,3 các năm khác.

## 9. Tái lập
`python3 research/analysis/gate_seedband_driver.py retrain S13 S21 S99 S123 S777 S2024` · `nullb` · `bag` · `g0` · `upload ARM` · `submit ARM --code-sha 11b61a9d` · `status` · `fetch ARM` · `parity` · `score --workers 3`. Artefact `~/claude_master/1004/gsb/` (pred_*/pred.bin + meta.json, retrain_*.json, g0g1.json, parity.json, mtm.json, *.log); Kaggle out `~/kaggle_sim/out/gsb-{s13,s21,s99,s123,s777,s2024,bag8,nullb}`; dataset `chuyendinh/gate-sb-*`.
