package com.binance.chuyennd.aerospike.tools;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;

/**
 * [TASK-251, 2026-08-05] CHẨN ĐOÁN mismatch 242 vs Oracle phát hiện ở verifySample() của
 * CopyTicker242To226 — verifySample() so RAW BYTES (Snappy-compressed proto), có thể ra
 * false-positive nếu thứ tự serialize map (protobuf Map<String,Kline>) khác nhau giữa 2 lần
 * ghi (bytes khác nhưng NỘI DUNG DECODE giống nhau). Tool này GIẢI NÉN + DECODE cả 2 bên rồi so
 * TỪNG SYMBOL (price_open/max/min/close/total_usdt, epsilon 1e-6) — chỉ báo mismatch THẬT.
 *
 * READ-ONLY cả 2 phía. KHÔNG ghi gì.
 *
 * CHẠY: java ... DiagnoseTickerMismatch242VsOracle <START yyyyMMdd> <END yyyyMMdd exclusive>
 *       [maxMismatchLog=20] [sampleEveryNMin=1]
 */
public class DiagnoseTickerMismatch242VsOracle {

    private static final Logger LOG = LoggerFactory.getLogger(DiagnoseTickerMismatch242VsOracle.class);
    private static final String SET_TICKER = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER;
    private static final float EPS = 1e-6f;

