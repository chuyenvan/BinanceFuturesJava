package com.binance.chuyennd.research;

import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;

import java.io.Serializable;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class BalanceIndex implements Serializable {

    public Double marginMax;
    public Double profitLossMax;
   public Long timeProfitLossMax;


    public Double unProfitMin;
    public Map<Long, Double> date2ProfitMin = new HashMap<>();
    public Map<Long, Double> date2MarginMax = new HashMap<>();
    public Map<String, Double> month2ProfitMin = new HashMap<>();
    public Map<String, Double> month2SLMax = new HashMap<>();
    public Map<String, Double> month2MarginMax = new HashMap<>();
    public TreeMap<Integer, Double> year2UnrealizedPnl = new TreeMap<>();
    public Long timeUnProfitMin;


    public void updateIndex(Double balance, Double positionMargin, Double positionMarginReal,
                            Long timeUpdate, Double profitLossMin, Double unrealizedProfitMin,
                            ConcurrentHashMap<String, List<OrderTargetInfoTest>> allOrderEntry, ConcurrentHashMap<String,
            OrderTargetInfoTest> orderRunning, Double unProfit) {


        Double dateMarginMax = date2MarginMax.get(Utils.getDate(timeUpdate));
        if (dateMarginMax == null || dateMarginMax < positionMargin) {
            dateMarginMax = positionMargin;
        }
        date2MarginMax.put(Utils.getDate(timeUpdate), dateMarginMax);


        Double monthMarginMax = month2MarginMax.get(Utils.getMonth(timeUpdate));
        if (monthMarginMax == null || monthMarginMax < positionMargin) {
            monthMarginMax = positionMargin;
            for (String symbol : allOrderEntry.keySet()) {
                OrderTargetInfoTest orderAll = orderRunning.get(symbol);
                if (orderAll != null) {
                    for (OrderTargetInfoTest order : allOrderEntry.get(symbol)) {
                        order.minPrice = orderAll.minPrice;
                        order.priceSL = orderAll.priceSL;
                    }
                }
            }
//            Storage.writeObject2File("storage/data/marginMax/" + Utils.getMonth(timeUpdate), allOrderEntry);
        }
        month2MarginMax.put(Utils.getMonth(timeUpdate), monthMarginMax);


        if (this.profitLossMax == null || this.profitLossMax > profitLossMin) {
            this.profitLossMax = profitLossMin;
            this.timeProfitLossMax = timeUpdate;
        }
        Double slMax = month2SLMax.get(Utils.getMonth(timeUpdate));
        if (slMax == null || slMax > profitLossMin) {
            slMax = profitLossMin;
//            Storage.writeObject2File("storage/data/slMin/" + Utils.getMonth(timeUpdate), allOrderEntry);
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
            for (String symbol : allOrderEntry.keySet()) {
                OrderTargetInfoTest orderAll = orderRunning.get(symbol);
                if (orderAll != null) {
                    for (OrderTargetInfoTest order : allOrderEntry.get(symbol)) {
                        order.minPrice = orderAll.minPrice;
                        order.priceTP = orderAll.minPrice;
                    }
                }
            }
//            Storage.writeObject2File("storage/data/unProfitMin/" + Utils.getMonth(timeUpdate), allOrderEntry);
        }
        month2ProfitMin.put(Utils.getMonth(timeUpdate), profitMinOfYear);
        year2UnrealizedPnl.put(Utils.getYear(timeUpdate), unProfit);
    }
}
