package com.binance.chuyennd.trading.grid;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.indicators.SimpleMovingAverage;
import com.binance.chuyennd.object.IndicatorEntry;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.PremiumIndex;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.GridConfigs;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class FundingFeeManagerProduction {
    public static final Logger LOG = LoggerFactory.getLogger(FundingFeeManagerProduction.class);
    public TreeMap<Double, String> funding2Symbol = new TreeMap<>();
    public Set<String> fundingBuy = new HashSet<>();
    public Set<String> fundingSell = new HashSet<>();
    private static volatile FundingFeeManagerProduction INSTANCE = null;

    public static FundingFeeManagerProduction getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new FundingFeeManagerProduction();
            INSTANCE.updateAllSymbol();
            INSTANCE.startThreadUpdateData();
        }
        return INSTANCE;
    }

    public static void main(String[] args) throws ParseException {
        System.out.println(Utils.toJson(FundingFeeManagerProduction.getInstance().fundingBuy));
    }


    private void startThreadUpdateData() {
        new Thread(() -> {
            Thread.currentThread().setName("FundingFeeManagerProduction");
            LOG.info("Start thread FundingFeeManagerProduction!");
            while (true) {
                try {
                    Thread.sleep(15 * Utils.TIME_MINUTE);
                    updateAllSymbol();
                } catch (Exception e) {
                    LOG.error("ERROR during FundingFeeManagerProduction {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void updateAllSymbol() {
        try {
            String respon = HttpRequest.getContentFromUrl(Configs.URL_PREMIUM_INDEX);
            List<Object> objects = Utils.gson.fromJson(respon, List.class);
            for (Object object : objects) {
                PremiumIndex data = Utils.gson.fromJson(object.toString(), PremiumIndex.class);
                if (StringUtils.endsWithIgnoreCase(data.symbol, "usdt")) {
                    try {
                        double funding = Double.parseDouble(data.lastFundingRate);
                        funding2Symbol.put(funding, data.symbol);
                        if (funding < 0) {
                            fundingBuy.add(data.symbol);
                            fundingSell.remove(data.symbol);
                        } else {
                            fundingBuy.remove(data.symbol);
                            if (funding > 0.001) {
                                fundingSell.add(data.symbol);
                            }
                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
            }
        } catch (Exception e) {
            LOG.info("Error during get all premium index!");
            e.printStackTrace();
        }
    }
}
