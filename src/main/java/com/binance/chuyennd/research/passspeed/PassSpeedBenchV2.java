package com.binance.chuyennd.research.passspeed;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
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
import com.binance.chuyennd.research.oibackfill.OiFeatLiveSets;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.selector.Net015ValueLive;
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
 * [B5-PASS-SPEED-V2] BENCH read-only cho 1 lượt predict FUNDING (feature 45 + pNoPump + net015):
 * KHÔNG đặt lệnh, KHÔNG ghi Redis/Aerospike/242.
 *
 * <p>Hai chế độ:
 * <ul>
 *   <li><b>timing</b> (mặc định): đo p50/p95 1 lượt predict (ticker read + extract + PASS-2 CS +
 *       predictBatch + net015) KHÔNG OI lookup (tránh cạnh tranh 242 khi shadow chạy). Phần OI
 *       (cold ~30s/giờ, cache-hit ~250ms) đã đo ở B4 (RESULT_PASS_SPEED.md §1).</li>
 *   <li><b>parity</b> (thêm {@code parity} làm arg): OLD (full-history OI per-coin) vs NEW (batch
 *       recent + cache) trên CÙNG snapshot → feature 45 + pNoPump + net015 BIT-IDENTICAL.</li>
 * </ul>
 *
 * <p>Sau B5 bỏ market-only skip, tick selector VÀ market-only đều predict full universe ⇒ cùng đường
 * predict. Args: {@code [mode] [universe] [subset] [iterations]}.
 */
public class PassSpeedBenchV2 {

    private static final Logger LOG = LoggerFactory.getLogger(PassSpeedBenchV2.class);

    private static final String[] OI_SETS = {
            OiFeatLiveSets.OI_DELTA24H, OiFeatLiveSets.OI_Z, OiFeatLiveSets.LS_GLOBAL,
            OiFeatLiveSets.LS_TOPTRADER, OiFeatLiveSets.TAKER_BUY
    };
    private static final long CACHE_WINDOW_MS = 24L * 60L * 60_000L;

    public static void main(String[] args) throws Exception {
        String mode = args.length >= 1 ? args[0] : "timing";
        int universe = args.length >= 2 ? Integer.parseInt(args[1]) : 0;   // 0 = toàn bộ snapshot
        int subset = args.length >= 3 ? Integer.parseInt(args[2]) : 60;    // parity OLD subset
        int iterations = args.length >= 4 ? Integer.parseInt(args[3]) : 30;
        String fundingModel = System.getProperty("funding.model",
                "../storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx");

        LOG.info("[V2] init SimpleSymbolMapper...");
        SimpleSymbolMapper.getInstance().init();

        FundingDataCollectionManager.FundingFeatureExtractorV2 extractor =
                new FundingDataCollectionManager.FundingFeatureExtractorV2();

        long tTicker0 = System.nanoTime();
        Map<String, List<KlineObjectSimple>> symbolToKlines = DataManagerAerospikeFloatSim.readDataForSymbols(
                System.currentTimeMillis() - 1000L * Utils.TIME_MINUTE, 1000);
        long tickerMs = (System.nanoTime() - tTicker0) / 1_000_000L;
        LOG.info("[V2] ticker read (1000') = {}ms, {} symbol", tickerMs, symbolToKlines.size());

        Map<String, KlineObjectSimple> snapshot = new HashMap<>();
        TreeMap<Long, Map<String, KlineObjectSimple>> byTime = new TreeMap<>();
        for (Map.Entry<String, List<KlineObjectSimple>> e : symbolToKlines.entrySet()) {
            List<KlineObjectSimple> l = e.getValue();
            if (l == null || l.isEmpty()) continue;
            for (KlineObjectSimple k : l) {
                if (k == null) continue;
                byTime.computeIfAbsent(k.startTime.longValue(), t -> new HashMap<>()).put(e.getKey(), k);
            }
            KlineObjectSimple last = l.get(l.size() - 1);
            if (last != null && Utils.isTickerAvailable(last)) snapshot.put(e.getKey(), last);
        }
        for (Map<String, KlineObjectSimple> tm : byTime.values()) extractor.updateMarketHistory(tm);
        LOG.info("[V2] warm HistoryManager: {} phut, {} symbol snapshot", byTime.size(), snapshot.size());

        FundingOnnxInferenceManager fundingBrain = new FundingOnnxInferenceManager(fundingModel);
        Net015ValueLive net015 = Net015ValueLive.getInstance();
        LOG.info("[V2] net015 ready={}", net015.isReady());

        List<String> syms = new ArrayList<>(snapshot.keySet());
        Collections.sort(syms);
        if (universe > 0 && syms.size() > universe) syms = syms.subList(0, universe);
        List<KlineObjectSimple> btc = symbolToKlines.get("BTCUSDT");
        long time = (btc != null && !btc.isEmpty()) ? btc.get(btc.size() - 1).startTime.longValue()
                : System.currentTimeMillis();
        MarketDataObject marketData = new MarketDataObject(0f, 0f, 0f);
        List<String> basket = Collections.singletonList("BTCUSDT");

        if ("parity".equals(mode)) {
            runParity(extractor, fundingBrain, net015, snapshot, syms, time, marketData, basket, subset);
        } else {
            runTiming(extractor, fundingBrain, net015, snapshot, syms, time, marketData, basket, iterations, tickerMs);
        }

        LOG.info("[V2] xong. KHONG ghi gi len 242 (read-only).");
        System.exit(0);
    }

