# SENSITIVITY GENE — TASK-111 (B) — kết quả + đề xuất cắt gene

> **Mục tiêu:** đo độ nhạy từng gene tới hàm mục tiêu (HPOFitnessCalculatorV4.finalFitness), cắt gene
> phẳng để đưa genome HPO từ 26 → ~12 gene mà chất lượng giảm trong mức chấp nhận.
>
> **Phương pháp:** OAT (one-at-a-time). Baseline = giá trị Configs hiện tại (finalFitness = **1.51966**,
> FAST 2024-01→2026-06, ~2.5 năm). Mỗi gene quét 4 mức trong range hợp lý, giữ 25 gene kia ở baseline,
> đo dao động fitness (range = max−min). **range lớn = quan trọng (giữ); range ~0 = phẳng (cắt).**
>
> **Đọc range:** range cỡ 10^5 = gene vặn sai đẩy vào REJECT (vi phạm constraint cứng → fitness âm sâu)
> = gene CỰC quan trọng (giữ chắc). range 0.x = nhạy vừa. range 0.000 = phẳng tuyệt đối (cắt).
>
> **Chạy:** Oracle (gene 0-8, 17-21) + 226 (gene 9-16, 22-25). Kaggle bỏ (kernel rơi vào nhánh HPO
> đọc file kaggle_data_hpo/*.bin — không phải đường backtest; không hợp cho việc này).
>
> **HẠN CHẾ:** OAT bỏ qua tương tác gene (gene phẳng đơn lẻ có thể nhạy khi kết hợp). Là bước SÀNG
> trước HPO, không phải kết luận tuyệt đối. Hàm mục tiêu dùng V4 hiện tại (chưa vá ổn-định-thời-gian).

---

## BẢNG SENSITIVITY (điền dần — cập nhật 2026-06-26 23:35, 6/26 gene xong, 2 máy ĐANG CHẠY)

> Baseline finalFitness = **1.51966**. Cập nhật khi gene mới xong (Oracle ~gene3, 226 ~gene5).

| Gene | Tầng | range fitness | Nhận định |
|---|---|---|---|
| `MIN_MOMENTUM_15M` | entry | **115895** | REJECT khi vặn sai → **CỰC QUAN TRỌNG, giữ** |
| `PREDICT_SYMBOL_RATE_MAX_THRESHOLD` | entry | **100035** | REJECT → **CỰC QUAN TRỌNG, giữ** |
| `HARD_RISK_LIMIT_4H` | entry | **0.2577** | nhạy vừa → giữ (theo dõi) |
| `MS_DOWN_SMALL_AVG_OR_15M` | market | **0.0044** | gần phẳng → **ứng viên cắt** |
| `PREDICT_SYMBOL_RATE_DOWN_15M` | market | **0.0000** | PHẲNG tuyệt đối → **CẮT** |
| `PREDICT_SYMBOL_RATE_UP_AVG` | market | **0.0000** | PHẲNG → **CẮT** |
| `PREDICT_SYMBOL_RATE_DOWN_AVG` | market | **0.0000** | PHẲNG → **CẮT** |
| (20 gene còn lại: DCA, trailing, budget, AI_DYNAMIC, MS_* khác) | | ĐANG CHẠY | chờ |

### Cách tiếp tục (cho session mới)
- 2 máy đang chạy nền (xem CONTEXT_HANDOFF bên dưới). Lấy kết quả mới:
  - Oracle: `grep range= ~/claudedata/sens_oracle.log ~/claudedata/sens_oracle2.log`
  - 226: `grep range= /tmp/sens_226.log /tmp/sens_226_2.log`
- Khi đủ 26 gene → xếp range giảm dần → cắt gene range~0 + đối chiếu bảng rà GENE_AUDIT → chốt ~12 gene.

---

## PHÁT HIỆN SỚM (chắc chắn, chưa cần chờ hết)

1. **Cụm `PREDICT_SYMBOL_RATE_*` (3 gene: DOWN_15M, UP_AVG, DOWN_AVG) PHẲNG TUYỆT ĐỐI (range=0).**
   Vặn cả range không đổi fitness 1 chút nào → 3 gene này VÔ TÁC DỤNG với kết quả → **cắt cả 3**.
   Khớp nghi ngờ ở bảng rà (GENE_AUDIT): cụm này chồng vai trò với MS_*; hóa ra PREDICT_RATE_* là cụm thừa,
   MS_* mới là cụm thật điều khiển market-state. → giảm 3 gene ngay.

2. **`MIN_MOMENTUM_15M` + `PREDICT_SYMBOL_RATE_MAX_THRESHOLD` cực quan trọng** (vặn sai → bot vi phạm
   constraint, sập). Đây là 2 cổng entry chính. Giữ chắc, KHÔNG đụng range rộng khi HPO.

---

## ĐỀ XUẤT CẮT (điền đầy đủ khi xong) — hướng tới ~12 gene

> [Claude tổng hợp khi đủ 26 gene: xếp hạng range, xác định "vách" cắt, đối chiếu bảng rà GENE_AUDIT
> (giữ tầng trailing/DCA/entry cốt lõi), ra danh sách 12 gene giữ + lý do từng gene bỏ.]

## CÂU HỎI ĐỂ UNI DUYỆT (sáng 27)
> [điền sau khi có kết quả đầy đủ]
