# A1_RETRAIN_DIAG - audit doc lap luot U4a chan doan tung model (PREREG_RETRAIN_DIAG 436977c1)
Doi tuong: v12/RESULT_RETRAIN_DIAG.md sha256 71f16779...3a3a (khop), score_lanes_U4a.json b6886751...ea6 (khop), DIAG_MASTER_DECISIONS_1121.md (TAM).
Auditor A1, 2026-11-21 ~21:40-22:30 +07. Chi doc + tinh lai; script + output: ~/claude_master/w3/retrain_audit/diag/ (a1_recalc.py/.json, a1_cmp.py,
a1_bins.py, a1_bins2.py, a1_seed.py, a1_dcal.py, a1_c.py, a1_c2.py). Moi script chi doc du lieu 2026 trong pham vi U4a (HOLDOUT_UNSEAL_2026_1121 U4a),
assert max ts < 2026-10-01 00:00 +07. Khong ghi gi vao w3/retrain, vz_e1_wt.

## PHAN QUYET: PASS-WITH-MINOR (kem 1 MAJOR ve DIEN GIAI - phai sua cau chu truoc khi commit; KHONG doi quyet dinh B5)

## Bang tung muc
| muc | ket qua | bang chung |
|---|---|---|
| A1 CO CHE truoc PnL | PASS | RESULT hien tai la append-only: sha256(67 dong dau) = 332aea23 (CO CHE, .progress 17:11:58), sha256(80 dong dau) = 6a8f0631 (CO CHE-2, 18:12:50). Output lane dau tien tai 17:38:36 (fetch_p_a1.log) > 17:11:58. score --allow-pnl 18:12:56 > CO CHE-2. Nguong B1 1,2/0,83 + 0,25, B2/B3 CI80, B4 10 % = van ban muc 8 P5; khong doi. Mau thuan B3-vs-B5 da ghi trong CO CHE (dong <= 67) TRUOC PnL. |
| A2 du lieu >= 10-01 | PASS | pred 2026 n=393120 (= 273 ngay), ts max 2026-09-30 16:59 UTC; bins 0701 L/N/S/M ts max 1790786700000 < S4; market ts_last 1790787540000; Update log max 20260930; printDone max end < 10-01 (assert 16 run). Ruler: tmax = S4-4h / S4-72h / S4-1d; file nhan 'funding_label_20260701_to_20261001' doc nhung loc. Khong tham chieu gs-*-q4 / Q4 trong code lane/diag/score. |
| A3 thu tu lane cap | PASS | quy ket cham 18:12:56; DATA26_PS/PM/SM 18:13:28-30; dong P2 18:15:10; PUSH ps 18:16:19. Khong lane cap nao truoc quy ket don. |
| B1 so lieu lane | PASS | a1_recalc.py doc printDone + 'Update' (E=b+unP) + GATE-RATIO, khong dung ham cham cua luot chay. 8 lane x 2 seed: sai lech ROI D5 max 4e-16 pp, n lenh 0, lenh chung 0, PnL chung/chi-o-lane 0, maxDD 0, thang khop. |
| B2 lane dung du lieu | PASS (rt_lchk co lo hong - MINOR) | inode hard link + result.json ho5.pred.md5: P/PS/PM = pred N (9dc04316 a1 / e43ac27b s123), S/M/SM = pred L; bins0701: P=L 9a914693, S/PS=aafc6266, M/PM=ea20967b, SM=N bb64cde3; 0101/0401 = L. a1_bins.py: S multiset/tick == L va top24/tick == N (8832/8832); M multiset == N va top24 == L (8832/8832); p1-p3 toan NaN (khong anh huong). printDone end<07-01 trung L (3866 dong, rt_lchk). |
| B3 quy ket | PASS | Delta_tot -9,5642; P -3,5079 (36,7 %), S -0,4914 (5,1 %), M -2,3641 (24,7 %); tuong tac -3,2008; Shapley P -5,842 S +0,758 M -4,480; cap PS -0,011 PM -6,742 SM +0,424 - khop 1e-12. Bo sung: tuong tac bac 3 = +3,13 pp (RESULT khong neu). |
| B4 D-cal / D-gate / D-ruler | PASS (1 MINOR) | Q3 q99,99 ti so 1,1920 (khop 1,192), q99,995 1,509. Q2: run 0,9793, cua so DUNG (04-01..07-01 +07) = 0,9803 -> hang Q2 trong rt_dcal.py = 1775034000000 = 2026-04-01 16:00 +07 (lech 16 h; Q1 lan 16 h sang thang 4). Khong doi B1 (xa nguong 0,83/1,2). D-gate: pass/seen 2026Q3 8 lane khop log (L 94/3041795, P 127/2962350, S 93/3035472, M 108/2994359, PS 128/2952806, PM 142/2898135, SM 108/2991437, N 142/2912910). D-ruler: RULER v1 == v2 cho p15/net015/S1 (chi dsrc_perm khac; v2 'none' IC duong khop ruler chinh) -> loi dau v1 chi anh huong D-src(b) mo ta, khong anh huong B2/B3. Nhan: ts < S4 - horizon. AUC/lift KHONG tinh lai (can nhan tren Kaggle). |
| B5 2 seed trung | PASS (do thiet ke) | Tap lenh Q3 (sym,start,end,status) trung 100 % giua a1/s123 o ca 8 lane; PnL s123/a1 = 0,99153 = ti le E_start -> chi khac quy mo von do DEV. Input khac that (pred md5 + src_md5 khac). Gate 2025Q4/2026Q1 pass trung, seen khac. => Q3 = 1 duong di duy nhat, KHONG co sai so lay mau. |
| C dien giai | MAJOR (dien giai) | xem phat hien M1. |
| D quyet dinh MASTER | PASS | Ca 2 cach doc cay deu ve 'giu live' (xem duoi). D-D2 can sua cau chu (M1). |

