package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.ScanPolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.io.File;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * A3 — Chặn "coin trong pred KHÔNG có ticker thật" (ghost {@code *USDCUSDT}; bug coin margin-USDC nối
 * {@code endsWith("USDT")?...:sym+"USDT"} tại {@code DataManagerAerospikeFloatSim:940} → symId ảo không ticker
 * → vào lệnh "mù"; {@code DATA_VALIDATION_FRAMEWORK §5.5} + {@code WFO_DATAFLOW §9}).
 *
 * <p><b>Cơ chế:</b> mọi {@code symId} xuất hiện trong pred phải map ra symbol CÓ ticker thật:
 * <ol>
 *   <li>Gom symId phân biệt trong pred selector/funding (file {@code predict_wf_*.bin}, byte 8-9 mỗi record 26B).
 *       Gate là market-level (không symId) nên A3 kiểm nguồn có symId = funding/selector.</li>
 *   <li>Nạp {@code symbol_mapper} (id→symbol) qua {@code ctx.client()}.</li>
 *   <li>Quét set ticker {@code kline_1m_opt} gom TẬP symbol CÓ ticker thật (union key của proto tickersMap).</li>
 *   <li>Mỗi symId pred: (a) phải có trong mapper; (b) symbol KHÔNG khớp ghost {@code *USDCUSDT};
 *       (c) symbol phải nằm trong tập symbol-có-ticker. Vi phạm bất kỳ ⇒ FAIL (A3 = BLOCK).</li>
 * </ol></p>
 *
 * <p>Ghi chú {@code WFO_DATAFLOW §9}: 38 ghost USDC còn TRONG mapper (mapper chỉ tích luỹ) nhưng VÔ HẠI vì
 * không có ticker ⇒ không vào feature/pred. A3 xác nhận điều đó: nếu ghost LỌT vào pred (symId ghost xuất hiện)
 * ⇒ regression, phải chặn.</p>
 *
 * <p><b>TODO-verify-trên-data-thật:</b> (1) quét FULL {@code kline_1m_opt} (~2.8M record, giải nén proto) khá
 * NẶNG cho tầng FAST — nếu chậm, cân nhắc chuyển A3 sang tầng SLOW hoặc cache tập symbol-có-ticker; (2) xác nhận
 * regex ghost: hiện bắt {@code endsWith("USDCUSDT")} (gồm cả "USDCUSDT" trần lẫn "XXXUSDCUSDT" do bug nối) —
 * kiểm dữ liệu thật xem có biến thể khác (vd USDC không hậu tố USDT); (3) mapper bin tên {@code "data"},
 * set/key theo {@code AEROSPIKE_SET_NAME_MAPPER}/{@code MAPPER_KEY_GLOBAL}.</p>
 */
