# RECON — Admission/Budget/Throttle/Sizing hiện tại (A-recon, đọc code, 0 sim)

> **Tài liệu ĐỌC CODE, KHÔNG phải thí nghiệm.** Không pre-reg, không sửa file, không chạy sim/build.
> Mục đích: trả lời TASK A-recon (`tasks/TASKS_2026-09-20b_bet_structure_and_closeout.md` §3) —
> biết chính xác "gate fix cứng hiện tại" điều tiết vào lệnh thế nào, để MASTER thiết kế pacing và
> tìm điểm cắm an toàn giữ cổng OFF byte-identical (`printDone.csv` md5 `efb793e2468ca3a7318da0f0ad23d4fc`).

Nguồn đọc: branch `module` @ `38691b6` (sạch, không dirty lúc đọc — có vài file untracked không
liên quan, xem project memory). File chính: `EntryGate.java`, `TradeUtils.java`,
`BudgetManagerSimple.java`, `VolTargetSizing.java`, `Configs.java`,
`SimulatorMarketLevelTicker1MStopLoss.java` (hàm `createOrder`, dòng ~1198–1460). Đã đọc thêm 3 tài
liệu descriptive có sẵn (không chạy sim mới, dùng lại số đã đo): `docs/diag/DIAG_BIGDOWN_CONCENTRATION.md`,
`docs/diag/DIAG_DCA_CONCURRENCY.md`, `docs/result/RESULT_CONCENTRATION_SAFETYCAP.md` — ba tài liệu này đã đo
đúng câu hỏi Uni hỏi (nhồi ồ ạt / cap vốn) trên dữ liệu thật 2021–2025, nên số ở đây có thể trích
dẫn thẳng thay vì đoán.

---

## 1. Luồng admission một tín hiệu BUY — candidate → admitted

### 1.1 Ba nguồn candidate (mỗi tick 1 phút)

| Nguồn | Sinh ra khi | Chọn bao nhiêu | Đi qua `EntryGate`? |
|---|---|---|---|
| **BIG_DOWN** (market-signal bắt-đáy) | `MarketBigChangeDetector.getMarketStatus1M(...) == BIG_DOWN` | `BdSelection.select(numberOrder,...)` — `numberOrder = NUMBER_ENTRY_EACH_SIGNAL = 2` (per-tick, per-signal) | **KHÔNG** — `createOrder`: `if (!levelChange.equals(BIG_DOWN)) { ...aiRejectFilter.entryGate... }` — nhánh BIG_DOWN nhảy thẳng qua |
| **DCA-grid** (nhồi thêm leg vào cụm đã mở) | `DcaUtils.shouldDcaGrid`: giá rớt ≤ −50%/−75%/−90% so `firstEntryPrice` | `DcaProcessor.getDCA` — **KHÔNG giới hạn**, `stream().filter().collect()` trên toàn bộ vị thế đang mở, vòng lặp tiêu thụ không `break`/`limit` | CÓ (nhánh `!BIG_DOWN`), nhưng gọi với `symbolPred=null` → `EntryGate.threshold()`: `if (symbolPred==null) return thrBase` — chỉ nhận ngưỡng CƠ SỞ, **không** ăn `GATE_DYN_SCALE` |
| **PREDICT_SYMBOL_TRADE** (selector funding) | mọi tick có `symbol2Pred` | `selectCands()` → top-K theo `SELECTOR_RANK_TOPK=8`, loại coin đang chạy | CÓ, với `symbolPred` thật → ăn đủ ngưỡng động × `GATE_DYN_SCALE` (T170=1.70) |

### 1.2 Chuỗi cổng trong `createOrder(...)` (thứ tự thực thi, mỗi cổng có thể `return` = từ chối)

