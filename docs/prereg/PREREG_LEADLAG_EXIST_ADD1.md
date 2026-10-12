# PREREG_LEADLAG_EXIST — ADDENDUM 1 (MASTER 2026-10-13, commit TRƯỚC khi chạy H2/H1c)

Bối cảnh: lần chấm 1 (scorer 9e63a754, result 0c49b91d, json md5 ea16fd5c) — H1 đạt luật §4 (k3h4 mean IC 0,01658, CI nở dưới 0,01285, 4/4 năm), V1/V2 PASS; H2 KHÔNG chạy được (ledger legs.pkl + cache kline 1m đã xoá). Kết luận treo.

## A. Nhiễu cơ chế cần loại (MASTER)
Tại mỗi t, r_BTC là hằng cắt ngang ⇒ g⊥_i ∝ (β̂_i/σ_i)·r_BTC(t−k,t]. IC dương có thể chỉ là (sai số β̂ tương quan với β̂/σ) × tự tương quan r_BTC giờ (BTC momentum), không phải alt bắt kịp BTC.

## B. Thêm H1c (bắt buộc cho GO)
- Tập con giờ "BTC đảo chiều": sign(r_BTC(t, t+h]) ≠ sign(r_BTC(t−k, t]) (bỏ giờ r_BTC = 0). Chỉ là chẩn đoán cơ chế (dùng tương lai để CHỌN tập giờ, không phải feature).
- Thống kê, bootstrap, CI nở 1,665 như §3 H1, cho cả 4 biến thể; quyết định theo k3h4.
- Diễn giải: lead-lag thật ⇒ IC trên tập đảo chiều vẫn > 0. Nhiễu β̂ × momentum ⇒ IC ≤ 0 trên tập này.
- Báo kèm tập "BTC cùng chiều" (bổ sung, không quyết định).

## C. H2 — khôi phục ledger (không đổi định nghĩa §2–§3)
- Dựng lại 23 654 chân bằng đúng quy trình EXEC (exec_legs.py từ printDone; close_M từ kline 1m data.binance.vision theo exec/need.json). V3 nguyên văn (≥ 95% chân ghép được). Chỉ nguồn data.binance.vision, KHÔNG Binance REST.

## D. Luật GO thay thế §4 (chặt hơn, không nới)
GO ⇔ H1 (đã đạt) VÀ H1c k3h4 mean IC > 0 với CI nở dưới > 0 VÀ H2 Δ > +0,30% với CI95 dưới > 0. Thiếu/hỏng bất kỳ ⇒ ĐÓNG hướng lead-lag giờ. Không chạy thêm biến thể.
