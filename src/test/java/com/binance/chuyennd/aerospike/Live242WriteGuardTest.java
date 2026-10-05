package com.binance.chuyennd.aerospike;

import ch.qos.logback.classic.Logger;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.read.ListAppender;
import com.aerospike.client.AerospikeClient;
import com.aerospike.client.policy.ClientPolicy;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.slf4j.LoggerFactory;

import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

/**
 * [FIX_NO_WRITE_242] (a) env thieu (= 242) => ham ghi DI TOI client 242; (b) shadow host => ghi bi bo,
 * doc VAN di toi client 242; (c) moi diem ghi 242 trong DataManager/Roller deu sau guard (kiem source).
 *
 * <p>AN TOAN: client242 bi thay bang {@link OfflineClient} (ctor protected, KHONG ket noi, cluster=null)
 * => moi put/get/operate nem loi ngay, ham DataManager bat va log ERROR. Test dem log do de biet
 * "lenh da toi client". Khong bao gio cham mang/242 that (assert instanceof truoc moi test).
 */
public class Live242WriteGuardTest {

    /** Client gia khong ket noi. */
    static final class OfflineClient extends AerospikeClient {
        OfflineClient() {
            super(new ClientPolicy());
        }
    }

    private Object savedClient;
    private ListAppender<ILoggingEvent> app;
    private Logger dmLog;

    private static Field clientField() throws Exception {
        Field f = DataManagerAerospikeFloatSim.class.getDeclaredField("client242");
        f.setAccessible(true);
        return f;
    }

    @Before
    public void setUp() throws Exception {
        Field f = clientField();
        savedClient = f.get(null);
        f.set(null, new OfflineClient());
        // chot an toan: tu day getClient242() tra client gia, KHONG mo ket noi toi AEROSPIKE_HOST that
        assertTrue(f.get(null) instanceof OfflineClient);
        assertTrue(DataManagerAerospikeFloatSim.getClient242() instanceof OfflineClient);
        dmLog = (Logger) LoggerFactory.getLogger(DataManagerAerospikeFloatSim.class);
        app = new ListAppender<>();
        app.start();
        dmLog.addAppender(app);
    }

    @After
    public void tearDown() throws Exception {
        clientField().set(null, savedClient);
        dmLog.detachAppender(app);
        Live242WriteGuard.resetForTest(null);
    }

    private long count(String needle) {
        return app.list.stream().filter(e -> e.getFormattedMessage().contains(needle)).count();
    }

    @Test
    public void decideMatrix() {
        assertTrue(Live242WriteGuard.decide(null, null));          // 242: env thieu => ghi nhu cu
        assertTrue(Live242WriteGuard.decide("", ""));
        assertTrue(Live242WriteGuard.decide("true", null));
        assertTrue(Live242WriteGuard.decide(null, "false"));
        assertTrue(Live242WriteGuard.decide("garbage", "1"));     // chi "true"/"false" tuong minh moi doi
        assertFalse(Live242WriteGuard.decide(null, "true"));
        assertFalse(Live242WriteGuard.decide(null, " TRUE "));
        assertFalse(Live242WriteGuard.decide("false", null));
        assertFalse(Live242WriteGuard.decide("true", "true"));    // shadow host thang enabled
    }

    @Test
    public void mode242_envMissing_writesReachClient() {
        assertNull("test phai chay KHONG co env shadow", System.getenv(Live242WriteGuard.KEY_SHADOW_HOST));
        assertNull(System.getenv(Live242WriteGuard.KEY_ENABLED));
        Live242WriteGuard.resetForTest(null);                     // doc env that (thieu) nhu tren 242
        assertTrue(Live242WriteGuard.writesEnabled());
        DataManagerAerospikeFloatSim.saveAiPrediction1M(new AiPredictionData(0L, 0.01f, 0.02f));
        assertEquals(1, count("Error saving AI Pred 1M"));        // put() da duoc goi tren client 242
        DataManagerAerospikeFloatSim.saveSymbolMapping("ZZZTESTUSDT", (short) 30000);
        assertEquals(1, count("Error saving symbol mapping"));    // operate() da duoc goi
        Map<Short, float[]> m = new HashMap<>();
        m.put((short) 1, new float[]{0.1f});
        DataManagerAerospikeFloatSim.saveDcaPredictions1M(0L, m);
        assertEquals(1, count("Error saving DCA Pred"));
    }

