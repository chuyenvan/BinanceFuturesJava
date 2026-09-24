# RESULT_INTRADAY_DD — DRAWDOWN THAT (MTM moc PHUT) vs DRAWDOWN NGAY

Ket qua cua `research/analysis/intraday_dd.py` (thuan Python offline tren Oracle, **KHONG** Java/sim,
**KHONG** claude-run, **KHONG push**). Thuc thi `docs/PREREG_INTRADAY_DD.md` (chot TRUOC khi do).
DEV only: truc phut `2021-07-01 00:00Z .. 2025-12-30 23:59Z`, **khong doc 2026**.

Log: `/home/ubuntu/intradaydd/run2.log` · report: `/home/ubuntu/intradaydd/report_intraday_dd.txt` ·
JSON: `/home/ubuntu/intradaydd/intraday_dd.json` · chuoi phut (cache): `/home/ubuntu/intradaydd/series.npz`.

## 0. Parity artifact (md5 `printDone.csv` khop `RESULT_BLACKSWAN_2510` §0)

| nhan | run dir | md5 | profile | n leg | eq_final |
|---|---|---|---|---|---|
| **T170** | `kaggle_sim/out/t170-x1-2021` | `efb793e2…` | `x1_gs_t170` | 1,089 | 111,070 |
| **KEEPLEG0** | `java/devrun/FG_KEEPLEG0` | `99e42b75…` | `t170_flat_keepleg0` | 1,085 | 103,083 |
| **T100** | `kaggle_sim/out/hn-t100` | `dc16e4da…` | `x1_c3_full` | 2,559 | 121,770 |
| **GD92** | `kaggle_sim/out/hn-g92` | `cd913759…` | `x1_c3_full` | 2,632 | 133,944 |

`CAPITAL_START = 35,000`. Du lieu 1m: `/home/ubuntu/kaggle_data_hpo/ticker_YYYYMMDD.bin.gz`
(universe 112 sym o 2021-07-01 → 598 sym o 2025-12-30; day 2025-10-10 = 553 sym).

**Moi so duoi day la MOT quan sat lich su — KHONG co CI** (khong bootstrap duoc cho metric cummax).
Cac episode top-10 khong doc lap: chung chi la ~9 dot thi truong (2021-09, 2021-11→2022-05 LUNA,
2022-11 FTT, 2023-04, 2024-04, 2024-08, 2025-02, 2025-10, 2025-11) lap tren 4 nen.

---

## 1. VIEC 1 — nguon equity moc PHUT trong sim logs: **KHONG CO** (da doc THAT, khong tin comment)

Doc `logs/sim.out` cua 4 run, dong `c.b.c.r.BudgetManagerSimple: Update ...`:

- **Tan suat THAT: dung 1644 lan/run, 100% tai `HH:MM = 07:00`** (= 00:00Z) — tuc **1 moc/ngay**,
  2021-07-01 → 2025-12-30. **Khong co bat ky dong nao cua equity moc phut.**
- Format THAT (map theo `BudgetManagerSimple.updateBalance()` + format string dong 269):

```
Update YYYYMMDD HH:MM => b:<bal> pD:<dProfit> m:<marginRun> max:<marginMaxDate> <marginMaxMonth>
  unP:<unrealNow> unPMin:<runningMinUnreal> <unProfitDate=0> <unProfitMonth> <pct>
  done:<SL>/<ndone>/<ncreated> run:<nrun>/<maxrun> f:<funding>
```

- `b` = `balanceBasic + profit` (**realized**, net) · `unP` = `Σ calProfit()` cua cum dang chay
  (mark = `priceClose` tick hien tai) · **`unPMin` = `balanceIndex.unProfitMin` = `trueUnrealizedMin`**
  — do **moi tick** bang `bar.low` (`SimulatorMarketLevelTicker1MStopLoss` dong 262-268) nhung chi
  giu **DAY CHAY TICH LUY** (min khong giam), in ra 1 lan/ngay. ⇒ **`unPMin` KHONG phai "day trong
  ngay"**, va `b+unPMin` **khong phai** duong equity moc phut.
- `unProfitDate` (cot 9) luon `0` (writer cu `date2ProfitMin` da bi go); `unProfitMonth` la min-chay
  theo thang cua writer cu.
