# TASK-019: Fix funding LIVE — FundingFeeManager không refresh + FundingIngestor flush chậm [ƯU TIÊN]

- **status:** TODO — **ƯU TIÊN (funding live sai → ảnh hưởng feature gate + funding model + trade).** Giao CCD #1.
- **owner:** _(điền khi claim — đồng bộ `docs/AGENTS.md`)_ · **updated:** _(điền)_
- **File:** `research/FundingFeeManager.java` + `websocket/FundingIngestor2AerospikeNew.java`. Production 242/live.

## ⚠️ AN TOÀN
- Live (242). Chỉ THÊM nhánh refresh / sửa nhịp flush; **KHÔNG đổi hành vi backtest** (sim determinism — luật "một bộ não"). SLF4J. Test riêng, KHÔNG tự deploy 242.

## Bối cảnh — một CHUỖI funding-live
`FundingIngestor` flush → Aerospike `funding_data` → `FundingFeeManager` cache → feature/model/trade. Hỏng ở 2 mắt: ingestor ghi chậm (B) + manager không reload (A). Sửa cache mà nguồn ghi chậm vẫn sai → làm CẢ HAI + verify nối chuỗi.

---

## PHẦN A — FundingFeeManager không refresh (isProductionMode dead)
### Bug (đã đọc code, xác nhận)
- `initData()` load TOÀN BỘ funding 1 lần lúc `getInstance()` → cache `symbol2FundingFee` (TreeMap time→rate).
- `isProductionMode` chỉ có `setProductionMode(...)`, **KHÔNG nơi nào ĐỌC** → không nhánh refresh.
- `getNearestFundingFee` dùng `floorEntry` trên cache TĨNH: live chạy lâu → funding mới (ingestor ghi) KHÔNG vào cache; `if (timestamp - entry.getKey() > 24h) return 0.0f` → **sau 24h funding trả 0** (mất hẳn).
- ⇒ feature funding (basketFundingAvg/Avg24H/Trend, B7) + funding classifier + trade live dùng funding cũ → 0. History train đúng → **train/serve mismatch**.

### Yêu cầu A
1. **Đọc `isProductionMode`** (hết dead). Khi `true` → refresh cache funding định kỳ.
   - **Đề xuất:** `setProductionMode(true)` khởi `ScheduledExecutorService` reload funding từ `funding_data` mỗi **N phút** (N ≤ chu kỳ funding; đề xuất 30–60′). Incremental nếu được (chỉ funding sau `lastLoadedTs`) để tránh `getAllFundingMap` nặng; nếu khó → reload per-symbol đang dùng. Atomic-swap per symbol (thread-safe).
   - **Hoặc lazy:** trong `getNearestFundingFee`, nếu production VÀ `floorEntry` quá cũ (> chu kỳ funding) → reload riêng symbol đó.
   - Chốt 1 cách + ghi lý do.
2. **Grep `setProductionMode(true)`** — đảm bảo luồng live THỰC SỰ gọi (đúng thứ tự, trước khi dùng funding). Nếu chưa → sửa. (Không set true thì nhánh refresh vẫn chết.)
3. **Backtest:** `isProductionMode=false` → KHÔNG schedule, load 1 lần như cũ; xác nhận sim cho kết quả y hệt (determinism).

---

## PHẦN B — FundingIngestor flush chậm (log ~1h thay vì 1 phút)
### Triệu chứng (log 2026-06-13 23:13→23:22)
- 9 phút KHÔNG có dòng nào từ `FundingIngestor2AerospikeNew` (trong khi Rest-Kline-Loop mỗi phút, OI-Forward mỗi ~5′). `startFlushLoop` đáng lẽ 60s/lần.

### Yêu cầu B
1. **Phân biệt bug-thật vs log-thưa TRƯỚC khi sửa:** đọc `funding_data` (Aerospike) vài symbol → `ts` mới nhất cách `now` bao lâu.
   - Cách `~vài phút` → flush vẫn ghi đúng, chỉ **log thưa** → sửa log cho phản ánh đúng, **KHÔNG động loop**.
   - Cách `~1h` → ghi chậm THẬT → tìm nguyên nhân: sleep sai đơn vị (phút↔giờ / `60*60*1000`), flush dùng chung thread với polling bị kéo dài, hay exception nuốt làm loop hụt nhịp. Đưa flush về đúng 60s.
2. KHÔNG đổi logic ghi `writeFundingMap` (guard chống mất lịch sử) — chỉ sửa NHỊP/log.

---

## Verify CHUỖI (sau A+B)
- `funding_data` cập nhật đúng nhịp (ts mới nhất gần `now`).
- `FundingFeeManager.getNearestFundingFee` ở production trả funding MỚI (không cũ/0) cho symbol vừa có funding.
- Backtest KHÔNG đổi.

## Deploy (gộp — KHÔNG tự chạy)
- Gộp **gỡ-`startHistoryCrawl`** (log xác nhận vẫn chạy 242 = jar 106baee) + **016** + **019** vào MỘT jar → restart 242 một lần (tránh nhiều lần gián đoạn ingest). Backup jar cũ + rollback. User duyệt thời điểm.

## Acceptance
- [ ] A: `isProductionMode` được đọc; production refresh; `setProductionMode(true)` gọi đúng; backtest determinism.
- [ ] B: xác định bug-thật/log-thưa bằng `funding_data` ts; sửa đúng (nhịp hoặc log), không đổi logic ghi.
- [ ] Verify chuỗi: funding live mới, không cũ/0.

## (Code điền)
- **A cách refresh + setProductionMode usage:** …
- **B funding_data ts trước/sau + nguyên nhân + sửa gì:** …
- **Verify chuỗi + backtest determinism:** …
