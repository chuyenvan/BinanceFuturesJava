# VERDICT đường cong lưới × ngưỡng (net 0.008 vs 0.015) — CHỐT 2026-08-13

## Kết luận 1 câu
Trên **10 window OOS chung (win4–13, 2023Q1–2025Q2)**: **0.008 vẫn là ngưỡng tốt hơn tổng thể**. Hai cấu hình đáng chọn nhất không đổi: **5m@0.008** (total cao nhất +10,814, t=2.95 có ý nghĩa) và **15m@0.008** (đều nhất, t=3.65, maxDD=0). **Không cấu hình 0.015 nào vượt được 2 cái này trên khúc đo được.** Lợi thế của 0.015 chỉ hiện ở 2025H2 (mà lưới mịn thiếu do OOM).

## Bảng 2 chiều — Total PnL (win4–13)

| Total PnL | 15m | 5m | 3m | 1m |
|---|---|---|---|---|
| **@0.008** | +8,176 | **+10,814** | +7,287 | +9,183 |
| **@0.015** | +8,568 | +9,000 | +9,498 | +9,202 |

## Bảng 2 chiều — t-stat (win4–13) · t≥2 = có ý nghĩa

| t-stat | 15m | 5m | 3m | 1m |
|---|---|---|---|---|
| **@0.008** | **3.65** | **2.95** | 1.38 ✗ | 1.44 ✗ |
| **@0.015** | 2.29 | 1.74 ✗ | **2.15** | 1.45 ✗ |

## Bảng 2 chiều — Max drawdown (win4–13)

| maxDD | 15m | 5m | 3m | 1m |
|---|---|---|---|---|
| **@0.008** | **0** | **−602** | −3,321 | −3,715 |
| **@0.015** | −1,988 | −2,942 | −1,943 | −3,715 |

## Tác động của việc nâng ngưỡng 0.008 → 0.015 (theo lưới)
- **15m**: total +5%, nhưng độ đều tụt (t 3.65→2.29, DD 0→−1,988). 2025Q1 từ +84 → −1,988. → xấu đi về chất.
- **5m**: total −17%, t 2.95→1.74 (mất ý nghĩa), DD −602→−2,942. → xấu đi rõ nhất.
- **3m**: total +30%, t 1.38→2.15 (đạt ý nghĩa), DD −3,321→−1,943. → **tốt lên rõ** (cấu hình 0.015 tốt nhất).
- **1m**: gần như KHÔNG đổi (total +19, t 1.44→1.45, DD −3,715 y hệt, win12 −3,715.4 giống nhau từng số). → **vô cảm với ngưỡng**.

## Đọc pattern (đã sửa nhận định)
Không có quy luật đơn giản "lưới càng mịn càng hưởng lợi từ ngưỡng cao" — **1m bác bỏ điều đó** (đổi ngưỡng vô tác dụng). Bức tranh thật: tác động của ngưỡng lên từng lưới **không đơn điệu**, chỉ **3m là điểm mà 0.015 thực sự có ích**; 15m/5m bị hại; 1m trơ. Nghĩa là 3m@0.015 là một local optimum riêng, không phải khởi đầu của một xu hướng.

## Xếp hạng tổng (8 cấu hình, theo t-stat / risk-adjusted, win4–13)
1. **15m@0.008** — t=3.65, total +8,176, DD 0 → đều nhất
2. **5m@0.008** — t=2.95, total **+10,814**, DD −602 → tốt nhất về return-có-ý-nghĩa
3. 15m@0.015 — t=2.29, +8,568
4. **3m@0.015** — t=2.15, +9,498 (0.015 tốt nhất)
5. 5m@0.015 — t=1.74, +9,000 (mất ý nghĩa)
6. 1m@0.015 — t=1.45, +9,202 (mất ý nghĩa)
7. 1m@0.008 — t=1.44, +9,183 (mất ý nghĩa)
8. 3m@0.008 — t=1.38, +7,287 (mất ý nghĩa)

## Khuyến nghị baseline
- **Ưu tiên đều/robust cho vận hành → 15m@0.008** (10/10 quý dương, DD 0, t 3.65).
- **Ưu tiên total mà vẫn chắc → 5m@0.008** (+10,814, t 2.95).
- **Cân nhắc 15m@0.015** CHỈ nếu tin thị trường tới giống 2025H2 (trend mạnh): full-12w=+13,691 (bắt sóng 2025Q4 +5,812). Rủi ro: 2025Q1 kiểu downtrend thì 0.015 ăn đòn nặng hơn.
- **Bỏ 1m và 3m@0.008**: over-trade, t<2, DD lớn, không có edge chắc.

## Cảnh báo (quyết định trước khi tin 0.015)
- **Lưới mịn thiếu 2 window 2025H2** (2025Q3 52M / Q4 61M row, OOM decode 1m). Toàn bộ so 0.015-vs-0.008 ở đây **chỉ trên win4–13**, vốn THIÊN VỊ 0.008 (vì 0.015 mạnh ở 2025H2). Ở 15m — nơi đo được cả 2025H2 — 0.015 (+13,691) > 0.008 (+11,817).
- Muốn phán 0.015 công bằng ở lưới mịn: cần lấp 2025H2 (decoder đọc-theo-dải hoặc re-export Tool1 1m theo tháng).

## Kiểm chứng dữ liệu (audit riêng — ĐẠT)
15/15 lệnh WFO mẫu: `priceClose` sim = close nến 1m Binance đúng timestamp, sai 0.0000%. Chi tiết ở `claude/wfo_trade_audit_2026-08-12.md`.

## Ghi chú kỹ thuật
- Nguồn: `~/claudedata/sweep/DONE_{15m,5m,3m,1m}{008f09,015f09}.txt` + `DONE_15m015.txt` (Oracle). TOTAL_12w = tổng PnL window OOS rời nhau. Metric win4–13 để 4 lưới apples-to-apples (15m có đủ win4–15).
- 0.015 = predict-only từ model 15m@0.015 (`sel-models-net015`), đồng bộ cách làm 0.008. Kernel 015 in "NET_THR=0.008" chỉ là print cứng cũ (thực chạy 0.015: pos-rate/AUC/MD5 xác nhận).
- Hạ tầng: device VM chết → Oracle qua Git-ssh + desktop-commander PowerShell + OrBash(base64). Kaggle CLI `/home/ubuntu/kaggle_latest_venv/bin/kaggle`.
