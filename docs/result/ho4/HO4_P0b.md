# HO4-P0b — Chẩn đoán vì sao store DEV (gate / Tool1 / nhãn) không tái lập được kể cả từ ticker DEV

Ngày 2026-10-11. Vòng CHẨN ĐOÁN: không dựng 2026, không sim cửa sổ 2026, không mở số 2026, không sửa `.java` src.
Tiền đề: HO4-P0 (ADDENDUM-5 `31e3c9e7`, kết quả `59955c48`/`82ffbbc3`/`8c3e782b`) — P3 FAIL; D1 (exporter hiện tại trên ticker DEV) khớp DEV gate 66,5% / Tool1 85,5% / nhãn 98,3%.
Mọi exporter Java chạy trên Kaggle (Aerospike CE trong kernel, jar HEAD, guard NOWRITE242); Oracle chỉ chạy so sánh Python (khoá `oracle_heavy.lock`).
Cửa sổ đo (đều ≤ 2025-12-31): gate 2025-09-30..10-16 (+07, 23 040 phút); Tool1 2025-10-01..10-16 UTC (721 647 khoá coin×15m); nhãn 2025-10-01..10-09 UTC (lookahead nằm trọn trong end-arg).
Thước: **tỉ lệ ô khớp** (ô = dòng×cột; dòng chỉ có ở 1 bên tính sai cả dòng), ô khớp ⇔ |Δ| ≤ 1e-6·max(1,|ref|) hoặc cùng NaN — như HO4-P0 (`ho4_cmp`).

## Thí nghiệm (Kaggle, cùng jar, cùng ticker DEV `wfo-ticker-2025h2`, cùng funding local)

| Kernel | Nội dung | Mục đích |
|---|---|---|
| `ho4b-det` | ingest 2025-09-01..10-31; `mkt1`,`mkt2` = ExportMarketData2File chạy 2 lần (truncate trước mỗi lần, dump set); gate `g1`,`g2` (0925→1016) + `g3` (0905→1016); Tool1 `t1`,`t2`; nhãn `l1`,`l2`; round-trip ticker | (i) bất định, phụ thuộc điểm bắt đầu |
| `ho4b-d1x` | như det nhưng BỎ 10 symbol chỉ có trong file ticker DEV, không có trong store DEV/local (DGB, FTT, GLMR, IDEX, MDT, RAD, RAY, SC, STRAX, WAVES) | (iii) universe |
| `ho4b-t1x` | như d1x + nạp NGUYÊN `market_data_object` của DEV (market.bin) thay vì tự sinh; gate `g1`, Tool1 `t1` (khởi 10-01) + `t1e` (khởi 09-15) | tách phần dư do set market (race) và do điểm khởi đầu Tool1 |
| Oracle | `git log` từ 2025-07-25 trên các lớp feature/exporter; port Python `devexport_202609` trên store local; so file ticker DEV vs Aerospike local; Q3 predict/retrain | (ii) trôi code, Q2, Q3 |

## Kết luận nhanh

- **Không có trôi code, exporter tất định.** Với input giống DEV, jar HEAD tái lập gate DEV **100%**, Tool1 **100% trong 1 bước lượng tử** (97,19% strict), nhãn **100%** khi đủ lookahead.
- Lệch D1 do: **universe input** (10 symbol settle có trong file ticker DEV nhưng không có trong store DEV) — 96,7% lệch gate, 81,4% lệch Tool1; **race `SimpleDateFormat`** trong `saveMarketDataBatch` (set `market_data_object` mất ~7% phút ngẫu nhiên) — 3,3% gate, 1,7% Tool1; **lượng tử theo chunk T1C2** — 16,8% Tool1 (ảo giác so sánh); **end-arg** — 100% lệch nhãn.
- Q2: live/DEV/exporter dùng CÙNG code feature; model đóng băng train trên feature giống live về code (khác về input: nến chưa chốt, universe, funding store). Q3: đủ model, tái sinh trùng bit.
- Race xác nhận ⇒ đề xuất fix `DataManagerAerospikeFloatSim.java:2200/2206` (ThreadLocal + pin GMT+7) và thước P3-DET (2 lần chạy byte-identical).

## Q1 — Tách nguyên nhân theo thành phần

### Bảng chuỗi đo (tỉ lệ ô khớp vs DEV; cùng cửa sổ)

