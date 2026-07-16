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

# So slot Kaggle toi da (chinh qua env neu chinh sach doi).
KAGGLE_MAX_SLOTS = int(os.environ.get("CE_KAGGLE_MAX_SLOTS", "5"))
# Dem RAM he thong (GB) cong them vao ram_limit truoc khi cho phep chay.
RAM_SAFETY_BUFFER_GB = float(os.environ.get("CE_RAM_BUFFER_GB", "3.0"))
# Tien trinh LIVE cot loi: TUYET DOI khong duoc kill.
PROTECTED_PROCS = ["BinanceDataIngestor", "BinanceOrderTradingManager",
                   "Aerospike", "Redis"]

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
        with open(path, "r", errors="ignore") as f:
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


def _count_kaggle_slots():
    """Dem slot Kaggle dang dung (running + queued). Tra (used, running, queued) hoac None neu loi."""
    p = subprocess.run("kaggle kernels list --mine", shell=True,
                       capture_output=True, text=True)
    if p.returncode != 0:
        logger.error("Loi truy van Kaggle kernels: %s", p.stderr.strip())
        return None
    running = queued = 0
    for line in p.stdout.strip().splitlines():
        if "running" in line:
            running += 1
        elif "queued" in line:
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
                       "slots_used": used, "slots_available": available}})
    except Exception as e:
        logger.exception("Loi kiem tra Kaggle slots.")
        emit({"status": "error", "summary": f"Loi kiem tra Kaggle slots: {e}"})


def cmd_kaggle_push(args):
    """NUT KAGGLE PUSH. Tu gac cong slot roi push kernel len Kaggle.

    Cu phap: kaggle_push <kernel_folder_path>
    """
    if not args:
        return emit({"status": "error", "summary": "Cu phap: kaggle_push <kernel_folder_path>"})
    folder = args[0]
    try:
        counts = _count_kaggle_slots()
        used = counts[0] if counts else 0
        if used >= KAGGLE_MAX_SLOTS:
            logger.warning("Chan push: da dat %s slot.", used)
            return emit({"status": "error",
                         "summary": f"CHAN AN TOAN: da dat gioi han {KAGGLE_MAX_SLOTS} slot "
                                    f"({used} dang dung). Khong push them."})
        p = subprocess.run(f"cd {folder} && kaggle kernels push -p .",
                           shell=True, capture_output=True, text=True)
        ok = p.returncode == 0
        (logger.info if ok else logger.error)("kaggle_push rc=%s", p.returncode)
        emit({"status": "success" if ok else "error",
              "summary": "Da push kernel len Kaggle." if ok else f"Loi push kernel: {p.returncode}",
              "stdout": p.stdout.strip(), "stderr": p.stderr.strip()})
    except Exception as e:
        logger.exception("Loi push Kaggle.")
        emit({"status": "error", "summary": f"Loi push Kaggle: {e}"})


def cmd_kaggle_status(args):
    """NUT KAGGLE STATUS. Trang thai 1 kernel.

    Cu phap: kaggle_status <kernel_slug>
    """
    if not args:
        return emit({"status": "error", "summary": "Cu phap: kaggle_status <kernel_slug>"})
    slug = args[0]
    try:
        p = subprocess.run(f"kaggle kernels status {slug}", shell=True,
                           capture_output=True, text=True)
        ok = p.returncode == 0
        emit({"status": "success" if ok else "error",
              "summary": p.stdout.strip() if ok else f"Khong lay duoc trang thai {slug}",
              "stderr": p.stderr.strip()})
    except Exception as e:
        logger.exception("Loi Kaggle status.")
        emit({"status": "error", "summary": f"Loi ket noi Kaggle API: {e}"})


def cmd_kaggle_output(args):
    """NUT KAGGLE OUTPUT. Tai tep ket qua kernel ve thu muc dich.

    Cu phap: kaggle_output <kernel_slug> <target_download_dir>
    """
    if len(args) < 2:
        return emit({"status": "error",
                     "summary": "Cu phap: kaggle_output <kernel_slug> <target_download_dir>"})
    slug, target_dir = args[0], args[1]
    os.makedirs(target_dir, exist_ok=True)
    try:
        p = subprocess.run(f"kaggle kernels output {slug} -p {target_dir}",
                           shell=True, capture_output=True, text=True)
        ok = p.returncode == 0
        (logger.info if ok else logger.error)("kaggle_output rc=%s", p.returncode)
        emit({"status": "success" if ok else "error",
              "summary": f"Tai ket qua tu {slug} ve {target_dir}." if ok
              else f"Loi tai ket qua: {p.returncode}",
              "stdout": p.stdout.strip(), "stderr": p.stderr.strip()})
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
    # Tien ich ha tang:
    "manage_jvm": cmd_manage_jvm,
    "remote_ssh": cmd_remote_ssh,
    # Kaggle fleet:
    "kaggle_slots": cmd_kaggle_slots,
    "kaggle_push": cmd_kaggle_push,
    "kaggle_status": cmd_kaggle_status,
    "kaggle_output": cmd_kaggle_output,
    "kaggle_parse_logs": cmd_kaggle_parse_logs,
    # Noi bo (KHONG danh cho CDK):
    "_supervise": cmd_supervise,
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

HA TANG:
  manage_jvm list | kill <pid>              Liet ke / dung JVM (chan proc LIVE cot loi).
  remote_ssh <host> "<cmd>"                 SSH co retry, tu chon port/user.

KAGGLE FLEET:
  kaggle_slots                              So slot dang dung / con trong.
  kaggle_push <folder>                      Gac cong slot roi push kernel.
  kaggle_status <slug>                      Trang thai kernel.
  kaggle_output <slug> <dir>                Tai ket qua kernel.
  kaggle_parse_logs <log_file>              Giai ma JSON log + boc block RESULT.
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
