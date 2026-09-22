# PREREG_TREND_REGIME_DIAG — khoá định nghĩa/metric/cổng TRƯỚC khi tính số (2026-09-21)

TASK B2 Bước 5, Bước 1 (`TASK_B2_step5_trend_detector_regime.md` §BƯỚC 1). Mục tiêu: đo detector
production `TrendDetector.isBtc/EthTrendBuyProduction` (lấy lại từ commit `157cf4d`, đã xoá ở HEAD)
làm regime filter thay MA200-trailing, HOÀN TOÀN 0-sim (không Java, không xgboost, không build).
Khoá theo §0 luật của round: PREREG trước, HOLDOUT 2026 bị loại bởi loader (`ts<2026-01-01`),
không sửa `bigdown_struct.py`/`c3_rates.py`/`trend_rank_ic.py`/`uw_source.py` gốc.

## 1. Xác nhận code detector gốc (đã đọc `git show 157cf4d:...`, CHỈ ĐỌC)

- `TrendDetector.isBtcTrendBuyProduction(time)` / `isETHTrendBuyProduction(time)`:
  `up(t) = (SMA_SHORT_1d(t) - SMA_LONG_1d(t) > 0) OR (SMA_SHORT_4h(t) - SMA_LONG_4h(t) > 0)`.
  Tên hàm Java gọi nhầm là "Ma10AndMa60" nhưng SMA period thật đọc từ
  `Configs.SMA_SHORT`/`Configs.SMA_LONG` (`Configs.getInt(...)`), và `config.properties` hiện tại
  VÀ ở `157cf4d` đều có `SMA_SHORT=7`, `SMA_LONG=100` — xác nhận đúng như đề bài (SMA7/100).
- `SimpleMovingAverage.calculate(candles, periods)`: `results[i] = avg(candles[i-periods+1..i])` khi
  `i>=periods` (đủ N nến kể cả nến hiện tại `i`), ngược lại `= 0` (không đủ dữ liệu).
- `SimpleMovingAverageDayManagerProduction`/`...4hManagerProduction.updateForSymbol`: SMA tính trên
  nến `ticker.startTime = S`, giá trị lưu tại khoá `S + 1 ngày` (1D) hoặc `S + 4h` (4H). Truy vấn
  `getDifferenceMa10AndMa60(symbol, t)` dùng khoá `Utils.getDate(t)` (1D) / `Utils.get4Hour(t)` (4H).
  `Utils.getDate(t) = floor(t/86400000)*86400000` (biên ngày UTC-epoch, KHÔNG lệch giờ);
  `Utils.get4Hour(t) = floor(t/14400000)*14400000` (biên 4h UTC-epoch: 00/04/08/12/16/20h).
  ⇒ giá trị hiệu lực cho MỌI thời điểm `t` trong ngày UTC D (hoặc bucket 4h B) là SMA tính từ nến đã
  ĐÓNG kết thúc tại D-1 (hoặc B-1) — **causal, không lookahead**, đúng như thiết kế mô tả.

## 2. Tái hiện Python (causal, 0-sim)

- Nguồn: `research/analysis/trend_rank_ic.load_closes()` NGUYÊN VĂN (không sửa) — đọc
  `/home/ubuntu/java/fsrun/CLOSES_1H.bin`, lọc `ts < 2026-01-01` (SEAL_2026, đúng HOLDOUT rule),
  `ctime = ts + 1h` (quy ước close-time). BTC = symId 1, ETH = symId 2
  (`/home/ubuntu/selector_pred_out/symbol_map.csv`).
- **Chuỗi ngày (1D)**: `daily_close[D] = close 1h cuối cùng trong [D, D+1 ngày)` theo biên
  `Utils.getDate` (UTC). **Chuỗi 4H**: `close4h[B] = close 1h cuối cùng trong [B, B+4h)` theo biên
  `Utils.get4Hour` (UTC).
- **Quy ước "detector_up cho ngày D"** (một giá trị/ngày, để so trực tiếp với chuỗi MA200 của
  `regime_build_ma200.py`): đánh giá TẠI THỜI ĐIỂM ĐẦU NGÀY D (00:00 UTC) — dùng nến 1D đã đóng gần
  nhất (ngày D-1) và nến 4H đã đóng gần nhất (bucket 20:00-24:00 UTC của ngày D-1):
  ```
  SMA7_1d(D)  = mean(daily_close[D-7 .. D-1]);   SMA100_1d(D) = mean(daily_close[D-100 .. D-1])
  SMA7_4h(D)  = mean(close4h[B(D)-7 .. B(D)-1]); SMA100_4h(D) = mean(close4h[B(D)-100 .. B(D)-1])
    (B(D) = bucket 00:00-04:00 UTC của ngày D; B(D)-1 = bucket 20:00-24:00 UTC ngày D-1)
  up_1d(D) = SMA7_1d(D) - SMA100_1d(D) > 0 ;  up_4h(D) = SMA7_4h(D) - SMA100_4h(D) > 0
  detector_up(D) = up_1d(D) OR up_4h(D)
  ```
  Đây là causal (chỉ dùng nến đã đóng < D), nhất quán với `not_up_ma200(D)` của
  `regime_build_ma200.py` (cũng dùng `close[D-1]`) — cho phép so % ngày up/năm 1-1.
