package com.binance.chuyennd.c3live.log;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.math.BigDecimal;
import java.util.function.Consumer;

/**
 * [V12 C14] 1 dong co dinh cot cho moi request/response lenh c3_live:
 * <pre>[C3-LIVE-ORDER] ts=.. cid=.. oid=.. sym=.. side=.. type=.. qty=.. px=.. status=.. lat_ms=.. err=.. reason=..</pre>
 * Cot luon du 12, gia tri rong = "-", khoang trang / '=' / ky tu dieu khien -> '_' (luon 1 dong). KHONG BAO GIO nhan key /
 * secret / signature / query string: lop nay chi nhan cac truong nghiep vu ben duoi.
 * Dry adapter (vong 2) dung cung cot voi tag {@link #DRY_TAG}.
 */
public final class OrderAuditLog {
    public static final String LIVE_TAG = "[C3-LIVE-ORDER]";
    public static final String DRY_TAG = "[LIVE-DRY]";
    static final int MAX_FIELD = 160;

    private static final Logger LOG = LoggerFactory.getLogger(OrderAuditLog.class);

    private final String tag;
    private final Consumer<String> sink;

    /** Ghi qua SLF4J (INFO; WARN neu co err). */
    public OrderAuditLog(String tag) {
        this(tag, null);
    }

    /** sink != null: nhan dong da format (test / bo dem); van KHONG ghi them qua SLF4J. */
    public OrderAuditLog(String tag, Consumer<String> sink) {
        this.tag = tag == null ? LIVE_TAG : tag;
        this.sink = sink;
    }

    public static OrderAuditLog live() { return new OrderAuditLog(LIVE_TAG); }

    public static OrderAuditLog dry() { return new OrderAuditLog(DRY_TAG); }

    public String getTag() { return tag; }

    /** Format + ghi; tra lai dong da ghi. */
    public String record(Entry e) {
        String line = format(tag, e);
        if (sink != null) {
            sink.accept(line);
        } else if (e.errCode != null && !e.errCode.isEmpty()) {
            LOG.warn(line);
        } else {
            LOG.info(line);
        }
        return line;
    }

    public static String format(String tag, Entry e) {
        StringBuilder sb = new StringBuilder(256);
        sb.append(tag);
        col(sb, "ts", e.ts == 0 ? null : Long.toString(e.ts));
        col(sb, "cid", e.clientOrderId);
        col(sb, "oid", e.orderId == 0 ? null : Long.toString(e.orderId));
        col(sb, "sym", e.symbol);
        col(sb, "side", e.side);
        col(sb, "type", e.type);
        col(sb, "qty", dec(e.qty));
        col(sb, "px", dec(e.price));
        col(sb, "status", e.status);
        col(sb, "lat_ms", e.latencyMs < 0 ? null : Long.toString(e.latencyMs));
        col(sb, "err", e.errCode);
        col(sb, "reason", e.reason);
        return sb.toString();
    }

    private static String dec(BigDecimal d) { return d == null ? null : d.toPlainString(); }

    private static void col(StringBuilder sb, String k, String v) {
        sb.append(' ').append(k).append('=').append(sanitize(v));
    }

    static String sanitize(String v) {
        if (v == null || v.isEmpty()) return "-";
        StringBuilder sb = new StringBuilder(Math.min(v.length(), MAX_FIELD));
        int n = 0;
        for (int i = 0; i < v.length() && n < MAX_FIELD; i++, n++) {
            char c = v.charAt(i);
            if (Character.isWhitespace(c) || Character.isISOControl(c) || c == '=' || Character.isSpaceChar(c)) sb.append('_');
            else sb.append(c);
        }
        if (v.length() > MAX_FIELD) sb.append("~");
        return sb.toString();
    }

    /** Ban ghi 1 su kien lenh. Moi truong co the null (-> "-"). */
    public static final class Entry {
        long ts;
        String clientOrderId;
        long orderId;
        String symbol;
        String side;
        String type;
        BigDecimal qty;
        BigDecimal price;
        String status;
        long latencyMs = -1;
        String errCode;
        String reason;

        public static Entry of(long ts) { Entry e = new Entry(); e.ts = ts; return e; }
        public Entry clientOrderId(String v) { clientOrderId = v; return this; }
        public Entry orderId(long v) { orderId = v; return this; }
        public Entry symbol(String v) { symbol = v; return this; }
        public Entry side(String v) { side = v; return this; }
        public Entry type(String v) { type = v; return this; }
        public Entry qty(BigDecimal v) { qty = v; return this; }
        /** Gia khop (MARKET) hoac stop/trigger (STOP_MARKET). */
        public Entry price(BigDecimal v) { price = v; return this; }
        public Entry status(String v) { status = v; return this; }
        public Entry latencyMs(long v) { latencyMs = v; return this; }
        /** Ma loi san (vd "-2019") hoac ErrorKind; null = OK. */
        public Entry errCode(String v) { errCode = v; return this; }
        public Entry reason(String v) { reason = v; return this; }
    }
}
