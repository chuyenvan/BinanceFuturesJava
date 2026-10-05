# RESULT_N700 — Tăng số lệnh dưới luật owner MỚI: K24 vs pct nới, trên B0 và GEOM-K16

Ngày: 2026-10-04 (GMT+7). Pre-reg `docs/prereg/PREREG_N700.md` (commit **`00ca54b6`**, chốt TRƯỚC mọi kernel). Driver `research/analysis/n700_driver.py`; số máy: `docs/result/n700.json` (+ `.parity`). 0 sửa `.java`/build, 0 Java sim trên Oracle, 0 chạm 242/shadow. DEV ≤ 2025-12-30.

## VERDICT: **NO-GO cả 4 arm** theo luật §5 — không lever nào đủ điều kiện lên shadow theo luật đã khoá.
- **A1 (B0 + K24)** đạt 4/5 (maxDD, Calmar, năm, n/năm); **trượt c1**: ΔCAGR +3,08 pp CI-inflate [−6,7; +12,9]; ΔPnL +12,9k CI raw **[+2,0k; +24,0k]** (ngoài 0) nhưng CI-inflate (k=4) [−5,3k; +31,3k] chứa 0.
- **A2 (B0 + pct 0,99985)** trượt c1 và **c3** (Calmar22 = 0,71× B0); 2022 ΣPnL **âm** (−2,1k), UW 284 ngày, ROI/lệnh 2,25 % (B0 4,48 %).
- **A3 (GEOM + K24)** giống A1: đạt 4/5, trượt c1 (ΔCAGR +1,34 [−9,3; +11,8]). **A4 (GEOM + pct)** trượt c1, c3 (0,74×), c4 (2/4 năm).
- Độ bền qua model: K24 cùng dấu trên B0 và GEOM (+3,1 / +1,3 pp); pct cùng dấu (+1,3 / +2,4 pp) nhưng chất lượng tệ ở cả hai model.

## 1. Hash / parity
| mục | giá trị |
|---|---|
| kernel `tools/kaggle_sim.py` HEAD (NOWRITE242) | md5 `8b60b00a…` (assert) |
| jar | `7368be46…` (sim-jar-gdv2) — cả 7 run |
| **B0REF** (`n700-b0ref`) | n 2517, eq 131 908, md5 **`ff3ce513`** = `selab-p0`; printDone giống từng ô (0 ô lệch giá trị, 0 ô lệch chuỗi) ⇒ **PARITY PASS** (ảnh Kaggle hiện tại = ảnh B0) |
| A1 (`n700-a1`) vs `de-p2` (ảnh cũ) | md5 `d9abf35f` ≠ `6802c08e` nhưng **0 ô lệch giá trị** (5 ô chuỗi cột `volume`) ⇒ K24 cũ tái lập đúng giá trị |
| A2 / A3 / A4 md5 | `628d5ab7` / `69c55e70` / `30c6fff1`; Cổng 1 PASS cả 4 (override có trong `prof_run`, md5 ≠ nền; A3/A4 `bins_sha256` = `6171f2cc…` g42) |
| Bootstrap | MTM ngày (b+unP), paired block-10d, NREP 2000, seed 20260905, cửa sổ 2022-01-01…2025-12-30 (rebase 2021-12-31), inflate √(2 ln 4) = **1,665** |

## 2. Bảng 4 arm + 2 nền (n/năm = lệnh ĐÓNG 2022–25 / 4; CAGR22/Calmar22 = cửa sổ 2022+; maxDD/UW = MTM phút)
| arm | n tổng | **n/năm** | ΣPnL 22–25 (k) | CAGR toàn kỳ | **CAGR22** | **maxDD MTM** | UW (ngày) | Calmar | **Calmar22** | win % | SL % | ROI/lệnh % | lệnh mở p95/max | exposure TB/p95/max % | % ΣPnL lệnh 0h |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **B0** | 2517 | 521 | 90,4 | 34,31 | 33,56 | −17,68 | 87 | 1,940 | 1,898 | 85,9 | 14,3 | 4,48 | 12 / 55 | 3,3 / 18,2 / 48,7 | 42,3 |
| **G42** | 2502 | 517 | 99,7 | 36,35 | 35,85 | −17,69 | 87 | 2,054 | 2,026 | 86,3 | 13,7 | 4,80 | 12 / 55 | 3,2 / 17,3 / 50,5 | 42,6 |
| A1 B0+K24 | 3526 | **732** | 103,4 | 37,16 | 36,65 | −22,21 | 117 | 1,673 | 1,650 | 84,6 | 16,0 | 4,07 | 19 / 83 | 4,3 / 23,0 / 53,7 | 42,6 |
| A2 B0+pct | 5877 | **1242** | 90,2 | 33,91 | 34,89 | −26,05 | 284 | 1,302 | 1,339 | 80,1 | 21,0 | 2,25 | 28 / 91 | 9,4 / 33,4 / 55,5 | **54,6** |
| A3 G42+K24 | 3541 | **736** | 105,7 | 37,64 | 37,19 | −19,92 | 116 | 1,889 | 1,867 | 84,8 | 15,8 | 4,32 | 19 / 78 | 4,3 / 23,0 / 54,3 | 41,8 |
| A4 G42+pct | 5921 | **1253** | 103,5 | 36,84 | 38,22 | −25,63 | 190 | 1,438 | 1,491 | 80,3 | 20,8 | 2,36 | 28 / 90 | 9,4 / 33,9 / 55,5 | 52,5 |
Lệnh mở/exposure: time-weighted lưới phút, cửa sổ 2022+. 0h = `time_order ≤ 0` (đóng trong giờ vào; `F3.hour0`, toàn kỳ). win/SL/ROI-lệnh = thông tin (T3 không quyết).

