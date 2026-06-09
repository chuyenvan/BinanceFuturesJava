# ADR-0004: Kỷ luật CONFIG_VERSION (bỏ cache HPO khi đổi thứ ngoài genome)

- **Ngày:** 2026-06-09
- **Trạng thái:** đã chấp nhận
- **Bối cảnh phát sinh:** HPO phân tán cache điểm fitness theo key; nếu đổi thứ ảnh hưởng kết quả backtest mà KHÔNG nằm trong genome, cache cũ trả điểm SAI. Nguồn: `src/main/java/com/binance/chuyennd/ai_ml/hpo/master/RunHpoMaster_Distributed.java` + CLAUDE.md (luật 5, 6).

## Vấn đề

HPO master đẩy population vào queue set và đọc điểm từ result set; key kết quả gồm `taskId` (băm genome) NHƯNG set tên gắn `CONFIG_VERSION`. Nếu đổi fee/slippage/logic trailing/model/maxDD-source… (ngoài genome) mà không đổi version → worker đọc lại điểm CŨ tính bằng cấu hình CŨ → toàn bộ run vô nghĩa một cách âm thầm.

## Các lựa chọn đã cân nhắc

1. **Xoá cache thủ công mỗi lần đổi** — nhược: dễ quên, không truy vết được.
2. **Gắn `CONFIG_VERSION` vào tên set; bump khi đổi bất kỳ thứ ngoài genome ảnh hưởng kết quả** — ưu: đổi version = tự động dùng set mới, set cũ bị bỏ; có lịch sử lý do.

## Quyết định

Chọn (2).
- `public static final String CONFIG_VERSION` trong `RunHpoMaster_Distributed.java` — **giá trị hiện tại = `"v8"`** (đã xác minh trong code; block comment lý do từng version ~dòng 38-48).
- `QUEUE_SET = "hpo_queue_" + CONFIG_VERSION`, `RESULT_SET = "hpo_results_" + CONFIG_VERSION` (≈ `:49-50`) → đổi version = queue/result set mới hoàn toàn, cache cũ tự động bị bỏ.
- **Khi nào BẮT BUỘC bump** (CLAUDE.md luật 5): đổi bất kỳ thứ ảnh hưởng kết quả backtest mà KHÔNG nằm genome — `RATE_FEE`, `SLIPPAGE_RATE`, logic trailing (`calRateLossDynamicBuy`), budget divider, circuit breaker, look-ahead guard, **đổi model AI**, số/loại gene, **và các fix đo-lường đổi PnL/fitness**.
- **Đi kèm luật 6:** `taskId` (`buildTaskId`) phải băm ĐỦ mọi gene; thêm gene mà quên đưa vào = trùng key.

**Lịch sử version (theo comment trong code):**
- v4→v5: thêm slippage 2 chân + bịt look-ahead nội-nến.
- v5→v6: bỏ gene `MIN_MOMENTUM_24H` (14→13 gene, đổi layout genome + buildTaskId) — xem [ADR-0003](0003-genome-13-gene.md).
- v6→v7: maxDD đổi nguồn sang `trueUnrealizedMin` per-tick (nuôi `HPOFitnessCalculatorV3`) — xem [ADR-0001](0001-do-luong-exit-maxdd-mae.md).
- v7→v8: kẹp giá chốt trailing-stop `min(priceSL, ticker.maxPrice)` (đổi calTp/PnL mọi genome) — xem [ADR-0001](0001-do-luong-exit-maxdd-mae.md).

## LÝ DO

- Version nằm trong TÊN SET (không chỉ trong key record) để một worker chạy code mới TUYỆT ĐỐI không đọc nhầm điểm của code cũ — kể cả khi genome y hệt. Đây là vì sao đổi 1 hằng "vô hại" như `RATE_FEE` vẫn phải bump: cùng genome nhưng điểm khác.
- Hai fix v7, v8 (maxDD-true, exit-clamp) KHÔNG nằm genome nhưng ĐỔI fitness/PnL của MỌI cá thể → nếu không bump, HPO sẽ trộn điểm cũ (DD hụt, PnL thổi) với điểm mới → landscape rác. Vì vậy bắt buộc v6→v7→v8.
- Một session sau thấy CONFIG_VERSION nhảy nhiều bậc đừng tưởng "ai đó nghịch version" — mỗi bậc là một thay đổi ảnh hưởng kết quả, có lý do trong comment + ADR.

## Hệ quả

- Mỗi lần bump: cache `hpo_results_<cũ>` thành rác (không xoá cũng không sao, chỉ không dùng); **phải chạy lại HPO từ đầu** trên version mới.
- Worker đang chạy version cũ ghi vào set cũ → vô hại với version mới.
- `docs/ROADMAP.md` Bước 0 nhắc "bump CONFIG_VERSION" như việc-còn-lại — thực tế đã vượt tới v8; roadmap nên cập nhật (chỉ báo).
