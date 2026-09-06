# L2_PORT_C3 — cam C3 vao duong LIVE sau co `LIVE_PROFILE=c3_shadow` + instance shadow tren Oracle

Ngay 2026-09-06. Tiep noi `docs/L1_SHADOW_C3.md`. **242 CHI DOC** (chi doc 2 file model + config,
khong ghi mot byte nao). **Khong lenh Binance. Khong key trade. Khong push.**

---

## 0. RUI RO TRUOC — 7 dieu

1. 🔴 **Shadow KHONG PHAI C3.** Thu tu selector la S1 that (cong 1+2 dat), nhung **gia tri gate
   `symbolPred` van la `Funding_Classifier_Final.onnx`** chu khong phai `predwf_G015x26`. Hieu chuan
   khac han (live ~0.05-0.12 vs sim ~0.35) => ty le nhanh trailing STRONG cua shadow gan 100% vs
   83.8% cua C3. L1 muc 4 da do: truc do **KHONG load-bearing** (0/5 rate ngoai CI o CA HAI cuc),
   nen sai so bi chan tren — nhung day van la **mot diem khac biet co that**, phai ghi khi bao cao.
2. 🔴 **Cong ONNX truot nguong |delta| tuyet doi**: `max|d| = 2.62e-06` > `1e-6` de bai dat.
   Nguyen nhan la cong don float32 trong onnxruntime vs float64 trong `xgboost.predict`.
   **Spearman = 1.000000 va tap top-8 trung 100.0000% tren ca 6,800 tick** — tuc thu ma selector
   THUC SU dung (thu hang) khong lech mot lenh nao. Bao ca hai so, khong lam tron.
3. 🔴 **OI live tren 242 chi giu 2 thang** (`oi_feat_*`: `BTCUSDT_202608`, `202609`; 202512/202511
   khong ton tai). => 2 feature OI (`ls_global`, `rk_oi_delta24h`) **KHONG do khop duoc** cho
   2025-12 tu nguon live. Cong 1 vi vay chi phu **7 feature GIA** (dung nhu de bai yeu cau ngưỡng),
   con 2 feature OI la **CHUA DO**.
4. 🔴 **Model S1 train toi 2025-09-28, dang chay forward 2026-09** — ngoai mep train **11 thang**.
   L1 muc 3b da canh bao; L2 khong go duoc (bi chan boi `CLOSES_1H` khong co generator).
5. ⚠️ **Exit C3 chay trong `ShadowBookC3` (so vi the GIAY), khong phai qua duong dat lenh that.**
   Ly do bat buoc: `SHADOW_NO_PUSH` chan entry => live khong co `PositionRisk` nao => duong exit
   that (`initSLFirst`/`processDynamicTP_SL`) khong bao gio chay. Neu sau nay bat trade that thi
   (b) time-stop tren duong THAT moi chi la **mot dong log**, chua noi vao lenh dong.
6. ⚠️ **Redis phai cai moi tren Oracle** (chua co). Da dung cum **1 node `127.0.0.1:7301`**
   (`cluster-enabled yes`, 16384 slot). **Khong mot ket noi nao toi Redis 242.**
7. ⚠️ **Dia Oracle con ~6.5G/194G (97%)**. Da hach logback rieng cho shadow: 50MB x 3 (mac dinh
   repo la 200MB x 10 = 2.2G, khong dung duoc).

---

## 1. CONG KHOP FEATURE (Viec 1) — **PASS** voi quy uoc `prev`

Code moi: `tradecore/selector/S1FeatureLive.java` (thuan tinh toan, 8 unit test) +
`research/s1live/S1FeatParityProbe.java` (probe READ-ONLY doc 242) +
`research/pipeline/s1live/feat_parity_check.py`.

Nguon live: Aerospike-242 `ns=ticker set=kline_1m_opt` (2,986,955 ban ghi, du lich su).
Cua so do: **2025-12** (thang cuoi co `CLOSES_1H.bin`), warm-up tu 2025-11-15 (384h > lookback 336h).
Doi chung: `featv2/feat_v2_x1.parquet`. Doc **1128/1128** moc gio, **601 symbol** live vs **591** ref,
ghep cap **421,344 dong = 99.80% cua ref**.

