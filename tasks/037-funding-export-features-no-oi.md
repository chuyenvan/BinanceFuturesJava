---
id: 037
status: DOING
owner: CCD-funding
updated: 2026-06-16
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
