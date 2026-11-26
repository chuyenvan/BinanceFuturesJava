# PREREG_LEVZ_B3_ERRATA1 - sau khi DEM pool (chua tinh nhan, chua train, chua cham gi)
Chot boi MASTER 2026-11-26, sau bao cao dem cua DEV (out/cand_b3.json, out/exitsel_b3.json). Tai thoi diem nay thu muc levz_b3 chi co
pool_b3.npz + 2 file json dem; KHONG co bang nhan, KHONG co model. Prereg goc: 30a8c413.

## Su that da thay (chi la so dem + lua chon thoat tu luoi B1 cua cac fold < Y)
- Pool W7 E0 z >= 1,5: 28 864 ung vien, 2 730 dot. Theo nam (ung vien / dot): 2022: 200 / 25; 2023: 6 686 / 644; 2024: 18 431 / 1 632;
  2025: 3 531 / 429. => tin hieu gan nhu KHONG ton tai truoc 2023; 60 % so dot nam o 2024. DEV thuc te chi co 3 nam.
- C0: Y = 2024: 500 dot train sau purge (can >= 600) => KHONG DAT. Y = 2025: 2 297 dot => DAT. Y = 2023: 25 dot => KHONG DAT.
- exit_2024 = SL 50 % / H 336 / arm 3 % gap 2 %; exit_2025 = SL 30 % / H 24 / arm 7 % gap 2 %. Hai lua chon khac han nhau => ghi nhan TRUOC
  khi co ket qua B3: luat chon thoat khong on dinh giua cac nam (khop voi B1). exit_2023 khong tinh duoc dung luat => khong lam Y = 2023.

## E1. Giu nguyen C0 (KHONG ha nguong 600)
Y = 2024 KHONG duoc cham chinh thuc. Van chay WFO 2024 (train 2023, exit_2024) nhung dan nhan "DUOI NGUONG MAU - CHI MO TA", khong vao tieu chi.
He qua: tieu chi P1..P8 (2 nam) cua prereg goc KHONG the dat => ket luan "B3 DAT" theo prereg goc la KHONG THE. Khong sua dieu nay.

## E2. Thang cham thay the (chot truoc khi co nhan; bang chung YEU HON thang goc - phai ghi ro khi bao owner)
(A) WFO 2025 (train 2022-2024 sau purge, exit_2025, bien the CHINH M1 + T20 + K5) - con so khong-nhin-truoc DUY NHAT:
 Q1 loi nhuan rong 2025 > 0. Q2 > BL_S20 va > BL_Z30 (2025). Q3 RAND 500 luot: p <= 0,05 (2025). Q4 >= 30 lenh. Q5 bo 5 % lenh loi nhat
 van > 0. Q6 >= 8 / 10 model mot-seed > 0. Q7 maxDD <= 25 %. Q8 >= 5 / 8 bien the lan can > 0.
(B) CV theo quy (KHONG phai khong-nhin-truoc: model du doan mot quy duoc train bang ca cac quy sau no; chi do tinh on dinh cua quan he
 dac trung - nhan): cac quy 2023Q1..2025Q4 (12 phan), moi phan giu lai 1 quy, train tren cac quy con lai + nam 2022, purge hai dau
 (bo ung vien train co gio vao trong [dau quy - H - 24 h ; cuoi quy + H + 24 h]), nhan theo exit_2025, M1 10 seed.
 C1 IC hang (Spearman diem - nhan, co trong so dot) > 0 o >= 9 / 12 quy.
 C2 danh muc chay lien tuc 2023-2025 bang diem OOF (K5; nguong = phan vi 80 % cua toan bo diem OOF - ro ri nhe o nguong, da ghi): loi nhuan
 rong > 0 o CA BA nam 2023, 2024, 2025 va tong > BL_S20 cung khoang.
 C3 (lan can) lap lai C2 voi nhan theo exit_2024: tong 3 nam > 0.
- Du Q1..Q8 + C1 + C2 + C3 => "B3 DAT MUC YEU (1 nam WFO + CV)": lam tiep B4 (DCA) va B5 (toi uu gop, dong bang), roi sim ghep he long; phep
  thu that la holdout 2026.
- Dat Q1 + Q3 + Q4 nhung thieu muc khac => "B3 CO TIN HIEU, CHUA DU": bao owner so thuc, owner quyet.
- Con lai => "B3 KHONG DAT": bao owner so thuc + khuyen nghi; owner quyet.
- Moi con so cua (B) va cua WFO 2024 phai mang nhan "CV - co nhin truoc" / "duoi nguong mau" trong moi bao cao.

## E3. Viec cua DEV thay doi
Them cv_b3 (phan B) + test ro ri cho CV theo quy (purge hai dau). Cac muc khac cua prereg goc giu nguyen (dac trung, model, danh muc, doi
chung, ky luat DEV khong train / cham tren du lieu that truoc khi A1 PASS).
