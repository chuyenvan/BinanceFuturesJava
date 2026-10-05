# RESULT — GATE_BAGFIX_NULL (Pha C chương trình GATE)

- **Pre-reg:** `docs/prereg/PREREG_GATE_BAGFIX_NULL.md` commit **8ee3b238** (chốt TRƯỚC khi sinh pred.bin; kèm driver), md5 6 pred.bin commit **ef09e7cf** (TRƯỚC khi đẩy kernel; = code_sha của 6 kernel). Driver `research/analysis/gate_bagfix_null_driver.py` (không sửa sau 8ee3b238). Số đầy đủ: `docs/result/gate_bagfix_null.json`.
- **Ràng buộc đã giữ:** 0 sửa .java, 0 build, 0 Java/sim trên Oracle (sinh pred.bin thuần numpy/pandas 11 s, RSS 0,89 GB; chấm 16 phút, RSS 0,60 GB, lock `oracle_heavy.lock` khi chấm, đã gỡ). 6 kernel Kaggle ≤ 2 song song, template `tools/kaggle_sim.py` HEAD (md5 8b60b00a, NOWRITE242) + khối `pred_ds` y nguyên GATE_SEEDBAND. 2026 không dùng (420 phút ≥ 2026 = p0, sim dừng 20251230). 0 lệnh xoá.
- **Đĩa:** trước 6 342 MB → sau 6 042 MB. Ghi mới: 230 MB `~/claude_master/1004/gbn` (6 pred.bin × 38 MB + log/json), 24 MB Kaggle out (`~/kaggle_sim/out/gbn-*`). Dataset Kaggle = hardlink (`dir_mode=skip`). Không lần nào gần ngưỡng 500 MB.
- **Tham chiếu:** A1 = `n700-a1` (printDone d9abf35f) = seed 42; dải 8 seed + BAG8/NULLB cũ lấy từ GATE_SEEDBAND (MTM cache md5 khớp; dải tính lại khớp RESULT_GATE_SEEDBAND tới 3 chữ số).

## 0. KẾT LUẬN (rủi ro trước)
1. **Q1 — BAG8M (bag số học + ánh xạ đơn điệu về phân phối p15 gốc): "trong dải", KHÔNG phải ứng viên giảm phương sai.** CAGR22 32,46 (percentile 37,5; < median 33,54 ⇒ trượt c_cagr), Calmar22 1,399 (≥ 0,9×1,455 ✓), maxDD22 −23,20 ✓, Jaccard phút TB vs seed 0,733 > 0,656 ✓. Ánh xạ sửa được một phần méo thang đo: phút mở 2022 101 → 130, CAGR22 29,11 → 32,46 (+3,35), nhưng vẫn dưới median và dưới A1 (ΔCAGR22 −4,19, CI inflate k=6 [−13,5; +3,5]).
2. **Q2 — RBAG8 (bag theo hạng + ánh xạ): "không phân biệt được" với BAG8M theo luật** (ΔCAGR22 RBAG8−BAG8M −3,68, CI inflate [−8,32; +0,06] — chạm 0; CI thô [−6,13; −1,70]). Chỉ báo cáo: ΔPnL −13,3k, CI inflate [−24,0k; −3,8k] toàn âm. RBAG8 tự nó: **"dưới dải"** (CAGR22 28,78 < min seed 29,24; percentile 0 mọi chỉ số chính), phút mở 2022 chỉ 104 dù đã ánh xạ về đúng phân phối p15 ⇒ co phút 2022 của bagging KHÔNG chỉ do thang đo: đồng thuận hạng 8 seed xếp ít phút 2022 lên đỉnh. RBAG8 ≈ BAG8 cũ (Jaccard phút 0,934, lệnh 0,902).
3. **Q3 — phân phối null: d = 2,23 ⇒ "có nhưng mỏng"** (luật 1 ≤ d < 3). Null hợp lệ G2 = 4/5 (NULLB 19,70, NULL1 12,31, NULL3 −0,86, NULL4 19,51; mean 12,66, sd 9,65); **NULL2 trượt G2** (n× 1,23, phút× 1,31 ⇒ loại theo pre-reg). Chỉ báo cáo: bản đủ 5 null d = 2,54; d Calmar22 1,19; **d CAGR23 (không 2022) 3,09**. Mô tả: 0/5 null ≥ min seed (max null 19,70 vs min seed 29,24).
4. **Bagging không cứu được tầng gate**: cả 3 biến thể bag (BAG8, BAG8M, RBAG8) đều ổn định hơn 1 seed (Jaccard phút 0,69–0,73 > 0,656) nhưng không biến thể nào ≥ median seed. Khác biệt gần như toàn bộ ở 2022 (ΔROI 2022 vs A1: BAG8M −11,5, RBAG8 −18,1; 2023–25 trong ±4) và cụ thể 22Q2 (−7,3 / −10,9 điểm).
5. **Không 2022, tầng gate gần như không phân biệt**: CAGR23 dải seed 47,8 ± 1,8 (45,4–50,4); BAG8M 48,37 (pct 50), RBAG8 46,43 (pct 25), A1 48,85. maxDD23 MTM cuối ngày mọi seed/bag −6,4…−6,8.

