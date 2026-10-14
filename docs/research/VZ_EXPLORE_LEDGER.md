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
| 9 | T4 | H-C | V1_rate_q5 | 367940 | net60 spread=-0.00009 CI=[-0.00075,0.00057] mono=-0.50 | 2026-10-14 |
| 10 | T4 | H-C | V2_absrate_top5 | 367940 | net60 spread=0.00020 CI=[-0.00110,0.00121] mono=nan | 2026-10-14 |
| 11 | T4 | H-C | V4_interval | 367940 | net60 spread=-0.00015 CI=[-0.00046,0.00018] mono=nan | 2026-10-14 |
| 12 | T4 | H-C | V3_sign_x_btcregime | 367940 | net60 levels=11:-0.00285,12:-0.00243,21:-0.00262,22:-0.00284 | 2026-10-14 |
| 13 | T5 | H-D | V1_absz_gt3 | 426790 | net60 mean=-0.00250 CI=[-0.0028310727724231233, -0.002175701455737736] hit=0.383 | 2026-10-14 |
| 14 | T5 | H-D | V2_z_neg | 240556 | net60 mean=-0.00236 CI=[-0.002780747921540754, -0.0019485065296041947] hit=0.392 | 2026-10-14 |
| 15 | T5 | H-D | V3_z_pos | 186234 | net60 mean=-0.00268 CI=[-0.0029846828641554085, -0.002394339346115761] hit=0.372 | 2026-10-14 |
| 16 | T5 | H-D | V4_liq_low | 142255 | net60 mean=-0.00263 CI=[-0.0028273376540670454, -0.0024158833095334663] hit=0.350 | 2026-10-14 |
| 17 | T5 | H-D | V5_liq_mid | 142270 | net60 mean=-0.00276 CI=[-0.003098295359280156, -0.002430214321362282] hit=0.388 | 2026-10-14 |
| 18 | T5 | H-D | V6_liq_high | 142265 | net60 mean=-0.00211 CI=[-0.0026576733097074166, -0.0015933693329672578] hit=0.411 | 2026-10-14 |
| 19 | T5 | H-D | V7_on_crash | 6020 | net60 mean=0.00109 CI=[-0.0026316718515473213, 0.0044138884794211065] hit=0.543 | 2026-10-14 |
| 20 | T5 | H-D | V8_off_crash | 420770 | net60 mean=-0.00255 CI=[-0.0028631053697100897, -0.0022522099430822367] hit=0.381 | 2026-10-14 |
| 21 | T6 | H-E | age_0-7d | 5206 | net60 mean=-0.00199 CI=[-0.003093472270432082, -0.000983054612396475] | 2026-10-14 |
| 22 | T6 | H-E | age_8-30d | 4987 | net60 mean=-0.00181 CI=[-0.0029901567256133445, -0.0005292945019202243] | 2026-10-14 |
| 23 | T6 | H-E | age_31-90d | 5779 | net60 mean=-0.00244 CI=[-0.00406620550445077, -0.0007965669799017861] | 2026-10-14 |
| 24 | T6 | H-E | age_>90d | 5713 | net60 mean=-0.00098 CI=[-0.003192426450722535, 0.0011221312923164013] | 2026-10-14 |
| 25 | T6 | H-E | age_unknown | 44335 | net60 mean=-0.00240 | 2026-10-14 |
| 26 | T6 | H-E | listing_drift_1d | 131 | mean=0.00194 CI=[-0.028617782496277454, 0.031803380686132456] | 2026-10-14 |
| 27 | T6 | H-E | listing_drift_3d | 129 | mean=0.03815 CI=[-0.05036621604405913, 0.13650544310022067] | 2026-10-14 |
| 28 | T6 | H-E | listing_drift_7d | 129 | mean=0.00618 CI=[-0.07172680699353194, 0.08335125082672537] | 2026-10-14 |
| 29 | T6 | H-E | listing_drift_30d | 105 | mean=0.04086 CI=[-0.07184206241237498, 0.16692903991489333] | 2026-10-14 |
| 30 | T6 | H-E | predelist_30d | 14 | median=0.00000 | 2026-10-14 |

> **T9 PRE-REG (MASTER 10-14, commit TRƯỚC khi tính outcome)** — 8 biến thể, config `research/vz/e1/configs/t9_config.json` (edges LẤY NGUYÊN từ `configs/t3_thresholds.json`) + code `research/vz/e1/e1_t9.py`. (a) trên 6 709 chân EXEC 2024 ghép sự kiện E1 theo cụm 30′ (feature của sự kiện, net đo trên chính chân: 60′/240′/hold-to-exit) = 4 biến thể × 3 mốc; (b) trên sự kiện E1, mốc 4h/24h cho ΔOI60 + đảo chiều taker = 4 biến thể. Dòng `n`/`kết quả` ở các dòng 31–38 được ĐIỀN sau khi đo, KHÔNG thêm dòng mới. (c) H-E listing drift (median/CI/tỉ lệ dương) KHÔNG tính là phép thử mới.

