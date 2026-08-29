# METRIC + ĐIỂM tổng hợp — net/72h/drop-OI + SL arm-rate + AUC — 2026-08-11

> Nơi gom TẤT CẢ số. File gốc Oracle: `sweep/DONE_*.txt`, `sweep/METRIC_*.txt`, `sweep/FULL_*.md`.
> SSH `ubuntu@161.118.212.3` key `id_rsa_chuyennd_openssh`.

## ⚠️ ĐỌC TRƯỚC — độ tin cậy (nhiễu run-to-run)
Cùng config (0.03, loose_k8, unf15net) chạy nhiều lần: **PnL ổn định ~±5-10%** (10,971 / 11,551 / 11,625) nhưng
**maxDD LOẠN** (19.6% / 21.9% / 35.4%). maxDD là thống kê ĐUÔI (chi phối bởi đúng khoảnh khắc tệ nhất ở 25Q4/sự kiện
Oct-2025), tổ hợp lệnh mở lúc đó đổi theo nondeterminism sim (nghi parallel order-matching). ⇒ **maxDD KHÔNG so được;
chỉ đọc PnL với ±10% noise. Gap PnL <~1,000 = nhiễu.** Đây là lý do cần audit lệnh (truy nondeterminism).

## 1. NET_THR sweep (15m, 12w) — chọn ngưỡng label net
0.005=+9,908(pos69%) | **0.008=+10,942** | 0.012=+8,714 | 0.02=+11,738(dồn 2024). maxFav(lướt)=**−7,030** (thua, chắc chắn).
→ band robust net = **0.005–0.008**, đủ feature.

## 2. So 3 cấu hình (cùng batch, 12w) — PnL/lệnh/maxDD
| | baseline 4h@0.008 | 72h | drop-OI |
|---|---:|---:|---:|
| PnL 12w | 11,551 | **9,264** | 10,397 |
| Số lệnh | 2,043 | 1,920 | 2,179 |
| 25Q1 crash | +1,397 | +1,415 | **−139** |
- **72h: thua** (−20%, >2× noise → thật kém hơn). **drop-OI: thua** (25Q1 lật âm — dấu hiệu tin hơn tổng). Giữ **net 4h + đủ feature (có OI)**.

## 3. AUC screen (selector-level, OOS, không sim) — mean 13 fold
| | mean AUC | prec@top10 | lift |
|---|---:|---:|---:|
| baseline full-feat | **0.5798** | 0.393 | 1.37 |
| drop-OI (bỏ 5 OI) | **0.5803** | ~0.39 | ~1.36 |
- **Gần như y HỆT** → bỏ OI KHÔNG đổi rank-skill tổng. Nhưng WFO cho thấy OI giúp ở **đuôi/crash** (25Q1). 
- **Bài học phương pháp:** AUC-screen sàng nhanh (~8', bỏ sim) bắt được edge *tổng*, KHÔNG bắt tail-risk → quyết định cuối vẫn cần WFO. Selector edge thật nhưng khiêm tốn (AUC ~0.58, lift ~1.37).

## 4. SL arm-rate sweep `SIM_RATE_PROFIT_STOP_MARKET` (bản ĐÃ FIX bug env — slb*)
| arm-rate | PnL 12w | Số lệnh | worstDD (KHÔNG tin) |
|---|---:|---:|---:|
| 0.03 (hiện tại) | 11,625 | 2,087 | 35.4%* |
| 0.04 | 12,797 | 2,011 | 19.8%* |
| **0.05** | **16,869** | 2,153 | 20.8%* |
- **PnL tăng MẠNH theo arm-rate: 11.6k → 12.8k → 16.9k. 0.05 = +45% vs 0.03 — vượt XA noise ⇒ hiệu ứng THẬT.**
- Cơ chế: arm-rate cao = SL chỉ đặt sau lãi +5% = **giữ winner chạy lâu hơn** → PnL cao. Khớp TASK-139 (0.03-0.05 → 2.4×).
- ⚠️ maxDD (*) KHÔNG đọc được (nondeterministic). **CHƯA chốt 0.05** vì: (a) cần repeat-confirm +45% không phải cú may, (b) phải bound DD qua nhiều lần chạy, (c) 0.05 = SL rất muộn, rủi ro loser chạy xa (dù có min-momentum + loser-exit gác).
- ❌ Bỏ qua bản `slr*` cũ (bug env xoá mất SIM_MIN_MOMENTUM_15M + SELECTOR_RANK_TOPK — số rác).

## 5. Full export 1m unfiltered — ✅ XONG
21/21 quý 2021Q1→2026Q1 tại `/home/ubuntu/tool1_1m_unf/` (~15GB). Sẵn sàng cho pipeline predict-1m (upload Kaggle → gen PRED_GRID_MIN=1).

## 6. Việc đáng làm tiếp (ưu tiên)
1. **Confirm SL 0.05** (repeat 2-3 lần lấy PnL trung bình + bound DD) + thử 0.06/0.07 xem PnL còn leo. **Lead mạnh nhất hiện tại.**
2. **Audit lệnh** (truy nondeterminism maxDD + verify vào/ra vs Aerospike/fapi/Vision).
3. Pipeline **predict-1m net@0.008** (export xong) — so 1m vs 15m.
