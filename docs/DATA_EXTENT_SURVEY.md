# DATA_EXTENT_SURVEY — lui du lieu duoc toi dau, va no mua duoc gi

Ngay: 2026-09-03. Do that, khong doan. Script: `/home/ubuntu/oifix/{v2,v4,v7,v10}.py` +
`r2.py` (bang MDE). Ket qua: `v2.json v4.json v7.json v10.json`.
Nguon do: listing S3 cua `data.binance.vision` (`?prefix=...&max-keys=...`, chinh xac theo file
co thuc) + REST `fapi.binance.com`. **Khong tai du lieu o at** — chi listing + HEAD + vai ngay mau.

Uni noi "du lieu tu 2021 do ve truoc". **Do duoc: sai.** Chi tiet duoi day.

---

## 1. BANG DO DAI DU LIEU THEO LOAI

Universe do: 862 symbol trong `claudedata/oi/symbol_map.csv`.

| loai du lieu | nguon | ngay som nhat (thuc do) | lo ngay | ghi chu |
|---|---|---|---|---|
| kline 1m (um) | Vision `monthly/klines/<S>/1m/` | **2020-01** | 0 (10 symbol quet day du) | 823/862 symbol co file |
| kline 1m (um) | Vision `daily/klines/<S>/1m/` | **2019-12-31** | — | Vision khong co 2019-09..2019-12-30 |
| kline 1m (um) | REST `/fapi/v1/klines` | **2019-09-08 17:57Z** (BTCUSDT) | — | ETHUSDT 2019-11-27; chi 3 symbol onboard 2019 |
| kline 5m (um) | Vision monthly / daily | **2020-01** / **2019-12-31** | 0 | y het 1m |
| **metrics (6 cot OI/LS/taker)** | Vision `daily/metrics/<S>/` | **2020-09-01 (CHI BTCUSDT)**; **2021-12-01 cho tat ca con lai** | **0 lo** (BTC 2193 ngay lien tuc; 9 symbol khac 1737 ngay lien tuc) | 820/862 symbol co file. Truoc 2021-12-01: **1 symbol duy nhat** |
| metrics | REST `/futures/data/*` | **~41.6 gio** (limit 500 diem 5m) | — | `startTime` cach 400 ngay -> HTTP 400. **Khong dung duoc de lui lich su** |
| funding rate | Vision `monthly/fundingRate/<S>/` | **2020-01** | 0 | 823/862 symbol |
| funding rate | REST `/fapi/v1/fundingRate` | **2019-09-10 08:00Z** (BTCUSDT) | — | |
| exchangeInfo / danh sach symbol | REST `/fapi/v1/exchangeInfo` | onboardDate tung symbol | — | **CHI symbol CON LIST** (656 perp USDT) => co thien lech song sot |

**So symbol kha dung theo nam** (do tu listing Vision, gom ca symbol da delist — khong bi thien
lech song sot):

| nam | co kline 1m | co kline 5m | co funding | **co metrics (OI)** |
|---|---|---|---|---|
| 2019 | 0 | 0 | 0 | 0 |
| 2020 | 80 | 80 | 80 | **1** |
| 2021 | 138 | 138 | 137 | **135** (thuc te chi tu 2021-12-01) |
| 2022 | 161 | 161 | 160 | 160 |
| 2023 | 248 | 248 | 248 | 255 |
| 2024 | 379 | 379 | 379 | 386 |
| 2025 | 608 | 608 | 610 | 627 |
| 2026 | 800 | 800 | 735 | 820 |

Doi chieu voi file OI dang dung (`v6.log`): 779 symbol, **BTCUSDT tu 2021-01-01**, **136 symbol tu
2021-12-01**, con lai muon hon. Dong theo nam: 2021 = 1.29M; 2022 = 14.8M; 2023 = 19.9M;
2024 = 29.0M; 2025 = 46.6M; 2026 = 29.4M. Khop chinh xac voi gioi han 2021-12-01 cua Vision
metrics => **file OI duoc build tu Vision metrics**, khong tu Aerospike 226.

---

## 2. CAU 1 — RANG BUOC CHAT NHAT

