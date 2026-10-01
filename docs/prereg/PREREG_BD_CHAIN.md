# PREREG_BD_CHAIN — đổi `rateDown15MAvg` ("DownAvg15M") theo TỶ LỆ UNIVERSE `f`, chạy CẢ DÂY CHUYỀN train→pred→sim

**Ngày chốt:** 2026-10-01 (TRƯỚC khi chạy bất kỳ phép đo nào).
**Chi nhánh:** `module`. **Repo:** `/home/ubuntu/src/BinanceFuturesJava`.
**Yêu cầu owner 2026-10-01 12:58:** *"thấy nó là thấy cả loạt từ train, pred rồi sim … cứ làm đi rảnh mà"*.
**Nền (không đổi trong suốt bài):** `profiles/g2_flat3.properties` = `G2 + FLAT3` (md5 FILE `c6d4ef57ecee25c663d2d396ac574c30`).
**Căn cứ thật (đã kiểm):** `docs/result/RESULT_BD_DEEP.md`, `docs/result/RESULT_BD_DEEP_STEER.md` (`b77947f0`).

> ⚠️ **KHÔNG tham chiếu vòng "BD-FRACTION" ở commit `60b7c995`** — vòng đó KHÔNG CÓ THẬT (lỗi báo cáo cũ).
> Bài này làm lại THỰC SỰ từ đầu; mọi số phải sinh ra trong bài này.

---

## 0. Phạm vi & ràng buộc (CỨNG)

1. **Train/pred/sim CHỈ trên KAGGLE.** KHÔNG chạy Java/sim trên Oracle. **Kaggle bận ⇒ DỪNG + báo RÕ.**
2. **KHÔNG chạm/sửa gì trên 242 / ONNX / đường LIVE.** KHÔNG `git add .` / `git add -A` (working tree đang có
   thay đổi DỞ DANG của job khác: `LiveFeatureDump.java`, `DetectEntrySignal2TradeNormal.java`, `parity_check.py`).
3. KHÔNG push file DỮ LIỆU. `df -h /` ~95% ⇒ dọn temp, giữ ≥ 8 G trống.
4. **DEV ≤ 2025-12-31**; **2026 = HOLDOUT, không đọc, không chạm** (`SIM_END_DATE=20251231`).
5. Luật quyết định: `docs/runbooks/RISK_APPETITE.md` §9 (4 tầng).

---

## 1. VIỆC 0 — `rateDown15MAvg` là INPUT MODEL hay RULE? (chốt TRƯỚC khi code)

**KẾT LUẬN: NÓ LÀ CẢ HAI — và đứng trong FEATURE VECTOR của CẢ GATE(33) LẪN SELECTOR(45).**
`rateDown15MAvg` **không chỉ là rule** (BIG_DOWN/DCA/size-adapt); nó **là input của 2 model**:

| model | sự thật | file:line |
|---|---|---|
| **GATE (33 = V3FULL)** | feature thứ **3** `f.momentum15M` nằm trong vector 33 | `ai_ml/onnx/entry/OnnxInferenceManager.java:67` (`(float) f.momentum15M, …`) |
| └ nguồn của `momentum15M` | `features.momentum15M = rate.rateDown15MAvg` | `ai_ml/features/export/entry/ComprehensiveMarketFeatureExtractor.java:94` |
| **SELECTOR (45)** | feature thứ **6** (index 5) = `f.rateDown15MAvg` | `ai_ml/onnx/funding/SelectorOnnxInferenceManager.java:62` |
| └ nguồn của `f.rateDown15MAvg` | `f.rateDown15MAvg = rate.rateDown15MAvg` | `ai_ml/features/export/funding/FundingDataCollectionManager.java:285-286` |
| **rule (song song)** | BIG_DOWN `getMarketStatus1M`; DCA `isDcaAlt`; size-adapt; weak-block | `tradecore/MarketBigChangeDetector.java:169-185`, `tradecore/BdSizeAdapt.java:86-89`, `tradecore/TickWeakBlock.java:135` |

⇒ **HỆ QUẢ (BẮT BUỘC): đổi `rateDown15MAvg` ⇒ PHẢI RETRAIN + PRED LẠI cả dây chuyền**, không được chỉ sim.

---

## 2. DÂY CHUYỀN sẽ chạy (định nghĩa TRƯỚC khi đo)

Đổi `calRateChangeAvg` ⇒ đổi **market-rate** (`rateDownAvg/rateUpAvg/rateDown15MAvg`) ⇒ đổi **cả rule lẫn feature**.
Thứ tự đã chốt (mọi bước train/pred/sim chạy trên Kaggle):

1. **Rebuild market-rate** với `N_f` (từ ticker 1m) → `market.bin` mới (rule path).
2. **Rebuild feature store GATE (33 V3FULL)** — cột `momentum15M` đổi → **retrain 19 fold DEV** (XGBRegressor
   depth 4/150 cây/lr 0.05/seed 42/purge 15′ theo `research/pipeline/gate_feat_study/run_cycle.py`) → **pred**
   `p15_*.csv` (OOS).
