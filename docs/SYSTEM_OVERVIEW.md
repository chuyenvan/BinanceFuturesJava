# SYSTEM_OVERVIEW — Chu trinh ca he thong end-to-end + danh gia S1 hien tai

Ngay 2026-09-17. Doc MO TA/AUDIT — KHONG chay sim, KHONG sua `.java`, KHONG them flag.
Moi muc kem dan chieu (file + dong, hoac ten doc + muc). Cho nao repo khong co thong tin thi
ghi ro "khong tim thay trong repo".

Nguon chinh: `docs/WFO_DATAFLOW.md`, `docs/AGENT_RUNBOOK.md`, `docs/C3_BASELINE.md`,
`docs/X1_EXTEND.md`, `docs/S1_PROVENANCE.md`, `docs/L1_SHADOW_C3.md`, `docs/L5_S1_WARMUP_242.md`,
`docs/RISK_APPETITE.md`, `docs/QUEUE.md`.

---

# PHAN 1 — CHU TRINH CA HE THONG (end-to-end)

Chuoi BAT BUOC (WFO_DATAFLOW.md §0): ticker goc -> market object -> export feature -> TRAIN ->
gen PRED -> WFO. WFO chay bang FILE BIN offline (WFO_DATA_DIR), KHONG scan Aerospike luc chay.

## 1. Du lieu

| file (dataset WFO) | noi dung | dan chieu |
|---|---|---|
| `market.bin` | 55MB / 2,774,140 rec; `[count][ts:long][3 float]` | WFO_DATAFLOW.md §5 |
| `pred.bin` | 28MB / 1,795,680 rec (gate); `[count][ts:long][predReturn15M][predRisk4H]` | WFO_DATAFLOW.md §5 |
| `funding.bin` | 30MB / 175,226 moc, 3.48M rec (selector 12h); `[count][ts:long][len:int][len x long]` | WFO_DATAFLOW.md §5 |
| `manifest.txt` | md5 3 file + provenance; `load()` verify md5 fail-fast | WFO_DATAFLOW.md §5 |

- Nguon goc Aerospike ns=`test` (Oracle 127.0.0.1:3222): `kline_1m_opt`, `market_data_object`,
  `funding_data`, 5 set OI, `symbol_mapper`, `wfo_jobs` (WFO_DATAFLOW.md §1).
- Dataset duoc build bang `ExportWfoDataset` (Java), doc funding qua
  `WfoDataset.buildFundingFromWfFiles()` tu cac file bin selector, BO Aerospike (WFO_DATAFLOW.md §4).
- Lenh export (WFO_DATAFLOW.md §4):
  `WFO_FUNDING_PRED_DIR=/home/ubuntu/selector_pred_out WFO_SEL_HORIZON_IDX=1 ... ExportWfoDataset /home/ubuntu/claudedata/wfo_dataset`.
- Dataset X1 (48 thang) mo rong: `marketCount=2,554,812 predCount=2,500,260 fundingCount=2,043,446`
  (X1_EXTEND.md §2).

## 2. Feature / model

- **Feature extractor**: `research/pipeline/feat_v2_build.py` (sinh `feat_v2.parquet`); 9 feature
  `KEEP` cua S1 nam o `research/pipeline/s1_rank.py:22`:
  `vol_7d, dd_7d, rk_dd_7d, hrs_since_high_7d, ret_3d, rk_ret_3d, ret_14d, ls_global, rk_oi_delta24h`.
- **Hai model/duong pred** (WFO_DATAFLOW.md §2):
  - **GATE**: `ml/gate/train_gate_fold.py` — XGBRegressor return, 33 feature V3FULL, label
    `oldbasket`, ONNX `Model_Regressor_Return15M.onnx` per-fold. Output
    `/home/ubuntu/claudedata/wfo_gate_pred.csv` (1,795,680 dong; `predReturn15M`, `predRisk4H`).
  - **SELECTOR**: train tren Kaggle (`ml/funding_selector/kaggle_kernel_train_selector.py`),
    pred `ml/training/gen_funding_wf_predictions.py` (walk-forward, purge 72h). Output 16 file
    `predict_wf_*.bin`.
