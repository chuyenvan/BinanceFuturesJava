package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.policy.BatchPolicy;
import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.ExpectedRanges;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * D2 — Chặn GAP THỜI GIAN (ngày &lt; 1440 phút bị SKIP im lặng).
 *
 * <p>WRAP logic quét gap của {@code aerospike.validate_data.marketobject.CheckGapMarketObject}
 * ({@code scanMissingData}) và {@code ticker.CheckGapTicker} ({@code getMissingTimestamps}): cùng kỹ
 * thuật {@code client.exists(batch)} theo từng phút (key {@code "yyyyMMdd-HHmm"}). Điểm KHÁC (giá trị
 * gia tăng): (1) dùng {@link PreflightContext#client()} thay vì tự {@code new client} (CORE: mọi thứ
 * chạm 242 đi qua read-client 226); (2) GOM theo NGÀY và đối chiếu mốc 1440 phút/ngày; (3) TRẢ metrics
 * số + danh sách ngày thiếu (2 tool cũ chỉ log hoặc trả list phẳng).</p>
 *
 * <p>Nguồn quét: {@code market_data_object} và {@code kline_1m_opt} (mirror hằng số
 * {@code DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_MARKET_DATA} và set ticker trong
 * {@code CheckGapTicker}). Mức WARN ({@code DATA_VALIDATION_FRAMEWORK §2}).</p>
 *
 * <p>TODO(verify): §4b cho phép ESCALATE D2 → BLOCK nếu gap chạm majors (BTC/ETH) HOẶC làm 1 cửa sổ WFO
 * tụt dưới ngưỡng coverage A1. Việc escalate cần cross-check với A1/universe (không có trong ngữ cảnh
 * check này) → để {@code PreflightGate} quyết dựa trên metrics {@code totalMissingMinutes}/ngày thiếu ở
 * đây; validator này giữ mức WARN.</p>
 *
 * <p>TODO(verify): range mặc định {@code 20210101 → now-2d} chép từ 2 tool cũ; nếu
 * {@link ExpectedRanges} đã khai báo range nguồn thì ưu tiên dùng khai báo đó.</p>
 */
