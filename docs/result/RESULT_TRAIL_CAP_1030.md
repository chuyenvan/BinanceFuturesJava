# RESULT_TRAIL_CAP_1030 — Nang tran giveback trailing 3%/8% -> **10%/30%** tren SIM THAT (Kaggle, T170, DEV)

Chot truoc: `docs/prereg/PREREG_TRAIL_CAP_1030.md` (commit `066ec4e`). **Khong doi code** (chi override profile)
=> **khong build lai jar**: dung dung jar hien tai `sha256=70066fca…`.
**Khong push.** Sim **chi tren Kaggle** (khong chay Java tren Oracle — shadow active).

## 0. KET LUAN (doc truoc)

**NULL / KHONG HON** (vong thu 6 tren truc exit). Khong dat tieu chi GO da chot:

- **5 rate chat luong: KHONG rate nao doi co y nghia** — ca 5 delta deu **chua 0** o **ca hai** do rong
  CI (block-72h, 2000 rep, seed `20260905`): `win%` +0,01 · `TSloss%` −0,19 · `mP|SM` −0,13 ·
  `mP|SL` −0,10 · `meanP` −0,08. => **0/5 rate ngoai CI cung huong TOT, 0/5 rate XAU ngoai CI**.
  Tieu chi GO doi `>=2` rate TOT ngoai CI => **khong dat** (va cung khong co rate nao XAU ngoai CI).
- **Tong thi hoi GIAM**: equity cuoi 111 070 -> **110 188 (−0,79%)**, `SumPnL` 76 070 -> **75 189
  (−881 USDT)**, `meanP` 5,244 -> 5,163; n 1089 -> **1090**. CAGR 29,27% -> 29,04%.
- **Yeu cau cua owner DA duoc thuc thi dung nghia**: tran giveback khong con chan o 3%/8% —
  nhom `peak >= 20%` **thoat xa dinh hon that** (con cach dinh trung vi 8,14 -> **14,49 diem %**),
  giu lenh lau hon (hold trung vi 4,80 -> **5,95h**, turnover 0,792 -> 0,837).
  **Nhung no KHONG chuyen thanh loi nhuan**: lai cua nhom `peak>=20%` **tang** (`SumPnL` 51 997 ->
  62 072) trong khi **tong lai GIAM** => **tai phan phoi** (lai doi tu cho khac sang nhom nay + mat
  lenh o cho khac), khong phai cai thien tong the.
- **Giong nhu 5 vong exit truoc**: khong on dinh giua 2 nua cua so — **TRAIN +1 694 / TEST −2 792**
  (`SumPnL`), `meanP` TRAIN +0,128 **nhung** TEST −0,273 (dau nguoc nhau).
- Rang buoc cung (`RISK_APPETITE`): **PASS ca 2 chan** (cap: maxDD −12,04%/nam, UW 164 ngay,
  quy xau nhat −1,60%, khong nam am, tap trung 9,79%).
- **Khuyen nghi: DUNG truc tran gap.** Day la vong thu 6 tren truc exit; mat phang (response surface)
  theo truc `maxGap` da duoc lay mau o 0,03/0,08 (goc) · 0,05/0,12 (hinge) · **0,10/0,30 (vong nay)**
  · bac thang L1/L2/L3 · cap 0,20/0,35 (harness, dinh CLOSE) — **tat ca deu NULL**, va vong nay
  **nang tran manh nhat** van khong tao ra rate ngoai CI nao. Them cap nua **khong dang** (xem §7).

## 1. BUOC 0 — Tham so da doi (dung 2 tham so, khong gi khac)

Doc code: `Configs.java:140-141` (gia tri) + `:801-802` (override) + `TradeUtils.trailFromCap` :52-58
+ `OrderTargetInfoTest.trailRate` :374-394 (phan nhanh `pNoPump > TS_PNOPUMP_WEAK_THR`).

| # | vai tro | ten that trong code | CU | **MOI** |
|---|---|---|---|---|
| (a) | tran `maxGap` MANH | `Configs.TS_MAX_GAP` | `0.08` | **`0.30`** |
| (b) | tran `maxGap` YEU | `Configs.TS_MAX_GAP_WEAK` | `0.03` | **`0.10`** |
| (c) | nguong yeu/manh | `Configs.TS_PNOPUMP_WEAK_THR` | `0.29` | **0.29 (giu)** |
| (d) | ty le giveback | `Configs.TS_GIVEBACK_RATIO` | `0.5` | **0.5 (giu)** |
| (e) | nguong arm | `RATE_PROFIT_STOP_MARKET` (T170: `0.07`) | `0.07` | **0.07 (giu)** |

