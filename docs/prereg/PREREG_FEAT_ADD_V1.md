# PRE-REG — THÊM feature V1 (26 cột = 21 keeper + 5 prescreen) trên nền G2+FLAT3
Chốt TRƯỚC khi xem số. Owner 09-29: thêm trước, cắt (bản 22=V0) đã biết kém. V1 = model net015/G015 biến thể 26 cột
(fs_v9_31 base_keepers[21] + appended_real[45..49]=rvol7d,mom30d,mom7d,daysSinceHigh30D,oi_delta7d). Bins V1 CÓ SẴN:
`~/ruler_bins/g015p2-stage2-featvar-gpu/stage2/V1`. Baseline = B0 = G2+FLAT3 (profiles/g2_flat3.properties, md5 sim 650c386f, n2517).

## Đã biết (nền CŨ, gate-independent ở model tier)
- Model tier (RESULT_MODEL_RULER): V1−V0 = +0.003656* lift@8 (5 feature thêm là tín hiệu THẬT); V1 vs 45deploy lift@8 +0.0097* (IC hoà).
- Sim cũ (RESULT_STAGE3_SIM_XCHECK, CHƯA parity): V1 +1.9% equity vs mốc (tốt nhất); V0 −3.7% (loại). V2/V3/V4 chưa sim.
- CÂU HỎI MỚI (chỉ trả lời được bằng sim trên G2): gate rộng + nhịp 1' + FLAT3 có làm lợi thế V1 rõ hơn không?

## Chạy
1. Xác minh bins V1: khớp giao thức WFO hiện tại (F0 PRED_PIPELINE_REPRO); CHỈ dùng fold DEV ≤2025-12-31 (BỎ fold 20260101/20260401 — trên holdout seal).
   Nếu bins V1 không tái lập được theo protocol hiện tại ⇒ retrain V1 bằng g015_net_train_add.py --drop-cols (theo fs_v9_31.stage2), seed 42.
2. Dựng pred map từ bins V1 (đường predwf tương đương predwf_G015x26 nhưng model V1), đặt WFO_FUNDING_PRED_DIR trỏ vào đó.
3. Sim trên Kaggle (jar sim-jar-gdv2, bundle x1-2021): 
   - B0 = G2+FLAT3 (bins deploy) — parity md5 650c386f BẮT BUỘC (cổng DỪNG).
   - ARM V1 = G2+FLAT3 nhưng bins V1.
   k=1 (1 ứng viên) ⇒ inflate 1.0.

## Luật kết luận (§9 + CI)
- Cổng: B0 md5 650c386f. |n_V1 − 2517| > 10% ⇒ ghi rõ (feature đổi ranking → đổi entry, xê dịch lớn hơn trailing).
- T1 rủi ro tuyệt đối §9 mỗi arm (maxDD MTM ≤40%/năm, UW ≤250, quý xấu ≥−20%, 0 năm âm, conc ≤15%). FAIL ⇒ loại.
- V1 thắng B0 ⇔ ĐẠT T1 VÀ (Calmar_MTM > B0 hoặc n cao hơn với Calmar ≥0.90×B0 — luật T4) VÀ bootstrap CI ΔCalmar_MTM
  (block-72h + episode, NREP 2000, seed 20260905) KHÔNG chứa 0 phía dương. Không đạt CI ⇒ "V1 ≈ B0" (báo thẳng, kể cả nếu điểm +1.9% lặp lại).
- Bảng quý+năm V1 vs B0; phân bổ ROI (roidist.py); so lợi thế V1 trên G2 vs +1.9% nền cũ — gate rộng có khuếch đại không.
- Không tune sau khi thấy số. KHÔNG chạm 242/shadow/holdout 2026. Job nặng Kaggle/Oracle 1/lúc ≤6GB nice. Python logging.
Kết quả: docs/result/RESULT_FEAT_ADD_V1.md + json. Commit + push.
