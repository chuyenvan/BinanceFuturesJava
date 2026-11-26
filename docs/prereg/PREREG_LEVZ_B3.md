# PREREG_LEVZ_B3 - tang B3 cua he SHORT LEVZ: SORT bang model (kieu S1) tren pool noi rong
Chot boi MASTER 2026-11-26 (truoc khi dung bat ky du lieu B3 nao). Khung: PROGRAM_SHORT_LEVZ.md. Ke thua: PREREG_LEVZ_B1 (54f40792 + ADD1
3226e940), PREREG_LEVZ_B2 (da636b28 + ADD1 d1241f48).

## 0. Boi canh va quyet dinh owner
- B1 + B2 KHONG dat tieu chi di tiep; luat dung som (PROGRAM muc 5) = "MASTER khuyen dung truoc B3; owner quyet".
- Owner 2026-11-26 (nguyen van, bo dau): "phan tich ki chay/audit ti mi toi thay huong sang do. giu 2026 holdout thoi" ; "chua sim lai doi fw
  voi holdout khong hieu" ; "fw holdout de lam gi". => OWNER QUYET DI TIEP B3 (ghi de khuyen nghi dung cua MASTER). Forward / holdout chi lam
  o B5 khi he da dung xong va dong bang.
- Rui ro da bao owner: tin hieu goc chua qua phep thu khong-nhin-truoc; ML tren mau nho (~200 dot coin doc lap / nam) de khop nhieu. Vi vay
  B3 KHONG co HPO, model nong, cham THUAN WFO, so voi chon ngau nhien.
- LECH so voi PROGRAM muc 2 (ghi ro): PROGRAM noi "< 300 ung vien / nam train => khong lam B3". Nam 2022 nhieu kha nang < 300 dot. B3 van
  lam, dung dieu kien C0 duoi day thay cho cau do. PROGRAM muc 3 noi nam kiem {2023, 2024, 2025}; B3 cham chinh thuc 2024 va 2025 (nhu B1);
  2023 chi mo ta va chi khi 2022 du mau.

## 1. Du lieu, pham vi
- CHI du lieu < 2026-01-01 00:00 UTC (CUT cua B1). Khong doc gi cua 2026. Cung kho du lieu B1: close 1 phut (work/close1m.npy), nen gio
  (levz2/work/px_1h.parquet), bang tin hieu levz2/work/sig_W7.parquet, funding, OI nhu B0 / B1.
- Thu muc moi ~/claude_master/w3/levz_b3/{code,work,out}. KHONG sua levz2, levz_b1, levz_b2 (chi import / doc).

## 2. Pool ung vien
- W = 7 ngay, kieu vao E0 (vao ngay), z_min = 1,5 (z_oi >= 1,5 va z_f >= 1,5, f > 0,01 % / 8h, san sd nhu B0). Moi thu khac (cach sinh ung
  vien, thoi diem vao, coin hop le, cooldown) Y HET bo sinh ung vien B1 - chi doi z_min. Kiem hoi quy: tap con z >= 2,5 / 3,0 / 3,5 cua pool
  moi phai TRUNG tung dong voi cand_b1.npz (W7_E0_*).
- "Dot coin" = cac ung vien cung coin cach nhau < 24 h gop thanh mot dot. Trong so mau = 1 / (so ung vien trong dot).
- C0 (dieu kien du mau, kiem TRUOC khi train): voi nam kiem Y, tap train (< Y, sau purge) co >= 600 dot VA nam train gan nhat co >= 300 dot.
  Y nao khong dat C0 thi KHONG cham Y do. Neu 2024 hoac 2025 khong dat C0 => B3 khong the "DAT" (bao owner so dem, dung).

## 3. Co che thoat va nhan
- Engine thoat = B1 (exits.py: danh gia tai close 1 phut, SL luon bat, truot gia, phi 0,07 % / chieu, funding that) khong sua.
- Thoat cho nam kiem Y (exit_Y) chon KHONG nhin truoc tu luoi B1 da co (out/grid_b1.parquet), chi cac dong W = 7, E = E0: voi moi bo thoat
  (SL, H, arm, gap) trong 195 bo, diem = trung vi qua 9 cau hinh (z x K) cua loi nhuan cac fold < Y (Y = 2024: fold F1 = 2022-23; Y = 2025:
  F1 + F2). exit_Y = bo diem cao nhat; hoa => SL nho hon, H ngan hon, thu tu trailing cua B1. Ghi ro cot da dung va exit_Y ra bao cao.
- Nhan cua ung vien = loi suat rong cua lenh short don le theo exit_Y (da tru phi, funding, truot gia). Khong cat, khong bien doi.
- Purge: bo khoi train moi ung vien co gio vao > (dau nam Y - H(exit_Y) - 24 h).

## 4. Dac trung (tat ca tinh tu du lieu <= gio quyet dinh k cua ung vien; cam dung ten coin, nam, thang, ngay trong tuan)
Muc coin: z_oi, z_f, s = min(z_oi, z_f), z_oi - z_f, f (muc funding r8), z_r, loi suat log 1 / 4 / 24 / 72 / 168 h, do bien dong thuc 24 h va
168 h (sd loi suat gio), bien do 24 h ((max high - min low) / close), khoang cach toi dinh 168 h va toi day 168 h, ln(qv 24 h), qv 24 h /
trung binh ngay cua 7 ngay, hang phan vi thanh khoan cat ngang theo qv 7 ngay, tuoi niem yet (ngay, tran 720), so gio lien tuc trong trang
thai LEV toi k, so ung vien cung coin trong 7 ngay truoc, thay doi ln(OI) 24 h va 72 h (neu co chuoi OI), thay doi f so voi 24 h truoc.
Muc thi truong: loi suat EW alt 3 / 7 / 14 ngay va BTC 7 / 20 ngay (dung mkt.py cua B2), do bien dong BTC 7 ngay, ti le coin dang o trang
thai LEV (z >= 2,5) va trong pool (z >= 1,5) tai k, so ung vien cung gio.
Dac trung nao KHONG dung duoc tu du lieu co san => bo va ghi vao bao cao (khong thay bang dac trung khac sau khi thay ket qua).
Kiem nhan qua bat buoc: xao tron / doi du lieu sau gio k khong lam doi dac trung tai k (test tu dong, >= 200 ung vien ngau nhien).