Giu nguyen: `peak = HIGH nen 1m` (`TS_PEAK_MODE` khong khai bao), step lam tron `0.005`, ratchet guard
(`priceSLNew > priceSL && > priceEntry`), loser time-stop 168h, funding/sizing/entry/gate/DCA.
Bat bien **SL > entry** van dung vi `gap = min(peak x 0.5, cap) <= peak x 0.5`.

**Pham vi anh huong (do TRUOC khi chay, tren trace parity, 1089 leg):** cap cu bind o **443 leg
(40,7%)** (weak peak > 6%: 320 leg; strong peak > 16%: 123 leg); cap moi chi con bind o **41 leg
(3,8%)**. => doi cap la **NOI trailing tren ~41% so lenh**, khong phai thay doi nho. Noi khac:
"3–8 diem cach dinh thi bi cat" **da duoc go** — sau khi doi, phai giveback ~10%/30% (hoac `peak/2`)
moi bi cat.

## 2. BUOC 1 — Code + profile (KHONG sua code, KHONG build lai)

Ca 2 tham so **da doc duoc qua override profile tu 2026-09-03** (`Configs.java:801-802`) => khong dong
nao code bi sua, **khong build lai jar**, **khong doi jar** (dung lai `70066fca…` cua vong peak-close).
Profile moi `profiles/x1_gs_t170_cap1030.properties` = ban sao nguyen `x1_gs_t170.properties` + dung
2 dong `SIM_TS_MAX_GAP=0.30` / `SIM_TS_MAX_GAP_WEAK=0.10` (khac **2 key duy nhat**).
`tools/check_cfg_gateway.sh` = OK.

## 3. BUOC 2 — CONG PARITY — **PASS byte-identical**

| chan | profile | override | printDone md5 | n | equity cuoi |
|---|---|---|---:|---:|---:|
| `tc-par` | `x1_gs_t170` (nguyen ban) | `SIM_TRAIL_TRACE=1` | **`efb793e2468ca3a7318da0f0ad23d4fc`** | 1089 | **111 070** |
| tham chieu | (`RESULT_PEAK_CLOSE` §3, jar cung sha) | | `efb793e2…` | 1089 | 111 070 |

`jar_sha256 = 70066fca33d347c3b6212dfd613f3a6694ca3684e7aece188790b183dfba24ff`,
`profile_hash = 23da7a0b5eba937b`, `symbol_mapper = 863`. => Cong parity **dat**, duoc phep doc ket qua
chan variant.

## 4. BUOC 3 — Ket qua chan cap 0.10/0.30 (`tc-cap`)

Chan variant chay **tren CHINH profile `x1_gs_t170` nhu chan parity** + dung 3 override
`SIM_TS_MAX_GAP=0.30`, `SIM_TS_MAX_GAP_WEAK=0.10`, `SIM_TRAIL_TRACE=1` (kiem lai trong
`prof_run.properties` cua kernel: tc-cap co 2 dong cap, tc-par khong co -> 2 chan chi khac nhau
**dung 2 tham so nay**; moi key khac giong y nguyen). Profile da commit
`profiles/x1_gs_t170_cap1030.properties` la **ban ghi tuong duong** cua tap override nay (khac
`x1_gs_t170` dung 2 dong) — dung lam tai lieu, khong can dua vao dataset.

`md5 printDone = 0c110a8aee1df8ce4ce1c963008674a1`, `profile_hash = e38c2d1b874d8b16`, `n = 1090`.

### 4.1 5 rate chat luong (theo LEG, toan bo tap) + CI block-72h

| rate | tc-par | tc-cap | delta | CI @1.21 (legacy) | CI @1.0 (inflate k=1) | ngoai CI ca 2 |
|---|---:|---:|---:|---|---|---|
| `win%` | 88,25 | 88,26 | **+0,011** | [−0,664, +0,720] | [−0,544, +0,600] | – |
| `TSloss%` | 9,73 | 9,54 | **−0,192** | [−0,709, +0,226] | [−0,628, +0,145] | – |
| `mP|SM` | 7,642 | 7,510 | **−0,131** | [−0,508, +0,324] | [−0,436, +0,252] | – |
| `mP|SL` | −16,992 | −17,096 | **−0,104** | [−0,293, +0,033] | [−0,264, +0,005] | – |
| `meanP` | 5,244 | 5,163 | **−0,081** | [−0,439, +0,337] | [−0,372, +0,270] | – |

