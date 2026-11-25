# A1_P15_STAB_S2 - audit doc lap cham Tang S2 (prereg PREREG_P15_STAB dea45002 muc 4)
Agent A1 (Opus), 2026-11-25. Doi tuong: RESULT_P15_STAB_S2.md (sha256 1c3da9fe...). Chi DEV; khong sim/mvn/java; khong 242; khong sua file RUN.
Code + so cua A1: a1/a1_light.py -> a1/a1_light.json ; a1/a1_mtm.py -> a1/a1_mtm.json (+a1_mtm.out) ; a1/a1_misc.py -> a1/a1_misc.json ; a1/a1_h0.py.
Code A1 KHONG import code RUN, khong import score_l5/gvz_mtm/reset_rule_score (tu parse printDone.csv + sim.out.gz + kline parquet).

## VERDICT: PASS-WITH-MINOR
(e) KHONG DAT - xac nhan. (f) KHONG DAT (CAGR22) - xac nhan ; DD22 DAT - xac nhan. Tong: E8 KHONG DAT S2 - dung luat.

## 1. Tuan thu prereg (doc code + so mtime)
- (e) s1_roi.py: sd ddof=1 giua 4 lap / quy ; DISP = trung vi 16 quy 2022Q1..2025Q4 ; nguong 0.6 x DISP(C0). Dung. (ti so DISP bat bien voi ddof.)
- (f) s5_verdict.py: mean4(cagr22 E8) - mean4(C0) >= -1.5 ; mean4(dd_mtm22) hieu >= -2.0. Dung.
- Thu tu: S0 khong-PnL 09:12:47 -> C1..C5 ghi 09:13:30 -> s3_mtm lan 1 dung 09:14 (log chi co LOAD, chua co RES) -> lua chon kline 09:15:43
  (= mtime s3_mtm.py) -> s1_roi.py mtime 09:17:05 / ket qua 09:17:16 -> MTM 09:17:52 -> verdict 09:19:49. Thu tu nhat quan. Gioi han: moc gio do
  chinh RUN ghi; A1 chi doi chieu mtime, khong chung minh duoc RUN chua nhin log kernel (dong RESULT) truoc do.
- s0_verify lan 1 so ca dict snapshot -> false gia, sua so sha truoc khi mo so tien: chap nhan (MINOR, da ghi).

## 2. Hop le lane (A1 tu kiem)
- 8/8 CHECK.json PASS, 0 truong False (33 khoa / lane).
- run.py kernel 8 lane vs template ho5-a3-rep4-s123: chi khac dong CFG ; trong CFG chi khac 5 khoa (tag, a3_ds, pred_ds, want_a3_sha, want_pred_md5).
  config.properties + prof_run.properties TRUNG BYTE giua 8 lane va voi ho5-a3-rep4-s123. dataset_sources giong nhau tru s2-a3-<lane>.
- md5 lane/<l>/pred.bin == LANE.json == want_pred_md5 == result.pred_md5_used (8/8) ; pred_md5_base = 5dd6bb4c (A1) ; n 2 500 260.
- Ghep A1: sha256 263 520 ban ghi dau pred.bin = 39d1316d... ca 8 lane (giong nhau). a3 sha concat == A3.json == want_a3_sha (8/8) - CHI so sha ghi lai
  (4 dataset a3 da xoa khoi Kaggle, bins local da xoa: khong tai kiem noi dung bins).

