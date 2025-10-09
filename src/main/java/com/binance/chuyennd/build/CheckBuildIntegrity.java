package com.binance.chuyennd.build;

import java.util.List;

/**
 * Lớp này dùng để thực hiện "smoke test" sau khi build.
 * Nó kiểm tra xem tất cả các class quan trọng, đặc biệt là các class có inner class,
 * có thực sự tồn tại và có thể được nạp bởi JVM từ file JAR cuối cùng hay không.
 */
public class CheckBuildIntegrity {

    /**
     * =======================================================================
     * QUAN TRỌNG: DANH SÁCH CÁC CLASS CẦN KIỂM TRA
     * Hãy thêm vào đây tất cả các class mà bạn nghi ngờ có nguy cơ lỗi build,
     * đặc biệt là những class bạn biết có sử dụng inner class/anonymous class.
     * Sử dụng tên đầy đủ (fully qualified name).
     * =======================================================================
     */
    private static final List<String> CLASSES_TO_CHECK = List.of(
            "com.binance.chuyennd.bigchange.market.MarketDataObject",
            "com.binance.chuyennd.bigchange.market.MarketLevelChange",
            "com.binance.chuyennd.client.BinanceFuturesClientSingleton",
            "com.binance.chuyennd.client.ClientSingleton",
            "com.binance.chuyennd.config.Labels",
            "com.binance.chuyennd.config.PrivateConfig",
            "com.binance.chuyennd.grid.Price4hManager",
            "com.binance.chuyennd.grid.SimpleMovingAverage4hManager",
            "com.binance.chuyennd.grid.SimpleMovingAverageDayManager",
            "com.binance.chuyennd.helper.OrderHelper",
            "com.binance.chuyennd.helper.PositionHelper",
            "com.binance.chuyennd.helper.TickerFuturesHelper",
            "com.binance.chuyennd.mongo.TickerMongoHelper",
            "com.binance.chuyennd.object.IndicatorEntry",
            "com.binance.chuyennd.object.KlineObjectNumber",
            "com.binance.chuyennd.object.KlineObjectSimpleExtend",
            "com.binance.chuyennd.object.MACDEntry",
            "com.binance.chuyennd.object.MarketRateChange",
            "com.binance.chuyennd.object.PremiumIndex",
            "com.binance.chuyennd.object.RsiEntry",
            "com.binance.chuyennd.object.sw.KlineObjectSimple",
            "com.binance.chuyennd.object.sw.SideWayObject",
            "com.binance.chuyennd.object.TickerStatistics",
            "com.binance.chuyennd.redis.RedisConst",
            "com.binance.chuyennd.redis.RedisDriver",
            "com.binance.chuyennd.redis.RedisHelper",
            "com.binance.chuyennd.research.BacktestEntryStrategies",
            "com.binance.chuyennd.research.BalanceIndex",
            "com.binance.chuyennd.research.BudgetManagerSimple",
            "com.binance.chuyennd.research.ExportMarketData2File",
            "com.binance.chuyennd.research.FundingFeeManager",
            "com.binance.chuyennd.research.OrderTargetInfoTest",
            "com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss",
            "com.binance.chuyennd.research.TechnicalAnalysisUtils",
            "com.binance.chuyennd.research.TestDataWithStruct",
            "com.binance.chuyennd.ticker.TickerManager",
            "com.binance.chuyennd.tradecore.DcaProcessor",
            "com.binance.chuyennd.tradecore.DcaUtils",
            "com.binance.chuyennd.tradecore.MarketBigChangeDetector",
            "com.binance.chuyennd.tradecore.TradeUtils",
            "com.binance.chuyennd.tradecore.TrendDetector",
            "com.binance.chuyennd.trading.BinanceOrderTradingManager",
            "com.binance.chuyennd.trading.BudgetManager",
            "com.binance.chuyennd.trading.DetectEntrySignal2TradeNormal",
            "com.binance.chuyennd.trading.FundingFeeManagerProduction",
            "com.binance.chuyennd.trading.OrderTargetInfo",
            "com.binance.chuyennd.trading.OrderTargetStatus",
            "com.binance.chuyennd.trading.Price4hManagerProduction",
            "com.binance.chuyennd.trading.Reporter",
            "com.binance.chuyennd.trading.SimpleMovingAverage4hManagerProduction",
            "com.binance.chuyennd.trading.SimpleMovingAverageDayManagerProduction",
            "com.binance.chuyennd.trading.SymbolOrderLockingManager",
            "com.binance.chuyennd.utils.CandleUtils",
            "com.binance.chuyennd.utils.Configs",
            "com.binance.chuyennd.utils.DoubleArrayUtils",
            "com.binance.chuyennd.utils.HttpRequest",
            "com.binance.chuyennd.utils.Storage",
            "com.binance.chuyennd.utils.StorageSnappy",
            "com.binance.chuyennd.utils.Utils",
            "com.binance.chuyennd.websocket.ListenAllTicker"
    );

    public static void main(String[] args) {
        System.out.println(">>> Bắt đầu kiểm tra sự toàn vẹn của build...");
        int errorCount = 0;

        for (String className : CLASSES_TO_CHECK) {
            try {
                // Class.forName() là cách chuẩn để yêu cầu JVM nạp một class vào bộ nhớ.
                // Nếu file .class bị thiếu trong file JAR, dòng này sẽ ném ra ClassNotFoundException.
                Class.forName(className);
                System.out.printf("[OK] Đã tìm thấy và nạp thành công class: %s%n", className);
            } catch (ClassNotFoundException e) {
                // Đây chính là lỗi ta muốn bắt!
                System.out.printf(">>> [LỖI] KHÔNG TÌM THẤY CLASS: %s%n", className);
                System.out.println("    => Nguyên nhân: File .class tương ứng có thể đã bị thiếu trong file JAR cuối cùng.");
                errorCount++;
            } catch (Throwable t) {
                // Bắt các lỗi khác, ví dụ như lỗi trong khối static
                System.out.printf(">>> [LỖI] Lỗi khi nạp class: %s%n", className);
                t.printStackTrace(System.out);
                errorCount++;
            }
        }

        System.out.println("--------------------------------------------------");
        if (errorCount == 0) {
            System.out.println("✅ TUYỆT VỜI! Tất cả các class quan trọng đều hợp lệ.");
            System.exit(0); // Thoát với mã thành công
        } else {
            System.out.printf("🚨 CẢNH BÁO: Tìm thấy %d class bị lỗi. Vui lòng kiểm tra lại quá trình build.%n", errorCount);
            System.exit(1); // Thoát với mã lỗi
        }
    }
}