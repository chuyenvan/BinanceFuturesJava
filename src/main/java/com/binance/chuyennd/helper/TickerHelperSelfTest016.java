package com.binance.chuyennd.helper;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.BinanceRestGuard;
import com.binance.chuyennd.utils.HttpRequest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;

/**
 * TASK-016 SELF-TEST — kiểm KỸ hành vi API + fix limit/-1130/-1003.
 * Chạy từ IP LOCAL (cô lập, KHÔNG đụng rate-budget của 242 live). KHÔNG deploy.
 *
 * 2 phần:
 *  (1) PROBE API THẬT: raw-GET fapi với limit ∈ {0,1,500,1500,1501,2000} để xác định boundary -1130;
 *      + helper clamp (limit 2000→1500, limit 0 không gọi API).
 *  (2) UNIT phân loại code (pure, không API): parseBanUntilMs cho -1130/-1003-rate/-1003-banned/-1121/array.
 */
public class TickerHelperSelfTest016 {

    private static final Logger LOG = LoggerFactory.getLogger(TickerHelperSelfTest016.class);
    private static final String SYM = "ADAUSDT";   // coin chuẩn (task: ADAUSDT dính -1130 → kiểm trực tiếp)
    private static int pass = 0, fail = 0;

    public static void main(String[] args) {
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);   // sạch trước probe
        long startTime = (System.currentTimeMillis() - 2L * 24 * 3600_000L) / 60000L * 60000L; // 2 ngày trước, phút-aligned

        LOG.info("================ (1) PROBE API THẬT (fapi, IP local) ================");
        // raw-GET trực tiếp (bỏ qua helper) để thấy Binance trả gì cho từng limit
        for (int lim : new int[]{0, 1, 500, 1500, 1501, 2000}) {
            String url = "https://fapi.binance.com/fapi/v1/klines?symbol=" + SYM + "&interval=1m&startTime=" + startTime + "&limit=" + lim;
            String resp = safe(url);
            String head = resp == null ? "null" : (resp.length() > 120 ? resp.substring(0, 120) : resp);
            boolean isArr = resp != null && resp.trim().startsWith("[");
            boolean is1130 = resp != null && resp.contains("-1130");
            LOG.info("  raw limit={} → {} {} | {}", lim, isArr ? "ARRAY(ok)" : "OBJ/err", is1130 ? "[-1130]" : "", head);
            sleepQuiet(400);
        }

        LOG.info("---- helper (có clamp [1,1500]) ----");
        // limit=0 → KHÔNG gọi API, trả rỗng (test guard, gần như tức thì)
        long t0 = System.currentTimeMillis();
        List<KlineObjectSimple> r0 = TickerFuturesHelper.getTickerSimpleWithStartTimeAndLimit(SYM, "1m", startTime, 0);
        check("helper limit=0 → rỗng & KHÔNG gọi API", r0.isEmpty() && (System.currentTimeMillis() - t0) < 200);

        List<KlineObjectSimple> r500 = TickerFuturesHelper.getTickerSimpleWithStartTimeAndLimit(SYM, "1m", startTime, 500);
        check("helper limit=500 → ~500 nến (caller live truyền 500 HỢP LỆ)", r500.size() >= 400 && r500.size() <= 500);
        sleepQuiet(400);

        List<KlineObjectSimple> r2000 = TickerFuturesHelper.getTickerSimpleWithStartTimeAndLimit(SYM, "1m", startTime, 2000);
        check("helper limit=2000 → clamp 1500, ≤1500 nến, KHÔNG -1130", !r2000.isEmpty() && r2000.size() <= 1500);

        LOG.info("================ (2) UNIT phân loại code (parseBanUntilMs, pure) ================");
        long now = System.currentTimeMillis();
        // -1130 → KHÔNG cooldown
        check("-1130 → 0 (không cooldown)",
                BinanceRestGuard.parseBanUntilMs("{\"code\":-1130,\"msg\":\"Data sent for parameter 'limit' is not valid.\"}") == 0);
        // -1003 rate (chưa banned-until) → backoff NGẮN ~8s
        long b = BinanceRestGuard.parseBanUntilMs("{\"code\":-1003,\"msg\":\"Too many requests; current limit of IP(1.2.3.4) is 2400 requests per minute.\"}");
        check("-1003 rate → backoff ngắn (~8s, KHÔNG 5')", b > now && b <= now + BinanceRestGuard.RATE_BACKOFF_MS + 1000
                && b < now + 60_000);
        // -1003 kèm banned until <ms> → đúng mốc
        long banUntil = now + 3_600_000L;
        check("-1003 banned until <ms> → đúng mốc",
                BinanceRestGuard.parseBanUntilMs("{\"code\":-1003,\"msg\":\"...IP banned until " + banUntil + ". Please...\"}") == banUntil);
        // -1121 delist / mã khác → KHÔNG cooldown
        check("-1121 (delist) → 0",
                BinanceRestGuard.parseBanUntilMs("{\"code\":-1121,\"msg\":\"Invalid symbol.\"}") == 0);
        // mảng giá bình thường → 0
        check("array hợp lệ → 0",
                BinanceRestGuard.parseBanUntilMs("[[1609459200000,\"1.0\",\"1.1\",\"0.9\",\"1.05\",\"100\"]]") == 0);

        // reportBan: -1003-rate đặt cooldown ngắn rồi tự hết
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
        BinanceRestGuard.reportBan("{\"code\":-1003,\"msg\":\"Too many requests; current limit ... 2400 per minute\"}");
        check("reportBan(-1003-rate) → isBanned()=true (cooldown ngắn đang hiệu lực)", BinanceRestGuard.isBanned());
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
        BinanceRestGuard.reportBan("{\"code\":-1130,\"msg\":\"limit invalid\"}");
        check("reportBan(-1130) → KHÔNG ban", !BinanceRestGuard.isBanned());

        LOG.info("================ TỔNG: {} PASS / {} FAIL ================", pass, fail);
        if (fail > 0) LOG.error("🔴 CÓ TEST FAIL — kiểm lại."); else LOG.info("✅ TẤT CẢ PASS.");
        BinanceRestGuard.BANNED_UNTIL_MS.set(0);
    }

    private static void check(String name, boolean ok) {
        if (ok) { pass++; LOG.info("  ✅ {}", name); }
        else { fail++; LOG.error("  🔴 FAIL: {}", name); }
    }

    private static String safe(String url) {
        try { return HttpRequest.getContentFromUrl(url); } catch (Exception e) { return "EX:" + e.getMessage(); }
    }

    private static void sleepQuiet(long ms) { try { Thread.sleep(ms); } catch (InterruptedException ignored) {} }
}
