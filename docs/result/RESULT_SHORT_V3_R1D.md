# RESULT_SHORT_V3_R1D — CONFIRMATION ENTRY (chờ W phút không đỉnh mới +0,7% rồi short TAKER)

Pre-reg: `docs/prereg/PREREG_SHORT_V3_R1D.md` (`c30a72b4`, chốt TRƯỚC đo) · Program: `PROGRAM_SHORT_V3.md` ADDENDUM 3 (`75dddd89`) · nguồn giả thuyết POST-HOC: R1c `e7c3e09d`
Script: `research/analysis/short_v3_r1d_confirm.py` (`scan` → `report`) · Số: `docs/result/RESULT_SHORT_V3_R1D.json` · per-trade: `~/claude_master/1002/r1d_cache/trades_r1d.csv` (ngoài repo).
DEV 2022–2025 (mọi cửa sổ t+W+1+1440 ≤ 2025-12-31 23:59 UTC ⇒ loại thêm **0** trigger; 2026 không đọc). 0 Java, 0 sửa .java, 0 chạm 242.
Stream lại 48 tháng (cache R1c không có H/L/C từng phút sau t+15), 3 proc ≈ 23 phút, lock `oracle_heavy.lock` = R1d.

## Kết luận: **NO-GO** — cả 2 ô gãy G1 (CI raw chứa 0), G2 (≤ 2/4 năm), G5 (stress < 0); S_W15 gãy thêm G4 (25,05%) và G7 (tập bị loại TỐT hơn).
"+1,5%/lệnh của tập no-fill R1c" **không phải edge khai thác được**: nó gần như 100% là phần giá đã rơi TRONG chính cửa sổ điều kiện (t+1..t+W).
Chờ xác nhận rồi vào ⇒ còn −0,16% (W=15) / +0,02% (W=30). Theo ADDENDUM 3: **ĐÓNG short trên dữ liệu hiện có.**

| ô (k=2) | G1 net>0 ngoài CI raw & infl | G2 ≥3/4 năm + | G3 n ≥ 1500 | G4 SL ≤ 25% | G5 stress −0,10% > 0 | G6 LONG mirror ≤ 0 | G7 tập loại < ô | GO |
|---|---|---|---|---|---|---|---|---|
| S_W15 | ✘ −0,162 raw [−0,534; +0,201] | ✘ 1/4 | ✔ 2 703 | ✘ 25,05% | ✘ −0,262% | ✔ −0,561% | ✘ X +0,050 > −0,162 | ✘ |
| S_W30 | ✘ +0,021 raw [−0,290; +0,339] | ✘ 2/4 | ✔ 2 169 | ✔ 23,1% | ✘ −0,079% | ✔ −0,479% | ✔ X −0,009 < +0,021 | ✘ |