1. `predict == null` → reject (parity với LIVE).
2. **[EntryGate]** — chỉ nhánh không-BIG_DOWN: `aiRejectFilter.entryGate(predict, symbolPred, ...)` dùng công thức `EntryGate.threshold()` = `thrBase × max(DYN_MIN, (symbolPred/SCORE_BASE)×DYN_MULT) × gateScale` (`gateScale` = `GATE_DYN_SCALE` hoặc `CURRENT_REGIME_SCALE` nếu `GATE_REGIME_ADAPTIVE`). REJECT → return.
3. `PumpDumpFilter.shouldSkip` (D3D4, mặc định OFF) → return nếu skip.
4. `GATE_COUNT_ONLY` (đo-only, mặc định OFF) → return sớm, không tạo lệnh.
5. `TIER_3_SHITCOIN` + `DCA_LEVEL1` → chặn DCA cho coin rác.
6. **[Budget — vốn]** `budget = getBudget()` (= `equity/NUMBER_ORDER_BUDGET`), rồi `TradeUtils.managerBudget(budget, marginRunning, balanceBasic, levelChange)`:
   - `u = marginRunning / equity`; **`u >= U_MAX (0.60) → return null` (chặn HẲN, không phân biệt loại lệnh)**;
   - `throttle = clamp(1 − u/U_MAX, 0,1)` (giảm liên tục, không vách);
   - `budget = equity × F_BASE × throttle / dcaGridTotalWeight()`.
   `budget == null` → reject.
7. `tierMultiplier` (CoinRankManager; T170 dùng `TIER_FLAT=1` → luôn 1.00).
8. **[Điểm cắm VolTargetSizing]** — `if (VolTargetSizing.ACTIVE) budget *= VolTargetSizing.multiplier(...)`. Mặc định `SIZE_VOL_TARGET_MODE=OFF` → `ACTIVE=false` → nhánh này không compile-chạy → byte-identical.
9. **[DCA-grid sizing]** nếu `DCA_GRID_ENABLED`: `budget *= DcaUtils.gridLegWeightRatio(legIdx)` = `w[legIdx] × DCA_GRID_SCALE` (khi `FIX_B2=true`, không chia lại). Hết bậc grid → reject.
10. `BdSizeAdapt` (mặc định OFF) — nhân thêm cho riêng leg BIG_DOWN theo severity.
11. `quantity = calQuantityTest(budget, leverage, entry, symbol)`.
12. **[CONC_CAP_AGG_DCA_ENABLED, mặc định FALSE]** — trần AGGREGATE margin trong các leg DCA-grid bậc≥1 (toàn bộ coin) ≤ 45% equity → reject leg nếu vượt.
13. **[CONC_CAP_PERCOIN_ENABLED, mặc định FALSE]** — trần margin MỘT coin (entry + mọi leg DCA) ≤ 15% equity → reject leg nếu vượt.
14. **[CONC_CAP_BD_RATE_ENABLED, mặc định FALSE]** — trần số leg BIG_DOWN mở trong 60 phút gần nhất (rolling, theo thời gian sim) ≤ `CONC_CAP_BD_PER_HOUR=75` → reject leg BIG_DOWN nếu vượt.
15. Tạo `OrderTargetInfoTest`, `marginRunning += order.calMargin()`.

**Sơ đồ rút gọn:**
```
candidate (BIG_DOWN top-2 | DCA-grid không-trần | selector top-8)
   -> [EntryGate: chỉ non-BIG_DOWN, DCA ăn ngưỡng cơ sở] -> [PumpDump OFF] -> [budget/U_MAX throttle]
   -> [tierMult] -> [VolTargetSizing: OFF mặc định] -> [DCA_GRID_SCALE] -> [BdSizeAdapt: OFF]
   -> quantity -> [CONC_CAP_AGG_DCA: OFF] -> [CONC_CAP_PERCOIN: OFF] -> [CONC_CAP_BD_RATE: OFF]
   -> ADMITTED
```

---

## 2. Có cap vốn triển khai không?

**CÓ MỘT — `U_MAX=0.60`** (`TradeUtils.managerBudget`): trần **tổng margin/equity** (không phân biệt
loại lệnh), throttle liên tục từ 0, chặn cứng ở 60%. Đây là cap portfolio-level DUY NHẤT luôn bật
(không cờ, không thể tắt qua profile ngoài đổi `SIM_U_MAX`). Với `LEVERAGE_ORDER=1`, margin=notional
nên đây cũng chính là trần **Σnotional/equity ≤ 60%**.

