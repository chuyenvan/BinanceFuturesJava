---
name: preregistration-frame-v1
description: Khung đấu v1 ĐÓNG BĂNG (pre-registration 2026-08-23) — objective O, knob, PASS criteria, giao thức CPCV. Freeze, không sửa bằng mắt.
type: project
---

# KHUNG ĐẤU v1 — ĐÓNG BĂNG (pre-registration) 2026-08-23

v1 = bản chốt sau khi user duyệt 6 quyết định. Đây là "luật đấu trường" — **freeze, không sửa bằng mắt**.
Sửa = pre-register mới + data/forward mới.

> Khôi phục 2026-08-24: bản gốc mất cùng workspace session cũ (bridge chết). Nội dung dưới = bản user
> paste lại nguyên văn, git-commit đóng dấu trong session này. Xem [[handoff-24-8-2026]].

## QUYẾT ĐỊNH ĐÃ KHOÁ (user duyệt)

1. **Tách thời gian**: EXPLORE ≤ 2024 (khám phá tự do) · TEST = 2025→nay (**chạm 1 lần, đếm**) · FORWARD = shadow (trọng tài cuối).
2. **Knob**: xem BẢNG dưới (v1).
3. **min-PnL 3% BỎ** (tránh tái tạo bẫy reject cứng).
4. **Sống-còn**: maxDD-cap **70%** (chỉ loại config tự sát; rủi ro thật thể hiện qua Calmar) · **leverage 1x** (khỏi cần mark-price).
5. **PASS %fold dương ≥ 80%** (bar chặt — ưu tiên đều đặn, hợp việc ghét "đuôi lớn").
6. **Shadow**: giờ 1 nhánh (log chiến lược đang chạy → tích data sạch); thêm nhánh 2 khi CPCV đẻ ứng viên.

## HÀM MỤC TIÊU O (freeze)

```
O = median_fold(Calmar_net) − 0.5 · std_fold(Calmar_net)
```

- `Calmar_net = netPnl / maxDD`, **net đủ fee + slippage + funding** theo timestamp
  (funding = giá của việc giữ dài → "nuôi" tự bị tính phí, **KHÔNG cấm**).
- `median − 0.5·std` qua các fold CPCV → chống đứng-đỉnh-nhọn.
- **KHÔNG có reject cứng nắn chiến lược** (bỏ `TOO_MUCH_CAPITAL_LOCK`, bỏ sàn min-trades cao).
  maxDD chỉ ở mẫu số + cap sống-còn 70%.

## TIÊU CHÍ PASS (quyết TRƯỚC, freeze) — chạm TEST 2025 một lần

Đạt = **TẤT CẢ**: `PBO < 0.2` · `DSR > 0.95` · `median WFE ≥ 0.5` · `%fold dương ≥ 80%`.

Không đạt → **KHÔNG tweak-retry trên TEST**; quay về EXPLORE đẻ giả thuyết mới.

## BẢNG KNOB v1 (Trụ 2 — không gian giả thuyết H)

Nguyên tắc: **ít bậc tự do** (tune 5-6, fix phần còn lại bằng prior). "lướt↔nuôi" = 1 trục liên tục qua `{TP, trailing, max_hold}`.

### Nhóm A — Selector label (target model học)

| knob | ý nghĩa | range tune | ghi chú |
|---|---|---|---|
| `L_TP` | fav barrier (thắng nếu chạm) | [0.04, 0.10] | thay hardcode 0.06 |
| `L_SL` | adv barrier (thua nếu chạm trước) | [0.015, 0.05] | 2-chiều; maxAdv ÂM → hit khi `maxAdv ≤ −L_SL` |
| (horizon) | cửa sổ label | **FIX 4h** | v1 giữ 4h; mở sau |

### Nhóm B — Exit-policy chiến lược (trục lướt↔nuôi)

| knob | ý nghĩa | range tune | ghi chú |
|---|---|---|---|
| `TP` | profit-stop (`RATE_PROFIT_STOP_MARKET`) | [0.01, 0.06] | thấp=lướt, cao=nuôi |
| `TS_MULT` | trailing multiplier (`TS_PROFIT_MULTIPLIER`) | [1.0, 6.0] | chặt=lướt, lỏng=nuôi |
| `MAX_HOLD_H` | trần giữ lệnh (giờ) | [4, 240] | 4h→10 ngày = trục lướt↔nuôi. ⚠️ sim hiện CHƯA có knob này → cần THÊM exit "quá hạn giữ" (việc build) |

### FIX bằng prior (không tune v1)

- DCA off; `SELECTOR_RANK_TOPK=5`; `MIN_MOMENTUM_15M=default`; budget ratios=default; `TS_GIVEBACK`/`TS_MIN_GAP`=default.
- Model hyperparam (XGBoost): `max_depth=5, lr=0.05, subsample=0.8, colsample=0.8` (prior chuẩn, KHÔNG tune v1).

> ⚠️ CẦN BẠN LIẾC: 6 knob tune (`L_TP, L_SL, TP, TS_MULT, MAX_HOLD_H` — 5 cái; horizon fix) đủ chưa hay muốn thêm/bớt.

## GIAO THỨC V (freeze)

- **CPCV**: chia lịch sử thành N block, chọn tổ hợp k block làm test → phân phối Calmar (không single-path).
  N/k chốt: **N=8, k=2 (28 tổ hợp)** — cân giữa số path & chi phí.
- **Purge + embargo** = `max(label_horizon, feature_lookback)` mỗi biên train/test (vá leak đang có).
- Knob chọn ở **INNER** (train-only); **OUTER chỉ đo**. Người **không chỉnh** giữa outer-fold.
- **Đếm mọi trial** → DSR + PBO.
- Pre-register (doc này) freeze **trước khi** chạm TEST 2025.

## KẾ HOẠCH BUILD (thứ tự, sau khi device/Oracle sẵn sàng)

1. Vá leak nền (Java+Python): purge/embargo = horizon ở WFO `buildWindows` + selector/gate train; `feature_order.json` 1 nguồn. [branch code]
2. Thêm knob `MAX_HOLD_H` vào sim (exit quá-hạn-giữ) + expose `L_TP/L_SL/TP/TS_MULT` làm tham số. [code]
3. Objective O mới (parameterized, median−0.5σ Calmar-net, bỏ reject cứng) — thay `HPOFitnessCalculatorV4` dạng soft. [code, có thể cần recompile jar]
4. CPCV harness (N=8,k=2) bọc pipeline: inner chọn knob, outer đo, purge/embargo, đếm trial, xuất phân phối + DSR/PBO. [orchestration]
5. Chạy trên EXPLORE ≤2024 để **debug code** (KHÔNG kết luận).
6. Freeze lần cuối → chạm TEST 2025 **một lần** → check PASS.
7. Song song: bật shadow 1 nhánh ngay (tích data sạch).

## RESIDUAL (thành thật)

Chọn H/O/feature/universe vẫn là prior người. Không về 0. Chặn biên bằng ít-knob + O chuẩn + forward xác nhận.
**Forward sụp = khung sai.**
