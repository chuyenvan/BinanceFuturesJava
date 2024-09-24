package com.binance.chuyennd.trading;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;

public class MarketBigChangeDetector {
    public static final Logger LOG = LoggerFactory.getLogger(MarketBigChangeDetector.class);
    public static final String TIME_RUN = Configs.getString("TIME_RUN");

    public static void main(String[] args) throws ParseException {
        System.exit(1);
    }

    public static List<String> getTopSymbol2TradeWithRateChange(Map<String, KlineObjectNumber> value, int period, Set<String> symbolsRunning) {
        TreeMap<Double, String> rateChange2Symbols = new TreeMap<>();
        for (Map.Entry<String, KlineObjectNumber> entry1 : value.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectNumber ticker = entry1.getValue();
            if (Utils.isTickerAvailable(ticker)) {
                Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
                rateChange2Symbols.put(rateChange, symbol);
            }
        }

        return getTopSymbol(rateChange2Symbols, period, symbolsRunning);
    }

    public static boolean isBtcReverse(List<KlineObjectNumber> btcTickers) {
        int period = 15;
        int index = btcTickers.size() - 1;
        if (index < period + 3) {
            return false;
        }
        KlineObjectNumber lastTicker = btcTickers.get(index);
        Double volumeTotal = 0d;
        for (int i = 3; i < period + 3; i++) {
            KlineObjectNumber ticker = btcTickers.get(index - i);
            volumeTotal += ticker.totalUsdt;
        }
        double volumeAvg = volumeTotal / period;
        Double rateBtc = Utils.rateOf2Double(lastTicker.priceClose, lastTicker.priceOpen);
        LOG.info("Check btc reverse: {} {} {}% {}", Utils.normalizeDateYYYYMMDDHHmm(lastTicker.startTime.longValue()),
                lastTicker.priceClose, Utils.formatDouble(rateBtc * 100, 2), lastTicker.totalUsdt / volumeAvg);
        if (lastTicker.totalUsdt > 10 * volumeAvg
                && rateBtc < -0.003
        ) {
            return true;
        }
        return false;
    }

    public static MarketLevelChange detectLevelChangeProduction1M(Map<String, KlineObjectNumber> entry) {
        TreeMap<Double, String> rateDown2Symbols = new TreeMap<>();
        TreeMap<Double, String> rateUp2Symbols = new TreeMap<>();

        for (Map.Entry<String, KlineObjectNumber> entry1 : entry.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectNumber ticker = entry1.getValue();
            Double rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);
            rateDown2Symbols.put(rateChange, symbol);
            rateUp2Symbols.put(-rateChange, symbol);
        }
        Double rateDownAvg = calRateChangeAvg(rateDown2Symbols, 50);
        Double rateUpAvg = -calRateChangeAvg(rateUp2Symbols, 50);
        KlineObjectNumber btcTicker = entry.get(Constants.SYMBOL_PAIR_BTC);
        Double btcRateChange = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
        LOG.info("Check level market: {} DownAvg: {}% UpAvg:{}% btcRate: {}%", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()),
                Utils.formatDouble(rateDownAvg * 100, 2), Utils.formatDouble(rateUpAvg * 100, 2),
                Utils.formatDouble(btcRateChange * 100, 2));

        return getMarketStatus1M(rateDownAvg, rateUpAvg, btcRateChange);
    }


    public static List<String> getTopSymbol(TreeMap<Double, String> rateLoss2Symbols, int period, Set<String> symbolsRunning) {
        List<String> symbols = new ArrayList<>();
        for (Map.Entry<Double, String> entry : rateLoss2Symbols.entrySet()) {
            if (symbolsRunning.contains(entry.getValue())) {
                continue;
            }
            if (!Constants.specialSymbol.contains(entry.getValue())) {
                symbols.add(entry.getValue());
            }
            if (symbols.size() >= period) {
                break;
            }
        }
        return symbols;
    }


    public static Double calRateChangeAvg(TreeMap<Double, String> rateLoss2Symbols, Integer period) {
        Double total = 0d;
        int counter = 0;
        for (Map.Entry<Double, String> entry : rateLoss2Symbols.entrySet()) {
            Double key = entry.getKey();
            counter++;
            if (period != null && counter >= period) {
                break;
            }
            total += key;
        }
        if (rateLoss2Symbols.isEmpty()) {
            return 0d;
        }
        return total / counter;
    }

    public static MarketLevelChange getMarketStatus15M(Double rateDown15MAvg, Double rateUp15MAvg, Double rateUpAvg) {

        if (rateDown15MAvg < -0.055) {
            return MarketLevelChange.MEDIUM_DOWN;
        }
        if (rateDown15MAvg < -0.03) {
            return MarketLevelChange.SMALL_DOWN_15M;
        }
        if (rateUp15MAvg > 0.04) {
            return MarketLevelChange.BIG_UP_15M;
        }
        if (rateUp15MAvg > 0.035 && rateUpAvg > 0.008) {
            return MarketLevelChange.SMALL_UP_15M;
        }
        return null;
    }

    public static MarketLevelChange getMarketStatus1M(Double rateDownAvg, Double rateUpAvg, Double btcRateChange) {
        if (rateDownAvg < -0.035
                && rateUpAvg < -0.01
                && btcRateChange < -0.005) {
            return MarketLevelChange.BIG_DOWN;
        }
        if (rateDownAvg < -0.011
                || (rateDownAvg < -0.008 && btcRateChange < -0.006)
        ) {
            return MarketLevelChange.MEDIUM_DOWN;
        }

        if (rateDownAvg > 0.01
                && rateUpAvg > 0.04) {
            return MarketLevelChange.BIG_UP;
        }
        if (rateUpAvg > 0.015) {
            return MarketLevelChange.MEDIUM_UP;
        }
        if (rateUpAvg > 0.0135
                || (rateUpAvg > 0.009 && btcRateChange > 0.01)) {
            return MarketLevelChange.SMALL_UP;
        }

        return null;
    }

}
