# AGENT_RUNBOOK — doc DAU TIEN moi session/agent moi

Muc dich: mot session moi (ke ca model yeu hon) doc file nay la du de tiep tuc,
khong can hoi lai user, khong can doc lai 30 doc khac.

## 0. LUAT CUNG — vi pham la sai, khong phai lua chon

1. **DEV = 2022-01-01 -> 2025-12-31 (48 thang)** tu 2026-09-05 (`docs/experiment/X1_EXTEND.md`).
   User da quyet: 2024-07 -> 2026-01 (xua la VAL) **nhap vao DEV**. **KHONG CON VAL SACH** —
   validate cuoi cung = **forward test**. Holdout duy nhat con lai la **2026**
   (`HoldoutSeal.SEAL_MS = 2026-01-01`; du lieu pred/gate 2026 da bi xoa khoi Oracle).
   Mo 2026 phai co user duyet TRUC TIEP trong chat + `HOLDOUT_UNSEAL`. Khong tu quyet.
   Chan 2021H2 (mo nguoc) **DA THU VA BO** — ly do cung o `X1_EXTEND` muc 1.2.
2. **Pre-register TRUOC khi chay.** Viet `docs/PREREG_<TEN>.md`, commit, ROI moi chay.
   Khong sua pre-reg sau khi thay ket qua. Null co tinh thong tin — bao cao null.
3. **Equity KHONG phai tieu chi.** `sd(dCAGR)` exit params = 2.57pp;
   `E[max nhieu]` = 2.57*sqrt(2 ln N) => N=50 cho +7.2pp. DEV da chay ~125 run.
   Tieu chi phai la RATE tren hang tram trade (TSloss%, win%, mean(profit|status),
   admit%). Equity bao cao rieng, dan nhan "khong phai tieu chi".
   -> Nguong RUI RO (khau vi, KHONG phai tieu chi bang chung) — **`docs/runbooks/RISK_APPETITE.md` §6–§7**
      (user chot 2026-09-24): **`maxDD <= 40%/nam` · `UW <= 250 ngay` · `quy xau nhat >= -20%` ·
      `khong nam am` (CUNG) · `tap trung 1 coin <= 15% equity` (CUNG — kenh MAT THAT duy nhat khi
      danh 1x; xem `docs/result/RESULT_FRAGILITY_N.md`)**. Nguong BANG CHUNG (>= 2 rate ngoai CI,
      bootstrap block-72h, 2000 rep, seed 20260905; lay he so bang `x1_rates.py --k <so_round>`) GIU NGUYEN.
   -> **BASELINE (moc so sanh + cong parity) = FLATGRID KEEPLEG0** ke tu 2026-09-24
      (`docs/decisions/DECISION_BASELINE_KEEPLEG0.md`): `profiles/t170_flat_keepleg0.properties`
      (`DCA_GRID_WEIGHTS=1,1,1,1` + `DCA_GRID_SCALE=6.0`), run `java/devrun/FG_KEEPLEG0`,
      printDone md5 **`99e42b75cf1a2142f9cd14dc72e371ba`** (1,085 leg, eq 103,083).
      **`efb793e2` (T170, 1,1,3,8) KHONG con la baseline** — chi la "nen cu" de doi chieu.
      MOI ket luan moi phai do tren baseline MOI; ket luan cu tren nen T170 KHONG tu dong chuyen.
   -> **SO SANH PHAI CUNG NGUON HA TANG** (user chot 2026-09-24): *"neu kaggle thi so voi kaggle con
      oracle so voi oracle"*. Moi bang so sanh (variant vs moc) **PHAI cung mot nguon chay**:
      Kaggle ↔ Kaggle, Oracle ↔ Oracle — **KHONG tron**. Ly do: cung 1 cau hinh co the lech giua hai
      ha tang (ticker source, mount path, phien ban bundle).
      Thuc te: moc KEEPLEG0 ton tai o CA HAI va **byte-identical** (`java/devrun/FG_KEEPLEG0` =
      `kaggle_sim/out/kg0-g170`, md5 `99e42b75`) ⇒ khi so sanh thi **dung ban Kaggle lam moc**
      (vi moi variant moi deu chay tren Kaggle) va **ghi ro nguon trong bang**.
      **Sim MOI = Kaggle** (Oracle KHONG chay sim/job: shadow dang LIVE).
4. **Bao rui ro/lo hong TRUOC**, khong khen, tieng Viet + thuat ngu Anh nguyen ban.
5. **Khong `print()` trong Python** — dung module `logging`. Java dung SLF4J.
6. **Khong push.** Commit branch `module`, de user push.
7. Model cho agent: Opus cho task nhieu buoc/co side-effect (chay sim, sua file,
   xoa file). Sonnet/Haiku cho doc-va-tom-tat. **KHONG dung Fable.**
8. **Shadow C3 tren Oracle — ba luat, xem `docs/experiment/L1_SHADOW_C3.md`.**
   (a) **Cai chay tren duong LIVE khong duoc goi la `C3` neu chua cam duoc score S1.**
   Duong live tinh `symbolPred` bang `Funding_Classifier_Final.onnx` (45 feature) va
   **khong doc `WFO_FUNDING_PRED_DIR`** o bat ky dong nao — bins `predwf_map_s1a2` la
   artifact OFFLINE. Model S1 lai **khong co file** (`s1_rank.py` khong `save_model`).
   Chay shadow bang selector live roi dan nhan C3 = so lieu VO GIA TRI.
   (b) **Shadow tren 242 hien khong sinh tin hieu**: 66 vi the cu giu `marginRunning` =>
   `u = 0.81 >= U_MAX 0.60` => `managerBudget` tra null => 0 dong `would-BUY` tu 27/08.
   Shadow phai chay tren **Oracle** (RAM 23G) voi **Redis RIENG** — tro vao Redis 242 se
   `blpop` CUOP lenh cua bot live.
   (c) **Moi tuan shadow chay la mot tuan holdout bi tieu.** Khi doi chung chi duoc
   `HOLDOUT_UNSEAL` DUNG doan shadow da troi qua, co user duyet truc tiep, roi seal lai.
