# RESULT_S1REFRESH — refresh S1 cutoff 20251231 (2026-09-12)

## Phán quyết
- Cổng tái lập (cut20251001): **PASS** (dạng mạnh nhất — booster JSON byte-identical).
- Toàn vẹn model mới (cut20251231): **PASS**.
- Probe parity onnx-vs-json top-8: **PASS 100% (6781/6781)**.
- => **ỨNG VIÊN DEPLOY SHADOW**. DỪNG, chờ USER quyết định deploy. Không deploy trong phiên này.

## 1. Cổng tái lập — cut20251001
- Pipeline: research/pipeline/x1/x1_s1_save_model.py, X1_CUT=20251001, OUT=/home/ubuntu/s1_model_repro (scratch, không đụng model gốc).
- Frame khớp gốc: train 3485834 (den 2025-09-27 16:45:00), oos 3499202 ticks 6909 = manifest gốc.
- So prediction tái tạo vs pred gốc pred_s1a2x1.parquet (3499202/3499202 dòng):
  - score_mem: spearman 1.000000, max|d| 0.0, med|d| 0.0
  - score_json: spearman 1.000000, max|d| 0.0, med|d| 0.0
  - score_onnx: spearman 1.0, max|d| 2.62e-6 (quantization ONNX — ngoài phạm vi cổng tái lập)
- sha256 booster JSON tái tạo = cc0924f1...997308 = **GIỐNG HỆT bản gốc (bit-for-bit)**.
- Cờ "CONG MODEL" nội bộ script = FAIL nhưng CHỈ do gộp dòng onnx 2.62e-6 > 1e-6 — giống hệt gate_pass=false của manifest gốc (tái lập đúng cả hành vi gốc). Tiêu chí pre-reg (json/mem spearman 1.0, max|d|<1e-6) ĐẠT.

## 2. Model mới cut20251231
- X1_CUT=20251231, OUT=/home/ubuntu/s1_model.
- train **6911775 rows (den 2025-12-27 16:30:00)** — KHÔNG có dòng ts>=2026-01-01 (ledger cand_dev_x1 ts_max=2025-12-31 16:45, không có data 2026). Holdout 2026 nguyên vẹn.
- oos nội bộ 30924 rows / 59 ticks (~1 ngày cuối 2025 do ledger hết data) → gate/topk nội bộ script so vs model CŨ nên KHÔNG dùng go/no-go.
- Artifact:
  - /home/ubuntu/s1_model/s1a2x1_cut20251231.json  sha256 `af706dc654c96f075caddc5f4153c768eec0732a28340cf9adbd6a6f791d8bf1` (655443 B)
  - /home/ubuntu/s1_model/s1a2x1_cut20251231.onnx  sha256 `8b1dcf00c1ce083793a2243631fa2cd892162ab95dcee0e360b829affca323c3` (293105 B)
  - .manifest.json (xgboost 3.2.0)

## 3. Toàn vẹn model mới (window chung 2025-10-01..2025-12-31: 3489797 rows, 6890 ticks, ts_max 2025-12-31 16:45)
- prediction: NaN 0, inf 0.
- phân phối: OLD mean -0.898 std 0.563 [-1.95,3.06]; NEW mean -1.065 std 0.611 [-2.12,3.25] — cùng scale, không lệch bất thường. PASS.

## 4. Top-K compare old-vs-new (READ-ONLY, mô tả)
- 6781 ticks (>=8 candidate).
- top-8 overlap: mean 67.51%, median 62.50%; full 8/8 identical 90/6781 (1.33%).
- per-tick spearman thứ hạng: mean 0.9589, median 0.9625, min 0.4727.
- Diễn giải: model mới giữ thứ hạng tổng thể rất cao (~0.96) nhưng đổi ~2-3/8 vị trí top-8 mỗi tick — thay đổi thực chất, hợp lý cho +3 tháng data. CHỈ mô tả, không tune.
- Lưu ý: Oct01–Dec27 là in-sample với model mới (train tới 2025-12-27); đây là so sánh mức thay đổi lựa chọn, không phải claim hiệu năng OOS.

## 5. Probe parity onnx-vs-json (cut20251231, window trên)
- onnxruntime (cùng runtime + cùng file .onnx + input [N,9] positional theo FEATURE_ORDER + quy ước score=-out mà S1RankerLive/S1OnnxProbe.java dùng) vs booster JSON:
  - spearman 0.99999999999, max|d| 1.67e-6, med|d| 2.38e-7
  - **top-8 onnx==json: 6781/6781 = 100.0000%**.
- Sai lệch pre-reg: probe chạy ở mức onnxruntime (proxy trung thực của S1RankerLive) chứ KHÔNG chạy full harness Java S1RankerLive end-to-end (cần build L4 harness + wiring config, ngoài phạm vi phiên read-only). Bản chất fidelity ONNX + thứ tự feature (thứ probe Java kiểm) = 100%.

## 6. Phán quyết + việc cần USER
- (a) cổng tái lập PASS; (b) toàn vẹn PASS; (c) probe parity 100% → ĐỦ 3 → **ỨNG VIÊN DEPLOY SHADOW**.
- USER quyết: có deploy /home/ubuntu/s1_model/s1a2x1_cut20251231.onnx vào shadow không (đổi Cfg S1_MODEL_ONNX / wiring). KHÔNG thực hiện trong phiên này.
- Không chạm 242, không deploy live, không tune, holdout 2026 nguyên vẹn.
- Artifact tái lập scratch còn tại /home/ubuntu/s1_model_repro/ (bằng chứng byte-identical, có thể xóa an toàn).
