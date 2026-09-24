# PREREG_T2B — luong DAY DU voi SIZE DUOC BU, C2b vs selector cu

Viet TRUOC khi chay, commit TRUOC khi chay, **khong sua sau khi thay so** (tru DUNG MOT lan
hieu chuan `DCA_GRID_SCALE` da khai o muc 2). Null co tinh thong tin.
DEV 2022-01-01..2024-06-30 (`SIM_END_DATE=20240630`). **Khong chay VAL. Khong push.**
jar `target/binance-java-sdk-1.2.4.jar` sha256 `09417d3e0e71f86e…`, code `6a9fdad`.

Tien de: `docs/experiment/T2_FULLFLOW.md` do `mean(margin)` 971 -> 9.21 khi bat `DCA_GRID_WEIGHTS=1,1,3,8`
ma KHONG bu `DCA_GRID_SCALE`. O diem van hanh do ca hai chan trien khai ~1% von => phep so
selector trong T2 **vo nghia**. T2b chay lai voi size duoc bu.

## 0. RUI RO / LO HONG — doc truoc khi doc so

1. **Bu size KHONG phai tuning.** Muc tieu kiem soat (`mean(margin)` leg 1 ~ 971) duoc chot
   TRUOC khi chay, va la muc tieu **san co cua baseline C2b**, khong phai muc chon theo outcome.
   Giong vai tro cua C1 trong F1. Nhung `DCA_GRID_SCALE` **van la mot truc sizing**, va
   `RUNBOOK muc 4` ghi ro **sizing khong do duoc tren DEV**. => Moi so bien do (maxDD, UW,
   equity, CAGR) o T2b **van** la ham cua size; chi rate PER-TRADE moi duoc dung ket luan.
2. **Chua tung ai chay `DCA_GRID_SCALE` = 253.5.** Bien duy nhat tung quet la `R7_scale15`/
   `R8_scale20` (1.5 / 2.0). Gia tri 253.5 nam ngoai moi mien da tham. Rui ro cu the:
   `U_MAX=0.60` co the bi cham thuong xuyen => `managerBudget` tra `null` => lenh bi CHAN,
   `n` tut. Neu `n < 600` chan do FAIL rang buoc cung va bao null.
3. **Leg BIG_DOWN BO QUA gate AI** (`Simulator…:817`) — nguyen van rui ro #1 cua `PREREG_T2`.
4. **`T2b_full_old` khac `T2b_full_c2b` o HAI bien**: bins (`predwf_G015_v2` vs
   `predwf_map_s1a2`) **va** gate calib (`SIM_MIN_MOMENTUM_15M` 0.014052 vs 0.008). Sai lech
   co y, ke thua nguyen tu `PREREG_T2 muc 0.3`, ghi truoc.
5. **`NUMBER_ENTRY_EACH_SIGNAL=2`, `MS_DOWN_BIG_AVG=-0.03157`, `F_BASE=0.03`, `U_MAX=0.60`
   la hardcode Java**, khong nam trong profile nao. KHONG quet trong T2b.
6. `E[max nhieu]` equity N=4 = `2.57*sqrt(2 ln 4)` = **4.28pp CAGR**. Equity bao rieng,
   dan nhan "khong phai tieu chi".
7. **Khong de cu ung vien baseline moi tu batch nay.**
8. DCA leg 2+ mo them exposure vao dung cai cum DANG THUA. Voi size bu, `total margin
   deployed` co the vuot xa `c2b_ref`. Bat buoc bao `total margin deployed` + PnL theo leg.

## 1. CONG THUC SIZE — he so 105x den tu dau (doc code, khong doan)

Duong di cua mot leg, `SimulatorMarketLevelTicker1MStopLoss.createOrder`:

