package com.binance.chuyennd.tradecore.selector;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

/**
 * [V12 R4d] Bo phan loai DUY NHAT cua universe A1 — dung CHUNG cho bo loc phia tin hieu ({@link UniverseA1Filter}) va
 * R7 cua c3_live ({@code c3live.universe.SymbolUniverseLive} qua {@code TradFiClassifier.universeA1()}).
 *
 * <p>Dinh nghia (MASTER R4d):
 * <ul>
 *   <li>TRADFI ⇔ {@code contractType} chua {@code TRADIFI} (hoac {@code TRADFI}) HOAC {@code underlyingType} ∈
 *       {@link #TRADFI_UNDERLYING} = {EQUITY, HK_EQUITY, KR_EQUITY, CN_EQUITY, COMMODITY, FX};</li>
 *   <li>INDEX ⇔ {@code underlyingType=INDEX};</li>
 *   <li>UNCLASSIFIED ⇔ khong TRADFI va thieu {@code underlyingType} (KHONG bi loai o phia tin hieu; R7 chat van khong mua);</li>
 *   <li>[PREMARKET-b] PREMARKET ⇔ {@code underlyingType=PREMARKET} (loai — CUNG R7 c3_live NOT_COIN);</li>
 *   <li>con lai CRYPTO (COIN, ...).</li>
 * </ul>
 * Loai khoi universe A1 ⇔ TRADFI, INDEX hoac PREMARKET ({@link #excluded}). Point-in-time theo onboardDate do {@link UniverseA1Filter} lo.
 * Snapshot that 2026-10-27 (936 symbol): dinh nghia nay = luat bu {COIN, INDEX, PREMARKET} cua TradFiClassifier /
 * HO2026_TRADFI_AUDIT §2 (229 TF, 3 INDEX, 0 khac biet) — xem {@code UniverseA1ClassifierTest}.
 */
public final class UniverseA1Classifier {

    public enum Kind { CRYPTO, TRADFI, INDEX, PREMARKET, UNCLASSIFIED }

    public static final Set<String> TRADFI_UNDERLYING = Collections.unmodifiableSet(new HashSet<>(Arrays.asList(
            "EQUITY", "HK_EQUITY", "KR_EQUITY", "CN_EQUITY", "COMMODITY", "FX")));

    /** Nguong R4b: nguon exchangeInfo tho phai co &gt;= 50 hop dong TradFi (contractType chua TRADIFI). */
    public static final int MIN_TRADFI = 50;
    /** Nguong R4b: so TradFi giam qua 30 % so voi lan nap truoc => canh bao (van nhan). */
    public static final double TRADFI_DROP_WARN = 0.30;

    private UniverseA1Classifier() {
    }

    public static Kind classify(String contractType, String underlyingType) {
        if (isTradFiContract(contractType)) return Kind.TRADFI;
        String ut = underlyingType == null ? "" : underlyingType.trim().toUpperCase(Locale.ROOT);
        if (TRADFI_UNDERLYING.contains(ut)) return Kind.TRADFI;
        if ("INDEX".equals(ut)) return Kind.INDEX;
        if ("PREMARKET".equals(ut)) return Kind.PREMARKET;   // [PREMARKET-b] loai khoi A1 (tin hieu + buffer + sim) = R7
        if (ut.isEmpty()) return Kind.UNCLASSIFIED;
        return Kind.CRYPTO;
    }

    public static boolean excluded(Kind k) {
        return k == Kind.TRADFI || k == Kind.INDEX || k == Kind.PREMARKET;
    }

    /** Hop dong TradFi theo contractType (dem cho nguong {@link #MIN_TRADFI}, giong R4b). */
    public static boolean isTradFiContract(String contractType) {
        String c = contractType == null ? "" : contractType.trim().toUpperCase(Locale.ROOT);
        return c.contains("TRADIFI") || c.contains("TRADFI");
    }

    /**
     * Kiem nguon exchangeInfo THO (chung cho R7 va bo loc tin hieu): co truong contractType, co truong underlyingType va
     * &gt;= {@link #MIN_TRADFI} hop dong TradFi. null = hop le.
     */
    public static String sourceProblem(int nSymbols, int nContractType, int nUnderlyingType, int nTradFiContract) {
        if (nContractType == 0) return "khong symbol nao co truong contractType (" + nSymbols + " symbol)";
        if (nUnderlyingType == 0) return "khong symbol nao co truong underlyingType (" + nSymbols + " symbol)";
        if (nTradFiContract < MIN_TRADFI) {
            return "chi " + nTradFiContract + " hop dong TradFi (< " + MIN_TRADFI + ") — khong phai exchangeInfo tho day du";
        }
        return null;
    }

    /** true neu so TradFi giam qua {@link #TRADFI_DROP_WARN} so voi lan truoc (lastTf &lt;= 0 = chua co moc). */
    public static boolean tradFiDropped(int lastTf, int tf) {
        return lastTf > 0 && tf < lastTf * (1d - TRADFI_DROP_WARN);
    }
}
