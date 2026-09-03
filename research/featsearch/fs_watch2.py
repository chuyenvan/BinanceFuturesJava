"""Doi ca hai luong (Oracle CPU + Kaggle CPU) xong roi chay bootstrap ngay."""
import logging, subprocess, sys, time, os
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
L = logging.getLogger(__name__)
K = "/home/ubuntu/.local/bin/kaggle"
FS = "/home/ubuntu/fs"
oracle_done = kaggle_done = False
for i in range(300):
    if not oracle_done and "ALL_CPU_ARMS_DONE" in open(f"{FS}/RUNCPU.out").read():
        oracle_done = True
        L.info("ORACLE XONG -> bootstrap")
        r = subprocess.run([sys.executable, f"{FS}/fs_boot2.py",
                            f"{FS}/out/fs_ticks_cpu.parquet", "oracle_cpu"],
                           capture_output=True, text=True)
        open(f"{FS}/BOOT_ORACLE.out", "w").write(r.stdout + "\n--ERR--\n" + r.stderr)
        L.info("bootstrap oracle rc=%d", r.returncode)
    if not kaggle_done:
        s = subprocess.run([K, "kernels", "status", "chuyendinh/fs-cand-cpu"],
                           capture_output=True, text=True)
        txt = (s.stdout + s.stderr)
        if "RUNNING" not in txt and "QUEUED" not in txt:
            kaggle_done = True
            L.info("KAGGLE trang thai: %s", txt.strip())
            os.makedirs(f"{FS}/outk", exist_ok=True)
            subprocess.run([K, "kernels", "output", "chuyendinh/fs-cand-cpu",
                            "-p", f"{FS}/outk"], capture_output=True, text=True)
            L.info("outk: %s", os.listdir(f"{FS}/outk"))
            if os.path.exists(f"{FS}/outk/fs_ticks_cpu.parquet"):
                r = subprocess.run([sys.executable, f"{FS}/fs_boot2.py",
                                    f"{FS}/outk/fs_ticks_cpu.parquet", "kaggle_cpu"],
                                   capture_output=True, text=True)
                open(f"{FS}/BOOT_KAGGLE.out", "w").write(r.stdout + "\n--ERR--\n" + r.stderr)
                L.info("bootstrap kaggle rc=%d", r.returncode)
    if oracle_done and kaggle_done:
        break
    time.sleep(120)
L.info("WATCH2_DONE oracle=%s kaggle=%s", oracle_done, kaggle_done)
