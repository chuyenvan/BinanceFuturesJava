# CE-BUTTONS — luật vận hành job qua nút & pipeline (chống đốt token vào việc chân tay)

> Triết lý (Uni chốt): **việc chân tay (chạy lệnh, chờ, poll, retry) máy làm TRỌN CHUỖI — LLM chỉ được
> gọi ở điểm cần TƯ DUY** (quyết định, thiết kế, code mới). Đổi kịch bản = sửa file JSON, không sửa code.

## LUẬT BẮT BUỘC cho mọi phiên LLM
1. **TRƯỚC KHI viết bất kỳ script vận hành nào** (bash driver, vòng poll, chuỗi bước):
   kiểm tra nút/pipeline có sẵn: `orchestrator/ce.cmd` (local) hoặc `python3 mcp_tools-v3.py` (VPS),
   pipeline mẫu ở `orchestrator/pipelines/*.json`. CÓ SẴN → dùng. GẦN GIỐNG → copy JSON, sửa, chạy.
   **CẤM viết bash driver ad-hoc mới cho việc mà pipeline làm được.**
2. **Mọi job > 5 phút** → `bg_run` hoặc `pipe_run` (detached, checkpoint). KHÔNG giữ tty/SSH chờ.
3. **Chuỗi nhiều bước có chờ-đợi** → viết/sửa pipeline JSON (`pipelines/`), KHÔNG để LLM ngồi poll.
   Điểm cần quyết định → step `llm_gate` (máy dừng, ghi NEED_LLM.json, chờ answer).
4. **Sau khi sửa mcp_tools-v3.py** → `ce --sync bg_selftest` phải PASS 6/6 rồi mới dùng.
5. **Vào phiên mới, muốn biết gì đang chạy**: `ce pipe_list` + `ce bg_list` + `ce wfo_status` —
   KHÔNG ssh mò log tay khi nút trả lời được.

## Nút hiện có (tầng nguyên tử — mcp_tools-v3.py trên Oracle, gọi qua ce.cmd)
- `bg_run/bg_status/bg_report/bg_stop/bg_cleanup/bg_list/bg_selftest` — vòng đời job nền (selftest-verified).
- `wfo_run <ds> [jar n seed workers tag]` / `wfo_status` / `wfo_report [tag]` / `wfo_stop` — WFO trọn gói.
- `sys_health` / `sys_zombies [kill=true]` / `sys_logtail <file> [n]` — sức khoẻ/vận hành.
- `pipe_run <file.json> [K=V…]` / `pipe_status` / `pipe_resume <id>` / `pipe_stop` / `pipe_list` — pipeline engine.
- `kaggle_slots` / `kaggle_push <dir>` / `kaggle_status <ref>` / `kaggle_output <ref> [dir]` / `kaggle_parse_logs <log>` — Kaggle fleet (qua venv `CE_KAGGLE_BIN`).
- `profile_list` — liệt kê execution profile (L4) + `verified` (xem mục Profiles).
- Đợt 2 (chưa build — cần thì đề xuất Uni duyệt): `data_*` (copy226/backfill/validate), `wfo_ab`, `deploy_verify`.

## Pipeline JSON — schema tối giản
`steps[]`, mỗi step: `id`, `type: tool|shell|wait|llm_gate`, `on_fail: abort|continue`, `retry`.
- `tool`: gọi nút nội bộ, `args` dict (hỗ trợ `${param}`).
- `wait`: poll `tool` tới khi `until.conditions[{path,equals|gte|lt…}]` — máy tự chờ, 0 token.
- `llm_gate`: dừng sạch, ghi `pipe_<id>_NEED_LLM.json` (question + context_files);
  trả lời = ghi `pipe_<id>_LLM_ANSWER.json {"answer": "..."}` rồi `pipe_resume <id>`.
- Checkpoint từng step ở `CE_RUN_DIR/pipe_<id>_state.json` → crash thì `pipe_resume`, không làm lại.
- **Profile (L4):** thêm field `"profile":"<tên>"` (hoặc list) → engine nạp
  `CE_PROFILES_DIR/<tên>.json` merge params hạ tầng. Ưu tiên: **CLI `K=V` > pipeline params >
  profile params**. Pipeline nghiệp vụ KHÔNG lặp lại `JAR/HOST/XMX/dataset…`.

## Profiles (L4 — cách chạy CỐ ĐỊNH theo môi trường × công nghệ)
> Kiến trúc 5 tầng: **L1 infra → L2 transport → L3 nút nguyên tử → L4 profiles → L5 pipeline nghiệp vụ.**
> **LUẬT: job mới CHỈ viết + test L5 (pipeline JSON); L4 đã `verified` thì KHÔNG test lại — chỉ tái dùng.**
> Chỉ khi hạ tầng đổi mới sửa + verify lại profile rồi cập nhật `verified: YYYY-MM-DD`.

- File ở `orchestrator/profiles/*.json`, schema `{name, description, verified, params{…}}`.
  `verified: null` = chưa có job thật chạy qua CE (chờ job đầu chốt).
- `ce profile_list` — liệt kê profile + `verified` + key params. `pipe_status` in profile đã dùng.
- 4 profile chuẩn: **java-oracle** (WFO Oracle, verified 2026-07-16) · **java-226** (chạy LAN
  trên 226, merge/copy data, 2026-07-14) · **java-kaggle** (Java qua Kaggle kernel, 2026-07-14;
  đổi jar/config = bump version dataset, đổi data = bump ff dataset) · **python-kaggle** (Python
  thuần qua Kaggle, *chưa verified*).
- Dùng: pipeline chỉ cần `"profile":"java-oracle"` + params nghiệp vụ (DS/tag/N) → `JAR/XMX/STATE_*`
  tự đến từ profile đã verified.

## Đường dẫn chuẩn
- Source of truth: `orchestrator/mcp_tools-v3.py` + `orchestrator/pipelines/` (repo) → deploy bằng `ce --sync`.
- Trên VPS: tool `/home/ubuntu/claudedata/.run/mcp_tools-v3.py`; env `CE_RUN_DIR=/home/ubuntu/claudedata/.run/mcp_ce`,
  `CE_PIPES_DIR=/home/ubuntu/claudedata/.run/pipelines`, `CE_PROFILES_DIR=/home/ubuntu/claudedata/.run/profiles`.
- Chi tiết kiến trúc + bảng nút đầy đủ: `orchestrator/cognitive-execution-framework-v3.md`.

## Uni prompt thế nào (cheat-sheet)
- Việc lặp đã có pipeline: "chạy ab_objective cho maxfav3" → LLM chỉ `pipe_run` (1 chạm).
- Việc mới nhiều bước: "làm X rồi Y rồi so Z" → LLM viết 1 pipeline JSON (1 lần) → chạy → từ đó thành nút bấm.
- Check tình hình: "đang chạy gì" → `pipe_list`/`wfo_status`, trả lời từ JSON.
- Cần quyết định giữa chừng: pipeline tự dừng ở gate — LLM/Uni đọc NEED_LLM + context rồi trả lời, KHÔNG canh.
