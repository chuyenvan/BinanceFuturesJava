package com.binance.chuyennd.ai_ml.data;

import com.binance.chuyennd.aerospike.AerospikeSymbolMapperStore;
import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Symbol (String) &lt;-&gt; id (short) dung chung cho moi process (Aerospike set {@code symbol_mapper}).
 *
 * <p>[MAPAUD 2026-10-11] docs/audit/MAPPER_AUDIT_20261011.md. Truoc fix: {@code getId} cap id moi bang bo dem RIENG
 * trong RAM ({@code ++counter}, khong synchronized, khoi tao = max id luc init) roi {@code MapOperation.put} vao 242
 * khong kiem trung ⇒ nhieu JVM ghi (242 collectData + v_t_m, truoc 10-02 ca shadow/tool Oracle) cung cap 843..850 cho
 * symbol khac nhau ⇒ 8 id dung chung (16 symbol niem yet 07/2026). Sau fix:
 * <ul>
 *   <li><b>Nap</b>: kiem id trung ({@link SymbolIdRules#assertUniqueIds}); {@code SYMBOL_MAPPER_DUP_POLICY}
 *       = FAIL (mac dinh, nem IllegalStateException) | WARN (log ERROR, id trung -&gt; getSymbol tra symbol nho nhat
 *       theo ten, tat dinh).</li>
 *   <li><b>Cap id</b> (process duoc ghi): doc map + generation tu CHINH cum ghi, symbol da co ⇒ dung id do (khong
 *       ghi de); chua co ⇒ id = max(da ghi, cuc bo)+1, ghi CAS (generation + CREATE_ONLY), xung dot ⇒ doc lai thu lai.</li>
 *   <li><b>Process chi doc</b> (shadow/kaggle/tool, Live242WriteGuard chan) hoac loi I/O: id CUC BO duy nhat trong
 *       JVM, KHONG ghi (ban da ghi giu bat bien duy nhat); log WARN/ERROR.</li>
 * </ul>
 */
public class SimpleSymbolMapper {

    private static final Logger LOG = LoggerFactory.getLogger(SimpleSymbolMapper.class);

    public static final String KEY_DUP_POLICY = "SYMBOL_MAPPER_DUP_POLICY";
    static final int MAX_CAS_RETRY = 20;
    /** Tran mang theo id (SymbolIdLimits.CAPACITY; truoc LIVEFIX2 = 1000 hardcode) — vuot =&gt; log ERROR. */
    static final int ID_SOFT_CAP = SymbolIdLimits.CAPACITY;

    // Map lưu trữ: Symbol (String) <-> ID (Short)
    private final Map<String, Short> strToId = new ConcurrentHashMap<>();
    private final Map<Short, String> idToStr = new ConcurrentHashMap<>();
    /** symbol co id CUC BO (khong ghi duoc vao store) — chi de log/kiem. */
    private final Map<String, Short> localOnly = new ConcurrentHashMap<>();

    // Bộ đếm ID cuc bo (max id da biet trong JVM nay). Chi doi trong synchronized.
    private short counter = 0;

    // Cờ đánh dấu đã load dữ liệu hay chưa
    private volatile boolean isInitialized = false;

    private volatile SymbolMapperStore store;
    private final String dupPolicyOverride;

    // --- SINGLETON PATTERN ---

    private SimpleSymbolMapper() {
        this(null, null);
    }

    /** Test / tool: store + policy tuong minh (null = mac dinh Aerospike / Cfg). */
    SimpleSymbolMapper(SymbolMapperStore store, String dupPolicy) {
        this.store = store;
        this.dupPolicyOverride = dupPolicy;
    }

    public Map<Float, String> extractSymbol(TreeMap<Float, Short> rate2Max) {
        Map<Float, String> rate2Symbol = new TreeMap<>();
        for (Map.Entry<Float, Short> entry : rate2Max.entrySet()) {
            String symbol = getSymbol(entry.getValue());
            rate2Symbol.put(entry.getKey(), symbol);
        }
        return rate2Symbol;
    }

    public TreeMap<Float, Short> convertSymbolList(TreeMap<Float, String> rateMax2Symbols) {
        TreeMap<Float, Short> rate2Id = new TreeMap<>();
        for (Map.Entry<Float, String> entry : rateMax2Symbols.entrySet()) {
            short id = getId(entry.getValue());
            rate2Id.put(entry.getKey(), id);
        }
        return rate2Id;
    }

    // Static Inner Class - Holder chứa Instance duy nhất
    // JVM đảm bảo class này chỉ được load và khởi tạo 1 lần duy nhất khi được gọi đến -> Thread-Safe
    private static class Holder {
        private static final SimpleSymbolMapper INSTANCE = new SimpleSymbolMapper();
    }

    // Public method để lấy Instance duy nhất
    public static SimpleSymbolMapper getInstance() {
        return Holder.INSTANCE;
    }

    // -------------------------

    private SymbolMapperStore store() {
        SymbolMapperStore s = store;
        if (s == null) {
            synchronized (this) {
                if (store == null) store = new AerospikeSymbolMapperStore();
                s = store;
            }
        }
        return s;
    }

    private String dupPolicy() {
        String p = dupPolicyOverride != null ? dupPolicyOverride : Cfg.get(KEY_DUP_POLICY);
        return (p == null || p.trim().isEmpty()) ? "FAIL" : p.trim().toUpperCase();
    }

    /**
     * Hàm khởi tạo: Load dữ liệu từ Aerospike vào RAM. Cần gọi hàm này 1 lần lúc start app.
     * [MAPAUD] fail-fast neu mapper co id trung (tru khi SYMBOL_MAPPER_DUP_POLICY=WARN).
     */
    public synchronized void init() {
        if (isInitialized) return;

        LOG.info("🔄 Initializing SimpleSymbolMapper (Singleton) from Aerospike...");
        Map<String, Short> dbMap = store().loadForInit();

        if (dbMap != null && !dbMap.isEmpty()) {
            Map<Short, List<String>> dups = SymbolIdRules.duplicateIds(dbMap);
            if (!dups.isEmpty()) {
                if ("WARN".equals(dupPolicy())) {
                    LOG.error("⛔ [MAPPER-DUP] symbol_mapper co {} id dung chung {} — {}=WARN nen CHAY TIEP; "
                            + "getSymbol(id trung) tra symbol nho nhat theo ten. Sua: SymbolMapperRepairTool.",
                            dups.size(), dups, KEY_DUP_POLICY);
                } else {
                    SymbolIdRules.assertUniqueIds(dbMap, "init");   // nem IllegalStateException
                }
            }
            strToId.putAll(dbMap);
            // Rebuild map ngược (ID -> String) TAT DINH: id trung -> symbol nho nhat theo ten.
            for (Map.Entry<String, Short> entry : new TreeMap<>(dbMap).entrySet()) {
                idToStr.putIfAbsent(entry.getValue(), entry.getKey());
            }
            // Cập nhật counter để ID tiếp theo không bị trùng
            counter = SymbolIdRules.maxId(dbMap);
        }

        isInitialized = true;
        LOG.info("✅ SimpleSymbolMapper initialized. Total: {}, Next ID: {}", strToId.size(), counter + 1);
    }

    /**
     * Lấy ID của Symbol. Đã có trong RAM -&gt; trả về ngay. Chưa có -&gt; {@link #allocate} (CAS trên store, xem javadoc lớp).
     */
    public short getId(String symbol) {
        // Tự động init nếu chưa init (Lazy Load an toàn)
        if (!isInitialized) {
            init();
        }
        Short id = strToId.get(symbol);
        if (id != null) return id;
        return allocate(symbol);
    }

    private synchronized short allocate(String symbol) {
        Short known = strToId.get(symbol);   // luong khac vua cap trong luc cho khoa
        if (known != null) return known;
        SymbolMapperStore st = store();
        if (st.writable()) {
            try {
                for (int attempt = 1; attempt <= MAX_CAS_RETRY; attempt++) {
                    SymbolMapperStore.Snapshot snap = st.readForWrite();
                    Short persisted = snap.map.get(symbol);
                    if (persisted != null) {        // process khac da cap — dung lai, KHONG ghi de
                        register(symbol, persisted);
                        LOG.info("🗺️ [MAPPER] {} -> {} (da co tren store, process khac cap).", symbol, persisted);
                        return persisted;
                    }
                    short newId = SymbolIdRules.nextId(SymbolIdRules.maxId(snap.map), counter);
                    if (st.putIfGenerationMatches(symbol, newId, snap.generation)) {
                        register(symbol, newId);
                        LOG.info("🗺️ [MAPPER] cap id moi {} -> {} (CAS gen={}, lan {}).", symbol, newId,
                                snap.generation, attempt);
                        return newId;
                    }
                    LOG.warn("[MAPPER] xung dot CAS khi cap {} (gen={}, lan {}/{}) — doc lai.", symbol,
                            snap.generation, attempt, MAX_CAS_RETRY);
                }
                LOG.error("⛔ [MAPPER] {} lan CAS deu xung dot khi cap {} -> dung id CUC BO (khong ghi).",
                        MAX_CAS_RETRY, symbol);
            } catch (RuntimeException e) {
                LOG.error("⛔ [MAPPER] loi store khi cap {}: {} -> dung id CUC BO (khong ghi).", symbol, e.toString());
            }
        }
        short localId = SymbolIdRules.nextId((short) 0, counter);
        register(symbol, localId);
        localOnly.put(symbol, localId);
        LOG.warn("[MAPPER] {} -> {} id CUC BO (process chi doc hoac loi store) — KHONG ghi symbol_mapper.",
                symbol, localId);
        return localId;
    }

    private void register(String symbol, short id) {
        strToId.put(symbol, id);
        String prev = idToStr.putIfAbsent(id, symbol);
        if (prev != null && !prev.equals(symbol)) {
            LOG.error("⛔ [MAPPER] id {} da thuoc {} trong JVM nay, nay store gan cho {} (id cuc bo cu?).", id, prev, symbol);
        }
        if (id > counter) counter = id;
        if (id >= ID_SOFT_CAP) {
            LOG.error("⛔ [MAPPER-CAP] {} -> id {} >= {}: SymbolIdLimits.CAPACITY: HistoryManager bo symbol (live, [ID-CAP]) "
                    + "hoac sim nem IllegalStateException — nang tran truoc (docs/audit/MAPPER_AUDIT_20261011.md).", symbol, id, ID_SOFT_CAP);
        }
    }

    public String getSymbol(short id) {
        if (!isInitialized) init();
        return idToStr.getOrDefault(id, "UNKNOWN-" + id);
    }

    public Map<String, Short> getAllMappings() {
        if (!isInitialized) init();
        return strToId;
    }

    /** Symbol dang dung id cuc bo (khong ghi duoc). */
    public Map<String, Short> getLocalOnlyMappings() {
        return localOnly;
    }

    public static void main(String[] args) {
        // 1. Khởi tạo (tùy chọn, vì getId tự gọi nếu cần)
        SimpleSymbolMapper.getInstance().init();
        // 2. Test lấy ID
        short id = SimpleSymbolMapper.getInstance().getId("ETHUSDT");
        String symbol = SimpleSymbolMapper.getInstance().getSymbol(id);
        LOG.info("ETHUSDT -> {} -> {}", id, symbol);
    }
}
