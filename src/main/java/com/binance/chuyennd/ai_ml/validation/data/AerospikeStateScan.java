package com.binance.chuyennd.ai_ml.validation.data;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.ScanPolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import com.google.gson.reflect.TypeToken;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.lang.reflect.Type;
import java.text.SimpleDateFormat;
import java.util.Map;
import java.util.TimeZone;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * TASK-023 Phần 2 — Tool ĐỌC-ONLY dump trạng thái thực các set Aerospike để Desktop reconcile
 * (recon 021 không đo được từ máy dev: 242 firewall + không có CLI). Chạy <b>TRÊN 226</b> (226 thấy
 * cả 242). KHÔNG ghi/sửa bất kỳ set nào — chỉ {@code scanAll} đếm + {@code get} vài symbol lấy ts cuối.
 * <p>Báo cáo cho mỗi client (242 LIVE + 226 BACKTEST):
 * <ul>
 *   <li>{@code funding_data} (019): ts funding mới nhất BTC/ETH so với now (live tươi không).</li>
 *   <li>{@code open_interest} (007-C/013): #record + ts mới nhất BTC/ETH (forward poll ghi gì).</li>
 *   <li>{@code kline_15m_btceth}/{@code kline_4h_btceth} (009): #record + startMs cuối BTCUSDT
 *       (forward-rolling đã bật chưa — ts có vượt 2026-06-07 không).</li>
 *   <li>{@code symbol_lifecycle} (010): #record + breakdown status (builder chạy chưa — kỳ vọng rỗng).</li>
 * </ul>
 * <p>Mỗi section bọc try/catch riêng: nếu 1 client không kết nối được (vd chạy từ dev → 242 timeout)
 * thì vẫn in được phần client kia. Mốc thời gian in theo GMT+7 (chuẩn hệ thống).
 */
public class AerospikeStateScan {
    private static final Logger LOG = LoggerFactory.getLogger(AerospikeStateScan.class);

    private static final String SET_FUNDING = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_FUNDINGFEE; // funding_data
    private static final String SET_OI = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_OPEN_INTEREST;    // open_interest
    private static final String SET_15M = "kline_15m_btceth";
    private static final String SET_4H = "kline_4h_btceth";
    private static final String SET_LIFECYCLE = "symbol_lifecycle";
    private static final String NS = Configs.AEROSPIKE_NAMESPACE;

    private static final Type MAP_SF = new TypeToken<Map<String, Float>>() {}.getType();
    private static final Type MAP_KLINE = new TypeToken<TreeMap<Long, float[]>>() {}.getType();

    private static final ThreadLocal<SimpleDateFormat> SDF = ThreadLocal.withInitial(() -> {
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd HH:mm");
        f.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        return f;
    });

    public static void main(String[] args) {
        long now = System.currentTimeMillis();
        LOG.info("================ AEROSPIKE STATE SCAN (TASK-023 P2, đọc-only) ================");
        LOG.info("now (GMT+7) = {}", fmt(now));

        scanClient("242-LIVE", safeClient(true), now);
        scanClient("226-BACKTEST", safeClient(false), now);

        LOG.info("================ HẾT — copy số vào docs/STATUS_RECON.md §5 ================");
    }

    /** Lấy client; bọc try/catch để lỗi kết nối 1 host không chặn host kia. */
    private static AerospikeClient safeClient(boolean is242) {
        try {
            return is242 ? DataManagerAerospikeFloatSim.getClient242() : DataManagerAerospikeFloatSim.getClient226();
        } catch (Exception e) {
            LOG.error("❌ Không tạo được client {}: {}", is242 ? "242" : "226", e.getMessage());
            return null;
        }
    }

    private static void scanClient(String label, AerospikeClient client, long now) {
        LOG.info("---------------- [{}] ----------------", label);
        if (client == null) {
            LOG.warn("[{}] client null → bỏ qua (xem lỗi kết nối ở trên).", label);
            return;
        }

        // 019 — funding_data
        try {
            tsReport(label, "funding_data(019)", client, SET_FUNDING, "f_data", "BTCUSDT", now);
            tsReport(label, "funding_data(019)", client, SET_FUNDING, "f_data", "ETHUSDT", now);
        } catch (Exception e) {
            LOG.error("[{}] funding_data lỗi: {}", label, e.getMessage());
        }

        // 007-C/013 — open_interest
        try {
            int oiCount = countSet(client, SET_OI);
            LOG.info("[{}] open_interest(013/007-C): #record = {}", label, oiCount);
            tsReport(label, "open_interest", client, SET_OI, "oi_data", "BTCUSDT", now);
            tsReport(label, "open_interest", client, SET_OI, "oi_data", "ETHUSDT", now);
        } catch (Exception e) {
            LOG.error("[{}] open_interest lỗi: {}", label, e.getMessage());
        }

        // 009 — kline 15m / 4h
        klineReport(label, client, SET_15M, now);
        klineReport(label, client, SET_4H, now);

        // 010 — symbol_lifecycle
        try {
            AtomicInteger total = new AtomicInteger(), live = new AtomicInteger(),
                    incomplete = new AtomicInteger(), dead = new AtomicInteger(), other = new AtomicInteger();
            ScanPolicy sp = new ScanPolicy();
            client.scanAll(sp, NS, SET_LIFECYCLE, (key, rec) -> {
                total.incrementAndGet();
                String st = rec.getString("status");
                if (st == null) other.incrementAndGet();
                else if (st.contains("LIVE")) live.incrementAndGet();
                else if (st.contains("INCOMPLETE")) incomplete.incrementAndGet();
                else if (st.contains("DEAD")) dead.incrementAndGet();
                else other.incrementAndGet();
            });
            LOG.info("[{}] symbol_lifecycle(010): #record = {} (LIVE={} DATA_INCOMPLETE={} DEAD={} other={}){}",
                    label, total.get(), live.get(), incomplete.get(), dead.get(), other.get(),
                    total.get() == 0 ? " → RỖNG (builder TASK-010 CHƯA chạy)" : "");
        } catch (Exception e) {
            LOG.error("[{}] symbol_lifecycle lỗi: {}", label, e.getMessage());
        }
    }

