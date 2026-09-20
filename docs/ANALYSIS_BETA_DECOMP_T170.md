# BETA_DECOMP_T170 — phân tách alpha (selector S1) vs beta (BTC market timing qua gate)

Task: `tasks/TASKS_2026-09-20_next_round.md` mục "TASK 1 — BETA_DECOMP_T170".
Script: `research/analysis/beta_decomp_t170.py` (idempotent, read-only, chạy lại
cho cùng kết quả). Kết quả máy đọc: `/home/ubuntu/s1hpo/beta_decomp.json`
(scratch trên Oracle, không commit git).

## Câu hỏi nghiên cứu

CAGR ~29%/năm của T170 (`profiles/x1_gs_t170.properties`,
`SIM_GATE_DYN_SCALE=1.70`) chủ yếu là alpha từ xếp hạng coin (selector S1) hay
chỉ là beta thị trường BTC được một gate bật/tắt đúng lúc (market timing)?

## Nguồn dữ liệu + múi giờ dùng (CHỈ ĐỌC, không sửa dữ liệu nguồn)

- **Equity theo ngày**: `java/devrun/<TAG>/logs/sim.out`, dòng
  `Update YYYYMMDD HH:MM => b:<B> ... unP:<U>`, equity = B+U, bản ghi CUỐI CÙNG
  mỗi ngày. Tái sử dụng nguyên hàm `research/analysis/c3_rates.py::equity()`.
  JVM sim chạy với `-Duser.timezone=Asia/Ho_Chi_Minh` ⇒ nhãn `YYYYMMDD` trong
  `sim.out` **là lịch GMT+7**.
- **Lệnh**: `java/devrun/<TAG>/storage/printDone.csv`. Tái sử dụng nguyên hàm
  `research/analysis/c3_rates.py::trades()` (leg/blk cũng tính từ đây,
  `on_bad_lines="skip"`). Cột `start`/`end` là giờ GMT+7 **naive** (vd
  `20251201 07:09`). Cột `margin` trong file này **thực chất là notional**
  (= quantity × entry, đối chiếu `MaeDistributionProbe.java`:
  `c.notional += o.quantity * o.priceEntry;`, kiểm tra số học trên các dòng đầu
  `printDone.csv` khớp trong phạm vi làm tròn giá) — `c3_rates.py` cũng dùng
  thẳng cột này (`r["margin"] = d.margin.mean()`) mà không chia thêm đòn bẩy,
  nên đây là "cách c3_rates.py đang tính" được dùng lại nguyên vẹn cho
  `notional_lệnh` ở tầng B.
- **Giá đóng cửa BTC 1h**: `java/fsrun/CLOSES_1H.bin`. Tái sử dụng nguyên hàm
  `research/analysis/trend_rank_ic.py::load_closes()` (dtype
  `[('ts','>i8'),('sym','>i2'),('c','>f4')]`, `ctime = open_time + 1h`, quy ước
  causal). `symId` của BTCUSDT = 1 (`selector_pred_out/symbol_map.csv`).
  Dữ liệu phủ 2021-01-01 → 2026-01-01 (đủ cho cửa sổ phân tích).

### Mốc ghép thời gian (đã kiểm tra thực tế trước khi chạy toàn bộ)

- **Tầng ngày**: giá BTC dùng cho ngày D = close 1h có `ctime <= 00:00 UTC`
  ngày D (= 07:00 GMT+7 ngày D, theo đúng đề bài). Kiểm tra trên 10 mẫu đầu/cuối
  của T170 (2021-07-01…07-05 và 2025-12-26…12-30): `delta_h = 0.0` — khớp
  CHÍNH XÁC, không lệch giờ. Ví dụ: `date=2021-07-01 target_utc_ms=1625097600000
  btc_close=34884.76 matched_ctime_utc=2021-07-01 00:00:00 delta_h=0.0`;
  `date=2025-12-30 btc_close=87317.00 matched_ctime_utc=2025-12-30 00:00:00
  delta_h=0.0`.
- **Tầng lệnh**: `start`/`end` naive GMT+7 → quy đổi UTC bằng trừ 7h, rồi lấy
  giá đóng 1h GẦN NHẤT `<=` mốc đó (`searchsorted(..., side="right") - 1`).
  Ví dụ kiểm tra: `sym=1000000MOG start_gmt7=20241206 05:28 -> start_utc=
  2024-12-05 22:28:00 btc@start=99125.30 | end_gmt7=20241206 06:03 -> end_utc=
  2024-12-05 23:03:00 btc@end=98968.10 r_btc_hold=-0.00159 profit%=6.999` —
  hợp lý (BTC gần như đi ngang trong 35 phút, trade lãi 7% đến từ altcoin, không
  từ BTC).
