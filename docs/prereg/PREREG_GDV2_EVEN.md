# PREREG_GDV2_EVEN — Gate rolling "đều lệnh" (quantile trên CHÍNH tỉ số cuối cùng) trên nền R4

**Chốt TRƯỚC khi chạy số.** Ngày: 2026-09-29 (TASK GDV2). Nhánh `module`, HEAD `4017d12`.
Nguồn yêu cầu: MASTER `FULL_GDV2_even.md` (owner Uni chốt 09-29: gate phải cho **ĐỀU lệnh theo thời gian**).
Baseline nghiên cứu = **`R4`** (`profiles/r4_kg0_k16_f015_g155.properties`, md5 `06fd6e9aa9c916945b2cf12310b337ff`).

Ràng buộc cứng: sim chạy **TRÊN KAGGLE** (KHÔNG Java/sim trên Oracle; bundle `sim-x1-2021-bundle` + overlay jar/profile)
· KHÔNG chạm production/`242`/ONNX/LIVE · KHÔNG push file dữ liệu · **DEV ≤ 2025-12-31** (2026 = HOLDOUT, không dùng) ·
jar build trong **worktree RIÊNG** `/home/ubuntu/claude_master/wt_gdv2` (KHÔNG đụng working tree chính) · 1 `mvn` build/lúc ·
output tool nhỏ · Logging **SLF4J** (cấm `System.out`/`printStackTrace`).

---

## 0. MỤC ĐÍCH (1 câu)

GD92 (quantile cuộn trên **p15** rồi nhân hệ số per-coin 0.415–2.0) làm tỉ lệ pass **phụ thuộc hình dạng đuôi p15 theo
regime** (quý yên ⇒ gate gần như đóng, vd D1 cắt 2025Q2 33→18). GDV2 sửa bằng cách tính quantile trên **CHÍNH tỉ số cuối
cùng** `r` (đã chuẩn hoá theo score selector) ⇒ tỉ lệ pass ≈ hằng số theo thời gian, **cùng tổng lượng mở như R4**, chỉ đổi
**PHÂN BỐ theo thời gian**.

---

## 1. THIẾT KẾ (khoá — không đổi sau khi có số)

### 1.1 Tỉ số `r` (mỗi lần gate đánh giá 1 ứng viên)

```
r = p15_t / (max(0.26787, sp_c/0.15×1.2876) × SCALE)
```
với `p15_t = prediction.predReturn15M`, `sp_c = symbolPred` của coin, `SCALE = EntryGate.GATE_DYN_SCALE` (= 1.55 trên R4).
Gate hiện tại (R4) ⇔ `r >= base` với `base = SIM_MIN_MOMENTUM_15M = 0.008` (so sánh `!(p15 < thr)`).

**Phạm vi `r`:** chỉ cho **PREDICT_SYMBOL_TRADE** (`sp != null`, candidate do selector khởi tạo). Leg **BIG_DOWN** (bỏ qua
gate) và **DCA_LEVEL1** (`sp == null`, nhoi) **GIỮ NGUYÊN base 0.008** — không có `sp_c` nên `r` không xác định, và chúng là
thiểu số (34 DCA + 248 BIG_DOWN vs 1745 PREDICT trên R4).

### 1.2 Buffer causal + quantile theo giờ

- Giữ buffer **CAUSAL** các `r` của **MỌI lần đánh giá ứng viên PREDICT** trong quá khứ (`ts < mốc giờ hiện tại`, cửa sổ `W` ngày).
- Mỗi **giờ** `h` (mốc epoch `floor(ts/3600_000)*3600_000`): `q_h = phân vị pct` của buffer `{r : h − W·86400000 ≤ ts < h}`.
- **pass ⇔ `r > q_h`** (thực thi bằng `!(p15 < q_h × factor × SCALE)` qua `EntryGate.threshold(q_h, sp)` — cùng phép nhân/NaN
  như gate hiện tại; khác biệt `>`/`>=` ở đúng biên float là measure-zero).
