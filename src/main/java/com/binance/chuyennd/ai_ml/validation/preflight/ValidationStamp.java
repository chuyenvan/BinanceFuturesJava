package com.binance.chuyennd.ai_ml.validation.preflight;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Properties;

/**
 * Con dấu chứng nhận một DATASET đã qua validate tầng SLOW — để WFO/HPO biết có cần re-validate không.
 *
 * <p>Uni chốt 2026-07-11: KHÔNG chạy check đắt mỗi lần WFO. Thay vào đó SLOW chạy NGOÀI theo trigger,
 * PASS thì ghi stamp. WFO khởi động chỉ kiểm: stamp có khớp {@code datasetFingerprint} (md5 manifest)
 * + {@code env} hiện tại không. Khớp → dataset đã sạch, khỏi chạy lại đắt. Không khớp (data đổi / đổi
 * môi trường Oracle→Kaggle / chưa từng validate) → BẮT chạy full trước.</p>
 *
 * <p>Lưu dạng {@link Properties} (text key=value) — không kéo thêm dependency JSON.</p>
 */
public final class ValidationStamp {

    private static final Logger LOG = LoggerFactory.getLogger(ValidationStamp.class);

    private final String datasetFingerprint;
    private final String env;
    private final boolean pass;
    private final long validatedAtMs;
    private final String gateVersion;

    public ValidationStamp(String datasetFingerprint, String env, boolean pass,
                           long validatedAtMs, String gateVersion) {
        this.datasetFingerprint = datasetFingerprint;
        this.env = env;
        this.pass = pass;
        this.validatedAtMs = validatedAtMs;
        this.gateVersion = gateVersion;
    }

    /** @return md5/fingerprint của dataset (khớp manifest.txt WFO). */
    public String datasetFingerprint() {
        return datasetFingerprint;
    }

    /** @return môi trường đã validate (vd "oracle", "kaggle"). */
    public String env() {
        return env;
    }

    /** @return true nếu lần validate SLOW đó PASS. */
    public boolean pass() {
        return pass;
    }

    /** @return phiên bản gate đã tạo stamp (so với PreflightGate.GATE_VERSION để hết hạn stamp cũ). */
    public String gateVersion() {
        return gateVersion;
    }

    /**
     * Stamp có còn hợp lệ cho lần chạy hiện tại không.
     *
     * @param fingerprint md5 dataset hiện tại
     * @param currentEnv  môi trường hiện tại
     * @return true nếu PASS và khớp cả fingerprint lẫn env
     */
    public boolean isValidFor(String fingerprint, String currentEnv) {
        return pass
                && datasetFingerprint != null && datasetFingerprint.equals(fingerprint)
                && env != null && env.equals(currentEnv);
    }

    /**
     * Ghi stamp ra file.
     *
     * @param path đường dẫn stamp (vd cạnh dataset: wfo_dataset/validation_stamp.properties)
     */
    public void writeTo(String path) {
        Properties p = new Properties();
        p.setProperty("datasetFingerprint", nvl(datasetFingerprint));
        p.setProperty("env", nvl(env));
        p.setProperty("pass", String.valueOf(pass));
        p.setProperty("validatedAtMs", String.valueOf(validatedAtMs));
        p.setProperty("gateVersion", nvl(gateVersion));
        try {
            Path fp = Paths.get(path);
            if (fp.getParent() != null) {
                Files.createDirectories(fp.getParent());
            }
            try (OutputStream os = Files.newOutputStream(fp)) {
                p.store(os, "PreflightGate validation stamp");
            }
            LOG.info("🔖 Ghi validation stamp: {} (fingerprint={}, env={}, pass={})",
                    path, datasetFingerprint, env, pass);
        } catch (IOException e) {
            LOG.error("Không ghi được validation stamp tại {}", path, e);
        }
    }

    /**
     * Đọc stamp từ file.
     *
     * @param path đường dẫn stamp
     * @return stamp, hoặc null nếu không có/không đọc được (coi như chưa validate)
     */
    public static ValidationStamp readFrom(String path) {
        Path fp = Paths.get(path);
        if (!Files.exists(fp)) {
            return null;
        }
        Properties p = new Properties();
        try (InputStream is = Files.newInputStream(fp)) {
            p.load(is);
            return new ValidationStamp(
                    p.getProperty("datasetFingerprint"),
                    p.getProperty("env"),
                    Boolean.parseBoolean(p.getProperty("pass", "false")),
                    Long.parseLong(p.getProperty("validatedAtMs", "0")),
                    p.getProperty("gateVersion"));
        } catch (IOException | NumberFormatException e) {
            LOG.warn("Stamp tại {} lỗi đọc — coi như chưa validate", path, e);
            return null;
        }
    }

    private static String nvl(String s) {
        return s == null ? "" : s;
    }
}
