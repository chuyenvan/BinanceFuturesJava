# RESULT_PRESCREEN_FEAT — ket qua pre-screen 23 feature MOI de xuat (Stage 0)

**Ngay:** 2026-09-24 · **Chi nhanh:** `module` · **Trang thai:** DO XONG, ket qua dong bang
**Tien dang ky (chot TRUOC):** `docs/PREREG_PRESCREEN_FEAT.md` commit `6695a8c`
**Script:** `research/analysis/prescreen_build.py` (nhom A + OI), `prescreen_market_load.py` +
`prescreen_market.py` (nhom B), `prescreen_eval.py` (do + ap tieu chi)
**Pham vi:** THUAN PYTHON OFFLINE · khong train · khong sim · khong job tren Oracle · **khong cham 2026** · khong push

---

## 0. Tra loi ngan

| Buoc | So |
|---|---|
| Feature de xuat ban dau (nhom A 14 + nhom B 9) | **23** |
| Loai NGAY vi THIEU DU LIEU (khong do) | **3** (`fundingCum7d`, `mktFundingPercentile`, `listingAgeDays`) |
| Do that | **20** (A: 12 · B: 8) |
| **PASS ca 4 tieu chi** | **5** — `rvol7d` · `mom30d` · `mom7d` · `daysSinceHigh30D` · `oi_delta7d` |
| Ap luat >8 / <5 | **khong ap dung** (5 nam trong khoang 5..8) ⇒ giu nguyen ca 5, **khong ha nguong** |

Mau do: **5.455.290 dong · 26.124 tick · 208,8 coin/tick** (median 218, min 139) — dung 3 quy DEV
`2023Q1 / 2023Q4 / 2024Q2` nhu `docs/EVAL_SELECTOR_FEATURES.md`, cung tick/cung nhan.

---

## 1. Kiem tra du lieu TRUOC (3 feature bi loai)

| Feature | Ly do loai (so THAT) |
|---|---|
| `fundingCum7d` | **Khong co dump lich su funding RATE** o dang doc duoc offline. Cac file `funding.bin` offline (`simbundle/funding.bin`, `wfo_ds_x1_2021/funding.bin`, `claudedata/funding_lf*.bin`) deu la **chuoi PREDICTION** (manifest `simbundle`: `sourceFundingSet=funding_selector_pred_1m_v2`), khong phai rate. Rate chi nam trong Aerospike (`FundingFeeManager` → `DataManagerAerospikeFloatSim`), khong nam trong pham vi "offline, khong job". |
| `mktFundingPercentile` | idem (cung nguon funding rate). |
| `listingAgeDays` | **Khong co bang listing/onboard date**: `simbundle/exchange_info_pin.json` (892 symbol) **khong co truong `onboardDate`**. Suy tu "ban ghi 1m dau tien" la SAI vi cache 1m bat dau 2021-01-01 cho **moi** coin cu ⇒ sinh survivorship gia. |

⇒ **Khong co ket luan gi ve 3 feature nay.** Muon do phai bo sung nguon du lieu (dump funding rate / bang listing).

## 2. Bang day du 20 feature (so THAT)

Quy uoc: `coverage` = 1 − ti le NaN tren 5.455.290 dong · `ftc` = `frac_tick_constant` ·
`max|rho|` = max |Spearman| voi **21 keeper** tren mau 250.000 dong (kem ten keeper dinh) ·
`rank-IC` = Spearman cross-section voi `retEnd_4h`, trung binh 26.124 tick ·
CI = block-72h · 2000 rep · seed `20260905`; cot `[raw]` va cot `[x2.5042]` = CI da nhan
`inflate(k=23)` (chuan `AUDIT_CI_INFLATE_STANDARDIZATION`) — **phan quyet bang cot inflate** ·
`edge` = decile 10 − decile 1 (bp, tren `retEnd_4h`).

