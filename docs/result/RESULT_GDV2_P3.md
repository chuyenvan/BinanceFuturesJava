# RESULT — GDV2 G2: @stress + độ bền P3 + phân rã quý chết 2025 (TASK GDV2_P3, theo §6 PREREG_GDV2_EVEN)

Pre-reg: `docs/prereg/PREREG_GDV2_P3.md` (commit `100c907`, chốt **TRƯỚC** khi chạy) + §6 `PREREG_GDV2_EVEN`
(`2b4dcbd`). Nhánh `module` HEAD `39944db`. Jar **DÙNG LẠI** GDV2 (sha256
`7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a`, dataset Kaggle `sim-jar-gdv2`) — **KHÔNG
build lại, KHÔNG merge**. Sim **trên Kaggle** (0 sim Oracle), bundle `sim-x1-2021-bundle`, `sim_end_date=20251231`,
`code_sha=2b4dcbd+cp1db0613`. DEV ≤ 2025-12-31.

Nền chung mọi arm: `profiles/r4_kg0_k16_f015_g155.properties` (KEEPLEG0, nhịp 1', `CONC_CAP 15%`,
`F_BASE 0.015`, `K=16`, gate scale `1.55`). **Arm G2** = GDV2 W90 (`SIM_GATE_ROLLING_MODE=ratio`,
`SIM_GATE_ROLLING_PCT=0.99995083`, `SIM_GATE_ROLLING_DAYS=90`). `@stress` = `SIM_SLIPPAGE_RATE=0.000259`
⇒ `0,150 %/vòng` (`SIM_RATE_FEE` giữ `0.000982`).

## 0. Kiểm hợp lệ (cổng DỪNG) — ĐẠT hết

| cổng | yêu cầu | đo được | kết |
|---|---|---|---|
| **Parity G0s** | `md5(printDone)=84402b57c2fa43b72f86a918e3e54e11` (= R4@stress `p2-r4-stress`) | **`84402b57c2fa43b72f86a918e3e54e11`** · n **2027** · eq **103 351** | **PASS** (byte-identical) |
| **jar DÙNG LẠI** | `sim-jar-gdv2` sha256 `7368be46…`, KHÔNG build lại | `jar_sha256=7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a` | **PASS** |
| **`[GATE-RATIO]` bật thật** G2s | `mode=ratio pct=0.99995083 window=90d` | G2s: `GATE-RATIO on pct=0.99995083 days=90 … beforeFirst=168` · G0s **không** có (mode off) | **PASS** |
| **`[CONC-PC]` trần 15%** | `blocked=0` | G0s/G2s `[CONC-PC] SUMMARY blocked=0 pct=0.15` | **PASS** |

⇒ Jar GDV2 + 3 điểm nối **byte-identical** với R4 khi key `SIM_GATE_ROLLING_*` vắng (G0s = R4@stress);
gate rolling chạy thật với `pct = 0,99995083` (đúng = 1 − ρ).

## 1. Bảng 4 tầng @stress (as-is, phí stress trong artifact)

`k=2` ⇒ `inflate = 1,1774`; self-check MTM G0s ≡ R4@stress: `dd_total=-16,44`, `UW=222,1` ngày — **khớp P2**.

| arm | n | equity | CAGR% | ddPhút% | UW (ngày) | q*% | top-1% | conc% | Calmar_MTM | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **G0s** (=R4@stress) | 2 027 | 103 351 | 27,22 | −16,44 | 222,1 | 21,4 | 19,54 | 5,30 | 1,655 | PASS | PASS | ref | ref |
| **G2s** (GDV2 @stress) | 2 509 | 129 642 | 33,79 | −18,00 | 128,9 | 23,7 | 17,59 | 4,09 | 1,877 | PASS | PASS | PASS | PASS |

