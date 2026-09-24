# PREREG_PRESCREEN_FEAT — tien dang ky: LOC SO BO ~23 FEATURE MOI de xuat (Stage 0)

**Ngay chot:** 2026-09-24 · **Chi nhanh:** `module` · **Trang thai:** CHOT TRUOC khi do (khong sua sau khi thay so)
**Pham vi:** THUAN PYTHON OFFLINE. Khong train. Khong sim. Khong job tren Oracle. DEV only, **khong cham 2026**. Khong push.

---

## 0. Boi canh

`docs/analysis/EVAL_SELECTOR_FEATURES.md` (commit `025767f`) chia 45 feature cua selector S1 thanh
**NGAT CHAC 5 / CAN NHAC 18 / GIU 22**. Owner chot: **bo `#36 rvol15m`** ⇒ con **21 keeper**.

Truoc khi dot mot vong GPU (Kaggle) de train lai, lam **pre-screen offline** cho danh sach
**23 feature MOI** (nhom A = dai han cua chinh coin, nhom B = regime thi truong) da de xuat trong
tin nhan 2026-09-24 20:28 (nguon: transcript phien chinh), loc con **5-8 cai** dang dua vao train.

**SO FEATURE DE XUAT BAN DAU = 23** (A: 14 · B: 9). Day la **multiplicity cua buoc nay**; moi
nguong va he so CI duoi day duoc chot voi `k = 23` va **khong duoc sua sau khi xem so**.

Nhom A (dai han cua chinh coin): `mom7d`, `mom30d`, `distFromHigh30D`, `distFromHigh90D`,
`rangePosition7D`, `rvol7d`, `rvolRatio`, `squeezeLong`, `trendConsistency7d`, `daysSinceHigh30D`,
`fundingCum7d`, `oi_delta7d`, `oiPersistence`, `listingAgeDays`.

Nhom B (regime thi truong): `btcMom7d`, `btcMom30d`, `marketBreadth7D`, `mktRealizedVol7D`,
`volRegime`, `dispersion7D`, `avgCorrToBtc7D`, `altBreadthMom7D`, `mktFundingPercentile`.

---

## 1. DU LIEU (kiem tra TRUOC, ghi ro cai nao KHONG tinh duoc ⇒ loai ngay)

| Nguon | Duong dan | Dung cho | Trang thai |
|---|---|---|---|
| 1m OHLCV per coin | `/home/ubuntu/claudedata/rvb_1m/raw/<SYM>.f32` (dtype `<i4,f4,f4,f4,f4,f4` = ts_minute,o,h,l,c,v; 627 sym; 2021-01-01..2025-12-31 UTC; manifest `rvb_1m/manifest.txt`) | moi feature gia/vol | **CO** |
| Feature + nhan (tick) | `/tmp/evfeat/joined.parquet` (5.455.290 dong, 26.124 tick, 275 symId, DEV 3 quy) — `f0..f39` + 5 OI + `retEnd_4h` | 21 keeper (cot `f*`), nhan do IC | **CO** |
| OI 5m per coin (5 cot da dan xuat) | `/home/ubuntu/claudedata/oi/oi_percoin_full.bin` (`ts>i8, sym>i2, oi>f4 x5`; cot 0 = `oi_delta24h`) | `oi_delta7d`, `oiPersistence` | **CO** |
| Map symId→symbol | `/home/ubuntu/claudedata/oi/symbol_map.csv` | join | **CO** |
| Funding rate lich su | — | `fundingCum7d`, `mktFundingPercentile` | **KHONG CO** |
| Bang listing (onboard date) | `/home/ubuntu/simbundle/exchange_info_pin.json` (892 symbol, **khong co `onboardDate`**) | `listingAgeDays` | **KHONG CO** |

**Loai truoc vi THIEU DU LIEU (khong do, chi ghi nhan): 3 feature**
`fundingCum7d`, `mktFundingPercentile` (khong co dump lich su funding rate o dang doc duoc: cac
`funding.bin` offline — `simbundle/funding.bin`, `wfo_ds_x1_2021/funding.bin`, `claudedata/funding_lf*.bin`
— deu la **chuoi PREDICTION**, khong phai rate; rate chi nam trong Aerospike) ·
`listingAgeDays` (khong co bang listing/onboard date; suy tu "ban ghi 1m dau tien" la SAI vi cache
bat dau 2021-01-01 cho moi coin cu ⇒ survivorship gia).