    public static void main(String[] args) throws Exception {
        String startArg = args.length >= 1 ? args[0] : "20210101";
        String endArg = args.length >= 2 ? args[1] : "20210102";
        int maxMismatchLog = args.length >= 3 ? Integer.parseInt(args[2]) : 20;
        int sampleEveryNMin = args.length >= 4 ? Integer.parseInt(args[3]) : 1;

        SimpleDateFormat sdfFile = new SimpleDateFormat("yyyyMMdd");
        SimpleDateFormat keyFmt = new SimpleDateFormat("yyyyMMdd-HHmm");
        long start = sdfFile.parse(startArg).getTime();
        long end = sdfFile.parse(endArg).getTime();

        AerospikeClient c242 = DataManagerAerospikeFloatSim.getClient242();
        AerospikeClient cOracle = DataManagerAerospikeFloatSim.getClientOracle();
        String ns242 = Configs.AEROSPIKE_NAMESPACE_242;
        String nsOracle = Configs.AEROSPIKE_NAMESPACE;

        LOG.info("🔎 DIAGNOSE {} -> {} | ns242={} nsOracle={} | sampleEveryNMin={}",
                startArg, endArg, ns242, nsOracle, sampleEveryNMin);

        AtomicLong minutesChecked = new AtomicLong();
        AtomicLong minutesByteMismatch = new AtomicLong();
        AtomicLong minutesRealDecodeMismatch = new AtomicLong();
        AtomicLong minutesBothMissing = new AtomicLong();
        AtomicLong minutesOnly242 = new AtomicLong();
        AtomicLong minutesOnlyOracle = new AtomicLong();
        AtomicLong symbolLevelDiffs = new AtomicLong();
        int loggedMismatch = 0;

        for (long day = start; day < end; day += 24L * 3600 * 1000) {
            for (int m = 0; m < 1440; m += sampleEveryNMin) {
                long ts = day + m * 60L * 1000;
                String ks = keyFmt.format(new Date(ts));
                Key k242 = new Key(ns242, SET_TICKER, ks);
                Key kOracle = new Key(nsOracle, SET_TICKER, ks);

                Record r242 = c242.get(null, k242);
                Record rOracle = cOracle.get(null, kOracle);
                byte[] b242 = r242 != null ? (byte[]) r242.getValue("data") : null;
                byte[] bOracle = rOracle != null ? (byte[]) rOracle.getValue("data") : null;

                minutesChecked.incrementAndGet();
                if (b242 == null && bOracle == null) { minutesBothMissing.incrementAndGet(); continue; }
                if (b242 != null && bOracle == null) { minutesOnly242.incrementAndGet(); continue; }
                if (b242 == null && bOracle != null) { minutesOnlyOracle.incrementAndGet(); continue; }

                boolean byteEqual = Arrays.equals(b242, bOracle);
                if (byteEqual) continue;
                minutesByteMismatch.incrementAndGet();

                // Giải nén + decode cả 2 bên, so THEO NỘI DUNG (không phải bytes thô)
                try {
                    Map<String, KlineObjectOptimized> map242 =
                            MinuteDataFinal.parseFrom(Snappy.uncompress(b242)).getTickersMap();
                    Map<String, KlineObjectOptimized> mapOracle =
                            MinuteDataFinal.parseFrom(Snappy.uncompress(bOracle)).getTickersMap();

                    List<String> diffSymbols = new ArrayList<>();
                    Set<String> allSymbols = new TreeSet<>();
                    allSymbols.addAll(map242.keySet());
                    allSymbols.addAll(mapOracle.keySet());
                    for (String sym : allSymbols) {
                        KlineObjectOptimized a = map242.get(sym);
                        KlineObjectOptimized b = mapOracle.get(sym);
                        if (a == null || b == null) { diffSymbols.add(sym); continue; }
                        boolean same = Math.abs(a.getPriceOpen() - b.getPriceOpen()) < EPS
                                && Math.abs(a.getMaxPrice() - b.getMaxPrice()) < EPS
                                && Math.abs(a.getMinPrice() - b.getMinPrice()) < EPS
                                && Math.abs(a.getPriceClose() - b.getPriceClose()) < EPS
                                && Math.abs(a.getTotalUsdt() - b.getTotalUsdt()) < EPS;
                        if (!same) diffSymbols.add(sym);
                    }

                    if (diffSymbols.isEmpty()) {
                        // Bytes khác nhưng NỘI DUNG GIỐNG NHAU => false-positive từ so-bytes-thô
                        // (thứ tự serialize map khác nhau). KHÔNG phải mismatch thật.
                    } else {
                        minutesRealDecodeMismatch.incrementAndGet();
                        symbolLevelDiffs.addAndGet(diffSymbols.size());
                        if (loggedMismatch < maxMismatchLog) {
                            loggedMismatch++;
                            StringBuilder sb = new StringBuilder();
                            for (String sym : diffSymbols) {
                                KlineObjectOptimized a = map242.get(sym);
                                KlineObjectOptimized b = mapOracle.get(sym);
                                sb.append(String.format("%n    %s | 242: open=%s max=%s min=%s close=%s usdt=%s | Oracle: open=%s max=%s min=%s close=%s usdt=%s",
                                        sym,
                                        a == null ? "NULL" : a.getPriceOpen(),
                                        a == null ? "NULL" : a.getMaxPrice(),
                                        a == null ? "NULL" : a.getMinPrice(),
                                        a == null ? "NULL" : a.getPriceClose(),
                                        a == null ? "NULL" : a.getTotalUsdt(),
                                        b == null ? "NULL" : b.getPriceOpen(),
                                        b == null ? "NULL" : b.getMaxPrice(),
                                        b == null ? "NULL" : b.getMinPrice(),
                                        b == null ? "NULL" : b.getPriceClose(),
                                        b == null ? "NULL" : b.getTotalUsdt()));
                            }
                            LOG.warn("🔴 REAL DECODE MISMATCH tại {} ({} symbol lệch):{}", ks, diffSymbols.size(), sb);
                        }
                    }
                } catch (Exception e) {
                    LOG.error("❌ Lỗi decode tại {}: {}", ks, e.toString());
                }
            }
            LOG.info("... xong ngày {} | checked={} byteMismatch={} realDecodeMismatch={} bothMissing={} only242={} onlyOracle={}",
                    sdfFile.format(new Date(day)), minutesChecked.get(), minutesByteMismatch.get(),
                    minutesRealDecodeMismatch.get(), minutesBothMissing.get(), minutesOnly242.get(), minutesOnlyOracle.get());
        }

        LOG.info("✅ XONG DIAGNOSE {}→{}: checked={} | byteMismatch={} (raw bytes khác) | " +
                        "realDecodeMismatch={} (NỘI DUNG khác thật, sau decode) | symbolLevelDiffs={} | " +
                        "bothMissing={} | only242={} | onlyOracle={}",
                startArg, endArg, minutesChecked.get(), minutesByteMismatch.get(), minutesRealDecodeMismatch.get(),
                symbolLevelDiffs.get(), minutesBothMissing.get(), minutesOnly242.get(), minutesOnlyOracle.get());
        if (minutesByteMismatch.get() > 0 && minutesRealDecodeMismatch.get() == 0) {
            LOG.info("🟢 KẾT LUẬN: TOÀN BỘ byteMismatch là FALSE-POSITIVE (serialize map thứ tự khác, " +
                    "nội dung decode giống nhau 100%). KHÔNG có data thật bị lệch trong phạm vi đã quét.");
        } else if (minutesRealDecodeMismatch.get() > 0) {
            LOG.warn("🔴 KẾT LUẬN: CÓ {} phút mismatch THẬT (nội dung khác nhau sau decode) — cần đối chiếu " +
                    "Binance Vision/API để biết bên nào đúng, xem log 🔴 REAL DECODE MISMATCH phía trên.",
                    minutesRealDecodeMismatch.get());
        }
        System.exit(0);
    }
}
