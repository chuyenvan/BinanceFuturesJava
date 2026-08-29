# Trailing-Stop: Hướng xây model/chiến lược riêng cho phần THOÁT LỆNH

> Bối cảnh: bot crypto futures **long-only, DCA, đòn bẩy 1x, KHÔNG hard-stop cứng**, chỉ
> **trailing-stop khi đã có lãi**. Hiện trailing chạy bằng **gene tĩnh** (tối ưu qua HPO/WFO),
> chưa có model học riêng cho việc thoát lệnh. Doc này: (1) mô tả CHÍNH XÁC trailing hiện tại,
> (2) điểm yếu, (3) 2–3 hướng xây model/chiến lược riêng, (4) một khuyến nghị ưu tiên + các bước
> triển khai nhỏ (validate-small-first).
>
> Doc nghiên cứu, KHÔNG sửa code. Mọi trích dẫn code là để tra cứu, không phải đề xuất vá ngay.

---

## 1. Cơ chế trailing-stop hiện tại (đọc từ code)

### 1.1 Các file & hàm liên quan
- `research/SimulatorMarketLevelTicker1MStopLoss.java` — vòng lặp tick 1M:
  `startUpdateOldOrderTrading()` → gọi `updateStatusNew()` / `updateTPSL()` / `closeOrder()`.
- `research/OrderTargetInfoTest.java` — trạng thái 1 **cụm lệnh** (cluster): `updatePriceByKlineSimple()`,
  `updateStatusNew()`, `updateTPSL()`, các field `priceSL / minPrice / maeLow / maePeak`.
- `tradecore/TradeUtils.java` — công thức rate: `calRateMinWithPredReturn15MForTradingStop()`,
  `calRateLossDynamicBuy()`.
- `tradecore/Configs.java` — các gene: `RATE_PROFIT_STOP_MARKET`, `TS_DYNAMIC_K`,
  `TS_PROFIT_MULTIPLIER`, `TS_GIVEBACK_RATIO`, `TS_MAX_GAP`, `TS_MAX_GAP_WEAK`,
  `TS_WEAK_MOMENTUM_THRES`, `HARD_STOP_LOSS_RATE`, `TIME_STOP_HOURS`.
- `ai_ml/onnx/AiPredictionData.java` — feature AI có sẵn: `predReturn15M`, `predRisk4H`.

### 1.2 Đối tượng áp trailing = CỤM (cluster), không phải leg lẻ
Do DCA, mỗi symbol chạy MỘT `OrderTargetInfoTest` gộp (`symbol2OrderRunning[id]`) với `priceEntry` =
**giá vào trung bình gia quyền** của mọi leg (xem `mergeOrder()`). Trailing tính trên giá vào TB này.
Mỗi lần DCA nhồi → `mergeOrder()` tạo lại cụm, `minPrice` reset về `ticker.priceClose` (nhưng `maeLow`
đo-lường thì KHÔNG reset). Nghĩa là **mỗi lần nhồi làm reset tham chiếu trailing của cụm**.

### 1.3 Luồng mỗi tick 1M (`startUpdateOldOrderTrading`)
1. `updatePriceByKlineSimple(ticker)`: cập nhật `lastPrice = close`; `minPrice` chỉ đi XUỐNG;
   `maeLow`/`maePeak` (chỉ đo-lường, không quyết định); `timeUpdate`.
2. **Cổng vào xử lý SL** — chỉ chạy tiếp nếu:
   `ticker.maxPrice >= priceEntry * (1 + RATE_PROFIT_STOP_MARKET)` **HOẶC** `priceSL != null`.
   → Tức là: hoặc trong nến này giá đỉnh đã chạm ngưỡng lãi ~**+1.032%** so với entry TB (điều kiện
   ARM lần đầu), hoặc SL đã được đặt từ trước.
3. Gọi `updateStatusNew()`. Nếu status thành `TAKE_PROFIT_DONE / STOP_LOSS_DONE / STOP_MARKET_DONE`
   → `closeOrder()`. Ngược lại gọi `updateTPSL()` (dời SL lên).