**Không có cap nào khác luôn bật.** Cụ thể, đã grep toàn bộ `Simulator*/DcaProcessor/Configs/
EntryGate/TradeUtils` theo `MAX_ORDER|MAX_POSITION|MAX_CONCURRENT|MAX_DCA|MAX_RUNNING|
TOTAL_MARGIN|MAX_SYMBOL|BREAKER` (kế thừa từ `DIAG_DCA_CONCURRENCY.md` mục 2) — không có cap số vị
thế đồng thời, không có cap tổng notional nào khác `U_MAX`, circuit-breaker toàn sổ **đã bị xoá**
2026-09-03 (chỉ còn hỗ trợ `SIM_BREAKER_MODE=OFF`).

**Có BA cap khác đã VIẾT SẴN trong code nhưng mặc định TẮT** (không nằm trong `x1_gs_t170.properties`
đang chạy production/T170):
- `CONC_CAP_AGG_DCA_ENABLED` (false) + `CONC_CAP_AGG_DCA_PCT=0.45` — trần aggregate margin trong
  DCA-grid bậc≥1 toàn sổ.
- `CONC_CAP_PERCOIN_ENABLED` (false) + `CONC_CAP_PERCOIN_PCT=0.15` — trần margin MỘT coin.
- `CONC_CAP_BD_RATE_ENABLED` (false) + `CONC_CAP_BD_PER_HOUR=75` — trần số leg BIG_DOWN/giờ (xem §3).

Ba cap này đã được **build, test parity (6/6 md5 khớp khi OFF) và falsification-test (khi bật ở
ngưỡng rất chặt 0.05/5 thì thực sự chặn 111+83 leg và đổi md5)** — xem `RESULT_CONCENTRATION_SAFETYCAP.md`.
Chúng KHÔNG bind ở ngưỡng 0.45/0.15/75 trên toàn bộ lịch sử 2021-2025 vì lịch sử chưa từng chạm tới
(xem số đo dưới).

**Trả lời trực tiếp lo ngại "nhồi hết vốn" của Uni**: đã **một phần** được chặn bởi `U_MAX=0.60`
(mềm, liên tục, không phân biệt BIG_DOWN/DCA/selector) — nhưng đo thực nghiệm cho thấy T170 **chưa
bao giờ** chạm 60% (max quan sát 52.85% margin/equity, 4.5 năm — `DIAG_DCA_CONCURRENCY.md` §3.2);
T100 (gate mở) đã lên tới 57.13%, và có **193 giờ** với margin ≥50% equity (T170 chỉ 1 giờ). Vậy
`U_MAX` là một trần thật nhưng RẤT LỎNG trong vùng gate hiện dùng — nó không phải cơ chế "chống nhồi
theo bigdown" có chủ đích, nó là trần vốn tổng quát tình cờ chưa bị chạm.

---

## 3. Có rate-limit vào lệnh theo thời gian không?

**Gần như KHÔNG — với MỘT ngoại lệ đã viết sẵn nhưng mặc định TẮT.**

- **Selector (PREDICT_SYMBOL_TRADE)**: không cooldown, không giới hạn số lệnh mở/giờ. `SELECTOR_RANK_TOPK=8`
  chỉ giới hạn số ỨNG VIÊN mỗi tick, không giới hạn tích luỹ theo thời gian.
- **DCA-grid**: `DcaUtils.shouldDcaGrid` **không nhận tham số `time`** — không cooldown, không trần
  số leg/tick. Nhánh `shouldDca()` cũ có `isTimeConditionMet()` (`DCA_TIME_BIG_DOWN` phút) nhưng
  **không chạy** khi `DCA_GRID_ENABLED=true` (đúng cấu hình T170).
- **BIG_DOWN**: `NUMBER_ENTRY_EACH_SIGNAL=2` giới hạn CHỈ trong 1 tick (per-signal), không phải
  per-giờ — thị trường có thể phát BIG_DOWN nhiều tick liên tiếp, mỗi tick lại được thêm 2 coin mới
  (miễn coin đó chưa có vị thế). Vì `symbolPred=null` cho BIG_DOWN, `GATE_DYN_SCALE` **không** áp
  dụng — gate 1.70 KHÔNG lọc bớt BIG_DOWN.
