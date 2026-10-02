# AUDIT_LONG_BDSIZE_ANATOMY_20261003 — (L3a) chấm lại BD_SIZE_ADAPT bằng thước đúng · (L3b) giải phẫu PnL B0 theo thời gian & vị trí trong episode

- **Ngày:** 2026-10-03 (GMT+7). **Vai:** auditor/quant, CHỈ ĐỌC. 0 sim Java, 0 Kaggle, 0 sửa `.java`, 0 chạm 242/shadow, DEV ≤ 2025-12-31.
- **Script:** `research/analysis/long_bdsize_anatomy.py` (1 lần chạy ~1 phút, RSS < 1,5 GB). **JSON:** `docs/audit/AUDIT_LONG_BDSIZE_ANATOMY_20261003.json`.
- **Nguồn (md5 kiểm trong script, assert):**
  - L3a: 4 run **Oracle** `java/devrun/X1_GS_T170_2021_BD_{PARITY,DOWN50,DOWN25,UP50}` — printDone `efb793e2…` / `976de012…` / `fa2876cf…` / `f7d31da2…`; profile `x1_gs_t170{,_bd_down50,_bd_down25,_bd_up50}.properties` (PROFILE_HASH `0d0fa221…` / `4bc81ca2…` / `b42e689b…` / `c301b93c…`), log xác nhận `[BD-SIZE-ADAPT] mode=… N=120 thr=-0.03157`. Equity MTM ngày = `b + unP` từ `logs/sim.out` (snapshot 07:00 GMT+7 = 00:00 UTC), 1 643 return ngày 2021-07-01→2025-12-30.
  - L3b: B0 `~/kaggle_sim/out/de-p1` (printDone md5 `650c386f…`, n 2 517, ΣPnL 96 909, eq 131 908, jar `7368be46…`, profile `r4_kg0_k16_f015_g155` + override G2/FLAT3). Giá: `CLOSES_1H_v2.bin` md5 `58f56069e8e1a7c739011ddfa13e9636`. Lineage `data/meta/symbol_lineage_v2.csv`. quoteVol: `claude_master/1002/p0a_cache/qv` (ngày, từ 2021-09-01).
- **Artifact Kaggle cho BD_SIZE_ADAPT: KHÔNG có.** `ls ~/kaggle_sim/out | grep -iE 'bd|size|adapt'` chỉ ra `bdal-*`, `bdf000-par`, `bdjar-par` (thuộc BD-CHAIN, không liên quan). Vòng BD_SIZE_ADAPT chạy trên Oracle, **nền T170 (`X1_GS_T170_2021`), KHÔNG phải B0** ⇒ L3a so với **nền tương ứng (T170 parity)**, cùng nguồn Oracle↔Oracle (đúng luật AGENT_RUNBOOK). Kết luận L3a là về T170; chuyển sang B0 là suy luận (§1.5).

## KẾT LUẬN (rủi ro trước)

