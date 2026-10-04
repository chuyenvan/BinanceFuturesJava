# GATE_QUOTA_DIAG_20261004 — chẩn đoán quota gate G2 + bộ mô phỏng gate offline (Pha D chương trình GATE)

- **Pre-reg:** `docs/prereg/PREREG_GATE_QUOTA_DIAG.md` + `research/analysis/gate_offline.py` commit **1750cfa0** (TRƯỚC khi chạy stage `all`). Số đầy đủ: `docs/audit/gate_quota_diag_20261004.json` (md5 0d4054ea…); phụ D2 (thời điểm lãng phí): `docs/audit/gate_quota_diag_waste2022_20261004.json`, script `research/analysis/gate_offline_waste.py`.
- **Ràng buộc đã giữ:** 0 sửa .java, 0 build, 0 sim/Java/Kaggle; thuần Python offline; 2026 không đọc. RAM đỉnh 3,44 GB (< 4 GB ⇒ không cần lock; lock không tồn tại lúc chạy). Đĩa 6 038 → 5 986 MB (cache tự tạo `~/claude_master/1004/gqd`, 53 MB). Thời gian chạy 4 phút 15 giây (8 seed × G2 90d + (a)(b)(c)).
- **Dữ liệu:** pred.bin 8 seed (A1=42 md5 5dd6bb4c…, S7, S13 cd6d7b2e…, S21 0b541d22…, S99 5ef90e92…, S123 9b1dad90…, S777 25f738f7…, S2024 3be4fac4…; md5 đủ trong json); bins S1 `~/predwf_map_s1a2_x1_2021` (18 fold, horizonIdx=0 = manifest dataset sim); lưới `market.bin`; printDone + log `[GATE-RATIO]` của `n700-a1`, `gabl-seed7`, `gsb-s*`.

## 0. KẾT LUẬN (rủi ro trước)
1. **Gate offline tái lập Java ở mức GATE gần như bit-level.** Forward-fill 2 301 065 phút = log Java. Tổng pass off/sim (8 seed): lệch −0,1…+0,5% (A1 3 233/3 231). Pass theo quý 2022Q2–2025Q4 khớp ±0–4 lượt ở mọi seed (lệch phân bổ 21Q4/22Q1 ±15–19 lượt, tổng hai quý khớp — chưa truy); seen +0,10% (không tái lập `isTickerAvailable`). Tại 25 008 lệnh PREDICT (8 seed): sp và p15 khớp **chính xác** (max |Δ| = 0); recall phút vào 0,9915–1,0000, recall cặp (phút, symbol) 0,9925–0,9986; 0 lệnh ngoài top-24, 0 thiếu phút, 0 unmapped.
2. **Cổng D1 theo luật pre-reg: TRƯỢT** (S21: phút gate-mở 2022 offline/sim = 251/106 = ×2,37; A1 ×1,05 và S777 ×0,99 đạt; 2023–25 cả 3 arm ×1,00–1,02). Nguyên nhân xác định: luật so "phút gate-mở" với "phút VÀO lệnh"; tháng 5/2022 gate PASS nhưng lệnh bị chặn ở `TradeUtils.managerBudget` (U = margin/equity ≥ U_MAX ⇒ null) — lúc pass bị bỏ có trung vị 70–80 vị thế mở, margin ~21 k so với 24–29 vị thế / ~15,5 k lúc vào được. `[CONC-PC] blocked=0`. Ở mức gate (pass/quý vs log) bộ mô phỏng ĐẠT; luật D1 định nghĩa sai cho năm có trần vốn.
3. **Giả thuyết MASTER — SAI về cơ chế, ĐÚNG về chỗ.** Phương sai CAGR22 nằm ở quota năm sập, nhưng KHÔNG do "dồn nhiều symbol vào ít phút":
   - pass symbol-phút 2022 gần như hằng số giữa seed (507–599; corr với CAGR22 **−0,00**);
   - symbol-phút/phút-mở 2022 seed TỐT lại CAO hơn (A1/S99/S777 3,0–3,4 vs S21/S13 2,4); corr **+0,93**;
   - corr(phút gate-mở offline 2022, CAGR22) = **−0,91** (ngược dấu); corr(phút VÀO sim 2022, CAGR22) = +0,90 (tái lập con số 0,80 của SEEDBAND trên năm 2022);
   - cơ chế thật = **lãng phí theo THỜI GIAN**: seed xấu tiêu quota vào 11–31/05/2022 khi đã chạm U_MAX (pass vô ích 0–255, 100% rơi vào tháng 5; corr lãng phí22 vs CAGR22 **−0,92**), và (suy từ cơ chế cửa sổ 90 ngày, q_t chưa đo trực tiếp) q_t bị đuôi r tháng 5 đẩy lên nên các seed này **bị đói T6–T9**: pass 22Q3 = 15 (S21) … 108 (S99), corr với CAGR22 **+0,93**; lệnh vào T6–T9 corr **+0,96**; pass tháng 5 vs pass 22Q3 corr −0,86.
