# L6_GATE_DYN_FIX — bat gate dyn tang 2 tren LIVE rank-mode · 🔴 **CHO USER DUYET, CHUA DEPLOY**

> **Agent KHONG SSH 242.** Moi lenh o muc 7 la cua USER. Trang thai: goi da san tren Oracle
> (`/home/ubuntu/deploy_242_l6/`), **242 chua cham**.

Nguon: `docs/audit/AUDIT_GATE_DYN_PARITY.md` (`3a36f02`) muc 5.2 huong **A**, sau khi huong **C**
(do bang so) da chay xong va ra ket luan trong `docs/result/RESULT_FLATGATE.md`.

## 1. VI SAO SUA (bang chung, khong phai y kien)

- **Lech**: sim LUON goi `checkSignalDynamic` cho `PREDICT_SYMBOL_TRADE`
  (`SimulatorMarketLevelTicker1MStopLoss.createOrder`, khong he co dieu kien `SELECTOR_RANK_TOPK`);
  live BO QUA no khi `SELECTOR_RANK_TOPK>0` (`DetectEntrySignal2TradeNormal:656`, commit `311bb29`)
  => live rank-mode chay gate **PHANG 0.008** con sim chay **0.0172-0.0240**.
- **Do lon**: 95.62% slot top-8 lech tren 48 thang; **77/78** entry so giay 242 07-11/09 se bi chan.
- **Chien luoc gate phang do duoc bao nhieu**: `docs/result/RESULT_FLATGATE.md` — equity **9,666** vs
  **111,428**, CAGR **-27.51%** vs **+33.58%**, `d CAGR = -61.08 pp` CI95 `[-85.76, -32.82]`,
  **vo rang buoc cung 4/4 nam**. Tuc cai 242 dang chay **la ban TE HON**, do tren 48 thang.
- **Comment `[PARITY]` cu SAI**: no suy tu buoc chon ung vien (tang 1, `maxThres`) sang buoc
  entry-filter (tang 2). Sim bo tang 1 khi `TOPK>0` nhung **giu nguyen** tang 2.

## 2. THAY DOI GI (3 file main + 1 file test)

### 2.1 `AIRejectFilter` — them `entryGate(...)`, mot cho duy nhat quyet dinh gate
```java
public FilterResult entryGate(AiPredictionData prediction, Float symbolPred, boolean predictSymbolTrade) {
    FilterResult r = null;
    if (predictSymbolTrade && symbolPred != null) {
        r = checkSignalDynamic(prediction, symbolPred);
    }
    return r != null ? r : checkSignal(prediction);
}
```
Ly do dat o day thay vi sua tai cho: cong entry tang 2 truoc day nam o HAI ban sao (sim + live)
va da troi khoi nhau 3 tuan ma khong ai thay. Nay live goi cong nay; sim goi
`checkSignalDynamic` truc tiep va co test `entryGateTrungKhitCheckSignalDynamic` rang buoc hai
duong ra CUNG quyet dinh tren 7 moc `pred15m`.

### 2.2 `DetectEntrySignal2TradeNormal.createOrderBuyRequest` (~652-662) — BO `SELECTOR_RANK_TOPK <= 0`
```diff
-        if (levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE) {
-            // [PARITY] rank-mode (SELECTOR_RANK_TOPK>0): backtest RANK-TOPK BO nguong per-symbol,
-            //   chi dung market gate => KHONG goi checkSignalDynamic, de roi xuong checkSignal (market-only).
-            //   TOPK<=0: giu checkSignalDynamic cu (byte-identical).
-            if (symbolPred != null && Configs.SELECTOR_RANK_TOPK <= 0) {
-                filterResult = aiRejectFilter.checkSignalDynamic(predict, symbolPred);
-            }
-        }
-        if (filterResult == null) {
-            filterResult = aiRejectFilter.checkSignal(predict);
-        }
+        // [PARITY 2026-09-11, docs/experiment/L6_GATE_DYN_FIX.md + docs/audit/AUDIT_GATE_DYN_PARITY.md]
+        //   DINH CHINH chu thich cu o day: cai ma backtest BO khi SELECTOR_RANK_TOPK>0 la nguong
+        //   UNG VIEN tang 1 (maxThres = RATE_MAX*AI_DYNAMIC_MAX, Simulator:324-345), KHONG phai
+        //   gate ENTRY tang 2. Sim GIU NGUYEN checkSignalDynamic cho PREDICT_SYMBOL_TRADE o moi
+        //   che do (Simulator.createOrder, khong he co dieu kien SELECTOR_RANK_TOPK). Dieu kien
+        //   `SELECTOR_RANK_TOPK <= 0` cu (commit 311bb29) suy sai tu tang 1 sang tang 2 va lam
+        //   LIVE rank-mode chay gate PHANG 0.008 trong khi sim chay 0.0172-0.0240 => lech 95.62%
+        //   slot tren 48 thang, 77/78 entry so giay 242. Nay ca hai di CHUNG AIRejectFilter.entryGate.
+        filterResult = aiRejectFilter.entryGate(predict, symbolPred,
+                levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE);
```