1. **L3a — verdict NULL của BD_SIZE_ADAPT ĐỨNG, nay bằng thước đúng.** AUDIT_LONG_LEVERS §3.5 nói đúng rằng luật PRIMARY cũ (≥ 2/3 rate chất lượng ngoài CI) **không thể PASS** với lever size. Chấm lại bằng return ngày MTM ghép cặp: ΔCalmar_MTM **−0,009 / −0,009 / +0,012** (DOWN50/DOWN25/UP50; CI ±0,15…±0,9 trên Calmar 2,47), ΔSharpe ≈ 0, ΔCAGR ≈ ±0,04 pp; **cùng exposure** ΔCalmar = **+0,000 / −0,004 / +0,003**. Không ô nào ngoài CI. Đây **không phải** "thiếu power": điểm ước lượng ≈ 0 tuyệt đối (ΔPnL thực +44 / −171 / +101 USD = 0,06–0,2 % ΣPnL).
2. **Cơ chế (ghép cặp theo lệnh):** đổi size leg BIG_DOWN dịch PnL leg BD **−2,15k / −1,19k / +1,98k**, nhưng BudgetManager **phân bổ lại ngân sách** sang leg không-BD **+2,20k / +1,02k / −1,88k** ⇒ tổng ≈ 0. Lever là **tái phân bổ trong cùng ngân sách**, không đổi rủi ro (β BTC 0,049–0,052, exposure TB 2,3–2,5 %). Phần "chọn lệnh" size-neutral **−1,24k / −1,05k / +0,63k** đến **100 % từ 2025** (một nhánh đường đi: 2,5–3,5 % lệnh khớp đổi exit, 5–10 lệnh lệch) — DOWN25 CI raw [−3,16k; −0,03k] chạm sát 0, inflate k=3 (×1,482) chứa 0, 1 năm ⇒ nhiễu đường đi, không phải chọn lệnh.
3. ⇒ **KHÔNG đề xuất pre-reg BD_SIZE_ADAPT trên B0.** Không có lợi ích Calmar ở cùng exposure (điều kiện đặt ra để đề xuất). Kỳ vọng trên B0 ≈ 0 vì cùng cơ chế tái phân bổ; một vòng Kaggle chỉ tốn multiplicity.
4. **L3b — múi giờ printDone = UTC+7 XÁC MINH:** 20 lệnh (seed, phút ≥ :57) căn với close 1h v2: offset −7h median |entry/close−1| **0,142 %** (13/20 < 0,5 %; 7 lệnh còn lại đều là phút sập 2024-08-05 07:57, cách close 2–3 phút), offset tốt nhì (−6h) **2,97 %**, 0h 6,78 %.
5. **L3b — KHÔNG tìm thấy lát nào ÂM có ý nghĩa ⇒ KHÔNG có ứng viên loại bỏ ex-ante.** k = **58 ô** (9 chiều), inflate √(2 ln 58) = **2,850**. Sau inflate: **0/58** ô khác phần còn lại. Raw: 4 ô TỐT hơn phần còn lại, 1 ô KÉM (n_open 6–15).
6. **Bốn giả thuyết loại bỏ đặt tên trước đều SAI CHIỀU** — lát đó là lát **lãi nhất**, loại đi mất tiền mọi năm: lệnh thứ >20 trong episode **−40,8k [−78,7; −17,0]** (5/5 năm âm), >30 lệnh mở **−22,7k [−58,7; −3,4]** (5/5), coin <30 ngày tuổi **−23,9k [−38,0; −12,5]** (5/5), vào lại cùng coin ≤72h **−29,6k [−60,2; −10,3]** (5/5). Cấu trúc thật của B0: **bắt đáy sâu trong cú sập đông đúc** (cuối episode, sổ đầy, BTC −4 %/4h) là nơi ROI cao nhất. Ứng viên âm duy nhất (raw) — **n_open 6–15**: ΣPnL vẫn **+5,9k**, loại ⇒ **−5,9k [−14,9; +3,6]**, 2/5 năm dương ⇒ **không phải ứng viên**.
7. **Mọi số L3b là hậu kiểm (k = 58 ô đã nhìn) trên DEV đã dùng 30+ lần** ⇒ chỉ đủ sinh giả thuyết. Ngay cả "tăng size khi sổ đầy / cuối episode" (raw tốt hơn) là lever tầng gate/episode: n_open > 30 có **17,1k / 22,7k (75 %) ở 2025** ⇒ dính power wall (AUDIT_LONG_LEVERS §2.4). **Không đề xuất pre-reg nào từ L3b**; nếu muốn, chỉ log forward `n_open`, `ep_rank`, `btc4h` lúc vào trên shadow.

## 1. L3a — BD_SIZE_ADAPT chấm lại (nền T170 parity, Oracle)

**Thước (chốt trong script trước khi chạy):** return ngày MTM `eq_t/eq_{t-1}−1`, bootstrap **ghép cặp** khối 10 ngày không chồng (cùng chỉ số khối cho nền và biến thể), NREP 2000, seed 20260905. CAGR (365 ngày), maxDD trên đường ngày, Calmar_MTM = CAGR/|maxDD|, Sharpe = mean/sd·√365. Exposure ngày = notional mở TB theo phút trong ngày UTC / equity đầu ngày. β = OLS return ngày vs return BTC ngày (close 00:00 UTC, v2). **Cùng exposure:** nền × c, **c = expoTB_biến thể / expoTB_nền** (tính trên toàn mẫu, cố định trước bootstrap). Ghép cặp lệnh: khớp `sym|start|level`, Δ size-neutral = Σ(p_x−p_b)/100·N_b + Σ_chỉ-x p_x/100·N_x − Σ_chỉ-b p_b/100·N_b, CI block-72h.

### 1.1 Điểm (toàn kỳ 2021-07-01→2025-12-30)

| tag | eq cuối | CAGR % | maxDD MTM ngày % | Calmar_MTM | Sharpe | exposure TB | β BTC | n | ΣPnL | ΣPnL leg BD | notional TB leg BD |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PARITY | 111 070 | 29,25 | −11,84 | 2,469 | 1,797 | 2,39 % | 0,051 | 1 089 | 76 070 | 16 254 | 1 761 |
| DOWN50 | 111 113 | 29,26 | −11,89 | 2,460 | 1,779 | 2,31 % | 0,049 | 1 091 | 76 114 | 14 101 | 1 440 |
| DOWN25 | 110 899 | 29,20 | −11,87 | 2,461 | 1,789 | 2,35 % | 0,050 | 1 090 | 75 899 | 15 062 | 1 616 |
| UP50 | 111 171 | 29,27 | −11,80 | 2,481 | 1,797 | 2,48 % | 0,052 | 1 088 | 76 171 | 18 234 | 2 060 |

