# A1_B3_CODE - audit doc lap code LEVZ B3 (PREREG 30a8c413 + ERRATA1 308cd1fc) - 2026-11-26
Auditor A1 (khong phai DEV). Khong train / cham tren du lieu that; khong xem tuong quan nhan-dac trung, khong xem loi nhuan.
Script + log cua A1: /tmp/tmp.75uXBHRUPo (a1_struct.py, a1_feat.py, a1_lab.py, a1_doi.py, mk.py, drv.py, mut.log).

## KET LUAN (tam): PASS-WITH-MINOR - KHONG co loi CHAN; 7 mutant tang model/wfo dang chay (xem muc 5)

## 1. Doi chieu prereg + ERRATA1 (tu doc code)
- Pool: B0 sim.candidates E0, pxok = has1m B1, chi doi z_min 1.5; hoi quy z>=2.5/3.0/3.5 == cand_b1 (cand_b3.py:146-158) - DUNG.
- Dot + trong so: A1 dung lai partition bang code rieng: trung 100 % (2 730 dot), w = 1/size dung.
- exit_Y: A1 tinh lai tu grid_b1.parquet (W7 E0, 1 755 dong, median 9 cau hinh): 2024 = SL .5 / H 336 / arm .03 / gap .02 (hoa voi
  H 720, score 0.241872 -> H ngan); 2025 = SL .3 / H 24 / arm .07 / gap .02 (score 0.273734, khong hoa). TRUNG out/exitsel_b3.json.
  Cot dung: F1_ret (2024), F1_ret + F2_ret (2025); FOLDS B0: F1 2022-01..2024-01, F2 2024-01..2025-01 => khong nhin truoc.
- Nhan: A1 tu tinh (1-xr) - .0007 - .0007 xr + fund tu exits.npz B1 tren 7 936 dong trung: lech 0 (ca 2 exit); == port._net/N
  (port.py:122-124). NaN 0/0; j <= 60 H moi dong.
- Purge WFO (cand_b3.py:204-209): k <= k0(Y) - H - 24. Do A1: 0 lenh train cham sang nam Y; khoang cach k train cuoi -> dau Y:
  385 h (2024), 92 h (2025); 0 dot vat ngang train/test; 0 dot bi cat trong so.
- CV (cv_b3.py:44-52): purge HAI dau dung ERRATA1; dot chung val/train ngoai dai: 7 dot / 110 ung vien tong 12 fold (H 24), 0 (H 336).
- C0: so dem khop ERRATA1 (500 / 2 297). M1/M2 tham so dung muc 5 (model_b3.py:12-15). T20/T10/T0, BL_S20, BL_Z30, RAND (cung pool
  ite, cung exit xl, cung port K5, p_keep = n chon CHINH / n pool Y), Q1..Q8, C1..C3, verdict, nhan canh bao trong report: DUNG.
- Khoa chan: wfo_b3 / cv_b3 assert token truoc khi doc du lieu (da thu: AssertionError). work/ + out/ + logs/: KHONG co model / diem /
  ledger / wfo / cv; find toan ~/claude_master sau prereg: khong co file wfo_b3*/cv_b3*/report_b3*/ledger nao.

## 2. Nhan qua - kiem doc lap
- 22 dac trung (z_oi, z_f, f, s, df24, lr1, lr24, lr168, rv24, rng24, dhi168, dlo168, lqv24, qvratio, liqrank, levrun, ncand7d,
  frac_lev, frac_pool, ncand_hour, btcvol7, doi24) x 150 ung vien ngau nhien (seed 424242), code rieng (pandas theo t, close1m cho lr,
  doc OI rieng): lech tuong doi lon nhat = 0 o CA 22. Lech NaN: lr* 2/150 (close1m ffill vs px NaN - nguon khac, dung), doi24 1/150
  (dong OI h=2024-01-01 nam o file thang 2023-12 theo tsr; DEV dung, reader A1 sai). age: 87 coin niem yet sau 2022-01-15: lech 0.
- Quy uoc gio: px dong k = nen dong tai T_k; sig dong k = T_k; OI doc tai tsr <= T_k - 10 phut (do: dung 10 phut); f = r8 cua lan
  settle gan nhat <= t - 1 phut. Vao lenh = close 1m bar mo T_k. => khong dung nen chua dong.
- Cat ngang (liqrank, frac_lev, frac_pool, ncand_hour): chi dung dong k.
- EW3/7/14, BTC7/20: KHONG tu tinh lai (chi dua vao assert DEV == mkt.npz B2 da audit).

