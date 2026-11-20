# RESULT_GRIDV2_S2 (ASCII) - engine muc giao dich, o S_COND_A_c0.2_k2. Chay 2026-11-21. Agent chay; KHONG dien giai vuot luat.
## 1. Tuan thu
- Prereg PREREG_GRIDV2_S2.md (56eddec8; + muc 18); mau commit 6dfd2453 (PREREG_GRIDV2_S2_SAMPLE.md), sha256 sample.csv
  5bb7b139a3dcf2f3d1f208609ca5dd7a84805ee717f23428777ae26802d95ad5 (khong tao lai). EXPECTED_SHA b852e849...; 13/13 file code khop o
  moi lan kiem (s2run/sha_checks.log: 4 lan: truoc khoi dong, xac nhan, truoc khoi dong lai, truoc run_s2 x2).
- Kernel: 5 kernel gridv2-s2-events0..4, 7 dataset allowlist, 0 chay lai; validate all_pass 5/5, E1a ok.
- Fetch: 6604 cum, 7950 file duy nhat (7962 ban ghi files.jsonl; 12 trung do restart), 28,35 GB zip, 0 thieu, 0 thay the, 0 loi checksum.
  fetch_reduce chay that: nice 15, --batch 10, workers 6, khong --base-url. 2 lan khoi dong: lan 1 dung sau 12 lo vi RSS dinh 3,99 GB
  > nguong 3 GB (MASTER nang len 6 GB); lan 2 (restart tu checkpoint) hoan tat 661 lo, RSS max 3734 MB, watchdog khong vi pham, ~58 phut.
