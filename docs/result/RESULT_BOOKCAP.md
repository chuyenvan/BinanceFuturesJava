# RESULT_BOOKCAP — overlay tang BOOK/VON tren X1_C3_FULL (48 thang)

Tien dang ky: `docs/prereg/PREREG_BOOKCAP.md` commit **7e1bbf6** (2026-09-11 16:46:30 +07), chot TRUOC khi cai code
va truoc moi run. Thuc thi 2026-09-11 16:5x..18:09 (+07) tren Oracle, branch `module`.

Nen: `devrun/X1_C3_FULL_PARITY_R` (md5 printDone ca header `2478e90d4e6147bf4cc64f75967ef47d`, bo header
`e13bc39e625b8d2ceebb7b9194f7f4f0`, equity 111,428, n=2,266). Cua so 2022-01-01..2025-12-31
(`SIM_END_DATE=20251231`), bins `/home/ubuntu/predwf_map_s1a2_x1` KHONG rebuild, dataset `/home/ubuntu/wfo_ds_x1`
(da co, KHONG rebuild), `TICKER_SOURCE=file`, `EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json`.
KHONG cham HOLDOUT 2026, KHONG cham 242.

---

## 1. CONG NGHIEM THU (PREREG muc 1) — **PASS**

Chay lai `profiles/x1_c3_full.properties` bang jar MOI (da co overlay, 2 key khong khai = TAT) vao thu muc moi
`devrun/X1_C3_FULL_CAPOFF`:

| kiem | ket qua |
|---|---|
| `cmp -s <(tail -n +2 CAPOFF/printDone.csv) <(tail -n +2 PARITY_R/printDone.csv)` | **rc=0** |
| md5 printDone CA header, CAPOFF | `2478e90d4e6147bf4cc64f75967ef47d` — **khop** PARITY_R |
| md5 printDone BO header, CAPOFF | `e13bc39e625b8d2ceebb7b9194f7f4f0` — **khop** PARITY_R |
| so dong | 2,267 (2,266 lenh) hai ben |
| equity cuoi | `b:111428` hai ben; `done:339/2266/2266` hai ben |
| PROFILE_HASH | `135750e04d67c263` (y ban canonical X1_C3_FULL) |
| so dong `BOOK-CAP` / `D_BOOK_CAP` trong `CAPOFF/logs/sim.out` | **0** |
| `tools/check_cfg_gateway.sh` | **rc=0** ("khong co tham so giao dich nao lach cong Cfg") |
| `mvn -DskipTests -o package` | **BUILD SUCCESS**, rc=0 |

=> TAT overlay la **byte-identical**. Duoc phep chay 3 bien the.

### 1.1 Co che da cai (chot cung, khong lech PREREG)
- 2 key doc qua `Cfg.get` (khai trong PROFILE, KHONG doc env): `SIM_MAX_OPEN_POSITIONS` (int, <=0 / khong khai
  = TAT) va `SIM_MAX_OPEN_NOTIONAL_PCT` (float, <=0 / khong khai = TAT). Khai trong `Configs.java`
  (`BOOK_MAX_OPEN` / `BOOK_MAX_NOTIONAL_PCT` / `BOOK_CAP_ON`) qua `envInt`/`envFloat` — cung khuon
  `SIM_GATE_ROLLING_PCT` o commit `c1785b9`. Tien to `SIM_` da nam trong `Cfg.TRADING_PREFIXES` nen
  khong phai sua danh sach key.
- Diem cam: `SimulatorMarketLevelTicker1MStopLoss.createOrder(...)`, **CHI** khi
  `levelChange == PREDICT_SYMBOL_TRADE`, **SAU** gate thi truong/`AIRejectFilter` (va sau nhanh
  `GATE_COUNT_ONLY`) va **TRUOC** budget/tier. Leg `DCA_LEVEL1` / `BIG_DOWN` KHONG bi chan.
- `n_open` = so lenh dang mo (moi status chua DONE, moi level) = `counterOrderRunning()`.
  `notional` = sum(priceEntry x quantity) tren moi leg con mo (`openNotional()`; `LEVERAGE_ORDER=1`).
  `equity` = balance THUC HIEN `b` = `balanceBasic + profit` tai tick (KHONG mark-to-market).
