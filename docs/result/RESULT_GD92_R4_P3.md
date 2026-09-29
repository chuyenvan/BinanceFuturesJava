# RESULT — GD92 D1: @stress + độ bền P3 (TASK D3, theo §6 PREREG_GD92_R4)

Pre-reg: `docs/prereg/PREREG_GD92_R4_P3.md` (commit `15e3d40`, chốt **TRƯỚC** khi chạy) + §6 `PREREG_GD92_R4`
(`2a759de`). Nhánh `module` HEAD `68a2836`. Jar **DÙNG LẠI** GD92 (sha256 `1433f3d7…`, dataset Kaggle
`sim-jar-gd92r4`) — **KHÔNG build lại, KHÔNG merge `gd92-recheck`**. Sim **trên Kaggle** (0 sim Oracle),
bundle `sim-x1-2021-bundle`, `sim_end_date=20251231`, `code_sha=2a759de+cp1db0613`. DEV ≤ 2025-12-31.

Nền chung mọi arm: `profiles/r4_kg0_k16_f015_g155.properties` (KEEPLEG0, nhịp 1', `CONC_CAP 15%`,
`F_BASE 0.015`, `K=16`, gate scale `1.55`). **Arm D1** = GD92 (`SIM_GATE_ROLLING_PCT=0.92`,
`SIM_GATE_ROLLING_DAYS=90`). `@stress` = `SIM_SLIPPAGE_RATE=0.000259` ⇒ `0,150 %/vòng`
(`SIM_RATE_FEE` giữ `0.000982`).

## 0. Kiểm hợp lệ (cổng DỪNG) — cả 3 điểm ĐẠT

| cổng | yêu cầu | đo được | kết |
|---|---|---|---|
| **Parity D0s** | `md5(printDone)=84402b57c2fa43b72f86a918e3e54e11` (= R4@stress `p2-r4-stress`) | **`84402b57c2fa43b72f86a918e3e54e11`** · n **2027** · eq **103 351** · `diff` 0 dòng | **PASS** (byte-identical) |
| **`[GATE-ROLL]` bật thật** D1s | `pct=0.92 window=90d …`, `nBeforeFirst=0` | D1s: `BAT pct=0.92 window=90d \| 39510 moc gio \| nguong min=0.00456 max=0.01265` · D0s **không** có dòng này | **PASS** |
| **`[CONC-PC]` trần 15%** | `blocked=0` | D0s/D1s: `[CONC-PC] SUMMARY blocked=0 pct=0.15` | **PASS** |

⇒ Jar GD92 + 3 điểm nối **byte-identical** với R4 khi key `SIM_GATE_ROLLING_*` vắng (D0s = R4@stress);
gate rolling chạy thật trong dải nguỡng **0,456 % – 1,265 %** (giống @base).

## 1. Bảng 4 tầng @stress (as-is, phí stress trong artifact)

`k=2` ⇒ `inflate = 1,1774`; self-check MTM D0s ≡ R4@stress: `dd_total=-16.44`, `UW=222.1` ngày — **khớp P2**.

| arm | n | equity | CAGR% | ddPhút% | UW (ngày) | q*% | top-1% | conc% | Calmar_MTM | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **D0s** (=R4@stress) | 2 027 | 103 351 | 27,22 | −16,44 | 222,1 | 21,4 | 19,54 | 5,30 | 1,655 | PASS | PASS | ref | ref |
| **D1s** (GD92 @stress) | 2 141 | 111 030 | 29,26 | −16,86 | 128,9 | 24,6 | 17,33 | 3,68 | 1,736 | PASS | PASS | PASS | PASS |

**D1s — PASS cả 4 tầng @stress:**
- T1: `maxDD phút` năm xấu nhất −16,86 % (≤40) · UW 128,9 ngày (≤250) · quý xấu nhất −2,06 % (≥−20) · 0 năm âm · conc 3,68 % (≤15).
- T2: `q* = 24,6 %` (≥15) · top-1 % = 17,33 % (≤25).
- T3 (vs D0s): `win% −0,32 pp` (≥−2,0) · `TSloss% +0,78 pp` (≤+2,5) — trong trần (giống hệt @base, bất biến phí).
- T4: `Calmar_MTM 1,736 ≥ 0,90×1,655 = 1,489` ✓ · `conc 3,68 ≤ 5,30` ✓.

**`@stress` ≠ `@base` ở đâu:** KHÔNG một trạng thái tầng nào đổi (D1 PASS 4 tầng ở cả hai mức phí). Chỉ độ lớn
đổi nhẹ: `equity` −1,2 % (112 373 → 111 030) · `CAGR` −0,34 pp (29,60 → 29,26) · `Calmar_MTM` 1,758 → 1,736
(D0s: 1,676 → 1,655) · `ddPhút` +0,02 pp. **Tầng 3 giống hệt byte** (`win%`/`TSloss%` trên `profit` % —
bất biến chi phí, đúng khai pre-reg §2).

