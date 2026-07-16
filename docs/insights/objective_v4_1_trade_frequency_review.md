# Objective V4.1 — Review "ưu tiên tần suất lệnh" (tham chiếu V1)

> TASK-3a — Proposal ONLY. KHÔNG áp vào production, KHÔNG commit, KHÔNG chạy WFO.
> Mục tiêu: giải thích vì sao hàm mục tiêu **HPOFitnessCalculatorV4 (V4.1)** không thưởng
> đủ cho việc vào nhiều lệnh (gốc rễ 9/16 window OOS rơi SENTINEL) và đề xuất sửa
> mà **KHÔNG phá ngữ nghĩa pass-criteria pre-registered**.

## 0. Bối cảnh đo được (nhắc lại)

WFO N=30, 16 window OOS quý, ticker sạch:

| Model | %OOS dương | WFE median | maxDD | Verdict |
|---|---|---|---|---|
| maxfav3 | 43.8% (7/16) | 1.009 | 38.7% | FAIL |
| ret2 | 37.5% (6/16) | ~0.54 | — | FAIL |

Ngưỡng PASS (pre-registered, `StrategyWfoTask`): `%OOS ≥ 70%`, `WFE median ≥ 0.5`, `maxDD ≤ 50%`.

Gốc rễ: ~9/16 window là SENTINEL — chủ yếu `TOO_FEW_TRADES`, kèm `ZERO_TRADES` và
`TOO_MUCH_CAPITAL_LOCK`. Hệ **không đủ tần suất cơ hội**. Đang nghiêng maxfav3.

## 1. Bản đồ file & vai trò (đo trực tiếp trong repo)

- `ai_ml/hpo/HPOFitnessCalculator.java` — **V1** (bản cũ "ưu tiên nhiều lệnh").
- `ai_ml/hpo/HPOFitnessCalculatorV3.java` — **V3** (trung gian: V1 + phạt giam-vốn log + DD theo vùng).
- `ai_ml/hpo/HPOFitnessCalculatorV4.java` — **V4 / V4.1** (đang dùng; constraint-first + Calmar thuần).
- `ai_ml/wfo/framework/tasks/StrategyWfoTask.java` — WFO thật: TRAIN chọn best genome theo
  `finalFitness`, OOS đo lại, tính WFE + %OOS + verdict.
- `ai_ml/hpo/TestFitnessV41.java` — GATE tầng 1 (unit test A–E cho V4.1).

### Điểm mấu chốt về LUỒNG (quyết định toàn bộ đề xuất bên dưới)

Trong `StrategyWfoTask.runJob`:

- **TRAIN**: random search N mẫu → chọn `bestGenome` = genome có `finalFitness` (isFit) lớn nhất.
  `bestIsPnl = totalProfit` của genome đó.
- **OOS**: áp `bestGenome`, backtest lại → `oos`.
- `WFE = oos.totalProfit / bestIsPnl` (PnL_OOS / PnL_IS — **KHÔNG** dùng calmar/finalFitness).
- `%OOS dương`: đếm window có `oosNote == "SUCCESS" && oosPnl > 0`.
- `Verdict PASS` ⟺ `wfeMedian ≥ 0.5 && posRatio ≥ 0.70 && worstDdPct ≤ 0.50`.

> **Hệ quả then chốt:** `finalFitness` CHỈ được dùng để **chọn genome trên TRAIN**.
> Nó KHÔNG vào WFE (dùng `totalProfit`), KHÔNG vào %OOS (dùng `note`), KHÔNG vào verdict.
> ⇒ **Sửa công thức `finalFitness` chỉ đổi genome nào được chọn, tuyệt đối không đổi
> cách đo/pass-criteria.** Đây là đòn bẩy an toàn duy nhất để "ưu tiên nhiều lệnh".

## 2. So sánh CHI TIẾT: V1 vs V3 vs V4.1

### 2a. Số lệnh / tần suất