(Khớp RESULT_BD_SIZE_ADAPT §7: eq 111 070/111 113/110 899/111 171, n 1 089/1 091/1 090/1 088.)

### 1.2 Δ ghép cặp vs nền (CI95 bootstrap block-10d)

| biến thể | ΔCAGR pp | ΔmaxDD pp | ΔCalmar_MTM | ΔSharpe | Δβ | Δexposure (pp) |
|---|---|---|---|---|---|---|
| DOWN50 | +0,01 [−1,38; +2,28] | −0,05 [−0,40; +0,83] | −0,009 [−0,310; +0,498] | −0,018 [−0,104; +0,034] | −0,002 [−0,007; +0,001] | −0,09 [−0,16; −0,04] |
| DOWN25 | −0,04 [−0,67; +0,89] | −0,02 [−0,19; +0,42] | −0,009 [−0,152; +0,240] | −0,008 [−0,045; +0,017] | −0,001 [−0,004; +0,000] | −0,04 [−0,08; −0,02] |
| UP50 | +0,03 [−1,69; +1,19] | +0,04 [−0,94; +0,36] | +0,012 [−0,883; +0,274] | +0,000 [−0,075; +0,057] | +0,001 [−0,001; +0,005] | +0,09 [+0,04; +0,15] |

Chỉ exposure dịch ngoài CI (đúng hướng thiết kế, cơ học). Không chỉ số hiệu quả nào ngoài CI.

### 1.3 Cùng exposure (biến thể vs nền × c)

| biến thể | c | ΔCAGR pp | ΔmaxDD pp | ΔCalmar_MTM | ΔSharpe |
|---|---|---|---|---|---|
| DOWN50 | 0,9628 | +1,19 [−0,28; +3,74] | −0,48 [−0,83; +0,38] | +0,000 [−0,288; +0,524] | −0,018 [−0,104; +0,034] |
| DOWN25 | 0,9819 | +0,53 [−0,13; +1,61] | −0,24 [−0,40; +0,22] | −0,004 [−0,139; +0,258] | −0,008 [−0,045; +0,017] |
| UP50 | 1,0370 | −1,15 [−3,20; +0,13] | +0,48 [−0,70; +0,79] | +0,003 [−0,915; +0,250] | +0,000 [−0,075; +0,057] |

Đọc: hạ size BD giảm exposure TB nhưng **không giảm CAGR** (ngân sách chảy sang leg khác) ⇒ so với nền co theo exposure, DOWN có CAGR cao hơn **và** maxDD sâu hơn đúng tỉ lệ ⇒ Calmar y hệt. Exposure TB không phải biến chi phối rủi ro ở đây.

### 1.4 Theo năm (ret % / maxDD % / Calmar; số "×c" = nền co về exposure biến thể)

| năm | PARITY | DOWN50 | DOWN50 vs nền×c | DOWN25 | DOWN25 vs nền×c | UP50 | UP50 vs nền×c |
|---|---|---|---|---|---|---|---|
| 2021H2 | 12,21 / −2,46 / 10,48 | 11,95 / −2,47 / 10,22 | 10,44 | 12,08 / −2,47 / 10,34 | 10,46 | 12,43 / −2,47 / 10,67 | 10,52 |
| 2022 | 19,58 / −11,84 / 1,65 | 18,91 / −11,89 / 1,59 | 1,65 | 19,25 / −11,87 / 1,62 | 1,65 | 20,23 / −11,80 / 1,71 | 1,65 |
| 2023 | 34,96 / −2,73 / 12,80 | 35,46 / −1,69 / 21,03 | 12,75 | 35,24 / −2,21 / 15,94 | 12,78 | 34,30 / −3,77 / 9,10 | 12,86 |
| 2024 | 32,06 / −6,60 / 4,84 | 29,88 / −6,81 / 4,38 | 4,82 | 31,01 / −6,70 / 4,61 | 4,83 | 33,90 / −6,41 / 5,27 | 4,87 |
| 2025 | 32,71 / −4,23 / 7,75 | 35,55 / −4,25 / 8,40 | 7,71 | 33,81 / −4,24 / 8,00 | 7,73 | 30,67 / −4,22 / 7,29 | 7,79 |

Calmar năm thắng nền×c: DOWN50 **2/5** (2023, 2025), DOWN25 **2/5**, UP50 **3/5** (2021, 2022, 2024). Lệch lớn duy nhất là 2023 (maxDD năm chỉ −1,7…−3,8 % ⇒ Calmar năm cực nhạy) và đổi dấu giữa DOWN/UP theo năm ⇒ không có hướng nhất quán.

