# CE-BUTTONS — luật vận hành job qua nút & pipeline (chống đốt token vào việc chân tay)

## ⚡ VỆ SINH CACHE & HÌNH DẠNG TURN (đo thực 2026-07-17 — QUAN TRỌNG NHẤT về token)
> Đo 5 turn cùng phiên dài: turn cache-SỐNG = **1%** quota; turn cache-VỠ = **12–26%** (cùng số lần gọi LLM).
> Cơ chế: context phiên được prompt-cache theo PREFIX; **danh sách tool đổi giữa turn (MCP disconnect/reconnect)
> → vỡ cache → mọi inference sau trả GIÁ ĐẦY toàn bộ history (×10–20)**. Session dài chỉ là hệ số;
> cache-vỡ là multiplier. Disconnect thường xảy ra sau KHOẢNG NGHỈ dài giữa 2 tool call (agent/job chạy lâu).

LUẬT (áp cho MỌI phiên CDK/CDC trên repo này):
1. **GOM tool call liền mạch** trong turn — không xen khoảng chờ dài giữa các call.
2. **Dispatch agent / job dài = hành động CUỐI turn.** Kết quả xử lý ở turn SAU, không làm tiếp trong cùng turn.
3. Load tool **1 lần đầu turn** (1 ToolSearch gom đủ danh sách); tránh ToolSearch giữa turn.
4. **Chẻ việc lớn thành nhiều turn ngắn liền mạch** — rẻ hơn 1 turn dài dù tổng số call bằng nhau
   (turn dài nhiều call = nhiều cửa sổ cho disconnect = nhiều lần vỡ).
5. Output tool vào chat ≤10 dòng (grep/head); log lớn → agent đọc (context riêng).
6. Turn đắt bất thường → kiểm marker "tools available again/no longer available" GIỮA turn
   trước khi đổ lỗi nguyên nhân khác.
7. Master-thread ≤3–5 inference/turn cho vận hành; chẩn đoán/sửa >2 bước → agent.
8. CẤM SSH inline quote phức tạp (PowerShell nuốt quote/`$` → retry = inference lãng phí):
   dùng `ce.cmd <nút>` hoặc viết script → scp → chạy.
