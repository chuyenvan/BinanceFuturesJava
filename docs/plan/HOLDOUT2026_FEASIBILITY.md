# HOLDOUT2026_FEASIBILITY — kiểm khả thi chấm holdout 2026 cho 3 cấu hình (HO0)

- Ngày 2026-10-08. Vai: agent HO0, CHỈ KIỂM KHO DỮ LIỆU / MODEL / PIPELINE. 0 sim, 0 Kaggle kernel, 0 train, 0 sửa .java, 0 ghi Aerospike, 0 chạm 242 (chỉ đọc docs đã có).
- **Tài liệu này KHÔNG chứa bất kỳ số hiệu năng / tín hiệu / thống kê p15-PnL nào trên 2026.** Mọi con số 2026 dưới đây là khoảng ngày, số file, số dòng, dung lượng, md5/sha, ngày train.
- Repo `module` HEAD lúc đọc `f24acb13`. Kế thừa (và cập nhật): `docs/plan/E3_HOLDOUT_2026_PREP.md` + `docs/prereg/PREREG_HOLDOUT_2026_DRAFT.md` (24c1aeec, 09-29), `docs/plan/H1_HOLDOUT_PREP.md`.
- 3 cấu hình cần chấm: **C1** B0 K16 (G2+FLAT3, jar `7368be46`), **C2** K24 + `GATE_QUOTA_SKIP_WHEN_FULL` (jar `0944841c`, dataset `sim-jar-gqsf`), **C3** K24 + skipFull + NSEL M2 (jar `b7c89f09`, module `386c7cdc`, dataset `sim-jar-nsel`).

## 0. KẾT LUẬN (rủi ro trước)

| Câu hỏi | Trả lời |
|---|---|
| Chạy được không? | **CÓ ĐIỀU KIỆN.** Cửa sổ khả thi ngay về dữ liệu: **2026-01-01 → 2026-06-30 (GMT+7), 6 tháng.** Kéo dài hơn cần dựng thêm 4 kho (§2.3) và vẫn kẹt ở ~2026-08-05 (funding_data Oracle). |
| Model ≤ 2025 có sẵn? | **S1 và net015: CÓ** (`s1a2x1_cut20251231`, `model_f19_4h` cut20251231, train tới 2025-12-27). **Gate p15: CÓ 1 seed** (seed 42: `wfo_models/fold_19` và bản Python cut20260101 sha256 `d37969ee…`); **7 seed còn lại PHẢI train** (rẻ: 1 fold/seed, Oracle, ~1–2 phút/seed). |
| Có artifact train ≥ 2026-01-01? | **CÓ, CẤM DÙNG:** gate `fold_20` (cut 2026-04-01, đang live 242/shadow), `model_cut20260701`, file `wfo_gate_pred_2026_H1.csv` (quý 2 sinh từ `fold_20`). |
| Blocker E3 (09-29) còn không? | **Đã gỡ phần lớn:** generator `CLOSES_1H` có (F0, `closes1h_build.py`); net015 tái lập tới 1 ULP + model cut20251231 có. Còn thiếu: **bins selector 2026, pred.bin 2026 × 8 seed, dataset WFO có 2026, ticker 2026 trên Kaggle đã kiểm md5.** |
| Rò rỉ lớn nhất | (1) 2026H1 đã từng là VAL trước seal 09-01 (thiết kế gate/HPO/fold chốt khi 2026 đang được nhìn) ⇒ holdout **có nhiễm ở tầng thiết kế**, không gỡ được; (2) kho có sẵn NHÃN 2026 (store gate `label_*`, `ds_label15m/funding_label_2026*`) ⇒ mọi loader phải cắt theo SEAL; (3) dùng nhầm `fold_20`/`wfo_gate_pred_2026_H1.csv`/`predict_wf_20251231.bin`. |
| Công | ~1–1,5 ngày công agent + 10–20 h wall Kaggle (48 kernel holdout + 3–6 kernel parity). Chi tiết §5. |

## 1. Pipeline dữ liệu sim hiện tại (DEV ≤ 2025-12-31) — nguồn từng thành phần

Kernel = `tools/kaggle_sim.py` HEAD (guard NOWRITE242 + preflight mapper) + 1 khối chèn của driver (vd `gate_skipfull_driver.py`: thay `pred.bin` theo seed, kiểm `want_pred_md5`). Class `SimulatorMarketLevelTicker1MStopLoss`, `TICKER_SOURCE=file`, `TIME_RUN=20210701` (trong `config.properties` của bundle), `SIM_END_DATE=20251231`.