- ⇒ **Artifact KHONG co chuoi equity moc phut** ⇒ da **TAI TAO** tu du lieu 1m (muc 2).

`resume` cac `Task-119`/`Task-110` (maxDD_mtm / quarter equity) **co trong code HEAD nhung KHONG** in
ra metric nao trong 4 run nay (grep `mtm|minEquity|marginCall|MAXDD` = 0 dong).

## 2. VIEC 2a — cong nghiem thu tai tao (BAT BUOC, chay TRUOC khi bao cao maxDD/UW)

Contract (chot trong pre-reg §2.2, da kiem truoc khi do): tuple 1m THAT =
`(startTime, maxPrice, minPrice, priceClose, priceOpen, totalUsdt)` ⇒ `tup[1]=HIGH, tup[2]=LOW,
tup[3]=CLOSE, tup[4]=OPEN` (**comment `(o,h,l,c,v)` trong `jbin.py` la SAI**); kiem tren du lieu
that: 1440/1440 nen co `tup[1] >= max(tup[3],tup[4])`, `tup[2] <= min(...)`, va
`tup[4](t) == tup[3](t-1)` (median sai so `0.000000`).

```
realized(m) = Σ_{leg: end<=m} pnl ;  unP(m) = Σ_{leg: start<=m<end} qty*(P_sym(m) - entry)
equity_mtm(m) = 35,000 + realized(m) + unP(m)          (P = close; bien the: P = minPrice)
```

| kiem | noi dung | T170 | KEEPLEG0 | T100 | GD92 |
|---|---|---|---|---|---|
| **V1** | `35,000+Σpnl` vs `b_final` (1644/1644 ngay) | diff **0.15** | 0.18 | 0.17 | 0.01 |
| **V2** | `equity_mtm(00:00Z)` vs `b+unP` in ra, 1644 ngay | max \|err\| **1.90** | 5.37 | 6.48 | 6.89 |
| **V2-rel** | `max\|err\|/equity` (AMENDMENT-1 ≤ 0.05%) | **0.0045%** | 0.0129% | 0.0173% | 0.0198% |
| **V3** | `min_chay(unP_low)` vs `unPMin` in ra | −23800.8 vs −23800 (**0.003%**) | 0.001% | 0.001% | 0.003% |
| **V4** | equity tai moc in == daily artifact | PASS | PASS | PASS | PASS |
| **V5** | maxDD(minute series lay mau moc 0) vs maxDD(chuoi NGAY artifact) | −11.85 vs −11.84 (**0.002 pp**) | 0.001 pp | 0.003 pp | 0.002 pp |

**V1/V3/V4/V5 PASS tuyet doi.** `V3` la phep kiem manh nhat: **no tai tao dung con so `bar.low`
per-tick ma sim dung**, sai lech 0.001-0.003% (1/3 don vi tren ~23,000 USDT).

### AMENDMENT-1 (bo sung SAU khi V2 chay lan dau, ghi ro vi pre-reg §3 dat nguong tuyet doi ≤2 USDT)

- Nguong **tuyet doi** cua V2 (≤2 USDT/ngay) **FAIL 8/6576 ngay-run** (KEEPLEG0 2 · T100 2 · GD92 2
  + T170 0), max **6.89 USDT** — **tat ca 2 ngay lien tiep 2022-05-14/15 va 2022-05-28/29** (LUNA).
- Da dieu tra: chay lai 2 ngay do bang **float64** cho KQ Y HET float32 (6.23/6.46/6.48/6.89 khong
  doi) ⇒ khong phai do luu tru. Nguyen nhan con lai: tren vai symbol cum-dang-chay, `Σ qty*entry`
  cua leg != `cluster.quantity*cluster.priceEntry` (cum DCA/TP mot phan) — sai lech **tuyet doi
  ~6 USDT** tren equity ~35-40k.
- ⇒ Them **V2-rel** (sai so **tuong doi** ≤ 0.05% equity): **PASS ca 4 nen, max 0.0198%**.
  **Cach doc dung**: sai so tai moc in ≤ **0.02% equity** ⇒ khong the dich maxDD qua **0.04 pp**.
  Khong dung AMENDMENT-1 de che ket qua: ca hai con so (tuyet doi FAIL / tuong doi PASS) deu duoc
  bao cao. Khong doi contract tai tao, khong doi nguong ket luan §6.

