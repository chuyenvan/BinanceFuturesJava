package com.binance.chuyennd.ai_ml.validation;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoDataset;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.util.*;
import java.util.zip.GZIPInputStream;

/**
 * TASK-128 — Đo CHẤT LƯỢNG model trong WFO dataset (gate/market + funding selector), THUẦN JAVA để tái dùng
 * ĐÚNG code nhãn (chống bẫy "đo sai chiều" khi reimplement Python). Xuất CSV thô per-record → Python tổng hợp
 * IC / decile / hit-rate theo quý.
 *
 * <p><b>Nguồn</b> (đều FILE, không scanAll Aerospike trên đường chạy):
 * <ul>
 *   <li>WfoDataset ({@code WFO_DATA_DIR}): market/pred/funding.bin + manifest (verify md5 qua {@link WfoDataset#load}).</li>
 *   <li>Ticker ({@code TICKER_DIR}, mặc định {@code kaggle_data_hpo}): {@code ticker_YYYYMMDD.bin[.gz]} =
 *       Java-serialized {@code TreeMap<Long,Map<String,KlineObjectSimple>>} (mirror {@code KaggleDataLoader}).</li>
 *   <li>Symbol mapper: {@link SimpleSymbolMapper#init()} (đọc Aerospike theo config box; chỉ ĐỌC).</li>
 * </ul>
 *
 * <p><b>ĐỊNH NGHĨA (pre-registered — xem docs/reports/model_quality_wfo_20260704.md):</b>
 * <ul>
 *   <li>Market {@code predReturn15M}: realized = {@code basketMaxGain(findPotentialLosers(t), 15m)} (mirror
 *       {@code ValidateOldPredictVsRealized} + {@code WFOGateRunner}). Chiều: cao ⇒ realized cao (IC dương).</li>
 *   <li>Market {@code predRisk4H}: realized = {@code basketMaxDrawdown(findPotentialLosers(t), 4h=240m)}. Cả hai âm; IC dương.</li>
 *   <li>Funding {@code score=pred[0]=1−P(win@24h)}: realized win = {@code maxFav_24h ≥ 0.06 & nBars_24h ≥ 96}.
 *       Chiều: SELECTED = score THẤP (P(win) cao). maxFav_24h = max((maxPrice/close(t))−1) trên (t,t+24h].</li>
 * </ul>
 *
 * <p>Args/env: {@code WFO_DATA_DIR} (bắt buộc), {@code TICKER_DIR} (mặc định {@code kaggle_data_hpo}),
 * {@code OUT_DIR} (mặc định {@code t128_out}), {@code START}/{@code END} (yyyyMMdd, mặc định = range pred),
 * {@code WARMUP_DAYS} (2), {@code FUNDING_SAMPLE_MIN} (60). Kết thúc {@code System.exit(0)} (Kaggle).
 */
public class Task128ModelQuality {

    private static final Logger LOG = LoggerFactory.getLogger(Task128ModelQuality.class);

    private static final long H15_MS = 15L * 60_000L;
    private static final long H4_MS = 4L * 60L * 60_000L;   // 240m
    private static final long H24_MS = 24L * 60L * 60_000L;
    private static final long BUCKET_MS = 15L * 60_000L;    // lưới 15m cho nBars funding (khớp ExportFundingLabel)
    private static final int NBARS_24H_FULL = 96;           // 24h/15m
    private static final float WIN = 0.06f;

