/*
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.ai_ml.onnx.entry.AIRejectFilter;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedOutputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.PrintWriter;
import java.util.zip.GZIPOutputStream;

/**
 * LOG QUYET DINH TUNG TICK CHO TUNG RUN — ha tang do luong (docs/PREREG_TICKLOG.md, commit 4d80fb9).
 *
 * <p>Ly do ton tai: truoc day khong ton tai log quyet dinh theo tick cho TUNG run
 * ({@code sim.out} chi co 911 dong {@code Update} theo ngay; pool tick o {@code /home/ubuntu/ledger/}
 * doc lap voi config). Vi vay ghep cap theo tick chi lam duoc cho gene selector/gate — moi gene
 * exit/sizing/concurrency khong co tang nao du suc phan biet (docs/PREREG_GS.md muc 12.2).
 *
 * <p>Ba stream nhi phan rieng (schema chot o PREREG_TICKLOG muc 2), MOI ban ghi 32 byte,
 * big-endian, ghi qua {@code BufferedOutputStream(1MB) -> GZIPOutputStream}:
 * <ul>
 *   <li>{@code cand.bin.gz} — mot (tick, symbol) duoc XET de vao lenh + quyet dinh/ly do chan.</li>
 *   <li>{@code pos.bin.gz} — mot (phut, cum dang mo) — trang thai exit sau khi engine cap nhat.</li>
 *   <li>{@code tick.bin.gz} — mot moc 15 phut — equity mark-to-market + kich thuoc pool.</li>
 * </ul>
 *
 * <p><b>BAT BIEN BAT BUOC:</b> moi ham public o day la READ-ONLY voi trang thai engine. Bat co
 * KHONG duoc doi mot quyet dinh nao — cong nghiem thu la {@code printDone.csv} byte-identical
 * o CA HAI trang thai co (PREREG_TICKLOG muc 5). Mac dinh {@code SIM_TICKLOG} khong khai bao
 * => {@link #ON} false => moi diem chen la {@code if (false)}.
 *
 * <p><b>KHONG dung cho WFO/HPO da luong.</b> Lop nay giu state static (writer + {@link #ctxRank})
 * nen chi hop le cho MOT sim don luong. Bat trong WFO nhieu sample = log rac. Khong them khoa
 * (khoa lam cham vong nong).
 */
public final class TickDecisionLog {

    private static final Logger LOG = LoggerFactory.getLogger(TickDecisionLog.class);

    /** Co chinh — doc qua cong Cfg (khai trong profile), khong doc System.getenv truc tiep. */
    public static final boolean ON = Configs.TICKLOG;
    /** Ghi ca pool bi top-K loai (decision 8). Mac dinh OFF: +497 MB/run tren DEV. */
    public static final boolean POOL = Configs.TICKLOG_POOL;

    public static final int MAGIC = 0x544B4C47;   // "TKLG"
    public static final int VERSION = 1;
    public static final int REC_LEN = 32;

    // --- ma quyet dinh (PREREG_TICKLOG muc 2.1) ---
    public static final byte D_ENTERED = 0;
    public static final byte D_ALREADY_OPEN = 1;
    public static final byte D_NO_TICKER = 2;
    public static final byte D_NO_PRED = 3;
    public static final byte D_GATE_REJECT = 4;
    public static final byte D_NO_BUDGET = 5;
    public static final byte D_TIER3_DCA = 6;
    public static final byte D_GRID_EXHAUSTED = 7;
    public static final byte D_TOPK_CUT = 8;

    // --- bit cua cot flags trong pos.bin ---
    public static final int F_ARMED = 1;
    public static final int F_CLOSED = 2;
    public static final int F_OPEN_AT_END = 4;

    private static DataOutputStream candOut;
    private static DataOutputStream posOut;
    private static DataOutputStream tickOut;
    private static long nCandRows, nPosRows, nTickRows;
    private static String outDir;

    /** Ngu canh: hang cua ung vien dang duoc xu ly trong tick (-1 = khong phai leg selector). */
    public static short ctxRank = -1;
    private static short ctxPoolSize;
    private static short ctxNPass;
    private static short ctxNCand;

    private TickDecisionLog() { }

    private static DataOutputStream openStream(String name) throws Exception {
        FileOutputStream fos = new FileOutputStream(new File(outDir, name));
        DataOutputStream d = new DataOutputStream(new GZIPOutputStream(new BufferedOutputStream(fos, 1 << 20), 1 << 20));
        d.writeInt(MAGIC);
        d.writeInt(VERSION);
        d.writeInt(REC_LEN);
        d.writeInt(0);
        return d;
    }