| Thành phần | Kaggle dataset | Nguồn Oracle / cách sinh | Phạm vi DEV | Ghi chú |
|---|---|---|---|---|
| `sim.jar` | `sim-jar-gdv2` (C1 `7368be46`), `sim-jar-gqsf` (C2 `0944841c`), `sim-jar-nsel` (C3 `b7c89f09`) | build từ branch tương ứng | — | cả 3 jar có `HoldoutSeal` (`clampEnd` trong sim, `trimMap` trong `WfoDataset.export`) |
| Bundle `sim-x1-2021-bundle` (25 file, ~5,3 GB) | `chuyendinh/sim-x1-2021-bundle` | stage `~/simbundle_x1_t170` (hardlink) | 2021-07-01..2025-12-31 | `config.properties` (`configs/sim_dev_file_2021.properties`, AEROSPIKE_HOST_226=Oracle), `exchange_info_pin.json`, `prof_*`, dataset WFO, bins |
| Dataset WFO `market.bin` | trong bundle | `WfoDataset.export` từ Aerospike set `market_data` (`MarketDataObject`: rateDownAvg/rateUpAvg/rateDown15MAvg), md5 `4ab691c9…` | marketRange 2021-01-01..2025-12-31, 2 554 812 phút | set "live", ~2,8% phút thiếu (giữ nguyên làm "data availability") |
| `pred.bin` (p15) | trong bundle (seed 42) / `gate-abl-seed7`, `gate-sb-s{13,21,99,123,777,2024}` | seed 42 = Java `WFOGateRunner` → `wfo_gate_pred.csv` → set `ai_pred_market_gate_wfo` → export; 7 seed khác = Python `gate_ablation_driver.retrain` (cùng recipe, chỉ đổi `random_state`) chỉ thay cột p15 | 2021-04-01..2025-12-31 23:59, 2 500 260 dòng, md5 `5dd6bb4c…` | format BE `[ts i64][p15 f32][predRisk4H f32]`; cột risk cũ không leak-free nhưng nhánh RISK đã bỏ khỏi gate |
| `funding.bin` (4,45 GB) | trong bundle | `WfoDataset.buildFundingFromWfFiles(WFO_FUNDING_PRED_DIR)`: bins selector 15′ forward-fill → mỗi phút | 2 301 065 phút, md5 `8e57d900…` | đây là nơi S1+net015 vào sim; thư mục `predict_wf_*` trong bundle chỉ để thoả guard |
| Bins selector `predwf_map_s1a2_x1_2021` (18 fold, 26 B/bản ghi `[ts][symId i16][p4h,p12h,p24h,p72h]`) | (qua funding.bin) | `x1_build_map.py`: giữ multiset P(win) **net015/G015x26** từng tick 15′, gán lại theo thứ hạng **S1** (`pred_s1a2x1`) | fold 20210701..20251001, binsSha256 `407e2aba…`, leakFreeFrom 2021-07-01 | S1: XGBRanker 9 feat, train < cut − 72h; net015: XGB 45 feat Tool1, train < cut − ~3,3 ngày |
| Ticker 1′ | `wfo-ticker-2021…2025h2` (7 dataset, 1 826 file, đủ ngày) | export từ Aerospike `test.kline_1m_opt` (tickexport 08-21/22) | 2021-01-01..2025-12-31 | guard `TICKER_MIN_DAYS=1826` |
| Symbol mapper | — | Aerospike Oracle (AEROSPIKE_HOST_226) đọc lúc chạy | 863 symbol | guard ≥ 800 |
| `CLOSES_1H_v2` + mask, `symbol_lineage_v2.csv` (627 sym) | — | `java/fsrun/` (DATA_AUDIT_20261003) | tới 2026-01-01 00:00 (OHLCV_1H_v2 manifest) | chỉ cho benchmark / scorer, không vào sim |

**p15 = 1 số market-level / phút** (không phải theo coin), model gate XGBRegressor 33 feature V3FULL, nhãn `label_oldbasket`, WFO expanding quý (19 fold 20210401..20251001, purge 15′). **pred.bin KHÔNG chứa bins S1/G015**; bins đi qua `funding.bin`.

## 2. Dữ liệu 2026 có sẵn (CHỈ LIỆT KÊ — không đọc giá trị)

