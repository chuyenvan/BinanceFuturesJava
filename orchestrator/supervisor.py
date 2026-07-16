#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
supervisor.py — Orchestrator điều phối worker CCD headless (claude -p).

Đọc docs/AGENT_WORKFLOW.md (v2) trước khi sửa. Nguyên tắc cứng:
  - touches_live_process=true  -> KHÔNG BAO GIỜ auto (đẩy người).
  - writes_242_data=true       -> auto được, NHƯNG worker phải chạm 242 qua SSH 226 (luật ở CLAUDE.md).
  - Không sửa spec task; chỉ đổi field `status`. Single-writer: file này sở hữu runtime_state.json + STATUS.md + status-transition.
  - Worker headless chạy với cwd=ROOT -> Claude Code tự đọc CLAUDE.md (bản mỏng, trỏ docs/CORE.md + docs/index.md).
    Prompt chỉ-thị đọc CORE + nạp pack theo cờ task; KHÔNG nhồi nội dung file qua argv/--append-system-prompt.
    Luật thật ở docs/CORE.md + docs/rules|db (progressive disclosure).

Chạy: python supervisor.py            (vòng lặp thật)
      python supervisor.py --dry-run  (poll + in quyết định, KHÔNG spawn)
      python supervisor.py --once     (chạy 1 vòng rồi thoát)

