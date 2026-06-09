# AUDIT — Filter ablation (luồng filter + tool đo bỏ nhánh 24H / DD4H)

> File tự chứa để AUDIT đúng/sai logic ablation filter mà KHÔNG cần mở repo.
> Mọi trích dẫn ở Phần 2 là **nguyên văn theo code hiện tại**. Phần 1 mô tả luồng; ⚠️ = điểm cần để ý.
> Bot: futures **long-only, DCA/martingale, KHÔNG hard stop-loss**, thoát bằng trailing khi đã lãi.

---

## PHẦN 1 — ARCHITECTURE (luồng dữ liệu thật)

### 1. Gen market predict
- **Class**: `com.binance.chuyennd.ai_ml.onnx.entry.RunGeneratePredictions` → dùng `OnnxInferenceManager` (3 ONNX regressor: `Model_Regressor_Return15M/Return24H/Drawdown4H` + scaler tương ứng, mỗi model nạp 33 feature `extractFeaturesV3Full`).
- **Ra**: `AiPredictionData{ timestamp, predReturn15M, predReturn24H, predRisk4H }` (predRisk4H = maxDrawdown 4H dự báo, **signed âm**).
- **Lưu**: `DataManagerAerospikeFloatSim.saveMarketAiPredictionsBatch` → set Aerospike **`ai_pred_market_full_basket_v2`** (client **226**), key = `yyyyMMdd-HHmm` (GMT+7), giá trị = JSON(AiPredictionData) → Snappy → bin `"data"`.
- **Đọc lúc backtest**: `getAllMarketAiPredictionsFromAerospike()` → `TreeMap<Long, AiPredictionData>` (key = `data.timestamp` trong JSON, không phải key Aerospike).

### 2. Gen funding predict
- **Class**: `com.binance.chuyennd.ai_ml.onnx.funding.GenerateFundingPredictionsTool` → dùng `FundingOnnxInferenceManager` (ONNX **classifier 5 lớp** `multi:softprob`, 21 feature, KHÔNG có momentum1M). Nhãn label6: **0=fail(không chạm +6%), 1=72H, 2=24H, 3=4H, 4=15M**.
- **Ra**: mỗi symbol 1 vector `float[5]` = `[P(class0)..P(class4)]`.
- **Lưu**: `saveFundingPredictions1M(time, Map<Short,float[5]>)` → set **`Configs.AEROSPIKE_SET_NAME_FUNDING_PRED`** (config.properties = `funding_pred_1m_v5`, client **226**), key = `yyyyMMdd-HHmm` (GMT+7). Encode bằng `encodeFundingMapToBinary` → **lưu TOÀN BỘ vector 5 float** mỗi symbol → Snappy → bin `"data"`.

### 3. Decode funding lúc đọc (⚠️ trọng yếu)
- `decodeFundingMapToPrimitiveArray(bytes)` đọc mỗi record nhưng **CHỈ lấy `pred[0]`** (float đầu tiên), bỏ qua 4 float còn lại; pack thành `long`: `(symbolId << 32) | floatBits(pred[0])`. → `getAllFundingPredictionsPrimitiveFromAerospike()` trả `TreeMap<Long, long[]>`.
- ⇒ **`symbolPred` = `pred[0]` = `P(class0)` = "P-FAIL"** (xác suất coin KHÔNG chạm +6% theo model funding label6). **Cao = xấu** (khả năng fail lớn).
- Hệ quả: dù trên đĩa lưu đủ 5 lớp, **toàn hệ chỉ dùng P-fail**. 4 lớp còn lại hiện không được dùng ở bước filter/sim.

### 4. Filter — `AIRejectFilter`
- `checkSignal(prediction)` → **ngưỡng CỨNG** (`MIN_MOMENTUM_15M`, `MIN_MOMENTUM_24H`, `HARD_RISK_LIMIT_4H`). Là fallback.
- `checkSignalDynamic(prediction, symbolPred)` → ngưỡng **ĐỘNG**:
  - `symbolPred == null` → fallback `checkSignal`.
  - **Nhánh EARLY**: `if (predReturn15M < MIN_MOMENTUM_15M && symbolPred > PREDICT_SYMBOL_RATE_MAX_THRESHOLD) → REJECT`. (= 15M yếu **và** P-fail cao). EARLY là 15M+funding, **độc lập** với `evaluate`.
  - `scale = clamp((symbolPred/PREDICT_SYMBOL_RATE_MAX_THRESHOLD) * AI_DYNAMIC_MULTIPLIER, AI_DYNAMIC_MIN, AI_DYNAMIC_MAX)`; `dyn15=MIN_MOMENTUM_15M*scale; dyn24=MIN_MOMENTUM_24H*scale; dynRisk=HARD_RISK_LIMIT_4H/scale` → gọi `evaluate(...)`.
- `evaluate(...)` có **3 nhánh REJECT** theo thứ tự: **RISK** (`risk4H <= thresRisk`) → **MOM15** (`pred15M < thres15M`) → **MOM24** (`pred24H < thres24H`); không nhánh nào reject → PASS.
- **Ablation (đã cắm)**: trong `evaluate`, `FILTER_MODE` bọc 2 nhánh: `checkRisk = !(B|D)`, `checkMom24 = !(C|D)`; **MOM15 luôn giữ**. Vì cả `checkSignal` và `checkSignalDynamic` đều gọi `evaluate`, **FILTER_MODE áp cho CẢ HAI** (✅ không lệch). Nhánh EARLY **không bị FILTER_MODE đụng** (nằm ngoài `evaluate`) → giữ ở mọi mode.