### 1.4 `updateStatusNew()` — ARM SL và khớp SL
- **Khi `priceSL == null` (CHƯA arm):**
  - (Tùy chọn, mặc định TẮT) `HARD_STOP_LOSS_RATE > 0` chỉ cho `PREDICT_SYMBOL_TRADE`: cắt khi lỗ sâu.
  - (Tùy chọn, mặc định TẮT) `TIME_STOP_HOURS > 0`: cắt lệnh chưa arm quá N giờ (tính từ leg ĐẦU cụm
    = `clusterFirstLegTime`, không bị DCA reset).
  - `rateLoss = calRateLossMax(ticker.maxPrice)` = **(đỉnh nến − entry)/entry** = mức lãi đỉnh trong nến.
  - `rateMin2MoveSl = calRateMinWithPredReturn15MForTradingStop(predReturn15M)`
    = `RATE_PROFIT_STOP_MARKET` (0.01032), nâng lên `predReturn15M * TS_DYNAMIC_K` nếu lớn hơn.
  - Nếu `rateLoss > rateMin2MoveSl` → **ARM**: `rateStop = calRateLossDynamicBuy(rateLoss, predReturn15M)`;
    `priceSL = entry * (1 - rateStop)` (qua `Utils.calPriceTarget`); `minPrice = lastPrice`.
    Với `BLOCK_INTRABAR_LOOKAHEAD=true` (mặc định) → chỉ ĐẶT SL, return; nến SAU mới khớp (chống look-ahead).
- **Khi `priceSL != null` (đã arm):** nếu `minPrice <= priceSL` → KHỚP.
  - `priceSL > priceEntry` → `STOP_MARKET_DONE` (thoát có lãi — đây là ca trailing "thắng").
  - ngược lại → `STOP_LOSS_DONE`.
  - Giá chốt `priceTP = min(priceSL, ticker.priceOpen)`: ca thường fill đúng SL; ca **gap-down**
    (open < SL) → fill tại open (haircut thực, đã mô hình hóa — bộ đếm `CLAMP_TOTAL`).

### 1.5 `updateTPSL()` — DỜI SL LÊN (ratchet, chỉ tăng)
- Chỉ chạy khi `priceSL != null`.
- `rateLoss = calRateLossMax(ticker.maxPrice)` (lãi đỉnh nến).
- `rateMin2MoveSl = TS_PROFIT_MULTIPLIER * calRateMinWithPredReturn15MForTradingStop(predReturn15M)`.
  → **TS_PROFIT_MULTIPLIER = 5.218**: yêu cầu lãi đỉnh phải cao GẤP ~5.2× ngưỡng arm mới dời SL tiếp.
- Nếu đạt → `rateSL = calRateLossDynamicBuy(rateLoss, predReturn15M)`;
  `priceSLNew = entry * (1 - rateSL)`; chỉ dời khi `priceSLNew > priceSL` **và** `priceSLNew > priceEntry`.
  → SL chỉ đi LÊN và luôn nằm trên entry sau khi ratchet (khóa lãi). `minPrice = lastPrice`.

### 1.6 `calRateLossDynamicBuy(maxProfitRate, predReturn15M)` — khoảng "nhả lại"
```
maxGap = (predReturn15M < TS_WEAK_MOMENTUM_THRES ? TS_MAX_GAP_WEAK : TS_MAX_GAP)   // 0.03 : 0.08
gap    = min(maxProfitRate * TS_GIVEBACK_RATIO, maxGap)                            // GIVEBACK=0.5
rate   = round((maxProfitRate - gap) / 0.005) * 0.005                              // làm tròn bậc 0.5%
```
→ SL đặt ở mức lãi = **đỉnh − gap**. `gap` = nửa lãi đỉnh (`GIVEBACK_RATIO=0.5`) nhưng **trần cứng**
`TS_MAX_GAP=8%` (hoặc `3%` nếu momentum yếu, `predReturn15M < 0.4%`).

