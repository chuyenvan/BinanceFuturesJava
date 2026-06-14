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
 * Ingest Open Interest (forward poll 5') → Aerospike set {@code open_interest} (242).
 * <p>History OI KHÔNG cào ở đây nữa (TASK-023 gỡ {@code startHistoryCrawl}): history → TASK-013
 * (metrics data.binance.vision, đủ từ ~2021-12, cùng đơn vị {@code sumOpenInterestValue}). Tránh tải
 * thừa ~554 call/khởi-động + lệch nguồn trước khi 013 backfill. Class này CHỈ còn forward poll.
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
    /** Sleep giữa mỗi REST call để KHÔNG burst (per-symbol ~554 call). */
    private static final long THROTTLE_MS = 250;
    /** Forward poll mỗi 5 phút (OI đổi chậm). */
    private static final long FORWARD_INTERVAL_MS = 5 * 60 * 1000;

    public static void main(String[] args) {
        new OpenInterestIngestor2AerospikeNew().start();
    }

    public void start() {
        LOG.info("🚀 Khởi động OpenInterestIngestor (forward 5', throttle {}ms/call, qua BinanceRestGuard; history → TASK-013)...", THROTTLE_MS);
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
                            // Cố ý bỏ qua 1 coin để tiếp coin khác, NHƯNG phải log (luật cấm nuốt câm).
                            LOG.warn("⚠️ OI forward bỏ qua symbol {} (lỗi tạm thời): {}", symbol, e.getMessage());
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
