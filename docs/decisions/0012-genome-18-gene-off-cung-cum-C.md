# ADR-0012: Genome HPO = 18 gene (A+B), OFF cứng 9 gene cụm C

- **Ngày:** 2026-06-27
- **Trạng thái:** đã chấp nhận (thay thế [ADR-0003](0003-genome-13-gene.md))
- **Bối cảnh phát sinh:** TASK-111 (sensitivity gene + hàm mục tiêu). Rà gene theo BACKTEST THẬT (engine `SimulatorMarketLevelTicker1MStopLoss` + lớp nó gọi), KHÔNG theo code HPO cũ (rác/phân mảnh). Nguồn số: `docs/insights/SENSITIVITY_TASK111.md`, bản đồ gene 6 tầng: `docs/reference/GENE_AUDIT_TASK111.md`.

## Vấn đề

Genome HPO cũ (ADR-0003, **13 gene**) chỉ phủ tầng market-status + AI + DCA — **thiếu toàn bộ tầng trailing-exit và budget**, là phần cõng PnL thật của bot không-stop-loss. HPO cũ vì thế tối ưu trên không gian thiếu (chỉ tinh chỉnh entry, để nguyên trailing/budget ở giá trị tay). Cần chốt genome THẬT cho WFO (ADR-0008/ROADMAP Bước 4), kèm quyết định xử lý các gene phẳng.

## Các lựa chọn đã cân nhắc

1. **Ép xuống 12 gene** (mục tiêu ban đầu ROADMAP "13→~8") — ưu: không gian nhỏ, HPO rẻ; nhược: số đo nói SAI — buộc hi sinh cụm B (có ảnh hưởng thật) + 1 gene cụm A (xương sống) → giảm chất lượng. Con số "8/12" đặt ra trước khi có sensitivity, quá tham vọng.
2. **Giữ 18 gene (A 13 + B 5), cắt 9 gene cụm C** — ưu: khớp số đo (chỉ cụm C cắt sạch được); nhược: nhiều hơn 13 cũ, không gian HPO lớn hơn (chấp nhận được vì đã loại 9 gene vô tác dụng).
3. **Cắt cụm C bằng off MỀM** (đổi giá trị về trung tính, giữ cơ chế) — nhược: Uni bác — "tự mua xích buộc chân": 9 gene vẫn chạy + vẫn impact 18 gene kia, đóng băng nửa vời, khó dọn sau.

## Quyết định

- **Genome = 18 gene** (cụm A 13 + cụm B 5). KHÔNG phải 12/8.
- **9 gene cụm C: OFF CỨNG** (vô hiệu cơ chế tại điểm dùng trong engine), KHÔNG off mềm.

### Cụm A — REJECT khi vặn sai (range ~10^5), XƯƠNG SỐNG, giữ chắc (13)
`MIN_MOMENTUM_15M`, `PREDICT_SYMBOL_RATE_MAX_THRESHOLD`, `AI_DYNAMIC_MULTIPLIER` (entry) ·
`DCA_LOSS_BIG_DOWN`, `DCA_TIME_BIG_DOWN`, `DCA_TIME_BIG_Up` (dca) ·
`RATE_PROFIT_STOP_MARKET`, `TS_MAX_GAP`, `TS_DYNAMIC_K`, `TS_MAX_GAP_WEAK` (trailing) ·
`BUDGET_MARGIN_RATIO_1`, `BUDGET_MARGIN_RATIO_2`, `BUDGET_DIVIDER_2` (budget).

### Cụm B — nhạy vừa (range 0.07–0.26), GIỮ (5)
`HARD_RISK_LIMIT_4H` (0.258), `AI_DYNAMIC_MIN` (0.180), `MS_DOWN_BIG_AVG` (0.178),
`TS_PROFIT_MULTIPLIER` (0.165), `TS_WEAK_MOMENTUM_THRES` (0.077).

### Cụm C — phẳng (range < 0.06), OFF CỨNG (9)
`AI_DYNAMIC_MAX` (0.053), `MS_UP_BIG_THRES` (0.032), `DCA_LOSS_BIG_UP` (0.009),
`BUDGET_DIVIDER_1` (0.0096), `MS_DOWN_SMALL_AVG_OR_15M` (0.0044), `MS_UP_SMALL_THRES` (0.0038),
`PREDICT_SYMBOL_RATE_DOWN_15M` (0), `PREDICT_SYMBOL_RATE_UP_AVG` (0), `PREDICT_SYMBOL_RATE_DOWN_AVG` (0).

**Off cứng = vô hiệu cơ chế tại điểm dùng** (giữ biến trong `Configs` vì 26 file tham chiếu, xóa hẳn = vỡ build); cờ `OFF_FLAT_HARD`:
- bỏ nhánh phân loại BIG_UP / SMALL_UP / SMALL_DOWN_15M (`MarketBigChangeDetector`)
- bỏ cận trên clamp `AI_DYNAMIC_MAX` (`AIRejectFilter`)
- bỏ nhánh DCA BIG_UP (`DcaUtils`)
- bỏ tầng `BUDGET_DIVIDER_1` (`TradeUtils`)
- 3 gene `PREDICT_SYMBOL_RATE_*` đã CHẾT sẵn (set-never-read) → không cần đụng.

