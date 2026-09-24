# L4_LIVE_BUILDMAP — `build_map` chay LIVE: shadow thanh **C3 dung nghia o tang entry**

Ngay 2026-09-07. Tiep noi `docs/experiment/L3_DEPLOY_PREP.md`, `docs/experiment/G4_RECIPE_C4.md`, `docs/experiment/G5_VALUE_LABELS.md`.
**Agent KHONG SSH 242** trong dot nay (khong doc, khong ghi). Deploy la viec cua user.

---

## 0. RUI RO TRUOC — 6 dieu

1. 🔴 **Cong REPLAY o day KHONG do duoc duong FEATURE cua live.** No do duoc ba thu:
   ONNX-trong-Java, port `build_map`, va ghep noi ba thu do — tren feature **OFFLINE**
   (Tool1 + `oi_percoin_full.bin`). Ly do bat buoc: `oi_feat_*` tren 242 **chi giu 2 thang**
   (`202608`, `202609` — `L2_PORT_C3` muc 0.3/1.3), nen **khong the** tai lap 45 feature
   real-time cua 2025-11/2025-12 tu nguon live. Cua so duy nhat co ca hai nguon la **2026-08**,
   nam trong `HoldoutSeal` => phai unseal + user duyet. **Khong lam.**
   => **Cong "45 feature live vs Tool1 offline" van CHUA DO.** Xem muc 3.
2. 🔴 **Toan bo L4 chua chay tren 242 mot giay nao.** Bang chung hanh vi that duy nhat con la
   instance shadow Oracle — ma no **da TAT** truoc dot nay (muc 6). L4 khong khoi dong lai.
3. 🔴 **Chieu cua `build_map` phan truc giac** — doc ky muc 1 truoc khi doc bat ky so nao:
   coin **TOT nhat** theo S1 nhan `P(win)` **LON nhat** cua tick, tuc `symbolPred` **THAP nhat**.
   Sai chieu o day = dao nguoc ca selector. Da kiem 3 duong doc lap (muc 1.3).
4. ⚠️ **Dai `p10/50/90` ma de bai neu (0.14/0.24/0.37) la dai cua `symbolPred` MUC LENH, khong
   phai cua vu tru moi tick.** Log `[MAP]` in dai VU TRU (p50 ~0.47). Do la hai dai khac nhau,
   khong phai lech hieu chuan. Chi tiet + so do duoc: muc 4.4. `verify.sh` vi vay gate tren dai
   **da do** `[0.20, 0.70]`, khong phai tren `0.14/0.24/0.37`. Day la **sua mot loi doi chieu
   nham**, khong phai noi cong.
5. ⚠️ **Khi thang gia tri khong san sang, so giay KHONG mo entry** (khong thay bang `pNoPump`).
   Chon co y: mot tick trong con hon mot tick sai hieu chuan. `verify.sh` FAIL neu thay
   `[MAP] chua co thang gia tri`.
6. ⚠️ **Model van ngoai mep train 11 thang** (S1 va net015 deu cutoff 2025-10, chay forward
   2026-09). L2 muc 5 diem 5, L3 muc 0 diem 5 — L4 **khong go duoc**.

---

## 1. QUY UOC `build_map` — rut TRUC TIEP tu code, khong dien giai

### 1.1 Bon dong quyet dinh (`research/pipeline/build_map.py:39-42`, giong het o
`x1/x1_build_map.py` va `x1/c4_build_map.py`)

```python
sub["r_score"]  = sub.groupby("ts").score.rank(method="first")                 # 1 = TOT nhat
sub["p_sorted"] = sub.groupby("ts").p.rank(method="first", ascending=False)    # 1 = p CAO nhat
key             = sub.set_index(["ts","p_sorted"]).p
sub["p_new"]    = key.reindex(list(zip(sub.ts, sub.r_score))).values
```