## 3. Δ vs nền — CI (raw / inflate 1,665)
| contrast | ΔCAGR pp | CI raw | **CI inflate** | ΔPnL (k USDT) | CI raw | **CI inflate** | ΔmaxDD ngày pp | ΔCalmar ngày |
|---|---|---|---|---|---|---|---|---|
| **A1 − B0** | +3,08 | [−2,8; +9,0] | [−6,7; +12,9] | +12,9 | **[+2,0; +24,0]** | [−5,3; +31,3] | −5,6 | −1,00 |
| **A2 − B0** | +1,33 | [−12,5; +16,7] | [−21,6; +26,9] | −0,3 | [−40,4; +38,6] | [−67,0; +64,4] | −10,3 | −1,64 |
| **A3 − G42** | +1,34 | [−5,1; +7,6] | [−9,3; +11,8] | +6,0 | [−5,9; +17,3] | [−13,7; +24,8] | −4,7 | −1,22 |
| **A4 − G42** | +2,38 | [−11,9; +18,7] | [−21,4; +29,6] | +3,8 | [−38,3; +45,3] | [−66,4; +72,9] | −10,8 | −1,98 |
| chéo: G42 − B0 | +2,28 | | [−1,6; +6,5] | +9,3 | | [−1,0; +20,9] | +0,8 | +0,54 |
| chéo: A3 − B0 | +3,62 | | [−5,4; +13,3] | +15,2 | | [−5,6; +36,4] | −3,9 | −0,68 |
| chéo: A4 − B0 | +4,66 | | [−19,0; +31,8] | +13,1 | | [−58,7; +84,2] | −10,0 | −1,44 |
| chéo: A1 − A2 (K vs pct) | +1,75 | | [−20,2; +22,9] | +13,2 | | [−50,6; +74,7] | +4,8 | +0,64 |
ΔPnL = ΣPnL thực hiện theo ngày đóng (USDT danh nghĩa, size compound) — cùng khối bootstrap với ΔCAGR. CI của arm pct rộng ±13–15 pp raw vì tương quan lợi suất ngày với nền chỉ 0,78 (A1: 0,98) — sổ lệnh khác hẳn (chỉ 27 % lệnh B0 còn trong A2; A1 75 %).

## 4. Theo năm (năm ĐÓNG lệnh; ROI % = equity compound; maxDD MTM phút năm)
| năm | B0 n / ΣPnL k / ROI / DD | A1 | A2 | G42 | A3 | A4 |
|---|---|---|---|---|---|---|
| 2022 | 423 / 4,6 / 11,1 / −17,7 | 592 / 2,4 / 5,7 / −22,2 | 643 / **−2,1** / **−3,5** / −26,1 | 427 / 6,3 / 15,2 / −17,0 | 589 / 2,9 / 6,9 / −19,9 | 709 / 0,0 / 1,8 / −25,6 |
| 2023 | 526 / 25,1 / 54,1 / −4,3 | 756 / 30,5 / 69,0 / −5,1 | 1152 / 31,8 / 80,8 / −8,4 | 525 / 27,4 / 56,9 / −3,8 | 764 / 31,7 / 70,5 / −4,5 | 1159 / 32,5 / 78,3 / −8,6 |
| 2024 | 600 / 30,7 / 43,4 / −10,7 | 839 / 35,3 / 47,7 / −12,1 | 1649 / 29,5 / 44,6 / −15,2 | 587 / 30,4 / 40,8 / −10,5 | 836 / 32,9 / 43,8 / −12,6 | 1660 / 35,7 / 51,6 / −15,5 |
| 2025 | 534 / 30,1 / 29,5 / −15,6 | 742 / 35,2 / 32,0 / −18,0 | 1523 / 30,9 / 31,2 / −17,5 | 529 / 35,5 / 33,6 / −17,7 | 755 / 38,3 / 35,1 / −19,1 | 1483 / 35,2 / 32,5 / −19,9 |
ΔROI năm vs nền (pp) 2022/23/24/25: **A1** −5,4 / +14,8 / +4,3 / +2,5 · **A2** −14,6 / +26,6 / +1,3 / +1,7 · **A3** −8,4 / +13,6 / +2,9 / +1,5 · **A4** −13,4 / +21,4 / +10,8 / −1,1.
⇒ Mọi lever tăng n **đều thua nặng năm 2022** (năm gấu) và thắng chủ yếu nhờ 2023; hiệu ứng tập trung 1 năm.