## 1. Bảng ô chính + đối chứng (net/lệnh, %; phí 0,056 + 0,056; funding exact; CI block 72h NREP 2000 seed 20260905; inflate nửa-độ-rộng × 1,18)
| ô | n | vào lệnh | net mean | median | CI raw | CI inflate | 2022 / 2023 / 2024 / 2025 | SL | TRAIL | TIME | win | gross | funding | held h | min | p1 | stress −0,10% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **S_W15** (short t+16) | 2 703 | 24,6% | **−0,162** | +2,41 | [−0,534; +0,201] | [−0,601; +0,267] | +0,50 / −0,18 / −0,29 / −0,22 | 25,05% | 49,7% | 25,3% | 62,6% | −0,018 | −0,031 | 12,0 | −13,8 | −10,3 | −0,262 |
| **S_W30** (short t+31) | 2 169 | 19,8% | **+0,021** | +2,35 | [−0,290; +0,339] | [−0,346; +0,396] | +0,82 / −0,48 / −0,09 / +0,07 | 23,1% | 49,0% | 27,9% | 63,1% | +0,163 | −0,030 | 12,9 | −12,3 | −10,4 | −0,079 |
| (a) L_W15 LONG mirror | 1 680 | 15,3% | −0,561 | +2,00 | [−1,037; −0,101] | [−1,122; −0,018] | −0,38 / −0,55 / −0,06 / −0,86 | 24,6% | 54,6% | 20,8% | 56,2% | −0,496 | +0,047 | 8,9 | −15,5 | −10,2 | −0,661 |
| (a) L_W30 LONG mirror | 1 201 | 10,9% | −0,479 | +2,08 | [−0,976; +0,026] | [−1,066; +0,117] | −0,49 / −0,53 / −0,49 / −0,45 | 25,2% | 56,6% | 18,2% | 58,0% | −0,433 | +0,066 | 8,6 | −10,4 | −10,2 | −0,579 |
| (b) X_W15 tập bị loại, short t+16 | 8 274 | 75,4% | +0,050 | +2,67 | [−0,152; +0,257] | [−0,189; +0,294] | +0,50 / +0,27 / −0,32 / +0,06 | 28,0% | 58,3% | 13,7% | 66,2% | +0,209 | −0,047 | 7,9 | −13,1 | −10,7 | −0,050 |
| (b) X_W30 tập bị loại, short t+31 | 8 808 | 80,2% | −0,009 | +2,62 | [−0,192; +0,185] | [−0,224; +0,220] | +0,37 / +0,14 / −0,30 / −0,00 | 27,3% | 56,4% | 16,2% | 65,4% | +0,156 | −0,053 | 8,8 | −15,2 | −10,6 | −0,109 |
| (c) C_15 = no-fill R1c, short t+1 | 2 703 | — | +1,522 | +3,01 | [+1,173; +1,848] | [+1,110; +1,906] | +1,95 / +1,42 / +1,28 / +1,58 | 16,4% | 65,6% | 18,0% | 75,1% | +1,666 | −0,032 | 9,5 | −15,3 | −10,3 | +1,422 |
| (c') C_30 tập W30, short t+1 (chỉ báo cáo) | 2 169 | — | +2,286 | +3,23 | [+1,978; +2,607] | [+1,922; +2,665] | +2,66 / +2,03 / +1,86 / +2,50 | 11,8% | 71,1% | 17,1% | 80,6% | +2,426 | −0,028 | 9,3 | −15,3 | −10,3 | +2,186 |
| T_ALL (= S_TK24 R1c) | 10 977 | 100% | +0,170 | +2,75 | [−0,030; +0,369] | [−0,066; +0,405] | +0,54 / +0,04 / +0,04 / +0,19 | 27,6% | 60,2% | 12,2% | 66,9% | +0,317 | −0,036 | 7,3 | −15,8 | −10,4 | +0,070 |

C_15/C_30 dùng thông tin TƯƠNG LAI (t+1..t+W) để chọn lệnh vào tại t+1 ⇒ KHÔNG giao dịch được; chỉ là thước đo. T_ALL CI inflate ở đây dùng × 1,18 (R1c dùng × 1,67).
100% lệnh có coin trong funding store. 0 lệnh entry phải dùng close ffill (close t+W+1 luôn có). 0 cặp lệnh cùng coin chồng lấn ở cả 2 ô.

## 2. Theo năm (năm UTC của entry; net %/lệnh; SL-rate; stress −0,10%)
| năm | trigger | S_W15 n (vào%) | S_W15 net | SL | stress | S_W30 n (vào%) | S_W30 net | SL | stress | X_W15 | X_W30 | C_15 | C_30 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022 | 1 135 | 264 (23,3%) | +0,50 | 20,8% | +0,40 | 220 (19,4%) | +0,82 | 16,8% | +0,73 | +0,50 | +0,37 | +1,95 | +2,66 |
| 2023 | 1 555 | 418 (26,9%) | −0,18 | 24,2% | −0,28 | 343 (22,1%) | −0,48 | 25,7% | −0,58 | +0,27 | +0,14 | +1,42 | +2,03 |
| 2024 | 2 468 | 639 (25,9%) | −0,29 | 26,3% | −0,39 | 524 (21,2%) | −0,09 | 24,8% | −0,19 | −0,32 | −0,30 | +1,28 | +1,86 |
| 2025 | 5 819 | 1 382 (23,7%) | −0,22 | 25,5% | −0,32 | 1 082 (18,6%) | +0,07 | 22,8% | −0,03 | +0,06 | −0,00 | +1,58 | +2,50 |
Chỉ 2022 dương rõ ở cả 2 ô; 2023–2025 ≈ 0 hoặc âm. Sau stress: 1/4 năm dương ở cả 2 ô. Tỉ lệ vào lệnh ổn định theo năm (S_W15 23–27%, S_W30 19–22%; LONG mirror 15% / 11%).

## 3. Phân rã "edge mất do vào trễ" = (c) − ô chính (cùng tập lệnh, chỉ khác giờ vào)
| W | C_W (vào t+1) | S_W (vào t+W+1) | C − S | trong đó gross | funding | phần edge mất | trôi giá trong lúc chờ P_{t+W+1}/P_{t+1} − 1 (mean / median) | SL C → S |
|---|---|---|---|---|---|---|---|---|
| 15 | +1,522 | −0,162 | **+1,684** | +1,684 | −0,000 | **111%** | **−1,68% / −1,37%** | 16,4% → 25,0% |
| 30 | +2,286 | +0,021 | **+2,265** | +2,263 | +0,002 | **99%** | **−2,31% / −1,92%** | 11,8% → 23,1% |
Tập bị loại: trôi giá lúc chờ +0,25% (W15) / +0,24% (W30).
- Phần chênh C − S trùng gần như tuyệt đối với mức giá đã rơi trong lúc chờ (1,684 vs 1,68; 2,265 vs 2,31). Điều kiện "không lên +0,7% trong W phút" chọn ra
  các đường giá ĐÃ rơi trong W phút đó; đo từ t+1 thì phần rơi ấy được tính vào lợi nhuận — là **look-ahead bằng điều kiện chọn đường đi**, không phải edge.
  Sau khi điều kiện đã biết (t+W+1), phần còn lại của đường giá ≈ 0 (−0,16 / +0,02), tức xác nhận KHÔNG mang thông tin về phần giá sau đó.
- W=30 "tốt hơn" W=15 (+0,021 vs −0,162; SL 23,1 vs 25,05%) nhưng chênh nằm gọn trong CI (raw ±0,31–0,37) và lệnh W30 ⊂ W15; C − S tăng từ 1,68 lên 2,27 —
  chờ lâu hơn chỉ "đẩy" thêm phần giá đã rơi vào thước đo look-ahead, phần còn khai thác được vẫn ≈ 0.
- SL tăng từ 16% lên 23–25% khi vào trễ: cùng mức SL +10% nhưng tính từ giá vào thấp hơn ~1,7–2,3% ⇒ SL gần đường giá hơn.

## 4. Đối chứng
- (a) LONG mirror âm ở cả 2 W, 0/4 năm dương (L_W15 CI raw [−1,04; −0,10] ngoài 0) ⇒ chiều sau trigger vẫn nghiêng xuống, như R1/R1c. G6 đạt.
- (b) Tập bị loại: W=15 X +0,050 > S −0,162 ⇒ **G7 gãy** (lọc xác nhận còn chọn ngược); W=30 X −0,009 < S +0,021 (đạt nhưng chênh 0,03% ≪ CI).
- (c) C_15 tái lập đúng +1,5222% của R1c (xem sanity ii) — tức con số R1c không sai số học; nó sai về KHẢ NĂNG GIAO DỊCH.

## 5. Sanity (PASS cả 4)
- **(i) Tập S_W15 = tập no-fill R1c:** 2 703 = 2 703, lệch **0** trigger (|ΔLp| tương đối max 6e-13; cùng dữ liệu, cùng công thức, cùng xử lý NaN). Tập W30 ⊂ W15 (2 169).
- **(ii) Tái lập R1c:** C_15 = +1,52221% vs R1c no-fill +1,52221% (|Δnet| per-trade max 1,1e-16), phút & lý do exit trùng 100%;
  T_ALL = +0,16971% = R1c S_TK24 trên 10 977 (|Δ| max 1,1e-16, phút/lý do trùng 100%).
- **(iii) Causal + vec/loop:** nhiễu từ t+W+1 ⇒ điều kiện không đổi 21 954/21 954 (2 W × 10 977); nhiễu từ t+W+2 ⇒ P = close t+W+1 không đổi 21 954/21 954;
  nhiễu từ e+1441 ⇒ exit không đổi 54 885/54 885 (5 chân × 10 977); vec vs loop thuần 54 885 phép |Δ| < 1e-9, phút/lý do trùng 100%. Assert exit ∈ [e+1, e+1440], ≤ 2025-12-31 23:59.
- **(iv) 10 mẫu S_W15 + 5 mẫu X_W15 (seed 20260905), kiểm tay high t+1..t+15:**
| ô | sym | t UTC | close t | Lp | max high t+1..t+15 | phút đầu ≥ Lp | P t+1 | P t+16 | lý do | gross t+16 | gross t+1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S_W15 | GALAUSDT | 2023-01-06 20:03 | 0,0221 | 0,0222547 | 0,0221 | — | 0,02206 | 0,02189 | SL | −10,00% | −10,00% |
| S_W15 | REEFUSDT | 2024-03-02 09:02 | 0,002634 | 0,00265244 | 0,002645 | — | 0,002585 | 0,002546 | TRAIL | +7,38% | +8,78% |
| S_W15 | SAGAUSDT | 2024-04-19 14:07 | 4,2214 | 4,25094958 | 4,2244 | — | 4,1778 | 4,1029 | TIME | −4,19% | −1,98% |
| S_W15 | DODOXUSDT | 2024-06-04 15:26 | 0,231726 | 0,23334809 | 0,23289 | — | 0,229223 | 0,224375 | TIME | +1,98% | +2,36% |
| S_W15 | ALGOUSDT | 2024-11-15 16:15 | 0,1832 | 0,1844824 | 0,1839 | — | 0,1790 | 0,1805 | SL | −10,00% | −10,00% |
| S_W15 | ESPORTSUSDT | 2025-08-22 14:29 | 0,0916 | 0,0922412 | 0,0922 | — | 0,0913 | 0,0900 | TIME | −0,67% | +0,44% |
| S_W15 | B2USDT | 2025-10-29 00:13 | 1,4423 | 1,45239606 | 1,45 | — | 1,4383 | 1,3377 | TRAIL | +9,67% | +5,90% |
| S_W15 | FILUSDT | 2025-11-06 17:10 | 1,48 | 1,49036002 | 1,485 | — | 1,479 | 1,462 | SL | −10,00% | −10,00% |
| S_W15 | USUALUSDT | 2025-11-24 15:57 | 0,02736 | 0,02755152 | 0,02748 | — | 0,02733 | 0,02673 | SL | −10,00% | −10,00% |
| S_W15 | DAMUSDT | 2025-12-01 17:03 | 0,02253 | 0,02268771 | 0,02254 | — | 0,02193 | 0,02181 | TRAIL | +2,34% | +2,87% |
| X_W15 | MAVUSDT | 2023-09-28 14:36 | 0,2814 | 0,2833698 | 0,2927 | t+3 | 0,2791 | 0,2761 | TRAIL | +2,56% | +3,61% |
| X_W15 | RADUSDT | 2024-01-15 01:10 | 1,91 | 1,92337 | 2,00 | t+1 | 1,904 | 1,916 | SL | −10,00% | −10,00% |
| X_W15 | MERLUSDT | 2025-09-07 04:55 | 0,17646 | 0,17769522 | 0,17808 | t+3 | 0,17602 | 0,16802 | TIME | +13,19% | +17,01% |
| X_W15 | ZEREBROUSDT | 2025-09-07 22:46 | 0,02236 | 0,02251652 | 0,02281 | t+2 | 0,02245 | 0,02211 | TRAIL | +4,22% | +3,61% |
| X_W15 | NTRNUSDT | 2025-12-27 18:28 | 0,02918 | 0,02938426 | 0,03033 | t+1 | 0,02968 | 0,02993 | SL | −10,00% | −10,00% |
  Cả 10 S_W15: max high 15' < Lp ✔ (vd GALAUSDT highs 0,0221 / 0,02206 / … / 0,02185, max = 0,0221 < 0,0222547); cả 5 X_W15 có phút ≥ Lp ✔.
- Tháng thử 2024-03 (415 trigger, 1 proc, 94 s) chạy trước full; sanity tháng thử 0 lỗi, tập no-fill khớp 111/111, chân t+1 khớp R1c 100%.

## 6. Giới hạn
- **Nguồn giả thuyết POST-HOC** (R1c) — đã ghi trong pre-reg; kết quả NO-GO nên không có rủi ro "chọn sau khi thấy". Không holdout ngoài DEV; 2026 niêm phong (không dùng).
- **Slippage:** TAKER tại close t+W+1 (15–30' sau spike, thị trường đã nguội) ít trượt hơn entry t+1 của R1, nhưng chỉ có cột stress −0,10%; ô chính đã âm ở stress.
- Kiểm tra tháng thử 2024-03 vô tình in gross-mean 1 tháng (do dùng bản script kiểm cũ) SAU khi pre-reg đã push; không tham số/quy ước nào đổi sau đó.
- W=15 và W=30 lồng nhau ⇒ 2 ô tương quan; k=2 là cận dưới số phép thử của chuỗi R1→R1d (≥ 21 vòng pre-reg trên cùng dữ liệu).
- Không mô hình vốn/size/đồng thời; 2025 chiếm 51% lệnh S_W15; queue/fill không liên quan (TAKER).

## 7. Ý nghĩa cho chương trình
- 4 lớp trên cùng trigger R1 đều NO-GO: exit (R1), selector tại t (R1b), execution LIMIT (R1c), confirmation entry (R1d). Hướng sau trigger nghiêng xuống là thật
  (LONG âm ở mọi ô, mọi vòng) nhưng phần khai thác được sau phí/stress ≈ 0 và tập trung ở 2022.
- Quan sát "+1,5% ở tập no-fill" của R1c §10 là **artifact điều kiện-đường-đi** (đo từ t+1 trên tập chọn bằng t+1..t+15): phần chênh = đúng mức giá đã rơi trong cửa sổ chờ.
  Bài học quy trình: mọi "tập con định nghĩa bằng tương lai" phải được đo từ thời điểm thông tin có sẵn trước khi diễn giải là edge.
- Theo ADDENDUM 3: NO-GO ⇒ **ĐÓNG short trên dữ liệu hiện có**. Không thêm W/δ. Chỉ còn hướng data mới (fill thật/L2/liquidation forward).

## 8. Tái lập
`python3 research/analysis/short_v3_r1d_confirm.py scan --months 202403 --procs 1` → `scan --months all --procs 3` → `report`
(trigger qua `load_trig()` R1c: `~/claude_master/1002/r1_cache/trades_r1.csv` + `cand_*.parquet`; cache `~/claude_master/1002/r1d_cache/r1d_YYYYMM.parquet` + `meta_*.json`;
sanity so với `~/claude_master/1002/r1c_cache/trades_r1c.csv`; funding `/tmp/fund_cache.npz`; Aerospike `test.kline_1m_opt` 127.0.0.1:3222).
