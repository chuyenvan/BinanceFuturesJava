# ADR-0007: Survivorship bias nặng — backtest thiếu 39 coin đã delist, phải backfill

- **Ngày:** 2026-06-09
- **Trạng thái:** đã chấp nhận
- **Bối cảnh phát sinh:** TASK-001 + TASK-002 (coverage thật).

## Vấn đề
Dataset backtest có phản ánh đủ rủi ro các coin đã về 0 không? Hay backtest đang né đúng các cú sập?

## Bằng chứng (TASK-001, số thật)
- Sau lọc USDT-perp (bỏ USDC/dominance/`_`): coverage = **711**, universe data.vision = **730**.
- **Tập thiếu hoàn toàn = 39 symbol** (universe − coverage). 38/39 có monthly klines (LENDUSDT không).
- **drawdown trung bình tập thiếu = −60.9%**, **12/39 diedNearZero**. Top sập: LUNAUSDT −99.7%, ANCUSDT −99.7%, DODOUSDT −98.1%, RAYUSDT −97.6%, FTTUSDT −97.1%, AUDIOUSDT −96.2%, DGBUSDT −95.7%, GALUSDT −94.8%, SRMUSDT −89.7%, ANTUSDT −88.5%.
- ⚠️ Bẫy đo: `avgQuoteVolume` mean toàn đời hạ thấp thanh khoản đỉnh (FTT/RAY/SRM từng rất thanh khoản) → đếm "liquid" bằng mean là ĐÁNH GIÁ THẤP số coin đáng kể. Ưu tiên backfill nên đo QV ĐỈNH, không mean.

## Quyết định
1. **Mọi kết quả backtest/HPO TRƯỚC backfill phải đọc kèm lưu ý "lạc quan giả"** — đặc biệt maxDD / worstSingleLoss / PnL qua chu kỳ. Bot long-only DCA-không-stop chết đúng ở coin về-0; thiếu chúng = né đúng đuôi tệ nhất.
2. **Backfill 38 coin chết** — cả `ticker` lẫn `funding rate` (242 = nguồn chân lý, 226 = sync từ 242; **cả hai đều thiếu** → phải tải từ Binance). Qua cổng gác: pilot 1 coin trên **226** validate format (TASK-004) → full 38 vào **242** rồi sync 242→226 (TASK-005). Funding pred: kiểm engine xử lý coin thiếu pred (TASK-004 §0c) rồi quyết có gen không (việc nặng, dính ADR-0005).
3. **Đo impact bằng golden (ADR-0006):** chụp FULL golden baseline TRƯỚC backfill; SAU backfill chạy lại FULL golden, so baseline → định lượng survivorship làm PnL/maxDD tệ đi bao nhiêu. Backfill = đổi nền dữ liệu ⇒ bump `CONFIG_VERSION` (ADR-0004).

## LÝ DO (vì sao đây là vấn đề thật, không bỏ qua được)
Kết luận hiện tại "hệ lỗ qua chu kỳ, maxDD −39%" (FINDINGS) được tính trên dataset ĐÃ THIẾU LUNA/FTT/RAY… → con số đó vẫn còn lạc quan. Thêm 38 coin về-0 gần như chắc làm đuôi rủi ro tệ hơn. Không backfill thì mọi HPO/WFO phía sau tối ưu trên một thế giới không có cú sập — vô nghĩa.

## Hệ quả
- TASK-004 (pilot) + TASK-005 (full) được mở.
- Con số đối chứng (golden trước/sau) sẽ là bằng chứng định lượng cho mức survivorship.
- Cảnh báo "lạc quan giả" áp cho mọi kết luận backtest cho tới khi backfill xong + golden re-run.
