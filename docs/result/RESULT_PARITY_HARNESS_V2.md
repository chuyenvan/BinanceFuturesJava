# RESULT V2 — PARITY HARNESS (`research/parity/parity_check.py`)

> V2 = V1 (commit `15021fc3`) + **tầng `marketparams` đo thật** + **làm các tầng MISSING đo được**.
> Harness: `research/parity/parity_check.py`. Report tự sinh: `docs/result/parity_report.{json,md}`.
> Pre-reg gốc: `docs/prereg/PREREG_PARITY_HARNESS.md` (không sửa). Ngày 2026-10-01 (GMT+7).

> ⛔ **2026 = HOLDOUT**: mọi số 2026 (nhất là LIVE 2026-09) **chỉ audit/đối chiếu**, KHÔNG chọn/tune tham số.
> Ràng buộc giữ đủ: **Python thuần · 0 Java/sim trên Oracle · 242 READ-ONLY · 0 ONNX · không push data · không in secret.**

## 0. KẾT QUẢ TỔNG: `FAIL` (exit_code=2)

| tầng | trạng thái | V1 → V2 |
|---|---|---|
| config | **FAIL** | không đổi (4 LECH + 18 MISSING) |
| features | **FAIL** | 29/33 → **27/33** vượt ngưỡng (2 feature market PASS sau tái tạo inline) |
| gate | **FAIL** | thêm nguồn p15 DEV **không-ONNX**; vẫn MISSING cùng-phút (không overlap) |
| **marketparams** | **MISSING** | **MỚI**: 2/4 field đo được (khớp mức nhiễu), 2 field MISSING; **flip LIVE = 0/0**, DEV(stress) = 0/1 |
| selector | **MISSING** | đo được "vì sao" (không có cột score/rank) |
| entry | **FAIL** | không đổi (0 vs ≥1) |
| exit | **MISSING** | không đổi |

Selftest: (a) tiêm lệch, (b) deterministic, (c) xoá cột — **3/3 PASS**.

---

## 1. VIỆC 1 — TẦNG `marketparams` (STEER owner 10:45)

**Ánh xạ đã xác minh** (`ComprehensiveMarketFeatureExtractor.java:93-94`): `momentum1M = rateDownAvg`, `momentum15M = rateDown15MAvg`.
`MarketDataObject` chỉ có **3 field có nghĩa** (`rateDownAvg/rateUpAvg/rateDown15MAvg`); `rateUp15MAvg` **không** được `calMarketData` tính (luôn 0).

### (1) Field LIVE vs BACKTEST tại cùng phút

Không có overlap ts trực tiếp LIVE(2026-09) ↔ store BACKTEST `market.bin`(2021-01-01→2025-12-31). Bắc cầu bằng **tái tạo INLINE** (`md_inline` = port Python của `MarketBigChangeDetector.calMarketData`) — chạy trên CÙNG phút, CÙNG thuật toán export dùng:

| field | cột LIVE | n | max\|Δ\| | mean\|Δ\| | corr | kết |
|---|---|---|---|---|---|---|
| `rateDownAvg` | momentum1M | 502 | **7.49e-4** | 4.48e-5 | **0.9949** | PASS (≤1e-3) |
| `rateDown15MAvg` | momentum15M | 502 | **7.40e-4** | 5.59e-5 | **0.9996** | PASS (≤1e-3) |
| `rateUpAvg` | — | — | — | — | — | **MISSING** (feat_dump KHÔNG xuất) |
| `rateUp15MAvg` | — | — | — | — | — | **N/A** (không được tính) |

Kiểm chéo phía DEV (store ↔ inline, ngày crash **2025-10-10**, n=1376): `rateDownAvg` max|Δ|=9.79e-4 corr 0.9970 · `rateDown15MAvg` max|Δ|=2.03e-3 corr 0.9977.
⇒ 2 phía (LIVE-tick-loop và store-backtest) **đều tái lập được ở mức ~1e-3** ⇒ lệch chỉ là **nhiễu ticker-vs-kline**, KHÔNG phải lỗi logic. **2/4 field MISSING** vì dump CSV không có.

### (2) Ngưỡng

`MS_DOWN_BIG_AVG`, `MS_DOWN_BIG_AVG_DCA`, `MS_UP_BIG_THRES` (+ alias `SIM_MS_*`): **242 unset & baseline unset** ⇒ cả hai dùng **cùng default Java** `-0.03157 / -0.03157 / 0.02046` (`Configs.java:465-470`) ⇒ **MATCH-DEFAULT**. Ngưỡng KHÔNG phải nguồn lệch.

### (3) TÁC ĐỘNG — số phút **BIG_DOWN / DCA ĐỔI TRẠNG THÁI**

