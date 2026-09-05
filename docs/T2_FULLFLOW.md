# T2_FULLFLOW — ghep selector C2b vao LUONG DAY DU (big_down + DCA)

Cau hoi cua user (nguyen van): *"ghep c2b vao luong sim hien tai (luong don c2b hien tai dang
khong co big_down va dca ma no dang dung SL cung 7d thi phai, toi muon test thu kieu thay c2b
voi selector cu ay)"*.

Pre-reg `docs/PREREG_T2.md`, commit TRUOC khi chay. DEV 2022-01-01..2024-06-30
(`SIM_END_DATE=20240630`). Khong chay VAL. jar `target/binance-java-sdk-1.2.4.jar`, code `acd9469`.

---

## 1. KHAM PHA — doc code, khong doan

### 1.1 `big_down` la gi

**KHONG co key cau hinh nao ten `big_down`.** Do la `MarketLevelChange.BIG_DOWN` — mot trong hai
NGUON LEG ENTRY cua engine (nguon kia la `PREDICT_SYMBOL_TRADE` = sleeve selector).

Co hoc, ba manh:

1. **Sinh tin hieu** — `MarketBigChangeDetector.getMarketStatus1M()`
   (`src/main/java/com/binance/chuyennd/tradecore/MarketBigChangeDetector.java:174-185`):
   ```java
   if (rateDownAvg < Configs.MS_DOWN_BIG_AVG) return MarketLevelChange.BIG_DOWN;
   return null;   // co OFF_FLAT_HARD da go 2026-09-03 -> chi con MOT nhanh song
   ```
   `rateDownAvg` = trung binh rate-change 1M cua ~100 coin giam manh nhat trong tick.
   `Configs.MS_DOWN_BIG_AVG = -0.03157f` (`Configs.java:369`, hardcode; key env
   `SIM_MS_DOWN_BIG_AVG` co ton tai nhung KHONG profile nao khai). Tuc: **thi truong sap
   trung binh > 3.157% trong 1 phut => BIG_DOWN**. Day la co che **bat day**, khong phai
   co che chan lenh hay dong lenh.

2. **Tieu thu tin hieu (leg entry)** — `SimulatorMarketLevelTicker1MStopLoss.java:246-278`:
   khi `levelChange != null`, engine lay `NUMBER_ENTRY_EACH_SIGNAL` coin tot nhat theo
   `predict2Symbol` roi mo leg voi `levelChange = BIG_DOWN`. **Vong lap nay nam trong**
   ```java
   if (!Configs.SELECTOR_ONLY_ENTRY) { ... createOrderBUY(symbolId, ticker, levelChange, ...) }
   ```
   => `SELECTOR_ONLY_ENTRY=1` **TAT hoan toan leg BIG_DOWN**. Day dung la cai user goi ten.
   Ten cu cua no trong lich su repo: ablation `A2_nobigdown`
   (`/home/ubuntu/java/dev_abl.sh:43`: `run A2_nobigdown $D1E SELECTOR_ONLY_ENTRY=1  # bo leg BIG_DOWN`).

3. **BIG_DOWN BO QUA GATE AI** — `SimulatorMarketLevelTicker1MStopLoss.java:817`:
   ```java
   if (!levelChange.equals(MarketLevelChange.BIG_DOWN)) { ...AIRejectFilter...; if REJECT return; }
   ```
   Leg BIG_DOWN khong di qua `checkSignalDynamic`/`checkSignal`. Day la **rui ro so 1** cua
   viec bat lai: gate duoc `RUNBOOK muc 4` xac nhan la **load-bearing** (`v3_g1_nomom` = 10,305
   voi 14,007 lenh), ma nhanh BIG_DOWN di vong qua no — dung luc thi truong sap manh nhat.

**Trong `c2b_min`: BIG_DOWN dang TAT** (`profiles/c2b_min.properties:13` `SELECTOR_ONLY_ENTRY=1`).
Khong khai key => `"1".equals(null)` = false => BIG_DOWN BAT (default = luong day du).

### 1.2 DCA dang tat bang duong nao

Hai co che rieng, dung mot cong ra:

- **Leg DCA_LEVEL1** (`DcaProcessor.getDCA`, goi o `Simulator...:290-305`) — cac vong lap nay
  **KHONG** nam trong guard `SELECTOR_ONLY_ENTRY`, tuc chung VAN chay trong `c2b_min`.
