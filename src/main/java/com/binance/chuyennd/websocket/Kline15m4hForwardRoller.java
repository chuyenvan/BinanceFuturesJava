package com.binance.chuyennd.websocket;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import com.google.gson.reflect.TypeToken;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.lang.reflect.Type;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

/**
 * TASK-031 — Forward-rolling nến 15m + 4h cho BTC/ETH trên 242 (live). Nối {@code Aggregate15m4hBtcEth}
 * (TASK-009) vốn chỉ là job HISTORICAL one-shot: thiếu cập nhật realtime nên sau lần chạy hai set
 * {@code kline_15m_btceth}/{@code kline_4h_btceth} đứng yên. Class này là thread chạy TRONG
 * {@link BinanceDataIngestor} (process live trên 242): mỗi phút kiểm; khi một khung 15m/4h vừa ĐÓNG
 * (biên UTC tuyệt đối) → aggregate từ {@code kline_1m_opt} LIVE (242) → ghi khung mới vào record-tháng 242.
 *
 * <p><b>Một bộ não với historical:</b> dùng ĐÚNG quy tắc + format của {@code Aggregate15m4hBtcEth}:
 * biên = {@code floor(epoch/frameMs)*frameMs}; open=1m đầu, high=max(maxPrice), low=min(minPrice),
 * close=1m cuối, vol=Σ totalUsdt; value = {@code Snappy(gson(TreeMap<startMs, float[o,h,l,c,v]>))};
 * key {@code SYMBOL-YYYYMM}. Khung THIẾU phút (&lt; need) → skip (không tạo nến nửa vời). ⇒ gate đọc
 * liền mạch historical + forward.
 *
 * <p><b>Read/Write 242:</b> đọc 1m qua {@link DataManagerAerospikeFloatSim#readDataFromAerospikeCustom}
 * — ở live {@code IS_KAGGLE_MODE=false} nên {@code getReadClient()} = 242. Ghi {@code getClient242()}
 * (append: đọc record-tháng → thêm khung → ghi lại). Chỉ MỘT thread forward nên read-modify-write
 * không race với chính nó.
 *
 * <p><b>An toàn nhịp:</b> chỉ aggregate khung khi {@code now ≥ frameEnd + GRACE} để chắc nến 1m cuối
 * khung đã được ingest ghi xong (tránh đếm thiếu phút do trễ ghi). {@code lastWritten} khởi từ record
 * 242 hiện có (resume sau restart 12h); nếu lệch quá xa (ingest gián đoạn lâu) → nhảy về gần now +
 * cảnh báo (gap lớn để {@code Aggregate15m4hBtcEth} xử, forward chỉ giữ realtime).
 */
public class Kline15m4hForwardRoller {
    private static final Logger LOG = LoggerFactory.getLogger(Kline15m4hForwardRoller.class);

    private static final String[] SYMBOLS = {"BTCUSDT", "ETHUSDT"};
    private static final long MS_15M = 15L * 60_000L, MS_4H = 240L * 60_000L;
    private static final int N_15M = 15, N_4H = 240;
    private static final String SET_15M = "kline_15m_btceth", SET_4H = "kline_4h_btceth";
    private static final Type SERIES_TYPE = new TypeToken<TreeMap<Long, float[]>>() {}.getType();
    /** Đợi nến 1m cuối khung được ingest ghi xong trước khi gom (tránh đếm thiếu phút). */
    private static final long GRACE_MS = 120_000L;
    /** Trần catch-up mỗi interval (số khung) — gap lớn hơn để Aggregate historical xử, không hammer. */
    private static final int MAX_CATCHUP_FRAMES = 200;

    private static final ThreadLocal<java.text.SimpleDateFormat> MONTH =
            ThreadLocal.withInitial(() -> new java.text.SimpleDateFormat("yyyyMM")); // GMT+7 (JVM default)

    /** lastWritten[interval][symbol] = startMs khung mới nhất ĐÃ xử (ghi hoặc skip). null = chưa init. */
    private final Map<String, Map<String, Long>> lastWritten = new HashMap<>();