**Rang buoc chat nhat la `metrics` (6 cot sinh ra 5 feature OI): som nhat 2021-12-01 cho toan bo
universe tru BTCUSDT.** kline va funding co tu 2020-01 (Vision) hoac 2019-09-08 (REST, 3 symbol).

DEV hien tai bat dau **2022-01-01** (`FEAT40_LOOKAHEAD` muc pham vi). Nghia la:

> **Neu giu 5 feature OI, keo DEV ve som nhat chi duoc thêm 31 ngay (2021-12-01).**
> `T_dev`: 2.496 nam -> 2.581 nam. Bang **+3.4%** thoi gian.

Ba lua chon va he qua:

**(a) DEV chi lui toi ngay metrics som nhat = 2021-12-01.**
- Duoc: +31 ngay, 5 feature OI nguyen ven, khong doan gi, khong sua model.
- Mat: gan nhu khong duoc gi. `MDE80` (exit-param) 7.20pp -> 7.08pp. **Vo nghia ve thong ke.**
- Chi phi: ~136 symbol x 31 ngay metrics = 4,216 file x 13.7KB = **58 MB**. Vai phut.

**(b) Lui xa hon (2020-01-01, hoac 2019-09-08 qua REST) va BO 5 feature OI khoi model.**
- Duoc: `T_dev` 2.496 -> **4.5 nam** (2020-01-01..2024-07-01), hoac **4.81 nam** neu lay ca
  2019-09-08 qua REST (nhung 2019 chi co 3 symbol => cross-sectional feature f3/f4/f5/f32-f34
  gan nhu vo nghia; thuc te nen coi 2020-01 la moc kha dung).
- Mat: 5/45 feature. **Phai train lai G015 tu dau** voi 40 feature, va moi so DEV/VAL/C2b, nguong
  `dyn_thr`, ket qua CI #8/#9 deu phai do lai. Do la mot model KHAC, khong so sanh truc tiep duoc
  voi ban hien tai.
- Rui ro phu: universe 2020 chi 80 symbol (vs 379 nam 2024) => `EntrySignalFilter` va cac feature
  rank cross-sectional (f32/f33/f34) hoat dong tren mot rank-space nho hon nhieu. Do la **thay
  doi che do do luong**, khong chi thay doi do dai.

**(c) Lui xa hon va de model chiu missing value o doan dau (giu 5 feature OI, NaN truoc 2021-12).**
- **KHONG NEN.** XGBoost xu ly NaN bang **huong mac dinh hoc duoc tren tap train**. Neu "OI = NaN"
  trung khop 1-1 voi "thoi gian < 2021-12", cay hoc duoc mot bien chi bao THOI GIAN mien phi va
  gan nhan che do thi truong cho no. Do la **ro ri che do** (regime leak): 2020-2021 la bull
  parabolic + COVID crash (xem muc 4), khac han 2022-2024. Model se hoc "khi khong co OI thi thi
  truong xu su kieu X" — mot dac trung khong bao gio ton tai o live.
- Rui ro nay **co tien le trong chinh repo**: `FEAT40_LOOKAHEAD` da ghi f23 `fundingPersistence`
  la ham tang theo lich va coi la "rui ro tong quat hoa". Them mot bien proxy-thoi-gian nua,
  lan nay **tuong quan hoan hao voi bien gioi che do**, thi xau hon f23 nhieu.
- Neu van muon lam: bat buoc phai (i) train tren tap co OI-NaN duoc **randomize** (mask NaN ngau
  nhien ca trong doan co OI) de "NaN" khong con la proxy thoi gian, va (ii) bao cao ket qua
  rieng tren hai doan. Chua ai lam vay trong repo nay.

**Khuyen nghi:** (a) neu muc tieu la giu tinh so sanh duoc; (b) neu muc tieu la tang cong suat
thong ke va chap nhan train lai tu dau. **Khong** chon (c).

---

## 3. CAU 2 — THEM DUOC BAO NHIEU NAM, VA MDE80 CON BAO NHIEU pp

**Day la con so quan trong nhat cua khao sat.**