- Nhung moi leg deu di qua `createOrder`, va o day
  (`Simulator...:889-898`) co cong grid:
  ```java
  if (Configs.DCA_GRID_ENABLED) {
      int legIdx = (cur == null) ? 0 : cur.size();
      float ratio = DcaUtils.gridLegWeightRatio(legIdx);
      if (ratio <= 0f) return;          // het bac grid -> khong mo them leg
      budget *= ratio;
  }
  ```
  `DCA_GRID_WEIGHTS=1,0,0,0` => `w[1]=w[2]=w[3]=0` => moi leg thu 2 tro di bi chan. Leg
  DCA_LEVEL1 chi nham vao coin DA co lenh chay (`getActiveOrderMap()`) nen `legIdx >= 1`
  **luon** => **DCA tat 100%**, dung nhu `W1_SWEEP muc 7` da ghi.

**Dinh chinh `C2B_SPEC.md:73`**: dong do ghi `SELECTOR_ONLY_ENTRY=1` -> "tat BIG_DOWN / DCA_LEVEL1".
Doc code thi **chi BIG_DOWN** bi key do tat; DCA_LEVEL1 bi `DCA_GRID_WEIGHTS` tat.
=> **hai co che TACH DUOC thanh 2 co doc lap** — nen chan `T2_full_c2b_noDCA` la kha thi.

### 1.3 Exit hien tai — user nho dung

`c2b_min` khong co stop-loss cung. Duong exit: arm `SIM_RATE_PROFIT_STOP_MARKET=0.07` roi
trailing `gap = min(peak*0.5, cap)` voi cap = `TS_MAX_GAP_WEAK=0.03` (W1 chung minh 100% lenh
di nhanh WEAK), cong **time-stop `SIM_LOSER_TIME_STOP_HOURS=168`** (= 7 ngay) cho cum chua arm.
Status `STOP_LOSS_DONE` trong `printDone.csv` **la time-stop 168h, khong phai SL**. `HARD_SL_PCT`
va `COND_EXIT_HOURS` deu = 0 (tat).

### 1.4 "Luong day du" — chon profile nao va TAI SAO

**Khong co profile nao trong `profiles/` co `SELECTOR_ONLY_ENTRY=0`** (36/36 file deu ke thua
`c2b_min`). Ung vien lich su co luong day du:

| ung vien | o dau | tinh trang |
|---|---|---|
| `devrun/D0_full` | `SELECTOR_ONLY_ENTRY=false`, 1688 lenh, b:48763 | jar `fs.jar` (khac), dataset `wfo_ds_sealed25` **da bi xoa**, cau hinh qua env (khong co profile) |
| `devrun/G1_giveback5` | base cu cua `AUDIT_APPLIED A1` (b:48352, 1736 lenh) | cung the: jar + dataset cu, khong tai lap |
| `devrun/A2_nobigdown` | = D1 + `SELECTOR_ONLY_ENTRY=1`, 1754 lenh | cung the |
| `configs/sim_dev.properties` | chi con tham so HA TANG | khong chua tham so giao dich nao |

**Quyet dinh: KHONG dung so lich su lam neo.** Ly do la mot bay da xay ra hai lan trong repo nay:
`W1_SWEEP muc 8` ghi `N4_a8s175` ban 2026-09-03 = 61,148/974 lenh, chay lai tren jar+dataset hien
tai = 61,592/918 — "khac jar va khac duong cau hinh, khong duoc ghep 2 so nay trong mot so sanh";
va `AUDIT_APPLIED` ghi su co `dev_h1.sh` da so nham baseline vi thieu 3 key.

**Dinh nghia dung trong T2**: "luong day du" = `c2b_min` **tru hai cong nghien cuu**, delta toi
thieu **2 key**:

| key | `c2b_min` (nghien cuu) | T2 "day du" |
|---|---|---|
| `SELECTOR_ONLY_ENTRY` | `1` (tat leg BIG_DOWN) | **`0`** |
| `DCA_GRID_WEIGHTS` | `1,0,0,0` (tat DCA) | **`1,1,3,8`** (luoi thiet ke, = default `Configs.java:190`, = `GRIDW` mac dinh cua `dev_abl.sh:20`) |