**G2s — PASS cả 4 tầng @stress:**
- T1: maxDD phút năm xấu nhất −18,00 % (≤40) · UW 128,9 (≤250) · quý xấu nhất −0,55 % (≥−20) · 0 năm âm · conc 4,09 % (≤15).
- T2: `q* = 23,7 %` (≥15) · top-1 % = 17,59 % (≤25).
- T3 (vs G0s): `win% −0,67 pp` (≥−2,0) · `TSloss% +1,67 pp` (≤+2,5) — trong trần (giống hệt @base, bất biến phí).
- T4: `Calmar_MTM 1,877 ≥ 0,90×1,655 = 1,489` ✓ · `conc 4,09 ≤ 5,30` ✓ · `n 2 509 > 2 027` (mục tiêu chính) ✓.

**`@stress` ≠ `@base` ở đâu:** KHÔNG một trạng thái tầng nào đổi (G2 PASS 4 tầng ở cả hai mức phí). Chỉ độ lớn
đổi nhẹ: `equity` −1,3 % (131 374 → 129 642) · `CAGR` −0,39 pp (34,18 → 33,79) · `Calmar_MTM` 1,900 → 1,877
(G0s: 1,676 → 1,655). **Tầng 3 giống hệt byte** (`win%`/`TSloss%` trên `profit` % — bất biến chi phí, đúng khai pre-reg §2).

## 2. P3 — độ bền cặp (G2 vs G0) ở CẢ @base và @stress

### 2.1 Episode jackknife bỏ top-1/3/5 — G2 KHÔNG đạt "không tệ hơn G0" ở mức top-1

| cost | G2 n_ep | G0 n_ep | ΣPnL(G2) | ΣPnL(G0) | Calmar_còn(1) G2/G0 | Calmar_còn(3) G2/G0 | Calmar_còn(5) G2/G0 |
|---|---|---|---|---|---|---|---|
| base | 104 | 93 | 96 375 | 69 490 | **3,42 / 3,54** ✗ | 3,06 / 2,70 ✓ | 2,83 / 2,30 ✓ |
| stress | 104 | 93 | 94 643 | 68 351 | **3,38 / 3,49** ✗ | 3,02 / 2,66 ✓ | 2,79 / 2,26 ✓ |

**Đọc:** G2 bền **hơn** G0 ở mức bỏ top-3/top-5 (Calmar_còn cao hơn, ΣPnL_còn > 0) — vì G2 phân tán lệnh đều
hơn (top-1% **lệnh** — chỉ số T2 — 17,6 % < G0 19,5 %). **NHƯNG** ở mức **top-1 episode** (bỏ 1 episode PnL lớn
nhất), `Calmar_còn(G2) 3,42 < G0 3,54` (base) và 3,38 < 3,49 (stress) ⇒ **vế (ii) "jackknife G2 không tệ hơn G0
mọi mức" = FAIL**. Lý do: episode top-1 của G2 nhỏ hơn G0 về tỉ trọng (12,5 % vs 17,3 %) nhưng G2 có nhiều
episode hơn (104 vs 93) và đường equity sau khi bỏ top-1 vẫn còn maxDD sâu hơn tương đối.

### 2.2 Bootstrap cụm episode (5000 rep, seed `20260928`) — paired lưới khối chung (K=109)

| chỉ tiêu (G2 − G0) | base | stress |
|---|---|---|
| **ΔCalmar** (đường dựng lại theo ngày) | **+0,97** CI **[−11,03 ; +14,28]** — **chứa 0** | **+0,98** CI **[−10,80 ; +13,98]** — **chứa 0** |
| ΔCAGR (pp) | **+6,73** CI **[+3,43 ; +10,18]** — ngoài 0 (dương) | **+6,65** CI **[+3,33 ; +10,11]** — ngoài 0 |
| Δn | +482,2 CI [+259,0 ; +722,0] | +482,2 CI [+259,0 ; +722,0] |
| ΔΣPnL | **+26 774** CI **[+12 537 ; +39 971]** — ngoài 0 | **+26 181** CI **[+12 068 ; +39 177]** — ngoài 0 |

