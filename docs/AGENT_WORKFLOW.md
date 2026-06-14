# AGENT_WORKFLOW (v2) — Điều phối bán tự động: CDK + orchestrator headless + worker CCD

> **v2 (2026-06-14):** sửa lại v1 (do phiên không-MCP soạn) theo hạ tầng THỰC. Khác v1 ở: live-gate TÁCH process/data, topology SSH-226 (không 242), timeout theo resource (không 10' cứng), model Kaggle kernel-độc-lập, giữ REVIEW gate, và **không chép luật — trỏ `CLAUDE.md`**.
> **Đọc trước khi:** sửa cơ chế điều phối. Phiên CDK mới chỉ cần: file này + `CLAUDE.md` + `docs/AGENTS.md` + `docs/DATA_ARCHITECTURE.md`.
> **Script thật:** `orchestrator/supervisor.py` (§9). **Trạng thái máy:** `orchestrator/runtime_state.json` + `orchestrator/STATUS.md`.

---

## 0. Mục tiêu & nguyên tắc bất biến

**Mục tiêu:** bỏ 2 việc tay — (1) forward report CCD↔CDK, (2) gõ "chạy task X" từng terminal. Người + CDK **lùi về planning + review**.

**Nguyên tắc cứng:**
1. **Live-gate 2 mức (đã tách — KHÁC v1):**
   - `touches_live_process=true` (deploy/restart `BinanceDataIngestor`/`BinanceOrderTradingManager`) → **KHÔNG BAO GIỜ auto**, đẩy người.
   - `writes_242_data=true` (ghi/sửa set 242: lấp gap, replicate, backfill) → **auto ĐƯỢC**, nhưng chỉ chạy **qua SSH 226** (xem §1). Không nhầm hai cái thành một như v1.
   - Đụng Aerospike/Redis/HPO của user trên 226: không kill bừa (luật `CLAUDE.md` §⚙️), nhưng đọc/ghi data thì auto được.
2. **Người ở lại mối ghép planning.** *Phân tích kết quả + viết spec* do người+CDK, KHÔNG giao planner headless. Lý do: dự án thắng nhờ *bắt kết luận sai* + *không tin "done" chưa kiểm*; planner headless sẽ tin report worker → tái lập failure-mode.
3. **Spec sai = hỏng nhân số-worker.** Bù: **pre-register acceptance** + ưu tiên acceptance **kiểm-được-bằng-máy**; task quan trọng giữ **REVIEW** (người soát) thay vì auto-DONE.
4. **Không đoán khi parse.** Report thiếu/sai format → `NEEDS_HUMAN`, không suy diễn.
5. **Luật kỹ thuật ở `CLAUDE.md`, KHÔNG chép vào đây** (kill-PID an toàn, SLF4J, bàn giao #4, checkpoint #5, System.exit #6, dọn tài nguyên #7, 242-data-qua-226). Worker mang theo `CLAUDE.md` mỗi run.

---

## 1. Vai trò & topology (sửa: SSH 226, KHÔNG 242)

| Thành phần | Chạy ở đâu | Làm gì | KHÔNG làm |
|---|---|---|---|
| **Người** | — | Quyết cuối; duyệt REVIEW/DONE; xử `NEEDS_HUMAN` + `touches_live_process` | Forward; trigger từng worker |
| **CDK (Claude Desktop)** | Local, filesystem MCP → E: | Phân tích report, viết spec/roadmap, tạo task, cập nhật `AGENTS.md` | Chạy shell; spawn worker (không có khả năng) |
| **Orchestrator (supervisor)** | **Local Windows, Python** | Poll queue, claim atomic, spawn worker headless, heartbeat/stale, dashboard, **ghi last-run-state** | Đụng live-process; sửa spec; tự quyết nghiệp vụ |
| **Worker CCD** | Local `claude -p` (headless) → **SSH 226**, Kaggle CLI | Thực thi 1 task, ghi report + RESULT contract | Deploy/restart 2 process live; `pkill/killall java` |

**Mạng (QUAN TRỌNG, v1 sai):** worker chạy trên máy dev. Dev/Kaggle **KHÔNG tới 242**. Mọi việc chạm 242 (đọc scan, ghi data) = **SSH vào 226 rồi chạy tại 226** (226 mới thông 242). Worker KHÔNG `ssh 242`.

**Kaggle là cloud độc lập:** worker chỉ **launch kernel + poll status qua Kaggle API**. Worker thoát/chết KHÔNG giết kernel; kernel "RUNNING" có thể đã xong nghiệp vụ nhưng treo (thiếu `System.exit` — `CLAUDE.md` #6). ⇒ supervisor theo dõi **kernel slug** (Kaggle API), KHÔNG suy ra trạng thái job từ tiến trình worker local.

**Kênh giao tiếp:** chỉ qua **file trên E:** (bus chung). Mỗi field một writer (§6).

---

## 2. Vòng đời task

```
[CDK/người: tasks/0XX.md status=TODO + acceptance + front-matter cờ]
        │
        ▼
[supervisor poll 60s] ── deps chưa DONE / hết slot / touches_live_process=true ──► chờ (hoặc đẩy người)
        │ đủ điều kiện + còn slot
        ▼
[claim atomic os.mkdir(locks/0XX)] → status=DOING, ghi runtime_state.json (started_at, kernel/pid)
        │
        ▼
[spawn worker headless: claude -p  (prompt = task.md + CLAUDE.md + AGENTS snapshot + DATA_ARCHITECTURE)]
   ├─ wrapper ghi heartbeat (pid|elapsed) mỗi 30s        → liveness MÁY
   ├─ worker ghi mốc-bước vào docs/reports/0XX.md         → tiến độ NGỮ NGHĨA
   └─ nếu job Kaggle: worker ghi kernel_slug → supervisor poll Kaggle API   → tiến độ KERNEL
        │
        ▼
[worker kết thúc bằng block RESULT (§4)]
        │
   ┌────┴───────────┬──────────────────┬─────────────────┐
   ▼                ▼                   ▼                 ▼
STATUS=DONE     STATUS=REVIEW      STATUS=NEEDS_HUMAN  STATUS=FAILED
(task thường)   (task quan trọng) đẩy STATUS.md       requeue ≤max_retry
status=DONE     chờ người soát    + chờ người         quá hạn→NEEDS_HUMAN
+commit, nhả                                          
        │
        ▼
[supervisor ghi last-run-state; người+CDK duyệt report → spec task kế]
```

---

## 3. Schema header task (`tasks/0XX.md`, front-matter YAML)

```yaml
id: 0XX
status: TODO                 # TODO|DOING|REVIEW|DONE|FAILED|NEEDS_HUMAN
                             #   TODO/REVIEW/DONE: người+CDK · DOING/FAILED/NEEDS_HUMAN: supervisor
depends_on: [015, 017]       # supervisor chỉ chạy khi TẤT CẢ = DONE
touches_live_process: false  # true => deploy/restart Ingestor/TradingManager => KHÔNG auto, đẩy người
writes_242_data: false       # true => ghi set 242 => auto ĐƯỢC nhưng BẮT BUỘC chạy qua SSH 226
resource: heavy_226          # local | heavy_226 | kaggle | kaggle_distributed  (cap riêng — §5.2)
checkpoint: false            # true => job dài, PHẢI resume-skip-done + output partial (CLAUDE.md #5)
max_retry: 2
report: docs/reports/0XX.md
require_review: false        # true => xong KHÔNG auto-DONE, sang REVIEW cho người soát
```

- **Acceptance** viết trong thân task, **pre-register trước khi để TODO**. Ưu tiên tiêu chí **kiểm-được-bằng-máy** (số dòng, fingerprint, recompute khớp) — worker đưa số vào RESULT.VERIFY để người/script đối chiếu, KHÔNG để worker tự tuyên "PASS".
- **Field runtime** (owner/pid/heartbeat/retry_count/started_at/kernel_slug) **KHÔNG để trong .md** → `runtime_state.json` (supervisor sở hữu).
- **`resource: kaggle_distributed`** = job NẶNG chia shard theo **master–worker** (tái dùng `RunHpoMaster_Distributed` + `RunWorkerKaggle`): supervisor spawn 1 **MASTER headless** → master ném task vào **queue Aerospike 226** → tự điều **≤5 Kaggle worker** poll queue song song. **Queue Aerospike = checkpoint phân tán** (worker chết → STALE → worker khác cướp; rerun chỉ làm task chưa DONE, KHÔNG lặp từ 0). Cap = 1 chiến dịch/lúc (5 worker dùng chung pool Kaggle ≤5). VD **TASK-013** backfill OI. Worker Kaggle ghi 226 → sau đẩy 226→242 (source) qua job trên 226.

---

## 4. Output contract (worker BẮT BUỘC kết thúc report bằng block này)

```
=== RESULT ===
STATUS: DONE | REVIEW | NEEDS_HUMAN | FAILED
COMMIT: <hash | ->
ARTIFACTS: <output path: CSV/jar/file 226 | ->
VERIFY: <số đối chiếu acceptance: #dòng, fingerprint, recompute... | ->
DECISIONS: <quyết-định reversible đã tự ra + log | ->
QUESTIONS: <gom 1 lần, chỉ câu thật cần người | ->
=== END ===
```

- Block là **phần cuối cùng**, fenced, key cố định. Thiếu/sai → `NEEDS_HUMAN`, **không đoán**.
- Câu hỏi vặt: tự quyết + ghi `DECISIONS` nếu reversible & không đụng live; **cấm hỏi giữa chừng** — gom cuối.
- `require_review=true` hoặc worker thấy cần người → `STATUS: REVIEW`.

---

## 5. Luật supervisor

1. **Poll 60s.** Chọn task: `status=TODO` ∧ mọi `depends_on`=DONE ∧ `touches_live_process=false` ∧ còn slot.
2. **Cap đồng thời:** toàn cục **4**. Cap phụ theo resource: **`heavy_226 ≤ 1`** (226 tài nguyên YẾU — 2 job đọc 5 năm 1m là sập; siết hơn v1) · **`kaggle ≤ 5`** (RUNBOOK; nhưng là kernel cloud nên ít tốn slot worker) · `local` tính vào cap 4.
3. **Claim atomic:** `os.mkdir(locks/<id>)` — thắng mới chạy. Cấm đọc-rồi-ghi. Set `status=DOING` + ghi `runtime_state.json`.
4. **Prompt worker = `tasks/0XX.md` + `CLAUDE.md` + snapshot `AGENTS.md` + `DATA_ARCHITECTURE.md`.** Bắt buộc mỗi run — worker headless không có mắt người, phải tự mang luật.
5. **Heartbeat 2 lớp + KERNEL:** wrapper `pid+elapsed`/30s (liveness máy); LLM mốc-bước trong report (ngữ nghĩa); job Kaggle → poll **kernel slug** qua API (nguồn sự thật cho job cloud). KHÔNG dùng tiến trình worker làm đồng hồ job Kaggle.
6. **Timeout THEO resource (KHÁC v1 — không 10' cứng):** `local` 20′ · `heavy_226` mặc định 4h (chỉnh per-task qua `timeout_min`) · `kaggle` 12h (theo cutoff). Stale = pid chết HOẶC quá timeout-resource HOẶC heartbeat-ngữ-nghĩa đứng quá ngưỡng → `FAILED` + nhả lock + requeue; quá `max_retry` → `NEEDS_HUMAN`. **Job `checkpoint=true` requeue thì resume-skip-done, không chạy lại từ 0.**
7. **`touches_live_process=true` KHÔNG auto** — liệt kê `STATUS.md` mục chờ-người. Lớp 2: luật `CLAUDE.md` buộc worker "task hoá ra phải deploy/restart 2 process → DỪNG + NEEDS_HUMAN".
8. **Đóng:** `STATUS=DONE` → set `.md status=DONE` + commit + nhả lock/slot. `require_review=true` hoặc `STATUS=REVIEW` → `status=REVIEW`, chờ người (KHÔNG nhả thành DONE).
9. **Idempotency + dọn:** task ghi Aerospike/backfill phải re-run-an-toàn (upsert/checkpoint). Worker xong phải dọn tài nguyên (`CLAUDE.md` #7: off kernel, kill đúng PID). Supervisor khi reap stale cũng cố off kernel slug nếu có.
10. **LAST-RUN-STATE (user yêu cầu — tường minh):** mỗi vòng poll supervisor ghi `runtime_state.json`:
    - top-level: `supervisor_pid`, `supervisor_last_tick` (ISO time), `last_action` (vd "spawned 017", "reaped 013 stale", "idle"), `slots_used`.
    - per-task: `{status, owner_pid, kernel_slug, started_at, last_heartbeat, last_semantic_step, retry_count, last_result_status, last_finished_at}`.
    - `STATUS.md` = render người-đọc của file trên (slot/4, từng worker, queue, NEEDS_HUMAN/chờ-live, **supervisor còn sống không + lần tick cuối**). Mở Desktop đọc 1 file thấy toàn cảnh.
11. **Dừng tay:** Ctrl-C = dừng dispatch mới; worker đang chạy để tự xong (không kill ngang).

---

## 6. Quyền ghi (single-writer mỗi field)

| File | Writer DUY NHẤT | Nội dung |
|---|---|---|
| `tasks/0XX.md` spec + acceptance + front-matter (lúc TODO) | **CDK / người** | Việc, deps, cờ, tiêu chí PASS |
| `tasks/0XX.md` field `status` lúc transition | **supervisor** | DOING/FAILED/NEEDS_HUMAN/DONE/REVIEW |
| `orchestrator/runtime_state.json` | **supervisor** | last-run-state §5.10 |
| `orchestrator/STATUS.md` | **supervisor** | dashboard |
| `docs/reports/0XX.md` | **worker** | tiến độ + RESULT |
| `docs/AGENTS.md` | **CDK** (summary người-đọc) | bảng tổng. **Worker KHÔNG ghi AGENTS nữa** (khác hiện tại — giảm race; worker chỉ ghi report) |

**Quy tắc:** CDK KHÔNG sửa `status` khi DOING; supervisor KHÔNG sửa thân spec; worker KHÔNG đụng AGENTS/runtime_state.

---

## 7. Phân pha (tuần tự, không big-bang)

- **Phase 0 (làm NGAY, không cần hạ tầng):** thêm front-matter §3 + RESULT contract §4 vào task; worker ghi report ra `docs/reports/`; file này trỏ `CLAUDE.md`. → diệt phần lớn forwarding + hỏi vặt. Người vẫn trigger nhưng thưa, theo lô.
- **Phase 1 (supervisor §9):** chạy cho task `touches_live_process=false`. Auto reversible; task quan trọng `require_review=true`. → diệt gõ trigger.
- **Phase 2 (planner headless):** **KHÔNG** (vi phạm §0.2). Người+CDK giữ planning.

---

## 8. Rủi ro & kỷ luật
- Spec ẩu = hỏng nhân 4 → pre-register acceptance kiểm-được-bằng-máy; ưu tiên reversible.
- Tin "done" → `require_review` cho task quan trọng; VERIFY phải có số.
- Parse contract giòn → format cứng; thiếu = NEEDS_HUMAN.
- Contention file → single-writer §6.
- Job nặng bị giết oan → timeout-theo-resource §5.6 + checkpoint.
- Token/quota: 4 worker headless song song = 4× token + supervisor luôn bật. Cap 4 + cap resource; theo dõi `STATUS.md`.

---

## 9. Orchestrator — `orchestrator/supervisor.py`

Script thật đã viết kèm (cùng commit). Tóm thành phần: poll loop 60s · scan `tasks/*.md` parse front-matter · check deps+slot+cap-resource+live-gate · claim lockdir `os.mkdir` · spawn `claude -p` (headless) với prompt §5.4 · wrapper heartbeat 30s · poll kernel Kaggle (nếu có slug) · parse RESULT §4 · stale reaper theo timeout-resource §5.6 · ghi `runtime_state.json`+`STATUS.md` §5.10 · live-gate §5.7.

**Headless — RẤT RÕ (user nhấn):** worker = `claude -p` (print mode, non-interactive). Lệnh mẫu supervisor spawn:
```
claude -p --dangerously-skip-permissions \
  --append-system-prompt "$(cat CLAUDE.md DATA_ARCHITECTURE.md)" \
  "Bạn là worker headless. Đọc task sau, thực thi, KẾT THÚC bằng block RESULT (§4 AGENT_WORKFLOW). Tuân CLAUDE.md tuyệt đối (kill-PID an toàn, không deploy/restart 2 process live, 242-data-qua-SSH-226, System.exit cuối main, checkpoint nếu job dài, dọn tài nguyên xong). Ghi tiến độ vào $REPORT.
=== TASK ===
$(cat tasks/0XX.md)"
```
- Cờ headless chính xác: xem https://docs.claude.com/en/docs/claude-code/overview (print/-p, output format). Supervisor chỉ điều phối — KHÔNG tự đụng live; live-gate nằm Ở supervisor + trong CLAUDE.md.
- stdout worker → supervisor đọc; nhưng **nguồn sự thật kết quả = block RESULT trong `docs/reports/0XX.md`**, không phải stdout (stdout có thể nhiễu).

**Acceptance script (tự test trước khi tin):** 2 task giả — 1 thường chạy OK; 1 `depends_on` chưa xong → KHÔNG chạy; 1 `touches_live_process=true` → KHÔNG auto; kill worker giữa chừng → reaper requeue đúng; vượt cap → không spawn quá 4/quá cap-resource.

---

## 10. Khởi tạo (CDK làm khi áp dụng)
1. Tạo `docs/reports/`, `locks/`, `orchestrator/`.
2. Tạo `orchestrator/runtime_state.json` (`{}`) + `orchestrator/STATUS.md` (placeholder) — supervisor ghi.
3. Thêm front-matter §3 vào header task chưa-done (rà toàn bộ `tasks/`).
4. `CLAUDE.md` đã có luật worker (#1–7) → file này TRỎ, không chép. Thêm pointer ở `CLAUDE.md` + `docs/index.md`.
5. `orchestrator/supervisor.py` để người chạy tay lần đầu (`python supervisor.py`) quan sát `STATUS.md` trước khi tin.
