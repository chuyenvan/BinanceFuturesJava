# RESULT S1_K24 — selector S1 trong khung K24: **NO-GO cả 3 arm** (ARM-A GEOM, ARM-B OBJ24, ARM-C OBJ24+GEOM)

Ngày 2026-10-04. Pre-reg `docs/prereg/PREREG_S1_K24.md` (**`15ec9e18`**, chốt trước mọi tính toán) · STEP 0 `docs/audit/RANKBAND_K24_20261004.md` (`96da8f82`). Driver `research/analysis/s1k24_driver.py`, train `research/analysis/s1k24_train.py`; số máy `docs/result/s1k24.json`. 0 sửa `.java`/build · 0 Java sim trên Oracle · 0 chạm 242/shadow · DEV ≤ 2025.

## 0. Verdict
- **ARM-A GEOM@K24:** ΔCAGR22 **+0,73 pp** CI raw [−1,85; +3,22], inflate [−3,09; +4,42] ⇒ **C1 trượt**; C2/C3/C4 đạt ⇒ **NO-GO**.
- **ARM-B OBJ24 (ndcg@24 + rel10):** ΔCAGR22 **−0,64** [−4,33; +2,75] ⇒ C1, **C4 (1/4 năm)** trượt ⇒ **NO-GO**; điểm ước lượng **âm**.
- **ARM-C OBJ24+GEOM:** ΔCAGR22 **+0,40** [−3,87; +4,55] ⇒ C1, **C4 (2/4)** trượt ⇒ **NO-GO**; thấp hơn ARM-A (−0,33).
- **H1 bị bác ở tầng sim**: đổi objective sang ndcg@24 + rel10 không tăng PnL (B −0,64, C−A −0,33). **H2**: GEOM ở K24 = +0,73 (G42 +1,15, G7 +0,32) < K16 4v4 +1,82 ⇒ khớp **pha loãng** (STEP 0: GEOM thắng hạng 1–8, thua hạng 17–24), nhưng CI vẫn chứa 0.
- Kết cục đúng loại pre-reg dự báo "khả dĩ nhất" cho A; B và C thấp hơn kỳ vọng khai trước (+1,5 / +2,5).

