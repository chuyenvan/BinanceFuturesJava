package com.binance.chuyennd.ai_ml.wfo;

import com.binance.chuyennd.ai_ml.wfo.entry.WFOTier1EntryRunner;
import com.binance.chuyennd.ai_ml.wfo.dca_trailing.WFOTier2RiskRunner;
import com.binance.chuyennd.ai_ml.wfo.budget.WFOTier3BudgetRunner;
import com.binance.chuyennd.tradecore.BotTradingConfig;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class WFOOrchestrator {
    private static final Logger LOG = LoggerFactory.getLogger(WFOOrchestrator.class);

    public void startProcess(long startTs, long endTs) {
        long isStep = 90 * Utils.TIME_DAY; // IS: 3 tháng huấn luyện
        long oosStep = 30 * Utils.TIME_DAY; // OOS: 1 tháng thực chiến giả định

        long current = startTs;
        BotTradingConfig rollingConfig = new BotTradingConfig();

        while (current + isStep + oosStep <= endTs) {
            long trainEnd = current + isStep;
            long testEnd = trainEnd + oosStep;

            LOG.info("🚀 STARTING WFO WINDOW: Train until {} -> Test until {}",
                    Utils.normalizeDateYYYYMMDD(trainEnd), Utils.normalizeDateYYYYMMDD(testEnd));

            // Chuyền đuốc qua 3 tầng [cite: 317, 318, 322]
            BotTradingConfig bestEntry = WFOTier1EntryRunner.optimize(current, trainEnd, rollingConfig);
            BotTradingConfig bestRisk = WFOTier2RiskRunner.optimize(current, trainEnd, bestEntry);
            BotTradingConfig finalIS = WFOTier3BudgetRunner.optimize(current, trainEnd, bestRisk);

            // Bước chốt: Kiểm chứng OOS [cite: 323]
            float oosScore = WFOBacktestEngine.run(trainEnd, testEnd, finalIS);

            LOG.info("🏁 RESULT OOS [{}]: Score = {}", Utils.normalizeDateYYYYMMDD(testEnd), oosScore);

            // Trượt cửa sổ và dùng tham số mới làm gốc cho kỳ sau
            current += oosStep;
            rollingConfig = finalIS;
        }
    }
}