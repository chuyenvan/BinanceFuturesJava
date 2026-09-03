# FEAT40 LOOKAHEAD — soat ro ri tuong lai o tang FEATURE cua G015

> **DINH CHINH 2026-09-03 (docs/OI_SCOPE_REPORT.md):** pham vi trong file nay bi UOC LUONG THAP.
> Khong phai 1/45 feature va 18.55% DEV. Thuc te ca 6/6 cot du lieu deu bi dich moc
> (toan bo BAN GHI dich, khong phai mot cot) => **5/5 feature OI ro ri 5 phut**, 71.30% dong
> file OI trien khai, va **100% VALIDATION**. Ngoai ra co train/serve skew tren duong LIVE.


Ngay do: 2026-09-03. Pham vi du lieu: **CHI DEV** (2022-01-01 .. 2024-07-01, va cac file quy
2021Q4..2024Q1). KHONG doc VALIDATION (2024-07-15..2025-12-31), KHONG doc HOLDOUT 2026.
Khong chay java, khong backtest, khong train. Khong sua file trong repo.
Script do: `/home/ubuntu/leakprobe/{p1,p3,p4,p5,p6,p7,p8,p9,p10}.py` + `lk1..lk13.sh`.

Nguon ngoai duy nhat da tai: `data.binance.vision` (file metrics + kline 5m cong khai) de xac dinh
nghia cot thoi gian OI — chi cac ngay thuoc DEV.

---

## QUY UOC THOI GIAN (nen tang cho moi phan quyet ben duoi)

Day la muc PHAI chot truoc, vi moi cau tra loi phu thuoc no.

| Su that | Bang chung |
|---|---|
| Nen 1m duoc luu/ index theo `startTime` | `HistoryManager.java:92-106` (`processKline` dedup + `lastUpdateTime` deu dung `kline.startTime`), `:159` (`k.startTime <= timestamp`) |
| Key cua map ticker = moc phut, doc theo key "yyyyMMdd-HHmm" | `DataManagerAerospikeFloatSim.java:1120-1152` |
| => nen tai key `t` phu khoang **[t, t+1m)**; `priceClose` cua no chi biet duoc tai **t+1m** | suy ra tu 2 dong tren |
| Tool1 nap history cua moc `t` **TRUOC** khi trich feature tai `t` | `ExportFeaturesForPythonTool.java:208` roi `:307-308` |
| Nhan (label) neo vao `closeT` = close cua **CUNG nen do** | `ExportFundingLabel.java:429-431` (`cs.bClose = k.priceClose`), `:751-752` (`new Anchor(b, close)`) |
| Nhan chi lay nen path co offset `o >= 1`, tuc **startTime >= t+1 buoc** | `ExportFundingLabel.java:732-733` (`if (o < 1) continue`), doc `:723` ("path la (t, t+H], khong gom t") |

**Ket luan quy uoc: thoi diem quyet dinh THAT la `t_dec = t + 1m` (luc nen tai `t` dong).**
Feature dung du lieu den het nen tai `t` = den het `t_dec`. Nhan do tuong lai bat dau tu `t_dec`.
Hai ben **KHOP NHAU**. Do la quy uoc "quyet dinh tai bar close" chuan, KHONG phai leak.

Ghi ro de khong troi: neu label duoc sinh voi `LABEL_STEP_MIN=15` thay vi 1, thi `closeT` la close
cua phut cuoi bucket 15m (`t+15m`) trong khi feature vang tai `t` -> feature bi **CU hon** nhan 14 phut.
Do la lech theo huong AN TOAN (bao thu), khong phai leak. Ca hai truong hop deu khong ro ri.

---

## CAU 1 — Tim ra Tool1

**KET LUAN: TIM DUOC, day du, khong phai suy doan. Tool1 = `ExportFeaturesForPythonTool.startGeneration`,
40 feature va DUNG THU TU f0..f39 nam o `convertFeaturesToArray` (`ExportFeaturesForPythonTool.java:407-427`).**

Duong day code (da xac dinh):

| Lop | File:line | Vai tro |
|---|---|---|
| Orchestrator theo thang | `src/main/java/com/binance/chuyennd/ai_ml/features/export/fundingv2/ExportTool1Master.java` | tao task PENDING theo thang |
| Worker | `.../fundingv2/ExportTool1Worker.java:84-85` | goi `new ExportFeaturesForPythonTool().startGeneration(tmpDir, range[0], range[1], marketData, symbolMap)` |
| **Tool1 THAT (vong lap sinh feature)** | `.../fundingv2/ExportFeaturesForPythonTool.java:97-391` | day-loop, filter, PASS1/PASS2, ghi sink |
| **Thu tu f0..f39** | `.../fundingv2/ExportFeaturesForPythonTool.java:407-427` | mang 40 float, co comment #1..#40 |
| Bo tinh feature per-coin | `.../export/funding/FundingDataCollectionManager.java:202-587` (class `FundingFeatureExtractorV2`) | `extractFeatures` `:248-326` |
| Kho lich su (ring buffer) | `.../export/HistoryManager.java` | moi getter lookback |
| Ghi file `.t1c.gz` | `.../fundingv2/Tool1ColSink.java` | columnar + quantize int16/int32 |
| Doc o Python | `ml/lib/tool1_col.py:210` (`read_tool1`) | goi tu `gen_funding_wf_predictions_1m.py:111-120` |
| Ghep OI (5 feature cuoi) | `/home/ubuntu/claudedata/gen_funding_wf_predictions_1m.py:373-374` | `merge_asof` |

