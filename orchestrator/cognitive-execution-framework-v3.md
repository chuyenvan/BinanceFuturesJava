# KIẾN TRÚC (V3): COGNITIVE – EXECUTION SEPARATION FRAMEWORK
## Điều phối TỰ ĐỘNG HOÀN TOÀN: Python làm HẾT phần thực thi, CDK chỉ "bấm nút"

**Nguyên tắc chốt:** Phần THỰC THI (spawn, poll, retry, report, cleanup) do **Python**
đảm nhận trọn vẹn qua 2 lớp — `supervisor.py` (điều phối task) và `mcp_tools-v3.py`
(thực thi job nặng). **Claude Code Desktop (CDK) chỉ "bấm nút"**: gọi 1 lệnh cấp cao rồi
đọc JSON trả về; KHÔNG tự gõ từng lệnh giám sát, KHÔNG "chờ mù" (blind waiting). Khi cần
đổi kịch bản/thêm nút, để **Claude Code triển khai** bằng cách sửa 2 file Python này.

---

## CHANGELOG (bản cập nhật gần nhất)

- **Thêm tầng EXECUTION PROFILE — L4 (mục 1.9).** "Cách chạy CỐ ĐỊNH theo môi trường ×
  công nghệ" tách khỏi pipeline nghiệp vụ (L5). Pipeline chỉ khai báo `"profile":"<tên>"`
  (hoặc list) → engine nạp `CE_PROFILES_DIR/<tên>.json` merge sẵn params hạ tầng
  (JAR/HOST/XMX/dataset…). Thứ tự ưu tiên: **CLI override > pipeline params > profile params**.
  Thêm nút `profile_list`; `pipe_status`/state ghi profile đã dùng + verified date. Kiến trúc
  giờ 5 tầng (L1 infra → L2 transport → L3 atomic → L4 profiles → L5 business pipelines):
  **job mới chỉ viết + test L5; L4 đã verified thì KHÔNG test lại.** 4 profile chuẩn ở
  `orchestrator/profiles/`: `java-oracle`, `java-226`, `java-kaggle`, `python-kaggle`.
- **Thêm PIPELINE ENGINE khai báo (mục 1.8).** Kịch bản đổi = sửa FILE `.json`, KHÔNG
  sửa code; máy chạy trọn chuỗi step `tool/shell/wait/llm_gate`, checkpoint sau mỗi step,
  `llm_gate` **dừng-và-chờ** (không tự gọi LLM). 5 nút: `pipe_run/status/resume/stop/list`.
- **Đồng bộ framework với code thực tế.** Bổ sung Lớp 1 (`supervisor.py`) vốn bị thiếu
  trong bản cũ; làm rõ đây là 2 lớp độc lập (không import chéo).
- **`mcp_tools-v3.py` viết lại theo hướng "1 nút = trọn vòng đời":**
  - `bg_run` / `check_or_restart` nay **detached** — spawn controller chạy nền qua lệnh
    nội bộ `_supervise` rồi **trả JSON tức thì** (đúng tinh thần "bấm nút", không còn block
    như bản cũ).
  - Thêm các nút vòng đời còn thiếu: **`bg_report`, `bg_stop`, `bg_cleanup`, `bg_list`**.
    Đổi tên `bg_monitor` → `bg_status` (giữ `bg_monitor` làm bí danh, không phá tương thích).
  - Chuẩn hoá xuất/nhập: **stdout = 1 khối JSON máy-đọc** (qua `emit()`); **chẩn đoán dùng
    `logging`** ra stderr + `RUN_DIR/mcp_tools.log` (bỏ `print` theo chuẩn dự án).
  - **Không nuốt exception**: mọi lỗi `logging.exception(...)` + emit JSON `status:"error"`.
  - Tham số hoá qua env: `CE_RUN_DIR`, `CE_LOCKS_DIR`, `CE_KAGGLE_MAX_SLOTS`, `CE_RAM_BUFFER_GB`.
  - Đã qua `python -m py_compile` (không lỗi cú pháp).

---

## 0. Hai lớp thực thi (bức tranh tổng thể)

