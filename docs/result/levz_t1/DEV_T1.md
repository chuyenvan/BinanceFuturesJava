# DEV_T1 - LEVZ T1 (PREREG_LEVZ_T1 @186f2a5a + ADD1 45f45a5b) - CODE + TEST, CHUA CHAY LUOI THAT (cho A1 audit)
2026-11-26. Khong co so loi nhuan that nao trong file nay. Lua chon cai dat: CHOICES_T1.md (22 muc).

## 1. Thanh phan (code/)
- common_t1.py : hang so, luoi 5 ho, all_cfgs() = 9 468 cau hinh (BRK 1 620 | VOL 864 | PART 144 | STATE 144 | HEDGE 6 696), loader B1/B2.
- exits_t1.py  : engine thoat BRK / VOL / PART / STATE (nen 1m close, quy uoc B1); compute() cho ung vien bat ky; PartView; 'all' ->
                 work/exits_t1_<FAM>.npz (56 MB) + thong ke ve sinh.
- hedge_t1.py  : lop phu HEDGE (vong port.run B1 chep lai + chan long BTC / BTCETH; ADD1 A1-A3).
- grid_t1.py   : luoi 9 468 -> out/grid_t1.parquet (resumable, 3 tien trinh). KHOA: --real I_HAVE_A1_PASS.
- select_t1.py : thuoc do muc 4 (i)(ii)(iv); WFO = select_b1.rule khong sua.
- rand_t1.py   : doi chung ngau nhien moi ho x moi gate, 100 luot, lop W7 E0 z3,0; 1 part / (ho, gate, luot). KHOA --real.
- report_t1.py : T-a..T-e, ket luan, nhan 'gate hau kiem', moc B1, ly do thoat THAT. KHOA --real.
- fake_t1.py   : du lieu GIA cho test (c)(e)(f)(g)(h).   test/test_t1.py : test (a)-(h).

## 2. Lenh mot dong (chay SAU khi A1 PASS; kiem truoc: free -m available >= 4000, df >= 12 GB)
(da chay 2026-11-26 16:24, du lieu that, chi ve sinh) exits:
cd ~/claude_master/w3/levz_t1 && flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 python3 code/exits_t1.py all > logs/exits_all.log 2>&1
Luoi:
cd ~/claude_master/w3/levz_t1 && nohup flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 python3 code/grid_t1.py --real I_HAVE_A1_PASS > logs/grid.log 2>&1 < /dev/null &
Doi chung ngau nhien (sau luoi; resumable - chay lai cung lenh se tiep tuc):
cd ~/claude_master/w3/levz_t1 && nohup flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 python3 code/rand_t1.py --real I_HAVE_A1_PASS 100 > logs/rand.log 2>&1 < /dev/null &
Bao cao (sau luoi + rand):
cd ~/claude_master/w3/levz_t1 && flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 python3 code/report_t1.py --real I_HAVE_A1_PASS > logs/report.log 2>&1
Test (khong can khoa; (a)(b)(d) doc du lieu that chi o muc bang thoat):
cd ~/claude_master/w3/levz_t1 && nice -n 10 python3 test/test_t1.py a b c d e g h > logs/test.log 2>&1 && nice -n 10 python3 test/test_t1.py f > logs/test_f.log 2>&1

## 3. Uoc thoi gian chay THAT (do tren du lieu GIA, nhan theo so ung vien that)
Do (test f, 2 tien trinh, du lieu gia 10 coin ~900 ung vien union / lop z2,5 ~900, z3,0 ~770, z3,5 ~640; ~450 lenh DEV / cau hinh):
- sec / cau hinh (4 fold): BRK 0,042 | VOL 0,043 | PART 0,044 | STATE 0,043 | HEDGE 0,328 (theo z: 0,345 / 0,327 / 0,314).
  HEDGE bi chi phoi boi vong ~70 000 gio (DEV + 3 fold) cho moi cau hinh, it phu thuoc so ung vien.
- rand 1 luot (lop z3,0, ~770 ung vien ngau nhien gia): BRK 13 s | VOL 7 s | PART 1,8 s | STATE 1,4 s | HEDGE 383 s (1 116 cau hinh).
That: lop W7 E0 so ung vien 4 792 / 1 965 / 838 (z 2,5 / 3,0 / 3,5) - lon hon gia 1,3-5 lan; B1 that do 0,03-0,06 s / cau hinh tren cung
port. Dot that lop z3,0 = 385 (= so ung vien ngau nhien moi luot rand) - IT hon gia (~770).
- grid_t1 that (3 tien trinh): khong HEDGE 2 772 x 0,05-0,08 s / 3 ~ 1-2 phut; HEDGE 6 696 x 0,35-0,6 s / 3 ~ 13-22 phut. Tong ~15-25 phut
  (+ nap ~1 phut). Dia: out/grid_t1.parquet + parts ~ 15 MB.
- rand_t1 that (100 luot x 5 ho x 2 gate, 3 tien trinh): HEDGE 200 luot x ~330-400 s / 3 ~ 6,1-7,4 h; 4 ho con lai 200 x ~24 s / 3 ~ 0,45 h.
  TONG ~6,5-8 h (diem uoc ~7,5 h). Gan nguong 8 h cua MASTER; neu A1 muon nhanh hon => Kaggle (code chi can mm / FR / pools; resumable).
- report_t1 that: chay lai top-1 WFO (<= 10 x 2 nam) ~ 1 phut.
- exits_t1 all that: 24,7 s (da do).