Da grep: `Tool1|feature|f0|buildFeature|extractFeature|exportFeature` tren `src/main`; tim theo ten
file dataset ma script G015 doc (`TOOL1_GLOB` -> `features_*.t1c.gz`); doi chieu `FEAT` o
`gen_funding_wf_predictions_1m.py:70`. Ket qua khop 1-1 voi `convertFeaturesToArray`.

Xac nhan doc lap them: ban inference LIVE lap lai **y het** thu tu 40 feature nay —
`ai_ml/onnx/funding/SelectorOnnxInferenceManager.java:56-76` (`extractFeatures45`, comment `:59`
ghi ro "KHOP HET ExportFeaturesForPythonTool.convertFeaturesToArray"). => thu tu cot khong bi lech
giua train va serve.

---

## CAU 2 — Bang 40 feature

**KET LUAN: soat DU 40/40. KHONG feature nao dung du lieu sau thoi diem quyet dinh `t_dec`.
11 feature co dung nen TAI `t` (close/high/low/volume cua nen [t, t+1m)) — hop le va CHI hop le vi
nhan neo vao close cua chinh nen do; neu ai doi quy uoc nhan, 11 feature nay thanh leak ngay.**

Viet tat nguon: `EFP` = `ExportFeaturesForPythonTool.java`, `FDCM` =
`export/funding/FundingDataCollectionManager.java`, `HM` = `export/HistoryManager.java`,
`FFM` = `research/FundingFeeManager.java`, `MDIG` = `export/MarketDataInlineGenerator.java`,
`MBCD` = `tradecore/MarketBigChangeDetector.java`, `EMD2F` = `research/ExportMarketData2File.java`.

Cot "nen t?" = co dung gia tri cua nen tai `t` (biet duoc luc `t_dec`) hay khong.
Cot "SAU t_dec?" = phan quyet ro ri: co dung du lieu sau thoi diem quyet dinh hay khong.

