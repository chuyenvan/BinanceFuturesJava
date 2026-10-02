# PREREG_SHORT_V3_R2 — Niêm yết mới (listing effect), vòng R2 của PROGRAM_SHORT_V3

Ngày 2026-10-02 · Chương trình: `docs/research/PROGRAM_SHORT_V3.md` @ a8eff3fb · Executor: research agent · MASTER: Claude.
Pre-reg này commit TRƯỚC khi đo bất kỳ outcome nào. Chưa đọc forward return / funding của bất kỳ coin niêm yết nào;
chỉ dựa trên định dạng dữ liệu đã xác minh ở `PREREG_SHORT_V2_P0A.md` §4. Ngưỡng/chiến lược/luật GO là của PROGRAM (KHÓA).

## 1. Chép nguyên PROGRAM §R2 và phần chấm chung
Chấm chung: net/lệnh sau phí 0,112% RT + funding exact (short nhận khi rate>0, pro-rata theo kỳ 8h thực giữ), CI block
(72h) NREP 2000 seed 20260905, raw và inflate; theo năm 2022–2025; SL-rate; n. Thiếu 1 điều kiện ⇒ NO-GO vòng đó.
DEV 2022-01-01..2025-12-31, 2026 niêm phong. 0 Java trên Oracle. Không sửa .java. Không 242. Lock job nặng (>4G RAM).

> ## R2 — NIÊM YẾT MỚI (listing effect) — 0-sim daily + 1h
> Định nghĩa: `listing_day` = ngày đầu tiên coin có kline 1m trong Aerospike (hoặc ngày đầu trong CLOSES_1H.bin; ghi nguồn).
> Chỉ coin có listing_day trong 2022-01-01..2025-12-24. Đo đường giá so với close ngày D0 (ngày listing, close UTC):
>   retEnd và maxFav tại D+1, D+3, D+7, D+14, D+30 (1h closes); pSQ10 theo horizon; funding thật D0..D+7.
> Chiến lược KHÓA: short tại close D0 (hoặc D1 nếu D0 thiếu <12h dữ liệu), giữ 7 ngày, SL +15% (1h), phí 0,112, funding exact.
> Thêm biến thể KHÓA duy nhất: vào tại close D1 thay D0 (k=2, inflate 1,18).
> Báo: n listing/năm, net mean/median, CI (block theo tháng vì n nhỏ, NREP 2000), theo năm, SL-rate, tail; so với ALL cùng ngày (excess).
> GO-R2 ⇔ net > 0 ngoài CI raw & inflate; ≥3/4 năm; n ≥ 120 listing; excess vs ALL cùng ngày > 0.

## 2. Nguồn dữ liệu
- **1h closes** (nguồn CHÍNH của listing_day, giá, SL): `/home/ubuntu/java/fsrun/CLOSES_1H.bin` (struct `>i8 ts, >i2 sym, >f4 close`;
  2021-01-01 01:00 → 2026-01-01 00:00 UTC; `ts` = thời điểm close được biết ⇒ nến 1h phủ (ts−1h, ts]; ngày UTC của nến = floor((ts−1h)/1 ngày)).
  Sym id → tên: `/home/ubuntu/claudedata/oi/symbol_map.csv`. Chỉ đọc ts ≤ 2026-01-01 00:00 (2026 không chạm).
- **Đối chiếu Aerospike `test.kline_1m_opt`**: qua cache quoteVol ngày `~/claude_master/1002/p0a_cache/qv/*.parquet` (do P0A dựng từ
  kline_1m_opt; cột date/sym/qv/nmin/lastc/nrec; 2021-09-01..2025-12-31; CHỈ ĐỌC). Ngày đầu Aerospike = ngày nhỏ nhất sym có nmin>0.
  Đối chiếu TOÀN BỘ listing (rẻ hơn yêu cầu 10 coin), in 10 mẫu.
- **Funding**: `/tmp/fund_cache.npz` (scan Aerospike `test.funding_data` bởi `funding_sign_reconcile.py`; cách cộng như lớp `Fund`
  của `short_v3_score.py` / `funding_cum` của `short_v2_p0a_statemap.py`): fund = Σ rate có settle ts ∈ (t0, t_exit]. rate>0 ⇒ SHORT NHẬN.
  Đây là "exact" (cộng đúng các kỳ settle thực sự giữ qua, bất kể kỳ 8h/4h/1h). Sym không có record funding trong cửa sổ ⇒ fund=0 (báo tỉ lệ).