⇒ **So feature duoc DO = 20** (A: 12 · B: 8). Danh sach nay dong bang tai thoi diem chot.

## 2. QUY UOC TINH (causal, cua so DA DONG)

- Truc thoi gian: `t` = tick 15m (ms). Gia tri 1m `c[m]` = close cua nen 1m phut `m` (khop quy uoc
  da kiem chung cua repo: `f35 ret15m == c[t]/c[t-15m]-1`, sai so ~1e-6 tren mau kiem tra).
- Nen 15m tai `b`: `c15[b]=c[b]`, `h15[b]=max h_1m` tren 15 phut `(b-14..b)`, `l15[b]=min l_1m`,
  `v15[b]=sum v_1m`. Moi thanh phan chi dung phut `<= b` ⇒ **cua so dong** theo dung quy uoc bar-close
  cua 22 feature hien co.
- Nen 1h tai `k`: `o1h[k]=o[60k]`, `c1h[k]=c[60k+59]`, `h/l` tuong tu ⇒ chi **hop le tu phut `60k+59`**
  tro di (ffill len luoi 15m theo `k_max(t)=(m-59)//60`, `m=t/60000`).
- Luoi tinh: [2022-03-01, 2024-07-01] (du warmup 90d truoc quy DEV som nhat 2023-01-01).
- **Regime dung QUANTILE TRUOT** (cua so 365 ngay truot), **KHONG `expanding`** — bai hoc `f21/f22/f23`.
- Moi cong thuc rolling chay tren luoi 15m **day du** (thieu nen ⇒ NaN); `rolling(min_periods=ceil(0.5*W))`
  cho max/min/mean (chiu duoc <=50% nen thieu trong cua so, phan anh dung chat luong du lieu).

### 2.1 Cong thuc nhom A (coin-level, 15m grid; W tinh bang nen 15m, 96 nen/ngay)

| ten | cong thuc | cua so |
|---|---|---|
| `mom7d` | `c15[b]/c15[b-672]-1` | 7d |
| `mom30d` | `c15[b]/c15[b-2880]-1` | 30d |
| `distFromHigh30D` | `(max(h15,W)-c15[b])/max(h15,W)` | 2880 |
| `distFromHigh90D` | idem | 8640 |
| `rangePosition7D` | `(c15[b]-min(l15,W))/(max(h15,W)-min(l15,W))` | 672 |
| `rvol7d` | `std(log(c1h[k]/c1h[k-1]))` | 168 gio |
| `rvolRatio` | `f36 rvol15m (tu joined) / rvol7d` | — |
| `squeezeLong` | `mean(h15-l15, 96) / mean(h15-l15, 672)` | 1d/7d |
| `trendConsistency7d` | `mean(c1h[k] > o1h[k])` | 168 gio |
| `daysSinceHigh30D` | `(b - argmax_rolling(h15,2880))/96` (ngay) | 2880 |
| `oi_delta7d` | `prod_{k=0..6}(1+oi_delta24h(t-24h*k)) - 1` (dong nhat dai so chinh xac tu cot `oi_delta24h` san co) | 7d |
| `oiPersistence` | so ky 24h LIEN TIEP gan nhat (quet lui tu `t`) co `oi_delta24h > 0`, cap 8 | — |

### 2.2 Cong thuc nhom B (market-level; tinh tren luoi NGAY 00:00 UTC, roi `shift(1)` + merge_asof
backward len tick ⇒ tick trong ngay D chi thay gia tri cua ngay D-1)

| ten | cong thuc |
|---|---|
| `btcMom7d` / `btcMom30d` | `d_BTC[D]/d_BTC[D-7\|30]-1` |
| `marketBreadth7D` | `mean_coin(d_coin > MA7d(d_coin))` |
| `mktRealizedVol7D` | `median_coin(std(log(c1h)/log(c1h[-1]) qua 168 gio))` |
| `volRegime` | percentile hang cua `mktRealizedVol7D[D]` trong cua so **truot 365 ngay** (`[D-365,D]`, causal, khong expanding) |
| `dispersion7D` | `std_coin(d_coin/d_coin[D-7]-1)` |
| `avgCorrToBtc7D` | `mean_coin(corr(168 log-return 1h cua coin, cua BTC))` |
| `altBreadthMom7D` | `mean_coin(d_coin/d_coin[D-7]-1 > 0)` |

