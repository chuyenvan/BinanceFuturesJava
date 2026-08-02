#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
================================================================================
COGNITIVE - EXECUTION SEPARATION FRAMEWORK (VERSION 3)
mcp_tools-v3.py — Lop THUC THI job nang (VPS/compute Linux).

Robust Job Controller + Heartbeat Monitor + Kaggle Fleet Manager + Diagnostic
Retry. Ban chat: CDK (Claude Code Desktop) chi "bam nut" (goi 1 lenh cap cao),
Python nay tu lo tron vong doi: start -> giam sat -> report -> retry -> cleanup.

TRIET LY XUAT/NHAP:
  * stdout = KENH TRA VE MAY DOC (machine-readable) cho CDK: MOI lenh in ra
    DUNG MOT khoi JSON qua ham emit(). CDK parse khoi JSON nay de ra quyet dinh.
  * stderr + file log (RUN_DIR/mcp_tools.log) = KENH CHAN DOAN cho nguoi/agent
    doc khi debug. Dung module `logging` (chuan du an: CAM print cho log).
  * KHONG bao gio nuot exception am tham: moi loi deu log.exception(...) va
    emit mot JSON co "status":"error" de CDK biet.

CAC "NUT" (xem bang trong docstring main() + framework md):
  bg_run, bg_status/bg_monitor, bg_report, check_or_restart, bg_stop,
  bg_cleanup, bg_list, manage_jvm, remote_ssh,
  kaggle_slots, kaggle_push, kaggle_status, kaggle_output, kaggle_parse_logs.

Chay syntax-check: python -m py_compile mcp_tools-v3.py
Nen tang muc tieu: Linux (dung /proc, setsid, SIGKILL). Cac loi goi dac thu
Linux deu duoc bao ve bang getattr/try nen file van import/compile tren Windows.
================================================================================
"""

import sys
import os
import time
import subprocess
import json
import signal
import re
import logging
import traceback
import shutil

# ----------------------------------------------------------------------------
# CAU HINH
# ----------------------------------------------------------------------------
RUN_DIR = os.environ.get(
    "CE_RUN_DIR", "/workspace/scratch/cognitive_execution/.run"
)
LOCKS_DIR = os.environ.get(
    "CE_LOCKS_DIR", "/workspace/scratch/cognitive_execution/locks"
)
TOOL_LOG = os.path.join(RUN_DIR, "mcp_tools.log")

# Thu muc chua file pipeline (.json) khai bao kich ban. Doi kich ban = sua FILE,
# khong sua code. State/checkpoint cua moi lan chay pipeline nam trong RUN_DIR.
CE_PIPES_DIR = os.environ.get(
    "CE_PIPES_DIR", "/home/ubuntu/claudedata/.run/pipelines")

# Thu muc chua EXECUTION PROFILE (.json) — "cach chay co dinh theo moi truong x
# cong nghe". Pipeline nghiep vu (L5) chi khai bao "profile":"<ten>" de nap
# san params ha tang (JAR/HOST/XMX/dataset...) da verified, khong lap lai chi
# tiet env trong tung pipeline. Doi profile = sua FILE, khong sua code.
CE_PROFILES_DIR = os.environ.get(
    "CE_PROFILES_DIR", "/home/ubuntu/claudedata/.run/profiles")

# So slot Kaggle toi da (chinh qua env neu chinh sach doi).
KAGGLE_MAX_SLOTS = int(os.environ.get("CE_KAGGLE_MAX_SLOTS", "5"))
# Cach goi kaggle CLI (venv rieng tren VPS). Chay qua bash -c "<bin> <subcmd>".
# Default: source venv roi goi kaggle (thuc dung tu van hanh thuc te).
CE_KAGGLE_BIN = os.environ.get(
    "CE_KAGGLE_BIN",
    "source /home/ubuntu/kaggle_latest_venv/bin/activate && kaggle")
# Dem RAM he thong (GB) cong them vao ram_limit truoc khi cho phep chay.
RAM_SAFETY_BUFFER_GB = float(os.environ.get("CE_RAM_BUFFER_GB", "3.0"))
# Tien trinh LIVE cot loi: TUYET DOI khong duoc kill.
PROTECTED_PROCS = ["BinanceDataIngestor", "BinanceOrderTradingManager",
                   "Aerospike", "Redis"]

# ----------------------------------------------------------------------------
# CAU HINH WFO (Walk-Forward Optimization) — tham so hoa qua env, default hop ly.
# Duc tu script van hanh ~/claudedata/.run/optimize_maxfav3.sh (python tu lam).
# ----------------------------------------------------------------------------
JAVA_BIN = os.environ.get("CE_JAVA_BIN", "java")
WFO_JAR_DEFAULT = os.environ.get(
    "CE_WFO_JAR", "/home/ubuntu/java/simulator/preflight-v42.jar")
WFO_WORKER_CWD = os.environ.get(
    "CE_WFO_WORKER_CWD", "/home/ubuntu/claudedata/.run/oracle_worker_cwd")
WFO_COORD_CLASS = os.environ.get("CE_WFO_COORD_CLASS", "com.binance.chuyennd.ai_ml.wfo.framework.WfoCoordinator")
WFO_WORKER_CLASS = os.environ.get("CE_WFO_WORKER_CLASS", "com.binance.chuyennd.ai_ml.wfo.framework.WfoWorker")
WFO_VERIFY_CLASS = os.environ.get("CE_WFO_VERIFY_CLASS", "com.binance.chuyennd.ai_ml.wfo.VerifyOneWindow")
WFO_COPYTICKER_CLASS = os.environ.get("CE_COPYTICKER_CLASS", "com.binance.chuyennd.aerospike.tools.CopyTicker242To226")
WFO_STRATEGY = os.environ.get("CE_WFO_STRATEGY", "strategy_window")
WFO_REPORT_NAME = os.environ.get("CE_WFO_REPORT_NAME", "wfo_strategy_window.md")
WFO_MAX_OOS_DATE = os.environ.get("CE_WFO_MAX_OOS_DATE", "20260101")
WFO_STATE_HOST = os.environ.get("CE_WFO_STATE_HOST", "103.157.218.226")
WFO_STATE_PORT = os.environ.get("CE_WFO_STATE_PORT", "3222")
WFO_STATE_NS = os.environ.get("CE_WFO_STATE_NS", "ticker")
WFO_WORKER_RAM_GB = float(os.environ.get("CE_WFO_WORKER_RAM_GB", "3.0"))
# Thu muc chua cac kernel dir Kaggle (moi kernel = 1 subdir co kernel-metadata.json).
# Dung cho wfo_fanout push fleet Kaggle. Trung voi profile java-kaggle (KERNELS_DIR).
WFO_KERNELS_DIR = os.environ.get(
    "CE_WFO_KERNELS_DIR", "/home/ubuntu/claudedata/.run/kernels")

# ----------------------------------------------------------------------------
# CAU HINH CHUOI WFO-FROM-PREDS (R1) — 3 nut nguyen tu: pred_convert / wfo_build_ds
# / wfo_verify. Duc tu orchestrator/tools/{ev2_csv_to_predictwf*.py,
# short_csv_to_predictwf.py, _export_oiz75.sh, run_short_wfo_verify.sh}. Tham so
# hoa qua env (default = thuc te van hanh Oracle). KHONG hardcode secret.
# ----------------------------------------------------------------------------
# Python venv XGB tren Oracle (chay converter CSV->predict_wf).
CE_XGB_PY = os.environ.get("CE_XGB_PY", "/home/ubuntu/xgb-env/bin/python")
# Snapshot symbol_map.csv (symId,symbol) DUNG cho SIM — PHAI khop predict_wf cu.
CE_SYMBOL_MAP = os.environ.get(
    "CE_SYMBOL_MAP", "/home/ubuntu/claudedata/feat/symbol_map.csv")
# Thu muc chua 3 converter .py tren Oracle (deploy kem mcp_tools; xem docstring).
CE_PRED_TOOLS_DIR = os.environ.get(
    "CE_PRED_TOOLS_DIR", "/home/ubuntu/claudedata/.run/tools")
# CWD chuan chay java simulator (co kaggle_data_hpo/ ticker file + cac jar).
CE_SIM_CWD = os.environ.get("CE_SIM_CWD", "/home/ubuntu/java/simulator")
# Class + set-pred cho ExportWfoDataset (build dataset offline tu funding pred dir).
WFO_EXPORT_CLASS = os.environ.get(
    "CE_WFO_EXPORT_CLASS",
    "com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset")
WFO_SET_PRED = os.environ.get("CE_WFO_SET_PRED", "ai_pred_market_gate_wfo")
# Heap + RAM guard cho ExportWfoDataset (scan Aerospike 226 -> ~12g).
CE_BUILDDS_XMX = os.environ.get("CE_BUILDDS_XMX", "12g")
CE_BUILDDS_RAM_GB = float(os.environ.get("CE_BUILDDS_RAM_GB", "12.0"))
# Heap + timeout cho VerifyOneWindow (1 window, jobstore-free).
CE_VERIFY_XMX = os.environ.get("CE_VERIFY_XMX", "8g")
CE_VERIFY_TIMEOUT = int(os.environ.get("CE_VERIFY_TIMEOUT", "1800"))
CE_VERIFY_JAR = os.environ.get("CE_VERIFY_JAR", WFO_JAR_DEFAULT)
# Timeout chay converter python (doc CSV lon ~78MB/3M row).
CE_PRED_CONVERT_TIMEOUT = int(os.environ.get("CE_PRED_CONVERT_TIMEOUT", "1800"))
# Optional: ep TICKER_DIR cho verify (default: de trong -> code dung mac dinh
# kaggle_data_hpo relative CWD, dung recipe run_short_wfo_verify.sh da verify).
CE_TICKER_DIR = os.environ.get("CE_TICKER_DIR", "")
# Anh xa mode -> (ten script converter, co nhan tham so quantile khong).
PRED_CONVERT_SCRIPTS = {
    "long": ("ev2_csv_to_predictwf.py", False),
    "oiz": ("ev2_csv_to_predictwf_oiz.py", True),
    "short": ("short_csv_to_predictwf.py", False),
}

os.makedirs(RUN_DIR, exist_ok=True)
os.makedirs(LOCKS_DIR, exist_ok=True)

# ----------------------------------------------------------------------------
# LOGGING (chan doan -> stderr + file). KHONG dung print cho log.
# ----------------------------------------------------------------------------
logger = logging.getLogger("mcp_tools_v3")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    _fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s",
                             "%Y-%m-%d %H:%M:%S")
    _sh = logging.StreamHandler(sys.stderr)
    _sh.setFormatter(_fmt)
    logger.addHandler(_sh)
    try:
        _fh = logging.FileHandler(TOOL_LOG, encoding="utf-8")
        _fh.setFormatter(_fmt)
        logger.addHandler(_fh)
    except Exception:
        # Neu khong ghi duoc file log (vd quyen) van tiep tuc voi stderr.
        logger.warning("Khong mo duoc file log %s, chi log ra stderr.", TOOL_LOG)


def emit(obj):
    """In DUY NHAT mot khoi JSON ra stdout — kenh tra ve may-doc cho CDK.

    Moi handler lenh phai ket thuc bang dung mot lan goi emit(). CDK doc
    khoi JSON nay (khong doc stderr) de ra quyet dinh "bam nut" tiep theo.
    """
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    sys.stdout.flush()


# ============================================================================
# ROBUST JOB CONTROLLER — bo dieu khien 1 job nang, chiu loi cuc doan.
# ============================================================================
class RobustJobController:
    """Boc tron vong doi mot Job nen (Java backtest / Kaggle / HPO sweep).

    Cam ket dau ra (Result Contract): du THANH CONG / THAT BAI / BI GIET,
    controller LUON ghi <job_id>_result.json truoc khi thoat. Nho vay CDK
    khong bao gio bi "cho mu".

    Ba tep trang thai ben vung tai RUN_DIR:
      * <job_id>_state.json  — heartbeat dong, cap nhat moi ~10s.
      * <job_id>_result.json — ket qua cuoi cung (Result Contract).
      * <job_id>.log         — stdout/stderr cua tien trinh con.
    Va 1 lock file tai LOCKS_DIR/<job_id>.lock de chong chay de.
    """

    def __init__(self, job_id, command=None, ram_limit_gb=3.0,
                 heartbeat_timeout_min=30):
        self.job_id = job_id
        self.command = command
        self.ram_limit_gb = ram_limit_gb
        self.heartbeat_timeout_min = heartbeat_timeout_min

        self.state_file = os.path.join(RUN_DIR, f"{job_id}_state.json")
        self.result_file = os.path.join(RUN_DIR, f"{job_id}_result.json")
        self.log_file = os.path.join(RUN_DIR, f"{job_id}.log")
        self.lock_file = os.path.join(LOCKS_DIR, f"{job_id}.lock")

        self.process = None
        self.interrupted = False
        self.stop_reason = ""

    # -- tien ich he thong ---------------------------------------------------
    def get_mem_available_gb(self):
        """Doc RAM kha dung (GB) tu /proc/meminfo. Fallback 4.0 GB neu khong doc duoc."""
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemAvailable" in line:
                        return float(line.split()[1]) / (1024.0 * 1024.0)
        except Exception:
            logger.warning("Khong doc duoc /proc/meminfo, dung fallback 4.0GB.")
        return 4.0

    def check_process_alive(self, pid):
        """True neu PID con song (gui signal 0). An toan voi pid<=0."""
        if not pid or pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _kill_pid_gracefully(self, pid):
        """SIGTERM roi cho toi 5s; con song thi SIGKILL. Chong tien trinh mo coi."""
        if not self.check_process_alive(pid):
            return
        try:
            os.kill(pid, signal.SIGTERM)
            for _ in range(10):
                time.sleep(0.5)
                if not self.check_process_alive(pid):
                    return
            sigkill = getattr(signal, "SIGKILL", signal.SIGTERM)
            os.kill(pid, sigkill)
        except Exception:
            logger.exception("Loi khi cuong che dung PID %s", pid)

    def _force_cleanup_files(self):
        """Xoa lock + state file (giu lai result file lam bang chung cho CDK)."""
        for f in [self.lock_file, self.state_file]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    logger.exception("Khong xoa duoc %s", f)

    # -- I/O trang thai ------------------------------------------------------
    def update_state(self, status, progress="", extra_data=None):
        """Ghi/cap nhat heartbeat file mot cach ben vung (fsync)."""
        state = {
            "job_id": self.job_id,
            "status": status,
            "controller_pid": os.getpid(),
            "child_pid": self.process.pid if self.process else -1,
            "last_heartbeat": time.time(),
            "progress": progress,
            "stop_reason": self.stop_reason,
        }
        if extra_data:
            state.update(extra_data)
        try:
            with open(self.state_file, "w") as f:
                json.dump(state, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            logger.exception("Khong ghi duoc state file %s", self.state_file)

    def _write_result_file(self, result_data):
        """Ghi Result Contract mot cach ben vung (fsync)."""
        try:
            with open(self.result_file, "w") as f:
                json.dump(result_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            logger.exception("Khong ghi duoc result file %s", self.result_file)

    # -- chan doan trang thai lo (stale) ------------------------------------
    def diagnose_and_cleanup(self):
        """Chan doan trang thai cu truoc khi chay / bam lai nut.

        Xu ly 4 kich ban loi (A/B/C/D trong framework md). Neu phat hien
        job mo coi / treo, tu dong cuong che tat + ghi result chan doan +
        don lock, roi cho phep chay lai.

        Returns:
            (can_start: bool, status_message: str)
        """
        logger.info("Bat dau chan doan trang thai cho Job ID: '%s'", self.job_id)

        if not os.path.exists(self.state_file):
            logger.info("Khong co state file cu. Trang thai sach, san sang chay.")
            return True, "Trang thai sach, san sang khoi chay moi."

        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)
        except Exception:
            logger.exception("State file cu hong, don de chay lai.")
            self._force_cleanup_files()
            return True, "State file cu bi loi, da don sach de chay lai."

        status = state.get("status", "UNKNOWN")
        controller_pid = state.get("controller_pid", -1)
        child_pid = state.get("child_pid", -1)
        last_heartbeat = state.get("last_heartbeat", 0)
        elapsed = time.time() - last_heartbeat

        ctrl_alive = self.check_process_alive(controller_pid)
        child_alive = self.check_process_alive(child_pid)
        logger.info("Trang thai cu: status=%s ctrl_alive=%s child_alive=%s "
                    "elapsed=%.1fs", status, ctrl_alive, child_alive, elapsed)

        # (1) Job cu da ket thuc ro rang -> don de chay lai.
        if status in ("SUCCESS", "FAILED", "KILLED") and not ctrl_alive and not child_alive:
            logger.info("Job cu da ket thuc hoan toan. Don de chay lai.")
            self._force_cleanup_files()
            return True, "Job cu da hoan thanh truoc do. San sang chay lai."

        # (2) Stale: qua han heartbeat, hoac controller chet nhung child con song.
        is_stale = elapsed > self.heartbeat_timeout_min * 60
        if is_stale or (not ctrl_alive and child_alive):
            if not ctrl_alive and child_alive:
                diagnosis = ("KICH BAN B: Python Controller CHET nhung tien trinh "
                             "nen (Java/Kaggle) van CHAY MO COI.")
            elif ctrl_alive and not child_alive:
                diagnosis = ("KICH BAN C: Controller con song nhung tien trinh nen "
                             "da CHET, vong lap giam sat bi treo.")
            elif ctrl_alive and child_alive:
                diagnosis = (f"KICH BAN D: Ca hai con song nhung TREO DO "
                             f"(khong heartbeat > {self.heartbeat_timeout_min} phut).")
            else:
                diagnosis = ("KICH BAN A: Khong tien trinh nao con song nhung state "
                             "van RUNNING (nghi sap nguon dot ngot).")
            logger.warning("PHAT HIEN SU CO: %s", diagnosis)

            # Ghi result chan doan TRUOC khi don, de CDK doc duoc nguyen nhan.
            self._write_result_file({
                "status": "FAILED",
                "stop_reason": "STALE_JOB_DETECTED",
                "diagnostic": diagnosis,
                "last_state": state,
                "timestamp": time.time(),
                "action_taken": "Tu dong tat tien trinh mo coi + don tai nguyen de chay lai.",
            })

            if child_alive:
                logger.info("Cuong che dung tien trinh nen mo coi PID %s", child_pid)
                self._kill_pid_gracefully(child_pid)
            if ctrl_alive and controller_pid != os.getpid():
                logger.info("Cuong che dung Controller cu bi treo PID %s", controller_pid)
                self._kill_pid_gracefully(controller_pid)

            self._force_cleanup_files()
            return True, f"Phat hien su co: {diagnosis} Da don sach de chay lai."

        # (3) Job cu van chay tich cuc (heartbeat con tuoi) -> CAM chay de.
        if ctrl_alive or child_alive:
            logger.warning("Job cu van chay tich cuc. KHONG duoc chay de.")
            return False, (f"Job hien tai van dang chay tich cuc (ctrl_pid={controller_pid}, "
                           f"child_pid={child_pid}). Cho hoac gui lenh bg_stop.")

        # (4) Fallback: trang thai khong xac dinh -> don dut diem.
        self._force_cleanup_files()
        return True, "Don dut diem trang thai khong xac dinh, san sang chay lai."

    # -- bat tin hieu & thoat hiem an toan ----------------------------------
    def handle_signal(self, signum, frame):
        """Bay SIGINT/SIGTERM: khong chet ngay, chay quy trinh thoat an toan."""
        sig_name = signal.Signals(signum).name
        logger.warning("Nhan tin hieu %s, kich hoat quy trinh thoat an toan...", sig_name)
        self.interrupted = True
        self.stop_reason = f"Killed by system signal: {sig_name}"
        self.cleanup_and_exit(exit_code=128 + signum)

    def cleanup_and_exit(self, exit_code=0):
        """Thu hoi tien trinh con, ghi Result Contract, giai phong lock roi thoat."""
        # 1. Thu hoi tien trinh con de giai phong tai nguyen.
        if self.process and self.process.poll() is None:
            logger.info("Dang dung tien trinh con (PID %s)...", self.process.pid)
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Tien trinh con cung dau, tien hanh SIGKILL...")
                self.process.kill()
            except Exception:
                logger.exception("Loi khi dung tien trinh con.")

        # 2. Doc 20 dong log cuoi de dinh kem bao cao.
        last_logs = []
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r", errors="ignore") as f:
                    last_logs = f.readlines()[-20:]
            except Exception:
                logger.exception("Khong doc duoc log file %s", self.log_file)

        # 3. Bien soan Result Contract.
        status = "SUCCESS" if exit_code == 0 else ("KILLED" if self.interrupted else "FAILED")
        log_text = "".join(last_logs)
        match = re.search(r"=== RESULT ===\s*(.*?)\s*=== END ===", log_text, re.DOTALL)
        result_extracted = match.group(1).strip() if match else None

        self._write_result_file({
            "status": status,
            "exit_code": exit_code,
            "stop_reason": self.stop_reason or (
                "Completed successfully" if exit_code == 0 else "Execution failed"),
            "timestamp": time.time(),
            "last_known_logs": [line.strip() for line in last_logs],
            "extracted_result": result_extracted,
        })
        self.update_state(status, progress="Job terminated.")

        # 4. Giai phong lock + state.
        self._force_cleanup_files()
        logger.info("Thoat hiem hoan tat. exit_code=%s. Result tai %s",
                    exit_code, self.result_file)
        sys.exit(exit_code)

    # -- vong doi thuc thi (chay blocking, thuong o tien trinh nen detached) -
    def run(self):
        """Chay tron vong doi job (blocking): chan doan -> lock -> RAM-gate ->
        spawn con -> vong lap heartbeat -> ghi Result Contract.

        Ham nay do lenh noi bo `_supervise` goi (chay o tien trinh nen detached
        do bg_run/check_or_restart tao). CDK KHONG goi truc tiep run().
        """
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)

        # 1. Chan doan an toan truoc khi khoi chay.
        can_start, diag_msg = self.diagnose_and_cleanup()
        if not can_start:
            logger.error("Tu choi khoi chay: %s", diag_msg)
            self.update_state("BLOCKED", progress=diag_msg)
            sys.exit(1)

        # 2. Tao lock file (danh dau quyen so huu).
        try:
            with open(self.lock_file, "w") as f:
                f.write(str(os.getpid()))
        except Exception:
            logger.exception("Khong tao duoc lock file %s", self.lock_file)
            sys.exit(1)

        # 3. Kiem tra RAM-budget.
        avail = self.get_mem_available_gb()
        required = self.ram_limit_gb + RAM_SAFETY_BUFFER_GB
        if avail < required:
            self.stop_reason = (f"Can kiet RAM: can {required:.2f}GB (gom "
                                f"{RAM_SAFETY_BUFFER_GB:.0f}GB dem) nhung chi co {avail:.2f}GB")
            logger.error("CHAN HOAT DONG: %s", self.stop_reason)
            self.cleanup_and_exit(exit_code=1)

        # 4. Khoi chay lenh chinh (log ra job_id.log).
        logger.info("Khoi chay lenh con: %s", self.command)
        try:
            log_fh = open(self.log_file, "w")
            self.process = subprocess.Popen(
                self.command, shell=True,
                stdout=log_fh, stderr=subprocess.STDOUT,
                start_new_session=True,  # session group rieng -> khong bi kill theo cha
            )
        except Exception as e:
            self.stop_reason = f"Khoi tao tien trinh con that bai: {e}"
            logger.exception("Khoi tao tien trinh con that bai.")
            self.cleanup_and_exit(exit_code=1)

        # 5. Vong lap giam sat Heartbeat.
        logger.info("Tien trinh con PID %s. Bat dau vong lap giam sat.", self.process.pid)
        last_progress_check = 0
        try:
            while self.process.poll() is None:
                time.sleep(10)  # polling sieu nhe
                progress = "Dang xu ly..."
                now = time.time()
                if now - last_progress_check > 30:
                    last_progress_check = now
                    progress = self._scan_progress() or progress
                self.update_state("RUNNING", progress=progress)

            exit_code = self.process.returncode
            logger.info("Tien trinh con thoat voi ma: %s", exit_code)
            log_fh.close()
            self.cleanup_and_exit(exit_code=exit_code)
        except Exception as e:
            self.stop_reason = f"Ngoai le trong vong lap giam sat: {e}\n{traceback.format_exc()}"
            logger.exception("Ngoai le trong vong lap giam sat.")
            self.cleanup_and_exit(exit_code=1)

    def _scan_progress(self):
        """Quet 5 dong log cuoi tim tu khoa tien do (Active Heartbeat)."""
        keywords = ("Progress", "TICK", "Processed", "Hoan thanh", "DONE", "Queue")
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, "r", errors="ignore") as f:
                    for line in reversed(f.readlines()[-5:]):
                        if any(kw in line for kw in keywords):
                            return line.strip()[:100]
        except Exception:
            logger.exception("Loi quet tien do tu log.")
        return None


# ============================================================================
# TIEN ICH CAP MODULE — dung chung cho cac nut bam.
# ============================================================================
def _paths(job_id):
    """Tra ve (state_file, result_file, log_file, lock_file) cua job_id."""
    return (
        os.path.join(RUN_DIR, f"{job_id}_state.json"),
        os.path.join(RUN_DIR, f"{job_id}_result.json"),
        os.path.join(RUN_DIR, f"{job_id}.log"),
        os.path.join(LOCKS_DIR, f"{job_id}.lock"),
    )


def _read_json(path):
    """Doc file JSON an toan. Tra None neu khong ton tai / hong (co log)."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8-sig", errors="ignore") as f:
            return json.load(f)
    except Exception:
        logger.exception("Khong parse duoc JSON: %s", path)
        return None


