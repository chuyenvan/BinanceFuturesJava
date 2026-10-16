# PRE-REG — FW: dòng tiền bắt buộc quanh mốc thanh toán funding, tầng 1 (MASTER 2026-10-17)

**Bối cảnh:**
- Owner (10-17) đồng ý đào theo hướng tìm "ai buộc phải giao dịch, vào lúc nào".
- Ngân sách tối đa 3 họ; nếu không họ nào sống thì dừng tìm alpha mới cho tới sau go-live. FW là họ số 1.
- Hệ mới, độc lập; không đụng hệ cũ.

**Cơ chế giả thuyết:** ở mỗi mốc thanh toán T, bên đang giữ phía phải trả funding có động cơ đóng lệnh ngay trước T rồi mở lại sau T.
- Funding dương cực đoan: bên long bán trước T nên giá dưới áp lực bán, sau T long mua lại nên giá hồi.
- Funding âm cực đoan: bên short mua đóng trước T nên giá tăng trước T, sau T giá giảm lại.

Họ này CHƯA từng được đo trong dự án. HO 2026 chưa chạm.

## Dữ liệu
- **Funding:** lake `~/claude_master/1016/carry/fund/funding-YYYY.parquet` (ts, sym, interval_h, rate).
  - Mốc T = ts làm tròn xuống phút.
  - Rate quy về 8h: `r8 = rate × 8 / interval_h`.
- **Giá 1m:** `~/vz_e1/raw/kline1m-YYYY-MM.parquet`, 2021-12 → 2025-12.
  - `P(t)` = close của nến 1m có open_time = t − 1 phút (giá ngay tại t).
- **Universe** tại ngày của T: qv30 ≥ 20M lấy từ `d1.parquet`, không phải stablecoin.

## Tín hiệu (không lookahead)
- `s = r8` của **lần thanh toán ngay trước** T, tức T − interval. Giá trị này đã biết chắc từ lâu trước T.
- **Cực dương:** s ≥ +0,05 %. **Cực âm:** s ≤ −0,05 %.
- Báo kèm theo quintile của s (chỉ mô tả).

## Đo (event study; log return)
- `pre = ln P(T) − ln P(T−60m)`; `post1 = ln P(T+60m) − ln P(T)`; `post4 = ln P(T+240m) − ln P(T)`.
- **Đối chứng (control):** cùng coin, cùng độ dài cửa sổ, nhưng lấy mốc T − 2h (không trùng mốc thanh toán nào với coin 4h/8h).
- **DiD:** chênh lệch event − control, ghép theo từng sự kiện.
- **t-stat:** gom theo mốc T (trung bình mọi coin cùng T), rồi tính t của chuỗi đó theo thời gian để tránh correlation mặt cắt.

## Luật giao dịch (long-only)
- Chi phí 0,05 % taker + 0,02 % slippage mỗi chiều, tức 0,14 % một vòng.
- Funding: tính khi đang giữ vị thế ở thời điểm T.

| Mã | Điều kiện | Lệnh |
|---|---|---|
| L_post | cực dương | mua tại T, bán tại T+60m (không giữ qua T nên không trả funding) |
| L_pre | cực âm | mua tại T−60m, bán tại T+1m (giữ qua T nên NHẬN funding \|rate\|) |
| L_cap | cực âm | mua tại T−5m, bán tại T+5m; lợi nhuận = giá + funding nhận được (bắt carry) |

## Kỳ đo
- DEV = 2022-01-01 → 2024-12-31.
- VAL = 2025-01-01 → 2025-12-31.

## Gate cho từng luật (phải đạt tất cả)
| # | Điều kiện |
|---|---|
| G1 | DEV lãi ròng trung bình mỗi lệnh > 0, với t (gom theo T) ≥ 3 |
| G2 | Lãi ròng dương ở cả 3 năm 2022, 2023, 2024 |
| G3 | VAL 2025 lãi ròng > 0 với t ≥ 2 |
| G4 | DiD (event − control) của cửa sổ tương ứng cùng dấu với giả thuyết và t ≥ 2 trên DEV, tức hiệu ứng gắn với mốc thanh toán chứ không phải giờ trong ngày |
| G5 | Chi phí ×2 (0,28 %/vòng): DEV lãi ròng trung bình > 0 |

Luật nào đạt hết thì lên tầng 2: capacity, độ sâu sổ lệnh, mô phỏng khớp maker, xây danh mục, HO 2026, forward. Ledger cộng 3.

## Kiểm dữ liệu
- **FW-V1:** ≥ 99 % số ts funding nằm trong 60 giây sau mốc giờ chẵn.
- **FW-V2:** ≥ 98 % sự kiện có đủ cả 4 điểm giá. Sự kiện thiếu điểm giá bị loại và báo số lượng.
- **FW-V3:** chọn ngẫu nhiên 10 sự kiện, tính tay pre/post1 từ 1m thô rồi so với kết quả pipeline. Sai lệch phải ≤ 1e-12.
