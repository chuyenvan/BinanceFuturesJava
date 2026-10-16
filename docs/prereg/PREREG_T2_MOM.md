# PRE-REG — T2-MOM: momentum cắt ngang 21 ngày trên alt perp, tầng 2 (MASTER 2026-10-16)

**Nguồn gốc.** SCREEN_WIDE tầng 1 (`docs/result/RESULT_SCREEN_WIDE_T1.md`, a9fa0f46): X1 = momentum 21 ngày, top decile, giữ 1 tuần.
- LO excess E 0,46 | C 1,00; LS E 0,41 | C 1,81.
- Trễ 1 ngày: excess E 0,25 | C 0,98, abs C 0,47.
- Theo năm (excess, tổng tuần): 2022 −0,53, 2024 −0,18, 2025 +1,05, 2026 +1,00.

**CÔNG KHAI:** các con số trên ĐÃ được nhìn thấy trước khi viết file này. Tiêu chí dưới đây không được nới sau khi chạy; mọi thay đổi phải là addendum có commit TRƯỚC lần chạy lại.

**Không còn OOS lịch sử.** 2021-03 → 2026-09 đều đã bị nhìn ở tầng 1, còn 2020 là SEALED (không mở nếu không có owner). Vì vậy tầng 2 là kiểm **độ bền + khả thi + rủi ro**, không phải kiểm OOS. OOS thật duy nhất là forward paper.

## Dữ liệu
- `~/claude_master/1016/screen/d1.parquet`: Vision UM 1d, 892 perp USDT (gồm cả coin đã delist), cột `fund_day` = tổng funding ngày (long trả khi > 0).
- Kỳ 2021-03-01 → 2026-09-30. Chia E = 2021–2023, C = 2024-01 → 2026-09, giống tầng 1.
- Đường crash-buy để đo correlation: `docs/result/gate_skipfull_detail_equity.csv`, cột `C2_mtm_close` (skipFull, 2021-07-08 → 2025-11-28), quy về lợi suất tuần cùng mốc.

## Luật (BASE, cố định)
- **Universe tại ngày tín hiệu s:**
  - median 30 ngày của quote volume ≥ 20M USDT;
  - đã niêm yết ≥ 60 ngày;
  - không phải stablecoin (danh sách STABLE của `sw_run.py`);
  - universe phải có ≥ 30 coin, không đủ thì bỏ tuần đó.
- **Tín hiệu:** `close[s] / close[s−21] − 1`. Long top decile, `n = max(3, N // 10)`, equal weight.
- **Thực thi:** s = Chủ nhật (UTC). Vào lệnh tại close của s+1 (Thứ Hai), tức trễ 1 ngày so với tầng 1. Thoát / rebalance tại close của s+8 (Thứ Hai tuần sau). Mỗi lệnh giữ 7 ngày.
- **Sửa survivorship (khác tầng 1):**
  - Coin không có close ở ngày thoát thì dùng close cuối cùng có trong kỳ giữ (ffill), không bị dropna.
  - Coin không có close ở ngày vào thì loại khỏi tuần đó trước khi xếp hạng.
- **Chi phí BASE, mỗi chiều:**
  - alt: 0,05 % fee + 0,05 % slippage = 0,10 %;
  - BTC: 0,05 % + 0,01 % = 0,06 %.
  - Chi phí tính theo turnover thực:
    - chân long: `(1 − overlap) × 2 × 0,10 %`;
    - hedge: `|r_long − r_hedge| × cost_hedge`, phần trôi lệch phải rebalance mỗi tuần;
    - basket thêm phần thay đổi thành phần universe: `(1 − |U_t ∩ U_{t−1}| / |U_t|) × 2 × 0,10 %`.
- **Funding:** dùng `fund_day` thật trong các ngày (s+2 … s+8). Long trả `+f`, short nhận `+f`.

## Các biến thể (tất cả đều được báo cáo; chỉ H1 dùng để quyết định)
- **H0:** chỉ long top decile, không hedge (lợi suất tuyệt đối).
- **H1 (CHÍNH):** long top decile + short BTCUSDT perp, notional bằng nhau, reset mỗi tuần.
- **H2:** long top decile + short giỏ equal-weight toàn universe.
- **H3:** long top decile / short bottom decile.

