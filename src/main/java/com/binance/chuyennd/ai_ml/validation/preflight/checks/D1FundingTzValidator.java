package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.policy.ScanPolicy;
import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import com.google.gson.reflect.TypeToken;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.lang.reflect.Type;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicLongArray;

/**
 * D1 — Chặn TIMEZONE LỆCH ở settlement funding (GMT+7 vs UTC).
 *
 * <p>Cơ chế: quét set {@code funding_data} (mỗi record = 1 symbol, bin {@code f_data} nén Snappy chứa
 * JSON {@code Map<tsMs, rate>}; legacy {@code f_map} = CDT Map). Với mỗi mốc settlement, tính giờ/phút
 * theo UTC. Funding của Binance LUÔN chốt trên lưới UTC chẵn: {00,08,16}h (chu kỳ 8h) hoặc
 * {00,04,08,12,16,20}h (chu kỳ 4h), phút = 00. Nếu dữ liệu bị lưu theo GMT+7 thì mọi mốc bị đẩy +7h
 * → rơi vào giờ LẺ (07,15,23 hoặc 11,19,03) — điều KHÔNG BAO GIỜ xảy ra trên lưới UTC. Vì vậy "giờ lẻ"
 * (hour % 2 == 1) hoặc "phút != 0" là chữ ký chắc chắn của lệch timezone / offset.</p>
 *
 * <p>Mức WARN ({@code DATA_VALIDATION_FRAMEWORK §2/§4b}) — cần người xác nhận vì có thể là dữ liệu nguồn
 * bất thường chứ không nhất thiết lỗi pipeline. Trả metrics số: phân bố mốc theo tiêu chí lưới UTC +
 * đếm giờ lẻ / phút lệch + giờ vi phạm nhiều nhất.</p>
 *
 * <p>TODO(verify): nếu dự án dùng chu kỳ funding khác 4h/8h, cập nhật lại lưới hợp lệ. Hiện coi
 * {@code hour % 4 == 0 && minute == 0} là hợp lệ (phủ cả 4h lẫn 8h).</p>
 */