**0/5 rate ngoai CI cung huong TOT · 0/5 rate XAU ngoai CI** => **khong dat** tieu chi GO (`>=2`).
Dau cua 4/5 delta la *hoi xau* nhung **deu nam trong nhieu** (khong ket luan duoc).

### 4.2 Rang buoc cung (RISK_APPETITE) + theo nam — **PASS ca 2**

| tag | equity | CAGR% | maxDD% | UW | quy min% | conc% (1 cum) | PASS |
|---|---:|---:|---:|---:|---:|---:|---|
| `tc-par` | 111 070 | 29,27 | −11,84 | 92 | −0,92 | 9,77 | PASS |
| `tc-cap` | 110 188 | 29,04 | **−12,04** | **164** | **−1,60** | 9,79 | PASS |

Theo nam (`maxDD% / UW / ret%`): 2021 −2,49/38/+12,83 · 2022 −12,04/73/+22,16 · 2023 −2,73/65/+35,35 ·
2024 −6,69/119/+27,53 · 2025 −3,78/164/+32,41 — **khong nam am**, UW 164 < 200, tap trung 9,79% < 15%.
(Luu y: `UW` cua ban cap **164 = dung bang F3** — cung la he qua "giu lau hon".)

### 4.3 n / hold / turnover

| tag | n_leg | hold med (h) | hold mean (h) | Σhold (h) | turnover |
|---|---:|---:|---:|---:|---:|
| `tc-par` | 1089 | 4,80 | 28,66 | 31 210 | 0,7915 |
| `tc-cap` | 1090 | **5,95** | 30,27 | 32 996 | **0,8368** |

=> Lenh giu **lau hon ~24%** (trung vi), turnover +5,7%; **khong mat luot vao** o quy mo lon (n +1) —
khac han F3 (mat 50 lenh). Day la diem **duong** cua chan nay so voi F3.

### 4.4 TRAIN / TEST (tach theo ngay LEG vao; TRAIN 2022-2023, TEST 2024-2025)

| period | tag | n | win% | TSloss% | mP|SM | meanP | SumPnL |
|---|---|---:|---:|---:|---:|---:|---:|
| TRAIN | tc-par | 324 | 85,49 | 12,96 | 8,131 | 5,499 | 24 019,6 |
| TRAIN | tc-cap | 326 | 86,50 | 11,96 | 8,026 | 5,627 | 25 713,5 |
| TEST | tc-par | 616 | 88,64 | 8,60 | 7,783 | 5,321 | 47 777,9 |
| TEST | tc-cap | 615 | 88,13 | 8,78 | 7,536 | 5,048 | 44 985,7 |

Hieu: **TRAIN `SumPnL` +1 694, `meanP` +0,128, `TSloss%` −1,00** (TOT) **nhung TEST −2 792,
`meanP` −0,273, `TSloss%` +0,18** (XAU) => **dau nguoc nhau o 2 nua cua so**, khong on dinh.
(Chan nay **khong** dung TRAIN/TEST de chon — chi de bao theo pre-reg.)

### 4.5 CAPTURE RATIO (bat buoc) — nhom dinh >= 20% / 50% / 100%

`peak` = `maePeak` = dinh **HIGH** gia that tu leg dau (cung mau so cho ca 2 chan);
`capture = ratePct/peakPct`; `med_gap_pp` = con cach dinh bao nhieu diem % luc thoat.

| nhom | tag | n | %trailing | %SL | med_capture | mean_capture | med_gap_pp | SumPnL | meanP |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **>=20%** | tc-par | 123 | 98,4 | 1,6 | **0,662** | 0,596 | 8,14 | 51 997 | 422,7 |
| | tc-cap | **155** | 98,7 | 1,3 | **0,504** | 0,498 | **14,49** | **62 072** | 400,5 |
| **>=50%** | tc-par | 29 | 93,1 | 6,9 | 0,406 | 0,420 | 64,70 | 23 049 | 794,8 |
| | tc-cap | **40** | 95,0 | 5,0 | 0,504 | 0,430 | 52,45 | **30 681** | 767,0 |
| **>=100%** | tc-par | 21 | 90,5 | 9,5 | 0,262 | 0,308 | 112,34 | 15 906 | 757,4 |
| | tc-cap | **22** | 90,9 | 9,1 | 0,288 | 0,325 | 109,77 | **17 675** | 803,4 |

