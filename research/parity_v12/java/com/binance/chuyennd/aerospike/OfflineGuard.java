package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.data.SymbolMapperStore;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.net.InetAddress;
import java.net.SocketPermission;
import java.nio.charset.StandardCharsets;
import java.security.Permission;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.zip.GZIPInputStream;

/**
 * HARNESS_OFFLINE=1 (docs/prereg/PREREG_PARITY_V11_WINDOW.md §1): harness doc 100 % tu file cuc bo, chan cung moi duong mang.
 * Lop chan: (1) config gia (AEROSPIKE_READ_CLUSTER=226, host 242/Oracle = offline.invalid); (2) stub AerospikeClient dung
 * truoc jar (constructor => halt 97); (3) SecurityManager: moi connect/resolve khong phai loopback => halt 98;
 * (4) provider file: SimpleSymbolMapper (store file, khong ghi) + FundingFeeManager (funding Vision). Tien kiem sai => halt 96.
 * Env: HARNESS_OFFLINE=1, HARNESS_MAPPER_FILE (dong "symbol,id"), HARNESS_FUNDING_FILE (csv.gz "symbol,ts,rate" — rate la chuoi
 * goc, parse Float.valueOf), HARNESS_FUNDING_EMPTY_OK=1 cho phep khong co funding (chi test).
 */
public final class OfflineGuard {
    private static final Logger LOG = LoggerFactory.getLogger(OfflineGuard.class);
    public static final String HOST_FAKE = "offline.invalid";
    public static final int EXIT_PRE = 96, EXIT_NET = 98;
    static volatile boolean installed;
    static int mapperN, fundingSym, fundingRows, fundingEmptyAdded;
    static Map<String, TreeMap<Long, Float>> fundingRef;

    private OfflineGuard() {
    }

    public static boolean enabled() {
        return "1".equals(System.getenv("HARNESS_OFFLINE"));
    }

    static void fail(String msg) {
        LOG.error("[HARNESS-OFFLINE] TIEN KIEM SAI: {} => halt({})", msg, EXIT_PRE);
        System.err.println("[HARNESS-OFFLINE-PRECHECK] " + msg);
        System.err.flush();
        Runtime.getRuntime().halt(EXIT_PRE);
    }

    /** Goi DAU TIEN trong main, truoc moi truy cap du lieu. Khong bat HARNESS_OFFLINE => khong lam gi (hanh vi cu). */
    public static synchronized void install() throws Exception {
        if (!enabled() || installed) return;
        // (2) stub phai duoc nap TRUOC jar
        java.net.URL u = OfflineGuard.class.getClassLoader().getResource("com/aerospike/client/AerospikeClient.class");
        if (u == null || u.toString().startsWith("jar:")) fail("stub AerospikeClient KHONG dung truoc jar tren classpath: " + u);
        try {
            Class.forName("com.aerospike.client.AerospikeClient").getField("EXIT_CODE");
        } catch (NoSuchFieldException e) {
            fail("AerospikeClient nap duoc khong phai stub");
        }
        // (1) config gia
        String c = Configs.AEROSPIKE_READ_CLUSTER;
        if (!"226".equals(c) || !HOST_FAKE.equals(Configs.AEROSPIKE_HOST_242) || !HOST_FAKE.equals(Configs.AEROSPIKE_HOST_ORACLE)) {
            fail("config khong phai ban offline: READ_CLUSTER=" + c + " host242=" + Configs.AEROSPIKE_HOST_242
                    + " hostOracle=" + Configs.AEROSPIKE_HOST_ORACLE);
        }
        // (4) provider
        Map<String, Short> mapper = readMapper(System.getenv("HARNESS_MAPPER_FILE"));
        installMapper(mapper);
        installFunding(System.getenv("HARNESS_FUNDING_FILE"), mapper.keySet());
        // (3) mang
        installNetGuard();
        installed = true;
        LOG.info("[HARNESS-OFFLINE] BAT: stub={} cluster={} host242={} hostOracle={} mapper={} funding_sym={} rows={} empty_added={}",
                u, c, Configs.AEROSPIKE_HOST_242, Configs.AEROSPIKE_HOST_ORACLE, mapperN, fundingSym, fundingRows, fundingEmptyAdded);
    }

