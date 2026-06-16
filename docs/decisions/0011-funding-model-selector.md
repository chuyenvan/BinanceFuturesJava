# ADR-0011: Funding model (per-symbol SELECTOR) — phân tích hiện trạng & thiết kế lại

- **status:** PHÂN TÍCH + ĐỀ XUẤT (chưa chốt). Song song ADR-0010 (market = gate). Thuộc P2 (ADR-0009).
- **Vai trò trong hệ:** market gate (ADR-0010) trả lời *"giờ có nên mở long mới không"*; funding model trả lời *"trong số coin, con nào đáng vào"* = **bộ chọn per-symbol**.
- **Liên quan:** ADR-0005 (trần inference funding) · ADR-0009 (pivot rebuild) · ADR-0010 (market gate) · REBUILD_ROADMAP.md.
- **⚠️ Không web:** phần "kiến thức thị trường" dưới đây từ hiểu biết tới 2026-01, KHÔNG phải tra cứu trực tuyến — cần đối chiếu nguồn ngoài khi có search.

---

## 1. Tư duy gốc (user) — model này NÊN bắt cái gì
Tại mỗi thời điểm thị trường luôn có **một vài coin được "bơm"** để tạo sóng / hút dòng tiền. Dấu hiệu kèm theo:
- **Funding bất thường** (lệch mạnh khỏi nền) + **volume lớn** đột biến.
- Hoặc kịch bản **quét short**: nuôi shorter ăn nhỏ một thời gian → squeeze mạnh một nhịp.

Mục tiêu model funding = **phát hiện sớm coin sắp được bơm / sắp squeeze**, để selector ưu tiên vào đúng con đang/đang-sắp có dòng tiền.

---

## 2. HIỆN TRẠNG (đọc từ code — sự thật, không suy diễn)

### 2.1 Export feature — `ai_ml/features/export/fundingv2/ExportFeaturesForPythonTool.java`
- Per-symbol, ghi `{time, id(symbol), features[21]}` ra `.bin.gz`, chunk 3 tháng, từ 2021-01, warmup 48h, extractor **stateful liên tục không reset** (`FundingFeatureExtractorV2.updateMarketHistory`).
- Basket = `CoinRankManager.getTopCoin(time)` (top50% tier thanh khoản) — ⚠️ NHƯNG đường còn lại (`funding/FundingDataCollectionManager`) dùng basket = `HistoryManager.findPotentialLosers` (coin sắp giảm). **Hai đường export song song, basket KHÁC NGHĨA** → feature basket-* khác hẳn. <CẦN XÁC NHẬN đường nào tạo training data thật>.
- **Label tính ở JAVA** (`FundingDataCollectionManager.calculateLabelsAndFormat` → `calculateLabelType` → `checkProfit`): quét `subMap[start, start+H]`, true nếu **`maxPrice ≥ target`** (target = entryPrice × 1.06/1.40). ⚠️ dùng **đỉnh nến (`maxPrice`)** + **KHÔNG chặn dưới** → first-passage một chiều, lạc quan (xem §4.1). `fundingv2` ghi `.bin.gz` feature-only; đường có label là CSV `data_funding_all.csv`.
- **21 feature** (đúng thứ tự `convertFeaturesToArray` = `extractFeaturesToArray` live):
  - *BTC/macro (5):* btcMomentum1H/4H/24H, btcDominance, marketBreadthStrength
  - *Coin-level (7):* momentum15M/1H/4H/24H, rsi1H, distFromLow24H, volatilityShock
  - *Basket (5):* basketMomentum15M/1H/24H, basketRsi14, basketVolSpike
  - *Funding (4):* coinFundingRate, fundingRateRaw, fundingRateAvg24H, fundingRateTrend
