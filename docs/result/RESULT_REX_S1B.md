# RESULT REX Bước 1b — market-neutral từ selector S1 (P1) (MASTER 2026-10-16)

- **Pre-reg:** `docs/prereg/PREREG_REX_S1B.md` (95e47376).
- **Code:** `research/rex/rex_s1b.py`.
- **Output:** `~/claude_master/rex/` gồm `s1b_result.json`, `s1b.log`, `s1b_*.csv`.

## VERDICT: **NO-GO** — đóng P1
Biến thể thắng N7 (C7, h = 7) trượt 3 gate:
- **G1:** DEV Sharpe 1,07, dưới ngưỡng 1,5.
- **G6:** chi phí ×2 còn 0,67, dưới 0,8.
- **G7:** VAL 2025 Sharpe −0,02.

| Biến thể | DEV Sh | ann | maxDD | Sh theo năm 22/23/24 | % tháng + | chi phí ×2 | turnover |
|---|---|---|---|---|---|---|---|
| N1 (h1) | 0,34 | +9,6 % | −41 % | 0,63 / 0,78 / −0,23 | 51 % | −1,33 | 1,28 |
| N3 | 0,76 | +19,1 % | −27 % | 0,96 / 0,71 / 0,62 | 68 % | 0,02 | 0,51 |
| **N7** | **1,07** | +25,0 % | −21 % | 1,65 / 1,46 / 0,43 | 68 % | 0,67 | 0,26 |
| N1b (buffer) | 0,85 | +22,6 % | −32 % | 1,40 / 0,82 / 0,49 | 54 % | 0,19 | 0,48 |

Các điểm đạt:
- Correlation với BTC ≈ 0 và correlation tuần với crash-buy ≈ 0, ở cả bốn biến thể.
- Ngày tệ nhất khoảng −5 %. Một coin short gây lỗ tối đa khoảng 2,5 % trong một ngày.

**VAL 2025 (N7):**
- Sharpe −0,02, lãi −0,5 %/năm, maxDD −23 %.
- Chân long −68,7 %/năm, chân short +77,0 %/năm: hai chân triệt tiêu nhau.
- Năm 2025 alt sập đồng loạt. Phần chênh nhờ chọn coin (top so với bottom) biến mất, cân beta không giữ được.
- Sharpe theo năm trong DEV giảm dần (1,65 → 1,46 → 0,43) rồi xuống 0 ở VAL: edge đang yếu đi theo thời gian.

## Kết luận
Selector S1 xếp hạng đúng thứ tự coin, với rank IC ổn định khoảng 0,11. Nhưng tín hiệu đó không chuyển thành tiền:
- **Long-only** (S1): không thắng universe sau phí, và thua BTC.
- **Market-neutral** (S1b): DEV chỉ đạt Sharpe khoảng 1, VAL 2025 bằng 0.

Rank IC chủ yếu đến từ hiện tượng "coin vol thấp đứng hạng trung vị cao hơn". Hiện tượng này không tạo ra chênh lệch lợi suất **trung bình** đủ lớn để trả phí và chịu được các năm sập đồng loạt.

Ledger cộng 4.
