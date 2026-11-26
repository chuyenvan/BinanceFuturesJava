# DEV_G3 - code + test (KHONG chay backtest that; khoa --real I_HAVE_A1_PASS). Cap nhat ERRATA2 (J1, J5) + ERRATA3 (K1-K4, K6)
Thu muc: ~/claude_master/w3/fx/g3/{code,out}. Python /usr/bin/python3, numpy 2.2.6, pandas 2.3.3. Lua chon: CHOICES_G3.md. Audit: A1_G3_CODE.md.
## Nguon du lieu
- Loader doc ~/claude_master/w3/fx/data/derived/cot_legacy_fx_cut.csv, cot_tff_fx_cut.csv (cat <= 2026-10-31; loader bo moi dong > cutoff khi doc), FRED_*.csv, ../cot_release_exceptions.csv.
- Raw TFF (11 zip) o data/raw/ - sha256:
```
c3a8d01765133a24ce9c082de88933816497d06f1b03eec8c53750bdd818f14b  ~/claude_master/w3/fx/data/raw/fin_fut_txt_2006_2016.zip
e6e2dd537efcc57cdd6cdcc4e45e567fd47e65d8afc8369d8383bf09195ae7f5  ~/claude_master/w3/fx/data/raw/fut_fin_txt_2017.zip
6843d130a25a17c6248df67463810f02077ef4eeafdd629299d21c18f5125e40  ~/claude_master/w3/fx/data/raw/fut_fin_txt_2018.zip
631b31880d513072aa50d63117c896184dd35db3cc8fcdd6debd80197ee7a661  ~/claude_master/w3/fx/data/raw/fut_fin_txt_2019.zip
c90d98d94db708772d669f263fb8061c75f8a7f681ba231fb21247e5c9798e6b  ~/claude_master/w3/fx/data/raw/fut_fin_txt_2020.zip
5c929991038c70ae2501661b6d442b9e784d3c29d3166ceac2e21b45ac93d56a  ~/claude_master/w3/fx/data/raw/fut_fin_txt_2021.zip
94c9c1fdee9dfbe377a09923ddfe26b88d3460605dd076081f221ad367d88601  ~/claude_master/w3/fx/data/raw/fut_fin_txt_2022.zip
43c3dbdd4d01fceefad5e457003751cdc0974c7cf46097b322e26e9e2fe44d7a  ~/claude_master/w3/fx/data/raw/fut_fin_txt_2023.zip
3f00585741a7cf76c207df640951d644dd91ff22a1106b38ca37a2469c765637  ~/claude_master/w3/fx/data/raw/fut_fin_txt_2024.zip
2ea0cda6395f7dd6501c27422be3763e1f2f5b41b768cfd36b871f092a07d438  ~/claude_master/w3/fx/data/raw/fut_fin_txt_2025.zip
8010e000c34c02584746296af98de12a267d8575e54f8513fbd6177fb05def9d  ~/claude_master/w3/fx/data/raw/fut_fin_txt_2026.zip
910120c7ef22366ef143af60722631b57aacd35cb840bb7d85d303c5da07759d  ~/claude_master/w3/fx/data/derived/cot_legacy_fx_cut.csv
ce04c4a31588c241429cda92569fad59e34b0754678e838292a53589269090d2  ~/claude_master/w3/fx/data/derived/cot_tff_fx_cut.csv
```
## Lenh mot dong
- kiem ke: `cd ~/claude_master/w3/fx/g3/code && python3 load_g3.py` -> out/inventory_g3.csv
- dem |z|>=1.5 (chi dem): `cd ~/claude_master/w3/fx/g3/code && python3 sig_g3.py --count` -> out/event_counts_g3.csv
- test: `cd ~/claude_master/w3/fx/g3/code && python3 test_g3.py` (~7 phut) -> out/test_results_abcdefghijk.txt
- SAU A1: `cd ~/claude_master/w3/fx/g3/code && python3 eval_g3.py --real I_HAVE_A1_PASS` -> out/eval_g3.{json,md}
## Ket qua test (run 2026-11-26T17:43:40Z)
```
PASS a_cost_rule_EUR rt=6.400e-05 hand=6.400e-05
PASS a_cost_rule_JPY rt=3.000e-04 hand=3.000e-04
PASS a_cost_rule_GBP rt=3.000e-04 hand=3.000e-04
PASS a_cost_rule_AUD rt=6.000e-04 hand=6.000e-04
PASS a_cost_rule_CAD rt=3.000e-04 hand=3.000e-04
PASS a_cost_rule_CHF rt=3.333e-04 hand=3.333e-04
PASS a_cost_rule_NZD rt=1.200e-03 hand=1.200e-03
PASS a_quote_EUR long EUR vs USD ret=0.100000 hand=0.100000
PASS a_quote_JPY long JPY vs USD ret=0.250000 hand=0.250000
PASS a_quote_GBP long GBP vs USD ret=0.100000 hand=0.100000
PASS a_quote_CHF long CHF vs USD ret=-0.200000 hand=-0.200000
PASS a_quote_CAD long CAD vs USD ret=0.250000 hand=0.250000
PASS a_quote_AUD long AUD vs USD ret=0.100000 hand=0.100000
PASS a_quote_NZD long NZD vs USD ret=-0.100000 hand=-0.100000
PASS a_missing_is_nan 
PASS a_fake_cutoff_rows_dropped 
PASS b_entry_ge_T_plus_7_LevFunds_TFF_W52 
PASS b_window_published_before_entry_LevFunds_TFF_W52 
PASS b_entry_ge_T_plus_7_LevFunds_TFF_W156 
PASS b_window_published_before_entry_LevFunds_TFF_W156 
PASS b_entry_ge_T_plus_7_AssetMgr_TFF_W52 
PASS b_window_published_before_entry_AssetMgr_TFF_W52 
PASS b_entry_ge_T_plus_7_AssetMgr_TFF_W156 
PASS b_window_published_before_entry_AssetMgr_TFF_W156 
PASS b_entry_ge_T_plus_7_NonComm_LEG_W52 
PASS b_window_published_before_entry_NonComm_LEG_W52 
PASS b_entry_ge_T_plus_7_NonComm_LEG_W156 
PASS b_window_published_before_entry_NonComm_LEG_W156 
PASS b_causal_NonComm_LEG_W52_T0_1995-06-13 book_same=True tranches_same=True later_changed=True
PASS b_causal_NonComm_LEG_W156_T0_1995-06-13 book_same=True tranches_same=True later_changed=True
PASS b_causal_NonComm_LEG_W52_T0_2001-09-11 book_same=True tranches_same=True later_changed=True
PASS b_causal_NonComm_LEG_W156_T0_2001-09-11 book_same=True tranches_same=True later_changed=True
PASS b_causal_LevFunds_TFF_W52_T0_2008-10-07 book_same=True tranches_same=True later_changed=True
PASS b_causal_LevFunds_TFF_W156_T0_2008-10-07 book_same=True tranches_same=True later_changed=True
PASS b_causal_AssetMgr_TFF_W52_T0_2008-10-07 book_same=True tranches_same=True later_changed=True
PASS b_causal_AssetMgr_TFF_W156_T0_2008-10-07 book_same=True tranches_same=True later_changed=True
PASS b_causal_NonComm_LEG_W52_T0_2008-10-07 book_same=True tranches_same=True later_changed=True
PASS b_causal_NonComm_LEG_W156_T0_2008-10-07 book_same=True tranches_same=True later_changed=True
PASS b_causal_LevFunds_TFF_W52_T0_2013-10-08 book_same=True tranches_same=True later_changed=True
PASS b_causal_LevFunds_TFF_W156_T0_2013-10-08 book_same=True tranches_same=True later_changed=True
PASS b_causal_AssetMgr_TFF_W52_T0_2013-10-08 book_same=True tranches_same=True later_changed=True
PASS b_causal_AssetMgr_TFF_W156_T0_2013-10-08 book_same=True tranches_same=True later_changed=True
PASS b_causal_NonComm_LEG_W52_T0_2013-10-08 book_same=True tranches_same=True later_changed=True
PASS b_causal_NonComm_LEG_W156_T0_2013-10-08 book_same=True tranches_same=True later_changed=True
PASS b_causal_LevFunds_TFF_W52_T0_2016-06-21 book_same=True tranches_same=True later_changed=True
PASS b_causal_LevFunds_TFF_W156_T0_2016-06-21 book_same=True tranches_same=True later_changed=True
PASS b_causal_AssetMgr_TFF_W52_T0_2016-06-21 book_same=True tranches_same=True later_changed=True
PASS b_causal_AssetMgr_TFF_W156_T0_2016-06-21 book_same=True tranches_same=True later_changed=True
PASS b_causal_NonComm_LEG_W52_T0_2016-06-21 book_same=True tranches_same=True later_changed=True
PASS b_causal_NonComm_LEG_W156_T0_2016-06-21 book_same=True tranches_same=True later_changed=True
PASS b_causal_LevFunds_TFF_W52_T0_2019-06-04 book_same=True tranches_same=True later_changed=True
PASS b_causal_LevFunds_TFF_W156_T0_2019-06-04 book_same=True tranches_same=True later_changed=True
PASS b_causal_AssetMgr_TFF_W52_T0_2019-06-04 book_same=True tranches_same=True later_changed=True
PASS b_causal_AssetMgr_TFF_W156_T0_2019-06-04 book_same=True tranches_same=True later_changed=True
PASS b_causal_NonComm_LEG_W52_T0_2019-06-04 book_same=True tranches_same=True later_changed=True
PASS b_causal_NonComm_LEG_W156_T0_2019-06-04 book_same=True tranches_same=True later_changed=True
PASS b_handcheck_2008_10_naive_z rows=10
PASS c_exceptions_le_cutoff_n 15
PASS c_all_listed_pub_gt_T6 
PASS c_excluded_LevFunds_TFF_W52 rows=105
PASS c_excluded_LevFunds_TFF_W156 rows=105
PASS c_excluded_AssetMgr_TFF_W52 rows=105
PASS c_excluded_AssetMgr_TFF_W156 rows=105
PASS c_excluded_NonComm_LEG_W52 rows=105
PASS c_excluded_NonComm_LEG_W156 rows=105
PASS c_rule_T6_kept_T7_excluded 
PASS c_late_report_not_in_window_before_pub n_win next=51 (no-ex 52), after=52
PASS d_hand_z_t4 1.161895
PASS d_hand_z_t5 1.460778
PASS d_short_window_nan 
PASS d_cover_W20_missing1 n_win=19
PASS d_z_matches_hand_W20 
PASS d_cover_W20_missing2 n_win=18
PASS d_cover_W52_missing2 n_win=50
PASS d_z_matches_hand_W52 
PASS d_cover_W52_missing3 n_win=49
PASS e_net_position_H4 {'2010-01-12': 0.125, '2010-01-19': 0.25, '2010-01-26': 0.125, '2010-02-02': 0.125, '2010-02-09': 0.125, '2010-02-16': 0.0, '2010-02-23': 0.125, '2010-03-09': 0.0}
PASS e_net_position_H1 {'2010-01-12': 0.5, '2010-01-19': 0.5, '2010-01-26': -0.5, '2010-02-02': 0.0, '2010-02-09': 0.5, '2010-02-16': 0.0}
PASS e_cost_netting net=0 gross=-1e-05
PASS e_cost_entry 
PASS e_no_netting_hand_H4 {'2010-01-12': np.float64(1.0), '2010-01-19': np.float64(1.0), '2010-01-26': np.float64(1.0), '2010-02-02': np.float64(-0.0), '2010-02-09': np.float64(2.0), '2010-02-16': np.float64(1.0), '2010-02-23': np.float64(1.0), '2010-03-09': np.float64(1.0)}
PASS e_cost_x2 
PASS e_ND_flips_sign 
PASS f_spy_only_train_seen calls=9
PASS f_wfo_change_no_dir_change_2013_LevFunds_TFF (('H_TD', 0.05473954726405754), ('H_TD', -0.059969664882081594))
PASS f_wfo_change_no_dir_change_2013_AssetMgr_TFF (('H_TD', 0.0555238991438271), ('H_TD', -0.0608972701335892))
PASS f_wfo_change_no_dir_change_2013_NonComm_LEG (('H_TD', 0.055465234095350986), ('H_TD', -0.0002809160417215675))
PASS f_wfo_change_no_dir_change_2006_LEG (('H_TD', 0.055465234095350986), ('H_TD', -0.06425888832386716))
PASS g_refuse_cutoff_2020-01-01 
PASS g_refuse_cutoff_2021-06-30 
PASS g_refuse_cutoff_2026-10-31 
PASS g_real_max_date_le_cutoff 2019-12-31
PASS g_sim_real_locked 
PASS g_sim_bad_token_refused 
PASS h_cont dirs={'LevFunds_TFF': 'H_TD', 'AssetMgr_TFF': 'H_TD', 'NonComm_LEG': 'H_TD'} groups={'LevFunds_TFF': 'DAT', 'AssetMgr_TFF': 'DAT', 'NonComm_LEG': 'DAT'} combined=DAT p=0.002 sharpe=4.27 (53s)
PASS h_rev dirs={'LevFunds_TFF': 'H_ND', 'AssetMgr_TFF': 'H_ND', 'NonComm_LEG': 'H_ND'} groups={'LevFunds_TFF': 'DAT', 'AssetMgr_TFF': 'DAT', 'NonComm_LEG': 'DAT'} combined=DAT p=0.002 sharpe=2.83 (47s)
PASS h_noise dirs={'LevFunds_TFF': 'H_ND', 'AssetMgr_TFF': 'H_ND', 'NonComm_LEG': 'H_ND'} groups={'LevFunds_TFF': 'KHONG DAT', 'AssetMgr_TFF': 'KHONG DAT', 'NonComm_LEG': 'KHONG DAT'} combined=KHONG DAT p=0.836 sharpe=-0.76 (47s)
PASS i_deterministic len=32586
PASS i_nrand_lt_500_refused 
PASS j_fake_ecu_dropped [Timestamp('2005-01-04 00:00:00')]
PASS j_fake_x 
PASS j_fake_gbp_3names_merged 
PASS j_fake_tff_x 
PASS j_fake_post_cutoff_cot_dropped 
PASS j_real_eur_from_1999 1999-01-05
PASS j_real_ecu_rows_dropped dropped=10
PASS j_real_GBP_names_merged BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE | BRITISH POUND STERLING- NEW - INTERNATIONAL MONETARY MARKET | POUND STERLING - CHICAGO MERCANTILE EXCHANGE | POUND STERLING - INTERNATIONAL MONETARY MARKET
PASS j_real_AUD_names_merged AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE | AUSTRALIAN DOLLARS - CHICAGO MERCANTILE EXCHANGE | AUSTRALIAN DOLLARS - INTERNATIONAL MONETARY MARKET
PASS j_real_NZD_names_merged NEW ZEALAND DOLLAR - CHICAGO MERCANTILE EXCHANGE | NEW ZEALAND DOLLARS - CHICAGO MERCANTILE EXCHANGE | NEW ZEALAND DOLLARS - INTERNATIONAL MONETARY MARKET
PASS j_real_gbp_continuous_across_renames 11 days 00:00:00
PASS k_threshold_1_5 
PASS k_d9_150 
PASS k_perm_p_plus1 
PASS k_swap_sign_+1 swap=7.778e-04 hand=7.778e-04
PASS k_margin_single_+1 
PASS k_swap_sign_-1 swap=-7.778e-04 hand=-7.778e-04
PASS k_margin_single_-1 
PASS k_margin_per_tranche_H4 tot=-3.8889e-04 hand=-3.8889e-04 day=-1.0417e-05
PASS k_margin_x2 
PASS k_close_at_cost 
PASS k_data_end_close_cost 
PASS k_random_keeps_sign_mix n=1421 short=660
PASS k_block_shift_same_count_per_ccy 
TOTAL 123 FAIL 0
```
## Dem |z|>=1.5 du lieu that (<= 2019-12-31; chi dem, khong loi suat)
```
group,W,period,eligible_ccy_weeks,n_absz_ge_1_5,per_ccy
LevFunds_TFF,52,train,2047,505,AUD:55;CAD:75;CHF:76;EUR:75;GBP:85;JPY:68;NZD:71
LevFunds_TFF,52,wfo,2450,594,AUD:89;CAD:76;CHF:84;EUR:90;GBP:89;JPY:86;NZD:80
LevFunds_TFF,156,train,1355,175,AUD:10;CAD:21;CHF:32;EUR:28;GBP:44;JPY:33;NZD:7
LevFunds_TFF,156,wfo,2450,441,AUD:65;CAD:67;CHF:72;EUR:56;GBP:45;JPY:63;NZD:73
AssetMgr_TFF,52,train,2047,519,AUD:70;CAD:92;CHF:57;EUR:74;GBP:78;JPY:82;NZD:66
AssetMgr_TFF,52,wfo,2450,743,AUD:83;CAD:110;CHF:115;EUR:100;GBP:83;JPY:107;NZD:145
AssetMgr_TFF,156,train,1355,223,AUD:47;CAD:31;CHF:19;EUR:15;GBP:27;JPY:84
AssetMgr_TFF,156,wfo,2450,752,AUD:65;CAD:84;CHF:136;EUR:154;GBP:83;JPY:81;NZD:149
NonComm_LEG,52,train,2611,462,AUD:108;CAD:114;CHF:51;EUR:43;GBP:112;JPY:34
NonComm_LEG,52,wfo,4935,1269,AUD:164;CAD:178;CHF:165;EUR:235;GBP:217;JPY:168;NZD:142
NonComm_LEG,156,train,2149,396,AUD:54;CAD:97;CHF:51;EUR:36;GBP:101;JPY:57
NonComm_LEG,156,wfo,4863,971,AUD:148;CAD:120;CHF:112;EUR:179;GBP:133;JPY:166;NZD:113
```
## sha256
```
34dccc35365a55cb57cee13cf8758c9287900a4ff7e4589825b07f510920f64c  code/eval_g3.py
15a2b28c9aed210d0cf06fe24cc2814047e494f7a0494269449e2283116eebf4  code/load_g3.py
079224ef49116f958e7d7b6a66f1a61d9d46f071852523225781de14f77f3e66  code/sig_g3.py
9244cc6eba5e937157870d1f5495566053d62e82ff2d3c9fedcafd1b288e66c9  code/sim_g3.py
a35f2d11f526f2292bf9c71eebfc63d664da1f760062884f8dc5c39b51ad6734  code/test_g3.py
2749a96097ca73efd3bb5f74d3fadd241da957d0dfa758c8c904d67b21655b9e  CHOICES_G3.md
```
