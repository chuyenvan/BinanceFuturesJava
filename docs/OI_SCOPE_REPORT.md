# OI_SCOPE_REPORT — pham vi cua moc doi nghia create_time 2024-03-04

Ngay do: 2026-09-03. Job dieu tra pham vi (khong sua du lieu, khong sua repo).
Script do: `/home/ubuntu/oiprobe/{m1,m2,m3,m4s,m5,m6,m7,m8}.py`, log `.log` cung ten.

---

## KET LUAN (5 dong)

1. Moc doi nghia anh huong **CA 6 COT DU LIEU** cua file metrics, khong rieng `taker_buy`:
   toan bo BAN GHI bi dich, khong phai mot cot.
2. Ban chat: `create_time` doi tu danh dau **CUOI** cua so 5m sang danh dau **DAU** cua so.
   Ban ghi tai `t` (t >= 2024-03-04) mo ta cua so `[t, t+5m)`, voi cac cot snapshot lay o
   **CUOI** cua so do (tuc trang thai tai `t+5m`) va cot flow tich luy tren ca cua so.
3. => **CA 5 feature OI** (`oi_delta24h`, `oi_z`, `ls_global`, `ls_toptrader`, `taker_buy`)
   chua 5 phut tuong lai tren **100% VALIDATION** va tren toan bo phan 2026 cua file OI dang dung.
   Ty le dong bi anh huong trong file OI trien khai: **71.30%** (100,475,431 / 140,924,110).
4. Bang chung manh nhat KHONG phai tuong quan ma la **dong nhat so hoc**: `vision(t) == api(t+5m)`
   voi `med_err = 0.000e+00` cho `sum_open_interest` va `sum_open_interest_value`; va cot 7 khop
   **chinh xac** ty le taker tinh tu kline (`med_err ~1e-4` o moc dung vs `~0.3-0.5` o moc sai).
5. Duong LIVE (REST API): API danh dau snapshot bang **dung thoi diem lay** (nhan qua), khac
   Vision-moi => **co train/serve skew 5 phut** o 4/5 feature OI. Cot taker thi API va Vision-moi
   **cung nghia** (moc = dau cua so) nen khong lech nguon-nguon.

---

## PHAM VI DU LIEU DA DOC (khai bao theo GIOI HAN CUNG)

Da doc metadata VA gia tri OI tho o **moi thoi diem**, ke ca sau 2024-07-15 va ke ca 2026.
Muc dich **duy nhat**: xac dinh TINH DUNG cua cot thoi gian (dong nghia giua 2 nguon).

- Vision daily metrics + daily kline 5m: DEV, VAL, va **mot ngay 2026 (2026-08-28, 3 symbol)**.
- REST API live `fapi.binance.com/futures/data/*` + `/fapi/v1/klines`, goi ngay 2026-09-03,
  3 symbol. Can thiet de giai mot **mau thuan** giua hai nguon (xem muc M6).
- Cot `ts` cua `/home/ubuntu/claudedata/oi/oi_percoin_full.bin` (dem dong theo ky).
  **Khong doc gia tri feature nao trong file nay**, chi doc cot thoi gian.
- Chi giu lai sai so tuong doi trung vi; khong luu gia tri thi truong 2026 nao.

KHONG lam: khong backtest, khong PnL/CAGR/maxDD, khong danh gia chien luoc, khong train,
khong chay java, khong sua du lieu OI, khong sua repo, khong mo `HoldoutSeal`,
khong doc label/score/ket qua 2026.

Ghi nhan phu (khong dung): file `oi_percoin_full.bin` **van con** 29,351,036 dong co
`ts >= 2026-01-01` (max ts = 2026-06-30 23:55). Do la du lieu OI tho, khong phai label/score.

---

## PHUONG PHAP — 4 phep do doc lap

**M1 — metadata min/max create_time theo ngay (phep do duoc goi y lam TRUOC).**
KET QUA **AM**: moi file daily, truoc va sau moc, deu chay `00:00:00 .. 23:55:00`, 288 dong,
header 8 cot khong doi. => **luoi nhan KHONG dich**, va gia thuyet "file cu chay 00:05..24:00"
la **SAI**. Phep do re nhat nay khong ket luan duoc gi; phai chuyen sang do gia tri.