## 1. Cổng
| cổng | kết quả |
|---|---|
| **G0** (format `GA.g1` + spot 3 mốc + multiset p15 DEV == p0 + 9 decile ± 1e-6 + 420 phút 2026 == p0) | **PASS 6/6**; decile maxdiff = 0 (hoán vị đúng tập giá trị). md5: BAG8M `a56d99b6…`, RBAG8 `e571ce90…`, NULL1 `8490f16b…`, NULL2 `b681c3e9…`, NULL3 `730fb272…`, NULL4 `d03842d8…` (đủ 32 ký tự trong pre-reg §6). Spearman vs p0: BAG8M/RBAG8 0,9984; null 0,006–0,143. Kiểm phụ: x của BAG8M ép float32 == BAG8 cũ (True). |
| **G2 quota** (±25% A1: 732 lệnh/năm; 146,5 phút/năm) | BAG8M 0,96/0,95 ✓ · RBAG8 0,92/0,89 ✓ · NULL1 1,06/1,09 ✓ · **NULL2 1,23/1,31 ✗** · NULL3 1,06/1,07 ✓ · NULL4 1,02/0,94 ✓. Phút mở 2022: A1 170, seed 106–170, BAG8 101, **BAG8M 130**, **RBAG8 104**, null 91–133. |
| **Parity Kaggle** | **PASS 6/6**: jar 7368be46, mapper ≥ 800, `SELECTOR_RANK_TOPK=24` + B0OV trong prof_run, `pred_md5_base` 5dd6bb4c, `pred_md5_used` = md5 arm, Java `WfoDataset LOAD offline OK … pred=2500260 (md5 verified)`; date_last 20251230; 1 805–2 659 s/kernel. |

## 2. Bảng arm (2022–2025; MTM ngày rebase 2021-12-31). Δ vs A1 = bootstrap MTM ngày ghép cặp block 10d, NREP 2000, seed 20260905; inflate √(2 ln 6) = 1,893 (CI của BAG8/NULLB cũ tính lại với k = 6 nên khác RESULT_GATE_SEEDBAND)
| arm | n | n/năm | phút mở/năm | phút 2022 | CAGR22 | maxDD22 | Calmar22 | UW22 | ΔCAGR22 [CI infl] | ΔPnL [CI infl] | pct CAGR22/Calmar22 | Jaccard phút/lệnh TB vs 8 seed | G2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **A1** | 3526 | 732 | 146,5 | 170 | 36,65 | −22,21 | 1,650 | 117 | — | — | 75 / 75 | — | — |
| BAG8 (cũ) | 3261 | 666 | 132,5 | 101 | 29,11 | −25,68 | 1,134 | 349 | −7,53 [−19,8; +2,3] | −30 482 [−58 207; −5 087] | 0 / 0 | 0,696 / 0,639 | ✓ |
| **BAG8M** | 3401 | 701 | 139,5 | 130 | 32,46 | −23,20 | 1,399 | 334 | −4,19 [−13,5; +3,5] | −18 023 [−37 925; +1 465] | 37,5 / 37,5 | **0,733 / 0,679** | ✓ |
| **RBAG8** | 3280 | 671 | 131,0 | 104 | 28,78 | −25,86 | 1,113 | 335 | −7,87 [−19,7; +1,7] | −31 295 [−59 439; −6 574] | 0 / 0 | 0,689 / 0,642 | ✓ |
| NULLB (cũ) | 4104 | 802 | 161,0 | 112 | 19,70 | −15,33 | 1,285 | 619 | −16,94 [−60,6; +26,7] | −59 030 [−152 035; +26 359] | 0 / 12,5 | 0,030 / 0,025 | ✓ |
| NULL1 | 3808 | 780 | 159,2 | 133 | 12,31 | −19,91 | 0,618 | 416 | −24,33 [−63,4; +11,2] | −75 412 [−175 329; +18 600] | 0 / 0 | 0,028 / 0,029 | ✓ |
| NULL2 | 4252 | 902 | 191,8 | 101 | 4,62 | −32,95 | 0,140 | 1265 | −32,03 [−66,8; −1,3] | −94 910 [−192 765; −4 821] | 0 / 0 | 0,031 / 0,028 | **✗** |
| NULL3 | 3619 | 776 | 157,0 | 91 | −0,86 | −33,67 (all −41,20) | −0,026 | 727 | −37,51 [−81,1; −1,8] | −105 392 [−206 705; −17 033] | 0 / 0 | 0,015 / 0,016 | ✓ |
| NULL4 | 3429 | 748 | 137,0 | 123 | 19,51 | −15,45 | 1,263 | 256 | −17,14 [−60,5; +19,7] | −65 540 [−167 803; +27 911] | 0 / 12,5 | 0,036 / 0,032 | ✓ |