| Bước | Gate 33 | Tool1 40 cột (strict 1e-6) | Nhãn |
|---|---|---|---|
| D1 (ticker DEV, exporter HEAD, store tự sinh) | 67,68% | 83,30% | 72,6% trên 10-01..10-12 (end-arg 10-12 cắt lookahead); **100%** trên 10-01..10-09 |
| (i) chạy lại cùng input: g1=g2, t1=t2, l1=l2 | 100% | 100% | 100% |
| (i) gate khởi đầu sớm hơn (g3: 09-05 vs 09-25) | 100% | — | — |
| (i) `market_data_object` run1 vs run2 | tập phút: 81 267 vs 81 201 / 87 840, chung 75 539 (lệch 5 728 + 5 662); giá trị phút chung **trùng bit 100%** | | |
| (iii) D1x = D1 bỏ 10 symbol settle chỉ-có-trong-file | **98,94%** (còn lệch duy nhất momentum1M/15M/Accel: 88,3% ô) | **96,90%** | = D1 |
| (iii)+(i) t1x = D1x + nạp nguyên set market DEV | **100,00%** | **97,19%** (ngày 0–11: 100%; 3 ngày cuối 83–92%) | — |
| Tool1 với dung sai ≈ 1 bước lượng tử T1C2 (đo: 1,01·range cột trên cửa sổ/65 535 + 1e-6) | — | **100,00%** (t1 vs DEV; cả t1e khởi 09-15 vs DEV) | — |

### Phân bổ % phần lệch D1 (điểm % ô, và tỉ trọng trong tổng lệch)

| Nguyên nhân | Gate (lệch 32,32 pp) | Tool1 (lệch 16,70 pp) | Nhãn (D1 lệch 1,7 pp ở P0) |
|---|---|---|---|
| (i) Bất định exporter (gate/Tool1/nhãn cùng input) | 0 (0%) | 0 (0%) | 0 (0%) |
| (i) Bất định **set market** (race `saveMarketDataBatch`) — DEV là 1 mẫu race khác | 1,06 pp (**3,3%**) — chỉ momentum×3 | 0,29 pp (**1,7%**) — cột #6 rateDown15MAvg | 0 |
| (ii) Trôi code (feature/exporter kể từ build DEV) | 0 (0%) | 0 (0%) | 0 (0%) |
| (iii) Input: universe (10 symbol settle có trong file ticker DEV, KHÔNG có trong store DEV) | 31,26 pp (**96,7%**) — breadth/basket/funding×3/btcDominance | 13,60 pp (**81,4%**) — basket* #13–#17, basketFundingAvg #19 | 0 |
| (iii) Input: funding / OI / CLOSES_1H | 0 (funding×3 khớp lại hoàn toàn khi universe đúng) | 0 | 0 |
| Định dạng: lượng tử int16 theo chunk 200k dòng (`Tool1ColSink`), chunk cuối khác vì t1 dừng ở 10-16 | — | 2,81 pp (**16,8%**) — sai ≤ 1 bước lượng tử | — |
| Cấu hình export: end-arg cắt lookahead 72h ở mép | — | — | 1,7 pp (**100%**) |

### Bằng chứng từng nhánh

- **(i) bất định**: exporter gate/Tool1/nhãn tất định tuyệt đối (2 lần chạy trùng 100%; gate không phụ thuộc điểm khởi đầu). Nguồn bất định DUY NHẤT là `ExportMarketData2File` → `DataManagerAerospikeFloatSim.saveMarketDataBatch`: `SimpleDateFormat` dùng chung trong `parallelStream` (**:2200/:2201/:2206**) ⇒ key phút ghép sai ⇒ 2 phút đè cùng record ⇒ mất ~7% phút, khác nhau mỗi lần chạy. Set DEV (nạp vào t1x: 85 236 record cho 09-01..10-31) cũng là 1 mẫu race. Nạp nguyên set DEV ⇒ gate 100% ⇒ **race xác nhận**.
- **(ii) trôi code**: `git log` từ 2025-07-25 (`gitlog.txt`): `ComprehensiveMarketFeatureExtractor`, `HistoryManager`, `FundingFeeManager`, `ExportMarketData2File`, `MarketFeatures` **0 commit**; `CoinRankManager` 1 commit (fab02f27, ablation env-gated default off); `ExportGateDataset` 08-11/08-21/08-24 chỉ thêm cột nhãn; Tool1/nhãn commit cuối 08-11 (trước export 08-13); `DataManagerAerospikeFloatSim` có commit sau DEV nhưng đều "default byte-identical". Thực nghiệm khép kín: exporter HEAD tái lập DEV 100% (gate) / 100% trong 1 bước lượng tử (Tool1) khi input giống ⇒ **không cần build jar cũ**.
- **(iii) input**: file ticker DEV (export 08-21/22) có 555 symbol ngày 10-10 vs Aerospike local 545; 10 symbol thừa = DGB, FTT, GLMR, IDEX, MDT, RAD, RAY, SC, STRAX, WAVES (settle/delist), cùng bộ ở 07-15; trên symbol chung OHLCV trùng 100% (783 478 / 680 835 dòng-phút); ingest round-trip md5 3/3 không mất. Port Python trên store local tái lập DEV 95–96% (2 ngày) — lệch momentum (race) + funding (port khác đường Java), không dùng port cho dựng.
- **Tool1 "phụ thuộc điểm bắt đầu"** (t1 khởi 10-01 vs t1e khởi 09-15: strict 62,4%) là **ảo giác định dạng**: T1C2 lượng tử int16 theo min/max của từng chunk 200k dòng ⇒ chunk khác ranh giới ⇒ giá trị lệch ≤ 1 bước; dung sai 1 bước ⇒ 100%. Giá trị feature float trước khi ghi KHÔNG phụ thuộc điểm bắt đầu.
- **Nhãn**: `ExportFundingLabel` không nhìn quá end-arg; DEV export end-arg quý kế tiếp nên mép cửa sổ D1 thiếu lookahead ⇒ 1,7 pp ở P0 là cấu hình, không phải dữ liệu/code.

