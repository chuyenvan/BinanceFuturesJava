# ADR-0009: Pivot — rebuild trên data đầy đủ + model mới (ONNX cũ = baseline)

- **Ngày:** 2026-06-11
- **Trạng thái:** đã chấp nhận (định hướng lớn).
- **Bối cảnh:** phân tích model (label `max-high` market-level lạc quan, edge mỏng x1.21) + TASK-006.1 (DCA-ruin) + nhận ra: training data méo vì thiếu coin die, và code train cũ đã mất (chỉ còn ONNX).

## Vấn đề
Tinh chỉnh chiến lược/breaker khi **data nền + model chưa đúng** = xây trên cát. Training data hiện tại méo (thiếu coin die), model cũ là hộp đen không tái tạo được.

## Quyết định
1. **Training data hiện tại KHÔNG đáng tin.** Feature market-level (avg top-100 coin sập mạnh nhất + basket) và label phụ thuộc TOÀN tập coin → thiếu coin die làm cả hai méo. Thêm coin die ⇒ **phải re-export 100%** (không chèn lẻ được).
2. **ONNX cũ: BỎ làm model production, GIỮ làm BASELINE.** Lý do bỏ KHÔNG phải "model cùi" mà "không tái tạo được (mất code train) → drift là không vá được". Train model mới bằng pipeline kiểm soát được; ONNX cũ chỉ để làm mốc so (đo lại trên data đầy đủ).
3. **Thứ tự rebuild:**
   - **P1 — Backfill đủ data** (TASK-005): fill ticker coin die → 226 test → audit → sync 242 → **re-export 100%** training data. Mục tiêu THẤP = đủ data, không cầu toàn. Chỉ ticker (prediction gen ở P3).
   - **P2 — Làm model mới:** chọn **label/target** đúng (sửa lỗi `max-high` market-level: lạc quan + lẫn timing với selection) + features + cách dùng (gate vs selector) + chiến lược. Train, so ONNX baseline, đạt **"đủ tốt + biết trần edge"** (không cầu toàn).
   - **P3 — Model mới → gen prediction → chạy lại golden baseline TOÀN BỘ → tối ưu dần** (breaker dùng ADR-0008 làm mốc).
4. **DỪNG tune breaker/DCA-cap chi tiết** (TASK-006.2) tới khi model mới final. Giữ ADR-0008 (cơ chế) làm mốc.

## Hệ quả — QUAN TRỌNG
- **Backfill = đổi nền data ⇒ MỌI golden baseline cũ (FAST/CRASH/BULL/FULL) + kết quả breaker 006 + scenario 006.1 thành VÔ HIỆU**, phải chụp lại sau re-export. Golden **harness** (công cụ) giữ; **baseline** (số) refresh. Bump CONFIG_VERSION (ADR-0004).
- Gần như làm lại từ đầu, NHƯNG trên insight đã có (FINDINGS, ADR 0001-0008, golden harness, cơ chế breaker) + phát triển với model mới.
- Survivorship (ADR-0007): từ "hoãn [C]" → **LÀM**, nhưng mục tiêu mới = data cho training (không phải đo-impact-qua-sim). An toàn vì 242 live chỉ dùng ~2 ngày gần nhất; lịch sử xa fill thoải mái.

## Bài học giữ lại
Verify nền (data + model) trước khi tối ưu tầng trên. Cơ chế risk (ADR-0008: ràng buộc neo vốn) độc lập model nên giữ; ngưỡng thì chờ model final.
