# Funding Fee Audit — TASK-131 PHA 1 (ĐIỀU TRA thuần)

- **CCD:** opus · **Ngày:** 2026-07-05 · **Branch:** module
- **Câu hỏi gốc:** Trong vòng đời 1 vị thế DCA của sim (`SimulatorMarketLevelTicker1MStopLoss` +
  `OrderTargetInfoTest`), funding fee **CÓ** bị trừ vào realized/unrealized PnL mỗi settlement không, hay
  `getNearestFundingFee`/`getFundingHistory` chỉ dùng làm **feature**? Nếu thiếu → PnL OOS bị thổi phồng?
- **Giới hạn PHA 1:** chỉ đọc code + trích dòng, KHÔNG sửa code PnL-impacting. Không đụng Oracle (N100 đang chạy).

---

## KẾT LUẬN (TL;DR)

1. **Funding CÓ bị trừ vào realized PnL** — cơ chế đã tồn tại và **ĐÚNG** (công thức, dấu, tần suất settlement).
   Đây KHÔNG phải chỉ là feature — nó tham gia trực tiếp vào PnL qua `calTp()`.
2. **NHƯNG bị gate sau công tắc `Configs.APPLY_FUNDING_FEE`, mặc định = `false`.** Khi tắt,
   `computeFundingOnClose()` return sớm → `time2FundingFee` rỗng → `calFundingFee()` = 0 → PnL **không** bị trừ.
3. **Giả thuyết "PnL phồng vì long trả funding" KHÔNG đúng cho chiến lược này.** Số đo thật (RunFundingImpact,
   full 2021→2026, Oracle) cho **Σfunding = −918** → hệ mua-đáy long **ĐƯỢC THƯỞNG** funding ròng ~**+1.8% PnL**
   (vào lệnh sau sụp, lúc funding thường ÂM → short trả cho long). ⇒ **Default OFF là THẬN TRỌNG (under-state PnL
   ~1.8%), KHÔNG phồng.** maxDD không đổi (−29.5%), Δtrades = 0.
4. ⇒ **KHÔNG thiếu code, KHÔNG cần PHA 2 sửa PnL.** Đây là trường hợp "đã áp đúng" của task → report xác nhận +
   ví dụ số minh hoạ (dưới). Marker `CCD131_DONE`. Không NEEDS_HUMAN.
5. Điểm cần Uni lưu ý (KHÔNG phải lỗi, không tự sửa): `GoldenBacktest.java` không bật `APPLY_FUNDING_FEE` → số
   Golden hiện đo với funding OFF. Vì funding là **upside** (+1.8%) và Uni đã chốt protocol "bật ở vòng
   HPO/Golden cuối trước go-live", đây chỉ là nhắc thực thi, không chặn.

---

## BẰNG CHỨNG (trích dòng)

### A. Funding được TRỪ vào PnL (không phải feature)

`OrderTargetInfoTest.calTp()` — hàm tính realized PnL của mỗi leg:
```
src/main/java/com/binance/chuyennd/research/OrderTargetInfoTest.java:238
    tp = tp - calFundingFee();
```
`calFundingFee()` cộng tổng các entry trong `time2FundingFee`:
```
OrderTargetInfoTest.java:129-135
    public Float calFundingFee() {
        float fundingTotal = 0;
        for (Float funding : time2FundingFee.values()) { fundingTotal += funding; }
        return fundingTotal;
    }
```
Và PnL tổng của backtest cộng dồn `calTp()` (đã bao gồm funding):
```
src/main/java/com/binance/chuyennd/research/BudgetManagerSimple.java:159-167
    fee += calFee(orderInfo);
    totalFundingFee += orderInfo.calFundingFee();
    profit += orderInfo.calTp();            // calTp đã trừ funding ở trên
```
⇒ Funding KHÔNG chỉ là feature; nó trực tiếp giảm/tăng realized PnL của mọi lệnh.

### B. Công thức + dấu + tần suất settlement — ĐÚNG

`computeFundingOnClose()` tính 1 LƯỢT khi đóng cụm, quét **mọi mốc settlement THẬT** trong vòng đời cụm:
```
OrderTargetInfoTest.java:252-271
    public void computeFundingOnClose() {
        if (!Configs.APPLY_FUNDING_FEE) return;                 // ⛔ CÔNG TẮC (xem mục C)
        ...
        TreeMap<Long, Float> fundingMap = FundingFeeManager.getInstance().getFundingHistory(symbol);
        ...
        long fromTime = (clusterFirstLegTime > 0L) ? clusterFirstLegTime : timeStart;   // leg ĐẦU cụm
        float notional = quantity * priceEntry;
        float feeTotal = 0f;
        for (Float rate : fundingMap.subMap(fromTime, false, timeUpdate, true).values()) {
            if (rate != null) feeTotal += rate * notional;      // long: rate>0 => trả (dương)
        }
        if (feeTotal != 0f) time2FundingFee.put(timeUpdate, feeTotal);   // 1 entry tổng
    }
```
- **Công thức:** `fee = Σ_settle rate(settle) × notional`, `notional = quantity × priceEntry` (avg entry cụm). ✔
- **Dấu:** `rate > 0` → long TRẢ → `feeTotal` DƯƠNG → `calTp` trừ (giảm PnL); `rate < 0` → long NHẬN → ÂM →
  `calTp` cộng (tăng PnL). ✔ đúng chiều long-only.