### 2.1 Bảng kho

| Kho | Vị trí | Phạm vi 2026 | Quy mô | Ghi chú / lỗ |
|---|---|---|---|---|
| Ticker 1′ (file sim) | Oracle `java/simulator/kaggle_data_hpo/ticker_2026*.bin.gz` | 2026-01-01..2026-08-12 | 224 file (đủ ngày lịch, 15 GB cả thư mục) | lỗ trong ngày chưa đo |
| Ticker 2026 (Kaggle) | `wfo-ticker-2026` (3,32 GB, 08-21), `wfo-ticker-2026pf` (2,48 GB, 08-23, cắt tới ~08-13) | như trên | — | **md5 Kaggle ↔ Oracle CHƯA khớp** (D1_DATA_AUDIT: "cần md5sum"); `tickexport/up2026/ticker_2026.tar` 3,35 GB khác bản pf |
| Aerospike Oracle `test.kline_1m_opt` | Oracle local | tới ~08-2026 (copy từ 242, `CopyTicker242To226`) | 2 952 455 obj | 09-04: Oracle thiếu ~32k phút so 242; mép cuối hiện tại **chưa đo** (không quét) |
| `market_data_object` (nguồn market.bin) | Aerospike (mọi cụm) | tới **2026-08-14** rồi chết | — | sau đó chỉ còn `MarketDataInlineGenerator` (lệch định nghĩa availability so DEV) |
| `funding_data` | Aerospike Oracle | tới **2026-08-05 12:00** | 831 obj | Oracle thiếu 23 symbol mới 2026 so 242 |
| Store gate 33 feature + nhãn | `claudedata/gate_dataset_full.csv.gz` (356 MB, 08-08; Kaggle `gate-dataset-full`) | 2026-01-01..2026-06-30 (≈260 600 dòng sau SEAL; tổng 2 889 623) | — | **CHỨA NHÃN 2026**; 2026-06 thiếu 457 phút; cùng 1 lượt export với phần DEV ⇒ cùng code feature |
| Replay gate 2026-07..09 | `claudedata/devexport_202609/devexport_20260701_20260928_FULL.csv.gz` (14,6 MB) | 2026-07-01..09-28 | 129 137 phút | export riêng 09-28, KHÁC lượt với store DEV ⇒ phải kiểm parity trước khi dùng |
| Tool1 15′ (feature net015) | Oracle `ds_feat15m/features_2026{0101_to_0401,0401_to_0701}.t1c.gz` (172 MB, 189 MB) | 2026-01-01..2026-07-01 | 2 file | Kaggle `funding-tool1-15m` (08-16) — phủ 2026 chưa kiểm |
| Nhãn 15′ net015/S1 | Oracle `ds_label15m/funding_label_2026{0101_to_0401,0401_to_0701}.pb` | tới 2026-07-01 | 2 file | **NHÃN 2026** — chỉ dùng cho định nghĩa pool (xem §6 R4), cấm train |
| OI per-coin | `claudedata/oi/oi_percoin_full.bin` (4,23 GB, sha `e3887f63`, file sạch đang ghim); `java/simulator/features_oi_percoin_v1/oi_percoin_20210101_to_20260701.bin.gz` (3,21 GB) | tới ~2026-07-01 (tên file); mép thật của bản ghim **chưa đo** | — | bài học `create_time` (OI_FIX_LOG 09-03): KHÔNG rebuild bằng code repo (leak 5′) |
| OI/funding/LSR realtime | `~/derivs_store/<ngày>/` (cron `collect_derivs.py` */5) | 2026-09-12..nay (≈27 ngày) | 528 sym, ~6–8 MB/ngày | ngoài cửa sổ khả thi; liquidation 0 dòng |
| p15 2026 sinh sẵn | `claudedata/wfo_gate_pred_2026_H1.csv` (260 183 dòng, sha256 `4cc62c14…`) | 2026-01-01..07-01 | — | **CẤM DÙNG:** Q2 lấy từ `fold_20` (train có 2026Q1), chỉ seed 42, purge 0 |
| 242 storage | 242 `storage/data/{prediction,predictionSymbol}` | 2026-08-20.. (đủ 1′ từ 09-28) | — | live, ngoài cửa sổ; lỗ **10-07 00:45→10:11** (DEPLOY_SHADOW2_K24 a9618cb4) — không ảnh hưởng holdout H1 |

