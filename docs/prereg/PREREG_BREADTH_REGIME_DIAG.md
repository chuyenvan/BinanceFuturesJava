# PREREG_BREADTH_REGIME_DIAG — khoá định nghĩa/metric/cổng TRƯỚC khi tính số (2026-09-21)

Đề xuất của Uni (khác nhánh trend-detector Bước 5.1 đã NO-GO): thử **market-breadth**
(% coin trên MA200 của CHÍNH nó — tín hiệu độ rộng/participation) làm regime filter, KHÁC LOẠI
tín hiệu với mọi detector hướng-giá BTC (MA200-BTC Bước 2/4, SMA-crossover Bước 5.1) đã thử và
đều NO-GO/NULL vì UW-2025 là bull-run-có-sóng-lớn (giá BTC vẫn +33%, không detector hướng-giá nào
gọi đó là "not-up" đủ). Giả thuyết: breadth thấp (ít coin tham gia uptrend) có thể phân biệt được
uptrend-khỏe (2023/24) khỏi uptrend-nhiễu (2025) — điều MA200/SMA-crossover không làm được.
HOÀN TOÀN 0-sim: không Java, không xgboost, không build, không sửa `.java`. Không đụng HOLDOUT
2026 (`ts<2026-01-01`, do loader gốc lọc sẵn). Không sửa `trend_rank_ic.py`/`bigdown_struct.py`/
`c3_rates.py`/`uw_source.py` gốc — chỉ tái dùng.

## 1. Nguồn dữ liệu & universe (đã recon, ghi rõ hạn chế)

- **Không có volume trong `CLOSES_1H.bin`**: đã xác nhận bằng đọc trực tiếp — file
  `/home/ubuntu/java/fsrun/CLOSES_1H.bin` có kích thước 144,513,404 byte, dtype đọc bởi
  `trend_rank_ic.load_closes()` là `(ts:int64, sym:int16, close:float32)` = 14 byte/record;
  144513404 / 14 = 10,322,386 record NGUYÊN (không dư) ⇒ xác nhận file CHỈ có 3 cột này, KHÔNG có
  volume ẩn. Nguồn volume thật (`CoinRankManager.java`: rank theo tổng volume 720 nến từ
  `HistoryManager` ring buffer, cập nhật hàng giờ qua Aerospike LIVE) đòi hỏi chạy JVM + Aerospike
  — VI PHẠM 0-sim (cấm build/run). File volume rời (`kaggle_data_hpo/ticker_YYYYMMDD.bin(.gz)`) là
  Java `ObjectOutputStream` serialize `TreeMap<Long,Map<String,KlineObjectSimple>>` — không đọc
  được bằng Python thuần không có JVM/thư viện deserialize Java, và không có artifact
  `ExportCoinTierStatic` nào đã xuất sẵn trên đĩa để đọc lại (đã tìm, không thấy).
- **PROXY top-N đã chọn (ghi rõ, đúng §0 cho phép khi thiếu volume)**: dùng **symId 1..N theo
  `map_kaggle.csv`** (thứ tự symId = thứ tự Binance Futures NIÊM YẾT theo thời gian — symId nhỏ =
  niêm yết sớm). Đã xác nhận `map_kaggle.csv` symId 1-50 là các coin lớn/thanh khoản cao đã biết
  (BTC,ETH,BNB,ADA,DOGE,LINK,AVAX,SOL,MATIC,UNI,AAVE,ATOM,NEAR,SNX,...) — nhất quán về mặt
  face-validity với "top vốn hoá/thanh khoản sớm" dù KHÔNG phải xếp hạng volume rolling thật.
  **STATIC (không rolling theo tháng)** — lý lẽ chọn: (i) task cho phép chọn 1 trong 2 khi ghi rõ
  lý lẽ; (ii) static tránh mọi rủi ro lookahead-selection (chọn top-N theo hiệu suất/volume ĐÃ xảy
  ra trong quá khứ gần thời điểm t vẫn có thể method-overfit nhẹ nếu vô tình tương quan với hướng
  giá); (iii) đã xác nhận bằng recon symId 1-50 (trừ 2 ca) có dữ liệu ĐẦY ĐỦ suốt 2021-01-01 →
  2026-01-01 nên không cần cơ chế "rolling universe" phức tạp cho cấu hình CHÍNH.
