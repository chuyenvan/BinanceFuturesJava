package com.binance.chuyennd.tradecore.selector;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.SymbolMeta;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.TreeMap;
import java.util.zip.GZIPInputStream;

/**
 * [V12 C6] Replay exit tren du lieu DEV THAT (ngoai CI): chan = SELRANK cua 1 seed printDone X14, gia = close 1m
 * ({@code ~/vz_e1/raw}), co X14 = {@code SIM_LOSER_TS_EXT_DAYS} cua chinh lan sim do. Chay SONG SONG so giay
 * {@link ShadowBookC3} va duong that ({@link ExitParityEngine}) => so quyet dinh arm/SL/time-stop/X14.
 *
 * <p>Chay: {@code SHADOW_C3_DIR=<tmp> java -cp <jar>:target/test-classes ...ExitReplayDevMain <dataDir> <prof_run.properties>
 * <out.json> <YYYYMMDD>...}. tick size = 4 chu so co nghia theo gia leg dau (fixture, CHUA XAC MINH voi san that).
 */
public final class ExitReplayDevMain {

    private static final Logger LOG = LoggerFactory.getLogger(ExitReplayDevMain.class);
    static final long MIN = 60_000L;
    static final long DAY = 86_400_000L;

    private ExitReplayDevMain() {
    }

    static BigDecimal tickFor(double px) {
        int e = (int) Math.floor(Math.log10(px)) - 4;
        return BigDecimal.ONE.scaleByPowerOfTen(e);
    }

    static SymbolMeta meta(String sym, double px) {
        BigDecimal tick = tickFor(px);
        return SymbolMeta.builder(sym).pair(sym).status("TRADING").contractType("PERPETUAL").baseAsset(sym.replace("USDT", ""))
                .quoteAsset("USDT").marginAsset("USDT").underlyingType("COIN").underlyingSubType(Collections.emptyList())
                .onboardDate(1_500_000_000_000L).deliveryDate(4_133_404_800_000L).tickSize(tick).minPrice(tick)
                .maxPrice(new BigDecimal("10000000")).stepSize(new BigDecimal("0.001")).minQty(new BigDecimal("0.001"))
                .maxQty(new BigDecimal("100000000")).marketStepSize(new BigDecimal("0.001")).marketMinQty(new BigDecimal("0.001"))
                .marketMaxQty(new BigDecimal("100000000")).minNotional(new BigDecimal("5")).build();
    }

