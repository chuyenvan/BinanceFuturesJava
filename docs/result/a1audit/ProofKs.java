import com.binance.chuyennd.ops.KillSwitchEngine;
import com.binance.chuyennd.ops.OpsConfig;
import com.binance.chuyennd.c3live.recon.Reconciler;
import java.io.File;
import java.nio.file.Files;

/** [A1] Chung minh: C6 cua c3_live dung dinh so GIAY (PAPER_EQUITY floor + file run/killsw_peak cua c3_shadow). */
public class ProofKs {
    public static void main(String[] a) throws Exception {
        File dir = Files.createTempDirectory("a1ks").toFile();
        File peak = new File(dir, "killsw_peak");          // = run/killsw_peak tren 242 (c3_shadow da ghi 35015.29)
        Files.write(peak.toPath(), "35015.29\n".getBytes());
        KillSwitchEngine.Params p = new KillSwitchEngine.Params();
        p.latchFile = new File(dir, "killsw_latch.json");
        p.resetFile = new File(dir, "killsw_reset.req");
        p.autoReleaseMs = 30 * 60_000L;
        p.autoReleaseCodes.add("C3");
        p.c4Capacity = true;
        KillSwitchEngine.Sink sink = new KillSwitchEngine.Sink() {
            public void info(String m) { System.out.println("INFO " + m); }
            public void warn(String m) { System.out.println("WARN " + m); }
        };
        long t = 1_793_000_000_000L;
        // y het OpsHooks.newEngine: paperEquity = LiveProfileC3::paperEquity (242: PAPER_EQUITY=35000), U_MAX 0.6
        KillSwitchEngine ks = new KillSwitchEngine(KillSwitchEngine.Mode.ACT, "act", sink, peak, () -> 35000d, () -> 0.6f, t, p);
        ks.onTickStart(t);
        // C3LiveRuntime: OpsHooks.onBook(book.openCount(), marginUsed, totalMarginBalance) — tai khoan con 10k, so trong
        ks.onPaper(t + 15_000L, 0, 0f, 10_000f);
        System.out.println("RESULT after first onBook: action=" + ks.requiredAction() + " allowNewEntry=" + ks.allowNewEntry("BTCUSDT") + " codes=" + ks.latchCodes());
        // owner reset (ops/killsw_reset.sh, reset_peak=1)
        Files.write(p.resetFile.toPath(), "{\"reset_at_ms\":1,\"reset_by\":\"owner\",\"reset_peak\":1}".getBytes());
        ks.periodic(t + 20_000L);
        System.out.println("RESULT right after reset: action=" + ks.requiredAction());
        ks.onPaper(t + 30_000L, 0, 0f, 10_000f);
        System.out.println("RESULT after next onBook: action=" + ks.requiredAction() + " codes=" + ks.latchCodes());
        // Reconciler truoc startup()
        Reconciler r = new Reconciler(null, null, null, null, null, null, () -> 0L, 0.01, 2, null);
        System.out.println("RESULT Reconciler.allowsEntry truoc startup() = " + r.allowsEntry("BTCUSDT") + " blocks=" + r.blocks());
    }
}