    /** Mo ba file. Loi => nem RuntimeException (khong duoc chay tiep roi bao "da ghi log"). */
    public static void open() {
        outDir = Configs.TICKLOG_DIR + "/" + Configs.TICKLOG_TAG;
        File d = new File(outDir);
        if (!d.exists() && !d.mkdirs()) {
            throw new RuntimeException("TICKLOG: khong tao duoc thu muc " + outDir);
        }
        try {
            candOut = openStream("cand.bin.gz");
            posOut = openStream("pos.bin.gz");
            tickOut = openStream("tick.bin.gz");
        } catch (Exception e) {
            throw new RuntimeException("TICKLOG: khong mo duoc file log tai " + outDir, e);
        }
        LOG.info("[TICKLOG] MO {} (pool={} posEveryMin={} recLen={} ver={})",
                outDir, POOL, Configs.TICKLOG_POS_EVERY_MIN, REC_LEN, VERSION);
    }

    /** Dong ba file + ghi meta. Goi mot lan o cuoi simulatorWithInitEntry. */
    public static void close() {
        try {
            if (candOut != null) candOut.close();
            if (posOut != null) posOut.close();
            if (tickOut != null) tickOut.close();
            try (PrintWriter pw = new PrintWriter(new File(outDir, "meta.txt"), "UTF-8")) {
                pw.println("magic=TKLG");
                pw.println("version=" + VERSION);
                pw.println("recLen=" + REC_LEN);
                pw.println("headerBytes=16");
                pw.println("candRows=" + nCandRows);
                pw.println("posRows=" + nPosRows);
                pw.println("tickRows=" + nTickRows);
                pw.println("pool=" + POOL);
                pw.println("posEveryMin=" + Configs.TICKLOG_POS_EVERY_MIN);
            }
        } catch (Exception e) {
            LOG.error("[TICKLOG] loi khi dong file log tai {}", outDir, e);
        }
        LOG.info("[TICKLOG] DONG {} — cand={} pos={} tick={} dong",
                outDir, nCandRows, nPosRows, nTickRows);
    }

    // =====================================================================
    // cand.bin — 32B: ts(8) sym(2) rank(2) dec(1) lvl(1) leg(1) pad(1)
    //                 score(4) dynThr(4) predRet15m(4) price(4)
    // =====================================================================
    private static void candRow(long ts, short symbolId, byte decision, MarketLevelChange lvl,
                                int legIdx, Float symbolPred, AiPredictionData predict, float price) {
        try {
            candOut.writeLong(ts);
            candOut.writeShort(symbolId);
            candOut.writeShort(ctxRank);
            candOut.writeByte(decision);
            candOut.writeByte(lvl != null ? lvl.ordinal() : -1);
            candOut.writeByte(legIdx);
            candOut.writeByte(0);
            candOut.writeFloat(symbolPred != null ? symbolPred : Float.NaN);
            candOut.writeFloat(predict != null ? AIRejectFilter.dynThreshold(predict, symbolPred) : Float.NaN);
            candOut.writeFloat(predict != null ? predict.predReturn15M : Float.NaN);
            candOut.writeFloat(price);
            nCandRows++;
        } catch (Exception e) {
            throw new RuntimeException("TICKLOG: loi ghi cand.bin", e);
        }
    }

    /** Diem chen trong createOrder(...) — moi ly do chan + ENTERED. */
    public static void cand(long ts, short symbolId, byte decision, MarketLevelChange lvl,
                            int legIdx, Float symbolPred, AiPredictionData predict, float price) {
        candRow(ts, symbolId, decision, lvl, legIdx, symbolPred, predict, price);
    }

    /** Chan som trong vong chonCands: da co vi the tren symbol nay. */
    public static void candAlreadyOpen(long ts, short symbolId, MarketLevelChange lvl, Float symbolPred) {
        candRow(ts, symbolId, D_ALREADY_OPEN, lvl, 0, symbolPred, null, Float.NaN);
    }

    /** Chan som trong vong chonCands: khong co ticker dung o phut nay. */
    public static void candNoTicker(long ts, short symbolId, MarketLevelChange lvl, Float symbolPred) {
        candRow(ts, symbolId, D_NO_TICKER, lvl, 0, symbolPred, null, Float.NaN);
    }

    /** Toan pool bi top-K loai — CHI khi SIM_TICKLOG_POOL=1 (xem PREREG_TICKLOG muc 3). */
    public static void poolCut(long ts, long[] symbol2Pred, int nChosen) {
        short keep = ctxRank;
        for (int i = nChosen; i < symbol2Pred.length; i++) {
            ctxRank = (short) i;
            candRow(ts, (short) (symbol2Pred[i] >> 32), D_TOPK_CUT, MarketLevelChange.PREDICT_SYMBOL_TRADE,
                    0, Float.intBitsToFloat((int) symbol2Pred[i]), null, Float.NaN);
        }
        ctxRank = keep;
    }

