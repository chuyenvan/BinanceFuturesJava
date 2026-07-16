package com.binance.chuyennd.ai_ml.wfo.framework;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

/**
 * WFO FRAMEWORK — COORDINATOR (chạy trên Local/điều phối). 3 lệnh "không cần nghĩ":
 * <ul>
 *   <li>{@code init <type>}  — sinh job từ task.buildJobs() → nạp PENDING vào Aerospike (CREATE_ONLY,
 *       idempotent: chạy lại không đè job đang chạy/đã xong).</li>
 *   <li>{@code status <type>} — in bảng đếm theo state + danh sách job chưa xong.</li>
 *   <li>{@code report <type>} — nếu tất cả DONE → task.aggregate() → ghi docs/reports/wfo_<type>.md +
 *       in VERDICT. Nếu chưa xong hết → cảnh báo còn bao nhiêu.</li>
 *   <li>{@code reset <type>}  — (thận trọng) xóa & nạp lại toàn bộ job PENDING.</li>
 * </ul>
 *
 * Arg: <cmd> [type=strategy_window]
 */
public class WfoCoordinator {

    private static final Logger LOG = LoggerFactory.getLogger(WfoCoordinator.class);
    static final String REPORT_DIR = "docs/reports";

    public static void main(String[] args) {
        try {
            if (args.length < 1) {
                LOG.info("Usage: WfoCoordinator <init|status|report|reset> [type]");
                System.exit(2);
            }
            String cmd = args[0];
            String type = args.length > 1 ? args[1] : "strategy_window";
            new WfoCoordinator().dispatch(cmd, type);
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("WfoCoordinator FAIL", e);
            System.exit(1);
        }
    }

    void dispatch(String cmd, String type) throws Exception {
        WfoTask task = WfoTaskRegistry.get(type);
        WfoJobStore store = new WfoJobStore();
        switch (cmd) {
            case "init":   init(task, store); break;
            case "status": status(task, store); break;
            case "report": report(task, store); break;
            case "reset":  reset(task, store); break;
            default: LOG.error("Lenh khong biet: {}", cmd);
        }
    }

    private void init(WfoTask task, WfoJobStore store) {
        List<WfoJob> jobs = task.buildJobs();
        for (WfoJob j : jobs) store.putNew(j);  // CREATE_ONLY: không đè job đang chạy
        LOG.info("INIT {} : nap {} job (CREATE_ONLY). Dung 'status' de xem.", task.type(), jobs.size());
        status(task, store);
    }

    private void reset(WfoTask task, WfoJobStore store) {
        List<WfoJob> jobs = task.buildJobs();
        java.util.Set<String> newIds = new java.util.LinkedHashSet<>();
        for (WfoJob j : jobs) { store.putForce(j); newIds.add(j.id); }  // ghi đè PENDING
        // BUG 2 (2026-07-13): purge orphan — job cùng type KHÔNG thuộc set buildJobs hiện tại
        // (vd cấu hình 19-window cũ để lại w17/w18) → xóa hẳn khỏi record + index, tránh report
        // tính sai mẫu số / lẫn kết quả cũ. Chỉ đụng job đúng type; type khác giữ nguyên.
        int orphan = 0;
        for (WfoJob existing : filterType(store, task.type())) {
            if (!newIds.contains(existing.id)) { store.deleteJob(existing.id); orphan++; }
        }
        LOG.warn("RESET {} : ghi de {} job ve PENDING, xoa {} orphan (job cu ngoai set).",
                task.type(), jobs.size(), orphan);
        status(task, store);
    }

    private void status(WfoTask task, WfoJobStore store) {
        List<WfoJob> all = filterType(store, task.type());
        Map<WfoJob.State, Integer> cnt = new EnumMap<>(WfoJob.State.class);
        for (WfoJob.State s : WfoJob.State.values()) cnt.put(s, 0);
        long now = System.currentTimeMillis();
        for (WfoJob j : all) cnt.merge(j.state, 1, Integer::sum);
        LOG.info("STATUS {} : total={} | PENDING={} RUNNING={} DONE={} FAILED={}",
                task.type(), all.size(), cnt.get(WfoJob.State.PENDING), cnt.get(WfoJob.State.RUNNING),
                cnt.get(WfoJob.State.DONE), cnt.get(WfoJob.State.FAILED));
        for (WfoJob j : all) {
            if (j.state == WfoJob.State.DONE) continue;
            String extra = "";
            if (j.state == WfoJob.State.RUNNING)
                extra = " owner=" + j.owner + " lease_in=" + ((j.leaseUntil - now) / 1000) + "s"
                        + (j.leaseExpired(now) ? " [STALE]" : "");
            if (j.state == WfoJob.State.FAILED) extra = " err=" + j.lastError;
            LOG.info("  {} {}{}", j.id, j.state, extra);
        }
    }

    private void report(WfoTask task, WfoJobStore store) throws Exception {
        List<WfoJob> all = filterType(store, task.type());
        long done = all.stream().filter(j -> j.state == WfoJob.State.DONE).count();
        long failed = all.stream().filter(j -> j.state == WfoJob.State.FAILED).count();
        if (all.isEmpty()) { LOG.warn("Chua co job nao. Chay 'init' truoc."); return; }
        if (done < all.size()) {
            LOG.warn("CHUA xong het: DONE {}/{} (FAILED {}). Van xuat report tu cac job DONE (partial).",
                    done, all.size(), failed);
        }
        List<WfoJob> doneJobs = new java.util.ArrayList<>();
        for (WfoJob j : all) if (j.state == WfoJob.State.DONE) doneJobs.add(j);
        String md = task.aggregate(doneJobs);

        File dir = new File(REPORT_DIR);
        if (!dir.exists()) dir.mkdirs();
        File out = new File(dir, "wfo_" + task.type() + ".md");
        try (Writer w = new java.io.OutputStreamWriter(new java.io.FileOutputStream(out), StandardCharsets.UTF_8)) {
            w.write(md);
        }
        LOG.info("REPORT ghi -> {}", out.getPath());
        // in VERDICT (dòng đầu chứa "VERDICT")
        for (String line : md.split("\n")) if (line.contains("VERDICT")) { LOG.info("{}", line.trim()); break; }
    }

    private List<WfoJob> filterType(WfoJobStore store, String type) {
        List<WfoJob> out = new java.util.ArrayList<>();
        for (WfoJob j : store.listAll()) if (type.equals(j.type)) out.add(j);
        return out;
    }
}
