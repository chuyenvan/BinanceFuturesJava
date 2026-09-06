package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.Collections;
import java.util.Set;
import java.util.TreeSet;
import java.util.concurrent.ConcurrentHashMap;

/**
 * SYMBOL DAC BIET "LEGACY" — vi the THAT co tu truoc, van dong THAT theo duong HEAD,
 * KHONG duoc so giay C3 dung toi. CHI co nghia khi {@link LiveProfileC3#on()}.
 *
 * <p>VI SAO CAN: tren 242 co 66 vi the that mo tu truoc. Khi bat {@code LIVE_PROFILE=c3_shadow}
 * tren CUNG mot JVM, hai duong cung ton tai:
 * <ul>
 *   <li>duong THAT: dong 66 vi the cu (SL/TP/reduce-only KHONG bi {@code SHADOW_NO_PUSH} chan),</li>
 *   <li>duong GIAY: {@link ShadowBookC3} chay C3 song song, khong lenh that.</li>
 * </ul>
 * Neu khong tach, co C3 (arm 0.07 / ratchet lien tuc / time-stop 168h) se ap len duong dong
 * vi the THAT => doi luat dong cua tien that. Lop nay danh dau tap symbol do de:
 * <ol>
 *   <li>duong dong that cua chung giu <b>byte-identical HEAD</b>
 *       ({@link LiveProfileC3#armRateFor}, {@link LiveProfileC3#ratchetDeadzoneMultFor},
 *        {@link LiveProfileC3#timeStopApplies}),</li>
 *   <li>so giay KHONG mo entry giay cho chung ({@code [SHADOW] skip-LEGACY}) va chung
 *       KHONG chiem slot top-K cua so giay.</li>
 * </ol>
 *
 * <p>Nguon su that: reconcile tu Binance moi tick trong
 * {@code BinanceOrderTradingManager.updatePositionInfo()} — LEGACY = (vi the that) \ (so giay).
 * Tu THU HEP khi vi the that dong. Ghi dia {@code run/legacy_symbols.csv} de song sot restart
 * (JVM tu restart moi 4h) truoc khi reconcile dau tien kip chay.
 *
 * <p>Co TAT (mac dinh moi noi khac): {@link #isLegacySymbol} tra {@code false} NGAY, khong doc
 * file, khong tao file => duong HEAD khong doi mot bit.
 */
public final class LegacySymbols {

    private static final Logger LOG = LoggerFactory.getLogger(LegacySymbols.class);

    /** Duong dan mac dinh, tuong doi so voi cwd cua JVM (giong pidfile {@code run/}). */
    public static final String DEFAULT_FILE = "run/legacy_symbols.csv";

    private static volatile LegacySymbols INSTANCE;

    private final Set<String> legacy = Collections.newSetFromMap(new ConcurrentHashMap<String, Boolean>());
    private final String path;

    private LegacySymbols(String path) {
        this.path = path;
        load();
    }

    public static LegacySymbols getInstance() {
        if (INSTANCE == null) {
            synchronized (LegacySymbols.class) {
                if (INSTANCE == null) INSTANCE = new LegacySymbols(Cfg.getOr("LIVE_LEGACY_FILE", DEFAULT_FILE));
            }
        }
        return INSTANCE;
    }

    /** CHI cho unit test. */
    static void resetForTest(String path) {
        synchronized (LegacySymbols.class) {
            INSTANCE = new LegacySymbols(path);
        }
    }

    /**
     * Cong DUY NHAT cho duong live hoi "symbol nay co phai vi the that cu khong".
     * Profile TAT -> {@code false} ngay lap tuc (khong cham dia) => HEAD khong doi.
     */
    public static boolean isLegacySymbol(String symbol) {
        if (!LiveProfileC3.on()) return false;
        return symbol != null && getInstance().legacy.contains(symbol);
    }

    public int size() {
        return legacy.size();
    }

    public Set<String> all() {
        return new TreeSet<>(legacy);
    }

    public String path() {
        return path;
    }

    /**
     * LUAT LEGACY (thuan tinh toan, de test): symbol co vi the THAT ma so GIAY khong giu.
     * Tap nay tu thu hep khi vi the that dong (khong con trong {@code realPositions}).
     */
    static TreeSet<String> compute(Set<String> realPositions, Set<String> paperPositions) {
        TreeSet<String> out = new TreeSet<>();
        if (realPositions == null) return out;
        for (String s : realPositions) {
            if (s == null || s.isEmpty()) continue;
            if (paperPositions != null && paperPositions.contains(s)) continue;
            out.add(s);
        }
        return out;
    }

    /**
     * Reconcile moi tick tu vi the THAT doc ve tu Binance. Ghi dia khi tap doi.
     * Luon in {@code [LEGACY] managed N: ...} de verify.sh/health doc duoc.
     */
    public void reconcile(Set<String> realPositions, Set<String> paperPositions) {
        TreeSet<String> now = compute(realPositions, paperPositions);
        boolean changed = !now.equals(new TreeSet<>(legacy));
        if (changed) {
            legacy.clear();
            legacy.addAll(now);
            save();
        }
        LOG.info("[LEGACY] managed {}: {}", now.size(), String.join(",", now));
    }

    /**
     * MO HINH thuan tinh toan cua vong chon top-K trong
     * {@code DetectEntrySignal2TradeNormal} sau patch L3: duyet pool theo thu tu, BO QUA symbol
     * legacy ma KHONG dem rank, lay {@code k} symbol dau tien con lai.
     * => legacy KHONG chiem slot cua so giay. Dung cho unit test cua luat do.
     */
    static java.util.List<String> paperCandidates(java.util.List<String> poolOrder,
                                                  Set<String> legacySet, int k) {
        java.util.List<String> out = new java.util.ArrayList<>();
        if (poolOrder == null) return out;
        for (String s : poolOrder) {
            if (legacySet != null && legacySet.contains(s)) continue;   // skip-LEGACY, khong dem rank
            if (out.size() >= k) break;
            out.add(s);
        }
        return out;
    }

    private void load() {
        File f = new File(path);
        if (!f.exists()) return;
        try {
            for (String ln : java.nio.file.Files.readAllLines(f.toPath())) {
                String s = ln.trim();
                if (s.isEmpty() || s.startsWith("#")) continue;
                legacy.add(s);
            }
            LOG.info("[LEGACY] nap lai {} symbol tu {}", legacy.size(), f.getAbsolutePath());
        } catch (Exception e) {
            LOG.error("[LEGACY] khong nap duoc {}: {}", f.getAbsolutePath(), e.getMessage());
        }
    }

    private synchronized void save() {
        try {
            File f = new File(path);
            File parent = f.getParentFile();
            if (parent != null && !parent.exists() && !parent.mkdirs()) {
                LOG.warn("[LEGACY] khong tao duoc thu muc {}", parent);
            }
            try (PrintWriter w = new PrintWriter(new FileWriter(f, false))) {
                w.println("# LEGACY symbols: vi the THAT cu, dong theo duong HEAD, so giay C3 KHONG cham.");
                w.println("# Tu sinh boi LegacySymbols.reconcile() — KHONG sua tay.");
                for (String s : new TreeSet<>(legacy)) w.println(s);
            }
        } catch (Exception e) {
            LOG.error("[LEGACY] khong ghi duoc {}: {}", path, e.getMessage());
        }
    }
}
