# PILOT_M_TOOL_DEV - bo cham hang ngay CHI LOG cho PREREG_PILOT_M (2a21fe35) - agent DEV (Opus), 2026-11-25 +07
CHUA COMMIT. Cho A1 audit truoc khi dung ket qua. Khong doc gi trong pull242/2026-11-24+ va cron >= 2026-11-24 07:00 (chay thu dung --max-ts "2026-11-24 07:00").

## File (sha256)
- tools/pilot_m/pilot_m_daily.py  024b5330b1dde63a2be1c04900d19a8a774c0ca6f3ceb2a0427900b9fd09f938 (cong_cu=024b5330b1dd)
- tools/pilot_m/pilot_m_daily.sh  4c8a84a9b7fb933ff5697144dff9559c892a12113cded1058b221e289dc96c3f
- tools/pilot_m/README_PILOT_M.md 97e25ed541064fb6caa9f6cd1988e6ccb25908b6380782c7b4d7fa32198a2b42
- tools/pilot_m/test/test_pilot_m_daily.sh 8d02ec25eba678e5d71027403c9321abc2d5942d05fbb1362d7172c5047cefd5
- tools/pilot_m/test/pm_tests.py  7183d8b1e90393c3b7f0b2346888337cc428e6cb1333f48d27a3ff2a855d5568
(tools/pilot_m = ~/claude_master/vz_e1_wt/tools/pilot_m). Dau ra thu: v12/pilot_m_devtest/final/D_2026112{1,2,3}.{md,json}.

## Test: 128/128 PASS (du lieu tong hop)
(a) sach => DAT 18 muc + bac XANH + dong dau md; (b) tiem 1 loi x 23 ca (M-E0 x2 gom BIG_DOWN, I3, I4, I8, I9 x2, I10, I11, I12, M-T x2,
D1, M-S x2 gom TIER=VANG, M-X, K1, K2, K3, K4, K5, K6 ERROR, K6 LATCH A40=DO) => VI_PHAM dung muc + dung bac + khong muc khac;
(c) ngay rong => KHONG_CO_SU_KIEN 12 muc su kien, K* DAT; (d) thieu pull / thieu COMPLETE / thieu cron / thieu pull ngay truoc / dong
khong parse => KHONG_CHAM_DUOC; qua D+3 09:00 => VANG; 26/11: restart trong khung, K2 mien, K5 INCOMPLETE hop le, M-S bo HOURLY JVM cu
(R1) => DAT; thieu --pilot-on-start => K1/K2 KCD; restart ngoai khung => K1 VI_PHAM; defer-START [pool-3-thread-1] bi bo qua; ALGO NEW
truoc STOP 20 ms => DAT; khong ro realized=/phi=/eq=/tmb/acct_*/signature/token (3 ca); 2 ngay VANG lien tiep; chan ghi chinh thuc sai co.
Neo that I9(b): F(peak) float32 tai lap SL log BLESS 0.014510079 va JCT 0.0015497198 (21/11).

## Chay thu 21-23/11 (khong phai ket qua cham; --max-ts 2026-11-24 07:00)
Dong khong parse: 0 o moi mau ca 3 ngay. Dong parse (21/22/23): SUBMIT 24/0/0, FILL_STREAM 23/0/0, FILL_EXEC 1/0/0, ARM 12/2/2,
STOP 75/4/8, ALGO 174/12/20, SFIL 16/2/2, CLOS 12/2/2, BOOK 12/2/2, RECON_H 24/24/24, KS_HOURLY 24/24/24, TSX_STATUS 24/24/24,
TSX_FLAG 1/1/1, TSX_DEFER 3/0/0 (deu [pool-3-thread-1]), STOPERR 1/0/0, E4130 1/0/0, MKT 1465/1440/1440, AIPASS 580/0/0. 0 gio trong.
Trang thai: M-E0 DAT 24/24 (21), KCSK (22,23); I3, I4, I8, I9, I10, I11, I12 DAT ca 3 ngay; M-T, D1 KHONG_CO_SU_KIEN; M-X DAT (21), KCSK;
K1, K3, K4, K5, K6 DAT; K2 VI_PHAM ca 3 ngay; M-S VI_PHAM 8/24 (21). Bac 21=DO (M-S), 22=VANG, 23=VANG (K2; luat 2 ngay K2 bat).
Thoi gian: 1,1 / 2,2 / 3,5 s (tang ~1,2 s moi ngay pull truoc; ~25 s toi 08/12).