- Vi pham => reject + `TickDecisionLog.D_BOOK_CAP` (ma moi = 9) + dem so lan chan / so tick co chan,
  in mot dong `[BOOK-CAP]` cuoi run qua SLF4J. Khong `System.out/err`, khong `printStackTrace`.
- KHONG sua exit / gate / selector / bins / 242 / `SHADOW_NO_PUSH`.

---

## 2. BA BIEN THE — bang chinh

3 profile = `x1_c3_full.properties` + DUNG 1 key (diff xac nhan chi them khoi BOOKCAP, khong doi key nao khac).

| tag | profile | key | PROFILE_HASH | md5 printDone |
|---|---|---|---|---|
| `X1_C3_FULL_PARITY_R` | `x1_c3_full.properties` | — | `135750e04d67c263` | `2478e90d4e61…` |
| `X1_C3_FULL_CAP12` | `x1_c3_full_cap12.properties` | `SIM_MAX_OPEN_POSITIONS=12` | `2ccaae3a0d201c41` | `e3c100bc2aff…` |
| `X1_C3_FULL_CAP16` | `x1_c3_full_cap16.properties` | `SIM_MAX_OPEN_POSITIONS=16` | `56e2b6c832b790b6` | `a462d967144f…` |
| `X1_C3_FULL_NOT40` | `x1_c3_full_not40.properties` | `SIM_MAX_OPEN_NOTIONAL_PCT=0.40` | `4d0a73e9348820a9` | `9abb835be2e2…` |

### 2.1 n + 5 rate + mMargin (mMargin CHI GHI) — `research/analysis/x1_rates.py`

| tag | n | win% | TSloss% | mP\|SM | mP\|SL | meanP | mMargin |
|---|---|---|---|---|---|---|---|
| PARITY_R | 2,266 | 84.69 | 14.96 | 7.333 | -19.570 | 3.308 | 1,945 |
| CAP12 | 1,810 | 83.92 | 15.36 | 7.405 | -19.654 | 3.249 | 2,105 |
| CAP16 | 1,987 | 84.00 | 15.85 | 7.444 | -19.463 | 3.179 | 2,070 |
| NOT40 | 2,082 | 84.29 | 15.47 | 7.460 | -19.613 | 3.273 | 2,072 |

### 2.2 Hieu (bien the - baseline) + CI khoi-72h x1.21 (2000 rep, seed 20260905), TOAN CUA SO

**CAP12** (n_A=1810 n_B=2266)

| rate | hieu | lo | hi | ngoai CI |
|---|---|---|---|---|
| n | -456.000 | -713.013 | -242.112 | YES (khong tinh) |
| win% | -0.764 | -2.151 | +0.652 | - |
| TSloss% | +0.399 | -1.128 | +1.764 | - |
| mP\|SM | +0.071 | -0.417 | +0.543 | - |
| mP\|SL | -0.084 | -2.086 | +2.315 | - |
| meanP | -0.060 | -0.618 | +0.494 | - |
| mMargin | +160.730 | +48.616 | +280.748 | YES (chi ghi) |

**=> so rate CHAT LUONG ngoai CI (bo n, mMargin): 0/5**

**CAP16** (n_A=1987 n_B=2266)

| rate | hieu | lo | hi | ngoai CI |
|---|---|---|---|---|
| n | -279.000 | -487.103 | -105.922 | YES (khong tinh) |
| win% | -0.691 | -1.867 | +0.484 | - |
| TSloss% | +0.893 | -0.070 | +1.889 | - |
| mP\|SM | +0.111 | -0.111 | +0.378 | - |
| mP\|SL | +0.107 | -0.765 | +1.094 | - |
| meanP | -0.130 | -0.460 | +0.249 | - |
| mMargin | +124.997 | +38.214 | +211.798 | YES (chi ghi) |

**=> so rate CHAT LUONG ngoai CI: 0/5**

**NOT40** (n_A=2082 n_B=2266)

| rate | hieu | lo | hi | ngoai CI |
|---|---|---|---|---|
| n | -184.000 | -323.890 | -60.110 | YES (khong tinh) |
| win% | -0.393 | -1.081 | +0.340 | - |
| TSloss% | +0.506 | -0.130 | +1.105 | - |
| mP\|SM | +0.127 | -0.059 | +0.341 | - |
| mP\|SL | -0.043 | -0.835 | +0.818 | - |
| meanP | -0.035 | -0.308 | +0.257 | - |
| mMargin | +127.577 | +51.835 | +208.171 | YES (chi ghi) |

