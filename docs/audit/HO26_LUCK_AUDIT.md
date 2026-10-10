# HO26 LUCK AUDIT — kiểm "số may" holdout 2026H1 (K24+skipFull vs B0 K16)

Ngày 2026-10-10. Vai: agent AUDIT. Đối tượng: verdict `docs/result/ho26/HO26_VERDICT.md` (d0349248; scorer A b89575bf, B db4f3ce8). 0 sửa Java, 0 build, 0 Java sim trên Oracle, 0 chạm 242/shadow. Script `research/analysis/ho26_luck_audit.py`, JSON `docs/audit/HO26_LUCK_AUDIT.json`.

## PHẦN 1 — PRE-REG (commit TRƯỚC khi đo; không tune sau khi thấy số)

Đã biết trước khi viết (từ verdict, không phải đo mới): ΣPnL_S mean k24 10 229 / b0 9 590; tháng 6 ≈ 62% ΣPnL k24; T3–T4 gần như không lệnh. Không có số nào của A1–A6 đã được tính.

Chung: cửa sổ W = [2026-01-01 00:00, 2026-07-01 00:00) +07 (181 ngày). Run: `~/kaggle_sim/out/ho26-{k24,b0}-s-s<seed>` (stress in-sim 1,675%), seed ∈ {42,7,13,21,99,123,777,2024}. ΣPnL_S = Σ pnl printDone có `end` ∈ W (y scorer A). Ngày = ngày lịch +07. Cụm lệnh = nhóm dòng printDone cùng (sym, end); leg0 = dòng `start` nhỏ nhất của cụm.

### A1 — kiểm giá độc lập (Binance Vision)
- Nguồn: `data.binance.vision/data/futures/um/daily/klines/<SYM>USDT/1m/` (ĐỘC LẬP với ticker sim). Tải theo (sym, ngày UTC) cần, parse rồi xoá zip. 404 ⇒ thử tên trong `data/meta/symbol_lineage_v2.csv`; vẫn không có ⇒ "không có nguồn" (báo riêng, không tính khớp/lệch).
- Chân: mọi dòng printDone của `ho26-k24-s-s42` và `ho26-b0-s-s42` có `start` ∈ W (kiểm giá vào); có `end` ∈ W (kiểm giá thoát).
- Nến quyết định = kline Vision có open_time = `start` (đổi +07→UTC), lag 0 (CHÍNH). Chẩn đoán phụ lag −1/+1 phút (chỉ báo, không đổi chuẩn).
- Chân sập (theo Vision) ⇔ close/open − 1 ≤ −1% ở nến quyết định. Giá vào kỳ vọng = close × 1,01675 nếu sập, ngược lại close. KHỚP ⇔ |entry/kỳ vọng − 1| ≤ 1e-6. Báo % khớp, liệt kê lệch; đối chiếu cờ sập Vision với danh sách `[CRASH-PENALTY] leg sap` trong sim.out.
- Giá thoát = cột `tp` (kiểm trước: tp ≈ entry·(1+profit/100)). KHỚP ⇔ low·(1−1e-6) ≤ tp ≤ high·(1+1e-6) của kline open_time = `end`.
- Kiểm dữ liệu: (i) Vision: số phút thiếu/0/NaN trong các ngày đã tải; (ii) ticker sim (`~/kaggle_data_hpo/ticker_2026*.bin.gz`): số phút-chân thiếu giá hoặc giá 0 trong lúc chân mở (16 run stress); (iii) delist: với mọi symbol giao dịch trong W (16 run), ngày kline 1m Vision cuối cùng (S3 listing); delist trong W ⇔ ngày cuối < 2026-06-30; báo chân dính.

### A2 — phụ thuộc vài sự kiện (k24, b0; stress; 8 seed)
- Trên ΣPnL_S từng seed: (a) bỏ lần lượt từng tháng (theo tháng của `end`); (b) bỏ top-1/3/5 ngày có PnL realized (theo ngày `end`) lớn nhất; (c) bỏ đợt lớn nhất — đợt = cụm ngày có lệnh vào, tách khi ≥ 3 ngày liền không lệnh (EP_GAP 3 như scorer A), chân gán theo ngày `start`, bỏ đợt có ΣPnL lớn nhất. Báo mean, min, số seed > 0; kèm Δ k24−b0 ghép seed. Tỉ trọng tháng 6 = ΣPnL(end ∈ T6)/ΣPnL_S.