### 2.2 Mép khả thi
Cửa sổ chặn bởi **store gate + Tool1 + nhãn pool + OI = 2026-07-01 00:00 GMT+7** ⇒ `SIM_END_DATE=20260630` (sim chạy tới hết ngày). Ticker và market_data_object dư tới 08-12/08-14.

### 2.3 Muốn kéo tới ~2026-08-05 (KHÔNG khuyến nghị cho lần chấm này)
Phải dựng thêm: (a) store gate 07-01→08-05 bằng `ExportGateDataset` (Java replay, cùng code DEV) — **không** ghép bản devexport 09-28 khi chưa có parity với store DEV trên một đoạn 2025; (b) Tool1 15′ + nhãn pool 07→08; (c) OI tới 08-05 với luật `create_time` theo từng (symbol, ngày); (d) ticker Kaggle tới 08-05. Trần cứng 08-05 12:00 do `funding_data` Oracle. Thêm ~1–2 ngày công, đổi bộ dữ liệu ⇒ phải chốt trong pre-reg trước.

## 3. Model — DEV, live, và "≤ 2025" cho holdout

| Model | Dùng cho DEV pred/bins | Live hiện tại (242 / shadow) | Bản train ≤ 2025-12-31 có sẵn | Bản train có 2026 (CẤM) |
|---|---|---|---|---|
| Gate p15 (XGBReg, 33 feat, `label_oldbasket`) | WFO 19 fold cut 20210401..20251001, train < cut − 15′; seed 42 Java, 7 seed Python (`gate-abl-seed7`, `gate-sb-*`) | `fold_20` ONNX md5 `8ec99757…` (cut 2026-04-01, train 2021-01-01→2026-03-31, purge 0) | seed 42: `claudedata/wfo_models/fold_19` (cut 2026-01-01, ghi 08-06, **purge 0**) + bản Python cut20260101 sha256 `d37969ee…` (DEPLOY242 readiness Q1, parity ORT 3,4e-8). **7 seed khác: CHƯA CÓ** | `fold_20`, `model_cut20260701` (train tới 2026-06-30), `wfo_gate_pred_2026_H1.csv` phần Q2 |
| S1 selector (XGBRanker 9 feat) | `pred_s1a2x1` 16+2 fold, train < cut − 72h, seed 42, CPU deterministic | `s1a2x1_cut20251231.onnx` (sha `8b1dcf00…`) trên 242 | **CÓ:** `~/s1_model/s1a2x1_cut20251231.{json,onnx}` (json sha `af706dc6…`), train 6 911 775 dòng tới **2025-12-27 16:30**, ledger ts_max 2025-12-31 (RESULT_S1REFRESH 37fd5024) | không thấy |
| net015 (G015x26, XGB 45 feat Tool1, nhãn 4h) | `predwf_G015x26` gốc (trainer 08-14 đã mất; thư mục gốc **không còn** trong `claudedata`, bản tái lập 1 ULP ở `f0_repro/g015x26_regen` 16 fold) | `g015x26_f15_cut20251231.onnx` (sha `41a07109…`, md5 `e65e683b`) | **CÓ:** `~/kg015x26_cut20251231/.../out/model_f19_4h.json` (cut20251231, train tới **2025-12-27 16:45**, GPU, seed 42, MANIFEST sha256 có) — RESULT_NET015_CUT20251231 37fd5024 | không thấy |

**Ghi chú bắt buộc:**
1. `kg015x26_cut20251231/out/predict_wf_20251231.bin` là sản phẩm phụ OOS 2026Q1 của model ≤ 2025 nhưng **mép lệch lịch DEV**: bắt đầu 2025-12-31 00:00 +07 (chồng 1 ngày với fold 20251001) và dừng 2026-03-30 23:45 +07 (thiếu 2026-03-31). ⇒ **không dùng nguyên file**; predict lại với mép [20260101, 20260401) và [20260401, 20260701) GMT+7 từ `model_f19_4h.json`.
2. Holdout "model ≤ 2025" ⇒ **1 model đông lạnh cho cả 2 quý** (Q2 cũ hơn 1 quý so với cách DEV refresh theo quý). Thiên lệch này đối xứng cho 3 cấu hình (so ghép cặp vẫn hợp lệ) nhưng làm lệch mức tuyệt đối so DEV. Phương án WFO quý (cut 20260401 dùng nhãn 2026Q1) **không** khuyến nghị: đụng nhãn holdout trong lúc build.
3. Gate seed 42: chọn **Python retrain cut20260101 purge 15′** cho cả 8 seed (cùng recipe `GA.retrain`, `RETRAIN[...]` seed 42/7/13/21/99/123/777/2024) thay vì `fold_19` (purge 0, Java, ghi 08-06) để 8 seed đồng nhất recipe. Cổng: seed 42 Python cut20260101 ↔ `d37969ee…` (và ↔ `fold_19`) pearson/spearman trên **2025Q4 (DEV, in-sample)** ≥ 0,99; không so trên 2026.
4. Hằng số `AI_DYNAMIC_MIN/MULT` (HPO GA ~2026-05) không truy được range dữ liệu — có thể đã thấy 2026H1 (GATE_INVENTORY §5) ⇒ nhiễm thiết kế, ghi vào pre-reg, không sửa được.