### 5. Simulator backtest — `SimulatorMarketLevelTicker1MStopLoss`
- `initDataReady(time2MarketData, predictionMap, time2FundingPre, aiRejectFilter)`: gán data, `time2SymbolPred = time2FundingPre`, `preprocessFundingData` (sort mảng theo `pred[0]` tăng dần), gán filter, reset Budget, `allOrderDone = new TreeMap<>()`.
- `simulatorWithInitEntry(startTime, endTime)`: **dòng đầu gọi `BacktestIntegrityGuard.assertProductionGrade()`** (✅ guard cắm tại nút chặn duy nhất). Đọc ticker theo ngày: `IS_KAGGLE_MODE ? KaggleDataLoader.loadDailyTickersShort : DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey` (tool ablation để `IS_KAGGLE_MODE=false` → Aerospike). Mỗi phút: cập nhật history + update lệnh đang chạy + (nếu có `levelChange`) tạo lệnh.
- **Gọi filter**: trong `createOrderBUY(...)`:
  - ⚠️ **Bỏ qua filter hoàn toàn nếu `levelChange == BIG_DOWN`** (`!levelChange.equals(BIG_DOWN)`), khớp cạm bẫy đã biết "sim bỏ qua AI trong BIG_DOWN".
  - `levelChange == PREDICT_SYMBOL_TRADE` → `checkSignalDynamic(predict, symbolPred)` (có EARLY + động). Các entry khác (SMALL_UP/DOWN, DCA_LEVEL1...) truyền `symbolPred=null` → `checkSignal` (cứng). ⇒ **EARLY chỉ kích hoạt cho entry PREDICT_SYMBOL_TRADE.**
  - `symbolPred` lấy từ vòng quét `time2SymbolPred.get(time)` (đã sort tăng theo P-fail; `if (symbolPred > maxThres) break` để cắt sớm).

### 6. Budget / PnL
- `OrderTargetInfoTest.calTp()` = **PnL thực hiện của cụm lệnh khi đóng** (`priceTP` là giá đóng của cụm đã merge). Đã trừ: **phí sàn** `qty*entry*RATE_FEE` (RATE_FEE=0.002, comment ghi "đã sửa thành 2 chân" → mô hình hoá phí 2 chân gộp 1 lần), **slippage 2 chân** `qty*entry*SLIPPAGE_RATE*2` (khi `APPLY_SLIPPAGE`), và `calFundingFee()`. ⚠️ Funding fee: `updateFundingFee()` đang **comment toàn bộ** → `calFundingFee()` thực tế ≈ 0 (kiểm lại nếu cần).
- `BudgetManagerSimple` (ThreadLocal/instance): `balanceBasic`=vốn khởi tạo (`CAPITAL_START`), `marginRunning`=margin đang dùng, `profit`=lãi đã chốt, `balanceIndex`=chỉ số danh mục. `resetInstance()` xoá instance ThreadLocal (mỗi mode reset).
- `BalanceIndex`: **`unProfitMin`** = min theo thời gian của TỔNG unrealized P&L danh mục = **maxDrawdown danh mục thật** (không phải 1 lệnh, không phải 1 thời điểm rời rạc). **`date2MarginMax`** = Map ngày→margin lớn nhất trong ngày (⚠️ **granularity NGÀY**, không phải phút).
- **"Vùng bóp vốn 2"**: trong `TradeUtils.managerBudget`, khi `marginRunning/balanceBasic >= BUDGET_MARGIN_RATIO_2` (0.7475) thì `budget /= BUDGET_DIVIDER_2`. Tool ablation đếm **số NGÀY** có `date2MarginMax/balanceBasic >= BUDGET_MARGIN_RATIO_2` (proxy gần-cháy, đọc state sẵn — không sửa core).

---

## PHẦN 2 — CODE NGUYÊN VĂN

### `src/main/java/com/binance/chuyennd/tradecore/Configs.java` (trích: hằng filter + budget + FILTER_MODE)
```java
    // 4. QUẢN TRỊ VỐN TỰ ĐỘNG (BUDGET MANAGEMENT)
    public static Integer number_order_budget = 50; // Tổng số phần chia vốn
    // Ngưỡng bóp vốn 1 & 2
    public static float BUDGET_MARGIN_RATIO_1 = 0.4820f;
    public static float BUDGET_DIVIDER_1 = 1.5578f;
    public static float BUDGET_MARGIN_RATIO_2 = 0.7475f;
    public static float BUDGET_DIVIDER_2 = 1.5984f;

    // 7. AI & BỘ LỌC TÍN HIỆU ĐỘNG (AI DYNAMIC FILTER - HPO UPDATE)
    public static float AI_DYNAMIC_MULTIPLIER = 1.28760f; // Cũ: 1.40234f
    public static float AI_DYNAMIC_MIN = 0.26787f;        // Cũ: 0.14568f
    public static float AI_DYNAMIC_MAX = 2.14135f;        // Cũ: 2.24405f

    public static float PREDICT_SYMBOL_RATE_DOWN_15M = -0.03234f;
    public static float PREDICT_SYMBOL_RATE_UP_AVG = 0.00454f;
    public static float PREDICT_SYMBOL_RATE_DOWN_AVG = -0.00503f;

    public static float PREDICT_SYMBOL_RATE_MAX_THRESHOLD = 0.19727f; // Cũ: 0.15f (Log map: PREDICT_MAX_THRES)
    public static float HARD_RISK_LIMIT_4H = -0.09200f;               // Cũ: -0.2f
    public static float MIN_MOMENTUM_15M = 0.01720f;                  // Cũ: 0.02284f
    public static float MIN_MOMENTUM_24H = 0.02129f;                  // Cũ: 0.01682f

    // === ABLATION FILTER (chỉ phục vụ ĐO, mặc định "A" = hiện trạng, KHÔNG ảnh hưởng CONFIG_VERSION) ===
    // A=full (3 nhánh RISK/MOM15/MOM24)  B=bỏ nhánh RISK(DD4H)  C=bỏ nhánh MOM24
    // D=bỏ cả RISK+MOM24 (chỉ còn MOM15 + nhánh EARLY 15M+funding).
    // Nhánh EARLY trong checkSignalDynamic GIỮ NGUYÊN ở mọi mode.
    public static String FILTER_MODE = "A";
```
> ⚠️ Lưu ý đọc: các hằng đang là **bộ HPO** (comment "Cũ:" là giá trị gốc). Ablation dùng đúng bộ hiện tại → mode A = hành vi live hiện tại.
> ⚠️ Slippage/look-ahead (kiểm bởi guard): `SLIPPAGE_RATE=0.0005f`, `APPLY_SLIPPAGE=true`, `BLOCK_INTRABAR_LOOKAHEAD=true`, `RATE_FEE=0.002f` (khai báo ở section khác của Configs).