**CI post-hoc block-72h (chi de doc, KHONG dung de ket luan — nhom la HAU-CHON theo dinh da xay ra):**

| nhom | d_capture | d_SumPnL |
|---|---|---|
| >=20% | **−0,099 [−0,146, −0,063] \*** | **+10 075 [+2 759, +18 007] \*** |
| >=50% | +0,010 [−0,107, +0,095] | **+7 632 [+2 554, +14 276] \*** |
| >=100% | +0,017 [−0,012, +0,093] | +1 768 [−928, +6 108] |

Doc ket qua nay **dung chieu ky vong da ghi TRUOC** (§1.2 pre-reg): tran rong hon => **thoat xa dinh
hon** => capture **giam co hoc** o nhom thap nhat (`peak>=20%`: 0,662 -> 0,504, ngoai CI) **va** nhom
nay co them **32 leg** (123 -> 155, vi song lau hon nen nhieu lenh cham +20%) => lai cua nhom **tang
+10 075** — **nhung do la dich chuyen thanh phan nhom (survivorship)**, khong phai cai thien cua
cung mot tap lenh: **tong `SumPnL` toan chan lai GIAM 881**. Nhom `peak>=50%`/`>=100%`: capture
**khong doi ngoai CI** (tang nhe, trong nhieu).

### 4.6 PnL / equity bao RIENG (KHONG dung de chon) + theo LEVEL

| tag | level | n | SumPnL | meanP | win% | TSloss% |
|---|---|---:|---:|---:|---:|---:|
| tc-par | BIG_DOWN | 248 | 16 254,4 | 4,786 | 88,71 | 8,47 |
| tc-par | DCA_LEVEL1 | 20 | 12 701,3 | 52,888 | 80,00 | 10,00 |
| tc-par | PREDICT_SYMBOL_TRADE | 821 | 47 114,5 | 4,221 | 88,31 | 10,11 |
| tc-par | **ALL** | **1089** | **76 070,2** | **5,244** | 88,25 | 9,73 |
| tc-cap | BIG_DOWN | 248 | 16 891,0 | 4,721 | 87,50 | 8,87 |
| tc-cap | DCA_LEVEL1 | 20 | 12 459,6 | 51,163 | 80,00 | 10,00 |
| tc-cap | PREDICT_SYMBOL_TRADE | 822 | 45 838,2 | 4,177 | 88,69 | 9,73 |
| tc-cap | **ALL** | **1090** | **75 188,8** | **5,163** | 88,26 | 9,54 |

Equity cuoi: **111 070 -> 110 188 (−882 USDT, −0,79%)** — khop `d SumPnL` (leg) = −881,4.

### 4.7 [POST-HOC — khong nam trong pre-reg] Ghep tung leg (1089 vs 1090, khop key `sym|start`: 1058 leg)

De tra loi cau "tien di dau", chia theo **leg co bi anh huong boi cap hay khong**:

| nhom | n | d_peakPct | d_gap_pp | d_capture | d_SumPnL |
|---|---:|---:|---:|---:|---:|
| leg **bi anh huong** (cap cu bind) | 426 | +3,55 | **+3,62** | **−0,126** | **+588** |
| leg **khong bi anh huong** | 632 | 0,00 | +0,01 | −0,006 | −269 |
| leg chi co o par / chi co o cap | 31 / 32 | – | – | – | **−1 201** (1 626 vs 425) |

=> Cap rong hon **lam dung nhu thiet ke** (gap +3,62 diem % tren 426 leg bi anh huong, dinh trung binh
+3,55 diem %) nhung phan lai tang them (+588) **khong bu duoc** phan mat do **doi thanh phan lenh**
(−1 201: 31 lenh cua parity bi thay bang 32 lenh khac) va phan nhieu nho o nhom khong doi (−269).
Tong = −882. **Ket luan khong doi: NULL.**

## 5. Ket luan + de xuat (theo §4.2 pre-reg da chot)

- **KHONG dat GO**: 0/5 rate ngoai CI (can `>=2`), 0/5 rate XAU ngoai CI, rang buoc cung PASS.
- **KHONG phai "chua du ket luan"** (dinh nghia: rate khong doi *nhung capture tang*): o day rate khong
  doi **va** capture nhom thap nhat **GIAM ngoai CI** dung nhu co hoc da ghi truoc, tong tien hoi giam,
  TRAIN/TEST nguoc dau => day la **NULL co giai thich**, khong phai tin hieu mo.