- **Ngoại lệ đã có sẵn**: `CONC_CAP_BD_RATE_ENABLED` (mặc định **false**) + `CONC_CAP_BD_PER_HOUR=75`
  — MỘT rolling-window rate-limit thật (60 phút, theo thời gian sim), nhưng **chỉ áp cho leg BIG_DOWN**,
  không áp cho DCA hay selector, và **không bật trong bất kỳ profile production nào hiện tại**.

**Số đo thực tế (đã có sẵn, không chạy sim mới — `DIAG_DCA_CONCURRENCY.md` §6):** kênh "vào ồ ạt"
thật sự KHÔNG phải DCA (chỉ 20 leg DCA/4.5 năm ở T170) mà là **mở cụm mới đồng loạt qua BIG_DOWN**:
max **54 leg BIG_DOWN trong 1 giờ**, **GIỐNG HỆT nhau ở cả 3 gate T170/T130/T100** (vì BIG_DOWN
bypass hoàn toàn `GATE_DYN_SCALE`) — xảy ra đúng 2025-10-11 04:13. Max tổng số cụm mở/giờ (mọi loại)
= 66 (T170), trong đó 54 là BIG_DOWN. Nếu `CONC_CAP_BD_RATE_ENABLED` được bật ở 75 (giá trị hiện có
trong code), ngưỡng này **VẪN KHÔNG bind** ở đỉnh lịch sử 54 — nghĩa là cap hiện có (nếu bật) chưa đủ
chặt để cắt đúng sự kiện 2025-10-11 mà chính DIAG đã ghi nhận là "kênh nhồi ồ ạt thật sự".

⇒ **Xác nhận đúng như brief dự đoán: KHÔNG có rate-limit chung theo thời gian**; có một rate-limit
hẹp (chỉ BIG_DOWN) đã viết sẵn, tắt mặc định, và ở giá trị mặc định 75 chưa chắc đủ chặt cho mục
tiêu chống-nhồi nếu Uni muốn dùng nó làm nền cho pacing.

---

## 4. Sizing quyết theo gì?

**Fixed-fraction-of-equity, với một throttle liên tục theo margin đang dùng (không phải "vốn rảnh"
tường minh nhưng về toán học tương đương)**:

```
margin(bậc i) = equity_now × F_BASE × throttle(u,U_MAX) × tierMultiplier × w[i]/Σw × DCA_GRID_SCALE
                 [× VolTargetSizing.multiplier nếu ACTIVE, mặc định 1.0]
                 [× BdSizeAdapt.mult nếu ACTIVE và BIG_DOWN, mặc định 1.0]
u = marginRunning / equity_now ;  throttle = clamp(1 − u/U_MAX, 0, 1)
```

- `equity_now` = `BudgetManagerSimple.equityNow()` = `balanceCurrent + unProfit` (equity đang chạy,
  compound, cập nhật mỗi giờ — causal, có độ trễ tối đa 1 giờ).
- `SIM_F_BASE` (env override `Configs.F_BASE`, mặc định 0.03 = 3% equity/lệnh gốc) — **không** bị
  T170 override (T170 dùng default 0.03).
- `DCA_GRID_SCALE` (mặc định 1.0, nhưng **T170 profile đặt = 19.5**) — hệ số nhân CẢ THANG lên toàn
  bộ ladder DCA, bù cho việc chia trọng số 1:1:3:8 làm leg đầu quá nhỏ. Đây đúng là "2 đòn size mạnh
  nhất" như GS wave-1 nói: với T170, `F_BASE × DCA_GRID_SCALE / Σw = 0.03 × 19.5 / 13 = 0.045` →
  công thức rút gọn `margin(bậc i) = equity × 4.5% × throttle × w[i]`.
- **Không** có sizing theo "vốn rảnh" TƯỜNG MINH (không có công thức `size ∝ (equity−marginRunning)`
  trực tiếp) — nhưng `throttle = 1 − u/U_MAX` **chính là một dạng thô của điều đó**: budget mỗi lệnh
  mới co lại tuyến tính khi margin-đang-dùng tăng, về 0 tại U_MAX=60%. Đây là **tiền lệ quan trọng**:
  ý tưởng "size theo tỉ lệ vốn đang rảnh" của Uni **đã tồn tại một phần** trong hệ, chỉ chưa được
  làm rõ/regime-aware/tối ưu cho mục tiêu chống-bigdown — MASTER có thể mở rộng đúng công thức này
  thay vì phát minh cơ chế mới từ đầu.
