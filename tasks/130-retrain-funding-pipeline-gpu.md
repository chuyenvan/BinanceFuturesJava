# TASK-130: Dựng pipeline RETRAIN funding selector với provenance sạch (Kaggle GPU) — CCD opus

- **status:** doing (giao 2026-07-05 trưa)
- **Bối cảnh:** model funding hiện tại (262MB ONNX) MẤT source code + nghi over-parameterized; bản 49.5MB nhanh 8×
  nhưng cũng không provenance. Nguyên tắc chốt: model phải đi kèm code + data sinh ra nó (direction A: retrain,
  không phục hồi artifact mồ côi). IC hiện tại của model cũ ĐÃ ĐO (TASK-128): rankIC 0.344, hit_SEL 65.8% — đây
  là BASELINE mà model mới phải THẮNG hoặc ít nhất hoà (kèm provenance + size hợp lý) mới được cân nhắc thay.
- **Phạm vi:** DỰNG + SMOKE pipeline end-to-end. KHÔNG thay model production. Thay hay không = quyết định của Uni
  sau khi so số.

## ⛔ HÀNG RÀO
1. Language unification (TASK-109 B1b): TRAIN data DUY NHẤT từ Java export (`ExportFeaturesForPythonTool` → ff_*.bin,
   `ExportFundingOiPerCoin` → OI). Python CHỈ là training code. Nếu script train hiện tại đọc data từ nguồn khác →
   ghi NEEDS_HUMAN, không tự chế nguồn data.
2. Repo có 3 bản train script (ml/funding_selector/train_funding_selector.py + _wfo.py, ml/training/...): pha khảo sát
   PHẢI xác định bản nào là bản đúng/mới nhất (đọc git log + nội dung), ghi rõ vào Thiết kế. Không đoán.
3. SSH Oracle: CHỈ đọc + ghi ~/claudedata/task130/ + ~/kaggle_kernels/funding-train/; Oracle đang chạy vế D —
   export TRAIN data để PENDING nếu cần chạy Java nặng (chỉ chạy khi Oracle rảnh, RAM budget AGENTS.md).
4. Kernel Kaggle: enable_gpu=true, slug funding-train-v1 (nhớ bài học slug kẹt: nếu "Notebook not found" → đổi slug).
   Smoke = train trên 1 lát data nhỏ (1 quý) ít epoch, mục tiêu CHỨNG MINH pipeline chạy + GPU được dùng
   (log device), KHÔNG phải ra model tốt.
5. Pre-register TRƯỚC trong Thiết kế: định nghĩa label (win@24h? — PHẢI khớp code Java sinh label như TASK-128 đã
   xác định score=1−P(win@24h)), split train/val theo THỜI GIAN (không random — leak), metric so sánh = rankIC/hit_SEL
   trên cùng nền TASK-128 để so táo-với-táo với baseline.
6. Provenance block trong mọi output: commit sha + lệnh export + md5 data + script + hyperparams.

## Việc làm
1. Khảo sát (ghi vào Thiết kế, commit trước khi dựng): script train nào đúng, data format ff_*.bin cần gì,
   ExportFeaturesForPythonTool args/env, label định nghĩa ở đâu trong Java.
2. Dựng kernel funding-train-v1 (GPU): đọc data từ dataset Kaggle (dataset TRAIN riêng — nếu chưa có data thì
   kernel smoke dùng lát data tự export nhỏ NẾU Oracle rảnh, không thì mock-run tới bước load rồi PENDING).
3. Smoke GPU: log xác nhận device=cuda, train 1 lát nhỏ chạy hết không crash, model file + provenance block ra output.
4. Kết quả: Thiết kế + trạng thái từng bước + việc PENDING còn lại để chạy train full. Marker /d/claudedata/CCD130_DONE.

## Thiết kế (CCD điền)
<CCD điền>

## Kết quả
<CCD điền>