## Chua cai duoc
Khong. Muc KCD_CAU_TRUC theo dung prereg: M-E, I1, I2, I5, I6, I7, D2, D3, D4, L-S, L-S2, M-G, K7, M-S (4)(5).

## DE NGHI ERRATA (chua sua gi; tool cai dung chu)
E1 M-S (1) dong 219-223: 21/11 8/24 leg r = 1,000158-1,000330 > 1+1e-6 trong khi r_cap = C_ngam/C3_CAPITAL <= 1 (min -0,00162, max 0):
   eq_lo (min eq= 2 dong HOURLY bao quanh) thap hon equity tai luc SUBMIT => VI_PHAM => DO gia. De xuat: "VI_PHAM tren khi
   C_ngam / min(C3_CAPITAL, eq_hi) > 1 + 1e-6, eq_hi = max eq= 2 dong bao quanh; nhanh < 0,98 giu eq_lo" (hoac nguong tren 1 + 1e-3).
E2 K2 dong 266-268: dong TOM TAT "adapter= C3_CAPITAL= push=OFF" (truong rong, monitor doc env loi) 2/3/3 dong ngay 21/22/23
   (23/11 co 2 dong lien tiep 08:26, 08:28) => K2 VI_PHAM moi ngay => VANG + luat 2 ngay => de xuat DO gia. De xuat: dong co adapter/
   C3_CAPITAL/push RONG xet nhu khan_canh_bao (VI_PHAM khi >= 3 dong lien tiep hoac > 10 phut), dong co gia tri SAI van VI_PHAM ngay.
E3 I4(d) dong 107 "TRIGGERED ... truoc do" mo ho: log that TRIGGERED in SAU CLOS 1 ms (TRIGGERING truoc). Tool: chi doi co dong TRIGGERED.
   De xuat ghi ro "co ALGO X=TRIGGERED (hoac TRIGGERING) cua cid stop dang hieu luc, trong [t_CLOS - 61 s ; t_CLOS + 61 s]".
E4 I10 dong 122-124 vs I8 dong 115-116: DELIST_SETTLE duoc phep o I8 nhung khong thuoc tap DAT I10 => VI_PHAM DO. Can xac nhan.
E5 M-S: v3 khong con muc "(2)" (dong 223-227 nhay (1) -> (3)) trong khi dong 30 nhac "M-S (2)". Tool bao "(1)/(2)" chung.

## A1 can soi
README muc "Lua chon cai dat" 1-15 (nhat la I4(d), I3 MOVE khong co P truoc, M-E0 cua so (d), D1(c), I11 n_ky_vong, I12(b) stepSize,
M-T flag/moc, K3/K4 gio JVM dung, K2 khung mien 26/11); san(); fail-closed 0,1 %; lookahead 2 h chi trong file pull D; trang thai cum
tu 21/11 (RECON n khop log 21-23/11: I11 DAT 30/30).
## Khong kiem duoc (chi test tong hop + doi chieu chuoi code)
Duong DCA, TIME-STOP, defer-START [C3LIVE-OPS], PX_CORRECTED, lop B / LECH / leo thang, LATCH, C2_WARN, restart trong ngay, flag PENDING/NA:
0 dong that truoc moc. Gia tri env (GAP/GIVEBACK, C2*, MIN_MOMENTUM_15M), tickSize/stepSize, K7.

## Lenh MASTER cham chinh thuc 1 ngay (sau A1)
~/claude_master/vz_e1_wt/tools/pilot_m/pilot_m_daily.sh 2026-11-24 --official
(ngay 26/11: them --pilot-on-start "2026-11-26 HH:MM")

