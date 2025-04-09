package com.binance.chuyennd.trading.grid;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.grid.GridObjectTestResearch;
import com.binance.chuyennd.grid.SimpleMovingAverage4hManager;
import com.binance.chuyennd.grid.SimpleMovingAverageDayManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.ArrayList;
import java.util.List;

public class CheckProduction {
    public static final Logger LOG = LoggerFactory.getLogger(CheckProduction.class);

    public static void main(String[] args) throws ParseException {
//       checkBNB();
       checkXRP();
//        checkMa();
    }

    private static void checkMa() throws ParseException {
        String symbol = Constants.SYMBOL_PAIR_BTC;
        Long time = Utils.sdfFileHour.parse("20250219 20:11").getTime();
        Double maPro = SimpleMovingAverage4hManagerProduction.getInstance().getDifferenceMa10AndMa60(symbol, time);
        Double maTest = SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(symbol, time);
        LOG.info("ma4H: {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), symbol, maPro, maTest);

        maPro = SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(symbol, time);
        maTest = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(symbol, time);
        LOG.info("maDay: {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), symbol, maPro, maTest);
        symbol = Constants.SYMBOL_PAIR_ETH;
        maPro = SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(symbol, time);
        maTest = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(symbol, time);
        LOG.info("maDay: {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), symbol, maPro, maTest);
        symbol = Constants.SYMBOL_PAIR_XRP;
        maPro = SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(symbol, time);
        maTest = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(symbol, time);
        LOG.info("maDay: {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), symbol, maPro, maTest);
        symbol = Constants.SYMBOL_PAIR_BNB;
        maPro = SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(symbol, time);
        maTest = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(symbol, time);
        LOG.info("maDay: {} {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), symbol, maPro, maTest);


    }

    private static void checkXRP() throws ParseException {
        String symbol = "XRPUSDT";
        OrderSide side = null;
        long startTime = Utils.sdfFileHour.parse("20250304 10:24").getTime() - 4 * Utils.TIME_HOUR;
        List<KlineObjectSimple> tickers = new ArrayList<>();
        for (int i = 0; i < 30; i++) {
            long time = startTime + i * 500 * Utils.TIME_MINUTE;
            tickers.addAll(TickerFuturesHelper.getTickerSimpleWithStartTime(symbol,
                    Constants.INTERVAL_1M, time));
            if (time > System.currentTimeMillis()) {
                break;
            }
        }
//        tickers.get(tickers.size() - 1).minPrice = 90800.0;
        KlineObjectSimple ticker = tickers.get(240);
        ticker.priceClose = 2.2839;
        LOG.info("Time create grid: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                symbol, ticker.priceClose);
        Double rate4h = null;
        KlineObjectSimple ticker4HAgo = tickers.get(0);
        rate4h = Utils.rateOf2Double(ticker.priceClose, ticker4HAgo.priceOpen);
        GridObjectTestResearch simulator = GridDetectorProd.findRange2RunProd(symbol, ticker, rate4h);
        if (side != null) {
            simulator.side = side;
        }
//        simulator.maxPrice = 3.4043;
//        GridObject simulator = new GridObject(symbol, side, tickerStart, range);
        simulator.initGrid();
        LOG.info("{}", Utils.toJson(simulator.prices));
        for (KlineObjectSimple kline : tickers) {
//            if (ticker.startTime.longValue() == Utils.sdfFileHour.parse("20250209 10:59").getTime()) {
//                System.out.println("Debug");
//            }
            if (simulator.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                simulator.updateAllOrderRunning(kline);
            } else {
                break;
            }
        }
        simulator.printResult();
    }

    private static void checkBNB() throws ParseException {
        String symbol = "ZEREBROUSDT";
        OrderSide side = OrderSide.BUY;
        long startTime = Utils.sdfFileHour.parse("20250301 07:00").getTime();
        List<KlineObjectSimple> tickers = new ArrayList<>();
        for (int i = 0; i < 30; i++) {
            long time = startTime + i * 500 * Utils.TIME_MINUTE;
            tickers.addAll(TickerFuturesHelper.getTickerSimpleWithStartTime(symbol,
                    Constants.INTERVAL_1M, time));
            if (time > System.currentTimeMillis()) {
                break;
            }
        }
//        tickers.get(tickers.size() - 1).minPrice = 90800.0;
        KlineObjectSimple tickerStart = tickers.get(0);
        tickerStart.priceClose = 654.7490909091;
        LOG.info("Time create grid: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(tickerStart.startTime.longValue()),
                symbol, tickerStart.priceClose);
        GridObjectTestResearch simulator = new GridObjectTestResearch(symbol, OrderSide.BUY,
                tickerStart.priceClose * 1.2, tickerStart.priceClose * 0.8,
                tickerStart);
//        GridObject simulator = new GridObject(symbol, side, tickerStart, range);
        simulator.initGrid();
        LOG.info("{}", Utils.toJson(simulator.prices));
        for (KlineObjectSimple ticker : tickers) {
//            if (ticker.startTime.longValue() == Utils.sdfFileHour.parse("20250209 10:59").getTime()) {
//                System.out.println("Debug");
//            }
            if (simulator.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                simulator.updateAllOrderRunning(ticker);
            } else {
                break;
            }
        }
        simulator.printResult();
    }
}