## Q2 — Parity live: live tính feature bằng code nào? model đóng băng train trên feature giống live hay giống exporter?

| Thành phần | Code LIVE | Code DEV (store 08-08 / Tool1 08-13) | Code exporter hiện tại (jar b7c89f09) | Bằng chứng |
|---|---|---|---|---|
| 33 feature gate | `DetectEntrySignal2TradeNormal.java:294` → `ComprehensiveMarketFeatureExtractor.extractAllFeatures` (+ `HistoryManager`, `CoinRankManager`, `FundingFeeManager`); momentum×3 từ `MarketDataObject` tính inline (`:263-266`, `calRateChangeAvg`) | `ExportGateDataset.replayToCsv:188` → CÙNG extractor; momentum×3 từ set `market_data_object` (`ExportMarketData2File` → CÙNG `calMarketData`) | như DEV; `git log` từ 07-25: extractor/HistoryManager/CoinRankManager/FundingFeeManager **0 commit**; `ExportGateDataset` 08-11/08-21/08-24 chỉ THÊM cột nhãn A/B (diff -w) | parity B4: ORT(model) trên `feat_dump` live == `p15_out` (max\|d\| 4,7e-12) |
| 40 cột Tool1 (net015) | `fundingExtractor.updateMarketHistory` → `FundingOnnxInferenceManager.extractFeaturesToArray` (FundingFeatureExtractorV2) | `ExportFeaturesForPythonTool` (CÙNG FundingFeatureExtractorV2) | như DEV (Tool1/nhãn: commit cuối 08-11, trước export 08-13) | `feature_order_net015.txt` (thứ tự = đường live) |
| Khác biệt đo được live↔DEV | — | — | — | parity v4: 27/33 vượt ngưỡng cùng phút (ticker-live vs kline-đóng); FEATDIFF PASS2: hiệu ứng lên p15 ≤ 0,006 pp sau ghép regime; D1 shadow↔242 cùng code vẫn lệch breadth/basket (đọc nến khác thời điểm) |

**Ghi chú Tool1:** live đưa mảng float trực tiếp vào ONNX, còn net015 train trên Tool1 DEV đã qua lượng tử int16 theo chunk (T1C2) ⇒ lệch train↔live ≤ 1 bước (≈ range cột/64 000 với cột int16) — có thật nhưng cỡ 1e-5 tương đối, không phải khác code.

**Kết luận Q2:** model đóng băng (gate 8 seed, net015 f15, S1) được train trên feature sinh bởi **CÙNG code Java với live** (và với exporter hiện tại — code feature không trôi kể từ export DEV). Khác biệt live↔DEV là **dữ liệu đầu vào**, không phải code: (a) live tính trên nến chưa chốt (KDIV: 242 chốt giây 2–6, sai 15,7% ô từ 04-25), DEV trên kline đã đóng; (b) universe: live/DEV store KHÔNG có 10 coin settle mà file ticker DEV có (Q1); (c) funding: live đọc store 242, DEV store local (khác giá trị, F2 HO3). Rủi ro "backtest DEV không phản ánh live" vì code khác: **không có bằng chứng**; rủi ro do input khác: có, đã lượng hoá một phần (p15 ≤ 0,006 pp cùng regime; KDOSE đo liều-đáp ứng lỗi nến).

