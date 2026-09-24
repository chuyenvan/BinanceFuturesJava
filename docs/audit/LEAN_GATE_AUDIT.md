# LEAN_GATE_AUDIT — rut gon cong entry (gate) va ra soat lech sim<->live

> **CAP NHAT 2026-09-11**: master da doc bao cao nay va **DUYET** ban lean "giu nguyen bieu thuc,
> gop hai ban sao ve mot ham" (byte-identical DO CAU TRUC, khong rut ve `K`). Da cai dat va chung
> minh o **`docs/experiment/L7_LEAN_GATE.md`** (`printDone.csv` byte-identical voi `X1_C3_FULL_PARITY_R`).
> Muc 4.3 co **dinh chinh** (xem trong muc do). Doan duoi day GIU NGUYEN lam ban ghi thoi diem audit.

> **KET LUAN DIEU HANH: DUNG SAU PHAN A.** Rang buoc cung cua master la
> "moi thay doi phai byte-identical voi `X1_C3_FULL_PARITY_R`", va lenh giao:
> *neu floor / early-gate co bind du mot lan => DUNG sau Phan A, bao so*.
> Do tren 48 thang: **floor `AI_DYNAMIC_MIN` CO bind dung 1 lan** (muc 3.3).
> => **KHONG cai dat Phan B** (khong sua code, khong chay sim, khong dong goi L7).
> Phan 5 la thiet ke lean de xuat, **chua ap**.

Read-only. Khong sua code, khong deploy, khong SSH 242. Repo
`/home/ubuntu/src/BinanceFuturesJava` branch `module`, HEAD = `e5e8440` (L6, soan xong chua deploy).
Nguon so cho 242 lay tu `docs/runbooks/runbook_live_242_2026-08-19.md` §2/§12.2 va `docs/experiment/L1_SHADOW_C3.md`
muc 2 — **khong** SSH 242.

---

## 1. TOM TAT SO

| cau hoi | tra loi |
|---|---|
| `min symbolPred` trong **top-8** moi tick, 48 thang (140,244 moc 15m) | **0.024885** (2024-08-05 13:30 GMT+7, symId 261, pool 259) |
| phan vi cua `min-top8` | p0 = 0.024885 · p0.1 = 0.086337 · p1 = 0.173502 · p50 = 0.332989 |
| floor `AI_DYNAMIC_MIN` co bind khong (`symbolPred < 0.031206`) | **CO — dung 1 slot / ~1.12 trieu slot (tick x top-8)** |
| slot co `dyn_thr < thr_base` (`symbolPred < 0.116496`) | **1,714** (2022: 538 · 2023: 73 · 2024: 315 · 2025: 788) |
| early-hard-gate 0.008 co doi quyet dinh nao khong | **KHONG — chung minh giai tich, dung voi moi input** (muc 3.4) |
| tang 1 `maxThres` co bind trong rank-mode khong | **KHONG** — bi bo hoan toan khi `SELECTOR_RANK_TOPK>0` (muc 2.2) |
| `riskDrawdown4H` co con lam gate khong | **KHONG** — nhanh RISK/DD4H bo 2026-08-08, field xoa 2026-09-03 |
| gate co rut ve `p15 >= K x symbolPred`, `K = 0.0686720` duoc khong | **KHONG chung minh duoc byte-identical** (1 slot lech nguong). Tren du lieu hien co thi **khong doi quyet dinh nao**, nhung do la lap luan **phu thuoc du lieu**, khong phai dong nhat thuc |

---

## 2. A1 — MOI THU THAM GIA QUYET DINH VAO LENH `PREDICT_SYMBOL_TRADE`

### 2.1 SIM — `SimulatorMarketLevelTicker1MStopLoss`

