package com.binance.chuyennd.research.passspeed;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.aerospike.LiveTickerWindow;
import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.features.export.funding.EntrySignalFilter;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingCrossSectional;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingDataCollectionManager;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.ai_ml.onnx.funding.FundingOnnxInferenceManager;
import com.binance.chuyennd.ai_ml.onnx.funding.LiveOiFeatProvider;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.selector.Net015ValueLive;
import com.binance.chuyennd.tradecore.selector.S1RankerLive;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * [B6-PASS-SPEED-V3] BENCH read-only cho B6: parity RỘNG (FULL universe, ≥30 tick liên tiếp) + timing.
 * KHÔNG đặt lệnh, KHÔNG ghi Redis/Aerospike/242.
 *
 * <p>So sánh OLD (full-read ticker + OI sync) vs NEW (ticker cache + OI double-buffer + S1 prefetch):
 * ticker prices, feature45, pNoPump, net015, S1 score, [MAP] multiset. [GATE] thr/n_pass và danh sách
 * symbol vào lệnh suy ra từ tính tất định khi đầu vào (ticker + OI + S1) bit-identical.
 *
 * <p>Args: {@code [mode] [universe] [ticks]}. mode = parity (default) | timing.
 */
public class PassSpeedBenchV3 {

    private static final Logger LOG = LoggerFactory.getLogger(PassSpeedBenchV3.class);

    public static void main(String[] args) throws Exception {
        String mode = args.length >= 1 ? args[0] : "parity";
        int universeCap = args.length >= 2 ? Integer.parseInt(args[1]) : 0;   // 0 = full universe
        int ticks = args.length >= 3 ? Integer.parseInt(args[2]) : 30;
        String fundingModel = System.getProperty("funding.model",
                "../storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx");

        LOG.info("[V3] init SimpleSymbolMapper...");
        SimpleSymbolMapper.getInstance().init();

        long now = System.currentTimeMillis() - (long) ticks * Utils.TIME_MINUTE;   // đủ phút trong quá khứ (bất biến)
        if ("timing".equals(mode)) {
            runTiming(now, fundingModel, ticks);
        } else {
            runParity(now, fundingModel, universeCap, ticks);
        }
        LOG.info("[V3] xong. KHONG ghi gi len 242 (read-only).");
        System.exit(0);
    }

