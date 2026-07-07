package com.binance.chuyennd.ai_ml.validation.data;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * TASK-140 - Backfill coin delist vao Aerospike DICH (mac dinh Oracle LOCAL 127.0.0.1:3222).
 * DOC LAP voi DataManagerAerospikeFloatSim (writeMinuteBatch hardcode getClient242).
 * Tool TU tao AerospikeClient theo ARG - KHONG doc Configs.AEROSPIKE_HOST_*.
 * Convert kline vision 12 cot -> proto KlineObjectOptimized. Set kline_1m_opt, key yyyyMMdd-HHmm GMT+7.
 * Args: coin1[,coin2] [host] [port] [ns] [startYYYYMM] [endYYYYMM]
 */
public class BackfillDelistCoin {
    private static final Logger LOG = LoggerFactory.getLogger(BackfillDelistCoin.class);
    private static final String FILE_BASE = "https://data.binance.vision";
    private static final String KLINE_PREFIX = "data/futures/um/monthly/klines/";
    private static final String SET_TICKER = "kline_1m_opt";
    private static final String NL = "\n";

    public static void main(String[] args) throws Exception {
        if (args.length < 1) { LOG.error("Can arg: coins [host] [port] [ns] [startYYYYMM] [endYYYYMM]"); System.exit(1); }
        String[] coins = args[0].split(",");
        String host = args.length >= 2 ? args[1] : "127.0.0.1";
        int port = args.length >= 3 ? Integer.parseInt(args[2]) : 3222;
        String ns = args.length >= 4 ? args[3] : "test";
        String startYM = args.length >= 5 ? args[4] : "202101";
        String endYM = args.length >= 6 ? args[5] : new SimpleDateFormat("yyyyMM").format(new Date());

        LOG.info("BACKFILL DELIST -> {}:{} ns={} set={}", host, port, ns, SET_TICKER);
        LOG.info("coins={} range {}..{}", Arrays.toString(coins), startYM, endYM);
        if (!"127.0.0.1".equals(host) && !"localhost".equals(host)) {
            LOG.warn("host KHONG phai localhost ({}). Xac nhan KHONG phai 242/226 that!", host);
        }

        WritePolicy wp = new WritePolicy();
        wp.sendKey = true;
        wp.expiration = 0;
        wp.recordExistsAction = RecordExistsAction.UPDATE;
        SimpleDateFormat keyFmt = new SimpleDateFormat("yyyyMMdd-HHmm");

        try (AerospikeClient client = new AerospikeClient(host, port)) {
            for (String coinRaw : coins) {
                String coin = coinRaw.trim().toUpperCase();
                if (coin.isEmpty()) continue;
                LOG.info("---- backfill {} ----", coin);
                int[] ym = parseYM(startYM), ymEnd = parseYM(endYM);
                long totalMin = 0;
                int monthsOk = 0;
                int y = ym[0], mo = ym[1];
                while (y < ymEnd[0] || (y == ymEnd[0] && mo <= ymEnd[1])) {
                    String url = String.format("%s/%s%s/1m/%s-1m-%04d-%02d.zip", FILE_BASE, KLINE_PREFIX, coin, coin, y, mo);
                    byte[] zip = httpBytes(url);
                    if (zip != null) {
                        Map<String, KlineObjectOptimized> byMinuteKey = new HashMap<>();
                        for (String line : unzipCsv(zip)) {
                            String[] p = line.split(",");
                            if (p.length < 8) continue;
                            long openTime;
                            float o, h, l, c, qv;
                            try {
                                openTime = (long) Double.parseDouble(p[0]);
                                o = Float.parseFloat(p[1]);
                                h = Float.parseFloat(p[2]);
                                l = Float.parseFloat(p[3]);
                                c = Float.parseFloat(p[4]);
                                qv = Float.parseFloat(p[7]);
                            } catch (NumberFormatException nf) { continue; }
                            String k = keyFmt.format(new Date(openTime));
                            byMinuteKey.put(k, KlineObjectOptimized.newBuilder()
                                    .setPriceOpen(o).setMaxPrice(h).setMinPrice(l).setPriceClose(c).setTotalUsdt(qv).build());
                        }
                        for (Map.Entry<String, KlineObjectOptimized> e : byMinuteKey.entrySet()) {
                            writeMinuteMerge(client, wp, ns, e.getKey(), coin, e.getValue());
                            totalMin++;
                        }
                        if (!byMinuteKey.isEmpty()) monthsOk++;
                    }
                    mo++;
                    if (mo > 12) { mo = 1; y++; }
                }
                LOG.info("   {} ghi {} phut ({} thang co data)", coin, totalMin, monthsOk);
            }
            LOG.info("READ-BACK VERIFY coin={}", coins[0]);
            verifyReadBack(client, ns, keyFmt, coins[0].trim().toUpperCase(), startYM);
        }
        LOG.info("HET BACKFILL");
        System.exit(0);
    }

