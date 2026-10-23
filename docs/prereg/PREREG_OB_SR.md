# PRE-REG — OB_SR: orderbook depth ±k% tại các mốc quyết định của lệnh crash-buy X14 (2026-10-23)

Trạng thái: file này được commit **TRƯỚC** khi tính bất kỳ biến kết quả nào (MFE, arm, giveback, PnL).
Đã biết trước khi viết: chỉ số đếm cụm/seed và tình trạng có/thiếu file bookDepth. Chưa đọc outcome.

## 0. Câu hỏi kiểm được

Tại ba mốc quyết định của cụm crash-buy X14 —
(1) lúc vào lệnh, (2) lúc arm trailing +7 %, (3) lúc chạm mốc 168h —
độ dày sổ lệnh phía trên/dưới trong các dải ±1, ±2, ±3, ±5 % (Vision `bookDepth`) có dự báo đường giá **sau** mốc đó không (arm, MFE, giveback, PnL giữ thêm)?

Đây là **chẩn đoán**, không phải chấm luật. Không chạy sim Java, không đổi luật X14.

## 1. Dữ liệu

- **Cụm crash-buy**: printDone X14, 8 seed DEV (`tsx-x14-{a1,s7,s13,s21,s99,s123,s777,s2024}`), `~/kaggle_sim/out/`.
  - `start`/`end` trong printDone là giờ **+07**. Quy đổi: `t_UTC = start − 7h`.
  - Cụm = nhóm leg cùng `(seed, sym, end)`. Anchor `t0` = `min(start)` của cụm (UTC).
  - **Đơn vị phân tích chính**: `(sym, t0)` duy nhất sau khi gộp seed (bookDepth tại cùng anchor là một). Outcome phụ thuộc seed (entry/qty) lấy **trung vị qua các seed**; đếm riêng số cụm-seed để báo cáo.
  - Năm khám phá: **2023 và 2025** (UTC, theo `t0`). Năm kiểm: **2024** — không đọc outcome 2024 cho tới khi prereg + code chốt xong. HO 2026: chỉ mô tả sau cùng. Không dùng 2020.
- **Giá 1m**: parquet Vision có sẵn trên Oracle (`/home/ubuntu/vz_e1/raw/kline1m-YYYY-MM.parquet`, `/home/ubuntu/claude_master/gvz/k2021/`). Không REST.
- **bookDepth**: `data.binance.vision/data/futures/um/daily/bookDepth/{sym}/{sym}-bookDepth-{day}.zip` (file tĩnh). Ưu tiên `~/vz_bd/raw` đã có; thiếu thì tải tĩnh. Snapshot 30 giây, 10 dải % (±1..±5), trường `timestamp, percentage, depth, notional`.
- **Đợt sập** (chỉ để tách nhóm, chốt trước): các khoảng ngày từ ALT_EW dd ≤ −25 % (lookback 45 ngày, nối khoảng cách ≤ 3 ngày) — định nghĩa `research/tsx_v2/common.py:episodes`:
  2023-03-09→03-13, 2023-05-09→06-03, 2023-06-10→06-20, 2024-04-13→05-24, 2024-06-18→07-26, 2024-08-04→08-19, 2024-08-29→09-08, 2024-11-05, 2024-12-19→2025-03-24, 2025-03-29→04-20, 2025-05-31→06-01, 2025-06-06→07-08, 2025-10-11→12-31.
  Ngày quyết định (UTC) nằm trong khoảng ⇒ `episode=1`.

## 2. Mốc quyết định

Với mỗi cụm `(sym, t0)`, `E` = trung vị entry leg-0 qua các seed:

1. **Entry** `t_e = t0`.
2. **Arm** `t_a` = phút đầu tiên `j ≥ 1` có `high(t0+j) ≥ E·1,07` (điều kiện sim là `(H−E)/E > 0,07`; dùng cùng ngưỡng, high 1m Vision), trong `[t0, t0+168h]`. Chỉ tính cho cụm có arm.
3. **168h** `t_168 = t0 + 168h + 1 phút` (đúng mốc cắt time-stop của engine `MARK = 168·60+1`). Chỉ tính cho cụm còn mở tới mốc (age ≥ MARK).

