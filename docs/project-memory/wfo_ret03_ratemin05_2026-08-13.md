# WFO retEnd=0.03 + rateMin(moveSL)=0.05 — XONG cả 15m+5m — 2026-08-13

## ⚠️ ĐIỀU KIỆN MỚI, KHÔNG apples-to-apples với bảng 0.008/0.015
Đổi **2 thứ cùng lúc**: `NET_THR` 0.008→**0.03** (label kén) + `SIM_RATE_PROFIT_STOP_MARKET` 0.03→**0.05** (SL chỉ dời-khóa-lãi sau lãi ≥5%). Không tách được ảnh hưởng riêng.

## Kết quả (win4–13)

| Lưới | total | Sharpe | t-stat | %pos | maxDD | full-12w |
|---|---|---|---|---|---|---|
| **15m@0.03rm5** | +9,860 | 0.35 | **1.11 ✗** | 7/10 | −5,318 | **+6,534** (2025H2 âm) |
| **5m@0.03rm5** | **+11,070** | 0.45 | **1.42 ✗** | 8/10 | −4,445 | (win14/15=0) |

So baseline:
| | 15m@0.008 | 5m@0.008 | 15m@0.015 | 5m@0.015 |
|---|---|---|---|---|
| total | +8,176 | +10,814 | +8,568 | +9,000 |
| t | 3.65 | 2.95 | 2.29 | 1.74 |
| maxDD | 0 | −602 | −1,988 | −2,942 |

## Kết luận: (0.03, moveSL0.05) XẤU ở CẢ 2 lưới
- Total **nhìn to** (5m +11,070 vượt cả 0.008; 15m +9,860) nhưng **hoàn toàn do variance**: t rớt **1.11–1.42 (mất ý nghĩa TK)**, maxDD phình **−4,445 / −5,318** (so 0.008: −602 / 0), 2025Q1(win12) = **−4,445 / −4,967** (thảm, vs −602/+84 ở 0.008).
- 15m@0.03 full-12w = **+6,534, THẤP NHẤT mọi config 15m** — **2025H2 chuyển sang ÂM** (−3,325), ngược hẳn 0.015 (+5,123).
- Cơ chế: retEnd 0.03 quá kén → cược to; + moveSL 0.05 → winner đạt 3–5% không kịp khóa lãi, nhả ngược thành lỗ khi dip. Đúng "pump ngắn dump dài" — nới moveSL làm khóa lãi quá muộn.

## Hàm ý
Đẩy threshold cao + nới moveSL **KHÔNG phải hướng tốt** (15m đo được cả 2025H2 mà vẫn xấu). Củng cố quyết định pivot: ưu tiên **native 5m features + lấp 2025H2 + giữ moveSL/threshold thấp (0.008)**.

## Housekeeping
- ✅ Worker đã **revert** về moveSL default 0.03 (bỏ SIM_RATE_PROFIT_STOP_MARKET, cả 5 worker verify hasMoveSL=0). Run sau về mặc định.
- Nguồn: `DONE_{15m,5m}03rm5.txt` (Oracle).
