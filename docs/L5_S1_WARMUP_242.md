# L5_S1_WARMUP_242 ? warm-up S1 tren 242: `0 coin` -> `635 coin`, va bo fallback `pNoPump`

Ngay 2026-09-07. Tiep noi `docs/L4_LIVE_BUILDMAP.md`, `docs/L3_DEPLOY_PREP.md`, `docs/L2_PORT_C3.md`.
**Da DEPLOY va da chay that tren 242** (khac L3/L4: hai dot do chi chuan bi goi).

---

## 0. Tom tat mot doan

L4 deploy len 242 luc 06:39 chay dung phan LEGACY (66 vi the that duoc co lap, 0 lenh that),
nhung **so giay khong chay C3 mot tick nao**: moi tick 15m in
`[S1] chi co 0 coin du lich su close 1h -> bo qua tick nay`, roi
`[S1] chua co score -> tick nay giu thu tu pNoPump cu`. `[MAP]`/net015 chua bao gio chay vi
nam SAU S1.

Nguyen nhan **khong phai du lieu, khong phai model, khong phai timeout**: `config.properties`
cua bot live tren 242 **thieu mot key**, lam namespace Aerospike thanh `null`, va mot
`catch` RONG nuot sach exception. Da sua, da do A/B, da deploy: warm-up doc **384/384 moc gio /
719 coin trong 603 ms**, tick dau tien sau restart cho `[S1] score 635 coin` + `[MAP]` day du.

---

## 1. NGUYEN NHAN ? do bang A/B, khong suy dien

### 1.1 Duong code

`S1RankerLive.refresh()` (warm-up close 1h) doc:

```java
DataManagerAerospikeFloatSim.getExistingTickersMap(
        new Key(Configs.AEROSPIKE_NAMESPACE_242, SET_TICKER, minuteKey(t - MIN)));
```

- `Configs.AEROSPIKE_NAMESPACE_242 = Configs.getString("AEROSPIKE_NAMESPACE_242")`, ma
  `getString` chi la `properties.get(name)` => **thieu key thi tra `null`, KHONG throw**.
- Key nay them 2026-08-05 (TASK-251) **chi cho 2 tool copy chay tren Oracle**
  (`CopyTicker242To226` / `CopyAuxSets242To226`). Chinh chu thich trong `Configs` muc 9 da
  canh bao: *"Neu properties thieu key nay ... gia tri se la null ? 2 tool copy se fail ro"*.
  Nhung L2/L3/L4 **cho `S1RankerLive` dung lai hang so do**, va no chay tren mot box ma
  `config.properties` **chua bao gio duoc cap nhat**.
- `config.properties` cua `/home/chuyennd/java/v_t_m` tren 242 (do truc tiep 07/09 06:52):

```
AEROSPIKE_HOST=103.157.218.242     AEROSPIKE_PORT=3222
AEROSPIKE_NAMESPACE=ticker         AEROSPIKE_READ_CLUSTER=242
AEROSPIKE_HOST_226=161.118.212.3   AEROSPIKE_PORT_226=3222
```
=> **KHONG co `AEROSPIKE_NAMESPACE_242`.** Tren Oracle thi CO (`AEROSPIKE_NAMESPACE_242=ticker`)
? vi vay shadow L2 tren Oracle warm-up tot, con 242 thi khong. **Khac biet nam O CONFIG.**

### 1.2 Vi sao im lang tuyet doi (khong mot dong log)

```java
public static Map<String, KlineObjectOptimized> getExistingTickersMap(Key key) {
    Map<String, KlineObjectOptimized> map = new HashMap<>();
    try {
        Record record = getClient242().get(null, key);
        ...
    } catch (Exception e) {         // <-- CATCH RONG: nuot sach
    }
    return map;                     // -> map RONG
}
```

