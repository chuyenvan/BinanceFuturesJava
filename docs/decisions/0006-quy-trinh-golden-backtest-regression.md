# ADR-0006: Quy trình golden backtest regression (chống drift khi thay đổi)

- **Ngày:** 2026-06-09
- **Trạng thái:** đã chấp nhận
- **Bối cảnh phát sinh:** mỗi thay đổi data ticker/funding, code core, hoặc config/param đều ảnh hưởng `SimulatorMarketLevelTicker1MStopLoss`. Đã từng mất kiểm soát: drift slippage 0.0005↔0.003, không tái lập (xem TRACE_backtest_drift).

## Vấn đề
Làm sao mỗi thay đổi đều được chạy lại + so kết quả với trước, để (a) bắt regression âm thầm khi refactor, (b) định lượng tác động khi đổi có chủ đích — mà không phải nhớ bằng đầu.

## Tiền đề bắt buộc
Sim phải **deterministic**: cùng commit + cùng config + cùng data → fingerprint GIỐNG HỆT. Verify trước (chạy 2 lần). Nếu lệch (HashMap order / parallel / tz) → diệt nguồn non-determinism TRƯỚC, nếu không cả quy trình vô nghĩa.

## Quyết định
Thiết lập **golden backtest** 2 tầng, chạy qua `BacktestIntegrityGuard`, xuất "fingerprint" và so baseline:

- **FAST** = **thư viện range theo regime** (KHÔNG phải 1 window cố định), mỗi range có baseline riêng, khóa lại sau khi chốt (đổi range = mất mốc so). 3 range:
  - **Crash (~2022):** vùng LUNA/FTT/sập sâu — quan trọng nhất cho survivorship/coin chết.
  - **Bull (~2023-2024):** vùng tăng mạnh.
  - **Recent (20251001→20260430):** gần đây, có cả PF cao lẫn maxDD ~−29%.
  Mốc Crash/Bull xác định bằng SỐ (quý maxDD sâu nhất / return cao nhất), không cảm tính — xem TASK-003.1.
  ⚠️ Fast chỉ là *regression guard*, KHÔNG kết luận chiến lược.
- **FULL** = `2021 → 2026` (~12'). Chạy trước thay đổi core/param và các mốc lớn (deploy cadence). Đây là đánh giá thật, gắn Cổng gác 2 của PIPELINE.

### Fingerprint = STAMP + METRICS
- STAMP: `commit`, `CONFIG_VERSION`, version set Aerospike (market + funding), `SLIPPAGE_RATE / RATE_FEE / APPLY_SLIPPAGE / BLOCK_INTRABAR_LOOKAHEAD / FILTER_MODE`.
- METRICS (theo thứ tự ưu tiên review): PnL (FULL: theo từng năm + tổng; FAST: PnL đoạn) → maxDD (`unProfitMin`) → `numTrades` → số cụm găm > 30 ngày → (rủi ro đuôi) `worstSingleLoss`, `nearLiq`.

### Quy tắc phán quyết (mấu chốt — phân biệt bằng STAMP)
- STAMP-input **không đổi** mà metric đổi → **REGRESSION (đỏ)**. `numTrades` và số-cụm-găm khớp tuyệt đối; PnL/maxDD khớp trong epsilon float. → điều tra ngay.
- STAMP-input **đổi có chủ đích** → không đỏ; in **diff report**, review theo thứ tự ưu tiên, rồi **duyệt baseline mới** + ghi lý do (ADR/changelog). Baseline KHÔNG được tự trôi.

### Quy tắc chọn range khi chạy fast
- Thay đổi data ở vùng X → chạy range phủ X (vd backfill coin chết → **Crash** + full).
- Refactor code core (ảnh hưởng mọi vùng) → chạy TẤT CẢ range hoặc full.
- **Không chắc thay đổi ảnh hưởng vùng nào → chạy full.** Fast nhiều-range là tối ưu tốc độ cho trường hợp *chắc chắn cục bộ*, không thay full.

### Quy tắc theo 3 loại thay đổi
- **Data ticker/funding** (đổi set Aerospike / gen lại predict): bump `CONFIG_VERSION` (ADR-0004) → baseline mới có chủ đích. Nếu thay đổi nằm ngoài cửa sổ fast → bắt buộc FULL.
- **Code core**: refactor kỳ vọng vô hại → FAST phải KHỚP baseline; fix logic có chủ đích → FULL + diff + ADR giải thích.
- **Config/param** (HPO mới): chạy lại + diff; bump version nếu đụng model/predict.

## LÝ DO
Mất kiểm soát xảy ra khi thay đổi tưởng vô hại làm kết quả đổi âm thầm, hoặc khi không phân biệt được "đổi do code" với "đổi do data/param". Tách bằng STAMP + baseline cố định trong repo biến việc này thành pass/fail tự động thay vì trí nhớ.

## Hệ quả
- Cần một tool `GoldenBacktest` (xem TASK-003).
- Baseline fingerprint **commit vào repo** (để mọi commit/máy so được), không để trong outputs/ bị gitignore.
- Củng cố kỷ luật reproducibility của TRACE: commit sạch trước khi chạy chính thức; fingerprint stamp commit + version.
