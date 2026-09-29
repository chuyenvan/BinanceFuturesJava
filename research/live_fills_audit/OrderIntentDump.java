import com.binance.chuyennd.trading.OrderTargetInfo;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.StorageSnappy;

import java.io.*;
import java.nio.file.*;
import java.util.Map;

/**
 * D6 (RESULT_LATENCY_FILL) — dump OrderTargetInfo intents (level + decision candle) from the
 * Snappy-compressed Java-serialized files written by DetectEntrySignal2TradeNormal.writeOrder2File
 * (path storage/data/order/<YYYYMMDD>/<SYM>-<startTime> on 242, READ-ONLY copy to Oracle first).
 *
 * NOT a sim — a plain deserializer. Run once on Oracle to produce orders_dump.csv, then
 * research/analysis/latency_fill.py consumes it (0 sim).
 *
 * Usage:
 *   javac -cp "<jar>:<snappy>" OrderIntentDump.java
 *   java  -cp ".:<jar>:<snappy>" OrderIntentDump <order_root> <out_csv>
 */
public class OrderIntentDump {
    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("usage: OrderIntentDump <order_root> <out_csv>");
            System.exit(2);
        }
        Path root = Paths.get(args[0]);
        BufferedWriter w = new BufferedWriter(new OutputStreamWriter(
                new FileOutputStream(args[1]), "UTF-8"));
        w.write("filename,symbol,level,startTime,priceOpen,maxPrice,minPrice,priceClose,priceEntry,timeStart,quantity\n");
        int n = 0, bad = 0;
        try (java.util.stream.Stream<Path> s = Files.walk(root)) {
            for (Path p : (Iterable<Path>) s.filter(Files::isRegularFile)::iterator) {
                File f = p.toFile();
                if (f.getName().endsWith(".tmp")) continue;
                try {
                    Object obj = StorageSnappy.readObjectFromFile(f.getAbsolutePath());
                    if (obj instanceof Map) {
                        Map<?, ?> m = (Map<?, ?>) obj;
                        Object o = m.get("order");
                        Object t = m.get("ticker");
                        if (o instanceof OrderTargetInfo && t instanceof KlineObjectSimple) {
                            OrderTargetInfo order = (OrderTargetInfo) o;
                            KlineObjectSimple tk = (KlineObjectSimple) t;
                            String level = order.marketLevel == null ? "NULL" : order.marketLevel.toString();
                            w.write(String.format("%s,%s,%s,%d,%.8f,%.8f,%.8f,%.8f,%.8f,%d,%.8f%n",
                                    f.getName(), order.symbol, level,
                                    tk.startTime == null ? -1L : tk.startTime,
                                    tk.priceOpen, tk.maxPrice, tk.minPrice, tk.priceClose,
                                    order.priceEntry == null ? -1f : order.priceEntry,
                                    order.timeStart,
                                    order.quantity == null ? -1f : order.quantity));
                            n++;
                        } else {
                            bad++;
                        }
                    } else {
                        bad++;
                    }
                } catch (Exception e) {
                    bad++;   // serialVersionUID drift on old MarketDataObject (20260424..0505) — before fill window
                }
            }
        }
        w.close();
        System.err.println("dumped n=" + n + " bad=" + bad);
    }
}
