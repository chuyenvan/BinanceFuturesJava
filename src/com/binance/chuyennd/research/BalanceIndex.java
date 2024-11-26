package com.binance.chuyennd.research;

import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;

import java.io.Serializable;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class BalanceIndex implements Serializable {

    public Double marginMax;
    public Double rateMarginMax;
    public Long timeMarginMax;
    public Double profitLossMax;
    public Long timeProfitLossMax;

    public Double unProfitMin;
    public Map<Long, Double> date2ProfitMin = new HashMap<>();
    public Map<Long, Double> date2MarginMax = new HashMap<>();
    public Map<String, Double> month2ProfitMin = new HashMap<>();
    public Map<String, Double> month2SLMax = new HashMap<>();
    public Map<String, Double> month2MarginMax = new HashMap<>();
    public Long timeUnProfitMin;


    public void updateIndex(Double balance, Double positionMargin, Long timeUpdate, Double profitLossMin, Double unrealizedProfitMin,
                            ConcurrentHashMap<String, List<OrderTargetInfoTest>> allOrderRunning, ConcurrentHashMap<String,
            OrderTargetInfoTest> orderRunning) {
        if (!Utils.getMonth(timeUpdate).startsWith("202105") && !Utils.getMonth(timeUpdate).startsWith("202106")) {
            if (rateMarginMax == null || rateMarginMax < positionMargin / balance) {
                rateMarginMax = positionMargin / balance;
                this.marginMax = positionMargin;
                timeMarginMax = timeUpdate;
            }
        }
        Double dateMarginMax = date2MarginMax.get(Utils.getDate(timeUpdate));
        if (dateMarginMax == null || dateMarginMax < positionMargin) {
            dateMarginMax = positionMargin;
        }
        date2MarginMax.put(Utils.getDate(timeUpdate), dateMarginMax);
        Double monthMarginMax = month2MarginMax.get(Utils.getMonth(timeUpdate));
        if (monthMarginMax == null || monthMarginMax < positionMargin) {
            monthMarginMax = positionMargin;
            for (String symbol : allOrderRunning.keySet()) {
                OrderTargetInfoTest orderAll = orderRunning.get(symbol);
                if (orderAll != null) {
                    for (OrderTargetInfoTest order : allOrderRunning.get(symbol)) {
                        order.minPrice =orderAll.minPrice;
                        order.priceSL = orderAll.priceSL;
                    }
                }
            }
            Storage.writeObject2File("storage/data/marginMax/" + Utils.getMonth(timeUpdate), allOrderRunning);
        }
        month2MarginMax.put(Utils.getMonth(timeUpdate), monthMarginMax);

        if (!Utils.getMonth(timeUpdate).startsWith("202105") && !Utils.getMonth(timeUpdate).startsWith("202106")) {
            if (this.profitLossMax == null || this.profitLossMax > profitLossMin) {
                this.profitLossMax = profitLossMin;
                this.timeProfitLossMax = timeUpdate;
            }
        }
        Double slMax = month2SLMax.get(Utils.getMonth(timeUpdate));
        if (slMax == null || slMax > profitLossMin) {
            slMax = profitLossMin;
            Storage.writeObject2File("storage/data/slMin/" + Utils.getMonth(timeUpdate), allOrderRunning);
        }
        month2SLMax.put(Utils.getMonth(timeUpdate), slMax);
        if (!Utils.getMonth(timeUpdate).startsWith("202105") && !Utils.getMonth(timeUpdate).startsWith("202106")) {
            if (this.unProfitMin == null || this.unProfitMin > unrealizedProfitMin) {
                this.unProfitMin = unrealizedProfitMin;
                this.timeUnProfitMin = timeUpdate;
            }
        }
        Double profitMinOfDate = date2ProfitMin.get(Utils.getDate(timeUpdate));
        if (profitMinOfDate == null || profitMinOfDate > unrealizedProfitMin) {
            profitMinOfDate = unrealizedProfitMin;
        }
        date2ProfitMin.put(Utils.getDate(timeUpdate), profitMinOfDate);
        Double profitMinOfYear = month2ProfitMin.get(Utils.getMonth(timeUpdate));
        if (profitMinOfYear == null || profitMinOfYear > unrealizedProfitMin) {
            profitMinOfYear = unrealizedProfitMin;
            Storage.writeObject2File("storage/data/unProfitMin/" + Utils.getMonth(timeUpdate), allOrderRunning);
        }
        month2ProfitMin.put(Utils.getMonth(timeUpdate), profitMinOfYear);

    }
}