### 1.1 Quy uoc gop 1m -> 1h — **`prev` la dung, `open` la sai**

| quy uoc | dinh nghia | ket qua |
|---|---|---|
| **`prev`** | `close(t)` = `priceClose` cua nen 1m co `open_time = t - 1m` (= close cua nen 1h phu `[t-1h, t)` = quy uoc **Vision**) | ✅ **PASS** |
| `open` | `close(t)` = `priceClose` cua nen 1m co `open_time = t` | ❌ FAIL 6/7 feature |

🟢 **Dinh chinh `docs/H1_HOLDOUT_PREP.md` muc 3**: gia thuyet "ticker 1m gop len" **KHONG bi bac** —
no chi bi bac o **canh sai** (`open`). Gop dung mep Vision thi khop den muc float64.

### 1.2 Bang 7 feature GIA (quy uoc `prev`) — nguong `spearman >= 0.999`

| feature | n_pair | spearman | max abs delta | med abs delta |
|---|---|---|---|---|
| `vol_7d` | 421,098 | **1.000000** | 1.70e-14 | 7.98e-17 |
| `dd_7d` | 421,113 | **1.000000** | 1.11e-16 | 2.78e-17 |
| `rk_dd_7d` | 421,113 | **0.999949** | 0.1246 | 0.00758 |
| `hrs_since_high_7d` | 421,113 | **1.000000** | 2.84e-08 | 1.14e-08 |
| `ret_3d` | 410,226 | **1.000000** | 4.44e-16 | 4.16e-17 |
| `rk_ret_3d` | 410,226 | **0.999729** | 0.1128 | 0.00427 |
| `ret_14d` | 407,554 | **1.000000** | 1.78e-15 | 2.78e-17 |

**CONG: PASS** (7/7 >= 0.999).

Doc ky hai cho:
- `hrs_since_high_7d` max|d| = 2.8e-08 la vi **parquet luu float32** (`np.full(..., dtype=np.float32)`
  trong `feat_v2_build.py`), khong phai lech thuat toan.
- `rk_dd_7d` / `rk_ret_3d` co max|d| ~0.12 **khong phai loi rank**, ma la **khac VU TRU cross-section**:
  live thay 601 coin, `CLOSES_1H` thay 591, chi 95.74% coin live ghep cap duoc. Mau so cua
  `rank(pct=True)` vi vay khac nhau. Day la **khac biet co huu va vinh vien** giua shadow va sim
  (vu tru live = coin co ticker that trong phut do; vu tru sim = cot cua `CLOSES_1H.bin`).

### 1.3 Hai feature OI — **CHUA DO DUOC**

`ls_global` va `rk_oi_delta24h` lay tu `LiveOiFeatProvider` (5 set `oi_feat_*` tren 242).
Do truc tiep: cac set do **chi con `BTCUSDT_202608` va `BTCUSDT_202609`** — khong co 2025-11/2025-12.
=> khong the tai lap cua so 2025-12 tu nguon live. Cong 1 **khong phu 2 feature nay**.
Rui ro con lai: `S1FeatureLive.rankPct` da co unit test, nhung *gia tri* `ls_global`/`oi_delta24h`
cua live chua tung duoc doi chung voi `oi_percoin_full.bin` tren mot cua so chung.

---

## 2. CONG MODEL S1 (Viec 2) — JSON **PASS**, ONNX **PASS ve thu hang**, truot |delta| tuyet doi

Code moi: `research/pipeline/x1/x1_s1_save_model.py` (`--save-model` cua fold cuoi).
Fold tai lap: cutoff **20251001**, train `ts < cutoff - 72h` -> **3,485,834** dong,
`train_ts_max = 2025-09-27 16:45` (dung purge 72h), OOS 2025Q4 **3,499,202** dong / 6,909 tick.
Sieu tham so, ledger (`cand_dev_x1`), feature (`feat_v2_x1`) y het `x1_s1_rank.py`.