### 1.5 Ghép cặp theo lệnh — tách "chọn lệnh" khỏi "size"

| biến thể | khớp / chỉ-nền / chỉ-x | lệnh khớp đổi profit | **Δ size-neutral** (chọn lệnh) CI95 block-72h | ΔPnL thực | size trên lệnh khớp | leg BD: Δ thực / size | không-BD: Δ thực / size |
|---|---|---|---|---|---|---|---|
| DOWN50 | 1 081 / 8 / 10 | 2,5 % | **−1,24k [−3,72; +0,00]** | +0,04k | +0,81k | −2,15k / −2,39k | +2,20k / +3,20k |
| DOWN25 | 1 083 / 6 / 7 | 2,9 % | **−1,05k [−3,16; −0,03]** | −0,17k | +0,69k | −1,19k / −1,06k | +1,02k / +1,75k |
| UP50 | 1 084 / 5 / 4 | 3,0 % | **+0,63k [−0,00; +1,90]** | +0,10k | −0,04k | +1,98k / +2,52k | −1,88k / −2,55k |

- Δ size-neutral theo năm: **toàn bộ ở 2025** (DOWN50 −1 239, DOWN25 −1 052, UP50 +632; các năm khác |Δ| < 1 USD). CI block "chạm 0" vì chỉ vài khối 72h khác 0 ⇒ bootstrap gần suy biến; DOWN25 inflate k=3 → ≈ [−3,9k; +0,8k] chứa 0.
- **Size** (notional leg BD khớp ×0,81 / ×0,91 / ×1,17) dịch PnL leg BD đúng tỉ lệ, rồi **bị bù gần đủ** bởi leg không-BD (notional ×1,006 / ×1,005 / ×0,997 nhưng rơi đúng các lệnh lãi lớn) ⇒ tổng thực ≈ 0.
- ⇒ "chọn lệnh" ≈ 0 ngoài một nhánh đường đi 2025; "size" là tái phân bổ zero-sum. **Không có alpha, không có giảm rủi ro.**

**Verdict L3a: NULL ĐỨNG** (cả 3 biến thể, mọi thước: Calmar_MTM ghép cặp, cùng exposure, theo năm, ghép cặp lệnh). Luật PRIMARY cũ sai về thiết kế (rate bất biến với size) nhưng kết luận không đổi. **Không đề xuất vòng mới trên B0** (B0 có 248 leg BD +11,7k = 12 % ΣPnL, cùng BudgetManager ⇒ cùng cơ chế tái phân bổ; prior ≈ 0). Nếu sau này vẫn muốn thử lever size trên B0, thước PRIMARY phải là ΔCalmar_MTM ghép cặp ở cùng exposure + Δ size-neutral theo lệnh — không dùng rate.

## 2. L3b — Giải phẫu PnL B0 (de-p1) theo thời gian & vị trí trong episode

**Định nghĩa (chốt trước khi đọc số):** giờ UTC = `start` − 7h (đã xác minh §2.0). Episode = chuỗi entry liên tiếp cách nhau **< 72h** (B0: **99 episode**). Thứ tự trong episode = rank min theo giờ vào (lệnh cùng phút cùng hạng). `n_open` = số lệnh có `ts_j ≤ ts_i < te_j` (gồm chính nó + lệnh cùng phút). BTC ret 1h/4h = close nến 1h **đã đóng** gần nhất (close ts ≤ giờ vào) so với 1h/4h trước (v2, 0 NaN). Tier quoteVol = qv **ngày UTC trước** ngày vào (causal); NA = 148 lệnh trước 2021-09-02 (cache bắt đầu 2021-09-01). Tuổi listing = giờ vào − `first_real_ts` (lineage v2); 78 mã left-censored (≤ 2021-01-01) ⇒ `>180d` (mọi lệnh ≥ 2021-07-01 ⇒ ≥ 181 ngày). Vào lại = có lệnh trước cùng coin đóng **trong 72h** trước giờ vào (hoặc còn mở). win = pnl > 0; SL-rate = `STOP_LOSS_DONE`. CI = bootstrap block-72h trên **lưới khối toàn mẫu** (535 khối, NREP 2000, seed 20260905): CI mean ROI (ratio Σprofit/n), CI Δ(mean lát − mean phần còn lại), CI ΣPnL. **Chỉ báo cáo lát n ≥ 100.** k = 58 ô ⇒ inflate √(2 ln 58) = 2,850. Toàn mẫu: n 2 517, ΣPnL 96 909, mean ROI 4,48 %, win 85,7 %, SL-rate 14,3 %.

