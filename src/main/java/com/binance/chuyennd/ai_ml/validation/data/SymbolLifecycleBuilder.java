package com.binance.chuyennd.ai_ml.validation.data;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.data.SymbolLifecycleManager;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.market.ExchangeInfoEntry;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

/**
 * TASK-010 — Builder vòng đời coin: dựng set Aerospike {@code symbol_lifecycle} (nguồn sự thật 1 mối
 * thay cách ad-hoc: cột drawdownToBottom sai / hardcode list rải rác).
 *
 * <p>ĐỌC-ONLY phần market data: quét tuần tự theo NGÀY {@code readDataFromAerospike1M_ShortKey} (mẫu như
 * {@link AerospikeCoverageMap}; không có index symbol→time) để lấy {@code firstSeen}/{@code lastSeen}
 * THẬT cho mỗi symbol. Đối chiếu universe đang TRADING từ exchangeInfo (tái dùng logic TASK-008) để phân
 * 3 trạng thái — KHÔNG suy chết/sống từ mỗi data-ta (kẻo đánh chết oan coin sống → tái lập survivorship).
 *
 * <p>3 trạng thái:
 * <ul>
 *   <li><b>LIVE</b> — exchangeInfo status=TRADING VÀ data-ta còn mới ({@code now-lastSeen} ≤ {@value #LIVE_FRESH_DAYS} ngày).</li>
 *   <li><b>DATA_INCOMPLETE</b> — exchangeInfo TRADING NHƯNG data-ta thủng/cũ (coin sống mà ta thiếu data,
 *       vd 8 coin vừa gỡ DIED ở TASK-008 hoặc coin TRADING mà lastSeen lùi xa).</li>
 *   <li><b>DEAD</b> — KHÔNG trong TRADING (delist thật) → {@code delistTs ≈ lastSeen}.</li>
 * </ul>
 *
 * <p>Ghi set {@code symbol_lifecycle} (namespace {@code ticker}) lên CẢ 242 (live) và 226 (sim/backtest đọc
 * qua getReadClient) — key = symbol UPPERCASE, bins: {@code sym, first, last, status, delist}.
 *
 * <p>⚠️ KHÔNG đụng {@code DIED_SYMBOLS}/config/trading/live. Chạy trên 226. SLF4J (không System.out).
 * Chạy lại định kỳ (vòng đời đổi chậm; 1 lần/ngày hoặc thủ công khi cần).
 */
public class SymbolLifecycleBuilder {

    private static final Logger LOG = LoggerFactory.getLogger(SymbolLifecycleBuilder.class);

    private static final String START_DATE = "20210101";
    /** Ngưỡng "data còn mới" để gán LIVE (vs DATA_INCOMPLETE). */
    private static final int LIVE_FRESH_DAYS = 2;

    /** Mẫu kiểm tay khi log summary: 30 core-die (repo DIED) + vài coin gỡ-DIED-008 (DATA_INCOMPLETE) + vài LIVE. */
    private static final String[] SAMPLE = {
            // 30 core die (repo config DIED_SYMBOLS)
            "STPTUSDT", "SNTUSDT", "MBLUSDT", "RADUSDT", "CVXUSDT", "IDEXUSDT", "SLPUSDT", "GLMRUSDT",
            "MDTUSDT", "AUDIOUSDT", "BLUEBIRDUSDT", "FOOTBALLUSDT", "ANTUSDT", "CTKUSDT", "DGBUSDT",
            "STRAXUSDT", "COCOSUSDT", "RAYUSDT", "FTTUSDT", "SCUSDT", "HNTUSDT", "BTCSTUSDT", "BTSUSDT",
            "TOMOUSDT", "SRMUSDT", "CVCUSDT", "USDCUSDT", "BTCDOMUSDT", "WAVESUSDT", "BNXUSDT",
            // vài coin TASK-008 gỡ-DIED (kỳ vọng DATA_INCOMPLETE: TRADING nhưng chưa có data)
            "SONICUSDT", "AERGOUSDT", "CELOUSDT", "LITUSDT",
            // vài coin LIVE phổ biến
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"
    };

