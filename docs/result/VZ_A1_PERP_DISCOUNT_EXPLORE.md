# VZ A1 — perp discount / perp-led flush tại tick vào đợt — KHÁM PHÁ 2022 + 2024 (MASTER 2026-10-16)

- **Pre-reg:** `docs/prereg/PREREG_VZ_A1_PERP_DISCOUNT.md`, commit c4de0684, có addendum 1 (4e5816d0) viết trước khi tính outcome.
- **Code:** `research/vz/a1/` gồm `a1_build.py`, `a1_kernel_body*.py` (Kaggle `chuyendinh/vz-a1-feat` v3) và `a1_test.py`.
- **Output:** `~/claude_master/1016/a1/out/a1_test_a1.json`.

**Dữ liệu chấm:** sim gqsf-a1, 69 đợt (mỗi đợt ≥ 6 chân, không tính lệnh DCA), tổng 957 chân.

**Kiểm dữ liệu — PASS:**
- V1 (causal): đạt.
- V2 (khớp giá): 100 % chân khớp.
- V3 (sửa theo addendum 1): corr lag 0 = 0,514, lớn nhất trong các lag.
- V4 (độ phủ): 100 %.

## Kết quả 4 phép thử (ledger 54 → 58): KHÔNG có ứng viên, cũng không có tín hiệu yếu

Cả 4 phép thử đều có CI95 chứa 0, và dấu theo năm không nhất quán.

| T | Feature | Tầng | IC | CI95 | CI Bonferroni | 2022 / 2024 | Spread (thấp − cao) |
|---|---|---|---|---|---|---|---|
| T1 | F1 prem_dis | Đợt | −0,048 | [−0,249; +0,159] | [−0,310; +0,211] | +0,020 / −0,128 | +0,009 |
| T2 | F2 perp_lead60 | Đợt | +0,061 | [−0,110; +0,236] | [−0,144; +0,290] | +0,113 / +0,018 | −0,041 |
| T3 | F1 | Trong đợt | +0,001 | [−0,085; +0,071] | [−0,107; +0,086] | −0,105 / +0,061 | +0,003 |
| T4 | F2 | Trong đợt | −0,027 | [−0,086; +0,041] | [−0,097; +0,057] | −0,091 / +0,009 | +0,005 |

⇒ Không có quan hệ đơn điệu nào giữa premium dislocation hay perp-lead với PnL của đợt, ở cả tầng đợt lẫn tầng chọn trong đợt.

## Mô tả (không chấm): đuôi phải của F1

- Phân vị F1 của đợt: q50 −0,04 %, q90 +0,12 %, q95 +0,27 %.
- Có 3 đợt với F1 > 0,4 %. Cả 3 thuộc 2022 và đều là ngày sụp đổ hệ thống. Lúc đó perp giao dịch **cao hơn** index, tức spot rơi nhanh hơn perp: sụp đổ do spot dẫn.

  | Thời điểm (UTC) | Sự kiện | Số chân | ret | PnL | F1 |
  |---|---|---|---|---|---|
  | 2022-05-05 15:09 | LUNA | 18 | −34,2 % | −4 349 | +0,68 % |
  | 2022-11-08 18:05 | FTX | 18 | −14,9 % | −1 606 | +0,71 % |
  | 2022-11-08 04:13 | FTX | 11 | −1,5 % | −125 | +0,61 % |

- So sánh: 3 đợt này cộng lại PnL −6 080, ret trung bình −16,9 %. 66 đợt còn lại PnL +32 704, ret trung bình +4,1 %.
- **Đây là quan sát sau khi nhìn dữ liệu, n = 3 và chỉ trong một năm.** Nó KHÔNG được tính là kết quả.
  - Có một khả năng gây nhiễu: tháng 11/2022, giá của FTX nằm trong rổ index của Binance. Index có thể đã méo do chính sự kiện FTX, không phải do cơ chế "spot dẫn".
  - Muốn coi là kết quả thì phải xác nhận trên năm chưa dùng (`PREREG_VZ_A1_TAIL_CONFIRM.md`).

## Đọc

- Giả thuyết đơn điệu "perp càng discount thì đợt càng tốt" bị bác ở mức khám phá.
- Còn một giả thuyết hẹp hơn: veto đuôi phải, khi perp > index rõ rệt (spot dẫn sụp đổ). Giả thuyết này được đưa sang xác nhận độc lập, với ngưỡng cố định 0,4 % đặt trước khi mở năm lẻ.