### 2.0 Xác minh múi giờ printDone (CLOSES_1H_v2, 20 lệnh phút ≥ :57, seed 20260905)

| giả thuyết UTC = local − h | h=−9 | −3 | 0 | +3 | +5 | +6 | **+7** | +8 | +9 |
|---|---|---|---|---|---|---|---|---|---|
| median \|entry/close − 1\| (20 lệnh) | 5,24 % | 5,55 % | 6,78 % | 5,04 % | 4,49 % | 2,97 % | **0,142 %** | 6,67 % | 8,36 % |
| số lệnh < 0,5 % | 0 | 0 | 2 | 1 | 1 | 4 | **13/20** | 0 | 0 |

7/20 lệch 0,8–1,3 % đều là phút sập 2024-08-05 07:57 (7 mã) cách close nến 3 phút ⇒ đúng kỳ vọng. Trên toàn bộ 66 lệnh phút ≥ :57: median 0,142 % ở h=7 (tốt nhì 3,85 %). **UTC+7 xác nhận.**

### 2.1 Giờ vào (UTC; VN = UTC+7)

| UTC | VN | n | ΣPnL | % ΣPnL | mean ROI % [CI95] | win % | SL % | Δ vs còn lại [CI95] |
|---|---|---|---|---|---|---|---|---|
| 0 | 7 | 148 | 7 768 | 8,0 | 5,21 [2,64; 7,59] | 93,2 | 8,1 | +0,78 [−1,98; +3,46] |
| 1 | 8 | 140 | 3 274 | 3,4 | 2,93 [−0,30; 5,40] | 81,4 | 17,9 | −1,64 [−5,12; +1,19] |
| 4 | 11 | 101 | 1 029 | 1,1 | 1,08 [−3,99; 7,19] | 76,2 | 26,7 | −3,53 [−8,48; +2,58] |
| 8 | 15 | 107 | 1 442 | 1,5 | 2,18 [−0,93; 5,51] | 77,6 | 24,3 | −2,40 [−5,78; +1,21] |
| 12 | 19 | 153 | 3 046 | 3,1 | 2,95 [0,74; 5,30] | 85,0 | 16,3 | −1,63 [−4,20; +1,07] |
| 13 | 20 | 104 | 3 695 | 3,8 | 4,15 [0,45; 7,46] | 85,6 | 14,4 | −0,34 [−3,96; +3,04] |
| 14 | 21 | 105 | 4 260 | 4,4 | 3,70 [0,45; 5,98] | 86,7 | 13,3 | −0,81 [−4,11; +1,67] |
| 15 | 22 | 117 | **−3 076** | −3,2 | **−1,51 [−13,13; 7,18]** | 78,6 | 17,9 | −6,28 [−18,07; +2,66] |
| 16 | 23 | 137 | 4 726 | 4,9 | 3,74 [0,42; 6,37] | 87,6 | 12,4 | −0,78 [−4,15; +1,83] |
| 17 | 0 | 136 | 8 165 | 8,4 | 4,57 [1,37; 6,41] | 89,0 | 11,8 | +0,10 [−3,27; +2,64] |
| 18 | 1 | 137 | 3 657 | 3,8 | 3,43 [−0,23; 6,86] | 82,5 | 16,8 | −1,11 [−4,97; +2,54] |
| 19 | 2 | 119 | 6 841 | 7,1 | 6,69 [4,14; 9,37] | 89,9 | 12,6 | +2,32 [−0,61; +5,56] |
| 21 | 4 | 163 | 13 549 | 14,0 | 11,41 [3,43; 15,59] | 84,7 | 7,4 | +7,41 [−0,77; +11,68] |
| 22 | 5 | 161 | 7 845 | 8,1 | 4,13 [2,67; 5,64] | 87,0 | 13,7 | −0,37 [−2,08; +1,63] |

n < 100 (không báo cáo CI): UTC 2 (87), 3 (65), 5 (31), 6 (91), 7 (83; +7,3k), 9 (87), 10 (37), 11 (56), 20 (84; −1,0k), 23 (68; +7,0k). Bảng giờ VN là cùng các ô dịch +7 (cột VN). **Không giờ nào khác phần còn lại** (kể cả raw). UTC 15 (22h VN) âm do đuôi (CI mean ROI rộng ±10 pp) — không ý nghĩa.

### 2.2 Thứ trong tuần (UTC, 0 = thứ Hai)

