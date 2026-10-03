# PRE-REG — S1_FIRSTHIT_RANK: S1 ranker học nhãn first-hit FLAT3 (FHP) / NDCG@16 (FHL)

Chốt TRƯỚC khi train (chỉ mới chạy: probe cấu trúc, sinh file nhãn join, MAP_PARITY, tầng model của ORIG/CTRL có sẵn).
DEV ≤ 2025, 16 fold 20220101..20251001, fold 2026 không dùng. KHÔNG 242/shadow, KHÔNG sửa .java/build, KHÔNG Java sim
trên Oracle (sim chỉ Kaggle, `tools/kaggle_sim.py` HEAD NOWRITE242 md5 8b60b00a), train chỉ Kaggle GPU. Không tune sau số.
Bối cảnh: SELECTOR_ABLATION (33d8fc17), SELECTOR_ABLATION_R50 (b7fedef4: xáo trong top-50 mất 14,71pp CAGR), LABEL_FIRSTHIT
(c6bb9c75: nhãn FH 39,6M dòng; G015 học FH = gần random, IC 0,016), S1_RETRAIN_NOISE (f0b9d8e6: MDE80 1v1 3,3pp CAGR / 0,58 Calmar).

## 1. S1 hiện tại (đọc `research/pipeline/x1/x1_s1_rank.py`, gọi `2x1` từ `run_x1.sh`)
- Pool = ledger `cand_dev_x1` (tick 15' gate mở p15 ≥ 0,008, nBars_72h ≥ 288; 7 020 129 dòng có g1lite, ~328 coin/tick).
- **Nhãn:** `g1lite` (72h) = maxFav_72h − min(0,5·maxFav_72h, 8%) nếu maxFav_72h ≥ 5%, ngược lại retEnd_72h;
  rel = g1lite − median(tick); **relevance rel5 = ngũ phân vị trong tick (0..4)**.
- **Loss: S1 ĐÃ LÀ LambdaRank** — `XGBRanker(objective="rank:ndcg", lambdarank_pair_method="topk",
  lambdarank_num_pair_per_sample=8)`, qid = tick; 300 cây, depth 4, lr 0,05, subsample/colsample 0,8, min_child_weight 50,
  hist; 9 feature KEEP9; WFO expanding 16 fold 3 tháng, purge 72h; seed 42 hard-code.
- CTRL cùng đợt = K42 (seed 42) + S7 (seed 7) của S1_RETRAIN_NOISE (Kaggle T4, xgboost 3.2.0, dataset
  `s1-featv2-x1-20260919`), sim `s1rn-k42` / `s1rn-s7` đã có.

## 2. Arm (k = 2 họ × 2 seed {42, 7}; device cuda, xgboost 3.2.0, cùng dataset + `s1-fhrank-yfh-20261003`)
| arm | khác CTRL |
|---|---|
| **FHP** | recipe S1 y hệt (rank:ndcg, topk 8, mọi hyper-param cây), CHỈ đổi relevance rel5 → **y_FH ∈ {0,1}** (giữ nhị phân, không dùng ret168 liên tục) |
| **FHL** | như FHP nhưng truncation **NDCG@16**: `lambdarank_num_pair_per_sample=16` (với topk đây chính là truncation level) + `eval_metric="ndcg@16"` (chỉ ghi, không early-stop; 300 cây cố định) |
Hệ quả khai trước: vì S1 đã là LambdaRank topk-8, **FHL − FHP chỉ khác truncation 8 → 16**; giả thuyết "listwise" đã nằm
sẵn trong CTRL ⇒ phần lớn khác biệt FHP/FHL vs CTRL là do NHÃN. LightGBM không dùng (không cần).
Chung FHP/FHL: **purge 169h** (≥ 168h horizon nhãn + 15' lệch căn chỉnh), assert `tr.ts.max() < cut − 168h`; dòng train
thiếu nhãn ⇒ loại (ghi số/fold); OOS dự báo MỌI dòng (tập (ts,sym) == ORIG). CTRL dùng purge 72h ⇒ **giới hạn** (lệch purge
đi kèm lệch nhãn, không tách được trong vòng này).

## 3. Nhãn & ghép (`research/analysis/s1_fhrank_prep.py`, đã chạy)
- y_FH = first-hit FLAT3 của LABEL_FIRSTHIT (`~/claude_master/1003/fh/fh_all.parquet`, sha 79003f67…): +7% trước −10%
  trong 168h (tie ⇒ SL, y=0; không chạm ⇒ y = 1[ret168 > 0]); hit ∈ {0 none, 1 arm, 2 SL, 3 tie}.
- **Căn chỉnh:** dòng ledger (ts, sym) nhận nhãn FH tại (ts + 15', sym). Probe (2023Q1, 38k dòng): đồng ý
  "SL ≤ 72h (FH)" vs "maxAdv_72h ≤ −10% (ledger)" = 0,936 / 0,947 / **0,962** / 0,941 / 0,911 khi lấy nhãn FH tại ts +45' / +30' / **+15'** / 0 / −15'
  (arm vs maxFav ≥ 7%: 0,964 ở +15' vs 0,932 ở 0) ⇒ outcome ledger bắt đầu sau close nến 15' ⇒ chọn +15'. Chốt, không đổi.
- **Coverage** (file `yfh_x1.parquet`, md5 `99c1e2ee70790083632caa53e30d877d`, 7 020 129 dòng): toàn bộ 97,19%; train
  < 2022 99,99%; 2022 / 2023 / 2024 = ~100%; 2025 96,40%. Thiếu 197 036 dòng, 94% ở 12/2025 (nhãn cuối 2025-12-24 23:00 vì cửa sổ 168h
  vượt 2025) + rải rác (delist/phút thiếu); tập train fold cuối (ts < 20251001 − 169h): 3 413 511 dòng, thiếu **1 401 (0,04%)**
  ⇒ loại khỏi train. OOS chấm tầng model chỉ trên dòng có nhãn; sim dùng mọi dòng. Lệch 0 cho coverage 97,21% (tham chiếu).
- Base rate y_FH trong pool: 2021 0,585 · 2022 0,552 · 2023 0,677 · 2024 0,659 · 2025 0,519; hit: arm 51,4% / SL 39,6% /
  none 8,9%. Spearman gộp y_FH ~ g1lite 0,695 (nhãn mới tương quan mạnh nhãn cũ).

## 4. Map & cổng hợp lệ (trước sim)
1. Kernel: md5 3 file dataset assert; xgboost 3.2.0; assert purge; ts < 2026.
2. Pred mỗi arm: 6 573 909 dòng, join (ts,sym) == ORIG 100%, số dòng/fold bằng, score hữu hạn.
3. Map `x1_build_map.py s1a2x1` với `X1_G015_DIR` = bins DEPLOY `~/predwf_map_s1a2_x1` (A1 S1_RETRAIN_NOISE);
   **MAP_PARITY**: map(deploy, pred_s1a2x1 gốc) == deploy md5 16/16 — FAIL ⇒ dừng.
4. Sim: jar 7368be46, mapper ≥ 800, bins sha trong kernel == Oracle; equity 2021-12-31 bằng nhau mọi arm.
5. **B0REF4** (B0 thuần cùng đợt): md5 printDone ff3ce513 (hoặc 0 ô khác giá trị), n 2517, eq 131 908 ⇒ B0 = `selab-p0` và
   CTRL K42/S7 (ảnh cũ) dùng được; FAIL ⇒ B0 = B0REF4 và ghi CTRL lệch ảnh là giới hạn.
   **Đã chạy: MAP_PARITY_PASS 16/16** (changed 0).

## 5. Tầng model (OOS 16 fold; CHỈ báo cáo, GO quyết ở sim) — `s1_fhrank_sim.py model`
Theo arm (ORIG, K42, S7, FHP42/7, FHL42/7) — toàn kỳ + theo fold + theo năm, trung bình per-tick:
rank-IC (Spearman) vs y_FH (dòng có nhãn) và vs g1lite (nhãn S1 cũ); **lift@16** = mean y_FH top-16 − mean y_FH hạng 17–50
(theo score arm, tick > 16 dòng); **precision@16 leg xấu** = tỉ lệ hit ∈ {SL, tie} trong top-16; **NDCG@16** nhị phân
(relevance y_FH); xs-rank-corr vs ORIG; overlap top-16 vs ORIG.
Mốc đã đo TRƯỚC train (ORIG / K42 / S7): IC_yFH +0,041 / +0,042 / +0,042 · IC_g1lite +0,171 / +0,172 / +0,172 · lift@16
+0,0154 / +0,0137 / +0,0146 · top-16 y_FH 0,592 / 0,591 / 0,591 · bad@16 0,405 / 0,405 / 0,405 · NDCG@16 0,597 / 0,597 / 0,597;
xs K42~ORIG 0,984, S7~ORIG 0,981 (khớp S1_RETRAIN_NOISE ⇒ code chấm đúng).

## 6. Sim (Kaggle CPU; config B0 = profile r4_kg0_k16_f015_g155 + G2 + FLAT3; CHỈ đổi bins S1)
4 kernel `sim-fhr-{fhp42,fhp7,fhl42,fhl7}` + `sim-fhr-b0ref4`. Cửa sổ 2022-01-01..2025-12-30, equity ngày từ 2021-12-31.
Thước: MTM daily paired (block-10d, NREP 2000, seed 20260905), **k = 2 họ ⇒ CI inflate 1,18**; arm họ = trung bình 2 seed
(trung bình chỉ số trên cùng mẫu bootstrap); **CTRL = trung bình K42 + S7**. Báo: ΔCAGR, ΔmaxDD, ΔCalmar ngày vs CTRL và vs B0;
ΣPnL, n, SL%, win%, UW; ROI năm 2022–25; overlap lệnh/Jaccard vs B0; ablation: frac = ΔCAGR(họ − CTRL) / 14,71pp (gap B0 − R50).

## 7. Luật GO (mỗi họ FHP / FHL, mean 2 seed) — GO ⇔ CẢ 5:
1. ΔCAGR vs CTRL ≥ **+3,3pp** (MDE80 1-run);
2. ΔCalmar ngày vs CTRL > 0 **ngoài CI inflate 1,18** (cận dưới > 0);
3. ROI năm (họ − CTRL) dương ở **≥ 3/4 năm** 2022–2025;
4. SL% họ ≤ SL% CTRL;
5. vs B0: CI inflate của ΔCAGR **không nằm hoàn toàn dưới 0** (cận trên > 0).
Vòng GO nếu ≥ 1 họ GO (nếu cả hai: ghi cả hai, ưu tiên ΔCalmar lớn hơn). Không thêm/bớt arm, seed, thước sau khi thấy số.

## 8. Chẩn đoán nếu NO-GO (khai trước)
- **Nhãn không học được**: IC_yFH / lift@16 của FHP/FHL ≤ CTRL + 0,005 (lift) ⇒ y_FH không thêm tín hiệu thứ tự so với rel5.
- **Listwise không đổi thứ tự**: xs FHL~FHP ≥ 0,95 và overlap top-16 ≥ 0,85 ⇒ truncation 16 vô tác dụng.
- **Nhiễu**: tầng model cải thiện (lift tăng ≥ +0,005) nhưng sim Δ trong CI / < MDE.
- **Lệch hướng**: lift tăng nhưng sim xấu (proxy tầng model không chuyển — như LABEL_FIRSTHIT).

## 9. Kỳ vọng khai trước
First-hit/listwise chiếm 1/4 gap R50 ⇒ ~+3,7pp, sát MDE; **xác suất GO chủ quan ~25%** (nghiêng thấp hơn: LABEL_FIRSTHIT IC
y_FH ~0,02 toàn universe; nhãn mới tương quan 0,70 với g1lite; FHL chỉ khác FHP ở truncation).

## 10. Artifact
Code `research/analysis/s1_fhrank_{prep,kernel,sim}.py`. Oracle `~/claude_master/1003/fhr/` (kds, kout, pred, map_*, log).
Kaggle: dataset `s1-fhrank-yfh-20261003`, `fhr-bins-*`; kernel `s1-fhrank-gpu`, `sim-fhr-*`. Không push bins/nhãn/printDone.
Kết quả: `docs/result/RESULT_S1_FIRSTHIT_RANK.md` + `docs/result/s1_fhrank.json`.
