# HO4-P0 — thiết kế + kiểm pipeline dựng holdout 2026 từ dữ liệu sàn (Vision), lát DEV (agent HO4-P0, 2026-10-10)

Pre-reg: `docs/prereg/PREREG_HOLDOUT2026H1.md` ADDENDUM-5 **`31e3c9e7`** (nguyên tắc MASTER nguyên văn + cổng P3 chốt TRƯỚC khi dựng/đo; khai: chưa nhìn số sim Q3). Không dựng dữ liệu 2026, không sim cửa sổ 2026, không mở printDone/equity 2026. JSON `docs/result/ho4/`. Script `research/analysis/ho4_*.py`. Oracle `~/claude_master/1010/ho4/`.

## KẾT LUẬN (rủi ro trước)

**P3 FAIL ⇒ DỪNG, không dựng 2026, không đẩy 32 kernel.** Dữ liệu sàn của các symbol DEV trùng tuyệt đối (kline 99,9999993%, funding 100%), nhưng mọi thành phần cross-section dựng lại bằng công cụ gốc đều lệch DEV (market 44,9%, store gate 60,6%, Tool1 55,1%, nhãn 96,5%, feat_v2 70,8%, p15 38,6%, net015 19,2%, bins 3,7%) và 2 sim DEV trùng lệnh chỉ 61,2% (k24) / 55,4% (b0), \|ΔΣPnL_S\| 22,1% / 7,2% — cỡ ngang đổi seed p15. Theo luật: không nới, không vá.

Chẩn đoán (đo, không sửa):
1. **Universe khác:** Vision USDT ∩ mapper có symbol store DEV không có (CTK, CVC, CVX, SLP đang giao dịch; BNX settle 100% phút volume 0; thêm BTCDOM/USDC vốn chỉ bị loại bởi `DIED_SYMBOLS`/bộ lọc riêng từng tool) ⇒ trung bình thị trường, breadth, basket, rank cross-section đổi ở gần MỌI phút. Vision còn lấp lỗ phút store DEV (0,49% ô; 2025-12-15 thiếu giờ). CLOSES_1H Vision 1h có 13 symbol (settle/BTCDOM/USDC…) mà ghim v1 không có ⇒ rank feat_v2 lệch.
2. **Công cụ market không tất định về tập phút:** `DataManagerAerospikeFloatSim.saveMarketDataBatch` dùng CHUNG một `SimpleDateFormat` trong `parallelStream` ⇒ key phút sai/trùng ⇒ mất phút ngẫu nhiên (bản dựng lại mất 8,8%; giải thích 2,8% phút thiếu + 2 348 phút trùng `time` của set DEV).
3. **Chẩn đoán D1 (cùng kernel, đầu vào = ticker DEV + funding local DEV):** market trùng **bit-exact 100%** trên 233 329 phút chung (công cụ tất định về giá trị) nhưng tập phút vẫn lệch (24 118 chỉ-DEV / 6 774 chỉ-mới — race ở mục 2); store gate CHỈ 66,5% (breadth/basket/funding-avg lệch ~mọi dòng), Tool1 85,5% (khoá trùng 100%), nhãn 98,3% ⇒ **store gate/Tool1/nhãn DEV (export 08-08/08-13 từ Aerospike Oracle lúc đó) không tái sinh được ngay cả từ chính ticker DEV (export 08-21/22) + bản sao funding/lifecycle hiện tại** — trạng thái store lúc export không còn. Thước "tất định so với DEV ở mức thành phần" của nguyên tắc 3 vì vậy không đạt được với bất kỳ nguồn nào cho các thành phần này.
4. OI: `oi_z` (expanding toàn lịch sử) chỉ 10,4% ô rel ≤ 1e-6 (lịch sử Vision khác lúc build ghim); 4 cột còn lại ≥ 99,98%.

