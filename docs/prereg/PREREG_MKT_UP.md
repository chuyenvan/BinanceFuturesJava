# PREREG MKT_UP — Tầng A (offline): model dự đoán "thị trường ĐI LÊN" (không phải "hồi sau sập") — 2026-10-20

Owner 10-20: không dùng MA200 (họ trend MA đã chết), mà dựng công thức/model có label = thị trường đi lên; dùng làm "trạng thái thị trường" cho hệ. Hệ cũ/shadow KHÔNG đụng; nếu đi tiếp chỉ là ứng viên v1.1. HO 2026 KHÔNG dùng ở tầng A.

## Label (đóng băng)
- Thị trường = ALT_EW (TB log-return 1m alt trừ BTC/ETH, như `edge_attr/index.npz`; 2026 không dùng). Mẫu 1 dòng/ngày tại 00:00 UTC.
- **y = 1 nếu log-return ALT_EW 72h tới > 0** (chính). Mô tả thêm: BTC 72h, ALT_EW 7d (không quyết định).

## Feature (chỉ dùng dữ liệu ≤ thời điểm mẫu, tính từ index.npz EW + BTC 1m)
Cho cả EW và BTC: return 1d, 3d, 7d, 30d; vol thực 1d, 7d (std log-ret 1m × √1440); khoảng cách tới max 30d và min 30d (log); EW−BTC return 7d, 30d. Tổng 18 cột. Không thêm/bớt sau khi xem kết quả.

## Model & walk-forward
- Chính: hồi quy logistic L2 (C=1, chuẩn hoá theo tập train). Phụ (mô tả): LightGBM depth 3, 200 cây, lr 0,05.
- Expanding window, refit mỗi tháng, train từ 2021-08, purge 3 ngày trước mốc dự đoán; dự đoán OOS từ **2022-07-01**. DEV-OOS = 2022-07→2024-12; VAL = 2025 (dùng 1 lần, chỉ xác nhận dấu).

## Đánh giá
- **E1 chất lượng dự báo** (DEV-OOS): AUC > 0,55 VÀ AUC > 0,5 ở ≥ 2/3 năm (2022H2, 2023, 2024); VAL 2025 AUC > 0,5.
- **E2 dùng để chỉnh size crash-buy** (cụm lệnh DEV từ `~/claude_master/entry_confirm/ec_a_clusters.parquet`, 8 seed): P = xác suất OOS của ngày chứa M (dự đoán tại 00:00 UTC ngày đó, tức trước M). Luật cố định: size ×0,5 nếu P < 0,45, ×1 nếu không. ΔPnL_thô = −0,5·Σ PnL cụm có P < 0,45 (bỏ qua path/vốn). Đạt nếu ΔPnL_thô TB > +5 000/seed, ≥ 6/8 seed dương, ≥ 2/3 năm DEV-OOS dương, VAL 2025 dương; kèm PnL/cụm theo tercile P (mô tả).
- **E3 dùng làm "lớp K5" khi dự báo đi lên**: long ALT_EW giữ 72h khi P > 0,55 (lệnh chồng nhau = trung bình), phí 0,10 %/chiều. Đạt nếu Sharpe năm hoá DEV-OOS > 0,5 VÀ > Sharpe long ALT_EW luôn VÀ VAL 2025 Sharpe > 0. Báo kèm phiên bản BTC (mô tả).
- **Đi tiếp tầng B nếu E1 đạt VÀ (E2 hoặc E3) đạt.** Trượt ⇒ ĐÓNG hướng "model thị trường đi lên" (không đổi label/H/feature/ngưỡng).

## Validate
V1 không look-ahead: feature tại t chỉ dùng phút < t (kiểm bằng cách cắt dữ liệu sau t, feature không đổi). V2 label dùng phút (t, t+72h]. V3 refit chỉ dùng mẫu có label hoàn tất trước mốc (purge). V4 E2 dùng đúng P của ngày chứa M (UTC) — kiểm 20 cụm tay.

## Ước lượng trước (MASTER): P(qua tầng A) ~10–15 %. Bằng chứng ngược: REX S2a regime, TF Donchian, T2-MOM, trend MA, GATE_VZ đều NO-GO; dự báo hướng thị trường crypto theo ngày thường IC rất thấp.
