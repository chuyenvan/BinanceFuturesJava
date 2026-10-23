# PREREG LIQX_S0 — Bước 0: proxy thanh lý từ Vision có đo đúng thanh lý thật không

Ngày: 2026-10-24. Agent: liqx0 (Opus). Thiết kế: MASTER. Đây là phép VALIDATE ĐO LƯỜNG — không PnL, không IC lợi nhuận, không đụng X14 printDone.
Commit file này TRƯỚC khi tính bất kỳ tương quan proxy–thanh lý nào. Đã xem trước: schema, độ phủ, ngữ nghĩa thời gian (không tương quan proxy–liq).

## 1. Dữ liệu (đã kiểm schema/phủ)
- Vision metrics 5m (đóng gói): `~/vz/out/metrics5m/YYYY/YYYY-MM.parquet`, cột `ts` = create_time ms int64, `oi` = sum_open_interest (HỢP ĐỒNG), `oi_value` = sum_open_interest_value (USD). 289 ts/symbol/ngày khi lọc [D, D+24h] (ts mod 300000 = 0, không trùng).
- Ngữ nghĩa create_time (kiểm bằng dữ liệu): so `oi` BTCUSDT 2024-01-01 với Tardis `derivative_ticker.open_interest` (≈1 s/điểm): sai số tương đối median nhỏ nhất ở lệch L = 0…+15 s (2,6e-5 / 1,9e-5), tăng đều hai phía (±60 s: ~1e-4; ±300 s: ~4e-4) ⇒ OI tại create_time T là SNAPSHOT tại ~T. (2022-05-01: Tardis OI lệch hằng ~0,9 % mọi L — không kết luận được cho 2022; CHƯA GIẢI THÍCH, có thể Tardis 2022 lấy OI nguồn khác.)
- Kline 1m: `~/vz_e1/raw/kline1m-YYYY-MM.parquet` (`ts` = open_time ms, quote_volume, taker_buy_quote; 1440 bar/symbol/ngày có hàng cho cả phút không giao dịch, cờ active). PIT (có symbol đã delist).
- Thanh lý thật lịch sử: Tardis.dev free ngày-01, `https://datasets.tardis.dev/v1/binance-futures/liquidations/YYYY/MM/01/PERPETUALS.csv.gz` (grouped symbol = mọi perpetual binance-futures; kiểm: phần BTCUSDT của PERPETUALS 2022-01-01 trùng khớp file BTCUSDT riêng 1052/1052). 48 file, 29 MB, lưu `~/claude_master/liqx_wk/tardis/`. Cột: timestamp (µs, độ phân giải ms), side (`sell` = LONG bị thanh lý, `buy` = SHORT bị thanh lý — theo docs Tardis), price ("liquidation price as provided by exchange" — docs không nói là `p` hay `ap`), amount (base qty). Không có cột avg/filled ⇒ notional = price × amount.
- ĐẾM THIẾU: stream forceOrder chỉ phát ≤1 lệnh/symbol/giây (snapshot). Kiểm: max sự kiện/symbol/giây = 1 ở cả 2022-01-01 và 2025-12-01 ⇒ LIQ thật là CẬN DƯỚI, tỉ lệ thiếu tăng đúng lúc cascade.
- Forward: collector `~/collect/liq/<YYYY-MM-DD>.csv.gz` (event_time, symbol, side, order_type, price, avg_price, orig_qty, filled_qty, status, trade_time; ngày theo UTC). Collector kline1m KHÔNG có quote_volume/taker và chỉ subscribe symbol sau lần thanh lý đầu ⇒ không dùng được cho P2/P3/r5 (xem Lệch thiết kế).

## 2. Đơn vị bucket
- Per symbol, ngày D (UTC). Mốc T ∈ {D + k·300 000 ms, k = 1..288} (T = D+5′ … D+24h). Cửa sổ thời gian [T−300 000, T) ms (≡ (T−5′, T] ở độ phân giải 5′; dùng nửa mở trái-đóng để khớp đúng 5 nến 1m open_time T−5′…T−1′ và để một sự kiện chỉ thuộc 1 bucket).
- Mọi ts int64 ms UTC. Tardis timestamp µs → `//1000` int64.
- Bucket hợp lệ khi có đủ: oi_value(T−5′), oi_value(T) (khớp ts đúng), close của nến open_time T−360 000 và T−60 000, 5 nến open_time T−300 000…T−60 000. Thiếu ⇒ loại khỏi mọi thước đo, đếm trong V1.

## 3. Proxy (chốt)
- OIdrop_usd(T) = max(0, oi_value(T−5′) − oi_value(T)) [USD].
- r5(T) = ln close(T) / close(T−5′); close(T) = close nến open_time T−60 000; close(T−5′) = close nến open_time T−360 000.
- TSX(T) = max(0, Σ(quote_volume − taker_buy_quote) − Σ taker_buy_quote) trên 5 nến [USD].
- P1 = OIdrop_usd × 1[r5 < 0].
- P2 = min(OIdrop_usd, TSX).
- P3 = OIdrop_usd × TSX / Σ quote_volume × 1[r5 < 0]; Σ quote_volume = 0 ⇒ P3 = 0.
- Không lag thêm cho bất kỳ biến nào.

## 4. Tham chiếu
- LIQ_long(T) = Σ price × amount của dòng Tardis side = `sell` (long bị thanh lý), symbol trùng, timestamp_ms ∈ [T−5′, T). LIQ_short tương tự với side = `buy`.
- Forward F: notional = avg_price × filled_qty, side SELL = long, BUY = short, thời điểm = trade_time (ms). Chỉ status FILLED (ghi số dòng khác).
- Symbol: so khớp nguyên chuỗi; thanh lý ở cặp BUSD/USDC (vd BTCBUSD) KHÔNG gộp vào USDT (instrument khác).