## 3. VIEC 2b — maxDD + UW: NGAY vs PHUT (mark = close)

`maxDD` = `min(s/cummax(s) - 1)` (khuon `c3_rates.py`). `UW` = do dai run lien tuc dai nhat duoi
dinh chay; **NGAY dem theo ngay, PHUT quy doi `phut/1440` = ngay** (bao cao ca phut tho o JSON).

### 3.1 Toan ky (2021-07-01 .. 2025-12-30)

| nen | NGAY maxDD | NGAY UW | **PHUT maxDD** | **PHUT UW (ngay)** | **ΔmaxDD (pp)** | ΔUW (ngay) |
|---|---|---|---|---|---|---|
| T170 | −11.84% | 92 | **−19.96%** | 144.4 | **−8.12** | +52.4 |
| KEEPLEG0 | −11.21% | 147 | **−19.96%** | 147.2 | **−8.75** | +0.2 |
| T100 | −16.13% | 248 | **−26.26%** | 248.2 | **−10.13** | +0.2 |
| GD92 | −16.55% | 278 | **−24.30%** | 277.8 | **−7.76** | −0.2 |

### 3.2 Theo nam (maxDD% / UW-ngay; `cummax` reset dau nam)

**T170** = **KEEPLEG0** (hai run TRUNG NHAU tung phut; ty le equity = 1.0000 suot 2021, = 1.0621
CO DINH suot 2023-2024, lech nhau tu 2022-05-12 va 2025 — nen moi % drawdown giong nhau tuyet doi):

| nam | NGAY maxDD / UW | PHUT maxDD / UW | ΔmaxDD (pp) |
|---|---|---|---|
| 2021 | −2.46% / 37 | −11.05% / 37.0 | **−8.58** |
| 2022 | −11.84% / 72 (KEEP −11.21%) | −15.43% / 74.0 | −3.58 (−4.22) |
| 2023 | −2.73% / 63 | −5.03% / 64.4 | −2.30 |
| 2024 | −6.60% / 92 | −12.16% / 91.5 | −5.56 |
| 2025 | −4.23% / 52 | **−19.96% / 129.0** | **−15.73** |

**T100**:

| nam | NGAY maxDD / UW | PHUT maxDD / UW | ΔmaxDD (pp) |
|---|---|---|---|
| 2021 | −7.35% / 47 | −16.02% / 47.8 | −8.67 |
| 2022 | −12.46% / 64 | −20.89% / 98.8 | −8.44 |
| 2023 | −2.51% / 45 | −5.07% / 54.3 | −2.56 |
| 2024 | −11.36% / 121 | −17.07% / 127.8 | −5.70 |
| 2025 | −10.60% / 227 | **−26.26% / 224.3** | **−15.66** |

**GD92**:

| nam | NGAY maxDD / UW | PHUT maxDD / UW | ΔmaxDD (pp) |
|---|---|---|---|
| 2021 | −7.74% / 47 | −16.21% / 47.8 | −8.47 |
| 2022 | −13.21% / 69 | −21.45% / 69.0 | −8.25 |
| 2023 | −5.24% / 63 | −9.12% / 63.6 | −3.88 |
| 2024 | −11.36% / 114 | −17.07% / 113.4 | −5.71 |
| 2025 | −6.11% / 116 | **−20.89% / 112.0** | **−14.78** |

**Doc ra 3 dieu:**
1. **Chuoi NGAY che mat 7.8-10.1 pp** maxDD toan ky, va **14.8-15.7 pp** o nam 2025 — muc che giau
   **lon nhat o nam 2025**, dung nam co su kien 2025-10-10.
2. **Nen nao "xau nhat" DOI**: T170/KEEPLEG0 theo NGAY xau nhat la **2022** (−11.8%) nhung theo PHUT
   xau nhat la **2025** (−20.0%). Moi ket luan kieu "drawdown te nhat la 2022" la **he qua cua
   sampling ngay**.