| | **Lớp 1 – `supervisor.py`** | **Lớp 2 – `mcp_tools-v3.py`** |
|---|---|---|
| Chạy ở | Máy điều phối (Windows local) | VPS/compute (Linux: oracle/226) |
| Vai trò | Điều phối **task** (`tasks/*.md`): tự spawn worker CCD headless (`claude -p`), poll, harvest `=== RESULT ===`, retry, ghi `STATUS.md` + `runtime_state.json` | Bọc **job nặng** (Java backtest, Kaggle, HPO): chịu lỗi cực đoan, cam kết Result Contract |
| CDK "bấm nút" | `python supervisor.py` (vòng lặp) / `--once` / `--dry-run` | `python3 mcp_tools-v3.py <nút> ...` |
| Đơn vị công việc | 1 task `.md` có front-matter | 1 `job_id` |
| Nguồn sự thật | report file `docs/reports/<id>.md` (block `=== RESULT ===`) | `<job_id>_result.json` (Result Contract) |

> 2 lớp **độc lập** (không import chéo). Lớp 1 điều phối "ai làm gì khi nào"; Lớp 2 là
> "tay chân" thực thi job tính toán nặng an toàn. Cùng dùng chung quy ước block
> `=== RESULT === ... === END ===` làm hợp đồng kết quả.

```
        ┌────────────────────────── CDK (chỉ BẤM NÚT) ──────────────────────────┐
        │  "chạy điều phối"                         "chạy job nặng / theo dõi"    │
        └───────────┬───────────────────────────────────────┬───────────────────┘
                    │ python supervisor.py                   │ python3 mcp_tools-v3.py <nút>
                    ▼                                         ▼
        ┌───────────────────────┐                 ┌──────────────────────────────┐
        │   LỚP 1 supervisor.py │                 │   LỚP 2 mcp_tools-v3.py       │
        │  scan tasks/*.md      │                 │  RobustJobController          │
        │  spawn worker (claude)│                 │  bg_run→_supervise (nền)      │
        │  poll + harvest RESULT│                 │  heartbeat / result contract  │
        │  retry / STATUS.md    │                 │  diagnose + retry + cleanup   │
        └───────────┬───────────┘                 └───────────────┬──────────────┘
                    ▼                                              ▼
          runtime_state.json                          <job_id>_state/result/.log
             STATUS.md                                  (RUN_DIR/.run)
```

---

## 1. LỚP 2 – `mcp_tools-v3.py`: 1 nút = trọn vòng đời

CDK gọi **1 lệnh cấp cao**, Python tự lo: spawn → giám sát → report → retry → cleanup.
Mỗi lệnh in ra **đúng một khối JSON** ở stdout (kênh máy-đọc cho CDK); log chẩn đoán đi
stderr + `RUN_DIR/mcp_tools.log`.

### 1.1 Hợp đồng trạng thái (Contract) — 3 tệp bền vững tại `RUN_DIR/.run/`

1. **`<job_id>_state.json`** — heartbeat động, cập nhật ~10s/lần (polling siêu nhẹ):
   ```json
   { "job_id":"hpo_v10", "status":"RUNNING", "controller_pid":12345,
     "child_pid":12346, "last_heartbeat":1784112000.0,
     "progress":"TICK 45/100: ETHUSDT..." }
   ```
2. **`<job_id>_result.json`** — **Result Contract (cam kết đầu ra duy nhất)**. Dù SUCCESS /
   FAILED / KILLED, tệp này **luôn được ghi** trước khi controller thoát → CDK không "chờ mù":
   ```json
   { "status":"SUCCESS|FAILED|KILLED", "exit_code":0,
     "stop_reason":"...", "timestamp":1784112500.0,
     "last_known_logs":["...","=== RESULT === PnL=+3428 ... === END ==="],
     "extracted_result":"PnL=+3428 CAGR=3.2% maxDD=-29.5%" }
   ```
3. **`<job_id>.log`** — stdout/stderr của tiến trình con (Java/Kaggle).

### 1.2 Cơ chế "bấm nút trả về tức thì"

`bg_run` / `check_or_restart` **không block**: chúng spawn controller chạy nền (detached,
`start_new_session`) qua lệnh nội bộ **`_supervise`** rồi emit JSON ngay (kèm `controller_pid`).
`_supervise` mới là tiến trình chạy `RobustJobController.run()` — vòng đời thật.

### 1.3 Chống lỗi cực đoan (Fault-Tolerance)

