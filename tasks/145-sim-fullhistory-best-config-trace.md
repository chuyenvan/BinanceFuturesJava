---
id: 145
status: CANCELLED
depends_on: []
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: false
max_retry: 1
report: docs/reports/145.md
require_review: true
---

# TASK-145: Chạy Simulator full-history + TraceData2Test với CẤU HÌNH TỐT NHẤT hiện tại

## Mục tiêu (1 câu)
Chạy `SimulatorMarketLevelTicker1MStopLoss` full-history (2021-01-01 → nay) với cấu hình tốt nhất hiện
tại, xuất `storage/OrderTestDone.data`, rồi chạy `TraceData2Test` ra báo cáo PnL đầy đủ.

## CẤU HÌNH TỐT NHẤT hiện tại (chốt 2026-07-11 — dùng ĐÚNG, không tự đổi)
- Dataset: `WFO_DATA_DIR=/home/ubuntu/claudedata/wfo_dataset_v4` (funding = ret2 leak-free).
- `TS_GIVEBACK_RATIO=1.0` (nuôi lãi — mảnh dương rõ nhất, "càng giữ càng tốt").
- `NUMBER_ORDER_BUDGET=50` (baseline; sizing đã chứng minh không phải đòn bẩy nên giữ mặc định).
- `DISABLE_PREDICT_SYMBOL=false` (BẬT PST — edge chính; tắt đi thì hệ về ~0, đã đo §2).
- `TIME_STOP_HOURS=0`, `HARD_STOP_LOSS_RATE=0` (đã đo: exit-rule net âm, giữ tắt).
- `WRITE_SIM_STORAGE=true` (BẮT BUỘC — để TraceData2Test đọc được).

## Scope
**Trong scope:**
1. Verify jar hiện tại trên Oracle CÓ các biến trên (grep help hoặc chạy thử). Nếu jar cũ thiếu biến →
   BÁO NGAY, KHÔNG tự build (build là việc của Desktop).
2. `pgrep -af 'SimulatorMarketLevel|WfoWorker|TraceData2Test'` phải RỖNG trước khi chạy (không đụng job khác).
3. Cp `config.properties.bak2` → `config.properties`, thêm 6 dòng cấu hình trên.
4. Chạy Simulator với `WFO_DATA_DIR=.../wfo_dataset_v4` và `SIM_END_DATE=20260601` (guard ticker-lag;
   "tới nay" = tới mốc data tốt nhất đã biết, KHÔNG để fail-fast vì ticker live thiếu vài ngày gần nhất).
   **KIỂM KĨ full-range:** log phải bắt đầu từ 2021-01-01 (dòng "BẮT ĐẦU SIMULATE TỪ 20210101...") và
   chạy tới ~2026-05. Nếu bắt đầu muộn hơn 2021 → BÁO (thiếu data, không giấu).
5. Xác nhận `storage/OrderTestDone.data` được ghi (ls -la, size > 0).
6. Chạy `com.binance.chuyennd.bigchange.test.TraceData2Test` → báo cáo PnL theo năm/level.
7. Trả `config.properties` về `config.properties.bak2` sau khi xong.

**Ngoài scope:**
- KHÔNG build/redeploy jar. KHÔNG đổi cấu hình khác cấu hình chốt trên.
- KHÔNG đụng 242. KHÔNG sweep thêm tham số.

## HÀNG RÀO (bài học đắt)
- `setsid nohup ... </dev/null >log 2>&1 &` — job dài, không chết theo SSH.
- KHÔNG ghi đè jar khi có job Java chạy (pgrep rỗng trước).
- Foreground tool-call cap 4 phút → detach + poll bằng `until <check>; do sleep 20; done`.
- Log/output → `/home/ubuntu/claudedata` (không ghi C: local).
- python stdout block-buffered nếu có script phụ → `python -u`; kiểm OOM/exit.

## Acceptance criteria (tự kiểm trước khi done)
- [ ] Log Simulator xác nhận range 2021-01-01 → ~2026-05 (in đủ mốc bắt đầu + kết thúc).
- [ ] `storage/OrderTestDone.data` tồn tại, size > 0.
- [ ] TraceData2Test in được PnL theo năm + theo level (DCA_LEVEL1, PREDICT_SYMBOL_TRADE, BIG_DOWN).
- [ ] Ghi balance đầu (35000) → cuối vào report 145.md + CAGR + PnL từng level.
- [ ] config.properties đã trả về bak2.
- [ ] Nếu bất kỳ bước nào lệch (range ngắn, storage rỗng, jar thiếu biến) → ghi rõ, KHÔNG che.

## Lệnh mẫu (worker tham khảo, tự điều chỉnh path)
```bash
cd /home/ubuntu/java/simulator
pgrep -af 'SimulatorMarketLevel|WfoWorker|TraceData2Test' | grep -v grep && exit 1
cp /home/ubuntu/claudedata/config.properties.bak2 config.properties
cat >> config.properties <<CFG
TS_GIVEBACK_RATIO=1.0
NUMBER_ORDER_BUDGET=50
DISABLE_PREDICT_SYMBOL=false
TIME_STOP_HOURS=0
HARD_STOP_LOSS_RATE=0
WRITE_SIM_STORAGE=true
CFG
WFO_DATA_DIR=/home/ubuntu/claudedata/wfo_dataset_v4 SIM_END_DATE=20260601 \
  java -Xmx8g -cp binance-futures-backfill.jar \
  com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss \
  > /home/ubuntu/claudedata/task145_sim.log 2>&1
# verify range + storage
grep 'BẮT ĐẦU SIMULATE' /home/ubuntu/claudedata/task145_sim.log
ls -la storage/OrderTestDone.data
java -cp binance-futures-backfill.jar com.binance.chuyennd.bigchange.test.TraceData2Test \
  > /home/ubuntu/claudedata/task145_trace.log 2>&1
cp /home/ubuntu/claudedata/config.properties.bak2 config.properties
```

---
## (Code điền) Kết quả
## (Code điền) Phát hiện ngoài scope
## (Code điền) Quyết định phát sinh
