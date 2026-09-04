# S1_PROVENANCE — bins predwf_map_s1a2 (selector THAT cua C2b) TAI LAP BYTE-IDENTICAL

Sinh luc: 2026-09-04 (Oracle, CPU). Tuan theo `docs/PREREG_S1PROV.md` (commit 020be5b).
S1 = selector + gate that cua C2b (`profiles/c2b.properties:23`
`WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2`). Day la VIEC VE SINH: chi tuyen bo
**he S1 TAI LAP DUOC**, KHONG tuyen bo gi ve "S1 tot hon" (khung NBETS / `power_wall`).

## 0. Ket qua tai lap — BYTE-IDENTICAL 3 NGUON

Chay **2 lan doc lap** (`r1`, `r2`) tron pipeline `s1_rank.py -> build_map.py` tu input ghim,
CPU. So sha256 tung file bins voi (i) `r2`, (ii) deploy `predwf_map_s1a2/`, (iii) backup Kaggle
`chuyendinh/predwf-map-s1a2-bins` (tai ve, giai nen, sha256).

| Phep so | Ket qua |
|---|---|
| `r1` vs `r2` (deterministic) | **byte-identical 10/10 fold** |
| `r1` vs **deploy** `predwf_map_s1a2/` | **byte-identical 10/10 fold** |
| `r1` vs **backup Kaggle** | **byte-identical 10/10 fold** |
| aggregate `bins.sha256` (noi tiep 10 file sort theo ten) | `0f8721558fbd87ef0bca8d2507b6eb0ed394efd746f59d4bc024e68b461d86ec` — **khop** ban ghi cu (`BINS_MANIFEST §2b`) |
| `edge5 g1lite OOS` pred r1 | **+6.8043%** (khop `BINS_MANIFEST`/`S1v2.out` +6.80%) |
| `spearman(pred_r1, pred deploy)` | **1.00000000** (774,270 dong chung) |
| so ban ghi lech thu hang trong tick (method=first) | **0 / 774,270** |

=> Dat **tieu chi CHINH** cua pre-reg (bins byte-identical), khong phai du phong. **He tai lap
duoc**, va ban dang deploy trung khop ban rebuild lan backup Kaggle tung byte.

**Lo `cand_dev` da DONG bang bang chung.** `ledger/cand_dev.parquet` bi build lai 2026-09-03 17:53,
SAU khi `pred_s1a2.parquet` sinh 2026-09-02 22:49 (`README §7`). Ban `cand_dev` 09-02 da mat.
Rebuild tu `cand_dev` HIEN TAI van cho bins **byte-identical deploy** => `cand_dev` hien tai sinh
**dung thu hang trong tung tick** nhu ban 09-02. Vi bins chi phu thuoc THU HANG (build_map.py:39-41),
dong nhat hang la du va o day con manh hon: dong nhat BYTE. Lo la **lanh tinh, da dong**.

## 1. Bins — `/home/ubuntu/predwf_map_s1a2/` (deploy = rebuild `predwf_s1_v2/`)

Dinh dang: 26 B/rec big-endian `[ts:int64][symId:int16][p4h,p12h,p24h,p72h:float32]`, slot `p0`=p4h,
`WFO_SEL_HORIZON_IDX=0`, `score = 1 - P(win)` (engine dao dau). Manifest sha co-located:
`predwf_s1_v2/MANIFEST.sha256` (ban rebuild); deploy co `predwf_map_s1a2/BINS_SHA256`.

| File | rec | sha256 |
|---|---|---|
| predict_wf_20220101.bin | 1,123,854 | `beb9b1ad87920837c37a4fbad987d7266a8fdc65e872901f23bff6e877b9fca4` |
| predict_wf_20220401.bin | 1,172,010 | `46d74f5af24408e29c4c89a5b0578e6b3b510ebd49341746368cbd88d1e54703` |
| predict_wf_20220701.bin | 1,188,418 | `bba6d88bb55475d2b27524a8745a9cd1cd5e1c3a81246f98ac43749a928d8de6` |
| predict_wf_20221001.bin | 1,242,626 | `52de4cf735a16ff3f35c7db01278ffa6740defccc28817d48c2f46af50d3b3c8` |
| predict_wf_20230101.bin | 1,302,607 | `5fbeeb76e766885a9f25003937f79aa5f97fe56fbe46d4be5c6bcaa9b44b21a1` |
| predict_wf_20230401.bin | 1,524,605 | `9dc70e5173d55e56f07b5e2d8dc57eccee8368887c2d54b819cabf146306697a` |
| predict_wf_20230701.bin | 1,671,614 | `f34966245a911853967e8028bf54b4be294ba150ece54f16ff8e93cc3e4ee264` |
| predict_wf_20231001.bin | 1,912,959 | `48d51834bb718cac1b4b089a33ebd953bbce2bb83348c7a2f62fb083f5e55005` |
| predict_wf_20240101.bin | 2,140,992 | `ac1fadf2c90836a8b6f13f470910785504de111e3d7449e9a3990ac60a148f08` |
| predict_wf_20240401.bin | 2,256,504 | `82d1b979cabda8aa3a5ee94ccdec95a00483150d93657a33189ceaa9f733e6ae` |