### 1.7 Giá trị gene hiện tại (Configs.java)
| Gene | Giá trị | Vai trò |
|---|---|---|
| `RATE_PROFIT_STOP_MARKET` | 0.01032 | Ngưỡng lãi để ARM lần đầu + base min-move |
| `TS_DYNAMIC_K` | 0.29774 | Nâng ngưỡng arm theo `predReturn15M` |
| `TS_PROFIT_MULTIPLIER` | 5.21847 | Bội số ngưỡng để DỜI SL tiếp (ratchet chậm) |
| `TS_GIVEBACK_RATIO` | 0.5 | Tỉ lệ nhả lại lợi nhuận đỉnh |
| `TS_MAX_GAP` | 0.08 | Trần khoảng nhả (momentum thường) |
| `TS_MAX_GAP_WEAK` | 0.03 | Trần khoảng nhả (momentum yếu) |
| `TS_WEAK_MOMENTUM_THRES` | 0.004 | Ngưỡng coi momentum là yếu |
| `HARD_STOP_LOSS_RATE` | 0 (off) | Cắt lỗ sâu (chỉ PREDICT_SYMBOL_TRADE) |
| `TIME_STOP_HOURS` | 0 (off) | Cắt theo thời gian lệnh chưa arm |

**Tổng kết bản chất:** trailing = ARM khi lãi vượt ~1% → khóa lãi ở mức `đỉnh − min(0.5·đỉnh, 8%)`,
ratchet lên rất chậm (cần lãi ×5.2). Yếu tố "thích ứng" DUY NHẤT là `predReturn15M` (1 con số AI/nến)
điều tiết ngưỡng arm và chọn trần gap thường/yếu. Tất cả còn lại là **hằng số tĩnh, chung cho mọi
coin và mọi regime**.

---

## 2. Điểm yếu của trailing hiện tại

1. **Cắt lãi non ("cắt non") vs whipsaw — cùng một hằng số:** `gap` tính theo % lãi tuyệt đối, KHÔNG
   theo biến động (ATR/vol) của từng coin. Coin vol thấp: gap 8% quá rộng → nhả lãi vô ích. Coin
   shitcoin vol cao: gap dựa trên `GIVEBACK 0.5` + trần 8% dễ bị **quét (whipsaw)** trong một nến
   nhiễu rồi giá lại tăng tiếp → thoát non. Một bộ số không thể tối ưu cả hai.
2. **Không thích ứng regime thị trường:** cùng một trailing áp cho bull trend mạnh (nên nới để cưỡi
   trend) lẫn thị trường sideway/choppy (nên siết để chốt nhanh). `predReturn15M` chỉ là micro-momentum
   15 phút, không đại diện regime vĩ mô (BTC trend, breadth, volatility regime).
3. **Ratchet quá chậm (`TS_PROFIT_MULTIPLIER=5.2`):** sau khi arm, SL chỉ dời tiếp khi lãi lại tăng
   ×5.2 ngưỡng. Với winner tăng dần đều (không nhảy vọt), SL "đứng im" lâu → trong nhịp đảo chiều
   nông vẫn nhả nhiều lợi nhuận đã có.
4. **ARM trễ + gap-fill:** ARM chỉ khi đỉnh nến chạm +1.032%. Coin vol cao có thể vọt +5% rồi sập
   trong cùng/kế nến trước khi SL kịp ratchet; gap-down khiến fill tại `bar.open` (đã mô hình hóa
   haircut, nhưng vẫn là mất mát thật). Trailing không "biết" xác suất đảo chiều để arm/siết sớm hơn.
5. **Coupling với DCA:** trailing áp trên **entry trung bình cụm**; mỗi lần nhồi reset `minPrice` và
   thay đổi ngưỡng arm. Một lần DCA muộn kéo entry TB xuống → thay đổi toàn bộ động học thoát của cụm.
   Logic thoát và logic nhồi bị trộn, khó tối ưu độc lập.
6. **Tối ưu bằng gene tĩnh dễ overfit:** 8 gene trên được HPO chọn trên lịch sử; một bộ số cố định cho
   5 năm × mọi coin có nguy cơ khớp quá khứ. Không có cơ chế cập nhật theo điều kiện hiện hành.
