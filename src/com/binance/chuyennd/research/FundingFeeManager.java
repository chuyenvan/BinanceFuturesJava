package com.binance.chuyennd.research;

import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.market.FundingRate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.HashSet;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class FundingFeeManager {
    public static final Logger LOG = LoggerFactory.getLogger(FundingFeeManager.class);
    private ConcurrentHashMap<String, TreeMap<Long, FundingRate>> symbol2FundingFee = new ConcurrentHashMap<>();
    private static volatile FundingFeeManager INSTANCE = null;

    public static FundingFeeManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new FundingFeeManager();
            INSTANCE.initData();
        }
        return INSTANCE;
    }

    private void initData() {
        try {
            for (File file : new File(Configs.FOLDER_FUNDING_FEE).listFiles()) {
                try {
                    String symbol = file.getName();
                    TreeMap<Long, FundingRate> time2RateFunding = symbol2FundingFee.get(symbol);
                    if (time2RateFunding == null) {
                        time2RateFunding = (TreeMap<Long, FundingRate>) Storage.readObjectFromFile(Configs.FOLDER_FUNDING_FEE + symbol);
                    }
                    if (time2RateFunding != null) {
                        symbol2FundingFee.put(symbol, time2RateFunding);
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
            LOG.info("Init funding fee: {} symbols", symbol2FundingFee.size());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void main(String[] args) {
        try {
            long time = Utils.sdfFileHour.parse("20250509 05:11").getTime();
//            LOG.info("{}", Utils.normalizeDateYYYYMMDDHHmm(Utils.get2Hour(time)));
//            LOG.info("{}", Utils.normalizeDateYYYYMMDDHHmm(Utils.get4Hour(time)));
//            FundingFeeManager.getInstance().printLastFunding("HIPPOUSDT");
            FundingFeeManager.getInstance().getFundingBuyNew(time);
//            FundingFeeManager.getInstance().printLastFunding();


//            String symbol = "TRBUSDT";
//            long time = Utils.sdfFileHour.parse("20230829 15:00").getTime();
//            long endTime = Utils.sdfFileHour.parse("20240306 02:57").getTime();

//            OrderTargetInfoTest orderTrade = new OrderTargetInfoTest(OrderTargetStatus.REQUEST, 0.0334,
//                    0.0336, 1.8, 5, symbol, time,
//                    endTime, OrderSide.BUY, Constants.TRADING_TYPE_VOLUME_MINI);
//            orderTrade.lastPrice = 84.0;
//            orderTrade.updateFundingFee();
//            orderTrade.printFundingFee();
//            System.out.println(orderTrade.calFundingFee());
//            Double fundingFee = FundingFeeManager.getInstance().getFundingFee(symbol, Utils.get4Hour(time));
//            if (fundingFee == null) {
//                fundingFee = FundingFeeManager.getInstance().getFundingFee(symbol, Utils.get4Hour(time) - 4 * Utils.TIME_HOUR);
//            }
//            LOG.info("{}", FundingFeeManager.getInstance().getFundingBuy(time));
//            System.out.println(fundingFee);
//            TreeMap<Long, FundingRate> fundingFee = FundingFeeManager.getInstance().getFundingFeeByTime(symbol, time , time + Utils.TIME_DAY);
//            if (fundingFee != null) {
//                for (Long t: fundingFee.keySet()){
//                    LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(t), Utils.toJson(fundingFee.get(t)));
//                }
//            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void printLastFunding() {
        for (String symbol : symbol2FundingFee.keySet()) {
            TreeMap<Long, FundingRate> time2Funding = symbol2FundingFee.get(symbol);
            int counter = 0;
            for (Long time : time2Funding.descendingKeySet()) {
                LOG.info("{} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), time2Funding.get(time).getFundingRate());
                counter++;
                if (counter > 3) {
                    break;
                }
            }
        }
    }

    private void printLastFunding(String symbol) {

        TreeMap<Long, FundingRate> time2Funding = symbol2FundingFee.get(symbol);
        int counter = 0;
        for (Long time : time2Funding.descendingKeySet()) {
            LOG.info("{} {} {} {}", symbol, time, Utils.normalizeDateYYYYMMDDHHmmss(time), time2Funding.get(time).getFundingRate());
            counter++;
            if (counter > 3) {
                break;
            }
        }

    }

    public Double getFundingFee(String symbol, long time) {
        TreeMap<Long, FundingRate> time2RateFunding = symbol2FundingFee.get(symbol);
        if (time2RateFunding == null) {
            time2RateFunding = (TreeMap<Long, FundingRate>) Storage.readObjectFromFile(Configs.FOLDER_FUNDING_FEE + symbol);
        }
        if (time2RateFunding != null) {
//            LOG.info("last funding: {} {}", Utils.normalizeDateYYYYMMDDHHmm(time2RateFunding.lastKey()), time2RateFunding.lastEntry().getValue());
            symbol2FundingFee.put(symbol, time2RateFunding);
            if (time2RateFunding.get(time) != null) {
                return time2RateFunding.get(time).getFundingRate().doubleValue();
            }
        }
        return null;
    }

    public TreeMap<Long, FundingRate> getFullFundingFee(String symbol) {
        TreeMap<Long, FundingRate> time2RateFunding = symbol2FundingFee.get(symbol);
        if (time2RateFunding == null) {
            time2RateFunding = (TreeMap<Long, FundingRate>) Storage.readObjectFromFile(Configs.FOLDER_FUNDING_FEE + symbol);
        }
        if (time2RateFunding != null) {
            symbol2FundingFee.put(symbol, time2RateFunding);
            return time2RateFunding;
        }
        return null;
    }

    public TreeMap<Long, FundingRate> getFundingFeeByTime(String symbol, long startTime, long endTime) {
        TreeMap<Long, FundingRate> time2RateFunding = symbol2FundingFee.get(symbol);
        if (time2RateFunding == null) {
            time2RateFunding = (TreeMap<Long, FundingRate>) Storage.readObjectFromFile(Configs.FOLDER_FUNDING_FEE + symbol);
        }
        if (time2RateFunding != null) {
            symbol2FundingFee.put(symbol, time2RateFunding);
            TreeMap<Long, FundingRate> results = new TreeMap<>();
            for (Long time : time2RateFunding.keySet()) {
                if (time <= startTime) {
                    continue;
                }
                if (time > endTime) {
                    break;
                }
                results.put(time, time2RateFunding.get(time));
            }
            return results;
        }
        return null;
    }



    public Set<String> getFundingBuyNew(long time) {
        Set<String> symbols = new HashSet();
        long timeGet = Utils.getHour(time);
        for (String symbol : symbol2FundingFee.keySet()) {
            TreeMap<Long, FundingRate> time2Funding = symbol2FundingFee.get(symbol);
            TreeMap<Long, FundingRate> time2FundingGet = new TreeMap<>();
            for (int i = 0; i < 20; i++) {
                Long timeF = timeGet - i * Utils.TIME_HOUR;
                if (time2Funding.containsKey(timeF)) {
                    time2FundingGet.put(timeF, time2Funding.get(timeF));
                }
                if (time2FundingGet.size() >= 3) {
                    break;
                }
            }
            for (FundingRate funding : time2FundingGet.values()) {
                if (funding.getFundingRate().doubleValue() < 0.00) {
                    symbols.add(symbol);
                }
            }
            StringBuilder builder = new StringBuilder();
            for (Long key : time2FundingGet.keySet()) {
                builder.append(Utils.normalizeDateYYYYMMDDHHmm(key)).append(" ").append(time2FundingGet.get(key).getFundingRate()).append(" ");
            }
//            LOG.info("{} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), builder);

        }
        return symbols;
    }

    public Set<String> getFundingBuySpecial(long time) {
        Set<String> symbols = new HashSet();
        long timeGet = Utils.getHour(time);
        for (String symbol : symbol2FundingFee.keySet()) {
            TreeMap<Long, FundingRate> time2Funding = symbol2FundingFee.get(symbol);
            TreeMap<Long, FundingRate> time2FundingGet = new TreeMap<>();
            for (int i = 0; i < 20; i++) {
                Long timeF = timeGet - i * Utils.TIME_HOUR;
                if (time2Funding.containsKey(timeF)) {
                    time2FundingGet.put(timeF, time2Funding.get(timeF));
                }
                if (time2FundingGet.size() == 2) {
                    break;
                }
            }

            for (FundingRate funding : time2FundingGet.values()) {
                if (funding.getFundingRate().doubleValue() < -0.005) {
                    symbols.add(symbol);
                }
            }
            StringBuilder builder = new StringBuilder();
            for (Long key : time2FundingGet.keySet()) {
                builder.append(Utils.normalizeDateYYYYMMDDHHmm(key)).append(" ").append(time2FundingGet.get(key).getFundingRate()).append(" ");
            }
//            LOG.info("{} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), builder);

        }
        return symbols;
    }


    public Set<String> getFundingSell(long time) {
        Set<String> symbols = new HashSet();
        long timeGet = Utils.getHour(time);
        for (String symbol : symbol2FundingFee.keySet()) {
            TreeMap<Long, FundingRate> time2Funding = symbol2FundingFee.get(symbol);
            TreeMap<Long, FundingRate> time2FundingGet = new TreeMap<>();
            for (int i = 0; i < 50; i++) {
                Long timeF = timeGet - i * Utils.TIME_HOUR;
                if (time2Funding.containsKey(timeF)) {
                    time2FundingGet.put(timeF, time2Funding.get(timeF));
                }
                if (time2FundingGet.size() == 2) {
                    break;
                }
            }

            for (FundingRate funding : time2FundingGet.values()) {
                if (funding.getFundingRate().doubleValue() >= 0.00005) {
                    symbols.add(symbol);
                }
            }
            StringBuilder builder = new StringBuilder();
            for (Long key : time2FundingGet.keySet()) {
                builder.append(Utils.normalizeDateYYYYMMDDHHmm(key)).append(" ");
            }
//            LOG.info("{} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), builder.toString());

        }
        return symbols;
    }

    public TreeMap<Double, String> getTopDownFundingFee(Long time, Set<String> allSymbols) {
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

    public TreeMap<Double, String> getTopDownFundingFee(Long time) {
        TreeMap<Double, String> funding2Symbol = new TreeMap<>();
        if (time % (4 * Utils.TIME_HOUR) == 0) {
            for (String symbol : symbol2FundingFee.keySet()) {
                Double funding = FundingFeeManager.getInstance().getFundingFee(symbol, time);
                if (funding != null) {
                    funding2Symbol.put(funding, symbol);
                }
            }
        }
        return funding2Symbol;
    }

    public TreeMap<Long, FundingRate> getFundingOfSym(String symbol) {
        return symbol2FundingFee.get(symbol);
    }

    public Set<String> getAllSymbolFunding() {
        return symbol2FundingFee.keySet();
    }
}
