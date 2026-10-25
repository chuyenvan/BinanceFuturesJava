import com.binance.chuyennd.ops.KillSwitchEngine;
import com.binance.chuyennd.ops.OpsHooks;
import java.io.File;
import java.lang.reflect.Method;
import java.nio.file.Files;
import java.util.function.DoubleSupplier;
import java.util.function.Supplier;

/** [A1 delta 2c] CRIT-1 hoi quy qua DUONG THAT OpsHooks.build (reflection, package-private). */
public class ProofKs2 {
    static Method BUILD;
    static KillSwitchEngine.Sink SINK = new KillSwitchEngine.Sink() {
        public void info(String m) { if (m.contains("dinh") || m.contains("LATCH")) System.out.println("  INFO " + m); }
        public void warn(String m) { if (!m.contains("BLOCK_")) System.out.println("  WARN " + m); }
    };

    static KillSwitchEngine build(boolean c3live, File shadowPeak, File c3Peak, File dir, long t) throws Exception {
        KillSwitchEngine.Params p = new KillSwitchEngine.Params();
        p.latchFile = new File(dir, "killsw_latch.json");
        p.resetFile = new File(dir, "killsw_reset.req");
        p.autoReleaseMs = 30 * 60_000L;
        p.autoReleaseCodes.add("C3");
        p.c4Capacity = true;
        DoubleSupplier pe = () -> 35000d;
        Supplier<Float> um = () -> 0.6f;
        return (KillSwitchEngine) BUILD.invoke(null, KillSwitchEngine.Mode.ACT, "act", SINK, c3live, shadowPeak, c3Peak, pe, um, t, p);
    }

    static void reset(File dir, int peak) throws Exception {
        Files.write(new File(dir, "killsw_reset.req").toPath(), ("{\"reset_at_ms\":1,\"reset_by\":\"a1\",\"reset_peak\":" + peak + "}").getBytes());
    }

    public static void main(String[] a) throws Exception {
        BUILD = OpsHooks.class.getDeclaredMethod("build", KillSwitchEngine.Mode.class, String.class, KillSwitchEngine.Sink.class,
                boolean.class, File.class, File.class, DoubleSupplier.class, Supplier.class, long.class, KillSwitchEngine.Params.class);
        BUILD.setAccessible(true);
        File dir = Files.createTempDirectory("a1d_ks").toFile();
        File shadowPeak = new File(dir, "killsw_peak");
        Files.write(shadowPeak.toPath(), "35015.29\n".getBytes());
        long shadowMtime = shadowPeak.lastModified();
        File c3Peak = new File(dir, "c3live_killsw_peak");
        final double[] eq = {10_000d};
        long t = 1_793_000_000_000L;

        System.out.println("== S1 ProofKs goc qua duong that (c3_live, PAPER_EQUITY=35000, run/killsw_peak=35015.29), tmb=10000");
        KillSwitchEngine ks = build(true, shadowPeak, c3Peak, dir, t);
        ks.attachEquitySource(() -> eq[0]);
        ks.onTickStart(t);
        ks.onPaper(t + 15_000L, 0, 0f, 10_000f);
        ks.periodic(t + 16_000L);
        System.out.println("RESULT S1 action=" + ks.requiredAction() + " codes=" + ks.latchCodes());

        System.out.println("== S2 tmb 10000 -> 5900 (-41%): C6 va A40 cung dat?");
        eq[0] = 5900d;
        long t2 = t + 20 * 60_000L;   // > PEAK_WRITE_MIN
        ks.onTickStart(t2);
        ks.onPaper(t2, 1, 100f, 5900f);
        ks.periodic(t2 + 1000L);
        System.out.println("RESULT S2 action=" + ks.requiredAction() + " codes=" + ks.latchCodes());

        System.out.println("== S3 reset_peak=0 => latch lai ngay?");
        reset(dir, 0);
        ks.periodic(t2 + 20_000L);
        System.out.println("RESULT S3a sau reset action=" + ks.requiredAction() + " codes=" + ks.latchCodes());
        ks.onPaper(t2 + 25_000L, 1, 100f, 5900f);
        ks.periodic(t2 + 30_000L);
        System.out.println("RESULT S3b sau nhip ke action=" + ks.requiredAction() + " codes=" + ks.latchCodes());

        System.out.println("== S4 reset_peak=1 => ca 2 dinh dat lai, khong latch lai");
        reset(dir, 1);
        ks.periodic(t2 + 40_000L);
        ks.onPaper(t2 + 45_000L, 1, 100f, 5900f);
        ks.periodic(t2 + 50_000L);
        System.out.println("RESULT S4 action=" + ks.requiredAction() + " codes=" + ks.latchCodes() + " c3PeakFileExists=" + c3Peak.exists());

        System.out.println("== S5 restart: engine moi, cung file => dinh nap tu dau? tmb=5800");
        eq[0] = 5800d;
        long t3 = t2 + 30 * 60_000L;
        ks.onPaper(t3, 1, 100f, 6000f);   // de ghi dinh (sau PEAK_WRITE_MIN)
        String c3PeakTxt = c3Peak.exists() ? new String(Files.readAllBytes(c3Peak.toPath())).trim() : "(khong co)";
        KillSwitchEngine ks2 = build(true, shadowPeak, c3Peak, dir, t3 + 1000L);
        ks2.attachEquitySource(() -> eq[0]);
        ks2.onTickStart(t3 + 1000L);
        ks2.onPaper(t3 + 2000L, 1, 100f, 5800f);
        ks2.periodic(t3 + 3000L);
        System.out.println("RESULT S5 c3_peak_file=" + c3PeakTxt + " action=" + ks2.requiredAction() + " codes=" + ks2.latchCodes());

        System.out.println("== S6 equity NaN/0 => giu C6");
        ks2.onPaper(t3 + 4000L, 1, 100f, Float.NaN);
        ks2.onPaper(t3 + 5000L, 1, 100f, 0f);
        System.out.println("RESULT S6 action=" + ks2.requiredAction());

        System.out.println("== S7 file dinh c3_shadow KHONG bi cham: noi dung="
                + new String(Files.readAllBytes(shadowPeak.toPath())).trim() + " mtime_doi=" + (shadowPeak.lastModified() != shadowMtime));

        System.out.println("== S8 cau hinh LIVE_C3_KILLSW_PEAK_FILE trung file so giay => fallback");
        Class<?> oc = Class.forName("com.binance.chuyennd.ops.OpsConfig");
        Method m = oc.getDeclaredMethod("c3LivePeakFile", String.class, String.class);
        m.setAccessible(true);
        System.out.println("RESULT S8 " + m.invoke(null, "run/killsw_peak", null) + " | " + m.invoke(null, "./run/../run/killsw_peak", "run/killsw_peak")
                + " | " + m.invoke(null, "/x/peak", "/x/peak"));

        System.out.println("== S9 duong c3_shadow (c3live=false) giu nguyen nghia v1.1 (san PAPER_EQUITY)");
        File d2 = Files.createTempDirectory("a1d_ks2").toFile();
        KillSwitchEngine sh = build(false, shadowPeak, null, d2, t);
        sh.onPaper(t + 1000L, 0, 0f, 34000f);
        System.out.println("RESULT S9 (ACT de thay C6) action=" + sh.requiredAction() + " codes=" + sh.latchCodes());
    }
}