# VONG 2 - sua theo A1_PILOT_M_TOOL (T1-T12) + ERRATA1 c0f35f3c (2026-11-25 ~14:55 +07). CHUA COMMIT.
## File (sha256)
- pilot_m_daily.py b6e5cd8117a0cc025949580c53a70decb1ed8710b1eddb20232fab3e83c20c18 (cong_cu=b6e5cd8117a0)
- pilot_m_daily.sh 4c8a84a9b7fb933ff5697144dff9559c892a12113cded1058b221e289dc96c3f (khong doi)
- README_PILOT_M.md 09c6b681b945b68547377255399a3870c5178e4fb5103508eb85e727b82692c6
- test/test_pilot_m_daily.sh 8d02ec25eba678e5d71027403c9321abc2d5942d05fbb1362d7172c5047cefd5 (khong doi)
- test/pm_tests.py 1ae9b6732b16d0c941b31b4e470ab63568e9e058685b6a400e3f82228d6dc84c
- test/run_mutants.py d1639a76c484037bb840ab2c8e61c15d68f4ef124bb1503a5cf6c9cf82c8c111 ; test/run_mutants.sh 0e60e19f402078c12077b87fa340d74c2923e87e45d38bd575d2a33fa7fc8ebe
## Sua: T1 tien to A1 + OTHER_TPL (125 mau literal tu code) => gia-ho PFX; T2/E6 cum dong = CLOS/BOOK/SFIL du qty, BOOK<->CLOS +-600 s;
T3/E2 K2 dong hop le, .log.1, khoang trong dau/cuoi ngay; T4/E3; T5/E1/E5 S1-S9 (S3 VANG EQ_DUOI); T6/E4 --delist-noted; T7/E7; T8/E8;
T9/E13; T10/E9 0 dung sai (tru MKT/AIPASS/SKIPORD/DCAGRID); T11 san() (WALLET/BALANCE, so_du, equity_so, upl*, chot, moc, chuyen, dinh,
tmb*, eq*, "eq = C3_CAPITAL + (..)"); E10/E11/E12 da dung; dong dau prereg=2a21fe35+E1.
## Test: 330/330 PASS (~11 s). Mutant: 17/17 GIET (run_mutants.sh, log v12/pilot_m_devtest/mutants.log)
| Mutant A1 | Ca giet |
|---|---|
| I4(a) bo | b_I4a_STOP_ARM_sau_61s |
| I4(b) bo han 61 s | b_I4b_ALGO_NEW_sau_61s |
| I4(c) luon DAT | b_I4c_thieu_CANCELED_stop_cu |
| I4(d) bo | b_I4d_khong_TRIGGER, b_I4d_TRIGGERED_sau_70s |
| I8 bo SFIL truoc ARM | b_I8_SFIL_truoc_arm |
| I10 bo ly do BOOK=CLOS | b_I10_BOOK_ly_do_khac_CLOS |
| I11(b) bo leo thang | b_I11b_leo_thang |
| I12(d) bo tong SFIL | b_I12d_tong_SFIL |
| M-T bo yeu cau CLOS | b_MT_khong_CLOS |
| M-T bo "som hon due" | b_MT_TS_som_hon_due |
| D1(a) bo level | b_D1a_level |
| M-S bo (6)=S7 | b_S7_budget_nho |
| M-E0 bo (c) | b_ME0c_leg0_khi_dang_giu |
| K2 bo khoang trong 10' | K2_khoang_trong_20_phut, E2_doc_hong_12_phut, B10, B11_thieu_log1 |
| K3 bo streak | b_K3_streak_nhay |
| K4 bo "chua co co ngay" | b_K4_chua_co_co_ngay |
| K5 bo log_minutes | b_K5_log_minutes |
Ca pha A1 (cong cu moi): B1 => I10 VI_PHAM; B2 => I10 KHONG_CHAM_DUOC (PFX); B10 => K2 VI_PHAM; B11 => K2 DAT (doc .log.1), thieu .log.1 => VI_PHAM;
B12 => I10 VI_PHAM. Ca ERRATA1: S1, S2, S3 EQ_DUOI/AVAIL, TIER, S4, S7, S8, S9, khong HOURLY cung JVM (KCD), S5/S6 KCD_CAU_TRUC; K2 1 / 2
luot doc hong DAT, doc hong 12' => VI_PHAM; I4(d) chi TRIGGERED sau CLOS 1 ms DAT; DELIST co/khong ghi chep; RST roi time-stop DAT,
arm khong RST => KCSK; flag NA => M-T DAT; E8 DCA khong khop DAT; E9 dong TRAIL/SUBMIT cat => KCD; E12 khung 60'; ro tien 0 o moi ca.
## Chay thu 21/22/23 (--max-ts 2026-11-24 07:00): 0 dong khong parse. M-E0 DAT/KCSK/KCSK; I3 I4 I8 I9 I10 I11 I12 DAT ca 3 ngay;
M-T, D1 KCSK; M-S DAT 24/24 (21, het DO - E1); M-X DAT/KCSK/KCSK; K1 K3 K4 K5 K6 DAT; K2: luot doc hong 2/3/3 KHONG con vi pham;
21, 22 = KHONG_CHAM_DUOC (dong TOM TAT truoc 22/11 17:24 chua co truong deadman=) => qua D+3 nen bac VANG; 23 = DAT. Bac 21 VANG, 22 VANG, 23 XANH.
Thoi gian 1,3 / 2,3 / 3,5 s.
## DE NGHI ERRATA2
1. E2 "thoi diem cuoi cua cron log da doc": neu la dong cuoi trong file => monitor chet khong bao gio sinh khoang trong (B10 lot).
   Cong cu dung thoi diem DOC (cham_luc, chan --max-ts). Can MASTER xac nhan cau chu.
