package com.binance.chuyennd.trading;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.market.FundingRate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

public class FundingFeeManagerProduction {
    public static final Logger LOG = LoggerFactory.getLogger(FundingFeeManagerProduction.class);

    private Set<String> fundingBuy = new HashSet<>();
    private Set<String> fundingSell = new HashSet<>();
    private static volatile FundingFeeManagerProduction INSTANCE = null;

    public static FundingFeeManagerProduction getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new FundingFeeManagerProduction();
        }
        return INSTANCE;
    }

    public void updateListBuySell() {

        Map<String, TreeMap<Long, Double>> symbol2Funding = DataManagerAerospikeFloatSim.getAllFundingMap();

        for (String symbol : symbol2Funding.keySet()) {
            try {
                TreeMap<Long, Double> time2Rate = symbol2Funding.get(symbol);
                if (time2Rate != null && !time2Rate.isEmpty()) {
                    while (time2Rate.size() > 0 && time2Rate.firstKey() < System.currentTimeMillis() -
                            Configs.NUMBER_HOUR_FUNDING_CAL * Utils.TIME_HOUR) {
                        time2Rate.remove(time2Rate.firstKey());
                    }

                    Boolean isFundingSell = true;
                    for (Double funding : time2Rate.values()) {
                        if (funding < Configs.FUNDING_MAX_TRADE
                                || funding > Configs.FUNDING_MIN_TRADE
                        ) {
                            fundingBuy.add(symbol);
                            fundingSell.remove(symbol);
                            isFundingSell = false;
                            break;
                        }
                    }
                    if (isFundingSell) {
                        fundingBuy.remove(symbol);
                        fundingSell.add(symbol);
                    }
                }
            } catch (Exception e) {
                LOG.info("Error update list sell/buy funding fee: {}", symbol);
                e.printStackTrace();
            }
        }
        LOG.info("Total funding fee buy: {}", fundingBuy.size());
    }

    public Double getNearestFundingFee(String symbol, long timestamp) {
        TreeMap<Long, Double> time2RateFunding = DataManagerAerospikeFloatSim.getFundingMap(symbol);

        // Kiểm tra null hoặc rỗng
        if (time2RateFunding == null || time2RateFunding.isEmpty()) {
            return 0.0; // Production không có dữ liệu thì trả về 0 để tránh lỗi
        }

        // Tìm mốc thời gian gần nhất <= timestamp
        Map.Entry<Long, Double> entry = time2RateFunding.floorEntry(timestamp);

        if (entry != null) {
            // Nếu dữ liệu trong RAM quá cũ (ví dụ > 24h trước) thì coi như không có
            if (timestamp - entry.getKey() > 24 * 3600 * 1000L) {
                return 0.0;
            }
            return entry.getValue().doubleValue();
        }

        return 0.0;
    }

    public static void main(String[] args) throws ParseException {
//        System.out.println(FundingFeeManagerProduction.getInstance().getFundingBuy());
        TreeMap<Long, Double> time2RateFunding = DataManagerAerospikeFloatSim.getFundingMap("CLOUSDT");
        for (Map.Entry<Long, Double> entry : time2RateFunding.entrySet()) {
            System.out.println("Time: " + Utils.normalizeDateYYYYMMDDHHmm(entry.getKey()) + " " + entry.getKey() +
                    " - Funding Rate: " + entry.getValue());
        }
    }

    public Set<String> getFundingBuy() {
        updateListBuySell();
        return fundingBuy;
    }
}