**=> so rate CHAT LUONG ngoai CI: 0/5**

n_eff muc lenh (so khoi 72h co >=1 lenh): PARITY_R 174, ca 3 bien the 173 — khong mat suc phan giai.

### 2.3 Equity / CAGR — **CHI GHI, KHONG phai tieu chi** (PREREG muc 3/4)

| tag | equity cuoi | CAGR% |
|---|---|---|
| PARITY_R | 111,428 | 33.63 |
| CAP12 | 107,150 | 32.33 |
| CAP16 | 103,013 | 31.03 |
| NOT40 | 108,418 | 32.72 |

### 2.4 d CAGR — paired block-bootstrap equity ngay MTM (`research/analysis/ci_bookcap.py`)

Khuon y `ci_gatedyn.py`: equity = `b+unP` doc tu `logs/sim.out`, ban ghi cuoi ngay; moving-block circular,
block chinh 21 ngay (kiem 10 va 42), 2000 rep, seed 20260903; n ngay = 1,460 (2022-01-01..2025-12-30), lich
ngay 4 run TRUNG khop. Hieu chinh so sanh boi **k=3** bien the khoa truoc => nguong `sqrt(2 ln 3) = 1.4823 * sd_boot`.

| tag | d (pp) | lo95 | hi95 | sd_boot | P(d>0) | nguong 1.4823*sd | so voi nguong |
|---|---|---|---|---|---|---|---|
| CAP12 | -1.301 | -9.362 | +8.700 | 4.536 | 0.359 | 6.724 | khong vuot |
| CAP16 | -2.597 | -7.054 | +0.720 | 1.993 | 0.074 | 2.954 | khong vuot |
| NOT40 | -0.911 | -2.953 | +1.524 | 1.161 | 0.216 | 1.721 | khong vuot |

Ben theo do dai block: doi block 21 -> 10 -> 42, `sd_boot` doi <=0.3 (CAP12 4.54/4.24/4.51; CAP16 1.99/1.97/2.04;
NOT40 1.16/1.16/1.15) — ket luan khong phu thuoc do dai block.
CI95 cua ca 3 **chua 0** => d CAGR khong phan biet duoc voi 0. Theo PREREG muc 4, **d CAGR khong doi duoc phan
quyet du dau nao**.

(CAGR trong bang nay tinh tu chuoi equity ngay 1,460 diem nen lech ~0.05pp so voi bang 2.3 cua `x1_rates.py`:
PARITY_R 33.58 vs 33.63. Khac phuong phap tinh, khong phai khac du lieu.)

---

## 3. QUAN SAT THEO NAM

### 3.1 Rang buoc cung theo nam — TUYET DOI (maxDD<=15%, UW<=120, nam khong am, quy>=-5%)

Bang `x1_rates.py` (maxDD/UW tinh tren chuoi equity CAT trong nam).

| tag | nam | maxDD% | UW | ret_nam% | quy_min% | PASS tuyet doi |
|---|---|---|---|---|---|---|
| PARITY_R | 2022 | -12.46 | 64 | +17.30 | +0.63 | PASS |
| PARITY_R | 2023 | -2.51 | 45 | +60.43 | +7.80 | PASS |
| PARITY_R | 2024 | -11.36 | 121 | +45.36 | -4.64 | **FAIL** (UW 121) |
| PARITY_R | 2025 | -10.60 | 227 | +16.45 | -2.47 | **FAIL** (UW 227) |
| CAP12 | 2022 | -11.40 | 137 | +19.97 | -0.96 | **FAIL** (UW 137) |
| CAP12 | 2023 | -2.51 | 45 | +59.08 | +7.79 | PASS |
| CAP12 | 2024 | -12.51 | 244 | +30.44 | -5.93 | **FAIL** (UW 244, quy -5.93) |
| CAP12 | 2025 | -9.92 | 240 | +23.04 | -2.35 | **FAIL** (UW 240) |
| CAP16 | 2022 | -12.61 | 64 | +18.78 | +0.53 | PASS |
| CAP16 | 2023 | -2.51 | 45 | +59.71 | +7.80 | PASS |
| CAP16 | 2024 | -10.97 | 136 | +40.58 | -5.52 | **FAIL** (UW 136, quy -5.52) |
| CAP16 | 2025 | -10.82 | 302 | +10.43 | -2.47 | **FAIL** (UW 302) |
| NOT40 | 2022 | -11.79 | 64 | +19.73 | +0.57 | PASS |
| NOT40 | 2023 | -2.51 | 45 | +59.64 | +7.80 | PASS |
| NOT40 | 2024 | -10.96 | 129 | +42.79 | -4.69 | **FAIL** (UW 129) |
| NOT40 | 2025 | -11.22 | 232 | +13.56 | -2.47 | **FAIL** (UW 232) |