| cửa sổ | n phút | BIG_DOWN flip | DCA flip | ghi chú |
|---|---|---|---|---|
| LIVE 2026-09-28 (LIVE vs inline) | 502 | **0** | **0** | ngày yên: `rateDown15MAvg` min ≈ -0.0249 > -0.0316; biên (6.7e-3) ≫ nhiễu (7.5e-4) |
| DEV 2025-10-10 (store vs inline) | 1376 | **0** | **1** | ngày crash: 1 phút DCA lệch (store bật, inline không) |

⇒ Trên cửa sổ LIVE **0 quyết định đổi trạng thái**; trên ngày crash DEV **1 phút DCA / 1376** (~0.07 %).

### (3b) TÁC ĐỘNG THẬT của "nguồn chết" trong export (cái owner lo)

Field market của export bị **= 0 (chết)** ở **68.902/129.137 = 53,4 %** số phút (2026-09: **100 % chết**; 2026-08 từ 14/08 chết dần). Với field = 0 thì `0 < -0.03157` = false ⇒ **BIG_DOWN + DCA bị khoá OFF** trong backtest ở đúng các phút đó. Từ `market.bin`, tỉ lệ phút có trigger DCA là **8.263/2.554.812 = 0,32 %** ⇒ ước lượng **~220 phút** trong cửa sổ export bị quyết định sai (OFF thay vì ON). Đây chính là "**lệch nhiều nơi**": 4 nơi cùng ăn `rateDown15MAvg` (BIG_DOWN, DCA/`isDcaAlt`, `TickWeakBlock` DROP15M, `BdSizeAdapt`) đều chết cùng lúc.

### (4) MISSING + đề xuất
- `rateUpAvg` / `rateUp15MAvg`: **MISSING** — không có trong feat_dump/export CSV. **Đề xuất:** thêm 4 cột market vào `feat_dump` + export.
- LIVE↔store cùng phút: **MISSING** — không overlap thời gian. **Đề xuất:** chạy lại export có `--md-inline` để sinh market cho cả cửa sổ (Kaggle/Java), khi đó so trực tiếp.

---

## 2. VIỆC 2 — LÀM CÁC TẦNG MISSING ĐO ĐƯỢC

### 2.1 features — tái tạo INLINE + xử lý file cắt cụt
- **Tái tạo inline** `momentum1M/15M/acceleration` phía BACKTEST (thay field chết = 0) bằng `md_inline` (port `calMarketData`, đọc kline 242 READ-ONLY). Ngưỡng thực dụng cho 3 feature này: **1e-3** (nhiễu ticker-vs-kline đo được 7.5e-4); 30 feature còn lại vẫn ngưỡng máy **1e-8**.
- **Kết quả: 29/33 → 27/33 feature vượt ngưỡng.** `momentum1M` (max 7.5e-4) và `momentum15M` (7.4e-4) **PASS**; `momentumAcceleration` **VẪN FAIL** (max 2.2e-3, corr 0.9945) — **lý do:** = `momentum5M − momentum15MAvg`, mà `momentum5M` LIVE≠export (max 2.2e-3), không phải do phần market.
- **File cắt cụt:** **6/6** và **CẢ file 242 mới nhất (20261001_090200)** thiếu gz trailer ⇒ **GỐC = writer Java không finalize `GZIPOutputStream`**. Harness **phục hồi toàn bộ dòng hoàn chỉnh** bằng partial-inflate (`zlib.decompressobj`) ⇒ pairs vẫn dùng được (385 cặp), **không crash**. **Đề xuất:** sửa writer gọi `flush()/close()` (rotating) rồi mới copy.
- 27 feature còn lệch là **lệch GIÁ TRỊ THẬT tại cùng phút** (không phải thiếu nguồn) — nhóm lớn nhất: `volumeRatioUpDown` 236.3 · `volumeSpike` 122.7 · `basketVolSpike` 79.6 · `rsi14` 40.3 · `advanceDeclineRatio` 6.64 · `volatilityTermStructure` 1.30 (đã định lượng tác động ≤0,006 pp lên p15 ở `RESULT_FEATDIFF_PASS2 §3`).

### 2.2 selector
**VẪN MISSING** (không bịa). Bằng chứng: feat_dump **không có** cột `selectorScore`/`rank` (36 cột); artifact LIVE là Java-serialized `HashMap<String,Float>` (`storage/data/predictionSymbol/*`) mà **lần ghi cuối = 2026-08-20**, KHÔNG phủ cửa sổ LIVE 2026-09-28; không có artifact selector BACKTEST cùng tick.
**Đề xuất:** thêm cột `selectorScore`+`rank` vào `feat_dump` (cả live lẫn export) ⇒ đo rank-overlap/top-K **không cần ONNX**.