- **`WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2` la gi**: bins selector (26 B/rec
  `[ts:int64][symId:int16][p4h,p12h,p24h,p72h:float32]`) — ket qua cua S1 rank ap len phan phoi
  P(win) cua G015x26 (xem Phan 2). Sinh bang `s1_rank.py` roi `build_map.py`
  (S1_PROVENANCE.md §1, §3). `predwf_map_s1a2_x1` la ban 16 fold cua X1 (X1_EXTEND.md §2).
- `WFO_SEL_HORIZON_IDX`: 0=4h, 1=12h, 2=24h, 3=72h; mac dinh 1=12h (WFO_DATAFLOW.md §4).

## 3. WFO (walk-forward)

- **Khung**: `WFORunner.java`, `ai_ml/wfo/framework/WfoCoordinator`, `WfoWorker`, va task
  `tasks/StrategyWfoTask.java`.
- **Cua so**: train 12 thang + OOS 3 thang, truot 3 thang, 17 cua so 20210101..20260601
  (WFO_DATAFLOW.md §6); `StrategyWfoTask.java:24,48` (`OOS_MONTHS=3`, `TRAIN_MONTHS=12`).
- **So fold/cua so**: 17 (`strategy_window`); N_samples = 30/cua so (WFO_DATAFLOW.md §6).
- **Chon tham so**: random-search N mau genome tren TRAIN -> best theo fitness V4.1 -> do OOS -> WFE
  (`StrategyWfoTask.java:24`). Genome 17 gene (`StrategyWfoTask.java:57`).
  `SensitivityTool.java` (HPO OAT) san loc gene phang truoc HPO (`SensitivityTool.java:23-38`).
- **Nguong pre-register** (`StrategyWfoTask.java:53-55`): WFE_median >= 0.5, %OOS-duong >= 70%,
  maxDD-OOS xau nhat <= 50%. Verdict do Uni quyet, agent khong tu ket luan.

## 4. Selector

- `symbolPred` -> xep hang -> lay top-K. Profile `c3_min.properties`: `SELECTOR_RANK_TOPK=8`,
  `SELECTOR_ONLY_ENTRY=1` (c3_min.properties:9-10).
- Sim doc bins qua `WfoDataset` -> `extractPredict2Symbol`
  (`SimulatorMarketLevelTicker1MStopLoss.java:324,822`) tao `TreeMap<Float, Short>` sort TANG
  (score thap = P(win) cao = tot), lay K phan tu dau.
- Nhanh market-signal (Best-N) dung `MarketBigChangeDetector.getTopSymbolArray`
  (`MarketBigChangeDetector.java:123`).
- Duong live: `tradecore/selector/S1RankerLive.java` (tinh 9 feature + score real-time),
  `LiveBuildMap.java` (gan P(win) theo rank), `EntryPoolGate.java`, `SelectorTier1Source.java`.
  Live KHONG doc `WFO_FUNDING_PRED_DIR` (xem Phan 2).

## 5. Entry / gate

- **Mot class, mot knob**: `tradecore/EntryGate.java`. Cong thuc
  (`EntryGate.java:16,44-48`):
  `thr(symbolPred) = thrBase * max(DYN_MIN, symbolPred/SCORE_BASE * DYN_MULT) * gateScale`;
  `DYN_MIN=0.26787f`, `DYN_MULT=1.28760f`; `gateScale = SIM_GATE_DYN_SCALE` (mac dinh 1.0).
  `PASS <=> !(predReturn15M < thr)` (`EntryGate.java:96-97`).
- `thrBase = SIM_MIN_MOMENTUM_15M` = 0.008 (c3_min.properties:32; EntryGate.java:87-88).
- Call-site: `AIRejectFilter.entryGate` — sim va live DUNG MOT cho (AGENT_RUNBOOK.md §10b).
- Nhanh **BIG_DOWN**: bypass gate AI, khong mang `symbolPred` (C3_BASELINE.md §2; L1_SHADOW_C3.md
  muc 2 cot `SELECTOR_ONLY_ENTRY`). `SELECTOR_ONLY_ENTRY=1` -> chi leg selector (tat BIG_DOWN o C3).
