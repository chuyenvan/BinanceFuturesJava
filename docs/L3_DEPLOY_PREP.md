# L3_DEPLOY_PREP — co lap LEGACY + goi deploy 242 (**CHUA DEPLOY**)

Ngay 2026-09-06. Tiep noi `docs/L2_PORT_C3.md`. **Agent KHONG SSH toi 242 trong dot nay**
(khong doc, khong ghi). Moi thu lam tren Oracle; deploy/restart la viec cua user.

Quyet dinh cua user: **mot JVM** tren 242 chay `LIVE_PROFILE=c3_shadow`, trong do
(i) 66 vi the THAT cu tiep tuc dong THAT theo duong **HEAD**, (ii) so giay C3 chay song song,
khong lenh that moi. 66 symbol do thanh **symbol dac biet LEGACY** de hai duong khong trung nhau.

---

## 0. RUI RO TRUOC — 6 dieu

1. 🔴 **Toan bo cong hoi quy cua L3 la UNIT TEST, chua chay tren 242 mot giay nao.** Bang chung
   duy nhat ve hanh vi that hien co la instance shadow tren Oracle (L2 muc 4.1), noi **khong co
   vi the that nao** — tuc nhanh LEGACY **chua tung chay that**. `verify.sh` la lop chan thu hai.
2. 🔴 **`TS_GIVEBACK_RATIO` la truc DUNG CHUNG.** `trailFromCap` (dung boi ca `tsGap` cua duong
   dong THAT lan `ShadowBookC3.trailRate` cua so giay) doc `Configs.TS_GIVEBACK_RATIO`. Khong co
   cach tach hai duong o truc nay bang env. Vi vay `env.sh.new` **KHONG dat** key nay: so giay
   242 se dung dung gia tri ma 242 dang dung. Neu `config.properties` cua 242 dat khac 0.5 thi
   so giay 242 **khac** shadow Oracle o truc nay. **Chua kiem duoc (khong SSH 242).**
3. 🔴 **Sizing so giay tren 242 se KHAC shadow Oracle ~13 lan** neu khong bat them 2 key.
   Oracle dat `DCA_GRID_WEIGHTS=1,0,0,0` (ladder=1) va `TIER_FLAT=1`; 242 khong co =>
   `budget = equity x 0.03 x throttle / 13` va con nhan tier 1.2/1.0/0.5. Hai key nay **chi**
   vao duong sizing ENTRY (`managerBudget` / `CoinRankManager`) — entry that da bi chan nen
   **khong the** cham duong dong legacy — nhung chung la **tham so giao dich**, agent khong tu
   bat. Da de **san, dang comment** trong `env.sh.new`. **Can user quyet.**
4. ⚠️ **`SELECTOR_RANK_TOPK` 5 -> 8 la thay doi tren duong live**, khong chi so giay. No khong
   cham duong dong vi the (`tsGap` dung `pNoPump`, khong dung rank), nhung no doi tap coin duoc
   xet moi tick. Voi entry that bi chan thi anh huong that = 0.
5. ⚠️ **Model S1 ngoai mep train 11 thang** (cutoff 2025-10, chay forward 2026-09) —
   L2 muc 5 diem 5, khong go duoc trong dot nay.
6. ⚠️ **RAM 242 chat**: box 7G, JVM `-Xms5g -Xmx5g`, `free` 0G / available 2G, swap 7G.
   Uoc tinh o muc 4. **KHONG de xuat tang `-Xmx`.**

---

## 1. VIEC 1 — CODE CO LAP LEGACY

### 1.1 Lop moi `LegacySymbols`

`src/main/java/com/binance/chuyennd/tradecore/selector/LegacySymbols.java` (158 dong).