```java
Float budget = BudgetManagerSimple.getInstance().getBudget();          // (1) BI BO QUA
budget = TradeUtils.managerBudget(budget, marginRunning, balanceBasic, levelChange);
budget *= tierMultiplier;                                              // TIER_FLAT=1 -> 1.0
if (Configs.DCA_GRID_ENABLED) { budget *= DcaUtils.gridLegWeightRatio(legIdx); }
quantity = Utils.calQuantityTest(budget, leverage, entry, symbolStr);  // LEVERAGE_ORDER=1
```

- (1) `getBudget()` tra `BUDGET_PER_ORDER = balanceBasic/50 = 700`, nhung `managerBudget`
  **khong doc tham so `budget`** — no la tham so chet. Con so 700 trong comment profile
  (`BASE_BUDGET = 35000/50`) **khong con anh huong gi**.
- `TradeUtils.managerBudget` (FROZEN v1 2026-08-24):
  ```java
  float u = marginRunning / balanceBasic;
  if (u >= Configs.U_MAX) return null;                       // U_MAX = 0.60
  float throttle = clamp(1f - u/U_MAX, 0, 1);
  float ladder = Configs.dcaGridTotalWeight();               // <-- CHIA LAN 1
  return balanceBasic * Configs.F_BASE * throttle / ladder;  // F_BASE = 0.03
  ```
- `DcaUtils.gridLegWeightRatio`:
  ```java
  return (w[legIdx] / Configs.dcaGridTotalWeight()) * Configs.DCA_GRID_SCALE;  // <-- CHIA LAN 2
  ```

### 1.1 Ghep lai — **tong trong so chia HAI LAN**

```
margin(leg i) = balanceBasic x F_BASE x throttle x DCA_GRID_SCALE x w[i] / total^2
              = 35000 x 0.03 x throttle x SCALE x w[i] / total^2
```

`balanceBasic` **la hang so** = `Configs.capitalStart()` = 35000; khong doan nao trong duong
sim ghi lai no (grep `balanceBasic *=` chi ra HPO/checker) => **size KHONG compound theo equity**.

| | `1,0,0,0` (`c2b_min`) | `1,1,3,8` (T2) |
|---|---|---|
| `total` | 1 | 13 |
| `total^2` | 1 | **169** |
| he so leg 1 (SCALE=1.5) | `1050 x throttle x 1.5 / 1` = **1575 x throttle** | `1050 x throttle x 1.5 / 169` = **9.3195 x throttle** |

**=> he so danh mac dinh la 169 (= 13^2), KHONG phai 13.** Truc giac "tong weight 13 nen leg 1
con 1/13" bo sot lan chia thu nhat trong `managerBudget` (comment code goi no la "chua cho du
ladder DCA" — nhung `gridLegWeightRatio` da chia roi, nen thanh chia doi).

### 1.2 Vi sao DO duoc 106 chu khong phai 169 — `throttle` hoi lai 1.59x

`throttle` la vong phan hoi: size nho => `marginRunning` nho => `u` nho => `throttle` -> 1.

| | `T2_c2b_ref` | `T2_full_c2b` |
|---|---|---|
| `mean(margin)` leg 1 do duoc | **971.0515** | **9.1440** |
| he so cong thuc | 1575 | 9.31953 |
| => `throttle` ngu y | **0.61654** | **0.98116** |
| => `u = U_MAX(1-throttle)` | 0.23008 (`marginRunning` ~ 8,053) | 0.01130 (~ 395) |

```
169 / (0.98116/0.61654) = 169 / 1.59137 = 106.19
do truc tiep: 971.0515 / 9.1440                = 106.19   ✓ khop tuyet doi
```
(`mean(margin)` TOAN BO cho 105.45 vi leg 2+ nang hon leg 1 — chinh la con so 105x cua T2.)

**Ket luan co hoc: 105x = 169x (chia binh phuong tong trong so) chia cho 1.59x (throttle
noi lai vi da gan nhu khong dung von).** Khong co he so an nao khac.