- Gate tang 2 (`checkSignalDynamic`) BI BO QUA khi `SELECTOR_RANK_TOPK>0` (L1_SHADOW_C3.md muc 2).

## 6. Exit (TS / ratchet / time-stop)

- **Arm**: `SIM_RATE_PROFIT_STOP_MARKET=0.07` (c3_min.properties:35).
- **Trailing giveback**: `exit = peak - min(peak*0.5, cap)`; `SIM_TS_GIVEBACK=1`,
  `TS_GIVEBACK_RATIO=0.5` (c3_min.properties:36,38; C3_BASELINE.md §4).
  Cap STRONG 0.08 / WEAK 0.03 theo ban le `SIM_TS_PNOPUMP_WEAK_THR=0.29` (AGENT_RUNBOOK.md muc 3;
  L1_SHADOW_C3.md muc 2).
- **Time-stop**: `SIM_LOSER_TIME_STOP_HOURS=168` (c3_min.properties:37); `STOP_LOSS_DONE` = time-stop,
  KHONG phai SL (AGENT_RUNBOOK.md muc 3).
- **Pre-arm hard SL**: `SIM_PRE_ARM_SL` (mac dinh 0 = TAT; `tradecore/PreArmSlUtils.java`) — khong
  dat trong baseline (AGENT_RUNBOOK.md muc 4).

## 7. DCA

- `tradecore/DcaProcessor.java` + `tradecore/DcaUtils.java`.
- `DcaUtils.gridLegWeightRatio(legCount)` (`DcaUtils.java:47-63`): voi `SIM_FIX_B2=true` tra
  `w * DCA_GRID_SCALE` (bo lan chia thu hai). `DCA_GRID_WEIGHTS=1,0,0,0` + `DCA_GRID_SCALE=1.5`
  (c3_min.properties; C3_BASELINE.md §2).
- `DCA_GRID_SCALE=19.5` (=1.5x13) chi dung cho `C3_FULL` (weights `1,1,3,8`); `C3` DCA tat
  (`1,0,0,0`) (C3_BASELINE.md §5).
- DCA leg 2+ duong o 2022 va 2025, KHONG phai "an FTX mot lan" (X1_EXTEND.md §6).

## 8. Rui ro / guard

| guard | gia tri | dan chieu |
|---|---|---|
| `F_BASE` | 0.03 (% equity/lenh goc) | Configs.java:155 |
| `U_MAX` | 0.60 (tran margin/equity) | Configs.java:156 |
| `CONC_CAP_PERCOIN_PCT` | 0.15 (tran 1 coin) | Configs.java:540; RISK_APPETITE.md §5 |
| `CONC_CAP_AGG_DCA_PCT` | 0.45 (tran aggregate) | Configs.java:519-520 |
| `CONC_CAP_BD_PER_HOUR` | 75 (toc do BIG_DOWN) | Configs.java:525-526 |
| `TIER_FLAT` | 1 (= tat tier sizing) | c3_min.properties; CoinRankManager.java:117 |
| Sizing | `margin = equity x F_BASE x throttle x DCA_GRID_SCALE x w[i]/total` | AGENT_RUNBOOK.md muc 3 |

- Nguong RUI RO (khau vi) 2026-09-16/17 (`docs/RISK_APPETITE.md`): `maxDD <= 30%/nam`,
  `UW <= 200 ngay`, `quy xau nhat >= -15%`, `tap trung 1 coin <= 15% equity`. NGUONG BANG CHUNG
  (`>= 2 rate ngoai CI`, bootstrap block-72h x1.21) GIU NGUYEN.

## 9. Do luong & cong

