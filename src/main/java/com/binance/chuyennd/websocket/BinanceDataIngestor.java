package com.binance.chuyennd.websocket;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class BinanceDataIngestor {
    public static final Logger LOG = LoggerFactory.getLogger(BinanceDataIngestor.class);

    public static void main(String[] args) {
        Utils.writePid2File();
//        new FundingIngestor2Aerospike().start();
        new FundingIngestor2AerospikeNew().start();
//        new TickerIngestor2Aerospike().start();
        new TickerIngestor2AerospikeNew().start();
        // OI ingester: thread riêng, per-symbol throttled qua BinanceRestGuard (TASK-007 C).
        new OpenInterestIngestor2AerospikeNew().start();
        // TASK-028 #2: bật lại watchdog (trước bị comment → P1 không có giám sát chạy-nhưng-stale).
        startThreadAutoRestartProgram();
    }

    private static void startThreadAutoRestartProgram() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadAutoRestartProgram");
            LOG.info("Start thread ThreadAutoRestartProgram");
            int counterMinutes = 0;
            while (true) {
                try {
                    Thread.sleep(Utils.TIME_MINUTE);
                } catch (InterruptedException ex) {
                    LOG.warn("ThreadAutoRestartProgram bị interrupt khi sleep: {}", ex.getMessage());
                }
                try {
                    int totalSymbolPriceError = DataManagerAerospikeFloatSim.checkAndComparePriceDiff();
                    if (totalSymbolPriceError > 50) {
                        LOG.error("Too many symbol price errors: {}. Restarting...", totalSymbolPriceError);
                        Utils.reset("Reset by Price Error Count " + totalSymbolPriceError);
                    }
                } catch (Exception e) {
                    // TASK-028 #2: KHÔNG nuốt câm (luật CLAUDE.md) — log đủ ngữ cảnh, vẫn tiếp vòng giám sát.
                    LOG.warn("ThreadAutoRestartProgram lỗi khi checkAndComparePriceDiff (bỏ qua nhịp này): {}", e.getMessage(), e);
                }
                // TASK-028 #2: counterMinutes TRƯỚC ĐÂY không bao giờ ++ → nhánh reset-12h là code chết.
                // Nay ++ mỗi phút để reset định kỳ ~12h hoạt động đúng (Utils.reset re-exec → process mới
                // bắt đầu lại từ 0).
                counterMinutes++;
                if (counterMinutes > 12 * 60) { // restart every 12 hours
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

