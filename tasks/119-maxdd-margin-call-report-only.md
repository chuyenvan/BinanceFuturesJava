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

## Kết quả
<CCD điền>
