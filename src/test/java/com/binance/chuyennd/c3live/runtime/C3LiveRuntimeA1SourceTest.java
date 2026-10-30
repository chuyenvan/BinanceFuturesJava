package com.binance.chuyennd.c3live.runtime;

import com.binance.chuyennd.c3live.adapter.GatewayFactory;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;

import static org.junit.Assert.*;

/** [V12 R4d] UNIVERSE_A1=1 + dry: R7 va bo loc tin hieu PHAI doc CUNG 1 file exchangeInfo (khac => nem => manage-only). */
public class C3LiveRuntimeA1SourceTest {

    @Rule
    public TemporaryFolder tmp = new TemporaryFolder();

    @Test
    public void drySameFileRequired() throws Exception {
        File a = tmp.newFile("c3live_exchangeInfo.json");
        File b = tmp.newFile("other.json");
        C3LiveRuntime.checkA1SameSource(GatewayFactory.Mode.DRY, a.getPath(), a.getAbsolutePath());
        C3LiveRuntime.checkA1SameSource(GatewayFactory.Mode.DRY, new File(a.getParentFile(), "./c3live_exchangeInfo.json").getPath(),
                a.getPath());
        try {
            C3LiveRuntime.checkA1SameSource(GatewayFactory.Mode.DRY, a.getPath(), b.getPath());
            fail("khac file => phai nem");
        } catch (IllegalStateException e) {
            assertTrue(e.getMessage(), e.getMessage().contains("CUNG 1 file"));
        }
        // live: R7 doc qua API => chi canh bao, khong nem
        C3LiveRuntime.checkA1SameSource(GatewayFactory.Mode.LIVE, a.getPath(), b.getPath());
    }
}
