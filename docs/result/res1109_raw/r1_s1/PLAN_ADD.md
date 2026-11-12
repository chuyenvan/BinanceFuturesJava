

## 5. Cập nhật 2026-11-10 (sau T1/T2, MASTER quyết)

### 5.1 T2b bỏ
Không làm lại harness `parity_v12` cho ngày DEV, vì 3 lý do:
1. OFF-NEW2/OFF-BT phụ thuộc dữ liệu ngày live: `pull242/<D>` (log, dump, buffer gate) và exchangeInfo PIT. Ngày DEV 2022–2025 không có các dữ liệu này. Dùng fixture 2026-10-27 thì thiếu các coin đã delist, nên universe sai.
2. R5 (ngày sập 2026-10-30, Vision, cả ngày) đã PASS 100 %: `rows_bit_nonfund_gate = 1.0`, `rows_tol_nonfund_fund = 1.0`, kể cả bản `pit1104`.
3. T2a (exit, toàn bộ DEV 1 seed), T2c (size/DCA) và watcher T3 hằng ngày trên r4u3 đã đủ cho mục đích go-live.

### 5.2 D11 thành cổng micro G-EXIT (đo, chưa sửa)
T2a cho thấy giá thoát trailing của live thấp hơn sổ giấy/sim trung bình **0,40 %** (2 259 lần thoát, seed a1). Ba nguồn gây lệch:

1. **Sim/sổ giấy khớp đúng tại SL.** Xem `ShadowBookC3.java:440` (`closeAt(c, c.priceSL, REASON_TRAILING, now)`); sim tương tự.
2. **Stop trên sàn làm tròn xuống theo tick.**
   - `TrailingStopManager.java:269` gọi `SymbolRules.roundStopPriceForLong`.
   - Hàm đó ở `SymbolRules.java:177-178` dùng `RoundingMode.FLOOR` theo `tickSize` thật của symbol, nên stop thấp hơn SL tối đa 1 tick.
   - Trong replay, tick lấy theo fixture `ExitReplayDevMain.tickFor` (`ExitReplayDevMain.java:45-47`) = 10^(⌊log10 giá⌋ − 4), tức 4 chữ số có nghĩa: 0,01–0,1 % giá. Mức này chưa xác minh với sàn.
3. **Ngưỡng dời stop.**
   - Stop chỉ được dời khi giá mới ≥ giá cũ + 1 tick **và** ≥ giá cũ × 1,001 (`TrailingStopManager.java:276-280`, `DEFAULT_MIN_MOVE_FRAC = 0.001` ở dòng 55).
   - Vì vậy stop có thể trễ sau SL logic tới khoảng 0,1 %.
4. **Khớp sau khi kích hoạt (thuộc replay).** Mock kích stop khi close ≤ stopPrice rồi khớp tại **close của phút đó** (`MockExchangeGateway.java:260, 271`), không khớp tại stop. Đây là cận bi quan.
   - Trên sàn, stop dùng MARK_PRICE (`TrailingStopManager.java:40`), kích trong phút rồi khớp market, nên trượt thật nằm trong khoảng từ 0 đến phần này.

**Việc của G-EXIT ở micro:** với mỗi lần thoát trailing thật, đo các thành phần sau:
- (giá khớp thật − SL logic)/SL;
- tách phần do tick, phần do min-move, phần do gap/trượt.

Từ đó so với 0,40 % (cận bi quan của replay). Nếu lệch thật ≥ 0,2 % thì xem xét giảm `minMoveFrac` hoặc mô hình hoá chi phí thoát trong B0'.