- **Bẫy tín hiệu** `SIGINT`/`SIGTERM` → `handle_signal` → `cleanup_and_exit`: thu hồi tiến
  trình con (SIGTERM→5s→SIGKILL), chụp 20 dòng log cuối, ghi Result Contract `KILLED`, giải
  phóng lock, thoát sạch (không để tiến trình mồ côi găm RAM).
- **Bẫy ngoại lệ** runtime: bọc `try/except`, ghi `FAILED` + traceback vào result file.
- **RAM-gate**: chặn khởi chạy nếu RAM khả dụng < `ram_limit + CE_RAM_BUFFER_GB` (mặc định 3GB).

### 1.4 Chẩn đoán & bấm lại nút an toàn (`check_or_restart`)

TUYỆT ĐỐI không `bg_run` đè lên job đang sống (gây 2 tiến trình cùng ghi → hỏng dữ liệu
backtest/Aerospike). Dùng `check_or_restart` để `diagnose_and_cleanup()` xử lý 4 kịch bản:

```
   A. Cả controller & child CHẾT (sập nguồn)   → dọn tệp rác, chạy lại.
   B. Controller CHẾT, child SỐNG mồ côi        → ghi lỗi, cưỡng chế kill child, chạy lại.
   C. Controller SỐNG, child CHẾT (treo loop)   → dọn wrapper treo, chạy lại.
   D. Cả hai SỐNG nhưng heartbeat > 30'         → cưỡng chế kill cả hai, ghi lỗi, chạy lại.
   (Job còn sống & heartbeat tươi)              → TỪ CHỐI chạy đè, báo ALIVE_DO_NOT_RESTART.
```

### 1.5 Quy ước cho CDK (Agent Rules)

- **Quy tắc lệch thời gian 30': ** khi theo dõi bằng `bg_status`, nếu
  `now - last_heartbeat > 30 phút` → coi job TREO/CHẾT LÂM SÀNG, **không chờ tiếp**, chuyển
  sang `check_or_restart`.
- **Bấm lại nút an toàn:** không bao giờ gọi `bg_run` để "chữa treo"; luôn dùng
  `check_or_restart` (nó tự chẩn đoán + dọn + chạy lại).

### 1.6 Bảng NÚT của Lớp 2