## 4. Feature 2026 — tái tạo giống DEV?

| Chuỗi | Tái tạo 2026 giống DEV? | Điều kiện |
|---|---|---|
| 33 feature gate (store) | **CÓ cho 2026H1**: rows 2026 nằm trong CÙNG file/lượt export 08-08 với DEV ⇒ cùng code `ExportGateDataset`/extractor (sau fix 7f70e30e, basket 6117d0be). | Loader đọc 2026 chỉ `timestamp` + 33 cột feature, **không** đọc cột nhãn. Sau 07-01 phải export lại (Java replay) + parity đoạn 2025 trước. |
| EXPORT-FIX 10-01 / FEATDIFF PASS-2 | **Không liên quan offline.** EXPORT-FIX sửa writer `LiveFeatureDump` (feat_dump 242); PASS-2 so live↔DEV. Holdout dùng store offline ⇒ không chịu lệch live 27/33 feature. | Không ghép feat_dump live vào holdout. |
| Tool1 15′ (net015) | Có file 2026 tới 07-01 cùng định dạng `.t1c.gz` | kiểm sinh cùng exporter/lượt với DEV (mtime, header) trước khi predict |
| feat_v2 (S1: CLOSES_1H + OI + funding Aerospike) | **Có đường:** `closes1h_build.py` (Vision 1h) cho đoạn 2026; đoạn DEV giữ `CLOSES_1H.bin` ghim (Vision đã đổi, không byte). OI dùng bản ghim `e3887f63` (đã đo nhân quả [t−5m, t) trên mẫu tới 2026-05). funding_data tới 08-05. | `x1_feat_v2_build.py` peak ~23 GB ⇒ **Kaggle** (vượt luật Oracle 8 GB). Kiểm: đoạn 2025 của feat_v2 mới == `feat_v2_x1.parquet` (equal_nan). Mép OI thật của file ghim phải đo trước (nếu < 2026-06-30 ⇒ cần bản 20260701 + kiểm `v3.py`/`v6.py` OI_FIX_LOG §5). |
| Ledger pool S1 | pool(tick) = coin có NHÃN tại tick 15′ khi p15 ≥ 0,008 (`x1_ledger.py`) | cần p15 2026 (seed 42 model ≤ 2025) + file nhãn 2026 (CHỈ tồn tại, không giá trị). Đây là look-ahead "availability" có sẵn trong DEV — giữ y hệt DEV để so được, khai trong pre-reg. |
| Liquidation | không có kho nào (0 dòng) | không dùng ở 3 cấu hình ⇒ không chặn |

## 5. Việc phải dựng + ước lượng (cửa sổ 2026-01-01→06-30)

Thứ tự bắt buộc: B1 pre-reg commit TRƯỚC mọi bước sinh input 2026; B2–B7 KHÔNG mở seal (không sim qua 2025-12-31); B8 chỉ sau khi owner duyệt mở seal.

