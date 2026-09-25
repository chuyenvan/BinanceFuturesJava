# DIAG_LIVE_COMPONENTS — AUDIT **ĐƯỜNG LIVE** TỪ CODE: thành phần · nhãn · ngưỡng · lưới

**Ngày:** 2026-09-25 · **Repo:** `/home/ubuntu/src/BinanceFuturesJava` (branch `module`) · **KHÔNG push**.
**Cách làm:** chỉ **đọc code** (đườNG LIVE + SIM) — không train, không sim, không job.
**Bối cảnh:** owner 25/09 11:28 nói live dùng **`retEnd 0,015`** + **lưới 15m** + *"1m chỉ là của big_down"*;
trước đó tôi đã **gộp 2 thành phần live thành 1** và gọi lưới 15m là "live bị 1/15 cơ hội". Tài liệu này
là bản đính chính **có `file:line`**.

Cấu hình đang chạy của instance LIVE/SHADOW: `deploy/shadow_c3/env.sh` (`LIVE_PROFILE=c3_shadow`,
`SHADOW_NO_PUSH=true`, `S1_MODEL_ONNX=/home/ubuntu/s1_model/s1a2x1_cut20251001.onnx`,
`SELECTOR_RANK_TOPK=8`, `SIM_MIN_MOMENTUM_15M=0.008`, `SIM_GATE_DYN_SCALE=1.70`).

---

## 0. BẢNG KẾT LUẬN BẮT BUỘC

| thành phần | NHÃN | NGƯỠNG | LƯỚI | file:line |
|---|---|---|---|---|
| **S1 ranker** (thứ tự xếp hạng pool entry) | `rel5` = **hạng ngũ phân vị trong tick** của `g1lite`; `g1lite = maxFav_72h − min(0,5·maxFav_72h, 0,08)` nếu `maxFav_72h ≥ 0,05`, ngược lại `retEnd_72h` | không (thuần thứ tự; score **THẤP = TỐT**) | mốc entry **15m**; đặc trưng lấy từ close **1h** | `selector/S1RankerLive.java:93,128` · `pipeline/x1/x1_s1_save_model.py:62,80` · `pipeline/x1/x1_ledger.py:7,44` · dùng tại `trading/DetectEntrySignal2TradeNormal.java:347-352` |
| **Thang giá trị gate C3** (`symbolPred`) | **`retEnd_4h > 0,015`** (lớp 1 = P(win) của `g015x26_f15_cut20251001.onnx`), đổi dấu thành `1 − P(win)` | không (là **đầu vào** ngưỡng dyn) | **15m** (bins 4h, mốc 15m) | `selector/Net015ValueLive.java:20,41` · `selector/LiveBuildMap.java:26-35,44` · gán `DetectEntrySignal2TradeNormal.java:395,466` |
| **Thang giá trị gate LEGACY** (`pNoPump`) | **`maxFav_24h ≥ 0,06` & `nBars_24h ≥ 96`** (`Funding_Classifier_Final.onnx`) | không | 15m | `DetectEntrySignal2TradeNormal.java:68` · `ai_ml/validation/Task128ModelQuality.java:34,51` · `selector/EntryPoolGate.java:9-13` |
| **Cổng entry tầng 2 (`EntryGate`)** | **`predReturn15M`** = dự báo **lợi nhuận 15 phút** của model entry (regression; model `ai_predictions.data_v3_FULL`) | `thr = MIN_MOMENTUM_15M × max(0,26787, (symbolPred/0,15)×1,28760) × GATE_DYN_SCALE`; `MIN_MOMENTUM_15M` = 0,02284 (env T170: **0,008**), `GATE_DYN_SCALE` = **1,70**; `symbolPred = null` (BIG_DOWN/DCA/leg market) ⇒ **ngưỡng CƠ SỞ** | **15m** | `tradecore/EntryGate.java:47-53,78-90` · `ai_ml/onnx/entry/AIRejectFilter.java:61-63` · gọi `DetectEntrySignal2TradeNormal.java:767` · hằng số `tradecore/Configs.java:407` |
| **BIG_DOWN** (leg market-signal) | **KHÔNG có nhãn** (luật giá) | `rateDownAvg < MS_DOWN_BIG_AVG` = **−0,03157** (env `SIM_MS_DOWN_BIG_AVG`); `rateDownAvg = calRateChangeAvg(rateDown2Symbols, 100)` | dữ liệu **1m** (rateChange = close/open **nến 1m mới nhất**); điểm quyết định live **15m** | `tradecore/MarketBigChangeDetector.java:174-182` · dựng `rateChange`/`rateDownAvg`: `DetectEntrySignal2TradeNormal.java:167,199-220,226` · `Configs.java:409` |
| **Chọn coin BIG_DOWN** | — (luật) | `BD_SEL_MODE` default **`off`** ⇒ `getTopSymbol` cũ | 15m | `Configs.java:693` · `tradecore/BdSelection.java` |
| **DCA** (`DCA_LEVEL1`) | — (luật) | `rateDown15MAvg < MS_DOWN_BIG_AVG_DCA` **hoặc** `rateDownAvg < MS_DOWN_BIG_AVG_DCA/3` (= −0,03157) | 15m (`rateDown15MAvg` = max của **15 nến 1m**) | `MarketBigChangeDetector.java:186-190` · `Configs.java:107,413` · `DetectEntrySignal2TradeNormal.java:297-330` |
| **PumpDumpFilter** | — (luật) | `SIM_FILTER_D3D4` default **null ⇒ TẮT** | — | `Configs.java:790` · `tradecore/PumpDumpFilter.java:53-54` |
| **Cầu dao / trần tập trung** | — (luật) | density-burst (`BURST_BASE=40`, `DENSITY_ALPHA=0.6`, lookback 4 phút) + `is50PercentOrderLossProd` + `ConcCapLiveGuard` | mỗi lệnh | `MarketBigChangeDetector.java:199-209` · `DetectEntrySignal2TradeNormal.java:798+` |
| **THOÁT** (arm trailing / ratchet / time-stop) | — (luật, không nhãn) | `RATE_PROFIT_STOP_MARKET` = **0,07** (C3) · time-stop **168h** · ratchet liên tục | quản lý **1 giây**/lần (shadow tick **10 giây**) | `selector/LiveProfileC3.java:25-46` · `trading/BinanceOrderTradingManager.java:256-262` |
| **NHỊP VÀO LỆNH (lưới)** | — | `second ∈ [6,10]` **và** `curMin % 15 == 0` | **15m** cho **MỌI** leg | `DetectEntrySignal2TradeNormal.java:988,991-1002` (hardcode; đã bỏ env 2026-09-03) |

