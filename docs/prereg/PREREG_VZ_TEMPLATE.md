# PREREG_VZ_<TÊN> — pre-registration cho xác nhận VZ

Mẫu. Copy sang `docs/prereg/PREREG_VZ_<TÊN>.md`, điền, **commit TRƯỚC khi chạy**.
Runner `research/vz/e1/e1_confirm.py` TỪ CHỐI chạy nếu file này chưa được commit
hoặc còn thay đổi chưa commit.

## 1. Khối YAML (máy đọc)

```yaml
name: <TÊN>                     # tên ngắn, dùng trong tên file output
family: H-B                     # họ giả thuyết (H-B hồi có điều kiện)
variant: V1_tss_event_q5        # biến thể đã chốt ở T3
thresholds:                     # ngưỡng CỐ ĐỊNH lấy từ 2024 (không đổi khi xác nhận)
  taker_sell_share:
    nq: 5
    edges: [...]                # biên quintile tính trên phân phối 2024
measure:                        # thước chính
  primary: net_60               # net ret 60' sau chi phí bucket EXEC + phí 2 chân
  secondary: net_240
  statistic: spread_extreme     # nhóm cực trên - nhóm cực dưới
go_rule: >                      # luật GO chốt trước
  GO nếu CI95 (block bootstrap 5 ngày) của spread net_60 loại 0 và dấu đúng chiều
  đã chốt ở 2024; nếu không đạt => NO-GO.
k_tests: 8                      # tổng số phép thử dùng để nở CI (sqrt(2 ln k))
years: [2022, 2023, 2025]       # năm xác nhận (báo từng năm)
cost: {bucket_real: true, fee_2leg: 0.000982, stress: true}
bootstrap: {block_days: 5, nrep: 2000, seed: 20261014}
```

## 2. Lý do (người đọc)

- Cơ chế kỳ vọng (1–3 câu).
- Vì sao biến thể/ngưỡng này được chốt từ khám phá 2024 (số phép thử, tính đơn điệu).
- Rủi ro đã biết (thanh khoản, giờ chốt funding, nhiễu metrics 5', trễ 7 s).
- Điều kiện bác bỏ (falsification).

## 3. Ghi chú vận hành

- Chạy: `python3 research/vz/e1/e1_confirm.py --prereg docs/prereg/PREREG_VZ_<TÊN>.md --years 2022,2023,2025`
- Output: `~/vz_e1/reports/e1_confirm_<TÊN>.json` (kèm md5 + commit hash của pre-reg).
- **KHÔNG** chạy trước khi pre-reg được commit; **KHÔNG** xem trước 2022/2023/2025.
