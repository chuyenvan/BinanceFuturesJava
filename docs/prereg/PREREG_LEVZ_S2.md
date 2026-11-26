# PREREG_LEVZ_S2 - dinh nghia lai TIN HIEU cua he SHORT LEVZ theo kieu ROLLING / CAT NGANG (khong muc cung), cham bang 3 nam kiem
Chot boi MASTER 2026-11-26, truoc khi tinh bat ky loi suat nao cua cac tap ung vien moi. Khung: PROGRAM_SHORT_LEVZ.md. Ke thua engine thoat +
danh muc + luoi thoat cua B1 (54f40792 + ADD1 3226e940).

## 0. Boi canh
- Owner 2026-11-26 (nguyen van, bo dau): "ma ko co tin hieu la dang lay theo muc cung a. ko ap dung rolling giong he buy dang co a ra ki di
  xem con gi ap dugnjd duoc nua ko. lam ko ki" ; "thieu thi collect nhe 5 nam du lieu la mong roi can phai lay du".
- Su that da do (CHI DEM, chua co loi suat; ~/claude_master/w3/levz_rev/sigcount/out/{SIGCOUNT.md, CAND_S2.md}; ra soat he long:
  ~/claude_master/w3/levz_rev/LONG_INVENTORY.md):
  * Tin hieu D0 hien tai (z_oi >= z, z_f >= z, f > 0,01 % / 8h, san sd co dinh) co so dot / nam (W7, z 2,5): 6 / 182 / 461 / 168
    (2022..2025). Bo san funding tuyet doi (D1): 16 / 182 / 462 / 169 - KHONG cuu duoc 2022. Nguyen nhan that: nam 2022 funding ghim o
    0,01 %, sd ~ 0, z-score funding cua chinh coin khong bat.
  * He long chi dung rolling / thich nghi o tang CHON lenh: gate GDV2 (phan vi truot 90 ngay, giu ti le vao lenh on dinh) va dac trung S1
    (rolling + hang cat ngang). Tang thoat / DCA / nguong sap cua he long la muc cung.
  * Hai kieu dinh nghia cho so dot deu giua cac nam: D5 (hang cat ngang cung gio) va D6 (nguong = phan vi truot 90 ngay cua s tren toan
    universe - kieu GDV2). Nhung nam 2022 chi 4-12 % dot cua chung co f > 0,01 %: phan lon la "cang TUONG DOI", chu yeu tu OI.
- Tien nghiem cua MASTER (ghi truoc): THAP. Cac nghien cuu cu (OI_STUDY, CROWDED_LONG) khong thay edge tu OI don thuan; D5 chi trung 18-31 %
  dot voi D0. Loi ich chac chan cua S2 la co 3 nam kiem (2023, 2024, 2025) thay vi 1.
- Loi nguon da ghi nhan (khong anh huong D0 / B1 / B2 / B3 / T1): levz.py fund_z dong 158 lay trung binh ca chuoi lam hang so centering
  => sai so lam tron phu thuoc tuong lai (toi da 3,2e-7 tren z_f). S2 dung ban tinh so nguyen chinh xac cua sigcount.

## 1. Du lieu, pham vi
CHI du lieu < 2026-01-01 UTC. Thu muc moi ~/claude_master/w3/levz_s2/{code,work,out}; khong sua levz2 / levz_b1 / levz_b2 / levz_b3 /
levz_t1 / levz_rev (chi doc / import).

## 2. Cac tap ung vien (W = 7, kieu vao E0, cooldown 72 h, universe + has1m nhu B1; da dung o sigcount/out/cand_s2.npz)
- REF  = D0 z 3,0 (cand_b1 W7_E0_3.0) - doi chieu.
- P5   = D5 p 2 %: tai gio t, z_oi va z_f (kieu D2: san sd thich nghi) cung thuoc top 2 % cat ngang universe, z_oi > 0, z_f > 0.
- P5b  = D5b p 2 %: nhu P5 + f >= trung vi cat ngang cua f tai gio do.
- P6a  = D6 Q 0,999: s = min(z_oi, z_f) (z kieu D1) >= phan vi 0,999 cua s moi coin-gio universe trong 90 ngay truoc (tinh lai moi ngay
  00:00 UTC, khoi dong >= 30 ngay), s > 0.
