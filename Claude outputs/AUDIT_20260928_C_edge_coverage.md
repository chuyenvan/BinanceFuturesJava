# C — Edge hiện có từ đâu ra, có thật không, và vùng giả thuyết nào CHƯA từng được thử

Auditor độc lập, 2026-09-28. Chỉ đọc doc/script trong `/home/claude/audit/{docs,research,profiles}`; không sim, không Oracle/Kaggle.
Nhãn: **[ĐO]** = số có trong doc (ghi nguồn) · **[SUY LUẬN]** = lập luận của auditor · **[KHÔNG RÕ]** = doc không đủ.
Lưu ý phạm vi: phần lớn phân rã theo leg/quý/năm chỉ có trên **T170** (`efb793e2`, n1089). Với **KEEPLEG0** (`99e42b75`, n1085) doc chỉ có số lệnh theo leg (817/248/20, `RESULT_SIM_CADENCE_MATCH.md` §3), **không có PnL theo leg** → [KHÔNG RÕ]. Hai nền chỉ khác lưới DCA (`DECISION_BASELINE_KEEPLEG0.md`), nên cấu trúc edge có thể suy từ T170, **trừ phần DCA** (KEEPLEG0 đã làm phẳng lưới DCA nên mất khoảng 8k equity).

---

## 0. TÓM TẮT RỦI RO (đọc trước)

1. **Chính baseline trượt các rào mới.** KEEPLEG0 có top-1% lệnh = **23,74%** PnL (rào ≤15%), bỏ top-50% lệnh thì PnL còn **−33.196**, `q*` = **19%** [ĐO, `RESULT_TAIL50_RULER_REDUNDANCY.md` §1]. Rào (a)+(b′) đang loại chính incumbent. Mọi ứng viên "NO-GO dưới rào mới" vì vậy đang bị so với một chuẩn mà baseline cũng không qua.
2. **Edge là "mua capitulation thị trường" với thoát bất đối xứng, không phải kỹ năng xếp hạng coin.** Selector S1 **không có edge TIỀN**. Rank-IC của S1 so với return thô **âm có ý nghĩa**: −0,069 @24h, và −0,087 @72h so với `retEnd_72h`. `glift8` nằm trong CI [ĐO, `RESULT_TREND_RANK_IC.md` §2, `RESULT_H72.md` §0, `RESULT_PNL_RULER.md` §2].
3. **Số cược độc lập nhỏ và dồn vào vài sự kiện.** Chỉ có **56 ngày** có BIG_DOWN, **110 ngày** có lệnh, **N_eff theo tuần = 76**. Cửa sổ 5 ngày 2025-10-09..13 tạo **44,2%** lãi năm 2025 (KEEPLEG0 41,0%) và khoảng **82%** return quý 2025Q4 (tính từ equity) [ĐO/SUY LUẬN, §1].
4. **Chưa từng deflate trên chính incumbent.** Ngưỡng BIG_DOWN −0,03157 được HPO trên DEV và nằm đúng **local max** PnL. Ước lượng DSR thô ([SUY LUẬN], §1e) cho T170 nhịp 1' ≈ 0,8–0,98 nếu số phép thử hiệu dụng 10–200 và độ phân tán SR giữa các cấu hình 0,5. Nếu độ phân tán SR là 1,0 thì DSR sụp dưới 0,2. Với nhịp live (sel15, CAGR 17,3%) DSR yếu hơn rõ.
5. **Edge DEV khó hiện thực hóa ở live.** (a) Nhịp đúng live (sel15) cho **CAGR 17,29%**, không phải 27,14%. Hiệu là −9,84pp, CI trên −0,49 [ĐO]. (b) p15 live bị **cụt đuôi**: max 2,30% so với DEV 12,26%, nên cổng AI tất định cho 0 lệnh [ĐO, `RESULT_GATE_ROOTCAUSE.md`]. (c) **Store feature sinh `pred.bin` DEV đã mất**: corr chỉ 0,762, không fold nào tái lập được [ĐO, `RESULT_P15_SOURCE.md` §3.4].
6. **Ô long-short / market-neutral gần như CHƯA được thử một cách công bằng.** Đường SELL đã bị xóa ở `5f40a90` (09-03). Các tín hiệu cross-section có dấu **ổn định ở phía short/avoid** (ΔOI cao, vol cao, funding cao, S1 cao) chỉ được chấm theo chuẩn "long-only net>0". SHORT_CARRY V3 (dollar-neutral) bị giết bởi turnover 36% mỗi chu kỳ 8h và proxy slip, không phải bởi tín hiệu.

---

## PHẦN 1 — GIẢI PHẪU EDGE BASELINE

### 1.1 Cơ chế thật của các leg (đọc code qua doc)

- **Gate p15 = mô hình "bật lại sau capitulation".** Nhãn `futureReturn15M` là *trung bình max-upside 15' của rổ top-60 "potential losers"* (coin sụt mạnh nhất từ đỉnh 15'). Output luôn ≥0; DEV có p50 0,545%, p99 1,308%, max 12,26% [ĐO, `DIAG_ENTRYGATE_PRED15M_REGIME.md` §1-2]. Ngưỡng T170 ≈ `0,0687·symbolPred·1,70`, tức p50 khoảng 3,1% (vượt p99). Nghĩa là cổng **chỉ mở ở đuôi p15**. Kết quả: 17.925.650 ứng viên → **841 PASS (0,0047%)** [ĐO, `RESULT_CAPACITY_DIAG.md` §1.2].
- **BIG_DOWN** kích hoạt khi return trung bình của 100 coin giảm mạnh nhất *trong đúng 1 nến 1'* < −0,03157 (khoảng −22σ). Có **124 phút / 56 ngày / 248 leg** trong 4,5 năm. Leg này bypass gate và chọn 2 coin theo pNoPump [ĐO, `AUDIT_BIGDOWN_DEEP.md` §1, §5].
- **DCA_LEVEL1** không phải nguồn vào lệnh độc lập. Cả 20 leg đều là leg 2/3 nhồi vào vị thế đang lỗ [ĐO, `RESULT_SELECTOR_LEG_CUT.md` §5.3].
- ⇒ [SUY LUẬN] **Cả ba leg cùng một họ: mua khi thị trường alt sụp theo phút, rồi thoát bằng arm +7% và trailing.** S1 chỉ quyết định *coin nào* trong pool small/mid-cap biến động.