| mat | cach lam |
|---|---|
| **dinh nghia** | `LEGACY = (vi the THAT doc tu Binance) \ (so GIAY)` — ham thuan `compute(real, paper)` |
| **nguon** | reconcile trong `BinanceOrderTradingManager.updatePositionInfo()`, ngay sau khi swap `symbol2Pos` (chay moi phut o giay thu 10 + mot lan luc khoi dong) |
| **tu thu hep** | vi the that dong -> khong con trong `getAllPositionInfos()` -> roi khoi tap ngay tick sau |
| **persist** | `run/legacy_symbols.csv` (cwd = `/home/chuyennd/java/v_t_m`), ghi khi tap DOI, nap lai luc khoi dong — `ThreadAutoRestartProgram` restart JVM moi 4h |
| **log** | `[LEGACY] managed N: SYM1,SYM2,...` **moi tick** |
| **co TAT** | `isLegacySymbol()` tra `false` NGAY khi `LiveProfileC3.on()==false` — khong doc dia, khong tao file => duong HEAD khong doi mot bit |

### 1.2 Duong dong THAT cua LEGACY = **HEAD byte-identical**

Truoc L3, khi profile bat thi co C3 ap cho **moi** symbol, ke ca vi the that. Da tach theo symbol:

| truc | HEAD (legacy) | so giay (C3) | diem noi |
|---|---|---|---|
| (a) arm | `Configs.RATE_PROFIT_STOP_MARKET` = **0.05** (env 242) | **0.07** | `TradeUtils.calRateMinWithPredReturn15MForTradingStop(pred, symbol)` -> `LiveProfileC3.armRateFor` |
| (c) dead-zone ratchet | **x5.21847** | **x1.0** (lien tuc) | `LiveProfileC3.ratchetDeadzoneMultFor(symbol, LIVE_RATCHET_DEADZONE_MULT)` |
| (b) time-stop 168h | **KHONG CO** | co (so giay) | `LiveProfileC3.timeStopApplies(symbol)` |
| gap trailing | `calRateLossDynamicBuyPNoPump` — **khong doi**, khong co co C3 nao o day | cung ham | — |

Diem ratchet that su cua legacy = `5.21847 x 0.05 = 26.1%` — **y het truoc L3, y het HEAD**
(test `ratchetTriggerPointLegacyIdenticalToHead` khang dinh dang thuc nay voi sai so 0).

### 1.3 So giay khong cham symbol LEGACY

| noi | hanh vi |
|---|---|
| vong chon top-K (`DetectEntrySignal2TradeNormal`) | symbol legacy -> log `[SHADOW] skip-LEGACY <sym>` + `continue` **TRUOC khi dem rank** => legacy **khong chiem slot** top-8 cua so giay |
| `createOrderBuyRequest` | chan MOI duong vao (selector, market-signal, DCA) mo entry giay tren symbol legacy |
| `shadowHandleOrder` (nhanh xu ly lenh giay) | chan lop cuoi, ke ca lenh den tu Redis queue/retry |

Truoc L3, symbol dang giu that bi skip **sau khi da dem rank** (cap-then-skip cua parity backtest);
day la thay doi CO Y va **chi ton tai khi profile bat** — profile tat thi `isLegacySymbol` luon
`false` nen vong lap byte-identical HEAD.

### 1.4 `SHADOW_NO_PUSH` hardcode

Da co tu L2 va **con nguyen**: `LiveProfileC3.forceNoPush()` tra `ON` (khong doc env); guard o
`processOrderNewMarketNew` la `forceNoPush() || Cfg.get("SHADOW_NO_PUSH")`. Test
`forceNoPushHardcodedWithProfile`. `env.sh.new` van dat `SHADOW_NO_PUSH=true` cho ro rang
(va de `verify.sh` doc duoc tu `/proc/<pid>/environ`).

### 1.5 Hai duong khong dung chung von