### 2.3 Log `[GATE-DYN]` — MOT dong/tick, thuan log, khong doi quyet dinh
```
[GATE-DYN] topk=8 thr_base=0.00800 thr_dyn=[0.01717..0.02404] n_cand=8 n_rej=8 n_pass=0
```
`verify.sh` doc dung dong nay de chung minh gate dong DANG chay (khong the suy ra dieu do tu
`AI CHECK`/`[PREDICT fail]` — hai dong do co ca truoc L6).

## 3. CAI GI **KHONG** DOI — da kiem tung call-site

| duong | ket luan | bang chung |
|---|---|---|
| `BIG_DOWN` | **khong doi** | nhanh dyn co dieu kien `predictSymbolTrade`; caller truyen `false` |
| `DCA_LEVEL1` (2 call-site: `:303`, `:324`) | **khong doi** | `levelChange = DCA_LEVEL1` => `predictSymbolTrade=false` => `checkSignal` phang y nhu truoc |
| leg market-signal (`:289`, `levelChange` bien) | **khong doi** | chi bang `PREDICT_SYMBOL_TRADE` o call-site `:382`; moi gia tri khac di duong phang |
| `symbolPred == null` (moi leg) | **khong doi** | `entryGate` roi thang xuong `checkSignal` — dung y hanh vi cu |
| **LEGACY (66 vi the that)** | **khong doi** | LEGACY chi DONG lenh, khong mo lenh moi. Duong dong di qua `LiveProfileC3.armRateFor` / `ratchetDeadzoneMultFor` / `timeStopApplies` (`TradeUtils:74`, `BinanceOrderTradingManager:531,541`) — **khong cai nao goi `AIRejectFilter`**. `LegacySymbols.isLegacySymbol` o `DetectEntrySignal2TradeNormal:372` va `:705` deu la `continue`/`return` **truoc/ngoai** cong gate. |
| `conf/env.sh` tren 242 | **khong cham mot dong nao** | `deploy.sh` chi copy jar + restart |
| sim / bins / selector / exit / sizing | **khong cham** | diff chi 3 file main |

## 4. KET QUA TEST

```
mvn -o test  ->  Tests run: 118, Failures: 0, Errors: 0, Skipped: 0   BUILD SUCCESS
tools/check_cfg_gateway.sh  ->  OK
```
**118 test** = 112 cu (deu PASS, khong cai nao doi) + **6 moi** cua `GateDynEntryTest`.
`src/test/java/com/binance/chuyennd/ai_ml/onnx/entry/GateDynEntryTest.java` — **6/6 PASS**:

| test | khang dinh |
|---|---|
| `dynThresholdDung0206` | `dyn_thr(symbolPred=0.30) = 0.008*max(0.26787, 0.30/0.15*1.28760) = 0.0206016` |
| `rankModePred012BiReject` | TOPK=8, `symbolPred=0.30`, `pred15m=0.012` (QUA gate phang) => **REJECT** |
| `rankModePred025Pass` | cung the, `pred15m=0.025` => **PASS** |
| `legKhacPstGiuGatePhang` | leg khong phai PST: `0.012` => PASS, `0.007` => REJECT (gate phang y cu) |
| `symbolPredNullGiuGatePhang` | `symbolPred=null` => duong cu |
| `entryGateTrungKhitCheckSignalDynamic` | `entryGate` == `checkSignalDynamic` tren 7 moc `pred15m` |

