# GATE_INVENTORY_20261004 — kiểm kê chuỗi gate p15 → dyn_thr → G2 của B0 (G2+FLAT3)

- **Ngày:** 2026-10-04. **Vai:** agent KIỂM KÊ, CHỈ ĐỌC (repo + git log/blame + file sẵn có). 0 train, 0 sim, 0 Kaggle, 0 sửa .java/.py, 0 chạm 242/shadow_c3.
- **Repo:** branch `module`, HEAD lúc đọc `a23d83ad`. Đường dẫn dạng `file:line` theo working tree HEAD đó. `KHÔNG TÌM THẤY` = đã tìm nhưng không có bằng chứng.
- **Phương pháp tìm:** `git grep` / `git log -S` (pickaxe) / `git blame` / đọc trực tiếp code + docs; mọi số lấy từ doc đã commit hoặc từ code, không chạy lại.

## 0. KẾT LUẬN CHO NGHI VẤN CỦA OWNER (rủi ro trước)

| Nghi vấn | Verdict | Bằng chứng chính |
|---|---|---|
| "Tham số train chưa đổi" | **ĐÚNG.** XGBoost depth4/n150/lr0.05 giống hệt ở mọi phiên bản script từ 2026-06-23 | `ml/gate/train_gate_fold.py:60-62` = `train_gate15m_v2_final.py:57-59` (64f47b91, cùng ngày 3111e72a) |
| "Có bước HPO nào không" | **Không có HPO cho model gate.** Có HPO (GA Jenetics) cho các hằng số entry/exit từ 2026-05, giờ đã đóng băng hardcode; không có bước HPO tự động nào đang áp trong B0 | §5 |
| "Feature + nhãn chọn cảm tính, chưa đổi" | **Một nửa.** Danh sách 33 cột + thứ tự (V3FULL) không đổi tên từ 2026-01-15; nhãn `label_oldbasket` chốt 2026-06-23 và chưa đổi. NHƯNG không phải "không đo": có featsel purged-CV (TASK-043), A/B 4 nhãn trên sim DEV, ablation từng feature (GATEFEAT); mọi lần đều KEEP. Và **giá trị feature đã đổi thật** (bug momentum/vol = 0 sửa 2026-06-02; định nghĩa basket đổi 2026-04-23) | §2, §3, §4 |
| "Store DEV không tái lập, corr 0.762" | **SAI/lỗi thời.** 0.762 = corr của `fold_20` đông lạnh áp lên cửa sổ 2025Q4; retrain per-fold tái lập `pred.bin` 19/19 fold (pearson 0.9918–0.9979) | `docs/result/RESULT_PREDBIN_REPRO.md` (bcfa83b8, 2026-09-28) |

## 1. MODEL GATE p15

**Kết luận:** p15 = `predReturn15M` = đầu ra 1 model XGBRegressor **market-level** (1 số / phút, mọi coin cùng giá trị), train expanding theo quý, chạy ONNX raw không scaler. Live (fold_20) cùng recipe/script với DEV, chỉ lệch 2 quý cutoff.

| Mục | Giá trị | Bằng chứng |
|---|---|---|
| Script train | `ml/gate/train_gate_fold.py` (bản y hệt ở `ml/training/train_gate_fold.py`, `diff` = IDENTICAL) | file; thêm vào git 3111e72a (2026-06-23), 66341cd9 (2026-07-01), c13574a2 (2026-08-24) |
| Điều phối | `WFOGateRunner.java` (Java điều phối, Python chỉ train): fold expanding, anchor `TRAIN_ANCHOR=20210101` (`:46`), minTrain 3 tháng (`:50`), OOS = step = 3 tháng; train `< cutoff` (`:139`) | `src/main/java/.../features/export/gate/WFOGateRunner.java` |
| Thuật toán | `XGBRegressor(objective="reg:squarederror", max_depth=4, n_estimators=150, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, min_child_weight=10, random_state=42, n_jobs=4)`; còn lại default xgboost | `train_gate_fold.py:60-62` |
| Config quyết định | **Không có file config.** Hyperparam hardcode trong script ("Tham số model = bản final đã chốt", `:7`); env chỉ `DATA, CUTOFF, OUT_DIR, GATE_LABEL, GATE_PURGE_MS` (`:18-20,35-36`) | `train_gate_fold.py` |
| Tiền xử lý | KHÔNG scaler; xuất ONNX `Model_Regressor_Return15M.onnx` (`:68-71`); `OnnxInferenceManager` chạy raw | `train_gate_fold.py:7`; RESULT_PREDBIN_REPRO §2.3 H2 |
| p15 dùng ở đâu | `predAll(...).return15M` → `AiPredictionData.predReturn15M` | `WFOGateRunner.predictOOSToFile`; `OnnxInferenceManager.java:51` |
| Live đang dùng | `Model_Regressor_Return15M.onnx` = `fold_20`: sha256 `d19fc8cd…` (md5 `8ec99757…`), cutoff **2026-04-01**, train 2021-01-01→2026-03-31; mtime 242 2026-08-17 16:27; bản Oracle `wfo_models/fold_20` mtime 2026-08-06, md5 trùng | `docs/audit/DEPLOY242_G2FLAT3_READINESS_20261002.md:21,44-45,59` |
| Recipe live = DEV? | **Cùng recipe** (cùng script, cùng 33 feature, cùng toolchain), fold muộn hơn 2 quý; retrain recipe cutoff 20260401 ↔ ONNX242: pearson 0.99821 / spearman 0.99877 | READINESS `:21,59-60` |
| Args/log lúc sinh fold_20 | **KHÔNG TÌM THẤY** (không có log/sha lần export 06/08) — RESULT_PREDBIN_REPRO §2.4(c) tự ghi là "khoảng trống provenance" | `grep purge_ms= ~/claudedata/*.log` rỗng |
| Đặc tính | p15 là số MARKET-level: mọi coin trong phút cùng p15, chỉ `symbolPred` (S1) khác nhau | `DetectEntrySignal2TradeNormal.java:942-943` |

