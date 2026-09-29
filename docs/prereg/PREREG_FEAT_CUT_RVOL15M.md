# PRE-REG — Cắt feature rvol15m (34% gain, #36 model selector) — đo TẦNG MODEL trước, sim sau
Chốt TRƯỚC khi xem số. Owner 09-29: "features trước, label sau; cắt feature chiếm 3x% xem sao". Feature = **rvol15m** (realized vol 15m),
per RESULT_PRESCREEN_FEAT.md #36 ~34% gain trong model selector (net015/G015 → predwf_G015x26). Nền = **G2 + FLAT3** (baseline mới đã chốt).

## BƯỚC 0 (chốt FLAT3, commit riêng TRƯỚC): tạo `profiles/g2_flat3.properties`
= r4_kg0_k16_f015_g155 + gate ratio (SIM_GATE_ROLLING_MODE=ratio, SIM_GATE_ROLLING_DAYS=90, SIM_GATE_ROLLING_PCT=0.999950829)
+ FLAT3 exit (TS_GIVEBACK_RATIO=1.0, SIM_TS_MAX_GAP=0.03, SIM_TS_MAX_GAP_WEAK=0.03; giữ SIM_RATE_PROFIT_STOP_MARKET=0.07).
Kiểm: sim profile này (jar sim-jar-gdv2, Kaggle) PHẢI md5 = FLAT3 vòng 2 = 650c386f… (n 2517). Đây thành baseline B0 của ablation.

## Phương pháp: TẦNG MODEL trước (cổng rẻ, power cao), sim chỉ khi qua
Dùng runbook `docs/runbooks/PRED_PIPELINE_REPRO.md` (F0) để build lại pred selector trên DEV.
- M_base = model selector HIỆN TẠI (có rvol15m) — tái lập, xác nhận khớp predwf_G015x26 (F0: spearman 1.0/fold, 83–88% bit-id).
- M_cut = HỆT M_base nhưng BỎ rvol15m khỏi feature list, retrain WFO đúng giao thức (train < mốc dự báo, seed cố định, KHÔNG leak, KHÔNG 2026).
- Đo mỗi fold: rank-IC (Spearman cross-section vs retEnd_4h), AUC/logloss nếu có; so M_cut vs M_base theo fold (paired), CI block-72h 2000 rep seed 20260905.
- Báo: gain của rvol15m có bị các feature khác hấp thụ không (gain top-10 M_cut vs M_base); feature nào lên thay.

## Cổng chuyển sang sim
- Nếu rank-IC M_cut KHÔNG kém M_base có ý nghĩa (CI ΔrankIC per-fold không âm ngoài 0) ⇒ chạy sim:
  arm C_cut = G2+FLAT3 nhưng dùng pred map của M_cut (bins mới). So 4 tầng §9 vs B0 (G2+FLAT3). Bảng quý+năm.
- Nếu rank-IC M_cut KÉM rõ rệt ⇒ DỪNG, kết luận rvol15m cần thiết (không sim, tiết kiệm).
- Nếu rank-IC M_cut TỐT hơn rõ rệt ⇒ ứng viên mạnh, sim + P3.

## Luật
- Không tune sau khi thấy số (đổi = amendment commit trước). k=1 (1 ablation) ⇒ inflate 1.0 cho tầng model; nếu sim, dùng luật §9.
- DEV ≤ 2025-12-31, KHÔNG chạm 2026/holdout/242/shadow. Job nặng: Kaggle hoặc Oracle 1 job/lúc ≤6GB nice. Python logging (không print ở pipeline).
- Ghi rõ đây là test trên DEV (đã test ~29 lần); rank-IC WFO power cao hơn sim PnL nên tin cậy hơn ở tầng này.
Kết quả: docs/result/RESULT_FEAT_CUT_RVOL15M.md + json. Commit + push.

## BỐI CẢNH ĐÃ TEST (bắt buộc đọc trước): A44 = 45−rvol15m ĐÃ chạy trên nền CŨ
Đọc RESULT_ARM44.md, RESULT_MODEL_RULER.md (A44), DIAG_RVOL15M.md. rvol15m = feature S1 45-cột, #36, 34.09% gain (gap 4.8x hạng 2).
Verdict CŨ (nền T170/KEEPLEG0, n~1100, gate hẹp, phí legacy): rvol15m LOAD-BEARING ở kênh XẾP HẠNG (đo độ lớn/fat-tail);
bỏ nó (A44) KHÔNG thắng, hơi TỆ hơn; ở tầng retEnd-4h-ròng ΔrankIC ≈ 0 ("bước-sai = nhãn"). ⇒ giữ rvol15m.
LÝ DO TEST LẠI (owner): nền giờ = G2+FLAT3, gate rộng hơn nhiều (n ~2500, nhịp 1'), kênh xếp hạng nuôi nhiều lệnh hơn ⇒ kết luận có thể khác.
TÁI DÙNG: nếu model/bins A44 (44 cột) còn tái lập được (tìm artifact A44 trong repo/~/kaggle_sim/~/predwf*/s1hpo), DÙNG LẠI, KHÔNG retrain lại từ đầu.
So sánh phải nêu RÕ: kết quả mới (nền G2) so verdict cũ (nền T170) — khác chỗ nào, có phải do gate rộng không.
