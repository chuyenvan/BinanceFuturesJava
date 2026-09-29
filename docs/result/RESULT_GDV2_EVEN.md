# RESULT — GDV2 (gate rolling "đều lệnh", quantile trên CHÍNH tỉ số cuối) trên nền R4

Pre-reg: `docs/prereg/PREREG_GDV2_EVEN.md` (commit `2b4dcbd`, chốt TRƯỚC khi chạy).
Nhánh `module` HEAD `4017d12` + cherry-pick `-n` `1db0613` (GD92) → worktree RIÊNG `/home/ubuntu/claude_master/wt_gdv2`.
Jar worktree sha256 `7368be46edb3fa387a41585bea18feb81ab812ebabdc9ff245f6d25947a82d6a`.
Sim **trên Kaggle** (bundle `sim-x1-2021-bundle`, dataset jar `sim-jar-gdv2`, `sim_end_date=20251231`,
`code_sha=2b4dcbd+cp1db0613`), 0 sim Oracle. DEV ≤ 2025-12-31 (2026 = HOLDOUT, không dùng).

Nền chung mọi arm: `profiles/r4_kg0_k16_f015_g155.properties` (KEEPLEG0, nhịp 1', CONC_CAP 15%,
F_BASE 0.015, K=16, gate scale 1.55, phí base 0,1116 %/vòng).

## 0. Kiểm hợp lệ (cổng DỪNG) — ĐẠT hết

| cổng | yêu cầu | đo được | kết |
|---|---|---|---|
| **Parity G0** | `md5(printDone)=06fd6e9aa9c916945b2cf12310b337ff`, n 2027, eq 104 489 | md5 **06fd6e9aa9c916945b2cf12310b337ff**, n **2027**, eq **104 489** | **PASS** |
| **`[GATE-RATIO]` bật thật** G1/G2 | `mode=ratio pct=… window=30/90d`, `beforeFirst=168` (7 ngày warm-up) | G1: `pct=0.99995083 window=30d | warm-up 7d`, `beforeFirst=168` · G2: `window=90d` | **PASS** |
| **ρ đo từ G0** (bộ đếm, không đổi hành vi) | `[GATE-RATIO] off … rho=…` | seen=35 488 397, pass=1745 ⇒ **ρ = 4,9171e-5** ⇒ `pct = 1−ρ = 0,99995083` | **PASS** |

⇒ 3 điểm nối GDV2 không dịch bit nào khi key `SIM_GATE_ROLLING_MODE` vắng (parity byte-identical);
gate rolling chạy thật với `pct = 0,99995083` (đúng = 1 − ρ).

## 1. Bảng chính — 3 arm @base (as-is, phí base trong artifact)

`k=2` ứng viên ⇒ `inflate = 1,1774`; self-check MTM G0≡R4: `dd_total=-16,42`, `UW=164,7` ngày — **khớp P2**.

| arm | n | equity | CAGR% | ddPhút | UW (ngày) | q*% | top-1% | conc% | Calmar_MTM | T1 | T2 | T3 | T4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **G0** (=R4) | 2 027 | 104 489 | 27,53 | −16,42 | 164,7 | 21,7 | 19,38 | 5,30 | 1,676 | PASS | PASS | ref | ref |
| **G1** (W30) | 3 199 | 104 903 | 27,64 | −24,90 | **472,6** | **12,5** | 22,40 | 6,46 | 1,110 | **FAIL** | **FAIL** | **FAIL** | **FAIL** |
| **G2** (W90) | 2 509 | 131 374 | 34,18 | −17,99 | 128,9 | 23,9 | 17,46 | 4,09 | 1,900 | PASS | PASS | PASS | PASS |

**G1 — FAIL cả 4 tầng:**
- T1: `UW 472,6 > 250` · **năm 2022 ÂM** (`neg_year=['2022']`) — gate giữ quota vào lệnh cả regime xấu 2022 (đúng rủi ro ghi trước).
- T2: `q* 12,5 < 15`.
- T3: `win% −5,34 pp` (< −2,0) · `TSloss% +6,93 pp` (> +2,5) — lệnh thêm loãng chất lượng.
- T4: `Calmar_MTM 1,110 < 0,90×1,676 = 1,509`.