Cong thuc chot san o `docs/PREREG_CI` section 5 va `docs/CI_REAUDIT` muc (iii):
`sd(CAGR) ~ 1/sqrt(T)`, `T_can = T_dev * (sd_dev / (delta/z))^2`, `z = 2.80158` (cong suat 80%),
`T_dev = 911 ngay = 2.4941 nam`. Dao lai:

> **`MDE80(T) = z * sd_dev * sqrt(T_dev / T)`**

Hang so: exit-param (`sd = 2.57pp`) -> `MDE80 = 11.371 / sqrt(T)`;
selector (`4.45pp`) -> `19.689 / sqrt(T)`; noi gate (`6.34pp`) -> `28.052 / sqrt(T)`
(T tinh bang nam). Kiem chung: `T = 14.3` -> 3.01pp; `T = 43.1` -> 3.00pp. Khop bang goc.

| kich ban | T (nam) | **MDE80 exit-param** | MDE80 selector | MDE80 noi gate |
|---|---|---|---|---|
| DEV hien tai | 2.50 | **7.20 pp** | 12.46 pp | 17.76 pp |
| (a) DEV lui ve 2021-12-01, giu OI | 2.58 | **7.08 pp** | 12.26 pp | 17.46 pp |
| DEV + VAL gop (moi thu tru holdout, hien co) | 3.96 | **5.71 pp** | 9.89 pp | 14.10 pp |
| (b) DEV lui ve 2020-01-01, bo OI | 4.50 | **5.36 pp** | 9.28 pp | 13.22 pp |
| (b') DEV lui ve 2019-09-08 (REST, 3 symbol) | 4.81 | **5.18 pp** | 8.98 pp | 12.79 pp |
| **TOI DA co the co**: 2020-01-01 .. 2025-12-31 gop | **6.00** | **4.64 pp** | 8.04 pp | 11.45 pp |
| toi da + 2019-09 (khong thuc te) | 6.31 | **4.53 pp** | 7.84 pp | 11.17 pp |
| can de do duoc 3pp | 14.30 | 3.01 pp | 5.21 pp | 7.42 pp |
| can de do duoc 3pp (selector) | 43.10 | 1.73 pp | **3.00 pp** | 4.27 pp |

Bien the lac quan hon (thong ke loga ghep cap, `CI_REAUDIT` ghi la khong pre-reg):
`T_can@3pp` = 9.0 nam (exit-param) / 33.9 (selector) / 14.2 (arm5-scale1) =>
`MDE80(T) = 3 * sqrt(T_can/T)`:

| T (nam) | exit-param | selector | arm5/scale1 |
|---|---|---|---|
| 2.50 (nay) | 5.70 pp | 11.06 pp | 7.16 pp |
| 3.96 | 4.52 pp | 8.78 pp | 5.68 pp |
| 4.50 | 4.24 pp | 8.23 pp | 5.33 pp |
| 6.31 (toi da) | **3.58 pp** | 6.95 pp | 4.50 pp |

### Tra loi dut khoat

- **Giu 5 feature OI: MDE80 di tu 7.20pp -> 7.08pp. Keo dai du lieu KHONG mua duoc gi.**
  Thieu he so 2.4 ve `MDE` = thieu **5.7 lan** ve thoi gian.
- **Bo feature OI, lui toi 2020-01: MDE80 = 5.36pp** (bi quan) / **4.24pp** (lac quan).
  Van **KHONG du** de do cai thien 3pp. Thieu he so 1.8 / 1.4 ve `MDE`.
- **Dung het moi byte co the tai ve (6.0-6.3 nam, gom ca VAL, tru holdout): MDE80 = 4.5-4.6pp**
  (bi quan) hoac **3.58pp** (lac quan). **Van khong dat 3pp** o ca hai cach tinh, cho cap so sanh
  **de nhat** (chi doi tham so exit). Voi cap "doi selector" thi con cach xa gap 2.3-2.6 lan.
- => **Keo dai du lieu KHONG giai quyet duoc bai toan do 3pp.** No la mot cai thien co thuc
  (7.20 -> 4.6pp la giam 36% do luong) nhung khong doi dau bai. Ket luan cua `CI_REAUDIT`
  ("khong the dat duoc bang cach cho them du lieu") **duoc xac nhan bang so lieu do phu that**,
  khong chi bang uoc luong.
- Cai co the doi dau bai la giam `sd` chu khong phai tang `T`: **so sanh ghep cap** (`PREREG_PAIRED`
  da di huong nay: `sd` 4.452pp -> `MDE` 12.47pp o cung T, tuc paired chua giup gi cho selector),
  tang so **khoi doc lap** (nhieu symbol / nhieu arm) thay vi nhieu nam, hoac doi tieu chi tu
  hieu CAGR sang mot dai luong co `sd` nho hon (per-trade edge, hit-rate, Sharpe cua chuoi daily).
  Do la huong khac, khong thuoc khao sat nay.

---

## 4. CAU 3 — CHI PHI TAI, DUNG LUONG, THOI GIAN, CO VUA DIA KHONG

Kich thuoc do bang HEAD `Content-Length` (4 mau moi loai, `v2.json` muc `cost`):

| loai file | kich thuoc trung binh (nen) |
|---|---|
| daily metrics (1 symbol-ngay) | **13,743 B** |
| monthly kline 1m (1 symbol-thang) | **1,757,154 B** |
| monthly kline 5m (1 symbol-thang) | **379,344 B** |
| monthly fundingRate (1 symbol-thang) | **927 B** |

Thong luong do that: 1.9 MB / 0.62 s tren **1 ket noi** = **~3.0 MB/s**. Vision khong gioi han ro,
`VisionMetricsClient` da co `vthreads=8`.

| kich ban | so file | tai ve (nen) | thoi gian tai (8 luong) | dung luong sau khi giai/ingest |
|---|---|---|---|---|
| (a) metrics 2021-12-01..12-31, 136 symbol | 4,216 | **58 MB** | ~1.5 phut (latency-bound) | khong dang ke; `.bin` +~1.2M dong = **+35 MB** |
| (b) kline 1m 2020-01..2021-12, 80 symbol | 1,920 | **3.37 GB** | ~4-19 phut | CSV giai nen ~**25-30 GB** — **PHAI stream tung file**, khong duoc giai het cung luc |
| (b) kline 5m cung ky | 1,920 | **0.73 GB** | ~1-4 phut | — |
| (b) funding cung ky | 1,920 | **1.7 MB** | <1 phut | — |
| (b) dataset Tool1 mo rong 4 quy | — | — | — | uoc **+240 MB** (`/home/ubuntu/ds_feat5m` = 4.6 GB cho 20 quy, quy 2021Q1 = 70 MB) |

**Co vua dia khong:** `/` = 194 G, **dung 176 G, con 19 G (91%)**.
- Kich ban (a): vua thoai mai (~0.1 GB).
- Kich ban (b): tai ve nen **4.1 GB** + dataset **0.24 GB** = **4.35 GB** => con **~14.6 G**. Vua,
  **voi dieu kien** giai nen tung file roi xoa ngay (khong duoc giai 25-30 GB CSV cung luc — se
  het dia va lam hong job cua agent khac).
- **CHUA DO va la rui ro that:** dung luong **Aerospike 226/242** tang bao nhieu khi nap them
  2 nam nen 1m cho 80 symbol (~84 trieu bar). Job nay khong duoc doc/ghi 226/242 nen khong do
  duoc. **Phai do truoc khi tai** — 19 G la khong nhieu.
- **Thoi gian ingest + Tool1 + train lai: KHONG DO DUOC** trong job nay (cam chay java, cam train).
  Dung trich con so uoc luong nao tu tai lieu nay cho 3 khoan do.

---

## 5. CAU 4 — 2019-2020 co che do gi ma 2022-2024 khong co (DO, khong doan)

Nen 1d BTCUSDT + funding rate that tu Vision, tinh theo nam (`v10.log` muc REGIME):

| nam | so ngay | ret nam | vol nam hoa | **1 ngay xau nhat** | 1 ngay tot nhat | maxDD | funding p01 (bp) | funding p50 | **funding p99 (bp)** |
|---|---|---|---|---|---|---|---|---|---|
| 2020 | 366 | +302.2% | **76.2%** | **-40.0%** | +16.9% | -54.0% | **-4.60** | +1.00 | +10.81 |
| 2021 | 365 | +57.5% | **81.2%** | -14.4% | +19.6% | -53.2% | -2.36 | +1.00 | **+15.85** |
| 2022 | 365 | -65.3% | 63.8% | -15.4% | +14.6% | -66.9% | -1.72 | +0.51 | +1.00 |
| 2023 | 365 | +154.7% | 44.2% | -7.3% | +10.3% | -20.0% | -0.51 | +0.83 | +3.78 |
| 2024 | 366 | +111.5% | 53.0% | -8.4% | +11.9% | -26.3% | -0.71 | +1.00 | +6.48 |
| 2025 | 365 | -7.4% | 41.7% | -8.5% | +9.6% | -32.0% | -0.60 | +0.48 | +1.00 |
| 2026 | 243 | -11.5% | 46.5% | -14.0% | +12.2% | -39.5% | -0.93 | +0.28 | +1.00 |

**Cai 2020-2021 co ma 2022-2026 KHONG co (do duoc, khong phai nhan dinh):**

1. **Cu sup thanh khoan mot ngay -40.0%** (2020-03-12, COVID). Ngay xau nhat cua ca 2022-2026 la
   -15.4%. => **2.6 lan** ngoai bien do ma model hien tai tung thay. Day la che do quan trong nhat
   voi mot chien luoc co stop/liquidation.
2. **Vol nam hoa 76-81%** (2020, 2021) so voi **41.7-63.8%** (2022-2026). Nam vol cao nhat sau nay
   (2022, 63.8%) van thap hon 2021 **21%**.
3. **Funding cuc doan o CA HAI dau:**
   - p99 = **+15.85 bp** (2021) va +10.81 bp (2020), so voi toi da **+6.48 bp** (2024). Che do
     "funding duong keo dai cuc manh" (long crowding cua bull parabolic) **khong ton tai** trong
     DEV/VAL hien tai.
   - p01 = **-4.60 bp** (2020) so voi toi da **-1.72 bp** (2022). Che do "funding am sau" cung khong co.
   - Dieu nay quan trong dac biet vi f17-f25 (9/45 feature) **deu la feature funding**, va
     `fundingPercentileCoin`/`fundingZCoin` la percentile/z tren lich su expanding: neu doan
     2020-2021 duoc them vao dau chuoi, **phan phoi tham chieu cua chinh 2 feature do se doi**
     cho toan bo giai doan sau. Do la mot thay doi feature, khong chi them du lieu.
4. **Universe 80 symbol** (2020) so voi 379 (2024). Feature rank cross-sectional f32/f33/f34 va
   `EntrySignalFilter` chay tren rank-space nho hon 4.7 lan.

**Cai 2022-2026 co ma 2020-2021 khong co** (de can bang): LUNA (2022-05), FTX (2022-11), nam
bear grind 2022 (-65.3%, maxDD -66.9% — sau nhat trong ca chuoi), va che do vol thap keo dai
2023/2025 (41-44%).

**He qua thuc te:** them 2020-2021 la them che do **that su moi va cuc doan**, khong phai them
"nhieu du lieu giong nhau". Do la ly do **manh** de mo rong — nhung ly do do la **do ben/tinh tong
quat**, KHONG phai **cong suat thong ke** (muc 3 da cho thay cong suat khong du bat ke the nao).
Va nhu muc 2, 2020-2021 **khong co metrics** => neu mo rong thi phai bo 5 feature OI o doan do.

## 6. Sai sot trong tien de duoc cap cho job nay

1. "Du lieu tu 2021 do ve truoc": **sai**. metrics (OI/LS/taker) chi co tu **2021-12-01** cho toan
   universe (chi BTCUSDT tu 2020-09-01). kline/funding tu 2020-01 (Vision) / 2019-09-08 (REST).
2. "sd giam theo `1/sqrt(n_khoi)`": dung ve dang, nhung con so pre-reg trong `PREREG_CI` la
   `1/sqrt(T)` theo **thoi gian**, va `CI_REAUDIT` da tinh `T_can` theo do. Bang muc 3 dung dung
   cong thuc pre-reg de dao nguoc ra `MDE80`, khong doi cong thuc.
