# VZ EXPLORE 2024 — bộ đo sự kiện E1 (khám phá)

Ngày 2026-10-14 · `research/vz-e1` · dữ liệu `vz-*-2024` (Vision), net sau chi phí bucket EXEC + 2 chân phí (0,000982) + bản stress. Bootstrap block 5 ngày, NREP 2000, seed 20261014.

**KHÔNG gọi GO.** Mọi kết luận là khám phá trên 1 năm (2024); xác nhận phải qua `docs/prereg/PREREG_VZ_*` + `e1_confirm.py`.

## 0. Cổng T1-V
| mục | kết quả |
|---|---|
| V-a causal | PASS 120/120 |
| **V-b1 giá** (open time = s_ms, Vision) | 6709/6709 = **1.0000** → PASS |
| **V-b2 timing** (bar_ret <= -1% ⇒ trùng sự kiện E1) | trùng đúng phút 1089/3081 = **0.3535**; trùng hoặc cùng cụm 30' = **1.0000** | lý do trượt: {'quote_volume': 0, 'merge_30m_direct': 1486, 'merge_30m_chain': 506, 'other': 0} |
| V-c determinism | xem `e1_t1v_c_determinism.json` |
| V-d đếm | PASS — 66 058 sự kiện, NC 0 |

`close_M` nguồn: Vision kline 1m (open time == s_ms) via ll_h2/exec_fetch.py kl/*.npz (leadlag_add1.load_cm); ledger t_star = hour floor of t_dec, NOT the event minute

## 1. Số phép thử

**Tổng số phép thử đã tính outcome (từ sổ `docs/research/VZ_EXPLORE_LEDGER.md`): 30.** (T2 mô tả thuần = 0.) Hệ số nở CI khi xác nhận: sqrt(2 ln k) = 2.608.

## 2. H-A (T2) — profile quanh phút sập (0 phép thử)

n = 66058 sự kiện; bảng median theo offset trong `~/vz_e1/reports/e1_t2_profile.md`.
Đọc: taker_sell_share nhảy lên mức cao ở phút sập rồi giảm dần; volume z đạt đỉnh trong ±5′; prem thường âm quanh sập; ΔOI tích luỹ. Chia C1/C2/C4 và BTC-cùng-sập.

## 3. H-B (T3) — hồi có điều kiện trên SỰ KIỆN E1

| biến thể | n | mono net60 | spread net60 [CI95] | spread stress60 |
|---|---|---|---|---|
| V1_tss_event_q5 | 66058 | 0.20 | -0.00010 [-0.00289, 0.00236] | -0.00023 |
| V2_tss_reversal_q5 | 66015 | -0.70 | -0.00235 [-0.00482, 0.00009] | -0.00239 |
| V3_doi15_q5 | 65946 | -0.30 | -0.00031 [-0.00282, 0.00238] | -0.00017 |
| V4_doi60_q5 | 65906 | -0.60 | -0.00249 [-0.00490, 0.00004] | -0.00237 |
| V5_premz7_q5 | 64590 | -0.90 | -0.00076 [-0.00343, 0.00201] | -0.00051 |
| V6_funding_q5 | 65878 | 0.10 | 0.00030 [-0.00392, 0.00407] | 0.00025 |
| V7_combo_tsshigh_doi15low_t3 | 65946 | 0.03 | 0.00078 [-0.00284, 0.00394] | 0.00057 |
| V8_combo_premlow_doi15low_t3 | 64587 | -0.32 | 0.00129 [-0.00230, 0.00479] | 0.00100 |

Ổn định theo quý (net60 spread) — 3 biến thể mạnh nhất:

| biến thể | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|
| V4_doi60_q5 | -0.00613 | 0.00204 | -0.00148 | -0.00348 |
| V2_tss_reversal_q5 | -0.00379 | 0.00205 | -0.00041 | -0.00510 |
| V8_combo_premlow_doi15low_t3 | 0.00511 | -0.00547 | 0.00413 | 0.00232 |

## 4. H-C (T4) — quanh giờ chốt funding

n = 367940 mốc chốt. Chi phí NC (0,0007 + 2 chân phí).
- **V1_rate_q5**: n=367940 mono=-0.50 spread(net60)=-0.00009 CI=[-0.00075, 0.00057]
- **V2_absrate_top5**: n=367940 mono=nan spread(net60)=0.00020 CI=[-0.00110, 0.00121]
- **V4_interval**: n=367940 mono=nan spread(net60)=-0.00015 CI=[-0.00046, 0.00018]
- **V3_sign_x_btcregime** net60 theo nhóm: 11=-0.00285, 12=-0.00243, 21=-0.00262, 22=-0.00284

## 5. H-D (T5) — basis lệch cực đoan

n = 426790 sự kiện |prem z7| > 3 (gộp 60′/symbol).

| biến thể | n | net60 mean [CI95] | hit | dprem15 | dprem60 |
|---|---|---|---|---|---|
| V1_absz_gt3 | 426790 | -0.00250 [-0.00283, -0.00218] | 0.383 | 0.00013 | 0.00015 |
| V2_z_neg | 240556 | -0.00236 [-0.00278, -0.00195] | 0.392 | 0.00159 | 0.00167 |
| V3_z_pos | 186234 | -0.00268 [-0.00298, -0.00239] | 0.372 | -0.00175 | -0.00181 |
| V4_liq_low | 142255 | -0.00263 [-0.00283, -0.00242] | 0.350 | 0.00049 | 0.00052 |
| V5_liq_mid | 142270 | -0.00276 [-0.00310, -0.00243] | 0.388 | 0.00003 | 0.00004 |
| V6_liq_high | 142265 | -0.00211 [-0.00266, -0.00159] | 0.411 | -0.00011 | -0.00010 |
| V7_on_crash | 6020 | 0.00109 [-0.00263, 0.00441] | 0.543 | 0.00360 | 0.00368 |
| V8_off_crash | 420770 | -0.00255 [-0.00286, -0.00225] | 0.381 | 0.00008 | 0.00010 |

## 6. H-E (T6) — tuổi symbol

| nhóm tuổi | n | net60 mean [CI95] | net240 mean |
|---|---|---|---|
| 0-7d | 5206 | -0.00199 [-0.00309, -0.00098] | -0.00308 |
| 8-30d | 4987 | -0.00181 [-0.00299, -0.00053] | -0.00037 |
| 31-90d | 5779 | -0.00244 [-0.00407, -0.00080] | -0.00106 |
| >90d | 5713 | -0.00098 [-0.00319, 0.00112] | 0.00162 |
| age_unknown | 44335 | -0.00240 | — |

Drift sau niêm yết 2024 (n symbol=131): 1d mean=0.00194, 3d mean=0.03815, 7d mean=0.00618, 30d mean=0.04086

Trước khi bị gỡ (~30 ngày, 14 symbol): median 0.00000, tỉ lệ âm 0.286. **Cảnh báo survivorship.**

## 7. Xếp hạng ≤ 3 ứng viên (KHÔNG gọi GO)

*Không ứng viên nào có hiệu ứng net (thực + stress) tách khỏi 0.*

## 8. Giới hạn

- 1 năm (2024) — không dùng để chốt GO; chưa có 2022/2023/2025 trong lake.
- **Không có dữ liệu thanh lý thật** (Vision không có liquidationSnapshot cho UM) ⇒ ΔOI chỉ là proxy.
- metrics 5′ (không phải tick); giá là kline khớp lệnh Vision.
- `vz-symbols` chưa upload ⇒ tuổi symbol suy từ 2024 (cột `age_known`); symbol niêm yết trước 2024 không đo được tuổi chính xác.
- Không có lookback 30 ngày cuối 2023 (`vz-basis1m-2023` chưa có) ⇒ `prem_z7` NaN ~1 ngày đầu tháng 1.
- **Liên kết với chân của hệ**: đã xác minh ở mức GIÁ (V-b1 = 100% khớp 1e-6) và CẤU TRÚC (V-b2: 100% phút sập của chân nằm trong cùng cụm 30' của một sự kiện E1). Tuy vậy mọi hiệu ứng ở trên đo trên SỰ KIỆN E1, KHÔNG dùng chân EXEC làm mẫu.

## 9. Tệp

- `~/vz_e1/out/`: `e1_events_2024.parquet`, `e1_panel_2024.parquet`, `e1_dayvol_2024.parquet`, `e1_t4_funding_events.parquet`, `e1_t5_basis_events.parquet`, `e1_listing_drift.parquet`, `e1_month_snap.parquet`, `e1_sym_life_2024.parquet`.
- `~/vz_e1/reports/`: các JSON ở trên.
