# PREREG_GD92_R4 — TEST LẠI GD92 (gate rolling-percentile) TRÊN NỀN R4

**Chốt TRƯỚC khi chạy số.** Ngày: 2026-09-29 (TASK D). Nhánh `module`, HEAD `0264816`.
Nguồn yêu cầu: MASTER `FULL_D_gd92.md` (owner Uni chốt 09-29: **ưu tiên SỐ LỆNH**).
Baseline nghiên cứu MỚI = **`R4`** (`docs/decisions/DECISION_BASELINE_R4.md`, owner 09-29).

Ràng buộc cứng: sim chạy **TRÊN KAGGLE** (KHÔNG Java/sim trên Oracle; bundle `sim-x1-2021-bundle` + overlay jar/profile)
· KHÔNG chạm production/`242`/ONNX/LIVE · KHÔNG push file dữ liệu · **DEV ≤ 2025-12-31** (2026 = HOLDOUT, không dùng) ·
jar build trong **worktree RIÊNG** (KHÔNG đụng working tree chính — TASK B2 song song) · 1 `mvn` build/lúc · output tool nhỏ.

---

## 0. MỤC ĐÍCH (1 câu)

Trên nền **R4** (KEEPLEG0, nhịp 1', `CONC_CAP 15%`, `F_BASE 0.015`, `K=16`, gate scale `1.55`, phí base),
bật lại cơ chế **GD92** — thay hằng số `MIN_MOMENTUM_15M=0.008` bằng **phân vị 92% của `p15` cuộn 90 ngày** (causal) —
rồi chấm bằng **luật 4 tầng §9** (`RISK_APPETITE.md`, **T4 MỚI ưu tiên số lệnh**), để trả lời dứt khoát:
**GD92 có THÊM lệnh ở các quý "chết" của R4 (2023Q1/2025Q2/2025Q3) không, và chất lượng lệnh thêm ra sao.**

---

## 1. BA ARM (khoá trước)

Nền chung MỌI arm = profile **`profiles/r4_kg0_k16_f015_g155.properties`** (chính là baseline R4, phí base
`SIM_RATE_FEE=0.000982` + `SIM_SLIPPAGE_RATE=0.000067` = `0,1116 %/vòng`; nhịp 1' `SIM_ENTRY_SAMPLE_MIN=1`).
Code GD92 = cherry-pick **`1db0613`** (branch `gd92-recheck`) vào HEAD `0264816`, `-n` (KHÔNG commit), build jar riêng.

| arm | thay đổi so R4 | ghi chú |
|---|---|---|
| **D0** | không (key `SIM_GATE_ROLLING_*` KHÔNG khai) | **parity BẮT BUỘC** `md5(printDone) = 06fd6e9aa9c916945b2cf12310b337ff` (n 2027, eq 104 489) trên jar MỚI |
| **D1** | + `SIM_GATE_ROLLING_PCT=0.92` + `SIM_GATE_ROLLING_DAYS=90`; giữ `SIM_GATE_DYN_SCALE=1.55` | **ứng viên chính** |
| **D2** | + `SIM_GATE_ROLLING_PCT=0.92` + `SIM_GATE_ROLLING_DAYS=90`; `SIM_GATE_DYN_SCALE=1.00` | công thức GD92 gốc trên size R4 |

`SIM_GATE_P15_Q` (GATE-RECAL W=30d, cơ chế KHÁC) **KHÔNG khai** ở mọi arm ⇒ byte-identical ở nhánh đó.
`k = 2` ứng viên (D1/D2) ⇒ **`inflate(2) = sqrt(2·ln 2) = 1,1774`**; seed `20260905`, NREP 2000, block 72 h.

## 2. LUẬT 4 TẦNG §9 (owner 09-29) — KHÁC bản tool cứng

- **T1 — RÀO RỦI RO (MTM phút):** `maxDD` **MTM phút** năm xấu nhất ≤ 40 % · `UW ≤ 250` ngày · quý xấu nhất ≥ −20 % ·
  **0 năm âm** (CỨNG) · conc 1 coin ≤ 15 % (CỨNG).
- **T2 — RÀO ĐỘ BỀN:** `q* ≥ 15 %` · `%PnL top-1% lệnh ≤ 25 %`.
- **T3 — NON-INFERIORITY vs D0:** `win%` ≥ −2,0 pp · `TSloss%` ≤ +2,5 pp (điểm ước lượng, so D0).
- **T4 — MỤC TIÊU (MỚI, ưu tiên số lệnh):** **`n` là mục tiêu chính** · `Calmar_MTM ≥ 0,90 × D0` · `conc ≤ D0`.

**BỎ khỏi T1–T3** (đo 0/20 bind ở P1, `RESULT_RESET_RULE_P1`): trần gross ≤ 70 % · `mP|SM%/mP|SL%` tầng 3 ·
"bỏ top-3 episode" trong tầng 2. (Khác tool cứng `reset_rule_score.py` — dùng driver mỏng, không viết lại thuật toán.)

## 3. KIỂM HỢP LỆ (cổng DỪNG — bắt buộc trước khi chấm)

1. **Parity D0:** `md5(printDone) = 06fd6e9aa9c916945b2cf12310b337ff` · `n = 2027` · `equity = 104 489` trên jar MỚI
   (chứng minh 3 điểm nối GD92 không dịch bit nào khi key `SIM_GATE_ROLLING_*` vắng). Lệch ⇒ **DỪNG**.
2. **`[GATE-ROLL]` BẬT thật** ở D1/D2 (log: `pct=0.92 window=90d | ... moc gio ...`), `nBeforeFirst=0`.
3. **`gross MAX < U_MAX 0,60`** + báo `[CONC-PC] blocked=` (trần 15 % không chặn leg nào ngoài dự kiến).

## 4. DỰ BÁO GHI TRƯỚC (đối chiếu, KHÔNG sửa sau)

1. D0 = R4 qua T1–T2; Calmar_MTM ≈ 1,676 (đã biết từ P2), n 2027, conc 5,30 %.
2. **GD92 mở gate ở quý yên** ⇒ n(D1) > n(D0); lệnh tăng tập trung ở 2023Q1 (D0 ~6 lệnh), 2025Q2 (~33), 2025Q3 (~38).
3. **Rủi ro (MASTER):** lệnh quý yên chất lượng thấp ⇒ `win%`/`TSloss%` D1 tệ hơn D0, có thể vượt trần T3 (−2,0/+2,5 pp);
   Calmar_MTM D1 < D0 vì quý yên thêm lệnh mà lãi không bù được đuôi.
4. D2 (scale 1.00) mở gate MẠNH hơn D1 ⇒ n(D2) > n(D1), nhưng chất lượng càng loãng hơn.

## 5. OUTPUT

- Báo cáo: `docs/result/RESULT_GD92_R4.md` + `docs/result/gd92_r4.json`.
- Bảng THEO QUÝ cho D0/D1/D2 (dùng lại `~/claude_master/0929/qstat_r4.py <tag>`): n (sel/BD/DCA), win%, TSloss%,
  meanP%, PnL, ROI%, maxDD quý, UW.
- Driver mỏng `research/analysis/reset_rule_gd92r4_driver.py` (gọi lại `reset_rule_score.py` + áp §9 T1–T4 đúng).

## 6. NHÁNH PHỤ (chỉ nếu arm qua 4 tầng @base)

Nếu D1 (hoặc D2) qua cả 4 tầng ở **base**:
1. Chạy lại arm đó ở **@stress** (`SIM_SLIPPAGE_RATE=0.000259` ⇒ `0,150 %/vòng`) + chấm lại 4 tầng (so D0 @stress).
2. Độ bền kiểu P3: episode jackknife bỏ top-1/3/5; bootstrap cụm episode 5000 rep seed `20260928`; **CI chênh Calmar vs D0**.

**LUẬT KẾT LUẬN:** chỉ đề xuất thay R4 nếu **PASS 4 tầng @base+@stress** VÀ **jackknife không tệ hơn D0** VÀ
**CI chênh Calmar không âm ngoài 0**. Ngược lại ⇒ giữ R4.

## 7. KỶ LUẬT

Không merge `gd92-recheck` vào `module` (code GD92 chỉ cherry-pick `-n` vào worktree, sau build `git checkout -- src/`).
Không chạm 242/holdout 2026. Không quét biến thể (pct khác 0.92, W khác 90d). Không đổi incumbent production (`B*`).
Nếu D1/D2 thắng: chỉ ghi rõ GateRollingThreshold có đường LIVE chưa (đọc code) + cần gì để port — **không port ở task này**.