Artifact: `/home/ubuntu/s1_model/s1a2x1_cut20251001.{json,onnx,manifest.json}`
(JSON 636,020 B · ONNX 282,380 B · sha256 trong manifest).

| nguon predict | n | spearman vs `pred_s1a2x1.parquet` | max abs delta | med abs delta | top-8 trung/tick |
|---|---|---|---|---|---|
| trong bo nho (sau `fit`) | 3,499,202 | **1.000000** | **0** | 0 | — |
| **JSON** (`booster.save_model` + `Booster.load_model`) | 3,499,202 | **1.000000** | **0** | 0 | **6800/6800 = 100.0000%** |
| **ONNX** (onnxruntime 1.23.2) | 3,499,202 | **1.000000** | **2.62e-06** | 1.79e-07 | **6800/6800 = 100.0000%** |

- ✅ **JSON PASS tuyet doi** (`max|d| = 0`): fold cuoi tai lap duoc **byte-for-byte** ve so.
- ⚠️ **ONNX truot nguong `1e-6`** (2.62e-06 = 2.6x). Nguyen nhan: `TreeEnsembleRegressor` cong don
  300 la bang float32 trong ORT; `xgboost.predict` cong bang float64. **Khong sua duoc bang tham so.**
- ✅ Nhung selector chi dung **THU HANG**: `spearman = 1.000000` va **tap top-8 trung tuyet doi
  6800/6800 tick**. => dung ONNX cho live **khong lam lech mot lenh nao** tren OOS 2025Q4.

⚠️ **Bay khi convert** (ghi lai de khoi mat 3 vong): `onnxmltools` 1.16 khong co converter cho
`XGBRanker` -> phai `update_registered_converter(xgb.XGBRanker, ..., calculate_linear_regressor_output_shapes,
convert_xgboost)` cua `skl2onnx`, dung `skl2onnx.common.data_types.FloatTensorType` (KHONG phai ban
cua onnxmltools), va doi `booster.feature_names` sang `f0..f8` TRUOC khi convert. File JSON tren dia
giu nguyen ten feature that; **input ONNX la VI TRI theo `S1FeatureLive.FEATURE_ORDER`**.

Runtime Java: tai dung `com.microsoft.onnxruntime:1.16.3` da co trong `pom.xml`
(cung runtime dang chay `Funding_Classifier_Final.onnx`) — **khong them phu thuoc moi**.

---

## 3. PORT C3 VAO DUONG LIVE (Viec 3) — sau co `LIVE_PROFILE=c3_shadow`, **mac dinh TAT**

Cong tac: `tradecore/selector/LiveProfileC3.java`. Doc co qua `Cfg.get("LIVE_PROFILE")`
(khong `System.getenv` truc tiep — luat `tools/check_cfg_gateway.sh`). Co TAT => moi ham tra
DUNG gia tri HEAD.

🔒 `SHADOW_NO_PUSH` **HARDCODE `true`** khi co bat: `LiveProfileC3.forceNoPush()` tra `true`
**khong doc env**; guard o `processOrderNewMarketNew` la `forceNoPush() || Cfg.get(...)`.
Khong ton tai duong nao dat lenh that khi profile bat.