**M2/M3 — doi chieu CHINH XAC voi kline 5m (khong phai tuong quan yeu).**
- Cot 7 (`sum_taker_long_short_vol_ratio`): kline daily co `taker_buy_volume` va `volume`,
  nen ty le taker cua tung bar tinh duoc **chinh xac** = `tb / (vol - tb)`. So voi cot 7 bang
  sai so tuong doi trung vi.
- Cot 2 + cot 3: `sum_open_interest_value / sum_open_interest` = **gia ngam** tai thoi diem lay
  snapshot. So voi close/open cua kline => xac dinh **thoi diem snapshot** chinh xac tung buoc 5m.
- Cot 4, 5, 6 (ty le ls, khong co nguon doc lap lich su): tuong quan **GOP** cua
  `d(cot) tren (t-5m, t]` voi return cua bar tai tung lag, gop 15 symbol x 7 ngay
  (n = 25,830..30,135 cap moi lag) — khong phai mot con so le.

**M6 — so sanh TRUC TIEP nguon-vs-nguon (phep do dut diem).**
Vision daily file 2026-08-28 vs REST API cung ngay, tung cot, tung shift.

**M7 — dem dong theo ky tren file OI trien khai** (chi cot `ts`).

**M5/M8 — dinh vi moc theo gio, va quet toan tuyen 2021..2025 tim moc thu hai.**

---

## BANG 8 COT

| # | ten cot | loai | bi dich moc? | bang chung | do chac chan |
|---|---|---|---|---|---|
| 0 | `create_time` | moc thoi gian (khong phai du lieu) | **chinh no doi nghia**: cuoi cua so -> dau cua so | toan bo bao cao nay | **CAO** |
| 1 | `symbol` | nhan | KHONG | hang so trong file | CAO |
| 2 | `sum_open_interest` | **snapshot** (so hop dong) | **CO, +5m** (snapshot lay tai `t+5m`) | M6: `vision(t) == api(t+5m)`, `med_err = 0.000e+00` (3 symbol x 288 moc). M2: gia ngam khop gia tai `t+5m` (6e-5) vs tai `t` (1.4e-3). M3 gop: peak `lag-1 +0.1208` (PRE) -> `lag0 +0.1670` (POST), n=30,135 | **CAO** |
| 3 | `sum_open_interest_value` | **snapshot** (USD) | **CO, +5m** | M6: `med_err = 0.000e+00` o shift+1 (3/3 symbol). M2: cung phep gia ngam | **CAO** — cot NAY sinh `oi_delta24h` + `oi_z` |
| 4 | `count_toptrader_long_short_ratio` | **snapshot** (ty le so tai khoan top) | **CO, +5m** | M6: shift+1 `med_err 1.0e-4` vs shift0 `1.1e-3`. M3 gop: `lag-1 -0.3639` (PRE) -> `lag0 -0.3327` (POST), n=25,830/30,135; cac lag khac ~0.00-0.05 | **CAO** — cot NAY sinh `ls_toptrader` |
| 5 | `sum_toptrader_long_short_ratio` | **snapshot** (ty le vi the top) | **CO, +5m** | M6: shift+1 `med_err 1.3e-5` vs shift0 `8.7e-4`. M3 gop: `lag-1 -0.0867` -> `lag0 -0.1141` | **CAO** (nhung KHONG feature nao dung cot nay) |
| 6 | `count_long_short_ratio` | **snapshot** (ty le tai khoan toan cau) | **CO, +5m** | M6: shift+1 `med_err 1.0e-4`. M3 gop: `lag-1 -0.2066` -> `lag0 -0.2370`, n=30,135 | **CAO** — cot NAY sinh `ls_global` |
| 7 | `sum_taker_long_short_vol_ratio` | **FLOW** (tich luy 5m) | **CO**: cua so doi tu `[t-5m,t)` sang `[t,t+5m)` | M2/M3: khop **chinh xac** ty le taker tu kline. Truoc moc `err_old` 1e-11..1e-4 / `err_new` 0.23-0.60; sau moc dao nguoc. M6: `vision(t) == api(t)` (`med_err 9.5e-5`) — API cung danh dau dau cua so | **CAO** — cot NAY sinh `taker_buy` |

**Phan giai: 6/6 cot du lieu, do chac chan CAO cho ca 6.** Hai cot con lai
(`create_time`, `symbol`) khong phai du lieu.