3. **Rebuild ledger/pool** (`research/pipeline/ledger.py`, pool = tick `p15 ≥ 0.008`, `T0=2021-04-01`).
4. **Retrain S1** (`research/pipeline/s1_rank.py 2`, LambdaRank, 9 feat, seed 42) → **pred** `pred_s1a2.parquet`.
5. **Rebuild bins** (`research/pipeline/build_map.py s1a2` → `predwf_map_s1a2_*/predict_wf_*.bin`).
6. **ExportWfoDataset** (market/pred/funding.bin + manifest) → **sim** `SimulatorMarketLevelTicker1MStopLoss`
   với `TRADING_PROFILE=profiles/g2_flat3.properties` → `printDone.csv`.

***Fallback (chỉ nếu bước 2–5 chứng minh KHÔNG ảnh hưởng):*** nếu đo được gate-store `momentum15M` không đổi
theo `f` (bất khả — vì nó chính là `rateDown15MAvg`) hoặc nếu S1 không đọc gate, ghi RÕ ở RESULT rồi mới rút
gọn còn sim. **Không được tự ý rút gọn mà không có bằng chứng.**

---

## 3. ĐỊNH NGHĨA `f` (chốt cứng — không đổi sau khi thấy số)

- `N_f = max(1, round(f × |universe|))`, với `|universe|` = `size()` của TreeMap tương ứng tại phút đó
  (SAU bộ lọc `diedSymbol` / `−0,15` / `+0,3`). Sau đó **cap 4/5 cũ VẪN áp dụng** (`period = min(period, size*4/5)`).
- `f ∈ {0.10, 0.30, 0.50, 1.00}`.
- **`f = 0` = giữ `N = 100` cũ = byte-identical** (parity, không phải một arm).
- Code thêm key **`SIM_BD_FRACTION`** (default `0`): `Configs.BD_FRACTION` + nhánh trong
  `MarketBigChangeDetector.calRateChangeAvg` (`MarketBigChangeDetector.java:149`). **KHÔNG chạm 242.**
- `SimCal`: `f=1.00` ⇒ `N=size` rồi cap `4/5` (khác f=0 khi size≠100).

---

## 4. CHỈ SỐ + CỔNG + CI (đo TRƯỚC, chốt TRƯỚC)

- **Cổng parity (BẮT BUỘC):** `f=0` phải tái lập `G2 + FLAT3` — **md5 `printDone.csv` = `650c386f0d0dfea334af9d55ca2f21d4`**
  (n 2517, equity 131908). Lệch ⇒ **DỪNG + báo RÕ**, không chấm tiếp.
- **Chấm:** `research/analysis/reset_rule_score.py` (§9) @ cost **base** (0,112 %) và **stress** (0,150 %),
  **theo NĂM**.
- **Chỉ số chính:** ON-rate BIG_DOWN/DCA · `n` leg · T3 (win% / TSloss%) · UW · maxDD (phút) · `q*` · `conc` · **Calmar**.
- **CI:** bootstrap **block 72 h**, **2000 reps**, seed `20260905`, nới **×1,21**; `k = 19` (INFL `sqrt(2 ln 19)`).
- **Tầng (RISK_APPETITE §9):** T1 rủi ro (maxDD≤40 · UW≤250 · q*≥−20 · conc≤15 · gross≤70) · T2 bền · T3 non-inferiority
  (win% ≥ −2,0 pp / TSloss% ≤ +2,5 pp) · T4 mục tiêu (Calmar).

---

## 5. LUẬT KẾT LUẬN (chốt TRƯỚC)

- **GO** cho một `f` ⟺ (a) parity `f=0` PASS; (b) `f` **qua CẢ 4 TẦNG** vs `G2` gốc; (c) **≥ 2 chỉ số chất lượng**
  (win%/TSloss%/mP|SM/mP|SL — KHÔNG tính `n`/mMargin) **dịch cùng chiều NGOÀI CI** 72h×1,21.
- **NO-GO / NULL** nếu ngược lại. Ghi rõ `f` **đang giữ** (mặc định `f=0` ⇒ N=100 nếu NULL).
- **Báo cáo thêm (bắt buộc):** xu hướng theo NĂM (ON-rate 2023 vs 2025) — đặc trưng non-stationarity đã ĐO ở
  `RESULT_BD_DEEP §3.4`; arm nào **không ra lệnh** ⇒ ghi **NO-CALL + `n_pass`**, KHÔNG bịa.

---

## 6. LUẬT DỪNG

- **Kaggle bận** (`kaggle kernels list --status running` có job) ⇒ **DỪNG + báo RÕ** (có thể là job khác).
- Mọi `git add` **CHỈ** đường-dẫn file của mình. Commit SỚM + push.
