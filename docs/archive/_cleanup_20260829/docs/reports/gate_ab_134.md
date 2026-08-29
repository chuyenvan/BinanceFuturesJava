# TASK-134 A/B — Gate MOM15 lọc ĐÚNG hay lọc MÙ? — 2026-07-06

**Thiết kế:** 3 arm (A=MOM15+RISK baseline, E=tắt MOM15, OFF=tắt hết) × 5 khoảng độc lập, cùng genome baseline, chỉ đổi FILTER_MODE. Đo PnL/ddPct/calmar/sortino/%năm-dương.

## Kết quả
| khoảng | A: pnl / calmar / note | E: pnl / calmar / note | OFF |
|---|---|---|---|
| 2022 crash | −84 / BURN | −12,812 / BURN | ≈ E |
| 2023 hồi phục | +928 / 2.64 | −4,239 / BURN | ≈ E |
| 2024 bull | **+5,084 / 4.99 / sortino 20.9 SUCCESS** | −6,478 / BURN | ≈ E |
| 2025Q2 phẳng | **+241 / 10.47 / sortino 55 SUCCESS** | −7,173 / BURN | ≈ E |
| toàn kỳ | **+17,804 / 1.65** | −2,641 / BURN | ≈ E |

## KẾT LUẬN DỨT KHOÁT
1. **Gate MOM15 lọc ĐÚNG, KHÔNG lọc mù.** Tắt nó (E/OFF) → CHÁY TÀI KHOẢN ở MỌI regime. 99.9% funding-selector
   bị chặn phần lớn LÀ RÁC: bỏ phanh, #lệnh 9.567→23.465 nhưng PnL +17.804 → −2.641.
2. **E ≈ OFF từng dòng** → RISK gate một mình không đủ; MOM15 là phanh sống còn.
3. ⇒ **HƯỚNG "nới gate/tách funding khỏi MOM15" BỊ BÁC BỎ.** May đã đo trước khi sửa — nếu làm, hệ cháy.

## PHÁT HIỆN NGƯỢC (đắt giá) — về 2025Q2 và bản chất hệ
- Config BASELINE: 2025Q2 KHÔNG zero — có 38 lệnh, calmar 10.47, sortino 55 (chất lượng CỰC CAO).
- w13 ZERO_TRADES là do **genome sau WFO siết MIN_MOMENTUM_15M lên 0.030-0.050** (baseline 0.0228) → giết cả
  cơ hội funding chất lượng cao. Vấn đề KHÔNG phải gate sai mà là **WFO tune ngưỡng gate tới cực đoan** cho
  một số window → mất giao dịch tốt ở regime phẳng.
- Nhận diện đúng bản chất hệ: **funding-selector + gate MOM15 = "chỉ vào coin pump/dump ĐÃ bắt đầu nảy"**.
  Gate MOM15 lọc coin dump-chưa-nảy (predReturn15M âm = đang rơi, bắt dao rơi). Đây là edge THẬT: selector tìm
  coin có dòng tiền lệch, MOM15 xác nhận đã tạo đáy/nảy → vào. Bỏ MOM15 = bắt dao rơi = cháy.

## HƯỚNG MỚI (thay hướng nới gate đã bác bỏ)
1. **KHÔNG tắt/nới MOM15.** Giữ gate — nó là lõi edge.
2. Vấn đề thật = **WFO over-tighten**: range gene MIN_MOMENTUM_15M [0.030,0.050] có thể quá cao ở cận trên.
   Baseline 0.0228 cho kết quả tốt hơn ở 2025Q2. → Cân nhắc HẠ cận trên gene về ~0.030 hoặc thu hẹp range.
3. Đo tiếp: sweep MIN_MOMENTUM_15M trên toàn kỳ (giữ nguyên phần còn lại) → tìm ngưỡng tối ưu robust,
   tránh để WFO đẩy tới cực đoan. Đây là tinh chỉnh 1 tham số, an toàn, có thể A/B sạch.
4. WFE ~0.24 giờ hiểu rõ: nhiều window OOS, WFO chọn genome siết quá chặt (tối ưu IS) → OOS ít/không trade →
   PnL_OOS thấp. KHÔNG phải model kém — là **over-tightening của chính vòng tối ưu**.
