# research/pipeline — PIPELINE SINH BINS SELECTOR S1 (predwf_map_s1a2)

Muc dich: S1 la nguon edge duy nhat da chung minh cua C2b (+7.35pp CAGR va maxDD -13.12 vs
-20.82 so voi G015 o CUNG thang exit C2b — xem `docs/AUDIT_APPLIED.md` muc 3.4). Truoc
2026-09-03 toan bo pipeline sinh S1 nam NGOAI git, chi ton tai o `/home/ubuntu/featv2/`
tren dia Oracle (dia 91% day). File trong thu muc nay la ban duoc git theo doi.

Bins that (394 MB) KHONG commit vao git. Chung duoc hash + sao luu ngoai may — xem
`BINS_MANIFEST.md`.

## 0. Bien quyet dinh

Cai lam nen S1 **khong phai** `SELECTOR_RANK_TOPK` hay `SELECTOR_ONLY_ENTRY` (hai key do
giong y nguyen o run `C2_g015` dung bins G015). Cai lam nen S1 la duong dan bins:

    WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2

Tu 2026-09-03 key nay duoc PIN trong `profiles/c2b.properties` va `profiles/c2b_min.properties`
va di qua cong `Cfg` nhu moi tham so giao dich khac (truoc day no o `INFRA_KEYS` = dat tuy y
qua env, va thieu no thi `WfoDataset` chi `LOG.warn` roi fallback Aerospike = ra so KHAC ma
khong bao loi). Nay thieu bins = **fail cung**.

## 1. So do luong du lieu

    Aerospike 226 (closes 1h)                     -.
    /home/ubuntu/claudedata/oi/oi_percoin_full.bin -+-> [1] feat_v2_build.py
    /home/ubuntu/java/fsrun/CLOSES_1H.bin         -'      -> featv2/feat_v2.parquet  (911 MB, 42 cot, hourly)

    /home/ubuntu/claudedata/wfo_gate_pred.csv (p15 theo tick 15m)  -.
    /home/ubuntu/claudedata/predwf_G015x26/predict_wf_*.bin (G015)  +-> [2] ledger.py build
    /home/ubuntu/label_15m/funding_label_2021..2024*.pb            -'      -> ledger/cand_dev.parquet (pool + g1lite)

    cand_dev.parquet + feat_v2.parquet  -> [3] s1_rank.py 2   -> ledger/pred_s1a2.parquet (ts,sym,score)

    pred_s1a2.parquet + predwf_G015x26  -> [4] build_map.py s1a2 -> predwf_map_s1a2/predict_wf_*.bin (10 file, 394 MB)

    predwf_map_s1a2  -> [5] ExportWfoDataset -> wfo_ds_*/{market,pred,funding}.bin + manifest.txt

    wfo_ds_*  -> [6] SimulatorMarketLevelTicker1MStopLoss (TRADING_PROFILE=profiles/c2b.properties)
                 -> devrun/<TAG>/storage/printDone.csv  (C2b: equity cuoi 60390)

## 2. Thu tu chay — lenh cu the

Tat ca chay tren **Oracle** (khong phai Kaggle). Cac script trong repo doc/ghi duong dan
TUYET DOI y nhu ban da sinh ra bins (khong doi duong dan de giu kha nang tai lap).

### Buoc 1 — feature hourly

    cd /home/ubuntu/featv2
    python3 /home/ubuntu/src/BinanceFuturesJava/research/pipeline/feat_v2_build.py > BUILD.out 2>&1

- Input: `CLOSES_1H.bin`, `oi_percoin_full.bin`, `symbol_map.csv`, Aerospike (ls_global)
- Output: `/home/ubuntu/featv2/feat_v2.parquet` (955,376,251 B), `feat_v2.meta.json`
- Thoi gian do duoc: **2 phut 54 giay** (`BUILD.out` 16:24:02 -> 16:26:56, 2026-09-02)
- Cuoi log phai co `ALL_V3_PASS`. FAIL bat ky check nao -> script `sys.exit` (khong train tren du lieu sai).
- Doan tuong ung cho VALIDATION: `feat_v2_build_val.py` (KHONG nam trong nhiem vu nay, khong commit).

### Buoc 2 — candidate ledger (pool + nhan)

    cd /home/ubuntu/featv2
    python3 /home/ubuntu/src/BinanceFuturesJava/research/pipeline/ledger.py build > LEDGER.out 2>&1