Câu hỏi cho MASTER (không tự quyết): (a) chấp nhận DEV không tái sinh được ở mức thành phần và chuyển thước P3 sang "pipeline Vision tất định với CHÍNH NÓ" (chạy 2 lần cùng input ⇒ trùng; cần sửa race `SimpleDateFormat` trong tool = sửa .java, ngoài quyền agent) + khai 2026 là dữ liệu-sàn-mới, không so DEV; (b) luật universe 2026 (loại settle/volume 0, loại `DIED_SYMBOLS`, hay giới hạn theo exchangeInfo TRADING) — phải chốt trước khi dựng; (c) CLOSES_1H: dùng 1m Vision (close phút :59) như v2 thay vì Vision 1h.
## P1 — Kiểm kê công cụ dựng từng thành phần (DEV bundle `sim-x1-2021-bundle` + `wfo-ticker-*`; HO26 `sim-ho26a-bundle`)

| Thành phần | Công cụ đã dựng DEV | Công cụ HO26 (H1 2026) | Input thô | Output | Tái chạy trên Kaggle? | Phụ thuộc |
|---|---|---|---|---|---|---|
| ticker 1′ (`ticker_YYYYMMDD.bin.gz`, ngày UTC, O/H/L/C/quoteVol float32, chỉ USDT) | Java `ai_ml/hpo/kaggle/ExportTickerDaily` dump Aerospike Oracle `test.kline_1m_opt` (tickexport 08-21/22) | cùng tool, cùng store (store chép từ 242 ⇒ mang lỗi 242 từ 04-25) | kline 1m (store ingest Binance) | 1 826 file DEV, 181 file H1 | Không có đường Java Vision→store; **bộ ghi `ho3b_jwrite.py`** (byte-format ObjectOutputStream, round-trip 3/3) + Java `IngestTickerFileToAerospike` để nạp store trong kernel — NGOẠI LỆ Python khai | Vision klines 1m |
| `market_data_object` → `market.bin` | Java `research/ExportMarketData2File.exportMarketEntries` (đọc store kline, `MarketBigChangeDetector.calMarketData`, key `yyyyMMdd-HHmm` theo TZ JVM) + `MarketObjectGapRepairTool`, nhiều lượt; dump `WfoDataset.export` (scanAll, last-wins) | DEV byte + append 2026 dump set (Python, last-wins) | store kline | market.bin `4ab691c9` (DEV), `34e33678` (HO26) | **Có**: tool gốc trong jar `b7c89f09`, chạy trên Aerospike trong kernel; dump set = scan (không logic) | kline (tập symbol, lỗ phút) |
| 3 momentum gate + Tool1 `rateDown15MAvg` | (đi kèm market_data_object) | inline cho Q3 (ADDENDUM-4 §4) | — | — | — | market |
| store gate 33 V3FULL (`gate_dataset_full.csv.gz` 08-08) | Java `ExportGateDataset.replayToCsv` (store kline + market_data_object + funding_data qua `FundingFeeManager`) | cùng lượt export 08-08 (H1 2026 nằm trong file DEV) | kline, market, funding | store 2 889 623 dòng | **Có** (HO3b §4c: Aerospike trong kernel, sau warm-up tái hiện HO26 100%) | kline, market, funding |
| pred.bin p15 | seed 42: Java `WFOGateRunner` (21 fold, `train_gate_fold.py`) → csv → set → `WfoDataset.export`; fold ONNX trên đĩa KHÔNG phải thế hệ sinh pred.bin (RESULT_PREDBIN_REPRO); 7 seed Python retrain | model HO1 B2 cut 2026-01-01 +07 × 8 seed (Python XGB, `ho1_gate_build.py`) predict store H1 | store gate | `5dd6bb4c` DEV; `22f69456`(s42) HO26 | Predict-only Python (model json có); DEV fold model seed 42 mất | store gate |
| Tool1 15′ (`ds_feat15m/*.t1c.gz`, 08-13) | Java `ExportFeaturesForPythonTool` `FF_UNFILTERED=1` (HO3b §4c) | cùng lượt 08-13 (file 2026 tới 07-01) | kline, market (`rateDown15MAvg`), funding (Aerospike) | 20 file quý UTC | **Có** (exporter trong kernel) | kline, market, funding |
| nhãn pool (`ds_label15m/*.pb`) | Java `ExportFundingLabel` (LABEL_STEP_MIN 15) | cùng lượt 08-13 | kline (+72 h nhìn trước), `symbol_lifecycle` | 20 file | **Có** | kline, lifecycle |
| funding_data | store Aerospike (ingest Binance API) | store local (chết 07-07) | — | set 831 obj | Vision fundingRate nạp vào cùng format record (`f_data` = snappy(json)); HO3 F1: giá trị trùng 100% trên mốc chung | — |
| OI per-coin `oi_percoin_full.bin` (`e3887f63`) | build Kaggle cũ từ Vision metrics, KHÔNG qua code repo (OI_FIX_LOG §2.1) — công cụ gốc không còn | ghim (H1 nằm trong file) | Vision daily metrics | 5 cột/5′ | Port Python `ho3b_oi_rebuild.py` — NGOẠI LỆ khai | Vision metrics (Vision đã sửa 2026-06, HO3b) |
| CLOSES_1H | `java/fsrun` (generator không còn); F0 `closes1h_build.py` (Python, Vision 1h) | `closes1h_build.py` cho 2026 | Vision klines 1h | 627 sym | Python (đúng tool đã dùng cho 2026) — NGOẠI LỆ khai cho DEV | Vision 1h |
| feat_v2 KEEP9 | `x1_feat_v2_build.py` (Python) | `ho1_featv2_window.py` (cùng công thức) | CLOSES_1H, OI | parquet | Python = cùng tool | CLOSES, OI |
| ledger/pool S1 | `x1_ledger.py` (Python) | `ho1_s1_2026.avail_pool` (định nghĩa ADDENDUM-1 §4) | p15 s42, nhãn | — | Python | p15, nhãn |
| S1 predict | `x1_s1_rank.py` (Python; model `s1a2x1_cut20251001` tái hiện fold Q4 max\|d\| 0; fold 20250701 model không lưu) | `s1a2x1_cut20251231` predict-only | feat_v2, pool | `pred_s1a2x1` | Python | feat_v2, pool |
| net015 (G015x26) | kernel Kaggle GPU 08-14 (trainer mất); 16 fold JSON mất; còn ONNX f15 (`7921ceaf`) + backup dự đoán `predwf-g015x26-gate` | ONNX f15 predict-only (phương án A) | Tool1 + OI (`build_rows`) | predict_wf_*.bin | Python/ONNX | Tool1, OI |
| bins | `x1_build_map.py` (Python) | cùng | net015, S1 | 26 B/rec | Python | net015, S1 |
| funding.bin | Java `WfoDataset.buildFundingFromWfFiles`; Python `ho1_funding_build` tái sinh byte `8e57d900` (G-B5f) | Python | bins, lưới market.bin | 4,45–5,5 GB | Python (trong kernel sim) | bins, market |

