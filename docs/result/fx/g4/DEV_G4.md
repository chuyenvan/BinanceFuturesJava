# DEV_G4 - code + test (KHONG chay backtest that; khoa --real I_HAVE_A1_PASS)
Thu muc ~/claude_master/w3/fx/g4/{code,out}. Python /usr/bin/python3 (numpy, pandas, pyarrow 25). Lua chon: CHOICES_G4.md.
## Du lieu (chi doc)
```
0293cbcd52c1ec5bd234403b8e56f7c215d01faf5c2cc024596cb61f34977091  ~/claude_master/w3/fx/data/derived/m1/AUDUSD_M1_2005_2019.parquet
8d5720a8b4f76ab867201b2a371023d4c9cabdf5e3d4534b09263123a24dd074  ~/claude_master/w3/fx/data/derived/m1/EURUSD_M1_2005_2019.parquet
345ef2b20ed9d8cce0533640e8c0d4ce105ec683d8338a6cbc4b0c0b126a357b  ~/claude_master/w3/fx/data/derived/m1/GBPUSD_M1_2005_2019.parquet
976e3e18ff21af71857189975d655dd6ccaa1419e78b08826e0ff9b51c2e9ec8  ~/claude_master/w3/fx/data/derived/m1/USDJPY_M1_2005_2019.parquet
```
## Lenh mot dong
- nap + kiem ke: `cd ~/claude_master/w3/fx/g4/code && python3 load_g4.py` (~20 s, RAM ~2,5 GB)
- dem su kien (chi dem): `cd ~/claude_master/w3/fx/g4/code && python3 sig_g4.py --count` -> out/event_counts_g4_{summary,by_pair_year}.csv
- test: `cd ~/claude_master/w3/fx/g4/code && python3 test_g4.py` (~5 phut) -> out/test_results_abcefghi.txt
- SAU A1: `cd ~/claude_master/w3/fx/g4/code && python3 eval_g4.py --real I_HAVE_A1_PASS` (D2 = dich vong ngay; `--d2 random` neu MASTER chon) -> out/eval_g4.{json,md}
## Ket qua test (run 2026-11-27T02:22:30Z)
```
PASS a_trailing_exit TRAIL exit=44 net=4.727471e-04 hand=4.727471e-04
PASS a_sl_exit_slip 
PASS a_time_stop_short TS exit=45
PASS a_gap_exit_at_open 
PASS a_rollover_x3_and_swap cost=1.818e-04 hand=1.818e-04 swap=1.565e-18 hand=0.000e+00
PASS a_cost_x2 
PASS a_swap_sign_short 
PASS a_cost_rule_jpy 
PASS b_gap5_window_rejected 
PASS b_after_gap60_30min_rejected 
PASS b_z_hand 
PASS b_sigma_prev20_hand 
PASS b_sigma_excludes_own_session 
PASS c_causal_events_before_T0_unchanged 
PASS c_excluded_pair_years_no_events 
PASS c_sigma_undefined_20_sessions_after_excluded_year 
PASS c_gbp_2009_excluded 
PASS e_random_same_count_hour_month 
PASS e_shift_keeps_time_of_day_count 
PASS f_selection_train_only L-15-4-24h / L-15-4-24h
PASS f_tie_break_short_TS_then_high_T 
PASS g_refuse_cutoff_2020-01-01 
PASS g_refuse_cutoff_2021-06-30 
PASS g_real_max_le_cutoff 2019-12-31 21:00:00
PASS g_sim_real_locked 
PASS g_perm_p_plus1 
PASS h_rebound sel=L-15-4-4h concl=DAT crit={'D1': True, 'D2': True, 'D3': True, 'D4': True, 'D5': True, 'D6': True, 'D7': True} ctrl={'n': 500, 'd2_basis': 'shift', 'p_day_shift': 0.002, 'p_random_same_hour_month': 0.002, 'shift_mean_sharpe': -2.6602, 'random_mean_sharpe': -2.8962} (53s)
PASS h_noise sel=S-60-4-24h concl=KHONG DAT crit={'D1': False, 'D2': False, 'D3': True, 'D4': False, 'D5': False, 'D6': False, 'D7': True} ctrl={'n': 500, 'd2_basis': 'shift', 'p_day_shift': 0.6607, 'p_random_same_hour_month': 0.1098, 'shift_mean_sharpe': -0.9941, 'random_mean_sharpe': -1.5371} (49s)
PASS i_deterministic 
PASS i_nrand_lt_500_refused 
TOTAL 30 FAIL 0
```
## Dem su kien du lieu that (<= 2019; event_bars = moi phut thoa, episodes = phut dau chuoi; KHONG phai so lenh)
```
kind,,,episodes,episodes,event_bars,event_bars
period,,,TRAIN,WFO,TRAIN,WFO
side,N,T,,,,
L,15,4.0,4036,7152,14684,28808
L,60,3.0,5323,8949,39520,72787
L,60,4.0,1828,3579,13038,29315
S,15,4.0,3882,6881,14146,27805
S,60,3.0,4910,8144,38041,66985
S,60,4.0,1704,3212,13322,27724
```
## sha256
```
37c1ef56f88ba12c9e4c8b8e789a35c47a3dc905f76bd43f75b67f47135bf207  code/eval_g4.py
a76f22cf8c98cfbf1aa889e1e86b8f6deb56327ab849fb995ee17f977637f073  code/load_g4.py
7269d85213243872633f2b33276da7c3c88c967d83aeea53f6de8ac0b15da6cb  code/sig_g4.py
1208187b6c3a9959a02e8fa84d3e9d50ac90de86b710beede2c3151fa3772854  code/sim_g4.py
28c4bc76c31354e018607ed769b4b0b3784c91d69d8464a6715d798f2ec3d5d3  code/test_g4.py
1dc7acb7508558c29ea2f43072bdd403f8ee03f1385b0abdacbcd6b9fed25541  CHOICES_G4.md
```