### 1.3 `DCA_GRID_SCALE` can de dua leg 1 ve ~971

Dat `margin_moi(leg1) = margin_ref(leg1)` o **cung throttle**:
```
1050 x SCALE / 169  =  1050 x 1.5 / 1     =>  SCALE = 1.5 x 169 = 253.5
```
**`DCA_GRID_SCALE = 253.5`** la gia tri dang ky cho lan chay dau.

Du bao (khai truoc): throttle SE TUT lai khi size ve that, va con tut them vi 120 leg
BIG_DOWN + cac leg DCA 2+ (trong so 1/3/8) cung an margin => `mean(margin)` leg 1 do duoc
se **thap hon** 971. Do la ly do co cong hieu chuan o muc 2.

## 2. CONG HIEU CHUAN (CALIBRATION — khong phai tuning)

**Muc tieu kiem soat chot truoc**: `mean(margin)` cua **leg 1** trong `T2b_full_c2b` phai nam
trong **±20% cua 971.05**, tuc **[776.84 , 1165.26]**.

- Lan chay 1 dung `DCA_GRID_SCALE = 253.5` (dan xuat dai so o muc 1.3).
- Neu ra ngoai khoang: duoc sua `DCA_GRID_SCALE` **DUNG MOT LAN**, theo dung ti so do duoc
  `SCALE_2 = 253.5 x 971.05 / mean(margin)_do_duoc`, va chay lai. **Khong co lan thu ba.**
- Ca hai gia tri scale (va ca hai `mean(margin)` do duoc) **deu duoc ghi vao bao cao**.
- Scale chot o buoc nay ap **y het** cho `T2b_full_old` va `T2b_dca_c2b` — khong hieu chuan
  rieng tung chan (hieu chuan rieng = chon theo outcome).
- Do la mot muc tieu **kiem soat** (giu bien do von khong doi de phep so selector co nghia),
  KHONG phai muc tieu **hieu nang**. Khong duoc doc lan hieu chuan nhu mot ket qua.

## 3. BON CHAN (toi da 4 run sim)

| tag | profile | bins | gate | `SELECTOR_ONLY_ENTRY` | `DCA_GRID_WEIGHTS` | `DCA_GRID_SCALE` | dataset |
|---|---|---|---|---|---|---|---|
| `T2b_c2b_ref` | `c2b_min` | `map_s1a2` | 0.008 | 1 | `1,0,0,0` | 1.5 | `wfo_ds_clean` |
| `T2b_full_c2b` | `t2b_full_c2b` | `map_s1a2` | 0.008 | **0** | **`1,1,3,8`** | **253.5** | `wfo_ds_clean` |
| `T2b_full_old` | `t2b_full_old` | **`G015_v2`** | **0.014052** | **0** | **`1,1,3,8`** | **253.5** | `wfo_ds_t2old` |
| `T2b_dca_c2b` | `t2b_dca_c2b` | `map_s1a2` | 0.008 | **1** (BIG_DOWN van TAT) | **`1,1,3,8`** | **253.5** | `wfo_ds_clean` |

- `T2b_c2b_ref` = **neo parity**: `b:60390`, 970 lenh, md5 `printDone.csv`
  `8f7afdfb27b15f5b6d4c886700def93c`. **Tai dung `T2_c2b_ref`** neu jar khong doi — da kiem:
  jar sha256 `09417d3e…`, `find src -newer <jar> -name '*.java'` **rong**, git tree sach
  => KHONG ton mot run. Lech md5 => DUNG batch.
- `T2b_dca_c2b` = **chi DCA** (BIG_DOWN van tat). Ghep voi chan big_down-mot-minh da co
  (`T2_full_c2b_noDCA`, 0/6 rate ngoai CI) de tach dong gop hai co che.
