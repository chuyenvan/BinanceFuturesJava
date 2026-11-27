# A1_G4_CODE - audit doc lap code G4 (mua sau cu sap / ban sau cu vot, nen 1 phut), 2026-11-27
A1 (khong phai DEV). Chi doc du lieu <= 2019-12-31; KHONG tinh loi suat / ti le thang tren du lieu that (so sach chi tren du lieu gia).
## KET LUAN: PASS-WITH-MINOR
Khong co loi CHAN (khong nhin truoc, su kien / sigma / ngay vao dung, so sach dung, chon chi bang TRAIN, D2 = dich vong ngay theo E21).
## SHA256 (khop SHA256SUMS + brief)
load_g4 a76f22cf...7f073 | sig_g4 7269d852...15da6cb | sim_g4 1208187b...2772854 | eval_g4 37c1ef56...135bf207 | test_g4 28c4bc76...f2ec3d5d3
## 1. Doi chieu prereg + ERRATA4 -> code (KHOP)
- z = log(c_i/c_j)/(sigma1*sqrt N), j = nen cuoi <= t_i - N; sigma1 = std gop r1 (chi khi 2 nen cach 1 phut) cua 20 phien giao dich TRUOC
  (phien = moc 17:00 NY, >= 60 nen) (sig_g4.py:166-206). L z <= -T, S z >= T. sigma60 = sigma1*sqrt60 cua phien su kien, CO DINH suot lenh (sim:124,133,139).
- N3: cap-nam loai theo nam UTC; khong su kien / vao lenh; sigma NaN neu 20 phien truoc hoac phien hien tai cham cap-nam loai (sig:188, load:25,61-64).
- N4: loai neu cua so (j, i] co khoang trong > 5 phut hoac i < 30 phut sau khoang trong > 60 phut (sig:200-205, load:65-67).
- Vao = close nen i+1 (<= 5 phut sau, khong trong 16:55-17:15 NY, khong cap-nam loai) (sig:214, sim:133,139). 1 vi the / cap / cau hinh (sim:128-138).
- Thoat tai close moi phut: SL 2,0 / arm 1,0 / gap 0,5 x sigma60, dinh = close da dong; nen sau khoang trong > 5 phut kiem tai gia MO truoc;
  thu tu SL > trailing > time-stop; time-stop = nen dau co gio mo >= gio mo nen vao + TS (sim:58-85).
- Chi phi max(3 pip, 3 bp) (EURUSD 0,8 pip) nua vao / nua ra; x3 khi thoat trong 16:55-17:15 NY hoac < 30 phut sau khoang trong > 60 phut;
  truot +0,5 C cho SL / TS / END; x2 nhan spread + truot + bien (sim:87-91). DST: America/New_York cho ca dong ho NY va moc 17:00 (load:42-46,74-88).
- Swap: moc 17:00 NY trong (vao, ra], thu 6 x3, (r_base - r_quote)/360 thang m-1, -1 %/nam (sim:92-97).
- 12 cau hinh (sig:231-237); TRAIN 2005-2012 / WFO 2013-2019 theo GIO VAO (eval:59-60); chon = Sharpe thang TRAIN cao nhat, hoa -> TS ngan,
  T cao (eval:132-137); D2 = dich vong ngay (mac dinh), random cung gio/thang mo ta (eval:250-258); p = (1+n_ge)/(N+1); D1-D7 dung (eval:260-261);
  nhan [in-sample]; khoa --real / --holdout; cutoff: pyarrow filter + assert (load:101-113), lai suat <= cutoff.
## 2. Tu kiem doc lap su kien (code rieng: doc parquet, phien theo gio NY >= 17h, sigma rolling pandas, r_N bang merge_asof)
- 3 cap EURUSD, USDJPY, GBPUSD x 2 cau hinh (15,4), (60,3) x 2 phia: sigma1 lech tuong doi <= 3e-13, 0 lech trang thai xac dinh (4,4-4,7 trieu nen / cap).
- Su kien: TOAN BO 2005-2019 lech 0 (vd EURUSD L-15-4 12035 = 12035; L-60-3 30959; S-60-3 31146; USDJPY 11770 / 9790 / 29901 / 23700;
  GBPUSD 10610 / 11112 / 28364 / 29201); tung nam 2010, 2015, 2016 lech 0.
