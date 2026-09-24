# L1_SHADOW_C3 — dung C3 chay forward (shadow) tren Oracle: hien trang, khac biet, feasibility

Ngay 2026-09-06. READ-ONLY tren 242. Khong dat lenh Binance. Khong push.
Doc truoc: `docs/runbooks/AGENT_RUNBOOK.md`, `docs/experiment/C3_BASELINE.md`, `docs/plan/H1_HOLDOUT_PREP.md`,
`docs/runbooks/runbook_live_242_2026-08-19.md`, `runbook_shadow_off_trade_2026-08-23.md`.

---

## 0. RUI RO TRUOC — 6 dieu, doc het roi hay doc tiep

1. 🔴 **KHONG dung duoc C3 lam shadow bay gio.** Cai lam nen C3 la **bins
   `predwf_map_s1a2`** — mot file OFFLINE `(ts, symId) -> P(win)`. Duong LIVE
   (`DetectEntrySignal2TradeNormal`) **khong doc `WFO_FUNDING_PRED_DIR` o bat ky dong nao**
   (chi `WfoDataset`/`ExportWfoDataset` + preflight doc). Live tu tinh `symbolPred` bang
   `Funding_Classifier_Final.onnx` (45 feature). => Cam C3 vao live **khong phai viec cau hinh**,
   phai viet moi mot bo sinh score S1 chay real-time. Chi tiet muc 3.
2. 🔴 **Model S1 KHONG CO FILE.** `research/pipeline/s1_rank.py` train roi `predict` ngay trong
   vong lap, ghi ra `pred_s1a2.parquet`, **khong co `save_model`**. Khong co artifact nao de
   predict live. Phai train lai (re, CPU) NHUNG con phai co 9 feature live (chua co).
3. 🔴 **Live 242 dang SHADOW nhung shadow do DA CHET ve mat tin hieu.** 10 ngay gan nhat:
   **0 dong `would-BUY`**, 1,346 dong `Not trade because over capital or budget not enough`.
   Nguyen nhan: 66 vi the THAT con lai tu thoi trade that van chiem `marginRunning` =>
   `managerBudget` tra null. Log shadow hien tai **khong dung lam doi chung duoc**.
   Dong `would-BUY` cuoi cung: **27/08/2026 22:45**.
4. 🔴 **Duong exit LIVE va duong exit SIM KHAC NHAU ve co che, khong chi ve tham so.**
   Live ratchet SL co **dead-zone `LIVE_RATCHET_DEADZONE_MULT = 5.21847`**
   (`BinanceOrderTradingManager:425,469`): arm SL lan dau o `+RATE_PROFIT_STOP_MARKET` (live 5%),
   nhung **doi SL** chi khi lai vuot `5.21847 x 0.05 = 26.1%`. Sim da **go** dead-zone nay
   (FROZEN v1 2026-08-24, `DumpConfig:78` "dead-zone x TS_PROFIT_MULTIPLIER da go") — sim ratchet
   LIEN TUC. Day la khac biet co che lon nhat, va no **khong nam trong bat ky bang tham so nao**.
5. 🔴 **`SIM_LOSER_TIME_STOP_HOURS=168` — kenh mat tien lon nhat cua C3 — KHONG TON TAI tren
   duong live.** Code time-stop chi o `SimulatorMarketLevelTicker1MStopLoss:672`. Live khong co.
   Shadow chay tren duong live se KHONG tai lap duoc `STOP_LOSS_DONE` cua C3.
6. ⚠️ **Dia Oracle con 6.9G/194G (97%)**. Duoi nguong 8G ma `run_x1_sim.sh` tu chan. Khong duoc
   build them dataset moi cho toi khi don dia.

---

## 1. HIEN TRANG LIVE 242 — **SHADOW** (khong phai REAL)

| do | gia tri |
|---|---|
| `conf/env.sh:35` | `export SHADOW_NO_PUSH=true` |
| `/proc/29022/environ` | `SHADOW_NO_PUSH=true` ✅ (da ap that, khong phai chi trong file) |
| PID trading | **29022**, start **06/09 11:36** (`run/...BinanceOrderTradingManager.pid`) |
| PID ingestor | 15494 (`BinanceDataIngestor`, tu 07:52) |
| env giao dich thuc te | `SELECTOR_RANK_TOPK=5`, `SIM_MIN_MOMENTUM_15M=0.008`, `SIM_RATE_PROFIT_STOP_MARKET=0.05`, `SIM_TS_PROFIT_MULTIPLIER=3.0`, `TS_PRED_GAP=1` — **HET**, khong co key nao khac |
| jar 242 | `sha256 d0825e8acc5ce022...`, mtime **02/09 11:25**, 99,686,080 B |
| jar Oracle `$R/target` | `sha256 1fb1b0ea2938a93e...` (HEAD `39c571d`), mtime 06/09 00:52 | 
| => | **HAI JAR KHAC NHAU.** 242 chay ban 02/09, TRUOC ca 3 fix B1/B2/B3 (05/09) va truoc X1/X2/X3 |
| model gate | `../storage/ai_ml_data/ai_models_reg_v3/Model_Regressor_Return15M.onnx` (144,774 B, **17/08 16:27**) |
| model selector | `../storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx` (788,710 B, 17/08 08:19, sha256 `dce8b6a692f672c2...`) |
| RAM 242 | total 7G, **free 0G, available 2G**, swap 7G |
| dia 242 | 92G, con 17G |
| vi the dang mo | **66** (`Update all position:66` moi phut) |
| `[SHADOW]` trong full.log | 1,030 dong; **dau 19/08 22:30**, **cuoi 27/08 22:45** |

### 1.1 Ket luan: REAL hay SHADOW

**SHADOW.** Khong con dat lenh entry that. Nhung phai noi ro hai dieu:

- **Vi the dang mo van dong THAT**: guard `SHADOW_NO_PUSH` chi nam o path entry moi
  (`processOrderNewMarketNew:169`). Path SL/TP/reduce-only KHONG bi chan.
  `Create Stop Loss Algo` xuat hien 579 lan trong full.log. **Tien that van dang chay ra/vao
  qua duong dong vi the.**