| Nhom | Feature | coverage | ftc | max\|rho\| | keeper dinh | rank-IC | CI [raw] | CI [x2.5042] | edge bp [x2.5042] | Ket |
|---|---|---|---|---|---|---|---|---|---|---|
| A | `rvol7d` | 0,9953 | 0,0000 | 0,399 | `distFromHigh24H` | −0,0482 | [−0,0575, −0,0388] | [−0,0714, −0,0246] | −0,66 [−17,54, +16,61] | **PASS** |
| A | `mom30d` | 0,9623 | 0,0000 | 0,451 | `basketFundingAvg` | −0,0289 | [−0,0348, −0,0227] | [−0,0436, −0,0133] | −1,90 [−12,02, +8,52] | **PASS** |
| A | `mom7d` | 0,9907 | 0,0000 | 0,329 | `momentum24H` | −0,0283 | [−0,0344, −0,0222] | [−0,0437, −0,0130] | +0,75 [−11,41, +13,34] | **PASS** |
| A | `daysSinceHigh30D` | 0,9806 | 0,0000 | 0,320 | `basketFundingAvg` | +0,0243 | [+0,0193, +0,0296] | [+0,0119, +0,0376] | +1,97 [−7,07, +11,06] | **PASS** |
| A | `oi_delta7d` | 0,9809 | 0,0001 | 0,259 | `oi_delta24h` | −0,0210 | [−0,0259, −0,0159] | [−0,0333, −0,0082] | −0,16 [−9,96, +9,69] | **PASS** |
| A | `rangePosition7D` | 0,9953 | 0,0000 | 0,558 | `momentum24H` | −0,0151 | [−0,0224, −0,0083] | [−0,0333, +0,0020] | +4,57 [−6,80, +15,24] | loai (d) |
| A | `squeezeLong` | 0,9953 | 0,0000 | 0,356 | `distFromLow24H` | −0,0138 | [−0,0213, −0,0062] | [−0,0327, +0,0053] | +4,26 [−7,55, +15,38] | loai (d) |
| A | `oiPersistence` | 0,9964 | 0,0001 | **0,822** | `oi_delta24h` | −0,0094 | [−0,0140, −0,0047] | [−0,0209, +0,0025] | −19,67 [−83,11, +26,92] | loai **(b)** |
| A | `rvolRatio` | 0,9953 | 0,0000 | 0,425 | `atrSqueeze` | −0,0064 | [−0,0107, −0,0017] | [−0,0170, +0,0054] | +1,06 [−6,99, +9,04] | loai (d) |
| A | `distFromHigh90D` | 0,9455 | 0,0000 | 0,388 | `basketFundingAvg` | +0,0051 | [−0,0027, +0,0132] | [−0,0146, +0,0253] | −1,16 [−13,82, +11,37] | loai (d) |
| A | `trendConsistency7d` | 0,9953 | 0,0000 | 0,279 | `basketFundingAvg` | −0,0005 | [−0,0051, +0,0043] | [−0,0120, +0,0117] | +0,62 [−8,27, +9,35] | loai (d) |
| A | `distFromHigh30D` | 0,9806 | 0,0000 | 0,349 | `basketFundingAvg` | +0,0003 | [−0,0079, +0,0084] | [−0,0203, +0,0205] | −3,25 [−17,29, +9,61] | loai (d) |
| B | `btcMom7d` | 1,0000 | **1,0000** | 0,228 | `basketFundingAvg` | khong xac dinh | — | — | — | loai **(c)** |
| B | `btcMom30d` | 1,0000 | **1,0000** | 0,521 | `basketFundingAvg` | khong xac dinh | — | — | — | loai **(c)** |
| B | `marketBreadth7D` | 1,0000 | **1,0000** | 0,357 | `basketMomentum24H` | khong xac dinh | — | — | — | loai **(c)** |
| B | `mktRealizedVol7D` | 1,0000 | **1,0000** | 0,230 | `distFromLow24H` | khong xac dinh | — | — | — | loai **(c)** |
| B | `volRegime` | 1,0000 | **1,0000** | 0,236 | `distFromLow24H` | khong xac dinh | — | — | — | loai **(c)** |
| B | `dispersion7D` | 1,0000 | **1,0000** | 0,601 | `basketFundingAvg` | khong xac dinh | — | — | — | loai **(c)** |
| B | `avgCorrToBtc7D` | 1,0000 | **1,0000** | 0,270 | `basketFundingAvg` | khong xac dinh | — | — | — | loai **(c)** |
| B | `altBreadthMom7D` | 1,0000 | **1,0000** | 0,333 | `coinFundingRate` | khong xac dinh | — | — | — | loai **(c)** |

