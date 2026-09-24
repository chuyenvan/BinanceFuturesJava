# PREREG_ALT_REGIME_WAVES — khoá định nghĩa/metric TRƯỚC khi đo (2026-09-23)

Task: kiểm chứng insight của Uni về hành vi ALT:
> "Thường alt pump/dump trong 1 khoảng ngắn rồi xu hướng đi XUỐNG dài hạn; nhưng trong 1 năm sẽ có
> 1 giai đoạn nào đó TẤT CẢ alt tăng đều theo sóng BTC ngắn hạn — ví dụ tháng 8-9/2026 (hiện tại)
> hoặc tháng 7-8/2025."

File này **chốt TRƯỚC** mọi định nghĩa / ngưỡng / luật kết luận. Commit file này TRƯỚC khi chạy đo.
**MO TẢ (descriptive).** Không sim, không sửa `.java`, không chạy JVM trên Oracle (shadow đang chạy),
không tune bất kỳ tham số hệ thống nào, **không push**.

## 0. Ràng buộc & nguồn dữ liệu (đã ĐO, không đoán)

| nguồn | nội dung | khoảng THẬT SỰ có | quy mô |
|---|---|---|---|
| `/home/ubuntu/java/fsrun/CLOSES_1H.bin` | close 1h, `(ts:int64 open_time, sym:int16 symId, close:float32)` | **2021-01-01T01:00Z → 2026-01-01T00:00Z** | 10.322.386 bản ghi, **627 symId** (load đọc `ts < 2026-01-01`) |
| `kaggle_data_hpo/ticker_YYYYMMDD.bin.gz` (`daily/`) | OHLCV 1m, `TreeMap<Long minute, Map<String,KlineObjectSimple>>` | **2021-01-01 → 2026-08-12** | 2050 file; 78 symbol (2021-01-01) → 685 symbol (2026-08-12) |
| Aerospike `ticker.kline_1m_opt` (cụm 242) | OHLCV 1m, Snappy+protobuf `MinuteDataFinal` | key tới **2026-09-23** (đo được key `20260923-0659`) | 685-730 symbol |

- **Key Aerospike là giờ LOCAL UTC+7** (đã kiểm chéo: key `20260813-0659` == phút UTC `2026-08-12T23:59Z`
  trùng khít giá BTC/ETH với file `ticker_20260812.bin.gz`). Từ đây: phút UTC `t` ⇒ key
  `strftime(t + 7h, "%Y%m%d-%H%M")`.
- **Cách đọc**: thuần Python (`research/analysis/jbin.py` tự viết parser Java-serialization cho file
  `.bin.gz`; `snappy` + protobuf thủ công cho Aerospike). KHÔNG chạy Java, KHÔNG build.
- Tải Aerospike: chỉ **~1 key/ngày** (phút 23:59 UTC của ngày), read-only ⇒ ~41 key cho phần mở rộng.
- **KHÔNG có dữ liệu ngày 2026-09-23 sau 03:23Z** (ngày đang chạy) ⇒ mọi metric dừng ở **2026-09-22**.
- Đối chiếu nguồn: lấy mẫu 24 ngày ngẫu nhiên 2021-2025 (seed 20260923) đọc từ ticker bins, so daily
  close với `CLOSES_1H.bin`; sai lệch tương đối > 1% ở > 20% symbol ⇒ DỪNG, báo lỗi nguồn (không
  trộn 2 nguồn).

## 1. Universe & chuỗi giá (khoá)

- **Danh sách symbol**: `/home/ubuntu/map_kaggle.csv` (symId → symbol). Chuẩn hoá tên về **base**
  (bỏ hậu tố `USDT`) để khớp giữa 3 nguồn (`BTCUSDT` ↔ `BTC`).
- **Majors KHOÁ TRƯỚC** (giữ nguyên danh sách đã dùng ở `DIAG_BREADTH_SUBSET`):
  `BTC ETH BNB SOL XRP ADA DOGE AVAX DOT LINK TRX MATIC POL LTC BCH`.
  **alt = universe − majors.**
- **Daily close(D)** = giá tại **thời điểm đóng ngày UTC D**: close của giờ `[23:00,24:00)` trong
  `CLOSES_1H.bin`, hoặc `priceClose` của phút `23:59` trong ticker bins / Aerospike.
- **Coin "sống" tại D** = có daily close hợp lệ tại D. Coin hết dữ liệu thì rớt khỏi mẫu số từ đó,
  KHÔNG backfill, KHÔNG loại trừ survivorship ở quá khứ.
- **Daily return** `r_i(D) = close_i(D)/close_i(D−1) − 1`, chỉ tính khi có đủ 2 ngày.
- Nguồn giá theo thời gian: **2021-01-01 → 2025-12-31 = `CLOSES_1H.bin`** (DEV);
  **2026-01-01 → 2026-08-12 = ticker bins**; **2026-08-13 → 2026-09-22 = Aerospike** (post-DEV).

## 2. Định nghĩa KHOÁ (không đổi sau khi thấy số)

**(2.1) Drift dài hạn.** Horizon `h ∈ {90, 180, 365, 730}` ngày (quy ước: 3m=90d, 6m=180d,
12m=365d, 24m=730d). `ret_h(D) = close(D)/close(D−h) − 1` (yêu cầu cả 2 đầu có giá).
Báo cáo tại **5 mốc cuối năm DEV** (2021-12-31 … 2025-12-31): median & mean cross-section của
`ret_h` cho alt, và giá trị của BTC. Thêm `% alt có ret_365 < 0` tại mỗi mốc.

**(2.2) Pump/dump ngắn hạn.** Pooled mọi quan sát (coin,ngày) DEV có return.
- Phân bố `ret_1d`, `ret_7d`, `ret_30d` cho alt: median, mean, sd, **skew**, **excess kurtosis**
  (định nghĩa Fisher, `scipy.stats`), p01/p05/p50/p95/p99.