    /** Timing: extract + PASS-2 CS + predictBatch + net015 (KHÔNG OI lookup) trên universe. */
    private static void runTiming(FundingDataCollectionManager.FundingFeatureExtractorV2 extractor,
                                  FundingOnnxInferenceManager fundingBrain, Net015ValueLive net015,
                                  Map<String, KlineObjectSimple> snapshot, List<String> syms, long time,
                                  MarketDataObject marketData, List<String> basket, int iterations, long tickerMs) {
        long[] extractMs = new long[iterations];
        long[] csMs = new long[iterations];
        long[] batchMs = new long[iterations];
        long[] netMs = new long[iterations];
        long[] totalMs = new long[iterations];
        int nCoin = 0;
        for (int it = 0; it < iterations; it++) {
            long t0 = System.nanoTime();
            List<FundingMarketFeatures> featsList = new ArrayList<>();
            long tExtract0 = System.nanoTime();
            for (String sym : syms) {
                KlineObjectSimple ticker = snapshot.get(sym);
                OrderTargetInfoTest dummy = new OrderTargetInfoTest(OrderTargetStatus.REQUEST,
                        ticker.priceClose, null, 1.0f, Configs.LEVERAGE_ORDER, sym, time, time, OrderSide.BUY);
                dummy.lastEntry = ticker.priceClose;
                FundingMarketFeatures feats = extractor.extractFeatures(time, dummy, snapshot, marketData, basket);
                if (feats != null) {
                    // OI lookup BỎ (timing CPU, không cạnh tranh 242) — OI đo riêng ở B4.
                    featsList.add(feats);
                }
            }
            long tExtractMs = (System.nanoTime() - tExtract0) / 1_000_000L;
            long tCs0 = System.nanoTime();
            java.util.Set<String> csPop = EntrySignalFilter.selectCoins(snapshot, HistoryManager.getInstance());
            List<FundingMarketFeatures> csList = new ArrayList<>();
            for (FundingMarketFeatures f : featsList) if (csPop.contains(f.symbol)) csList.add(f);
            FundingCrossSectional.apply(csList);
            long tCsMs = (System.nanoTime() - tCs0) / 1_000_000L;
            long tBatch0 = System.nanoTime();
            List<float[]> featureArrays = new ArrayList<>();
            for (FundingMarketFeatures f : featsList) featureArrays.add(fundingBrain.extractFeaturesToArray(f));
            List<float[]> preds = fundingBrain.predictBatch(featureArrays);
            long tBatchMs = (System.nanoTime() - tBatch0) / 1_000_000L;
            long tNet0 = System.nanoTime();
            if (net015.isReady() && !featureArrays.isEmpty()) net015.pwin(featureArrays.toArray(new float[0][]));
            long tNetMs = (System.nanoTime() - tNet0) / 1_000_000L;
            extractMs[it] = tExtractMs;
            csMs[it] = tCsMs;
            batchMs[it] = tBatchMs;
            netMs[it] = tNetMs;
            totalMs[it] = (System.nanoTime() - t0) / 1_000_000L;
            nCoin = featsList.size();
        }
        LOG.info("[V2-TIMING] ticker-read = {}ms | nCoin = {} (universe cap)", tickerMs, nCoin);
        report("extract(no-OI)", extractMs);
        report("cs-rank", csMs);
        report("predictBatch", batchMs);
        report("net015", netMs);
        report("TOTAL-predict(1-luot, no-OI)", totalMs);
    }

