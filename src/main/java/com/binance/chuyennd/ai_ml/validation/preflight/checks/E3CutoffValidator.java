package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.ExpectedRanges;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoDataset;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * E3 — Chặn "cutoff config im lặng": {@code manifest.txt} phải KHAI BÁO train range/cutoff và range đó
 * phải khớp mong đợi pre-register ({@link PreflightContext#expected()}). Không khai báo, hoặc lệch mong
 * đợi = FAIL (BLOCK).
 *
 * <p>Nguồn canonical: {@code DATA_VALIDATION_FRAMEWORK.md} §2 (E3 "Cutoff config im lặng — gate train
 * cutoff 2023 không khai báo → Manifest ghi train range; validate khớp mong đợi"). Nguyên tắc §1.4:
 * mỗi nguồn khai báo TRƯỚC range, validate so khai báo — chống "so với trí nhớ".</p>
 *
 * <p><b>WRAP</b> manifest của {@link WfoDataset}: dùng cùng cách parse key=value. Range đối chiếu lấy từ
 * field {@code marketRange} (do {@code WfoDataset.export()} ghi dạng {@code firstKeyMs..lastKeyMs}).</p>
 *
 * <p><b>TODO(verify) — manifest hiện CHƯA có field train-cutoff riêng:</b> {@code WfoDataset.export()}
 * chỉ ghi {@code marketRange} (range DỮ LIỆU của market), KHÔNG ghi cutoff huấn luyện (vd gate train
 * cutoff 2023) cũng như range riêng của pred/funding. Validator này dùng {@code marketRange} làm proxy
 * tốt nhất hiện có và ĐÁNH DẤU thiếu field cutoff chuyên biệt (metric {@code dedicatedTrainCutoffField});
 * KHÔNG bịa field. Khi export bổ sung {@code trainCutoff}/{@code trainRange}, đổi {@link #K_RANGE} và
 * thêm đối chiếu cutoff huấn luyện thật.</p>
 */
public final class E3CutoffValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(E3CutoffValidator.class);

    /** Field range dùng đối chiếu (proxy hiện có — xem TODO Javadoc class). */
    private static final String K_RANGE = "marketRange";
    /** Tên nguồn tra {@link ExpectedRanges} tương ứng {@link #K_RANGE}. */
    private static final String EXPECTED_SOURCE = "market";
    /** Dấu ngăn cách range trong manifest ({@code firstKeyMs..lastKeyMs}). */
    private static final String RANGE_SEP = "\\.\\.";

    @Override
    public CheckId id() {
        return CheckId.E3;
    }

    /**
     * Kiểm manifest có khai báo range và range khớp mong đợi pre-register.
     *
     * @param ctx ngữ cảnh (cần {@link PreflightContext#wfoDataDir()} và {@link PreflightContext#expected()})
     * @return FAIL nếu manifest không khai báo range (cutoff im lặng) hoặc range lệch mong đợi; PASS kèm số
     * @throws IllegalStateException khi lỗi hạ tầng: thiếu {@code wfoDataDir}/thư mục/manifest, HOẶC chưa
     *                               pre-register range cho nguồn {@code market} (không "so với trí nhớ" →
     *                               NEEDS_HUMAN)
     * @throws IOException           khi I/O đọc manifest lỗi
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) throws IOException {
        File dir = requireDataDir(ctx);
        File manifestFile = new File(dir, WfoDataset.F_MANIFEST);
        if (!manifestFile.exists()) {
            throw new IllegalStateException("E3: thiếu manifest.txt để đọc train range: "
                    + manifestFile.getAbsolutePath());
        }
        Map<String, String> mani = readManifest(manifestFile);

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("dataDir", dir.getAbsolutePath());
        metrics.put("rangeKey", K_RANGE);
        // Đánh dấu thiếu field cutoff huấn luyện chuyên biệt (xem TODO): hiện chỉ có range dữ liệu.
        metrics.put("dedicatedTrainCutoffField", "MISSING(TODO: export chưa ghi trainCutoff)");

        String rawRange = mani.get(K_RANGE);
        metrics.put(K_RANGE, rawRange == null ? "MISSING" : rawRange);
        if (rawRange == null || rawRange.trim().isEmpty()) {
            LOG.warn("E3: manifest không khai báo {} → cutoff im lặng (BLOCK).", K_RANGE);
            return ValidationResult.fail(id(),
                    "Manifest không khai báo train range/cutoff (field " + K_RANGE
                            + ") — cutoff config im lặng, cấm chạy.", metrics);
        }

        ExpectedRanges.SourceRange expected = ctx.expected().source(EXPECTED_SOURCE);
        if (expected == null) {
            // Chưa pre-register (ExpectedRanges skeleton, WS1 chưa nạp validate_criteria) → không so trí nhớ.
            throw new IllegalStateException("E3: chưa pre-register range cho nguồn '" + EXPECTED_SOURCE
                    + "' trong ExpectedRanges (WS1 nạp validate_criteria) — không so với trí nhớ.");
        }

        String[] parts = rawRange.trim().split(RANGE_SEP);
        if (parts.length != 2) {
            return ValidationResult.fail(id(),
                    "Range manifest sai định dạng (mong 'startMs..endMs'): " + rawRange, metrics);
        }
        long declStart;
        long declEnd;
        try {
            declStart = Long.parseLong(parts[0].trim());
            declEnd = Long.parseLong(parts[1].trim());
        } catch (NumberFormatException ex) {
            return ValidationResult.fail(id(),
                    "Range manifest không parse được số: " + rawRange, metrics);
        }

        metrics.put("declaredStartMs", declStart);
        metrics.put("declaredEndMs", declEnd);
        metrics.put("expectedStartMs", expected.expectedStartMs);
        metrics.put("expectedEndMs", expected.expectedEndMs);
        long startDelta = declStart - expected.expectedStartMs;
        long endDelta = declEnd - expected.expectedEndMs;
        metrics.put("startDeltaMs", startDelta);
        metrics.put("endDeltaMs", endDelta);

        if (startDelta != 0 || endDelta != 0) {
            return ValidationResult.fail(id(),
                    "Train range khai báo lệch mong đợi (§1.4): declared=[" + declStart + ".." + declEnd
                            + "] expected=[" + expected.expectedStartMs + ".." + expected.expectedEndMs
                            + "] startDelta=" + startDelta + "ms endDelta=" + endDelta + "ms.", metrics);
        }
        return ValidationResult.pass(id(),
                "Train range khai báo khớp mong đợi [" + declStart + ".." + declEnd + "].", metrics);
    }

    /**
     * Lấy thư mục dataset, ném khi thiếu (lỗi hạ tầng → NEEDS_HUMAN).
     *
     * @param ctx ngữ cảnh
     * @return thư mục dataset đã xác thực tồn tại
     */
    private static File requireDataDir(PreflightContext ctx) {
        String dataDir = ctx.wfoDataDir();
        if (dataDir == null || dataDir.trim().isEmpty()) {
            throw new IllegalStateException("E3: thiếu wfoDataDir trong PreflightContext (WFO_DATA_DIR).");
        }
        File dir = new File(dataDir);
        if (!dir.exists() || !dir.isDirectory()) {
            throw new IllegalStateException("E3: wfoDataDir không tồn tại/không phải thư mục: "
                    + dir.getAbsolutePath());
        }
        return dir;
    }

    /**
     * Đọc {@code manifest.txt} thành map key=value — WRAP cách parse của {@code WfoDataset.readManifest}.
     *
     * @param f file manifest (đã biết tồn tại)
     * @return map field manifest
     * @throws IOException khi I/O đọc lỗi
     */
    private static Map<String, String> readManifest(File f) throws IOException {
        Map<String, String> m = new LinkedHashMap<>();
        try (BufferedReader r = new BufferedReader(
                new InputStreamReader(Files.newInputStream(f.toPath()), StandardCharsets.UTF_8))) {
            String line;
            while ((line = r.readLine()) != null) {
                int eq = line.indexOf('=');
                if (eq > 0) {
                    m.put(line.substring(0, eq).trim(), line.substring(eq + 1).trim());
                }
            }
        }
        return m;
    }
}