- Input: `wfo_gate_pred.csv` (p15), `predwf_G015x26/predict_wf_*.bin`, `label_15m/*.pb`, `symbol_map.csv`
- Output: `/home/ubuntu/ledger/cand_dev.parquet`
- Pham vi: `T0 = 2021-04-01`, `T1 = 2024-07-01` (GMT+7). Bat dau tu 2021-04 de fold 0 co du train.
- Pool = moi coin co NHAN tai tick 15m ma gate thi truong MO (`p15 >= 0.008`).
- Nhan chinh: `g1lite = if maxFav_72h >= 0.05 then maxFav_72h - min(0.5*maxFav_72h, 0.08) else retEnd_72h`
- Thoi gian do duoc: **~18 giay** (`S1v2.out` 22:44:33 -> 22:44:51, 2026-09-02)
- So do ban chay ra bins: 113,952 tick 15m, 8,686 tick gate mo (7.6%), 1,220,490 dong nhan,
  ledger 1,220,490 dong / 8,642 tick, 63.4% dong co `p_g015` (2021 khong co G015).
- Che do cham diem (khong bat buoc cho bins): `ledger.py score <ten>=<bins_dir> ...` -> `ledger/edge_scores.csv`

### Buoc 3 — S1 ranker (LambdaRank)

    cd /home/ubuntu/featv2
    python3 /home/ubuntu/src/BinanceFuturesJava/research/pipeline/s1_rank.py 2 > S1v2.out 2>&1

- Doi so `2` la HAU TO ten output: `run("s1a" + SUF)` -> ghi `pred_s1a2.parquet`.
  Chay khong doi so -> `pred_s1a.parquet` (ban ledger cu 2022+, DA BI A1 thay the).
- Input: `ledger/cand_dev.parquet` + `featv2/feat_v2.parquet` (join theo `ts_h = (ts//3600000)*3600000`, `sym`)
- Output: `/home/ubuntu/ledger/pred_s1a2.parquet` (cot `ts, sym, score`; score THAP = tot),
  `ledger/pool_rankic.csv` (chan doan rank-IC tung feature theo nam)
- Thoi gian do duoc: **4 phut 50 giay** (`S1v2.out` 22:44:51 -> 22:49:41, 2026-09-02)
- So do ban chay ra bins: 774,270 dong pred / 4,595 tick / 288 symbol;
  `ts` 1640971800000 .. 1719261900000 (2022-01-01 .. 2024-06-25 GMT+7)

#### Hyperparameter THAT cua s1_rank.py (doc tu code, dong 26-42)

| Muc | Gia tri | Vi tri trong code |
|---|---|---|
| Thu vien | `xgboost.XGBRanker` | dong 33 |
| objective | **`rank:ndcg`** | dong 33 |
| `lambdarank_pair_method` | `topk` | dong 33 |
| `lambdarank_num_pair_per_sample` | `8` | dong 33 |
| `n_estimators` | 300 | dong 33 |
| `max_depth` | 4 | dong 33 |
| `learning_rate` | 0.05 | dong 33 |
| `subsample` / `colsample_bytree` | 0.8 / 0.8 | dong 33 |
| `min_child_weight` | 50 | dong 33 |
| `tree_method` / `n_jobs` / `random_state` | `hist` / 4 / 42 | dong 33 |
| **label (relevance)** | `rel5` = `min(int(rank_pct(rel)*5), 4)` — **ngu phan vi TRONG TICK** cua `rel = g1lite - median_tick(g1lite)`. Tuc label la **cross-sectional**, khong phai gia tri tuyet doi. | dong 9-10 |
| **group (qid)** | `pd.factorize(tr.ts, sort=True)[0]` — **1 group = 1 tick 15m** | dong 34 |
| **so vong WFO** | **10 fold**, cutoff `20220101, 20220401, 20220701, 20221001, 20230101, 20230401, 20230701, 20231001, 20240101, 20240401`; OOS = 3 thang ke tiep tung cutoff | dong 24-25, 29 |
| **purge** | `PURGE = 72h` — train chi lay `ts < cutoff - 72h` (khop horizon nhan 72h) | dong 6, 30 |
| chan leak | `assert tr.ts.max() < c, "LEAK"` | dong 32 |
| dieu kien bo fold | `len(tr) < 5000` hoac `len(oos) == 0` -> skip | dong 31 |
| feature (9, danh sach `KEEP`) | `vol_7d, dd_7d, rk_dd_7d, hrs_since_high_7d, ret_3d, rk_ret_3d, ret_14d, ls_global, rk_oi_delta24h` | dong 7 |
| doi chung shuffle | fold 0/5/9: train lai voi label da tron TRONG TICK (`random_state=1`, `n_estimators=100`) | dong 36-38 |
| nguong PASS pre-reg | `edge5 g1lite OOS >= +6.0%` va duong ca 3 nam va `t >= 10` (G015 = +4.55%) | dong 45 |

