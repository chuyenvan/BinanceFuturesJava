package com.binance.chuyennd.ops;

import org.junit.Assume;
import org.junit.Test;

import java.io.File;
import java.util.Collections;

import static org.junit.Assert.*;

/** [V11D OPS] co mac dinh (env khong dat) => moi hook la no-op, khong nem, khong tao file. */
public class OpsHooksTest {

    @Test
    public void hooksAreNoOpByDefault() {
        Assume.assumeTrue(System.getenv(OpsConfig.KEY_KILLSW_MODE) == null);
        Assume.assumeTrue(System.getenv(OpsConfig.KEY_HEARTBEAT) == null);
        File hb = new File(OpsConfig.DEFAULT_HEARTBEAT_FILE);
        File pk = new File(OpsConfig.DEFAULT_KILLSW_STATE_FILE);
        boolean hb0 = hb.exists(), pk0 = pk.exists();
        OpsHooks.onTickStart();
        OpsHooks.onMarketData(null);
        OpsHooks.onMarketData(Collections.emptyMap());
        OpsHooks.onApiResult("positionRisk", false);
        OpsHooks.onPaperBook(null);
        OpsHooks.onPaperTick(null, null);
        assertEquals(hb0, hb.exists());
        assertEquals(pk0, pk.exists());
    }
}
