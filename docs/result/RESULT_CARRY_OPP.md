# RESULT CARRY_OPP — carry funding theo cơ hội, delta-neutral (MASTER 2026-10-16)

- Pre-reg: `docs/prereg/PREREG_CARRY_OPP.md` (116de7e3).
- Addendum 1 (4506e522): viết TRƯỚC khi có outcome.
- Code: `research/carry/co_data.py`, `co_bt.py` (addc2a30), `co_diag.py`.
- Output: `~/claude_master/1016/carry/carry_opp_result.json`.

## Kiểm dữ liệu

| Mục | Kết quả |
|---|---|
| C1 | PASS. Funding BTC trung bình 11,9 %/năm, so với 11,6 % ở nghiên cứu 08-31 |
| C2 | PASS sau addendum 1: 99,74 %. Đã loại 17 symbol bị delist hoặc ticker bị tái dùng |
| Phạm vi | 410 symbol có cả spot lẫn perp, dữ liệu 2021-01 → 2026-09 |

## Kết quả

Luật cố định: s > 0,01 %/8h tính trung bình 30 ngày; tối đa 10 cặp; phí khứ hồi 0,30 %.

| Run | CAGR | Sharpe | maxDD | Thời gian có vị thế | Số thanh lý | Theo năm (%) |
|---|---|---|---|---|---|---|
| DEV chính (vốn ×2,0) | +5,58 % | 5,80 | −0,32 % | 57 % | **3** | 2021: +19,6 · 2022: −0,1 · 2023: +2,5 · 2024: +7,2 · 2025: **−0,05** |
| DEV vốn ×1,5 | +7,12 % | 5,62 | −0,61 % | 57 % | 17 | 2021: +26,0 · 2022: −0,1 · 2023: +2,9 · 2024: +9,3 · 2025: −0,4 |
| DEV maker 0,15 % | +5,98 % | 6,25 | −0,28 % | 57 % | 3 | 2025: +0,3 |
| DEV bỏ top-30 (universe độc lập) | +5,57 % | 5,48 | −0,60 % | 55 % | 3 | gần như trùng bản chính |
| **HO 2026** | **−0,12 %** | −1,00 | −0,14 % | 27 % (TB 1 cặp) | 0 | 2026: −0,1 |

- Tương quan theo ngày với hệ mua đáy: **0,06**.
- Trong 4 tháng hệ mua đáy không có lệnh nào, carry cộng dồn −0,3 %. Tổng cả kỳ là +13,6 %.

## Gate

| Gate | Kết quả |
|---|---|
| G1 | ✅ |
| G2 | ✅ |
| G3 | ✅ |
| G4 HO 2026 > 0 | ❌ |
| G5 | ✅ |
| G6 0 thanh lý ở vốn ×2,0 | ❌ (3 lần) |

⇒ **NO-GO.**

## Đọc

1. **Edge chỉ có ở quá khứ.**
   - 2021 đóng góp gần hết lợi nhuận DEV.
   - 2024 có lời (+7,2 %), nhưng 2025 ≈ 0 và HO 2026 ≈ 0.
   - Kết quả khớp với kết luận 08-31: funding đã bị nén. Một nguyên nhân cấu trúc nhiều khả năng là các sản phẩm delta-neutral quy mô lớn (kiểu stablecoin dựa trên funding, từ 2024) đứng phía short perp, hút hết phần funding. Đây là suy luận, chưa kiểm.
   - Bản "theo cơ hội" không né được hiện tượng nén này.
2. **Rủi ro chân short là thật.**
   - Ngay cả với margin bằng 100 % notional, kiểm lại mỗi ngày, vẫn có 3 lần thanh lý do pump mạnh trong ngày.
   - Ở vốn ×1,5 số lần thanh lý lên 17.
   - Sharpe 5–6 và maxDD dưới 1 % là hình ảnh của mô phỏng theo nến ngày. Nó không tính slippage khi vào/ra hai chân trên alt, cũng không tính trượt giá lúc bị thanh lý.
3. Chỉ có hai điểm đạt: tương quan thấp (0,06) và universe độc lập (G3). Hai điểm này không cứu được việc lợi nhuận hiện tại ≈ 0.

**Kết luận: ĐÓNG hướng carry (cả thường trực lẫn theo cơ hội) trên Binance.** Ledger +1.
