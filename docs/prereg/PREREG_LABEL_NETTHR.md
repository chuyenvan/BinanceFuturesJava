# PRE-REG — Label sweep NET_THR cho selector G015 (model-tier trước, sim sau) — owner 09-30 mục 1
Chốt TRƯỚC số. Nhãn train hiện tại: y = (retEnd_4h > NET_THR), NET_THR=0.015, horizon 4h (g015_net_train.py, base rate 0.1849).
Baseline B0 sim = G2+FLAT3 (md5 650c386f). Nền train = fs deploy (45 cột) — KHÔNG đổi feature (đã cạn), CHỈ đổi nhãn.

## Phương pháp: TẦNG MODEL trước (rank-IC WFO, gate-independent, power cao), sim chỉ khi qua.
Dùng docs/runbooks/PRED_PIPELINE_REPRO.md (F0). Retrain WFO đúng giao thức (train < mốc dự báo, seed 42, BỎ fold 2026 — holdout seal). KHÔNG dùng 2026.
- M_015 = nhãn hiện tại (tái lập, xác nhận khớp predwf_G015x26 — F0 spearman 1.0/fold).
- M_010 = NET_THR 0.010 (nhãn lỏng hơn, base rate cao hơn).
- M_020 = NET_THR 0.020 (nhãn chặt hơn, base rate thấp hơn).
- (tuỳ chọn M_maxfav = LABEL_MODE=maxfav thr 0.06 — chỉ nếu 2 arm trên gợi ý horizon/label-mode đáng thử; KHÔNG chạy mặc định.)
k=2 (M_010, M_020 vs M_015) ⇒ inflate sqrt(2 ln 2)=1.177 ở tầng model.

## Đo tầng model (mỗi fold, so M_015)
- rank-IC (Spearman cross-section) vs MỘT target kinh tế CỐ ĐỊNH = retEnd_4h (để so công bằng giữa các nhãn — nhãn đổi nhưng target đo giữ nguyên).
- lift@8 (top-8 admit), AUC. Paired per-fold, CI block-72h 2000 rep seed 20260905.
- Báo: đổi NET_THR có đổi THỨ HẠNG coin không (rank-IC) hay chỉ đổi calibration (P(win) mức tuyệt đối). [SUY LUẬN có kiểm]: nhãn chủ yếu đổi calibration ⇒ rank-IC ~ không đổi; nếu đúng, label-thr KHÔNG phải lever ranking.

## Cổng sim
- rank-IC arm nào TỐT hơn M_015 có ý nghĩa (CI ΔrankIC dương ngoài 0) ⇒ sim arm đó trên G2+FLAT3 (bins model mới, WFO_FUNDING_PRED_DIR), so 4 tầng §9 vs B0.
- Không arm nào hơn ⇒ DỪNG, kết luận label-threshold không phải lever (tiết kiệm sim). Nếu tất cả ~ nhau ⇒ báo "nhãn chỉ đổi calibration, gate G2 tự bù".
- CẢNH BÁO tương tác: P(win) tuyệt đối đổi theo NET_THR sẽ tương tác với gate G2 (rolling ratio trên r=p15/…). Nếu sim, phải kiểm gate có tự hiệu chỉnh không (n_pass đổi nhiều không).

## Luật chung
Không tune sau số (đổi = amendment commit trước). KHÔNG chạm 242/shadow/holdout 2026. DEV ≤2025-12-31. Retrain WFO nặng: Kaggle GPU, 1 job/lúc, seed 42.
Ổ Oracle ~95% đầy — dọn scratch sau. Python logging. Kết quả: docs/result/RESULT_LABEL_NETTHR.md + json. Commit + push.
