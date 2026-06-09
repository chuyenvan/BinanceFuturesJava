# ADR-0002: Cổng liêm chính backtest & cơ chế bịt look-ahead nội-nến

- **Ngày:** 2026-06-09
- **Trạng thái:** đã chấp nhận
- **Bối cảnh phát sinh:** chống "ảo giác look-ahead" trong backtest futures DCA. ADR này chốt VỊ TRÍ THẬT của guard (xác minh từ code, KHÔNG tin mô tả cũ trong roadmap).

## Vấn đề

Backtest dễ vô tình đo lợi nhuận trong điều kiện ăn gian: (a) khớp lệnh nội-nến biết trước đỉnh/đáy (look-ahead), (b) slippage/fee = 0. Cần một cổng chặn cứng + cơ chế cấm khớp nội-nến.

## Các lựa chọn đã cân nhắc

1. **Tin mỗi engine tự gọi assert** — nhược: dễ quên ở 1 engine → lọt.
2. **Đặt guard ở NÚT CHẶN DUY NHẤT mà mọi engine đều đi qua** — ưu: không engine nào bypass được; nhược: phải xác định đúng nút đó.

## Quyết định

Chọn (2).

**Vị trí THẬT của guard (đã xác minh):** `BacktestIntegrityGuard.assertProductionGrade()` được gọi ở đầu `SimulatorMarketLevelTicker1MStopLoss.simulatorWithInitEntry(...)` tại `src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java:74`.
> ⚠️ Mọi engine (HPO master, WFO, các BackTestEngine*, chạy `main()` trực tiếp) đều đi qua hàm này, nên đây là choke-point duy nhất. **Roadmap (`docs/ROADMAP.md` Bước 0) ghi guard "cắm trong `BackTestEngineMaster.run`" — KHÔNG khớp code; vị trí đúng là `simulatorWithInitEntry:74`.**

**Guard kiểm gì** (`src/main/java/com/binance/chuyennd/ai_ml/hpo/BacktestIntegrityGuard.java:31-58`): ném `IllegalStateException` nếu BẤT KỲ điều sau sai —
- `!Configs.BLOCK_INTRABAR_LOOKAHEAD` (đang cho look-ahead nội-nến)
- `!Configs.APPLY_SLIPPAGE`
- `APPLY_SLIPPAGE && SLIPPAGE_RATE <= 0`
- `RATE_FEE <= 0`
Chỉ nới khi CỐ Ý đối chứng: `assertProductionGrade(true)` → chỉ log cảnh báo, không ném.

**Cơ chế bịt khớp nội-nến** (`OrderTargetInfoTest.updateStatusNew`, `src/main/java/com/binance/chuyennd/research/OrderTargetInfoTest.java:138-176`):
- Nhánh `priceSL == null` (vừa ĐẶT SL trong nến này): nếu `BLOCK_INTRABAR_LOOKAHEAD` → `return` ngay (`:148-153`), KHÔNG khớp trong chính nến vừa đặt SL.
- Nhánh `else` (`priceSL != null`, SL đã có từ nến TRƯỚC): nến này mới được khớp khi `minPrice <= priceSL` (`:163`). → đặt SL ở nến N, chỉ cho khớp ở nến ≥ N+1.

## LÝ DO

- Đặt assert ở `simulatorWithInitEntry` thay vì rải ở từng engine: vì đó là điểm DUY NHẤT mọi đường backtest hội tụ → không thể quên/bypass. Đừng "dọn" assert này khỏi đó.
- Cấm khớp ngay trong nến đặt SL: trong 1 nến đã đóng KHÔNG ai biết đỉnh hay đáy đến trước; nếu vừa dùng `maxPrice` để kích SL vừa khớp theo `minPrice` cùng nến = ăn gian biết trước. Vì vậy nhánh `priceSL==null` cố ý `return` — **trông như "bỏ sót xử lý khớp" nhưng là CHỦ Ý**, đừng thêm khớp vào đó.
- Phân biệt với ADR-0001: dùng `bar.low` để ĐO maxDD/MAE (metric) thì KHÔNG vi phạm — vì metric không ra quyết định vào/ra lệnh. Look-ahead chỉ cấm ở đường QUYẾT ĐỊNH (trigger/fill).

## Hệ quả

- Mọi backtest "thật" tự fail-fast nếu cấu hình ảo (look-ahead/slippage=0/fee=0).
- Việc còn nợ (theo roadmap Bước 0): chạy đối chứng guard bật vs tắt để định lượng "ảo giác look-ahead" — `<CẦN XÁC NHẬN: đã chạy đối chứng này chưa và kết quả?>`.
- Roadmap nên sửa vị trí guard cho khớp (thuộc quyền chủ repo — chỉ báo, ADR không sửa roadmap).
