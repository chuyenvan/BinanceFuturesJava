# PREREG GRID T1 — grid trading có cửa không: kiểm tiền đề VR + grid có luật vào/ra + control random-walk

- **Ngày viết:** 2026-10-23 (giờ Asia/Saigon), commit TRƯỚC khi tính bất kỳ PnL nào.
- **Nguồn yêu cầu:** MASTER Claude, task `grid` ngày 10-23. Owner: cộng đồng chia sẻ grid trong vùng S/R, size cố định, cắt lỗ cứng, tắt khi trend.
- **Bối cảnh:** họ G của `RESULT_SCREEN_WIDE_T1` (G1/G1b/G1c) đều âm; owner cho rằng luật vào/ra chưa đủ tốt. Task này kiểm lại từ nền lý thuyết.
- **Nền lý thuyết:** grid trên random walk có kỳ vọng 0 trước phí (arXiv 2506.11921, Chen–Chen–Jang). Edge chỉ có nếu giá mean-revert ở thang bước lưới.
- **Repo:** `~/claude_master/vz_e1_wt`, nhánh `research/vz-e1`.
- **Code:** `research/grid_t1/` (g_data.py, grid_engine.c, g_run.py, g_vr.py, g_report.py).
- **Output:** `docs/result/GRID_T1.md` + `docs/result/grid_t1/` (JSON nhỏ, không kèm dữ liệu lớn).

Luật bất biến: **không đổi tham số/ngưỡng sau khi đã xem PnL**. Mọi thay đổi phải là addendum commit trước khi chạy lại, và ghi rõ.

---

## 1. Dữ liệu

- Nguồn: Vision UM kline 1m có sẵn trên Oracle `~/vz_e1/raw/kline1m-YYYY-MM.parquet` (2021-12 → 2025-12, 49 file tháng). Không tải dữ liệu lớn về Oracle.
- Funding: file tĩnh `data.binance.vision/data/futures/um/monthly/fundingRate/<SYM>/<SYM>-fundingRate-YYYY-MM.zip` (được phép: file tĩnh, không REST). Nếu một tháng thiếu file → funding tháng đó = 0 và ghi nhận vào mục bất thường.
- Tài sản nền: BTCUSDT, ETHUSDT.
- Alt: top 10 theo **quote volume point-in-time**. Quy tắc: tại mỗi tháng M, xếp hạng các symbol (trừ BTC/ETH) theo trung bình ngày của `quote_volume` trong tháng M−1, yêu cầu `ndays ≥ 25` trong tháng M−1; lấy top 10 cho tháng M. Rổ của tháng M = BTC + ETH + top 10 đó. Symbol delist vẫn được giữ nếu đủ điều kiện ở tháng xếp hạng; giao dịch dừng tại bar cuối cùng có dữ liệu.
- Universe của một kỳ = hợp các symbol từng nằm trong rổ tháng của kỳ đó (danh sách dưới đây chốt tại commit này).
- Kỳ **E = 2022-01-01 → 2023-12-31**, **C = 2024-01-01 → 2025-12-31** (UTC). 2021-12 chỉ dùng warmup 14 ngày đầu E. **HO 2026 không đụng.**

### 1.1 Universe chốt

E (63): 1000BONKUSDT, 1000LUNCUSDT, 1000PEPEUSDT, 1000SHIBUSDT, ADAUSDT, APEUSDT, APTUSDT, ARBUSDT, ARPAUSDT, ATOMUSDT, AVAXUSDT, AXSUSDT, BCHUSDT, BLURUSDT, BLZUSDT, BNBUSDT, CFXUSDT, CHZUSDT, COMPUSDT, CYBERUSDT, DOGEUSDT, DYDXUSDT, EOSUSDT, ETCUSDT, FILUSDT, FTMUSDT, FTTUSDT, GALAUSDT, GALUSDT, GASUSDT, GMTUSDT, IDUSDT, INJUSDT, LINAUSDT, LINKUSDT, LPTUSDT, LTCUSDT, LUNAUSDT, MANAUSDT, MASKUSDT, MATICUSDT, MEMEUSDT, MTLUSDT, NEARUSDT, OPUSDT, ORDIUSDT, PERPUSDT, RNDRUSDT, RVNUSDT, SANDUSDT, SOLUSDT, SUIUSDT, SXPUSDT, TIAUSDT, TRBUSDT, TRXUSDT, UNFIUSDT, WAVESUSDT, WLDUSDT, XLMUSDT, XRPUSDT, YGGUSDT, ZILUSDT

