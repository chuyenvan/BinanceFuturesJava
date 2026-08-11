package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.List;
import java.util.TimeZone;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * TASK-251 — FILL-GAP đoạn cuối history OI/LS/taker (2026-06-16 -> 2026-07-01) qua ĐÚNG pattern
 * TASK-013 (nguồn {@code data.binance.vision}, KHÔNG dùng REST /futures/data/* trực tiếp vì API đó chỉ
 * giữ ~30 ngày gần nhất — đã đo thật 2026-08-05: startTime > 30 ngày trước bị Binance trả lỗi -1130).
 *
 * <p>KHÁC {@link BackfillOiMaster}/{@link BackfillOiWorker}: tool này là ONE-SHOT đơn giản, KHÔNG dùng
 * queue {@code oi_backfill_queue}/{@code oi_backfill_done} — vì hầu hết symbol đã có {@code oi_backfill_done}
 * từ lần backfill full-history trước (tới 2026-06-16), nếu tái dùng Master/Worker sẽ bị {@code isDone()}
 * chặn tất cả (skip toàn bộ, không enqueue được đoạn mới) trừ khi {@code --reset} (mất bookkeeping DONE
 * toàn bộ history — không cần cho việc nhỏ này). Ghi vẫn qua {@link DataManagerAerospikeFloatSim#writeMetricMap226}
 * (merge-guard, idempotent, không đụng {@code oi_backfill_done}) nên an toàn chạy lại nhiều lần.
 *
 * <p>Args: {@code <start yyyyMMdd> <end yyyyMMdd> [run] [SYMBOL,SYMBOL,...]}. Không có {@code run} ->
 * DRY-RUN (chỉ liệt kê #điểm sẽ ghi). Không liệt kê symbol -> lấy TOÀN BỘ universe từ S3 listing
 * (giống {@link BackfillOiMaster} mặc định, đảm bảo survivorship symbol đã delist sau 2026-07-01 nhưng
 * còn sống trong khoảng cần fill vẫn được xử lý).
 */
public class OiFillGapVision {
    private static final Logger LOG = LoggerFactory.getLogger(OiFillGapVision.class);
    private static final int DOWNLOAD_THREADS = 8;

    public static void main(String[] args) {
        if (args.length < 2) {
            System.err.println("Usage: OiFillGapVision <start yyyyMMdd> <end yyyyMMdd> [run] [SYM1,SYM2,...]");
            System.exit(1);
        }
        long startMs = parseDate(args[0], true);
        long endMs = parseDate(args[1], false);
        boolean run = false;
        List<String> explicit = new ArrayList<>();
        for (int i = 2; i < args.length; i++) {
            String a = args[i];
            if ("run".equalsIgnoreCase(a)) run = true;
            else {
                for (String s : a.split("[,\\s]+")) {
                    if (!s.trim().isEmpty()) explicit.add(s.trim().toUpperCase());
                }
            }
        }
        try {
            new OiFillGapVision().run(startMs, endMs, run, explicit);
        } catch (Exception e) {
            LOG.error("❌ Lỗi nghiêm trọng: ", e);
            System.exit(1);
        }
        System.exit(0);
    }

    private static long parseDate(String yyyymmdd, boolean startOfDay) {
        try {
            SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd");
            f.setTimeZone(TimeZone.getTimeZone("UTC"));
            long t = f.parse(yyyymmdd.trim()).getTime();
            return startOfDay ? t : t + 24 * 60 * 60_000L - 1;
        } catch (Exception e) {
            throw new IllegalArgumentException("Không parse được ngày '" + yyyymmdd + "' (cần yyyyMMdd): " + e.getMessage());
        }
    }

    private void run(long startMs, long endMs, boolean doRun, List<String> explicit) throws Exception {
        VisionMetricsClient vision = new VisionMetricsClient();
        List<String> symbols;
        if (!explicit.isEmpty()) {
            symbols = explicit;
            LOG.info("🧪 Universe từ args: {} symbol.", symbols.size());
        } else {
            TreeSet<String> all = vision.listSymbols();
            symbols = new ArrayList<>(all);
            LOG.info("🌐 Universe từ S3 listing data.binance.vision: {} symbol.", symbols.size());
        }
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm");
        sdf.setTimeZone(TimeZone.getTimeZone("UTC"));
        LOG.info("===== [TASK-251] OI FILL-GAP-VISION mode={} range=[{}..{}] symbols={} =====",
                doRun ? "RUN" : "DRY-RUN", sdf.format(startMs), sdf.format(endMs), symbols.size());

        int touched = 0, emptyCount = 0, errCount = 0;
        long totalPoints = 0;
        for (int i = 0; i < symbols.size(); i++) {
            String symbol = symbols.get(i);
            try {
                VisionMetricsClient.SymbolMetrics m = vision.fetchSymbol(symbol, DOWNLOAD_THREADS, startMs, endMs);
                int totalTs = VisionMetricsClient.totalTs(m);
                if (totalTs == 0) {
                    emptyCount++;
                    continue;
                }
                if (doRun) {
                    int writeFails = 0;
                    for (int mi = 0; mi < OiMetricSets.ALL.length; mi++) {
                        TreeMap<Long, Float> map = m.maps[mi];
                        if (map.isEmpty()) continue;
                        OiMetricSets.Metric metric = OiMetricSets.ALL[mi];
                        writeFails += DataManagerAerospikeFloatSim.writeMetricMap226(metric.set, metric.bin, symbol, map);
                    }
                    if (writeFails > 0) {
                        errCount++;
                        LOG.error("❌ {} có {} chunk-tháng GHI LỖI (giữ để chạy lại sau, KHÔNG mark gì cả vì tool này không dùng done-set).", symbol, writeFails);
                        continue;
                    }
                    LOG.info("✅ [{}/{}] {} ghi xong | filesOk={} rawRows={} | OI ts-range[{}..{}] #ts={}",
                            i + 1, symbols.size(), symbol, m.filesOk, m.rawRows,
                            m.maps[0].isEmpty() ? "-" : sdf.format(m.maps[0].firstKey()),
                            m.maps[0].isEmpty() ? "-" : sdf.format(m.maps[0].lastKey()), totalTs);
                } else {
                    LOG.info("[DRY {}/{}] {} sẽ ghi | filesOk={} rawRows={} | OI ts-range[{}..{}] #ts={}",
                            i + 1, symbols.size(), symbol, m.filesOk, m.rawRows,
                            m.maps[0].isEmpty() ? "-" : sdf.format(m.maps[0].firstKey()),
                            m.maps[0].isEmpty() ? "-" : sdf.format(m.maps[0].lastKey()), totalTs);
                }
                touched++;
                totalPoints += totalTs;
            } catch (Exception e) {
                errCount++;
                LOG.warn("⚠️ {} bỏ qua (lỗi tải/parse): {}", symbol, e.getMessage());
            }
        }
        LOG.info("===== FILL-GAP-VISION xong: touched={} | empty(no-data-trong-range)={} | error={} | tổng-điểm(OI-đại-diện)={} | mode={} =====",
                touched, emptyCount, errCount, totalPoints, doRun ? "RUN" : "DRY-RUN");
    }
}
