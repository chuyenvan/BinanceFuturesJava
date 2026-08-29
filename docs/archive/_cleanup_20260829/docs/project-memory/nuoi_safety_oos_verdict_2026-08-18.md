# Nuôi-safety gate (label horizon dài + regime) — OOS test = KHÔNG generalize (2026-08-18)

Triển khai theo yêu cầu user: test giả thuyết "label horizon dài (24h/72h) + feature regime (momentum24H...) →
model học được coin nào SUSTAIN để bật nuôi an toàn". Chạy LOCAL (Oracle CPU, xgboost 3.2), không cần Kaggle.

## Setup
- Data: 170,790 entry thật (g008) × forward path, join 30 market feature từ wfo_feature_store (tại entry ts).
- Target: sustain72 = retEnd_72h>0 (base 68.5%); holdsafe = retEnd_72h>0.05 & maxAdv_72h>−0.20 (base 51.4%).
- Walk-forward: train năm < Y, test năm Y (2023/2024/2025). Model xgb depth4, 200 round.
- 2 biến thể feature: (A) level tuyệt đối; (B) regime-relative = rolling z-score 30 ngày (shift 1, leak-free).

## KẾT QUẢ — OOS gần như NHIỄU, non-stationary
### (A) level tuyệt đối — sustain72
| năm | n | AUC | TOP25% lift | TOP25% win | BOT25% win |
|---|---:|---:|---:|---:|---:|
| 2023 | 2568 | **0.351 (ĐẢO)** | 0.69x | 47% | 74% |
| 2024 | 27311 | 0.583 | 1.14x | 90% | 78% |
| 2025 | 58901 | 0.526 | 1.08x | 76% | 73% |
holdsafe: AUC 0.319/0.556/0.564. Feat importance top: fundingRateAvg24H, fundingRateRaw, volatility24H,
momentum24H, fundingRateTrend (crowded-long/high-funding → reversal — hợp lý kinh tế nhưng KHÔNG generalize).

### (B) regime-relative (z30d) — không cứu được
sustain72 AUC 0.452/0.468/0.450 (dưới ngẫu nhiên đều). holdsafe AUC 0.639/0.318/0.474 (nhảy loạn, đảo dấu 2024).
lift top-quartile 0.85–1.0x (không hơn base).

## VERDICT: hướng nuôi-safety-gate KHÔNG khả thi ở market level
- Không dự đoán được OOS coin nào sustain vs reverse từ feature regime market-level. AUC ~0.45-0.58, đổi dấu
  qua năm (2024 bull lật dấu 2023/2025). Correlation momentum24H −0.196 in-sample là **artifact non-stationary**,
  KHÔNG transfer forward.
- **3 dòng bằng chứng độc lập HỘI TỤ về "không time được nuôi":**
  1. strategy_exit_sweep: nuôi lỏng (RATE_PROFIT 0.10) sụp net −4587; đỉnh ở 0.05 moderate hiện tại.
  2. strategy_volume_regime_join: pattern volume-shape KHÔNG tách runner/reverser.
  3. (doc này) OOS regime model AUC ~0.5, non-stationary.
- Edge SELECTION là thật (11.7× lift bắt pump) — nhưng phần "sẽ sustain hay reverse" KHÔNG dự đoán được từ
  regime feature có sẵn. → Exit moderate cố định (bắt một phần upside, chặn downside) là tối ưu vì KHÔNG time được.

## Còn 1 nhánh chưa test (prior thấp sau kết quả này)
- Per-COIN feature (không phải market aggregate) + label 24h/72h cho SELECTOR. Coin-specific momentum/volume có thể
  mang signal idiosyncratic mà market-aggregate rửa mất. Cần per-coin feature matrix + Kaggle fanout (đang hết quota).
  Given market-level null, prior thành công thấp → chỉ làm nếu muốn đóng đinh dứt điểm.

## KHUYẾN NGHỊ
- DỪNG theo đuổi nuôi-safety-gate / relabel horizon dài cho mục tiêu "nuôi an toàn". Bằng chứng đủ mạnh.
- Giữ: gate max/oldbasket, exit moderate (RATE_PROFIT 0.05), lưới 5m (thắng 15m ở phần bug đã sửa).
- Nếu vẫn muốn vắt: A/B per-coin selector relabel 24h (Kaggle, sau khi quota reset) — nhưng đặt kỳ vọng thấp.

## Files
- /home/ubuntu/nuoi_safety.py (level), nuoi_safety2.py (regime-relative z30d) — Oracle, xgb-env.
