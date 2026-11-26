# DEV_B1 - engine thoat nen 1 phut + cong cu luoi/chon/WFO/doi chung (PREREG_LEVZ_B1 @54f40792) - CHUA CHAY LUOI, cho A1 audit
2026-11-26. Khong co so loi nhuan nao trong file nay.

## 1. paths
- work/close1m.npy 5,42 GB (631 coin x 2 148 480 phut, float32, ffill) + gaps.npz (134 gap, 124 gap > 24 h) + hourly.npz (113 MB)
  + cand_b1.npz (0,8 MB; union 8 524 ung vien). Dung: ~8 phut (49 file thang, 0 dong loi, 0 trung). work tong 5,2 GiB.
## 2. Toc do (do tren X1/X2)
- exits: 2,73 ms / ung vien cho CA 195 bo thoat (1,4e-5 s / ung vien / bo); bang day du 8 524 ung vien ~23 s (exits.npz ~0,3 GB).
- port: 0,007-0,026 s / lan chay fold (DEV dai nhat) => ~0,04-0,06 s / cau hinh (4 fold). CHI do voi H = 24, trailing tat; H dai hon
  giu lau hon -> co the cham hon (chua do, khong duoc chay cau hinh khac).
- Uoc luoi 7 020: ~7 phut / 1 tien trinh => ~2-5 phut voi 3 tien trinh (+ nap ~1 phut).
- Uoc doi chung: moi (lop, luot) = exits cho <= 749 ung vien ngau nhien (~2 s) + 585 cau hinh x ~0,04 s (~25 s) => ~27 s.
  12 lop x 100 luot = 1 200 => ~3 h voi 3 tien trinh (sai so x2 neu H dai cham hon); 'reduced' 6 lop E0 x 100 => ~1,5 h.
## 3. Test: 57/57 PASS (test/test_report.json). Gom: SL/trailing/time/miss/eod tinh tay; so khop 195 bo thoat voi vong lap tung phut doc lap
  (3 duong ngau nhien, 0 lech); port so khop vong lap tung gio doc lap (10 bo, eq lech <= 1e-8); bat bien ke toan <= 1e-6 (45 x 3 lan chay);
  equity pha 1 = so cai; khong look-ahead gia (ca exits va port) va tin hieu; tat dinh; WFO bay; luat chon tai lap B0 (759, 69 hop le).
## 4. Doi chieu X1 / X2 voi B0 (B0 cfg_id 96 / 756; DCA tat) - so lenh, tap vao, ly do thoat (KHONG loi nhuan)
| | so lenh DEV/F1/F2/F3 B1 | B0 | tap (sym, gio vao) DEV trung | ty le SL DEV B1 / B0 | time B1 / B0 |
| X1 | 584/160/320/104 | 584/160/320/104 | 581/584 = 99,5 % | 2,40 % / 2,91 % | 97,4 % / 96,7 % (+ time_sub 0,17 %) |
| X2 | 287/75/126/86 | 287/75/126/86 | 284/287 = 99,0 % | 14,6 % / 16,0 % | 85,4 % / 83,6 % (+ time_sub 0,35 %) |
- Bang cheo ly do tren lenh trung: X1 sl->sl 14, sl->time 2, time->time 563, time_sub->time 1, eod->eod 1; X2 sl->sl 42, sl->time 4,
  time->time 237, time_sub->time 1. Khong co time->sl.
- Giai thich: (a) B0 kich SL bang HIGH gio cham muc stop; B1 chi khi CLOSE 1m >= stop => rau nen (wick) khong kich => it SL hon
  (6 lenh sl->time); B1 khong bao gio SL ma B0 khong SL. (b) Gia vao lech 1 phut (B1 = close nen open T_k; B0 = close nen gio ket thuc T_k):
  |lech| trung vi 0,17-0,21 %, q95 ~1 %, max 6,8 %. (c) Ung vien: B1 can nen 1m tai T_k, B0 can nen store => B1 nhieu hon 12 / 19 gio
  ung vien (khong mat cai nao cua B0). (d) 'time_sub' B0 (thieu nen store tai gio time-stop) la 'time' binh thuong o B1. (e) Khac thoi
  diem / ly do thoat lam doi trang thai cho trong => 3 lenh khac nhau moi cau hinh. Bat bien ke toan X1/X2 moi fold |err| <= 1e-12.
## 5. Diem A1 can soi
- exits_core: searchsorted tren cmax/cmin (nguong >= / <=), trailing tu phut kich hoat, uu tien SL>TRAIL>TIME>MISS, quy tac funding 60h-1<=j.
- port: kx = ke + ceil(j/60) (cho trong), EOD tai mk(kl), equity size = MTM truoc phi vao, 'worst' them N max(0, mxh - xr).
- path_of: gap > 1 440 phut tinh tu sau khi vao; ffill; cat 2025-12-31 23:59. paths.ffill_gaps.
- rand_b1: pool = universe & has1m; dem dot tren ung vien B1; thong ke max qua 585; p_max theo lop.
- select_b1: restrict()/rule() voi fold cho phep; hang xom trailing (CAN MASTER QUYET A); top-20 (B).
## 6. KHONG kiem duoc / suy doan
- Toc do voi H 168-720 va trailing bat (khong duoc chay) => uoc thoi gian la suy doan.
- Do phu 1m: chi biet so gap (134); chat luong gia 1m so voi san that chua doi chieu doc lap trong B1.
- Funding ky lam tron ve moc gio (B0 FR) - khong kiem lai tung ky.
- select_b1 / rand_b1 main va breakdown() chua chay tren du lieu that (chi test tong hop + luat chon tren grid B0).
- Thu tu nen trong phut: engine chi thay CLOSE 1m (dung prereg); squeeze trong phut khong thay duoc.
