# PRE-REG — CVX: tín hiệu cross-venue public, tầng 1 (MASTER 2026-10-16)

**Bối cảnh.** SCREEN_WIDE và T2-MOM cho thấy mọi anomaly dựng từ dữ liệu Binance đều đã chết hoặc chỉ là beta. Hướng còn lại là thông tin **từ sàn khác** mà hệ hiện tại chưa dùng: Coinbase (dòng tiền Mỹ), Upbit (retail Hàn), Bybit (funding của sàn đối thủ).

Đã probe từ Oracle, đều reach được:
- Coinbase candles 1h có từ 2021 (USDT-USD chỉ có từ 2021-06).
- Upbit candles có từ 2021, nhưng KRW-USDT không có lịch sử cũ.
- Bybit funding history có từ 2021.
- Hyperliquid chỉ có từ 2023-05 nên bỏ ở tầng 1.

KHÔNG dùng Binance REST; phía Binance chỉ lấy từ Vision. File này commit TRƯỚC khi tải dữ liệu.

**Bài học T2-MOM được áp dụng ngay ở tầng 1:**
- Với các tín hiệu cắt ngang, điều kiện sống sót tính trên **long top − short BTC** và **vào trễ 1 ngày**, không tính trên excess so với giỏ alt equal-weight.
- Excess so với giỏ EW vẫn được báo, nhưng chỉ để tham khảo.

## Dữ liệu
- **Binance:** Vision spot 1h BTCUSDT và ETHUSDT 2021-01 → 2026-09 (timestamp từ 2025 là µs). `d1.parquet` của SCREEN_WIDE gồm perp 1d và `fund_day`.
- **Coinbase:** BTC-USD và ETH-USD 1h (`api.exchange.coinbase.com`, phân trang 300 nến), cùng kỳ.
- **Upbit:** nến ngày KRW-* (bucket UTC 00:00–24:00; `trade_price` là close lúc 24:00 UTC, khớp mốc close ngày của Binance), từ 2021-01. Chỉ lấy các market đang niêm yết, map với perp Binance theo base coin; perp kiểu `1000X` thì chia giá cho 1000.
- **Bybit:** funding history linear USDT, chỉ các symbol đang niêm yết và trùng với Binance. Gộp theo ngày UTC.
- **Kỳ:** E = 2021-03-01 → 2023-12-31; C = 2024-01-01 → 2026-09-30.

**Giới hạn biết trước: survivorship.** Upbit và Bybit chỉ cho market đang niêm yết, nên coin bị delist khỏi Upbit/Bybit bị loại khỏi universe CV3/CV4. Nếu tín hiệu nào sống sót, tầng 2 phải đánh giá lại ảnh hưởng này.

## Tín hiệu (dấu giả thuyết cố định trước)

**CV1 — Coinbase premium**
- Công thức: `CP_t = ln(CB_BTCUSD_close / BN_spot_BTCUSDT_close)` theo giờ. `CPd = CP − mean(CP, 168 giờ trước, tính cả t)`; bỏ phần level để khử độ lệch peg USDT.
- Giả thuyết: premium dương nghĩa là dòng tiền Mỹ đang mua, BTC sẽ tăng.
- **CV1a:** long BTC perp từ close giờ t tới close giờ t+1 nếu `CPd_t > 0`; ngược lại đứng ngoài. Phí tính theo số lần đổi trạng thái.
- **CV1b:** mỗi ngày lúc 00:00 UTC, long 24h nếu trung bình `CPd` của 24 giờ trước > 0.
- Báo kèm ETH (ETH-USD so với ETHUSDT), không tính vào tiêu chí.
- Báo thêm IC Spearman giữa `CPd_t` và lợi suất tương lai 1h / 4h / 24h. Mẫu 24h lấy không chồng (mỗi ngày một điểm lúc 00 UTC).

**CV2 — Kimchi premium BTC**
- Công thức: `KP_d = ln(Upbit_KRW-BTC_close / BN_perp_BTCUSDT_close)` theo ngày. `KPd = KP − median(KP, 30 ngày trước, không tính d)`; median đã khử phần tỷ giá KRW/USD.
- Giả thuyết contrarian: premium cao nghĩa là retail Hàn hưng phấn, BTC sẽ kém đi.
- **CV2a:** long BTC 24h tiếp theo nếu `KPd_d < 0`.
- **CV2b:** mỗi thứ Hai, long BTC 7 ngày nếu `KPd` của Chủ nhật < 0.
- Báo IC giữa `KPd` và lợi suất tương lai 1d / 7d (mẫu không chồng).

**CV3 — Premium tương đối của Upbit, cắt ngang (rebalance hàng tuần như họ X)**
- Công thức: `RP_i = mean 7 ngày [ln(Up_i/BN_i) − ln(Up_BTC/BN_BTC)]`. Không cần tỷ giá vì so với BTC.
- Giả thuyết: coin bị retail Hàn pump (RP cao) sẽ kém trên Binance tuần sau.
- **CV3-LO:** long decile RP THẤP nhất.
- **CV3-LS:** decile thấp nhất − decile cao nhất.
- **CV3b (attention):** `A_i = KRW turnover 7 ngày trên Upbit / (Up_BTC/BN_BTC) / qv perp 7 ngày của Binance`. LO long decile A thấp; LS thấp − cao.

