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

> **MASTER 2026-10-14 chốt**: V-b cũ SO SAI CỘT (t_star = sàn giờ của t_dec, không phải phút sự kiện = s_ms). Chẩn đoán 3 quy ước: giờ-mở = 100,000%; giờ-đóng 0,328%; dịch ±1-2′ ≤1,3%. ⇒ **V-b1 GIÁ 100% PASS**. V-b2 TIMING: trùng đúng phút 35,35% nhưng **trùng hoặc cùng cụm 30′ = 100%** (1 992 lý do gộp cụm, 0 lọc quote_volume, 0 khác). MỞ LẠI T2–T6 (T3 chỉ trên sự kiện E1). Xem docs/plan/VZ_E1_TASKS.md (T1-V) + docs/result/VZ_EXPLORE_2024.md.