**TUONG DOI voi baseline** (baseline TU NO da FAIL 2/4 nam — rang buoc tuyet doi nay chua tung duoc X1_C3_FULL
thoa man): CAP12 hong THEM nam 2022 (UW 64 -> 137) va lam UW 2024 xau gap doi (121 -> 244), 2025 240 vs 227,
quy_min 2024 tu -4.64 sang -5.93 (vuot nguong -5). CAP16 giu 2022 (UW 64) nhung UW 2025 302 vs 227 va quy_min
2024 -5.52 (vuot). NOT40 gan baseline nhat: UW 2024 129 vs 121, 2025 232 vs 227, khong lam vo them nguong quy nao.
**KHONG bien the nao cai thien UW o bat ky nam nao.**

### 3.2 maxDD theo nam — hieu so voi baseline (duong = TOT hon, it am hon)

| tag | 2022 | 2023 | 2024 | 2025 | so nam TOT hon |
|---|---|---|---|---|---|
| CAP12 | **+1.05** | +0.00 | **-1.15** | **+0.68** | 2/4 |
| CAP16 | -0.15 | -0.00 | **+0.39** | -0.22 | 1/4 |
| NOT40 | **+0.67** | +0.00 | **+0.40** | -0.62 | 2/4 |

2023 la nam maxDD y het nhau (-2.51 ca 4 run) — khong tinh la "tot hon".

### 3.3 Collapse-day, ngay te nhat, book mo (tu `printDone.csv`, khuon `dev_collapse_check.py`)

collapse-day = ngay co >=4 lenh dong `STOP_LOSS_DONE`. `pnl_ngay_te` = tong pnl cac lenh DONG trong ngay do.
`open` = so lenh dang mo tai ngay D (start <= D < end).

| tag | nam | n | collapse-day | pnl ngay te nhat | ngay | open_max | open_p90 |
|---|---|---|---|---|---|---|---|
| PARITY_R | 2022 | 406 | 5 | -3,749 | 2022-05-12 | 30 | 7.0 |
| PARITY_R | 2023 | 308 | 1 | -1,636 | 2023-10-23 | 21 | 4.0 |
| PARITY_R | 2024 | 668 | 9 | -5,448 | 2024-04-17 | 27 | 8.5 |
| PARITY_R | 2025 | 884 | 10 | -8,415 | 2025-11-12 | 29 | 11.0 |
| CAP12 | 2022 | 317 | 3 | -3,190 | 2022-05-12 | 17 | 5.0 |
| CAP12 | 2023 | 289 | 1 | -1,674 | 2023-10-23 | 12 | 4.0 |
| CAP12 | 2024 | 517 | 8 | -5,313 | 2024-04-17 | 16 | 7.0 |
| CAP12 | 2025 | 687 | 5 | -4,896 | 2025-04-21 | 15 | 9.0 |
| CAP16 | 2022 | 356 | 4 | -3,549 | 2022-05-12 | 22 | 7.0 |
| CAP16 | 2023 | 297 | 1 | -1,657 | 2023-10-23 | 16 | 4.0 |
| CAP16 | 2024 | 587 | 8 | -5,527 | 2024-04-17 | 19 | 8.0 |
| CAP16 | 2025 | 747 | 10 | -7,953 | 2025-11-12 | 17 | 9.0 |
| NOT40 | 2022 | 376 | 4 | -3,486 | 2022-05-12 | 22 | 7.0 |
| NOT40 | 2023 | 296 | 1 | -1,670 | 2023-10-23 | 15 | 4.0 |
| NOT40 | 2024 | 600 | 8 | -5,568 | 2024-04-17 | 19 | 8.0 |
| NOT40 | 2025 | 810 | 10 | -8,012 | 2025-11-12 | 24 | 10.0 |

