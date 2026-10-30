package com.binance.chuyennd.websocket;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.RestBudget;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class BinanceDataIngestor {
    public static final Logger LOG = LoggerFactory.getLogger(BinanceDataIngestor.class);

    /** Ngưỡng số symbol lệch >0,2 % để CẢNH BÁO (trước 10-30: ngưỡng RESTART JVM). */
    static final int PRICE_DIFF_ALERT = 50;

    public static void main(String[] args) {
        Configs.assertLiveRuntime();   // #12 (TASK-030/112): fail-fast nếu AEROSPIKE_READ_CLUSTER thiếu/khác 242 → tránh đọc/ghi nhầm 226 trên live
        Utils.writePid2File();
        // [INGEST-QF 2026-10-30] ngân sách REST CỨNG cho MỌI call fapi của JVM này — bật TRƯỚC khi start các ingester.
        // Prereg docs/prereg/PREREG_INGEST_QUICKFIX.md (Q4/Q5/Q6).
        RestBudget.enable((int) TickerIngestor2AerospikeNew.cfgLong("INGEST_REST_WEIGHT_CAP", RestBudget.MAX_CAP),
                (int) TickerIngestor2AerospikeNew.cfgLong("INGEST_HDR_SOFT", 1600),
                (int) TickerIngestor2AerospikeNew.cfgLong("INGEST_HDR_HARD", 2000));
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
    }

    private static void startThreadAutoRestartProgram() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadAutoRestartProgram");
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
                    LOG.warn("ThreadAutoRestartProgram bị interrupt khi sleep: {}", ex.getMessage());
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
                            final String msg = "collectData 242: " + priceDiff + " symbol lech gia >0.2% (watchdog, KHONG restart). "
                                    + "Thuong do bien dong manh; neu keo dai >10 phut hay kiem Rest-Price-Loop.";
                            Thread tg = new Thread(() -> {
                                try {
                                    Utils.sendSms2Telegram(msg);
                                } catch (Exception e) {
                                    LOG.warn("[PRICE-DIFF] gui Telegram loi: {}", e.toString());
                                }
                            }, "PriceDiff-Telegram");
                            tg.setDaemon(true);
                            tg.start();
                        }
                    }
                } catch (Exception e) {
                    // TASK-028 #2: KHÔNG nuốt câm (luật CLAUDE.md) — log đủ ngữ cảnh, vẫn tiếp vòng giám sát.
                    LOG.warn("ThreadAutoRestartProgram lỗi khi checkAndComparePriceDiff (bỏ qua nhịp này): {}", e.getMessage(), e);
                }
                try {
                    RestBudget b = RestBudget.get();
                    LOG.info("[REST-BUDGET] {} | price_gap_max_ms={} price_diff={}",
                            b == null ? "off" : b.statsLine(), TickerIngestor2AerospikeNew.takePriceGapMaxMs(), priceDiff);
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

        }).start();
    }
}
