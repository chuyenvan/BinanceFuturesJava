# WFO_DATA_PIPELINE_MASTER — Nguồn sự thật SỐNG toàn trình dữ liệu WFO

> **VERSION: 1.1.2** (2026-08-05) — bump version mỗi khi 1 trong các script/file
> được nêu ở tài liệu này đổi HÀNH VI DỮ LIỆU (không phải mọi sửa code, chỉ khi
> output/format/semantics của tầng thay đổi). Đây là tài liệu vận hành DUY NHẤT
> operator tra khi WFO có vấn đề — không phải phụ, không phải snapshot.

> File này viết theo THỨ TỰ LUỒNG DỮ LIỆU thật (không theo mức độ quan trọng):
> ticker → market → OI → funding label → Tool1 feature → selector (train+predict)
> → gate (độc lập) → WFO dataset export → validate → consume.

## Version History

| Version | Ngày | Thay đổi |
|---|---|---|
| 1.0.0 | 2026-08-04 | Khởi tạo tài liệu master, hợp nhất trạng thái canonical lưới 1-phút: fold-0 leak fix (2026-08-03), PURGE_STEPS grid-relative fix (2026-08-04), LABEL_STEP_MIN/FF_GRID_MIN/SELECTOR_GRID_MIN=1, FIRST_CUTOFF=20230101 (lối A), WFO_SEL_HORIZON_IDX=0 canonical, manifest tự-stamp thật (2026-08-03), CHUNK_YEARS byte-identical verify (2026-08-04). |
| 1.1.0 | 2026-08-04 | Thêm CE-button/pipeline cho toàn bộ buộc A-E (`orchestrator/mcp_tools-v3.py`: atom mới `label_export`/`tool1_export`/`wfo_validate` + vá `wfo_build_ds` thêm `code_sha`; pipeline mới `orchestrator/pipelines/wfo_canonical_1m.json`; kernel Kaggle mới `orchestrator/kernels_wfo1m/selector-predict-1m/`) theo rule R1 (`ce-buttons.md`) — Runbook giờ ưu tiên `ce pipe_run wfo_canonical_1m`, lệnh SSH tay hạ xuống làm tham chiếu. GAP còn treo: chưa có atom upload/version Kaggle dataset (gate bằng `llm_gate`); 3 atom mới CHƯA test thật trên Oracle (SSH session hỏng lúc viết) — chờ `ce --sync bg_selftest`. |
| 1.1.1 | 2026-08-04 | Lấp GAP upload dataset: thêm atom `kaggle_dataset_push`/`kaggle_dataset_status` (pattern lấy từ `run_106_headless.sh` B2 đã chạy thật, không suy đoán). Pipeline `wfo_canonical_1m.json` giờ tự push+chờ ready 2 dataset Tool1/label 1-phút, bỏ `gate_dataset_upload` (llm_gate) — chỉ còn `gate_sign` (chủ ý giữ, không phải gap). Tự bắt và sửa 1 lỗi thiết kế: `_subst` không resolve tham chiếu lồng giữa params (1 pass), đã đổi `label_csv` từ tham chiếu `${label_dataset_dir}` sang literal. |
| 1.1.2 | 2026-08-05 | **Chỉ đổi phạm vi EXPORT, GIỮ NGUYÊN "lối A".** Uni xác nhận `FIRST_CUTOFF=20230101` vẫn ĐÚNG (fold đầu train full từ `ts_min=20210101` tới `20230101 − 72h purge` — đúng thiết kế sẵn có, không đổi). Việc "gen từ 20210101 tới 20260701" chỉ là phạm vi **export** `label_export`/`tool1_export` (đã đúng `start=20210101` từ 08-04) — thêm `end=20260701` (trước để rỗng). *(Session này có 1 lần sửa nhầm `FIRST_CUTOFF`→`20210101` + `EXPECT_LEAKFREE`→`2021-01-01`, đã REVERT lại đúng ngay trong phiên — xem `tasks/251-*.md` để tránh lặp nhầm.)* |

---

## ⚠️ CẢNH BÁO NỔI BẬT — 5 điểm rủi ro/bug đã biết (đọc trước khi làm bất cứ gì)

