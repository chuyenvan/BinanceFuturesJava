# PREREG_CRASH_PENALTY — ĐỘ BỀN R4 & G2 khi PHẠT THẬT leg "sập" (E2: kiểm độ bền, KHÔNG tối ưu)

Ngày chốt: **2026-09-29**. Viết **TRƯỚC** khi chạy bất kỳ số kết quả nào của vòng này. Sau khi thấy số
**KHÔNG sửa thiết kế** (mọi thay đổi ⇒ AMENDMENT có lý do, ghi cuối file, commit trước khi xem số bị ảnh hưởng).

Bối cảnh: `RESULT_LATENCY_FILL` (`63fc042`) kết luận `+1,675 %/chân` của `RESULT_COST_TRUTH` là **(a) lệch mốc đo**,
không bias; đo lại đúng mốc nến quyết định ⇒ nhóm sập `slip_dec = +0,693 %/chân`, **CI95 `[−0,187, +1,497]` CHỨA 0**
(n=27, thiếu power). ⇒ **KHÔNG rescore**, giữ `base 0,112 %/vòng`. Vòng này KHÔNG tranh cãi kết luận đó —
thay vào đó hỏi **"nếu phạt thật cỡ đó thì sao"**: phạt cỡ **điểm (+0,69 %)** và **biên trên CI (+1,50 %)** vào
GIÁ VÀO của leg sập, R4 và G2 còn qua 4 tầng không. Đây là **stress test độ bền**, KHÔNG chọn tham số nào.

Ràng buộc (cứng): sim **TRÊN KAGGLE** (bundle `sim-x1-2021-bundle`, `TICKER_SOURCE=file`) · **0 sim Oracle** (shadow-c3
đang chạy) · **DEV ≤ 2025-12-31** (2026 = HOLDOUT, KHÔNG dùng) · **KHÔNG chạm 242/production/ONNX/LIVE** ·
**KHÔNG push file dữ liệu** · SLF4J (Java) / `logging` (Python) · `nice -n 10` · jar build trong **worktree riêng**.

## 0. CÂU HỎI QUYẾT ĐỊNH

1. **Phạt `+0,69 %` (điểm) vào giá vào leg sập:** R4 và G2 còn PASS 4 tầng §9 không?
2. **Phạt `+1,50 %` (biên trên CI95) vào giá vào leg sập:** edge còn sống không?
3. **G2 có NHẠY hơn R4** trước cùng mức phạt không (Δ trạng thái 4 tầng / Δ Calmar / Δ ROI lớn hơn)?

## 1. ĐỊNH NGHĨA "LEG SẬP" (y hệt `RESULT_LATENCY_FILL`, KHÔNG tự chế)

Leg **sập** ⇔ nến **QUYẾT ĐỊNH** (nến 1m mà sim dùng làm giá vào, `SimulatorMarketLevelTicker1MStopLoss.java:1372`
`entry = ticker.priceClose`) có `bar_ret ≤ −1 %`, với:

```
bar_ret = (priceClose − priceOpen) / priceOpen     // của nến quyết định (KlineObjectSimple)
```

Đây chính là ngưỡng `CRASH_PROXY` mà `RESULT_COST_TRUTH`/`RESULT_LATENCY_FILL` dùng (`−1 %`), áp trên **nến quyết định**
(đúng mốc sim). Áp cho **MỌI leg entry** (PREDICT_SYMBOL_TRADE · BIG_DOWN · DCA_LEVEL1) — không phân biệt `level`.

## 2. CODE (chốt trước · byte-identical khi vắng key)

- Thêm key `SIM_CRASH_ENTRY_PENALTY` (float, **fraction**, đọc qua `Cfg.get` như mọi `SIM_*`).
- `Configs.CRASH_ENTRY_PENALTY` default `0f`; parse `SIM_CRASH_ENTRY_PENALTY` trong block SIM-override (cạnh
  `SIM_RATE_FEE`/`SIM_SLIPPAGE_RATE`).
- Trong `createOrder` (sau `Float entry = ticker.priceClose;`, **trước** `calQuantityTest`), nếu `penalty > 0`:
  ```java
  if (Configs.CRASH_ENTRY_PENALTY > 0f) {
      float barRet = (ticker.priceClose - ticker.priceOpen) / ticker.priceOpen;
      if (barRet <= -0.01f) {
          entry = entry * (1f + Configs.CRASH_ENTRY_PENALTY);   // BUY: vào ĐẮT hơn = bất lợi
          // đếm leg bị phạt (total + theo năm GMT+7), log [CRASH-PENALTY]
      }
  }
  ```
