# Kế hoạch: bảng grid × threshold + audit lệnh (2026-08-12, Uni giao)

## Mục tiêu bảng 2 chiều (grid predict × NET_THR), mỗi ô = total + độ đều
Metric mỗi ô: total win4-13, Sharpe/window (mean/std), t-stat (mean/(std/√10)), %win, maxDD, quý lỗ nặng nhất, top2/gross.

| grid \ thr | 0.008 | 0.015 |
|---|---|---|
| 15m | ✅ +8,176 (Sharpe1.15 t3.65 10/10 DD0) | ⏳ |
| 5m | ⏳ đang chạy | ⏳ |
| 3m | ⏳ queued | ⏳ |
| 1m | ✅ +9,183 (Sharpe0.45 t1.44 9/10 DD-3715) | ⏳ |

Tất cả trên CÙNG 10 window OOS (2023Q1-2025Q2, fold 0-9) để so công bằng. (2 window 2025H2 thiếu do OOM decode quý 1m to — gác.)

## Chiều "train grid" (điểm mới Uni nêu: có features 1m kín rồi)
- Hiện tại: train luôn ở 15m (PRED_TOOL1_GLOB tách), predict ở grid mịn (predict-only, model y hệt).
- Thử TRAIN NATIVE ở lưới mịn tùy OOM:
  - 15m train: chắc chắn OK (đang dùng).
  - 5m / 3m train: THỬ (build_features_memmap đọc Tool1 ~3-5x 15m; có thể vừa 30GB). Nếu OOM -> fallback train-15m.
  - 1m train: gần như chắc OOM (lý do ban đầu tách train-15m). Chỉ thử nếu 3m/5m ổn và còn muốn.
  - Đánh dấu rõ trong bảng: ô nào "train-native@grid" vs "train-15m→predict@grid".
- Lưu ý: train-native đổi cả mật độ mẫu train + nhãn theo grid -> model KHÁC (không còn "edge y hệt" như predict-only). Đây là biến mới, tách riêng để so.

## Audit lệnh (đối chiếu dữ liệu vào/ra)
- Dump random ~10-20 lệnh (entry ts/price + exit ts/price + symbol) từ sim của 1 run (vd 15m@0.008).
- Đối chiếu giá tại entry/exit ts với: (a) Binance API ticker (fapi klines 1m), (b) ticker trong Aerospike (raw market data ns=test trên Oracle).
- Mục tiêu: xác nhận entry/exit khớp giá thật, không lệch/nhầm — tính khách quan.

## Sequencing (tránh tranh CPU, Kaggle CPU limit 5)
1. Xong đường cong 0.008: 5m (đang chạy) -> 3m -> fanout từng cái.
2. Rồi threshold 0.015: cần model 15m@0.015 (train-save GPU như Stage A cho 0.008) -> predict 1m/3m/5m/15m -> fanout.
3. Thử train-native 5m/3m (đo OOM).
4. Audit lệnh (độc lập, chạy bất cứ lúc nào có 1 run sim + Aerospike/Binance).

## Trạng thái verdict 0.008 (đã có)
1m total cao hơn 15m +12% NHƯNG kém đều (t1.44 vs 3.65, maxDD -3715 vs 0). Theo risk-adjusted: 15m > 1m. Chờ 5m/3m để thấy điểm ngọt.
