# PRE-REG — SQ: short squeeze sau funding âm sâu kéo dài — họ #3, họ CUỐI theo ngân sách (MASTER 2026-10-17)

**Cơ chế:**
- Khi funding âm sâu nhiều kỳ liền, bên short phải trả phí liên tục. Đây là "người buộc phải giao dịch": họ phải đóng lệnh dần hoặc bị ép lên giá.
- Long đúng lúc này vừa đứng phía mua đối diện dòng cover, vừa **nhận** funding.
- Khung thời gian tính bằng ngày, nên phí (0,14 %/vòng) nhỏ so với biên độ biến động. Khác FW, vốn chỉ đo ±1h.

**Khác X5 (SCREEN_WIDE):**
- X5 xếp hạng decile funding 7 ngày theo mặt cắt, rebalance hằng tuần.
- SQ là **sự kiện** theo ngưỡng tuyệt đối: chỉ ra lệnh khi funding vượt ngưỡng ở cấp từng coin.

**Nhiễm dữ liệu:** họ này CHƯA đo. HO 2026 chưa chạm.

**Quy tắc ngân sách đã chốt với owner:** SQ là họ #3, cũng là họ cuối. Nếu NO-GO thì dừng tìm alpha mới cho tới sau go-live.

## Sự kiện
- **Dữ liệu:** funding lake (từng lần thanh toán), `r8 = rate × 8 / interval_h`.
- **Điều kiện kích hoạt tại mốc T:** `r8 ≤ −0,10 %` ở lần thanh toán T **và** ở lần ngay trước đó, tức 2 kỳ liên tiếp.
- **Universe:** qv30 ≥ 20M, niêm yết ≥ 60 ngày, không phải stablecoin.
- **Cooldown:** mỗi coin tối đa 1 sự kiện trong 72h. Sự kiện tiếp theo chỉ tính khi T mới > T cũ + 72h.

## Giao dịch (long-only)
- Mua tại `P(T+1m)` (close của nến 1m có open_time = T).
- Thoát tại `P(T+H)` với H ∈ {24h (CHÍNH), 72h}.
- PnL = lợi suất giá − 0,14 % + Σ funding nhận được tại các mốc thanh toán trong (T, T+H].
  - Long nhận khi rate < 0: cộng −rate.
  - Lấy từ funding lake của chính coin đó.
- **Excess** (chỉ để tham khảo) = PnL − lợi suất BTC trong cùng cửa sổ.

## Kỳ và thước đo
- DEV = 2022–2024; VAL = 2025. Sự kiện thiếu giá thoát (cuối 2025) bị loại.
- Thước đo:
  - lãi ròng trung bình, median, hit rate;
  - t gom theo ngày (trung bình các sự kiện cùng ngày, rồi tính t của chuỗi theo ngày);
  - theo năm;
  - 5 % sự kiện tệ nhất;
  - excess so với BTC.

## Gate (H = 24h; phải đạt tất cả)
| # | Điều kiện |
|---|---|
| G1 | DEV lãi ròng trung bình > 0, t ≥ 3 |
| G2 | Dương ở cả 3 năm 2022, 2023, 2024 |
| G3 | VAL lãi ròng > 0, t ≥ 2 |
| G4 | DEV excess so với BTC > 0, tức không phải beta |
| G5 | Lãi ròng trung bình DEV vẫn > 0 sau khi bỏ 1 % sự kiện lãi nhất, tức không phụ thuộc vài cú squeeze cực lớn |

Ledger cộng 2 (H24, H72).

## Kiểm dữ liệu
- **SQ-V1:** chọn ngẫu nhiên 10 sự kiện, tính lại tay điều kiện kích hoạt và P(T+1), P(T+24h) từ dữ liệu thô.
- **SQ-V2:** ≥ 97 % sự kiện có đủ giá.
