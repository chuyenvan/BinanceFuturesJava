# VZ EXPLORE LEDGER - so phep thu kham pha 2024

Mỗi biến thể ĐÃ TÍNH outcome = 1 dòng. Vai trò năm: `docs/plan/VZ_RESEARCH_SPLIT.md`.
Chi phí: bucket EXEC thực + phí 2 chân (SIM_RATE_FEE=0.000982). Bootstrap block 5 ngày, NREP 2000, seed 20261014.

| # | task | họ | biến thể | n sự kiện | kết quả chính | ngày |
|---|---|---|---|---|---|---|
| 1 | T3 | H-B | V1_tss_event_q5 | 66058 | spread60=-0.00010 CI=[-0.00289,0.00236] mono60=0.20 | 2026-10-14 |
| 2 | T3 | H-B | V2_tss_reversal_q5 | 66015 | spread60=-0.00235 CI=[-0.00482,0.00009] mono60=-0.70 | 2026-10-14 |
| 3 | T3 | H-B | V3_doi15_q5 | 65946 | spread60=-0.00031 CI=[-0.00282,0.00238] mono60=-0.30 | 2026-10-14 |
| 4 | T3 | H-B | V4_doi60_q5 | 65906 | spread60=-0.00249 CI=[-0.00490,0.00004] mono60=-0.60 | 2026-10-14 |
| 5 | T3 | H-B | V5_premz7_q5 | 64590 | spread60=-0.00076 CI=[-0.00343,0.00201] mono60=-0.90 | 2026-10-14 |
| 6 | T3 | H-B | V6_funding_q5 | 65878 | spread60=0.00030 CI=[-0.00392,0.00407] mono60=0.10 | 2026-10-14 |
| 7 | T3 | H-B | V7_combo_tsshigh_doi15low_t3 | 65946 | spread60=0.00078 CI=[-0.00284,0.00394] mono60=0.03 | 2026-10-14 |
| 8 | T3 | H-B | V8_combo_premlow_doi15low_t3 | 64587 | spread60=0.00129 CI=[-0.00230,0.00479] mono60=-0.32 | 2026-10-14 |

> T2 (H-A) la mo ta thuan tuy - **0 phep thu** (khong chon nguong, khong tinh outcome). Profile: ~/vz_e1/reports/e1_t2_profile.md

> **T1-V(b) FAIL** (2026-10-14): ledger EXEC 2024 dung bar 1p tu ticker noi bo, KHONG khop kline Vision (chi 8,5% khop 1e-6; trung vi lech 1,8%). Theo luat chung => DUNG cac ho gia thuyet. 8 dong T3 o tren duoc tinh TRUOC khi cong V-b ket luan va KHONG duoc dung de ket luan (xem docs/result/VZ_E1_T1V_2024.md).