    /** PARITY OLD (full-history OI) vs NEW (cached) trên CÙNG snapshot: feature45 + pNoPump + net015. */
    private static void runParity(FundingDataCollectionManager.FundingFeatureExtractorV2 extractor,
                                  FundingOnnxInferenceManager fundingBrain, Net015ValueLive net015,
                                  Map<String, KlineObjectSimple> snapshot, List<String> syms, long time,
                                  MarketDataObject marketData, List<String> basket, int subset) throws Exception {
        long cutoff = time - CACHE_WINDOW_MS;
        LiveOiFeatProvider oi = new LiveOiFeatProvider();
        oi.beginTick(syms);

        List<String> paritySyms = syms.subList(0, Math.min(subset, syms.size()));
        List<FundingMarketFeatures> newFeats = new ArrayList<>();
        List<FundingMarketFeatures> oldFeats = new ArrayList<>();
        for (String sym : paritySyms) {
            KlineObjectSimple ticker = snapshot.get(sym);
            OrderTargetInfoTest dummy = new OrderTargetInfoTest(OrderTargetStatus.REQUEST,
                    ticker.priceClose, null, 1.0f, Configs.LEVERAGE_ORDER, sym, time, time, OrderSide.BUY);
            dummy.lastEntry = ticker.priceClose;
            FundingMarketFeatures fn = extractor.extractFeatures(time, dummy, snapshot, marketData, basket);
            if (fn == null) continue;
            float[] oOld = oldLookup(sym, time, cutoff);
            float[] oNew = oi.lookup(sym, time);
            fn.oiDelta24hCoin = oNew[0]; fn.oiZCoin = oNew[1]; fn.lsGlobalCoin = oNew[2];
            fn.lsToptraderCoin = oNew[3]; fn.takerBuyRatioCoin = oNew[4];
            FundingMarketFeatures fo = copyWithOi(fn, oOld);
            newFeats.add(fn);
            oldFeats.add(fo);
        }
        java.util.Set<String> csPop = EntrySignalFilter.selectCoins(snapshot, HistoryManager.getInstance());
        List<FundingMarketFeatures> newCs = new ArrayList<>(), oldCs = new ArrayList<>();
        for (FundingMarketFeatures f : newFeats) if (csPop.contains(f.symbol)) newCs.add(f);
        for (FundingMarketFeatures f : oldFeats) if (csPop.contains(f.symbol)) oldCs.add(f);
        FundingCrossSectional.apply(newCs);
        FundingCrossSectional.apply(oldCs);
        List<float[]> newArr = new ArrayList<>(), oldArr = new ArrayList<>();
        for (FundingMarketFeatures f : newFeats) newArr.add(fundingBrain.extractFeaturesToArray(f));
        for (FundingMarketFeatures f : oldFeats) oldArr.add(fundingBrain.extractFeaturesToArray(f));
        List<float[]> newPred = fundingBrain.predictBatch(newArr);
        List<float[]> oldPred = fundingBrain.predictBatch(oldArr);
        float[] newPwin = net015.isReady() && !newArr.isEmpty() ? net015.pwin(newArr.toArray(new float[0][])) : null;
        float[] oldPwin = net015.isReady() && !oldArr.isEmpty() ? net015.pwin(oldArr.toArray(new float[0][])) : null;

        int sameFeat = 0, diffFeat = 0, samePnp = 0, diffPnp = 0, sameNet = 0, diffNet = 0;
        float maxFeatDiff = 0f, maxPnpDiff = 0f, maxNetDiff = 0f;
        List<String> diffSyms = new ArrayList<>();
        for (int i = 0; i < newFeats.size(); i++) {
            String sym = newFeats.get(i).symbol;
            float[] a = newArr.get(i), b = oldArr.get(i);
            boolean feq = true;
            for (int k = 0; k < a.length; k++) {
                boolean an = Float.isNaN(a[k]), bn = Float.isNaN(b[k]);
                if (an || bn) { if (an != bn) { feq = false; maxFeatDiff = Float.MAX_VALUE; } }
                else if (a[k] != b[k]) { feq = false; maxFeatDiff = Math.max(maxFeatDiff, Math.abs(a[k] - b[k])); }
            }
            if (feq) sameFeat++; else { diffFeat++; diffSyms.add(sym + ":feat"); }
            float pn = newPred.get(i)[0], po = oldPred.get(i)[0];
            boolean peq = (Float.isNaN(pn) && Float.isNaN(po)) || pn == po;
            if (peq) samePnp++; else { diffPnp++; maxPnpDiff = Math.max(maxPnpDiff, Math.abs(pn - po)); if (!diffSyms.contains(sym + ":pnp")) diffSyms.add(sym + ":pnp"); }
            if (newPwin != null && oldPwin != null) {
                float wn = newPwin[i], wo = oldPwin[i];
                boolean weq = (Float.isNaN(wn) && Float.isNaN(wo)) || wn == wo;
                if (weq) sameNet++; else { diffNet++; maxNetDiff = Math.max(maxNetDiff, Math.abs(wn - wo)); if (!diffSyms.contains(sym + ":net")) diffSyms.add(sym + ":net"); }
            }
        }
        LOG.info("[V2-PARITY] nCoin={} feature45 same={} diff={} maxDiff={} | pNoPump same={} diff={} maxDiff={} | net015 same={} diff={} maxDiff={}",
                newFeats.size(), sameFeat, diffFeat, maxFeatDiff, samePnp, diffPnp, maxPnpDiff, sameNet, diffNet, maxNetDiff);
        LOG.info("[V2-PARITY] lech (≤10): {}", diffSyms.isEmpty() ? "-" : diffSyms.subList(0, Math.min(10, diffSyms.size())));
        LOG.info("[V2-PARITY] VERDICT: {}", (diffFeat == 0 && diffPnp == 0 && diffNet == 0) ? "PASS (bit-identical)" : "FAIL");
    }

