# W1_SWEEP — quet cac truc CHUA TUNG SWEEP tren nen C2b

Pre-reg `docs/PREREG_W1.md` commit `e606b76`, commit TRUOC khi chay. Khong sua sau khi thay so.
DEV 2022-01-01..2024-06-30, `SIM_END_DATE=20240630`. **Khong chay VAL.**
Dataset dung chung `/home/ubuntu/wfo_ds_clean`, jar `binance-java-sdk-1.2.4.jar` (2026-09-05),
code `08a9c16`. 16 run (15 o quet + parity), tuan tu, 1 slot JVM, ~3.5 phut/run.

---

## 0. RUI RO / LO HONG — doc truoc

1. **`SIM_TS_MAX_GAP` (truc A) va `SIM_TS_PNOPUMP_WEAK_THR` (truc C) la KEY CHET trong sim.**
   5/5 run doi hai key nay ra `printDone.csv` **byte-identical voi parity**. Khong phai "khong
   co tin hieu" — la **khong co duong day**. Chi tiet co hoc o muc 1.
2. **Hau qua: mo ta exit trong `AGENT_RUNBOOK` muc 3 va `C2B_SPEC` la SAI cho sim.**
   Runbook ghi "cap 0.08 STRONG / 0.03 WEAK (ban le `symbolPred < 0.29`)". Thuc te trong sim
   **100% lenh chay nhanh WEAK, cap = 0.03**; nhanh STRONG **khong bao gio duoc goi**.
   `DumpConfig` in ra `sl_at_arm STRONG(score<=0.29)=0.0350` — dong do la **hien thi ly thuyet**,
   khong phai duong chay. Bat ky ket luan nao truoc day dua tren "C2b co cap 8% cho 88% lenh"
   deu phai xem lai.
3. **Truc D va truc E KHONG doc lap** — gate chi phu thuoc TI SO `SIM_MIN_MOMENTUM_15M /
   SIM_PREDICT_SYMBOL_RATE_MAX`. `W1_E010` byte-identical `W1_D012`; `W1_E012` byte-identical
   `W1_D010`. 4 run chi cho 2 diem thong tin. Xem muc 5.
4. **Truc F tron 2 thay doi** (da neu truoc trong pre-reg muc 0): bat DCA **va** cat size leg
   dau 50%/60%. `mean(margin)` tut 971 -> 593 -> 497. Phan lon cai "dep len" cua F la thu ma
   mot lenh nho hon cung tao ra, ma sizing thi **khong do duoc tren DEV** (RUNBOOK muc 4).
5. `E[max nhieu]` = 2.57 x sqrt(2 ln 16) = **6.05pp**. Khong o nao duoc chon vi equity.
6. **Khong de cu ung vien baseline moi.** Day la quet kham pha. Moi thu duoi day can mot
   pre-reg xac nhan rieng truoc khi dung.

---

## 1. Key nao TRO — va tai sao

Truoc khi chay: `grep -rn` trong `src/main` + `DumpConfig` voi tung profile.
**Ca 8 key deu duoc `Cfg.get` doc va deu doi gia tri hieu dung trong `DumpConfig`** =>
khong loai key nao khoi grid. Nhung **do hieu dung tren `DumpConfig` la chua du**: hai key
doi duoc gia tri ma van khong doi duoc mot lenh nao.

| key | DumpConfig doi? | printDone doi? | ket luan |
|---|---|---|---|
| `SIM_TS_MAX_GAP` | CO (`cap_strong`) | **KHONG** (3/3 muc) | **TRO trong sim** |
| `SIM_TS_PNOPUMP_WEAK_THR` | CO (`STRONG(score<=x)`) | **KHONG** (2/2 muc) | **TRO trong sim** |
| `SIM_TS_MAX_GAP_WEAK` | CO | CO (3/3) | song |
| `SIM_MIN_MOMENTUM_15M` | CO | CO | song (nhung trung truc voi E) |
| `SIM_PREDICT_SYMBOL_RATE_MAX` | CO | CO | song (trung truc voi D) |
| `DCA_GRID_WEIGHTS` | CO | CO | song |
| `DCA_GRID_SCALE`, `SIM_RATE_PROFIT_STOP_MARKET` | CO | CO | song |

