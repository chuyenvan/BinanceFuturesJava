# L7_LEAN_GATE — cong entry ve MOT class `EntryGate` · 🔴 **CHO USER DUYET, CHUA DEPLOY**

> **Agent KHONG SSH 242.** Goi da san tren Oracle (`/home/ubuntu/deploy_242_l7/`), **242 chua cham**.

Nguon: `docs/audit/LEAN_GATE_AUDIT.md` (`e249a06`) — audit do 48 thang truoc khi sua. Tien than:
`docs/experiment/L6_GATE_DYN_FIX.md` (bat gate dong tren live rank-mode) va `docs/audit/AUDIT_GATE_DYN_PARITY.md`.

## 0. L7 lam gi trong mot cau

Gop **hai ban sao** cua cong entry tang 2 (`checkSignalDynamic` trong `AIRejectFilter` +
nhanh rieng cua sim) ve **mot class `EntryGate`** ma ca backtest lan live deu goi, bot gate tu
**4 knob xuong 1**, xoa **4 co che tro** — va chung minh bang **`printDone.csv` byte-identical**
voi `X1_C3_FULL_PARITY_R` rang **khong mot con so nao doi**.

## 1. CONG PARITY — day la bang chung, khong phai loi hua

| cong | ket qua |
|---|---|
| `tools/check_cfg_gateway.sh` | **OK** — khong tham so giao dich nao lach cong `Cfg` |
| `mvn -o test` | **Tests run: 125, Failures: 0, Errors: 0, Skipped: 0 — BUILD SUCCESS** (118 truoc L7: 112 cu + 6 `GateDynEntryTest`; nay 112 cu + **9** `EntryGateTest` + **4** `TrailHingeTest`) |
| sim `x1_c3_full.properties` -> `devrun/X1_C3_FULL_LEAN` | `b:111428` · `done:339/2266/2266` · 2,267 dong · `PROFILE_HASH=135750e04d67c263` · 0 Exception |
| `md5sum printDone.csv` | **`2478e90d4e6147bf4cc64f75967ef47d`** = **KHOP** `X1_C3_FULL_PARITY_R` |
| `md5sum` bo header | **`e13bc39e625b8d2ceebb7b9194f7f4f0`** = **KHOP** |
| `cmp` bo header vs `PARITY_R` | **rc = 0 (IDENTICAL)** |
| jar | `35ffb41c678593d7ba7bf9f7c55e0f2271bcd9b5841ade702e3afcd591ebf98f`, 99,649,446 B |

## 2. THAY DOI GI

### 2.1 `EntryGate` (tradecore) — mot bieu thuc duy nhat
```java
public static float threshold(float thrBase, Float symbolPred) {
    if (symbolPred == null) return thrBase;
    float scale = (symbolPred / SCORE_BASE) * DYN_MULT;
    return thrBase * Math.max(DYN_MIN, scale);
}
public static boolean pass(float predReturn15M, float thrBase, Float symbolPred) {
    return !(predReturn15M < threshold(thrBase, symbolPred));
}
```
`DYN_MIN = 0.26787f`, `SCORE_BASE = 0.15f`, `DYN_MULT = 1.28760f` — **`static final`, het knob**.

**Ba dieu co y lam, moi dieu deu co ly do bang so:**
1. **GIU NGUYEN tung phep nhan.** Khong rut ve `p15 >= K*symbolPred` (`K = 0.0686720`) vi
   (a) floor `DYN_MIN` **CO bind that**: 1 slot / 140,244 moc 15m x top-8 tren 48 thang
   (2024-08-05 13:30 GMT+7, symId 261, `symbolPred = 0.024885`), va (b) nhan `float` **khong ket
   hop** — `base*((sp/RMAX)*MULT)` lech `(base*MULT/RMAX)*sp` toi 1 ULP, do duoc ngay tren tick
   do (rank2 `delta = -0.0000000`). Gate so sanh `>=` nen 1 ULP du doi mot quyet dinh.
   Chi tiet: `docs/audit/LEAN_GATE_AUDIT.md` muc 3.
2. **Viet `!(x < thr)` chu khong phai `x >= thr`** — hai dang khac nhau khi `predReturn15M`
   la NaN, va dang `<` la dang goc da chay 48 thang (`AIRejectFilter.evaluate`).
3. **Ba he so thanh hang so** vi **khong profile/env nao tung khai** `SIM_AI_DYNAMIC_*`
   (audit muc 2.3) — chung von la hang so tra hinh cau hinh. Gate nay chi con doc
   **`Configs.MIN_MOMENTUM_15M`** (key `SIM_MIN_MOMENTUM_15M`) => **`conf/env.sh` cua 242 KHONG DOI**.

