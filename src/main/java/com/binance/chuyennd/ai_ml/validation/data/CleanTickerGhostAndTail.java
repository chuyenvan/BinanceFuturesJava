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

import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * TASK-134 - Clean ticker Aerospike Oracle local (127.0.0.1:3222 ns=test set kline_1m_opt):
 *   (1) LOAI 38 ghost symbol khop regex USDCUSDT$ (cap USDC-margin bi normalize sai) o MOI record phut.
 *   (2) CAT DUOI DON: 10 coin delist-futures co ticker gia phang vol=0 keo dai — xoa symbol do khoi cac
 *       record phut SAU moc lastVol>0 (delist that). Moc per-coin truyen cung (do bang MeasureDelistPoint).
 *
 * DOC LAP DataManager (hardcode 242). Tu tao AerospikeClient theo arg. GHI DE record da sua (RecordExistsAction.UPDATE).
 * Chi ghi lai record CO thay doi (bo qua record khong dung toi -> nhanh hon).
 * Args: [host] [port] [ns]  (mac dinh 127.0.0.1 3222 test)
 */
public class CleanTickerGhostAndTail {
    private static final Logger LOG = LoggerFactory.getLogger(CleanTickerGhostAndTail.class);
    private static final String SET = "kline_1m_opt";

    // moc lastVol>0 (delist that) per coin — sau moc nay la duoi don, xoa. Do bang MeasureDelistPoint 2026-07-07.
    private static final Map<String, Long> DELIST_TS = new HashMap<>();
    static {
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd HH:mm");
        f.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        try {
            DELIST_TS.put("DGBUSDT",   f.parse("2024-04-01 16:00").getTime());
            DELIST_TS.put("FTTUSDT",   f.parse("2022-11-14 11:00").getTime());
            DELIST_TS.put("GLMRUSDT",  f.parse("2024-05-15 16:00").getTime());
            DELIST_TS.put("IDEXUSDT",  f.parse("2024-05-15 16:00").getTime());
            DELIST_TS.put("MDTUSDT",   f.parse("2024-05-16 16:00").getTime());
            DELIST_TS.put("RADUSDT",   f.parse("2024-05-14 16:00").getTime());
            DELIST_TS.put("RAYUSDT",   f.parse("2022-11-15 11:00").getTime());
            DELIST_TS.put("SCUSDT",    f.parse("2022-06-17 15:59").getTime());
            DELIST_TS.put("STRAXUSDT", f.parse("2024-03-15 15:59").getTime());
            DELIST_TS.put("WAVESUSDT", f.parse("2024-06-11 15:59").getTime());
        } catch (Exception e) { throw new RuntimeException(e); }
    }

    public static void main(String[] args) throws Exception {
        String host = args.length >= 1 ? args[0] : "127.0.0.1";
        int port = args.length >= 2 ? Integer.parseInt(args[1]) : 3222;
        String ns = args.length >= 3 ? args[2] : "test";
        LOG.info("CLEAN TICKER -> {}:{} ns={} set={}", host, port, ns, SET);
        LOG.info("Ghost: loai symbol khop USDCUSDT$. Cat duoi don: {} coin.", DELIST_TS.size());
        if (!"127.0.0.1".equals(host) && !"localhost".equals(host)) LOG.warn("host KHONG localhost ({})!", host);

        SimpleDateFormat kf = new SimpleDateFormat("yyyyMMdd-HHmm");
        kf.setTimeZone(TimeZone.getTimeZone("GMT+7"));

        AerospikeClient client = new AerospikeClient(host, port);
        WritePolicy wp = new WritePolicy();
        wp.sendKey = true; wp.expiration = 0; wp.recordExistsAction = RecordExistsAction.UPDATE;

        // dem (ghi NGAY trong callback, KHONG gom vao RAM -> tranh OOM)
        final long[] scanned = {0}, modified = {0}, ghostRemoved = {0}, tailRemoved = {0};

        ScanPolicy sp = new ScanPolicy(); sp.concurrentNodes = true;
        client.scanAll(sp, ns, SET, (key, rec) -> {
            if (key.userKey == null) return;
            String kstr = key.userKey.toString();
            long ts;
            try { synchronized(kf){ ts = kf.parse(kstr).getTime(); } } catch(Exception e){ return; }
            byte[] data = (byte[]) rec.getValue("data");
            if (data == null) return;
            try {
                Map<String, KlineObjectOptimized> m = MinuteDataFinal.parseFrom(Snappy.uncompress(data)).getTickersMap();
                Map<String, KlineObjectOptimized> cleaned = new HashMap<>();
                boolean changed = false;
                long localGhost = 0, localTail = 0;
                for (Map.Entry<String, KlineObjectOptimized> e : m.entrySet()) {
                    String sym = e.getKey();
                    if (sym.matches("^[A-Z0-9]+USDCUSDT$")) { changed = true; localGhost++; continue; }
                    Long dts = DELIST_TS.get(sym);
                    if (dts != null && ts > dts) { changed = true; localTail++; continue; }
                    cleaned.put(sym, e.getValue());
                }
                if (changed) {
                    // ghi NGAY (Aerospike client thread-safe). Snappy nen ngoai synchronized.
                    byte[] comp = Snappy.compress(MinuteDataFinal.newBuilder().putAllTickers(cleaned).build().toByteArray());
                    client.put(wp, new Key(ns, SET, kstr), new Bin("data", comp));
                }
                synchronized (scanned) {
                    scanned[0]++;
                    if (changed) { modified[0]++; ghostRemoved[0] += localGhost; tailRemoved[0] += localTail; }
                    if (scanned[0] % 200000 == 0) LOG.info("  scan {} record, da sua {}", scanned[0], modified[0]);
                }
            } catch (Exception ignore) {}
        }, "data");

        LOG.info("HET CLEAN: scan {} record, sua {} record | ghost xoa {} entry | duoi-don xoa {} entry", scanned[0], modified[0], ghostRemoved[0], tailRemoved[0]);

        // verify: doc lai FTT sau delist (phai KHONG con) + ghost (phai KHONG con)
        LOG.info("VERIFY:");
        SimpleDateFormat kf2 = new SimpleDateFormat("yyyyMMdd-HHmm"); kf2.setTimeZone(TimeZone.getTimeZone("GMT+7"));
        for (String[] chk : new String[][]{{"20240601-1200","FTTUSDT","phai KHONG con (delist 2022-11)"},
                                            {"20260201-1200","BTCUSDCUSDT","ghost phai KHONG con"},
                                            {"20221110-1200","FTTUSDT","phai CON (truoc delist)"}}) {
            Record r = client.get(null, new Key(ns, SET, chk[0]));
            boolean has = false;
            if (r != null) {
                byte[] d = (byte[]) r.getValue("data");
                if (d != null) has = MinuteDataFinal.parseFrom(Snappy.uncompress(d)).getTickersMap().containsKey(chk[1]);
            }
            LOG.info("  {} @ {}: {} ({})", chk[1], chk[0], has ? "CON" : "KHONG con", chk[2]);
        }
        client.close();
        LOG.info("DONE");
        System.exit(0);
    }
}