### Co hoc — vi sao A va C chet

Duong trailing duy nhat (`TradeUtils.calRateLossDynamicBuyPNoPump`):

```java
maxGap = (pNoPump != null && pNoPump > pNoPumpWeakThres) ? TS_MAX_GAP_WEAK : TS_MAX_GAP;
gap    = min(maxProfitRate * TS_GIVEBACK_RATIO, maxGap);
```

`pNoPump` den tu `OrderTargetInfoTest.trailRate()`:

```java
Float pnp = (this.symbolPred != null) ? this.symbolPred : 1f;   // null -> coi nhu YEU
```

Doi tuong chay `updateTPSL`/`trailRate` la **cum da merge** (`symbol2OrderRunning[symbolId]`,
gan o `SimulatorMarketLevelTicker1MStopLoss.java:941`), va `mergeOrder()`
(`SimulatorMarketLevelTicker1MStopLoss.java:730-777`) **tao object MOI va KHONG chep
`symbolPred`** (no chep `firstEntryPrice`, `maeLow`, `maePeak`, `lastEntry`, `rateChange`,
`tickerOpen`, `marketLevelChange`, `clusterFirstLegTime`, `legCount`, funding — khong co
`symbolPred`, cung khong co `predict`/`marketData`).

=> tren cum dang chay `symbolPred == null` => `pnp = 1f` => `1f > thres` **luon dung** voi moi
`thres < 1` => **luon nhanh WEAK** => `TS_MAX_GAP` khong bao gio duoc doc, va `TS_PNOPUMP_WEAK_THR`
khong doi duoc gi (0.05 hay 0.60 deu cho cung ket qua).

Cot `symbolPred` trong `printDone.csv` **van co so that** (min 0.0723, p50 0.2416, max 0.5237)
vi `closeOrder()` ghi ra tu **object LEG** (`putOrderDone(order)` trong vong lap `orders`),
ma leg thi co `symbolPred` (gan o dong 924). **Nhin CSV se tuong trailing da dung symbolPred —
no chua bao gio dung.** Day la cai bay: bang chung gian tiep (cot CSV) mau thuan voi duong chay that.

Bang chung thuc nghiem khop chinh xac voi co hoc nay:
- `symbolPred` that co max **0.5237** < 0.60. Neu trailing dung symbolPred that thi `thres=0.60`
  phai lat **toan bo** 970 lenh sang STRONG => phai doi ket qua. **Khong doi.**
- `thres=0.05`: symbolPred that **100%** > 0.05 => phai lat 695 lenh (71.65%) sang WEAK => phai
  doi. **Khong doi.**
- Chi mot gia thiet giai thich duoc ca hai: `pnp = 1f` hang so.

---

## 2. Parity

| tag | md5 `printDone.csv` | b | so lenh |
|---|---|---|---|
| neo C2b | `8f7afdfb27b15f5b6d4c886700def93c` | 60390 | 970 |
| `W1_parity` | `8f7afdfb27b15f5b6d4c886700def93c` | 60390 | 970 |

**PARITY OK — byte-identical.** Batch chay tiep.
Moi run `rc=1` (khong phai fail — bay 1), deu co `done:` + `b:` va `printDone.csv` co dong.

---

## 3. TRUC A — `SIM_TS_MAX_GAP` (tran nha trailing STRONG)

| muc | 0.05 | **0.08 (base)** | 0.12 | 0.16 |
|---|---|---|---|---|
| md5 | `8f7afdfb...` | `8f7afdfb...` | `8f7afdfb...` | `8f7afdfb...` |
| moi rate | y het baseline | — | y het baseline | y het baseline |

