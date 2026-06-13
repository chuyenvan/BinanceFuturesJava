package com.binance.chuyennd.websocket;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.BinanceRestGuard;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Ingest Open Interest (forward poll + cào history ~30 ngày) → Aerospike set {@code open_interest} (242).
 * <p>OI KHÔNG có endpoint toàn-sàn nên BẮT BUỘC gọi PER-SYMBOL (~554 calls) → burst → góp phần ban.
 * Do đó class này gọi TUẦN TỰ + throttle + qua {@link BinanceRestGuard} (dùng chung cooldown ban với
 * ticker/funding) — KHÁC hẳn kline (ForkJoinPool 30 luồng). Value lưu = {@code sumOpenInterestValue}
 * (USD notional, chuẩn hoá cross-coin tốt hơn số hợp đồng).
 * <p>Dùng {@code HttpRequest.getContentFromUrl} (không qua OkHttp client) để body lỗi -1003 đi thẳng
 * vào {@link BinanceRestGuard#reportBan(String)} như các ingester khác. Endpoint
 * {@code /futures/data/openInterestHist} là public (không cần ký).
 */
public class OpenInterestIngestor2AerospikeNew {
    private static final Logger LOG = LoggerFactory.getLogger(OpenInterestIngestor2AerospikeNew.class);

    private static final String OI_HIST_ENDPOINT = "https://fapi.binance.com/futures/data/openInterestHist";
    /** OI hist Binance CHỈ giữ ~30 ngày gần nhất. */
    private static final long HISTORY_LOOKBACK_MS = 30L * 24 * 60 * 60 * 1000;
    /** Sleep giữa mỗi REST call để KHÔNG burst (per-symbol ~554 call). */
    private static final long THROTTLE_MS = 250;
    /** Forward poll mỗi 5 phút (OI đổi chậm). */
    private static final long FORWARD_INTERVAL_MS = 5 * 60 * 1000;
    private static final int PAGE_LIMIT = 500;

    public static void main(String[] args) {
        new OpenInterestIngestor2AerospikeNew().start();
    }

    public void start() {
        LOG.info("🚀 Khởi động OpenInterestIngestor (forward 5' + cào history ~30 ngày, throttle {}ms/call, qua BinanceRestGuard)...", THROTTLE_MS);
        startHistoryCrawl();
        startForwardLoop();
    }

    /** Đọc danh sách symbol USDT còn sống từ Redis (giống TickerIngestor). */
    private List<String> collectSymbols() {
        List<String> symbols = new ArrayList<>();
        Set<String> redisData = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
        for (String s : redisData) {
            String upperS = s.toUpperCase();
            if (!Constants.diedSymbol.contains(upperS) && upperS.endsWith("USDT") && upperS.matches("^[A-Z0-9]+$")) {
                symbols.add(upperS);
            }
        }
        return symbols;
    }

    /** Cào history ~30 ngày MỘT LẦN lúc start (period 15m, page lùi theo endTime). Thread riêng. */
    private void startHistoryCrawl() {
        new Thread(() -> {
            Thread.currentThread().setName("OI-History-Crawl");
            try {
                List<String> symbols = collectSymbols();
                long boundary = System.currentTimeMillis() - HISTORY_LOOKBACK_MS;
                LOG.info("📥 OI history: bắt đầu cào {} symbol (period=15m, lùi ~30 ngày).", symbols.size());
                int done = 0, withData = 0;
                for (String symbol : symbols) {
                    Map<Long, Float> hist = crawlHistoryForSymbol(symbol, boundary);
                    if (!hist.isEmpty()) {
                        DataManagerAerospikeFloatSim.writeOpenInterestMap(symbol, hist);
                        withData++;
                    }
                    done++;
                    if (done % 50 == 0) {
                        LOG.info("📥 OI history tiến độ: {}/{} symbol (có data: {}).", done, symbols.size(), withData);
                    }
                }
                LOG.info("✅ OI history XONG: {}/{} symbol có data.", withData, symbols.size());
            } catch (Exception e) {
                LOG.error("❌ OI history crawl lỗi: {}", e.getMessage());
            }
        }).start();
    }

    /**
     * Cào toàn bộ history khả dụng của 1 symbol (lùi tới {@code boundary}) qua nhiều trang.
     *
     * @param symbol   symbol.
     * @param boundary mốc ms-epoch dừng (không lấy cũ hơn).
     * @return map ts → OI notional (USD).
     */
    private Map<Long, Float> crawlHistoryForSymbol(String symbol, long boundary) {
        Map<Long, Float> result = new HashMap<>();
        long endTime = System.currentTimeMillis();
        try {
            while (true) {
                if (BinanceRestGuard.awaitIfBanned(60_000L)) continue; // đang ban → chờ rồi tái kiểm

                String url = OI_HIST_ENDPOINT + "?symbol=" + symbol + "&period=15m&limit=" + PAGE_LIMIT + "&endTime=" + endTime;
                String response = HttpRequest.getContentFromUrl(url, 5000);
                BinanceRestGuard.reportBan(response);
                if (BinanceRestGuard.isBanned()) continue; // body báo ban → quay lại chờ

                if (StringUtils.isBlank(response) || !response.trim().startsWith("[")) break;
                JSONArray arr = new JSONArray(response);
                if (arr.length() == 0) break;

                long minTs = Long.MAX_VALUE;
                for (int i = 0; i < arr.length(); i++) {
                    JSONObject o = arr.getJSONObject(i);
                    long ts = o.getLong("timestamp");
                    float val = (float) o.getDouble("sumOpenInterestValue");
                    result.put(ts, val);
                    if (ts < minTs) minTs = ts;
                }

                // Đã chạm/qua mốc giới hạn, hoặc trang chưa đầy (hết data) → dừng.
                if (minTs <= boundary || arr.length() < PAGE_LIMIT) break;
                endTime = minTs - 1;
                Thread.sleep(THROTTLE_MS);
            }
        } catch (Exception e) {
            LOG.error("❌ OI history {} lỗi: {}", symbol, e.getMessage());
        }
        return result;
    }

    /** Forward poll mỗi 5 phút: period=5m limit=1 cho từng symbol (tuần tự + throttle), flush per-symbol. */
    private void startForwardLoop() {
        new Thread(() -> {
            Thread.currentThread().setName("OI-Forward-Loop");
            while (true) {
                long sweepStart = System.currentTimeMillis();
                try {
                    List<String> symbols = collectSymbols();
                    int written = 0;
                    for (String symbol : symbols) {
                        try {
                            if (BinanceRestGuard.awaitIfBanned(60_000L)) {
                                // đang ban: bỏ qua phần còn lại của sweep, chờ vòng sau.
                                break;
                            }
                            String url = OI_HIST_ENDPOINT + "?symbol=" + symbol + "&period=5m&limit=1";
                            String response = HttpRequest.getContentFromUrl(url, 5000);
                            BinanceRestGuard.reportBan(response);
                            if (BinanceRestGuard.isBanned()) break;

                            if (StringUtils.isNotBlank(response) && response.trim().startsWith("[")) {
                                JSONArray arr = new JSONArray(response);
                                if (arr.length() > 0) {
                                    JSONObject o = arr.getJSONObject(arr.length() - 1);
                                    Map<Long, Float> one = new HashMap<>();
                                    one.put(o.getLong("timestamp"), (float) o.getDouble("sumOpenInterestValue"));
                                    DataManagerAerospikeFloatSim.writeOpenInterestMap(symbol, one);
                                    written++;
                                }
                            }
                            Thread.sleep(THROTTLE_MS);
                        } catch (Exception e) {
                            // bỏ qua lỗi 1 coin, tiếp coin khác
                        }
                    }
                    LOG.info("✅ OI forward: cập nhật {} symbol.", written);
                } catch (Exception e) {
                    LOG.error("❌ OI forward sweep lỗi: {}", e.getMessage());
                }

                // Ngủ phần còn lại cho đủ chu kỳ 5'.
                long elapsed = System.currentTimeMillis() - sweepStart;
                long sleep = FORWARD_INTERVAL_MS - elapsed;
                if (sleep < 1000) sleep = 1000;
                try {
                    Thread.sleep(sleep);
                } catch (InterruptedException ignored) {
                }
            }
        }).start();
    }
}