- **Universe coin**: symbol kết thúc `USDT`, không chứa `_`; loại BTCUSDT và stable {USDC,BUSD,TUSD,FDUSD,USDP}USDT (như P0A).

## 3. listing_day, D0 close và loại trừ (chốt trước khi đo)
- **L1** `D0` = ngày UTC của nến 1h ĐẦU TIÊN của sym trong TOÀN BỘ CLOSES_1H.bin (nguồn ghi: CLOSES_1H). Coin có nến đầu trước
  2022-01-01 không phải listing.
- **L2** Chỉ giữ D0 ∈ [2022-01-01, 2025-12-24].
- **L3 (gap, không phải niêm yết)**: (a) D0 − ngày đầu file ≥ 90 ngày (tự đúng với D0 ≥ 2022 vì file bắt đầu 2021-01-01, ghi lại);
  (b) nếu Aerospike (qv cache) có dữ liệu của sym ở ngày ≤ D0 − 2 ⇒ ngày đầu trong CLOSES_1H chỉ là gap thu thập ⇒ LOẠI, in danh sách.
  (Dung sai 1 ngày cho lệch biên.) Aerospike có muộn hơn D0 ⇒ chỉ báo, không loại.
- **L5 entry chính "D0"** (QUY TẮC, không phải biến thể): nếu ngày D0 có ≥ 12 nến 1h ⇒ entry = close 1h CUỐI CÙNG có trong ngày D0
  (thông thường ts = (D0+1) 00:00 UTC); nếu < 12 nến ⇒ entry = close 1h cuối cùng của ngày D1. `t0` = ts của close đó, `P0` = close đó.
  Ngày dùng không có nến nào ⇒ loại (báo số).
- **L6 biến thể KHÓA "D1"**: entry = close 1h cuối cùng của ngày D1 (luôn D1; nếu nhánh chính đã fallback D1 thì hai lệnh trùng nhau).
- **L4 cửa sổ**: loại lệnh nếu t0 + 168h > 2026-01-01 00:00 (báo số theo nhánh).

## 4. Chiến lược (KHÓA, 0-sim)
SHORT notional 1 tại P0, giữ 168h. SL: nếu ∃ close 1h với ts ∈ (t0, t0+168h] và close ≥ 1,15·P0 ⇒ thoát tại ts đầu tiên đó,
lỗ giá = 0,15 + 0,002 (quy ước P0A: stop + trượt 0,2%). Không SL ⇒ thoát tại close ở t0+168h (ffill close cuối ≤ t0+168h; nếu sym hết
dữ liệu trước đó ⇒ close cuối, đánh dấu `trunc`).
`net = (SL ? −0,152 : −ret_7d) − 0,00112 + fund`, fund = Σ rate ∈ (t0, t_exit], t_exit = ts SL hoặc t0+168h.
Độ nhạy CHỈ BÁO (không vào luật GO, khai trước): (i) SL thoát tại chính close 1h kích hoạt (lỗ = C/P0 − 1 + 0,002, bảo thủ khi gap);
(ii) fund = 0; (iii) loại listing "giống đổi tên" (có sym khác có nến cuối trong [D0−3, D0+3] và giá đầu mới / giá cuối cũ ∈ ×{1, 1000, 1/1000}
trong ±5%) — chỉ để biết migration/rename có kéo kết quả không.

## 5. Đường giá (mô tả, anchor = (t0, P0) của nhánh chính)
h ∈ {1, 3, 7, 14, 30} ngày: `retEnd_h` = C(t0+24h·h, ffill)/P0 − 1; `maxFav_h` = max close 1h ∈ (t0, t0+24h·h] / P0 − 1 (1h closes ⇒ cận
DƯỚI của squeeze); `pSQ10_h` = P(maxFav_h ≥ +10%). Chỉ listing có t0+24h·h ≤ 2026-01-01 00:00 (n mỗi h khác nhau, ghi n).
Báo mean/median retEnd, mean/median maxFav, pSQ10, P(retEnd ≤ −10%), n. Thêm mô tả `ret_D0intra` = P0 / close nến 1h đầu tiên − 1.

## 6. Funding D0..D+7 (báo riêng)
Mọi kỳ settle của listing với ts ∈ (D0 00:00, D0+8 00:00]: phân vị p1/p5/p25/p50/p75/p95/p99 của rate, mean, tỉ lệ rate<0, tỉ lệ |rate| ≥ 0,1%,
khoảng cách settle trung vị (giờ). Theo lệnh: phân phối fund của nhánh chính (mean, median, p5, p95) và theo năm.