## 2. P3 — độ bền cặp (D1 vs D0) ở CẢ @base và @stress

### 2.1 Episode jackknife bỏ top-1/3/5 — D1 KHÔNG tệ hơn D0 (mọi mức, cả 2 mức phí)

| cost | D1 n_ep | top-1% | top-3% | top-5% | ΣPnL_còn(1) | Calmar_còn(1) | ΣPnL_còn(3) | Calmar_còn(3) | ΣPnL_còn(5) | Calmar_còn(5) |
|---|---|---|---|---|---|---|---|---|---|---|
| base D1 | 90 | — | — | — | 66 453 | 5,02 | 55 789 | 4,17 | 49 878 | 3,85 |
| base D0 | 93 | — | — | — | 57 467 | 3,54 | 46 502 | 2,70 | 40 958 | 2,30 |
| stress D1 | 90 | — | — | — | 65 351 | 4,94 | 54 795 | 4,10 | 48 965 | 3,78 |
| stress D0 | 93 | — | — | — | 56 532 | 3,49 | 45 666 | 2,66 | 40 193 | 2,26 |

**Đọc:** D1 bền **hơn** D0 ở mọi mức bỏ (Calmar_còn cao hơn, ΣPnL_còn > 0) — vì D1 phân tán lệnh đều hơn
(top-1% 17,3 % < D0 19,5 %). `Calmar_còn(3)` D0 = 2,70/2,66 khớp `RESULT_RESET_RULE_P3` (R4 base 2,70) ⇒
harness tái lập. **Vế (ii) "jackknife D1 không tệ hơn D0" = PASS.**

### 2.2 Bootstrap cụm episode (5000 rep, seed `20260928`) — paired lưới khối chung (K=100)

| chỉ tiêu (D1 − D0) | base | stress |
|---|---|---|
| **ΔCalmar** (đường dựng lại theo ngày) | **+2,56** CI **[−3,72 ; +9,85]** — **chứa 0** | **+2,50** CI **[−3,64 ; +9,59]** — **chứa 0** |
| ΔCAGR (pp) | **+2,18** CI **[+0,26 ; +4,49]** — ngoài 0 (dương) | **+2,14** CI **[+0,22 ; +4,44]** — ngoài 0 |
| Δn | +115,7 CI [−52,0 ; +288,0] | +115,7 CI [−52,0 ; +288,0] |
| ΔΣPnL | **+7 885** CI **[+982 ; +15 133]** — ngoài 0 | **+7 681** CI **[+849 ; +14 779]** — ngoài 0 |

**Đọc:** ΔCAGR và ΔΣPnL của D1 **dương có ý nghĩa** (CI ngoài 0), Δn dương nhưng chứa 0; **NHƯNG**
**ΔCalmar chứa 0** (cận dưới −3,7 / −3,6 < 0) ⇒ cải thiện **risk-adjusted** (Calmar) của D1 **KHÔNG** sống
qua bootstrap. Đúng mẫu hình đã thấy ở `RESULT_RESET_RULE_P3` (Calmar-theo-bootstrap bất ổn, CI rộng).

## 3. Chẩn đoán MÔ TẢ (ghi trước, KHÔNG phải cổng — xem `gd92_gate_diag.json`)

### (a) Ngưỡng GD92 hiệu dụng theo QUÝ (median/p10/p90, so hằng 0.008)

| quý | p10 | **p50** | p90 | | quý | p10 | **p50** | p90 |
|---|---|---|---|---|---|---|---|---|
| 2021Q3 | 0,00787 | 0,01156 | 0,01262 | | 2023Q4 | 0,00466 | 0,00594 | 0,00648 |
| 2021Q4 | 0,00732 | 0,00740 | 0,00759 | | 2024Q1 | 0,00688 | 0,00704 | 0,00815 |
| 2022Q1 | 0,00750 | 0,00827 | 0,00840 | | 2024Q2 | 0,00727 | 0,00822 | 0,00833 |
| 2022Q2 | 0,00779 | 0,00838 | 0,00991 | | 2024Q3 | 0,00662 | 0,00690 | 0,00711 |
| 2022Q3 | 0,00693 | 0,00839 | 0,00994 | | 2024Q4 | 0,00660 | 0,00701 | 0,00817 |
| 2022Q4 | 0,00635 | 0,00676 | 0,00713 | | 2025Q1 | 0,00819 | 0,00871 | 0,00884 |
| 2023Q1 | 0,00598 | 0,00648 | 0,00693 | | 2025Q2 | 0,00871 | 0,00894 | 0,00905 |
| 2023Q2 | 0,00551 | 0,00638 | 0,00673 | | 2025Q3 | 0,00863 | 0,00870 | 0,00893 |
| 2023Q3 | 0,00499 | 0,00524 | 0,00547 | | 2025Q4 | 0,00940 | **0,01128** | 0,01159 |