## 3. Ro ri
(i) purge WFO: sach (so o muc 1). (ii) OOF khong purge giua quy: Y=2025 31/2 297 dot (725 ung vien, 2.9 %) trai >1 quy, 5.9 % ung
vien trong +-48 h quanh bien quy; H=24 => nhan chong lan rat it. Anh huong len T20/T10 (phan vi diem OOF) khong dang ke; KHONG can sua.
Y=2024 (mo ta) 9.6 % trong +-360 h. (iii) dot vat bien nam: 0; vat bien quy: nhu (ii). (iv) C2 nguong toan khoang: dung nhu ERRATA1.
(v) Khong co nhan / gia sau gio vao trong dac trung hay loc; ngoai le da biet: pool (va ncand_hour) dung has1m tai T_k (bar vao lenh,
quy uoc B1) - do: anh huong 0 / 28 864 dong. (vi) RAND: cung pool / exit / danh muc - dung.

## 4. Loi / ghi nhan (khong co CHAN)
NHO-1 test_b3 khong bao phu tang model/wfo (trong so, p_keep RAND, Q5, nguong, BL, nhom OOF) - xem mutant. De nghi them unit test
      truc tiep cho tung cong thuc.
NHO-2 test b_regression kiem nhan bang chinh label_of (tu tham chieu) - doi dau trong label_of chi bi bat vi file cu con. De nghi
      so voi port._net/N.