## Phat hien (theo muc do)
### MAJOR
M1 [dien giai, RESULT 'Doc co che + PnL' va DIAG_MASTER_DECISIONS D-D2] Cau 'thua lo do TUONG TAC p15 T1 x net015 T1 tai GATE' / 'Thua lo tap trung o
GATE' noi qua so lieu. Q3 la 1 duong di (B5), lenh tap trung vao 10-17 ngay, PnL moi lenh duoi nang (|pnl| max ~2,9k ~ 1,8 pp). Lenh chi-o-lane:
- NNN (a1): 129 lenh, -11 472; 3 lenh te nhat = -8 177 (71 %). Ngay 2026-07-27 (BANK): -5 854.
- PM (a1): 130 lenh, -15 543; tuong tac cap PM -6,74 pp ~ 2 'tap' coin: BANK 07-27 -> SL 08-03 (1 PREDICT 13:17 + 3 DCA_LEVEL1 07-27/07-31, tong ~-7 374
  ~ -4,6 pp) + LAB 07-08 (-2 936 ~ -1,8 pp). Trong lane P (p15 T1 + net015 live) BANK 07-27 khong vao; 07-31 20:46 P vao 10 lenh thang (+2,1k).
- DCA_LEVEL1 Q3: L 4 lenh -650; NNN/PM 10 lenh ~-4,8k -> mot phan lon lo di qua nhanh DCA (nhanh nguong p15 TUYET DOI theo prereg muc 1), khong chi gate rolling.
=> So lieu PHU HOP voi gia thuyet 'thang diem p15/net015 T1 lam pass gate o vai su kien', nhung KHONG du de noi 'thua lo do tuong tac tai gate' nhu ket
luan: bang chung = 1-2 su kien, khong CI, va mot phan qua DCA ladder. De xuat sua: 'Lo Lane N tap trung o 2 tap lenh (BANK 07-27..08-03 co 3 DCA,
LAB 07-08) chi xuat hien khi co ca p15 T1 + net015 T1; phu hop gia thuyet tuong tac thang diem tai gate/DCA; chua kiem, 1 duong di.'
Khong doi quyet dinh B5 (B5 khong dua vao cau nay); nhung D-D3 dang dinh huong nghien cuu theo cau nay -> prereg moi nen coi gate va DCA/nhanh
nguong tuyet doi la 2 gia thuyet canh tranh.
### MINOR
m1 rt_dcal.py hang Q2 = 1775034000000 (04-01 16:00 +07, dung la 1774976400000): Q2 ti so 0,9793 thay vi 0,9803; so phut Q1 130 560 / Q2 130 080 trong
   bang D-cal sai 960. Khong doi B1. Sua bang trong RESULT (ghi chu dinh chinh, khong sua lich su).