### 2.2 `AIRejectFilter` con la vo boc mong
Xoa: `checkSignalDynamic` (ban sao thu hai cua cong thuc), `checkSignal` (nay chi la truong hop
`symbolPred == null` cua cung ham — **khong con duong code rieng de troi**), `dynThreshold`,
`thres15M`, va **nhanh EARLY-HARD-GATE** + counter `earlyHardGateReject`.

> **Early-hard-gate bi bo vi CHUNG MINH GIAI TICH la thua**, khong phai vi do thay no it chay:
> no chi fire khi `symbolPred > 0.15`; khi do
> `thr = base*max(0.26787, sp/0.15*1.2876) > 1.2876*base > base > p15`, nen `evaluate` **cung**
> tra REJECT. Dung voi **moi** `p15`, **moi** `sp`, **moi** `base > 0`. Bo no chi doi chuoi
> `reason` trong log; `mom15RejectCount` tang dung 1 lan o ca hai duong nen counter khong doi.

### 2.3 Mot call-site moi ben
| ben | truoc | sau |
|---|---|---|
| SIM | `Simulator...createOrder:962-972` — `if (PST && !GATE_DYN_BYPASS) checkSignalDynamic; if (null) checkSignal` | `aiRejectFilter.entryGate(predict, symbolPred, levelChange == PREDICT_SYMBOL_TRADE)` |
| LIVE | `DetectEntry...:685-686` (da la `entryGate` tu L6) | y nguyen, chu thich viet lai |

### 2.4 Log live `[GATE-DYN]` -> `[GATE]`
```
[GATE] topk=8 base=0.00800 thr=[0.01717..0.02404] n_cand=8 n_rej=8 n_pass=0
```
`verify.sh` cua goi L7 doc dung dong nay. Thuan LOG, khong doi quyet dinh.

### 2.5 Tang 1 (`maxThres`/`nPass`) — chuyen vao nhanh `TOPK<=0`, **khong xoa han**
Rank-mode bo hoan toan tang 1 nen truoc day `maxThres`/`nPass` la **phep tinh chet chay moi tick**.
Nay chung nam trong `else` cua `if (SELECTOR_RANK_TOPK > 0)`. **KHONG xoa han** vi nhanh `TOPK<=0`
**van song**: profile khong khai `SELECTOR_RANK_TOPK` thi `Configs` tra `-1`. Xoa han se lam vo
moi profile cu — day la lua chon **risk-first**, khac voi de nghi ban dau.

### 2.6 Xoa 4 co che TRO (10 key, 1 class)
| co che | key xoa | trang thai | doc ket qua |
|---|---|---|---|
| `GateRollingThreshold` (149 dong) + 2 diem `init` + re nhanh `thres15M` | `SIM_GATE_ROLLING_PCT`, `SIM_GATE_ROLLING_DAYS` | B4/GATEDYN dong | `docs/result/B4_RESULT.md` muc 6 (da hoi master tu truoc), `docs/audit/AUDIT_GATEDYN_GD92.md` |
| book cap + `TickDecisionLog.D_BOOK_CAP` + `openNotional()` + 6 counter | `SIM_MAX_OPEN_POSITIONS`, `SIM_MAX_OPEN_NOTIONAL_PCT` | BOOKCAP **NULL** | commit `573dd1f` |
| HOLDDCA + log `[DCA13]` + `DcaUtils.shouldDcaHold` + nhanh `DcaProcessor` | `SIM_DCA_TRIGGER`, `SIM_DCA_MIN_DROP`, `SIM_DCA_COOLDOWN_H`, `SIM_DCA_MAX_LEGS`, `SIM_ENTRY_FRACTION` | **0/3 PASS, ca ba THUA** | commit `f10f6ca` |
| FLATGATE | `SIM_GATE_DYN_BYPASS` | thi nghiem xong | `docs/result/RESULT_FLATGATE.md` |
| gate knob | `SIM_AI_DYNAMIC_MIN`, `SIM_AI_DYNAMIC_MULTIPLIER` | thanh hang so `EntryGate` | muc 2.1 |

**19 profile** thi nghiem -> `profiles/archive/` kem `README.md` tro toi doc ket qua + commit tao.
**Docs ket qua GIU nguyen.**

