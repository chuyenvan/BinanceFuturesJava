# PREREG_LOB_T1 — tín hiệu order book (BNBUSDT, 100 level) có vượt chi phí?

Ngày 2026-10-23. Viết và commit **TRƯỚC** khi kernel B chạy/đo bất kỳ IC nào. Sau commit: không đổi
feature, horizon, cách chia mẫu, cách tính IC/R², ngưỡng luật. Mọi số báo cáo lấy trên đoạn TEST.

## 0. Bối cảnh
- Dataset ngoài `alpha000x/crypto-lob-data` (Kaggle, private): 5 file CSV, 95,01 GB, snapshot 100 level
  bid/ask (`bid_px_1..100`, `bid_qty_1..100`, `ask_px_1..100`, `ask_qty_1..100`) + `event_ts_ms`,
  `recv_ts_ns`, `update_id`.
- **Số liệu Phase A (kernel `chuyendinh/lob-verify-a`, run hoàn tất 2026-10-23) quyết định thị trường**:
  BNBUSDT = 3.851.648 dòng, 2026-10-06T06:22:26Z → 2026-10-13T06:22:25Z (7,0 ngày), 10.081 phút liên tục,
  0 crossed / 0 locked / 0 ts không tăng / 0 trùng / 0 NaN; spread median 0,133 bps (= 1 tick 0,01 USDT).
  Đối chiếu mid phút: **spot** |dev| p50 0,067 bps, |dev| p95 0,34 bps, corr return 1m 0,9989;
  futures/um |dev| p50 3,19 bps, corr 0,9887 ⇒ **book là SPOT BNBUSDT**. Phase B dùng spot.
- Chỉ chạy Phase B nếu A đạt §7 (đã đạt). Kết quả A không dùng để chọn feature/horizon/ngưỡng.
- Phạm vi B: **một symbol = BNBUSDT** (file nhỏ nhất 14,39 GB, thanh khoản cao). 4 symbol còn lại chỉ ở A.

## 1. Dữ liệu, chia mẫu, grid
- Grid 1 giây: mỗi giây lấy **trạng thái cuối** (row cuối có `event_ts_ms // 1000 = s`) ⇒ feature tại `s`
  chỉ dùng dữ liệu `event_ts_ms ≤ s*1000 + 999`.
- Đoạn khám phá (discovery) = **60 % đầu** theo thời gian; đoạn kiểm (test) = **40 % cuối**. Mốc chia in ra
  trong `t1.json.grid.split_utc`. Không dùng test để chọn feature/hướng/ngưỡng.
- Horizon: 1 s, 10 s, 60 s trên grid 1 s (mẫu mỗi giây); 300 s, 900 s trên grid 60 s (mẫu mỗi phút).
- Return: `r_h(t) = (mid(t+h) - mid(t)) / mid(t) * 1e4` (bps), mid = (bid_px_1+ask_px_1)/2.
  Chỉ tính khi cả hai đầu có observation thật (không dùng giá trị forward-fill cho return).

## 2. Feature (6, định nghĩa đóng băng)
Ký hiệu `b_i, a_i` = bid/ask price level i; `B_i, A_i` = qty; mid = (b_1+a_1)/2; L = 5.
1. `imb1 = (B_1 - A_1) / (B_1 + A_1)`
2. `imb5 = (Σ_{i≤L} B_i − Σ_{i≤L} A_i) / (Σ B_i + Σ A_i)`
3. `ofi1` = OFI Cont–Kukanov–Stoikov (2014) mức 1, cộng dồn trong 1 giây rồi chuẩn hoá:
   `e_n = 1[b_n≥b_{n−1}]·B_n − 1[b_n≤b_{n−1}]·B_{n−1} − 1[a_n≤a_{n−1}]·A_n + 1[a_n≥a_{n−1}]·A_{n−1}`;
   `ofi1 = Σ_{n∈giây} e_n / mean(B_1+A_1)`.
4. `micro_bps` = microprice Stoikov (2018) lệch mid: `( (b_1·A_1 + a_1·B_1)/(A_1+B_1) − mid ) / mid · 1e4`
5. `slope_imb = (D_b − D_a)/(D_b + D_a)` với `D_b = Σ_{i≤L} B_i·(mid−b_i)/mid·1e4`, `D_a = Σ A_i·(a_i−mid)/mid·1e4`
   (depth slope có trọng số khoảng cách, dạng imbalance).
6. `depth_bps5 = D_b + D_a` (độ sâu 5 level, thước đo thanh khoản; dùng làm control).

Dấu kỳ vọng theo literature: `imb1, imb5, ofi1, micro_bps` dương ⇒ return kỳ vọng dương. `slope_imb`,
`depth_bps5` không có dấu tiên nghiệm (báo dấu, không dùng để chọn hướng).