- **Ngày-có-vị-thế-mở (sanity check)**: dùng LỊCH GMT+7 trực tiếp từ
  `start`/`end` của `printDone.csv` (KHÔNG quy đổi UTC) vì đây là cùng hệ quy
  chiếu với nhãn `Update YYYYMMDD` trong `sim.out` (cả hai đều là lịch JVM
  Asia/Ho_Chi_Minh).

## Luật đọc D (PRE-DECLARED, chép nguyên văn — không được diễn giải lại)

> (i) Nếu phần beta ≥60% tổng lợi nhuận log VÀ |t(α)|<2 ⇒ nhãn **CHỦ YẾU BETA**
> (tối ưu selector S1 tiếp là tối ưu sai chỗ; sản phẩm thật đang vận hành là
> một chiến lược BTC-beta có timing qua gate). (ii) Nếu phần beta ≤40% VÀ
> |t(α)|≥2 ⇒ nhãn **CHỦ YẾU ALPHA**. (iii) Các trường hợp còn lại ⇒ nhãn
> **HỖN HỢP**, báo rõ tỉ lệ %.
> Không được kết luận gì thêm ngoài 3 nhãn này ở phần D — không được tự thêm
> điều kiện phụ hay ngoại lệ để đổi nhãn sau khi thấy số.

Phương pháp: OLS `r_s = α + β·r_b + ε` (HAC Newey-West lag=5, statsmodels
`cov_type='HAC', cov_kwds={'maxlags':5}`); α quy đổi năm bằng ×365×100 (%).
Phần beta = Σ(β·r_b) / Σr_s (theo log-return tích lũy toàn kỳ).

## A. Tầng ngày (log-return equity vs log-return BTC, HAC lag=5)

### T170 (`X1_GS_T170_2021`)

| Năm | n | α(ngày) | α năm hoá (%) | β | R² | t(α) | %beta_của_tổng | β(BTC↑) | β(BTC↓) |
|---|---|---|---|---|---|---|---|---|---|
| 2021* | 183 | 0.000607 | 22.15 | 0.0137 | 0.0108 | 2.025 | 3.6% | 0.0279 | 0.0169 |
| 2022 | 365 | 0.000769 | 28.08 | 0.0977 | 0.0917 | 1.781 | −57.0% | 0.1692 | 0.0979 |
| 2023 | 365 | 0.000788 | 28.77 | 0.0130 | 0.0014 | 2.021 | 4.0% | 0.0051 | −0.0429 |
| 2024 | 366 | 0.000700 | 25.56 | 0.0276 | 0.0158 | 2.419 | 7.8% | 0.0259 | 0.0068 |
| 2025 | 364 | 0.000785 | 28.66 | 0.0461 | 0.0277 | 2.240 | −1.0% | 0.1404 | −0.0238 |
| **FULL** | **1643** | **0.000676** | **24.66** | **0.0487** | **0.0312** | **4.372** | **3.9%** | **0.0716** | **0.0413** |
| Sanity: ngày CÓ vị thế mở | 435 | 0.003051 | — | 0.1219 | 0.0862 | 4.776 | — | — | — |
| Sanity: ngày KHÔNG vị thế nào mở | 1208 | 0.0000341 | — | **0.0011** | 0.0014 | 1.565 | — | — | — |

*2021 là năm bán phần (07-01 → 12-31).

### Baseline (`X1_C3_FULL_2021`)

| Năm | n | α(ngày) | α năm hoá (%) | β | R² | t(α) | %beta_của_tổng | β(BTC↑) | β(BTC↓) |
|---|---|---|---|---|---|---|---|---|---|
| 2021* | 183 | 0.000296 | 10.79 | 0.1156 | 0.1555 | 0.586 | 39.0% | 0.0914 | 0.2484 |
| 2022 | 365 | 0.000789 | 28.80 | 0.1231 | 0.1374 | 1.910 | −80.5% | 0.1370 | 0.1525 |
| 2023 | 365 | 0.001220 | 44.53 | 0.0294 | 0.0061 | 2.937 | 5.8% | 0.0261 | −0.0529 |
| 2024 | 366 | 0.000783 | 28.58 | 0.1102 | 0.1059 | 1.824 | 23.3% | 0.0836 | 0.0992 |
| 2025 | 364 | 0.000443 | 16.18 | 0.1491 | 0.1037 | 0.886 | −5.9% | 0.2592 | 0.0589 |
| **FULL** | **1643** | **0.000698** | **25.49** | **0.1081** | **0.0929** | **3.426** | **8.0%** | **0.1049** | **0.1225** |
| Sanity: ngày CÓ vị thế mở | 885 | 0.001799 | — | 0.1722 | 0.1519 | 4.752 | — | — | — |
| Sanity: ngày KHÔNG vị thế nào mở | 758 | 0.0000507 | — | **0.0031** | 0.0047 | 1.389 | — | — | — |