2. E1 S1 khong co ngoai le TIER: leg tierMul 1,2 that => r_cap 1,2 => S1 VI_PHAM DO, trong khi S2 TIER = VANG. Cai dung chu (ca test
   S1_tierMul_1_2_ra_DO_theo_chu).
3. E13 chi cho M-T: K4 van doi flag=(ON|OFF) => ngay co dong NA(->OFF) K4 VI_PHAM (VANG).
## A1 can soi: README "Lua chon cai dat" 1-13 (8-13 moi); OTHER_TPL (co dung loai het chuoi cua ho cham?); E2 (b) ap ca dong
khong hop le voi latch rong; dong hop le thieu deadman => KCD.

# VONG 3 - ERRATA2 efc4f9c1 (F1 chan gio --official < D+1 07:10; F2 S1 > 1,2(1+1e-6) DO, S1b VANG TIER). CHUA COMMIT.
sha256: pilot_m_daily.py 8bc4da418d25be674d49b1cc28f792db60d6f609b0f199163c10014daacaecdd; README f8da0e125a1ae666ac6cb8936109b9adf195cf1e3b668b7dbf10b9241547b30c;
test/pm_tests.py, test/run_mutants.py: xem sha256sum (bao cao vong 3). Test 351/351; mutant 20/20 (M18 S1 nguong, M19 bo S1b, M20 bo chan gio).
Test r_cap 1,0 DAT; 1,01 VANG TIER; 1,1 DO (kem S2 vi r_hi >= r_cap); 1,2 VANG; 1,21 DO. Chan gio official kiem bang ham thuan official_time_ok
(gio tiem) + kiem main goi ham; KHONG chay --official that trong test/mutant. Dong dau prereg=2a21fe35+E1+E2.
Thu 21/22/23: khong doi so voi vong 2 (VANG/VANG/XANH; M-S 21 DAT 24/24; K2 21-22 KCD thieu truong deadman, 23 DAT).

