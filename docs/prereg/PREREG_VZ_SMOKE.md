# PREREG_VZ_SMOKE — pre-reg GIẢ để smoke-test runner T7 (ĐÁNH DẤU SMOKE)

> **SMOKE**: đây KHÔNG phải pre-reg cho một giả thuyết thật. Mục đích duy nhất: chứng minh
> `e1_confirm.py` (i) từ chối khi file chưa commit, (ii) chạy và ra ĐÚNG số như T3 cho biến thể
> tương ứng trên 2024 (bit-exact). Ngưỡng dưới đây copy từ `research/vz/e1/configs/t3_thresholds.json`
> (đóng băng trước khi tính outcome).

## 1. Khối YAML

```yaml
name: SMOKE
family: H-B
variant: V1_tss_event_q5
thresholds:
  taker_sell_share:
    nq: 5
    edges: [0.5881896727941192, 0.6419255366430383, 0.689828635738672, 0.7465652534679003]
measure:
  primary: net_60
  statistic: spread_extreme
go_rule: "SMOKE - khong dung de ket luan"
k_tests: 8
years: [2024]
cost: {bucket_real: true, fee_2leg: 0.000982, stress: true}
bootstrap: {block_days: 5, nrep: 2000, seed: 20261014}
```

## 2. Ghi chú

- Chạy: `python3 e1_confirm.py --prereg docs/prereg/PREREG_VZ_SMOKE.md --smoke-check`
- Kỳ vọng: PASS và mọi `mean/median/hit_rate/n` của `net_60`/`net_240` khớp từng số với
  mục `V1_tss_event_q5` trong `~/vz_e1/reports/e1_t3.json`.
