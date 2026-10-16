# PRE-REG — REX Bước 1: selector xếp hạng coin (MASTER 2026-10-16)

Thuộc `docs/plan/PLAN_REX.md`. Chỉ chạy sau khi Bước 0 PASS. Đầu vào là `~/claude_master/rex/panel.parquet`. **Không đọc dòng nào có day ≥ 2026-01-01.**

## Câu hỏi
Có thể xếp hạng các coin thanh khoản sao cho nhóm đầu thắng universe **ổn định**, tức thắng ở mọi năm DEV và được xác nhận ở VAL, sau khi trừ chi phí hay không?

## Model (cố định, KHÔNG tune)
- **LightGBM regression.** Target = `rk_h − 0,5`, tức rank % mặt cắt của lợi suất h ngày.
- **Feature:** bản rank `r_*` (bền theo thời gian), không dùng bản thô. Họ h (bối cảnh) KHÔNG đưa vào.
- **Tham số:**
  - num_leaves 15, min_data_in_leaf 500, learning_rate 0,03, 300 cây;
  - feature_fraction 0,7, bagging_fraction 0,7, bagging_freq 1, lambda_l2 10;
  - 3 seed (1, 2, 3), lấy trung bình dự báo.
- **Walk-forward:**
  - retrain theo quý: 2022Q1 … 2025Q4;
  - tập train = mọi dòng có day ≤ (ngày đầu quý − h − 1), tính từ 2021-03-01; mở rộng dần;
  - dự báo cho cả quý đó, toàn bộ là OOS.

## Biến thể (9; chọn trên DEV theo t-stat IC cao nhất)
| Mã | h | Feature |
|---|---|---|
| A1 / A3 / A7 | 1 / 3 / 7 | họ a–e (giá + volume) |
| B1 / B3 / B7 | 1 / 3 / 7 | a–f (+ taker) |
| C1 / C3 / C7 | 1 / 3 / 7 | a–g (+ funding/OI/LS) |

## Baseline
- IC của từng feature `r_*` đơn lẻ trên DEV. Dấu chọn theo DEV.
- Báo IC theo từng năm DEV. Feature đơn có |IC| lớn nhất là "baseline tốt nhất" của mỗi h.

## Thước đo (DEV = 2022-01-01 → 2024-12-31; VAL = 2025)
- **IC ngày** = Spearman(dự báo, y_h) trong universe.
  - Báo mean, t-stat Newey-West (lag = h), % tháng có IC tháng > 0, IC theo năm.
- **Decile:** lợi suất trung bình theo decile dự báo (kiểm đơn điệu).
- **Danh mục top-10:**
  - Chia vốn thành h tranche, mỗi ngày mua top-10 bằng 1/h vốn và giữ đúng h ngày (lợi suất ngày theo close).
  - Chi phí 0,10 %/chiều trên turnover thực. Funding thật.
  - Báo: excess so với universe EW, excess so với BTC, và lợi suất tuyệt đối.
  - Sharpe ngày × √365. maxDD. Theo năm.

## Gate GO cho biến thể thắng (phải đạt tất cả)
| # | Điều kiện |
|---|---|
| G1 | IC DEV mean > 0 và t (NW) ≥ 3 |
| G2 | IC > 0 ở cả 3 năm 2022, 2023, 2024 |
| G3 | ≥ 65 % số tháng DEV có IC > 0 |
| G4 | Top-10 excess vs universe, ròng, Sharpe DEV ≥ 1,0 và dương ở cả 3 năm |
| G5 | Nhìn VAL 2025 một lần: IC > 0 với t ≥ 2, và excess top-10 ròng > 0 |

**Ghi nhận thêm (không gate):**
- IC model so với IC của baseline tốt nhất. Nếu model không hơn ≥ 20 % thì Bước 2 dùng baseline đơn giản, vì đơn giản thì bền hơn.
- Top-10 vs BTC và lợi suất tuyệt đối: đây là đầu vào cho Bước 2a (regime), không gate ở Bước 1.

## Đầu ra đóng băng (nếu GO)
- `pred_s1.parquet` (day, sym, score) của biến thể thắng cho 2022–2025.
- Dự báo cho 2026 CHỈ được sinh ở Bước 4, bằng đúng quy trình này.
