package com.binance.chuyennd.websocket;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.LoopSupervisor;
import com.binance.chuyennd.utils.RestBudget;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

public class BinanceDataIngestor {
    public static final Logger LOG = LoggerFactory.getLogger(BinanceDataIngestor.class);

    /** Ngưỡng số symbol lệch >0,2 % để CẢNH BÁO (trước 10-30: ngưỡng RESTART JVM). */
    static final int PRICE_DIFF_ALERT = 50;
    /** [INGEST-QF2] Watchdog tuổi giá (prereg ADD1, cố định): X cảnh báo, Y liên tục ⇒ restart có kiểm soát, ≤1/giờ, ân hạn sau start. */
    static final long PRICE_WARN_MS = 15_000L, PRICE_RESTART_MS = 90_000L, PRICE_GRACE_MS = 180_000L, RESTART_MIN_GAP_MS = 3_600_000L;
    static final long JVM_START_MS = System.currentTimeMillis();

    public static void main(String[] args) {
        Configs.assertLiveRuntime();   // #12 (TASK-030/112): fail-fast nếu AEROSPIKE_READ_CLUSTER thiếu/khác 242 → tránh đọc/ghi nhầm 226 trên live
        Utils.writePid2File();
        // [INGEST-QF] ngân sách REST CỨNG cho MỌI call fapi của JVM này — bật TRƯỚC khi start các ingester.
        RestBudget.enable((int) TickerIngestor2AerospikeNew.cfgLong("INGEST_REST_WEIGHT_CAP", RestBudget.MAX_CAP),
                (int) TickerIngestor2AerospikeNew.cfgLong("INGEST_HDR_SOFT", 1600),
                (int) TickerIngestor2AerospikeNew.cfgLong("INGEST_HDR_HARD", 2000),
                (int) TickerIngestor2AerospikeNew.cfgLong("INGEST_FDATA_REQ_CAP", RestBudget.DEFAULT_FDATA_CAP));
//        new FundingIngestor2Aerospike().start();
        new FundingIngestor2AerospikeNew().start();
//        new TickerIngestor2Aerospike().start();
        new TickerIngestor2AerospikeNew().start();
        // OI ingester: thread riêng, per-symbol throttled qua BinanceRestGuard (TASK-007 C).
        new OpenInterestIngestor2AerospikeNew().start();
        // TASK-031: forward-rolling nến 15m/4h BTC/ETH → 242 (nối 009 historical). Cần trước golive gate.
        new Kline15m4hForwardRoller().start();
        // TASK-028 #2: bật lại watchdog (trước bị comment → P1 không có giám sát chạy-nhưng-stale).
        startThreadAutoRestartProgram();
        startPriceAgeWatchdog();
    }

    /** Quyết định của watchdog tuổi giá — thuần, test được. 0 ổn, 1 cảnh báo, 2 restart, 3 cần restart nhưng đã restart trong 1h. */
    static int decidePriceAge(long ageMs, long sinceStartMs, long lastRestartMs, long now) {
        if (sinceStartMs < PRICE_GRACE_MS) return 0;
        if (ageMs <= PRICE_WARN_MS) return 0;
        if (ageMs <= PRICE_RESTART_MS) return 1;
        return now - lastRestartMs >= RESTART_MIN_GAP_MS ? 2 : 3;
    }

    static Path restartMarker() {
        String dir = System.getenv("APP_PID_DIR");
        return Paths.get(dir == null || dir.isEmpty() ? "./run" : dir, "price_age_restart.ts");
    }

    static long readLastRestart() {
        try {
            return Long.parseLong(new String(Files.readAllBytes(restartMarker()), StandardCharsets.US_ASCII).trim());
        } catch (Exception e) {
            return 0L;
        }
    }

    static void sendTelegramAsync(String msg) {
        Thread tg = new Thread(() -> {
            try {
                Utils.sendSms2Telegram(msg);
            } catch (Exception e) {
                LOG.warn("Telegram loi: {}", e.toString());
            }
        }, "Ingest-Telegram");
        tg.setDaemon(true);
        tg.start();
    }