7. **Không dùng thông tin rủi ro sẵn có:** `predRisk4H` (dự báo rủi ro 4H) đang KHÔNG được dùng trong
   trailing — trong khi đây chính là tín hiệu "khả năng sập" hợp lý để siết gap.

---

## 3. Ba hướng xây model/chiến lược riêng cho trailing

Nguyên tắc chung xuyên suốt (tránh look-ahead): **mọi quyết định tại nến t chỉ được dùng dữ liệu
≤ t** (đúng như `BLOCK_INTRABAR_LOOKAHEAD` đang bật). Label ex-post (nhìn tương lai) CHỈ dùng lúc
train/gán nhãn offline, TUYỆT ĐỐI không đưa giá trị tương lai vào runtime.

### Hướng (a) — Rule-based thích ứng regime/volatility (nâng cấp công thức, KHÔNG học)
**Ý tưởng:** giữ nguyên khung ARM/ratchet/gap hiện tại nhưng thay các HẰNG SỐ bằng HÀM của
volatility + regime.
- **Đo gap theo ATR thay vì % tuyệt đối:** `gap = k · ATR_pct(coin)` với ATR ước lượng từ N nến gần
  nhất (dùng `maxPrice/minPrice/close` của `KlineObjectSimple`). Coin vol cao → gap tự nới theo vol,
  coin vol thấp → gap hẹp lại. Cắt whipsaw mà không nhả lãi thừa.
- **Điều tiết theo regime:** dùng `MarketDataObject` (`rateDownAvg`, `rateUpAvg`, `rateDown15MAvg`)
  làm proxy breadth/regime, và `predRisk4H` làm proxy rủi ro. Khi regime rủi ro (breadth xấu /
  `predRisk4H` cao) → giảm `GIVEBACK_RATIO` và hạ trần gap (siết, chốt sớm). Khi trend rộng khỏe
  → nới gap + ratchet nhanh hơn (giảm `TS_PROFIT_MULTIPLIER` hiệu dụng) để cưỡi trend.
- **Input/feature:** ATR_pct coin (N=15–60 nến), `predReturn15M`, `predRisk4H`, 3 rate breadth thị
  trường, tuổi lệnh, mức lãi đỉnh hiện tại (`maePeak` runtime).
- **"Train":** không học — đây là mở rộng bộ gene. Thêm vài hệ số (vd `TS_ATR_MULT`,
  `TS_RISK_SIET`, `TS_REGIME_NOI`) rồi để **HPO/WFO hiện có tối ưu** như các gene khác.
- **Validate (WFO):** dùng đúng khung Walk-Forward đang có (`docs/insights/WFO_FRAMEWORK_DESIGN.md`,
  `WFO_ROADMAP.md`): so A/B **baseline gene tĩnh vs rule thích ứng** trên các out-of-sample window;
  chỉ nhận nếu tốt hơn ổn định qua nhiều window, không chỉ trung bình.
- **Rủi ro:** overfit thấp hơn model học (ít bậc tự do), nhưng vẫn có thể over-tune số window HPO;
  look-ahead gần như 0 vì chỉ dùng feature quá khứ. **Chi phí thấp nhất, an toàn nhất.**

### Hướng (b) — Model học riêng cho trailing (exit model)
Hai cách gán nhãn, chọn 1 (khuyến nghị b1 trước vì gần với vòng lặp hiện tại nhất):

**(b1) Phân loại "tiếp tục tăng vs đảo chiều" (reversal classifier).**
- **Label:** tại mỗi nến khi lệnh ĐANG có lãi & đã arm, gán `y=1` nếu trong H nến tới giá còn tạo
  đỉnh cao hơn trước khi thủng ngưỡng nhả (tức "nên tiếp tục giữ"), `y=0` nếu đảo chiều/sập
  (tức "nên siết/thoát"). H = horizon (vd 15–60 nến). Label tính ex-post offline từ chuỗi giá.
- **Feature (chỉ ≤ t):** lãi đỉnh hiện tại, ATR_pct, momentum ngắn (`predReturn15M`), `predRisk4H`,
  breadth thị trường (3 rate), tuổi lệnh, khoảng cách giá tới SL hiện tại, số lần đã DCA, vị thế
  giá so với entry TB. Không đưa giá tương lai.
