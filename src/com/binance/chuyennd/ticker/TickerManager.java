/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.ticker;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.mongo.TickerMongoHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.bson.Document;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class TickerManager {

    public static final Logger LOG = LoggerFactory.getLogger(TickerManager.class);
    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));

    public static void main(String[] args) {
        new TickerManager().startThreadUpdateTicker();
//        new TickerManager().updateTickerASymbol("PIXELUSDT");
    }

    private void startThreadUpdateTicker() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdateTicker");
            LOG.info("Start ThreadUpdateTicker !");
            while (true) {
                try {
                    try {
                        if (Utils.getCurrentHour() == 10) {
                            Set<String> symbols = TickerFuturesHelper.getAllSymbol();
                            symbols.removeAll(Constants.specialSymbol);
                            for (String symbol : symbols) {
                                executorService.execute(() -> updateTickerASymbol(symbol));
                            }
                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                    Thread.sleep(Utils.TIME_HOUR);
                } catch (Exception e) {
                    LOG.error("ERROR during UpdateTicker: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void updateTickerASymbol(String symbol) {
        try {
            LOG.info("Start update ticker for {}", symbol);
            Long lastHourUpdate = TickerMongoHelper.getInstance().getLastHourTickerBySymbol(symbol);
            LOG.info("update ticker for {} from: {}", symbol, new Date(lastHourUpdate));
            updateDataByHour(symbol, lastHourUpdate);
            LOG.info("Finished update ticker for {}", symbol);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void updateDataByHour(String symbol, Long lastHourUpdate) {
        List<KlineObjectNumber> allTickers = TickerFuturesHelper.getTickerWithStartTimeFull(symbol, Constants.INTERVAL_1M, lastHourUpdate);
        if (lastHourUpdate != 0) {
            // delete hour start update
            TickerMongoHelper.getInstance().deleteTicker(symbol, lastHourUpdate);
        }
        Map<Long, List<KlineObjectNumber>> time2Tickers = new HashMap<>();
        for (KlineObjectNumber ticker : allTickers) {
            long timeHour = Utils.getHour(ticker.startTime.longValue());
            List<KlineObjectNumber> docs = time2Tickers.get(timeHour);
            if (docs == null) {
                docs = new ArrayList<>();
                time2Tickers.put(timeHour, docs);
            }
            docs.add(ticker);
        }
        for (Map.Entry<Long, List<KlineObjectNumber>> entry : time2Tickers.entrySet()) {
            Long hour = entry.getKey();
            List<KlineObjectNumber> tickers = entry.getValue();
            List<Document> details = new ArrayList<>();
            for (KlineObjectNumber ticker : tickers) {
                details.add(convertTicker2Doc(ticker));
            }
            Document doc = new Document();
            doc.append("sym", symbol);
            doc.append("hour", hour);
            doc.append("details", details);
            TickerMongoHelper.getInstance().insertTicker(doc);
        }
    }

    private Document convertTicker2Doc(KlineObjectNumber ticker) {
        Document doc = new Document();
        doc.append("startTime", ticker.startTime);
        doc.append("endTime", ticker.endTime);
        doc.append("maxPrice", ticker.maxPrice);
        doc.append("minPrice", ticker.minPrice);
        doc.append("priceOpen", ticker.priceOpen);
        doc.append("priceClose", ticker.priceClose);
        doc.append("totalUsdt", ticker.totalUsdt);
        return doc;
    }
}