**Vì sao cổng 4 HO3b dùng generator inline:** ADDENDUM-4 quyết định 4 (MASTER) chọn `MarketDataInlineGenerator` vì set `market_data_object` không còn ghi sau 2026-08-13 và HO3b chạy trên 242/Oracle (không có store kline Q3 trong kernel lúc đó). Công cụ gốc sinh set DEV (`ExportMarketData2File`) **có tồn tại** trong jar — khác inline ở: không guard `MIN_SYMBOLS`/cold-drop, ghi mọi phút `calMarketData` khác null; inline bỏ phút có < 50 symbol hợp lệ. HO3b đo inline vs HO26 trên H1 (dữ liệu 242) — phép so đó trộn 2 khác biệt (công cụ + lỗi 242) nên không chẩn đoán được nguồn lệch.

## P3 — Kiểm pipeline trên lát DEV S = [2025-07-01, 2026-01-01) +07 (ngưỡng chốt ở ADDENDUM-5 §5.3 trước khi đo)

Universe dựng lại = Vision `futures/um` USDT, không `_`, ∈ mapper 863 (481→608 symbol/tháng); lệnh DEV trong lát 234 symbol (đều có trên Vision trừ 币安人生USDT — chỉ lỗi URL của script so K). Lead-in từ 2025-06-01.