- `storage/printDone.csv` (bang lenh + md5 parity); `logs/sim.out` (log chay) (AGENT_RUNBOOK.md muc 2).
- Score: `research/analysis/qret_ladder.py`, `research/analysis/x1_rates.py`, `/home/ubuntu/java/fsrun/qret.py`
  (AGENT_RUNBOOK.md muc 2 "Cham diem").
- Bootstrap block-72h, 2000 rep, CI x1.21, seed 20260905, luoi khoi chung (C3_BASELINE.md §7).
- Parity gate: md5 `printDone.csv` phai trung neo (`C3` `38be0cb3...`, `X1_C3` `d39da294...`) —
  L7 gate parity `2478e90d...` (AGENT_RUNBOOK.md §10b; X1_EXTEND.md §11).
- Pre-register TRUOC khi chay (`docs/PREREG_<TEN>.md`) — AGENT_RUNBOOK.md muc 0.2.
- Holdout 2026: `HoldoutSeal.SEAL_MS = 2026-01-01` (`HoldoutSeal.java:20`); mo bang
  `HOLDOUT_UNSEAL` chi khi user duyet truc tiep (AGENT_RUNBOOK.md muc 0.1).

## 10. Chay o dau

- **Oracle box** (1 slot JVM — khong chay 2 sim cung luc), `TICKER_SOURCE=file` (neo 60395),
  `SIM_END_DATE` (X1: 20251231). Kaggle CPU == Oracle+file byte-for-byte (AGENT_RUNBOOK.md muc 2).
- Lenh build dataset + chay sim (AGENT_RUNBOOK.md muc 2); X1: `research/pipeline/x1/run_x1.sh`
  + `run_x1_sim.sh` (X1_EXTEND.md §11).

---

# PHAN 2 — DANH GIA S1 HIEN TAI

## A. S1 la gi (chinh xac)

- **S1 = selector/ranker**, KHONG phai value model. Train bang
  `research/pipeline/s1_rank.py` (ban 48 thang: `research/pipeline/x1/x1_s1_rank.py`).
- **Model**: `XGBRanker(objective="rank:ndcg", n_estimators=300, max_depth=4, learning_rate=0.05,
  subsample=0.8, colsample_bytree=0.8, min_child_weight=50, n_jobs=4, tree_method="hist",
  random_state=42, lambdarank_pair_method="topk", lambdarank_num_pair_per_sample=8)`
  (`s1_rank.py:48`; S1_PROVENANCE.md §4).
- **Du doan gi**: THU TU coin trong tung tick 15m (rank), KHONG du doan gia tri.
  Label `rel5 = min(int(rank_pct(rel)*5),4)`, `rel = g1lite - median_tick(g1lite)` (S1_PROVENANCE.md §4;
  `s1_rank.py:24-25`).
- **Feature**: 9 feature `KEEP` (`s1_rank.py:22`; xem Phan 1 muc 2).
- **Sinh artifact o dau**: `s1_rank.py` ghi `ledger/pred_s1a2.parquet` (cot `ts,sym,score`), roi
  `build_map.py` ghi bins `/home/ubuntu/predwf_map_s1a2/` (S1_PROVENANCE.md §3). Ban 16 fold:
  `pred_s1a2x1.parquet` + `/home/ubuntu/predwf_map_s1a2_x1/` (X1_EXTEND.md §11).
- **Ai goi no**:
  - **Duong sim**: `WfoDataset.buildFundingFromWfFiles()` doc `WFO_FUNDING_PRED_DIR` (bins) de
    xep hang coin (WFO_DATAFLOW.md §4; `WfoDataset.java:74,248`).
  - **Duong live**: `S1RankerLive` tinh 9 feature + score real-time tu `kline_1m_opt` 242 + OI,
    `LiveBuildMap` gan P(win) theo rank (L5_S1_WARMUP_242.md §2; `tradecore/selector/`).
    Live KHONG doc `WFO_FUNDING_PRED_DIR` (AGENT_RUNBOOK.md muc 0.8a; L1_SHADOW_C3.md muc 0.1).

## B. Trang thai artifact `predwf_map_s1a2`