public final class A3GhostTickerValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(A3GhostTickerValidator.class);

    private static final int FUNDING_REC_BYTES = 26; // >q h 4f
    private static final String MAPPER_BIN = "data"; // = DataManagerAerospikeFloatSim.MAPPER_BIN_NAME (private)
    private static final String GHOST_SUFFIX = "USDCUSDT";
    private static final int MAX_LIST = 50;

    @Override
    public CheckId id() {
        return CheckId.A3;
    }

    /**
     * Kiểm mọi symId pred có ticker thật + không phải ghost USDC.
     *
     * @param ctx cần {@link PreflightContext#client()} != null và {@link PreflightContext#fundingPredDir()} có bin
     * @return FAIL (BLOCK) nếu có symId ghost / thiếu mapper / thiếu ticker; PASS kèm metrics
     * @throws IllegalStateException nếu thiếu client / fundingPredDir (lỗi hạ tầng → NEEDS_HUMAN)
     * @throws Exception nếu lỗi đọc file / giải nén
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) throws Exception {
        AerospikeClient client = ctx.client();
        if (client == null) {
            throw new IllegalStateException("A3: thieu Aerospike client (can nap mapper + quet ticker).");
        }
        String fundingDir = ctx.fundingPredDir();
        if (fundingDir == null || fundingDir.trim().isEmpty()) {
            throw new IllegalStateException("A3: thieu fundingPredDir — khong lay duoc symId pred de kiem ghost.");
        }

        Set<Short> predSymIds = collectPredSymIds(fundingDir);
        Map<Short, String> idToSym = loadMapper(client);
        Set<String> tickerSymbols = collectTickerSymbols(client);

        List<String> unmapped = new ArrayList<>();
        List<String> ghost = new ArrayList<>();
        List<String> noTicker = new ArrayList<>();

        for (Short symId : predSymIds) {
            String sym = idToSym.get(symId);
            if (sym == null) {
                if (unmapped.size() < MAX_LIST) unmapped.add(String.valueOf(symId));
                continue;
            }
            if (sym.endsWith(GHOST_SUFFIX)) {
                if (ghost.size() < MAX_LIST) ghost.add(symId + "=" + sym);
                continue; // ghost => cung khong co ticker; khong can bao trung noTicker
            }
            if (!tickerSymbols.contains(sym)) {
                if (noTicker.size() < MAX_LIST) noTicker.add(symId + "=" + sym);
            }
        }

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("predSymIds", predSymIds.size());
        metrics.put("mapperSize", idToSym.size());
        metrics.put("tickerSymbols", tickerSymbols.size());
        metrics.put("unmapped", unmapped.size());
        metrics.put("ghostUsdc", ghost.size());
        metrics.put("noTicker", noTicker.size());
        metrics.put("unmappedList", unmapped);
        metrics.put("ghostUsdcList", ghost);
        metrics.put("noTickerList", noTicker);

        List<String> reasons = new ArrayList<>();
        if (!ghost.isEmpty()) reasons.add(ghost.size() + " ghost *USDCUSDT lot vao pred");
        if (!unmapped.isEmpty()) reasons.add(unmapped.size() + " symId khong co trong mapper");
        if (!noTicker.isEmpty()) reasons.add(noTicker.size() + " symbol khong co ticker that");

        if (!reasons.isEmpty()) {
            return ValidationResult.fail(id(),
                    "Pred tham chieu coin khong ticker that: " + reasons, metrics);
        }
        return ValidationResult.pass(id(),
                predSymIds.size() + " symId pred deu co ticker that, khong ghost USDC.", metrics);
    }

    /** Đọc symId (short, byte 8-9 mỗi record 26B) từ mọi {@code predict_wf_*.bin}. */
    private Set<Short> collectPredSymIds(String predDir) throws Exception {
        File d = new File(predDir);
        File[] files = d.listFiles((dir, name) -> name.startsWith("predict_wf_") && name.endsWith(".bin"));
        if (files == null || files.length == 0) {
            throw new IllegalStateException("A3: khong thay predict_wf_*.bin trong " + predDir);
        }
        Set<Short> ids = new TreeSet<>();
        for (File f : files) {
            byte[] all = Files.readAllBytes(f.toPath());
            if (all.length % FUNDING_REC_BYTES != 0) {
                throw new IllegalStateException("A3: " + f.getName() + " (" + all.length
                        + " byte) khong chia het " + FUNDING_REC_BYTES);
            }
            ByteBuffer buf = ByteBuffer.wrap(all); // big-endian
            int nrec = all.length / FUNDING_REC_BYTES;
            for (int i = 0; i < nrec; i++) {
                buf.getLong();               // ts
                ids.add(buf.getShort());     // symId
                buf.position(buf.position() + 16); // bo 4 float
            }
        }
        return ids;
    }

    /** Nạp {@code symbol_mapper} (global_id_map) qua ctx.client() → id→symbol. */
    private Map<Short, String> loadMapper(AerospikeClient client) {
        Key key = new Key(Configs.AEROSPIKE_NAMESPACE,
                DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_MAPPER,
                DataManagerAerospikeFloatSim.MAPPER_KEY_GLOBAL);
        Record rec = client.get(null, key);
        if (rec == null) {
            throw new IllegalStateException("A3: khong doc duoc symbol_mapper (record null).");
        }
        Map<?, ?> raw = rec.getMap(MAPPER_BIN);
        if (raw == null || raw.isEmpty()) {
            throw new IllegalStateException("A3: symbol_mapper bin '" + MAPPER_BIN + "' rong.");
        }
        Map<Short, String> idToSym = new HashMap<>(raw.size() * 2);
        for (Map.Entry<?, ?> e : raw.entrySet()) {
            String sym = String.valueOf(e.getKey());
            short id = ((Number) e.getValue()).shortValue();
            idToSym.put(id, sym);
        }
        return idToSym;
    }

    /** Quét FULL {@code kline_1m_opt}, gom union symbol trong proto tickersMap (= có ticker thật). */
    private Set<String> collectTickerSymbols(AerospikeClient client) {
        Set<String> symbols = ConcurrentHashMap.newKeySet();
        AtomicLong scanned = new AtomicLong();
        AtomicLong errors = new AtomicLong();
        ScanPolicy sp = new ScanPolicy();
        sp.concurrentNodes = true;
        client.scanAll(sp, Configs.AEROSPIKE_NAMESPACE,
                DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER, (key, rec) -> {
                    scanned.incrementAndGet();
                    try {
                        byte[] compressed = (byte[]) rec.getValue("data");
                        if (compressed == null) return;
                        byte[] raw = Snappy.uncompress(compressed);
                        MinuteDataFinal proto = MinuteDataFinal.parseFrom(raw);
                        symbols.addAll(proto.getTickersMap().keySet());
                    } catch (Exception e) {
                        errors.incrementAndGet();
                    }
                }, "data");
        LOG.info("A3: quet ticker {} record, {} symbol phan biet, {} record loi giai nen.",
                scanned.get(), symbols.size(), errors.get());
        if (symbols.isEmpty()) {
            throw new IllegalStateException("A3: quet ticker khong ra symbol nao (set rong / loi proto).");
        }
        // Chuyen sang TreeSet bat bien-view khong can; giu Set thuong.
        return Collections.unmodifiableSet(symbols);
    }
}