### `src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/AIRejectFilter.java` (TOÀN BỘ)
```java
package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.Configs;

public class AIRejectFilter {
    public enum FilterDecision {PASS, REJECT}

    public static class FilterResult {
        public FilterDecision decision;
        public String reason;

        public FilterResult(FilterDecision decision, String reason) {
            this.decision = decision;
            this.reason = reason;
        }
    }


    public FilterResult checkSignal(AiPredictionData prediction) {
        return evaluate(prediction.predReturn15M, prediction.predReturn24H, prediction.predRisk4H,
                Configs.MIN_MOMENTUM_15M, Configs.MIN_MOMENTUM_24H, Configs.HARD_RISK_LIMIT_4H);
    }

    // ==============================================================
    // LUỒNG 2: DÙNG RIÊNG CHO PREDICT_SYMBOL_TRADE (ĐỘNG)
    // ==============================================================
    public FilterResult checkSignalDynamic(AiPredictionData prediction, Float symbolPred) {
        if (symbolPred == null) {
            return checkSignal(prediction); // Fallback về cứng nếu lỗi
        }

        if (prediction.predReturn15M < Configs.MIN_MOMENTUM_15M && symbolPred > Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("DANGER: pred 15m %.2f%% thap (Min %.2f%%)", prediction.predReturn15M * 100, Configs.MIN_MOMENTUM_15M * 100));
        }
        // Lấy baseline
        float baselineProb = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD;

        // 🔥 LOGIC MỚI: Tính toán dựa trên Configs
        float scaleFactor = (symbolPred / baselineProb) * Configs.AI_DYNAMIC_MULTIPLIER;

        // Chặn Trần/Sàn bằng Configs
        scaleFactor = Math.max(Configs.AI_DYNAMIC_MIN, Math.min(scaleFactor, Configs.AI_DYNAMIC_MAX));

        float dynamic_15M = Configs.MIN_MOMENTUM_15M * scaleFactor;
        float dynamic_24H = Configs.MIN_MOMENTUM_24H * scaleFactor;
        float dynamic_Risk4H = Configs.HARD_RISK_LIMIT_4H / scaleFactor;

        return evaluate(prediction.predReturn15M, prediction.predReturn24H, prediction.predRisk4H,
                dynamic_15M, dynamic_24H, dynamic_Risk4H);
    }

    // 🔥 HÀM MỚI: Chỉ nhận 3 tham số
    public void setConfig(float risk, float min15m, float min24h) {
        Configs.HARD_RISK_LIMIT_4H = risk;
        Configs.MIN_MOMENTUM_15M = min15m;
        Configs.MIN_MOMENTUM_24H = min24h;
    }

    /**
     * LOGIC ĐÁNH GIÁ LÕI
     */
    private FilterResult evaluate(float pred15M, float pred24H, float risk4H,
                                  float thres15M, float thres24H, float thresRisk) {

        // ABLATION: bọc nhánh RISK & MOM24 theo FILTER_MODE (chỉ để đo; A=hiện trạng giữ cả 3).
        // B,D bỏ RISK; C,D bỏ MOM24. MOM15 luôn giữ. EARLY (checkSignalDynamic) không đụng tới đây.
        String mode = Configs.FILTER_MODE;
        boolean checkRisk = !("B".equals(mode) || "D".equals(mode));
        boolean checkMom24 = !("C".equals(mode) || "D".equals(mode));

        if (checkRisk && risk4H <= thresRisk) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("DANGER: MaxDD 4H %.2f%% quá cao (Limit %.2f%%)", risk4H * 100, thresRisk * 100));
        }
        if (pred15M < thres15M) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("BAD MOMENTUM: 15M chưa nảy mạnh (%.2f%% < %.2f%%)", pred15M * 100, thres15M * 100));
        }
        if (checkMom24 && pred24H < thres24H) {
            return new FilterResult(FilterDecision.REJECT,
                    String.format("MACRO DUMP: 24H quá xấu (%.2f%% < %.2f%%)", pred24H * 100, thres24H * 100));
        }

        return new FilterResult(FilterDecision.PASS,
                String.format("PERFECT: 15M(%.2f%%) | 24H(%.2f%%) | DD4H(%.2f%%)", pred15M * 100, pred24H * 100, risk4H * 100));
    }
}
```