| truc | duong THAT (legacy) | so GIAY |
|---|---|---|
| `BudgetManager.BUDGET_PER_ORDER` (tu `getAccountUMInfo()`) | **van chay nhu cu** (thread cap nhat moi gio) | khong dung: `managerBudget` **khong** doc doi so `budget` — test `paperSizingIgnoresLiveBudgetPerOrder` |
| `balanceBasic` | `Configs.capitalStart()` cua tai khoan that | `ShadowBookC3.equityNow()` = `PAPER_EQUITY` + PnL giay — test `paperEquityIsolatedFromLiveCapital` |
| `marginRunning` | tinh lai tu `PositionRisk` moi tick | `ShadowBookC3.marginRunning()` |
| ghi nguoc trang thai | — | **da chan**: `BudgetManager.addMarginRunning(budget)` chi chay khi profile TAT |

### 1.6 Nhanh giay KHONG dung Redis queue cua bot

Truoc L3 lenh giay di qua `rpush REDIS_KEY_BINANCE_TD_ORDER_MANAGER_QUEUE` roi `blpop` lai —
tren 242 do la cum Redis 30001-6 **cua bot that**. Da them co
`LiveProfileC3.shadowUseRedisQueue()` (`LIVE_C3_QUEUE`, **mac dinh TAT**): profile bat =>
goi thang `BinanceOrderTradingManager.shadowHandleOrder(...)` trong cung JVM, **khong cham queue**.
Test `shadowDoesNotUseBotRedisQueueByDefault`.

### 1.7 Cong hoi quy

```
mvn -o test                 -> Tests run: 97, Failures: 0, Errors: 0   (82 cu + 15 moi)
mvn -o -DskipTests package  -> BUILD SUCCESS
tools/check_cfg_gateway.sh  -> OK (rc=0)
```
15 test moi o `src/test/.../selector/LegacyIsolationTest.java`. Vi khong doi duoc env trong JVM
dang chay, nhanh "profile BAT" duoc kiem qua **dung cac ham thuan tinh toan ma ban chinh thuc goi
vao** (`decideArmRate` / `decideDeadzone` / `decideTimeStop`), khong phai ban sao. Rieng luat
"legacy khong chiem slot" duoc kiem bang **mo hinh** `LegacySymbols.paperCandidates` — ghi ro day
la mo hinh cua vong lap, khong phai chinh vong lap.

---

## 2. VIEC 2 — GOI DEPLOY `/home/ubuntu/deploy_242_l3/`

| file | sha256 / kich thuoc |
|---|---|
| `sim.jar` (99,630,839 B) | `c8cec3988601edbc67c75d781fe587da095d6f3657a8f799c2dc53b32d5fb3d7` |
| `s1_c3/s1a2x1_cut20251001.onnx` (282,380 B) | `6067a0a2eb8ca462c03614f1fe37f83ff42d5bb58d3b1b031427966ec9983354` |
| `s1_c3/s1a2x1_cut20251001.json` (636,020 B) | `cc0924f1e26f9fcc199e33ef161916e293f48f4b4a0b3f8ca14ade0127997308` |
| `s1_c3/s1a2x1_cut20251001.manifest.json` | `5de107944532f00b6acab49620756e6bbd8a5fcc6c8b36c4f3269bb9e2680579` |
| `s1_c3/feature_order.txt` | thu tu 9 feature (input ONNX la VI TRI, khong phai ten) |
| `s1_c3/SHA256SUMS`, `sim.jar.sha256` | `deploy.sh` tu `sha256sum -c`, hong thi DUNG |
| `env.sh.new`, `deploy.sh`, `verify.sh`, `rollback.sh`, `README_DEPLOY.md` | — |

Hai sha256 model **trung** voi `s1a2x1_cut20251001.manifest.json` cua L2 (khong build lai model).

### 2.1 `env.sh.new` — them 6 key, KHONG dung toi phan con lai

```
export LIVE_PROFILE=c3_shadow
export SHADOW_NO_PUSH=true
export PAPER_EQUITY=35000
export SELECTOR_RANK_TOPK=8            # 5 -> 8
export SHADOW_C3_DIR=/home/chuyennd/java/shadow_c3
export S1_MODEL_ONNX=/home/chuyennd/java/storage/s1_c3/s1a2x1_cut20251001.onnx
# (dang comment, can user quyet) DCA_GRID_WEIGHTS=1,0,0,0 ; TIER_FLAT=1
```