- `(a) coverage >= 0,90`: **20/20 dat** (thap nhat `distFromHigh90D` 0,9455; roi `mom30d` 0,9623).
- `(b) max|rho| <= 0,70`: **19/20 dat**; duy nhat `oiPersistence` vi pham (**0,822** voi `oi_delta24h`) —
  dung nhu khu vuc rui ro da biet (`oi_delta24h` la feature OI manh nhat, share 5,74%).
- `(c) frac_tick_constant <= 0,95`: **12/20 dat**; **toan bo 8 feature nhom B dat ftc = 1,0000**
  (hang so cross-section ⇒ khong xep hang duoc coin) ⇒ rank-IC/decile **khong xac dinh** (n_tick = 0),
  khong phai "bang 0". 12 feature nhom A deu ftc ≤ 0,0001.
- `(d) tin hieu`: 5 dat (4 CI inflate ngoai 0 + `|IC|>=0,02`; `daysSinceHigh30D` va `oi_delta7d`
  dat ca hai duong). 7 feature A con lai co `|IC|` 0,0003–0,0151 va CI inflate **chua 0**.
- **`edge` decile: KHONG feature nao co CI (ke ca raw) ngoai 0** ⇒ khong co bang chung kinh te don bien;
  tieu chi (d) duoc dat **hoan toan bang rank-IC** (nhu ky vong o pre-reg §5).

## 3. DANH SACH CUOI (5 feature) + phan nhom A/B

| # | Feature | Nhom | Cong thuc · cua so | rank-IC |
|---|---|---|---|---|
| 1 | `rvol7d` | **A** (dai han cua coin) | `std(log-return 1h)` tren 168 gio (7d, cua so dong) | −0,0482 [−0,0714, −0,0246] |
| 2 | `mom30d` | **A** | `c(t)/c(t−30d) − 1` | −0,0289 [−0,0436, −0,0133] |
| 3 | `mom7d` | **A** | `c(t)/c(t−7d) − 1` | −0,0283 [−0,0437, −0,0130] |
| 4 | `daysSinceHigh30D` | **A** | so NGAY ke tu dinh 30d (cua so truot 2880 nen 15m) | +0,0243 [+0,0119, +0,0376] |
| 5 | `oi_delta7d` | **A** | `prod_{k=0..6}(1+oi_delta24h(t−24h·k)) − 1` (OI 5m) | −0,0210 [−0,0333, −0,0082] |

**Nhom B (regime thi truong): 0/8 vao danh sach cuoi** — bi chan boi (c) (xem §4.1). **Khong co
feature nao cua nhom B duoc dua vao vong train tiep theo** theo dung tieu chi da chot.

## 4. Nhung dieu phai doc kem

### 4.1 Nhom B bi loai BOI THIET KE, khong phai "yeu"
8/8 feature nhom B la **dai luong cap thi truong** (moi coin cung mot gia tri tai mot tick) ⇒
`frac_tick_constant = 1,0000` va rank-IC **khong xac dinh**. Day dung la so phan da ghi o pre-reg §5
("du kien bi loai boi (c)"), giong het 12 feature `f0..f5, f12..f16, f18` cua model hien tai
(`ftc ≈ 0,9992`). Neu muon dung nhom B thi phai la **bien the tuong tac / timing**, khong phai
feature xep hang — **ngoai pham vi cua tieu chi nay**.

⚠️ **Loi trong pre-reg (ghi ro, KHONG sua tieu chi):** pre-reg §5 co ghi "ngoai le du kien:
`avgCorrToBtc7D` (coin-level, co phuong sai cross-section)". Cau do **SAI va mau thuan voi dinh nghia
§2.2** (dinh nghia van hanh: `mean_coin(corr(...))` = cap thi truong). Ket qua do duoc chinh la
hang so cross-section ⇒ loai boi (c). Tieu chi, nguong va `k=23` **giu nguyen**; **khong** them mot
bien the `corrToBtc` coin-level trong vong nay (them sau khi da thay so = vi pham multiplicity) —
do la viec cua vong sau, phai tinh vao `k` moi.