10 fold roi nhau, fold dai nhat 91 ngay < 100 => khong `LEAK-SUSPECT`. Khong co fold 20240701 /
20241001 => bins khong the cham VALIDATION. `predwf_s1_v2/` la ban rebuild giu lam nguon chinh thuc
(byte-identical deploy); KHONG ghi de deploy.

## 2. Input duoc ghim — sha256

Bang day du: `research/analysis/s1prov_inputs_sha.json` (commit cung PREREG 020be5b).
Manifest digest: `sha256(s1prov_inputs_sha.json) = ca1d262d347d04b6c8c8c0516897f763dd9c8f272b77f596c8f98a47354bb809`.

| nhom | file | sha256_16 | bytes |
|---|---|---|---|
| feature hourly (KHONG rebuild) | `featv2/feat_v2.parquet` | `29d2c1e09c1b320e` | 955,376,251 |
| candidate ledger (dau vao s1_rank) | `ledger/cand_dev.parquet` | `31876176cd60205c` | 30,494,120 |
| gate pred p15 (nguon cand_dev) | `claudedata/wfo_gate_pred.csv` | `ac5f6365dee520ec` | 92,509,649 |
| OI (SACH, KHONG rebuild) | `claudedata/oi/oi_percoin_full.bin` | `e3887f6309729965` | 4,227,723,300 |
| symbol map (ledger) | `selector_pred_out/symbol_map.csv` | `41ee8f1b96b8a01c` | 10,964 |
| symbol map (feat/oi) | `claudedata/oi/symbol_map.csv` | `3f8175512f385d83` | 11,232 |
| G015 source bins DEV (build_map tai phan phoi p) | `claudedata/predwf_G015x26/predict_wf_{10 fold}.bin` | xem json | — |
| label DEV (nguon cand_dev) | `label_15m/funding_label_{14 file}.pb` | xem json | — |

**DEV-only:** chi hash 14 file label DEV (den `20240401_to_20240701`) + 10 G015 source bins DEV;
`ledger.py:33` glob co the cham file VAL nhung `ledger.py:17,28` loc `ts < 2024-07-01` (0 dong VAL).
OI **KHONG rebuild** (code hien tai gay leak — `docs/OI_FIX_LOG.md`); sha dung lai tu `G015_PROVENANCE`.

## 3. Lenh chinh xac + moi truong

- Script (ban DA sinh deploy, sha256 khop `BINS_MANIFEST §4`):
  - `s1_rank.py 2` -> `ledger/pred_s1a2.parquet` (sha `e61120940109bb59...` = ban featv2).
  - `build_map.py s1a2 /home/ubuntu/predwf_map_s1a2` (sha `f5323b1f3e3a0c0f...`).
  - Ban trong git (canonical, khac ban da chay CHI o `print` -> `logging`, logic 0 doi):
    `research/pipeline/s1_rank.py`, `research/pipeline/build_map.py`.
- Rebuild job nay: chay dung 2 script featv2 tren (sha da doi chieu truoc khi chay), suffix moi
  `2r1`/`2r2` -> bins ra `/home/ubuntu/predwf_s1_v2{,_r2}`, KHONG ghi de deploy; pred tam trong
  `ledger/` da xoa sau khi so; `pool_rankic.csv` khoi phuc ban goc.
- Moi truong: python **3.10.12**, xgboost **3.2.0** (`XGBRanker objective=rank:ndcg`,
  `tree_method=hist`, **CPU** `n_jobs=4` co dinh, `random_state=42`), numpy 2.2.6, pandas 2.3.3,
  scipy 1.15.3 (theo `research/pipeline/README.md §4`).
