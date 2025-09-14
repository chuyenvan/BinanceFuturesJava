package com.binance.chuyennd.trading;

import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.PremiumIndex;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.*;
import com.binance.client.model.market.FundingRate;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.math.BigDecimal;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class FundingFeeManagerProduction {
    public static final Logger LOG = LoggerFactory.getLogger(FundingFeeManagerProduction.class);
    private ConcurrentHashMap<String, TreeMap<Long, FundingRate>> symbol2FundingFee = new ConcurrentHashMap<>();
    public static final String FILE_DATA_FUNDING = "storage/funding/fundingData.data";
    public Set<String> fundingBuy = new HashSet<>();
    public Set<String> extremeNegative = new HashSet<>();
    public Set<String> fundingSell = new HashSet<>();
    private static volatile FundingFeeManagerProduction INSTANCE = null;

    public static FundingFeeManagerProduction getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new FundingFeeManagerProduction();
            if (new File(FILE_DATA_FUNDING).exists()) {
                INSTANCE.symbol2FundingFee = (ConcurrentHashMap<String, TreeMap<Long, FundingRate>>)
                        StorageSnappy.readObjectFromFile(FILE_DATA_FUNDING);
                INSTANCE.updateListBuySell();
            } else {
                INSTANCE.initAllFunding();
            }
            INSTANCE.startThreadUpdateData();
        }
        return INSTANCE;
    }

    public void updateListBuySell() {

        for (String symbol : symbol2FundingFee.keySet()) {
            try {
                TreeMap<Long, FundingRate> time2Rate = symbol2FundingFee.get(symbol);
                if (time2Rate != null && !time2Rate.isEmpty()) {
                    while (time2Rate.size() > Configs.NUMBER_LAST_FUNDING_CAL) {
                        time2Rate.remove(time2Rate.firstKey());
                    }
                    while (time2Rate.size() > 0 && time2Rate.firstKey() < System.currentTimeMillis() -
                            Configs.NUMBER_HOUR_FUNDING_CAL * Utils.TIME_HOUR) {
                        time2Rate.remove(time2Rate.firstKey());
                    }
                    symbol2FundingFee.put(symbol, time2Rate);
                    Boolean isFundingSell = true;
                    for (FundingRate funding : time2Rate.values()) {
                        if (funding.getFundingRate().doubleValue() < Configs.FUNDING_MAX_TRADE
                                || funding.getFundingRate().doubleValue() > Configs.FUNDING_MIN_TRADE) {
                            fundingBuy.add(symbol);
                            fundingSell.remove(symbol);
                            isFundingSell = false;
                            break;
                        }

                    }
                    while (time2Rate.size() > Configs.NUMBER_LAST_FUNDING_EXTREME) {
                        time2Rate.remove(time2Rate.firstKey());
                    }
                    for (FundingRate funding : time2Rate.values()) {
                        if (funding.getFundingRate().doubleValue() < Configs.FUNDING_MAX_TRADE_EXTREME) {
                            extremeNegative.add(symbol);
                            isFundingSell = false;
                            break;
                        }
                    }
                    if (isFundingSell) {
                        extremeNegative.remove(symbol);
                        fundingBuy.remove(symbol);
                        fundingSell.add(symbol);
                    } else {
//                        Long currentTime = System.currentTimeMillis();
//                        StringBuilder builder = new StringBuilder();
//                        for (Long time : time2Rate.keySet()) {
//                            builder.append(Utils.normalizeDateYYYYMMDDHHmm(time)).append(" ").
//                                    append(time2Rate.get(time).getFundingRate()).append(" ");
//                        }
//                        LOG.info("Update funding buy: {} {} {} ", symbol, Utils.normalizeDateYYYYMMDDHHmm(currentTime),
//                                builder);
                    }
                }
            } catch (Exception e) {
                LOG.info("Error update list sell/buy funding fee: {}", symbol);
                e.printStackTrace();
            }
        }
        LOG.info("Total funding fee buy: {}", fundingBuy.size());
    }

    private void initAllFunding() {
        LOG.info("Init all funding. {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS)) {
            getFundingBySymbol(symbol);
        }
        StorageSnappy.writeObject2File(FILE_DATA_FUNDING, symbol2FundingFee);
    }

    public void getFundingBySymbol(String symbol) {
        try {
            long time = System.currentTimeMillis() - Configs.NUMBER_HOUR_FUNDING_CAL * Utils.TIME_HOUR;
            TreeMap<Long, FundingRate> time2Rate = TickerFuturesHelper.getFundingFeeWithStartTime(symbol, time);
            if (time2Rate != null && !time2Rate.isEmpty()) {
                while (time2Rate.size() > Configs.NUMBER_LAST_FUNDING_CAL) {
                    time2Rate.remove(time2Rate.firstKey());
                }
                symbol2FundingFee.put(symbol, time2Rate);
            }
        } catch (Exception e) {
            LOG.info("Error get funding rate for : {}", symbol);
            e.printStackTrace();
        }
    }

    public static void main(String[] args) throws ParseException {
        TreeMap<Long, FundingRate> time2Rate = FundingFeeManagerProduction.getInstance().symbol2FundingFee.get("MITOUSDT");
        for (Long time : time2Rate.keySet()) {
            LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(time), time2Rate.get(time).getFundingRate());
        }
