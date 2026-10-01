package com.binance.chuyennd.ai_ml.wfo.framework;

import com.binance.chuyennd.ai_ml.features.export.MarketDataInlineGenerator;
import com.binance.chuyennd.ai_ml.hpo.kaggle.KaggleDataLoader;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedOutputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.Map;
import java.util.TreeMap;

/**
 * KERNEL A (BD-CHAIN harness) — sinh {@code market.bin} TU TICKER FILE, khong can Aerospike.
 *
 * <p>Bo canh tranh (blocker B cua {@code docs/result/RESULT_BD_CHAIN.md} §3): buoc 1 cua day chuyen
 * doi {@code rateDown15MAvg} theo ty le universe {@code f} phai sinh lai {@code market.bin}. Tren
 * Kaggle khong co Aerospike nen phai doc ticker 1m tu dataset ticker san co
 * ({@link KaggleDataLoader#loadDailyTickersStringKey}), nuoi {@link MarketDataInlineGenerator}
 * (DUNG mot bo nao voi live/ExportMarketData2File) roi ghi file dung format
 * {@code WfoDataset.writeMarket}: {@code [count:int] × ([ts:long][down:float][up:float][down15m:float])}.
 *
 * <p><b>f</b> lay tu {@code SIM_BD_FRACTION} qua {@link Configs#BD_FRACTION} (0 = N=100 cu,
 * byte-identical). Vi vay cung 1 tool chay cho moi f.
 *
 * <p><b>Buffer lien tuc:</b> generator giu buffer truot 15 nen XUYEN NGAY (khong reset theo ngay);
 * warm-up {@link #WARMUP_DAYS} ngay TRUOC {@code start} de cua so 15m day du ngay tu phut dau.
 * (Day la dieu kien de parity: regen reset-buffer-theo-ngay chi khop ~99,2% — xem
 * {@code docs/result/RESULT_BD_DEEP_STEER.md} §1.3.)
 *
 * <p>Args: {@code [start=20210701] [end=20251231] [outFile]}.
 */
public class ExportMarketBinFromTicker {

    static final Logger LOG = LoggerFactory.getLogger(ExportMarketBinFromTicker.class);
    static final int WARMUP_DAYS = 2;
    static final String DEFAULT_START = "20210701";
    static final String DEFAULT_END = "20251231";

    public static void main(String[] args) {
        try {
            String start = args.length > 0 ? args[0] : DEFAULT_START;
            String end = args.length > 1 ? args[1] : DEFAULT_END;
            String out = args.length > 2 ? args[2]
                    : System.getProperty("user.home") + "/market.bin";

            long fairStart = Utils.sdfFile.parse(start).getTime();
            long evalEnd = Utils.sdfFile.parse(end).getTime() + Utils.TIME_DAY - 1; // tron ngay cuoi
            long warmupStart = fairStart - (long) WARMUP_DAYS * Utils.TIME_DAY;

            File parent = new File(out).getParentFile();
            if (parent != null) parent.mkdirs();

            LOG.info("🚀 KERNEL A | market.bin TU TICKER FILE | {} -> {} | warmup {}d | BD_FRACTION={}",
                    start, end, WARMUP_DAYS, Configs.BD_FRACTION);
            long n = generate(warmupStart, fairStart, evalEnd, out);
            LOG.info("✅ GHI XONG market.bin: {} dong -> {} ({} bytes)", n, out, new File(out).length());
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("❌ ExportMarketBinFromTicker FAIL", e);
            System.exit(1);
        }
    }

    /** Doc ticker theo ngay, nuoi generator lien tuc, chi ghi cac phut trong [fairStart, evalEnd]. */
    static long generate(long warmupStart, long fairStart, long evalEnd, String out) throws IOException {
        MarketDataInlineGenerator gen = new MarketDataInlineGenerator();
        TreeMap<Long, MarketDataObject> result = new TreeMap<>();

        long day = Utils.getDate(warmupStart);
        long lastDay = Utils.getDate(evalEnd);
        int nDays = 0, nMiss = 0;
        for (; day <= lastDay; day += Utils.TIME_DAY) {
            TreeMap<Long, Map<String, KlineObjectSimple>> today;
            try {
                today = KaggleDataLoader.loadDailyTickersStringKey(day);
            } catch (Exception e) {
                LOG.warn("⚠️ doc ticker ngay {} loi: {}", Utils.normalizeDateYYYYMMDD(day), e.getMessage());
                today = null;
            }
            if (today == null || today.isEmpty()) {
                nMiss++;
                continue;
            }
            nDays++;
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : today.entrySet()) {
                long ts = e.getKey();
                MarketDataObject md = gen.update(e.getValue());   // PHAI goi MOI phut de nuoi buffer
                if (md != null && ts >= fairStart && ts <= evalEnd) {
                    result.put(ts, md);
                }
            }
            if (nDays % 30 == 0) {
                LOG.info("... {} ngay | rows={} | {}", nDays, result.size(),
                        Utils.normalizeDateYYYYMMDD(day));
            }
        }
        LOG.info("{} | ngay doc={} ngay thieu={} | first={} last={}", gen.report(), nDays, nMiss,
                result.isEmpty() ? "-" : Utils.normalizeDateYYYYMMDD(result.firstKey()),
                result.isEmpty() ? "-" : Utils.normalizeDateYYYYMMDD(result.lastKey()));

        writeMarket(new File(out), result);
        return result.size();
    }

    /** DUNG format {@code WfoDataset.writeMarket} (private ben do) — [count] × [ts][down][up][down15m]. */
    static void writeMarket(File f, TreeMap<Long, MarketDataObject> m) throws IOException {
        try (DataOutputStream o = new DataOutputStream(
                new BufferedOutputStream(new FileOutputStream(f), 1 << 20))) {
            o.writeInt(m.size());
            for (Map.Entry<Long, MarketDataObject> e : m.entrySet()) {
                o.writeLong(e.getKey());
                MarketDataObject d = e.getValue();
                o.writeFloat(d.rateDownAvg);
                o.writeFloat(d.rateUpAvg);
                o.writeFloat(d.rateDown15MAvg);
            }
        }
    }
}