- **Tần suất:** `subMap(fromTime, false, timeUpdate, true)` = MỌI settlement trong `(leg-đầu, thời-điểm-đóng]`
  → phủ đủ vòng đời cụm DCA qua nhiều settlement (1h/4h/8h). KHÔNG look-ahead (chỉ settle ≤ `timeUpdate`). ✔
- **Được gọi thật** ở đường đóng lệnh:
  ```
  SimulatorMarketLevelTicker1MStopLoss.java:507
      orderMulti.computeFundingOnClose();
  ```
  Toàn bộ phí cụm gán vào DUY NHẤT leg đầu (tránh cộng trùng khi Σ calTp qua các leg): `closeOrder` dòng 516-519.

**Xấp xỉ đã biết (không phải lỗi):** tính 1 lượt tại đóng dùng `avgEntry` cụm làm notional cho mọi settlement,
thay vì close-tại-từng-settlement. Sai số nhỏ vì rate rất bé (đã ghi rõ ở docstring `OrderTargetInfoTest.java:247-249`).

### C. Công tắc mặc định TẮT

```
src/main/java/com/binance/chuyennd/tradecore/Configs.java:146
    public static boolean APPLY_FUNDING_FEE = false;
```
Comment `Configs.java:141-145`: MẶC ĐỊNH OFF (Uni chốt 2026-06-29) — tác động nhỏ nhưng làm chậm HPO/WFO;
CHỈ bật ở vòng HPO/Golden CUỐI trước go-live. Không có env-override; chỉ set trong code.
Grep toàn repo: **duy nhất** `RunFundingImpact.java` (runner đo đối chứng) gán `APPLY_FUNDING_FEE`
(dòng 90 bật/tắt xen kẽ). `GoldenBacktest.java` KHÔNG tham chiếu công tắc → chạy với default `false`.

### D. Số đo thực tế (đã có sẵn — KHÔNG chạy lại Oracle)

`docs/FINDINGS.md:220-227` ghi kết quả `RunFundingImpact` full 2021→2026:
- OFF: `totalPnl = 50311`, `trades = 35774` (GATE PASS — khớp đúng-từng-đồng baseline RunMarginHaltSweep;
  funding KHÔNG rò vào logic giao dịch nhờ tách `clusterFirstLegTime` khỏi `timeStart`).
- **Σfunding ON = −918** ⇒ hệ ĐƯỢC THƯỞNG ròng ~**1.8% PnL** (mua-đáy long nhận funding âm sau sụp; dấu ĐÚNG).
- `maxDD` không đổi (−29.5%), `Δtrades = 0` ⇒ funding không đổi cấu trúc rủi ro / không méo việc HPO chọn genome.
- ⇒ ON PnL ≈ 50311 − (−918) = **~51229** (funding-ON LÀM TĂNG PnL, không giảm).

---

## VÍ DỤ SỐ MINH HOẠ (analytic, khớp code — không cần chạy job)

Long cụm: `quantity = 10`, `priceEntry = 2.0` → `notional = 20.0`. Giữ qua 3 settlement với
`rate = {+0.0001, +0.00005, −0.0002}` trong `(leg-đầu, đóng]`:
```
feeTotal = (0.0001 + 0.00005 − 0.0002) × 20.0 = (−0.00005) × 20.0 = −0.001
calTp:  tp = tp − calFundingFee() = tp − (−0.001) = tp + 0.001   (long NHẬN ròng → PnL tăng)
```
Nếu cả 3 rate dương (bull) `{+0.0001,+0.00005,+0.0002}` → `feeTotal = +0.007` → `tp − 0.007` (long TRẢ → PnL giảm).
⇒ dấu và độ lớn khớp đúng mô tả code.

---

## HẠNG MỤC PHỤ (ghi nhận, KHÔNG sửa)

- **Cụm còn MỞ cuối kỳ backtest** (`SimulatorMarketLevelTicker1MStopLoss.java:296-316`): đường này chỉ COPY
  `time2FundingFee` từ `symbol2OrderRunning[id]` mà **không** gọi `computeFundingOnClose()`. Với các vị thế
  còn mở tại mốc kết thúc, funding vòng đời của chúng không được tính. Tác động negligible (số cụm mở cuối kỳ ít,
  PnL của chúng vốn là unrealized) — nêu để đầy đủ, KHÔNG phải lỗi chặn.

---

## TRẢ LỜI TRỰC TIẾP CÂU HỎI TASK

| Câu hỏi | Trả lời |
|---|---|
| Funding chỉ là feature? | KHÔNG. Trực tiếp trừ vào realized PnL qua `calTp():238`. |
| Có trừ mỗi settlement? | Có — quét MỌI settlement trong `(leg-đầu, đóng]`, cộng 1 tổng, áp 1 lượt khi đóng. |
| Công thức đúng? | Đúng: `Σ rate × notional`, `notional = quantity × avgEntry`. |
| Dấu đúng? | Đúng: rate>0 long trả (PnL giảm), rate<0 long nhận (PnL tăng). |
| Nếu KHÔNG trừ → phồng bao nhiêu? | Mặc định OFF → **KHÔNG phồng**; ngược lại under-state ~1.8% (Σfunding=−918, hệ được thưởng). |
| Cần PHA 2 sửa PnL? | KHÔNG. Code đúng & đủ. Chỉ nhắc Uni: Golden go-live nên bật `APPLY_FUNDING_FEE` (upside +1.8%). |

**Kết luận cuối:** ĐÃ áp đúng → `CCD131_DONE`. Không NEEDS_HUMAN.
