package com.binance.chuyennd.ai_ml.features.export.gate;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.features.export.entry.ComprehensiveMarketFeatureExtractor;
import com.binance.chuyennd.ai_ml.features.export.entry.MarketFeatures;
import com.binance.chuyennd.ai_ml.features.export.funding.EntrySignalFilter;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.util.*;

/**
 * TASK-043 Bước A — Export dataset GATE 15m v2 để kiểm GIẢ THUYẾT: đổi tập lấy nhãn từ basket cũ
 * ({@code findPotentialLosers} = coin đang giảm) SANG tập selector ({@code EntrySignalFilter}) có làm
 * model 15m tốt hơn không.
 *
 * <p><b>Feature</b>: dùng NGUYÊN {@link ComprehensiveMarketFeatureExtractor} (parity ONNX cũ) —
 * KHÔNG đổi feature ở bước này (cô lập biến: chỉ đổi NHÃN). OI sẽ thêm ở bước sau NẾU nhãn-selector thắng.
 *
 * <p><b>Hai nhãn song song</b> (cùng feature, cùng mốc, để A/B trực tiếp):
 * <ul>
 *   <li>{@code label_oldbasket} = basketMaxGain 15m trên {@code findPotentialLosers(ts)} (= model cũ).</li>
 *   <li>{@code label_selector} = basketMaxGain 15m trên {@code EntrySignalFilter.selectCoins(snap, history)}.</li>
 * </ul>
 *
 * <p><b>LOOK-AHEAD SẠCH</b> (copy cơ chế CompareMarketModels đã ra IC 0.5175 thật):
 * <ul>
 *   <li>Feature tại t dùng history ≤ t (updateHistory trước extract).</li>
 *   <li>Label dùng {@code subMap(ts, false, ts+15m, true)} = chỉ (t, t+15m] — KHÔNG gồm t.</li>
 *   <li>Basket chốt tại t (entry=priceClose@t); de-overlap 15m theo thời gian.</li>
 * </ul>
 *
 * <p>Chạy ORACLE (đọc Aerospike 226+242). Mode: SMOKE (1-2 tháng, validate) | FULL.
 * Args: [mode=SMOKE|FULL] [startYYYYMMDD] [endYYYYMMDD] [outCsv]
 */
public class ExportGate15mV2 {

    static final Logger LOG = LoggerFactory.getLogger(ExportGate15mV2.class);
    static final long H15 = 15 * 60_000L;
    static final int WARMUP_HOURS = 48;

    public static void main(String[] args) {
        try {
            String mode = args.length > 0 ? args[0] : "SMOKE";
            String startStr = args.length > 1 ? args[1] : (mode.equals("FULL") ? "20210101" : "20220401");
            String endStr = args.length > 2 ? args[2] : (mode.equals("FULL") ? "20260601" : "20220601");
            String outCsv = args.length > 3 ? args[3]
                    : (System.getProperty("user.home") + "/claudedata/gate15m_v2_" + mode.toLowerCase() + ".csv");
            new ExportGate15mV2().run(mode, startStr, endStr, outCsv);
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("❌ ExportGate15mV2 FAIL", e);
            System.exit(1);
        }
    }

    void run(String mode, String startStr, String endStr, String outCsv) throws Exception {
        long fairStart = Utils.sdfFile.parse(startStr).getTime();
        long evalEnd = Utils.sdfFile.parse(endStr).getTime();
        long warmupStart = fairStart - WARMUP_HOURS * Utils.TIME_HOUR;
        LOG.info("📤 EXPORT gate15m v2 | mode={} | {} -> {} | out={}", mode, startStr, endStr, outCsv);
        LOG.info("   feature=ComprehensiveMarketFeatureExtractor (parity ONNX); 2 nhãn: oldbasket vs selector");

        LOG.info("📥 Nạp market rate data (cho momentum1M/15M)...");
        TreeMap<Long, MarketDataObject> time2Rate = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        LOG.info("   market rate: {} mốc", time2Rate.size());

        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();
        ComprehensiveMarketFeatureExtractor extractor = new ComprehensiveMarketFeatureExtractor();

        File outFile = new File(outCsv);
        if (outFile.getParentFile() != null) outFile.getParentFile().mkdirs();

        long nRows = 0, nWarmupSkip = 0, nBasketEmptyOld = 0, nBasketEmptySel = 0;
        long last15 = 0L;
        // determinism mẫu: hash cộng dồn feature (so 2 lần chạy ngoài)
        double featChecksum = 0;

        try (BufferedWriter w = new BufferedWriter(new FileWriter(outFile))) {
            // header: feature CSV (bỏ 2 cột label cũ của MarketFeatures) + 2 nhãn mới + meta basket size
            w.write(headerWithDualLabels());
            w.newLine();

            long day = Utils.getDate(warmupStart);
            long lastDay = Utils.getDate(evalEnd);
            int dayCount = 0;
            while (day <= lastDay) {
                try {
                    TreeMap<Long, Map<String, KlineObjectSimple>> today =
                            DataManagerAerospikeFloatSim.readDataFromAerospike1M(day);
                    TreeMap<Long, Map<String, KlineObjectSimple>> tomorrow =
                            DataManagerAerospikeFloatSim.readDataFromAerospike1M(day + Utils.TIME_DAY);
                    TreeMap<Long, Map<String, KlineObjectSimple>> lookup = new TreeMap<>();
                    if (today != null) lookup.putAll(today);
                    if (tomorrow != null) lookup.putAll(tomorrow);
                    if (today == null) { day += Utils.TIME_DAY; continue; }

                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : today.entrySet()) {
                        long ts = e.getKey();
                        Map<String, KlineObjectSimple> snap = e.getValue();

                        // nuôi history mỗi phút (kể cả warmup)
                        HistoryManager.getInstance().updateHistory(snap);
                        CoinRankManager.getInstance().getTopCoin(ts);
                        if (ts < fairStart || ts > evalEnd) { nWarmupSkip++; continue; }

                        // de-overlap 15m
                        if (ts - last15 < H15) continue;

                        MarketFeatures f = extractor.extractAllFeatures(ts, snap, time2Rate.get(ts));
                        if (f == null) continue;

                        // 2 basket tại t
                        List<String> basketOld = HistoryManager.getInstance().findPotentialLosers(ts);
                        Set<String> basketSel = EntrySignalFilter.selectCoins(snap, HistoryManager.getInstance());
                        if (basketOld == null || basketOld.isEmpty()) nBasketEmptyOld++;
                        if (basketSel.isEmpty()) nBasketEmptySel++;

                        // Label look-ahead sạch: chỉ (t, t+15m] (subMap exclusive-t bên dưới)
                        float labOld = basketMaxGain(lookup, ts, basketOld);
                        float labSel = basketMaxGain(lookup, ts, new ArrayList<>(basketSel));

                        // checksum vài feature để determinism-check
                        featChecksum += f.momentum15M + f.volatility15M + f.basketVolSpike;

                        w.write(rowWithDualLabels(f, labOld, labSel,
                                basketOld == null ? 0 : basketOld.size(), basketSel.size()));
                        w.newLine();
                        nRows++;
                        last15 = ts;
                    }
                } catch (Exception ex) {
                    LOG.warn("⚠️ Lỗi ngày {}: {}", Utils.normalizeDateYYYYMMDD(day), ex.getMessage());
                }
                day += Utils.TIME_DAY;
                if (++dayCount % 10 == 0) LOG.info("... {} ngày | rows={} | day={}", dayCount, nRows, Utils.normalizeDateYYYYMMDD(day));
            }
        }