Dải 8 seed (tính lại): CAGR22 34,18 ± 3,58 (29,24 / median 33,54 / 39,34); Calmar22 1,529 ± 0,254 (median 1,455); maxDD22 −22,55 ± 1,37; Jaccard cặp đôi seed phút 0,656 / lệnh 0,586. Jaccard BAG8M~BAG8 0,844/0,822; RBAG8~BAG8M 0,831/0,832; RBAG8~BAG8 0,934/0,902.
md5 printDone: BAG8M 45e8bd1e, RBAG8 cc94fadb, NULL1 837656d8, NULL2 bd600469, NULL3 2d4b36d6, NULL4 8f76a54f (đủ trong json).

## 3. Có / không 2022 (mọi arm) + ROI năm + phút gate-mở năm
CAGR23 / maxDD23 / Calmar23 = equity MTM cuối ngày (b+unP), cửa sổ 2022-12-31..2025-12-30 (rebase 2022-12-31) — chỉ báo cáo.

| arm | CAGR22 | Calmar22 | CAGR23 | maxDD23 | Calmar23 | ROI 2022 | 2023 | 2024 | 2025 | phút mở 22/23/24/25 |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | 36,65 | 1,650 | 48,85 | −6,54 | 7,474 | 5,7 | 69,0 | 47,7 | 32,0 | 170/106/130/180 |
| S7 | 31,34 | 1,377 | 46,82 | −6,59 | 7,107 | −6,0 | 62,4 | 43,7 | 35,5 | 138/112/144/178 |
| S13 | 34,10 | 1,488 | 49,29 | −6,45 | 7,638 | −2,8 | 66,3 | 49,8 | 33,5 | 137/114/128/182 |
| S21 | 29,24 | 1,185 | 45,78 | −6,79 | 6,741 | −9,9 | 56,7 | 47,5 | 34,0 | 106/105/133/172 |
| S99 | 38,23 | 1,785 | 50,41 | −6,53 | 7,715 | 7,3 | 70,0 | 47,8 | 35,3 | 163/105/138/186 |
| S123 | 31,56 | 1,362 | 47,13 | −6,77 | 6,960 | −5,9 | 65,5 | 42,3 | 35,2 | 131/108/124/178 |
| S777 | 39,34 | 1,962 | 45,39 | −6,48 | 7,007 | 22,6 | 58,6 | 52,3 | 27,1 | 160/111/131/173 |
| S2024 | 32,98 | 1,422 | 48,88 | −6,44 | 7,596 | −5,2 | 70,9 | 46,8 | 31,5 | 126/110/122/177 |
| BAG8 | 29,11 | 1,134 | 46,88 | −6,58 | 7,125 | −12,3 | 60,6 | 48,9 | 32,4 | 101/113/133/183 |
| **BAG8M** | 32,46 | 1,399 | 48,37 | −6,42 | 7,531 | −5,7 | 65,1 | 49,3 | 32,4 | 130/114/130/184 |
| **RBAG8** | 28,78 | 1,113 | 46,43 | −6,56 | 7,075 | −12,4 | 61,4 | 46,8 | 32,4 | 104/110/127/183 |
| NULLB | 19,70 | 1,285 | 24,38 | −10,96 | 2,224 | 6,7 | 3,7 | 26,7 | 46,3 | 112/140/187/205 |
| NULL1 | 12,31 | 0,618 | 6,63 | −15,19 | 0,437 | 31,2 | 3,1 | 0,5 | 17,1 | 133/146/193/165 |
| NULL2 ✗G2 | 4,62 | 0,140 | 9,87 | −17,26 | 0,572 | −9,7 | −8,3 | 21,6 | 18,9 | 101/157/242/267 |
| NULL3 | −0,86 | −0,026 | 0,88 | −26,74 | 0,033 | −5,9 | 4,3 | −5,6 | 4,3 | 91/209/143/185 |
| NULL4 | 19,51 | 1,263 | 20,77 | −8,48 | 2,450 | 15,8 | 17,8 | 41,7 | 5,5 | 123/161/116/148 |

