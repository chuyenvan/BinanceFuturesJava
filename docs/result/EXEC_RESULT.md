# EXEC_RESULT — khớp lệnh vào chân trên DEV 2022–2025 bằng aggTrades Binance Vision

Ngày **2026-10-12**. Pre-reg `docs/prereg/PREREG_EXEC.md` commit **`c60048d9`** (trước khi tải dữ liệu và trước khi đo; sau đó
không đổi thiết kế, ngưỡng hay k). Script `research/analysis/exec_{legs,fetch,measure,bookticker,v1diag,v1diag2,finalize}.py`.
JSON `docs/result/exec_result.json`. 0 sim Java, 0 Kaggle, 0 Binance REST (chỉ data.binance.vision), 0 chạm 242/shadow,
0 đọc ho4-*/ho26-*, 0 đụng kho backcast. Chân: `nsel-nen-s{42,7,13,21,99,123,777,2024}` (md5 trong pre-reg §1), start 2022–2025 +07.

## 0. Kết luận

1. **Không chính sách limit/ladder/trễ nào được GO.** P1/P2/P3 cho kết quả **xấu hơn** market P0, và P1 xấu hơn có ý nghĩa thống kê
   kể cả sau inflate (ΔPnL −10 256 USD/seed, CI_infl [−18 864, −1 647]). Nguyên nhân là adverse selection: những chân không khớp lại là
   những chân lãi nhất. P4 (chờ 1 nến xanh) cho Δ −1 688, CI_infl chứa 0. Thêm vào đó, **V1 FAIL** (xem §1), mà pre-reg ghi
   "không đạt ⇒ không GO". Vậy NO-GO có hai lý do độc lập.
2. **Penalty in-sim 1,675 % đang ĐẶT THỪA, khoảng 20 lần.** Chi phí market thực tế (P0) trên chân sập là **+7,4 bps**
   (CI95 [−2,3, +17,2]), so với 167,5 bps đang giả định. Ngay cả cận trên P0max (giá taker mua cao nhất trong 3 s) cũng chỉ
   **50,6 bps**. Trong 2022–25 (USD sim, bậc 1), stress trừ 17 820 USD/seed. Chi phí thực ước 1 555 USD/seed (chân sập 1 037,
   chân không sập 518), tức stress ăn thêm khoảng **16 300 USD/seed ≈ 25 % ΣPnL stress (65 096)**.
3. **Khuyến nghị:** live giữ **market**, không đổi adapter sang limit hay ladder. Sim thay penalty 1,675 % bằng chi phí vào đã hiệu chuẩn
   (§6). Trước khi dùng phải xác nhận trên kho backcast, và không tune lại trên HO4.

## 1. Dữ liệu, phủ, kiểm hợp lệ

| kiểm | ngưỡng pre-reg | đo | kết |
|---|---|---|---|
| Tải aggTrades daily | 3 071 (sym, ngày) | 3 071 ok, sha256 khớp `.CHECKSUM` 3 071/3 071, 0 thiếu | OK |
| Tải kline 1m monthly | 2 241 (sym, tháng) | 2 240 ok (sha 2 240/2 240); thiếu `AKROUSDT_2022-06` (không ảnh hưởng nến M) | OK |
| **V4 phủ** | — | sự kiện 5 283/5 284 (99,98 %); chân **23 651/23 654** có ≥1 trade trong [t_dec, t_dec+30 s] | OK |
| **V1 aggTrades vs kline** | ≥ 99,9 % phút trùng | **91,76 %** (106 336/115 881) | **FAIL** |
| V2 entry printDone == close_M·(1+0,01675·sập) | ≥ 99 % | **99,19 %** (23 462/23 654); 42,8 % chân là chân sập | PASS |
| V3 proxy thoát (E = entry printDone) vs `profit` | pearson ≥ 0,95 | **0,99997** (n 22 775 leg0 không-DCA), lệch TB 0,005 pp, 99,7 % trùng phút thoát | PASS |
| V5 vệ sinh | E ≤ L; bảo thủ ≤ lạc quan | đúng 100 % | PASS |

