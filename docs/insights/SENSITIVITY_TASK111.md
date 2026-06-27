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

## BẢNG SENSITIVITY (cập nhật 2026-06-27 06:30, **17/26 gene xong**, batch2 9 gene ĐANG CHẠY)

> Baseline finalFitness = **1.51966**. ⚠️ ĐỌC KỸ cột "chuỗi mức" — cột `range` thô bị THỔI PHỒNG bởi
> giá trị REJECT (-100033 = vi phạm constraint cứng). Một gene range=10^5 KHÔNG tự động là "quan trọng nhất";
> phải xem baseline đang nằm ĐÂU so với vùng REJECT.

**Đã có (17 gene) — xếp theo bản chất, không chỉ theo range thô:**

| Gene | Tầng | range | Chuỗi mức (min→max value → fitness) | Bản chất |
|---|---|---|---|---|
| `MIN_MOMENTUM_15M` | entry | 115895 | 0.005→REJECT, 0.02→REJECT, 0.035→2.31, 0.05→2.13 | **GIỮ.** baseline 0.0228 ở MÉP REJECT — cần cẩn thận khi HPO |
| `PREDICT_SYMBOL_RATE_MAX_THRESHOLD` | entry | 100035 | 0.05→1.95, 0.13→2.12, 0.22→REJECT, 0.30→REJECT | **GIỮ.** vặn cao quá → sập; baseline 0.15 an toàn |
| `AI_DYNAMIC_MULTIPLIER` | entry | 100035 | 0.8→REJECT, 1.2→REJECT, 1.6→2.02, 2.0→1.54 | **GIỮ.** vặn thấp → sập; baseline 1.29 ở mép |
| `DCA_LOSS_BIG_DOWN` | dca | 100035 | -0.30→REJECT, -0.23→1.63, -0.15→1.54, -0.08→1.51 | **GIỮ.** nhồi quá sâu → sập (rủi ro đuôi) |
| `DCA_TIME_BIG_DOWN` | dca | 100035 | 3→1.52, 8.7→REJECT, 14→REJECT, 20→1.54 | **GIỮ.** nhưng phi tuyến lạ — xem kỹ |
| `DCA_TIME_BIG_Up` | dca | 100035 | 5→1.52, 13→REJECT, 22→1.53, 30→1.53 | **GIỮ.** phi tuyến |
| `HARD_RISK_LIMIT_4H` | entry | 0.2577 | -0.35→1.52, -0.25→1.52, -0.15→1.52, -0.05→1.78 | nhạy nhẹ ở biên cao → giữ |
| `AI_DYNAMIC_MIN` | entry | 0.1799 | 0.1→1.52 ... 0.5→1.70 | nhạy nhẹ |
| `MS_DOWN_BIG_AVG` | market | 0.1776 | -0.06→1.58, -0.047→1.59, -0.033→1.52, -0.02→1.70 | nhạy vừa → **GIỮ** (ngưỡng BIG_DOWN) |
| `AI_DYNAMIC_MAX` | entry | 0.0531 | 1.5→1.45 ... 3.0→1.47 | gần phẳng → ứng viên cắt/gộp |
| `MS_UP_BIG_THRES` | market | 0.0318 | 0.01→1.49 ... 0.04→1.51 | gần phẳng |
| `DCA_LOSS_BIG_UP` | dca | 0.0092 | -0.4→1.52 ... -0.1→1.53 | **phẳng → CẮT** (nhánh BIG_UP ít tác dụng) |
| `MS_DOWN_SMALL_AVG_OR_15M` | market | 0.0044 | -0.04→1.52 ... -0.01→1.52 | **phẳng → CẮT** |
| `MS_UP_SMALL_THRES` | market | 0.0038 | 0.002→1.52 ... 0.01→1.52 | **phẳng → CẮT** |
| `PREDICT_SYMBOL_RATE_DOWN_15M` | market | 0.0000 | tất cả → 1.520 | **PHẲNG TUYỆT ĐỐI → CẮT** |
| `PREDICT_SYMBOL_RATE_UP_AVG` | market | 0.0000 | tất cả → 1.520 | **PHẲNG TUYỆT ĐỐI → CẮT** |
| `PREDICT_SYMBOL_RATE_DOWN_AVG` | market | 0.0000 | tất cả → 1.520 | **PHẲNG TUYỆT ĐỐI → CẮT** |

**Tầng TRAILING (5 gene, batch2 17-21 — XONG 2026-06-27):**

| Gene | Tầng | range | Bản chất |
|---|---|---|---|
| `RATE_PROFIT_STOP_MARKET` | trail | 100036 | **GIỮ.** REJECT khi vặn sai — ngưỡng bắt đầu chốt lời |
| `TS_DYNAMIC_K` | trail | 100035 | **GIỮ.** REJECT — hệ số bám volatility dời SL |
| `TS_MAX_GAP` | trail | 100035 | **GIỮ.** REJECT — gap trailing tối đa |
| `TS_MAX_GAP_WEAK` | trail | 100035 | **GIỮ.** REJECT — gap khi momentum yếu (⚠️ định cắt nhưng KHÔNG nên: vặn sai → sập) |
| `TS_PROFIT_MULTIPLIER` | trail | 0.1648 | **GIỮ.** nhạy vừa (5.0→...→fitness đổi 0.16) |

> ⭐ PHÁT HIỆN QUAN TRỌNG: cả 5 gene trailing đều phải GIỮ — 4/5 vặn sai làm bot SẬP (REJECT).
> Xác nhận: tầng EXIT là sống còn cho bot long-only KHÔNG stop-loss. Khác phán đoán ban đầu (định cắt
> TS_MAX_GAP_WEAK/TS_WEAK_MOMENTUM) — dữ liệu nói KHÔNG cắt được.