C (57): 1000BONKUSDT, 1000FLOKIUSDT, 1000PEPEUSDT, 1000SATSUSDT, 1000SHIBUSDT, AAVEUSDT, ADAUSDT, ALPACAUSDT, APEUSDT, ARBUSDT, ASTERUSDT, AUCTIONUSDT, AVAXUSDT, BCHUSDT, BEATUSDT, BNBUSDT, BOMEUSDT, COAIUSDT, DOGEUSDT, DOGSUSDT, ENAUSDT, FARTCOINUSDT, FILUSDT, GIGGLEUSDT, HBARUSDT, HIGHUSDT, HYPEUSDT, LIGHTUSDT, LINKUSDT, LTCUSDT, MOODENGUSDT, MYXUSDT, NEIROETHUSDT, NEIROUSDT, NOTUSDT, OPUSDT, ORDIUSDT, PENGUUSDT, PEOPLEUSDT, PIPPINUSDT, PNUTUSDT, PUMPUSDT, REEFUSDT, SEIUSDT, SOLUSDT, SUIUSDT, TONUSDT, TRBUSDT, TRUMPUSDT, WIFUSDT, WLDUSDT, WLFIUSDT, XLMUSDT, XPLUSDT, XRPUSDT, ZECUSDT, ZROUSDT

---

## 2. Bước 0 — kiểm tiền đề (quyết định có cơ sở lý thuyết)

Trên close 1m của từng tài sản, từng kỳ E/C:

1. **Variance ratio Lo–MacKinlay** cho q ∈ {5, 15, 60, 240, 1440} phút:
   `VR(q) = Var(r_t(q)) / (q · Var(r_t(1)))`, dùng return log 1m, cửa sổ chồng lấn, variance theo công thức dị phương sai (heteroskedasticity-robust, Lo–MacKinlay 1988):
   `z(q) = (VR(q) − 1) / sqrt(θ(q))`, θ theo Newey–West với trọng số Bartlett và độ trễ `q−1`.
2. **Autocorr lag-1** của return log ở thang 5m, 15m, 1h, 4h, 1d (returns không chồng lấn).

Gate tiền đề (chốt trước): **PASS** nếu ở CẢ E và C, ≥ 50 % số tài sản của kỳ có `VR(q) < 1` với `z(q) < −1,96` tại ít nhất một q ∈ {60, 240, 1440} (1h/4h/1d — thang gần với thời gian vượt một bước lưới 1–3 %). Ngược lại **FAIL**.
- FAIL ⇒ verdict chắc chắn NO-GO về mặt lý thuyết. Bước 1 vẫn được chạy và báo cáo như *chẩn đoán mô tả* (để có bảng theo yêu cầu), không dùng để cứu grid.
- PASS ⇒ Bước 1 là phép thử quyết định.

Ghi chú: VR z-stat trên 2 năm dữ liệu 1m rất nhạy; báo cáo cả median VR và % tài sản significant theo từng q, không chỉ p-value.

---

## 3. Bước 1 — hai cấu hình cố định, không tune

### 3.1 Khung chung

- Mỗi tài sản một tài khoản con vốn cố định `M = 1` (đơn vị chuẩn hoá), **không đòn bẩy, gross ≤ 1×**.
- Vào/ra bằng limit; **chỉ khớp khi giá xuyên mức**: mua khớp nếu `low < mức mua`, bán khớp nếu `high > mức bán`. Mỗi mức tối đa 1 lần khớp mỗi bar 1m.
- Thứ tự trong bar 1m: nếu `close ≥ open` xử lý `low` (mua) trước rồi `high` (bán); nếu `close < open` xử lý `high` (bán) trước rồi `low` (mua).
- Phí chính: **maker 0,02 %/chiều**. Biến thể bắt buộc: **taker 0,05 %/chiều** (mọi lần khớp, kể cả limit).
- Các lệnh buộc phải đóng (stop, tắt lưới, kết thúc kỳ, delist) khớp tại close của nến quyết định với phí **taker 0,05 %** ở bản chính.
- Funding: trừ/ cộng **funding thật** trên notional tồn kho tại đúng timestamp funding (long trả khi rate > 0). Không nội suy.
- Không có slippage/queue ngoài phí; đây là giả định lạc quan cho grid và được ghi nhận.
- Equity đánh giá mỗi phút = cash + tồn kho × close; chốt sổ ngày tại 00:00 UTC.

### 3.2 G-RANGE — lưới số học trong vùng 14 ngày, cắt lỗ cứng