**Đọc:** ΔCAGR, Δn và ΔΣPnL của G2 **dương có ý nghĩa** (CI ngoài 0); **NHƯNG** **ΔCalmar chứa 0** (cận dưới
−11,0 / −10,8 < 0) ⇒ cải thiện **risk-adjusted** (Calmar) của G2 **KHÔNG** sống qua bootstrap. Đúng mẫu hình đã
thấy ở `RESULT_RESET_RULE_P3` (R4 vs B*) và `RESULT_GD92_R4_P3` (D1 vs D0): **nhiều lệnh hơn + CAGR/PnL cao hơn
nhưng đi kèm drawdown lớn hơn ⇒ Calmar bất ổn, CI rộng**.

## 3. Chẩn đoán MÔ TẢ (ghi trước, KHÔNG phải cổng — xem `gdv2_p3_diag.json`)

### (a) Bảng quý ĐẦY ĐỦ 2021Q3..2025Q4 — G0 vs G2 (n sel/BD/DCA · seen · pass · pass-rate · win% · TSloss% · PnL · maxDD)

| quý | n G0→G2 | sel G0→G2 | BD/DCA G0→G2 | pass G0→G2 | pass-rate G0→G2 | win% G0→G2 | TSloss% G0→G2 | PnL G0→G2 | maxDD% G0→G2 |
|---|---|---|---|---|---|---|---|---|---|
| 2021Q3 | 123→285 | 109→271 | 14/0→14/0 | 110→274 | 5,56e-5→1,45e-4 | 89,4→86,3 | 10,6→14,0 | 2053→5213 | −2,71→−5,34 |
| 2021Q4 | 124→150 | 106→132 | 18/0→18/0 | 105→129 | 5,32e-5→6,56e-5 | 80,7→80,0 | 19,4→20,7 | 953→1213 | −3,16→−3,17 |
| 2022Q1 | 67→64 | 67→64 | 0→0 | 67→64 | 3,45e-5→3,28e-5 | 86,6→87,5 | 14,9→14,1 | 1526→1606 | −2,05→−2,05 |
| 2022Q2 | 164→200 | 150→173 | 8/6→8/19 | 150→173 | 7,81e-5→9,19e-5 | 86,6→81,0 | 10,4→22,0 | 3112→−203 | −2,84→−10,41 |
| 2022Q3 | 50→56 | 42→48 | 8/0→8/0 | 42→48 | 2,07e-5→2,37e-5 | 90,0→91,1 | 12,0→10,7 | 2571→2807 | −0,19→−0,21 |
| 2022Q4 | 76→103 | 67→92 | 4/5→4/7 | 67→92 | 3,44e-5→4,75e-5 | 69,7→72,8 | 27,6→25,2 | −423→40 | −9,99→−9,39 |
| 2023Q1 | **6→109** | 0→103 | 6/0→6/0 | 0→103 | 0→5,39e-5 | 83,3→89,9 | 50,0→13,8 | −33→3586 | −0,74→−2,08 |
| 2023Q2 | 68→122 | 51→106 | 17/0→16/0 | 51→116 | 2,57e-5→6,04e-5 | 86,8→77,9 | 19,1→24,6 | 6262→6741 | −1,78→−2,03 |
| 2023Q3 | 45→103 | 28→85 | 17/0→18/0 | 28→75 | 1,39e-5→3,81e-5 | 88,9→87,4 | 15,6→18,5 | 2692→5509 | −0,84→−0,70 |
| 2023Q4 | 104→194 | 95→185 | 9/0→9/0 | 95→185 | 4,77e-5→9,50e-5 | 91,4→87,1 | 8,7→13,4 | 4450→7907 | −1,87→−2,42 |
| 2024Q1 | 178→183 | 153→158 | 25/0→25/0 | 153→158 | 7,76e-5→8,04e-5 | 90,5→90,2 | 9,6→9,8 | 7307→8890 | −1,39→−1,54 |
| 2024Q2 | 149→143 | 122→116 | 26/1→26/1 | 122→116 | 6,40e-5→6,08e-5 | 81,9→81,1 | 18,8→19,6 | 1499→1179 | −5,55→−5,51 |
| 2024Q3 | 108→102 | 102→96 | 6/0→6/0 | 102→96 | 5,14e-5→4,84e-5 | 90,7→90,2 | 12,0→12,8 | 5268→5994 | −1,32→−1,26 |
| 2024Q4 | 146→164 | 132→150 | 14/0→14/0 | 132→150 | 6,56e-5→7,50e-5 | 93,8→94,5 | 6,2→5,5 | 9362→13975 | −0,28→−0,45 |
| 2025Q1 | 201→173 | 192→165 | 8/1→8/0 | 192→165 | 1,01e-4→8,55e-5 | 89,1→93,1 | 10,0→6,4 | 10635→14826 | −3,92→−1,88 |
| 2025Q2 | **33→26** | 33→26 | 0→0 | 33→26 | 1,64e-5→1,29e-5 | 87,9→88,5 | 12,1→11,5 | 2203→2544 | −0,98→−0,72 |
| 2025Q3 | **38→53** | 34→49 | 4/0→4/0 | 34→49 | 1,67e-5→2,43e-5 | 71,1→75,5 | 23,7→22,6 | −358→−307 | −1,55→−1,59 |
| 2025Q4 | 347→279 | 262→197 | 64/21→64/18 | 262→197 | 1,39e-4→1,01e-4 | 85,6→86,4 | 8,7→5,4 | 10414→14855 | −3,14→−1,31 |

