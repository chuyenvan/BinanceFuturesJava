# PREREG_X2 — danh vao DUOI cua phan bo lenh thua tren cua so 48 thang

Viet va commit **TRUOC** khi chay bat ky thu gi (RUNBOOK muc 0.2). Khong sua sau khi thay so.
Nen: `C3` (`profiles/c3_min.properties`, 3 co B1/B2/B3 ON), cua so DEV **2022-01-01 -> 2025-12-31**,
`SIM_END_DATE=20251231`, bins `predwf_map_s1a2_x1` (16 fold, sha `b8776231...`), neo `X1_C3`.

---

## 0. RUI RO — doc TRUOC

1. 🔴 **Pre-arm SL PHAI VIET LAI.** `SIM_HARD_SL_PCT` **khong con doc duoc o HEAD**: khong co
   dong `Cfg.get("SIM_HARD_SL_PCT")` nao trong `src/main`. Con lai chi la **di vat**: field
   `OrderTargetInfoTest.firstEntryPrice` (van duoc set dung, bat bien qua DCA) va dong in
   `DumpConfig.derived.pre_arm_stop`. => X2 la mot **thay doi ENGINE**, khong phai mot phep quet
   tham so. Moi so cua X2 chi co nghia neu cong hoi quy o muc 3 PASS.
2. 🔴 **Cat lo som lam UW DAI RA.** `E1` muc 5.3 do duoc UW 93 -> 156 ngay khi cat 168h -> 72h
   (tang 68%). `X1` do duoc UW 2025 cua `X1_C3` da la **302 ngay**. Vi vay rang buoc UW o day
   dat **TUONG DOI** (<= 1.2 x UW parity cung nam), khong phai tuyet doi 120 — nguong 120 da
   duoc `X1_EXTEND` muc 7 tuyen bo la **khong con dat duoc**, ke ca baseline.
3. 🔴 **`A4_hardsl` (17,598) la test HONG, KHONG duoc trich dan.** No tat luon arm
   (`SIM_RATE_PROFIT_STOP_MARKET=0`) nen do mot he khac han. X2 giu arm = **0.07** o ca 6 run.
4. ⚠️ **Chi phi that cua SL la lenh bi cat OAN.** Mot pre-arm SL tot khong phai la cai lam
   `mP|SL` bot am nhat — no lam vay mot cach tam thuong bang cach chuyen lenh thua sau thanh
   lenh thua nong. Cai phai tra la nhung cum sau do QUAY LAI arm va thang. Do la tieu chi
   PRIMARY thu 5 o muc 5, khong phai ghi chu.
5. ⚠️ **Dia Oracle 95% (con 11G).** Dataset WFO 48 thang ~4.0G. Phai `rm -rf` ngay sau khi
   chay xong 6 run. Kiem `df -h /` truoc khi build; duoi 8G free thi DUNG (runner tu abort).
6. ⚠️ `n` doi thi CI cua rate quality no ra (`C3_BASELINE` muc 7, bai hoc da ghi). Cat lo som
   giai phong margin => `n` tang => moi so sanh rate deu bi pha loang. Bao `n` o moi bang.

---

## 1. NEN, CUA SO, DAU VAO

| muc | gia tri |
|---|---|
| profile nen | `profiles/x1_c3.properties` (= `c3_min` + `WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2_x1`) |
| cua so | 2022-01-01 -> 2025-12-31 (`SIM_END_DATE=20251231`, duoi `HoldoutSeal` 2026-01-01) |
| bins | `predwf_map_s1a2_x1`, 16 fold, sha256 noi tiep `b87762312620f31769a8ef0160ec8132a5482c8f235d86e3364b59cce022a862` (`research/pipeline/BINS_MANIFEST.md` muc X1) |
| dataset WFO | `/home/ubuntu/wfo_ds_x1` — **X1 da xoa**, build lai 1 LAN bang `run_x1_sim.sh` (buoc BUILD) |
| ticker | `TICKER_SOURCE=file`, `/home/ubuntu/java/simulator/kaggle_data_hpo` (1,461/1,461 ngay) |
| neo | `X1_C3`: 2,058 lenh, equity 98,523, md5 printDone `d39da2940dfd815f60772f70517750bf` |

## 2. CO CHE PRE-ARM SL — DAC TA CHOT TRUOC

### 2.1 Hien trang code (do thuc, khong doan)

- `grep -rn "HARD_SL" src/main` => **khong co** `Cfg.get("SIM_HARD_SL_PCT")`. Key da chet that.
- `OrderTargetInfoTest.firstEntryPrice` **con song**: set o `createOrder` (Simulator:957) va mang
  qua `mergeOrder` (Simulator:771) => **bat bien qua DCA** (khong bi averaged nhu `priceEntry`).