- **Moi trong sim quyet dinh chay tren Oracle + `TICKER_SOURCE=aerospike`** (neo 60390).
  Kaggle chi duoc dung cho **probe hieu chuan** (do `mean(margin)`), KHONG cho bat ky so nao
  vao bang so sanh — vi Kaggle bat buoc `TICKER_SOURCE=file` (neo 60395) va `RUNBOOK bay #7`
  cam ghep cap so tu hai moi truong trong mot phep so. Probe chi doc `mean(margin)`, mot
  dai luong lech < 0.1% giua hai moi truong (do thuc `KAGGLE_SIM muc 1`).

## 4. PRIMARY — rate (tieu chi quyet dinh)

Do tren `storage/printDone.csv`, script `research/analysis/t2b_legs.py`:

1. `TSloss%` (= ti le `STOP_LOSS_DONE` = time-stop 168h)
2. `win%`
3. `mean(profit | STOP_MARKET_DONE)`
4. `mean(profit | STOP_LOSS_DONE)`
5. `n`
6. `mean(margin)` **leg 1** va `mean(margin)` **toan bo**
7. `total margin deployed`
8. **so leg DCA thuc thi theo level** (`legdist`: leg 1 / leg 2 / leg 3) + phan bo `level`
9. **PnL tach theo leg level**: `sum(pnl)` va `mean(profit%)` cho **leg 1** vs **leg 2+**
10. phan bo status day du (khong gia dinh chi co 2 status)

**Tai lap leg index** (khong co cot san trong file): gom cum theo `(sym, end)` — `mergeOrder`
gop moi leg cua mot coin thanh MOT vi the nen ca cum dong cung mot moc `end`; trong cum sap
theo `start` => leg 0 / leg 1 / leg 2. Da kiem tren so T2: so dong `leg>=1` = **21** khop dung
so dong `level=DCA_LEVEL1` = 21 (`T2_full_c2b`), va **47** = 47 (`T2_full_old`). Khop 100%.

## 5. RANG BUOC CUNG (loai truc tiep, khong thuong luong)

`maxDD <= 15%` · `underwater <= 120 ngay` · khong nam am · khong quy < -5% · `n >= 600`.

## 6. QUY TAC QUYET DINH (viet truoc)

- **CAU CHINH** = `T2b_full_c2b` vs `T2b_full_old` (cung luong day du, cung size, khac selector).
  **KHAC nhau** khi **>= 2 rate PRIMARY lech CUNG HUONG va ngoai CI** block-bootstrap khoi 72h
  x1.21 (cung cong da dung o T1/T2). Duoi nguong = **KHONG PHAN BIET DUOC**, bao null.
- **CAU PHU** = `T2b_dca_c2b` vs `T2b_c2b_ref` — "DCA co dang bat khong". Theo **cung luat
  >= 2 rate** o tren, **VA** them dieu kien bat buoc: **`sum(pnl)` cua leg 2+ phai DUONG**.
  Thieu mot trong hai => **khong dang bat**.
- Chan FAIL rang buoc cung bi loai bat ke rate — nhung van bao day du rate cua no.
- **Khong chon chan nao theo equity.**
- CI: block-bootstrap 72h, **hai mau doc lap** (khong ghep cap theo lenh — so lenh khac nhau),
  4000 lan lay mau, noi rong nua-do-rong x1.21, seed 7.

## 7. HA TANG / VE SINH

1 slot JVM (`pgrep java` rong truoc moi run), `df -h /` > 5G truoc khi build (hien 14G free),
`rm -rf /home/ubuntu/wfo_ds_t2old` ngay sau `T2b_full_old`. Khong dat env `SIM_*` kem
`TRADING_PROFILE` (bay #2). Profile T2b sinh bang `sed` tu `c2b_min` (khong key chet).
Cham diem: `research/analysis/t2b_legs.py`, `/home/ubuntu/java/fsrun/qret.py`,
`research/analysis/qret_ladder.py`, `/home/ubuntu/java/fsrun/ev.sh`.