| Bước | Việc | Nơi chạy / tài nguyên | Thời gian (ước) | Cổng (FAIL ⇒ dừng) |
|---|---|---|---|---|
| B1 | Pre-reg holdout (3 cấu hình, cửa sổ, luật, scorer, danh sách artifact cho phép/cấm theo sha) | MASTER | 2–3 h | commit hash trước B2 |
| B2 | Gate p15: retrain cut **20260101** × 8 seed (`GA.retrain` recipe, purge 15′; `load_store` cắt SEAL 2026-01-01 +07 ⇒ train thực ≤ 2025-12-31 16:59 UTC) → predict 2026H1 từ store (chỉ cột feature) → 8 `pred.bin` = phần DEV y hệt từng seed (A1/gabl-seed7/gsb-*) + đoạn 2026 | Oracle Python, RAM ~3–4 GB, 1 job | ~1 h | G-B2a seed 42 ↔ `d37969ee`/`fold_19` trên 2025Q4 ≥ 0,99; G-B2b phần ≤ 2025 của 8 pred.bin == md5 DEV từng seed; meta ghi `train_ts_max` < SEAL |
| B3 | net015 2026: predict-only `model_f19_4h.json` trên Tool1 2026 theo mép [0101,0401),[0401,0701) +07 | Kaggle (peak ~11 GB > luật Oracle) — kernel KHÔNG phải sim | ~1 h (gồm upload Tool1 2026 nếu dataset Kaggle chưa phủ) | G-B3 tái hiện `predict_wf_20251001` từ `model_f18` (spearman 1,0 / ≤1,2e-7) trên cùng kernel |
| B4 | S1 2026: `CLOSES_1H` 2026 (`closes1h_build.py`, Vision) → feat_v2 tới 2026-07-01 → ledger (`X1_T1=2026-07-01`, pool dùng p15 seed 42 B2) → predict-only `s1a2x1_cut20251231.json` → `x1_build_map` → `predict_wf_20260101.bin`, `predict_wf_20260401.bin`; thư mục bins mới = 18 file DEV (hardlink) + 2 file | feat_v2 trên Kaggle (~23 GB); còn lại Oracle | 3–4 h | G-B4a feat_v2 đoạn ≤ 2025 == `feat_v2_x1` (equal_nan); G-B4b S1 predict 2025Q4 bằng model cut20251231 == ghi chép RESULT_S1REFRESH; G-B4c multiset P(win) từng tick == net015 (kiểm có sẵn trong build_map) |
| B5 | Dataset WFO có 2026: **đề xuất Python append** (market.bin từ `market_data_object` 2026H1; funding.bin = forward-fill bins 15′ theo đúng `buildFundingFromWfFiles`; pred.bin từ B2) — phần ≤ 2025 COPY nguyên. Phương án Java `ExportWfoDataset` + `HOLDOUT_UNSEAL` cần `-Xmx14g` (> 8 GB) ⇒ Kaggle hoặc ngoại lệ owner + lock | Oracle Python streaming ≤ 4 GB | 2–3 h | G-B5 bộ ghi Python tái sinh funding.bin/market.bin DEV từ chính nguồn DEV **byte-identical** md5 `8e57d900`/`4ab691c9` trước khi ghi đoạn 2026 |
| B6 | Kaggle: bundle mới `sim-ho26-bundle` (~6 GB, manifest mới, `leakFreeFrom` giữ 2021-07-01), dataset ticker `wfo-ticker-2026h1` (181 file từ Oracle, md5 manifest) hoặc kiểm md5 `wfo-ticker-2026pf`; 8 dataset pred | Oracle → Kaggle; đĩa Oracle trống 21 GB, cần ~6–7 GB tạm | 1–2 h | md5 từng file Kaggle == Oracle; symbol trong ticker 2026H1 ⊂ mapper Oracle (863) và `exchange_info_pin.json` (chỉ so TÊN) |
| B7 | Parity P5 (seal ĐÓNG, `SIM_END_DATE=20251231`, bundle mới): C1 seed 42 base, C2 seed 42 base, C3 M2-S seed 42 stress | Kaggle 3 kernel song song | ~45 min wall | md5 printDone == DEV: C1 `650c386f` (de-p1), C2 == `gqsf-a1`, C3 == run M2-S s42 của NSEL |
| B8 | **Holdout** (owner mở seal, `HOLDOUT_UNSEAL` qua `extra_env`, `SIM_END_DATE=20260630`, `ticker_min_days=2007`): 3 cấu hình × 8 seed × {base, stress 1,675%} = **48 kernel**, chạy liên tục từ `TIME_RUN=20210701` | Kaggle; ~35–45 min/kernel (DEV 54 tháng: 1 742–2 069 s JVM) | 4 slot: ~9–10 h; 2 slot: ~18–20 h | `result.json` jar sha, mapper ≥ 800, log có dòng `HOLDOUT_UNSEAL DUNG`, pred md5 theo seed |
| B9 | Chấm: 2 scorer độc lập (như NSEL J-F), script commit TRƯỚC khi tải output | Oracle | 2–3 h | lệch > 0,1% ⇒ hoà giải |