    private static FundingMarketFeatures copyWithOi(FundingMarketFeatures src, float[] oi) {
        FundingMarketFeatures f = new FundingMarketFeatures();
        f.timestamp = src.timestamp;
        f.symbol = src.symbol;
        f.oiDelta24hCoin = oi[0]; f.oiZCoin = oi[1]; f.lsGlobalCoin = oi[2];
        f.lsToptraderCoin = oi[3]; f.takerBuyRatioCoin = oi[4];
        copyBase(src, f);
        return f;
    }

    private static void copyBase(FundingMarketFeatures s, FundingMarketFeatures d) {
        d.btcMomentum1H = s.btcMomentum1H; d.btcMomentum4H = s.btcMomentum4H; d.btcMomentum24H = s.btcMomentum24H;
        d.btcDominance = s.btcDominance; d.marketBreadthStrength = s.marketBreadthStrength;
        d.rateDownAvg = s.rateDownAvg; d.rateDown15MAvg = s.rateDown15MAvg;
        d.momentum1H = s.momentum1H; d.momentum4H = s.momentum4H; d.momentum24H = s.momentum24H;
        d.rsi1H = s.rsi1H; d.distFromLow24H = s.distFromLow24H; d.volatilityShock = s.volatilityShock;
        d.basketMomentum15M = s.basketMomentum15M; d.basketMomentum1H = s.basketMomentum1H; d.basketMomentum24H = s.basketMomentum24H;
        d.basketRsi14 = s.basketRsi14; d.basketVolSpike = s.basketVolSpike;
        d.coinFundingRate = s.coinFundingRate; d.basketFundingAvg = s.basketFundingAvg; d.fundingRateAvg24H = s.fundingRateAvg24H; d.fundingRateTrend = s.fundingRateTrend;
        d.fundingPercentileCoin = s.fundingPercentileCoin; d.fundingZCoin = s.fundingZCoin; d.fundingPersistence = s.fundingPersistence; d.fundingSum24h = s.fundingSum24h; d.fundingAbs = s.fundingAbs;
        d.volumeZCoin = s.volumeZCoin; d.volumeTrend = s.volumeTrend;
        d.distFromHigh24H = s.distFromHigh24H; d.rangePosition24H = s.rangePosition24H; d.atrSqueeze = s.atrSqueeze; d.relStrengthBtc24H = s.relStrengthBtc24H;
        d.fundingRankCS = s.fundingRankCS; d.volumeZRankCS = s.volumeZRankCS; d.momentumRankCS = s.momentumRankCS;
        d.ret15m = s.ret15m; d.rvol15m = s.rvol15m; d.volumeZ5m = s.volumeZ5m; d.closePosRange15m = s.closePosRange15m; d.wickRatio15m = s.wickRatio15m;
    }