Tong collapse-day 48 thang: baseline **25**, CAP12 **17**, CAP16 **23**, NOT40 **23**.
Ngay te nhat 2025 (2025-11-12, -8,415) chi CAP12 tranh duoc (ngay te nhat cua CAP12 la 2025-04-21, -4,896).

**Luu y co che:** `open_max` VUOT tran o ca 3 bien the (CAP12 max 17 > 12; CAP16 max 22 > 16). Dung nhu thiet ke:
cap CHI chan leg `PREDICT_SYMBOL_TRADE`; leg `DCA_LEVEL1` va `BIG_DOWN` di qua tu do nen book van co the vuot
tran. Day KHONG phai loi cai dat — do la dieu khoan chot cung o PREREG muc 1.

### 3.4 So lan cap chan / % tick co chan (dong `[BOOK-CAP]` trong `sim.out`)

| tag | lenh bi chan / ung vien toi tang cap | tick co chan / tick co ung vien | % (mau so = tick co ung vien) | % (mau so = 140,160 moc 15 phut cua 1,460 ngay) |
|---|---|---|---|---|
| CAP12 | 24,210 / 25,762 | 7,901 / 8,411 | **93.94%** | 5.64% |
| CAP16 | 16,460 / 18,184 | 5,388 / 6,003 | **89.76%** | 3.84% |
| NOT40 | 11,337 / 13,155 | 3,342 / 4,041 | **82.70%** | 2.38% |

Mau so ma CODE do la "tick co it nhat 1 ung vien `PREDICT_SYMBOL_TRADE` di qua gate va toi duoc tang cap" — do la
mau so dung cho cau hoi "khi co co hoi hanh dong thi cap co hanh dong khong". Cot cuoi la mau so rong (moi moc
15 phut cua ca cua so, ke ca tick khong he co ung vien) ghi kem de minh bach. **Duoi CA HAI mau so, dieu kien
"cap chan < 5% tick o CA 3 bien the" cua PREREG muc 4(c) KHONG thoa man** (CAP12 = 93.94% resp. 5.64%, deu >=5%).

---

## 4. PHAN QUYET (PREREG muc 4, khong doc cach khac, khong them bo loc hau kiem)

Bien the **PASS** <=> dong thoi (i) KHONG rate nao trong 5 rate xau di ngoai CI (toan cua so);
(ii) maxDD quan sat TOT hon baseline o >= 3/4 nam VA khong nam nao xau hon qua 1.0pp;
(iii) qua het rang buoc cung TUYET DOI theo nam.

| bien the | (i) 0/5 rate xau ngoai CI | (ii) maxDD >=3/4 nam tot hon & khong nam nao xau >1.0pp | (iii) rang buoc cung tuyet doi | **PHAN QUYET** |
|---|---|---|---|---|
| `X1_C3_FULL_CAP12` | DAT (0/5) | **KHONG DAT** — 2/4 nam tot hon; 2024 xau hon **1.15pp** (>1.0) | **KHONG DAT** — FAIL 3/4 nam (2022 UW 137, 2024 UW 244 + quy -5.93, 2025 UW 240) | **KHONG PASS** |
| `X1_C3_FULL_CAP16` | DAT (0/5) | **KHONG DAT** — 1/4 nam tot hon | **KHONG DAT** — FAIL 2/4 nam (2024 UW 136 + quy -5.52, 2025 UW 302) | **KHONG PASS** |
| `X1_C3_FULL_NOT40` | DAT (0/5) | **KHONG DAT** — 2/4 nam tot hon (xau nhat -0.62pp, trong nguong) | **KHONG DAT** — FAIL 2/4 nam (2024 UW 129, 2025 UW 232) | **KHONG PASS** |

