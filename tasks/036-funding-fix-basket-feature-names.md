---
id: 036
status: HOLD
depends_on: []
touches_live_process: false
writes_242_data: false
resource: local
checkpoint: false
max_retry: 2
report: docs/reports/036.md
require_review: true
---

# TASK-036: Funding F1+F2 — gỡ mâu thuẫn basket export + sửa tên feature lệch cấp

- **status:** TODO. Độc lập hoàn toàn (đọc/sửa code feature funding; KHÔNG đụng 013/gate/live). **Chạy song song được NGAY** với backfill OI.
- **Nền:** ADR-0011 §2.1, §5.3, §6.

## F1 — gỡ mâu thuẫn basket (open item ADR-0011 §6)
Hai đường export funding feature với basket KHÁC nghĩa:
- `fundingv2/ExportFeaturesForPythonTool`: basket = `CoinRankManager.getTopCoin` (top50% thanh khoản).
- `funding/FundingDataCollectionManager`: basket = `HistoryManager.findPotentialLosers` (coin sắp giảm).

VIỆC: đọc kỹ 2 đường → **xác minh đường nào tạo training data THẬT** (file `.bin.gz` / `data_funding_all.csv` đang/đã dùng train). Ghi rõ kết luận (đường thật + basket nghĩa gì) vào report + cập nhật ADR-0011 §6. Đánh dấu/đường chết để không lẫn nữa. **Đây là tiền đề — phải chốt trước khi thêm feature (037) / train (039).**

## F2 — sửa tên feature lệch cấp (ADR-0011 §5.3)
- `fundingRateRaw` thực ra = **basket-avg** (`cachedBasketFundingRaw`) → đổi tên `basketFundingAvg` (export + tên cột + tài liệu).
- `momentum1M`/`momentum15M` thực ra = `rateDownAvg`/`rateDown15MAvg` (market-MDO) → đổi tên đúng cấp **market**, bỏ nhãn "coin".
- ⚠️ **CHỈ đổi TÊN/nhãn, TUYỆT ĐỐI không đổi THỨ TỰ 21 feature** (`convertFeaturesToArray` ↔ inference `FundingOnnxInferenceManager`) — đổi thứ tự = sai dấu inference âm thầm. Ghi bảng mapping cũ→mới.

## An toàn
- Chỉ đọc/sửa code feature funding + tài liệu. KHÔNG train, KHÔNG đụng live/gate/013. SLF4J.

## Validate (require_review)
- Report: (F1) đường export THẬT + basket nghĩa gì; (F2) bảng mapping tên cũ→mới + xác nhận **thứ tự 21 feature KHÔNG đổi** (diff chỉ là tên). javac11 PASS.

## (Code / Kết quả điền)
