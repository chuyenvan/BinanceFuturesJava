# TASK-119: maxDD mark-to-market + sentinel MARGIN_CALL (REPORT-ONLY) — CCD opus

- **status:** doing (giao 2026-07-05 sáng)
- **Bối cảnh:** verdict pre-registered dùng "worst OOS maxDD ≤ 50%". Vế C worst = 44.0% — SÁT ngưỡng — trong khi
  maxDD hiện tại "hiểu nhẹ": tính trên equity chưa phản ánh đầy đủ mark-to-market các vị thế DCA đang mở +
  chưa có khái niệm margin-call. Hệ long-only 1x nhưng martingale nhiều vị thế đồng thời → equity mtm có thể
  âm sâu hơn số đang đo.

## ⛔ HÀNG RÀO
1. **REPORT-ONLY:** TUYỆT ĐỐI không đổi fitness function, verdict logic, hành vi trade, hay bất kỳ số hiện có.
   Chỉ THÊM metric mới chạy song song: `oosMaxDD_mtm` (+ cờ `MARGIN_CALL_HIT` nếu chạm ngưỡng) ghi thêm vào
   report/log. Verdict pre-registered giữ nguyên đọc maxDD cũ. Mọi diff phải chứng minh: nếu tắt metric mới,
   bytecode hành vi cũ không đổi.
2. **Pha 1 — THIẾT KẾ TRƯỚC (ghi vào mục Thiết kế của task này, commit, RỒI MỚI CODE):**
   - Đọc code: equity/maxDD hiện tính ở đâu (BudgetManager*, nơi tính OOS_maxDD trong StrategyWfoTask/engine),
     realized vs unrealized xử lý thế nào, giá mark lấy từ đâu theo bar.
   - Định nghĩa đề xuất: equity_mtm(t) = vốn + realizedPnL(t) + Σ unrealizedPnL vị thế mở (mark = close bar t);
     maxDD_mtm = max drawdown trên chuỗi equity_mtm; MARGIN_CALL nếu equity_mtm(t) ≤ ngưỡng (đề xuất ngưỡng
     và căn cứ Binance cross 1x — ghi rõ giả định, KHÔNG tự chế im lặng).
   - Nêu chi phí hiệu năng (tính mỗi bar × mỗi vị thế mở) + cách giữ rẻ.
3. Gate: mvn package sau mỗi cụm; unit test tối thiểu 1 case tổng hợp (2 vị thế mở, giá rơi, maxDD_mtm > maxDD cũ).
4. Số đo thử: chạy lại 1 window nhỏ (w0 leaked, N=5, local — nice, Xmx ≤6g, KHÔNG đụng Oracle vì export v3 đang chạy;
   chạy máy local nếu đủ RAM, hoặc ghi rõ PENDING chạy khi Oracle rảnh).
5. Kết quả: bảng so maxDD cũ vs maxDD_mtm window thử + commit branch module + marker /d/claudedata/CCD119_DONE.

## Thiết kế (CCD điền pha 1) — CHỐT 2026-07-05, commit TRƯỚC khi code

### A. maxDD hiện tại tính ở đâu (đọc code)
- **Nguồn per-tick:** `SimulatorMarketLevelTicker1MStopLoss.simulatorWithInitEntry()` dòng 141–156.
  Mỗi phút (chỉ khi `activeRunningCount > 0`) tính `unrealAtLow = Σ qty·(bar.minPrice − priceEntry)`
  trên MỌI cụm đang mở = unrealized GỘP danh mục tại đáy nến (bar.low). Gọi
  `BudgetManagerSimple.updateTrueUnrealizedMin(unrealAtLow, time)`.
- **Giữ đáy:** `BudgetManagerSimple.updateTrueUnrealizedMin` (dòng 84–99) theo dõi MIN (âm nhất) của
  chuỗi đó → `trueUnrealizedMin` → ghi thẳng `balanceIndex.unProfitMin` (single source).