| | V1 | V3 | V4.1 |
|---|---|---|---|
| Sàn min-trade | `max(5, windowDays·0.33)`, `windowDays` suy từ **span lệnh** | như V1 (span lệnh) | `max(5, windowDaysActual·0.33)`, `windowDays` = **range backtest THẬT** (caller truyền) |
| Dưới sàn (`TOO_FEW`) | **RAMP mềm**: `-5000 + tradeCount·(5000/minReq)` → tăng dần về 0 khi tiến sát sàn | y hệt V1 | **CLIFF cứng**: `REJECT_BASE + tradeCount` (≈ −100000, +tradeCount vô nghĩa so với thang) |
| Thưởng tần suất khi ĐÃ pass | **CÓ**: `+ tradeCount·0.1` (tie-break, gradient dương thật) | **CÓ**: `+ tradeCount·0.1` | **KHÔNG có gì** |
| Bản chất hàm mục tiêu (nhánh SUCCESS) | `netScore − DDpenalty·1.5 + count·0.1` = **PnL tuyệt đối** − phạt | `netScore − DDpenalty(vùng) + count·0.1` = **PnL tuyệt đối** − phạt | `calmar = netPnl/DD` = **TỈ SỐ** |

### 2b. Phạt sentinel (TOO_FEW / ZERO / CAPITAL_LOCK)

| Sentinel | V1 | V3 | V4.1 |
|---|---|---|---|
| `ZERO_TRADES` | `-10000` (đáy) | `-10000` | `REJECT_BASE` (−100000) |
| `TOO_FEW_TRADES` | ramp `[-5000 .. ~0)` theo tradeCount | ramp như V1 | `REJECT_BASE + tradeCount` (≈ phẳng, gradient ~0.1% thang) |
| `TOO_MUCH_CAPITAL_LOCK` | phạt phí giam-vốn `margin·hours·0.0002` **trừ dần vào netScore** (không loại) | phạt log giam-vốn có trần 2.5% (không loại) | **HARD REJECT**: `REJECT_BASE − pctHeldOver7d·100` (loại thẳng) |
| `BURN/EATEN` | mềm | mềm | hard reject |

### 2c. Thành phần fitness

| Thành phần | V1 | V3 | V4.1 |
|---|---|---|---|
| PnL | netScore tuyệt đối (vào fitness) | netScore tuyệt đối | chỉ vào qua tử số Calmar |
| Calmar | có (report) nhưng fitness = netScore − DDpen | không (fitness = netScore − DDpen vùng) | **MỤC TIÊU DUY NHẤT** khi pass |
| DD | penalty tuyến tính ·1.5 | penalty theo vùng 15/30/40% + killswitch | **constraint cứng** `MAX_DD_PCT=0.65` |
| held>7d | không tách | phạt log giam-vốn | **constraint cứng** `MAX_PCT_HELD_OVER_7D=0.02` |
| posYear | không | không | constraint cứng `≥0.80` (chỉ khi ≥2 năm) |
| Sortino | không | không | tính, **report-only** (không vào fitness) |
| **tradeCount bonus** | **+count·0.1** | **+count·0.1** | **KHÔNG** |

## 3. CHẨN ĐOÁN GAP — chính xác vì sao V4.1 không thưởng đủ cho nhiều lệnh

**Nguyên nhân #1 — Mục tiêu là TỈ SỐ, không phải lượng.**
Nhánh SUCCESS của V4.1: `finalFitness = calmar = netPnl / maxDD`. Calmar là **đại lượng
scale-free** ⇒ **bất biến với số lệnh**. Genome vào 20 lệnh chất-lượng-cao (calmar 2.0) luôn
thắng genome vào 120 lệnh calmar 1.8 — dù cái sau bền vững hơn nhiều khi sang OOS. HPO do đó
tự chọn genome **ít lệnh / gần mép sàn min-trade**. Sang OOS (regime khác, tần suất tụt) → rơi
xuống dưới sàn 29 lệnh (OOS 3 tháng) → `TOO_FEW_TRADES` → không được đếm SUCCESS.
V1/V3 ngược lại: fitness = **PnL tuyệt đối** (+ `count·0.1`) — cả hai số hạng đều **tăng theo
số lệnh** ⇒ HPO ưu tiên genome giao dịch nhiều. Đây là khác biệt gốc rễ.

**Nguyên nhân #2 — Sàn min-trade là VÁCH CLIFF, không có gradient leo ra.**
`TOO_FEW`: `finalFitness = REJECT_BASE + tradeCount`. Với REJECT_BASE=−100000, phần `+tradeCount`
(tối đa ~120) là nhiễu ~0.1% thang điểm ⇒ với random-search, **mọi** genome ít-lệnh nhìn như
"cùng một đáy phẳng". Không có gradient để HPO ưu tiên genome 25 lệnh hơn genome 3 lệnh.
V1/V3 ramp `-5000·(1 − tradeCount/minReq)` phủ đủ dải ⇒ tạo gradient thật để leo về phía sàn.

