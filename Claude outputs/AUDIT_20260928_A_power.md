# A_power — "NULL có thông tin hay NULL vì mù?" (audit độc lập, 2026-09-28)

Phạm vi: các vòng 2026-09-12 → 09-28 trong `docs/result/RESULT_*.md`, `docs/RESULT_S1_FREE_OFI_V3_*.md`,
kèm `docs/notes/power_wall.md`, `docs/result/NBETS_RESULT.md`, `docs/result/COV_RESULT.md`,
`docs/ops/INVENTORY_RECENT_MEASURES.md`, `docs/result/RESULT_CAPACITY_DIAG.md`, `docs/runbooks/RISK_APPETITE.md`.
Chỉ đọc doc, không chạy sim. Nhãn: **[ĐO]** = số có trong doc (dẫn file:dòng/mục) · **[SUY LUẬN]** = lập luận/số học của auditor ·
**[KHÔNG RÕ]** = doc không đủ.

> Lưu ý nguồn: `docs/notes/ci_reality.md` mà đề bài nêu **không tồn tại** trong bản giải nén (chỉ được nhắc tên ở
> `COV_RESULT.md:35`, `SELECTOR_LADDER.md:47`). Con số "39–52 khối" của nó được `COV_RESULT.md:35-36` trích lại.

---

## 0. KẾT LUẬN (đọc trước)

1. **Phân bố 50 dòng (44 vòng, một số vòng tách theo giả thuyết):** INFORMATIVE-NULL **10 (20%)** · UNDERPOWERED
   **15 (30%)** · NEGATIVE **14 (28%)** · STRUCTURAL-NULL **7 (14%)** · POSITIVE (không phải NULL) **3 (6%)** ·
   KHÔNG CHẤM ĐƯỢC **1 (2%)**. Nếu tính là "loại trừ có thông tin" = INFORMATIVE + NEGATIVE thì được **48%**; phần
   "mù" (UNDERPOWERED + KHÔNG CHẤM) là **32%**; 14% bị loại bằng luật, không phải bằng dữ liệu.
2. **Mù tập trung ở 2 chỗ:** (a) trục **alpha mới / overlay sự kiện** (8/15 dòng UNDERPOWERED, MDE 2–4 %/lệnh trong
   khi ngưỡng thực tế là 0,3 pp/lệnh); (b) **thước TIỀN** của exit và của selector (EXIT_FIT, CLOSE_BIGGAP,
   PEAK_CLOSE, PNL_RULER). Chỗ **có thông tin**: tầng rate của exit (so ghép cặp, cùng điểm vào), nới gate
   (tụt chất lượng từng lệnh, ngoài CI), toàn họ funding/carry (âm có ý nghĩa), và tầng model rank-IC (CI ±0,002).
3. **Tầng equity/CAGR gần như mù hoàn toàn** [SUY LUẬN từ số ĐO]: MDE80 của ΔCAGR ≈ **3,6–7,3 pp** khi biến thể
   gần là tập con của baseline (GATE_RECAL), còn **≈ 15–19 pp** khi tập lệnh khác hẳn (GATESCALE, GD92_RECHECK,
   BREADTH). So với edge baseline (CAGR 27,14% ở nhịp 1′; **~17,3% ở nhịp live `sel15`**), mức cải thiện 10–20% edge
   = **1,7–5,4 pp** ⇒ **không phân giải được**, trừ trường hợp tốt nhất (thay đổi kiểu tập con, mức 20%, nền 1′).
   Chỉ **1/50 dòng** (GATE_RECAL) có CI ΔCAGR loại trừ được +3 pp.
4. **Kết luận có điều kiện cho "DEV cạn chưa":** *đã loại trừ có thông tin* các cải tiến **≥ ~10–25% chất lượng
   từng lệnh** trong họ exit trailing, việc nới gate, họ funding/carry, và cải tiến **≥ 0,01 rank-IC** ở feature.
   *Chưa nhìn thấy được* mọi cải tiến **cỡ 10–20% edge ở tầng CAGR**, mọi overlay trên MOM15 **< 2 %/lệnh**, và
   exit/selector chấm bằng **tiền** (điểm ước lượng +14% đến +25% chưa bị loại). "Cạn" dưới rào (b′) là hệ quả của
   **luật**, không phải của dữ liệu.

---

## 1. Chuẩn "có ý nghĩa thực tế" — chốt TRƯỚC khi lập bảng (không đổi sau)

| mã | áp cho | ngưỡng | nguồn baseline |
|---|---|---|---|
| (i) | ΔCAGR / equity | **±3 pp** | đề bài |
| (ii) | rate chất lượng. Không doc nào khai "Δ tối thiểu có ý nghĩa" cho rate ⇒ **[KHÔNG RÕ] ⇒ dùng 25% baseline**. "Nửa độ lệch" của phân phối từng lệnh không áp được (doc không in SD từng lệnh; `mP\|SL` −19 so với `mP\|SM` +8 cho thấy SD từng lệnh lớn gấp nhiều lần mean ⇒ d=0,5 sẽ là hiệu ứng khổng lồ). `win%` bỏ qua, xét qua `TSloss%` (ρ −0,992, `RULERS_CURRENT.md:119`) | meanP: KEEPLEG0 5,147→**1,29** · T170 5,244→**1,31** · T100 3,173→**0,79** · GD92 3,315→**0,83**; TSloss%: KEEPLEG0 10,32→**2,58 pp** · T170 9,73→**2,43** · T100 15,36→**3,84**; harness net/trade USD: P0 TEST 77,5→**19,4 USD** (`RESULT_CLOSE_BIGGAP` bảng §2: 46 827/604) | bảng mốc của từng doc |
| (iii) | rank-IC / IC / lift | **+0,01 rank-IC**; edge5 không có quy đổi ⇒ [KHÔNG RÕ] ⇒ 25% × edge5 baseline 15,21% = **3,8 pp** | `RESULT_S1_FREE_OFI_V3_UNIVERSE.md:108` |
| (iv) | net/lệnh (%/lệnh, %/chu kỳ, glift8, netm8, net_coin) | **0,3 pp/lệnh = 0,003** | đề bài |

