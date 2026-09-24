# RESULT_PUMPDUMP_DETECT — do 4 detector "pump xong chuan bi dump" tren TOAN BO lenh (n=1089)

> **MO TA (descriptive) — KHONG chay sim, KHONG sua `.java`, KHONG push.**
> Thuc hien dung `docs/prereg/PREREG_PUMPDUMP_DETECT.md` (commit `f22bae0`). Script
> `research/analysis/pumpdump_detect.py`. Du lieu: `printDone.csv` T170 (n=1089) +
> `CLOSES_1H.bin` + `selector_pred_out/symbol_map.csv`. 2026-09-17.

## 0. TOM TAT (doc nhanh)

**Ca 6 feature / 4 detector deu NULL.** Khong detector nao dat ca 3 tieu chi chot truoc
(monotone + CI khong chua 0 + PnL rong >= 0). Ket qua nhat quan voi `mom30d` (postpump, NULL):
he vao lenh coin momentum, nen **extension cao cung chinh la nhung lenh LAI** — khong tach duoc
"pump sap dump" ra khoi "pump sap con bay" bang close.

Dau hieu gan nhat la **`accel_24h` (D4)**: ti le SUP don dieu tang theo decile (rho=0.744, D1 3.8%
→ D10 7.5%) — nhung CI hieu mean **van chua 0** ([-9.2, +22.4]) va loc lam PnL **XAU DI** (net am
o ca 3 nguong). => van NULL.

## 1. Nhom (GIU NGUYEN)

| nhom | dinh nghia | n |
|---|---|---|
| `SUP` | `profit <= -20` | **49** |
| `DOI_CHUNG` | con lai | **1040** |

## 2. Bang ket qua 6 feature / 4 detector

| detector | feature | n NaN | rho decile | monotone | D1→D10 SUP% | CI infl (x1.21) hieu mean | excl0 | PnL rong >=0 (p75/p90/p95) | **ket luan** |
|---|---|---|---|---|---|---|---|---|---|
| D1 ext-ngan | `ret_24h` | 15 | +0.679 | ✗ | 2.8→7.4 | [-1.7, +18.4] | ✗ | ✗/✗/✗ | **NULL** |
| D1 ext-ngan | `ret_72h` | 41 | +0.141 | ✗ | 6.7→6.7 | [-10.6, +34.8] | ✗ | ✗/✗/✗ | **NULL** |
| D2 ext-vs-MA | `ext_ma7` | 2 | +0.240 | ✗ | 4.6→8.3 | [-1.2, +5.4] | ✗ | ✗/✓/✓ | **NULL** |
| D2 ext-vs-MA | `ext_ma30` | 22 | +0.513 | ✗ | 2.8→9.3 | [-0.2, +13.1] | ✗ | ✗/✓/✓ | **NULL** |
| D3 rollover | `ddmag_72h` | 0 | **-0.018** | ✗ | 7.3→6.4 | [-6.3, +8.5] | ✗ | ✗/✗/✗ | **NULL** |
| D4 acceleration | `accel_24h` | 33 | **+0.744** | **✓** | 3.8→7.5 | [-9.2, +22.4] | ✗ | ✗/✗/✗ | **NULL** |

- `CI infl` = bootstrap block-72h (2000 rep, seed `20260905`) cho hieu mean (SUP - DOI_CHUNG),
  inflate x1.21 quanh tam. `excl0` = CI sau inflate khong chua 0.
- `PnL rong >=0` = `-(tong pnl lenh bi loc)` tai nguong p75/p90/p95 (what-if, KHONG re-run).

## 3. (a) Ti le SUP theo decile (moi feature)

Decile theo feature tang dan (rank-based, 10 bucket):

