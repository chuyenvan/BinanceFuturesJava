# MASTER_NOTE LEVZ tang S2 (tin hieu rolling / cat ngang) - 2026-11-26 23:20 +0700
Prereg 74ec941e + ERRATA1 5f917679 + ERRATA2 e6a2ad65. Code A1 PASS-WITH-MINOR 2 vong (A1_S2_CODE.md; tin hieu doi chieu doc lap 0 lech).
Chay that 26/11: grid + select Oracle, rand 500 luot tren 4 kernel Kaggle (chay thu khop tuyet doi Oracle), report Oracle.
Ket qua A1 XAC NHAN (A1_S2_RESULT.md: tu cai lai luat WFO trung 15 / 15 cap; port.run 52 o lech <= 1,4e-15; p_wfo tinh lai khop).
KET LUAN: ca 4 tap moi "KHONG HON D0" (truot S-a, S-b, S-c).
- Trung vi top-20 WFO (2023 / 2024; 2025 khong cham duoc o tap nao): P5 -39,2 % / khong cham; P5b -32,6 % / -7,9 %; P6a -30,6 % / -21,5 %;
  P6b -17,6 % / -27,8 %. p_wfo: 0,96 / 0,59 / 0,43 / 0,32. So nam cham duoc: P5 1; P5b, P6a, P6b 2; REF 0.
- Ti le cau hinh co lai Y22 / Y23 / Y24 / Y25 (mo ta toan luoi): P5 100 / 0 / 21 / 29 %; P5b 99 / 3 / 11 / 8 %; P6a 95 / 34 / 2 / 55 %;
  P6b 82 / 43 / 3 / 38 %; REF 96 / 66 / 49 / 97 %.
- "Khong cham duoc" la he qua DUNG cua luat (gop = min qua fold train + plateau), khong phai loi: 2025 chi 4-8 cau hinh lai ca 3 nam train.
- A1 (mo ta, ngoai tieu chi): loi suat moi lenh tru short ngau nhien cung nam: 2022 +1,7..+3,6 diem %; 2023-24 phan lon am; 2025 ~ 0.
  Alt EW: 2022 -82 %, 2023 +107 %, 2024 +6 %, 2025 -71 % => nam 2025 alt giam manh ma tap moi van lo / hoa: khong phai thuan beta am;
  phan du doi dau theo nam.
- Duoc noi: "tin hieu kieu rolling / cat ngang (cang tuong doi, chu yeu tu OI) KHONG co edge de short; kem ro so voi luat goc z >= 3,0".
  Khong duoc noi: "2022 co edge" (nam train); trung vi luoi 2025 duong cua P6a / REF nhu ket qua WFO; "chi la beta".
- He qua: pool cua he short giu D0 z >= 3,0 (W7). Huong tin hieu con mo: dieu kien vao (T2), khong phai noi rong dinh nghia.