- **Warm-up:** trước khi buffer đủ **7 ngày** dữ liệu (`h − ts_đầu_tiên < 7·86400000`) ⇒ **fallback base 0.008**, đếm
  `nBeforeFirst` (log 1 lần + tổng cuối run).

### 1.3 Phân vị (convention, khoá)

Sort tăng `a[0..m−1]`; chỉ số `k = min(m−1, max(0, floor(pct·(m−1))))`; `q_h = a[k]` (cùng convention GD92
`GateRollingThreshold`). Thuật toán exact (quickselect trên float[], không nội suy).

### 1.4 Chọn `pct` (1 tham số, KHÔNG PnL)

- **Bước 1** chạy **G0 = R4** (key mới vắng ⇒ byte-identical) có **bộ đếm** (không đổi hành vi) đo
  `ρ = (PREDICT candidates PASS) / (PREDICT candidates evaluated)` trên toàn DEV.
- **`pct = 1 − ρ`** (cùng tổng lượng mở PREDICT như R4, chỉ đổi PHÂN BỐ theo thời gian). Đây là **hiệu chỉnh dùng cả kỳ DEV,
  1 tham số, không PnL**. Ghi rõ: `pct` được KHOÁ sau khi đọc `ρ` từ G0; không điều chỉnh theo bất kỳ kết quả nào khác.

---

## 2. ARM (khoá trước)

