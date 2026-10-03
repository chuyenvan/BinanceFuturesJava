# PREREG — S1_RETRAIN_NOISE: sàn nhiễu retrain S1 ranker (đổi seed) ở tầng SIM

Chốt TRƯỚC khi train bất kỳ seed nào / xem bất kỳ số nào của vòng này. Agent thực thi KHÔNG đổi ngưỡng/công thức/nhánh
quyết định sau khi thấy số. DEV ≤ 2025, fold 2026 KHÔNG dùng. KHÔNG 242/shadow, KHÔNG sửa .java, KHÔNG Java trên Oracle.

## 0. Câu hỏi
LABEL_FIRSTHIT (`c6bb9c75`): bins sim là quantile-map **s1a2x1** — ở tick có điểm S1, S1 quyết thứ tự coin, ~70% lệnh B0
vào ở tick đó; CTRL retrain G015 (nhãn cũ) thua B0 −6,8pp CAGR CI ngoài 0 ⇒ sàn nhiễu retrain ở tầng sim có thể rất lớn.
R50 (`b7fedef4`): giá trị selector nằm ở xếp hạng top-50→16. Trước khi cải thiện S1 phải đo:
**retrain S1 ranker đúng recipe, chỉ đổi seed ⇒ CAGR/Calmar sim dao động bao nhiêu? B0 nằm đâu? MDE cho S1 mới?**

## 1. Feasibility (đã làm trước pre-reg, chỉ đọc code/hash — chưa có số nào của seed mới)
- Pipeline S1 deploy (`docs/experiment/X1_EXTEND.md`, `research/pipeline/x1/run_x1.sh`):
  `x1_s1_rank.py 2x1` (ledger `cand_dev_x1`, feature `feat_v2_x1` KEEP-9, 16 fold CUTS16 20220101..20251001, OOS 3 tháng,
  purge 72h, `assert tr.ts.max()<c`, nhãn `rel5` = ngũ phân vị trong tick của `g1lite − median_tick`, qid = tick) →
  `~/ledger/pred_s1a2x1.parquet` (sha256 `2618fe1a…` — khớp X1_EXTEND, đo lại hôm nay) → `x1_build_map.py s1a2x1`
  với `X1_G015_DIR=~/f0_repro/g015x26_regen` ⇒ bins `~/f0_repro/predwf_map_s1a2_x1` (MAP_PARITY_PASS 16/16 ở LABEL_FIRSTHIT).
- Recipe gốc: `XGBRanker(objective=rank:ndcg, n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8,
  colsample_bytree=0.8, min_child_weight=50, n_jobs=4, tree_method=hist, random_state=42, lambdarank_pair_method=topk,
  lambdarank_num_pair_per_sample=8)`, xgboost 3.2.0, Oracle CPU aarch64. **Seed gốc = 42** (hard-code). Model shuffle
  (`X1_SHUF`) chỉ ghi log, không vào pred.
- Dữ liệu: `~/featv2/feat_v2_x1.parquet` KHÔNG còn trên Oracle. Dùng Kaggle dataset `chuyendinh/s1-featv2-x1-20260919`
  (`feat_v2_x1_keep9.parquet` md5 `1aa3b97490cb68d6ce654051184eae7c`, `cand_dev_x1_lite.parquet` md5
  `2cc8381e0577b5289fa1e5714fd865fe`; sinh bởi `~/s1hpo/kaggle_ds/make_reduced.py` từ đúng 2 file gốc, chỉ cắt cột
  ts,sym,KEEP9 / ts,sym,g1lite và ép float64→float32 — xgboost vốn train trên float32). Vòng S1_HPO đã dùng dataset này.
- Sim: tái dùng đường `research/analysis/label_firsthit_sim.py` (= SELECTOR_ABLATION: kernel `tools/kaggle_sim.py` HEAD
  NOWRITE242 md5 `8b60b00a`, jar `7368be46`, profile `r4_kg0_k16_f015_g155` + B0OV, prefix 2021H2 = `moc21` chung,
  funding.bin dựng lại trong kernel bằng `s3_funding.py`), CHỈ đổi nguồn 16 bins arm.