- **Shadow nay khong sinh tin hieu.** 30,000 dong log gan nhat: `would-BUY` = **0**,
  `Create order market` = **0**, `Not trade because over capital or budget not enough` = **1,346**.
  Gate AI van PASS (929 dong `AI PASS`) roi chet o `managerBudget`. Vi:
  `u = marginRunning / balanceBasic`; `balanceBasic = CAPITAL_START = 14000` (242
  `config.properties`), `marginRunning` do 66 vi the cu ~11,343 => `u = 0.81 >= U_MAX 0.60`
  => `managerBudget` tra **null** => moi entry bi chan.
  **=> Muon shadow tren 242 co ich lai thi phai dong het 66 vi the cu (quyet dinh cua user,
  la thao tac tien that) — hoac chay shadow o cho khac.**

---

## 2. BANG KHAC BIET — live 242 (dang chay) vs C3 vs C3_FULL

Cot cuoi tra loi cau quan trong nhat: **duong LIVE co doc key do khong**. "sim-only" = code
chi ton tai trong `SimulatorMarketLevelTicker1MStopLoss`/`BudgetManagerSimple`, dat key tren
live **khong co tac dung gi**.

| tham so | live 242 | C3 (`c3_min`) | C3_FULL | duong LIVE co doc? |
|---|---|---|---|---|
| **selector — model** | `Funding_Classifier_Final.onnx` 45-feat, tinh real-time, `preds[0]` = pNoPump | bins `predwf_map_s1a2` = **multiset P(win) cua G015x26 gan lai theo thu hang S1** | y het C3 | ❌ **KHAC HAN CO CHE.** `WFO_FUNDING_PRED_DIR` chi doc o `WfoDataset:74` + preflight; `DetectEntrySignal2TradeNormal` khong doc |
| **selector — K** | `SELECTOR_RANK_TOPK=5` | **8** | 8 | ✅ `Configs:341` -> `DetectEntry...:322,327` |
| **`SELECTOR_ONLY_ENTRY`** | **khong dat => false** (con leg market-signal + BIG_DOWN) | **1** (chi leg selector) | **0** | ✅ `Configs:346`; live dang o che do "FULL" tren truc nay |
| **gate value (`symbolPred`)** | pNoPump live, do duoc trong log **0.054-0.116** | P(win) G015x26, X3 do duoc **~0.35** trong 1 tick | nt | ✅ nhung **hieu chuan KHAC HAN** (muc 3c) |
| **`SIM_MIN_MOMENTUM_15M`** | **0.008** | **0.008** | 0.008 | ✅ `Configs:490` -> `MIN_MOMENTUM_15M` -> `AIRejectFilter.checkSignal` |
| **gate tang 2 (`checkSignalDynamic`)** | **BI BO QUA** (TOPK=5>0) | BI BO QUA (TOPK=8>0) | nt | ✅ `DetectEntry...:512` — giong nhau |
| **arm (`SIM_RATE_PROFIT_STOP_MARKET`)** | **0.05** (env de len `config.properties` 0.01) | **0.07** | 0.07 | ✅ `Configs:506` |
| **ratchet dead-zone** | 🔴 **`LIVE_RATCHET_DEADZONE_MULT=5.21847`** => doi SL chi khi lai > **26.1%** | **KHONG CO** (da go, ratchet lien tuc) | nt | ✅ hardcode `BinanceOrderTradingManager:425,469` — **khac biet CO CHE, khong cau hinh duoc** |
| **`TS_PRED_GAP=1`** | dat trong env | khong dat | — | ⚠️ **KHONG co reader trong ma nguon HEAD.** Xem muc 2.1 |
| **`SIM_TS_PROFIT_MULTIPLIER=3.0`** | dat trong env | khong dat | — | ⚠️ **KHONG co reader** (`BinanceOrderTradingManager:419`: "field do da xoa"). Xem muc 2.1 |
| **`SIM_TS_GIVEBACK`** | khong dat (null => bo qua guard) | **1** | 1 | ✅ `Configs:562` guard; ca hai deu di duong giveback |
| **`TS_GIVEBACK_RATIO`** | khong dat => default **0.5** | **0.5** | 0.5 | ✅ `Configs:173` |
| **cap trailing STRONG/WEAK** | `TS_MAX_GAP=0.08` / `TS_MAX_GAP_WEAK=0.03` (default) | y het | y het | ✅ |
| **ban le 0.29 (`TS_PNOPUMP_WEAK_THR`)** | default **0.29** — **CO CHAY** | 0.29 | 0.29 | ✅ **live CO dung**: `BinanceOrderTradingManager.tsGap():427-434` lay `LATEST_SEL_PNOPUMP` (pNoPump live) -> `calRateLossDynamicBuyPNoPump`. Sim: `OrderTargetInfoTest.trailRate():365` |
| **time-stop 168h** | 🔴 **KHONG CO** (`LOSER_TIME_STOP_HOURS` default 0, va code chi o sim) | **168** | 168 | ❌ **sim-only** (`Simulator...:672`) |
| **pre-arm hard SL** | khong co | `SIM_PRE_ARM_SL` default 0 = TAT | TAT | ❌ sim-only (`PreArmSlUtils`) |
| **sizing — duong nao** | `TradeUtils.managerBudget(budget, marginRunning, balanceBasic, level)` voi **`balanceBasic = Configs.capitalStart() = 14000`** (242 `config.properties`), **KHONG compound** | cung ham `managerBudget` nhung `balanceBasic` = `equityNow()` (B3) | nt | ✅ CUNG HAM. Khac o **doi so thu 3**: live truyen `BudgetManager.balanceBasic` (hang so tu config), sim truyen equity dong |
| | ⚠️ tham so thu nhat (`budget = BUDGET_PER_ORDER = 14000/50 = 280`) **BI HAM BO QUA** — `TradeUtils:83` chi dung `balanceBasic * F_BASE * throttle / ladder` | | | so `BASE_BUDGET=700` trong `c3_min` la **CHU THICH lich su**, khong phai duong tinh |
| **`F_BASE` / `U_MAX`** | default 0.03 / 0.60 | 0.03 / 0.60 | nt | ✅ |
| **`DCA_GRID_WEIGHTS` (mau so `ladder`)** | khong dat => **`1,1,3,8`, total = 13** | **`1,0,0,0`, total = 1** | **`1,1,3,8`, total 13** | ✅ `Configs:189` — **anh huong TRUC TIEP size live**: `budget = 14000*0.03*throttle/13` vs sim `equity*0.03*throttle/1` |
| **`DCA_GRID_SCALE`** | khong dat => **1.0** | **1.5** | **19.5** | ⚠️ chi vao qua `DcaUtils.gridLegWeightRatio` — **duong live KHONG BAO GIO goi ham nay** => vo hieu tren live |
| **`TIER_FLAT`** | khong dat => **false** (tier 1.2/1.0/0.5 CO chay) | **1** (tat tier) | 1 | ✅ `CoinRankManager:117` |
| **`CAPITAL_START`** | **14000** | **35000** | 35000 | ✅ `Configs:462` |
| **big_down / `DCA_LEVEL1`** | **CO** (vi `SELECTOR_ONLY_ENTRY=false`) | **KHONG** | **CO** | ✅ |
| **funding (`SIM_APPLY_FUNDING`/`SIM_FUNDING_MARK`)** | khong dat => `APPLY_FUNDING_FEE=false` | **true/true** | true/true | ❌ **sim-only ke toan** (`Configs:516,517`) — live tra funding THAT cho san, khong qua co nay |
| **`SIM_BREAKER_MODE`** | khong dat | OFF | OFF | ✅ guard `Configs:568`; co che breaker **da bi go** khoi engine |
| **cau dao mat do (`is50PercentOrderLossProd`)** | **CO** (kill-switch live, doc lap breaker) | khong co trong sim | nt | ✅ live-only (`DetectEntry...:545`) |
| **`SIM_FIX_B1`** | (jar 02/09 co the chua co code nay) | **true** | true | ❌ **sim-only** — `Simulator...:848` |
| **`SIM_FIX_B2`** | default `true` khi thieu key | **true** | true | ⚠️ doc o `DcaUtils:62` **nhung duong live khong goi `gridLegWeightRatio`** => **LIVE KHONG DOI MOT BIT**. ✅ **XAC NHAN khang dinh cua agent truoc** |
| **`SIM_FIX_B3`** | — | **true** | true | ❌ **sim-only** — `Simulator...:973` (`BudgetManagerSimple.equityNow`) |
| **nguon gia** | Aerospike 242 ns=`ticker`, quyet dinh theo nen 1m da dong, size theo `price_realtime` | dataset `wfo_ds_*` (`TICKER_SOURCE=file`, neo 60395) | nt | — |