- **Còn sống tại thời điểm t (causal, không lookahead survivorship)**: đã recon — symId 4
  (EOSUSDT) và 35 (MATICUSDT) trong nhóm 1-50 KHÔNG có dữ liệu đến hết 2025 (dừng sớm — hủy
  niêm yết/đổi symbol). Xử lý: coin `i` được tính "sống" tại ngày D nếu có close hợp lệ tại
  D-1 (dữ liệu daily causal); khi hết dữ liệu thì rớt khỏi mẫu số breadth từ ngày đó, KHÔNG
  backfill/lookahead. Không loại các coin này khỏi universe tĩnh — chỉ đơn giản chúng dừng đóng
  góp khi dữ liệu dừng, đúng ý "chỉ dùng coin còn sống tại t".

## 2. Định nghĩa (khoá, causal)

```
Universe = symId 1..50 (map_kaggle.csv, STATIC, xem §1)
Với mỗi coin i trong Universe, mỗi ngày UTC D:
  daily_close_i[D] = close 1h cuối cùng trong [D, D+1 ngày) UTC  (giống trend_regime.py Bước 5.1,
                     resample tu CLOSES_1H.bin qua to_period_series)
  ma200_i(D) = mean(daily_close_i[D-200 .. D-1])   (rolling causal, min_periods=30 — như
               regime_build_ma200.py, cho phep "chua du 200" o dau lich su, KHONG anh huong causal)
  alive_i(D) = daily_close_i[D-1] khong NaN  (con du lieu)
  up_i(D)    = alive_i(D) AND ma200_i(D) khong NaN AND daily_close_i[D-1] >= ma200_i(D)
  (coin khong "song" hoac chua du min_periods thi LOAI khoi mau so ngay do, khong tinh la up/down)

breadth(D) = 100 * (so coin up_i(D)=True) / (so coin alive_i(D) va co ma200 hop le)
not_up(D)  = breadth(D) < 50.0   [NGUONG CHINH, ly le: duoi nua thi truong tren MA200 = tham gia
                                   yeu -> regime "khong khoe", tuong tu logic MA200-BTC nhung do
                                   TREN CA THI TRUONG thay vi 1 dong BTC]
```

- Cửa sổ mô phỏng: `SIM0=2021-07-01`, `SIM1=2025-12-31` — TRÙNG với `trend_regime.py` (Bước 5.1)
  để so trực tiếp năm-với-năm.
- 2 chuỗi UW dài (KHÔNG tính lại, lấy nguyên văn từ Bước 1/chẩn đoán UW-2025):
  `UW2022 = 2021-11-16 → 2022-07-21` (248 ngày, gate-1.0/P3), `UW2025 = 2025-03-04 → 2025-10-16`
  (227 ngày, gate-1.0/T100).
- Cấu hình CHÍNH khoá cho cổng: **top-50, MA200, ngưỡng 50%**. Mọi biến thể khác (top-N khác,
  MA100, ngưỡng 40/60%) chỉ dùng cho sweep MÔ TẢ ở mục 4 — KHÔNG dùng để đổi verdict.

## 3. Metric đo (khoá thứ tự)

1. Chuỗi `breadth(D)` + `not_up(D)` mỗi năm 2021-2025 (n_ngày, %not-up), so cạnh:
   - MA200-BTC (Bước 2/4): not-up%/năm = 100 - {2021:64.7,2022:0.0,2023:80.3,2024:80.1,2025:73.4}
     = {2021:35.3,2022:100.0,2023:19.7,2024:19.9,2025:26.6}.
   - Trend-detector SMA7/100 BTC (Bước 5.1): not-up%/năm = 100 - {2021:79.3,2022:39.2,2023:86.8,
     2024:84.7,2025:67.4} = {2021:20.7,2022:60.8,2023:13.2,2024:15.3,2025:32.6}.
2. **CỔNG QUYẾT ĐỊNH — %phủ not-up 2 chuỗi UW** (cấu hình CHÍNH top50/MA200/50%): `%not_up` trong
   `UW2022` và trong `UW2025`. **GO nếu CẢ HAI ≥ 60%.** NO-GO nếu `UW2025 < 60%` (breadth cũng mù
   2025 như mọi detector hướng-giá trước ⇒ đóng vĩnh viễn hướng breadth-regime).
3. **Edge độc lập (không qua sim)**:
   - Forward BTC return 1D/7D theo `not_up(D)` (dùng `daily_close` BTC, symId 1, cùng công thức
     `fwd1/fwd7` như `trend_regime.py`) — so `up` (breadth≥50%) vs `notup` (breadth<50%), kèm N,
     mean, std.
   - ROI trung bình + tỷ lệ thua sổ T100 (`X1_C3_FULL_2021`, `bigdown_struct.load_trades_utc`
     NGUYÊN VĂN) gán theo `not_up` của NGÀY MỞ LỆNH; CI90 block-bootstrap 72h
     (`bigdown_struct.block_boot_mean` NGUYÊN VĂN); `phi` đồng-thua (`bigdown_struct.phi_for`
     NGUYÊN VĂN) theo nhóm up/not-up.