3. **UW gan nhu KHONG doi** (|ΔUW| ≤ 0.2 ngay, tru T170 +52.4) — vi UW la do dai **thoi gian**
   duoi dinh, va diem in 00:00Z da roi xuong duoi dinh trong hau het cac ngay do. Ngoai le T170:
   NGAY 92 → PHUT 144.4 vi intraday co nhieu doan ngan (vai gio → vai ngay) tut roi hoi phuc **trong
   ngay**, chuoi NGAY khong thay. ⇒ **UW la metric BEN** voi sampling; **maxDD thi KHONG**.

### 3.3 [do ben] bien the `P = bar.low` (can duoi intrabar — cung cadence `unPMin` cua sim)

| nen | maxDD toan ky | UW (ngay) | nam xau | maxDD nam |
|---|---|---|---|---|
| T170 | **−24.27%** | 129.0 | 2025 | −24.27% |
| KEEPLEG0 | −24.16% | 147.2 | 2025 | −24.16% |
| T100 | **−29.92%** | 248.2 | 2025 | −29.92% |
| GD92 | −24.82% | 277.8 | 2025 | −24.82% |

⇒ dung `close` (chinh) hay `bar.low` (can duoi), **thu tu nen va nam xau nhat khong doi**.

## 4. VIEC 2c — TOP-10 cu giam INTRADAY sau nhat (toan ky, moc phut; gio = do dai gio)

`coin xau nhat` = attribution tai **phut day** (tinh lai `unP` tung coin tren leg dang mo).

**T170** (KEEPLEG0 giong het ve thoi diem/%, khac USD)

| # | dinh → day (UTC) | do sau % | gio | USD | coin xau nhat (% do sau) |
|---|---|---|---|---|---|
| 1 | 2025-09-25 00:09 → **2025-10-10 21:20** | **19.96** | 381 | 19,952 | AIA 18% (20 coin dang mo) |
| 2 | 2022-05-11 13:49 → 2022-05-12 07:17 | 15.43 | 17.5 | 6,607 | KNC 13% |
| 3 | 2022-11-08 18:34 → 2022-11-09 21:28 | 14.30 | 26.9 | 6,660 | **FTT 32%** |
| 4 | 2024-04-10 13:56 → 2024-04-13 21:29 | 12.16 | 79.5 | 8,805 | CKB 16% |
| 5 | 2021-11-26 09:45 → 2021-12-04 05:27 | 11.05 | 188 | 4,447 | ENJ 11% |
| 6 | 2021-09-07 12:04 → 2021-09-07 15:09 | 10.29 | 3.1 | 3,676 | STMX 13% |
| 7 | 2022-05-10 06:39 → 2022-05-11 12:51 | 9.65 | 30.2 | 4,062 | GAL 28% |
| 8 | 2025-02-03 00:57 → 2025-02-03 02:07 | 8.93 | 1.2 | 7,913 | VVV 12% |
| 9 | 2024-07-11 02:00 → 2024-08-05 06:25 | 7.53 | 604 | 5,460 | PENDLE 12% |
| 10 | 2022-11-11 14:47 → 2022-11-14 02:11 | 6.30 | 59.4 | 3,006 | SRM 24% |

**T100**

| # | dinh → day (UTC) | do sau % | gio | USD | coin xau nhat (% do sau) |
|---|---|---|---|---|---|
| 1 | 2025-03-03 00:20 → **2025-10-10 21:20** | **26.26** | 5,325 | 32,462 | AIA 10% (25 coin) |
| 2 | 2021-11-15 13:12 → 2022-05-12 07:17 | 24.08 | 4,266 | 9,802 | DAR 10% |
| 3 | 2024-04-10 13:59 → 2024-04-13 21:29 | 17.07 | 79.5 | 14,471 | BEL 16% |
| 4 | 2021-09-06 14:50 → 2021-09-07 15:09 | 13.22 | 24.3 | 5,120 | IOTA 9% |
| 5 | 2022-11-08 16:42 → 2022-11-09 21:28 | 12.63 | 28.8 | 5,716 | FTT 16% |
| 6 | 2025-10-29 18:53 → 2025-11-22 04:48 | 11.92 | 562 | 15,476 | TNSR 11% |
| 7 | 2025-02-02 20:25 → 2025-02-03 02:07 | 11.26 | 5.7 | 12,275 | GRIFFAIN 13% |
| 8 | 2022-11-11 13:28 → 2022-11-14 02:11 | 9.58 | 60.7 | 4,370 | FTT 30% |
| 9 | 2021-09-20 05:15 → 2021-09-21 21:19 | 8.88 | 40.1 | 3,479 | SRM 11% |
| 10 | 2024-12-07 00:20 → 2024-12-09 21:04 | 7.96 | 68.7 | 7,960 | TRX 17% |