| Nút | Cú pháp | Python tự lo |
|---|---|---|
| **START** | `bg_run <job_id> "<cmd>" [ram_gb]` | Chẩn đoán nhanh → spawn controller nền → trả JSON tức thì |
| **STATUS** | `bg_status <job_id> [tail]` *(bí danh `bg_monitor`)* | Trả state realtime + result + N dòng log cuối |
| **REPORT** | `bg_report <job_id>` | Trả Result Contract gọn (ưu tiên result, fallback state) |
| **RETRY** | `check_or_restart <job_id> "<cmd>" [ram_gb]` | Chẩn đoán 4 kịch bản, dọn mồ côi, chạy lại nền an toàn |
| **STOP** | `bg_stop <job_id>` | Kill an toàn controller + child, dọn lock/state |
| **CLEANUP** | `bg_cleanup <job_id> [--all]` | Xoá state/lock (— `--all`: xoá cả result/log) |
| **LIST** | `bg_list` | Liệt kê mọi job đã biết + trạng thái sống/chết |
| **SELF-TEST** | `bg_selftest` | Tự chạy trọn chuỗi bg_* bằng job sleep → `overall: PASS/FAIL` (bấm sau mỗi lần sửa kịch bản) |
| **WFO fanout (MẶC ĐỊNH full-16-window)** | `wfo_fanout <ds> [jar] [n] [seed] [oracle_workers] [kaggle_kernels] [tag] [extra_env]` | Như `wfo_run` (reset + spawn Oracle worker) NHƯNG THÊM push tối đa 5 Kaggle kernel từ `KERNELS_DIR` (cùng jobstore 226) → 6-node fan-out. `extra_env` (vd `ABLATION_MODE=C,WFO_DISABLE_DCA=1`) chỉ áp Oracle worker; Kaggle dùng env baked. KHÔNG block |
| WFO run (Oracle-only, CHỈ debug/verify-1-window) | `wfo_run <ds> [jar] [n] [seed] [workers] [tag]` | Kill worker cũ → `WfoCoordinator reset` → spawn N `WfoWorker` nền (bg_run infra), KHÔNG block. Full-window → dùng `wfo_fanout` |
| WFO status | `wfo_status` | Parse total/PENDING/RUNNING/DONE/FAILED + list per-window FAILED |
| WFO report | `wfo_report [tag]` | Chạy `WfoCoordinator report`, cp md về `RUN_DIR/wfo_report_<tag>.md`, parse VERDICT/%OOS/WFE/maxDD + note-breakdown |
| WFO stop | `wfo_stop` | `pkill WfoWorker` + `VerifyOneWindow`, báo số proc bị kill |
| Sức khỏe VPS | `sys_health` | disk(`df /`) + RAM + load + danh sách java proc (pid/etime/main) |
| Zombie procs | `sys_zombies [kill=true]` | Liệt kê `WfoWorker`/`VerifyOneWindow`/`CopyTicker`; `kill=true` → kill + báo |
| Log tail | `sys_logtail <file> [n]` | N dòng cuối 1 tệp trong `RUN_DIR` (CHẶN path-traversal) |
| Liệt kê/kill JVM | `manage_jvm list \| kill <pid>` | Liệt kê Java; kill 1 PID (CHẶN cứng process LIVE cốt lõi) |
| SSH retry | `remote_ssh <host> "<cmd>"` | SSH không banner, tự chọn port/user, retry mạng rớt |
| Kaggle slots | `kaggle_slots` | Báo số slot dùng/còn trống (giới hạn `CE_KAGGLE_MAX_SLOTS`) |
| Kaggle push | `kaggle_push <folder>` | Gác cổng slot rồi push kernel |
| Kaggle status | `kaggle_status <slug>` | Trạng thái kernel |
| Kaggle output | `kaggle_output <kernel_ref> [dir]` | Kéo output về (mặc định `CE_RUN_DIR/kaggle_out/<ref-slug>/`), grep lỗi (Exception/FAIL-FAST/rc=) → `{log_path, errors_found[], tail}` |
| Kaggle logs | `kaggle_parse_logs <log_file>` | Giải mã JSON log → 50 dòng cuối + block `=== RESULT ===` |
| Profile list | `profile_list` | Liệt kê execution profile (L4) trong `CE_PROFILES_DIR` + `verified` + key params |

> **Kaggle chạy qua venv riêng:** mọi lệnh Kaggle gọi qua `_kaggle()` =
> `bash -c "<CE_KAGGLE_BIN> <subcmd>"`; `CE_KAGGLE_BIN` mặc định
> `source /home/ubuntu/kaggle_latest_venv/bin/activate && kaggle`. `kaggle_status` chuẩn hoá
> `kernel_state` = RUNNING/COMPLETE/ERROR/QUEUED; `kaggle_push` parse "successfully pushed".

> `_supervise` là lệnh **nội bộ** (do `bg_run`/`check_or_restart` tự gọi ở tiến trình nền) —
> CDK KHÔNG gọi trực tiếp.

### 1.7 Cây NÚT của Lớp 2 (đợt 1 đã có + TODO đợt 2)

