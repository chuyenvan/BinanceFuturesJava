package com.binance.chuyennd.research;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Map;

/**
 * TASK-041 A0: xuất chuỗi giá thị trường 15m (BTC + ETH close) từ Aerospike ticker set
 * {@code kline_1m_opt} (key {@code yyyyMMdd-HHmm}, bin {@code data} = Snappy+protobuf mọi coin/phút).
 * Đọc TỪNG record 15m (nhẹ RAM — KHÁC readDataFromAerospike1M load cả ngày × mọi coin → OOM-prone).
 * Ra CSV {@code ts,btc_close,eth_close} để Python đếm cú sập forward H giờ (chốt H/X cho gate).
 *
 * <p>Args: [startYYYYMMDD=20210101] [endYYYYMMDD=now] [outCsv] [instance=226|242].
 * Chạy trên 226: {@code java -cp jar com.binance.chuyennd.research.ExportMarketCloseSeries 20210101 20260622 /home/chuyennd/java/simulator/mkt_close_15m.csv 226}
 */
public class ExportMarketCloseSeries {

    static final Logger LOG = LoggerFactory.getLogger(ExportMarketCloseSeries.class);
    static final String SET = "kline_1m_opt";
    static final long STEP = 15 * 60 * 1000L;

    public static void main(String[] args) throws Exception {
        SimpleDateFormat day = new SimpleDateFormat("yyyyMMdd");
        long start = args.length > 0 ? day.parse(args[0]).getTime() : day.parse("20210101").getTime();
        long end = args.length > 1 ? day.parse(args[1]).getTime() : System.currentTimeMillis();
        String out = args.length > 2 ? args[2] : "/home/chuyennd/java/simulator/mkt_close_15m.csv";
        String inst = args.length > 3 ? args[3] : "226";

        AerospikeClient client = inst.equals("242")
                ? DataManagerAerospikeFloatSim.getClient242()
                : DataManagerAerospikeFloatSim.getClient226();
        SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
        LOG.info("Export BTC/ETH 15m close [{} .. {}] inst={} -> {}",
                fmt.format(new Date(start)), fmt.format(new Date(end)), inst, out);

        long n = 0, hit = 0;
        try (BufferedWriter w = new BufferedWriter(new FileWriter(out))) {
            w.write("ts,btc_close,eth_close\n");
            for (long ts = start; ts <= end; ts += STEP) {
                n++;
                Key key = new Key(Configs.AEROSPIKE_NAMESPACE, SET, fmt.format(new Date(ts)));
                Record rec = client.get(null, key);
                if (rec == null) continue;
                byte[] data = (byte[]) rec.getValue("data");
                if (data == null) continue;
                Map<String, KlineObjectOptimized> m =
                        MinuteDataFinal.parseFrom(Snappy.uncompress(data)).getTickersMap();
                KlineObjectOptimized btc = m.get("BTCUSDT");
                if (btc == null) continue;
                KlineObjectOptimized eth = m.get("ETHUSDT");
                float bc = (float) btc.getPriceClose();
                float ec = eth != null ? (float) eth.getPriceClose() : Float.NaN;
                w.write(ts + "," + bc + "," + ec + "\n");
                hit++;
                if (n % 5000 == 0) {
                    LOG.info("  {} mocs | {} hit | ts {}", n, hit, fmt.format(new Date(ts)));
                    w.flush();
                }
            }
        }
        LOG.info("DONE {} mocs | {} hit -> {}", n, hit, out);
    }
}