Dải 8 seed không 2022: CAGR23 47,82 ± 1,80 (45,39–50,41), Calmar23 7,28 ± 0,37, maxDD23 −6,57 ± 0,14. Percentile BAG8M CAGR23 50 / Calmar23 62,5; RBAG8 25 / 37,5; BAG8 37,5 / 50.

**Δ lợi suất MTM theo quý vs A1 (điểm %)** — 22Q1..25Q4:
- BAG8M: −1,0 −7,3 −2,7 +0,1 | −1,4 −1,6 −0,8 +1,3 | +2,4 −0,3 +0,9 −1,8 | −0,2 −0,3 −0,0 +0,9
- RBAG8: −1,1 −10,9 −5,8 −0,0 | −3,4 −1,8 −1,0 +1,1 | +0,9 −0,4 +0,9 −2,1 | −0,5 −0,3 +0,2 +0,9
- BAG8 (cũ): −1,2 −10,8 −5,8 +0,0 | −3,6 −1,8 −1,6 +1,4 | +2,5 −0,3 +0,7 −1,9 | −0,3 −0,3 −0,0 +0,9
- NULL1: +7,4 +14,9 −8,4 +8,3 | −7,7 −25,5 −9,9 −9,1 | −10,1 +0,1 −10,9 −20,3 | −5,4 −7,3 +1,3 −1,3
- NULL2: +4,3 −16,0 −7,3 +5,8 | −12,7 −28,8 −9,4 −12,9 | −2,2 −0,2 −7,2 −11,8 | −14,5 −4,2 +4,4 +3,4
- NULL3: −5,0 −3,9 −7,7 +4,8 | −10,2 −30,4 −7,6 −1,5 | −8,7 −6,9 −15,4 −15,8 | −22,7 +4,9 +3,7 −10,3
- NULL4: +1,4 +9,4 −4,0 +2,1 | −7,3 −12,4 −8,3 −11,4 | −3,6 +6,7 +1,6 −10,1 | −19,6 +2,1 +0,7 −6,8

## 4. Phân phối null (Q3)
| tập null | n | CAGR22 mean | sd | d CAGR22 | d Calmar22 | d CAGR23 (không 2022) |
|---|---|---|---|---|---|---|
| **hợp lệ G2 (pre-reg): NULLB, NULL1, NULL3, NULL4** | 4 | 12,66 | 9,65 | **2,23** | 1,19 | 3,09 |
| đủ 5 (kể NULL2 trượt G2) — chỉ báo cáo | 5 | 11,06 | 9,10 | 2,54 | 1,43 | 3,59 |

d = (mean 8 seed − mean null)/sd null; mean seed CAGR22 34,18, Calmar22 1,529, CAGR23 47,82. Null giữ tự tương quan trong khối 30 ngày nhưng phá căn chỉnh thời gian với thị trường; tản mát null rất lớn (−0,86…19,70) — sd null gấp 2,7 lần sd seed.

## 5. Trả lời Q1–Q3 theo luật pre-reg
| Q | luật | kết quả |
|---|---|---|
| Q1 BAG8M | vị trí CAGR22 trong dải; ứng viên giảm phương sai ⇔ CAGR22 ≥ 33,54 AND Calmar22 ≥ 1,310 AND \|maxDD\| ≤ 40 AND Jaccard phút TB > 0,656 (+ G2, parity) | **"trong dải"** (percentile 37,5). **Không phải ứng viên**: c_cagr ✗ (32,46), c_calmar ✓ (1,399), c_dd ✓, c_jac ✓ (0,733), G2 ✓. |
| Q1' RBAG8 (cùng luật) | như trên | **"dưới dải"** (28,78 < 29,24). Không phải ứng viên: c_cagr ✗, c_calmar ✗ (1,113), c_dd ✓, c_jac ✓ (0,689). |
| Q2 | "khác" ⇔ CI inflate ΔCAGR22 (RBAG8 − BAG8M) không chứa 0 | **"không phân biệt được"** (−3,68 [−8,32; +0,06]). |
| Q3 | d ≥ 3 rõ; 1 ≤ d < 3 mỏng; d < 1 không đo được (null hợp lệ G2, ≥ 3) | **"gate có giá trị timing nhưng mỏng"** (d = 2,23, 4 null). |

