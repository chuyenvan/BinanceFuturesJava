package com.binance.chuyennd.tradecore.selector;

import org.slf4j.helpers.MessageFormatter;

import java.util.Collections;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.function.Function;
import java.util.function.Supplier;

/**
 * [SHADOW2 2026-10-05] docs/runbooks/SHADOW2_K24_SKIPFULL_PLAN.md (C2): nguon von cho {@code liveBookFull}
 * (tach ra de unit test) + dong log {@code [GATE]} co dem skipFull.
 *
 * <p>Key {@code GATE_QUOTA_SKIP_WHEN_FULL} TAT => dong {@code [GATE]} y het chuoi cu ({@link #GATE_LINE_LEGACY}),
 * khong doi parser. BAT => them {@code n_skipfull=} (so ung vien PREDICT bi REJECT vi so day trong tick, da nam
 * trong {@code n_rej}) va {@code u=} (U = margin/equity luc goi liveBookFull cuoi cung trong tick, 4 chu so;
 * {@code -} neu khong tinh duoc). Thuan LOG — khong doi quyet dinh.
 */
public final class LiveBookU {

    /** Mau dong [GATE] CU (verify.sh / parser doc dung chuoi nay). */
    public static final String GATE_LINE_LEGACY =
            "[GATE] scale={} topk={} base={} thr=[{}..{}] n_cand={} n_rej={} n_pass={}";
    /** Mau khi key bat: mau cu + 2 truong o CUOI dong. */
    public static final String GATE_LINE_SKIPFULL = GATE_LINE_LEGACY + " n_skipfull={} u={}";

    private LiveBookU() {
    }

    /**
     * {margin, equity} dung cho {@code TradeUtils.managerBudget}: profile C3 (c3_shadow/c3_live) => so giay
     * ({@code c3Source}); nguoc lai BudgetManager (giu nguyen Float, ke ca null, nhu ban cu).
     */
    public static Float[] marginEquity(boolean c3On, Float bmMargin, Float bmBalance, Supplier<Float[]> c3Source) {
        if (c3On) return c3Source.get();
        return new Float[]{bmMargin, bmBalance};
    }

    /** {marginRunning, equityNow(px)} cua so giay; gia chi lay khi dang giu vi the (y het liveBookFull cu). */
    public static Float[] fromBook(ShadowBookC3 book, Function<Set<String>, Map<String, Float>> priceFetch) {
        Map<String, Float> pxOpen = book.openCount() == 0
                ? Collections.<String, Float>emptyMap()
                : priceFetch.apply(book.openSymbols());
        float equity = book.equityNow(pxOpen);
        float margin = book.marginRunning();
        return new Float[]{margin, equity};
    }

    /** U = margin/equity; NaN neu thieu so hoac equity &lt;= 0. */
    public static float u(Float margin, Float equity) {
        if (margin == null || equity == null || !(equity > 0f)) return Float.NaN;
        return margin / equity;
    }

    /** U 4 chu so (Locale.ROOT => dau cham); NaN => "-". */
    public static String fmtU(float u) {
        return Float.isNaN(u) ? "-" : String.format(Locale.ROOT, "%.4f", u);
    }

    /**
     * Dong [GATE] cua mot tick. {@code skipFullKey=false} => DUNG chuoi cu (n_pass = n_cand - n_rej).
     * {@code skipFullKey=true} => chuoi cu + {@code n_skipfull=<n> u=<U>}.
     */
    public static String gateLine(boolean skipFullKey, String scale, int topk, String base, String thrMin,
                                  String thrMax, int nCand, int nRej, int nSkipFull, float u) {
        if (!skipFullKey) {
            return MessageFormatter.arrayFormat(GATE_LINE_LEGACY, new Object[]{
                    scale, topk, base, thrMin, thrMax, nCand, nRej, nCand - nRej}).getMessage();
        }
        return MessageFormatter.arrayFormat(GATE_LINE_SKIPFULL, new Object[]{
                scale, topk, base, thrMin, thrMax, nCand, nRej, nCand - nRej, nSkipFull, fmtU(u)}).getMessage();
    }
}
