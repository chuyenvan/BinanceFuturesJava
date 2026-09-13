# PREREG_S1_OI12 — mo rong S1 tu 9 -> 12 feature (them 3 OI: oi_z, ls_toptrader, taker_buy)

Pre-reg CHOT TRUOC khi chay variant. Nen: DEV mo rong 18 fold (2021Q3..2025Q4), dataset
`wfo_ds_x1_2021`, bins `predwf_map_s1a2_x1_2021`, baseline `X1_GS_T170_2021` (md5 printDone
`efb793e2`, n=1089). Session Opus. LUAT: chi Oracle, KHONG cham 242, KHONG git push,
KHONG tune (feature list co dinh pre-reg), KHONG cham holdout 2026 (train <= 2025-12-31).

## 1. Muc tieu
S1 12 feature = 9 hien + **oi_z, ls_toptrader, taker_buy** (raw, dung dang featv2 luu; KHONG them
rank-version de tranh no feature). Gia thuyet: them OI/positioning -> ranking tot hon -> entry tot hon.
KEEP moi (12) = ["vol_7d","dd_7d","rk_dd_7d","hrs_since_high_7d","ret_3d","rk_ret_3d","ret_14d",
"ls_global","rk_oi_delta24h","oi_z","ls_toptrader","taker_buy"].

## 2. Baseline vs Variant
- Baseline = **X1_GS_T170_2021** (S1 9-feat + gate T170 scale 1.70). md5 efb793e2, n=1089.
- Variant  = **S1_OI12** (tag run: X1_GS_T170_OI12_2021): S1 12-feat + gate T170, CUNG dataset/
  bins-rebuild, CUNG net015 (quantile-map giu NGUYEN phan phoi P(win) per tick), CUNG gate/exit/
  sizing (profile x1_gs_t170.properties), CUNG config sim_dev_file_2021, CUNG net015 cut hien dung.
- Chi doi DUY NHAT: feature set S1 (9 -> 12). Moi thu khac giu nguyen chuoi baseline.

## 3. Cong (gate)
(a) REPRODUCTION — 2 cong doc lap, deterministic (CPU seed42, shuffle off):
  - R1 S1-model: x1_s1_save_all_folds.py retrain 9-feat 16 fold -> spearman==1.0 & top8 100% vs
    pred_s1a2x1 (bins hien). FAIL -> DUNG.
  - R2 sim/jar: re-run baseline T170 tren wfo_ds_x1_2021 (jar HEAD hien) -> md5 printDone == efb793e2.
    Neu jar da doi hanh vi (md5 khac) -> dung ban RE-RUN cung jar lam anchor cham diem, ghi ro lech.
(b) chi doi FEATURE S1; net015 mapped + gate + dataset-build + config + profile giu nguyen.

## 4. Chuoi chay variant (tuan tu, 1 job nang / box)
1. S1 rank 12-feat 2022+ (x1_s1_rank_oi12.py = ban sao x1_s1_rank.py CHI doi KEEP; X1_CUTS=16 fold,
   X1_LNAME=cand_dev_x1, X1_FEAT=feat_v2_x1) -> pred_s1a2x1oi12.parquet.
2. S1 rank 12-feat 2021 (X1_CUTS="20210701 20211001") -> pred_s1a2x1oi12_y21.parquet.
3. build_map: name s1a2x1oi12 (G015=claudedata/predwf_G015x26, 16 fold) + name s1a2x1oi12_y21
   (G015=kg015x26_2021/g015x26-2021-gpu/out, 2 fold) -> predwf_map_s1a2_x1_oi12_2021 (18 bins).
   Sanity: build_map bao "phan phoi p per tick == p cu" (gate dong y het).
4. ExportWfoDataset -> wfo_ds_x1_oi12_2021 (profile x1_c3_oi12_2021build = ban sao x1_c3_2021build
   CHI doi WFO_FUNDING_PRED_DIR; config sim_dev_file_2021; market tu Aerospike). Sanity:
   md5_market == 4ab691c908fc545c26243e8328d7a0a6, foldCount=18, HOLDOUT SEAL cat >=2026.
5. Sim gate T170 (profile x1_gs_t170) SIM_END_DATE=20251231 -> X1_GS_T170_OI12_2021 printDone.

## 5. Cham + quyet dinh
- python3 research/analysis/x1_rates.py X1_GS_T170_2021 X1_GS_T170_OI12_2021 (k=1, mot variant).
  CI = variant - baseline (block-72h x1.21).
- Quyet dinh = LUAT CU: **THANG** neu >=2 rate CHAT LUONG (bo n, mMargin) ngoai CI CUNG HUONG TOT
  + PASS rang buoc cung (maxDD<=15, UW<=120, nam>=0, quy>=-5) KHONG te hon baseline. Nguoc lai **NULL**.
  (Baseline T170 da PASS rang buoc cung ca 5 nam.)
- Ghi feature importance: 3 feature moi co duoc model dung khong (importance > 0, Delta).

## 6. Ngoai pham vi
holdout 2026, tune (KHONG sweep feature, KHONG chon feature theo ket qua), 242, deploy,
doi code Java / rebuild jar.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
