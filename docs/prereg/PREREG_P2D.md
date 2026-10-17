# PRE-REG — P2-D: chẩn đoán offline "điểm REX S1 trên các lệnh sim của K24+skipFull" (MASTER 2026-10-17)

**Mục tiêu.** Kiểm xem các lệnh K24 vào những coin mà selector REX S1 xếp hạng thấp có lãi kém hơn rõ rệt hay không.

**Phạm vi:**
- Chỉ đọc dữ liệu, KHÔNG sửa logic hệ cũ, KHÔNG đụng shadow 242 (owner 10-17).
- Kết quả tốt cũng chỉ mở đường sang Bước B: sim có veto với key mặc định tắt, 8 seed, sau đó HO 2026 một lần, rồi shadow.
- Owner yêu cầu "tỉ mỉ, tránh NO-GO trên phân tích mỏng". Vì vậy file này khai trước đủ các phép kiểm độ bền (seed, model, năm, vol, loại lệnh), không chốt chỉ dựa trên một con số.

## Dữ liệu
**Lệnh K24+skipFull** từ 8 seed: `~/kaggle_sim/out/gqsf-{a1,s7,s13,s21,s99,s123,s777,s2024}/storage/printDone.csv`.
- Jar `0944841c`, 2021-07 → 2025-12, khoảng 3 541 lệnh mỗi seed.
- Seed **A1 là chính**, 7 seed còn lại dùng kiểm độ bền.

**Múi giờ: đã kiểm, KHÔNG phải UTC.**
- Cột `start` của sim ở **UTC+7**. Giá vào lệnh khớp chính xác close nến 1m Vision tại `start − 7h`, ở 8/8 mẫu (vd OMG 1,659; MKR 848,8).
- ⇒ thời điểm vào (UTC) = `start − 7h`.
- Ngày UTC vào lệnh là D. Điểm REX dùng là điểm của **ngày D−1**, vì điểm ngày d đã tính bằng close d lúc 24:00 UTC, trước mọi lệnh trong ngày D. Không có lookahead.

**Điểm REX:** `~/claude_master/rex/pred_s1_{C1,C3,C7}.parquet`, walk-forward OOS 2022–2025.
- **C1 là chính**; C3 và C7 dùng kiểm độ bền.
- r = percentile của score trong universe REX ngày D−1. Score cao nghĩa là coin được xếp hạng tốt.

**Bucket:** Q1 (r < 0,2, nhóm REX xếp thấp nhất), Q2 … Q5, và NA (coin không nằm trong universe REX ngày đó: thanh khoản < 20M hoặc niêm yết < 60 ngày).

**Thước đo mỗi lệnh:**
- `profit` = ROI % trên margin, cột của sim; corr với pnl/margin = 0,997.
- Tổng `pnl` ($).
- Win rate, tỷ lệ STOP_LOSS.

## Kỳ
- DEV: lệnh có ngày UTC vào trong 2022-01-01 → 2024-12-31.
- VAL: năm 2025.
- 2021 không có điểm REX nên bỏ.

## Thống kê chính
**Δ = mean profit(Q1) − mean profit(Q2…Q5)**, đo trên DEV, seed A1, model C1.
- CI 95 % bằng bootstrap theo **cụm ngày UTC vào lệnh**: 5000 lần lặp, seed 1017.
- Lý do gom cụm: lệnh vào theo đợt (burst), nhiều lệnh cùng phút.

## Gate để sang Bước B (phải đạt TẤT CẢ)
| # | Điều kiện |
|---|---|
| G1 | Δ DEV < 0 và cận trên CI 95 % < 0 |
| G2 | Δ < 0 ở mỗi năm 2022, 2023, 2024 |
| G3 | VAL 2025: Δ < 0 |
| G4 | Σpnl DEV của các lệnh Q1 < 0, tức bỏ chúng đi thì cộng thêm tiền (xấp xỉ, chưa tính việc nhả slot cho lệnh khác) |
| G5 | Độ bền seed: Δ < 0 ở ≥ 7/8 seed, và cận trên CI < 0 ở ≥ 6/8 seed |
| G6 | Không chỉ là vol: chia DEV theo tercile `r_vol30` của ngày D−1, Δ (Q1 so với phần còn lại) < 0 ở ≥ 2/3 tercile |

**Mô tả kèm (không gate):**
- Kết quả theo C3 và C7.
- Theo loại lệnh (PREDICT_SYMBOL_TRADE / BIG_DOWN / DCA_LEVEL1).
- Bucket NA.
- Một veto đơn giản thay thế (top-quintile `r_vol30`) để so sánh.
- Thứ tự đơn điệu Q1 → Q5.

**Kết luận theo gate:**
- G1–G5 đạt nhưng G6 trượt: ghi nhận "giá trị đến từ vol". Bước B khi đó thử veto vol đơn giản thay vì REX.
- G1 trượt: đóng, kèm toàn bộ bảng mô tả để owner thấy chi tiết. Không kết luận chỉ từ một con số.

## Kiểm dữ liệu
- **P2D-V1:** chọn ngẫu nhiên 20 lệnh, khớp giá vào với 1m Vision tại `start − 7h`. Phải ≥ 19/20 khớp (sai số ≤ 1e-9 tương đối).
- **P2D-V2:** ≥ 85 % lệnh DEV có bucket khác NA. Nếu thấp hơn, báo và vẫn chạy.
- **P2D-V3:** assert ngày điểm REX < ngày UTC vào lệnh.
