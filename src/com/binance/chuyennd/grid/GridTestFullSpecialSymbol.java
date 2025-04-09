package com.binance.chuyennd.grid;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.GridConfigs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;


public class GridTestFullSpecialSymbol {
    public static final Logger LOG = LoggerFactory.getLogger(GridTestFullSpecialSymbol.class);

    public static void main(String[] args) throws ParseException {
//        String symbol = "XRPUSDT";
//        for (int i = 0; i < 10; i++) {
//            GridConfigs.RATE_DOWN_4H_REVERSE = 0.07 + i * 0.01;
        ConcurrentHashMap<Long, GridObjectTestResearch> allGridDone = new ConcurrentHashMap<>();
        Double totalBuy = 0d;
        Double totalSell = 0d;
        TreeMap<Integer, Double> year2ProfitTotal = new TreeMap<>();
        TreeMap<Integer, Double> year2ProfitStartTotal = new TreeMap<>();
        StringBuilder builder = new StringBuilder();
        builder.append("Rate: ").append(GridConfigs.GRID_RATE_TRADE)
                .append(" numberOrder: ").append(GridConfigs.GRID_NUMBER_ORDER_ACTIVE)
                .append(" sma: ").append(GridConfigs.SMA_LONG).append("-").append(GridConfigs.SMA_SHORT)
                .append(" rate4hReverse: ").append(GridConfigs.RATE_DOWN_4H_REVERSE)
                .append(" budget: ").append(BudgetManagerSimple.getInstance().getBudgetGrid())
                .append("\n");
//        Set<String> hashSet = getAllSymbolHaveTicker1M();
//        for (String symbol : hashSet) {
        for (String symbol : Constants.specialSymbol) {
            TreeMap<Integer, Double> year2Profit = new TreeMap<>();
            long startTime = Utils.sdfFileHour.parse("20210102 07:23").getTime();
            long endTime = Utils.sdfFileHour.parse("20260101 07:23").getTime();
            try {
                List<KlineObjectSimple> tickers = (List<KlineObjectSimple>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_1M + symbol);
                if (tickers == null) {
                    continue;
                }
//                List<KlineObjectNumber> ticker1Ds = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_1D + symbol);
                List<KlineObjectNumber> ticker1Ds = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_4HOUR + symbol);
                Double profitSellTotal = 0d;
                Double profitBuyTotal = 0d;
                int counter = 0;
                int counterOrder = 0;
                GridObjectTestResearch simulator = null;
                GridObjectTestResearch lastGrid = null;
                Map<Long, KlineObjectSimple> time2Ticker = new HashMap<>();
                for (KlineObjectSimple ticker : tickers) {
                    time2Ticker.put(ticker.startTime.longValue(), ticker);
                    if (ticker.startTime.longValue() < startTime) {
                        continue;
                    }
                    if (ticker.startTime.longValue() > endTime) {
                        break;
                    }
                    Double differenceMa20AndMa60 = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC
                            , ticker.startTime.longValue());
                    Double difference4hMa20AndMa60 = SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC
                            , ticker.startTime.longValue());

                    if (simulator != null) {
                        if (simulator.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                            if (ticker.startTime.longValue() <= simulator.tickerStart.startTime.longValue()) {
                                continue;
                            }
                            simulator.updateAllOrderRunning(ticker);

                        } else {
//                    simulator.printResult();
                            Integer year = Utils.getYear(simulator.endTime);
                            Double profitYear = year2Profit.get(year);
                            if (profitYear == null) {
                                profitYear = 0d;
                            }
                            Double profitYearTotal = year2ProfitTotal.get(year);
                            if (profitYearTotal == null) {
                                profitYearTotal = 0d;
                            }
                            Double profitStartYearTotal = year2ProfitStartTotal.get(year);
                            if (profitStartYearTotal == null) {
                                profitStartYearTotal = 0d;
                            }
                            profitYear += simulator.calProfit();
                            profitYearTotal += simulator.calProfit();
                            profitStartYearTotal += simulator.calProfitStart();
                            year2Profit.put(year, profitYear);
                            year2ProfitTotal.put(year, profitYearTotal);
                            year2ProfitStartTotal.put(year, profitStartYearTotal);
                            counter++;
                            counterOrder += simulator.time2OrderDone.size();
                            if (simulator.side.equals(OrderSide.BUY)) {
                                profitBuyTotal += simulator.calProfit();
                            } else {
                                profitSellTotal += simulator.calProfit();
                            }
                            lastGrid = simulator;
                            allGridDone.put(simulator.tickerStart.startTime.longValue() + allGridDone.size(), simulator);
                            simulator = null;
                        }
                    }
                    if (simulator == null) {
                        KlineObjectSimple ticker4h = time2Ticker.get(ticker.startTime.longValue() - 4 * Utils.TIME_HOUR);
                        Double rate4h = null;
                        if (ticker4h != null) {
                            rate4h = Utils.rateOf2Double(ticker.priceClose, ticker4h.priceOpen);
                        }
                        simulator = GridDetector.findGridSpecialSymbol(symbol, ticker, ticker.startTime.longValue(), ticker1Ds,
                                differenceMa20AndMa60, difference4hMa20AndMa60, rate4h);
                        if (simulator != null) {
                            LOG.info("Init grid: {} {} ", symbol, Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()));
                            simulator.initGrid();
                        }
                    }


                }
                if (simulator != null) {
                    if (simulator.side.equals(OrderSide.BUY)) {
                        profitBuyTotal += simulator.calProfit();
                    } else {
                        profitSellTotal += simulator.calProfit();
                    }
                    counter++;
                    counterOrder += simulator.time2OrderDone.size();
//            simulator.printResult();
//                simulator.exportFile();
                }