### `src/main/java/com/binance/chuyennd/ai_ml/validation/RunFilterAblation.java` (TOÀN BỘ)
```java
package com.binance.chuyennd.ai_ml.validation;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.TreeMap;

public class RunFilterAblation {

    private static final Logger LOG = LoggerFactory.getLogger(RunFilterAblation.class);

    // ⚙️ Giai đoạn đo — CHỈNH để phủ rộng đuôi (càng dài càng dễ gặp cú sập hiếm).
    private static final String START_DATE = "20251001";
    private static final String END_DATE = "20260430";

    private static final String[] MODES = {"A", "B", "C", "D"};

    public static void main(String[] args) {
        try {
            new RunFilterAblation().run();
        } catch (Exception e) {
            LOG.error("Ablation error", e);
        }
    }

    public void run() throws Exception {
        // Cấu hình chạy thuần, nguồn Aerospike (không Kaggle file). KHÔNG đụng tham số tuning nào.
        Configs.IS_HPO_MODE = false;
        Configs.IS_KAGGLE_MODE = false;
        Configs.TIME_RUN = START_DATE;

        // ----- PRE-FLIGHT: xác nhận cấu hình KHÔNG ảo (guard sẽ throw nếu sai, nhưng log sớm cho rõ) -----
        LOG.info("🔒 INTEGRITY PRE-FLIGHT: BLOCK_INTRABAR_LOOKAHEAD={} APPLY_SLIPPAGE={} SLIPPAGE_RATE={} RATE_FEE={}",
                Configs.BLOCK_INTRABAR_LOOKAHEAD, Configs.APPLY_SLIPPAGE, Configs.SLIPPAGE_RATE, Configs.RATE_FEE);
        if (!Configs.BLOCK_INTRABAR_LOOKAHEAD || !Configs.APPLY_SLIPPAGE || Configs.RATE_FEE <= 0f) {
            LOG.error("⛔ Cấu hình ảo (look-ahead/slippage/fee tắt) — DỪNG. So sánh ablation sẽ vô nghĩa.");
            return;
        }

        long startTime = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR;
        long endTime = Utils.sdfFile.parse(END_DATE).getTime() + (24 * Utils.TIME_HOUR) - Utils.TIME_MINUTE;

        // ----- LOAD DATA MỘT LẦN, dùng chung cho cả 4 mode (read-only) -----
        SimpleSymbolMapper.getInstance().init();
        LOG.info("📥 Nạp data từ Aerospike (market / AI-pred / funding-pred)...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        TreeMap<Long, AiPredictionData> predictionMap = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospike();
        TreeMap<Long, long[]> time2FundingPre = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        LOG.info("✅ market={} pred={} funding={} | giai đoạn {} -> {}",
                time2MarketData.size(), predictionMap.size(), time2FundingPre.size(), START_DATE, END_DATE);
        if (time2FundingPre.isEmpty()) {
            LOG.warn("⚠️ funding-pred RỖNG -> symbolPred null hàng loạt -> nhánh EARLY mất tác dụng, lệch live. Kiểm tra Aerospike trước khi tin kết quả.");
        }

        List<Row> rows = new ArrayList<>();
        for (String mode : MODES) {
            Configs.FILTER_MODE = mode;   // KHÁC BIỆT DUY NHẤT giữa 4 run
            LOG.info("\n================= ▶️ CHẠY MODE {} (FILTER_MODE={}) =================", mode, mode);

            // reset y hệt BackTestEngineMaster.run để mỗi mode bắt đầu sạch
            BudgetManagerSimple.resetInstance();
            HistoryManager.getInstance().resetCache();
            CoinRankManager.getInstance().resetCache();

            SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
            AIRejectFilter filter = new AIRejectFilter();   // KHÔNG setConfig -> dùng đúng Configs hiện trạng
            sim.initDataReady(time2MarketData, predictionMap, time2FundingPre, filter);
            sim.simulatorWithInitEntry(startTime, endTime);  // guard liêm chính chạy ở đây

            rows.add(computeMetrics(mode, sim));
        }

        printTable(rows);
    }

    // ====================== METRIC (đúng cho martingale, KHÔNG dùng win-rate) ======================
    private Row computeMetrics(String mode, SimulatorMarketLevelTicker1MStopLoss sim) {
        Row r = new Row();
        r.mode = mode;

        double sumWin = 0, sumLossAbs = 0;
        int nWin = 0, nLoss = 0;
        float worst = 0f;
        if (sim.allOrderDone != null) {
            for (OrderTargetInfoTest o : sim.allOrderDone.values()) {
                float pnl = o.calTp();           // P&L thực hiện của lệnh/cụm khi đóng
                r.totalPnl += pnl;
                if (pnl >= 0) { sumWin += pnl; nWin++; }
                else { sumLossAbs += -pnl; nLoss++; }
                if (pnl < worst) worst = pnl;    // lỗ nặng nhất (âm nhất)
            }
            r.tradeCount = sim.allOrderDone.size();
        }
        r.worstSingleLoss = worst;
        r.profitFactor = (sumLossAbs > 0) ? (float) (sumWin / sumLossAbs) : (sumWin > 0 ? Float.POSITIVE_INFINITY : 0f);
        float avgWin = nWin > 0 ? (float) (sumWin / nWin) : 0f;
        float avgLoss = nLoss > 0 ? (float) (sumLossAbs / nLoss) : 0f;
        r.payoffRatio = (avgLoss > 0) ? avgWin / avgLoss : (avgWin > 0 ? Float.POSITIVE_INFINITY : 0f);

        // maxDrawdown danh mục + đếm ngày chạm "vùng bóp vốn 2" (margin/vốn >= BUDGET_MARGIN_RATIO_2)
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        r.maxDrawdown = (bm.balanceIndex.unProfitMin != null) ? bm.balanceIndex.unProfitMin : 0f;
        float capital = (bm.balanceBasic != null && bm.balanceBasic > 0) ? bm.balanceBasic : 1f;
        int nearLiq = 0;
        float maxRatio = 0f;
        for (Float marginMax : bm.balanceIndex.date2MarginMax.values()) {
            if (marginMax == null) continue;
            float ratio = marginMax / capital;
            if (ratio > maxRatio) maxRatio = ratio;
            if (ratio >= Configs.BUDGET_MARGIN_RATIO_2) nearLiq++;
        }
        r.nearLiqDays = nearLiq;
        r.maxMarginRatio = maxRatio;
        return r;
    }

    private void printTable(List<Row> rows) {
        LOG.info("\n\n================= 📊 BẢNG ABLATION FILTER ({} -> {}) =================", START_DATE, END_DATE);
        LOG.info("Bóp vốn 2 = số NGÀY có margin-max/vốn >= BUDGET_MARGIN_RATIO_2 ({}). Trọng tâm: maxDD + worstLoss + nearLiq2.",
                Configs.BUDGET_MARGIN_RATIO_2);
        LOG.info(String.format(Locale.US, "%-6s %8s %12s %8s %12s %12s %8s %8s %9s",
                "MODE", "trades", "totalPnl", "PF", "maxDD", "worstLoss", "payoff", "nearLiq2", "maxMargR"));
        for (Row r : rows) {
            LOG.info(String.format(Locale.US, "%-6s %8d %12.1f %8s %12.1f %12.1f %8s %8d %9.2f",
                    r.mode, r.tradeCount, r.totalPnl, fmt(r.profitFactor), r.maxDrawdown, r.worstSingleLoss,
                    fmt(r.payoffRatio), r.nearLiqDays, r.maxMarginRatio));
        }
        LOG.info("------------------------------------------------------------------------------------------");
        LOG.info("CÁCH ĐỌC: D≈A ở (maxDD, worstLoss, nearLiq2) => bỏ 24H+DD4H AN TOÀN, đơn giản hoá filter.");
        LOG.info("          D xấu hơn A rõ ở đuôi => GIỮ (đã có số chứng minh). So B vs C để biết nhánh nào đáng giữ.");
        LOG.info("          ⚠️ totalPnl cao hơn KHÔNG có nghĩa tốt hơn — bỏ lá chắn thường tăng PnL mà xấu đuôi.");
    }

    private static String fmt(float v) {
        if (Float.isInfinite(v)) return "INF";
        return String.format(Locale.US, "%.2f", v);
    }

    private static class Row {
        String mode;
        int tradeCount = 0;
        float totalPnl = 0f;
        float profitFactor = 0f;
        float maxDrawdown = 0f;
        float worstSingleLoss = 0f;
        float payoffRatio = 0f;
        int nearLiqDays = 0;
        float maxMarginRatio = 0f;
    }
}
```