**CV4 — Độ lệch funding Binance − Bybit, cắt ngang hàng tuần**
- Công thức: `FD_i = Σ 7 ngày (fund_bn_day − fund_bybit_day)`.
- Giả thuyết: long trên Binance bị đông bất thường so với Bybit nên coin sẽ kém.
- **CV4-LO:** long decile FD thấp. **CV4-LS:** thấp − cao.

**Universe CV3/CV4.**
- Lấy universe của họ X: qv30 ≥ 20M, niêm yết ≥ 60 ngày, không phải stablecoin.
- Giao với các coin có đủ 7 ngày dữ liệu Upbit (CV3) hoặc Bybit (CV4).
- Cần ≥ 20 coin, không đủ thì bỏ tuần đó. `n = max(3, N // 10)`.

## Thực thi và chi phí
- **TS (CV1, CV2):** giao dịch BTCUSDT perp, taker 0,05 %/chiều. Long trả funding thật (`fund_day`, chia đều theo giờ cho CV1a).
- **Cắt ngang (CV3, CV4):**
  - Tín hiệu dùng dữ liệu tới close Chủ nhật s. Vào ở close s+1 (trễ 1 ngày), thoát ở close s+8.
  - Chi phí alt 0,10 %/chiều theo turnover, BTC 0,06 %/chiều.
  - Funding thật. Ngày thoát không có close thì ffill.
  - **LO-H** = long decile − short BTC. Hedge rebalance tốn `|r_L − r_B| × 0,06 %`.
  - LS = 2 chân alt.
  - Báo thêm, chỉ để tham khảo: LO excess so với giỏ EW.

## Sống sót (lên tầng 2) — cùng thước với SCREEN_WIDE
Tính trên kết quả chính: TS ròng; cắt ngang dạng LO-H và LS.
1. Sharpe ròng E > 0,5.
2. Sharpe ròng C > 0,5.
3. Cùng dấu ở E và C.
4. Lãi ròng/năm ở C > 0.

Ledger cộng 10 (CV1a, CV1b, CV2a, CV2b, CV3-LO, CV3-LS, CV3b-LO, CV3b-LS, CV4-LO, CV4-LS). Với 10 phép thử, dự kiến khoảng 0,5 tín hiệu sống sót chỉ do may.

## Kiểm dữ liệu (FAIL thì dừng và báo)
- **D1:** Coinbase 1h phủ ≥ 99 % số giờ; Binance spot 1h phủ ≥ 99,5 %.
- **D2:** trung vị |CP| < 1 %, và correlation lợi suất giờ CB vs BN > 0,99.
- **D3:** Upbit KRW-BTC phủ ≥ 99 % số ngày; KP thô nằm trong [−10 %, +25 %] ở ≥ 99 % số ngày.
- **D4:** correlation funding ngày của BTCUSDT giữa Bybit và Binance > 0,7.
- **D5:** CV3 và CV4 mỗi cái có ≥ 200 tuần hợp lệ với N ≥ 20.
- **D6 (assert trong code):** feature chỉ dùng dữ liệu ≤ mốc tín hiệu; vào lệnh sau mốc tín hiệu.


## Addendum 1 (2026-10-16 21:40) — viết SAU lần chạy đầu, chỉ sửa kiểm dữ liệu và lọc dữ liệu ghép sai

**Công khai:** kết quả lần chạy đầu (`cvx_run.log`) đã được nhìn thấy trước khi viết addendum này. Không tín hiệu nào sống sót ở lần chạy đó. Addendum này KHÔNG đổi luật tín hiệu, tham số hay tiêu chí sống sót.

**1. Spec D3 sai.**
- `KP` thô = ln(KRW/USDT) ≈ 7,2, vì công thức đã gộp cả tỷ giá; tỷ giá chỉ được khử khi trừ median ở bước sau. Do đó điều kiện "KP thô trong [−10 %, +25 %]" không bao giờ đúng.
- D3 được thay bằng: `KPd` nằm trong [−10 %, +25 %] ở ≥ 99 % số ngày. Kết quả chẩn đoán: 100 % (q01 −4,9 %, q99 +7,2 %).
- Thay đổi này không ảnh hưởng tới CV2.

**2. CV3/CV3b có ghép token sai.** Một số coin cùng ticker trên Upbit và Binance nhưng là token khác nhau, hoặc khác mệnh giá (`upbit_match_diag.csv`):
- META có median |lr| 11,2.
- BTT 6,9 (khác mệnh giá BTT/BTTC).
- STRAX 3,1; RAY 2,1; EDGE 1,9; SNT 0,18; SC 0,13.
- Một số coin có giai đoạn ticker bị tái sử dụng: CVC, KAVA, ORBS.

**Luật lọc cơ học** (dựa trên tính hợp lệ của dữ liệu, không dựa trên hiệu suất):
- (a) Loại cả symbol nếu median |lr| > 5 % hoặc correlation lợi suất ngày Upbit vs Binance < 0,80.
- (b) Loại coin-ngày có |lr| > 50 %.

Áp dụng cho cả CV3 và CV3b, sau đó chạy lại toàn bộ `cv_run.py`. Các phần khác tất định nên không đổi. Báo cả kết quả lần đầu lẫn kết quả sau khi lọc.