### A3 — bootstrap tuyệt đối
- r_d = return ngày MTM (181 giá trị) đúng thước scorer A (tái dùng `ho26_score_a` + cache U; tự kiểm: ROI tái lập = RESULT_A ≤ 1e-9 tương đối).
- Block bootstrap vòng (circular), block ∈ {5, 10} ngày, NREP 5000, `default_rng(20261010)`. ROI* = Π(1+r*) − 1; ΣPnL* = E0·ROI*. Từng seed; GỘP = mean 8 seed với CÙNG chỉ số block (giữ tương quan chéo seed). Báo P(ROI* ≤ 0), CI95 percentile, CI inflate (half-width × √(2 ln 2), k = 2 block).

### A4 — đối chứng ngẫu nhiên (tách thời điểm + chọn coin khỏi beta)
- Lịch: leg0 của 8 run `ho26-k24-s-*` có `start` ∈ W (mọi loại chân), giữ phút vào và notional = margin leg0. DCA KHÔNG mô phỏng (chỉ leg0).
- Tập ứng viên tại phút t: top-24 hạng S1 (bins `~/claude_master/1009/ho26/bins2026Ax/predict_wf_2026*.bin` = bins bundle sim-ho26a; sp = 1 − p0, bỏ NaN, sort tăng, mốc 15m gần nhất ≤ t và t − mốc ≤ 15'); không có ⇒ universe = symbol có close ticker sim tại t. Coin rút đều; nhiều leg0 cùng phút rút không lặp; coin không có close tại t ⇒ rút lại (≤ 50 lần). Không loại coin "đang giữ".
- Thoát = proxy `qsleeve_q0` (hàm `seg`: arm +7%, trail GAP 3%/STEP 0,5%, time-stop 168h, không DCA/funding/SL cứng), vào ở close ticker sim của nến quyết định; chi phí 0,1116% notional + 1,675pp nếu nến quyết định close/open−1 ≤ −1%. Chân chưa thoát tới 2026-06-30 23:59 +07 ⇒ đánh dấu theo close phút đó. PnL = notional × (px/E − 1 − phí).
- Thống kê CHÍNH: S_real = Σ_8seed Σ_leg0 PnL proxy với COIN THẬT (cùng proxy ⇒ cùng mô hình thoát). Đối chứng C1 "cùng phút, coin ngẫu nhiên": 1000 lần; C2 "phút ngẫu nhiên": cùng số leg0 mỗi seed, phút rút từ pool 4000 phút đều trong W (cố định, seed 20261010), coin ngẫu nhiên top-24, notional = hoán vị notional thật; 1000 lần. p một phía = (1 + #{S_ctrl ≥ S_real})/1001; k = 2 đối chứng (báo cả ngưỡng Bonferroni 0,025). Kèm: p từng seed; ΣPnL_S thật (sim, có DCA) chỉ để tham chiếu.
- Phân rã: beta ≈ mean C2; giá trị thời điểm ≈ mean C1 − mean C2; giá trị chọn coin ≈ S_real − mean C1.
- Hiệu chuẩn proxy 2026: pearson + lệch TB (pp) giữa proxy gross và `profit` printDone trên leg0 KHÔNG-DCA (cụm 1 chân) của 8 run k24-s.

### A5 — độ nhạy phí in-sim
- 8 kernel `aud26-k24-p267-s<seed>`: override y hệt `ho26-k24-s-*` trừ SIM_CRASH_ENTRY_PENALTY=0.0267; bundle sim-ho26a-bundle, jar sim-jar-nsel (b7c89f09), SIM_END_DATE=20260701, kernel = template `tools/kaggle_sim.py` HEAD (guard NOWRITE). Orchestrator `~/claude_master/1010/aud26/aud26_queue.py` (≤ 2 kernel toàn tài khoản, kiểm API trước mỗi lần đẩy). Parity tự động như ho26_queue (ok, jar, override, t26 181/181, pred md5, `[CRASH-PENALTY] SUMMARY penalty=0.0267`).
- Chấm: ΣPnL_S cửa sổ (end ∈ W), n, số seed > 0; Δ ghép seed vs `ho26-k24-s` (1,675%). Lưu ý: penalty áp từ 2021 ⇒ vốn đầu 2026 khác; báo kèm ROI realized = ΣPnL_S / (equity_start + Σ pnl end < T0).

### A6 — bối cảnh thị trường (Vision)
- Nguồn: `futures/um/monthly/klines/<SYM>/1h/` 2022-01 → 2026-06 (+ `1mo` để xếp hạng khối lượng). Top-50: mỗi tháng M, 50 symbol USDT-perp (loại stable: USDC, BUSD, TUSD, FDUSD, USDP, DAI) quote volume lớn nhất tháng M−1. Chỉ số EW: return giờ = mean return giờ các thành phần có giá ở cả 2 giờ.
- Cho BTC, ETH, EW50: return, maxDD (trên chuỗi giờ), số ngày (+07) return ≤ −5%, số giờ return ≤ −3% và số "đợt sập" = cụm giờ ≤ −3% gộp khi cách nhau < 24h — theo tháng. So 2026H1 với từng nửa năm DEV 2022H1…2025H2 (hạng 2026H1 trong 9 nửa năm) và mật độ /30 ngày.

### A7 — luật kết luận (khai trước)
- (a) EDGE vượt đối chứng: p(C1) < 0,025 VÀ p(C2) < 0,025.
- (b) PHỤ THUỘC SỰ KIỆN nếu bất kỳ: bỏ tháng 6 ⇒ mean ΣPnL_S(k24) ≤ 0 hoặc < 6/8 seed > 0; bỏ top-3 ngày ⇒ mean ≤ 0.
- (c) BETA: mean C2 > 0 và S_real − mean C2 < 50% S_real.
- Mức tin cậy: CAO nếu (a) và không (b), A3 gộp P(ROI ≤ 0) < 5% (block 10), A1 ≥ 99% khớp, A5 ≥ 6/8 seed > 0; THẤP nếu không (a) hoặc (b); còn lại TRUNG BÌNH.

## PHẦN 2 — KẾT QUẢ (sinh bởi `ho26_luck_audit.py report`)

### A1 — kiểm giá độc lập (Vision)

| cfg s42 | chân vào | % khớp vào (lag0) | lệch | không nguồn | lag −1/+1 % | chân thoát | % thoát ∈ [L,H] | lệch | cờ sập Vision×sim |
|---|---|---|---|---|---|---|---|---|---|
| k24 | 221 | 85,52 | 32 | 0 | 1,81 / 1,81 | 217 | 100,00 | 0 | {"both": 49, "vis_only": 1, "sim_only": 0, "none": 171} |
| b0 | 174 | 83,91 | 28 | 0 | 1,72 / 1,72 | 171 | 100,00 | 0 | {"both": 42, "vis_only": 1, "sim_only": 0, "none": 131} |

Vision: {"files": 328, "n404": 0, "rows_bad": 0, "zero": 0, "nan": 0, "missing_min": 0}. Ticker sim (16 run): {"legs": 3536, "legmin": 7967567, "miss": 624, "zero": 0, "nosym": 0, "legs_with_miss": 150, "miss_pct": 0.007831750897105728}. Delist trong W: []; list mới trong W: 40 symbol.

### A2 — phụ thuộc vài sự kiện (ΣPnL_S, 8 seed; mean [min] · số seed > 0)

| phép bỏ | k24 | b0 | Δ k24−b0 |
|---|---|---|---|
| total | 10 229 [8 359] · 8/8 | 9 590 [7 446] · 8/8 | 639 · 7/8 |
| drop_month_2026-01 | 6 917 [4 963] · 8/8 | 6 814 [5 075] · 8/8 | 103 · 2/8 |
| drop_month_2026-02 | 10 376 [7 720] · 8/8 | 9 448 [7 288] · 8/8 | 928 · 8/8 |
| drop_month_2026-03 | 9 748 [7 832] · 8/8 | 9 167 [7 106] · 8/8 | 582 · 7/8 |
| drop_month_2026-04 | 10 212 [8 359] · 8/8 | 9 785 [8 233] · 8/8 | 428 · 7/8 |
| drop_month_2026-05 | 10 007 [7 928] · 8/8 | 9 311 [7 107] · 8/8 | 696 · 6/8 |
| drop_month_2026-06 | 3 884 [1 864] · 8/8 | 3 426 [1 524] · 8/8 | 457 · 5/8 |
| drop_top_1 | 7 508 [5 836] · 8/8 | 7 375 [5 326] · 8/8 | 133 · 2/8 |
| drop_top_3 | 3 539 [1 696] · 8/8 | 4 173 [2 504] · 8/8 | -633 · 1/8 |
| drop_top_5 | 601 [-1 200] · 6/8 | 1 727 [236] · 8/8 | -1 126 · 1/8 |
| drop_ep | 6 333 [4 567] · 8/8 | 5 300 [3 496] · 8/8 | 1 033 · 8/8 |

Tỉ trọng tháng 6: k24 mean 0,63 [0,53..0,79]; b0 mean 0,65.

### A3 — block bootstrap return ngày MTM (NREP 5000, seed 20261010)

| block | cfg | GỘP P(ROI≤0) | CI95 ROI % | CI95 inflate | CI95 ΣPnL USD | P(ROI≤0) từng seed mean [min..max] |
|---|---|---|---|---|---|---|
| 5 | k24 | 0,0052 | 1,49 … 18,02 | 0,35 … 19,81 | 1 557 … 18 820 | 0,018 [0,001..0,057] |
| 5 | b0 | 0,0036 | 1,62 … 18,25 | 0,51 … 20,09 | 1 618 … 18 252 | 0,021 [0,000..0,079] |
| 10 | k24 | 0,0028 | 1,69 … 17,54 | 0,57 … 19,23 | 1 769 … 18 322 | 0,012 [0,002..0,044] |
| 10 | b0 | 0,0022 | 1,60 … 17,99 | 0,50 … 19,80 | 1 599 … 17 999 | 0,018 [0,000..0,078] |

Tự kiểm ROI tái lập vs RESULT_A: max |rel| 7.7e-09.

### A4 — đối chứng ngẫu nhiên (proxy thoát non-DCA, 1000 lần, ΣPnL USD gộp 8 seed)

|  | giá trị | p một phía | p5 / p50 / p95 |
|---|---|---|---|
| S_real (coin thật, proxy) | 50 921 |  |  |
| C1 cùng phút, coin ngẫu nhiên | 35 265 | 0,0030 | 26 027 / 35 504 / 44 175 |
| C2 phút ngẫu nhiên | -10 974 | 0,0010 | -27 158 / -10 714 / 4 866 |

Phân rã: beta (C2) -10 974 · thời điểm (C1−C2) 46 239 · chọn coin (thật−C1) 15 656. p từng seed C1 ['0,162', '0,091', '0,059', '0,430', '0,289', '0,429', '0,089', '0,060']; C2 ['0,004', '0,020', '0,002', '0,117', '0,120', '0,014', '0,002', '0,002'].
leg0/seed [220, 265, 270, 268, 256, 241, 245, 243]; bỏ {'nosym': 0, 'noprice': 0}; nguồn ứng viên {'top24': 4053, 'universe': 1}; thoát proxy coin thật {'trail': 1723, 'time': 258, 'mark': 27}. ΣPnL_S sim thật (có DCA) ['10 675', '10 821', '14 018', '8 359', '8 849', '8 528', '10 670', '9 912'].
Hiệu chuẩn proxy 2026 (leg0 không-DCA k24-s): n 1955, pearson 0,988, lệch TB -0,31 pp, |lệch| p50 0,00 pp.

### A6 — bối cảnh thị trường (Vision 1h; 2026H1 vs 8 nửa năm DEV 2022H1–2025H2)

| chuỗi | chỉ số | 2026H1 | DEV mean [min..max] | hạng (giảm dần) | mật độ /30 ngày 2026 vs DEV |
|---|---|---|---|---|---|
| BTC | ret | -33,26 | 18,06 [-59,00..83,07] | 8/9 |  |
| BTC | maxdd | -40,32 | -32,49 [-62,89..-20,86] | 8/9 |  |
| BTC | days_le5 | 2,00 | 4,38 [1,00..14,00] | 6/9 | 0,33 vs 0,72 |
| BTC | crash_h | 4,00 | 8,00 [1,00..20,00] | 7/9 | 0,66 vs 1,32 |
| BTC | episodes | 4,00 | 6,00 [1,00..14,00] | 6/9 | 0,66 vs 0,99 |
| ETH | ret | -47,17 | 7,98 [-72,23..57,84] | 8/9 |  |
| ETH | maxdd | -55,01 | -43,34 [-76,69..-23,26] | 7/9 |  |
| ETH | days_le5 | 10,00 | 11,88 [1,00..27,00] | 5/9 | 1,66 vs 1,96 |
| ETH | crash_h | 12,00 | 17,00 [2,00..43,00] | 5/9 | 1,99 vs 2,80 |
| ETH | episodes | 10,00 | 11,12 [2,00..20,00] | 4/9 | 1,66 vs 1,83 |
| EW50 | ret | -40,54 | -13,03 [-76,60..64,94] | 6/9 |  |
| EW50 | maxdd | -51,55 | -54,24 [-81,05..-33,66] | 5/9 |  |
| EW50 | days_le5 | 11,00 | 17,12 [5,00..29,00] | 7/9 | 1,82 vs 2,82 |
| EW50 | crash_h | 9,00 | 34,50 [12,00..76,00] | 9/9 | 1,49 vs 5,68 |
| EW50 | episodes | 8,00 | 20,62 [10,00..31,00] | 9/9 | 1,33 vs 3,40 |

Theo tháng 2026 (EW50: ret % / maxDD % / ngày ≤−5% / đợt sập): 01 -12,9/-23,5/2/1; 02 -14,8/-20,8/1/4; 03 -6,1/-16,9/3/0; 04 2,7/-9,9/1/0; 05 -8,5/-20,1/0/1; 06 -9,2/-18,1/4/2
BTC theo tháng 2026 ret %: 01 -8,3, 02 -19,0, 03 4,0, 04 12,7, 05 -3,6, 06 -20,4
Thành phần/giờ EW50: {"mean": 49.9, "min": 0.0, "max": 50.0, "n_pos": 39407, "n": 39408}; file 1h 2700 (404: 1).


### Sai khác so với pre-reg (khai minh bạch)
- A6: Vision KHÔNG còn file `1mo` sau 2024-02 (404) ⇒ xếp hạng khối lượng dùng tổng quote volume từ file `1d` của tháng M−1 (cùng định nghĩa, khác file nguồn). Lần chạy đầu với `1mo` bị bỏ (top-50 rỗng từ 2024-03), không xem như biến thể.
- A1x (dưới) là BỔ SUNG SAU KHI THẤY A1 — chỉ mô tả, không vào luật A7.
- A4: lỗi hạ tầng (NSMAX symbol ticker 760 → 900) sửa trước khi có số; không đổi định nghĩa.

### A1x — bổ sung mô tả: lệch giá vào trên 16 run stress
- 696 chân duy nhất (sym, phút): khớp 84,8%; 106 lệch dồn vào 29 phút (top: 05-22 15:00 ×12, 06-05 13:22 ×11, 06-05 13:19 ×10, 06-06 11:19 ×8, 06-04 08:22 ×6 …) — các phút biến động mạnh, chủ yếu T5–T6. Lệch trung bình +0,049% (trung vị +0,023%; 59 dương / 47 âm) ⇒ giá vào sim hơi CAO hơn Vision (bảo thủ), không thiên vị có lợi.
- Nguồn lệch: entry = close ticker sim 106/106; ticker sim ≠ close Vision ở 31% phút (52 565/168 480) của các (symbol, ngày) liên quan ⇒ ticker sim là nguồn giá khác Vision ở phút biến động (không phải lỗi gắn nhãn/lệch phút: lag ±1 chỉ khớp ~2%).
- Tác động bậc 1 (đổi giá vào → Vision, giữ notional + giá thoát): ΣPnL_S k24 mean 10 229 → 10 230 (Δ +1, [−45..+51]); b0 9 590 → 9 627 (Δ +37). Không đổi kết luận.
- Giá thoát: 100% nằm trong [low, high] Vision (388/388 chân s42). Cờ sập: 91/93 trùng; 2 chân Vision sập mà sim không (BTW 06-25 20:53 …) — sim không phạt ⇒ thiên vị có lợi ~1,6% × 2 chân, không đáng kể. Phút thiếu giá ticker sim khi chân mở 0,008% (624/7,97M); 0 giá 0; 0 symbol delist trong W (153 symbol).

### Đọc A4 — cảnh báo
- p gộp C1 = 0,003 nhưng p từng seed 0,06–0,43 (0/8 < 0,025, trung vị ~0,12). Các seed chọn trùng coin/phút nhiều (tương quan cao) trong khi đối chứng rút độc lập theo seed ⇒ phương sai đối chứng gộp bị đánh giá thấp ⇒ p gộp C1 **lạc quan**. Giá trị chọn coin (+15,7k / 50,9k = 31%) là THẬT về điểm ước lượng nhưng bằng chứng thống kê YẾU. C2 vững hơn: 6/8 seed p < 0,025.
- Thời điểm (C1 − C2 = +46,2k) là nguồn chính: mua top-24 đúng các phút gate cho vào (sau sập) lãi, kể cả coin ngẫu nhiên; mua phút ngẫu nhiên lỗ (beta −11,0k trong thị trường −40%).
- Proxy chỉ leg0, không DCA, không giới hạn vốn/slot ⇒ S_real proxy (mean 6,4k/seed) ≠ ΣPnL_S sim (10,2k/seed); so sánh hợp lệ chỉ giữa S_real và đối chứng (cùng proxy). Hiệu chuẩn 2026: pearson 0,988, lệch TB −0,31pp.

### A5, A7
Đang chờ 8 kernel A5 (aud26-k24-p267-s*); A7 viết sau khi có A5.