| # | task | họ | biến thể | n (kế hoạch) | kết quả chính | ngày |
|---|---|---|---|---|---|---|
| 31 | T9 | H-B-chan | A1_doi60_q5 | 3062 chân | net60=-0.00982 CI=[-0.04040,0.01921] mono=-0.20; net240=-0.00266 CI=[-0.02836,0.01616]; exit=-0.01911 CI=[-0.10540,0.04070] mono=-0.30 | 2026-10-14 |
| 32 | T9 | H-B-chan | A2_tss_reversal_q5 | 3067 chân | net60=+0.01913 CI=[-0.00017,0.04262] mono=+1.00; net240=+0.01387 CI=[-0.01195,0.03963] mono=+0.90; exit=-0.02405 | 2026-10-14 |
| 33 | T9 | H-B-chan | A3_premz7_q5 | 3012 chân | net60=-0.00848 CI=[-0.03740,0.02816] mono=-0.60; net240=-0.03402 CI=[-0.06535,0.00487]; exit=-0.00007 | 2026-10-14 |
| 34 | T9 | H-B-chan | A4_combo_doi15low_premlow_t3 | 3012 chân | net60=+0.01066 CI=[-0.03281,0.04868] mono=-0.40; net240=+0.02899 CI=[-0.02667,0.06365]; exit=+0.00787 | 2026-10-14 |
| 35 | T9 | H-B-4h | B1_doi60_h4 | 65906 sự kiện | net240=-0.00542 CI=[-0.00960,-0.00136] mono=-0.70 (stress -0.00530) | 2026-10-14 |
| 36 | T9 | H-B-24h | B2_doi60_h24 | 65906 sự kiện | net1440=-0.00566 CI=[-0.01282,0.00141] mono=-0.30 (stress -0.00554) | 2026-10-14 |
| 37 | T9 | H-B-4h | B3_tssrev_h4 | 66015 sự kiện | net240=-0.00399 CI=[-0.00758,-0.00049] mono=-0.30 (stress -0.00403) | 2026-10-14 |
| 38 | T9 | H-B-24h | B4_tssrev_h24 | 66015 sự kiện | net1440=-0.01306 CI=[-0.02254,-0.00364] mono=-1.00 (stress -0.01310) | 2026-10-14 |

> **T9 hoàn tất (2026-10-14)** — outcome điền vào chính dòng PRE-REG 31–38, KHÔNG thêm dòng nào. Ghép mẫu (a): chỉ **3 081/6 709** chân EXEC có `s_ms` là phút ứng viên crash E1 (3 628 chân vào lệnh ở phút `bar_ret > -1 %`, trung vị -0,91 %) ⇒ (a) chạy trên 3 012–3 067 chân, power thấp hơn ±0,8 %. Hold-to-exit: ledger **không có cột giá thoát**; dùng thời điểm thật `e_ms` (ll_h2/legs.pkl, join seed,row) + Vision close(`e_ms`) — kiểm chứng lệch trung vị -0,19 %. (b): 3/4 tách khỏi 0 (chiều âm, cùng dấu T3) nhưng sẽ chết sau nở CI k=8. (c) median drift âm (1/3/7 ngày, CI không chứa 0), tỉ lệ dương 0,34–0,40 = 0 phép thử mới. **KHÔNG gọi GO.** Báo cáo: `docs/result/VZ_EXPLORE_2024.md` §6b.

> T9 (c) H-E listing drift: bổ sung median/CI95/tỉ lệ dương cho cùng dữ liệu T6 — **0 phép thử mới**.

> **MASTER 2026-10-14 chốt**: V-b cũ SO SAI CỘT (t_star = sàn giờ của t_dec, không phải phút sự kiện = s_ms). Chẩn đoán 3 quy ước: giờ-mở = 100,000%; giờ-đóng 0,328%; dịch ±1-2′ ≤1,3%. ⇒ **V-b1 GIÁ 100% PASS**. V-b2 TIMING: trùng đúng phút 35,35% nhưng **trùng hoặc cùng cụm 30′ = 100%** (1 992 lý do gộp cụm, 0 lọc quote_volume, 0 khác). MỞ LẠI T2–T6 (T3 chỉ trên sự kiện E1). Xem docs/plan/VZ_E1_TASKS.md (T1-V) + docs/result/VZ_EXPLORE_2024.md.

> Q1 (2026-10-14): sua gia dinh phi - SIM_RATE_FEE=0.000982 la phi KHU HOI (2 chan), sim tru MOT lan; E1 cu cong 2x => da sua e1_common.cost_of (FEE_ROUNDTRIP). Tinh lai chi phi T3-T9, 0 phep thu moi. Spread nhom bat bien (max |Δ| <= 2.8e-17).