- **De xuat: DUNG truc tran `maxGap`.** Ly do (day la vong thu 6 tren truc exit):
  1. Day la **thay doi manh nhat con lai** tren truc nay (noi trailing tren **40,7%** so lenh, go han
     nguong "3–8 diem cach dinh thi bi cat" ma owner neu) — ma van **0 rate ngoai CI**.
  2. Mat phang theo truc `maxGap` da lay mau: **0,03/0,08 (goc, incumbent)** · 0,05/0,12 (hinge V1/V2/V3)
     · **0,10/0,30 (vong nay)** · bac thang L1/L2/L3 · 0,20/0,35 + `None` (harness, dinh CLOSE).
     **Moi diem do deu NULL**; chi phi bien (rate) khong bao gio xuat hien.
  3. Cap **0,10/0,30 khong con "chat"**: cap chi con bind o **41/1089 leg (3,8%)**; noi them nua gan
     nhu chi con tac dung o nhom dinh > 30–60% — nhom **n rat nho** (>=50%: 29 leg; >=100%: 21 leg).
     => **cac cap trung gian/rong hon nua (vd 0,15/0,45 hay `None`) chi con do lai gan nhu toan bo
     nhom cuc tri <= 22 leg — khong the dat `>=2` rate ngoai CI vi phuong sai qua lon.**
  4. Bang chung doc lap cung huong: `RESULT_CAPACITY_DIAG` — exit chi doi duoc **<5%** tap lenh
     va **nut that su la CONG AI** (17,9 trieu ung vien -> 841 PASS), khong phai exit.
- Ownership tam giu **T170**. Ket qua **am**: khong tich hop, **khong de xuat them slot Kaggle** cho
  huong nay. Neu muon tien, phai doi **tang khac** (entry/gate/capacity), khong phai tran gap.

## 6. Gioi han (ghi truoc trong pre-reg, khong phai loi chinh minh sau)
1. Kaggle sim chay `TICKER_SOURCE=file` (neo lech 1 lenh/970 vs aerospike) — khong anh huong so **giua
   2 chan** (cung bundle/cua so/che do).
2. **1 chan = 1 diem do**; khong quet cap khac trong round nay (§5 da tra loi vi sao khong nen quet them).
3. `maePeak` (mau so capture) **khong doi** theo cap => capture giam la **he qua thiet ke** (thoat xa
   dinh hon), **khong** phai bang chung xau; nhom la **hau-chon** theo dinh da xay ra (survivorship
   ghi ro o §4.5).
4. Nhom `peak >= 100%` chi **21–22 leg** => moi so nhom la tham khao, khong ket luan rieng.
5. Harness offline khong thay the duoc chan nay (dinh CLOSE + khong dinh gia phan "mat luot vao") —
   ly do bat buoc chay sim that; o chan nay **khong mat luot vao** (n +1), tuc rieng canh bao cua F3
   **khong** lap lai, va ket qua van NULL vi ly do khac (tai phan phoi + TRAIN/TEST lech dau).

## 7. Chi phi / thoi gian Kaggle

| | |
|---|---|
| Chan chay | 2 kernel SONG SONG (`sim-tc-par`, `sim-tc-cap`) — 2/5 slot, push->COMPLETE ~**40 phut** |
| JVM tren Kaggle | `tc-par` **1158,6s** · `tc-cap` **906,7s** |
| Chi phi | **0** (Kaggle CPU kernel khong tinh quota) |
| Dataset jar | `chuyendinh/sim-jar-cap1030` (private, 95 MB: `sim.jar` sha `70066fca…` + profile cap1030) |

## 8. Commit (khong push) + tai san dung lai

- `066ec4e` — prereg `docs/prereg/PREREG_TRAIL_CAP_1030.md` + profile `profiles/x1_gs_t170_cap1030.properties`.
  (**Khong co commit code**: khong sua dong nao.)
- commit CUOI cua vong nay (subject *result(trail-cap-1030): NULL*, `git log --oneline -1`) —
  `research/analysis/trailcap1030_run.py` + `trailcap1030_score.py` + tai lieu nay.

Tai san: `/home/ubuntu/kaggle_sim/out/{tc-par,tc-cap}/` (printDone + sim.out + `trailTrace.csv`) +
`/home/ubuntu/kaggle_sim/out/trailcap1030_score.{txt,json}`; bundle `sim-x1-2021-bundle` va jar
`70066fca…` tai dung (khong rebuild).