- ⚠️ **Tên feature lệch nghĩa (đã đọc extractor):** `fundingRateRaw` thực ra = **funding trung bình của BASKET** (`cachedBasketFundingRaw`), không phải coin; `momentum15M`/`momentum1M` gán từ `rate.rateDown15MAvg`/`rateDownAvg` (chỉ số **market-level MDO**), không phải return coin. ⇒ vài feature nhãn "coin" thực là market/basket → lẫn cấp + **trùng tín hiệu market gate**.

### 2.2 Label — `python/tool/train_fundingfee_xgboost_optuna.py`
- **5 lớp theo TỐC ĐỘ chạm target tăng giá:** `4`=chạm trong 15M · `3`=4H · `2`=24H · `1`=72H · `0`=**FAIL** (không chạm trong 72H).
- TARGET = `label6` (+6%) hoặc `label40` (+40%). ⇒ model học *"coin sắp tăng +X% nhanh tới đâu, hay không"* = **first-passage / pump-detection**. Khớp tư duy §1.
- Đo (đã viết lại cẩn thận): **de-overlap PER-SYMBOL** (horizon 72H), thước chính = **conditional hit-rate / LIFT vs base-rate + z-test** (cross-section chỉ 2–5 coin/mốc nên rank-IC cross-section vô nghĩa); rank-IC + t-stat + block-bootstrap là phụ. Split theo thời gian + purge 72H, **không shuffle, không scale** (live không có scaler). Gate: LIFT≥1.20, N≥100, z≥2, |t-IC|≥2. Holdout 12 tháng.

### 2.3 Inference — `ai_ml/onnx/funding/FundingOnnxInferenceManager.java`
- ONNX batch, input 21 feature, **output probs 5 lớp** (`float[][]`); crash-safe trả `{0,0,0,0,0}`.

### 2.4 Tiêu thụ ở ENTRY (đã đọc `SimulatorMarketLevelTicker1MStopLoss` + `AIRejectFilter`)
- **Funding pred ĐƯỢC dùng để RANK/CHỌN coin** (resolve): pred nạp qua `time2SymbolPred` (long[] encode → decode `Float.intBitsToFloat` = **1 scalar/coin** pre-compute từ 5 lớp). `extractPredict2Symbol` → `TreeMap<Float,Short>` sort theo pred; `MarketBigChangeDetector.getTopSymbolArray(numberOrder, …, predict2Symbol)` chọn **top-k coin** BUY ⇒ funding LÀ selector thật, không chỉ reject.
- **Trigger entry = MARKET, không phải funding:** chỉ vào khi `levelChange != null` (rule từ `rateDownAvg/rateUpAvg/rateDown15MAvg`) **và** `predict != null` (market ML `predReturn15M/predRisk4H`). ⇒ **market quyết WHEN, funding quyết WHICH** — phân vai gate/selector đã tồn tại một phần.
- Vẫn còn **mạch TRỘN vai** ở `checkSignalDynamic(prediction, symbolPred)`:
  - Nếu `predReturn15M < MIN_MOMENTUM_15M` **VÀ** `symbolPred > PREDICT_SYMBOL_RATE_MAX_THRESHOLD` → **REJECT** (DANGER).
  - `scaleFactor = (symbolPred / baseline) * AI_DYNAMIC_MULTIPLIER`, kẹp [MIN,MAX] → siết/nới ngưỡng động: `dynamic_15M = MIN_MOMENTUM_15M * scaleFactor`, `dynamic_Risk4H = HARD_RISK_LIMIT_4H / scaleFactor`.
  - `evaluate()` còn 2 nhánh: RISK (DD4H) + MOM15 (theo FILTER_MODE).
- ⚠️ **`symbolPred` là 1 scalar pre-compute** (gộp từ 5 lớp probs, lưu `time2SymbolPred`), không phải vector 5 lớp tại entry. **Scalar đó là đại lượng gì (P(fail)/P(pump)/expected speed?) và getTopSymbolArray chọn pred cao hay thấp** vẫn cần đọc `GenerateFundingPredictionsTool` để chốt dấu — chỗ dễ sai dấu nhất. <CẦN XÁC NHẬN scalar + chiều rank>.
- Mạch entry thứ 2 ("BƯỚC 3 funding") lặp `time2SymbolPred` riêng với `maxThres = PREDICT_SYMBOL_RATE_MAX_THRESHOLD × AI_DYNAMIC_MAX` → song song với getTopSymbolArray, cần hợp nhất sau rebuild.

