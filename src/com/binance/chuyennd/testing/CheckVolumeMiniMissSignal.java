package com.binance.chuyennd.testing;

import com.binance.chuyennd.bigchange.statistic.BreadDetectObject;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.indicators.SimpleMovingAverage1DManager;
import com.binance.chuyennd.movingaverage.MAStatus;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.educa.chuyennd.funcs.BreadProductFunctions;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * @author pc
 */
public class CheckVolumeMiniMissSignal {

    public static final Logger LOG = LoggerFactory.getLogger(CheckVolumeMiniMissSignal.class);

    public Double RATE_BREAD_MIN_2TRADE = Configs.getDouble("RATE_BREAD_MIN_2TRADE");
    public final Double RATE_MA_MAX = Configs.getDouble("RATE_MA_MAX");


    private void printAllSignalByTime(Long startTime) {
        Map<String, List<KlineObjectNumber>> symbol2Tickers = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_15M, startTime);
        printAllSignalByTickers(symbol2Tickers);
    }

    void printAllSignalByTickers(Map<String, List<KlineObjectNumber>> allSymbolTickers) {
        TreeMap<Long, String> time2BigInfo = new TreeMap<>();
        int counter = 0;
        for (String symbol : allSymbolTickers.keySet()) {
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            try {
                List<KlineObjectNumber> tickers = allSymbolTickers.get(symbol);
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
                    BreadDetectObject breadData = BreadProductFunctions.calBreadDataAlt(kline, RATE_BREAD_MIN_2TRADE);
                    Double rateChange = BreadProductFunctions.getRateChangeWithVolume(kline.totalUsdt / 1E6);
                    MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(kline.startTime.longValue(), symbol);
                    Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol, Utils.getDate(kline.startTime.longValue()));
                    Double rateMa = Utils.rateOf2Double(kline.priceClose, maValue);

                    if (breadData.orderSide != null
                            && breadData.orderSide.equals(OrderSide.BUY)
                            && maStatus != null && maStatus.equals(MAStatus.TOP)
                            && rateMa < RATE_MA_MAX
                            && breadData.totalRate >= rateChange) {
                        counter++;
                        String log = symbol + "\t";
                        log += "\t" + Utils.normalizeDateYYYYMMDDHHmm(kline.startTime.longValue());
                        log += "\t" + breadData.rateChange;
                        log += "/" + breadData.totalRate;
                        log += "\t" + kline.totalUsdt;
                        log += "\t" + rateMa;
                        log += "\t" + maStatus;
                        time2BigInfo.put(kline.startTime.longValue() + counter, log);
                    }
                }

            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        for (Map.Entry<Long, String> entry : time2BigInfo.entrySet()) {
            Long time = entry.getKey();
            String value = entry.getValue();
            LOG.info(value);
        }

    }

    public static void main(String[] args) throws ParseException {
        new CheckVolumeMiniMissSignal().printAllSignalByTime(Utils.sdfFileHour.parse("20240507 00:00").getTime());
    }

}