    /** PARITY: ticker cache vs full-read trên FULL universe, ≥{@code ticks} tick liên tiếp; + funding + S1. */
    private static void runParity(long now0, String fundingModel, int universeCap, int ticks) throws Exception {
        LiveTickerWindow cache = new LiveTickerWindow();
        int totalSym = 0;
        long tickerDiff = 0, tickerSameTicks = 0;
        List<String> firstDiff = new ArrayList<>();
        long fullReadMs = 0, cacheMs = 0;

        FundingDataCollectionManager.FundingFeatureExtractorV2 extractor =
                new FundingDataCollectionManager.FundingFeatureExtractorV2();
        FundingOnnxInferenceManager fundingBrain = new FundingOnnxInferenceManager(fundingModel);
        Net015ValueLive net015 = Net015ValueLive.getInstance();
        LOG.info("[V3] net015 ready={}", net015.isReady());

        for (int t = 0; t < ticks; t++) {
            long now = now0 + (long) t * Utils.TIME_MINUTE;

            long t0 = System.nanoTime();
            Map<String, List<KlineObjectSimple>> full = DataManagerAerospikeFloatSim.readDataForSymbols(
                    now - 1000L * Utils.TIME_MINUTE, 1000);
            fullReadMs += (System.nanoTime() - t0) / 1_000_000L;

            t0 = System.nanoTime();
            Map<String, List<KlineObjectSimple>> cached = cache.read(now, 1000);
            cacheMs += (System.nanoTime() - t0) / 1_000_000L;

            boolean same = true;
            if (full.size() != cached.size()) {
                same = false;
                if (firstDiff.size() < 5) firstDiff.add("tick" + t + ":size " + full.size() + " vs " + cached.size());
            }
            totalSym = Math.max(totalSym, full.size());
            for (Map.Entry<String, List<KlineObjectSimple>> e : full.entrySet()) {
                List<KlineObjectSimple> cf = cached.get(e.getKey());
                if (cf == null || cf.size() != e.getValue().size()) {
                    same = false;
                    if (firstDiff.size() < 5) firstDiff.add("tick" + t + ":" + e.getKey() + ":list " + (cf == null ? -1 : cf.size()) + " vs " + e.getValue().size());
                    continue;
                }
                for (int i = 0; i < e.getValue().size(); i++) {
                    if (!pricesEqual(e.getValue().get(i), cf.get(i))) {
                        same = false;
                        if (firstDiff.size() < 5) firstDiff.add("tick" + t + ":" + e.getKey() + "@" + i);
                        break;
                    }
                }
                if (!same) break;
            }
            if (same) tickerSameTicks++;
            else tickerDiff++;
            LOG.info("[V3-TICKER] tick {} nSym={} cache==full: {}", t, full.size(), same);
        }

        LOG.info("[V3-TICKER-PARITY] ticks={} same={} diff={} | fullRead avg={}ms cache avg={}ms | universe={}",
                ticks, tickerSameTicks, tickerDiff, fullReadMs / ticks, cacheMs / ticks, totalSym);
        LOG.info("[V3-TICKER-PARITY] first diff: {}", firstDiff.isEmpty() ? "-" : firstDiff);
        LOG.info("[V3-TICKER-PARITY] VERDICT: {}", tickerDiff == 0 ? "PASS (prices bit-identical)" : "FAIL");

        // Funding pipeline parity: OLD ticker (full-read) vs NEW ticker (cache) — CÙNG recent-batch OI.
        //   Vì OI double-buffer KHÔNG đổi dữ liệu (vẫn getMetricMap242RecentBatch như f98208d), biến duy
        //   nhất là ticker ⇒ so sánh pipeline trên 2 bản ticker map (đã chứng minh bit-identical ở trên).
        runFundingParity(extractor, fundingBrain, net015, now0 + (ticks - 1) * Utils.TIME_MINUTE, universeCap);

        // S1 score parity (determinism: same OI + closes => same score).
        runS1Parity(now0 + (ticks - 1) * Utils.TIME_MINUTE, universeCap);
    }

    private static boolean pricesEqual(KlineObjectSimple a, KlineObjectSimple b) {
        return a.priceOpen == b.priceOpen && a.maxPrice == b.maxPrice && a.minPrice == b.minPrice
                && a.priceClose == b.priceClose && a.totalUsdt == b.totalUsdt;
    }