## Q3 — Kiểm kê model (chỉ tỉ lệ khớp/sha, không số 2026)

| Artifact | Còn? | Tái sinh |
|---|---|---|
| gate 8 seed cut20260101 (`~/claude_master/1003/ho1/gate/gate_s*_cut20260101p15.json`) | **còn đủ 8** | predict lại store H1 ⇒ pred.bin H1 HO26 **trùng bit 100%** cả 8 seed (260 602 dòng/seed); retrain seed 42 (thư mục tạm) ⇒ **sha model trùng** (`6a50ebb6…`), dự đoán H1 trùng bit |
| net015 ONNX f15 `7921ceaf` | còn, sha OK | predict lại fold 20260101 (Tool1+OI ghim) ⇒ `net015_2026A` **trùng bit 100%** (4 587 093 ô) |
| S1 `s1a2x1_cut20251231.json` `af706dc6` | còn, sha OK | (đã chứng minh ở HO1 G-B4b) |
⇒ Không cần retrain; model holdout tất định và tái sinh được.

## Quyết định MASTER (ghi nguyên ý, có hiệu lực cho HO4 tiếp theo)

1. **Universe 2026** = bộ lọc universe của code LIVE áp point-in-time; loại BTCDOM/USDC và symbol settle sau ngày delist; symbol thiếu mapper/funding ⇒ drop + liệt kê.
2. **CLOSES_1H** dựng từ 1m Vision.
3. **Thước P3 mới** (chốt sau chẩn đoán này): pipeline Vision chạy 2 lần phải **byte-identical** (sau khi sửa race `SimpleDateFormat` — MASTER sẽ giao fix vì Q1 xác nhận race); kline/funding giữ như P3 cũ; so sánh với DEV chỉ **BÁO CÁO**, không là cổng, trừ khi Q1 chỉ ra trôi code sửa được (Q1: KHÔNG có trôi code ⇒ giữ "chỉ báo cáo").

## Đề xuất thước P3 (để MASTER chốt trong addendum mới, TRƯỚC khi đo)

- **P3-DET (cổng):** trên Kaggle, cùng input Vision (ticker đã build + funding), chạy toàn chuỗi 2 lần độc lập (ingest → ExportMarketData2File → ExportGateDataset → Tool1 → ExportFundingLabel): md5 từng file đầu ra (ticker tháng, dump `market_data_object` sắp theo key, CSV gate, CSV Tool1, CSV nhãn) **trùng 100%**. Điều kiện tiên quyết: fix race bên dưới (trước fix, set market lệch ~7% phút giữa 2 lần chạy ⇒ P3-DET chắc chắn FAIL).
- **P3-KF (cổng, như cũ):** kline 1m Vision vs nguồn tham chiếu, funding Vision vs store — ngưỡng của ADDENDUM-5 giữ nguyên.
- **P3-DEV (chỉ báo cáo):** trên cửa sổ 2025 (≤ 12-31), sau khi áp cùng universe (bỏ 10 symbol settle chỉ-có-trong-file), báo cáo % khớp gate/Tool1/nhãn vs DEV. Kỳ vọng từ đo này: gate ≈ 98,9% (phần dư = set market race của chính DEV; 100% nếu nạp set DEV), Tool1 ≈ 96,9% strict; nhãn 100% khi end-arg phủ lookahead. **Tool1 phải so với dung sai 1 bước lượng tử T1C2** (int16: ≈ range cột của chunk/64 000; cột WIDE int32 mịn hơn) hoặc cùng ranh giới chunk (cùng ngày bắt đầu + cùng ngày kết thúc như DEV: chunk quý từ 07:00 ngày đầu quý), nếu không sẽ thấy lệch giả ~3–38%.

## Fix Java đề xuất (KHÔNG tự sửa — chờ MASTER giao)