//        long time = Utils.sdfFileHour.parse("20250830 23:14").getTime();
//        System.out.println(FundingFeeManagerProduction.getInstance().getExtremeNegativeFundingSymbols(time));
//        for (String symbol : FundingFeeManagerProduction.getInstance().symbol2FundingFee.keySet()) {
//            TreeMap<Long, FundingRate> time2Rate = FundingFeeManagerProduction.getInstance().symbol2FundingFee.get(symbol);
//            for (Long time : time2Rate.keySet()) {
//                if (Math.abs(time2Rate.get(time).getFundingRate().doubleValue()) >= 0.02) {
//                    LOG.info("{} {} {}",symbol, Utils.normalizeDateYYYYMMDDHHmm(time), time2Rate.get(time).getFundingRate());
//                }
//            }
//        }
//        LOG.info("size: ------------------------------ {} {}", FundingFeeManagerProduction.getInstance().fundingBuy.size(),
//                FundingFeeManagerProduction.getInstance().symbol2FundingFee.size());
    }


    private void startThreadUpdateData() {
        new Thread(() -> {
            Thread.currentThread().setName("FundingFeeManagerProduction2025");
            LOG.info("Start thread FundingFeeManagerProduction2025!");
            while (true) {
                try {
                    updateAllFunding();
                    Thread.sleep(5 * Utils.TIME_MINUTE);
                    if (Utils.getCurrentMinute() < 5) {
                        initAllFunding();
                        StorageSnappy.writeObject2File(FILE_DATA_FUNDING, symbol2FundingFee);
                    }
                } catch (Exception e) {
                    LOG.error("ERROR during FundingFeeManagerProduction {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void updateAllFunding() {
        try {
            String respon = HttpRequest.getContentFromUrl(Configs.URL_PREMIUM_INDEX);
            List<Object> objects = Utils.gson.fromJson(respon, List.class);
            for (Object object : objects) {
                PremiumIndex data = Utils.gson.fromJson(object.toString(), PremiumIndex.class);
                if (StringUtils.endsWithIgnoreCase(data.symbol, "usdt")) {
                    try {
                        String symbol = data.symbol;
                        TreeMap<Long, FundingRate> time2Funding = symbol2FundingFee.get(symbol);
                        if (time2Funding != null && !time2Funding.isEmpty()) {
                            time2Funding.lastEntry().getValue().setFundingRate(new BigDecimal(data.lastFundingRate));
                        } else {
                            if (RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS, symbol) != null) {
                                time2Funding = new TreeMap<>();
                                time2Funding.put(Utils.get4Hour(System.currentTimeMillis()), new FundingRate());
                                time2Funding.lastEntry().getValue().setFundingRate(new BigDecimal(data.lastFundingRate));
                                LOG.info("Add new funding: {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
                                symbol2FundingFee.put(symbol, time2Funding);
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
        updateListBuySell();
    }

}
