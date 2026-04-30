package com.binance.chuyennd.trading.monitor;

import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.trading.BudgetManager;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.trade.Asset;
import com.binance.client.model.trade.PositionRisk;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class Reporter {
    public static final Logger LOG = LoggerFactory.getLogger(Reporter.class);

    public static void main(String[] args) {
        Reporter.buildReport();
    }

    public static void buildReport() {
        try {
            // check is last time market < 15m thi reset
            String timeLastCheck = RedisHelper.getInstance().get().get(RedisConst.REDIS_KEY_LAST_TIME_CHECK_MARKET);
            if (StringUtils.isNotEmpty(timeLastCheck)){
                long time = Long.parseLong(timeLastCheck);
                if (System.currentTimeMillis() - time > 15 * Utils.TIME_MINUTE){
                    Utils.reset("Reset by last check market over 15m: " + Utils.normalizeDateYYYYMMDDHHmm(time));
                }
            }
            Set<PositionRisk> positions = new HashSet<>();
            positions.addAll(BudgetManager.getInstance().symbol2Pos.values());
            StringBuilder reportRunning = calReportRunning(positions);
            String logStats = LogMonitor.getStats(4); // Lấy thống kê 4 tiếng qua
            reportRunning.append("\n").append(logStats); // Ghép vào cuối báo cáo
            Utils.sendSms2Telegram(reportRunning.toString());
            Utils.printMemoryUsage("Total ram used");
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static StringBuilder calReportRunning(Collection<PositionRisk> positions) {
        StringBuilder builder = new StringBuilder();
        Asset umInfo = BinanceFuturesClientSingleton.getInstance().getAccountUMInfo();

        BudgetManager.getInstance().balance = umInfo.getWalletBalance().floatValue();
        Float marginRunning = umInfo.getPositionInitialMargin().floatValue() - umInfo.getUnrealizedProfit().floatValue();
        builder.append("Balance: ").append(umInfo.getMarginBalance().longValue()).append("$ -> ")
                .append(umInfo.getWalletBalance().longValue()).append("$")
                .append(" marginRun: ").append(BudgetManager.getInstance().calMarginRunning(positions).longValue()).append("/")
                .append(marginRunning.longValue()).append("/")
                .append(umInfo.getCrossUnPnl().longValue());
        builder.append(" \nRunning: ").append(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_RUNNING).size())
                .append(" orders");
        return builder;
    }


}