### `src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java` (trích: field + initDataReady + đoạn gọi filter)
```java
public class SimulatorMarketLevelTicker1MStopLoss {
    public static final Logger LOG = LoggerFactory.getLogger(SimulatorMarketLevelTicker1MStopLoss.class);
    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;
    public TreeMap<Long, MarketDataObject> time2MarketData;
    public TreeMap<Long, AiPredictionData> predictionMap;
    public TreeMap<Long, long[]> time2SymbolPred;
    public AIRejectFilter aiRejectFilter;
    public Boolean is50PercentOrderLoss = null;

    // --- ĐẦU simulatorWithInitEntry: guard + nguồn ticker ---
    public void simulatorWithInitEntry(Long startTime, Long endTime) throws ParseException {
        BacktestIntegrityGuard.assertProductionGrade();   // 🔒 nút chặn liêm chính DUY NHẤT
        ...
        while (true) {
            TreeMap<Long, KlineObjectSimple[]> time2Tickers;
            if (Configs.IS_KAGGLE_MODE) {
                time2Tickers = KaggleDataLoader.loadDailyTickersShort(startTime);
            } else {
                time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey(startTime);
            }
            ...
        }
    }

    // --- Vòng quét entry PREDICT_SYMBOL_TRADE: symbolPred = pred[0] đã decode ---
    long[] symbol2Pred = time2SymbolPred.get(time);
    if (symbol2Pred != null) {
        float maxThres = Configs.PREDICT_SYMBOL_RATE_MAX_THRESHOLD * Configs.AI_DYNAMIC_MAX;
        for (long encodedData : symbol2Pred) {
            float symbolPred = Float.intBitsToFloat((int) encodedData);
            if (symbolPred > maxThres) break;                 // mảng đã sort tăng -> cắt sớm
            short targetId = (short) (encodedData >> 32);
            if (!isSymbolRunning(targetId)) {
                KlineObjectSimple ticker = symbol2Ticker[targetId];
                if (Utils.isTickerAvailable(ticker)) {
                    createOrderBUY(targetId, ticker, MarketLevelChange.PREDICT_SYMBOL_TRADE, marketData, symbolPred);
                }
            }
        }
    }

    // --- createOrderBUY: ĐIỂM GỌI FILTER quyết định vào lệnh ---
    public void createOrderBUY(short symbolId, KlineObjectSimple ticker, MarketLevelChange levelChange,
                               MarketDataObject marketData, Float symbolPred) {
        ...
        AiPredictionData predict = predictionMap.get(ticker.startTime);
        if (predict != null && !levelChange.equals(MarketLevelChange.BIG_DOWN)) {   // ⚠️ BIG_DOWN bỏ qua filter
            AIRejectFilter.FilterResult filterResult = null;
            if (levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE) {
                filterResult = aiRejectFilter.checkSignalDynamic(predict, symbolPred);
            }
            if (filterResult == null)
                filterResult = aiRejectFilter.checkSignal(predict);
            if (filterResult.decision == AIRejectFilter.FilterDecision.REJECT) {
                return;
            }
        }
        ...
    }

    // --- initDataReady: nạp data, gán filter, sort funding ---
    public void initDataReady(TreeMap<Long, MarketDataObject> time2MarketData,
                              TreeMap<Long, AiPredictionData> predictionMap, TreeMap<Long, long[]> time2FundingPre,
                              AIRejectFilter aiRejectFilter) throws OrtException {
        BudgetManagerSimple.getInstance().resetInstance();
        allOrderDone = new TreeMap<>();
        SimpleSymbolMapper.getInstance().init();
        this.time2MarketData = time2MarketData;
        this.predictionMap = predictionMap;
        this.time2SymbolPred = time2FundingPre;
        preprocessFundingData(this.time2SymbolPred);   // sort mảng theo pred[0] tăng dần (1 lần)
        this.aiRejectFilter = aiRejectFilter;
    }
}
```