    @Test
    public void shadowHost_writesSkipped_readsKept() {
        Live242WriteGuard.resetForTest(false);                    // = LIVE_IS_SHADOW_HOST=true
        assertFalse(Live242WriteGuard.allowed("x"));
        DataManagerAerospikeFloatSim.saveAiPrediction1M(new AiPredictionData(0L, 0.01f, 0.02f));
        DataManagerAerospikeFloatSim.saveSymbolMapping("ZZZTESTUSDT", (short) 30000);
        Map<Short, float[]> m = new HashMap<>();
        m.put((short) 1, new float[]{0.1f});
        DataManagerAerospikeFloatSim.saveDcaPredictions1M(0L, m);
        Map<Long, Float> one = new HashMap<>();
        one.put(0L, 1f);
        assertEquals(0, DataManagerAerospikeFloatSim.writeMetricMap242("s", "b", "ZZZTESTUSDT", one));
        DataManagerAerospikeFloatSim.writeAccum242("s", "b", "ZZZTESTUSDT", 0L, 0, 0, 0);
        assertEquals("khong ham ghi nao duoc toi client", 0, count("Error saving") + count("Error writeAccum242"));
        // doc 242 GIU NGUYEN: get() van duoc goi tren client 242
        assertNull(DataManagerAerospikeFloatSim.getAiPredictionAtTime(0L));
        assertEquals(1, count("Error getting AI Pred"));
    }

    private static final Pattern WRITE = Pattern.compile(
            "getClient242\\(\\)\\s*\\.(put|operate|delete|add|append|touch)\\(|writeMetricMapTo\\(getClient242\\(\\)|client\\.put\\(");
    private static final Pattern METHOD = Pattern.compile("^\\s*(public|private|protected)\\s+(static\\s+)?[\\w<>\\[\\], ]+\\s+\\w+\\s*\\(");

    /** Moi diem GHI 242 nam trong ham da co guard o phia truoc (dong method -> diem ghi). */
    private static List<String> unguarded(String path, boolean onlyAfterGet242) throws Exception {
        List<String> lines = Files.readAllLines(Paths.get(path), StandardCharsets.UTF_8);
        List<String> bad = new ArrayList<>();
        for (int i = 0; i < lines.size(); i++) {
            String l = lines.get(i);
            if (!WRITE.matcher(l).find() || l.trim().startsWith("//") || l.trim().startsWith("*")) continue;
            int j = i;
            while (j > 0 && !METHOD.matcher(lines.get(j)).find()) j--;
            boolean get242 = false, guarded = false;
            for (int k = j; k <= i; k++) {
                if (lines.get(k).contains("Live242WriteGuard.allowed(")) guarded = true;
                if (lines.get(k).contains("getClient242()")) get242 = true;
            }
            if (onlyAfterGet242 && !get242) continue;              // client.put(...) cua client khac (vd Oracle)
            if (!guarded) bad.add((i + 1) + ": " + l.trim());
        }
        return bad;
    }

    @Test
    public void everyWrite242IsGuarded_source() throws Exception {
        String base = "src/main/java/com/binance/chuyennd/";
        List<String> bad = unguarded(base + "aerospike/DataManagerAerospikeFloatSim.java", true);
        assertTrue("diem ghi 242 CHUA co guard: " + bad, bad.isEmpty());
        bad = unguarded(base + "websocket/Kline15m4hForwardRoller.java", true);
        assertTrue("diem ghi 242 CHUA co guard: " + bad, bad.isEmpty());
        // doc 242 KHONG duoc gan guard (shadow can doc 242)
        List<String> dm = Files.readAllLines(Paths.get(base + "aerospike/DataManagerAerospikeFloatSim.java"),
                StandardCharsets.UTF_8);
        int start = -1;
        for (int i = 0; i < dm.size(); i++) {
            if (dm.get(i).contains("public static AiPredictionData getAiPredictionAtTime(long timestamp)")) start = i;
        }
        assertTrue(start > 0);
        for (int k = start; k < start + 15; k++) assertFalse(dm.get(k).contains("Live242WriteGuard"));
    }
}