    /** Đọc 1 record map<ts,val> (Snappy+gson) → in ts cuối + tuổi so now. */
    private static void tsReport(String label, String tag, AerospikeClient client, String set, String bin,
                                 String symbol, long now) {
        try {
            Record rec = client.get(null, new Key(NS, set, symbol));
            if (rec == null) {
                LOG.info("[{}] {} {}: KHÔNG có record.", label, tag, symbol);
                return;
            }
            byte[] comp = (byte[]) rec.getValue(bin);
            if (comp == null) {
                LOG.info("[{}] {} {}: record có nhưng bin {} null.", label, tag, symbol, bin);
                return;
            }
            String json = new String(Snappy.uncompress(comp), "UTF-8");
            Map<String, Float> map = Utils.gson.fromJson(json, MAP_SF);
            if (map == null || map.isEmpty()) {
                LOG.info("[{}] {} {}: map RỖNG.", label, tag, symbol);
                return;
            }
            long last = Long.MIN_VALUE;
            for (String k : map.keySet()) last = Math.max(last, Long.parseLong(k));
            LOG.info("[{}] {} {}: #điểm={} · ts-cuối={} (cách now {}).",
                    label, tag, symbol, map.size(), fmt(last), age(now - last));
        } catch (Exception e) {
            LOG.error("[{}] {} {} lỗi đọc: {}", label, tag, symbol, e.getMessage());
        }
    }

    /** kline set: đếm record + đọc BTCUSDT các key tháng, lấy startMs cuối cùng. */
    private static void klineReport(String label, AerospikeClient client, String set, long now) {
        try {
            AtomicInteger count = new AtomicInteger();
            long[] maxStartHolder = {Long.MIN_VALUE};
            ScanPolicy sp = new ScanPolicy();
            sp.includeBinData = true;
            client.scanAll(sp, NS, set, (key, rec) -> {
                count.incrementAndGet();
                // chỉ giải nén key BTCUSDT-* để lấy startMs cuối (tránh giải nén toàn bộ)
                Object userKey = key.userKey == null ? null : key.userKey.getObject();
                String ks = userKey == null ? null : userKey.toString();
                if (ks != null && ks.startsWith("BTCUSDT-")) {
                    try {
                        byte[] comp = (byte[]) rec.getValue("data");
                        if (comp != null) {
                            String json = new String(Snappy.uncompress(comp), "UTF-8");
                            TreeMap<Long, float[]> series = Utils.gson.fromJson(json, MAP_KLINE);
                            if (series != null && !series.isEmpty()) {
                                synchronized (maxStartHolder) {
                                    maxStartHolder[0] = Math.max(maxStartHolder[0], series.lastKey());
                                }
                            }
                        }
                    } catch (Exception ex) {
                        LOG.warn("[{}] {} giải nén key {} lỗi: {}", label, set, ks, ex.getMessage());
                    }
                }
            });
            String tail = maxStartHolder[0] == Long.MIN_VALUE
                    ? "BTCUSDT không có record"
                    : "BTCUSDT startMs-cuối=" + fmt(maxStartHolder[0]) + " (cách now " + age(now - maxStartHolder[0]) + ")";
            LOG.info("[{}] {}(009): #record(key-tháng)={} · {}", label, set, count.get(), tail);
        } catch (Exception e) {
            LOG.error("[{}] {} lỗi: {}", label, set, e.getMessage());
        }
    }

    private static int countSet(AerospikeClient client, String set) {
        AtomicInteger c = new AtomicInteger();
        ScanPolicy sp = new ScanPolicy();
        sp.includeBinData = false;
        client.scanAll(sp, NS, set, (key, rec) -> c.incrementAndGet());
        return c.get();
    }

    private static String fmt(long ms) {
        return SDF.get().format(new java.util.Date(ms));
    }

    /** ms → "Nd Hh Mm" gọn. */
    private static String age(long ms) {
        if (ms < 0) return "tương lai?";
        long m = ms / 60000, h = m / 60, d = h / 24;
        if (d > 0) return d + "d " + (h % 24) + "h";
        if (h > 0) return h + "h " + (m % 60) + "m";
        return m + "m";
    }
}
