package com.binance.chuyennd.trading;

import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.trade.Asset;
import com.binance.client.model.trade.PositionRisk;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class Reporter {
    public static final Logger LOG = LoggerFactory.getLogger(Reporter.class);
    public static Double balanceStart = Configs.getDouble("CAPITAL_START");
    public static Double rateProfit = Configs.getDouble("PROFIT_RATE");
    public static long timeStartRun = Configs.getLong("TIME_START");

    public static void startThreadReportPosition() {
        new Thread(() -> {
            Thread.currentThread().setName("Reporter");
            LOG.info("Start thread report !");
            while (true) {
                try {
                    Thread.sleep(30 * Utils.TIME_SECOND);
                    if (isTimeReport()) {
                        buildReport();
                    }
                } catch (Exception e) {
                    LOG.error("ERROR during : {}", e);
                    e.printStackTrace();
                }
            }
        }).start();

    }

    public static boolean isTimeReport() {
        return Utils.getCurrentMinute() % 15 == 1 && Utils.getCurrentSecond() < 30;
    }

    public static void buildReport() {
        StringBuilder reportRunning = calReportRunning();
        Utils.sendSms2Telegram(reportRunning.toString());
    }

    public static StringBuilder calReportRunning() {
        StringBuilder builder = new StringBuilder();
        Set<String> symbolsSell = new HashSet<>();

        Long totalLoss = 0l;
        Long totalBuy = 0l;
        Long totalSell = 0l;
        Long totalUnder3 = 0l;
        Long totalOver5 = 0l;

        TreeMap<Double, PositionRisk> rate2Order = new TreeMap<>();
        List<PositionRisk> positions = BinanceFuturesClientSingleton.getInstance().getAllPositionInfos();
        for (PositionRisk position : positions) {
            if (position.getPositionAmt() != null && position.getPositionAmt().doubleValue() != 0) {
                Double rateLoss = Utils.rateOf2Double(position.getMarkPrice().doubleValue(), position.getEntryPrice().doubleValue()) * 100;
                rate2Order.put(rateLoss, position);
                if (rateLoss < -5) {
                    totalOver5++;
                }
                if (rateLoss >= -3) {
                    totalUnder3++;
                }
            }
        }
        int counterLog = 0;
        for (Map.Entry<Double, PositionRisk> entry : rate2Order.entrySet()) {
            Double rateLoss = entry.getKey();
            PositionRisk pos = entry.getValue();
            Long ratePercent = rateLoss.longValue();
            totalLoss += ratePercent;
            if (pos.getPositionAmt().doubleValue() > 0) {
                totalBuy += ratePercent;
            } else {
                symbolsSell.add(pos.getSymbol());
                totalSell += ratePercent;
            }
            if (counterLog < 15) {
                counterLog++;
                OrderSide side = OrderSide.BUY;
                if (pos.getPositionAmt().doubleValue() < 0) {
                    side = OrderSide.SELL;
                }
                Double pnl = Utils.callPnl(pos) * 100;
                Long pnlLong = pnl.longValue();
                Double entryPrice = ClientSingleton.getInstance().normalizePrice(pos.getSymbol(), pos.getEntryPrice().doubleValue());
                Double lastPrice = ClientSingleton.getInstance().normalizePrice(pos.getSymbol(), pos.getMarkPrice().doubleValue());
                String orderJson = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, pos.getSymbol());
                OrderTargetInfo order = Utils.gson.fromJson(orderJson, OrderTargetInfo.class);
                String marketOrder = "";
                if (order != null) {
                    marketOrder = order.marketLevel.toString();
                }
                builder.append(side).append(" ")
                        .append(pos.getSymbol().replace("USDT", "")).append(" ")
                        .append(marketOrder)
                        .append(" ")
                        .append(entryPrice).append("->").append(lastPrice)
                        .append(" ").append(ratePercent).append("%")
                        .append(" ").append(pnlLong.doubleValue() / 100).append("$")
                        .append("\n");
            }
        }
        Asset umInfo = BinanceFuturesClientSingleton.getInstance().getAccountUMInfo();
        Double balanceTarget = getTargetBalance(System.currentTimeMillis() + Utils.TIME_DAY);
        Double profit = balanceTarget - umInfo.getWalletBalance().doubleValue();

        builder.append("Balance: ").append(umInfo.getMarginBalance().longValue()).append("$ -> ")
                .append(umInfo.getWalletBalance().longValue())
                .append("/").append(balanceTarget.longValue()).append("$")
                .append(" profit: ").append(profit.longValue()).append("");
        builder.append("\nTotal: ").append(totalLoss.doubleValue()).append("% -> ")
                .append(umInfo.getCrossUnPnl().longValue()).append("$");
        builder.append(" Buy: ").append(totalBuy.doubleValue()).append("%");
        builder.append(" Sell: ").append(totalSell.doubleValue()).append("%");
        builder.append(" ").append(symbolsSell.toString());
        builder.append(" \nRunning: ").append(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_RUNNING).size())
                .append(" orders");
        builder.append(" Under3: ").append(totalUnder3);
        builder.append(" Over5: ").append(totalOver5);
        return builder;
    }

    public static Double getTargetBalance(Long currentTime) {
        Double total = balanceStart;
        Long numberDay = (currentTime - timeStartRun) / Utils.TIME_DAY;
        for (int i = 0; i < numberDay; i++) {
            Double inc = total * rateProfit;
            total += inc;
        }
        return total;
    }

}