m2 rt_lchk.py khong kiem md5 pred 2026 cua lane so voi y dinh (pred_src_eq_L la nguon DEV), va 'bins26' so voi DATA26_<lane>.json do chinh rt_lane sinh
   (tu tham chieu) -> khong bat duoc lane P lo dung pred L. Thuc te dung (audit kiem doc lap bang inode + result.json). Lan sau them pred.md5 mong doi.
m3 Kernel log sim-rt-<lane>-l26-<seed>.log (tai tu 17:38) chua equity_final / b_final (PnL toan run) - nam tren dia truoc CO CHE-2 (18:12:50). CO CHE-2
   chi la dem gate, B1 da SAI tu dk1 o CO CHE (17:11:58) -> khong anh huong; nhung cam ket 'chua tai PnL' chi dung cho printDone/score. Lan sau loai *.log.
m4 rt_score_lane.py sua 18:18:57 (sau lan cham dau 18:12:56) de them Shapley/cap (MO TA). Phan luat 2.4 tinh lai doc lap khop prereg -> khong anh huong.
### NOTE
n1 Thu tu muc 8: PUSH sim-rt-p-l26-a1 16:53:59 truoc khi D-cal xong (16:57:34). Chi push, khong tai output -> khong vi pham ban chat.
n2 Tuong tac bac 3 = +3,13 pp (NNN te it hon PM 3,05 pp): cho thay quy ket cap/Shapley rat nhay voi vai lenh (1 duong di); Shapley S +0,76 vs Delta_S -0,49
   trai dau. Nen ghi ro trong RESULT.
n3 p15 T1 lech thang TOAN phan phoi, thay doi theo thang (median T1/live: 07 +3,3 %, 08 +3,8 %, 09 +0,6 %; q99 +4,9/+4,7/+1,6 %). So phut p15 > q99,995 live
   (90 ngay truoc S3): chi thang 8 (T1 14 vs live 6; thang 7/9 = 0). Nhung lane P them lenh PREDICT o thang 9 (50 vs 27) -> them lenh thang 9 khong giai
   thich bang 'duoi p15 vuot nguong cu'; gate pass theo thang KHONG co trong log (chi tong quy) nen khong tach duoc. Lech thang khong co dinh -> quantile-map
   co dinh (P4) co the khong du; dua vao prereg moi.