**Sanity check kết quả**: β trên nhóm ngày KHÔNG có vị thế mở ≈ 0 cho cả hai
(T170: 0.0011, |t|=0.71; Baseline: 0.0031, |t|=2.12 — nhỏ về độ lớn kinh tế dù
t hơi > 2 do n=758 lớn). Không phát hiện dấu hiệu lệch múi giờ (nếu lệch 7h,
nhóm "không vị thế" sẽ nhiễm beta từ phiên lân cận và cho β lớn bất thường —
không xảy ra). **Kết luận (C) sơ bộ nhìn tầng ngày**: gate T170 (1.70) có β
toàn kỳ thấp hơn baseline (0.0487 vs 0.1081, ~45%), tức gate chặt hơn **có làm
giảm beta thực chất**, không chỉ giảm số lệnh — nhưng ở cả hai chân, %beta/tổng
lợi nhuận log đều rất nhỏ (3.9% và 8.0%), nên phần "giảm" này chỉ có ý nghĩa
tương đối, tổng thể cả hai đều alpha-dominant.

## B. Tầng lệnh (profit% vs r_btc_hold thực theo thời gian giữ lệnh, cluster-robust SE theo ngày vào lệnh)

Đơn vị: `a` (hằng số) và `profit` theo %; `b` là hệ số trên `r_btc_hold` (log-return
phân số, vd 0.01 = BTC +1% trong thời gian giữ lệnh) ⇒ `b=75.8` nghĩa là BTC
+1% trong lúc giữ lệnh dự báo profit trung bình đổi thêm ~0.76 điểm %.
`sum_pnl_btc_only` = Σ(notional_lệnh × r_btc_hold) — "PnL nếu chỉ nhờ BTC".

### T170 (`X1_GS_T170_2021`)

| Năm | n | a | b | R² | t(a) | t(b) | n_cluster(ngày) | n(BTC↑) | n(BTC↓) | winrate BTC↑ % | winrate BTC↓ % | Σpnl thật (USDT) | Σpnl nếu chỉ nhờ BTC (USDT) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 149 | 6.514 | 73.548 | 0.1550 | 13.20 | 3.325 | 11 | 14 | 135 | 92.9 | 92.6 | 4,272.7 | −4,809.5 |
| 2022 | 198 | 6.120 | 92.584 | 0.0824 | 5.81 | 3.462 | 19 | 41 | 157 | 87.8 | 82.8 | 7,688.3 | −6,641.2 |
| 2023 | 126 | 8.842 | 53.776 | 0.0053 | 2.72 | 0.872 | 25 | 24 | 102 | 79.2 | 90.2 | 16,331.3 | −3,472.7 |
| 2024 | 281 | 6.395 | 89.049 | 0.0709 | 6.47 | 2.310 | 34 | 58 | 223 | 82.8 | 91.9 | 20,403.1 | −10,959.3 |
| 2025 | 335 | 6.049 | 45.714 | 0.0048 | 3.94 | 0.799 | 21 | 73 | 262 | 87.7 | 87.4 | 27,374.8 | −4,686.5 |
| **FULL** | **1089** | **6.500** | **75.799** | **0.0293** | **8.69** | **3.871** | **110** | **210** | **879** | **85.7** | **88.9** | **76,070.2** | **−30,569.1** |

### Baseline (`X1_C3_FULL_2021`)

| Năm | n | a | b | R² | t(a) | t(b) | n_cluster(ngày) | n(BTC↑) | n(BTC↓) | winrate BTC↑ % | winrate BTC↓ % | Σpnl thật (USDT) | Σpnl nếu chỉ nhờ BTC (USDT) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2021 | 293 | 5.703 | 113.768 | 0.3275 | 8.43 | 5.736 | 27 | 70 | 223 | 94.3 | 77.6 | 3,247.5 | −8,108.6 |
| 2022 | 406 | 5.244 | 112.963 | 0.2338 | 8.06 | 4.352 | 43 | 108 | 298 | 96.3 | 77.2 | 6,619.1 | −12,576.4 |
| 2023 | 308 | 5.933 | 14.987 | 0.0012 | 3.93 | 0.307 | 46 | 89 | 219 | 87.6 | 89.0 | 27,014.2 | −6,124.9 |
| 2024 | 668 | 5.065 | 91.023 | 0.0797 | 10.07 | 3.065 | 70 | 202 | 466 | 83.2 | 87.6 | 32,687.2 | −19,926.5 |
| 2025 | 884 | 2.822 | 42.517 | 0.0051 | 1.88 | 1.089 | 82 | 237 | 647 | 81.4 | 83.9 | 17,202.2 | −23,843.8 |
| **FULL** | **2559** | **4.481** | **86.864** | **0.0616** | **7.62** | **4.809** | **268** | **706** | **1853** | **86.3** | **83.6** | **86,770.2** | **−70,580.2** |