9. **Shadow C3 Oracle — DA TAT** (`docs/experiment/L2_PORT_C3.md`; trang thai 2026-09-07:
   `health.log` bao `DOWN` lien tuc tu **2026-09-06 19:00Z**, pid mat. Dong bang tai luc tat:
   `wouldBUY=30 wouldCLOSE=4 createOrder=0 errLines=0 ledgerRows=4`. Cron `health.sh` van cai.
   **L4 KHONG khoi dong lai.** Muon chay lai: `cd /home/ubuntu/shadow_c3/app && bin/daemon.sh start`
   — nhung jar trong do la ban L2, CHUA co `LiveBuildMap`; phai copy jar moi vao truoc.)
   - **dir**: `/home/ubuntu/shadow_c3/` · JVM cwd `/home/ubuntu/shadow_c3/app`
     (jar rieng, `config.properties` rieng, `conf/env.sh` co `LIVE_PROFILE=c3_shadow`).
   - **start/stop**: `cd /home/ubuntu/shadow_c3/app && bin/daemon.sh {start|stop|restart|status}`.
     pidfile `run/com.binance.chuyennd.trading.BinanceOrderTradingManager.pid`.
   - **log**: `logs/full.log` (logback RIENG 50MB x 3 — dia Oracle 97%). `logs/error.log`.
     health moi gio: `shadow_c3/health.log` (cron `0 * * * * shadow_c3/bin/health.sh`).
     ledger: `shadow_c3/ledger.csv` (do `ShadowBookC3` ghi, co exit+pnl) va
     `shadow_c3/ledger_from_log.csv` (do `tools/shadow_vs_sim.py parse` dung lai tu log).
   - **Redis**: cum RIENG `127.0.0.1:7301` (`shadow_c3/redis/redis-shadow.conf`, cluster 1 node).
     🔴 **TUYET DOI khong tro vao Redis 242** — se `blpop` CUOP lenh cua bot live.
   - **1 slot JVM Oracle**: shadow chiem **~2.6-3.2G RSS** (do lai 2026-09-20, docs/plan/PLAN_SHADOW_T170_PARALLEL.md; so ~1.7G cu SAI, da dinh chinh). **Dung sim truoc khi chay sim** (`bin/daemon.sh stop`).
   - 🔒 Co `LIVE_PROFILE` **mac dinh TAT** o moi noi khac. Co tat = HEAD (`LiveProfileC3Test`).
     Khi bat, `SHADOW_NO_PUSH` bi HARDCODE `true`, khong doc env.
10. **L3 — goi deploy 242 DA SAN, 242 CHUA DEPLOY** (`docs/experiment/L3_DEPLOY_PREP.md`, 2026-09-06).
   - Quyet dinh user: MOT JVM tren 242 chay `LIVE_PROFILE=c3_shadow`; 66 vi the that cu thanh
     **LEGACY** (dong THAT theo luat HEAD: arm 0.05, dead-zone x5.21847, khong time-stop),
     so giay C3 chay song song, khong lenh that moi.
   - **LEGACY = (vi the that tu Binance) \ (so giay)**, reconcile moi tick trong
     `updatePositionInfo()`, persist `run/legacy_symbols.csv`, log `[LEGACY] managed N: ...`.
     Co C3 chi ap cho SO GIAY: `LiveProfileC3.armRateFor/ratchetDeadzoneMultFor/timeStopApplies`
     deu nhan `symbol`. So giay khong mo entry tren symbol legacy (`[SHADOW] skip-LEGACY`) va
     legacy KHONG chiem slot top-K cua so giay.
   - Nhanh giay **khong dung Redis queue cua bot** (co `LIVE_C3_QUEUE`, mac dinh TAT) va khong ghi
     vao `BudgetManager` (von giay = `PAPER_EQUITY` + PnL giay).
   - Goi: `/home/ubuntu/deploy_242_l3/` (`sim.jar` + `s1_c3/` + `env.sh.new` + `deploy.sh` +
     `verify.sh` + `rollback.sh` + `README_DEPLOY.md`). **Agent KHONG SSH 242** — user tu deploy.
   - Cong hoi quy: `mvn -o test` **97/97 PASS** (82 cu + 15 moi), `check_cfg_gateway.sh` OK.
   - Keo log ve doi chung: `tools/pull_242_shadow.sh` (Oracle) — **cron chua bat**, doi deploy.


10b. **GATE ENTRY = MOT class `tradecore/EntryGate`, MOT knob, dung chung sim + live**
    (`docs/experiment/L7_LEAN_GATE.md`, 2026-09-11. Goi `/home/ubuntu/deploy_242_l7/` san, **242 CHUA DEPLOY**.)
    - `thr = SIM_MIN_MOMENTUM_15M * max(0.26787, symbolPred / 0.15 * 1.28760)`; PASS `<=> !(p15 < thr)`.
      Ba he so la `static final` — **het knob**; gate chi con doc `SIM_MIN_MOMENTUM_15M`
      (=> `conf/env.sh` 242 **khong phai doi**).
    - 🔴 **KHONG duoc "rut gon" thanh `p15 >= K*symbolPred`** (`K=0.0686720`): floor CO bind that
      1 lan/48 thang (2024-08-05 13:30 GMT+7, `symbolPred=0.024885`) va nhan `float` khong ket hop
      (lech ULP). Do o `docs/audit/LEAN_GATE_AUDIT.md` muc 3. **KHONG doi thu tu phep nhan.**
    - Sim va live moi ben DUNG MOT call-site (`Simulator...createOrder`,
      `DetectEntry...createOrderBuyRequest`) — ca hai goi `AIRejectFilter.entryGate`.
      Lich su: hai ban sao da troi khoi nhau 3 tuan (`311bb29`) => lech 95.62% slot entry.
    - Cong parity bat buoc khi cham vao gate: `printDone.csv` cua `X1_C3_FULL` phai
      `md5 = 2478e90d4e6147bf4cc64f75967ef47d` (bo header `e13bc39e625b8d2ceebb7b9194f7f4f0`),
      `b:111428`, 2,266 lenh. Chay: `bash /home/ubuntu/l7run.sh`.
    - **Con lai, co y giu**: gene `AI_DYNAMIC_MIN`/`AI_DYNAMIC_MULTIPLIER` trong HPO tu L7
      **khong con tac dong len gate** (da ghi canh bao tai `Configs.java`). Go khoi gene vector = L8.

