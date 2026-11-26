# A1_B1_ENGINE - audit doc lap engine thoat 1 phut + luoi/chon/WFO/doi chung LEVZ B1 (TRUOC khi chay luoi 7 020)
A1 (Opus), 2026-11-26 04:43-05:06Z. Khong sua code DEV, khong commit, khong chay grid/select that, rand chi 2 luot thu. Khong so loi nhuan.
Code A1: a1/ref_b1.py (tham chieu doc lap, KHONG import DEV), cmp_b1.py, mm_check.py, la_b1.py, break_b1.py, wfo_b1.py, tim_b1.py; ket qua a1/*.json.

## VERDICT: PASS-WITH-MINOR - DUOC chay pipeline exits all -> grid -> select -> rand reduced 100. Khong co loi BAT BUOC.

## 1. Toan ven
- SHA256SUMS.txt 15/15 OK. w3/levz2/SHA256SUMS.txt 0 loi; khong file nao trong w3/levz, w3/levz2 co mtime >= 2026-11-26 (levz khong co file SHA - chi kiem mtime).

## 2. paths / memmap (mm_check.json - doc parquet goc, khong code DEV)
- 556 mau (coin, phut) ngau nhien + phut cuoi 2025-12-31 23:59 + phut nen dau + phut truoc nen dau: 0 lech (gia tri = float32(close nen cuoi co ts <= phut), NaN truoc nen dau => ffill dung chieu).
- has1m va CLH 260 mau gio: 0 lech. first bar 631/631 trung. So nen moi coin = NMIN - first - tong gap cho MOI coin (=> gaps.npz day du, 134 gap), 0 nen nam trong gap.
- Reader: max ts doc duoc = 1767225540000 (23:59), assert < 2026; khong mo file 2026 (ca funding).
- Quy uoc thoi gian: sig t = "info up to t" (levz2 sig.py); vao = close nen 1m open_time t (= t + 1 phut) => khong look-ahead, tre 1 phut dung prereg 2.

## 3. exits.py vs engine tham chieu doc lap (vong lap tung phut python, gia tu parquet goc, funding tu funding lake goc)
- 300 ung vien ngau nhien x 195 bo = 58 500 o: j / ly do / gia thoat / funding / mx / mxh: 0 lech (dung sai 1e-9 tuong doi).
  Phan bo ly do tham chieu: sl 8 207, trail 34 744, time 15 544, eod 5, miss 0 (miss chi kiem bang ca tong hop).
- Vong lap ngay tho tung cau hinh (25 x 195): 0 lech voi cach tach su kien.
- Funding doc lap tu ts goc (lech toi da 47 ms so voi moc gio): trung tuyet doi; dau: rate > 0 => short NHAN (+N x rate x gia moc / p0); ky tai T_k khong tinh; ky tai moc h tinh khi j >= 60h - 1.
- float32 (MINOR M1): chay tham chieu tren gia float64 => 19/58 500 o (2/300 ung vien) doi phut thoat 1-3 phut, KHONG doi ly do
  (1 ca SL50 tre 1 phut trong phut squeeze: xr +0,093; 1 ca trailing tre 3 phut: xr +0,0011); cung phut thi |lech xr| <= 1,0e-7.
  Do mong manh o dung nguong (close == nguong) ton tai ca voi float64 (gia theo tick). Khong can sua truoc khi chay luoi (float64 = 10,8 GB, dia khong du).

## 4. port.py vs tang danh muc tham chieu doc lap (fold 2024, ung vien E0/E1 A1 tu dung tu sig parquet + has1m tu parquet goc)
| cfg | tap ung vien 2024 | so lenh / khoa (c, ke, kx, j, ly do) | N, net | eq, eq_worst theo gio | maxDD, maxDD worst |
| c1 W14 E0 z2,5 K10 SL50 H24 off | 3117 = 3117 | trung (320) | <= 1e-13 | <= 1e-15 x von | <= 5e-16 |
| c2 W7 E0 z3,0 K3 SL15 H24 10/5 | 1055 = 1055 | trung (131) | <= 1e-13 | <= 1e-15 | <= 2e-16 |
| c3 W7 E0 z3,5 K5 SL30 H720 3/2 | 415 = 415 | trung (95) | <= 1e-13 | <= 1e-15 | <= 3e-16 |
| c4 W14 E1 z3,0 K3 SL30 H168 5/3 | 260 = 260 | trung (70) | <= 1e-13 | <= 1e-15 | <= 4e-16 |
Bat bien ke toan run_all 4 fold c1-c4: acct_err <= 1e-12, cash_end - eq_end <= 1,5e-11.

## 5. Look-ahead tren du lieu that (la_out.json, code DEV + wrapper)
Xao gia 1m sau phut 60kc (nhan exp(N(0;0,15)) tung phut), FR sau gio kc, thay ung vien sau kc bang ung vien ngau nhien; kc = 2024-04-01 va 2024-07-01; c1-c4:
lenh dong truoc moc, lenh vao <= moc (ca size), eq va eq_worst moi gio <= moc: TRUNG HET (8/8); sau moc co doi (kiem co hieu luc).

## 6. grid / select / WFO / rand
- grid: 7 020 cau hinh, 7 020 khong trung, = tich prereg muc 3, cfg_id 0..7019, xidx dung. Resume: part ghi tmp + replace, gop drop_duplicates. check_acct chi kiem acct_err (M3).
- select_b1.rule == cai dat A1 doc lap (chon top-1, passing20, valid20) tren 6 luoi gia x {in-sample, WFO 2024, WFO 2025}: 18/18 trung. Hang xom (ADDENDUM1 A) trung cho ca 7 020.
- Ro ri WFO: hoan vi + nhan he so cac cot F2/F3/DEV (Y=2024) va F3/DEV (Y=2025), 5 lan x 6 luoi: lua chon khong doi 12/12; bay (cau hinh tot nhat o fold kiem, xau o fold chon) khong duoc chon va khong vao top-20 12/12.
- rand_b1 (lop W7 E0 z3,0): so dot = 385 (tinh lai doc lap = 385), rut 385, theo thang = so dot that tung thang, 100 % trong universe & co nen 1m, khong trung; chay 2 luot end-to-end OK (585 cau hinh/luot).

## 7. CHOICES_B1 (22 muc)
- Khong muc nao DOI LUAT so voi prereg + ADDENDUM1 (A-E da chot dung nhu code).
- Lac quan nhe (giu, ghi nhan): #10 thoat dung phut j = 60h - 1 (close nen ket thuc dung moc) van nhan funding moc do (quy uoc B0 CHOICES2 #12) - chi anh huong ~1/60 lenh SL/trailing, 1 ky funding; khong dang ke. #8 miss/time trong gap dong o close cuoi (dung prereg 1).
- #14 worst bat loi hon B0 (tot). #4 vao can nen 1m tai T_k (trung tinh).
- Can sua nhan: CHOICES B / docstring select_b1 goi top-20 "chinh" = passing20 (co cao nguyen) - NGUOC ADDENDUM1 B. So cho tieu chi DI TIEP B2 = wfo[Y].top20_valid (M2).
  Cau ADDENDUM de xuat: "Tieu chi muc 5 'trung vi top-20 WFO' doc tu select_b1.json wfo.<Y>.top20_valid; top20_rule chi bao them."

## 8. Test
- DEV 57/57 PASS (chay lai tren ban sao). Ca pha A1 15/15 PASS (break_out.json): SL+trailing cung phut; trailing kich hoat phut cuoi truoc time-stop / dung phut time-stop;
  gia phang (195 bo => time, xr 1, funding 0); SL dung nguong; trailing thoat phut ke dung gap; gap > 24 h luc giu (time truoc miss, flag; gap = 1 440 khong miss);
  funding phut vao / ra (j = 58 khong nhan, j = 59 nhan, notional gia moc); H720 cham cuoi du lieu (eod nv-1); thoat j = 60 => cho trong gio ke (j = 61 => sau 2 gio);
  hai ung vien cung s => sym nho truoc; lenh mo qua bien fold (eod mk(kl), funding toi kl, net tinh tay); cooldown 72/73; size theo MTM; khong vao o kl.

## 9. Thoi gian + RAM (do mau, Oracle, 1 tien trinh)
- exits all: 3,9 ms/ung vien => ~35 s cho 8 524; exits.npz ~0,26 GB.
- port run_all (4 fold): 0,03-0,06 s (ca H720) => luoi 7 020 ~6 phut 1 tien trinh, ~2-3 phut x 3.
- rand: 21,7 s/luot (lop W7 E0 z3,0, 385 dot) => reduced 6 lop x 100 = 600 luot ~ 1,2 h x 3 tien trinh (lop z2,5 dong ung vien hon: co the toi ~2 h).
- RAM dinh 1 tien trinh (gom bang thoat toan union): 1,2 GB => 3 tien trinh ~2-4 GB; dia moi ~0,3 GB.

## MINOR
M1 float32 memmap (muc 3) - khong sua. M2 nhan top-20 (muc 7) - sua doc/nhan truoc khi doc ket qua.
M3 grid_b1: them assert |eq_end_ledger_minus_eq| <= 1e-6 cho 4 fold (hien chi check acct_err).
M4 grid_b1/rand_b1 resume khong gan part voi hash exits.npz/code: xoa out/grid_b1_parts, out/rand_b1_parts truoc lan chay that neu co.
M5 rand_b1 khong co tham so chay 1 lop rieng (ADDENDUM1 C truong hop WFO top-1 2025 la E1) - them khi can.
## KHONG kiem duoc
Chat luong nen 1m so voi san; bien dong trong phut; miss tren du lieu that (0 ca trong mau); thoi gian rand lop z2,5; select/breakdown tren luoi that (chua co).