| feature | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 | rho |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ret_24h` | 2.8 | 3.7 | 4.7 | 2.8 | 3.7 | 5.6 | 5.6 | 5.6 | 3.7 | 7.4 | +0.679 |
| `ret_72h` | 6.7 | 2.9 | 4.8 | 2.9 | 5.7 | 2.9 | 4.8 | 4.8 | 3.8 | 6.7 | +0.141 |
| `ext_ma7` | 4.6 | 0.9 | 5.6 | 4.6 | 1.8 | 9.3 | 1.8 | 3.7 | 4.6 | 8.3 | +0.240 |
| `ext_ma30` | 2.8 | 2.8 | 4.7 | 3.7 | 2.8 | 6.6 | 4.7 | 5.7 | 2.8 | 9.3 | +0.513 |
| `ddmag_72h` | 7.3 | 3.7 | 5.5 | 2.8 | 2.8 | 3.7 | 5.5 | 2.8 | 4.6 | 6.4 | **-0.018** |
| `accel_24h` | 3.8 | 3.8 | 1.9 | 1.9 | 4.8 | 2.8 | 5.7 | 7.5 | 6.7 | 7.5 | **+0.744** |

- **D3 (`ddmag_72h`) hoan toan phang** (rho -0.018): do sau tu dinh 72h khong phan biet SUP.
- **D4 (`accel_24h`) don dieu nhat** (rho +0.744, D1 3.8% → D10 7.5%) — nhung CI van chua 0 (muc 4).

## 4. (b) Hieu mean SUP - DOI_CHUNG + CI bootstrap

| feature | SUP mean / median (n) | DC mean / median (n) | hieu mean | CI raw | **CI infl x1.21** | excl0 |
|---|---|---|---|---|---|---|
| `ret_24h` | +1.98 / -5.86 (49) | -6.37 / -9.62 (1025) | +8.35 | [-0.66, +16.06] | **[-1.69, +18.39]** | ✗ |
| `ret_72h` | +7.25 / -15.49 (48) | -2.73 / -18.37 (1000) | +9.98 | [-7.55, +29.99] | **[-10.58, +34.81]** | ✗ |
| `ext_ma7` | -2.77 / -2.10 (49) | -4.61 / -3.12 (1038) | +1.84 | [-0.77, +4.74] | **[-1.23, +5.41]** | ✗ |
| `ext_ma30` | -0.53 / -3.70 (49) | -6.98 / -7.73 (1018) | +6.44 | [+0.75, +12.10] | **[-0.20, +13.14]** | ✗ |
| `ddmag_72h` | +25.58 / +24.18 (49) | +24.70 / +22.87 (1040) | +0.87 | [-4.80, +7.58] | **[-6.29, +8.53]** | ✗ |
| `accel_24h` | +0.65 / +1.81 (49) | -6.97 / -7.69 (1007) | +7.62 | [-6.80, +19.55] | **[-9.25, +22.38]** | ✗ |

- `ext_ma30` CI raw (+0.75..+12.10) **chua 0 truoc inflate**, nhung sau inflate x1.21 con lai
  **[-0.20, +13.14]** → chua 0. Tat ca deu khong dat (b).
- Hieu mean deu duong nhe (SUP hoi cao hon DC) nhung sd_boot lon (4-10 pp), n=49 SUP qua nho.

## 5. (c) Bang danh doi (what-if, KHONG re-run)

Loc bo lenh co `feature > nguong`. "PnL rong" = `-(tong pnl lenh bi loc)` = (lo SUP tranh) - (lai mat).

| feature | nguong | gia tri | lenh loc | SUP loc (lo tranh USD) | LAI loc (lai mat USD) | lo-nhe loc | **PnL rong (USD)** |
|---|---|---|---|---|---|---|---|
| `ret_24h` | p75 | +6.59% | 269 | 17 (+17,968) | 235 (-29,624) | 15 | **-9,080** |
| | p90 | +26.84% | 108 | 8 (+8,797) | 94 (-13,951) | 5 | **-4,373** |
| | p95 | +43.12% | 54 | 5 (+4,643) | 44 (-6,212) | 5 | **-800** |
| `ret_72h` | p75 | +20.05% | 262 | 13 (+12,968) | 236 (-32,397) | 12 | **-16,233** |
| | p90 | +56.60% | 105 | 7 (+8,157) | 93 (-12,150) | 5 | **-2,976** |
| | p95 | +85.96% | 53 | 5 (+6,175) | 47 (-6,412) | 1 | **-164** |
| `ext_ma7` | p75 | +0.22% | 272 | 16 (+17,399) | 237 (-32,459) | 18 | **-11,510** |
| | p90 | +3.45% | 109 | 9 (+8,242) | 92 (-9,600) | 8 | **+175** |
| | p95 | +6.12% | 55 | 4 (+4,039) | 49 (-4,501) | 2 | **+97** |
| `ext_ma30` | p75 | +3.41% | 267 | 16 (+17,186) | 233 (-28,576) | 17 | **-8,378** |
| | p90 | +13.61% | 107 | 10 (+10,958) | 92 (-10,978) | 5 | **+749** |
| | p95 | +22.14% | 54 | 6 (+5,959) | 44 (-5,365) | 4 | **+1,239** |
| `ddmag_72h` | p75 | +37.60% | 265 | 12 (+9,923) | 239 (-36,159) | 14 | **-23,479** |
| | p90 | +48.73% | 109 | 7 (+6,099) | 95 (-21,043) | 8 | **-13,406** |
| | p95 | +54.80% | 54 | 4 (+3,040) | 47 (-13,010) | 3 | **-9,470** |
| `accel_24h` | p75 | +7.88% | 264 | 17 (+16,266) | 232 (-39,690) | 13 | **-20,957** |
| | p90 | +22.94% | 106 | 8 (+9,075) | 93 (-15,426) | 4 | **-5,195** |
| | p95 | +38.68% | 53 | 6 (+6,100) | 43 (-8,310) | 4 | **-1,066** |

- **Mau chung ro ret**: o moi feature, so lenh **LAI bi loc** luon **nhieu hon gap ~10 lan** so
  lenh SUP, va tong lai mat >= lo tranh duoc. Loc "coin dang extension cao" **cat dung vao nguon
  loi** cua he momentum nay. Day la ly do cot loi PnL rong am o hau het nguong.

## 6. (d) So lenh NaN/khong do duoc

| feature | n NaN | % | ghi chu |
|---|---|---|---|
| `ret_24h` | 15 | 1.4% | coin niem yet < 24h |
| `ret_72h` | 41 | 3.8% | < 72h |
| `ext_ma7` | 2 | 0.2% | < 7 close |
| `ext_ma30` | 22 | 2.0% | < 30 close |
| `ddmag_72h` | **0** | 0% | chi can 1 close |
| `accel_24h` | 33 | 3.0% | < 48h |

## 7. KET LUAN

- **Ca 4 detector (6 feature) deu NULL** theo tieu chi chot truoc. Khong co bang chung "detect duoc
  pump sap dump" tu cac dau hieu extension-ngan / extension-vs-MA / rollover / acceleration o luc
  vao lenh, tren toan bo 49 lenh SUP.
- **Vi sao**: he vao lenh coin momentum (mean profit +5.24%), nen **extension/acceleration cao cung
  la dac diem cua nhung lenh LAI**. "Pump sap dump" va "pump sap bay" khong tach duoc bang close
  tai entry. D4 `accel_24h` la gan nhat (monotone) nhung CI chua 0 va cat vao loi.
- **DUNG** — khong de xuat ap dung, khong chay sim tiep.

## 8. CAN DU LIEU GI de lam duoc thu user mo ta ("nhin bieu do")

User noi "nhin bieu do thi thay de" — tuc pattern **body/wick/volume** ("nen xanh dai roi xuong",
blow-off volume, upper wick), khong phai chi close. Day la dieu **close-only KHONG do duoc**. May man:

| can gi | CO chua | o dau | ghi chu |
|---|---|---|---|
| **OHLCV 1m** (body/wick/volume) | **CO** | `ticker_*.bin.gz` (`/home/ubuntu/kaggle_data_hpo/`, 2021-01-01..2026-07-01, 636 symbol, OHLC + totalUsdt) | **chua dung trong lan nay** (detector chot la close-based). Da verify parse duoc (Java parser, BTCUSDT 2026-06-30 o/h/l/c/v = 60224.7/60224.7/60164.3/60188.0/7.14M) |
| **OI** (OI surge truoc dump) | CO | `oi_percoin_full.bin` (`claudedata/oi/`, 5m, oiDelta/z/ls/taker, 863 symbol) | follow-up co the do "OI tang dot bien truoc dump" |
| **Funding rate that** (lich su) | **KHONG** | chi live `derivs_store/funding.csv` (tu 2026-09-12) | `funding.bin` la score selector, KHONG phai rate. Can tai `data.binance.vision monthly/fundingRate/<S>/` (2020-01..) neu can |

**Huong follow-up (KHONG de xuat con so, chi neu huong):** do truc tiep pattern candle tren
`ticker_*.bin.gz` 1m quanh thoi diem entry cua 49 lenh SUP vs DOI_CHUNG (body/wick ratio, volume
spike, upper wick, "long green then red reversal" truoc khi vao). Day la thu user thuc su mo ta
va **du lieu da co san** — chi chua ai do.

## 9. Gioi han (phai ghi)

- Close-only (detector close-based, do tu `CLOSES_1H.bin`); khong dung high/low/volume trong lan nay.
- Lenh **conditional** (chi lenh he THUC SU da vao); khong suy ra gi ve coin/lenh bi loai.
- **n_SUP = 49 nho**; decile ~5 SUP/decile; sd_boot lon (CI rong).
- What-if (muc 5) khong re-run, khong tinh tuong quan vi the / margin / giai phong margin.
- CI chi cho (b) hieu mean, khong cho bang danh doi (c).

Co-Authored-By: Claude (subagent) — phan tich mo ta, pre-reg truoc, khong push.