**Ghi chú độ nhạy (bắt buộc):** `meanP` vừa là "rate" (ii) vừa là net/lệnh (iv). Phân loại chính dùng (ii) như đề bài
xếp; nếu dùng (iv) 0,3 pp thì TRAIL_LADDER, TRAIL_CAP_1030, ARM44 chuyển từ INFORMATIVE-NULL sang UNDERPOWERED (biên).
Quy tắc: **INFORMATIVE-NULL** = cận phía TỐT của CI (độ rộng quyết định của doc) < ngưỡng; **UNDERPOWERED** = CI bao
ngưỡng; **NEGATIVE** = cả CI nằm phía XẤU (loại 0); **STRUCTURAL** = bị loại bằng cơ chế/luật; **POSITIVE** = ngoài CI
phía tốt.

MDE80 quy đổi từ nửa độ rộng CI: MDE80 ≈ (c·1,96+0,84)/(c·1,96) × half ≈ **1,3–1,4 × half** với c ∈ {1,21; 1,48} [SUY LUẬN].

---

## 2. BẢNG CHÍNH (50 dòng)

Cột: vòng | câu hỏi | thước quyết định | n / n_eff | Δ điểm | CI (độ rộng) | MDE doc | ngưỡng áp | **phân loại**.
Mọi số là [ĐO] trừ khi ghi khác.

### 2.1 Trục EXIT (12)

| # | vòng | câu hỏi | thước | n / n_eff | Δ | CI | MDE doc | ngưỡng | phân loại |
|---|---|---|---|---|---|---|---|---|---|
| 1 | TRAIL_LADDER (09-23) | gap bậc thang theo đỉnh | ≥2 rate | 1089 ghép cặp | meanP L1 +0,005 · L2 +0,009 · L3 −0,006 | L1 @1,21 [−0,336;+0,398] (@1,48 [−0,419;+0,480]) · L3 [−0,069;+0,042] (§4 dòng 92-102) | — | (ii) 1,31 | **INFORMATIVE-NULL** (UNDER nếu dùng (iv)); CAGR: eq +3,3% không có CI ⇒ tầng CAGR KHÔNG CHẤM |
| 2 | TRAIL_CAP_1030 (ngày [KHÔNG RÕ], sau PEAK_CLOSE) | nới trần gap 10/30 | ≥2 rate | 1089/1090 | meanP −0,081; CAGR −0,23 pp | @1,21 [−0,439;+0,337] (§4.1) | — | (ii) 1,31 | **INFORMATIVE-NULL**; TRAIN/TEST ngược dấu |
| 3 | PEAK_CLOSE | đỉnh = CLOSE (F3) | ≥2 rate | 1039 vs 1089 | meanP **+0,750 (+14,3%)**; TSloss +1,72 XẤU; mP\|SM +1,40 TỐT | meanP @1,21 [−0,224;+1,794] (dòng 87) | — | (ii) 1,31 | **UNDERPOWERED** (cận trên 1,79 > 1,31); 1 TỐT/1 XẤU |
| 4 | EXIT_FIT (harness) | fit công thức gap, 17 policy | CI TEST block-ngày ≠0 | TEST **chỉ 54 block-ngày** (§2.2 dòng 122) | F3 **+16,01 USD/tr (+20,6%)** | [−14,43;+37,64] | — | (ii) 19,4 USD | **UNDERPOWERED** cho policy được chọn; 14 policy khác cận trên ≤ +12,7 ⇒ informative; F1 0.02+0.15p NEGATIVE [−21,65;−0,02] |
| 5 | CLOSE_BIGGAP (harness) | cap lớn / ratio | (a)+(b)+(c) CI | TEST n=604 | BB_50_12 ≈ **+19,4 USD/tr (+25%)** | raw [−9,5;+40,4], dùng để kết luận ×2,816 = **[−62,0;+100,8]** (§6) | — | (ii) 19,4 USD | **UNDERPOWERED** (CI rộng ~8× ngưỡng) |
| 6 | GIVEBACK_RATIO | ratio 1/2/5 | 0 XẤU & ≥2 TỐT | 1069–1071 | TSloss **+9,2…+10,3** XẤU; mP\|SL +9,7…+10,6 TỐT; meanP ±0,006 | TSloss [+6,87;+11,89] (§4) ; CI meanP **không in** | — | (ii) 2,58 | **NEGATIVE** (theo luật 0 XẤU; đánh đổi cơ học), meanP ≈ 0 [KHÔNG RÕ CI] |
| 7 | SL_7_TO_3 | arm 3% / SL cứng | ≥2 rate | 1085→1503…4219 | V1 meanP **−2,137** | [−3,834;−0,348] (@1,665) | — | (ii) 1,29 | **NEGATIVE** (V2–V4 thêm vỡ rào) |
| 8 | ARM3_3NEN | arm 3% trên 3 nền | ≥2 rate | 3 cặp | meanP −2,137/−1,390/−1,432; ΣPnL −34…−47% | tất cả loại 0 phía âm (§ bảng dòng 90-92) | — | (ii) | **NEGATIVE** |
| 9 | EXIT_HIGH_N | exit có mạnh lên khi n×2,4? | ≥2 rate | 2559/2632 ghép cặp | \|Δ\| ≤ 0,24 mọi rate | vd win% [+0,006;+0,145]@1,21 (§4.1) — nửa rộng ~0,07 pp | — | (ii) TSloss 3,84 | **INFORMATIVE-NULL** ở tầng rate; ΔCAGR GD92+CAP **+3,32 pp**, T100+HINGE +1,58 pp **không có CI** ⇒ tầng CAGR KHÔNG CHẤM |
| 10 | EXIT_STRUCT | bỏ TS168 / DCA tới chết | dCAGR + rào | 744–935 | dCAGR A1 −8,23 · A2 −10,18 · A3 −11,57 | P(>0) 0,090 / 0,001 / 0,000 (§1) | — | (i) 3 pp | **NEGATIVE** (A2/A3 bị **nhiễu size 1/6**, §2) |
| 11 | SHAPE1_EARLY_CUT | cắt lỗ sớm (3 giá trị) | (a)+(b′) | 744–2510 | CAGR 17,29 → −3,8/−6,9/+10,0/−7,0 | không in CI | — | (i) | **NEGATIVE** (3 arm lỗ); S3 bị loại bằng luật (b′) |
| 12 | FAMILY2_TP_SL | TP nhỏ + SL nhỏ | (a)+(b′) | 2270–2734 | CAGR −20,5…−22,9 | — | — | (i) | **NEGATIVE** |