### 2.7 Con so
| | |
|---|---|
| file doi | **35** (`+382 / -583`, net **-201 dong**) |
| class xoa | **1** (`GateRollingThreshold`) · class them: **1** (`EntryGate`, 79 dong) |
| key cau hinh xoa | **10** |
| profile chuyen vao archive | **19** |
| gate: knob truoc -> sau | **4** (`SIM_MIN_MOMENTUM_15M` + 3 `SIM_AI_DYNAMIC_*`) -> **1** |
| gate: so cho viet cong thuc | **2 ban sao** (`checkSignalDynamic` + `dynThreshold`) -> **1** |
| test | 118 -> **125** |

## 3. CAI GI **KHONG** DOI — da kiem tung duong

| duong | ket luan | bang chung |
|---|---|---|
| `printDone.csv` cua `X1_C3_FULL` | **byte-identical** | muc 1: `cmp` rc=0, md5 khop ca co lan bo header |
| `BIG_DOWN` / `DCA_LEVEL1` / leg market-signal | khong doi | `entryGate(..., predictSymbolTrade=false)` => nguong CO SO, y het `checkSignal` cu |
| `symbolPred == null` | khong doi | `EntryGate.threshold(base, null)` tra thang `base` |
| `conf/env.sh` tren 242 | **khong cham mot dong** | gate chi con doc `SIM_MIN_MOMENTUM_15M` (da co san) |
| LEGACY (vi the that) | khong doi | LEGACY chi DONG lenh; duong dong di qua `LiveProfileC3.armRateFor` / `ratchetDeadzoneMultFor` / `timeStopApplies` — **khong cai nao goi `AIRejectFilter`** |
| ban le trailing 0.29 | khong doi (xem muc 4) | `TrailHingeTest` 4 case |
| sizing / sleeve DCA cua so giay | **khong cham** — co y | muc 5 + `docs/experiment/L8_SIZING_PARITY_BACKLOG.md` |

## 4. Ban le trailing 0.29 — **KHONG can sua code**, phan con lai la HIEU CHUAN

Master yeu cau sua live cho khop sim neu la thay doi nho. **Do lai thi hoa ra da khop san o muc
code**: `ShadowBookC3:233-234` goi **cung ham** `TradeUtils.calRateLossDynamicBuyPNoPump(peak, pnp,
Configs.tsPnoPumpWeakThr())` nhu sim (`OrderTargetInfoTest.trailRate:365-373`), va gia tri truyen
vao la `DetectEntrySignal2TradeNormal.paperSymbolPred(symbol)` (`:99-105`) = **`LATEST_SEL_MAPPRED`
= gia tri net015 DA QUA quantile-map**, tuc **cung thang do voi bins cua sim**, chi roi ve
pNoPump khi thieu map.

=> Da chot phan chot duoc bang test: **`TrailHingeTest`** (4 case) — ban le doc tu MOT nguon
(`Configs.tsPnoPumpWeakThr() = 0.29`), duoi ban le => STRONG (peak 10% -> SL 5%), tren ban le =>
WEAK (-> SL 7%), cung input => cung ket qua, thieu `symbolPred` => ca hai coi la WEAK (1f).

**Phan KHONG chot duoc bang test**, va do la thu that su con lech: **phan phoi** cua map net015
tren live khac phan phoi score bins tren sim (ledger so giay do 0.065-0.144; top-8 cua bins
median 0.31-0.50 theo nam). Cung mot ban le tren hai phan phoi khac nhau se phan loai
STRONG/WEAK khac nhau tren du lieu that. **Do la bai toan hieu chuan model, khong phai loi nhanh
code** => tach sang `docs/experiment/L8_SIZING_PARITY_BACKLOG.md` muc 2, dung quyet dinh cua master
("khong chung minh duoc bang test thi tach").

## 5. Sizing — **DO, khong sua** (ket qua do nam trong L8)

Master chot khong sua sizing trong L7. Da do va ghi vao `docs/experiment/L8_SIZING_PARITY_BACKLOG.md`:

| | mean %equity / leg | nguon |
|---|---|---|
| **SIM** `X1_C3_FULL_PARITY_R` (2,266 leg, 48 thang) | **2.498%** (median 2.505%) | `research/analysis/sizing_parity_measure.py` tren `printDone.csv` |
| **LIVE** so giay C3 (8 leg mot tick, `PAPER_EQUITY=35,000`) | **3.000% -> 2.085%** | `docs/experiment/L2_PORT_C3.md` muc 4.1 (do truc tiep tu log) |

