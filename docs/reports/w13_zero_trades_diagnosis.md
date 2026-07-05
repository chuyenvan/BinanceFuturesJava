# Mổ w13 — vì sao OOS 2025Q2 ZERO_TRADES (cả vế A lẫn D, mọi seed) — 2026-07-06

**Ca:** w13 OOS = 2025-04-01→2025-07-01. IS_fit=2.84 (dương, train tốt) nhưng OOS=ZERO_TRADES ở A, D, seed42, seed142.

## Phương pháp
Tool `W13Diagnose` (không chạy sim) đọc dataset offline, tái hiện CHÍNH XÁC 2 cổng sinh entry của
`SimulatorMarketLevelTicker1MStopLoss`, đếm theo tháng 2025. KHÔNG đoán — đo trực tiếp.

## Kết quả (dataset wf, market=2.80M pred=2.82M funding=2.76M — phủ 100%)
| tháng | tickMkt | tickPred | funding | bigDown@−0.0316 | minDown | avgDown |
|---|---|---|---|---|---|---|
| 2025-01 | 43973 | 43973 | 43973 | 0 | −0.0269 | −0.0011 |
| 2025-02 | 40131 | 40131 | 40131 | **4** | −0.0945 | −0.0013 |
| 2025-03 | 44364 | 44364 | 44364 | 0 | −0.0220 | −0.0013 |
| **2025-04** (OOS) | 42923 | 42923 | 42923 | **0** | −0.0209 | −0.0015 |
| **2025-05** (OOS) | 44430 | 44430 | 44430 | **0** | −0.0293 | −0.0015 |
| **2025-06** (OOS) | 42903 | 42903 | 42903 | **0** | −0.0304 | −0.0012 |

Quét ngưỡng (số tick BIG_DOWN theo gene range):
| tháng | <−0.020 | <−0.0316 | <−0.045 | <−0.055 |
|---|---|---|---|---|
| 2025-04 | 1 | 0 | 0 | 0 |
| 2025-05 | 4 | 0 | 0 | 0 |
| 2025-06 | 1 | 0 | 0 | 0 |

## CHẨN ĐOÁN (nguyên nhân gốc)
1. **Data KHÔNG thiếu** — pred + funding phủ 100% mọi tháng 2025Q2. Loại bỏ giả thuyết "thiếu coverage".
2. **Thị trường 2025Q2 quá phẳng:** avgDown ~−0.0013, minDown cả quý không chạm nổi −0.0316. Đây là 3 tháng
   đi ngang/tăng nhẹ — KHÔNG có cú sụt thị trường nào.
3. **`OFF_FLAT_HARD=true` giết 4/5 nhánh entry market-level** (BIG_UP, SMALL_UP, SMALL_DOWN_15M off cứng),
   chỉ còn **BIG_DOWN** sống: `rateDownAvg < MS_DOWN_BIG_AVG` (gene [-0.055,-0.020]). Cả gene range đều cho
   **0 tick** BIG_DOWN ở 2025Q2 (kể cả cận lỏng nhất −0.020 chỉ 1-4 tick/tháng — không đủ trade).
4. ⇒ **Market-signal entry chết sạch cả quý.** Nhánh PREDICT_SYMBOL_TRADE cũng cần `levelChange`-driven DCA +
   qua gate; với market phẳng + no big-down, không cụm nào mở → ZERO_TRADES.

## Vì sao khớp MỌI triệu chứng
- ZERO bất kể seed (42/142): thị trường phẳng độc lập random-search. ✔
- ZERO ở cả A lẫn D: độc lập pred-model (nguyên nhân là market rateDownAvg, không phải pred). ✔
- IS_fit dương: 12 tháng IS (2024-04→2025-03) CÓ tháng biến động (2025-02 có 4 tick big-down) → train được. ✔
- OOS ZERO: 3 tháng OOS trúng đúng vùng đi ngang. ✔

## Ý NGHĨA CHIẾN LƯỢC (vượt xa w13)
**Đây KHÔNG phải bug — là ĐẶC TÍNH thiết kế: chiến lược chỉ vào lệnh khi thị trường sụt (BIG_DOWN mua-đáy).**
Khi thị trường đi ngang/tăng đều (như 2025Q2), hệ ĐỨNG NGOÀI hoàn toàn. Hệ quả trực tiếp cho WFE ~0.24:
- WFE thấp KHÔNG phải vì strategy "kém" — mà vì nhiều window OOS rơi vào regime không-có-tín-hiệu (đi ngang),
  IS lại giàu tín hiệu (có sụt) → PnL_OOS/PnL_IS thấp là hệ quả REGIME MISMATCH, đúng như seed-noise gợi ý.
- `OFF_FLAT_HARD` cắt hết nhánh non-BIG_DOWN làm hệ CHỈ kiếm tiền ở regime sụt — đây là nút thắt strategy layer
  cụ thể nhất: hệ không có cách kiếm tiền ở thị trường đi ngang/bull đều.

## Hướng kế (đề xuất, Uni quyết)
1. **Kiểm regime mismatch toàn bộ 17 window:** đếm bigDown-tick mỗi window OOS vs IS → xác nhận WFE thấp tương
   quan với thiếu-tín-hiệu-OOS (không phải overfit tham số). Nếu đúng → WFE không phải thước đo "chất lượng model"
   mà là "may rủi regime của cửa sổ".
2. **Cân nhắc mở lại một nhánh non-BIG_DOWN** (SMALL_DOWN_15M?) để hệ có tín hiệu ở thị trường phẳng — NHƯNG
   đây là thay đổi chiến lược PnL-impacting, cần Uni quyết + đo A/B.
3. Economic rationale giờ rõ hơn: "hệ kiếm tiền khi thị trường sụt, người bán tháo hoảng loạn bán rẻ, hệ mua đáy".
   Câu hỏi mở: regime sụt chiếm bao nhiêu % thời gian? Nếu ít (như 2025Q2 = 0) thì hệ đứng ngoài phần lớn thời gian.
