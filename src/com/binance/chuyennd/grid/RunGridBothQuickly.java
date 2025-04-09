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
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static com.binance.chuyennd.utils.Utils.sdfFileHour;

public class RunGridBothQuickly {
    public static final Logger LOG = LoggerFactory.getLogger(RunGridBothQuickly.class);
    public Map<String, List<KlineObjectNumber>> symbol2Ticker1Ws = new HashMap<>();

    public static void main(String[] args) throws ParseException {
//        runWithGridMultiOrder();
        runWithGridOnlyAnOrder();

    }

    private static void runWithGridOnlyAnOrder() throws ParseException {
        String symbol = "CAKEUSDT";
        long startTime = sdfFileHour.parse("20250130 07:00").getTime();
        long timeCheck = sdfFileHour.parse("20250211 11:00").getTime();

        OrderSide side = null;
//        side = OrderSide.BUY;
        List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_4HOUR + symbol);
//        List<KlineObjectSimple> tickers = (List<KlineObjectSimple>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_1M + symbol);

//        List<KlineObjectSimple> tickers = new ArrayList<>();
//        for (int i = 0; i < 30; i++) {
//            long time = startTime + i * 500 * Utils.TIME_MINUTE;
//            tickers.addAll(TickerFuturesHelper.getTickerSimpleWithStartTime(symbol,
//                    Constants.INTERVAL_15M, time));
//            if (time > System.currentTimeMillis()) {
//                break;
//            }
//        }
        Map<Long, KlineObjectSimple> time2Ticker1M = new HashMap<>();
        GridObjectTestResearch simulator = null;
        for (KlineObjectNumber tickerN : tickers) {
            KlineObjectSimple ticker = Utils.convertKlineSimple(tickerN);
            long time = ticker.startTime.longValue();
            if (time == timeCheck){
                System.out.println("Debug");
            }
            time2Ticker1M.put(time, ticker);
            if (ticker.startTime.longValue() < startTime) {
                continue;
            }
            if (ticker.startTime.longValue() == startTime) {

                simulator = new GridObjectTestResearch(symbol, OrderSide.BOTH,
                        ticker.priceClose * 3, ticker.priceClose * 0.1,
                        ticker);

                if (simulator != null) {
                    if (side != null){
                        simulator.side = side;
                    }
                    simulator.initGrid();
                    LOG.info("Time create grid: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                            symbol, ticker.priceClose);
                }

            }
            if (simulator.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                if (ticker.startTime.longValue() <= simulator.tickerStart.startTime.longValue()) {
                    continue;
                }
                simulator.updateAllOrderRunning(ticker);
            } else {
                simulator.printResult();
                simulator.exportFile();
                simulator = null;
                break;
            }
        }
        if (simulator != null) {
            simulator.printResult();
            simulator.exportFile();
        }
    }

    private static void runWithGridMultiOrder() throws ParseException {
        String symbol = "BNBUSDT";
        long startTime = sdfFileHour.parse("20220428 11:00").getTime();
        OrderSide side = null;
//        side = OrderSide.BUY;
        List<KlineObjectNumber> ticker1Ds = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_1D + symbol);
        List<KlineObjectSimple> tickers = (List<KlineObjectSimple>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_1M + symbol);
        Map<Long, KlineObjectSimple> time2Ticker1M = new HashMap<>();
        GridObjectTestResearch simulator = null;
        for (KlineObjectSimple ticker : tickers) {
            long time = ticker.startTime.longValue();
            time2Ticker1M.put(time, ticker);
            if (ticker.startTime.longValue() < startTime) {
                continue;
            }
            KlineObjectSimple ticker4hAgo = time2Ticker1M.get(time - 4 * Utils.TIME_HOUR);
            Double rate4h = null;
            if (ticker4hAgo != null) {
                rate4h = Utils.rateOf2Double(ticker.priceClose, ticker4hAgo.priceOpen);
            }
            if (ticker.startTime.longValue() == startTime) {
                Double differenceMa20AndMa60 = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC
                        , ticker.startTime.longValue());
                Double difference4HMa20AndMa60 = SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC
                        , ticker.startTime.longValue());
                simulator = GridDetector.findGridSpecialSymbol(symbol, ticker, time, ticker1Ds, differenceMa20AndMa60, difference4HMa20AndMa60, rate4h);

                if (simulator != null) {
                    if (side != null){
                        simulator.side = side;
                    }
                    simulator.initGrid();
                    LOG.info("Time create grid: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker.startTime.longValue()),
                            symbol, ticker.priceClose);
                }

            }
            if (simulator.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                if (ticker.startTime.longValue() <= simulator.tickerStart.startTime.longValue()) {
                    continue;
                }
                simulator.updateAllOrderRunning(ticker);
            } else {
                simulator.printResult();
                simulator.exportFile();
                simulator = null;
                break;
            }
        }
        if (simulator != null) {
            simulator.printResult();
            simulator.exportFile();
        }
    }
}