    // =====================================================================
    // pos.bin — 32B: ts(8) sym(2) flags(1) status(1) leg(1) pad(3)
    //                entry(4) lastPrice(4) maePeak(4) priceSL(4)
    // =====================================================================
    private static void posRow(long ts, short symbolId, int flags, int status, int legCount,
                               Float entry, Float lastPrice, Float maePeak, Float priceSL) {
        try {
            posOut.writeLong(ts);
            posOut.writeShort(symbolId);
            posOut.writeByte(flags);
            posOut.writeByte(status);
            posOut.writeByte(legCount);
            posOut.writeByte(0);
            posOut.writeByte(0);
            posOut.writeByte(0);
            posOut.writeFloat(entry != null ? entry : Float.NaN);
            posOut.writeFloat(lastPrice != null ? lastPrice : Float.NaN);
            posOut.writeFloat(maePeak != null ? maePeak : Float.NaN);
            posOut.writeFloat(priceSL != null ? priceSL : Float.NaN);
            nPosRows++;
        } catch (Exception e) {
            throw new RuntimeException("TICKLOG: loi ghi pos.bin", e);
        }
    }

    /**
     * Anh chup trang thai exit cua mot cum SAU khi startUpdateOldOrderTrading da chay phut nay.
     * {@code cluster == null} => cum vua bi dong trong phut nay (dong CLOSED da duoc posClose ghi)
     * => KHONG ghi them, tranh dong rong.
     */
    public static void pos(long ts, short symbolId, OrderTargetInfoTest cluster, KlineObjectSimple ticker) {
        if (cluster == null) return;
        int every = Configs.TICKLOG_POS_EVERY_MIN;
        if (every > 1 && (ts / 60000L) % every != 0) return;
        posRow(ts, symbolId, cluster.priceSL != null ? F_ARMED : 0,
                cluster.status != null ? cluster.status.ordinal() : -1, cluster.legCount,
                cluster.priceEntry, ticker != null ? ticker.priceClose : cluster.lastPrice,
                cluster.maePeak, cluster.priceSL);
    }

    /** Dong CLOSED — goi tu closeOrder truoc khi cum bi xoa so. Luon ghi (khong thua thot). */
    public static void posClose(long ts, short symbolId, OrderTargetInfoTest cluster) {
        if (cluster == null) return;
        posRow(ts, symbolId, F_CLOSED | (cluster.priceSL != null ? F_ARMED : 0),
                cluster.status != null ? cluster.status.ordinal() : -1, cluster.legCount,
                cluster.priceEntry, cluster.priceTP != null ? cluster.priceTP : cluster.lastPrice,
                cluster.maePeak, cluster.priceSL);
    }

    /** Dong cum CON MO o cuoi ky DEV (khong di qua closeOrder). */
    public static void posOpenAtEnd(long ts, short symbolId, OrderTargetInfoTest cluster) {
        if (cluster == null) return;
        posRow(ts, symbolId, F_OPEN_AT_END | (cluster.priceSL != null ? F_ARMED : 0),
                cluster.status != null ? cluster.status.ordinal() : -1, cluster.legCount,
                cluster.priceEntry, cluster.lastPrice, cluster.maePeak, cluster.priceSL);
    }

    // =====================================================================
    // tick.bin — 32B: ts(8) pool(2) nPass(2) nCand(2) nActive(2)
    //                 balanceBasic(4) profitRealized(4) unrealClose(4) marginRunning(4)
    // =====================================================================
    /** Ngu canh pool cua tick hien tai — set trong khoi FUNDING FEE, doc boi tickIfDue. */
    public static void selCtx(int poolSize, int nPassAbs, int nCand) {
        ctxPoolSize = (short) poolSize;
        ctxNPass = (short) nPassAbs;
        ctxNCand = (short) nCand;
    }

    /**
     * Ghi mot dong tong hop moi moc 15 phut. Tinh {@code unrealClose} READ-ONLY (Sigma qty*(close-entry))
     * tren cac cum dang mo — khong ghi nguoc vao engine.
     */
    public static void tickIfDue(long ts, short[] activeIds, int activeCount,
                                 OrderTargetInfoTest[] running, KlineObjectSimple[] tickers) {
        if (ts % 900000L != 0) return;
        float unreal = 0f;
        for (int i = 0; i < activeCount; i++) {
            short id = activeIds[i];
            OrderTargetInfoTest c = running[id];
            KlineObjectSimple tk = tickers[id];
            if (c != null && c.priceEntry != null && c.quantity != null && tk != null && tk.priceClose > 0) {
                unreal += c.quantity * (tk.priceClose - c.priceEntry);
            }
        }
        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        try {
            tickOut.writeLong(ts);
            tickOut.writeShort(ctxPoolSize);
            tickOut.writeShort(ctxNPass);
            tickOut.writeShort(ctxNCand);
            tickOut.writeShort((short) activeCount);
            tickOut.writeFloat(bm.balanceBasic != null ? bm.balanceBasic : Float.NaN);
            tickOut.writeFloat(bm.profit != null ? bm.profit : Float.NaN);
            tickOut.writeFloat(unreal);
            tickOut.writeFloat(bm.marginRunning != null ? bm.marginRunning : Float.NaN);
            nTickRows++;
        } catch (Exception e) {
            throw new RuntimeException("TICKLOG: loi ghi tick.bin", e);
        }
        ctxPoolSize = 0;
        ctxNPass = 0;
        ctxNCand = 0;
    }
}