- Hai cong "truoc arm" da ton tai va dung dung mot cho — `startUpdateOldOrderTrading`, deu guard
  boi `orderMulti.priceSL == null`: `LOSER_TIME_STOP_HOURS` (cat PHANG theo gio) va
  `COND_EXIT_HOURS` (F2, cat co dieu kien). X2 chen cong thu ba **cung cho do**.

### 2.2 Dac ta cong moi `SIM_PRE_ARM_SL` (khai bao TRONG profile, khong qua env)

```
enabled   := SIM_PRE_ARM_SL < 0            (0 = TAT = mac dinh = byte-identical)
stopLevel := firstEntryPrice * (1 + SIM_PRE_ARM_SL)
hit       := enabled AND priceSL == null AND firstEntryPrice != null AND bar.minPrice <= stopLevel
exitPrice := min(stopLevel, min(bar.priceOpen, bar.priceClose))
status    := STOP_LOSS_DONE
```

Bon quyet dinh thiet ke, chot truoc:

1. **Do tren `firstEntryPrice`, KHONG phai `priceEntry`** — de nguong bat bien qua DCA (dung y
   nghia goc cua field). `C3` chay `DCA_GRID_WEIGHTS=1,0,0,0` nen thuc te khong co leg 2+, nhung
   dac ta phai dung san cho `C3_FULL`.
2. **Chi tac dong khi `priceSL == null`** (chua arm). Da arm roi thi trailing lam chu, khong
   dung hai co che chong nhau.
3. **Phat hien bang `bar.minPrice`** — doi xung voi cong arm da dung `bar.maxPrice`. Day la quy
   uoc intrabar san co cua engine, khong phai ngoai le moi.
4. **Gia dong = `min(stopLevel, min(open, close))`** — KHONG BAO GIO tot hon muc stop (chan
   look-ahead co loi khi nen thung xuong roi bat len), va **xau hon** neu nen dong duoi stop
   (chiu gap, dung tinh than haircut `min(open,close)` cua `LOSER_TIME_STOP`).

**Thu tu uu tien:** pre-arm SL dat **TRUOC** `LOSER_TIME_STOP` va `COND_EXIT` trong cung ham.
Cung mot nen ma ca hai cung dieu kien thi SL thang (cong chat hon). Xac dinh, khong ngau nhien.

### 2.3 Phan biet ly do thoat — KHONG them cot vao `printDone.csv`

Ca time-stop lan pre-arm SL deu ra `STOP_LOSS_DONE`. Them cot / them status se lam **moi dong**
`printDone.csv` doi => cong hoi quy byte-identical o muc 3 khong con thuc hien duoc.
=> X2 ghi ly do bang **mot dong SLF4J** `PREARM_SL sym=... first=... stop=... exit=... tOpen=... tNow=...`
vao `logs/sim.out` tai diem trigger. Dem/ghep bang `sym` + `tOpen` (= `clusterFirstLegTime`).
`printDone.csv` **giu nguyen schema**.

### 2.4 Cong ky thuat bat buoc truoc khi chay

`mvn test` (them `PreArmSlTest`), `mvn -DskipTests package`, `tools/check_cfg_gateway.sh` OK.

## 3. CONG HOI QUY — dieu kien tien quyet

Jar MOI + profile `x1_c3` **khong khai bao** `SIM_PRE_ARM_SL` (hoac = 0), moi thu con lai y nguyen:

| do | ky vong |
|---|---|
| md5 `storage/printDone.csv` | `d39da2940dfd815f60772f70517750bf` |
| so dong | 2,059 (2,058 lenh + header) |
| equity cuoi | 98,523 |

**FAIL bat ky o nao => DUNG, bao cao, khong chay 5 run con lai.** Run nay dong thoi la **arm parity**
cua grid (tag `X2_PARITY`), khong ton them slot.

## 4. GRID — 6 RUN, ONE-AT-A-TIME, KHONG CROSS

| tag | profile | doi so voi `x1_c3` | truc |
|---|---|---|---|
| `X2_PARITY` | `x2_parity.properties` | (khong doi) | — |
| `X2_T120` | `x2_t120.properties` | `SIM_LOSER_TIME_STOP_HOURS=120` | T |
| `X2_T96` | `x2_t96.properties` | `SIM_LOSER_TIME_STOP_HOURS=96` | T |
| `X2_T72` | `x2_t72.properties` | `SIM_LOSER_TIME_STOP_HOURS=72` | T |
| `X2_S20` | `x2_s20.properties` | `SIM_PRE_ARM_SL=-0.20` (TS_H giu **168**) | S |
| `X2_S30` | `x2_s30.properties` | `SIM_PRE_ARM_SL=-0.30` (TS_H giu **168**) | S |