1. **`FF_GRID_MIN` (tầng 5) phải khớp `LABEL_STEP_MIN` (tầng 4).** Lệch lưới =
   mất ~93% dữ liệu ÂM THẦM khi join (symbol, ts) — KHÔNG lỗi, KHÔNG crash, chỉ
   ít training rows hơn mà tưởng là bình thường. Đây là rủi ro âm thầm nguy hiểm
   nhất trong toàn pipeline.
2. **`WFO_SEL_HORIZON_IDX` default trong code là `1` (12h)**, canonical CẦN
   `0` (4h). Quên override ở bước export dataset (tầng 8) sẽ âm thầm dùng nhầm
   horizon 12h cho dataset gắn mác 4h. **Cùng chỗ, `WFO_SET_PRED` default
   trong code là `ai_pred_market_full_basket_v2` (set CŨ) — canonical CẦN
   `ai_pred_market_gate_wfo` (tầng 7). Quên override cả 2 env này ở bước D
   là rủi ro dễ mắc nhất trong toàn runbook.**
3. **Bug lịch sử: fold-0 leak** — `block_lo=ts_min` từng phủ vào vùng IS đã
   train → leak nhẹ ở OOS block đầu tiên. Đã sửa 2026-08-03 (xem tầng 6).
4. **Bug lịch sử: PURGE_STEPS grid-relative** — default cũ `"288"` đúng nghĩa
   72h CHỈ ở lưới 15 phút; ở lưới 1 phút, 288 bước = 4.8h → rút ngắn purge âm
   thầm, gây leak. Đã sửa 2026-08-04 (xem tầng 6).
5. **Gate coverage 2023+ CHƯA được đo lại** trong phiên tạo canonical 1-phút
   này. ĐỪNG tin số liệu coverage "2023-2025" từ trí nhớ cũ (Task 156 nói về
   2021-2022) — trạng thái PENDING, phải đo trước khi export chính thức
   (tầng 7 và tầng 8).

---
## 1. Ticker (nguồn gốc)

- **Code:** đọc-only, không có exporter riêng — mọi tầng sau đều SELECT trực
  tiếp hoặc gián tiếp từ đây.
- **Input:** none (đây là nguồn gốc).
- **Output:** set Aerospike `kline_1m_opt` @ Aerospike 226 — nến 1 phút thô
  (OHLCV per symbol per phút).
- **Env var:** không có (địa chỉ Aerospike 226 cố định, không tham số hoá ở
  tầng này).
- **Bất biến:** đọc-only tuyệt đối. Không script nào trong pipeline này được
  ghi vào `kline_1m_opt`. Mọi tầng downstream (market, OI, label, Tool1) đều
  xuất phát trực tiếp hoặc gián tiếp từ set này.

---

## 2. Market layer

- **Code:** `DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike()`.
- **Input:** set Aerospike `market_data` (do process khác ghi, upstream của
  layer này không thuộc phạm vi tài liệu này).
- **Output:** dữ liệu per-minute: `rateDownAvg`, `rateUpAvg`, `rateDown15MAvg`.
- **Env var:** không có ghi nhận riêng ở tầng đọc này.
- **Bất biến:** per-minute — đây là lưới thời gian "chuẩn" mà tầng 8 (export
  dataset) forward-fill mọi nguồn khác lên.

---

## 3. OI layer (KHÔNG đổi trong canonical 1-phút — Uni chốt "kệ nó")

- **Code:** `ExportFundingOiPerCoin.java`.
- **Input:** dữ liệu open-interest / long-short ratio / taker-buy per-coin từ
  nguồn Binance (không đi qua `kline_1m_opt`).
- **Output:** `oi_percoin_*.bin.gz` — record 30 byte:
  `ts, symId, oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy`. Cadence
  gốc ~5 phút, per-coin.
- **Env var:** `OI_TOL_MS` — tolerance cho `merge_asof` backward khi ráp vào
  feature. Default **2h**. KHÔNG có giá trị canonical khác — layer này chủ
  động GIỮ NGUYÊN cadence gốc, không ép về lưới 1 phút (Uni chốt "kệ nó": OI
  vẫn merge bằng `merge_asof` backward như cũ, không phải re-export theo phút).