Không được chọn biến thể thắng sau khi chạy. Nếu H1 trượt mà H2/H3 đạt, điều đó chỉ được ghi nhận. Muốn chuyển sang H2/H3 phải có pre-reg mới + forward.

## Kiểm dữ liệu (chạy trước, FAIL thì dừng)
- **V1:** tắt sửa survivorship, dùng lag 0 và chi phí 0,05 %/chiều. Excess vs universe phải khớp dòng `X1 goc` trong `sw_diag.log`, Sharpe E và C sai lệch ≤ 0,01.
- **V2:** ≥ 280 tuần hợp lệ; universe nhỏ nhất ≥ 30.
- **V3:** báo số coin-tuần phải ffill vì delist. Phải ≤ 2 % tổng coin-tuần long, nếu vượt thì báo FAIL kèm danh sách.
- **V4 (assert trong code):** chỉ số ngày tín hiệu < ngày vào < ngày thoát; feature chỉ dùng close ≤ s.
- **V5:** crash-buy trùng ≥ 200 tuần với H1.

## Độ bền (dùng trong tiêu chí)
- **R1:** lookback 14 và 28 ngày.
- **R2:** đổi ngày tín hiệu sang 7 ngày khác nhau trong tuần (offset 0..6). Vẫn vào lệnh trễ 1 ngày, vẫn giữ 7 ngày.
- **R3:** quintile thay cho decile (chỉ để mô tả, không có trong tiêu chí).
- **R4:** chi phí ×2.
- **R5:** lag 0 và lag 2 (chỉ để mô tả).

## Rủi ro và khả thi (để mô tả, trừ G7 và G9)
- **Đuôi rủi ro:** maxDD, tuần tệ nhất, chuỗi 4 tuần tệ nhất, skew.
- **Khi thị trường sập:** H1 trong các tuần BTC giảm > 10 % (momentum crash).
- **Correlation:** với lợi suất tuần của BTC; với crash-buy C2; H1 trung bình trong 10 tuần tệ nhất của crash-buy.
- **Capacity:**
  - participation = (vốn / n) / median qv30 của coin, tính cho vốn $50k, $200k, $1M;
  - báo p95 participation;
  - capacity ước tính = mức vốn lớn nhất mà p95 participation ≤ 0,5 %.
- **Multiple testing:** báo Deflated Sharpe (Bailey & López de Prado) trên lợi suất tuần toàn kỳ, với N_trials = 50 (≈ 39 cấu hình tầng 1 + biến thể tầng 2). Chỉ báo cáo, không gate.

## Tiêu chí GO (H1, cấu hình BASE; phải đạt TẤT CẢ)
| # | Điều kiện |
|---|---|
| G1 | Sharpe toàn kỳ (tuần × √52) ≥ 0,60 |
| G2 | Sharpe E ≥ 0,20 và Sharpe C ≥ 0,60 |
| G3 | Chi phí ×2: Sharpe toàn kỳ ≥ 0,35 |
| G4 | ≥ 5/7 offset ngày có Sharpe toàn kỳ > 0,30 |
| G5 | Lookback 14 và 28 đều có Sharpe toàn kỳ > 0,30 |
| G6 | ≥ 4/6 năm dương (2021 … 2026, theo tổng lợi suất tuần) |
| G7 | maxDD toàn kỳ ≥ −45 % |
| G8 | Block bootstrap (khối 4 tuần, 5000 lần, seed 20261016): P(mean ≤ 0) < 0,05 |
| G9 | Correlation tuần với crash-buy C2 ≤ 0,50 |

- **GO** = chuyển sang forward paper, chỉ log, KHÔNG tiền thật.
  - Rebalance mỗi Thứ Hai bắt đầu từ 2026-10-19, ≥ 8 tuần.
  - Có bao nhiêu vốn và có pilot hay không do owner quyết.
- **NO-GO** = đóng X1 trong ledger.

## Ghi chú rủi ro biết trước
- Momentum crypto phụ thuộc regime: thắng trong uptrend alt, thua khi xoay vòng nhanh (2022, 2024). Hedge BTC không giải quyết được rủi ro alt/BTC đảo chiều.
- Close ngày ≠ giá khớp thực. Slippage 0,05 % là giả định, không đo được trên dữ liệu 1d.
- Delist với ffill có thể vẫn lạc quan: giá thanh toán khi delist có thể thấp hơn close cuối.
