# PREREG MD_STRAT — Tầng A (offline, cắt lớp): rateDownAvg / rateUpAvg / rateDown15MAvg lúc vào có cho biết nên vào top-K mấy không — 2026-10-20

Owner 10-20: dùng MarketDataObject (rateDown15MAvg bắt big-down, rateUpAvg) cắt lớp xem có giá trị chọn top-K nào để vào.
Định nghĩa (MarketBigChangeDetector.calMarketData): mỗi phút, rateDownAvg = TB return 1m của ~100 coin giảm mạnh nhất; rateUpAvg = TB return 1m của ~100 coin tăng mạnh nhất; rateDown15MAvg = TB (close/max gần đây − 1) của ~100 coin sâu nhất. BIG_DOWN = rateDownAvg < MS_DOWN_BIG_AVG.
Đã có (trên T170, không phải K24): BD_SIZE_ADAPT (size theo độ sâu rateDownAvg) NULL; TICK_BLOCK (chặn lượt yếu theo DEPTH/DROP15M) NULL vì lệnh bị chặn được vào lại ở lượt sau. Lưu ý: GATE_INVENTORY ghi `MarketDataInlineGenerator`/`rateDownAvg` CHƯA kiểm look-ahead.

## Dữ liệu
Lệnh DEV K24+skipFull phí gốc 8 seed `~/kaggle_sim/out/gqsf-*/storage/printDone.csv` (cột dow, up, dow15m, pred15m, symbolPred lúc vào — PHẢI xác minh trong code ghi printDone rằng dow=rateDownAvg, up=rateUpAvg, dow15m=rateDown15MAvg của phút vào). Cụm như ENTRY_CONFIRM (`~/claude_master/entry_confirm/ec_a_clusters.parquet` + join cột từ chân mở). Đợt = các cụm mở cùng phút M trong 1 seed. Hạng r trong đợt = thứ tự symbolPred giảm dần (xác minh đúng thứ tự S1 dùng chọn top-K; nếu không, dùng thứ tự sim ghi và nêu rõ).

## Chia mẫu (đóng băng)
Khám phá D = 2021-07→2023-12; Xác nhận C = 2024-01→2025-12. Mọi ngưỡng tính trên D.

## Cắt lớp
- Biến trạng thái đợt S ∈ {dow, up, dow15m} (giá trị chân mở đầu tiên của đợt), mỗi biến chia tercile theo cutoff D (theo đợt, không theo cụm).
- Nhóm hạng: R1 = 1–5, R2 = 6–12, R3 = 13–24.
- Báo mỗi ô (biến × tercile × nhóm hạng), tách D và C: số cụm/seed, PnL/cụm, win %, % time-stop, ΣPnL/seed.

## Luật ứng viên (chọn trên D bằng thủ tục cố định, xác nhận trên C)
- Ứng viên "thu hẹp K": ô (biến, tercile) mà ΣPnL nhóm R2+R3 trên D < 0 (TB 8 seed) VÀ ≥ 6/8 seed âm. Luật = trong ô đó chỉ vào hạng 1–5. Nếu nhiều ô đạt, lấy ô có ΣPnL R2+R3 âm nhất (1 ô duy nhất).
- Xác nhận C: ΣPnL R2+R3 của đúng ô đó trên C < 0 (TB) VÀ ≥ 6/8 seed âm VÀ ΔPnL_thô = −ΣPnL(R2+R3 trong ô) > +5 000/seed trên C.
- Ngược lại (nới K): ô mà R3 lãi/cụm > R1 trên D — chỉ mô tả (không có cơ chế K>24 trong luật này).
- Không ô nào đạt D ⇒ ĐÓNG (biến trạng thái không giúp chọn K). Đạt D nhưng trượt C ⇒ ĐÓNG. Đạt cả hai ⇒ viết prereg tầng B (sim 8 seed, vì TICK_BLOCK cho thấy lệnh bị bỏ có thể dồn sang lượt sau — ΔPnL offline có thể ảo).
- Mô tả thêm: tương quan Spearman (theo đợt) của dow/up/dow15m với PnL/cụm TB của đợt, D và C.

## Validate
V1 cột dow/up/dow15m đúng nghĩa (đọc code ghi printDone; so 3 đợt với market.bin nếu đọc được). V2 ΣPnL/seed khớp ENTRY_CONFIRM V1. V3 hạng r khớp số cụm/đợt (≤ 24). V4 không dùng dữ liệu C khi chọn ngưỡng/ô.