    public static void main(String[] args) throws Exception {
        File data = new File(args[0]);
        Properties prof = new Properties();
        try (FileInputStream in = new FileInputStream(args[1])) {
            prof.load(in);
        }
        File out = new File(args[2]);
        Configs.properties.putIfAbsent("CAPITAL_START", "35000");
        String dir = System.getenv("SHADOW_C3_DIR");
        if (dir == null || dir.isEmpty()) throw new IllegalStateException("can SHADOW_C3_DIR (thu muc tam cho so giay)");
        DateTimeFormatter f = DateTimeFormatter.ofPattern("yyyyMMdd");
        java.util.Set<Long> onDays = new java.util.HashSet<>();
        for (String r : prof.getProperty("SIM_LOSER_TS_EXT_DAYS", "").split(",")) {
            if (r.trim().isEmpty()) continue;
            String[] p = r.trim().split("-");
            for (LocalDate d = LocalDate.parse(p[0], f); !d.isAfter(LocalDate.parse(p[1], f)); d = d.plusDays(1)) {
                onDays.add(d.toEpochDay());
            }
        }
        StringBuilder json = new StringBuilder("[");
        for (int a = 3; a < args.length; a++) {
            String d = args[a];
            new File(dir, "open_positions.csv").delete();
            new File(dir, "ledger.csv").delete();
            new File(dir, "legs.csv").delete();
            // legs
            List<String[]> legs = new ArrayList<>();
            for (String ln : Files.readAllLines(new File(data, "legs_" + d + ".csv").toPath())) {
                if (ln.startsWith("ts_ms")) continue;
                legs.add(ln.split(","));
            }
            // gia
            TreeMap<Long, Map<String, Float>> px = new TreeMap<>();
            try (BufferedReader br = new BufferedReader(new InputStreamReader(new GZIPInputStream(
                    new FileInputStream(new File(data, "px_" + d + ".csv.gz"))), StandardCharsets.UTF_8))) {
                String ln;
                while ((ln = br.readLine()) != null) {
                    if (ln.startsWith("ts_ms")) continue;
                    String[] p = ln.split(",");
                    long ts = Long.parseLong(p[0]);
                    if (ts % MIN != 0) throw new IllegalStateException("ts khong tron phut " + ts);
                    px.computeIfAbsent(ts, k -> new HashMap<>()).put(p[1], Float.parseFloat(p[2]));
                }
            }
            // exchangeInfo fixture theo gia leg dau
            Map<String, SymbolMeta> metas = new LinkedHashMap<>();
            for (String[] l : legs) {
                Map<String, Float> m = px.get(Long.parseLong(l[0]));
                Float c = m == null ? null : m.get(l[1]);
                if (c != null && !metas.containsKey(l[1])) metas.put(l[1], meta(l[1], c));
            }
            ExchangeInfo ei = new ExchangeInfo(0L, Collections.emptyList(), new ArrayList<>(metas.values()));
            // co X14 (TsMktExt test instance — dung cho CA HAI so)
            TsMktExt.enabledForTest = true;
            TsMktExt.legacyCheck = s -> false;
            TsMktExt x = new TsMktExt(null, null, 0L, 0L);
            long d0 = Math.floorDiv(px.firstKey(), DAY) - 2;
            for (long day = d0; day <= Math.floorDiv(px.lastKey(), DAY) + 2; day++) {
                x.setFlagForTest(day, onDays.contains(day) ? AltEwIndex.State.ON : AltEwIndex.State.OFF);
            }
            TsMktExt.setInstanceForTest(x);
            ExitParityEngine e = new ExitParityEngine(ei, px.firstKey(), TsMktExt::deferTimeStop);
            Map<Long, List<String[]>> legAt = new HashMap<>();
            for (String[] l : legs) legAt.computeIfAbsent(Long.parseLong(l[0]), k -> new ArrayList<>()).add(l);
            int nLeg = 0, nSkip = 0;
            for (Map.Entry<Long, Map<String, Float>> en : px.entrySet()) {
                long ts = en.getKey();
                List<String[]> ls = legAt.get(ts);
                if (ls != null) {
                    for (String[] l : ls) {
                        Float c = en.getValue().get(l[1]);
                        if (c == null || !(c > 0f) || !metas.containsKey(l[1])) {
                            nSkip++;
                            continue;
                        }
                        e.leg(l[1], ts, c, (float) (100.0 / c), Integer.parseInt(l[2]), Float.parseFloat(l[3]));
                        nLeg++;
                    }
                }
                e.minute(ts, en.getValue());
            }
            ExitParityEngine.Compare cmp = e.compare();
            int openP = e.paper.openCount(), openL = e.book.openCount();
            int openStateDiff = 0;
            for (String s : e.paper.openSymbols()) {
                ShadowBookC3.Cluster pc = e.paper.cluster(s);
                java.util.Optional<com.binance.chuyennd.c3live.book.LiveBookC3.ClusterView> lc = e.book.cluster(s);
                Float psl = pc.priceSL;
                float lsl = lc.isPresent() ? lc.get().priceSL : Float.NaN;
                boolean same = lc.isPresent() && (psl == null ? Float.isNaN(lsl) : Float.floatToIntBits(psl) == Float.floatToIntBits(lsl))
                        && Float.floatToIntBits(pc.peakRate) == Float.floatToIntBits(lc.get().peakRate);
                if (!same) openStateDiff++;
            }
            String line = String.format(java.util.Locale.ROOT,
                    "{\"date\":\"%s\",\"legs\":%d,\"legs_skipped\":%d,\"minutes\":%d,\"symbols\":%d,\"decision_events\":%d,"
                            + "\"decision_mismatch_symbols\":%d,\"arms\":%d,\"sl_moves\":%d,\"time_stops\":%d,\"defers\":%d,"
                            + "\"trail_exit_both\":%d,\"trail_exit_same_minute\":%d,\"trail_exit_later\":%d,"
                            + "\"trail_exit_only_paper\":%d,\"trail_exit_only_live\":%d,\"mean_exit_px_diff_rel\":%.6g,"
                            + "\"open_end_paper\":%d,\"open_end_live\":%d,\"open_state_diff\":%d,\"mismatches\":%s}",
                    d, nLeg, nSkip, px.size(), cmp.symbols, cmp.decisionEvents, cmp.decisionMismatch, cmp.arms, cmp.slMoves,
                    cmp.timeStops, cmp.defers, cmp.trailExitBoth, cmp.trailExitSameMinute, cmp.trailExitLater,
                    cmp.trailExitOnlyPaper, cmp.trailExitOnlyLive,
                    cmp.trailExitBoth == 0 ? 0d : cmp.sumExitPxDiffRel / cmp.trailExitBoth, openP, openL, openStateDiff,
                    toJsonArr(cmp.mismatches));
            LOG.warn("[EXIT-REPLAY-DEV] {}", line);
            json.append(a > 3 ? ",\n" : "\n").append(line);
            TsMktExt.setInstanceForTest(null);
        }
        json.append("\n]\n");
        Files.write(out.toPath(), json.toString().getBytes(StandardCharsets.UTF_8));
    }

    private static String toJsonArr(List<String> l) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < l.size() && i < 50; i++) {
            if (i > 0) sb.append(',');
            sb.append('"').append(l.get(i).replace("\\", "/").replace("\"", "'")).append('"');
        }
        return sb.append(']').toString();
    }
}