| cau hoi cua de bai | tra loi |
|---|---|
| `symbolPred = 1 − P(win)`? | **DUNG.** Bins `predict_wf_*.bin` luu `p0 = P(win)` (4h, `retEnd_4h > 0.015`). Java **dao dau** o `WfoDataset.buildFundingFromWfFiles:248`: `float score = 1.0f - pwin; // DAO DAU`. Khop tuyen bo pre-reg cua `AGENT_RUNBOOK` muc 4 (G5). |
| sort chieu nao? | `score` S1 **tang dan** (thap = tot); `p` **giam dan** (`ascending=False`). Coin rank k nhan `p` lon thu k. Sau dao dau: coin rank 1 co `symbolPred` **thap nhat** => duoc sim chon truoc (`SimulatorMarketLevelTicker1MStopLoss:316-323` lay K phan tu dau cua mang da sort TANG). |
| `method="first"`? | **Co**, ca hai lan. The pha theo **THU TU DONG** trong DataFrame. |
| tie-break? | Thu tu dong. Live khong co "thu tu dong" => `LiveBuildMap` bat caller truyen `rowOrder`; duong live dung **ten symbol tang dan** (tat dinh). Harness REPLAY dung **thu tu dong cua file bins** de doi chung Python duoc. |
| dong khong co score? | **Giu nguyen `p` cu** (`M["p_new"] = M.p` roi chi ghi de tren `sub`). Da tai lap y het trong harness; do duoc **23.73%** dong tren 3 ngay DEV. |

### 1.2 Multiset bat bien
`sub` chi hoan vi gia tri trong pham vi **cac dong CO score cua cung mot tick**. Multiset
`P(win)` cua nhom do khong doi => admission bat bien tuyet doi (`G5_VALUE_LABELS`, kiem
`pass=103,840` / `adm_top8=5,906` bang tung don vi). L4 do lai o muc 4: `max|d| = 0`.

### 1.3 BA duong kiem doc lap cho CHIEU (vi day la cho de sai nhat)
1. **Code**: `WfoDataset:248` dao dau + `Simulator:316-323` lay K phan tu **dau** mang **tang**.
2. **Thuc nghiem tren bins da deploy** (fold `20251001`): spearman per-tick giua `score`
   (`pred_s1a2x1.parquet`) va `p0` (`predwf_map_s1a2_x1`) = **−1.000000 chinh xac** o moi tick.
3. **Edge**: tren `cand_dev_x1`, chon 8 coin `p0` **CAO** nhat cho `edge8 = +21.49%`
   (bins map) / `+24.22%` (bins gia tri goc); chon 8 coin `p0` **THAP** nhat cho **−4.20%** /
   **−3.44%**. Tuc `p0` cao = tot, va sau dao dau thi `symbolPred` thap = tot. Ba duong dong y.

---

## 2. VIEC 1 — `LiveBuildMap` trong nhanh `LIVE_PROFILE=c3_shadow`

### 2.1 Lop moi

| lop | vai tro |
|---|---|
| `tradecore/selector/LiveBuildMap.java` (160 dong) | **thuan tinh toan**, khong I/O. `assign(rowOrder, s1Score, pwin)` -> `symbolPred` + `pwinMapped` + `rank`. `rankFirst()` = `pandas.rank(method="first")`. |
| `tradecore/selector/Net015ValueLive.java` (116 dong) | nap `net015` ONNX, `pwin(float[][])` -> `P(win)` = `probabilities[:,1]`. Hong model -> `isReady()=false`. |
| `research/l4/L4ReplayHarness.java` + `S1OnnxProbe.java` | harness REPLAY (khong nam trong duong chay live). |

### 2.2 Diem noi tren duong live (`DetectEntrySignal2TradeNormal`)

1. `predictAllCandidates`: sau khi da co `featureArrays` cho model funding live, **giu lai chinh
   mang do** — `selFeat45.put(sym, featureArrays.get(i))`, chi khi `LiveProfileC3.on()`.
   🟢 **KHONG tinh them mot feature nao**: `net015` va `Funding_Classifier_Final.onnx` dung
   **cung mot** `float[45]`.
2. Truoc vong chon top-K: `buildValueMap(time, selPool)` — score toan vu tru da qua gate p15
   (dung tap coin ma S1 cham diem) -> `pwin[]` -> `LiveBuildMap.assign(...)` ->
   `selMapPred` + `LATEST_SEL_MAPPRED`.
3. Trong vong chon: `Float symbolPred = s1Order ? selMapPred.get(symbol) : entry.getKey();`
   (truoc L4 la `selPnp.get(symbol)` = `pNoPump`).
