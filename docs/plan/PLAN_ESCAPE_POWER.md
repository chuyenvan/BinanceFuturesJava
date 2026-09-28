# PLAN_ESCAPE_POWER — Lối thoát nút thắt "THIẾU POWER" (owner 28/09 15:45)

## 0. Nút thắt (đã đo, không tranh luận lại)
`MDE(ΔCAGR) = 3,6–19pp` vs cải thiện thật `1,7–5,4pp`; `N_eff ≈ 76 tuần`; edge dồn **~9 đợt**; 1 cửa sổ 5 tuần = **41–44%** lãi năm 2025.
Phân loại 50 vòng: **20% NULL-có-thông-tin · 28% xấu có ý nghĩa · 30% THIẾU POWER · 14% loại bằng luật**.
⇒ **Chạy thêm vòng trên cùng 4,5 năm = không thêm thông tin.**

## 1. BA LỐI THOÁT (owner đề xuất) + ĐÁNH GIÁ
| # | lối thoát | đánh giá của em |
|---|---|---|
| **L1** | Không trông chờ gom thêm **thời gian** | ✔ ĐÚNG — thêm năm của **cùng thị trường** không tạo sự kiện độc lập |
| **L2** | **Chuyển trục kiểm định: tầng TIỀN → tầng VI MÔ/TÍN HIỆU** (Rank-IC · Top-decile Lift · Winrate cửa sổ cố định · **PnL/lệnh chuẩn hoá theo Volatility**) | ✔ ĐÚNG và **rẻ nhất** — làm được ngay trên artifact có sẵn; mật độ mẫu ~13.900 tick thay vì vài chục |
| **L3** | **Alpha tần suất cao** (funding/differential · mean-reversion ngắn hạn) để tự tích `N_eff` mỗi tuần | ✔ ĐÚNG về nguyên lý — nhưng là **dòng nghiên cứu mới** (pre-reg riêng + dữ liệu funding có sẵn) |

## 2. BỔ SUNG CỦA OWNER (quan trọng nhất về mặt KỸ THUẬT)
> *"mở rộng entry bằng thay lưới **5m hoặc 1m** nhưng cần chiến lược pred tốt mới đủ không gian lưu dữ liệu và chạy. **kiểu pass gate đủ thấp thì mới pred selector và s1**"*
⇒ Đây chính là **CASCADE (lọc rẻ trước, dự đoán đắt sau)**:
`gate (rẻ) → chỉ ứng viên ĐẠT mới chạy selector + S1 (đắt)`
- Đây là **cách phá chặn nhịp** đã đo 27/09: `checkMarketLevelChange2Trade()` tốn **~2m48s/lượt** vì chạy **toàn bộ prep + S1 cho mọi coin**; nếu đảo thành cascade thì **tick rẻ hơn nhiều lần** ⇒ **1m/5m mới khả thi**.
- Cũng **giảm tải lưu trữ** (`predictionSymbol`/`prediction` chỉ ghi cho ứng viên đạt) — vấn đề đĩa 93%.

## 3. TRIỂN KHAI (thứ tự thực thi)
| # | việc | trạng thái |
|---|---|---|
| **W1** | **CASCADE (gate-first, lazy S1/selector)**: thiết kế + đo lại **chi phí/tick** ⇒ xác định nhịp khả thi (1m? 5m?) | 🔄 chạy ngay (dev, parity, KHÔNG deploy) |
| **W2** | **Bộ thước TẦNG ENTRY** (L2): pre-reg + hiện thực `rank-IC` · `top-decile lift` · `winrate` cửa sổ cố định · **`PnL/lệnh ÷ volatility`** ⇒ chấm lại các đối tượng/feature đang có | 🔄 chạy ngay (offline, rẻ) |
| **W3** | **Sleeve tần suất cao** (L3): funding/differential + mean-reversion ngắn hạn — khảo sát nguồn dữ liệu + pre-reg | ⏸️ sau W1/W2 |

## 4. NGUYÊN TẮC GIỮ NGUYÊN
Không push file dữ liệu · DEV ≤2025-12-31 (2026 = holdout) · pre-reg TRƯỚC khi đọc số · **đo ở tầng dày, cổng quyết định bằng 2 rào XÁC ĐỊNH (a)/(b′)** (không cần power) · không chạm ONNX/LIVE khi chưa duyệt.
