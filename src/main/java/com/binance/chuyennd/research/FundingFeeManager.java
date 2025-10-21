package com.binance.chuyennd.research;

import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
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
    public static final String FILE_FUNGDING_FEE = "storage/fundingfee_time.data";
    public static final String FILE_FUNGDING_FEE_EXTREME = "storage/fundingfee_time_extreme.data";
    public static final String FILE_FUNGDING_FEE_EXTREME_EX = "storage/fundingfee_time_extreme_extend.data";
    public ConcurrentHashMap<Long, Set<String>> time2FundingFeeTrade;
    public ConcurrentHashMap<Long, Set<String>> time2FundingFeeExtremeTrade;
    public ConcurrentHashMap<Long, Set<String>> time2FundingFeeExtremeExtendTrade;
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
            if (new File(FILE_FUNGDING_FEE).exists()) {
                time2FundingFeeTrade = (ConcurrentHashMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(FILE_FUNGDING_FEE);
            } else {
                time2FundingFeeTrade = new ConcurrentHashMap<>();
            }
            if (new File(FILE_FUNGDING_FEE_EXTREME).exists()) {
                time2FundingFeeExtremeTrade = (ConcurrentHashMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(FILE_FUNGDING_FEE_EXTREME);
            } else {
                time2FundingFeeExtremeTrade = new ConcurrentHashMap<>();
            }
            if (new File(FILE_FUNGDING_FEE_EXTREME_EX).exists()) {
                time2FundingFeeExtremeExtendTrade = (ConcurrentHashMap<Long, Set<String>>) StorageSnappy.readObjectFromFile(FILE_FUNGDING_FEE_EXTREME_EX);
            } else {
                time2FundingFeeExtremeExtendTrade = new ConcurrentHashMap<>();
            }
            LOG.info("Init funding fee: {} symbols", symbol2FundingFee.size());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void writeData2File() {
        try {
            StorageSnappy.writeObject2File(FILE_FUNGDING_FEE, time2FundingFeeTrade);
            StorageSnappy.writeObject2File(FILE_FUNGDING_FEE_EXTREME, time2FundingFeeExtremeTrade);
            StorageSnappy.writeObject2File(FILE_FUNGDING_FEE_EXTREME_EX, time2FundingFeeExtremeExtendTrade);
        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    public static void main(String[] args) {
        try {
//            long time = Utils.sdfFileHour.parse("20250705 05:11").getTime();
//            LOG.info("{}", Utils.normalizeDateYYYYMMDDHHmm(Utils.get2Hour(time)));
//            LOG.info("{}", Utils.normalizeDateYYYYMMDDHHmm(Utils.get4Hour(time)));
            FundingFeeManager.getInstance().printLastFunding("MITOUSDT");
//            for (String symbol : FundingFeeManager.getInstance().symbol2FundingFee.keySet()) {
//                TreeMap<Long, FundingRate> time2Rate = FundingFeeManager.getInstance().symbol2FundingFee.get(symbol);
//                for (Long time : time2Rate.keySet()) {
//                    if (Math.abs(time2Rate.get(time).getFundingRate().doubleValue()) >= 0.02) {
//                        LOG.info("{} {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), time2Rate.get(time).getFundingRate(),
//                                time2Rate.get(time).getMarkPrice().doubleValue());
//                    }
//                }
//            }
//            Set<String> symbolAllFunding = FundingFeeManager.getInstance().getAllFunding(time);
//            Set<String> symbolFundingBuy = FundingFeeManager.getInstance().getFundingBuyNew(time);
//            TreeMap<Double, String> symbolFundingBig = FundingFeeManager.getInstance().getFundingBig(time);
//            LOG.info("{} {} {} {}", symbolAllFunding.size(), symbolFundingBuy.size(),
//                    symbolFundingBuy.size() * 100 / symbolAllFunding.size(), symbolFundingBig);
//            FundingFeeManager.getInstance().getFundingBuyNew(time);
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
        long timeGet = Utils.getHour(time);
        if (time2FundingFeeTrade.containsKey(timeGet)) {
            return time2FundingFeeTrade.get(timeGet);
        } else {
            Set<String> symbols = new HashSet();
            for (String symbol : symbol2FundingFee.keySet()) {
                TreeMap<Long, FundingRate> time2Funding = symbol2FundingFee.get(symbol);
                TreeMap<Long, FundingRate> time2FundingGet = new TreeMap<>();
                for (int i = 0; i < Configs.NUMBER_HOUR_FUNDING_CAL; i++) {
                    Long timeF = timeGet - i * Utils.TIME_HOUR;
                    if (time2Funding.containsKey(timeF)) {
                        time2FundingGet.put(timeF, time2Funding.get(timeF));
                    }
                    if (time2FundingGet.size() >= Configs.NUMBER_LAST_FUNDING_CAL) {
                        break;
                    }
                }
                for (FundingRate funding : time2FundingGet.values()) {
                    if (funding.getFundingRate().doubleValue() < Configs.FUNDING_MAX_TRADE
                            || funding.getFundingRate().doubleValue() > Configs.FUNDING_MIN_TRADE
                    ) {
                        symbols.add(symbol);
                    }
                }
                StringBuilder builder = new StringBuilder();
                for (Long key : time2FundingGet.keySet()) {
                    builder.append(Utils.normalizeDateYYYYMMDDHHmm(key)).append(" ").append(time2FundingGet.get(key).getFundingRate()).append(" ");
                }
//            LOG.info("{} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), builder);

            }
            time2FundingFeeTrade.put(timeGet, symbols);
            return symbols;
        }
    }


    public Set<String> getExtremeNegativeExtendFundingSymbols(long time) {
        long timeGet = Utils.getHour(time);
        if (time2FundingFeeExtremeExtendTrade.containsKey(timeGet)) {
            return time2FundingFeeExtremeExtendTrade.get(timeGet);
        } else {
            Set<String> symbols = new HashSet();
            for (String symbol : symbol2FundingFee.keySet()) {
                TreeMap<Long, FundingRate> time2Funding = symbol2FundingFee.get(symbol);
                TreeMap<Long, FundingRate> time2FundingGet = new TreeMap<>();
                for (int i = 0; i < Configs.NUMBER_HOUR_FUNDING_CAL; i++) {
                    Long timeF = timeGet - i * Utils.TIME_HOUR;
                    if (time2Funding.containsKey(timeF)) {
                        time2FundingGet.put(timeF, time2Funding.get(timeF));
                    }
                    if (time2FundingGet.size() >= Configs.NUMBER_LAST_FUNDING_EXTREME) {
                        break;
                    }
                }
                for (FundingRate funding : time2FundingGet.values()) {
                    if (funding.getFundingRate().doubleValue() < Configs.FUNDING_MAX_TRADE_EXTREME_EXTEND) {
                        symbols.add(symbol);
                    }
                }
                StringBuilder builder = new StringBuilder();
                for (Long key : time2FundingGet.keySet()) {
                    builder.append(Utils.normalizeDateYYYYMMDDHHmm(key)).append(" ").append(time2FundingGet.get(key).getFundingRate()).append(" ");
                }
//            LOG.info("{} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), builder);

            }
            time2FundingFeeExtremeExtendTrade.put(timeGet, symbols);
            return symbols;
        }
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


}