- Cu soc CHF 2015-01-15 09:00-12:00 UTC, GBP flash 2016-10-06 22:00..10-07 02:00: so su kien khop (vd GBP L-60-3 96 = 96); Giang sinh 2015 / nam moi 2016: 0 su kien ca hai.
- Dau tuan: su kien chu nhat NY < 18:30 chi xuat hien >= 30 phut sau mo cua (dung N4); 0 su kien co cua so cham khoang trong.
## 3. So sach tay (du lieu gia GBPUSD, sigma60 = 0,1 %)
- Trailing: gross 0,0010, phi 0,0003, net 0,0007 = sim (thoat dung nen 5).
- SL co khoang trong 10 phut: thoat tai gia MO -0,30 %, phi 0,00045 (0,5 + 0,5 + truot 0,5 x C) = sim, reason SL at_open.
- Time-stop thu 6 13:00 NY, TS 4 h: thoat nen 17:00 NY, phi x3 + truot = 0,00075; swap thu 6 x3 long +4,17e-5 / short -2,08e-4 = sim; dung CA mua he (EDT)
  va mua dong (EST) => DST dung.
## 4. Nhin truoc: khong. sigma chi tu phien truoc; sigma60 co dinh tai su kien; trailing dung close da dong; vao close nen ke tiep.
## 5. Doi chung / chon / cutoff
- Dich vong ngay: moi cap 1 k, giu phut-trong-phien gio NY (DST dung), so lenh, phia, co che thoat + phi; p = (1+n_ge)/(N+1). Chon chi TRAIN (test f + mutant).
- Cutoff: filter parquet + assert; file parquet von chi den 2019 nen mutant bo filter tuong duong (assert van chan).
## 6. Test + mutant (ban copy, mktemp)
test_g4.py: 30/30 PASS. 18 mutant: BAT 14 - sigma gom phien hien tai; bo spread khi vao; quen x3; SL khong truot; dong ho NY co dinh EST;
moc swap co dinh EST; cap-nam loai van sinh su kien; bo N4; chon bang WFO; p khong +1; tat guard cutoff; dao dau swap; dich vong khong giu gio;
time-stop lech 1 gio. LOT 4: vao cung nen su kien (M02); trailing dung high (M06 - du lieu test co high = close); cho vao lenh trong cua so
rollover (M14); bo filter parquet (tuong duong). A1 da doc code va tu kiem 3 diem lot dau => code DUNG, test thieu.
## 7. Loi NHO (khong chan) + cach sua
1. Test thieu cho 3 quy tac prereg: vao nen i+1 trong run_config, dinh trailing bang close (khong high), loai vao lenh 16:55-17:15. Them test voi high != close
   va su kien sat rollover.
2. E7 / sig_g4.py:214: chi loai khi NEN VAO trong 16:55-17:15; su kien luc 17:14 (vao 17:15) van duoc. Prereg ghi "loai su kien ... cua so rollover" =>
   them & ~roll[i] (hieu ung rat nho).
3. E18 / eval_g4.py:63-69: chuoi thang TRAIN gom 2007-2008 (va thang cap-nam loai) la thang 0 => Sharpe TRAIN dung de CHON bi pha loang khong deu
   giua cau hinh. Nen bo cac thang ma ca 4 cap bi loai (2007-2008) khoi chuoi TRAIN, hoac MASTER ghi ro. Lenh vao cuoi TRAIN ra o thang WFO bi
   roi khoi ca hai chuoi (rat nho).
4. E16: swap x3 vao thu 6 (quy uoc thi truong la thu 4 cho spot T+2) - tong tuan bang nhau, lech phan bo cho lenh 24 h; ghi la gioi han.
5. Doi chung: nen dich vong khong kiem lai N4 (co the vao trong 30 phut sau mo cua tuan); doi chung random dung gio UTC thay vi gio NY +-30 phut
   (chi mo ta). Nho.
## 8. CHOICES
E3 OK. E7 xem NHO-2. E9 OK (bao thu). E13 OK (SL truoc = bao thu). E14 OK. E15 OK (x3 ca sau khoang trong > 60 phut = bao thu). E18 xem NHO-3.
E19 OK (D3 dung MTM cau hinh chon). E21 OK - mac dinh dich vong ngay dung chot MASTER.
## CHUA kiem
AUDUSD (chi kiem 3 cap); toc do / RAM cua eval that; cac khoang trong noi bo ngay le khac ngoai Giang sinh / nam moi.