Nền chung MỌI arm = profile **`r4_kg0_k16_f015_g155.properties`** (R4, phí base `0,1116 %/vòng`, nhịp 1').

| arm | thay đổi so R4 | ghi chú |
|---|---|---|
| **G0** | không (key `SIM_GATE_ROLLING_MODE` KHÔNG khai) | **parity BẮT BUỘC** `md5(printDone) = 06fd6e9aa9c916945b2cf12310b337ff` (n 2027, eq 104 489); đồng thời đo `ρ` |
| **G1** | + `SIM_GATE_ROLLING_MODE=ratio` + `SIM_GATE_ROLLING_PCT=1−ρ` + `SIM_GATE_ROLLING_DAYS=30` | GDV2 W30 |
| **G2** | + `SIM_GATE_ROLLING_MODE=ratio` + `SIM_GATE_ROLLING_PCT=1−ρ` + `SIM_GATE_ROLLING_DAYS=90` | GDV2 W90 |

`k = 2` ứng viên (G1/G2) ⇒ **`inflate(2) = sqrt(2·ln 2) = 1,1774`**; CI block-72h, 2000 rep, seed `20260905`.

---

## 3. CODE (worktree RIÊNG, KHÔNG merge module)

- Worktree `/home/ubuntu/claude_master/wt_gdv2` từ `module` HEAD `4017d12` + `git cherry-pick -n 1db0613` (code GD92
  `GateRollingThreshold` gốc + 3 điểm nối) làm nền.
- Class mới **`GateRollingRatio`** (parallel `GateRollingThreshold`): buffer online (vì `r` cần `symbolPred` chỉ có lúc chạy).
  Key mới `SIM_GATE_ROLLING_MODE=ratio` (+ dùng lại `SIM_GATE_ROLLING_PCT`, `SIM_GATE_ROLLING_DAYS`).
- `AIRejectFilter.entryGate` dispatch: `GateRollingRatio` (MODE=ratio) → `GateRollingThreshold` (GD92, nếu PCT khai không MODE)
  → base. `GateRollingThreshold.init` thêm guard **TẮT khi MODE=ratio** (tránh hai cơ chế cùng chạy).
- Bộ đếm ρ: static counters `predictGateSeen`/`predictGatePass` (PREDICT) + log `[GATE-RHO]` tổng + `[GATE-RHO-Q]` theo quý.
- **Unit test causal:** `q_h` tại giờ `h` chỉ dùng `r` có `ts < h` (feed ứng viên giờ `h` vào ⇒ `q_h` không đổi).
- SLF4J; cấm `System.out`/`printStackTrace`.

---

## 4. DỰ BÁO GHI TRƯỚC (đối chiếu, KHÔNG sửa sau)

1. G0 = R4 qua T1–T2; Calmar_MTM ≈ 1,676, n 2027, conc 5,30 % (đã biết từ P2). `ρ` ≈ n_pass/n_cand từ log `[GATE]` R4
   (P2: R4 n_cand 35,49M / n_pass 1819 ⇒ ρ cỡ ~5,1e-5, `pct` ≈ 0,99995).
2. **GDV2 giữ quota đều** ⇒ tỉ lệ pass theo quý gần hằng `ρ`, `CV(n quý)` và `min n quý` của G1/G2 tốt hơn G0; không còn quý
   "chết" (2023Q1 6 lệnh) hay bị cắt đột ngột (2025Q2).
3. **Rủi ro (MASTER):** gate giữ quota sẽ **vào lệnh cả regime xấu (2022)** ⇒ theo dõi T1 năm 2022, `TSloss%` 2022; tổng lệnh
   có thể không còn tập trung vào các quý "tốt" như R4 ⇒ `Calmar_MTM` có thể < G0. Đây là lần thử **~26** trên cùng DEV.

---

## 5. CHẤM (điểm)

### 5.1 4 tầng RISK_APPETITE §9 (G1, G2 vs G0) @base — dùng lại `reset_rule_score.py` (driver mỏng)

- **T1** RÀO RỦI RO (MTM phút): maxDD phút năm xấu ≤40% · UW ≤250 ngày · quý xấu ≥−20% · 0 năm âm (CỨNG) · conc 1 coin ≤15% (CỨNG).
- **T2** RÀO ĐỘ BỀN: `q* ≥ 15%` · `%PnL top-1% lệnh ≤ 25%`.
- **T3** NON-INFERIORITY vs G0: `win% ≥ −2,0 pp` · `TSloss% ≤ +2,5 pp` (điểm ước lượng).
- **T4** MỤC TIÊU (ưu tiên số lệnh): **`n` là mục tiêu chính** · `Calmar_MTM ≥ 0,90×G0` · `conc ≤ G0`.

### 5.2 ĐỘ ĐỀU (mới — mô tả + tiêu chí ứng viên)

Theo quý `2021Q3..2025Q4` (18 quý): `n` (lệnh/quý), **tỉ lệ pass quý** (từ `[GATE-RHO-Q]`); thống kê **CV(n quý)** =
`std/mean`, **min n quý**, **số quý n<40**, **độ lệch tỉ lệ pass quý so ρ** (RMS). So **G0** và **D1** (GD92, từ
`docs/result/gd92_r4.json` / log `gd92-r4-d1`) để xác nhận GDV2 **đều hơn thật**.

### 5.3 Tiêu chí ỨNG VIÊN (đi tiếp task sau @stress + P3)

**Ứng viên ⇔ PASS 4 tầng @base VÀ `CV(n quý) < G0` VÀ `min n quý > G0`.** (Chỉ ứng viên mới chạy @stress + P3 ở task sau.)

---

## 6. OUTPUT

- Báo cáo `docs/result/RESULT_GDV2_EVEN.md` + `docs/result/gdv2_even.json`.
- Bảng quý đầy đủ (dùng lại `~/claude_master/0929/qstat_r4.py <tag>`): n (sel/BD/DCA), win%, TSloss%, meanP%, PnL, ROI%,
  maxDD quý, UW + bảng ĐỘ ĐỀU (n/tỉ lệ pass theo quý, CV/min/count<40/lệch so ρ).
- Driver mỏng `research/analysis/reset_rule_gdv2_driver.py` (gọi lại `reset_rule_score.py` + áp §9 T1–T4 + ĐỘ ĐỀU).

---

## 7. KỶ LUẬT

Không merge code vào `module` (chỉ cherry-pick `-n` trong worktree, sau build `git checkout -- src/`). Không chạm 242/holdout
2026. Không quét biến thể (chỉ W∈{30,90}, `pct=1−ρ`). Không đổi incumbent production (`B*`). Nếu G1/G2 thắng: chỉ ghi rõ
`GateRollingRatio` có đường LIVE chưa (đọc code) + **cần gì để port** (buffer 30/90d warm-up cho live) — **không port ở task này**.