- **Vào fitness/verdict:** `HPOFitnessCalculatorV4.evaluateDetailed` (dòng 103–107):
  `maxDrawdown = |unProfitMin|`; `ddPct = maxDrawdown / balanceBasic`. `StrategyWfoTask.aggregate`
  (dòng 268) lấy `worstDdPct = max(oosDdPct)` → so `PASS_MAXDD_OOS = 0.50`. (Vế C worst = 44%.)
- **realized vs unrealized:** realized NET cộng dồn ở `BudgetManagerSimple.profit`
  (`updatePnl` gọi tại `closeOrder` mỗi khi lệnh đóng — LIVE per-tick). `profit` đã trừ fee + slippage
  2 chân + funding (xem `OrderTargetInfoTest.calTp`). `balance = balanceBasic + profit` = equity CHƯA
  gồm unrealized. unrealized per-tick lấy mark = `bar.minPrice` (đáy nến, đây là METRIC nên KHÔNG look-ahead).

**Kết luận cái "hiểu nhẹ":** metric cũ = `|min_t Σ unrealized(t)|`, NEO tại 0 unrealized. Nó BỎ:
(1) realized PnL đã tích luỹ rồi trả lại (đỉnh equity cao hơn vốn khi martingale gom lãi nhỏ liên tục);
(2) khái niệm drawdown-từ-đỉnh; (3) margin-call/cháy tài khoản.

### B. Định nghĩa metric MỚI (report-only, chạy song song)
Tính TẠI CHÍNH vòng lặp per-tick đã có (dòng 145–155), cùng cadence + cùng mark `bar.low` với maxDD cũ
→ khác biệt DUY NHẤT là cộng thêm realized + đo từ đỉnh (cô lập đúng cái cũ bỏ sót):

```
equity_mtm(t)   = balanceBasic + profit(t) + unrealAtLow(t)     // realized NET + unrealized gộp @bar.low
equityPeak(t)   = max_{s<=t} equity_mtm(s)                       // đỉnh chạy
maxDD_mtm(t)    = max_{s<=t} (equityPeak(s) − equity_mtm(s))     // abs USD
maxDD_mtm_pct   = maxDD_mtm / balanceBasic                       // chia VỐN — so trực tiếp với ddPct cũ + verdict 50%
```

**MARGIN_CALL — căn cứ Binance USDⓈ-M cross, giả định GHI RÕ:**
- Binance cross: thanh lý khi `marginBalance < maintenanceMargin`. `marginBalance = walletBalance + Σ uPnL`
  = ĐÚNG `equity_mtm(t)` của ta (walletBalance = vốn + realized). `maintenanceMargin = Σ notional_i·MMR_i − maintAmount_i`.
- **Giả định (proxy v1, KHÔNG tự chế im lặng):** MMR phẳng `MAINT_MARGIN_RATE = 0.005` (0.5%) — xấp xỉ bậc
  MMR thấp nhất của alt trên USDⓈ-M (BTC 0.4%, nhiều alt 0.5–1%); `maintAmount = 0` (bậc thấp nhất).
  notional tính theo MARK tại đáy nến để đồng bộ với equity@low: `notionalAtLow = Σ qty·bar.minPrice`.
- **Cờ:** `MARGIN_CALL_HIT = true` nếu tồn tại tick với `equity_mtm(t) ≤ MAINT_MARGIN_RATE · notionalAtLow(t)`.
  Ghi kèm `minEquityMtm`, `minEquityMtmPct = minEquityMtm/balanceBasic`, `timeMarginCall`.
- Hệ long-only 1x: margin = notional (lev=1) → equity sàn ~0 (khó âm trừ khi DCA vượt vốn); cờ này bắt
  đúng ca martingale chồng vị thế kéo equity sát ngưỡng thanh lý — thứ maxDD cũ (neo 0) không thấy.

