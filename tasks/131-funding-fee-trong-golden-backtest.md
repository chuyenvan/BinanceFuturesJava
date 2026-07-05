# TASK-131: Kiểm & (nếu thiếu) áp funding fee vào PnL trong WFO/Golden backtest — CCD opus

- **status:** PHA 1 DONE (2026-07-05) — funding ĐÃ áp ĐÚNG vào PnL (`calTp:238`), gate sau `APPLY_FUNDING_FEE`
  (default OFF). Số thật: Σfunding=−918 ⇒ hệ ĐƯỢC THƯỞNG ~1.8% PnL, OFF là THẬN TRỌNG (không phồng). KHÔNG cần
  PHA 2 sửa PnL. Report: `docs/reports/funding_fee_audit.md`. Marker CCD131_DONE.
- **Bối cảnh:** hệ long-only DCA giữ vị thế QUA nhiều settlement funding (1h/4h/8h). Nếu backtest KHÔNG trừ
  funding fee mỗi settlement → PnL OOS bị THỔI PHỒNG (long trả funding khi funding dương, phổ biến ở bull).
  Đây là 1 trong 2 mục "hoàn thiện đo lường trung thực" trước khi lên product. FundingFeeManager đã tồn tại
  + có getNearestFundingFee() + đã được SimulatorMarketLevelTicker1MStopLoss/OrderTargetInfoTest import.

## ⛔ HÀNG RÀO
1. **PHA 1 = ĐIỀU TRA, KHÔNG SỬA CODE.** Trả lời chính xác bằng trích code + số dòng:
   - Trong vòng đời 1 vị thế DCA của sim (SimulatorMarketLevelTicker1MStopLoss + OrderTargetInfoTest), funding fee
     CÓ bị trừ vào realized/unrealized PnL mỗi settlement không? Hay getNearestFundingFee chỉ dùng làm FEATURE?
   - Nếu có trừ: công thức đúng chưa (fee = notional × rate, dấu: long trả khi rate>0), tần suất đúng settlement chưa?
   - Nếu KHÔNG trừ: đó là nguồn phồng PnL — ghi rõ mức độ ảnh hưởng ước lượng (bao nhiêu settlement/trade trung bình).
   - Ghi kết luận PHA 1 vào task + commit TRƯỚC khi đề xuất sửa.
2. **PHA 2 chỉ làm nếu PHA 1 kết luận THIẾU và Uni duyệt hướng** (đánh dấu NEEDS_HUMAN xin duyệt, KHÔNG tự sửa sim
   PnL — đây là code PnL-impacting, thay đổi làm lệch mọi số verdict đã đo). Nếu PHA 1 thấy ĐÃ áp đúng → chỉ cần
   report xác nhận + 1 test số minh hoạ, xong.
3. Không đụng Oracle compute nặng (N100 đang chạy). Đọc code local + nếu cần đo thì 1 window nhỏ trên máy local/226 nice.
4. SLF4J only. Không commit lên branch khác module.

## Output: docs/reports/funding_fee_audit.md (PHA 1) + marker /d/claudedata/CCD131_DONE. NEEDS_HUMAN nếu cần Uni duyệt PHA 2.
