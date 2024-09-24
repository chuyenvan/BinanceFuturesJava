/*
 * Copyright 2024 pc.
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
package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * @author pc
 */
public class Volume24hrManager {

    public static final Logger LOG = LoggerFactory.getLogger(Volume24hrManager.class);
    public ConcurrentHashMap<String, Map<Long, Map<String, Double>>> month2Time2Symbol2Volume = new ConcurrentHashMap<>();
    public static final String FILE_STORAGE_VOLUME24H = "../storage/data/";
//    public static final String FILE_STORAGE_VOLUME24H = "E:\\educa\\source\\github/storage/data/";
    private static volatile Volume24hrManager INSTANCE = null;

    public static Volume24hrManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new Volume24hrManager();
        }
        return INSTANCE;
    }


    public Map<String, Double> getVolume24h(Long time) {
        String month = Utils.getMonth(time);
        Map<Long, Map<String, Double>> time2SymbolAndVolume = month2Time2Symbol2Volume.get(month);
        if (time2SymbolAndVolume == null || !time2SymbolAndVolume.containsKey(time)) {
            updateVolume24hForTime(time);
        }
        time2SymbolAndVolume = month2Time2Symbol2Volume.get(month);
        if (time2SymbolAndVolume != null) {
            return time2SymbolAndVolume.get(time);
        }
        return null;
    }

    private void updateVolume24hForTime(Long time) {
        try {
            String month = Utils.getMonth(time);
            String fileMonthData = FILE_STORAGE_VOLUME24H + month;
            Map<Long, Map<String, Double>> time2Symbol2Volume = month2Time2Symbol2Volume.get(month);
            // remove data for mem not big over
            Set<String> hashSet = new HashSet<>();
            hashSet.addAll(month2Time2Symbol2Volume.keySet());
            for (String monthData : hashSet) {
                if (!StringUtils.equals(monthData, month) && month2Time2Symbol2Volume.size() > 3) {
                    month2Time2Symbol2Volume.remove(monthData);
                }
            }
            if (time2Symbol2Volume == null) {
                if (new File(fileMonthData).exists()) {
                    time2Symbol2Volume = (Map<Long, Map<String, Double>>) Storage.readObjectFromFile(fileMonthData);
                } else {
                    time2Symbol2Volume = new HashMap<>();
                }
                month2Time2Symbol2Volume.put(month, time2Symbol2Volume);
            }
            if (!time2Symbol2Volume.containsKey(time)) {
                Long timeRun = System.currentTimeMillis();
                Long startTime = Utils.getDate(time - Utils.TIME_DAY);
                LOG.info("Start statistic volume24h of: {}", Utils.normalizeDateYYYYMMDD(time));
                // data ticker
                TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManager.readDataFromFile1M(startTime);
                TreeMap<Long, Map<String, KlineObjectSimple>> dataNextDate = DataManager.readDataFromFile1M(startTime + Utils.TIME_DAY);
                if (time2Tickers == null){
                    return;
                }
                if (dataNextDate != null) {
                    time2Tickers.putAll(dataNextDate);
                }
                for (int i = 0; i < 1440; i++) {
                    long timeVolume24h = startTime + Utils.TIME_DAY + i * Utils.TIME_MINUTE;
                    Map<String, Double> symbol2Volume24h = new HashMap<>();
                    time2Symbol2Volume.put(timeVolume24h, symbol2Volume24h);
                    for (int j = 0; j < 1440; j++) {
                        long timeData = timeVolume24h - j * Utils.TIME_MINUTE;
                        Map<String, KlineObjectSimple> symbol2Ticker = time2Tickers.get(timeData);
                        if (symbol2Ticker != null) {
                            for (String symbol : symbol2Ticker.keySet()) {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                Double volume24h = symbol2Volume24h.get(symbol);
                                if (volume24h == null) {
                                    volume24h = 0d;
                                }
                                volume24h += ticker.totalUsdt;
                                symbol2Volume24h.put(symbol, volume24h);
                            }
                        }
                    }
                }
                Storage.writeObject2File(fileMonthData, time2Symbol2Volume);
                LOG.info("Finish update volume 24h for {} {} {}s", Utils.normalizeDateYYYYMMDD(time), month2Time2Symbol2Volume.size()
                        , (System.currentTimeMillis() - timeRun) / Utils.TIME_SECOND);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void main(String[] args) {
        Long time = 1725408000000L;
        Map<String, Double> symbol2Volume24h = Volume24hrManager.getInstance().getVolume24h(time);
        if (symbol2Volume24h != null) {
            for (String symbol : symbol2Volume24h.keySet()) {
                LOG.info("{} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), symbol, symbol2Volume24h.get(symbol));
            }
        }
    }

}
