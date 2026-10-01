# RESULT — PARITY HARNESS shadow/242 ↔ BACKTEST (`research/parity/parity_check.py`)

- **Yêu cầu owner (2026-10-01):** viết harness so shadow với backtest; **validate INPUT/OUTPUT chặt**; **deterministic**;
  **LUÔN ra PASS/FAIL/MISSING + exit code** (không "test fail rồi không có kết quả"); tiêu chí **khớp 100 %**.
- **Pre-reg (chốt TRƯỚC):** `docs/prereg/PREREG_PARITY_HARNESS.md`. Harness: `research/parity/parity_check.py`.
- **Report (sinh tự động):** `docs/result/parity_report.json` + `.md` (deterministic, `sort_keys`, **không** timestamp).
- **Ràng buộc đã giữ:** Python thuần; **0 Java/sim**; **242 READ-ONLY** (chỉ `fetch` đọc key non-secret); **0 ONNX**;
  không in secret; **không push file dữ liệu** (chỉ code/doc/JSON/snapshot non-secret); 2026 = **HOLDOUT** (chỉ đo).
- **Ngày chạy:** 2026-10-01 (GMT+7). **Kết quả tổng: `FAIL` (exit_code=2).**

---

## 1. HARNESS — 7 subcommand + 3 tự kiểm (đều ĐẠT)

`python3 research/parity/parity_check.py {config|features|gate|selector|entry|exit|all|selftest|fetch}`

| tự kiểm | kết quả | bằng chứng |
|---|---|---|
| (a) **tiêm lệch** 1 feature (BACKTEST += 1.0) | **PASS** | `hourOfDay` chuyển PASS→**FAIL**, **chỉ** feature đó (`FAIL them moi=['hourOfDay']`) |
| (b) **deterministic** (chạy 2 lần) | **PASS** | stdout **byte-identical**; `parity_report.json` md5 `e153207b…` **= nhau** giữa 2 lần |
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
| **selector** | Java-serialized HashMap | — | — | == | **MISSING** |
| **entry** | **0 entry** (2818/2818 dòng `n_pass=0`) | G2 ≥1 (bất biến thang đo) | 0 vs ≥1 | == | **FAIL** |
| **exit** | ledger **0 lệnh đóng** từ 12/09 | — | — | == | **MISSING** |

**4/33 feature KHỚP** (max\|Δ\|=0): `hourOfDay`, `dayOfWeek`, `weekOfMonth`, `monthOfYear` (feature lịch — instrument ĐÚNG).
**29/33 feature LỆCH** — lớn nhất: `volumeRatioUpDown` (max\|Δ\| **236.3**, corr 0.64) · `volumeSpike` (**122.7**, 0.69) ·
`basketVolSpike` (**79.6**, 0.10) · `rsi14` (**40.3**, 0.86) · `advanceDeclineRatio` (6.64) · `volatilityTermStructure` (1.30).
Ba feature `momentum1M/15M/acceleration` lệch **vì export thiếu nguồn (=0)** — cần tái tạo inline (`RESULT_FEATDIFF_PASS2 §2.1`).

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
(Thêm 1 check MISSING trong tầng gate: p15 phía BACKTEST cần ONNX — bị cấm nên không đo.)

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
