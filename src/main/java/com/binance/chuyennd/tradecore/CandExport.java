package com.binance.chuyennd.tradecore;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.io.IOException;
import java.io.Writer;

/**
 * [QUEUE_1015 P4 / T9-FIX 2026-10-15] XUAT TAP UNG VIEN cua vong selector.
 *
 * <p>Muc dich: sua loi phuong phap T9 — "chan he" (leg he thong vao lenh) khac "su kien crash".
 * Khi bat, moi ung vien DUOC DANH GIA trong vong selector duoc ghi mot dong:
 * {@code ts,symbol,bar_ret,p15,thr_base,q_t,gate_pass,gate_reason,s1,rank,topk,entered}.
 *
 * <p><b>Mac dinh TAT.</b> {@code SIM_EXPORT_CANDIDATES} rong/khong khai => {@link #ON}=false
 * => khong mo file, khong ghi, khong doi bat ky quyet dinh nao => byte-identical (parity md5
 * {@code ad26fd55} nhu ECMEAS). Bat bang {@code SIM_EXPORT_CANDIDATES=/path/cands.csv}.
 *
 * <p>Side-channel cua gate (p15/thr_base/q_t/pass/reason) duoc {@code AIRejectFilter} set khi
 * key BAT. Khong bao gio goi lai {@code GateRollingRatio.threshold} (ham do NAP buffer) — chi
 * dung lai gia tri da tinh cho chinh lan danh gia do, nen buffer/quota khong doi.
 *
 * <p>"entered" duoc chot bang {@link #finish(boolean)} ngay sau loi goi tao lenh tuong ung,
 * de phan biet "qua gate" va "qua gate NHUNG khong vao lenh" (budget/breaker/filter).
 */
public final class CandExport {

    /** Bat/tat: chi true khi {@code SIM_EXPORT_CANDIDATES} duoc khai. */
    public static volatile boolean ON = false;

    // --- side-channel do AIRejectFilter ghi (chi khi ON) ---
    public static volatile float LAST_P15 = Float.NaN;
    public static volatile float LAST_THR_BASE = Float.NaN;
    public static volatile float LAST_QT = Float.NaN;
    public static volatile boolean LAST_PASS = false;
    public static volatile String LAST_REASON = "";

    private static Writer w;
    private static boolean headerDone;
    private static String pend = null;
    private static long n = 0;

    private CandExport() {
    }

    /** Khoi tao writer. Tra ve false neu khong mo duoc (=> ON=false, khong ghi). */
    public static synchronized boolean init(String path) {
        ON = false;
        if (path == null || path.trim().isEmpty()) {
            return false;
        }
        try {
            w = new BufferedWriter(new FileWriter(path, false), 1 << 16);
            headerDone = false;
            n = 0;
            ON = true;
            return true;
        } catch (IOException e) {
            System.err.println("[CAND-EXPORT] khong mo duoc " + path + ": " + e);
            w = null;
            return false;
        }
    }

    /** Ghi header 1 lan. */
    private static void header() throws IOException {
        if (!headerDone) {
            w.write("ts,symbol,bar_ret,p15,thr_base,q_t,gate_pass,gate_reason,s1,rank,topk,entered\n");
            headerDone = true;
        }
    }

    private static void writeRow(String row) {
        try {
            header();
            w.write(row);
            w.write("\n");
            n++;
            if (n % 4096 == 0) {
                w.flush();
            }
        } catch (IOException e) {
            System.err.println("[CAND-EXPORT] ghi loi: " + e);
        }
    }

    /**
     * Mo mot dong ung vien (chua biet "entered"). Neu con dong cho thi dong cu duoc chot
     * voi entered=false truoc (an toan: khong bao gio mat dong).
     */
    public static synchronized void begin(long ts, String symbol, float barRet, Float s1,
                                          Integer rank, boolean topk, boolean gatePass,
                                          String reason, boolean gateEvaluated) {
        if (!ON) {
            return;
        }
        if (pend != null) {
            writeRow(pend + ",0");
            pend = null;
        }
        String r = clean(reason);
        pend = ts + "," + symbol + "," + f(barRet) + "," + f(LAST_P15) + "," + f(LAST_THR_BASE) + ","
                + f(LAST_QT) + "," + (gateEvaluated ? (gatePass ? "1" : "0") : "") + ","
                + (gateEvaluated ? r : "NOT_EVALUATED") + "," + (s1 == null ? "" : f(s1)) + ","
                + (rank == null ? "" : rank) + "," + (topk ? "1" : "0");
    }

    /** Chot dong dang mo: entered = co vi the moi sau loi goi. */
    public static synchronized void finish(boolean entered) {
        if (!ON || pend == null) {
            return;
        }
        writeRow(pend + "," + (entered ? "1" : "0"));
        pend = null;
    }

    /** Chot dong dang mo voi entered=false (cho cac nhanh khong tao lenh). */
    public static synchronized void finishNoEnter() {
        finish(false);
    }

    /** Ghi mot dong "khong qua gate" (Ung vien bi bo TRUOC khi danh gia gate: dang giu san / thieu ticker). */
    public static synchronized void direct(long ts, String symbol, Float s1, Integer rank, String reason) {
        if (!ON) {
            return;
        }
        String topk = (rank != null && (Configs.SELECTOR_RANK_TOPK <= 0 || rank <= Configs.SELECTOR_RANK_TOPK))
                ? "1" : "0";
        writeRow(ts + "," + symbol + ",,,,,," + clean(reason) + ","
                + (s1 == null ? "" : f(s1)) + "," + (rank == null ? "" : rank) + "," + topk + ",0");
    }

    /**
     * Chot dong dang mo; neu KHONG co dong cho (createOrder thoat TRUOC khi toi gate) thi ghi
     * mot dong fallback voi ly do cho truoc de ung vien khong bi mat.
     */
    public static synchronized void finishOrFallback(boolean entered, long ts, String symbol, Float s1,
                                                     Integer rank, String reason) {
        if (!ON) {
            return;
        }
        if (pend != null) {
            writeRow(pend + "," + (entered ? "1" : "0"));
            pend = null;
        } else {
            direct(ts, symbol, s1, rank, reason);
        }
    }

    public static synchronized void close() {
        try {
            if (pend != null) {
                writeRow(pend + ",0");
                pend = null;
            }
            if (w != null) {
                w.flush();
                w.close();
            }
        } catch (IOException ignored) {
            // dong file la best-effort
        }
        w = null;
        ON = false;
    }

    public static long count() {
        return n;
    }

    private static String f(float v) {
        return Float.isNaN(v) ? "" : Float.toString(v);
    }

    private static String clean(String s) {
        if (s == null) {
            return "";
        }
        return s.replace(',', ';').replace('\n', ' ').replace('\r', ' ');
    }
}
