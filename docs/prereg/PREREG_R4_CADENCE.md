# PREREG_R4_CADENCE — ĐO GIÁ TRỊ NHỊP 1' CỦA R4 (C0 nhịp 1' vs C1 nhịp live 15')

**Chốt TRƯỚC khi chạy số.** Ngày: 2026-09-29 (TASK B3). Nhánh `module`, HEAD `68a2836`.
Nguồn yêu cầu: MASTER `TASK_B3_design.md` (owner Uni). Baseline nghiên cứu = **`R4`**
(`docs/decisions/DECISION_BASELINE_R4.md`). KHÔNG deploy · KHÔNG sửa code live · KHÔNG đụng shadow-c3/242.

Ràng buộc cứng: sim chạy **TRÊN KAGGLE** (KHÔNG Java/sim trên Oracle; bundle `sim-x1-2021-bundle`) ·
KHÔNG chạm production/`242`/ONNX/LIVE · KHÔNG push file dữ liệu · **DEV ≤ 2025-12-31** (2026 = HOLDOUT, không dùng) ·
output tool nhỏ · 0 sim Oracle.

---

## 0. MỤC ĐÍCH (1 câu)

Sim hiện tại chạy R4 ở **nhịp 1'** (`SIM_ENTRY_SAMPLE_MIN=1` = no-op) — tức selector (PREDICT_SYMBOL_TRADE)
được xét entry **mỗi phút**. Đường **LIVE hiện tại** lại chọn lệnh selector **mỗi 15'** (`LIVE_ENTRY_GRID_MIN=15`),
còn BIG_DOWN/DCA vẫn 1' (CADENCE-SPLIT-V2). Đo xem nếu R4 chạy **đúng nhịp live** (selector 15', BD/DCA 1')
thì giữ được **bao nhiêu % `n` và `Calmar`** so với nhịp 1' — từ đó quyết định **có đáng làm kỹ thuật 1'
(full-universe < 45s/lượt) hay không**.

## 1. HAI ARM (khoá trước)

Nền chung MỌI arm = profile **`profiles/r4_kg0_k16_f015_g155.properties`** (baseline R4: KEEPLEG0,
`CONC_CAP 15%`, `SIM_F_BASE 0.015`, `SELECTOR_RANK_TOPK 16`, `SIM_GATE_DYN_SCALE 1.55`, phí base
`SIM_RATE_FEE=0.000982`+`SIM_SLIPPAGE_RATE=0.000067` = `0,1116 %/vòng`).

| arm | thay đổi so R4 | ý nghĩa |
|---|---|---|
| **C0** | không (profile nguyên, `SIM_ENTRY_SAMPLE_MIN=1` = no-op) | **parity BẮT BUỘC** `md5(printDone) = 06fd6e9aa9c916945b2cf12310b337ff` (n 2027, eq 104 489) |
| **C1** | `SIM_ENTRY_SAMPLE_MIN=15` | **nhịp live**: selector (PREDICT_SYMBOL_TRADE) lưới 15', BIG_DOWN/DCA giữ 1' |

### 1.1 Key sim đúng — `SIM_ENTRY_SAMPLE_MIN` áp leg nào (ĐÃ ĐỌC CODE, khoá trước)

`SimulatorMarketLevelTicker1MStopLoss.createOrder(...)` (comment `[GATE-RECAL 2026-09-26]`, ~:1305):

```java
if (Configs.ENTRY_SAMPLE_MIN > 1
        && levelChange != MarketLevelChange.BIG_DOWN
        && levelChange != MarketLevelChange.DCA_LEVEL1) {
    long _t = EntryGate.CURRENT_P15_TIME;
    if (_t == Long.MIN_VALUE) _t = ticker.startTime;
    if (((_t / 60000L) % Configs.ENTRY_SAMPLE_MIN) != 0) return;
}
```

`Configs.ENTRY_SAMPLE_MIN` ← key `SIM_ENTRY_SAMPLE_MIN` (`Configs.java:832`; ≤1 ⇒ byte-identical).
⇒ **`SIM_ENTRY_SAMPLE_MIN=15` chỉ lọc entry mở mới KHÔNG phải BIG_DOWN và KHÔNG phải DCA_LEVEL1**
(= leg selector PREDICT_SYMBOL_TRADE), giữ BIG_DOWN/DCA ở nhịp 1'. **ĐÚNG thiết kế live CADENCE-SPLIT-V2** ⇒
**sim TÁCH được theo leg** ⇒ C1 = `SIM_ENTRY_SAMPLE_MIN=15` **chính xác, KHÔNG cần fallback "15' toàn bộ"**.

## 2. LUẬT 4 TẦNG §9 (owner 09-29) — KHÁC bản tool cứng

- **T1 — RÀO RỦI RO (MTM phút):** `maxDD` **MTM phút** năm xấu nhất ≤ 40 % · `UW ≤ 250` ngày · quý xấu nhất ≥ −20 % ·
  **0 năm âm** (CỨNG) · conc 1 coin ≤ 15 % (CỨNG).