### Buoc 4 — quantile-map ra bins (san pham cuoi)

    python3 /home/ubuntu/src/BinanceFuturesJava/research/pipeline/build_map.py s1a2 /home/ubuntu/predwf_map_s1a2

- Input: `ledger/pred_s1a2.parquet` + `claudedata/predwf_G015x26/predict_wf_*.bin`
- Output: `/home/ubuntu/predwf_map_s1a2/predict_wf_*.bin` — **10 file, 403,945,010 B**
- Chi lay fold 2022/2023/2024, BO `20240701` va `20241001` (chan VALIDATION/HOLDOUT).
- Co che: TRONG TUNG TICK, cac coin CO score moi nhan lai chinh tap gia tri `p` cua nhom do
  theo thu hang score; coin khong co score giu `p` cu. => **phan phoi P(win) theo tick GIU NGUYEN
  cua G015** nen gate chat/long y nhau; chi doi "coin nao nhan gia tri nao".
- Thoi gian do duoc: **~45 giay** (mtime bins 22:50:32 -> 22:50:37, 2026-09-02)
- Cuoi log phai in `MAP_OK` va dong `TOTAL rows ... changed ...`. Ti le `changed` cho s1a2 ~5%
  (neu ~41% thi la nhanh pool-day-du s1a4/s1b4 — nhanh nay DA THUA, xem AUDIT A4).
- LUU Y: log di ra **stdout** (khong stderr) vi cac script goi dung `... | tail -2`.

### Buoc 5 — export dataset WFO (Java)

    cd /home/ubuntu/java/devrun
    cp -f /home/ubuntu/src/BinanceFuturesJava/configs/sim_dev.properties config.properties
    env TRADING_PROFILE=/home/ubuntu/src/BinanceFuturesJava/profiles/c2b.properties \
        WFO_SET_PRED=ai_pred_market_gate_wfo WFO_SEL_HORIZON_IDX=0 WFO_CODE_SHA=<git rev-parse HEAD> \
        java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g \
        -cp /home/ubuntu/src/BinanceFuturesJava/target/binance-java-sdk-1.2.4.jar \
        com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset /home/ubuntu/wfo_ds_c2b

- **DOI 2026-09-03**: bins KHONG con cap qua env `WFO_FUNDING_PRED_DIR`. No doc tu profile qua
  `Cfg.get`. Dat CA HAI (env + profile) => `Cfg` fail-fast exit 2 ("hai nguon su that").
  Cac script cu trong `/home/ubuntu/java/` (`dev_min.sh`, `parity2/3.sh`, `verify_inert.sh`,
  `dev_br.sh`, `dev_k.sh`, `dev_rnd.sh`, `parity_profile.sh`) con `export WFO_FUNDING_PRED_DIR=...`
  -> phai BO dong export do va them `TRADING_PROFILE` vao buoc build. Ban chuan: `tools/run_c2b_dev.sh`.
- `WFO_SEL_HORIZON_IDX=0` = horizon 4h (bins slot `p0`). Default trong code la `1` — **phai dat ro**.
- Output: `wfo_ds_c2b/{market.bin,pred.bin,funding.bin,manifest.txt}`. `manifest.txt` ghi md5 tung
  file bins nguon + `binsSha256` + `fundingPredDir` + `codeGitSha` + `leakFreeFrom` (tinh TU DATA).
- Thoi gian do duoc: **31 giay** (`devrun/logs/build_min.out` 14:28:26 -> 14:28:57, 2026-09-03)
- Log phai co `*** HOLDOUT SEAL *** ... cat 312322 ban ghi >= 2026-01-01`.

### Buoc 6 — chay sim C2b

Xem `tools/run_c2b_dev.sh` (ban chuan, da dung lam cong nghiem thu byte-identity).

## 3. Script phu (khong sinh bins, nhung thuoc tang selector)

