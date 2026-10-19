# BOOK_HEDGE_ALT — công cụ hedge `ZILUSDT` (kết quả, THĂM DÒ)

Ngày 2026-10-19. Pre-reg `docs/prereg/PREREG_BOOK_HEDGE_ALT.md` **`bf2a53d7`** (commit TRƯỚC khi chạy).
Đây là **lần thử thứ 3** trong họ BOOK_HEDGE ⇒ kết quả **THĂM DÒ**: kể cả GO cũng **KHÔNG** thăng hạng trên DEV;
chỉ được chuyển sang xác nhận **1 lần** trên HO4 2026 với `h` cố định.

Return phút `ZILUSDT` dựng từ kline1m Vision (2 361 599 phút, 2021-07-01 → 2025-12-31, gap = return 0).

| Arm | CAGR22 | maxDD22 | Calmar22 | UW22 | ΣPnL | DD LUNA | DD ≥5pp nông hơn | ΔCalmar CI99 | GO |
|---|---|---|---|---|---|---|---|---|---|
| Nền | 37,95 | −22,55 | 1,69 | 116 | 110 047 | −22,3 | — | — | — |
| **ZIL h0,5** | 33,09 | **−11,62** | 2,90 | 112 | 93 271 | −11,6 | **8/8** | **[+0,78; +1,64]** | **GO** |
| **ZIL h1,0** | 27,85 | **−8,63** | **3,23** | 177 | 76 496 | −7,3 | **8/8** | **[+1,23; +1,85]** | **GO** |
| BTC h0,5 (7c6e816e) | 34,71 | −17,81 | 1,95 | 127 | 99 956 | −17,1 | 4/8 | [+0,06; +0,47] | NO |
| ETH h0,5 (563810ed) | 35,32 | −18,02 | 1,96 | 104 | 97 595 | −14,9 | 5/8 | [+0,04; +0,50] | NO |

**Ghép cặp theo seed (8 seed) — ZIL thắng tuyệt đối:**
| so sánh | ΔDD trung bình | ΔCalmar trung bình | ZIL tốt hơn |
|---|---|---|---|
| ZIL vs BTC, h0,5 | **+10,93pp** vs +4,74 | **+1,209** vs +0,261 | **8/8** |
| ZIL vs ETH, h0,5 | +10,93pp vs +4,53 | +1,209 vs +0,271 | **8/8** |
| ZIL vs BTC, h1,0 | **+13,91pp** vs +5,68 | **+1,538** vs +0,172 | **8/8** |
| ZIL vs ETH, h1,0 | +13,91pp vs +3,97 | +1,538 vs +0,056 | **8/8** |

**Chi phí:** ΣPnL giảm **−15,2 %** (h0,5) và **−30,4 %** (h1,0) — trong luật ≤ 50 %.
Phí: 1 416–1 580 USD (h0,5) / 2 832–3 159 USD (h1,0).

**Hedge PnL theo năm (USD trung bình/seed, h0,5):** 2021 **+730** · 2022 **+1 978** · 2023 **−5 905** ·
2024 **−9 875** · 2025 **−3 368** ⇒ chi phí nằm ở năm tăng, lợi ích dồn vào vài đợt sập (đúng cơ chế mong đợi).

**Tương quan ngày book ↔ coin:** ZIL **0,257** (BTC/ETH cùng cách đo ~0,26–0,28) — **không** cao hơn;
cái khác là **beta và độ nhạy pha sập**, không phải corr ngày.

## Đọc
- **ZIL cắt DD sâu hơn BTC/ETH rất nhiều cùng h**: h0,5 DD −11,6 vs −17,8/−18,0; h1,0 −8,6 vs −16,9/−18,6.
  ΔCalmar +1,21/+1,54 so +0,26/+0,27 ⇒ khác biệt **không phải nhiễu** (CI99 hẹp, 8/8 seed).
- Cơ chế hợp lý: screen chọn theo **corr với nhân tố alt (EW) 0,908** vs BTC 0,750 / ETH 0,829 ⇒ hedge bám
  đúng thứ book nắm (97 % alt), nên khi book sập theo alt thì hedge lãi.
- **Rủi ro phải nói rõ:** thanh khoản ZIL **11,9 M USD/ngày** (median) — nhỏ hơn BTC ~1 360×, ETH ~630×.
  Test giả định taker 0,05 % và **không mô phỏng impact**; với notional lớn, chi phí thực sẽ cao hơn ⇒
  **phải kiểm capacity trước khi coi là ứng viên thật**. Funding cũng bị bỏ qua (so sánh công bằng).

## Bước tiếp (chờ MASTER)
1. Pre-reg **xác nhận 1 lần** trên HO4 2026 với `h = 1,0` (winner) — cố định, không đổi trục.
2. Trước đó: đo **capacity/impact** cho quy mô thực (không đổi kết quả thăm dò này).
3. Không thử thêm coin khác trong họ này (đã là lần 3; thêm nữa là đốt ngân sách kiểm định).

**Bổ sung:** kiểm capacity/impact → `docs/result/BOOK_HEDGE_ALT_CAPACITY.md` (GO bền tới 25 bps ở h1,0).