(Năm: 2021 n 247→435 · 2022 357→423 · 2023 223→528 (**+305**) · 2024 581→592 · 2025 619→531. G1 W30: n 3199;
D1 (GD92 W90): n 2141 — `[GATE-ROLL]` **KHÔNG log per-quarter** nên cột seen/pass của D1 chỉ có tổng
`n_cand=35 350 708 / n_pass=1895`, đánh dấu "n/a theo quý".)

### (b) PHÂN RÃ 2025Q2 (G0 33 → G2 26) và 2025Q3 — **100% do GATE, KHÔNG phải chỗ trống/CONC/top-K**

| quý | arm | candidate seen | gate pass | pass-rate | actual sel (printDone) | vacancy (=pass−sel) |
|---|---|---|---|---|---|---|
| 2025Q2 | G0 (base 0.008) | 2 013 928 | 33 | 1,639e-5 | 33 | **0** |
| 2025Q2 | G2 (rolling) | 2 017 510 | 26 | 1,289e-5 | 26 | **0** |
| 2025Q3 | G0 (base 0.008) | 2 033 007 | 34 | 1,672e-5 | 34 | **0** |
| 2025Q3 | G2 (rolling) | 2 014 611 | 49 | 2,432e-5 | 49 | **0** |

**Đọc:** candidate seen hai arm gần bằng nhau (≈2,0M/quý); **vacancy = 0 ở cả hai quý** (gate pass = actual
PREDICT trade) ⇒ chỗ trống/CONC/top-K **KHÔNG** gây ra 33→26. Sự thay đổi **100% do pass-rate của gate**:
- **2025Q2**: G2 pass-rate **1,289e-5 < G0 1,639e-5** (tỉ lệ 0,79×) ⇒ rolling gate **CHẶT hơn** base 0.008 — đúng
  giả thuyết "cửa sổ 90d còn nhớ 2025Q1 sôi động" (q_t cao).
- **2025Q3**: G2 pass-rate **2,432e-5 > G0 1,672e-5** (1,45×) ⇒ window trượt qua 2025Q2 nguội ⇒ q_t tụt ⇒ gate
  **LỎNG hơn** base, mở thêm lệnh.

**[SUY LUẬN] ngưỡng q_t theo TUẦN 2025Q1–Q3** (proxy = phân vị cuộn p15 tại pct=0.99995083, W=90d, causal, từ
`pred.bin` DEV — jar GDV2 **CHỈ log per-quarter**, không log q_t per-tuần như GD92 `[GATE-ROLL]`):

| tuần | q_t_proxy | tuần | q_t_proxy | tuần | q_t_proxy |
|---|---|---|---|---|---|
| 2025-01-02 | 0,0247 | 2025-03-27 | 0,0326 | 2025-06-26 | 0,0216 |
| 2025-01-23 | 0,0309 | 2025-04-17 | 0,0326 | 2025-07-17 | 0,0181 |
| 2025-02-06 | 0,0326 | 2025-05-01 | 0,0216 | 2025-08-14 | 0,0166 |
| 2025-03-06 | 0,0326 | 2025-05-22 | 0,0239 | 2025-09-18 | 0,0156 |