def _tail(path, n):
    """Doc n dong cuoi cua file text (rong neu khong ton tai)."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", errors="ignore") as f:
            return [ln.strip() for ln in f.readlines()[-n:]]
    except Exception:
        logger.exception("Khong doc duoc %s", path)
        return []


def _spawn_detached_supervisor(job_id, command, ram_limit):
    """Spawn controller o TIEN TRINH NEN detached, tra ve PID.

    Day la mau chot cua "bam nut tra ve tuc thi": bg_run/check_or_restart goi
    ham nay roi emit ngay, khong block. Controller nen chay lenh noi bo
    `_supervise` (goi RobustJobController.run()), stdout/stderr do vao devnull
    (dien bien di vao mcp_tools.log qua logging + job log).
    """
    devnull = open(os.devnull, "w")
    proc = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "_supervise",
         job_id, command, str(ram_limit)],
        stdout=devnull, stderr=devnull,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    return proc.pid


def _live_job_state(job_id):
    """Neu job dang chay tich cuc (ctrl/child con song), tra ve state dict; nguoc lai None."""
    state_file, _, _, _ = _paths(job_id)
    state = _read_json(state_file)
    if not state:
        return None
    ctrl = RobustJobController(job_id)
    if ctrl.check_process_alive(state.get("controller_pid", -1)) or \
       ctrl.check_process_alive(state.get("child_pid", -1)):
        return state
    return None


# ============================================================================
# NUT BAM (COMMAND HANDLERS) — CDK goi 1 lenh, Python tu lo phan con lai.
# Moi handler nhan `args` (list phan con lai sau ten lenh) va emit() 1 JSON.
# ============================================================================
def cmd_bg_run(args):
    """NUT START (detached). Chan doan nhanh -> spawn controller nen -> tra ve tuc thi.

    Cu phap: bg_run <job_id> "<command>" [ram_limit_gb]
    """
    if len(args) < 2:
        return emit({"status": "error", "summary": "Cu phap: bg_run <job_id> \"<command>\" [ram_gb]"})
    job_id, command = args[0], args[1]
    ram = float(args[2]) if len(args) > 2 else 3.0

    live = _live_job_state(job_id)
    if live:
        return emit({
            "status": "error", "job_id": job_id,
            "state": "ALIVE_DO_NOT_RESTART",
            "summary": "Job dang chay tich cuc, khong chay de. Dung bg_stop truoc neu can.",
            "live_state": live,
        })
    try:
        pid = _spawn_detached_supervisor(job_id, command, ram)
        logger.info("bg_run job=%s -> spawn controller nen PID %s", job_id, pid)
        emit({
            "status": "started", "job_id": job_id, "controller_pid": pid,
            "summary": f"Da khoi chay job '{job_id}' o nen. Dung bg_status de theo doi.",
            "state_file": _paths(job_id)[0], "result_file": _paths(job_id)[1],
        })
    except Exception as e:
        logger.exception("bg_run that bai.")
        emit({"status": "error", "job_id": job_id, "summary": f"Khong khoi chay duoc: {e}"})


def cmd_gate_count(args):
    """NUT GATE-COUNT (count-only). Chay GatePassCountProbe: dem candidate PASS gate
    o cac nguong cung MIN_MOMENTUM_15M, KHONG PnL/order (SIM_GATE_COUNT_ONLY=1).

    Cu phap: gate_count [jar] [data_dir] [ram_gb]
      jar      = /home/ubuntu/java/simulator/gatecount.jar
      data_dir = /home/ubuntu/claudedata/wfo_dataset  -> WFO_DATA_DIR
      ram_gb   = 10
    Boc RobustJobController (bg_run infra), CWD=oracle_worker_cwd (co config.properties),
    log ve RUN_DIR. Thu ket qua: bg_report gate_count.
    """
    jar = args[0] if len(args) > 0 and args[0] else "/home/ubuntu/java/simulator/gatecount.jar"
    data_dir = args[1] if len(args) > 1 and args[1] else "/home/ubuntu/claudedata/wfo_dataset"
    try:
        ram = float(args[2]) if len(args) > 2 and args[2] else 10.0
    except ValueError:
        return emit({"status": "error", "summary": "ram_gb phai la so."})
    job_id = "gate_count"
    live = _live_job_state(job_id)
    if live:
        return emit({"status": "error", "job_id": job_id, "state": "ALIVE_DO_NOT_RESTART",
                     "summary": "Job dang chay tich cuc. bg_stop truoc neu can.", "live_state": live})
    probe_cls = "com.binance.chuyennd.ai_ml.wfo.framework.tasks.GatePassCountProbe"
    cmd = (f"cd {WFO_WORKER_CWD} && SIM_GATE_COUNT_ONLY=1 WFO_DATA_DIR={data_dir} "
           f"{JAVA_BIN} -Xmx9g -cp {jar} {probe_cls}")
    try:
        pid = _spawn_detached_supervisor(job_id, cmd, ram)
        logger.info("gate_count: spawn controller_pid=%s jar=%s", pid, jar)
        emit({"status": "started", "job_id": job_id, "controller_pid": pid,
              "jar": jar, "data_dir": data_dir,
              "summary": "Da khoi chay gate_count o nen. bg_status/bg_report gate_count de theo doi."})
    except Exception as e:
        logger.exception("gate_count that bai.")
        emit({"status": "error", "job_id": job_id, "summary": f"Khong khoi chay duoc: {e}"})


def cmd_hard_sl_sweep(args):
    """NUT HARD-SL SWEEP (full PnL). Chay HardSlSweepProbe: sweep hard stop-loss %
    tren GIA ENTRY DAU TIEN {0,0.20,0.30,0.40}, do PnL/maxDD/calmar/sortino qua nhieu period.

    Cu phap: hard_sl_sweep [jar] [data_dir] [ram_gb]
      jar      = /home/ubuntu/java/simulator/gatecount.jar
      data_dir = /home/ubuntu/claudedata/wfo_dataset  -> WFO_DATA_DIR
      ram_gb   = 10
    Boc RobustJobController (bg_run infra), CWD=oracle_worker_cwd (co config.properties),
    log ve RUN_DIR. Thu ket qua: bg_report hard_sl_sweep.
    """
    jar = args[0] if len(args) > 0 and args[0] else "/home/ubuntu/java/simulator/gatecount.jar"
    data_dir = args[1] if len(args) > 1 and args[1] else "/home/ubuntu/claudedata/wfo_dataset"
    try:
        ram = float(args[2]) if len(args) > 2 and args[2] else 10.0
    except ValueError:
        return emit({"status": "error", "summary": "ram_gb phai la so."})
    job_id = "hard_sl_sweep"
    live = _live_job_state(job_id)
    if live:
        return emit({"status": "error", "job_id": job_id, "state": "ALIVE_DO_NOT_RESTART",
                     "summary": "Job dang chay tich cuc. bg_stop truoc neu can.", "live_state": live})
    probe_cls = "com.binance.chuyennd.ai_ml.wfo.framework.tasks.HardSlSweepProbe"
    cmd = (f"cd {WFO_WORKER_CWD} && WFO_DATA_DIR={data_dir} "
           f"{JAVA_BIN} -Xmx9g -cp {jar} {probe_cls}")
    try:
        pid = _spawn_detached_supervisor(job_id, cmd, ram)
        logger.info("hard_sl_sweep: spawn controller_pid=%s jar=%s", pid, jar)
        emit({"status": "started", "job_id": job_id, "controller_pid": pid,
              "jar": jar, "data_dir": data_dir,
              "summary": "Da khoi chay hard_sl_sweep o nen. bg_status/bg_report hard_sl_sweep de theo doi."})
    except Exception as e:
        logger.exception("hard_sl_sweep that bai.")
        emit({"status": "error", "job_id": job_id, "summary": f"Khong khoi chay duoc: {e}"})


def cmd_invsel_run(args):
    """NUT INVERTED-SELECTOR (standalone backtest, doc Aerospike). Chay
    SimulatorMarketLevelInvertedSelector voi SELECTOR_INVERT=1 (mua Worst-N).

    Cu phap: invsel_run [jar] [sim_end_date] [ram_gb]
      jar          = /home/ubuntu/java/simulator/gatecount.jar
      sim_end_date = 20251231  -> SIM_END_DATE (tranh thieu ticker 2026)
      ram_gb       = 10
    CWD=oracle_worker_cwd (config.properties: TIME_RUN, AEROSPIKE_READ_CLUSTER).
    LUU Y: doc Aerospike runtime, KHONG phai WFO OOS. Thu ket qua: bg_report invsel_run.
    """
    jar = args[0] if len(args) > 0 and args[0] else "/home/ubuntu/java/simulator/gatecount.jar"
    sim_end = args[1] if len(args) > 1 and args[1] else "20251231"
    try:
        ram = float(args[2]) if len(args) > 2 and args[2] else 10.0
    except ValueError:
        return emit({"status": "error", "summary": "ram_gb phai la so."})
    job_id = "invsel_run"
    live = _live_job_state(job_id)
    if live:
        return emit({"status": "error", "job_id": job_id, "state": "ALIVE_DO_NOT_RESTART",
                     "summary": "Job dang chay tich cuc. bg_stop truoc neu can.", "live_state": live})
    cls = "com.binance.chuyennd.research.SimulatorMarketLevelInvertedSelector"
    cmd = (f"cd {WFO_WORKER_CWD} && SELECTOR_INVERT=1 SIM_END_DATE={sim_end} "
           f"{JAVA_BIN} -Xmx9g -cp {jar} {cls}")
    try:
        pid = _spawn_detached_supervisor(job_id, cmd, ram)
        logger.info("invsel_run: spawn controller_pid=%s jar=%s end=%s", pid, jar, sim_end)
        emit({"status": "started", "job_id": job_id, "controller_pid": pid,
              "jar": jar, "sim_end_date": sim_end,
              "summary": "Da khoi chay invsel_run o nen. bg_status/bg_report invsel_run de theo doi."})
    except Exception as e:
        logger.exception("invsel_run that bai.")
        emit({"status": "error", "job_id": job_id, "summary": f"Khong khoi chay duoc: {e}"})


def cmd_supervise(args):
    """NUT NOI BO (khong danh cho CDK). Chay blocking RobustJobController.run().

    Cu phap: _supervise <job_id> "<command>" [ram_limit_gb]
    """
    if len(args) < 2:
        logger.error("_supervise thieu doi so.")
        sys.exit(1)
    job_id, command = args[0], args[1]
    ram = float(args[2]) if len(args) > 2 else 3.0
    RobustJobController(job_id, command, ram).run()


def cmd_bg_status(args):
    """NUT STATUS. Tra ve state realtime + result + tail log (khong ton token log tho).

    Cu phap: bg_status <job_id> [tail_lines]   (bi danh: bg_monitor)
    """
    if not args:
        return emit({"status": "error", "summary": "Cu phap: bg_status <job_id> [tail_lines]"})
    job_id = args[0]
    tail_lines = int(args[1]) if len(args) > 1 else 50
    state_file, result_file, log_file, _ = _paths(job_id)
    emit({
        "status": "success", "job_id": job_id,
        "state": _read_json(state_file),
        "result": _read_json(result_file),
        "log_tail": _tail(log_file, tail_lines),
    })


def cmd_bg_report(args):
    """NUT REPORT. Tra ve Result Contract gon (uu tien result, fallback state).

    Cu phap: bg_report <job_id>
    """
    if not args:
        return emit({"status": "error", "summary": "Cu phap: bg_report <job_id>"})
    job_id = args[0]
    state_file, result_file, log_file, _ = _paths(job_id)
    result = _read_json(result_file)
    state = _read_json(state_file)
    if result is None and state is None:
        return emit({"status": "unknown", "job_id": job_id,
                     "summary": "Chua co du lieu job (chua chay bao gio hoac da cleanup)."})
    emit({
        "status": "success", "job_id": job_id,
        "job_status": (result or {}).get("status") or (state or {}).get("status", "UNKNOWN"),
        "result": result,
        "live_state": state,
        "log_tail": _tail(log_file, 20),
    })


def cmd_check_or_restart(args):
    """NUT RETRY an toan. Chan doan -> don job mo coi/treo -> chay lai (detached).

    Cu phap: check_or_restart <job_id> "<command>" [ram_limit_gb]
    """
    if len(args) < 2:
        return emit({"status": "error",
                     "summary": "Cu phap: check_or_restart <job_id> \"<command>\" [ram_gb]"})
    job_id, command = args[0], args[1]
    ram = float(args[2]) if len(args) > 2 else 3.0

    controller = RobustJobController(job_id, command, ram)
    can_start, diag_msg = controller.diagnose_and_cleanup()
    if not can_start:
        return emit({"status": "error", "job_id": job_id,
                     "state": "ALIVE_DO_NOT_RESTART", "summary": diag_msg})
    try:
        pid = _spawn_detached_supervisor(job_id, command, ram)
        logger.info("check_or_restart job=%s -> chay lai nen PID %s", job_id, pid)
        emit({"status": "restarted", "job_id": job_id, "controller_pid": pid,
              "diagnosis": diag_msg,
              "summary": f"Da chan doan/don dep va chay lai job '{job_id}' o nen."})
    except Exception as e:
        logger.exception("check_or_restart that bai.")
        emit({"status": "error", "job_id": job_id, "summary": f"Khong chay lai duoc: {e}"})


def cmd_bg_stop(args):
    """NUT STOP. Dung an toan controller + tien trinh con cua 1 job, don lock.

    Cu phap: bg_stop <job_id>
    """
    if not args:
        return emit({"status": "error", "summary": "Cu phap: bg_stop <job_id>"})
    job_id = args[0]
    state_file, _, _, _ = _paths(job_id)
    state = _read_json(state_file)
    controller = RobustJobController(job_id)
    killed = []
    if state:
        for key in ("child_pid", "controller_pid"):
            pid = state.get(key, -1)
            if controller.check_process_alive(pid):
                controller._kill_pid_gracefully(pid)
                killed.append({key: pid})
    controller._force_cleanup_files()
    logger.info("bg_stop job=%s killed=%s", job_id, killed)
    emit({"status": "stopped", "job_id": job_id, "killed": killed,
          "summary": f"Da dung job '{job_id}' va don lock/state." if killed
          else f"Job '{job_id}' khong con tien trinh song; da don lock/state."})


def cmd_bg_cleanup(args):
    """NUT CLEANUP. Xoa state/lock (va tuy chon result) cua job da ket thuc.

    Cu phap: bg_cleanup <job_id> [--all]
      --all: xoa ca result file (mac dinh giu result lam bang chung).
    """
    if not args:
        return emit({"status": "error", "summary": "Cu phap: bg_cleanup <job_id> [--all]"})
    job_id = args[0]
    wipe_result = "--all" in args[1:]
    live = _live_job_state(job_id)
    if live:
        return emit({"status": "error", "job_id": job_id,
                     "summary": "Job dang chay, khong cleanup. Dung bg_stop truoc."})
    state_file, result_file, log_file, lock_file = _paths(job_id)
    removed = []
    targets = [lock_file, state_file]
    if wipe_result:
        targets += [result_file, log_file]
    for f in targets:
        if os.path.exists(f):
            try:
                os.remove(f)
                removed.append(os.path.basename(f))
            except Exception:
                logger.exception("Khong xoa duoc %s", f)
    logger.info("bg_cleanup job=%s removed=%s", job_id, removed)
    emit({"status": "success", "job_id": job_id, "removed": removed,
          "summary": f"Da don {len(removed)} tep cua job '{job_id}'."})


def cmd_bg_list(args):
    """NUT LIST. Liet ke moi job da biet (tu state/result file trong RUN_DIR).

    Cu phap: bg_list
    """
    jobs = {}
    for fn in os.listdir(RUN_DIR):
        if fn.endswith("_state.json"):
            jobs.setdefault(fn[:-len("_state.json")], {})["has_state"] = True
        elif fn.endswith("_result.json"):
            jobs.setdefault(fn[:-len("_result.json")], {})["has_result"] = True
    controller_probe = RobustJobController("_probe")
    report = []
    for job_id in sorted(jobs):
        state_file, result_file, _, _ = _paths(job_id)
        state = _read_json(state_file) or {}
        result = _read_json(result_file) or {}
        alive = controller_probe.check_process_alive(state.get("controller_pid", -1)) or \
            controller_probe.check_process_alive(state.get("child_pid", -1))
        report.append({
            "job_id": job_id,
            "alive": alive,
            "state_status": state.get("status"),
            "result_status": result.get("status"),
            "progress": state.get("progress"),
        })
    emit({"status": "success", "summary": f"Tim thay {len(report)} job.", "jobs": report})


def cmd_manage_jvm(args):
    """NUT QUAN LY JVM. list: liet ke tien trinh Java; kill: dung 1 PID (chan proc LIVE).

    Cu phap: manage_jvm list | manage_jvm kill <pid>
    """
    action = args[0] if args else "list"

    if action == "list":
        try:
            p = subprocess.run(["pgrep", "-af", "java"], capture_output=True, text=True)
            jvms = []
            for line in p.stdout.splitlines():
                parts = line.split(" ", 1)
                if len(parts) == 2:
                    jvms.append({"pid": int(parts[0]), "cmd": parts[1]})
            emit({"status": "success",
                  "summary": f"Tim thay {len(jvms)} tien trinh Java.",
                  "data": {"jvms": jvms}})
        except Exception as e:
            logger.exception("Loi liet ke JVM.")
            emit({"status": "error", "summary": f"Loi liet ke JVM: {e}"})

    elif action == "kill":
        if len(args) < 2:
            return emit({"status": "error", "summary": "Cu phap: manage_jvm kill <pid>"})
        try:
            pid = int(args[1])
            with open(f"/proc/{pid}/cmdline", "r") as f:
                cmdline = f.read().replace("\x00", " ")
            if any(p in cmdline for p in PROTECTED_PROCS):
                logger.warning("Chan kill PID %s (LIVE cot loi).", pid)
                return emit({"status": "error",
                             "summary": f"CHAN BAO VE CUNG: PID {pid} ({cmdline[:50]}...) "
                                        "la tien trinh LIVE cot loi. Nghiem cam dung!"})
            os.kill(pid, signal.SIGTERM)
            logger.info("Da SIGTERM PID %s.", pid)
            emit({"status": "success", "summary": f"Da gui SIGTERM den PID {pid}."})
        except Exception as e:
            logger.exception("Khong tat duoc PID.")
            emit({"status": "error", "summary": f"Khong tat duoc PID: {e}"})
    else:
        emit({"status": "error", "summary": f"Hanh dong manage_jvm '{action}' khong hop le."})


def cmd_remote_ssh(args):
    """NUT SSH (co retry). Ket noi khong banner, tu chon port/user theo host.

    Cu phap: remote_ssh <host> "<command>"
    """
    if len(args) < 2:
        return emit({"status": "error", "summary": "Cu phap: remote_ssh <host> \"<command>\""})
    host, ssh_cmd = args[0], args[1]
    port = "2222" if host in ("103.157.218.226", "103.157.218.242") else "22"
    user = "root" if host == "103.157.218.226" else "ubuntu"
    full = (f"ssh -p {port} -o ConnectTimeout=10 -o ConnectionAttempts=3 "
            f"-o StrictHostKeyChecking=no {user}@{host} \"{ssh_cmd}\"")
    try:
        p = subprocess.run(full, shell=True, capture_output=True, text=True)
        ok = p.returncode == 0
        (logger.info if ok else logger.error)("SSH %s rc=%s", host, p.returncode)
        emit({"status": "success" if ok else "error",
              "summary": "Lenh SSH thanh cong." if ok else f"SSH tra ve ma loi: {p.returncode}",
              "stdout": p.stdout.strip(), "stderr": p.stderr.strip()})
    except Exception as e:
        logger.exception("Ket noi SSH that bai.")
        emit({"status": "error", "summary": f"Ket noi SSH that bai: {e}"})


def _kaggle(subcmd, timeout=300):
    """Goi kaggle CLI qua `bash -c "<CE_KAGGLE_BIN> <subcmd>"`. Tra (rc, out, err).

    CE_KAGGLE_BIN mac dinh 'source <venv>/bin/activate && kaggle' — dung venv
    rieng tren VPS. Chay qua bash de source venv duoc trong cung shell.
    """
    return _sh_bash("%s %s" % (CE_KAGGLE_BIN, subcmd), timeout=timeout)


def _kaggle_ref_slug(ref):
    """Bien kernel_ref (vd 'chuyendinh/java-run-lc') thanh slug an toan cho ten thu muc."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "__", str(ref)).strip("_") or "kernel"


