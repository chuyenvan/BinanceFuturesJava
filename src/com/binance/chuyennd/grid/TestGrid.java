package com.binance.chuyennd.grid;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

public class TestGrid {
    public static final Logger LOG = LoggerFactory.getLogger(TestGrid.class);
    public ConcurrentHashMap<Long, GridObjectTest> allGridDone = new ConcurrentHashMap<>();

    public static void main(String[] args) throws ParseException {
//        String symbol = Constants.SYMBOL_PAIR_BNB;

//        new TestGrid().simulatorASymbol(symbol);
        for (String symbol : Constants.specialSymbol) {
            new TestGrid().simulatorFullSymbol(symbol);
        }

//        List<GridObjectTest> grids = new ArrayList<>();
//        Long startTime;
//        for (int i = 0; i < 10; i++) {
//            startTime = Utils.sdfFileHour.parse("20241117 07:00").getTime()  + Utils.TIME_DAY * i * 2;
//            List<KlineObjectSimple> tickers = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M, startTime);
//            grids.add(new GridObjectTest(symbol, OrderSide.BUY, 110000.0, 90000.0,
//                    112000.0, 88000.0, 25, tickers.get(0)));
//        }
//        new TestGrid().simulatorByTime(grids);


//        String symbol = Constants.SYMBOL_PAIR_BNB;
//        List<GridObjectTest> grids = new ArrayList<>();
//        List<Long> times= new ArrayList<>();
//        Long startTime;
//
//        for (int i = 0; i < 10; i++) {
//            times.add(Utils.sdfFileHour.parse("20240313 07:00").getTime() + Utils.TIME_DAY * i * 3);
//        }
//        times.add(Utils.sdfFileHour.parse("20240320 07:00").getTime());
//        times.add(Utils.sdfFileHour.parse("20240617 07:00").getTime());
//        times.add(Utils.sdfFileHour.parse("20240805 13:24").getTime());
//        times.add(Utils.sdfFileHour.parse("20250203 09:08").getTime());
//        for (Long time: times){
//            List<KlineObjectSimple> tickers = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M, time);
//            grids.add(new GridObjectTest(symbol, OrderSide.BUY, 730.0, 500.0,
//                    800.0, 395.0, 50, tickers.get(0)));
//        }
//        new TestGrid().simulatorByTime(grids, symbol);

    }

    private void simulatorByTime(List<GridObjectTest> grids, String symbol) {
        Long minTime = null;
        for (GridObjectTest grid : grids) {
            grid.initGrid();
            allGridDone.put(grid.tickerStart.startTime.longValue() + allGridDone.size(), grid);
            if (minTime == null || minTime > grid.tickerStart.startTime.longValue()) {
                minTime = grid.tickerStart.startTime.longValue();
            }
        }
        List<KlineObjectSimple> tickers = (List<KlineObjectSimple>) Storage.readObjectFromFile(
                Configs.FOLDER_TICKER_1M + symbol);

        while (true) {
            if (tickers.get(0).startTime < minTime) {
                tickers.remove(0);
            } else {
                break;
            }
        }
        LOG.info("size: {}", tickers.size());
        while (true) {
//            LOG.info("start time check: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
            KlineObjectSimple ticker = tickers.get(0);
            tickers.remove(0);
            for (GridObjectTest grid : grids) {
                if (grid.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                    grid.updateGrid(ticker);
                }
            }
            if (tickers.size() < 100) {
                break;
            }
        }
        for (GridObjectTest grid : grids) {
            grid.printResult();
        }
        Storage.writeObject2File("storage/GridTestDone.data", allGridDone);
    }

    private void simulatorFullSymbol(String symbol) {
        List<KlineObjectNumber> ticker15Ms = (List<KlineObjectNumber>)
                Storage.readObjectFromFile(Configs.FOLDER_TICKER_15M + symbol);
        List<KlineObjectSimple> tickers = (List<KlineObjectSimple>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_1M + symbol);
        while (true) {
//            LOG.info("start time check: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
            GridObjectTest grid = null;
            while (grid == null) {
                tickers.remove(0);
                grid = findRange2Run(symbol, ticker15Ms, tickers.get(0));
                if (tickers.size() < 100) {
                    break;
                }
            }
            if (grid != null) {
                grid.initGrid();
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectSimple ticker = tickers.get(0);
                    tickers.remove(0);
                    if (grid.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                        grid.updateGrid(ticker);
                    }
                    if (grid.status.equals(OrderTargetStatus.FINISHED)) {
                        grid.printResult();
                        allGridDone.put(grid.tickerStart.startTime.longValue() + allGridDone.size(), grid);
                        break;
                    }
                }


            }
            if (tickers.size() < 100) {
                break;
            }
        }
        Storage.writeObject2File("storage/GridTestDone.data-" + symbol, allGridDone);
    }

    private static void printResultBySymbol(String symbol, List<GridObjectTest> allGridDone) {
        int counterSuccess = 0;
        int counterFlase = 0;
        Double totalProfit = 0d;
        for (GridObjectTest gridObject : allGridDone) {
            Double profit = gridObject.calProfit();
            if (profit > 0) {
                counterSuccess++;
            } else {
                counterFlase++;
            }
            totalProfit += profit;
        }
        LOG.info("ResultAll: {} s {} f {} {} profit:{} avg:{} ", symbol, counterSuccess, counterFlase, allGridDone.size(),
                totalProfit, totalProfit / allGridDone.size());
    }

    private static GridObjectTest findRange2Run(String symbol, List<KlineObjectNumber> ticker15Ms, KlineObjectSimple ticker) {
        Double maxPrice = null;
        Double minPrice = null;
        Long startTime = ticker.startTime.longValue();
//        int counter = 0;
        for (KlineObjectNumber kline : ticker15Ms) {
            if (kline.startTime.longValue() <= startTime
                    && kline.startTime.longValue() > startTime - 3 * Utils.TIME_DAY) {
//                counter++;
                maxPrice = Utils.maxPrice(kline, maxPrice);
                minPrice = Utils.minPrice(kline, minPrice);
            }
        }
//        LOG.info("Counter ticker 15M cal rate: {} {} {}", symbol, counter, Utils.normalizeDateYYYYMMDDHHmm(startTime));
        if (maxPrice == null || minPrice == null) {
            return null;
        }
        double rateCheck = -0.08;
        Double rateOver = 0.03;
        if (Constants.stableSymbol.contains(symbol)) {
            rateCheck = -0.07;
            rateOver = 0.07;
        }
        if (Utils.rateOf2Double(ticker.priceClose, (maxPrice + minPrice) / 2) < rateCheck) {
            Double top = maxPrice * (1 + rateOver);
            Double bottom = minPrice * (1 - rateOver);
            Double range = Utils.rateOf2Double(maxPrice, minPrice) * 100 ;
            GridObjectTest simulator = new GridObjectTest(symbol, OrderSide.BUY, maxPrice, minPrice, top, bottom, range.intValue(), ticker);
            return simulator;
        }
        return null;
    }
}
