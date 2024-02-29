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
package com.binance.chuyennd.grid;

import com.binance.chuyennd.funcs.ClientSingleton;
import com.binance.chuyennd.funcs.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import org.apache.commons.io.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class GridDetector {

    public static final Logger LOG = LoggerFactory.getLogger(GridDetector.class);

    public static void main(String[] args) throws IOException {
        Double rangeLimit = 1.1;
        Integer ageMin = 100;
        Double rateBigChangeMin = 0.005;

        gridDetector(rangeLimit, ageMin, rateBigChangeMin);
    }

    private static void gridDetector(Double rangeLimit, Integer ageMin, Double rateBigChangeMin) throws IOException {
        // get all symbols
        List<String> lines = new ArrayList<>();
        Set<String> symbols = ClientSingleton.getInstance().getAllSymbol();

// test        
//        Set<String> symbols = new HashSet<String>();
//        symbols.add("WLDUSDT");

// end test
        TreeMap<Integer, GridObject> rate2GridInfo = new TreeMap<>();
        for (String symbol : symbols) {
            try {
                // range change in 3 month by ticker 1d
                List<KlineObjectNumber> kline1Ds = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_1D);
                if (kline1Ds.size() < ageMin) {
                    continue;
                }
                int limitDay2Get = 60;
                Double currentPrice = ClientSingleton.getInstance().getCurrentPrice(symbol);
                Double maxPrice = TickerFuturesHelper.getMaxPrice(kline1Ds, limitDay2Get);
                Double minPrice = TickerFuturesHelper.getMinPrice(kline1Ds, limitDay2Get);
                Double rangeOfSym = Utils.rateOf2Double(maxPrice, minPrice);
                if (rangeOfSym > rangeLimit) {
                    continue;
                }
                int totalCurrentPriceInKlineDay = TickerFuturesHelper.getTotalCurrentPriceInKline(kline1Ds, currentPrice, limitDay2Get);
                // ticker 15M rate
                List<KlineObjectNumber> kline15ms = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_15M);
                List<KlineObjectNumber> klineBigchanges = TickerFuturesHelper.getTotalKlineBigchange(kline15ms, rateBigChangeMin);
                int totalCurrentPriceInKlineMax = TickerFuturesHelper.getTotalCurrentPriceInKline(klineBigchanges, currentPrice, limitDay2Get);
                GridObject gridInfo = new GridObject(symbol, currentPrice, rangeOfSym,
                        maxPrice, minPrice, kline1Ds.size(), klineBigchanges.size(),
                        totalCurrentPriceInKlineMax, totalCurrentPriceInKlineDay);
                rate2GridInfo.put(gridInfo.totalKlineBigChange, gridInfo);
            } catch (Exception e) {
                LOG.info("Erorr during get info of: {}", symbol);
//                e.printStackTrace();
            }
        }
        StringBuilder builder = new StringBuilder();
        builder.append("symbol").append(",");
        builder.append("range2month").append(",");
        builder.append("currentPrice").append(",");
        builder.append("maxPrice").append(",");
        builder.append("minPrice").append(",");
        builder.append("ageSym").append(",");
        builder.append("totalKlineBigchange").append(",");
        builder.append("currentPriceInBigchange").append(",");
        builder.append("totalCurrentPriceInKlineDay").append(",");
        lines.add(builder.toString());
        for (Map.Entry<Integer, GridObject> entry : rate2GridInfo.entrySet()) {
            GridObject gridInfo = entry.getValue();
            builder.setLength(0);
            builder.append(gridInfo.symbol).append(",");
            builder.append(gridInfo.range2Month).append(",");
            builder.append(gridInfo.currentPrice).append(",");
            builder.append(gridInfo.maxPrice).append(",");
            builder.append(gridInfo.minPrice).append(",");
            builder.append(gridInfo.ageSymbolByDay).append(",");
            builder.append(gridInfo.totalKlineBigChange).append(",");
            builder.append(gridInfo.totalCurrentPriceInKlineBigChange).append(",");
            builder.append(gridInfo.totalCurrentPriceInKlineDay).append(",");
            lines.add(builder.toString());
        }
        FileUtils.writeLines(new File("target/gridDetect.csv"), lines);
    }

}
