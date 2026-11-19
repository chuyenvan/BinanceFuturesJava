package com.binance.chuyennd.c3live.runtime;

import com.binance.chuyennd.tradecore.selector.LiveProfileC3;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.StandardOpenOption;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

/**
 * [W3A muc 6 ? AUDIT_GOLIVE_1116_B B-09] Khoa khoi dong c3_live: JVM {@code LIVE_ADAPTER=live} khoi dong ma KHONG co
 * {@code run/KILL_SWITCH} (moi script go-live ? micro_on/pilot_on/rollback ? DAT KILL_SWITCH truoc khi dung bot va chi go
 * sau hau kiem) => coi la khoi dong KHONG qua script (crash/watchdog/reboot/Utils.reset/restart tay) => JVM TU tao
 * {@code run/KILL_SWITCH} token {@code c3live_boot <TS>} => PUSH OFF (khong mo lenh moi, khong DCA); quan ly vi the dang mo
 * (trailing/stop san/time-stop/X14/FLATTEN) chay binh thuong. Mo khoa = owner {@code MODE=undrain golive_live_off.sh}.
 * <ul>
 *   <li>KILL_SWITCH da co (script / drain / monitor) => KHONG dung vao (khong ghi de token ? hau kiem script grep token).</li>
 *   <li>Khong ghi duoc file => khoa trong RAM ({@link LiveProfileC3#setBootLockMem}) toi khi restart + canh bao.</li>
 *   <li>Chi chay 1 lan / JVM (runtime thu tao lai moi 60 s KHONG khoa lai sau khi owner da undrain).</li>
 *   <li>Env {@code C3_BOOT_KILLSWITCH=false} => tat han (y nhu jar 5e10325b).</li>
 * </ul>
 */
public final class C3BootLock {

    private static final Logger LOG = LoggerFactory.getLogger(C3BootLock.class);

    /** Env tat (chi "false" moi tat). */
    public static final String KEY_FLAG = "C3_BOOT_KILLSWITCH";
    /** Tien to token trong file KILL_SWITCH do JVM dat. */
    public static final String TOKEN = "c3live_boot";

    /** Ket qua ap khoa. */
    public enum Outcome { NOT_LIVE, DISABLED, EXISTING, LOCKED, FAILED_MEM_LOCK, ALREADY_DONE }

    private final File killFile;
    private final String flag;
    private final Consumer<String> alert;
    private final AtomicBoolean done = new AtomicBoolean(false);

    /**
     * @param killFile file kill-switch hieu luc
     * @param flag     gia tri env {@code C3_BOOT_KILLSWITCH}
     * @param alert    kenh canh bao (Telegram); null = chi log
     */
    public C3BootLock(File killFile, String flag, Consumer<String> alert) {
        this.killFile = killFile;
        this.flag = flag;
        this.alert = alert == null ? m -> { } : alert;
    }

    /**
     * Thuan: co bat khoa khoi dong khong.
     *
     * @param flag env {@code C3_BOOT_KILLSWITCH}
     * @return false CHI khi flag == "false" (khong phan biet hoa thuong)
     */
    static boolean enabled(String flag) {
        return !(flag != null && "false".equalsIgnoreCase(flag.trim()));
    }

    /**
     * Ap khoa (1 lan / doi tuong).
     *
     * @param live  adapter = LIVE
     * @param nowMs thoi diem (token)
     * @return ket qua
     */
    public Outcome applyOnce(boolean live, long nowMs) {
        if (!live) return Outcome.NOT_LIVE;
        if (!done.compareAndSet(false, true)) return Outcome.ALREADY_DONE;
        if (!enabled(flag)) {
            LOG.warn("[C3-BOOT] {}=false => KHONG khoa khoi dong (B-09 tat)", KEY_FLAG);
            return Outcome.DISABLED;
        }
        if (killFile.exists()) {
            LOG.warn("[C3-BOOT] {} da co luc khoi dong (script/drain) => giu nguyen, khong ghi de", killFile.getPath());
            return Outcome.EXISTING;
        }
        String ts = new SimpleDateFormat("yyyyMMdd_HHmmss").format(new Date(nowMs));
        String token = TOKEN + " " + ts + " B-09: JVM LIVE khoi dong KHONG qua script go-live (crash/watchdog/reboot/restart tay)"
                + " => dung mo moi, vi the c3 van duoc quan ly. Mo: MODE=undrain bash golive_live_off.sh\n";
        try {
            File abs = killFile.getAbsoluteFile();
            try {
                // CREATE_NEW = O_EXCL: KHONG BAO GIO ghi de token cua script dat cung luc (hau kiem script grep token)
                Files.write(abs.toPath(), token.getBytes(StandardCharsets.UTF_8), StandardOpenOption.CREATE_NEW,
                        StandardOpenOption.WRITE);
            } catch (java.nio.file.FileAlreadyExistsException race) {
                LOG.warn("[C3-BOOT] {} vua duoc dat boi tien trinh khac => giu nguyen", killFile.getPath());
                return Outcome.EXISTING;
            }
            if (!abs.exists()) throw new java.io.IOException("khong thay file sau khi ghi");
            String m = "[C3-BOOT] KHOA KHOI DONG: JVM LIVE len KHONG co " + killFile.getPath() + " (khong qua script) => da DAT "
                    + killFile.getPath() + " token " + TOKEN + " " + ts + ": PUSH OFF, KHONG mo lenh moi; vi the c3 van duoc quan ly."
                    + " Owner kiem golive_monitor roi MODE=undrain golive_live_off.sh";
            LOG.warn("{}", m);
            alert.accept(m);
            return Outcome.LOCKED;
        } catch (Exception e) {
            LiveProfileC3.setBootLockMem(true);
            String m = "[C3-BOOT] KHAN: KHONG ghi duoc " + killFile.getPath() + " (" + e.getClass().getSimpleName()
                    + ") => khoa push TRONG RAM toi khi restart (undrain KHONG mo duoc; can sua quyen/dia roi restart qua script)";
            LOG.error("{}", m);
            alert.accept(m);
            return Outcome.FAILED_MEM_LOCK;
        }
    }
}
