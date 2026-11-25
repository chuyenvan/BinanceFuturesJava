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
