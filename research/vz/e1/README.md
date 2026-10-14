# VZ E1 — bộ đo sự kiện 2024 (event study engine)

Branch `research/vz-e1` · worktree `~/claude_master/vz_e1_wt` · dữ liệu trung gian `~/vz_e1/`.

Kế hoạch: `docs/plan/VZ_E1_TASKS.md` (T0–T8 + luật chung), vai trò năm
`docs/plan/VZ_RESEARCH_SPLIT.md`. Chỉ đọc **2024** (`chuyendinh/vz-*-2024`,
`vz-metrics5m` file 2024, `vz-funding` file 2024).

## Thứ tự chạy

```bash
cd ~/claude_master/vz_e1_wt/research/vz/e1
python3 e1_core.py                 # T1: events + panel + dayvol  -> ~/vz_e1/out
python3 -c "import e1_selftest; e1_selftest.run_causal()"        # T1-V(a) causal
python3 e1_validate.py --what bd   # T1-V(b) ledger + (d) counts
python3 e1_validate.py --what c    # T1-V(c) determinism (chạy build 2 lần)
python3 e1_t2.py                   # H-A mô tả (0 phép thử)
python3 e1_t3.py --freeze          # chốt ngưỡng T3 (commit config TRƯỚC khi --run)
python3 e1_t3.py --run             # H-B
python3 e1_families_pass.py        # dựng event set cho T4/T5/T6
python3 e1_t4.py                   # H-C
python3 e1_t5.py                   # H-D
python3 e1_t6.py                   # H-E
python3 e1_confirm.py --prereg ../../../docs/prereg/PREREG_VZ_SMOKE.md --smoke-check
```

## Quy ước

- Chi phí: bucket EXEC theo `bar_ret` nến sự kiện (NC .0007 / C1 .0018 / C2 .0019 / C4 .0032)
  + **2 chân phí** `RATE_FEE = SIM_RATE_FEE = 0.000982` (từ `ho4p1-c2`). Bản stress bucket
  0.0023/0.0033/0.0041/0.0101. Xem `e1_common.cost_of`.
- Thống kê: block bootstrap theo ngày UTC, block 5 ngày, NREP 2000, seed 20261014
  (`e1_stats.day_level_boot`).
- Sự kiện chuẩn `crash`: `close/open-1 ≤ -1%` (float32 như `EntryCost.bucketOf`),
  `active`, `quote_volume ≥ 50 000`, gộp < 30′/symbol (giữ phút đầu).
- Ledger: `docs/research/VZ_EXPLORE_LEDGER.md` (mỗi biến thể đã tính outcome = 1 dòng).

## Giới hạn đã ghi nhận

- `vz-symbols` chưa upload ⇒ tuổi symbol suy từ dữ liệu 2024 (`age_known`); symbol niêm yết
  trước 2024 không đo được tuổi chính xác.
- Lookback 30 ngày cuối 2023 (được phép cho feature) không dùng được vì `vz-basis1m-2023`
  chưa upload ⇒ `prem_z7` là NaN ở ~1 ngày đầu tháng 1.
- Không có liquidation thật (Vision không có), metrics là 5′.