11. **L4 — `build_map` chay LIVE, shadow thanh C3 dung nghia o tang ENTRY**
    (`docs/experiment/L4_LIVE_BUILDMAP.md`, 2026-09-07). **242 van CHUA DEPLOY.**
    - 🔴 **QUY UOC PHAI THUOC** (sai chieu la dao nguoc selector):
      `symbolPred = 1 − P(win)` (`WfoDataset.buildFundingFromWfFiles:248` `// DAO DAU`);
      `build_map` gan cho coin **rank k theo S1** (k=1 = `score` THAP nhat = tot nhat) gia tri
      `P(win)` **LON thu k** cua tick => `symbolPred` **THAP thu k** => sim lay K phan tu dau
      cua mang sort TANG. Ca hai lan rank deu `method="first"`, **the pha theo THU TU DONG**.
      Kiem 3 duong doc lap: code; spearman per-tick `score` vs `p0(predwf_map_s1a2_x1)` =
      **−1.000000 chinh xac**; edge8 chon `p0` CAO = **+21.5%** vs chon `p0` THAP = **−4.2%**.
    - Lop moi: `tradecore/selector/LiveBuildMap.java` (thuan tinh toan) +
      `Net015ValueLive.java`. Diem noi: `DetectEntrySignal2TradeNormal.buildValueMap(...)`.
      🟢 **Khong tinh them mot feature nao** — `net015` an CUNG mang `float[45]` da nap cho
      `Funding_Classifier_Final.onnx`.
    - 🔒 `LATEST_SEL_MAPPRED` (so GIAY) **tach han** `LATEST_SEL_PNOPUMP` (duong THAT/legacy,
      `BinanceOrderTradingManager:485`) — doi truc do la doi luat dong tien that.
    - Cong REPLAY 3 ngay DEV (2025-11-03/11-17/12-08, 150,084 dong, 288 tick):
      port `build_map` tai lap bins da deploy **BYTE-EXACT (`max|d| = 0`)**; end-to-end
      spearman **1.000000** (per-tick min 1.000000), top-8 **100.0000%**, multiset
      `max|d| = 4.768e-07`. `net015` ONNX trong Java vs bins: spearman 1.000000, `max|d|` 4.768e-07.
    - 🔴 **CHUA DO DUOC: duong FEATURE 45 real-time vs Tool1 offline.** `oi_feat_*` tren 242 chi
      giu 2 thang => khong tai lap duoc 2025-11/12; cua so co ca hai nguon la 2026-08 = holdout.
      Chi moi cong THU TU (tinh) la PASS. **Day la rui ro lon nhat con lai o tang entry.**
    - ⚠️ **Dai `symbolPred` co HAI muc, dung lan**: vu tru moi tick p50 ~**0.47** (= 1−0.4642,
      dung `p_mean` net015); **muc LENH** (top-8) p10/50/90 = **0.2555/0.2974/0.3373**
      (tham chieu `C4_parity` 48 thang: 0.1424/0.2173/0.3223). Log `[MAP]` in dai VU TRU,
      nen `verify.sh` gate `p50 in [0.20, 0.70]` (do tren 220 tick: 0.2262..0.6093).
    - `DCA_GRID_WEIGHTS=1,0,0,0` + `TIER_FLAT=1` **DA BAT** trong `env.sh.new` (user duyet
      2026-09-07) — tham so SO GIAY, chi vao duong sizing entry.
12. **THUOC CHON MODEL = MODEL RULER (Tang A); SIM = kiem HE THONG (Tang B)** — chot 2026-09-25
    (`docs/prereg/PREREG_MODEL_RULER.md` **`cc22253`** · `docs/result/RESULT_MODEL_RULER.md` ·
    tool `research/analysis/model_ruler.py`).
    - Cau hoi *"tap feature moi co tot hon khong"* **PHAI** tra loi bang **model ruler**
      (`rank-IC` / `|rank-IC|` / `lift@8` (K=8) / `precision@8` / `AUC` / `pairwise P(s_A>s_B|y_A>y_B)` /
      decile / gross-net theo chi phi `0,008`, tat ca OFFLINE, **khong train, khong sim**) —
      **KHONG** bang equity/PnL/`n` (equity da la luat 3).
    - **SIM CHI chay cho model DA QUA Tang A**, VA **phai RE-CALIBRATE gate theo scale score cua model
      moi** (gate dung **multiset `P(win)`** cua tick ⇒ doi model ⇒ doi `dyn_thr` ⇒ doi so lenh;
      bang chung: `docs/experiment/G5_VALUE_LABELS.md`). So sim giua 2 model khac scale score ma
      khong re-calibrate = do CALIBRATION, **khong** do skill.
    - Thao tac: `python3 research/analysis/model_ruler.py ruler --name <TAG> (--bins <dir> | --ticks <parquet>)`
      · `... validate [--reuse]` (6 arm + 2 doi chung + tu-kiem T1 shuffle / T2 bat bien rank).
    - Trai nghiem do duoc: **thuoc nay bat bien** voi moi bien doi TANG NGHIEM NGAT cua score
      (`max|Δ| = 0,00e+00`) ⇒ no **khong** bi "thuong" vi hop hien trang.

## 1. Kenh truy cap Oracle

Repo o box Oracle, chi toi duoc qua desktop bridge cua may Windows.
Load: `ToolSearch select:mcp__remote-devices__plugin_desktop-commander_desktop-commander__start_process,...__write_file,...__read_file`

```
1. write_file  -> C:\Users\pc\AppData\Local\Temp\<PREFIX>_<n>.sh   (prefix rieng moi agent)
2. start_process timeout_ms 25000:
   powershell.exe -NoProfile -Command "Start-Process powershell.exe -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\Users\pc\AppData\Local\Temp\runsh.ps1','-Sh','<sh>','-Out','<log>' -WindowStyle Hidden; 'launched'"
3. read_file <log>   (ENOENT = chua xong, cho roi doc lai)
```
BAT BUOC `Start-Process` roi poll. Goi runsh.ps1 truc tiep => chet o timeout 60s
cua device bridge. `runsh.ps1` tu strip BOM + CRLF (2 cai bay cu).

Duong dan: repo `/home/ubuntu/src/BinanceFuturesJava` (branch `module`),
sim runs `/home/ubuntu/java/devrun/<TAG>/`, jar `$R/target/binance-java-sdk-1.2.4.jar`.

## 2. Chay mot sim run

```bash
R=/home/ubuntu/src/BinanceFuturesJava; JAR=$R/target/binance-java-sdk-1.2.4.jar
B=/home/ubuntu/java/devrun; PROF=$R/profiles/c2b_min.properties; DS=/home/ubuntu/wfo_ds_<x>
# build dataset 1 LAN (dung chung cho N sim neu chi doi param exit/gate/sizing)
cd $B && cp -f $R/configs/sim_dev.properties $B/config.properties
env TRADING_PROFILE=$PROF WFO_SET_PRED=ai_pred_market_gate_wfo WFO_SEL_HORIZON_IDX=0 \
  WFO_CODE_SHA=$(cd $R && git rev-parse --short HEAD) java -Duser.timezone=Asia/Ho_Chi_Minh \
  -Xmx14g -cp $JAR com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset $DS > logs/build.out 2>&1
# moi run
D=$B/<TAG>; mkdir -p $D/storage $D/logs; cd $D
cp -f $R/configs/sim_dev.properties config.properties; rm -f storage/*
env WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20240630 \
  EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE=$PROF \
  java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
  com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
```