**Điều tra V1** (`exec_v1diag*.py`, bổ sung sau khi thấy FAIL, không dùng để chọn chính sách): lệch giá gần như chỉ nằm ở
**open/close** (4 090 phút), high/low lệch chỉ 153 phút. Với 400 phút lệch open lấy mẫu, **100 %** có giá open của kline xuất hiện trong
các print ±1 s quanh biên phút. Lệch volume đối xứng (51 % âm, trung vị −4e-6, p5/p95 ±0,25 %). Kết luận: lỗi nằm ở cách gán phút cho
trade sát biên (mốc ms của kline khác `transact_time`), **không phải mất dữ liệu**, và lệch có ở mọi năm (90–94 %). Phép đo P0/P4 dùng
print sau t_dec = giây 6 (giữa phút), còn limit dùng ngưỡng giá, nên về bản chất không phụ thuộc gán biên phút. Dù vậy, pre-reg đã
chốt "V1 không đạt ⇒ không GO", nên tôi giữ nguyên luật này.

**Kiểm P0 bằng bookTicker** (Vision chỉ có bookTicker futures cho 766/3 004 (sym, ngày), chủ yếu 2023; mẫu 150 (sym, ngày) → 256 sự kiện,
seed 20261012): P0 − ask tốt nhất tại t_dec có **trung vị −0,23 bps**, TB −3,2, p90 +2,5. Spread trung vị 4,1 bps (chân sập 7,2).
Có tới **54 % sự kiện mà notional ask L1 < N** (N trung vị khoảng 400 USDT), nên walk-the-book là cần thiết. P0 dùng VWAP các print
taker-mua thật nên đã gồm phần walk này. P0 khớp với quote, nhưng vẫn chưa phải sổ lệnh đầy đủ; P0max là cận trên.

Cờ P0 (paper): ok 21 398, thin (3 s chưa đủ qty, nới tới 30 s) 2 127, short (30 s vẫn thiếu; phần còn lại tính ở print cao nhất,
một chi tiết pre-reg chưa nêu) 99, noask 27.

## 2. Bảng chính: sizing paper 35 000 (chính), 23 651 chân × 8 seed, 93 đợt

Chi phí tính bằng bps so với close_M, chỉ trên phần đã khớp (âm = mua rẻ hơn close). ΣPnL proxy là USD trung bình/seed, 2022–25,
notional cố định theo sizing live (không lãi kép). ΔS = Σ_đợt Δ_e. CI_infl = S ± 1,794·1,96·sd_boot (k = 5, B = 4 000, bootstrap theo đợt).

| CS | khớp | chi phí TB / trung vị (bps) | ΣPnL | ΔS vs P0 | CI_infl | CI thô | đợt lãi (P0 = 75) | GO |
|---|---|---|---|---|---|---|---|---|
| **P0** market @giây 6 | 1,00 | **+5,1 / +5,2** (P0max +36,4) | 36 224 | — | — | — | 75 | ref |
| P1 limit close, 60 s | 0,77 | −25,3 / −0,3 | 25 969 | **−10 256** | **[−18 864, −1 647]** | [−15 054, −5 457] | 70 (93 %) | **NO** (xấu hơn có ý nghĩa) |
| P2 limit −0,3 %, 5′ | 0,70 | −47,1 / −30,0 | 24 966 | −11 259 | [−23 465, +948] | [−18 062, −4 455] | 67 (**89 % < 90 %**) | NO |
| P3 ladder 0/−0,5/−1 %, 5′ | 0,65 | −58,8 / −50,0 | 23 092 | −13 133 | [−27 027, +761] | [−20 877, −5 389] | 69 (92 %) | NO |
| P4 chờ 1 nến xanh | 1,00 | +28,3 / +46,7 | 34 537 | −1 688 | [−10 038, +6 663] | [−6 342, +2 967] | 71 (95 %) | NO (CI chứa 0) |

Độ nhạy (mô tả, không dùng cho GO). Khớp "= L" (lạc quan): P1 −9 553, P2 −11 259, P3 −13 031. Cộng lợi phí maker 3 bps:
P1 −10 122, P2 −11 058, P3 −12 965. Chỉ tập không-DCA: P1 −10 661, P2 −12 964, P3 −15 518, P4 −3 418.
**Pilot 10 000** cùng dấu: P0 ΣPnL 10 311; ΔS P1 −2 850 [−5 262, −439], P2 −3 148 [−6 727, +430], P3 −3 727 [−7 642, +188],
P4 −450 [−2 846, +1 946]; đợt lãi P0 74, P1 70, P2 67, P3 69, P4 72.

**Theo ngày MTM proxy (paper, mô tả):** tỉ lệ ngày Δ>0 là P1 30 %, P2 35 %, P3 31 %, P4 39 %. DD vốn chốt (cận dưới): P0 −12,9 %,
P1 −11,4, P2 −7,2, P3 −6,3, P4 −13,1. Limit giảm DD chỉ vì giảm phơi nhiễm, và lợi nhuận giảm nhiều hơn.