- **Bất biến / leak-free:** `merge_asof` backward đảm bảo chỉ dùng OI đã biết
  tại hoặc trước `ts` — không nhìn tương lai. Tolerance 2h nghĩa là nếu gap
  giữa 2 điểm OI > 2h, dòng đó không được merge (NaN), không bị merge nhầm với
  OI quá cũ.

---
## 4. Funding LABEL layer

- **Code:**
  `src/main/java/com/binance/chuyennd/ai_ml/features/export/ExportFundingLabel.java`.
- **Input:** `kline_1m_opt` (giá), universe alt USDT-perp qua
  `SymbolLifecycleManager`.
- **Output:** `funding_label.csv`. Label kiểu **path** per-coin: `maxFav_H`,
  `maxAdv_H`, `tHitFav_H`, `tHitAdv_H`, `retEnd_H`, `nBars_H` cho
  H ∈ {4h, 12h, 24h, 72h, 7d, 14d, 30d}.
  - Universe = alt USDT-perp, LOẠI BTC/ETH/BTCDOM/USDC. Đi qua
    `SymbolLifecycleManager` — bao gồm CẢ coin đã delist/chết, tức KHÔNG có
    survivorship bias.
  - Sidecar tự sinh **`<output>.meta.json`**: `stepMinutes`, `hStepsMinutes`,
    `generatedAt`, `coinCount`, `emittedRows` — để downstream (tầng 6) tự
    validate bằng cách đọc file, không phải đoán mù.
- **Env var:** `LABEL_STEP_MIN` — default `"15"` (hành vi cũ). **Canonical:
  `"1"`** (model live của Uni chạy theo phút).
  `H_STEPS` = các mốc phút-thật BẤT BIẾN
  `{240, 720, 1440, 4320, 10080, 20160, 43200}` chia cho `LABEL_STEP_MIN` —
  **throw nếu không chia hết**.
- **Bất biến / leak-free:** universe bao gồm coin chết → chống survivorship
  bias. `H_STEPS` luôn được tính lại từ mốc phút-thật, không hardcode theo
  step — trừ 2 chỗ đã sửa dưới đây.
- **Sửa 2026-08-04:** 2 chỗ code cũ hardcode `*15` khi convert
  offset→phút (trong `emit()` và trong `validate` `recompute72()`) đã đổi
  thành `*STEP_MIN`. Trước khi sửa, chạy ở lưới 1 phút sẽ tính sai offset
  15 lần.

---
## 5. Tool1 feature layer

- **Code:**
  `src/main/java/com/binance/chuyennd/ai_ml/features/export/fundingv2/ExportFeaturesForPythonTool.java`.
- **Input:** `kline_1m_opt` + universe alt coin (tương tự tầng 4).
- **Output:** `features_export_python_v3/features_*.bin.gz` — record 170 byte:
  `ts, symId, f[40]` (40 feature per coin per mốc thời gian).
- **HAI chế độ:**
  1. **Mặc định** — production/live inference của 1 coin ĐÃ qua
     `EntrySignalFilter`. **KHÔNG dùng để sinh dữ liệu TRAIN** vì gây
     selection bias (chỉ thấy coin đã lọt filter).
  2. **`FF_UNFILTERED=1`** — dùng cho TRAIN selector: xuất MỌI alt coin,
     KHÔNG qua filter.