Tham số duy nhất (không tune):
- Vùng: `lo = min(low 1h)` và `hi = max(high 1h)` của **336 nến 1h gần nhất** (14 ngày) tính đến thời điểm dựng lưới.
- Bước `s = (hi − lo)/10`; 11 mức `lo + i·s`, i = 0..10.
- Size mỗi lot = `M/10` (tối đa 10 lot ⇒ gross ≤ 1). Mua tại mức i = 0..9; lot mua ở mức i được bán tại mức i+1.
- Dựng lưới: bật các lệnh mua tại mọi mức `< giá hiện tại`; chưa có tồn kho ban đầu (long-only, toàn cash).
- Cắt lỗ cứng: tại close nến 1h, nếu `close < lo − s` → đóng toàn bộ tồn kho tại close (taker), tắt lưới.
- Tắt khi trend: tại close nến 1h, nếu `close > hi + s` → đóng toàn bộ tồn kho tại close (taker), tắt lưới.
- Lọc trend: `ADX(14)` trên nến 4h (Wilder). Chỉ bật lưới khi `ADX < 20`. Nếu đang bật mà tại close 4h `ADX ≥ 20` → đóng toàn bộ tồn kho, tắt lưới.
- Dựng lại: sau khi tắt, chờ đủ **24h**, sau đó tại mỗi close 1h: nếu `ADX < 20` và giá nằm trong `[lo, hi]` của vùng 14 ngày mới → dựng lưới mới. Nếu không, tiếp tục chờ (kiểm lại mỗi giờ).
- Đầu kỳ: dựng lưới tại 00:00 UTC ngày đầu kỳ nếu đủ 14 ngày warmup và điều kiện ADX/giá thoả.

### 3.3 G-DYN — luật dynamic grid của paper 2506.11921

Cài đặt theo **đúng thuật toán paper** (Algorithm 1 + §1.1, §3.1), không thêm luật riêng:
- Lưới quanh giá trung tâm `P0`, `half = 5` ⇒ `n = 10` khoảng, 11 mức.
  - **Biến thể chính G-DYN-g (theo text paper: geometric):** `level_i = P0·(1+k)^(i−half)`, i = 0..10, `k = 0,02`.
  - **Biến thể phụ G-DYN-a (theo code release của tác giả: arithmetic):** `level_i = P0 + (i−half)·P0·k`, cùng k.
- Vốn lưới `M = 1`. Tại P0 (mức giữa): mua `M·half/n = 0,5M` bằng coin, giữ `0,5M` cash.
- Khi giá tăng vượt mức đang đứng lên mức trên: bán `1/G_i` lượng coin đang giữ, với `G_i` = số thứ tự mức đó **đếm từ đỉnh** (đỉnh = 1 ⇒ bán 100 %).
- Khi giá giảm vượt mức xuống mức dưới: dùng `1/G_j` lượng cash đang giữ để mua, với `G_j` = số thứ tự mức đó **đếm từ đáy** (đáy = 1 ⇒ dùng 100 % cash).
- **Reset khi vượt biên trên:** bán toàn bộ coin còn lại tại giá vượt biên (taker), thu hồi đủ vốn `M` để mở lưới mới quanh giá hiện tại; phần lãi còn lại nằm trong cash và được ghi nhận là lợi nhuận đã thực hiện.
- **Reset khi vượt biên dưới:** **giữ coin** (không bán), mở lưới mới quanh giá hiện tại với vốn = lợi nhuận grid tích luỹ kể từ lần reset gần nhất. Nếu vốn đó `< 1 % M`, dùng `1 % M` và phần thiếu được ghi là vốn nạp thêm (làm tăng mẫu số lợi suất — trung thực với hành vi “averaging down” của code tác giả).
- Không cắt lỗ, không lọc ADX, không tắt lưới: đây là bản “hold coin + grid” đúng như paper. Funding trừ trên notional coin đang giữ.
- Chỉ số quyết định là **G-DYN-g**; G-DYN-a chỉ báo cáo chẩn đoán (không dùng để cứu/đổi verdict).

### 3.4 Rổ & metric