    public static final String STATUS_LIVE = "LIVE";
    public static final String STATUS_DATA_INCOMPLETE = "DATA_INCOMPLETE";
    public static final String STATUS_DEAD = "DEAD";

    public static void main(String[] args) {
        try {
            new SymbolLifecycleBuilder().run();
        } catch (Exception e) {
            LOG.error("❌ SymbolLifecycleBuilder lỗi", e);
        }
        System.exit(0);
    }

    private static boolean isUsdtPerp(String s) {
        return s != null && s.endsWith("USDT") && !s.contains("_");
    }

    public void run() throws Exception {
        // Đọc bản ticker đã sync trên 226 (chạy local trên 226 cho nhanh). Phần market data: ĐỌC-ONLY.
        long t0 = System.currentTimeMillis();
        LOG.info("🧬 LIFECYCLE BUILDER | đọc ticker 226 (AEROSPIKE_READ_CLUSTER={}) | từ {} → nay | freshLIVE≤{}d",
                Configs.AEROSPIKE_READ_CLUSTER, START_DATE, LIVE_FRESH_DAYS);

        // 1) Universe đang TRADING từ exchangeInfo (tái dùng logic TASK-008: USDT-perp + status TRADING).
        Set<String> liveSet = fetchLiveSet();
        LOG.info("🌐 LIVE_SET (exchangeInfo TRADING USDT-perp) = {} symbol", liveSet.size());
        if (liveSet.isEmpty()) {
            LOG.error("⛔ LIVE_SET rỗng — exchangeInfo lỗi/không kết nối. DỪNG (tránh gán DEAD oan toàn bộ).");
            return;
        }

        // 2) Quét data-ta lấy firstSeen/lastSeen THẬT cho mỗi symbolId.
        SimpleSymbolMapper mapper = SimpleSymbolMapper.getInstance();
        mapper.init();
        Map<String, Short> all = mapper.getAllMappings();
        int maxId = 0;
        for (Map.Entry<String, Short> e : all.entrySet()) {
            if (isUsdtPerp(e.getKey()) && e.getValue() > maxId) maxId = e.getValue();
        }

        long startTs = Utils.sdfFile.parse(START_DATE).getTime() + 7 * Utils.TIME_HOUR;
        long endTs = System.currentTimeMillis();

        long[] firstSeen = new long[maxId + 1];  // firstSeen[symbolId] (0 = chưa thấy)
        long[] lastSeen = new long[maxId + 1];

        int dayCount = 0, emptyDays = 0, lastMonthLogged = -1;
        for (long d = startTs; d <= endTs; d += Utils.TIME_DAY) {
            TreeMap<Long, KlineObjectSimple[]> day;
            try {
                day = DataManagerAerospikeFloatSim.readDataFromAerospike1M_ShortKey(d);
            } catch (Exception ex) {
                LOG.warn("⚠️ đọc ngày {} lỗi: {}", Utils.normalizeDateYYYYMMDD(d), ex.getMessage());
                continue;
            }
            dayCount++;
            if (day == null || day.isEmpty()) {
                emptyDays++;
                continue;
            }
            // TreeMap minute ASC + ngày ASC ⇒ firstSeen set 1 lần, lastSeen tự kết thúc đúng giá trị max.
            for (Map.Entry<Long, KlineObjectSimple[]> me : day.entrySet()) {
                long minute = me.getKey();
                KlineObjectSimple[] arr = me.getValue();
                if (arr == null) continue;
                int n = Math.min(arr.length, maxId + 1);
                for (int id = 1; id < n; id++) {
                    if (arr[id] != null && Utils.isTickerAvailable(arr[id])) {
                        if (firstSeen[id] == 0) firstSeen[id] = minute;
                        lastSeen[id] = minute;
                    }
                }
            }
            int mi = monthOf(d);
            if (mi != lastMonthLogged) {
                lastMonthLogged = mi;
                LOG.info("   ...quét tới {} ({} ngày, {} rỗng) {}s",
                        Utils.normalizeDateYYYYMMDD(d), dayCount, emptyDays, (System.currentTimeMillis() - t0) / 1000);
            }
        }
        LOG.info("✅ Quét xong {} ngày ({} rỗng) {}s — gán trạng thái + ghi set.",
                dayCount, emptyDays, (System.currentTimeMillis() - t0) / 1000);

        // 3) Dựng record cho universe = (symbol có data) ∪ (LIVE_SET) + phân 3 trạng thái.
        Map<String, long[]> dataSeen = new HashMap<>();   // symbol -> [first,last]
        for (Map.Entry<String, Short> e : all.entrySet()) {
            String sym = e.getKey();
            short id = e.getValue();
            if (!isUsdtPerp(sym) || id > maxId) continue;
            if (firstSeen[id] > 0) dataSeen.put(sym, new long[]{firstSeen[id], lastSeen[id]});
        }

        TreeSet<String> universe = new TreeSet<>();
        universe.addAll(dataSeen.keySet());
        universe.addAll(liveSet);

        long freshMs = (long) LIVE_FRESH_DAYS * Utils.TIME_DAY;
        long now = System.currentTimeMillis();

        WritePolicy wp = new WritePolicy();
        wp.sendKey = true;
        wp.expiration = 0;
        wp.recordExistsAction = RecordExistsAction.UPDATE;
        AerospikeClient c226 = DataManagerAerospikeFloatSim.getClient226();
        // 242 là PRIVATE: chỉ tới được TỪ 226/242. Khi chạy từ dev/Kaggle (chỉ tới 226) thì
        // new AerospikeClient(242) NÉM ngay → phải bọc để KHÔNG chết cả builder. Tới được (chạy trên
        // 226) → vẫn dual-write 242+226 như thiết kế. Tới-không-được → 226-only, log MỘT lần.
        AerospikeClient c242 = null;
        try {
            c242 = DataManagerAerospikeFloatSim.getClient242();
        } catch (Exception ex) {
            LOG.warn("⚠️ Không kết nối 242 (private — chỉ tới từ 226/242). Chạy 226-ONLY, bỏ ghi 242: {}", ex.getMessage());
        }

        int nLive = 0, nIncomplete = 0, nDead = 0, written = 0;
        for (String sym : universe) {
            long first = 0, last = 0;
            long[] seen = dataSeen.get(sym);
            if (seen != null) {
                first = seen[0];
                last = seen[1];
            }
            boolean trading = liveSet.contains(sym);
            String status;
            long delist = 0;
            if (trading) {
                if (last > 0 && (now - last) <= freshMs) {
                    status = STATUS_LIVE;
                    nLive++;
                } else {
                    status = STATUS_DATA_INCOMPLETE;
                    nIncomplete++;
                }
            } else {
                status = STATUS_DEAD;
                delist = last;   // ≈ mốc delist (lastSeen); 0 nếu chưa từng có data
                nDead++;
            }

            Bin[] bins = {
                    new Bin("sym", sym),
                    new Bin("first", first),
                    new Bin("last", last),
                    new Bin("status", status),
                    new Bin("delist", delist)
            };
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, SymbolLifecycleManager.SET_NAME, sym);
            boolean ok = false;
            if (c242 != null) {
                try {
                    c242.put(wp, key, bins);
                    ok = true;
                } catch (Exception ex) {
                    LOG.warn("⚠️ ghi 242 {} lỗi: {}", sym, ex.getMessage());
                }
            }
            try {
                c226.put(wp, key, bins);
                ok = true;
            } catch (Exception ex) {
                LOG.warn("⚠️ ghi 226 {} lỗi: {}", sym, ex.getMessage());
            }
            if (ok) written++;
        }

