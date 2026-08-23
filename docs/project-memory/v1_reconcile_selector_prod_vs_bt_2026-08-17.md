# Reconcile selector PROD (live) vs BT (recompute) — 2026-08-17

Chạy `ProductionVsBacktestFundingComparator` trên Oracle (RAM 21g), đọc Aerospike-242 (port 3222 open), so
dump live thật (`storage/data/predictionSymbol/20260817/*.features`) vs recompute từ Aerospike cùng timestamp
bằng cùng `FundingFeatureExtractorV2` + cùng model `Funding_Classifier_Final.onnx`. ~10 mẫu phút.

## KẾT LUẬN: live selector KHÔNG khớp backtest. Có 2 root cause thật.

### Root cause 1 (NGHIÊM TRỌNG): 8/45 feature = NaN trong live
Cả PROD lẫn BT đều NaN, nhất quán (142 lần/feature):
- **5 OI (#41-45)**: `oiDelta24hCoin, oiZCoin, lsGlobalCoin, lsToptraderCoin, takerBuyRatioCoin`.
- **3 cross-sectional rank (#33-35)**: `fundingRankCS, volumeZRankCS, momentumRankCS`.

WFO TRAIN có các feature này (OI merge_asof từ `ExportFundingOiPerCoin`; CS rank từ full cross-section).
Live feed NaN chỗ training có giá trị → XGBoost coi là missing → **lệch hệ thống 8 feature**. Dump live NaN =
bằng chứng trực tiếp live không tính được (OI Aerospike sets chưa chảy vào funding extractor, và/hoặc basket
CS chưa đủ để rank). Đây là lỗi wiring feature live, ưu tiên số 1.

### Root cause 2: z-score/rolling features lệch nặng (warmup/state)
- `volumeZCoin` lệch 150-195%, **đảo dấu** (PROD +0.34 vs BT -0.35...). z-score phụ thuộc mean/std cửa sổ →
  live HistoryManager state liên tục vs recompute fresh 1500′ khác baseline hoàn toàn.
- `volumeTrend, basketMomentum15M/24H, distFromLow24H, rangePosition24H, closePosRange15m` lệch 15-40%.

### Net: selector predict lệch lớn
PROD vs BT (P(no-pump)): BNC 80%, MINIMAX 83%, SOXS 57%, US 46%, TUT 46%, AKE 39%, ACE(2 mẫu) 2-39%.
Nhiều coin 20-45%. ⇒ ranking coin live ≠ backtest → edge backtest KHÔNG được tái tạo trung thực.

## Ý nghĩa
- 2 lần swap model (selector + gate) là đúng và cần, NHƯNG chưa đủ: **feature pipeline live lệch** làm input
  của model sai → output sai dù model đúng.
- Ưu tiên fix: (1) OI #41-45 + CS rank #33-35 NaN (wiring), (2) warmup-depth/state cho z-score features.
- Cần chạy lại reconcile sau fix để xác nhận về ~0%.

## Caveat
- BT (recompute fresh 1500′) xấp xỉ export/train nhưng không 100% (export tool có thể warmup khác) → phần z-score
  có thể một phần là harness artifact; nhưng **NaN OI/CS là lỗi live rõ ràng** (dump live NaN thật).
- Harness: jar 15m build đẩy lên Oracle `~/reconcile_v1.jar`; work dir `~/reconcile_v1_work` (config 242 + 12 dump + model).