| # | Thành phần | Công cụ (dựng lại) | Kết quả | Ngưỡng | Kết luận |
|---|---|---|---|---|---|
| K-a | kline giá trị (khoá chung, 6 tháng) | Vision 1m (Oracle, `ho3_b2_kline_vision.py`) | 142 604 152 / 142 604 153 = **99,9999993%** | ≥ 99,99% | PASS |
| K-b | khoá chỉ-DEV | — | 4 820 = **0,0034%** | ≤ 0,01% | PASS |
| — | khoá chỉ-Vision (lỗ ticker DEV, mô tả) | — | 698 900 = 0,49% (gồm 2025-12-15 thiếu giờ) | — | — |
| F | funding (507 367 mốc store DEV, 574 symbol) | Vision fundingRate | **100%** (0 mốc thiếu, 0 lệch) | 100% | PASS |
| M | market.bin | `ExportMarketData2File` (jar b7c89f09, Aerospike trong kernel) → dump set | **44,9%** ô (phút chung 234 754: 50,5% ô ≤1e-6, 15,0% dòng đủ 3 cột, max\|Δ\| 0,061; chỉ-DEV 22 693 phút; chỉ-mới 6 840) | ≥ 99,9% | **FAIL** |
| G | store gate 33 V3FULL (264 960 dòng hai bên) | `ExportGateDataset` | **60,6%** ô; lệch ~mọi dòng: breadth (advanceDecline, percentAboveMA20, volumeRatioUpDown, marketBreadthStrength, btcDominance), basket×4, fundingRate×3 (~233 k dòng); momentum1M/15M/Accel ~54%; cột per-coin (momentum5M…, volatility, rsi) ~99,6% | ≥ 99,9% | **FAIL** |
| T | Tool1 40 cột (8 583 757 khoá DEV, 112 674 khoá chỉ-mới) | `ExportFeaturesForPythonTool` `FF_UNFILTERED=1`, mép file DEV | **55,1%** ô (mô tả 0,01·IQR: 86%) ; cột tệ nhất 14–16, 32–34 ≈ 0% | ≥ 99,9% | **FAIL** |
| L | nhãn nBars_72h (tick ≤ 12-28 23:45 UTC) | `ExportFundingLabel` | **96,5%** khoá DEV (tìm thấy 8 476 926 / 8 490 842; chỉ-mới 46 324) | ≥ 99,9% | **FAIL** |
| O | OI 5 cột (mô tả) | `ho3b_oi_rebuild` (kernel `ho4-dev-oi`) | ls_global 100%; ls_toptrader 99,9999%; taker 99,992%; oi_delta24h 99,977%; **oi_z 10,4%** rel≤1e-6; chỉ-mới 29 599 dòng | — | — |
| V | feat_v2 KEEP9 | `closes1h_build` (Vision 1h) + OI ghép + `ho1_featv2_window.features` | **70,8%** ô (rk_dd_7d, rk_ret_3d ~0%, rk_oi_delta24h 61%; cột không-rank ≥ 96%) | ≥ 99,9% | **FAIL** |
| P | gate p15 (model s42 cut20260101) | Python XGB predict | **38,6%** dòng \|Δ\|≤1e-6; max\|Δ\| **0,226**; 0/264 960 dòng 33 feature trùng | ≥ 99,9% | **FAIL** |
| N | net015 p0 Q4 (ONNX `7921ceaf` gốc) | `build_rows` + ONNX | **19,2%** ô ≤1e-3; spearman 0,983; max\|Δ\| 0,53; khoá mới thừa 81 901 (Q3 xấp xỉ Δ: 25,7%) | khoá trùng ∧ ≥ 99% | **FAIL** |
| B | bins Q4 (`x1_build_map`, S1 cut20251001 gốc) | Python | **3,7%** ô (Q3: 11,9%); pool Jaccard 0,842 | khoá trùng ∧ ≥ 99% | **FAIL** |
| — | kiểm đường ống S1 | S1 cut20251001 trên pool+feature DEV Q4 | == `pred_s1a2x1` (max\|d\| 0, 3 499 202 dòng) | — | đường ống đúng |
| — | kiểm đường ống funding.bin | khối FUND_REBUILD_HO4 với bins DEV trên lưới market DEV | trùng byte 257 433/257 433 bản ghi S | — | đường ống đúng |

### Cổng sim (đầu-cuối; `SIM_END_DATE=20260101`, không UNSEAL; thay ticker ngày UTC 07-01..12-31, market, pred s42, funding.bin dựng trong kernel)