**G2 — PASS cả 4 tầng @base:**
- T1: maxDD phút −17,99 % (≤40) · UW 128,9 (≤250) · qmin −0,47 (≥−20) · 0 năm âm · conc 4,09 % (≤15).
- T2: q* 23,9 (≥15) · top-1 % 17,46 (≤25).
- T3 (vs G0): `win% −0,67 pp` (≥−2,0) · `TSloss% +1,67 pp` (≤+2,5) — trong trần.
- T4: `Calmar_MTM 1,900 ≥ 1,509` ✓ · `conc 4,09 ≤ 5,30` ✓ · `n 2 509 > 2 027` (mục tiêu chính) ✓.

## 2. ĐỘ ĐỀU theo quý 2021Q3..2025Q4 (mới)

| arm | CV(n quý) | min n quý | số quý n<40 | RMS lệch tỉ lệ pass quý so ρ | n quý (min…max) |
|---|---|---|---|---|---|
| **G0** (=R4) | **0,693** | **6** (2023Q1) | **3** (2023Q1·2025Q2·2025Q3) | 3,4e-5 | 6 … 347 |
| **D1** (GD92, từ gd92-r4-d1) | 0,56 | 18 | 3 | — | 18 … 316 |
| **G1** (W30) | **0,326** | **104** | **0** | **2,9e-5** | 104 … 301 |
| **G2** (W90) | **0,505** | **26** (2025Q2) | **1** (2025Q2) | 3,2e-5 | 26 … 285 |

**Đọc:** cả G1 (W30) và G2 (W90) **đều hơn thật** so với G0 (R4) VÀ D1 (GD92): CV giảm 0,693→0,505/0,326,
min n tăng 6→26/104, quý "chết" 2023Q1 được mở (G0 6 → G2 109 → G1 171). GDV2 sửa đúng chỗ GD92 còn lệch
(quantile trên CHÍNH tỉ số r, không phải p15). G1 (W30) đều nhất nhưng **đắt**: vào lệnh regime xấu 2022.

## 3. Đối chiếu dự báo ghi trước (§4 prereg)

1. G0 = R4 qua T1–T2, Calmar ≈ 1,676, n 2027, conc 5,30 %; `ρ ≈ 5,1e-5` — **ĐÚNG** (ρ đo được 4,9171e-5).
2. GDV2 giữ quota đều ⇒ CV/min n tốt hơn G0, hết quý "chết" — **ĐÚNG** (CV 0,505/0,326 < 0,693; min 26/104 > 6).
3. **Rủi ro (MASTER):** gate giữ quota vào lệnh cả regime xấu (2022) — **XẢY RA với G1** (W30): năm 2022 ÂM,
   TSloss% 2022 29,63 %, UW 472,6. **G2 (W90) nhẹ hơn nhiều** (0 năm âm, TSloss% 2022 20,09 %, UW 128,9).
   ⇒ W ngắn (30d) thích ứng nhanh → đều nhất nhưng vào lệnh 2022 quá mạnh; W dài (90d) cân bằng.

## 4. CI tầng 3 — paired block-72h, NREP 2000, seed 20260905, inflate 1,1774

| chỉ tiêu | G2 − G0 (obs) | CI95 | kết |
|---|---|---|---|
| `win%` | −0,67 | [−2,67 ; +1,25] | không âm ngoài 0 (trong trần −2,0) |
| `TSloss%` | +1,67 | [−0,52 ; +3,78] | không âm ngoài 0 (trong trần +2,5) |

| chỉ tiêu | G1 − G0 (obs) | CI95 |
|---|---|---|
| `win%` | **−5,34** | [−8,38 ; −2,38] (âm có ý nghĩa) |
| `TSloss%` | **+6,93** | [+3,59 ; +10,14] (dương có ý nghĩa) |

## 5. ỨNG VIÊN (theo tiêu chí đã chốt)

**Ứng viên ⇔ PASS 4 tầng @base VÀ CV(n quý) < G0 VÀ min n quý > G0.**