4. **D3 — dyn(sp):** pass rate giảm rất mạnh theo decile sp quần thể (decile 1 43,7e-5 → decile 2 3,5e-5 → decile 9 0,09e-5 → decile 10 0) nhưng gần PHẲNG theo rank trong phút (5,2–6,8e-5): decile sp chủ yếu phản ánh thời điểm (lúc cả rổ có sp thấp), không phải chọn coin trong phút. ROI lệnh thật A1: **không có bằng chứng dyn(sp) đang loại coin tốt** — Spearman(sp, ROI) −0,03; quintile sp 1 → 5: 5,13 / 2,94 / 4,24 / 3,42 / 2,04 %; decile quần thể 8 (sp ≈ 0,51, n 52) −18,8% [−26,0; −11,5]; nửa sp cao thua ở 2022 (−1,11 vs +2,94) và 2025 (−2,23 vs +4,66), thắng ở 2023 (+5,79 vs +3,95).
5. **D4:** chỉ (a) quota-theo-phút-p15 đạt tiêu chí pre-reg (CV phút-mở-2022 0,114 < 0,149; Jaccard 0,637 > 0,626; tổng 600 trong ±10% của 586) — **nhưng** nhận 13,5 symbol/phút (×4,9 so G2) và dời phân bổ năm (2023 139 vs 109, 2025 136 vs 179) ⇒ không phải "cùng quota" theo symbol-phút. (b) CV 0,189 (tệ hơn). (c) CV 0,420, tổng 765 = +31% so 586 (trượt cả hai). **Giới hạn quyết định:** D4 chỉ đếm phút gate-mở, không mô hình U_MAX; mục 3 cho thấy phương sai đến từ chuyển đổi pass→lệnh dưới trần vốn, nên ổn định phút gate-mở không suy ra ổn định lệnh (G2off CV 0,149 ≈ SIM 0,153).

## 1. Cơ chế tái lập (đọc code HEAD; chi tiết quan trọng)
| điểm | Java | offline |
|---|---|---|
| ứng viên | `time2SymbolPred.get(time)` = bins 15' (horizonIdx 0, sp = 1f − p0, bỏ NaN) forward-fill ra mọi phút market nếu t − mốc ≤ 15' (`WfoDataset:126-131,289-302`); sort tăng sp (`preprocessFundingData`) | như Java; 2 301 065 phút (= log) |
| K cap | `selectCands`: K=24 phần tử đầu, rank đếm trên toàn top-24 (cap-then-skip) | như Java |
| held | `isSymbolRunning` ⇒ `continue` TRƯỚC `createOrder` ⇒ không `noteCandidate`, không nạp buffer | xấp xỉ từ printDone cùng run: PREDICT khoá (start, end), level khác [start, end) |
| p15 | `predictionMap.get(ticker.startTime)`, null ⇒ return trước gate | pred.bin khớp phút (0 phút thiếu) |
| r, q_t | `r = p15/(max(0.26787, sp/0.15·1.2876)·1.55)` float; q = phần tử thứ `floor(pct·(m−1))` (nearest-rank) của r có ts ∈ [h−90d, h), tính ở truy vấn đầu mỗi giờ; warm-up 7 ngày / m=0 ⇒ 0.008 (`GateRatioBuffer:42-68`) | cây đoạn theo giờ giữ top-J (J=256; j tối đa 149) — chính xác cho phân vị đuôi |
| quyết định | `thr = (q·factor)·gs` float; REJECT ⇔ p15 < thr (`EntryGate:196-198`, `AIRejectFilter.evaluate`) | như Java, float32 |
| sàn 0.008 | **chỉ** là fallback warm-up và nhánh sp==null (BIG_DOWN/DCA). Sau warm-up nhánh PREDICT **không có sàn tuyệt đối**; "floor" duy nhất = DYN_MIN 0.26787 của factor | — |
| sau gate | `PumpDumpFilter` (OFF), tier (chỉ DCA), `managerBudget` (**U ≥ U_MAX ⇒ null**), conc-cap (blocked=0) | không mô hình ⇒ "lãng phí" = pass − lệnh thật |