---

## 1. CÂU HỎI (i) — LIVE DÙNG `retEnd 0,015` HAY `maxFav`?

**Từng thành phần — KHÁC NHAU, KHÔNG được gộp:**

1. **Thang giá trị gate của C3 (`symbolPred`)**: **`retEnd 0,015`** — `Net015ValueLive.java:20`:
   *"`P(win) = probabilities[:,1]` (lớp 1 = `retEnd_4h > 0.015`)"*; Java đảo dấu `symbolPred = 1 − P(win)`
   (`LiveBuildMap.java:44`). ⇒ **owner đúng**: live (profile C3) đang dùng **`retEnd 0,015`**.
2. **S1 ranker**: **không** dùng `retEnd 0,015`. Nhãn của nó là `rel5` trên `g1lite`, mà
   `g1lite` **pha cả hai họ**: `maxFav_72h` (khi `≥ 0,05`, xấp xỉ trailing) **và** `retEnd_72h` (khi không)
   (`x1_ledger.py:7,44`). ⇒ **thành phần thứ hai, khác** — đây là chỗ tôi đã nói gộp thành `maxFav` và **SAI**.
3. **Thang giá trị LEGACY (`pNoPump` của `Funding_Classifier_Final.onnx`)**: đây **mới** là họ **`maxFav`**
   (`maxFav_24h ≥ 0,06 & nBars_24h ≥ 96`, `Task128ModelQuality.java:34,51`). Nó **chỉ** còn là đường
   dự phòng: bị **bỏ hẳn** khi profile C3 bật (`EntryPoolGate.java:9-13` — *"bo FALLBACK pNoPump"*,
   `DetectEntrySignal2TradeNormal.java:347-366`), và vẫn là chuỗi của **66 vị thế legacy** (`:89-92`).
4. **Cổng entry tầng 2**: nhãn là **`predReturn15M`** (lợi nhuận **15m**, regression) — **không** phải `retEnd_4h`, **không** phải `maxFav`.
5. **BIG_DOWN**: **không có nhãn** (luật giá thuần).

⇒ Trả lời gọn: **live = `retEnd 0,015` ở TẦNG GIÁ TRỊ GATE (C3) + `g1lite` (maxFav_72h ⊗ retEnd_72h) ở TẦNG XẾP HẠNG + `predReturn15M` ở TẦNG CỔNG**; `maxFav` thuần chỉ còn ở nhánh **legacy**.

---

## 2. CÂU HỎI (ii) — LƯỚI VÀO LỆNH LIVE LÀ 15m HAY 1m?

- **15m cho MỌI leg.** `ENTRY_GRID_MIN = 15L` là **hằng số hardcode** (`DetectEntrySignal2TradeNormal.java:988`);
  `isTimeProcessData()` chỉ trả `true` khi `second ∈ [6,10] && curMin % 15 == 0` (`:991-1002`); vòng duy nhất
  gọi nó là `startThreadDetectMarketLevel2Trader` (`:122-140`) → `checkMarketLevelChange2Trade()` (`:144`),
  nơi sinh **cả 4 loại leg**: `PREDICT_SYMBOL_TRADE` (selector, `:411`), `BIG_DOWN` (`:272-291`),
  `DCA_LEVEL1` (`:304,325`). Env đổi nhịp **đã bị gỡ** 2026-09-03 (`:987`).