- Thoi gian: s1_rank 286.6s (r1) / 283.8s (r2); build_map 6.8s / 5.7s; tong 9.8 phut ca 2 run.

## 4. Hyperparameter that (doc tu code s1_rank.py)

`XGBRanker(objective="rank:ndcg", n_estimators=300, max_depth=4, learning_rate=0.05,
subsample=0.8, colsample_bytree=0.8, min_child_weight=50, n_jobs=4, tree_method="hist",
random_state=42, lambdarank_pair_method="topk", lambdarank_num_pair_per_sample=8)`.
- **label** `rel5` = `min(int(rank_pct(rel)*5),4)`, `rel = g1lite - median_tick(g1lite)` — ngu phan
  vi **TRONG TICK** (cross-sectional), khong phai gia tri tuyet doi.
- **group (qid)** = 1 tick 15m (`pd.factorize(ts)`).
- **WFO** 10 fold cutoff `20220101..20240401`, OOS 3 thang, **purge 72h**, `assert tr.ts.max()<c`.
- 9 feature `KEEP` = `vol_7d, dd_7d, rk_dd_7d, hrs_since_high_7d, ret_3d, rk_ret_3d, ret_14d,
  ls_global, rk_oi_delta24h`.
- **build_map**: trong tung tick, coin CO score nhan lai chinh tap gia tri `p` cua G015 trong nhom do
  theo thu hang score; coin khong score giu `p` cu => **phan phoi P(win) theo tick GIU NGUYEN cua G015**,
  bins chi phu thuoc **thu hang** cua S1. Ti le `changed` = 4.9%.

## 5. Vi sao CPU

GPU (`device=cuda`) khong tai lap theo bit cho rankIC/rho (da do o G015 + `power_wall`). CPU `hist`
`nthread=4` co dinh cho ket qua **byte-identical** giua r1/r2 va khop deploy. Baseline chinh thuc
la con so CPU.

## 6. Ly do cat 40 -> 9 feature — KHOI PHUC DUOC TOI DAU

**Van ban quy tac cat (R1-R4) KHONG tai lap duoc.** `v5_train_v3.py` docstring ghi
"cat 28/37 theo quy tac R1-R4 trong PROCESS_LOG"; **`PROCESS_LOG.md` khong ton tai tren dia va
chua tung vao git** (kiem: `find -iname *process_log*` rong; `git log --all --diff-filter=A` rong).
Cac "R1-R4" tim thay trong `docs/archive` la luat van hanh "CE-first", KHONG lien quan cat feature.
=> **Ly do CHON tung feature da mat. 9 feature la du kien; van ban quy tac cat thi khong.**

**Nhung BANG CHUNG lam nen phep cat thi con** (khong bia):
- `featv2/SPEC_FEAT_V2.md` (pre-reg 40 feature + 3 nhieu, 2026-09-02 16:17): quy trinh V1-V6,
  tieu chi, cam "tune feature theo ket qua".
- `featv2/ic_stab.py` + `IC_STAB.out` + `IC_stab.csv`: chan doan cat = IC theo NAM (2021-2024H1) x
  3 nhan, do nhat quan dau, `min|IC|`, va **cum feature trung `|rho|>0.8`** — 9 feature giu khop
  voi ba tieu chi nay (moi cum trung giu 1, dau IC nhat quan).
- `V5_importance.csv` / `V5v3_importance.csv`: 3 feature nhieu nam day importance (pipeline sach).

**Va co bang chung TIEN (forward), manh hon van ban da mat:** `docs/FS_RESULT.md` (pre-reg
`docs/PREREG_FS.md`) sang **16 ung vien feature moi** (5 nhom gia/volume/funding chua tung co trong
S1) tren `g1_replay` co CI khoi 72h, ket qua **0/16 vuot nguong**. Tuc du KHONG con ly do cat cu,
bo 7-9 feature hien tai da duoc kiem lai TU DAU va **khong feature suy tu gia/volume/funding luoi gio
nao them thong tin do duoc**. Bo 9 feature vi vay khong con phu thuoc van ban da mat.

## 7. Backup ngoai may

Kaggle dataset PRIVATE `chuyendinh/predwf-map-s1a2-bins` version 1 (11 file, 411,342,208 B, `ready`)
— job nay da tai ve + sha256 + xac nhan **byte-identical** deploy va rebuild (muc 0), roi xoa ban tai.