        LOG.info("💾 Ghi set '{}' xong: {} record | LIVE={} | DATA_INCOMPLETE={} | DEAD={} | targets={}",
                SymbolLifecycleManager.SET_NAME, written, nLive, nIncomplete, nDead,
                (c242 != null ? "242+226" : "226-only"));

        // 4) Sample kiểm tay.
        LOG.info("🔬 SAMPLE (kiểm tay): symbol | status | firstSeen | lastSeen");
        for (String sym : SAMPLE) {
            long[] seen = dataSeen.get(sym);
            String first = seen != null ? Utils.normalizeDateYYYYMMDD(seen[0]) : "—";
            String last = seen != null ? Utils.normalizeDateYYYYMMDD(seen[1]) : "—";
            String status;
            if (liveSet.contains(sym)) {
                status = (seen != null && (now - seen[1]) <= freshMs) ? STATUS_LIVE : STATUS_DATA_INCOMPLETE;
            } else {
                status = STATUS_DEAD;
            }
            LOG.info("   {} | {} | {} → {}", sym, status, first, last);
        }
        LOG.info("🏁 LIFECYCLE BUILDER DONE {}s", (System.currentTimeMillis() - t0) / 1000);
    }

    /** File override LIVE_SET (1 symbol/dòng) đọc từ CWD — dùng khi Binance API bị geo-block (vd Kaggle). */
    private static final String LIVE_SET_FILE = "live_set.txt";

    /**
     * Lấy tập symbol đang giao dịch (status TRADING, USDT-perp).
     * <p>ƯU TIÊN file {@value #LIVE_SET_FILE} trong CWD (mỗi dòng 1 symbol UPPERCASE) nếu có — phục vụ
     * môi trường KHÔNG gọi được Binance (Kaggle bị geo-block "restricted location"): list được pre-fetch
     * sẵn từ máy tới được Binance (vd dev/226) rồi bundle vào dataset. KHÔNG có file → gọi Binance
     * exchangeInfo như cũ (tái dùng pattern TASK-008/BudgetManager).
     *
     * @return set symbol UPPERCASE đang TRADING; rỗng nếu cả file lẫn API đều không cho dữ liệu.
     */
    private Set<String> fetchLiveSet() {
        Set<String> fromFile = loadLiveSetFile();
        if (!fromFile.isEmpty()) {
            LOG.info("🌐 LIVE_SET nạp từ {} = {} symbol (bỏ qua Binance API — môi trường geo-block).",
                    LIVE_SET_FILE, fromFile.size());
            return fromFile;
        }
        Set<String> liveSet = new HashSet<>();
        try {
            List<ExchangeInfoEntry> symbols =
                    ClientSingleton.getInstance().syncRequestClient.getExchangeInformation().getSymbols();
            for (ExchangeInfoEntry s : symbols) {
                String sym = s.getSymbol() == null ? "" : s.getSymbol().toUpperCase();
                if (isUsdtPerp(sym)
                        && StringUtils.equalsIgnoreCase(s.getQuoteAsset(), "USDT")
                        && s.getStatus() != null && s.getStatus().contains("TRADING")) {
                    liveSet.add(sym);
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Lấy exchangeInfo lỗi: {}", e.getMessage());
        }
        return liveSet;
    }

    /**
     * Đọc LIVE_SET override từ file {@value #LIVE_SET_FILE} trong CWD nếu tồn tại.
     * Mỗi dòng 1 symbol; bỏ dòng trống/comment (#); lọc {@link #isUsdtPerp}; upper-case.
     *
     * @return set symbol UPPERCASE; rỗng nếu file không có/đọc lỗi/không dòng hợp lệ.
     */
    private Set<String> loadLiveSetFile() {
        Set<String> set = new HashSet<>();
        java.nio.file.Path p = java.nio.file.Paths.get(LIVE_SET_FILE);
        if (!java.nio.file.Files.exists(p)) return set;
        try {
            for (String line : java.nio.file.Files.readAllLines(p)) {
                String sym = line == null ? "" : line.trim().toUpperCase();
                if (sym.isEmpty() || sym.startsWith("#")) continue;
                if (isUsdtPerp(sym)) set.add(sym);
            }
        } catch (Exception e) {
            LOG.warn("⚠️ đọc {} lỗi: {} — sẽ thử Binance API.", LIVE_SET_FILE, e.getMessage());
        }
        return set;
    }

    private static int monthOf(long ts) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(ts);
        return c.get(Calendar.YEAR) * 12 + c.get(Calendar.MONTH);
    }
}
