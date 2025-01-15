package com.binance.chuyennd.research;

import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class FundingFeeManager {
    public static final Logger LOG = LoggerFactory.getLogger(FundingFeeManager.class);
    private ConcurrentHashMap<String, TreeMap<Long, Double>> symbol2FundingFee = new ConcurrentHashMap<>();
    private static volatile FundingFeeManager INSTANCE = null;

    public static FundingFeeManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new FundingFeeManager();
        }
        return INSTANCE;
    }

    public static void main(String[] args) {
        try {
            String symbol = "MOVEUSDT";
            long time = Utils.sdfFileHour.parse("20241210 15:00").getTime();
            Double fundingFee = FundingFeeManager.getInstance().getFundingFee(symbol, time);
            System.out.println(fundingFee);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public Double getFundingFee(String symbol, long time) {
        TreeMap<Long, Double> time2RateFunding = symbol2FundingFee.get(symbol);
        if (time2RateFunding == null) {
            time2RateFunding = (TreeMap<Long, Double>) Storage.readObjectFromFile(Configs.FOLDER_FUNDING_FEE + symbol);
        }
        if (time2RateFunding != null) {
            symbol2FundingFee.put(symbol, time2RateFunding);
            return time2RateFunding.get(time);
        }
        return null;
    }
    public TreeMap<Double, String> getTopFundingFee(Long time, Set<String> allSymbols) {
        TreeMap<Double, String> funding2Symbol = new TreeMap<>();
        if (time % (4 * Utils.TIME_HOUR) == 0) {
            for (String symbol : allSymbols) {
                Double funding = FundingFeeManager.getInstance().getFundingFee(symbol, time);
                if (funding != null) {
                    funding2Symbol.put(funding, symbol);
                }
            }
        }
        return funding2Symbol;
    }
}