### 4.1 Cach doc
- **(a) KHONG ap dung**: 0/3 bien the PASS, khong co nhanh "GIU MO", KHONG de xuat so giay thu 2 chay song song.
- **(c) KHONG ap dung**: cap chan 93.94% / 89.76% / 82.70% tick-co-ung-vien (5.64% / 3.84% / 2.38% neu lay mau so
  rong nhat) — khong bien the nao duoi 5%, va dieu kien doi hoi CA 3 deu duoi 5%. Co che **da that su duoc thu**,
  khong phai "chua co phep thu": no cat 8-20% so lenh (n 2,266 -> 2,082/1,987/1,810) va ha `open_max` tu 27-30
  xuong 15-24.
- **(b) AP DUNG** — 0 PASS, khong rate nao xau di ngoai CI toan cua so:
  **DONG "khong phan biet duoc / cap khong giup maxDD"**. Khong noi "cap thua".

### 4.2 Ghi kem, KHONG doi phan quyet
- maxDD toan cua so gan nhu bat dong: -12.46 (base) vs -12.51 / -12.61 / -11.79. Bien do <=0.8pp o ca 4 run.
- Do do **UW xau di co he thong** o phia cap (CAP12 2022 64->137 va 2024 121->244; CAP16 2025 227->302), khong nam
  nao tot hon. Nghia la cap keo dai thoi gian duoi dinh chu khong lam dinh nong hon. Day la so QUAN SAT mot lan,
  `PREREG_CI` 2.5 cam coi la co CI.
- Rieng **nam 2024**, CI theo nam cho CAP12 va CAP16 co **3/5 rate xau ngoai CI** (CAP12: win% -2.67 [-4.51,-1.01],
  TSloss% +2.50 [+0.78,+4.40], meanP -0.95 [-1.60,-0.32]; CAP16 cung 3 rate, bien do ~1/2). NOT40 0/5 moi nam.
  Tieu chi (i) cua PREREG dinh nghia tren TOAN CUA SO nen viec nay KHONG doi phan quyet — ghi lai vi no la bang
  chung nguoc chieu voi gia thuyet "cap giup".
- CAP12 la bien the duy nhat giam ro collapse-day (25 -> 17) va tranh duoc ngay te nhat 2025 (-8,415 -> -4,896).
  Nhung no cung la bien the lam UW xau nhat va la bien the duy nhat lam VO THEM nguong quy (-5.93 nam 2024).
  Hai dieu nay di cung nhau; khong duoc lay rieng nua ve co loi.
- d CAGR am nhe o ca 3 (-1.30 / -2.60 / -0.91 pp), CI95 deu chua 0 => khong ket luan duoc gi ve CAGR.
- mMargin TANG ngoai CI o ca 3 bien the (+161 / +125 / +128). Gia thuyet co hoc (CHUA do rieng, khong ket luan): it lenh dang mo hon =>
  `marginRunning` thap hon => throttle trong `TradeUtils.managerBudget` noi tay => moi lenh con lai to hon.
  Day la HE QUA co hoc cua cap, khong phai tin hieu chat luong (`mMargin` chi ghi theo PREREG muc 3).

---

## 5. NHUNG GI KHONG LAM / KHONG KET LUAN

- **Khong tune sau khi thay so.** Ba bien the la 3 con so khoa trong PREREG muc 2 (12 / 16 / 0.40). Khong chay
  them muc cap nao, khong ket hop count+notional, khong doi nguong, khong them bien the "cuu" CAP12.
- **Khong doi quy tac quyet dinh.** (i)(ii)(iii) va cach doc (a)/(b)/(c) doc y PREREG muc 4. Khong them bo loc
  hau kiem, khong doi mau so de ep (c) thanh dung, khong doi (ii) tu "3/4 nam" thanh "2/4".
- **Khong ket luan "cap thua"** — PREREG muc 4(b) cam cau chu do. Ket luan dung la: tren DEV 48 thang nay,
  cap book KHONG cai thien duoc maxDD theo nam, va lam UW xau di.
- **Khong ket luan gi tu CAGR/equity.** d CAGR am o ca 3 nhung CI95 chua 0 va nguong k=3 khong bi vuot.
- **Khong ket luan tu collapse-day cua CAP12.** 25 -> 17 la so QUAN SAT, khong co CI (PREREG muc 3 ghi ro
  "quan sat, khong CI"), va di kem UW xau hon + vo them nguong quy.