**Adverse selection (hậu kiểm mô tả, không pre-reg):**

| CS | chân khớp đủ | lãi/chân P0 → CS (% N) | chân không khớp | lãi/chân P0 của chân bị lỡ | PnL P0 bị lỡ (USD/seed) |
|---|---|---|---|---|---|
| P1 | 18 108 | 3,10 → 3,21 | 5 259 | **4,19** | 11 077 |
| P2 | 16 514 | 3,04 → 3,30 | 7 016 | **4,01** | 13 273 |
| P3 | 11 258 | 2,73 → 3,16 | 3 654 | **4,89** | 8 524 |

Limit chỉ cải thiện giá vào khoảng **+0,1–0,4 pp trên chân khớp**. Đổi lại nó bỏ lỡ 15–30 % số chân, và đó chính là những chân bật lên
ngay sau khi vào (lãi TB 4–4,9 %, cao hơn chân khớp). Đây là adverse selection kinh điển của chiến lược bắt đáy: chân không khớp là
chân giá không quay lại.

## 3. Hiệu chuẩn penalty 1,675 % bằng P0 (paper; CI95 bootstrap theo đợt, không inflate vì đây là một phép đo)

| nhóm nến M | chân | đợt | chi phí P0 TB (bps) | CI95 | trung vị | p90 | P0max TB (cận trên) |
|---|---|---|---|---|---|---|---|
| **sập (≤ −1 %)** | 10 126 | 78 | **+7,4** | **[−2,3, +17,2]** | +11,7 | +91,0 | +50,6 |
| −1..−2 % | 4 661 | 74 | +10,8 | [+3,3, +17,6] | +15,4 | +58,0 | +32,9 |
| −2..−4 % | 3 241 | 60 | +8,9 | [−1,8, +19,0] | +8,7 | +92,5 | +41,1 |
| < −4 % | 2 224 | 45 | −2,0 | [−34,3, +31,9] | −2,9 | +187,7 | +101,4 |
| không sập | 13 525 | 88 | +3,3 | [+0,1, +6,8] | +2,8 | +44,8 | +23,2 |

**Phán quyết theo luật pre-reg: THỪA** (CI_trên 17,2 bps < 167,5 bps). Không có nhóm nào mà kể cả cận trên P0max chạm tới
167,5 bps. Chân sập vào ở market chỉ tốn khoảng 7 bps vì sau một nến sập, ask tại giây 6 thường đã ở quanh close hoặc thấp hơn
(bookTicker: ask − close của chân sập là −6,3 bps). Đuôi phải dày: p90 91 bps, nhóm < −4 % có p90 188 bps. Vì vậy một mức phạt **đều**
là sai về hình dạng phân phối, chứ không chỉ sai về mức. Chân không sập tốn +3,3 bps, so với sim đang giả định 0,67 bps/chiều.

P0 trên chân sập theo năm: 2022 +17,3 · 2023 −12,3 · 2024 +19,6 · 2025 +6,4 bps.

## 4. Theo năm × mức sập (paper, mô tả; ΣPnL USD/seed)

ΔS so với P0 theo năm:

| CS | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|
| P1 | −806 | −3 481 | −4 020 | −1 950 |
| P2 | −60 | −5 289 | −4 035 | −1 875 |
| P3 | −770 | −5 982 | −4 368 | −2 013 |
| P4 | −31 | +745 | −2 986 | +585 |

ΔS so với P0 theo mức sập nến M: P1 không sập −3 852 · −1..−2 −4 037 · −2..−4 −1 243 · < −4 −1 124; P2 −4 034 / −3 900 / −1 967 / −1 358;
P3 −5 441 / −3 791 / −2 591 / −1 310; P4 +929 / −655 / −845 / −1 117. Limit thua ở **mọi** năm và **mọi** mức sập. P4 có lợi nhẹ ở chân
không sập nhưng thua ở chân sập (chờ nến xanh tức là vào sau khi giá đã bật).

Chi tiết năm × mức sập: số chân (gộp 8 seed), chi phí P0 (bps), tỉ lệ khớp P1/P2/P3, chi phí P4 (bps), ΣPnL P0 → P1 (USD/seed):

