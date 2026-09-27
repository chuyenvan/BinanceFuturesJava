# PLAN — INSTRUMENT FEATURE LIVE (`LIVE_FEAT_DUMP`) + TOOL DIFF VOI EXPORT DEV

Trang thai: **CHUAN BI (chua deploy, chua chay tren host live).** Owner phai duyet TRUOC khi ap.
Bo canh: `docs/result/RESULT_P15_SOURCE.md` — model gate p15 giong het fold_20, KHONG phai thieu scaler;
nghi pham con lai la **(iii) pipeline/feature duong LIVE KHAC export DEV**. Live khong ghi feature ra file
=> phai instrument moi do duoc.

---

## 1. Diem dung chung feature (file:line)

| Thanh phan | Vi tri |
|---|---|
| Duong LIVE sinh p15 | `src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java:265` (`aiBrain.predictAll(features)`) |
| Build vector 33 feature | `src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/OnnxInferenceManager.java:67-80` (`extractFeaturesV3Full`) |
| Feed model it nhat | `OnnxInferenceManager.java:45` (p15 = `SinglePredictor(modelDir,"futureReturn15M","Regressor")`), `:51` extract, `:53` `p15M.predict` |
| Model file | `Model_Regressor_Return15M.onnx` md5 `8ec9975726270782692bfe00b39bd37f` (= `wfo_models/fold_20`) |
| **NUM_FEATURES** | **33** (mang inline, KHONG co hang so ten `NUM_FEATURES`) |

**Nguon tung feature** (extractor `ComprehensiveMarketFeatureExtractor.extractAllFeatures:61`):

- Nen 1 phut/breadth/basket: **Aerospike** qua `DataManagerAerospikeFloatSim.readDataForSymbols` (DetectEntrySignal2TradeNormal:165) → `HistoryManager` ring (in-memory).
  momentum5M/1H/4H/24H, momentumAcceleration, trendStrengthETH(ETH), trendConsistency, volatility1M/15M/1H/24H/termStructure, rsi14, volumeSpike, distMA20, advanceDeclineRatio, percentAboveMA20, volumeRatioUpDown, marketBreadthStrength, btcDominance, basketMomentum15M/1H, basketRsi14, basketVolSpike.
- `marketRate` (tinh tu chinh batch kline do): momentum1M `=rateDownAvg`, momentum15M `=rateDown15MAvg`.
- Danh sach basket: `CoinRankManager.getTopCoin(ts)` (DetectEntrySignal2TradeNormal:85 → extractor:69).
- Funding: `FundingFeeManager.getNearestFundingFee` → **Aerospike** (`DataManagerAerospikeFloatSim.getFundingMap`): fundingRateRaw/Avg24H/Trend.
- Thoi gian: `Calendar` tu `timestamp` (tinh toan, khong nguon ngoai): hourOfDay/dayOfWeek/weekOfMonth/monthOfYear.

**Thu tu 33 feature (model an theo thu tu nay — CO Y NGHIA):**
`momentum1M, momentum5M, momentum15M, momentum1H, momentum4H, momentum24H, momentumAcceleration, trendStrengthETH, trendConsistency, volatility1M, volatility15M, volatility1H, volatility24H, volatilityTermStructure, advanceDeclineRatio, percentAboveMA20, volumeRatioUpDown, marketBreadthStrength, btcDominance, rsi14, volumeSpike, distMA20, fundingRateRaw, fundingRateAvg24H, fundingRateTrend, hourOfDay, dayOfWeek, weekOfMonth, monthOfYear, basketMomentum15M, basketMomentum1H, basketRsi14, basketVolSpike`.

⚠️ Thu tu cot trong CSV DEV (`gate15m_v2_full.csv`) **KHAC** thu tu tren (CSV: basket truoc funding truoc time).
`ml/gate/train_gate_fold.py:23-36` doc CSV theo **TEN** (hang so `V3FULL`), khong theo vi tri ⇒ moi tool doi chieu
PHAI align theo TEN, khong theo vi tri. Instrument cung ghi header co ten cot.

---

## 2. Instrument (da code, MAC DINH TAT)

- File moi: `src/main/java/com/binance/chuyennd/ai_ml/features/export/entry/LiveFeatureDump.java`.
- Diem goi (duy nhat): `DetectEntrySignal2TradeNormal.java` — ngay sau `predictData = aiBrain.predictAll(features);`
  (3 dong, gom 1 comment + 1 call 2 dong).
- Key: **`LIVE_FEAT_DUMP`** (int = **so tick ghi**). Doc qua `Cfg.getOr("LIVE_FEAT_DUMP","0")`.
  - **Khong khai / `<=0` ⇒ `maybeDump()` return NGAY**: khong tao file, khong doc/ghi gi, khong doi bat ky
    tham so/thuat toan nao khac. (`LIVE_` la trading-prefix: khi co `TRADING_PROFILE` phai khai key trong profile;
    khong co profile — nhu shadow dung `env.sh` — thi doc tu env nhu cu.)