- Đếm `crashPenTotal` + `crashPenByYear` (TreeMap năm → count, năm = `Utils.sdfMonth` GMT+7), log summary
  `[CRASH-PENALTY] SUMMARY penalty=… total=… byYear=…` ở cuối run (chỉ khi penalty > 0).
- **Parity BẮT BUỘC** (key vắng ⇒ byte-identical, jar MỚI chạy trên Kaggle):
  - R4: `md5(printDone) = 06fd6e9aa9c916945b2cf12310b337ff` (n 2027, eq 104 489).
  - G2: `md5(printDone) = 853aaa086be7d2d811162879df0653f6` (n 2509, eq 131 374).

## 3. ARM (4 kernel @base + 2 kernel parity)

Nền chung mọi arm: phí **base** `0,1116 %/vòng` (trong profile). `k = 4` ⇒ `inflate = √(2·ln 4) = 1,6651`.

| tag | nền | penalty | mục đích |
|---|---|---|---|
| `cp-r4-parity` | R4 (profile nguyên) | — | parity 06fd6e9a |
| `cp-g2-parity` | G2 (gate rolling) | — | parity 853aaa |
| `cp-r4-p069` | R4 | `0.0069` | độ bền R4 @điểm |
| `cp-r4-p150` | R4 | `0.0150` | độ bền R4 @biên trên |
| `cp-g2-p069` | G2 | `0.0069` | độ bền G2 @điểm |
| `cp-g2-p150` | G2 | `0.0150` | độ bền G2 @biên trên |

- **R4** = `profiles/r4_kg0_k16_f015_g155.properties`.
- **G2** = R4 + `SIM_GATE_ROLLING_MODE=ratio`, `SIM_GATE_ROLLING_PCT=0.99995083`, `SIM_GATE_ROLLING_DAYS=90`.
- Jar = GDV2 jar (`sim-jar-gdv2`, sha256 `7368be46…`) **+ code §2**, build trong worktree riêng (base `2b4dcbd3`
  + cherry-pick GDV2 như `wt_gdv2`), upload làm dataset `sim-jar-crashpen`.

## 4. BÁO 4 TẦNG §9 (mỗi arm so **R4 gốc** = baseline)

Baseline = **R4 gốc** (`cp-r4-parity`, byte-identical `gdv2-g0`, Calmar_MTM 1,676 · n 2027 · conc 5,30 %).
Thước/ngưỡng y hệt `RISK_APPETITE.md` §9.2/§9.3 (dùng lại `reset_rule_score.py`, KHÔNG viết lại thuật toán):

- **T1** RÀO RỦI RO (MTM phút): maxDD phút ≤ 40 %/năm · UW ≤ 250 ngày · quý xấu ≥ −20 % · 0 năm âm (CỨNG) · conc 1 coin ≤ 15 %.
- **T2** RÀO ĐỘ BỀN: `q* ≥ 15 %` · `%PnL top-1% lệnh ≤ 25 %`.
- **T3** NON-INFERIORITY vs R4: `win% ≥ −2,0 pp` · `TSloss% ≤ +2,5 pp` (CI block-72h · 2000 rep · seed 20260905 · inflate 1,6651).
- **T4** MỤC TIÊU: `Calmar_MTM ≥ 0,90 × R4` · `conc ≤ R4` (n là mục tiêu chính, báo riêng).

Báo trạng thái T1–T4 của 4 arm; ghi rõ **arm nào còn PASS, arm nào FAIL ở tầng nào** so R4 gốc.

## 5. BẢNG NĂM (mỗi arm + R4 gốc) — `n` · `ROI` · `TSloss` · `maxDD`

Theo **năm (calendar, GMT+7)**:

| cột | định nghĩa | nguồn |
|---|---|---|
| `n` | số leg **vào** trong năm | `ts.year` từ printDone.csv |
| `ROI %` | return equity năm đó | `yearly_quarterly(eq)` (`core_metrics.yr`) |
| `TSloss %` | % leg (vào năm đó) kết thúc `STOP_LOSS_DONE` | `rates_profit` theo năm |
| `maxDD %` | maxDD **MTM phút** trong năm | `run_mtm.dd_year` |