⇒ q_t proxy **cao ~0,0326** suốt 2025Q1 (nhớ nóng cuối 2024/đầu 2025) → **tụt dần** 0,0326→0,0156 qua 2025Q2→Q3
khi cửa sổ 90d trượt qua vùng nguội. Khớp đúng hướng với pass-rate đo thật (Q2 chặt, Q3 lỏng).

### (c) q_t tại 2025-12-31 so median toàn kỳ

**[SUY LUẬN] proxy q_t(2025-12-31) = 0,06687 vs median toàn kỳ 0,03860 ⇒ tỉ lệ `1,732×`** — tức cửa sổ 90d
cuối DEV nhớ đợt **nóng 2025Q4** (nến 2025Q4 mạnh). Nhưng pass-rate **2025Q4 đo thật = 1,01e-4 = 1,6× ρ**
(197/1 948 434) — gate thực tế đang **mở RỘNG hơn thiết kế** (điều kiện hiện tại nóng hơn cửa sổ trượt). Dự báo
port live đầu 2026: gate khởi đầu ở ngưỡng **cao** (nhớ 2025Q4) nhưng tự hiệu chỉnh về ≈ρ (đặc tính tự chuẩn hoá
của quantile-trên-tỉ-số-r); **chỉ đọc log sim DEV + pred.bin DEV, KHÔNG dùng dữ liệu 2026**.

## 4. VERDICT theo §6 (giữ nguyên luật, KHÔNG nới)

| điều kiện §6 | kết quả | PASS? |
|---|---|---|
| (i) PASS 4 tầng @base + @stress | G2 PASS 4 tầng @base (`RESULT_GDV2_EVEN`) + G2s PASS 4 tầng @stress | **PASS** |
| (ii) jackknife G2 không tệ hơn G0 (mọi mức bỏ 1/3/5, cả 2 mức phí) | `Calmar_còn(1)` G2 3,42/3,38 < G0 3,54/3,49 | **FAIL** |
| (iii) CI chênh Calmar **không âm ngoài 0** | ΔCalmar CI **[−11,03 ; +14,28]** (base) / **[−10,80 ; +13,98]** (stress) — **chứa 0** | **FAIL** |

⇒ **`G2 ≈ R4` về rủi ro-lợi nhuận, KHÔNG thay.** Thiếu (ii) + (iii) ⇒ theo §6 giữ R4.

**Đọc thêm (không đổi luật):** G2 **thắng có ý nghĩa** về **ΔCAGR** (CI [+3,43 ; +10,18] pp, ngoài 0), **Δn**
(+482, CI [+259 ; +722]) và **ΔΣPnL** (CI [+12 537 ; +39 971]), và bền hơn G0 trong jackknife top-3/top-5 (phân
tán lệnh đều hơn). Nhưng cải thiện **risk-adjusted** (Calmar) **không đạt ý nghĩa** (CI chứa 0) — đúng mẫu hình
lịch sử (rolling gate không tạo khác biệt Calmar đo được). §6 chốt Calmar là cổng ⇒ **giữ R4**.

## 5. ĐỘ ĐỀU (ghi RIÊNG — mục tiêu owner, vì T4 đặt `n` là mục tiêu chính)

Dù verdict rủi ro-lợi nhuận = "G2 ≈ R4", **mục tiêu ĐỘ ĐỀU của owner ĐẠT** (đã chốt ở `RESULT_GDV2_EVEN` §2):

| arm | CV(n quý) | min n quý | số quý n<40 | quý "chết" |
|---|---|---|---|---|
| **G0** (=R4) | 0,693 | **6** (2023Q1) | 3 (2023Q1·2025Q2·2025Q3) | 2023Q1 (6 lệnh) |
| **G2** (W90) | **0,505** | **26** (2025Q2) | **1** (2025Q2) | — |
| G1 (W30) | 0,326 | 104 | 0 | — |
| D1 (GD92) | 0,56 | 18 | 3 | — |

