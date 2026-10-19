# TS_AFTER — lệnh bị time-stop 168h trên K24+skipFull: nếu GIỮ thêm thì sao? (chẩn đoán, KHÔNG pre-reg)

Ngày 2026-10-19. Chỉ mô tả (không phải phép thử GO/NO-GO). Script `research/analysis/ts_after.py`, JSON `docs/result/ts_after/ts_after.json`.
Dữ liệu: 8 run OFF `gqsf-*`; giá sau cắt = close kline1m Vision; nhân tố alt = ALT_EW (`edge_attr/index.npz`).

- Time-stop (status STOP_LOSS_DONE, đúng 168h): 541 cụm/seed (4 331 tổng), ΣPnL −79,1k/seed (lãi ròng cả hệ 110k).
- Đối chiếu: trailing thắng 2 974 chân, +189,7k (seed A1).
- "PnL thêm" = q × (giá thoát giả định − giá cắt), thoát khi chạm arm (TB vốn × 1,07, trừ 3 % trượt trailing) hoặc hết H ngày; bỏ phí;
  KHÔNG tính vốn bị khoá (xem dưới).

| Giữ thêm H | ret coin trung vị | DD thêm trung vị / p10 | về hoà vốn | chạm arm | PnL thêm/seed |
|---|---|---|---|---|---|
| 7 ngày | −0,5 % | −9,7 / −22,8 % | 44 % | 23 % | −2,5k |
| 14 ngày | +0,3 % | −13,6 / −32,9 % | 54 % | 36 % | −2,1k |
| 30 ngày | −7,8 % | −21,5 / −46,1 % | 62 % | 45 % | −13,1k |
| 60 ngày | −7,1 % | −30,0 / −57,1 % | 68 % | 55 % | −11,7k |
| 90 ngày | −13,2 % | −35,4 / −62,4 % | 74 % | 62 % | −11,8k |

Theo trạng thái thị trường lúc cắt (tercile DD 30 ngày của ALT_EW — ngưỡng chọn từ chính dữ liệu này):
| Nhóm | PnL thêm/seed H=7 / 14 / 30 / 60 / 90 ngày |
|---|---|
| T1 alt sập mạnh (ALT_EW ≤ −30 % so đỉnh 30 ngày) | **+6,2k / +8,8k / +4,8k / +8,0k / +11,7k** |
| T2 | −4,5k / −6,7k / −11,0k / −13,0k / −17,0k |
| T3 alt bình thường | −4,2k / −4,1k / −6,9k / −6,8k / −6,4k |

Theo năm cắt (H=30): 2021 +1,2k · 2022 +0,7k · 2023 −1,1k · 2024 −6,7k · 2025 −7,2k. 28,6 % cụm bị hệ VÀO LẠI cùng coin trong 30 ngày.

Vốn bị khoá: hệ lãi trung bình 2,1 %/USD/ngày khi vốn đang làm việc ⇒ cận trên chi phí cơ hội (H=14) ~91k/seed — cận trên vì vốn không phải lúc nào
cũng bị chặn; nhưng lúc sập (T1) là lúc trần vốn bị chạm nhiều nhất ⇒ chi phí thật chỉ đo được bằng sim (HOLDTODIE 09-30: tắt TS ⇒ CAGR 34 → 2 %).

## Đọc
- Giữ vô điều kiện làm XẤU hơn ở mọi H (kể cả chưa tính vốn khoá) — khớp HOLDDCA / HOLDTODIE / EXIT_STRUCT.
- Có một tập con đúng trực giác owner: cắt khi CẢ thị trường alt đang sập (T1) ⇒ giữ thêm 14–90 ngày có lãi +5…+12k/seed (thô).
  Ngưỡng tercile là hậu kiểm; hiệu ứng nhỏ hơn MDE thước exit trên DEV (~16–19k, EXIT_TIME_B0) và chưa trừ vốn khoá đúng lúc vốn quý nhất.