| # | Ten | Cong thuc | Cua so | nen t? | **SAU t_dec?** | Bang chung file:line |
|---|---|---|---|---|---|---|
| f0 | btcMomentum1H | close_BTC(t)/close_BTC(t-60m)-1 | [t-60m, t] | co (close) | **KHONG** | FDCM:489 -> FDCM:577-580 -> HM:427-437 |
| f1 | btcMomentum4H | idem 240m | [t-240m, t] | co | **KHONG** | FDCM:490; HM:427-437 |
| f2 | btcMomentum24H | idem 1440m | [t-1440m, t] | co | **KHONG** | FDCM:491; HM:427-437 |
| f3 | btcDominance | vol_BTC(t) / sum vol(t) | {t} | co (totalUsdt) | **KHONG** | FDCM:497-509 |
| f4 | marketBreadthStrength | #(close>open tai t) / #valid | {t} | co (close,open) | **KHONG** | FDCM:497-507 |
| f5 | rateDown15MAvg | avg top-100 (close(t)/max15m -1), tu MarketDataObject tai key t | [t-14m, t] | co | **KHONG** | EFP:308 (`time2MarketData.get(time)`); FDCM:285-286; MDIG:74-85 (quet **LUI**); MBCD:79,88; EMD2F:131-141 (`put(time, marketData)`) |
| f6 | momentum1H | close(t)/close(t-60m)-1 | [t-60m, t] | co | **KHONG** | FDCM:292; HM:427-437 |
| f7 | momentum4H | idem 240m | [t-240m, t] | co | **KHONG** | FDCM:293 |
| f8 | momentum24H | idem 1440m | [t-1440m, t] | co | **KHONG** | FDCM:294 |
| f9 | rsi1H | RSI14 tren 14 nen gan nhat | [t-14m, t] | co | **KHONG** | FDCM:296; HM:167-191 |
| f10 | distFromLow24H | (close(t)-low24)/low24 | [t-1440m, t] | co | **KHONG** | FDCM:299-301; HM:248-261 |
| f11 | volatilityShock | (high(t)-low(t)) / avgRange20 | {t} + [t-21m, t-1] | **co (high/low)** | **KHONG** | FDCM:582-586; HM:349-367 |
| f12 | basketMomentum15M | avg_basket getReturn(15) | [t-15m, t] | co | **KHONG** | FDCM:521,540; EFP:209 (basket tai t) |
| f13 | basketMomentum1H | avg_basket getReturn(60) | [t-60m, t] | co | **KHONG** | FDCM:522,541 |
| f14 | basketMomentum24H | avg_basket getReturn(1440) | [t-1440m, t] | co | **KHONG** | FDCM:523,542 |
| f15 | basketRsi14 | avg_basket RSI14 | [t-14m, t] | co | **KHONG** | FDCM:518,543; HM:167-191 |
| f16 | basketVolSpike | avg_basket vol(t)/avgVol20 | {t} + [t-21m, t-1] | **co (volume)** | **KHONG** | FDCM:524-526,544; HM:281-293,295-312 |
| f17 | coinFundingRate | funding cua settlement gan nhat <= t | (-inf, t] | - | **KHONG** | FDCM:555; **FFM:119** (`floorEntry`) |
| f18 | basketFundingAvg | avg_basket cua f17 | (-inf, t] | - | **KHONG** | FDCM:531-534,549; FFM:119 |
| f19 | fundingRateAvg24H | avg floorEntry tai t-0,4,8,12,16,20,24h | [t-24h, t] | - | **KHONG** | FDCM:558-568 |
| f20 | fundingRateTrend | f17 - f19 | [t-24h, t] | - | **KHONG** | FDCM:569 |
| f21 | fundingPercentileCoin | percentile cua funding hien tai trong **toan lich su <= t** | (-inf, t] expanding | - | **KHONG** | FDCM:346-357 (`floorKey(t)`), :373 (`headMap(key,true)`), :392-404 |
| f22 | fundingZCoin | z-score tren cung tap expanding <= t | (-inf, t] expanding | - | **KHONG** | FDCM:405-407 |
| f23 | fundingPersistence | so ky lien tiep cung dau, quet lui tu ky <= t | (-inf, t] | - | **KHONG** | FDCM:378-390 |
| f24 | fundingSum24h | sum funding settle trong (t-24h, t] | (t-24h, t] | - | **KHONG** | FDCM:412-417 (`subMap(t-24h,false,t,true)`) |
| f25 | fundingAbs | abs(funding ky <= t) | (-inf, t] | - | **KHONG** | FDCM:375 |
| f26 | volumeZCoin | (vol(t) - mean20_truoc)/std20_truoc | {t} + [t-21m, t-1] | **co (volume)** | **KHONG** | FDCM:430; HM:323-347 (`startIndex = head-1`, **bo nen hien tai** khoi mean/std) |
| f27 | volumeTrend | avgVol5 / avgVol60 (deu bo nen t) | [t-61m, t-1] | khong | **KHONG** | FDCM:431-433; HM:295-312 (`startIndex = head-2`) |
| f28 | distFromHigh24H | (high24 - close(t))/high24 | [t-1440m, t] | co | **KHONG** | FDCM:452; HM:248-261 |
| f29 | rangePosition24H | (close(t)-low24)/(high24-low24) | [t-1440m, t] | co | **KHONG** | FDCM:453-454 |
| f30 | atrSqueeze | avgRange14 / avgRange100 (deu bo nen t) | [t-101m, t-1] | khong | **KHONG** | FDCM:456-458; HM:349-367 |
| f31 | relStrengthBtc24H | f8 - f2 | [t-1440m, t] | co | **KHONG** | FDCM:460 |
| f32 | fundingRankCS | rank-percentile f17 giua cac coin **cung moc t** | {t}, cross-sectional | - | **KHONG** | EFP:320,447-468,474-498 |
| f33 | volumeZRankCS | rank-percentile f26 cung moc t | {t}, cross-sectional | - | **KHONG** | EFP:447-468 |
| f34 | momentumRankCS | rank-percentile f8 cung moc t | {t}, cross-sectional | - | **KHONG** | EFP:447-468 |
| f35 | ret15m | close(t)/close(t-15m)-1 | [t-15m, t] | co | **KHONG** | FDCM:472; HM:427-437 |
| f36 | rvol15m | std cua return giua 15 nen gan nhat | [t-15m, t] | co | **KHONG** | FDCM:473; HM:442-460 |
| f37 | volumeZ5m | sumVol5 / (avgVol20 * 5) | [t-20m, t] | **co (volume)** | **KHONG** | FDCM:474-476; HM:281-293,295-312 |
| f38 | closePosRange15m | (close(t)-low15)/(high15-low15) | [t-15m, t] | **co (high/low)** | **KHONG** | FDCM:477-481; HM:373-401 |
| f39 | wickRatio15m | avg (high-max(open,close))/(high-low) tren 15 nen | [t-15m, t] | **co (high/low)** | **KHONG** | FDCM:482; HM:405-421 |

### Vi sao khong co feature nao vuot qua t_dec — ly do KIEN TRUC (khong phai kiem tung dong)

Moi feature per-coin doc qua DUNG MOT cua: `HistoryManager` ring buffer. Ring la **append-only** va con
tro `historyHead` chi tang khi `processKline` duoc goi (`HM:92-106`). Tool1 goi
`updateMarketHistory(snapshot tai t)` roi moi trich feature tai `t` (`EFP:208` truoc `:307`). Vi vay
**phan tu moi nhat trong ring LUON la nen tai `t`**, va **moi** getter chi lui tu `head`:
`HM:157-163, 177-179, 199-201, 213-216, 235-238, 255-259, 272-276, 289-291, 304-310, 333-340, 358-364,
380-384, 396-400, 412-419, 431-435, 450-452`. Khong ton tai getter nao doc `head + k` voi `k > 0`.
=> khong co duong vao cho du lieu tuong lai o tang per-coin.

Ba nguon ngoai ring, da kiem rieng va deu LUI:
1. `MarketDataObject` (f5): quet max/min **LUI** `tickers.size()-i-1` (`MDIG:74-85`), luu theo dung
   moc `time` cua snapshot (`EMD2F:131-141`).
2. `FundingFeeManager` (f17..f25): `floorEntry` / `headMap(...,true)` / `subMap(...,t,true)` —
   khong bao gio `ceilingEntry`/`tailMap` (`FFM:119`; FDCM:348,373,412).
3. `CoinRankManager.getTopCoin(t)` (basket cho f12..f16, f18): xep hang bang
   `HistoryManager.getSumVolume(symId, 720)` (`CoinRankManager.java:196`) = ring <= t.
   Che do tinh (`WFO_STATIC_RANK`) dung `floorEntry(key)` (`CoinRankManager.java:168`) — cung LUI.

### Ket qua soat tung bay dien hinh