| buoc | dong | lam gi | co bind trong rank-mode? |
|---|---|---|---|
| tang 1 — `maxThres` | `324-329` | `maxThres = PREDICT_SYMBOL_RATE_MAX_THRESHOLD x AI_DYNAMIC_MAX` = 0.15 x 2.14135 = **0.3212**; dem `nPass` = so coin co score <= maxThres | **KHONG.** `331-341`: `SELECTOR_RANK_TOPK>0` => lay thang K phan tu dau cua `symbol2Pred`; `nPass`/`maxThres` chi con di vao `LOG.debug` (`339-340`). `nPass` **khong** duoc doc o nhanh nao khac |
| tang 1 — chon top-K | `336-337` | `nSel = min(TOPK, pool)`, lay K phan tu dau (pool sort TANG theo score) | co — day la co che chon ung vien |
| cap-then-skip | `358-368` | `selRank++` cho MOI phan tu trong `chosenCands` (ke ca coin dang giu), roi `if (!isSymbolRunning)` | co |
| `predict == null` | `958-961` | reject (parity #10 voi live) | co |
| **gate tang 2** | `962-972` | `levelChange == PREDICT_SYMBOL_TRADE && !GATE_DYN_BYPASS` => `checkSignalDynamic(predict, symbolPred)`; nguoc lai `checkSignal(predict)` | **CO — day la cong quyet dinh** |
| book cap | `1020-1038` | `BOOK_MAX_OPEN` / `BOOK_MAX_NOTIONAL_PCT` | **khong** — ca hai = 0 (khong khai) => `BOOK_CAP_ON=false` |
| budget | `1062-1081` | `managerBudget(...)` + `tierMultiplier` | co |
| DCA grid sizing | `1089-1105` | `budget *= gridLegWeightRatio(legIdx)` | co (`DCA_GRID_ENABLED=true`) |

### 2.2 LIVE — `DetectEntrySignal2TradeNormal`

| buoc | dong | lam gi | co bind trong rank-mode? |
|---|---|---|---|
| tang 1 — `maxThres` | `625, 639-644` | loc `preds[0] > maxThres` -> khong vao `sortedCandidates` | **KHONG** — `340` chon `selPool = selectorRankPool` (pool DAY DU, ghi o `631`) khi `TOPK>0` |
| `EntryPoolGate` + `LiveBuildMap` | `348-365` | `LiveProfileC3.on()`: `buildS1Pool` -> `EntryPoolGate.usable/choose`; `buildValueMap` (net015) -> khong co map thi `selPool` rong | **live-only** (sim khong co) |
| `LegacySymbols` skip | `376-379` | `continue` **truoc** khi dem rank => legacy khong chiem slot | **live-only** |
| cap-then-skip | `380-385` | `rank++` roi `if (ticker==null \|\| symbol2Pos.containsKey) continue` | co — **khop sim** (sua o `311bb29`) |
| log `[GATE-DYN]` | `386-409` | thuan log, `dynThreshold(...)` tinh lai PURE | khong doi quyet dinh |
| `prediction == null` | `665-668` | return | co |
| **gate tang 2** | `685-686` | `aiRejectFilter.entryGate(predict, symbolPred, levelChange == PREDICT_SYMBOL_TRADE)` (L6) | **CO — cong quyet dinh, nay dung chung ham voi y nghia cua sim** |
| shadow book + sizing | `727-748` | `balanceBasic = book.equityNow()`, `marginRunning = book.marginRunning()`, cap 4.5% equity | **live-only** |
| tier | `761-773` | `budget *= tierMultiplier` | co |

### 2.3 Bang tham so — gia tri THAT

| tham so | gia tri hieu dung | nguon | bind rank-mode | dung o |
|---|---|---|---|---|
| `MIN_MOMENTUM_15M` | **0.008** | `x1_c3_full.properties:32` (`SIM_MIN_MOMENTUM_15M`); 242 `conf/env.sh:29` cung 0.008. Default Java `Configs:400` = 0.02284 (khong dung o dau) | CO | sim + live |
| `AI_DYNAMIC_MULTIPLIER` | **1.28760** | `Configs.java:340` (khong profile/env nao khai `SIM_AI_DYNAMIC_MULTIPLIER`) | CO | sim + live |
| `AI_DYNAMIC_MIN` | **0.26787** | `Configs.java:341` | **1 slot / 48 thang** (muc 3.3) | sim + live |
| `AI_DYNAMIC_MAX` | 2.14135 | `Configs.java:342` | **KHONG** (chi tang 1, ma tang 1 bi bo) | sim + live (tang 1) + 6 tool HPO/validation |
| `PREDICT_SYMBOL_RATE_MAX_THRESHOLD` | **0.15** | `Configs.java:367` | CO (mau so cua scale) | sim + live + 8 tool HPO/validation |
| `SELECTOR_RANK_TOPK` | **8** | profile:9; 242 `conf/env.sh` §12.2 = 8 (truoc do 5) | CO | sim + live |
| `GateRollingThreshold` | **OFF** | khong noi nao khai `SIM_GATE_ROLLING_PCT` => `thres15M()` tra `MIN_MOMENTUM_15M` | khong | sim-only |
| `GATE_DYN_BYPASS` | **false** | `SIM_GATE_DYN_BYPASS` khong khai (`Configs:472`) | khong | sim-only |
| `riskDrawdown4H` | **khong lam gate** | `AIRejectFilter:127-129` — nhanh RISK bo 2026-08-08, field `HARD_RISK_LIMIT_4H` xoa 2026-09-03 (`5f40a90`) | khong | chi con di vao `AiPredictionData` + log |
| `TS_CAP_STRONG_RANK` | 0 (TAT) | default | khong | sim + live deu roi ve duong pNoPump |

---

## 3. A2 — CHUNG MINH RUT GON (do that tren 48 thang)

### 3.1 Cong thuc hien hanh
`AIRejectFilter.checkSignalDynamic` (70-92):
```
neu p15 < thr_base VA sp > RATE_MAX            -> REJECT (early-hard-gate)
scale   = max(AI_DYNAMIC_MIN, sp/RATE_MAX * AI_DYNAMIC_MULTIPLIER)
dyn_thr = thr_base * scale                      (CHI CAN DUOI, khong tran)
PASS   <=> p15 >= dyn_thr
```
Voi `thr_base=0.008, AI_DYNAMIC_MIN=0.26787, RATE_MAX=0.15, MULT=1.28760`:

| dai | cong thuc | diem chuyen |
|---|---|---|
| ve 2 (tuyen tinh) thang | `sp > AI_DYNAMIC_MIN x RATE_MAX / MULT` | **sp > 0.031206** |
| `dyn_thr >= thr_base` | `sp >= RATE_MAX / MULT` | **sp >= 0.116496** |
| dang rut gon neu ve 2 luon thang | `p15 >= K x sp`, `K = thr_base x MULT / RATE_MAX` | **K = 0.0686720** |

### 3.2 Nguon do
`predwf_map_s1a2_x1/predict_wf_*.bin` (16 file, dtype
`[("ts",">i8"),("sym",">i2"),("p0",">f4"),("p1",">f4"),("p2",">f4"),("p3",">f4")]`),
`symbolPred = 1 - p0` — **quy uoc xac nhan tai `WfoDataset.java:245-249`**
(`horizonIdx=0` -> `pwin = p4` = truong float dau tien; `score = 1.0f - pwin` "DAO DAU").
Cat `ts < 1767200400000` (= `HoldoutSeal` 2026-01-01 GMT+7). Bo ban ghi `p0` NaN (0 ban ghi).
Ket qua: **35,806,379 ban ghi**, **140,244 moc 15m**. Moi moc: sort TANG, lay 8 phan tu dau
(= dung `chosenCands` cua `Simulator:336-337`).

### 3.3 Ket qua — floor CO bind (1 lan)

| nam | so moc 15m | `min symbolPred` trong top-8 | slot `< 0.031206` (floor bind) | slot `< 0.116496` (`dyn_thr < thr_base`) |
|---|---|---|---|---|
| 2022 | 35,036 | 0.036810 | 0 | 538 |
| 2023 | 35,039 | 0.072333 | 0 | 73 |
| 2024 | 35,130 | **0.024885** | **1** | 315 |
| 2025 | 35,039 | 0.044306 | 0 | 788 |
| **tong** | **140,244** | **0.024885** | **1** | **1,714** |

**Slot duy nhat lam floor bind**: tick `1722839400000` = **2024-08-05 13:30 GMT+7** (ngay sap thi truong),
file `predict_wf_20240701.bin`, pool 259 coin, `symId=261`, `symbolPred = 0.024885`.
- `dyn_thr` (hien hanh, floor thang) = `0.008 x 0.26787` = **0.0021430**
- `K x symbolPred` (dang rut gon)      = **0.0017089**
- lech nguong = **0.0004340** — dang rut gon **LONG hon**

Rank 2..8 cua chinh tick do: `symbolPred` 0.031258..0.033669, `delta = 0.0000000` (ve 2 thang, hai dang trung khop bit-for-bit).

**Slot do co doi quyet dinh khong? KHONG.** `claudedata/wfo_gate_pred.csv` cho 15 phut ma moc 15m
nay forward-fill sang (`1722839400000..1722840240000`): `predReturn15M` = **0.02791 .. 0.04533**
(min 0.02791). Ca hai nguong (0.0021430 va 0.0017089) deu **thap hon 13 lan** => ca hai deu PASS
o ca 15 phut. Nghia la tren du lieu hien co, hai dang gate **cho cung mot tap quyet dinh**.

> **Nhung day KHONG phai dong nhat thuc.** No la khang dinh *"vung nguong lech
> `[0.0017089, 0.0021430)` khong bao gio bi `p15` roi trung"* — dung voi bins nay + gate csv nay,
> **khong** dung noi chung. Doi bins (S1 remap moi), doi `MIN_MOMENTUM_15M`, hay chay profile khac
> (`x1_gd88/92/96` doi `MIN_MOMENTUM_15M`; `b4_rg*` bat `GateRollingThreshold` lam `thr_base` thanh
> ham cua thoi gian) la lap luan sap. Vi vay theo rang buoc cung cua master: **KHONG rut ve `K` don**.

### 3.4 Early-hard-gate 0.008 — chung minh GIAI TICH la thua

Early fire <=> `p15 < thr_base` VA `sp > RATE_MAX`. Khi `sp > RATE_MAX = 0.15`:
```
scale   = max(0.26787, sp/0.15 x 1.28760) > max(0.26787, 1.28760) = 1.28760
dyn_thr = thr_base x scale > 1.28760 x thr_base > thr_base > p15
```
=> nhanh `evaluate` phia duoi **cung tra REJECT**. Dung voi **moi** `p15`, **moi** `sp`, **moi**
`thr_base > 0` — khong can du lieu. Vay early-hard-gate la **shortcut hieu nang thuan tuy**:
bo no **khong doi mot quyet dinh nao**.

Hai thu no con lam va phai xu ly neu bo:
1. `reason` string khac (`"DANGER: pred 15m ..."` vs `"BAD MOMENTUM: ..."`) — chi vao log,
   khong vao `printDone.csv`.
2. counter `earlyHardGateReject` (`AIRejectFilter:31`) — **chi** dung cho bao cao ablation;
   `mom15RejectCount` tang dung 1 lan o ca hai duong nen **khong doi**.

### 3.5 Tang 1 `maxThres` trong rank-mode — XAC NHAN chet
`Simulator:331-345`: khi `SELECTOR_RANK_TOPK > 0` thi `chosenCands` = K phan tu dau, **khong**
tham chieu `nPass`/`maxThres`. Hai bien do chi con xuat hien o `LOG.debug` (`339-340`).
Live tuong duong: `340` chon `selectorRankPool` (pool truoc loc `maxThres`).
`grep` xac nhan `nPass` khong co reader nao khac trong file.
**Nhung `AI_DYNAMIC_MAX` + `PREDICT_SYMBOL_RATE_MAX_THRESHOLD` KHONG xoa duoc**: con
**14 reader** ngoai gate (`DumpConfig`, `WFORunner`, `StrategyWfoTask`, `SensitivityTool`,
`AblationClusterTool`, `BackTestEngineCombined`, `RunOptimization*`, `RunWorkerKaggle`,
`RunFundingMonotonicity`, `ValidateBrakeDynamic`, `ValidateFundingOOS`, `CompareFundingSetV5V6`,
`CompareFundingModels`, `BenchmarkSpeedTest`). Xem muc 5.3.

### 3.6 `riskDrawdown4H`
Khong con la gate. `AIRejectFilter.evaluate` (130-138) chi con nhanh MOM15; `setConfig(risk, min15m)`
giu tham so `risk` chi de khong vo 3 call-site HPO (`120-124`). `predRisk4H` con chay vao
`AiPredictionData` va dong log `[PREDICT fail]` cua live — **khong quyet dinh gi**.

---

## 4. A3 — LECH / PHUC TAP KHAC GIUA SIM VA LIVE

Muc do: 🔴 doi tap lenh hoac doi size >2x · ⚠️ doi hanh vi nhung chua do duoc · 🟢 da khop.

### 4.1 Nhanh re khac nhau giua hai file

| # | diem | sim | live | muc |
|---|---|---|---|---|
| i.1 | `SELECTOR_RANK_TOPK` o **gate tang 2** | khong he co dieu kien (`Simulator:962-972`) | truoc L6 co `&& TOPK<=0` (`311bb29`); **L6 da bo**, nay goi `AIRejectFilter.entryGate` (`:685-686`) | 🟢 **da khop o HEAD `e5e8440`** (chua deploy 242) |
| i.2 | `SELECTOR_RANK_TOPK` o **tang 1** | `331-345` bo `maxThres` | `340` doi sang `selectorRankPool` | 🟢 khop |
| i.3 | `LiveProfileC3.on()` | **khong ton tai** trong sim | 8 diem re trong `DetectEntrySignal2TradeNormal` (`100, 348, 633, 727, 745, 807, 812`) + `BinanceOrderTradingManager` (`225, 256, 441`) | ⚠️ live-only theo thiet ke (so giay), nhung la 8 duong ma sim **khong mo phong** |
| i.4 | `symbolPred == null` | `checkSignalDynamic` tu fallback `checkSignal` (`:71-73`) | `entryGate` roi thang `checkSignal` (`:112-115`) | 🟢 cung ket qua |
| i.5 | `EntryPoolGate` / `LiveBuildMap` | **khong co** | `:348-365` — khong co score S1 / khong co value-map => BO TICK | ⚠️ **live-only**: sim khong bao gio "bo tick", live bo. Anh huong tan suat, khong do duoc offline |
| i.6 | gia tri `symbolPred` | bins `predwf_map_s1a2_x1` (`1 - p0` cua G015x26 remap S1) | rank-mode + `LiveProfileC3` => `selMapPred` (net015 quantile-map); profile tat => `preds[0]` cua `Funding_Classifier_Final.onnx` | 🔴 **hai thang do khac nhau** (L4 muc 7 diem 1 bao "da dong" o **thu tu**, nhung **hieu chuan gia tri** thi ledger cho 0.065-0.144 con bins top-8 median 0.31-0.50) |

### 4.2 Trailing / arm / giveback / time-stop

| truc | sim | live (`ShadowBookC3`) | muc |
|---|---|---|---|
| ham gap | `OrderTargetInfoTest.trailRate():365-373` -> `calRateLossDynamicBuyPNoPump(peak, pnp, 0.29)`; `TS_CAP_STRONG_RANK=0` nen khong di duong rank | `ShadowBookC3:234` -> **cung ham** `calRateLossDynamicBuyPNoPump(peak, pnp, tsPnoPumpWeakThr())` | 🟢 **cung cong thuc** |
| cap STRONG/WEAK | `TS_MAX_GAP=0.08` / `TS_MAX_GAP_WEAK=0.03`, ban le `symbolPred < 0.29` = STRONG | y het | 🟢 khop tham so |
| **nhung dau vao ban le** | `symbolPred` = score bins (top-8 median 0.31-0.50 => **da so WEAK**) | `symbolPred` = net015 map (ledger do 0.065-0.144 => **da so STRONG**) | 🔴 **cung ham, khac ket qua**: ban le 0.29 phan loai nguoc nhau giua hai ben |
| arm | `RATE_PROFIT_STOP_MARKET = 0.07` (profile:35) | `LiveProfileC3.ARM_RATE = 0.07` (so giay); **vi the LEGACY that van 0.05** | 🟢 so giay khop; legacy co chu dich khac |
| ratchet | lien tuc (dead-zone da go o `5f40a90`) | so giay lien tuc; **duong THAT co `LIVE_RATCHET_DEADZONE_MULT=5.21847`** (`BinanceOrderTradingManager:425,469`) | 🔴 cho vi the that (legacy) — **khac co che, khong cau hinh duoc** |
| giveback | `gap = min(peak x TS_GIVEBACK_RATIO(0.5), maxGap)`, lam tron `step=0.005` (`TradeUtils:40-46`) | cung ham | 🟢 |
| **time-stop 168h** | `LOSER_TIME_STOP_HOURS=168` (profile:37), cat cum **chua arm** | `ShadowBookC3:258-264` **CO** (`LiveProfileC3.TIME_STOP_HOURS=168`) tren so giay; **duong THAT khong co** | 🟢 so giay da co (L1 muc 7 diem "sim-only" **da cu**); 🔴 van sim-only doi voi vi the that |
| avg entry khi DCA | sim `mergeOrder` -> `priceEntry` = VWAP; `SIM_FIX_B1` chep `symbolPred` | `ShadowBookC3.Pos` **khong co khai niem DCA** (grep: 0 nhanh DCA/BIG_DOWN trong file) | 🔴 xem 4.4 |

### 4.3 Sizing — CUNG ham `managerBudget`, KHAC hau to

```
managerBudget = balanceBasic x F_BASE(0.03) x throttle / dcaGridTotalWeight()
                throttle = clamp(1 - (marginRunning/balanceBasic)/U_MAX(0.60), 0, 1)
```
| | SIM (`x1_c3_full`) | LIVE (so giay C3) |
|---|---|---|
| `balanceBasic` | `BudgetManagerSimple.equityNow()` (compound, `SIM_FIX_B3=true`, `Simulator:1068-1070`) | `ShadowBookC3.equityNow()` = `PAPER_EQUITY 35000 + realized + MtM` (`DetectEntry...:740`) |
| `dcaGridTotalWeight()` | `DCA_GRID_WEIGHTS=1,1,3,8` (profile:51) => **13** | env-phu-thuoc: 242 khong dat key => default `1,1,3,8` = **13**; shadow Oracle dat khac (do tu ledger: mean margin **809.9** USDT / leg, n=4 => mau so ~**1**) |
| tier | `TIER_FLAT=1` (profile:44) => **1.0** | 242/shadow **khong dat** `TIER_FLAT` => tier **1.2/1.0/0.5 CO chay** (`:761-773`) |
| **`x gridLegWeightRatio(legIdx)`** | **CO** (`Simulator:1089-1105`), leg0 = `w0/sum x DCA_GRID_SCALE` = `1/13 x 19.5` = **1.5** | **KHONG CO** — duong live khong goi `DcaUtils.gridLegWeightRatio` o bat ky dong nao |
| cap tran | **khong co** | `SIZE_CAP_OF_EQUITY = 0.045` x equity (`:746-747`) |

> 🔴 **DINH CHINH 2026-09-11 (L7, do bang so — xem `docs/experiment/L8_SIZING_PARITY_BACKLOG.md` muc 1.2).**
> Uoc luong "~16x" duoi day **SAI**: no suy tu cong thuc chu khong do. Do that:
> sim **2.498%** equity/leg (2,266 leg, 48 thang, `printDone.csv`) vs live so giay
> **3.000% -> 2.085%** (`docs/experiment/L2_PORT_C3.md` muc 4.1) => **~1.0-1.2x, KHOP bac do lon**.
> Nhung phep do lai **khong khop chinh cong thuc duoi day** (cong thuc cho 0.346%, do duoc
> 2.498% — lech ~7.2 lan) => **duong sizing cua sim chua ai doc dung**. Doan duoi giu nguyen
> lam ban ghi cua suy dien SAI, de lan sau khong ai lap lai kieu ket luan tu doc code.

=> **leg dau**: sim = `equity x 0.03 x throttle x 1.5` ; live = `equity x 0.03 x throttle x tier / sum(w)`.
Voi 242 (`sum(w)=13`, tier<=1.2) ti so **sim / live = 1.5 / 0.0923 = ~16x**.
🔴 **Day la lech sizing bac mot con so, khong phai tinh chinh.** `DCA_GRID_SCALE=19.5` la
**sim-only** (L1 muc 3 da ghi "duong live KHONG BAO GIO goi ham nay => vo hieu tren live") nhung
he qua dinh luong thi chua noi ai ghi. Con `x1_c3_full` la profile **da duoc dung de ra moi
quyet dinh 48 thang**, nen "sim va live cung sizing" la **sai**.

### 4.4 DCA / BIG_DOWN

| | sim `x1_c3_full` | live so giay |
|---|---|---|
| `DCA_LEVEL1` (nhip `isDcaAlt`) | **CO** — `SIM_DCA_TRIGGER` khong khai => `HOLD_DCA_ON=false` => nhanh `Simulator:306-319` **chay** | `DetectEntry...:303,324` co goi `createOrderBuyRequest(..., DCA_LEVEL1, ...)`; nhung `ShadowBookC3.openPos` **khong co khai niem leg/cum** — `open` la `Map<symbol,Pos>` va `putIfAbsent` nen leg thu 2 tren cung symbol **bi bo im lang** |
| `BIG_DOWN` | **CO** (`SELECTOR_ONLY_ENTRY=0`) | leg BIG_DOWN vao qua `:289` roi cung `putIfAbsent` |
| `DCA_GRID_ENABLED` | `true`, weights 1,1,3,8, scale 19.5 | khong ap (4.3) |

🔴 **So giay KHONG tai lap duoc sleeve DCA cua backtest**: khong nhoi leg 2/3/4 tren cung coin,
khong VWAP lai gia von, khong ap ti trong 1:1:3:8. Neu sleeve DCA dong gop ~23% pnl cua backtest
(con so nay cua `HOLDDCA §0`, **chua kiem lai trong audit nay** — phai do bang `printDone` loc
`level=DCA_LEVEL1` truoc khi trich dan) thi so giay thieu dung phan do. **Can mot phep do rieng**,
khong ket luan bang niem tin.

### 4.5 Cap-then-skip — 🟢 da khop
Sim `358-368`: `selRank++` cho MOI phan tu trong top-K roi moi `isSymbolRunning` skip.
Live `380-385`: `rank++` roi `symbol2Pos.containsKey` skip; break tai `rank >= TOPK`.
Khac duy nhat: live `LegacySymbols` `continue` **truoc** `rank++` (legacy khong chiem slot) — co chu dich, live-only.

### 4.6 Key lach cong `Cfg` — 🟢 sach
`tools/check_cfg_gateway.sh` chay: **OK** (muc 7). Ngoai le hop le da khai trong `INFRA_KEYS`:
`SIM_END_DATE`, `SHADOW_NO_PUSH`, `OI_STALE_HALT*`.
Luu y rieng: `SELECTOR_RANK_TOPK` la `static final` doc luc nap lop (`Configs:374-375`) =>
**env-only, khong doi duoc trong JVM** (`CpcvCellTask:36` da ghi canh bao nay) — khong phai vi pham
nhung la mot cai bay da co nguoi vap.

### 4.7 Co che TRO con trong cay sau DOT 2 (`5f40a90`)

| co che | key | trang thai that | commit tao | doc dong |
|---|---|---|---|---|
| `GateRollingThreshold` (198 dong) + `thres15M` re nhanh | `SIM_GATE_ROLLING_PCT`, `SIM_GATE_ROLLING_DAYS` | **TRO** — khong profile/env nao khai => `isOn()=false`; da bi xoa o `5f40a90` roi **quay lai** o B4 (`a0c7ad6`) | `c1785b9` (pre-reg `a0c7ad6`) | `docs/result/B4_RESULT.md` (B4 dong), `docs/audit/AUDIT_GATEDYN_GD92.md` |
| tran so | `SIM_MAX_OPEN_POSITIONS`, `SIM_MAX_OPEN_NOTIONAL_PCT` + `TickDecisionLog.D_BOOK_CAP` | **TRO** — ca hai mac dinh 0 => `BOOK_CAP_ON=false`; nhanh `Simulator:1011-1040` chet | `573dd1f` | `docs/` ket qua BOOKCAP = **NULL** |
| HOLDDCA | `SIM_DCA_TRIGGER`, `SIM_DCA_MIN_DROP`, `SIM_DCA_COOLDOWN_H`, `SIM_DCA_MAX_LEGS`, `SIM_ENTRY_FRACTION` + log `[DCA13]` | **TRO** — `SIM_DCA_TRIGGER` rong => `HOLD_DCA_ON=false`; 3 profile `x1_holddca_*` deu THUA | `f10f6ca` | `f10f6ca` "0/3 PASS, ca ba THUA ro" |
| FLATGATE | `SIM_GATE_DYN_BYPASS` + nhanh `Simulator:964-968` | **TRO** — thi nghiem da dong | `ee00475` | `docs/result/RESULT_FLATGATE.md` |
| `LIVE_LOSER_TIME_STOP_HOURS` | — | **DA XOA ROI** — `grep` toan repo: 0 hit | — | `5f40a90` |

Profile di kem co the dua vao `profiles/archive/`: `b4_rg95`, `b4_rg95w180`, `b4_rg97`,
`x1_gd88/92/96`, `x1_gd2_G9*W*` (6 file), `x1_c3_full_cap12/cap16/not40`,
`x1_holddca_e25/e50/e100`, `x1_c3_full_flatgate` — **19 file**. Docs ket qua GIU nguyen.

---

## 5. A4 — THIET KE LEAN DE XUAT (**CHUA AP**, cho master chot)

### 5.1 Vi sao KHONG lam duoc "1 key `GATE_K`"
Dang `p15 >= K x sp` sai o hai cho:
1. **Floor bind 1 lan** (muc 3.3) => khong phai dong nhat thuc.
2. **Ke ca khi floor khong bind**, thu tu nhan doi: hien hanh tinh
   `base x ((sp/RATE_MAX) x MULT)`, dang rut gon tinh `((base x MULT)/RATE_MAX) x sp`.
   Nhan `float` **khong ket hop** => hai ve co the lech 1 ULP. Voi gate so sanh `>=` thi 1 ULP
   du de doi mot quyet dinh. **Khong duoc dung "chay thu thay khop" lam bang chung** — ma phai
   giu nguyen bieu thuc.

### 5.2 Dang lean AN TOAN (byte-identical **do cau truc**, khong do may man)
Giu nguyen bieu thuc, chi bo **ban sao** va **nhanh chet**. Mot ham, hai call-site.

```java
// AIRejectFilter — MOT cho duy nhat tinh nguong tang 2
public static float dynThreshold(AiPredictionData p, Float symbolPred) {
    float base = thres15M(p);                                  // = Configs.MIN_MOMENTUM_15M
    if (symbolPred == null) return base;
    float scale = (symbolPred / Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD)
                * Configs.AI_DYNAMIC_MULTIPLIER;               // GIU NGUYEN thu tu nhan
    return base * Math.max(Configs.AI_DYNAMIC_MIN, scale);
}
// cong duy nhat — sim va live cung goi
public FilterResult entryGate(AiPredictionData p, Float symbolPred, boolean predictSymbolTrade) {
    float thr = (predictSymbolTrade && symbolPred != null) ? dynThreshold(p, symbolPred) : thres15M(p);
    return evaluate(p.predReturn15M, thr);
}
```
Xoa theo do:
- `checkSignalDynamic` (ban sao thu 2 cua cung cong thuc) va **nhanh early-hard-gate** ben trong
  no — da chung minh giai tich la thua (muc 3.4). Counter `earlyHardGateReject` xoa kem.
- `checkSignal` chi con la `evaluate(p15, thres15M(p))` — giu vi 4 caller HPO dung.
- **Call-site sim** `Simulator:962-972` -> 1 dong `entryGate(predict, symbolPred, levelChange == PREDICT_SYMBOL_TRADE)`;
  **call-site live** `DetectEntry...:685-686` da o dang do tu L6.
- `thres15M()` bo re nhanh rolling -> tra thang `Configs.MIN_MOMENTUM_15M`.

**Ten key KHONG doi** => `conf/env.sh` tren 242 **khong phai sua mot dong**. Day la ly do chon
phuong an nay thay vi dat key moi `GATE_K`: dat key moi buoc `deploy.sh` phai sua `env.sh`
(them mot cua so rui ro cau hinh tren may dang giu tien that), doi lai chi de bot 2 dong Java.

### 5.3 Cai KHONG lean duoc
| thu | vi sao giu |
|---|---|
| `PREDICT_SYMBOL_RATE_MAX_THRESHOLD`, `AI_DYNAMIC_MULTIPLIER`, `AI_DYNAMIC_MIN` | la **ba con so cua gate**; gop lai = doi thu tu nhan = co the doi bit (5.1) |
| `AI_DYNAMIC_MAX` | tang 1 chet trong rank-mode, **nhung** con 14 reader o HPO/validation (muc 3.5). Xoa = vo 14 file khong lien quan gate |
| tang 1 `maxThres`/`nPass` o `Simulator:324-329` | co the xoa (chi con `LOG.debug` doc) — **nhung** phai xoa dong bo voi `DetectEntry...:625,639-644` cua live, va do la nhanh `TOPK<=0` van song. Khuyen nghi: **giu, them assert** thay vi xoa |
| `GateRollingThreshold` | **xoa duoc** — quyet dinh nay da duoc `docs/result/B4_RESULT.md` §6 dat len ban master tu truoc va chua tra loi |

### 5.4 Du kien bot duoc (neu master duyet)

| nhom | xoa | dong (uoc) | key |
|---|---|---|---|
| gate tang 2 gop ban sao + bo early-gate | `checkSignalDynamic`, `earlyHardGateReject`, nhanh `if/else` o `Simulator:962-972` | ~45 | 0 |
| `GATE_DYN_BYPASS` (FLATGATE xong) | `Configs:464-472` + `Simulator:964-968` | ~14 | **1** |
| `GateRollingThreshold` (B4 dong) | ca class + 2 `init` + re nhanh `thres15M` | ~155 | **2** |
| book cap (BOOKCAP NULL) | `Configs:303-309`, `Simulator:1011-1040`, `:517`, `TickDecisionLog.D_BOOK_CAP` | ~45 | **2** |
| HOLDDCA (0/3 PASS) | `Configs:315-330`, `DcaUtils.shouldDcaHold` + `DcaProcessor:36`, `Simulator:99,306-319,507-511,1097-1098,1142-1147` | ~95 | **5** |
| profile thi nghiem -> `profiles/archive/` | 19 file | — | — |
| **tong** | | **~355 dong, 1 class** | **10 key** |

Sau do: `docs/ops/CONFIG_FIELD_MAP.md` sinh lai (cach cua `4dd3b04`), `docs/experiment/L4_LIVE_BUILDMAP.md` §7
va `docs/runbooks/AGENT_RUNBOOK.md` muc 0 them cau "gate = mot ham `entryGate`, dung chung sim+live".

### 5.5 Cong parity BAT BUOC truoc khi coi la xong (chua chay)
1. `tools/check_cfg_gateway.sh` OK · `mvn -o test` toan bo PASS (118 test hien tai; thay
   `GateDynEntryTest` bang `EntryGateTest`, giu 0.30/0.012 REJECT + 0.30/0.025 PASS, **them bien
   `symbolPred = 0.0313` va `0.024885`** = dung slot floor-bind cua muc 3.3).
2. Sim `x1_c3_full.properties` -> `devrun/X1_C3_FULL_LEAN`; `cmp` phan sau header voi
   `X1_C3_FULL_PARITY_R` phai **rc=0**, `md5sum printDone.csv` = `2478e90d4e6147bf4cc64f75967ef47d`,
   bo header = `e13bc39e...`, `b:111428`, 2,266 lenh.
3. FAIL => tim nguyen nhan toi da 2 vong; **cam** "sua cho khop" bang cach them tham so; khong
   khop => revert.

---

## 6. VIEC CHUA LAM / GIOI HAN CUA AUDIT NAY

1. **Khong chay sim, khong sua mot dong code nao.** Repo sach ngoai file doc nay.
2. Muc 3 do **offline** tren bins + `wfo_gate_pred.csv`: la ty le **slot co hoi**, khong phai ty le
   lenh. Ty le lenh chi do duoc bang `TickDecisionLog`.
3. Muc 4.3 (sizing ~16x) suy tu **doc code + 4 dong ledger shadow Oracle**, chua doi chieu bang
   `mean(margin)` cua `printDone.csv` vs ledger 242 (agent khong SSH 242). **Phai do lai truoc khi
   dung lam co so quyet dinh.**
4. Muc 4.4 (sleeve DCA cua so giay) suy tu cau truc `ShadowBookC3.open` (`Map<symbol,Pos>` +
   `putIfAbsent`). Con so "23% pnl" lay tu `HOLDDCA §0` **chua kiem lai** trong audit nay.
5. Khong danh gia gate nao **tot hon** — `docs/result/RESULT_FLATGATE.md` da tra loi cau do
   (`d CAGR = -61.08 pp`, CI95 `[-85.76,-32.82]`, vo rang buoc cung 4/4 nam).

---

## 7. TAI LAP

```bash
cd /home/ubuntu/src/BinanceFuturesJava
# muc 3.3 — quet 48 thang bins (~40s)
python3 research/analysis/lean_gate_floor_scan.py
# muc 3.3 — tick floor-bind
python3 research/analysis/lean_gate_floor_scan.py --tick 1722839400000
# p15 tai 15 phut cua tick do
awk -F, '$1>=1722839400000 && $1<1722840300000' /home/ubuntu/claudedata/wfo_gate_pred.csv
# muc 2 — code
sed -n '324,345p;358,370p;958,975p' src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java
sed -n '619,646p;659,710p;720,750p' src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java
sed -n '39,116p' src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/AIRejectFilter.java
sed -n '245,250p' src/main/java/com/binance/chuyennd/ai_ml/wfo/framework/WfoDataset.java
# muc 4.7 — co tro
grep -rn "GateRollingThreshold\|BOOK_MAX_OPEN\|HOLD_DCA_ON\|GATE_DYN_BYPASS" --include=*.java src
tools/check_cfg_gateway.sh
```
Tham so tra nhanh: `Configs.java:186-190,254-255,284-292,303-330,340-342,367,374-375,400,464-472`;
`profiles/x1_c3_full.properties:9,32,37,43-44,50-51`; 242 `conf/env.sh` qua
`docs/runbooks/runbook_live_242_2026-08-19.md` §2 + §12.2.
