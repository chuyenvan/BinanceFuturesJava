# TASK-116: Jar sanitize → version java-run-lc → smoke WfoWorker 1 kernel Kaggle

- **status:** done 2026-07-02 21:16
- **depends_on:** TASK-114 · **resource:** local build + Kaggle · **touches_live_process:** không

## Việc làm
1. Backup `PrivateConfig.java` → thay API/SECRET = `SANITIZED_*` → build → **restore ngay** backup.
2. Verify: `unzip -p jar` grep chuỗi secret-live = **0 match** (log bằng chứng). FAIL → DỪNG, không upload.
3. scp jar → Oracle → `kaggle datasets version` dataset `chuyendinh/java-run-lc` (message = git sha).
4. Smoke 1 kernel `wfo-worker-smoke`: mount java-run-lc + wfo-dataset-wf-leakfree; glob tìm jar/dataset (rule §3b);
   env `WFO_SMART_CACHE=1 WFO_DATA_DIR=<glob> WFO_STATE_HOST=103.157.218.226 WFO_STATE_PORT=3222 WFO_STATE_NS=ticker`
   (jobstore 226 thật — set `wfo_jobs` rỗng → worker idle-exit 0; KHÔNG đụng jobstore Oracle).
   PASS = kernel COMPLETE + log `LOAD offline OK (md5 verified)` + `worker thoat` + exit 0.

## Output bắt buộc
- `/d/claudedata/task116_sanitize_grep.log` · `/d/claudedata/task116_kernel.log` (log kernel parse từ JSON)
- Version dataset + kernel status ghi vào Kết quả.

## Kết quả
- PrivateConfig on-disk sẵn placeholder → jar build TASK-114 đã sạch; verify grep -a SANITIZED trong PrivateConfig.class = 1 (log /d/claudedata/task116_sanitize_grep.log). Không cần vòng swap/restore.
- Jar md5 eaa4d9c38754870a017be027f1d46db4 (local = Oracle khớp) → dataset chuyendinh/java-run-lc version mới (msg: TASK-112 refactor HEAD 26f3a1a) + config thêm AEROSPIKE_READ_CLUSTER=226, TICKER_SOURCE=file. Status: ready.
- Smoke kernel wfo-worker-smoke: COMPLETE, SMOKE_PASS — jobstore 226 thật ns=ticker connect OK, LOAD offline OK market=2804363 pred=2819841 funding=2758365 (md5 verified), idle 3 vòng → exit 0. Log: /d/claudedata/task116_kernel.log.
- Kaggle giờ đủ điều kiện làm WFO worker node khi cần: jar mới + dataset wf + WFO_STATE_HOST trỏ store chung.
