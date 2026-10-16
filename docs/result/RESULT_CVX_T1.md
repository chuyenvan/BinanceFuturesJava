# RESULT CVX tầng 1 — tín hiệu cross-venue public (MASTER 2026-10-16)

- **Pre-reg:** `docs/prereg/PREREG_CVX.md` (b01558e1).
  - Addendum 1 (b5278de9) viết SAU lần chạy đầu. Nó chỉ sửa spec D3 và lọc các token ghép sai giữa Upbit và Binance, không đổi luật tín hiệu.
  - Lần chạy đầu cũng không có tín hiệu nào sống sót.
- **Code:** `research/cvx/cv_data.py`, `cv_run.py`, `cv_diag.py`.
- **Output:** `~/claude_master/1016/cvx/`, gồm `cvx_result.json`, `cvx_run.log`, `cvx_run_v0.log` (lần đầu) và `upbit_match_diag.csv`.
- **Dữ liệu:**
  - Vision spot 1h BTC/ETH.
  - Coinbase 1h BTC-USD/ETH-USD.
  - Upbit 1d: 238 coin KRW trùng với perp Binance; 9 coin bị loại theo addendum.
  - Bybit funding: 648 perp trùng Binance.
- **Kiểm dữ liệu D1–D5:** PASS sau addendum.
  - Coinbase phủ 99,97 %.
  - Correlation lợi suất giờ CB vs BN = 0,998.
  - Correlation funding BTC giữa Bybit và Binance = 0,85.

## VERDICT: **0/10 sống sót** → đóng hướng cross-venue ở dạng tầng 1

Sharpe E | C sau phí. Các dòng cắt ngang là LO-H (long decile, short BTC, vào trễ 1 ngày) hoặc LS.

| Tín hiệu | E | C | Ghi chú |
|---|---|---|---|
| CV1a: Coinbase premium, giữ theo giờ | +0,01 | +0,09 | khoảng 4 lần đổi trạng thái mỗi ngày, phí ăn hết |
| CV1b: Coinbase premium, giữ theo ngày | +0,41 | +0,82 | = beta: buy & hold BTC cho E 0,27, C 0,76. IC 24h là 0,005 \| 0,006 |
| CV2a: kimchi BTC contrarian, 1 ngày | −0,19 | +0,39 | |
| CV2b: kimchi BTC contrarian, 7 ngày | +0,26 | +0,10 | IC 7d là −0,14 ở E nhưng +0,03 ở C, tức đã tắt |
| CV3-LO: long RP Upbit thấp | −0,62 | −0,79 | |
| CV3-LS | −0,89 | +0,27 | đổi dấu giữa hai kỳ |
| CV3b-LO: attention Upbit thấp | −0,04 | −0,84 | |
| CV3b-LS | −0,35 | +0,85 | đổi dấu |
| CV4-LO: funding Binance − Bybit thấp | −0,22 | −0,21 | |
| CV4-LS | +0,01 | −0,22 | maxDD −99 % |

**IC.** Coinbase premium so với lợi suất BTC: 1h E 0,018 / C 0,002; 4h E 0,028 / C −0,002. Có một chút tín hiệu ở E rồi biến mất ở C. Điều này khớp với việc chỉ số này đã được CryptoQuant công khai rộng rãi.

**Mô tả hậu kiểm, không phải phép thử.** CV3-LO âm mạnh ở cả hai kỳ:
- Coin có premium Upbit thấp kém hơn BTC, và kém hơn cả giỏ alt EW ở E (EXC −1,66).
- Đảo dấu lại (long coin có premium Hàn cao) thì LS cho E +0,89 nhưng C −0,27, tức không ổn định.
- Không đưa lên tầng 2.

## Giới hạn
- Survivorship: Upbit và Bybit chỉ cho các market đang niêm yết.
- Hyperliquid chưa được thử vì chỉ có dữ liệu từ 2023-05.
- OKX không có funding lịch sử qua API.

Ledger cộng 10.
