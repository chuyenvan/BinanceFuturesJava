# PRE-REG — REX Bước 0: panel ngày (feature + target) cho selector (MASTER 2026-10-16)

Thuộc `docs/plan/PLAN_REX.md`. Bước này chỉ dựng dữ liệu và kiểm dữ liệu, không đo hiệu suất.

## Nguồn
- **Vision UM 1d:** `~/claude_master/1016/screen/k1d`, gồm 892 perp kể cả coin đã delist. Đọc lại đầy đủ các cột, trong đó có `taker_buy_quote`.
- **Funding:** `fund_day` = tổng funding thật trong ngày UTC, lấy từ `d1.parquet`.
- **Metrics 5m:** Kaggle `chuyendinh/vz-metrics5m`, gồm `oi_value`, `toptrader_ls_sum`, `ls_cnt`, `taker_ls_vol`, có từ 2021-12.
  - **Bẫy `create_time`:** từ 2024-03-04 cột này đổi nghĩa, lệch 5 phút ở phần lớn symbol (xem `data_leak_oi_2026-09-03`).
  - **Chặn:** chỉ dùng snapshot có ts ≤ **23:30 UTC** của ngày d. Taker LS lấy trung bình các bản ghi có ts ≤ 23:30.
  - Biên an toàn 30 phút lớn hơn nhiều so với độ lệch 5 phút, nên không cần xác định quy ước của từng symbol.

## Mốc thời gian
- Feature của ngày d chỉ dùng dữ liệu tới close d (24:00 UTC). Với metrics thì tới 23:30.
- Mốc quyết định là 00:00 UTC ngày d+1.
- Target lấy close d làm giá vào (≈ open d+1). Lệnh vào thực tế 1m sẽ đo ở Bước 2.

## Universe (point-in-time)
- Perp USDT, không thuộc STABLE.
- Median qv 30 ngày ≥ 20M, niêm yết ≥ 60 ngày, có close ngày d.

## Feature
Chuẩn hoá bằng rank % theo mặt cắt từng ngày, chỉ trong universe; lưu cả bản thô.

| Họ | Feature |
|---|---|
| a. momentum | `mom_k = C/C[−k] − 1`, k ∈ {1, 3, 7, 14, 28, 56, 90}; `rmom28 = mom28 − β90 · btc_mom28` (β = cov/var của lợi suất ngày, 90 ngày) |
| b. vol | `vol7`, `vol30` = std của log-ret; `atr14` = mean((H−L)/C, 14); `dvol30` = std của các log-ret < 0 trong 30 ngày |
| c. hình dạng | `skew30`; `max30` và `min30` = ret ngày lớn nhất / nhỏ nhất trong 30 ngày; `up30` = tỷ lệ ngày tăng trong 30 ngày |
| d. volume | `lqv30` = log median qv 30; `vs3` = Σqv3 / (mean qv30 · 3); `vs7` = Σqv7 / (mean qv90 · 7); `amih30` = mean(\|ret\|/qv) · 1e9 |
| e. vị trí giá | `dhi_k = C / max(H, k) − 1`, k ∈ {7, 30, 90, 365}; `dlo_k = C / min(L, k) − 1`, k ∈ {7, 30, 90}; `ma20 = C/MA20`; `ma50 = C/MA50`; `ma2050 = MA20/MA50` |
| f. taker | `tbr_k = Σtbq / Σqv`, k ∈ {1, 3, 7}; `dtbr = tbr3 − tbr30` |
| g. phái sinh | `f1 = fund_day`; `f7 = Σ7`; `fz = (f7 − mean90(f7)) / std90(f7)`; `df7 = f7 − f7[−7]`; `doi_k = OIv/OIv[−k] − 1`, k ∈ {1, 3, 7}; `oiqv = OIv / mean qv7`; `tls` = toptrader_ls_sum; `dtls7 = tls − tls[−7]`; `gls` = ls_cnt; `tkls` = mean taker_ls_vol của ngày |
| h. bối cảnh (giống nhau mọi coin; chỉ dùng ở Bước 2a) | `btc_mom7`, `btc_mom28`, `btc_vol30`; `br50` = % universe có C > MA50; `disp7` = std mặt cắt của mom7; `mfund` = median f7 |

## Target
Gọi CF là close đã ffill để xử lý coin delist.
- `y_h = CF[d+h] / C[d] − 1`, h ∈ {1, 3, 7}.
- `yx_h = y_h − median_universe(y_h)`.
- `yb_h = y_h − btc_y_h`.
- `rk_h` = rank % mặt cắt của `y_h`.
- `mae_h`, `mfe_h` = min / max của (L hoặc H)/C[d] − 1 trên các ngày d+1 … d+h. Chỉ dùng để mô tả; Bước 2–3 dùng 1m.

## Kiểm dữ liệu (FAIL thì dừng)
- **S0-V1:** assert khi dựng — mọi rolling chỉ dùng hàng ≤ d; snapshot metrics có ts ≤ d 23:30.
- **S0-V2:** chọn ngẫu nhiên 30 bộ (sym, ngày), seed 1016, rồi tính lại độc lập từ dữ liệu thô:
  - mom7, tbr3, f7, doi1, dhi30, y_3;
  - sai lệch phải ≤ 1e-9 tương đối.
- **S0-V3:** độ phủ theo năm, tính trong universe.
  - Họ a–f phải ≥ 98 % từ 2021-04.
  - Họ g/OI phải ≥ 85 % từ 2022-01.
  - Không đạt thì báo FAIL kèm danh sách.
- **S0-V4:** universe ≥ 30 coin mỗi ngày từ 2021-03. Số target bị ffill (coin delist trong cửa sổ h) phải ≤ 1 % số dòng.
- **S0-V5:** khai báo số dòng có |y_1| > 100 %, kèm danh sách, để biết có glitch dữ liệu hay không. Không loại tự động.

## Đầu ra
- `~/claude_master/rex/panel.parquet`, khoá (day, sym), gồm thô + rank + target + cờ universe.
- `s0_checks.json`.