Nguỡng cuộn dao động **0,0046 – 0,0116**: **thấp hơn** hằng 0,008 ở 2021Q4–2024Q4 (mở gate ở quý yên,
nhất là 2023Q3 0,0052) và **cao hơn** 0,008 ở 2025Q2–Q4 (siết gate ở quý nóng). ⇒ giải thích cơ học việc
D1 thêm lệnh ở 2023 và cắt lệnh ở 2025 (khớp `RESULT_GD92_R4` §3–§4).

**% giờ gate mở theo quý (D0 hằng 0.008 vs D1 nguỡng cuộn):** D1 mở **nhiều hơn** ở 2023 (vd 2023Q4
+18,6 pp, 2023Q1 +7,7 pp) và 2024 (2024Q4 +7,8 pp); mở **ít hơn** ở 2025 (2025Q4 **−59,6 pp**, 2025Q3
−12,5 pp, 2025Q2 −10,4 pp). Chi tiết trong `gd92_gate_diag.json`.

### (b) Bảng quý ĐẦY ĐỦ 2021Q3..2025Q4 (D0 vs D1, `qstat_r4.py`)

| quý | n D0→D1 | Δn | win% D0→D1 | TSloss% D0→D1 | meanP% D0→D1 | PnL D0→D1 | maxDD% D0→D1 |
|---|---|---|---|---|---|---|---|
| 2021Q3 | 123→122 | −1 | 89,4→91,0 | 10,6→9,0 | 3,98→4,10 | 2053→1952 | −2,71→−2,62 |
| 2021Q4 | 124→136 | +12 | 80,7→80,9 | 19,4→19,1 | 1,86→2,15 | 953→1244 | −3,16→−3,17 |
| 2022Q1 | 67→66 | −1 | 86,6→86,4 | 14,9→16,7 | 3,58→3,57 | 1526→1504 | −2,05→−2,01 |
| 2022Q2 | 164→155 | −9 | 86,6→85,2 | 10,4→11,0 | 4,01→3,60 | 3112→2559 | −2,84→−2,63 |
| 2022Q3 | 50→29 | −21 | 90,0→82,8 | 12,0→17,2 | 7,06→5,54 | 2571→1221 | −0,19→−0,11 |
| 2022Q4 | 76→67 | −9 | 69,7→67,2 | 27,6→32,8 | −1,41→−2,23 | −423→−884 | −9,99→−11,14 |
| 2023Q1 | 6→52 | **+46** | 83,3→92,3 | 50,0→15,4 | −0,18→4,60 | −33→1671 | −0,74→−1,30 |
| 2023Q2 | 68→108 | +40 | 86,8→87,0 | 19,1→16,7 | 11,01→8,66 | 6262→7492 | −1,78→−1,75 |
| 2023Q3 | 45→97 | **+52** | 88,9→87,6 | 15,6→18,6 | 7,81→5,83 | 2692→4831 | −0,84→−0,64 |
| 2023Q4 | 104→186 | **+82** | 91,4→87,1 | 8,7→13,4 | 4,48→4,48 | 4450→6998 | −1,87→−2,43 |
| 2024Q1 | 178→184 | +6 | 90,5→90,2 | 9,6→9,8 | 4,64→4,61 | 7307→8244 | −1,39→−1,54 |
| 2024Q2 | 149→142 | −7 | 81,9→81,0 | 18,8→19,7 | 2,31→1,60 | 1499→405 | −5,55→−5,51 |
| 2024Q3 | 108→122 | +14 | 90,7→86,1 | 12,0→16,4 | 6,60→5,81 | 5268→4927 | −1,32→−1,45 |
| 2024Q4 | 146→149 | +3 | 93,8→92,0 | 6,2→8,7 | 6,10→5,99 | 9362→9739 | −0,28→−0,57 |
| 2025Q1 | 201→193 | −8 | 89,1→90,7 | 10,0→8,3 | 4,18→4,49 | 10635→11743 | −3,92→−2,60 |
| 2025Q2 | 33→18 | −15 | 87,9→94,4 | 12,1→5,6 | 4,23→6,26 | 2203→1838 | −0,98→−0,66 |
| 2025Q3 | 38→36 | −2 | 71,1→69,4 | 23,7→25,0 | −0,61→−0,95 | −358→−569 | −1,55→−1,68 |
| 2025Q4 | 347→279 | −68 | 85,6→85,7 | 8,7→6,5 | 5,67→6,88 | 10414→12460 | −3,14→−1,54 |