### 8 cai bay bat buoc biet
1. **`rc=1` KHONG phai fail.** Sim in rc=1 du hoan tat. Tieu chi: log co `done:` + `b:`
   va `storage/printDone.csv` co dong.
2. **Da co `TRADING_PROFILE` thi KHONG duoc dat bien env tien to `SIM_`** (tru
   `INFRA_KEYS`) — `Cfg` fail-fast `exit 2`. Muon doi param => COPY profile, sua 1 dong.
3. `WFO_FUNDING_PRED_DIR` dat CA env VA profile => exit 2. Chi de trong profile.
   Thieu bins => `ExportWfoDataset` THROW. Kiem `grep -q '^WFO_FUNDING_PRED_DIR=' $PROF`.
4. Chi **1 slot JVM**. `pgrep java` phai rong. Chay TUAN TU. `run_c2b_dev.sh` tu exit 3.
5. **Dia 92% (con ~16G)**. `rm -rf $DS` sau khi xong. `df -h /` truoc khi build;
   duoi 5G free thi DUNG.
6. Neo: **60390** voi `TICKER_SOURCE=aerospike`; **60395** voi `TICKER_SOURCE=file`
   (lech 1 lenh/970, FTT 2022-11-09). So sanh Oracle<->Kaggle chi tin toi ~0.01%.
7. **Device: CPU o dau cung duoc; GPU chi de QUET.** Do lai 2026-09-05, 3 moi truong
   x 3 seed, cung mot file hash khop (`docs/ops/BENCH_DEVICE.md`).
   - **Kaggle CPU == Oracle CPU byte-for-byte**: per-tick `|dIC|` = **0.0 chinh xac**,
     `ic_sha256` trung ca 3 seed, cay dau tien trung sha — du khac arch (x86 vs aarch64),
     python (3.12 vs 3.10), numpy (2.0.2 vs 2.2.6). => **train S1 tren Kaggle CPU vo dieu
     kien**. So cu `0.17040 vs 0.1723` la lech DU LIEU/pipeline, KHONG phai lech may;
     khong duoc dung no de khoa vao Oracle.
   - **GPU lech that, nhung ly do khac lenh cam cu**: per-tick lech ngang nhieu seed
     (x1.07-x1.20), `edge5` cung nam trong nhieu seed (x1.21); cai lech that la
     `|d mean rank-IC|` = **0.00448 ~ x3.7** nen seed cua CPU, va GPU **tu no nhieu gap
     4.8 lan** CPU. Nguyen nhan: `Cover` lech 31/31 node (RNG `subsample`/`colsample`
     khac) + `Split` lech 11/31 (quantile sketch `hist` khac). Ghim seed khong cuu duoc.
   - **`nthread` khong anh huong**: `n_jobs=1` vs `4` cho ket qua giong het (tree1 sha
     trung, `dIC` = 0.0).
   - **Cong `spearman >= 0.999` DA BO.** Doi seed tren cung mot may cho spearman
     **0.9817** (774,270 dong) — cong do loai ca viec re-seed chinh mo hinh. Chinh no
     tao 2 false positive, khong phai GPU. Thay bang: **hieu ung phai vuot CI multi-seed
     (>= 3 seed) do trong cung moi truong**; chua co CI thi chua duoc ket luan.
   - **Van giu nguyen**: khong ghep cap so tu 2 moi truong trong mot so sanh; GPU thi CA
     phep so phai tren GPU; parity/byte-identity phai chay tren dung device sinh ra neo;
     Java sim o lai Oracle (data host + neo 60390).
8. `TIME_RUN` (ngay bat dau DEV) o `configs/sim_dev.properties:39`, KHONG co
   `SIM_START_DATE`, va `TIME_RUN` khong trong whitelist `Cfg.java:50` => chi doi
   qua file config.

### Chay SONG SONG tren Kaggle (thoat rang buoc 1 slot JVM Oracle)