4. **Sweep MÔ TẢ (KHÔNG chọn winner)**: lưới top-N ∈ {30,50,100} (symId 1..N, cùng proxy §1) ×
   MA ∈ {100,200} × ngưỡng ∈ {40%,50%,60%} — vẽ "%phủ not-up UW-2025" (và UW-2022 để đối chiếu)
   theo tham số. Cấu hình chính (top50/MA200/50%) là ô DUY NHẤT trong lưới dùng để quyết định
   GO/NO-GO ở mục 2; các ô khác chỉ mô tả độ nhạy.

## 4. Cổng GO/NO-GO (khoá TRƯỚC khi tính số, KHÔNG đổi sau khi thấy số)

- **GO** nếu: `%not_up` (cấu hình CHÍNH top50/MA200/50%) trong `UW2022` **≥ 60%** VÀ trong
  `UW2025` **≥ 60%** — breadth phủ được CẢ HAI giai đoạn UW bằng MỘT cơ chế, điều mọi tín hiệu
  hướng-giá (MA200-BTC, SMA-crossover) đã thử đều KHÔNG làm được với UW-2025.
- **NO-GO** nếu: `%not_up(UW2025) < 60%` (breadth cũng mù 2025) — dừng, không làm sim, ghi
  power_wall, đóng vĩnh viễn hướng breadth-regime (đây là hướng cuối cùng còn lại theo đề xuất từ
  chẩn đoán UW-2025 trước — nếu NO-GO thì đã cạn hết các cơ chế regime hợp lý cho breadth).
- Ngưỡng 60% giữ NGUYÊN như Bước 5.1 (nhất quán, không đổi ngưỡng giữa các round để so sánh công
  bằng).

## 5. Đầu ra

`research/analysis/breadth_regime.py` (mới, tái dùng nguyên văn `trend_rank_ic.load_closes`,
`bigdown_struct.load_trades_utc/block_boot_mean/phi_for`, không sửa các file gốc) +
`research/analysis/out/breadth_regime.json` + `docs/diag/DIAG_BREADTH_REGIME.md` (kết quả + GO/NO-GO).
Dùng `logging`, cấm `print()`.

## 6. Bổ sung Bước 5.3 (2026-09-21, giao trực tiếp trong brief MASTER — khoá TRƯỚC khi tính số)

MASTER giao thêm định nghĩa **B** để so cạnh A (breadth, §2 trên) và **C** (BTC-đơn MA200, đối
chiếu). Định nghĩa B/C dưới đây được khoá NGUYÊN VĂN theo brief MASTER (không đổi sau khi thấy
số), tính TRONG CÙNG script/cửa sổ SIM/UW như A để so sánh công bằng (`research/analysis/
breadth_regime.py`, phần "BUOC 5.3" cuối file).

- **C (BTC-đơn, đối chiếu)**: `not_up_C(D) = close_BTC[D-1] < MA200_causal_BTC(D)` — CÔNG THỨC
  NGUYÊN VĂN của `regime_build_ma200.py` (Bước 2/4), tính lại bằng `up_matrix(symids=[1])` của
  `breadth_regime.py` (cùng công thức causal, cùng `min_periods_floor=30`) để dùng đúng cửa sổ
  UW2022/UW2025 và SIM range như A.
- **B (BTC+ETH kết hợp, MA200 "nguyên văn" — KHÁC SMA7/100-crossover của Bước 5.1)**:
  `not_up_BTC(D)` như C; `not_up_ETH(D) = close_ETH[D-1] < MA200_causal_ETH(D)` (symId 2, cùng
  công thức). `B_AND(D) = not_up_BTC(D) AND not_up_ETH(D)`; `B_OR(D) = not_up_BTC(D) OR
  not_up_ETH(D)`. Báo CẢ HAI biến thể (yêu cầu MASTER).
- Cửa sổ SIM/UW, ngưỡng cổng (≥60% cả hai chuỗi) và 2 chuỗi UW2022/UW2025 GIỮ NGUYÊN như §2-4
  trên (không tính lại, không đổi ngưỡng).
- Gate cho B/C tính bằng CÙNG hàm `gate_verdict()` như A (không có tham số nào chọn sau khi thấy
  số — B_AND/B_OR/C đều dùng công thức + cửa sổ cố định, không sweep để "tìm" biến thể đạt).