`new Key(null, ...)` => NPE luc dung lenh doc => bi nuot => map rong => `refresh()` coi nhu
"moc gio nay khong co du lieu" (`if (m.isEmpty()) continue;`) => lap du 384 lan => `cnt = 0`
=> **khong in ca dong `[S1] nap ... moc gio close`** (dong do co guard `if (cnt > 0)`).
Dau vet duy nhat con lai la `[S1] chi co 0 coin`, va no o muc **WARN** nen khong bat duoc
bang `grep -c ERROR`.

### 1.3 Cong A/B ? `S1WarmupProbe` (doc that cum 242:3222, cua so 384 gio toi 07/09 07:00 GMT+7)

| # | config | code | ns thuc dung | moc gio doc duoc | coin | coin >= 336 moc | thoi gian |
|---|---|---|---|---:|---:|---:|---:|
| A | **cua 242** (thieu key) | **CU** (`raw`) | `null` | **0/384** | **0** | **0** | 478 ms |
| B | **cua 242** (thieu key) | **MOI** | `ticker` | **384/384** | **719** | **698** | 23.7 s |
| C | cua Oracle (co key) | MOI | `ticker` | 384/384 | 719 | 698 | 22.4 s |

A tai lap **chinh xac** trieu chung tren 242 (0 coin, that bai trong ~0.5s vi khong he cham
mang). B chung minh: cung config do, chi doi cach resolve namespace, la doc du.
3 coin mau (B): `0GUSDT`, `1000000BOBUSDT`, `1000000MOGUSDT` ? deu **384/384 moc**,
tu `Sat Aug 22 08:00 GMT+7` den `Mon Sep 07 07:00 GMT+7`.

=> **Du lieu close 1h tren 242 DU** (698/719 coin dat nguong 336 moc). Khong phai thieu du lieu,
khong phai sai set (`kline_1m_opt` dung), khong phai sai `SimpleSymbolMapper`
(`refresh()` khong dung mapper ? no lay key tu chinh `getTickersMap()` roi noi `USDT`),
khong phai timeout (A that bai sau 478 ms).

---

## 2. SUA ? 4 diem

| # | file | sua |
|---|---|---|
| 1 | `tradecore/selector/S1RankerLive.java` | `NS_242 = resolveNs242(Configs.AEROSPIKE_NAMESPACE_242)`: thieu/rong -> `"ticker"` (namespace THAT cua cum 242, `Configs` muc 9 do bang `client.info_all('namespaces')`). **Khong de `null` di tiep.** |
| 2 | `S1RankerLive.refresh()` | Log warm-up ro: `host:port`, `ns`, `set`, so moc **doc duoc/can**, so coin, **thoi gian ms**. Doc 0 moc => `LOG.error` + `probeSource()` doc thu 1 ban ghi **NGOAI** `getExistingTickersMap` de exception THAT hien ra. |
| 3 | `S1RankerLive.scoreAll()` | Gate "du lich su" chuyen **WARN -> ERROR** (moi tick), va dem `countReady(closes, 336)` = so coin du 14 ngay, in ca trong log thanh cong. |
| 4 | `tradecore/selector/EntryPoolGate.java` + `DetectEntrySignal2TradeNormal` | **BO FALLBACK**: co C3 bat ma S1 chua co score => pool **RONG** => `[S1] skip tick ? khong phai C3` => **khong mo mot entry giay nao**. Truoc day rot ve thu tu `pNoPump`. |

### 2.1 Vi sao chon "sua resolve namespace", khong phai doc qua WAN tu Oracle

De bai cho hai duong. Chon duong **doc tai cho tren 242** vi:
- du lieu **da co san va DU** tren chinh cum 242 (do o muc 1.3, 698/719 coin);
- warm-up tai cho **603 ms** (do that sau deploy) so voi **23.7 s** qua WAN tu Oracle ?
  nhanh hon **~39 lan**, va khong them mot phu thuoc mang nao vao duong live;
- khong phai gop `kline_1m` theo quy uoc `prev` (khong dung toi), vi `kline_1m_opt` da dung
  quy uoc VISION san.

