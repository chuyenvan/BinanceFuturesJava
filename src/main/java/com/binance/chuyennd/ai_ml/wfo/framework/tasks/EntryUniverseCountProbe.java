package com.binance.chuyennd.ai_ml.wfo.framework.tasks;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.ai_ml.wfo.framework.WfoDataset;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

/**
 * E0 — DEM SO VI THE DOC LAP trong TAP ENTRY DONG BANG (gate ∩ rank-K, BO filter von).
 *
 * <p>Muc dich (xem `docs/reports/EXIT_MACHINE_20260730_stop_schedule.md` §PHAN 2): truoc khi export
 * zigzag path cho nghien cuu exit, phai biet tap entry dong bang co BAO NHIEU vi the DOC LAP.
 * Bang `freq_probe_table.md` cho 26 394 gate-pass (w4–w14, gate 0.010) vs 996 trade thuc = 26.5x,
 * NHUNG 26 394 dem theo <b>signal-minute</b>: cung 1 symbol pass gate nhieu phut lien tiep bi dem
 * nhieu lan. Con so dung phai <b>dedup</b>. Class nay do con so do.
 *
 * <p><b>Tai sao dung dung duong admission that:</b> chay voi {@code SIM_GATE_COUNT_ONLY=1} +
 * {@code SIM_ENTRY_UNIVERSE_DUMP=1}. Diem dump nam SAU filter AI (gate) va TRUOC breaker/budget/
 * createOrder. Vi count-only KHONG bao gio tao order nen {@code isSymbolRunning} luon false =>
 * filter von tu dong bi bo => dung y muon C1. KHONG reimplement lai logic selector (tranh lech).
 *
 * <p><b>Dedup:</b> khong biet exit that (chua co schedule) nen dedup bang COOLDOWN co dinh: sau 1 vi
 * the ao tai t tren symbol S, moi admission cua S trong [t, t+H) bi gop. Bao cao count theo nhieu H
 * => Uni chon H khop horizon exit du dinh. KHONG chon H thay Uni.
 *
 * <p>READ-ONLY: khong ghi Aerospike, khong tao order, khong doi PnL. Chi ghi 1 file CSV.
 *
 * <p>Env: {@code WFO_DATA_DIR} (dataset), {@code SIM_GATE_COUNT_ONLY=1},
 * {@code SIM_ENTRY_UNIVERSE_DUMP=1}, {@code SELECTOR_RANK_TOPK=8}, {@code SIM_MIN_MOMENTUM_15M=0.010},
 * {@code E0_OUT} (CSV out, default /home/ubuntu/claudedata/entry_universe_e0.csv),
 * {@code E0_FROM}/{@code E0_TO} (yyyyMMdd, default 20230101..20251231 = vung w4..w14).
 */
public class EntryUniverseCountProbe {
    private static final Logger LOG = LoggerFactory.getLogger(EntryUniverseCountProbe.class);

    /** Cac muc cooldown (gio) de bao cao do nhay cua so vi the doc lap. */
    private static final int[] COOLDOWN_HOURS = {0, 1, 4, 12, 24, 72, 168};

