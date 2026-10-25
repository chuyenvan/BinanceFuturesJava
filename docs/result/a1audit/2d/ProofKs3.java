import com.binance.chuyennd.ops.KillSwitchEngine;
import com.binance.chuyennd.ops.OpsHooks;
import java.io.File;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.util.function.DoubleSupplier;
import java.util.function.Supplier;

/** [A1 delta 2d] MIN-19: dinh dry khong mang sang live; live->live restart giu dinh; C6/A40 khong hoi quy. */
public class ProofKs3 {
    static Method B;
    static KillSwitchEngine.Sink S = new KillSwitchEngine.Sink() {
        public void info(String m) { if (m.contains("dinh")) System.out.println("  INFO " + m); }
        public void warn(String m) { if (m.contains("dinh") || m.contains("acct_peak") || m.contains("LATCH action")) System.out.println("  WARN " + m); }
    };
    static KillSwitchEngine mk(String tag, File dir, File shadow, File c3, long t) throws Exception {
        KillSwitchEngine.Params p = new KillSwitchEngine.Params();
        p.latchFile = new File(dir, "killsw_latch.json");
        p.resetFile = new File(dir, "killsw_reset.req");
        p.c4Capacity = true;
        p.peakTag = tag;
        DoubleSupplier pe = () -> 35000d;
        Supplier<Float> um = () -> 0.6f;
        return (KillSwitchEngine) B.invoke(null, KillSwitchEngine.Mode.ACT, "act", S, true, shadow, c3, pe, um, t, p);
    }
    public static void main(String[] a) throws Exception {
        B = OpsHooks.class.getDeclaredMethod("build", KillSwitchEngine.Mode.class, String.class, KillSwitchEngine.Sink.class,
                boolean.class, File.class, File.class, DoubleSupplier.class, Supplier.class, long.class, KillSwitchEngine.Params.class);
        B.setAccessible(true);
        File dir = Files.createTempDirectory("a1e_ks").toFile();
        File shadow = new File(dir, "killsw_peak");
        Files.write(shadow.toPath(), "35015.29\n".getBytes());
        File c3 = new File(dir, "c3live_killsw_peak");
        long t = 1_793_000_000_000L;
        final double[] eq = {12_000d};
        KillSwitchEngine d = mk("dry", dir, shadow, c3, t);
        d.attachEquitySource(() -> eq[0]);
        d.onPaper(t + 1000, 0, 0f, 12_000f);
        d.periodic(t + 2000);
        d.onPaper(t + 20 * 60_000L, 0, 0f, 12_000f);   // ghi dinh dry
        d.periodic(t + 20 * 60_000L + 1000);
        System.out.println("file c3 sau dry: " + new String(Files.readAllBytes(c3.toPath())).trim() + " | latch: " + new String(Files.readAllBytes(new File(dir, "killsw_latch.json").toPath())).trim());
        long t2 = t + 3_600_000L;
        eq[0] = 7_000d;   // live tmb 7000 (< 0.6*12000)
        KillSwitchEngine l = mk("live", dir, shadow, c3, t2);
        l.attachEquitySource(() -> eq[0]);
        l.onPaper(t2 + 1000, 0, 0f, 7_000f);
        l.periodic(t2 + 2000);
        System.out.println("RESULT dry->live (dinh dry 12000, tmb live 7000): action=" + l.requiredAction() + " codes=" + l.latchCodes());
        l.onPaper(t2 + 20 * 60_000L, 0, 0f, 7_000f);
        l.periodic(t2 + 20 * 60_000L + 1000);
        long t3 = t2 + 3_600_000L;
        eq[0] = 4_000d;   // -42.9% vs 7000
        KillSwitchEngine l2 = mk("live", dir, shadow, c3, t3);
        l2.attachEquitySource(() -> eq[0]);
        l2.onPaper(t3 + 1000, 1, 100f, 4_000f);
        l2.periodic(t3 + 2000);
        System.out.println("RESULT live->live restart (dinh 7000, tmb 4000): action=" + l2.requiredAction() + " codes=" + l2.latchCodes());
        System.out.println("shadow peak file: " + new String(Files.readAllBytes(shadow.toPath())).trim());
    }
}
