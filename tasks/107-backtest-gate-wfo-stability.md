---
id: 107
status: todo
owner: unassigned
updated: 2026-06-24T06:30
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: true
max_retry: 1
require_review: true
report: docs/reports/107.md
---

# TASK-107: Phân tích ỔN ĐỊNH per-quý của gate WFO + viết report

## Mục tiêu (1 câu)
Đo gate WFO (model train-lại expanding mỗi 3 tháng) có ổn định qua TỪNG quý OOS không —
bằng chuỗi 14 điểm per-quý, KHÔNG kết luận pass/fail (để người quyết).

## ⚠️ QUAN TRỌNG cho headless worker
- CHẠY THẲNG tới hết, KHÔNG "schedule wakeup" / KHÔNG tự dừng chờ đánh thức. `claude -p` là one-shot:
  nếu dừng giữa chừng sẽ KHÔNG có ai resume → task thất bại. Chạy job nền bằng `setsid`, rồi POLL bằng
  vòng lặp `until grep -q ... ; do sleep 60; done` trong CÙNG phiên, tới khi xong mới viết report.
- Backtest TỔNG + so baseline ĐÃ CHẠY XONG (số ở mục dưới). Worker CHỈ cần: chạy 14 backtest per-quý
  + tổng hợp + viết report. KHÔNG chạy lại backtest tổng.

## Bối cảnh + KẾT QUẢ ĐÃ CÓ (không chạy lại)
- Gate WFO file: `~/claudedata/wfo_gate_pred.csv` (1,795,680 dòng, `timestamp,predReturn15M,predRisk4H`,
  range OOS 2023-01→2026-06, 14 fold expanding OOS 3 tháng).
- jar: `~/java/simulator/binance-futures-verify.jar` (có GATE_FILE + BT_START/BT_END + V4 + loadGateFromFile).
- Backtest đọc gate file qua env `GATE_FILE`; giới hạn range qua env `BT_START`/`BT_END` (yyyyMMdd).

**Backtest TỔNG (đã chạy, CÙNG range 2023-01→2026-06):**
| | Gate WFO | Gate cũ (baseline) |
|---|---|---|
| PnL | 40189.84 | 40639.74 |
| maxDD | -19381.67 | -20382.73 |
| numTrades | 36767 | 39470 |
| Calmar | 2.074 | 1.994 |
| held>30d | 24 | 28 |
→ Gate WFO ≈ gate cũ (Calmar nhỉnh +4%, maxDD thấp hơn 5%). Train-lại-theo-quý KHÔNG cải thiện
  đáng kể → model gate đủ ổn định. (Đây là kết luận sơ bộ; per-quý để xác nhận ổn định không che giấu quý lỗ nặng.)
- Gate WFO chỉ cô lập 1 biến = model gate. predRisk4H/selector/funding-fee GIỮ NGUYÊN hiện trạng.
  Đọc kết quả đúng phạm vi "train lại gate có ổn định không".

## Scope
**Trong scope:**
1. Chạy 14 backtest per-quý trên gate WFO — mỗi quý 1 lần với BT_START/BT_END:
   fold0 `BT_START=20230101 BT_END=20230401`, fold1 `20230401..20230701`, ... fold13 `20260401..20260601`.
   Mỗi lần: `GATE_FILE=~/claudedata/wfo_gate_pred.csv BT_START=<s> BT_END=<e> java -Xmx20g -cp
   binance-futures-verify.jar com.binance.chuyennd.ai_ml.validation.GoldenBacktest FULL`.
   Lấy dòng `PnL=... maxDD=... numTrades=...` cuối log mỗi quý.
2. Lập bảng 14 quý: quý | PnL | maxDD | Calmar(=PnL/|maxDD|) | numTrades.
3. Tính chỉ số ổn định: % quý PnL dương, Calmar median/min/max, quý xấu nhất (maxDD sâu nhất, PnL âm nhất).
4. (tùy chọn, nếu nhanh) chạy thêm 14 quý cho gate cũ (GATE_SET mặc định, KHÔNG GATE_FILE) cùng các mốc
   để so per-quý WFO vs cũ. Nếu hết giờ thì bỏ, chỉ cần per-quý của WFO.
5. Ghi `docs/reports/107.md`: bảng tổng (đã có ở trên) + bảng 14 quý + chỉ số ổn định. KHÔNG kết luận pass/fail.

**Ngoài scope (KHÔNG động):**
- KHÔNG chạy lại WFOGateRunner / replay / đụng feature_store.csv.
- KHÔNG wire selector, KHÔNG bật funding fee, KHÔNG sửa lõi PnL/sim/engine.
- KHÔNG tự kết luận pass/fail hay "đem deploy" — chỉ xuất số.

## Acceptance criteria (tự kiểm trước khi báo done)
- [ ] Bảng 14 quý OOS đủ PnL/maxDD/Calmar/numTrades (số thật từ log, không bịa).
- [ ] Chỉ số ổn định: %quý dương, Calmar median/min, quý xấu nhất.
- [ ] Guard look-ahead/slippage BẬT (GoldenBacktest tự log PRE-FLIGHT; nếu tắt → DỪNG).
- [ ] SLF4J, log/output → `~/claudedata`, KHÔNG ổ C.
- [ ] report 107.md có bảng tổng + 14 quý + ổn định, KHÔNG câu pass/fail.
- [ ] Worker chạy THẲNG tới hết trong 1 phiên (không tự dừng chờ wakeup).

## An toàn
- Chạy TRÊN Oracle, đọc Aerospike read-only + đọc gate file. KHÔNG đụng live/242/ingest.
- 14 lần × ~12 phút ≈ 2-3 giờ. Chạy tuần tự nền + poll trong phiên. Mỗi quý ghi log riêng
  `~/claudedata/q107_<start>.log` để không đè nhau.
- Mẫu vòng lặp (gợi ý, worker tự điều chỉnh):
  ```bash
  KEY=/c/Users/pc/.ssh/id_rsa_chuyennd
  Q="20230101:20230401 20230401:20230701 20230701:20231001 20231001:20240101 \
     20240101:20240401 20240401:20240701 20240701:20241001 20241001:20250101 \
     20250101:20250401 20250401:20250701 20250701:20251001 20251001:20260101 \
     20260101:20260401 20260401:20260601"
  for q in $Q; do s=${q%:*}; e=${q#*:}; \
    GATE_FILE=~/claudedata/wfo_gate_pred.csv BT_START=$s BT_END=$e java -Xmx20g \
      -cp ~/java/simulator/binance-futures-verify.jar \
      com.binance.chuyennd.ai_ml.validation.GoldenBacktest FULL > ~/claudedata/q107_$s.log 2>&1; \
    grep -aE "PnL=.*maxDD" ~/claudedata/q107_$s.log | tail -1; done
  ```

## Ước tính
- 14 quý × ~12 phút ≈ 2-3 giờ. KHÔNG replay (gate file sẵn).

---

## (Worker điền) Kết quả
<bảng 14 quý + chỉ số ổn định; commit nào>

## (Worker điền) Phát hiện ngoài scope
<thấy vấn đề nhưng KHÔNG tự sửa — ghi đây>

## (Worker điền) Quyết định phát sinh
<có cần ADR mới không?>