**Hai ket luan, mot trong do la dinh chinh chinh minh:**
1. Bac do lon **KHOP** (~1.0-1.2x). Uoc luong **"~16x" o `docs/audit/LEAN_GATE_AUDIT.md` muc 4.3 la SAI**
   — no suy tu cong thuc chu khong do. **Da ghi dinh chinh vao audit do.**
2. 🔴 Nhung **cong thuc trong code KHONG giai thich duoc phep do**: theo code sim leg0 phai la
   `equity x 0.03 x throttle x 1.5/13 = 0.346% x throttle`, do duoc **2.498%** — lech ~7.2 lan.
   **Chua ai doc dung duong sizing cua sim.** Khong duoc sua mot dong sizing nao truoc khi giai
   xong cho nay.

Sleeve ma so giay **khong tai lap duoc** (`ShadowBookC3.open` la `Map<symbol,Pos>` + `putIfAbsent`
=> leg thu 2 tren cung coin bi bo im lang): `BIG_DOWN` 9,884.4 + `DCA_LEVEL1` 7,407.3 =
**17,291.7 / 76,428.4 = 22.6% pnl** cua backtest. Ai doc so cua so giay phai doc kem dieu nay.

## 6. RUI RO

1. **Restart JVM tren 242** — graceful <=60s; vi the legacy khong mo coi (`updatePositionInfo()`
   doc lai tu Binance khi JVM len, `STOP_MARKET` treo san van hieu luc). Giong het moi lan
   `ThreadAutoRestartProgram` restart 4h/lan dang chay san. `deploy.sh` ghi `N0` truoc,
   `verify.sh` FAIL neu `Update all position:N != N0`.
2. **Gate siet khuech dai lech `p15` live-vs-offline** (`L4_LIVE_BUILDMAP` muc 7 diem 8): gate cat
   o ~4% tren cung cua phan phoi `p15`, nen neu `Model_Regressor_Return15M.onnx` (live) lech
   `wfo_gate_pred.csv` (offline) thi sai so an manh hon. **Chua do duoc — rui ro lon nhat, va no
   khong bien mat khi deploy.** Giam thieu: dong `[GATE]` ghi ca dai `thr` lan `n_pass` moi tick
   => sau 2-4 tuan doi chieu phan phoi voi DEV.
3. **Gate khong con tat duoc bang env.** Doi lai khong co rui ro cau hinh. Muon quay lai: `rollback.sh`.
4. **Ba he so thanh hang so => 3 gene HPO thanh vo hieu.** `WFORunner:64-65`,
   `StrategyWfoTask:71-72`, `SensitivityTool:64-65` van dinh nghia gene `AI_DYNAMIC_MIN` /
   `AI_DYNAMIC_MULTIPLIER`; tu L7 chung **khong con tac dong len gate**. Da ghi canh bao ngay tai
   `Configs.java` cho khai bao hai field do. **Go chung khoi gene vector la viec cua L8** (doi
   index gene — khong duoc lam chung dot voi cong parity). Day la mot **co tro co y giu, co
   tai lieu**, khac voi co tro am tham.
5. **Ky vong sai cua nguoi doc**: ai quen 17 entry/ngay se thay bot "chet". Nhip ky vong
   **~1.4/ngay** (0.8-3.0), nhieu ngay trong la binh thuong.

## 7. CHECKLIST DEPLOY
Goi **`/home/ubuntu/deploy_242_l7/`** — xem `README_DEPLOY.md` trong goi (3 lenh, `verify.sh` 8
phep kiem, phep 3 doi dong `[GATE]`, phep 5/6 FAIL => rollback ngay).
**L6 chua deploy => deploy L7 THAY L6.** Neu L6 da deploy => L7 la buoc sau, **hanh vi gate khong doi**.

## 8. 🔴 CHO USER DUYET — CHUA DEPLOY
Agent **khong** SSH 242 va **khong** chay `deploy.sh`.

## 9. TAI LAP
```bash
cd /home/ubuntu/src/BinanceFuturesJava
export PATH=/home/ubuntu/tools/apache-maven-3.9.9/bin:$PATH
tools/check_cfg_gateway.sh && mvn -o test && mvn -q -DskipTests -o package
bash /home/ubuntu/l7run.sh            # build + sim X1_C3_FULL_LEAN + cmp/md5 voi PARITY_R
python3 research/analysis/sizing_parity_measure.py
python3 research/analysis/lean_gate_floor_scan.py
```
Log: `/home/ubuntu/x1log/l7_test.out`, `/home/ubuntu/x1log/l7_sim.out`.