**Khong mot rate nao doi. Khong mot lenh nao doi.** Khong phai null thong ke — la **key chet**.
=> **DONG TRUC.** Khong quet lai truc nay cho toi khi `mergeOrder` chep `symbolPred`
(hoac trailing doc symbolPred tu leg dau). Sau khi sua, truc nay **phai quet lai tu dau** —
gio ta chua biet gi ve no.

## 4. TRUC C — `SIM_TS_PNOPUMP_WEAK_THR` (ban le STRONG/WEAK)

| muc | 0.05 | **0.29 (base)** | 0.60 |
|---|---|---|---|
| md5 | `8f7afdfb...` | `8f7afdfb...` | `8f7afdfb...` |

**Khong doi gi.** Gia thiet cua de bai ("88.55% hang admit co score < 0.30 => ban le nam giua
dai van hanh => dich la lat hang loat lenh") **dung ve phan bo nhung vo nghia ve co hoc**:
ban le duoc so voi hang so `1f`, khong so voi score. => **DONG TRUC**, ly do giong truc A.

---

## 5. TRUC D + E — GOP LAM MOT (gate ratio)

`AIRejectFilter.checkSignalDynamic`: `dyn_thr = MIN_MOMENTUM_15M * max(AI_DYNAMIC_MIN,
symbolPred/RATE_MAX * AI_DYNAMIC_MULTIPLIER)`. Nhanh san (`AI_DYNAMIC_MIN=0.26787`) chi hoat dong
khi `symbolPred < 0.2080 * RATE_MAX` = 0.0208..0.0312 — ma `symbolPred` **min = 0.0723** =>
**nhanh san KHONG BAO GIO chay**. Con lai `dyn_thr = (MIN_MOM/RATE_MAX) * symbolPred * MULT`
=> gate **chi phu thuoc TI SO** `MIN_MOM / RATE_MAX`.

Xac nhan byte-identical (khong phai suy luan):

| tag | MIN_MOM | RATE_MAX | ti so | md5 | b | n |
|---|---|---|---|---|---|---|
| `W1_D010` | 0.010 | 0.15 | 0.0667 | `1bdac007...` | 55338 | 644 |
| `W1_E012` | 0.008 | 0.12 | 0.0667 | `1bdac007...` | 55338 | 644 |
| `W1_D012` | 0.012 | 0.15 | 0.0800 | `f4e08e08...` | 54475 | 504 |
| `W1_E010` | 0.008 | 0.10 | 0.0800 | `f4e08e08...` | 54475 | 504 |

=> 4 run = **2 diem thong tin**. Truc D va truc E la **cung mot truc**.

### Bang rate theo ti so gate

| ti so | **0.0533 (base)** | 0.0667 | 0.0800 | don dieu? |
|---|---|---|---|---|
| n lenh | 970 | 644 | 504 | **CO** (giam) |
| win% | 85.26 | 85.56 | 86.90 | **CO** (tang) |
| TSloss% | 15.15 | 15.06 | 13.29 | **CO** (giam) |
| mean(profit\|STOP_MARKET_DONE) | 7.476 | 7.830 | 7.859 | **CO** (tang) |
| mean(profit\|STOP_LOSS_DONE) | -18.896 | -18.894 | -19.580 | CO (yeu; buoc 1 la hoa 0.01%) |
| mean(profit) toan bo | 3.479 | 3.805 | 4.212 | **CO** (tang) |
| mean(margin) | 971 | 1006 | 1046 | **CO** (tang) |
| maxDD% | -13.12 | -10.33 | -9.94 | **CO** (tot len) |
| underwater (ngay) | 93 | **172** | **223** | **CO** (xau di) |

**Rate don dieu: win%, TSloss%, mean(profit|SM), mean(profit), mean(margin), n.**
**Rate KHONG don dieu: khong co** (mean(profit|SL) don dieu yeu, buoc dau nam trong dung sai hoa).

Doc: siet gate lam **chat luong tung lenh tot len don dieu** (win% len, time-stop it di,
lai trung binh cao hon) va **maxDD nho lai**, doi lai **so lenh sup 48%** va **underwater
dai gap 2.4 lan**. Day la danh doi giua chat luong lenh va tan suat/hoi phuc, khong phai
"tot hon" hay "te hon".

## 6. TRUC B — `SIM_TS_MAX_GAP_WEAK` (tran WEAK — tran DUY NHAT dang thuc su chay)

| muc | 0.015 | **0.03 (base)** | 0.05 | 0.08 | don dieu? |
|---|---|---|---|---|---|
| n lenh | 971 | 970 | 970 | 959 | yeu (co 1 buoc hoa) |
| win% | 85.07 | 85.26 | 85.26 | 85.09 | **KHONG** (len, hoa, xuong) |
| TSloss% | 15.35 | 15.15 | 15.15 | 15.33 | **KHONG** (xuong, hoa, len) |
| mean(profit\|STOP_MARKET_DONE) | 7.453 | 7.476 | 7.431 | 7.483 | **KHONG** |
| mean(profit\|STOP_LOSS_DONE) | -18.794 | -18.896 | -18.841 | -18.827 | **KHONG** |
| mean(profit) toan bo | 3.426 | 3.479 | 3.450 | 3.450 | **KHONG** |
| mean(margin) | 971 | 971 | 971 | 973 | **KHONG** |
| median(profit) | 6.305 | 5.499 | 4.499 | 4.499 | **CO** (giam) — xem canh bao |
| maxDD% | -12.68 | -13.12 | -13.57 | -13.67 | **CO** (xau di) — xem canh bao |
| underwater (ngay) | 95 | 93 | 93 | 81 | **KHONG** |

**KHONG MOT RATE DA DANG KY TRUOC nao don dieu.** Hai dai luong don dieu la `median(profit)`
va `maxDD` — **ca hai deu KHONG nam trong danh sach rate da pre-register** (`medP` khong duoc
liet ke o pre-reg muc 4; `maxDD` la **rang buoc**, khong phai rate). Theo quy tac da chot
(pre-reg muc 5): **truc B = NULL**.

Ghi lai de khong mat: `medP` giam don dieu 6.305 -> 5.499 -> 4.499 -> 4.499 khi noi cap la
**he qua so hoc truc tiep** cua `exit = peak - min(peak/2, cap)` (cap chat => chot sat dinh =>
median cao hon nhung nuoi it hon), khong phai phat hien ve thi truong. `maxDD` xau di don dieu
theo cap la quan sat dang mot pre-reg rieng, **khong duoc dung tu batch nay**.

## 7. TRUC F — `DCA_GRID_WEIGHTS` (bat DCA — CO CONFOUND SIZING)

| muc | **1,0,0,0 (base)** | 0.5,0.5,0,0 | 0.4,0.3,0.3,0 | don dieu? |
|---|---|---|---|---|
| n lenh | 970 | 992 | 1000 | **CO** (tang) |
| win% | 85.26 | 84.58 | 84.40 | **CO** (giam) |
| TSloss% | 15.15 | 16.13 | 16.10 | CO (yeu; buoc 2 hoa trong 0.2%) |
| mean(profit\|STOP_MARKET_DONE) | 7.476 | 7.535 | 7.624 | **CO** (tang) |
| mean(profit\|STOP_LOSS_DONE) | -18.896 | -18.091 | -17.370 | **CO** (bot lo) |
| mean(profit) toan bo | 3.479 | 3.402 | 3.600 | **KHONG** |
| mean(margin) | 971 | 593 | 497 | **CO** (giam) — CO HOC, khong phai phat hien |
| maxDD% | -13.12 | -9.12 | -7.62 | **CO** (tot len) |
| underwater (ngay) | 93 | 73 | 58 | **CO** (tot len) |

**Rate don dieu: win%, mean(profit|SM), mean(profit|SL), n, mean(margin), TSloss% (yeu).**
**Rate khong don dieu: mean(profit) toan bo.**

**Nhung phan lon cau truc nay la sizing, khong phai DCA.** `mean(margin)` tut 971 -> 497 la
**tat yeu so hoc**: tong trong so van = 1.0 nen `ladder` khong doi, nhung leg dau chi con
0.5/0.4 lan budget. maxDD -13.12 -> -7.62 va underwater 93 -> 58 la thu ma **bat ky lenh nho
hon nao** cung tao ra. Theo RUNBOOK muc 4, sizing **khong do duoc tren DEV**.

Phan **khong** giai thich duoc bang sizing: `mean(profit|STOP_LOSS_DONE)` di tu -18.90 len
-17.37 (bot lo 1.53pp, don dieu qua ca 3 muc). Nhom bi time-stop la kenh mat tien lon nhat
(RUNBOOK muc 4) va DCA ha gia von trung binh cua chinh nhom do. Day la **manh duy nhat cua
truc F dang mot gia thuyet co hoc rieng**, va no can mot thiet ke **giu nguyen size leg dau**
(bu `DCA_GRID_SCALE` cho tong khong doi) de tach khoi sizing. **Chua duoc ket luan gi o day.**

## 8. TRUC G — `N4_a8s175` (do cho du, khong phai truc quet)

`SIM_RATE_PROFIT_STOP_MARKET=0.08` + `DCA_GRID_SCALE=1.75`.

| | C2b | `W1_G_A8S175` |
|---|---|---|
| n lenh | 970 | 918 |
| win% | 85.26 | 82.14 |
| TSloss% | 15.15 | **19.17** |
| mean(profit\|STOP_MARKET_DONE) | 7.476 | 8.592 |
| mean(profit\|STOP_LOSS_DONE) | -18.896 | -17.649 |
| mean(margin) | 971 | 1059 |
| maxDD% | -13.12 | -13.61 |
| underwater (ngay) | 93 | **140** |
| quy te nhat | -3.7 (2022Q4) | **-5.3 (2022Q4)** |

**LOAI boi rang buoc cung: underwater 140 > 120 VA quy 2022Q4 = -5.3% < -5%.**
Arm cao hon (7% -> 8%) day them 4pp lenh sang time-stop 168h (TSloss 15.15 -> 19.17) — dung
kenh mat tien da biet la lon nhat.

⚠️ **So cu khong tai lap duoc**: ban 2026-09-03 ghi 61,148 / 974 lenh; chay lai hom nay tren
jar + dataset hien tai cho **61,592 / 918 lenh**. Khac jar va khac duong cau hinh (ban cu
chay truoc khi co profile). **Khong duoc ghep 2 so nay trong mot so sanh.**

---

## 9. RANG BUOC CUNG — maxDD <= 15%, underwater <= 120 ngay, khong nam am, khong quy < -5%, n >= 600

| tag | maxDD% | UW | nam am | quy min | n | ket qua |
|---|---|---|---|---|---|---|
| C2b / `W1_parity` | -13.12 | 93 | khong | -3.7 | 970 | PASS |
| `W1_B015` | -12.68 | 95 | khong | -3.7 | 971 | PASS |
| `W1_B05` | -13.57 | 93 | khong | -3.6 | 970 | PASS |
| `W1_B08` | -13.67 | 81 | khong | -3.3 | 959 | PASS |
| `W1_D010` = `W1_E012` | -10.33 | **172** | khong | -3.6 | 644 | **FAIL** UW |
| `W1_D012` = `W1_E010` | -9.94 | **223** | khong | -2.6 | **504** | **FAIL** UW, n |
| `W1_F55` | -9.12 | 73 | khong | -1.6 | 992 | PASS |
| `W1_F433` | -7.62 | 58 | khong | 0.0 | 1000 | PASS |
| `W1_G_A8S175` | -13.61 | **140** | khong | **-5.3** | 918 | **FAIL** UW, quy |
| A05/A12/A16/C005/C060 | = parity | | | | | PASS (nhung tro) |

Khong tag nao co nam am. Khong tag nao vi pham maxDD 15%.

---

## 10. PHAN QUYET TUNG TRUC

| truc | rate don dieu? | co muc pass rang buoc? | phan quyet |
|---|---|---|---|
| **A** `SIM_TS_MAX_GAP` | — | — | **KEY CHET** — khong co duong day. Dong truc, mo bug. |
| **C** `SIM_TS_PNOPUMP_WEAK_THR` | — | — | **KEY CHET** — cung nguyen nhan. Dong truc. |
| **B** `SIM_TS_MAX_GAP_WEAK` | **KHONG** (0/7 rate pre-reg) | co (3/3 muc pass) | **NULL** — dong truc |
| **D+E** gate ratio | **CO** (5 rate) | **KHONG** (ca 2 muc quet FAIL underwater) | **don dieu nhung bi rang buoc cung loai** => null cho ung dung, giu phat hien cau truc |
| **F** `DCA_GRID_WEIGHTS` | **CO** (5 rate) | **CO** (2/2 muc pass) | **CO TIN HIEU** — nhung bi confound sizing; chi manh sach la `mean(profit\|SL)` |
| **G** `N4_a8s175` | khong phai truc quet | **KHONG** | **LOAI** boi UW 140 + quy -5.3 |

**Khong de cu ung vien baseline moi tu batch nay** (dung pre-reg muc 0/6). Hai the mo:
1. Sua `mergeOrder` chep `symbolPred` roi **quet lai truc A va C tu dau** (gio la vung trang).
2. Pre-reg rieng cho DCA **tach khoi sizing**: giu `mean(margin)` khong doi (bu `DCA_GRID_SCALE`),
   chi kiem mot gia thuyet: DCA co ha `|mean(profit|STOP_LOSS_DONE)|` khong.

---

## 11. EQUITY — **KHONG PHAI TIEU CHI**

Dan nhan ro: `E[max nhieu]` voi N=16 la **6.05pp CAGR**; khoang cach giua cac o duoi day
nam trong hoac gan mien nhieu do. **Khong duoc chon o theo cot nay.**

| tag | equity cuoi | vs C2b |
|---|---|---|
| `W1_G_A8S175` | 61,592 | +1,202 (nhung FAIL rang buoc cung) |
| C2b / `W1_parity` | 60,390 | 0 |
| `W1_B015` | 59,993 | -397 |
| `W1_B05` | 60,385 | -5 |
| `W1_B08` | 59,890 | -500 |
| `W1_D010` = `W1_E012` | 55,338 | -5,052 |
| `W1_D012` = `W1_E010` | 54,475 | -5,915 |
| `W1_F55` | 50,698 | -9,692 |
| `W1_F433` | 49,042 | -11,348 |
| A05 / A12 / A16 / C005 / C060 | 60,390 | 0 (byte-identical) |

---

## 12. SAI LECH SO VOI PRE-REG (ghi de minh bach)

- De bai neu **18 run**; luoi liet ke ra dung **15 o + 1 parity = 16 run**. Pre-reg da ghi 16
  truoc khi chay va dung N=16 de tinh nguong nhieu (6.05pp thay vi 6.1pp).
- **Khong build lai dataset**: `/home/ubuntu/wfo_ds_clean` da co san va dang duoc cac batch
  gan day dung. Dia giu nguyen 16G truoc va sau batch. **Khong `rm -rf`** vi day khong phai
  dataset batch nay tao ra (pre-reg muc 7).
- Truc D/E gop lam mot **sau khi thay so** (byte-identical). Day khong phai doi pre-reg: grid,
  muc quet va tieu chi giu nguyen; chi la phat hien rang 4 run cho 2 diem.
