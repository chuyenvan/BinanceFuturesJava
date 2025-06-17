package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.text.ParseException;
import java.util.Map;
import java.util.TreeMap;

public class ConvertDataTicker1M2Snappy {
    public static final Logger LOG = LoggerFactory.getLogger(ConvertDataTicker1M2Snappy.class);

    public static void main(String[] args) throws ParseException {
        convertData();
//        convertFile("../storage/ticker/symbols-1m/");
    }

    private static void convertFile(String folder) {
        for (File file : new File(folder).listFiles()) {
            Object data = Storage.readObjectFromFile(file.getAbsolutePath());
            if (data != null) {
                StorageSnappy.writeObject2File(file.getAbsolutePath(), data);
            }
        }
    }

    private static void convertData() throws ParseException {
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            try {
                if (new File(Configs.FOLDER_TICKER_1M_SNAPPY_FILE + startTime).exists()) {
                    startTime += Utils.TIME_DAY;
                    continue;
                }
                time2Tickers = DataManager.readDataFromFile1M(startTime);
                LOG.info("Read data date: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                StorageSnappy.writeObject2File(Configs.FOLDER_TICKER_1M_SNAPPY_FILE + startTime, time2Tickers);
                FileUtils.delete(new File(Configs.FOLDER_TICKER_1M_FILE + startTime));
            } catch (Exception e) {
                e.printStackTrace();
            }
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                break;
            }
        }
    }
}