## 3. Tai tinh doc lap (so A1 vs RUN)
| muc | A1 | RUN | |d| |
|---|---|---|---|
| ROI D5 quy, 8 lane x 16 quy | tu parse | S2_roi_q.tsv | max 4.9e-5 pp (do lam tron 4 so le cua tsv) |
| DISP C0 / E8 / ti so | 0.9813 / 0.7122 / 0.7257 | 0.9813 / 0.7122 / 0.7257 | 0 |
| so quy sd_E8<sd_C0 ; trung vi ti so quy | 13/16 ; 0.5926 | 13/16 ; 0.5926 | 0 |
| CAGR22 8 lane (equity ngay sim.out, W0 2021-12-31 -> 2025-12-30) | khop | S3_mtm.json | 0.0 |
| mean CAGR22 C0 / E8 / hieu | 37.508 / 35.480 / -2.028 | idem | 0 |
| dd_mtm22 8 lane + gqsf-s7 (MTM phut code rieng) | khop | S3_mtm.json | <= 1e-5 pp |
| missing (thieu gia) | 0 ca 9 tag | 0 | - |
| n_trades | 3462/3585/3570/3452 ; 3607/3526/3534/3596 | idem | 0 |
| lenh khac nhau (sym,start,level), trung vi quy, TB 6 cap | C0 126.42 ; E8 76.75 (ca 12 cap khop tung cap) | idem | 0 |
- Nguon kline MTM (res1109/r1_s1/kl, 49 thang 2021-12..2025-12): phu du symbol/ngay cho 8 lane (missing 0 o code A1, kiem ca leg co NaN ca ngay).

## 4. Do vung (mo ta, khong doi luat)
(a) (e): ti so phu thuoc cach tong hop: ti so trung vi-sd 0.726 ; mean-sd 0.588 ; RMS-sd 0.519 ; trung vi ti so quy 0.593 ; TB hinh hoc ti so 0.607 ;
  trimmed mean 0.696 ; leave-one-quarter-out 0.698..0.755. Bootstrap theo quy (20 000): CI95 [0.41; 1.08], P(ti so <= 0.6) = 0.33.
  Bootstrap lan lap (4 lap / ho): CI95 [0.30; 1.57]. Hoan vi 35 cach chia 8 lane: 0.726 xep thu 6/35 (p ~ 0.17).
  => E8 co xu huong giam dao dong ROI quy (~25-45 %), chua phan biet ro voi nhieu; ket luan "khong dat" vung theo dung chi so ghi truoc,
  nhung mot so cach tong hop khac (mean/RMS/median-of-ratio) se cham sat hoac duoi 0.6 - KHONG duoc dung de dao ket qua (khong ghi truoc).
(b) (f) CAGR22: sd giua lap C0 2.19, E8 1.14 ; SE hieu 1.23 pp (Welch df 4.5) ; CI95 th? [-5.30; +1.25] ; P(hieu that >= -1.5) ~ 0.34 (t, prior phang) ;
  hoan vi 70 nhan: P(hieu <= quan sat) = 0.10. => -2.03 pp CHUA phan biet duoc voi 0 va cung chua phan biet voi -1.5 ; truot theo luat la
  dung, nhung "E8 kem hon 2 pp" la phat bieu qua muc bang chung. 4 C0 la thanh vien e8g1 (tuong quan duong e8g1 voi C0): khong lam lech diem uoc
  luong; bo e8g1 thi hieu = -2.30 pp. Sd CAGR22 E8 thap hon C0 (x0.52) - mo ta, cung chieu on dinh.
(c) Leg dong 07:00 +07 (00:00 UTC): 91-106 / lane do lop X14 (SIM_LOSER_TS_EXT_HOURS 336 + SIM_LOSER_TS_EXT_DAYS trong overrides template, giong
  r1-a3-s7 104, r1-a3-s123 / ho5-a3-rep4-s123 107): cum STOP_LOSS dong cung phut sau het cua so gia han (20211212: 23-26 leg, 20240421: 14-18,
  20220205, 20251020). gqsf-s7 (jar bcd, khong X14) chi 10. => KHONG phai dau hieu lane S2 sai; la khac biet ho template (r1-a3/ho5) vs gqsf.
  Tac dong: code A1 tinh MTM 2 bien the (LEG = mo phong loi legacy bo pnl leg dong 00:00 UTC trong ngay do ; FIX = ghi nhan tai m1): dd22 TRUNG NHAU
  ca 9 tag - maxDD22 moi lane la cung mot su kien (day 2022-05-12 07:17 UTC, LUNA) => loi 00:00 UTC anh huong DD22 = 0 ; doi xung C0/E8.
  Diem "khong chac" muc 7 RESULT duoc go bo. Luu y: DD22 thuc chat la do 1 su kien.
  Phu: Moi sim (ke ca baseline r1-a3 / gqsf) khong co lenh vao sau 2025-11-21 (end cuoi 2025-11-28) => 2025Q4 ~ 2 thang ; cua so MTM ket thuc 2025-11-28.