- **Giới hạn phương pháp (ghi rõ, chấp nhận cho nghiên cứu)**: `daily_close`/`close4h` là RESAMPLE
  từ lưới 1H, không phải kline 1D/4H gốc của Binance. Với dữ liệu liên tục (không gap), close tại
  đúng biên ngày/4h trùng với kline gốc; sai khác có thể xảy ra nếu lưới 1H có gap đúng tại biên
  (dùng candle 1h gần nhất ≤ biên tiếp theo, tương đương "close cuối kỳ" nên lệch tối thiểu).
  SMA của close-resample có thể lệch nhẹ so với SMA của kline gốc nếu có gap hệ thống; không ảnh
  hưởng tính causal.
- **BTC/ETH/BTC-OR-ETH**: tính riêng `detector_up_BTC(D)`, `detector_up_ETH(D)`, và biến thể
  `detector_up_BTCORETH(D) = detector_up_BTC(D) OR detector_up_ETH(D)`. Regime CHÍNH đề xuất cho
  phán quyết GO/NO-GO là **BTC** (thị trường dẫn, đúng ý thiết kế); ETH và BTC-OR-ETH chỉ báo cáo
  mô tả thêm cho MASTER chọn.
- Cấu hình CHÍNH khoá theo production gốc: `SMA_SHORT=7, SMA_LONG=100, khung={1D,4H}, OR`.
  KHÔNG nhặt tham số từ sweep.

## 3. Metric đo (khoá thứ tự, đúng §1.2 thiết kế)

1. **% ngày detector_up mỗi năm 2021-2025** (BTC, ETH, BTC-OR-ETH), so cạnh số MA200 đã có (Bước 4):
   2021=64.7%, 2022=0%, 2023=80.3%, 2024=80.1%, 2025=73.4%. Câu chính: **detector (BTC) gọi 2025
   up bao nhiêu %?** Kỳ vọng < 73.4% (bắt bull-nhiễu tốt hơn MA200).
2. **% phủ not-up của 2 chuỗi UW dài** (đã xác định ở TASK B2 Bước 1/chẩn đoán UW-2025, KHÔNG tính
   lại): UW-2022 = gate-1.0/P3, `2021-11-16 → 2022-07-21` (248 ngày); UW-2025 = gate-1.0/T100
   (`X1_C3_FULL_2021`), `2025-03-04 → 2025-10-16` (227 ngày). Tính `% ngày detector_up=False` trong
   MỖI cửa sổ, cho BTC/ETH/BTC-OR-ETH.
3. **Edge độc lập (không qua sim)**:
   - forward return BTC 1D và 7D theo ngày D, dùng `daily_close`: `fwd1(D)=close(D)/close(D-1)-1`,
     `fwd7(D)=close(D+6)/close(D-1)-1` (return "ngày D" và "7 ngày kể từ đầu ngày D", đúng ý nghĩa
     causal của `detector_up(D)` — biết TRƯỚC khi ngày D bắt đầu). So trung bình theo
     `detector_up(D)` (BTC detector) = True vs False, kèm N và std.
   - ROI trung bình + tỷ lệ thua của sổ T100 (`X1_C3_FULL_2021`, `bigdown_struct.load_trades_utc`
     NGUYÊN VĂN) gán theo `detector_up` của NGÀY MỞ LỆNH (BTC detector); CI90 block-bootstrap 72h
     (`bigdown_struct.block_boot_mean` NGUYÊN VĂN, seed/nrep như file gốc); `phi` đồng-thua
     (`bigdown_struct.phi_for` NGUYÊN VĂN) theo nhóm up/not-up.
4. **Sweep MÔ TẢ (KHÔNG chọn winner)**: lưới `SMA_LONG ∈ {50,100,150,200}` × khung
   `{1D-only, 4H-only, 1D+4H-OR}`, `SMA_SHORT=7` cố định, detector BTC. Vẽ "% ngày 2025 gọi
   not-up" theo tham số — CHỈ để hiểu độ nhạy, cấu hình gốc (7/100/1D+4H-OR) là cái DUY NHẤT dùng
   cho phán quyết mục 4 dưới.

## 4. Cổng GO/NO-GO (khoá TRƯỚC khi tính số — §1.3 thiết kế, KHÔNG đổi sau khi thấy số)

- **GO** nếu: `%not-up` (detector BTC, cấu hình gốc 7/100/1D+4H-OR) trong cửa sổ UW-2025 **≥ 60%**
  VÀ trong cửa sổ UW-2022 **≥ 60%** (bắt được CẢ HAI giai đoạn — điều MA200 không làm được với
  2025, vì MA200 gọi UW-2025 hầu như toàn bộ là up).
- **NO-GO** nếu: detector gọi UW-2025 phần lớn vẫn là up (tức `%not-up(UW-2025) < 60%`), giống
  MA200 → không hơn MA200, dừng Bước 2, ghi power_wall.
- Ngưỡng 60% là quy ước theo lý lẽ (đủ phủ để một gate chặt cắt phần lớn phơi nhiễm xấu trong cửa
  sổ), khoá trước khi xem số, không điều chỉnh sau.
- Ghi rõ: cổng dùng CHỈ detector BTC/cấu hình gốc; số của ETH/BTC-OR-ETH/sweep là mô tả bổ sung,
  không dùng để đổi verdict GO/NO-GO của bước này.

## 5. Đầu ra

`research/analysis/trend_regime.py` (mới, tái dùng nguyên văn `trend_rank_ic.load_closes`,
`bigdown_struct.load_trades_utc/block_boot_mean/phi_for`, không sửa các file gốc) +
`research/analysis/out/trend_regime.json` + `docs/DIAG_TREND_REGIME.md` (kết quả + GO/NO-GO).
Dùng `logging`, cấm `print()`.
