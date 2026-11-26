# A1 audit DELTA pilot_m_daily.py (ERRATA3) - V3
A1 (Opus, doc lap) 2026-11-26 ~12:35 +07. Ban audit: sha256 0ab2edded6db7ed12e2a3a30b2ca456546728d88cc9decc702e5f6a5554871c7 (chua commit), base 989a2531 (8bc4da418d25).

## VERDICT: PASS-WITH-MINOR (dieu kien: sua 1 dong bat buoc B1 + them 2 ca test; sau do commit va dung cham tu D=2026-11-26, khong can A1 vong nua neu diff chi gom B1 + test)

## 1. Delta (da kiem bang doc diff tung dong)
- sha256 khop. Diff: pilot_m_daily.py 60 dong, README, pm_tests.py, run_mutants.py. Nhan PREREG_SHA = 2a21fe35+E1+E2+E3.
- H1 chk_MT (:1330-1332 armed_at, :1409-1413): dung chu ERRATA3 (ARM cuoi <= t, khong RST trong (ARM; t]) cho ca TIME-STOP va CLOS TIME_STOP_168H.
- H2 chk_K2 (:1956, :1959, :1961): (b) latch/khan/jar chi xet khi khong rong. Dong 1959 (khan) la no-op.
- H3 chk_I10 (:1165-1209): ghep theo cl.clos/cl.books (cum), mo coi => VI_PHAM.
- Thay doi logic NGOAI 3 diem (ghi nhan, khong chan): khoi "TIME-STOP som hon due-2s" bi doi len TRUOC `if due >= C.hi: continue` va `unarmed_at` => nay bat ca TS som khi due con o tuong lai / cum dang arm tai due (truoc day lot). Dung huong E7, nhung DEV can ghi vao nhat ky thay doi.

## 2. Test / mutant DEV (da chay trong sandbox)
- pm_tests: 371/371. run_mutants: 25/25 GIET.

## 3. Mutant cua A1 (20, cung bo test DEV): GIET 7/20
GIET: Y02 bo RST, Y04 H1 chi TS, Y06 dung sai som 200 s, Y09 khan rong xet, Y10 jar rong xet, Y11 khong dem doc_hong, Y16 I10 ghep theo symbol.
SONG (lo test):
- Y01 armed_at dung arms[0] (arm->RST->arm->TS khong co test)
- Y03 ARM sau TS van tinh; Y05 H1 chi khi arm tai due (arm sau due roi TS); Y20 RST cung ms (bien ms - gan tuong duong)
- Y07 M-T CLOS <= moc+600 s doi 900 s; Y08 M-T KCD moc+600 s doi 60 s
- Y12 I10 600 s doi 900 s; Y13 I10 han KCD +600 s doi 60 s; Y14 bo kiem 2 BOOK/cum; Y15 bo kiem 2 CLOS/cum; Y19 bo SFIL-khong-CLOS
- Y17 UNPARSED_MAX 0,1 % doi 5 %; Y18 K2 bo chan dong TOM TAT khong parse
De nghi DEV them ca: C1 (duoi), 2 BOOK 1 cum, BOOK-CLOS cach 601 s vs 599 s, CLOS TIME_STOP tai moc+601 s, K2 unparsed 0,2 %.

## 4. Ca pha (log tong hop, dung khung pm_tests.clean): 16/20 khop ky vong tinh tay
OK: C1 arm->RST->arm->TS => M-T VP (H1); C1b arm->RST->TS => DAT; C2 khong arm, TS dung han => DAT; C3a ARM truoc TS cung giay => VP;
C3b ARM sau TS cung giay => VP (do dong CLOS TIME_STOP sau ARM - dung chu H1); C3c ARM cung ms sau TS => VP; C4 chi CLOS TIME_STOP_168H cum arm => VP;
C5 2 cum cung symbol dong cach 3 phut, moi cum du CLOS+BOOK => I10 DAT; C7a BOOK mo coi, C7b CLOS mo coi, C7c BOOK le 2 h sau => VP;
C8 TOM TAT hop le latch=A40 => VP; C9 3 luot doc hong toan bo => DAT, so_luot_doc_hong=3; C10 khan rong 1 dong => DAT; C13 latch+jar rong => DAT; C14 dong khong hop le latch=A40 => VP.
XX:
- C11 / C12 (LOI B1): 2 dong TOM TAT HOP LE lien tiep co khan= rong (hoac khan_canh_bao= rong) => K2 VI_PHAM "khan= o 2 dong hop le lien tiep". Trai H2 ("truong rong khong sinh VI_PHAM").
- C3d (minor): ARM va RST cung ms (RST dong sau) roi TS => tool VP; theo thu tu dong la DAT. armed_at so sanh `arms[-1] < r` theo ms, khong theo thu tu dong (unarmed_at cung vay, co tu truoc).
- C6 (minor, gioi han da biet): CLOS1, cum 2 mo, CLOS2, BOOK1, BOOK2 => tool gan BOOK1 vao cum 2 (S.last_closed theo symbol) => VP; ly tuong DAT. Dong BOOK/CLOS khong co id cum; thuc te BOOK/CLOS cung luong closedOnExchange cach ~100 ms nen kho xay ra. Ghi vao README.