| mang | live 242 (HEAD) | profile `c3_shadow` | diem noi | co TAT = HEAD? |
|---|---|---|---|---|
| **(a) arm** `SIM_RATE_PROFIT_STOP_MARKET` | 0.05 (env doc duoc, xac nhan `Configs:506`) | **0.07** | `TradeUtils.calRateMinWithPredReturn15MForTradingStop` -> `LiveProfileC3.armRate(Configs.RATE_PROFIT_STOP_MARKET)` | ✅ test `armRateFallsBackWhenOff` |
| **(b) time-stop 168h** | **KHONG CO** (`Simulator...:672` sim-only) | **168h** cho cum chua arm | (i) `ShadowBookC3.tick` — dong that trong so giay; (ii) `processDynamicTP_SL` — **chi LOG** `[SHADOW] would-CLOSE time-stop`, KHONG lenh | ✅ ca hai nhanh sau `on()` |
| **(c) ratchet** | dead-zone `x5.21847` => doi SL chi khi lai > 26.1% | **LIEN TUC** (`x1.0`), `giveback = min(peak*0.5, cap)`, cap **0.08/0.03** ban le **0.29** tren `symbolPred` | `LIVE_RATCHET_DEADZONE_MULT` -> `LiveProfileC3.ratchetDeadzoneMult(...)`; `ShadowBookC3.trailRate` goi CUNG HAM `TradeUtils.calRateLossDynamicBuyPNoPump` voi sim | ✅ test `ratchetDeadzoneFallsBackWhenOff` |
| **(d) sizing** | `14000 x 0.03 x throttle / 13`, KHONG compound; `getAccountUMInfo()` nem (key STUB) => `BUDGET_PER_ORDER = 0` | **compound**: `balanceBasic = PAPER_EQUITY + PnL shadow` (mark-to-market tu `price_realtime`), `marginRunning` tu so giay, `ladder = 1` (`DCA_GRID_WEIGHTS=1,0,0,0`), **tran 4.5% equity** | `createOrderBuyRequest` truoc/sau `TradeUtils.managerBudget` | ✅ nhanh nam tron trong `if (on())` |
| **(e) K** | `SELECTOR_RANK_TOPK=5` | **8** | thuan cau hinh (`conf/env.sh`) | — |
| **thu tu selector** | `selectorRankPool` xep theo `pNoPump` tang dan | **score S1** tang dan (`S1RankerLive`) | `DetectEntry...` `buildS1Pool(time)`; `cap-then-skip` **GIU NGUYEN** (dem rank tren toan pool, `break` tai K, skip coin dang giu sau khi dem) | ✅ `s1Order=false` khi co tat |

### 3.1 `ShadowBookC3` — vi sao phai co (khong phai lam sang)

`SHADOW_NO_PUSH` chan `OrderHelper.newOrderMarket` => **khong sinh `PositionRisk`** =>
(i) `marginRunning` mai bang 0 nen `throttle = 1` va **cung mot coin duoc `would-BUY` lai moi tick**,
(ii) toan bo duong exit live khong bao gio chay => khong the do C3.
`ShadowBookC3` giu vi the GIAY de chan mo trung, cap `equity`/`marginRunning` cho (d), va chay
exit (a)(b)(c). Ghi `shadow_c3/ledger.csv`.

Cot ledger (dat ten de `tools/shadow_vs_sim.py pair` doc thang duoc):
`sym,ts_entry,entry,qty,rank,symbol_pred,ts_exit,exit_price,reason,pnl`.
`reason` ∈ {`TRAILING_STOP`, `TIME_STOP_168H`}.

⚠️ Khac sim o hai cho da biet: ke toan giay **khong tinh phi/slippage/funding** va **khong lam tron
tick-size** (`Utils.calPriceTarget` khong duoc goi vi khong dat lenh).

### 3.2 Unit test + CONG HOI QUY

| lop test | so test | noi dung |
|---|---|---|
| `S1FeatureLiveTest` | 8 | lap lai V3(a) cua `feat_v2_build.py` (ret tuyen tinh, dd=0 khi tang deu, dd sau buoc -50%), `min_periods=84`, `hrs_since_high` 3 canh, `vol_7d` ddof=1, `rank(pct)` tie/NaN, `computeTick` thu tu |
| `LiveProfileC3Test` | 8 | **co TAT => tra dung gia tri HEAD** (arm, dead-zone, forceNoPush, paperEquity=0); hang so C3; hinh dang `trailRate`; tran 4.5%; `U_MAX` van chan |
| `ShadowBookC3Test` | 5 | arm chi khi >7%; ratchet lien tuc (dong o muc live-dead-zone SE KHONG dong); time-stop 168h chi khi chua arm; ke toan equity/margin; khong mo trung |

**Cong hoi quy:** `mvn -o test` = **81/81 PASS** (60 test cu + 21 moi), `mvn -o -DskipTests package`
BUILD SUCCESS. Toan bo 60 test cu khong sua mot dong.
**Chung minh duong cu khong doi:** moi diem noi deu la `if (LiveProfileC3.on())` hoac
`LiveProfileC3.xxx(<gia tri HEAD>)`; `LiveProfileC3Test` khang dinh co TAT tra dung `<gia tri HEAD>`
cho ca ba (a)(c) + `forceNoPush()=false`. Khong co nhanh nao doi hanh vi khi co tat.