## 3. Đặc trưng (cố định, không tune)

Tại mốc `t`, lấy snapshot bookDepth **gần nhất có `ts ≤ t`** (không look-ahead), chỉ chấp nhận nếu `ts ≥ t − 5 phút`.
- `A_k(t)` = `notional` dải `percentage = +k`; `B_k(t)` = `notional` dải `−k`; `k ∈ {1,2,3,5}`.
  (bookDepth là depth **tích luỹ** trong dải ±k %, đúng như file Vision.)
- `R_k(t) = (B_k − A_k)/(B_k + A_k)`.
- `wall_A_k(t) = 1[A_k(t) ≥ 3 × median{A_k(s): s ∈ (t−24h, t]}]`; `wall_B_k` tương tự với `B_k`.
  Median chỉ tính nếu có ≥ 720 snapshot hợp lệ trong 24h; nếu không ⇒ `wall = NaN`.
- Snapshot hợp lệ: đủ 8 dải dùng, `A_k>0`, `B_k>0`; `mid = 0,5·(B_1/depth(−1) + A_1/depth(+1))` phải nằm trong `[min(low)·0,995, max(high)·1,005]` của hai nến 1m kết thúc tại phút snapshot (bỏ snapshot hỏng/crossed).
- Không chuẩn hoá thêm. `A_k/B_k` dùng USD notional; IC Spearman bất biến với biến đổi đơn điệu.

Tổng: 4 dải × (A, B, R, wall_A, wall_B) = 20 đặc trưng, dùng giống nhau ở cả 3 mốc.

## 4. Biến kết quả

Tất cả tính từ nến 1m Vision, `E` = trung vị entry leg-0; quy ước `j` = phút kể từ `t0`.

**(a) Tại entry**
- `arm168` = 1 nếu có `j ∈ [1, 10080]` với `high_j ≥ E·1,07`, ngược lại 0.
- `mfe24` = `max(high_j, j∈[1,1440])/E − 1` (bps).
- `mfe72` = `max(high_j, j∈[1,4320])/E − 1` (bps).

**(b) Tại arm** (chỉ cụm arm trong 168h)
- Chạy lại `research/tsx_v2/engine.py` (đã validate 100 % với printDone) trên cửa sổ `t0..t0+264h`, legs thực của từng seed, luật X14 (trailing 3 % từ đỉnh, tick floor, fee 0,000982 + 2×0,000067).
- `giveback_bps` = `(peak_high(sau arm → exit) − exit_px)/peak_high · 1e4`. Cụm chưa thoát trong 264h ⇒ NaN (censored).
- `pnl_trail_bps` = `PnL replay / entry_notional · 1e4`, `entry_notional = Σ q_i·e_i` của các leg đã dùng. Lấy trung vị qua seed.

**(c) Tại 168h** (chỉ cụm còn mở tới mốc)
- `px168` = close phút `t_168`.
- `extra24_bps` = `(close(t_168+24h) − px168)/E_avg · 1e4`; `extra72_bps` tương tự với 72h. `E_avg` = entry trung bình theo notional của các leg đang mở tại 168h. Không trừ fee (so sánh giữ vs không giữ).
- Thiếu nến đúng mốc ⇒ dùng close cuối cùng ≤ mốc trong vòng 5 phút; quá 5 phút ⇒ NaN.

## 5. Thống kê

- **IC**: Spearman hạng giữa từng đặc trưng và từng outcome, tính riêng 2023, 2025, 2024; gộp 2023+2025 (khám phá). Đơn vị `(sym,t0)`.
- **CI 95 %**: bootstrap theo **ngày UTC** (resample ngày có hoàn lại; mỗi ngày mang toàn bộ cụm của ngày đó), `NREP=2000`, `seed=20261023`. Chỉ chạy CI cho tổ hợp vượt màn dấu/độ lớn ở cả 3 năm (tiết kiệm; các tổ hợp khác báo "screen fail").
- **Tách đợt**: IC theo `episode=1` vs `episode=0` trong từng năm (chỉ báo cáo khi mỗi nhóm ≥ 100 cụm).
- **Decile cực** (chỉ 2024): chia 10 nhóm theo đặc trưng; báo `mean outcome` nhóm cao nhất − nhóm thấp nhất, kèm số cụm.
- Không impute; NaN bị loại theo từng cặp (feature, outcome). Báo n từng ô.