### `src/main/java/com/binance/chuyennd/ai_ml/hpo/BacktestIntegrityGuard.java` (TOÀN BỘ)
```java
package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public final class BacktestIntegrityGuard {

    private static final Logger LOG = LoggerFactory.getLogger(BacktestIntegrityGuard.class);

    private BacktestIntegrityGuard() {}

    /** Gọi ở đầu mỗi backtest thật. Ném lỗi nếu cấu hình không "production-grade". */
    public static void assertProductionGrade() {
        check(false);
    }

    /** Dùng khi cố ý chạy đối chứng look-ahead/slippage. */
    public static void assertProductionGrade(boolean allowDiagnostic) {
        check(allowDiagnostic);
    }

    private static void check(boolean allowDiagnostic) {
        StringBuilder violations = new StringBuilder();

        if (!Configs.BLOCK_INTRABAR_LOOKAHEAD) {
            violations.append("\n  - BLOCK_INTRABAR_LOOKAHEAD=false (đang cho phép look-ahead nội-nến!)");
        }
        if (!Configs.APPLY_SLIPPAGE) {
            violations.append("\n  - APPLY_SLIPPAGE=false (không tính trượt giá!)");
        }
        if (Configs.APPLY_SLIPPAGE && Configs.SLIPPAGE_RATE <= 0f) {
            violations.append("\n  - SLIPPAGE_RATE<=0 (slippage bật nhưng bằng 0!)");
        }
        if (Configs.RATE_FEE <= 0f) {
            violations.append("\n  - RATE_FEE<=0 (không tính phí sàn!)");
        }

        if (violations.length() == 0) {
            return; // sạch
        }

        String msg = "⛔ BACKTEST INTEGRITY VIOLATION:" + violations
                + "\n  => Kết quả sẽ LẠC QUAN GIẢ. Sửa cấu hình hoặc dùng chế độ diagnostic.";

        if (allowDiagnostic) {
            LOG.warn("⚠️⚠️⚠️ DIAGNOSTIC MODE — guard đang bị nới lỏng CÓ CHỦ Ý: {}", msg);
        } else {
            throw new IllegalStateException(msg);
        }
    }
}
```

### `src/main/java/com/binance/chuyennd/research/OrderTargetInfoTest.java` — `calTp()` (NGUYÊN VĂN)
```java
    public Float calTp() {
        OrderTargetInfoTest orderInfo = this;
        if (orderInfo.priceTP == null) {
            return 0f;
        }
        Float tp = orderInfo.quantity * (orderInfo.priceTP - orderInfo.priceEntry)
                - orderInfo.quantity * orderInfo.priceEntry * Configs.RATE_FEE;
        if (orderInfo.side.equals(OrderSide.SELL)) {
            tp = orderInfo.quantity * (orderInfo.priceEntry - orderInfo.priceTP)
                    - orderInfo.quantity * orderInfo.priceEntry * Configs.RATE_FEE;
        }

        // 🔥 SLIPPAGE 2 chân
        if (Configs.APPLY_SLIPPAGE) {
            float slip = orderInfo.quantity * orderInfo.priceEntry * Configs.SLIPPAGE_RATE * 2f;
            tp = tp - slip;
        }

        tp = tp - calFundingFee();
        return tp;
    }
```
> ⚠️ `updateFundingFee()` đang **comment toàn bộ** (xem cùng file) → `calFundingFee()` thực tế trả ~0 → funding fee CHƯA được tính trong PnL backtest.

