# KIẾN TRÚC (V3): COGNITIVE – EXECUTION SEPARATION FRAMEWORK
## Điều phối TỰ ĐỘNG HOÀN TOÀN: Python làm HẾT phần thực thi, CDK chỉ "bấm nút"

**Nguyên tắc chốt:** Phần THỰC THI (spawn, poll, retry, report, cleanup) do **Python**
đảm nhận trọn vẹn qua 2 lớp — `supervisor.py` (điều phối task) và `mcp_tools-v3.py`
(thực thi job nặng). **Claude Code Desktop (CDK) chỉ "bấm nút"**: gọi 1 lệnh cấp cao rồi
đọc JSON trả về; KHÔNG tự gõ từng lệnh giám sát, KHÔNG "chờ mù" (blind waiting). Khi cần
đổi kịch bản/thêm nút, để **Claude Code triển khai** bằng cách sửa 2 file Python này.

---

## CHANGELOG (bản cập nhật gần nhất)

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
| Liệt kê/kill JVM | `manage_jvm list \| kill <pid>` | Liệt kê Java; kill 1 PID (CHẶN cứng process LIVE cốt lõi) |
| SSH retry | `remote_ssh <host> "<cmd>"` | SSH không banner, tự chọn port/user, retry mạng rớt |
| Kaggle slots | `kaggle_slots` | Báo số slot dùng/còn trống (giới hạn `CE_KAGGLE_MAX_SLOTS`) |
| Kaggle push | `kaggle_push <folder>` | Gác cổng slot rồi push kernel |
| Kaggle status | `kaggle_status <slug>` | Trạng thái kernel |
| Kaggle output | `kaggle_output <slug> <dir>` | Tải kết quả kernel về |
| Kaggle logs | `kaggle_parse_logs <log_file>` | Giải mã JSON log → 50 dòng cuối + block `=== RESULT ===` |

> `_supervise` là lệnh **nội bộ** (do `bg_run`/`check_or_restart` tự gọi ở tiến trình nền) —
> CDK KHÔNG gọi trực tiếp.

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
