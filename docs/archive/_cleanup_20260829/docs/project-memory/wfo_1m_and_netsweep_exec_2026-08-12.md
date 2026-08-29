# WFO 1m full predict + retEnd NET_THR sweep — exec log 2026-08-12

## >>> QUYẾT ĐỊNH & ƯU TIÊN (2026-08-12, chốt bởi Uni) <<<
- **Ưu tiên #1: full 1m @0.008 vs 15m @0.008 — chốt "1m tốt hay 15m tốt".** Đây là câu hỏi nền; chốt xong cái này thì mọi thứ khác mới đủ chắc để chốt.
- 1m full chạy **predict-only** (tái dùng model train ở 15m, KHÔNG train lại — edge đã xác nhận trùng khít). Grid predict = 1m, label NET_THR=0.008 (khớp baseline 15m +10,942 để so apples-to-apples).
- **Sweep NET_THR (0.02 winner) — GÁC LẠI, chỉ note.** Đánh giá 0.02 "chưa đủ chặt" (mới 1 lần fanout, PnL có noise ±10%, maxDD nondeterministic). Sẽ đánh giá lại SAU khi có full 1m + trên grid thắng.
- Note để sau: quét tiếp NET_THR **0.03 / 0.05** tìm đỉnh đường cong PnL (đang tăng đơn điệu tới 0.02). CHƯA chạy.
- bake vào loose_k8 (NET_THR winner + SIM_RATE_PROFIT_STOP_MARKET=0.05) — chờ, sau khi chốt 1m-vs-15m + ngưỡng.

## KẾT QUẢ SWEEP retEnd 15m (xong 2026-08-12) — edge & PnL đều tăng theo ngưỡng
| NET_THR | pos-rate | mean AUC | mean lift | PnL 12 quý |
|---------|----------|----------|-----------|-----------|
| 0.006 | 0.30 | 0.563 | 1.27 | (chưa fanout) |
| 0.008 (baseline) | 0.28 | 0.580 | 1.36 | **+10,942** |
| 0.015 | 0.17 | 0.633 | 1.77 | (đang fanout t015) |
| **0.02** | **0.12** | **0.664** | **2.10** | **+12,920** (+18% vs baseline) |
- t020 per-window: win8/2024Q1 +3398 (đậm nhất), win11 +2414, win15 +2551; lỗ win12/2025Q1 −1630, win14 −396. posRatio lenient 63% (10/16 window WFE+).
- KẾT LUẬN sơ bộ: ngưỡng cao (0.02) chọn lọc hơn + PnL cao hơn — nhưng "chưa đủ chặt", cần full 1m + lặp lại mới tin.

## Bối cảnh / nhầm lẫn đã làm rõ
- maxFav KHÔNG test lại. "6%" (maxFav peak) ≠ 0.008 (net endpoint) — không phải số bị đổi.
- **1m KHÔNG train model khác 15m.** train trên data 15m rồi áp lên lưới 1m. Edge trên điểm trùng 15m = TRÙNG KHÍT (net@0.008: fold0 0.570vs0.565, fold2 0.608vs0.607, fold4 0.598vs0.599). Full 1m chỉ đổi MẬT ĐỘ điểm vào lệnh (~15x) → chỉ ảnh hưởng PnL qua độ phủ/fill, KHÔNG đổi chất lượng model. Đây chính là lý do làm predict-only.

## Hạ tầng
- Oracle `161.118.212.3`, SSH `ssh -i ~/.ssh/id_rsa_chuyennd_openssh ubuntu@161.118.212.3` (BẮT BUỘC -i key). 4 core/23GB.
- Kaggle: GPU limit 2, CPU limit 5 đồng thời. GPU kernel RAM ~13GB; CPU ~30GB. API log CHỈ có khi kernel COMPLETE/ERROR (RUNNING → rỗng). KHÔNG watcher nền poll (gây 429).
- Code dataset `chuyendinh/sel1m-code`. Data: funding-unf15-data (15m .bin), funding-tool1-1m-unf (1m .t1c), funding-oi-percoin.

## gen_funding_wf_predictions_1m.py — cơ chế đã có
- **Two-glob**: TOOL1_GLOB=15m .bin (train/cutoff), PRED_TOOL1_GLOB=1m .t1c (OOS predict).
- **Stream predict**: iter_oos_features_1m yield sub-chunk 30 ngày; train trước rồi stream predict.
- **RAM fix**: CPU 30GB + gc.collect + memmap OI + malloc_trim (cho quý 1m 2025 ~45M row).
- **MODEL_DIR**: set → nếu có model_f{fidx}_{h}.json thì LOAD (bỏ train); nếu train thì SAVE. => train 1 lần 15m (GPU nhanh) rồi predict-only 1m (CPU) không train lại.

## Pipeline full-1m predict-only (ĐANG CHẠY)
- **Stage A** `selector-15m-savemodel-net008-gpu` (GPU, 15m, MODEL_DIR=/kaggle/working): train 14 fold + SAVE model_f*.json. RUNNING.
- **Stage B** (chưa dựng): pull model → dataset `chuyendinh/sel-models-net008` → 2 kernel 1m CPU (clone k1m_n0/n1, +MODEL_DIR trỏ sel-models trong /kaggle/input, +dataset_source sel-models-net008, NET_THR=0.008, enable_gpu=false, NUM_NODES=2). Predict-only → predict_wf 1m.
- Downstream: gộp predict_wf 1m → drive_exp (build funding.bin 1m + fanout) → PnL 1m@0.008 → SO +10,942 (15m). Đây là câu trả lời 1m-vs-15m.
- node1 (1m code cũ pre-model-load) ERROR ở 2025 — bỏ, thay bằng Stage B.

## Trạng thái các fanout tạm (điểm PnL sweep, đang chạy nốt, KHÔNG mở rộng)
- t020 (0.02): DONE = +12,920.
- t015 (0.015): đang fanout (~08:00 UTC).
- t006 (0.006): mới có SCREEN, chưa fanout PnL.
