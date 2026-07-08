package com.binance.chuyennd.ai_ml.features.export;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SymbolLifecycleManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.FileWriter;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * TASK-024 (ADR-0011 §5.2) — export FUNDING LABEL = PATH THÔ per-coin (KHÔNG ép nhãn 3-lớp ở đây;
 * triple-barrier X/Y + horizon được QUÉT lúc train, KHÔNG re-export).
 *
 * <p>Đây là H1-DATA của funding (tương đương TASK-012 {@link ExportGateReturn} cho gate). Khác gate ở chỗ
 * gate = AGGREGATE (1 dòng/mốc), funding = PER-COIN (selector "coin NÀO sắp bơm").
 *
 * <p><b>Định nghĩa path (cho mỗi {@code (coin, t)}, với τ là các nến 15m thuộc {@code (t, t+H]}):</b>
 * <ul>
 *   <li>{@code maxFav_H}  = max( high(τ)/close(t) − 1 )  — biên thuận lợi cực đại (đỉnh) trong cửa sổ.</li>
 *   <li>{@code maxAdv_H}  = min( low(τ)/close(t)  − 1 )  — biên bất lợi cực đại (đáy) trong cửa sổ.</li>
 *   <li>{@code tHitFav_H} / {@code tHitAdv_H} = OFFSET (phút) từ t tới lúc chạm đỉnh / đáy đó.</li>
 *   <li>{@code retEnd_H}  = close(t+H)/close(t) − 1 — return close-to-close cuối cửa sổ.</li>
 *   <li>{@code nBars_H}   = số nến 15m THỰC CÓ trong (t, t+H] (đủ = H/15m: 16/48/96/288). Thiếu ⇒ data gap/coin chết.</li>
 * </ul>
 * Lưu tại nhiều mốc H = {4h,12h,24h,72h} (= {16,48,96,288} bước 15m) để train suy được nhiều horizon mà
 * KHÔNG cần re-export. Triple-barrier ở train: chạm +X% trước (tHitFav &lt; tHitAdv) / chạm −Y% trước / hết H.
 *
 * <p><b>Look-ahead (ĐÚNG ranh giới H1):</b> LABEL ĐƯỢC nhìn tương lai — path chỉ dùng nến τ &gt; t tới t+H.
 * close(t) lấy từ nến tại t (đã biết tại t). FEATURE (task sau) mới phải ≤ t. Vì là LABEL nên KHÔNG dính
 * luật chống intrabar look-ahead của backtest ({@code BLOCK_INTRABAR_LOOKAHEAD} — luật đó cho KHỚP LỆNH, không cho nhãn).
 *
 * <p><b>Universe (BẮT BUỘC qua lifecycle — KHÔNG đọc DIED_SYMBOLS):</b> tạo anchor tại (coin, t) chỉ khi
 * {@link SymbolLifecycleManager#isAlive(String, long)} (gồm CẢ coin đã chết, trong khoảng [firstSeen, lastSeen]).
 * ⚠️ Phụ thuộc builder TASK-010 đã chạy. Nếu set {@code symbol_lifecycle} rỗng ({@code loadedCount()==0})
 * ⇒ tool DỪNG ngay (BLOCKED), KHÔNG fallback DIED âm thầm.
 *
 * <p><b>Nhịp sample = 15m</b> (constant {@link #SAMPLE_STEP_MS}; khớp sibling gate TASK-012, đủ mịn cho
 * triple-barrier timing, nhẹ ~15× so với nhịp-1m của export feature cũ). Path bar cũng 15m: gộp 1m→15m
 * (high=max maxPrice, low=min minPrice, close=close nến 1m cuối bucket). Train có thể subsample thêm nếu cần.
 *
 * <p>Nguồn: ticker {@code kline_1m_opt} (226, đọc-only; box cần {@code AEROSPIKE_READ_CLUSTER=226}). Output {@link #OUT}.
 */
public class ExportFundingLabel {

    private static final Logger LOG = LoggerFactory.getLogger(ExportFundingLabel.class);

    /** Nhịp sample anchor + độ rộng 1 nến path (15m). */
    private static final long SAMPLE_STEP_MS = 15L * 60_000L;
    /** Mốc H (bước-15m): 4h,12h,24h,72h. H_MAX = 288 bước. */
    private static final int[] H_STEPS = {16, 48, 96, 288};
    private static final String[] H_NAME = {"4h", "12h", "24h", "72h"};
    private static final int H_MAX = 288;
    private static final String START_DATE = "20210101";
    private static final String OUT = "outputs/funding_label.csv";

    private static final SymbolLifecycleManager LIFECYCLE = SymbolLifecycleManager.getInstance();

    /** Universe = USDT-perp alt (selector chọn alt; loại BTC/ETH = vai market gate, loại BTCDOM/USDC/đa-tài-sản). */
    private static boolean isAlt(String s) {
        return s.endsWith("USDT") && !s.equals("BTCUSDT") && !s.equals("ETHUSDT")
                && !s.contains("_") && !s.contains("USDC") && !s.equals("BTCDOMUSDT");
    }

    /** Trạng thái tích luỹ path của 1 anchor (coin, t). */
    private static final class Anchor {
        final long tStep;          // bucket index = epoch/SAMPLE_STEP_MS của t
        final float closeT;
        float maxFav = -Float.MAX_VALUE;
        float maxAdv = Float.MAX_VALUE;
        int tHitFavStep = 0;       // offset (số bước 15m) tới đỉnh
        int tHitAdvStep = 0;
        int barsSeen = 0;          // số nến THỰC trong cửa sổ tới hiện tại
        // snapshot tại từng H
        final boolean[] snap = new boolean[H_STEPS.length];
        final float[] maxFavH = new float[H_STEPS.length];
        final float[] maxAdvH = new float[H_STEPS.length];
        final int[] tHitFavH = new int[H_STEPS.length];
        final int[] tHitAdvH = new int[H_STEPS.length];
        final float[] retEndH = new float[H_STEPS.length];
        final int[] nBarsH = new int[H_STEPS.length];
        boolean[] retEndSet = new boolean[H_STEPS.length];

        Anchor(long tStep, float closeT) {
            this.tStep = tStep;
            this.closeT = closeT;
        }
    }

    /** Trạng thái streaming per-coin: bucket 15m đang gộp + danh sách anchor đang mở. */
    private static final class CoinState {
        long curBucketIdx = -1;
        float bHi, bLo, bClose;
        final ArrayDeque<Anchor> active = new ArrayDeque<>();
    }

    public static void main(String[] args) {
        try {

            // ===== GUARD universe: builder TASK-010 phải đã chạy =====
            int nLifecycle = LIFECYCLE.loadedCount();
            if (nLifecycle == 0) {
                LOG.error("⛔ BLOCKED: set Aerospike 'symbol_lifecycle' RỖNG (loadedCount=0) ⇒ builder TASK-010 CHƯA chạy. "
                        + "TASK-024 KHÔNG fallback DIED_SYMBOLS âm thầm. Hãy chạy SymbolLifecycleBuilder trên 226 trước, rồi chạy lại.");
                return;
            }
            LOG.info("✅ Lifecycle nạp {} symbol (universe qua isAlive — gồm coin đã chết).", nLifecycle);

            String startStr = args.length > 0 ? args[0] : START_DATE;
            String endStr   = args.length > 1 ? args[1] : null;
            String outPath  = args.length > 2 ? args[2] : OUT;
            long start = Utils.sdfFile.parse(startStr).getTime() + 7 * Utils.TIME_HOUR;
            long end   = (endStr != null) ? Utils.sdfFile.parse(endStr).getTime() + 7 * Utils.TIME_HOUR
                                          : System.currentTimeMillis();
            LOG.info("🏷️ TASK-024 export funding LABEL path-thô per-coin | {} → {} | sample 15m | H={4h,12h,24h,72h}", startStr, (endStr != null ? endStr : "nay"));

            Map<String, CoinState> coins = new HashMap<>();
            FileWriter w = new FileWriter(outPath);
            w.write(header());

            boolean noValidate = "1".equals(System.getenv("NO_VALIDATE"));
            Validate v = new Validate(noValidate);
            if (noValidate) LOG.info("NO_VALIDATE=1 -> bo gom validate (tranh OOM 20M dong).");
            long[] emitted = {0};
            long days = 0;

            for (long day = start; day < end; day += 24L * Utils.TIME_HOUR) {
                TreeMap<Long, Map<String, KlineObjectSimple>> oneDay = DataManagerAerospikeFloatSim.readDataFromAerospike1M(day);
                for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : oneDay.entrySet()) {
                    long epoch = e.getKey();
                    long bucketIdx = epoch / SAMPLE_STEP_MS;
                    for (Map.Entry<String, KlineObjectSimple> se : e.getValue().entrySet()) {
                        String sym = se.getKey();
                        if (!isAlt(sym)) continue;
                        KlineObjectSimple k = se.getValue();
                        if (!Utils.isTickerAvailable(k)) continue;
                        CoinState cs = coins.computeIfAbsent(sym, x -> new CoinState());
                        if (cs.curBucketIdx != bucketIdx) {
                            if (cs.curBucketIdx >= 0) finalizeBucket(cs, sym, w, v, emitted);
                            cs.curBucketIdx = bucketIdx;
                            cs.bHi = k.maxPrice;
                            cs.bLo = k.minPrice;
                            cs.bClose = k.priceClose;
                        } else {
                            if (k.maxPrice > cs.bHi) cs.bHi = k.maxPrice;
                            if (k.minPrice < cs.bLo) cs.bLo = k.minPrice;
                            cs.bClose = k.priceClose;
                        }
                    }
                }
                if (++days % 200 == 0)
                    LOG.info("   ... {} ngày, {}, emitted={}", days, Utils.normalizeDateYYYYMMDD(day), emitted[0]);
            }

            // flush: hoàn tất bucket cuối + emit mọi anchor còn mở (coin chết / cuối dữ liệu → H dài có thể thiếu)
            for (Map.Entry<String, CoinState> ce : coins.entrySet()) {
                CoinState cs = ce.getValue();
                if (cs.curBucketIdx >= 0) finalizeBucket(cs, ce.getKey(), w, v, emitted);
                for (Anchor a : cs.active) emit(a, ce.getKey(), w, v, emitted);
                cs.active.clear();
            }
            w.close();
            LOG.info("✅ Ghi {} dòng → {} | range {} → {} | {} coin trong universe", emitted[0], outPath, startStr, (endStr != null ? endStr : "nay"), coins.size());

            v.report();
        } catch (Exception e) {
            LOG.error("ExportFundingLabel lỗi", e);
            System.exit(1);
        }
        // BẮT BUỘC: DataManagerAerospikeFloatSim giữ ExecutorService non-daemon → main return KHÔNG đủ
        // để JVM thoát (treo). Trên Kaggle = kernel kẹt tới timeout 12h. System.exit để chấm dứt sạch.
        System.exit(0);
    }

    /**
     * Đóng nến 15m hiện tại của coin: feed nó như PATH bar cho mọi anchor đang mở, finalize anchor quá hạn,
     * rồi tạo anchor MỚI tại bucket này (nếu coin còn sống theo lifecycle). Thứ tự đảm bảo anchor mới KHÔNG
     * tự ăn nến của chính nó (path là (t, t+H], không gồm t).
     */
    private static void finalizeBucket(CoinState cs, String sym, FileWriter w, Validate v, long[] emitted) throws Exception {
        long b = cs.curBucketIdx;
        float hi = cs.bHi, lo = cs.bLo, close = cs.bClose;
        // 1) feed bucket cho anchor đang mở
        Iterator<Anchor> it = cs.active.iterator();
        while (it.hasNext()) {
            Anchor a = it.next();
            int o = (int) (b - a.tStep);
            if (o < 1) continue;                 // không xảy ra (bucket tăng dần)
            if (o > H_MAX) {                      // hết cửa sổ → emit & gỡ
                emit(a, sym, w, v, emitted);
                it.remove();
                continue;
            }
            updateAnchor(a, o, hi, lo, close);
        }
        // 2) tạo anchor mới tại t = b (nếu alive theo lifecycle)
        long tEpoch = b * SAMPLE_STEP_MS;
        if (LIFECYCLE.isAlive(sym, tEpoch) && close > 0) {
            cs.active.addLast(new Anchor(b, close));
        }
    }

    /** Cập nhật 1 anchor với 1 nến path tại offset o (bước 15m) trong (t, t+H_MAX]. */
    private static void updateAnchor(Anchor a, int o, float hi, float lo, float close) {
        // (a) xử lý CROSS H mà KHÔNG có nến đúng mốc (gap): snapshot bằng trạng thái TRƯỚC nến này
        //     (retEnd để trống vì không có close đúng mốc t+H)
        for (int h = 0; h < H_STEPS.length; h++) {
            if (!a.snap[h] && o > H_STEPS[h]) snapshot(a, h, Float.NaN);
        }
        // (b) cập nhật running max/min (chỉ trong cửa sổ)
        float favR = hi / a.closeT - 1f;
        float advR = lo / a.closeT - 1f;
        if (favR > a.maxFav) { a.maxFav = favR; a.tHitFavStep = o; }
        if (advR < a.maxAdv) { a.maxAdv = advR; a.tHitAdvStep = o; }
        a.barsSeen++;
        // (c) snapshot tại mốc H ĐÚNG (có nến tại t+H): gồm cả nến này + retEnd close-to-close
        for (int h = 0; h < H_STEPS.length; h++) {
            if (!a.snap[h] && o == H_STEPS[h]) snapshot(a, h, close / a.closeT - 1f);
        }
    }

    /** Chốt snapshot cho mốc H thứ h từ trạng thái running hiện tại. retEnd = NaN ⇒ không có close đúng mốc (gap). */
    private static void snapshot(Anchor a, int h, float retEnd) {
        a.snap[h] = true;
        a.maxFavH[h] = a.maxFav;
        a.maxAdvH[h] = a.maxAdv;
        a.tHitFavH[h] = a.tHitFavStep;
        a.tHitAdvH[h] = a.tHitAdvStep;
        a.nBarsH[h] = a.barsSeen;
        if (!Float.isNaN(retEnd)) { a.retEndH[h] = retEnd; a.retEndSet[h] = true; }
    }

    /** Emit 1 anchor: mốc H nào chưa snapshot (data hết sớm — coin chết/cuối dữ liệu) → chốt incomplete. */
    private static void emit(Anchor a, String sym, FileWriter w, Validate v, long[] emitted) throws Exception {
        if (a.barsSeen == 0) return;   // không có nến tương lai nào (anchor sát cuối tuyệt đối) → bỏ, không 0 giả
        for (int h = 0; h < H_STEPS.length; h++) if (!a.snap[h]) snapshot(a, h, Float.NaN);

        long tEpoch = a.tStep * SAMPLE_STEP_MS;
        StringBuilder sb = new StringBuilder(160);
        sb.append(tEpoch).append(',').append(FMT.get().format(new Date(tEpoch))).append(',').append(sym);
        for (int h = 0; h < H_STEPS.length; h++) {
            sb.append(',').append(f(a.maxFavH[h]))
              .append(',').append(f(a.maxAdvH[h]))
              .append(',').append(a.tHitFavH[h] * 15)
              .append(',').append(a.tHitAdvH[h] * 15)
              .append(',').append(a.retEndSet[h] ? f(a.retEndH[h]) : "")
              .append(',').append(a.nBarsH[h]);
        }
        sb.append('\n');
        w.write(sb.toString());
        emitted[0]++;
        v.collect(sym, tEpoch, a);
    }

    private static String header() {
        StringBuilder h = new StringBuilder("tEpochMs,tDate,symbol");
        for (String n : H_NAME)
            h.append(",maxFav_").append(n).append(",maxAdv_").append(n)
             .append(",tHitFav_").append(n).append(",tHitAdv_").append(n)
             .append(",retEnd_").append(n).append(",nBars_").append(n);
        return h.append('\n').toString();
    }

    private static String f(float val) {
        return (Float.isNaN(val) || val == -Float.MAX_VALUE || val == Float.MAX_VALUE)
                ? "" : String.format(Locale.US, "%.6f", val);
    }

    // ================== VALIDATE (chạy sau export trên 226) ==================

    /**
     * Gom thống kê khi emit + recompute độc lập một số anchor. Mọi kiểm tra theo §Validate của TASK-024:
     * (a) phân bố maxFav/maxAdv theo H/năm; (b) tỉ lệ giả-lập chạm +6%/72h; (c) recompute ~5 (coin,t) đường khác;
     * (d) look-ahead inherent (chỉ nến trong (t,t+H]); (e) bắt coin bơm lịch sử (top maxFav_72h); (f) coin die.
     */
    private static final class Validate {
        final int H72 = H_STEPS.length - 1;    // index mốc 72h
        // (a) phân bố
        final List<Float>[] favAll = lists();
        final List<Float>[] advAll = lists();
        // (a) theo năm cho maxFav_72h
        final Map<Integer, List<Float>> year2fav72 = new TreeMap<>();
        // (b) hit +6%/72h (chỉ trên nBars_72h đủ)
        long hit6 = 0, complete72 = 0;
        // (e) top pump
        final TreeMap<Float, String> topPump = new TreeMap<>();
        // (f) coin die
        long incomplete72 = 0;
        final Set<String> deadSyms = new TreeSet<>();
        // (c) recompute: bắt vài anchor 72h-đủ để đọc lại đường khác
        final List<long[]> watch = new ArrayList<>();   // {tEpoch, tStep} ; sym ở watchSym
        final List<String> watchSym = new ArrayList<>();
        final List<float[]> watchExp = new ArrayList<>(); // {maxFav72, maxAdv72, retEnd72}

        @SuppressWarnings("unchecked")
        private static List<Float>[] lists() {
            List<Float>[] a = new List[H_STEPS.length];
            for (int i = 0; i < a.length; i++) a[i] = new ArrayList<>();
            return a;
        }

        final boolean disabled;
        Validate(boolean disabled) { this.disabled = disabled; }
        void collect(String sym, long tEpoch, Anchor a) {
            if (disabled) return;
            for (int h = 0; h < H_STEPS.length; h++) {
                if (a.maxFavH[h] != -Float.MAX_VALUE) favAll[h].add(a.maxFavH[h]);
                if (a.maxAdvH[h] != Float.MAX_VALUE) advAll[h].add(a.maxAdvH[h]);
            }
            int y = year(tEpoch);
            if (a.maxFavH[H72] != -Float.MAX_VALUE)
                year2fav72.computeIfAbsent(y, x -> new ArrayList<>()).add(a.maxFavH[H72]);

            boolean full72 = a.nBarsH[H72] >= H_STEPS[H72];
            if (full72) {
                complete72++;
                if (a.maxFavH[H72] >= 0.06f) hit6++;
                // (e) top pump
                if (a.maxFavH[H72] != -Float.MAX_VALUE) {
                    topPump.put(a.maxFavH[H72], sym + "@" + FMT.get().format(new Date(tEpoch)));
                    if (topPump.size() > 20) topPump.remove(topPump.firstKey());
                }
                // (c) bắt 5 anchor đầu đủ-72h để recompute
                if (watch.size() < 5) {
                    watch.add(new long[]{tEpoch, a.tStep});
                    watchSym.add(sym);
                    watchExp.add(new float[]{a.maxFavH[H72], a.maxAdvH[H72], a.retEndSet[H72] ? a.retEndH[H72] : Float.NaN});
                }
            } else {
                incomplete72++;
                if (a.nBarsH[H72] < H_STEPS[H72]) deadSyms.add(sym);
            }
        }

        void report() throws Exception {
            if (disabled) return;
            LOG.info("=== (a) PHÂN BỐ maxFav/maxAdv mỗi H (p1/p5/p50/p95/p99) ===");
            for (int h = 0; h < H_STEPS.length; h++) {
                List<Float> fv = favAll[h], ad = advAll[h];
                Collections.sort(fv); Collections.sort(ad);
                LOG.info("  {} maxFav: n={} p1={} p5={} p50={} p95={} p99={}", H_NAME[h], fv.size(),
                        pc(fv, 1), pc(fv, 5), pc(fv, 50), pc(fv, 95), pc(fv, 99));
                LOG.info("  {} maxAdv: n={} p1={} p5={} p50={} p95={} p99={}", H_NAME[h], ad.size(),
                        pc(ad, 1), pc(ad, 5), pc(ad, 50), pc(ad, 95), pc(ad, 99));
            }
            LOG.info("=== (a') maxFav_72h theo NĂM (p50/p95 | #(≥+6%)) ===");
            for (Map.Entry<Integer, List<Float>> e : year2fav72.entrySet()) {
                List<Float> r = e.getValue(); Collections.sort(r);
                long h6 = r.stream().filter(x -> x >= 0.06f).count();
                LOG.info("  {}: n={} p50={} p95={} #(≥6%)={} ({}%)", e.getKey(), r.size(),
                        pc(r, 50), pc(r, 95), h6, r.isEmpty() ? 0 : String.format(Locale.US, "%.1f", 100.0 * h6 / r.size()));
            }
            LOG.info("=== (b) TỈ LỆ giả-lập chạm +6% trong 72h (trên nBars_72h ĐỦ) = {}/{} = {}% (đối chiếu trực giác label cũ) ===",
                    hit6, complete72, complete72 == 0 ? 0 : String.format(Locale.US, "%.2f", 100.0 * hit6 / complete72));

            LOG.info("=== (c) RECOMPUTE độc lập 72h (đọc lại window 1m→15m đường khác) ===");
            for (int i = 0; i < watch.size(); i++) {
                long tEpoch = watch.get(i)[0];
                String sym = watchSym.get(i);
                float[] exp = watchExp.get(i);
                float[] re = recompute72(sym, tEpoch);
                boolean okF = re != null && Math.abs(re[0] - exp[0]) < 1e-4;
                boolean okA = re != null && Math.abs(re[1] - exp[1]) < 1e-4;
                LOG.info("  {} t={} : maxFav export={} recompute={} {} | maxAdv export={} recompute={} {}",
                        sym, FMT.get().format(new Date(tEpoch)),
                        f(exp[0]), re == null ? "null" : f(re[0]), okF ? "KHỚP✅" : "LỆCH🔴",
                        f(exp[1]), re == null ? "null" : f(re[1]), okA ? "KHỚP✅" : "LỆCH🔴");
            }

            LOG.info("=== (d) LOOK-AHEAD: path chỉ dùng nến (t, t+H]; (coin,t) thiếu data tới t+H giữ nBars thiếu (KHÔNG 0 giả), train lọc. ===");

            LOG.info("=== (e) BẮT COIN BƠM (top-20 maxFav_72h — kỳ vọng đúng đợt bơm lịch sử) ===");
            for (Map.Entry<Float, String> e : topPump.descendingMap().entrySet())
                LOG.info("   maxFav_72h={} : {}", f(e.getKey()), e.getValue());

            LOG.info("=== (f) COIN DIE / data dừng: {} dòng nBars_72h THIẾU; {} coin chạm cảnh thiếu-data ===",
                    incomplete72, deadSyms.size());
            int shown = 0;
            for (String s : deadSyms) {
                LOG.info("   coin thiếu-data tới 72h: {} (status lifecycle={})", s, LIFECYCLE.getStatus(s));
                if (++shown >= 15) break;
            }
        }

        /**
         * Recompute độc lập maxFav/maxAdv_72h bằng ĐƯỜNG KHÁC: đọc lại 1m từ t, gộp 15m, tính trực tiếp.
         * Khớp định nghĩa chính: {@code close(t)} = close nến 1m CUỐI trong bucket t; path = bucket (tBucket, tBucket+288].
         */
        private float[] recompute72(String sym, long tEpoch) throws Exception {
            long tBucket = tEpoch / SAMPLE_STEP_MS;
            int minutes = (H_MAX + 1) * 15 + 5;   // đủ bucket t + 288 bucket sau
            TreeMap<Long, Map<String, KlineObjectSimple>> win =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(tEpoch, minutes);
            if (win == null || win.isEmpty()) return null;
            // gộp 15m: idx -> {hi, lo, lastClose, lastTs}; lastClose chốt theo ts lớn nhất trong bucket
            Map<Long, float[]> bucket = new TreeMap<>();
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : win.entrySet()) {
                long ep = e.getKey();
                long idx = ep / SAMPLE_STEP_MS;
                if (idx < tBucket || idx > tBucket + H_MAX) continue;
                KlineObjectSimple k = e.getValue().get(sym);
                if (k == null || !Utils.isTickerAvailable(k)) continue;
                float[] b = bucket.computeIfAbsent(idx, x -> new float[]{-Float.MAX_VALUE, Float.MAX_VALUE, 0f, -1f});
                if (k.maxPrice > b[0]) b[0] = k.maxPrice;
                if (k.minPrice < b[1]) b[1] = k.minPrice;
                if (ep > b[3]) { b[3] = ep; b[2] = k.priceClose; }
            }
            float[] bt = bucket.get(tBucket);
            if (bt == null || bt[2] <= 0) return null;
            float closeT = bt[2];
            float maxFav = -Float.MAX_VALUE, maxAdv = Float.MAX_VALUE;
            for (Map.Entry<Long, float[]> e : bucket.entrySet()) {
                if (e.getKey() <= tBucket) continue;   // path chỉ (t, t+H]
                float[] b = e.getValue();
                float favR = b[0] / closeT - 1f, advR = b[1] / closeT - 1f;
                if (favR > maxFav) maxFav = favR;
                if (advR < maxAdv) maxAdv = advR;
            }
            return new float[]{maxFav, maxAdv};
        }
    }

    private static String pc(List<Float> sorted, int p) {
        if (sorted.isEmpty()) return "-";
        int idx = Math.min(sorted.size() - 1, (int) Math.ceil(p / 100.0 * sorted.size()) - 1);
        if (idx < 0) idx = 0;
        return String.format(Locale.US, "%.4f", sorted.get(idx));
    }

    private static final ThreadLocal<SimpleDateFormat> FMT =
            ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyyMMdd-HHmm")); // GMT+7

    private static int year(long ms) { return Integer.parseInt(new SimpleDateFormat("yyyy").format(new Date(ms))); }
}