| Bay | Ket qua | Bang chung |
|---|---|---|
| Dung nen DANG chay thay vi nen da dong | **CO dung nen tai `t`** (11 feature) nhung nhan neo vao close cua CHINH nen do => khong ro ri. Day la quy uoc bar-close, KHONG phai bug. | `EFP:208,307`; `ExportFundingLabel.java:429-431,751-752,732-733` |
| Dung high/low/maxPrice cua nen tai t | CO: f11, f38, f39 (va f16/f26/f37 dung volume tai t). Cung ly do tren => khong ro ri. | FDCM:584, 477-482 |
| Chuan hoa / scale / winsorize bang thong ke TOAN KY | **KHONG CO.** Do that: 0/40 feature co (mean~0, std~1); 0/40 co std trung nhau giua 2 quy; mean lech toi 3.78 sd giua 2022Q1 va 2024Q1. Quantize cua sink dung min/max **CUA TUNG CHUNK** va co ghi `scale` de giai luong tu (`Tool1ColSink.java:42,252,284,297`), va comment `:43` ghi ro "TUYET DOI KHONG winsorize/clip theo percentile". Phia Python: grep `fillna\|ffill\|bfill\|interpolate\|StandardScaler\|MinMax\|scaler\|winsor\|clip(\|quantile\|center=\|rolling` tren `gen_funding_wf_predictions_1m.py` => **0 dong**. | `p5.log`; `lk6` |
| `fillna`/`ffill`/`bfill` lay gia tri tu tuong lai | **KHONG CO** o ca 2 tang. Java de `Float.NaN` khi thieu (FDCM:340-344, 430-433, 449-458, 476-481); Python khong fillna (XGBoost tu xu ly NaN). | `lk6`; FDCM:307-323 |
| rolling/EMA `center=True` | **KHONG CO** (khong co rolling nao trong ca 2 tang). | `lk6` |
| shift sai dau / join khong lech | Join `(symId, ts)` **exact**, khong shift. Nhan va feature dung cung `ts` va cung quy uoc bar-close. | `gen_..._1m.py:375`; muc QUY UOC |
| resample gan nhan dau ky nhung gia tri cuoi ky | **KHONG CO** o Tool1 (khong resample; `Tool1ColSink` dung `stepMin=1`, `tIdx` theo phut that — `EFP:267-269`). **CO o tang OI** — xem Cau 3. | EFP:267-269 |
| Chon mau (sample selection) dung du lieu tuong lai | **KHONG.** `EntrySignalFilter.selectCoins` chi dung `getAverageVolume`/`getReturn` tu ring <= t + rank cross-sectional cung moc. | `EntrySignalFilter.java:57-99` |

### Hai muc KHONG phai lookahead nhung phai ghi de khong troi

1. **Survivorship trong f3/f4/f5.** `Constants.diedSymbol` duoc dung de LOAI coin khoi trung binh thi
   truong (`MBCD:63`, `MDIG:63`). Danh sach coin "da chet" la thong tin cua TUONG LAI so voi `t`.
   Day khong phai lookahead ve GIA nhung la mot dang thien lech song sot da biet
   (repo da co `ai_ml/validation/data/SurvivorshipFeatureCheck.java` do viec nay). **Chua do lai o phien nay.**
2. **f23 `fundingPersistence` la ham tang theo lich.** mean 22.95 (2022Q1) -> 223.91 (2024Q1) (`p5.log`),
   vi no dem so ky lien tiep tren lich su expanding. No hoat dong nhu mot proxy cho THOI GIAN.
   Trong WFO expanding thi khong nhin duoc tuong lai, nen khong phai leak; nhung no lam model hoc
   duoc "dang o giai doan nao cua du lieu" — nen coi la rui ro tong quat hoa, khong phai ro ri.

---

## CAU 3 — 5 feature OI

**KET LUAN: co ché ghep (`merge_asof backward`, sort, tolerance) la DUNG va da xac nhan bang so.
NHUNG cot thoi gian `create_time` cua Binance **DOI NGHIA tu 2024-03-04**: truoc do no danh dau
CUOI cua so 5m (nhan qua, an toan), tu do tro di no danh dau DAU cua so 5m — nghia la gia tri tai `t`
mo ta khoang [t, t+5m). => **feature `taker_buy` ro ri 5 phut tuong lai tu 2024-03-04 tro di.**
Do la LEAK XAC DINH, do duoc, khu tru vao 1/45 feature va vao 1 khoang thoi gian.**

### 3.1 Co che ghep — SACH

