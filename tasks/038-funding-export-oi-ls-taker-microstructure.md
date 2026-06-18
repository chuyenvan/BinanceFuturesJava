---
id: 038
status: REVIEW
depends_on: [037]
touches_live_process: false
writes_242_data: false
resource: kaggle
report: docs/reports/038.md
require_review: true
---

# TASK-038: Funding F4 — append OI/LS/taker + microstructure 1m (#36+)

Tiếp **append-only** sau 037 (#22-35). Thêm OI/LS/taker per-coin + microstructure 1m per-coin vào CUỐI mảng, giữ nguyên #1-35.

## CHỐT KIẾN TRÚC (bắt buộc)
1. **APPEND-ONLY**: ghép vào CUỐI `convertFeaturesToArray` của `fundingv2/ExportFeaturesForPythonTool.java` (sau `f.momentumRankCS` = #35). KHÔNG chèn giữa, KHÔNG đổi #1-35.
2. **KHÔNG đụng `FundingOnnxInferenceManager`** (model đang LIVE). Inference đổi sau khi 039 train v2 + deploy.
3. **KHÓA thứ tự #36..#N**: ghi rõ danh sách + thứ tự vào `docs/reports/038.md` cho 039/inference v2.
4. **No-leak**: mọi feature chỉ dùng dữ liệu <= t.

## Nhóm A — OI/LS/taker per-coin (đọc 5 set metrics 013 tren Aerospike 226)
Tái dùng pattern đọc metric của `ai_ml/features/export/ExportGateFeaturesGroupBCrowd.java` (TASK-018):
`DataManagerAerospikeFloatSim.getMetricMap226(OiMetricSets.<SET>.set, .bin, coin)` cho từng coin, resample lên grid mốc bằng 2-con-trỏ ts<=t + STALE_MS (coin chết ngừng đóng góp). Set: OI (sum_open_interest_value), LS_GLOBAL_ACC, LS_TOPTRADER_ACC, TAKER_VOL.
Feature (per-coin, KHÁC B6/B8 gate vốn là aggregate toàn thị trường):
- `oiDelta24h_coin`: Δ% OI coin vs floorEntry(t-24h).
- `oiZ_coin`: z-score OI hiện tại vs lịch sử coin (expanding <=t, no-leak — mẫu B7 FundingBreadth).
- `lsGlobal_coin`: long/short global accounts coin tại t.
- `lsToptrader_coin`: long/short top-trader coin tại t.
- `takerBuyRatio_coin`: taker buy/(buy+sell) coin (= `takerBuyRatioCoin` hoãn từ 037 — lấy từ TAKER_VOL, KHÔNG từ kline).

## Nhóm B — Microstructure 1m per-coin (~5, từ kline 1m coin)
Tổng hợp từ N nến 1m gần (<=t), KHÔNG nhồi nến thô. Tái dùng helper kline của extractor `FundingFeatureExtractorV2`.
- `ret_15m`: close_t/close_{t-15m} - 1.
- `rvol_15m`: std của 15 return 1m gần.
- `volumeZ_5m`: volume 5m gần / nền (vd /avg 20x5m).
- `closePosRange_15m`: (close - low15m)/(high15m - low15m).
- `wickRatio_15m`: (high - max(open,close))/(high - low) trung bình N nến gần.

## Cách làm
- Thêm field mới (CUỐI) vào `funding/FundingMarketFeatures.java`.
- Tính trong `FundingDataCollectionManager.FundingFeatureExtractorV2`: microstructure (#36-40) tính ngay từ ring kline.
- **CHỐT A2 (xem `docs/reports/038.md`):** `.bin.gz` funding (ExportFeaturesForPythonTool) = **#1..#40** — chỉ append #36..#40 (microstructure-B) vào `convertFeaturesToArray`. ⇒ **037 chạy ra 40 cột là ĐÚNG (KHÔNG phải 45).**
- **OI/LS/taker (#41..#45, nhóm A) KHÔNG vào .bin.gz** → tool RIÊNG `ExportFundingOiPerCoin` (loop-theo-coin RAM-aware, tránh OOM ~5-8GB khi nhồi vào loop-theo-phút). Output binary riêng, **MERGE ở train 039** bằng merge_asof(by=symId,on=ts,backward). Tổng feature train = 40 + 5 = 45.
- `javac --release 11 -cp "C:/Users/pc/oi-fleet/binance-java-sdk-1.2.4-shaded.jar" -d /d/claudedata/build/c038 <file sửa>` PASS.

## Validate (require_review) — theo docs/insights/TRAINING_NOTES.md
- Recompute >=3 feature mới o >=3 mốc khớp.
- No-leak: oiZ/microstructure chỉ dùng <=t (giá trị tại t không đổi khi thêm data tương lai).
- #coin OI/LS/taker active theo năm (tăng dần như 018: 2021~93 .. 2026~621).
- Phân phối (min/p1/p50/p99/max) + #null mỗi feature; null KHÔNG fill-0 (warmup -> null).
- System.exit(0) cuối main.

## Chạy
Kaggle (Aerospike 226 public) — dùng chung harness Java-on-Kaggle CCD đang dựng cho 037. Harness chưa sẵn thì CODE+compile+commit trước, RUN chờ.

## (Code / Kết quả điền)
- Thứ tự CHÍNH XÁC #36..#N (khóa cho 039/inference v2).
- #dòng x #cột .bin.gz v3, đường dẫn. Kết quả validate. commit hash.