# VONG 4 - A1_PILOT_M_TOOL_V2 m1-m5 + ERRATA3 230efcef (2026-11-26 ~12:20 +07). Sua tai cho tren ban da commit 989a2531, CHUA COMMIT.
sha256: pilot_m_daily.py 0ab2edded6db7ed12e2a3a30b2ca456546728d88cc9decc702e5f6a5554871c7 (cong_cu=0ab2edded6db);
README 54598698fb965711eb3ed01e368fc5ccfcf1c5de9e27e35300573bbe2a3d68cf; test/pm_tests.py 68f98deb952e74d7f8425e869fdf10c420a9008ca3ede8d7f23940891a39cb56;
test/run_mutants.py 3319407a95b15e90678f22020fe617987cc027c5396719244a66a85c7816f3bd.
Sua: H1 chk_MT (TIME-STOP / CLOS TIME_STOP_168H khi cum dang arm => VI_PHAM; kiem ca khi due >= cuoi ngay); H2 chk_K2 latch/khan/jar chi
xet khi khong rong; H3 chk_I10 ghep theo cum (1 CLOS + 1 BOOK cung cum, +-600 s; SFIL du qty can CLOS cung cum; mo coi => VI_PHAM);
dong dau prereg=2a21fe35+E1+E2+E3; README lua chon 9, 10 + bang muc.
Test 371/371: them H1 (cum dang arm bi TIME-STOP => DO; chi CLOS TIME_STOP_168H => DO), arm->RST->time-stop DAT (giu), H2 N6 (luot ssh hong
toan bo => DAT, so_luot_doc_hong=1), H3 N12 (2 cum SYMA dong cach 5 phut => DAT), BOOK mo coi => DO, X01 (CLOS sau BOOK 890 s => I10 VI_PHAM),
X04 (1 dong ALGO hong / 1101 => I4 KHONG_CHAM_DUOC).
Mutant 25/25 GIET (them X01 [bo moi han 600 s cua E6, ca 3 cho], X04, H1_bo, H2_latch_rong_van_xet, H3_mo_coi_thanh_DAT).
Hoi quy: 21/22/23 (--max-ts 24/11 07:00) VANG/VANG/XANH khong doi; 24 (khong max-ts) va 25 (--max-ts 2026-11-26 07:00, khong doc du lieu D=26)
TRUNG 100 % trang thai + mau tung muc voi ban chinh thuc v12/pilot_m/D_2026112{4,5}.json (bac XANH/XANH).

# VONG 5 - A1_PILOT_M_TOOL_V3 (2026-11-26 ~12:40 +07). Sua tai cho, CHUA COMMIT.
364ee37d866e5b2a1514d285fd4253ad75ce602629f38d98dbcd9370a9dd01f7  pilot_m_daily.py
7c70dac1128463a1250214ce7985b05cff58d280f4a3a6e65d9b8a5c954b05bf  README_PILOT_M.md
9f68aac7aab6db6c0346c1209a993dc5e0ed530e295aa7db5ca789dfc8add5b4  test/pm_tests.py
47cdc68f67b532b7455f0a75886f1042fcf4742af662a66122cd9340248018f7  test/run_mutants.py
- B1: chk_K2 (c) `a not in (None, '', '0')` (H2: khan / khan_canh_bao rong o dong hop le khong VI_PHAM); test C11, C12 => DAT.
- m1/C3d: armed_at / unarmed_at so theo (ms, thu tu dong); ARM va RST cung ms (RST in sau) roi TS => DAT (test).
- m4: nhat ky (README "Nhat ky thay doi"): khoi "TS som hon due-2 s" doi len truoc due >= C.hi / unarmed_at tu vong 4. m2: C6 vao README gioi han.
- Test 417/417. Mutant 39/39 GIET (them B1 + Y01 Y03 Y05 Y20 Y07 Y08 Y12 Y13 Y14 Y15 Y19 Y17 Y18; Y20 dung lai theo code moi = so chi theo ms).
- Hoi quy D=24 (khong max-ts), D=25 (--max-ts 2026-11-26 07:00): 31/31 muc trung trang_thai/mau/so_vi_pham/so_khong_cham_duoc voi ban chinh thuc; bac XANH/XANH.
