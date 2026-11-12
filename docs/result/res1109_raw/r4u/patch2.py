"""R4u-2 BIG_DOWN-GATE: leg BIG_DOWN cua c3 KHONG qua entryGate (nhu sim Simulator:1506); giu guard seed fail-closed."""
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("patch2")


def rep(path, old, new):
    s = open(path, "rb").read().decode("utf-8")
    c = s.count(old)
    assert c == 1, (path, c, old[:80])
    open(path, "wb").write(s.replace(old, new).encode("utf-8"))


D = "src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java"
rep(D, """        filterResult = aiRejectFilter.entryGate(predict, symbolPred,
                levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE, bookFull);
""", """        if (com.binance.chuyennd.tradecore.selector.BigDownSelect.bypassGate(
                com.binance.chuyennd.tradecore.selector.LiveProfileC3.on(), levelChange)) {
            // [V12 R4u BIG_DOWN-GATE 2026-11-10] sim (Simulator createOrder: `else if (!levelChange.equals(BIG_DOWN))`)
            //   KHONG goi entryGate cho leg BIG_DOWN => live c3 cung bo gate p15 >= 0.008 cho leg nay. Chi giu guard van
            //   hanh fail-closed (seed buffer gate hong) nhu entryGate dang ap cho MOI leg moi. Profile TAT => y nguyen.
            String g = com.binance.chuyennd.tradecore.selector.BigDownSelect.bigDownGuard(
                    com.binance.chuyennd.ai_ml.onnx.entry.LiveGateRollingRatio.isSeedBlocked());
            filterResult = g != null
                    ? new AIRejectFilter.FilterResult(AIRejectFilter.FilterDecision.REJECT, g)
                    : new AIRejectFilter.FilterResult(AIRejectFilter.FilterDecision.PASS,
                    "BIG_DOWN: khong qua gate p15 (nhu sim)");
        } else {
            filterResult = aiRejectFilter.entryGate(predict, symbolPred,
                    levelChange == MarketLevelChange.PREDICT_SYMBOL_TRADE, bookFull);
        }
""")

B = "src/main/java/com/binance/chuyennd/tradecore/selector/BigDownSelect.java"
rep(B, """import java.util.ArrayList;
""", """import com.binance.chuyennd.object.MarketLevelChange;

import java.util.ArrayList;
""")
rep(B, """    /** "SYM=0.123456,SYM2=..." cho dong log [BIG_DOWN-SEL]. */""",
    """    /**
     * [V12 R4u BIG_DOWN-GATE] sim KHONG goi entryGate cho leg BIG_DOWN (chi BIG_DOWN; SMALL_UP/SMALL_DOWN_15M van qua gate
     * nguong co so nhu cu). Live: bo gate chi khi profile c3 BAT.
     */
    public static boolean bypassGate(boolean profileC3On, MarketLevelChange level) {
        return profileC3On && level == MarketLevelChange.BIG_DOWN;
    }

    /** Guard van hanh con giu cho leg BIG_DOWN khi bo gate: seed buffer gate hong => REJECT (ly do); null = qua. */
    public static String bigDownGuard(boolean seedBlocked) {
        return seedBlocked ? "GATE-SEED HONG: chan vao lenh moi (van quan ly vi the/stop)" : null;
    }

    /** "SYM=0.123456,SYM2=..." cho dong log [BIG_DOWN-SEL]. */""")

T = "src/test/java/com/binance/chuyennd/tradecore/selector/BigDownSelectTest.java"
rep(T, """import com.binance.chuyennd.object.sw.KlineObjectSimple;
""", """import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
""")
rep(T, """    @Test
    public void describeFormat() {""", """    @Test
    public void gateBypassOnlyBigDownWithC3LikeSim() {
        // sim createOrder: gate chay khi !levelChange.equals(BIG_DOWN) => chi BIG_DOWN bo gate
        for (MarketLevelChange lv : MarketLevelChange.values()) {
            boolean simBypass = lv.equals(MarketLevelChange.BIG_DOWN);
            assertEquals(lv.name(), simBypass, BigDownSelect.bypassGate(true, lv));
            assertEquals(lv.name(), false, BigDownSelect.bypassGate(false, lv));   // profile TAT => y nguyen
        }
        assertEquals(false, BigDownSelect.bypassGate(true, null));
    }

    @Test
    public void bigDownGuardSeedOnly() {
        assertEquals(null, BigDownSelect.bigDownGuard(false));
        assertTrue(BigDownSelect.bigDownGuard(true).startsWith("GATE-SEED HONG"));
    }

    @Test
    public void describeFormat() {""")
log.info("PATCH2_OK")