| Muc | Ket qua | Bang chung |
|---|---|---|
| Huong ghep | `direction="backward"` — chi lay ban ghi OI co `ts <= ts_feature` | `gen_funding_wf_predictions_1m.py:374` (va ban chunk `:190`, `:149`) |
| Sort truoc khi ghep | **CO, ca 2 phia**: `t = t.sort_values("ts")`, `o = o.sort_values("ts")` ngay truoc `merge_asof` | `gen_..._1m.py:373` (va `:188-189`, `:139,147`) |
| Key phu | `by="symId"` — khong tron coin | `gen_..._1m.py:374` |
| tolerance | `OI_TOL_MS = 2h`; voi `direction=backward` tolerance chi **gioi han do CU** (`t - ts_oi <= 2h`), khong bao gio cho lay ban ghi moi hon `t` | `gen_..._1m.py:57,374` |
| Bien dau nam | OI duoc mo rong som `lo - OI_TOL_MS` de asof backward khong thieu gia tri o mep — dung huong | `gen_..._1m.py:179` (`ao_chunk = ao[(ao["ts"] >= lo - OI_TOL_MS) & (ao["ts"] < hi)]`) |
| `oi_z` co dung thong ke toan ky? | **KHONG** — expanding: `sum/sumSq/n` tich luy theo thu tu ts tang dan cua TreeMap, `z` tinh tai moi diem bang thong ke **den va gom** diem do | `ExportFundingOiPerCoin.java:98-113` |
| `oi_delta24h` | `oiVal(t) / oi(floorEntry(t-24h)) - 1`, co chan stale 60m | `ExportFundingOiPerCoin.java:105-107` |
| `ls_global`, `ls_toptrader`, `taker_buy` | `floorStale(map, t)` = `floorEntry(t)` + chan stale 60m — chi lui | `ExportFundingOiPerCoin.java:114-117,135-140` |
| Luoi ts cua file OI da trien khai | **100% dung luoi 5m** (48,173,553 dong DEV, 1 offset duy nhat = 0) | `p1.log` |
| `normalize5m` co the day moc VE QUA KHU? | Ham la `Math.round` (lam tron GAN NHAT) nen **ve nguyen tac** co the lui toi 2.5 phut = leak. **Do that: KHONG BAO GIO xay ra** — `create_time` nguon da dung luoi 5m san (0/1440 dong lech tren 5 symbol-ngay) | `OiMetricSets.java:58-59`; `VisionMetricsClient.java:250`; `p3.log` |

=> Ba cau hoi cua Cau 3 (dung cot, dung huong, dung thu tu sort) deu **DAT**.

### 3.2 Nhung cot thoi gian doi nghia — LEAK XAC DINH o `taker_buy`

`taker_buy = r/(1+r)` voi `r = sum_taker_long_short_vol_ratio`, cot 7 cua file metrics
(`OiMetricSets.java:52`, `ExportFundingOiPerCoin.java:117`), moc thoi gian lay tu cot 0 `create_time`
(`VisionMetricsClient.java:248`).

Khac voi `sum_open_interest` (anh chup tuc thoi), cot nay la mot **luong tich luy tren 5 phut**, nen
nghia cua no phu thuoc `create_time` danh dau DAU hay CUOI cua so. Do bang cach doi chieu voi kline 5m
that: ty le taker-buy cua mot cua so phai tuong quan MANH voi return cua **dung cua so do**.

`corr_spearman(taker_buy(ts), return cua nen 5m)` — BTCUSDT (`p8.log`, `p9.log`, `p10.log`):

| ngay | nen KET THUC tai ts (lag=-1, nhan qua) | nen BAT DAU tai ts (lag=0, ro ri) | nghia cua create_time |
|---|---|---|---|
| 2022-08-10 | **+0.7104** | -0.0583 | CUOI cua so — an toan |
| 2023-03-15 | **+0.7802** | -0.0463 | CUOI — an toan |
| 2023-09-08 | **+0.7527** | -0.1203 | CUOI — an toan |
| 2024-01-25 | **+0.7128** | -0.0504 | CUOI — an toan |
| 2024-02-01 | **+0.7662** | -0.0094 | CUOI — an toan |
| 2024-02-20 | **+0.7049** | -0.0097 | CUOI — an toan |
| 2024-03-01 | **+0.7603** | -0.0403 | CUOI — an toan |
| 2024-03-03 | **+0.7315** | +0.0586 | CUOI — an toan |
| **2024-03-04** | +0.0958 | **+0.7436** | **DAU — RO RI 5 PHUT** |
| 2024-03-05 | +0.0826 | **+0.7650** | DAU — ro ri |
| 2024-03-07 | +0.0103 | **+0.7843** | DAU — ro ri |
| 2024-03-10 | +0.0286 | **+0.7448** | DAU — ro ri |
| 2024-06-25 | +0.0891 | **+0.7612** | DAU — ro ri |

Kiem chung cheo tren 5 symbol khac (`p6.log`, `p7.log`): truoc moc doi, PRECEDING thang tuyet doi
(SOLUSDT 2022-08-10 +0.641 vs -0.040; ETHUSDT 2023-03-15 +0.682 vs -0.043; DOGEUSDT 2023-09-08
+0.776 vs -0.159; AVAXUSDT 2022-11-11 +0.558 vs -0.077; LINKUSDT 2024-01-25 +0.601 vs -0.065).

**Moc doi: giua 2024-03-03 va 2024-03-04.**

Ban chat: tu 2024-03-04, ban ghi mang moc `ts` mo ta luong taker cua khoang **[ts, ts+5m)** — thong tin
CHUA TON TAI tai `ts`. `merge_asof(direction="backward")` van lam dung viec cua no (`ts_oi <= t`),
nhung **du lieu ben trong ban ghi da la tuong lai**. Purge/embargo khong cuu duoc loai ro ri nay vi no
nam TRONG feature vector, khong nam o ranh gioi train/test.

**Do lon anh huong (do duoc, chi tren DEV):**
- Pham vi feature: **1/45** (`taker_buy`). 4 feature OI con lai (`oi_delta24h`, `oi_z`, `ls_global`,
  `ls_toptrader`) la anh chup trang thai, khong co "cua so tich luy" — phep do lech-nen tren `oi_diff`
  KHONG ket luan duoc (tuong quan yeu ca 2 phia: 2024-03-10 lag-1 +0.2119 vs lag0 +0.2017 — `p9.log`).
  => **KHONG TIM THAY BANG CHUNG** cho 4 feature con lai theo ca 2 huong; xem "Con lai chua dong".