| kernel | lệnh start ∈ S mới / gốc | trùng (sym, start ±1′) | \|ΔΣPnL_S\| | dòng start < 2025-07-01 | md5 dòng < SEAL | kết luận |
|---|---|---|---|---|---|---|
| `sim-ho4-dev-k24-s-s42` | 498 / 461 | 305 = **61,2%** | **22,1%** | 3 056 trùng từng dòng | khác | **FAIL** (≥ 99% ∧ ≤ 1%) |
| `sim-ho4-dev-b0-s-s42` | 372 / 341 | 206 = **55,4%** | **7,2%** | 2 151 trùng từng dòng | khác | **FAIL** |

Toàn vẹn 2 kernel: jar, override, pred md5 (`31de47f1`, base `22f69456`), mapper, penalty 0,01675, không UNSEAL, ticker 1 826 (1 642 DEV + 184 dựng lại, md5 184/184 == exporter), FUND_HO4_SELFCHECK trùng byte 257 433/257 433, `FUND_HO4_OK`. Tham chiếu (không phải chuẩn — nguyên tắc 3): đổi seed p15 cùng cấu hình cho trùng 57–67% (k24) / 57–84% (b0) — dựng lại dữ liệu từ Vision làm lệch đường lệnh cỡ ngang đổi seed.

### Chẩn đoán D1 (KHÔNG phải cổng; kernel `ho4-dev-d1`: ticker = `wfo-ticker-2025h1/h2` DEV, funding_data = bản sao local DEV, cùng exporter/jar/config)

| Thành phần | Vision (cổng) | D1 (đầu vào DEV) | Đọc |
|---|---|---|---|
| market.bin giá trị phút chung | 50,5% ô ≤1e-6 | **100% bit-exact** (233 329 phút) | công cụ tất định về giá trị; lệch giá trị ở cổng = do universe/lỗ phút Vision |
| market.bin tập phút (chỉ-DEV / chỉ-mới) | 22 693 / 6 840 | 24 118 / 6 774 | race `SimpleDateFormat` ⇒ tập phút KHÔNG tất định |
| store gate 33 | 60,6% | 66,5% (breadth×5, basket×4, funding×3 lệch ~mọi dòng; momentum×3 lệch đúng các phút market thiếu) | store DEV phụ thuộc trạng thái Aerospike lúc export (08-08) không còn |
| Tool1 | 55,1% (khoá thừa 112 674) | 85,5% (khoá trùng 100%) | phần lệch còn lại không do dữ liệu Vision |
| nhãn | 96,5% | 98,3% (DEV thừa 13 916 khoá) | như trên |

## P4 — kế hoạch 2026: xem `HO4_P0_P4` dưới (chưa làm; bị chặn bởi P3 FAIL)
## P4 — Kế hoạch dựng 2026 (CHƯA làm; chỉ khi P3 PASS hoặc MASTER quyết sau chẩn đoán)

Nguồn: Vision `futures/um` (monthly 2025-12..2026-09; daily 2026-10-01..03 cho 72 h nhìn trước nhãn; REST `fapi/v1/klines`/`fundingRate` cho ngày Vision chưa phát hành). Universe = USDT, không `_`, ∈ mapper 863 (luật §5.3). Mọi bước nặng trên Kaggle; Oracle chỉ Python nhẹ (đĩa còn ~2,3 GB ⇒ ticker 2026 KHÔNG đi qua Oracle: dùng output kernel làm `kernel_sources`, như P3).