NHO-3 GroupKFold theo quy lech kich thuoc (2025: val 9 193 / 6 299 / 4 530 / 2 678 / 2 594; fold 4 gom 8 quy 2022-2023Q3+2024Q3).
NHO-4 report_b3 thieu exit_Y day du (SL/arm/gap) va so ung vien / dot / nam (prereg muc 3, 9) - them tu exitsel_b3.json / cand_b3.json.
NHO-5 age: coin co tu truoc 2021-01-01 bi chan duoi trong 2022 (chi anh huong 2022).
NHO-6 Token mo khoa nam ngay trong DEV_B3.md - chi la ky luat quy trinh; khong co dau vet chay that.
NHO-7 T20 = phan vi KHONG trong so (CHOICES #18) - trung tinh, chap nhan.
CHOICES #1-#27: khong thay lua chon trai prereg hay lam dep ket qua (#3 sum == compound; #4 hoa dung luat).
Logging: 0 print. Tat dinh: seed LGB 0..9 deterministic, RAND / boot co seed; g_determinism PASS. NaN: LGB native, M2 -> 0.5.

## 5. test_b3 chay lai (ban copy khong sua, khong ghi out/): 8/8 PASS (a_causal 34 s, f_fake 304 s).
Mutant (copy tam, sua 1 dong):
 m01 lr dich +1h: BAT (200/200) | m02 liqrank gom gio k+1: BAT (65/200) | m03 frac_lev k+1: BAT | m04 doi24 k+1: BAT |
 m05 age +1 ngay: BAT (do crash IndexError) | m06 bo purge WFO: BAT (c_purge; e_groupkfold LOT) | m07 CV purge 1 dau: BAT |
 m08 doi dau nhan: BAT (b_regression, xem NHO-2) | m09 dot gap >= -> >: BAT |
 m10 bo trong so, m11 RAND p_keep=1, m12 Q5 bo lenh te nhat, m13 OOF nhom theo dot, m14 tap test chong train, m15 T20 = q20,
 m16 BL_Z30 = 2.5: DANG CHAY (test f ~5 phut/mutant) - ket qua o /tmp/tmp.75uXBHRUPo/mut.log.

## 6. CHUA kiem
EW/BTC dac trung (chi dua assert DEV), z_oi/z_f/z_r goc (lay tu sig B0 da audit), 12 dac trung con lai (lr4, lr72, rv168, zdiff, z_r,
age ngoai mau, ew*, btc*), engine exits B1 (da audit o B1), S.metrics (pnl_Y, maxdd_worst) cua B0.

## Vong 1 - ket qua mutant tang model/wfo voi test CU (m10-m16)
m10 bo trong so: LOT | m11 RAND p_keep=1: BAT | m12 Q5 bo nham: LOT | m13-m16: A1 dung giua chung (thay bang vong 2 tren code moi).
Thu muc tam vong 1 /tmp/tmp.75uXBHRUPo: DA XOA.

## Vong 2 (sau khi DEV sua 5 muc NHO) - 2026-11-26
(i) DIFF that so voi ban A1 da audit: model/feat/cand/labels/common/exitsel KHONG doi. wfo_b3: tach split_masks, bl_s20_thr, bl_z30_mask
   (BLZ = 3.0), rand_p_keep, rand_pvalue, drop_top5, oof_fold_sizes; cv_b3: span_mask, span_thr, c1_count, c2_pass, c3_pass. Doc tung
   dong: cung cong thuc (nguong q0.80, p_keep = n chon / n test, p = mean(rr >= main), Q5 bo ceil(5 %) net LON nhat, train/test nhu cu +
   assert tm & te rong, span_thr tren span & finite == isp cu; s luon finite). Assert `not tm[ite].any()` va khoa `--real` con nguyen.
   report_b3: them counts_block, kich thuoc OOF fold, 10 nhom M1+M2, 8 bien the lan can - chi doc json, khong doi verdict.
   test b: nhan so voi port._net/N (khong con tu tham chieu). DEV_B3.md: het token. CHOICES #28, #29 hop ly.
(ii) Toan bo 11 test tren ban copy hien tai (A1, khong ghi out/): a_causal, a_px_timing, b_regression, c_purge, d_dots, e_groupkfold,
   h_weights, i_wfo_formulas, j_cv_formulas, g_determinism, f_fake_pipeline (nrand 100): 11/11 PASS. out/test_report.json cua DEV (16:14):
   11/11 PASS.
(iii) Mutant tren code moi (test h, i, j, e):
   n10 bo sample_weight trong fit_m1: BAT (h) | n11 p_keep=1 o cho goi: BAT (i) | n11b rand_p_keep tra 1: BAT (i) | n12 Q5 bo net nho nhat:
   BAT (i) | n12b drop_top5(-net): BAT (i) | n13 nhom OOF theo dot: BAT (h) | n14 tap test chong train: BAT (h, i) | n15 T20 = q0.20: BAT (i)
   | n16 BLZ = 2.5: BAT (i) | n17 p-value dung >: BAT (i) | n18 WFO truyen trong so = 1: BAT (h) | n19 CV C2 nguong q0.70 trong
   portfolio_check: LOT (j chi test ham span_thr, khong test cho goi) => NHO-8.
(iv) work/: pool_b3.npz, labels_b3.npz, feat_b3.parquet; out/: 4 json dem + test_report.json. find ~/claude_master: khong co
   wfo_b3*.json / cv_b3*.json / report_b3* / ledger / .lgb / .pkl ngoai code/.

NHO-8 (moi): cv_b3.portfolio_check khong co test noi day cho nguong C2 (n19 lot). Doc code: dung (span_thr(oof, D.k)). De nghi them 1
   assert trong test j: portfolio_check tren fake tra thr == span_thr(oof, k). Khong chan.

KET LUAN CUOI: PASS-WITH-MINOR (khong loi CHAN). sha256 ban da audit:
aa62028914a7c79c917957e0d1495dcea2d6047272845925681073ceb9c208f4  code/cand_b3.py
687f14bc8058b8f56f7d90eb80983734253067cbc6ed128298d30c27c3a4832e  code/common_b3.py
61c4a88447638c15f5e3f7abcfca1ca105e7d5fd4ac3e1dbb58441e043e4a477  code/cv_b3.py
b1802505374ab118245994b2a54be62fc552c9dd6c70fa4716e309ca7ba86821  code/exitsel_b3.py
b809e857fa65493a7dd1a510b41b7b54641b63715f29227bbca51c16ed8d72a7  code/feat_b3.py
2b8f56c698a3f5969308fa268f16127b18cd7a5cb34a00d87ffe6ed3a8a2054b  code/labels_b3.py
ff5a1f196ed7f76f6007d6cb70db0a85df6ca2686a5d8fb194f53ea75158674d  code/model_b3.py
418654bc393233857a9bda15550ab15edb3ab2a69418b0c3c5df202064da36e5  code/report_b3.py
f436a168c22f71956fa9e8295e5c1e16c48e0bb010d3b0a6ab1d3706084eb81e  code/test_b3.py
119b845499c39ec79c05ca0b4fee1aada87c47dab6b9eb3073bed631c8269d4f  code/wfo_b3.py
68f1070291c1ca9a837e2a0bc83c4e3f66531c0cfcd1db6ec533609d75f73866  code/heavy.sh
Thu muc tam vong 2 /tmp/tmp.RYPVhUMuS9: DA XOA sau ALLDONE.