**GD92**

| # | dinh → day (UTC) | do sau % | gio | USD | coin xau nhat (% do sau) |
|---|---|---|---|---|---|
| 1 | 2021-11-15 13:11 → 2022-05-12 07:17 | **24.30** | 4,266 | 9,410 | DAR 9% |
| 2 | 2025-08-14 17:59 → **2025-10-10 21:20** | 20.89 | 1,371 | 24,594 | AIA 13% (25 coin) |
| 3 | 2024-04-10 13:59 → 2024-04-13 21:29 | 17.07 | 79.5 | 13,999 | BEL 16% |
| 4 | 2024-08-02 00:18 → 2024-08-05 06:25 | 14.70 | 78.1 | 12,085 | AMB 12% |
| 5 | 2022-11-08 16:42 → 2022-11-09 21:53 | 14.45 | 29.2 | 5,996 | BAND 12% |
| 6 | 2021-09-06 14:50 → 2021-09-07 15:09 | 13.23 | 24.3 | 4,871 | IOTA 9% |
| 7 | 2025-02-02 23:47 → 2025-02-03 02:07 | 10.90 | 2.3 | 11,021 | GRIFFAIN 14% |
| 8 | 2023-04-28 02:05 → 2023-06-10 04:27 | 9.12 | 1,034 | 4,687 | HIGH 15% |
| 9 | 2021-09-20 05:15 → 2021-09-21 21:19 | 8.89 | 40.1 | 3,313 | SRM 11% |
| 10 | 2024-12-08 02:18 → 2024-12-09 21:04 | 8.46 | 42.8 | 7,986 | TRX 16% |

**Doc ra**: 8/10 cu giam sau nhat la **HE THONG** (coin xau nhat chi 9-18% do sau, 13-30 coin dang
mo) — tru 2022-11 la **FTT don le** (30-32%). **Khong co cu nao la "1 coin pha san"**. Danh sach
do sau khong doi neu dung `bar.low` (chi sau hon).

## 5. VIEC 2d — cua so `2025-10-09 .. 2025-10-13` (doi chieu `RESULT_BLACKSWAN_2510`)

`max drop` tinh bang dinh chay (peak TRUOC trough), khong phai min/cummax cat cua so:

| nen | NGAY (dinh chay dau W) | PHUT (close) | PHUT (bar.low) | chenh (pp) |
|---|---|---|---|---|
| T170 | **−0.00%** | **−19.57%** | −23.78% | −19.57 |
| KEEPLEG0 | **−0.00%** | **−19.57%** | −23.67% | −19.57 |
| T100 | **−0.00%** | **−20.41%** | −24.29% | −20.41 |
| GD92 | **−0.00%** | **−20.70%** | −24.48% | −20.70 |

Trough cua ca 4 nen = **`2025-10-10 21:20Z`** (giong het `RESULT_BLACKSWAN_2510` §A3: phut ALT sap
manh nhat). Neu tinh tu **dinh TRUOC W** (`2025-09-25 00:09`, muc 4 bang tren) thi drop phut =
**−19.96%** (T170/KEEPLEG0) — tuc **ca cu giam toan ky cua T170 nam gon trong 1 phut nay**.

**Sua 1 con so cua blackswan**: `RESULT_BLACKSWAN_2510` §2 ghi moc-to-market trong W = **−16.3…−17.6%**
(tinh tu `b+unPMin`, ma `unPMin` la **day chay toan ky** chu khong phai day trong ngay ⇒ nen so bi
tron). Do lai dung: **−19.6…−20.7%** (close) / **−23.7…−24.5%** (low). Ket luan cua blackswan **dung
HUONG va dung BAC DO** (daily che mat), nhung **thap hon thuc te ~3-4 pp**.

## 6. TRA LOI (a)(b)(c)(d)

