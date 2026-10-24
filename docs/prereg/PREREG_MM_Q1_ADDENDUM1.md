# PREREG MM_Q1 — ADDENDUM 1 (sửa bug phát hiện SAU khi thấy kết quả lần chạy 1)

Lần chạy 1 (prereg e2766839) đã cho kết quả: mọi tier/kỳ/cấu hình mean net < 0, CI cận trên < 0 (NO-GO). Validation phát hiện 2 lỗi dữ liệu + 1 điểm xử lý chưa định nghĩa; sửa và chạy lại TOÀN BỘ (giữ nguyên mọi tham số, seed, tiêu chí). Báo cả số trước/sau.

## Bug 1 — trade "NA" giá 0, qty 0
- V5 trượt nặng ở tier lớn (AS0 trung bình −100…−680 bps/giờ). Truy: file trades có hàng `order_type = NA`, price = "0", quantity = "0" (vd SOLUSDT 2026-06-17 03:00: 547/37 588 hàng). Hàng is_buyer_maker = true với giá 0 thoả "giá < giá quote" ⇒ fill BID GIẢ (không có adverse selection ⇒ thiên lệch markout LÊN). Cũng làm sai V1 (lệnh mua giá 0) và V5.
- Sửa: bỏ mọi trade có price = 0 hoặc quantity = 0 trước mọi bước (fill, V1, V5, r_1h); đếm theo symbol-giờ: số trade bị bỏ, số trade NA, số NA có giá ≠ 0.

## Bug 2 — r_1h từ kline cryptohftdata không phải nến đóng
- V2b trượt: 649/720 giờ D lệch kline Oracle (max 0,45 %). Nguyên nhân: file kline cryptohftdata lưu MỘT bản tin/phút, thường nhận ~0,4–1 s sau khi nến MỞ (vd bar 12:00 nhận 12:00:00.437) ⇒ "close" là giá đầu phút, không phải close nến ⇒ r_1h thực chất ≈ 59 phút.
- Sửa: r(H) = giá trade hợp lệ cuối / giá trade hợp lệ đầu trong [H, H+1h) − 1 (sắp theo trade_time, trade_id; dedupe trade_id; bỏ trade giá/qty 0) — đúng bằng close/open của nến 1h. Áp cho BTC và symbol, cả hai kỳ. Thiếu file trades (hoặc < 2 trade hợp lệ) ⇒ loại như cũ. V2b mới: so r này với kline Oracle (D) |Δ| < 1e-9.
- Hệ quả: tập giờ nhận có thể đổi (quy trình chọn giữ nguyên: cùng thứ tự ứng viên seed 202507/202601).

## Điểm 3 — hàng orderbook không phải `update` (snapshot) xuất hiện từ 2026-04
- Lần 1: 3 808 hàng non-update, hầu hết ở giờ đã bị loại do đứt pu; 2 giờ được nhận (NEIRO, NEO 2026-07-24 07:00) có hàng snapshot nhưng pu liên tục. Prereg không định nghĩa cách xử lý snapshot.
- Quy ước: symbol-giờ có BẤT KỲ hàng event_type ≠ update ⇒ loại ("rej_snapshot", tương đương đứt luồng diff), lấy ứng viên kế.

## Không đổi
Thứ tự ứng viên, điều kiện yên (ngưỡng), loại đợt MKT, mô phỏng fill, L, h, phí, bootstrap (seed 7), tiêu chí §8, nhãn GO/ỨNG VIÊN/NO-GO. Lần chạy 1 lưu ở `mm_wk/res` (số trước), lần 2 ở `mm_wk/res2`.
