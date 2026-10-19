# BOOK_HEDGE — short BTC perp theo phơi nhiễm long đang mở (kết quả)

Ngày 2026-10-19. Pre-reg `docs/prereg/PREREG_BOOK_HEDGE.md` 8521f018. Script `research/analysis/book_hedge.py`, JSON `docs/result/book_hedge/`.
Overlay trên equity MTM phút (Vision) của 8 run OFF `gqsf-*`; return BTC phút từ `edge_attr/index.npz`.

## Kiểm hợp lệ
- V1 PASS: nền tái lập dd_mtm22 ISO_RISK đúng tới 1e-4 cả 8 seed.
- V2 PASS: phút thiếu BTC lúc có vị thế 19–47 / 1–2,1 triệu phút (≤ 0,003 %).
- CAGR22 ở đây tính trên đường MTM phút (nền 37,95) — khác 37,0 của ISO (equity ngày của sim); so sánh nền↔hedge dùng cùng một cách.

## Kết quả (trung bình 8 seed)

| Arm | CAGR22 | maxDD22 | DD toàn kỳ | Calmar22 | UW22 (ngày) | ΣPnL | DD LUNA | DD FTX | Phí hedge |
|---|---|---|---|---|---|---|---|---|---|
| Nền (không hedge) | 37,95 | −22,55 | −22,63 | 1,69 | 116 | 110 047 | −22,3 | −14,8 | — |
| h = 0,5 | 34,71 | −17,81 | −18,30 | 1,95 | 127 | 99 956 | −17,1 | −10,7 | ~1,5k |
| h = 1,0 | 31,37 | −16,86 | −16,86 | 1,86 | 197 | 89 865 | −12,2 | −6,6 | ~3,0k |

Tương quan lợi suất ngày book ↔ BTC: 0,28.

## Luật ⇒ **NO-GO cả hai arm**
- h = 0,5: DD nông hơn ≥ 5pp ở 4/8 seed (cần 7/8; trung bình +4,74pp); ΔCalmar +0,26 CI99 [+0,06; +0,47] (đạt); ΣPnL −9 % (đạt) ⇒ FAIL tiêu chí DD.
- h = 1,0: 6/8 seed (cần 7/8; trung bình +5,68pp); ΔCalmar +0,17 CI99 [−0,08; +0,42] (FAIL); ΣPnL −18 %.

## Đọc (mô tả, không đổi luật)
- Hedge là cơ chế DUY NHẤT trong chuỗi nghiên cứu làm DD nông hơn rõ mà không cắt mạnh lợi nhuận: h = 0,5 đổi −9 % ΣPnL lấy −4,7pp DD,
  Calmar tăng 7/8 seed (S777 giảm 2,01 → 1,88), CI99 Calmar > 0. ΔDD từng seed: 4,98 / 5,93 / 5,03 / 6,08 / 4,43 / 6,02 / 0,47 / 4,98
  (hai seed trượt ngưỡng 5pp đúng 0,02pp — luật vẫn là luật). Không đạt ngưỡng DD đã chốt ⇒ không được thăng hạng.
- h = 1,0 cắt sâu đợt sập (LUNA −22 → −12) nhưng sinh nguồn DD mới khi BTC tăng mạnh mà alt không theo (UW 116 → 197 ngày):
  DD tệ nhất dời sang giai đoạn khác, dừng quanh −16,5 % mọi seed.
- Funding bị bỏ qua (thường có lợi cho short trong 2023–2025) ⇒ PnL hedge có thể bị đánh giá thấp; slippage BTC bỏ qua (thanh khoản rất cao).
- Mọi số là DEV đã dùng nhiều lần. Nếu muốn theo hướng này: pre-reg mới với h = 0,5 cố định, xác nhận một lần trên dữ liệu độc lập
  (HO4 2026, cần tải kline1m 2026 từ Vision) — không chỉnh h trên DEV.