Jar: `target/binance-java-sdk-1.2.4.jar`, sha256
**`0aac66bef1a54f09cc6bc0e81ba8d874b3d14a493a79d9b7d095fa4f8b1f2fcb`** (99,655,295 B).

## 5. DU DOAN GHI TRUOC — tac dong len so giay 242 (chot TRUOC khi deploy)

Ghi 2026-09-11, de sau deploy doi chieu duoc. Neu sai thi la tin hieu co lech khac chua biet.

1. **Nhip entry tut ~12 lan: 17.0/ngay -> ~1.4/ngay** (khoang tin **0.8-3.0/ngay**).
   Co so: `PARITY_R` 48 thang cho 0.84-2.43 entry PST/ngay; do offline 95.62% slot bi chan.
2. **Nhieu ngay LIEN TIEP khong co entry nao.** `PARITY_R` 2023 chi 0.84 entry/ngay => ngay
   trong la binh thuong. **Khong duoc coi "im lang" la loi** trong 1-2 tuan dau.
3. **So lenh dang mo giam manh**: 27 -> ky vong **3-8** sau ~2 tuan (DEV `open p90` = 4-11).
4. **`[GATE-DYN]` se cho `n_pass=0` o da so tick**; `n_pass>=1` chi o cac phut `p15` that su cao.
   Do tren 78 entry cua cua so 07-11/09: chi **1** co `p15 >= dyn_thr`.
5. **`[PREDICT fail N]` se tang** len gan bang so ung vien top-8 moi tick.
6. **Von khoa va MTM am se giam** cung chieu voi so bag: `SHADOW_EVAL` do -3.07% paperEquity
   voi 27 bag; voi 3-8 bag thi bien do nho hon nhieu (khong doan dau).
7. **KHONG du doan PnL tot hon trong 1-2 thang.** n qua nho. Bang chung duy nhat ve chat luong
   la 48 thang DEV, khong phai vai tuan live.

## 6. RUI RO

1. **Restart JVM tren 242** — theo `runbook_live_242_2026-08-19.md` §12.4 diem 1: graceful <=60s,
   vi the legacy KHONG mo coi (`updatePositionInfo()` doc lai tu Binance khi JVM len; `STOP_MARKET`
   treo tren san van hieu luc luc JVM tat). Rui ro con lai giong het moi lan `ThreadAutoRestartProgram`
   restart 4h/lan dang chay san. `deploy.sh` ghi `N0` truoc, `verify.sh` FAIL neu `Update all position:N != N0`.
2. **LEGACY khong doi** (muc 3) — nhung van phai kiem bang `verify.sh` muc 5, khong tin suong.
3. **Gate siet khuech dai lech `p15` live-vs-offline** (`L4_LIVE_BUILDMAP` muc 7 diem 8): gate moi
   cat o **4% tren cung** cua phan phoi `p15`, nen neu `Model_Regressor_Return15M.onnx` (live) lech
   `wfo_gate_pred.csv` (offline) thi sai so se an manh hon truoc. **Chua do duoc** — day la rui ro
   lon nhat cua ban va cua no khong bien mat khi deploy. Giam thieu: dong `[GATE-DYN]` ghi ca dai
   `thr_dyn` lan `n_pass` moi tick => sau 2-4 tuan co the doi chieu phan phoi voi DEV.
4. **Ky vong sai cua nguoi doc**: ai quen 17 entry/ngay se thay bot "chet". Muc 5 diem 1-2 chot truoc.
5. **`conf/env.sh` khong doi** => khong co rui ro cau hinh; doi lai, **khong the tat gate moi bang env**.
   Muon quay lai gate phang phai rollback jar (muc 7).

## 7. CHECKLIST DEPLOY — 3 lenh (USER chay, theo mau `deploy_242_l3/README_DEPLOY.md`)

Goi: **`/home/ubuntu/deploy_242_l6/`** — `sim.jar` + `sim.jar.sha256` + `deploy.sh` + `verify.sh`
+ `rollback.sh` + `README_DEPLOY.md`. **Khong co `env.sh.new`, khong co `models/`** — L6 chi doi jar.