def _count_kaggle_slots():
    """Dem slot Kaggle dang dung (running + queued). Tra (used, running, queued) hoac None neu loi."""
    rc, out, err = _kaggle("kernels list --mine")
    if rc != 0:
        logger.error("Loi truy van Kaggle kernels: %s", (err or "").strip())
        return None
    running = queued = 0
    for line in (out or "").strip().splitlines():
        low = line.lower()
        if "running" in low:
            running += 1
        elif "queued" in low:
            queued += 1
    return running + queued, running, queued


def cmd_kaggle_slots(args):
    """NUT KAGGLE SLOTS. Bao cao so slot dang dung / con trong.

    Cu phap: kaggle_slots
    """
    try:
        counts = _count_kaggle_slots()
        if counts is None:
            return emit({"status": "error", "summary": "Loi truy van danh sach Kaggle Kernels."})
        used, running, queued = counts
        available = max(0, KAGGLE_MAX_SLOTS - used)
        emit({"status": "success",
              "summary": f"Kaggle: {running} running, {queued} queued. "
                         f"Slot kha dung: {available}/{KAGGLE_MAX_SLOTS}",
              "data": {"running": running, "queued": queued,
                       "slots_used": used, "slots_available": available,
                       "used": used, "free": available,
                       "cap": KAGGLE_MAX_SLOTS}})
    except Exception as e:
        logger.exception("Loi kiem tra Kaggle slots.")
        emit({"status": "error", "summary": f"Loi kiem tra Kaggle slots: {e}"})


def cmd_kaggle_push(args):
    """NUT KAGGLE PUSH. Gac cong slot roi push kernel len Kaggle.

    Cu phap: kaggle_push <kernel_dir>
    Chay `kaggle kernels push -p <dir>` qua CE_KAGGLE_BIN. Parse chuoi
    "successfully pushed" trong stdout de xac nhan (pushed=true/false) + boc
    kernel_ref neu Kaggle in ra.
    """
    if not args:
        return emit({"status": "error", "summary": "Cu phap: kaggle_push <kernel_dir>"})
    folder = args[0]
    try:
        counts = _count_kaggle_slots()
        used = counts[0] if counts else 0
        if used >= KAGGLE_MAX_SLOTS:
            logger.warning("Chan push: da dat %s slot.", used)
            return emit({"status": "error",
                         "summary": f"CHAN AN TOAN: da dat gioi han {KAGGLE_MAX_SLOTS} slot "
                                    f"({used} dang dung). Khong push them."})
        rc, out, err = _kaggle("kernels push -p %s" % folder)
        out, err = (out or "").strip(), (err or "").strip()
        pushed = "successfully pushed" in out.lower()
        # Kaggle in dong dang: '... url: https://www.kaggle.com/code/<ref>'
        m = re.search(r"kaggle\.com/(?:code/)?([\w-]+/[\w-]+)", out)
        kernel_ref = m.group(1) if m else None
        ok = rc == 0 and pushed
        (logger.info if ok else logger.error)("kaggle_push rc=%s pushed=%s", rc, pushed)
        emit({"status": "success" if ok else "error",
              "pushed": pushed, "kernel_ref": kernel_ref, "rc": rc,
              "summary": ("Da push kernel len Kaggle."
                          + (f" ref={kernel_ref}" if kernel_ref else ""))
              if ok else f"Push kernel that bai (rc={rc}, pushed={pushed}).",
              "stdout": out, "stderr": err})
    except Exception as e:
        logger.exception("Loi push Kaggle.")
        emit({"status": "error", "summary": f"Loi push Kaggle: {e}"})


def cmd_kaggle_status(args):
    """NUT KAGGLE STATUS. Trang thai 1 kernel.

    Cu phap: kaggle_status <kernel_ref>
    Parse output Kaggle (vd '... has status "complete"') -> kernel_state
    chuan hoa: RUNNING | COMPLETE | ERROR | QUEUED | UNKNOWN.
    """
    if not args:
        return emit({"status": "error", "summary": "Cu phap: kaggle_status <kernel_ref>"})
    ref = args[0]
    try:
        rc, out, err = _kaggle("kernels status %s" % ref)
        out, err = (out or "").strip(), (err or "").strip()
        low = out.lower()
        if "running" in low:
            kstate = "RUNNING"
        elif "complete" in low:
            kstate = "COMPLETE"
        elif "error" in low or "fail" in low:
            kstate = "ERROR"
        elif "queue" in low:
            kstate = "QUEUED"
        else:
            kstate = "UNKNOWN"
        ok = rc == 0
        emit({"status": "success" if ok else "error",
              "kernel_ref": ref, "kernel_state": kstate,
              "summary": out if ok else f"Khong lay duoc trang thai {ref} (rc={rc})",
              "stdout": out, "stderr": err})
    except Exception as e:
        logger.exception("Loi Kaggle status.")
        emit({"status": "error", "summary": f"Loi ket noi Kaggle API: {e}"})