---

## 4. INSTANCE SHADOW TREN ORACLE (Viec 4)

```
/home/ubuntu/shadow_c3/
  app/                       <- cwd cua JVM
    target/binance-java-sdk-1.2.4.jar   (build tu branch `module` + patch L2)
    config.properties        AEROSPIKE_READ_CLUSTER=242, ns=ticker, CAPITAL_START=35000
    redis.config             Redis.Address=127.0.0.1:7301   <- CUM RIENG, khong phai 242
    logback.xml              50MB x 3 (dia 6.5G)
    conf/env.sh              LIVE_PROFILE=c3_shadow ...
    bin/{daemon.sh,start.sh} start|stop|restart|status
    logs/ run/
  storage/ai_ml_data/{models_funding,ai_models_reg_v3}   <- copy CHI-DOC tu 242
  redis/                     redis-server 7301 (cluster-enabled, 16384 slot)
  bin/health.sh              cron moi gio
  ledger.csv  ledger_from_log.csv  health.log
```

`conf/env.sh`:
```
export LIVE_PROFILE=c3_shadow
export SHADOW_NO_PUSH=true
export PAPER_EQUITY=35000
export SHADOW_C3_DIR=/home/ubuntu/shadow_c3
export S1_MODEL_ONNX=/home/ubuntu/s1_model/s1a2x1_cut20251001.onnx
export SELECTOR_RANK_TOPK=8
export SELECTOR_ONLY_ENTRY=1
export SIM_MIN_MOMENTUM_15M=0.008
export SIM_RATE_PROFIT_STOP_MARKET=0.07
export DCA_GRID_WEIGHTS=1,0,0,0
export TIER_FLAT=1
export SIM_TS_GIVEBACK=1
export TS_GIVEBACK_RATIO=0.5
export EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json
```

Kiem truoc khi chay: `free -g` = 23G total / **19G available**; `df -h /` = **6.5G free (97%)**.
`-Xms1g -Xmx4g`. **1 slot JVM Oracle**: shadow dang chiem => KHONG chay sim dong thoi.

Hai file copy tu 242 (**CHI DOC**, khong ghi gi len 242):
`models_funding/Funding_Classifier_Final.onnx` (sha256 `dce8b6a692f672c2...` — **trung dung
gia tri L1 ghi cho model live**) va `ai_models_reg_v3/*` (11 file, 105M).


### 4.1 SHADOW **CHAY DUOC** — quan sat truc tiep (2026-09-06, gio GMT+7)

| moc | quan sat |
|---|---|
| 14:49:26 | JVM len. Nap `ai_models_reg_v3` (Return15M + maxDrawdown4H) va `Funding_Classifier_Final.onnx` OK. `exchange_info_pin.json` offline mode, 892 symbol. Symbol mapper 904. |
| 14:49:45 | `🟡 [LIVE_PROFILE=c3_shadow] BAT — arm=0.07 timeStop=168h ratchet=LIEN TUC paperEquity=35000.0 sizeCap=4.5%` |
| 14:49:50 | `[SHADOW] so vi the giay khoi tao, ledger=/home/ubuntu/shadow_c3/ledger.csv` |
| **15:00:06** | tick selector dau tien (luoi 15m: `:00/:15/:30/:45`, cua so giay 03-10) |
| 15:03:22 | `[S1] nap model ONNX ... input=input nFeature=9` |
| 15:03:47 | `[S1] nap 384 moc gio close, 719 coin trong bo nho` — **warm-up 14 ngay (+2 ngay du tru) doc lui tu Aerospike, 25 giay** |
| 15:07:03 | `[S1] score 550 coin` |
| 15:07:03-07 | **8 dong `would-BUY`** = DUNG `SELECTOR_RANK_TOPK=8` |
| **15:15:06 -> 15:18:56** | tick 2 (sau khi toi uu nap OI): tron ven **3 phut 50 giay** |
| 15:18:53 | `[S1] nap OI (delta24h + ls_global) cho 569 coin trong 11950 ms` |
| 15:18:54-56 | 8 dong `[SHADOW] open` rank **1..8** lien tuc, co `symbolPred` va `margin` |

