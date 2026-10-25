package com.binance.chuyennd.c3live.replay;

import com.binance.chuyennd.c3live.adapter.DryGateway;
import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.SymbolMeta;
import com.binance.chuyennd.c3live.book.LiveBookC3;
import com.binance.chuyennd.c3live.entry.C3LiveEntry;
import com.binance.chuyennd.c3live.exec.C3LiveOrderExecutor;
import com.binance.chuyennd.c3live.filters.SymbolRules;
import com.binance.chuyennd.c3live.guard.AccountModeGuard;
import com.binance.chuyennd.c3live.log.OrderAuditLog;
import com.binance.chuyennd.c3live.universe.SymbolUniverseLive;
import com.binance.chuyennd.c3live.universe.TradFiClassifier;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TimeZone;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.GZIPInputStream;

/**
 * [V12 C12] Replay "dry" 1 ngay live THAT: moi leg so giay ({@code [SHADOW] would-BUY} trong full.log keo tu 242) =>
 * {@link C3LiveEntry} + {@link DryGateway} (KHONG mang) => dem leg c3_live dry vs so giay, liet ke khac biet (TradFi /
 * universe / sizing / U_MAX). exchangeInfo: {@code exchange_info_pin.json} (tick/minQty/minNotional; stepSize = minQty —
 * CHUA XAC MINH) + symbol thieu trong pin dung fixture suy tu so le gia/qty cua log; TradFi = danh sach proxy
 * {@code live_low_activity_1023.csv} (CHUA XAC MINH truong TradFi that). Von dry 10 000, sizing that (managerBudget).
 *
 * <p>Chay: {@code java -cp <jar>:target/test-classes ...DryDayReplayMain <out.json> <pin.json> <tradfi.csv> <fromMs> <toMs>
 * <full.log.gz>...}
 */
public final class DryDayReplayMain {

    private static final Logger LOG = LoggerFactory.getLogger(DryDayReplayMain.class);
    static final Pattern RX = Pattern.compile(
            "\\[SHADOW\\] would-BUY BUY (\\S+) entry: (\\S+) quantity: (\\S+) time:(\\d{8} \\d\\d:\\d\\d) market level: (\\S+)");

    private DryDayReplayMain() {
    }

    static final class Leg {
        final String sym;
        final double entry;
        final double qty;
        final long ts;
        final String level;

        Leg(String sym, double entry, double qty, long ts, String level) {
            this.sym = sym;
            this.entry = entry;
            this.qty = qty;
            this.ts = ts;
            this.level = level;
        }
    }

    static int decimals(String s) {
        int i = s.indexOf('.');
        if (i < 0) return 0;
        String t = s.substring(i + 1).replaceAll("0+$", "");
        return t.length();
    }