def cmd_kaggle_output(args):
    """NUT KAGGLE OUTPUT. Keo output kernel ve va grep loi thuong gap.

    Cu phap: kaggle_output <kernel_ref> [target_dir]
    - Khong co target_dir -> mac dinh CE_RUN_DIR/kaggle_out/<ref-slug>/.
    - Sau khi tai, grep cac pattern loi (Exception, FAIL-FAST, rc=) trong cac
      tep .log/.txt/.json tai ve.
    Tra JSON {log_path, errors_found[], tail}.
    """
    if not args:
        return emit({"status": "error",
                     "summary": "Cu phap: kaggle_output <kernel_ref> [target_dir]"})
    ref = args[0]
    if len(args) >= 2 and args[1]:
        target_dir = args[1]
    else:
        target_dir = os.path.join(RUN_DIR, "kaggle_out", _kaggle_ref_slug(ref))
    os.makedirs(target_dir, exist_ok=True)
    try:
        rc, out, err = _kaggle("kernels output %s -p %s" % (ref, target_dir))
        out, err = (out or "").strip(), (err or "").strip()
        ok = rc == 0
        (logger.info if ok else logger.error)("kaggle_output rc=%s", rc)
        # Grep loi trong cac tep text tai ve.
        patterns = ("Exception", "FAIL-FAST", "rc=")
        errors_found, log_path, last_lines = [], None, []
        try:
            for fn in sorted(os.listdir(target_dir)):
                fp = os.path.join(target_dir, fn)
                if not os.path.isfile(fp):
                    continue
                if not (fn.endswith(".log") or fn.endswith(".txt")
                        or fn.endswith(".json")):
                    continue
                with open(fp, "r", errors="ignore") as f:
                    lines = f.read().splitlines()
                if fn.endswith(".log") or log_path is None:
                    log_path = fp
                for ln in lines:
                    if any(pat in ln for pat in patterns):
                        errors_found.append(ln.strip()[:300])
                last_lines = lines
        except Exception:
            logger.exception("Loi doc tep output Kaggle o %s", target_dir)
        tail = [l.strip() for l in last_lines[-30:]]
        emit({"status": "success" if ok else "error",
              "kernel_ref": ref, "target_dir": target_dir, "rc": rc,
              "log_path": log_path,
              "errors_found": errors_found[:50], "tail": tail,
              "summary": (f"Tai output {ref} ve {target_dir}. "
                          f"errors_found={len(errors_found)}.") if ok
              else f"Loi tai output (rc={rc}).",
              "stdout": out, "stderr": err})
    except Exception as e:
        logger.exception("Loi Kaggle output.")
        emit({"status": "error", "summary": f"Loi ket noi Kaggle API: {e}"})


def cmd_kaggle_parse_logs(args):
    """NUT KAGGLE PARSE LOGS. Giai ma JSON log Kaggle, tra 50 dong cuoi + block RESULT.

    Cu phap: kaggle_parse_logs <log_file_path>
    """
    if not args:
        return emit({"status": "error", "summary": "Cu phap: kaggle_parse_logs <log_file_path>"})
    log_file = args[0]
    if not os.path.exists(log_file):
        return emit({"status": "error", "summary": f"Khong tim thay tep log: {log_file}"})
    try:
        with open(log_file, "r", errors="ignore") as f:
            content = f.read().strip()
        if content.startswith("[") and content.endswith("]"):
            extracted = [str(r.get("data", "")).strip() for r in json.loads(content)]
        else:
            extracted = [ln.strip() for ln in content.splitlines()]
        log_text = "\n".join(extracted[-500:])
        match = re.search(r"=== RESULT ===\s*(.*?)\s*=== END ===", log_text, re.DOTALL)
        emit({"status": "success",
              "summary": f"Giai ma log xong. Tong {len(extracted)} dong, tra 50 dong cuoi.",
              "log_tail": extracted[-50:],
              "extracted_result": match.group(1).strip() if match else None})
    except Exception as e:
        logger.exception("Loi parse logs Kaggle.")
        emit({"status": "error", "summary": f"Loi parse logs: {e}"})


# ============================================================================
# TIEN ICH BO SUNG cho nhom nut bg_selftest / wfo_* / sys_*.
# ============================================================================
def _sh(cmd, timeout=60):
    """Chay 1 lenh shell, tra (rc, stdout, stderr). Khong nem ngoai le ra ngoai."""
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        logger.error("Lenh qua han (%ss): %s", timeout, cmd)
        return 124, (e.stdout or ""), (e.stderr or "") + "\n[TIMEOUT]"
    except Exception as e:
        logger.exception("Loi chay lenh shell: %s", cmd)
        return 1, "", str(e)


def _run_self(button_args, timeout=60):
    """Goi lai chinh script nay nhu mot NUT con (phuc vu bg_selftest).

    Chay THAT SU qua dispatch de tu-test dung duong ma CDK se di.
    Tra (dict_json | None, raw_stdout).
    """
    argv = [sys.executable, os.path.abspath(__file__)] + list(button_args)
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        raw = (p.stdout or "").strip()
        try:
            return json.loads(raw), raw
        except Exception:
            return None, raw
    except Exception as e:
        logger.exception("_run_self loi voi args=%s", button_args)
        return None, str(e)


def cmd_bg_selftest(args):
    """NUT TU-TEST. Chay tron chuoi bg_* bang job sleep don gian de biet he con lanh.

    Cu phap: bg_selftest
    Trinh tu tuan tu: bg_run job 'selftest_<ts>' cmd 'sleep 20 && echo SELFTEST_OK'
    -> poll bg_status toi RUNNING -> bg_report -> bg_stop -> bg_cleanup --all ->
    bg_list (xac nhan sach). Buoc nao loi thi pass=false + detail, VAN chay tiep
    cac buoc con lai (co gang don duoc thi don). Day la nut CDK bam sau moi lan
    sua kich ban de biet he thong con lanh.
    Emit: {status, job_id, steps:[{step,pass,detail}...], overall: PASS|FAIL}.
    """
    job_id = "selftest_%d" % int(time.time())
    cmd = "sleep 20 && echo SELFTEST_OK"
    # Job selftest chi la sleep, khong can 3GB mac dinh -> ram_gb=0.2 de guard RAM
    # khong chan tren VPS RAM thap.
    ram_gb = "0.2"
    steps = []

    def _step(name, ok, detail):
        steps.append({"step": name, "pass": bool(ok), "detail": str(detail)[:300]})

    # 1) bg_run (ram_gb=0.2: job sleep khong can RAM, tranh guard chan tren VPS)
    r, raw = _run_self(["bg_run", job_id, cmd, ram_gb])
    started = bool(r and r.get("status") == "started")
    _step("bg_run", started, (r or {}).get("summary", raw))

    # 2) poll bg_status toi RUNNING (toi da ~50s, noi nhe cho VPS spawn cham)
    running = False
    detail = "Khong dat trang thai RUNNING trong thoi gian cho."
    if started:
        deadline = time.time() + 50
        while time.time() < deadline:
            time.sleep(2)
            rs, _ = _run_self(["bg_status", job_id, "5"])
            st = (rs or {}).get("state") or {}
            cur = st.get("status")
            if cur == "RUNNING":
                running = True
                detail = "state.status=RUNNING child_pid=%s" % st.get("child_pid")
                break
            if cur in ("FAILED", "KILLED", "BLOCKED"):
                detail = "state.status=%s (khong len duoc RUNNING)" % cur
                break
    _step("bg_status_running", running, detail)

    # 3) bg_report
    rr, raw = _run_self(["bg_report", job_id])
    rep_ok = bool(rr and rr.get("status") == "success")
    _step("bg_report", rep_ok,
          ("job_status=%s" % (rr or {}).get("job_status")) if rep_ok else raw)

    # 4) bg_stop
    rstop, raw = _run_self(["bg_stop", job_id])
    stop_ok = bool(rstop and rstop.get("status") == "stopped")
    _step("bg_stop", stop_ok, (rstop or {}).get("summary", raw))

    # Cho controller kip ghi result KILLED + don state truoc khi cleanup (tranh race).
    time.sleep(2)

    # 5) bg_cleanup --all
    rc, raw = _run_self(["bg_cleanup", job_id, "--all"])
    clean_ok = bool(rc and rc.get("status") == "success")
    _step("bg_cleanup", clean_ok, (rc or {}).get("summary", raw))

    # 6) bg_list xac nhan sach (job da bien mat)
    rl, raw = _run_self(["bg_list"])
    remaining = [j for j in (rl or {}).get("jobs", []) if j.get("job_id") == job_id]
    list_ok = bool(rl and rl.get("status") == "success" and not remaining)
    _step("bg_list_clean", list_ok,
          "Job da bien mat khoi danh sach." if list_ok
          else ("Van con dau vet job: %s" % remaining))

    overall = "PASS" if all(s["pass"] for s in steps) else "FAIL"
    passed = sum(1 for s in steps if s["pass"])
    logger.info("bg_selftest job=%s overall=%s (%d/%d)", job_id, overall,
                passed, len(steps))
    emit({"status": "success", "job_id": job_id, "steps": steps,
          "overall": overall,
          "summary": "Tu-test chuoi bg_*: %s (%d/%d buoc dat)."
          % (overall, passed, len(steps))})


# ---- Nhom WFO -------------------------------------------------------------
def _wfo_coord_cmd(subcmd, jar=None, extra_env=""):
    """Dung chuoi shell chay WfoCoordinator tai WFO_WORKER_CWD.

    subcmd vd: "reset strategy_window" / "status strategy_window" / "report".
    """
    jar = jar or WFO_JAR_DEFAULT
    # FIX 2026-07-17: LUON gan env WFO_STATE_* (truoc day thieu -> WfoJobStore roi ve config CWD
    # ns=test -> doc NHAM jobstore -> pipeline wait khong bao gio thoa). extra_env de sau de override duoc.
    state_env = (f"WFO_STATE_HOST={WFO_STATE_HOST} WFO_STATE_PORT={WFO_STATE_PORT} "
                 f"WFO_STATE_NS={WFO_STATE_NS} WFO_MAX_OOS_DATE={WFO_MAX_OOS_DATE}")
    env = state_env + ((" " + extra_env) if extra_env else "")
    # passthrough WFO_HARNESS_FIX (AUDIT P0/P1) tu env python vao JVM coordinator/worker
    if os.environ.get("WFO_HARNESS_FIX") and "WFO_HARNESS_FIX" not in env:
        env = env + " WFO_HARNESS_FIX=" + os.environ["WFO_HARNESS_FIX"]
    return (f"cd {WFO_WORKER_CWD} && {env} {JAVA_BIN} -cp {jar} "
            f"{WFO_COORD_CLASS} {subcmd}")


def _autosnap_prev_report(new_tag, jar=None):
    """GUARD (2026-08-02) chong mat verdict: truoc khi reset coordinator cho fanout
    moi, snapshot report cua run TRUOC (state hien tai) neu con window DONE. Ly do:
    fanout dung CHUNG job-group `strategy_window` + 1 index tren jobstore 226, reset
    ghi de -> run truoc chua kip luu report se mat aggregate (vd confirm_n30 bi dcaoff
    reset de). Non-fatal: moi loi chi log, KHONG chan fanout."""
    try:
        # dung `report <group>` (khong phai `report` tran) de recompute LIVE tu jobstore
        # + passthrough WFO_HARNESS_FIX -> ra ban P1 lenient dung, khong phai md cache cu.
        _sh(_wfo_coord_cmd(f"report {WFO_STRATEGY}", jar=jar), timeout=180)
        src = os.path.join(WFO_WORKER_CWD, "docs", "reports", WFO_REPORT_NAME)
        if not os.path.exists(src):
            logger.info("autosnap: khong co report md truoc (state rong) -> bo qua")
            return None
        with open(src, "r", errors="ignore") as f:
            md = f.read()
        m = re.search(r"DONE:\s*(\d+)", md)
        done = int(m.group(1)) if m else 0
        if done <= 0:
            logger.info("autosnap: state khong co window DONE -> khong snapshot")
            return None
        ts = time.strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(RUN_DIR, f"wfo_report_autosnap_{ts}.md")
        shutil.copyfile(src, dst)
        logger.warning("autosnap: SAP reset de %d window DONE cua run truoc -> da luu "
                       "snapshot %s (tag moi=%s)", done, dst, new_tag)
        return dst
    except Exception:
        logger.exception("autosnap: loi (bo qua, khong chan fanout)")
        return None


def cmd_wfo_run(args):
    """NUT WFO RUN. Kill worker cu -> reset coordinator -> spawn N WfoWorker nen.

    Cu phap: wfo_run <ds> [jar] [n] [seed] [workers] [tag]
      ds        : path dataset _ff (BAT BUOC) -> WFO_DATA_DIR
      jar       : jar simulator (default preflight-v42.jar)
      n=30      : so mau -> WFO_N_SAMPLES
      seed=42   : WFO_SEED_BASE
      workers=2 : so tien trinh WfoWorker spawn nen
      tag=opt   : nhan job (job_id = wfo_<tag>_w<i>)
    Hanh vi: kill WfoWorker cu -> `WfoCoordinator reset strategy_window`
    (env WFO_N_SAMPLES) -> spawn <workers> java WfoWorker DETACHED (env
    WFO_N_SAMPLES/WFO_DATA_DIR/WFO_SMART_CACHE=1/WFO_SEED_BASE/WFO_MAX_OOS_DATE/
    WFO_STATE_HOST/PORT/NS) CWD=oracle_worker_cwd, log ve RUN_DIR, moi con giao
    1 RobustJobController (bg_run infra) giam sat. KHONG block cho xong.
    """
    if not args:
        return emit({"status": "error",
                     "summary": "Cu phap: wfo_run <ds> [jar] [n] [seed] [workers] [tag]"})
    ds = args[0]
    jar = args[1] if len(args) > 1 and args[1] else WFO_JAR_DEFAULT
    n = args[2] if len(args) > 2 else "30"
    seed = args[3] if len(args) > 3 else "42"
    try:
        workers = int(args[4]) if len(args) > 4 else 2
    except ValueError:
        return emit({"status": "error", "summary": "workers phai la so nguyen."})
    tag = args[5] if len(args) > 5 else "opt"

    # 1) Kill WfoWorker cu (tranh 2 the he cung ghi state store).
    krc, _, _ = _sh(f"pkill -f {WFO_WORKER_CLASS}")
    logger.info("wfo_run: pkill %s rc=%s", WFO_WORKER_CLASS, krc)

    # 2) Reset coordinator (dong bo, nhanh). WFO_N_SAMPLES quyet dinh so cua so.
    reset_cmd = _wfo_coord_cmd(f"reset {WFO_STRATEGY}", jar=jar,
                               extra_env=f"WFO_N_SAMPLES={n}")
    rrc, rout, rerr = _sh(reset_cmd, timeout=120)
    if rrc != 0:
        logger.error("wfo_run: reset coordinator that bai rc=%s", rrc)
        return emit({"status": "error", "phase": "reset", "rc": rrc,
                     "summary": "Reset WfoCoordinator that bai.",
                     "stdout": rout.strip()[-2000:], "stderr": rerr.strip()[-2000:]})

    # 3) Spawn <workers> WfoWorker nen, moi con boc trong 1 RobustJobController.
    env_prefix = (
        f"WFO_N_SAMPLES={n} WFO_DATA_DIR={ds} WFO_SMART_CACHE=1 "
        f"WFO_SEED_BASE={seed} WFO_MAX_OOS_DATE={WFO_MAX_OOS_DATE} "
        f"WFO_STATE_HOST={WFO_STATE_HOST} WFO_STATE_PORT={WFO_STATE_PORT} "
        f"WFO_STATE_NS={WFO_STATE_NS}"
    )
    spawned, errors = [], []
    for i in range(workers):
        job_id = f"wfo_{tag}_w{i}"
        live = _live_job_state(job_id)
        if live:
            errors.append({"job_id": job_id, "reason": "ALIVE_DO_NOT_RESTART"})
            continue
        worker_cmd = (f"cd {WFO_WORKER_CWD} && {env_prefix} {JAVA_BIN} -cp {jar} "
                      f"{WFO_WORKER_CLASS} {WFO_STRATEGY}")
        try:
            pid = _spawn_detached_supervisor(job_id, worker_cmd, WFO_WORKER_RAM_GB)
            spawned.append({"job_id": job_id, "controller_pid": pid})
            logger.info("wfo_run: spawn worker %s controller_pid=%s", job_id, pid)
        except Exception as e:
            logger.exception("wfo_run: spawn worker %s that bai", job_id)
            errors.append({"job_id": job_id, "reason": str(e)})

    emit({"status": "started" if spawned else "error",
          "tag": tag, "dataset": ds, "jar": jar,
          "n_samples": n, "seed_base": seed, "workers_requested": workers,
          "reset_ok": True, "spawned": spawned, "errors": errors,
          "summary": (f"Reset xong, da spawn {len(spawned)}/{workers} WfoWorker nen. "
                      f"Dung wfo_status/bg_status de theo doi.")
          if spawned else "Khong spawn duoc worker nao (xem 'errors')."})


def _parse_extra_env(spec):
    """Chuan hoa extra_env -> dict[str,str]. Chap nhan:
      - dict (khi goi noi bo)
      - JSON object string:  '{"ABLATION_MODE":"C"}'
      - Python-dict-repr:    "{'ABLATION_MODE': 'C'}" (khi pipeline dict bi str())
      - dang K=V phan tach boi ',' hoac khoang trang: 'ABLATION_MODE=C,WFO_DISABLE_DCA=1'
    Tra {} neu rong/khong parse duoc (khong nem loi).
    """
    if not spec:
        return {}
    if isinstance(spec, dict):
        return {str(k): str(v) for k, v in spec.items()}
    s = str(spec).strip()
    if not s or s in ("{}", "None"):
        return {}
    if s.startswith("{"):
        try:
            d = json.loads(s)
            if isinstance(d, dict):
                return {str(k): str(v) for k, v in d.items()}
        except Exception:
            pass
        try:
            import ast
            d = ast.literal_eval(s)
            if isinstance(d, dict):
                return {str(k): str(v) for k, v in d.items()}
        except Exception:
            logger.warning("extra_env khong parse duoc: %s", s[:200])
            return {}
    out = {}
    for tok in re.split(r"[,\s]+", s):
        if "=" in tok:
            k, v = tok.split("=", 1)
            if k.strip():
                out[k.strip()] = v.strip()
    return out