### 2.2 Vi sao BO fallback `pNoPump` (khong phai "de tam cho co so lieu")

`pNoPump` la dau ra cua `Funding_Classifier_Final.onnx` ? mot selector **KHAC** (ho maxFav,
hieu chuan lech 2 lan, `G4_RECIPE_C4` muc 6.2 do admission x5.05). Mo entry theo no roi ghi
vao `ledger.csv` cua so giay C3 lam **ban ca chuoi do**: ta khong con phan biet duoc dong nao
la C3 that. **Mot tick TRONG hon mot tick SAI.** Day dung la nguyen tac L4 da ap cho thang
gia tri net015 (`[MAP] chua co thang gia tri ... KHONG mo entry giay`) ? nay ap not cho tang
xep hang S1.

### 2.3 KHONG dung toi (bang chung: 112/112 test + `Update all position:66` sau restart)

`SIM_RATE_PROFIT_STOP_MARKET=0.05` (nguong arm cua 66 vi the legacy), ratchet dead-zone
x5.21847, time-stop; `LATEST_SEL_PNOPUMP` (duong THAT doc thang o
`BinanceOrderTradingManager:485`); `getExistingTickersMap` (dung chung voi duong that ?
`probeSource` la duong RIENG, khong sua ham cu).

---

## 3. CONG TEST

| cong | ket qua |
|---|---|
| `mvn -o test` (Oracle) | **112/112 PASS** (105 cu + 7 moi), 0 fail 0 error |
| `EntryPoolGateTest` (4) | co TAT -> tra dung pool cu; co BAT + co score -> pool S1; **co BAT + chua co score -> pool RONG** (khong phai pool pNoPump) |
| `S1WarmupSourceTest` (3) | `resolveNs242(null/""/"   ") == "ticker"`; co key thi ton trong; `countReady` dem dung nguong 336 |
| `tools/check_cfg_gateway.sh` | OK (rc=0) ? khong them `System.getenv` nao |
| `mvn -o -DskipTests package` (Oracle) | BUILD SUCCESS |
| **build Windows** (jar deploy) | BUILD SUCCESS, `99,652,513 B`, sha256 `7ee36e9c991b3288ccabf01a030cd2bb9f7ed44ffc25276688c9fe82246a006c` |
| **PrivateConfig guard** | `PrivateConfig.class` trong jar MOI **md5 `fe8c91a8100e8e4d067a4d9606cea048`, byte-identical** voi jar dang chay (kiem tren ca Windows lan 242). Bay sang 07/09 (jar Oracle mang stub -> `-2014 API-key format invalid`) **da loai tru truoc khi restart**. |

---

## 4. DEPLOY 242 ? 2026-09-07

### 4.1 Goi va cong truoc restart

| muc | gia tri |
|---|---|
| goi | `/root/deploy_242_l3/` ? **chi thay `sim.jar` + `sim.jar.sha256`**; `deploy.sh` (co GUARD 90s auto-rollback), `rollback.sh` (da sua stop-truoc-restore), `verify.sh`, `models/` **giu nguyen** |
| jar | `99,652,513 B`, sha256 `7ee36e9c991b3288ccabf01a030cd2bb9f7ed44ffc25276688c9fe82246a006c` ? build tren **WINDOWS** |
| sha256 goi | `sim.jar: OK`; `models/SHA256SUMS`: 6/6 OK (khong build lai model nao) |
| **PrivateConfig** | jar moi vs jar dang chay: **612 B, md5 `fe8c91a8100e8e4d067a4d9606cea048` ? bang nhau** |
| **pgrep truoc** | `22060` ? **1 process**; pidfile = `22060` ? (dieu kien bat buoc) |
| RAM truoc | used 7156M / 7821M, available 368M, swap 968M |

### 4.2 Chay