        LOG.info("✅ DONE export -> {}", outCsv);
        LOG.info("   rows={} | warmupSkip={} | basketEmptyOld={} | basketEmptySel={}",
                nRows, nWarmupSkip, nBasketEmptyOld, nBasketEmptySel);
        LOG.info("   featChecksum={} (so 2 lần chạy để check determinism)", String.format("%.6f", featChecksum));
        LOG.info("   look-ahead: label dùng subMap(ts,false,..) = (t,t+15m] — exclusive t (sạch theo CompareMarketModels)");
        if (nRows == 0) LOG.error("⛔ 0 rows — kiểm range/đọc data!");
    }

    /** Header = feature MarketFeatures (cắt 2 cột label cũ) + 2 nhãn mới + 2 cột basketSize. */
    private String headerWithDualLabels() {
        String base = new MarketFeatures().toCSVHeader();
        // bỏ đuôi ",futureReturn15M,maxDrawdownNext4H" của MarketFeatures, thay bằng nhãn mới
        int cut = base.indexOf(",futureReturn15M");
        if (cut > 0) base = base.substring(0, cut);
        return base + ",label_oldbasket,label_selector,nBasketOld,nBasketSel";
    }

    private String rowWithDualLabels(MarketFeatures f, float labOld, float labSel, int nOld, int nSel) {
        String base = f.toCSVRow();
        // toCSVRow kết thúc bằng "...,<futureReturn15M>,<maxDrawdownNext4H>" — cắt 2 cột cuối
        int idx = nthLastComma(base, 2);
        if (idx > 0) base = base.substring(0, idx);
        return base + "," + fmt(labOld) + "," + fmt(labSel) + "," + nOld + "," + nSel;
    }

    private static int nthLastComma(String s, int n) {
        int count = 0;
        for (int i = s.length() - 1; i >= 0; i--) {
            if (s.charAt(i) == ',') { if (++count == n) return i; }
        }
        return -1;
    }

    private static String fmt(float v) {
        if (Float.isNaN(v) || Float.isInfinite(v)) return "0.000000";
        return String.format(Locale.US, "%.8f", v);
    }

    /** basketMaxGain: TB max-gain 15m của basket. entry=priceClose@t; tương lai = (t, t+15m]. Copy CompareMarketModels. */
    private float basketMaxGain(TreeMap<Long, Map<String, KlineObjectSimple>> data, long ts, List<String> basket) {
        if (basket == null || basket.isEmpty()) return 0f;
        long end = ts + H15;
        Map<String, KlineObjectSimple> cur = data.get(ts);
        if (cur == null) return 0f;
        Map<String, Float> entry = new HashMap<>();
        for (String s : basket) if (cur.containsKey(s) && cur.get(s).priceClose > 0) entry.put(s, cur.get(s).priceClose);
        if (entry.isEmpty()) return 0f;
        NavigableMap<Long, Map<String, KlineObjectSimple>> fut = data.subMap(ts, false, end, true);
        Map<String, Float> maxRet = new HashMap<>();
        for (String s : entry.keySet()) maxRet.put(s, -999f);
        for (Map<String, KlineObjectSimple> m : fut.values()) {
            for (String s : entry.keySet()) {
                if (m.containsKey(s)) {
                    float e = entry.get(s);
                    float r = (m.get(s).maxPrice - e) / e;
                    if (r > maxRet.get(s)) maxRet.put(s, r);
                }
            }
        }
        float sum = 0; int c = 0;
        for (String s : entry.keySet()) { float r = maxRet.get(s); if (r != -999f) { sum += r; c++; } }
        return c > 0 ? sum / c : 0f;
    }
}