## 5. Model (khong HPO, khong early stopping, khong chon dac trung)
- M1 (CHINH): LightGBM hoi quy L2 tren nhan; num_leaves 8, max_depth 3, min_child_samples 100, learning_rate 0,03, n_estimators 300,
  subsample 0,7 (bagging_freq 1), colsample_bytree 0,7, reg_lambda 10; 10 seed (0..9); diem = trung binh 10 seed. Trong so mau nhu muc 2.
- M2 (phu, mo ta): Ridge alpha 10 tren dac trung da doi sang hang phan vi theo tap train.
- Moi nam kiem Y train MOT lan tren tap train cua Y (khong train lai trong nam).
- Diem OOF trong tap train: GroupKFold 5 phan theo QUY lich; dung de dat nguong.

## 6. Luat giao dich va danh muc
- Tang danh muc = B1 (port.py) khong sua: 1x, tong phoi nhiem toi da 60 % equity, co lenh = equity x 0,60 / K, moi coin 1 vi the, het cho thi
  bo; trong cung mot gio xep theo DIEM giam dan (thay cho s). Equity moi nam kiem bat dau lai nhu fold B1.
- Nguong vao: T20 = chi vao khi diem >= phan vi 80 % cua diem OOF tap train (CHINH); T10 = phan vi 90 %; T0 = diem > 0.
- K: 5 (CHINH); 3 va 10 (lan can). => 9 bien the (nguong x K); bien the CHINH = M1 + T20 + K5 + exit_Y.
- Luu y ghi truoc: xep theo diem chi tac dung trong cung gio; phan lon tac dung cua model den tu nguong.

## 7. Doi chung (cung pool, cung exit_Y, cung danh muc, cung nam kiem)
- BL_S20: khong model, xep theo s, chi vao khi s >= phan vi 80 % cua s tren tap train.
- BL_Z30: luat goc z >= 3,0 (ung vien B1 W7_E0_3.0), xep theo s.
- RAND: giu ngau nhien ung vien trong pool voi xac suat = (so ung vien qua nguong cua bien the CHINH trong nam Y) / (so ung vien pool nam Y),
  xep ngau nhien; 500 luot; p = ti le luot co tong loi nhuan 2 nam >= bien the CHINH.

## 8. Tieu chi (chot truoc; cham tren WFO 2024 + 2025 cua bien the CHINH)
P1 loi nhuan rong 2024 > 0 VA 2025 > 0.
P2 tong 2 nam > BL_S20 va > BL_Z30; rieng 2024 cung tot hon ca hai.
P3 RAND: p <= 0,05.
P4 so lenh >= 30 moi nam va >= 100 tong.
P5 bo 5 % lenh loi nhat (tinh tren 2 nam) thi tong van > 0.
P6 on dinh seed: >= 8 / 10 model mot-seed (chay rieng qua ca quy trinh) co tong 2 nam > 0.
P7 maxDD (MTM xau nhat trong nen, nhu B1) <= 25 % o tung nam.
P8 lan can: >= 5 / 8 bien the con lai co tong 2 nam > 0.
- Du P1..P8 => "B3 DAT": lam tiep B4 (DCA) va B5 (toi uu gop + dong bang), sau do sim ghep voi he long, roi moi toi holdout 2026.
- Dat P1 + P3 + P4 nhung thieu muc khac => "B3 CO TIN HIEU, CHUA DU": bao owner so thuc, owner quyet.
- Con lai => "B3 KHONG DAT": bao owner so thuc + khuyen nghi; owner quyet.
- So in-sample (train) chi bao kem, ghi ro nhan "in-sample", KHONG dung de ket luan.

## 9. Bao cao mo ta bat buoc (khong vao tieu chi)
So ung vien / dot / nam; exit_Y; IC hang (Spearman diem - nhan) tung nam kem khoang tin cay bootstrap theo dot; bang 10 nhom diem; do quan
trong dac trung (gain + hoan vi tren nam kiem); loi nhuan theo thang; lenh te nhat; so lenh trung coin; M2 va 8 bien the lan can; Y = 2023
(train 2022) neu dat C0, neu khong thi ghi "khong du mau". Dem so thu: 9 bien the x 2 model + 3 doi chung.

## 10. Ky luat
prereg (file nay) -> DEV (agent Opus) -> A1 audit code (agent khac) -> RUN -> A1 audit ket qua -> MASTER tu kiem >= 3 so -> bao owner.
DEV duoc: dung pool, dem C0, dung dac trung, viet test, chay thu quy trinh tren du lieu GIA. DEV KHONG duoc train / cham tren du lieu that
truoc khi A1 PASS. Viec nang tren Oracle qua flock oracle_heavy.lock. Python dung logging. Khong doi luat sau khi thay so; sai sot => ERRATA
commit truoc khi chay lai.