### 4.2 Nam feature PASS **khong doc lap hoan toan** (tuong quan NOI BO, mau 250k dong)
`mom7d ↔ oi_delta7d = +0,707` · `mom30d ↔ daysSinceHigh30D = −0,729` · con lai |rho| ≤ 0,21
(`rvol7d` gan nhu doc lap: ≤ 0,206). ⇒ **hieu dung ~3 nhom tin hieu**: (i) momentum 7d + OI 7d,
(ii) momentum 30d + daysSinceHigh30D, (iii) bien dong dai han `rvol7d`. Day la co so de thiet ke
cac bien the train (muc 6).

### 4.3 Dau IC nhat quan voi feature hien co
Momentum/vol dai han co **IC am** (coin da tang / bien dong manh hon ⇒ `retEnd_4h` thap hon) —
cung dau voi `f6/f7/f8 momentum`, `f36 rvol15m`, `f10 distFromLow24H` trong
`EVAL_SELECTOR_FEATURES`. `daysSinceHigh30D` duong (gan voi "da tich luy lau" = tot) va nguoc dau manh
voi `mom30d` (−0,729).

### 4.4 `oi_delta7d`: ky han dai THAT SU them thong tin
`max|rho|` voi 21 keeper chi **0,259** (`oi_delta24h`) — tuc la OI 7 ngay **khong** la ban sao cua
OI 24h, va do la feature OI duy nhat vuot (a)–(d) trong khi `oiPersistence` (cung ho) bi (b) chan
(0,822).

## 5. Ghi chu ky thuat / sai so (de tai lap)

1. **Nguon gia:** `rvb_1m/raw/*.f32` (dtype `<i4,f4,f4,f4,f4,f4` = ts_phut,o,h,l,c,v; 627 symbol;
   2021-01-01..2025-12-31 UTC). Quy uoc `close(t) = c_1m[phut t]` duoc **kiem chung bang chinh feature
   cua repo**: `f35 ret15m = c[t]/c[t−15] − 1` khop ~1e-6 tren mau.
2. **Nguon gia KHAC nguon sinh `f0..f39`**: `retEnd_4h` (nhan) **khong tai lap duoc** tu cache nay
   (thu 6 symbol: |lech| 0,0–1,0pp o mot so mau). Vi vay cache **chi** dung de tinh feature moi va ghep
   theo `(ts, symId)`; nhan van lay tu `joined.parquet` ⇒ moi so IC o day co **sai so do lech nguon**
   (khong do duoc chinh xac), va khong duoc dung de khang dinh "feature X co/khong alpha".
3. **Do phu / NaN:** 1 feature A co coverage 0,9455 (`distFromHigh90D`, can 90 ngay warmup + coin moi list);
   cac feature khac ≥ 0,9623. `oi_delta7d` NaN 1,91% (chu yeu do ky 24h thieu trong chuoi OI 5m).
4. **Multiplicity:** do **20** feature (23 de xuat, 3 loai vi thieu du lieu) ⇒ CI nhan
   `inflate(k=23) = sqrt(2 ln 23) = 2,5042`; 2000 rep block-72h seed `20260905`.
5. **Nhan do vs nhan train (DINH CHINH 2026-09-24, commit `4adc4e1`):** nhan train THAT cua selector la
   **`retEnd_4h > 0,015`** (base 0,1849), **khong** phai `maxFav_4h >= 6%`. Sua lai: do IC tren
   **chinh `retEnd_4h`** (ban lien tuc cua nhan train) ⇒ IC o day **gan voi muc tieu train hon**
   so voi gia dinh trong pre-reg §6.1 ("nhan do khac nhan train") — day la **dinh chinh pham vi
   dien giai**, **khong** doi tieu chi/nguong/`k`. Luu y `maxFav>=0.06` la nhan cua ho
   `G015_v2` / **model LIVE ONNX**, khac han, khong dung cheo.