**Sizing compound (d) hoat dong dung cong thuc** — budget cua 8 lenh trong mot tick:

```
MARSCOIN 1050.00   BTR 997.57   FLOCK 947.49   BULLA 901.06
UAI       853.83   AKE 810.88   ARB  771.03   DASH 729.92
```
Lenh dau = `35000 x 0.03 x 1.0 / 1 = 1050.00` **chinh xac** (`PAPER_EQUITY` x `F_BASE` x `throttle` / `ladder`,
`ladder = 1` do `DCA_GRID_WEIGHTS=1,0,0,0`). Cac lenh sau nho dan vi `throttle = 1 - u/U_MAX` giam khi
`marginRunning` cua so giay tang. Tran 4.5% equity (1575) khong rang buoc o day.
=> **Duong `getAccountUMInfo()` da bi bo hoan toan**; chan B4 cua L1 (`BUDGET_PER_ORDER = 0`) da mo.

**Kiem an toan (bat buoc):**

| kiem | ket qua |
|---|---|
| lenh THAT (`market level:` khong co `[SHADOW]`) | **0** |
| `[SHADOW] would-BUY` | 16 (2 tick x 8) |
| ket noi toi Redis 242 (`ss -ntp \| grep 3000[1-6]`) | **rong** — chi `127.0.0.1:7301` |
| ghi len 242 | **khong** (chi doc `kline_1m_opt`, `oi_feat_*`, `ai_pred_1m`, `funding_data`) |
| `logs/error.log` | **0 dong**; `Exception` trong `full.log` **0** |
| RAM | RSS **1.6-1.8G** / `-Xmx4g`, Oracle con 17-18G available |
| dia | 6.5G free, khong doi (logback 50MB x 3) |
| cron `0 * * * *` | chay dung gio (`health.log` co ban ghi 08:00:01Z) |

⚠️ `Error get position from binance!` moi 60 giay va `Ba and Bu` nem — **BINH THUONG va MONG DOI**:
key Oracle la STUB (`PrivateConfig`), khong co vi the that. Khong anh huong duong shadow vi sizing
da chuyen sang `ShadowBookC3`.


### 4.1b Cua so 76 PHUT lien tuc (14:49 -> 16:05 GMT+7) — **5 tick, khong loi**

| tick (bat dau) | ket thuc | dai | `[S1] score` | `would-BUY` |
|---|---|---|---|---|
| 15:00:06 | 15:07:07 | 7'01" | 550 coin | 8 |
| 15:15:06 | 15:18:56 | 3'50" | 569 coin (OI 11,950 ms) | 8 |
| 15:30:06 | 15:34:02 | 3'56" | 592 coin (OI 9,730 ms) | 8 |
| 15:45:06 | 15:48:20 | 3'14" | 582 coin | **0** |
| 16:00:06 | 16:03:08 | 3'02" | 529 coin | **0** |

Hai tick cuoi **0 `would-BUY` la DUNG, khong phai loi**: ca 8 slot cua `SELECTOR_RANK_TOPK=8`
dang bi chiem trong `ShadowBookC3` => `book.isHolding(symbol)` chan mo trung (dung vai tro cua
`symbol2Pos` tren duong that). Day chinh la trang thai "no candidate" ma de bai noi.