## 6. Lệch pre-reg / ghi chú
- Không đổi arm, luật, thước, rng, thứ tự cộng bag sau khi thấy số. 0 arm thêm. Driver không sửa sau commit pre-reg 8ee3b238.
- Trước khi kernel xong đã chạy `score` 1 lần chỉ với arm cũ (dry-run kiểm code; không có số arm mới) — dải tính lại khớp GATE_SEEDBAND.
- `parity` chạy sớm 1 lần khi BAG8M/RBAG8 xong (chỉ kiểm parity, không chấm).
- NULL2 trượt G2 ⇒ loại khỏi tập null đúng pre-reg; bản đủ 5 chỉ báo cáo.
- maxDD23 dùng equity MTM cuối ngày (b+unP), không phải `dd_mtm` intraday của `R.run_mtm` (đã ghi trong pre-reg §4).
- CI của BAG8/NULLB cũ trong bảng §2 dùng k = 6 (vòng này), khác bản k = 8 của RESULT_GATE_SEEDBAND.
- Trailer commit dùng đúng chuỗi trong brief MASTER.

## 7. Rủi ro + đề xuất cho MASTER (không tự quyết)
**Rủi ro:**
1. **sd null từ 4 mẫu**: CI 95% của sd (χ², 3 bậc tự do) ≈ [5,5; 36] ⇒ d tương ứng ≈ [0,6; 3,9]. Kết luận "mỏng" là theo luật, không phải ước lượng chặt.
2. **Null không cố định quota**: hoán vị khối làm đổi động học rolling-quantile 90 ngày ⇒ phút mở/năm null dao động 137–192 (NULL2 trượt G2). Một phần chênh seed–null có thể đến từ lệch quota theo năm, không chỉ timing (NULL3 mở 209 phút năm 2023 vs A1 106).
3. **Tầng gate quyết định chủ yếu bởi 22Q2**: mọi bag/seed khác nhau gần hết ở 2022; không 2022 dải seed CAGR23 chỉ ± 1,8 và bag nằm giữa dải. Bagging không đổi được kỳ vọng, chỉ đổi phút mở ở crash 2022.
4. RBAG8 mở ít phút 2022 dù cùng phân phối p15 ⇒ giả thuyết "BAG8 chỉ méo thang đo" chỉ đúng một phần (BAG8M thu hồi 29 phút 2022 và +3,35 CAGR22, vẫn < median).
5. ΔPnL RBAG8−BAG8M CI inflate toàn âm trong khi ΔCAGR22 chạm 0 — 2 thước không đồng thuận; theo luật dùng ΔCAGR22.

**Đề xuất:**
- (P1) Không deploy BAG8M/RBAG8 (trượt luật). Giữ A1/B0 (seed 42) làm gate production; kỳ vọng kế hoạch theo dải seed (CAGR22 ~34,2), không theo A1.
- (P2) Đóng nhánh "bagging gate" — 3 biến thể đều ≤ median; chi phí thêm (8× retrain) không có lợi ích đo được.
- (P3) Nếu cần Q3 chặt hơn: thêm ≥ 6 null (rng chốt trước) và/hoặc null có quota cố định theo năm (ánh xạ lại phân vị theo từng năm) để tách timing khỏi quota; pre-reg riêng.
- (P4) Ưu tiên nghiên cứu tầng gate theo hướng ổn định hành vi 22Q2 (crash regime) thay vì tinh chỉnh model; mọi lever gate báo kèm bản không 2022.

## 8. Tái lập
`python3 research/analysis/gate_bagfix_null_driver.py gen` · `g0` · `upload ARM…` · `dsstatus` · `submit ARM --code-sha ef09e7cf` · `status` · `fetch ARM` · `parity` · `score --workers 3`. Artefact `~/claude_master/1004/gbn/` (pred_*/pred.bin + meta.json, g0.json, g1.json, parity.json, mtm.json, gen.log, g0.log, orch.log, tables.md, gbn_orch.sh); Kaggle out `~/kaggle_sim/out/gbn-{bag8m,rbag8,null1..4}`; dataset `chuyendinh/gate-bn-*`.