n4 D-D4 xoa out/lane/*/ds: bins S/M 0701 (aafc6266, ea20967b) chi con 2 link (s+ps, m+pm) -> xoa thi mat ban local; giu manifest sha + dataset Kaggle.
n5 Script audit nay khong in dong 'HOLDOUT_UNSEAL_2026_1121 (U4a)' (doc trong pham vi U4a) - ghi nhan tai day.

## Muc C - so lieu bo sung (MO TA, khong chon cau hinh)
| lane | ngay co lenh Q3 | lenh/thang 07-08-09 (PREDICT/BIG_DOWN/DCA) | chi-o-lane n / PnL (a1) | 3 lenh chi-o-lane te nhat |
|---|---|---|---|---|
| LLL | 10 | 07: DCA 2; 08: P67 B8; 09: P27 B4 D2 | 0 | - |
| P | 12 | 07: P12 D2; 08: P65 B8 D1; 09: P50 B4 D3 | 89 / -1 691 | -5 211 |
| S | 11 | 07: D2; 08: P67 B8; 09: P26 B4 D3 | 31 / +2 815 | -2 557 |
| M | 13 | 07: D2; 08: P69 B8; 09: P39 B4 D2 | 45 / -2 146 | -5 451 |
| PM | 17 | 07: P7 D5; 08: P65 B8 D1; 09: P70 B4 D4 | 130 / -15 543 | -8 669 |
| NNN | 17 | 07: P6 D5; 08: P67 B8 D1; 09: P69 B4 D4 | 129 / -11 472 | -8 177 |
So lenh/tuan tu 07-01 (a1): L [2,0,0,0,0,5,0,48,22,2,2,26,3,0]; P [4,0,0,0,10,25,0,48,1,2,6,27,22,0]; NNN [3,1,0,2,5,26,0,50,0,3,26,24,24,0].
Gia thuyet trong de bai: (a) 'pass M tang la co hoc qua sp' - DUNG, RESULT da neu (+14); net015 T1 p0 trung binh 0,4075 vs 0,4027 (multiset khac
o 100 % tick) -> sp thap hon -> r cao hon; la hieu chuan tuyet doi, khong phai xep hang. (b) chuyen tiep bo dem 90 ngay: khong tach duoc pass theo thang
(log chi in tong quy); proxy p15 cho thay lech thang giam dan toi thang 9 nhung lenh them o thang 9 van nhieu -> khong ung ho 'chi la chuyen tiep'. (c)
thang 9 77 vs 33: do 3 ngay 09-10/09-16/09-23 (~24 lenh/ngay) ma L khong vao. (d) nguon feature tron: KHONG kiem duoc trong pham vi.

## Muc D - danh gia quyet dinh MASTER (B5)
- Van ban: B1/B2 chi dinh hanh dong khi kich hoat; B3 co nhanh 'nguoc lai lam moi'; B5 'khong nhanh nao kich hoat'; N2 'mau thuan co che vs PnL =>
  khong ket luan => nhanh mac dinh'. Doc (B) theo tung model: p15 -> B4 giu live; net015 -> B3 'lam moi' nhung Delta_M -2,36 cung dau Delta_tot ->
  B4/N2 giu live; S1 -> B2 khong kich hoat (ngam 'lam moi') nhung Delta_S -0,49 CUNG dau Delta_tot (PnL noi S1 T1 hoi te hon), Shapley +0,76 trai dau,
  ruler ns -> theo N2 cung la 'khong ket luan' => giu live. RESULT ghi 'S1 khong mau thuan dang ke' la de dai. => Ca 2 cach doc deu ve B5. Quyet dinh
  (A) B5 HOP van ban prereg + muc 8 P7; ly do 'chon cach bao thu' hop le.
- D-D1: so (0,979; S1 lift@8 +0,0019 CI80 chua 0; lane S -0,49) khop. Neu sua m1 thi 0,979 -> 0,980 (khong doi).
- D-D2: 'ca 3 model T1 >= live tren Tang A' - p15/net015 dung (CI80 > 0); S1 ns -> nen viet 'khong kem'. 'Thua lo tap trung o GATE' -> sua theo M1.
  'Q3: 1,19 o q99,99; 1,51 o q99,995' khop. Loi thiet ke B1 (do in-sample Q2) ghi nhan trung thuc, khong sua sau khi thay so - dung.
- D-D3: dung huong (chi DEV, prereg moi); bo sung gia thuyet DCA/nhanh nguong tuyet doi va lech thang thay doi theo thang (n3).

## KHONG kiem duoc
- Tinh lai AUC net015 / lift@8 S1 / IC p15: nhan + feature Q3 chi co trong kernel Kaggle (ho4p1-x26-q3), khong co ban local; khong push kernel moi (rang
  buoc). Chi kiem cau truc code + v1==v2 + bo loc horizon.
- Horizon cua label_oldbasket (p15) - chi thay bo loc ts < S4-1d trong code.
- Gate pass theo thang/tuan: log sim chi in tong theo quy.
- Noi dung CO CHE truoc khi ghi sha (chi chung minh duoc khong sua SAU khi ghi sha).
- So lieu D-src(a) (K3: 0,21 %, 49,3 %) - tu luot truoc, khong trong pham vi.