| năm | nhóm | chân | P0 bps | khớp P1/P2/P3 | P4 bps | PnL P0 → P1 |
|---|---|---|---|---|---|---|
| 2022 | không sập | 3 125 | +1,8 | 0,85/0,75/0,64 | +12,5 | 590 → 292 |
| 2022 | −1..−2 | 929 | +12,8 | 0,68/0,65/0,59 | +32,3 | 776 → 213 |
| 2022 | −2..−4 | 531 | +8,0 | 0,76/0,66/0,66 | +71,5 | 441 → 651 |
| 2022 | < −4 | 357 | +42,7 | 0,73/0,73/0,70 | +30,1 | 536 → 382 |
| 2023 | không sập | 3 407 | +6,0 | 0,79/0,63/0,60 | −0,5 | 6 841 → 5 203 |
| 2023 | −1..−2 | 1 158 | −3,7 | 0,83/0,71/0,69 | −37,3 | 1 660 → 1 138 |
| 2023 | −2..−4 | 954 | −3,9 | 0,75/0,68/0,65 | +7,9 | 2 849 → 2 049 |
| 2023 | < −4 | 581 | −43,4 | 0,81/0,79/0,79 | +42,1 | 2 092 → 1 571 |
| 2024 | không sập | 3 629 | +2,5 | 0,76/0,67/0,60 | +30,5 | 5 300 → 3 899 |
| 2024 | −1..−2 | 1 532 | +18,5 | 0,57/0,61/0,57 | +91,2 | 3 997 → 2 056 |
| 2024 | −2..−4 | 884 | +29,1 | 0,63/0,59/0,56 | +84,9 | 1 483 → 985 |
| 2024 | < −4 | 668 | +9,5 | 0,78/0,76/0,76 | +306,8 | 1 703 → 1 523 |
| 2025 | không sập | 3 364 | +2,8 | 0,81/0,77/0,68 | −13,4 | 2 762 → 2 247 |
| 2025 | −1..−2 | 1 042 | +14,0 | 0,69/0,65/0,63 | +40,1 | 2 130 → 1 121 |
| 2025 | −2..−4 | 872 | +2,9 | 0,84/0,84/0,78 | −75,4 | 2 012 → 1 856 |
| 2025 | < −4 | 618 | −1,4 | 0,88/0,85/0,84 | +166,2 | 1 051 → 783 |

## 5. Tác động lên ROI/DD k24 (proxy bậc 1, không phải sim)

Penalty stress so với chi phí P0 thực, tính bằng margin sim × chi phí, USD/seed:

| năm | penalty stress trừ | chi phí P0 thực (mọi chân) | ΣPnL stress (printDone) |
|---|---|---|---|
| 2022 | 1 630 | 108 | 1 687 |
| 2023 | 4 304 | −105 | 22 303 |
| 2024 | 6 076 | 880 | 21 220 |
| 2025 | 5 811 | 672 | 19 886 |
| **2022–25** | **17 820** | **1 555** | **65 096** |

- Stress trừ thừa khoảng **16 300 USD/seed ≈ 25 % ΣPnL stress**. Riêng năm 2022, penalty gần như xoá sạch PnL. Bậc 1 thì k24 với chi phí thực
  gần với bản phí gốc `gqsf-*` (CAGR22 36,95 %, maxDD −22,55 %, Calmar 1,647; nguồn COVERAGE_M2) trừ khoảng 1 555 USD/seed, chứ không gần
  bản stress (27,63 % / −22,86 % / 1,212). Không có sim nên không có CI cho ROI/DD.
- Chính sách limit: P1 tương đương khoảng −29 pp ROI đơn (trên 35 000, 4 năm), tức khoảng −7 pp/năm. P4 khoảng −1,2 pp/năm (không có ý nghĩa).
  DD vốn chốt của limit thấp hơn chỉ vì vào ít chân hơn.
- HO4 (số liệu trong đề bài: W9 k24 ΣPnL 14 758 phí gốc so với 9 262 stress) chênh theo đúng hướng này. Tôi KHÔNG dùng HO4 để chỉnh gì.

## 6. Đề xuất (KHÔNG sửa Java vòng này)

**Sim:**
- (a) Thay phạt đều `SIM_CRASH_ENTRY_PENALTY=0.01675` bằng chi phí vào theo mức sập nến M, qua key mới (cần đổi Java, chỉ đề xuất):
  `SIM_ENTRY_COST_MODE=bucket`, `SIM_ENTRY_COST_{NC,C1,C2,C4}`. Bản *thực* dùng CI_trên: NC 0,0007 · C1 (−1..−2) 0,0018 · C2 (−2..−4)
  0,0019 · C4 (< −4) 0,0032. Bản *stress* dùng P0max: NC 0,0023 · C1 0,0033 · C2 0,0041 · C4 0,0101.
