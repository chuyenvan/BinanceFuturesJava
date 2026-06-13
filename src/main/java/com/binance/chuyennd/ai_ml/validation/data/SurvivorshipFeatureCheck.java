package com.binance.chuyennd.ai_ml.validation.data;

import com.aerospike.client.*;
import com.aerospike.client.Record;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.proto.MinuteDataFinalProto.KlineObjectOptimized;
import com.binance.chuyennd.proto.MinuteDataFinalProto.MinuteDataFinal;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.text.SimpleDateFormat;
import java.util.*;

/**
 * TASK-005 B6 — sample-check survivorship: tại ~8 mốc (quanh sập LUNA 2022-05, FTT 2022-11 + mốc thường),
 * tính lại feature market-level CŨ ({@link MarketBigChangeDetector#calMarketData}: rateDownAvg/rateUpAvg/
 * rateDown15MAvg = avg top-~100 crashed/up/15m-drawdown) theo 2 cấu hình: (1) GỒM 30 core coin die,
 * (2) LOẠI 30 core. So % khác biệt → survivorship có méo feature thật không. KHÔNG re-export 100%, read-only.
 *
 * TÁI DÙNG calMarketData (một bộ não). Đọc 15 nến/mốc từ 242 (nguồn sim đọc), window 15m như generator.
 */
public class SurvivorshipFeatureCheck {

    private static final Logger LOG = LoggerFactory.getLogger(SurvivorshipFeatureCheck.class);
    private static final String NS = Configs.AEROSPIKE_NAMESPACE;
    private static final String SET = DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER;
    private static final int WINDOW = Configs.NUMBER_TICKER_CAL_RATE_CHANGE; // 15

    private static final Set<String> CORE30 = new HashSet<>(Arrays.asList(
            "LUNAUSDT","ANCUSDT","SRMUSDT","DODOUSDT","HNTUSDT","AUDIOUSDT","AKROUSDT","BTSUSDT","GALUSDT","TOMOUSDT",
            "RNDRUSDT","ANTUSDT","BZRXUSDT","YFIIUSDT","BTTUSDT","KEEPUSDT","FOOTBALLUSDT","NUUSDT","BLUEBIRDUSDT","DOTECOUSDT",
            "RAYUSDT","WAVESUSDT","FTTUSDT","DGBUSDT","SCUSDT","GLMRUSDT","MDTUSDT","IDEXUSDT","RADUSDT","STRAXUSDT"));

    // mốc (12:00 GMT+7): quanh sập + thường
    private static final String[] TS = {
            "20210615-1200",  // thường (sớm, nhiều core còn sống)
            "20220511-1200",  // LUNA sập
            "20220512-1200",  // LUNA sập
            "20220618-1200",  // hậu LUNA / 3AC
            "20221109-1200",  // FTT/FTX sập
            "20221110-1200",  // FTT sập
            "20230815-1200",  // thường
            "20240315-1200",  // bull
            "20250915-1200"}; // gần đây (chỉ ~10 coin còn-niêm-yết sống)

    public static void main(String[] args) {
        try {
            AerospikeClient c = DataManagerAerospikeFloatSim.getClient242();
            LOG.info("🔬 B6 survivorship feature-check | diedSymbol(filter sẵn)={} | window={}", com.binance.client.constant.Constants.diedSymbol, WINDOW);
            LOG.info(String.format("%-14s | %5s | %-22s | %-22s | %-22s", "mốc", "#core", "rateDownAvg cũ→sửa(Δ%)", "rateUpAvg", "rateDown15MAvg"));
            for (String ts : TS) {
                long end = parse(ts);
                // đọc WINDOW nến (end-14..end); snapshot = nến end; max/min = qua cửa sổ
                Map<String, KlineObjectSimple> snapshot = null;
                Map<String, Float> maxP = new HashMap<>(), minP = new HashMap<>();
                for (int i = WINDOW - 1; i >= 0; i--) {
                    long t = end - (long) i * 60000L;
                    Map<String, KlineObjectSimple> rec = read(c, t);
                    if (rec == null) continue;
                    for (Map.Entry<String, KlineObjectSimple> e : rec.entrySet()) {
                        maxP.merge(e.getKey(), e.getValue().maxPrice, Math::max);
                        minP.merge(e.getKey(), e.getValue().minPrice, Math::min);
                    }
                    if (i == 0) snapshot = rec;
                }
                if (snapshot == null) { LOG.info("{} | (không có record)", ts); continue; }
                int coreAlive = 0;
                for (String s : CORE30) if (snapshot.containsKey(s)) coreAlive++;

                MarketDataObject all = MarketBigChangeDetector.calMarketData(snapshot, maxP, minP);
                // cấu hình LOẠI 30 core
                Map<String, KlineObjectSimple> snapEx = new HashMap<>(snapshot);
                Map<String, Float> maxEx = new HashMap<>(maxP), minEx = new HashMap<>(minP);
                for (String s : CORE30) { snapEx.remove(s); maxEx.remove(s); minEx.remove(s); }
                MarketDataObject ex = MarketBigChangeDetector.calMarketData(snapEx, maxEx, minEx);

                LOG.info(String.format(Locale.US, "%-14s | %5d | %9.5f→%9.5f (%+.1f%%) | %9.5f→%9.5f (%+.1f%%) | %9.5f→%9.5f (%+.1f%%)",
                        ts, coreAlive,
                        all.rateDownAvg, ex.rateDownAvg, pct(all.rateDownAvg, ex.rateDownAvg),
                        all.rateUpAvg, ex.rateUpAvg, pct(all.rateUpAvg, ex.rateUpAvg),
                        all.rateDown15MAvg, ex.rateDown15MAvg, pct(all.rateDown15MAvg, ex.rateDown15MAvg)));
            }
            LOG.info("Ghi chú: cũ=GỒM 30 core, sửa=LOẠI 30 core. Δ% = (GỒM−LOẠI)/|LOẠI|. #core = số coin die còn sống tại mốc.");
        } catch (Exception e) {
            LOG.error("SurvivorshipFeatureCheck lỗi", e);
        }
    }

    private static float pct(float withAll, float without) {
        if (Math.abs(without) < 1e-9) return 0f;
        return (withAll - without) / Math.abs(without) * 100f;
    }

    private static Map<String, KlineObjectSimple> read(AerospikeClient c, long ms) throws Exception {
        Record r = c.get(null, new Key(NS, SET, FMT.get().format(new Date(ms))));
        if (r == null) return null;
        byte[] data = (byte[]) r.getValue("data");
        if (data == null) return null;
        Map<String, KlineObjectOptimized> m = MinuteDataFinal.parseFrom(Snappy.uncompress(data)).getTickersMap();
        Map<String, KlineObjectSimple> out = new HashMap<>();
        for (Map.Entry<String, KlineObjectOptimized> e : m.entrySet()) {
            KlineObjectOptimized p = e.getValue();
            KlineObjectSimple k = new KlineObjectSimple();
            k.startTime = ms; k.priceOpen = p.getPriceOpen(); k.maxPrice = p.getMaxPrice();
            k.minPrice = p.getMinPrice(); k.priceClose = p.getPriceClose(); k.totalUsdt = p.getTotalUsdt();
            out.put(e.getKey(), k);
        }
        return out;
    }

    private static final ThreadLocal<SimpleDateFormat> FMT =
            ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyyMMdd-HHmm")); // GMT+7 (TimeZoneGuard)

    private static long parse(String key) { try { return FMT.get().parse(key).getTime(); } catch (Exception e) { throw new RuntimeException(e); } }
}