### 1.2 PnL theo leg (T170) [ĐO, `AUDIT_BIGDOWN_DEEP.md` §3.1; `RESULT_SELECTOR_LEG_CUT.md` §5.1]

| leg | n | %leg | PnL USDT | %PnL | PnL/leg | win% | mP\|SM | mP\|SL |
|---|---|---|---|---|---|---|---|---|
| PREDICT_SYMBOL_TRADE (qua gate) | 821 | 75,4% | 47.115 | 61,9% | 57,4 | 89,9 | +110,8 | −417,1 |
| BIG_DOWN | 248 | 22,8% | 16.254 | 21,4% | 65,5 | 91,5 | +96,6 | −269,9 |
| DCA_LEVEL1 | 20 | 1,8% | 12.701 | 16,7% | 635,1 | 80,0 | — | — |
| **Tổng** | 1089 | | **76.070** | | 69,9 | 88,25 | | |

- Cắt hẳn leg selector (V1 CUT): chỉ còn BIG_DOWN, n=248, **CAGR 7,23%**, UW 184 [ĐO, `RESULT_SELECTOR_LEG_CUT.md` §4.3].
- BIG_DOWN rút nhiều hơn ở T170 so với T100 là nhờ **sizing** (gate chặt → throttle cao), không phải chọn entry tốt hơn. PnL/leg tăng 46,6 → 53,3 → 65,5 khi đi T100 → T130 → T170 [ĐO, `AUDIT_BIGDOWN_DEEP.md` §4].
- KEEPLEG0 có 817/248/20 leg nhưng PnL theo leg [KHÔNG RÕ]. [SUY LUẬN] Phần DCA (16,7% ở T170, nhờ trọng số 8 ở bậc cuối) gần như chắc giảm mạnh khi lưới làm phẳng 1,1,1,1.

### 1.3 Theo năm / quý (T170) [ĐO, `DETAIL_BR_QUARTERLY.md` §1-2; `AUDIT_BIGDOWN_DEEP.md` §3.2]

| năm | return% | PnL tổng (end) | PnL BIG_DOWN | %BD | n lệnh |
|---|---|---|---|---|---|
| 2021H2 | 12,21 | 4.273 | 982 | 23,0% | 149 |
| 2022 | 19,58 | 7.688 | 1.358 | 17,7% | 198 |
| 2023 | 34,96 | 16.637 | 2.022 | 12,2% | 126 |
| 2024 | 32,06 | 20.097 | 6.172 | 30,7% | 281 |
| 2025 | 32,71 | 27.374 | 5.720 | 20,9% | 335 |

Quý (return%, số lệnh): 2023Q1 **−0,37% / 6 lệnh**; 2023Q2 **+16,18% / 36**; 2024Q2 −0,92%; 2025Q1 +14,62%; **2025Q2 +1,57% / 10 lệnh**; **2025Q3 +1,27% / 20 lệnh**; 2025Q4 +12,56% / 189.
- [SUY LUẬN, tính từ bảng quý] **6/18 quý** (2023Q2, 2025Q1, 2025Q4, 2024Q1, 2024Q4, 2023Q4) chiếm khoảng **62% tổng log-return** (0,713/1,155). Có 3 quý gần như không có lệnh (2023Q1, 2025Q2, 2025Q3).
- **Theo regime macro BTC 30d** (T170): m_up +44.332, m_flat +16.847, m_down +14.891 [ĐO, `ANALYSIS_T170_VS_T100.md` §4c; bucket được chọn hậu kiểm].

### 1.4 Sự kiện đuôi [ĐO]

| sự kiện | tác động | nguồn |
|---|---|---|
| **2025-10-09..13 cascade** | Σpnl lệnh đóng trong cửa sổ W **+12.106** (T170) / **+9.943** (KEEPLEG0) = **44,2% / 41,0%** lãi 2025. Sau W chỉ còn 1,0%. Equity 10-08 → 10-14: +10,3%. MTM trong ngày **−16,3% / −17,6%** (lớn hơn maxDD ngày toàn kỳ). Open margin **56,7% / 54,2%** equity | `RESULT_BLACKSWAN_2510.md` §2 |
| 2025Q4 | Equity đầu quý 98.676 = equity 10-08; cuối quý 111.070. [SUY LUẬN] W (+10.195 theo equity) ≈ **82%** return cả quý | `DETAIL_BR_QUARTERLY.md`, `RESULT_BLACKSWAN_2510.md` |
| **2022-11 FTT** | maxDD T170 −11,84% (2022-10-17 → 11-10), **100%** mức sụt nằm trong ngày BIG_DOWN. Giữ FTT tới 9,77% equity; net +685 nhờ stop cắt kịp, "may về thời điểm, không phải cơ chế" | `ANALYSIS_BIGDOWN_STRUCT.md` Q1/M5; `RESULT_FRAGILITY_N.md` A6 |
| 2022-05 LUNA | T170 không bị (đã thoát từ 2021); T100/GD92 mất −12,06% / −13,55% trong 1 ngày | `RESULT_FRAGILITY_N.md` A6(c) |
| 2023Q2 | +16,18% với 36 lệnh (quý tốt nhất). Sự kiện cụ thể [KHÔNG RÕ]; [SUY LUẬN] có thể trùng đợt alt-dump 06/2023 (danh sách episode 2023-04 ở `RESULT_INTRADAY_DD.md` §0) | |
| MTM phút | maxDD thật (mark phút) **−19,96%** (T170/KEEPLEG0) so với −11,84% theo ngày; UW 144–147 | `RESULT_TAIL_LEVER.md` W2 |

### (a) PnL đến từ đâu

