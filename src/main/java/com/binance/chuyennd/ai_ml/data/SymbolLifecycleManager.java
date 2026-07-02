package com.binance.chuyennd.ai_ml.data;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.AerospikeException;
import com.aerospike.client.policy.ScanPolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * TASK-010 — Runtime manager đọc vòng đời coin từ set Aerospike {@code symbol_lifecycle}
 * (do {@code SymbolLifecycleBuilder} dựng). Load-cache 1 LẦN như {@link SimpleSymbolMapper}.
 *
 * <p>Dùng ở feature/basket (lọc {@link #isAlive(String, long)} → bỏ coin chưa sinh/đã chết/zombie) và
 * backtest (không mở/giữ lệnh sau lastSeen). TÍCH HỢP ở task export feature (H1) — KHÔNG đụng live ở
 * TASK-010. Read client theo cùng quy ước getReadClient của DataManager (226 khi Kaggle/HPO, else 242).
 */
public class SymbolLifecycleManager {

    private static final Logger LOG = LoggerFactory.getLogger(SymbolLifecycleManager.class);

    /** Tên set Aerospike (namespace {@code ticker}). */
    public static final String SET_NAME = "symbol_lifecycle";

    /** Bản ghi vòng đời 1 coin. */
    public static class Lifecycle {
        public final long firstSeen;
        public final long lastSeen;
        public final String status;
        public final long delistTs;

        public Lifecycle(long firstSeen, long lastSeen, String status, long delistTs) {
            this.firstSeen = firstSeen;
            this.lastSeen = lastSeen;
            this.status = status;
            this.delistTs = delistTs;
        }
    }

    private final Map<String, Lifecycle> cache = new ConcurrentHashMap<>();
    private volatile boolean isInitialized = false;

    private static class Holder {
        private static final SymbolLifecycleManager INSTANCE = new SymbolLifecycleManager();
    }

    public static SymbolLifecycleManager getInstance() {
        return Holder.INSTANCE;
    }

    /** Read client dùng chung {@link DataManagerAerospikeFloatSim#getReadClient()} (TASK-112: gom 1 chỗ, hết bản sao if). */
    private static AerospikeClient readClient() {
        return DataManagerAerospikeFloatSim.getReadClient();
    }

    /** Nạp toàn bộ set {@code symbol_lifecycle} vào cache (1 lần). Idempotent. */
    public synchronized void init() {
        if (isInitialized) return;
        LOG.info("🔄 Nạp SymbolLifecycleManager từ Aerospike set '{}'...", SET_NAME);
        try {
            ScanPolicy policy = new ScanPolicy();
            policy.concurrentNodes = true;
            readClient().scanAll(policy, Configs.AEROSPIKE_NAMESPACE, SET_NAME, (key, rec) -> {
                String sym = rec.getString("sym");
                if (sym == null && key.userKey != null) sym = key.userKey.toString();
                if (sym == null) return;
                cache.put(sym, new Lifecycle(
                        rec.getLong("first"), rec.getLong("last"),
                        rec.getString("status"), rec.getLong("delist")));
            }, "sym", "first", "last", "status", "delist");
        } catch (AerospikeException e) {
            LOG.warn("⚠️ scan set '{}' lỗi (set chưa dựng?): {}", SET_NAME, e.getMessage());
        }
        isInitialized = true;
        LOG.info("✅ SymbolLifecycleManager nạp {} symbol.", cache.size());
    }

    private Lifecycle get(String symbol) {
        if (!isInitialized) init();
        return symbol == null ? null : cache.get(symbol.toUpperCase());
    }

    /**
     * Số symbol đã nạp từ set {@code symbol_lifecycle} (gọi {@link #init()} nếu chưa). Dùng làm GUARD:
     * giá trị {@code 0} nghĩa là set chưa dựng (builder TASK-010 chưa chạy) → caller PHẢI dừng,
     * KHÔNG được fallback đọc {@code DIED_SYMBOLS} âm thầm (xem TASK-024).
     *
     * @return kích thước cache vòng đời (0 nếu set rỗng/chưa dựng)
     */
    public int loadedCount() {
        if (!isInitialized) init();
        return cache.size();
    }

    /**
     * Coin có data SỐNG tại thời điểm t hay không (dùng lọc zombie ở feature/backtest).
     *
     * @param symbol symbol (sẽ uppercase)
     * @param t      mốc thời gian (ms)
     * @return true nếu firstSeen ≤ t ≤ lastSeen (đã từng có data và chưa quá lastSeen)
     */
    public boolean isAlive(String symbol, long t) {
        Lifecycle lc = get(symbol);
        return lc != null && lc.firstSeen > 0 && t >= lc.firstSeen && t <= lc.lastSeen;
    }

    /**
     * @param symbol symbol
     * @return firstSeen (ms) hoặc 0 nếu không có bản ghi/chưa có data
     */
    public long getFirstSeen(String symbol) {
        Lifecycle lc = get(symbol);
        return lc == null ? 0 : lc.firstSeen;
    }

    /**
     * @param symbol symbol
     * @return lastSeen (ms) hoặc 0 nếu không có bản ghi/chưa có data
     */
    public long getLastSeen(String symbol) {
        Lifecycle lc = get(symbol);
        return lc == null ? 0 : lc.lastSeen;
    }

    /**
     * Trạng thái HIỆN TẠI (LIVE / DATA_INCOMPLETE / DEAD) theo builder gần nhất.
     *
     * @param symbol symbol
     * @return status, hoặc {@code "UNKNOWN"} nếu không có bản ghi
     */
    public String getStatus(String symbol) {
        Lifecycle lc = get(symbol);
        return lc == null ? "UNKNOWN" : lc.status;
    }

    /**
     * Trạng thái TẠI thời điểm t (point-in-time, cho backtest):
     * {@code PRE_LIST} (t &lt; firstSeen), {@code LIVE} (firstSeen ≤ t ≤ lastSeen), {@code DEAD} (t &gt; lastSeen).
     *
     * @param symbol symbol
     * @param t      mốc thời gian (ms)
     * @return trạng thái point-in-time; {@code UNKNOWN} nếu không có bản ghi/data
     */
    public String getStatus(String symbol, long t) {
        Lifecycle lc = get(symbol);
        if (lc == null || lc.firstSeen == 0) return "UNKNOWN";
        if (t < lc.firstSeen) return "PRE_LIST";
        if (t > lc.lastSeen) return "DEAD";
        return "LIVE";
    }
}
