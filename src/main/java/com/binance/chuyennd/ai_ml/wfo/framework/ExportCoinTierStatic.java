package com.binance.chuyennd.ai_ml.wfo.framework;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.util.Date;
import java.util.Map;
import java.util.NavigableMap;
import java.util.TreeMap;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;

/**
 * Export TĨNH CoinRank tier theo interval (giờ) cho WFO/HPO.
 *
 * <p>Sinh dữ liệu bằng CHÍNH code live: feed kline RAW (có totalUsdt, đọc qua
 * {@link DataManagerAerospikeFloatSim#readDataFromAerospike1M_ShortKey} — y hệt đường non-cache của
 * simulator) qua {@link HistoryManager#updateHistoryArray} + {@link CoinRankManager} (LIVE ranking),
 * snapshot mảng tier mỗi khi sang interval mới.
 *
 * <p><b>Semantic CONTINUOUS (xem docs/insights/WFO_STATIC_DATA_DESIGN.md #6,#7):</b> chạy LIÊN TỤC nên
 * ring ấm + cập nhật ĐỀU mỗi giờ — sạch & gene-invariant, KHÁC live (cold-start mỗi window + update
 * vướng logic lệnh). Delta PnL vs live phải ĐO và để Uni duyệt, KHÔNG coi là khớp tuyệt đối.
 *
 * <p>Artifact: {@code TreeMap<Long intervalKey, byte[symbolId]>} (1=T1,2=T2,3=T3,0=unknown),
 * intervalKey = time / (number_minute_update * TIME_MINUTE). Ghi GZIP + ObjectOutputStream.
 *
 * <p>Chạy: {@code ExportCoinTierStatic <startYYYYMMDD> <endYYYYMMDD> <outFile>} với
 * {@code -Duser.timezone=Asia/Ho_Chi_Minh}. KHÔNG bật WFO_STATIC_RANK (cần LIVE ranking để sinh).
 */
public class ExportCoinTierStatic {
    private static final Logger LOG = LoggerFactory.getLogger(ExportCoinTierStatic.class);

    public static void main(String[] args) throws Exception {
        if (args.length < 3) {
            LOG.error("Usage: ExportCoinTierStatic <startYYYYMMDD> <endYYYYMMDD> <outFile>");
            System.exit(2);
        }
        // LIVE ranking để sinh data: tắt static. Cluster đọc theo config box AEROSPIKE_READ_CLUSTER=226 (Oracle local).
        Configs.WFO_STATIC_RANK = false;

        long startTs = Utils.sdfFile.parse(args[0]).getTime();
        long endTs = Utils.sdfFile.parse(args[1]).getTime();
        String outFile = args[2];

        SimpleSymbolMapper.getInstance().init();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();

        long intervalLenMs = (long) CoinRankManager.number_minute_update * Utils.TIME_MINUTE;
        LOG.info("=== EXPORT CoinTier static {} -> {} (intervalLen={}m) ===",
                args[0], args[1], CoinRankManager.number_minute_update);

        TreeMap<Long, byte[]> result = new TreeMap<>();
        long lastKey = Long.MIN_VALUE;
        int days = 0, minutesSeen = 0;

        long dayStart = startTs;
        while (dayStart < endTs) {
            TreeMap<Long, KlineObjectSimple[]> day =
                    DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey(dayStart);
            if (day != null && !day.isEmpty()) {
                days++;
                for (Map.Entry<Long, KlineObjectSimple[]> e : day.entrySet()) {
                    long time = e.getKey();
                    KlineObjectSimple[] snapshot = e.getValue();

                    // Đúng đường live: nuôi ring buffer rồi trigger ranking (updateRanking chỉ chạy tại phút-0/giờ).
                    HistoryManager.getInstance().updateHistoryArray(snapshot);
                    CoinRankManager.getInstance().getTopCoinShort(time);
                    minutesSeen++;

                    long key = time / intervalLenMs;
                    if (key != lastKey) {
                        result.put(key, CoinRankManager.getInstance().exportCurrentTierBytes());
                        lastKey = key;
                    }
                }
            } else {
                LOG.warn("Khong co kline ngay {}", Utils.normalizeDateYYYYMMDD(dayStart));
            }
            dayStart += Utils.TIME_DAY;
        }

        // OOM-safe: result ~ (#interval × 5000B). 5 nam hourly ~ 220MB raw, GZIP nho hon nhieu.
        File out = new File(outFile);
        if (out.getParentFile() != null) out.getParentFile().mkdirs();
        try (ObjectOutputStream oos = new ObjectOutputStream(
                new GZIPOutputStream(new BufferedOutputStream(new FileOutputStream(out))))) {
            oos.writeObject(result);
        }
        LOG.info("✅ DONE export: days={} minutes={} intervals={} -> {} ({} bytes)",
                days, minutesSeen, result.size(), outFile, out.length());
        LOG.info("EXPORT_COINTIER_DONE intervals={}", result.size());
    }

    /** Nạp artifact tĩnh từ file (GZIP + ObjectInputStream) -> NavigableMap để đưa vào CoinRankManager. */
    @SuppressWarnings("unchecked")
    public static NavigableMap<Long, byte[]> load(String path) throws IOException, ClassNotFoundException {
        try (ObjectInputStream ois = new ObjectInputStream(
                new GZIPInputStream(new BufferedInputStream(new FileInputStream(path))))) {
            return (TreeMap<Long, byte[]>) ois.readObject();
        }
    }
}
