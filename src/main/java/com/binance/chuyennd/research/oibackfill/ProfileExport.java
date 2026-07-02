package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.features.export.funding.EntrySignalFilter;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * PROFILE tang logic export: do RIENG thoi gian tung phan tren 1 doan ngan,
 * de tim nut that (vi sao 1 nam ~2h du Aerospike doc nhanh).
 * Do: (A) updateHistory, (B) getTopCoin, (C) selectCoins filter, (D) doc Aerospike.
 * In ms tong + ms/moc tung phan.
 *
 * Usage: java ProfileExport <startEpochMs> <days>
 */
public class ProfileExport {
    private static final Logger LOG = LoggerFactory.getLogger(ProfileExport.class);

    public static void main(String[] args) {
        long start = args.length > 0 ? Long.parseLong(args[0]) : 1640995200000L; // 2022-01-01
        int days = args.length > 1 ? Integer.parseInt(args[1]) : 3;

        HistoryManager history = HistoryManager.getInstance();
        // market data cho extractFeatures (giong Tool1)
        TreeMap<Long, com.binance.chuyennd.object.MarketDataObject> time2MarketData =
                DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        com.binance.chuyennd.ai_ml.features.export.funding.FundingDataCollectionManager.FundingFeatureExtractorV2 extractor =
                new com.binance.chuyennd.ai_ml.features.export.funding.FundingDataCollectionManager.FundingFeatureExtractorV2();
        long tRead = 0, tHist = 0, tTop = 0, tFilter = 0, tExtract = 0;
        int totalMoc = 0; long extractCalls = 0;

        for (int d = 0; d < days; d++) {
            long dayStart = start + (long) d * Utils.TIME_DAY;
            long t0 = System.nanoTime();
            TreeMap<Long, Map<String, KlineObjectSimple>> data =
                    DataManagerAerospikeFloatSim.readDataFromAerospike1M(dayStart);
            tRead += System.nanoTime() - t0;
            if (data == null) continue;

            for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : data.entrySet()) {
                long time = e.getKey();
                Map<String, KlineObjectSimple> snap = e.getValue();
                totalMoc++;

                long a = System.nanoTime();
                history.updateHistory(snap);
                tHist += System.nanoTime() - a;

                long b = System.nanoTime();
                List<String> basket = CoinRankManager.getInstance().getTopCoin(time);
                tTop += System.nanoTime() - b;

                long c = System.nanoTime();
                Set<String> pass = EntrySignalFilter.selectCoins(snap, history);
                tFilter += System.nanoTime() - c;

                // (E) extractFeatures cho moi coin qua filter (giong PASS1, tuan tu de do thuan)
                com.binance.chuyennd.object.MarketDataObject rate = time2MarketData.get(time);
                long ee = System.nanoTime();
                for (String symbol : pass) {
                    KlineObjectSimple ticker = snap.get(symbol);
                    if (ticker == null) continue;
                    com.binance.chuyennd.research.OrderTargetInfoTest dummy =
                            new com.binance.chuyennd.research.OrderTargetInfoTest(
                                    com.binance.chuyennd.trading.OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0f,
                                    Configs.LEVERAGE_ORDER, symbol, time, time, com.binance.client.model.enums.OrderSide.BUY);
                    dummy.lastEntry = ticker.priceClose;
                    extractor.extractFeatures(time, dummy, snap, rate, basket);
                    extractCalls++;
                }
                tExtract += System.nanoTime() - ee;
            }
            LOG.info("...ngay {}/{} xong, totalMoc={}", d + 1, days, totalMoc);
        }

        double ms = 1e6;
        LOG.info("===================================================");
        LOG.info("Tong moc = {} ({} ngay)", totalMoc, days);
        LOG.info("(A) readAerospike : {} ms tong", String.format("%.0f", tRead / ms));
        LOG.info("(B) updateHistory : {} ms tong | {} us/moc", String.format("%.0f", tHist / ms), String.format("%.1f", tHist / 1e3 / totalMoc));
        LOG.info("(C) getTopCoin    : {} ms tong | {} us/moc", String.format("%.0f", tTop / ms), String.format("%.1f", tTop / 1e3 / totalMoc));
        LOG.info("(D) selectCoins   : {} ms tong | {} us/moc", String.format("%.0f", tFilter / ms), String.format("%.1f", tFilter / 1e3 / totalMoc));
        LOG.info("(E) extractFeatures: {} ms tong | {} calls | {} us/call", String.format("%.0f", tExtract / ms), extractCalls, String.format("%.1f", extractCalls > 0 ? tExtract / 1e3 / extractCalls : 0));
        double perYear = (tHist + tTop + tFilter + tExtract) / ms / totalMoc * 525600 / 1000;
        LOG.info(">>> Uoc tinh TOAN BO logic (B+C+D+E) cho 1 nam (525600 moc): {} giay = {} phut", String.format("%.0f", perYear), String.format("%.1f", perYear / 60));
        double extractYear = tExtract / ms / totalMoc * 525600 / 1000;
        LOG.info(">>> Rieng extractFeatures cho 1 nam: {} giay = {} phut ({}%% tong)", String.format("%.0f", extractYear), String.format("%.1f", extractYear / 60), String.format("%.0f", 100.0 * tExtract / (tHist + tTop + tFilter + tExtract)));
        LOG.info("===================================================");
        System.exit(0);
    }
}
