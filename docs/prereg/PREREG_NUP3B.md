# PREREG NUP3b: sleeve cỡ nhỏ theo iso-DD và luật symbol triển khai được (MASTER 2026-10-27)

## 1. Lý do
NUP3 Pha 1 (commit 48a9eea7, ADDENDUM (c) 40c706bb):
- **V0:** cụm ×1,82, ΣPnL ×1,62, maxDD −36,3 %.
- **V1:** cụm ×1,71, ΣPnL ×1,58, maxDD −35,0 %.
- Cả V0 và V1 qua G1 + G2 nhưng TRƯỢT G3 (ngưỡng −32 %).
- **V2** chết ở G1.
- Sleeve có ROI_stress +2,1 %/lệnh, và 4/4 seed dương.

Ước lượng tuyến tính: muốn maxDD median = −30 % thì size sleeve s* là:
- V0: s* = 0,525 ⇒ cụm ×1,82, PnL ×1,33.
- V1: s* = 0,574 ⇒ cụm ×1,71, PnL ×1,33.

Số lệnh hầu như không phụ thuộc size, nên giảm size sleeve có thể giữ được mục tiêu của owner (lệnh số 1) mà vẫn nằm trong G3.

Quy tắc chọn s: s* được chọn bằng luật iso-DD đã khai trong NUP2 §4, chỉ dựa vào DD. Không chọn theo PnL, không tune lại. Phải kiểm lại bằng sim.

Rủi ro triển khai: overlap 41–48 % (sổ nền mở cụm trên symbol sleeve đang giữ). Trên sàn chế độ one-way, hai vị thế cùng symbol sẽ gộp làm một. Phải đo một biến thể triển khai được.

## 2. Arm (chốt, 3 arm, cùng jar `sim-jar-nup3-sleeve`)
Thêm key `BASE_SKIP_SLEEVE_SYMBOLS`, mặc định false. Code mới, TẮT thì byte-identical.

| Arm | Cấu hình |
|---|---|
| S0b | V0 + `SLEEVE_SIZE_MULT=0.525` |
| S1b | V1 + `SLEEVE_SIZE_MULT=0.574` |
| S1x | S1b + `BASE_SKIP_SLEEVE_SYMBOLS=true`: sổ nền KHÔNG mở cụm mới trên symbol sleeve đang giữ. Đây là biến thể triển khai được trên one-way; sổ nền sẽ đổi so với B0. |

## 3. Thực thi
1. Code `BASE_SKIP_SLEEVE_SYMBOLS` + unit test.
   - Cổng G-OFF: cờ tắt ⇒ printDone trùng byte với NUP3 V1 cùng seed (s7).
   - Cổng G-INV cho S0b và S1b: lọc bỏ sleeve thì phần còn lại trùng byte B0 (a1).
2. **Pha 1:** 3 arm × 4 seed (a1, s7, s21, s99).
3. **Pha 2:** arm qua G1–G3 ở Pha 1 ⇒ thêm 4 seed DEV + 8 seed HO.
   - Tối đa 2 arm. Ưu tiên arm triển khai được (S1x) nếu nó qua; arm còn lại lấy cụm/năm cao nhất.

## 4. Thước đo và luật
- Thước đo giữ nguyên PREREG_NUP3 §5 và diễn giải MASTER (U = notional@mark/equity MTM; báo margin@entry và số leg bị từ chối; overlap; N_eff).
- Kỳ DEV 2022–25. Equity tính từ 2021-07 (gồm 2021H2, theo ADDENDUM (c)). Không có V2, nên không cần niêm phong 2021H2.
- Luật G1–G4: giữ nguyên PREREG_NUP3 §6, ngưỡng không đổi. Riêng S1x thì "×B0" so với B0 cùng seed (sổ nền đã đổi).
- Báo thêm cho S1x (mô tả):
  - số cụm nền bị bỏ vì trùng symbol;
  - PnL của số cụm đó trong B0 (chi phí cơ hội).
- Kiểm s*: maxDD median sim thực tế lệch so với −30 % quá 3 điểm % ⇒ ghi "iso-DD tuyến tính không giữ", nhưng KHÔNG chỉnh lại s. Chấm theo đúng số thực.
- GO = ứng viên v1.3, cần forward/paper shadow ≥ 4 tuần. Không đổi v1.1/v1.2 trước D 12-08.
- Trial ledger họ NUP: +3. Không thêm arm, không đổi s hay ngưỡng sau khi thấy số.

## 5. Giới hạn
- s* hiệu chỉnh trên 1 cú sập (2022-05).
- Throttle sleeve phi tuyến: size nhỏ hơn ⇒ U_s thấp hơn ⇒ throttle bớt chặn.
- HO 2026 đã dùng ở NUP và S0 cho các tập liên quan. Đây là lần thứ 3, ghi ledger.
- Sim chưa mô hình sàn từ chối lệnh khi margin@entry > equity. Số leg bị ảnh hưởng ở Pha 1 NUP3 ≤ 0,4 %.