- **La gi**: bins 26 B/rec `[ts][symId][p4h,p12h,p24h,p72h]`, `p0`=p4h (`WFO_SEL_HORIZON_IDX=0`),
  `score = 1 - P(win)` (dao dau). Tai lap BYTE-IDENTICAL 3 nguon (r1/r2/deploy/backup Kaggle)
  (S1_PROVENANCE.md §0, §1).
- **Causal theo tung fold hay mot lan toan cua so**: **CAUSAL THEO TUNG FOLD WFO**.
  `s1_rank.py` chay WFO 10 fold cutoff `20220101..20240401`, OOS 3 thang, purge 72h,
  `assert tr.ts.max() < c` (S1_PROVENANCE.md §4). Moi fold train tren `ts < cutoff - 72h` roi
  predict OOS — khong co bien nao train tren toan cua so.
- **Gioi han can biet**: `predwf_map_s1a2` khong chi la S1 — no la **S1 rank (causal per fold)
  ap len multiset P(win) cua G015x26** bang `build_map.py` (`build_map.py:1,39-41`; `changed` 4.9%).
  G015x26 la bo bins **KHONG tai lap duoc** (X1_EXTEND.md §12; AGENT_RUNBOOK.md muc 5).

## C. Chat luong da do cua S1

- **edge5** (top-5 vs pool, outcome `g1lite`) OOS: toan 16 fold **+15.41%**, `t = 72.3`; theo nam
  2022 +6.25% / 2023 +8.89% / 2024 +8.52% / **2025 +19.34%** (X1_EXTEND.md §10.5).
- **Spearman score S1 vs deploy = 1.000000** (774,270 dong) (S1_PROVENANCE.md §0).
- **Khong co IC / rank-IC rieng cho S1** trong repo ngoai edge5 — **chua co do luong IC/rank-IC
  cua S1** (chua tim thay so lieu nao; edge5 la metric duy nhat do chat luong thu tu S1).
- **Khong co PnL attribution rieng cua leg qua selector** (S1 vs baseline) o dang bang so sach —
  uu the C3 so x26-order da do o `G5_VALUE_LABELS` (4/5 rate), nhung do la so C3 vs order-x26,
  khong phai mot "S1 quality report" doc lap (AGENT_RUNBOOK.md muc 4).
- Selector ladder **CHUA THIET LAP** (78% uu the nam 2022; rebase 2023 thi C2b THUA) —
  `docs/SELECTOR_LADDER_Q.md`; AGENT_RUNBOOK.md muc 4.

## D. Van de da biet — `AGENT_RUNBOOK.md` muc 0.8 (shadow C3 tren Oracle)

Tom tat chinh xac (dan chieu AGENT_RUNBOOK.md muc 0.8, va `L1_SHADOW_C3.md` muc 0):

1. **(a) Live khong goi duoc la C3**: duong live tinh `symbolPred` bang
   `Funding_Classifier_Final.onnx` (45 feature) va **khong doc `WFO_FUNDING_PRED_DIR` o bat ky dong
   nao** — bins `predwf_map_s1a2` la artifact OFFLINE. Model S1 **khong co file** (`s1_rank.py`
   khong `save_model`). "Chay shadow bang selector live roi dan nhan C3 = so lieu VO GIA TRI."
2. **(b) Shadow 242 hien khong sinh tin hieu**: 66 vi the cu giu `marginRunning` => `u=0.81 >=
   U_MAX 0.60` => `managerBudget` null => 0 dong `would-BUY` tu 27/08. Shadow phai chay tren
   **Oracle** voi **Redis RIENG** (tro vao Redis 242 se `blpop` cuop lenh bot live).
3. **(c) Moi tuan shadow = mot tuan holdout bi tieu**: doi chung chi duoc `HOLDOUT_UNSEAL` DUNG
   doan da troi qua, co user duyet truc tiep, roi seal lai.

