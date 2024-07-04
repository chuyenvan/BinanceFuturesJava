package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.btctd.BreadDetectObject;
import com.binance.chuyennd.indicators.SimpleMovingAverage1DManager;
import com.binance.chuyennd.movingaverage.MAStatus;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.educa.chuyennd.funcs.BreadFunctions;
import com.educa.chuyennd.funcs.TraderScoring;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.text.ParseException;
import java.util.ArrayList;
import java.util.List;

public class VolumeMiniRateChangeByTime {
    public static final Logger LOG = LoggerFactory.getLogger(VolumeMiniRateChangeByTime.class);
    public static Double RATE_BREAD_MIN_2TRADE = Configs.getDouble("RATE_BREAD_MIN_2TRADE");
    public final static Double RATE_MA_MAX = Configs.getDouble("RATE_MA_MAX");
    public final static Double RATE_TARGET = Configs.getDouble("RATE_TARGET");
    public final static String TIME_DETECT = Configs.getString("TIME_DETECT");

    public static void main(String[] args) throws ParseException, IOException {
        long startTime = Utils.sdfFileHour.parse(TIME_DETECT).getTime();
        printAllChange(startTime);
        System.exit(1);
    }

    private static void printAllChange(long startTime) throws IOException {
        List<String> lines = new ArrayList<>();
        int counter = 0;
        int total = new File(DataManager.FOLDER_TICKER_15M).listFiles().length;
        for (File file : new File(DataManager.FOLDER_TICKER_15M).listFiles()) {
            try {
                String symbol = file.getName();
                counter++;
                if (Constants.diedSymbol.contains(symbol) || !StringUtils.containsIgnoreCase(symbol, "usdt")) {
                    continue;
                }
                LOG.info("Process {} {}/{}", symbol, counter, total);
                List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(file.getPath());
                for (int i = 0; i < tickers.size(); i++) {
                    KlineObjectNumber kline = tickers.get(i);
                    if (kline.startTime.longValue() == startTime) {
                        BreadDetectObject breadData = BreadFunctions.calBreadDataAlt(kline, RATE_BREAD_MIN_2TRADE);
                        Double rateChange = BreadFunctions.getRateChangeWithVolume(kline.totalUsdt / 1E6);
                        if (rateChange == null) {
//                        LOG.info("Error rateChange with ticker: {} {}", symbol, Utils.toJson(kline));
                            continue;
                        }
                        SimpleMovingAverage1DManager.getInstance().updateWithTicker(symbol, kline);
                        MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(kline.startTime.longValue(), symbol);
                        Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol,
                                Utils.getDate(kline.startTime.longValue() - Utils.TIME_DAY));
                        Double rateMa = Utils.rateOf2Double(kline.priceClose, maValue);

                        if (BreadFunctions.isAvailableTrade(breadData, kline, maStatus, maValue, rateChange, rateMa, RATE_MA_MAX)) {
                            StringBuilder builder = TraderScoring.buildLineData(tickers, maValue, i, symbol, breadData, rateMa);
                            lines.add(builder.toString());

                        }
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        FileUtils.writeLines(new File(VolumeMiniRateChangeByTime.class.getSimpleName() + "-rate-ma-" + RATE_MA_MAX.toString() + ".csv"), lines);
    }


}