## Loi bat buoc
B1 pilot_m_daily.py:1979 `if a not in (None, '0') and a == bb:` => `if a not in (None, '', '0') and a == bb:` + test C11/C12 (K2 DAT).
Minor: m1 armed_at/unarmed_at dung (t, seq) thay vi t (C3c, C3d); m2 ghi gioi han C6 vao README; m3 bo sung test cho 13 mutant song; m4 ghi thay doi khoi "TS som" trong nhat ky DEV.

## 5. Hoi quy du lieu that (sandbox, khong --official)
D=2026-11-24 va D=2026-11-25 (--max-ts "2026-11-26 07:00"): 31/31 muc trung (trang_thai, mau, so_vi_pham, so_khong_cham_duoc) voi D_20261124.json / D_20261125.json chinh thuc; bac XANH ca hai. Chi khac dau: prereg +E3, cong_cu 0ab2edded6db.

## 6. Ngay pilot_on (chi tu code + prereg, KHONG doc du lieu D=26/11)
(a) D=2026-11-26 khong co restart:
- Thieu --pilot-on-start: K1 va K2 bi force KHONG_CHAM_DUOC (:1695-1696, :1911-1912) => khong VI_PHAM gia, XANH toi D+3 09:00 roi VANG ("thieu du lieu > 1 ngay"). Nhung K2 bi bo TRANG ca ngay (latch, gap 10', C3_CAPITAL... khong duoc cham) => vi pham that bi che.
- Neu MASTER van truyen --pilot-on-start: K1 VP "khong co restart trong khung owner" (:1721-1723), K2 VP "qua 60 phut chua co TOM TAT push=ON va C3_CAPITAL=5000" (:1934) + moi dong sau pilot_on VP C3_CAPITAL (exp_cap :1681) => VI_PHAM gia.
- Theo CHU prereg muc 8 K1 (dong 263: "tru ngay 2026-11-26 >= 1 restart trong khung owner") khong co restart ngay 26/11 la VI_PHAM => can errata. Luu y: prereg dem banner C3LiveRuntime, khong dem dong MainClass; MainClass chi dung tach doan von (muc 1, dong 62-63).
- K5 (:1802): ngoai le INCOMPLETE ngay 26 van mo nhung nguong >= 1440-20x0 => vo hai.
(b) pilot_on ngay 27/11 (hoac sau): moi ngoai le cung PILOT_DAY=2026-11-26 (:34) KHONG ap. exp_cap (:1679-1680) = 5000 cho MOI ngay > 26/11 => K2 VP C3_CAPITAL=1000 moi dong truoc restart (ca ngay 27 neu restart muon, va moi ngay 26..ngay truoc pilot); K1 VP "co banner khoi dong JVM" (:1705) cho restart pilot; K2 khung mien pilot_on khong ap (push=OFF trong luc chuyen => VP); K5 INCOMPLETE khong duoc chap nhan. --pilot-on-start bi bo qua ngoai D=26/11.

### Cau ERRATA4 de xuat (ASCII)
"ERRATA4 (thay ngay co dinh 2026-11-26): Moi ngoai le va moc von ghi 'ngay 2026-11-26' / 'restart pilot 2026-11-26' trong PREREG_PILOT_M (muc 1 Von dong 62-63, muc 4 luu y M-S, M-T dong 162, muc 8 K1, K2, K5) va ERRATA1 E12 nay gan voi NGAY PILOT_ON = ngay cham D co cua so [D 07:00; D+1 07:00) +07 chua thoi diem bat dau lenh golive_pilot_on.sh do owner chay (theo ghi chep MASTER; truyen cho bo cham bang --pilot-on-start 'yyyy-mm-dd HH:MM' +07). Von ky vong = 1000 truoc pilot_on, 5000 tu pilot_on tro di (ke ca cac ngay sau). Ngay D khong chua pilot_on: K1 = 0 banner, K2 va K5 khong co ngoai le pilot. Ngay D ma MASTER ghi 'owner chua chay pilot_on' (--pilot-on-none): cham nhu ngay thuong voi von 1000. Ngay D >= 2026-11-26 chua co ghi chep MASTER (khong co ca hai tham so): K1, K2 = KHONG_CHAM_DUOC (khong VI_PHAM), MASTER bo sung ghi chep truoc D+3 09:00 +07."

### Thay doi cong cu tuong ung
- pilot_m_daily.py:34 PILOT_DAY co dinh => C.pilot_day suy tu C.pilot_on (ngay D co cua so chua pilot_on); them --pilot-on-none (:2234 vung argparse, :2069 parse); co the luu ghi chep MASTER vao file (vd v12/pilot_m/PILOT_ON.txt) de cac ngay sau doc lai.
- :1676-1681 exp_cap: 5000 neu pilot_on biet va t >= pilot_on; 1000 neu pilot_on > t hoac --pilot-on-none; khong biet => K1/K2 KCD.
- :1695-1696, :1702-1705, :1721-1723 (K1); :1802 (K5); :1911-1912, :1926-1934 (K2): `C.D == PILOT_DAY` => `C.D == C.pilot_day`; thong diep '26/11' => 'ngay pilot_on'.
- :2234 help; pilot_m_daily.sh dong 2; README_PILOT_M.md dong 6, 42, 90.
- pm_tests: p26 tham so hoa ngay (26 va 27/11), ca D=26 khong restart + --pilot-on-none => K1 DAT, ca D sau pilot (von 5000), ca D truoc pilot (von 1000).