4. `BinanceOrderTradingManager` (mo vi the GIAY): `LATEST_SEL_PNOPUMP.get(...)` ->
   `DetectEntrySignal2TradeNormal.paperSymbolPred(...)`.
   🔒 **Duong THAT (66 vi the legacy) VAN doc thang `LATEST_SEL_PNOPUMP`** o
   `BinanceOrderTradingManager:485` (SL-loop) — khong doi mot bit. Hai ban do TACH HAN.

### 2.3 Log `[MAP]`

```
[MAP] tick=1762102800000 n_coins=522 p10=0.3900 p50=0.5176 p90=0.6210
[MAP] top <SYM> rank=<k> symbolPred=<v>        (8 dong dau bang thu tu selector)
```

### 2.4 An toan
- `SHADOW_NO_PUSH` **hardcode** (`LiveProfileC3.forceNoPush()`) — **khong dong toi**, con nguyen.
- Co TAT (`LIVE_PROFILE` khong dat) => `selFeat45` khong duoc ghi, `buildValueMap` khong chay,
  `paperSymbolPred` tra dung `LATEST_SEL_PNOPUMP` => **duong HEAD byte-identical**.
- LEGACY isolation cua L3 **giu nguyen** (`LegacySymbols`, `skip-LEGACY` truoc khi dem rank).
- `tools/check_cfg_gateway.sh` -> **OK (rc=0)**: `NET015_MODEL_ONNX` doc qua `Cfg.get`.

### 2.5 Unit test — **105/105 PASS** (97 cu + 8 moi), `mvn -o -DskipTests package` BUILD SUCCESS

`LiveBuildMapTest` (8 test). Fixture VANG do **chinh pandas** sinh
(`research/pipeline/l4/gen_buildmap_fixture.py` chay dung 4 dong cua `build_map.py`), **co y**
cai 3 dong trung `score` + 5 dong trung `p` de kiem tie-break:

| test | khang dinh |
|---|---|
| `matchesPythonBuildMapValueByValue` | Java == pandas **tung gia tri** (`delta = 0f`) tren ca 40 dong, ke ca dong co the |
| `symbolPredIsOneMinusPwin` | dao dau dung `WfoDataset:248` |
| `multisetPreserved` | multiset `P(win)` khong doi |
| `bestRankGetsHighestPwin` | rank 1 <-> `P(win)` max <-> `symbolPred` min |
| `rankFirstBreaksTiesByRowOrder` | `rank(method="first")` ca hai chieu, khong co rank trung |
| `rowOrderMattersOnlyForTies` | dao thu tu dong chi doi dung cac dong co the |
| `returnsNullOnMissingOrNaN` | thieu khoa/NaN -> `null` (caller giu duong cu, KHONG doan) |
| `liveRowOrderIsDeterministic` | thu tu dong live tat dinh |

**97 test cu khong sua mot dong.**

---

## 3. CONG FEATURE 45 LIVE vs TOOL1 — **CHUA DO DUOC** (khai bao thang)

De bai yeu cau: score cung rows offline bang `g015_net_train.py`, cong `spearman >= 0.999`.
**Khong chay duoc**, ly do o muc 0 diem 1 (`oi_feat_*` tren 242 chi giu 2 thang; cua so co ca
hai nguon la 2026-08, nam trong holdout).

Cai **da lam duoc** la **cong THU TU (tinh)** — dieu kien can, khong phai dieu kien du:

| vi tri | duong LIVE (`FundingOnnxInferenceManager.extractFeaturesToArray`) | duong TRAIN (`g015_net_train.build_matrix`) |
|---|---|---|
| 0..39 | 40 truong theo thu tu khoa, chu thich trong code: *"khop selector WFO 45-feature (`ExportFeaturesForPythonTool.convertFeaturesToArray` + 5 OI). Thu tu KHOA, KHONG chen giua."* | `X[:, :40] = F[ridx]` — 40 cot Tool1 |
| 40..44 | `oiDelta24hCoin, oiZCoin, lsGlobalCoin, lsToptraderCoin, takerBuyRatioCoin` | `OI_NAMES = ["oi_delta24h","oi_z","ls_global","ls_toptrader","taker_buy"]` |