def _kaggle_kernel_dirs(root, prefix=None):
    """Liet ke cac kernel dir push duoc duoi `root`.

    - Neu root co san kernel-metadata.json -> [root] (1 kernel).
    - Nguoc lai: moi subdir co kernel-metadata.json la 1 kernel (sap xep ten).
    - `prefix` (mac dinh env CE_WFO_KERNEL_PREFIX, fallback "wfo-worker"): CHI lay
      subdir ten bat dau bang prefix nay. Ly do: `.run/kernels/` con chua kernel
      KHONG lien quan (vd `test226`) dung cho viec khac, dung sort() alphabet se
      dua no len truoc `wfo-worker-1` -> wfo_fanout push NHAM kernel khi
      kaggle_kernels < so_kernel_dir (da an TASK exit003 2026-07-30). Truyen
      prefix="" de tat filter (lay tat ca, hanh vi cu).
    """
    if not os.path.isdir(root):
        return []
    if os.path.exists(os.path.join(root, "kernel-metadata.json")):
        return [root]
    if prefix is None:
        prefix = os.environ.get("CE_WFO_KERNEL_PREFIX", "wfo-worker")
    dirs = []
    for name in sorted(os.listdir(root)):
        if prefix and not name.startswith(prefix):
            continue
        sub = os.path.join(root, name)
        if os.path.isdir(sub) and os.path.exists(
                os.path.join(sub, "kernel-metadata.json")):
            dirs.append(sub)
    return dirs


def cmd_wfo_fanout(args):
    """NUT WFO FANOUT — MAC DINH cho WFO full-16-window (6 node).

    Cu phap: wfo_fanout <ds> [jar] [n] [seed] [oracle_workers] [kaggle_kernels]
                        [tag] [extra_env]
      ds             : path dataset _ff (BAT BUOC) -> WFO_DATA_DIR (Oracle worker)
      jar            : jar simulator Oracle (default preflight-v42.jar)
      n=30           : so mau -> WFO_N_SAMPLES
      seed=42        : WFO_SEED_BASE
      oracle_workers=2 : so WfoWorker spawn nen tren Oracle
      kaggle_kernels=5 : so kernel Kaggle MUON push (bi cap boi free-slot + so kernel dir)
      tag=opt        : nhan job (Oracle job_id = wfo_<tag>_w<i>)
      extra_env      : env bo sung cho WORKER Oracle (vd 'ABLATION_MODE=C,WFO_DISABLE_DCA=1'
                       hoac JSON). LUU Y: chi ap cho Oracle worker; Kaggle kernel dung env
                       baked trong notebook/dataset (xem docstring + ce-buttons.md).

    Hanh vi: nhu wfo_run (kill worker cu -> reset coordinator -> spawn Oracle worker
    detached) NHUNG THEM: kiem slot Kaggle, push toi da min(free_slot, kaggle_kernels,
    so_kernel_dir) kernel tu WFO_KERNELS_DIR (cung jobstore 226). KHONG block.
    Ca 2 tang cung an vao WfoJobStore 226 (ns=ticker) -> tu can tai qua CAS claim.
    """
    if not args:
        return emit({"status": "error",
                     "summary": "Cu phap: wfo_fanout <ds> [jar] [n] [seed] "
                                "[oracle_workers] [kaggle_kernels] [tag] [extra_env]"})
    ds = args[0]
    jar = args[1] if len(args) > 1 and args[1] else WFO_JAR_DEFAULT
    n = args[2] if len(args) > 2 and args[2] else "30"
    seed = args[3] if len(args) > 3 and args[3] else "42"
    try:
        oracle_workers = int(args[4]) if len(args) > 4 and args[4] else 2
    except ValueError:
        return emit({"status": "error", "summary": "oracle_workers phai la so nguyen."})
    try:
        kaggle_kernels = int(args[5]) if len(args) > 5 and args[5] else 5
    except ValueError:
        return emit({"status": "error", "summary": "kaggle_kernels phai la so nguyen."})
    tag = args[6] if len(args) > 6 and args[6] else "opt"
    extra_env = _parse_extra_env(args[7]) if len(args) > 7 else {}

    # 0) GUARD (2026-08-02): snapshot report cua run TRUOC truoc khi reset -> tranh mat
    #    verdict khi fanout moi de len state cu (jobstore serial, chung group).
    _autosnap_prev_report(tag, jar=jar)

    # 1) Kill WfoWorker cu (tranh 2 the he cung ghi state store).
    krc, _, _ = _sh(f"pkill -f {WFO_WORKER_CLASS}")
    logger.info("wfo_fanout: pkill %s rc=%s", WFO_WORKER_CLASS, krc)

    # 2) Reset coordinator (dong bo). WFO_N_SAMPLES quyet dinh so cua so.
    reset_cmd = _wfo_coord_cmd(f"reset {WFO_STRATEGY}", jar=jar,
                               extra_env=f"WFO_N_SAMPLES={n}")
    rrc, rout, rerr = _sh(reset_cmd, timeout=120)
    if rrc != 0:
        logger.error("wfo_fanout: reset coordinator that bai rc=%s", rrc)
        return emit({"status": "error", "phase": "reset", "rc": rrc,
                     "summary": "Reset WfoCoordinator that bai.",
                     "stdout": rout.strip()[-2000:], "stderr": rerr.strip()[-2000:]})

    # 3) Spawn Oracle worker nen (co the kem extra_env).
    extra_prefix = " ".join(f"{k}={v}" for k, v in extra_env.items())
    env_prefix = (
        f"WFO_N_SAMPLES={n} WFO_DATA_DIR={ds} WFO_SMART_CACHE=1 "
        f"WFO_SEED_BASE={seed} WFO_MAX_OOS_DATE={WFO_MAX_OOS_DATE} "
        f"WFO_STATE_HOST={WFO_STATE_HOST} WFO_STATE_PORT={WFO_STATE_PORT} "
        f"WFO_STATE_NS={WFO_STATE_NS}"
    )
    if extra_prefix:
        env_prefix = f"{extra_prefix} {env_prefix}"
    spawned, errors = [], []
    for i in range(oracle_workers):
        job_id = f"wfo_{tag}_w{i}"
        live = _live_job_state(job_id)
        if live:
            errors.append({"job_id": job_id, "reason": "ALIVE_DO_NOT_RESTART"})
            continue
        worker_cmd = (f"cd {WFO_WORKER_CWD} && {env_prefix} {JAVA_BIN} -cp {jar} "
                      f"{WFO_WORKER_CLASS} {WFO_STRATEGY}")
        try:
            pid = _spawn_detached_supervisor(job_id, worker_cmd, WFO_WORKER_RAM_GB)
            spawned.append({"job_id": job_id, "controller_pid": pid})
            logger.info("wfo_fanout: spawn Oracle worker %s pid=%s", job_id, pid)
        except Exception as e:
            logger.exception("wfo_fanout: spawn Oracle worker %s that bai", job_id)
            errors.append({"job_id": job_id, "reason": str(e)})

    # 4) Push fleet Kaggle: kiem slot -> push min(free, kaggle_kernels, #kernel_dir).
    kaggle = {"requested": kaggle_kernels, "pushed": [], "skipped": [],
              "kernels_dir": WFO_KERNELS_DIR}
    if kaggle_kernels > 0:
        counts = _count_kaggle_slots()
        if counts is None:
            kaggle["error"] = "Khong truy van duoc Kaggle slots (bo qua push Kaggle)."
            logger.error("wfo_fanout: %s", kaggle["error"])
        else:
            used = counts[0]
            free = max(0, KAGGLE_MAX_SLOTS - used)
            kaggle["slots_used"], kaggle["slots_free"] = used, free
            kdirs = _kaggle_kernel_dirs(WFO_KERNELS_DIR)
            kaggle["kernel_dirs_found"] = len(kdirs)
            n_push = min(kaggle_kernels, free, len(kdirs))
            if extra_env:
                kaggle["note_extra_env"] = (
                    "extra_env KHONG ap cho Kaggle kernel (env baked trong notebook); "
                    "muon dong bo -> bump kernel dataset.")
            for d in kdirs[:n_push]:
                rc, out, err = _kaggle("kernels push -p %s" % d)
                out = (out or "").strip()
                pushed = rc == 0 and "successfully pushed" in out.lower()
                m = re.search(r"kaggle\.com/(?:code/)?([\w-]+/[\w-]+)", out)
                kref = m.group(1) if m else None
                (kaggle["pushed"] if pushed else kaggle["skipped"]).append(
                    {"dir": d, "rc": rc, "pushed": pushed, "kernel_ref": kref})
                logger.info("wfo_fanout: kaggle push %s rc=%s pushed=%s", d, rc, pushed)
            for d in kdirs[n_push:kaggle_kernels]:
                kaggle["skipped"].append({"dir": d, "reason": "no_free_slot"})

    n_oracle = len(spawned)
    n_kaggle = len(kaggle["pushed"])
    total_nodes = n_oracle + n_kaggle
    emit({"status": "started" if total_nodes else "error",
          "tag": tag, "dataset": ds, "jar": jar,
          "n_samples": n, "seed_base": seed,
          "oracle_workers_requested": oracle_workers,
          "kaggle_kernels_requested": kaggle_kernels,
          "extra_env": extra_env,
          "reset_ok": True, "oracle_spawned": spawned, "oracle_errors": errors,
          "kaggle": kaggle, "nodes": total_nodes,
          "summary": (f"FANOUT khoi chay: {n_oracle} Oracle worker + {n_kaggle} Kaggle kernel "
                      f"= {total_nodes} node (cung jobstore 226). Dung wfo_status theo doi.")
          if total_nodes else "Khong khoi chay duoc node nao (xem oracle_errors/kaggle)."})


def cmd_wfo_status(args):
    """NUT WFO STATUS. Chay WfoCoordinator status, parse tong hop + cua so FAILED.

    Cu phap: wfo_status
    Parse total/PENDING/RUNNING/DONE/FAILED + liet ke per-window FAILED + err.
    """
    cmd = _wfo_coord_cmd(f"status {WFO_STRATEGY}")
    rc, out, err = _sh(cmd, timeout=120)
    if rc != 0:
        logger.error("wfo_status rc=%s", rc)
        return emit({"status": "error", "rc": rc,
                     "summary": "WfoCoordinator status that bai.",
                     "stdout": out.strip()[-2000:], "stderr": err.strip()[-2000:]})
    counts = {}
    for kw in ("total", "PENDING", "RUNNING", "DONE", "FAILED"):
        m = re.search(r"%s\s*[:=]\s*(\d+)" % kw, out, re.IGNORECASE)
        if m:
            counts[kw] = int(m.group(1))
        elif kw == "total":
            counts[kw] = None
        else:
            # Fallback: dem so dong chua token trang thai.
            counts[kw] = sum(1 for ln in out.splitlines()
                             if re.search(r"\b%s\b" % kw, ln))
    failed_windows = [ln.strip()[:200] for ln in out.splitlines()
                      if re.search(r"\bFAILED\b", ln)]
    emit({"status": "success", "strategy": WFO_STRATEGY,
          "counts": counts, "failed_windows": failed_windows,
          "summary": ("WFO status: total=%s PENDING=%s RUNNING=%s DONE=%s FAILED=%s"
                      % (counts.get("total"), counts.get("PENDING"),
                         counts.get("RUNNING"), counts.get("DONE"),
                         counts.get("FAILED"))),
          "raw_tail": out.strip().splitlines()[-30:]})


def cmd_wfo_report(args):
    """NUT WFO REPORT. Chay WfoCoordinator report, cp report md ve RUN_DIR, parse chi so.

    Cu phap: wfo_report [tag]
    Cp CWD/docs/reports/wfo_strategy_window.md -> RUN_DIR/wfo_report_<tag>.md.
    Parse: VERDICT / %OOS / WFE / maxDD + note-breakdown
    (dem SUCCESS / TOO_FEW_TRADES / ZERO_TRADES / TOO_MUCH_CAPITAL_LOCK).
    """
    tag = args[0] if args else "opt"
    cmd = _wfo_coord_cmd("report")
    rc, out, err = _sh(cmd, timeout=180)
    if rc != 0:
        logger.error("wfo_report rc=%s", rc)
        return emit({"status": "error", "rc": rc,
                     "summary": "WfoCoordinator report that bai.",
                     "stdout": out.strip()[-2000:], "stderr": err.strip()[-2000:]})
    src = os.path.join(WFO_WORKER_CWD, "docs", "reports", WFO_REPORT_NAME)
    dst = os.path.join(RUN_DIR, f"wfo_report_{tag}.md")
    copied, md = False, ""
    if os.path.exists(src):
        try:
            shutil.copyfile(src, dst)
            copied = True
            with open(dst, "r", errors="ignore") as f:
                md = f.read()
        except Exception:
            logger.exception("wfo_report: khong cp/doc duoc report md %s", src)
    else:
        logger.warning("wfo_report: khong tim thay report md %s", src)

    def _find(pat):
        m = re.search(pat, md, re.IGNORECASE)
        return m.group(1).strip() if m else None

    metrics = {
        "VERDICT": _find(r"VERDICT\s*[:=]?\s*([A-Za-z_\-]+)"),
        "OOS_pct": _find(r"%?\s*OOS[^\d\-]*([-\d.]+)\s*%"),
        "WFE": _find(r"WFE\s*[:=]?\s*([-\d.]+)\s*%?"),
        "maxDD": _find(r"max\s*DD[^\d\-]*([-\d.]+)\s*%?"),
    }
    note_breakdown = {note: len(re.findall(r"\b%s\b" % note, md))
                      for note in ("SUCCESS", "TOO_FEW_TRADES",
                                   "ZERO_TRADES", "TOO_MUCH_CAPITAL_LOCK")}
    emit({"status": "success", "tag": tag,
          "report_copied": copied, "report_path": dst if copied else None,
          "report_src": src, "metrics": metrics, "note_breakdown": note_breakdown,
          "summary": ("WFO report tag=%s VERDICT=%s OOS=%s WFE=%s maxDD=%s"
                      % (tag, metrics["VERDICT"], metrics["OOS_pct"],
                         metrics["WFE"], metrics["maxDD"]))})


def cmd_wfo_stop(args):
    """NUT WFO STOP. pkill WfoWorker (va VerifyOneWindow), bao so proc bi kill.

    Cu phap: wfo_stop
    """
    killed = {}
    for pat in (WFO_WORKER_CLASS, WFO_VERIFY_CLASS):
        _, cout, _ = _sh(f"pgrep -fc {pat}")
        try:
            before = int((cout or "0").strip() or "0")
        except ValueError:
            before = 0
        _sh(f"pkill -f {pat}")
        killed[pat] = before
    total = sum(killed.values())
    logger.info("wfo_stop killed=%s", killed)
    emit({"status": "success", "killed": killed, "total_killed": total,
          "summary": f"Da pkill {total} tien trinh WFO ({killed})."})


# ---- Nhom WFO-FROM-PREDS (R1: chuoi CSV preds -> predict_wf -> dataset -> verify) ----
def _read_manifest_funding(out_ds):
    """Doc fundingCount tu <out_ds>/manifest.txt. Tra (int|None, manifest_path)."""
    manifest = os.path.join(out_ds, "manifest.txt")
    if not os.path.exists(manifest):
        return None, manifest
    try:
        with open(manifest, "r", errors="ignore") as f:
            for line in f:
                m = re.match(r"\s*fundingCount\s*=\s*(\d+)", line)
                if m:
                    return int(m.group(1)), manifest
    except Exception:
        logger.exception("Khong doc duoc manifest %s", manifest)
    return None, manifest