| thứ | n | ΣPnL | % | mean ROI % [CI95] | win % | SL % | Δ vs còn lại |
|---|---|---|---|---|---|---|---|
| T2 | 508 | 22 001 | 22,7 | 4,48 [2,78; 5,92] | 88,2 | 13,0 | +0,01 [−2,14; +2,11] |
| T3 | 442 | 24 053 | 24,8 | 5,69 [3,53; 8,63] | 87,1 | 12,7 | +1,47 [−1,17; +4,70] |
| T4 | 433 | 14 166 | 14,6 | 4,07 [2,52; 5,78] | 85,2 | 15,7 | −0,49 [−2,41; +1,60] |
| T5 | 354 | 12 630 | 13,0 | 3,82 [−0,66; 6,84] | 86,4 | 15,5 | −0,77 [−5,41; +2,51] |
| T6 | 509 | 13 827 | 14,3 | 4,50 [0,81; 7,32] | 80,7 | 16,1 | +0,03 [−3,83; +2,91] |
| T7 | 208 | 7 609 | 7,9 | 4,53 [0,52; 7,45] | 88,5 | 11,5 | +0,06 [−3,70; +3,36] |

CN: n 63 (+2,6k) — dưới ngưỡng. Không cấu trúc.

### 2.3 Vị trí trong episode, độ đông của sổ, độ sâu cú sập, thanh khoản, tuổi coin, vào lại

| chiều | lát | n | ΣPnL | % | mean ROI % [CI95] | win % | SL % | Δ vs còn lại [CI95 raw] | sig raw / sau inflate |
|---|---|---|---|---|---|---|---|---|---|
| thứ tự trong episode | 1–5 | 1 043 | 41 294 | 42,6 | 3,71 [2,39; 5,16] | 84,5 | 16,4 | −1,32 [−3,23; +0,74] | 0 / 0 |
| | 6–20 | 600 | 14 782 | 15,3 | 2,46 [0,09; 4,45] | 82,8 | 17,2 | −2,65 [−5,48; +0,04] | 0 / 0 |
| | **>20** | 874 | **40 833** | **42,1** | **6,78 [4,67; 8,43]** | 89,2 | 9,8 | **+3,53 [+0,87; +5,80]** | TỐT / 0 |
| lệnh đang mở lúc vào | 1–5 | 175 | 10 178 | 10,5 | 3,62 [1,67; 5,26] | 87,4 | 14,3 | −0,92 [−2,89; +0,88] | 0 / 0 |
| | **6–15** | 334 | 5 889 | 6,1 | **1,39 [−1,79; 3,82]** | 82,3 | 16,8 | **−3,56 [−6,79; −0,82]** | KÉM / 0 |
| | 16–30 | 1 569 | 58 141 | 60,0 | 3,96 [2,82; 5,08] | 84,6 | 15,5 | −1,38 [−4,26; +1,79] | 0 / 0 |
| | **>30** | 439 | 22 701 | 23,4 | **9,03 [5,14; 11,16]** | 91,8 | 8,2 | **+5,51 [+1,29; +8,09]** | TỐT / 0 |
| BTC ret 1h (%) | ≤ −2 | 478 | 21 871 | 22,6 | 6,29 [2,74; 10,16] | 83,5 | 14,9 | +2,24 [−1,55; +6,15] | 0 / 0 |
| | (−2; −1] | 502 | 17 961 | 18,5 | 3,62 [0,47; 5,87] | 86,9 | 13,7 | −1,07 [−4,32; +1,50] | 0 / 0 |
| | (−1; −0,3] | 639 | 22 750 | 23,5 | 4,46 [3,14; 5,91] | 88,6 | 11,1 | −0,02 [−2,61; +2,48] | 0 / 0 |
| | (−0,3; 0,3] | 551 | 25 053 | 25,9 | 4,53 [2,53; 6,95] | 83,8 | 17,8 | +0,07 [−2,07; +2,70] | 0 / 0 |
| | > 0,3 | 347 | 9 274 | 9,6 | 3,16 [1,06; 5,32] | 85,0 | 14,7 | −1,52 [−3,83; +0,89] | 0 / 0 |
| BTC ret 4h (%) | **≤ −4** | 213 | 7 829 | 8,1 | **7,39 [5,01; 10,44]** | 90,1 | 13,1 | **+3,18 [+0,50; +6,37]** | TỐT / 0 |
| | (−4; −2] | 652 | 24 711 | 25,5 | 4,51 [0,29; 7,91] | 83,7 | 15,0 | +0,05 [−4,40; +3,68] | 0 / 0 |
| | (−2; −0,5] | 831 | 29 937 | 30,9 | 3,63 [2,20; 4,90] | 86,2 | 13,0 | −1,26 [−3,70; +1,18] | 0 / 0 |
| | (−0,5; 0,5] | 479 | 22 894 | 23,6 | 4,71 [2,58; 7,41] | 84,1 | 17,3 | +0,29 [−2,08; +3,35] | 0 / 0 |
| | > 0,5 | 342 | 11 539 | 11,9 | 4,31 [2,38; 6,34] | 88,0 | 12,6 | −0,19 [−2,15; +1,97] | 0 / 0 |
| tier quoteVol ngày trước | ≥ 100M | 1 409 | 55 406 | 57,2 | 4,36 [2,89; 5,80] | 85,2 | 14,3 | −0,27 [−1,24; +0,74] | 0 / 0 |
| | 20–100M | 744 | 25 466 | 26,3 | 4,16 [2,81; 5,47] | 84,0 | 16,8 | −0,45 [−1,39; +0,38] | 0 / 0 |
| | **5–20M** | 197 | 10 368 | 10,7 | **6,09 [4,48; 7,58]** | 92,4 | 8,6 | **+1,75 [+0,09; +3,71]** | TỐT / 0 |
| | < 5M | 19 | 636 | 0,7 | (n < 100) | | | | |
| | NA (trước 2021-09-02) | 148 | 5 033 | 5,2 | 5,23 [3,61; 7,05] | 90,5 | 10,1 | +0,80 [−1,24; +3,09] | 0 / 0 |
| tuổi listing | < 30 ngày | 474 | 23 876 | 24,6 | 4,88 [2,95; 6,70] | 86,9 | 11,6 | +0,49 [−1,34; +1,96] | 0 / 0 |
| | 30–180 ngày | 642 | 27 756 | 28,6 | 4,83 [3,22; 6,26] | 88,8 | 9,5 | +0,47 [−0,90; +1,54] | 0 / 0 |
| | > 180 ngày | 1 401 | 45 277 | 46,7 | 4,18 [2,92; 5,55] | 83,9 | 17,4 | −0,67 [−2,25; +1,15] | 0 / 0 |
| vào lại cùng coin | lần đầu | 1 842 | 67 307 | 69,5 | 3,82 [2,71; 4,95] | 85,4 | 15,0 | −2,43 [−5,03; +0,65] | 0 / 0 |
| | vào lại ≤ 72h | 675 | 29 602 | 30,5 | 6,26 [3,48; 8,61] | 86,7 | 12,4 | +2,43 [−0,65; +5,03] | 0 / 0 |