Bảng năm để đọc **phân bố độ nhạy theo thời gian** (năm nào bị phạt nặng nhất — năm nhiều leg sập nhất).

## 6. SỐ LEG BỊ PHẠT / NĂM

Đọc từ log `[CRASH-PENALTY] SUMMARY … byYear=…` của mỗi arm (Java đếm, khớp định nghĩa §1). Báo `total` + `byYear`
để đối chiếu với bảng năm §5 (năm nhiều leg sập = năm nhạy phạt).

## 7. LUẬT KẾT LUẬN (chốt TRƯỚC, không đổi sau khi thấy số)

1. **Edge "sống"** ở mức phạt P ⇔ arm đó còn **PASS cả 4 tầng** so R4 gốc ở mức P.
2. **R4 bền** ⇔ R4 @`1,50 %` vẫn PASS 4 tầng (biên trên CI là worst-case đã đo).
3. **G2 nhạy hơn R4** ⇔ (ΔCalmar_MTM của G2@P) < (ΔCalmar_MTM của R4@P) cùng P, hoặc G2 FAIL 4 tầng trước R4.
4. Mọi kết luận là **mô tả DEV ≤ 2025-12-30**, không cam kết forward; KHÔNG chọn/tune tham số từ task này.

## 8. HẠN CHẾ (khai trước)

1. `n=27` cho nhóm sập (RESULT_LATENCY_FILL) ⇒ CI thiếu power; vòng này chỉ là **stress giả định**, không phải đo lại
   chi phí thật.
2. Phạt áp **đều 1 mức** cho mọi leg sập (không phân biệt độ sâu bar_ret) — xấp xỉ đã khai.
3. `quantity = budget/entry` giảm nhẹ khi vào đắt hơn (hiệu ứng bậc 2, đúng bản chất margin cố định).
4. MTM phút chỉ có giá đóng nến 1m (cận dưới); 1 quan sát lịch sử, không CI.
5. G2 = GDV2 W90 nói riêng; kết luận nhạy cảm chỉ cho cặp (R4, G2) này.

## 9. TÁI LẬP

```bash
# jar trong worktree riêng (base 2b4dcbd3 + GDV2 + code §2):
#   /home/ubuntu/tools/apache-maven-3.9.9/bin/mvn -o package  (worktree wt_crash)
# upload jar -> dataset sim-jar-crashpen; 6 kernel:
python3 - <<'PY'
import sys; sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks
R4 = "r4_kg0_k16_f015_g155"
G2OV = {"SIM_GATE_ROLLING_MODE":"ratio","SIM_GATE_ROLLING_PCT":"0.99995083","SIM_GATE_ROLLING_DAYS":"90"}
JAR = "sim-jar-crashpen"; BND = "sim-x1-2021-bundle"
refs = [
  ks.submit("cp-r4-parity", R4, {}, jar_ds=JAR, bundle_ds=BND, sim_end_date="20251231"),
  ks.submit("cp-g2-parity", R4, G2OV, jar_ds=JAR, bundle_ds=BND, sim_end_date="20251231"),
  ks.submit("cp-r4-p069", R4, {"SIM_CRASH_ENTRY_PENALTY":"0.0069"}, jar_ds=JAR, bundle_ds=BND, sim_end_date="20251231"),
  ks.submit("cp-r4-p150", R4, {"SIM_CRASH_ENTRY_PENALTY":"0.0150"}, jar_ds=JAR, bundle_ds=BND, sim_end_date="20251231"),
  ks.submit("cp-g2-p069", R4, {**G2OV,"SIM_CRASH_ENTRY_PENALTY":"0.0069"}, jar_ds=JAR, bundle_ds=BND, sim_end_date="20251231"),
  ks.submit("cp-g2-p150", R4, {**G2OV,"SIM_CRASH_ENTRY_PENALTY":"0.0150"}, jar_ds=JAR, bundle_ds=BND, sim_end_date="20251231"),
]
ks.wait(refs)
PY
# chấm 4 tầng + bảng năm:
python3 research/analysis/reset_rule_crashpen_driver.py --json docs/result/crash_penalty.json
```
