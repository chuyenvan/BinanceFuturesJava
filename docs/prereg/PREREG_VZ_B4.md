# PREREG_VZ_B4 — xác nhận: đảo chiều taker tại nến sập ⇒ net 24h xấu hơn (MASTER 2026-10-14)

Nguồn giả thuyết: khám phá 2024 (`docs/result/VZ_EXPLORE_2024.md` §6b.2, branch research/vz-e1 6b2ae088), biến thể B4_tssrev_h24: spread quintile cao − thấp = −1,31 % [−2,25; −0,36], mono −1,00. Tổng phép thử khám phá k = 38.

## Khối YAML (máy đọc)

```yaml
name: B4
family: H-B
variant: V2_tss_reversal_q5
thresholds:
  tss_reversal:
    nq: 5
    edges: [0.0653215038194228, 0.12279905054056256, 0.17445347601643468, 0.24196095258927172]
measure:
  primary: net_1440
  secondary: net_240
  statistic: spread_extreme
go_rule: >
  GO ⇔ cả ba: (1) gộp 3 năm spread net 24h < 0 và cận trên CI95 nở √(2 ln 38) = 2,70
  (mean + 2,70·se) < 0; (2) mỗi năm 2022, 2023, 2025 spread net 24h < 0;
  (3) bản stress cùng chiều (gộp < 0). Ngược lại ⇒ ĐÓNG giả thuyết; không thử chân trời/biên khác.
k_tests: 38
years: [2022, 2023, 2025]
cost: {bucket_real: true, fee_2leg: 0.000982, stress: true}
bootstrap: {block_days: 5, nrep: 2000, seed: 20261014}
```

## Giả thuyết
H: trên sự kiện `crash` E1 (định nghĩa e1_core, KHÔNG đổi), quintile cao nhất của `tss_reversal` (taker_sell_share phút sự kiện − TB 5′ trước) có net 24h thấp hơn quintile thấp nhất.

## Cố định (lấy nguyên từ 2024, không tính lại)
- Định nghĩa sự kiện, feature, công thức net (`log(close ts+1440′ / close ts) − (bucket EXEC + 2×0,000982)`), bản stress: như `e1_core` tại commit 6b2ae088.
- Biên quintile `tss_reversal`: đúng file `research/vz/e1/configs/t3_thresholds.json` (ngưỡng 2024) — KHÔNG tính lại quintile theo năm xác nhận.
- Bootstrap block 5 ngày UTC, NREP 2000, seed 20261014.

## Dữ liệu xác nhận
2022, 2023, 2025 (mỗi năm riêng + gộp). Lookback feature được dùng ≤ 30 ngày cuối năm trước; sự kiện có `ts+1440′` vượt năm ⇒ bỏ (không đọc năm sau). Không dùng 2021/2024/2026/2020s.

## Luật GO (chốt trước)
GO ⇔ cả ba:
1. Gộp 3 năm: spread net 24h < 0 và cận trên CI95 **nở √(2 ln 38) = 2,70** (tức mean + 2,70·se) < 0.
2. Mỗi năm 2022, 2023, 2025: spread net 24h < 0.
3. Bản stress cùng chiều (gộp < 0).
Ngược lại ⇒ ĐÓNG giả thuyết; không thử chân trời/biên khác.

## Báo kèm (không quyết định)
- Spread net 60′, 240′ cùng sự kiện; mono theo quintile; theo quý.
- n sự kiện mỗi năm, tỉ lệ sự kiện có đủ 24h.

## Nếu GO
Không triển khai gì trực tiếp. Bước sau (pre-reg riêng): đo trên tập ứng viên thật của hệ (không phải sự kiện crash thô — T9 cho thấy 3 628/6 709 chân EXEC 2024 vào ở phút bar_ret > −1 %) rồi mới sim lọc.

## Thực thi
OpenClaw: chuyển các tham số trên vào khối YAML theo `docs/prereg/PREREG_VZ_TEMPLATE.md` NGAY TRONG FILE NÀY, commit, rồi chạy `e1_confirm.py --prereg docs/prereg/PREREG_VZ_B4.md --years 2022,2023,2025` khi lake đủ 3 năm (+ lookback). Không sửa nội dung giả thuyết/luật khi chuyển YAML.
