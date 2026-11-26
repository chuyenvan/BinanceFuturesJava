# MASTER_NOTE LEVZ tang B3 (sort bang model tren pool z >= 1,5) - 2026-11-26 17:47 +0700
Prereg 30a8c413 + ERRATA1 308cd1fc. Code A1 PASS-WITH-MINOR (A1_B3_CODE.md, 2 vong, sha256 11 / 11 khop luc chay). Chay that 16:30-16:57.
Ket qua A1 XAC NHAN (A1_B3_RESULT.md: train lai doc lap, lech 0). MASTER tu kiem tu ledger: CHINH 2025 n = 220, tong net -3256,03,
bo 11 lenh loi nhat => -4889,68, lenh te nhat -418,0 (khop report).
KET LUAN THEO ERRATA1 E2: "B3 KHONG DAT".
- Pool: 28 864 ung vien / 2 730 dot; theo nam (dot): 2022: 25; 2023: 644; 2024: 1 632; 2025: 429. Tin hieu gan nhu khong ton tai truoc 2023.
- WFO 2025 (khong nhin truoc, train 2022-24, exit_2025 = SL 30 % / H 24 / arm 7 % gap 2 %): bien the CHINH M1 + T20 + K5 = -32,6 %, 220 lenh,
  maxDD 36,2 %; ca 9 bien the M1 va 9 bien the M2 deu am; 10 / 10 model mot-seed am; RAND 500 luot p = 0,97 (model KEM chon ngau nhien:
  trung vi ngau nhien -12,1 %); IC diem - nhan = -0,071 (CI95 [-0,143; -0,001]). Q1..Q8: chi Q4 (so lenh) dat.
- Doi chung cung nam, cung thoat: BL_S20 (pool rong, xep theo s) -5,1 %; BL_Z30 (luat goc z >= 3,0) +20,5 %, 87 lenh, maxDD 9,2 % - day la
  dung ket qua F3 cua B1 (khong phai phat hien moi), thoat duoc chon tu du lieu < 2025.
- CV theo quy [co nhin truoc]: C1 7 / 12 (truot), C2 truot, C3 dat. WFO 2024 [duoi nguong mau, chi mo ta]: CHINH -50,8 %, IC -0,081.
- Giai phau (A1): diem model NGUOC dau voi nhan tren nam kiem o ca hai nam; khong phai loi code (IC in-sample +0,51; thu tay 20 / 20 dung
  dau) ma la quan he dac trung - nhan DAO CHIEU giua cac quy / nam (IC OOF tung quy -0,45..+0,40); dac trung model dua vao nhieu nhat la
  dac trung che do thi truong (btc20, btcvol7, ew*), khong ben. Noi rong pool xuong z < 3 lam XAU (BL_S20 < BL_Z30).
- Duoc noi: "model sort khong hoc duoc gi dung duoc sang nam sau; noi pool lam xau; luat goc z >= 3,0 van la ban tot nhat va nam 2025 no
  lai that (+20,5 %) voi thoat chon khong nhin truoc". Khong duoc noi: so CV, so 2024 nhu bang chung; "dao dau diem la co edge" (hau kiem).
- He qua cho chuong trinh: B5 (dong bang) se KHONG co tang sort bang model; pool giu z >= 3,0 xep theo s. Tiep: T1 (ky thuat lenh) dang chay.
