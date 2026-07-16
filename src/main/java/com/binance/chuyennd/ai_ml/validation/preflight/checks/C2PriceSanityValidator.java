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

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicLong;

/**
 * C2 — Chặn GIÁ PHI LÝ (0, âm, nhảy lớn — bug USDC-margin nhảy x1000):
 * giá &gt; 0; |Δ trong-nến| &lt; 50%; OHLC hợp lệ (high ≥ low ≥ 0, low ≤ close ≤ high, low ≤ open ≤ high).
 * Mức BLOCK ({@code DATA_VALIDATION_FRAMEWORK.md} §2 C2).
 *
 * <p>WRAP {@code aerospike/validate_data/marketobject/ValidateMarketObjectConsistency} và
 * {@code ticker/ValidateAerospikeVsBinance}: mượn nguồn dữ liệu nến 1m ({@code kline_1m_opt}) và cách
 * decode proto ({@link MinuteDataFinal} → {@code tickersMap}), NHƯNG thay vì so 20 mẫu với API Binance
 * (đắt, cần mạng), C2 FULL-SCAN kiểm tính hợp lệ NỘI TẠI mỗi nến — rẻ, chạy inline, chỉ ĐỌC 226.</p>
 *
 * <p>Bài học nền §5.5: coin margin-USDC tạo ticker ảo / scale sai → giá phi lý lọt vào backtest.
 * Kiểm nội tại bắt được: giá ≤ 0, high &lt; low, close/open ngoài [low, high], và cú nhảy open→close
 * ≥ 50% trong 1 phút.</p>
 *
 * <p><b>TODO-verify (giới hạn có chủ đích — "thà hẹp mà đúng"):</b> spec nói "|Δ 1 phút| &lt; 50%" giữa
 * hai nến LIỀN KỀ. Full-scan Aerospike KHÔNG trả record theo thứ tự thời gian/symbol nên bản này dùng
 * PROXY = biên độ trong-nến |close − open|/open (cú nhảy x1000 trong 1 phút vẫn lộ). Phần so close↔close
 * hai phút liền kề (bắt x1000 QUA biên phút) cần pass có-thứ-tự per-symbol HOẶC đối soát chéo Binance
 * ({@code ValidateAerospikeVsBinance}) — thuộc tầng đắt/sample, CHƯA gộp vào đây.</p>
 */