- **Tổng exposure lý thuyết 1 coin nếu nhồi hết ladder**: 58.5% equity (throttle=1, tức sổ đang
  rỗng); có throttle bù dần: 44.1%; kỷ lục thật quan sát: 39.17% equity (T130/AIA 2025-11-07,
  lỗ −12.400 USD) — xem `DIAG_BIGDOWN_CONCENTRATION.md`.

---

## 5. Điểm cắm pacing giữ OFF byte-identical — có hay không, chi phí bao nhiêu

**CÓ HAI điểm cắm an toàn đã có TIỀN LỆ THỰC THI THÀNH CÔNG trong repo — cả hai đều pass cổng md5
`efb793e2` khi OFF.**

### 5.1 Tầng SIZING (rẻ, an toàn) — mẫu `VolTargetSizing`

Điểm cắm: ngay sau `tierMultiplier`, trước nhân `DCA_GRID_SCALE` ratio, trong `createOrder`
(dòng ~1301-1311 `SimulatorMarketLevelTicker1MStopLoss.java`):
```java
budget *= tierMultiplier;
if (VolTargetSizing.ACTIVE) { budget *= VolTargetSizing.multiplier(vtSymbol, currentTs); }
```
`ACTIVE = !"OFF".equals(MODE)`, mặc định `SIZE_VOL_TARGET_MODE=OFF` → nhánh không compile-chạy →
**byte-identical đã verify** (md5 `efb793e2`, TASK5). Một rule pacing (P1 capital-availability hoặc
P3 regime-bigdown) **CẮM ĐƯỢC ở đúng chỗ này**: thêm một multiplier mới (vd `PacingSizing.multiplier(...)`)
gọi ngay cạnh dòng trên, gated bởi một flag mới mặc định OFF (vd `SIZE_PACING_MODE=OFF`), tính theo
`(equity − marginRunning)/equity` (vốn rảnh) hoặc theo cờ bigdown causal đã tính trước tick. **Không
đổi tập lệnh nào được admit** — chỉ đổi KÍCH THƯỚC — nên không có confound "đổi admission → đổi tập
lệnh → không tách được hiệu ứng" mà §0.5 cảnh báo. Đây là chỗ khớp trực tiếp với thiết kế P0 (giảm
size đều) và P3-dạng-size (giảm size khi bigdown) của TASK B §4.2.

### 5.2 Tầng ADMISSION (đắt hơn, nhưng có tiền lệ đã test — KHÁC Phương án B hedge)

Điểm cắm: cuối `createOrder`, SAU khi `quantity` đã tính, TRƯỚC khi construct `OrderTargetInfoTest`
(dòng ~1390-1448) — đúng chỗ 3 guard `CONC_CAP_*` đã cắm:
```java
if (Configs.CONC_CAP_BD_RATE_ENABLED && levelChange == MarketLevelChange.BIG_DOWN) {
    int nBd60m = concBdCountLastHour(ticker.startTime);
    if (nBd60m >= Configs.CONC_CAP_BD_PER_HOUR) { ...; return; }
}
```
Mẫu này đã được **build + test parity (6/6 md5 khớp khi OFF) + falsification test (bật ở ngưỡng
chặt → thực sự chặn leg, đổi md5 đúng như kỳ vọng)** — `RESULT_CONCENTRATION_SAFETYCAP.md`, commit
`5e82983`. Một rule pacing muốn CHẶN/HOÃN candidate (không chỉ giảm size) — ví dụ P2 burst
rate-limit tổng quát hoá (K lệnh/W giờ, mọi loại, không chỉ BIG_DOWN) hoặc P3-dạng-admission (chặn
hẳn khi bigdown + vốn rảnh thấp) — **cắm được ở cùng vị trí này**, theo đúng khuôn: flag mới mặc
định false, đọc qua `Cfg.getOr(..., "false")`, chỉ `return` (skip leg), không sửa logic phía trước.