public final class D2TimeGapValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(D2TimeGapValidator.class);

    private static final String SET_MARKET = "market_data_object";
    private static final String SET_TICKER = "kline_1m_opt";

    private static final String DEFAULT_START_DAY = "20210101";
    private static final long MINUTE_MS = 60_000L;
    private static final long DAY_MS = 86_400_000L;
    private static final int FULL_DAY_MINUTES = 1440;
    private static final int BATCH_SIZE = 5000;
    private static final int MAX_LOGGED_DAYS = 50;

    @Override
    public CheckId id() {
        return CheckId.D2;
    }

    /**
     * Quét gap 2 nguồn (market + ticker), gom theo ngày, đối chiếu 1440 phút/ngày.
     *
     * @param ctx ngữ cảnh (cần {@link PreflightContext#client()} != null — read-client 226)
     * @return WARN nếu có ngày thiếu phút ở bất kỳ nguồn; PASS nếu mọi ngày đủ 1440. Luôn kèm metrics số.
     * @throws IllegalStateException nếu thiếu Aerospike client (lỗi hạ tầng → gate xử NEEDS_HUMAN)
     * @throws ParseException        nếu parse ngày mặc định lỗi (không xảy ra với hằng số hợp lệ)
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) throws ParseException {
        AerospikeClient client = ctx.client();
        if (client == null) {
            throw new IllegalStateException("D2: thiếu Aerospike client trong PreflightContext (226/Oracle).");
        }

        Map<String, Object> metrics = new LinkedHashMap<>();
        long grandMissing = 0;
        long grandIncompleteDays = 0;

        for (String set : new String[]{SET_MARKET, SET_TICKER}) {
            SourceScan scan = scanSource(client, ctx.expected(), set);
            Map<String, Object> sub = new LinkedHashMap<>();
            sub.put("daysTotal", scan.daysTotal);
            sub.put("daysComplete", scan.daysComplete);
            sub.put("daysIncomplete", scan.daysIncomplete);
            sub.put("totalMissingMinutes", scan.totalMissing);
            sub.put("worstDays", scan.worstDays);
            metrics.put(set, sub);
            grandMissing += scan.totalMissing;
            grandIncompleteDays += scan.daysIncomplete;
        }
        metrics.put("totalMissingMinutes", grandMissing);
        metrics.put("totalIncompleteDays", grandIncompleteDays);

        if (grandMissing > 0) {
            return ValidationResult.warn(id(),
                    "Gap thời gian: " + grandIncompleteDays + " ngày không đủ " + FULL_DAY_MINUTES
                            + " phút (tổng " + grandMissing + " phút thiếu). Xem metrics theo nguồn + worstDays. "
                            + "Nếu chạm majors / tụt coverage cửa sổ WFO thì gate escalate BLOCK (§4b).", metrics);
        }
        return ValidationResult.pass(id(),
                "Mọi ngày ở " + SET_MARKET + " và " + SET_TICKER + " đủ " + FULL_DAY_MINUTES + " phút.", metrics);
    }

    /**
     * Quét 1 nguồn theo từng phút bằng {@code exists(batch)}, gom present/expected theo ngày.
     *
     * @param client   read-client (226)
     * @param expected khai báo range pre-register (dùng nếu có, else default)
     * @param setName  tên set
     * @return kết quả gom theo ngày của nguồn
     * @throws ParseException nếu parse ngày mặc định lỗi
     */
    private SourceScan scanSource(AerospikeClient client, ExpectedRanges expected, String setName)
            throws ParseException {
        SimpleDateFormat keyFmt = new SimpleDateFormat("yyyyMMdd-HHmm");
        SimpleDateFormat dayFmt = new SimpleDateFormat("yyyyMMdd");

        long startMs;
        long endMs;
        ExpectedRanges.SourceRange sr = expected == null ? null : expected.source(setName);
        if (sr != null && sr.expectedStartMs > 0 && sr.expectedEndMs > sr.expectedStartMs) {
            startMs = floorToDay(sr.expectedStartMs);
            endMs = sr.expectedEndMs;
        } else {
            startMs = dayFmt.parse(DEFAULT_START_DAY).getTime();
            endMs = System.currentTimeMillis() - 2 * DAY_MS;
        }

        BatchPolicy bp = new BatchPolicy();
        bp.maxConcurrentThreads = 4;

        // Gom theo ngày: dayStr -> [present, expected]
        Map<String, long[]> byDay = new LinkedHashMap<>();
        List<Long> timeBuffer = new ArrayList<>(BATCH_SIZE);
        List<Key> keyBuffer = new ArrayList<>(BATCH_SIZE);

        LOG.info("D2: quét gap set [{}] từ {} tới {}", setName,
                dayFmt.format(new Date(startMs)), dayFmt.format(new Date(endMs)));

        for (long t = startMs; t <= endMs; t += MINUTE_MS) {
            timeBuffer.add(t);
            keyBuffer.add(new Key(Configs.AEROSPIKE_NAMESPACE, setName, keyFmt.format(new Date(t))));
            boolean flush = keyBuffer.size() == BATCH_SIZE || t + MINUTE_MS > endMs;
            if (!flush) {
                continue;
            }
            boolean[] exists = client.exists(bp, keyBuffer.toArray(new Key[0]));
            for (int i = 0; i < exists.length; i++) {
                String dayStr = dayFmt.format(new Date(timeBuffer.get(i)));
                long[] pe = byDay.computeIfAbsent(dayStr, k -> new long[2]);
                pe[1]++;                       // expected minute
                if (exists[i]) {
                    pe[0]++;                   // present minute
                }
            }
            timeBuffer.clear();
            keyBuffer.clear();
        }

        SourceScan out = new SourceScan();
        out.daysTotal = byDay.size();
        for (Map.Entry<String, long[]> e : byDay.entrySet()) {
            long present = e.getValue()[0];
            long expectedMin = e.getValue()[1];
            long missing = expectedMin - present;
            if (missing > 0) {
                out.daysIncomplete++;
                out.totalMissing += missing;
                if (out.worstDays.size() < MAX_LOGGED_DAYS) {
                    out.worstDays.add(e.getKey() + "(" + present + "/" + expectedMin + ")");
                }
            } else {
                out.daysComplete++;
            }
        }
        LOG.info("D2: [{}] daysTotal={} incomplete={} missingMinutes={}",
                setName, out.daysTotal, out.daysIncomplete, out.totalMissing);
        return out;
    }

    /** Làm tròn xuống 00:00 (UTC) của ngày chứa {@code ms}. */
    private long floorToDay(long ms) {
        return ms - (ms % DAY_MS);
    }

    /** Kết quả gom gap của MỘT nguồn. */
    private static final class SourceScan {
        private long daysTotal;
        private long daysComplete;
        private long daysIncomplete;
        private long totalMissing;
        private final List<String> worstDays = new ArrayList<>();
    }
}