- **Luật "pump rồi dump"**: tập P = quan sát alt có `ret_7d ≥ +0.30` **và** có đủ 30 ngày sau.
  `frac_pump = P(ret_30d_forward < 0 | P)`. **Baseline** = `P(ret_30d_forward < 0)` trên toàn bộ
  quan sát alt có đủ 30 ngày sau. So sánh `frac_pump − baseline` + CI bootstrap block (xem §3.2).

**(2.3) Breadth theo thời gian.** Với **alt**:
`breadth30(D) = 100 × #{i alt: close_i(D) > close_i(D−30)} / #{i alt: có đủ 2 giá}`.
Mẫu số chỉ gồm alt sống ở cả D và D−30. Chỉ tính D khi mẫu số ≥ **15**.
Phụ (chỉ để mô tả): `breadth1d(D) = % alt có close(D) > close(D−1)`.

**(2.4) "Cửa sổ tăng đồng loạt" (window) — KHOÁ.** Window = **run tối đa liên tiếp các ngày có
`breadth30 ≥ 70` và dài ≥ 5 ngày**. (Sensitivity 65/75 chỉ báo cáo thêm, KHÔNG dùng để kết luận.)

**(2.5) Đồng pha với BTC.**
- `corr30(D)` = trung bình các cặp (off-diagonal) tương quan Pearson pairwise-complete của daily
  returns alt trên cửa sổ **30 ngày gần nhất kết thúc tại D**; yêu cầu ≥ 15 alt, mỗi alt ≥ 25 ngày hợp lệ.
- `beta30(D)` = trung bình (qua các alt) hệ số OLS slope của `r_i` trên `r_BTC` trong 30 ngày gần
  nhất kết thúc tại D; mỗi alt cần ≥ 25 quan sát chung.
- **Trong window** = trung bình của `corr30`/`beta30` trên các ngày thuộc window;
  **ngoài window** = trung bình trên các ngày DEV không thuộc window nào.

## 3. Luật kết luận (chốt TRƯỚC)

### 3.1 Hai phần của insight
**Phần A** ("pump/dump ngắn hạn rồi đi XUỐNG dài hạn") đạt nếu **cả 3**:
- **A1**: tại ≥ 3/5 mốc cuối năm DEV, `median(ret_365)` của alt **< 0**;
- **A2**: excess kurtosis > 0 cho **cả** `ret_1d`, `ret_7d`, `ret_30d` (đuôi dày);
- **A3**: `frac_pump > baseline` **và** CI 90% (inflate ×1.21) của `frac_pump − baseline` **không chứa 0**.

**Phần B** ("1 lần/năm tất cả alt tăng đều theo sóng BTC") đạt nếu **cả 3**:
- **B1**: **mỗi** năm DEV 2021…2025 có **≥ 1** window (định nghĩa §2.4);
- **B2**: số window/năm trên DEV nằm trong **[1, 3]** (khớp "~1 lần/năm", không phải "vài lần/tháng");
- **B3**: `corr30` **và** `beta30` trong window **đều cao hơn** ngoài window, CI 90% inflated của
  hiệu **không chứa 0** (bootstrap §3.2).

### 3.2 Bootstrap (khoá)
Block bootstrap trên trục thời gian: block = **7 ngày liên tiếp**, NREP = **2000**, seed
**20260923**; CI 90% percentile, sau đó **inflate nửa-độ-rộng ×1.21** (chuẩn repo). Với
`frac_pump − baseline`: resample block ngày, mỗi rep lấy toàn bộ quan sát (coin,ngày) thuộc các
ngày được chọn.

### 3.3 Verdict tổng (khoá)
- **DUNG**: A đạt **và** B đạt.
- **SAI**: A không đạt bất kỳ mục nào (A1,A2,A3 đều ✗) **và** B1 ✗ (không có window nào).
- **DUNG MOT PHAN**: mọi trường hợp còn lại.
Ghi rõ từng mục A1..A3, B1..B3 đạt/không trong result.

## 4. Phần mô tả thuần (không tham gia verdict)

- (4.1) Danh sách window: ngày bắt đầu/kết thúc, độ dài, `breadth30` đỉnh & trung bình, % số ngày
  trong năm thuộc window nào.
- (4.2) Kiểm 2 ví dụ cụ thể: **2025-07-01 … 2025-08-31** và **2026-08-01 … 2026-09-22** (có dữ liệu
  tới 2026-09-22) có nằm trong/ chồng lấn window nào không; in `breadth30` trung bình từng tháng.
- (4.3) Liên hệ T170: `printDone.csv` — tổng PnL theo **tháng** có tập trung vào các window không
  (chỉ mô tả: PnL tháng trong window vs ngoài, số lệnh). **Không** dùng để chọn/threshold.
- (4.4) Sensitivity breadth 65/75 và length 3 ngày (mô tả, không kết luận).

## 5. DEV vs post-DEV

- **DEV = 2021-01-01 … 2025-12-31** (phân tích chính, dùng cho verdict A/B).
- **post-DEV/forward observation = 2026-01-01 … 2026-09-22** (dán nhãn rõ ở mọi bảng; **KHÔNG**
  dùng để tune/đổi định nghĩa — chỉ trả lời câu "hiện tại thế nào").

## 6. Output

`docs/prereg/PREREG_ALT_REGIME_WAVES.md` (file này) → commit TRƯỚC khi đo; sau đó
`docs/result/RESULT_ALT_REGIME_WAVES.md` + script `research/analysis/alt_regime_waves.py`,
`research/analysis/jbin.py`, output JSON/CSV. Commit, **không push**, dọn temp.
