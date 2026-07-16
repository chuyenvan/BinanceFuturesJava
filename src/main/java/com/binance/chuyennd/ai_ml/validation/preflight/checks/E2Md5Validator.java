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
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * E2 — Chặn "copy pred.bin quên sửa manifest": md5 của MỌI file bin phải khớp {@code manifest.txt}
 * TRƯỚC khi load. Lệch = FAIL (BLOCK) — data drift / snapshot không đồng nhất giữa các node.
 *
 * <p>Nguồn canonical: {@code DATA_VALIDATION_FRAMEWORK.md} §2 (E2 "md5 mismatch — md5 mọi file khớp
 * manifest trước load"). Bài học task 149 (copy từ v5 + sửa md5 manifest → sai lệch âm thầm).</p>
 *
 * <p><b>WRAP</b> logic md5-verify của {@link WfoDataset}: framework kiểm md5 bên trong
 * {@code WfoDataset.load()} qua {@code verifyMd5}/{@code md5} (đều PRIVATE). E2 tái hiện đúng thuật toán
 * đó (MD5 hoa/thường không phân biệt, hex lowercase) nhưng CHỈ tính hash + so sánh, KHÔNG đọc/parse 3 file
 * bin vào RAM (nhẹ, chạy inline). Nhờ vậy gate bắt được drift SỚM hơn — trước cả bước load nặng của WFO.</p>
 *
 * <p>Tính md5 dùng {@link MessageDigest} (thuật toán {@code MD5}), đọc file bằng {@link java.nio java.nio}
 * ({@link Files#newInputStream}). Đọc-only, KHÔNG ghi/sửa file dataset.</p>
 */
public final class E2Md5Validator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(E2Md5Validator.class);

    /** Ánh xạ tên file bin → key md5 trong manifest (khớp {@code WfoDataset.export()}). */
    private static final Map<String, String> FILE_TO_KEY = new LinkedHashMap<>();

    static {
        FILE_TO_KEY.put(WfoDataset.F_MARKET, "md5_market");
        FILE_TO_KEY.put(WfoDataset.F_PRED, "md5_pred");
        FILE_TO_KEY.put(WfoDataset.F_FUNDING, "md5_funding");
    }

    @Override
    public CheckId id() {
        return CheckId.E2;
    }

    /**
     * Tính md5 từng file bin và so với giá trị khai báo trong {@code manifest.txt}.
     *
     * @param ctx ngữ cảnh (cần {@link PreflightContext#wfoDataDir()} != null)
     * @return FAIL nếu bất kỳ md5 nào lệch hoặc manifest thiếu md5 của nguồn đó; PASS kèm md5 đo được
     * @throws IllegalStateException khi lỗi hạ tầng: thiếu {@code wfoDataDir}, thư mục/file bin/manifest
     *                               không tồn tại (gate xử NEEDS_HUMAN)
     * @throws IOException           khi I/O đọc file lỗi
     * @throws NoSuchAlgorithmException khi JVM không có thuật toán MD5 (lỗi môi trường)
     */
    @Override
    public ValidationResult validate(PreflightContext ctx)
            throws IOException, NoSuchAlgorithmException {
        File dir = requireDataDir(ctx);
        File manifestFile = new File(dir, WfoDataset.F_MANIFEST);
        if (!manifestFile.exists()) {
            // Thiếu manifest = precondition hạ tầng cho E2 (verdict "thiếu manifest" là việc của E1).
            throw new IllegalStateException("E2: thiếu manifest.txt để đối chiếu md5: "
                    + manifestFile.getAbsolutePath());
        }
        Map<String, String> mani = readManifest(manifestFile);

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("dataDir", dir.getAbsolutePath());
        List<String> mismatches = new ArrayList<>();
        List<String> missingKeys = new ArrayList<>();

        for (Map.Entry<String, String> e : FILE_TO_KEY.entrySet()) {
            String fileName = e.getKey();
            String key = e.getValue();
            File bin = new File(dir, fileName);
            if (!bin.exists()) {
                throw new IllegalStateException("E2: thiếu file bin " + bin.getAbsolutePath()
                        + " (không thể verify md5).");
            }
            String actual = md5(bin);
            String expected = mani.get(key);
            metrics.put(fileName + ".md5", actual);
            metrics.put(fileName + ".manifest", expected == null ? "MISSING" : expected);
            if (expected == null || expected.trim().isEmpty()) {
                missingKeys.add(key);
            } else if (!actual.equalsIgnoreCase(expected.trim())) {
                mismatches.add(fileName + " (file=" + actual + " manifest=" + expected + ")");
            }
        }

        metrics.put("mismatchCount", mismatches.size());
        metrics.put("missingKeyCount", missingKeys.size());

        if (!missingKeys.isEmpty()) {
            return ValidationResult.fail(id(),
                    "Manifest thiếu md5 cho nguồn: " + missingKeys
                            + " — không đối chiếu được (data provenance khuyết).", metrics);
        }
        if (!mismatches.isEmpty()) {
            LOG.warn("E2: md5 LỆCH → data drift/snapshot không đồng nhất: {}", mismatches);
            return ValidationResult.fail(id(),
                    "md5 LỆCH manifest (nghi copy file quên sửa manifest → data drift L3): " + mismatches,
                    metrics);
        }
        return ValidationResult.pass(id(),
                "md5 " + FILE_TO_KEY.size() + " file bin khớp manifest.", metrics);
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
            throw new IllegalStateException("E2: thiếu wfoDataDir trong PreflightContext (WFO_DATA_DIR).");
        }
        File dir = new File(dataDir);
        if (!dir.exists() || !dir.isDirectory()) {
            throw new IllegalStateException("E2: wfoDataDir không tồn tại/không phải thư mục: "
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

    /**
     * Tính md5 hex (lowercase) của một file — WRAP đúng thuật toán {@code WfoDataset.md5} (private).
     *
     * @param f file cần hash (đã biết tồn tại)
     * @return chuỗi md5 hex 32 ký tự (lowercase)
     * @throws IOException              khi I/O đọc lỗi
     * @throws NoSuchAlgorithmException khi JVM không có MD5
     */
    private static String md5(File f) throws IOException, NoSuchAlgorithmException {
        MessageDigest md = MessageDigest.getInstance("MD5");
        try (InputStream in = Files.newInputStream(f.toPath())) {
            byte[] buf = new byte[1 << 16];
            int r;
            while ((r = in.read(buf)) != -1) {
                md.update(buf, 0, r);
            }
        }
        StringBuilder sb = new StringBuilder();
        for (byte b : md.digest()) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}