```
mcp_tools-v3.py <nút>
├── bg_*  — vòng đời job nặng (RobustJobController + heartbeat + Result Contract)
│   ├── bg_run <job_id> "<cmd>" [ram_gb]        START nền (detached), trả tức thì
│   ├── bg_status <job_id> [tail]               STATUS (bí danh bg_monitor)
│   ├── bg_report <job_id>                       REPORT: Result Contract gọn
│   ├── check_or_restart <job_id> "<cmd>" [ram]  RETRY an toàn (4 kịch bản)
│   ├── bg_stop <job_id>                         STOP + dọn lock/state
│   ├── bg_cleanup <job_id> [--all]              CLEANUP state/lock (--all: cả result/log)
│   ├── bg_list                                  LIST mọi job đã biết
│   └── bg_selftest                              SELF-TEST trọn chuỗi bg_* bằng job sleep
│                                                → {steps[], overall: PASS/FAIL}
├── wfo_*  — Walk-Forward Optimization (đúc từ optimize_maxfav3.sh)
│   ├── wfo_fanout <ds> [jar] [n] [seed] [oracle_workers] [kaggle_kernels] [tag] [extra_env]
│   │        MẶC ĐỊNH full-16-window: reset → 2 Oracle worker + push ≤5 Kaggle kernel
│   │        (cùng jobstore 226) = 6-node fan-out. extra_env chỉ áp Oracle worker. KHÔNG block
│   ├── wfo_run <ds> [jar] [n] [seed] [workers] [tag]   (Oracle-only, CHỈ debug/verify-1-window)
│   │        kill WfoWorker cũ → WfoCoordinator reset (env WFO_N_SAMPLES)
│   │        → spawn <workers> WfoWorker nền (bg_run infra), KHÔNG block
│   ├── wfo_status                               parse total/PENDING/RUNNING/DONE/FAILED
│   ├── wfo_report [tag]                         cp report md → RUN_DIR, parse VERDICT/%OOS/WFE/maxDD
│   └── wfo_stop                                 pkill WfoWorker + VerifyOneWindow
├── sys_*  — sức khỏe & vệ sinh VPS
│   ├── sys_health                               disk(df /) + RAM + load + java procs
│   ├── sys_zombies [kill=true]                  WfoWorker/VerifyOneWindow/CopyTicker (+ kill)
│   └── sys_logtail <file> [n]                   N dòng cuối tệp trong RUN_DIR (chặn path-traversal)
├── manage_jvm / remote_ssh                      hạ tầng (đã có)
├── kaggle_slots/push/status/output/parse_logs   Kaggle fleet (đã có)
└── _supervise                                   NỘI BỘ (không dành cho CDK)

TODO đợt 2 (chưa cài):
├── data_*        — dựng/kiểm dataset _ff, copy ticker, split IS/OOS
├── kaggle_*      — mở rộng fleet Kaggle (auto push nhiều kernel, harvest hàng loạt)
├── wfo_ab        — chạy A/B 2 cấu hình WFO rồi so verdict
└── wfo_verify_window — verify lại 1 cửa sổ OOS bằng VerifyOneWindow
```

---

## 1.8 PIPELINE ENGINE (khai báo) — MÁY LÀM HẾT TRỌN CHUỖI, LLM chỉ GÁC ở điểm cần TƯ DUY

**Triết lý (chủ nhân chốt):** việc **CHÂN TAY** (chạy lệnh, chờ, poll, retry, so sánh
file) máy tự làm **trọn chuỗi** — KHÔNG cần LLM. LLM **chỉ** được gọi ở bước `llm_gate`
(điểm cần tư duy: chốt baseline, quyết định A/B...). **Đổi kịch bản = sửa FILE pipeline
`.json`, KHÔNG sửa code.**

Runner chạy **detached** (spawn qua lệnh nội bộ `_pipe_exec`, không giữ tty — pipeline
dài hàng giờ), thực thi tuần tự các step, **ghi checkpoint sau MỖI step** vào
`RUN_DIR/pipe_<id>_state.json`. Sập giữa chừng → `pipe_resume` chạy tiếp từ step dở.

### Định dạng file (JSON, stdlib — KHÔNG PyYAML)
File `.json` trong `CE_PIPES_DIR` (env, mặc định `/home/ubuntu/claudedata/.run/pipelines`;
`pipe_run` cũng nhận path trực tiếp / bỏ đuôi `.json`).

```json
{"name":"ab_objective","params":{"DS":"/home/ubuntu/claudedata/wfo_ds_maxfav3_4h_ff"},
 "steps":[
  {"id":"wfo_a","type":"tool","tool":"wfo_run",
   "args":{"ds":"${DS}","jar":"/home/ubuntu/java/simulator/preflight-226.jar","tag":"V41"},
   "on_fail":"abort","retry":1},
  {"id":"wait_a","type":"wait","tool":"wfo_status",
   "until":{"path":"counts.RUNNING","equals":0,"and_path":"counts.PENDING","and_equals":0},
   "interval_sec":120,"timeout_sec":18000},
  {"id":"rep_a","type":"tool","tool":"wfo_report","args":{"tag":"V41"}},
  {"id":"ab_merge","type":"shell","cmd":"grep -iE 'VERDICT|OOS' a.md b.md > ab_summary.txt"},
  {"id":"decide","type":"llm_gate","question":"V4.2 tốt hơn V4.1? Chốt baseline?",
   "context_files":["wfo_report_V41.md","wfo_report_V42.md"]}
 ]}
```