Moi truc khac (exit arm 7% + trailing + time-stop 168h, gate 0.008, `DCA_GRID_SCALE=1.5`,
`TIER_FLAT=1`, `CAPITAL_START=35000`, funding, breaker OFF) **giu y nguyen c2b_min**. Nho vay
`T2_full_c2b` vs `T2_c2b_ref` do dung 2 co che user hoi, va `T2_full_c2b` vs `T2_full_old` do
dung selector — khong tron them truc nao.

**Tham so AN duoc hoi sinh khi bat BIG_DOWN (bat buoc ghi truoc):**
- `Configs.NUMBER_ENTRY_EACH_SIGNAL = 2` (`Configs.java:106`) — so leg mo moi tick BIG_DOWN.
  Key nay **da bi xoa khoi `configs/sim_dev.properties`** trong dot don 20 key "khong ai doc"
  (dung, vi voi `SELECTOR_ONLY_ENTRY=1` no la key chet). Bat BIG_DOWN => no song lai va chay
  bang **default hardcode Java**, khong nam trong profile. Da ghi vao pre-reg nhu mot bien co
  dinh, KHONG quet.
- `Configs.MS_DOWN_BIG_AVG = -0.03157f` — nguong BIG_DOWN, cung la hardcode, cung khong quet.
- `DCA_TIME_BIG_DOWN=8`, `DCA_LOSS_BIG_DOWN=-0.15f` — chi duoc doc o `DcaUtils.getDcaConfig(BIG_DOWN)`,
  ma nhanh do chi chay khi `DCA_GRID_ENABLED=false`. Voi grid bat, chung **van tro**.

### 1.5 "Selector cu" la gi

Selector cua C2b = **S1** (XGBRanker, 9 feature), bins `/home/ubuntu/predwf_map_s1a2`.
Selector cu = **G015**. Ban goc `predwf_G015x26` **KHONG tai lap duoc** (mat training export —
`RUNBOOK muc 5`, single point of failure) va **khong con tren dia**. Ban tai lap duoc la
**`/home/ubuntu/predwf_G015_v2`** (10 file bins + `MANIFEST.sha256`, 386MB), da duoc dung lam
selector cu trong `profiles/c3.properties` (`docs/G015REBUILD_RESULT.md`).

Kem theo: `c3.properties` **hieu chuan gate** `SIM_MIN_MOMENTUM_15M` 0.008 -> **0.014052**
(he so c=1.75654) de dua admit-rate cua G015_v2 ve dung diem van hanh cua ban cu. T2 giu nguyen
hieu chuan do cho chan `T2_full_old` — neu khong, phep so selector se tron them mot cu soc tan suat.
**Day la mot sai lech co y va da ghi truoc**: `T2_full_old` khac `T2_full_c2b` o **2 bien**
(bins + gate calib), khong phai 1.

### 1.6 `CONFIG_STRICT` — 5 key chet

`configs/c2b.properties` chua 5 key chet (`DISABLE_PREDICT_SYMBOL`, `HARD_STOP_LOSS_RATE`,
`TIME_STOP_HOURS`, `TS_GAP_CONST`, `TS_MIN_GAP`) => `CONFIG_STRICT=1` se STOP. Ba profile T2
duoc sinh bang `sed` tu **`c2b_min`** (16 key, `PROFILE_HASH=a2f859b2463108fe`, da PASS strict),
chi doi 4 dong + them `DCA_GRID_LEVELS` => **khong key chet nao**. `DCA_GRID_LEVELS` duoc doc o
`Configs.java:188` nen khong bi `Cfg.auditProfile()` bao.

---

## 2. PARITY

| tag | md5 `printDone.csv` | b | n |
|---|---|---|---|
| neo `C2b` (RUNBOOK muc 3) | `8f7afdfb27b15f5b6d4c886700def93c` | 60390 | 970 |
| **`T2_c2b_ref`** | **`8f7afdfb27b15f5b6d4c886700def93c`** | **60390** | **970** |