    /** [INGEST-QF2] Watchdog tuổi price_realtime (MAJ-1): mỗi 5 s; X=15 s ⇒ WARN+Telegram ≤1/10′; Y=90 s ⇒ restart JVM có kiểm soát ≤1/h. */
    private static void startPriceAgeWatchdog() {
        LoopSupervisor.start("Price-Age-Watchdog", () -> {
            long lastTg = 0, lastSuppressLog = 0;
            LOG.info("[PRICE-AGE] watchdog bat: canh bao > {} ms, restart co kiem soat > {} ms (<=1/gio), an han {} ms sau start",
                    PRICE_WARN_MS, PRICE_RESTART_MS, PRICE_GRACE_MS);
            while (true) {
                try {
                    Thread.sleep(5_000L);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    return;
                }
                long now = System.currentTimeMillis();
                long age = TickerIngestor2AerospikeNew.priceAgeMs();
                if (age < 0) age = now - JVM_START_MS;   // chua ghi gia lan nao
                long lastRestart = readLastRestart();
                int d = decidePriceAge(age, now - JVM_START_MS, lastRestart, now);
                if (d == 0) continue;
                if (now - lastTg >= 600_000L) {
                    lastTg = now;
                    sendTelegramAsync("collectData 242: price_realtime dung " + age / 1000 + " s (nguong canh bao 15 s)"
                            + (d == 2 ? " — RESTART JVM co kiem soat" : d == 3 ? " — da restart trong 1h, KHONG restart lai, can nguoi xem" : ""));
                }
                if (d == 1) {
                    LOG.warn("[PRICE-AGE] price_realtime dung {} ms (> {} ms)", age, PRICE_WARN_MS);
                } else if (d == 3) {
                    if (now - lastSuppressLog >= 300_000L) {
                        lastSuppressLog = now;
                        LOG.error("[PRICE-AGE] price_realtime dung {} ms > {} ms nhung da restart luc {} (<1h) — KHONG restart lai", age, PRICE_RESTART_MS, lastRestart);
                    }
                } else {
                    LOG.error("[PRICE-AGE] price_realtime dung {} ms > {} ms lien tuc — RESTART JVM co kiem soat (bien phap cuoi)", age, PRICE_RESTART_MS);
                    try {
                        Files.write(restartMarker(), Long.toString(now).getBytes(StandardCharsets.US_ASCII));
                    } catch (Exception e) {
                        LOG.error("[PRICE-AGE] khong ghi duoc moc restart {}: {} — KHONG restart (tranh vong lap)", restartMarker(), e.toString());
                        continue;
                    }
                    Utils.resetInWindow("Reset by Price Age " + age + "ms", 8, 20);
                }
            }
        }, true);
    }

    private static void startThreadAutoRestartProgram() {
        LoopSupervisor.start("ThreadAutoRestartProgram", () -> {
            // [INGEST-QF] restart lịch: 0 = tắt (script deploy 2a đặt 0); mặc định 12 = hành vi cũ khi env vắng.
            long schedMinutes = TickerIngestor2AerospikeNew.cfgLong("INGEST_SCHEDULED_RESTART_HOURS", 12) * 60L;
            long tgEveryMs = Math.max(1, TickerIngestor2AerospikeNew.cfgLong("INGEST_PRICE_DIFF_TG_MIN", 30)) * 60_000L;
            LOG.info("Start thread ThreadAutoRestartProgram | INGEST-QF: lech gia KHONG restart JVM (canh bao >{} symbol, Telegram <=1/{}') | restart lich {}",
                    PRICE_DIFF_ALERT, tgEveryMs / 60_000L, schedMinutes > 0 ? (schedMinutes / 60) + "h" : "TAT");
            long lastTgMs = 0;
            int counterMinutes = 0;
            while (true) {
                try {
                    Thread.sleep(Utils.TIME_MINUTE);
                } catch (InterruptedException ex) {
                    Thread.currentThread().interrupt();
                    return;
                }
                int priceDiff = -1;
                try {
                    priceDiff = DataManagerAerospikeFloatSim.checkAndComparePriceDiff();
                    if (priceDiff > PRICE_DIFF_ALERT) {
                        // [INGEST-QF] 10-30: 15 restart do đây (chỉ là biến động: 2 giá chụp cách nhau 3–6 s), mỗi restart burst
                        // ~1 500 weight ⇒ -1003 IP 242 lúc 03:47:59. Nay chỉ cảnh báo + metric, KHÔNG restart.
                        LOG.warn("[PRICE-DIFF] {} symbol lech >0.2% giua price_realtime va ticker/price (nguong canh bao {}) — KHONG restart JVM",
                                priceDiff, PRICE_DIFF_ALERT);
                        long now = System.currentTimeMillis();
                        if (now - lastTgMs >= tgEveryMs) {
                            lastTgMs = now;
                            sendTelegramAsync("collectData 242: " + priceDiff + " symbol lech gia >0.2% (watchdog, KHONG restart). "
                                    + "Thuong do bien dong manh; neu keo dai >10 phut hay kiem Rest-Price-Loop.");
                        }
                    }
                } catch (Exception e) {
                    LOG.warn("ThreadAutoRestartProgram lỗi khi checkAndComparePriceDiff (bỏ qua nhịp này): {}", e.getMessage(), e);
                }
                try {
                    RestBudget b = RestBudget.get();
                    LOG.info("[REST-BUDGET] {} | price_gap_max_ms={} price_age_ms={} price_diff={} loop_restarts={} repair_xong={}",
                            b == null ? "off" : b.statsLine(), TickerIngestor2AerospikeNew.takePriceGapMaxMs(),
                            TickerIngestor2AerospikeNew.priceAgeMs(), priceDiff, LoopSupervisor.RESTARTS.get(),
                            TickerIngestor2AerospikeNew.startupRepairDone ? 1 : 0);
                } catch (Exception e) {
                    LOG.warn("[REST-BUDGET] loi ghi thong ke: {}", e.toString(), e);
                }
                counterMinutes++;
                if (schedMinutes > 0 && counterMinutes > schedMinutes) {
                    try {
                        Utils.reset("Reset by Schedule");
                    } catch (Exception e) {
                        LOG.error("ERROR during Restart: {}", e.getMessage(), e);
                    }
                }
            }
        }, false);
    }
}