**GIU NGUYEN, KHONG DUNG TOI**: `SIM_RATE_PROFIT_STOP_MARKET=0.05` (chinh la nguong arm cua 66
vi the legacy — doi = doi luat dong tien that), `SIM_MIN_MOMENTUM_15M=0.008`,
`TS_PRED_GAP=1`, `SIM_TS_PROFIT_MULTIPLIER=3.0` (L1 muc 6.1 **chua** xac nhan la key chet —
khong tu xoa).

`deploy.sh` **khong thay the** ca `conf/env.sh`: no xoa dung cac dong `export <key trong danh sach
quan ly>=` roi noi `env.sh.new` vao cuoi, va in `diff` truoc khi restart. Moi dong khac cua env.sh
242 (JAVA_HOME, APP_MAIN_CLASS, ...) **giu nguyen** — agent khong doc duoc file that nen khong
duoc phep viet de len no.

### 2.2 Thu tu lenh cua user

```
scp goi -> 242 ; ssh 242 ; bash deploy.sh ; sleep 180 ; bash verify.sh ; (FAIL) bash rollback.sh
```
Lenh day du: `deploy_242_l3/README_DEPLOY.md` muc 1 (port 2222, user root, key `id_rsa_chuyennd`).

### 2.3 `verify.sh` — 10 nhom kiem, PASS/FAIL tung dong, `exit 1` neu co FAIL

pid moi; `/proc/<pid>/environ` du 4 key; `Update all position:N` **= N0**; `[LEGACY] managed N0`;
co tick `[S1] score`; co `would-BUY|skip-LEGACY|no-candidate`; **0** `Create order market` va **0**
entry that; `Create Stop Loss Algo` cho legacy; 0 `Exception`; RSS < 5G.

Moi phep dem chi chay tren phan log **sau byte-offset ghi luc deploy** (`OFF0`) — khong lan sang
lich su. **Mot sai lech co chu dich so voi de bai**: dong `Create Stop Loss Algo` la **WARN**,
khong phai FAIL, khi chua xuat hien sau 3 phut — no la SU KIEN (chi phat khi can tao/doi SL),
mot vi the dang gong lo co the nhieu gio khong sinh dong nao. Bat FAIL o day se sinh **rollback
gia**, nguy hiem hon. Huong dan: chay lai `verify.sh` sau 15-30' truoc khi ket luan.

### 2.4 `rollback.sh`

Lay `backup_l3_*` moi nhat -> khoi phuc `target/*.jar`, `conf/env.sh`, `run/` -> xoa
`run/legacy_symbols.csv` -> `bin/daemon.sh restart` -> in pid moi + `Update all position:N` +
env thuc te cua process.

### 2.5 `tools/pull_242_shadow.sh` (chay tren ORACLE) — **CHUA BAT**

Keo `full.log` (200k dong cuoi, gzip qua WAN) + `ledger.csv` + `open_positions.csv` +
`legacy_symbols.csv` ve `/home/ubuntu/shadow_242/`, chay `tools/shadow_vs_sim.py parse`
(242 khong co python3), in tom tat. Cron **de dang comment trong chinh file**, chua cai:
```
# 5 * * * * /home/ubuntu/src/BinanceFuturesJava/tools/pull_242_shadow.sh >> /home/ubuntu/shadow_242/pull.log 2>&1
```
Ly do chua bat: 242 chua deploy, keo ve se chi ra file rong va lam nhieu log.

---

## 3. VIEC 3 — SHADOW ORACLE

**Van dang chay, khong tat trong dot nay** (dung y de bai). Do luc 2026-09-06 18:32 GMT+7:
pid **643543**, RSS **2,142,280 KB = 2.04G**, uptime **3h06'**, `ledger.csv` 2 lenh da dong,
`open_positions.csv` 9 vi the giay dang mo, cron health `0 * * * *` con nguyen.

