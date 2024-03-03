/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.client;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class PriceManager {

    public static final Logger LOG = LoggerFactory.getLogger(PriceManager.class);
    public ConcurrentHashMap<String, Double> symbol2MaxPrice = new ConcurrentHashMap<>();
    public ConcurrentHashMap<String, Double> symbol2MinPrice = new ConcurrentHashMap<>();
    public Double PERCENT_MINIMUM_CHANGE_2_SELL = 0.15;
    private static volatile PriceManager INSTANCE = null;

    public static PriceManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new PriceManager();
            INSTANCE.updateData();
            INSTANCE.startThreadUpdateDataByHour();
        }
        return INSTANCE;
    }

    private void updateData() {
        Map<String, List<KlineObjectNumber>> symbol2Tickers = TickerFuturesHelper.getAllKlineStartTime(Constants.INTERVAL_1D,
                Utils.getStartTimeDayAgo(30), 50 * Utils.TIME_MINUTE);
        for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2Tickers.entrySet()) {
            String symbol = entry.getKey();
            List<KlineObjectNumber> klines = entry.getValue();
            Double maxPrice = null;
            Double minPrice = null;
            for (KlineObjectNumber kline : klines) {
                if (maxPrice == null || maxPrice < kline.maxPrice) {
                    maxPrice = kline.maxPrice;
                }
                if (minPrice == null || minPrice > kline.minPrice) {
                    minPrice = kline.minPrice;
                }
            }
            symbol2MaxPrice.put(symbol, maxPrice);
            symbol2MinPrice.put(symbol, minPrice);
        }
        LOG.info("Finished update all p maxmin!");
    }

    private void startThreadUpdateDataByHour() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdateDataByHour");
            LOG.info("Start thread ThreadUpdateDataByHour!");
            while (true) {
                try {
                    Thread.sleep(Utils.TIME_HOUR);
                    updateData();
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadUpdateDataByHour: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    public boolean isAvalible2Trade(String symbol, Double price, OrderSide side) {
        if (side.equals(OrderSide.SELL)) {
            Double minPriceIn30d = symbol2MinPrice.get(symbol);
            return !(minPriceIn30d == null
                    || Utils.rateOf2Double(price, minPriceIn30d) < PERCENT_MINIMUM_CHANGE_2_SELL);
        }
        return true;
    }

    public static void main(String[] args) {
        for (Map.Entry<String, Double> entry : PriceManager.getInstance().symbol2MaxPrice.entrySet()) {
            String symbol = entry.getKey();
            Double maxPrice = entry.getValue();
            Double rate = Utils.rateOf2Double(maxPrice, PriceManager.getInstance().symbol2MinPrice.get(symbol)) * 100;
            LOG.info("{} {} {} {}", symbol, PriceManager.getInstance().symbol2MinPrice.get(symbol), maxPrice, rate.longValue());
        }
        Double price = 0.5778;
        System.out.println(PriceManager.getInstance().isAvalible2Trade("CTKUSDT", price, OrderSide.SELL));
        System.out.println(PriceManager.getInstance().isAvalible2Trade("CTKUSDT", price * 1.15, OrderSide.SELL));
        System.out.println(PriceManager.getInstance().isAvalible2Trade("CTKUSDT", price * 1.25, OrderSide.SELL));
        System.out.println(PriceManager.getInstance().isAvalible2Trade("CTKUSDT", price * 1.5, OrderSide.BUY));
        System.out.println(PriceManager.getInstance().isAvalible2Trade("CTKUSDT", price * 1.12, OrderSide.SELL));
        System.out.println(PriceManager.getInstance().isAvalible2Trade("CTKUSDT", price * 1.19, OrderSide.SELL));

    }

}
