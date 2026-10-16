# PRE-REG — MK: sleeve maker trên BTC (S1 giờ 21–23 UTC, S7 cuối tuần) với khớp maker bảo thủ trên 1m — họ #2 (MASTER 2026-10-17)

**Bối cảnh:**
- Trong SCREEN_WIDE, chỉ 2 tín hiệu còn dương, và chỉ dương khi khớp maker:
  - S1: long BTC 21:00 → 23:00 UTC. Taker: E −0,98 \| C −0,93. Maker giả định: E +0,20 \| C +0,78.
  - S7: long từ thứ Sáu 16:00 ET tới thứ Hai 10:00 ET. Maker: E +0,39 \| C +0,56.
- Con số "maker" ở SCREEN_WIDE giả định **luôn khớp tại close**. Đó là ước tính lạc quan.
- Họ #2 chỉ hỏi một câu: **khớp maker thực tế hơn (bảo thủ) thì còn lãi không?**

**Nhiễm dữ liệu:** toàn bộ 2021 → 2026-09, kể cả 2026, ĐÃ được nhìn trong SCREEN_WIDE ở dạng gross. Vì vậy bước này KHÔNG phải kiểm OOS. Nếu GO, chỉ forward paper mới là bằng chứng mới.

## Dữ liệu
- `~/claude_master/1016/screen/m1_BTCUSDT.parquet`: perp 1m, có O/H/L/C, 2021-01 → 2026-09.
- Funding BTC theo ngày lấy từ `d1.parquet`. Phân bổ theo thời gian giữ: S1 không giữ qua mốc funding (21–23 không chứa 00/08/16), S7 giữ qua khoảng 8 mốc.

## Mô phỏng khớp (cố định)
**Vào lệnh:**
- Tại mốc vào t0, đặt limit BUY bằng close của phút t0−1.
- Phút m trong [t0, t0+10) khớp nếu **low_m < limit**, tức giá xuyên qua mức limit; chạm bằng thì không tính khớp.
- Khớp thì giá vào = limit, phí maker 0,02 %.
- Không khớp trong 10 phút thì **bỏ phiên**, PnL = 0.

**Thoát lệnh:**
- Tại mốc thoát t1, đặt limit SELL bằng close của phút t1−1.
- Khớp nếu high_m > limit trong [t1, t1+10). Phí 0,02 %.
- Không khớp trong 10 phút thì thoát market tại close phút t1+9, phí taker 0,05 % + slippage 0,02 %.

**Hai bản để so sánh:**
- Taker cả hai đầu: 0,07 %/chiều, khớp tại close t0−1 và t1−1.
- Maker luôn khớp: cách SCREEN_WIDE dùng.

## Luật thời gian
- **S1:** t0 = 21:00 UTC, t1 = 23:00 UTC, mỗi ngày.
- **S7:** t0 = 16:00 ET thứ Sáu, t1 = 10:00 ET thứ Hai. ET có DST, theo `America/New_York`.

## Thước đo
- Theo năm 2021 … 2026-09:
  - Sharpe tính theo PnL ngày, × √365, mỗi ngày lịch là một quan sát;
  - lãi/năm, maxDD.
- Tỷ lệ khớp vào; tỷ lệ phải thoát bằng market.
- "Chi phí cơ hội": phần lợi suất của các phiên bị bỏ do không khớp.

## Gate (cho từng sleeve S1M, S7M; phải đạt tất cả)
| # | Điều kiện |
|---|---|
| G1 | Sharpe toàn kỳ ≥ 0,5 |
| G2 | Lãi ròng > 0 ở ≥ 5/6 năm (2021 … 2026) và ở cả 2024, 2025 |
| G3 | Tỷ lệ khớp vào ≥ 60 % |
| G4 | maxDD ≥ −25 % |

**Nếu GO:** pre-reg forward paper ≥ 8 tuần. Đây là tín hiệu mới duy nhất được chấp nhận.

Ledger cộng 2.
