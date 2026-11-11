package com.binance.chuyennd.aerospike;

import org.junit.Assume;
import org.junit.Test;

import java.io.File;
import java.util.*;

import static org.junit.Assert.assertEquals;

/** [AS-FILE] roundtrip file (bit float chinh xac) + so voi Aerospike that khi env AS_PARITY_MAPPER/AS_PARITY_FUNDING tro toi dump. */
public class SimDataFilesTest {

    @Test
    public void roundtripMapperAndFundingBitExact() throws Exception {
        Map<String, Short> m = new HashMap<>();
        m.put("BTCUSDT", (short) 1);
        m.put("ETHUSDT", (short) 2);
        m.put("1000PEPEUSDT", (short) 845);
        Map<String, TreeMap<Long, Float>> f = new HashMap<>();
        TreeMap<Long, Float> a = new TreeMap<>();
        a.put(1640995200000L, 1.0E-4f);
        a.put(1641024000000L, -0.00037512f);
        a.put(1641052800000L, Float.intBitsToFloat(0x80000000));   // -0.0
        f.put("BTCUSDT", a);
        File fm = File.createTempFile("asmap", ".tsv.gz"), ff = File.createTempFile("asfund", ".tsv.gz");
        SimDataFiles.writeMapper(m, fm.getPath());
        SimDataFiles.writeFunding(f, ff.getPath());
        assertEquals(m, new HashMap<>(SimDataFiles.loadMapper(fm.getPath())));
        SimDataFiles.resetCacheForTest();
        Map<String, TreeMap<Long, Float>> g = SimDataFiles.loadFunding(ff.getPath());
        assertEquals(f.keySet(), g.keySet());
        for (Map.Entry<Long, Float> e : a.entrySet()) {
            assertEquals(Float.floatToRawIntBits(e.getValue()), Float.floatToRawIntBits(g.get("BTCUSDT").get(e.getKey())));
        }
        assertEquals(0, SimDataFiles.fundingOne(ff.getPath(), "NOPEUSDT").size());
        SimDataFiles.resetCacheForTest();
    }

    /** Chay tay tren Oracle: AS_PARITY_MAPPER=<dump> AS_PARITY_FUNDING=<dump> mvn -Dtest=SimDataFilesTest test (doc Aerospike, chi doc). */
    @Test
    public void fileEqualsAerospikeWhenConfigured() throws Exception {
        String pm = System.getenv("AS_PARITY_MAPPER"), pf = System.getenv("AS_PARITY_FUNDING");
        Assume.assumeTrue(pm != null && pf != null);
        Map<String, Short> as = DataManagerAerospikeFloatSim.loadSymbolMapperAerospike();
        assertEquals(new HashMap<>(as), new HashMap<>(SimDataFiles.loadMapper(pm)));
        SimDataFiles.resetCacheForTest();
        Map<String, TreeMap<Long, Float>> af = DataManagerAerospikeFloatSim.getAllFundingMapAerospike();
        Map<String, TreeMap<Long, Float>> ff = SimDataFiles.loadFunding(pf);
        assertEquals(af.keySet(), ff.keySet());
        for (String s : af.keySet()) {
            assertEquals(s, af.get(s).keySet(), ff.get(s).keySet());
            for (Map.Entry<Long, Float> e : af.get(s).entrySet()) {
                assertEquals(s + "@" + e.getKey(), Float.floatToRawIntBits(e.getValue()), Float.floatToRawIntBits(ff.get(s).get(e.getKey())));
            }
        }
        SimDataFiles.resetCacheForTest();
    }
}