- **Khong suy ra gi cho LIVE.** `SIM_MAX_OPEN_NOTIONAL_PCT=0.40` chon vi no bang muc live 27 lenh/35k, nhung
  ket qua o day la ket qua DEV cua sim; khong dong nghia live nen/khong nen dat cap.
- **Khong cham**: HOLDOUT 2026, 242, `shadow_c3`, `SHADOW_NO_PUSH`, exit/gate/selector/TOPK/bins/arm/time-stop/
  giveback. Khong rebuild bins, khong rebuild dataset. Khong xoa devrun cua nguoi khac. Khong `git push`.
- **Khong de xuat so giay thu 2.** Do la nhanh (a) cua PREREG va nhanh do doi >=1 PASS; o day 0 PASS.
- Chua do: ly do UW xau di (gia thuyet "cap bo mat chain pump sinh lai nen duong equity leo doc cham hon"
  chua duoc kiem chung rieng). Khong ket luan.

---

## 6. TAI LAP

```bash
# 0. code
cd /home/ubuntu/src/BinanceFuturesJava && git checkout module
export PATH=/home/ubuntu/tools/apache-maven-3.9.9/bin:$PATH
./tools/check_cfg_gateway.sh && mvn -DskipTests -o package     # -> target/binance-java-sdk-1.2.4.jar

# 1. cong nghiem thu (byte-identical khi TAT)
/home/ubuntu/x1log/run_bookcap.sh X1_C3_FULL_CAPOFF \
    /home/ubuntu/src/BinanceFuturesJava/profiles/x1_c3_full.properties
cmp -s <(tail -n +2 /home/ubuntu/java/devrun/X1_C3_FULL_CAPOFF/storage/printDone.csv) \
       <(tail -n +2 /home/ubuntu/java/devrun/X1_C3_FULL_PARITY_R/storage/printDone.csv); echo rc=$?
md5sum /home/ubuntu/java/devrun/X1_C3_FULL_CAPOFF/storage/printDone.csv   # 2478e90d4e6147bf4cc64f75967ef47d
grep -c 'BOOK-CAP\|D_BOOK_CAP' /home/ubuntu/java/devrun/X1_C3_FULL_CAPOFF/logs/sim.out   # 0

# 2. ba bien the (TUAN TU, 1 slot java, ~13.5 phut/run)
/home/ubuntu/x1log/run3.sh

# 3. cham
cd research/analysis
python3 x1_rates.py X1_C3_FULL_PARITY_R X1_C3_FULL_CAP12    # va CAP16 / NOT40
python3 ci_bookcap.py                                        # -> /home/ubuntu/x1log/ci_bookcap.out
```

`run_bookcap.sh` la ban rut gon cua `runx()` trong `research/pipeline/x1/run_x1_sim.sh` (cung env
`WFO_DATA_DIR=/home/ubuntu/wfo_ds_x1 WFO_SMART_CACHE=1 SIM_END_DATE=20251231
EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json`, `-Xmx16g`, guard `pgrep java` rong + disk >=8G).

### 6.1 Artifact
- Code: `Configs.java` (+12), `TickDecisionLog.java` (+2, `D_BOOK_CAP=9`),
  `SimulatorMarketLevelTicker1MStopLoss.java` (+80).
- Profile: `profiles/x1_c3_full_cap12.properties`, `_cap16`, `_not40`.
- Script cham: `research/analysis/ci_bookcap.py`.
- Run dir (Oracle, GIU): `devrun/X1_C3_FULL_CAPOFF`, `X1_C3_FULL_CAP12`, `X1_C3_FULL_CAP16`, `X1_C3_FULL_NOT40`.
- Log cham (Oracle): `/home/ubuntu/x1log/{rates_CAP12,rates_CAP16,rates_NOT40,ci_bookcap}.out`,
  `/home/ubuntu/x1log/{bc_capoff,bc_run3,bookcap_build}.out`, `/home/ubuntu/x1log/{run_bookcap,run3}.sh`.
- Thoi gian: build 24s; 4 run sim ~13.5 phut/run (CAPOFF 17:00:38-17:13:56, CAP12 17:16:42-17:30:02,
  CAP16 17:30:02-17:43:15, NOT40 17:43:15-17:56:38); cham ~9 phut. Tong ~1h10.