- [ĐO] Khoảng **62% PnL** thuộc leg qua gate p15 (cổng chỉ mở ở đuôi "bounce sau sụp"), **21%** từ BIG_DOWN (1' sụp toàn thị trường), **17%** từ DCA nhồi vào lệnh lỗ rồi hồi (T170). Nhập lệnh tập trung vào giờ bigdown: số lệnh mỗi giờ trong bigdown cao **10,3×** ngoài bigdown (T170) [ĐO, `ANALYSIS_BIGDOWN_STRUCT.md` M2].
- [ĐO] Không phải beta BTC: %beta **3,9%**, t(α) 4,37. Nếu chỉ nhờ BTC thì Σpnl = **−30.569**; **879/1089** lệnh có BTC giảm trong lúc giữ mà win 88,9% [`ANALYSIS_BETA_DECOMP_T170.md` A, B]. Doc tự ghi giới hạn: chưa kiểm beta với chỉ số alt-market.
- [SUY LUẬN] Dạng payoff là **cung cấp thanh khoản lúc cascade**: win 88%, lỗ trung bình ≈ **3,1×** lãi trung bình [ĐO, `RESULT_TAIL50…` §3], cộng một đuôi phải nhờ trailing (top-1% = 23–26% PnL). Đây là **phần bù rủi ro crash-continuation**. Nó chỉ trả tiền khi có cascade rồi hồi, và phạt nặng khi cascade kéo dài (FTT, LUNA với nền gate mở).

### (b) Số cược độc lập thật sự

| thước | giá trị | nguồn |
|---|---|---|
| ngày có ≥1 leg | **110** / 1644 (T170); "105/1644 ngày có lệnh vào" | `RESULT_FRAGILITY_N.md` B; `power_wall.md` |
| ngày có trigger BIG_DOWN | **56** (124 phút) | `AUDIT_BIGDOWN_DEEP.md` §5 |
| N_eff (cụm tuần ISO) | **76** (N_eff/n = 0,070) | `RESULT_FRAGILITY_N.md` B |
| ICC(ROI, cohort ngày) | **0,0516** (T100: 0,1016); trần 1/ICC = 19,4; n_eff(k̄=3,55) = 3,13 | `power_wall.md` đính chính; `ANALYSIS_BIGDOWN_STRUCT.md` |
| n_eff_total (cohort ngày) | 606 / 1084 | `ANALYSIS_BIGDOWN_STRUCT.md` M6 |
| top-1% / top-5% / top-10% share | T170 25,9 / 56,7 / 76,8%; **KEEPLEG0 top-1% 23,74%** | `RESULT_FRAGILITY_N.md`; `RESULT_TAIL50…` |
| q* (bỏ top-q% thì PnL=0) | **19%** (khoảng 206 lệnh) cho cả T170 lẫn KEEPLEG0 | `RESULT_TAIL50…` §1 |
| episode thị trường lớn | khoảng **9 đợt** (2021-09, 2021-11 → 22-05, 2022-11, 2023-04, 2024-04, 2024-08, 2025-02, 2025-10, 2025-11) | `RESULT_INTRADAY_DD.md` §0 |
| leg BIG_DOWN thua | **21** quan sát (mP\|SL dựa trên 21 điểm) | `AUDIT_BIGDOWN_DEEP.md` §5 |

⇒ [SUY LUẬN] **Khoảng 60–110 cược độc lập**. Phần quyết định dấu PnL (khoảng 200 lệnh top) lại dồn vào **khoảng 9 episode**. Ở cỡ đó, DEV chỉ phân biệt được hiệu ứng ≥2–4%/lệnh (MDE, `RESULT_HARNESS_CONTROL.md` §0C). Ngay chính tín hiệu MOM15 cũng không qua được trên riêng DEV: +1,28%, CI [−0,72; +3,28] [ĐO].

### (c) S1: edge TIỀN hay chỉ edge xếp hạng? → **chỉ xếp hạng trên nhãn; TIỀN = 0 hoặc âm**

- Trên nhãn: `g1lite` ic +0,167, `maxFav_72h` ic +0,277 (ngoài CI) [ĐO, `RESULT_H72.md` §0.1].
- Trên tiền: ic vs `retEnd_72h` **−0,0869**, pacc 0,4689 (<0,5, ngoài CI). S1 rank-IC so với return thô −0,025/−0,041/−0,069 @1/4/24h, ngoài CI và âm cả 4 năm [ĐO, `RESULT_TREND_RANK_IC.md` §2, `RESULT_S1_RANK_QUALITY.md`]. Đo đúng mốc BIG_DOWN: −0,019 ở 72h, CI chứa 0 [ĐO, `RESULT_S1_CORRECT_MEASURE.md`].
- Trong pool P32 với nhãn PnL luật thoát: `glift8` 45deploy +0,0006, trong CI. Nới K 8 → 32: Δ trong CI. `netm8`@0,8% dương nhưng CI chạm 0. **"Mức" đến từ rổ + luật thoát, không từ xếp hạng** [ĐO, `RESULT_PNL_RULER.md`, `RESULT_K_SWEEP.md`]. Sau khi bỏ đuôi: `tf_10` âm ở cả 12 đối tượng; S1 có `tf_5` −0,0015 [ĐO, `RESULT_TAIL_ROBUST_RULERS.md` §3].
- 4 lần đổi nhãn (g1lite, retEnd_h, PnL-exit, maxFav×3) và OFI đều cho **Δ tiền = 0** [ĐO, `RESULT_S1_MAXFAV`, `RESULT_MONEY_RANKER`, `RESULT_OFI_MONEY`].
- ⇒ [SUY LUẬN] S1 thực chất là **bộ lọc biến động/upside-potential**: chọn coin dễ chạm +7%. Giá trị của nó chỉ tồn tại *cùng với* luật thoát bất đối xứng và thời điểm capitulation. Vì vậy 62% PnL "leg selector" nên quy cho **timing của gate p15**, không phải cho **xếp hạng S1**. Phép tách sạch (random coin vào cùng phút gate mở, cùng luật thoát) **chưa có** [KHÔNG RÕ].

### (d) Phụ thuộc cadence (27,14% nhịp 1' so với 17,29% sel15)

[ĐO, `RESULT_SIM_CADENCE_MATCH.md` §3-4]: selector 817 → 483 lệnh (−41%); BIG_DOWN giữ nguyên 248; n_cand giảm 15× nhưng n_pass chỉ giảm 1,69×. 5 rate chất lượng **không khác** (0/5 ngoài CI). ΔCAGR −9,84pp, CI [−20,76; −0,49]. Chặn tất cả leg ở 15' thì BIG_DOWN rơi 248 → 14.
- [SUY LUẬN] Nhịp phút **không chọn lệnh tốt hơn**, nó **bắt được nhiều lệnh hơn trong cùng một cửa sổ sự kiện**. Trạng thái cổng mở là biến cố ngắn (vài phút), và BIG_DOWN bản chất là hiện tượng 1 nến 1'. Edge nằm ở **độ phủ cửa sổ capitulation theo phút**, không ở tốc độ phản ứng tính bằng giây.
- Hệ quả: (i) mọi số 27% là số của một kiến trúc live chưa từng chạy (live hardcode `ENTRY_GRID_MIN=15`, `DIAG_GATE_LIVE_VS_OFFLINE.md` §1.6). (ii) Slip có điều kiện ngay phút sụp **chưa đo**. Slip live trung vị 0,33%/chân là của mọi lệnh [ĐO, `RESULT_LIVE_FILLS_AUDIT.md`]. Nhân chi phí ×10 trong cửa sổ W đã xóa 48,8% lãi 2025 của KEEPLEG0 [ĐO, `RESULT_BLACKSWAN_2510.md` C1].

### (e) Incumbent đã được deflate cho việc chọn từ khoảng 200 vòng chưa? → **CHƯA**

- Không có DSR/PBO nào tính trên T170/KEEPLEG0. DSR/PBO chỉ xuất hiện ở pha CPCV cũ (trước T170): baseline DSR 0,950@400 / 0,932@1000 **FAIL**; v3 0,936/0,912 **FAIL** [ĐO, `ROADMAP_NOLEAK.md:82-85`; `AUDIT_APPLIED.md` F7].
- Các bậc tự do đã tiêu trên cùng DEV: 183 profile, 171 PREREG, 187 RESULT (đếm file); GS Sobol 256 điểm; sweep gate-scale khoảng 13 giá trị. **Ngưỡng BIG_DOWN −0,03157 được HPO rồi revert và là local max** (PnL BD dao 8,3k–16,3k qua 5 điểm) [ĐO, `RESULT_BD_THRESHOLD_FRAGILITY.md` §2.1; `AUDIT_BIGDOWN_DEEP.md` §2.2]. Lý do cắt S1 40 → 9 feature đã mất [ĐO, `power_wall.md`]. **Store feature của `pred.bin` đã mất** [ĐO, `RESULT_P15_SOURCE.md` §3.4].
- Điểm có lợi [ĐO]: CAGR CI95 (khối 72h, k=2) của T170 là **[14,80; 46,23]** (`PREREG_REGIME_GATE.md:116-117`). t(α) = 4,37 (HAC) sống qua Bonferroni khoảng 200 phép thử (p·200 ≈ 2,5e-3) [SUY LUẬN, số học]. T170 được chọn theo rủi ro, CAGR thấp hơn T100, nên việc chọn không trực tiếp thổi CAGR.
- **Ước lượng DSR thô [SUY LUẬN]**: SR năm ≈ ln(1,2927)/0,145 ≈ 1,77 (vol tự nhiên khoảng 14,5%/năm theo `RESULT_VOL_TARGET.md` §0), T = 1643 ngày. Kết quả:

| độ phân tán SR năm giữa các phép thử | N hiệu dụng 10 | 50 | 200 |
|---|---|---|---|
| 0,5 — T170 nhịp 1' | 0,98 | 0,90 | 0,79 |
| 0,5 — cấu hình SR≈1,2 (tương đương sel15, giả định) | 0,81 | 0,55 | 0,35 |
| 1,0 — T170 nhịp 1' | 0,66 | 0,14 | 0,02 |

  Giả định iid theo ngày là **lạc quan**: 73% ngày không có vị thế, lợi nhuận dồn vào khoảng 110 ngày, và vol theo ngày bỏ qua MTM trong ngày. ⇒ Rủi ro "incumbent là may mắn chọn lọc" ở mức **trung bình**. Nguồn rủi ro lớn nhất không nằm ở chọn gate-scale, mà ở **(i) ngưỡng BIG_DOWN tune trên DEV, (ii) phiên bản p15 không tái lập được, (iii) 44% lãi 2025 dồn vào 1 sự kiện**. Việc tính đúng DSR có thể làm rẻ (§3.iii).

### (f) Rủi ro "edge không ổn định"

- [ĐO] 2025Q2 có 10 lệnh, 2025Q3 có 20 lệnh, 2023Q1 có 6 lệnh. UW là rào **binding** duy nhất cho mọi hướng "tăng breadth" (5 thiết kế phòng thủ đều thất bại cùng một lý do, `power_wall.md` mục BREADTH).
- [ĐO] Tần suất trigger BIG_DOWN theo năm: 16/10/25/35/38 phút. Độ sâu `rateDownAvg` 2025 là −0,354 so với 2024 −0,137. Mật độ k cần để giữ tần suất dao động **3,1×** theo giai đoạn (`AUDIT_BIGDOWN_DEEP.md` §5).
- [ĐO] p15 2026: đuôi offline-2021-25 **dày khoảng 5×** 2026 (`DIAG_GATE_LIVE_VS_OFFLINE.md` §1.6a). Đọc theo phân phối: theo thời gian cổng mở hiếm dần.
- [SUY LUẬN] Lợi nhuận **phụ thuộc vào việc có cascade alt lớn rồi hồi nhanh**. Năm không có cascade thì hệ gần như đứng yên (UW dài). Năm có cascade không hồi (FTT/LUNA kiểu mới) thì chịu MTM −17 đến −20%. 2025 đã cho thấy cả hai: 2 quý trống, rồi 1 cascade tạo gần một nửa lãi năm.

---

## PHẦN 2 — BẢN ĐỒ PHỦ GIẢ THUYẾT

Ký hiệu: **ĐÃ** = đã thử, có verdict · **MỘT PHẦN** = chỉ thử trên khung chung (S1 pool + gate p15 + arm 7%/trailing + alts USDT-M + long-only), hoặc thử với thiết kế không công bằng · **CHƯA** = chưa thử. ⚑ = "alpha mới" nhưng vẫn cắm lên khung chung, nên không phải phép thử độc lập của trục đó.

### 2.1 Tín hiệu / dữ liệu

| ô | trạng thái | vòng / verdict | ghi chú |
|---|---|---|---|
| Giá-volume lưới 1h làm feature selector | ĐÃ ⚑ | FS 0/16; S1_OI12 NULL; Stage2/3; ARM44; G015ABL | chỉ ở vai trò feature S1, chấm theo khung chung |
| Trend/mom/vol cross-section | MỘT PHẦN | TREND_RANK_IC: IC **âm** ngoài CI (vol −0,09 @24h, mom −0,049) → "NULL vì trend giả thuyết long" | **tín hiệu reversal/low-vol có thật nhưng chưa từng được thử như book L/S** |
| Sự kiện 1' thị trường (BIG_DOWN, MOM15) | ĐÃ (là edge) | đang chạy; BIG_UP/MEDIUM NULL (thiếu power); LEVEL_SENSITIVITY | |
| Sự kiện 1' từng coin | MỘT PHẦN | REVERSAL_BOUNCE NULL (có lực, long 24h cố định); P-COIN DEDUP ≈0; PUMPDUMP n=49 | chưa có "flush thanh lý từng coin" (giá + OI rơi) |
| Funding | ĐÃ (long) / MỘT PHẦN (hedged) | FACTOR (D10−D1 −0,25%/24h ngoài CI, nhưng NO-GO long-only); TOPK_ROTATE/K13/LONG NO-GO; SHORT_CARRY NO-GO | carry có hedge, turnover thấp, universe thanh khoản: chưa |
| OI (5 cột) | ĐÃ (long) | OI_STUDY: ΔOI cao = decile **tệ nhất** (−0,4165%) → "chỉ dùng được phía short"; H3 tách được −5,5% ở MOM15 nhưng "không lọc coin" | phía short/avoid **chưa thử** |
| LS global/toptrader/taker | ĐÃ (long) | LS_TAKER NO-GO/NULL; CROWDED_LONG NULL | hướng "LS cao ⇒ tệ" nhất quán nhưng dưới MDE |
| OFI/aggTrades | ĐÃ ⚑ | S1_FREE_OFI_V3: +1,76pp edge selector; OFI_MONEY tiền = 0 | **chỉ ở dạng feature 1h cho S1**; chưa dùng ở thang phút cho gate/timing |
| L2 order book (bookDepth 2023+) | CHƯA | nguồn có (`AGENTS.md` task 014) | |
| Premium index / basis 1m | CHƯA | đã verify dữ liệu (task 022) nhưng chưa dùng làm tín hiệu | |
| Liquidation | CHƯA | `liquidationSnapshot` không còn; chỉ có thể dùng proxy (OI↓ + giá) | |
| On-chain | CHƯA | — | |
| Listing/delisting | CHƯA | RECON_EVENT_ALPHA: GO có điều kiện, **bước 2 chưa chạy**; nhánh delisting→short bị loại vì owner né short; file còn marker merge-conflict | 648 event / 4,5 năm; 0/709 trùng với entry T170 |
| Unlock / leverage-tier | CHƯA (bị chặn bởi dữ liệu) | EVENT_DATA_SURVEY: không có nguồn lịch sử đáng tin | |
| Cross-exchange (funding/basis chéo sàn, venue khác) | CHƯA | nhắc tới ở `power_wall.md` §4, EVENT_DATA_SURVEY | |
| Regime/breadth (làm gate) | ĐÃ ⚑ | 9 bước B2: BR/BRC/BRCT50/MA200/trend-detector/DD-throttle/pacing… đều NULL | tất cả là gate trên cùng khung |

### 2.2 Nhãn / mục tiêu train

| ô | trạng thái | vòng |
|---|---|---|
| `retEnd_4h>0.015` (net015, gate tier-1) | ĐÃ ⚑ | G5 labels, SELECTOR_NET015_GATE |
| `retEnd_72h>0.015` | ĐÃ ⚑ | GATE_H72: **tệ hơn**, ngoài CI |
| `maxFav` 4h/72h | ĐÃ ⚑ | S1_MAXFAV, LABELH, C4H (tiền = 0) |
| `g1lite` 72h (deploy) | ĐÃ ⚑ | H72 |
| `retEnd_h` liên tục / PnL luật thoát | ĐÃ ⚑ | MONEY_RANKER, PNL_RULER (tiền = 0) |
| Nhãn gate = kết cục top-K | ĐÃ ⚑ | GATE_TOPK_LABEL_SIM: **tệ hơn** |
| Horizon ngày/tuần, portfolio-level return | CHƯA | chỉ có probe mô tả 168h (RESEARCH_SHORT) |

Toàn bộ trục nhãn được chấm **trong pool P32 do S1 định nghĩa**, với nhãn (b) là **luật thoát WEAK cap 0,03**. Vì vậy đây là cùng một khung ⚑ (`RESULT_TAIL_ROBUST_RULERS.md` §9.5 tự ghi "đo trên sân của S1").

### 2.3 Hướng giao dịch

| ô | trạng thái | chi tiết |
|---|---|---|
| Long-only | ĐÃ (cạn trong khung) | toàn bộ khoảng 200 vòng |
| Short đơn (mirror S1) | ĐÃ (probe offline) | RESEARCH_SHORT: short leg gross khoảng 0 (+0,03%/72h), net −0,77%. **Nhưng spread L/S lowK−highK +0,83%/72h, t=6,47 chưa được đánh giá như một book** |
| Short carry | MỘT PHẦN (không công bằng) | SHORT_CARRY: xem 2.9 |
| **Long-short market-neutral cross-section** | **CHƯA** | không có vòng nào chấm *spread* sau phí làm tiêu chí; mọi factor test đều chấm "decile long net > 0" |
| Long có hedge BTC | ĐÃ (counterfactual) | HEDGE_OVERLAY_A: β bị triệt, CAGR +1,7pp, nhưng ICC tăng 4,3×, maxDD −17,3%, UW 266 → NULL theo tiêu chí ICC |
| Long có hedge rổ alt / sector | CHƯA | — |

**Trạng thái kỹ thuật thật của ô long-short [ĐO]:** `createOrderSELL`/`ENABLE_SHORT` đã bị xóa ở `5f40a90` (2026-09-03, "xoá 40 cơ chế trơ"); `SimulatorMarketLevelInvertedSelector.java` (555 dòng) cũng bị xóa. Engine chỉ còn `calTp()` hai chiều. Funding cho SELL trong code draft **sai dấu**: short bị trừ khi funding dương, trong khi Binance thật là short nhận [`DESIGN_HEDGED_BOOK.md` §1a-b; `RESEARCH_SHORT.md` §1.2; `AUDIT_APPLIED.md` F9]. Portfolio-level leg không có chỗ gắn, vì state đánh địa chỉ theo `symbolId` [`DESIGN_HEDGED_BOOK.md` §1c]. ⇒ Ô này **chỉ thử được bằng harness Python**; Java sim cần viết lại khoảng 630–870 dòng. Thêm nữa, owner "long-only 1x, cực kỳ né short" (`RECON_EVENT_ALPHA.md` §0) là rào về khẩu vị.

### 2.4 Universe

| ô | trạng thái |
|---|---|
| Alts USDT-M (khoảng 627–863 symbol) | ĐÃ (mọi vòng) |
| Cắt theo thanh khoản | ĐÃ: COST_LIQUIDITY — decile kém thanh khoản **lãi nhất** → không cắt |
| Chỉ majors / top-50 làm universe giao dịch | CHƯA (top-50 chỉ dùng làm breadth cho gate) |
| Spot, COIN-M, sàn khác | CHƯA |

### 2.5 Tần suất quyết định

1' (sim) ĐÃ · 5' grid ĐÃ (5MGRID NULL) · 15' ĐÃ (sel15) · 4h rotate ĐÃ (RANGE4H NO-GO) · 8h rotate ĐÃ (funding) · 24h hold ĐÃ (harness 0-sim) · **ngày/tuần rebalance portfolio: CHƯA**.

### 2.6 Cấu trúc exit — ĐÃ ⚑ (cạn trên tập entry này)

Arm 7→3% (ARM3_3NEN), SL 7→3 (SL_7_TO_3), hinge (TRAIL_HINGE), ladder (TRAIL_LADDER), cap 10/30 (TRAIL_CAP_1030), peak-close F3 (PEAK_CLOSE), giveback 1/2/5, TP nhỏ + SL nhỏ không DCA (FAMILY2 **0/4, CAGR −20%**), early cut (SHAPE1 0/4), bỏ time-stop / DCA tới chết (EXIT_STRUCT 0/4), 17 policy (EXIT_FIT), conditional exit (F2), trên nền nhiều lệnh (EXIT_HIGH_N 0/6). **Lý do cấu trúc [ĐO, `RESULT_CAPACITY_DIAG.md` §1.5]:** exit chỉ xáo được dưới 5% tập lệnh, nên không thể là đòn bẩy. Cảnh báo: các vòng exit cũ chấm bằng "rate" do chính luật exit định nghĩa (H2 = đúng: Kendall τ(meanP, Calmar) = 0,333).

### 2.7 Sizing / portfolio construction — ĐÃ ⚑

VOL_TARGET (COIN giảm rủi ro thật, PORTFOLIO sai tham số), 2X_HALFSIZE, SIZE_COUNT, K_SWEEP/K_DENSITY/K12, CONC_CAP (không binding), BOOKCAP, DD_THROTTLE, PACING, BD_SIZE_ADAPT, CONF_SIZE (đã xóa), FLATGRID. Kết luận chung: size chỉ đổi mức (CAGR ↔ DD); UW ↔ breadth là trade-off nội tại. **Risk-parity giữa các sleeve độc lập: CHƯA**, vì chưa có sleeve thứ hai.

### 2.8 Gate / regime — ĐÃ ⚑

GATESCALE (+SWEEP, +KEEPLEG0, CALIB), GATEDYN/GD92 (không phân biệt được), GATE_RECAL (percentile cuộn 0/3), GATEFEAT, GATE_TOPK_LABEL, GATE_H72, REGIME_GATE/UPDOWN, BREADTH×4, TICK_BLOCK, FLATGATE (tệ hơn rõ). **Nút cổ binding thật là cổng AI** (99,995% ứng viên chết ở đó), nhưng mọi vòng chỉ vặn *ngưỡng/scale*, không thêm *thông tin mới ở thang phút* vào cổng.

### 2.9 Execution

| ô | trạng thái |
|---|---|
| Maker vs taker | MỘT PHẦN: EXECUTION_MAKER (offline, không có fill thật; hòa vốn cần p_fill 0,96–0,99) |
| LIMIT entry | ĐÃ trên reversal-bounce (adverse selection lớn) |
| Chi phí thật | ĐO: fee 0,05%/chân, slip trung vị 0,33%/chân, RT ≈ 0,76% ≈ giả định sim 0,8% (`RESULT_LIVE_FILLS_AUDIT.md`) |
| Slip có điều kiện ngay phút capitulation | **CHƯA ĐO** |

### 2.10 SHORT_CARRY có phải phép thử công bằng của carry có hedge, turnover thấp? → **KHÔNG**

[ĐO, `RESULT_SHORT_CARRY.md`]: Re-rank mỗi 8h (00/08/16 UTC) theo rate đã settle, top-decile trên cả **627 symbol** (kể cả coin kém thanh khoản), EW. Turnover 1 vế **34–36% mỗi chu kỳ**. Chi phí = taker 0,05%/chân + slip proxy 0,5×(h−l)/c mỗi chân, tính trên chính nhóm biến động nhất. Không stop squeeze. V3 dollar-neutral: **gross +0,0539%/chu kỳ**, cost 0,1666%, net −0,1127%.
- Với slip 1bp/chân: V1 net −0,0215%, CI [−0,1075; +0,0645] (chứa 0). Carry spread là thật: top-decile thu +0,0251%, bottom trả −0,0552%, chênh khoảng 0,24%/ngày. Tín hiệu bền: Spearman f_entry → f_cum 24h = 0,60 (`RESULT_FUNDING_FACTOR.md`).
- [SUY LUẬN] Điểm không công bằng: (1) không có dải trễ (hysteresis) / giữ tới khi rank đổi đáng kể. Với tín hiệu bền 0,60 thì turnover 34% mỗi 8h là thừa. (2) Không lọc thanh khoản. Slip proxy trên coin biến động là mức mà repo tự gọi là "không phải slip thật" (`RESULT_EXECUTION_MAKER.md`); proxy đó còn bảo thủ khoảng 1,6–2,2× so với slip live thật. (3) Không kiểm soát squeeze (p99 MAE +20%/8h). (4) V3 dùng cùng danh sách cho 2 chân, và median gross V3 [KHÔNG RÕ] (V1 median gross −0,11%, tức mean bị đuôi kéo). ⇒ Đó là **phép thử carry turnover cao trên universe bẩn**, không phải carry có hedge, turnover thấp.

---

## PHẦN 3 — KẾT LUẬN

### (i) "Cạn" đúng cho những vùng nào

1. **Xếp hạng coin bằng feature giá/volume/funding/OI/LS/OFI lưới giờ, mọi nhãn, trong pool S1**: tiền = 0 qua ít nhất 6 vòng độc lập về nhãn/feature/model (PNL_RULER, MONEY_RANKER, S1_MAXFAV, H72, OFI_MONEY, TAIL_ROBUST). **Cạn.**
2. **Hình dạng luật thoát trên tập entry hiện tại**: ít nhất 10 vòng, cơ chế chỉ đổi được dưới 5% lệnh. **Cạn.**
3. **Sizing / exposure / pacing / DCA / concentration**: chỉ đổi mức; trade-off UW ↔ breadth không phá được. **Cạn.**
4. **Vặn ngưỡng/scale/regime của gate hiện có** (gate-scale, GD92, percentile, MA200, breadth×4): **cạn**. Riêng *thông tin mới cho gate* thì chưa thử.
5. **BIG_DOWN: chọn coin / size / ngưỡng**: thiếu power (248 leg / 56 ngày), ngưỡng đã bị nhiễm DEV. **Không giải được trên DEV** (khác với "không có edge").
6. **Factor long-only xoay vòng 4h/8h bằng taker** (funding, range): chết vì cost × turnover, CI âm. **Cạn cho long-only turnover cao.**
7. **Hedge beta BTC** để tăng số cược độc lập: NULL có cơ chế (ICC tăng). **Cạn.**

Lưu ý cách đọc chữ "cạn": nhiều NULL ở nhóm B là **thiếu power** (MDE 2–4%/lệnh, `INVENTORY_RECENT_MEASURES.md`). "Cạn" ở đây nghĩa là *DEV không thể trả lời thêm*, không phải *đã chứng minh không có edge*.

### (ii) Ô CHƯA THỬ có tiên nghiệm hợp lý nhất (xếp hạng)

| # | ô | lý do dựa trên Phần 1 và bằng chứng đã có | dữ liệu / hạ tầng, chi phí ước lượng [SUY LUẬN] |
|---|---|---|---|
| **1** | **Book market-neutral cross-section, turnover thấp, universe thanh khoản** (long thấp / short cao theo funding, ΔOI, vol, reversal; rebalance ngày có hysteresis) | Tín hiệu **đã đo có dấu ổn định ở phía short**: vol IC −0,09 @24h; ΔOI Q9 tệ nhất (CI ngoài 0); funding D10−D1 −0,25%/24h (CI ngoài 0); spread S1 +0,83%/72h (t 6,47); V3 gross +0,054%/8h. **Trực giao với edge capitulation**, và có thể hoạt động đúng những quý hệ trống (2025Q2-Q3), tức là **đánh thẳng vào rào binding UW**. Rủi ro: squeeze đuôi (p99 +20%/8h), khẩu vị owner | Dữ liệu **đã có** (funding Aerospike, `raw/*.f32` 1m, OI panel). Harness Python 0-sim khoảng 1–2 ngày. **Không cần** Java SELL ở bước đo. Pre-reg: tiêu chí là *spread sau phí* + trần squeeze + so với null coin ngẫu nhiên |
| **2** | **Thông tin vi cấu trúc ở thang phút đưa vào gate/timing capitulation** (OFI 1'-5' từ aggTrades, premium/basis 1m, OI rơi làm proxy thanh lý, bookDepth 2023+) | Edge nằm ở **cửa sổ phút của capitulation** (§1d); gate là nút binding (99,995% ứng viên chết); OFI mới chỉ được thử ở dạng feature 1h cho S1. OI H3 cho thấy ΔOI tách được kết cục tại MOM15 (−5,5%, ngoài CI) nhưng chưa được dùng cho timing | aggTrades 630 symbol **đã tải** (OFI v3); premiumIndex free; bookDepth free từ 2023. Trung bình: khoảng 3–5 ngày build feature phút + đo offline trên chính các phút gate/BIG_DOWN. Cảnh báo: retrain p15 đổi admit-rate 3–3,7× và p15 đang có lỗ provenance |
| **3** | **Listing event (bước 2 của RECON)** | Độc lập với MOM15 (0/709 trùng), 648 event, causal-safe, free. Tiên nghiệm dấu cho long **yếu** (bản thân recon ghi vậy) | **Rẻ nhất**: 0-sim, khoảng nửa ngày (đo forward-return sau listing, sau phí). Sửa merge-conflict trong `RECON_EVENT_ALPHA.md` trước |
| **4** | **Cross-venue** (cùng alt perp trên Bybit/OKX; divergence funding/basis giữa các sàn) | Là nguồn duy nhất tăng **số quan sát trên cùng episode** để phân giải các ứng viên nhóm B (SEL_BIGDOWN +82%/leg, …) và kiểm độ bền của edge capitulation ngoài Binance. Divergence funding chéo sàn: chưa có tiên nghiệm cụ thể | Dữ liệu public nhưng phải crawl và chuẩn hóa symbol. Trung bình–cao (khoảng 1 tuần) |
| **5** | **Flush thanh lý từng coin** (giá rơi mạnh + OI rơi, không cần thị trường sụp) | Cùng họ phần bù thanh khoản với edge đang có, nhưng tần suất cao hơn nên có thêm episode. REVERSAL_BOUNCE (sụt 1%, nhỏ) và P-COIN level-dedup đã NULL. Biến thể mức sụt lớn có OI xác nhận thì chưa thử | Dữ liệu đã có (1m + OI 5m). 0-sim khoảng 1 ngày. Tiên nghiệm trung bình-thấp |

Không xếp hạng cao: long-only theo horizon tuần hoặc chỉ majors (alts drift âm dài hạn: median ret_365d −80,9% năm 2025, `RESULT_ALT_REGIME_WAVES.md`); unlock (không có dữ liệu sạch); on-chain (chi phí cao, không có tiên nghiệm trong repo).

### (iii) Cảnh báo: chính edge baseline có thể không thật, hoặc không hiện thực hóa được. Cách kiểm rẻ nhất

**Dấu hiệu đáng lo:**
1. Baseline tự trượt rào mới (top-1% 23,74%, TF50 âm, q* 19%).
2. MOM15 (tín hiệu live) không qua được trên riêng DEV (CI chứa 0).
3. S1 có IC tiền âm; phần "selector" 62% thực chất là timing của gate.
4. Ngưỡng BIG_DOWN được tune trên DEV và nằm ở local max. Nếu dùng ngưỡng trung bình của 5 điểm quét thì PnL BD chỉ khoảng 12,7k thay vì 16,3k, tức thổi phồng khoảng 3–4k/76k, khoảng 5% PnL [SUY LUẬN].
5. **p15 DEV (`pred.bin`) không tái lập được**: store feature đã mất, corr 0,762. Đuôi p15 (thứ mở cổng) chưa từng thấy ở live (0/8.986 mẫu ≥2,947%, trong khi DEV cùng quý có 10/8.831). Không loại trừ được khả năng một phần đuôi DEV là artifact của pipeline offline, vì 40 feature Tool1 vẫn "opaque", là lỗ leak chưa đóng (`LEAK_L1_REPORT.md` phần "CÒN LẠI").
6. 44% lãi 2025 nằm trong 5 ngày; 62% log-return nằm trong 6/18 quý.
7. Nhịp khả thi (sel15) chỉ cho 17,3%. Slip ngay phút sụp chưa đo.
8. 2026 đã bị "nhìn" ở dạng mô tả (phân phối p15 live/offline 2026H1, cửa sổ alt 2026-08). Mức nhiễm nhẹ nhưng cần ghi vào pre-reg.

**Kiểm rẻ nhất, theo thứ tự chi phí:**
1. **Jackknife theo sự kiện + bootstrap theo cụm episode** (0-sim, vài phút, dùng `printDone`/`sim.out` có sẵn): CAGR KEEPLEG0 và sel15 khi bỏ top-k cửa sổ sự kiện (k = 1, 3, 5, 9); CI khi resample theo cụm episode/ngày-BIG_DOWN (N ≈ 56–110) thay cho khối 72h. Pre-reg ngưỡng: ví dụ "bỏ top-3 episode mà CAGR vẫn > 0".
2. **DSR/PBO đúng chuẩn trên corpus sẵn có** (0-sim): corpus 448 run DEV (đã dùng ở TAIL50) cho độ phân tán SR giữa các phép thử. N lấy từ ledger PREREG (171). Báo DSR cho cả KEEPLEG0 nhịp 1' và sel15.
3. **Placebo tách timing khỏi selection** (0-sim, khoảng vài giờ; harness replay exit Python đã PASS parity trong `RESULT_EXIT_FIT.md`): giữ đúng phút vào lệnh, thay coin bằng (a) coin ngẫu nhiên từ universe, (b) coin ngẫu nhiên từ S1 top-32, (c) nhóm S1 bottom; cùng luật thoát. Cách này quy PnL cho gate, cho pool hay cho xếp hạng. Có thể thêm biến thể dịch thời gian p15 ±N giờ để kiểm edge có phụ thuộc đúng phút hay không.
4. **Holdout 2026 một lần duy nhất, có pre-reg** (Kaggle CPU khoảng 20–30 phút mỗi leg sau khi dựng bundle 2026; ticker có tới 2026-08-12): KEEPLEG0 ở **sel15** (cấu hình live thật) với model đóng băng (S1 cut20251231, p15 fold hiện hành, net015 cut20251231). Tiêu chí chính chốt trước: return > 0, entry/tháng ∈ [5; 30], PASS rào cứng; báo kèm top-1% share. **Điều kiện tiên quyết**: chốt pipeline p15 dùng cho 2026 = đúng pipeline live sẽ chạy. Nếu dùng store offline hiện tại (khác store DEV) thì phải ghi rõ đây là phép thử "chiến lược + pipeline mới". Cần nói trước khi chạy: khoảng 7 tháng chỉ phát hiện được thất bại lớn (âm, hoặc cổng không mở), không phân biệt được 27% với 10%.

---

## Phụ lục — thông tin đáng lưu cho session sau

- Baseline: KEEPLEG0 `99e42b75` (n1085, CAGR 27,14%, sel15 17,29%). T170 `efb793e2` là nền cũ, có đủ phân rã leg/năm/quý.
- Chưa có trong doc: PnL theo leg của KEEPLEG0; tách timing khỏi selection; DSR của incumbent; slip ngay phút capitulation; median gross của SHORT_CARRY V3.
