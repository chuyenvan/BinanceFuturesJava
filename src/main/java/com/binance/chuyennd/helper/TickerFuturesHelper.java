/*
 * Copyright 2023 pc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.binance.chuyennd.helper;

import com.binance.chuyennd.object.*;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.*;

import java.math.BigDecimal;
import java.util.List;

import com.binance.client.constant.Constants;

import java.text.ParseException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

import com.binance.client.model.event.CandlestickEvent;
import com.binance.client.model.market.FundingRate;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * @author pc
 */
public class TickerFuturesHelper {

    public static final Logger LOG = LoggerFactory.getLogger(TickerFuturesHelper.class);


    public static List<KlineObjectSimple> getTickerSimpleWithStartTime(String symbol, String interval, Long startTime) {
        String url = Constants.URL_TICKER_FUTURES_STARTTIME.replace("xxxxxx", symbol) + interval;
        List<KlineObjectSimple> results = new ArrayList();
        try {
            String urlData = url.replace("tttttt", startTime.toString());
            String respon = HttpRequest.getContentFromUrl(urlData);
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            for (List<Object> allKline : allKlines) {
                results.add(KlineObjectSimple.convertString2Kline(allKline));
            }

        } catch (Exception e) {
            LOG.info("Error get ticker {} {}", Utils.normalizeDateYYYYMMDDHHmm(startTime), symbol);
            e.printStackTrace();
        }

        return results;
    }

    public static TreeMap<Long, FundingRate> getFundingFeeWithStartTime(String symbol, Long startTime) {
        String url = Constants.URL_FUNDING_FEE_FUTURES_START_TIME.replace("xxxxxx", symbol);
        TreeMap<Long, FundingRate> results = new TreeMap<>();
        try {
            String urlData = url.replace("tttttt", startTime.toString());
            String respon = HttpRequest.getContentFromUrl(urlData);
            if (respon.length() > 100) {
                List<Map<Object, Object>> allKlines = Utils.gson.fromJson(respon, List.class);
                for (Map<Object, Object> objs : allKlines) {
                    try {
                        if (objs.get("markPrice").equals("")){
                            objs.put("markPrice", "0");
                        }
                        results.put(Utils.getHour(new BigDecimal(objs.get("fundingTime").toString()).longValue()),
                                Utils.gson.fromJson(objs.toString(), FundingRate.class));
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
            }

        } catch (Exception e) {
            LOG.info("Error get funding fee: {} {}", symbol, startTime);
            e.printStackTrace();
        }

        return results;
    }



    public static Set<String> getAllSymbol() {
        Set<String> results = new HashSet<>();
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                results.add(ticker.getSymbol());
            }
        }
        return results;
    }

