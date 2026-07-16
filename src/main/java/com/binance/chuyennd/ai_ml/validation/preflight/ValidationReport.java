package com.binance.chuyennd.ai_ml.validation.preflight;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

/**
 * Tổng hợp kết quả 19 check thành báo cáo PASS/FAIL — theo §3 bước 4-5.
 *
 * <p>Verdict gate: FAIL nếu CÓ BẤT KỲ kết quả {@link ValidationResult#isBlockingFailure()};
 * WARN được ghi report nhưng KHÔNG chặn. Render bảng markdown + số đo để người/script đối chiếu.
 * KHÔNG ghi ra ổ C (CORE): đường dẫn report do caller truyền, mặc định {@code docs/reports/}.</p>
 */
public final class ValidationReport {

    private static final Logger LOG = LoggerFactory.getLogger(ValidationReport.class);

    private final List<ValidationResult> results = new ArrayList<>();
    private final List<CheckId> infraErrors = new ArrayList<>();

    /** @param r thêm 1 kết quả check. */
    public void add(ValidationResult r) {
        results.add(r);
    }

    /**
     * Ghi nhận check lỗi hạ tầng (ném exception) → gate coi là chưa kiểm được → chặn (NEEDS_HUMAN).
     *
     * @param id check bị lỗi hạ tầng
     */
    public void addInfraError(CheckId id) {
        infraErrors.add(id);
    }

    /** @return true nếu gate PASS (không BLOCK-fail và không lỗi hạ tầng). */
    public boolean isPass() {
        if (!infraErrors.isEmpty()) {
            return false;
        }
        for (ValidationResult r : results) {
            if (r.isBlockingFailure()) {
                return false;
            }
        }
        return true;
    }

    /** @return số BLOCK-fail. */
    public long blockingFailures() {
        return results.stream().filter(ValidationResult::isBlockingFailure).count();
    }

    /** @return số WARN (fail mức WARN). */
    public long warnings() {
        return results.stream().filter(r -> !r.passed() && r.severity() == Severity.WARN).count();
    }

    /**
     * Render báo cáo markdown.
     *
     * @return nội dung markdown (bảng từng check + verdict)
     */
    public String renderMarkdown() {
        SimpleDateFormat fmt = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        StringBuilder sb = new StringBuilder();
        sb.append("# DATA PREFLIGHT REPORT — ").append(fmt.format(new Date())).append("\n\n");
        sb.append("VERDICT: ").append(isPass() ? "PASS ✅" : "FAIL ⛔").append("\n\n");
        sb.append("BLOCK-fail: ").append(blockingFailures())
          .append(" · WARN: ").append(warnings())
          .append(" · infra-error: ").append(infraErrors.size()).append("\n\n");
        sb.append("| Check | Nhóm | Kết quả | Mức | Số đo / Lý do |\n");
        sb.append("|---|---|---|---|---|\n");
        for (ValidationResult r : results) {
            sb.append("| ").append(r.checkId())
              .append(" | ").append(r.checkId().group())
              .append(" | ").append(r.passed() ? "PASS" : "FAIL")
              .append(" | ").append(r.severity())
              .append(" | ").append(r.message().replace("|", "\\|"))
              .append(" ").append(r.metrics())
              .append(" |\n");
        }
        if (!infraErrors.isEmpty()) {
            sb.append("\n**Lỗi hạ tầng (chưa kiểm được → NEEDS_HUMAN):** ").append(infraErrors).append("\n");
        }
        return sb.toString();
    }

    /**
     * Ghi report ra file (không ghi ổ C).
     *
     * @param outPath đường dẫn file markdown
     */
    public void writeTo(String outPath) {
        try {
            Path p = Paths.get(outPath);
            if (p.getParent() != null) {
                Files.createDirectories(p.getParent());
            }
            Files.write(p, renderMarkdown().getBytes(StandardCharsets.UTF_8));
            LOG.info("📄 Preflight report ghi tại: {}", outPath);
        } catch (IOException e) {
            LOG.error("Không ghi được preflight report tại {}", outPath, e);
        }
    }
}