- **Env var:** ở chế độ (b), `FF_GRID_MIN` — default `"15"`. **Canonical:
  `"1"`**.
  > ⚠️ **PHẢI khớp `LABEL_STEP_MIN` ở tầng 4.** Nếu không, join (symbol, ts)
  > ở tầng 6 sẽ rớt hầu hết dữ liệu **MÀ KHÔNG BÁO LỖI** — đây là rủi ro âm
  > thầm nguy hiểm nhất trong toàn pipeline (xem Cảnh báo #1 ở đầu file).
- **Bất biến / leak-free:** chế độ (a) và (b) là 2 đường code riêng biệt về
  mục đích sử dụng — không được lấy output chế độ (a) làm dữ liệu train
  selector.

---
## 6. Selector train + predict (walk-forward, leak-free)

- **Code:** `ml/training/gen_funding_wf_predictions.py`, chạy trên **Kaggle**
  (OI merge nặng — lịch sử đã OOM Oracle 23GB, cần Kaggle 30GB).
- **Input:** `TOOL1_GLOB`, `OI_FILE`, `LABEL_CSV`, `MAP_CSV`.
- **Cách train:** XGBoost mỗi (fold, horizon) trên **toàn bộ lịch sử
  expanding từ `ts_min=2021-01-01`** (`ts < cutoff - purge`). **KHÔNG BAO GIỜ
  windowed/cắt ngắn** — Uni chốt rõ: mọi fold train full data để HPO in-sample
  đủ và đúng. Predict OOS block `[cutoff, cutoff + OOS_MONTHS)`.
- **Cutoff schedule:** qua `FIRST_CUTOFF`. **Canonical = `20230101`** —
  "lối A": bỏ hẳn các window sớm không đủ ≥2 năm train sạch, thay vì vá lẻ
  từng window. Xác nhận lại 2026-08-05 (Uni): fold đầu ("20230101") vẫn
  train FULL từ `ts_min=20210101` tới `20230101−72h purge` — đây chính là
  lý do "gen label/feature từ 20210101" (phạm vi export, KHÔNG phải đổi
  điểm cutoff). KHÔNG hạ `FIRST_CUTOFF` xuống sớm hơn 20230101.
- **Env var lưới:** `SELECTOR_GRID_MIN` (canonical = `1`) — `H_STEPS` tính
  giống tầng 4, **PHẢI khớp `LABEL_STEP_MIN`**. Tự-validate bằng cách đọc
  sidecar `.meta.json` của `LABEL_CSV` — **throw `AssertionError` nếu lệch**,
  không im lặng (khác với tầng 5 nơi lệch lưới không báo lỗi gì).
- **`CHUNK_YEARS=1`:** bật đường build RAM-bounded (`build_features_chunked`)
  — merge OI + Tool1 theo từng năm thay vì 1 lần toàn bộ. Cần thiết ở lưới
  1 phút vì Tool1 phình ~15x và OI phải giữ full-native (không còn lọc được
  về grid thô như lúc Tool1 = 15 phút). **Đã verify bằng test tổng hợp
  (2026-08-04): `build_features_full` và `build_features_chunked` cho kết
  quả BYTE-IDENTICAL** — an toàn dùng đường chunked ở production.
- **Output:** `predict_wf_<cutoff>.bin` — record 26 byte:
  `ts, symId, p_4h, p_12h, p_24h, p_72h`. Mỗi file = đúng 1 block OOS
  disjoint (không overlap với file khác).

### 2 bug lịch sử đã sửa tại đây (institutional memory — đừng vô tình revert)

- **2026-08-03 — fold-0 leak:** fold-0 từng dùng `block_lo=ts_min`, phủ luôn
  vùng IS mà model đã train → leak nhẹ ở block OOS đầu tiên. **Sửa:**
  `block_lo=cutoff` luôn, mọi fold = 1 block disjoint.
- **2026-08-04 — PURGE_STEPS grid-relative:** default `PURGE_STEPS="288"` là
  literal SỐ BƯỚC, đúng nghĩa "72h" CHỈ ở lưới 15 phút (288×15p = 72h). Ở lưới
  1 phút, 288 bước = 288 phút = 4.8h → nếu không sửa sẽ ÂM THẦM rút ngắn purge
  từ 72h xuống 4.8h (leak). **Sửa:** default tự tính từ `H_STEPS["72h"]`
  (luôn ra đúng 72h wall-clock bất kể grid).

---
## 7. Gate layer (ĐỘC LẬP hoàn toàn với selector)

- **Code:** `WFOGateRunner.java` + `ml/training/train_gate_fold.py`.
- **Đặc điểm:** KHÔNG bị ảnh hưởng bởi đổi lưới 1 phút ở tầng 4/5/6 — walk-
  forward riêng cho model gate (`predReturn15M`, `predRisk4H` — tín hiệu tổng
  hợp thị trường, KHÔNG phải per-coin).
- **Cách train:** expanding fold, train `< cutoff`, predict OOS (cùng nguyên
  lý walk-forward như tầng 6 nhưng pipeline độc lập).
- **Output:** ghi set Aerospike `ai_pred_market_gate_wfo`.
- **Lưu ý lịch sử:** coverage 2021-2022 từng gần trống (Task 156), gây
  false-FAIL verdict WFO cũ. Với canonical selector giờ bỏ hẳn window <2023
  (lối A, tầng 6), lỗ hổng gate 2021-2022 KHÔNG còn liên quan trực tiếp.
- > ⚠️ **PENDING — CHƯA đo lại coverage thật 2023+ trong phiên này.** Đây là
  > việc còn treo, cần đo trước khi export chính thức (tầng 8). KHÔNG được
  > coi là đã xác nhận — xem Cảnh báo #5 ở đầu file.

---
## 8. WFO dataset export (tầng ráp)

- **Code:**
  `src/main/java/com/binance/chuyennd/ai_ml/wfo/framework/ExportWfoDataset.java`
  + `WfoDataset.java` (`WfoDataset.export(outDir)`).
- **Input — 3 nguồn:** `market_data` (tầng 2) + gate set
  `ai_pred_market_gate_wfo` (tầng 7) + selector `predict_wf_*.bin` (tầng 6,
  qua `WFO_FUNDING_PRED_DIR`).
- **Output:** `market.bin`, `pred.bin`, `funding.bin`, `manifest.txt`.
- **`buildFundingFromWfFiles()`:** chọn 1 horizon qua `WFO_SEL_HORIZON_IDX`
  (`0`=4h, `1`=12h, `2`=24h, `3`=72h).
  > ⚠️ **Default trong code là `1` (12h) — canonical PHẢI override `=0` (4h).
  > Đây là chỗ dễ quên nhất, xem Cảnh báo #2 ở đầu file.**
  Encode `score = 1 - P(win)` (đảo dấu — engine chọn score THẤP = P(win)
  CAO). Throw nếu 2 file `predict_wf` overlap ts-range (leak-guard) hoặc
  span > 100 ngày (self-validate, thêm 2026-08-03).
- **`forwardFillToGrid()`:** carry-forward score selector (ở lưới gốc của
  nó) lên lưới per-minute của `market`, staleness cap qua
  `WFO_FUNDING_FILL_STALE_MS` (default **15 phút** — nên SIẾT LẠI khi
  selector đã tự chạy lưới 1 phút, tránh staleness che gap dữ liệu).
- **Manifest (sửa 2026-08-03):** stamp THẬT từ data, không phải khai báo tay
  — `leakFreeFrom` (OOS sớm nhất đo được từ data), `codeGitSha` (git
  rev-parse HEAD thật, **throw nếu "unknown"**), `horizonIdx`,
  `maxFoldSpanDays`, md5 + ts-range của mỗi file `predict_wf` nguồn,
  `VALIDATED_BY=PENDING` chờ ký (tầng 9).

---
## 9. Validate (độc lập, không tái dùng code exporter)

- **Code:** `scripts/model_quality/validate_canonical_wfo.py`.
- **Cách làm:** đọc THẲNG bytes (không gọi lại `WfoDataset`/`ExportWfoDataset`
  — tránh bug chung giữa exporter và validator).
- **Kiểm tra:**
  - span mỗi fold ≤ 100 ngày;
  - không fold nào overlap ts;
  - OOS sớm nhất ≥ ngày kỳ vọng (`EXPECT_LEAKFREE`);
  - `market`/`pred`/`funding` đều thẳng lưới phút (`ts % 60000 == 0`);
  - gate không có `ts < leakFreeFrom`;
  - tỷ lệ NaN theo horizon;
  - cross-check md5 trong manifest với file thật.
- **Fail-closed:** ghi `validation_report.txt`, `exit 1` nếu FAIL. Chỉ ký
  `VALIDATED_BY` khi `SIGN=1` **VÀ** tất cả PASS.

---

## 10. Consume

- **Code:** `WfoDataset.load()` — mọi worker WFO. Verify md5 theo manifest
  TRƯỚC KHI load `market.bin`/`pred.bin`/`funding.bin` vào RAM.
- **Dùng ở:** `StrategyWfoTask` / `WfoCoordinator` / `WfoWorker` cho backtest/
  HPO thật (`HPOFitnessCalculatorV4`).
- > ⚠️ **CHƯA thêm check reject `leakFreeFrom=unknown`** — cố ý trì hoãn tới
  > khi dataset canonical PASS. Nếu bật ngay sẽ làm vỡ WFO đang chạy trên
  > dataset cũ `ret2wf_4h` (chưa có `leakFreeFrom` thật). Việc này nằm trong
  > backlog "Step F" — chỉ bật SAU khi tầng 9 ký PASS cho dataset canonical.

---
## Bảng env var tổng hợp (chỗ vận hành hay sai nhất)

| Env var | Default | Canonical (1-phút) | Ý nghĩa ngắn | Rủi ro nếu quên |
|---|---|---|---|---|
| `LABEL_STEP_MIN` | `15` | `1` | Bước lưới của funding label (tầng 4) | `H_STEPS` throw nếu không chia hết; lệch với `FF_GRID_MIN` → mất data âm thầm |
| `FF_UNFILTERED` | (unset/0) | `1` (khi export TRAIN) | Xuất mọi coin (không qua `EntrySignalFilter`) | Quên → dữ liệu train bị selection bias |
| `FF_GRID_MIN` | `15` | `1` | Bước lưới Tool1 feature (tầng 5) | **Lệch `LABEL_STEP_MIN` → mất ~93% data, KHÔNG báo lỗi** |
| `TOOL1_GLOB` | (bắt buộc set) | path Tool1 1m | Glob file Tool1 feature đầu vào selector | Sai path → không tìm thấy file, script fail rõ |
| `OI_FILE` | (bắt buộc set) | path OI export | File OI đầu vào selector | Sai path → fail rõ |
| `LABEL_CSV` | (bắt buộc set) | `funding_label_1m.csv` | File label đầu vào selector | Sai path/step → assert lệch grid |
| `MAP_CSV` | (bắt buộc set) | map symId↔symbol | Bảng map coin | Thiếu → không giải mã được symId |
| `OUT_DIR` | (bắt buộc set) | `wf_pred_LF_1m_<ngày>` | Nơi ghi `predict_wf_*.bin` | Trỏ nhầm dir cũ → lẫn dataset |
| `FIRST_CUTOFF` | (bắt buộc set) | `20230101` (lối A, xác nhận lại 2026-08-05) | Cutoff đầu tiên của walk-forward selector | Đặt sớm hơn → window <2 năm train sạch, không đủ data |
| `CUTOFFS` | (tự sinh từ `FIRST_CUTOFF`+`OOS_MONTHS` nếu không set) | (tự sinh) | Danh sách cutoff walk-forward | Set tay sai thứ tự → fold không disjoint |
| `OOS_MONTHS` | (tuỳ script, thường `3`) | `3` (dùng ở SMOKE) | Độ dài mỗi block OOS | Quá dài → vi phạm self-validate span >100 ngày ở tầng 8 |
| `TZ_OFFSET_MS` | `7*3600*1000` (GMT+7) | `7*3600*1000` (không đổi — khớp WFO) | Offset timezone khi tính cutoff/ts | Đổi sai → lệch mốc ngày mọi fold |
| `PURGE_STEPS` | **cũ:** `288` (literal, đúng nghĩa 72h chỉ ở lưới 15p) — **mới (2026-08-04):** tự tính từ `H_STEPS["72h"]` | tự tính (luôn ra 72h wall-clock) | Số bước purge giữa train và OOS, chống leak biên | Dùng bản cũ ở lưới 1 phút → purge chỉ còn 4.8h, leak (xem tầng 6) |
| `SELECTOR_GRID_MIN` | `15` | `1` | Bước lưới selector, PHẢI khớp `LABEL_STEP_MIN` | Lệch → `AssertionError` khi đọc sidecar `.meta.json` (fail rõ, không âm thầm) |
| `CHUNK_YEARS` | (unset = full build) | `1` | Bật `build_features_chunked` (RAM-bounded, theo năm) | Không set ở lưới 1 phút → Tool1 phình ~15x có thể OOM |
| `SMOKE_FOLDS` | (unset = full run) | `1` (chỉ khi test trước khi chạy full) | Giới hạn số fold để test nhanh | Quên bỏ sau smoke → dataset thiếu fold, tưởng đã full |
| `NEST` | (tham số XGBoost, mặc định theo script) | (không đổi theo lưới) | Số n_estimators XGBoost | Không liên quan trực tiếp leak-free, chỉ ảnh hưởng chất lượng model |
| `SEED` | (mặc định theo script) | (không đổi theo lưới) | Seed random cho XGBoost | Không set → kết quả không tái lập giữa các lần chạy |
| `OI_TOL_MS` | `2h` (7200000) | `2h` (không đổi — tầng OI giữ nguyên cadence gốc) | Tolerance `merge_asof` backward khi ráp OI | Tăng quá lớn → merge OI cũ vào ts không liên quan |
| `WFO_FUNDING_PRED_DIR` | (bắt buộc set) | dir chứa `predict_wf_*.bin` canonical | Nơi `ExportWfoDataset` đọc selector | Trỏ nhầm dir → dataset dùng prediction sai đợt |
| `WFO_SEL_HORIZON_IDX` | **`1` (12h)** | **`0` (4h)** | Chọn horizon nào trong `predict_wf` để làm `funding.bin` | **Quên override → dataset gắn mác 4h nhưng chứa dữ liệu 12h** (Cảnh báo #2) |
| `WFO_SET_PRED` | **`ai_pred_market_full_basket_v2`** (set CŨ, khác gate WFO) | **`ai_pred_market_gate_wfo`** | Set Aerospike đọc gate prediction | **Quên override → dataset âm thầm đọc set CŨ (`full_basket_v2`, không phải gate walk-forward tầng 7) — cùng loại rủi ro như `WFO_SEL_HORIZON_IDX`** |
| `WFO_CODE_SHA` | (unset → throw "unknown") | `$(git rev-parse HEAD)` thật | Stamp git SHA thật vào manifest | Không set → export THROW (fail-closed, không âm thầm) |
| `WFO_LEAKFREE_FROM` | (đã bỏ dùng) | (đã bỏ dùng) | **KHÔNG còn tác dụng** — `leakFreeFrom` giờ tính từ data thật, không nhận qua env này. Giữ lại CHỈ để log warn nếu giá trị set lệch với số đo thật | Set env này để "ép" leakFreeFrom sẽ KHÔNG có hiệu lực gì, chỉ ra warning |
| `WFO_FUNDING_FILL_STALE_MS` | `15 phút` (900000) | nên siết lại (chưa chốt số cụ thể) | Staleness cap khi forward-fill score selector lên lưới per-minute | Để mặc định 15 phút ở lưới 1 phút → có thể che gap dữ liệu thật |
| `WFO_VALIDATED_BY` | `PENDING` | ký tên thật sau khi PASS (tầng 9) | Ai đã ký duyệt dataset | Còn `PENDING` = chưa ai xác nhận dataset an toàn để dùng |
| `LF_DIR` | (bắt buộc set khi validate) | dir `predict_wf` canonical | Input cho `validate_canonical_wfo.py` | Sai dir → validate sai nguồn |
| `DS_DIR` | (bắt buộc set khi validate) | dir dataset export (tầng 8) | Input cho validator | Sai dir → validate dataset khác |
| `EXPECT_LEAKFREE` | (bắt buộc set khi validate) | `2023-01-01` (xác nhận lại 2026-08-05) | Ngày kỳ vọng OOS sớm nhất | Set sai ngày → validator PASS nhầm hoặc FAIL nhầm |
| `HORIZON_IDX` | (bắt buộc set khi validate) | `0` | Horizon để validator kiểm tra khớp với `WFO_SEL_HORIZON_IDX` đã export | Không khớp giá trị đã dùng ở tầng 8 → validate sai đối tượng |
| `SIGN` | `0` | `1` (chỉ khi chắc chắn PASS) | Bật ký `VALIDATED_BY` khi tất cả check PASS | Set `1` khi chưa chắc → ký duyệt nhầm dataset lỗi |

---
## Runbook — ưu tiên CE pipeline (R1, `docs/rules/ce-buttons.md`)

**[2026-08-04] Cách chạy CHUẨN, không SSH tay:**
```
ce pipe_run wfo_canonical_1m
# theo doi (18 step, tu dong het tru 1 gate ky cuoi):
ce pipe_status <pipe_id>
# pipeline TU DONG push+cho READY ca 2 dataset Kaggle (tool1/label 1-phut) —
# khong con buoc tay nao giua duong.
# CHI dung o gate_sign (llm_gate CHU Y giu lai — diem ky duyet cuoi cung, khong
# phai gap): xem ${out_ds}/validation_report.txt truoc, PASS moi pipe_resume;
# FAIL/chua chac thi pipe_stop (KHONG pipe_resume — llm_gate khong re nhanh
# theo noi dung answer, resume la di thang toi buoc ky).
```
Override tham số qua `K=V` (vd đổi `out_ds`, `expect_leakfree`) — xem đầy đủ trong
`orchestrator/pipelines/wfo_canonical_1m.json` (`params`). 5 atom mới
(`label_export`/`tool1_export`/`wfo_validate`/`kaggle_dataset_push`/`kaggle_dataset_status`)
viết 2026-08-04, đã `py_compile` + smoke-test dispatch cục bộ (kể cả nhánh
create/version thật của `kaggle_dataset_push` — xác nhận `dataset-metadata.json`
sinh đúng), **CHƯA chạy thật trên Oracle+Kaggle** (SSH session lúc viết bị
chặn) — bắt buộc `ce --sync bg_selftest` PASS trước khi tin tưởng, theo rule 4
`ce-buttons.md`.

Runbook SSH tay dưới đây là **lệnh THAM CHIẾU** (những gì pipeline trên thực thi bên
trong) — chỉ dùng khi debug 1 bước riêng lẻ hoặc pipeline hỏng cần chạy tay tạm.

## Runbook lệnh canonical (COPY Y NGUYÊN — KHÔNG tự đổi tên biến/giá trị)

```
# A) Oracle — label 1 phút
LABEL_STEP_MIN=1 java ...ExportFundingLabel <start> <end> /home/ubuntu/claudedata/funding_label_1m.csv

# B) Oracle/226 — Tool1 unfiltered 1 phút
FF_UNFILTERED=1 FF_GRID_MIN=1 java ...ExportFeaturesForPythonTool <start> <end> features_export_python_v3_1m/

# C) Kaggle — selector predict_wf 1 phút (SMOKE truoc)
FIRST_CUTOFF=20230101 OOS_MONTHS=3 SELECTOR_GRID_MIN=1 CHUNK_YEARS=1 SMOKE_FOLDS=1 \
  TOOL1_GLOB=... OI_FILE=... LABEL_CSV=funding_label_1m.csv MAP_CSV=... OUT_DIR=wf_pred_LF_1m_20260804 \
  python3 ml/training/gen_funding_wf_predictions.py
# (bo SMOKE_FOLDS sau khi kiem log OK)

# D) Node co Aerospike 226 — export dataset
WFO_CODE_SHA=$(git rev-parse HEAD) WFO_FUNDING_PRED_DIR=/home/ubuntu/claudedata/wf_pred_LF_1m_20260804 \
  WFO_SEL_HORIZON_IDX=0 WFO_SET_PRED=ai_pred_market_gate_wfo \
  java ...ExportWfoDataset /home/ubuntu/claudedata/wfo_ds_LF_1m_20260804_h4h_v1

# E) Validate + ky PASS
LF_DIR=/home/ubuntu/claudedata/wf_pred_LF_1m_20260804 DS_DIR=/home/ubuntu/claudedata/wfo_ds_LF_1m_20260804_h4h_v1 \
  EXPECT_LEAKFREE=2023-01-01 HORIZON_IDX=0 SIGN=1 python3 scripts/model_quality/validate_canonical_wfo.py
```

> Thứ tự bắt buộc: A → B → C (smoke rồi full) → D → E. KHÔNG chạy D trước khi
> C xong full (không smoke). KHÔNG ký `SIGN=1` ở E nếu chưa đo lại gate
> coverage 2023+ (tầng 7, Cảnh báo #5) — dù validator không tự kiểm điều này,
> đây là điều kiện vận hành operator phải tự nhớ.
