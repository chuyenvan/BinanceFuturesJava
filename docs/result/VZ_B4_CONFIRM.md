# VZ_B4_CONFIRM — xác nhận B4 (đảo chiều taker → net 24h âm), 2022/2023/2025

MASTER 10-15. Chạy **đúng một lần** theo pre-reg `docs/prereg/PREREG_VZ_B4.md` (+ Addendum 1, commit `997f18f3`)
bằng `research/vz/e1/e1_confirm.py` (code `ebfbb806`). Không đổi định nghĩa/biên/biến thể; chỉ biến thể
`V2_tss_reversal_q5`; edges quintile **đóng băng** từ 2024 (`configs/t3_thresholds.json`).

- Output: `~/vz_e1/reports/e1_confirm_B4.json` — **md5 `e9b6560cc292dc1bcb52425deccfc1ff`**
- pre-reg commit: `997f18f32405ea22eccfd1ba41e26113ff558569`; hệ số nở CI √(2 ln 38) = **2,697**
- Dữ liệu: kline1m 2022/2023/2025 + lookback 30 ngày cuối năm trước (2021-12/2022-12/2024-12).
  Sự kiện giữ lại chỉ khi `ts+1440′` trong năm. n = 38 049 / 36 626 / 153 973 (gộp 228 648); tỉ lệ có đủ 24h = 99,63 % / 99,30 % / 99,59 %.

## LUẬT GO (chốt trước) — kết quả

| điều kiện | yêu cầu | kết quả | đạt? |
|---|---|---|---|
| (1) gộp 3 năm | spread net 24h < 0 **và** mean + 2,70·se < 0 | spread **+0,00144**; CI95 [−0,00181, +0,00464]; cận nở **+0,00583** | **KHÔNG** |
| (2) mỗi năm | spread net 24h < 0 (đủ 2022/2023/2025) | 2022 **+0,00107**; 2023 **−0,00235**; 2025 **+0,00320** | **KHÔNG** |
| (3) stress gộp | cùng chiều (< 0) | **+0,00148** (CI95 [−0,00176, +0,00469]) | **KHÔNG** |

## KẾT LUẬN: **NO-GO** ⇒ ĐÓNG giả thuyết B4.

Hướng khám phá 2024 (spread −1,31 %, mono −1,00) **không tái lập**: ở 2022 và 2025 spread **dương** (ngược chiều,
2025 còn CI95 tách khỏi 0 ở cả 60′/240′), 2023 âm nhưng CI chứa 0; gộp 3 năm **dương** với CI chứa 0.
Đơn điệu gộp **+0,40** (đảo dấu so với 2024). Theo pre-reg: "Ngược lại ⇒ ĐÓNG giả thuyết; không thử chân trời/biên khác."

## Báo kèm (không quyết định)

| năm | n (đủ 24h) | net_60″ spread | net_240′ spread | net_1440 spread [CI95] | mono |
|---|---|---|---|---|---|
| 2022 | 38 049 | +0,00120 | +0,00061 | **+0,00107** [−0,00786, +0,00991] | +0,40 |
| 2023 | 36 626 | −0,00032 | −0,00081 | **−0,00235** [−0,00574, +0,00116] | 0,00 |
| 2025 | 153 973 | +0,00177 | +0,00256 | **+0,00320** [−0,00097, +0,00717] | +0,70 |
| gộp | 228 648 | +0,00131 | +0,00149 | **+0,00144** [−0,00181, +0,00464] | +0,40 |

Phí: theo Addendum 1 (phí khứ hồi cộng **một lần**, `SIM_RATE_FEE=0,000982`) — spread bất biến với dịch phí đều,
kết luận GO/NO-GO không phụ thuộc kịch bản phí.

## Tệp
- `~/vz_e1/reports/e1_confirm_B4.json` (md5 `e9b6560cc292dc1bcb52425deccfc1ff`)
- log: `~/vz_e1/logs/q6_confirm.out`