    private static float[] oldLookup(String sym, long time, long cutoff) {
        @SuppressWarnings("unchecked")
        TreeMap<Long, Float>[] arr = new TreeMap[]{
                recentTail(DataManagerAerospikeFloatSim.getMetricMap242(OI_SETS[0], OiFeatLiveSets.BIN, sym), cutoff),
                recentTail(DataManagerAerospikeFloatSim.getMetricMap242(OI_SETS[1], OiFeatLiveSets.BIN, sym), cutoff),
                recentTail(DataManagerAerospikeFloatSim.getMetricMap242(OI_SETS[2], OiFeatLiveSets.BIN, sym), cutoff),
                recentTail(DataManagerAerospikeFloatSim.getMetricMap242(OI_SETS[3], OiFeatLiveSets.BIN, sym), cutoff),
                recentTail(DataManagerAerospikeFloatSim.getMetricMap242(OI_SETS[4], OiFeatLiveSets.BIN, sym), cutoff),
        };
        Long ref = floorKeyTol(arr[1], time);
        if (ref == null) ref = floorKeyTol(arr[0], time);
        if (ref == null) return new float[]{Float.NaN, Float.NaN, Float.NaN, Float.NaN, Float.NaN};
        return new float[]{val(arr[0], ref), val(arr[1], ref), val(arr[2], ref), val(arr[3], ref), val(arr[4], ref)};
    }

    private static TreeMap<Long, Float> recentTail(TreeMap<Long, Float> m, long cutoff) {
        if (m == null || m.isEmpty()) return m;
        return new TreeMap<>(m.tailMap(cutoff, true));
    }

    private static Long floorKeyTol(TreeMap<Long, Float> m, long t) {
        if (m == null || m.isEmpty()) return null;
        Long k = m.floorKey(t);
        if (k == null || (t - k) > OiFeatLiveSets.MERGE_TOL_MS) return null;
        return k;
    }

    private static float val(TreeMap<Long, Float> m, long ts) {
        if (m == null) return Float.NaN;
        Float v = m.get(ts);
        return v == null ? Float.NaN : v;
    }

    private static void report(String label, long[] ms) {
        long[] s = Arrays.copyOf(ms, ms.length);
        Arrays.sort(s);
        long p50 = s[s.length / 2];
        long p95 = s[Math.min(s.length - 1, (int) (s.length * 0.95))];
        LOG.info("[V2-BENCH] {} n={} p50={}ms p95={}ms max={}ms", label, s.length, p50, p95, s[s.length - 1]);
    }
}
