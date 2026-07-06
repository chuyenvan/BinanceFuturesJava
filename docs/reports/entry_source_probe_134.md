# TASK-134 — Đo đóng góp funding-selector vs gate MOM15 (probe, config baseline) — 2026-07-06

**Câu hỏi:** funding-selector (nguyên lý: pump/dump tồn tại mọi regime) có bị gate bắt-đáy bóp không?

## Kết quả (EntrySourceProbe, dataset wf, config baseline chưa tune genome)
| giai đoạn | coin funding đủ ĐK | PASS | bị gate chặn | %PASS | tỉ trọng nguồn (BIG_DOWN/PRED/DCA) |
|---|---|---|---|---|---|
| 2025Q2 phẳng (w13) | 743,380 | 38 | 743,342 | 0.0% | 0% / 100% / 0% |
| 2024Q2 thường | 274,795 | 168 | 274,627 | 0.1% | 12.9% / 83.6% / 3.5% |
| 2022 crash LUNA/FTT | 380,539 | 1,705 | 378,834 | 0.4% | 0.7% / 96.3% / 2.9% |
| **toàn kỳ 2021–2026** | **8,264,021** | **9,567** | 8,254,454 | **0.1%** | **2.4% / 93.2% / 4.4%** |

## PHÁT HIỆN (đảo ngược hiểu biết cũ)
1. **Gate MOM15 chặn ~99.9% tín hiệu funding-selector ở MỌI regime** (không chỉ thị trường phẳng). 8.26M tín hiệu → 9.567 vào lệnh.
2. **Funding-selector LÀ nguồn entry chính (93% số leg toàn kỳ)**, KHÔNG phải BIG_DOWN (2.4%). Hệ sống nhờ số ít lệnh funding lọt khe, không phải bắt-đáy.
3. **Xung đột triết lý:** `checkSignalDynamic` đòi `predReturn15M ≥ MIN_MOMENTUM_15M` (~2%), nhưng coin funding-selector chọn (pump/dump) thường momentum 15m thấp/âm → gần trực giao → gate loại gần hết. rankIC 0.344 của selector CHƯA từng được khai thác.
4. w13 ZERO: market phẳng (BIG_DOWN=0) + funding chỉ 38 lệnh lọt/quý → không lệnh nào sống → ZERO.

## CÂU HỎI QUYẾT ĐỊNH (đo tiếp trước khi sửa)
9.567 lệnh lọt qua gate — chúng TỐT hơn hay chỉ NGANG số bị loại? 
- Nếu gate lọc ĐÚNG (giữ tinh hoa) → nới = thêm rác, phải thận trọng.
- Nếu gate lọc MÙ (loại cả lệnh tốt) → nới = mỏ vàng chưa khai thác.
→ Cần A/B: chạy backtest FILTER_MODE=E (tắt MOM15, giữ RISK) vs baseline, so PnL/WFE/maxDD.

## Hướng (chờ kết quả A/B + Uni duyệt)
Tách funding-selector khỏi gate MOM15 bắt-đáy: hoặc (a) FILTER_MODE=E cho nhánh PREDICT_SYMBOL, hoặc
(b) gate riêng phù hợp pump/dump (chấp nhận momentum thấp nếu funding score đủ mạnh). PnL-impacting → Uni quyết.