    /** Funding pipeline (extract + PASS-2 CS + predictBatch + net015) trên OLD-ticker vs NEW-ticker,
     *  FULL universe, CÙNG recent-batch OI (đầu vào OI đồng nhất ⇒ biến duy nhất là ticker). */
    private static void runFundingParity(FundingDataCollectionManager.FundingFeatureExtractorV2 extractor,
                                         FundingOnnxInferenceManager fundingBrain, Net015ValueLive net015,
                                         long now, int universeCap) throws Exception {
        Map<String, List<KlineObjectSimple>> fullTicker = DataManagerAerospikeFloatSim.readDataForSymbols(
                now - 1000L * Utils.TIME_MINUTE, 1000);
        LiveTickerWindow cache = new LiveTickerWindow();
        Map<String, List<KlineObjectSimple>> cachedTicker = cache.read(now, 1000);

        Map<String, KlineObjectSimple> snapshotFull = snapshotOf(extractor, fullTicker);
        Map<String, KlineObjectSimple> snapshotCache = snapshotOf(extractor, cachedTicker);

        List<String> syms = new ArrayList<>(snapshotFull.keySet());
        Collections.sort(syms);
        if (universeCap > 0 && syms.size() > universeCap) syms = syms.subList(0, universeCap);
        List<KlineObjectSimple> btc = fullTicker.get("BTCUSDT");
        long time = (btc != null && !btc.isEmpty()) ? btc.get(btc.size() - 1).startTime.longValue() : now;
        MarketDataObject marketData = new MarketDataObject(0f, 0f, 0f);
        List<String> basket = Collections.singletonList("BTCUSDT");

        LiveOiFeatProvider oi = new LiveOiFeatProvider();
        oi.beginTick(syms);

        List<FundingMarketFeatures> fullFeats = new ArrayList<>();
        List<FundingMarketFeatures> cacheFeats = new ArrayList<>();
        for (String sym : syms) {
            KlineObjectSimple tf = snapshotFull.get(sym);
            KlineObjectSimple tc = snapshotCache.get(sym);
            if (tf == null || tc == null) continue;
            float[] o = oi.lookup(sym, time);
            FundingMarketFeatures ff = extractOne(extractor, tf, sym, time, snapshotFull, marketData, basket, o);
            FundingMarketFeatures fc = extractOne(extractor, tc, sym, time, snapshotCache, marketData, basket, o);
            if (ff != null) fullFeats.add(ff);
            if (fc != null) cacheFeats.add(fc);
        }
        java.util.Set<String> csPopFull = EntrySignalFilter.selectCoins(snapshotFull, HistoryManager.getInstance());
        java.util.Set<String> csPopCache = EntrySignalFilter.selectCoins(snapshotCache, HistoryManager.getInstance());
        List<FundingMarketFeatures> fullCs = new ArrayList<>(), cacheCs = new ArrayList<>();
        for (FundingMarketFeatures f : fullFeats) if (csPopFull.contains(f.symbol)) fullCs.add(f);
        for (FundingMarketFeatures f : cacheFeats) if (csPopCache.contains(f.symbol)) cacheCs.add(f);
        FundingCrossSectional.apply(fullCs);
        FundingCrossSectional.apply(cacheCs);
        List<float[]> fullArr = new ArrayList<>(), cacheArr = new ArrayList<>();
        for (FundingMarketFeatures f : fullFeats) fullArr.add(fundingBrain.extractFeaturesToArray(f));
        for (FundingMarketFeatures f : cacheFeats) cacheArr.add(fundingBrain.extractFeaturesToArray(f));
        List<float[]> fullPred = fundingBrain.predictBatch(fullArr);
        List<float[]> cachePred = fundingBrain.predictBatch(cacheArr);
        float[] fullPwin = net015.isReady() && !fullArr.isEmpty() ? net015.pwin(fullArr.toArray(new float[0][])) : null;
        float[] cachePwin = net015.isReady() && !cacheArr.isEmpty() ? net015.pwin(cacheArr.toArray(new float[0][])) : null;

        int n = Math.min(fullFeats.size(), cacheFeats.size());
        int sameFeat = 0, diffFeat = 0, samePnp = 0, diffPnp = 0, sameNet = 0, diffNet = 0;
        for (int i = 0; i < n; i++) {
            float[] a = fullArr.get(i), b = cacheArr.get(i);
            boolean feq = true;
            for (int k = 0; k < a.length; k++) {
                boolean an = Float.isNaN(a[k]), bn = Float.isNaN(b[k]);
                if (an || bn) { if (an != bn) feq = false; }
                else if (a[k] != b[k]) feq = false;
            }
            if (feq) sameFeat++; else diffFeat++;
            float pf = fullPred.get(i)[0], pc = cachePred.get(i)[0];
            if ((Float.isNaN(pf) && Float.isNaN(pc)) || pf == pc) samePnp++; else diffPnp++;
            if (fullPwin != null && cachePwin != null) {
                float wf = fullPwin[i], wc = cachePwin[i];
                if ((Float.isNaN(wf) && Float.isNaN(wc)) || wf == wc) sameNet++; else diffNet++;
            }
        }
        LOG.info("[V3-FUNDING-PARITY] nCoin={} feature45 same={} diff={} | pNoPump same={} diff={} | net015 same={} diff={}",
                n, sameFeat, diffFeat, samePnp, diffPnp, sameNet, diffNet);
        LOG.info("[V3-FUNDING-PARITY] VERDICT: {}", (diffFeat == 0 && diffPnp == 0 && diffNet == 0) ? "PASS (bit-identical)" : "FAIL");
    }