---

## 3. Kiến thức thị trường (domain — chưa tra web, cần đối chiếu)
- **Funding rate** = phí định kỳ (8h, một số sàn 1–4h) giữa long↔short perp để neo giá perp về spot. Dương = long trả short (đám đông long, perp premium); âm = short trả long.
- **Pump + funding cao:** coin được đẩy → perp premium → funding dương mạnh + OI tăng + volume đột biến. Funding **cực dương kéo dài** thường đi trước **long-squeeze / xả** (đám đông long quá tải). ⇒ funding cao *một mình* mơ hồ: vừa là "đang được bơm (vào)" vừa là "sắp xả (tránh)". Phải đi kèm **biến thiên OI + volume + giai đoạn**.
- **Short-squeeze (kịch bản user):** funding **âm kéo dài** (đám đông short) + OI short chất cao → một nhịp đẩy giá ép short cover → bùng tăng. Tín hiệu nến: funding âm dai dẳng → giá nén → breakout + volume. Đây là **mẫu khác hẳn pump-long**, label hiện (chỉ "tăng +X% nhanh") **không phân biệt** hai cơ chế.
- **Hệ quả:** chỉ 4 feature funding thuần (rate/avg/trend) là **mỏng** so với điều cần bắt. Thiếu hẳn **open interest** và **volume bất thường** — hai chân quan trọng nhất của "đang được bơm".
- **Insight (kiến thức ≤2026-01, CHƯA web): funding cực trị thường CONTRARIAN ngắn hạn** — funding dương rất cao hay đi TRƯỚC điều chỉnh/xả (long quá tải), không phải tăng tiếp. ⇒ label "sắp tăng" + feature "funding cao" dễ khiến model học SAI CHIỀU nếu không có OI/giai-đoạn để tách *early-pump (vào)* vs *late-pump (tránh)*. OI + volume-trend là trọng tài phân biệt.
- **Insight: tín hiệu "bất thường" là TƯƠNG ĐỐI** — chỉ có nghĩa khi so mặt bằng. Cross-sectional rank/z (so các coin CÙNG mốc) + per-coin percentile (so lịch sử chính coin) thường mạnh hơn giá trị thô. Tham khảo: khung factor **qlib** (Alpha158/360 — momentum/volatility/volume factor đã chuẩn hoá) + **AFML** (triple-barrier, meta-labeling, sample-uniqueness). Crypto-specific: nhiều phân tích perp dùng **funding + OI + basis** làm proxy crowdedness; short-squeeze ≈ funding âm bền + OI short cao (analog "short-interest / days-to-cover" bên cổ phiếu).

---

## 4. PHÂN TÍCH PHẢN BIỆN

### 4.1 Label
- ✅ First-passage +X% là đúng hướng (phát hiện coin sắp chạy). Phân lớp theo tốc độ hợp lý (nhanh = tín hiệu mạnh hơn).
- ⚠️ **Một chiều (chỉ tăng).** Không có khái niệm "vào rồi sập" / drawdown trong cửa sổ → coin chạm +6% rồi −30% vẫn label tốt. Long-only DCA thì sập là rủi ro thật ⇒ **nên cân nhắc triple-barrier 2 phía** (chạm +X% trước / chạm −Y% trước / hết H) thay vì chỉ first-passage tăng. Khớp ADR-0010 §label market.
- ⚠️ **+6% vs +40% là hai bài toán khác nhau** (lướt sóng ngắn vs bắt trend lớn) — cần chốt selector phục vụ chiến lược DCA nào trước khi chọn target.
- ⚠️ **Không phân biệt cơ chế** pump-long vs short-squeeze (cùng cho ra "tăng nhanh") → model học trộn hai phân phối, khó và dễ nhiễu.

