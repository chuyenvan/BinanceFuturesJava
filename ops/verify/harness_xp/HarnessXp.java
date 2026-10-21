package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.ops.ExecProbe;
import com.binance.chuyennd.tradecore.selector.LiveDcaGridC3;
import com.binance.chuyennd.tradecore.selector.ShadowBookC3;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * [EXEC-PROBE harness OFFLINE] Lai so giay {@link ShadowBookC3} tren CUNG luong phut cua V11FeatHarness (NEW2) bang
 * mot luat vao lenh TAT DINH (khong phai chien luoc — chi de tao su kien mo/DCA/dong that tren so): moi phut, toi da 3
 * symbol co bar_ret &lt;= -2 % (tang dan theo bar_ret, roi ten), notional 500 USDT; DCA khi gia &lt;= 95 % gia leg dau
 * (toi da 3 leg); exit = {@code ShadowBookC3.tick} (arm/ratchet/time-stop THAT). Goi hook EXEC-PROBE DUNG nhu call
 * site live (sau openPos, chi khi {@code ExecProbe.on()}). So sanh ledger/state giua co 0 va co 1 => phai trung byte.
 */
final class HarnessXp {

    private static final Logger LOG = LoggerFactory.getLogger(HarnessXp.class);
    private static final long MIN = 60_000L;
    static final boolean XP = "1".equals(System.getenv("HARNESS_XP_BOOK"));
    private static long nOpen = 0, nDca = 0, nTickClosed = 0;

    private HarnessXp() {
    }

    static void step(long ts, Map<String, KlineObjectSimple> fin) {
        ShadowBookC3 book = ShadowBookC3.getInstance();
        // DCA truoc (cum dang giu), roi mo moi — thu tu co dinh theo ten
        List<LiveDcaGridC3.GridState> gs = book.gridStates();
        gs.sort((a, b) -> a.symbol.compareTo(b.symbol));
        for (LiveDcaGridC3.GridState g : gs) {
            KlineObjectSimple k = fin.get(g.symbol);
            if (k == null || !(k.priceClose > 0f) || g.legCount >= 3) continue;
            if (k.priceClose <= g.firstEntryPrice * 0.95f) {
                leg(book, g.symbol, k, "DCA_LEVEL1");
                nDca++;
            }
        }
        List<Object[]> cand = new ArrayList<>();
        for (Map.Entry<String, KlineObjectSimple> e : fin.entrySet()) {
            KlineObjectSimple k = e.getValue();
            if (!(k.priceOpen > 0f) || !(k.priceClose > 0f) || book.isHolding(e.getKey())) continue;
            float r = (k.priceClose - k.priceOpen) / k.priceOpen;
            if (r <= -0.02f) cand.add(new Object[]{r, e.getKey()});
        }
        cand.sort((a, b) -> {
            int c = Float.compare((Float) a[0], (Float) b[0]);
            return c != 0 ? c : ((String) a[1]).compareTo((String) b[1]);
        });
        for (int i = 0; i < cand.size() && i < 3 && book.openCount() < 25; i++) {
            String s = (String) cand.get(i)[1];
            leg(book, s, fin.get(s), "BIG_DOWN");
            nOpen++;
        }
        Map<String, Float> px = new HashMap<>();
        for (String s : book.openSymbols()) {
            KlineObjectSimple k = fin.get(s);
            if (k != null && k.priceClose > 0f) px.put(s, k.priceClose);
        }
        nTickClosed += book.tick(px, ts + MIN + 6000L);
    }

    private static void leg(ShadowBookC3 book, String s, KlineObjectSimple k, String lvl) {
        float qty = 500f / k.priceClose;
        book.openPos(s, k.startTime, k.priceClose, qty, -1, 0.2f, lvl);
        // == call site live (DetectEntrySignal2TradeNormal sau shadowHandleOrder) ==
        if (ExecProbe.on()) {
            ExecProbe.onPaperLeg(s, lvl, book.legCount(s) - 1, qty, k.priceClose, k.priceOpen, k.startTime);
        }
    }

    static void finish() {
        boolean idle = ExecProbe.awaitIdle(60_000L);
        LOG.info("[HARNESS-XP] done nOpen={} nDca={} closed={} probeOn={} idle={} summary={}", nOpen, nDca, nTickClosed,
                ExecProbe.on(), idle, ShadowBookC3.getInstance().summary(null));
    }
}