### 2.1 ⚠️ Hai key trong `env.sh` live khong tim thay reader

`grep -rn "TS_PRED_GAP\|SIM_TS_PROFIT_MULTIPLIER" src/main/java/` tren HEAD `39c571d` ra
**0 reader**; chi con chu thich `BinanceOrderTradingManager:419` ghi field da bi xoa
(FROZEN v1 2026-08-24, `TS_PROFIT_MULTIPLIER=1.0` == `TS_RATCHET_DECOUPLED=true`).
**Nhung jar dang chay tren 242 la ban 02/09**, khong phai HEAD, nen day **chua phai ket luan
ve nhi phan dang chay**. `grep -c` truc tiep len file jar tra 0 cho MOI key (jar la ZIP nen,
chuoi bi deflate) => phep thu do **vo nghia**, khong duoc dung.
**Lenh cho user kiem dut diem** o muc 6.

### 2.2 Ba khac biet quan trong hon moi tham so trong bang

1. **Selector la hai HE khac nhau**, khong phai hai gia tri. Sim: thu tu = S1 (9 feature
   hourly), gia tri = G015x26. Live: ca thu tu lan gia tri = mot model 45-feature duy nhat.
2. **Live thieu time-stop 168h.** Trong C3, `STOP_LOSS_DONE` = time-stop, chiem `TSloss%`
   14.87% so lenh voi `mean(profit|SL)` −21.85. Tren live nhung lenh do **khong bao gio bi
   dong bang co che nay**; chung nam mai cho toi khi trailing bat hoac coin delist.
   `docs/plan/HOLD_TO_DIE.md` da do counterfactual nay.
3. **Live ratchet co dead-zone 26.1%, sim khong.** Voi phan bo peak cua C3 (p90 = 12.06%),
   **da so lenh live se KHONG BAO GIO ratchet lan hai** — SL dung o muc arm dau tien.
   Sim thi keo SL len lien tuc. Hai duong exit khac nhau ve chat.

---

## 3. FEASIBILITY — C3 chay forward can gi

### (a) 9 feature S1 co tinh live duoc khong

`s1_rank.py:KEEP` = `vol_7d, dd_7d, rk_dd_7d, hrs_since_high_7d, ret_3d, rk_ret_3d, ret_14d,
ls_global, rk_oi_delta24h`. Nguon trong `feat_v2_build.py`:

| feature | nguon offline | co nguon LIVE khong | do tre | warm-up |
|---|---|---|---|---|
| `ret_3d`, `ret_14d`, `vol_7d`, `dd_7d`, `hrs_since_high_7d` | `CLOSES_1H.bin` (luoi gio, close nen 1h) | ⚠️ **gian tiep**: Aerospike 242 ns=`ticker` co `kline_1m`; gop 60 nen 1m -> 1h | ~1 phut | **`ret_14d` can 336 gio = 14 ngay**; `hrs_since_high_7d`/`dd_7d`/`vol_7d` can 168 gio |
| `rk_dd_7d`, `rk_ret_3d` | rank cross-section cua 2 feature tren | ✅ suy ra duoc trong tick | — | nt |
| `ls_global` | `oi_percoin_full.bin` cot 3 | ✅ **CO SAN LIVE**: `LiveOiFeatProvider.lookup()[2]`, doc Aerospike-242 set do `ComputeOiFeat2Live242` push (cadence 60') | asof backward, tol **2h** | — |
| `rk_oi_delta24h` | rank cua `oi_delta24h` | ✅ `lookup()[0]` roi rank trong tick | nt | — |

**Ket luan (a): ve DU LIEU thi lam duoc, ve MA NGUON thi chua co gi.**
- Khong ton tai component nao tinh 7 feature gia theo gio o live. Phai viet moi (Java trong
  `DetectEntrySignal2TradeNormal`, hoac mot job Python sidecar ghi score vao Aerospike).
- 🔴 **Bay ve nguon goc**: `docs/plan/H1_HOLDOUT_PREP.md` muc 3 do duoc `CLOSES_1H.bin[t]` = close
  cua **kline 1h Binance** co `open_time = t - 1h` (sai so 4e-08), va gia thuyet "dung ticker
  1m gop len" bi bac. Dung **kline_1m gop** se cho mot chuoi **KHAC** chuoi da train S1
  => feature live lech phan bo so feature train. Phai do lai truoc, khong duoc gia dinh.
- Warm-up 14 ngay: doc lui duoc tu Aerospike nen khong phai cho, nhung phai kiem `kline_1m`
  242 co du 14 ngay lich su cho **toan bo** universe (~700-900 coin) hay khong.

### (b) Model S1 da luu file chua — **CHUA**

`s1_rank.py` ham `run()`: `m.fit(...)` -> `m.predict(oos[FE])` -> `pd.concat(preds)` ->
`P[["ts","sym","score"]].to_parquet(...)`. **Khong co `save_model`/`save_raw`/`pickle`.**
Model song trong bien `m` roi bi ghi de moi fold; ket thuc process la mat.
Tim tren dia: chi co `model_wfo_last_{4,12,24,72}h.ubj` (ho selector cu, KHAC S1) —
**khong co artifact S1 nao**.

**Chi phi tai lap**: re. Du lieu con nguyen (`/home/ubuntu/ledger/cand_dev.parquet`,
`/home/ubuntu/featv2/feat_v2.parquet`; ban 48 thang o `research/pipeline/x1/x1_s1_rank.py`).
Fold cuoi cua X1 la cutoff `20251001`. Train mot `XGBRanker` (300 cay, depth 4, `n_jobs=4`)
tren `ts < cutoff - 72h` roi `save_model(.json)` — CPU, vai phut.
⚠️ **Nhung mot model train toi 2025-10 chi hop le cho OOS 2025Q4.** Chay forward 2026-09 la
**du bao ngoai mep train 11 thang**. Phai hoac (i) chap nhan va ghi ro, hoac (ii) mo rong
`cand_dev`/`featv2` toi hien tai — ma cai do bi chan boi **blocker `CLOSES_1H` khong co
generator** (`H1_HOLDOUT_PREP` muc 3). => **(b) khong doc lap voi (a).**

### (c) Gia tri gate — G015x26 khong tai lap. Hai phuong an

**Nhac lai `symbolPred` di vao dau khi `SELECTOR_RANK_TOPK>0`:** DUNG MOT cho —
ban le trailing STRONG/WEAK. Gate tang 2 bi bo qua. Nen day **khong phai** cau hoi ve gate
admission, ma la cau hoi ve **cap trailing**.

**(i) `G015_v2` (tai lap duoc) chay live** — can 45 feature Tool1 real-time.
🟢 **Tin tot, va no lat nguoc de bai**: **live DA CO san duong nay.**
`FundingOnnxInferenceManager` (45 input = 40 Tool1 + 5 OI) dang chay moi tick tren 242,
model `Funding_Classifier_Final.onnx`. `ds_feat15m` la ban offline cua CHINH bo feature do
(`ExportFeaturesForPythonTool.convertFeaturesToArray` + 5 OI, thu tu KHOA).
=> Khong can dung `ai_models_reg_v3` (do la model **gate**, khac viec).
⚠️ Nhung hieu chuan **KHAC**: gia tri live do duoc trong log **0.054-0.116**; X3 do gia tri
G015x26 trong mot tick **0.3547/0.3586/0.3613**. Voi ban le 0.29: live => **gan 100% STRONG**;
C3 sim => 83.8% STRONG (X1, 48 thang). **Khong tuong duong, nhung lech theo huong da biet.**

**(ii) Hang so / S1-percentile thay `symbolPred`.**
Vi ban le la nguong TUYET DOI, mot hang so chi cho ra **mot trong hai** ket qua: 100% STRONG
hoac 100% WEAK. S1-percentile cung vay tru khi doi ban le — ma X3 muc 3 da do: ban le
**gan nhu TRUC GIAO voi rank** (spread %STRONG theo rank chi 6.8pp), va `TS_CAP_STRONG_RANK`
(2/4/6) ra **NULL** (0/8 rate ngoai CI).

**KHUYEN NGHI: phuong an (i)** — dung chinh `Funding_Classifier_Final.onnx` dang chay live
lam nguon `symbolPred`, KHONG thay bang hang so.
Ly do: (1) khong them phu thuoc moi; (2) no la **cung ho model** voi G015 (45 feature,
nhan pump/no-pump), khac `predwf_G015x26` o ban train chu khong o thiet ke; (3) ket qua run
doi chung muc 4 cho thay thay gia tri nay bang hang so **khong pha ket qua** — nen sai so
cua (i) bi chan tren boi so o muc 4.

🔴 **GHI RO — day la diem shadow C3 se KHAC sim C3:**
> Trong sim, `symbolPred` la gia tri cua `predwf_G015x26` (mot artifact dong bang, khong tai
> lap, khong co ban 2026). Trong shadow, no la output cua `Funding_Classifier_Final.onnx`.
> **Hai phan phoi khac hieu chuan** (live ~0.05-0.12 vs sim ~0.35). Hau qua: ty le nhanh
> trailing STRONG cua shadow se cao hon C3 (uoc gan 100% vs 83.8%). Moi so sanh
> shadow<->sim phai **tach rieng nhom STRONG/WEAK** truoc khi ghep cap.

### (c-bis) Run doi chung DEV — DA CHAY, xem muc 4

### (d) Gate `p15` — live va sim co cung model khong

- Sim: `p15 = predReturn15M` doc tu Aerospike set `ai_pred_market_gate_wfo`, nap tu
  `claudedata/wfo_gate_pred.csv` do `WFOGateRunner` (21 fold, expanding, `train_gate_fold.py`
  -> ONNX) sinh ra. (`H1_HOLDOUT_PREP` muc 1.1)
- Live: `DataManagerAerospikeFloatSim.getAiPredictionAtTime(...)` -> `predReturn15M`, sinh boi
  `Model_Regressor_Return15M.onnx` (144,774 B) trong `ai_models_reg_v3`. File nay xuat hien
  **17/08/2026 16:27** va ben canh no la `Model_Regressor_Return15M.onnx.bak_gatewfo_20260817`
  (189,507,135 B) — tuc **ngay 17/08 model gate live DA duoc thay bang ban gate-WFO**, va ban
  189MB la model CU bi day sang .bak.
- **=> Rat co kha nang CUNG HO model**, nhung **KHONG XAC NHAN duoc bang so trong dot nay**:
  - `wfo_gate_pred.csv` da bi seal cat, chi con **<= 2026-01-01**.
  - Ban tai sinh `wfo_gate_pred_2026_H1.csv` phu **2026-01-01 -> 2026-07-01**.
  - Log live con lai bat dau **19/08/2026** (`logs/archived/` khong co full.log 2026-01..08).
  - **Khong co cua so nao giao nhau** => khong so duoc.
- Do duoc gian tiep: gia tri live 06/09 `return15M` = **0.00937 / 0.00947 / 0.00994**, nguong
  `Min15M = 0.80%` => sat nguong, gate dang o che do "vua du mo". Hop ly voi mot model 15m.

**Ket luan (d): CHUA CHUNG MINH DUOC dong nhat.** Khong duoc gia dinh. Phep do dut diem re
nhat: khi da co shadow, ghi `predReturn15M` cua shadow moi phut ra file va so voi
`wfo_gate_pred.csv` **sinh lai bang `h1_p15_gen.py` cho dung cua so shadow** (can feature
store gate keo dai qua 2026-07-01 — hien **chua co**, la blocker rieng).

### (e) Sizing — shadow khong co tai khoan that

- **Khong co mode paper-equity.** `BudgetManager.balanceBasic = Configs.capitalStart()` (hang
  so tu `config.properties`), va `updateBudget()` goi
  `BinanceFuturesClientSingleton.getAccountUMInfo()` **chi de LOG** `balanceCurrent`.
- 🔴 **Nhung co mot bay cung**: `BUDGET_PER_ORDER = balanceBasic / number_order_budget` duoc
  gan **SAU** loi goi API trong cung block `try`. Key API tren Oracle la **STUB**
  (`PrivateConfig.API_KEY = "STUB_NOT_A_REAL_KEY_..."`, file that trong `.gitignore`) =>
  `getAccountUMInfo()` NEM => `BUDGET_PER_ORDER` **o nguyen 0f** => moi entry bi chan.
  Ngoai ra `updatePositionInfo()` (`BinanceOrderTradingManager:345`) goi `getAllPositionInfos()`
  moi giay, cung se nem.
- **=> Chay shadow tren Oracle bang jar hien tai se KHONG sinh mot dong `would-BUY` nao.**
  Ba lua chon, deu la thao tac tren DEV (Oracle), khong cham 242:
  1. **Key read-only Binance** (khong co quyen trade). `getAccountUMInfo`/`getAllPositionInfos`
     la endpoint `USER_DATA` — key read-only dung duoc. **User phai tao key moi; TUYET DOI
     khong dung key that cua bot.**
  2. **Stub o tang client**: cho `BinanceFuturesClientSingleton` tra `walletBalance` gia lap va
     `getAllPositionInfos()` tra rong khi bat co `PAPER_EQUITY=<so>`. Sua ~20 dong, nam sau mot
     co mac dinh TAT => `X1_C3` van byte-identical. **Day la duong sach nhat**, nhung la mot
     thay doi ma nguon nen phai pre-reg + unit test + cong hoi quy.
  3. Khong sua gi, chap nhan shadow **chi log tin hieu** neu ta bo qua nhanh budget — khong lam
     duoc vi budget la mot cong `return` som.
- **PnL**: du lua chon nao, shadow **khong co equity that** => `SIM_FIX_B3` (compound) khong
  the tai lap live. **PnL cua shadow PHAI tinh offline tu log** (entry/exit/qty), bang
  `tools/shadow_vs_sim.py` (muc 7). Ghi ro: **so equity cua shadow la ke toan giay, khong
  phai ket qua giao dich.**

### (f) RAM / ha tang — shadow o dau

| | 242 | Oracle |
|---|---|---|
| RAM | 7G total, **0G free / 2G available** | 23G total, **16G free / 19G available** |
| dia | 92G, con 17G | 194G, **con 6.9G (97%)** 🔴 |
| JVM dang chay | 2 (trading 7G heap + ingestor 2G) | 0 (luc kiem) |

**=> Shadow phai chay tren Oracle**, dung `-Xmx4g` (con du cho sim 16g **khong** chay dong
thoi — Oracle chi **1 slot JVM** cho sim, bay #4; shadow 4g + sim 16g = 20g/23g, sat qua).
🔴 **Phai xep lich: shadow va sim khong chay cung luc, hoac ha `-Xmx` cua sim.**

Ket noi tu Oracle -> 242 can kiem/khai bao:
- `AEROSPIKE_HOST=103.157.218.242:3222` ns=`ticker` — **listen tren IP public** (`ss -lntp` xac
  nhan `103.157.218.242:3222`). Bot doc `kline_1m`, `price_realtime`, `ai_pred_market_*`,
  va 5 set OI live tu day.
- 🔴 **Redis 242:30001-30006 la BAT BUOC va DAY LA RUI RO NANG NHAT cua ke hoach shadow.**
  Duong entry di qua Redis: `DetectEntry...:614` `rpush` vao
  `REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE`, `BinanceOrderTradingManager:127` `blpop` **cung
  key do**. Neu shadow tro vao cum Redis cua 242 thi no se:
  (1) `blpop` **CUOP** lenh cua bot live khoi hang doi, va
  (2) ghi de `REDIS_KEY_SYMBOL_2_ORDER_INFO` cua live.
  **=> Shadow BAT BUOC phai co Redis RIENG tren Oracle** (`redis.config` rieng, cluster hoac
  single-node tuy `RedisDriver`). Day khong phai toi uu, day la dieu kien an toan.
  `ss -lntp` tren 242 cho thay **30004 KHONG listen** (chi 30001/2/3/5/6) — cum dang thieu 1
  node; them mot client la khong duoc.

---

## 4. RUN DOI CHUNG — "symbolPred = HANG SO" (DA CHAY, 48 thang)

Pre-reg `docs/prereg/PREREG_L1.md` (commit `39c571d`), viet va commit **TRUOC** khi chay.

### 4.1 Thiet ke — re hon de bai de xuat, va CHINH XAC hon

De bai de xuat sinh bins moi voi `symbolPred` hang so. **Khong can.** Khi
`SELECTOR_RANK_TOPK>0`, gia tri `symbolPred` di vao **DUNG MOT cho**: ban le
`pnp <= TS_PNOPUMP_WEAK_THR` trong `OrderTargetInfoTest.trailRate()`. Dat mot hang so
cho `symbolPred` tuong duong dat ban le ra ngoai dai gia tri — ma cai do co san key
`SIM_TS_PNOPUMP_WEAK_THR`.

Loi the: **giu NGUYEN thu tu selector** (neu lam bins hang so thi ranking bi pha, khong
con do duoc mot minh gia tri gate) va **khong phai build lai bins hay dataset** (dung lai
`/home/ubuntu/wfo_ds_x1`, dia con 6.9G khong du de build).

| arm | profile | khac `x1_c3` | y nghia |
|---|---|---|---|
| `L1_PNP_STRONG` | `l1_pnp_strong.properties` | `SIM_TS_PNOPUMP_WEAK_THR=1.0` | hang so DUOI ban le -> **100% STRONG** (cap 0.08) |
| `L1_PNP_WEAK` | `l1_pnp_weak.properties` | `SIM_TS_PNOPUMP_WEAK_THR=0.0` | hang so TREN ban le -> **100% WEAK** (cap 0.03) |

Hai arm **chan tren va chan duoi** moi hang so co the co. `SIM_END_DATE=20251231` —
khong cham holdout 2026. `TICKER_SOURCE=file`. Chay tuan tu, 1 slot JVM. 739 giay/arm.

Kiem nguong da ap that (**khong tin bang "NHANH TRAILING" cua `x1_rates.py`** — bang do
phan loai HAU KIEM bang 0.29 co dinh tren cot CSV, dung cai bay `C3_BASELINE` muc 4 da ghi):
`X1_C3` 1,724/334 (83.8% STRONG) · `L1_PNP_STRONG` **2,056/0 (100.0%)** · `L1_PNP_WEAK`
**0/2,077 (0.0%)**. ✅ Ban le da bi vo hieu dung nhu thiet ke.

### 4.2 Bang chinh

| arm | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | mMargin | maxDD% | UW | equity | CAGR% | md5 printDone |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `X1_C3` (nen) | 2,058 | 85.33 | 14.87 | 7.178 | −21.848 | 2.863 | 1,918 | −13.31 | 302 | 98,523 | 29.58 | `d39da294...` |
| `L1_PNP_STRONG` | 2,056 | 85.31 | 14.88 | 7.190 | −21.848 | 2.869 | 1,931 | −13.26 | 302 | **98,972** | 29.72 | `93627374...` |
| `L1_PNP_WEAK` | 2,077 | 85.41 | 14.78 | 7.185 | −21.927 | 2.882 | 1,955 | **−12.89** | **240** | **103,231** | 31.10 | `f11c0168...` |

### 4.3 CI khoi-72h (x1.21, luoi khoi chung, toan cua so)

| so sanh | rate ngoai CI | ket luan |
|---|---|---|
| `L1_PNP_STRONG` − `X1_C3` | chi `mMargin` (+13.2, CI [+11.4,+15.0]) | **0/5 rate CHAT LUONG ngoai CI** |
| `L1_PNP_WEAK` − `X1_C3` | `n` (+19, CI [+3.2,+35.9]) va `mMargin` (+36.9) | **0/5 rate CHAT LUONG ngoai CI** |

`mMargin` la bien KIEM SOAT (thang do), khong phai bang chung chat luong — dung mach
`C3_BASELINE` muc 7 da ghi.

### 4.4 🔴 KET LUAN — va no manh hon ky vong

**Gia tri cua `symbolPred` KHONG load-bearing tren bat ky rate chat luong nao.**
Thay no bang hang so — o **ca hai cuc** — cho **0/5 rate ngoai CI**. Khoang cach equity
lon nhat do duoc la **+4.78%** (`L1_PNP_WEAK`), tuong duong **CAGR +1.52pp**, **nam gon
trong nhieu `sd(dCAGR)` = 2.57pp** ma `AGENT_RUNBOOK` muc 0.3 da chot.

**He qua truc tiep cho shadow (tra loi cau (c)):**
> Viec shadow phai dung `Funding_Classifier_Final.onnx` thay cho `predwf_G015x26` —
> mot phan phoi lech hieu chuan hoan toan (0.05-0.12 vs ~0.35) — **KHONG lam hong phep
> do**, vi hai cuc cua chinh truc do da duoc do va deu NULL. Sai so cua phuong an (i)
> bi **chan tren** boi khoang cach `STRONG`-`WEAK` do o day.
> **Day khong con la blocker cua shadow C3.** Blocker con lai la **S1** (muc 3a/3b), khong
> phai gate value.

**Quan sat phu, phai ghi vi no nguoc voi truc giac:** arm `100% WEAK` (cap chi 3%) cho
**maxDD tot hon** (−12.89 vs −13.31) va **UW tot hon 62 ngay** (240 vs 302) — dung cai
rang buoc R4 dang chan `C3`. Nhung `n` cung doi (+19) va **0/5 rate chat luong ngoai CI**,
nen day **KHONG phai mot cai tien do duoc**; no cung kieu single-realization ma `X3` muc 3
da canh bao la NHIEU. **Khong de cu, khong tune.**

### 4.5 DU DOAN GHI TRUOC — dung 3/4, **SAI 1**, ghi nguyen van

| # | du doan (`PREREG_L1` muc 4) | thuc te | |
|---|---|---|---|
| 1 | `n` **giong het** 2,058 o ca hai arm | **2,056** va **2,077** | ❌ **SAI** |
| 2 | `L1_PNP_STRONG` khong rate nao ngoai CI | 0/5 | ✅ |
| 3 | `L1_PNP_WEAK` doi HINH DANG winner (than len, duoi phai tut) | p10 3.500→**4.242**, p25 4.000→**4.986**, med 4.999→**5.999**, p75 7.446→**8.000**, p90 12.495→**11.024** | ✅ dung ca chieu |
| 4 | lech equity < 5% | +0.46% / +4.78% | ✅ |

🔴 **Vi sao du doan 1 SAI — day la thong tin, khong phai loi vat.**
Toi lap luan "ban le chi tac dong SAU khi arm nen khong doi tap lenh vao". Sai o mot mat
xich: cap trailing doi => **thoi diem thoat** doi => `marginRunning` tai moi tick doi =>
`throttle = 1 − u/U_MAX` doi => mot vai tick o sat tran von **lat** quyet dinh admission.
=> **`n` KHONG bat bien duoi bat ky thay doi exit nao khi sizing la compound.** Cai nay
ap cho MOI dot do exit tren engine sau B3, khong rieng dot nay. Ghi vao `AGENT_RUNBOOK`.
(Do lon: 2/2,058 = 0.1% o `STRONG`, 19/2,058 = 0.9% o `WEAK` — nho, nhung khac 0.)

---

## 5. SHADOW DUNG DUOC TOI DAU — **DUNG LAI, KHONG DUNG**

Theo de bai: "neu (b)+(c) chua xong -> DUNG o day, ghi ro thieu gi, dung chay shadow voi
selector cu roi goi la C3". **Dieu kien do dang KHONG dat.** Khong tao
`/home/ubuntu/shadow_c3/`, khong copy jar, khong chay `nohup`. Ly do, theo thu tu chan:

| # | chan | trang thai | go duoc chua |
|---|---|---|---|
| B1 | **Model S1 khong co file** (muc 3b) | 🔴 chan | train lai duoc (CPU, vai phut) — nhung xem B2 |
| B2 | **Khong co bo tinh 9 feature S1 real-time** (muc 3a) | 🔴 chan | phai VIET MOI + phai do lai nguon gia (`CLOSES_1H` = kline 1h, khong phai ticker 1m gop) |
| B3 | **Live khong doc `WFO_FUNDING_PRED_DIR`** (muc 0.1) | 🔴 chan | phai viet duong cam score S1 vao `selectorRankPool` |
| B4 | **`BUDGET_PER_ORDER = 0` khi khong co API key** (muc 3e) | 🔴 chan | key read-only, hoac co `PAPER_EQUITY` (sua ma nguon, phai pre-reg) |
| B5 | **Redis phai rieng** (muc 3f) | 🟡 lam duoc | dung redis rieng tren Oracle |
| B6 | **Live khong co time-stop 168h** (muc 0.5) | 🟡 chap nhan / ghi ro | `LIVE_LOSER_TIME_STOP_HOURS` da tung ton tai (`e2c8fde`) nhung khong con reader o HEAD |
| B7 | **Live co dead-zone ratchet 26.1%, sim khong** (muc 0.4) | 🟡 chap nhan / ghi ro | hardcode, muon bo phai sua ma nguon |
| B8 | **Dia Oracle 6.9G** | 🟡 | don dia truoc |

**Neu bo qua B1-B3** (tuc dung selector 45-feature live thay S1) thi cai chay duoc **KHONG
PHAI C3**. No la "cau hinh exit cua C3 + selector live". Goi dung ten no la vay; **khong duoc
dat nhan C3 len ket qua do**, va no khong tra loi duoc cau hoi "C3 co song ngoai DEV khong".

### 5.1 Thu tu viec de mo khoa (de xuat, moi buoc mot pre-reg)

1. **Do nguon gia** — dung `kline_1m` Aerospike 242 gop len 1h cho 3 coin x 1 thang, so voi
   `CLOSES_1H.bin` cung khoang. Sai so tuong doi phai <= 1e-6. FAIL => B2 khong go duoc bang
   duong nay va `H1` cung ket (cung mot blocker).
2. **Train + luu S1** (`x1_s1_rank.py` + `save_model`) tai cutoff `20251001`, ghi
   `research/pipeline/S1_MODEL_MANIFEST.md` (sha256 + feature order + cutoff).
3. **`PAPER_EQUITY`** (hoac key read-only) — cong hoi quy: `X1_C3` byte-identical
   (`d39da2940dfd815f60772f70517750bf`).
4. **Sidecar S1 live**: job doc `kline_1m` + OI 242, tinh 9 feature, predict, ghi score vao
   Aerospike; bot doc score do vao `selectorRankPool`. Cong: score offline cua ngay X phai
   trung score sidecar tinh cho ngay X.
5. Chi khi 1-4 xong moi dung duoc chu **shadow C3**.

---

## 6. LENH CHO USER — moi thu can CHAM 242 (agent khong lam)

**Khong lenh nao duoi day la bat buoc cho ke hoach shadow.** Chung la de (i) lam sach trang
thai live va (ii) tra loi hai cau con treo. Doc ky truoc khi chay — 242 la tien that.

### 6.1 (CHI ĐỌC — an toan) Xac dinh 2 key `TS_PRED_GAP` / `SIM_TS_PROFIT_MULTIPLIER` co song
trong **jar dang chay** khong (muc 2.1). `grep` thang len jar la VO NGHIA (ZIP nen).

```
ssh -p 2222 root@103.157.218.242
cd /home/chuyennd/java/v_t_m
mkdir -p /tmp/jarx && cd /tmp/jarx
unzip -o -q /home/chuyennd/java/v_t_m/target/binance-java-sdk-1.2.4.jar \
  'com/binance/chuyennd/tradecore/Configs.class' \
  'com/binance/chuyennd/trading/BinanceOrderTradingManager.class'
strings com/binance/chuyennd/tradecore/Configs.class | grep -E 'TS_PRED_GAP|TS_PROFIT_MULTIPLIER'
strings com/binance/chuyennd/trading/BinanceOrderTradingManager.class | grep -E 'TS_PRED_GAP|TS_PROFIT_MULTIPLIER'
rm -rf /tmp/jarx
```
Khong ra dong nao => hai key trong `env.sh` la **key chet**, nen xoa khoi `env.sh` (lan restart
sau) de khong ai doc nham la he dang chay pred-gap.

### 6.2 (CHI ĐỌC) Kiem `kline_1m` 242 co du 14 ngay cho toan universe (dieu kien cua muc 3a)
```
ssh -p 2222 root@103.157.218.242
grep -a 'Update all position' /home/chuyennd/java/v_t_m/logs/full.log | tail -1
ls -la /home/chuyennd/java/storage/ticker/ | head
```
(242 khong co `aql`/`asinfo`; phep dem chinh xac phai lam tu Oracle qua client Aerospike.)

### 6.3 🔴 (GHI — TIEN THAT, chi lam khi user quyet) Giai phong 66 vi the de shadow 242 song lai
Hien `u = marginRunning/14000 = 0.81 >= U_MAX 0.60` nen **moi entry shadow bi chan**
(muc 1.1). Muon log shadow tren 242 co gia tri lam doi chung thi phai **dong 66 vi the**.
Day la quyet dinh giao dich, **khong phai viec ky thuat**, va **agent khong de xuat lam**.
Neu lam, lam **tay tren Binance UI**, khong qua bot.
Ban chi de doi chung: **giu 242 nhu hien tai** va dung Oracle lam shadow (muc 5).

### 6.4 (GHI — cau hinh, khi da san sang bat lai) Doi trang thai shadow/real
Da co san trong `docs/runbooks/runbook_shadow_off_trade_2026-08-23.md`. Khong lap lai o day.
⚠️ Restart PHAI qua `bin/daemon.sh restart` (source `conf/env.sh`).
Verify sau restart: `xargs -0 -n1 -a /proc/$(cat run/*.pid)/environ | grep -E "SIM_|SHADOW"`.

### 6.5 (GHI — khi trien khai jar moi len 242) **DUNG deploy jar Oracle hien tai len 242**
Jar Oracle `39c571d` chua `SIM_FIX_B2` (mac dinh **true**). Tren duong live `FIX_B2` di vao
`DcaUtils.gridLegWeightRatio` — **ma duong live khong goi ham do**, nen ve ly thuyet vo hai.
Nhung jar do con chua toan bo thay doi X1/X2/X3 chua tung chay tren live. **Deploy la mot
viec rieng, phai co runbook rieng va pre-reg rieng.**

---

## 7. DOI CHUNG SHADOW <-> SIM

Cong cu: `tools/shadow_vs_sim.py` (da viet trong dot nay, **chua co du lieu de chay**).

- Doc: `tools/shadow_vs_sim.py parse <full.log> <out.csv>` -> bang lenh
  `sym, ts, side, entry, qty, market_level, rank, symbol_pred, exit_ts, exit_px, profit`.
  Nguon dong: `[SHADOW] would-BUY ...` (entry), `AI PASS [sym] ... symbolPred: x` (gia tri
  gate), `Market level:...` (budget/qty), `Remove symbol trade success` (dong).
- Ghi `shadow_c3/ledger.csv`, cap nhat dinh ky (cron Oracle moi gio):
  `0 * * * * cd /home/ubuntu/shadow_c3 && python3 <repo>/tools/shadow_vs_sim.py parse logs/full.log ledger.csv >> logs/cron.out 2>&1`
- So voi sim khi da co **>= 4 tuan**: chay sim C3 tren **dung cua so shadow da troi qua**,
  roi ghep cap tung lenh theo `(sym, ts_entry)` — giong cach `X2`/`X3` do "chi phi cat oan".

### 7.1 🔴 LUAT UNSEAL — ghi ro, khong duoc lach

> Cua so ma shadow **da chay qua roi** thi **khong con la holdout**: shadow da "nhin" no.
> Do do khi doi chung, chi duoc `HOLDOUT_UNSEAL` **DUNG doan da troi qua**, khong duoc mo
> them mot ngay nao ve tuong lai. Moi lan mo phai:
> 1. co user duyet TRUC TIEP trong chat (`AGENT_RUNBOOK` muc 0.1),
> 2. ghi vao ledger holdout la da tieu doan do,
> 3. `unset HOLDOUT_UNSEAL` + niem phong lai ngay sau khi chay.
>
> **He qua phai chap nhan tu dau**: moi tuan shadow chay la mot tuan holdout bi tieu.
> Doi 4 tuan roi doi chung = tieu 4 tuan. Do la CAI GIA cua forward test, khong phai loi cua
> quy trinh. Neu khong chap nhan gia do thi khong nen bat shadow.

### 7.2 Ba phep so BAT BUOC tach rieng (khong duoc gop)

1. **Tap lenh vao** (`n`, ty le trung `(sym, ts)`): do selector + gate. Nhay voi K=5 vs K=8
   va voi selector khac he (muc 2.2.1) => **du kien lech lon**, dung coi la loi.
2. **Ket qua tung lenh** (`win%`, `mP|SM`, `mP|SL`): chi so tren **tap lenh GHEP CAP DUOC**,
   va **tach STRONG/WEAK** (muc 3c) truoc khi so.
3. **Thang do** (`mean(margin)`, equity): **KHONG so duoc** — shadow khong co equity that
   (muc 3e). Bao rieng, dan nhan "ke toan giay".

---

## 8. ARTIFACT DOT NAY

| duong dan | noi dung |
|---|---|
| `docs/experiment/L1_SHADOW_C3.md` | file nay |
| `docs/prereg/PREREG_L1.md` | pre-reg run doi chung `symbolPred = hang so` (commit `39c571d`) |
| `profiles/l1_pnp_strong.properties` | `x1_c3` + `SIM_TS_PNOPUMP_WEAK_THR=1.0` (100% STRONG) |
| `profiles/l1_pnp_weak.properties` | `x1_c3` + `SIM_TS_PNOPUMP_WEAK_THR=0.0` (100% WEAK) |
| `tools/shadow_vs_sim.py` | parse log shadow -> ledger.csv (chua co du lieu de chay) |
| `/home/ubuntu/java/devrun/L1_PNP_STRONG`, `L1_PNP_WEAK` | 2 run doi chung |

## 9. NO KY THUAT PHAT HIEN TRONG DOT NAY

1. 🔴 `s1_rank.py` / `x1_s1_rank.py` **khong luu model**. Bins `predwf_map_s1a2*` la output
   duy nhat con lai cua S1 — cung mot loai no ky thuat nhu `predwf_G015x26`
   (single point of failure), chi khac la **con tai lap duoc** vi con du lieu.
2. 🔴 `BudgetManager.updateBudget()`: `BUDGET_PER_ORDER` duoc gan SAU loi goi API trong cung
   `try` => mot loi mang thoang qua o Binance cung lam `BUDGET_PER_ORDER` **giu gia tri cu
   hoac 0** ma khong co canh bao. Tren live day la mot cho hong that (khong phai chi bay
   cho shadow).
3. ⚠️ `TS_PRED_GAP` / `SIM_TS_PROFIT_MULTIPLIER` trong `conf/env.sh` cua 242 khong co reader
   o HEAD — `env.sh` va runbook `rev5` deu mo ta chung nhu dang co tac dung. Can 6.1 de chot.
4. ⚠️ Redis cluster 242 dang thieu node **30004** (chi 30001/2/3/5/6 listen).
5. ⚠️ `242/config.properties` co `CAPITAL_START=14000` con moi profile sim dung **35000** —
   hai the gioi khac nhau ve thang do, de doc nham khi so PnL.