### `src/main/java/com/binance/chuyennd/research/BudgetManagerSimple.java` (trích: field + reset + getInstance)
```java
    public BalanceIndex balanceIndex = new BalanceIndex();
    public Float BUDGET_PER_ORDER;
    public Float marginRunning = 0f;
    public Float profit = 0f;
    public Float balanceBasic = Configs.getDouble("CAPITAL_START");
    public Float balanceCurrent = balanceBasic;

    private static final ThreadLocal<BudgetManagerSimple> threadLocalInstance = ThreadLocal.withInitial(BudgetManagerSimple::new);
    public static BudgetManagerSimple getInstance() { return threadLocalInstance.get(); }
    public static void resetInstance() { threadLocalInstance.remove(); }
```
### `src/main/java/com/binance/chuyennd/research/BalanceIndex.java` (trích: field tool ablation đọc)
```java
    public Float unProfitMin;                                  // min theo thời gian của TỔNG unrealized P&L danh mục = maxDrawdown danh mục
    public Map<Long, Float> date2MarginMax = new HashMap<>();  // key = ngày (Utils.getDate), value = margin lớn nhất TRONG NGÀY đó
    // updateIndex(...): date2MarginMax.put(getDate(t), max(cũ, positionMargin)); unProfitMin = min(unProfitMin, unrealizedProfitMin)
```
### `src/main/java/com/binance/chuyennd/tradecore/TradeUtils.java` (trích: nơi "bóp vốn 2" kích hoạt)
```java
        float marginRatio = marginRunning / balanceBasic;
        if (isNormalLevel && marginRatio >= Configs.BUDGET_MARGIN_RATIO_1) {
            budget /= Configs.BUDGET_DIVIDER_1;
        }
        if (marginRatio >= Configs.BUDGET_MARGIN_RATIO_2) {     // <-- "vùng bóp vốn 2" (gần cháy)
            budget /= Configs.BUDGET_DIVIDER_2;
        }
```

### `DataManagerAerospikeFloatSim.java` — funding pred: save / encode / decode / loadAll (NGUYÊN VĂN)
```java
    public static void saveFundingPredictions1M(long timestamp, Map<Short, float[]> predictions) {
        if (predictions == null || predictions.isEmpty()) return;
        try {
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            String keyString = fmt.format(new Date(timestamp));
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, AEROSPIKE_SET_NAME_FUNDING_PRED, keyString);
            // 🔥 THAY ĐỔI: Dùng Binary Codec thay cho JSON
            byte[] rawBytes = encodeFundingMapToBinary(predictions);
            byte[] compressed = Snappy.compress(rawBytes);
            getClient226().put(writePolicy, key, new Bin("data", compressed));
        } catch (Exception e) {
            LOG.error("❌ Error saving Funding Pred at {}: {}", timestamp, e.getMessage());
        }
    }

    public static byte[] encodeFundingMapToBinary(Map<Short, float[]> map) {
        if (map == null) return new byte[0];
        int size = 4; // 4 bytes lưu số lượng phần tử của Map
        for (float[] arr : map.values()) {
            size += 2; // 2 bytes lưu Key (Short)
            size += 4; // 4 bytes lưu độ dài mảng (Int)
            size += arr.length * 4; // 4 bytes cho mỗi giá trị Float
        }
        java.nio.ByteBuffer buffer = java.nio.ByteBuffer.allocate(size);
        buffer.putInt(map.size()); // Ghi số lượng Entry
        for (Map.Entry<Short, float[]> entry : map.entrySet()) {
            buffer.putShort(entry.getKey()); // Ghi ID (Symbol)
            float[] arr = entry.getValue();
            buffer.putInt(arr.length);       // Ghi số phần tử mảng (LƯU TOÀN BỘ vector)
            for (float v : arr) {
                buffer.putFloat(v);          // Ghi từng giá trị float
            }
        }
        return buffer.array();
    }

    // ⚠️ DECODE CHỈ LẤY pred[0] (P-fail), bỏ phần còn lại của vector 5 lớp
    public static long[] decodeFundingMapToPrimitiveArray(byte[] data) {
        if (data == null || data.length == 0) return new long[0];
        java.nio.ByteBuffer buffer = java.nio.ByteBuffer.wrap(data);
        int mapSize = buffer.getInt(); // Đọc số lượng Entry
        long[] result = new long[mapSize];
        for (int i = 0; i < mapSize; i++) {
            short symbolId = buffer.getShort();     // Đọc ID
            int arrLen = buffer.getInt();           // Đọc độ dài mảng float
            float firstPred = 0f;
            if (arrLen > 0) {
                firstPred = buffer.getFloat();      // Chỉ lấy giá trị pred[0]
            }
            for (int j = 1; j < arrLen; j++) {      // Bỏ qua các float còn lại
                buffer.getFloat();
            }
            // ĐÓNG GÓI: 16 bit đầu là symbolId, 32 bit cuối là bit của float
            long encoded = ((long) symbolId << 32) | (Float.floatToRawIntBits(firstPred) & 0xFFFFFFFFL);
            result[i] = encoded;
        }
        return result;
    }

    public static TreeMap<Long, long[]> getAllFundingPredictionsPrimitiveFromAerospike() {
        java.util.concurrent.ConcurrentSkipListMap<Long, long[]> concurrentResults = new java.util.concurrent.ConcurrentSkipListMap<>();
        try {
            ScanPolicy scanPolicy = new ScanPolicy();
            scanPolicy.concurrentNodes = true;
            getClient226().scanAll(scanPolicy, Configs.AEROSPIKE_NAMESPACE, Configs.AEROSPIKE_SET_NAME_FUNDING_PRED, (key, record) -> {
                try {
                    byte[] compressed = (byte[]) record.getValue("data");
                    if (compressed != null && key.userKey != null) {
                        long timestamp = tlKeyFormat.get().parse(key.userKey.toString()).getTime();
                        byte[] rawBytes = org.xerial.snappy.Snappy.uncompress(compressed);
                        long[] primitives = decodeFundingMapToPrimitiveArray(rawBytes);
                        concurrentResults.put(timestamp, primitives);
                    }
                } catch (Exception e) { /* Bỏ qua record lỗi */ }
            }, "data");
        } catch (Exception e) {
            LOG.error("❌ Lỗi khi Scan Funding Pred", e);
        }
        return new TreeMap<>(concurrentResults);
    }
```
> Set funding pred: `Configs.AEROSPIKE_SET_NAME_FUNDING_PRED` = `funding_pred_1m_v5` (config.properties), client 226, key `yyyyMMdd-HHmm` (GMT+7).
> Market AI pred: set `ai_pred_market_full_basket_v2`, `saveMarketAiPredictionsBatch` (JSON+Snappy), `getAllMarketAiPredictionsFromAerospike` (key = `data.timestamp`).

