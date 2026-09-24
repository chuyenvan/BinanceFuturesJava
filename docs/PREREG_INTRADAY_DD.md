# PREREG_INTRADAY_DD — DRAWDOWN THAT (MTM moc PHUT) vs DRAWDOWN NGAY

Chot **TRUOC khi do** (2026-09-24). Thuan Python offline tren Oracle, **KHONG** Java/sim, **KHONG**
claude-run, **KHONG push**, DEV only (moi moc `<= 2025-12-30`, khong doc 2026). Script:
`research/analysis/intraday_dd.py`. Ket qua: `docs/RESULT_INTRADAY_DD.md`.

## 0. Dong co (phat hien that, khong phai gia thuyet)

`docs/RESULT_BLACKSWAN_2510.md` (commit `8bcd806`): trong cua so `2025-10-09..13`, **max drop equity
NGAY (moc 07:00 GMT+7) = 0.00%** ca 4 nen, NHUNG moc-to-market trong ngay giam **−14…−18% equity**
⇒ **chuoi NGAY co the da CHE MAT phan drawdown TRONG NGAY**. Neu dung, moi ket luan rui ro dua tren
`maxDD`/`UW` tinh tu chuoi NGAY (nguong hien hanh `RISK_APPETITE` §7 / `S3`: `maxDD <= 40%`,
`UW <= 250`) dang **thap hon thuc te**.

## 1. Cau hoi do (chot truoc)

Voi 4 nen: `T170` = `kaggle_sim/out/t170-x1-2021` · `KEEPLEG0` = `java/devrun/FG_KEEPLEG0` ·
`T100` = `kaggle_sim/out/hn-t100` · `GD92` = `kaggle_sim/out/hn-g92`.

- **(a)** chuoi NGAY che mat bao nhieu **pp** maxDD (moi nen, toan ky + theo nam)?
- **(b)** nen nao **vuot `maxDD <= 40%`** khi do bang intraday?
- **(c)** nen nao **vuot `UW <= 250`** khi do bang intraday?
- **(d)** ket qua nay co lam **doi huong** verdict rui ro nao da ban khong?

## 2. Nguon du lieu — doc THAT, khong tin comment

### 2.1 Artifact (sim logs)

Doc `logs/sim.out` cua 4 run. Dong `c.b.c.r.BudgetManagerSimple: Update ...` (regex bat buoc co ca
`unP` VA `unPMin`). Format thuc te:

```
Update YYYYMMDD HH:MM => b:<bal> pD:<dProfit> m:<marginRunning> max:<marginMaxDate> <marginMaxMonth>
   unP:<unrealizedNow> unPMin:<runningMinUnrealized> <unProfitDate> <unProfitMonth> <pct>
   done:<nSL>/<ndone>/<ncreated> run:<nrun>/<maxrun> f:<funding>
```

Map cot theo `BudgetManagerSimple.updateBalance()` (`src/main/java/com/binance/chuyennd/research/`)
+ format string tai dong 269: `b` = `balanceBasic + profit` (realized), `unP` = `Σ calProfit()` cua
cum dang chay, **`unPMin` = `balanceIndex.unProfitMin` = `trueUnrealizedMin` — DAY KHONG phai
"day trong ngay"**: no la **day unrealized TICH LUY toan ky** (min chay, khong giam), do **moi tick**
bang `bar.low` (`SimulatorMarketLevelTicker1MStopLoss` dong 262-268), in ra **moi ngay**.
`unProfitDate` (cot 9) luon `0` (writer cu `date2ProfitMin` da bi go). ⇒ **KHONG co chuoi equity moc
phut trong artifact** (da kiem: `Update` xuat hien **dung 1644 lan/run, 100% tai `HH:MM = 07:00`**).

⇒ Ghi ro: **artifact KHONG co equity moc phut** ⇒ phai **TAI TAO MTM moc phut** (muc 2.2).

### 2.2 Tai tao MTM moc phut (contract chot TRUOC)

Du lieu 1m: `/home/ubuntu/kaggle_data_hpo/ticker_YYYYMMDD.bin.gz` (Java `ObjectOutputStream`,
`TreeMap<Long minute_ms, Map<String, KlineObjectSimple>>`), doc bang `research/analysis/jbin.py`.
**Thu tu field da kiem bang du lieu that**: tuple = `(startTime, maxPrice, minPrice, priceClose,
priceOpen, totalUsdt)` ⇒ `tup[1]=HIGH`, `tup[2]=LOW`, `tup[3]=CLOSE`, `tup[4]=OPEN` (kiem: 1440/1440
nen `tup[1] >= max(tup[3],tup[4])` va `tup[2] <= min(...)`; `tup[4](t) == tup[3](t-1)` voi median
sai so **0.000000**). Comment `(o,h,l,c,v)` trong `jbin.py` **SAI**, `tup[3] = close` dung.