**PARITY OK — byte-identical.** Moi run `rc=1` (bay #1, khong phai fail): deu co `done:` + `b:`
va `printDone.csv` co dong.

md5 cac chan con lai (de tai lap / doi chieu):
`T2_full_c2b` `99dfd5c5791f922d4bd070cffee24408` · `T2_full_c2b_noDCA` `e67df5fca12b9b94600cc850d45ed229`
· `T2_full_old` `d01d2530d6508befebd685ae3c9722c2`.

Dataset: `wfo_ds_clean` (`fundingPredDir=/home/ubuntu/predwf_map_s1a2`) cho 3 chan dau;
`wfo_ds_t2old` build rieng (`fundingPredDir=/home/ubuntu/predwf_G015_v2`,
`md5_funding=f6f088f02e360964783d66e32b488399`) cho `T2_full_old`, **da `rm -rf` sau khi chay**
(dia ve 14G free). `HOLDOUT SEAL` cat 312,322 ban ghi >= 2026-01-01 nhu moi lan build.

---

## 3. BANG RATE PRIMARY

| | `T2_c2b_ref` | `T2_full_c2b_noDCA` | **`T2_full_c2b`** | **`T2_full_old`** |
|---|---|---|---|---|
| big_down | tat | **bat** | **bat** | **bat** |
| DCA | tat | tat | **bat (1,1,3,8)** | **bat (1,1,3,8)** |
| selector | S1 (`map_s1a2`) | S1 | S1 | **G015_v2** |
| **n lenh** | 970 | 1025 | 1076 | **2709** |
| **TSloss%** | 15.155 | 15.122 | 14.777 | **19.232** |
| **win%** | 85.258 | 85.756 | 85.223 | **80.657** |
| **mean(profit\|STOP_MARKET_DONE)** | 7.476 | 7.457 | 7.141 | 6.820 |
| **mean(profit\|STOP_LOSS_DONE)** | -18.896 | -18.318 | -16.033 | -19.898 |
| mean(profit) toan bo | 3.479 | 3.559 | 3.716 | 1.671 |
| median(profit) | 5.499 | 5.499 | 5.500 | 5.496 |
| **mean(margin)** | 971.05 | 956.58 | **9.21** | **9.23** |
| **total margin deployed** | 941,920 | 980,493 | **9,908** | **25,015** |

### 3.1 Phan bo status (day du, khong gia dinh truoc)

| tag | `STOP_MARKET_DONE` | `STOP_LOSS_DONE` (= time-stop 168h) | khac |
|---|---|---|---|
| `T2_c2b_ref` | 823 (84.85%) | 147 (15.15%) | — |
| `T2_full_c2b_noDCA` | 870 (84.88%) | 155 (15.12%) | — |
| `T2_full_c2b` | 917 (85.22%) | 159 (14.78%) | — |
| `T2_full_old` | 2187 (80.73%) | 521 (19.23%) | **`REQUEST` 1 (0.04%)** |

Luong day du **khong sinh status exit moi**. Ngoai le duy nhat: `T2_full_old` co **1 dong
`REQUEST`** — lenh chua bao gio duoc khop/dong tinh den `SIM_END_DATE`. 1/2709, khong doi rate nao.

### 3.2 Phan bo NGUON leg entry (`level`) — do truc tiep dong gop cua big_down/DCA

| tag | `PREDICT_SYMBOL_TRADE` | `BIG_DOWN` | `DCA_LEVEL1` |
|---|---|---|---|
| `T2_c2b_ref` | 970 (100.00%) | 0 | 0 |
| `T2_full_c2b_noDCA` | 905 (88.29%) | **120 (11.71%)** | 0 |
| `T2_full_c2b` | 935 (86.90%) | **120 (11.15%)** | 21 (1.95%) |
| `T2_full_old` | 2542 (93.84%) | **120 (4.43%)** | 47 (1.73%) |

**`BIG_DOWN` = dung 120 leg o CA BA chan** — dung nhu co hoc: tin hieu BIG_DOWN sinh tu
`marketData.rateDownAvg` (toan thi truong), **khong phu thuoc selector**, va so tick BIG_DOWN
trong DEV la co dinh. 120 leg / 2.5 nam = **~48 leg/nam**. DCA thuc te chi khop 21-47 leg —
grid `-50/-75/-90%` rat it khi cham (khop con so 0.34% cua `Configs.java:180`).

### 3.3 CI 95% block-bootstrap 72h x1.21 — **cau hoi cua user**: `T2_full_c2b` - `T2_full_old`

| rate | hieu | CI | ket qua |
|---|---|---|---|
| `TSloss%` | -4.455 | [-9.119, +0.279] | trong CI |
| `win%` | +4.566 | [-0.335, +9.526] | trong CI |
| `mean(profit\|SM)` | +0.321 | [-0.893, +1.773] | trong CI |
| `mean(profit\|SL)` | +3.865 | [-1.238, +8.864] | trong CI |
| `mean(profit)` | +2.045 | **[+0.061, +4.011]** | **KHAC** |
| `mean(margin)` | -0.026 | [-0.441, +0.376] | trong CI |

**1/6 rate ngoai CI.** Quy tac pre-reg doi **>= 2 rate cung huong ngoai CI** => **KHONG PHAN
BIET DUOC**. Ghi nhan: bon rate deu nghieng ve C2b (TSloss thap hon 4.5pp, win% cao hon 4.6pp)
va hai cai do **cham bien CI** — huong nhat quan nhung chua du bang chung theo cong da dang ky.

### 3.4 CI 95% block-72h x1.21 — `T2_c2b_ref` - `T2_full_c2b_noDCA` (bat rieng big_down)

| rate | hieu | CI | ket qua |
|---|---|---|---|
| `TSloss%` | +0.033 | [-6.157, +6.389] | trong CI |
| `win%` | -0.498 | [-6.781, +5.719] | trong CI |
| `mean(profit\|SM)` | +0.019 | [-1.639, +1.672] | trong CI |
| `mean(profit\|SL)` | -0.579 | [-8.008, +7.029] | trong CI |
| `mean(profit)` | -0.080 | [-2.846, +2.663] | trong CI |
| `mean(margin)` | +14.47 | [-126.8, +156.7] | trong CI |

**0/6 rate ngoai CI** => bat big_down mot minh **KHONG PHAN BIET DUOC voi c2b_min**.

---

## 4. RANG BUOC CUNG (maxDD <= 15% · UW <= 120 ngay · khong nam am · khong quy < -5% · n >= 600)

| tag | maxDD% | UW (ngay) | nam am | quy min | n | ket qua |
|---|---|---|---|---|---|---|
| `T2_c2b_ref` | -13.1 | 93 | khong | -3.7 (2022Q4) | 970 | **PASS** |
| `T2_full_c2b_noDCA` | -12.9 | 93 | khong | -2.9 (2022Q4) | 1025 | **PASS** |
| `T2_full_c2b` | -0.1 | 58 | khong | 0.0 | 1076 | PASS *(rong — xem 4.1)* |
| `T2_full_old` | -0.4 | **147** | khong | -0.1 | 2709 | **FAIL** (UW 147 > 120) |

### 4.1 Canh bao doc so: hai chan co DCA PASS mot cach RONG

`T2_full_c2b` PASS moi rang buoc **vi no gan nhu khong giao dich bang tien**: `mean(margin)`
9.21 vs 971 = **1.05%** von trien khai cua `c2b_min`; equity 35,000 -> 35,314 (**+0.9% trong 2.5
nam**, CAGR **0.36%**). maxDD -0.1% khong phai "an toan hon", no la **khong co gi de mat**.
Rang buoc cung khong co san mot muc loi nhuan toi thieu nen chung khong bat duoc truong hop nay.
`T2_full_old` cung vay (CAGR **0.32%**) va van FAIL underwater.

---

## 5. PHAN QUYET

**Cau hoi user (`T2_full_c2b` vs `T2_full_old`, cung luong, chi khac selector):
KHONG PHAN BIET DUOC** — 1/6 rate PRIMARY ngoai CI (can >= 2). Nhung phep so nay duoc thuc
hien **o mot diem van hanh gan nhu vo hieu** (ca hai chan trien khai ~1% von), nen no **khong**
tra loi duoc cau hoi "selector nao tot hon trong luong day du" — no chi noi rang o diem do,
hai selector khong tach nhau tren rate.

**Cai T2 tra loi duoc, ro rang:**

1. **`big_down` bat lai mot minh = vo hai va cung gan nhu vo ich.** `T2_full_c2b_noDCA` them
   **120 leg BIG_DOWN** (11.7% so lenh) ma **0/6 rate ngoai CI**, maxDD -12.9 vs -13.1,
   underwater 93 = 93, equity 61,287 vs 60,390. Dieu nay dang chu y vi leg BIG_DOWN **bo qua
   gate AI** (muc 1.1) — vay ma khong lam hong gi. Gia thiet don gian nhat: 120 leg / 2.5 nam
   qua it de doi bat ky rate nao.
2. **DCA voi luoi thiet ke `1,1,3,8` la thu pha luong**, va **pha bang SIZING chu khong bang
   chat luong lenh**: tong trong so 13 nen leg dau chi con `1/13` suat budget, `DCA_GRID_SCALE`
   van de o **1.5** (khong bu) => `mean(margin)` **971 -> 9.21 (105 lan nho hon)**,
   `total margin deployed` 941,920 -> 9,908. Chat luong tung lenh **khong xau di**
   (`mean(profit)` 3.48 -> 3.72, `mean(profit|SL)` -18.90 -> -16.03); chi co **quy mo** bien mat.
3. **Khong de cu ung vien baseline moi** (dung pre-reg muc 0.6). `T2_full_c2b_noDCA` khong phan
   biet duoc voi `c2b_min` nen khong co ly do doi.

**The mo (can pre-reg rieng, KHONG lam trong T2):** chay lai luong day du voi
`DCA_GRID_SCALE` **duoc bu** de `mean(margin)` giu nguyen ~971 (voi `1,1,3,8` thi can
`scale ~ 1.5 x 13 = 19.5`, phai kiem `CapacityProbe` truoc vi dinh von dong thoi se x13 o cac
tick cham day). Day dung la the ma `W1_SWEEP muc 10` da mo va van chua ai dong.

---

## 6. EQUITY — **KHONG PHAI TIEU CHI**

Dan nhan ro: `E[max nhieu]` voi N=4 = `2.57 x sqrt(2 ln 4)` = **4.28pp CAGR**. Khoang cach giua
`T2_c2b_ref` va `T2_full_c2b_noDCA` (0.7pp) nam **hoan toan trong** mien nhieu do.
**Khong duoc chon chan nao theo cot nay.**

| tag | equity cuoi | CAGR (2.496 nam) | vs `T2_c2b_ref` |
|---|---|---|---|
| `T2_full_c2b_noDCA` | 61,287 | ~25.2% | +897 |
| `T2_c2b_ref` | 60,390 | 24.48% | 0 |
| `T2_full_c2b` | 35,314 | **0.36%** | -25,076 |
| `T2_full_old` | 35,283 | **0.32%** | -25,107 |

Loi nhuan theo nam: `T2_c2b_ref` 11.6 / 45.4 / 6.3 · `noDCA` 12.1 / 45.4 / 7.4 ·
`full_c2b` 0.3 / 0.4 / 0.2 · `full_old` 0.2 / 0.4 / 0.2. Khong chan nao co nam am.

---

## 7. CONFOUND SIZING — bao truoc, do thuc

Pre-reg muc 0.4 canh bao "DCA doi `mean(margin)` nen cai thien maxDD/UW co the chi la size nho
hon". Do thuc **manh hon canh bao**: khong phai "co the", ma la **toan bo** hieu ung.

| | `c2b_ref` | `full_c2b` | ti le |
|---|---|---|---|
| `mean(margin)` | 971.05 | 9.21 | **0.95%** |
| `total margin deployed` | 941,920 | 9,908 | **1.05%** |
| maxDD | -13.1% | -0.1% | — |
| CAGR | 24.48% | 0.36% | — |

maxDD va underwater cua hai chan co DCA **khong duoc doc nhu cai thien rui ro**. Theo
`RUNBOOK muc 4`, sizing **khong do duoc tren DEV**; moi so o cot `full_c2b`/`full_old` lien quan
den bien do (maxDD, UW, equity, CAGR) **chi la ham cua size**, khong phai bang chung ve co che.
Cac rate PER-TRADE (`TSloss%`, `win%`, `mean(profit|status)`) **khong** bi confound nay va la
phan duy nhat cua muc 3 duoc dung de ket luan.

### 7.1 Sai lech so voi pre-reg (ghi de minh bach)

- Dung **4/4 run** da dang ky, khong them chan nao sau khi thay so.
- `T2_full_old` khac `T2_full_c2b` o **2 bien** (bins + gate calib 0.014052) — da ghi truoc o
  pre-reg muc 0.3, khong phai phat sinh.
- CI dung block-bootstrap 72h **hai mau doc lap** (khong ghep cap theo lenh — hai chan co so
  lenh khac nhau 1076 vs 2709 nen khong the ghep cap), 4000 lan lay mau,
  noi rong nua-do-rong x1.21. Script: `research/analysis/t2_rates.py`.
- Khong chay VAL. Khong push.