**Step (các field):**
- `id` (bắt buộc), `type`: `tool` | `shell` | `wait` | `llm_gate`.
- `on_fail`: `abort` (mặc định) | `continue`. `retry`: mặc định `0`, delay `30s` giữa các lần.
- `type=tool`: `tool`=tên nút; `args`=**dict named** (map sang positional qua bảng
  `TOOL_ARG_ORDER`, tự điền default, cắt đuôi rỗng để nút tự áp default) **hoặc list positional**.
  Gọi **nội bộ cùng process** (tạm đổi `sys.stdout` bắt khối JSON `emit()`) — KHÔNG subprocess đệ quy.
- `type=shell`: `cmd` chạy `bash -c` (hỗ trợ process substitution); lưu `rc` + tail stdout/stderr.
- `type=wait`: `tool`+`args` poll mỗi `interval_sec`, đọc JSON output của tool theo **dot-path**
  so với `until` tới khi đạt hoặc hết `timeout_sec`. `until` 2 dạng:
  - Gọn: `{"path":..,"equals":..[,"and_path":..,"and_equals":..]}` (như ví dụ).
  - Tổng quát: `{"conditions":[{"path":..,"equals|gt|lt|gte|lte":..}, ...]}` (AND toàn bộ).
- `type=llm_gate`: `question` + `context_files`. Runner ghi `RUN_DIR/pipe_<id>_NEED_LLM.json`
  `{question,context_files,step_id}`, set `status=WAITING_LLM` rồi **dừng-và-chờ** (exit sạch,
  **KHÔNG tự gọi LLM**). Khi có `RUN_DIR/pipe_<id>_LLM_ANSWER.json {answer:"..."}` thì
  `pipe_resume` tiêu thụ answer (lưu vào state) và đi tiếp.
- `${param}`: thay trong MỌI chuỗi từ `params` (merge override CLI `K=V`) trước khi chạy.

**State/checkpoint** (`RUN_DIR/pipe_<id>_state.json`): `pipe_id, name, pipe_file, params,
pipeline (đã resolve), status, current_step, runner_pid, step_results[], llm_answer`.
`status`: `RUNNING | WAITING_LLM | DONE | FAILED | STOPPED`.

### Bảng NÚT pipeline (Lớp 2)

| Nút | Cú pháp | Python tự lo |
|---|---|---|
| **PIPE RUN** | `pipe_run <file.json> [K=V ...]` | Validate schema → `${param}` subst → spawn runner nền (`_pipe_exec`) → trả `pipe_id` tức thì |
| **PIPE STATUS** | `pipe_status [pipe_id]` | Đọc state → tiến độ từng step (bỏ trống `pipe_id` → tóm tắt tất cả) |
| **PIPE RESUME** | `pipe_resume <pipe_id>` | Chạy tiếp từ step dở (sau crash; hoặc sau khi `llm_gate` có answer) |
| **PIPE STOP** | `pipe_stop <pipe_id>` | Kill runner (SIGTERM) + đánh dấu `STOPPED` |
| **PIPE LIST** | `pipe_list` | Liệt kê mọi pipeline run + status + tiến độ |

> `_pipe_exec` là lệnh **nội bộ** (runner detached tự chạy) — CDK KHÔNG gọi trực tiếp.
> 2 pipeline mẫu ở `orchestrator/pipelines/`: `selftest_pipe.json` (đi qua đủ 4 loại step
> để tự-test luồng) và `ab_objective.json` (A/B thật: wfo_run V41→wait→report→wfo_run V42
> →wait→report→gộp verdict→`llm_gate` chốt baseline).

**Luồng LLM-gate (điển hình):** `pipe_run` → chạy tự động → gặp `llm_gate` → `WAITING_LLM`
+ ghi `NEED_LLM.json` → **CDK/agent đọc câu hỏi + context_files, suy nghĩ, ghi
`LLM_ANSWER.json`** → `pipe_resume` → máy chạy nốt trọn chuỗi tới `DONE`.

---

## 1.9 EXECUTION PROFILE (L4) — "cách chạy CỐ ĐỊNH theo môi trường × công nghệ"

