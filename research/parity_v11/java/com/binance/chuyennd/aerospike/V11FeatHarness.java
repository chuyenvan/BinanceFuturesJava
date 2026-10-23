package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.features.export.MarketDataInlineGenerator;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;

import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.PrintWriter;
import java.lang.reflect.Field;
import java.util.*;
import java.util.zip.GZIPOutputStream;

/**
 * AUDIT-ONLY v1.1 (docs/plan/V11_COLLECTOR_SETTLE.md): tai lap feature gate 33 cot tren du lieu 1m DA SETTLE (Aerospike 242,
 * CHI DOC) theo 3 duong:
 *  LIVE = duong live hien tai (seed 2000' x2 luot, LiveTickerWindow 1000', loc died + isTickerAvailable, last-ticker, rate tu window)
 *  NEW  = duong sua v1.1 (seed replay tung phut + getTopCoin, snapshot phut M day du, MarketDataInlineGenerator)
 *  BT   = ExportGateDataset.replayToCsv (warmup 48h, snapshot phut day du, MarketDataInlineGenerator)
 * args: mode restartMs firstMinute lastMinute out.csv.gz
 * HARNESS_OFFLINE=1 (research/parity_v11, PREREG_PARITY_V11_WINDOW §1): chi doc cache file cuc bo + provider file,
 * chan cung Aerospike/mang (OfflineGuard + stub AerospikeClient). Thieu cache => dung, KHONG doc Aerospike.
 */
public class V11FeatHarness {
    private static final org.slf4j.Logger LOG = org.slf4j.LoggerFactory.getLogger(V11FeatHarness.class);
    static final long MIN = 60_000L;
    static final String[] FEATS = {"momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H",
            "momentumAcceleration", "trendStrengthETH", "trendConsistency", "volatility1M", "volatility15M", "volatility1H",
            "volatility24H", "volatilityTermStructure", "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown",
            "marketBreadthStrength", "btcDominance", "rsi14", "volumeSpike", "distMA20", "fundingRateRaw",
            "fundingRateAvg24H", "fundingRateTrend", "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
            "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike"};
    static final TreeMap<Long, Map<String, KlineObjectSimple>> DATA = new TreeMap<>();

    static KlineObjectSimple cp(KlineObjectSimple k) {
        KlineObjectSimple c = new KlineObjectSimple();
        c.startTime = k.startTime;
        c.priceOpen = k.priceOpen;
        c.maxPrice = k.maxPrice;
        c.minPrice = k.minPrice;
        c.priceClose = k.priceClose;
        c.totalUsdt = k.totalUsdt;
        return c;
    }

    static Map<String, KlineObjectSimple> cpMap(Map<String, KlineObjectSimple> m) {
        Map<String, KlineObjectSimple> o = new HashMap<>();
        if (m != null) for (Map.Entry<String, KlineObjectSimple> e : m.entrySet()) o.put(e.getKey(), cp(e.getValue()));
        return o;
    }

    @SuppressWarnings("unchecked")
    static void load(long from, long to) throws Exception {
        java.io.File cf = new java.io.File("cache_" + from + "_" + to + ".ser.gz");
        if (cf.exists()) {
            try (java.io.ObjectInputStream in = new java.io.ObjectInputStream(new java.util.zip.GZIPInputStream(new java.io.FileInputStream(cf)))) {
                DATA.putAll((TreeMap<Long, Map<String, KlineObjectSimple>>) in.readObject());
            }
            LOG.info("{}", "cache minutes=" + DATA.size());
            return;
        }
        if (OfflineGuard.enabled()) throw new IllegalStateException("HARNESS_OFFLINE: thieu cache " + cf.getAbsolutePath());
        long t = from;
        while (t <= to) {
            int n = (int) Math.min(240, (to - t) / MIN + 1);
            TreeMap<Long, Map<String, KlineObjectSimple>> r = DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(t, n);
            DATA.putAll(r);
            t += n * MIN;
        }
        if (DATA.isEmpty()) throw new IllegalStateException("khong doc duoc phut nao tu Aerospike 242");
        try (java.io.ObjectOutputStream o = new java.io.ObjectOutputStream(new GZIPOutputStream(new FileOutputStream(cf)))) { o.writeObject(DATA); }
        LOG.info("{}", "loaded minutes=" + DATA.size() + " " + DATA.firstKey() + ".." + DATA.lastKey());
    }