## 1. Hash / parity (mọi run PASS: jar `7368be46`, mapper ≥ 800, bins_ok + sha khai, `SELECTOR_RANK_TOPK=24` trong prof_run)
| run | tag | bins sha256_concat | n | equity | md5 printDone |
|---|---|---|---|---|---|
| K42 / S7 / S13 / S21 (CTRL4) | s1k24-k42/-s7/-s13/-s21 | fad7a45a / 44fa768f / c8dc4ef6 / db80c79a | 3490 / 3529 / 3502 / 3509 | 140 755 / 148 051 / 140 219 / 140 738 | e6c38033 / df92fee5 / 789c8068 / f0ae5b96 |
| G42 / G7 (ARM-A) | n700-a3 / s1k24-g7 | 6171f2cc / a687bf2b | 3541 / 3542 | 147 276 / 143 752 | 69c55e70 / 0fb92635 |
| B42 / B7 (ARM-B) | s1k24-b42/-b7 | 9fe5618c / bd697183 | 3547 / 3568 | 141 519 / 138 005 | f7f56910 / d92ebaf3 |
| C42 / C7 (ARM-C) | s1k24-c42/-c7 | cd944ce8 / 82278abf | 3563 / 3573 | 143 544 / 144 680 | b77c1984 / 3ea27235 |
| A1 (B0@K24, tham chiếu) | n700-a1 | deploy 407e2aba | 3526 | 144 974 | d9abf35f |
Kernel `tools/kaggle_sim.py` HEAD md5 `8b60b00a` (assert), template label_firsthit, code_sha 15ec9e18. 9 kernel mới, ≤ 2 song song. Pred train (Oracle CPU aarch64, xgboost 3.2.0) md5: B42 f37870bd · B7 296970d6 · C42 8964ee12 · C7 ba95155e (~24–25'/arm).

## 2. Cổng trước sim
| cổng | kết quả |
|---|---|
| **G0** đường mặc định `s1k24_train.py` (topk 8, rel5, seed 42, keep9) | **PASS byte-identical**: sha256 file == `pred_s1a2x1` `2618fe1a…`, ts/sym/score/index bằng bit (6 573 909 dòng) |
| **G1a** MAP_PARITY map(deploy, pred_s1a2x1) | **PASS** 16/16 md5 == deploy |
| **G1b** tái sinh map G42 từ geom/kout | **PASS** sha `6171f2cc` == vòng GEOM |
| **G1c** bins mới G42/B42/B7/C42/C7 | **PASS** 16/16 file: (ts,sym) cùng thứ tự, p1..p3 y hệt, multiset p0/tick y hệt, "có score" == ORIG |
| **G2** Δedge@24 (TB 2 seed vs CTRL cùng seed, ticks ≥ 25 ứng viên) | **ĐẠT** cả hai: ARM-B **+0,31 pp** (B42−K42 +0,25 [−0,27; +0,86], B7−S7 +0,37 [−0,05; +0,87]); ARM-C **+0,61** (C42−K42 +0,58 [−0,08; +1,36], C7−S7 +0,65 [+0,01; +1,36]) |
G2 chi tiết (chỉ báo cáo): OBJ24 tăng edge **đỉnh** (Δedge@8 B +1,0…+1,9, C +2,7…+3,9) nhưng **giảm** edge dải 17–24 (B −0,45/−0,05, C −1,11/−0,80) — ngược cơ chế H1 (kỳ vọng cải thiện dải 17–24).

## 3. Bảng nhóm (TB seed; cửa sổ 2022+; maxDD/UW = MTM phút; n/năm = lệnh đóng 2022–25 / 4)
| nhóm | n/năm | CAGR22 % | maxDD MTM (worst seed) | Calmar22 | UW ngày | win % | SL % | ROI/lệnh % | ΣPnL 22–25 k |
|---|---|---|---|---|---|---|---|---|---|
| **CTRL4@K24** | 728 | 36,04 | −21,67 (−22,00) | 1,663 | 135 | 85,1 | 15,6 | 4,01 | 100,8 |
| ARM-A GEOM | 736 | 36,77 | −20,37 (−20,82) | 1,806 | 131 | 85,3 | 15,3 | 4,23 | 103,9 |
| ARM-B OBJ24 | 740 | 35,40 | −21,08 (−21,22) | 1,679 | 116 | 85,0 | 15,5 | 4,00 | 98,1 |
| ARM-C OBJ24+GEOM | 743 | 36,44 | −20,51 (−20,61) | 1,777 | 116 | 85,1 | 15,3 | 4,14 | 102,5 |
| A1 B0@K24 (tham chiếu) | 732 | 36,65 | −22,21 | 1,650 | 117 | 85,4 | 15,4 | 4,07 | 103,4 |
Từng seed CAGR22: K42 35,64 · S7 37,37 · S13 35,51 · S21 35,64 · G42 37,19 · G7 36,36 · B42 35,82 · B7 34,97 · C42 36,31 · C7 36,58.

## 4. Δ vs CTRL4@K24 (paired block-10d NREP 2000 seed 20260905; inflate √(2 ln 3) = 1,4823)
| contrast | ΔCAGR22 pp | CI raw | **CI inflate** | ΔPnL k | CI raw | CI inflate |
|---|---|---|---|---|---|---|
| **ARM-A − CTRL4** | **+0,73** | [−1,85; +3,22] | [−3,09; +4,42] | +3,1 | [−2,6; +8,8] | [−5,3; +11,6] |
| **ARM-B − CTRL4** | **−0,64** | [−3,13; +1,65] | [−4,33; +2,75] | −2,7 | [−8,4; +2,6] | [−11,1; +5,1] |
| **ARM-C − CTRL4** | **+0,40** | [−2,48; +3,20] | [−3,87; +4,55] | +1,7 | [−5,5; +9,3] | [−8,9; +13,0] |
| chỉ báo cáo: ARM-C − ARM-A | −0,33 | [−2,35; +1,69] | | −1,4 | | |
| chỉ báo cáo: ARM-C − ARM-B | +1,04 | [−2,26; +3,83] | | +4,4 | | |
| chỉ báo cáo: B42 − A1 (cùng môi trường CPU, seed 42) | −0,82 | [−3,74; +1,80] | | −3,5 | | |
| chỉ báo cáo: A1 − CTRL4 | +0,61 | [−1,14; +2,33] | | +2,5 | | |
Từng seed vs CTRL4: G42 +1,15 · G7 +0,32 · B42 −0,21 · B7 −1,07 · C42 +0,27 · C7 +0,54 · (CTRL: K42 −0,40, S7 +1,33, S13 −0,53, S21 −0,40).

## 5. Theo năm / quý
ROI năm % (MTM equity) CTRL4 2022/23/24/25 = 5,5 / 68,4 / 46,1 / 31,9. **ΔROI pp:** ARM-A +0,73 / +1,29 / **−2,88** / +3,56 · ARM-B **−2,08 / −2,45** / +2,60 / **−0,28** · ARM-C **−0,48** / +0,01 / **−0,71** / +2,80.
ΣPnL đóng lệnh (TB seed, k) 2022/23/24/25: CTRL4 2,3 / 30,2 / 33,9 / 34,4 · A 2,6 / 31,1 / 32,2 / 38,1 · B 1,4 / 28,6 / 34,6 / 33,5 · C 2,1 / 30,1 / 33,2 / 37,1.
Quý (ΔΣPnL k vs CTRL4): A dương 10/16 quý, lớn nhất 25Q1 +1,2 / 25Q3 +1,0 / 25Q4 +1,1, âm 24Q1 −1,2; C: **25Q1 +2,8** chiếm > 100 % ΔPnL toàn kỳ (+1,7k); B: 23Q2 −1,0, 25Q4 −1,6.
⇒ Phần dương của A/C dồn **2025** (đúng mẫu reaudit: tín hiệu S1 mới chỉ hiện 2024–25); 2022–24 gộp âm ở cả 3 arm (C5).

## 6. Luật GO (§6 pre-reg)
| điều kiện | ARM-A | ARM-B | ARM-C |
|---|---|---|---|
| C1 ΔCAGR22 > 0, CI-inflate > 0 | FAIL (+0,73; [−3,09; …]) | FAIL (−0,64) | FAIL (+0,40; [−3,87; …]) |
| C2 maxDD MTM ≥ −40 % mọi seed | PASS −20,8 | PASS −21,2 | PASS −20,6 |
| C3 Calmar22 ≥ 0,90 × CTRL4 | PASS 1,086× | PASS 1,010× | PASS 1,069× |
| C4 ≥ 3/4 năm ΔROI ≥ 0 | PASS 3/4 | **FAIL 1/4** | **FAIL 2/4** |
| C5 (báo cáo) ΔROI gộp 2022–24 ≥ 0 | −1,36 pp | −4,35 | −2,41 |
| **GO** | **NO** | **NO** | **NO** |

## 7. Kỳ vọng khai trước vs thực tế
| arm | kỳ vọng ΔCAGR22 | thực tế | CI raw nửa-độ-rộng |
|---|---|---|---|
| ARM-A | +1,0 | +0,73 | 2,5 pp (khớp ước 2,5) |
| ARM-B | +1,5 | **−0,64** | 2,4 |
| ARM-C | +2,5 | +0,40 | 2,8 |
MDE80 thực ≈ (1,96 × 1,48 + 0,84) × (2,5/1,96) ≈ **4,8 pp** (pre-reg ước 3,5–4) ⇒ P(GO) thực tế thấp hơn khai báo.

## 8. Đọc kết quả (thông tin, không đổi verdict)
1. **OBJ24 sai cơ chế**: offline edge@24 tăng nhờ **đỉnh** (edge@8 +1…+4 pp), dải 17–24 lại kém đi; trên sim, KEEP9+OBJ24 âm (−0,64) và GEOM+OBJ24 kém GEOM thường (−0,33). STEP 0 đã cho thấy ROI/lệnh dải 17–24 không thua dải 1–8 (3,47 vs 3,42 %) — "dải 17–24 thiếu huấn luyện" không phải nút thắt PnL. rel10 (gain 2⁹−1 cho decile đỉnh) dồn model vào top-decile, không phải dải 17–24.
2. **GEOM pha loãng ở K24** (H2): K16 4v4 +1,82 → K24 2 seed +0,73; seed G7 chỉ +0,32. Cơ chế từ STEP 0: GEOM thắng hạng 1–8, thua 17–24. Vẫn cùng dấu dương, CI chứa 0 — không đủ bằng chứng, không bác.
3. **B0 deploy@K24 (A1) − CTRL4 = +0,61** và B42 − A1 = −0,82: B0 lại là realization trên trung bình retrain (như S1_RETRAIN_NOISE ở K16); so sánh selector với A1 thay vì CTRL4 sẽ thiên lệch âm ~0,6 pp — xác nhận chọn CTRL4@K24 làm nền.
4. Mọi lợi ích dương (A, C) dồn **2025** (25Q1/Q3/Q4); 2022–24 âm gộp ở cả 3 arm ⇒ cùng mẫu "chỉ 2024–25" của reaudit; DEV không phân xử được.

## 9. Lệch pre-reg / quy trình (ghi thật)
- Thứ tự: 2 kernel CTRL đầu (K42, S7) được push 05:27, **trước** commit STEP 0 (`96da8f82`, ~05:33); STEP 0 đã chạy xong 05:25 trước khi push, không ảnh hưởng arm. Mọi arm/luật giữ nguyên pre-reg.
- Sửa lỗi code trước khi đo arm (không đổi định nghĩa): `check_map` so p1..p3 thiếu `equal_nan` (p1..p3 toàn NaN) và chỉ số cột "co score" — sửa trước khi map B/C; G1c G42 chạy lại PASS.
- Lock `oracle_heavy.lock` cũ (0 byte, 10-03 23:03, không có tiến trình nặng) bị coi là stale và ghi đè khi train; đã xoá sau train và sau score.
- ARM-B/C train Oracle **CPU**, CTRL4/GEOM train Kaggle **GPU** (khai trước §3). Đối chứng cùng môi trường B42 − A1 = −0,82 cùng dấu với B42 − CTRL4 (−0,21) ⇒ không có dấu hiệu lệch môi trường làm đổi kết luận.
- Commit ghi `Co-Authored-By: Claude Opus 5.5` (model thực chạy) thay vì dòng "Fable 5.1" trong brief.

## 10. Rủi ro còn lại
- n = 2 seed/arm, 4 seed nền; σ seed CAGR@K24 (CTRL4) ≈ 0,89 pp; CI thời gian ±2,5 pp raw chặn mọi hiệu ứng < ~4,8 pp sau inflate.
- MTM phút dùng close 1m (cận dưới DD). DEV đã nhìn ~37 lần; 2026 niêm phong chưa dùng.
- STEP 0: hạng BIG_DOWN/DCA không kiểm được (symbolPred ≠ điểm S1).

## 11. Đề xuất cho MASTER (không tự quyết)
1. Đóng hướng **đổi objective/relevance S1** (OBJ24, rel10) trên DEV — âm ở KEEP9, kém GEOM thường.
2. GEOM@K24 giữ trạng thái "CHƯA ĐỦ, dương nhất quán" (6/6 run GEOM dương vs nền cùng K: 4 ở K16 vs CTRL K42+S7, 2 ở K24 vs CTRL4); chỉ kiểm tiếp trên dữ liệu mới (shadow #2 / 2026), không tune thêm trên DEV.
3. Nếu làm S1_V2 (G2 funding/OFI) trong khung K24: dùng CTRL4@K24 của vòng này làm nền (đã có 4 printDone, MTM cache `~/claude_master/1004/s1k24/mtm.json`); cân nhắc ≥ 3 seed/arm vì MDE inflate thực ~5 pp.
4. Lever dải 17–24 nếu còn muốn thử nên nhắm **size/SL** (STEP 0: ROI phẳng, SL tăng 14→17 %, margin/lệnh ½) chứ không phải thứ hạng.