🟢 **Bat duoc ca duong exit chay that** luc 15:39:01:
```
[SHADOW] arm FLOCKUSDT peak=0.07274954 SL=0.0761139
```
va 26 phut sau, `open_positions.csv` cho `FLOCKUSDT`: `peak_rate = 0.10837636`,
`price_sl = 0.0775847`. Tuc **SL da duoc ratchet len** tu 0.0761139 -> 0.0775847 khi dinh di tu
7.27% -> 10.84%. Kiem lai bang tay: `entry x (1 + peak - min(peak x 0.5, 0.08))`
= `0.07354 x (1 + 0.10838 - 0.05419)` = **0.077525** ✓ (`symbolPred = 0.1444 <= 0.29` => STRONG,
cap 0.08 khong rang buoc).
🔴 **Tren duong live HEAD, SL nay se KHONG NHUC NHICH**: dead-zone doi lai phai vuot
`5.21847 x 0.05 = 26.1%`, ma dinh moi 10.8%. Day la bang chung TRUC TIEP cho khac biet co che
so 4 cua `docs/L1_SHADOW_C3.md` muc 0.

Tai nguyen cuoi cua so: RSS **2.0G** (phang tu 1.9G suot 30 phut), Oracle con **17G** available,
dia **6.5G** khong doi, `full.log` **102 KB**, `error.log` **0 byte**, `Exception` **0**,
ket noi Redis 242 **0**, lenh THAT **0**.

### 4.2 Hai loi da phat hien va sua NGAY trong dot nay

1. 🔴 **So vi the chi nam trong RAM**. `ThreadAutoRestartProgram` restart JVM **moi 4 gio** =>
   (i) time-stop 168h **KHONG BAO GIO** toi duoc, (ii) cung mot coin bi mo lai moi 4h => ledger sai
   he thong. **Da sua**: `ShadowBookC3` ghi `shadow_c3/open_positions.csv` sau MOI thay doi
   (open / arm / ratchet doi SL / close) va nap lai luc khoi dong. Test `stateSurvivesRestart`.
