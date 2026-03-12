package com.binance.chuyennd.trading;

import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
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
            Utils.sendSms2Telegram(reportRunning.toString());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static StringBuilder calReportRunning(Collection<PositionRisk> positions) {
        StringBuilder builder = new StringBuilder();
//        Set<String> symbolsSell = new HashSet<>();
//
//        Long totalLoss = 0l;
//        Long totalBuy = 0l;
//        Long totalSell = 0l;
//        Long totalUnder3 = 0l;
//        Long totalOver5 = 0l;
//
//        TreeMap<Float, PositionRisk> rate2Order = new TreeMap<>();
//        for (PositionRisk position : positions) {
//            if (position.getPositionAmt() != null && position.getPositionAmt().floatValue() != 0) {
//                Float rateLoss = PositionHelper.calRateLoss(position) * 100;
//                rate2Order.put(rateLoss, position);
//                if (rateLoss < -5) {
//                    totalOver5++;
//                }
//                if (rateLoss >= -3) {
//                    totalUnder3++;
//                }
//            }
//        }
//        int counterLog = 0;
//        for (Map.Entry<Float, PositionRisk> entry : rate2Order.entrySet()) {
//            Float rateLoss = entry.getKey();
//            PositionRisk pos = entry.getValue();
//            Long ratePercent = rateLoss.longValue();
//            totalLoss += ratePercent;
//            Float rateLoss2DcaOfSym;
//            if (pos.getPositionAmt().floatValue() > 0) {
//                totalBuy += ratePercent;
//                rateLoss2DcaOfSym = BudgetManager.getInstance().callRate2DcaBuy(-0.25, PositionHelper.callMargin(pos));
//            } else {
//                symbolsSell.add(pos.getSymbol());
//                totalSell += ratePercent;
//                rateLoss2DcaOfSym = -BudgetManager.getInstance().callRate2DcaSell(PositionHelper.callMargin(pos));
//            }
//            if (counterLog < 15) {
//                counterLog++;
//                Float pnl = Utils.callPnl(pos) * 100;
//                Long pnlLong = pnl.longValue();
//                Float entryPrice = ClientSingleton.getInstance().normalizePrice(pos.getSymbol(), pos.getEntryPrice().floatValue());
//                Float lastPrice = ClientSingleton.getInstance().normalizePrice(pos.getSymbol(), pos.getMarkPrice().floatValue());
//                Float priceDCA = entryPrice * (1 + rateLoss2DcaOfSym);
//                priceDCA = ClientSingleton.getInstance().normalizePrice(pos.getSymbol(), priceDCA);
//                builder.append(pos.getSymbol().replace("USDT", "")).append(" ")
//                        .append(PositionHelper.callMargin(pos).longValue())
//                        .append(" ")
//                        .append(entryPrice).append("->").append(lastPrice).append("->").append(priceDCA)
//                        .append(" ").append(ratePercent).append("%")
//                        .append(" ").append(pnlLong.floatValue() / 100).append("$")
//                        .append("\n");
//            }
//        }
        Asset umInfo = BinanceFuturesClientSingleton.getInstance().getAccountUMInfo();

        BudgetManager.getInstance().balance = umInfo.getWalletBalance().floatValue();
        Float marginRunning = umInfo.getPositionInitialMargin().floatValue() - umInfo.getUnrealizedProfit().floatValue();
        builder.append("Balance: ").append(umInfo.getMarginBalance().longValue()).append("$ -> ")
                .append(umInfo.getWalletBalance().longValue()).append("$")
                .append(" marginRun: ").append(BudgetManager.getInstance().calMarginRunning(positions).longValue()).append("/")
                .append(marginRunning.longValue()).append("/")
//        builder.append("\nTotal: ")
//                .append(totalLoss.floatValue()).append("% -> ")
                .append(umInfo.getCrossUnPnl().longValue());
//        builder.append(" Buy: ").append(totalBuy.floatValue()).append("%");
//        builder.append(" Sell: ").append(totalSell.floatValue()).append("%");
        builder.append(" \nRunning: ").append(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_RUNNING).size())
                .append(" orders");
//        builder.append(" Under3: ").append(totalUnder3);
//        builder.append(" Over5: ").append(totalOver5);
        return builder;
    }


}