6. **Khong co ket luan** ve: sim/PnL, `maxFav`, nhom B, 3 feature bi loai, va ve "feature co alpha".

## 6. DE XUAT SO BIEN THE TRAIN (V0..V5) — ly do ngan

Boi canh: baseline = **21 keeper** (22 GIU bo `#36 rvol15m`). 5 feature PASS nam trong nguong 5..8
nen **khong cat**; nhung chung xep thanh ~3 nhom tin hieu (§4.2) ⇒ tach bien the de **do tac dong tung nhom**
thay vi chi do "tat ca vs khong".

| Bien the | Feature vao model | Ly do |
|---|---|---|
| **V0** | 21 keeper | **moc** — bat buoc co de biet "them feature moi" co lam gi khong (moi vong them feature truoc day deu NULL) |
| **V1** | 21 + **ca 5** (`rvol7d`, `mom30d`, `mom7d`, `daysSinceHigh30D`, `oi_delta7d`) | de xuat chinh: toan bo nhom A vuot ca 4 tieu chi |
| **V2** | 21 + **{`mom7d`, `mom30d`}** | nhom momentum dai han thuan (2 khung, cung ho voi `f8 momentum24H` da co — kiem "dai hon co them gi khong") |
| **V3** | 21 + **{`rvol7d`}** | **nguoi thay truc tiep cua `rvol15m` vua bi bo** (`#36`, 34% gain): kiem gia thuyet "model dang gan nhu 1-feature bien dong ngan han; keo dai khung 7d co giu duoc tin hieu khong" |
| **V4** | 21 + **{`daysSinceHigh30D`, `oi_delta7d`}** | 2 feature **it trung nhat** voi ho hien co (rho 0,320 / 0,259) va **khac ho nhau** (rho −0,176) ⇒ "thong tin moi" thuan |
| **V5** | 21 + 5 **+ 5 cot NHIEU** (dung dung NaN-mask cua 5 cot that) | **doi chung nhieu** theo protocol da dung (`PREREG_FEAT_ABLATION`): neu V1 khong hon V5 ngoai CI thi "them cot" = them nhieu, khong phai them tin hieu |

**Khong de xuat** them nhom B vao train (0/8 vuot (c)) tru khi doi cau hoi sang **tuong tac/timing**
— do la mot vong rieng, phai pre-reg rieng.

**Lien he voi `research/pipeline/featuresets/` (version hoa danh sach cot):** V0..V5 o day la **bien the
TRAIN**, khac truc voi `fs_v*`. Theo dung quy tac "them/bot cot => VERSION MOI" cua
`featuresets/README.md`, **khong duoc sua `fs_v2_21.json`**; moi bien the V1..V5 phai la mot file
`fs_v<k>_<n>.json` **MOI** (v3 da reserved cho ablation Stage 1 ⇒ bien the moi nen bat dau tu v4),
voi thu tu cot ghi ro (21 keeper theo thu tu `fs_v2_21` + cac cot moi **noi tiep o cuoi**, vi
`model_f*`/ONNX khong luu ten cot). So cot: V0 21 · V1/V5 26 · V2 23 · V3 22 · V4 23.

## 7. Gioi han
1. Pre-screen nay tra loi "co dang dot GPU khong", **khong** tra loi "co alpha khong".
1b. **Chinh chinh nhan (2026-09-24, `4adc4e1`):** nhan train la `retEnd_4h > 0,015` ⇒ IC do tren
   `retEnd_4h` la **ban lien tuc cua chinh nhan train** (xem §5.5). Khong doi ket qua loc.
2. `edge` decile (bp) khong feature nao ngoai 0 ⇒ ky vong **mac dinh la NULL** van giu nguyen.
3. Chua do: do on dinh theo nam, do on dinh qua fold, tac dong len `maxFav`, va tac dong len sim.
4. Lech nguon gia (§5.2) chua dinh luong duoc ⇒ moi IC o day co sai so chua do.