Anh xa cot -> feature (`ExportFundingOiPerCoin.java:70-71` che do vision,
`OiMetricSets.java:49-54`): `oi = maps[0]` = **cot 3**; `lst = maps[1]` = **cot 4**;
`lsg = maps[3]` = **cot 6**; `tk = maps[4]` = **cot 7**. Ca 4 cot duoc dung deu bi dich
=> **5/5 feature OI bi anh huong** (`oi_delta24h`, `oi_z` tu cot 3; `ls_global` cot 6;
`ls_toptrader` cot 4; `taker_buy` cot 7). Cot 2 va cot 5 khong duoc feature nao dung.

---

## MOC DOI: dinh vi chinh xac + kiem huong nguoc

**Theo ngay, 15 symbol** (`m3.log` PART A, `m4s.log`): quet 2024-02-26..2024-03-12.
Ca 15 symbol (ADA, ATOM, AVAX, BNB, BTC, DOGE, DOT, ETH, FIL, LINK, LTC, NEAR, SOL, TRX, XRP):
**OLD den het 2024-03-03, NEW tu 2024-03-04**. Khong co khoang chuyen tiep,
khong co symbol nao lech ngay. TRXUSDT co 4 ngay phep do gia-ngam ra AMBIG
(TRX bien dong 5m nho hon chenh mark-vs-last nen phep gia ngam mat phan giai);
phep do taker cua TRX van NEW ca 4 ngay do => khong phai bat dong thuc su.

**Theo gio** (`m5.log` PART 1): 2024-03-03 gio 00..23 = OLD **tat ca**;
2024-03-04 gio 00..23 = NEW **tat ca**. => moc la **2024-03-04 00:00:00 UTC**, sac net.

**Dau vet cau truc tai diem noi** (`m5.log` PART 2, BTCUSDT + ETHUSDT):
- label `03-03 23:55` khop bar `[23:50, 23:55)`
- label `03-04 00:00` khop bar `[00:00, 00:05)`
- => cua so **`[23:55, 00:00)` bi MAT hoan toan**, khong ban ghi nao mo ta no;
  va **0 ts trung lap** giua 2 file (`288 / 288 / trung lap = 0`).
Do la dau vet vat ly cua viec dich moc, doc lap voi moi phep tuong quan.

**Kiem huong nguoc — co moc thu hai khong?** (`m8.log`): quet theo quy
2021-01-15 .. 2025-12-15 (3 symbol) + 2024-02-15 + 2024-05-15.
Ket qua: **dung MOT lan doi duy nhat**. 2021-01 .. 2024-02-15 = OLD (ca 2 phep do);
2024-04-15 .. 2025-12-15 = NEW (ca 2 phep do). Khong co lan dao thu hai.

Chi tiet phu dang ghi: cot 7 **rong** trong file 2022-01-15 va 2022-04-15
(=> `taker_buy` = NaN o giai doan do); cot 4 va 5 rong trong file 2022-08-10.
Do phu cot thay doi theo thoi gian — khong lien quan moc 2024-03-04 nhung anh huong
ty le NaN cua feature.

---

## CAU 2 — VALIDATION, HOLDOUT, va duong LIVE

### 2.1 VALIDATION (2024-07-15 .. 2025-12-31): BI, 100%, da do TRUC TIEP
Khong phai suy ra. Da do va xac nhan NEW o ca 2 phep do tai:
2024-07-15, 2024-10-15, 2024-12-15, 2025-01-15, 2025-04-15, 2025-06-15,
2025-07-15, 2025-10-15, 2025-12-15 (m2.log, m8.log).
Trong file OI trien khai: **61,050,217 dong = 43.32%** thuoc VAL.

### 2.2 Phan bo dong cua file OI trien khai (`m7.log`)
`/home/ubuntu/claudedata/oi/oi_percoin_full.bin`, 140,924,110 dong,
ts 2021-01-01 00:00 .. 2026-06-30 23:55:

| ky | dong | % |
|---|---|---|
| DEV truoc moc (2021-01-01 .. 2024-03-04) | 40,448,679 | 28.70% |
| DEV sau moc (2024-03-04 .. 2024-07-01) | 9,011,190 | 6.39% |
| khe (2024-07-01 .. 2024-07-15) | 1,062,988 | 0.75% |
| VALIDATION (2024-07-15 .. 2026-01-01) | 61,050,217 | 43.32% |
| 2026+ | 29,351,036 | 20.83% |
| **TONG ts >= 2024-03-04 (bi dich)** | **100,475,431** | **71.30%** |