def cmd_pred_convert(args):
    """NUT PRED_CONVERT. CSV preds -> predict_wf_<win>.bin (chay converter python venv XGB).

    Cu phap: pred_convert <csv_path> <out_dir> <mode> [param]
      mode=long  : ev2_csv_to_predictwf.py — cam p6 vao ca 4 horizon slot.
      mode=oiz   : ev2_csv_to_predictwf_oiz.py — loc entry oi_z<=quantile[param]
                   (param=OIZ_Q, default 0.75; P6_MIN co dinh 0.7).
      mode=short : short_csv_to_predictwf.py — doc cot ps, score=1-ps (dao trong Java).
    Chay `{CE_XGB_PY} <script> <csv> <CE_SYMBOL_MAP> <out_dir> [params]` tren Oracle,
    parse dong "XONG: N rec, W window, S symId". Tra {rows, symIds, windows, out_dir}.
    Converter .py phai co san o CE_PRED_TOOLS_DIR (deploy kem mcp_tools).
    """
    if len(args) < 3:
        return emit({"status": "error",
                     "summary": "Cu phap: pred_convert <csv_path> <out_dir> <mode> [param]"})
    csv_path, out_dir, mode = args[0], args[1], args[2]
    param = args[3] if len(args) > 3 and args[3] else None
    mode = mode.lower()
    if mode not in PRED_CONVERT_SCRIPTS:
        return emit({"status": "error", "mode": mode,
                     "summary": "mode phai la long | oiz | short."})
    script_name, takes_q = PRED_CONVERT_SCRIPTS[mode]
    script = os.path.join(CE_PRED_TOOLS_DIR, script_name)
    if not os.path.exists(script):
        return emit({"status": "error", "mode": mode, "script": script,
                     "summary": f"Khong tim thay converter {script}. "
                                f"Deploy cac .py trong orchestrator/tools/ len "
                                f"CE_PRED_TOOLS_DIR ({CE_PRED_TOOLS_DIR})."})
    if not os.path.exists(csv_path):
        return emit({"status": "error", "csv_path": csv_path,
                     "summary": f"Khong tim thay CSV preds: {csv_path}"})
    if not os.path.exists(CE_SYMBOL_MAP):
        return emit({"status": "error", "symbol_map": CE_SYMBOL_MAP,
                     "summary": f"Khong tim thay symbol_map: {CE_SYMBOL_MAP}"})
    tail = ""
    if takes_q and param:
        # oiz converter nhan [P6_MIN] [OIZ_Q]; giu P6_MIN=0.7 chuan, ep OIZ_Q=param.
        tail = " 0.7 %s" % param
    cmd = "%s %s %s %s %s%s" % (CE_XGB_PY, script, csv_path, CE_SYMBOL_MAP,
                                out_dir, tail)
    logger.info("pred_convert mode=%s cmd=%s", mode, cmd)
    rc, out, err = _sh(cmd, timeout=CE_PRED_CONVERT_TIMEOUT)
    out, err = (out or "").strip(), (err or "").strip()
    m = re.search(r"XONG:\s*(\d+)\s*rec,\s*(\d+)\s*window,\s*(\d+)\s*symId", out)
    rows = int(m.group(1)) if m else None
    windows = int(m.group(2)) if m else None
    sym_ids = int(m.group(3)) if m else None
    ok = rc == 0 and m is not None
    (logger.info if ok else logger.error)("pred_convert rc=%s rows=%s", rc, rows)
    emit({"status": "success" if ok else "error", "mode": mode,
          "csv_path": csv_path, "out_dir": out_dir, "param": param,
          "rows": rows, "windows": windows, "symIds": sym_ids, "rc": rc,
          "summary": (f"pred_convert[{mode}]: {rows} rec, {windows} window, "
                      f"{sym_ids} symId -> {out_dir}") if ok
          else f"pred_convert[{mode}] that bai (rc={rc}). Xem stdout/stderr.",
          "stdout_tail": out.splitlines()[-15:],
          "stderr_tail": err.splitlines()[-15:]})


def cmd_wfo_build_ds(args):
    """NUT WFO_BUILD_DS. Chay ExportWfoDataset -> dataset offline tu funding pred dir.

    Cu phap: wfo_build_ds <predict_wf_dir> <out_ds> [jar]
      predict_wf_dir : thu muc predict_wf_<win>.bin -> WFO_FUNDING_PRED_DIR.
      out_ds         : thu muc dataset dich (arg cua ExportWfoDataset).
      jar            : jar simulator (default preflight-v42.jar).
    Env: WFO_SET_PRED=ai_pred_market_gate_wfo WFO_FUNDING_PRED_DIR=<dir>
         WFO_SEL_HORIZON_IDX=0, cwd=CE_SIM_CWD, -Xmx12g. Scan Aerospike 226 nen
         CHAY DETACHED (bg infra: RobustJobController) -> tra job handle tuc thi.
    Neu <out_ds>/manifest.txt DA co (job truoc xong) va khong con job song ->
    tra thang {fundingCount} tu manifest (status=done, idempotent).
    """
    if len(args) < 2:
        return emit({"status": "error",
                     "summary": "Cu phap: wfo_build_ds <predict_wf_dir> <out_ds> [jar]"})
    pred_dir, out_ds = args[0], args[1]
    jar = args[2] if len(args) > 2 and args[2] else WFO_JAR_DEFAULT
    job_id = "buildds_" + re.sub(r"[^A-Za-z0-9_.-]+", "_", os.path.basename(
        out_ds.rstrip("/")) or "ds")

    # Idempotent: dataset da build xong (manifest co) va khong con job song -> tra luon.
    live = _live_job_state(job_id)
    if not live:
        funding, manifest = _read_manifest_funding(out_ds)
        if funding is not None:
            return emit({"status": "done", "job_id": job_id, "out_ds": out_ds,
                         "manifest": manifest, "fundingCount": funding,
                         "summary": f"Dataset da san: {out_ds} (fundingCount={funding})."})
    if live:
        return emit({"status": "error", "job_id": job_id,
                     "state": "ALIVE_DO_NOT_RESTART", "live_state": live,
                     "summary": "Job build_ds dang chay. Dung bg_status theo doi."})

    cmd = (f"cd {CE_SIM_CWD} && WFO_SET_PRED={WFO_SET_PRED} "
           f"WFO_FUNDING_PRED_DIR={pred_dir} WFO_SEL_HORIZON_IDX=0 "
           f"{JAVA_BIN} -Xmx{CE_BUILDDS_XMX} -cp {jar} {WFO_EXPORT_CLASS} {out_ds}")
    logger.info("wfo_build_ds job=%s cmd=%s", job_id, cmd)
    try:
        pid = _spawn_detached_supervisor(job_id, cmd, CE_BUILDDS_RAM_GB)
        _, _, manifest = (None, None, os.path.join(out_ds, "manifest.txt"))
        emit({"status": "started", "job_id": job_id, "controller_pid": pid,
              "out_ds": out_ds, "pred_dir": pred_dir, "jar": jar,
              "manifest": manifest,
              "summary": (f"Da khoi chay ExportWfoDataset '{job_id}' o nen. Theo doi "
                          f"bg_status {job_id}; xong -> goi lai wfo_build_ds de lay fundingCount."),
              "state_file": _paths(job_id)[0], "result_file": _paths(job_id)[1]})
    except Exception as e:
        logger.exception("wfo_build_ds spawn that bai.")
        emit({"status": "error", "job_id": job_id,
              "summary": f"Khong khoi chay duoc ExportWfoDataset: {e}"})


def cmd_wfo_verify(args):
    """NUT WFO_VERIFY. Chay VerifyOneWindow 1 cua so (jobstore-free) -> RESULT_JSON.

    Cu phap: wfo_verify <ds> <winIdx> [extra_env]
      ds       : WfoDataset offline -> WFO_DATA_DIR.
      winIdx   : chi so window (arg cua VerifyOneWindow).
      extra_env: env bo sung (K=V,... hoac JSON). 2 key DAC BIET duoc boc ra
                 khoi env va ap vao lenh java: WFO_JAR=<jar> (default preflight-v42.jar),
                 WFO_XMX=<heap> (default 8g). Vi du short-verify:
                 'WFO_JAR=/home/ubuntu/java/simulator/preflight-v42-short.jar,ENABLE_SHORT=1,WFO_DISABLE_DCA=1'.
    Env co dinh: TICKER_SOURCE=file (+ TICKER_DIR neu CE_TICKER_DIR set), cwd=CE_SIM_CWD.
    KHONG dung coordinator/jobstore (khong reset). Chay DONG BO, parse dong
    'RESULT_JSON {...}' -> {oosPnl, wfe, oosTrades, oosNote}.
    """
    if len(args) < 2:
        return emit({"status": "error",
                     "summary": "Cu phap: wfo_verify <ds> <winIdx> [extra_env]"})
    ds, win_idx = args[0], args[1]
    extra = _parse_extra_env(args[2]) if len(args) > 2 else {}
    # Boc 2 key dac biet ra khoi env (ap vao lenh java, khong phai env).
    jar = extra.pop("WFO_JAR", None) or CE_VERIFY_JAR
    xmx = extra.pop("WFO_XMX", None) or CE_VERIFY_XMX
    env_parts = ["WFO_DATA_DIR=%s" % ds, "TICKER_SOURCE=file"]
    if CE_TICKER_DIR:
        env_parts.append("TICKER_DIR=%s" % CE_TICKER_DIR)
    for k, v in extra.items():
        env_parts.append("%s=%s" % (k, v))
    env_str = " ".join(env_parts)
    cmd = (f"cd {CE_SIM_CWD} && {env_str} {JAVA_BIN} -Xmx{xmx} -cp {jar} "
           f"{WFO_VERIFY_CLASS} {win_idx}")
    logger.info("wfo_verify ds=%s win=%s cmd=%s", ds, win_idx, cmd)
    rc, out, err = _sh(cmd, timeout=CE_VERIFY_TIMEOUT)
    out, err = (out or "").strip(), (err or "").strip()
    # RESULT_JSON co the o stdout hoac stderr (log slf4j -> stderr).
    blob = out + "\n" + err
    m = re.search(r"RESULT_JSON\s+(\{.*\})", blob)
    result_json, parsed = None, {}
    if m:
        result_json = m.group(1)
        try:
            parsed = json.loads(result_json)
        except Exception:
            logger.exception("wfo_verify: khong parse duoc RESULT_JSON")
    ok = rc == 0 and bool(m)
    metrics = {k: parsed.get(k) for k in ("oosPnl", "wfe", "oosTrades", "oosNote")}
    (logger.info if ok else logger.error)("wfo_verify rc=%s win=%s ok=%s", rc, win_idx, ok)
    emit({"status": "success" if ok else "error",
          "ds": ds, "winIdx": win_idx, "jar": jar, "extra_env": extra, "rc": rc,
          "result_json": result_json, "metrics": metrics,
          "summary": (f"wfo_verify w{win_idx}: oosPnl={metrics['oosPnl']} "
                      f"wfe={metrics['wfe']} oosTrades={metrics['oosTrades']} "
                      f"oosNote={metrics['oosNote']}") if ok
          else f"wfo_verify w{win_idx} that bai (rc={rc}, RESULT_JSON={'co' if m else 'khong'}).",
          "stdout_tail": out.splitlines()[-15:],
          "stderr_tail": err.splitlines()[-15:]})


# ---- Nhom SYS -------------------------------------------------------------
def _short_main(cmdline):
    """Rut gon main class / jar tu dong lenh java (best-effort)."""
    toks = cmdline.split()
    for i, t in enumerate(toks):
        if t == "-jar" and i + 1 < len(toks):
            return os.path.basename(toks[i + 1])
    skip_next = False
    for t in toks:
        if skip_next:
            skip_next = False
            continue
        if t in ("-cp", "-classpath", "--class-path"):
            skip_next = True
            continue
        if t.startswith("-") or t.endswith("java"):
            continue
        if re.match(r"^[\w.$]+$", t) and not t.endswith(".jar"):
            return t.split(".")[-1]
    return cmdline[:60]


def _java_procs():
    """Liet ke tien trinh java: [{pid, etime, main}] (main = class/jar rut gon)."""
    procs = []
    rc, out, _ = _sh("ps -eo pid=,etime=,args=")
    if rc != 0:
        return procs
    for ln in out.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        parts = ln.split(None, 2)
        if len(parts) < 3:
            continue
        pid, etime, cmdline = parts
        if "java" not in cmdline:
            continue
        procs.append({"pid": pid, "etime": etime, "main": _short_main(cmdline)})
    return procs


def cmd_sys_health(args):
    """NUT SYS HEALTH. disk(df /), RAM(free/meminfo), load, danh sach java proc -> JSON.

    Cu phap: sys_health
    """
    disk = {}
    rc, out, _ = _sh("df -P /")
    if rc == 0:
        lines = out.strip().splitlines()
        if len(lines) >= 2:
            f = lines[1].split()
            if len(f) >= 6:
                disk = {"filesystem": f[0], "size": f[1], "used": f[2],
                        "avail": f[3], "use_pct": f[4], "mount": f[5]}
    ram = {}
    try:
        mi = {}
        with open("/proc/meminfo", "r") as fh:
            for line in fh:
                kv = line.split(":")
                if len(kv) == 2:
                    mi[kv[0].strip()] = kv[1].strip()

        def _gb(key):
            v = mi.get(key, "0").split()
            try:
                return round(float(v[0]) / (1024.0 * 1024.0), 2)
            except Exception:
                return None
        ram = {"total_gb": _gb("MemTotal"), "available_gb": _gb("MemAvailable"),
               "free_gb": _gb("MemFree")}
    except Exception:
        logger.exception("sys_health: khong doc duoc /proc/meminfo.")
    load = None
    try:
        load = list(os.getloadavg())
    except Exception:
        rc2, lo, _ = _sh("cat /proc/loadavg")
        if rc2 == 0:
            load = lo.split()[:3]
    jvms = _java_procs()
    emit({"status": "success", "disk": disk, "ram": ram, "load": load,
          "java_procs": jvms,
          "summary": ("Disk /=%s dung (con %s); RAM avail=%s/%sGB; load=%s; "
                      "java_procs=%d"
                      % (disk.get("use_pct"), disk.get("avail"),
                         ram.get("available_gb"), ram.get("total_gb"),
                         load, len(jvms)))})


def cmd_sys_zombies(args):
    """NUT SYS ZOMBIES. Liet ke WfoWorker/VerifyOneWindow/CopyTicker dang chay.

    Cu phap: sys_zombies [kill=true]
      kill=true -> kill cac tien trinh tim thay va bao so luong.
    """
    patterns = [WFO_WORKER_CLASS, WFO_VERIFY_CLASS, WFO_COPYTICKER_CLASS]
    do_kill = any(a in ("kill=true", "--kill", "kill", "true") for a in args)
    report = {}
    for pat in patterns:
        _, out, _ = _sh(f"pgrep -af {pat}")
        found = []
        for ln in out.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            p = ln.split(" ", 1)
            found.append({"pid": int(p[0]) if p[0].isdigit() else p[0],
                          "cmd": (p[1] if len(p) > 1 else "")[:160]})
        entry = {"count": len(found), "procs": found}
        if do_kill and found:
            krc, _, _ = _sh(f"pkill -f {pat}")
            entry["killed"] = True
            entry["kill_rc"] = krc
            logger.info("sys_zombies: pkill %s rc=%s (%d proc)", pat, krc, len(found))
        report[pat] = entry
    total = sum(v["count"] for v in report.values())
    emit({"status": "success", "kill_requested": do_kill,
          "report": report, "total_found": total,
          "summary": ("Tim thay %d tien trinh zombie tiem nang%s."
                      % (total, " — da kill" if do_kill else ""))})


def cmd_sys_logtail(args):
    """NUT SYS LOGTAIL. Tra n dong cuoi cua 1 tep trong RUN_DIR (chan path-traversal).

    Cu phap: sys_logtail <file> [n]
      file: ten tep trong RUN_DIR. Tu choi neu chua '..' hoac la duong dan tuyet
            doi / thoat ra ngoai RUN_DIR.
    """
    if not args:
        return emit({"status": "error", "summary": "Cu phap: sys_logtail <file> [n]"})
    fname = args[0]
    try:
        n = int(args[1]) if len(args) > 1 else 50
    except ValueError:
        return emit({"status": "error", "summary": "n phai la so nguyen."})
    # Chan path-traversal (den truoc: cu phap ten tep).
    if (not fname) or (".." in fname) or fname.startswith("/") \
       or fname.startswith("\\") or os.path.isabs(fname):
        logger.warning("sys_logtail: chan ten tep bat hop le '%s'", fname)
        return emit({"status": "error",
                     "summary": "Ten tep khong hop le (chan path-traversal)."})
    run_real = os.path.realpath(RUN_DIR)
    full = os.path.realpath(os.path.join(run_real, fname))
    # Chan chot chan: sau khi resolve phai van nam trong RUN_DIR.
    try:
        inside = os.path.commonpath([full, run_real]) == run_real
    except ValueError:
        inside = False
    if not inside:
        logger.warning("sys_logtail: chan tep ngoai RUN_DIR '%s'", fname)
        return emit({"status": "error",
                     "summary": "Tep nam ngoai RUN_DIR (chan path-traversal)."})
    if not os.path.exists(full):
        return emit({"status": "error", "summary": f"Khong tim thay tep: {fname}"})
    lines = _tail(full, n)
    emit({"status": "success", "file": fname, "path": full, "n": n,
          "lines": lines,
          "summary": f"Doc {len(lines)} dong cuoi cua {fname}."})


# ============================================================================
# PIPELINE ENGINE (declarative) — MAY LAM HET, LLM CHI GAC O DIEM CAN TU DUY.
# ----------------------------------------------------------------------------
# Triet ly: viec CHAN TAY (chay lenh, cho, poll, retry, so file) may tu lam
# TRON CHUOI. LLM CHI duoc goi o buoc `llm_gate` (dung-va-cho). Doi kich ban =
# sua FILE pipeline .json, KHONG sua code.
#
# Schema pipeline (.json): {"name","params":{...},"steps":[{step},...]}
# Moi step:
#   id       : ten buoc (bat buoc, dinh danh trong state)
#   type     : tool | shell | wait | llm_gate
#   on_fail  : abort (mac dinh) | continue
#   retry    : so lan thu lai (mac dinh 0, delay 30s)
#   type=tool : tool=<ten nut>, args={named}|[positional]
#   type=shell: cmd="<bash -c>"
#   type=wait : tool, args, interval_sec, timeout_sec, until={path,equals
#               [,and_path,and_equals]} hoac until={conditions:[{path,op:value}]}
#   type=llm_gate: question, context_files=[...]
# ${param}: thay trong moi chuoi tu params (merge override CLI K=V) truoc khi chay.
# State/checkpoint: RUN_DIR/pipe_<id>_state.json ghi SAU MOI step.
#   status: RUNNING | WAITING_LLM | DONE | FAILED | STOPPED
# llm_gate: runner ghi RUN_DIR/pipe_<id>_NEED_LLM.json {question,context_files,
#   step_id}, set WAITING_LLM, exit sach. Co RUN_DIR/pipe_<id>_LLM_ANSWER.json
#   {answer:"..."} thi pipe_resume tieu thu answer va di tiep. KHONG tu goi LLM.
# ============================================================================
_STEP_TYPES = ("tool", "shell", "wait", "llm_gate")