    private static void writeMinuteMerge(AerospikeClient client, WritePolicy wp, String ns,
                                         String minuteKey, String coin, KlineObjectOptimized kline) {
        try {
            Key key = new Key(ns, SET_TICKER, minuteKey);
            Map<String, KlineObjectOptimized> finalMap = new HashMap<>();
            Record rec = client.get(null, key);
            if (rec != null) {
                byte[] data = (byte[]) rec.getValue("data");
                if (data != null) finalMap.putAll(MinuteDataFinal.parseFrom(Snappy.uncompress(data)).getTickersMap());
            }
            finalMap.put(coin, kline);
            byte[] compressed = Snappy.compress(MinuteDataFinal.newBuilder().putAllTickers(finalMap).build().toByteArray());
            client.put(wp, key, new Bin("data", compressed));
        } catch (Exception e) {
            LOG.error("ghi phut {} coin {} loi: {}", minuteKey, coin, e.getMessage());
        }
    }

    private static void verifyReadBack(AerospikeClient client, String ns, SimpleDateFormat keyFmt, String coin, String startYM) {
        try {
            int[] ym = parseYM(startYM);
            Calendar cal = Calendar.getInstance();
            cal.set(ym[0], ym[1] - 1, 1, 12, 0, 0);
            cal.set(Calendar.MILLISECOND, 0);
            int found = 0;
            for (int d = 0; d < 90 && found < 3; d++) {
                String k = keyFmt.format(cal.getTime());
                Key key = new Key(ns, SET_TICKER, k);
                Record rec = client.get(null, key);
                if (rec != null) {
                    byte[] data = (byte[]) rec.getValue("data");
                    if (data != null) {
                        try {
                            Map<String, KlineObjectOptimized> m = MinuteDataFinal.parseFrom(Snappy.uncompress(data)).getTickersMap();
                            KlineObjectOptimized kl = m.get(coin);
                            if (kl != null) {
                                LOG.info("   OK {} @ {}: close={} high={} low={} usdt={} tong {} coin",
                                        coin, k, kl.getPriceClose(), kl.getMaxPrice(), kl.getMinPrice(), kl.getTotalUsdt(), m.size());
                                found++;
                            }
                        } catch (Exception ignore) {}
                    }
                }
                cal.add(Calendar.DAY_OF_MONTH, 1);
            }
            if (found == 0) LOG.warn("   KHONG doc lai duoc {} thang {}", coin, startYM);
        } catch (Exception e) {
            LOG.error("verify loi: {}", e.getMessage());
        }
    }

    private static int[] parseYM(String ym) {
        return new int[]{Integer.parseInt(ym.substring(0, 4)), Integer.parseInt(ym.substring(4, 6))};
    }

    private static byte[] httpBytes(String url) throws IOException {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        c.setRequestProperty("User-Agent", "backfill-delist/1.0");
        c.setConnectTimeout(20000);
        c.setReadTimeout(120000);
        int code = c.getResponseCode();
        if (code == 404) return null;
        if (code != 200) throw new IOException("HTTP " + code);
        try (InputStream in = c.getInputStream(); ByteArrayOutputStream bo = new ByteArrayOutputStream()) {
            byte[] buf = new byte[65536];
            int n;
            while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
            return bo.toByteArray();
        }
    }

    private static List<String> unzipCsv(byte[] zip) throws IOException {
        List<String> lines = new ArrayList<>();
        try (ZipInputStream zis = new ZipInputStream(new ByteArrayInputStream(zip))) {
            ZipEntry e = zis.getNextEntry();
            if (e == null) return lines;
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] buf = new byte[65536];
            int n;
            while ((n = zis.read(buf)) > 0) bo.write(buf, 0, n);
            for (String l : bo.toString("UTF-8").split(NL)) {
                l = l.trim();
                if (!l.isEmpty()) lines.add(l);
            }
        }
        return lines;
    }
}