2. ⚠️ **`[S1]` nap OI qua cham qua WAN**: ban dau dung `LiveOiFeatProvider` (nap ca **5** set, xoa
   cache moi tick) => ~3.5 phut/tick tu Oracle. **Da sua**: chi nap **2** set S1 can
   (`oi_feat_delta24h`, `oi_feat_lsg`), doc **song song 8 luong**, cache theo GIO (cadence
   `ComputeOiFeat2Live242` la 60'). Do lai: **11,950 ms cho 569 coin**.
3. ⚠️ `health.sh` ban dau dem `Create order market` la "lenh that" — **bao dong gia**: dong do duoc
   in **TRUOC** guard `SHADOW_NO_PUSH`. Da doi sang `grep 'market level: ' | grep -v '[SHADOW]'`.

### 4.3 Phan bo `symbolPred` do duoc — **nguoc voi du doan cua L1**

L1 muc 3c du doan shadow se "gan 100% STRONG" (dua tren log 242 co `symbolPred` 0.054-0.116).
Do that trong tick 15:15 (8 lenh, ban le 0.29):

```
MARSCOIN 0.213 S · BTR 0.694 W · FLOCK 0.198 S · BULLA 0.079 S
UAI      0.154 S · AKE 0.190 S · ARB   0.220 S · DASH  0.549 W
```
=> **6/8 STRONG (75%)**, khong phai 100%. Dai gia tri that rong hon nhieu so voi dai quan sat
tren 242 (0.07-0.69 vs 0.054-0.116). **Ghi lai vi no lam nhe bot — nhung KHONG go bo — diem khac
biet so 1 o muc 5.** n = 8 lenh, khong duoc coi la uoc luong phan bo.

---

## 5. DIEM SHADOW KHAC SIM C3 — doc TRUOC khi so bat ky con so nao

| # | truc | sim C3 | shadow C3 | do lon / huong |
|---|---|---|---|---|
| 1 | **gia tri gate `symbolPred`** | `predwf_G015x26` (bins offline, ~0.35) | `Funding_Classifier_Final.onnx` real-time (0.054-0.116) | **lech hieu chuan hoan toan**. Ban le 0.29 => shadow ~**100% STRONG**, C3 **83.8% STRONG**. L1 muc 4 do: truc nay **0/5 rate ngoai CI** o ca hai cuc => sai so bi chan tren, nhung **phai tach STRONG/WEAK truoc khi ghep cap** |
| 2 | **thu tu selector** | S1 tren bins `predwf_map_s1a2` (`build_map` tren G015x26) | **S1 truc tiep** (ONNX fold cutoff 20251001) | Ve THU HANG day la **cung mot model**: cong 2 do top-8 trung **100.0000%** tren 6,800 tick OOS 2025Q4. Khac o cho sim di **qua bins**, shadow tinh **thang** |
| 3 | **nguon close 1h** | `CLOSES_1H.bin` = kline 1h Vision | `kline_1m_opt` 242 gop theo quy uoc `prev` | Cong 1: spearman **1.000000** cho 5 feature gia tho, max\|d\| <= 1.8e-15. **Khong phai nguon lech** |
| 4 | **vu tru cross-section** | cot cua `CLOSES_1H.bin` (591 coin trong 2025-12) | coin co ticker that trong phut do (601) | mau so cua `rank(pct=True)` khac => `rk_dd_7d`/`rk_ret_3d` lech toi 0.12 o duoi 0.03% so cap. **Co huu, khong sua duoc** |
| 5 | **model S1 ngoai mep train** | OOS ngay sau cutoff | forward **2026-09**, cach cutoff 2025-10 **11 thang** | chua do duoc. Day la rui ro lon nhat ve chat luong |
| 6 | **exit chay o dau** | trong engine sim, dong lenh that trong mo phong | trong `ShadowBookC3` (so GIAY) | (b) time-stop tren duong dat lenh THAT moi chi la **log**, chua noi vao lenh dong |
| 7 | **ke toan** | co funding (`SIM_APPLY_FUNDING=true`), phi, tick-size | **khong** funding, **khong** phi/slippage, **khong** lam tron tick-size | PnL shadow la "ke toan giay" — **khong so `mean(margin)`/equity voi sim** (`L1` muc 7.2) |
| 8 | **`p15` gate** | `wfo_gate_pred.csv` (21 fold WFO) | `Model_Regressor_Return15M.onnx` cua 242 (ban gate-WFO 17/08) | L1 muc 3d: **chua chung minh duoc dong nhat**, khong duoc gia dinh |
| 9 | **do tre** | dataset, khong tre | tick 15m + `kline_1m` tre ~1 phut + OI asof <= 2h | — |

---

## 6. LENH CHO USER

### 6.1 Deploy len 242 — **CHUA LAM, la viec cua user**
Jar moi (`target/binance-java-sdk-1.2.4.jar` tren Oracle, branch `module`) chua toan bo thay doi
L2 **sau co mac dinh TAT**, cong voi X1/X2/X3/X4 chua tung chay tren live. Deploy la mot viec RIENG,
phai co runbook + pre-reg rieng (`L1` muc 6.5 da ghi). **Neu deploy: KHONG dat `LIVE_PROFILE` tren
242** thi hanh vi bot that khong doi mot bit (81/81 test + `LiveProfileC3Test` chung minh).

### 6.2 Van con treo tu L1 (khong doi)
- `L1` 6.1: xac dinh `TS_PRED_GAP` / `SIM_TS_PROFIT_MULTIPLIER` co song trong jar 02/09 dang chay khong.
- `L1` 6.3: 66 vi the cu tren 242 — **quyet dinh giao dich cua user**, agent khong de xuat.

### 6.3 Muon do 2 feature OI (cong 1 con thieu)
`oi_feat_*` tren 242 chi giu 2 thang. Hai duong:
1. Chay `ComputeOiFeat2Live242` backfill cho 2025-11/2025-12 roi do — **GHI len 242**, can user duyet.
2. Do gian tiep tren cua so **2026-08** (thang duy nhat co ca oi_feat live lan `oi_percoin_full.bin`)
   — **KHONG can cham 242**, nhung 2026-08 **nam trong holdout** (`HoldoutSeal.SEAL_MS=2026-01-01`)
   nen phai co `HOLDOUT_UNSEAL` + user duyet truc tiep. **Agent khong tu mo.**

### 6.4 Unseal khi doi chung shadow <-> sim
Giu nguyen luat `L1` muc 7.1: chi mo DUNG doan shadow da troi qua, co user duyet truc tiep,
ghi ledger holdout, roi seal lai ngay.
