# RESULT REX-TF tầng 1 — trend-following Donchian ensemble (Zarattini–Pagani–Barbon 2025) (MASTER 2026-10-17)

- **Pre-reg:** `docs/prereg/PREREG_REX_TF.md` (56dbba7f).
- **Code:** `research/rex/rex_tf.py`; phần đo độ nhạy hậu kiểm ở `rex_tf_sens.py`.
- **Output:** `~/claude_master/rex/` gồm `tf_result.json`, `tf.log`, `tf_sens.log`, `tf_*.csv`.
- **Kiểm dữ liệu:**
  - TF-V2: 20 lần chuyển trạng thái được kiểm tay, 0 lỗi.
  - TF-V3: universe đủ 20 coin mỗi ngày.

## VERDICT: **NO-GO** — TF20 trượt G1, G2, G6
| | Sharpe | Lãi/năm | maxDD | Năm (tổng lợi suất) | Alpha so với BTC | Correlation với BTC | Phơi nhiễm trung bình |
|---|---|---|---|---|---|---|---|
| **TF20** DEV | 0,72 | +5,1 % | −9 % | 2022 −5,2 % · 2023 +13,1 % · 2024 +7,0 % | +2,2 % | 0,59 | 0,08 |
| TF20 VAL 2025 | **−0,58** | −3,4 % | −5 % | | −3,5 % | | |
| TFBTC DEV | 0,89 | +12,9 % | −12 % | 2022 −11 % · 2023 +23 % · 2024 +26 % | +5,9 % | 0,70 | 0,22 |
| TFBTC VAL | −0,55 | −7,2 % | | | | | |
| TF20R DEV (lọc bằng selector) | 0,68 | | | | | | |
| TF20R VAL | −0,91 | | | | | | |
| BTC buy & hold DEV / VAL | 0,69 / 0,02 | | −67 % / −32 % | | | | |

Gate:
- **Đạt:** G3 (maxDD), G4 (chi phí ×2 Sharpe 0,65), G5 (alpha DEV > 0), G7 (correlation với crash-buy 0,11).
- **Trượt:** G1 (0,72 < 0,8), G2 (2022 −5,2 % < −5 %), G6 (VAL âm).

Selector REX không cộng thêm giá trị: TF20R kém TF20 ở cả DEV lẫn VAL.

**Đoạn OOS thật của paper (2025-04 → 2025-12):**
- TF20: Sharpe −0,02, tổng −0,1 %.
- Bản chuẩn hoá theo số vị thế đang mở (hậu kiểm): Sharpe −0,04.

## Ghi chú
- Phơi nhiễm thấp (khoảng 8–11 %), vì cách sizing đã khai cho mỗi coin là (1/20) × min(0,25/σ, 2).
  - Sharpe không đổi khi phóng to danh mục, nên kết luận không phụ thuộc vào mức phơi nhiễm.
  - Đã thử thêm bản chuẩn hoá theo số vị thế đang mở (hậu kiểm): DEV Sharpe 0,69, VAL −0,52. Kết quả gần như y hệt.
- Trên DEV, trend-following giảm drawdown rất mạnh so với BTC (−9 % so với −67 %) nhưng lợi suất nhỏ. Năm 2025 thì không có edge. Kết quả paper (Sharpe > 1,5) không lặp lại trên Binance perp sau thời điểm công bố.

Ledger cộng 3.
