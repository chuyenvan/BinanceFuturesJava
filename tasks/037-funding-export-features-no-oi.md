---
id: 037
status: DOING
owner: CCD-funding
updated: 2026-06-17
depends_on: [036]
touches_live_process: false
writes_242_data: false
resource: kaggle
checkpoint: false
max_retry: 2
report: docs/reports/037.md
require_review: true
---

# TASK-037: Funding F3 — export feature funding KHÔNG cần OI (per-coin sâu + volume + cấu trúc giá + cross-sectional)

- **status:** TODO. `depends_on: [036]` (đã xong: đường export THẬT + tên feature sạch). **Độc lập 013** (KHÔNG dùng OI) → chạy song song nhánh gate.
- **Nền:** ADR-0011 §5.3 (THÊM, phần không-OI) + cross-sectional. Đọc `docs/reports/036.md` trước.

## CHỐT KIẾN TRÚC với user (2026-06-16) — BẮT BUỘC tuân
1. **APPEND-ONLY.** Feature mới ghép vào **CUỐI** mảng, **giữ nguyên thứ tự #1–21 hiện có**. KHÔNG chèn giữa, KHÔNG đổi 21 feature cũ.
2. **Export ra `.bin.gz` PHIÊN BẢN MỚI** (thư mục/tên riêng, vd `features_export_python_v3/`), **KHÔNG đè** data model cũ.
3. **TUYỆT ĐỐI KHÔNG đụng `FundingOnnxInferenceManager`** — model 21-feature đang chạy LIVE. Inference chỉ đổi khi deploy model v2 (sau 039), là task riêng. Sửa inference bây giờ = vỡ live.
4. **Cross-sectional tính TRONG export Java** (2-pass mỗi mốc), feature sẵn trong `.bin.gz`.
5. **KHÓA thứ tự feature mới**: ghi rõ danh sách + thứ tự vào report 037 — 039 train + inference v2 phải khớp đúng thứ tự này.

## Đường sửa (xác định ở 036)
- Export: `ai_ml/features/export/fundingv2/ExportFeaturesForPythonTool.java` (đường THẬT).
- Extractor stateful: `FundingDataCollectionManager.FundingFeatureExtractorV2` (`updateMarketHistory` + `extractFeatures`). Có sẵn: `getRsi14`, `getSumVolume(sym,n)`, `getAverageVolume(sym,n)`, `calculateDistFromLow24H`, `calculateVolatilityShock`, cached BTC/basket.
- Field: `funding/FundingMarketFeatures.java` (thêm field MỚI ở CUỐI).

## Feature THÊM (~16, non-OI) — tên + công thức + look-ahead
**A. Funding sâu per-coin** (cần lịch sử funding RIÊNG mỗi coin — thêm vào extractor stateful, append theo thời gian, CHỈ dùng ≤t):
- `fundingPercentileCoin`: percentile của `coinFundingRate` hiện tại trong lịch sử coin (**expanding ≤t**, no-leak — mẫu B7 FundingBreadth expanding-histogram ở `ExportGateFeaturesGroupB`).
- `fundingZCoin`: (coinFundingRate − mean_lichsu) / std_lichsu (expanding ≤t).
- `fundingPersistence`: số kỳ funding liên tiếp CÙNG DẤU (run-length, tính lúc cập nhật).
- `fundingSum24h`: tổng funding các kỳ trong 24h gần (bắt "nuôi shorter").
- `fundingAbs`: |coinFundingRate|.
**B. Volume per-coin** (đã có getSumVolume/getAverageVolume):
- `volumeZCoin`: cur/avgN (vd N=20) hoặc (cur−avg)/std.
- `volumeTrend`: volume gần / volume xa (slope đơn giản).
- `takerBuyRatioCoin`: nếu kline có takerBuyVolume → buy/(total); KHÔNG có thì BỎ, để 038 (taker từ metrics). Ghi rõ trong report có/không.
**C. Cấu trúc giá per-coin** (từ kline ≤t):
- `distFromHigh24H`: đối xứng `distFromLow24H` (đã có hàm mẫu).
- `rangePosition24H`: (close − low24h)/(high24h − low24h).
- `atrSqueeze`: ATR_ngắn / ATR_dài (<1 = nén, pre-breakout).
- `relStrengthBtc24H`: return_coin_24h − return_btc_24h.
**D. Cross-sectional (2-PASS mỗi mốc — so coin CÙNG mốc, chỉ coin có data tại t)**:
- `fundingRankCS`: rank-percentile của coinFundingRate trong các coin cùng mốc.
- `volumeZRankCS`: rank-percentile volumeZCoin cross-coin.
- `momentumRankCS`: rank-percentile momentum (return 24h) cross-coin.
**GIỮ market-context cũ** (btcMom, breadth, basket-*, rateDown*) — tỉa sau bằng importance, KHÔNG bỏ tay (user §5.3).