**Nguyên nhân #3 — Chọn genome sát mép sàn ⇒ không có biên an toàn cho OOS.**
Vì mục tiêu (calmar) không thưởng vượt sàn, best-IS thường nằm **ngay trên sàn TRAIN** (365 ngày →
sàn 120 lệnh). Genome vừa đủ 120 trên TRAIN, sang OOS 90 ngày (sàn 29) chỉ cần tần suất giảm nhẹ là
tụt < 29 → sentinel. Thiếu "biên tần suất" chính là cơ chế biến IS-đẹp thành OOS-sentinel.

**Không phải nguyên nhân:** cách đếm %OOS/WFE/verdict (đúng chuẩn pre-registered) và fix reorder
V4.1 (số thật ở nhánh sentinel) — các thứ này lành mạnh, giữ nguyên.

## 4. ĐỀ XUẤT SỬA — V4.2 (diff cho `HPOFitnessCalculatorV4.java`)

Nguyên tắc: **chỉ đổi `finalFitness` (đòn bẩy TRAIN-selection)**; giữ nguyên định nghĩa `note`,
`totalProfit`, `calmar` (report), và mọi sàn constraint rủi ro (DD/held/posYear/burn). Vì `note`
và `totalProfit` không đổi ⇒ %OOS, WFE, verdict **byte-identical** cho cùng genome+data. Chỉ khác:
HPO nay chọn genome **giao dịch nhiều + có biên tần suất** → giảm xác suất OOS rơi TOO_FEW.

**KHÔNG hạ sàn min-trade OOS** (nếu hạ, window 6 lệnh sẽ thành SUCCESS = gaming pass-criteria). Giữ
nguyên `minTrades`. Chỉ (a) làm mềm `TOO_FEW` thành ramp tỉ lệ để có gradient TRAIN, và (b) thêm
hệ số thưởng-tần-suất nhân vào Calmar ở nhánh SUCCESS để đẩy lựa chọn ra khỏi mép vách.

### 4a. Thêm hằng static (khối "NGƯỠNG CONSTRAINT")

```diff
     public static int MIN_YEARS_FOR_RATIO = 2;         // chỉ áp %năm-dương khi backtest ≥2 năm
     public static long HELD_TOO_LONG = 7L * Utils.TIME_DAY;
+
+    // ===== V4.2 (TASK-3a) — THƯỞNG TẦN-SUẤT-LỆNH (chỉ tác động TRAIN-selection) =====
+    // Lý do: Calmar là TỈ SỐ (bất biến số lệnh) → HPO chọn genome ít-lệnh sát mép sàn →
+    // OOS regime khác thì tụt < sàn → TOO_FEW. Các hằng này CHỈ đổi finalFitness (genome
+    // nào được chọn), KHÔNG đổi note/totalProfit/calmar → %OOS, WFE, verdict pre-registered
+    // GIỮ NGUYÊN NGỮ NGHĨA. Chỉnh tập trung tại đây; đặt =off bằng FREQ_TARGET_MULT<=0.
+    public static float FREQ_TARGET_MULT = 2.0f;  // mốc "đủ biên" = 2× sàn min-trade
+    public static float FREQ_FLOOR       = 0.5f;  // genome ngay sàn → còn 0.5×calmar (0..1)
```

### 4b. Nhánh `TOO_FEW_TRADES` — cliff → ramp tỉ lệ (mượn V1)

```diff
-        if (r.tradeCount < minTrades) {
-            r.finalFitness = REJECT_BASE + r.tradeCount; r.note = "TOO_FEW_TRADES"; return r;
-        }
+        if (r.tradeCount < minTrades) {
+            // V4.2: ramp tỉ lệ (mượn V1) — tạo GRADIENT để random-search leo RA khỏi vùng ít-lệnh.
+            // Vẫn < 0 tuyệt đối (SUCCESS luôn > 0) → không bao giờ vượt 1 window SUCCESS.
+            // 0 lệnh → REJECT_BASE; sát sàn → tiến về 0⁻. note GIỮ NGUYÊN → %OOS không đổi ngữ nghĩa.
+            r.finalFitness = REJECT_BASE * (1f - (float) r.tradeCount / minTrades);
+            r.note = "TOO_FEW_TRADES"; return r;
+        }
```

