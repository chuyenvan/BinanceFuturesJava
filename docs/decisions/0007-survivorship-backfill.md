# ADR-0007: Survivorship bias nặng — backtest thiếu 39 coin đã delist, phải backfill

- **Ngày:** 2026-06-09
- **Trạng thái:** đã chấp nhận — ⚠️ CẬP NHẬT 2026-06: phần BACKFILL **HOÃN** (phương án C, xem cuối file)
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

## 🔴 BẰNG CHỨNG TRỰC TIẾP — golden CRASH baseline (TRƯỚC backfill, commit `71de547`)
Range CRASH `20220401→20221231` (LUNA/FTT sập sâu nhất lịch sử) cho kết quả **ĐẸP BẤT THƯỜNG**:
- CRASH: PnL **+5507**, maxDD chỉ **−6286**, worstSingleLoss **−110**, numTrades **7064** (~785/tháng).
- RECENT (2025-10→2026-04, để đối chiếu): PnL 6510, maxDD **−19613**, worstLoss −808, numTrades 14154 (~2020/tháng).
→ Crash tệ nhất lịch sử lại lời + maxDD nông hơn + mật độ trade ~39% Recent. Nguyên nhân: **data 2022 thiếu đúng coin sập** (38 coin chết chưa backfill + universe 2022 nhỏ) ⇒ bot né cú sập vì không có data để lỗ.
- ⚠️ `baseline-CRASH.json` (+5507) **KHÔNG phải bằng chứng "bot sống tốt qua crash"** — nó là ảnh THIẾU coin sập. Giá trị duy nhất: làm mốc so SAU backfill (kỳ vọng PnL/maxDD xấu đi rõ, numTrades tăng).
- (chưa xác nhận bằng số) giả thuyết data-mỏng nên kiểm: đếm coin có data Q2-Q4 2022 vs Recent.

## 🔄 CẬP NHẬT (2026-06, sau khảo sát TASK-004) — HOÃN backfill [phương án C]
Khảo sát read-only của TASK-004 lộ 3 điều phá vỡ giả định backfill ban đầu ⇒ phần Quyết định #2/#3 ở trên **HOÃN**, không thực thi bây giờ:
1. **Sim/golden đọc node `242`, KHÔNG phải 226** (`getReadClient`→242 khi không kaggle/hpo; baseline stamp `readCluster=242`). ⇒ giả định "226 = staging an toàn" SAI; backfill để golden thấy phải ghi **242 (node tiền thật)** — rủi ro cao.
2. **Backfill ticker đơn lẻ KHÔNG làm sim trade coin chết.** Entry rank theo PREDICTION (`ai_pred_market_full_basket_v2` + funding pred), không theo ticker (B3). Coin chết thiếu prediction 2022 ⇒ không vào top ⇒ ΔPnL=0. Muốn đo phải GEN lại prediction (market+funding) cho 38 coin suốt 2022 = inference lịch sử nặng (trần ADR-0005).
3. **Funding fee đang TẮT** (`updateFundingFee` comment) ⇒ ingest funding rate vô nghĩa với PnL sim.

**Quyết định (C):** HOÃN backfill. Survivorship đã được định lượng GIÁN TIẾP đủ mạnh (baseline CRASH +5507 = crash lãi giả). Survivorship chỉ làm backtest LẠC QUAN THÊM ⇒ kết luận "hệ lỗ qua chu kỳ" không bị lật; ưu tiên thật là ruin/breaker (ROADMAP bước 3).

**Điều kiện làm backfill đầy đủ [phương án B] về sau:** khi đã sửa được ruin và CẦN xác nhận PnL dương là THẬT (không do thiếu coin chết). Lúc đó làm trọn gói: tải ticker 38 coin + GEN market+funding prediction 2022 + bật `updateFundingFee` + ghi **242** (cẩn trọng node tiền thật) → chạy lại golden CRASH so `baseline-FAST_CRASH` → diff = survivorship.

TASK-004 đóng (khảo sát xong, không ingest); TASK-005 KHÔNG mở.
