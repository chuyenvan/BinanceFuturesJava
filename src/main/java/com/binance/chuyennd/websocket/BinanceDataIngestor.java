//package com.binance.chuyennd.websocket;
//
//import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
//import com.binance.chuyennd.trading.DetectEntrySignal2TradeNormal;
//import com.binance.chuyennd.utils.Utils;
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
//import java.util.logging.Level;
//
//public class BinanceDataIngestor {
//    public static final Logger LOG = LoggerFactory.getLogger(BinanceDataIngestor.class);
//
//    public static void main(String[] args) {
//        Utils.writePid2File();
////        new FundingIngestor2Aerospike().start();
//        new FundingIngestor2AerospikeNew().start();
////        new TickerIngestor2Aerospike().start();
//        new TickerIngestor2AerospikeNew().start();
////        startThreadAutoRestartProgram();
//    }
//
//    private static void startThreadAutoRestartProgram() {
//        new Thread(() -> {
//            Thread.currentThread().setName("ThreadAutoRestartProgram");
//            LOG.info("Start thread ThreadAutoRestartProgram");
//            int counterMinutes = 0;
//            while (true) {
//                try {
//                    Thread.sleep(Utils.TIME_MINUTE);
//                } catch (InterruptedException ex) {
//                    java.util.logging.Logger.getLogger(DetectEntrySignal2TradeNormal.class.getName()).log(Level.SEVERE, null, ex);
//                }
//                try {
//                    int totalSymbolPriceError = DataManagerAerospikeFloatSim.checkAndComparePriceDiff();
//                    if (totalSymbolPriceError > 50) {
//                        LOG.error("Too many symbol price errors: {}. Restarting...", totalSymbolPriceError);
//                        Utils.reset("Reset by Price Error Count " + totalSymbolPriceError);
//                    }
//                } catch (Exception e) {
//                    e.printStackTrace();
//                }
//                if (counterMinutes > 12 * 60) { // restart every 12 hours
//                    try {
//                        Utils.reset("Reset by Schedule");
//                    } catch (Exception e) {
//                        LOG.error("ERROR during Restart: {}", e);
//                        e.printStackTrace();
//                    }
//                }
//            }
//
//        }).start();
//    }
//}
//