```
nohup bash deploy.sh > /root/deploy_l5.log 2>&1 &     # + poll
```
- `bin/daemon.sh restart` -> **pid moi 22810**
- **GUARD 90s**: `reconcile OK: Update all position:66 (N0=66)` -> khong auto-rollback
- backup: `/home/chuyennd/java/v_t_m/backup_l3_20260907_071414`
- **pgrep sau restart = 1** (`22810`), pidfile = `22810` ? ? **khong dinh bay 2 JVM**

### 4.3 Warm-up that (dong log moi)

```
07:15:45.093 [S1] warm-up BAT DAU: nguon aerospike 103.157.218.242:3222 ns=ticker
             set=kline_1m_opt | doc 384 moc gio (1787360400000 -> 1788739200000),
             can >= 336 moc close 1h moi coin
07:15:45.696 [S1] nap 384/384 moc gio close (toi 1788739200000), 719 coin trong bo nho,
             603 ms (ns=ticker set=kline_1m_opt)
07:15:50.000 [S1] nap OI (delta24h + ls_global) cho 635 coin trong 4196 ms
```
**603 ms** doc 384 moc gio / 719 coin (tai cho tren 242) ? so voi **23.7 s** khi Oracle doc
cung tap qua WAN. OI mat them 4.2 s (635 coin x 2 set, 8 luong).

### 4.4 `verify.sh` ? **PASS (0 FAIL)**

Tat ca 20 dong PASS, gom: 6 env moi + 3 env **GIU NGUYEN**
(`SIM_RATE_PROFIT_STOP_MARKET=0.05`, `TS_PRED_GAP=1`, `SIM_TS_PROFIT_MULTIPLIER=3.0`),
`Update all position:66 = N0`, `[LEGACY] managed 66 = N0`, `[MAP]` = so tick `[S1] score`,
p50 trong `[0.20,0.70]`, **`0 lenh THAT moi`**, **0 Exception/ERROR**, `RSS = 4.23G (< 5G)`.
Mot `WARN` duy nhat: chua co `Create Stop Loss Algo` sau restart ? day la SU KIEN
(chi phat khi can tao/doi SL), khong phai loi.

---

## 5. HAI TICK DAU ? so lieu that

| | tick 1 (07:15:50) | tick 2 (07:30:42) |
|---|---|---|
| `[S1] score` | **635 coin** (626 du >= 336 moc) | **617 coin** (609 du >= 336 moc) |
| `[MAP] n_coins` | 635 | 617 |
| `[MAP] p10 / p50 / p90` | **0.4560 / 0.6201 / 0.8720** | **0.4254 / 0.5947 / 0.8383** |
| `[MAP] top` (8 dong) | co | co |
| top-8 `symbolPred` | 0.2736 .. 0.3402 | 0.2847 .. 0.3290 |
| `[SHADOW] would-BUY` | **8** (= `SELECTOR_RANK_TOPK`) | 0 ? **dung**: top-8 gan nhu y het tick 1 va **da mo trong so giay** |
| `[SHADOW] skip-LEGACY` | 1 (`VELVETUSDT`) | 1 (`VELVETUSDT`) |
| `[S1] skip tick` | 0 | 0 |
| lenh THAT moi | **0** | **0** |
| `Update all position` | **66** | **66** |
| `[LEGACY] managed` | **66** | **66** |
| RSS | 4.23G | **4.30G** (< 5G) |

`verify.sh` chay lai sau tick 2: **PASS (0 FAIL)**, `[MAP] xuat hien 2 lan = so tick [S1] score (2)`.
So giay mo **8 vi the giay** o tick 1 (`ShadowBookC3 ... open=8`), `ledger.csv` chua co dong
dong nao (chua co exit) ? dung ky vong sau 15 phut.

### 5.1 ?? Dai `[MAP]` live LECH CAO so voi DEV ? phai ghi, chua ket luan

