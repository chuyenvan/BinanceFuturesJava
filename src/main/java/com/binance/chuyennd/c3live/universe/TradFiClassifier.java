package com.binance.chuyennd.c3live.universe;

import com.binance.chuyennd.c3live.api.SymbolMeta;

import java.util.Collections;
import java.util.HashSet;
import java.util.Locale;
import java.util.Set;

/**
 * [V12 P0-U3] Phan loai TradFi perp (co phieu / ETF / FX / commodity ...) tu exchangeInfo. Owner quyet 10-25: LOAI khoi
 * universe mua VA khoi market level / ALT_EW cua c3_live.
 * <p>
 * CHUA XAC MINH truong phan loai that (chua co dump exchangeInfo 242 tren Oracle ngay 10-25). Luat theo thu tu, trung 1 la TradFi:
 * <ol>
 *   <li>LIST: symbol trong danh sach tuong minh (UNIVERSE_TRADFI_LIST) - fallback khi san khong gan nhan;</li>
 *   <li>contractType chua "TRADIFI" hoac "TRADFI" (vd TRADIFI_PERPETUAL);</li>
 *   <li>underlyingType co va KHONG thuoc tap crypto (mac dinh COIN, INDEX);</li>
 *   <li>underlyingSubType chua nhan TradFi (mac dinh TRADFI, STOCK(S), EQUITY, ETF, FOREX, FX, COMMODITY/IES, METAL(S)).</li>
 * </ol>
 * underlyingType thieu -> KHONG TradFi nhung verified=false (bao dem moi lan refresh).
 */
public final class TradFiClassifier {
    public static final Set<String> DEFAULT_CRYPTO_UNDERLYING = set("COIN", "INDEX");
    public static final Set<String> DEFAULT_TRADFI_TAGS = set("TRADFI", "STOCK", "STOCKS", "EQUITY", "EQUITIES", "ETF", "FOREX", "FX",
            "COMMODITY", "COMMODITIES", "METAL", "METALS");

    /** Ket qua phan loai. */
    public static final class Verdict {
        private final boolean tradfi;
        private final boolean verified;
        private final String rule;

        Verdict(boolean tradfi, boolean verified, String rule) {
            this.tradfi = tradfi;
            this.verified = verified;
            this.rule = rule;
        }

        public boolean isTradFi() { return tradfi; }
        /** false = thieu truong de ket luan (underlyingType null). */
        public boolean isVerified() { return verified; }
        /** Bang chung: luat da khop (vd "contractType=TRADIFI_PERPETUAL"). */
        public String getRule() { return rule; }

        @Override
        public String toString() { return (tradfi ? "TRADFI(" : "CRYPTO(") + rule + (verified ? ")" : ", CHUA XAC MINH)"); }
    }

    private final Set<String> cryptoUnderlying;
    private final Set<String> tradfiTags;
    private final Set<String> explicitList;

    public TradFiClassifier(Set<String> cryptoUnderlying, Set<String> tradfiTags, Set<String> explicitList) {
        this.cryptoUnderlying = upper(cryptoUnderlying == null || cryptoUnderlying.isEmpty() ? DEFAULT_CRYPTO_UNDERLYING : cryptoUnderlying);
        this.tradfiTags = upper(tradfiTags == null || tradfiTags.isEmpty() ? DEFAULT_TRADFI_TAGS : tradfiTags);
        this.explicitList = explicitList == null ? Collections.emptySet() : Collections.unmodifiableSet(new HashSet<>(explicitList));
    }

    public static TradFiClassifier defaults() { return new TradFiClassifier(null, null, null); }

    public Verdict classify(SymbolMeta m) {
        if (explicitList.contains(m.getSymbol())) return new Verdict(true, true, "LIST");
        String ct = m.getContractType() == null ? "" : m.getContractType().toUpperCase(Locale.ROOT);
        if (ct.contains("TRADIFI") || ct.contains("TRADFI")) return new Verdict(true, true, "contractType=" + m.getContractType());
        String ut = m.getUnderlyingType();
        if (ut != null && !cryptoUnderlying.contains(ut.toUpperCase(Locale.ROOT))) return new Verdict(true, true, "underlyingType=" + ut);
        for (String tag : m.getUnderlyingSubType()) {
            if (tag != null && tradfiTags.contains(tag.trim().toUpperCase(Locale.ROOT))) return new Verdict(true, true, "underlyingSubType=" + tag);
        }
        if (ut == null) return new Verdict(false, false, "underlyingType thieu");
        return new Verdict(false, true, "underlyingType=" + ut);
    }

    private static Set<String> set(String... s) {
        Set<String> out = new HashSet<>();
        Collections.addAll(out, s);
        return Collections.unmodifiableSet(out);
    }

    private static Set<String> upper(Set<String> in) {
        Set<String> out = new HashSet<>();
        for (String s : in) if (s != null && !s.trim().isEmpty()) out.add(s.trim().toUpperCase(Locale.ROOT));
        return Collections.unmodifiableSet(out);
    }
}