### C. Ranh giới report-only (chứng minh bytecode cũ KHÔNG đổi)
- CHỈ THÊM: field mới trong `BudgetManagerSimple` (`equityPeakMtm, maxDDMtm, timeMaxDDMtm, minEquityMtm,
  marginCallHit, timeMarginCall`) + 1 method mới `updateEquityMtm(...)` + 1 biến cộng dồn `notionalAtLow`
  trong vòng lặp đã có + trường JSON/log mới ở report.
- KHÔNG đụng: `unrealAtLow`, `updateTrueUnrealizedMin`, `unProfitMin`, `ddPct`, `finalFitness`, `note`,
  `PASS_MAXDD_OOS`, `worstDdPct`, hành vi tạo/đóng lệnh. Metric mới KHÔNG được đọc bởi bất kỳ nhánh
  quyết định nào. Xoá method mới + accumulator + field ⇒ hành vi cũ y hệt (báo trong diff).
- **Không bump CONFIG_VERSION:** metric report-only, KHÔNG đổi PnL/trade/genome/fee/slippage → cache HPO
  vẫn đúng (luật CORE: chỉ bump khi đổi thứ ảnh hưởng backtest).

### D. Chi phí hiệu năng + cách giữ rẻ
- Thêm/tick: 1 phép nhân-cộng (`notionalAtLow += qty·low`) trong vòng lặp cụm ĐÃ chạy sẵn + 1 call
  vài phép float. Bọc trong `activeRunningCount > 0` đã có ⇒ 0 chi phí khi rảnh vị thế. Overhead ~vài %
  của hook maxDD hiện tại, không thêm vòng lặp/allocation. Không streaming funding (giữ như cũ).

### E. Xấp xỉ đã biết (ghi minh bạch)
- `equityPeak` lấy theo equity@bar.low ⇒ nếu đỉnh equity rơi đúng nến đang có vị thế mở lời, dùng low sẽ
  hạ nhẹ đỉnh ⇒ maxDD_mtm hơi thấp. Bù: đỉnh được chốt CHÍNH XÁC tại tick MỞ lệnh (unrealized≈0 →
  equity = vốn+realized = đỉnh realized thật). Ca bỏ sót là hiếm; v1 chấp nhận, ghi rõ.
- KHÔNG khẳng định maxDD_mtm ≥ maxDD cũ MỌI trường hợp (trough tick có thể lệch). Chỉ khẳng định: trong
  regime martingale-crash (realized trả lại) maxDD_mtm ≥ maxDD cũ — unit test minh hoạ 1 ca cụ thể.

### F. Điểm expose report
- `StrategyWfoTask.backtest()` đọc `BudgetManagerSimple` sau sim → thêm `oosMaxDD_mtm`, `oosDdPct_mtm`,
  `marginCallHit`, `minEquityMtmPct` vào JSON res + log. `aggregate()` thêm CỘT thông tin vào bảng md
  (verdict + worstDdPct GIỮ NGUYÊN đọc ddPct cũ).

## Kết quả (CCD điền pha 2 — 2026-07-05)

### Code (thuần additive, report-only — xoá là về cũ y hệt)
| File | Thay đổi |
|---|---|
| `research/BudgetManagerSimple.java` | +6 field mới (`equityPeakMtm/maxDDMtm/timeMaxDDMtm/minEquityMtm/marginCallHit/timeMarginCall`) + const `MAINT_MARGIN_RATE=0.005` + method `updateEquityMtm(unrealAtLow, notionalAtLow, time)`. KHÔNG đụng `updateTrueUnrealizedMin`/`unProfitMin`. |
| `research/SimulatorMarketLevelTicker1MStopLoss.java` | +1 accumulator `notionalAtLow` trong vòng lặp cụm ĐÃ có + 1 call `updateEquityMtm`. `unrealAtLow`/maxDD cũ không đổi. |
| `hpo/HPOFitnessCalculatorV4.java` | +4 field report vào `FitnessReport` + copy từ BudgetManagerSimple (đặt CẠNH chỗ đọc `unProfitMin`, KHÔNG vào constraint/fitness). |
| `wfo/framework/tasks/StrategyWfoTask.java` | +4 key JSON + log + 4 cột bảng md + dòng tổng hợp. Verdict/`worstDdPct` GIỮ NGUYÊN đọc ddPct cũ. |
| `wfo/WFORunner.java` | +2 cột summary + log (ddPct cũ, ddPct_mtm, marginCall). |
| `ai_ml/validation/MaxDDMtmChecker.java` | MỚI — unit test main() (repo không JUnit). |