- Bang kiem: W0_events PASS (5 shard all_pass, prereg_constants); W0_fetch PASS (7962 file, 0 bad); E1b PASS (max_abs 2.9e-11);
  W1 PASS (6604 chon, 6604 done, 0 subs); W6 PASS (A 0/3307, B 0/3297 thieu); W2 PASS (3.258.940 phut; low&high bang 0,99934;
  open/close 0,98755; 142 phut lake hop le khong co giao dich; 256 phut co giao dich ma lake khong hop le); W3 PASS (24644 don vi;
  K_OPT agree_all 0,99988 dM_B -0,068 dM_A -0,0005; K_PESS 0,99992 dM_B -0,002 dM_A -0,0005); W4 PASS (549 full / 708 out, 0 lech);
  W5 PASS (612 don vi, mismatch_ref 0, mismatch_replay 0). Muc 18: (c) PASS (moi url bat dau https://data.binance.vision/; ngay < 2026);
  (d) PASS (n_outside_day != 0: 0; cum 100% excl: 0; excl rate 0); (e) PASS (done-ok == chon \ missing U subs; 0 subs); (i) bao cao:
  tong id_gaps 66788; 20/7962 file (0,251 %) co id_gaps > 0 (> 0,1 % => NGHI VAN muc (i), khong chan); n_time_back 0; us_converted 0.
  Cac script (s2run/checks/extra_checks2.py) chi in dem, chay TRUOC run_s2; ket qua 100% don vi khong excl.
## 2. Luat
run_s2: rule = L2-C ; label = L2-C (L2-A-INFRA khong ap). weighted_rule_core = L2-C. Tu doi chieu tay: TL_THROUGH khong PASS (nua B M -9,12, p 0,998
  khong dat (a): p <= 0,04 va M_B > 4; (b) M_A -2,44 < 4; (c) M_adj_C4_B -11,99 <= 0; (d) -10,32; (e) -9,59/-2,87) ; TL_TOUCH khong PASS
  (M_B -1,19, p 0,93; M_A 5,92 nhung p_A 0,2585 > 0,10; (c) -4,12; (d) -2,29) => L2-C (ca hai khong PASS). Khong INSUFFICIENT.
  result_s2.json: TEST_ONLY False, alpha_B 0,04, alpha_A 0,10, B 2000, seed 2026112160, W_all_pass true.
## 3. Bang (bps; units: n dat / khop; P(khop); M; SE; t=M/SE; p; CI95; gross; phi; truot; funding; M_adj_C4; M bo top3; M bo 3 su kien; M maker0,04; INS)
THROUGH A: 11968/8422; 0,7037; -2,44; 2,98; -0,82; p 0,972; [-8,20; 4,15]; gross 4,97; fee 4,89; slip 2,37; fund -0,15; adj -4,63; top3 -3,87 (NEAR,QTUM,RSR); ev -2,87; stress -5,84; INS no
THROUGH B: 12676/9089; 0,7170; -9,12; 4,03; -2,26; p 0,998; [-18,69; -1,42]; gross -1,34; fee 4,86; slip 2,63; fund -0,29; adj -11,99; top3 -10,32 (1000PEPE,FLUX,DOGE); ev -9,59; stress -12,55; INS no
TOUCH A: 11968/8541; 0,7137; +5,92; 2,91; 2,03; p 0,2585; [0,01; 12,12]; gross 10,10; fee 4,00; slip 0; fund -0,18; adj 3,66; top3 4,50; ev 5,22; stress 1,92; INS no
TOUCH B: 12676/9190; 0,7250; -1,19; 3,64; -0,33; p 0,9315; [-9,50; 5,56]; gross 3,09; fee 4,00; slip 0; fund -0,29; adj -4,12; top3 -2,29; ev -1,68; stress -5,19; INS no
THROUGH_LAT5S (chi bao cao) A: 11968/8421; M -2,51; SE 2,97; p 0,974; gross 4,91; adj -4,70; top3 -3,95; ev -2,94; stress -5,91
THROUGH_LAT5S B: 12676/9088; M -9,84; SE 3,97; p 1,0; CI [-19,42; -2,16]; gross -2,04; adj -12,70; top3 -11,04; ev -10,03; stress -13,26
Dieu kien PASS (a,b,c,d,e): tat ca false o ca 3 mo hinh; not_insufficient true. Hajek (chi bao cao): THROUGH A -2,45 / B -9,12; TOUCH A 5,91 (p 0,2555) -> cung ket luan L2-C.
## 4. Doi chieu S1 tren CUNG mau (nen 1 phut): K_OPT A 18,25 (n 8541) B 19,82 (n 9190); K_PESS A -5,96 (n 8422) B -13,68 (n 9089).
  W3 dong y 0,99988 / 0,99992. Phan ra kieu thoat (khop): kind 1 limit / 2 het han / 3 delist / 4 taker_beyond:
  THROUGH A 5912/2500/0/10; B 6473/2605/1/10. TOUCH A 6169/2372/0/0; B 6681/2508/1/0. LAT5S A 5894/2501/0/26; B 6440/2611/1/36.
  Ti le don vi K_OPT thoat cung phut khop va PnL duoi THROUGH: khong co (run_s2 khong xuat; khong tu tinh).
## 5. Theo nam / tier (M, chi bao cao)
THROUGH nam: 2021 +8,97; 2022 -5,41; 2023 -4,25; 2024 -5,54; 2025 -12,10. tier A: T1 +0,75 T2 +5,78 T3 -6,61; B: T1 +10,10 T2 -13,28 T3 -9,14.
TOUCH nam: 2021 +13,55; 2022 +4,73; 2023 +4,35; 2024 +0,75; 2025 -2,80. tier A: T1 +4,93 T2 +12,21 T3 +3,03; B: T1 +11,95 T2 -6,40 T3 -0,85.
## 6. Bat thuong / nghi van
- (i) 0,251 % file co id_gaps (20 file; tong 66788 id) > 0,1 %: nghi van muc (i), khong chan.
- 12 ban ghi files.jsonl trung (batch bi dung giua chung o lan 1, tai lai): khong lap hang trong res (res_dup_rows 0; 661 part == state.part).
- Khong co file thieu, khong checksum loi, n_time_back 0, khong doi tham so. RSS dinh vuot nguong ban dau (xu ly nhu tren).
- THROUGH n_excl = 0: khong don vi nao bi loai (khong lo > 60 phut).
## 7. sha256 + duong dan
result_s2.json: bf79f95f43a875551bd2a1734b69b37c308d5e26d0b5fa48625f0490f55b13b7 (~/claude_master/w3/gridv2/s2run/result/result_s2.json)
Khac: s2run/fetch/ (state.json, files.jsonl, res, bars, audit), checks/extra_checks2.json, sha_checks.log, fetch.log, run_s2.log.