```bash
# (1) lay goi tu Oracle ve may Windows roi day len 242
scp -i C:\Users\pc\.ssh\id_rsa_chuyennd -r ubuntu@161.118.212.3:/home/ubuntu/deploy_242_l6 .
scp -P 2222 -i C:\Users\pc\.ssh\id_rsa_chuyennd -r deploy_242_l6 root@103.157.218.242:/root/

# (2) deploy + verify
ssh -p 2222 -i C:\Users\pc\.ssh\id_rsa_chuyennd root@103.157.218.242
cd /root/deploy_242_l6 && bash deploy.sh && sleep 180 && bash verify.sh

# (3) CHI khi verify FAIL
bash rollback.sh
```
⚠️ IP **103.157.218.242**, port **2222**, user **root**.

**`deploy.sh` lam gi**: doc pre-state (`pid0`, `N0` tu `Update all position:`, `OFF0` byte-offset
`full.log`) — khong doc duoc `N0` thi **DUNG**; `sha256sum -c sim.jar.sha256`; backup
`target/*.jar` + `conf/env.sh` + `run/` -> `backup_l6_<ts>/` va them `*.jar.bak_l6_<ts>` canh jar;
copy jar; `bin/daemon.sh restart`. **KHONG cham `conf/env.sh`.**

**`verify.sh` kiem** (exit 1 neu co FAIL; moi phep dem chi tinh log **sau `OFF0`**):

| # | kiem | nguong |
|---|---|---|
| 1 | pid moi, khac pid cu, con song | FAIL neu khong |
| 2 | sha256 jar o `target/` = sha256 goi | FAIL neu lech |
| **3** | **co dong `[GATE-DYN]`** | **FAIL neu khong** — day la bang chung gate dong dang chay |
| 3b | moi dong `[GATE-DYN]` co `thr_dyn` that (khong phai `[-..-]`) | FAIL (thieu = `symbolPred` null = roi ve gate phang) |
| 3b | in `thr_base` vs `thr_dyn` de mat doi chieu (ky vong `0.0172-0.0240` vs `0.00800`) | thong tin |
| 4 | co `[PREDICT fail]`; in them `AI PASS` / `AI CHECK` | WARN neu chua qua mot tick 15m |
| **5** | **`Update all position:N` = `N0`** | **FAIL -> ROLLBACK NGAY** |
| 5 | `[LEGACY] managed N` (ky vong = `N0`) | thong tin |
| **6** | **`Create order market` = 0** | **FAIL -> ROLLBACK NGAY** |
| 7 | 0 `Exception` moi (tru `RequestHandler`/`fapi`) | FAIL |
| 8 | RSS < 5G | FAIL |

**ROLLBACK** = `rollback.sh`: copy `target/binance-java-sdk-1.2.4.jar.bak_l6_<ts>` (hoac ban trong
`backup_l6_<ts>/`) de len, `bin/daemon.sh restart`, cho 120s, doi chieu lai `Update all position:N`
voi `N0`. `conf/env.sh` khong can phuc hoi vi chua bao gio bi doi. Thoi gian rollback ~3 phut.

## 8. 🔴 CHO USER DUYET — CHUA DEPLOY

Agent **khong** SSH 242 va **khong** chay `deploy.sh`. Quyet dinh can user:
- (a) **Co deploy L6 khong?** Du lieu ung ho (muc 1), nhung deploy = chap nhan nhip tut ~12 lan
  va chap nhan rui ro muc 6.3 (lech `p15` bi khuech dai) ma hien **chua do duoc**.
- (b) Neu khong deploy: 242 tiep tuc chay chien luoc da do la **te hon ro** tren 48 thang
  (`RESULT_FLATGATE`). Rui ro nay phai ghi vao `QUEUE.md` (da ghi).
- (c) Neu deploy: sau 2-4 tuan doi chieu `[GATE-DYN]` va nhip entry voi muc 5 diem 1-5.

## 9. TAI LAP

```
cd /home/ubuntu/src/BinanceFuturesJava
export PATH=/home/ubuntu/tools/apache-maven-3.9.9/bin:$PATH
tools/check_cfg_gateway.sh && mvn -o test && mvn -q -DskipTests -o package
sha256sum target/binance-java-sdk-1.2.4.jar
git show --stat HEAD
```
Log test: `/home/ubuntu/x1log/l6_test.out`.
