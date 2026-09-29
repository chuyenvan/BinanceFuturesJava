# RESULT — GD92 (gate rolling-percentile) trên nền R4

Pre-reg: `docs/prereg/PREREG_GD92_R4.md` (commit `2a759de`, chốt TRƯỚC khi chạy).
Nhánh `module` HEAD `0264816` + cherry-pick `-n` `1db0613` (branch `gd92-recheck`) → jar riêng.
Jar worktree sha256 `1433f3d7138bdb0f71586d87b6efbe0cc350c80d747a9abba36362da9e5a69f3`.
Sim **trên Kaggle** (bundle `sim-x1-2021-bundle`, dataset `sim-jar-gd92r4`, `sim_end_date=20251231`,
`code_sha=2a759de+cp1db0613`), 0 sim Oracle. DEV ≤ 2025-12-31 (2026 = HOLDOUT, không dùng).

Nền chung mọi arm: `profiles/r4_kg0_k16_f015_g155.properties` (KEEPLEG0, nhịp 1',
`CONC_CAP 15%`, `F_BASE 0.015`, `K=16`, gate scale `1.55`, phí base `0,1116 %/vòng`).

## 0. Kiểm hợp lệ (cổng DỪNG) — cả 3 điểm ĐẠT

| cổng | yêu cầu | đo được | kết |
|---|---|---|---|
| **Parity D0** | `md5(printDone)=06fd6e9aa9c916945b2cf12310b337ff`, n 2027, eq 104 489 | md5 **06fd6e9aa9c916945b2cf12310b337ff**, n **2027**, eq **104 489** | **PASS** |
| **`[GATE-ROLL]` bật thật** D1/D2 | `pct=0.92 window=90d …`, `nBeforeFirst=0` | D1: `08:44:53 WARN GateRollingThreshold: BAT pct=0.92 window=90d \| 39510 moc gio \| moc dau 1624989600000 \| nguong min=0.00456 max=0.01265` · D2 tương tự (`08:42:47`) | **PASS** |
| **`[CONC-PC]` trần 15%** | `blocked=` không chặn leg nào ngoài dự kiến | D0/D1/D2: `[CONC-PC] SUMMARY blocked=0 pct=0.15` | **PASS** |

⇒ 3 điểm nối GD92 **không dịch một bit nào** khi key `SIM_GATE_ROLLING_*` vắng (parity byte-identical);
gate rolling chạy thật trong dải nguỡng **0,456 % – 1,265 %** (dao quanh hằng số cũ 0,800 %).

## 1. Bảng chính — 3 arm @base (as-is, phí base trong artifact)

`k=2` ứng viên ⇒ `inflate = 1,1774`; self-check MTM D0≡R4: `dd_total=-16.42`, `UW=164.7` ngày — **khớp P2**.

| arm | n | equity | CAGR% | ddPhút | UW (ngày) | q*% | top-1% | conc% | Calmar_MTM | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **D0** (=R4) | 2 027 | 104 489 | 27,53 | −16,42 | 164,7 | 21,7 | 19,38 | 5,30 | 1,676 | PASS | PASS | ref | ref |
| **D1** (pct .92 W90, scale 1.55) | 2 141 | 112 373 | 29,60 | −16,84 | 128,9 | 24,9 | 17,22 | 3,68 | 1,758 | PASS | PASS | PASS | PASS |
| **D2** (pct .92 W90, scale 1.00) | 4 287 | 131 010 | 34,10 | −24,36 | **278,0** | **10,2** | **26,03** | 4,62 | 1,400 | **FAIL** | **FAIL** | **FAIL** | **FAIL** |

**D1 — PASS cả 4 tầng @base:**
- T1: `maxDD phút` năm xấu nhất −16,84 % (≤40) · UW 128,9 ngày (≤250) · quý xấu nhất −2,03 % (≥−20) · 0 năm âm · conc 3,68 % (≤15).
- T2: `q* = 24,9 %` (≥15) · top-1 % = 17,22 % (≤25).
- T3 (vs D0): `win% −0,32 pp` (≥−2,0) · `TSloss% +0,78 pp` (≤+2,5) — trong trần.
- T4 (MỚI, ưu tiên số lệnh): `n 2 141 > 2 027` ✓ · `Calmar_MTM 1,758 ≥ 0,90×1,676 = 1,509` ✓ · `conc 3,68 ≤ 5,30` ✓.

**D2 — FAIL cả 4 tầng:** UW 278 > 250 (T1) · `q*` 10,2 < 15, top-1 % 26,03 > 25 (T2) · `win% −4,43 pp`, `TSloss% +6,18 pp` (T3) · Calmar_MTM 1,400 < 1,509 (T4, dù conc đạt).

## 2. CI tầng 3 — paired block-72h, NREP 2000, seed 20260905, inflate 1,1774

