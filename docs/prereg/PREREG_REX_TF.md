# PRE-REG — REX-TF: trend-following long-only theo từng coin (Zarattini–Pagani–Barbon 2025), tầng 1 (MASTER 2026-10-17)

**Vì sao làm hướng này:**
- Owner muốn một hệ MỚI đi từng bước: chọn coin → vào khi nào → giữ và thoát ra sao. Hệ cũ không được động vào.
- REX S1/S1b/S2a cho thấy chọn coin theo mặt cắt không tạo ra tiền. Hướng này thì khác: thời điểm vào và luật thoát (trailing stop) chính là nguồn edge.
- Nguồn: Zarattini, Pagani, Barbon (2025), "Catching Crypto Trends: A Tactical Approach for Bitcoin and Altcoins"; tóm tắt trên CXO Advisory và Concretum.
  - Paper báo Sharpe ròng > 1,5 và alpha 10,8 %/năm so với BTC.
  - Dữ liệu paper tới 2025-03, nên **2025-04 → 2026-09 là out-of-sample thật đối với paper**.
- Tham số lấy đúng như paper đã công bố. KHÔNG tune.

**Nhiễm dữ liệu:**
- DEV 2022–2024 đã được dùng ở REX (khác tín hiệu), và cũng nằm trong mẫu của paper.
- Luật TF này CHƯA được đo trên dữ liệu của mình.

## Luật (theo paper; những chỗ paper không nói, tôi tự khai ở đây)

**Universe:**
- Hằng ngày lấy **20 perp USDT thanh khoản nhất** theo median qv 30 ngày.
- Điều kiện: niêm yết ≥ 365 ngày, không phải stablecoin.
- Coin rớt khỏi top-20 thì đóng vị thế ở close hôm đó (danh mục xoay vòng).

**Lookback ensemble:** N ∈ {5, 10, 20, 30, 60, 90, 150, 250, 360}.

**Với mỗi coin và mỗi N:**
- **Vào lệnh:** close_t > max(close_{t−N} … close_{t−1}).
- **Trailing stop:** `stop_t = max(stop_{t−1}, (max_N + min_N) / 2)`. max_N và min_N là max/min của close trong N ngày gần nhất, tính cả t. Stop đặt lần đầu ở ngày vào lệnh.
- **Thoát lệnh:** close_t < stop_t. Thoát xong thì chờ breakout mới.
- Mọi quyết định lấy theo close ngày t. Vào và thoát giả định khớp ở close t (≈ open t+1). Độ trễ khớp thực tế sẽ đo bằng 1m ở tầng 2.

**Sizing:**
- Trọng số coin i = (1/20) × (tỷ lệ số N đang ở trạng thái long) × min(0,25 / σ90_ann, 2,0).
- σ90_ann = std của lợi suất ngày trong 90 ngày × √365.
- Cân lại hằng ngày. Tổng gross tối đa 2,0.

**Chi phí:** 0,10 % mỗi chiều trên Σ|Δw|, và funding thật (long trả).

## Biến thể
| Mã | Mô tả |
|---|---|
| **TF20 (CHÍNH)** | Như trên |
| TFBTC | Chỉ BTC: trọng số = tỷ lệ N đang long × min(0,25/σ, 2) |
| TF20R | Như TF20 nhưng chỉ lấy coin có score S1 (C7) ≥ median của universe REX trong ngày, thay coin rớt bằng coin thanh khoản kế tiếp. Dùng để đo selector REX có cộng thêm giá trị không |

## Benchmark
BTC buy & hold, đo trong cùng kỳ.

## Kỳ đo
- DEV = 2022-01-01 → 2024-12-31.
- VAL = 2025-01-01 → 2025-12-31. Trong đó 2025-04 trở đi là OOS của paper.
- HO 2026: KHÔNG đọc ở tầng 1.

## Gate (TF20; phải đạt tất cả để lên tầng 2)
| # | Điều kiện |
|---|---|
| G1 | Sharpe ròng DEV ≥ 0,8 |
| G2 | Lãi ròng ≥ −5 % ở mỗi năm 2022, 2023, 2024. Năm 2022 là năm sập: hệ trend được phép lỗ nhẹ, không được lỗ nặng |
| G3 | maxDD DEV ≥ −35 % |
| G4 | Chi phí ×2: Sharpe DEV ≥ 0,5 |
| G5 | Alpha so với BTC dương trên DEV (intercept của hồi quy lợi suất ngày theo BTC, nhân 365) |
| G6 | VAL 2025: Sharpe ≥ 0,4 và lãi > 0 |
| G7 | Correlation tuần với crash-buy C2 ≤ 0,5 |

TF20R chỉ được ghi nhận là "selector có giá trị" khi Sharpe TF20R > TF20 ở CẢ DEV lẫn VAL.

**Nếu GO, tầng 2 gồm:**
- khớp lệnh bằng 1m;
- đo độ trễ khớp;
- các tinh chỉnh vào/thoát khai trước;
- HO 2026 chạy 1 lần;
- forward paper.

## Kiểm dữ liệu
- **TF-V1:** assert mọi max/min/σ chỉ dùng close ≤ t.
- **TF-V2:** chọn ngẫu nhiên 10 (coin, N, ngày), tính trạng thái tay và so với trạng thái của mô phỏng.
- **TF-V3:** universe đủ 20 coin mỗi ngày từ 2022-01.