    public static void main(String[] args) throws Exception {
        if (!Configs.GATE_COUNT_ONLY || !Configs.ENTRY_UNIVERSE_DUMP) {
            LOG.error("FAIL-FAST: can SIM_GATE_COUNT_ONLY=1 VA SIM_ENTRY_UNIVERSE_DUMP=1. "
                    + "Hien GATE_COUNT_ONLY={} ENTRY_UNIVERSE_DUMP={}",
                    Configs.GATE_COUNT_ONLY, Configs.ENTRY_UNIVERSE_DUMP);
            System.exit(2);
        }
        String dataDir = System.getenv().getOrDefault("WFO_DATA_DIR", "/home/ubuntu/claudedata/wfo_dataset");
        String out = System.getenv().getOrDefault("E0_OUT", "/home/ubuntu/claudedata/entry_universe_e0.csv");
        String fromStr = System.getenv().getOrDefault("E0_FROM", "20230101");
        String toStr = System.getenv().getOrDefault("E0_TO", "20251231");
        long from = Utils.sdfFile.parse(fromStr).getTime() + 7 * Utils.TIME_HOUR;
        long to = Utils.sdfFile.parse(toStr).getTime() + 7 * Utils.TIME_HOUR;

        WfoDataset ds = WfoDataset.load(dataDir);
        LOG.info("LOAD OK market={} pred={} funding={} | range {}..{} | RANK_TOPK={} MIN_MOM15={} TICKER_SOURCE={}",
                ds.market.size(), ds.pred.size(), ds.funding.size(), fromStr, toStr,
                Configs.SELECTOR_RANK_TOPK, Configs.MIN_MOMENTUM_15M, Configs.TICKER_SOURCE);

        BudgetManagerSimple.resetInstance();
        HistoryManager.getInstance().resetCache();
        CoinRankManager.getInstance().resetCache();
        AIRejectFilter.resetCounters();
        SimulatorMarketLevelTicker1MStopLoss sim = new SimulatorMarketLevelTicker1MStopLoss();
        sim.initDataReady(ds.market, ds.pred, ds.funding, new AIRejectFilter());
        sim.simulatorWithInitEntry(from, to);

        List<long[]> raw = sim.entryUniverse;
        LOG.info("RAW admission (signal-minute) = {} | gateSeen={} gatePass={}",
                raw.size(), sim.ablationSignalSeen, sim.ablationPassCount);
        if (raw.isEmpty()) {
            LOG.error("RONG — kiem tra dataset/range/gate. KHONG ghi CSV.");
            System.exit(3);
        }

        writeCsv(out, raw);
        reportDedup(raw);
        LOG.info("========== HET E0 ==========");
        System.exit(0);   // CORE.md: tool batch PHAI exit tuong minh (executor non-daemon treo JVM)
    }

    /** Ghi CSV tho — dau vao truc tiep cho E1 (export zigzag). 1 dong = 1 admission. */
    private static void writeCsv(String path, List<long[]> raw) throws Exception {
        try (BufferedWriter w = new BufferedWriter(new FileWriter(path))) {
            w.write("ts,tsHuman,symbolId,symbol,score,priceClose,levelChangeOrdinal\n");
            for (long[] r : raw) {
                short symId = (short) r[1];
                w.write(String.format(Locale.US, "%d,%s,%d,%s,%.6f,%.10f,%d%n",
                        r[0], Utils.normalizeDateYYYYMMDDHHmm(r[0]), symId,
                        SimpleSymbolMapper.getInstance().getSymbol(symId),
                        Float.intBitsToFloat((int) r[2]),
                        Float.intBitsToFloat((int) r[3]),
                        r[4]));
            }
        }
        LOG.info("Da ghi CSV {} dong -> {}", raw.size(), path);
    }

    /**
     * Dem so vi the DOC LAP theo tung muc cooldown. Gia dinh raw da theo thu tu thoi gian tang
     * (simulator chay tien theo phut) — van xu ly an toan neu khong bang cach so voi lan cuoi/symbol.
     */
    private static void reportDedup(List<long[]> raw) {
        LOG.info("{}", "=".repeat(78));
        LOG.info(String.format(Locale.US, "%-14s %14s %14s %12s", "cooldownH", "viThe", "%soRaw", "symbolDuyNhat"));
        for (int h : COOLDOWN_HOURS) {
            long cd = h * Utils.TIME_HOUR;
            Map<Short, Long> lastEntry = new HashMap<>();
            List<Short> kept = new ArrayList<>();
            for (long[] r : raw) {
                long ts = r[0];
                short symId = (short) r[1];
                Long last = lastEntry.get(symId);
                if (last == null || ts - last >= cd) {
                    lastEntry.put(symId, ts);
                    kept.add(symId);
                }
            }
            long distinct = kept.stream().distinct().count();
            LOG.info(String.format(Locale.US, "%-14d %14d %13.2f%% %12d",
                    h, kept.size(), 100.0 * kept.size() / raw.size(), distinct));
        }
        LOG.info("{}", "=".repeat(78));
        LOG.info("cooldownH=0 -> khong dedup (= so signal-minute tho). Chon H khop horizon exit du dinh.");
        LOG.info("GATE STOP (pre-register, EXIT_MACHINE_20260730 §E0): neu so vi the o H hop ly < ~3000 "
                + "-> DUNG, xet lai C2/C3 thay vi export zigzag.");
    }
}