| tap | p10 | p50 | p90 |
|---|---:|---:|---:|
| **live 242**, tick 1 | 0.4560 | **0.6201** | **0.8720** |
| **live 242**, tick 2 | 0.4254 | **0.5947** | **0.8383** |
| DEV 220 tick (`L4` muc 4.4), trung binh | 0.3732 | 0.4689 | 0.5588 |
| DEV, khoang qua 220 tick | 0.1826..0.4909 | 0.2262..**0.6093** | 0.2660..**0.7221** |

- `p50` live **sat mep tren** dai DEV (0.6201 > max DEV 0.6093 mot chut; 0.5947 nam trong).
  Cong `verify.sh` la `[0.20, 0.70]` nen **van PASS**, nhung khong con nhieu bien.
- `p90` live **VUOT HAN** dai DEV (0.87 / 0.84 vs max 0.7221).
- ?? **Nhung dai muc LENH thi khop**: top-8 live `0.2736..0.3402` so voi DEV top-8
  `p10/p50/p90 = 0.2555/0.2974/0.3373` ? **cung dai**. Tuc phan tram gia tri **thuc su thanh
  lenh** dang o dung cho, chi cai **duoi** cua vu tru la nang hon.
- Doc the nao: `symbolPred = 1 ? P(win)` => `p90` cao = **duoi vu tru co nhieu coin `P(win)`
  RAT THAP**. Co the la (a) che do thi truong 07/09 khac 2025-11/12, hoac (b) dau hieu cua
  **diem 4 trong `L4` muc 7** ? duong FEATURE 45 live vs Tool1 offline **chua do duoc**.
  **Hai tick khong du de phan biet.** Xem muc 7.

---

## 6. CON GI ? va cai gi da dong

| # | truc | trang thai |
|---|---|---|
| ~~warm-up S1~~ | ~~0 coin~~ | ?? **DONG.** 384/384 moc, 603 ms, 635/617 coin/tick. |
| ~~fallback `pNoPump`~~ | ~~so giay mo entry theo selector khac~~ | ?? **DONG.** Pool RONG khi chua co score; `EntryPoolGateTest` giu cong. |
| **A** | **dai `[MAP]` live vs DEV** | ?? **MOI ? muc 5.1.** Can >= 1 ngay tick de biet la regime hay hieu chuan. |
| **B** | duong FEATURE 45 live vs Tool1 (`L4` muc 7 diem 4) | ?? **con, van CHUA DO DUOC** ? va nay co them mot trieu chung (A) co the lien quan. |
| **C** | vu tru live vs `CLOSES_1H.bin` (`L4` diem 3) | ?? con ? co huu. Live: 719 coin trong bo nho, 635 duoc S1 cham diem (loc qua gate p15 + co OI). |
| **D** | model ngoai mep train 11 thang | ?? con (S1 va net015 deu cutoff 2025-10). |
| **E** | ke toan GIAY (khong phi/funding/slippage/tick-size) | ?? con. |
| **F** | RAM box | ?? RSS 4.30G/5G, `available` box **0G**, swap 0.9G. Khong con cho cho bat ky thu gi them. |
| **G** | `config.properties` 242 van thieu `AEROSPIKE_NAMESPACE_242` | ?? Code da co mac dinh nen khong gap; nen them cho config tu mo ta dung (QUEUE). |
| **H** | `conf/env.sh` co khoi comment L4 nhan doi sau deploy lan 2 | ?? Vo hai (cac `export` giong het). Runbook muc 13.3. |

---

## 7. VIEC TIEP THEO (theo thu tu)

1. **Theo doi `[MAP]` qua >= 1 ngay** (96 tick). Neu `p50` vuot **0.70** -> `verify.sh` FAIL ->
   dieu tra hieu chuan `net015` tren vu tru live. Neu on dinh 0.55..0.65 -> ghi lai dai live
   nhu mot dai RIENG (khong ep ve dai DEV) va noi cong theo no.
2. Bat cron `tools/pull_242_shadow.sh` (Oracle) ? nay 242 da co du lieu that de keo ve doi chung.
3. Cac muc B/C/D/E khong go duoc trong dot nay (da ghi o `L4` muc 7).