    public static void main(String[] args) throws Exception {
        File out = new File(args[0]);
        File pin = new File(args[1]);
        File tradfi = new File(args[2]);
        long from = Long.parseLong(args[3]);
        long to = Long.parseLong(args[4]);
        SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd HH:mm");
        f.setTimeZone(TimeZone.getTimeZone("Asia/Ho_Chi_Minh"));
        Map<String, Leg> legs = new LinkedHashMap<>();
        Map<String, String[]> rawTok = new HashMap<>();
        for (int a = 5; a < args.length; a++) {
            try (BufferedReader br = new BufferedReader(new InputStreamReader(new GZIPInputStream(new FileInputStream(args[a])),
                    StandardCharsets.UTF_8))) {
                String ln;
                while ((ln = br.readLine()) != null) {
                    Matcher m = RX.matcher(ln);
                    if (!m.find()) continue;
                    long ts = f.parse(m.group(4)).getTime();
                    if (ts < from || ts >= to) continue;
                    String key = m.group(1) + "|" + ts + "|" + m.group(5);
                    if (legs.containsKey(key)) continue;
                    legs.put(key, new Leg(m.group(1), Double.parseDouble(m.group(2)), Double.parseDouble(m.group(3)), ts,
                            m.group(5)));
                    rawTok.put(m.group(1), new String[]{m.group(2), m.group(3)});
                }
            }
        }
        // exchangeInfo
        Set<String> tf = new HashSet<>();
        for (String ln : Files.readAllLines(tradfi.toPath())) {
            String s = ln.split(",")[0].trim();
            if (!s.isEmpty() && !"sym".equals(s)) tf.add(s);
        }
        boolean realDump = pin.getName().endsWith(".json.gz");
        Map<String, SymbolMeta> metas = new TreeMap<>();
        Set<String> synth = new HashSet<>();
        JsonObject root = realDump ? new JsonObject() : JsonParser.parseString(new String(Files.readAllBytes(pin.toPath()),
                StandardCharsets.UTF_8)).getAsJsonObject();
        if (realDump) {
            try (java.io.InputStream in = new GZIPInputStream(new FileInputStream(pin))) {
                java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
                byte[] buf = new byte[65536];
                int n;
                while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
                ExchangeInfo real = com.binance.chuyennd.c3live.api.ExchangeInfoParser.parse(
                        new String(bo.toByteArray(), StandardCharsets.UTF_8));
                metas.putAll(real.getSymbols());
            }
            root.add("symbols", new JsonArray());
        }
        for (JsonElement e : root.getAsJsonArray("symbols")) {
            JsonObject o = e.getAsJsonObject();
            String sym = o.get("symbol").getAsString();
            BigDecimal tick = null, minQty = null, mktMin = null, notional = new BigDecimal("5");
            for (JsonElement fa : o.getAsJsonArray("filters")) {
                JsonArray arr = fa.isJsonArray() ? fa.getAsJsonArray() : null;
                if (arr == null) continue;
                for (JsonElement fe : arr) {
                    JsonObject fo = fe.getAsJsonObject();
                    String ft = fo.get("filterType").getAsString();
                    if ("PRICE_FILTER".equals(ft) && fo.has("tickSize")) tick = new BigDecimal(fo.get("tickSize").getAsString());
                    if ("LOT_SIZE".equals(ft) && fo.has("minQty")) minQty = new BigDecimal(fo.get("minQty").getAsString());
                    if ("MARKET_LOT_SIZE".equals(ft) && fo.has("minQty")) mktMin = new BigDecimal(fo.get("minQty").getAsString());
                    if ("MIN_NOTIONAL".equals(ft) && fo.has("notional")) notional = new BigDecimal(fo.get("notional").getAsString());
                }
            }
            if (tick == null || minQty == null) continue;
            metas.put(sym, meta(sym, o.get("status").getAsString(), tick, minQty, mktMin == null ? minQty : mktMin, notional));
        }
        for (Map.Entry<String, String[]> e : rawTok.entrySet()) {
            if (metas.containsKey(e.getKey())) continue;
            BigDecimal tick = BigDecimal.ONE.scaleByPowerOfTen(-Math.max(decimals(e.getValue()[0]), 1));
            BigDecimal step = BigDecimal.ONE.scaleByPowerOfTen(-decimals(e.getValue()[1]));
            metas.put(e.getKey(), meta(e.getKey(), "TRADING", tick, step, step, new BigDecimal("5")));
            synth.add(e.getKey());
        }
        ExchangeInfo ei = new ExchangeInfo(0L, Collections.emptyList(), new ArrayList<>(metas.values()));
        // duong c3_live dry
        AtomicLong now = new AtomicLong(from);
        Map<String, BigDecimal> refs = new ConcurrentHashMap<>();
        List<String> dryLines = new ArrayList<>();
        DryGateway gw = new DryGateway(() -> ei, refs::get, new BigDecimal("10000"),
                new OrderAuditLog(OrderAuditLog.DRY_TAG, dryLines::add), now::get, null, DryGateway.DEFAULT_FEE_RATE);
        LiveBookC3 book = new LiveBookC3(null, 1.0);
        SymbolUniverseLive.Config cfg = new SymbolUniverseLive.Config(new HashMap<>(), false,
                realDump ? TradFiClassifier.defaults() : new TradFiClassifier(null, null, tf), 365L * 86_400_000L);
        SymbolUniverseLive uni = new SymbolUniverseLive(cfg, () -> ei, m -> { });
        uni.apply(ei, from);
        C3LiveOrderExecutor ex = new C3LiveOrderExecutor(gw, book, null, null, now::get, ms -> { }, 0L, 3, Runnable::run);
        C3LiveEntry entry = C3LiveEntry.builder().book(book)
                .killSwitch(new C3LiveEntry.KillSwitchView() {
                    public boolean armed() { return true; }
                    public boolean allowNewEntry(String s) { return true; }
                })
                .universe(uni).modeGuard(new AccountModeGuard(gw, m -> { })).rules(() -> new SymbolRules(ei, from))
                .capital(() -> gw.account().getTotalMarginBalance().min(new BigDecimal("10000")).doubleValue())
                .legacy(s -> false).budgetFn((m, c) -> TradeUtils.managerBudget(null, m, c, null)).legBudgetFn((b, i) -> b)
                .gridDue((fe, p, n) -> true).executor(ex).audit(new OrderAuditLog(OrderAuditLog.DRY_TAG, dryLines::add))
                .refSink((s, p) -> refs.put(s, BigDecimal.valueOf(p))).pushAllowed(() -> true).dcaGridEnabled(true)
                .sizeCapOfEquity(0.045f).build();
        Map<C3LiveEntry.Outcome, Integer> cnt = new EnumMap<>(C3LiveEntry.Outcome.class);
        List<String> diff = new ArrayList<>();
        double paperNotional = 0d, dryNotional = 0d;
        List<Leg> sorted = new ArrayList<>(legs.values());
        sorted.sort((x, y) -> Long.compare(x.ts, y.ts));
        for (Leg l : sorted) {
            now.set(l.ts + 60_000L);
            boolean dca = "DCA_LEVEL1".equals(l.level);
            C3LiveEntry.Result r = entry.onLeg(new C3LiveEntry.LegInput(l.sym, l.level, dca, l.ts, l.entry, l.entry, 1f, false),
                    now.get());
            cnt.merge(r.outcome, 1, Integer::sum);
            paperNotional += l.entry * l.qty;
            if (r.outcome == C3LiveEntry.Outcome.SUBMITTED) {
                dryNotional += r.qty.doubleValue() * l.entry;
            } else {
                diff.add(l.sym + " " + l.level + " " + r.outcome + " " + r.detail.replace('"', '\''));
            }
        }
        int dryOrderLines = 0;
        for (String s : dryLines) if (s.contains("[LIVE-DRY]") && s.contains("FILLED")) dryOrderLines++;
        StringBuilder sb = new StringBuilder();
        sb.append("{\"exchange_info\":\"").append(pin.getName()).append(realDump ? " (dump THAT)" : " (pin+danh sach TradFi proxy)")
                .append("\",\"from_ms\":").append(from).append(",\"to_ms\":").append(to).append(",\"paper_legs\":").append(sorted.size())
                .append(",\"dry_outcomes\":\"").append(cnt).append("\",\"dry_submitted\":")
                .append(cnt.getOrDefault(C3LiveEntry.Outcome.SUBMITTED, 0)).append(",\"dry_filled_lines\":").append(dryOrderLines)
                .append(",\"paper_notional\":").append(String.format(java.util.Locale.ROOT, "%.2f", paperNotional))
                .append(",\"dry_notional\":").append(String.format(java.util.Locale.ROOT, "%.2f", dryNotional))
                .append(",\"synthetic_meta\":\"").append(new TreeMap<>(Collections.singletonMap("n", synth.size())))
                .append(' ').append(new java.util.TreeSet<>(synth)).append("\",\"tradfi_list_n\":").append(tf.size())
                .append(",\"diff\":[");
        for (int i = 0; i < diff.size(); i++) sb.append(i > 0 ? "," : "").append('"').append(diff.get(i)).append('"');
        sb.append("]}\n");
        Files.write(out.toPath(), sb.toString().getBytes(StandardCharsets.UTF_8));
        LOG.warn("[DRY-DAY] {}", sb.toString().trim());
    }

    static SymbolMeta meta(String sym, String status, BigDecimal tick, BigDecimal step, BigDecimal mktStep, BigDecimal notional) {
        return SymbolMeta.builder(sym).pair(sym).status(status).contractType("PERPETUAL").baseAsset(sym.replace("USDT", ""))
                .quoteAsset("USDT").marginAsset("USDT").underlyingType("COIN").underlyingSubType(Collections.emptyList())
                .onboardDate(1_500_000_000_000L).deliveryDate(4_133_404_800_000L).tickSize(tick).minPrice(tick)
                .maxPrice(new BigDecimal("10000000")).stepSize(step).minQty(step).maxQty(new BigDecimal("100000000"))
                .marketStepSize(mktStep).marketMinQty(mktStep).marketMaxQty(new BigDecimal("100000000")).minNotional(notional)
                .build();
    }
}