Lenh TAT (chi chay khi user bao 242 da deploy xong):
```bash
cd /home/ubuntu/shadow_c3/app && bin/daemon.sh stop
crontab -l | grep -v 'shadow_c3/bin/health.sh' | crontab -
```

---

## 4. RAM — uoc tinh cho 242

Do that tren Oracle voi **cung khoi luong** (warm-up 384 moc gio, 719 coin, ONNX S1 + 2 model
cu): RSS **2.04-2.09G** voi `-Xms1g -Xmx4g`.

Phan L3 **them** vao mot JVM 242 (`-Xms5g -Xmx5g`, heap da commit san 5G):

| khoan | uoc tinh | cach tinh |
|---|---|---|
| `S1RankerLive.hist` | **~22-30 MB** | 700 coin x 384 moc gio x (Long+Double+TreeMap.Entry ~80 B) |
| `closes` moi tick | ~2.2 MB | 700 x `double[384]` |
| `oiCache` | ~2 MB | 700 x 2 x 24 moc x ~60 B (da `tail()` ve 24h) |
| doc warm-up | **transient**, ~150 KB/moc gio | doc **tung moc gio mot** (`getExistingTickersMap` cho 1 phut), tha ngay sau vong lap — khong gom 14 ngay vao bo nho |
| ONNX session S1 | ~50-100 MB **native** (ngoai heap) | model 282 KB + arena cua onnxruntime |
| 8 luong doc OI | khong dang ke | pool tao/huy moi gio |
| `ShadowBookC3` + `LegacySymbols` | < 1 MB | <= 8 vi the giay + 66 chuoi symbol |

=> **heap them ~35 MB** (nam gon trong `-Xmx5g` da cap), **native them ~0.1G**.
Ket luan: khong can giam buffer, **khong tang `-Xmx`** (box 7G, available 2G).
`verify.sh` FAIL neu RSS >= 5G; khi do huong xu ly la **giam** `S1FeatureLive.WARMUP_HOURS`/
`HIST_HOURS` roi build lai — khong phai tang Xmx.

⚠️ Con so tren la **uoc tinh**, khong phai do tren 242 (khong duoc SSH). Cua so rui ro that su
la `free` = 0G / available 2G: mot JVM 5G + ingestor 2G da gan het 7G, swap 7G dang de dem.

---

## 5. BA CUA SO RUI RO KHI DEPLOY

1. **Restart graceful <= 60s** — vi the legacy **khong mo coi**: `updatePositionInfo()` doc lai
   toan bo tu `getAllPositionInfos()` (Binance) ngay khi JVM len, va `STOP_MARKET` da treo tren san
   van hieu luc trong luc JVM tat. `runbook_shadow_off_trade_2026-08-23.md` da xac nhan chu ky nay.
   Rui ro con lai giong het moi lan `ThreadAutoRestartProgram` restart 4h/lan dang chay.
2. **RAM** — muc 4.
3. **`Update all position:N != N0` => ROLLBACK NGAY**, khong debug tren live. N tut = vi the bi
   dong ngoai y muon; N tang = co lenh that moi.

---

## 6. CON TREO (khong tu quyet)

- **User quyet**: co bat `DCA_GRID_WEIGHTS=1,0,0,0` + `TIER_FLAT=1` khong (muc 0 diem 3).
  Khong bat => sizing so giay 242 lech ~13 lan so voi shadow Oracle va so voi C3.
- **Chua kiem duoc** `TS_GIVEBACK_RATIO` hieu dung tren 242 (muc 0 diem 2) — can mot lenh CHI DOC
  cua user: `grep -i TS_GIVEBACK /home/chuyennd/java/v_t_m/config.properties conf/env.sh`.
- L1 muc 6.1 (`TS_PRED_GAP` / `SIM_TS_PROFIT_MULTIPLIER` co song trong jar khong) **van treo** —
  khong xoa hai key.
- Nhanh LEGACY **chua tung chay that**; du lieu doi chung dau tien chi co sau khi user deploy.