**Lát "ΣPnL lớn (≥ 10 %) VÀ CI mean ROI ngoài 0":** mọi lát ≥ 10 % ΣPnL đều có CI mean ROI **dương** (vì mean toàn mẫu +4,48 %), tức là "đóng góp lớn, lãi thật" — không có lát lớn nào âm. **Lát ÂM có ý nghĩa (CI mean ROI < 0): KHÔNG CÓ** (0/58).

### 2.4 Năm lát quan trọng nhất (xếp theo |ΣPnL − phần kỳ vọng theo n|, n ≥ 100)

| # | lát | n | ΣPnL | dư so với kỳ vọng | mean ROI | Δ vs còn lại raw | Δ sau inflate ×2,85 | đọc |
|---|---|---|---|---|---|---|---|---|
| 1 | thứ tự trong episode **>20** | 874 | +40,8k (42,1 %) | **+7,2k** | 6,78 % | +3,53 [+0,87; +5,80] | [−3,69; +10,36] | lệnh cuối cú sập kéo dài = tốt nhất; 5/5 năm dương |
| 2 | **> 30 lệnh mở** lúc vào | 439 | +22,7k (23,4 %) | **+5,8k** | 9,03 % | +5,51 [+1,29; +8,09] | [−5,00; +14,39] | sổ đầy = đáy capitulation; **75 % ΣPnL ở 2025** (17,1k) |
| 3 | **6–15 lệnh mở** | 334 | +5,9k (6,1 %) | **−7,0k** | 1,39 % | −3,56 [−6,79; −0,82] | [−12,30; +4,69] | "giữa chừng" — cú giảm chưa đủ sâu; ô KÉM duy nhất (raw) |
| 4 | thứ tự trong episode **6–20** | 600 | +14,8k (15,3 %) | **−8,3k** | 2,46 % | −2,65 [−5,48; +0,04] | [−10,59; +5,15] | cùng hình chữ U: giữa episode kém hơn đầu/cuối |
| 5 | BTC 4h **≤ −4 %** | 213 | +7,8k (8,1 %) | −0,4k | 7,39 % | +3,18 [+0,50; +6,37] | ≈ [−4,9; +11,8] | sập BTC càng sâu ROI càng cao (size nhỏ hơn ⇒ ΣPnL không vượt) |

Kèm: tuổi > 180 ngày dư −8,7k (Δ −0,67 [−2,25; +1,15], n.s.); UTC 21h (4h VN) dư +7,3k (Δ +7,41 [−0,77; +11,68], n.s.); UTC 15h (22h VN) dư −7,6k (n.s.). **Sau inflate k=58 không ô nào khác 0.**
Hình dạng chung (mô tả, không phải bằng chứng): B0 kiếm tiền nhất khi **cú sập sâu và đông** (cuối episode, sổ > 30, BTC −4 %/4h); "giữa chừng" (6–20 trong episode, 6–15 lệnh mở) là vùng ROI thấp. Đây là tín hiệu **gate/regime theo episode** ⇒ power wall (99 episode, 2025-10 chiếm phần lớn).