## 3. DO CAI GI (tren `joined.parquet`, cung tick/nhan, inner-join `(ts,symId)`)

1. **`coverage`** = 1 − ti le NaN tren so dong joined.
2. **`frac_tick_constant`** = ti le tick (co >=2 coin) ma `std(feature trong tick) == 0` (bai hoc 12 feature market/basket).
3. **`max|rho|` voi 21 keeper** = max |Spearman| tren mau 250.000 dong (cung cach `EVAL_SELECTOR_FEATURES` §5), kem **ten keeper dinh**.
4. **rank-IC cross-section** voi nhan that `retEnd_4h` (Spearman trong tung tick, lay trung binh qua tick) + **CI block-72h, 2000 rep, seed 20260905**.
5. **decile edge (bp)** = `mean(retEnd_4h | decile 10) − mean(retEnd_4h | decile 1)` trong tick + CI cung chuan.

**CI chuan:** block-72h · 2000 rep · seed `20260905` · **nhan he so `inflate(k=23)=sqrt(2 ln 23)=2.5042`**
(chuan `AUDIT_CI_INFLATE_STANDARDIZATION`). Bao CAO ca CI raw va CI da inflate; **phan quyet bang CI da inflate**.

## 4. TIEU CHI LOC — CHOT TRUOC. Giu feature neu THOA CA 4:

- (a) `coverage >= 0,90`
- (b) `max|rho| voi 21 keeper <= 0,70` (khong trung lap)
- (c) `frac_tick_constant <= 0,95` (co phuong sai cross-section ⇒ moi xep hang duoc)
- (d) co tin hieu: **CI(rank-IC) khong chua 0** HOAC **CI(decile edge) khong chua 0** HOAC `|rank-IC| >= 0,02`

**Luong xu ly sau (a)-(c):**
- Neu `> 8` cai ⇒ xep hang theo `|rank-IC|`, lay **top 8**.
- Neu `< 5` cai ⇒ **BAO RO, KHONG ha nguong, khong tu noi long de du so**.
- Neu `5..8` ⇒ giu nguyen ca danh sach.

**Khong duoc sua sau khi thay so:** khong doi cong thuc, khong doi cua so, khong doi nguong,
khong doi `k`. Neu phat hien loi tinh ⇒ ghi `AMENDMENT` rieng co ngay + ly do, cong lai multiplicity.

## 5. KY VONG KHOA TRUOC (de tranh hoc ket qua)

- Nhom B (market-level) **du kien BI LOAI boi (c)**: la hang so cross-section (giong 12 feature `f0..f5,f12..f16,f18`
  co `frac_tick_constant ~ 0,9992`) ⇒ khong xep hang duoc coin. **Ngoai le du kien:** `avgCorrToBtc7D`
  (coin-level, co phuong sai cross-section).
- Nhom A dai han (`mom7d/30d`, `distFromHigh30D/90D`, `rvol7d`) du kien **dinh `mom24H`/`distFromHigh24H`/`rvol15m`**
  voi `|rho|` cao (cung ho), nen `max|rho|` la cai chan chinh.
- Ky vong chung: **NULL** (moi vong them feature truoc day deu NULL). Pre-screen nay chi tra loi
  "co dang dot GPU khong", KHONG tra loi "co alpha khong".

## 6. Gioi han ghi TRUOC

1. `retEnd_4h` la nhan **do**, khac nhan train; IC thap khong phu dinh dong gop trong model da bien.
2. Du lieu gia cua 1m cache (`rvb_1m/raw`) la **nguon khac** voi nguon dung de sinh `f0..f39`
   (kiem chung `f35` khop ~1e-6 tren mau, nhung `retEnd_4h` KHONG tai lap duoc tu cache nay ⇒
   chi dung cache de tinh **feature moi** va ghep theo `(ts,symId)`, khong dung de tinh lai nhan).
3. 3 feature bi loai vi thieu du lieu ⇒ **khong co ket luan** ve chung.
4. CI chi ap multiplicity cho `k=23` ung vien cua vong nay.
5. Khong train, khong sim ⇒ khong co ket luan ve `maxFav>=6%` hay ve sim.
