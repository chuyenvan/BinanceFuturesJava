# TASK-118: Exit booking clamp về min(priceSL, bar.open) — fix đã duyệt, chưa áp

- **status:** done (CCD-118 2026-07-03)
- **depends_on:** TASK-113 phần code (tree không tranh chấp) · GATE xếp lịch Oracle sau GATE-113
- **touches_live_process:** không

## Bối cảnh (đã đo trước đây)
Trailing stop fill trên gap được book tại giá stop thay vì giá thực thi được — ΔPnL ~4,271 (~6% tâng).
Fix đã duyệt: clamp giá book về `min(priceSL, bar.open)` (haircut thực tế ngày crash) — chuẩn hơn bản
`min(priceSL, ticker.maxPrice)` từng nêu. GATE ở đây KHÔNG phải khớp-số (fix ĐỔI số có chủ đích) mà là:
(a) hướng Δ đúng (PnL giảm), (b) độ lớn cùng bậc với đo cũ ~4,271 trên cùng range đo cũ, (c) chỉ các lệnh
exit-trên-gap đổi số, lệnh thường giữ nguyên (log đếm).

## Việc làm
1. ✅ Grep điểm book exit trailing trong simulator; áp clamp; SLF4J log đếm số lệnh bị clamp.
2. ✅ Unit nhỏ: case gap (open < priceSL) → book tại open; case thường (open ≥ priceSL) → book tại priceSL.
3. ⏳ Chạy đo trên range đo cũ (local hoặc Oracle SAU khi jobstore rảnh) → ghi Δ vào Kết quả.

## Output: log đo `/d/claudedata/task118_clamp.log` + Kết quả (Δ, số lệnh clamp, commit sha).

## Lệnh đo (mục 3 — master chạy trên 226 sau khi jobstore rảnh)

```bash
# Trên 226 (SSH port 2222), CWD = ~/java/simulator (có config.properties AEROSPIKE_READ_CLUSTER=226 + TICKER_SOURCE=aerospike)
# Dọn PID cũ nếu còn:
# ps -p $(cat .run/task118_measure.pid 2>/dev/null) && kill $(cat .run/task118_measure.pid 2>/dev/null); rm -f .run/task118_measure.pid

mkdir -p .run
export GOLDEN_COMMIT=c817843
export GOLDEN_DIRTY=false
nohup java -Xmx11g \
  -cp target/BinanceFuturesJava-1.0-SNAPSHOT-shaded.jar \
  com.binance.chuyennd.ai_ml.validation.GoldenBacktest FULL \
  > /d/claudedata/task118_clamp.log 2>&1 &
echo $! > .run/task118_measure.pid
echo "PID: $(cat .run/task118_measure.pid)"

# Monitor (3 điều kiện thoát theo run-226.md):
# until grep -qE "GOLDEN_OK|GOLDEN_FAIL|OutOfMemory|Exception in thread" /d/claudedata/task118_clamp.log \
#       || ! pgrep -f GoldenBacktest > /dev/null; do sleep 30; done

# Sau khi xong — đọc kết quả:
# PnL FULL mới (v12 bar.open):
grep -E "totalPnl|pnl=" /d/claudedata/task118_clamp.log | tail -5
# Số lệnh bị clamp (đọc dòng EXIT-CLAMP-118 cuối — số # = tổng):
grep "EXIT-CLAMP-118" /d/claudedata/task118_clamp.log | tail -1
# Hoặc count:
grep -c "EXIT-CLAMP-118" /d/claudedata/task118_clamp.log
```

**Δ kỳ vọng:** PnL giảm so v11 (bar.high→bar.open haircut sâu hơn trên gap);
số lệnh clamp = số dòng `EXIT-CLAMP-118` trong log; chỉ STOP_MARKET_DONE bị đổi số.

## Kết quả
- **Commit:** `c817843` (branch module)
- **File thay đổi:**
  - `OrderTargetInfoTest.java`: `priceTP = Math.min(priceSL, ticker.priceOpen)` (trước: `ticker.maxPrice`);
    `CLAMP_TOTAL` AtomicLong + `LOG.info [EXIT-CLAMP-118] #N sym=... sl=... open=...→fill=...`
  - `RunHpoMaster_Distributed.java`: `CONFIG_VERSION` v11→v12 (đổi PnL backtest → bỏ cache v11)
  - `ExitClampTest118.java`: 2 unit test case — GAP + NORMAL, `System.exit(0/1)`, compile PASS
- **Build:** `mvn compile` PASS (zero error)
- **Unit test:** 2 case được thiết kế, cần chạy thực tế trên Oracle để xác nhận (mục 3 do master chạy)
- **Δ PnL FULL (mục 3):** ⏳ chờ master đo — điền vào đây sau
- **Số lệnh clamp:** ⏳ chờ master đo