## 7. Thống kê
- Theo nhánh: n, net mean/median, win% (net>0), SL-rate, tail (min net, p1, p5 net), fund mean, ret_7d mean/median.
- **CI block theo THÁNG** (tháng UTC của t0; nb = 48 tháng 2022-01..2025-12): `rng = np.random.default_rng(20260905)`,
  `idx = rng.integers(0, nb, (2000, nb))`, mỗi replicate = Σ net / Σ count trên các tháng rút; percentile 2,5/97,5 ⇒ CI raw.
  **Inflate**: nửa-độ-rộng mỗi phía × 1,18 (PROGRAM: k=2 nhánh D0/D1, √(2 ln 2) = 1,177 ≈ 1,18), tức `[μ − 1,18(μ−lo), μ + 1,18(hi−μ)]`.
  Ghi chú: theo đúng số PROGRAM ghi (bảo thủ hơn quy ước ZK/1,96 của P0A); "CI block (72h)" trong phần chấm chung được PROGRAM §R2
  thay bằng block theo tháng vì n nhỏ.
- **Theo năm** (năm của t0): n, mean, median, SL-rate, CI raw block tháng trong năm (cùng seed).
- **excess vs ALL cùng ngày**: với mỗi lệnh, `ALL_t0` = mean `ret7_j = C_j(t0+168h, ffill)/C_j(t0) − 1` trên mọi coin universe có close
  đúng tại ts t0 (kể cả chính coin listing; raw, không SL, không funding). `excess_short = ALL_t0 − ret_7d(listing)` (dương = listing
  kém thị trường ⇒ thuận short). Báo mean, median, CI raw block tháng.

## 8. Luật GO (áp cơ học)
Mỗi nhánh X ∈ {D0, D1}, PASS_X ⇔ đồng thời:
- **G1** net mean > 0 VÀ cận dưới CI raw > 0 VÀ cận dưới CI inflate > 0;
- **G2** net mean theo năm > 0 ở ≥ 3/4 năm 2022, 2023, 2024, 2025 (năm không có lệnh = không dương);
- **G3** n ≥ 120 listing (lệnh hợp lệ của nhánh);
- **G4** mean `excess_short` > 0.
**GO-R2 ⇔ ≥ 1 nhánh PASS.** Ngược lại NO-GO. Báo từng điều kiện của từng nhánh. Không thêm nhánh, không lọc thêm, không đổi SL/T sau khi thấy số.

## 9. Sanity bắt buộc (báo trong RESULT trước kết luận)
- **S1** n listing theo năm (năm D0) + số bị loại theo L3b/L4/L5, n sym toàn file, n sym có nến đầu ≥ 2022.
- **S2** 10 listing mẫu (rút ngẫu nhiên seed 20260905 từ tập cuối, sắp theo ngày): số nến D0, P0, close cuối ngày D0..D+7, ngày đầu Aerospike ⇒ kiểm tay.
- **S3** Aerospike: tỉ lệ listing có ngày đầu Aerospike khớp D0 (±1 ngày); |lastc_1m(D0)/close cuối ngày D0 − 1| median/p99.
- **S4** tỉ lệ lệnh có funding; số `trunc`; nhất quán SL ⇔ maxFav_7d ≥ 15%.
- **S5** danh sách listing "giống đổi tên" (mục 4.iii).
Sanity lệch (vd S3 khớp < 90%) ⇒ báo rõ, KHÔNG sửa định nghĩa sau khi thấy số.

## 10. Giới hạn đã biết (ghi trước)
- SL/maxFav kiểm trên 1h close ⇒ SL-rate và pSQ là cận dưới; lỗ SL cố định −15,2% lạc quan khi gap (có độ nhạy 4.i).
- Slippage/spread ngày niêm yết, giới hạn đòn bẩy/notional ngày đầu, khả năng mở short ngay D0 trên Binance: CHƯA mô hình.
- Survivorship/độ phủ của CLOSES_1H (sym đã delist có còn trong file hay không): báo số sym, không sửa.
- Script: `research/analysis/short_v3_r2_listing.py` → `docs/result/RESULT_SHORT_V3_R2.json` + `RESULT_SHORT_V3_R2.md`. RAM ≤ 4G, Python `logging`.