Trong rieng DEV: 9,011,190 / 49,459,869 = **18.22%** (khop moc 18.55% cua bao cao cu).
So voi bao cao cu: pham vi feature tu **1/45** len **5/45**; pham vi dong tu
"18.55% DEV" len "18.2% DEV + 100% VAL + 100% phan 2026 co trong file".

### 2.3 HOLDOUT 2026
Noi dung holdout (label/score/ket qua): **khong doc** (niem phong). Chi biet
(a) file OI van con 29.35M dong 2026, (b) quy uoc `create_time` cua nguon van la NEW
tai 2026-08-28 (do 1 ngay, 3 symbol). Suy ra: neu holdout 2026 duoc dung lai tu nguon nay
thi no cung bi. **Chua do truc tiep tren du lieu holdout.**

### 2.4 Duong LIVE REALTIME — CO train/serve skew, da do
Truy code (khong doan):
- `OpenInterestIngestor2AerospikeNew.java:53-58` — 5 endpoint API anh xa **dung** 4 cot
  ma feature dung (`openInterestHist`, `topLongShortAccountRatio`,
  `topLongShortPositionRatio`, `globalLongShortAccountRatio`, `takerlongshortRatio`).
- `:214` `out.put(o.getLong("timestamp"), v)` — lay `timestamp` cua API **nguyen xi**,
  khong dich. `OiFillGap.java:159` y het.
- Forward ghi **CUNG set/bin** voi backfill Vision (`OiMetricSets.java:49` va comment
  ":47-48": "history + forward ghi CUNG cho").
- `ComputeOiFeat2Live242.java:183-187, 216-220, 226-230` — dung dung 4 metric do, cong thuc
  y het `ExportFundingOiPerCoin`.
- `LiveOiFeatProvider.java:83-88` — `floorKey(t)` + tol 2h, chi LUI (dung huong).

Do tren API live (2026-09-03, `m5.log` PART 3):
- `openInterestHist`: gia ngam khop **gia tai `t`** (`2.6e-5`) chu khong phai `t+5m` (`6.0e-4`)
  => **API danh dau snapshot bang dung thoi diem lay** = NHAN QUA.
- `takerlongshortRatio`: `err_new 8.2e-5` vs `err_old 0.54`
  => API danh dau **dau cua so**, giong Vision-moi.
- Xac nhan cheo bang M6 (2026-08-28): `vision(t) == api(t+5m)` **chinh xac 0.000e+00** cho
  cot 2/3, `~1e-5..1e-4` cho cot 4/5/6; nhung `vision(t) == api(t)` cho cot 7.

**He qua (day la phat hien moi, khong co trong bao cao cu):**
1. `oi_delta24h`, `oi_z`, `ls_global`, `ls_toptrader`: **history (Vision, ts >= 2024-03-04)
   la trang thai tai `t+5m`, con live (API) la trang thai tai `t`** => lech **dung 5 phut**.
   Model hoc tren gia tri "som 5 phut", live nhan gia tri "dung gio" => train/serve skew.
   Va vi backfill + forward ghi cung set, **ben trong cung mot chuoi luu tru co mot buoc
   nhay 5 phut** tai diem noi backfill/forward.
2. `taker_buy`: hai nguon **cung nhan** (dau cua so) => khong lech nguon-nguon. Nhung API
   chi phat hanh dong taker **sau khi cua so dong** (do duoc: `max_ts` tre 5-12 phut so voi
   now) nen gia tri live thuc te la mot cua so **da dong**, con gia tri training tai cung `ts`
   la cua so **tuong lai** => van la mot lech nghia 1-2 bar, chi khac la live khong bi ro ri.
3. **Vi sao verify cu khong bat duoc**: `BackfillOiVerify.java:130` goi
   `openInterestHist?...&limit=30` (30 diem = 2.5h gan nhat) roi so `stored[ts]` vs `api[ts]`
   (`:141-147`). 2.5h gan nhat trong thuc te la **dong do forward ingest ghi** (chinh la API)
   => phep do so API voi API, **chua bao gio** so dong Vision-backfill voi API.
   Do la diem mu that su cua khau verify.

---

## CAU 3 — PHUONG AN SUA

