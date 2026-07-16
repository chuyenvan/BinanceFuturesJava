# REPORT — Sizing sweep + Model sweep (2026-07-11, đêm)

## A. SIZING SWEEP (v4 ret2 + giveback 1.0) — bác thang năm/6tháng/quý

| NUMBER_ORDER_BUDGET | $/lệnh | CAGR | maxDD | năm+ | 6th+ | quý+ |
|---|---|---|---|---|---|---|
| 50 (baseline) | 700 | 3.2% | 0.5% | 4/6 | 7/11 | 9/22 |
| 35 | 1000 | 3.9% | 0.7% | 4/6 | 7/11 | 9/22 |
| 25 | 1400 | 4.2% | 0.9% | 4/6 | 7/11 | 9/22 |
| 15 | 2333 | 2.6% | 4.2% | 3/6 | 6/11 | 8/22 |
| 10 | 3500 | 4.8% | 1.5% | 4/6 | 7/11 | 9/22 |

**KẾT LUẬN — giả thuyết "sizing là đòn bẩy 20%/năm" SAI (rút lại).** Sizing gấp 5 chỉ nâng CAGR
3.2%→4.8%, không đâu gần 20%. Bằng chứng quyết định: **maxDD gần như không đổi (<2%) khi size gấp 5**
→ phần lớn vốn vẫn nằm không → hệ **bị giới hạn bởi SỐ CƠ HỘI TRADE, không phải size**. 13/22 quý = +0.0
(không trade gì). Vốn nhàn rỗi vì **không có kèo để vào**, không phải vì lệnh nhỏ.

Điểm gãy ở NB=15: 2025 âm (−2%), maxDD vọt 4.2% — tăng size làm lệnh xấu lỗ nặng hơn mà không thêm
lệnh tốt. → Gốc bệnh là **tầng tín hiệu (thưa cơ hội)**, chỉ model/feature/label mới sửa được.

## B. MODEL SWEEP (45 combo backtest-lite, 5 kernel Kaggle)

**CẢNH BÁO:** backtest-lite có bug compound → CAGR_lite nổ mũ (11 triệu %), **con số tuyệt đối VÔ NGHĨA,
chỉ dùng THỨ HẠNG tương đối** (cùng bug, so được). Xếp theo metric bền (%fold dương + return/lệnh/bước):

| combo | %fold+ | ret/bước | ghi chú |
|---|---|---|---|
| **0.01\|72h\|pump** | **6/6** | 3.60% | ứng viên #1 |
| 0.01\|24h\|pump | 6/6 | 1.57% | |
| 0.01\|72h\|oi | 5/6 | 3.23% | |
| 0.03\|72h\|oi | 5/6 | 2.57% | |
| baseline 0.02\|12h\|oi (ret2) | 3/6 | 0.39% | đang dùng |

**Ba tín hiệu hội tụ:** (1) horizon **72h** thắng áp đảo (baseline 12h thua); (2) feature-set **pump**
(oi×taker, ls-skew — giả thuyết "hàng được pump giữ thanh khoản") có giá trị thật; (3) label lỏng
**0.01** thắng (bắt nhiều kèo hơn → đúng thuốc cho bệnh "thưa cơ hội").

## C. Hành động đang chạy
- Kernel `selector-wf-pred-cand` (RET_WIN=0.01 + pump features, WF leak-free) đang sinh predict_wf.
- Bước tiếp: build `wfo_dataset_v5` (WFO_SEL_HORIZON_IDX=3 cho 72h) → Java sim full-history + bậc thang,
  so với ret2 (v4). Chỉ Java mới xác nhận vì backtest-lite lạc quan + buggy.

## D. Bức tranh chiến lược cập nhật
1 năm dương: gần đạt (4/6 năm, 2 năm trống là 2021-2022 thiếu data gate/pred). 6 tháng: 7/11. Quý: 9/22.
Đòn bẩy để siết bậc thang xuống 6th/quý = **tăng số quý CÓ trade**, chỉ model tốt hơn làm được. Ứng viên
`0.01|72h|pump` tấn công đúng chỗ này. Sizing/exit/giveback đã cạn (đều không tạo thêm cơ hội).