**Chứng minh report-only:** không field/nhánh quyết định nào (fitness, note, verdict, hành vi lệnh, `PASS_MAXDD_OOS`,
`worstDdPct`) bị đổi. Metric mới CHỈ được ĐỌC bởi log/JSON/bảng report. Xoá `updateEquityMtm` + accumulator +
field ⇒ bytecode hành vi cũ y hệt. KHÔNG bump CONFIG_VERSION (không đổi PnL/trade/genome/fee/slippage).

### Gate + VERIFY bằng số (in-session)
- `mvn -o package`: OK (fat jar dựng, exit 0).
- `MaxDDMtmChecker` (chạy trên jar, exit 0) — **2/2 PASS**:

| Case | maxDD cũ (\|unProfitMin\|) | maxDD_mtm | marginCall | Kết luận |
|---|---|---|---|---|
| A (2 vị thế mở + giá rơi + realized give-back) | 100 | **300** | no | maxDD_mtm > maxDD cũ (bắt thêm 200 realized bị nuốt) ✅ |
| B (lỗ realized ăn hết vốn, còn vị thế mở) | — | — | **YES** (t=11, minEq=-5) | cờ MARGIN_CALL bật đúng ✅ |

Case A chính là minh hoạ "maxDD cũ hiểu nhẹ": neo tại 0 unrealized nên bỏ lãi realized đã trả lại;
maxDD_mtm đo từ đỉnh equity → sâu hơn.

### Số đo trên window THẬT — **PENDING** (đúng ràng buộc task điểm 4)
- **Lý do hoãn:** `WFORunner` nạp TOÀN BỘ dataset 2021–2026 vào RAM 1 lần (dòng 144–146, KHÔNG smart-cache)
  trước khi chạy bất kỳ window nào → không có "window nhỏ" nhẹ; cần nhiều GB + tải mạng từ Aerospike 226.
  Local hiện chỉ ~7.6GB RAM trống (Xmx≤6g theo task) → biên OOM + job mạng nhiều phút. Theo CORE (không
  spawn job nền mù khi thiếu đo/kết/verify) → KHÔNG chạy mù. Oracle bận export v3 (task cấm đụng).
- **Metric đã VERIFY đúng bằng unit test trên chính code path Simulator dùng** (arithmetic khớp), nên số
  window thật chỉ để quan sát mức thực (vế C 44% cũ → ddPct_mtm bao nhiêu, có dính margin-call không).
- **Lệnh tái lập khi máy rảnh** (leaked w0, N=5, seed 42), chạy trên 226 hoặc local khi đủ RAM:
  ```bash
  java -Xmx6g -cp target/binance-java-sdk-1.2.4-shaded.jar \
       com.binance.chuyennd.ai_ml.wfo.WFORunner 5 0:1 42
  # đọc dòng "[WIN 0] ... | [119] ddPct=..% ddPct_mtm=..% marginCall=.." + bảng SUMMARY
  ```
  (Nếu chạy nền: redirect log ra `/d/claudedata/119_wfo_w0.log`, KHÔNG ghi ổ C.)

### Bảng so maxDD cũ vs maxDD_mtm (điền khi PENDING chạy xong)
| nguồn | maxDD cũ % | maxDD_mtm % | marginCall |
|---|---|---|---|
| unit Case A | 10.0 (100/1000) | 30.0 (300/1000) | no |
| WFO w0 leaked N=5 | _PENDING_ | _PENDING_ | _PENDING_ |
