package com.binance.chuyennd.ai_ml.hpo.kaggle;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.ObjectOutputStream;
import java.util.Map;
import java.util.TreeMap;

/**
 * [2026-08-04] TASK-112b: Xuat ticker 1-phut/ngay tu Aerospike (qua getReadClient(),
 * bam theo AEROSPIKE_READ_CLUSTER cua config.properties CWD) ra file
 * kaggle_data_hpo/ticker_YYYYMMDD.bin (dinh dang giong het KaggleDataLoader.loadObject
 * doc lai - ObjectOutputStream serialize TreeMap<Long, Map<String, KlineObjectSimple>>,
 * KHONG gzip, khop convention .bin uncompressed cua dataset hpo-ticker-daily hien co).
 *
 * Dung de bo sung doan ngay con thieu tren Kaggle (vd 2026 H1) sau khi da
 * CopyTicker242To226 (nap tuoi) + CleanTickerGhostAndTail (don ghost/duoi-don) tren
 * cluster nguon. KHONG tu lam sach du lieu - tool nay chi doc-va-serialize nguyen ban.
 *
 * Args: [startDate yyyyMMdd] [endDate yyyyMMdd, loai tru] [outDir, default kaggle_data_hpo/]
 */
public class ExportTickerDaily {
    private static final Logger LOG = LoggerFactory.getLogger(ExportTickerDaily.class);

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            LOG.error("Cu phap: ExportTickerDaily <startDate yyyyMMdd> <endDate yyyyMMdd> [outDir]");
            System.exit(1);
            return;
        }
        String outDir = args.length >= 3 && !args[2].isEmpty() ? args[2] : "kaggle_data_hpo/";
        if (!outDir.endsWith("/")) outDir = outDir + "/";
        new File(outDir).mkdirs();

        long start = Utils.sdfFile.parse(args[0]).getTime();
        long end = Utils.sdfFile.parse(args[1]).getTime();

        LOG.info("EXPORT TICKER DAILY -> {} | {} -> {} (loai tru)", outDir, args[0], args[1]);

        int written = 0, emptyDays = 0;
        for (long day = start; day < end; day += 24L * Utils.TIME_HOUR) {
            String dayStr = Utils.sdfFile.format(new java.util.Date(day));
            TreeMap<Long, Map<String, KlineObjectSimple>> oneDay =
                    DataManagerAerospikeFloatSim.readDataFromAerospike1M(day);
            if (oneDay == null || oneDay.isEmpty()) {
                LOG.warn("Ngay {} RONG tren Aerospike - bo qua (khong ghi file).", dayStr);
                emptyDays++;
                continue;
            }
            String path = outDir + "ticker_" + dayStr + ".bin";
            try (ObjectOutputStream oos = new ObjectOutputStream(
                    new BufferedOutputStream(new FileOutputStream(path), 1024 * 1024))) {
                oos.writeObject(oneDay);
            }
            written++;
            if (written % 30 == 0) {
                LOG.info("... da ghi {} ngay (gan nhat {}), rong={}", written, dayStr, emptyDays);
            }
        }
        LOG.info("XONG: {} file .bin da ghi vao {} | ngay rong bo qua: {}", written, outDir, emptyDays);
        System.exit(0);
    }
}