**Đang chạy (4 gene budget, batch3 22-25 trên Oracle):** NUMBER_ENTRY_EACH_SIGNAL, BUDGET_MARGIN_RATIO_1,
BUDGET_DIVIDER_1, BUDGET_MARGIN_RATIO_2 (lưu ý: 226 batch2 budget bị `NoClassDefFoundError: Storage` do
RSS chạm 12GB sát -Xmx11g → thiếu RAM; đã chuyển sang Oracle 23GB chạy nối tiếp sau 17-21).

### Lấy kết quả batch3 (khi xong)
- Oracle: `grep -E "\] [A-Z_]+ range=" ~/claudedata/sens_oracle3.log`

---

## PHÁT HIỆN SỚM (chắc chắn, chưa cần chờ hết)

1. **Cụm `PREDICT_SYMBOL_RATE_*` (3 gene: DOWN_15M, UP_AVG, DOWN_AVG) PHẲNG TUYỆT ĐỐI (range=0).**
   Vặn cả range không đổi fitness 1 chút nào → 3 gene này VÔ TÁC DỤNG với kết quả → **cắt cả 3**.
   Khớp nghi ngờ ở bảng rà (GENE_AUDIT): cụm này chồng vai trò với MS_*; hóa ra PREDICT_RATE_* là cụm thừa,
   MS_* mới là cụm thật điều khiển market-state. → giảm 3 gene ngay.

2. **`MIN_MOMENTUM_15M` + `PREDICT_SYMBOL_RATE_MAX_THRESHOLD` cực quan trọng** (vặn sai → bot vi phạm
   constraint, sập). Đây là 2 cổng entry chính. Giữ chắc, KHÔNG đụng range rộng khi HPO.

---

## KẾT QUẢ ĐẦY ĐỦ 26/27 gene (gene 26 BUDGET_DIVIDER_2 đang chạy nốt) — xếp theo range GIẢM DẦN

**Nhóm A — REJECT khi vặn sai (range ~10^5) → CỰC QUAN TRỌNG, GIỮ (14 gene):**
MIN_MOMENTUM_15M, PREDICT_SYMBOL_RATE_MAX_THRESHOLD, AI_DYNAMIC_MULTIPLIER (entry) ·
DCA_LOSS_BIG_DOWN, DCA_TIME_BIG_DOWN, DCA_TIME_BIG_Up (dca) ·
RATE_PROFIT_STOP_MARKET, TS_MAX_GAP, TS_DYNAMIC_K, TS_MAX_GAP_WEAK (trail) ·
BUDGET_MARGIN_RATIO_1, BUDGET_MARGIN_RATIO_2 (budget).
→ Vặn sai = bot vi phạm constraint (sập). KHÔNG cắt được. *(12 unique + 2 = đếm lại: 12 gene REJECT)*

**Nhóm B — NHẠY VỪA (range 0.07–0.26) → GIỮ (5 gene):**
HARD_RISK_LIMIT_4H (0.258), AI_DYNAMIC_MIN (0.180), MS_DOWN_BIG_AVG (0.178),
TS_PROFIT_MULTIPLIER (0.165), TS_WEAK_MOMENTUM_THRES (0.077).

**Nhóm C — PHẲNG (range < 0.06) → CẮT được (9 gene):**
AI_DYNAMIC_MAX (0.053), MS_UP_BIG_THRES (0.032), DCA_LOSS_BIG_UP (0.009),
BUDGET_DIVIDER_1 (0.0096), MS_DOWN_SMALL_AVG_OR_15M (0.0044), MS_UP_SMALL_THRES (0.0038),
PREDICT_SYMBOL_RATE_DOWN_15M (0), PREDICT_SYMBOL_RATE_UP_AVG (0), PREDICT_SYMBOL_RATE_DOWN_AVG (0).
*(+ BUDGET_DIVIDER_2 nếu phẳng — cùng loại DIVIDER_1, đang chạy nốt.)*

## KẾT LUẬN: genome tối thiểu ~17 gene (A+B), KHÔNG phải 12

Dữ liệu nói thẳng: **chỉ 9 gene cụm C cắt sạch được**; 5 gene cụm B có ảnh hưởng thật (không nên cắt);
12 gene cụm A là xương sống (vặn sai → sập). Ép xuống 12 buộc phải hi sinh cụm B → giảm chất lượng.
→ Đề xuất: **giữ 17 gene (A+B), ngắt 9–10 gene cụm C.** Số "12" ban đầu quá tham vọng.

**Tầng trailing/exit phải giữ TOÀN BỘ** (4/5 REJECT) — ngược trực giác cắt ban đầu; exit là sống còn
cho bot không stop-loss. **Cụm PREDICT_RATE_* (3 gene) phẳng tuyệt đối** → MS_* mới là cụm thật.

## KIỂM CHỨNG & HÀNH ĐỘNG (đang chạy)
- **AblationClusterTool** (off ĐỒNG THỜI cụm C, kiểm tương tác OAT bỏ sót): delta<2% → NGẮT CỨNG
  (xóa khỏi code); delta≥2% → NGẮT MỀM (constant + comment KHÔNG-HPO). Đang chờ Oracle rảnh.
- **WFORunner** đã dựng (genome 17 gene cụm A+B, cửa sổ OOS 3 tháng trượt 3 tháng, train 12 tháng,
  random search). Kim chỉ nam: WFO_OBJECTIVE_RESEARCH.md.