## 5. Mẫu và universe
- A = ngày-01 tháng 2022-01…2023-12 (24 ngày); B = 2024-01…2025-12 (24 ngày).
- Universe ngày D: top-100 symbol theo Σ quote_volume kline 1m trên [D−30 ngày, D) từ kline parquet (PIT). Symbol không có kline/metrics ngày D ⇒ không có bucket (ghi số lượng, không lấp bằng hạng 101+).
- Tier (cho M5): hạng 1–10, 11–30, 31–100.
- F = 2026-10-16…2026-10-22 (ngày UTC đủ trọn collector và có Vision metrics daily). Mô tả, không dùng cho verdict.

## 6. Thước đo (từng proxy × từng mẫu; gộp mọi symbol-ngày của mẫu)
- M1: Spearman(proxy, LIQ_long) trên bucket hợp lệ có r5 < −0,01 (r5 log).
- M2: Spearman(proxy, LIQ_long) trên bucket có proxy > 0 hoặc LIQ_long > 0.
- M3: AUC (Mann–Whitney, ties = 0,5) phân loại "thanh lý lớn". Nhãn per symbol trong mẫu: q = percentile 99 (numpy linear) của LIQ_long trên mọi bucket hợp lệ của symbol đó trong mẫu; nếu q > 0: dương ⇔ LIQ_long ≥ q; nếu q = 0 (symbol quá ít sự kiện): dương ⇔ LIQ_long ≥ 1 000 000 USD. M3 = trung bình AUC per symbol có trọng số số dương (chỉ symbol có ≥1 dương và ≥1 âm). Phụ (không chấm): AUC gộp mọi bucket.
- M4: Spearman(proxy(T), LIQ_long(T+k·5′)), k ∈ {−3…+3}, cặp trong cùng symbol-ngày, tập con proxy(T) > 0 hoặc LIQ_long(T+k) > 0. ĐẠT ⇔ argmax tại k = 0. Chỉ chẩn đoán căn thời gian, không chọn lag.
- M5: OLS log1p(LIQ_long) ~ a + b·log1p(proxy) theo tier, trên tập con M2; báo b, R², n.
- M6: Spearman(proxy, LIQ_short) trên bucket proxy > 0 hoặc LIQ_short > 0. Phụ: M6 trên tập con M1.
- Mô tả: Σproxy / ΣLIQ_long (mọi bucket hợp lệ) — chỉ mô tả vì LIQ thật bị đếm thiếu.
- Chẩn đoán kích thước (không chấm): Spearman(oi_value(T−5′), LIQ_long) trên tập M1 (proxy "chỉ là kích thước symbol" sẽ cho số này cao), và M1 trong-symbol = trung bình Spearman per symbol (trọng số n, symbol có n ≥ 20).

## 7. TIÊU CHÍ ĐẠT (sang Bước 1)
Ít nhất 1 proxy thoả ĐỒNG THỜI: M1 ≥ 0,40 VÀ M3 ≥ 0,80 ở CẢ A và B; M4 đỉnh tại k = 0 ở cả A và B; M6 < 0,5 × M1 (ở cả A và B). Không đạt ⇒ NO-GO cho Bước 1 với proxy đó. F chỉ mô tả.

## 8. Validation
- V1: ts int64 mọi bảng (assert dtype); số bucket hợp lệ/symbol-ngày = 288 hoặc liệt kê thiếu; kline 1440/symbol-ngày; metrics trùng ts = 0.
- V2: tái lập ĐỘC LẬP M1 của P1 mẫu A bằng script tối giản viết lại (không import pipeline, đọc file thô trực tiếp, rank tự cài), |Δ| < 1e-9.
- V3: kiểm tay 5 bucket LIQ_long lớn nhất (A∪B): in OI USD, close, taker, các dòng thanh lý thật đọc thẳng từ file thô.
- V4: P1 tính cả bằng `oi` (hợp đồng): P1c = max(0, oi(T−5′) − oi(T)) × 1[r5<0]; báo M1/M3 của P1c cạnh P1 (USD). Verdict theo USD.
- V5: ngữ nghĩa create_time (mục 1) chạy lại thêm 1 ngày 2025 nếu Tardis derivative_ticker có OI.

## 9. Lệch thiết kế
- Cửa sổ [T−5′, T) thay (T−5′, T] (khác biệt chỉ ở biên 1 ms; để khớp nến 1m).
- F: collector kline1m thiếu quote_volume/taker_buy và chỉ có symbol sau lần thanh lý đầu ⇒ dùng Vision daily klines 1m (`data/futures/um/daily/klines/<SYM>/1m/`, ~60 KB/file) + Vision daily metrics cho F; collector kline chỉ để đối chiếu close (V). Universe F = top-100 theo Σ quote_volume tháng 2026-09 (Vision monthly klines 1d, ~2 KB/file) thay [D−30, D) vì kline 2026 không có trên Oracle. F bỏ 2026-10-15 (collector bắt đầu giữa ngày) và loại bucket nằm trong khoảng trống collector > 180 s không có sự kiện nào (log có ngắt "Too many requests" 10-19).
- M3 dùng AUC per symbol trọng số số dương (nhãn p99 là per symbol nên AUC gộp sẽ trộn quy mô symbol); AUC gộp báo kèm.
- M6 dùng tập con proxy>0 hoặc LIQ_short>0 (đối xứng M2) để bắt đúng trường hợp proxy kêu khi short bị quét.