(d) CAGR22 C0-PROD 37.5 vs 37.0 cong bo (gqsf ISO_RISK OFF, jar bcd, khong X14): khong cung ho. So dung ho: r1-a3 8 seed cu (A1 tinh tu sim.out):
  mean 37.72, [34.94; 40.45] => C0 37.5 [35.0; 39.8] hop ly.
(e) n_trades, |A symdiff B| tu dem lai: khop RUN tung cap (C0 c0s42-c0s7 121, E8 e8g1-e8g2 73, ...).

## 5. Loi theo muc
- MAJOR: khong.
- MINOR: (1) Muc 7 RESULT de ngo tac dong 00:00 UTC len DD22 - A1 do = 0 (nen bo sung). (2) RESULT so voi baseline 37.0 (khac ho, khong X14);
  so dung ho la r1-a3 (37.7). (3) Toolcheck MTM dung gqsf-s7 (10 leg 00:00) - khong kiem nhanh 00:00 UTC; A1 da bu bang code rieng.
  (4) s0_verify sua phep so sau false gia (truoc so tien, da ghi). (5) 2025Q4 chi ~2 thang giao dich (chung moi ho) - nen ghi.
- Khong thay sai so lieu / sai luat.

## 6. Y KIEN A1 (y kien, khong phai ket qua)
- Ket luan "E8 KHONG DAT S2" dung luat. Phat bieu dung muc: "E8 giam dao dong ROI quy giua cac lan train ~27 % theo chi so ghi truoc (25-48 % theo cach
  tong hop khac; 13/16 quy), chua dat nguong 40 % ; tap lenh vao khac nhau giam ~40 % (126 -> 77 / ~170 lenh / quy) ; chi phi CAGR22 -2.0 pp
  [CI95 -5.3; +1.2] CHUA phan biet duoc voi nhieu (4 lap)". Qua tay: "E8 lam giam hieu nang 2 pp", "ensemble khong giup on dinh".
- Huong tiep (moi huong can prereg rieng; rui ro overfit ghi kem):
  1. Tang so lap (C0 8-16 seed, E8 8 nhom) truoc moi y tuong moi - de uoc luong hieu CAGR voi SE <= 0.7 pp. Rui ro thap; chi ton compute.
  2. On dinh o tang QUYET DINH: nguong gate theo quantile da on dinh (vd trung vi nguong cua K model, hoac nguong tren rank thay q0.99995 tuyet doi). Rui ro: chon
     nguong sau khi thay so -> pre-reg nguong.
  3. Giam phu thuoc duoi q0.99995: do on dinh tap pass theo q (0.9999 / 0.99995 / 0.99999) cho C0 vs E8 o tang S1 (khong PnL) truoc. Rui ro: doi q = doi
     chien luoc, phai so hieu nang rieng.
  4. Ensemble lon hon (E16/E32) chi khi (1) cho thay hieu CAGR ~0: ky vong giam sd ~1/sqrt(K) o diem nhung PnL con phu thuoc pool/S1 (khong giam theo K).
  5. Do nguon dao dong con lai: lane cung p15 nhung S1/pool rebuild khac -> tach phan dao dong do S1/A3 vs do p15. Rui ro thap, thong tin cao.
  6. DD22 chi la 1 su kien (2022-05-12): khong dung DD22 de chon ung vien; bo sung DD theo nam / CVaR ngay.

## 7. Diem KHONG kiem duoc
- Noi dung bins A3 + dataset s2-a3-* (da xoa): chi so sha ghi lai. S1 16 fold / ledger: khong tai tinh (ngoai pham vi S2 cham).
- Kernel Kaggle chay dung template: chi kiem run.py/metadata local + result.json/CHECK; khong co log Kaggle goc ngoai file tai ve.
- Khong chung minh duoc RUN chua xem PnL truoc khi ghi lua chon (chi mtime + progress do RUN ghi).
- Kline res1109 ~ Vision tai lai: A1 khong doi chieu voi file goc vz_e1/raw (da xoa); hop le hoa gian tiep qua gqsf-s7 tai lap.
