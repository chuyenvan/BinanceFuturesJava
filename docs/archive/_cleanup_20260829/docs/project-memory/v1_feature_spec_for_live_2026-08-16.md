# Spec 45 feature cho service feature live (step 3, 2026-08-16)

Nguồn: `ExportFeaturesForPythonTool.convertFeaturesToArray` + `ComprehensiveMarketFeatureExtractor` (sim jar). Thứ tự KHÓA — phải khớp y hệt khi tính live nếu không selector đọc sai cột.

## 40 Tool1 feature (f0..f39), theo đúng thứ tự
| idx | tên | nhóm | ghi chú tính live |
|---|---|---|---|
| 0-2 | btcMomentum1H/4H/24H | BTC | cần kline BTC |
| 3 | btcDominance | market | tổng market |
| 4 | marketBreadthStrength | market | agg toàn universe |
| 5 | rateDown15MAvg | market | agg |
| 6-8 | momentum1H/4H/24H | per-coin | `calculateReturn(sym, phút)`: 60/240/1440 |
| 9 | rsi1H | per-coin | kline |
| 10 | distFromLow24H | per-coin | kline |
| 11 | volatilityShock | per-coin | kline |
| 12-16 | basketMomentum15M/1H/24H, basketRsi14, basketVolSpike | **basket** | TB trên `getTopCoin(ts)` |
| 17 | coinFundingRate | funding | funding history |
| 18 | basketFundingAvg | basket+funding | TB funding trên basket |
| 19-25 | fundingRateAvg24H, fundingRateTrend, fundingPercentileCoin, fundingZCoin, fundingPersistence, fundingSum24h, fundingAbs | **funding (9)** | `FundingFeatureExtractorV2`, cửa sổ ≥24h |
| 26-27 | volumeZCoin, volumeTrend | per-coin | volume |
| 28-30 | distFromHigh24H, rangePosition24H, atrSqueeze | per-coin | kline |
| 31 | relStrengthBtc24H | per-coin vs BTC | |
| 32-34 | fundingRankCS, volumeZRankCS, momentumRankCS | **CS rank** | rank across universe/ts |
| 35-39 | ret15m, rvol15m, volumeZ5m, closePosRange15m, wickRatio15m | micro 5m/15m | kline mịn |

## 5 OI feature (merge_asof, ngoài 40)
`oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy` — OI ingestor (bug Infinity 3 symbol, step 2).

## Cơ chế thật (từ ComprehensiveMarketFeatureExtractor) — QUAN TRỌNG cho live parity
- **basket = `CoinRankManager.getInstance().getTopCoin(timestamp)`** (tập top-coin ĐỘNG mỗi ts), KHÔNG phải sector tĩnh. basket features = TB trên tập đó. Nếu basket rỗng → fallback về feature coin/BTCUSDT.
- Momentum windows = phút: 1H=60, 4H=240, 24H=1440. volatilityTermStructure = vol1H/vol24H.
- Funding features qua `FundingFeatureExtractorV2` (deep cache, cửa sổ 24h+).
- CS-rank (f32-34) + basket đều đi qua `CoinRankManager` (stateful).
- **Hệ quả**: feature computation ĐAN XEN `CoinRankManager` + `FundingFeatureExtractorV2` + kline cache — đều stateful. Dựng live parity **PHẢI tái dùng chính các class source này**, reimplement tay từ decompiled sẽ lệch (nhất là getTopCoin + funding cache). → **step 3 cần SOURCE, không thể chỉ từ jar.**

## Việc step 3
1. **Có source** → tái dùng ComprehensiveMarketFeatureExtractor + CoinRankManager + FundingFeatureExtractorV2 để tính 45 feature live từ Aerospike (klines+funding) + join OI → ghi format selector đọc (thay `ai_models_reg_v3`).
2. Reconcile: dump feature live tại 1 ts vs feature backtest cùng ts → phải khớp (chống lệch quan trọng nhất).
3. Song song: fix OI Infinity guard.

## BLOCKER
Source Java KHÔNG có trên Oracle/242 (chỉ jar) và không ở IdeaProjects máy dev. Cần Uni chỉ repo source. Đọc/hiểu thì decompile được; build/sửa production thì cần source + build setup.