# Anh xa dict named-args -> list positional cho tung nut (kem default).
# default=None nghia la BAT BUOC. Nut ngoai bang chi nhan args dang list.
TOOL_ARG_ORDER = {
    "wfo_run": [("ds", None), ("jar", ""), ("n", "30"), ("seed", "42"),
                ("workers", "2"), ("tag", "opt")],
    "wfo_fanout": [("ds", None), ("jar", ""), ("n", "30"), ("seed", "42"),
                   ("oracle_workers", "2"), ("kaggle_kernels", "5"),
                   ("tag", "opt"), ("extra_env", "")],
    "wfo_status": [],
    "wfo_report": [("tag", "opt")],
    "wfo_stop": [],
    "pred_convert": [("csv_path", None), ("out_dir", None), ("mode", None),
                     ("param", "")],
    "wfo_build_ds": [("predict_wf_dir", None), ("out_ds", None), ("jar", "")],
    "wfo_verify": [("ds", None), ("winIdx", None), ("extra_env", "")],
    "bg_run": [("job_id", None), ("cmd", None), ("ram", "3.0")],
    "gate_count": [("jar", ""), ("data_dir", ""), ("ram", "10")],
    "hard_sl_sweep": [("jar", ""), ("data_dir", ""), ("ram", "10")],
    "invsel_run": [("jar", ""), ("sim_end_date", ""), ("ram", "10")],
    "bg_status": [("job_id", None), ("tail", "50")],
    "bg_report": [("job_id", None)],
    "bg_stop": [("job_id", None)],
    "bg_list": [],
    "sys_health": [],
    "sys_zombies": [("kill", "")],
    "kaggle_slots": [],
    "kaggle_push": [("dir", None)],
    "kaggle_status": [("ref", None)],
    "kaggle_output": [("ref", None), ("dir", "")],
    "profile_list": [],
}


def _pipe_paths(pipe_id):
    """Tra ve (state_file, need_llm_file, llm_answer_file) cho 1 pipeline run."""
    return (
        os.path.join(RUN_DIR, f"pipe_{pipe_id}_state.json"),
        os.path.join(RUN_DIR, f"pipe_{pipe_id}_NEED_LLM.json"),
        os.path.join(RUN_DIR, f"pipe_{pipe_id}_LLM_ANSWER.json"),
    )


def _write_json(path, obj):
    """Ghi JSON nguyen tu (tmp + rename) — checkpoint an toan khi crash."""
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
        return True
    except Exception:
        logger.exception("Khong ghi duoc JSON: %s", path)
        return False


def _subst(obj, params):
    """Thay ${key} bang params[key] trong moi chuoi (de quy qua dict/list)."""
    if isinstance(obj, str):
        out = obj
        for k, v in params.items():
            out = out.replace("${%s}" % k, str(v))
        return out
    if isinstance(obj, dict):
        return {k: _subst(v, params) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_subst(v, params) for v in obj]
    return obj


def _dot_get(obj, path):
    """Lay gia tri theo dot-path 'a.b.c' (ho tro index list). None neu thieu."""
    cur = obj
    for part in str(path).split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return cur


def _cmp(actual, op, expected):
    """So sanh mem: uu tien so hoc neu ep duoc ve float, nguoc lai so chuoi."""
    fa = fe = None
    try:
        fa, fe = float(actual), float(expected)
    except (TypeError, ValueError):
        pass
    if fa is not None and fe is not None:
        a, e = fa, fe
    else:
        a, e = actual, expected
    if op == "equals":
        return a == e
    if op == "gt":
        return a is not None and a > e
    if op == "lt":
        return a is not None and a < e
    if op == "gte":
        return a is not None and a >= e
    if op == "lte":
        return a is not None and a <= e
    return False


def _until_conditions(until):
    """Chuan hoa khoi `until` ve list dieu kien [{path,op,value}] (AND)."""
    conds = []
    if not isinstance(until, dict):
        return conds
    if isinstance(until.get("conditions"), list):
        for c in until["conditions"]:
            for op in ("equals", "gt", "lt", "gte", "lte"):
                if op in c:
                    conds.append({"path": c.get("path"), "op": op, "value": c[op]})
                    break
        return conds
    # Dang gon: path/equals (+ and_path/and_equals nhu vi du).
    if "path" in until:
        conds.append({"path": until["path"], "op": "equals",
                      "value": until.get("equals")})
    if "and_path" in until:
        conds.append({"path": until["and_path"], "op": "equals",
                      "value": until.get("and_equals")})
    return conds


def _eval_until(until, result):
    """Tra (ok, chi_tiet). ok=True neu MOI dieu kien until dung tren result."""
    conds = _until_conditions(until)
    if not conds:
        return False, "until rong/khong hop le"
    details, ok_all = [], True
    for c in conds:
        actual = _dot_get(result, c["path"])
        ok = _cmp(actual, c["op"], c["value"])
        ok_all = ok_all and ok
        details.append("%s(%s)%s%s->%s" % (c["path"], actual, c["op"],
                                           c["value"], "OK" if ok else "x"))
    return ok_all, "; ".join(details)


def _call_tool_capture(tool, arg_list):
    """Goi NOI BO 1 nut cung process, bat khoi JSON emit() -> (dict|None, raw).

    Khong subprocess de quy: chi tam doi sys.stdout de bat JSON tra ra.
    """
    handler = COMMANDS.get(tool)
    if handler is None:
        return {"status": "error", "summary": f"tool '{tool}' khong ton tai"}, ""
    import io
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        handler(list(arg_list))
    except SystemExit:
        pass
    except Exception as e:
        sys.stdout = old
        logger.exception("pipeline: loi goi tool %s", tool)
        return {"status": "error", "summary": f"exception: {e}"}, ""
    finally:
        sys.stdout = old
    raw = buf.getvalue().strip()
    try:
        return json.loads(raw), raw
    except Exception:
        return None, raw


def _tool_args_list(tool, args):
    """Chuan hoa args (dict named | list positional) -> list str positional."""
    if args is None:
        return []
    if isinstance(args, list):
        return [str(a) for a in args]
    if isinstance(args, dict):
        order = TOOL_ARG_ORDER.get(tool)
        if order is None:
            return [str(v) for v in args.values()]  # best-effort
        out = []
        for key, default in order:
            if key in args:
                out.append(str(args[key]))
            elif default is None:
                raise ValueError(f"tool '{tool}' thieu tham so bat buoc '{key}'")
            else:
                out.append(str(default))
        while out and out[-1] == "":  # bo duoi default rong -> nut tu ap default
            out.pop()
        return out
    return [str(args)]


def _sh_bash(cmd, timeout=600):
    """Chay `bash -c cmd` (ho tro process substitution). Tra (rc, out, err)."""
    try:
        p = subprocess.run(["bash", "-c", cmd], capture_output=True,
                           text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as e:
        logger.error("shell qua han (%ss): %s", timeout, cmd)
        return 124, (e.stdout or ""), (e.stderr or "") + "\n[TIMEOUT]"
    except Exception as e:
        logger.exception("Loi chay bash: %s", cmd)
        return 1, "", str(e)


def _validate_pipeline(pipe):
    """Kiem tra schema pipeline. Tra list loi (rong = hop le)."""
    errs = []
    if not isinstance(pipe, dict):
        return ["pipeline khong phai JSON object"]
    if not pipe.get("name"):
        errs.append("thieu 'name'")
    steps = pipe.get("steps")
    if not isinstance(steps, list) or not steps:
        errs.append("'steps' phai la list khong rong")
        return errs
    seen = set()
    for i, s in enumerate(steps):
        if not isinstance(s, dict):
            errs.append(f"step[{i}] khong phai object")
            continue
        sid = s.get("id")
        if not sid:
            errs.append(f"step[{i}] thieu 'id'")
        elif sid in seen:
            errs.append(f"step id trung: '{sid}'")
        else:
            seen.add(sid)
        st = s.get("type")
        if st not in _STEP_TYPES:
            errs.append(f"step '{sid}' type '{st}' khong hop le {_STEP_TYPES}")
            continue
        if st == "tool" and not s.get("tool"):
            errs.append(f"step '{sid}' (tool) thieu 'tool'")
        if st == "shell" and not s.get("cmd"):
            errs.append(f"step '{sid}' (shell) thieu 'cmd'")
        if st == "wait":
            if not s.get("tool"):
                errs.append(f"step '{sid}' (wait) thieu 'tool'")
            if not s.get("until"):
                errs.append(f"step '{sid}' (wait) thieu 'until'")
        if st == "llm_gate" and not s.get("question"):
            errs.append(f"step '{sid}' (llm_gate) thieu 'question'")
        if s.get("on_fail", "abort") not in ("abort", "continue"):
            errs.append(f"step '{sid}' on_fail phai la abort|continue")
    return errs


def _resolve_pipe_file(arg):
    """Tim file pipeline: path truc tiep -> CE_PIPES_DIR -> them .json. Tra abspath|None."""
    if os.path.exists(arg):
        return os.path.abspath(arg)
    cand = os.path.join(CE_PIPES_DIR, arg)
    if os.path.exists(cand):
        return os.path.abspath(cand)
    if not arg.endswith(".json"):
        return _resolve_pipe_file(arg + ".json")
    return None


# ----------------------------------------------------------------------------
# EXECUTION PROFILE — tang L4: "cach chay co dinh theo moi truong x cong nghe".
# Profile file schema: {"name","description","verified":"YYYY-MM-DD"|null,
#   "params":{...}}. Pipeline L5 khai bao "profile":"<ten>" (hoac list) de nap
# san params ha tang. Thu tu uu tien khi merge: CLI override > pipeline params
# > profile params (profile la NEN, nghiep vu de len tren, CLI cao nhat).
# ----------------------------------------------------------------------------
def _resolve_profile_file(name):
    """Tim file profile: path truc tiep -> CE_PROFILES_DIR -> them .json. Tra abspath|None."""
    if os.path.exists(name):
        return os.path.abspath(name)
    cand = os.path.join(CE_PROFILES_DIR, name)
    if os.path.exists(cand):
        return os.path.abspath(cand)
    if not str(name).endswith(".json"):
        return _resolve_profile_file(name + ".json")
    return None


def _load_profile(name):
    """Nap 1 profile theo ten. Tra (dict|None, error_str|None).

    Thieu file -> loi ro rang (nem ten + CE_PROFILES_DIR). Thieu 'params' ->
    loi schema. Khong nuot loi am tham.
    """
    pf = _resolve_profile_file(name)
    if not pf:
        return None, ("Khong tim thay profile '%s' (da thu ./%s va %s)"
                      % (name, name, CE_PROFILES_DIR))
    data = _read_json(pf)
    if data is None:
        return None, f"Khong parse duoc profile JSON: {pf}"
    if not isinstance(data.get("params"), dict):
        return None, f"Profile '{name}' thieu 'params' (phai la object)"
    return data, None


def _resolve_params(pipe, kv_args):
    """Gop params cho 1 lan chay pipeline theo thu tu uu tien.

    Thu tu (thap -> cao): profile params < pipeline params < CLI K=V.
    Tra (params_dict, profiles_used[], errors[]). profiles_used moi phan tu:
    {name, verified, description}. errors rong = OK.
    """
    params, profiles_used, errors = {}, [], []
    prof_field = pipe.get("profile")
    if isinstance(prof_field, str):
        names = [prof_field]
    elif isinstance(prof_field, list):
        names = [str(x) for x in prof_field]
    elif prof_field is None:
        names = []
    else:
        return {}, [], ["'profile' phai la string hoac list string"]
    for pname in names:
        prof, err = _load_profile(pname)
        if err:
            errors.append(err)
            continue
        params.update(prof.get("params", {}) or {})
        profiles_used.append({"name": prof.get("name", pname),
                              "verified": prof.get("verified"),
                              "description": prof.get("description")})
    params.update(pipe.get("params", {}) or {})
    for kv in kv_args:
        if "=" in kv:
            k, v = kv.split("=", 1)
            params[k] = v
    return params, profiles_used, errors


def _record_step(state, idx, sid, stype, ok, result):
    """Ghi/ghi de ket qua 1 step vao state.step_results (theo index)."""
    entry = {"index": idx, "id": sid, "type": stype,
             "status": "success" if ok else "failed",
             "result": result, "ts": time.time()}
    srs = state.setdefault("step_results", [])
    for j, e in enumerate(srs):
        if e.get("index") == idx:
            srs[j] = entry
            return
    srs.append(entry)


def _run_wait(step):
    """Poll tool moi interval_sec, danh gia until, toi khi dat hoac het timeout."""
    tool = step["tool"]
    arg_list = _tool_args_list(tool, step.get("args"))
    interval = int(step.get("interval_sec", 60))
    timeout = int(step.get("timeout_sec", 3600))
    until = step.get("until", {})
    deadline = time.time() + timeout
    polls, last_detail = 0, ""
    while True:
        polls += 1
        res, _ = _call_tool_capture(tool, arg_list)
        if res is not None:
            ok, last_detail = _eval_until(until, res)
            if ok:
                return True, {"status": "success", "polls": polls,
                              "detail": last_detail, "last_result": res}
        else:
            last_detail = "tool khong tra JSON"
        if time.time() >= deadline:
            return False, {"status": "error", "reason": "timeout",
                           "polls": polls, "detail": last_detail}
        time.sleep(interval)


def _run_step(step):
    """Chay 1 step (tru llm_gate). Tra (ok, result_dict) — result luon co 'status'."""
    st = step.get("type")
    if st == "tool":
        arg_list = _tool_args_list(step["tool"], step.get("args"))
        res, raw = _call_tool_capture(step["tool"], arg_list)
        if res is None:
            return False, {"status": "error", "summary": "tool khong tra JSON",
                           "raw": raw[:1000]}
        return (res.get("status") != "error"), res
    if st == "shell":
        rc, out, err = _sh_bash(step["cmd"],
                                timeout=int(step.get("timeout_sec", 600)))
        return rc == 0, {"status": "success" if rc == 0 else "error", "rc": rc,
                         "stdout_tail": (out or "").strip().splitlines()[-20:],
                         "stderr_tail": (err or "").strip().splitlines()[-10:]}
    if st == "wait":
        return _run_wait(step)
    return False, {"status": "error", "summary": f"type '{st}' khong ho tro"}


def _pipe_execute(pipe_id):
    """RUNNER (noi bo, chay detached). Doc state -> chay tiep tu current_step.

    Checkpoint SAU MOI step. Gap llm_gate -> ghi NEED_LLM, set WAITING_LLM, dung.
    """
    state_file, need_llm_file, answer_file = _pipe_paths(pipe_id)
    state = _read_json(state_file)
    if not state:
        logger.error("pipe_execute: khong doc duoc state %s", pipe_id)
        return
    steps = state["pipeline"]["steps"]
    state["status"] = "RUNNING"
    state["runner_pid"] = os.getpid()
    state["updated_at"] = time.time()
    _write_json(state_file, state)

    i = state.get("current_step", 0)
    while i < len(steps):
        step = steps[i]
        sid = step.get("id", "step%d" % i)
        stype = step.get("type")
        logger.info("pipe %s: step[%d] %s (%s)", pipe_id, i, sid, stype)

        if stype == "llm_gate":
            ans = _read_json(answer_file)
            if ans and "answer" in ans:  # da co answer -> tieu thu, di tiep
                _record_step(state, i, sid, stype, True,
                             {"status": "answered", "answer": ans["answer"],
                              "question": step.get("question")})
                state["llm_answer"] = ans["answer"]
                for f in (answer_file, need_llm_file):
                    try:
                        os.remove(f)
                    except OSError:
                        pass
                i += 1
                state["current_step"] = i
                state.pop("need_llm", None)
                _write_json(state_file, state)
                continue
            need = {"pipe_id": pipe_id, "step_id": sid,
                    "question": step.get("question"),
                    "context_files": step.get("context_files", [])}
            _write_json(need_llm_file, need)
            state["status"] = "WAITING_LLM"
            state["current_step"] = i
            state["need_llm"] = need
            state["updated_at"] = time.time()
            _write_json(state_file, state)
            logger.info("pipe %s: WAITING_LLM tai step '%s'", pipe_id, sid)
            return  # exit sach, cho pipe_resume

        retry = int(step.get("retry", 0))
        on_fail = step.get("on_fail", "abort")
        ok, result, attempt = False, {}, 0
        while attempt <= retry:
            attempt += 1
            ok, result = _run_step(step)
            if ok:
                break
            if attempt <= retry:
                logger.warning("pipe %s: step '%s' fail lan %d, thu lai sau 30s",
                               pipe_id, sid, attempt)
                time.sleep(30)
        result["attempts"] = attempt
        _record_step(state, i, sid, stype, ok, result)

        if not ok and on_fail == "abort":
            state["status"] = "FAILED"
            state["current_step"] = i  # dung o step loi de sua & resume
            state["updated_at"] = time.time()
            _write_json(state_file, state)
            logger.error("pipe %s: FAILED tai step '%s' (on_fail=abort)",
                         pipe_id, sid)
            return

        i += 1
        state["current_step"] = i
        _write_json(state_file, state)

    state["status"] = "DONE"
    state["updated_at"] = time.time()
    _write_json(state_file, state)
    logger.info("pipe %s: DONE (%d step)", pipe_id, len(steps))


def _spawn_detached_pipe(pipe_id):
    """Spawn runner pipeline o tien trinh nen detached, tra ve PID."""
    devnull = open(os.devnull, "w")
    proc = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "_pipe_exec", pipe_id],
        stdout=devnull, stderr=devnull, stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    return proc.pid


