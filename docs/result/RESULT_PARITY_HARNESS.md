# RESULT — PARITY HARNESS shadow/242 ↔ BACKTEST (`research/parity/parity_check.py`)

> ⚠️ **BẢN CŨ (V1).** Số ở §2B dưới đây là của V1 (khi export field market **chưa** được tái tạo inline, và chưa có
> nguồn non-ONNX cho gate). **BẢN HIỆN HÀNH: `docs/result/RESULT_PARITY_HARNESS_V2.md`** + `docs/result/parity_report.{json,md}`
> (tái tạo inline `momentum1M/15M`; field market khớp mức nhiễu ~1e-3; có `pred.bin` cho p15 DEV).

- **Yêu cầu owner (2026-10-01):** viết harness so shadow với backtest; **validate INPUT/OUTPUT chặt**; **deterministic**;
  **LUÔN ra PASS/FAIL/MISSING + exit code** (không "test fail rồi không có kết quả"); tiêu chí **khớp 100 %**.
- **Pre-reg (chốt TRƯỚC):** `docs/prereg/PREREG_PARITY_HARNESS.md`. Harness: `research/parity/parity_check.py`.
- **Report (sinh tự động):** `docs/result/parity_report.json` + `.md` (deterministic, `sort_keys`, **không** timestamp).
- **Ràng buộc đã giữ:** Python thuần; **0 Java/sim**; **242 READ-ONLY** (chỉ `fetch` đọc key non-secret); **0 ONNX**;
  không in secret; **không push file dữ liệu** (chỉ code/doc/JSON/snapshot non-secret); 2026 = **HOLDOUT** (chỉ đo).
- **Bổ sung STEER owner 10:45:** thêm tầng `marketparams` audit tham số market `rateDown15MAvg` (+3 field market) — xem §2B.
- **Ngày chạy:** 2026-10-01 (GMT+7). **Kết quả tổng: `FAIL` (exit_code=2).**

---

## 1. HARNESS — 10 subcommand + 3 tự kiểm (đều ĐẠT)

`python3 research/parity/parity_check.py {config|features|gate|marketparams|selector|entry|exit|all|selftest|fetch}`

| tự kiểm | kết quả | bằng chứng |
|---|---|---|
| (a) **tiêm lệch** 1 feature (BACKTEST += 1.0) | **PASS** | `hourOfDay` chuyển PASS→**FAIL**, **chỉ** feature đó (`FAIL them moi=['hourOfDay']`) |
| (b) **deterministic** (chạy 2 lần) | **PASS** | stdout **byte-identical**; `parity_report.json` md5 `17c28162…` **= nhau** giữa 2 lần |
| (c) **xoá 1 cột** input (`momentum5M`) | **PASS** | **FAIL kèm lý do** `"thieu cot trong export: momentum5M"` — **không crash**, **không 0-kết-quả** |

Ngoài ra: artifact feat_dump bị **cắt cụt 6/6 file** (đang ghi/copy dở) ⇒ harness **phục hồi các dòng hoàn chỉnh**
(zlib partial), ghi `input.integrity` (pairs=385) — **không crash**.

---

## 2. BẢNG TẦNG — LIVE vs BACKTEST vs LỆCH vs PASS/FAIL

| tầng | LIVE (242) | BACKTEST (baseline `g2_flat3`) | lệch | ngưỡng | kết |
|---|---|---|---|---|---|
| **config** | 4 LECH + 18 MISSING | profile 31 key | — | == | **FAIL** |
| **features** | feat_dump BTCUSDT (385 cặp ts) | export DEV cùng phút | **29/33 feature** vượt \|Δ\| | max\|Δ\| ≤ 1e-8 | **FAIL** |
| **gate** | mode=**fixed**, p15_max **0.0150** | mode=**ratio** (G2) | thr 0.0326 **>** p15_max | mode khớp | **FAIL** (1 check MISSING) |
| **marketparams** (STEER 10:45) | `rateDownAvg/rateDown15MAvg` thật | export **=0** 100% cửa sổ | 2/2 field lệch; **385/385** phút field chết | max\|Δ\| ≤ 1e-8 & flip=0 | **FAIL** (2 field MISSING) |
| **selector** | Java-serialized HashMap | — | — | == | **MISSING** |
| **entry** | **0 entry** (2818/2818 dòng `n_pass=0`) | G2 ≥1 (bất biến thang đo) | 0 vs ≥1 | == | **FAIL** |
| **exit** | ledger **0 lệnh đóng** từ 12/09 | — | — | == | **MISSING** |