    public static void main(String[] args) {
        try {
            String dataDir = env("WFO_DATA_DIR", args.length > 0 ? args[0] : null);
            if (dataDir == null) { LOG.error("⛔ Thiếu WFO_DATA_DIR"); System.exit(1); }
            String tickerDir = env("TICKER_DIR", "kaggle_data_hpo");
            String outDir = env("OUT_DIR", "t128_out");
            int warmupDays = Integer.parseInt(env("WARMUP_DAYS", "2"));
            long sampleMs = Long.parseLong(env("FUNDING_SAMPLE_MIN", "60")) * 60_000L;
            new File(outDir).mkdirs();

            LOG.info("🔎 init SimpleSymbolMapper (đọc Aerospike, chỉ đọc)...");
            SimpleSymbolMapper.getInstance().init();

            LOG.info("📥 Load WfoDataset (verify md5) từ {}", dataDir);
            WfoDataset ds = WfoDataset.load(dataDir);
            LOG.info("✅ market={} pred={} funding={}", ds.market.size(), ds.pred.size(), ds.funding.size());

            long start, end;
            String startStr = env("START", null), endStr = env("END", null);
            start = (startStr != null) ? Utils.sdfFile.parse(startStr).getTime() + 7 * Utils.TIME_HOUR : ds.pred.firstKey();
            end = (endStr != null) ? Utils.sdfFile.parse(endStr).getTime() + 7 * Utils.TIME_HOUR : ds.pred.lastKey();
            LOG.info("🗓️ range [{} .. {}] warmup={}d sample={}m", Utils.normalizeDateYYYYMMDD(start),
                    Utils.normalizeDateYYYYMMDD(end), warmupDays, sampleMs / 60_000L);

            new Task128ModelQuality().run(ds, tickerDir, outDir, start, end, warmupDays, sampleMs);
            LOG.info("🎯 DONE");
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("❌ Task128ModelQuality FAIL", e);
            System.exit(1);
        }
    }