    public static TreeMap<Float, String> getSymbolVolumeLower() {
        TreeMap<Float, String> results = new TreeMap<Float, String>();
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                results.put(Float.parseFloat(ticker.getQuoteVolume()), ticker.getSymbol());
            }
        }
        return results;
    }
    public static TreeMap<String, Float> getSymbolPrice() {
        TreeMap<String, Float>  results = new TreeMap<>();
        String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
        List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
        for (Object futurePrice : futurePrices) {
            TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
            if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                results.put( ticker.getSymbol(),Float.parseFloat(ticker.getLastPrice()));
            }
        }
        return results;
    }

    public static void main(String[] args) throws ParseException {
//        System.out.println(TickerHelper.getCurrentSide("BIGTIMEUSDT", Constants.INTERVAL_1D));

//        Map<String, List<KlineObjectNumber>> symbol2Tickers = TickerHelper.getAllKlineStartTime(Constants.INTERVAL_15M, Utils.getStartTimeDayAgo(300));
//        System.out.println("Done: " + symbol2Tickers.size());
//        for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2Tickers.entrySet()) {
//            Object symbol = entry.getKey();
//            List<KlineObjectNumber> tickers = entry.getValue();
//            LOG.info("{} {}", symbol, tickers.size());
//        }
//        testGetTicker24hr();
        TreeMap<Float, String> volume2Symbol = getSymbolVolumeLower();
        for (Float volume : volume2Symbol.keySet()) {
            LOG.info("{} {} ", volume2Symbol.get(volume), volume / 1E6);
        }
//        LOG.info("{}", TickerFuturesHelper.getFundingFeeWithStartTime("OCEANUSDT", 1731916800000L));
//        getCurrentTrendLongTime(Contanst.SYMBOL_PAIR_BTC, 60);
//        System.out.println(getCurrentTrendWithInterval("DYDXUSDT", Contanst.INTERVAL_15M));
//        System.out.println(Utils.toJson(getLastTicker("DYDXUSDT", Contanst.INTERVAL_15M)));
//        System.out.println(Utils.toJson(getLastTicker("WLDUSDT", Contanst.INTERVAL_15M)));
//        System.out.println(Utils.toJson(getLastTicker(Contanst.SYMBOL_PAIR_BTC, Contanst.INTERVAL_15M)));
    }


    /**
     * Lấy danh sách nến (Kline) của Futures có giới hạn số lượng (Limit).
     * Đã được bọc thép chống lỗi JSON Crash (Limit Exceeded) từ Binance.
     */
    public static List<KlineObjectSimple> getTickerSimpleWithStartTimeAndLimit(String symbol, String interval, Long startTime, int limit) {
        List<KlineObjectSimple> results = new ArrayList<>();

        // 🛡️ TASK-016 Phần A: clamp limit [1,1500] (Binance futures klines hợp lệ). ≤0 = vô nghĩa → KHÔNG gọi API (tốn weight).
        if (limit <= 0) {
            LOG.debug("Bỏ qua klines {} vì limit={} (≤0, không hợp lệ)", symbol, limit);
            return results;
        }
        if (limit > 1500) {
            LOG.debug("Clamp limit {}→1500 cho {} (Binance max futures klines)", limit, symbol);
            limit = 1500;
        }
        // 🔒 đang trong cooldown REST (ban/-1003) → KHÔNG gọi (tránh gia hạn ban). Caller nên throttle thêm.
        if (BinanceRestGuard.isBanned()) {
            LOG.debug("Skip klines {} — đang cooldown REST", symbol);
            return results;
        }

        // Tự construct URL chuẩn của Binance có chứa limit để tránh phụ thuộc vào hằng số cũ
        String url = "https://fapi.binance.com/fapi/v1/klines?symbol=" + symbol
                + "&interval=" + interval
                + "&startTime=" + startTime
                + "&limit=" + limit;

        try {
            String respon = HttpRequest.getContentFromUrl(url);

            // 🔥 BỌC THÉP CHỐNG JSON CRASH: Chỉ parse nếu Binance trả về một Mảng (Bắt đầu bằng "[")
            // Lỗi Object "{code:-XXXX,...}" → PHÂN BIỆT code (TASK-016 Phần B), KHÔNG gộp chung "Limit/Delist".
            if (StringUtils.isBlank(respon) || respon.trim().startsWith("{")) {
                if (StringUtils.isNotBlank(respon)) {
                    BinanceRestGuard.reportBan(respon);   // -1003/banned-until → cooldown (ngắn/đủ); -1130/khác → no-op
                    String r = respon.length() > 220 ? respon.substring(0, 220) : respon;
                    if (respon.contains("-1003")) {
                        LOG.warn("⏳ RATE-LIMIT (-1003) klines {} → đã đặt backoff qua guard. resp={}", symbol, r);
                    } else if (respon.contains("-1130")) {
                        LOG.warn("🐞 -1130 limit invalid {} (limit={}, startTime={}) — KHÔNG cooldown, KIỂM caller. resp={}", symbol, limit, startTime, r);
                    } else {
                        LOG.debug("Skip {} (delist/lỗi khác): {}", symbol, r);
                    }
                }
                return results;
            }

            // Parse danh sách nến
            List<List<Object>> allKlines = Utils.gson.fromJson(respon, List.class);
            for (List<Object> allKline : allKlines) {
                results.add(KlineObjectSimple.convertString2Kline(allKline));
            }

        } catch (Exception e) {
            LOG.error("❌ Lỗi lấy nến {} {}: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime), symbol, e.getMessage());
        }

        return results;
    }
}