### 4.2 Feature
- ⚠️ **Thiếu Open Interest** — chân thiếu nghiêm trọng nhất. "Đang được bơm" = giá + OI + volume cùng tăng; "sắp squeeze" = OI short cao + funding âm. Không có OI thì model gần như **mù** với chính cơ chế user mô tả. **→ ĐÃ TÌM nguồn history (user, 2026-06-13): `data.binance.vision/.../daily/metrics/` có OI + long/short + taker TỪ 2020 — xem §5.3 (đảo kết luận "không backfill được").**
- ⚠️ **Volume bất thường yếu** — chỉ có `basketVolSpike` (rổ) + `volatilityShock`; thiếu **volume-z per-coin** (volume hiện / nền) là tín hiệu "bơm" trực tiếp.
- ⚠️ **Funding mới ở mức "raw/avg/trend"** — thiếu: **funding cực trị** (percentile trong lịch sử coin), **funding bền/dai** (số kỳ liên tiếp cùng dấu, để bắt "nuôi shorter một thời gian"), **dấu + độ lệch khỏi nền** thay vì giá trị thô.
- ⚠️ Nhiều feature **trùng với market gate** (btcMom, breadth, basket…) → nếu gate đã lo bối cảnh thị trường thì selector nên dồn vào **tín hiệu RIÊNG của coin** (funding/OI/volume/vị thế giá), tránh hai model học chồng nhau.

### 4.3 Tiêu thụ ở entry (cốt lõi — đã đọc Simulator)
- ✅ **Funding ĐÃ là selector rank** (getTopSymbolArray theo predict2Symbol) — phần "WHICH coin" đã đúng vai.
- ⚠️ **Còn mạch TRỘN vai** ở `checkSignalDynamic`: scaleFactor lấy `symbolPred` đi **siết/nới ngưỡng momentum + risk của market filter**. Đây đúng chỗ ADR-0010 muốn tách — funding KHÔNG nên chỉnh ngưỡng GATE. Sau rebuild nên **bỏ mạch scaleFactor**: gate tự quyết ngưỡng, funding chỉ rank coin. Khó giải thích + dễ sai dấu.
- ⚠️ **Hai mạch entry dùng funding song song** (getTopSymbolArray vs "BƯỚC 3") → hợp nhất thành một đường selector duy nhất sau rebuild.

### 4.4 Đo lường
- ✅ Khung đo (de-overlap per-symbol, lift/z, gate cứng, holdout 12T, không scale) đã chuẩn — giữ.
- ⚠️ Bổ sung **mục tiêu KINH TẾ** (như ADR-0010): selector tốt = cải thiện PnL/Sharpe của hệ **so với chọn ngẫu nhiên / chọn theo rule đơn giản** (vd "funding-percentile cao + volume-z cao"), không chỉ lift phân loại. Phải **beat một rule** mới giữ ML.

---

## 5. ĐỀ XUẤT THIẾT KẾ LẠI — đã DUYỆT (user)
**Chốt từ user:** (1) label **triple-barrier** — LÀM · (2) thêm feature **OI/squeeze** — LÀM (chờ xác nhận data OI) · (3) feature **market-context GIỮ**, đánh dấu tỉa-sau bằng importance (lý do user: đều là tham số ảnh hưởng giá MỌI coin; chất lượng kém mới cân nhắc lại) · (4) gỡ **mạch trộn-vai entry** (`checkSignalDynamic` scaleFactor) — **GÁC tới sau khi model xong + review kỹ**, không đụng bây giờ.

### 5.1 Vai trò
market = gate (ADR-0010, WHEN); funding = **selector per-coin** (WHICH), rank coin khi gate cho phép. Mạch scaleFactor trộn-vai: GÁC (mục 4), gỡ sau.