`src/main/java/com/binance/chuyennd/aerospike/DataManagerAerospikeFloatSim.java`
- **:2200** `SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");` dùng chung cho `dataMap.entrySet().parallelStream()` **:2201**, gọi `fmt.format(...)` trong lambda **:2206** ⇒ `SimpleDateFormat` không thread-safe ⇒ key phút bị ghép sai/trùng ⇒ ghi đè/mất phút, khác nhau giữa các lần chạy.
- Sửa: thay :2200 bằng `ThreadLocal<SimpleDateFormat> tlFmt = ThreadLocal.withInitial(() -> { SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd-HHmm"); f.setTimeZone(TimeZone.getTimeZone("GMT+7")); return f; });` (đúng mẫu đã có ở **:2115** cho pred và pin TZ như đường đọc **:1059-1060**), và :2206 dùng `tlFmt.get().format(...)`. Không đổi giá trị ghi (MarketDataObject đã tất định: giá trị trên phút chung trùng bit 100%).
- Phụ (cùng file, an toàn hoá): **:2274** `getMarketDataAtTime` tạo `SimpleDateFormat` không pin TZ ⇒ nên `setTimeZone("GMT+7")` để key đọc không phụ thuộc `-Duser.timezone` (hiện kernel/live đều chạy `Asia/Ho_Chi_Minh` nên chưa gây lệch).
- Caller bị ảnh hưởng: `ExportMarketData2File.java:158`, `MarketObjectGapRepairTool.java:67`.
- Kiểm thử chấp nhận: chạy `mkt` 2 lần ⇒ số phút = 87 840/87 840 (trừ phút thật sự thiếu nến) và md5 dump trùng; gate/Tool1 2 lần trùng byte.
- Cơ chế khớp với số đo: đường đọc `scanAll` lấy timestamp từ bin `time` chứ không từ key ⇒ key ghép sai làm 2 phút đè lên cùng 1 record ⇒ **mất phút** (không bao giờ sai giá trị) — đúng như quan sát: run1 81 267 / run2 81 201 phút trên 87 840, giá trị phút chung trùng bit 100%.

## Rủi ro

1. **10 symbol settle chỉ có trong file ticker DEV** (export 08-21/22) nhưng KHÔNG có trong store dùng để export gate DEV (08-08) lẫn Aerospike local: sim DEV (đọc file ticker) thấy chúng, feature gate/Tool1 DEV thì không ⇒ train/sim DEV có lệch universe nội bộ; quyết định MASTER #1 (drop sau delist) làm 2026 nhất quán hơn DEV — chênh hành vi so với DEV là có chủ đích, phải ghi nhận khi so 2026 vs DEV.
2. **Set market của chính DEV là sản phẩm race** (thiếu ~7% phút, ngẫu nhiên): model đóng băng đã train trên momentum×3 có "lỗ" ngẫu nhiên; sau fix, 2026 sẽ có momentum đầy đủ hơn DEV ⇒ phân phối momentum×3 lệch nhẹ (≈ 10–12% dòng gate chứa giá trị khác). Cần báo cáo, không phải lỗi.
3. **Trạng thái funding store**: funding×3 (gate) và cột funding Tool1 phụ thuộc store funding + basket; D1x khớp lại hoàn toàn khi universe đúng, nhưng port Python vẫn lệch funding ⇒ mọi dựng 2026 phải dùng đúng đường Java + funding Vision, không dùng port.
4. **Live ≠ backtest do input** (nến chưa chốt, thời điểm đọc): không thuộc phạm vi P3, đã có KDIV/KDOSE lượng hoá.
5. Kết luận dựa trên 1 cửa sổ 16 ngày (2025-09/10) + 2 ngày port (07-15, 10-10); các cơ chế (race, universe) là cấu trúc, không theo mùa, nhưng chưa quét toàn 2025.
6. **So Tool1 phải tính lượng tử T1C2**: mọi phép so Tool1 với dung sai 1e-6 giữa 2 file khác ranh giới chunk sẽ báo lệch giả (đến 38%); P3/so DEV phải dùng dung sai 1 bước hoặc cùng quy ước chunk quý.
7. Rút gọn: không chạy lại nhánh nhãn trong t1x (nhãn đã 100% ở det/d1x khi đủ lookahead); không build jar cũ (thực nghiệm khép kín đã loại trôi code).

## Sản phẩm

- `docs/result/ho4/HO4_P0b.md` (file này), `docs/result/ho4/HO4_P0b.json` (gom detcmp, detcmp_lab, t1xcmp, t1q, t1path, portcmp, tkas, q3, gitlog).
- Script: `research/analysis/ho4b_*.py` (+ `ho4b_gitlog.sh`, `ho4b_t1x_auto.sh`), `research/analysis/ho4_exp_kernel.py` (thêm `truncate_market`, `post market/tk_rt`, `drop_syms`, `market_from_dev`).
- Kernel Kaggle: `ho4b-det`, `ho4b-d1x`, `ho4b-t1x` (jar sha `b7c89f09…`, NOWRITE242); dữ liệu đầu ra không push.