### 2.3 gate-p15-dev — tìm nguồn không-ONNX
Đã tìm được nguồn **không-ONNX**: **`pred.bin`** = `int n + n×(long ts, float predReturn15M, float predRisk4H)` (`WfoDataset.writePred`), **n = 2.500.260**, ts **2021-03-31 → 2025-12-31**. **Nhưng KHÔNG phủ cửa sổ LIVE (2026-09)** ⇒ **không so cùng phút được** ⇒ giữ **MISSING + lý do**. (LIVE gate: `p15_max = 0.0150 < thr_min 0.03257` ⇒ n_pass=0; mode `fixed` ≠ baseline `ratio`.)

---

## 3. TRẢ LỜI CÂU HỎI

1. **marketparams — field nào lệch + bao nhiêu lần BIG_DOWN/DCA đổi trạng thái?**
   → Đo được `rateDownAvg` (max|Δ| **7.5e-4**, corr 0.9949) và `rateDown15MAvg` (**7.4e-4**, 0.9996) — khớp **mức nhiễu**, không phải lệch logic. **`rateUpAvg`/`rateUp15MAvg` MISSING** (không có trong CSV).
   → **Số lần đổi trạng thái: LIVE = `BIG_DOWN 0 / DCA 0`** (502 phút); **DEV stress 2025-10-10 = `BIG_DOWN 0 / DCA 1`** (1376 phút). Cái độc hại là **export = 0 (chết) 53,4 % số phút** ⇒ BIG_DOWN/DCA bị khoá OFF trong backtest (~220 phút ước lượng), không phải do ngưỡng (ngưỡng MATCH default).
2. **features — còn bao nhiêu cặp vượt ngưỡng sau tái tạo inline?**
   → **27/33** (từ 29/33). `momentum1M`, `momentum15M` **PASS**; `momentumAcceleration` vẫn FAIL (do `momentum5M` lệch, không do market). 26 feature còn lại lệch **giá trị thật** (nhóm volume/volatility/rsi/breadth).
3. **selector / gate-p15 đã đo được chưa?**
   → **Chưa.** selector = **MISSING** (không có score/rank; artifact chết từ 2026-08-20). gate-p15-dev = **MISSING cùng-phút** (nguồn không-ONNX `pred.bin` **có** nhưng hết 2025-12-31, không phủ LIVE 2026-09). Đã **loại trừ ONNX** đúng ràng buộc.
4. **Đề xuất tối thiểu để khớp 100 %** (xem §4).

---

## 4. ĐỀ XUẤT TỐI THIỂU (KHÔNG tự sửa 242 — cần restart)

**(A) config (nguyên nhân gốc — như V1):** thêm `LIVE_GATE_ROLLING_MODE=ratio`, `LIVE_GATE_ROLLING_PCT=0.999950829`, `LIVE_GATE_ROLLING_DAYS=90`; `TS_GIVEBACK_RATIO=1.0`, `SIM_TS_MAX_GAP=0.03`, `SIM_TS_GIVEBACK=1`, `SIM_LOSER_TIME_STOP_HOURS=168`; đổi `SIM_GATE_DYN_SCALE` 1.70→1.55, `SIM_RATE_PROFIT_STOP_MARKET` 0.05→0.07, `DCA_GRID_WEIGHTS` 1,0,0,0→1,1,1,1, `CAPITAL_START` 14000→35000; thêm `SIM_F_BASE=0.015`, `SIM_RATE_FEE=0.000982`, `SIM_SLIPPAGE_RATE=0.000067`, `SIM_FIX_B1/B2/B3=true`, `CONC_CAP_PERCOIN_ENABLED=true`, `CONC_CAP_PERCOIN_PCT=0.15`, `SIM_BREAKER_MODE=OFF`.
**(B) marketparams:** chạy lại exporter với `--md-inline` (Kaggle) → market cho cả cửa sổ; **xuất thêm `rateUpAvg/rateUp15MAvg`** ra CSV.
**(C) đo được 2 tầng MISSING:** thêm cột `selectorScore`+`rank` vào feat_dump (live+export); dump `p15` DEV ra CSV.
**(D) writer dump:** `GZIPOutputStream.flush()/close()` để hết cắt cụt.
**(E) 26 feature lệch thật:** soi `volume*`/`volatility*`/`rsi` (định hướng `RESULT_FEATDIFF_PASS2 §3`).

---

## 5. MỤC BỎ / LÝ DO (khai rõ)

- **Bỏ** chạy Java/sim/WFO trên Oracle (ràng buộc cứng) ⇒ **không** tự tính lại market cho cả cửa sổ export (đề xuất Kaggle).
- **Bỏ** ONNX ⇒ `gate.p15_dev_parity` = **MISSING** (đã chỉ ra nguồn thay thế không-ONNX `pred.bin`, nhưng không overlap).
- **Bỏ** bịa PASS cho selector/exit ⇒ giữ **MISSING + lý do + đề xuất**.
- **KHÔNG** sửa bất kỳ file trên 242; **KHÔNG** push file dữ liệu (chỉ code/doc/JSON/snapshot non-secret).
- **KHÔNG** dùng 2026 để chọn/tune.
