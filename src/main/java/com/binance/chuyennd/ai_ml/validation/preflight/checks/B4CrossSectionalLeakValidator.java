package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.policy.ScanPolicy;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedInputStream;
import java.io.DataInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * B4 — Chặn CROSS-SECTIONAL / POPULATION LEAK: mọi đại lượng cắt-ngang (population/basket, z-score,
 * merge OI) chỉ được tính từ dữ liệu {@code <= t}; và KHÔNG được có coin niêm yết TƯƠNG LAI trong
 * cross-section tại thời điểm {@code t}. Nguồn lệch ngầm CORE nêu (basket warmup, z-score toàn kỳ,
 * OI merge tương lai), spec §4b bổ sung B4 (BLOCK).
 *
 * <p><b>Phần ĐO ĐƯỢC ở preflight (đã cài):</b> "không coin niêm yết tương lai trong cross-section".
 * Với mỗi mốc {@code ts} lấy mẫu trong {@code predict_wf_*.bin}, mọi symId có mặt phải đã NIÊM YẾT
 * ({@code first <= ts}) theo {@code symbol_lifecycle} (đọc qua {@link PreflightContext#client()}).
 * Coin có {@code first > ts} mà vẫn xuất hiện = leak niêm-yết-tương-lai (backtest thấy coin trước khi
 * nó tồn tại). Lấy mẫu phân tầng: ưu tiên {@code sampleSizePerCell} mốc ts ĐẦU mỗi fold (vùng ±embargo,
 * dễ leak nhất) + lấy thưa theo bước cho phần còn lại.</p>
 *
 * <p><b>Phần CHƯA đo được từ pred bin (TODO-verify):</b>
 * <ul>
 *   <li>z-score/basket warmup toàn-kỳ: cần soi CODE/dataset sinh feature (population statistics phải
 *       dùng cửa sổ {@code <= t}, không dùng mean/std toàn bộ lịch sử). Không lộ trong file pred.</li>
 *   <li>OI merge tương lai: {@code gen_funding_wf_predictions.py} dùng {@code merge_asof(direction="backward")}
 *       — leak-free theo thiết kế; TODO xác nhận không có nhánh forward-fill nào khác.</li>
 * </ul>
 * KHÔNG tự tuyên PASS cho hai phần này — chỉ báo trạng thái + TODO.</p>
 *
 * <p><b>TODO (mapping):</b> symId→symbol hiện lấy qua {@link SimpleSymbolMapper} (chuẩn dùng khắp
 * codebase, vd {@code ValidateFundingOOS}), nhưng mapper tự nạp qua {@code DataManagerAerospikeFloatSim}
 * chứ KHÔNG qua {@link PreflightContext#client()}. Khi chốt schema set {@code symbol_mapper}, nên đọc
 * mapping qua {@code ctx.client()} để đồng nhất nguồn.</p>
 */
public final class B4CrossSectionalLeakValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(B4CrossSectionalLeakValidator.class);

    private static final String SET_LIFECYCLE = "symbol_lifecycle";

    /** Kích thước record predict_wf (big-endian long ts + short symId + 4 float). */
    private static final int REC = 26;

    /** Lấy thưa: ngoài vùng biên, lấy mẫu 1 mốc ts mỗi {@value} mốc (đủ phủ, không quét mù toàn bộ). */
    private static final int SAMPLE_STRIDE = 50;

    @Override
    public CheckId id() {
        return CheckId.B4;
    }

    @Override
    public boolean expensive() {
        return true;
    }

    /**
     * Kiểm không có coin niêm yết tương lai trong cross-section của các mốc ts lấy mẫu.
     *
     * @param ctx ngữ cảnh (cần {@link PreflightContext#client()} và {@link PreflightContext#fundingPredDir()})
     * @return FAIL (BLOCK) nếu phát hiện symId có {@code first > ts} trong cross-section; PASS kèm metrics
     * @throws IllegalStateException thiếu client / thiếu pred dir / thiếu file (hạ tầng → NEEDS_HUMAN)
     * @throws IOException lỗi đọc file (hạ tầng → NEEDS_HUMAN)
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) throws IOException {
        AerospikeClient client = ctx.client();
        if (client == null) {
            throw new IllegalStateException("B4: thiếu Aerospike client (cần symbol_lifecycle).");
        }
        String predDir = ctx.fundingPredDir();
        if (predDir == null || predDir.trim().isEmpty()) {
            throw new IllegalStateException("B4: thiếu WFO_FUNDING_PRED_DIR (fundingPredDir).");
        }
        File dir = new File(predDir);
        File[] files = dir.listFiles((d, name) -> name.startsWith("predict_wf_") && name.endsWith(".bin"));
        if (files == null || files.length == 0) {
            throw new IllegalStateException("B4: không thấy predict_wf_*.bin trong " + predDir);
        }
        java.util.Arrays.sort(files);

        // 1) Nạp symbol_lifecycle: symbol -> first(listing ms). CHỈ ĐỌC (giống A5).
        Map<String, Long> firstBySymbol = new ConcurrentHashMap<>();
        ScanPolicy sp = new ScanPolicy();
        sp.concurrentNodes = true;
        client.scanAll(sp, Configs.AEROSPIKE_NAMESPACE, SET_LIFECYCLE, (key, rec) -> {
            String sym = rec.getString("sym");
            long first = rec.getLong("first");
            if (sym != null && first > 0) {
                firstBySymbol.put(sym, first);
            }
        }, "sym", "first");
        if (firstBySymbol.isEmpty()) {
            throw new IllegalStateException("B4: symbol_lifecycle rỗng — không thể kiểm niêm-yết-tương-lai.");
        }

        SimpleSymbolMapper mapper = SimpleSymbolMapper.getInstance();
        int boundaryTs = Math.max(1, ctx.sampleSizePerCell()); // số mốc ts đầu mỗi fold (vùng ±embargo)

        long tsSampled = 0;
        long crossChecks = 0;
        long unknownSymbol = 0;   // mapper không map được symId
        long unknownLifecycle = 0; // symbol không có trong lifecycle
        List<String> futureListed = new ArrayList<>();

        for (File f : files) {
            long len = f.length();
            if (len % REC != 0) {
                throw new IOException("B4: " + f.getName() + " kích thước " + len + " không chia hết " + REC);
            }
            try (DataInputStream in = new DataInputStream(new BufferedInputStream(new FileInputStream(f), 1 << 20))) {
                long nrec = len / REC;
                long curTs = Long.MIN_VALUE;
                int groupIdx = -1;
                boolean sampleThisTs = false;
                for (long i = 0; i < nrec; i++) {
                    long ts = in.readLong();
                    short symId = in.readShort();
                    in.skipBytes(16); // 4 float
                    if (ts != curTs) {
                        curTs = ts;
                        groupIdx++;
                        // Mẫu vùng biên (đầu fold) + lấy thưa phần còn lại.
                        sampleThisTs = groupIdx < boundaryTs || (groupIdx % SAMPLE_STRIDE == 0);
                        if (sampleThisTs) {
                            tsSampled++;
                        }
                    }
                    if (!sampleThisTs) {
                        continue;
                    }
                    crossChecks++;
                    String sym = mapper.getSymbol(symId);
                    if (sym == null || sym.startsWith("UNKNOWN-")) {
                        unknownSymbol++;
                        continue;
                    }
                    Long first = firstBySymbol.get(sym);
                    if (first == null) {
                        unknownLifecycle++;
                        continue;
                    }
                    if (first > ts) {
                        if (futureListed.size() < 50) {
                            futureListed.add(sym + "@ts=" + ts + "(first=" + first + ")");
                        }
                    }
                }
            }
        }

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("folds", files.length);
        metrics.put("lifecycleSymbols", firstBySymbol.size());
        metrics.put("sampleSizePerCell", ctx.sampleSizePerCell());
        metrics.put("sampleStride", SAMPLE_STRIDE);
        metrics.put("tsSampled", tsSampled);
        metrics.put("crossSectionChecks", crossChecks);
        metrics.put("unknownSymbol", unknownSymbol);
        metrics.put("unknownLifecycle", unknownLifecycle);
        metrics.put("futureListedFound", futureListed.size());
        metrics.put("todo_zscoreBasket", "cần soi code sinh feature (population <= t)");
        metrics.put("todo_oiMerge", "xác nhận merge_asof backward-only (không forward-fill)");

        if (!futureListed.isEmpty()) {
            return ValidationResult.fail(id(),
                    "LEAK B4: coin niêm yết TƯƠNG LAI (first > ts) xuất hiện trong cross-section: "
                            + futureListed, metrics);
        }
        LOG.info("B4 OK: {} mốc ts mẫu, {} lượt cross-check, 0 coin niêm-yết-tương-lai (unknownSym={}, unknownLC={}).",
                tsSampled, crossChecks, unknownSymbol, unknownLifecycle);
        return ValidationResult.pass(id(),
                "Không thấy coin niêm-yết-tương-lai trong " + tsSampled + " mốc ts mẫu ("
                        + crossChecks + " cross-check). TODO: z-score/basket warmup + OI merge (xem Javadoc).",
                metrics);
    }
}
