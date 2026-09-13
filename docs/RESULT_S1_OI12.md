# RESULT_S1_OI12 — mo rong S1 9 -> 12 feature (oi_z, ls_toptrader, taker_buy) tren DEV 2021

Pre-reg: `docs/PREREG_S1_OI12.md` (commit fb142d0, chot TRUOC khi chay variant).
Nen: DEV mo rong 18 fold (2021Q3..2025Q4), dataset `wfo_ds_x1_2021`, bins `predwf_map_s1a2_x1_2021`,
baseline `X1_GS_T170_2021` (md5 efb793e2, n=1089). Jar HEAD 8650f19 (KHONG rebuild). SIM_END_DATE=20251231,
holdout 2026 nguyen ven. KHONG cham 242, KHONG tune, KHONG push, KHONG doi code Java.

## 0. Phan quyet (so truoc)
- **REPRODUCTION: PASS** (3 cong doc lap deu tuyet doi).
- **S1_OI12 vs T170: NULL.** 0 rate CHAT LUONG ngoai CI (can >=2). Moi rate chat luong lech HUONG XAU
  nhung deu TRONG CI: win% -0.90, TSloss% +0.70, meanP -0.304, mP|SL -0.93. PASS rang buoc cung ca 5 nam
  (nhu baseline) nhung te hon nhe moi mat: equity 104312 vs 111070, CAGR 27.48 vs 29.27, UW 119 vs 92.
- **3 feature moi CO duoc model dung** (2022+: taker_buy 0.080, oi_z 0.031, ls_toptrader 0.023) va lam TANG
  edge5 ranking g1lite (+15.91% vs 9-feat), NHUNG KHONG chuyen thanh entry tot hon duoi gate T170 (trung tinh
  -> hoi xau, trong nhieu). 2021: ca 3 feature = 0.000 (ledger 2021 nho, model bo qua).

## 1. Reproduction gate (PASS)
- **R1 S1-model (byte-level):** x1_s1_save_all_folds.py retrain 9-feat 16 fold vs pred_s1a2x1 (bins hien):
  16/16 fold **spearman 1.000000000, maxd 0, top8 100%**, ALL_PASS=True. S1 train tat dinh tuyet doi.
- **R2 sim/jar:** re-run baseline T170 tren wfo_ds_x1_2021 (jar hien Sep-13) -> printDone md5 **efb793e2**
  = trung baseline goc byte-for-byte (1089 lenh). Jar KHONG doi hanh vi sim.
- **R3 dataset (bonus):** build lai dataset baseline (9-feat bins) CUNG session -> sim T170 -> md5 **efb793e2**
  trung tuyet doi. Chung minh md5_market non-deterministic (byte-order Aerospike: old 4ab691 / variant e39d320
  / base_now e8b3fa6c, cung 2554812 rec) KHONG anh huong ket qua sim. => variant vs efb793e2 la apples-to-apples.

## 2. Chuoi variant (chi doi FEATURE S1)
- S1 rank 12-feat: x1_s1_rank_oi12.py = ban sao x1_s1_rank.py CHI doi dong KEEP (diff 1 dong). 2022+ 16 fold
  -> pred_s1a2x1oi12.parquet; 2021 2 fold -> pred_s1a2x1oi12_y21.parquet.
- build_map (quantile-map giu NGUYEN phan phoi P(win) net015 per tick): 2022+ (G015 predwf_G015x26) doi 18.2%
  coin->p; 2021 (G015 x26-2021) doi 5.3%. -> predwf_map_s1a2_x1_oi12_2021 (18 bins). pred.bin (net015 gate)
  IDENTICAL baseline; funding.bin (selector S1) DIFFERS -> ranking 12-feat da vao dataset.
- ExportWfoDataset -> wfo_ds_x1_oi12_2021 (foldCount=18, marketCount 2554812 khop, leakFreeFrom 2021-07-01,
  HOLDOUT SEAL cat >=2026). Sim gate T170 (profile x1_gs_t170) -> X1_GS_T170_OI12_2021 md5 9fbb882c.