- **Thành phần nào dùng 1m?** (a) **dữ liệu** nến **1m** để tính `rateChange` mỗi coin
  (`Utils.rateOf2Double(priceClose, priceOpen)` của nến 1m mới nhất — `:167`) và `rateDownAvg`
  trung bình 100 coin rớt mạnh nhất (`:199-220`) ⇒ **BIG_DOWN là thành phần 1m duy nhất**;
  (b) `rateDown15MAvg` dùng `NUMBER_TICKER_CAL_RATE_CHANGE = 15` nến 1m = cửa sổ 15m (`Configs.java:107`).
  **KHÔNG** có đường BIG_DOWN riêng chạy mỗi 1m ở live: BIG_DOWN live bị **lấy mẫu ở 15m**.
- ⇒ Câu owner nói *"1m chỉ là của big_down"* đúng ở nghĩa **độ phân giải dữ liệu / phía SIM** (xem §3),
  **không** đúng ở nghĩa "live có lưới 1m cho big_down" (đọc code: **không có**).

---

## 3. CÂU HỎI PHỤ — SIM CHẠY LƯỚI NÀO, VÀ KHE SIM ↔ LIVE

- **SIM lặp MỌI nến 1m**: `for (entry : time2Tickers.entrySet())` với `time2Tickers` = 1440 mốc/ngày
  (`research/SimulatorMarketLevelTicker1MStopLoss.java:221,219`).
- **Leg SELECTOR của sim vẫn 15m**: nó chỉ chạy khi `time2SymbolPred.get(time) != null` (`:403`), và
  `time2SymbolPred` là map của **file prediction** (grid canonical 15m = `predwf_map_s1a2_x1`); hàm
  `preprocessFundingData` **chỉ sort**, **KHÔNG** forward-fill ra từng phút (`:1551-1560`) — đối chiếu
  `RESULT_5MGRID.md:16-18` (đổi grid prediction ⇒ đổi số entry, chứng tỏ selector theo grid file).
- **Leg BIG_DOWN / DCA của sim chạy MỖI PHÚT** (`:319-399`: `getMarketStatus1M(marketData...)` theo `time`
  1m) ⇒ **đây chính là "1m của big_down"** (khớp câu owner), nhưng nó nằm ở **SIM**, không ở live.
- **KHE SIM ↔ LIVE (định lượng được / không):**
  1. **BIG_DOWN + DCA + re-entry**: sim có **~15× số điểm quyết định** so với live (1 phút vs 15 phút) —
     đây là khe **có thật, do code**, và **cùng chiều "sim lạc quan hơn"**. Bằng chứng gián tiếp đã có:
     `RESULT_LIVE_VS_SIM.md` §6 — shadow **0/65 leg BIG_DOWN** vs sim **248/1089 leg**; và §1 mục (c)
     shadow vào tối đa 8 lệnh/tick 15m, re-entry ở tick kế.
  2. **Đo trực tiếp khe này cần chạy sim khoá lưới 15m** ⇒ **vòng này CẤM sim** ⇒ **KHÔNG định lượng
     được** ở đây (ghi rõ, không suy đoán). Dấu hiệu gián tiếp **ngược chiều** với "mịn hơn = tốt hơn":
     `RESULT_5MGRID.md` §2 đo 5m (mịn hơn 15m): `win% −2,016pp` và `TSloss% +1,923pp` **ngoài CI**
     (đều theo hướng XẤU) ⇒ lưới mịn hơn **không** miễn phí. Nhưng **không** được suy từ đó ra chiều của
     khe 1m (BIG_DOWN là leg khác cơ chế, và 5M là grid **prediction**, không phải grid **market-signal**).
  3. **Chi phí**: sim trừ 0,008/leg; shadow ghi **GROSS** ⇒ **không** phải "lạc quan hoá lưới" mà là
     khác **mô hình phí** (`RESULT_LIVE_VS_SIM.md` §4).

---

## 4. NHỮNG CHỖ TÔI ĐÃ NÓI SAI (đính chính tường minh)

| # | tôi đã nói | sự thật (code) |
|---|---|---|
| 1 | live dùng 1 model `maxFav` | **2 thành phần khác nhau**: xếp hạng = **S1** (nhãn `g1lite`), giá trị gate = **net015** (`retEnd_4h > 0,015`). `maxFav` thuần chỉ ở nhánh **legacy** `pNoPump` |
| 2 | "live bị 1/15 cơ hội" (do lưới 15m) | **SIM** mới là bên có 15× cơ hội ở leg **BIG_DOWN/DCA** (1m); leg **selector** của sim vẫn **15m** ⇒ không phải "live bị mất 14/15" đồng nhất cho mọi leg |
| 3 | live chạy `retEnd 0,015` | **đúng** cho tầng giá trị gate C3 (owner đúng) — nhưng **thiếu** 2 tầng còn lại: `g1lite` (S1) và `predReturn15M` (cổng) |
