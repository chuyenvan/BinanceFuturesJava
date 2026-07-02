# TASK-115: Lưu report leaked run + GATE-112 trên Oracle (tuần tự, KHÔNG đảo)

- **status:** doing (master = Claude chat; phần A orchestrator detached trên Oracle)
- **depends_on:** leaked run w2 xong (pgrep WfoWorker rỗng) · phần C thêm TASK-114 (jar mới)
- **resource:** Oracle · **touches_live_process:** không

## ⛔ Thứ tự CỨNG
GATE-112 reset jobstore `strategy_window` 4-window → **PHÁ kết quả leaked 17-window**. Bắt buộc A → B → C.

## A. Orchestrator chờ + lưu leaked report (script `~/claudedata/task115_orchestrator.sh`, detached, poll 20s)
1. `while pgrep -f WfoWorker; do sleep 20; done`
2. `java -cp binance-futures-wfo-lf.jar WfoCoordinator report strategy_window`
3. Copy report coordinator → **`~/claudedata/wfo_leaked_v1_report.md`** (KHÔNG reset gì).
4. Marker **`~/claudedata/task115_A_DONE`** + log **`~/claudedata/task115_orchestrator.log`**.

## B. So sánh cặp V4 (master, sau A)
- scp report leaked về repo → **`docs/reports/wfo_leaked_funding_v1_report.md`**
- Viết bảng so leaked-vs-leakfree (verdict 3 tiêu chí + per-window) → **`docs/reports/wfo_pair_v4_compare.md`**. Tính chất: THAM KHẢO (V4 che số LOW_TRADES).

## C. GATE-112 (sau A + 114; theo spec trong tasks/112 mục GATE)
1. Determinism: jar CŨ `wfo-lf`, reset `WFO_MAX_WINDOWS=4 WFO_N_SAMPLES=3`, env cũ → 4 dòng [WIN] khớp baseline 15:12. Lệch → DỪNG báo Uni.
2. Deploy `binance-futures-task112.jar` (md5 verify) + `config.properties` Oracle thêm `TICKER_SOURCE=aerospike AEROSPIKE_READ_CLUSTER=226`, env mới chỉ `WFO_SMART_CACHE=1 WFO_DATA_DIR=...` → 4 dòng [WIN] khớp 100%.
3. Log → **`~/claudedata/gate112_old.log` / `gate112_new.log`**; 8 dòng [WIN] + verdict GATE ghi vào tasks/112 Kết quả.

## Kết quả
<master điền>