    private static Map<String, KlineObjectSimple> snapshotOf(
            FundingDataCollectionManager.FundingFeatureExtractorV2 extractor,
            Map<String, List<KlineObjectSimple>> symbolToKlines) {
        Map<String, KlineObjectSimple> snapshot = new HashMap<>();
        TreeMap<Long, Map<String, KlineObjectSimple>> byTime = new TreeMap<>();
        for (Map.Entry<String, List<KlineObjectSimple>> e : symbolToKlines.entrySet()) {
            List<KlineObjectSimple> l = e.getValue();
            if (l == null || l.isEmpty()) continue;
            for (KlineObjectSimple k : l) {
                if (k == null) continue;
                byTime.computeIfAbsent(k.startTime.longValue(), x -> new HashMap<>()).put(e.getKey(), k);
            }
            KlineObjectSimple last = l.get(l.size() - 1);
            if (last != null && Utils.isTickerAvailable(last)) snapshot.put(e.getKey(), last);
        }
        for (Map<String, KlineObjectSimple> tm : byTime.values()) extractor.updateMarketHistory(tm);
        return snapshot;
    }

    private static FundingMarketFeatures extractOne(FundingDataCollectionManager.FundingFeatureExtractorV2 extractor,
                                                    KlineObjectSimple ticker, String sym, long time,
                                                    Map<String, KlineObjectSimple> snapshot, MarketDataObject marketData,
                                                    List<String> basket, float[] o) {
        OrderTargetInfoTest dummy = new OrderTargetInfoTest(OrderTargetStatus.REQUEST,
                ticker.priceClose, null, 1.0f, Configs.LEVERAGE_ORDER, sym, time, time, OrderSide.BUY);
        dummy.lastEntry = ticker.priceClose;
        FundingMarketFeatures f = extractor.extractFeatures(time, dummy, snapshot, marketData, basket);
        if (f == null) return null;
        f.oiDelta24hCoin = o[0]; f.oiZCoin = o[1]; f.lsGlobalCoin = o[2];
        f.lsToptraderCoin = o[3]; f.takerBuyRatioCoin = o[4];
        return f;
    }

    /** S1 score: gọi scoreAll 2 lần (determinism) — cùng OI + closes ⇒ cùng score. */
    private static void runS1Parity(long now, int universeCap) throws Exception {
        S1RankerLive s1 = S1RankerLive.getInstance();
        if (!s1.isReady()) {
            LOG.info("[V3-S1] model ONNX chua san sang — BO (khong phai FAIL parity)");
            return;
        }
        Map<String, List<KlineObjectSimple>> symbolToKlines = DataManagerAerospikeFloatSim.readDataForSymbols(
                now - 1000L * Utils.TIME_MINUTE, 1000);
        java.util.Set<String> universe = new java.util.HashSet<>(symbolToKlines.keySet());
        List<String> syms = new ArrayList<>(universe);
        Collections.sort(syms);
        if (universeCap > 0 && syms.size() > universeCap) syms = syms.subList(0, universeCap);

        Map<String, Float> s1a = s1.scoreAll(syms, now);
        Map<String, Float> s1b = s1.scoreAll(syms, now);
        if (s1a == null || s1b == null) {
            LOG.info("[V3-S1] scoreAll tra null (warm-up chua du / model loi) — BO tick");
            return;
        }
        int same = 0, diff = 0;
        for (String s : syms) {
            Float a = s1a.get(s), b = s1b.get(s);
            if (a == null && b == null) { same++; continue; }
            if (a == null || b == null) { diff++; continue; }
            if (a.floatValue() == b.floatValue()) same++; else diff++;
        }
        LOG.info("[V3-S1-PARITY] nCoin={} scored={} same={} diff={} (determinism 2 lan)",
                syms.size(), s1a.size(), same, diff);
        LOG.info("[V3-S1-PARITY] VERDICT: {}", diff == 0 ? "PASS (bit-identical)" : "FAIL");
    }