## 2. D1 — validate (8 seed; cổng chốt cho A1/S21/S777)
| arm | seen off/sim | pass off/sim | recall phút 22–25 | recall cặp | phút 2022 off/sim | ×2022 | ×2023/24/25 |
|---|---|---|---|---|---|---|---|
| **A1** | 52 505 973 / 52 453 438 | 3 233 / 3 231 | 0,9915 | 0,9947 | 179 / 170 | 1,05 | 1,00/1,00/1,00 |
| S7 | 52 461 977 / 52 409 437 | 3 220 / 3 223 | 0,9965 | 0,9925 | 206 / 138 | 1,49 | 1,00/1,00/1,00 |
| S13 | 52 530 628 / 52 478 051 | 3 215 / 3 211 | 0,9964 | 0,9928 | 227 / 137 | 1,66 | 1,00/1,00/1,00 |
| **S21** | 52 694 313 / 52 641 724 | 3 169 / 3 157 | 0,9961 | 0,9979 | 251 / 106 | **2,37** | 1,01/1,00/1,00 |
| S99 | 52 352 143 / 52 299 703 | 3 384 / 3 369 | 1,0000 | 0,9986 | 177 / 163 | 1,09 | 1,00/1,00/1,00 |
| S123 | 52 508 436 / 52 455 875 | 3 240 / 3 234 | 0,9963 | 0,9957 | 217 / 131 | 1,66 | 1,00/1,00/1,00 |
| **S777** | 52 503 334 / 52 450 771 | 3 172 / 3 167 | 0,9983 | 0,9936 | 159 / 160 | 0,99 | 1,00/1,00/1,02 |
| S2024 | 52 556 310 / 52 503 752 | 3 224 / 3 221 | 0,9963 | 0,9949 | 218 / 126 | 1,73 | 1,00/1,00/1,00 |

Lệnh PREDICT không pass offline: 4–19/seed (0,1–0,6%), còn lại "pass". Pass theo quý vs log: xem json `D1.*.quarter` (2022Q2–2025Q4 lệch ≤ 4 lượt/quý). **Cổng: recall ĐẠT 3/3; tỉ lệ phút/năm ĐẠT A1, S777, TRƯỢT S21 (2022) ⇒ PASS=false theo luật.** Đây là lệch giữa "gate mở" và "vào được lệnh", không phải lỗi tái lập gate (mục 3).

## 3. D2 — lãng phí quota (2022; 2023–25 lãng phí 0–6/năm mọi seed)
| arm | CAGR22 | pass 2022 | phút gate-mở | phút vào sim | vào (khớp) | lãng phí | tỉ lệ | sym-phút/phút mean·p50·p90·max | pass 22Q3 | lệnh vào T6–T9 |
|---|---|---|---|---|---|---|---|---|---|---|
| S777 | 39,34 | 542 | 159 | 160 | 542 | 0 | 0,000 | 3,41·1·8,4·24 | 93 | 172 |
| S99 | 38,23 | 592 | 177 | 163 | 578 | 14 | 0,024 | 3,34·1·11,0·24 | 108 | 202 |
| A1 | 36,65 | 537 | 179 | 170 | 523 | 14 | 0,026 | 3,00·1·7,2·24 | 66 | 144 |
| S13 | 34,10 | 549 | 227 | 137 | 410 | 139 | 0,253 | 2,42·1·4,0·24 | 45 | 88 |
| S2024 | 32,98 | 557 | 218 | 126 | 419 | 138 | 0,248 | 2,56·1·4,0·24 | 64 | 99 |
| S123 | 31,56 | 546 | 217 | 131 | 415 | 131 | 0,240 | 2,52·1·5,0·23 | 35 | 74 |
| S7 | 31,34 | 507 | 206 | 138 | 392 | 115 | 0,227 | 2,46·1·3,0·23 | 43 | 80 |
| S21 | 29,24 | 595 | 251 | 106 | 340 | 255 | 0,429 | 2,37·2·3,0·24 | 15 | 33 |