## 5. Verdict từng điều kiện (§5, vs nền của arm)
| điều kiện | A1 | A2 | A3 | A4 |
|---|---|---|---|---|
| c1 ΔCAGR hoặc ΔPnL: CI-inflate > 0 | **FAIL** (ΔPnL raw đạt, inflate không) | FAIL | FAIL | FAIL |
| c2 maxDD MTM ≥ −40 % (toàn kỳ & 2022+) | PASS −22,2 | PASS −26,1 | PASS −19,9 | PASS −25,6 |
| c3 Calmar22 ≥ 0,80 × nền | PASS 0,87× | **FAIL 0,71×** | PASS 0,92× | **FAIL 0,74×** |
| c4 ≥ 3/4 năm ΔROI ≥ 0 | PASS 3/4 | PASS 3/4 | PASS 3/4 | **FAIL 2/4** |
| c5 n/năm ≥ 700 | PASS 732 | PASS 1242 | PASS 736 | PASS 1253 |
| **GO** | NO | NO | NO | NO |

## 6. Kỳ vọng khai trước vs thực tế
- A1: khớp mọi kỳ vọng điểm (n 732, maxDD −22,2, Calmar 0,87×, 2022 âm) **trừ độ rộng CI**: pre-reg ước nửa-độ-rộng ΔCAGR raw 2–3 pp, thực tế **5,9 pp** (inflate 9,8 pp) ⇒ MDE ≈ +10 pp CAGR — lever K24 (+3 pp) **không thể** vượt luật c1 với thước này trên DEV 4 năm. Lỗi ước lượng là của pre-reg (lấy từ S1_GEOM, nơi sổ lệnh gần như trùng nền).
- A2: n **+138 %** (5877 vs 2517; ước +48 % từ AUDIT_CHAIN_AND_N là sai xa — khoá audit dùng sổ B0; pct nới đổi hẳn sổ lệnh, chỉ 27 % lệnh B0 còn lại). Chất lượng sụt đúng hướng lịch sử nới gate (G1/D2): ROI/lệnh ½, SL +6,7 pp, thời gian có lệnh mở 34 → 61 %, phần ΣPnL lệnh 0h 42 → 55 % (nhạy giá khớp phút sập hơn).

## 7. Lever nào đáng đưa lên shadow
- **Theo luật đã khoá: không lever nào.** Không đổi profile live/shadow.
- Thông tin cho owner (không phải đề xuất theo luật): nếu owner chấp nhận chỉ tiêu PnL ở mức raw (k=1) thay vì inflate k=4, **K24 (A1) là ứng viên duy nhất** — ΔPnL raw CI [+2,0k; +24,0k], maxDD −22 % (≪ 40 %), Calmar 0,87×, n 732/năm, bền qua model (A3 cùng dấu); cái giá: 2022 ROI 5,7 vs 11,1 %, UW 87 → 117 ngày, lệnh mở p95 12 → 19. Đây là quyết định chính sách (đổi luật sau khi thấy số) ⇒ nếu làm phải ghi rõ là amendment hậu kiểm, và shadow là phép thử thật.
- **pct nới (A2/A4): không nên** — vượt mục tiêu n (×2,4) nhưng Calmar −30 %, 2022 âm, UW 284 ngày, crash-sensitivity tăng; không có dấu hiệu lợi nhuận (ΔPnL A2 ≈ 0).
- Giới hạn: DEV đã nhìn ~28 lần; MTM phút dùng giá đóng nến 1m (cận dưới DD); K24 và pct là cùng một lever độ rộng ống (AUDIT_CHAIN_AND_N) — pct đổi sổ lệnh nhiều hơn K ở cùng nền.
- Ghi chú quy trình: driver được chạy thử (`dryscore`, A1 := `de-p2`) SAU commit pre-reg để kiểm code; thiết kế/luật không đổi.
