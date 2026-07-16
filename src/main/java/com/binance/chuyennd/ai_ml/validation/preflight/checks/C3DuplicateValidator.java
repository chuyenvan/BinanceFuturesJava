package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.policy.ScanPolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicLong;

/**
 * C3 — Chặn TRÙNG LẶP (ts, symbol): mỗi nguồn không được có hai bản ghi cùng cặp (timestamp, symId).
 * Mức BLOCK ({@code DATA_VALIDATION_FRAMEWORK.md} §2 C3).
 *
 * <p>Nguồn nến 1m ({@code kline_1m_opt}): mỗi phút = 1 record (key = yyyyMMdd-HHmm, DUY NHẤT theo thiết kế
 * Aerospike), chứa map symbol→nến. Vì vậy trùng (ts, symId) chỉ có thể sinh khi HAI symbol thô KHÁC nhau
 * bị CHUẨN-HOÁ về cùng một symbol đầy đủ — chính là rủi ro bug ghost USDC §5.5 (chuẩn-hoá
 * {@code sym.endsWith("USDT") ? sym : sym+"USDT"} khiến "BTC" và "BTCUSDT" đụng nhau). C3 phát hiện đúng
 * va chạm này TRONG mỗi phút. Chỉ ĐỌC, full-scan rẻ, chạy inline.</p>
 *
 * <p>WRAP tinh thần {@code CheckGap*} (đếm/đối chiếu key theo phút) nhưng tập trung vào TRÙNG thay vì GAP.
 * Dùng cùng chuẩn-hoá symbol với {@code DataManagerAerospikeFloatSim.convertProtoMapToJavaMap} để va chạm
 * đo ở đây khớp đúng va chạm mà pipeline thật gặp.</p>
 *
 * <p>TODO-verify: (1) trùng liên-phút là bất khả do key phút duy nhất — nếu về sau nguồn pred (gate/selector)
 * lưu THEO (symId) rời rạc thì cần scan-key-set riêng để bắt trùng cross-record; (2) xác nhận không nguồn nào
 * lưu nhiều record/phút.</p>
 */
public final class C3DuplicateValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(C3DuplicateValidator.class);

    private static final int MAX_SAMPLES = 50;

    @Override
    public CheckId id() {
        return CheckId.C3;
    }

    /**
     * Full-scan set nến 1m; trong mỗi phút, phát hiện symbol trùng sau chuẩn-hoá USDT.
     *
     * @param ctx ngữ cảnh (cần {@link PreflightContext#client()} != null)
     * @return FAIL (BLOCK) nếu có cặp (ts, symId) trùng; PASS kèm metrics (số phút, số cặp, số trùng)
     * @throws IllegalStateException nếu thiếu client hoặc scan trả 0 record (NEEDS_HUMAN)
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) {
        AerospikeClient client = ctx.client();
        if (client == null) {
            throw new IllegalStateException("C3: thiếu Aerospike client trong PreflightContext (226/Oracle).");
        }

        AtomicLong minutesScanned = new AtomicLong();
        AtomicLong pairs = new AtomicLong();
        AtomicLong duplicates = new AtomicLong();
        AtomicLong decodeErrors = new AtomicLong();
        List<String> samples = new CopyOnWriteArrayList<>();

        ScanPolicy sp = new ScanPolicy();
        sp.concurrentNodes = true;
        client.scanAll(sp, Configs.AEROSPIKE_NAMESPACE, DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER,
                (key, rec) -> {
                    minutesScanned.incrementAndGet();
                    byte[] compressed = (byte[]) rec.getValue("data");
                    if (compressed == null) {
                        return;
                    }
                    Map<String, KlineObjectOptimized> tickers;
                    try {
                        tickers = MinuteDataFinal.parseFrom(Snappy.uncompress(compressed)).getTickersMap();
                    } catch (Exception e) {
                        decodeErrors.incrementAndGet();
                        if (samples.size() < MAX_SAMPLES) {
                            samples.add(key.userKey + "|decodeErr:" + e.getClass().getSimpleName());
                        }
                        return;
                    }
                    // Va chạm sau chuẩn-hoá symbol TRONG cùng 1 phút = trùng (ts, symId).
                    Set<String> seen = new HashSet<>();
                    for (String rawSym : tickers.keySet()) {
                        pairs.incrementAndGet();
                        String full = normalize(rawSym);
                        if (!seen.add(full)) {
                            duplicates.incrementAndGet();
                            if (samples.size() < MAX_SAMPLES) {
                                samples.add(key.userKey + "|dup symId=" + full + " (raw=" + rawSym + ")");
                            }
                        }
                    }
                }, "data");

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("set", DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER);
        metrics.put("minutesScanned", minutesScanned.get());
        metrics.put("tsSymPairs", pairs.get());
        metrics.put("duplicates", duplicates.get());
        metrics.put("decodeErrors", decodeErrors.get());
        metrics.put("samples", samples);

        if (minutesScanned.get() == 0) {
            throw new IllegalStateException("C3: scan trả 0 record set "
                    + DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER + " — nghi sai namespace/set/kết nối (NEEDS_HUMAN).");
        }
        long violations = duplicates.get() + decodeErrors.get();
        if (violations > 0) {
            return ValidationResult.fail(id(),
                    "Trùng (ts, symId): " + duplicates.get() + " cặp trùng, " + decodeErrors.get()
                            + " phút decode lỗi (mẫu: " + samples + ").", metrics);
        }
        return ValidationResult.pass(id(),
                "Không trùng (ts, symId): " + pairs.get() + " cặp / " + minutesScanned.get() + " phút.", metrics);
    }

    /**
     * Chuẩn-hoá symbol GIỐNG pipeline thật ({@code convertProtoMapToJavaMap}): thêm "USDT" nếu thiếu đuôi.
     *
     * @param rawSym symbol thô trong DB (vd "BTC" hoặc "BTCUSDT")
     * @return symbol đầy đủ
     */
    private static String normalize(String rawSym) {
        return rawSym.endsWith("USDT") ? rawSym : rawSym + "USDT";
    }
}
