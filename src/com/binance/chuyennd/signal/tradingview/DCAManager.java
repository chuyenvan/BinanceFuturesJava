///*
// * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
// * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
// */
//package com.binance.chuyennd.signal.tradingview;
//
//import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
//import com.binance.chuyennd.client.OrderHelper;
//import com.binance.chuyennd.client.TickerFuturesHelper;
//import com.binance.chuyennd.redis.RedisConst;
//import com.binance.chuyennd.redis.RedisHelper;
//import com.binance.chuyennd.trading.BinanceOrderTradingManager;
//import com.binance.chuyennd.trading.BudgetManager;
//import com.binance.chuyennd.utils.Configs;
//import com.binance.chuyennd.utils.Utils;
//import com.binance.client.model.enums.OrderSide;
//import com.binance.client.model.trade.Order;
//import com.binance.client.model.trade.PositionRisk;
//
//import java.io.File;
//import java.util.ArrayList;
//import java.util.HashMap;
//import java.util.HashSet;
//import java.util.List;
//import java.util.Map;
//import java.util.Set;
//import java.util.TreeMap;
//import java.util.concurrent.ConcurrentHashMap;
//import java.util.concurrent.ExecutorService;
//import java.util.concurrent.Executors;
//
//import org.apache.commons.io.FileUtils;
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
///**
// * @author pc
// */
//public class DCAManager {
//
//    public static final Logger LOG = LoggerFactory.getLogger(DCAManager.class);
//    public static Map<Integer, Integer> level2Rate = new HashMap<>();
//    public static final String FILE_STORAGE_ORDER_DCA = "storage/OrderDCA.data";
//
//    public Double MAX_CAPITAL_RATE_DCA = Configs.getDouble("MAX_CAPITAL_RATE_DCA");
//    private final ConcurrentHashMap<String, PositionRisk> symbol2Processing = new ConcurrentHashMap<>();
//    public ExecutorService executorServiceDCA = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));
//
//    //    static {
////        level2Rate.put(0, 30);
////        level2Rate.put(1, 60);
////        level2Rate.put(2, 95);
////        level2Rate.put(3, 98);
////    }
//    static {
//        level2Rate.put(0, 50);
//        level2Rate.put(1, 99);
//        level2Rate.put(2, 99);
//        level2Rate.put(3, 99);
//    }
//
//    public static void main(String[] args) {
////        PositionRisk pos = BinanceFuturesClientSingleton.getInstance().getPositionInfo("REEFUSDT");
////        RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_BINANCE_ORDER_DCA_QUEUES, Utils.toJson(pos));
////        new DCAManager().startTheadListenAndProcessDCA();
//        List<PositionRisk> positions = BinanceFuturesClientSingleton.getInstance().getAllPositionInfos();
//        String reportDca = DCAManager.buildReportDCA(positions);
//        System.out.println(reportDca);
////        new DCAManager().traceDcaRate();
//    }
//
//    private static Double calPriceDca(double priceOld, double priceNew) {
//        return priceNew * 2 - priceOld;
//    }
//
//    public static String buildReportDCA(List<PositionRisk> positions) {
//        Map<String, PositionRisk> symbol2Position = new HashMap<>();
//        for (PositionRisk position : positions) {
//            symbol2Position.put(position.getSymbol(), position);
//        }
//        String result = "";
//        Map<String, Double> sym2LastPrice = TickerFuturesHelper.getAllLastPrice();
//        try {
//            List<String> lines = FileUtils.readLines(new File(FILE_STORAGE_ORDER_DCA));
//            Map<PositionRisk, PositionRisk> pairPositionDca = new HashMap<>();
//            PositionRisk posOld = null;
//            PositionRisk posNew = null;
//            for (String line : lines) {
//                if (posNew != null && posOld != null) {
//                    pairPositionDca.put(posOld, posNew);
//                    posOld = null;
//                    posNew = null;
//                }
//                if (posOld == null) {
//                    posOld = Utils.gson.fromJson(line, PositionRisk.class);
//                } else {
//                    posNew = Utils.gson.fromJson(line, PositionRisk.class);
//                }
//            }
//            if (posNew != null && posOld != null) {
//                pairPositionDca.put(posOld, posNew);
//            }
//            // remove dca old
//            Set<PositionRisk> posRemoves = new HashSet<>();
//            Map<String, PositionRisk> symbol2LastPos = new HashMap<>();
//            for (Map.Entry<PositionRisk, PositionRisk> entry : pairPositionDca.entrySet()) {
//                PositionRisk pos1 = entry.getKey();
//                PositionRisk pos2 = entry.getValue();
//                PositionRisk posBefore = symbol2LastPos.get(pos2.getSymbol());
//                if (posBefore != null) {
//                    // check quantity
//                    if (pos1.getPositionAmt().doubleValue() == posBefore.getPositionAmt().doubleValue()) {
//                        // check time
//                        if (pos1.getUpdateTime() > posBefore.getUpdateTime()) {
//                            symbol2LastPos.put(pos1.getSymbol(), pos1);
//                            posRemoves.add(posBefore);
//                            LOG.info("Remove dca old of {} time1:{} time2: {}", pos1.getSymbol(),
//                                    Utils.normalizeDateYYYYMMDDHHmm(posBefore.getUpdateTime()),
//                                    Utils.normalizeDateYYYYMMDDHHmm(pos1.getUpdateTime()));
//                        } else {
//                            posRemoves.add(pos1);
//                            LOG.info("Remove dca old of {} time1:{} time2: {}", pos1.getSymbol(),
//                                    Utils.normalizeDateYYYYMMDDHHmm(pos1.getUpdateTime()),
//                                    Utils.normalizeDateYYYYMMDDHHmm(posBefore.getUpdateTime()));
//                        }
//                    }
//                } else {
//                    symbol2LastPos.put(pos1.getSymbol(), pos1);
//                }
//            }
//            for (PositionRisk posRemove : posRemoves) {
//                pairPositionDca.remove(posRemove);
//            }
//            Double totalRateLoss = 0d;
//            Double totalPnl = 0d;
//            TreeMap<Double, String> rateLoss2Symbol = new TreeMap();
//            Map<String, Double> symbol2Pnl = new HashMap<>();
//            Set<String> symbolDones = new HashSet<>();
//
//            for (Map.Entry<PositionRisk, PositionRisk> entry : pairPositionDca.entrySet()) {
//                PositionRisk pos1 = entry.getKey();
//                PositionRisk pos2 = entry.getValue();
//                // check pos done
//                PositionRisk currentPosition = symbol2Position.get(pos1.getSymbol());
//                if (currentPosition.getPositionAmt().doubleValue() != pos2.getPositionAmt().doubleValue()) {
//                    symbolDones.add(pos1.getSymbol());
//                    totalPnl += Utils.callPnlDone(pos1);
//                    continue;
//                }
//                // pos not done
//                Double priceDca = calPriceDca(pos1.getEntryPrice().doubleValue(), pos2.getEntryPrice().doubleValue());
//                Double lastPrice = sym2LastPrice.get(pos1.getSymbol());
//                totalRateLoss += Utils.rateOf2Double(lastPrice, priceDca);
//                totalPnl += Utils.callPnl(pos2, lastPrice) - Utils.callPnl(pos1);
//                symbol2Pnl.put(pos1.getSymbol(), Utils.callPnl(pos2, lastPrice) - Utils.callPnl(pos1));
//                rateLoss2Symbol.put(Utils.rateOf2Double(lastPrice, priceDca),
//                        pos1.getSymbol() + " " + Utils.callPnl(pos2, lastPrice) + " " + Utils.callPnl(pos1));
//            }
//            for (Map.Entry<Double, String> entry : rateLoss2Symbol.entrySet()) {
//                Double rateLoss = entry.getKey();
//                String symbol = entry.getValue();
//                LOG.info("Dca rate: {} ->  {}% {}", symbol, Utils.formatPercent(rateLoss), symbol2Pnl.get(symbol.split(" ")[0]));
//            }
//            StringBuilder builder = new StringBuilder();
//            builder.append("Rate:").append(Utils.formatPercent(totalRateLoss)).append("%");
//            builder.append(" Pnl:").append(totalPnl.longValue()).append("$");
//            builder.append(" Done:").append(symbolDones.size()).append("/")
//                    .append(pairPositionDca.size()).append(" ");//.append(Utils.toJson(symbolDones));
//            return builder.toString();
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//        return result;
//    }
//
//    private void dcaForOrder(PositionRisk pos) {
//        try {
//            Order orderInfo = OrderHelper.newOrderMarket(pos.getSymbol(), OrderSide.BUY,
//                    pos.getPositionAmt().doubleValue(), BudgetManager.getInstance().getLeverage());
//            if (orderInfo != null) {
//                List<String> lines = new ArrayList<>();
//                lines.add(Utils.toJson(pos));
//
//                //cancel order tp old
//                List<Order> orderOpens = BinanceFuturesClientSingleton.getInstance().getOpenOrders(pos.getSymbol());
//                for (Order orderOpen : orderOpens) {
//                    Utils.sendSms2Telegram("Cancel order: " + orderOpen.getOrderId() + " of " + pos.getSymbol());
//                    LOG.info("Cancel order: " + orderOpen.getOrderId() + " of " + pos.getSymbol());
//                    BinanceFuturesClientSingleton.getInstance().cancelOrder(pos.getSymbol(),
//                            orderOpen.getClientOrderId());
//                }
//                // re create tp
//                PositionRisk posNew = BinanceFuturesClientSingleton.getInstance().getPositionInfo(pos.getSymbol());
//                if (posNew != null && posNew.getPositionAmt().doubleValue() != 0) {
//                    lines.add(Utils.toJson(posNew));
//                    new BinanceOrderTradingManager().createTp(posNew);
//                }
//                FileUtils.writeLines(new File(FILE_STORAGE_ORDER_DCA), lines, true);
//            }
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//    }
//
//    public static Double getMinRateDCA() {
//        return level2Rate.get(0).doubleValue();
//    }
//
//    public static Integer getLevelBudget(Double budgetOfOrder) {
//        return budgetOfOrder.intValue() / BudgetManager.getInstance().getBudget().intValue();
//    }
//
//    private static Integer getRateDcaWithBudget(Double budgetOfOrder) {
//        Integer level = getLevelBudget(budgetOfOrder);
//        return getRateOfLevel(level);
//    }
//
//    public static Integer getRateOfLevel(Integer level) {
//        if (level >= 3) {
//            return 99;
//        }
//        return level2Rate.get(level);
//    }
//
//    private void checkAndDcaOrder(PositionRisk pos) {
//        try {
//            Double budgetOfOrder = callBudgetOfOrder(pos);
//            Integer levelDca = getLevelBudget(budgetOfOrder);
//            LOG.info("Level dca: {} budgetPos: {} BudgetCurrent: {}", pos.getSymbol(),
//                    budgetOfOrder, BudgetManager.getInstance().getBudget());
//            Integer rate2Dca = getRateDcaWithBudget(budgetOfOrder);
//            Double rateLoss = getRateLoss(pos);
//            if (Math.abs(rateLoss) * 100 >= rate2Dca.doubleValue()) {
//                LOG.info("Dca for {} budgetOrder:{} budget:{} entry: {} lastprice: {} rateLoss: {} levelDca: {} rateDca: {} quantity: {}",
//                        pos.getSymbol(), budgetOfOrder, BudgetManager.getInstance().getBudget(), pos.getEntryPrice().doubleValue(),
//                        pos.getMarkPrice().doubleValue(), rateLoss * 100, levelDca, rate2Dca, pos.getPositionAmt().doubleValue());
//                dcaForOrder(pos);
//            } else {
//                LOG.info("Not Dca for {} entry: {} lastprice: {} rateLoss: {} levelDca: {} rateDca: {} quantity: {}",
//                        pos.getSymbol(), pos.getEntryPrice().doubleValue(), pos.getMarkPrice().doubleValue(),
//                        rateLoss * 100, levelDca, rate2Dca, pos.getPositionAmt().doubleValue());
//            }
//
//        } catch (Exception e) {
//            e.printStackTrace();
//        }
//        symbol2Processing.remove(pos.getSymbol());
//
//    }
//
//    public static Double callBudgetOfOrder(PositionRisk pos) {
//        return pos.getMarkPrice().doubleValue() * pos.getPositionAmt().doubleValue() / pos.getLeverage().doubleValue();
//    }
//
//    public static Double getRateLoss(PositionRisk pos) {
//        return Math.abs(Utils.rateOf2Double(pos.getMarkPrice().doubleValue(), pos.getEntryPrice().doubleValue()));
//    }
//
//    public void startTheadListenAndProcessDCA() {
//        new Thread(() -> {
//            Thread.currentThread().setName("ListenAndProcessDCA");
//            LOG.info("Start thread ListenAndProcessDCA!");
//            while (true) {
//                List<String> data;
//                try {
//                    data = RedisHelper.getInstance().get().blpop(0, RedisConst.REDIS_KEY_BINANCE_ORDER_DCA_QUEUES);
//                    String json = data.get(1);
//                    try {
//                        PositionRisk pos = Utils.gson.fromJson(json, PositionRisk.class);
//                        LOG.info("Queue listen pos to dca manager received : {} ", pos.getSymbol());
//                        if (BudgetManager.getInstance().getInvesting() > MAX_CAPITAL_RATE_DCA) {
//                            LOG.info("Stop dca {} because investing over: {}", pos.getSymbol(),
//                                    BudgetManager.getInstance().getInvesting());
//                            continue;
//                        }
////                         check entry 2 dca by btc trend
//                        if (!symbol2Processing.containsKey(pos.getSymbol())) {
//                            symbol2Processing.put(pos.getSymbol(), pos);
//                            executorServiceDCA.execute(() -> checkAndDcaOrder(pos));
//                        } else {
//                            LOG.info("{} is lock because processing! {}", pos.getSymbol(), symbol2Processing.size());
//                        }
//                    } catch (Exception e) {
//                        e.printStackTrace();
//                    }
//                } catch (Exception e) {
//                    LOG.error("ERROR during ListenAndProcessDCA {}", e);
//                    e.printStackTrace();
//                }
//            }
//        }).start();
//    }
//
//    private void traceDcaRate() {
//        Double quantity = 100d;
//        Double startPrice = 1d;
//        Double totalBalance = quantity * startPrice;
//        for (int level = 0; level < 10; level++) {
//            Integer rate = DCAManager.getRateOfLevel(level);
//            Double priceDca = startPrice * (100 - rate) / 100;
//            Double balanceNew = priceDca * quantity;
//            totalBalance += balanceNew;
//            startPrice = (priceDca + startPrice) / 2;
//            quantity += quantity;
//            LOG.info("level:{} -> rate:{} priceDca:{} balance:{} totalBalance:{} quantity:{} priceNew:{} ",
//                    level, rate, priceDca, balanceNew, totalBalance, quantity, startPrice);
//        }
//    }
//
//}