    private void run(WfoDataset ds, String tickerDir, String outDir, long start, long end,
                     int warmupDays, long sampleMs) throws Exception {
        HistoryManager hm = HistoryManager.getInstance();
        hm.resetCache();

        long warmupStart = start - (long) warmupDays * Utils.TIME_DAY;
        long dayStart = Utils.getDate(warmupStart);
        long dayEnd = Utils.getDate(end);

        long mktRows = 0, fndRows = 0, daysDone = 0, missTicker = 0;

        try (BufferedWriter mw = new BufferedWriter(new FileWriter(outDir + "/market_realized.csv"));
             BufferedWriter fw = new BufferedWriter(new FileWriter(outDir + "/funding_realized.csv"))) {
            mw.write("ts,pred15,real15,predRisk4H,realDD4H,basketSize"); mw.newLine();
            fw.write("ts,symId,symbol,score,pwin,maxFav24,nBars24,win,complete"); fw.newLine();

            // sliding window: curDay (đang xử lý) + nextDay (future cho label). Cả hai dùng key ĐÃ chuẩn hoá full-USDT.
            TreeMap<Long, Map<String, KlineObjectSimple>> curDay = loadTickerDay(tickerDir, dayStart);
            for (long day = dayStart; day <= dayEnd; day += Utils.TIME_DAY) {
                TreeMap<Long, Map<String, KlineObjectSimple>> nextDay = loadTickerDay(tickerDir, day + Utils.TIME_DAY);
                if (curDay == null) { missTicker++; curDay = nextDay; continue; }

                // lookup cho label = curDay ∪ nextDay (đủ phủ +24h khi tick nằm trong curDay)
                TreeMap<Long, Map<String, KlineObjectSimple>> lookup = new TreeMap<>(curDay);
                if (nextDay != null) lookup.putAll(nextDay);

                for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : curDay.entrySet()) {
                    long ts = e.getKey();
                    Map<String, KlineObjectSimple> snap = e.getValue();
                    hm.updateHistory(snap);                       // warm ring MỖI phút (kể cả warmup)
                    if (ts < start || ts > end) continue;

                    // ---- MARKET ----
                    AiPredictionData pd = ds.pred.get(ts);
                    if (pd != null) {
                        List<String> basket = hm.findPotentialLosers(ts);
                        if (basket != null && !basket.isEmpty()) {
                            float real15 = basketMaxGain(lookup, ts, H15_MS, basket);
                            float realDD4 = basketMaxDrawdown(lookup, ts, H4_MS, basket);
                            mw.write(ts + "," + f(pd.predReturn15M) + "," + f(real15) + ","
                                    + f(pd.predRisk4H) + "," + f(realDD4) + "," + basket.size());
                            mw.newLine();
                            mktRows++;
                        }
                    }

                    // ---- FUNDING (sample theo lưới) ----
                    if (ts % sampleMs == 0) {
                        long[] fp = ds.funding.get(ts);
                        if (fp != null) {
                            for (long enc : fp) {
                                short symId = (short) (enc >> 32);
                                float score = Float.intBitsToFloat((int) enc);
                                String sym = SimpleSymbolMapper.getInstance().getSymbol(symId);
                                float[] mf = maxFav24(lookup, ts, sym);   // [maxFav, nBars]
                                if (mf == null) continue;                 // không có close(t) / không nến future
                                int nBars = (int) mf[1];
                                boolean complete = nBars >= NBARS_24H_FULL;
                                int win = (complete && mf[0] >= WIN) ? 1 : 0;
                                fw.write(ts + "," + symId + "," + sym + "," + f(score) + "," + f(1f - score)
                                        + "," + f(mf[0]) + "," + nBars + "," + win + "," + (complete ? 1 : 0));
                                fw.newLine();
                                fndRows++;
                            }
                        }
                    }
                }
                if (++daysDone % 30 == 0)
                    LOG.info("... {} ngày | {} | mktRows={} fndRows={} missTicker={}",
                            daysDone, Utils.normalizeDateYYYYMMDD(day), mktRows, fndRows, missTicker);
                curDay = nextDay;
            }
        }
        LOG.info("✅ Ghi xong: market_realized={} rows, funding_realized={} rows, missTicker={} ngày",
                mktRows, fndRows, missTicker);
    }

    // ===================== REALIZED (mirror ValidateOldPredictVsRealized — GIỮ NGUYÊN logic) =====================

    /** Trung bình rổ của max((maxPrice−close(t))/close(t)) trên (t, t+horizonMs]. Mirror :189-213. */
    private float basketMaxGain(TreeMap<Long, Map<String, KlineObjectSimple>> data, long ts,
                                long horizonMs, List<String> basket) {
        long end = ts + horizonMs;
        Map<String, KlineObjectSimple> cur = data.get(ts);
        if (cur == null) return 0f;
        Map<String, Float> entry = new HashMap<>();
        for (String s : basket) if (cur.containsKey(s)) entry.put(s, cur.get(s).priceClose);
        NavigableMap<Long, Map<String, KlineObjectSimple>> fut = data.subMap(ts, false, end, true);
        Map<String, Float> maxRet = new HashMap<>();
        for (String s : basket) maxRet.put(s, -999f);
        for (Map<String, KlineObjectSimple> m : fut.values()) {
            for (String s : basket) {
                if (m.containsKey(s) && entry.containsKey(s)) {
                    float e = entry.get(s);
                    if (e > 0) {
                        float r = (m.get(s).maxPrice - e) / e;
                        if (r > maxRet.get(s)) maxRet.put(s, r);
                    }
                }
            }
        }
        float sum = 0; int c = 0;
        for (String s : basket) { float r = maxRet.get(s); if (r != -999f) { sum += r; c++; } }
        return c > 0 ? sum / c : 0f;
    }

    /** Worst trên (t,t+horizonMs] của trung-bình-rổ (minPrice−close(t))/close(t) (kẹp ≥ −1). Mirror :215-240. */
    private float basketMaxDrawdown(TreeMap<Long, Map<String, KlineObjectSimple>> data, long ts,
                                    long horizonMs, List<String> basket) {
        long end = ts + horizonMs;
        NavigableMap<Long, Map<String, KlineObjectSimple>> range = data.subMap(ts, false, end, true);
        Map<String, Float> entry = new HashMap<>();
        Map<String, KlineObjectSimple> cur = data.get(ts);
        if (cur == null) return 0f;
        for (String s : basket) if (cur.containsKey(s) && cur.get(s).priceClose > 1e-7) entry.put(s, cur.get(s).priceClose);
        if (entry.isEmpty()) return 0f;
        float worst = 0f;
        for (Map<String, KlineObjectSimple> m : range.values()) {
            float sum = 0; int c = 0;
            for (String s : entry.keySet()) {
                if (m.containsKey(s)) {
                    float low = m.get(s).minPrice, e = entry.get(s);
                    if (low > 0 && e > 0) {
                        float d = (low - e) / e;
                        if (d < -1) d = -1f;
                        sum += d; c++;
                    }
                }
            }
            if (c > 0) { float avg = sum / c; if (avg < worst) worst = avg; }
        }
        return worst;
    }

    /**
     * maxFav_24h per-coin (mirror ExportFundingLabel định nghĩa maxFav, nhưng entry = close nến 1m TẠI t = phút
     * dự báo, không phải last-close-in-15m-bucket — vì pred sinh per-phút; chênh &lt;15m, đã disclose trong report).
     * Trả {@code [maxFav, nBarsDistinct15m]} hoặc null nếu thiếu close(t)/không nến future.
     */
    private float[] maxFav24(TreeMap<Long, Map<String, KlineObjectSimple>> data, long ts, String sym) {
        Map<String, KlineObjectSimple> cur = data.get(ts);
        if (cur == null) return null;
        KlineObjectSimple k0 = cur.get(sym);
        if (k0 == null || k0.priceClose <= 0 || !Utils.isTickerAvailable(k0)) return null;
        float closeT = k0.priceClose;
        long end = ts + H24_MS;
        NavigableMap<Long, Map<String, KlineObjectSimple>> fut = data.subMap(ts, false, end, true);
        float maxFav = -Float.MAX_VALUE;
        Set<Long> buckets = new HashSet<>();
        long tBucket = ts / BUCKET_MS;
        for (Map.Entry<Long, Map<String, KlineObjectSimple>> me : fut.entrySet()) {
            KlineObjectSimple k = me.getValue().get(sym);
            if (k == null || !Utils.isTickerAvailable(k)) continue;
            float r = (k.maxPrice - closeT) / closeT;
            if (r > maxFav) maxFav = r;
            long b = me.getKey() / BUCKET_MS;
            if (b > tBucket) buckets.add(b);
        }
        if (maxFav == -Float.MAX_VALUE) return null;
        return new float[]{maxFav, buckets.size()};
    }

    // ===================== TICKER FILE LOADER (mirror KaggleDataLoader + chuẩn hoá full-USDT) =====================

    /**
     * Đọc {@code ticker_YYYYMMDD.bin[.gz]} (Java-serialized {@code TreeMap<Long,Map<String,KlineObjectSimple>>}),
     * chuẩn hoá key symbol về full-USDT (mirror {@code loadDailyTickersShort}: endsWith("USDT")?key:key+"USDT")
     * → khớp mapper (funding symbolId dùng full-name). null nếu không có file.
     */
    @SuppressWarnings("unchecked")
    private TreeMap<Long, Map<String, KlineObjectSimple>> loadTickerDay(String dir, long dayTs) {
        String base = dir + "/ticker_" + Utils.sdfFile.format(new Date(dayTs));
        File bin = new File(base + ".bin");
        File gz = new File(base + ".bin.gz");
        try {
            InputStream is;
            if (bin.exists()) is = new BufferedInputStream(new FileInputStream(bin), 1 << 20);
            else if (gz.exists()) is = new BufferedInputStream(new GZIPInputStream(new FileInputStream(gz)), 1 << 20);
            else return null;
            TreeMap<Long, Map<String, KlineObjectSimple>> raw;
            try (ObjectInputStream ois = new ObjectInputStream(is)) {
                raw = (TreeMap<Long, Map<String, KlineObjectSimple>>) ois.readObject();
            }
            if (raw == null) return null;
            TreeMap<Long, Map<String, KlineObjectSimple>> norm = new TreeMap<>();
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : raw.entrySet()) {
                Map<String, KlineObjectSimple> m = new HashMap<>(e.getValue().size() * 2);
                for (Map.Entry<String, KlineObjectSimple> se : e.getValue().entrySet()) {
                    String s = se.getKey();
                    String full = s.endsWith("USDT") ? s : s + "USDT";
                    m.put(full, se.getValue());
                }
                norm.put(e.getKey(), m);
            }
            return norm;
        } catch (Exception ex) {
            LOG.warn("⚠️ load ticker {} lỗi: {}", base, ex.getMessage());
            return null;
        }
    }

    private static String f(float v) {
        if (Float.isNaN(v) || Float.isInfinite(v)) return "";
        return String.format(Locale.US, "%.6f", v);
    }

    private static String env(String k, String def) {
        String v = System.getenv(k);
        return (v == null || v.isEmpty()) ? def : v;
    }
}