- **Dùng ở runtime:** model xuất `p_continue`. Map sang hành động: `p` cao → nới gap (giữ);
  `p` thấp → siết gap / thoát. Đây là bộ ĐIỀU TIẾT gap, không thay khung khớp SL (giữ chống look-ahead).

**(b2) Hồi quy mức trailing tối ưu ex-post (oracle-regression).**
- **Label:** với mỗi lệnh, tính hậu nghiệm mức gap/SL "lý tưởng" tối đa hóa PnL đã chốt trên đường
  giá thực (oracle). Model học ánh xạ feature→gap tối ưu.
- **Rủi ro cao hơn b1:** label oracle rất nhiễu và phụ thuộc mạnh đường giá cá biệt → dễ học pattern
  không tái lập; cần regularize mạnh.

**Train chung cho (b):**
- Sinh dataset từ chính simulator: chạy backtest, ở mỗi tick-của-lệnh-đang-lãi ghi (feature, outcome).
  Tận dụng `WfoDataset` / bin offline đã có (`WFO_STATIC_DATA_DESIGN.md`, `INGEST_FORMAT.md`).
- Model gọn (logistic/GBM/cây nông) export **ONNX** — hạ tầng đã có `AIRejectFilter`/ONNX cho entry,
  tái dụng được cho exit. Tránh model to (ít data độc lập, dễ overfit).
- **Validate (WFO bắt buộc):** train trên IS window, đo trên OOS window kế; **purge + embargo** quanh
  ranh giới để chống rò (đã có `WFO_LEAKS_TODO.md`). So với baseline gene tĩnh trên cùng OOS.
- **Rủi ro overfit/look-ahead:**
  - Look-ahead: nguy cơ lớn nhất ở khâu tính feature (vd ATR/breadth dùng nến chứa tương lai) và ở
    label (đương nhiên nhìn tương lai — phải cô lập khỏi runtime). Kiểm bằng `BacktestIntegrityGuard`
    + đối chứng `BLOCK_INTRABAR_LOOKAHEAD`.
  - Overfit: các "lệnh" từ cùng một cụm/coin/thời điểm KHÔNG độc lập (autocorrelation) → phải split
    theo THỜI GIAN (không random split), giới hạn số feature, ưu tiên model đơn giản.

### Hướng (c) — Tách sleeve exit riêng theo nguồn tín hiệu
- **Ý tưởng:** engine đã phân loại entry theo nguồn (`entryBigDown`, `entryPredictSymbol`,
  `entryDcaLevel` — probe TASK-134) và `marketLevelChange` gắn trên từng cụm. Các nguồn này có bản
  chất khác nhau: `BIG_DOWN`/`DCA_LEVEL1` là mean-reversion bắt đáy (thoát nên chốt nhanh khi hồi);
  `PREDICT_SYMBOL_TRADE` là momentum/funding (thoát nên cưỡi trend lâu hơn).
- **Chiến lược:** cho mỗi sleeve một BỘ THAM SỐ TRAILING RIÊNG (hoặc riêng cả model ở hướng b),
  thay vì một bộ gene chung. Bắt đầu bằng tách 2 sleeve: mean-reversion vs momentum.
- **Input/label/train:** như (a) hoặc (b) nhưng **fit riêng từng sleeve**; hoặc đơn giản là nhân đôi
  bộ gene và để HPO tối ưu độc lập từng nhóm.
- **Validate (WFO):** so 3 kịch bản — (i) gene chung, (ii) 2 bộ gene theo sleeve, (iii) sleeve + rule
  thích ứng. Cẩn thận **chia nhỏ mẫu**: tách sleeve làm mỗi nhóm ít lệnh hơn → phương sai OOS tăng,
  dễ overfit per-sleeve. Cần đủ số lệnh mỗi sleeve mỗi window.
- **Rủi ro:** bùng nổ tham số (mỗi sleeve ×8 gene), giảm cỡ mẫu; nhưng look-ahead thấp và dễ diễn giải.