public final class D1FundingTzValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(D1FundingTzValidator.class);

    /** Set funding (mirror {@code DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_FUNDINGFEE}). */
    private static final String SET_FUNDING = "funding_data";

    private static final Type MAP_STR_FLOAT = new TypeToken<Map<String, Float>>() {
    }.getType();

    @Override
    public CheckId id() {
        return CheckId.D1;
    }

    /**
     * Quét funding_data, tính giờ/phút UTC mỗi settlement, đếm mốc lệch lưới UTC.
     *
     * @param ctx ngữ cảnh (cần {@link PreflightContext#client()} != null — client 226 theo CORE)
     * @return WARN nếu có mốc giờ lẻ / phút != 0 (chữ ký GMT+7); PASS nếu mọi mốc trên lưới UTC chẵn.
     *         Luôn kèm metrics số.
     * @throws IllegalStateException nếu thiếu Aerospike client (lỗi hạ tầng → gate xử NEEDS_HUMAN)
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) {
        AerospikeClient client = ctx.client();
        if (client == null) {
            throw new IllegalStateException("D1: thiếu Aerospike client trong PreflightContext (226/Oracle).");
        }

        AtomicLong symbols = new AtomicLong();
        AtomicLong settlements = new AtomicLong();
        AtomicLong onGrid4h = new AtomicLong();     // hour % 4 == 0 && minute == 0 (hợp lệ UTC)
        AtomicLong stdGrid8h = new AtomicLong();     // hour in {0,8,16} && minute == 0
        AtomicLong oddHour = new AtomicLong();       // hour % 2 == 1 → chữ ký GMT+7
        AtomicLong nonZeroMinute = new AtomicLong(); // phút != 0 → lệch offset
        AtomicLong decodeErrors = new AtomicLong();
        AtomicLongArray hourHist = new AtomicLongArray(24);

        ScanPolicy sp = new ScanPolicy();
        sp.concurrentNodes = true;
        sp.includeBinData = true;

        client.scanAll(sp, Configs.AEROSPIKE_NAMESPACE, SET_FUNDING, (key, rec) -> {
            symbols.incrementAndGet();
            Map<String, Float> map = decodeFunding(rec, key == null ? "?" : String.valueOf(key.userKey), decodeErrors);
            if (map == null) {
                return;
            }
            for (String tsStr : map.keySet()) {
                long ts;
                try {
                    ts = Long.parseLong(tsStr.trim());
                } catch (NumberFormatException nfe) {
                    decodeErrors.incrementAndGet();
                    continue;
                }
                settlements.incrementAndGet();
                ZonedDateTime utc = Instant.ofEpochMilli(ts).atZone(ZoneOffset.UTC);
                int hour = utc.getHour();
                int minute = utc.getMinute();
                hourHist.incrementAndGet(hour);
                if (minute != 0) {
                    nonZeroMinute.incrementAndGet();
                }
                if (hour % 2 == 1) {
                    oddHour.incrementAndGet();
                }
                if (hour % 4 == 0 && minute == 0) {
                    onGrid4h.incrementAndGet();
                }
                if ((hour == 0 || hour == 8 || hour == 16) && minute == 0) {
                    stdGrid8h.incrementAndGet();
                }
            }
        }, "f_data", "f_map");

        long total = settlements.get();
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("symbols", symbols.get());
        metrics.put("settlements", total);
        metrics.put("onGrid4hUtc", onGrid4h.get());
        metrics.put("stdGrid8hUtc", stdGrid8h.get());
        metrics.put("oddHour", oddHour.get());
        metrics.put("nonZeroMinute", nonZeroMinute.get());
        metrics.put("decodeErrors", decodeErrors.get());
        metrics.put("topOffendingHours", topOffendingHours(hourHist));

        if (total == 0) {
            // Không có settlement nào để kiểm — không kết luận PASS bừa.
            throw new IllegalStateException(
                    "D1: set '" + SET_FUNDING + "' không có mốc funding nào (symbols=" + symbols.get()
                            + ", decodeErrors=" + decodeErrors.get() + ") — nghi sai client/route hoặc set rỗng.");
        }

        long offGrid = oddHour.get() + nonZeroMinute.get();
        if (offGrid > 0) {
            return ValidationResult.warn(id(),
                    "Funding lệch lưới UTC: " + oddHour.get() + " mốc giờ LẺ + " + nonZeroMinute.get()
                            + " mốc phút != 0 (chữ ký GMT+7/offset). Giờ vi phạm nhiều nhất: "
                            + metrics.get("topOffendingHours") + ". Kỳ vọng chốt tại 00/08/16h (hoặc lưới 4h) UTC.",
                    metrics);
        }
        return ValidationResult.pass(id(),
                "Toàn bộ " + total + " mốc funding nằm trên lưới UTC chẵn (00/08/16h; " + onGrid4h.get()
                        + " trên lưới 4h), phút = 0.", metrics);
    }

    /**
     * Giải mã record funding: ưu tiên {@code f_data} (Snappy JSON), fallback legacy {@code f_map} (CDT Map).
     *
     * @param rec          record Aerospike
     * @param symbol       symbol (để log khi lỗi)
     * @param decodeErrors bộ đếm lỗi giải mã (cập nhật khi record hỏng — KHÔNG nuốt lỗi im lặng)
     * @return map {@code <tsMs, rate>} (key dạng chuỗi số); null nếu record rỗng/không giải mã được
     */
    @SuppressWarnings("unchecked")
    private Map<String, Float> decodeFunding(com.aerospike.client.Record rec, String symbol, AtomicLong decodeErrors) {
        if (rec == null) {
            return null;
        }
        Object blob = rec.getValue("f_data");
        if (blob instanceof byte[]) {
            try {
                String json = new String(Snappy.uncompress((byte[]) blob), "UTF-8");
                return Utils.gson.fromJson(json, MAP_STR_FLOAT);
            } catch (Exception e) {
                decodeErrors.incrementAndGet();
                LOG.warn("D1: lỗi giải mã f_data symbol={} — {}", symbol, e.toString());
                return null;
            }
        }
        Map<?, ?> legacy = rec.getMap("f_map");
        if (legacy != null && !legacy.isEmpty()) {
            Map<String, Float> out = new LinkedHashMap<>();
            legacy.forEach((k, v) -> out.put(String.valueOf(k), ((Number) v).floatValue()));
            return out;
        }
        return null;
    }

    /**
     * Lấy tối đa 5 giờ (UTC) có nhiều mốc nhất trong số các giờ LẺ hoặc ngoài lưới 4h (giờ vi phạm).
     *
     * @param hourHist histogram 24 giờ
     * @return map "giờ -> số mốc" của các giờ vi phạm, rỗng nếu không có
     */
    private Map<String, Long> topOffendingHours(AtomicLongArray hourHist) {
        Map<String, Long> offenders = new LinkedHashMap<>();
        for (int h = 0; h < 24; h++) {
            long c = hourHist.get(h);
            if (c > 0 && h % 4 != 0) {
                offenders.put(String.format("%02dh", h), c);
            }
        }
        return offenders;
    }
}