- **T2 — RÀO ĐỘ BỀN:** `q* ≥ 15 %` · `%PnL top-1% lệnh ≤ 25 %`.
- **T3 — NON-INFERIORITY vs C0:** `win%` ≥ −2,0 pp · `TSloss%` ≤ +2,5 pp (điểm ước lượng, so C0).
- **T4 — MỤC TIÊU (MỚI, ưu tiên số lệnh):** **`n` là mục tiêu chính** (báo cáo, KHÔNG gate) ·
  `Calmar_MTM ≥ 0,90 × C0` · `conc ≤ C0`.

**BỎ khỏi T1–T3** (đo 0/20 bind ở P1, `RESULT_RESET_RULE_P1`): trần gross ≤ 70 % · `mP|SM%/mP|SL%` tầng 3 ·
"bỏ top-3 episode" tầng 2. (Dùng lại driver mỏng kiểu `reset_rule_gd92r4_driver.py`, KHÔNG viết lại thuật toán.)

### 2.1 `k` và CI

`k = 1` ứng viên (chỉ C1 so C0) ⇒ **không cần hiệu chỉnh đa so sánh** (single comparison). CI tầng 3
(block-72h, 2000 rep, seed `20260905`) báo cáo với **INFL = 1,0** (công thức `sqrt(2·ln k)` chỉ có nghĩa khi k ≥ 2).
`win%`/`TSloss%` tầng 3 vẫn là **điểm ước lượng** (không qua CI), đúng như driver GD92.

## 3. KIỂM HỢP LỆ (cổng DỪNG — bắt buộc trước khi chấm)

1. **Parity C0:** `md5(printDone) = 06fd6e9aa9c916945b2cf12310b337ff` · `n = 2027` · `equity = 104 489`.
   Lệch ⇒ **DỪNG** (báo FAIL, không chấm C1).
2. **Jar đúng:** kernel log `JAR_SHA256=8d93dad9…` (jar dd8d063, **Java-identical HEAD 68a2836** —
   `git diff dd8d063..HEAD -- src/main/java` = rỗng; parity R4 đã PASS trên dòng jar này ở GD92 D0).
3. **`[CONC-PC]` trần 15%**: `blocked=` không chặn leg nào ngoài dự kiến (C0/C1 đều phải báo).

## 4. DỰ BÁO GHI TRƯỚC (đối chiếu, KHÔNG sửa sau)

1. C0 = R4: n 2027, eq 104 489, CAGR 27,53 %, ddPhut −16,42 %, UW 164,7, Calmar_MTM 1,676, conc 5,30 % (đã biết P2).
2. **C1 (selector 15') sẽ MẤT lệnh selector**: live giữ lệnh ở 1 trong 15 phút ⇒ `n(C1) < n(C0)`. Dự báo **giữ ~60–80 %
   n** (phần lệnh mất chủ yếu là selector; BIG_DOWN/DCA nguyên vẹn; selector ~83 % leg đầu nên mất nhiều nhất ở nhánh này).
3. **Chất lượng từng lệnh (win%/TSloss%) gần như KHÔNG đổi** (C1 là tập con chọn mốc thưa hơn của C0, cùng gate/S1) ⇒
   T3 non-inferior PASS. **Calmar_MTM có thể GIỮ hoặc NHỈNH** (bỏ các entry selector 1' nhiễu ⇒ đuôi mỏng hơn) nhưng
   `n` giảm rõ là đánh đổi.
4. **Nếu C1 giữ ≥ 90 % n và Calmar ≥ 0,90×C0** ⇒ kỹ thuật 1' (full-universe < 45s) **KHÔNG đáng** (phương án C/B đủ).
   Nếu C1 mất > 20–30 % n ⇒ kỹ thuật 1' **đáng** (phương án A/B).

## 5. OUTPUT

- Báo cáo: `docs/result/RESULT_R4_CADENCE.md` + `docs/result/r4_cadence.json`.
- Bảng THEO QUÝ cho C0/C1 (driver mỏng, tái dùng mẫu `qstat`): n (sel/BD/DCA), win%, TSloss%, meanP%, PnL.
- Driver mỏng `research/analysis/reset_rule_cadence_driver.py` (gọi lại `reset_rule_score.py` + áp §9 T1–T4 đúng,
  INFL=1.0, k=1).

## 6. KỶ LUẬT

- KHÔNG quét thêm biến thể cadence (chỉ C0/C1). KHÔNG tune sau khi thấy số; mọi đổi = AMENDMENT commit trước.
- KHÔNG chạm 242/holdout 2026/shadow-c3. KHÔNG deploy. 0 sim Oracle (chỉ Kaggle).
- KHÔNG đổi incumbent production. Kết quả là **ĐO LƯỜNG** (quyết định đáng làm 1' hay không), KHÔNG phải "đổi baseline".