//                LOG.info("Rate:{} numberOrder:{} {} {} grids {} orders profit: {} {} {}",
//                        GridConfigs.GRID_RATE_TRADE, GridConfigs.GRID_NUMBER_ORDER_ACTIVE,
//                        symbol, counter, counterOrder,
//                        profitBuyTotal.longValue(), profitSellTotal.longValue(),
//                        profitBuyTotal.longValue() + profitSellTotal.longValue());

                builder.append(Utils.formatLogString(symbol.replace("USDT", "").replace("1000", ""), 6)).append("\t");
                for (Integer year : year2Profit.keySet()) {
                    builder.append(year).append(": ").append(Utils.formatLog(year2Profit.get(year).longValue(), 6)).append("\t");
                }
                builder.append("grids: ").append(Utils.formatLog(counter, 3)).append("\t");
                builder.append("orders: ").append(Utils.formatLog(counterOrder, 4)).append("\t");
                builder.append("profit: ").append(Utils.formatLog(profitBuyTotal.longValue(), 6)).append("\t");
                builder.append(Utils.formatLog(profitSellTotal.longValue(), 6)).append("\t");
                builder.append(Utils.formatLog(profitBuyTotal.longValue() + profitSellTotal.longValue(), 8)).append("\n");

                totalSell += profitSellTotal;
                totalBuy += profitBuyTotal;
            } catch (Exception e) {
                LOG.info("Error simulator for: {}", symbol);
                e.printStackTrace();
            }
        }
        builder.append("Total:\t");
        for (Integer year : year2ProfitTotal.keySet()) {
            builder.append(year).append(": ");
//            builder.append(Utils.formatLog(year2ProfitStartTotal.get(year).longValue(), 6)).append("/");
            builder.append(Utils.formatLog(year2ProfitTotal.get(year).longValue(), 6)).append("\t");
        }
        builder.append(" \t \t \t \t \t \t \tprofit: ");
        builder.append(Utils.formatLog(totalBuy.longValue(), 6)).append("\t");
        builder.append(Utils.formatLog(totalSell.longValue(), 6)).append("\t");
        builder.append(Utils.formatLog(totalBuy.longValue() + totalSell.longValue(), 8)).append("\n");
        LOG.info(builder.toString());
        Storage.writeObject2File("storage/GridTestDone.data", allGridDone);
    }

    private static Set<String> getAllSymbolHaveTicker1M() {
        Set<String> hashSet = new HashSet<>();
        File[] symbolFiles = new File(Configs.FOLDER_TICKER_1D).listFiles();
        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
            hashSet.add(symbol);
        }
        return hashSet;
    }
//    }


}