Lãng phí 2022 nằm **100% trong 11/05–31/05/2022** (S21: 254/255), lúc trung vị 70–80 vị thế mở / margin 20,5–21,4 k (vào được: 24–29 vị thế / 15,2–16,3 k) ⇒ trần U_MAX. Pass tháng 5: S21 388, S13 277, S2024 271, S123 266, S7 257 vs A1 192, S99 192, S777 177.

**Tương quan (n = 8, Pearson / Spearman) với CAGR22:** pass 2022 −0,00/−0,14 · phút gate-mở offline 2022 **−0,91/−0,76** · phút vào sim 2022 +0,90/+0,74 · lệnh vào 2022 **+0,96/+0,90** · lãng phí 2022 **−0,92/−0,75** · tỉ lệ lãng phí −0,94/−0,76 · sym-phút/phút 2022 **+0,93/+0,86** · pass tháng 5 −0,89/−0,76 · pass 22Q3 +0,93/+0,93 · lệnh T6–T9 +0,96/+0,93. Phụ: corr(phút gate-mở, sym-phút/phút) 2022 = −0,92.
**Đọc:** quota năm 2022 (số pass) không đổi giữa seed; khác nhau ở **thời điểm** tiêu quota. Seed nào có đuôi r tập trung trong cú sập tháng 5 tiêu quota khi đã kín vốn (pass vô ích), rồi q_t (90 ngày) bị chính các r đó nâng ⇒ ít pass T6–T9 lúc có vốn. "Dồn" (nhiều symbol/phút) đi CÙNG chiều CAGR22, không ngược. n = 8 ⇒ chỉ báo, không phải chứng minh nhân quả; nhưng chuỗi cơ chế (U_MAX chặn ⇒ q_t cao ⇒ đói) khớp từng bước.

## 4. D3 — hiệu ứng dyn(sp)
**Pass rate (×1e-5 / ô ứng viên hợp lệ, 2022–25 sau warm-up) theo decile sp** — biên decile từ A1: 0,305 / 0,336 / 0,363 / 0,390 / 0,419 / 0,452 / 0,489 / 0,530 / 0,580.
| decile | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| A1 | 43,66 | 3,53 | 2,24 | 2,01 | 2,14 | 0,94 | 0,98 | 1,11 | 0,09 | 0 |
| min–max 8 seed | 43,2–45,2 | 3,1–3,7 | 1,8–2,8 | 1,5–2,5 | 1,5–2,4 | 0,45–1,18 | 0,83–1,33 | 0,60–1,35 | 0,06–0,30 | 0 |

Theo rank trong phút (A1): 1–3 **6,00** · 4–8 5,24 · 9–16 5,35 · 17–24 6,13 (8 seed: 4,7–6,8). ⇒ Đúng là coin sp cao (score xấu) **khó qua hơn rất nhiều** theo mức tuyệt đối (decile 1 gấp ~12× decile 2), nhưng trong cùng phút gate gần như mở/đóng cả rổ: biến thiên chủ yếu theo THỜI ĐIỂM (phút sập ⇒ p15 cực trị ⇒ cả top-24 qua; sym-phút/phút max 24).