## LÝ DO (phần quan trọng nhất)

- **Phương pháp đo:** OAT sensitivity, baseline `finalFitness=1.51966` (FAST 2024-01→2026-06), mỗi gene quét 4 mức giữ 25 gene kia ở baseline, đo `range = max−min`. range ~10^5 = vặn sai đẩy vào REJECT (vi phạm constraint cứng) = gene cực quan trọng; range ~0 = phẳng (cắt được). HẠN CHẾ: OAT bỏ qua tương tác gene — là bước SÀNG trước HPO, không phải kết luận tuyệt đối.
- **Vì sao 18 không phải 12:** chỉ 9 gene cụm C cắt sạch được; 5 gene cụm B có ảnh hưởng thật; 13 gene cụm A vặn sai làm bot SẬP. Ép xuống 12 = hi sinh B + 1 gene A.
- **Phát hiện ngược trực giác — tầng trailing/exit phải GIỮ TOÀN BỘ:** 4/5 gene trailing vặn sai làm bot SẬP (REJECT). Xác nhận EXIT là sống còn cho bot long-only KHÔNG stop-loss. Khác phán đoán ban đầu (định cắt `TS_MAX_GAP_WEAK`/`TS_WEAK_MOMENTUM_THRES`) — dữ liệu nói KHÔNG cắt được.
- **Cụm `PREDICT_SYMBOL_RATE_*` (3 gene) phẳng tuyệt đối (range=0):** vặn cả dải không đổi fitness → vô tác dụng. Hóa ra `MS_*` mới là cụm thật điều khiển market-state; `PREDICT_RATE_*` là cụm THỪA (chồng vai trò) — đã set-never-read.
- **`BUDGET_DIVIDER_2` range 10^5 nhưng `BUDGET_DIVIDER_1` phẳng:** đoán "cùng loại nên cùng phẳng" là SAI — đo mới biết. → DIVIDER_2 vào cụm A (giữ), DIVIDER_1 vào cụm C (off).
- **Off cứng thay off mềm (Uni chốt 2026-06-27):** 18 gene giữ đều chịu impact lẫn nhau nên đánh giá "bỏ hẳn" phải vô hiệu cơ chế khỏi đường chạy, không phải đổi giá trị (off mềm để gene phẳng vẫn chạy + vẫn nhiễu 18 gene kia).
- **Số kiểm chứng off cứng (GoldenBacktest FULL, Uni đánh giá TỐT HƠN — ít nhánh rối):** equity cuối năm sát baseline cũ — 2021:21336→21448, 2022:6845→6179, 2023:10152→11047, 2024:18262→17712, 2025:8723→8586, 2026:4811→4652. AblationCluster off đồng thời cụm C: fitness 1.5197→1.4868 (delta −2.16% — tương tác cộng dồn nhẹ, chấp nhận).

## Hệ quả

- **Supersede ADR-0003 (13 gene).** Genome thật giờ 18 gene; mọi tài liệu/HPO nói "13" hoặc "13→8/12" đọc lại theo 18 (đã sửa ROADMAP Bước 4 + PIPELINE B6).
- **WFORunner** dựng trên genome 18 gene này (random search). Verdict WFO: WFO_FRAMEWORK_DESIGN.md mục 6.
- **Ràng buộc cứng (kế thừa ADR-0003/0004):** thêm/bớt/đổi thứ tự gene BẮT BUỘC cập nhật `eval()` mapping + `buildTaskId` (key băm đủ gene) + bump CONFIG_VERSION.
- **Việc còn lại (Uni duyệt trước khi commit — xóa code không đảo ngược dễ):**
  1. Biến off cứng thành VĨNH VIỄN (xóa cờ `OFF_FLAT_HARD` + xóa hẳn các nhánh) — hiện đang để dạng cờ (hành vi = off cứng, đảo ngược dễ).
  2. Baseline mới cho HPO = hệ thống SAU off cứng (KHÔNG phải bản cũ 1.5197).
  3. WFO full sau function-test (xác nhận thời gian + tỷ lệ REJECT chấp nhận được).
- **Gene đang hardcode (cân nhắc THÊM sau, Uni quyết — GENE_AUDIT B1):** DCA margin ladder (4 bậc), trailing "nhả nửa lãi 0.5f", các bậc managerBudget. Quan trọng nhất là DCA margin ladder (điều khiển rủi ro đuôi).
- **KHÓA (không tối ưu):** `LEVERAGE_ORDER=1` (ràng buộc chiến lược), `FILTER_MODE`/`BREAKER_MODE` (categorical, chọn bằng ADR không phải gene liên tục).