    /** Cho phép chạy standalone test: 1 vòng roll rồi thoát (KHÔNG loop). Ghi 242 thật → test có chủ đích. */
    public static void main(String[] args) {
        LOG.info("🧪 Kline15m4hForwardRoller TEST: chạy 1 vòng rollOnce rồi thoát (ghi 242 thật).");
        Kline15m4hForwardRoller roller = new Kline15m4hForwardRoller();
        roller.rollOnce(System.currentTimeMillis());
        LOG.info("🧪 TEST xong.");
        System.exit(0);
    }

    /** Khởi thread forward (gọi trong BinanceDataIngestor.main). */
    public void start() {
        new Thread(() -> {
            Thread.currentThread().setName("Kline-Forward-Roller");
            LOG.info("🚀 Khởi động Kline15m4hForwardRoller (15m/4h BTC/ETH → 242, kiểm mỗi phút, grace {}s).",
                    GRACE_MS / 1000);
            while (true) {
                try {
                    Thread.sleep(Utils.TIME_MINUTE);
                    rollOnce(System.currentTimeMillis());
                } catch (InterruptedException ie) {
                    LOG.warn("Kline-Forward-Roller bị interrupt khi sleep: {}", ie.getMessage());
                } catch (Exception e) {
                    LOG.error("❌ Kline-Forward-Roller lỗi vòng roll (bỏ qua nhịp này): {}", e.getMessage(), e);
                }
            }
        }).start();
    }

    /** Một vòng: xử mọi khung đã đóng-và-quá-grace cho cả 15m lẫn 4h, mọi symbol. */
    void rollOnce(long now) {
        rollInterval(SET_15M, MS_15M, N_15M, now);
        rollInterval(SET_4H, MS_4H, N_4H, now);
    }

    private void rollInterval(String set, long frameMs, int need, long now) {
        // Khung "sẵn sàng" mới nhất: fs lớn nhất sao cho fs + frameMs + GRACE ≤ now.
        long latestReady = Math.floorDiv(now - frameMs - GRACE_MS, frameMs) * frameMs;
        Map<String, Long> perSym = lastWritten.computeIfAbsent(set, k -> new HashMap<>());
        for (String symbol : SYMBOLS) {
            try {
                Long last = perSym.get(symbol);
                if (last == null) {
                    last = initLastWritten(set, frameMs, symbol, latestReady);
                    perSym.put(symbol, last);
                }
                if (latestReady <= last) continue; // chưa có khung mới

                long from = last + frameMs;
                long frames = (latestReady - last) / frameMs;
                if (frames > MAX_CATCHUP_FRAMES) {
                    LOG.warn("⚠️ {} {}: gap {} khung > trần {} (ingest gián đoạn lâu?) → nhảy tới gần now; gap lớn dùng Aggregate historical.",
                            set, symbol, frames, MAX_CATCHUP_FRAMES);
                    from = latestReady - (long) (MAX_CATCHUP_FRAMES - 1) * frameMs;
                }
                for (long fs = from; fs <= latestReady; fs += frameMs) {
                    aggregateAndWrite(set, frameMs, need, symbol, fs);
                    perSym.put(symbol, fs); // advance dù ghi hay skip (khung thiếu phút không retry vô hạn)
                }
            } catch (Exception e) {
                LOG.error("❌ {} {} rollInterval lỗi: {}", set, symbol, e.getMessage(), e);
            }
        }
    }

    /**
     * Khởi {@code lastWritten} từ record-tháng 242 hiện có (resume). Không có historical 242 → cảnh báo +
     * bắt đầu từ khung gần nhất (forward chỉ giữ realtime; backfill 242 là việc của Aggregate).
     */
    private long initLastWritten(String set, long frameMs, String symbol, long latestReady) {
        TreeMap<Long, float[]> month = readMonth(set, symbol, latestReady);
        if (month != null && !month.isEmpty()) {
            long lk = month.lastKey();
            LOG.info("↪️ {} {}: resume từ record 242, khung cuối {}.", set, symbol, fmt(lk));
            return lk;
        }
        // Thử tháng trước (latestReady có thể là đầu tháng → record tháng này chưa có).
        TreeMap<Long, float[]> prev = readMonth(set, symbol, latestReady - frameMs);
        if (prev != null && !prev.isEmpty()) {
            long lk = prev.lastKey();
            LOG.info("↪️ {} {}: resume từ record 242 (tháng trước), khung cuối {}.", set, symbol, fmt(lk));
            return Math.max(lk, latestReady - frameMs);
        }
        LOG.warn("⚠️ {} {}: 242 CHƯA có historical (record-tháng rỗng) → forward bắt đầu từ khung gần nhất {}. " +
                "Cần chạy Aggregate15m4hBtcEth (ghi 242) để có historical liền mạch cho gate.", set, symbol, fmt(latestReady));
        return latestReady - frameMs; // sẽ xử đúng khung latestReady ở vòng này
    }