**Tổng:** ~12–16 h công agent (Sonnet cho B2/B5/B6/B9, Opus cho B4/B5-thiết kế) trải 2–3 ngày lịch; Kaggle ~40 kernel-giờ CPU + ~1 kernel-giờ cho B3/B4. Đĩa Oracle: +6–7 GB tạm (xoá sau upload). RAM Oracle: mọi bước ≤ 4 GB; 2 bước nặng (feat_v2 23 GB, net015 11 GB) đẩy Kaggle.

**Phương án rút gọn (không khuyến nghị):** `TIME_RUN=20250701` (đủ 90 ngày buffer + 6 tháng burn-in) ⇒ ~10 min/kernel, B8 ~2–3 h; đổi lại mất trạng thái liên tục với DEV và B7 không so được md5 DEV.

**Một jar hay ba jar:** stress 1,675% chỉ có ở jar NSEL (`b7c89f09`, port crashpen, J-C 0 lệnh đổi). Đề xuất dùng **1 jar `b7c89f09` cho cả 3 cấu hình**; khi đó B7 cho C1 (K16, NSEL OFF, penalty 0) là cổng parity mới bắt buộc vs `650c386f` (J-B mới chứng minh ở K24).

## 6. Rủi ro rò rỉ / thiên lệch và cách khoá

| # | Rủi ro | Mức | Khoá |
|---|---|---|---|
| R1 | 2026H1 từng là VAL (trước reset 09-05 / seal 09-01): feature, nhãn, fold plan, hằng số HPO GA (~2026-05, range không truy được) chốt khi 2026 đang được nhìn; artifact stale có data 2026 (`java/fsrun`, `java/simulator/storage`, `runs/*`, `team_*` — E3 §1.2) | CAO, không gỡ được | Khai trong pre-reg: kết quả = **forward test có nhiễm thiết kế**; chỉ dùng cho rào cứng + dấu ghép cặp giữa 3 cấu hình, không làm bằng chứng edge tuyệt đối |
| R2 | NHÃN 2026 nằm sẵn trong store gate (`label_*`) và `ds_label15m/funding_label_2026*` | CAO nếu sơ ý | Loader 2026 `usecols` chỉ feature; train assert `max(train_ts) < cut − purge` và `cut ≤ 2026-01-01`; glob nhãn train `202[1-5]` (bẫy `X1_LBGLOB`); review code trước chạy |
| R3 | Artifact có train 2026: `fold_20`, `model_cut20260701`, `wfo_gate_pred_2026_H1.csv` (Q2 từ fold_20), ONNX live 242 | CAO | Danh sách đen theo sha/md5 trong pre-reg; driver assert sha model ∈ danh sách trắng (S1 `af706dc6…`, net015 MANIFEST cut20251231, gate 8 model mới ghi meta) |
| R4 | Pool S1 = coin có nhãn tại tick (availability look-ahead: coin không có dữ liệu 4h tới bị loại) | THẤP–TB | Giữ y DEV để so sánh được; khai báo; không dùng giá trị nhãn |
| R5 | OI `create_time` đổi quy ước 2024-03-04 (2/281 symbol vẫn quy ước cũ 2026-05-15) | TB | Chỉ dùng file ghim `e3887f63`; nếu phải thêm đoạn: luật theo (symbol, ngày) + `v3.py` 18/18, `v6.py` 150/150 (OI_FIX_LOG §5) |
| R6 | Buffer gate rolling 90 ngày + warm-up 7 ngày | THẤP | Chạy liên tục từ 2021-07-01 ⇒ buffer đầu 2026 = 90 ngày cuối 2025 (quá khứ, hợp lệ). Nếu rút gọn TIME_RUN: ≥ 97 ngày trước 2026-01-01 |
| R7 | Mép fold net015 lệch lịch (`predict_wf_20251231.bin`) | TB | Không dùng file đó; predict lại theo mép +07 của DEV; kiểm span ≤ 100 ngày, không chồng/khuyết với fold 20251001 |
| R8 | Hiệu chuẩn net015 cut20251231 (GPU retrain) ≠ G015x26 gốc ⇒ hinge tuyệt đối `symbolPred ≤ 0,29` / `TRAIL_HINGE_NET015` đổi nghĩa | TB | Đo CHỈ trên DEV trước mở seal: phân vị P(win) f18-retrain vs gốc 2025Q4; ngưỡng chấp nhận chốt trong pre-reg |
| R9 | Model đông lạnh ≤ 2025 cho 2 quý (DEV refresh theo quý) | TB (mức tuyệt đối) | Đối xứng 3 cấu hình; báo theo quý; không so mức với DEV như tiêu chí |
| R10 | Universe 2026: coin niêm yết mới thiếu trong mapper Oracle (863)/`exchange_info_pin`/lineage v2 (627); coin chết 2026 + lỗi ffill đuôi `CLOSES_1H` v1 (DATA_AUDIT) | TB | Kiểm tên symbol (B6) trước; cách xử lý coin thiếu chốt trong pre-reg (KHÔNG ghi mapper 242; ghi mapper Oracle cần owner); ffill giữ y DEV (đồng nhất), scorer dùng v2 mở rộng |
| R11 | Ticker Kaggle 2026 chưa khớp md5 với Oracle | TB | Dataset mới từ Oracle + manifest md5, hoặc kiểm `2026pf` từng file |
| R12 | Rò kết quả trước khi khoá luật chấm / chạy lại khi thấy số | CAO | Scorer A/B commit trước tải output; một lần; chạy lại chỉ khi lỗi hạ tầng (rc, mapper, timeout) với cfg y hệt — khai trước; `HOLDOUT_UNSEAL` chỉ trong `extra_env` của 48 kernel B8; ghi ledger holdout |
| R13 | Selection: 3 cấu hình chọn trên DEV đã dùng 30+ lần; 8 seed chỉ đo nhiễu model, không đo nhiễu đường giá; 6 tháng ≈ 1/9 DEV | CAO (diễn giải) | Inflate k = 3 (√(2 ln 3) ≈ 1,48) trên half-width; thước SIZE/exposure = bootstrap return ngày MTM ghép cặp; thước cùng tập lệnh = ΔPnL ghép cặp theo lệnh; không dùng ΔCalmar ledger-closed; báo theo quý + ngày |
| R14 | Chồng lấp quan sát live | THẤP cho H1 | Cửa sổ H1 không chồng 242 G2FLAT3 (deploy 08-17) hay shadow (09-30); kéo sang 08 thì chồng ⇒ thêm lý do giữ H1 |

