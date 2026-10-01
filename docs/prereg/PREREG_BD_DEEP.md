# PREREG_BD_DEEP — đào sâu `rateDown15MAvg` ("DownAvg15M"): cách tính + ý nghĩa + các NÚT có thể chỉnh

**Ngày chốt:** 2026-10-01 (TRƯỚC khi chạy bất kỳ phép đo nào).
**Chi nhánh:** `module`. **Repo:** `/home/ubuntu/src/BinanceFuturesJava`.
**Yêu cầu owner 2026-10-01:** *"ra lại xem `DownAvg15M` đang được tính ntn, đào sâu ý nghĩa của nó,
có thể chỉnh nó để cải thiện cả strategy hiện tại không"*.

## 0. Phạm vi & ràng buộc (CỨNG)

1. **0-SIM THUẦN OFFLINE (Python).** KHÔNG chạy Java, KHÔNG build, KHÔNG xgboost, KHÔNG job Kaggle,
   KHÔNG sim. Mọi số lấy từ artifact/DATA đã có sẵn trên máy.
2. **KHÔNG chạm/sửa 242.** **KHÔNG sửa `.java`.** **KHÔNG push file dữ liệu.**
3. **DEV ≤ 2025-12-31.** Cửa sổ DEV = `[2021-07-01 00:00, 2025-12-31 00:00)` giờ `Asia/Saigon`
   (khớp `SIM_END_DATE=20251231`); **2026 = HOLDOUT, không đọc, không chạm.**
4. Baseline tham chiếu: `de-p1` = profile `r4_kg0_k16_f015_g155` (n 2517), artifact
   `/home/ubuntu/kaggle_sim/out/de-p1`.
5. Luật quyết định: `docs/runbooks/RISK_APPETITE.md` §9 (4 tầng: T1 rủi ro · T2 bền · T3 non-inferiority
   win% ≥ −2,0pp / TSloss% ≤ +2,5pp · T4 mục tiêu).

## 1. Nguồn dữ liệu (đã kiểm trước khi chốt)

| nguồn | nội dung | dùng cho |
|---|---|---|
| `/home/ubuntu/wfo_ds_x1_2021/market.bin` | `[count:int][ts:long][down:f4][up:f4][down15:f4]` (big-endian), 2 554 812 phút | **toàn bộ** phân bố / tần suất vượt ngưỡng / quét ngưỡng |
| `/home/ubuntu/java/simulator/kaggle_data_hpo/ticker_YYYYMMDD.bin.gz` | 1 phút/ngày → `{sym: (startTime,maxPrice,minPrice,priceClose,priceOpen,totalUsdt)}` | **tái lập ĐÚNG công thức** để quét `N` / cửa sổ / định nghĩa |

**Kiểm chứng nguồn (BẮT BUỘC, làm trước):**
- `market.bin` phải khớp **byte-cấp gần đúng** với cột `dow/up/dow15m` tại entry trong
  `de-p1/storage/printDone.csv`.
- Tái lập `calMarketData` từ ticker bin 1 ngày phải cho `max|Δ|` ≤ 5e-3 (sai khác do `diedSymbol` +
  cửa sổ ấm đầu ngày). Nếu lớn hơn ⇒ dừng, không kết luận.

## 2. Định nghĩa hiện tại (đọc code, TRƯỚC khi đo)

`MarketBigChangeDetector.calMarketData` (`src/main/java/com/binance/chuyennd/tradecore/MarketBigChangeDetector.java`):

- per coin: `rateChange = close/open − 1`; bỏ `diedSymbol`; bỏ nếu `rateChangeBtc > −0.004 && rateChange < −0.15`;
  bỏ nếu `rateChange > +0.3`.
- `rateDown2Symbols{rateChange}` · `rateUp2Symbols{−rateChange}` · `rateMax2Symbols{close/maxPrice − 1}`
  · `rateMin2Symbols{−(close/minPrice − 1)}`, với `maxPrice`/`minPrice` = **max/min của 15 nến 1M gần nhất**
  (`Configs.NUMBER_TICKER_CAL_RATE_CHANGE = 15`).
- `calRateChangeAvg(map, period)`: duyệt TreeMap **tăng dần**, lấy **`period` khoá ĐẦU TIÊN** rồi **lấy TRUNG BÌNH**;
  `period` bị chặn `= min(period, size*4/5)`.
- `rateDownAvg = calRateChangeAvg(rateDown2, 100)` → gọi `MS_DOWN_BIG_AVG` (`-0.03157`) → **BIG_DOWN**.
- `rateDown15MAvg = calRateChangeAvg(rateMax2, 100)` → gọi `MS_DOWN_BIG_AVG_DCA` (`-0.03157`) → **DCA**.
- `isDcaAlt = rateDown15MAvg < THR_DCA || rateDownAvg < THR_DCA/3`.

## 3. Câu hỏi & chỉ số đo (chốt TRƯỚC)

**Q1 — Phân bố/tần suất (VIỆC 1).** Trên toàn DEV: p1/p5/p25/p50/p75/p95/p99/min/max của 3 field;
% phút và **số episode** (0→1) khi vượt từng ngưỡng; tương quan `down` vs `down15`, `down` vs `up`.

**Q2 — Quét NGƯỠNG (VIỆC 2/3).** Grid `−0.020 → −0.10` (11 điểm, gồm −0.03157 hiện tại và −0.05514
giá trị HPO cũ). Chỉ số: `frac` (% phút ON), `minutes`, `episodes`. **Chỉ ĐO TÍN HIỆU — không suy PnL
từ đây** (không có sim ⇒ không được tuyên bố PnL).

**Q3 — Quét `N` / cửa sổ / định nghĩa (VIỆC 2/3).** Trên **mẫu ngày**: TẤT CẢ 54 ngày có BIG_DOWN
+ thêm ngày thường rải đều (tối đa 100 ngày, seed 20261001). Với mỗi biến thể, đo trên **CÙNG tập phút**:
- `n_on` = số phút `< thr`, `episodes` = số 0→1, `jaccard` = |A∩B|/|A∪B| với baseline, `corr` series.
- Biến thể: `N ∈ {20,50,100(base),200,400}` (mode `avg`) · `WIN ∈ {5,15(base),30,60}` ·
  định nghĩa `frac_q ∈ {0.10,0.33,0.50}` (trung bình `q*n` khoá âm nhất — 0.50 = "nửa thị trường dưới đỉnh").

**Tiêu chí kết luận tín hiệu (chốt trước):** một nút được coi là **"đổi được bộ ngày BIG_DOWN"**
nếu `jaccard < 0.8` hoặc `n_on` lệch > 25 % so với baseline. Ngược lại = **"không đổi bộ ngày"**.

## 4. Điều KHÔNG được làm

- KHÔNG chọn/tinh chỉnh ngưỡng dựa trên số đẹp ⇒ mọi ngưỡng chỉ báo cáo dạng đường cong, **verdict = NO-GO/NULL**
  trừ khi có bằng chứng PnL (mà 0-sim KHÔNG có).
- KHÔNG hồi tố; KHÔNG sửa chỉ số sau khi thấy số; mọi lệch ghi là "phát hiện lúc chạy".
- KHÔNG đụng holdout 2026.

## 5. Đầu ra

`research/analysis/bd_deep.py` + `research/analysis/bd_deep_raw.py` → `research/analysis/out/bd_deep_*.json`
→ `docs/result/RESULT_BD_DEEP.md` (+ JSON trong `docs/result/`).
