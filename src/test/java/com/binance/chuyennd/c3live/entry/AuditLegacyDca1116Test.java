package com.binance.chuyennd.c3live.entry;

import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.DcaUtils;
import org.junit.Test;
import static org.junit.Assert.*;

/** AUDIT 16-11 (tam): leg DCA_LEVEL1 do LEGACY sinh tren duong that c3 (wiring gridDue = DcaUtils.shouldDcaGrid nhu C3LiveRuntime:420). */
public class AuditLegacyDca1116Test {
    static final long NOW = C3LiveEntryTest.NOW;

    @Test
    public void legacyDcaNeverOpensOrAddsOffGrid() {
        float[] lv = Configs.DCA_GRID_LEVELS;
        boolean sc = Configs.DCA_GRID_SCALAR;
        try {
            Configs.DCA_GRID_LEVELS = new float[]{-0.5f, -0.75f, -0.9f};
            Configs.DCA_GRID_SCALAR = false;
            C3LiveEntryTest.Setup s = new C3LiveEntryTest.Setup(3);
            C3LiveEntry e = s.builder().gridDue((f, p, n) -> DcaUtils.shouldDcaGrid(f, p, n)).build();
            String x = com.binance.chuyennd.c3live.entry.C3LiveFixtures.sym(0);
            // (1) c3 KHONG giu X: tin hieu DCA LEGACY -> DCA_NOT_HOLDING, 0 lenh
            assertEquals(C3LiveEntry.Outcome.DCA_NOT_HOLDING, e.onLeg(C3LiveEntryTest.leg(x, true, 0.7), NOW).outcome);
            assertEquals(0, s.gw.calls("newMarketOrder"));
            // (2) c3 giu X (leg0 @1.0); LEGACY DCA o -30% (luat cu shouldDca co the ban) -> DCA_NOT_DUE
            assertEquals(C3LiveEntry.Outcome.SUBMITTED, e.onLeg(C3LiveEntryTest.leg(x, false, 1.0), NOW).outcome);
            assertEquals(C3LiveEntry.Outcome.DCA_NOT_DUE, e.onLeg(C3LiveEntryTest.leg(x, true, 0.7), NOW + 60_000L).outcome);
            assertEquals(1, s.gw.calls("newMarketOrder"));
            // (3) o -50%: LEGACY DCA = DUNG leg grid 1 (legIdx=1); leg grid cung tick sau do KHONG nhan doi
            C3LiveEntry.Result r1 = e.onLeg(C3LiveEntryTest.leg(x, true, 0.5), NOW + 120_000L);
            assertEquals(C3LiveEntry.Outcome.SUBMITTED, r1.outcome);
            assertTrue(r1.detail, r1.detail.startsWith("legIdx=1"));
            C3LiveEntry.Outcome dup = e.onLeg(C3LiveEntryTest.leg(x, true, 0.5), NOW + 120_000L).outcome;
            assertTrue(dup.toString(), dup == C3LiveEntry.Outcome.DCA_NOT_DUE || dup == C3LiveEntry.Outcome.DCA_PENDING);
            assertEquals(2, s.gw.calls("newMarketOrder"));
            assertEquals(2, s.book.legCount(x));
            System.out.println("AUDIT1116 OK notHolding=0 offGrid=0 dupSameTick=" + dup);
        } finally {
            Configs.DCA_GRID_LEVELS = lv;
            Configs.DCA_GRID_SCALAR = sc;
        }
    }
}