public final class C2PriceSanityValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(C2PriceSanityValidator.class);

    /** Ngưỡng nhảy giá trong 1 nến (spec §2 C2: 50%). */
    private static final double MAX_INTRA_MINUTE_MOVE = 0.50;

    /** Số mẫu vi phạm tối đa giữ lại (đa luồng → CopyOnWriteArrayList; tránh log phình). */
    private static final int MAX_SAMPLES = 50;

    @Override
    public CheckId id() {
        return CheckId.C2;
    }

    /**
     * Full-scan set nến 1m, kiểm tính hợp lệ nội tại mỗi nến.
     *
     * @param ctx ngữ cảnh (cần {@link PreflightContext#client()} != null — client 226 dùng chung)
     * @return FAIL (BLOCK) nếu có bất kỳ vi phạm (giá ≤ 0 / OHLC sai / nhảy ≥ 50% / decode lỗi); PASS kèm metrics
     * @throws IllegalStateException nếu thiếu Aerospike client (lỗi hạ tầng → NEEDS_HUMAN)
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) {
        AerospikeClient client = ctx.client();
        if (client == null) {
            throw new IllegalStateException("C2: thiếu Aerospike client trong PreflightContext (226/Oracle).");
        }

        AtomicLong minutesScanned = new AtomicLong();
        AtomicLong candles = new AtomicLong();
        AtomicLong nonPositive = new AtomicLong();
        AtomicLong ohlcInvalid = new AtomicLong();
        AtomicLong bigMove = new AtomicLong();
        AtomicLong decodeErrors = new AtomicLong();
        List<String> samples = new CopyOnWriteArrayList<>();

        ScanPolicy sp = new ScanPolicy();
        sp.concurrentNodes = true;
        // scanAll đa luồng: mọi biến đếm là AtomicLong, sample là CopyOnWriteArrayList.
        // KHÔNG bắt AerospikeException ở đây → lỗi hạ tầng propagate lên gate = NEEDS_HUMAN.
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
                        // Decode lỗi = data hỏng (KHÔNG câm): đếm + mẫu, tiếp tục (không gãy scan).
                        decodeErrors.incrementAndGet();
                        addSample(samples, String.valueOf(key.userKey), "?",
                                "decodeErr:" + e.getClass().getSimpleName());
                        return;
                    }
                    for (Map.Entry<String, KlineObjectOptimized> en : tickers.entrySet()) {
                        candles.incrementAndGet();
                        KlineObjectOptimized k = en.getValue();
                        double open = k.getPriceOpen();
                        double high = k.getMaxPrice();
                        double low = k.getMinPrice();
                        double close = k.getPriceClose();

                        if (open <= 0 || high <= 0 || low <= 0 || close <= 0) {
                            nonPositive.incrementAndGet();
                            addSample(samples, String.valueOf(key.userKey), en.getKey(),
                                    String.format("price<=0 O=%s H=%s L=%s C=%s", open, high, low, close));
                            continue;
                        }
                        if (high < low || close > high || close < low || open > high || open < low) {
                            ohlcInvalid.incrementAndGet();
                            addSample(samples, String.valueOf(key.userKey), en.getKey(),
                                    String.format("OHLC sai O=%s H=%s L=%s C=%s", open, high, low, close));
                            continue;
                        }
                        double move = Math.abs(close - open) / open;
                        if (move >= MAX_INTRA_MINUTE_MOVE) {
                            bigMove.incrementAndGet();
                            addSample(samples, String.valueOf(key.userKey), en.getKey(),
                                    String.format("nhảy %.1f%% O=%s C=%s", move * 100, open, close));
                        }
                    }
                }, "data");

        long violations = nonPositive.get() + ohlcInvalid.get() + bigMove.get() + decodeErrors.get();
        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("set", DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER);
        metrics.put("minutesScanned", minutesScanned.get());
        metrics.put("candles", candles.get());
        metrics.put("nonPositive", nonPositive.get());
        metrics.put("ohlcInvalid", ohlcInvalid.get());
        metrics.put("bigMoveGE50pct", bigMove.get());
        metrics.put("decodeErrors", decodeErrors.get());
        metrics.put("violations", violations);
        metrics.put("samples", samples);

        if (minutesScanned.get() == 0) {
            throw new IllegalStateException("C2: scan trả 0 record set "
                    + DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER + " — nghi sai namespace/set/kết nối (NEEDS_HUMAN).");
        }
        if (violations > 0) {
            return ValidationResult.fail(id(),
                    "Giá phi lý: " + nonPositive.get() + " nến giá≤0, " + ohlcInvalid.get() + " OHLC sai, "
                            + bigMove.get() + " nến nhảy≥50%, " + decodeErrors.get() + " phút decode lỗi (mẫu: "
                            + samples + ").", metrics);
        }
        return ValidationResult.pass(id(),
                "Giá hợp lệ trên " + candles.get() + " nến / " + minutesScanned.get() + " phút "
                        + "(giá>0, OHLC hợp lệ, không nhảy≥50% trong-nến).", metrics);
    }

    /**
     * Thêm 1 mẫu vi phạm (giới hạn {@link #MAX_SAMPLES}).
     *
     * @param samples list chia sẻ đa luồng
     * @param minuteKey userKey của record (chuỗi yyyyMMdd-HHmm)
     * @param symbol   symbol trong nến
     * @param reason   mô tả vi phạm
     */
    private static void addSample(List<String> samples, String minuteKey, String symbol, String reason) {
        if (samples.size() < MAX_SAMPLES) {
            samples.add(minuteKey + "|" + symbol + "|" + reason);
        }
    }
}
