package com.binance.chuyennd.research;

import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.market.FundingRate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.HashSet;
import java.util.Map;
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
//            long time = Utils.sdfFileHour.parse("20250705 05:11").getTime();
//            LOG.info("{}", Utils.normalizeDateYYYYMMDDHHmm(Utils.get2Hour(time)));
//            LOG.info("{}", Utils.normalizeDateYYYYMMDDHHmm(Utils.get4Hour(time)));
//            FundingFeeManager.getInstance().printLastFunding("HIPPOUSDT");
            for (String symbol : FundingFeeManager.getInstance().symbol2FundingFee.keySet()) {
                TreeMap<Long, FundingRate> time2Rate = FundingFeeManager.getInstance().symbol2FundingFee.get(symbol);
                for (Long time : time2Rate.keySet()) {
                    if (Math.abs(time2Rate.get(time).getFundingRate().doubleValue()) >= 0.02) {
                        LOG.info("{} {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), time2Rate.get(time).getFundingRate(),
                                time2Rate.get(time).getMarkPrice().doubleValue());
                    }
                }
            }
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
            for (int i = 0; i < 30; i++) {
                Long timeF = timeGet - i * Utils.TIME_HOUR;
                if (time2Funding.containsKey(timeF)) {
                    time2FundingGet.put(timeF, time2Funding.get(timeF));
                }
                if (time2FundingGet.size() >= 4) {
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


    /**
     * Lấy danh sách các symbol có funding fee ÂM CỰC ĐOAN tại một thời điểm.
     * Tín hiệu này mạnh hơn so với việc chỉ kiểm tra funding âm thông thường.
     *
     * @param time          Thời điểm cần kiểm tra.
     * @param fundingFeeMin
     * @return Một TreeMap được sắp xếp, với key là mức funding fee (càng âm càng ở đầu),
     * và value là tên symbol. Trả về rỗng nếu không có symbol nào thỏa mãn.
     */
    public TreeMap<Double, String> getExtremeNegativeFundingSymbols(long time, Double fundingFeeMin) {
        // ================== CÁC THAM SỐ CÓ THỂ TÙY CHỈNH ==================
        // Mức funding được coi là "cực đoan". Mặc định là -0.001 tương đương -0.1%
        // Các mức khác bạn có thể thử: -0.0005 (-0.05%), -0.002 (-0.2%)
        final double EXTREME_FUNDING_THRESHOLD = fundingFeeMin;
        // =================================================================

        TreeMap<Double, String> extremeFundingSymbols = new TreeMap<>();
        long timeGet = Utils.getHour(time); // Lấy giờ chẵn gần nhất để khớp với dữ liệu funding

        for (String symbol : symbol2FundingFee.keySet()) {
            TreeMap<Long, FundingRate> time2Funding = symbol2FundingFee.get(symbol);
            if (time2Funding == null || time2Funding.isEmpty()) {
                continue;
            }

            // Tìm entry funding gần nhất tại hoặc trước thời điểm kiểm tra
            Map.Entry<Long, FundingRate> lastEntry = time2Funding.floorEntry(timeGet);

            if (lastEntry != null) {
                double currentRate = lastEntry.getValue().getFundingRate().doubleValue();

                // Kiểm tra nếu mức funding đủ âm để được coi là cực đoan
                if (currentRate < EXTREME_FUNDING_THRESHOLD) {
                    extremeFundingSymbols.put(currentRate, symbol);
                }
            }
        }
        return extremeFundingSymbols;
    }
    public TreeMap<Double, String> getFundingBig(long time) {
        TreeMap<Double, String> fundingFee2Symbol = new TreeMap<>();
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
                if (funding.getFundingRate().doubleValue() < -0.003) {
                    fundingFee2Symbol.put(funding.getFundingRate().doubleValue(), symbol);
                }
            }
            StringBuilder builder = new StringBuilder();
            for (Long key : time2FundingGet.keySet()) {
                builder.append(Utils.normalizeDateYYYYMMDDHHmm(key)).append(" ").append(time2FundingGet.get(key).getFundingRate()).append(" ");
            }
//            LOG.info("{} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), builder);

        }
        return fundingFee2Symbol;
    }

    public Set<String> getAllFunding(long time) {
        Set<String> symbols = new HashSet();
        long timeGet = Utils.getHour(time);
        for (String symbol : symbol2FundingFee.keySet()) {
            TreeMap<Long, FundingRate> time2Funding = symbol2FundingFee.get(symbol);
            if (time2Funding != null && time2Funding.size() > 0 && time2Funding.firstKey() < timeGet) {
                symbols.add(symbol);
            }
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
//            StringBuilder builder = new StringBuilder();
//            for (Long key : time2FundingGet.keySet()) {
//                builder.append(Utils.normalizeDateYYYYMMDDHHmm(key)).append(" ");
//            }
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
