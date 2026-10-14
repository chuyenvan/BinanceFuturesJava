# VZ_REGISTRY — sổ đăng ký kho dữ liệu Binance Vision (Kaggle)

Bản đầy đủ (thiết kế lake + Phase 1 theo năm) nằm ở branch `data/vz-lake`
(`docs/data/VZ_REGISTRY.md` của worktree `~/claude_master/vz_wt`). File này ghi
các dataset mà **E1 (research/vz-e1)** đã dùng, để truy vết.

Owner: OpenClaw (UniDeep). Cập nhật: 2026-10-14.

## Dataset 2024 dùng cho E1 (chỉ đọc, PRIVATE `chuyendinh/*`)

| slug | file dùng | n rows (đo) | ghi chú |
|---|---|---|---|
| `chuyendinh/vz-kline1m-2024` | kline1m-2024-01..12.parquet | 155 015 111 (12 file) | schema: ts int64, sym dict, open/high/low/close/volume/quote_volume float64, n_trades int32, taker_buy_base, taker_buy_quote, active bool; 1 row group = 1 symbol |
| `chuyendinh/vz-basis1m-2024` | basis1m-2024-01..12.parquet | 153 683 583 (12 file) | ts, sym, prem_high/low/close, mark_close, index_close, active |
| `chuyendinh/vz-metrics5m` | metrics5m-2024.parquet | 29 137 211 | ts (create_time ms), sym, oi, oi_value, toptrader_ls_cnt/sum, ls_cnt, taker_ls_vol |
| `chuyendinh/vz-funding` | funding-2024.parquet | 439 989 | ts (calc_time), sym, interval_h, rate |

- Ngoài phạm vi E1: `vz-kline1m-2023`, `vz-basis1m-2023`, `vz-kline1m-2025`,
  `vz-symbols` **chưa được upload** tại thời điểm chạy (probe `kaggle datasets files`
  trả 403). Vì vậy lookback 30 ngày cuối 2023 (được phép cho feature) **không dùng được**,
  và tuổi symbol phải suy từ dữ liệu 2024 (xem T6: `age_known`).
- md5 `~/claude_master/1013/ll_h2/leadlag_h2_legs.csv.gz` = `e3a63b58…` (khớp hằng số
  trong VZ_E1_TASKS) — dùng cho T1-V(b).

## File trung gian E1 (không upload)

`~/vz_e1/out/`: `e1_events_2024.parquet`, `e1_panel_2024.parquet`, `e1_dayvol_2024.parquet`,
`e1_t4_funding_events.parquet`, `e1_t5_basis_events.parquet`, `e1_listing_drift.parquet`,
`e1_month_snap.parquet`, `e1_sym_life_2024.parquet`.