### Danh gia cach da duoc neu (dich `+5m` cho ts >= 2024-03-04)

**DUNG.** Va **phai ap dung cho CA 6 cot, ke ca cot snapshot** — day la cau tra loi cho
cau hoi phu "co can dich cot snapshot hay chi cot flow".

Chung minh: ban ghi NEW tai `t` chua (a) flow tich luy tren `[t, t+5m)` va (b) snapshot tai
`t+5m`. Ban ghi OLD tai `t'` chua (a) flow tren `[t'-5m, t')` va (b) snapshot tai `t'`.
Dat `t' = t + 5m` thi hai mo ta **trung khop hoan toan cho ca hai loai cot**.
Da xac nhan (b) bang 2 duong doc lap: gia ngam khop gia tai `t+5m`, va
`vision(t) == api(t+5m)` voi sai so **chinh xac 0**.
=> **KHONG duoc ap quy tac khac nhau theo cot.** Mot phep dich `+5m` dong nhat la dung.

Tool1 (f0..f39) **khong can doi** — dung nhu bao cao cu noi.

### Ba phuong an

**A (de xuat) — dich `+5m` khi doc Vision, cho MOI ban ghi `create_time >= 2024-03-04T00:00Z`,
ap cho ca 6 cot; DONG THOI dich `+5m` cho cot taker cua duong FORWARD.**
- Diem sua: `VisionMetricsClient.parseDay` (`:248-250`, ngay sau `parseCreateTime`) hoac
  `OiMetricSets.normalize5m`; va `OpenInterestIngestor2AerospikeNew.parseAll` (`:214`)
  chi cho endpoint `takerlongshortRatio`.
- Vi sao phai dich forward taker: sau khi sua history ve quy uoc nhan qua (nhan = cuoi cua so),
  forward OI/LS **da dung san** (API danh dau snapshot tai dung thoi diem), nhung forward taker
  van danh dau dau cua so => neu khong dich, ta **tao ra mot skew 5 phut MOI cho taker**
  dung luc vua go skew cho OI/LS.
- Chi phi: build lai file OI (`ExportFundingOiPerCoin --vision`, ~554-880 coin x ~1,700 ngay
  daily Vision) + chay lai merge trong `gen_funding_wf_predictions_1m.py`. Toi **khong do**
  thoi gian thuc te (khong duoc chay java) — dung lay so nao tu bao cao nay.
