# ADR-0007: Survivorship bias là MATERIAL — phải backfill coin chết trước khi tin backtest

- **Ngày:** 2026-06-09
- **Trạng thái:** đã chấp nhận
- **Bối cảnh phát sinh:** TASK-001 (survivorship bậc-0) + TASK-002 (coverage map ticker1m). Đo bằng số, không suy đoán.

## Vấn đề

Dataset backtest (ticker1m Aerospike) THIẾU HOÀN TOÀN **39 symbol USDT-perp** từng tồn tại — gồm các coin sập-về-0 lịch sử (LUNA, FTT, RAY, SRM, WAVES, DODO, AUDIO, ANC…). Bot là **long-only, DCA-nhồi-loser, KHÔNG hard-SL**. Nếu các coin này có trong dataset, bot sẽ nhồi suốt đường về 0 = lỗ thảm. Backtest hiện KHÔNG có chúng ⇒ giấu đúng rủi ro ĐUÔI nặng nhất. Phải quyết: bỏ qua hay backfill?

## Các lựa chọn đã cân nhắc

1. **Bỏ qua (giữ dataset hiện tại)** — ưu: không tốn công; nhược: PnL/DD/HPO/WFO đang LẠC QUAN GIẢ vì thiếu các thảm họa, phán quyết "edge" không đáng tin.
2. **Backfill coin chết + chạy đối chứng** — ưu: backtest phản ánh rủi ro thật; nhược: tốn công ingest + phải chạy lại HPO trên dataset mới.

## Quyết định

Chọn (2): backfill 38 coin chết (có klines) vào Aerospike ticker, rồi chạy backtest **đối chứng (có/không các coin này)** để định lượng ΔPnL/ΔDD, **TRƯỚC** khi tin kết quả backtest/HPO. Triển khai ở **TASK-004**.

## LÝ DO (số liệu — vì sao MATERIAL với CHÍNH chiến lược này)

- Tập thiếu = 39/730 universe USDT-perp (≈5.3%) — nhưng **không phải mẫu ngẫu nhiên: toàn coin CHẾT**. 38 có klines, **12 died-near-zero**, drawdown TB **−60.9%**.
- LUNAUSDT: drawdown **−99.7%**, avgQV(toàn đời) **609k**, sống 470 ngày — đúng kiểu coin bot vào rồi DCA mãi. FTT −97.1%, RAY −97.6%, SRM −89.7%, WAVES −80.6%, DODO −98.1%, AUDIO −96.2%, ANC −99.7%.
- Chiến lược **long-only + DCA-nhồi-loser + KHÔNG hard-SL** ⇒ tổn thất KHÔNG bị chặn; một coin về 0 = mất ~toàn bộ margin cụm đó. Khớp cảnh báo trong CLAUDE.md: "lá chắn chống sập THẬT không nằm ở entry filter — phải xây ở tầng DCA/margin"; và CẠM BẪY "DCA pro-cyclical `isAll=true` trong BIG_DOWN nhồi không trần". Các coin chết này CHÍNH là kịch bản kích hoạt rủi ro đó.
- `avgQuoteVolume` toàn-đời HẠ THẤP thanh khoản đỉnh (FTT/RAY/SRM avg thấp giả do đuôi gần-0 dài) ⇒ số "coin liquid bị thiếu" thực tế **> con số cổng 6**; survivorship còn nặng hơn báo cáo thô.
- Win rate vô nghĩa với martingale (CLAUDE.md) — rủi ro nằm ở ĐUÔI, mà đuôi chính là các coin này. Một session sau thấy backtest "đẹp" đừng tin: nó đẹp một phần vì KHÔNG có LUNA/FTT trong tập.

## Hệ quả

- **Mọi backtest/HPO/WFO hiện tại NGHI NGỜ** cho tới khi backfill + đối chứng (TASK-004).
- Backfill đổi NỀN DỮ LIỆU (thêm symbol) → kết quả backtest đổi; cache HPO cũ KHÔNG còn so sánh được với sau-backfill → **phải chạy lại HPO sau backfill** (đây là dữ liệu, không phải config, nhưng tác động tương đương rule 5: điểm cũ vô nghĩa).
- Ingest phải: cấp `symbolId` trong `symbol_mapper` cho coin mới + đúng format ticker float-packed; ghi vào **242 (nguồn)** rồi re-sync **226** (CopyTicker242To226). CHỈ THÊM coin thiếu, KHÔNG đè symbol đang có.
- Loại khỏi backfill: 2 symbol rác `我踏马来了USDT`, `龙虾USDT` (meme/test) + `LENDUSDT` (không có monthly klines).
- Bằng chứng: `outputs/survivorship_missing_symbols.csv`, `outputs/aerospike_coverage.csv` (TASK-001/002). Liên quan: chuỗi 002→001→004.