**4/33 feature KHỚP** (max\|Δ\|=0): `hourOfDay`, `dayOfWeek`, `weekOfMonth`, `monthOfYear` (feature lịch — instrument ĐÚNG).
**29/33 feature LỆCH** — lớn nhất: `volumeRatioUpDown` (max\|Δ\| **236.3**, corr 0.64) · `volumeSpike` (**122.7**, 0.69) ·
`basketVolSpike` (**79.6**, 0.10) · `rsi14` (**40.3**, 0.86) · `advanceDeclineRatio` (6.64) · `volatilityTermStructure` (1.30).
Ba feature `momentum1M/15M/acceleration` lệch **vì export thiếu nguồn (=0)** — cần tái tạo inline (`RESULT_FEATDIFF_PASS2 §2.1`).

---

## 2B. STEER owner (2026-10-01 10:45) — AUDIT THAM SỐ MARKET `rateDown15MAvg`

Ánh xạ đã xác minh (`ComprehensiveMarketFeatureExtractor.java:93-94`): **`momentum1M = rateDownAvg`**, **`momentum15M = rateDown15MAvg`**.
`rateDown15MAvg` chạy vào **4 nơi** (BIG_DOWN `:174-186`, DCA `:188-191`, `TickWeakBlock:135` DROP15M, `BdSizeAdapt:90`).

**(1) 4 field market tại cùng phút** (385 cặp):

| field | cột | max\|Δ\| | mean\|Δ\| | corr | kết |
|---|---|---|---|---|---|
| `rateDownAvg` | momentum1M | **0.0091** | 0.0016 | nan (BT hằng 0) | **FAIL** |
| `rateDown15MAvg` | momentum15M | **0.0249** | 0.0127 | nan (BT hằng 0) | **FAIL** |
| `rateUpAvg` | — | — | — | — | **MISSING** (không có trong CSV) |
| `rateUp15MAvg` | — | — | — | — | **MISSING** (không có trong CSV) |

**(2) Ngưỡng:** `MS_DOWN_BIG_AVG`, `MS_DOWN_BIG_AVG_DCA`, `MS_UP_BIG_THRES` (+ alias `SIM_MS_*`): **242 unset & baseline unset**
⇒ cả hai dùng **cùng default Java** `-0.03157 / -0.03157 / 0.02046` (`Configs.java:465-470`) ⇒ **MATCH-DEFAULT (PASS)** — ngưỡng KHÔNG phải nguồn lệch.

**(3) Tác động lên quyết định (đo bằng số lần ĐỔI TRẠNG THÁI, không chỉ max|Δ|):** trên 385 phút ghép,
BIG_DOWN flip = **0**, DCA flip = **0** (cả hai bên đều 0 vì live 2026-09-28 là ngày yên: `rateDown15MAvg` min **-0.0249 > -0.0316**)
**NHƯNG** phía BACKTEST field **= 0 (chết) ở 385/385 = 100%** cửa sổ ⇒ BIG_DOWN/DCA **không thể kích hoạt từ field này**.
Trên **toàn export 2026-07→09** field chết **68 902/129 137 = 53.4%** số phút (60 phút còn lại mới vượt ngưỡng) ⇒
**nguồn market của export bị khuyết nặng** — đây chính là "lệch nhiều nơi" (BIG_DOWN + DCA + weak-block + size-adapt cùng chết).

**Đề xuất:** bật lại nguồn `MarketBigChangeDetector.calMarketData` (inline) cho exporter trước khi dùng export làm backtest;
xuất thêm `rateUpAvg/rateUp15MAvg` ra CSV để đo đủ 4 field. *(Ghi rõ: đây là **STEER của owner 10:45**.)*

---

## 3. TRẢ LỜI

**(1) 242 có khớp `G2 + FLAT3` không? → KHÔNG.** (tầng config)
- **LECH (4):** `SIM_GATE_DYN_SCALE` 1.55→**1.70** · `SIM_RATE_PROFIT_STOP_MARKET` 0.07→**0.05** ·
  `DCA_GRID_WEIGHTS` 1,1,1,1→**1,0,0,0** · `CAPITAL_START` 35000→**14000**.
- **MISSING (18):** **toàn bộ** gate rolling (`SIM_/LIVE_GATE_ROLLING_MODE/DAYS/PCT`) ⇒ gate **fixed** ·
  `TS_GIVEBACK_RATIO`(→default **0.5**) · `SIM_TS_MAX_GAP`(→**0.08**) ⇒ exit **T0** · `SIM_TS_GIVEBACK` ·
  `SIM_LOSER_TIME_STOP_HOURS` · `DCA_GRID_SCALE` · `SIM_F_BASE`(→**0.03**) · `SIM_RATE_FEE`(→**0.002**) ·
  `SIM_SLIPPAGE_RATE`(→**0.003**) · `SIM_FIX_B1/B2/B3` · `SIM_BREAKER_MODE` · `CONC_CAP_PERCOIN_ENABLED/PCT` ·
  `SELECTOR_ONLY_ENTRY`.
