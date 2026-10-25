# PREREG_NUP — ADDENDUM B (nguồn giá MTM DEV) — 2026-10-26

## B.1 Sự cố

`research/golive_quarterly/mtm_dev.py` đọc giá 1m từ `~/kaggle_data_hpo` (symlink
`/home/ubuntu/java/simulator/kaggle_data_hpo/daily`). Ngày 2026-10-26 symlink **trỏ vào thư mục
không còn tồn tại**; không có file `ticker_*.bin.gz` nào trên Oracle. Vì vậy `gvz_mtm/_work` không
thể chạy cho run mới. Không tải lại dữ liệu (luật đĩa + không gọi Binance REST).

## B.2 Thay thế

Dùng **cùng nguồn giá Vision 1m close**, đã có sẵn trên Oracle dưới dạng parquet tháng:
- 2021: `/home/ubuntu/claude_master/gvz/k2021/kline1m-2021-MM.parquet`
- 2022–2025: `/home/ubuntu/vz_e1/raw/kline1m-YYYY-MM.parquet`

Script `research/nup/mtm_parquet.py` tái tạo **đúng công thức legacy** của
`reset_rule_score._work`:
`u(t)=Σ q·(close(t)−entry)` cho leg đang mở; `sp(t)=cumsum(pnl tại m1)`;
`eq(t)=CAP0+sp(t)+u(t)`. Leg đóng đúng 00:00 UTC được cộng PnL tự nhiên (không bỏ sót) — tức bản
ĐÃ SỬA lỗi 00:00 UTC. Vì vậy khi chấm dùng `quarterly.build(..., fix_off=None)` (không cộng bù lần 2).

Quy ước trục giữ nguyên: giờ +07, trục UTC = +07−7h; eq bắt đầu 2021-07-01 00:00 UTC; khi đưa vào
`quarterly.build` đặt tại offset 420 phút (ub = 2021-06-30 17:00 UTC).

## B.3 Kiểm chứng (trước khi chấm arm)

Chạy lại B0 seed S7 bằng parquet: `n_cl=2891`, `n_leg=2951`, `ΣPnL=108 906,7`,
`CAGR22=37,872 %`, `maxDD= −22,744 %`, `Calmar=1,665` — khớp tuyệt đối
`docs/result/golive_quarterly/quarterly_x14_by_seed.csv` (S7: 2891/2951/108 907/37,87/−22,74).
Sai số `flat_maxabs` = 97,5 USD (0,09 % equity) tại ranh giới một phút; `missing` = 0 mọi leg.
Sẽ chạy đủ 8 seed B0 và báo median; nếu lệch số công bố (−22,83 / 39,06) quá 0,1 pp thì DỪNG.

## B.4 Phạm vi

Chỉ thay **cách lấy giá**; không đổi cụm/leg/PnL/printDone, không đổi luật G1–G4, không đổi seed.
HO 2026 vẫn dùng `ecm_mtm_h` + cache `ecm_px` như `mtm_ho.py` (kiểm `miss=0`).