Phụ thuộc: chỉ standard library. Front-matter parse tay (YAML phẳng), không cần PyYAML.
"""

import os
import re
import sys
import json
import time
import signal
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path

# ----------------------------------------------------------------------------
# CẤU HÌNH (chỉnh theo máy)
# ----------------------------------------------------------------------------
ROOT = Path(os.environ.get(
    "BFJ_ROOT",
    r"E:\educa\source\github\20260415\BinanceFuturesJava"
))
TASKS_DIR   = ROOT / "tasks"
REPORTS_DIR = ROOT / "docs" / "reports"
LOCKS_DIR   = ROOT / "locks"
ORCH_DIR    = ROOT / "orchestrator"
RUNTIME     = ORCH_DIR / "runtime_state.json"
STATUS_MD   = ORCH_DIR / "STATUS.md"

POLL_SEC = 60
CAP_GLOBAL = 6
# resource: local=may dieu phoi (CHI dispatch nhe, KHONG job nang), oracle=VPS compute chinh (sim/export/train),
#           heavy_226=benchmark only, kaggle=5 slot CPU, kaggle_distributed=1 chien dich/luc.
CAP_RESOURCE = {"local": 1, "oracle": 4, "heavy_226": 1, "kaggle": 5, "kaggle_distributed": 1}
TIMEOUT_MIN  = {"local": 20, "oracle": 360, "heavy_226": 240, "kaggle": 720, "kaggle_distributed": 1440}
HEARTBEAT_STALE_MIN = 20   # report mtime dung qua lau (process con song) -> nghi treo

# Model worker: TUYET DOI KHONG dung Fable (Uni chot 2026-07-10). Opus/Sonnet/Haiku deu duoc.
# Doi qua env WORKER_MODEL; mac dinh Sonnet (can bang toc do/chat luong cho task co-hoc).
WORKER_MODEL = os.environ.get("WORKER_MODEL", "claude-sonnet-4-6")

# Lệnh spawn worker headless. Đặt env CLAUDE_BIN nếu 'claude' không trên PATH.
# Cờ headless: https://docs.claude.com/en/docs/claude-code/overview
CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "claude")

# ----------------------------------------------------------------------------
def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

def log(msg):
    print(f"[{now_iso()}] {msg}", flush=True)

# ---- parse front-matter YAML phẳng (giữa cặp ---), không cần PyYAML ----------
def parse_front_matter(text):
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end].strip("\n")
    fm = {}
    for line in block.splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            inner = val[1:-1].strip()
            items = [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]
            fm[key] = items
        elif val.lower() in ("true", "false"):
            fm[key] = (val.lower() == "true")
        elif val.lstrip("-").isdigit():
            fm[key] = int(val)
        else:
            fm[key] = val.strip("'\"")
    return fm

def scan_tasks():
    """Trả list (id, path, fm). Bỏ task không có front-matter (chưa migrate Phase 0)."""
    out = []
    for p in sorted(TASKS_DIR.glob("*.md")):
        try:
            text = p.read_text(encoding="utf-8")
        except Exception as e:
            log(f"WARN không đọc được {p.name}: {e}")
            continue
        fm = parse_front_matter(text)
        if not fm or "id" not in fm:
            continue
        out.append((str(fm["id"]).zfill(3), p, fm))
    return out

# ---- runtime_state.json (single-writer = supervisor) ------------------------
def load_state():
    if RUNTIME.exists():
        try:
            return json.loads(RUNTIME.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"supervisor_pid": os.getpid(), "tasks": {}}

def save_state(state):
    state["supervisor_pid"] = os.getpid()
    state["supervisor_last_tick"] = now_iso()
    RUNTIME.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

# ---- đổi field status trong .md (chỉ supervisor ghi field này) --------------
def set_task_status(path, new_status):
    text = path.read_text(encoding="utf-8")
    m = re.search(r"^(status:\s*).*$", text, flags=re.MULTILINE)
    if m:
        text = text[:m.start()] + f"{m.group(1)}{new_status}" + text[m.end():]
        path.write_text(text, encoding="utf-8")

# ---- lock atomic ------------------------------------------------------------
def claim(task_id):
    lock = LOCKS_DIR / str(task_id)
    try:
        os.mkdir(lock)          # atomic: thắng mới chạy
        return True
    except FileExistsError:
        return False

def release(task_id):
    lock = LOCKS_DIR / str(task_id)
    try:
        os.rmdir(lock)
    except FileNotFoundError:
        pass

# ---- parse block RESULT (nguồn sự thật = report file, KHÔNG phải stdout) -----
RESULT_RE = re.compile(r"=== RESULT ===\s*(.*?)\s*=== END ===", re.DOTALL)
def parse_result(report_path):
    if not report_path.exists():
        return None
    txt = report_path.read_text(encoding="utf-8", errors="replace")
    matches = RESULT_RE.findall(txt)
    if not matches:
        return None
    block = matches[-1]   # block CUỐI cùng
    res = {}
    for line in block.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            res[k.strip().upper()] = v.strip()
    if "STATUS" not in res:
        return None  # sai format -> caller đánh NEEDS_HUMAN
    return res

# ---- spawn worker headless --------------------------------------------------
def resolve_claude():
    """Tìm executable claude. Windows: .cmd/.bat phải chạy qua `cmd /c`. None nếu không có."""
    p = shutil.which(CLAUDE_BIN)
    if not p:
        return None
    if os.name == "nt" and p.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", p]
    return [p]

def packs_for(fm):
    """Goi y pack tri thuc theo co front-matter (tang recall cho worker headless).
    Worker van tu doc docs/index.md de nap them; day chi la goi y chac-chan theo co."""
    hints = []
    res = fm.get("resource", "local")
    if res in ("kaggle", "kaggle_distributed"):
        hints.append("docs/KAGGLE_RULES.md (BAT BUOC truoc moi Kaggle job: slot=5, 12h-kill, System.exit, o-C)")
    if res == "heavy_226":
        hints.append("docs/rules/run-226.md (don job cu + kill dung PID) + docs/db/index.md")
    if fm.get("writes_242_data", False):
        hints.append("docs/db/aerospike-242.md + docs/rules/run-226.md (ghi 242 => chay qua SSH 226)")
    if fm.get("touches_live_process", False):
        hints.append("docs/deploy/ (NHUNG deploy/restart 2 process live = NGUOI tay -> task nay khong tu lam)")
    hints.append("docs/rules/code.md + docs/rules/backtest.md (neu cham code/sim/HPO)")
    hints.append("docs/db/index.md (neu doc/ghi Aerospike)")
    return hints

def build_prompt(task_path):
    # Prompt NGAN: worker chay voi cwd=ROOT -> Claude Code tu doc CLAUDE.md (ban mong, tro CORE+index).
    # KHONG nhoi noi dung file qua argv/--append-system-prompt (vuot gioi han argv Windows + escape vo).
    text = task_path.read_text(encoding="utf-8")
    fm = parse_front_matter(text) or {}
    task_rel = task_path.relative_to(ROOT).as_posix()
    report_rel = f"docs/reports/{task_path.stem.split('-')[0]}.md"
    pack_lines = "\n".join(f"  - {h}" for h in packs_for(fm))
    return (
        "Ban la WORKER HEADLESS, thuc thi dung MOT task roi dung. "
        "DOC TRUOC (BAT BUOC): docs/CORE.md (luat an toan + toan ven backtest) va docs/index.md (router tri thuc). "
        "CLAUDE.md (cwd) la ban mong tro toi CORE+index; tu index NAP pack theo loai viec.\n"
        f"Pack lien quan task nay (doc neu cham toi):\n{pack_lines}\n"
        f"Task can lam: {task_rel} (doc ky, lam dung pham vi).\n"
        "Tuan tuyet doi (chi tiet docs/CORE.md): khong pkill/killall, chi kill dung PID minh spawn; "
        "KHONG deploy/restart 2 process live (BinanceDataIngestor/BinanceOrderTradingManager) - task can thi DUNG; "
        "cham 242 qua SSH 226; System.exit(0) cuoi main tool batch; checkpoint neu job dai; don tai nguyen khi xong; cam hoi giua chung.\n"
        f"Ghi tien do (moc-buoc) vao {report_rel}, KET THUC bang block:\n"
        "=== RESULT ===\nSTATUS: DONE|REVIEW|NEEDS_HUMAN|FAILED\nCOMMIT: <hash|->\n"
        "ARTIFACTS: <path|->\nVERIFY: <so doi chieu|->\nDECISIONS: <|->\nQUESTIONS: <|->\n=== END ==="
    )

def spawn_worker(task_id, task_path):
    base = resolve_claude()
    if base is None:
        raise FileNotFoundError(
            f"Khong tim thay '{CLAUDE_BIN}' tren PATH. Cai Claude Code CLI hoac dat env CLAUDE_BIN = duong dan day du."
        )
    prompt = build_prompt(task_path)
    # --model: pin worker (Opus/Sonnet/Haiku). TUYET DOI KHONG Fable (Uni chot). Mac dinh WORKER_MODEL.
    cmd = base + ["-p", "--dangerously-skip-permissions", "--model", WORKER_MODEL]
    logf = (REPORTS_DIR / f"{task_id}.worker.log").open("w", encoding="utf-8")
    proc = subprocess.Popen(
        cmd, cwd=str(ROOT),
        stdin=subprocess.PIPE, stdout=logf, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8",
    )
    try:
        proc.stdin.write(prompt)
        proc.stdin.close()
    except Exception:
        pass
    log(f"spawned worker task={task_id} pid={proc.pid}")
    return proc

# ----------------------------------------------------------------------------
class Supervisor:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.state = load_state()
        self.procs = {}          # task_id -> Popen
        self.stop = False

    def running_ids(self):
        return [tid for tid, p in self.procs.items() if p.poll() is None]

    def slots_used(self):
        return len(self.running_ids())

    def resource_used(self, resource):
        cnt = 0
        for tid in self.running_ids():
            r = self.state["tasks"].get(tid, {}).get("resource", "local")
            if r == resource:
                cnt += 1
        return cnt

    def deps_done(self, fm, all_status):
        for d in fm.get("depends_on", []) or []:
            if all_status.get(str(d).zfill(3)) != "DONE":
                return False
        return True

    def report_mtime_min(self, task_id):
        rp = REPORTS_DIR / f"{task_id}.md"
        if not rp.exists():
            return None
        age = time.time() - rp.stat().st_mtime
        return age / 60.0

    # ---- thu hoạch worker đã kết thúc --------------------------------------
    def harvest(self, tasks_by_id):
        for tid in list(self.procs.keys()):
            proc = self.procs[tid]
            if proc.poll() is None:
                continue  # còn chạy
            # đã kết thúc -> đọc RESULT
            path = tasks_by_id.get(tid)
            rp = REPORTS_DIR / f"{tid}.md"
            res = parse_result(rp)
            tinfo = self.state["tasks"].setdefault(tid, {})
            if res is None:
                log(f"task={tid} ket thuc nhung RESULT thieu/sai -> NEEDS_HUMAN")
                if path: set_task_status(path, "NEEDS_HUMAN")
                tinfo["last_result_status"] = "NEEDS_HUMAN(parse-fail)"
            else:
                st = res.get("STATUS", "").upper()
                tinfo["last_result_status"] = st
                tinfo["last_commit"] = res.get("COMMIT", "-")
                if st == "DONE":
                    if path: set_task_status(path, "DONE")
                    log(f"task={tid} DONE commit={res.get('COMMIT','-')}")
                elif st == "REVIEW":
                    if path: set_task_status(path, "REVIEW")
                    log(f"task={tid} REVIEW -> cho nguoi")
                elif st == "NEEDS_HUMAN":
                    if path: set_task_status(path, "NEEDS_HUMAN")
                    log(f"task={tid} NEEDS_HUMAN: {res.get('QUESTIONS','-')}")
                elif st == "FAILED":
                    self.handle_failed(tid, path, tinfo)
                else:
                    if path: set_task_status(path, "NEEDS_HUMAN")
            tinfo["last_finished_at"] = now_iso()
            release(tid)
            del self.procs[tid]

    def handle_failed(self, tid, path, tinfo):
        tinfo["retry_count"] = tinfo.get("retry_count", 0) + 1
        maxr = tinfo.get("max_retry", 2)
        if tinfo["retry_count"] > maxr:
            log(f"task={tid} FAILED qua max_retry -> NEEDS_HUMAN")
            if path: set_task_status(path, "NEEDS_HUMAN")
        else:
            log(f"task={tid} FAILED -> requeue ({tinfo['retry_count']}/{maxr})")
            if path: set_task_status(path, "TODO")   # checkpoint=true -> worker tự resume-skip

    # ---- reap stale (pid chết bất thường / quá timeout / treo) --------------
    def reap_stale(self, tasks_by_id):
        for tid in list(self.procs.keys()):
            proc = self.procs[tid]
            if proc.poll() is not None:
                continue
            tinfo = self.state["tasks"].get(tid, {})
            resource = tinfo.get("resource", "local")
            started = tinfo.get("started_at_epoch", time.time())
            elapsed_min = (time.time() - started) / 60.0
            timeout = TIMEOUT_MIN.get(resource, 60)
            # idle = thoi gian tu HOAT DONG GAN NHAT = max(start, mtime report).
            # Tranh giet oan khi report cu ton tai tu truoc (worker chua kip ghi moi).
            rp = REPORTS_DIR / f"{tid}.md"
            last_act = started
            if rp.exists():
                last_act = max(started, rp.stat().st_mtime)
            idle_min = (time.time() - last_act) / 60.0
            stale = False
            reason = ""
            if elapsed_min > timeout:
                stale, reason = True, f"qua timeout {resource} {timeout}'"
            elif idle_min > HEARTBEAT_STALE_MIN and resource not in ("kaggle", "kaggle_distributed"):
                stale, reason = True, f"idle {idle_min:.0f}' tu hoat dong cuoi (nghi treo)"
            if stale:
                log(f"task={tid} STALE ({reason}) -> kill + requeue")
                try:
                    proc.terminate()
                except Exception:
                    pass
                path = tasks_by_id.get(tid)
                self.handle_failed(tid, path, self.state["tasks"].setdefault(tid, {}))
                release(tid)
                del self.procs[tid]

    # ---- một vòng poll ------------------------------------------------------
    def tick(self):
        tasks = scan_tasks()
        tasks_by_id = {tid: path for tid, path, fm in tasks}
        all_status = {}
        for tid, path, fm in tasks:
            text = path.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"^status:\s*(\S+)", text, flags=re.MULTILINE)
            all_status[tid] = m.group(1) if m else fm.get("status", "TODO")

        self.harvest(tasks_by_id)
        self.reap_stale(tasks_by_id)

        actions = []
        for tid, path, fm in tasks:
            status = all_status.get(tid, "TODO")
            resource = fm.get("resource", "local")
            reason = None
            if tid in self.procs:
                reason = "dang chay (worker nay spawn)"
            elif status != "TODO":
                reason = f"status={status} (khong pick)"
            elif fm.get("touches_live_process", False):
                reason = "touches_live_process -> nguoi deploy tay"
            elif not self.deps_done(fm, all_status):
                reason = f"cho deps {fm.get('depends_on')}"
            elif self.slots_used() >= CAP_GLOBAL:
                reason = "het slot toan cuc"
            elif self.resource_used(resource) >= CAP_RESOURCE.get(resource, CAP_GLOBAL):
                reason = f"het cap resource {resource}"
            if reason:
                if self.dry_run:
                    log(f"  SKIP {tid}: {reason}")
                continue
            # đủ điều kiện
            if self.dry_run:
                log(f"  READY {tid} ({resource}) -> WOULD spawn")
                actions.append(f"WOULD spawn {tid} ({resource})")
                continue
            if not claim(tid):
                continue
            set_task_status(path, "DOING")
            try:
                proc = spawn_worker(tid, path)
            except Exception as e:
                log(f"spawn FAIL {tid}: {e} -> rollback (status TODO + nha lock)")
                set_task_status(path, "TODO")
                release(tid)
                continue
            self.procs[tid] = proc
            tinfo = self.state["tasks"].setdefault(tid, {})
            tinfo.update({
                "status": "DOING", "owner_pid": proc.pid, "resource": resource,
                "started_at": now_iso(), "started_at_epoch": time.time(),
                "max_retry": fm.get("max_retry", 2),
                "checkpoint": fm.get("checkpoint", False),
                "require_review": fm.get("require_review", False),
            })
            actions.append(f"spawned {tid} ({resource})")

        self.state["last_action"] = "; ".join(actions) if actions else "idle"
        self.state["slots_used"] = self.slots_used()
        # cập nhật heartbeat semantic cho task đang chạy
        for tid in self.running_ids():
            mt = self.report_mtime_min(tid)
            self.state["tasks"].setdefault(tid, {})["report_age_min"] = round(mt, 1) if mt is not None else None
        save_state(self.state)
        self.write_status_md(tasks, all_status)

    # ---- dashboard người-đọc ------------------------------------------------
    def write_status_md(self, tasks, all_status):
        lines = []
        lines.append("# STATUS - orchestrator dashboard (supervisor ghi, dung sua tay)\n")
        lines.append(f"- supervisor_pid: {os.getpid()} | last_tick: {now_iso()} | last_action: {self.state.get('last_action','-')}")
        lines.append(f"- slots: {self.slots_used()}/{CAP_GLOBAL}  (heavy_226 {self.resource_used('heavy_226')}/{CAP_RESOURCE['heavy_226']}, kaggle {self.resource_used('kaggle')}/{CAP_RESOURCE['kaggle']}, kaggle_distributed {self.resource_used('kaggle_distributed')}/{CAP_RESOURCE['kaggle_distributed']})\n")
        lines.append("## Dang chay")
        run = self.running_ids()
        if run:
            for tid in run:
                t = self.state["tasks"].get(tid, {})
                lines.append(f"- {tid}: pid={t.get('owner_pid')} resource={t.get('resource')} started={t.get('started_at')} report_age={t.get('report_age_min')}'")
        else:
            lines.append("- (none)")
        lines.append("\n## Cho nguoi (live-process / NEEDS_HUMAN / REVIEW)")
        waiting = []
        for tid, path, fm in tasks:
            st = all_status.get(tid)
            if fm.get("touches_live_process", False) and st == "TODO":
                waiting.append(f"- {tid}: touches_live_process -> nguoi deploy tay")
            if st in ("NEEDS_HUMAN", "REVIEW"):
                waiting.append(f"- {tid}: {st}")
        lines += waiting if waiting else ["- (none)"]
        lines.append("\n## Queue (TODO san sang / bi chan deps)")
        for tid, path, fm in tasks:
            st = all_status.get(tid)
            if st != "TODO" or fm.get("touches_live_process", False):
                continue
            blocked = not self.deps_done(fm, all_status)
            tag = "BLOCKED deps" + str(fm.get("depends_on")) if blocked else "ready"
            lines.append(f"- {tid} ({fm.get('resource','local')}): {tag}")
        STATUS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def run(self, once=False):
        log(f"supervisor start (dry_run={self.dry_run}) ROOT={ROOT}")
        # dọn lock mồ côi từ lần chạy trước (start = chưa kế thừa proc nào)
        if not self.dry_run:
            for d in list(LOCKS_DIR.glob("*")):
                if d.is_dir():
                    try:
                        os.rmdir(d)
                        log(f"don lock mo coi: {d.name}")
                    except OSError:
                        pass
            # reset task DOING mo coi (instance truoc chet) -> TODO de chay lai (checkpoint tu resume)
            for tid, path, fm in scan_tasks():
                txt = path.read_text(encoding="utf-8")
                m = re.search(r"^status:\s*(\S+)", txt, flags=re.MULTILINE)
                if m and m.group(1) == "DOING":
                    set_task_status(path, "TODO")
                    log(f"reset task mo coi DOING->TODO: {tid}")
        def handle_sigint(sig, frame):
            log("Ctrl-C: dung dispatch moi; worker dang chay de tu xong.")
            self.stop = True
        signal.signal(signal.SIGINT, handle_sigint)
        while not self.stop:
            try:
                self.tick()
            except Exception as e:
                log(f"ERROR tick: {e}")
            if once:
                break
            for _ in range(POLL_SEC):
                if self.stop:
                    break
                time.sleep(1)
        running = [t for t, p in self.procs.items() if p.poll() is None]
        if running:
            log(f"dung dispatch. Cho {len(running)} worker con lai: {running}")
            for tid, p in self.procs.items():
                if p.poll() is None:
                    p.wait()
        else:
            log("dung dispatch. Khong co worker nao dang chay.")
        log("supervisor thoat.")

# ----------------------------------------------------------------------------
if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    once = "--once" in sys.argv or dry
    for d in (REPORTS_DIR, LOCKS_DIR, ORCH_DIR):
        d.mkdir(parents=True, exist_ok=True)
    Supervisor(dry_run=dry).run(once=once)
