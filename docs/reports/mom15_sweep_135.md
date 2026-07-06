# TASK-135 — Sweep MIN_MOMENTUM_15M (giữ mọi tham số khác baseline) — 2026-07-06

**Mục đích:** gate MOM15 lọc đúng (A/B chứng minh), nhưng WFO gene range [0.030,0.050] có over-tighten? Tìm vùng tối ưu robust.

## Bảng đầy đủ (pnl / calmar / sortino / note)
| min15m | 2023 | 2024 bull | 2025Q2 phẳng | toàn kỳ (pnl/calmar/posYr) |
|---|---|---|---|---|
| 0.010 | 1369 / 0.99 / LOCK | 7312 / 2.40 | **−10 BURN** | 14650 / 1.01 / 83% (maxDD 41%) |
| 0.015 | 1087 / 2.56 | 6966 / **4.44** | 733 / 5.47 | 16022 / 1.39 / 67% |
| **0.0228 (baseline)** | 928 / 2.64 | 5165 / 5.07 | 242 / **10.5** | **17685 / 1.63 / 67%** |
| 0.030 | 712 / 2.69 | 4312 / **5.28** | 70 / TOO_FEW | 15955 / 1.50 / 83% |
| 0.040 | 678 / 2.56 | 3195 / 4.36 | **0 ZERO** | **17321 / 1.78 / 100%** |
| 0.050 | 647 / 2.44 | 1793 / 2.72 | 0 ZERO | 10126 / 0.92 / 83% |
| 0.070 | 455 / TOO_FEW | 458 / TOO_FEW | 0 ZERO | 14547 / **1.95** / 83% |

## PHÁT HIỆN — có hai "điểm ngọt" khác nhau tùy tiêu chí
1. **Tối đa PnL tuyệt đối toàn kỳ: 0.0228** (17,685) — nhưng posYr 67% (UNSTABLE, một năm âm).
2. **Tối đa ổn định + calmar: 0.040** (pnl 17,321, calmar 1.78, **posYr 100%**, maxDD thấp nhất 27.8%) —
   gần bằng PnL đỉnh nhưng ỔN ĐỊNH hơn hẳn (mọi năm dương). ĐÁNG CHÚ Ý: 0.040 lại làm 2025Q2 ZERO.
3. **Cận trên gene 0.050 là điểm TỆ NHẤT toàn kỳ** (pnl 10,126, calmar 0.92) — xác nhận WFO được phép chọn
   0.050 = được phép chọn điểm tệ nhất. Đây là bằng chứng over-tighten: range [0.030,0.050] CHỨA điểm tệ nhất.

## MÂU THUẪN QUAN TRỌNG (không vội kết luận)
- Ở khoảng NGẮN (2024, 2025Q2): ngưỡng THẤP (0.015-0.0228) tốt nhất — calmar cao, trade nhiều, 2025Q2 sống.
- Ở TOÀN KỲ: ngưỡng CAO hơn (0.040) ổn định nhất (posYr 100%) dù 2025Q2 ZERO.
- ⇒ Không có MỘT ngưỡng tĩnh tối ưu mọi khoảng. Đây CHÍNH LÀ lý do WFO tồn tại (chọn ngưỡng per-window).
  Nhưng gene range hiện [0.030,0.050] LOẠI mất vùng 0.015-0.0228 vốn tốt cho nhiều window ngắn.

## KHUYẾN NGHỊ (Uni quyết — PnL-impacting)
1. **MỞ RỘNG gene range xuống**, KHÔNG thu hẹp: [0.030,0.050] → **[0.015, 0.045]**. Lý do: cho WFO CƠ HỘI
   chọn vùng thấp (tốt cho window ngắn/phẳng như 2025Q2) VÀ vùng cao (ổn định cho window biến động), thay vì
   ép vào dải toàn giá trị cao. Bỏ 0.050 (điểm tệ nhất) khỏi range.
2. Đây là thay đổi 1 dòng GENOME trong StrategyWfoTask — cần chạy lại WFO để đo WFE mới. Kỳ vọng: WFE tăng vì
   WFO thoát khỏi dải bị ép.
3. Vẫn giữ 2 AI (corr −0.54: gate bổ sung thông tin thật; A/B: bỏ gate = cháy). KHÔNG cần đổi kiến trúc.

## GHI CHÚ: w13/2025Q2 ZERO không phải bug — là hệ quả ngưỡng cao. Baseline 0.0228 thì 2025Q2 SỐNG (242 pnl,
calmar 10.5). Nếu mở range xuống 0.015, WFO có thể chọn ngưỡng thấp cho window phẳng → hết ZERO.