Chi tiet cau thanh phan (L1_SHADOW_C3.md muc 3): S1 can 9 feature live (3a — chua co bo tinh gia
theo gio real-time; `CLOSES_1H.bin` = kline 1h, KHONG phai ticker 1m gop), model S1 chua luu file
(3b), live khong doc bins (0.1), budget=0 khi khong co API key (3e), Redis rieng (3f), live thieu
time-stop 168h (0.5), live ratchet co dead-zone 26.1% (0.4).

## E. Danh gia trung thuc

**S1 hien tai la CHUA KIEM CHUNG (unverified) o tang live/forward.** Cu the:

- **Da biet / da chung minh trong repo**:
  - S1 xep hang tot OOS theo edge5 (+15.41%, t=72.3) — X1_EXTEND.md §10.5.
  - S1 tai lap byte-identical (bins) — S1_PROVENANCE.md §0.
  - Uu the C3 (dung S1 order) so x26-order da do — AGENT_RUNBOOK.md muc 4 (G5).
- **Chua biet / chua chung minh**:
  - Khong co model file S1 de predict live (`s1_rank.py` khong `save_model`) — L1_SHADOW_C3.md muc 3b.
  - Khong co bo tinh 9 feature S1 real-time cho toan universe — L1_SHADOW_C3.md muc 3a.
  - Duong FEATURE 45 live vs Tool1 offline **CHUA DO DUOC** — L1_SHADOW_C3.md muc 3d; L5 §5.1 muc B.
  - Khong co IC/rank-IC rieng cua S1 (chi edge5) — muc C.
  - Khong co so sanh shadow<->sim cho leg S1 (chua co du lieu) — L1_SHADOW_C3.md muc 7.

**Mau thuan sim vs live (neu RO, khong tu sua)**:
1. **Selector la hai HE khac nhau** (L1_SHADOW_C3.md muc 2.2.1): sim = S1 order + G015x26 value;
   live = mot model 45-feature duy nhat (`Funding_Classifier_Final.onnx`, ho maxFav).
2. **K=8 (sim) vs K=5 (live)** (`SELECTOR_RANK_TOPK`) — AGENT_RUNBOOK.md muc 5; L1_SHADOW_C3.md muc 2.
3. **Live thieu time-stop 168h** — L1_SHADOW_C3.md muc 2.2.2.
4. **Live ratchet co dead-zone 26.1%, sim khong** — L1_SHADOW_C3.md muc 2.2.3.
5. **`CAPITAL_START` 14000 (242) vs 35000 (sim)** — L1_SHADOW_C3.md muc 9.5.

## F. Rui ro / uong

1. 🔴 **Leak artifact**: `predwf_G015x26` khong tai lap duoc (single point of failure) — X1_EXTEND.md §12.
2. 🔴 **Live/sim divergence** o selector (hai he khac nhau) + exit (time-stop, dead-zone) — L1_SHADOW_C3.md muc 2.2.
3. 🔴 **S1 khong co model file** — neu mat du lieu dau vao thi khong predict lai duoc live
   (L1_SHADOW_C3.md muc 9.1).
4. ⚠️ **Model ngoai mep train 11 thang**: S1 va net015 deu cutoff 2025-10; chay forward 2026-09 la
   du bao ngoai mep (L1_SHADOW_C3.md muc 3b; L5 §6 muc D).
5. ⚠️ **purge 72h < holding 168h** => train/test overlap tren equity path (AGENT_RUNBOOK.md muc 5).
6. ⚠️ `Constants.diedSymbol` (hardcode danh sach delist) va `f23 fundingPersistence` (proxy thoi
   gian) la future-info/proxy — AGENT_RUNBOOK.md muc 5.
7. ⚠️ **Stale bins / dai live lech DEV**: dai `[MAP]` live 242 (p50 0.59-0.62, p90 0.84-0.87) cao
   hon dai DEV (p50 max 0.6093, p90 max 0.7221) — L5_S1_WARMUP_242.md §5.1; chua ket luan (regime
   hay hieu chuan).
8. ⚠️ `config.properties` 242 thieu `AEROSPIKE_NAMESPACE_242` (code co mac dinh, khong gap) —
   L5 §6 muc G.
