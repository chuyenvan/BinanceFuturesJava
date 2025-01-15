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
    public Double rateMarginRealMax;
    public Long timeMarginMax;
    public Double profitLossMax;
    public Long timeProfitLossMax;

    public Double unProfitMin;
    public Map<Long, Double> date2ProfitMin = new HashMap<>();
    public Map<Long, Double> date2MarginMax = new HashMap<>();
    public Map<Long, Double> date2MarginRealMax = new HashMap<>();
    public Map<String, Double> month2ProfitMin = new HashMap<>();
    public Map<String, Double> month2SLMax = new HashMap<>();
    public Map<String, Double> month2MarginMax = new HashMap<>();
    public Map<String, Double> month2MarginRealMax = new HashMap<>();
    public Long timeUnProfitMin;


    public void updateIndex(Double balance, Double positionMargin, Double positionMarginReal,
                            Long timeUpdate, Double profitLossMin, Double unrealizedProfitMin,
                            ConcurrentHashMap<String, List<OrderTargetInfoTest>> allOrderRunning, ConcurrentHashMap<String,
            OrderTargetInfoTest> orderRunning) {

        if (rateMarginMax == null || rateMarginMax < positionMargin / balance) {
            rateMarginMax = positionMargin / balance;
            this.marginMax = positionMargin;
            timeMarginMax = timeUpdate;
        }
        if (rateMarginRealMax == null || rateMarginRealMax < positionMarginReal / balance) {
            rateMarginRealMax = positionMarginReal / balance;
        }
        Double dateMarginMax = date2MarginMax.get(Utils.getDate(timeUpdate));
        if (dateMarginMax == null || dateMarginMax < positionMargin) {
            dateMarginMax = positionMargin;
        }
        date2MarginMax.put(Utils.getDate(timeUpdate), dateMarginMax);

        Double dateMarginRealMax = date2MarginRealMax.get(Utils.getDate(timeUpdate));
        if (dateMarginRealMax == null || dateMarginRealMax < positionMarginReal) {
            dateMarginRealMax = positionMarginReal;
        }
        date2MarginRealMax.put(Utils.getDate(timeUpdate), dateMarginRealMax);

        Double monthMarginMax = month2MarginMax.get(Utils.getMonth(timeUpdate));
        if (monthMarginMax == null || monthMarginMax < positionMargin) {
            monthMarginMax = positionMargin;
            for (String symbol : allOrderRunning.keySet()) {
                OrderTargetInfoTest orderAll = orderRunning.get(symbol);
                if (orderAll != null) {
                    for (OrderTargetInfoTest order : allOrderRunning.get(symbol)) {
                        order.minPrice = orderAll.minPrice;
                        order.priceSL = orderAll.priceSL;
                    }
                }
            }
            Storage.writeObject2File("storage/data/marginMax/" + Utils.getMonth(timeUpdate), allOrderRunning);
        }
        month2MarginMax.put(Utils.getMonth(timeUpdate), monthMarginMax);

        Double monthMarginRealMax = month2MarginRealMax.get(Utils.getMonth(timeUpdate));
        if (monthMarginRealMax == null || monthMarginRealMax < positionMarginReal) {
            monthMarginRealMax = positionMarginReal;
            for (String symbol : allOrderRunning.keySet()) {
                OrderTargetInfoTest orderAll = orderRunning.get(symbol);
                if (orderAll != null) {
                    for (OrderTargetInfoTest order : allOrderRunning.get(symbol)) {
                        order.minPrice = orderAll.minPrice;
                        order.priceSL = orderAll.priceSL;
                    }
                }
            }
            Storage.writeObject2File("storage/data/marginRealMax/" + Utils.getMonth(timeUpdate), allOrderRunning);
        }
        month2MarginRealMax.put(Utils.getMonth(timeUpdate), monthMarginRealMax);

        if (this.profitLossMax == null || this.profitLossMax > profitLossMin) {
            this.profitLossMax = profitLossMin;
            this.timeProfitLossMax = timeUpdate;
        }
        Double slMax = month2SLMax.get(Utils.getMonth(timeUpdate));
        if (slMax == null || slMax > profitLossMin) {
            slMax = profitLossMin;
            Storage.writeObject2File("storage/data/slMin/" + Utils.getMonth(timeUpdate), allOrderRunning);
        }
        month2SLMax.put(Utils.getMonth(timeUpdate), slMax);

        if (this.unProfitMin == null || this.unProfitMin > unrealizedProfitMin) {
            this.unProfitMin = unrealizedProfitMin;
            this.timeUnProfitMin = timeUpdate;
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