### 2.2 Trục GATE / EXPOSURE (10)

| # | vòng | câu hỏi | thước | n / n_eff | Δ | CI | MDE doc | ngưỡng | phân loại |
|---|---|---|---|---|---|---|---|---|---|
| 13 | GATESCALE (09-12) | scale 1,30/1,70 vs nền | dCAGR | 2266 | T130 −8,3; T170 −3,9 | T130 [−19,4;+1,7]; T170 **[−18,1;+8,9]** (dòng 73-74) | ~10 pp (INVENTORY B11) | (i) 3 pp | **UNDERPOWERED** (T170); T130 loại được +3 pp |
| 14 | GATESCALE_SWEEP | nới gate → nhiều lệnh | ≥2 rate + rào | 1089→2559; relSE KHÔNG giảm theo 1/√n (§5) | meanP −0,57…−2,07; CAGR tới **+3,70 pp** (1,10) | meanP 1,00: [−3,156;−1,036] (§2) ; ΔCAGR **không có CI** | — | (ii) 1,31 | **NEGATIVE** (chất lượng/lệnh); tầng CAGR UNDERPOWERED (dùng CI ±10–13 pp của #13); rào UW/conc |
| 15 | GATESCALE_KEEPLEG0 | như trên, nền production | ≥2 rate | 1085→2549 | TSloss +2,58…+5,29 XẤU ở ≤1,40; CAGR 1,00 **+2,88 pp** | ngoài CI k=6 (§3); ΔCAGR không có CI | — | (ii) 2,58 | **NEGATIVE** (TSloss); tầng CAGR UNDERPOWERED |
| 16 | GD92_RECHECK (09-15) | gate rolling vs T100 | dCAGR + 3 rate | 2266 | dCAGR **+4,98** | **[−4,47;+16,09]** (dòng 148) | 10,3 pp | (i) | **UNDERPOWERED** |
| 17 | GATE_RECAL | siết gate theo phân vị p15 | dCAGR ghép cặp + rate | 868–1021 (tập con) | dCAGR −0,99/−1,51/−3,56; meanP Q999 +0,348 | dCAGR [−4,18;+1,75] / [−5,47;+2,20] / [−8,73;+1,24], sd 1,53/2,00/2,62 (§2); meanP [−0,36;+1,13] | — | (i) 3 pp; (ii) 1,29 | **INFORMATIVE-NULL** — dòng DUY NHẤT loại được +3 pp CAGR; nhịp 15′ NEGATIVE (−16,0 [−28,6;−5,5]) |
| 18 | GATE_ROOTCAUSE | gate theo đơn vị live | 4 điều kiện | 3 arm | meanP −3,30/−2,62/−2,39; dCAGR −0,93/−2,84/−7,68 | meanP [−4,90;−1,40] … (§3.3) | — | (ii) | **NEGATIVE** (+ UW 568–773) |
| 19 | BREADTH_GATE_SIM (BR) | gate breadth | u1–u5 | 1582, n_eff 742 (×1,224) | CAGR +0,85 pp | CAGR BR [16,08;46,16] (không phải Δ) | — | (i) | **STRUCTURAL** (NULL chỉ vì u1 = mục tiêu thiết kế n_eff×1,5); tầng CAGR UNDERPOWERED |
| 20 | BREADTH_CONT (BRC) | gate breadth liên tục | u1–u5 | 1689, n_eff 754 | CAGR +2,0 pp | — | — | (i) | **STRUCTURAL** (UW 2025 = 221 > 200 — ngưỡng **đã nới lên 250** sau đó; u1) |
| 21 | BREADTH_CONT_T50 | top50 | u1–u5 | 1776, n_eff 812 | CAGR +1,8 pp | — | — | (i) | **STRUCTURAL** (UW 223 > 200 cũ) |
| 22 | REGIME_UPDOWN (RA12) | up-gate 1,2 | u1–u4 | 1552, n_eff 769 | CAGR +1,2 pp | CAGR RA12 [16,99;47,60] | — | (i) | **STRUCTURAL** (UW 221/205 > 200 cũ; u3 UW ≤ 115) |

### 2.3 Trục SIZING / RỦI RO (3)

| # | vòng | câu hỏi | thước | n | Δ | CI | ngưỡng | phân loại |
|---|---|---|---|---|---|---|---|---|
| 23 | DD_THROTTLE | giảm phơi nhiễm theo DD | u1/u2 | n_eff 1091 | CAGR 27,38 (−1,9) | — | (i) | **STRUCTURAL** (UW 332 > cả 250 mới) |
| 24 | CONC_CAP_HIGHN | trần 15%/coin | cơ chế + rate | chặn 44/37 leg | conc 27,23→10,83%; 0 rate XẤU | — | — | **STRUCTURAL** (guard an toàn, không phải phép thử alpha; no-op trên KEEPLEG0 theo GATESCALE_KEEPLEG0 §1) |
| 25 | SIZE_COUNT | nhỏ size / nhiều lệnh | (a)+(b′) | 744–1885 | CAGR B4 +1,14 pp | không có CI | (i) | **STRUCTURAL** (đồng nhất thức: scale không đổi dấu TF50, §2 Fact #1) |

### 2.4 Trục SELECTOR / FEATURE / NHÃN (10)

| # | vòng | câu hỏi | thước | n / n_eff | Δ | CI | ngưỡng | phân loại |
|---|---|---|---|---|---|---|---|---|
| 26 | ARM44 | bỏ `rvol15m` | ≥2 rate (sim) + model | 140 238 tick; sim 1103 | sim meanP −0,004; model Δrank-IC +0,00197 (bất lợi), Δlift8 −0,0031 | meanP [−0,615;+0,705]; rank-IC [+0,00123;+0,00265] (dòng 92, 161) | (ii) 1,29; (iii) 0,01 | **INFORMATIVE-NULL** (sim; UNDER nếu (iv)); model: bất lợi nhỏ, có ý nghĩa thống kê, dưới 0,01 |
| 27 | STAGE2_TRAIN | +feature (6 biến thể) | Δrank-IC vs V0 & V5 | 140 238 tick | \|Δ\| ≤ 0,0053 | vd V3 [−0,00735;−0,00318] (§2.2), nửa rộng ~0,002 | (iii) 0,01 | **INFORMATIVE-NULL** |
| 28 | STAGE3_SIM | sim V0/V1/V5 vs mốc | ≥2 rate | 1085–1268 | V0 meanP −1,159 (NEGATIVE); **V1−V0 +0,491** | V0 [−2,310;−0,143]; **V1−V0 [−0,697;+1,865]** (§3) | (ii) 1,29 | **UNDERPOWERED** cho câu hỏi chính "SIM tách được feature thật khỏi nhiễu" |
| 29 | MODEL_RULER | dựng thước model | auc/lift/pacc | 140 238 tick | pacc 0,4821 (<0,5); net@8 −0,0079 | pacc [0,4810;0,4833] (§2) | — | **INFORMATIVE-NULL** (thước có lực; kết luận "không có skill xếp hạng" loại được) |
| 30 | MONEY_RANKER | ranker ra tiền? | Δglift8/netm8 | 140k tick | Δglift8 4h +0,00016 | nhiễu 4h −0,0001 đã **ngoài CI** ⇒ nửa rộng ~1e-4 (dòng 214) | (iv) 0,003 | **INFORMATIVE-NULL** (4h); 72h Δ −0,00266 "trong CI" ⇒ [KHÔNG RÕ] độ rộng |
| 31 | PNL_RULER | lift kinh tế trên PnL luật thoát | Δglift8 @1,21 | 8718–9658 tick | **+0,00170…+0,00301** | raw95 [−0,00063;+0,00392] … [+0,00033;+0,00565] (§4) ⇒ ×1,21 cận trên ~+0,0045…+0,0066 | (iv) 0,003 | **UNDERPOWERED** (CI glift8 rộng 4–5× mức glift8, §2(ii)) |
| 32 | S1_MAXFAV | nhãn maxFav | Δglift8 vs 2 đối chứng | 16 fold | +0,00072/+0,00184 (MFB72) | **không in** CI | (iv) | **KHÔNG CHẤM ĐƯỢC** [SUY LUẬN: cùng pool P32 ⇒ khả năng cao cùng độ rộng #31 ⇒ underpowered] |
| 33 | OFI_V3_UNIVERSE | OFI 630 symbol | Δedge5 + Δrank-IC CONFIRM | 13 914 tick / 229 block | Δedge5 +1,65 pp; Δrank-IC +0,00196 | [+0,62;+2,76] pp; [+0,00039;+0,00357] (dòng 71) | (iii) | **POSITIVE** nhưng cận trên < ngưỡng thực tế (0,0036 < 0,01; 2,76 < 3,8 pp) |
| 34 | OFI_V3_MULTISEED | xác nhận ≥3 seed | pooled | 229 block | Δedge5 +1,76 pp; Δrank-IC +0,00258 | [+0,50;+3,15]; [+0,00057;+0,00467] (§2) | (iii) | **POSITIVE** dưới ngưỡng thực tế |
| 35 | OFI_MONEY | OFI ra tiền? | Δnet_gr1dv @f=0,006, K=8 | 9657 tick, pool 475k | Δnet_coin B2 **−0,057 pp** | CI5 [−0,215;+0,096] pp (§4.3) | (iv) 0,3 pp | **INFORMATIVE-NULL** (loại được +0,1 pp) |

### 2.5 Trục ALPHA MỚI / OVERLAY SỰ KIỆN (15)

| # | vòng | câu hỏi | thước | N / N_blk | Δ | CI72h×1,21 | MDE doc | ngưỡng | phân loại |
|---|---|---|---|---|---|---|---|---|---|
| 36a | FUNDING_FACTOR T2 | long decile funding thấp | net 24h | 6585 / 487 | −0,191% | [−0,468;+0,086] | 0,50% | (iv) | **INFORMATIVE-NULL** |
| 36b | FUNDING_FACTOR T3 | overlay f≤0 trên MOM15 | net diff | ~7k / 301 | **+0,948%** | **[−0,013;+1,909]** | **2,00%** | (iv) | **UNDERPOWERED** (doc tự ghi "chưa đủ lực", §6) |
| 37 | FUNDING_TOPK_K13 | K=1..20 | net/chu kỳ | 4382 / 487 | K≥3: −0,15…−0,22% | loại 0 phía âm; K=1 [−0,784;+0,051] | 0,2–0,5% | (iv) | **NEGATIVE** (K=1: informative, cận trên +0,05 < 0,3) |
| 38 | FUNDING_TOPK_LONG | long funding cao | net/chu kỳ | 487 blk | −0,180% | [−0,272;−0,089] | — | (iv) | **NEGATIVE** |
| 39 | FUNDING_TOPK_ROTATE | thu funding rotate | net/chu kỳ | 487 blk | −0,15…−0,22% | loại 0 phía âm | 0,20% | (iv) | **NEGATIVE** |
| 40 | SHORT_CARRY | short carry | net/chu kỳ | 487 blk | −0,11…−0,38% | loại 0 phía âm | — | (iv) | **NEGATIVE** |
| 41a | OI_STUDY H1 | ΔOI cross-section | Q9 net | — | −0,417% | [−0,704;−0,129] | — | (iv) | **NEGATIVE** (cho long) |
| 41b | OI_STUDY H2 | OI–giá phân kỳ | tương phản | — | +0,066% | [−0,326;+0,458] | — | (iv) | **UNDERPOWERED** |
| 41c | OI_STUDY H3 | ΔOI overlay MOM15 | tercile | 7128 | **−5,51%** | **[−9,48;−1,54]**, pNull 0,001 | 5,15% | (iv) | **POSITIVE** (thông tin thật) — bị gạt bằng tiền lệ "filter cấp-coin vô hiệu", **không có sim kiểm** [KHÔNG RÕ] |
| 42 | LS_TAKER H1/H2/H3 | ls_global / smart-retail / taker overlay | Q9−EW / tercile | — | −0,058 / −0,032 / −1,080% | [−0,456;+0,340] / [−0,422;+0,357] / [−5,145;+2,985] | 0,32 / 0,31 / 2,36% | (iv) | **UNDERPOWERED** (cả 3 cận trên > 0,3) |
| 43 | REVERSAL_BOUNCE | bounce long | net DEV | 1 179 302 (ICC 72h 0,057) | −0,080% | [−0,515;+0,355] | 0,43% | (iv) | **UNDERPOWERED** (biên: 0,355 > 0,3; INVENTORY xếp informative theo ngưỡng 0,5) |
| 44 | BIGUP_MEDIUPDOWN | 3 level cũ | net DEV | 89/316/158 | +0,87/+1,84/+1,25% | chứa 0 (p 0,63/0,94/0,73) | 4,00% | (iv) | **UNDERPOWERED** |
| 45 | LEVEL_SENSITIVITY | tăng N per-coin | 27 ô | N_eff **32/111/52** | DEDUP ≈0/âm | — | 2,00 / >4,00% | (iv) | **UNDERPOWERED** |
| 46 | CROWDED_LONG | crowded-long (rủi ro/timing) | ON−OFF | N=30/90 | EW −0,22/−0,28%; **MOM15 −2,42/−2,56%** (OOS cùng dấu) | chứa 0 | 0,53% / 1,91% | (iv) | **UNDERPOWERED** |
| 47 | HARNESS_CONTROL (neo) | MOM15 trên riêng DEV | net | 3167, ICC(day) 0,50 | **+1,28%** | **[−0,72;+3,28]** | 2,00% | (iv) | **UNDERPOWERED** — **chính tín hiệu đang chạy live cũng không chứng nhận được trên DEV** |

Tổng dòng theo trục: exit 12 · gate 10 · sizing 3 · selector 10 · alpha 15 = **50**.

---

## 3. TỔNG HỢP

### 3.1 Phân bố

| loại | số | % | exit | gate | sizing | selector | alpha |
|---|---|---|---|---|---|---|---|
| INFORMATIVE-NULL | 10 | 20% | 3 | 1 | 0 | 5 | 1 |
| UNDERPOWERED | 15 | 30% | 3 | 2 | 0 | 2 | 8 |
| NEGATIVE | 14 | 28% | 6 | 3 | 0 | 0 | 5 |
| STRUCTURAL-NULL | 7 | 14% | 0 | 4 | 3 | 0 | 0 |
| POSITIVE (không phải NULL) | 3 | 6% | 0 | 0 | 0 | 2 | 1 |
| KHÔNG CHẤM ĐƯỢC | 1 | 2% | 0 | 0 | 0 | 1 | 0 |

Độ nhạy [SUY LUẬN]: dùng (iv) 0,3 pp cho meanP ⇒ INFORMATIVE 7 / UNDERPOWERED 18 (36%). Dùng ngưỡng "10% edge"
(≈0,52 pp meanP) ⇒ giữ nguyên như bảng chính.

### 3.2 Loại nào tập trung ở trục nào

- **Exit:** 9/12 là NEGATIVE hoặc INFORMATIVE ở **tầng rate**. Có một lý do cơ chế đã đo: exit chỉ xáo lại được
  **≤ ~5% tập lệnh** (khóa symbol 5,35–5,46%, `RESULT_CAPACITY_DIAG` §1.5). 3 dòng UNDERPOWERED đều là các phép
  **chấm bằng tiền/net-per-trade** (EXIT_FIT, CLOSE_BIGGAP, PEAK_CLOSE), trong đó điểm ước lượng tốt nhất là +14% đến +25%.
  ⚠️ Mọi kết luận exit đều chấm bằng rate, và `RESULT_CAPACITY_DIAG` §2.4 cho thấy thứ hạng theo rate và theo Calmar
  chỉ có Kendall τ = 0,333 ⇒ **tầng rate có thông tin, nhưng về một đại lượng không phải tiền**.
- **Gate/exposure:** nới gate ⇒ **NEGATIVE thật** (chất lượng từng lệnh, ngoài CI ở mọi điểm ≤ 1,40). Đồng thời
  CAGR **tăng** về điểm (+2,9 đến +3,7 pp ở 1,00–1,10) mà không có CI ⇒ thước theo **từng lệnh** phạt việc thêm lệnh
  kể cả khi tổng PnL có thể tăng [SUY LUẬN]. Họ breadth/regime **đều STRUCTURAL**, bị loại bằng UW, một thống kê
  chuỗi đơn **không được bootstrap theo thiết kế** (`AUDIT_READJUDICATE_CI_RESCORE.md:113`: *"UW KHONG duoc bootstrap"*),
  với ngưỡng đã bị nới **120 → 200 (09-16) → 250 (~09-24)** (`RISK_APPETITE.md:11,136`) mà **không chấm lại**
  BRC (221), BRCT50 (223), RA12 (221), BR0 (221) [KHÔNG RÕ owner có chấm lại ngoài doc không].
- **Sizing:** toàn STRUCTURAL (đồng nhất thức toán học, hoặc luật), đúng bản chất.
- **Selector/feature:** tầng model **có lực** (Δrank-IC CI ±0,002 ≪ 0,01) ⇒ phần lớn là INFORMATIVE. Nhưng
  chuyển sang tầng tiền thì kết quả chia đôi: OFI_MONEY (pool mở rộng, CI ±0,15 pp) **có thông tin**, còn
  PNL_RULER (pool P32) thì **mù** (CI glift8 ±0,3–0,4 pp).
- **Alpha mới:** **mù nhiều nhất**, 8/15 dòng. Các ý tưởng "đứng riêng" (funding/carry rotate) đều **NEGATIVE rõ**
  vì chi phí. Các **overlay có điều kiện trên MOM15** (funding ≤ 0: +0,95%; crowded-long: +2,4% nếu né; taker; OI
  H3) đều có MDE ≥ 2 %/lệnh ⇒ không phân giải được, và một overlay đã **có ý nghĩa** (OI H3) thì lại bị gạt bằng
  tiền lệ thay vì bằng thí nghiệm.

### 3.3 Power ceiling tổng thể [SUY LUẬN từ số ĐO]

| tầng | nửa rộng CI điển hình [ĐO] | MDE80 ≈ 1,35×half | edge baseline | MDE / edge | 10–20% edge có thấy không? |
|---|---|---|---|---|---|
| **CAGR, đơn lẻ** | T170 CI95 [17,17;43,86] ⇒ ±13,3 pp (`RESULT_REGIME_UPDOWN` §1) | ~18–19 pp | 27,14% (1′) / 17,3% (sel15) | 70% / 110% | **KHÔNG** |
| **ΔCAGR ghép cặp, tập lệnh khác nhau** | ±10,3–13,5 pp (GD92_RECHECK, GATESCALE) | ~14–19 pp | như trên | 52–70% / 81–110% | **KHÔNG** |
| **ΔCAGR ghép cặp, biến thể là tập con** | sd 1,53–2,62 ⇒ ±3,0–5,1 pp (GATE_RECAL §2) ; NBETS exit-param MDE80 6,0–7,7 pp, sàn 3,78 pp | 3,6–7,3 pp | như trên | 13–27% / 21–42% | **chỉ ở mức 20%, nền 1′, với thay đổi kiểu tập con**; nền sel15: không |
| **meanP, exit ghép cặp (cùng điểm vào)** | ±0,34–0,44 (TRAIL_LADDER, TRAIL_CAP) | 0,46–0,60 pp | 5,15–5,24 | 9–12% | **CÓ** (≥ ~12%) — nhưng meanP ≠ tiền (τ 0,33 với Calmar) |
| **meanP, tập lệnh khác nhau (gate/feature)** | ±0,56–1,15 (GATESCALE, STAGE3, ARM44, GATE_RECAL) | 0,76–1,56 pp | 5,15 | 15–30% | **10%: không; 20%: biên** |
| **net/lượt (glift8), pool P32** | raw95 ±0,22–0,35 ⇒ ×1,21 ±0,27–0,42 (PNL_RULER §4) | 0,37–0,57 pp | gross8 1,33%; net@0,8% 0,53% (CI của chính mức này [−0,14;+1,19]) | 28–43% gross / 70–110% net | **KHÔNG** |
| **net/coin, pool mở rộng B2** | CI5 ±0,15 pp (k=5) ⇒ ~±0,10 ở ×1,21 (OFI_MONEY §4.3) | ~0,14 pp | gross ~1,24% | ~11% | **CÓ** ở mức 20% |
| **rank-IC (model)** | ±0,002–0,003 (STAGE2, ARM44, OFI) | ~0,003–0,004 | \|IC\| 0,05 | ~7% | **CÓ**, nhưng pacc 0,482 < 0,5 (MODEL_RULER): tầng model **không** là tầng tiền |
| **%/lệnh sự kiện (MOM15-type)** | ±2,0 (MOM15 DEV [−0,72;+3,28]) | **2,0–4,0%** (HARNESS_CONTROL §4) | MOM15 DEV +1,28% | **156–310%** | **KHÔNG — kể cả chính edge 100%** |

Về n_eff: con số "~300 khối 72h" khớp **N_blk = 301** của tập sự kiện MOM15 (`RESULT_FUNDING_FACTOR` §6),
229 block ở OFI CONFIRM, 487 block ở cross-section; T170 có `n_eff_total` = 606 lệnh hiệu dụng
(`RESULT_BREADTH_GATE_SIM` §1); chuỗi gate MỞ chỉ có **39/52 khối có dữ liệu** (`COV_RESULT.md:35-36`). Nút cổ thật là
**tỉ số tín/nhiễu và số episode độc lập**, không phải số dòng: tăng N ×142–186 thì N_eff vẫn đứng yên 32/111/52
(`RESULT_LEVEL_SENSITIVITY` §0); GATESCALE_SWEEP §5 cho relSE của meanP **tăng** 0,124 → 0,175 khi n tăng 2,35×.
⚠️ Chuỗi xếp hạng "dày" bị **hiểu thiếu sd ~21%** ở khối 72h (độ phủ 0,896, `f = 1,21`, `COV_RESULT` §4/§6.2) ⇒
các CI model dùng `inflate(1)=1,0` hoặc `k=2` (1,1774 < 1,21) như OFI_V3_UNIVERSE, ARM44 là **hơi hẹp** so với mức hợp lệ.

**Trả lời thẳng:** hệ **không** đủ độ phân giải để phân biệt một cải tiến 10–20% edge ở tầng CAGR/equity (MDE80
gấp 1,3–11 lần mức cải tiến đó tùy loại thay đổi và nền). Hệ **đủ** ở tầng rate cho exit ghép cặp và ở tầng rank-IC,
nhưng cả hai đều đã được đo là **tương quan yếu với tiền** (CAPACITY_DIAG τ 0,33; MODEL_RULER pacc 0,482;
MONEY_RANKER "thống kê lên, kinh tế = 0").

---

## 4. Các vòng mà verdict trong doc DIỄN GIẢI QUÁ MỨC (trích nguyên văn)

1. **PNL_RULER §0(3)**: *"Nói dứt khoát: **alpha XẾP HẠNG trên 45 feature = 0 ngoài CI, ở CẢ 2 thước**"* — Δglift8
   có điểm ước lượng +0,17 đến +0,30 pp/lượt, cận trên raw95 tới **+0,39 đến +0,57 pp**. "Không khác 0" ≠ "= 0"; CI
   chưa loại được một lift cỡ 0,3–0,5 pp/lượt, tức cỡ **60–100% của net 0,53%**.
2. **LS_TAKER §0**: *"⇒ **(4) BA CỘT NÀY KHÔNG DÙNG ĐƯỢC — ĐÓNG TRỤC DỮ LIỆU OI HOÀN TOÀN (đủ 5/5 cột).**"* — H3
   có CI [−5,15;+2,98] với MDE 2,36%; H1/H2 có cận trên +0,34/+0,36 pp > 0,3. Không có ô nào chứng minh được hiệu
   ứng bằng 0. Trong cùng trục OI, H3 của OI_STUDY lại **có ý nghĩa** (−5,51% [−9,48;−1,54]).
3. **OI_STUDY §0 H3 (diễn giải thiếu)**: *"**Nhưng** (a) đây là **split cấp-coin** — pre-reg §1.H3 + bài học repo
   **đã biết mọi filter cấp-coin VÔ HIỆU**"* — một tín hiệu vượt CI bị gạt bằng tiền lệ, không phải bằng sim.
   Đây là ứng viên **âm tính giả**, ngược chiều với các vòng khác.
4. **CROWDED_LONG §0(3)**: *"**ĐÓNG NỐT trục crowded-long/positioning.**"* — overlay MOM15 −2,42/−2,56% với OOS
   cùng dấu (−3,72/−7,12%), CI chứa 0, MDE nhánh ON 1,91% ⇒ underpowered, chưa bị bác.
5. **CLOSE_BIGGAP §6**: *"⇒ **Dong huong nay.**"* — BB_50_12 có điểm +25% net/trade, CI dùng để kết luận
   [−62,0;+100,8] USD/tr (rộng ~8× ngưỡng 19,4); TEST gộp chỉ có ~54 block-ngày (`RESULT_EXIT_FIT` §2.2). Lý do đóng
   hợp lệ duy nhất là cơ chế (harness không định giá chiếm slot), **không** phải thống kê.
6. **RESULT_CAPACITY_DIAG §4.3**: *"**Khong** dau tu them vao exit (P0, hinge, ladder, peak-close, 17 policy = 4 vong
   NULL)"* — chính doc đó (§2.4) kết luận các NULL exit đã dùng **thước sai**, còn PEAK_CLOSE/EXIT_FIT/CLOSE_BIGGAP là
   underpowered ở thước tiền. Lập luận "exit chỉ xáo được ≤5% lệnh" là cơ chế đúng, nhưng nó giới hạn **số lệnh**, không
   giới hạn **PnL của nhóm đuôi** (TRAIL_LADDER đo được nhóm peak ≥ 50% có ΣPnL +10 483/+13 630 USDT, CI loại 0,
   dù đó là hậu-chọn).
7. **INVENTORY_RECENT_MEASURES §6.3**: *"Da so ket qua NULL gan day la DANG TIN (nhom A: 16) hoac bi loai vi rang buoc
   cung/co che (nhom C: 69) ... ra soat lai vo nghia"* — gộp các NULL do vỡ UW (thống kê chuỗi đơn, không có CI,
   ngưỡng sau đó đã nới 200 → 250) vào nhóm "không phải câu hỏi thống kê". UW **là** một ước lượng nhiễu. Kết luận
   "rà soát lại vô nghĩa" quá mạnh ở ít nhất NOBD_READJUDICATE (UW 131 > 120 cũ), BRC/BRCT50/RA12 (221–223 > 200 cũ).
8. **GATESCALE_SWEEP §0/§7(c)**: *"tang lenh KHONG giam rui ro trong du lieu nay"*, *"moi thu do rui ro deu XAU di
   don dieu"* — phần rate (NEGATIVE) là vững; phần rủi ro (UW 92→248, SD ret năm 9,92→22,00 pp) dựa trên **1 đường
   equity và 5 điểm năm**, không có CI. Nên phát biểu là "quan sát", không phải "đo được đơn điệu".
9. **LEVEL_SENSITIVITY §0**: *"sau khi tăng N, **không** level-signal nào ... còn đáng theo"* — doc có tự rào ("đã có
   lực tới ~2%/lệnh"), nhưng câu kết vẫn được đọc như đóng hẳn, trong khi MDE là 2 đến >4 %/lệnh, gấp 7–13× ngưỡng
   0,3 pp.
10. **SHAPE1_EARLY_CUT §0.4**: *"KẾT LUẬN CỨNG ... KHÔNG THỂ đạt (a)+(b′) bằng chỉnh tham số ⇒ PHẢI ĐỔI HỌ CHIẾN
    LƯỢC"* — dựa trên 4 arm cộng luật (b′). Với (b′) thì câu này đúng theo cấu trúc (SIZE_COUNT Fact #1), nhưng đó là
    kết luận **về luật**, không phải "đã đo hết không gian tham số".

Ngược lại, vài doc **tự khai đúng** mức power: FUNDING_FACTOR §6 (*"NULL của chúng là 'chưa đủ lực' cho hiệu ứng
≲2%"*), FUNDING_TOPK_K13 (tách "bác bỏ" với "không phân giải được"), HARNESS_CONTROL, power_wall ("tầng equity đã chết").

---

## 5. Rủi ro / lỗ hổng của chính audit này

- **Chọn ngưỡng (ii) = 25% baseline** là quy ước. Ngưỡng này làm các NULL exit trông "có thông tin"; đổi sang 0,3 pp thì
  4 dòng lật sang UNDERPOWERED (§3.1).
- Nhiều doc **không in CI** cho đại lượng quyết định (meanP của GIVEBACK_RATIO, ΔCAGR của mọi vòng exit, Δglift8 của
  S1_MAXFAV) ⇒ những ô đó được suy từ độ rộng của vòng anh em [SUY LUẬN] hoặc để trống.
- Các CI rate trong doc được tính trên **toàn bộ leg**, với bootstrap khối 72h; hệ số 1,21 và `inflate(k)` được áp
  không nhất quán giữa các vòng (1,0 / 1,1774 / 1,21 / 1,48 / 1,665 / 1,79 / 1,89 / 2,816) ⇒ so sánh độ rộng giữa các
  vòng chỉ nên xem như **bậc độ lớn**.
- Audit không kiểm lại số học của doc. Sai lệch nào ở nguồn sẽ lan sang đây.
