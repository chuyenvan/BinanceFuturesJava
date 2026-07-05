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

## Thiết kế (CCD điền pha 1)
<CCD điền>

## Kết quả
<CCD điền>