**Chi phí/rủi ro của 5.2 so với 5.1 và so với Phương án B hedge (đã bị chặn)**:
- **Rẻ hơn Phương án B nhiều**: Phương án B ước tính 647-890 dòng, bắt buộc SỬA `equityNow()`,
  `marginRunning`, và một hàm DÙNG CHUNG với mọi lệnh long (funding sign) — tức sửa **logic tính
  toán lõi** dùng chung cho cả nhánh OFF. Guard `CONC_CAP_*` chỉ THÊM một khối `if` độc lập ở cuối
  hàm, không sửa dòng nào của logic cũ, nên rủi ro phá byte-identical khi OFF thấp hơn hẳn (đã verify
  thực nghiệm, không phải suy đoán).
- **Nhưng vẫn đắt hơn 5.1 về mặt PHƯƠNG PHÁP, không phải về dòng code**: guard admission **đổi tập
  lệnh được chọn** khi BẬT (một số candidate bị `return` thay vì tạo lệnh) → đúng loại confound §0.5
  cảnh báo ("đổi admission → đổi tập lệnh → không tách được hiệu ứng pacing khỏi hiệu ứng đổi-tập-lệnh").
  Vì vậy nếu TASK B dùng đường 5.2 (P2 burst rate-limit, hoặc P3-admission), PREREG phải khai báo rõ
  đây là thay đổi tập lệnh (không chỉ size) và đo riêng phần "mất bao nhiêu lệnh nào, ROI lệnh bị mất"
  — tương tự cách `DIAG_DCA_CONCURRENCY` đã tách BIG_DOWN khỏi DCA để không nhầm kênh.
- Guard `CONC_CAP_BD_PER_HOUR` **hiện chỉ áp cho BIG_DOWN**; mở rộng nó thành rate-limit tổng quát
  (đếm mọi `levelChange`, không riêng BIG_DOWN) là một thay đổi nhỏ (đổi điều kiện `if` bọc ngoài +
  1 rolling window mới) nhưng vẫn nằm trong "thêm nhánh mới, không sửa nhánh cũ" nên vẫn giữ được
  byte-identical khi flag mới OFF.

### 5.3 Kết luận cho g4

**GO — có điểm cắm an toàn.** Ưu tiên đề xuất cho MASTER: bắt đầu bằng **5.1 (sizing multiplier)**
cho P0/P3 — rẻ nhất, không confound tập lệnh, đúng khuôn `VolTargetSizing` đã pass cổng OFF. Chỉ
dùng **5.2 (admission guard)** nếu Uni/MASTER thực sự muốn P2 (burst rate-limit chặn hẳn tín hiệu
yếu hơn) hoặc muốn P3 ở dạng "chặn" thay vì "giảm size" — khi đó phải pre-reg rõ đây là thay đổi tập
lệnh và đo confound riêng, đúng bài học Phương án B (không phải cấm hẳn, mà phải làm có kỷ luật hơn
Phương án B đã làm).

---

## 6. Giới hạn phương pháp

1. Chỉ đọc code trên `module` tại thời điểm đọc (không diff với commit khác, không chạy sim để xác
   nhận số liệu mới — mọi số nhồi/cap trích từ `DIAG_BIGDOWN_CONCENTRATION.md`/`DIAG_DCA_CONCURRENCY.md`/
   `RESULT_CONCENTRATION_SAFETYCAP.md`, đã tự ghi rõ là descriptive, không phải variant).
2. Không kiểm tra đường LIVE (`DetectEntrySignal2TradeNormal`) — theo brief, A-recon chỉ cần luồng
   sim/backtest dùng cho TASK B.
3. `NUMBER_ENTRY_EACH_SIGNAL` và `SELECTOR_RANK_TOPK` là cap CANDIDATE (trước mọi cổng vốn), không
   phải cap admission — không liệt lại ở §2/§3 như cap vốn/rate-limit riêng vì bản chất khác (giới
   hạn nguồn tín hiệu, không giới hạn được-mở-lệnh-hay-không theo vốn/thời gian).
