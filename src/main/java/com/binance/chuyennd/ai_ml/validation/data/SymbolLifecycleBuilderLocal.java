package com.binance.chuyennd.ai_ml.validation.data;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.ScanPolicy;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.nio.file.Files;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * TASK-142 - Dung set symbol_lifecycle tu ticker Aerospike DICH (mac dinh Oracle LOCAL 127.0.0.1:3222 ns=test).
 *
 * DOC LAP SymbolLifecycleBuilder goc (no hardcode ghi 242 + goi Binance exchangeInfo). Tool nay:
 *  - Tu tao AerospikeClient theo arg (KHONG dung getClient242 -> KHONG dung 242 that).
 *  - Quet set kline_1m_opt (scanAll) lay firstSeen/lastSeen THAT moi symbol tu key phut.
 *  - Phan trang thai: DEAD neu lastSeen cach 'now-of-data' > freshDays; else LIVE. (Khong goi Binance;
 *    coin delist = lastSeen lui xa so voi max ticker.) delist = lastSeen cho DEAD.
 *  - Ghi set symbol_lifecycle vao CHINH client do (local), bins sym/first/last/status/delist.
 *
 * Args: [host] [port] [ns] [freshDays]
 */
public class SymbolLifecycleBuilderLocal {
    private static final Logger LOG = LoggerFactory.getLogger(SymbolLifecycleBuilderLocal.class);
    private static final String SET_TICKER = "kline_1m_opt";
    private static final String SET_LIFECYCLE = "symbol_lifecycle";

    public static void main(String[] args) throws Exception {
        String host = args.length >= 1 ? args[0] : "127.0.0.1";
        int port = args.length >= 2 ? Integer.parseInt(args[1]) : 3222;
        String ns = args.length >= 3 ? args[2] : "test";
        int freshDays = args.length >= 4 ? Integer.parseInt(args[3]) : 3;

        LOG.info("LIFECYCLE BUILDER LOCAL -> {}:{} ns={}", host, port, ns);
        if (!"127.0.0.1".equals(host) && !"localhost".equals(host)) {
            LOG.warn("host KHONG phai localhost ({})!", host);
        }
        SimpleDateFormat keyFmt = new SimpleDateFormat("yyyyMMdd-HHmm"); // JVM tz GMT+7

        try (AerospikeClient client = new AerospikeClient(host, port)) {
            // 1) scanAll set ticker: moi symbol -> [firstSeen, lastSeen] (ms)
            LOG.info("Quet scanAll {} lay firstSeen/lastSeen...", SET_TICKER);
            Map<String, long[]> seen = new HashMap<>();
            long[] maxTickerTs = {0L};
            long[] scanned = {0L};
            ScanPolicy sp = new ScanPolicy();
            sp.concurrentNodes = true;
            client.scanAll(sp, ns, SET_TICKER, (key, rec) -> {
                if (key.userKey == null) return;
                long ts;
                try { synchronized (keyFmt) { ts = keyFmt.parse(key.userKey.toString()).getTime(); } }
                catch (Exception e) { return; }
                byte[] data = (byte[]) rec.getValue("data");
                if (data == null) return;
                try {
                    Map<String, KlineObjectOptimized> m = MinuteDataFinal.parseFrom(Snappy.uncompress(data)).getTickersMap();
                    synchronized (seen) {
                        if (ts > maxTickerTs[0]) maxTickerTs[0] = ts;
                        for (String sym : m.keySet()) {
                            String full = sym.endsWith("USDT") ? sym : sym + "USDT";
                            long[] fl = seen.get(full);
                            if (fl == null) { seen.put(full, new long[]{ts, ts}); }
                            else { if (ts < fl[0]) fl[0] = ts; if (ts > fl[1]) fl[1] = ts; }
                        }
                        scanned[0]++;
                        if (scanned[0] % 100000 == 0) LOG.info("  scan {} record phut...", scanned[0]);
                    }
                } catch (Exception ignore) {}
            }, "data");
            LOG.info("Quet xong {} record phut, {} symbol, maxTickerTs={}", scanned[0], seen.size(),
                    new Date(maxTickerTs[0]));

            // 2) fresh threshold theo maxTickerTs (khong dung now that vi data test co the cu)
            long freshMs = (long) freshDays * 86400_000L;
            long ref = maxTickerTs[0];

            WritePolicy wp = new WritePolicy();
            wp.sendKey = true; wp.expiration = 0; wp.recordExistsAction = RecordExistsAction.UPDATE;

            int nLive = 0, nDead = 0;
            List<String> deadCoins = new ArrayList<>();
            for (Map.Entry<String, long[]> e : seen.entrySet()) {
                String sym = e.getKey();
                long first = e.getValue()[0], last = e.getValue()[1];
                String status; long delist = 0;
                if ((ref - last) <= freshMs) { status = "LIVE"; nLive++; }
                else { status = "DEAD"; delist = last; nDead++; deadCoins.add(sym); }
                Bin[] bins = {
                        new Bin("sym", sym), new Bin("first", first), new Bin("last", last),
                        new Bin("status", status), new Bin("delist", delist)
                };
                client.put(wp, new Key(ns, SET_LIFECYCLE, sym), bins);
            }
            LOG.info("Ghi set {} xong: {} symbol | LIVE={} DEAD={}", SET_LIFECYCLE, seen.size(), nLive, nDead);
            Collections.sort(deadCoins);
            LOG.info("DEAD coins ({}): {}", deadCoins.size(), deadCoins);

            // 3) verify: doc lai vai coin delist
            LOG.info("VERIFY read-back:");
            for (String coin : new String[]{"LUNAUSDT","FTTUSDT","ANCUSDT","BTCUSDT"}) {
                Record r = client.get(null, new Key(ns, SET_LIFECYCLE, coin));
                if (r != null) {
                    SimpleDateFormat fd = new SimpleDateFormat("yyyy-MM-dd HH:mm");
                    LOG.info("  {} status={} first={} last={}", coin, r.getString("status"),
                            fd.format(new Date(r.getLong("first"))), fd.format(new Date(r.getLong("last"))));
                } else LOG.info("  {} KHONG CO", coin);
            }
        }
        LOG.info("HET LIFECYCLE BUILDER");
        System.exit(0);
    }
}
