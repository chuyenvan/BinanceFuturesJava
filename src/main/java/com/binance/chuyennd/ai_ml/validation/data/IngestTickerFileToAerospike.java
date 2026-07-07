package com.binance.chuyennd.ai_ml.validation.data;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.io.BufferedInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.ObjectInputStream;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.zip.GZIPInputStream;

/**
 * TASK-141 - Nap ticker tu FILE (kaggle_data_hpo/daily/ticker_YYYYMMDD.bin.gz) vao Aerospike DICH
 * (mac dinh Oracle LOCAL 127.0.0.1:3222 ns=test set kline_1m_opt). File la nguon DAY DU (co 38 coin delist).
 *
 * DOC LAP DataManagerAerospikeFloatSim (writeMinuteBatch hardcode 242). Tu tao AerospikeClient theo arg.
 * File format: ObjectInputStream -> TreeMap<Long, Map<String,KlineObjectSimple>> (phut -> symbol -> kline).
 * Ghi: moi phut 1 record key yyyyMMdd-HHmm GMT+7, bin data=Snappy(MinuteDataFinal), symbol FULL.
 * GHI DE (khong merge) vi day la nap toan bo tu nguon day du - record cu la rac.
 *
 * Args: startYYYYMMDD endYYYYMMDD [host] [port] [ns] [tickerDir]
 *   worker chia ngay: moi worker 1 khoang [start,end].
 */
public class IngestTickerFileToAerospike {
    private static final Logger LOG = LoggerFactory.getLogger(IngestTickerFileToAerospike.class);
    private static final String SET_TICKER = "kline_1m_opt";

    public static void main(String[] args) throws Exception {
        if (args.length < 2) { LOG.error("Args: startYYYYMMDD endYYYYMMDD [host] [port] [ns] [tickerDir]"); System.exit(1); }
        SimpleDateFormat fday = new SimpleDateFormat("yyyyMMdd");
        long startDay = fday.parse(args[0]).getTime();
        long endDay = fday.parse(args[1]).getTime();
        String host = args.length >= 3 ? args[2] : "127.0.0.1";
        int port = args.length >= 4 ? Integer.parseInt(args[3]) : 3222;
        String ns = args.length >= 5 ? args[4] : "test";
        String tickerDir = args.length >= 6 ? args[5] : "kaggle_data_hpo/daily/";
        if (!tickerDir.endsWith("/")) tickerDir += "/";

        LOG.info("INGEST TICKER FILE -> {}:{} ns={} set={} | dir={}", host, port, ns, SET_TICKER, tickerDir);
        LOG.info("range {} .. {}", args[0], args[1]);
        if (!"127.0.0.1".equals(host) && !"localhost".equals(host)) {
            LOG.warn("host KHONG phai localhost ({}). Xac nhan KHONG phai 242/226 that!", host);
        }

        WritePolicy wp = new WritePolicy();
        wp.sendKey = true;
        wp.expiration = 0;
        wp.recordExistsAction = RecordExistsAction.UPDATE;
        SimpleDateFormat keyFmt = new SimpleDateFormat("yyyyMMdd-HHmm");

        long totalRec = 0;
        int daysOk = 0, daysMiss = 0;
        try (AerospikeClient client = new AerospikeClient(host, port)) {
            for (long day = startDay; day <= endDay; day += 86400_000L) {
                String dayStr = fday.format(new Date(day));
                File gz = new File(tickerDir + "ticker_" + dayStr + ".bin.gz");
                if (!gz.exists()) { daysMiss++; continue; }
                TreeMap<Long, Map<String, KlineObjectSimple>> raw;
                try (ObjectInputStream ois = new ObjectInputStream(new BufferedInputStream(new GZIPInputStream(new FileInputStream(gz)), 1 << 20))) {
                    @SuppressWarnings("unchecked")
                    TreeMap<Long, Map<String, KlineObjectSimple>> r = (TreeMap<Long, Map<String, KlineObjectSimple>>) ois.readObject();
                    raw = r;
                } catch (Exception e) {
                    LOG.error("doc file {} loi: {}", gz.getName(), e.getMessage());
                    daysMiss++;
                    continue;
                }
                long recDay = 0;
                for (Map.Entry<Long, Map<String, KlineObjectSimple>> min : raw.entrySet()) {
                    long ts = min.getKey();
                    Map<String, KlineObjectSimple> symMap = min.getValue();
                    if (symMap == null || symMap.isEmpty()) continue;
                    MinuteDataFinal.Builder b = MinuteDataFinal.newBuilder();
                    for (Map.Entry<String, KlineObjectSimple> se : symMap.entrySet()) {
                        String sym = se.getKey();
                        String full = sym.endsWith("USDT") ? sym : sym + "USDT";
                        KlineObjectSimple k = se.getValue();
                        if (k == null) continue;
                        b.putTickers(full, KlineObjectOptimized.newBuilder()
                                .setPriceOpen(k.priceOpen).setMaxPrice(k.maxPrice).setMinPrice(k.minPrice)
                                .setPriceClose(k.priceClose).setTotalUsdt(k.totalUsdt).build());
                    }
                    byte[] compressed = Snappy.compress(b.build().toByteArray());
                    Key key = new Key(ns, SET_TICKER, keyFmt.format(new Date(ts)));
                    client.put(wp, key, new Bin("data", compressed));
                    recDay++;
                }
                totalRec += recDay;
                daysOk++;
                if (daysOk % 30 == 0) LOG.info("  {} ngay xong (ngay gan nhat {}, {} phut), tong {} record",
                        daysOk, dayStr, recDay, totalRec);
                raw.clear();
            }
        }
        LOG.info("HET INGEST: {} ngay OK, {} ngay thieu file, tong {} record phut", daysOk, daysMiss, totalRec);
        System.exit(0);
    }
}