**ROI lệnh thật A1 (PREDICT, 2022–25, n = 2 652; profit = % margin):**
| nhóm sp | n | sp median | ROI mean [CI95] | win | PnL |
|---|---|---|---|---|---|
| decile quần thể 1 (sp < 0,305) | 2 042 | 0,201 | 3,94 [3,50; 4,38] | 0,874 | +74 436 |
| decile 2 | 165 | 0,321 | 4,09 [2,60; 5,57] | 0,836 | +3 897 |
| decile 3–4 | 199 | 0,35–0,38 | 2,25 / 2,86 (CI chứa 0) | 0,76–0,79 | +2 842 |
| decile 5–6 | 144 | 0,40–0,44 | 8,02 / 6,70 | 0,91 | +8 012 |
| decile 7 | 46 | 0,467 | 1,03 [−4,40; 6,45] | 0,783 | +436 |
| **decile 8** | 52 | 0,506 | **−18,75 [−26,0; −11,5]** | 0,385 | −5 327 |
| decile 9 | 4 | 0,533 | 7,25 | 1,0 | +160 |
| quintile trong lệnh 1→5 | 531×5 | 0,11→0,38 | 5,13 / 2,94 / 4,24 / 3,42 / 2,04 | 0,92→0,79 | 21,6k/19,9k/21,0k/13,0k/8,9k |

Spearman(sp, ROI) = −0,03. Theo năm (nửa sp thấp vs cao, ROI mean): 2022 +2,94 vs **−1,11**; 2023 +3,95 vs **+5,79**; 2024 +4,57 vs +3,86; 2025 +4,66 vs **−2,23**. ⇒ Không có bằng chứng dyn(sp) đang loại coin TỐT; lệnh sp cao lọt qua không tốt hơn (kém ở 2022/2025 và đuôi decile 8). Không đo được ROI của ứng viên bị loại (cần giá + exit), nên kết luận chỉ một chiều.

## 5. D4 — 3 cơ chế quota thay thế (CHỈ ĐẾM; held = printDone từng seed; không mô hình U_MAX)
Hiệu chỉnh theo ĐẾM chỉ trên A1 (target = 586 phút vào PREDICT thật 2022–25): ρ_a = 2,385e-4 (→ 586), ρ_b = 2,143e-4 (→ 586); áp nguyên cho 7 seed. (c) không hiệu chỉnh.

**Phút mở 2022 theo seed**
| cơ chế | A1 | S7 | S13 | S21 | S99 | S123 | S777 | S2024 |
|---|---|---|---|---|---|---|---|---|
| SIM (phút vào thật) | 170 | 138 | 137 | 106 | 163 | 131 | 160 | 126 |
| G2off (gate 90d hiện tại) | 179 | 206 | 227 | 251 | 177 | 217 | 159 | 218 |
| (a) phút, p15 | 134 | 181 | 150 | 177 | 135 | 159 | 145 | 163 |
| (b) phút, r_max | 116 | 158 | 152 | 199 | 130 | 155 | 113 | 158 |
| (c) sym-phút 365d | 136 | 283 | 264 | 426 | 158 | 276 | 121 | 321 |

**Tóm tắt (8 seed)**
| cơ chế | 2022 mean ± sd | CV 2022 | phút/năm 22/23/24/25 (mean) | tổng 22–25 | Jaccard 22–25 | Jaccard 2022 | sym/phút 2022 | tiêu chí pre-reg |
|---|---|---|---|---|---|---|---|---|
| SIM | 141,4 ± 21,6 | 0,153 | 141/109/131/178 | 560 | 0,656 | 0,486 | 3,28 | (tham chiếu) |
| G2off | 204,3 ± 30,4 | 0,149 | 204/109/131/179 | 623 | 0,626 | 0,465 | 2,76 | (nền) |
| (a) | 155,5 ± 17,7 | **0,114** | 156/139/170/136 | 600 | **0,637** | 0,549 | **13,51** | ổn định ✓, quota phút ✓ — symbol-phút ✗ (×4,9) |
| (b) | 147,6 ± 27,9 | 0,189 | 148/162/168/132 | 609 | 0,630 | 0,491 | 3,43 | ổn định ✗ (CV), quota ✓ |
| (c) | 248,1 ± 104,2 | 0,420 | 248/58/214/245 | 765 | 0,602 | 0,403 | 2,88 | ✗ / ✗ (+31%) |

