package com.binance.chuyennd.research;

import com.binance.chuyennd.ai_ml.hpo.kaggle.KaggleDataLoader;
import com.binance.chuyennd.object.sw.KlineObjectSimple;

import java.io.FileWriter;
import java.io.PrintWriter;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Map;
import java.util.TimeZone;
import java.util.TreeMap;

/**
 * Dump BTC (symId=1) daily close tu tick-data (kaggle_data_hpo) — nguon gia CHINH ma sim giao dich
 * (docs/PREREG_REGIME_GATE.md). Bucket theo UTC-day (startTime/86400000); daily close = bar co
 * startTime LON nhat trong ngay UTC. Doc lap timezone (bucket theo epoch tuyet doi).
 *
 * <p>Args: startYYYYMMDD endYYYYMMDD outCsv. Chay voi cwd co symlink {@code kaggle_data_hpo}.
 * Output CSV: {@code utcDay,dateUTC,lastTs,close}.
 */
public class DumpBtcDaily {
    private static final long DAY_MS = 86400000L;

    public static void main(String[] args) throws Exception {
        SimpleDateFormat file = new SimpleDateFormat("yyyyMMdd"); // tz he thong: CHI chon ten file
        long start = file.parse(args[0]).getTime();
        long end = file.parse(args[1]).getTime();
        String out = args[2];

        TreeMap<Long, long[]> dayLast = new TreeMap<>(); // utcDay -> {maxTs, closeBits}
        int files = 0;
        long barsSeen = 0;
        for (long d = start; d <= end; d += DAY_MS) {
            TreeMap<Long, KlineObjectSimple[]> data = KaggleDataLoader.loadDailyTickersShort(d);
            if (data == null || data.isEmpty()) continue;
            files++;
            for (Map.Entry<Long, KlineObjectSimple[]> e : data.entrySet()) {
                KlineObjectSimple[] arr = e.getValue();
                if (arr == null || arr.length <= 1 || arr[1] == null) continue;
                KlineObjectSimple k = arr[1];
                if (k.startTime == null) continue;
                long ts = k.startTime;
                long ud = Math.floorDiv(ts, DAY_MS);
                long[] cur = dayLast.get(ud);
                if (cur == null || ts > cur[0]) {
                    dayLast.put(ud, new long[]{ts, Float.floatToRawIntBits(k.priceClose)});
                }
                barsSeen++;
            }
        }

        SimpleDateFormat u = new SimpleDateFormat("yyyy-MM-dd");
        u.setTimeZone(TimeZone.getTimeZone("UTC"));
        try (PrintWriter pw = new PrintWriter(new FileWriter(out))) {
            pw.println("utcDay,dateUTC,lastTs,close");
            for (Map.Entry<Long, long[]> e : dayLast.entrySet()) {
                long ud = e.getKey();
                long ts = e.getValue()[0];
                float close = Float.intBitsToFloat((int) e.getValue()[1]);
                pw.println(ud + "," + u.format(new Date(ud * DAY_MS)) + "," + ts + "," + close);
            }
        }
        System.out.println("DUMP_BTC_DAILY files=" + files + " barsSeen=" + barsSeen
                + " days=" + dayLast.size() + " -> " + out);
    }
}