## 7. Quyết định cần MASTER/owner chốt trong pre-reg

1. Cửa sổ: **H1 (01-01→06-30)** [đề xuất] hay kéo tới ≤ 08-05 (+1–2 ngày dựng, §2.3).
2. Chạy liên tục từ 2021-07-01 [đề xuất] hay `TIME_RUN=20250701`.
3. Một jar `b7c89f09` cho 3 cấu hình [đề xuất, cần cổng C1 K16] hay jar riêng.
4. Dựng dataset: Python append + cổng byte DEV [đề xuất] hay Java export unseal (Kaggle / ngoại lệ RAM).
5. Gate 8 seed Python purge 15′ cut20260101 [đề xuất] hay giữ `fold_19` cho seed 42.
6. Xử lý symbol 2026 thiếu mapper/pin.
7. Luật phán xử: rào cứng RISK_APPETITE §9 + dấu Δ ghép cặp (C2 vs C1, C3 vs C2), inflate k = 3, không tune, một lần.

## 8. Nguồn
E3_HOLDOUT_2026_PREP / PREREG_HOLDOUT_2026_DRAFT (24c1aeec) · H1_HOLDOUT_PREP (37fd5024) · RESULT_S1REFRESH, RESULT_NET015_CUT20251231 (37fd5024) · PRED_PIPELINE_REPRO (13ee7c63) · DEPLOY242_G2FLAT3_READINESS (baf8c21d) · GATE_INVENTORY (886312a4) · DISK_INVENTORY (d79a2346) · OI_FIX_LOG (37fd5024) · RESULT_FEATDIFF_PASS2 (d024f310) · DEPLOY_SHADOW2_K24 (a9618cb4) · NSEL_VERDICT (f24acb13) · `tools/kaggle_sim.py`, `research/analysis/{gate_ablation,gate_seedband,gate_skipfull}_driver.py`, `research/pipeline/x1/*`, `WfoDataset.java`, `HoldoutSeal.java` · `wfo_ds_x1_2021/manifest.txt` · listing thư mục Oracle + `kaggle datasets list` (2026-10-08).
