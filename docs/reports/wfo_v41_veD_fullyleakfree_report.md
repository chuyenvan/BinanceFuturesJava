# WFO V4.1 — VẾ D (FULLY-LEAK-FREE: universe + funding per-fold + PRED GATE-WF per-fold) — 2026-07-05

**Env:** Oracle ns=test, DATA_DIR=wfo_dataset_wf_v3 (pred=1,795,680 gate-WF, md5 6df3b59d; funding wf-v2; market unchanged), jar task113, N=30, tiêu chí pre-registered V4.1.
**Số tổng (17 window):** WFE_med 0.142 | %OOS-SUCCESS 35.3% (6/17) | worst maxDD 29.4% | ❌ FAIL/REVIEW.
**⚠️ Hiệu ứng cấu trúc phải đọc kèm:** pred gate-WF chỉ tồn tại từ FIRST_OOS=2023-01 → w0–w3 (OOS 2022) ZERO_TRADES
do gate reject 30/30 vì thiếu pred — KHÔNG phải tín hiệu chất lượng. Số tổng 17-window vì thế KHÔNG so được với A.

## SO A vs D TRÊN VÙNG CHUNG w4–w16 (13 window, OOS 2023Q1→2026Q1)
| w | A (pred full_basket, leaked-model): WFE / pnl / trades | D (pred gate-WF sạch): WFE / pnl / trades |
|---|---|---|
| 4 | 0 / 0 / 0 ZERO | 0 / 6.6 / 8 TOO_FEW |
| 5 | 0.008 / 26 / 10 | 0.225 / 15.6 / 32 |
| 6 | 0.486 / 517 / 31 | 1.842 / 388 / 17 |
| 7 | 0.227 / 252 / 8 | 0.317 / 276 / 16 |
| 8 | 0.639 / 659 / 94 | 0.586 / 774 / 50 |
| 9 | 0.561 / 876 / 201 | 0.286 / 447 / 192 |
| 10 | 0.635 / 1343 / 424 | 0.347 / 621 / 286 |
| 11 | 0.583 / 885 / 33 | 0.062 / 66 / 8 |
| 12 | 0.380 / 1799 / 281 | 0.560 / 613 / 202 |
| 13 | 0 / 0 / 0 **ZERO** | 0 / 0 / 0 **ZERO** |
| 14 | 0.114 / 152 / 10 | 0.142 / 152 / 10 |
| 15 | 8.874 / 15775 / 1441 | 14.243 / 18566 / 1461 |
| 16 | 0.015 / 216 / 12 | 0.025 / 337 / 40 |
Tổng pnl vùng chung: A ≈ 22,500 vs D ≈ 22,260 — **TƯƠNG ĐƯƠNG**, thắng/thua đan xen.

## KẾT LUẬN
1. **Pred leaked-model KHÔNG phải nguồn phồng kết quả đáng kể** — thay pred sạch per-fold, kết quả vùng chung không đổi
   về chất. Nhất quán với đo IC: gap in-sample→OOS của gate chỉ 0.02–0.04 (model không overfit nặng).
2. Ghép trọn chuỗi thí nghiệm A/B/C/D: nguồn phồng %OOS = leak universe/funding (B−A = +23.5đ); pred-model leak ≈ 0;
   coverage +5.9đ; **WFE thấp đồng đều mọi cấu hình → tầng selection là nghi phạm duy nhất còn lại.**
3. **BÍ ẨN MỚI w13 (OOS 2025Q2): ZERO_TRADES ở CẢ A lẫn D** — reject 30/30 không do pred (hai nguồn pred khác nhau
   cùng zero). Nghi funding selector/universe/tham số reject sạch quý này → mổ w13 là ca lâm sàng đầu tiên của
   cuộc điều tra selection layer. (w14 A=D y hệt từng số lẻ → gate không binding window đó — thêm dấu vết gate
   ít quyết định hơn ta tưởng?)