- Pham vi thoi gian: **18.55% dong OI trong DEV** (8,936,857 / 48,173,553 dong co `ts >= 2024-03-05`) — `p10.log`.
- Do sau ro ri: **5 phut**, doi chieu horizon nhan **4h** (= 240 phut). Ty le 5/240 ~ 2.1% dau cua so nhan.
- **Diem nghiem trong nhat: moc doi 2024-03-04 nam TRUOC toan bo VALIDATION (2024-07-15..2025-12-31)
  va toan bo HOLDOUT 2026.** Nghia la 100% du lieu danh gia out-of-sample nam sau moc doi, trong khi
  ~81% du lieu DEV (nen phan lon du lieu TRAIN) nam truoc moc doi. Ngoai chuyen ro ri, day con la mot
  **doi nghia feature giua train va test** (train hoc `taker_buy` = qua khu, test/serve dua ra
  `taker_buy` = tuong lai) — mot regime break im lang.
- Toi **KHONG do** anh huong tren VAL/holdout (bi cam doc).

---

## CAU 4 — Kiem nghiem bang so

**KET LUAN: 3 phep do deu ung ho "khong co leak THO o f0..f39": (a) profile do lech cua score G015
giam TRON, khong co dinh nhon tai buoc 0; (b) khong co dau vet chuan hoa toan ky (0/40 feature
z-score, 0/40 std trung nhau giua 2022 va 2024); (c) luoi ts cua OI sach 100%. Phep do (a) co
DO NHAY THAP voi ro ri nho (<=15 phut) — no khong the va khong duoc dung de bac bo leak 5 phut o Cau 3.**

Khong train model. Khong chay java. Chi DEV.

### 4.1 Profile tuong quan theo do lech (`p4.py`, `p4.log`)

Du lieu: `/home/ubuntu/ledger/cand_dev3.parquet`, da loc `ts < 2024-07-01` (log xac nhan:
"after DEV filter rows=18484971", pham vi 2021-03-31 .. 2024-06-30). Panel 15,442,092 dong / 288 symbol,
100% dong dung luoi 15m. Ghep theo `sym` roi `shift(k)` co **kiem tra cung**
`(ts - ts_shifted == k*15m)` de khong ghep sai qua gap.

`corr(score_g015(t - k*15m), g1lite(t))`:

| k (buoc 15m) | n | spearman | pearson |
|---|---|---|---|
| -3 (feature SAU moc nhan) | 15,422,601 | -0.1647 | -0.1085 |
| -2 | 15,428,977 | -0.1662 | -0.1099 |
| -1 | 15,435,470 | -0.1685 | -0.1120 |
| **0** | 15,442,092 | **-0.1675** | **-0.1114** |
| 1 | 15,435,470 | -0.1667 | -0.1108 |
| 2 | 15,428,977 | -0.1660 | -0.1103 |
| 3 | 15,422,601 | -0.1654 | -0.1098 |
| 4 | 15,416,397 | -0.1648 | -0.1094 |
| 8 | 15,392,505 | -0.1632 | -0.1081 |
| 16 (= 4h) | 15,348,152 | -0.1600 | -0.1056 |

(Dau am la quy uoc dau cua `score_g015` trong ledger nay; |0.1675| tai k=0 **khop chinh xac** moc
0.1675 cua `LEAK_L1_REPORT.md`, xac nhan phep do bam dung cot.)

**Doc:** duong cong giam **don dieu va TRON** tu 0.1675 (k=0) xuong 0.1600 (k=16), khong co buoc nhay.
Chenh k=0 vs k=1 chi **0.0008** — nho hon sd block-bootstrap 0.0187 (moc cua bao cao L1) **23 lan**.
Feature bi leak tho co dang nguoc lai: dinh nhon tai k=0 roi sup ngay tai k=1 (vi du 0.40 -> 0.05).
Khong thay dang do. Chieu k<0 (feature lay tu SAU moc nhan, chi de kiem may do) cho 0.1685 tai k=-1
roi GIAM lai (0.1662, 0.1647) — hanh vi cua tin hieu tu tuong quan binh thuong.

**Gioi han cua phep do nay (phai ghi ro):** outcome `g1lite` co cua so **72h**. Mot ro ri 5-15 phut
bi pha loang trong 72h nen phep do gan nhu KHONG co suc phat hien no. Vi vay ket qua 4.1
**khong phai bang chung bac bo** leak 5 phut da tim thay o Cau 3; no chi loai tru leak THO
(loai lam vo nghia toan bo score). Trong `cand_dev3.parquet` / `path_labels.parquet` khong co
outcome horizon ngan hon 72h de do sac hon (`lk11`).

### 4.2 Kiem tra chuan hoa (`p5.py`, `p5.log`)

Doc 2 quy DEV bang chinh decoder cua repo (`ml/lib/tool1_col.py`):
`features_20220101_to_20220401.t1c.gz` (1,123,966 dong) va `features_20240101_to_20240401.t1c.gz`
(2,141,608 dong), da loc `ts < 2024-04-01`, luoi 15m.