    public static void main(String[] a) throws Exception {
        Field g = Live242WriteGuard.class.getDeclaredField("decided");
        g.setAccessible(true);
        g.set(null, Boolean.FALSE);   // CHI DOC: chan moi ghi 242 (mapper, ai_pred...)
        OfflineGuard.install();       // HARNESS_OFFLINE=1: provider file + chan mang (khong bat => nhu cu)
        try {
            LOG.info("cluster={}", Configs.AEROSPIKE_READ_CLUSTER);
        } catch (Throwable t) {
            LOG.error("Configs init loi", t);
            System.exit(3);
        }
        String mode = a[0];
        long restart = Long.parseLong(a[1]);
        long first = Long.parseLong(a[2]);
        long last = Long.parseLong(a[3]);
        long rFloor = restart - restart % MIN;
        long seedFrom = rFloor - 2000 * MIN;
        long btFrom = first - 48 * 60 * MIN;
        load(Math.min(seedFrom, btFrom) - 1000 * MIN, last);
        LOG.info("{}", "died=" + Constants.diedSymbol.size() + " N15=" + Configs.NUMBER_TICKER_CAL_RATE_CHANGE
                + " BD_FRACTION=" + Configs.BD_FRACTION + " STATIC_RANK=" + Configs.WFO_STATIC_RANK);
        HistoryManager hm = HistoryManager.getInstance();
        ComprehensiveMarketFeatureExtractor ex = new ComprehensiveMarketFeatureExtractor();
        CoinRankManager cr = CoinRankManager.getInstance();
        String hd = System.getenv("HARNESS_MD_DIED");
        MarketDataInlineGenerator md = new MarketDataInlineGenerator(diedOf(hd == null ? "BTCDOM,USDC" : hd));
        java.lang.reflect.Field uf = sun.misc.Unsafe.class.getDeclaredField("theUnsafe");
        uf.setAccessible(true);
        FOM = (com.binance.chuyennd.ai_ml.onnx.funding.FundingOnnxInferenceManager) ((sun.misc.Unsafe) uf.get(null))
                .allocateInstance(com.binance.chuyennd.ai_ml.onnx.funding.FundingOnnxInferenceManager.class);
        FW = new PrintWriter(new OutputStreamWriter(new GZIPOutputStream(new FileOutputStream(a[4].replace("out_", "fund_")))));
        FW.print("min,symbol,cand");
        for (int i = 0; i < 45; i++) FW.print(",f" + i);
        FW.println();
        try (PrintWriter w = new PrintWriter(new OutputStreamWriter(new GZIPOutputStream(new FileOutputStream(a[4]))))) {
            w.print("min,nsym,nbasket,basket_hash,r_down,r_up,r_down15");
            for (String f : FEATS) w.print("," + f);
            w.println();
            if ("BT".equals(mode)) {
                for (long ts = btFrom; ts <= last; ts += MIN) {
                    Map<String, KlineObjectSimple> raw = DATA.get(ts);
                    if (raw == null) continue;
                    Map<String, KlineObjectSimple> snap = cpMap(raw);
                    MarketDataObject rate = md.update(snap);
                    hm.updateHistory(snap);
                    cr.getTopCoin(ts);
                    if (ts < first) continue;
                    MarketFeatures f = ex.extractAllFeatures(ts, snap, rate);
                    row(w, ts, snap.size(), cr.getTopCoin(ts), rate, f);
                    fund(ts, null, snap, snap, rate, true);
                }
            } else if ("NEW".equals(mode)) {
                for (long ts = seedFrom; ts < first; ts += MIN) {
                    Map<String, KlineObjectSimple> raw = DATA.get(ts);
                    if (raw == null) continue;
                    Map<String, KlineObjectSimple> snap = cpMap(raw);
                    md.update(snap);
                    hm.updateHistory(snap);
                    cr.getTopCoin(ts);
                }
                for (long ts = first; ts <= last; ts += MIN) {
                    Map<String, KlineObjectSimple> raw = DATA.get(ts);
                    if (raw == null) continue;
                    Map<String, KlineObjectSimple> snap = cpMap(raw);
                    MarketDataObject rate = md.update(snap);
                    MarketFeatures f = ex.extractAllFeatures(ts, snap, rate);
                    row(w, ts, snap.size(), cr.getTopCoin(ts), rate, f);
                }
            } else if ("NEW2".equals(mode)) {   // duong PROD v1.1: LiveFeaturePipeline + LiveTickerWindow(inPlace, await)
                com.binance.chuyennd.ai_ml.features.export.entry.LiveFeaturePipeline p =
                        com.binance.chuyennd.ai_ml.features.export.entry.LiveFeaturePipeline.forProd(ex);
                long off = Math.floorMod(restart, MIN);
                TreeMap<Long, Map<String, KlineObjectSimple>> seed = new TreeMap<>();
                for (int i = 0; i < 2000; i++) {
                    long t = seedFrom + i * MIN;
                    if (!DATA.containsKey(t)) continue;
                    Map<String, KlineObjectSimple> m = cpMap(DATA.get(t));
                    for (KlineObjectSimple k : m.values()) k.startTime = t + off;   // key lech ms nhu live
                    seed.put(t + off, m);
                }
                p.seed(seed);
                final LiveTickerWindow win = new LiveTickerWindow((fromMinute, count) -> {
                    TreeMap<Long, Map<String, KlineObjectSimple>> r = new TreeMap<>();
                    for (int i = 0; i < count; i++) {
                        long t = fromMinute + i * MIN;
                        Map<String, KlineObjectSimple> m = DATA.get(t);
                        if (m != null) r.put(t, cpMap(m));
                    }
                    return r;
                }, 3);
                win.setInPlaceReread(true);
                com.binance.chuyennd.ai_ml.features.export.entry.LiveFeaturePipeline.MinuteSource src =
                        new com.binance.chuyennd.ai_ml.features.export.entry.LiveFeaturePipeline.MinuteSource() {
                            public Map<String, KlineObjectSimple> snapshot(long minute) {
                                return win.minuteSnapshot(minute);
                            }

                            public com.binance.chuyennd.ai_ml.features.export.entry.LiveFeaturePipeline.SettleInfo await(long minute, int expected) {
                                long[] r = win.awaitMinuteComplete(minute, expected, 3000L, 250L);
                                return new com.binance.chuyennd.ai_ml.features.export.entry.LiveFeaturePipeline.SettleInfo(
                                        (int) r[0], expected, r[2], (int) r[1]);
                            }
                        };
                for (long ts = first; ts <= last; ts += MIN) {
                    Map<String, List<KlineObjectSimple>> s2l = win.read(ts + MIN + 6000, 1000);
                    com.binance.chuyennd.ai_ml.features.export.entry.LiveFeaturePipeline.Result r =
                            p.onTick(src, win.lastEndMinute(), null);
                    if (r == null || r.features == null) continue;
                    row(w, ts, r.nSym, cr.getTopCoin(ts), r.featRate, r.features);
                    Map<String, KlineObjectSimple> fin = new HashMap<>();
                    for (Map.Entry<String, List<KlineObjectSimple>> e : s2l.entrySet()) {
                        if (Constants.diedSymbol.contains(e.getKey())) continue;
                        KlineObjectSimple k = e.getValue().get(e.getValue().size() - 1);
                        if (Utils.isTickerAvailable(k)) fin.put(e.getKey(), k);
                    }
                    fund(ts, fin.keySet(), fin, r.snapshot, r.featRate, true);
                }
            } else {   // LIVE (duong hien tai, DetectEntrySignal2TradeNormal.initData + checkMarketLevelChange2Trade)
                TreeMap<Long, Map<String, KlineObjectSimple>> seed = new TreeMap<>();
                for (int i = 0; i < 2000; i++) {
                    long t = seedFrom + i * MIN;
                    if (DATA.containsKey(t)) seed.put(t, cpMap(DATA.get(t)));
                }
                ex.initDataFromTickerMap(seed);
                for (Map<String, KlineObjectSimple> m : seed.values()) hm.updateHistory(m);  // fundingExtractor luot 2
                LiveTickerWindow win = new LiveTickerWindow((fromMinute, count) -> {
                    TreeMap<Long, Map<String, KlineObjectSimple>> r = new TreeMap<>();
                    for (int i = 0; i < count; i++) {
                        long t = fromMinute + i * MIN;
                        Map<String, KlineObjectSimple> m = DATA.get(t);
                        if (m != null) r.put(t, cpMap(m));
                    }
                    return r;
                }, 3);
                for (long ts = first; ts <= last; ts += MIN) {
                    Map<String, List<KlineObjectSimple>> s2l = win.read(ts + MIN + 6000, 1000);
                    Map<String, KlineObjectSimple> fin = new HashMap<>();
                    TreeMap<Float, String> d15 = new TreeMap<>(), u15 = new TreeMap<>(), d = new TreeMap<>(), u = new TreeMap<>();
                    List<KlineObjectSimple> btcs = s2l.get(Constants.SYMBOL_PAIR_BTC);
                    KlineObjectSimple btc = btcs.get(btcs.size() - 1);
                    Float btcRate = Utils.rateOf2Double(btc.priceClose, btc.priceOpen).floatValue();
                    long time = btc.startTime.longValue();
                    for (Map.Entry<String, List<KlineObjectSimple>> e : s2l.entrySet()) {
                        String s = e.getKey();
                        if (Constants.diedSymbol.contains(s)) continue;
                        List<KlineObjectSimple> tk = e.getValue();
                        KlineObjectSimple k = tk.get(tk.size() - 1);
                        if (!Utils.isTickerAvailable(k)) continue;
                        fin.put(s, k);
                        Float rc = Utils.rateOf2Double(k.priceClose, k.priceOpen).floatValue();
                        if (btcRate > -0.004 && rc < -0.15) continue;
                        if (rc > 0.3) continue;
                        d.put(rc, s);
                        u.put(-rc, s);
                        Float pMax = null, pMin = null;
                        for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
                            int idx = tk.size() - i - 1;
                            if (idx >= 0) {
                                KlineObjectSimple kl = tk.get(idx);
                                if (pMax == null || pMax < kl.maxPrice) pMax = kl.maxPrice;
                                if (pMin == null || pMin > kl.minPrice) pMin = kl.minPrice;
                            }
                        }
                        d15.put(Utils.rateOf2Double(tk.get(tk.size() - 1).priceClose, pMax).floatValue(), s);
                        u15.put(-Utils.rateOf2Double(tk.get(tk.size() - 1).priceClose, pMin).floatValue(), s);
                    }
                    Float rd = MarketBigChangeDetector.calRateChangeAvg(d, 100);
                    Float ru = -MarketBigChangeDetector.calRateChangeAvg(u, 100);
                    Float rd15 = MarketBigChangeDetector.calRateChangeAvg(d15, 100);
                    MarketDataObject rate = new MarketDataObject(rd, ru, rd15);
                    hm.updateHistory(fin);   // fundingExtractor.updateMarketHistory(symbol2FinalTicker)
                    MarketFeatures f = ex.extractAllFeatures(time, new HashMap<>(fin), rate);
                    row(w, ts, fin.size(), cr.getTopCoin(time), rate, f);
                    fund(time, fin.keySet(), fin, fin, rate, false);
                }
            }
        }
        FW.close();
        OfflineGuard.finish();
        LOG.info("{}", "done " + mode);
        System.exit(0);
    }

    static PrintWriter FW;
    static com.binance.chuyennd.ai_ml.onnx.funding.FundingOnnxInferenceManager FOM;
    static final com.binance.chuyennd.ai_ml.features.export.funding.FundingDataCollectionManager.FundingFeatureExtractorV2 FEX =
            new com.binance.chuyennd.ai_ml.features.export.funding.FundingDataCollectionManager.FundingFeatureExtractorV2();

    static java.util.Set<String> diedOf(String v) {
        java.util.Set<String> o = new java.util.HashSet<>();
        for (String x : v.split(",")) { String t = x.trim(); if (!t.isEmpty()) o.add(t.contains("USDT") ? t : t + "USDT"); }
        return o;
    }

    static com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures fx(long time, String sym,
            KlineObjectSimple tk, Map<String, KlineObjectSimple> snap, MarketDataObject rate, List<String> basket) {
        com.binance.chuyennd.research.OrderTargetInfoTest d = new com.binance.chuyennd.research.OrderTargetInfoTest(
                com.binance.chuyennd.trading.OrderTargetStatus.REQUEST, tk.priceClose, null, 1.0f,
                Configs.LEVERAGE_ORDER, sym, time, time, com.binance.client.model.enums.OrderSide.BUY);
        d.lastEntry = tk.priceClose;
        return FEX.extractFeatures(time, d, snap, rate, basket);
    }

    /**
     * Funding-45: cands = ung vien live (null = Tool1: chi coin qua filter); csSnap = snapshot cho selectCoins;
     * fullPop = xep hang CS tren toan bo coin qua filter (Tool1 / fix V11) hay chi cands (legacy live).
     */
    static void fund(long time, java.util.Collection<String> cands, Map<String, KlineObjectSimple> tickers,
                     Map<String, KlineObjectSimple> fsnap, MarketDataObject rate, boolean fullPop) {
        List<String> basket = CoinRankManager.getInstance().getTopCoin(time);
        java.util.Set<String> pop = com.binance.chuyennd.ai_ml.features.export.funding.EntrySignalFilter.selectCoins(
                fsnap, com.binance.chuyennd.ai_ml.features.export.HistoryManager.getInstance());
        Map<String, com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures> f = new TreeMap<>();
        java.util.Collection<String> calc = cands == null ? pop : cands;
        for (String sym : calc) {
            KlineObjectSimple tk = tickers.get(sym);
            if (tk == null || !Utils.isTickerAvailable(tk)) continue;
            com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures x = fx(time, sym, tk, fsnap, rate, basket);
            if (x != null) f.put(sym, x);
        }
        List<com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures> cs = new ArrayList<>();
        for (String sym : pop) if (f.containsKey(sym)) cs.add(f.get(sym));
        Map<String, com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures> extra = new TreeMap<>();
        if (fullPop) {
            for (String sym : pop) {
                if (f.containsKey(sym)) continue;
                KlineObjectSimple tk = fsnap.get(sym);
                if (tk == null || !Utils.isTickerAvailable(tk)) continue;
                com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures x = fx(time, sym, tk, fsnap, rate, basket);
                if (x != null) { cs.add(x); extra.put(sym, x); }
            }
        }
        com.binance.chuyennd.ai_ml.features.export.funding.FundingCrossSectional.apply(cs);
        for (String sym : pop) {
            com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures x = f.containsKey(sym) ? f.get(sym) : extra.get(sym);
            if (x == null) continue;
            float[] a = FOM.extractFeaturesToArray(x);
            StringBuilder sb = new StringBuilder();
            sb.append(time).append(',').append(sym).append(',').append(f.containsKey(sym) ? 1 : 0);
            for (float v : a) sb.append(',').append(Float.toString(v));
            FW.println(sb);
        }
    }

    static void row(PrintWriter w, long ts, int nsym, List<String> basket, MarketDataObject r, MarketFeatures f) throws Exception {
        List<String> b = new ArrayList<>(basket);
        Collections.sort(b);
        StringBuilder sb = new StringBuilder();
        sb.append(ts).append(',').append(nsym).append(',').append(b.size()).append(',').append(Integer.toHexString(b.hashCode()));
        sb.append(',').append(r == null ? "" : String.valueOf(r.rateDownAvg)).append(',').append(r == null ? "" : String.valueOf(r.rateUpAvg))
                .append(',').append(r == null ? "" : String.valueOf(r.rateDown15MAvg));
        for (String n : FEATS) {
            Field fl = MarketFeatures.class.getField(n);
            sb.append(',').append(String.valueOf(fl.get(f)));
        }
        w.println(sb);
    }
}
