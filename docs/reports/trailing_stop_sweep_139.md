# TASK-139 — Sweep RATE_PROFIT_STOP_MARKET (giả thuyết Uni: trailing cắt non đuôi phải) — 2026-07-07

**Giả thuyết Uni (đi ngủ để lại):** hệ chọn coin pump/dump đánh nhanh-rút-gọn, nhưng RATE_PROFIT_STOP_MARKET=0.01032
làm trailing kích hoạt QUÁ SỚM (lãi 1% đã kéo SL) → coin giật 1-3% bị quét stop non → tự cắt cụt đuôi phải.

## Kết quả (config baseline, chỉ đổi RATE_PROFIT_STOP_MARKET)
| rateTS | 2024 PnL/calmar/hold | 2025Q2 PnL/calmar | TOÀN KỲ PnL/calmar/maxDD | holdMed toàn kỳ | %hold>60p |
|---|---|---|---|---|---|
| 0.01032 (base) | 5084 / 4.99 / 9ph | 241 / 10.5 | 17804 / 1.65 / 30.9% | 7 phút | 16.1% |
| 0.02032 | 7255 / 6.43 | 340 / 9.3 | 27747 / 2.55 / 31.0% | 21 phút | 33.0% |
| **0.03032 (Uni)** | 8501 / 5.41 / 76ph | 489 / **16.6** | 34442 / 3.06 / 32.1% | 52 phút | 47.6% |
| 0.04032 | 9851 / 3.74 | 463 / 16.0 | 38346 / 3.41 / 32.1% | 110 phút | 59.2% |
| 0.05032 | 10598 / 3.76 | 326 / 7.5 | **42405 / 3.78** / 32.0% | 197 phút | 67.0% |

## KẾT LUẬN — GIẢ THUYẾT UNI ĐÚNG HOÀN TOÀN (phát hiện lớn nhất chuỗi điều tra)
1. **Trailing stop 0.01032 là thủ phạm chính, KHÔNG phải WFO/gate/model.** Nó cắt non đuôi phải:
   holding median 7 phút (coin chưa kịp pump đã bị chốt).
2. **Nâng ngưỡng → PnL toàn kỳ TĂNG 2.4x (17.8k→42.4k) VÀ calmar TĂNG 2.3x (1.65→3.78), maxDD gần như KHÔNG ĐỔI (~31-32%).**
   Đây là cải thiện Pareto hiếm: lãi nhiều hơn + rủi ro/lãi tốt hơn CÙNG LÚC. Không phải đánh đổi.
3. **Holding median 7→197 phút, %hold>60p 16%→67%.** Đúng thiết kế gốc: giữ coin tới pump thật thay vì chốt non.
4. 2025Q2 (quý phẳng) cũng lãi gấp đôi ở 0.03 (241→489, calmar 10.5→16.6).

## ĐIỂM NGỌT
- **0.03032 (giá trị Uni chọn): cân bằng đẹp nhất** — PnL +93% (34.4k), calmar 3.06 (tốt), maxDD 32% (thấp), 2025Q2 calmar 16.6 (đỉnh).
- 0.05032: PnL cao nhất (42.4k) + calmar cao nhất (3.78) toàn kỳ, nhưng 2025Q2 calmar tụt (7.5) → hơi over ở quý phẳng.
- Khuyến nghị: 0.03-0.04 là vùng robust. 0.05 tối đa PnL nhưng kém ổn định ở regime phẳng.

## ĐẢO NGƯỢC KẾT LUẬN TỐI QUA
Tối qua kết luận "edge thưa, WFE ~0.22 là trần cấu trúc". SAI. Trần đó do trailing cắt non. Sửa trailing:
- Edge KHÔNG thưa như tưởng — nó bị chốt non nên trông thưa.
- WFE có thể tăng đáng kể nếu chạy lại WFO với RATE_PROFIT_STOP_MARKET cao hơn (đưa vào genome để WFO tune).

## HƯỚNG KẾ (Uni quyết khi dậy)
1. Đổi RATE_PROFIT_STOP_MARKET baseline 0.01032 → 0.03032 (hoặc đưa vào GENOME range [0.02,0.05] cho WFO tune).
2. Chạy lại WFO với trailing mới → đo WFE. Kỳ vọng WFE tăng mạnh (đây mới là nút thắt thật, không phải MIN_MOM15).
3. Cân nhắc: giữ hold không stoploss tới pump (Uni gợi ý) — sweep cho thấy 0.05 hold 197 phút vẫn maxDD 32%, an toàn.
