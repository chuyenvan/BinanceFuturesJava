# PREREG_BOOK_HEDGE_ETH — biến thể ETH của BOOK_HEDGE (owner yêu cầu 10-19)

Ngày 2026-10-19. Commit TRƯỚC khi chạy. Chỉ đo offline, y nguyên PREREG_BOOK_HEDGE (8521f018) trừ công cụ hedge.

## Ghi nhận trung thực
- Đây là lần thử THỨ HAI sau khi đã thấy BOOK_HEDGE (BTC) trượt luật sát nút ⇒ kiểm định bội. Vì vậy kết quả ETH là
  THĂM DÒ: kể cả GO cũng KHÔNG được thăng hạng trên DEV; chỉ được đưa sang xác nhận 1 lần trên HO4 2026 với h cố định.
- Lý do kỹ thuật để thử ETH: book 97 % alt; alt thường đi sát ETH hơn BTC ⇒ hedge ETH có thể bám nhân tố sập alt tốt hơn,
  đổi lại rủi ro ETH yếu riêng (2024–2025) làm hedge lãi/lỗ lệch.

## Thay đổi duy nhất so với BOOK_HEDGE
- Công cụ: short ETHUSDT perp; return phút = log-return close kline1m Vision ETHUSDT (phút đầu tháng nối với close cuối tháng trước).
- Mọi định nghĩa khác giữ nguyên: N(m), h ∈ {0,5; 1,0}, phí taker 0,05 % × h × |ΔN|, BỎ QUA funding (để so được với BTC),
  chỉ số, V1/V2, luật GO (DD nông ≥ 5pp ở ≥ 7/8 seed VÀ ΔCalmar CI99 > 0 VÀ ΣPnL giảm ≤ 50 %), winner theo Calmar.
- Báo kèm (mô tả): so ETH vs BTC cùng h (ΔDD, ΔCalmar ghép cặp theo seed); tương quan ngày book ↔ ETH.