Khoi OI **trung ten va trung thu tu 5/5**. Da ghi ca 45 vi tri ra
`deploy_242_l3/models/feature_order_net015.txt`.

🔴 **Cai CHUA chung minh** (phai ghi ro, khong duoc coi la da xong):
- **gia tri** 40 feature Tool1 tinh real-time co bang gia tri Tool1 offline khong (chi biet
  chung dung chung mot ham export theo chu thich trong code, chua do bang so);
- **gia tri** 5 feature OI live (`LiveOiFeatProvider`) vs `oi_percoin_full.bin`;
- quy uoc `merge_asof(tol=2h)`: live dung `MERGE_TOL_MS` cua `OiFeatLiveSets` + `OI-GUARD-2`
  (gate ca tick khi pipeline OI qua han 2h) — **cung tham so**, nhung chua doi chung bang so.

Do la **cung mot lo hong** ma `L2_PORT_C3` muc 1.3 da mo cho 2 feature OI cua S1, nay mo rong
ra 5 feature OI cua net015. **Khong go duoc trong dot nay.** Huong duy nhat khong cham holdout:
backfill `ComputeOiFeat2Live242` cho 2025-11/12 — **GHI len 242**, can user duyet
(`L2_PORT_C3` muc 6.3 duong 1).

---

## 4. CONG REPLAY 3 NGAY DEV — **PASS**

3 ngay: **2025-11-03, 2025-11-17, 2025-12-08** (fold `20251001`, co ca bins `predwf_G015x26`
lan bins map `predwf_map_s1a2_x1`). Input do `research/pipeline/l4/build_replay_input.py` dung;
chay bang `research/l4/L4ReplayHarness`; cham bang `research/pipeline/l4/l4_gates.py`.

```
150,084 dong | 288 tick (3 x 96) | 537 coin | co score S1 = 76.27%
dong KHONG co score (build_map giu nguyen p) = 35,613 = 23.73%
220/288 tick co it nhat mot coin duoc map (68 tick con lai: gate dong het)
```

### 4.1 Cong A — ONNX trong JAVA vs bins

| doi chieu | n | spearman | max\|d\| | med\|d\| |
|---|---:|---:|---:|---:|
| `net015` ONNX (Java) vs `predwf_G015x26` `p0` | 150,084 | **1.000000** | **4.768e-07** | 2.980e-08 |
| S1 ONNX (Java) vs `pred_s1a2x1.parquet` `score` | 114,471 | **1.000000** | **1.431e-06** | 1.788e-07 |

`4.768e-07` khop bac do lon ma `G4_RECIPE_C4` muc 5 ghi cho cap ONNX-vs-JSON (`4.6e-07`) —
la sai so cong don float32 cua `TreeEnsembleRegressor/Classifier`, **khong doi mot thu hang nao**.

### 4.2 Arm `MAPONLY` — co lap RIENG ban port `build_map` (pwin = bins, score = parquet)

| do | ket qua |
|---|---|
| `symbolPred_live` vs bins, **toan bo 150,084 dong** | spearman **1.000000**, **max\|d\| = 0.000e+00** |
| spearman **per-tick** (220 tick) | min **1.000000**, tb **1.000000** |
| top-8 trung / tick | **100.0000%** |
| multiset per-tick max\|d\| | **0.000e+00** |

🟢 **Ban Java cua `build_map` tai lap bins da deploy BYTE-EXACT tren 150,084 dong.**
Day la cong manh nhat cua dot nay: no tach han loi port ra khoi moi nguon sai so khac.

### 4.3 Arm `E2E` — pwin va score deu do **JAVA ONNX** sinh

| do | ket qua | **cong** | dat? |
|---|---|---|:--:|
| spearman (toan bo) | **1.000000** | >= 0.999 | ✅ |
| spearman **per-tick**, min tren 220 tick | **1.000000** | — | ✅ |
| top-8 trung / tick | **100.0000%** | >= 99% | ✅ |
| multiset per-tick max\|d\| | **4.768e-07** | khop | ✅ |
| `symbolPred` max\|d\| | 1.241e-03 | — | ghi lai |