- Chi phí ước: 1 kernel Kaggle GPU (4 arm GPU + 1 arm CPU chẩn đoán), 5 kernel sim CPU song song (~35'), map ~vài phút/arm.

## 2. Thiết kế
### 2.1 Arm train (MỘT kernel Kaggle GPU, `pip install xgboost==3.2.0`; dữ liệu/fold/nhãn/hyper-param y hệt §1)
| arm | random_state | backend | vai trò |
|---|---:|---|---|
| **S7** | 7 | `device=cuda`, hist | seed mới |
| **S13** | 13 | `device=cuda`, hist | seed mới |
| **S21** | 21 | `device=cuda`, hist | seed mới |
| **K42** | 42 | `device=cuda`, hist | đối chứng MÔI TRƯỜNG: seed gốc, chỉ khác backend/máy ⇒ tách "nhiễu seed" khỏi "lệch môi trường" |
| KC42 | 42 | CPU hist `n_jobs=4` | CHẨN ĐOÁN tầng model (KHÔNG sim): tách lệch kiến trúc x86 vs aarch64 khỏi lệch GPU |
**Lệch recipe khai trước:** backend `cuda` thay CPU gốc — do ràng buộc "train chỉ Kaggle GPU"; mọi S1 mới về sau cũng sẽ
train ở môi trường này ⇒ sàn nhiễu đúng cho MDE là sàn Kaggle-GPU. K42 đo trực tiếp lệch môi trường so với B0.
Thứ tự train: K42, S7, S13, S21, KC42 (mất KC42 nếu hết giờ không ảnh hưởng thước chính). Score = −p (như gốc).

### 2.2 Bins
Mỗi arm: `x1_build_map.py s1a2x1 <map_arm>` với `X1_G015_DIR=~/f0_repro/g015x26_regen`, `X1_CUTS=CUTS16`, pred arm đặt
tạm dưới tên `pred_s1a2x1rn<arm>` trong `~/ledger` (không ghi đè file gốc). **G015 giữ nguyên bins gốc — chỉ đổi S1.**
Trước khi map: dựng lại ORIG bằng cùng lệnh ⇒ md5 16/16 == `~/f0_repro/predwf_map_s1a2_x1` (MAP_PARITY), FAIL ⇒ DỪNG.

### 2.3 Sim (Kaggle CPU, config B0, cùng đợt)
Arm sim: K42, S7, S13, S21 (đường label_firsthit_sim) + **B0REF3** = B0 thuần (cấu hình `selab-b0ref`, kaggle_sim HEAD
md5 `8b60b00a`). B0 dùng cho thước = legs `selab-p0` (md5 printDone `ff3ce513`, n 2517, eq 131 908) **nếu** B0REF3
md5 == `ff3ce513` HOẶC printDone B0REF3 vs `selab-p0` 0 ô khác giá trị float32 VÀ n/eq khớp; ngược lại B0 := B0REF3
(cùng đợt) và ghi "ảnh Kaggle đã đổi".

## 3. Thước
Cửa sổ CHÍNH: 2022-01-01..2025-12-30, equity ngày từ 2021-12-31, lệnh vào ≥ 2022 (như LABEL_FIRSTHIT §5).
Phụ: toàn kỳ MTM phút (`reset_rule_score.run_mtm`, legacy).
- Mỗi arm + B0: CAGR %, maxDD MTM ngày %, **Calmar_MTM ngày**, (toàn kỳ) CAGR / DD MTM phút / Calmar MTM phút / UW ngày,
  n, SL %, ΣPnL, win %, ROI năm 2022–2025, overlap tập lệnh vs B0 (`SAD.overlap`, % lệnh B0 + Jaccard).
- Phân phối seed: mean, sd (ddof=1) trên **{S7,S13,S21}** (CHÍNH); phụ trên {K42,S7,S13,S21} (4 điểm Kaggle).
- Vị trí B0: **z3 = (B0 − mean3)/sd3** cho CAGR (CHÍNH) và Calmar ngày (phụ); z4K so với 4 điểm Kaggle; z_pool = vị trí
  B0 trong 4 điểm gộp {B0,S7,S13,S21} (chặn trên ~1,5 do cấu tạo n=4 — chỉ mô tả) + thứ hạng B0.
- MTM paired từng arm − B0 (S7, S13, S21, K42) và mean(S7,S13,S21) − B0: ΔCAGR, ΔCalmar ngày, block-10d,
  NREP 2000, seed 20260905, k=1 (CI raw) — `selector_ablation_driver.daily_boot/ci_of`.
- Tầng model (OOS 16 fold, so với ORIG = `pred_s1a2x1`): xs-rank-corr Spearman per tick (tick ≥ 10 coin) mean theo fold;
  overlap top-16 trong tick (|top16_arm ∩ top16_ORIG|/16); edge5 g1lite; cùng các thước cho từng cặp seed với nhau.

## 4. Kết luận khai trước (CHÍNH = z3 trên CAGR cửa sổ 2022+)
- **|z3| < 1 ⇒ "B0 là realization bình thường"** của recipe S1.
- **z3 > 1,5 ⇒ "B0 may mắn"** (deploy là lần rút tốt bất thường; kỳ vọng retrain bất kỳ ≈ mean3).
- 1 ≤ z3 ≤ 1,5 ⇒ "B0 trên trung bình, chưa đủ gọi may mắn" (biên). z3 ≤ −1 ⇒ "B0 dưới trung bình retrain".
- Calmar ngày: cùng luật, chỉ báo cáo phụ (không đổi kết luận chính).
- **Môi trường:** nếu |K42 − B0|_CAGR > 2·sd3 ⇒ "lệch môi trường > nhiễu seed" ⇒ CTRL cho S1 mới PHẢI train cùng môi
  trường (Kaggle-GPU, cùng đợt), cấm so với B0 deploy. Ngược lại ghi "lệch môi trường trong tầm nhiễu seed".
- **MDE80** (α=0,05 hai phía, power 0,8; z_{0,975}+z_{0,80} = 1,960+0,842 = **2,802**), σ = sd3(CAGR):
  - MDE80_vsMean = 2,802·σ — S1 mới 1 run so với baseline mà mean đã biết chính xác (công thức brief, ≈2,8·sd);
  - MDE80_1v1 = 2,802·√2·σ — 1 run S1 mới vs 1 run CTRL cùng đợt (tình huống thực tế);
  - MDE80_mxm = 2,802·σ·√(2/m), m seed mỗi arm, bảng m ∈ {1,2,3,5}. Cùng bảng cho Calmar ngày.
  σ là nhiễu GIỮA các lần retrain trên CÙNG đường thị trường; CI bootstrap thời gian (paired) là nguồn nhiễu khác —
  báo cáo cả hai, không cộng gộp.
- Ghi thẳng: sd từ n=3 rất thô (CI95 của σ ≈ [0,52σ̂; 6,28σ̂], χ² 2 bậc tự do) ⇒ z3 và MDE mang tính định cỡ, không
  phải kiểm định; kết luận phải đọc kèm độ rộng này.

## 5. Sanity / cổng (FAIL ⇒ DỪNG, không chấm)
1. Kernel: md5 2 file dataset == §1; `xgboost.__version__ == 3.2.0` (pip lỗi ⇒ DỪNG, không âm thầm dùng bản khác);
   `assert tr.ts.max() < c` mỗi fold; 16 fold mỗi arm; mọi ts < 2026-01-01 GMT+7.
2. Oracle: mỗi arm tập (ts,sym) OOS == `pred_s1a2x1` (join 100%, số dòng/fold bằng nhau); score hữu hạn.
3. K42: mean xs-corr per tick K42~ORIG ≥ 0,80, ngược lại DỪNG (nghi lỗi pipeline, không phải nhiễu).
4. MAP_PARITY ORIG (§2.2). Bins sha trong kernel == Oracle; jar sha; mapper ≥ 800; funding md5 ghi lại.
5. Equity ngày 2021-12-31 bằng nhau mọi arm (prefix 2021H2 chung) — ghi; B0REF3 parity theo §2.3.

## 6. Rủi ro khai trước
- n = 3 seed: sd thô (§4). Không thêm seed sau khi thấy số (nếu cần, vòng sau pre-reg riêng).
- Backend cuda ≠ CPU gốc: K42 + KC42 dùng để tách; nếu K42 lệch B0 nhiều, "B0 vs seed" lẫn hiệu ứng môi trường —
  kết luận chính vẫn đọc theo z3 nhưng phải nêu song song vị trí K42.
- Seed đổi đồng thời subsample + colsample ⇒ đây là nhiễu recipe "tự nhiên", đúng thứ cần đo.
- Không đo nhiễu do G015 (giữ nguyên) — sàn retrain G015 đã có ở LABEL_FIRSTHIT.

## 7. Output
`docs/result/RESULT_S1_RETRAIN_NOISE.md`, `docs/result/s1_retrain_noise.json`, script `research/analysis/s1_retrain_noise_*.py`.
Artifact Oracle `~/claude_master/1003/s1rn/` (pred, map bins, log). Không push bins/printDone.