- Rui ro / can luu y:
  - (r1) Lo trong `[2024-03-03 23:55, 00:00)` van la lo (1 ban ghi). `merge_asof backward`
    che duoc bang gia tri cu 5 phut. Khong sinh trung lap ts (da kiem: 0 trung lap; sau khi
    dich, ban ghi moi dau tien la `00:05` > `23:55`).
  - (r2) `oi_z` la accumulator expanding theo thu tu ts. Phep dich la don dieu tang, khong dao
    thu tu, khong sinh ts trung => `oi_z` chi doi gia tri, khong hong cau truc.
  - (r3) `oi_delta24h` trong 24h dau sau moc dang so 2 quy uoc voi nhau (cua so thuc 24h05m);
    sau khi sua thi sach.
  - (r4) Phai kiem lai diem noi backfill/forward trong Aerospike 226/242 sau khi sua
    (xem muc CHUA PHAN GIAI #2).

**B — dich ngay tai tang build feature (`ExportFundingOiPerCoin`), khong sua store tho.**
- Re hon (khong phai re-ingest 226/242).
- Nhung 226/242 tho **van sai**, nen moi consumer khac (verify tool, duong live doc 226,
  `ComputeOiFeat2Live242`) van sai; va trong cung mot set ton tai 2 quy uoc.
  => khong khuyen nghi lam phuong an cuoi cung.

**C — bo han 5 feature OI (hoac chi bo o phan sau moc).**
- Khong con leak, khong phai xu ly du lieu. Nhung mat tin hieu that (neu co) va tao mot
  **doan feature** tai 2024-03-04 neu chi bo mot phia. Van phai train lai.
- Dung lam phuong an du phong neu ap luc thoi gian cao.

**D (LOAI) — dich `-5m` cho phan truoc moc de dong bo theo quy uoc moi.**
Lam 100% lich su thanh ro ri. Tu choi.

**Cai KHONG duoc lam:** de nguyen va chi noi rong purge/embargo. Ro ri nam **trong** feature
vector, khong nam o ranh gioi train/test — purge 72h khong chan duoc (bao cao cu da noi dung).

---

## CAU 4 — LIET KE (khong lam)

### Model phai train lai
- **G015 selector** — 28 artifact `.json` trong `/home/ubuntu/sel_models_net015`
  (`model_f0_4h` .. `model_f15_4h` + phan con lai). Vi VAL/OOS **toan bo** nam sau moc,
  moi fold co train hoac test cham vung `ts >= 2024-03-04` => trong thuc te la **ca 16 fold**.
- Cac bien the neu chung tieu thu cung file OI (**chua kiem** — xem CHUA PHAN GIAI #5):
  `sel_models_net015_ds`, `sel_models_net008`, `sel_models_net03`, `sel_models_net03_ds`.
- Ban ONNX dung live (`conv_onnx.py`) phai convert lai theo model moi.
- Gate model (`train_gatemodels.sh` / `train_gatemodels.log`) neu dung score G015 lam dau vao.

### Thoi gian
**Khong do duoc trong job nay** (cam train / cam java). Hai cau phan chi phi:
(i) build lai file OI 4.2GB tu Vision, (ii) chay lai 16 fold cua
`gen_funding_wf_predictions_1m.py`. Khong trich dan so uoc luong nao tu bao cao nay.

### Ket qua da cong bo phai do lai
Tat ca thu nam duoi `score_g015` -> `dyn_thr` -> nguong vao lenh C2b:
- `docs/LEAK_L1_REPORT.md`: rho ~0.1675 va CI kem theo.
- `docs/CI_REAUDIT.md`: #8 gia tri XEP HANG `+0.0182 [+0.0085, +0.0227]`;
  #9 gia tri GATE `+0.0238 [-0.0053, +0.0442]`.
- `docs/PHASE1_DECISION_SURFACE.md`: B5 (`dyn_thr` clamp, nguong hang 1.713%,
  `profiles/c2b.properties:15-16`), B6 (K=8 vs K=5, phep do A8).
- `docs/PREREG_CI.md`: n hieu dung / DSR / PBO tinh lai.
- `docs/PREREG_GS.md` GS wave-1 (256 diem Sobol) neu co dung score selector.
- Moi so DEV/VAL cua C2b.
- **Va chinh `docs/FEAT40_LOOKAHEAD.md`**: cau "pham vi feature 1/45" va "18.55% dong DEV"
  gio **sai**. Phai sua thanh **5/45 feature**, **71.30% dong file OI**,
  **100% VALIDATION**.

---

## CHUA PHAN GIAI (can gi de phan giai)

1. **Do lon thiet hai that** (score G015 co vs khong co OI dung moc): **chua do**.
   Can chay lai inference (java/ONNX) tren bins da co — job nay khong duoc chay.
2. **Diem noi backfill-Vision / forward-API trong Aerospike 226/242**: **chua xac dinh**.
   Quan trong vi buoc nhay 5 phut nam dung o do. Can log van hanh cua TASK-035
   (ngay bat dau forward sweep) hoac mot lan doc 226/242 doi chieu voi Vision.
3. **File `oi_percoin_full.bin` duoc build tu `--vision` hay tu 226**: chi **suy ra** tu do phu
   2021-01-01..2026-06-30 va tu ten `oi_percoin_20210101_to_20260624.bin.gz`; log tai xuong
   (`claudedata/oi/oi_dl.log`) cho thay file duoc tai tu Kaggle, khong co log build.
   Neu build tu 226 thi phan duoi (sau khi forward ingest chay) co the **da nhan qua**,
   nghia la buoc nhay 5 phut nam **ben trong** file.
4. **Noi dung holdout 2026**: khong doc (niem phong). Quy uoc nguon da xac nhan NEW tai
   2026-08-28, nhung **chua do truc tiep** tren du lieu holdout.
5. **Model dir nao khac dung cung file OI**: chua kiem.
6. **Cot 2 va cot 5** bi dich nhung **khong feature nao dung** — neu ve sau co ai them feature
   tu 2 cot nay thi phai ap cung phep dich.
7. **Do phu cot theo thoi gian** (cot 7 rong dau 2022, cot 4/5 rong 2022) chua duoc do he thong;
   no anh huong ty le NaN chu khong anh huong ket luan ve moc.