### 2.5 Ứng viên LOẠI BỎ ex-ante — ΔPnL nếu loại (size-neutral = bỏ đúng PnL B0 của lát, không tái phân bổ vốn)

4 ứng viên đặt tên TRƯỚC (từ đề bài) + mọi ô n ≥ 100 có CI mean ROI < 0 hoặc KÉM hơn phần còn lại (raw) — chỉ 1 ô.

| ứng viên | nguồn | n | ΔPnL nếu loại [CI95 block-72h] | % ΣPnL | Δ theo năm 2021H2 / 22 / 23 / 24 / 25 | Δ nếu notional đều 1k | phán |
|---|---|---|---|---|---|---|---|
| thứ tự trong episode > 20 | đặt trước | 874 | **−40,8k [−78,7; −17,0]** | −42,1 | −1,6 / −4,2 / −3,0 / −9,8 / −22,3k | −59,3k | **loại = mất tiền 5/5 năm** |
| > 30 lệnh mở | đặt trước | 439 | **−22,7k [−58,7; −3,4]** | −23,4 | −1,5 / −1,7 / −1,0 / −1,5 / −17,1k | −39,6k | **mất tiền 5/5** |
| coin < 30 ngày tuổi | đặt trước | 474 | **−23,9k [−38,0; −12,5]** | −24,6 | −0,8 / −0,7 / −2,2 / −6,3 / −13,9k | −23,1k | **mất tiền 5/5** |
| vào lại cùng coin ≤ 72h | đặt trước | 675 | **−29,6k [−60,2; −10,3]** | −30,5 | −1,5 / −2,6 / −2,8 / −5,5 / −17,1k | −42,2k | **mất tiền 5/5** |
| 6–15 lệnh mở | dữ liệu (KÉM raw) | 334 | −5,9k [−14,9; +3,6] | −6,1 | −0,9 / **+2,1** / −5,0 / −2,7 / **+0,7k** | −4,6k | CI chứa 0, 2/5 năm dương ⇒ **không** |

- **k = 58 ô đã nhìn** (+ 4 giả thuyết đặt trước) ⇒ mọi thứ ở đây là **post-hoc**; kể cả nếu có ô qua ngưỡng raw cũng chỉ đủ để pre-reg vòng sau, không phải bằng chứng. Ở đây **không ô nào** qua ngưỡng loại bỏ ⇒ **không có gì để pre-reg** từ hướng "lọc entry theo thời gian/vị trí".
- Ngược với kỳ vọng ban đầu (lệnh cuối episode / sổ đầy / coin mới / vào lại là lệnh "đuối"), dữ liệu cho thấy chúng **lãi hơn trung bình** (ROI 4,9–9,0 % vs 4,48 %). Lý do cơ học hợp lý: các lát này là cú sập sâu kéo dài nơi trailing FLAT3 ăn nhịp hồi lớn; coin < 30 ngày có SL-rate thấp (11,6 % vs 17,4 % ở > 180 ngày).

## 3. Giới hạn (khai rõ)
- L3a nền **T170**, không phải B0 (không có artifact BD_SIZE_ADAPT trên B0/Kaggle). Chuyển kết luận sang B0 dựa vào cơ chế (tái phân bổ ngân sách) — chưa đo trực tiếp.
- Equity MTM là **snapshot ngày** (b + unP lúc 00:00 UTC), không phải MTM phút ⇒ maxDD ngày nông hơn maxDD phút (T170 parity −11,84 % ngày). Thước Δ ghép cặp vẫn hợp lệ vì cùng lưới.
- Bootstrap Δ size-neutral L3a gần suy biến (khác 0 chỉ ở vài khối 2025) ⇒ CI không tin được ở cận; dùng kết hợp với phân rã theo năm.
- L3b: lệnh cùng phút được tính vào `n_open` và cùng hạng episode; định nghĩa episode (< 72h giữa entry) khác AUDIT_LONG_LEVERS (khoảng trống ngày đóng ≤ 2 ngày) ⇒ 99 vs 123 episode. ΔPnL loại bỏ bỏ qua tái phân bổ vốn/slot (B0 không binding vốn — CAPACITY_DIAG) và hiệu ứng lên lệnh khác.
- quoteVol tier không có cho 148 lệnh 2021-07/08 (NA, báo riêng). DEV đã bị nhìn 30+ lần; L3b thêm 58 ô.