- (b) Nếu chưa có key mới: dùng tạm key hiện có, `SIM_CRASH_ENTRY_PENALTY=0.005` cho stress (khoảng P0max chân sập) và `0.0017`
  cho bản thực. Chân không sập thì chênh +3 bps so với `SIM_SLIPPAGE_RATE`, nhỏ, có thể bỏ qua.
- (c) Không thêm key kiểu vào limit hay ladder vào sim; dữ liệu không ủng hộ.

**Live (adapter lệnh):** giữ **market** tại giây 6. Ghi cho mỗi chân `t_dec`, VWAP khớp, close_M, ask/bid L1 và độ sâu, để hiệu chuẩn liên tục
(live 2026 trước đây chỉ có 27 chân sập). Một bản market có trần (limit IOC tại close_M·(1+x)) là ý tưởng **chưa kiểm**: nó cắt đúng đuôi
p90 91–188 bps nhưng có thể bỏ lỡ chân. Muốn dùng phải pre-reg riêng.

**Cần xác nhận trên kho backcast 2020–2021H1** (tôi không đụng): (1) chi phí P0 chân sập, nhất là nhóm < −4 % trong các cú sập
5/2021 (đuôi dày, CI rộng [−34, +32]); (2) dấu ΔPnL của P1 và P4; (3) sim lại k24 với key (a)/(b) trên DEV + backcast trước khi dùng
cho bất kỳ quyết định nào.

## 7. Giới hạn

1. **V1 FAIL** (91,8 % < 99,9 %). Đã điều tra: lỗi gán biên phút ở mức ms, không phải mất dữ liệu. Theo pre-reg thì đây vẫn là lý do NO-GO.
2. aggTrades không có sổ lệnh. P0 là VWAP các print taker-mua sau t_dec, không phải walk-the-book thật: nó không mô hình lệnh của ta làm cạn sổ
   hay việc sổ hồi lại. bookTicker (256 sự kiện, chủ yếu 2023) cho thấy P0 khớp ask tại t_dec (trung vị −0,2 bps), nhưng 54 % sự kiện có L1
   mỏng hơn N. Cận trên là P0max.
3. Queue limit được giả định bảo thủ ("= L" không khớp). Bản lạc quan cũng cho kết luận như vậy (P1o −9 553).
4. Proxy thoát không có DCA, funding hay SL cứng. Chân không khớp tính PnL 0, không tính việc dùng vốn rảnh vào chân khác. Bị cắt dữ liệu kline
   ở 169,5 h với 31 chân P0 (0,13 %, đã trail-arm, chốt ở close cuối). Phí như nhau ở mọi chính sách.
5. 8 seed dùng chung phần lớn sự kiện nên không độc lập; đơn vị bootstrap là đợt (93 đợt). Nhóm < −4 % chỉ có 45 đợt.
6. Mốc t_dec = s+66 s; live đo latency median 7,2 s (p75 25 s). Phần trễ dài hơn chưa được mô hình (P0 chỉ nới cửa sổ khi thiếu qty).
7. Chỉ DEV 2022–2025. Tác động ROI/DD ở §5 là ước lượng bậc 1, không có sim và không có CI.

## 8. Tái lập + cache

```bash
cd ~/src/BinanceFuturesJava/research/analysis
python3 exec_legs.py                 # legs.pkl md5 c55224e7bbc82cf5be83e9c2217d6b8e (23 654 chân, 5 284 sự kiện)
python3 exec_fetch.py kl 6 && python3 exec_fetch.py agg 6     # ~30', ~1 GB cắt cửa sổ, zip gốc xoá ngay
python3 exec_measure.py sim 3        # sim.pkl md5 767b67516b982fa0854bd1fd25279390
python3 exec_measure.py report       # -> docs/result/exec_result.json
python3 exec_bookticker.py fetch && python3 exec_bookticker.py cmp
python3 exec_v1diag.py && python3 exec_v1diag2.py && python3 exec_finalize.py merge
```

Cache tự tạo `~/claude_master/1012/exec/{agg,kl}/*.npz` + `*.pkl` (5 315 file, khoảng 1,1 G) đã ghi manifest md5
(`cache_manifest.md5`, md5 a6e51a257050be670530c2fe8601f2a6) rồi **xoá**. Manifest và các log/JSON nhỏ được giữ lại.
