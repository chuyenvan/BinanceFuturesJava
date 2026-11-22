package com.binance.chuyennd.tradecore.selector;

import java.io.File;
import java.util.Set;
import java.util.TreeMap;

/** ADD24 R-SIM (DEV-B, test-only): dat co TS_EXT ngay UTC tu SIM_LOSER_TS_EXT_DAYS cua sim (ON) / OFF cho MOI ngay khac
 *  trong [fromDay, toDay] vao instance TsMktExt cua JAR (ham deferTimeStop/decide cua jar giu nguyen). Khong doc store. */
public final class Add24TsxInject {
    private Add24TsxInject() {
    }

    public static int install(Set<Long> onDays, long fromDay, long toDay, File dayFile) {
        TsMktExt x = new TsMktExt((s, m) -> new TreeMap<>(), dayFile, 0L, 0L);
        int n = 0;
        for (long d = fromDay; d <= toDay; d++) {
            x.setFlagForTest(d, onDays.contains(d) ? AltEwIndex.State.ON : AltEwIndex.State.OFF);
            n++;
        }
        TsMktExt.setInstanceForTest(x);
        return n;
    }
}
