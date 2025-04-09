package com.binance.chuyennd.grid;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static com.binance.chuyennd.utils.Utils.sdfFileHour;

public class RunAOrderQuickly {
    public static final Logger LOG = LoggerFactory.getLogger(RunAOrderQuickly.class);

    public static void main(String[] args) throws ParseException {
        runWithGridOnlyAnOrder();
    }

    private static void runWithGridOnlyAnOrder() throws ParseException {
        String symbol = "ETHUSDT";
        long startTime = sdfFileHour.parse("20211109 21:40").getTime();
        OrderSide side = null;
//        side = OrderSide.BUY;
        List<KlineObjectSimple> tickers = (List<KlineObjectSimple>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_1M + symbol);
        Map<Long, KlineObjectSimple> time2Ticker1M = new HashMap<>();
        OrderTargetInfoTest simulator = null;
        for (KlineObjectSimple ticker : tickers) {
            long time = ticker.startTime.longValue();
            time2Ticker1M.put(time, ticker);
            if (ticker.startTime.longValue() < startTime) {
                continue;
            }
            if (ticker.startTime.longValue() == startTime) {

                Double entry = ticker.priceClose;
                Double budget = BudgetManagerSimple.getInstance().getBudget();
                Integer leverage = BudgetManagerSimple.getInstance().getLeverage();
                Double quantity = Utils.calQuantityTest(budget, leverage, entry, symbol);
                simulator = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, entry, null, quantity,
                        leverage, symbol, ticker.startTime.longValue(), ticker.startTime.longValue(), OrderSide.BOTH);
                simulator.minPrice = entry;
                simulator.lastPrice = entry;
                simulator.maxPrice = entry;
                simulator.tickerOpen = Utils.convertKlineSimple(ticker);

            }
            if (simulator.status.equals(OrderTargetStatus.REQUEST)) {
                if (ticker.startTime.longValue() <= simulator.timeStart) {
                    continue;
                }
                simulator.updatePriceByKlineSimple(ticker);
                Double rateMin = 0d;
                simulator.updateStatusNew();
                simulator.updateFundingFee(ticker.startTime.longValue() + Utils.TIME_MINUTE);
                if (simulator.status.equals(OrderTargetStatus.TAKE_PROFIT_DONE)
                        || simulator.status.equals(OrderTargetStatus.STOP_LOSS_DONE)
                        || simulator.status.equals(OrderTargetStatus.STOP_MARKET_DONE)) {
                    LOG.info("Order done: {}\t{}\t{}\t{} -> {}\t{}%\t{} {}", simulator.side, simulator.symbol, Utils.normalizeDateYYYYMMDDHHmm(simulator.timeStart),
                            simulator.priceEntry, simulator.priceTP, Utils.formatPercent(Utils.rateOf2Double(simulator.priceTP, simulator.priceEntry)),
                            simulator.status, simulator.calProfit());
                } else {
                    simulator.updateTPSL();
                }
            } else {
                simulator = null;
                break;
            }
        }
        if (simulator != null) {
            simulator.priceTP = simulator.lastPrice;
            LOG.info("Order running: {}\t{}\t{}\t{} -> {}\t{}%\t{} {}", simulator.side, simulator.symbol, Utils.normalizeDateYYYYMMDDHHmm(simulator.timeStart),
                    simulator.priceEntry, simulator.priceTP, Utils.formatPercent(Utils.rateOf2Double(simulator.priceTP, simulator.priceEntry)),
                    simulator.status, simulator.calProfit());
        }
    }
}
