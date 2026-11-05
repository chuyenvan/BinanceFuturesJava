package com.binance.chuyennd.c3live.adapter;

import com.binance.chuyennd.c3live.api.ExchangeInfo;
import com.binance.chuyennd.c3live.api.SymbolMeta;
import com.binance.chuyennd.c3live.universe.SymbolUniverseLive;
import com.binance.chuyennd.c3live.universe.TradFiClassifier;
import com.binance.chuyennd.tradecore.selector.UniverseA1Classifier;
import org.junit.Assume;
import org.junit.Test;

import java.io.File;
import java.util.Optional;

import static org.junit.Assert.*;

/**
 * [V12 R4d] R7 c3_live (SymbolUniverseLive) va bo loc tin hieu dung MOT bo phan loai: voi UNIVERSE_A1=1 R7 lay
 * {@link TradFiClassifier#universeA1()} = {@link UniverseA1Classifier}. Kiem tren exchangeInfo tho that 2026-10-27 qua CHINH
 * parser cua DryGateway (fileSource). Co tat: bo phan loai mac dinh y nguyen.
 */
public class UniverseA1R7SharedClassifierTest {

    private static final File GZ = new File("/home/ubuntu/claude_master/v12/fixtures/exchangeInfo_20261027_1140.json.gz");

    @Test
    public void r7AndSignalFilterShareOneClassifier_realSnapshot() {
        Assume.assumeTrue(GZ.isFile());
        ExchangeInfo ei = GatewayFactory.fileSource(GZ).get();
        assertTrue(ei.getSymbols().size() > 900);
        long now = 1793072475507L;
        SymbolUniverseLive.Config cfg = SymbolUniverseLive.Config.defaults().strictCoin().withClassifier(TradFiClassifier.universeA1());
        assertTrue(cfg.getClassifier().isUniverseA1());
        SymbolUniverseLive a1 = new SymbolUniverseLive(cfg, () -> ei, m -> { });
        assertNotNull(a1.apply(ei, now));
        SymbolUniverseLive def = new SymbolUniverseLive(SymbolUniverseLive.Config.defaults().strictCoin(), () -> ei, m -> { });
        assertNotNull(def.apply(ei, now));
        int tf = 0;
        int idx = 0;
        int pm = 0;
        int buyable = 0;
        for (SymbolMeta m : ei.getSymbols().values()) {
            String s = m.getSymbol();
            UniverseA1Classifier.Kind k = UniverseA1Classifier.classify(m.getContractType(), m.getUnderlyingType());
            Optional<TradFiClassifier.Verdict> v = a1.classification(s);
            assertTrue(s, v.isPresent());
            assertEquals("R7 TradFi == bo loc A1: " + s, k == UniverseA1Classifier.Kind.TRADFI, v.get().isTradFi());
            // tren snapshot that: bo phan loai mac dinh (co tat) cho CUNG ket qua => doi bo phan loai khong doi tap TF
            assertEquals("mac dinh == A1 tren snapshot that: " + s, v.get().isTradFi(), def.classification(s).get().isTradFi());
            Optional<String> why = a1.whyNotBuyable(s, now);
            if (UniverseA1Classifier.excluded(k)) {
                assertTrue("TF/INDEX khong bao gio mua duoc: " + s, why.isPresent());
                if ("TRADING".equals(m.getStatus()) && "USDT".equals(m.getQuoteAsset())) {
                    // [PREMARKET-b] PREMARKET: A1 loai, R7 strictCoin NOT_COIN (nhat quan: khong bao gio mua)
                    assertTrue(s + " " + why.get(), why.get().startsWith(k == UniverseA1Classifier.Kind.TRADFI ? "TRADFI"
                            : k == UniverseA1Classifier.Kind.INDEX ? "INDEX" : "NOT_COIN"));
                }
                if (k == UniverseA1Classifier.Kind.TRADFI) tf++;
                else if (k == UniverseA1Classifier.Kind.INDEX) idx++;
                else pm++;
            } else if (!why.isPresent()) {
                buyable++;
                assertEquals("mua duoc => CRYPTO (COIN) theo bo loc A1: " + s, UniverseA1Classifier.Kind.CRYPTO, k);
            }
        }
        assertEquals(229, tf);
        assertEquals(3, idx);
        assertEquals("[PREMARKET-b] snapshot 10-27: 1 PREMARKET (PREDICTUSDT)", 1, pm);
        assertTrue(buyable > 400);
        assertNull(SymbolUniverseLive.sourceProblem(ei));
        assertEquals(UniverseA1Classifier.MIN_TRADFI, SymbolUniverseLive.MIN_TRADFI_IN_SOURCE);
        assertEquals(UniverseA1Classifier.TRADFI_DROP_WARN, SymbolUniverseLive.TRADFI_DROP_WARN, 0d);
    }

    @Test
    public void defaultClassifierUnchanged() {
        TradFiClassifier d = SymbolUniverseLive.Config.defaults().getClassifier();
        assertFalse(d.isUniverseA1());
        assertFalse(SymbolUniverseLive.Config.defaults().strictCoin().getClassifier().isUniverseA1());
    }
}