---

## 4. Khuyến nghị ưu tiên + các bước triển khai nhỏ

### Khuyến nghị: LÀM HƯỚNG (a) TRƯỚC — rule-based thích ứng vol/regime.
Lý do:
- Rủi ro overfit/look-ahead thấp nhất, tái dùng nguyên khung HPO/WFO hiện có (không cần hạ tầng train
  mới, không cần dataset gán nhãn tương lai).
- Đánh trúng 2 điểm yếu nặng nhất: **gap không theo vol** (điểm yếu #1) và **không theo regime/rủi
  ro** (#2, #7) — chỉ cần thêm ATR-scaling + dùng `predRisk4H` đã có sẵn.
- Là bước đệm sạch cho (b): các feature vol/regime xây ở (a) chính là feature đầu vào cho model học
  (b1) sau này. Nếu (a) đã ăn phần lớn cải thiện thì có thể KHÔNG cần model học (tiết kiệm rủi ro).

Thứ tự kế tiếp nếu (a) tới hạn: **(c) tách 2 sleeve** (rẻ, dễ) → rồi mới cân nhắc **(b1) reversal
classifier** (đắt nhất, rủi ro cao nhất, làm sau cùng và chỉ khi có bằng chứng còn dư địa).

### Các bước nhỏ (validate-small-first)
1. **Đo baseline & chẩn đoán (không đổi code logic).** Từ `allOrderDone` + các field đã có
   (`maePeak`, `maeLow`, `priceTP`, `priceEntry`), tính phân phối: "% đỉnh giữ được khi thắng",
   tỉ lệ thoát-non (giá tạo đỉnh cao hơn ngay sau khi thoát), whipsaw. Cắt lát theo coin-vol và theo
   `marketLevelChange`/sleeve. → Xác nhận định lượng điểm yếu #1/#2 trước khi sửa gì.
2. **Thêm ATR-scaling cho gap (1 biến).** Đưa `gap = min(maxProfitRate·GIVEBACK, k·ATR_pct)` sau một
   flag config mặc định TẮT (giữ hành vi cũ), thêm 1 gene `TS_ATR_MULT`. Chạy A/B trên **1–2 WFO
   window nhỏ** trước, không full 5 năm ngay.
3. **Nếu (2) dương → mở rộng regime/risk.** Thêm điều tiết theo `predRisk4H` + breadth
   (`rateDown15MAvg`...). Vẫn qua flag + gene mới, để HPO tối ưu. Đo lại trên WFO đầy đủ.
4. **Gate nhận/loại theo WFO.** Chỉ giữ thay đổi nếu tốt hơn baseline ỔN ĐỊNH qua nhiều OOS window
   (không chỉ mean), maxDD không xấu đi; tuân thủ `BacktestIntegrityGuard` + guard look-ahead.
5. **(Sau, tùy chọn) tách sleeve (c).** Nếu còn dư địa: nhân bộ gene theo 2 sleeve, HPO độc lập.
6. **(Cuối, tùy chọn) model học (b1).** Chỉ làm khi (a)+(c) đã tới hạn: sinh dataset từ simulator,
   train GBM/logistic nhỏ, export ONNX, validate WFO có purge+embargo, so với (a) là baseline mới.

### Nguyên tắc an toàn xuyên suốt
- Mọi thay đổi trailing đặt sau **flag config mặc định = hành vi cũ** (giống cách `HARD_STOP_LOSS_RATE`,
  `TIME_STOP_HOURS`, `TS_GIVEBACK_RATIO` được thêm) → luôn có đường lùi và đo A/B sạch.
- KHÔNG đụng `timeStart` (leg-cuối, tham chiếu logic) — dùng `clusterFirstLegTime` cho các mốc theo
  vòng đời cụm (bài học funding/time-stop trong code).
- Giữ `BLOCK_INTRABAR_LOOKAHEAD=true`; feature volatility/regime chỉ dùng nến ĐÃ đóng ≤ t.
- Validate trên vài window nhỏ trước khi chạy full-history/compute lớn (yêu cầu "validate-small-first").