---

## PHẦN 3 — CÂU HỎI TỰ KIỂM (trả lời từ code Phần 2)

1. **FILTER_MODE áp vào CẢ `checkSignal` lẫn `checkSignalDynamic` chưa?**
   → ✅ CÓ. Cả hai đều gọi `evaluate(...)`, và FILTER_MODE nằm TRONG `evaluate` → áp cho cả 2 luồng.

2. **Mode B/C/D bỏ ĐÚNG nhánh và GIỮ EARLY không?**
   → ✅ `checkRisk=!(B|D)` (B,D bỏ RISK), `checkMom24=!(C|D)` (C,D bỏ MOM24), MOM15 luôn chạy. EARLY nằm trong `checkSignalDynamic` TRƯỚC `evaluate` → KHÔNG bị FILTER_MODE đụng → giữ mọi mode.

3. **`simulatorWithInitEntry` có gọi `BacktestIntegrityGuard` không?**
   → ✅ CÓ, là **dòng đầu tiên** của hàm (`assertProductionGrade()`). Tool có thêm pre-flight log ngoài nhưng guard thật nằm trong sim → mọi mode đều qua.

4. **`calTp()` đã trừ fee 2 chân + slippage chưa?**
   → ✅ Fee: `qty*entry*RATE_FEE` (RATE_FEE=0.002, mô hình "2 chân gộp"). Slippage: `qty*entry*SLIPPAGE_RATE*2` khi APPLY_SLIPPAGE. ⚠️ **Funding fee CHƯA tính** (`updateFundingFee` comment hết → `calFundingFee()`≈0). Không lệch giữa các mode (đều thiếu như nhau) nhưng PnL tuyệt đối hơi lạc quan.

5. **4 mode dùng CHUNG data + reset sạch giữa run?**
   → ✅ Data load 1 lần ngoài vòng lặp (read-only). Mỗi mode: `BudgetManagerSimple.resetInstance()` + `HistoryManager.resetCache()` + `CoinRankManager.resetCache()` + `new Simulator` + `new AIRejectFilter`. KHÔNG override tham số tuning. Khác biệt duy nhất = `FILTER_MODE`.

6. **`date2MarginMax` đo theo NGÀY hay PHÚT? "nearLiq2" đếm gì?**
   → ⚠️ Theo **NGÀY** (key = `Utils.getDate`). `nearLiq2` = **số NGÀY** có margin-max/vốn ≥ BUDGET_MARGIN_RATIO_2 (0.7475). KHÔNG phải số phút/số lần chạm trong ngày → đọc như "số ngày nguy hiểm", không phải tần suất tick.

7. **`unProfitMin` là drawdown danh mục thật hay 1 thời điểm?**
   → ✅ Drawdown **danh mục thật**: min theo thời gian của TỔNG unrealized P&L toàn bộ lệnh đang chạy (cập nhật mỗi lần `updateBalance` → `balanceIndex.updateIndex`), không phải 1 lệnh đơn, không phải snapshot rời rạc.

---

### Phụ chú audit (điểm dễ sai khi đọc kết quả)
- EARLY **chỉ kích hoạt cho entry `PREDICT_SYMBOL_TRADE`**; entry theo market-level/DCA dùng `checkSignal` (cứng) — nên mode D vẫn còn EARLY cho nhánh PREDICT_SYMBOL_TRADE nhưng các entry khác chỉ còn MOM15 cứng.
- ⚠️ Khi `levelChange == BIG_DOWN`, filter **bị bỏ qua hoàn toàn** ở mọi mode → ablation không tác động lúc BIG_DOWN.
- `symbolPred` (P-fail) càng cao → `scale` càng lớn → ngưỡng 15M/24H càng cao, ngưỡng risk (số âm) càng gần 0 → **lọc càng gắt**. Mảng funding sort tăng theo P-fail + `break` khi `> MAX_THRESHOLD*AI_DYNAMIC_MAX`.
- Trọng tâm kết luận: **maxDD (`unProfitMin`) + worstLoss + nearLiq2**, KHÔNG phải totalPnl/PF (bỏ lá chắn thường tăng PnL mà xấu đuôi).
```