## 3. Chỉ số (chỉ tính trên TEST; discovery chỉ để fit)
- **IC** = Spearman(signal(t), r_h(t)) trên test, mỗi feature × mỗi horizon.
- **NW t**: t-stat của Pearson với hiệu chỉnh Newey–West, lag = h (giây) — chống overlap.
- **R² OOS**: OLS `r = α + β·x` fit **chỉ trên discovery** (β, α), dự báo trên test,
  `R² = 1 − SS_res/SS_tot(test)`.
- **Decile**: biên decile lấy từ phân vị discovery; test chia 10 nhóm; báo mean return từng nhóm (bps),
  `spread = mean(D10) − mean(D1)`. Hướng chiến lược = dấu `IC_discovery` (không chọn hướng theo test).
- **Net**: `gross = direction · spread`; `net_taker = gross − 2·5 bps`; `net_maker = gross − 2·2 bps`
  (một vòng vào+ra cho một leg; spread là chênh lệch return 2 leg cùng notional 1).
- Spread trung vị của book được báo kèm (chi phí vượt spread là phí, không phải spread).

## 4. Regime
- `vol15` = std của return mid 1 phút trong 15 phút **quá khứ** (rolling, chỉ dùng quá khứ); ngưỡng =
  median trên discovery ⇒ `vol_hi` / `vol_lo`.
- `crash` = |return 1 phút| ≥ phân vị 99,9 của discovery (ngưỡng in trong `t1.json`).
- Báo IC theo regime ở horizon 10 s (chính) + số giây mỗi regime. Không dùng regime để chọn tham số.

## 5. Kiểm hợp lệ (fail ⇒ báo, không chấm điểm phần liên quan)
- V1 placebo: xáo trộn **return** trong test (giữ nguyên phân bố signal) 3 lần ⇒ |IC| phải ≤ 0,01.
- V2 control ngẫu nhiên: 10 vector N(0,1) ⇒ mean IC ≈ 0, sd ≈ 1/√n.
- V3 nhất quán theo ngày: IC của `imb1` h=10 s theo từng ngày UTC (báo, không chấm).
- V4 số học chi phí: kiểm 100−2·5 = 90 và 100−2·2 = 96.
- V5 số mẫu: n_1s = số giây phủ, n_60s = ⌈n_1s/60⌉; lệch > 1 ⇒ báo.
- V6 parse độc lập: đọc 2 000 dòng bằng `csv` thuần và bằng pandas, so `imb1`/`micro` (max abs diff < 1e-9).

## 6. Luật (chốt trước khi đo)
Với mỗi horizon, một feature được coi là **có tín hiệu** nếu đồng thời:
- G1: `|IC_test| ≥ 0,02` và `|NW t| ≥ 3`, và dấu `IC_test` = dấu `IC_discovery`;
- G2: `net_taker > 0` (đã trừ 10 bps) tại horizon đó;
- G3: dấu IC đúng ở ≥ 5/7 ngày test (V3 mở rộng cho feature đó).
Kết luận:
- **GO (tradeable with taker)**: ≥ 2 feature đạt G1–G3 ở cùng một horizon, và `|IC|` của chúng không cùng
  một biến thể của một feature duy nhất (imb1 và imb5 tính là 2; ofi1 riêng; micro_bps riêng).
- **GO-maker-only**: ≥ 2 feature đạt G1+G3 nhưng `net_taker ≤ 0 < net_maker`.
- **NO-GO**: còn lại. Mọi kết luận ghi rõ "7 ngày dữ liệu là mẫu ngắn; GO chỉ là tạm thời".

## 7. Điều kiện chạy B (từ Phase A)
Chạy B chỉ khi A đạt **tất cả**: (i) 0 dòng NaN ở `bid_px_1..5`/qty; (ii) `crossed + locked = 0`;
(iii) `nonmono_ts = 0` và `dup_ts = 0` trên file BNB; (iv) đối chiếu Vision: `|median dev| ≤ 1 bps` và
`abs_p95 ≤ 5 bps` ở ít nhất một thị trường (spot hoặc futures/um); (v) số giây phủ ≥ 90 % khoảng thời gian.
- **Trạng thái Phase A: ĐẠT** — (i) 0 NaN, (ii) crossed+locked = 0, (iii) 0/0, (iv) spot |median| 0,065 bps /
  p95 0,34 bps, (v) 10.081/10.081 phút, 0 lỗ hổng.
Nếu không đạt: B không chạy, báo lý do.

## 8. Giới hạn đã biết (ghi trước)
- 7 ngày, một symbol ⇒ không kết luận được về mùa vụ/thị trường khác; không kiểm được impact theo size.
- Không mô phỏng queue position/huỷ lệnh; maker 2 bps là giả định, chưa chứng minh fill.
- Snapshot 100 level không cho biết book có phải consolidated hay chỉ một venue.
