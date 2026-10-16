# PRE-REG (xác nhận) — A1-TAIL: veto đợt khi perp > index (spot dẫn sụp đổ) (MASTER 2026-10-16)

- **Nguồn giả thuyết.** Đây là quan sát mô tả SAU khi nhìn dữ liệu khám phá A1 2022 + 2024 (`docs/result/VZ_A1_PERP_DISCOUNT_EXPLORE.md`). Có 3 đợt mang F1 > 0,4 %: LUNA và FTX ×2. PnL của 3 đợt này −6 080, trong khi 66 đợt còn lại +32 704.
- **Vì giả thuyết sinh ra trong mẫu,** dữ liệu 2022 + 2024 KHÔNG được dùng làm bằng chứng. Chỉ chấm trên năm chưa mở.
- File này commit TRƯỚC khi chạy kernel feature cho các năm 2021, 2023, 2025.

## Luật (cố định, không tune)

- Một đợt gồm các chân cùng phút `start` (UTC), có ≥ 6 chân, không tính lệnh `DCA_LEVEL1`. Sim `gqsf-a1`.
- F1 của chân lấy đúng định nghĩa trong `PREREG_VZ_A1_PERP_DISCOUNT.md`: prem_close[b] − trung vị prem_close trong cửa sổ [t0 − 1440′, t0 − 60′].
- F1 của đợt = trung vị F1 các chân.
- **Cờ veto** = F1 đợt > **0,004**. Ngưỡng này lấy từ khám phá và ghi rõ như vậy. Không thử ngưỡng nào khác.

## Dữ liệu xác nhận

- **DEV năm lẻ 2021, 2023, 2025:** chưa từng chấm outcome A1 trên các năm này. Đây là thước chính.
- **HO 2026:** sim K24 + skipFull trên Vision 2026-01 → 09. Chọn run tương đương gqsf-a1 (seed A1/a1 nếu có, nếu không thì s42). Run được ghi trong result trước khi ghép outcome. Phần này chỉ báo cáo.
- **Backcast 2020:** vẫn niêm phong, không dùng trong file này.

## Tiêu chí (năm lẻ gộp)

Gọi n_flag là số đợt bị gắn cờ.

| Kết luận | Điều kiện |
|---|---|
| **XÁC NHẬN** | n_flag ≥ 2, **và** ΣPnL đợt cờ < 0, **và** ret TB đợt cờ < ret TB đợt không cờ − 0,05, **và** tỉ lệ đợt bị cờ ≤ 10 % |
| **KHÔNG KẾT LUẬN** | n_flag < 2. Luật hiếm khi kích hoạt; ghi nhận lại nếu luật có kích hoạt thì nó đã giúp hay đã hại |
| **BÁC BỎ** | Còn lại, tức là có ≥ 2 đợt cờ nhưng không thỏa đủ các điều kiện của dòng XÁC NHẬN |

Báo kèm:
- danh sách đợt cờ, gồm thời điểm, số chân, ret, PnL, F1;
- tỉ lệ đợt cờ theo từng năm;
- phần PnL bị bỏ (= −ΣPnL đợt cờ) so với ΣPnL các đợt ≥ 6 chân.

## Kiểm dữ liệu

V1–V4 giống A1, với V3 theo addendum 1 (lag 0 lớn nhất và > 0,3). FAIL thì dừng.

## Bước sau (chỉ khi XÁC NHẬN)

Viết pre-reg riêng cho luật sim với key mới. Key mặc định TẮT để byte-identical, đo trên 8 seed DEV (CAGR22, maxDD MTM, Calmar, UW), sau đó HO 2026. Ghi rõ: luật chỉ chặn các đợt hiếm, nên CAGR thay đổi ít, còn tác dụng chính là ở đuôi lỗ.