Oracle chi co **1 slot JVM** (bay #4) => moi sim phai xep hang. Kaggle CPU chay duoc
**5 kernel cung luc**, moi kernel 4 core / 31GB. Do that 2026-09-05: Kaggle+file ra
`b:60395` va `printDone.csv` **giong Oracle+file tung byte** (`md5 910f1aa6...`);
`x96`/`x120` con giong ca ban Oracle+aerospike (`docs/result/E1_EXIT_RESULT.md`) tung byte.

```python
import sys; sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava")
from tools import kaggle_sim as ks
ks.free_slots()                                                    # DUNG neu = 0
r = ks.submit("x96", "c2b_min", {"SIM_LOSER_TIME_STOP_HOURS": 96}, code_sha="bd20e42")
ks.wait([r]); out = ks.fetch("x96")      # out["result"]["equity_final"], out["print_done"]
```

**Bay rieng cua duong Kaggle (them vao 8 bay o tren):**
9. **Neo Kaggle la 60395**, khong phai 60390 — Kaggle bat buoc `TICKER_SOURCE=file`.
10. **Kernel phai `enable_internet=True`**: `SimpleSymbolMapper` van doc Aerospike Oracle.
    Mapper rong => ket qua lech am tham; `kaggle_sim` da guard (`exit 2` neu < 800 symbol).
11. **`PROFILE_HASH` Kaggle KHAC Oracle** (duong `WFO_FUNDING_PRED_DIR` khac) — so parity
    bang md5 `printDone.csv`, KHONG bang `PROFILE_HASH`.
12. Doi jar/profile => phai `dataset_create_version` lai `chuyendinh/sim-c2b-bundle`.

Chi tiet + kiem ke dau vao + wall-clock: **`docs/runbooks/KAGGLE_SIM.md`**.

### Cham diem
```bash
python3 $R/research/analysis/qret_ladder.py C2b <TAG>...   # quy/nam/TSloss/margin/medP
python3 /home/ubuntu/java/fsrun/qret.py C2b <TAG>...        # + underwater, quy>=5%
bash    /home/ubuntu/java/fsrun/ev.sh   C2b <TAG>...        # phan bo exit
md5sum $B/C2b/storage/printDone.csv $B/<TAG>/storage/printDone.csv   # parity
java -cp $JAR com.binance.chuyennd.tradecore.DumpConfig     # PROFILE_HASH + derived.*
```

## 3. Baseline hien tai

> **C3 = HAI cau kien, ca hai DEU TAI LAP DUOC** (2026-09-06, `docs/experiment/G4_RECIPE_C4.md`):
> **(1) S1 order** — `pred_s1a2x1.parquet` (sha256 `2618fe1a…`), 4 cong byte-identical o
> `X1_EXTEND` muc 2. **(2) net015 value** — bins `claudedata/predwf_G015x26/`:
> tai SINH byte-tuong-duong bang `research/pipeline/g015x26_train.py` (predict tu 18 model goc,
> spearman 1.0), va **TRAIN LAI tu dau** bang `research/pipeline/g015_net_train.py`
> (recipe day du: `docs/experiment/G015_RECIPE.md`; cong GPU-vs-GPU spearman **0.985997** > nen nhieu
> between-seed 0.984931). Nhan THAT = `retEnd_4h > 0.015` (`LABEL_MODE=net`, base 0.1849),
> **KHONG** phai `maxFav_4h >= 0.06` — `predwf_G015_v2` la model KHAC NHAN.
> `c4_build_map.py` + bins x26 -> `predwf_map_s1a2_x1` **byte-identical 16/16**;
> sim ra dung `X1_C3` (md5 `d39da294…`, 2,058 lenh, 98,523).
>
> 🔴 **Nhung `Funding_Classifier_Final.onnx` tren duong LIVE KHONG phai net015**: cham cung
> 2,134,469 dong OOS 2024Q1, spearman vs net015 = **0.854** con vs `G015_v2` (nhan maxFav) =
> **0.961**; hieu chuan live `p_mean 0.2268` vs net015 **0.4642**. Model live thuoc ho `maxFav`.
> Muon shadow = C3 that thi phai thay bang ONNX cua net015
> (`/home/ubuntu/g3x26/g015x26_f15_cut20251001.onnx`, sha256 `7921ceaf24…`).
>
> 🔴 **Bins SELECTOR khong tai lap BYTE duoc** du bins gia tri tai lap toi 1 ULP:
> `sort_values("ts")` (quicksort khong on dinh) + `rank(method="first")` trong `build_map.py`
> pha the theo THU TU DONG => sai so `1.19e-07` bi khuech dai thanh **0.3715**. Sim van gan
> nhu khong doi (trung khoa `(sym,start)` 99.90%, `win%`/`TSloss%`/`mP|SL` bang 0 tuyet doi,
> chi `mean(margin)` +0.18%) — nhung md5 `printDone` KHAC. `docs/experiment/G4_RECIPE_C4.md` muc 4.

`C3` = equity 35,000 -> **68,278**, CAGR **30.76%**, maxDD **-13.31%**, **961 lenh**,
underwater **96 ngay**. Profile **`profiles/c3_min.properties`** (16 key cua `c2b_min` +
3 co `SIM_FIX_B1/B2/B3=true`), md5 printDone `38be0cb3195984e1000e61d9cdef54da`.
Chi tiet: **`docs/experiment/C3_BASELINE.md`**, pre-reg `docs/prereg/PREREG_C3.md`.

### Tren cua so DEV MOI 48 thang (X1, 2026-09-05) — `docs/experiment/X1_EXTEND.md`

`X1_C3` (= `C3` chay toi 2025-12-31, bins `predwf_map_s1a2_x1` 16 fold, profile
`profiles/x1_c3.properties`): **2,058 lenh**, win **85.33%**, TSloss **14.87%**,
`mean(profit|SL)` **-21.85**, equity **98,523**, CAGR **29.58%**, maxDD **-13.31%**,
UW **302 ngay**. md5 printDone `d39da2940dfd815f60772f70517750bf`.
**Cong parity noi bo PASS**: cat toi 2024-06-30 ra **dung 961 dong IDENTICAL** `C3_BASE`.

`X1_C3_FULL` (profile `profiles/x1_c3_full.properties`): 2,266 lenh, equity 111,428,
CAGR 33.63%, maxDD -12.46%, UW 227. md5 `2478e90d4e6147bf4cc64f75967ef47d`.
**KHONG duoc nhan lam baseline** — chi 1/5 rate chat luong ngoai CI, va FAIL rang buoc cung.

🔴 **`UW <= 120 ngay` KHONG con la nguong dat duoc** tren 48 thang: **ca hai** arm FAIL o
2024 (121) va 2025 (302 / 227). Nguong nay duoc dat khi chi co 30 thang (UW max 96).
Can user quyet lai — **khong duoc tu ha nguong.**

Chay lai: `research/pipeline/x1/run_x1.sh` (bins, 4 cong byte-identical) roi
`research/pipeline/x1/run_x1_sim.sh` (dataset + 2 arm, Oracle + `TICKER_SOURCE=file`).
Cham diem: `research/analysis/x1_rates.py X1_C3 X1_C3_FULL`.

**`C2b` = 60,390 chi con la SO LICH SU.** No sinh tu engine co 3 bug (B1/B2/B3).
KHONG ghep cap so cu (E1/W1/T1/T2/T2b) voi so moi trong cung mot so sanh.
Muon tai lap C2b: `profiles/c3_regress.properties` (3 co `false`) -> ra
**byte-identical** 60395/970/`910f1aa6...` tren duong `file`.

> 🔴 **G5 (2026-09-07, `docs/experiment/G5_VALUE_LABELS.md`): value model KHONG phai bo chon coin.**
> Chay 10 sim 48 thang voi **hieu chuan CO DINH** (multiset `P(win)` cua x26 trong tung tick,
> giu nguyen o moi arm) va chi doi THU TU: `G5_x26_order` (de chinh x26 xep hang, bo S1) thua
> `G5_parity_S1` **4/5 rate chat luong ngoai CI** (`win%` −3.64, `TSloss%` +4.19), FAIL rang buoc
> cung 2022 + 2025, equity 76,700 vs **98,523**. 7 nhan ung vien khac (`net` 0.015/0.02/0.03 x
> {4h,72h}, `maxFav06` x {4h,72h}) **deu thua**: 8/8 arm co >= 1 rate xau ngoai CI, **0 arm co
> rate nao TOT ngoai CI**, 8/8 FAIL rang buoc cung >= 2 nam (parity PASS 4/4).
> => **Uu the cua C3 nam o THU TU cua S1.** Value model chi la bo sinh nguong gate theo tick.
> Ho `72h` la huong CAM: `net*_72h` bien 2025 thanh nam AM 20-25%, `maxDD` −25..−31%.
> Neu bat buoc train value model moi: `maxFav_4h >= 0.06` (rank-IC per-tick +0.164, cao nhat)
> **VA phai quantile-map ve multiset cua bins dang deploy** — tha nguyen phan phoi cua no vao
> gate = admit **x4.56** candidate-minute (`x19.4` adm_top8) = tai lap tham hoa `C4_maxfav30`.

Kien truc: **S1** (9 feature, XGBRanker rank:ndcg, label `rel5` = quintile trong tick
cua `g1lite - median`) quyet dinh THU TU coin; **G015x26 = net015** (45 feature, XGBClassifier,
label **`retEnd_4h > 0.015`** — DINH CHINH 2026-09-06, truoc day ghi nham `maxFav_4h >= 0.06`)
quyet dinh GIA TRI gate. `build_map.py` giu nguyen multiset
P(win) cua G015x26 trong moi tick, chi gan lai theo rank cua S1 (`changed` 4.9%).

Exit: arm +7% roi trailing `giveback = min(peak*0.5, cap)`.
**Ban le NGUOC voi truc giac:** `symbolPred (=pNoPump) <= 0.29` -> **STRONG cap 0.08**
(nha nhieu hon, nuoi lau hon); `> 0.29` hoac null -> **WEAK cap 0.03**.
Do thuc: **83.8% lenh di nhanh STRONG** tren 48 thang (`X1_C3`); 71.5% la so cu cua `C3` (30 thang).

🔴 **DAY KHONG PHAI "trailing theo selector" — do lai o X3 (`docs/experiment/X3_RANKCAP_SL50.md` muc 3):**
`symbolPred` la gia tri thang do **G015x26**; `build_map.py` giu NGUYEN multiset P(win) cua G015
trong tung tick, chi gan lai coin nao nhan gia tri nao theo thu hang S1. Ban le 0.29 la **TUYET DOI,
nam NGOAI tick**, ma cac gia tri trong MOT tick lai bam rat sat nhau (vd 0.3547 / 0.3586 / 0.3613).
Hau qua do duoc: `%STRONG` theo rank chi trai tu **80.9% (rank 6) den 87.7% (rank 1)** — spread
**6.8pp**, tuc ban le gan nhu **TRUC GIAO voi rank**. No quyet dinh theo **muc lac quan cua G015 tai
tick do**: tick nong ca 8 coin STRONG, tick lanh ca 8 WEAK.
Key `TS_CAP_STRONG_RANK` (mac dinh 0 = TAT) cho phep doi sang cap theo RANK — **da thu 2/4/6, NULL**.
⚠️ Truoc fix B1 (moi so <= `af6181e`) nhanh STRONG **CHUA BAO GIO chay** — 100% WEAK.
**Khong co stop-loss truoc arm** o baseline. `STOP_LOSS_DONE` = **time-stop 168h**, KHONG phai SL.
(`SIM_PRE_ARM_SL` ton tai tu X2 nhung mac dinh 0 = TAT; −0.20/−0.30/−0.50 deu NULL.)

Sizing: `margin = equity x F_BASE x throttle x DCA_GRID_SCALE x w[i]/total`, voi
`equity = balanceCurrent + unProfit` (**COMPOUND**, tu fix B3) va
`throttle = 1 - marginRunning/(equity x U_MAX)`. Tran margin/leg = **4.5% equity**
(= `F_BASE 0.03 x SCALE 1.5`), khong phai hang so 1575.
⚠️ `maxDD` in trong log sim (`unProfitMin/35000`) MAT Y NGHIA duoi compound — luon do
maxDD/UW tu **chuoi equity** (`qret.py`).

## 4. Ket luan da chot — DUNG lam lai

- 🔴 **BA BUG DA SUA (C3, 2026-09-05)** — `docs/experiment/C3_BASELINE.md`. Cong hoi quy PASS
  byte-identical. **Toan bo phan tang equity la B3 (compound), KHONG phai B1**:
  B1 mot minh lam equity GIAM 60,395 -> 59,722 va **0/7 rate ngoai CI**.
  B3 cho hieu **bang 0 TUYET DOI o moi rate muc lenh**, chi `mean(margin)` doi
  (+424, CI [+287,+562]) => compound di qua DUNG MOT kenh (thang do), khong ro ri.
- **B1 doi HINH DANG phan bo winner, khong doi trung binh**: than tut ~1pp
  (p10 4.46->3.50, p25 4.99->4.00, med 6.00->5.00), duoi phai len (p90 11.00->12.06).
  So hoc: `exit = peak - min(peak*0.5, cap)`; voi `peak` trong 6%..16% thi STRONG chot
  THAP hon WEAK dung 5pp. **Danh doi median-doi-duoi, khong phai cai tien.**
- **`SIM_TS_MAX_GAP` va `SIM_TS_PNOPUMP_WEAK_THR` GIO DA SONG** (truoc la key chet).
  `W1` truc A va C la **vung trang**, quet lai duoc. Ban le 0.29 nam giua dai van hanh
  (71.5% STRONG / 28.5% WEAK).
- **Gate `SIM_MIN_MOMENTUM_15M=0.008` KHONG bo qua chat** (do lai tren engine DA SUA):
  noi ra 0.006 mua them 631 lenh nhung 5/5 rate CHAT LUONG deu trong CI, va FAIL 3/4
  rang buoc cung (maxDD -20.75, UW 133, quy -8.3). Hai rate vuot CI (`n`, `mean(margin)`)
  la hai mat cua cung mot su kien co hoc, khong phai bang chung chat luong.
- **`DCA_GRID_SCALE` bu dung sau B2 la 19.5** (`= 1.5 x 13`), KHONG phai 253.5
  (`= 1.5 x 169`, bu cho chinh cai bug). Hieu chuan `C3_FULL` PASS lan dau (+2.19%).
- ⚠️ **Moi ket luan cua E1/W1/T1/T2/T2b deu sinh tu engine co 3 bug.** Phan lien quan
  **trailing** (E1, W1 A/B/C, T2b DCA) can do lai. Phan lien quan selector/gate/label
  (T1, T2, F1-F4, G1) it kha nang doi nhung **chua kiem chung**.

- **Selector ladder CHUA THIET LAP.** 78% uu the C2b−C2_g015 nam trong 2022; rebase
  2023-01 thi C2b THUA 5.5pp. medP giong het (5.50 vs 5.49). Khac biet la co dac
  co hoc: it lenh hon 39%, margin/trade lon 1.85x. Xem `docs/analysis/SELECTOR_LADDER_Q.md`.
  => **KHONG lam them selector variant / rank-IC / feature selection.**
- **Gate la load-bearing**: `v3_g1_nomom` = 10,305 voi 14,007 lenh. Giu.
- **Exit G1 -> C2 la cai tien that**: medP 3.5-4.0 -> 5.5-6.0 o 10/10 quy.
- **Time-stop 168h la kenh mat tien lon nhat**, va `mean(profit|SL_DONE)` giam don
  dieu khi rut ngan: 168h −18.90% / 120h −16.15% / 96h −13.99% / 72h −12.31%.
  Xem `docs/result/E1_EXIT_RESULT.md`.
- 🔴 **X2 (48 thang, 2026-09-05): CA HAI truc exit deu NULL — `docs/experiment/X2_EXIT48.md`.**
  Co che cua `E1` TAI LAP DUOC tren engine da sua va tren 48 thang (`mP|SL` −21.85 ->
  −18.70 -> −16.73 -> **−14.58**, `p10 loser` −46.89 -> **−30.86**, `mP|SM` khong doi),
  **nhung `win%` giam NGOAI CI o ca 5 muc** va **0/5 muc PASS rang buoc cung**.
  **Cat lo som KHONG giam underwater, no DOI CHO underwater**: `T72` doi 113 ngay UW cua
  2025 (302 -> 189) lay 95 ngay UW cua 2022 (64 -> **159**). Do la cai `E1` muc 5.3 thay
  ma khong tach duoc theo nam. **DUNG chay lai truc time-stop.**
- 🔴 **PRE-ARM HARD SL DA CO TRONG ENGINE** (`SIM_PRE_ARM_SL`, 0 = tat = mac dinh,
  `tradecore/PreArmSlUtils.java`, 5 unit test). Key cu `SIM_HARD_SL_PCT` da chet; day la ban
  VIET LAI: nguong do tren `firstEntryPrice` (bat bien qua DCA), chi khi `priceSL==null`, gia
  dong `min(stopLevel, min(open,close))`. Cong hoi quy: key tat -> `X1_C3` byte-identical.
  **Ket qua do duoc: mot nguong SL TINH la cong cu SAI.** No **dun** phan bo lenh thua thanh
  mot cot tai dung muc cat (`medloser` = −20.00 o `S20`, −30.00 o `S30`, vs −18.11 parity):
  duoi dai duoc keo len (`p10 loser` −46.89 -> −21.55) nhung THAN bi keo xuong, nen `mP|SL`
  cua muc −30% **xau hon parity** (−22.78 vs −21.85). `S20` con lam **2025 thanh NAM AM**
  (−1.91%). **KHONG dat `SIM_PRE_ARM_SL` khac 0 trong bat ky baseline nao.**
- **Chi phi that cua SL do duoc** (ghep `(sym,start)` voi parity): ty le lenh bi cat ma parity
  ket thuc `STOP_MARKET_DONE` = 10.1% (`T120`) / 16.6% (`T96`) / 22.9% (`T72`) / 10.0% (`S30`),
  tang don dieu theo do cat ngan. `S20` KHONG do duoc (ty le ghep 77.1% < 80%).
- ⚠️ **`tools/kaggle_sim.py` CHUA chay duoc cua so 48 thang**: `TICKER_DS` thieu
  `wfo-ticker-2024h2` / `-2025h1` / `-2025h2` (ba dataset nay **DA co** tren Kaggle) va guard
  `len(tk) < 912` phai thanh 1,461. X1 va X2 deu phai chay tuan tu tren Oracle vi cho nay.
- 🔴 **X3 (48 thang, 2026-09-06): CA HAI viec NULL — `docs/experiment/X3_RANKCAP_SL50.md`.**
  - **Trailing cap theo RANK selector (`TS_CAP_STRONG_RANK` = 2/4/6): NULL, va ly do la CO HOC.**
    Do tren `PARITY`: `mean(profit|SM)` cua **rank 1-2 = 6.801** con **rank 7-8 = 7.065** — **KHONG
    co gradient chat luong theo rank**, rank sau con nhinh hon. Nha cap rong 8% cho rank nong la dat
    cuoc vao mot truc khong mang thong tin. `X3_R6` ra **0/8 rate ngoai CI**, `n` (2,058) va `win%`
    (85.33) **giong het** PARITY. `X3_R2` chi doi HINH DANG winner (than +0.5pp, p90 −1.27pp) — dung
    phep doi median-doi-duoi cua B1, chay NGUOC chieu. **`S1` xep hang coin de VAO lenh, no KHONG noi
    gi ve pha SAU-ARM.** Hai cau hoi khac nhau — dung tai dung selector cho trailing.
  - **`SIM_PRE_ARM_SL=-0.50`: NULL.** `p10loser` **XAU DI** −46.89 -> −50.07 (co hoc: parity p10loser
    nam TREN muc cat, nen cat dan phan vi do **hoi tu ve −50 tu ca hai phia**). Cai no mua duoc that
    su: `minloser` −94.64 -> **−71.44** va **chi phi cat oan 1.8%** (re nhat da do, vs 10.0% cua `S30`,
    22.9% cua `T72`). **DUNG them muc thu tu cho truc S** — X2 (−20/−30) + X3 (−50) da dong o ba do sau.
  - 🔴 **R4 (underwater) o do phan giai nay chu yeu la NHIEU.** `X3_R6` khong phan biet duoc voi PARITY
    o MOI rate muc lenh, nhung `UW 2022` **64 -> 159 ngay** va vo tran R4. Mot rang buoc bi nhieu
    single-realization lam nhay 95 ngay thi khong con do duoc chat luong. Phai dua len user.
- Nhom bi time-stop chet vi **khong bao gio chay**: 66.6% chua tung vuot +3%,
  maxFav median 1.83% dat o gio thu 4. Ha nguong arm KHONG cuu duoc. `docs/experiment/E0_EXIT_CF.md`.
- **DCA cua `C3_FULL` KHONG phai "an FTX mot lan"** (X1, 48 thang): leg 2+ duong o
  **2022** (20 leg, +2,758) VA **2025** (32 leg, +4,813), am nhe 2024 (2 leg, -164),
  khong co leg nao 2023. Gia thuyet regime-dependent da bi bac bo. Cai chan `C3_FULL` bay
  gio la **chung co muc rate con mong** (1/5) va rang buoc cung UW — ma `C3` cung vi pham.
- **2025 khong lam xau `TSloss%`/`win%`** (15.05 / 84.69, y het 4 nam). Cai xau di la
  **do sau lenh thua**: `mean(profit|SL)` -15.52 (2024) -> **-28.94** (2025), moi phan vi
  sau gap ~2 lan. Universe x2.2 (265 -> 591 coin), gate mo x5 (2,258 -> 11,653 tick 15m),
  nhanh trailing STRONG 91.8% -> **95.4%**, median hold 13.8h -> **9.0h**.
  S1 selector **manh len** o 2025 (`edge5` +8.52% -> **+19.34%**). Xem `X1_EXTEND` muc 10.
- **Aerospike Oracle da du 2021** (`test/funding_data` 88-136 coin/thang). Khong
  can copy set nao ve. `docs/audit/D1_DATA_AUDIT.md`.
- **Sizing (F_BASE / U_MAX / DCA_GRID_SCALE) KHONG do duoc tren DEV.** Sizing khong
  doi chat luong tung lenh, chi doi thang do => tieu chi duy nhat la maxDD/underwater,
  deu la single-realization n_eff nho. Day la nut RISK PREFERENCE user dat, khong
  phai bai toan toi uu. **DUNG dot sim run vao day.**

- 🔴 **L1 (2026-09-06): GIA TRI cua `symbolPred` KHONG load-bearing** — `docs/experiment/L1_SHADOW_C3.md`
  muc 4. Thay no bang HANG SO o **ca hai cuc** (`SIM_TS_PNOPUMP_WEAK_THR` = 1.0 -> 100% STRONG,
  = 0.0 -> 100% WEAK) tren 48 thang: **0/5 rate chat luong ngoai CI** o CA HAI arm. Lech equity
  lon nhat +4.78% (CAGR +1.52pp) — trong nhieu `sd(dCAGR)` 2.57pp. Cong voi `X3`
  (`TS_CAP_STRONG_RANK` NULL), **truc "chon cap trailing bang cai gi" da dong o ca ba huong**
  (gia tri G015, rank S1, hang so). Dung quet lai.
  He qua thuc dung: shadow duoc phep dung `symbolPred` cua model 45-feature LIVE thay
  `predwf_G015x26` (khac hieu chuan 0.05-0.12 vs ~0.35) ma khong lam hong phep do.
  🔴 **DINH CHINH 2026-09-06 (`docs/experiment/G4_RECIPE_C4.md` muc 6): cau tren CHI DUNG CHO TANG
  TRAILING.** O tang **GATE** thi gia tri **CO** load-bearing va rat manh: `C4_maxfav30`
  (bins nhan `maxFav`, `symbolPred` p50 0.0893 vs 0.2420) admit **x5.05** (4,857 vs 961 lenh),
  `win%` −8.04pp, `TSloss%` +8.44pp — **3/5 rate ngoai CI**, FAIL rang buoc cung moi nam,
  equity 28,384 (**am**), va chi **13.11%** lenh cua parity con ton tai. Co che:
  `dyn_thr` tang don dieu theo `score` => phan phoi thap hon => nguong thap hon => admit nhieu
  hon. Vi model live thuoc ho `maxFav` (khong phai `net015`), **so lieu ADMISSION cua shadow
  khong so duoc voi C3**.
- ⚠️ **`n` KHONG bat bien duoi thay doi EXIT khi sizing la compound (sau B3).** Do duoc o L1:
  doi cap trailing -> doi thoi diem thoat -> doi `marginRunning` -> doi `throttle` ->
  vai tick sat tran von LAT quyet dinh admission. `n` 2,058 -> 2,056 / 2,077 (0.1% / 0.9%).
  Moi pre-reg do exit tu nay **khong duoc dat cong "n phai giong het"**.

- 🔴 **G5 (2026-09-07): TACH duoc HIEU CHUAN khoi THONG TIN — `docs/experiment/G5_VALUE_LABELS.md`.**
  Bang co hoc do TRUOC khi chay (pre-reg muc 1): `symbolPred = 1 − P(win)`
  (`WfoDataset.export` ghi `floatBits(1-P(win))`), `dyn_thr` KHONG co tran nen trong MOT tick
  "qua gate" ⟺ `p >= nguong_tick`; ma `predReturn15M` la dai luong THEO TICK => **so
  candidate-minute qua gate chi phu thuoc MULTISET `p` cua tick**. `c4_build_map.py` giu nguyen
  multiset do => **admission bat bien TUYET DOI**: do duoc `pass = 103,840` va `adm_top8 = 5,906`
  o **CA 8** ung vien va o parity, bang tung don vi. Day la cong kiem cau truc re nhat cho moi
  thi nghiem doi value model ve sau — chay bang `research/analysis/g5_proxy.py`, khong can sim.
- ⚠️ **`n` (so lenh THUC THI) KHONG bat bien du admission bat bien.** G5 do +37%..+64%
  (2,815..3,385 vs 2,058) trong khi so candidate-minute qua gate giong het. Nguyen nhan: coin
  nao duoc chon quyet dinh von bi chiem bao lau + slot + khong mo trung symbol.
  **Moi pre-reg doi THU TU khong duoc dat cong "n phai gan parity".**
- 🔴 **rank-IC per-tick lai mot lan nua KHONG du de ket luan** (lan 1: `T1_LABEL3` muc 3 diem 3).
  G5: truc nguong `net` 4h co rank-IC **tang don dieu** 0.144 → 0.150 → 0.159 (ca ba ngoai CI)
  nhung o sim thu tu **dao lon** (4/5 → 4/5 → 2/5 rate xau; equity 76,700 → 72,140 → 72,995).
  **Dung dung rank-IC lam tieu chi cuoi cho value model.**
- ⚠️ **Tran Kaggle GPU do duoc: 2 batch session cung luc** (`Maximum batch GPU session count of 2
  reached`). CPU van 5. Mot model 45-feature 16 fold = **~30 phut** GPU.

## 5. Leak / no ky thuat con mo
- ~~`predwf_G015x26` KHONG reproduce duoc~~ **DA GO 2026-09-06** — xem `docs/experiment/G3_X26_RECOVERY.md`.
  Tai lap duoc: 16/16 fold `spearman = 1.0`, `max|d| = 1.192e-07`. Export Tool1 2021 KHONG mat;
  18 model goc con o `claudedata/predwf_G015/`. Con thieu: source cua TRAINER ban 08-14
  (khong chan gi — tai sinh bang predict tu model da luu).
- `VisionMetricsClient.parseDay` con lo 5-phut forward. **KHONG rebuild OI truoc khi patch.**
- purge 72h < holding 168h => train/test overlap tren equity path.
- `Constants.diedSymbol` trong G015 f3/f4/f5 = danh sach delist hardcode (future info).
  Huong: lam NHE uu the C2b, khong phong dai.
- `f23 fundingPersistence` = proxy thoi gian.
- `SELECTOR_FEATURES` muc D dua tren claim da retract => coi la VOID.
- API key trong git history chua rotate. K=8 (sim) vs K=5 (live) chua dong.
- `configs/c2b.properties` co 5 key chet (`DISABLE_PREDICT_SYMBOL`,
  `HARD_STOP_LOSS_RATE`, `TIME_STOP_HOURS`, `TS_GAP_CONST`, `TS_MIN_GAP`) =>
  `CONFIG_STRICT=1` se STOP. `c2b_min` (16 key) va `c2c_round` (19) pass.