| # | Bước | Nơi | Dung lượng | Kernel | ETA (wall) |
|---|---|---|---|---|---|
| 1 | Exporter 2026 (như `ho4-dev-x`): Vision klines → ticker 2025-12..2026-10-03 (≈ 307 ngày × ~13 MB gz ≈ 4 GB output) → Aerospike → `ExportMarketData2File` → market 2026; `ExportGateDataset` 2025-12-20→2026-10-01; Tool1 3 quý; nhãn 3 quý; funding_data Vision | Kaggle | out ≈ 5 GB | 2 (H1, Q3 có lead-in ≥ 30 ngày) nếu RAM Aerospike không đủ cho 1 kernel (đo ở P3) | 3–5 h |
| 2 | OI Vision toàn lịch sử → OI 2026 (ghép: ghim DEV ts < 2026-01-01 00:00 +07) | Kaggle | out ≈ 1,5 GB gz | 1 | ~1 h |
| 3 | p15 8 seed predict-only (model HO1 B2) → 8 pred.bin (đoạn DEV byte) | Oracle | 8 × 30 MB | 0 | 0,5 h |
| 4 | CLOSES_1H Vision 2026 → feat_v2 → pool (nhãn mới) → S1 `af706dc6` → net015 ONNX 3 fold → `x1_build_map` → 3 bins; loại symbol | Oracle (lock, ≤ 8 G) | ~1 GB tạm | 0 | 1–2 h |
| 5 | market.bin 2026 + 3 bins + 8 pred → dataset nhỏ; funding.bin dựng TRONG kernel sim (khối FUND_REBUILD_HO4) | Oracle→Kaggle | ~0,5 GB | 0 | 0,5 h |
| 6 | Parity C1/C2 seal đóng (bundle mới, `SIM_END_DATE=20251231`) | Kaggle | — | 2 | ~1 h |
| 7 | 32 kernel (b0, k24) × {b, s} × 8 seed, `SIM_END_DATE=20261001`, orchestrator ≤ 2 song song | Kaggle | — | 32 | ~60–65′/kernel ⇒ ~17 h |
| 8 | 2 scorer độc lập (commit trước khi đọc), chấm 1 lần (i) 9 tháng (ii) H1 (iii) Q3 + báo kèm HO4 vs HO26 H1 | Oracle | — | 0 | 2–3 h |

Tổng ≈ 37 kernel-run, ~1,5 ngày lịch. Symbol bị loại (liệt kê + số lệnh HO26 của chúng): (a) không có funding Vision — 37 symbol HO3 (24 lệnh H1 trong 18/48 run ho26: ARX 14, GLW 6, BMNR 2, STXX 2; b0/k24 chỉ seed 13); (b) niêm yết 2026 ngoài mapper 863/`exchange_info_pin` (HO1 B6: 41 symbol, 3 trong bins); (c) symbol 242 ngừng ingest (42, DEGO, DENT, DF, GHST, NKN, RVV, TANSSI, YALA — KDIV) KHÔNG còn bị loại vì nguồn là Vision. Số lệnh ho26 của nhóm (b)/(c) đo khi dựng (vòng sau).

## Rủi ro / giới hạn của phép đo này
- Xấp xỉ khai trước (ADDENDUM-5 §5.3): p15 lát = p15 DEV + Δ(model s42 cut20260101) vì fold model DEV mất; net015/S1 Q3 xấp xỉ Δ (f14/S1 fold 20250701 mất). Cổng N/B chỉ chấm Q4 (model gốc). Không thay đổi kết luận (P/G đã FAIL ở mức feature).
- Mép file: Tool1/nhãn DEV chia quý UTC ⇒ thước T/L bắt đầu 2025-07-01 00:00 UTC (S trừ 7 h đầu); ticker thay theo ngày UTC 07-01..12-31.
- 2 lỗi thực thi đã sửa khi kiểm toàn vẹn phát hiện (trước khi dùng số): ghi net015/market little-endian (`np.concatenate`) — sửa, chạy lại N/B/mkt; RSS stage S1 4,8 G chạy KHÔNG lock (vượt luật 4 G, không có job nặng khác lúc đó) — các bước sau dùng `ho4_locked.sh`.
- Cache tự tạo đã xoá (đĩa Oracle còn ~1,9 G): OI dựng lại, Tool1/nhãn tải về, net015/bins/market/pred (md5 lưu `chain/deleted_cache_md5.txt`; market/pred/bins còn trên Kaggle `ho4-dev-{mkt,pred,bins}`). Giữ `~/ledger/pred_ho4dev.parquet` (S1 lát).
- Kernel đã dùng (≤ 2 song song, kiểm API trước mỗi lần đẩy): `ho4-dev-x` (2 h 37′), `ho4-dev-oi` (~47′), `ho4-tk-copy`, `sim-ho4-dev-k24-s-s42` (~37′), `sim-ho4-dev-b0-s-s42` (~34′), `ho4-dev-d1` (~1 h 30′).
