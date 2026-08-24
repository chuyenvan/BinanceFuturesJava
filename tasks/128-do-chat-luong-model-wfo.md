# TASK-128: Đo chất lượng model đang dùng trong WFO (CCD opus, Kaggle CPU kernel)

- **status:** DOING/BLOCKED — **owner:** CCD-opus · **updated:** 2026-07-04 (semantics+tool+jar+kernel XONG; BLOCKED slot Kaggle 5/5=wfo-worker + Oracle bận WFO vế-C; số chờ slot — xem Kết quả)
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

## Kết quả (CCD-opus 2026-07-04)

**Semantics + pipeline XONG; số CHƯA có — BLOCKED slot compute (job WFO khác đang chiếm, không tranh).**

- ĐỊNH NGHĨA PRE-REGISTERED (chốt chiều/threshold từ code) + ĐÍNH CHÍNH provenance: `docs/reports/model_quality_wfo_20260704.md`.
  - Death-trap gỡ: funding `pred[0]=score=1−P(win@24h)` (manifest `fundingSetProvenance=...score1minusPwin`), engine chọn **score THẤP = P(win) cao**; horizon 24h target +6% (`maxFav_24h≥0.06 & nBars≥96`).
  - ⚠️ `pred.bin` = `ai_pred_market_full_basket_v2` **UNCHANGED, KHÔNG leak-free** (khác giả định đề) → IC market <2025-12 là in-sample.
- Tool: `src/.../ai_ml/validation/Task128ModelQuality.java` (compile OK, tái dùng đúng code nhãn). Jar fat sanitize → Kaggle dataset `chuyendinh/t128-model-quality-jar`.
- Kernel `model-quality-1` (2024Q1 validate) + `model-quality-full` + `analyze.py` (test synthetic PASS): `scripts/model_quality/`.

### JOB ĐANG CHỜ (bàn giao — CCD khác/next tiếp quản)
- **BLOCKER:** Kaggle 5/5 slot = `wfo-worker-1..5` RUNNING (12h-kill ~01:04 04/07). Oracle ~20/23g WFO vế-C. KHÔNG đụng cả hai.
- **Khi có ≥1 slot:** `cd scripts/model_quality/kernel_validate && kaggle kernels push -p .`; poll `kaggle kernels status chuyendinh/model-quality-1`; `kaggle kernels output ... -p /d/claudedata/mq1-out`; `python scripts/model_quality/analyze.py /d/claudedata/mq1-out/t128_out`. Validate PASS (IC dương, hit_SEL>UNI>REJ) → push `model-quality-full` → điền Bảng 1-3 report.
- Marker: `/d/claudedata/CCD128_BLOCKED` (chưa DONE — chưa có số).