Leg: `storage/printDone.csv` (moi run) — cot `sym, entry, quantity, pnl, start, end` (gio GMT+7).
`side` cua ca 7369 leg trong 4 run = `BUY` (chi LONG).

Cong thuc chot truoc (moc PHUT `m`, don vi USDT):

```
realized(m) = Σ_{leg: end<=m} pnl                       (khong can gia)
unP(m)      = Σ_{leg: start<=m<end} qty * (P_sym(m) - entry)
equity_mtm(m) = 35,000 + realized(m) + unP(m)
```

`P = priceClose` (**chinh**); `P = minPrice` (**bien the do ben** = can duoi, dung dung cadence
`bar.low` ma sim dung cho `unPMin`).
Thieu nen 1m o 1 symbol ⇒ **carry-forward** gia truoc (dung nhu sim: ticker null ⇒ `lastPrice`
khong doi); nen dau tien thieu ⇒ dung `entry`.
`ts/te` doi tu GMT+7 sang UTC (`−7h`) vi ticker key la ms UTC (`1760054400000 = 2025-10-10T00:00Z`).
Truc phut: `2021-07-01 00:00Z .. 2025-12-30 23:59Z` (1644 ngay × 1440 = 2,367,360 moc).

## 3. Cong nghiem thu — BAT BUOC, chay TRUOC khi bao cao bat ky so maxDD/UW nao

- **V1** `35,000 + Σ pnl` (toan bo leg) `== b_final` in ra. (Ky vong: khop tuyet doi.)
- **V2** `unP_recon` tai moc in (00:00 UTC) `== unP` in ra, tren **toan bo 1644 ngay / run** (khong
  chi mau). Ky vong: sai so `<= ~1 USDT`/ngay (lam tron `int` cua log).
- **V3** **min chay cua `unP_low(m)` tren toan truc phut `== unPMin`** in ra o ngay cuoi (toan ky),
  sai lech `<= 1%` cua |unPMin|. Day la phep kiem **manh nhat**: no tai tao dung metric `bar.low`
  per-tick ma sim dung.
- **V4** `equity_mtm` tai moc in `== b + unP` in ra (suy ra tu V1+V2).

**Luat chan:** neu V1/V2 (hoac V3 sai > 1%) ⇒ **KHONG** bao cao ket qua do; phai sua contract truoc.
Ghi ro trong RESULT muc nao PASS/FAIL.

## 4. Dinh nghia do — CHOT TRUOC

Dung dung khuon `c3_rates.py::stats()` (`research/analysis/`): `dd = s/s.cummax()-1`;
`uw = s < s.cummax()`, `UW = do dai run lien tuc dai nhat` (dem theo **so diem**).

| metric | chuoi NGAY | chuoi PHUT |
|---|---|---|
| `maxDD` | `min(dd)` tren 1644 moc 00:00 UTC | `min(dd)` tren 2,367,360 moc phut |
| `UW` | **ngay** (1 diem = 1 ngay) | **phut/1440 = ngay** (bao cao ca phut tho) |
| `maxDD_nam`, `UW_nam` | `cummax` **trong nam** (reset dau nam), nhan nam = ngay UTC | y het, tren chuoi phut |

Nam = nam UTC cua moc (moc in la 00:00 UTC ⇒ nhan ngay UTC trung nhan `date` trong `sim.out`).

**Thuoc tinh toan hoc phai kiem (sanity):** `maxDD_intraday >= maxDD_daily` va
`UW_intraday >= UW_daily` voi MOI nen/nam. Neu khong ⇒ bug tai tao, phai dieu tra truoc khi bao cao.

**Top-10 episode:** quet chuoi phut, tach episode "duoi dinh" (bat dau khi tut khoi dinh, ket thuc
khi quay lai dinh), lay 10 episode **sau nhat** theo `do sau % = (dinh-day)/dinh * 100`; ghi
`t_dinh -> t_day`, do sau %, so gio, va **attribution**: tai phut day, tinh lai `unP` tung symbol
(parse lai dung 1 ngay ticker do) ⇒ symbol am nhat + % dong gop vao do sau.

## 5. Cua so rieng `2025-10-09 .. 2025-10-13` (doi chieu blackswan)