    /** Gom 1m@242 của khung [fs, fs+frameMs) → ghi 242 nếu đủ phút; thiếu → skip + log. */
    private void aggregateAndWrite(String set, long frameMs, int need, String symbol, long fs) {
        TreeMap<Long, Map<String, KlineObjectSimple>> oneMin =
                DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(fs, need);
        long openEpoch = Long.MAX_VALUE, closeEpoch = Long.MIN_VALUE;
        float open = 0f, close = 0f, high = Float.NEGATIVE_INFINITY, low = Float.POSITIVE_INFINITY, vol = 0f;
        int count = 0;
        for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : oneMin.entrySet()) {
            KlineObjectSimple k = e.getValue() == null ? null : e.getValue().get(symbol);
            if (!Utils.isTickerAvailable(k)) continue;
            long epoch = e.getKey();
            if (epoch < openEpoch) { openEpoch = epoch; open = k.priceOpen; }
            if (epoch > closeEpoch) { closeEpoch = epoch; close = k.priceClose; }
            high = Math.max(high, k.maxPrice);
            low = Math.min(low, k.minPrice);
            vol += k.totalUsdt;
            count++;
        }
        if (count != need) {
            LOG.warn("⏭️ {} {} khung {}: thiếu phút ({}/{}) → skip (không tạo nến nửa vời).",
                    set, symbol, fmt(fs), count, need);
            return;
        }
        float[] ohlcv = new float[]{open, high, low, close, vol};
        writeFrame(set, symbol, fs, ohlcv);
        LOG.info("🧱 {} {} khung {}: o={} h={} l={} c={} v={} → 242.",
                set, symbol, fmt(fs), open, high, low, close, vol);
    }

    /** Đọc record-tháng (242) chứa {@code fs}; null nếu chưa có. */
    private TreeMap<Long, float[]> readMonth(String set, String symbol, long fs) {
        try {
            Key key = new Key(Configs.AEROSPIKE_NAMESPACE, set, monthKey(symbol, fs));
            Record r = DataManagerAerospikeFloatSim.getClient242().get(null, key);
            if (r == null) return null;
            byte[] comp = (byte[]) r.getValue("data");
            if (comp == null) return null;
            return Utils.gson.fromJson(new String(Snappy.uncompress(comp), "UTF-8"), SERIES_TYPE);
        } catch (Exception e) {
            LOG.error("❌ readMonth {} {} {} lỗi: {}", set, symbol, fmt(fs), e.getMessage());
            return null;
        }
    }

    /** Append khung {@code fs} vào record-tháng tương ứng trên 242 (read-modify-write, 1 thread forward). */
    private void writeFrame(String set, String symbol, long fs, float[] ohlcv) {
        try {
            TreeMap<Long, float[]> month = readMonth(set, symbol, fs);
            if (month == null) month = new TreeMap<>();
            month.put(fs, ohlcv);
            byte[] comp = Snappy.compress(Utils.gson.toJson(month).getBytes("UTF-8"));
            WritePolicy w = new WritePolicy();
            w.expiration = 0;
            w.sendKey = true;
            w.recordExistsAction = RecordExistsAction.UPDATE;
            AerospikeClient client = DataManagerAerospikeFloatSim.getClient242();
            client.put(w, new Key(Configs.AEROSPIKE_NAMESPACE, set, monthKey(symbol, fs)), new Bin("data", comp));
        } catch (Exception e) {
            LOG.error("❌ writeFrame {} {} {} lỗi: {}", set, symbol, fmt(fs), e.getMessage(), e);
        }
    }

    private static String monthKey(String symbol, long fs) {
        return symbol + "-" + MONTH.get().format(new Date(fs));
    }

    private static String fmt(long ms) {
        return Utils.normalizeDateYYYYMMDDHHmm(ms);
    }
}