- Khi bat: ghi `feat_dump/feat_dump_<yyyyMMdd_HHmmss>.csv.gz` (thu muc tuong doi theo CWD cua tien trinh),
  header `ts,symbol,<33 ten theo thu tu V3FULL>,p15_out`. Chi GHI, khong sua logic.
- **Tran cung 200 MB** (byte thuc ghi, dem bang counter — KHONG dung `file.length()` vi gzip buffer lam bao thieu):
  cham tran ⇒ ghi xong dong cuoi roi **DONG file, dung ghi**; ghi ro so dong. Ngoai ra con tran so tick = gia tri key.
  `syncFlush=true` ⇒ file doc duoc ngay khi dang chay.
- Moi loi IO bi nuot + tat dump: khong the anh huong duong LIVE.

**Bang chung "khong khai key ⇒ y nguyen"** (chay local, JVM rieng, `/tmp/lfd_probe`):
- Khong set `LIVE_FEAT_DUMP`: `DIR_EXISTS=false` (khong sinh `feat_dump/`), khong file, khong output khac.
- `LIVE_FEAT_DUMP=3`: 1 file, `wc -l` = 4 (header + 3 dong), 36 cot = `ts,symbol` + 33 + `p15_out`; tick thu 4,5 khong ghi.
- Test tran (ban copy nem `MAX_BYTES=1KB`, khong sua repo): dung sau 42 dong, file 1048 B (~tran + trailer gzip).

---

## 3. Thu thap (read-only) + cua so

1. (Owner) Build jar tu commit nay (khong push) va deploy nhu moi lan deploy shadow (`deploy/shadow_c3/README.md`).
2. (Owner) Them 1 dong vao `/home/ubuntu/shadow_c3/app/conf/env.sh`:
   `export LIVE_FEAT_DUMP=20000`  ← 20.000 tick ≈ **~14 ngay** (1 tick/phut = 1440/ngay).
3. (Owner) `sudo systemctl restart shadow-c3.service`.
4. Cua so de xuat: **~14 ngay** (>= 1 chu ky funding day du + du dai de co duoi). Co the dung som bang cach sua key = 0.
5. Thu thap: CHI DOC — `cp feat_dump/*.csv.gz /tmp/` (hoac `scp` ve may phan tich) roi chay tool diff.
   Dung luong thuc te rat nho: do duoc header+3 dong = 401 B nen ⇒ 20.000 dong ~ **vai MB** (<< tran 200 MB).

---

## 4. Xac minh

- Sau restart: `ls -la /home/ubuntu/shadow_c3/app/feat_dump/` phai co `feat_dump_*.csv.gz`.
- `zcat feat_dump/*.csv.gz | head -1` phai dung 36 cot, ten khop §1.
- `zcat feat_dump/*.csv.gz | wc -l` = so tick + 1, dung sau khi dat tran/key.
- Doi chieu cheo: `p15_out` trong dump phai khop `AiPredictionData.return15M` da ghi Aerospike cung `ts`.
- Log journald phai co dong `[LIVE_FEAT_DUMP] mo file ...` (va `DU TICK`/`CHAM TRAN` khi dung).
- Diff: `python3 research/analysis/feat_diff_live_vs_dev.py --live <dump.csv.gz> --dev ~/claudedata/gate15m_v2_full.csv`
  (co `--self-test` de chay thu offline; da chay local: 20 s, 43.201 dong khop, tool phat hien dung 2 feature bi pha co chu y).

---

## 5. Rollback

- **Tat**: bo dong `LIVE_FEAT_DUMP` khoi `env.sh` (hoac `LIVE_FEAT_DUMP=0`) → restart `shadow-c3.service`.
  Sau do `maybeDump()` return ngay ⇒ **y nguyen** hanh vi truoc khi bat.
- Xoa file da ghi: `rm -rf /home/ubuntu/shadow_c3/app/feat_dump/` (chi la file chan doan, khong ai doc).
- Rollback code: revert commit nay (chua push) — khong dong cham nao khac (khong sua ONNX/`NUM_FEATURES`/`extractFeatures45`/gate/tham so).

---

## 6. CANH BAO

- Day la **thay doi tren duong LIVE (SHADOW)** ⇒ **PHAI owner duyet truoc khi deploy**. Bai nay chi chuan bi code + plan.
- Sau khi co dump: **KHONG hieu chuan lai nguong** dua tren DEV (moi nguong hieu chuan tren DEV VO HIEU voi live —
  xem `RESULT_P15_SOURCE.md` §4). Chi ket luan duoc (ii) vs (iii) SAU khi diff xong.
- **KHONG** khoi phuc `Scaler_Return15M.onnx` (se pha p15: +7-20%).
- Dia 93 %: instrument da co tran 200 MB + tran tick; van nen theo doi `df -h /` khi bat.