- MATCH=5 (`SELECTOR_RANK_TOPK`, `SIM_MIN_MOMENTUM_15M`, `TIER_FLAT`, `SIM_ENTRY_SAMPLE_MIN`, `SIM_TS_MAX_GAP_WEAK`).

**(2) Tầng dữ liệu nào lệch?** → **features 29/33** (số ở §2) và **gate/entry**: p15 live max **0.0150 < thr 0.0326** ⇒
**n_pass=0**; gate mode **fixed ≠ ratio**; entry **0 vs ≥1**. Tầng **config** lệch (4+18 key) là **nguyên nhân gốc**.

**(3) Tầng nào MISSING + lý do?** → **selector**: artifact live là Java-serialized `HashMap<String,Float>`
(`storage/data/predictionSymbol/*`), không có score CSV đọc được, và **không có** artifact selector BACKTEST cùng tick.
→ **exit**: 242 **không có lệnh đóng nào từ 12/09** (gate đóng trước) ⇒ không có dữ liệu thoát để so FLAT3 vs T0.
(Thêm MISSING: `rateUpAvg`/`rateUp15MAvg` không có trong CSV artifact; p15 phía BACKTEST cần ONNX — bị cấm nên không đo.)

**(4) Đề xuất TỐI THIỂU để khớp 100 % (trình bày — KHÔNG tự sửa 242, cần restart):**
1. Thêm `conf/env.sh`: `LIVE_GATE_ROLLING_MODE=ratio`, `LIVE_GATE_ROLLING_PCT=0.999950829`, `LIVE_GATE_ROLLING_DAYS=90`
   (jar đang chạy `c389b4be…` **đã có** `LiveGateRollingRatio` ⇒ chỉ thêm key + restart).
2. Thêm `TS_GIVEBACK_RATIO=1.0`, `SIM_TS_MAX_GAP=0.03`, `SIM_TS_MAX_GAP_WEAK=0.03`, `SIM_TS_GIVEBACK=1`,
   `SIM_LOSER_TIME_STOP_HOURS=168`.
3. Đổi `SIM_GATE_DYN_SCALE` 1.70→**1.55**; `SIM_RATE_PROFIT_STOP_MARKET` 0.05→**0.07**;
   `DCA_GRID_WEIGHTS` 1,0,0,0→**1,1,1,1**; `CAPITAL_START` **14000→35000**.
4. Thêm `SIM_F_BASE=0.015`, `SIM_RATE_FEE=0.000982`, `SIM_SLIPPAGE_RATE=0.000067`, `SIM_FIX_B1/B2/B3=true`,
   `CONC_CAP_PERCOIN_ENABLED=true`, `CONC_CAP_PERCOIN_PCT=0.15`, `SIM_BREAKER_MODE=OFF`.
5. (features) Bật tái tạo **inline** cho `momentum×3` trong export; điều tra `volume*`/`volatilityTermStructure`
   (`RESULT_FEATDIFF_PASS2 §3`). **Lưu ý:** bật G2 chỉ đưa `n_pass` từ 0 → **rất nhỏ nhưng khác 0** — theo dõi ledger.
- **Cần thêm để đo được 2 tầng MISSING:** thêm cột `selectorScore`+`rank` vào dump CSV (cả live lẫn export) và
  dump `p15` phía DEV ra CSV ⇒ khi đó harness đo được selector + gate-p15 parity mà **không chạm ONNX**.

---

## 4. MỤC BỎ / KHÔNG LÀM (khai rõ)

- **Bỏ** chạy sim/Java/WFO trên Oracle (ràng buộc cứng); không cần Kaggle vì không có Java mới.
- **Bỏ** ONNX inference ⇒ check `gate.p15_dev_parity` = **MISSING** (đã ghi lý do + đề xuất CSV), **KHÔNG** tính PASS.
- **Bỏ** đo selector/exit live (thiếu nguồn đối ứng) ⇒ **MISSING + lý do + đề xuất**, không bịa PASS.
- **KHÔNG** sửa bất kỳ file nào trên 242; mọi thay đổi config chỉ **trình bày** ở §3(4).
- **KHÔNG** dùng 2026 để chọn/tune; chỉ audit/đối chiếu.
- **STEER 10:45:** tầng `marketparams` đo **2/4 field** (`rateDownAvg`,`rateDown15MAvg`); 2 field `rateUp*` **MISSING** (không có trong CSV).
  Kernel field, threshold parity, và impact đã ghi ở §2B; đề xuất bật nguồn inline cho exporter + xuất `rateUp*` ra CSV.