### 4c. Nhánh SUCCESS — Calmar thuần → Calmar × thưởng-tần-suất

```diff
-        // ===== QUA HẾT CONSTRAINT → fitness = Calmar thuần (1 số sạch) =====
-        r.finalFitness = r.calmar;
-        r.note = "SUCCESS";
-        return r;
+        // ===== QUA HẾT CONSTRAINT → mục tiêu = Calmar × thưởng-tần-suất (V4.2) =====
+        // r.calmar (report/oosCalmar) GIỮ NGUYÊN Calmar thuần — KHÔNG bị nhân.
+        // finalFitness (điểm CHỌN genome) = calmar × factor; factor ramp 0.5..1.0, bão hòa tại
+        // FREQ_TARGET_MULT × sàn. Genome trade nhiều (có biên) được ưu tiên → chống OOS TOO_FEW.
+        // Bất biến ordering: SUCCESS = calmar×[0.5..1] > 0 > mọi reject → không đảo bậc.
+        float factor = 1f;
+        if (FREQ_TARGET_MULT > 0f) {
+            float freqTarget = Math.max(1f, minTrades * FREQ_TARGET_MULT);
+            float freqFactor = Math.min(1f, r.tradeCount / freqTarget);   // 0..1
+            factor = FREQ_FLOOR + (1f - FREQ_FLOOR) * freqFactor;
+        }
+        r.finalFitness = r.calmar * factor;
+        r.note = "SUCCESS";
+        return r;
```

### 4d. Vì sao KHÔNG phá pass-criteria (chứng minh)

1. `note` không đổi ở mọi nhánh (SUCCESS vẫn SUCCESS, TOO_FEW vẫn TOO_FEW) → `posCount`
   (`SUCCESS && oosPnl>0`) tính y hệt cho bất kỳ genome+data.
2. `totalProfit`, `calmar` (report) không bị đụng → `WFE = oosPnl/isPnl` và cột `oosCalmar` nguyên.
3. Sàn constraint rủi ro (DD 0.65 / held 0.02 / posYear 0.80 / burn / **sàn min-trade**) giữ nguyên
   → không có window nào "được cứu" nhờ nới ngưỡng.
4. Thay đổi duy nhất: `finalFitness` → best-IS genome khác đi. Đó đúng là mục tiêu: chọn genome
   giao dịch nhiều/bền hơn. Nếu genome đó THẬT SỰ tốt hơn ở OOS → %OOS tăng hợp lệ; nếu không →
   verdict vẫn FAIL trung thực. Không có đường nào "ăn gian" điểm.

### 4e. Ảnh hưởng tới GATE tầng 1 (`TestFitnessV41`) — CẦN cập nhật kỳ vọng

- **caseA** (60 lệnh, window 90 → sàn 29, freqTarget=58, 60≥58 → factor=1.0): `finalFitness = calmar`
  ⇒ **vẫn PASS y nguyên** (may mắn 60 > 2×29=58). Không cần sửa.
- **caseB** (8 lệnh, sàn 29): kỳ vọng cũ `-99992` **SẼ FAIL** vì ramp mới cho
  `REJECT_BASE·(1 − 8/29) = -72413.8`. → phải đổi expected của caseB thành công thức ramp mới.
- **caseC** (10 lệnh) chỉ assert `note==TOO_FEW_TRADES` → vẫn PASS.
- **caseD** (BURN) không đụng nhánh SUCCESS/TOO_FEW → PASS.
- **caseE** (CAPITAL_LOCK) không đụng → PASS.

> Master cần cập nhật `TestFitnessV41.caseB` (expected fitness) trước khi merge. Đây là chỉ báo
> tốt (test đang khoá đúng hành vi cliff cũ).

## 5. KẾ HOẠCH VALIDATE (đo trước/sau, chống overfit)

**B0 — Gate hàm thuần (không cần Aerospike):**
- Chạy `TestFitnessV41` (đã cập nhật caseB) → 5/5 PASS.
- Chạy `StrategyWfoTaskMetricTest` → xác nhận `collectSuccessWfe` / `median` KHÔNG đổi (ta không
  đụng aggregate) → bảo chứng ngữ nghĩa đếm còn nguyên.