Jaccard phút SIM vs G2off cùng seed: 0,77 (S21) … 0,99 (S777) — thấp đúng ở seed có lãng phí tháng 5.
**Đọc:** (a) giảm CV 2022 23% và tăng ổn định phút, nhưng là thay đổi thiết kế lớn (mọi ứng viên của phút mở được nhận ⇒ số symbol-phút ×4,9; phân bổ năm lệch khỏi B0: 2023 +27%, 2024 +30%, 2025 −24%). (b) — "trả quota dư" theo phút — KHÔNG ổn định hơn: đúng với D2 (dồn symbol không phải nguồn phương sai). (c) cửa sổ 365d làm 2022 tệ hơn nhiều (q_t neo vào 2021 ít đuôi ⇒ 2022 mở 121–426 phút). Không cơ chế nào giải quyết nguồn phương sai thật (pass dưới trần U_MAX ⇒ q_t cao ⇒ đói sau sập) vì cả 3 đều không biết trạng thái vốn.

## 6. Rủi ro + đề xuất cho MASTER (không tự quyết)
**Rủi ro:** (1) n = 8 seed — tương quan |0,9| là chỉ báo mạnh nhưng 1 sự kiện (05/2022) chi phối; DEV chỉ có 1 cú sập kiểu này. (2) Chuỗi "q_t cao ⇒ đói T6–T9" suy từ cơ chế + tương quan, chưa đo q_t theo giờ giữa seed. (3) Held xấp xỉ bằng printDone ⇒ D4 dưới cơ chế khác dùng sổ lệnh B0 của chính seed (sai số bậc 2). (4) Lệch phân bổ 21Q4/22Q1 ~15 pass chưa truy (tổng khớp).
**Đề xuất:**
- (P1) Vòng Java pre-reg "**quota theo năng lực vốn**": chỉ nạp r vào buffer (q_t) — và/hoặc chỉ đếm pass vào quota — khi `managerBudget` khả dụng (U < U_MAX). Kỳ vọng: pass tháng 5 không tiêu quota vô ích, q_t T6–T9 không bị nâng. Đo trên ≥ 3 seed (A1, S21, S777) so với dải 8 seed (P1 của SEEDBAND); thước MTM ngày ghép cặp. Không đổi pct.
- (P2) Biến thể rẻ hơn để so cùng vòng: q_t loại khỏi buffer các r của phút có U ≥ U_MAX (live dùng chung `GateRatioBuffer` ⇒ cần thêm cờ, không đổi công thức). Nếu không muốn đụng gate: chẩn đoán U_MAX (lever SIZE ⇒ thước MTM ngày) trên dải seed.
- (P3) Không theo (b), (c). (a) chỉ nếu có thêm quy tắc chọn symbol trong phút mở (top-c, c chốt trước) — vòng riêng.
- (P4) Từ nay báo tách "phút gate-PASS" và "phút VÀO" (luật D1 của vòng này trộn hai thứ); thêm vào log cuối sim số pass bị `managerBudget` null theo quý (đọc-only counter, `TickDecisionLog.D_NO_BUDGET` đã có nhưng tắt).
- (P5) `gate_offline.py` dùng được làm thước offline cho mọi lever tầng gate (pct/K/W/sp-factor): khớp log pass/quý; chi phí ~30 giây/seed. Khi so lever, phải báo cả lãng phí dưới U_MAX (cần held từ run thật).

## 7. Tái lập
`python3 research/analysis/gate_offline.py prep` (cache `~/claude_master/1004/gqd/cand_base.npz`) → `python3 research/analysis/gate_offline.py all` (json) → `python3 research/analysis/gate_offline_waste.py` (thời điểm/vị thế của lãng phí 2022). Lệch pre-reg: không đổi định nghĩa/tiêu chí/seed sau khi thấy số; phân tích thời điểm lãng phí (`gate_offline_waste.py`) và tương quan theo tháng/quý là **bổ sung sau khi thấy D1/D2** (mô tả, không là cổng).
