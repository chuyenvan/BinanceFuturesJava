# TASK-128: Đo chất lượng model đang dùng trong WFO (CCD opus, Kaggle CPU kernel)

- **status:** doing (giao CCD 2026-07-04 đêm)
- **Bối cảnh giá trị:** funding IC CHƯA TỪNG được đo đúng (validator cũ đo SAI CHIỀU nhóm + threshold hardcode sai
  — đã xác nhận hỏng). Gate/market model có 1.79M pred leak-free per-fold nhưng chưa có IC/AUC chính thức.
- **Tài nguyên:** code local (repo, branch module) + SSH Oracle (rào bên dưới) + Kaggle kernel CPU.
  GPU/TPU KHÔNG dùng cho task này (đo IC là pandas/numpy CPU; GPU quota để dành retrain — ghi rõ trong Kết quả nếu thấy chỗ GPU giúp thật).

## ⛔ HÀNG RÀO
1. SSH Oracle: CHỈ đọc + ghi vào ~/claudedata/task128/ và ~/kaggle_kernels/model-quality/ (mkdir mới); kaggle CLI chỉ
   push kernel tên model-quality-*. CẤM đụng jobstore/worker/242/226-ssh. nice -n 15, Xmx/RAM ≤2g khi chạy gì trên Oracle.
2. **CHIỀU SEMANTICS LÀ TỬ HUYỆT** (validator cũ chết vì đây): TRƯỚC KHI TÍNH bất kỳ số nào, phải đọc code Java đang
   dùng pred/score trong sim (AIRejectFilter + nơi đọc predReturn15M/predRisk4H + funding selector threshold/direction,
   kèm manifest các dataset) và GHI MỤC "ĐỊNH NGHĨA PRE-REGISTERED" đầu report: công thức outcome, chiều kỳ vọng
   (score cao = gì), horizon, nguồn giá. Ghi xong mới code. Số không khớp định nghĩa đã ghi → sửa số liệu là gian lận, chỉ được sửa nếu phát hiện định nghĩa sai và GHI RÕ lý do đổi.
3. Kaggle kernel: theo rule docs/KAGGLE_RULES.md §3b-bis (glob recursive /kaggle/input, .gz→.bin auto-unzip, copy
   config.properties vào CWD nếu chạy java — task này thuần python thì không cần, dataset_sources: wfo-dataset-wf-leakfree
   + hpo-ticker-daily + java-run-lc nếu cần mapper).
4. Số nào cũng kèm lệnh/cell tái lập. Validate-small trước (1 quý) rồi mới full.

## Phạm vi đo (dữ liệu đều đã trên Kaggle)
1. **Gate/market model (pred.bin leak-free trong wfo-dataset-wf-leakfree, format WfoDataset — đọc reader Java để parse đúng):**
   IC Spearman predReturn15M vs realized return 15m (từ ticker daily); predRisk4H vs realized risk 4h (định nghĩa risk
   lấy từ code label gốc — TÌM trong WFOGateRunner/labeling, không tự chế); theo quý 2021→2026 + toàn kỳ; decile lift table.
2. **Funding selector (funding.bin wf):** per tick, outcome của nhóm được-chọn (theo đúng chiều/threshold code dùng)
   vs nhóm bị-loại vs toàn universe — hit-rate + mean return theo horizon code dùng; theo quý.
3. Bảng tổng: IC theo quý (có suy giảm theo thời gian không?), vùng nào model mù (coverage thấp/IC≈0) — đánh dấu
   các quý trùng window WFO âm để buổi phân tích 3 vế đối chiếu.

## Output
- `docs/reports/model_quality_wfo_20260704.md`: mục ĐỊNH NGHĨA PRE-REGISTERED trước, số sau, mỗi bảng kèm nguồn/lệnh.
- Kernel + scripts commit vào scripts/model_quality/ (branch module). Marker /d/claudedata/CCD128_DONE.
- Mơ hồ về semantics → NEEDS_HUMAN, KHÔNG đoán chiều.

## Kết quả
<CCD điền>
