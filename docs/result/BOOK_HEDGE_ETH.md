# BOOK_HEDGE_ETH — biến thể ETH (kết quả, THĂM DÒ)

Ngày 2026-10-19. Pre-reg `docs/prereg/PREREG_BOOK_HEDGE_ETH.md` 10bd5a02 (lần thử thứ 2 ⇒ thăm dò, không thăng hạng trên DEV).
Return phút ETHUSDT dựng từ kline1m Vision (2,37 triệu phút, 0 khoảng trống). V1 PASS (nền trùng ISO 8/8), V2 PASS (0 phút thiếu).

| Arm | CAGR22 | maxDD22 | Calmar22 | UW22 | ΣPnL | DD LUNA | DD ≥5pp nông hơn | ΔCalmar CI99 | GO |
|---|---|---|---|---|---|---|---|---|---|
| Nền | 37,95 | −22,55 | 1,69 | 116 | 110 047 | −22,3 | — | — | — |
| BTC h0,5 | 34,71 | −17,81 | 1,95 | 127 | 99 956 | −17,1 | 4/8 | [+0,06; +0,47] | NO |
| **ETH h0,5** | 35,32 | −18,02 | 1,96 | 104 | 97 595 | −14,9 | 5/8 | [+0,04; +0,50] | NO |
| BTC h1,0 | 31,37 | −16,86 | 1,86 | 197 | 89 865 | −12,2 | 6/8 | [−0,08; +0,42] | NO |
| ETH h1,0 | 32,45 | −18,57 | 1,75 | 151 | 85 144 | −11,2 | 1/8 | [−0,16; +0,27] | NO |

ETH − BTC ghép cặp theo seed: h0,5 ΔCalmar +0,01 (4/8), ΔDD −0,21pp (3/8) ⇒ ngang nhau; h1,0 ETH kém hơn 8/8.
PnL hedge theo năm (h0,5, USD trung bình/seed): BTC 2022 +435, 2023 −2 622, 2024 −6 121, 2025 −2 652;
ETH 2022 +403, 2023 −3 542, 2024 −5 334, 2025 −3 388 ⇒ chi phí hedge nằm ở năm tăng, lợi ích tập trung trong vài đợt sập.

## Đọc
- ETH không tốt hơn BTC. Hai công cụ cho cùng một hiệu ứng ở h0,5 (DD −4,5…−4,7pp, Calmar +0,26…+0,27, ΣPnL −9…−11 %)
  ⇒ hiệu ứng có vẻ là của việc hedge nhân tố thị trường, không phải của riêng công cụ. Cả hai trượt luật DD (cần 7/8 seed ≥ 5pp).
- Funding bỏ qua cho cả hai (so sánh công bằng). Ứng viên nếu đi tiếp: BTC h0,5 (thanh khoản cao nhất, funding thường có lợi hơn).