**(a) Chuoi NGAY che mat bao nhieu pp?**
- Toan ky: **T170 −8.12 · KEEPLEG0 −8.75 · T100 −10.13 · GD92 −7.76 pp**.
- Theo nam, gap LON NHAT: **ca 4 nen deu o nam 2025**: T170/KEEPLEG0 **−15.73 pp**,
  T100 **−15.66 pp**, GD92 **−14.78 pp** (cac nam khac 2.3-8.7 pp).
- ⇒ che giau **lon nhat o nam 2025**, dung nam co su kien.

**(b) Co nen nao vuot tran `maxDD <= 40%` khi dung intraday khong?** **KHONG.**
Toan ky: T170 −19.96 · KEEPLEG0 −19.96 · T100 −26.26 · GD92 −24.30 (deu < 40%).
Nam xau nhat: −19.96 / −19.96 / −26.26 / −21.45 (deu < 40%).
Bien the `bar.low`: −24.27 / −24.16 / **−29.92** / −24.82 → **van duoi 40%**, nhung T100 chi con
cach tran **10.1 pp** (so voi 23.9 pp neu nhin chuoi NGAY — **bien an toan THUC nho hon ~2.4 lan**).

**(c) Co nen nao vuot `UW <= 250` theo intraday khong?** **CO — GD92: 277.8 ngay (toan ky).**
T170 144.4 · KEEPLEG0 147.2 · T100 248.2 · GD92 **277.8** (nam xau nhat deu <= 129 ngay).
Nhung GD92 **cung da vuot 250 tren chuoi NGAY** (278) ⇒ intraday **khong tao vi pham moi**.

**(d) Co lam doi huong verdict rui ro nao da ban khong?** **KHONG doi trang thai PASS/FAIL nao**
(0/4 nen doi). Nhung **phai danh dau 3 huong doc sai dang luu hanh**:
1. **Bien an toan thuc nho hon nhieu** (vd T100: 40% − 26.3% = 13.7 pp, khong phai 23.9 pp). Moi
   ket luan kieu "con cach tran 40% rat xa" la **SAI vi duoc do bang chuoi NGAY**.
2. **"Nam xau nhat la 2022" la SAI** voi T170/KEEPLEG0: theo phut nam xau nhat la **2025**
   (−19.96% vs −11.84% NGAY). Cac bang xep hang `maxDD theo nam` (vd `RISK_APPETITE` §3,
   `RESULT_GATESCALE` §3) **xep sai nam** — khong doi PASS/FAIL nhung doi **thu tu uu tien**.
3. **`qmin` (quy xau nhat) va `conc` CHUA do lai** — vong nay khong do ⇒ **khong duoc** dung ket qua
   nay de ket luan 3 muc do (§6 pre-reg).
Ket luan tong: **daily che mat that (7.8-10.1 pp toan ky; 14.8-15.7 pp o 2025) NHUNG khong verdict
rui ro nao doi huong** (khong tran `maxDD 40%`, khong tran `UW 250` moi).

## 7. Muc nao BO / gioi han (theo pre-reg §7, bo sung cai da thay that)

1. **KHONG mo hinh hoa margin call / thanh ly** (sim cung khong) ⇒ cac so tren la **can duoi cua
   rui ro thuc**, khong phai mo phong pha san. Xem §3.3 (`bar.low`) la can duoi chat hon cua chinh
   xap xi nay.
2. `P = close` bo qua duong di **trong nen 1m**; da bao cao them bien the `bar.low`. Khong suy dien
   duong di giua cac moc.
3. Khong tinh lai **funding/phi theo phut** (chi cong khi leg dong — giong sim).
4. **Sai so V2 tai moc in ≤ 0.02% equity** (AMENDMENT-1) ⇒ khong the dich ket qua maxDD qua 0.04 pp.
5. `unProfitMonth` (writer cu, min-chay theo thang) **BO khong dung**: no la day tich luy theo thang,
   khong phai day trong thang; va `unProfitDate` luon `= 0` nen khong dung duoc.
6. **Khong chay lai sim / khong doi code, profile, fitness** — chi doc artifact + 1m.
7. 4 nen duy nhat; khong suy rong ra tag khac (`X1_GS_T170`, `X1_C3_FULL_PARITY_R`... khong thuoc
   pham vi nay).