- Rổ đều trọng số **rebalance hằng ngày** trên các tài sản đang nằm trong rổ tháng: `r_p,t = mean_a r_a,t` (tài sản không có bar hôm đó bị loại).
- Sharpe = mean/std(daily return)·√365; CAGR từ equity ngày; maxDD trên equity ngày; tuần tệ nhất = min tổng lợi suất 7 ngày.
- Báo cáo gross (không phí/funding) và net (maker, có funding), cùng bản taker.
- Tương quan ngày với equity crash-buy X14 DEV: `~/claude_master/tsx/deep_cache/eq_dev.npz`, chuỗi `X14_<seed>`, DAY0 = 2021-07-01, mỗi điểm = 1 ngày; lấy trung bình cộng 8 seed đã chuẩn hoá về 1 tại DAY0 rồi tính lợi suất ngày. Kỳ tính: E và C.
- PnL trong các đợt sập: các cửa sổ trong `pairs_t1_report.py` (LUNA 2022-05, 3AC 2022-06, FTX 2022-11, 2024-04, 2024-08-05, 2025-02-03, 2025-03, 2025-10-10).

---

## 4. CONTROL random-walk (bắt buộc)

- Với mỗi tài sản, mỗi kỳ: bootstrap **block** các bar 1m, block = **60 bar (1h)**, lấy mẫu có hoàn lại từ chính chuỗi bar của tài sản trong kỳ đó.
- Mỗi bar được biểu diễn bằng 4 tỷ lệ so với close trước: `open/prev_close`, `high/prev_close`, `low/prev_close`, `close/prev_close`; ghép block và nhân dồn từ giá mở đầu kỳ ⇒ giữ vol/fat-tail và hình dạng intraday, phá tự tương quan giữa các block.
- Chạy **60 seed**/tài sản/kỳ; mỗi seed là một đường giá giả lập độc lập. Áp dụng **đúng** luật G-RANGE và G-DYN (range/ADX tính lại trên chuỗi giả lập; funding dùng đúng chuỗi funding thật theo timestamp — không phụ thuộc giá).
- Với mỗi seed, tính Sharpe rổ theo cùng membership tháng ⇒ phân phối control. Ngưỡng: **p95** của phân phối control theo từng kỳ.
- Báo cáo `% control vượt Sharpe thật` và vị trí percentile của thật.
- Robustness (không quyết định): block = 1440 bar (1 ngày), 20 seed, báo cáo phụ.

---

## 5. Tiêu chí SỐNG (chốt trước, không đổi)

Grid sống chỉ khi **tất cả** đúng:
1. Net Sharpe (maker) **≥ 1,0 ở CẢ E và C** trên rổ đều trọng số.
2. Net Sharpe thật **> p95 control** ở cả E và C.
3. maxDD **≤ 20 %** ở cả E và C.
4. **Dương ở bản taker**: net Sharpe (taker 0,05 %) > 0 ở cả E và C.
5. **Không phụ thuộc 1 tài sản**: bỏ bất kỳ 1 tài sản nào (leave-one-out) vẫn có net Sharpe ≥ 0,5 ở cả E và C.

Bước 0 FAIL ⇒ thêm điều kiện lý thuyết không thoả ⇒ NO-GO dù Bước 1 có số đẹp.

Không đạt ⇒ **đóng họ grid**, không thử biến thể khác trong task này. Không đổi ngưỡng, không thêm tham số, không chọn lại universe.

---

## 6. Đầu ra & cách báo cáo

- `docs/result/GRID_T1.md`: hash prereg, bảng VR (median VR, % significant theo q, E|C), bảng G-RANGE/G-DYN (gross/net Sharpe E|C, CAGR, maxDD, tuần tệ nhất, % control vượt, p-value empirical), verdict, bất thường.
- `docs/result/grid_t1/`: script + JSON nhỏ (metrics, control distribution summary, universe, funding gaps). Không commit parquet lớn.
- Payload cuối: việc đã làm, số chính, hash prereg/result, commit hash, mọi bất thường/lệnh bị chặn.

## 7. Rủi ro đã biết (ghi trước)

1. Khớp limit khi giá chỉ *chạm* mức (low < mức) là lạc quan; thực tế queue có thể không khớp. Bản taker là biên dưới chi phí, không phải biên dưới queue.
2. Funding lấy từ file tháng; tháng thiếu = 0 (sẽ liệt kê).
3. Delist: đóng tồn kho tại bar cuối; nếu bar cuối thanh khoản kém, đây là giả định lạc quan.
4. 1m OHLC không cho biết thứ tự thật trong bar; quy ước ở §3.1 là cố định.
5. Membership tháng dùng quote volume tháng trước ⇒ không nhìn trước, nhưng có độ trễ 1 tháng.
6. Paper 2506.11921 là **spot**; áp lên perp có funding là phép thử khắc nghiệt hơn, đúng theo yêu cầu task.