`max|d| = 1.241e-03` la **hoan vi the**: hai coin co `P(win)` cach nhau ~1e-07 doi cho nhau
trong bang xep hang `p`, nen nhan hai gia tri lan can cua multiset. Do la dung co che
`G4_RECIPE_C4` muc 4.3 mo ta (o do bien do len toi 0.3715 vi bins goc lech 1 ULP tren 13.25%
dong). O day bien do nho hon **300 lan** va **khong doi mot thu hang nao** (spearman per-tick
min = 1.000000, top-8 = 100%).

### 4.4 Lech vu tru + dai `symbolPred` (doc ky — de bai doi chieu nham dai)

- **Lech vu tru live vs offline**: 23.73% dong khong co score S1 (`build_map` giu nguyen `p`);
  0.00% dong thieu 45 feature; 1.47% dong thieu >= 1 trong 9 feature S1.
  Tren duong LIVE khong ton tai "dong khong co score" — vu tru live = dung tap coin S1 cham
  diem duoc. Day la **lech co huu**, khong sua duoc, giong `L2_PORT_C3` muc 5 diem 4.
- **Dai `symbolPred`**:

| tap | p10 | p50 | p90 |
|---|---:|---:|---:|
| **vu tru moi tick** (cai `[MAP]` in ra), tb 220 tick | 0.3732 | **0.4689** | 0.5588 |
| vu tru, khoang qua 220 tick | 0.1826..0.4909 | **0.2262..0.6093** | 0.2660..0.7221 |
| **top-8 moi tick** (cai thanh LENH) | **0.2555** | **0.2974** | **0.3373** |
| tham chieu `C4_parity` muc LENH, 48 thang (`G4` muc 4.1) | 0.1424 | 0.2173 | 0.3223 |

Dai `0.14/0.24/0.37` cua de bai la dai **muc lenh**. Do duoc o day cho top-8 la
**0.2555/0.2974/0.3373** — cung bac, nam gon trong `0.14..0.40`; lech vi (i) chi 3 ngay
2025-11/12 chu khong phai 48 thang, (ii) chua qua gate `mom15`. Dai **vu tru** thi p50 ~0.47
(= `1 − 0.4642`, dung `p_mean` cua `net015` ma `G4` muc 5 ghi) — **khong** so duoc voi 0.24.
=> `verify.sh` gate `p50 in [0.20, 0.70]` (do tren 220 tick: 0.2262..0.6093).

---

## 5. GOI DEPLOY `/home/ubuntu/deploy_242_l3/` — **CHUA DEPLOY**

| file | sha256 |
|---|---|
| `sim.jar` (99,646,626 B) | `f7e3873cc6b012dac462e2f298b37c22f2bd5f342e6fed54c9da64cbd5fbfeff` |
| `models/g015x26_f15_cut20251001.onnx` (806,830 B) | `7921ceaf2405049ddf2c23187264c34d6c95a38125f33c9ef3506f02f4e6dd8b` |
| `models/s1a2x1_cut20251001.onnx` (282,380 B) | `6067a0a2eb8ca462c03614f1fe37f83ff42d5bb58d3b1b031427966ec9983354` |
| `models/s1a2x1_cut20251001.json` | `cc0924f1e26f9fcc199e33ef161916e293f48f4b4a0b3f8ca14ade0127997308` |
| `models/s1a2x1_cut20251001.manifest.json` | `5de107944532f00b6acab49620756e6bbd8a5fcc6c8b36c4f3269bb9e2680579` |
| `models/feature_order_net015.txt` (45 cot) | `79abb95e358028dbfe01c7bd0843e10417f0166edca5006ca550b4cb1d45e509` |
| `models/feature_order_s1.txt` (9 cot) | `e98bd1f4baf4db86221f7bb1bf85e8bc35dd45cc03f9953f858bb5655840b303` |

sha256 cua `g015x26_f15_cut20251001.onnx` **trung** gia tri `G4_RECIPE_C4` muc 5 ghi
(`7921ceaf24...`); 4 sha cua S1 **trung** L3 (khong build lai model nao).
`s1_c3/` cu **da bo** (thay bang `models/`), tranh deploy nham file cu.