### 5.2 Label
✅ **Triple-barrier 2 phía** (chạm +X% trước / −Y% trước / hết H) thay first-passage một chiều dùng `maxPrice`. Chốt X/Y + target theo chiến lược DCA khi vào H1. [⬚ X/Y cụ thể chờ quét]

### 5.3 Feature — SỬA / GIỮ / THÊM
**SỬA (lẫn cấp — bắt buộc, kẻo diễn giải sai):**
- `fundingRateRaw` → đổi tên `basketFundingAvg` (nó là basket-avg, KHÔNG phải coin).
- `momentum1M`/`momentum15M` (đang = `rateDownAvg`/`rateDown15MAvg` market-MDO) → gọi đúng tên market-level, không để nhãn "coin".

**GIỮ (theo duyệt user — tỉa sau bằng importance, KHÔNG bỏ tay):**
- market-context: btcMomentum1H/4H/24H, btcDominance, marketBreadthStrength + basket-* → candidate; importance tỉa nếu trùng/thừa.

**THÊM — theo domain (per-coin, cái phân biệt coin-này-pump vs coin-khác):**
- *Funding sâu (per-coin):* **percentile/z-score** theo lịch sử CHÍNH coin (bất thường tương đối); **độ bền** (số kỳ liên tiếp cùng dấu, tổng funding N kỳ — bắt "nuôi shorter"); **|funding|** + **dấu** (âm = squeeze-setup; dương-cao = long-crowded → cảnh báo xả).
- *Volume per-coin (khả thi — đã có `getSumVolume`/`getAverageVolume`):* volume-z (cur/avgN), volume-trend, taker-buy ratio (nếu có).
- *Open Interest + long/short + taker ratio (✅ **CÓ HISTORY TỪ 2020** — `data.binance.vision/futures/um/daily/metrics/<SYM>`):* OI level, ΔOI, **OI/price divergence** (giá ngang + OI tăng = tích vị thế → squeeze setup), OI×funding (crowdedness); + **long/short ratio** (top-trader theo account & vị thế, global) + **taker buy/sell ratio**.
  - **PHÁT HIỆN (user 2026-06-13):** dump metrics có sẵn từ 2020, granularity ~5m. Fields: `sum_open_interest` (contracts), `sum_open_interest_value` (USDT — dùng cái này, chuẩn hoá cross-coin), `count/sum_toptrader_long_short_ratio`, `count_long_short_ratio`, `sum_taker_long_short_vol_ratio`.
  - ⚠️ **ĐẢO kết luận cũ:** "OI chỉ 30 ngày, không backfill được" CHỈ đúng cho API `openInterestHist`; **dump metrics thì backfill train 2021+ ĐƯỢC**. ⇒ OI/LS/taker thành **feature KHẢ DỤNG cho model v1**, KHÔNG phải chờ tích luỹ.
  - **Kiến trúc 2 nguồn:** (a) history batch từ metrics 2020→T-1 cho TRAIN (như backfill ticker 004/005, cùng host `data.binance.vision`); (b) forward poll T-1→now cho LIVE (TASK-007 phần C). Phải khớp đơn vị giữa hai nguồn.
  - **⚠️ CCD VERIFY trước khi xây (TASK-013):** granularity 5m thật; coverage per-coin (firstSeen — alt chỉ có từ ngày list, không phải 2020); `sum_open_interest_value` khớp định nghĩa `openInterestHist.sumOpenInterestValue` (tránh bậc thang train/serve); dedup dòng lặp + gap.
- *Cấu trúc giá:* distFromHigh (đối xứng distFromLow24H), vị trí trong range, **nén biên độ** (range/ATR co — pre-breakout); relative-strength vs BTC/basket (coin mạnh hơn nền = đang hút tiền).