## 6. Tiêu chí "có cửa" (cố định, không nới)

Một bộ `(mốc, đặc trưng, outcome)` được coi là **CÓ CỬA** khi đủ cả 3:

1. `|IC| ≥ 0,10` và **cùng dấu** ở 2023, 2025 **và** 2024.
2. CI 95 % của IC năm 2024 **không chứa 0**.
3. Chênh decile cực 2024 đủ lớn để một luật lọc/exit ước tính `≥ +5 000 USD/seed direct`:
   `Δ̂/seed = 0,10 × N_dec_per_seed × spread_USD`, trong đó
   - `N_dec_per_seed` = số cụm/seed của tập quyết định đó trong 2024 (entry ≈ 105; arm ≈ 90; 168h ≈ 23 — tính lại từ dữ liệu, không hard-code);
   - `spread_USD` = chênh mean outcome top − bottom decile, quy USD:
     - outcome bps ⇒ `bps/1e4 × median(entry_notional)` của tập 2024;
     - `arm168` ⇒ dùng chênh mean **PnL thực** (printDone, USD/cụm) giữa top và bottom decile (luật lọc hành động ở entry).
   - Công thức giả định luật chỉ dịch 10 % cụm từ decile thấp sang cao; là ước tính thô, không phải kết quả sim.
   Không đạt ⇒ **đóng ý tưởng**, không thử biến thể khác (không thêm dải, không đổi ngưỡng wall, không đổi horizon).

Nếu đạt: chỉ **đề xuất 1 luật** cụ thể (điều kiện + hành động) để prereg vòng sau; không tự chấm bằng sim.

## 7. Kiểm vệ sinh (bắt buộc báo cáo)

- **V1 causal**: mọi snapshot dùng có `ts ≤ t`; assert 100 %.
- **V2 timezone/giá**: median `|log(mid_snap / close phút snapshot)| < 0,01`; báo p99.
- **V3 phủ**: % cụm có đặc trưng hợp lệ tại từng mốc × năm; nếu < 50 % ⇒ đánh dấu "underpowered", vẫn báo cáo, không thay đổi mẫu.
- **V4 replay**: trên mẫu cụm còn mở tới 168h, replay phải khớp printDone ≥ 99 % (|ΔPnL| ≤ 1e-3·max(|PnL|,1)).
- **V5 sổ hỏng**: đếm snapshot bị loại (thiếu dải / notional ≤ 0 / mid ngoài băng); báo tỉ lệ.
- **Căn múi giờ**: mọi mốc tính bằng UTC; printDone trừ 7h; assert không có mốc nào lệch nửa đêm hàng loạt.

## 8. Đầu ra

`docs/result/OB_SR.md` + `docs/result/ob_sr/` (script + JSON nhỏ + bảng). Commit, **không push**.
Payload cuối: hash prereg/result, phủ dữ liệu, bảng IC theo năm × mốc × đặc trưng, verdict theo tiêu chí, đề xuất (nếu có), bất thường.

## 9. Giới hạn đã biết trước

- bookDepth là snapshot 30 s, không phải sổ đầy đủ; dải % là tích luỹ.
- Cú sập 2025-10-10/11 quét sạch sổ: các snapshot ở đó có thể bị V5 loại; đây là mẫu quan trọng nhất nên kết quả có thể mất power đúng vào lúc cần nhất.
- X14 chủ yếu arm trước 168h (≈ 85 % cụm), nên mẫu mốc 168h nhỏ (~190 cụm/năm) — MDE cao.
- Đơn vị `(sym,t0)` gộp seed làm mất nhiễu mô hình giữa seed (chấp nhận; báo kèm bản seed-cluster để đối chiếu).
