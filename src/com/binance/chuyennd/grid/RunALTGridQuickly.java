package com.binance.chuyennd.grid;

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
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static com.binance.chuyennd.utils.Utils.sdfFileHour;

public class RunALTGridQuickly {
    public static final Logger LOG = LoggerFactory.getLogger(RunALTGridQuickly.class);

    public static void main(String[] args) throws ParseException {
//        runWithGridMultiOrder();
        runWithGridOnlyAnOrder();

    }

    private static void runWithGridOnlyAnOrder() throws ParseException {
        String symbol = "ETHUSDT";
        long startTime = sdfFileHour.parse("20211109 21:40").getTime();
        OrderSide side = null;
        side = OrderSide.BUY;
        List<KlineObjectSimple> tickers = (List<KlineObjectSimple>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_1M + symbol);
        Map<Long, KlineObjectSimple> time2Ticker1M = new HashMap<>();
        GridObjectALTResearch simulator = null;
        for (KlineObjectSimple ticker : tickers) {
            long time = ticker.startTime.longValue();
            time2Ticker1M.put(time, ticker);
            if (ticker.startTime.longValue() < startTime) {
                continue;
            }
            if (ticker.startTime.longValue() == startTime) {

                simulator = new GridObjectALTResearch(symbol, OrderSide.SELL, ticker.priceOpen * 1.1, ticker.priceClose * 0.5, ticker);

                if (simulator != null) {
                    if (side != null) {
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
                simulator.updateGridWithMaBtc(ticker);
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
                    if (side != null) {
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