    static Map<String, Short> readMapper(String f) throws Exception {
        if (f == null) fail("thieu HARNESS_MAPPER_FILE");
        Map<String, Short> m = new LinkedHashMap<>();
        Set<Short> ids = new HashSet<>();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8))) {
            String ln;
            while ((ln = r.readLine()) != null) {
                ln = ln.trim();
                if (ln.isEmpty() || ln.startsWith("#") || ln.startsWith("symbol,")) continue;
                String[] p = ln.split(",");
                short id = Short.parseShort(p[1].trim());
                if (!ids.add(id) || m.put(p[0].trim(), id) != null) fail("mapper trung symbol/id: " + ln);
            }
        }
        if (m.isEmpty()) fail("mapper rong: " + f);
        return m;
    }

    static final class FileStore implements SymbolMapperStore {
        final Map<String, Short> map;

        FileStore(Map<String, Short> m) {
            this.map = Collections.unmodifiableMap(new HashMap<>(m));
        }

        public Map<String, Short> loadForInit() {
            return new HashMap<>(map);
        }

        public boolean writable() {
            return false;   // symbol moi => id cuc bo (khong ghi dau ca)
        }

        public Snapshot readForWrite() {
            throw new UnsupportedOperationException("offline store khong ghi");
        }

        public boolean putIfGenerationMatches(String symbol, short id, int expectedGeneration) {
            return false;
        }
    }

    static void installMapper(Map<String, Short> m) throws Exception {
        SimpleSymbolMapper sm = SimpleSymbolMapper.getInstance();
        Field ini = SimpleSymbolMapper.class.getDeclaredField("isInitialized");
        ini.setAccessible(true);
        if ((Boolean) ini.get(sm)) fail("SimpleSymbolMapper da init truoc khi cai store offline");
        Field st = SimpleSymbolMapper.class.getDeclaredField("store");
        st.setAccessible(true);
        st.set(sm, new FileStore(m));
        sm.init();
        Field s2i = SimpleSymbolMapper.class.getDeclaredField("strToId");
        s2i.setAccessible(true);
        mapperN = ((Map<?, ?>) s2i.get(sm)).size();
        if (mapperN != m.size()) fail("mapper nap " + mapperN + " != file " + m.size());
    }

    @SuppressWarnings("unchecked")
    static void installFunding(String f, Set<String> universe) throws Exception {
        Field inst = FundingFeeManager.class.getDeclaredField("INSTANCE");
        inst.setAccessible(true);
        if (inst.get(null) != null) fail("FundingFeeManager da khoi tao truoc offline");
        Constructor<FundingFeeManager> k = FundingFeeManager.class.getDeclaredConstructor();
        k.setAccessible(true);
        FundingFeeManager mgr = k.newInstance();   // constructor mac dinh: KHONG goi initData (Aerospike)
        Field mf = FundingFeeManager.class.getDeclaredField("symbol2FundingFee");
        mf.setAccessible(true);
        ConcurrentHashMap<String, TreeMap<Long, Float>> map = (ConcurrentHashMap<String, TreeMap<Long, Float>>) mf.get(mgr);
        if (f == null || f.isEmpty()) {
            if (!"1".equals(System.getenv("HARNESS_FUNDING_EMPTY_OK"))) fail("thieu HARNESS_FUNDING_FILE");
        } else {
            try (BufferedReader r = new BufferedReader(new InputStreamReader(new GZIPInputStream(new FileInputStream(f)), StandardCharsets.UTF_8))) {
                String ln;
                while ((ln = r.readLine()) != null) {
                    if (ln.startsWith("symbol,") || ln.isEmpty()) continue;
                    String[] p = ln.split(",");
                    map.computeIfAbsent(p[0], x -> new TreeMap<>()).put(Long.parseLong(p[1]), Float.valueOf(p[2]));
                    fundingRows++;
                }
            }
        }
        fundingSym = map.size();
        for (String s : universe) {
            if (!map.containsKey(s)) {
                map.put(s, new TreeMap<>());   // = live khi store khong co record (getFundingMap tra rong) — chan lazy-load
                fundingEmptyAdded++;
            }
        }
        inst.set(null, mgr);
        fundingRef = map;
    }

    static boolean loopback(String h, Set<String> allow) {
        if (h == null) return false;
        String x = h.trim().toLowerCase(Locale.ROOT);
        if (x.startsWith("[") && x.endsWith("]")) x = x.substring(1, x.length() - 1);
        return allow.contains(x) || x.startsWith("127.") || "::1".equals(x) || "0:0:0:0:0:0:0:1".equals(x);
    }

    static void netTrip(String what) {
        LOG.error("[HARNESS-OFFLINE-VIOLATION] ket noi mang bi CHAN: {} => halt({})", what, EXIT_NET, new IllegalStateException("stack"));
        System.err.println("[HARNESS-OFFLINE-VIOLATION] net " + what);
        System.err.flush();
        Runtime.getRuntime().halt(EXIT_NET);
    }

    /** SecurityManager chi chan mang; moi quyen khac cho phep (harness la tool doc file). */
    public static void installNetGuard() {
        final Set<String> allow = new HashSet<>(Arrays.asList("localhost", "127.0.0.1"));
        try {
            allow.add(InetAddress.getLocalHost().getHostName().toLowerCase(Locale.ROOT));   // logback HOSTNAME (resolve, khong connect)
        } catch (Exception ignored) {
            // khong co hostname => chi loopback
        }
        System.setSecurityManager(new SecurityManager() {
            @Override
            public void checkPermission(Permission p) {
                if (p instanceof SocketPermission) sock((SocketPermission) p);
            }

            @Override
            public void checkPermission(Permission p, Object ctx) {
                checkPermission(p);
            }

            void sock(SocketPermission p) {
                String a = p.getActions();
                if (a.contains("connect") || a.contains("resolve") || a.contains("accept")) {
                    String n = p.getName();
                    int i = n.lastIndexOf(':');
                    String h = (i > 0 && n.indexOf(':') == i) ? n.substring(0, i) : n;
                    if (!loopback(h, allow)) netTrip(a + " " + n);
                }
            }

            @Override
            public void checkConnect(String host, int port) {
                if (!loopback(host, allow)) netTrip("connect " + host + ":" + port);
            }

            @Override
            public void checkConnect(String host, int port, Object context) {
                checkConnect(host, port);
            }

            @Override
            public void checkMulticast(InetAddress maddr) {
                netTrip("multicast " + maddr);
            }
        });
    }

    /** Cuoi run: kiem provider khong bi thay doi (khong lazy-load, khong symbol moi ngoai mapper). */
    public static void finish() throws Exception {
        if (!installed) return;
        SimpleSymbolMapper sm = SimpleSymbolMapper.getInstance();
        Field s2i = SimpleSymbolMapper.class.getDeclaredField("strToId");
        s2i.setAccessible(true);
        Field lo = SimpleSymbolMapper.class.getDeclaredField("localOnly");
        lo.setAccessible(true);
        int nNow = ((Map<?, ?>) s2i.get(sm)).size();
        Map<?, ?> local = (Map<?, ?>) lo.get(sm);
        LOG.info("[HARNESS-OFFLINE] KET THUC: mapper {} -> {} (id cuc bo {}: {}), funding symbol {} -> {}", mapperN, nNow,
                local.size(), local.keySet(), fundingSym + fundingEmptyAdded, fundingRef.size());
    }
}