| chỉ tiêu | D1 − D0 (obs) | CI95 | kết |
|---|---|---|---|
| `win%` | −0,32 | [−1,66 ; +1,04] | không âm ngoài 0 |
| `TSloss%` | +0,78 | [−0,65 ; +2,21] | không âm ngoài 0 |
| `mP\|SM` | −0,15 | [−0,40 ; +0,12] | — |
| `mP\|SL` | +2,74 | [+0,74 ; +5,35] | D1 **tốt hơn** (SL lỗ nhẹ hơn) |

| chỉ tiêu | D2 − D0 (obs) | CI95 |
|---|---|---|
| `win%` | **−4,43** | [−7,28 ; −1,88] (âm có ý nghĩa) |
| `TSloss%` | +6,18 | [+3,48 ; +8,87] |

## 3. Bảng theo QUÝ (D1 vs D0) — chỗ GD92 đổi hành vi

| quý | n D0 | n D1 | Δn | win% D0→D1 | TSloss% D0→D1 |
|---|---|---|---|---|---|
| 2023Q1 | 6 | 52 | **+46** | 83,3→92,3 | 50,0→15,4 |
| 2023Q2 | 68 | 108 | +40 | 86,8→87,0 | 19,1→16,7 |
| 2023Q3 | 45 | 97 | **+52** | 88,9→87,6 | 15,6→18,6 |
| 2023Q4 | 104 | 186 | **+82** | 91,4→87,1 | 8,7→13,4 |
| 2024Q3 | 108 | 122 | +14 | 90,7→86,1 | 12,0→16,4 |
| 2024Q4 | 146 | 149 | +3 | 93,8→92,0 | 6,2→8,7 |
| 2025Q1 | 201 | 193 | −8 | 89,1→90,7 | 10,0→8,3 |
| 2025Q2 | 33 | 18 | −15 | 87,9→94,4 | 12,1→5,6 |
| 2025Q3 | 38 | 36 | −2 | 71,1→69,4 | 23,7→25,0 |

(Năm: 2023 n 223→443 (+220), 2021 247→258, 2022 357→317, 2024 581→597, 2025 619→526.)

## 4. Đối chiếu dự báo ghi trước (§4 prereg)

1. D0 = R4 qua T1–T2, Calmar_MTM ≈ 1,676, n 2027, conc 5,30 % — **ĐÚNG**.
2. `n(D1) > n(D0)`, lệnh tăng tập trung 2023Q1/2025Q2/2025Q3 — **ĐÚNG một phần & SAI chiều ở 2025**:
   tăng thật ở **2023Q1 (+46)** và cả cụm 2023 (+220), nhưng GD92 **CẮT** ở **2025Q2 (−15)** và **2025Q4 (−68)**.
   Lý do: GD92 thay hằng số 0,008 bằng **phân vị 92 % cuộn**; ở regime "yên" của 2025 nguỡng trượt
   **cao hơn** 0,008 ⇒ lọc bớt, chứ không phải mở gate như giả định (gate mở khi lịch sử biến động cao).
3. **Rủi ro (MASTER)** D1 tệ hơn D0 về `win%`/`TSloss%` và có thể vượt trần T3 — **KHÔNG xảy ra**:
   D1 trong trần (−0,32 / +0,78 pp), `mP|SL` còn **tốt hơn** (CI dương).
4. `n(D2) > n(D1)`, chất lượng loãng hơn — **ĐÚNG cả hai** (4 287 > 2 141; win 82,25 vs 86,36).

## 5. Kết luận & bước tiếp (theo LUẬT KẾT LUẬN §6 prereg)

- **D1 là ỨNG VIÊN duy nhất** qua 4 tầng @base. **D2 loại** (FAIL cả 4 tầng @base).
- **CHƯA kết luận thay R4.** §6 buộc: chỉ đề xuất thay nếu **PASS 4 tầng @base+@stress** VÀ **jackknife
  không tệ hơn D0** VÀ **CI chênh Calmar không âm ngoài 0**. Ba điều kiện @stress/P3 **chưa chạy**.
- **KHÔNG merge `gd92-recheck`** vào `module`; không port LIVE ở task này (D1 thắng chỉ ⇒ báo có đường
  LIVE cho `GateRollingThreshold` chưa + cần gì để port). Không chạm 242/holdout 2026.

**Bước kế (TASK D tiếp):** chạy D1 @stress (`SIM_SLIPPAGE_RATE=0.000259` ⇒ `0,150 %/vòng`) + D0 @stress làm
mốc, chấm lại 4 tầng; rồi P3 (episode jackknife bỏ top-1/3/5; bootstrap cụm episode 5000 rep seed `20260928`;
CI chênh Calmar vs D0).

Artifact: `docs/result/gd92_r4.json` · output Kaggle `~/kaggle_sim/out/gd92-r4-{d0,d1,d2}/`.