| arm | PASS 4 tầng | CV < G0 (0,693) | min n > G0 (6) | kết |
|---|---|---|---|---|
| G1 (W30) | **FAIL** | ✓ (0,326) | ✓ (104) | **KHÔNG** (FAIL 4 tầng) |
| **G2 (W90)** | **PASS** | ✓ (0,505) | ✓ (26) | **ỨNG VIÊN** |

⇒ **G2 (GDV2 W90) là ỨNG VIÊN DUY NHẤT** — qua 4 tầng @base và đều hơn G0. Theo luật, **chỉ ứng viên mới
chạy @stress + P3 ở task sau** (chưa làm ở task này).

## 6. Kết luận & bước tiếp (theo LUẬT KẾT LUẬN)

- **G2 là ứng viên duy nhất** (PASS 4 tầng @base + đều hơn G0). **G1 (W30) loại** (FAIL cả 4 tầng: vào lệnh 2022).
- **CHƯA kết luận thay R4.** Chưa chạy @stress + P3 (episode jackknife / bootstrap / CI chênh Calmar vs G0) —
  theo pre-reg, chỉ ứng viên mới chạy, ở **task sau**.
- **KHÔNG merge** `wt_gdv2` vào `module`; không port LIVE ở task này; không chạm 242/holdout 2026.

**Ghi chú để PORT LIVE (không làm ở task này):** `GateRollingRatio` dùng buffer **ONLINE** (r cần `symbolPred`
chỉ có lúc chạy, khác GD92 precompute từ predictionMap). Để port: (1) duy trì buffer causal các `r` của
candidate PREDICT trong process live (cửa sổ W=30/90 ngày, thêm theo mỗi `entryGate`); (2) warm-up **7 ngày**
(fallback base 0.008) trước khi bật quantile; (3) **persist buffer qua restart** (hoặc chịu warm-up lại);
(4) `symbolPred` có sẵn qua `build_map` live. Cần thêm đường LIVE riêng trong
`DetectEntrySignal2TradeNormal` (hiện chỉ sim có `GateRollingRatio`).

## 7. HẠN CHẾ (khai rõ)

1. **"Cùng tổng lượng mở" CHỈ XẤP XỈ**: G2 n 2 509 = 1,24× G0 (2 027), G1 1,58× — vì phân vị 99,995 % trên
   cửa sổ HỮU HẠN (30/90d) **đánh giá thấp** đuôi cực (heavy-tailed, non-stationary) ⇒ q_t thấp hơn mức
   "cùng tổng" ⇒ mở nhiều hơn. Cửa sổ càng lớn càng sát ρ (W90 1,24× vs W30 1,58×). Đây là [SUY LUẬN].
2. T3 là **điểm ước lượng** (không phải CI) — đúng luật §9 như gd92; CI báo riêng (§4).
3. MTM phút chỉ có giá đóng nến 1m (cận dưới); 1 quan sát lịch sử, không CI.
4. Mọi số là mô tả quá khứ DEV (≤ 2025-12-30), không phải cam kết forward; chưa chạm HOLDOUT 2026.

## 8. TÁI LẬP

```bash
cd /home/ubuntu/src/BinanceFuturesJava
python3 research/analysis/reset_rule_gdv2_run.py g0                       # parity + đo ρ
python3 research/analysis/reset_rule_gdv2_run.py g1 g2 --pct 0.999950829 # GDV2 W30/W90
python3 research/analysis/reset_rule_gdv2_driver.py --json docs/result/gdv2_even.json  # chấm 4 tầng + ĐỘ ĐỀU
```

## 9. COMMIT

- Pre-reg: **`2b4dcbd`** (`docs/prereg/PREREG_GDV2_EVEN.md`).
- Kết quả: commit này (`RESULT_GDV2_EVEN.md` + `gdv2_even.json` + `reset_rule_gdv2_driver.py` + `reset_rule_gdv2_run.py`).
- Kaggle: 3 kernel `chuyendinh/sim-gdv2-{g0,g1,g2}`; dataset jar `chuyendinh/sim-jar-gdv2`.