- P6b  = D6 Q 0,998 (nhu tren).
Sua truoc khi chay (chua thay loi suat): voi P5 / P5b BO cac gio co so coin xep hang duoc < 40 (131 gio mat du lieu) - dung lai tap ung vien
va bao so dem moi. Diem xep hang trong danh muc: s (P6, REF) hoac min(hang phan vi z_oi, hang phan vi z_f) (P5 / P5b).
KHONG them tap nao khac sau khi thay so (cac tap p 5 %, Q 0,995, D1 da dem nhung KHONG chay o S2).

## 3. Luoi
Moi tap x K in {3, 5, 10} x 195 bo thoat cua B1 (SL 15 / 30 / 50 % x H 24 / 72 / 168 / 336 / 720 x trailing {tat, arm 3 / 5 / 7 / 10 x gap
2 / 3 / 5 %}). 5 tap x 585 = 2 925 cau hinh. Engine thoat + danh muc B1 khong sua (1x, phoi nhiem 60 %, phi 0,07 % / chieu, funding that,
danh gia close 1 phut, truot SL 0,3 %).

## 4. Fold va WFO
- Fold THEO NAM: Y22, Y23, Y24, Y25 (equity bat dau lai moi nam nhu fold B1) + DEV lien tuc 2022-2025.
- WFO: nam kiem Y in {2023, 2024, 2025}; chon cau hinh (K, bo thoat) trong CUNG tap chi bang cac fold < Y, dung DUNG ham cham diem / hop le
  cua select_b1 (khong sua) tinh tren cac nam train gop; bao top-1 va trung vi top-20 cua nam Y, so voi trung vi ca luoi cua tap.
  Nam 2023 chon chi bang Y22: neu tap khong co cau hinh hop le o Y22 thi ghi "khong cham duoc 2023" (REF nhieu kha nang roi vao day).
- Doi chung ngau nhien moi tap, 100 luot: ung vien ngau nhien tu universe, so luong moi nam bang so dot (ep72) cua tap, cung luoi, cung
  danh muc; hai thong ke: (i) max qua luoi tren DEV nhu B1 (p_max); (ii) tong 3 nam cua trung vi top-20 WFO (p_wfo).

## 5. Tieu chi cho TUNG tap moi (chot truoc)
S-a WFO trung vi top-20 > 0 o >= 2 / 3 nam kiem VA tong 3 nam > 0.
S-b ti le cau hinh co lai >= 50 % o >= 3 / 4 nam (Y22..Y25).
S-c p_wfo <= 0,05.
S-d top-1 WFO: >= 30 lenh moi nam kiem; gop ledger 3 nam, bo 5 % lenh loi nhat van > 0.
S-e top-1 WFO: maxDD (xau nhat trong nen) <= 25 % o tung nam kiem.
- Du S-a..S-e => "TAP DAT": thanh pool cua B5 (toi uu gop voi ky thuat lenh T1). Dat S-a + S-c => "CO CAI THIEN, CHUA DU". Con lai =>
  "KHONG HON D0". Bao kem REF cung quy trinh de so. Khong tap nao dat => bao owner so thuc; owner quyet.
- So in-sample (DEV, p_max) chi bao kem, khong dung de ket luan.

## 6. Bao cao mo ta bat buoc
So ung vien / dot / nam tung tap (sau sua muc 2); ti le lenh co funding > 0 va tong funding nhan / tra; lai lo theo thang; do tap trung coin;
do trung lenh giua cac tap va voi REF; ban do tham so (H, SL, trailing) cua tung tap; tuong quan thu hang cau hinh giua cac nam.

## 7. Ky luat
prereg -> DEV (agent Opus) -> A1 audit code (agent khac) -> RUN -> A1 audit ket qua -> bao owner. Test bat buoc: REF qua duong S2 phai tai
lap dung so B1 (cung cau hinh, fold F1 / F2 / F3 tinh lai tu fold nam neu can - it nhat DEV va F2 = Y24, F3 = Y25 phai trung grid_b1);
kiem nhan qua bang nhieu du lieu sau gio t cho P5b va P6 (sigcount chua chay); bang thoat cua ung vien trung voi exits.npz B1 phai khop
tuyet doi. Viec nang qua flock oracle_heavy.lock hoac Kaggle (khi co duong chay da kiem). Python dung logging. Khong doc 2026.