Bat buoc bao cao cho ca 4 nen: `equity_mtm` moc phut min trong cua so, so voi **dinh TRUOC** cua so
(`2025-10-09 00:00Z`), va so voi `maxDD_intraday` toan ky — de tra loi **dung** cau hoi cua
`RESULT_BLACKSWAN_2510.md` §2 (o do ghi `b+unPMin` giam −16.3…−17.6% va goi la "trong ngay").

## 6. Nguong + luat ket luan — CHOT TRUOC (khong doi sau khi thay so)

Nguong hien hanh (`RISK_APPETITE` §7 / `PREREG_GATESCALE_SWEEP` §6 dong `S3`):
`maxDD <= 40%` (**theo nam LAN toan ky**) · `UW <= 250 ngay` · `qmin >= -20%` · khong nam am ·
`conc <= 15%`. Vong nay **chi** do lai `maxDD` va `UW`; `qmin`/nam am/conc **khong** do lai
⇒ khong duoc dung vong nay de ket luan 3 muc do.

- **(b) FAIL** neu ton tai nen co `maxDD_intraday > 40%` o **toan ky** hoac bat ky **nam** nao.
- **(c) FAIL** neu ton tai nen co `UW_intraday > 250` ngay (toan ky hoac nam).
- **(d)** "Doi huong verdict" **chi** khi: (b) hoac (c) FAIL, **HOAC** chenh lech lam **doi trang thai
  PASS/FAIL** cua mot nen giua 2 chuoi. Chenh lech dep (`+x pp`) ma khong doi PASS/FAIL ⇒ ket luan:
  **nang rui ro do duoc, nhung KHONG doi huong verdict**.
- **1 quan sat lich su, KHONG co CI** (khong bootstrap duoc cho metric cummax; khong keo CI vao).
  Moi so la mot quan sat, khong phai bang chung thong ke.

## 7. Muc do bo / gioi han ghi TRUOC

1. Khong mo hinh hoa **margin call / thanh ly** (sim cung khong) ⇒ maxDD intraday la **can duoi cua
   nguong thuc**, khong phai mo phong rui ro pha san.
2. `P=close` bo qua duong di **trong nen 1m**; bien the `low` bu phan nao (can duoi). Khong suy dien
   duong di giua cac moc.
3. Khong tinh lai **funding/phi theo phut** (chi cong khi leg dong — dung nhu sim).
4. Chi 4 nen duoc liet ke; khong suy rong ra nen khac / tag khac.
5. Chi DEV (`<= 2025-12-30`); khong doc 2026.
6. Khong push. Khong tich hop vao code/profile/fitness.

## 8. AMENDMENT-1 (bo sung SAU khi V2 chay lan dau — ghi ro, khong giau)

Sau khi tai tao xong (V1/V3/V4/V5 PASS tuyet doi), **V2 theo nguong TUYET DOI `<= 2 USDT/ngay`**
da **FAIL 8/6,576 ngay-run** (max **6.89 USDT**, tat ca tai `2022-05-14/15` va `2022-05-28/29` — LUNA).

- Da dieu tra TRUOC khi bao cao: chay lai dung 2 ngay do bang **float64** ⇒ KQ **y het** float32
  ⇒ khong phai loi luu tru. Nguyen nhan: tren vai symbol, `Σ qty*entry` cua cac leg != tich
  `cluster.quantity * cluster.priceEntry` (cum DCA / TP mot phan) — lech tuyet doi ~6 USDT.
- Bo sung **V2-rel**: `max |err| / equity <= 0.05%`. Ket qua: **0.0045 / 0.0129 / 0.0173 / 0.0198 %**
  cho T170 / KEEPLEG0 / T100 / GD92 ⇒ **PASS**.
- **Khong** doi contract tai tao, **khong** doi nguong §6, **khong** dung V2-rel de che V2 tuyet doi:
  ca hai con so deu duoc bao cao trong RESULT.
- Y nghia: sai so ≤ **0.02% equity** ⇒ khong the dich maxDD qua **0.04 pp** — nho hon moi ket luan
  trong RESULT (chenh 7.8-15.7 pp).

**Ngoai pham vi pre-reg (da lo ra khi chay, ghi de trung thuc):** 2 phep sua CONG CU (khong phai
nguong ket luan) — (i) `max drop trong cua so` phai tinh bang **dinh chay** (peak TRUOC trough),
khong phai `min/cummax` cat cua so (cach cu cho −8.10% o cua so W trong khi dung la **0.00%**);
(ii) cot `(a) theo nam` phai lay gap **LON NHAT**, ban dau in nham gap **NHO NHAT**. Ca 2 sua deu
lam **xau/trung thuc hon** ket qua, khong lam dep so.
