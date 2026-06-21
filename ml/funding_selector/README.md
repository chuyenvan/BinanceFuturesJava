# Funding Selector (TASK-039)

Selector lọc entry DCA: XGBoost dự đoán P(giá chạm +6% trong horizon H). Mục tiêu = +6% CHỐT.

## Data (3 Kaggle dataset, user chuyendinh)
- `chuyendinh/funding-tool1-features` — 66 file `ff_YYYYMM.bin`, 40 feature Tool1, record `>q h 40f`, cadence 1m (train lọc về grid 15m).
- `chuyendinh/funding-oi-percoin` — `oi_percoin_full.bin` (5 feature OI #41–45, record `>q h 5f`) + `symbol_map.csv`.
- `chuyendinh/funding-label-full` — `funding_label.csv` (47.86M dòng, 27 cột, H={4h,12h,24h,72h}, alt-only, build từ ExportFundingLabel `-Xmx11g`).

LƯU Ý Kaggle: tự giải nén `.gz` → file `.bin`; mount ở `/kaggle/input/datasets/<user>/<slug>/` (KHÔNG phải `/kaggle/input/<slug>/`). Header dùng glob đệ quy `/kaggle/input/**/...` để khỏi phụ thuộc path.

## Chạy
1. Header: `kaggle/kernel_header_per_horizon.py` (set HORIZONS + resolve path đệ quy) nối với `train_funding_selector.py`.
2. Per-horizon (song song, nhanh): 4 kernel `funding-sel-{4h,12h,24h,72h}`, mỗi kernel HORIZONS=1.
3. Hoặc 1 kernel HORIZONS="4h,12h,24h,72h" (tuần tự, chậm hơn).
4. Output `/kaggle/working/metrics_<H>.json`.

train env: TOOL1_GLOB, OI_FILE, LABEL_CSV, MAP_CSV, HORIZONS, OUT_DIR, SMOKE(=1 chỉ load+merge+shape, không train).

## Kết quả v1 (OOS 12 tháng cuối, top-decile) — results_v1/
| H | base_rate | LIFT | hit top10% | rankIC | baseline(1 feat) | ML hơn | PASS |
|---|---|---|---|---|---|---|---|
| 4h | 20.7% | 2.58 | 53.4% | 0.353 | 2.468 (f10=distFromLow24H) | +4.5% | ✓ |
| 12h | 36.3% | 1.82 | 66.2% | 0.327 | 1.802 (f10) | +1.2% | ✓ |
| 24h | 47.2% | 1.54 | 72.9% | 0.286 | 1.523 (f10) | +1.3% | ✓ |
| 72h | 63.3% | 1.26 | 79.6% | 0.198 | 1.246 (f28=distFromHigh24H) | +1.0% | ✓ |

Acceptance pre-register (LIFT≥1.20, N≥100, z≥2, |t-IC|≥2, beat baseline): cả 4 PASS.

## CẢNH BÁO (đọc trước khi tin/triển khai)
- **Margin mỏng**: ML chỉ hơn 1 feature đơn (f10=distFromLow24H) 1–4.5%. Chỉ 4h (+4.5%) là ML thêm giá trị rõ; 12/24/72h gần như rule-f10 là đủ.
- **z/t_IC khổng lồ là ảo giác do N lớn** (~105k) — độ mạnh thật xem rankIC.
- **f36=rvol15m thống trị importance 26–36%** — đã kiểm: dùng 15 nến 1m ≤t (`historyManager.getVolatility(symbol,15)`), KHÔNG leak. Bản chất model học "coin đang biến động mạnh → dễ chạm 6%".
- **Luật chốt thật = giữ tới khi +6% hoặc coin delist** → maxDD/tụt-sâu KHÔNG đổi thắng/thua → không đưa vào nhãn. Rủi ro thật là delist, nhưng dữ liệu coin-chết chưa đủ tin để mô hình hóa → xử bằng rule lọc thanh khoản, không bằng ML.
- **CHƯA validate ổn định theo regime** (bull/bear) và **chưa retrain lặp lại** — version chỉ đáng tin sau 2 bước này.

## Map feature index (0-based, train dùng f0..f39 + oi_*)
f0–f20 = #1–#21 (btc/momentum/rsi/funding cơ bản); f10=distFromLow24H. f21–25 funding sâu. f26–27 volume. f28–31 cấu trúc giá; f28=distFromHigh24H. f32–34 cross-sectional rank. f35–39 microstructure 1m: f35=ret15m, **f36=rvol15m**, f37=volumeZ5m, f38=closePosRange15m, f39=wickRatio15m. oi_delta24h/oi_z/ls_global/ls_toptrader/taker_buy = #41–45 (merge ở train).
