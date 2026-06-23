//package com.binance.chuyennd.trading.monitor;
//
//// ============================================================================
//// ORACLE FREE-TIER WATCHER — bản Java port từ /root/oracle_monitor.sh (v5)
//// Phát hiện tài nguyên billable/thu hồi OCI trong ~5 phút. Đo TÀI NGUYÊN (tức thời),
//// không đo TIỀN (trễ 24h). Quét MỌI compartment + MỌI AD.
////
//// Khác biệt so với bản bash (cố ý):
////   - Gọi `oci` CLI qua ProcessBuilder (giữ nguyên cách cũ, không dùng OCI Java SDK).
////   - Thay `jq` bằng Jackson (com.fasterxml.jackson.databind).
////   - Log qua SLF4J (KHÔNG System.out). Muốn ghi ra oracle_monitor.log như bản
////     bash thì cấu hình 1 file appender trong logback/log4j.
////   - PATH-fix (lỗi v5): set biến môi trường OCI_BIN=/root/bin/oci khi chạy cron
////     để chắc chắn tìm được oci (cron PATH tối thiểu không thấy /root/bin/oci).
////
//// Build: Corretto-17, --release 11. Cần Jackson + SLF4J trên classpath.
//// Chạy tay test:  java -DOCI_BIN=/root/bin/oci ... monitor.OracleMonitor
//// Cron:           */5 * * * * OCI_BIN=/root/bin/oci java -cp <jar> monitor.OracleMonitor
//// ============================================================================
//
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
//import java.io.IOException;
//import java.net.URI;
//import java.net.URLEncoder;
//import java.net.http.HttpClient;
//import java.net.http.HttpRequest;
//import java.net.http.HttpResponse;
//import java.nio.channels.FileChannel;
//import java.nio.channels.FileLock;
//import java.nio.channels.OverlappingFileLockException;
//import java.nio.charset.StandardCharsets;
//import java.nio.file.Files;
//import java.nio.file.Path;
//import java.nio.file.Paths;
//import java.nio.file.StandardOpenOption;
//import java.time.Duration;
//import java.util.ArrayList;
//import java.util.LinkedHashMap;
//import java.util.List;
//import java.util.Map;
//import java.util.TreeSet;
//import java.util.concurrent.TimeUnit;
//import java.util.stream.Collectors;
//
//public class OracleMonitor {
//
//    private static final Logger log = LoggerFactory.getLogger(OracleMonitor.class);
//    private static final ObjectMapper MAPPER = new ObjectMapper();
//
//    // ===== CONFIG (giữ nguyên từ script) =====
//    static final String TENANCY =
//            "ocid1.tenancy.oc1..aaaaaaaapr72ui5bj5hzcax7tbgf5q6po74nsgoktumywgzg6app7oygytla";
//    static final Path BASELINE = Paths.get(home(), "oci_baseline.txt");
//    static final Path SECRETS  = Paths.get(home(), ".oci_monitor_secrets");
//    static final Path NOW_FILE = Paths.get(System.getProperty("java.io.tmpdir"), "oci_now.txt");
//    static final Path LOCK     = Paths.get("/var/lock/oracle_monitor.lock");
//
//    // Whitelist free-tier
//    static final int MAX_A1_OCPU   = 4;
//    static final int MAX_A1_MEM    = 24;   // GB
//    static final int MAX_VOLUME_GB = 200;
//
//    // PATH-fix v5: cho phép ép full path oci khi cron PATH tối thiểu (mặc định "oci").
//    static final String OCI = System.getProperty("OCI_BIN",
//            System.getenv().getOrDefault("OCI_BIN", "oci"));
//
//    private static final HttpClient HTTP = HttpClient.newBuilder()
//            .connectTimeout(Duration.ofSeconds(10)).build();
//
//    // ===== state =====
//    private int err = 0;       // đếm lệnh oci rc!=0 — KHÔNG mù khi 1 call fail âm thầm
//    private boolean ok = true;
//    private String tgToken = "";
//    private String tgChat  = "";
//
//    // flock handles
//    private static FileChannel lockChannel;
//    private static FileLock lock;
//
//    public static void main(String[] args) {
//        // ===== flock: bỏ lượt nếu lần trước chưa xong (oci chậm, tránh chồng cron */5) =====
//        if (!lockOrSkip()) return;
//        try {
//            new OracleMonitor().run();
//        } finally {
//            releaseLock();
//        }
//    }
//
//    void run() {
//        loadSecrets();
//        boolean tgOn = !tgToken.isEmpty() && !tgChat.isEmpty();
//
//        // ===== BƯỚC 0: mọi compartment ACTIVE (gồm root) + mọi AD =====
//        List<String> comps = listCompartments();
//        List<String> ads   = listAvailabilityDomains();
//
//        // ===== BANNER PARAMS =====
//        log.info("──── WATCHER (java) | whitelist: A1_OCPU<={} A1_RAM<={}G volume<={}G "
//                        + "| compartments={} AD={} | TG={} | baseline={} ────",
//                MAX_A1_OCPU, MAX_A1_MEM, MAX_VOLUME_GB,
//                comps.size(), ads.size(), tgOn ? "on" : "off", BASELINE);
//
//        // ===== CHECK 1: instances =====
//        List<Inst> insts = collectInstances(comps);
//        double a1Ocpu = insts.stream().filter(i -> i.shape.equals("VM.Standard.A1.Flex"))
//                .mapToDouble(i -> i.ocpu).sum();
//        double a1Mem = insts.stream().filter(i -> i.shape.equals("VM.Standard.A1.Flex"))
//                .mapToDouble(i -> i.mem).sum();
//        String badList = insts.stream()
//                .filter(i -> !i.shape.equals("VM.Standard.A1.Flex")
//                        && !i.shape.equals("VM.Standard.E2.1.Micro"))
//                .map(i -> i.name + "(" + i.shape + ", " + i.state + ")")
//                .collect(Collectors.joining("; "));
//
//        if (!badList.isEmpty())
//            alert("Instance NGOÀI whitelist shape (trả phí nếu chạy): " + badList);
//        if (a1Ocpu > MAX_A1_OCPU)
//            alert("Tổng A1 OCPU = " + fmt(a1Ocpu) + " > " + MAX_A1_OCPU + " (vượt free)!");
//        if (a1Mem > MAX_A1_MEM)
//            alert("Tổng A1 RAM = " + fmt(a1Mem) + "GB > " + MAX_A1_MEM + "GB (vượt free)!");
//
//        log.info("┌─ INSTANCE: tổng {} | A1 đang dùng {}/{} OCPU, {}/{}G RAM",
//                insts.size(), fmt(a1Ocpu), MAX_A1_OCPU, fmt(a1Mem), MAX_A1_MEM);
//        if (insts.isEmpty()) {
//            log.info("│   (không có instance non-terminated)");
//        } else {
//            for (Inst i : insts)
//                log.info("│   {} | {} | {} | {}OCPU {}G", i.name, i.shape, i.state, fmt(i.ocpu), fmt(i.mem));
//        }
//
//        // ===== CHECK 2: volumes (block + boot) > 200GB — MỌI compartment + MỌI AD =====
//        double totalGb = 0;
//        List<String> volLines = new ArrayList<>();
//        for (String c : comps) {
//            JsonNode vData = ociData(OCI, "bv", "volume", "list", "--compartment-id", c, "--all", "--output", "json");
//            for (JsonNode n : vData) {
//                if ("TERMINATED".equals(n.path("lifecycle-state").asText())) continue;
//                double sz = n.path("size-in-gbs").asDouble(0);
//                totalGb += sz;
//                volLines.add("block " + n.path("display-name").asText() + " " + fmt(sz) + "G "
//                        + n.path("lifecycle-state").asText());
//            }
//            for (String a : ads) {
//                JsonNode bData = ociData(OCI, "bv", "boot-volume", "list",
//                        "--compartment-id", c, "--availability-domain", a, "--all", "--output", "json");
//                for (JsonNode n : bData) {
//                    if ("TERMINATED".equals(n.path("lifecycle-state").asText())) continue;
//                    double sz = n.path("size-in-gbs").asDouble(0);
//                    totalGb += sz;
//                    volLines.add("boot  " + n.path("display-name").asText() + " " + fmt(sz) + "G "
//                            + n.path("lifecycle-state").asText());
//                }
//            }
//        }
//        if (totalGb > MAX_VOLUME_GB)
//            alert("Tổng volume " + fmt(totalGb) + "GB > " + MAX_VOLUME_GB + "GB free!");
//
//        log.info("┌─ VOLUME: tổng {}G / {}G", fmt(totalGb), MAX_VOLUME_GB);
//        if (volLines.isEmpty()) {
//            log.info("│   (không có volume non-terminated)");
//        } else {
//            for (String l : volLines) log.info("│   {}", l);
//        }
//
//        // ===== CHECK 3: diff toàn bộ resource với baseline (search tenancy-wide) =====
//        TreeSet<String> now = searchAllResources();   // sort -u tự nhiên bằng TreeSet
//
//        // best-effort ghi file audit (giống /tmp/oci_now.txt), không fail nếu lỗi
//        try {
//            Files.write(NOW_FILE, (String.join("\n", now) + (now.isEmpty() ? "" : "\n"))
//                    .getBytes(StandardCharsets.UTF_8));
//        } catch (IOException e) {
//            log.debug("Không ghi được {} (bỏ qua, không critical): {}", NOW_FILE, e.getMessage());
//        }
//
//        if (!now.isEmpty()) {
//            log.info("┌─ INVENTORY: {} resource active | theo loại:", now.size());
//            for (Map.Entry<String, Integer> e : countByType(now).entrySet())
//                log.info("│   {} {}", String.format("%7d", e.getValue()), e.getKey());
//        }
//
//        if (now.isEmpty()) {
//            alert("Resource search trả rỗng — kiểm tra CLI.");
//        } else if (!Files.exists(BASELINE)) {
//            try {
//                Files.write(BASELINE, (String.join("\n", now) + "\n").getBytes(StandardCharsets.UTF_8));
//                alert("Baseline mới được tạo (" + now.size() + " resource). Mở " + BASELINE
//                        + " xác nhận đúng trạng thái chuẩn.");
//            } catch (IOException e) {
//                alert("Không tạo được baseline " + BASELINE + ": " + e.getMessage());
//            }
//        } else {
//            TreeSet<String> base = readBaseline();
//            // comm -13 baseline now  -> chỉ có trong now  -> resource MỚI
//            List<String> newOnes = now.stream().filter(s -> !base.contains(s)).collect(Collectors.toList());
//            // comm -23 baseline now  -> chỉ có trong baseline -> BIẾN MẤT
//            List<String> gone = base.stream().filter(s -> !now.contains(s)).collect(Collectors.toList());
//            if (!newOnes.isEmpty())
//                alert("Resource MỚI xuất hiện: " + String.join(";", newOnes)); // bash dùng ';' (tr) — giữ nguyên
//            if (!gone.isEmpty())
//                alert("Resource BIẾN MẤT (máy bị thu hồi/xóa?): " + String.join(";", gone));
//        }
//
//        // ===== đếm lỗi oci: nếu có call fail thì kết quả có thể THIẾU =====
//        if (err > 0)
//            alert(err + " lệnh oci lỗi (rc!=0) — kết quả có thể THIẾU, kiểm tra quyền/mạng.");
//
//        if (ok)
//            log.info("✅ OK — volume hiện {}GB/{}GB, A1 {}c/{}G, mọi thứ trong whitelist free-tier.",
//                    fmt(totalGb), MAX_VOLUME_GB, fmt(a1Ocpu), fmt(a1Mem));
//    }
//
//    // ===== BƯỚC 0 helpers =====
//
//    private List<String> listCompartments() {
//        List<String> comps = new ArrayList<>();
//        comps.add(TENANCY);
//        Cmd c = exec(OCI, "iam", "compartment", "list",
//                "--compartment-id-in-subtree", "true", "--all", "--output", "json");
//        if (c.rc != 0) err++;
//        if (c.out == null || c.out.isBlank()) {
//            alert("Không list được compartment — kiểm tra oci CLI/quyền.");
//            return comps; // chỉ TENANCY, giống bash
//        }
//        for (JsonNode n : tree(c.out).path("data")) {
//            if ("ACTIVE".equals(n.path("lifecycle-state").asText()))
//                comps.add(n.path("id").asText());
//        }
//        return comps;
//    }
//
//    private List<String> listAvailabilityDomains() {
//        List<String> ads = new ArrayList<>();
//        Cmd c = exec(OCI, "iam", "availability-domain", "list",
//                "--compartment-id", TENANCY, "--output", "json");
//        if (c.rc != 0) err++;
//        if (c.out != null && !c.out.isBlank()) {
//            for (JsonNode n : tree(c.out).path("data"))
//                ads.add(n.path("name").asText());
//        }
//        if (ads.isEmpty()) alert("Không list được availability-domain.");
//        return ads;
//    }
//
//    // ===== CHECK 1 helper =====
//
//    private List<Inst> collectInstances(List<String> comps) {
//        List<Inst> out = new ArrayList<>();
//        for (String c : comps) {
//            JsonNode data = ociData(OCI, "compute", "instance", "list",
//                    "--compartment-id", c, "--all", "--output", "json");
//            for (JsonNode n : data) {
//                String st = n.path("lifecycle-state").asText();
//                if ("TERMINATED".equals(st)) continue;
//                Inst i = new Inst();
//                i.name  = n.path("display-name").asText();
//                i.state = st;
//                i.shape = n.path("shape").asText();
//                JsonNode sc = n.path("shape-config");
//                i.ocpu = sc.path("ocpus").asDouble(0);
//                i.mem  = sc.path("memory-in-gbs").asDouble(0);
//                out.add(i);
//            }
//        }
//        return out;
//    }
//
//    // ===== CHECK 3 helper =====
//
//    private TreeSet<String> searchAllResources() {
//        TreeSet<String> now = new TreeSet<>();
//        Cmd c = exec(OCI, "search", "resource", "structured-search",
//                "--query-text", "query all resources", "--output", "json");
//        if (c.rc != 0) err++;
//        if (c.out == null || c.out.isBlank()) return now;
//        for (JsonNode n : tree(c.out).path("data").path("items")) {
//            String ls = n.path("lifecycle-state").asText("x");
//            if (ls.matches("(?i).*(TERMINAT|DELET).*")) continue; // bỏ TERMINATED/DELETED
//            now.add(n.path("resource-type").asText() + "\t" + n.path("display-name").asText());
//        }
//        return now;
//    }
//
//    private TreeSet<String> readBaseline() {
//        TreeSet<String> base = new TreeSet<>();
//        try {
//            for (String l : Files.readAllLines(BASELINE))
//                if (!l.isEmpty()) base.add(l);
//        } catch (IOException e) {
//            log.warn("Không đọc được baseline {}: {}", BASELINE, e.getMessage());
//        }
//        return base;
//    }
//
//    private static Map<String, Integer> countByType(TreeSet<String> now) {
//        Map<String, Integer> tmp = new LinkedHashMap<>();
//        for (String line : now) {
//            String type = line.split("\t", 2)[0];
//            tmp.merge(type, 1, Integer::sum);
//        }
//        // sort -rn theo count giảm dần
//        return tmp.entrySet().stream()
//                .sorted((x, y) -> Integer.compare(y.getValue(), x.getValue()))
//                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue,
//                        (a, b) -> a, LinkedHashMap::new));
//    }
//
//    // ===== ALERT + Telegram =====
//
//    private void alert(String msg) {
//        ok = false;
//        log.warn("[ALERT] {}", msg);
//        if (!tgToken.isEmpty() && !tgChat.isEmpty()) sendTelegram("[ORACLE] " + msg);
//    }
//
//    private void sendTelegram(String text) {
//        try {
//            String body = "chat_id=" + URLEncoder.encode(tgChat, StandardCharsets.UTF_8)
//                    + "&text=" + URLEncoder.encode(text, StandardCharsets.UTF_8);
//            HttpRequest req = HttpRequest.newBuilder(
//                            URI.create("https://api.telegram.org/bot" + tgToken + "/sendMessage"))
//                    .timeout(Duration.ofSeconds(10))
//                    .header("Content-Type", "application/x-www-form-urlencoded")
//                    .POST(HttpRequest.BodyPublishers.ofString(body))
//                    .build();
//            HTTP.send(req, HttpResponse.BodyHandlers.discarding()); // -s: bỏ qua nội dung
//        } catch (Exception e) {
//            log.debug("Gửi Telegram lỗi (bỏ qua): {}", e.getMessage());
//        }
//    }
//
//    // ===== secrets (.oci_monitor_secrets dạng shell: TG_TOKEN="..." / TG_CHAT="...") =====
//
//    private void loadSecrets() {
//        if (!Files.exists(SECRETS)) return;
//        try {
//            for (String raw : Files.readAllLines(SECRETS)) {
//                String line = raw.trim();
//                if (line.isEmpty() || line.startsWith("#")) continue;
//                if (line.startsWith("export ")) line = line.substring(7).trim();
//                int eq = line.indexOf('=');
//                if (eq <= 0) continue;
//                String k = line.substring(0, eq).trim();
//                String v = stripQuotes(line.substring(eq + 1).trim());
//                if ("TG_TOKEN".equals(k)) tgToken = v;
//                else if ("TG_CHAT".equals(k)) tgChat = v;
//            }
//        } catch (IOException e) {
//            log.warn("Không đọc được secrets {}: {}", SECRETS, e.getMessage());
//        }
//    }
//
//    private static String stripQuotes(String v) {
//        if (v.length() >= 2
//                && ((v.startsWith("\"") && v.endsWith("\"")) || (v.startsWith("'") && v.endsWith("'"))))
//            return v.substring(1, v.length() - 1);
//        return v;
//    }
//
//    // ===== oci/process helpers =====
//
//    /** Chạy lệnh -> Cmd{rc,out}. Tự đếm err nếu rc!=0 do caller xử lý ngữ cảnh. */
//    private static Cmd exec(String... args) {
//        Cmd c = new Cmd();
//        try {
//            ProcessBuilder pb = new ProcessBuilder(args);
//            pb.redirectError(ProcessBuilder.Redirect.DISCARD); // tương đương 2>/dev/null
//            Process p = pb.start();
//            byte[] data = p.getInputStream().readAllBytes();
//            c.out = new String(data, StandardCharsets.UTF_8);
//            if (!p.waitFor(180, TimeUnit.SECONDS)) {
//                p.destroyForcibly();
//                c.rc = -1;
//            } else {
//                c.rc = p.exitValue();
//            }
//        } catch (Exception e) {
//            c.rc = -1;
//            c.out = "";
//            log.debug("exec lỗi {}: {}", String.join(" ", args), e.getMessage());
//        }
//        return c;
//    }
//
//    /** Chạy lệnh oci, đếm err nếu rc!=0, trả node "data" (rỗng nếu lỗi/parse fail). */
//    private JsonNode ociData(String... args) {
//        Cmd c = exec(args);
//        if (c.rc != 0) err++;
//        if (c.out == null || c.out.isBlank()) return MAPPER.createArrayNode();
//        return tree(c.out).path("data");
//    }
//
//    private static JsonNode tree(String json) {
//        try {
//            return MAPPER.readTree(json);
//        } catch (Exception e) {
//            log.debug("Parse JSON lỗi (bỏ qua): {}", e.getMessage());
//            return MAPPER.createObjectNode();
//        }
//    }
//
//    // ===== flock =====
//
//    private static boolean lockOrSkip() {
//        try {
//            Path dir = LOCK.getParent();
//            if (dir == null || !Files.exists(dir)) {
//                // /var/lock không tồn tại (vd test trên Windows) -> chạy không khóa
//                log.debug("Lock dir {} không có — chạy không khóa (test mode).", dir);
//                return true;
//            }
//            lockChannel = FileChannel.open(LOCK, StandardOpenOption.CREATE, StandardOpenOption.WRITE);
//            lock = lockChannel.tryLock();
//            if (lock == null) {
//                log.info("đang chạy dở — bỏ lượt này.");
//                return false;
//            }
//            return true;
//        } catch (OverlappingFileLockException e) {
//            log.info("đang chạy dở — bỏ lượt này.");
//            return false;
//        } catch (IOException e) {
//            log.warn("Không tạo được lock {} — chạy không khóa: {}", LOCK, e.getMessage());
//            return true;
//        }
//    }
//
//    private static void releaseLock() {
//        try { if (lock != null) lock.release(); } catch (Exception ignore) { }
//        try { if (lockChannel != null) lockChannel.close(); } catch (Exception ignore) { }
//    }
//
//    // ===== util =====
//
//    private static String home() {
//        String h = System.getenv("HOME");
//        if (h == null || h.isEmpty()) h = System.getProperty("user.home");
//        return h;
//    }
//
//    /** In số như jq: số nguyên không phần thập phân; còn lại giữ thập phân. */
//    private static String fmt(double d) {
//        if (d == Math.rint(d) && !Double.isInfinite(d)) return Long.toString((long) d);
//        return Double.toString(d);
//    }
//
//    // ===== POJOs =====
//
//    private static final class Cmd {
//        int rc;
//        String out = "";
//    }
//
//    private static final class Inst {
//        String name;
//        String state;
//        String shape;
//        double ocpu;
//        double mem;
//    }
//}