## 3. Bang chinh (equity/CAGR KHONG phai tieu chi)
| tag | scale | n | win% | TSloss% | meanP | maxDD% | UW | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|
| X1_GS_T170_2021 (baseline) | 1.70 | 1089 | 88.25 | 9.73 | 5.244 | -11.84 | 92 | 111070 | 29.27 |
| X1_GS_T170_OI12_2021 (variant) | 1.70 | 1083 | 87.35 | 10.43 | 4.940 | -11.57 | 119 | 104312 | 27.48 |

## 4. CI khoi-72h x1.21 (variant - baseline), k=1 — TOAN CUA SO (n_A=1083 n_B=1089)
| rate | hieu | lo | hi | ngoaiCI |
|---|---|---|---|---|
| win% | -0.896 | -1.951 | +0.196 | - |
| TSloss% | +0.700 | -0.295 | +1.631 | - (xau, trong CI) |
| mP\|SL | -0.932 | -1.927 | +0.091 | - |
| meanP | -0.304 | -0.748 | +0.124 | - |
=> **so rate CHAT LUONG ngoai CI = 0** (can >=2 de THANG). Theo NAM (2021..2025): moi nam cung 0 rate ngoai CI.

## 5. Rang buoc cung tung nam (maxDD<=15, UW<=120, nam>=0, quy>=-5) — x1_rates
| tag | 2021 | 2022 | 2023 | 2024 | 2025 | verdict |
|---|---|---|---|---|---|---|
| baseline | PASS | PASS(DD-11.84) | PASS | PASS(UW92) | PASS | **PASS 5 nam** |
| S1_OI12 | PASS | PASS(DD-11.57) | PASS | PASS(UW119) | PASS(ret26.0) | **PASS 5 nam** (UW 2024 119 sat tran 120) |
n_eff muc lenh: baseline 96, variant 97 (power tuong duong).

## 6. Feature importance (imp fold cuoi moi arm)
- 2022+ (fold 20251001, du lieu day): vol_7d .272 rk_dd_7d .178 ret_14d .140 rk_ret_3d .100 **taker_buy .080**
  ret_3d .055 ls_global .036 **oi_z .031** dd_7d .031 hrs_since_high_7d .031 **ls_toptrader .023** rk_oi_delta24h .022.
  => ca 3 feature moi duoc model dung (tong ~0.134 imp). edge5 ranking g1lite +15.91% t=73.4 (vs 9-feat) —
  ranking "tot hon" tren g1lite nhung KHONG cai thien trade duoi gate T170.
- 2021 (fold 20211001, ledger nho): oi_z / ls_toptrader / taker_buy = **0.000** (cung ls_global, rk_oi_delta24h)
  => 2021 model ~ khong dung feature moi; edge5 +7.522% ~ 9-feat +7.545%.
- Rank-IC vs rel (pool, theo nam): oi_z mean +0.028 (consistent), ls_toptrader -0.022 (KHONG consistent, doi dau),
  taker_buy +0.004 (KHONG consistent). Chi oi_z co tin hieu nho on dinh; 2 feature con lai nhieu/doi dau.

## 7. Phan quyet
- **S1_OI12: NULL.** 0/2 rate chat luong ngoai CI; moi diem lech huong xau (trong nhieu). Them 3 OI feature
  KHONG cai thien ranking-cho-trade duoi gate T170. KHONG dang deploy. Giu S1 9-feat.
- Feature moi khong vo dung ve ly thuyet (model co dung, edge5 g1lite tang) nhung tin hieu do bi gate T170 +
  selector top-8 hap thu, khong ra alpha rong.

## 8. Ghi chu van hanh + tai lap
- Artifact: `predwf_map_s1a2_x1_oi12_2021/` (18 bins), `wfo_ds_x1_oi12_2021/`, ledger pred_s1a2x1oi12{,_y21}.parquet,
  devrun X1_GS_T170_OI12_2021 (md5 9fbb882c) + X1_GS_T170_2021_RE / X1_GS_T170_BASE_NOW (repro efb793e2).
- Script: research/pipeline/x1/x1_s1_rank_oi12.py, profiles/x1_c3_oi12_2021build.properties (deu chi doi 1 dong).
- Cham: python3 research/analysis/x1_rates.py X1_GS_T170_2021 X1_GS_T170_OI12_2021.
- KHONG cham 242 / holdout 2026, KHONG deploy, KHONG git push, KHONG doi code Java / rebuild jar.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