## 2. FEATURE của model gate (33 cột V3FULL, thứ tự khoá cứng)

**Kết luận:** 33 feature **market-level** (1 vector/phút): 2 cột từ `MarketDataObject` (top-100 coin giảm mạnh), phần lớn là BTC/ETH 1m close, breadth + basket aggregate trên "top 50% volume", funding trung bình basket, 4 cột lịch. Không có cột symbol-level. Đọc định nghĩa: không thấy cột nào dùng dữ liệu sau `ts` (3 điểm CHƯA KIỂM ở cuối bảng).

Thứ tự + tên: `train_gate_fold.py:24-34` = `OnnxInferenceManager.java:67-81` (`extractFeaturesV3Full`). Tính ở `ComprehensiveMarketFeatureExtractor.java:61-86` (timestamp ép về đầu phút `:66`, anchor `BTCUSDT` `:76`).

| # | Cột (horizon) | Nguồn / công thức | file:line |
|---|---|---|---|
| 1,3 | momentum1M, momentum15M | `MarketDataObject.rateDownAvg`, `rateDown15MAvg` tại ts (TB top-100 coin giảm mạnh nhất; 1 nến / 15') — precomputed/inline | Extractor `:91-95` |
| 2,4,5,6 | momentum5M/1H/4H/24H | BTC return close 1m (ring `HistoryManager.getReturn`) | `:96-99,204-207` |
| 7 | momentumAcceleration | mom5M − mom15M | `:100` |
| 8,9 | trendStrengthETH, trendConsistency | ETH return 60'; dấu(mom5M·mom1H) | `:101-102` |
| 10-13 | volatility1M(3 nến)/15M/1H/24H | BTC `getVolatility` | `:105-109,209-212` |
| 14 | volatilityTermStructure | vol1H / vol24H | `:111-112` |
| 15-18 | advanceDeclineRatio, percentAboveMA20, volumeRatioUpDown, marketBreadthStrength | trên basket `CoinRankManager.getTopCoin(ts)`, nến hiện tại (close>open), MA20 | `:137-159` |
| 19 | btcDominance | volume BTC / (upVol+downVol) của basket | `:160-161` |
| 20-22 | rsi14, volumeSpike, distMA20 | BTC 1m: RSI14, vol/avg20, (close−MA20)/MA20 | `:119-134` |
| 23-25 | fundingRateRaw, Avg24H, Trend | TB basket, `FundingFeeManager.getNearestFundingFee` = `floorEntry(ts)` (quá khứ; >24h → 0) | `:214-251`; `FundingFeeManager.java:119-122` |
| 26-29 | hourOfDay, dayOfWeek, weekOfMonth, monthOfYear | `Calendar` JVM tz (GMT+7, TimeZoneGuard 7f70e30e) | `:255-262` |
| 30-33 | basketMomentum15M/1H, basketRsi14, basketVolSpike | TB trên basket | `:164-199` |

- **Basket** = `top50PercentSymbols` theo volume (đổi từ 6117d0be, 2026-04-23): `CoinRankManager.java:64-67`.
- **Nguồn dữ liệu:** close/volume 1m (Aerospike `kline_1m_opt`, replay bởi `ExportGateDataset.replayToCsv` `:140-190`) + funding map. **Không dùng OI** trong 33 feature gate.
- **Look-ahead (kiểm định nghĩa):** history = ring tới ts (`updateHistory(snap)` rồi mới extract, `ExportGateDataset.java:181,188`); funding `floorEntry`; lịch thuần ts. 7f70e30e (2026-06-02) "bịt look-ahead" đã xử lý nội-nến ở tầng sim. **CHƯA KIỂM:** (a) `MarketDataObject` tại ts có chứa close nến ts hay nến sau (`MarketDataInlineGenerator`, 7f70e30e); (b) `CoinRankManager.updateRanking` dùng cửa sổ nào (`checkAndUpdate :129-139`); (c) 4 cột lịch cho phép tree nhớ theo tháng/giờ (không phải leak, rủi ro khớp regime).
- **Ablation 33 feature (GATEFEAT, DEV 19 fold, IC de-overlap):** đề xuất bỏ 3 → 30 cột (có `rsi14`, bỏ làm IC tăng nhẹ); sim 48 tháng = NULL → **GIỮ 33** (`docs/result/RESULT_GATEFEAT.md:29,53,92-102`).

## 3. NHÃN gate

**Kết luận:** `label_oldbasket` = với rổ "losers" tại ts, trung bình theo coin của **max upside 15 phút tới** (từ close nến ts đến `maxPrice` cao nhất trong nến (ts, ts+15m]), sàn 0. Không phải return, luôn ≥ 0. 1 nhãn/phút, không de-overlap.

| Thành phần | Định nghĩa | file:line |
|---|---|---|
| Rổ | `findPotentialLosers(ts)`: coin có `totalUsdt ≥ 5000` ở nến hiện tại, `dropFromPeak = (close − max15m)/max15m < −0.001`, lấy **60 coin** giảm sâu nhất | `HistoryManager.java:477-510`; gọi `ExportGateDataset.java:194` |
| Nhãn | `basketMaxGain(lookup, ts, basket, 15')`: `entry = close@ts`; `maxGain = max_k (maxPrice_k − entry)/entry` trên `future = subMap(ts, false, ts+15m, true)`, `maxGain` khởi 0; TB qua coin | `ExportGateDataset.java:195,285-332` (`:293-295,314-325`) |
| Horizon | `LABEL_HORIZON_MS = 15 phút` | `ExportGateDataset.java:65-66` |
| Transform/threshold | Không (hồi quy trực tiếp trên giá trị thô, `reg:squarederror`) | `train_gate_fold.py:57-63` |
| Nhãn khác trong store | `label_ret15m/ret60m/retall15m/retall60m/max24h/retall24h` — chỉ cho A/B, không dùng ở B0 | `ExportGateDataset.java:129` |
| A/B chọn nhãn | oldbasket TOTAL_12w +13,812 vs ret60m +9,591 vs ret15m +7,520 vs gate-off −2,779; 24h THUA, "KHÔNG đổi gate live" | `docs/archive/_cleanup_20260829/docs/project-memory/track2_gate_ab_results_2026-08-18.md`, `gate_24h_label_verdict_2026-08-19.md:26,40` |
| **Purge `GATE_PURGE_MS`** | **CÓ dùng**: Java đặt env theo nhãn (`24h`→24h; chứa `60`→60'; còn lại **15'**) → script `tr_cut = cut − GATE_PURGE_MS`, train `< tr_cut`, assert không leak | `WFOGateRunner.java:197-201`; `train_gate_fold.py:35,44,46,52-53` |
| Thời điểm có purge | Commit đầu chứa purge: Java 463edee8 (2026-08-21), script c13574a2 (2026-08-24) — cả hai là commit **checkpoint WIP** nên ngày sửa thật có thể sớm hơn (bản 66341cd9 ngày 2026-07-01 chưa có purge). Bản gốc 3111e72a (2026-06-23) KHÔNG purge (`train = df[df.timestamp < cut]`). `wfo_models/fold_20` mtime 2026-08-06, `wfo_gate_pred.csv` mtime 2026-09-02: purge có áp hay không **KHÔNG XÁC ĐỊNH** (không có log `purge_ms=`) | git pickaxe; `ls -la` |
| Overlap nhãn | Nhãn mỗi phút, cửa sổ 15' ⇒ 2 nhãn liền kề chung 14/15 ≈ **93.3%** (suy ra, `ExportGateDataset.java:187` "MỌI PHÚT, không de-overlap"). Là tự tương quan trong train; **không** leak qua cutoff khi có purge 15'. Rò biên khi purge=0: ≤15 dòng cuối train có nhãn nhìn vào [cutoff, cutoff+15') — ghi nhận ở `WFO_LEAKS_TODO.md` L1 | `docs/archive/_cleanup_20260829/docs/insights/WFO_LEAKS_TODO.md:21-27` |

## 4. LỊCH SỬ THAY ĐỔI (feature / nhãn / script train)

Số commit chạm file (`git log --follow`): `ExportGateDataset` 3 · `WFOGateRunner` 7 · `train_gate_fold.py` 3 · `MarketFeatures` 5 · `ComprehensiveMarketFeatureExtractor` 15 · `HistoryManager` 15 · `OnnxInferenceManager` 16.

| Ngày | Commit | Đổi gì | Ảnh hưởng gate |
|---|---|---|---|
| 2025-12-01 | ab572070 | tạo `MarketFeatures`/extractor ("add ai filter") | khởi đầu |
| 2025-12-15 | 65b959ba | thêm `basketMomentum15M` + cột basket | feature set |
| 2026-01-15 | 60f2dae3 | "best benchmark v3": `extractFeaturesV3Full` 33 cột | **chốt danh sách 33 cột** |
| 2026-04-23 | 6117d0be | basket = top 50% volume (extractor, HistoryManager) | **đổi giá trị** 10+ feature breadth/basket/funding |
| 2026-06-02 | 7f70e30e | bịt look-ahead; sửa `getHistory()` rỗng ⇒ momentum/volatility trước đó **luôn = 0**; thêm ring O(1); `MarketDataObject` sinh inline | **đổi giá trị** nhiều feature |
| 2026-06-04 | a4b16fbf | gỡ `predReturn24H`/MOM24 | bỏ nhánh, 33 cột giữ |
| 2026-06-23 | 11228288, 64f47b91, 3111e72a | `ExportGate15mV2`, `train_gate15m_v2_final.py`, `WFOGateRunner` + `train_gate_fold.py`; nhãn `oldbasket` ("thắng bước B": IC 0.469 vs selector 0.459, `featsel_gate15m.py:3-5`) | **chốt nhãn + hyperparam** |
| 2026-07-01 | 66341cd9 | đưa code train vào git (provenance GAP #4) | không đổi recipe |
| 2026-08-11 | c56e1fdb | `ExportGateDataset` thêm 6 nhãn A/B (không dùng ở B0) | không |
| 2026-08-21/24 | 463edee8, c13574a2 | thêm `GATE_PURGE_MS` (Java + script; commit dạng checkpoint WIP) | **thêm purge 15'** (L1 leak vá ở code) |

**Kết luận:** (1) **tham số train: không đổi** từ 2026-06-23 (3 phiên bản script cùng depth4/n150/lr0.05/sub0.8/col0.8/mcw10/seed42). (2) **Danh sách+thứ tự 33 cột: không đổi** từ 2026-01-15; **giá trị feature đổi** ở 6117d0be và 7f70e30e (trước 2026-06-02 momentum/vol ra 0 — mọi model cũ train trên feature sai). (3) **Nhãn: không đổi** từ 2026-06-23 (các nhãn A/B thua). (4) Thay đổi duy nhất lên pipeline train sau chốt: purge. Featsel `ml/gate/featsel_gate15m.py` (purged 5-fold CV: baseline / drop-weak / backward / forward / top-k) chạy 2026-06-23; **output `gate15m_v2_featsel.json` không kiểm** ⇒ KHÔNG TÌM THẤY kết quả; V3FULL vẫn 33 cột nên featsel không cắt gì.

## 5. HPO — mọi dấu vết

**Kết luận:** (a) Model gate p15: **không có HPO** (không Optuna/sweep nào nối được tới depth4/n150/…). (b) Có **HPO bằng GA (Jenetics)** cho ~13 gene entry/exit/DCA/budget chạy ~2026-05, sau đó nhiều giá trị bị **revert** (2026-06-04) hoặc **đóng băng hardcode** (L7, 2026-09-11). (c) **Trong pipeline B0 hiện tại không có bước HPO nào đang áp** (không tự động, không thủ công); chỉ có (i) hằng số HPO cũ đóng băng, (ii) knob chọn bằng sweep DEV có pre-reg.

| Dấu vết | Bằng chứng |
|---|---|
| Engine HPO | `ai_ml/hpo/master/RunHpoMaster_Distributed.java:23-31`: Jenetics GA, population 50, ≤100 gen, dừng sớm 15 gen, `TOTAL_PARAMS=13`; distributed qua Aerospike/Kaggle (c65fd49d 2026-05-14); cache version v4→v11 (`:36-70`); fitness "V3/V4.2" (`:45-46`, 0bd65a14) |
| Giá trị "HPO mới nhất" | `Configs.java:337-339` blame cb50841b 2026-06-01 "update HPO mơi nhất" (cũ: MULT 1.40234, MIN 0.14568, MAX 2.24405) |
| Revert HPO | 1fbe620b 2026-06-04 "revert params HPO về cũ": `Configs.java:364,416,465-466,479-482` ghi "HPO (đã revert về cũ): 0.19727 / 0.01720 / −0.05514 / …" |
| WFO "không optimize" | frozen genome 17 gene min==max, IS_fit ≈ −100000: `docs/archive/.../arm_sweep_rootcause_wfo_no_hpo_2026-08-20.md` |
| Rolling WFO per-fold HPO N=30 | 1/18 fold SUCCESS; Σ OOS ≈ 8.5k vs frozen 22.7k ⇒ "tín hiệu tiêu cực về edge robust": `.../hpo_wfo_findings_2026-08-23.md` |
| Phương pháp | HPO trộn vào WFO ⇒ selection bias; đề xuất tail holdout: `.../wfo_methodology_hpo_in_wfo_2026-08-15.md` |
| Thư mục `kaggle_data_hpo/`, `s1hpo/` | **KHÔNG TÌM THẤY trong repo.** Chỉ có `configs/exit_dca_20260801_hpo.env`, `orchestrator/pipelines/wfo_dca_grid_hpo.json`, `tasks/112,210` |
| HPO khác | `PREREG_S1_HPO_BAG_FEATGRP.md` / `RESULT_S1_HPO_BAG_FEATGRP.md` (a04fc10) — cho **selector S1**, không phải gate; `python/tool/train_*_optuna.py` (market/funding XGB cũ) tồn tại, không mở, không nối được tới recipe gate |

**Từng hằng số** (HPO khi nào / dữ liệu / objective / pre-reg / hiệu lực trong B0):

| Hằng số | Giá trị | HPO khi nào, range, objective | Pre-reg | Trong B0 |
|---|---|---|---|---|
| `AI_DYNAMIC_MIN` | 0.26787 | cb50841b 2026-06-01; range dữ liệu + objective của lần chạy: **KHÔNG TÌM THẤY** (fitness V3 theo code) | không | **CÒN, hiệu lực**: hardcode `EntryGate.DYN_MIN` (`EntryGate.java:44`); là floor của `factor` trong r |
| `AI_DYNAMIC_MULTIPLIER` | 1.28760 | như trên | không | **CÒN**: `EntryGate.DYN_MULT` (`:48`) |
| `AI_DYNAMIC_MAX` | 2.14135 | như trên | không | **CHẾT**: tầng 1 bị bỏ khi `SELECTOR_RANK_TOPK>0` (`EntryGate.java:37-39`; `LEAN_GATE_AUDIT.md:73`) |
| rate_max `PREDICT_SYMBOL_RATE_MAX_THRESHOLD` | 0.15 | HPO đề xuất 0.19727 đã **revert** (`Configs.java:364`) | không | CÒN = `SCORE_BASE` (`EntryGate.java:46`) |
| `MIN_MOMENTUM_15M` | default 0.02284 (HPO 0.01720 revert) | `Configs.java:416` | không | Profile ghi đè `SIM_MIN_MOMENTUM_15M=0.008` (nguồn 0.008: override của WFO worker, `PHASE1_GENE_REFERENCE.md`); chỉ còn tác dụng ở warm-up 7 ngày + nhánh sp==null |
| `MS_DOWN_BIG_AVG` (BIG_DOWN) | −0.03157 | xuất hiện a391b7e0 2026-02-26 "optimize"; HPO −0.05514 revert (`Configs.java:466`) | không | **CÒN** (BIG_DOWN 248 lệnh, `AUDIT_CHAIN_AND_N_20261003.md` #5); nới −0.025 làm lệnh biên âm |
| `TS_DYNAMIC_K` | 0.29774 | có từ 2023-12-15 (7757433b `config.properties`) | không | **CHẾT** (`C2B_SPEC.md:486`; `PHASE1_RECIPE_FROZEN_v1.md:49,69`); không còn trong `Configs.java` |
| `TS_PROFIT_MULTIPLIER` | 5.21847 | có từ f1ff5892 2026-04-18 | không | không còn trong `Configs.java`/profile B0; chỉ còn dead-zone live `BinanceOrderTradingManager.java:485`; arm B0 = `SIM_RATE_PROFIT_STOP_MARKET=0.07` |
| `BUDGET_MARGIN_RATIO_1` | 0.4820 | không rõ | không | **CHẾT** khi `OFF_FLAT_HARD=true` (`PHASE1_GENE_REFERENCE.md:10-12`); không còn trong `Configs.java` |
| `BUDGET_DIVIDER_1` | 1.5578 | không rõ | không | liệt kê ở `TRADING_CONFIG_REDESIGN.md:13`; `PHASE1_RECIPE_FROZEN_v1.md:70` ghi BỎ; KHÔNG kiểm thêm |

## 6. CHUỖI p15 → QUYẾT ĐỊNH MỞ LỆNH

**Kết luận:** pass ⇔ `r = p15 / (max(0.26787, sp/0.15·1.2876)·1.55) ≥ q_t`, với `q_t` = phân vị 0.99995083 của `r` trên mọi ứng viên PREDICT **chưa giữ** trong 90 ngày, cập nhật mỗi giờ. `gs` triệt tiêu (r và ngưỡng cùng nhân gs) ⇒ gate là **QUOTA** ρ ≈ 6.2e-5/ứng viên, không phải ngưỡng tín hiệu (`AUDIT_CHAIN_AND_N_20261003.md` KẾT LUẬN 2-3). BIG_DOWN và DCA_LEVEL1 **không qua** nhánh này.

| Tầng | Công thức / hành vi | file:line | Tham số chọn thế nào |
|---|---|---|---|
| T0 p15 | model §1; sim đọc `predictionMap.get(ticker.startTime)`, `predict==null` ⇒ reject | `SimulatorMarketLevelTicker1MStopLoss.java:1318-1325` | — |
| T1 chọn ứng viên S1 | `symbol2Pred` sort tăng theo score `sp = 1 − P(win 4h)`; lấy K đầu; **bỏ coin đang giữ trước khi vào gate** | sim `:405-410,433-436`; live `DetectEntrySignal2TradeNormal.java:473,482,489` | K=16: owner chọn 2026-09-29 (`DECISION_BASELINE_R4.md`, 8→16), tham chiếu `RESULT_K_SWEEP.md` (428b3319, 8/10/12, thước tiền) |
| T2 factor | `max(DYN_MIN, (sp/SCORE_BASE)·DYN_MULT)`, 0.26787 / 0.15 / 1.28760 | `EntryGate.java:44-48,196` | hằng số HPO cũ (§5); `EntryGate.java:28` "ĐỪNG ĐỔI" |
| T3 gs | `GATE_DYN_SCALE` = 1.55 (key `SIM_GATE_DYN_SCALE`, `profiles/g2_flat3.properties`) | `EntryGate.java:58,191,197` | sweep gs (`RESULT_GATESCALE.md` 0.80/1.30/1.70, prereg 1985a81; `RESULT_GATESCALE_SWEEP.md:10` trên nền KEEPLEG0) kết luận **NULL** (không mức nào vượt mốc 1.70); 1.55 do owner chốt ở R4 (ưu tiên số lệnh), không do sweep chọn. Sau G2 **gs không còn tác dụng** trừ warm-up |
| T4 r | `r = p15/(factor·gs)` | `GateRollingRatio.java:105-108` | — |
| T5 q_t | quantile theo GIỜ, causal (`ts < h`), cửa sổ `days`, warm-up 7 ngày fallback `MIN_MOMENTUM_15M`=0.008; `k = floor(pct·(m−1))` | `GateRatioBuffer.java:21,42-68` | `pct = 1−ρ`, ρ = 4.9171e-5 đo từ G0 (35,488,397 ứng viên, 1745 pass), "1 tham số, không PnL" (`PREREG_GDV2_EVEN.md:51-56`, 2b4dcbd); `DAYS`: G1 W30 vs G2 W90 (k=2, inflate 1.1774): G1 FAIL T1 (UW 472.6, 2022 âm), G2 PASS 4 tầng ⇒ W90 (`RESULT_GDV2_EVEN.md`, 39944dbb) |
| T6 quyết định | `thrBase=q_t` ⇒ `EntryGate.threshold(q_t, sp)=q_t·factor·gs`; REJECT nếu `p15 < thr` | `AIRejectFilter.java:74-82`; `EntryGate.java:196-198` | — |
| Bypass | `sp==null` (BIG_DOWN, DCA_LEVEL1) ⇒ ngưỡng 0.008; BIG_DOWN không gọi `entryGate` | `EntryGate.java:195`; sim `:1326` | — |
| FLAT3 (exit, ngoài gate) | `TS_GIVEBACK_RATIO=1.0`, `SIM_TS_MAX_GAP[_WEAK]=0.03` | `RESULT_TRAIL2_G2.md` (3969bc84/baf8c21d): chọn "luật đơn giản nhất không kém" (CI chứa 0) | pre-reg có |

**q_t có loại held-symbol không:** **CÓ, cả sim và live** — coin đang giữ bị `continue` trước `createOrder`/`createOrderBuyRequest` nên `noteCandidate` và nạp `r` vào buffer chỉ xảy ra cho coin chưa giữ (`AIRejectFilter.java:65-69,74-82`; sim `:433`, live `:482`). Rank vẫn đếm trên toàn top-K ("cap-then-skip", sim `:417-419`, live `:473-474`).

**Sim vs live:** cùng `AIRejectFilter.entryGate` → `EntryGate.threshold`; lõi q_t dùng chung `GateRatioBuffer` (`GateRatioBuffer.java:8-11`: bit-identical sim/live); live ưu tiên key `LIVE_GATE_ROLLING_*`, sim `SIM_*` (`AIRejectFilter.java:75-80`). **Khác biệt đã khai:** (1) seed live **không** tái tạo loại held-symbol, tick thiếu bị bỏ, sp seed = predictionSymbol (`LiveGateRollingRatio.java:213-222`); (2) nhịp `SIM_ENTRY_SAMPLE_MIN=1` ↔ `LIVE_ENTRY_GRID_MIN=1`; (3) buffer live ramp 7→90 ngày từ 2026-09-30, đủ ~12-29; (4) **p15 đầu vào khác nguồn feature** (§8); (5) model lệch 2 quý. Không có test parity đo `q_t` live vs sim-replay cùng chuỗi `r` (`AUDIT_CHAIN` §6 #4).

## 7. DỮ LIỆU DEV p15 (bins) và ghi chép "corr 0.762"

| Mục | Giá trị | Bằng chứng |
|---|---|---|
| p15 DEV | `/home/ubuntu/wfo_ds_x1_2021/pred.bin`: md5 `5dd6bb4c3f98d89d58770005c0001526` (= `manifest.txt`), 2,500,260 dòng, 2021-04-01→2025-12-31 23:59, lưới 1', big-endian `[ts:i64][p15:f32][predRisk4H:f32]`; bản y hệt ở `simbundle`, `simbundle_x1_t170` | `RESULT_PREDBIN_REPRO.md` §1.1 |
| Sinh bằng | `ExportGateDataset` → `WFOGateRunner` (21 fold) → `wfo_gate_pred.csv` (md5 `b160a018…`, join 2,500,260/2,500,260, corr 1.0) → `LoadWfoGatePredTool` → set `ai_pred_market_gate_wfo` → `WfoDataset.export` 2026-09-12 (`codeGitSha=e57fd3d`) | §1.2 |
| Bins selector | `predwf_map_s1a2*` (sp của S1, 26 B/bản ghi), sinh 2026-09-02; md5 từng file ở `research/pipeline/BINS_MANIFEST.md` | file; `AUDIT_CHAIN` header: p15 printDone == `p15_dev` 2223/2223, sp == bins 2223/2223 |
| Tái lập | **TÁI LẬP ĐƯỢC bằng retrain**, không bit-exact: 19/19 fold pearson 0.9918–0.99786, spearman 0.9847–0.99812, p50 khớp 1e-5; max cực trị lệch 1–20% (nhiễu) | §2.2 bảng |
| "corr 0.762" | = corr `fold_20` đông lạnh (train tới 2026-04) áp lên 2025Q4 = **0.76214**; per-fold đúng cách `fold_18` chỉ 0.681 vì model đông lạnh khác thế hệ. Doc gốc `RESULT_P15_SOURCE.md` §3.4 ("store gốc đã mất") đã bị đánh dấu **SAI** ở `:130` | `RESULT_PREDBIN_REPRO.md` §2.1; `PREREG_PREDBIN_REPRO.md:1,16` |
| Khoảng trống còn lại | bộ `.onnx` đông lạnh thuộc thế hệ nào: **KHÔNG TÌM THẤY** log/sha; cột `predRisk4H` lấy từ set cũ **không leak-free** (model tĩnh train tới ~2025-12-19), nhưng nhánh RISK đã bỏ khỏi gate từ 2026-08-08 (`AIRejectFilter.java:101-102`) |  §2.4(c), §3(1) |

## 8. LỖ HỔNG ĐÃ GHI TRONG DOCS VỀ GATE — TRẠNG THÁI

| Lỗ hổng | Trạng thái | Bằng chứng |
|---|---|---|
| L1 label leak quanh cutoff (nhãn 15' nhìn vào OOS) | **Đã vá ở CODE** (purge 15', assert; commit đầu 2026-08-21/24, dạng checkpoint WIP). **Chưa chứng minh áp cho dữ liệu đang dùng**: `fold_20` (mtime 08-06) và `wfo_gate_pred.csv` (09-02) đều không có log `purge_ms`. Độ lớn: ≤15 dòng biên / ~2.5M | §3; `WFO_LEAKS_TODO.md:21-27` |
| "L1 leak, overlap 93%" | Là nghi vấn của **selector G015** (grid 15m, nhãn 4h), **không phải gate**: KẾT LUẬN "chỉ chồng lấp cửa sổ, không leak thật" (purge 72h > horizon 4h, ra 68.25h ở 16/16 vòng), spearman không chồng lấp 0.1718 vs 0.1675. Chuỗi "93%" **KHÔNG TÌM THẤY** trong docs; 93.3% ở §3 là suy ra (14/15) cho nhãn gate. Lỗ hổng mở còn lại: 40 feature Tool1 "opaque" của S1 | `docs/analysis/LEAK_L1_REPORT.md:61,120-121`; `AUDIT_APPLIED.md:410-411`; RESULT_PREDBIN_REPRO §4.5 |
| p15 live ≠ p15 DEV | **MỞ — CHẶN-TIỀN-THẬT.** Giả thuyết "khác thế hệ model" đã bác bỏ (ONNX242 max 1.895% vs DEV-gen 1.975% trên cùng feature live, pearson 0.985); còn lại: **input 33 feature live khác store DEV** (nghi VTS + funding). Live max 2.30% (n=8,986) vs DEV 2025Q4 cực trị 11.95%. `B0_LIVEMODEL` chưa chạy | `AUDIT_CHAIN` #2, §6.3; READINESS Q2 `:22,79-98`; RESULT_PREDBIN_REPRO §3(3) |
| `ai_pred_1m` trộn nguồn (242 + shadow, `gen=2`) | **Có bản vá chuẩn bị** (jar `f282581a` + `LIVE_IS_SHADOW_HOST=true`, bỏ ghi `ai_pred_1m`); trạng thái deploy **KHÔNG xác minh được từ repo**. Dữ liệu đã nhiễm không sửa; phân tích "p15 live 242" phải cắt từ T_restart | `FIX_NO_WRITE_242_20261003.md:35-41,110-115`; `PARITY_LIVE_VS_SIM_20261003.md:101,118` |
| Gate live ramp W7→W90 | **MỞ** (buffer 242 từ 2026-09-30; đủ 90 ngày ~12-29); DEV chưa có run "W tăng dần" | `AUDIT_CHAIN` §6.1 |
| Model live trễ 2 quý (fold_20, cutoff 2026-04-01) | **MỞ** (B0 đúng = cutoff đầu quý đang giao dịch; Q4/2026 cần cutoff 2026-10-01 + nối store bằng Java replay) | READINESS `:77` |
| `q_t` phụ thuộc sổ lệnh (held-symbol) | **MỞ**: tái lập không trừ held chỉ ra 43 ngày-mở thay vì 141; seed live không trừ held | `AUDIT_CHAIN` §3, §6.4 |

## 9. ĐIỂM ĐÁNG NGỜ NHẤT (theo bằng chứng)

1. **Chuyển giao p15 DEV→live chưa chứng minh, và edge B0 có thể không sống ở regime live.** DEV 2025Q4 cực trị p15 11.95% vs live max 1.9–2.3%; sau warm-up G2 vẫn pass ~4.9e-5·ứng viên "bất kể model" nhưng ở p15 ≈ 1.3–2% thay vì ≥ 3% như DEV (READINESS `:98`). Nguyên nhân còn lại = feature live ≠ DEV; `RESULT_FEAT_DIFF_PASS1.json` mới có 46 dòng live, `matched_ts_pairs=0`, `sufficient_ge_200=false` ⇒ **chưa đo được**.
2. **Gate thực chất là quota nhân với thứ hạng S1, không phải "dự báo thị trường".** Proxy chỉ-p15 chỉ tái lập 30% ngày-mở (`AUDIT_CHAIN` #3); `gs` triệt tiêu; ρ = 1−pct lấy từ chính DEV (R4). Mọi lever K/pct/gs đều là cùng 1 lever (nới quota). Trong khi 4/33 feature p15 là lịch (hour/dow/wom/month) cho tree nhớ regime.
3. **Selection trên cùng DEV 2021-2025 nhiều lần, không phân tách tầng.** Nhãn (A/B sim 2023-2025), `gs`, K, pct/W, FLAT3, đều chọn trên cùng cửa sổ; `AUDIT_CHAIN` header ghi "DEV đã dùng 30+ lần"; inflate chỉ theo k từng vòng. Chính `wfo_methodology_hpo_in_wfo_2026-08-15.md` đã chỉ ra lỗi cấu trúc này; rolling-WFO per-fold HPO (08-23) cho kết quả kém frozen ×2.7.
4. **Hằng số HPO `AI_DYNAMIC_MIN/MULT` nằm cứng trong `EntryGate` mà không có range/objective/pre-reg truy được.** Chạy GA ~2026-05 trên Aerospike dataset (có thể trùm cả 2026 H1 và DEV; **KHÔNG TÌM THẤY** range); cùng đợt HPO nhiều gene khác bị revert vì "drift" (1fbe620b). Floor 0.26787 chỉ bind 1/140,244 mốc (`EntryGate.java:22-23`) nên rủi ro thực nhỏ, nhưng MULT 1.2876 co giãn toàn bộ `factor`.
5. **Provenance purge mờ:** không có log cho `fold_20` (live) lẫn `wfo_gate_pred.csv` nên không biết purge 0 hay 15'; code vá nằm trong 2 commit checkpoint WIP (08-21 Java, 08-24 script, lệch 3 ngày ⇒ từng có bản Java đặt env mà script chưa đọc). Ảnh hưởng số học nhỏ (≤15 dòng/fold), nhưng "chưa chứng minh sạch" ≠ "sạch".

## 10. KHÔNG TÌM THẤY

- Log/args lúc sinh `wfo_models/fold_20` và `wfo_gate_pred.csv` (không có `purge_ms=` trong `~/claudedata/*.log|*.out`).
- Nguồn gốc con số depth4/n150/lr0.05/sub0.8/col0.8/mcw10 (chỉ có comment "bản final đã chốt", `train_gate_fold.py:7`); không log HPO/Optuna nối tới gate.
- Range dữ liệu, objective, ngày chạy, pre-reg của HPO ra `AI_DYNAMIC_MIN/MULT/MAX`, `TS_DYNAMIC_K`, `TS_PROFIT_MULTIPLIER`, `BUDGET_*`, `MS_DOWN_BIG_AVG`.
- Thư mục `kaggle_data_hpo/`, `s1hpo/` trong repo.
- Kết quả `featsel_gate15m` (`gate15m_v2_featsel.json`) — không kiểm file.
- Chuỗi "93%" trong docs; sha/log của bộ `.onnx` đông lạnh `wfo_models/gate_ab_full/models`.
- Kiểm look-ahead chưa làm: `MarketDataInlineGenerator`, `CoinRankManager.updateRanking`, nguồn chính xác `rateDownAvg` tại ts.
- Trạng thái deploy thực của bản vá `FIX_NO_WRITE_242`.