| File | Vai tro | Ket qua da ghi |
|---|---|---|
| `ledger3.py` | pool MO RONG (`p15 >= 0.002`) + chan doan gate theo bucket p15 -> `cand_dev3.parquet` | dung cho S1 v3/v4 va label_pick; nhanh pool-day-du DA THUA (AUDIT A4) |
| `path_labels.py` | label tu PATH gia theo gio: `nH_above_6/3`, `frac_above_6`, `g1_replay` (mo phong dung luat exit G1) -> `path_labels.parquet` | AUDIT A11 |
| `label_pick.py` | CHON label bang du lieu: Spearman(label, ROI that tu `printDone.csv`) + rank-corr trong tick vs `g1_replay` | `g1lite` thang (0.584 tren lenh that, 0.8133 rank-corr vs g1_replay) => nhan dang dung LA dung |
| `s1_eval.py` | S1 vs doi chung tam thuong (`vol_7d`, `-rk_dd_7d`, G015) tren 4 outcome | AUDIT A3 (control `vol_7d` thua: b:41876) |
| `admit_rate.py` | ty le VAO THAT (`p15 >= dyn_thr`) theo fold, rieng cho top-8 | AUDIT B5: admit top-8 DEV 0.51% / VAL 0.71% / 2025Q4 2.03% |

`gate_cfg.py` (cong thuc `dyn_thr`) KHONG o day — no da nam trong git tai
`research/analysis/gate_cfg.py`; `/home/ubuntu/featv2/gate_cfg.py` chi la shim `importlib` tro vao repo.

## 4. Moi truong

| | |
|---|---|
| May | Oracle (`/home/ubuntu`), 194 GB `/dev/sda1` |
| python | 3.10.12 |
| numpy | 2.2.6 |
| pandas | 2.3.3 |
| **xgboost** | **3.2.0** |
| scipy | 1.15.3 |
| pyarrow | 25.0.1 |
| scikit-learn | 1.7.2 |
| Java | `target/binance-java-sdk-1.2.4.jar`, `-Xmx14g`, `-Duser.timezone=Asia/Ho_Chi_Minh` |
| Kaggle | KHONG dung cho pipeline nay (chi H3 va GS wave chay Kaggle) |

`lambdarank_pair_method` / `lambdarank_num_pair_per_sample` chi ton tai tu xgboost 2.x.
Ha version xgboost duoi 2.0 => `XGBRanker` bao loi tham so la KHONG hop le.

## 5. Secret

Da quet `api_key|secret|passwd|password|token|Bearer|AKIA|-----BEGIN` tren ca 9 script:
**KHONG co secret nhung nao**. Khong file nao phai sua vi ly do bao mat.

Credential Kaggle nam ngoai repo tai `/home/ubuntu/.kaggle/kaggle.json` (mode 600) va da co
trong `.gitignore` cua he thong (khong nam trong worktree). Khong duoc echo file nay.

## 6. KHAC BIET giua ban trong repo va ban DA CHAY sinh ra bins

Chi duy nhat MOT loai sua: **`print` -> module `logging`** (luat repo: Python cam `print`).
6 file bi sua: `feat_v2_build.py`, `s1_rank.py`, `build_map.py`, `path_labels.py`,
`label_pick.py`, `s1_eval.py`. Cach sua thuan co hoc:

- them preamble `logging.basicConfig(..., format="%(message)s", stream=sys.stdout)` + helper `_p(*a)`
- doi `print(` -> `_p(`, bo `, flush=True`

`format="%(message)s"` + `stream=stdout` giu nguyen noi dung VA kenh output, nen hanh vi cac
script goi (`| tail -2`) khong doi. **Logic, tham so, thu tu tinh toan: 0 thay doi.**

3 file `ledger.py`, `ledger3.py`, `admit_rate.py` da dung `logging` san -> copy nguyen trang
(sha256 giong y ban tren dia).

sha256 ban DA CHAY vs ban trong repo: xem `BINS_MANIFEST.md` muc 4.

## 7. Canh bao tai lap — file trung gian DA BI GHI DE

`ledger/cand_dev.parquet` (dau vao buoc 3) da bi **build lai luc 2026-09-03 17:53**, sau khi
`pred_s1a2.parquet` duoc sinh (2026-09-02 22:49). Cung voi viec `ledger.py` doi cach ghi log
giua hai thoi diem, **khong dam bao chay lai buoc 2+3 hom nay ra dung tung bit
`pred_s1a2.parquet` cu**.

=> Artifact CO THAM QUYEN la `pred_s1a2.parquet` + `predwf_map_s1a2/` (da hash, da sao luu
Kaggle), khong phai file trung gian. Muon tai lap C2b thi LAY LAI hai artifact do, dung chay
lai buoc 2-3. Chay lai buoc 2-3 = mot thi nghiem MOI, phai pre-reg.