Quan sát nổi bật: nếu pnl chỉ đến từ việc "trúng hướng BTC" (long BTC-beta
thuần), cả hai chân đều **LỖ** trên toàn kỳ theo phép tính `notional × r_btc_hold`
(T170: −30,569 USDT; Baseline: −70,580 USDT), trong khi pnl thật đều **LÃI LỚN**
(76,070 và 86,770 USDT). Đây là bằng chứng trực tiếp cho thấy phần lớn lợi
nhuận không đến từ việc đặt cược đúng hướng BTC trong lúc giữ lệnh, mà đến từ
lựa chọn coin (idiosyncratic/alpha) — nhất quán với kết quả tầng ngày.

## C. So sánh T170 (gate 1.70) vs baseline (không gate chặt)

- β toàn kỳ tầng ngày: T170 = 0.0487 vs Baseline = 0.1081 (T170 ≈ 45% beta của
  baseline) ⇒ gate chặt hơn của T170 **có làm giảm beta thực chất** (không chỉ
  giảm số lượng lệnh mà giữ nguyên tỉ lệ beta/alpha — nếu chỉ giảm số lệnh mà
  tỉ lệ không đổi thì β hai chân sẽ xấp xỉ nhau).
- %beta/tổng lợi nhuận log toàn kỳ: T170 = 3.9% vs Baseline = 8.0% — cùng
  hướng, T170 phụ thuộc BTC ít hơn tương đối, nhưng CẢ HAI đều rất nhỏ so với
  ngưỡng 60%/40% của luật D — cả hai đều alpha-dominant theo luật D nếu áp
  riêng cho baseline (không bắt buộc theo đề bài, chỉ để đối chiếu).
- t(α) toàn kỳ: T170 = 4.372, Baseline = 3.426 — cả hai đều |t|≥2 rõ rệt.
- Tầng lệnh: hệ số b (nhạy với r_btc_hold) của T170 toàn kỳ = 75.8 thấp hơn
  Baseline = 86.9, cùng hướng với kết luận tầng ngày.

## D. Nhãn cuối cùng cho T170 (áp dụng ĐÚNG luật đọc D, không thêm điều kiện phụ)

Số liệu toàn kỳ (2021-07-01 → 2025-12-31) của T170: %beta = **3.9%** (≤40%),
|t(α)| = **4.372** (≥2).

⇒ **NHÃN D: CHỦ YẾU ALPHA**

## Giới hạn

- BTC là proxy thị trường DUY NHẤT được dùng trong phân tích này — không có
  proxy altcoin-market rộng hơn (ví dụ market-cap-weighted index của universe
  giao dịch). Một phần "alpha" đo được ở đây có thể thực chất là beta với
  altcoin-market rộng (không phải BTC riêng) nếu altcoin-market và BTC tách rời
  nhau trong giai đoạn nào đó; điều này KHÔNG được kiểm định trong task này.
- Cỡ mẫu theo năm nhỏ hơn nhiều so với toàn kỳ (n=126–366 ngày/năm,
  n=126–884 lệnh/năm) nên t-stat theo năm kém tin cậy hơn toàn kỳ, đặc biệt
  các năm có R² rất thấp (2023, 2025 ở tầng lệnh) khiến ước lượng b theo năm
  nhiễu hơn.
- Tầng lệnh dùng cluster-robust SE theo NGÀY VÀO LỆNH (`statsmodels
  cov_type='cluster'`) thay vì HAC lag cố định — lựa chọn này chặt hơn so với
  yêu cầu tối thiểu trong đề bài ("nếu phức tạp, ít nhất dùng HAC lag phù hợp")
  vì statsmodels hỗ trợ cluster-robust trực tiếp; không có giới hạn kỹ thuật
  nào bị bỏ qua so với yêu cầu.
- 2021 là năm bán phần (chỉ 07-01 → 12-31, ~183 ngày), không so sánh trực tiếp
  độ lớn tuyệt đối với các năm đầy đủ khác.
- `notional_lệnh` dùng cột `margin` trong `printDone.csv` (đã xác minh bằng số
  học = quantity×entry, tức notional thực, KHÔNG chia đòn bẩy) theo đúng cách
  `c3_rates.py` đang dùng cột này; nếu định nghĩa "notional" khác đi (vd nhân
  thêm đòn bẩy danh nghĩa) con số `sum_pnl_btc_only` sẽ đổi theo tỉ lệ nhưng
  KHÔNG đổi dấu/kết luận định tính (vẫn âm toàn kỳ trong khi pnl thật dương).
- Toàn bộ 1089 (T170) và 2559 (baseline) lệnh đều là `side=BUY` (long-only),
  nên không cần xử lý dấu cho lệnh SHORT.