(Năm: 2023 n 223→443 (**+220**); 2021 247→258; 2022 357→317; 2024 581→597; 2025 619→526.)

### (c) Ngưỡng GD92 tại mốc cuối DEV 2025-12-31

**`thr(2025-12-31) = 0,01159`** — cao hơn hằng `0,008` (tỷ lệ **1,449×**). Đọc từ `pred.bin` DEV
(`wfo_ds_x1_2021`, 166 684 mẫu 15'), **KHÔNG đụng dữ liệu 2026**.

## 4. VERDICT theo §6 (giữ nguyên luật, KHÔNG nới)

| điều kiện §6 | kết quả | PASS? |
|---|---|---|
| (i) PASS 4 tầng @base + @stress | D1 PASS 4 tầng @base (`RESULT_GD92_R4`) + D1s PASS 4 tầng @stress | **PASS** |
| (ii) jackknife D1 không tệ hơn D0 (mọi mức bỏ 1/3/5, cả 2 mức phí) | Calmar_còn(D1) ≥ Calmar_còn(D0) & ΣPnL_còn > 0 ở mọi k | **PASS** |
| (iii) CI chênh Calmar **không âm ngoài 0** | ΔCalmar CI **[−3,72 ; +9,85]** (base) / **[−3,64 ; +9,59]** (stress) — **chứa 0** | **FAIL** |

⇒ **`D1 ≈ R4`, KHÔNG thay.** Thiếu điều (iii) ⇒ theo §6 giữ R4.

**Đọc thêm (không đổi luật):** D1 **thắng có ý nghĩa** về **ΔCAGR** (CI [+0,26 ; +4,49] pp, ngoài 0) và
**ΔΣPnL** (CI [+982 ; +15 133]), và bền hơn D0 trong jackknife (phân tán lệnh đều hơn). Nhưng cải thiện
**risk-adjusted** (Calmar) **không đạt ý nghĩa** (CI chứa 0) — đúng mẫu hình lịch sử GD92
(`AUDIT_GATEDYN_GD92`: rolling gate không tạo khác biệt hiệu quả đo được). §6 chốt Calmar là cổng ⇒ **giữ R4**.

## 5. RỦI RO & HẠN CHẾ

1. **Lần test THỨ 3 cùng cấu hình GD92** (pct `.92`/W90 chọn từ vòng DEV cũ) ⇒ `inflate(k=2)` **chưa tính
   lịch sử chọn** (L2 leak). Kết luận "D1 thay R4" (nếu có) vẫn là một quan sát duy nhất.
2. Bootstrap `ΔCalmar` dùng đường dựng lại **theo ngày** (không MTM phút) — đúng hạn chế `RESULT_RESET_RULE_P3`
   §7.1; điểm `ΔCalmar_MTM` (tầng 4: 1,736 vs 1,655 @stress) báo riêng, không trộn hai định nghĩa.
3. `maxDD`/`UW`/`qmin` là **số quan sát một lần** (không CI); T3 chỉ `win%`/`TSloss%` điểm ước lượng.
4. Mọi số là **mô tả quá khứ DEV (≤ 2025-12-30)**, không phải cam kết forward; **chưa chạm HOLDOUT 2026**.

## 6. TÁI LẬP

```bash
cd /home/ubuntu/src/BinanceFuturesJava
# (a)/(c) nguong cuon: python3 research/analysis/gd92_gate_diag.py
# (b) bang quy: python3 ~/claude_master/0929/qstat_r4.py gd92-r4-d0   (va gd92-r4-d1)
# 4 tang @stress + P3: python3 research/analysis/reset_rule_gd92r4_p3.py --workers 4
# Kaggle: 2 kernel sim-gd92-r4-{d0,d1}-stress (profile r4_kg0_k16_f015_g155,
#   overrides D0s={SIM_SLIPPAGE_RATE:0.000259}, D1s=+{SIM_GATE_ROLLING_PCT:0.92, SIM_GATE_ROLLING_DAYS:90})
```

## 7. COMMIT

- Pre-reg: **`15e3d40`** (`docs/prereg/PREREG_GD92_R4_P3.md`).
- Kết quả: commit này (`RESULT_GD92_R4_P3.md` + `gd92_r4_p3.json` + `gd92_gate_diag.json` +
  `research/analysis/reset_rule_gd92r4_p3.py` + `research/analysis/gd92_gate_diag.py`).
- Kaggle: 2 kernel `chuyendinh/sim-gd92-r4-{d0,d1}-stress`.
- Không port LIVE · không chạm shadow-c3/242/holdout 2026 · không merge `gd92-recheck`.