## 4. Test (test/test_t1.py; bao cao json test/test_report_<phan>.json) - TAT CA PASS 2026-11-26
| test | du lieu | ket qua |
|---|---|---|
| (a) engine T1 (BRK khong TP; STATE khong kich) = bang thoat B1 khong trailing, 3 SL x 5 H | THAT, 600 ung vien | PASS 18 000 phep so, 0 lech (bang tung bit: j, rs, xr, fund, mx, mxh, flag) |
| (b) ban tham chieu vong for thuan Python (BRK / VOL / PART / STATE, ca u cua VOL, gio STATE tinh lai tu tin hieu) | THAT, 500 ung vien x 3 cfg / ho | PASS 1 500 lenh / ho, 0 lech (j, ly do, xr, fund, j1); u lech tuong doi max 3e-14 |
| (c) HEDGE h = 0 = B1 port.run_all | GIA | PASS 108 cau hinh, 99 595 lenh; trades + equity .equals(), moi cot metrics bang nhau |
| (d) khong nhin truoc: CL sau gio vao khong doi u; STATE khong dung hang tuong lai / chua chot (bo hang k+h => thoat muon hon); gia sau phut thoat khong doi lenh thoat | THAT, 300 | PASS 0 / 0 / 0 vi pham; u co dung hang k (299 / 300) |
| (e) tong net lenh (+ hedge_pnl) = thay doi equity; acct_err, eq_end_ledger_minus_eq, hedge_acct_err | GIA, 252 lan chay | PASS max |err| 1,7e-10 |
| (f) quy trinh tron grid 9 468 -> select -> rand (3 luot x 5 ho x 2 gate) -> report | GIA, 899 ung vien, 2 tien trinh | PASS; grid 1 161 s; rand 1 118 s; fake_report_t1.md mau |
| (g) tat dinh: tao lai du lieu gia, bang thoat, 98 cau hinh, 1 luot rand | GIA | PASS 0 lech |
| (h) nhanh 'miss' (gap > 24 h) - that KHONG co ca nao (B1 exits.npz: 0 miss, longgap = 0) | GIA, gap 2 000 phut | PASS 390 phep so voi B1 exits_core, 186 lenh miss + 51 PART miss, 0 lech |
| (i) report in ly do thoat THAT cua PART (tp / be), khong in ma da map | GIA | PASS be 304, tp 393 |
Sua sau (f): report_t1.to_md doi "ho|gate" thanh "ho / gate" (dau | lam vo bang md); fake_report_t1.md la ban TRUOC sua (cot dau bi tach).
Ghi chu: trong (f) PART khong co cau hinh qua tron luat chon (du lieu gia) nen muc ly do PART trong fake_report rong - da kiem rieng o (i).

## 5. Ve sinh bang thoat THAT (khong loi nhuan; logs/exits_all.log)
8 524 dong, 0 NaN xr / fund. Ti le ly do: BRK sl 36 % time 37 % tp 26 %; VOL sl 36 % time 53 % tp 10 %; PART sl 40 % time 37 % be 17 %
tp 6 % (ti le chot nua 19-53 % tuy cfg); STATE state 93 % sl 7 %. 0 'miss' o moi ho = KHOP B1 (B1 cung 0 miss, xem CHOICES 22).
VOL: 38 ung vien < 24 loi suat gio hop le -> SL tran 50 %; u trung vi 6,3 % / ngay (q05 2,7 %, q95 15,6 %).

## 6. A1 nen soi
- hedge_t1.run: chep vong port.run (thu tu xu ly thoat chi tai gio co ung vien); chan long can lai sau quyet dinh gio k; eq_worst A3.
- exits_t1.part + PartView (mang gio hieu dung), rt -> rs map; STATE dung hang k+h tai phut 60h; VOL u tu CL[k-168..k].
- select_t1 hang xom tung ho (CHOICES 17), T-e = bo 5 % lenh LAI nhat (+ hedge_pnl).
- rand_t1: cung tap ngau nhien cho moi ho / gate; G_EW14 loc ung vien ngau nhien theo gate gio vao.
## 7. KHONG lam / chua kiem
- Chua chay grid / select / rand / report that (khoa --real). Chua do toc do tren du lieu that (uoc tu du lieu gia, muc 3).
- Vi tri 124 gap > 24 h cua B1 so voi ung vien: chi biet ket qua (0 miss), chua kiem tung gap.
## 8. sha256 (SHA256SUMS.txt)
    c8074eb655ab4b1f61da573bcce5c7c217fb931a7a5802bb2b144f987b88fc05  code/common_t1.py
    1a50e86e441d02390cbad93c6398615450df344efc6e264ebe69b9f6d285ed7a  code/exits_t1.py
    281d8dbf8f41b2b0ca37ad691e6c29887d2e4ba821e8b63afc25a0cbbbeaa0dc  code/fake_t1.py
    b35f46ef51f36ab2574522898e252a19cb1401e4184d025986e9c29a8c02cb17  code/grid_t1.py
    d59531a8c6e4a0ba1fbcd080fc903a880dee1e3981e907416bde59d290387a8d  code/hedge_t1.py
    40a613494aa85271645dcca836057564815723fb8eb04f34e61d052cab8fc949  code/rand_t1.py
    32c9ae823884b77451914183bac00393cac1ffb932808c0cb7bfdcfeb6d70e2a  code/report_t1.py
    36370bd1bdae8b60904bcf24601ce091693bc08d92e5c8eb3bfccbb4c4f48391  code/select_t1.py
    74c40afbb8eb2a19a7834c04586b66b9e904d3d976a7789ef5eed706ffb88f2e  test/test_t1.py