`env.sh.new` them `NET015_MODEL_ONNX` va **BAT** `DCA_GRID_WEIGHTS=1,0,0,0` + `TIER_FLAT=1`
(user duyet 2026-09-07; day la **tham so SO GIAY**, chi vao duong sizing entry — entry that da
bi chan nen khong cham duong dong legacy; `README_DEPLOY.md` muc 6).
`SIM_RATE_PROFIT_STOP_MARKET=0.05`, `TS_PRED_GAP`, `SIM_TS_PROFIT_MULTIPLIER` **GIU NGUYEN**.

`verify.sh` them nhom **5b**: `[MAP] nap model GIA TRI net015` co trong log; so dong `[MAP]`
**bang** so tick `[S1] score`; `p50` cua **moi** dong `[MAP]` trong `[0.20, 0.70]`; **0** dong
`[MAP] chua co thang gia tri`. Cac cong cu (`Create order market` = 0, `Update all position` = N0,
`[LEGACY] managed` = N0, RSS < 5G) **giu nguyen**.

### 5.1 BA LENH CUA USER
```bash
scp -P 2222 -i C:\Users\pc\.ssh\id_rsa_chuyennd -r /duong/dan/deploy_242_l3 root@103.157.218.242:/root/
ssh -p 2222 -i C:\Users\pc\.ssh\id_rsa_chuyennd root@103.157.218.242 \
    'cd /root/deploy_242_l3 && bash deploy.sh && sleep 180 && bash verify.sh'
# CHI khi verify FAIL:
ssh -p 2222 -i C:\Users\pc\.ssh\id_rsa_chuyennd root@103.157.218.242 'cd /root/deploy_242_l3 && bash rollback.sh'
```

### 5.2 RAM
L4 them **mot ONNX session** (`net015`, file gap 2.9 lan file S1) => **+~80-150MB native**;
`selFeat45` ~110 KB/tick (thay moi tick); `selMapPred`/`LATEST_SEL_MAPPRED` < 50 KB.
**Khong** them phep tinh feature nao. Tong L3+L4 uoc **heap +~35MB, native +~0.15-0.25G**,
nam trong `-Xmx5g` da commit. **KHONG tang `-Xmx`**. ⚠️ Uoc tinh, chua do tren 242.

---

## 6. SHADOW ORACLE — **DA TAT TU TRUOC, L4 KHONG KHOI DONG LAI**

`health.log` bao `DOWN` (pid mat) tu **2026-09-06 19:00Z** lien tuc toi ban ghi cuoi
21:00Z. Trang thai dong bang tai luc tat: `tick_cuoi 06/09 22:00:06`, `s1_cuoi 06/09 22:03:31`,
`wouldBUY=30`, `wouldCLOSE=4`, `createOrder=0`, `errLines=0`, `ledgerRows=4`.
Cron `health.sh` **van con cai** (1 dong crontab) — moi gio ghi mot dong `DOWN`, khong ton
tai nguyen. **Khong khoi dong lai, khong go cron** (dung y de bai).

---

## 7. DIEM SHADOW KHAC SIM C3 — CON LAI SAU L4

`L2_PORT_C3` muc 5 co 9 diem. L4 **dong duoc diem 1** (truc load-bearing nhat) va **lam ro
diem 2**. Con lai:

| # | truc | trang thai sau L4 |
|---|---|---|
| ~~1~~ | ~~gia tri gate `symbolPred`~~ | 🟢 **DA DONG.** `symbolPred` = `1 − P(win)` cua `net015` da qua `build_map` — dung thang gia tri cua C3. Cong REPLAY muc 4.2/4.3. |
| ~~2~~ | ~~thu tu selector~~ | 🟢 **DA DONG HAN.** Truoc L4 shadow tinh S1 "thang" con sim di qua bins; nay live chay **dung** `build_map` nen ca hai di cung duong. |
| **3** | **vu tru live (coin co ticker) vs cot `CLOSES_1H.bin`** | 🔴 **con** — co huu. L4 do them: 23.73% dong offline khong co score S1; live khong co khai niem do. |
| **4** | **duong FEATURE 45 live vs Tool1** | 🔴 **con, va CHUA DO DUOC** (muc 3). Day la **rui ro lon nhat con lai o tang entry**. |
| **5** | **model ngoai mep train 11 thang** | 🔴 **con** — ca S1 lan net015 cutoff 2025-10. |
| **6** | **ke toan GIAY** (khong phi, khong funding, khong slippage, khong tick-size) | 🔴 **con** — nhung `mean(margin)`/equity **DA SO duoc** (L7): sim **2.498%**/leg vs so giay **3.000%->2.085%** = khop bac do lon; sai so ke toan thi chua do. `docs/experiment/L8_SIZING_PARITY_BACKLOG.md` muc 1 |
| **11** | **so giay KHONG tai lap duoc sleeve DCA / nhieu leg** (`ShadowBookC3.open` = `Map<symbol,Pos>` + `putIfAbsent` => leg 2 bi bo im lang) | 🔴 **THEM 2026-09-11 (L7).** Hai sleeve `BIG_DOWN` + `DCA_LEVEL1` = **17,291.7 / 76,428.4 = 22.6% pnl** cua backtest. Moi so cua so giay phai doc kem dieu nay. `docs/experiment/L8_SIZING_PARITY_BACKLOG.md` muc 2 |
| **7** | **exit chay trong `ShadowBookC3`**, time-stop tren duong that chi la log | ⚠️ **con** |
| **8** | **gate `p15`** (`Model_Regressor_Return15M.onnx` vs `wfo_gate_pred.csv`) | ⚠️ **con, chua chung minh dong nhat** |
| **9** | **do tre** (tick 15m + kline 1m tre ~1' + OI asof <= 2h) | ⚠️ **con** |
| **10** | **GATE ENTRY TANG 2** (`checkSignalDynamic` vs gate phang 0.008) | 🔴 **THEM 2026-09-11, LON HON CA 9 DIEM TREN CONG LAI.** Sim LUON chay gate dong `dyn_thr = 0.008*max(0.26787, symbolPred/0.15*1.28760)` (0.0172-0.0240 voi top-8), live rank-mode BO no (`DetectEntrySignal2TradeNormal:656`, `311bb29`) => chay gate PHANG 0.008. Lech **95.62%** slot tren 48 thang; **77/78** entry so giay 242 07-11/09 se bi chan neu live chay nhu sim. `docs/audit/AUDIT_GATE_DYN_PARITY.md`. 🟢 **DA SUA** trong `docs/experiment/L6_GATE_DYN_FIX.md`, roi **L7** (`docs/experiment/L7_LEAN_GATE.md`) gop not hai ban sao cong thuc ve MOT class `tradecore/EntryGate` ma ca sim lan live cung goi — `printDone.csv` byte-identical voi `X1_C3_FULL_PARITY_R`. Goi `deploy_242_l7` soan xong, **CHUA DEPLOY 242**. |

De bai du doan "chi con: universe live, ke toan giay, model train toi 2025-09/2025-10".
Do dung 3 diem **3, 6, 5**. **Nhung con them 3 diem nua** phai ghi: **4** (duong feature 45 —
chua do duoc, quan trong nhat), **7/8/9**. Khong duoc bo qua diem 4.

> **BO SUNG 2026-09-11 (audit `3a36f02`).** Bang tren truoc day THIEU **diem 10** — gate entry
> tang 2. No khong nam trong 9 diem cua `L2_PORT_C3` vi ca hai ben deu "co gate", chi khac
> NGUONG; nhung do lon thi vuot xa: no doi ~96% tap entry cua sleeve selector, tuc so giay
> 07-11/09 **khong phai C3_FULL** ma la mot chien luoc gate phang chua tung backtest.
> Do la ly do `docs/analysis/SHADOW_EVAL_20260911.md` va `docs/ops/DEV_COLLAPSE_CHECK_20260911.md` phai
> doc lai phan **nhip/so bag** (xem khung canh bao o dau hai file do).

---

## 8. TAI LAP

```bash
python3 research/pipeline/l4/build_replay_input.py            # -> /home/ubuntu/l4/{rows,x45,x9}
cd /home/ubuntu/l4/run && env NET015_MODEL_ONNX=... S1_MODEL_ONNX=... \
  java -Xmx8g -cp target/binance-java-sdk-1.2.4.jar \
  com.binance.chuyennd.research.l4.L4ReplayHarness /home/ubuntu/l4
python3 research/pipeline/l4/l4_gates.py                      # -> bang muc 4
python3 research/pipeline/l4/gen_buildmap_fixture.py <duong/dan/LiveBuildMapTest.java>
```