9. **CACHE CÓ TTL — biến số LỚN NHẤT (đo 8 turn, chốt 2026-07-17):** nghỉ giữa 2 turn vài PHÚT = turn 1%;
   nghỉ ≥2h = turn ~26% (cache chết → inference đầu trả FULL history). Chi phí "quay lại sau nghỉ" =
   kích thước history × 1 lần, KHÔNG tránh được bằng hành vi → chỉ giảm bằng HISTORY NHỎ:
   **session làm việc theo phiên-ngắn + handoff file (NEXT_SESSION) + đổi session sau mỗi đợt nghỉ dài
   khi history đã phình.** Turn đầu sau nghỉ: GỘP tối đa việc vào 1 turn (đã trả full thì tận dụng).
   (Ghi chú thêm: agent NGẮN <5' giữa turn không phá cache; agent DÀI đặt cuối turn.)

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
6. **WFO full-16-window → MẶC ĐỊNH `wfo_fanout`** (6-node = 2 Oracle worker + 5 Kaggle kernel,
   cùng jobstore 226). Master phê 2026-07-16: KHÔNG bỏ phí 5 Kaggle node. `wfo_run` (Oracle-only,
   2-worker) CHỈ dùng debug / verify-1-window. Đảo mặc định: full-window = `wfo_fanout`.

## Nút hiện có (tầng nguyên tử — mcp_tools-v3.py trên Oracle, gọi qua ce.cmd)
- `bg_run/bg_status/bg_report/bg_stop/bg_cleanup/bg_list/bg_selftest` — vòng đời job nền (selftest-verified).
- `wfo_fanout <ds> [jar n seed oracle_workers kaggle_kernels tag extra_env]` — **MẶC ĐỊNH WFO full-16-window**:
  reset jobstore → 2 Oracle worker + push tối đa 5 Kaggle kernel (cùng jobstore 226). `extra_env`
  (`ABLATION_MODE=C,WFO_DISABLE_DCA=1` hoặc JSON) chỉ áp cho Oracle worker; Kaggle dùng env baked.
- `wfo_run <ds> [jar n seed workers tag]` / `wfo_status` / `wfo_report [tag]` / `wfo_stop` — WFO Oracle-only,
  CHỈ debug/verify-1-window (KHÔNG dùng cho full-window — dùng `wfo_fanout`).
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

## Pipeline nghiệp vụ có sẵn (`orchestrator/pipelines/`)
- `ab_objective.json` — A/B 2 baseline (V41 vs V42), profile mặc định cũ (Oracle-only 2-worker).
- `dca_ablation.json` — đo đóng góp DCA: run `dca_off` (extra_env WFO_DISABLE_DCA=1) vs `dca_on`,
  profile **wfo-fanout**, chạy TUẦN TỰ (cùng jobstore). Gate đầu chờ master áp diff Java (xem dưới).
- `edge_dca_hard.json` — đo edge model khi DCA cứng: run A (ABLATION_MODE=A) vs C (placebo),
  cả hai WFO_DISABLE_DCA=1, profile **wfo-fanout**, tuần tự.
- ⚠️ 2 pipeline ablation CHỜ master áp `Configs.WFO_DISABLE_DCA` + guard `DcaProcessor.getDCA`
  (chưa có trong Java) — chi tiết diff ở `docs/insights/dca_off_ablation_plan.md`. Kaggle kernel
  KHÔNG nhận extra_env → muốn fan-out đồng bộ phải bump kernel dataset, hoặc chạy `KAGGLE_KERNELS=0`.

## Profiles (L4 — cách chạy CỐ ĐỊNH theo môi trường × công nghệ)
> Kiến trúc 5 tầng: **L1 infra → L2 transport → L3 nút nguyên tử → L4 profiles → L5 pipeline nghiệp vụ.**
> **LUẬT: job mới CHỈ viết + test L5 (pipeline JSON); L4 đã `verified` thì KHÔNG test lại — chỉ tái dùng.**
> Chỉ khi hạ tầng đổi mới sửa + verify lại profile rồi cập nhật `verified: YYYY-MM-DD`.

- File ở `orchestrator/profiles/*.json`, schema `{name, description, verified, params{…}}`.
  `verified: null` = chưa có job thật chạy qua CE (chờ job đầu chốt).
- `ce profile_list` — liệt kê profile + `verified` + key params. `pipe_status` in profile đã dùng.
- 5 profile chuẩn: **java-oracle** (WFO Oracle, verified 2026-07-16) · **java-226** (chạy LAN
  trên 226, merge/copy data, 2026-07-14) · **java-kaggle** (Java qua Kaggle kernel, 2026-07-14;
  đổi jar/config = bump version dataset, đổi data = bump ff dataset) · **python-kaggle** (Python
  thuần qua Kaggle, *chưa verified*) · **wfo-fanout** (MẶC ĐỊNH WFO full-window: merge java-oracle
  + java-kaggle, 6-node cùng jobstore 226; *verified null* — chờ run đầu sau retry-fix).
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


## 🔒 2 QUY TẮC VẬN HÀNH BẮT BUỘC (Uni chốt 2026-07-17) — đọc mỗi session

### R1. CE-FIRST (config động → viết nút, đừng chạy cơm lặp lại)
- Việc **config-động-hóa được HOẶC sẽ chạy ≥2 lần** → PHẢI thành nút/pipeline CE (mcp_tools/pipelines).
  Thiếu nút/param (vd `wfo_run` thiếu `extra_env`, `TIME_STOP_HOURS` chỉ đọc properties) → **bổ sung** rồi
  dùng, KHÔNG lách bằng SSH tay.
- Chỉ **one-off đặc thù thật** (chạy đúng 1 lần, không lặp) mới bằng cơm — NHƯNG vẫn **track script vào repo**
  (vd `orchestrator/tools/*.py`) để reproduce, không gõ ad-hoc rồi mất.
- **Guardrail:** đừng để việc dựng nút CHẶN phép đo đang cần. Gấp → chạy tay xong → productize ngay sau.
  Không block science để xây infra; nhưng xong là phải wrap lại.

### R2. HANDOFF-LUÔN (history nhỏ = rẻ; đừng bê cả mớ context)
- Sau **mỗi milestone** (chốt số / đổi hướng / job dài dispatch) → cập nhật `NEXT_SESSION_TODO_*.md`
  = single-source-of-truth: **đang ở đâu / đang chạy gì (pipe_id, cách resume) / bước kế / rủi ro treo**.
- Handoff phải **live + concise + TRIM** (xoá mục đã xong). Handoff cũ/phình còn hại hơn không có.
  Chi tiết đo → docs/insights (không nhét vào handoff). Handoff chỉ trỏ.
- Mục tiêu: turn/session sau chỉ cần đọc handoff + ce-buttons là đủ ngữ cảnh — KHÔNG kéo full history
  (đo thực: cache-vỡ = ×10-20 token; history nhỏ là đòn bẩy rẻ nhất).
- Turn dài nhiều bước → chốt bằng cập nhật handoff TRƯỚC khi nghỉ.