**Chuẩn hoá CROSS-SECTIONAL (insight — chốt khi vào H1):** selector so coin-với-coin tại CÙNG mốc → feature bất thường nên là **rank/z trong số coin cùng mốc**, không phải giá trị tuyệt đối. "Vài coin được bơm" = bất thường TƯƠNG ĐỐI so các coin khác lúc đó. Cân nhắc thêm bản cross-sectional-rank của funding/volume/momentum.

### 5.4 Phân biệt cơ chế
✅ Thêm feature để model TỰ phân biệt pump-long vs short-squeeze (dấu funding + OI + nén giá). Tách sub-model: chưa cần, ưu tiên feature trước.

### 5.5 Acceptance kinh tế
Selector phải beat rule baseline (vd "funding-percentile cao + volume-z cao + OI tăng") trên OOS; không thì dùng rule, bỏ ML — như gate.

---

## 6. OPEN ITEMS (cập nhật sau khi đọc code entry + label)
- [x] **Code tính label** — Java `FundingDataCollectionManager.calculateLabelType` (peak-touch `maxPrice`, KHÔNG chặn dưới). Label đọc `subMap` tương lai (đúng chiều), nhưng phải kiểm de-overlap khi train.
- [x] **Nơi nạp `symbolPred` + RANK hay REJECT** — `time2SymbolPred` (scalar/coin) → `getTopSymbolArray` RANK top-k (selector thật) + `checkSignalDynamic` điều biến + mạch "BƯỚC 3" riêng.
- [x] **Scalar `symbolPred`** = `pred[0]` = **P(fail)** (FINDINGS §3) → rank ưu tiên P(fail) THẤP. ⚠️ cạm bẫy: đổi thứ tự output ONNX = sai dấu âm thầm → phải khoá thứ tự lớp khi train model mới.
- [x] **Đường export THẬT = `fundingv2/ExportFeaturesForPythonTool`** (basket=`getTopCoin` top-liquidity, ghi `.bin.gz`, `convertFeaturesToArray` khớp inference `FundingOnnxInferenceManager`). `funding/FundingDataCollectionManager` (findPotentialLosers, `data_funding_all.csv`) = đường phụ/cũ, KHÔNG khớp inference hiện tại. ⇒ basket train thật = **rổ top-thanh-khoản** (TASK-036, 2026-06-16; report `docs/reports/036.md`). F2 đã đổi tên: `fundingRateRaw`→`basketFundingAvg`, `momentum15M`→`rateDown15MAvg`, `momentum1M`→`rateDownAvg` (thứ tự 21 feature KHÔNG đổi).
- [x] **OI / long-short / taker:** ĐÃ backfill 2020→T-1 từ `data.binance.vision/metrics` (TASK-013, xong 2026-06-15) lên 226+242 — coin sống coverage tới ~T-1 (cách hiện tại <2 ngày), coin chết tới lúc delist; **KHẢ DỤNG cho train v1** (ĐẢO kết luận cũ "history ~30 ngày, không backfill được" — cái đó chỉ đúng cho API `openInterestHist`, KHÔNG đúng cho dump metrics). Forward (LIVE): OI đang chuyển 1-record/symbol → **chunk-tháng** + bổ sung LS/taker (TASK-035, đang code). ⚠️ **Giới hạn API:** 3 metric này KHÔNG có WebSocket và KHÔNG có endpoint all-symbol → buộc REST `/futures/data/*` **per-symbol** (~5 endpoint × ~554 coin ≈ 11–12'/sweep) → poll chu kỳ **~30'** (selector dùng khung chậm, không cần realtime). Riêng **funding rate** có `!markPrice@arr` (WS) / `premiumIndex` (REST) all-symbol nên tươi & rẻ. Volume per-coin: CÓ sẵn (ticker).
- [ ] Đối chiếu **nguồn thị trường ngoài** (khi có web) cho cơ chế funding/OI/squeeze.

---

## 7. Hệ quả
- Thuộc P2, **sau** market gate hoặc song song. Dùng chung data nền P1 (đã back