| Kiem tra | Ket qua | Y nghia |
|---|---|---|
| Feature co dang z-score (mean~0, std~1) trong 2022Q1 | **0/40** | khong he co standardize |
| Feature co **mean trung nhau** giua 2 quy (rtol 1e-6) | **3/40** = f32, f33, f34 | 3 cai nay la rank-percentile cross-sectional; mean = 0.5 va std = 0.2887 = 1/sqrt(12) la **tinh chat toan hoc** cua rank deu tren [0,1], khong phai dau vet chuan hoa. Xac nhan bang code `EFP:474-498` |
| Feature co **std trung nhau** giua 2 quy | **0/40** | khong co hang so scale dung chung cho ca ky |
| Feature bi ep vao [0,1] | 12/40 (f3,f4,f21,f25,f28,f29,f32,f33,f34,f36,f38,f39) | deu la ty le/rank **theo dinh nghia** (dominance, breadth, percentile, rangePosition, wickRatio...), khong phai min-max scale: `p5.log` cho thay std cua chung KHAC nhau giua 2 quy |
| Dich chuyen phan phoi giua 2 quy | rat lon o vai cot: f23 `dmean/s22 = +3.780`, f18 `+2.935`, f21 `+2.092`, f22 `+1.409` | **bang chung truc tiep** rang gia tri la RAW, khong bi ep ve cung mot thang do toan ky |