def _pipe_progress(state):
    """Tom tat tien do step (dung cho pipe_status/pipe_list)."""
    steps = (state.get("pipeline") or {}).get("steps", [])
    done = sum(1 for e in state.get("step_results", [])
               if e.get("status") == "success")
    return {"n_steps": len(steps), "done": done,
            "current_step": state.get("current_step", 0)}


def cmd_pipe_run(args):
    """NUT PIPE RUN. Validate schema -> spawn runner nen -> tra ve tuc thi + pipe_id.

    Cu phap: pipe_run <file.json> [K=V ...]
    """
    if not args:
        return emit({"status": "error",
                     "summary": "Cu phap: pipe_run <file.json> [K=V ...]"})
    pfile = _resolve_pipe_file(args[0])
    if not pfile:
        return emit({"status": "error",
                     "summary": f"Khong tim thay pipeline: {args[0]} "
                                f"(da thu ./{args[0]} va {CE_PIPES_DIR})"})
    pipe = _read_json(pfile)
    if pipe is None:
        return emit({"status": "error", "summary": f"Khong parse duoc JSON: {pfile}"})
    errs = _validate_pipeline(pipe)
    if errs:
        return emit({"status": "error", "summary": "Pipeline sai schema.",
                     "errors": errs})
    params, profiles_used, perrs = _resolve_params(pipe, args[1:])
    if perrs:
        return emit({"status": "error",
                     "summary": "Loi nap execution profile.", "errors": perrs})
    resolved = _subst(pipe, params)
    pipe_id = "%s_%d" % (re.sub(r"[^A-Za-z0-9_]+", "_",
                                str(pipe.get("name", "pipe"))), int(time.time()))
    state_file, _, _ = _pipe_paths(pipe_id)
    state = {"pipe_id": pipe_id, "name": pipe.get("name"), "pipe_file": pfile,
             "params": params, "profiles": profiles_used, "pipeline": resolved,
             "status": "RUNNING",
             "current_step": 0, "step_results": [],
             "created_at": time.time(), "updated_at": time.time()}
    _write_json(state_file, state)
    try:
        pid = _spawn_detached_pipe(pipe_id)
        state["runner_pid"] = pid
        _write_json(state_file, state)
        logger.info("pipe_run %s -> runner PID %s (%d step)", pipe_id, pid,
                    len(resolved["steps"]))
        emit({"status": "started", "pipe_id": pipe_id, "runner_pid": pid,
              "name": pipe.get("name"), "n_steps": len(resolved["steps"]),
              "profiles": profiles_used, "state_file": state_file,
              "summary": f"Da khoi chay pipeline '{pipe.get('name')}' "
                         f"(id={pipe_id}) o nen. Dung pipe_status {pipe_id}."})
    except Exception as e:
        logger.exception("pipe_run spawn that bai.")
        state["status"] = "FAILED"
        _write_json(state_file, state)
        emit({"status": "error", "pipe_id": pipe_id,
              "summary": f"Khong spawn duoc runner: {e}"})


def cmd_pipe_exec(args):
    """NUT NOI BO (khong danh cho CDK). Chay runner blocking."""
    if not args:
        logger.error("_pipe_exec thieu pipe_id")
        sys.exit(1)
    _pipe_execute(args[0])


def cmd_pipe_status(args):
    """NUT PIPE STATUS. Doc state file -> tien do tung step.

    Cu phap: pipe_status [pipe_id]   (khong co pipe_id -> tom tat tat ca)
    """
    if not args:
        return cmd_pipe_list(args)
    pipe_id = args[0]
    state_file, _, _ = _pipe_paths(pipe_id)
    state = _read_json(state_file)
    if not state:
        return emit({"status": "unknown", "pipe_id": pipe_id,
                     "summary": "Khong co state (chua chay hoac da xoa)."})
    results = {e["index"]: e for e in state.get("step_results", [])}
    steps_view = []
    for i, s in enumerate((state.get("pipeline") or {}).get("steps", [])):
        r = results.get(i)
        steps_view.append({
            "index": i, "id": s.get("id"), "type": s.get("type"),
            "status": (r or {}).get("status", "pending"),
            "summary": ((r or {}).get("result") or {}).get("summary")})
    prog = _pipe_progress(state)
    emit({"status": "success", "pipe_id": pipe_id,
          "pipe_status": state.get("status"), "progress": prog,
          "profiles": state.get("profiles"),
          "need_llm": state.get("need_llm")
          if state.get("status") == "WAITING_LLM" else None,
          "llm_answer": state.get("llm_answer"), "steps": steps_view,
          "summary": "Pipeline %s: %s (%d/%d step)"
          % (pipe_id, state.get("status"), prog["done"], prog["n_steps"])})


def cmd_pipe_resume(args):
    """NUT PIPE RESUME. Chay tiep tu step do (sau crash / sau khi co LLM answer).

    Cu phap: pipe_resume <pipe_id>
    Neu WAITING_LLM: can co pipe_<id>_LLM_ANSWER.json {answer:"..."} truoc.
    """
    if not args:
        return emit({"status": "error", "summary": "Cu phap: pipe_resume <pipe_id>"})
    pipe_id = args[0]
    state_file, _, answer_file = _pipe_paths(pipe_id)
    state = _read_json(state_file)
    if not state:
        return emit({"status": "error", "pipe_id": pipe_id,
                     "summary": "Khong co state de resume."})
    if state.get("status") == "DONE":
        return emit({"status": "error", "pipe_id": pipe_id,
                     "summary": "Pipeline da DONE, khong can resume."})
    if state.get("status") == "WAITING_LLM":
        ans = _read_json(answer_file)
        if not ans or "answer" not in ans:
            return emit({"status": "waiting_llm", "pipe_id": pipe_id,
                         "need_llm": state.get("need_llm"),
                         "summary": "Dang cho LLM. Hay ghi %s {answer:\"...\"} "
                                    "roi resume lai." % answer_file})
    probe = RobustJobController("_pipe_probe")
    if probe.check_process_alive(state.get("runner_pid", -1)):
        return emit({"status": "error", "pipe_id": pipe_id, "state": "ALIVE",
                     "runner_pid": state.get("runner_pid"),
                     "summary": "Runner cu con song. Dung pipe_stop truoc khi resume."})
    try:
        pid = _spawn_detached_pipe(pipe_id)
        logger.info("pipe_resume %s -> runner PID %s (tu step %s)",
                    pipe_id, pid, state.get("current_step"))
        emit({"status": "resumed", "pipe_id": pipe_id, "runner_pid": pid,
              "from_step": state.get("current_step"),
              "summary": f"Da chay tiep pipeline {pipe_id} tu step "
                         f"{state.get('current_step')}."})
    except Exception as e:
        logger.exception("pipe_resume spawn that bai.")
        emit({"status": "error", "pipe_id": pipe_id,
              "summary": f"Khong spawn duoc runner: {e}"})


def cmd_pipe_stop(args):
    """NUT PIPE STOP. Kill runner + danh dau STOPPED trong state.

    Cu phap: pipe_stop <pipe_id>
    """
    if not args:
        return emit({"status": "error", "summary": "Cu phap: pipe_stop <pipe_id>"})
    pipe_id = args[0]
    state_file, _, _ = _pipe_paths(pipe_id)
    state = _read_json(state_file)
    if not state:
        return emit({"status": "unknown", "pipe_id": pipe_id,
                     "summary": "Khong co state."})
    killed, pid = None, state.get("runner_pid", -1)
    try:
        if pid and pid > 0:
            os.kill(pid, signal.SIGTERM)
            killed = pid
    except (OSError, ProcessLookupError):
        pass
    state["status"] = "STOPPED"
    state["updated_at"] = time.time()
    _write_json(state_file, state)
    logger.info("pipe_stop %s killed=%s", pipe_id, killed)
    emit({"status": "success", "pipe_id": pipe_id, "killed_pid": killed,
          "summary": f"Da dung pipeline {pipe_id}"
                     + (f" (kill runner {killed})." if killed
                        else " (runner khong con song).")})


def cmd_pipe_list(args):
    """NUT PIPE LIST. Liet ke moi pipeline run trong RUN_DIR.

    Cu phap: pipe_list
    """
    pipes = []
    for fn in sorted(os.listdir(RUN_DIR)):
        if fn.startswith("pipe_") and fn.endswith("_state.json"):
            st = _read_json(os.path.join(RUN_DIR, fn)) or {}
            pipes.append({"pipe_id": st.get("pipe_id"), "name": st.get("name"),
                          "status": st.get("status"),
                          "progress": _pipe_progress(st),
                          "updated_at": st.get("updated_at")})
    emit({"status": "success", "summary": f"Tim thay {len(pipes)} pipeline.",
          "pipelines": pipes})


def cmd_profile_list(args):
    """NUT PROFILE LIST. Liet ke cac execution profile + verified date.

    Cu phap: profile_list
    Doc moi <ten>.json trong CE_PROFILES_DIR, tra name/verified/description +
    danh sach key params (khong dump het gia tri de gon).
    """
    profs = []
    if os.path.isdir(CE_PROFILES_DIR):
        for fn in sorted(os.listdir(CE_PROFILES_DIR)):
            if not fn.endswith(".json"):
                continue
            d = _read_json(os.path.join(CE_PROFILES_DIR, fn)) or {}
            profs.append({"name": d.get("name", fn[:-5]),
                          "verified": d.get("verified"),
                          "description": d.get("description"),
                          "params_keys": sorted((d.get("params") or {}).keys()),
                          "file": fn})
    emit({"status": "success", "profiles_dir": CE_PROFILES_DIR,
          "summary": f"Tim thay {len(profs)} execution profile.",
          "profiles": profs})


# ============================================================================
# DISPATCH — bang anh xa ten NUT -> handler.
# ============================================================================
COMMANDS = {
    # Vong doi job nang (CDK bam nut):
    "bg_run": cmd_bg_run,
    "bg_status": cmd_bg_status,
    "bg_monitor": cmd_bg_status,   # bi danh giu tuong thich framework v3 cu
    "bg_report": cmd_bg_report,
    "check_or_restart": cmd_check_or_restart,
    "bg_stop": cmd_bg_stop,
    "bg_cleanup": cmd_bg_cleanup,
    "bg_list": cmd_bg_list,
    "bg_selftest": cmd_bg_selftest,
    "gate_count": cmd_gate_count,
    "hard_sl_sweep": cmd_hard_sl_sweep,
    "invsel_run": cmd_invsel_run,
    # WFO (Walk-Forward Optimization) fleet:
    "wfo_run": cmd_wfo_run,
    "wfo_fanout": cmd_wfo_fanout,
    "wfo_status": cmd_wfo_status,
    "wfo_report": cmd_wfo_report,
    "wfo_stop": cmd_wfo_stop,
    # WFO-from-preds (R1: CSV preds -> predict_wf -> dataset -> verify 1 window):
    "pred_convert": cmd_pred_convert,
    "wfo_build_ds": cmd_wfo_build_ds,
    "wfo_verify": cmd_wfo_verify,
    # He thong / suc khoe VPS:
    "sys_health": cmd_sys_health,
    "sys_zombies": cmd_sys_zombies,
    "sys_logtail": cmd_sys_logtail,
    # Tien ich ha tang:
    "manage_jvm": cmd_manage_jvm,
    "remote_ssh": cmd_remote_ssh,
    # Kaggle fleet:
    "kaggle_slots": cmd_kaggle_slots,
    "kaggle_push": cmd_kaggle_push,
    "kaggle_status": cmd_kaggle_status,
    "kaggle_output": cmd_kaggle_output,
    "kaggle_parse_logs": cmd_kaggle_parse_logs,
    # Pipeline engine (declarative, may-lam-het + LLM-gate):
    "pipe_run": cmd_pipe_run,
    "pipe_status": cmd_pipe_status,
    "pipe_resume": cmd_pipe_resume,
    "pipe_stop": cmd_pipe_stop,
    "pipe_list": cmd_pipe_list,
    # Execution profile (L4 — cach chay co dinh theo moi truong x cong nghe):
    "profile_list": cmd_profile_list,
    # Noi bo (KHONG danh cho CDK):
    "_supervise": cmd_supervise,
    "_pipe_exec": cmd_pipe_exec,
}

USAGE = """Su dung: python3 mcp_tools-v3.py <nut> [args...]

VONG DOI JOB NANG (CDK chi bam nut, Python tu lo):
  bg_run <job_id> "<cmd>" [ram_gb]          START nen, tra ve tuc thi.
  bg_status <job_id> [tail_lines]           STATUS: state+result+tail log.
  bg_report <job_id>                        REPORT: Result Contract gon.
  check_or_restart <job_id> "<cmd>" [ram]   RETRY: chan doan + chay lai an toan.
  bg_stop <job_id>                          STOP: dung job + don lock.
  bg_cleanup <job_id> [--all]               CLEANUP: xoa state/lock (--all: ca result/log).
  bg_list                                   LIST: liet ke moi job da biet.
  bg_selftest                               TU-TEST tron chuoi bg_* bang job sleep.

WFO (WALK-FORWARD OPTIMIZATION):
  wfo_fanout <ds> [jar] [n] [seed] [oracle_workers] [kaggle_kernels] [tag] [extra_env]
                                            MAC DINH cho WFO full-16-window: reset + 2 Oracle worker
                                            + push 5 Kaggle kernel (cung jobstore 226 = 6 node).
  wfo_run <ds> [jar] [n] [seed] [workers] [tag]
                                            Oracle-only (reset + spawn N WfoWorker). CHI dung debug/1-window.
  wfo_status                                Parse total/PENDING/RUNNING/DONE/FAILED + cua so FAILED.
  wfo_report [tag]                          Chay report, cp md ve RUN_DIR, parse VERDICT/%OOS/WFE/maxDD.
  wfo_stop                                  pkill WfoWorker + VerifyOneWindow, bao so proc bi kill.

WFO-FROM-PREDS (chuoi R1: CSV preds -> predict_wf -> dataset -> verify 1 window):
  pred_convert <csv> <out_dir> <mode> [param]
                                            CSV preds -> predict_wf_<win>.bin (venv XGB).
                                            mode=long|oiz|short (oiz: param=OIZ_Q quantile).
  wfo_build_ds <predict_wf_dir> <out_ds> [jar]
                                            ExportWfoDataset DETACHED -> dataset offline.
                                            Goi lai khi xong -> fundingCount tu manifest.
  wfo_verify <ds> <winIdx> [extra_env]      VerifyOneWindow 1 window (jobstore-free) ->
                                            RESULT_JSON {oosPnl,wfe,oosTrades,oosNote}.
                                            extra_env ho tro WFO_JAR=/WFO_XMX= (short-verify).

HE THONG (VPS):
  sys_health                                disk(df /) + RAM + load + danh sach java proc.
  sys_zombies [kill=true]                   Liet ke WfoWorker/VerifyOneWindow/CopyTicker (kill=true de kill).
  sys_logtail <file> [n]                    n dong cuoi 1 tep trong RUN_DIR (chan path-traversal).

HA TANG:
  manage_jvm list | kill <pid>              Liet ke / dung JVM (chan proc LIVE cot loi).
  remote_ssh <host> "<cmd>"                 SSH co retry, tu chon port/user.

KAGGLE FLEET:
  kaggle_slots                              So slot dang dung / con trong.
  kaggle_push <folder>                      Gac cong slot roi push kernel.
  kaggle_status <slug>                      Trang thai kernel.
  kaggle_output <slug> <dir>                Tai ket qua kernel.
  kaggle_parse_logs <log_file>              Giai ma JSON log + boc block RESULT.

PIPELINE ENGINE (may lam het TRON CHUOI, LLM chi gac o llm_gate):
  pipe_run <file.json> [K=V ...]            Validate + spawn runner nen -> pipe_id.
  pipe_status [pipe_id]                      Tien do tung step (bo trong: tom tat het).
  pipe_resume <pipe_id>                      Chay tiep sau crash / sau khi co LLM answer.
  pipe_stop <pipe_id>                        Kill runner + danh dau STOPPED.
  pipe_list                                  Liet ke moi pipeline run.

EXECUTION PROFILE (L4 — cach chay co dinh theo moi truong x cong nghe):
  profile_list                               Liet ke profiles + verified date.
  (Pipeline khai bao "profile":"<ten>" -> tu nap params ha tang. Uu tien merge:
   CLI K=V > pipeline params > profile params.)
"""


def main():
    """Diem vao CLI: doc argv, dispatch den handler tuong ung."""
    if len(sys.argv) < 2:
        emit({"status": "error", "summary": "Thieu ten nut.", "usage": USAGE})
        sys.exit(1)

    cmd = sys.argv[1]
    handler = COMMANDS.get(cmd)
    if handler is None:
        emit({"status": "error", "summary": f"Nut '{cmd}' khong hop le.", "usage": USAGE})
        sys.exit(1)

    try:
        handler(sys.argv[2:])
    except SystemExit:
        raise  # ton trong sys.exit() tu handler/controller
    except Exception as e:
        # Khong bao gio nuot exception: log day du + emit JSON loi cho CDK.
        logger.exception("Ngoai le khong mong doi khi chay nut '%s'.", cmd)
        emit({"status": "error", "summary": f"Ngoai le khi chay '{cmd}': {e}",
              "traceback": traceback.format_exc()})
        sys.exit(1)


if __name__ == "__main__":
    main()