G2 mở lại quý chết 2023Q1 (6→109 lệnh), min n quý 6→26, CV 0,693→0,505 — **đều hơn R4 thật**. **NHƯNG** cải
thiện này **lẫn với tăng số lệnh**: G2 n = 2 509 = **1,24× G0** (không đạt "cùng tổng lượng mở" — phân vị
99,995 % trên cửa sổ HỮU HẠN đánh giá thấp đuôi cực ⇒ q_t thấp hơn mức "cùng tổng"). Lợi ích độ đều **không tách
sạch** khỏi lợi ích "nhiều cược nhỏ cùng chất lượng" (đúng ý owner ưu tiên `n`).

## 6. RỦI RO & HẠN CHẾ

1. **Lần test ~27 trên cùng DEV** (GDV2_EVEN ghi "~26"; GD92 P3 = lần 3 cùng cấu hình GD92) ⇒ `inflate(k=2)`
   **chưa tính lịch sử chọn** (L2 leak). Kết luận "G2 thay R4" (nếu có) vẫn là một quan sát duy nhất.
2. **"Cùng tổng lượng mở" KHÔNG đạt** (G2 n = 1,24× G0) ⇒ độ đều lẫn với tăng số lệnh (đã nêu §5).
3. Bootstrap `ΔCalmar` dùng đường dựng lại **theo ngày** (không MTM phút) — đúng hạn chế `RESULT_RESET_RULE_P3`
   §7.1; điểm `ΔCalmar_MTM` (tầng 4: 1,877 vs 1,655 @stress) báo riêng, không trộn hai định nghĩa.
4. `maxDD`/`UW`/`qmin` là **số quan sát một lần** (không CI); T3 chỉ `win%`/`TSloss%` điểm ước lượng.
5. Chẩn đoán (b)/(c) "q_t theo tuần" và "q_t cuối DEV" là **[SUY LUẬN]** (jar GDV2 chỉ log per-quarter; proxy =
   phân vị cuộn p15 từ `pred.bin` 15' — lệch lưới so buffer 1' thật ⇒ chỉ đọc XU HƯỚNG, không đọc giá trị).
6. Mọi số là **mô tả quá khứ DEV (≤ 2025-12-30)**, không phải cam kết forward; **chưa chạm HOLDOUT 2026**.

## 7. TÁI LẬP

```bash
cd /home/ubuntu/src/BinanceFuturesJava
# G0s/G2s @stress (Kaggle, jar reuse sim-jar-gdv2):
python3 research/analysis/reset_rule_gdv2_p3_run.py g0s g2s
# 4 tang @stress + P3 (jackknife + bootstrap) + verdict:
python3 research/analysis/reset_rule_gdv2_p3.py --workers 4 --json docs/result/gdv2_p3.json
# chan doan (a/b/c):
python3 research/analysis/gdv2_p3_diag.py
python3 ~/claude_master/0929/qstat_r4.py gdv2-g0   # (va gdv2-g1, gdv2-g2, gd92-r4-d1)
# Kaggle: 2 kernel sim-gdv2-{g0,g2}-stress (profile r4_kg0_k16_f015_g155,
#   overrides G0s={SIM_SLIPPAGE_RATE:0.000259}, G2s=+{SIM_GATE_ROLLING_MODE:ratio,
#   SIM_GATE_ROLLING_PCT:0.99995083, SIM_GATE_ROLLING_DAYS:90})
```

## 8. COMMIT

- Pre-reg: **`100c907`** (`docs/prereg/PREREG_GDV2_P3.md`).
- Kết quả: commit này (`RESULT_GDV2_P3.md` + `gdv2_p3.json` + `gdv2_p3_diag.json` +
  `research/analysis/reset_rule_gdv2_p3.py` + `reset_rule_gdv2_p3_run.py` + `gdv2_p3_diag.py`).
- Kaggle: 2 kernel `chuyendinh/sim-gdv2-{g0,g2}-stress`.
- Không port LIVE · không chạm shadow-c3/242/holdout 2026 · không build lại jar · không merge.
