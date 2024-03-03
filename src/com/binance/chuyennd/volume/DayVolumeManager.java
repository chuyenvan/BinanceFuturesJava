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
package com.binance.chuyennd.volume;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class DayVolumeManager {

    public static final Logger LOG = LoggerFactory.getLogger(DayVolumeManager.class);
    public final String FILE_STORAGE_VOLUME = "storage/data/ticker/volumebydate.data";
    public ConcurrentHashMap<Integer, Map<String, Double>> date2SymbolVolume = new ConcurrentHashMap<>();
    private static volatile DayVolumeManager INSTANCE = null;

    public static DayVolumeManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new DayVolumeManager();
            INSTANCE.startThreadUpdateAtStartDay();
        }
        return INSTANCE;
    }

    private void startThreadUpdateAtStartDay() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdateAtStartDay");
            LOG.info("Start ThreadUpdateAtStartDay !");
            String fileName = FILE_STORAGE_VOLUME;
            File fileStorage = new File(fileName);
            if (fileStorage.exists()) {
                try {
                    date2SymbolVolume = (ConcurrentHashMap<Integer, Map<String, Double>>) Storage.readObjectFromFile(fileName);
                } catch (Exception e) {
                    e.printStackTrace();
                }
            } else {
                updateVolume();
            }
            while (true) {
                try {
                    Thread.sleep(Utils.TIME_HOUR);
                    updateVolume();
                } catch (Exception e) {
                    LOG.error("ERROR during UpdateAtStartDay: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void updateVolume() {
        try {
            Map<String, List<KlineObjectNumber>> symbol2Tickers = TickerFuturesHelper.getAllKlineWithUpdateTime(Constants.INTERVAL_1D, Utils.TIME_HOUR);
            for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2Tickers.entrySet()) {
                String symbol = entry.getKey();
                List<KlineObjectNumber> tickers = entry.getValue();
                for (KlineObjectNumber ticker : tickers) {
                    Integer date = Integer.valueOf(Utils.normalizeDateYYYYMMDD(ticker.startTime.longValue()));
                    Map<String, Double> symbol2Volume = date2SymbolVolume.get(date);
                    if (symbol2Volume == null) {
                        symbol2Volume = new HashMap<>();
                        date2SymbolVolume.put(date, symbol2Volume);
                    }
                    symbol2Volume.put(symbol, ticker.totalUsdt);
                }
            }
            Storage.writeObject2File(FILE_STORAGE_VOLUME, date2SymbolVolume);
            LOG.info("Finish update volume start day");
        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    public static void main(String[] args) throws InterruptedException {
        DayVolumeManager.getInstance();
        for (Map.Entry<Integer, Map<String, Double>> entry : DayVolumeManager.getInstance().date2SymbolVolume.entrySet()) {
            Integer date = entry.getKey();
            Map<String, Double> symbol2Volume = entry.getValue();
            for (Map.Entry<String, Double> entry1 : symbol2Volume.entrySet()) {
                String symbol = entry1.getKey();
                Double volume = entry1.getValue();
                LOG.info("{} {} {}", date, symbol, Utils.formatMoney(volume));
            }
        }

    }
}