Doi chieu voi code: `Tool1ColSink.java:252` ("colMeta: min/max/IQR chi tren gia tri HUU HAN, theo
**TUNG CHUNK**"), `:284` scale theo chunk, `:297` **ghi scale vao file** de giai luong tu ->
gia tri doc ra tro ve don vi goc. `:43` ghi ro "TUYET DOI KHONG winsorize/clip theo percentile".
Phia Python: 0 dong `fillna/ffill/bfill/interpolate/scaler/MinMax/winsor/clip/quantile/center=/rolling`
(`lk6`). => **khong co leak chuan hoa.**

Ghi nhan mot muc nho, khong phai leak: gia tri sau giai-luong-tu co nhieu ~0.0038 IQR
(`Tool1ColSink.java:35`), va **do lon** cua nhieu do phu thuoc min/max cua chunk (tuc phu thuoc ca
cac dong sau `t` trong cung chunk). Ve nguyen tac day la mot kenh thong tin, nhung de khai thac no
model phai dao nguoc nhieu luong tu de suy ra cuc tri cua chunk — khong kha thi ve thuc te.
Xep **INFO**, khong xep leak. Dieu dang lo hon o day la train/serve skew: ban live
(`SelectorOnnxInferenceManager.java:56-76`) **khong** luong tu hoa, nen no dua vao model gia tri float32
day du trong khi model duoc huan luyen tren gia tri da luong tu. **Chua ai do lech nay.**

### 4.3 Luoi thoi gian OI (`p1.py`, `p1.log`)

48,173,553 dong OI trong DEV: `ts % 300000` chi co **1 gia tri duy nhat = 0** (frac 1.000000),
`ts % 60000` lech = 0.000000. => luoi 5m sach, khong co ban ghi lech giay co the bi `Math.round`
day ve qua khu. Cong voi `p3.log` (0/1440 dong `create_time` nguon lech luoi tren 5 symbol-ngay)
=> risk cua `normalize5m` la **tiem an nhung khong hien thuc hoa**.

---

## CON LAI CHUA DONG (khong du bang chung — ghi de khong troi)

1. **4 feature OI con lai (`oi_delta24h`, `oi_z`, `ls_global`, `ls_toptrader`): KHONG TIM THAY
   BANG CHUNG theo ca hai huong.** Neu moc doi 2024-03-04 la mot **doi nhan create_time cho CA FILE**
   (chu khong rieng cot taker), thi ca 4 cot nay cung bi lech 5 phut ve tuong lai. Phep do `oi_diff`
   khong phan giai duoc (tuong quan qua yeu — `p9.log`). Can mot phep do khac (vi du doi chieu
   `sum_open_interest` tai `create_time` voi REST `openInterestHist`, hoac doi chieu 2 nguon doc lap)
   de ket luan. **Day la lo hong lon nhat con lai sau phien nay.**
2. **Anh huong dinh luong len score/gate: chua do.** Toi khong duoc train lai nen khong the do
   "score G015 co va khong co `taker_buy`" chenh bao nhieu. Do lon that cua thiet hai
   **chua biet**; toi chi biet pham vi (1/45 feature, 5 phut, 18.55% DEV, 100% VAL/holdout).
3. **VAL va HOLDOUT: khong doc (bi cam).** Moi phat bieu ve VAL/2026 trong bao cao nay la SUY RA tu
   moc doi 2024-03-04 nam truoc chung, khong phai do truc tiep.
4. **Survivorship trong f3/f4/f5** (`Constants.diedSymbol`, `MBCD:63`, `MDIG:63`): chua do lai.
5. **Train/serve skew do luong tu hoa** (muc 4.2): chua do.
6. **f5 phu thuoc vao set `market_data` da trien khai.** Toi xac minh HUONG cua so (lui) va moc luu
   (`put(time, ...)`) tren code sinh (`MDIG:74-85`, `EMD2F:131-141`), **khong** xac minh lai noi dung
   set da luu trong Aerospike 226 khop voi code do.
7. **Khong doc duoc `LABEL_STEP_MIN` that cua file label da dung.** Da chung minh CA HAI gia tri (1 va 15)
   deu khong gay ro ri (xem muc QUY UOC), nen khong can thiet cho phan quyet — nhung van la mot an so.

---

## PHAN QUYET

### => **CO LEAK XAC DINH**

Chon muc nay, khong chon "SACH", va **khong** chon "SOAT MOT PHAN" (vi 40/40 feature Tool1 da soat het).

**Leak duy nhat tim duoc, phat bieu chinh xac:**

> Feature `taker_buy` (feature thu 45, thuoc khoi 5 feature OI — **KHONG** thuoc f0..f39) chua
> **5 phut du lieu tuong lai** o moi ban ghi co `ts >= 2024-03-04`. Nguyen nhan: cot `create_time`
> trong file `data.binance.vision .../metrics/` doi tu "danh dau CUOI cua so 5m" sang "danh dau DAU
> cua so 5m" giua 2024-03-03 va 2024-03-04; pipeline lay nguyen `create_time` lam moc
> (`VisionMetricsClient.java:248`) nen tu moc do, gia tri tai `t` mo ta khoang `[t, t+5m)`.

Bang chung: `p8.log`, `p9.log`, `p10.log`, `p6.log`, `p7.log` — tuong quan voi nen 5m dao chieu dut
khoat tai dung 1 ngay (2024-03-03: PRECEDING +0.7315 / FOLLOWING +0.0586; 2024-03-04: PRECEDING
+0.0958 / FOLLOWING +0.7436), tai lap tren 5 ngay sau do va doi chung tren 5 symbol truoc do.
Code: `OiMetricSets.java:52` (cot 7), `VisionMetricsClient.java:248-250`,
`ExportFundingOiPerCoin.java:117`, `gen_funding_wf_predictions_1m.py:374`.

**Bao ve phan quyet cho phan CON LAI la sach:**

- **f0..f39: 40/40 da soat, khong thay lookahead.** Ly do kien truc (khong phai chi kiem mau): moi
  feature per-coin di qua DUY NHAT ring buffer append-only cua `HistoryManager`, va **moi** getter chi
  lui tu `historyHead` (16 vi tri code da liet ke o Cau 2). Ba nguon ngoai ring
  (`MarketDataObject`, `FundingFeeManager`, `CoinRankManager`) deu chung minh duoc la lui
  (`MDIG:74-85`, `FFM:119`, `CoinRankManager.java:196,168`). Cross-sectional chi dung coin cung moc `t`
  (`EFP:447-468`).
- **Quy uoc bar-close khop giua feature va nhan** — 11 feature dung nen tai `t` la hop le vi nhan neo
  vao close cua chinh nen do va do tuong lai tu do tro di (`EFP:208,307` vs
  `ExportFundingLabel.java:429-431,751-752,732-733`).
- **Khong co leak chuan hoa** — do that: 0/40 z-score, 0/40 std trung nhau giua 2022Q1 va 2024Q1,
  dich chuyen mean toi 3.78 sd; quantize theo tung chunk co ghi scale; 0 dong fillna/scaler/rolling
  o tang Python (`p5.log`, `lk6`, `Tool1ColSink.java:42-43,252,284,297`).
- **Co che ghep OI dung** — backward + sort ca 2 phia + tolerance chi gioi han do cu
  (`gen_..._1m.py:373-374`); luoi ts sach 100% (`p1.log`); `normalize5m` khong hien thuc hoa (`p3.log`).

**Vi sao KHONG the ket luan "SACH":** ro ri o `taker_buy` la do duoc, tai lap duoc, va nam dung
trong feature vector ma G015 tieu thu — purge 72h cua tang chia du lieu **khong** chan duoc no.

**Vi sao KHONG ket luan nang hon (vo hieu hoa moi ket qua):** ro ri khu tru vao 1/45 feature,
sau 5 phut, tren 18.55% dong DEV; va profile do lech cua score (muc 4.1) khong cho thay dinh nhon
nao — nen no khong the la nguon chinh cua rho ~0.17. Nhung phep do 4.1 co do nhay thap voi 5 phut,
nen **khong duoc dung no de tuyen bo thiet hai la nho**; thiet hai that **chua do duoc**.

---

## VIEC CAN QUYET

1. **Dong lo hong muc 1 phan "Con lai chua dong" TRUOC MOI VIEC KHAC**: xac dinh moc doi 2024-03-04
   chi anh huong cot 7 (taker) hay ca 8 cot. Neu ca 8 cot => **toan bo 5 feature OI ro ri 5 phut tren
   100% VAL va holdout**, va do la muc do nghiem trong khac han.
2. **Quyet cach sua `taker_buy`**: cach re nhat va an toan nhat la **dich moc len 5 phut cho moi ban ghi
   co ts >= 2024-03-04** (`ts_hieu_chinh = create_time + 5m`) khi build lai file OI, roi ghep lai.
   Khong can doi Tool1 (f0..f39 khong bi anh huong).
3. **Quyet co phai train lai G015 khong.** Chu y: sua feature nay lam doi 1/45 cot tren ~18.55% dong
   DEV va 100% dong VAL => doi score => doi `dyn_thr` => doi nguong vao lenh C2b. Neu khong train lai
   thi phai ghi vao bang quyet dinh rang score dang chay co feature ro ri 5 phut trong vung danh gia.
4. **Quyet co do "delta score co/khong taker_buy" khong** (khong can train: co the do bang cach thay
   cot taker bang NaN roi chay lai inference tren bins da co — toi KHONG chay vi khong duoc chay java/train).
5. Ghi nhan vao `PHASE1_DECISION_SURFACE.md` rang muc "f0..f39 opaque" (`:13`) **da duoc dong**:
   40/40 feature co cong thuc, cua so va bang chung `file:line` (Cau 2 bao cao nay). (Toi khong sua repo.)