**Vấn đề:** pipeline nghiệp vụ (chạy gì, chờ gì, so gì) trước đây phải nhét lẫn cả chi tiết
env (JAR nào, HOST nào, XMX bao nhiêu, dataset version nào). Đổi 1 job = lại chép/sửa các
giá trị hạ tầng → dễ sai, khó verify. **Chốt (chủ nhân):** tách 1 tầng **EXECUTION PROFILE**
= "cách chạy cố định theo môi trường × công nghệ". Pipeline L5 **chỉ viết bước nghiệp vụ**;
tầng dưới (đã verified) được **dùng lại** qua profile.

### Kiến trúc 5 TẦNG (mỗi tầng chỉ tin tầng dưới đã verified)

```
L5  BUSINESS PIPELINES   pipelines/*.json — CHỈ bước nghiệp vụ (chạy gì→chờ gì→so gì→hỏi gì).
    (job mới viết ở đây)  Khai báo "profile":"<tên>"; KHÔNG lặp chi tiết env.
      ▲ dùng
L4  EXECUTION PROFILES   profiles/*.json — CÁCH CHẠY cố định (env × công nghệ):
    (verified, tái dùng)   {name, description, verified, params{JAR/HOST/XMX/dataset…}}.
      ▲ nạp params          java-oracle · java-226 · java-kaggle · python-kaggle · wfo-fanout(MẶC ĐỊNH WFO full).
L3  ATOMIC BUTTONS       nút cmd_* trong mcp_tools-v3.py: wfo_fanout/wfo_run/wfo_status/kaggle_push/…
    (selftest-verified)    1 nút = 1 việc nguyên tử, trả JSON máy-đọc.
      ▲ gọi
L2  TRANSPORT            bash -c / subprocess / remote_ssh / _kaggle(venv) / _sh_bash.
      ▲ chạy trên
L1  INFRA                Oracle VPS · máy 226 (LAN) · Aerospike(226:3222) · Kaggle fleet(cap 5).
```

**LUẬT VÀNG:** **job mới CHỈ viết + test tầng L5** (pipeline JSON). **L4 (profile) đã
`verified` thì KHÔNG test lại** — chỉ tái dùng. Chỉ khi hạ tầng đổi (VPS mới, jar path đổi,
policy slot đổi) mới sửa + verify lại profile rồi cập nhật `verified: YYYY-MM-DD`.
`verified: null` = chưa có job thật chạy qua CE → job đầu tiên chốt xong thì điền ngày.

### Cơ chế nạp & merge (trong engine)

- Pipeline thêm field tuỳ chọn `"profile": "java-oracle"` (hoặc list `["java-oracle","java-226"]`).
- `pipe_run` nạp `CE_PROFILES_DIR/<tên>.json` (env `CE_PROFILES_DIR`, mặc định
  `/home/ubuntu/claudedata/.run/profiles`) → merge `params`.
- **Thứ tự ưu tiên (thấp → cao): profile params < pipeline params < CLI `K=V`.** List profile:
  profile sau đè profile trước. Thiếu file profile → **lỗi rõ ràng** (nêu tên + `CE_PROFILES_DIR`).
- `pipe_run`/`pipe_status` + state ghi `profiles: [{name,verified,description}]` đã dùng.
- Nút `profile_list` liệt kê mọi profile + `verified` + key params.

### Bảng 4 PROFILE chuẩn (`orchestrator/profiles/`)

| Profile | verified | CỐ ĐỊNH (cách chạy) | ĐƯỢC PHÉP ĐỔI (ở L5) |
|---|---|---|---|
| **java-oracle** | 2026-07-16 | jar preflight-v42, XMX 8g, state Aerospike 226 ns=ticker, ticker=file, MAX_OOS 20260101 | dataset, N, workers, seed, tag |
| **java-226** | 2026-07-14 | chạy LAN `HOST_226=127.0.0.1`, jar `/root/preflight226.jar`, ns=ticker (merge/copy data) | dataset nguồn/đích, tag |
| **java-kaggle** | 2026-07-14 | kernel template + slots cap 5 + XMX 20g + ticker Aerospike-226 | jar/config = **bump version** dataset `java-run-lc`; data = bump ff dataset; notebook nguồn ở `KERNELS_DIR` |
| **python-kaggle** | *null* | kernel type=script, internet on, slots cap 5, session ≤12h, venv chuẩn | source notebook/script + dataset input (chờ job đầu để chốt) |