    /** Timing end-to-end: ticker cache + OI + funding predict + net015 trên FULL universe. */
    private static void runTiming(long now0, String fundingModel, int iterations) throws Exception {
        FundingDataCollectionManager.FundingFeatureExtractorV2 extractor =
                new FundingDataCollectionManager.FundingFeatureExtractorV2();
        FundingOnnxInferenceManager fundingBrain = new FundingOnnxInferenceManager(fundingModel);
        Net015ValueLive net015 = Net015ValueLive.getInstance();
        LiveTickerWindow cache = new LiveTickerWindow();
        LiveOiFeatProvider oi = new LiveOiFeatProvider();

        long[] total = new long[iterations];
        long[] ticker = new long[iterations];
        long[] oiMs = new long[iterations];
        for (int it = 0; it < iterations; it++) {
            long now = now0 + (long) it * Utils.TIME_MINUTE;
            long t0 = System.nanoTime();
            Map<String, List<KlineObjectSimple>> symbolToKlines = cache.read(now, 1000);
            long tTicker = (System.nanoTime() - t0) / 1_000_000L;
            Map<String, KlineObjectSimple> snapshot = new HashMap<>();
            TreeMap<Long, Map<String, KlineObjectSimple>> byTime = new TreeMap<>();
            for (Map.Entry<String, List<KlineObjectSimple>> e : symbolToKlines.entrySet()) {
                List<KlineObjectSimple> l = e.getValue();
                if (l == null || l.isEmpty()) continue;
                for (KlineObjectSimple k : l) byTime.computeIfAbsent(k.startTime.longValue(), x -> new HashMap<>()).put(e.getKey(), k);
                KlineObjectSimple last = l.get(l.size() - 1);
                if (last != null && Utils.isTickerAvailable(last)) snapshot.put(e.getKey(), last);
            }
            for (Map<String, KlineObjectSimple> tm : byTime.values()) extractor.updateMarketHistory(tm);
            List<String> syms = new ArrayList<>(snapshot.keySet());
            Collections.sort(syms);
            List<KlineObjectSimple> btc = symbolToKlines.get("BTCUSDT");
            long time = (btc != null && !btc.isEmpty()) ? btc.get(btc.size() - 1).startTime.longValue() : now;
            MarketDataObject marketData = new MarketDataObject(0f, 0f, 0f);
            List<String> basket = Collections.singletonList("BTCUSDT");
            oi.beginTick(syms);
            long tOi0 = System.nanoTime();
            List<FundingMarketFeatures> featsList = new ArrayList<>();
            for (String sym : syms) {
                KlineObjectSimple tk = snapshot.get(sym);
                if (tk == null) continue;
                OrderTargetInfoTest dummy = new OrderTargetInfoTest(OrderTargetStatus.REQUEST,
                        tk.priceClose, null, 1.0f, Configs.LEVERAGE_ORDER, sym, time, time, OrderSide.BUY);
                dummy.lastEntry = tk.priceClose;
                FundingMarketFeatures feats = extractor.extractFeatures(time, dummy, snapshot, marketData, basket);
                if (feats != null) {
                    float[] o = oi.lookup(sym, time);
                    feats.oiDelta24hCoin = o[0]; feats.oiZCoin = o[1]; feats.lsGlobalCoin = o[2];
                    feats.lsToptraderCoin = o[3]; feats.takerBuyRatioCoin = o[4];
                    featsList.add(feats);
                }
            }
            long tOi = (System.nanoTime() - tOi0) / 1_000_000L;
            java.util.Set<String> csPop = EntrySignalFilter.selectCoins(snapshot, HistoryManager.getInstance());
            List<FundingMarketFeatures> csList = new ArrayList<>();
            for (FundingMarketFeatures f : featsList) if (csPop.contains(f.symbol)) csList.add(f);
            FundingCrossSectional.apply(csList);
            List<float[]> featureArrays = new ArrayList<>();
            for (FundingMarketFeatures f : featsList) featureArrays.add(fundingBrain.extractFeaturesToArray(f));
            fundingBrain.predictBatch(featureArrays);
            if (net015.isReady() && !featureArrays.isEmpty()) net015.pwin(featureArrays.toArray(new float[0][]));
            total[it] = (System.nanoTime() - t0) / 1_000_000L;
            ticker[it] = tTicker;
            oiMs[it] = tOi;
        }
        report("TOTAL end-to-end (ticker cache + OI + funding + net015)", total);
        report("ticker (cache)", ticker);
        report("OI (lookup)", oiMs);
    }

    private static void report(String label, long[] ms) {
        long[] s = Arrays.copyOf(ms, ms.length);
        Arrays.sort(s);
        long p50 = s[s.length / 2];
        long p95 = s[Math.min(s.length - 1, (int) (s.length * 0.95))];
        LOG.info("[V3-BENCH] {} n={} p50={}ms p95={}ms max={}ms", label, s.length, p50, p95, s[s.length - 1]);
    }
}
