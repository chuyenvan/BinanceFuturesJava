package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
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
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * E1 — Chặn "model/dataset MẤT PROVENANCE": mỗi nguồn (market/pred/funding trong
 * {@link PreflightContext#wfoDataDir()}) phải có {@code manifest.txt} ghi đủ
 * <b>commit + data hash + cutoffs</b>; thiếu manifest (hoặc thiếu field bắt buộc) = FAIL (BLOCK).
 *
 * <p>Nguồn canonical: {@code DATA_VALIDATION_FRAMEWORK.md} §2 (E1 "Model không khớp code/data —
 * Manifest ghi commit + data hash + cutoffs") và §1.5 provenance ("Không có provenance = không dùng").
 * Bài học task 154 (ONNX 262MB mất source → dead end).</p>
 *
 * <p><b>WRAP</b> format manifest của {@link WfoDataset} (hàm {@code export()} sinh; {@code load()} đọc):
 * đây là tầng RẺ (chỉ đọc {@code manifest.txt}, KHÔNG load 3 file bin, KHÔNG verify md5 — md5 là E2,
 * cutoff/range là E3). E1 chỉ khẳng định provenance ĐƯỢC KHAI BÁO ĐỦ trước khi các check khác dựa vào nó.</p>
 *
 * <p>Field bắt buộc (bám {@code WfoDataset.export()} manifest):
 * <ul>
 *   <li>commit: {@code codeGitSha} — phải có và != {@code "unknown"} (mất source = fail).</li>
 *   <li>data hash: {@code md5_market}, {@code md5_pred}, {@code md5_funding} — mỗi nguồn một hash.</li>
 *   <li>cutoffs/range: {@code marketRange} — khai báo range dữ liệu.</li>
 * </ul>
 * TODO(verify): {@code WfoDataset.export()} hiện CHỈ ghi {@code marketRange} (range của market), chưa ghi
 * range/cutoff riêng cho pred và funding, và chưa ghi field <i>train cutoff</i> (thuộc E3). Khi export bổ
 * sung {@code predRange}/{@code fundingRange}/{@code trainCutoff}, thêm vào danh sách bắt buộc dưới đây —
 * KHÔNG bịa field chưa tồn tại.</p>
 */
public final class E1ManifestValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(E1ManifestValidator.class);

    /** Commit sinh dataset (mất = provenance đứt). {@code export()} ghi từ env {@code WFO_CODE_SHA}. */
    private static final String K_COMMIT = "codeGitSha";
    /** Giá trị "chưa khai báo" mà {@code export()} điền khi env commit rỗng → coi như THIẾU. */
    private static final String COMMIT_UNKNOWN = "unknown";
    /** Data hash per nguồn — mỗi file bin một md5. */
    private static final List<String> K_DATA_HASH =
            Arrays.asList("md5_market", "md5_pred", "md5_funding");
    /** Cutoff/range khai báo (hiện chỉ có của market — xem TODO ở Javadoc class). */
    private static final String K_RANGE = "marketRange";

    @Override
    public CheckId id() {
        return CheckId.E1;
    }

    /**
     * Kiểm {@code manifest.txt} tồn tại và khai báo đủ commit + data hash (3 nguồn) + range.
     *
     * @param ctx ngữ cảnh (cần {@link PreflightContext#wfoDataDir()} != null, trỏ thư mục dataset)
     * @return FAIL nếu thiếu {@code manifest.txt} hoặc thiếu field provenance bắt buộc; PASS kèm metrics
     * @throws IllegalStateException khi lỗi hạ tầng: thiếu {@code wfoDataDir} hoặc thư mục không tồn tại
     *                               (gate xử NEEDS_HUMAN, KHÔNG suy diễn PASS)
     * @throws IOException           khi không đọc được {@code manifest.txt} dù file tồn tại (I/O hạ tầng)
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) throws IOException {
        File dir = requireDataDir(ctx);
        File manifest = new File(dir, WfoDataset.F_MANIFEST);

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("dataDir", dir.getAbsolutePath());
        metrics.put("manifestPath", manifest.getAbsolutePath());

        if (!manifest.exists()) {
            metrics.put("manifestExists", false);
            LOG.warn("E1: thiếu manifest {} → provenance đứt (BLOCK).", manifest.getAbsolutePath());
            return ValidationResult.fail(id(),
                    "Thiếu manifest.txt tại " + manifest.getAbsolutePath()
                            + " — không có provenance = KHÔNG dùng (§1.5).", metrics);
        }
        metrics.put("manifestExists", true);

        Map<String, String> mani = readManifest(manifest);
        List<String> missing = new ArrayList<>();

        String commit = mani.get(K_COMMIT);
        boolean commitOk = commit != null && !commit.trim().isEmpty()
                && !COMMIT_UNKNOWN.equalsIgnoreCase(commit.trim());
        metrics.put(K_COMMIT, commit == null ? "MISSING" : commit);
        if (!commitOk) {
            missing.add(K_COMMIT + (commit == null ? "(missing)" : "(=" + commit + ")"));
        }

        for (String key : K_DATA_HASH) {
            String v = mani.get(key);
            boolean present = v != null && !v.trim().isEmpty();
            metrics.put(key, present ? "set" : "MISSING");
            if (!present) {
                missing.add(key);
            }
        }

        String range = mani.get(K_RANGE);
        boolean rangeOk = range != null && !range.trim().isEmpty();
        metrics.put(K_RANGE, rangeOk ? range : "MISSING");
        if (!rangeOk) {
            missing.add(K_RANGE);
        }

        metrics.put("missingCount", missing.size());
        if (!missing.isEmpty()) {
            return ValidationResult.fail(id(),
                    "Manifest thiếu field provenance bắt buộc (commit + data hash + range): " + missing,
                    metrics);
        }
        return ValidationResult.pass(id(),
                "Manifest đủ provenance: commit=" + commit + ", md5 3 nguồn, range khai báo.", metrics);
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
            throw new IllegalStateException("E1: thiếu wfoDataDir trong PreflightContext (WFO_DATA_DIR).");
        }
        File dir = new File(dataDir);
        if (!dir.exists() || !dir.isDirectory()) {
            throw new IllegalStateException("E1: wfoDataDir không tồn tại/không phải thư mục: "
                    + dir.getAbsolutePath());
        }
        return dir;
    }

    /**
     * Đọc {@code manifest.txt} thành map key=value (tách theo dấu '=' đầu tiên).
     *
     * <p>WRAP đúng logic {@code WfoDataset.readManifest} (private trong framework) để khớp cách parse
     * khi {@code load()} verify — dùng {@link java.nio java.nio}.</p>
     *
     * @param f file manifest (đã biết tồn tại)
     * @return map field manifest
     * @throws IOException khi I/O đọc file lỗi
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