**B1 — WFO A/B cùng cấu hình, chỉ khác objective:**
- Chạy `WFORunner` (hoặc `StrategyWfoTask` qua framework) cho **cả ret2 & maxfav3**, cùng
  `WFO_N_SAMPLES=30`, `WFO_SEED_BASE=42`, cùng window (16 quý), cùng `WFO_MAX_OOS_DATE`.
- BEFORE = V4.1 hiện tại; AFTER = V4.2 (patch trên). So từng model:

| Chỉ số | Nguồn | Kỳ vọng AFTER |
|---|---|---|
| # `TOO_FEW_TRADES` OOS | cột `oosNote` bảng window | GIẢM |
| # `ZERO_TRADES` OOS | `oosNote` | GIẢM hoặc bằng |
| # `TOO_MUCH_CAPITAL_LOCK` | `oosNote` | không tăng |
| `%OOS dương` (posRatio) | verdict block | TĂNG (mục tiêu tiến ≥70%) |
| `WFE median` | verdict block | ≥ 0.5, không sụp |
| `worstDdPct` | verdict block | ≤ 0.50, không xấu đi |
| `oosTrades` trung vị | cột `trades` | TĂNG, có biên trên sàn 29 |

**B2 — Chống overfit / gaming:**
- Kiểm tra mọi window mới thành SUCCESS đều có `oosTrades ≥` sàn OOS (29 ở window 90d) — xác nhận
  KHÔNG do hạ sàn (ta không hạ) mà do genome thật sự trade nhiều hơn.
- Cảnh báo đỏ: nếu `oosTrades` tăng nhưng `WFE median` tụt < 0.5 hoặc `worstDdPct` vượt 0.50 →
  freq-reward đang kéo genome sang "trade nhiều nhưng chất lượng kém" → chỉnh `FREQ_FLOOR` cao lên
  (0.6–0.7) hoặc `FREQ_TARGET_MULT` xuống (1.5) để bớt nhấn tần suất.

**B3 — Robustness (nhiễu lựa chọn & độ nhạy hằng):**
- Multi-seed: chạy lại B1 với `WFO_SEED_BASE ∈ {42, 7, 123}` → posRatio/WFE median không được
  dao động mạnh (nếu dao động → cải thiện chỉ là may rủi seed, không phải tín hiệu).
- Ablation hằng: sweep `FREQ_TARGET_MULT ∈ {1.5, 2.0, 3.0}` × `FREQ_FLOOR ∈ {0.3, 0.5, 0.7}`
  (mỗi lần chỉ đổi static, không đổi code) → chọn cấu hình cho posRatio cao nhất mà WFE median
  vẫn ≥ 0.5 và worstDdPct ≤ 0.50. Ưu tiên cấu hình ổn định giữa các seed hơn là cực đại 1 seed.
- Đặt `FREQ_TARGET_MULT=0` = **tắt hoàn toàn** freq-reward (nhánh SUCCESS trở lại calmar thuần,
  nhánh TOO_FEW vẫn ramp) → dùng làm baseline kiểm soát để tách riêng đóng góp của 4c vs 4b.

**Tiêu chí kết luận:** V4.2 được coi là cải thiện nếu — với ÍT NHẤT maxfav3 — số window sentinel
(TOO_FEW+ZERO+CAPITAL_LOCK) giảm rõ, posRatio tăng về phía 70%, đồng thời WFE median ≥ 0.5 và
worstDdPct ≤ 50% (không đánh đổi rủi ro). Nếu tần suất tăng mà WFE/DD xấu đi → giữ V4.1, chỉnh hằng.

## 6. Tóm tắt đề xuất (1 dòng)

Khôi phục "ưu tiên nhiều lệnh" kiểu V1 vào V4.1 **chỉ qua `finalFitness`** (TRAIN-selection):
(a) `TOO_FEW` cliff → ramp tỉ lệ; (b) SUCCESS `calmar` → `calmar × freqFactor` (0.5..1.0, bão hòa
tại 2× sàn). Không đụng `note`/`totalProfit`/`calmar-report`/sàn rủi ro ⇒ %OOS, WFE, verdict
pre-registered giữ nguyên ngữ nghĩa; chỉ genome được chọn thay đổi theo hướng trade-nhiều-có-biên.