## Cách làm
- **Per-coin (A/B/C):** mở rộng `FundingFeatureExtractorV2`: thêm state lịch sử funding/giá per-coin (Map<symbol, deque/accumulator>), cập nhật trong `updateMarketHistory`/`extractFeatures`; tính expanding no-leak. Thêm field mới vào `FundingMarketFeatures` (cuối). Stateful liên tục KHÔNG reset (như hiện tại).
- **Cross-sectional (D):** đổi vòng lặp per-minute trong `ExportFeaturesForPythonTool`: **PASS 1** tính per-coin raw cho TẤT CẢ coin tại mốc t (gom List); **PASS 2** rank/z cross-coin từ List đó rồi set vào features; ghi batch. Chỉ coin có ticker hợp lệ tại t (không tương lai, không coin khác mốc).
- **convertFeaturesToArray** (trong ExportFeaturesForPythonTool): APPEND feature mới SAU `fundingRateTrend` (#21). Thứ tự #1–21 giữ y nguyên.
- Ghi `.bin.gz` **thư mục mới** (vd `features_export_python_v3/`), format {long ts, short id, float[N]} (N = 21 + số feature mới). Từ 2021, warmup 48h.
- Chạy **Kaggle** (đọc Aerospike 226 public). KHÔNG OI/LS (để 038).

## Validate (require_review)
- **Recompute** ≥3 feature ở ≥3 mốc bằng tay khớp (vd fundingPercentileCoin, volumeZCoin, distFromHigh24H).
- **KHÔNG look-ahead**: percentile/z/persistence/sum dùng CHỈ dữ liệu ≤t (kiểm bằng cách so giá trị tại t không đổi khi thêm data tương lai); cross-sectional chỉ coin cùng mốc.
- **Cross-sectional đúng #coin/mốc**: in #coin tham gia rank theo vài mốc (phải khớp #coin có ticker tại mốc đó; tăng dần theo năm như 018: 2021~93 … 2026~621).
- **#dòng/coverage** hợp lý so lifecycle 010 (coin sống theo thời gian); null không fill-0 (warmup → null).
- In phân phối (min/p1/p50/p99/max) + #null mỗi feature mới (bắt outlier coin mới list).
- System.exit(0) cuối main (tránh treo JVM — bài học 015).

## (Code / Kết quả điền)

### CODE DONE + compile PASS (2026-06-16, CCD-funding) — chi tiết: `docs/reports/037.md`
- **14 feature mới** (taker BỎ → 038 vì KlineObjectSimple không có takerBuyVolume). N = 21 + 14 = **35 float/record**.
- **Thứ tự KHÓA #22..#35:** fundingPercentileCoin, fundingZCoin, fundingPersistence, fundingSum24h, fundingAbs, volumeZCoin, volumeTrend, distFromHigh24H, rangePosition24H, atrSqueeze, relStrengthBtc24H, fundingRankCS, volumeZRankCS, momentumRankCS. (#1..#21 GIỮ NGUYÊN — append-only.)
- File sửa: `FundingMarketFeatures` (+14 field cuối), `FundingDataCollectionManager.FundingFeatureExtractorV2` (computeFundingDeep+cache settlementKey / computeVolumeStructure / computePriceStructure), `HistoryManager` (+getHigh24H/+getVolumeZScore), `FundingFeeManager` (+getFundingHistory), `fundingv2/ExportFeaturesForPythonTool` (outputDir v3 + 2-PASS cross-sectional + convertFeaturesToArray append). `mvn -o compile` PASS.
- KHÔNG đụng `FundingOnnxInferenceManager` (model 21-feat LIVE). Output `features_export_python_v3/` (KHÔNG đè cũ).

### JOB ĐANG CHẠY (handoff — CCD khác tiếp quản được)
- **Kiến trúc run (user chốt 2026-06-16):** giữ per-minute × all-coin → **CHIA NĂM**, mỗi năm 1 kernel Kaggle (per-minute 5 năm ~40-50GB không vừa /kaggle/working ~20GB). main nhận `args[0]=start args[1]=end` (yyyyMMdd).
- **Jar:** `chuyendinh/java-run-lc` (dataset) đã update jar sanitized build từ commit `8bdd2d1` (35 cột). Stage dev: `C:\Users\pc\java-run-lc-stage`.
- **Kernel mẫu:** `C:\Users\pc\ff37-2021\` (kernel-metadata + ff37.py). Script: tìm jar+config → copy config+live_set → `java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx16g -cp jar MAIN_CLASS <start> <end>` → **validate numpy ngay trong kernel** (output quá lớn không tải về: đếm #record, #null + phân phối p1/p50/p99 mỗi feature, cross-sectional #coin/mốc). MAIN_CLASS=`...fundingv2.ExportFeaturesForPythonTool`.
- **PILOT đang chạy:** kernel slug **`chuyendinh/ff37-2021`** (năm 2021 — nhẹ nhất, validate code trên Kaggle + đo size năm thật). Output `/kaggle/working/features_export_python_v3/*.bin.gz`. Check: `kaggle kernels status chuyendinh/ff37-2021`; log: `kaggle kernels output chuyendinh/ff37-2021 -p <dir>`.
- **BƯỚC TIẾP sau pilot OK:** clone kernel cho **2022/2023/2024/2025/2026** (đổi START/END trong ff37.py + id). ⚠️ năm nhiều coin (2024-2026) có thể >20GB/năm → nếu pilot cho size lớn thì CHIA NỬA NĂM. Mỗi kernel tự validate. Output để LẠI Kaggle cho 039 chain (`kernel_sources`), KHÔNG tải về (BẪY 3).
- **Khi tất cả năm OK:** điền report 037 (#dòng tổng × 35, phân phối, CS #coin/mốc tăng dần, #null), set REVIEW + commit hash.

### ▶ RESUME (2026-06-16, sau khi Claude Desktop chốt va-chạm + fix perf) — CCD CHẠY TIẾP ĐƯỢC

**1. SỐ CỘT CHỐT — hết va chạm 037↔038:** `.bin.gz` = **40 cột** (#1-21 live + #22-35 funding-deep + #36-40 microstructure-B). OI/LS/taker #41-45 = **TOOL RIÊNG**, KHÔNG nằm trong .bin.gz (quyết định A2 — tránh OOM). ⇒ pilot 35 cột (`chuyendinh/ff37-2021`) **bỏ**, chạy lại 40 cột. Chi tiết: `tasks/038` + `docs/reports/038.md`.

**2. PERF — ĐÃ FIX (commit kèm):** thêm `HistoryManager.getLowHigh24H` (1 quét trả `[low,high]`); `extractFeatures` gọi 1 lần, dùng chung cho distFromLow24H (#11) + distFromHigh24H (#29) + rangePosition24H (#30). Từ **3 lần quét 1440-nến/record → 1**. Microstructure #36-40 chỉ quét 15 nến (nhẹ). `javac --release 11` PASS. ⇒ giảm rủi ro cutoff 12h ở năm nặng.

**3. REBUILD JAR (CCD) từ HEAD** — gồm 037 + 038 (microstructure + tool OI) + perf-fix. Jar cũ commit `8bdd2d1` (35 cột) **LỖI THỜI**, phải rebuild → cập nhật dataset `chuyendinh/java-run-lc`.

**4. CHẠY 2 TOOL trên Kaggle (chia năm qua args, hạ tầng cũ tái dùng):**
- **Tool 1 — feature .bin.gz (40 cột):** MAIN=`com.binance.chuyennd.ai_ml.features.export.fundingv2.ExportFeaturesForPythonTool`, args `<start> <end>` (yyyyMMdd). Output `features_export_python_v3/*.bin.gz`. Record = 8(ts)+2(id)+40×4 = **170 byte** → validate `(filesize/170)` = #record; #float = `(recordbytes-10)/4` = 40.
- **Tool 2 — OI per-coin (5 cột):** MAIN=`com.binance.chuyennd.ai_ml.features.export.fundingv2.ExportFundingOiPerCoin`, args `<start> <end> symfile=/tmp/oisyms.txt` (universe GỒM coin chết). Output `features_oi_percoin_v1/oi_percoin_<start>_<end>.bin.gz`. Record = 8+2+5×4 = **30 byte**.
- Hai tool cùng key **(ts, symId)** → train 039 `merge_asof(by=symId, on=ts, direction=backward)` → 45 feature. Tool 2 mốc 5m, Tool 1 mốc 1m: asof backward gắn OI gần nhất ≤t (no-leak).

**5. VALIDATE trong kernel (numpy, output KHÔNG tải về — BẪY 3):**
- Tool 1: #record, #null + p1/p50/p99 mỗi feature; cross-sectional #coin/mốc tăng dần (2021~93 .. 2026~621); #36-40 phân phối hợp lý (ret15m quanh 0, closePosRange15m∈[0,1], wickRatio15m∈[0,1]).
- Tool 2: #coin có OI/năm (tăng dần, survivorship); null-count 5 cột (`oiDelta24h,oiZ,lsGlobal,lsToptrader,takerBuyRatio`); oiZ phân bố quanh 0, takerBuyRatio∈[0,1].
- Output để LẠI Kaggle cho 039 chain (`kernel_sources`).

**6. NĂM NẶNG (2024-26):** nếu >20GB/năm → chia nửa năm. Perf-fix đã giảm thời gian/record.

**7. Khi tất cả năm OK:** điền report 037 + 038 (#dòng tổng, phân phối, #coin/mốc, #null), set REVIEW + commit hash.

### ▶▶ LAUNCHED 2026-06-17 (CCD-funding) — JAR REBUILT + PILOT 40-CỘT ĐANG CHẠY

**Jar rebuild từ HEAD `7bcd6d5`** (Tool1 40-cột + Tool2 OI + perf-fix getLowHigh24H). Đã verify 2 MAIN class trong shaded jar (build 06:00 17/06). Dataset `chuyendinh/java-run-lc` ĐÃ push version mới (jar + `DumpSymbolMapper.class` + config + live_set).

**⚠️ SỬA UNIVERSE Tool 2 (survivorship):** `/tmp/oisyms.txt` tĩnh (622 coin) là universe ĐANG-NIÊM-YẾT — THIẾU hầu hết coin chết backfill task-005 (LUNA/FTT/RAY/SRM/WAVES/DODO/AUDIO/ANC/BTS/SC/AKRO/HNT/BTCST/COCOS/TOMO). Dùng nó cho Tool 2 = **survivorship bias** (vi phạm luật 7 + sai yêu cầu 038 "GỒM coin chết"). ⇒ Kernel B0 chạy `DumpSymbolMapper` sinh universe ĐẦY ĐỦ từ symbol mapper 226 (map bền mọi coin từng có id, KHỚP universe data-driven của Tool 1) → `/tmp/oisyms.txt` trước khi chạy Tool 2. (Helper precompile sẵn trong dataset, kernel chỉ cần `java`.) DumpSymbolMapper LOG `mapper=N usdt-perp=M` — nếu M≈622 thì mapper KHÔNG có coin chết (vấn đề tầng data, ngoài 037); nếu M>622 thì đã gồm coin chết → đúng.

**Kernel mẫu mới:** `C:\Users\pc\ff40-2021\` (`ff40.py` + kernel-metadata). 1 kernel/năm chạy TUẦN TỰ: B0 dump mapper → B1 Tool1 (40 cột) → B2 Tool2 (OI) → validate cả 2 bằng numpy (#record, #null + p1/p50/p99 mỗi cột, cross-sectional #coin/mốc, #coin distinct cho OI). args START/END sửa trong `ff40.py`.

**PILOT đang chạy:** kernel slug **`chuyendinh/ff40-2021`** (năm 2021, START=20210101 END=20220101). Output `/kaggle/working/features_export_python_v3/*.bin.gz` (Tool1) + `features_oi_percoin_v1/*.bin.gz` (Tool2). Check: `kaggle kernels status chuyendinh/ff40-2021`; log validate: `kaggle kernels output chuyendinh/ff40-2021 -p <dir>`. **Kernel cũ 35-cột `ff37-2021` BỎ** (đã COMPLETE, không zombie).

**BƯỚC TIẾP sau pilot 2021 OK:** clone `ff40-2021` → `ff40-2022..2026` (đổi START/END + id trong cả ff40.py lẫn kernel-metadata.json), push + run. ⚠️ Năm nặng 2024-2026 (~600 coin) có thể >20GB Tool1/năm → nếu pilot cho size lớn thì CHIA NỬA NĂM. Output để LẠI Kaggle cho 039 (`kernel_sources`), KHÔNG tải về (BẪY 3).

### ✅ PILOT 2021 VALIDATE PASS (2026-06-17) — `chuyendinh/ff40-2021` COMPLETE
- **Universe mapper = 781 symbol (780 USDT-perp)** → GỒM coin chết (vs oisyms tĩnh 622, thiếu ~158). Survivorship FIX xác nhận đúng.
- **Tool1 (40 cột):** 57,625,738 record | 4.69GB | rec=170B N=40 ✓ format. CS #coin/mốc tăng: 78→103→112→123→131.
- **Tool2 (OI 5 cột):** 1,286,316 record | rec=30B ✓ | 137/780 coin có OI (OI sử ~2021-12, hợp lý). null-count=[39627,493,55515,55515,55514].
- **Phân phối SANE:** bounded ∈[0,1] đúng biên (percentile/rank/rangePos/closePosRange/wickRatio/takerBuyRatio); z-score centered p50≈0 (fundZCoin/oiZ); outlier coin-mới (volZCoin 3147, oiDelta 50x) đúng cảnh báo; không cột toàn-NaN; null cao chỉ ở expanding-warmup → nhất quán no-leak. `System.exit(0)` OK (COMPLETE, không treo).

### 🚀 FAN-OUT các năm (2026-06-17) — 8 kernel, mỗi năm chạy cả 2 tool + validate
Kaggle giới hạn **5 CPU session đồng thời**. Ma trận (id | START | END exclusive | size kỳ vọng):
| kernel | START | END | ghi chú |
|---|---|---|---|
| ff40-2021 | 20210101 | 20220101 | ✅ DONE 4.69GB |
| ff40-2022 | 20220101 | 20230101 | RUNNING |
| ff40-2023 | 20230101 | 20240101 | RUNNING |
| ff40-2024h1 | 20240101 | 20240701 | RUNNING (chia nửa: năm nặng >20GB) |
| ff40-2024h2 | 20240701 | 20250101 | RUNNING |
| ff40-2025h1 | 20250101 | 20250701 | RUNNING |
| ff40-2025h2 | 20250701 | 20260101 | ⏳ PENDING (chờ slot, orchestrator nền tự push) |
| ff40-2026 | 20260101 | 20260617 | ⏳ PENDING (partial year tới hôm nay) |
- Mỗi kernel: dir `C:\Users\pc\<slug>\` (ff40.py + kernel-metadata). Check: `kaggle kernels status chuyendinh/<slug>`. Log validate (KHÔNG tải .bin.gz): `kaggle kernels output chuyendinh/<slug> -p <dir> --file-pattern '.*\.log'` rồi parse `<slug>.log` (JSON stdout).
- Output để LẠI Kaggle cho 039 (`kernel_sources`), KHÔNG tải về (BẪY 3).
- **CCD tiếp quản:** nếu kernel nào ERROR/treo → đọc log, sửa, push lại. Khi cả 8 COMPLETE + validate PASS → gộp số liệu vào report 037+038, set REVIEW + commit.

**Khi tất cả năm OK:** điền report 037 + 038 (#dòng tổng × 40 / × 5, phân phối, CS #coin/mốc tăng dần, #null, mapper-size=781), set REVIEW + commit hash.

### ⏸ (lịch sử) PAUSED 2026-06-16 — đã giải quyết ở mục RESUME trên
- Va chạm 037↔038 (35 vs 40 cột): CHỐT 40 cột + OI tool riêng (mục 1).
- PERF 3-lần-quét: ĐÃ FIX getLowHigh24H (mục 2).
- Rebuild jar: mục 3.