> **Ví dụ L5 dùng profile:** pipeline chỉ cần
> `{"name":"wfo_maxfav3","profile":"java-oracle","params":{"DS":"...","TAG_A":"V41"},"steps":[…]}`
> — `JAR/XMX/STATE_*` tự đến từ profile (đã verified), pipeline không lặp lại.

---

## 2. LỚP 1 – `supervisor.py`: điều phối task tự động

Vòng lặp `tick()` mỗi `POLL_SEC` (60s): quét `tasks/*.md` → lọc task `status: TODO` đủ điều
kiện (deps xong, còn slot toàn cục/theo resource, không `touches_live_process`) → `claim`
lock nguyên tử → đổi `status: DOING` → `spawn_worker` (`claude -p --model <WORKER_MODEL>`,
cwd=ROOT, prompt ngắn trỏ `docs/CORE.md`) → `harvest` khi worker xong (đọc block `=== RESULT ===`
trong report) → cập nhật `status` (DONE/REVIEW/NEEDS_HUMAN/FAILED) → `handle_failed` retry theo
`max_retry` → `reap_stale` kill worker quá timeout/treo → ghi `runtime_state.json` + `STATUS.md`.

**Bất biến (không được phá):** single-writer — chỉ `supervisor.py` ghi `runtime_state.json`,
`STATUS.md` và field `status` trong task; `touches_live_process=true` → KHÔNG auto (người
deploy tay); `writes_242_data` → chạm 242 qua SSH 226. Fable bị cấm (chốt 2026-07-10).

### 2.1 Nút của Lớp 1 (CDK bấm)

| Nút | Lệnh | Python tự lo |
|---|---|---|
| Chạy điều phối | `python supervisor.py` | Vòng lặp poll → dispatch → harvest → retry vô hạn tới khi Ctrl-C |
| Chạy 1 vòng | `python supervisor.py --once` | Poll + xử lý đúng 1 lần rồi thoát |
| Xem quyết định | `python supervisor.py --dry-run` | In "WOULD spawn / SKIP" mà KHÔNG spawn (an toàn) |

Cấu hình qua env: `BFJ_ROOT`, `WORKER_MODEL` (mặc định `claude-sonnet-4-6`), `CLAUDE_BIN`.

---

## 3. Khi nào cần Claude Code sửa kịch bản (không phải CDK "bấm nút")

CDK chỉ bấm các nút trên. Khi cần **đổi hành vi** → để Claude Code sửa 2 file Python:

> **NGOẠI LỆ QUAN TRỌNG — kịch bản pipeline:** đổi **thứ tự/nội dung chuỗi việc**
> (chạy gì, chờ gì, so sánh file nào, hỏi LLM câu gì) → **CHỈ sửa FILE `.json`** trong
> `CE_PIPES_DIR` (hoặc `orchestrator/pipelines/`), **KHÔNG đụng code**. Chỉ khi cần
> **loại step mới** (ngoài `tool/shell/wait/llm_gate`) hay **nút tool mới** thì mới sửa Python.

- Thêm/đổi **nút** ở Lớp 2 → thêm handler `cmd_*` + đăng ký vào dict `COMMANDS` trong
  `mcp_tools-v3.py`.
- Đổi **chính sách điều phối** (cap slot, timeout, luật resource, prompt worker, luật retry)
  → sửa hằng số/hàm tương ứng trong `supervisor.py` (`CAP_RESOURCE`, `TIMEOUT_MIN`,
  `HEARTBEAT_STALE_MIN`, `build_prompt`, `handle_failed`).
- Đổi **ngưỡng tài nguyên/hạ tầng** (RAM buffer, slot Kaggle, danh sách process LIVE được
  bảo vệ, host/port SSH) → env `CE_*` hoặc hằng số đầu `mcp_tools-v3.py`.
- Đổi **định dạng Result Contract / heartbeat** → phải sửa ĐỒNG BỘ cả nơi ghi
  (`_write_result_file`/`update_state`) và nơi đọc (`bg_status`/`bg_report`; `parse_result`
  ở supervisor nếu liên quan block `=== RESULT ===`).