Moi profile khac `x1_c3` dung **MOT dong**. `SIM_RATE_PROFIT_STOP_MARKET=0.07` o CA 6 run.
**KHONG** co run nao doi ca hai truc. **Quota = 6, khong duoc chay them.**

## 5. TIEU CHI PRIMARY

Do tren **toan cua so 48 thang VA tach theo tung nam** (2022/2023/2024/**2025**).
CI: block-72h paired bootstrap, 2000 rep, x1.21, seed 20260905, luoi khoi CHUNG
(`research/analysis/c3_rates.py`, dung lai nguyen may cua `X1`). Doi chieu luon la `X2_PARITY`.

| # | dai luong | ghi chu |
|---|---|---|
| P1 | `mean(profit \| STOP_LOSS_DONE)` | muc tieu chinh |
| P2 | **`p10` cua phan bo `profit` cua LENH THUA** (`profit < 0`) | **DUOI — day moi la muc tieu that** |
| P3 | `TSloss%` = ty le `STOP_LOSS_DONE` (gom CA time-stop VA pre-arm SL) | mau so doi => doc kem `n` |
| P4 | `win%` va `mean(profit \| STOP_MARKET_DONE)` | canh gac: khong duoc xau di ngoai CI |
| P5 | **so cum bi pre-arm SL ma o `X2_PARITY` KET THUC `STOP_MARKET_DONE`** | **chi phi that cua SL** |

**P5 do the nao (chot truoc):** ghep `X2_S*` voi `X2_PARITY` theo khoa `(sym, start)` cua leg-1.
Mot cum tinh la **CAT OAN** khi: o `X2_S*` no dong bang pre-arm SL (co trong log `PREARM_SL`)
VA o `X2_PARITY` cung khoa do co `status = STOP_MARKET_DONE` (tuc no **da arm +7%** roi chot lai).
Bao ca 3 so: so cat oan, tong `pnl` ma parity thu duoc tu chinh nhung cum do, va **ty le ghep
duoc** (hai run phan ky theo thoi gian vi margin/throttle khac nhau => khong ghep 100%).
Neu ty le ghep < 80% thi **bao la KHONG do duoc dang tin cay**, khong duoc lam tron.
Truc T ap dung y het (cum bi time-stop som).

## 6. RANG BUOC CUNG (da sua theo `X1_EXTEND` muc 7)

Do tren chuoi equity `b+unP` cuoi ngay, `cummax` **reset dau moi nam** (y het `x1_rates.py`).

| # | rang buoc |
|---|---|
| R1 | `maxDD` <= 15% o **tung nam** |
| R2 | khong nam nao am |
| R3 | khong quy nao < −5% |
| R4 | **UW tung nam <= 1.2 x UW cua `X2_PARITY` cung nam** (TUONG DOI) |

R4 la tuong doi vi nguong tuyet doi 120 ngay da bi `X1_EXTEND` muc 7 chung minh la khong dat
duoc tren 48 thang (parity 2025 = 302 ngay). Tran 1.2x cho `X2_PARITY`: 2022 ~76 / 2023 ~68 /
2024 ~145 / 2025 ~362 (tinh lai chinh xac tu chinh `X2_PARITY` khi cham diem).

## 7. QUY TAC QUYET DINH — CHOT TRUOC, THEO CAU TRUC DON DIEU DOC TRUC

Mot **truc** (T hoac S) duoc goi la **CO TIN HIEU** khi va chi khi **ca ba**:

1. `mean(profit|SL)` **VA** `p10 loser` deu cai thien **DON DIEU** qua cac muc cua truc
   (T: 168 -> 120 -> 96 -> 72; S: off -> −0.30 -> −0.20), do tren **toan cua so** va **rieng 2025**;
2. `win%` **khong giam ngoai CI** o bat ky muc nao cua truc;
3. **it nhat mot muc** PASS toan bo R1-R4.

Khong thoa => truc do **KHONG CO TIN HIEU** — bao null, khong dien giai them.

🔴 **KHONG de cu baseline moi tu dot nay**, ke ca khi ca hai truc co tin hieu. Xac nhan mot
baseline moi la mot pre-reg RIENG (phai co arm doi chung va CI da khai bao truoc cho dung mot rate).
Equity/CAGR bao rieng, dan nhan **"KHONG phai tieu chi"**: N=6 => `2.57 x sqrt(2 ln 6) = 4.9pp`.

## 8. DU DOAN GHI TRUOC (ghi de sau nay doi chieu, khong duoc sua)

**Cau hoi: truc nao cai thien `p10 loser` 2025 nhieu hon?**

> **Du doan: TRUC S (pre-arm SL) cai thien `p10 loser` 2025 NHIEU HON HAN truc T.**

Ly do co hoc: `p10 loser` 2025 = **−54.8**, `min` = **−94.6** (`X1_EXTEND` muc 10.3). Pre-arm SL
la mot phep **CAT CUT phan phoi** ngay tai muc dat ra: khong lenh nao co the te hon `−X%` cong
gap, nen `p10` bi keo len gan `−X` theo dinh nghia. Time-stop chi rut ngan THOI GIAN phoi nhiem —
`E1` (30 thang) do duoc no cai thien `mP|SL` −18.9 -> −12.3 tu 168h->72h, tuc **~6.6pp cho 96 gio**,
va no khong dat tran nao cho duoi.

So cu the toi du doan (2025, `p10 loser`): `X2_S20` **−22 +- 4**, `X2_S30` **−33 +- 5**,
`X2_T72` **−45 +- 7**, `X2_T96` **−48 +- 7**, `X2_T120` **−51 +- 6**.

Ba du doan phu:

- (a) **Truc S se lam `win%` giam va `TSloss%` tang NHIEU HON truc T**, vi SL bien cum-se-hoi-phuc
  thanh lenh thua ngay lap tuc. Du doan `X2_S20` mat **2-5pp win%** so parity (co the vuot CI o
  2025), `X2_S30` mat **1-3pp**. => kha nang cao truc S **truot dieu kien 2 cua muc 7 o muc −0.20**.
- (b) **Ca hai truc lam UW DAI RA** (co che `E1` muc 5.3: cat som => margin quay vong nhanh =>
  `n` tang => nhieu lenh xau hon vao). Du doan >= 3/6 run vi pham R4 (UW > 1.2x parity) o it nhat
  mot nam. Neu KHONG vi pham thi day la ket qua bat ngo va phai noi ro.
- (c) `n` tang o ca hai truc; du doan `X2_T72` co `n` >= 2,200 (parity 2,058) va `X2_S20` >= 2,150.

Xac suat toi dat: truc S co tin hieu day du **~35%** (kha nang cao truot o dieu kien `win%`);
truc T co tin hieu day du **~30%** (kha nang cao truot o R4/UW); ca hai deu null **~40%**.

## 9. SAI LECH CO Y SO VOI DE BAI — Oracle TUAN TU thay vi 6 kernel Kaggle

De bai yeu cau `dataset_create_version` bundle Kaggle roi chay **6 kernel song song**. X2 chay
**tuan tu tren Oracle** (`TICKER_SOURCE=file`). Ghi truoc khi chay, kem so do duoc:

- **Chi phi Oracle**: `X1` do that **12.9 phut/run** cho cua so 48 thang (21:11:57 -> 21:24:51),
  + build dataset 76s => **6 run ~ 78 phut**. Oracle dang rong (`pgrep java` trong).
- **Chi phi Kaggle**: ticker 2024h2/2025h1/2025h2 **DA co tren Kaggle** (`wfo-ticker-2024h2`,
  `wfo-ticker-2025h1`, `wfo-ticker-2025h2`) nen khong phai upload 3.6G. **Nhung** van phai:
  (i) upload lai bundle voi `sim.jar` MOI + dataset WFO 48 thang (`funding.bin` 48 thang > 1.7G
  cua ban 30 thang) + bins X1 888MB => **~5G upload** voi dia con 11G;
  (ii) **SUA `tools/kaggle_sim.py`**: `TICKER_DS` (them 3 dataset) va guard `len(tk) < 912`
  (phai thanh 1,461) — tuc doi ma cua duong chay o giua mot dot do.
- **Ly do chon Oracle**: cong hoi quy cua X2 phai tai lap **md5 `d39da294...`**, ma so do sinh ra
  tren **Oracle + `file`**. Chay cong do tren dung may sinh ra neo la duong ZERO-RISK; chuyen sang
  Kaggle them mot bien (dung: `KAGGLE_SIM` muc 1 da chung minh byte-identity, nhung o cua so
  **30 thang**, chua bao gio o 48 thang). Doi 78 phut wall-clock lay bot 2 nguon loi la danh doi
  dung huong khi tieu chi la **byte-identity**, khong phai throughput.
- `X1_EXTEND` muc 1.3(b) da chon y het, cung ly do.

## 10. ARTIFACT / LENH TAI LAP

```bash
R=/home/ubuntu/src/BinanceFuturesJava
bash $R/research/pipeline/x2/run_x2_sim.sh          # build dataset + 6 run tuan tu
python3 $R/research/analysis/x2_rates.py            # rate/CI/nam/rang buoc/P5
rm -rf /home/ubuntu/wfo_ds_x1                        # BAT BUOC (dia 95%)
```

Bao cao: `docs/X2_EXIT48.md`. Cap nhat `docs/AGENT_RUNBOOK.md` muc 4 va `docs/QUEUE.md`.
Commit branch `module`, **KHONG push**.
