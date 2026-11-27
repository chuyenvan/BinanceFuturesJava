# A1_B4_CODE - kiem toan code doc lap B4 (DCA short LEVZ) - 2026-11-27
Phan quyet: PASS-WITH-MINOR (engine + port mapping dung tuyet doi tren tham chieu doc lap; 1 diem luat can MASTER chot truoc RUN, xem #9).
Khong chay grid/select/report tren du lieu that; khong tong hop loi nhuan.

1. PASS sha256 = SHA256SUMS.txt (9/9 OK). Luoi 60 xi x 3 z x 3 K = 540, 108 / kieu (5 kieu), dung A2-A4.
2. PASS engine (exits_b4.py): leg them L = p0(1+a l), khop phut i>=1 close >= L(1-1e-12) (searchsorted tren cummax p[1:nv], L108-110),
   gia khop = L, phi 0,07 %; N = 1/(1+n); avg theo khoi luong (segs L132-144); SL close >= avg(1+s) theo segment (avg moi ngay phut khop),
   truot 0,3 %; trailing arm avg(1-a), gap tu day nhu B1, truot 0,1 % (B1); STATE = gio T1; TIME 60H; uu tien SL>TRAIL>STATE>TIME>MISS;
   retb = sum N(1-X/L) - FEE N(1+nf) - FEE sum NX/L + fund (phan chua khop = 0). Funding: dau dung (fh B1 = nhan khi FR>0), notional
   tung leg qty x close moc. LUU Y quy uoc moc: khop o f = 60h-1 (close dung luc moc) KHONG tra, nhung thoat o j = 60h-1 CO tra (bat doi
   xung 1 phut); tren 3 960 phep so chi 10 (0,25 %) lech neu dung f <= 60h-1, do lon 1 lan funding 1 leg -> khong dang ke.
3. PASS tham chieu doc lap (vong for cua toi, viet truoc khi doc test_b4): 330 lenh that ngau nhien (seed 11) x 12 cfg (4 kieu DCA x 3 thoat,
   ca 2 SL, ca 2 H) = 3 960 phep so: j, ly do, nleg, avg, fund, retb, xraw lech 0 (max |d| 2,2e-16); port identity 1-xr-FEE(1+xr)+fund
   == retb lech 0 (max 2,5e-16); worst lech 0; MTM gio 4 kieu (1-mk-FEE vs MTM tu tinh) lech 0 (max 1,8e-15). nleg 1/2/3 = 2418/1128/414.
4. PASS nhan qua: fill tu cummax tien to, chi tinh khi f <= j; test c (doi gia/funding sau j) lap lai PASS; STATE dung bang T1 (gio da chot).
   Moc thoi gian max: k max 2025-12-31 10:00, close thoat max 2026-01-01 00:00 = close cua nen mo 23:59 (70 dong EOD) -> khong du lieu >= 2026.
5. PASS-LUU Y port.py: notional = tron ngan sach (test e + doc code); port net/N == retb chinh xac cho moi lenh KHONG EOD (dai so + 3 960 so
   that, gom 1 leg TIME, 2 leg + SL, 3 leg + trailing). MTM gio dung. LOI NHO: lenh dong cuong buc cuoi fold (EOD, port L109 xr = mk[h])
   bi tru them Nu FEE(1-FEE) (Nu = phan ngan sach chua khop) vi mk dinh gia phan chua khop (1-FEE) chu khong (1-FEE)/(1+FEE); bat loi cho
   DCA <= 0,05 % mot cho / lenh EOD (toi da K lenh / fold) -> khong doi ket luan. adjw (eq_worst) lech bao thu ~0,07 % x Nu tuong tu.
   Phi leg khong tinh 2 lan / khong sot (port tinh phi vao tron ngan sach, hoan phan chua khop qua xr_eff).
6. PASS select/report: rule() restrict chi cot fold < Y (assert); hang xom trong kieu (subset + neigh); top-20 = valid20 (nhu T1/T2);
   V-a..V-e dung cong thuc/nguong A6; doi chung NONE cung quy trinh; DEV gan [in-sample]. LUU Y: V-e chi tren top-1 (CHOICES #12) - doc hop ly.
7. PASS-LUU Y test: chay lai test_b4 all = log (a-g PASS, sha g 3f761bef). Dot bien: M1 SL tu p0 -> test b, f FAIL (d KHONG bat);
   M2 bo phi leg them (retb + xr nhat quan) -> test b, d FAIL. Ca hai bi bat. Yeu: test b so mk/fh voi Kind cung code (khong doc lap) -
   da bu bang tham chieu cua toi; test e bo qua lenh EOD (che loi #5). Test h: du lieu rand gan nhu KHONG co cfg hop le (seed 100: n_valid 0
   moi kieu ca 2 nam; seed 101: 0-3), NONE khong cham duoc => V-b False tu dong -> "bao dong gia 0/80" gan nhu vo nghia (khong do duoc
   do nhay that cua tieu chi); chi chung minh pipeline noi duoc 'DAT' (pump).
8. PASS khoa: grid/select/report khong co khoa hoac --real WRONG -> SystemExit LOCKED, out/ khong doi. logging, khong print. Tat dinh (test g).
9. Khong dong y / can MASTER chot TRUOC RUN:
   - CHOICES #12: NONE khong cham duoc nam Y => V-b False. Day la SIET luat (prereg chi noi "hon KHONG DCA"); neu NONE khong co cfg hop le
     thi doc tu nhien la so voi 0 (khong vao lenh) => V-b = V-a. Anh huong: co the ha 'CO CAI THIEN'/'DAT' thanh 'KHONG HON'. Can chot 1 cach.
   - CHOICES #14 / test h: xem muc 7 (khong chan RUN).
   - CHOICES #5/#6: dung, tru loi nho EOD (#5 tren).
Viec DEV: BAT BUOC truoc RUN: khong (sau khi MASTER chot #12). Nen sua (nho): EOD fold-end tinh dung phan chua khop; test e kiem ca EOD;
test d them ca SL tu avg khac SL tu p0. sha256 da kiem = SHA256SUMS.txt (common 7d121666, exits 8983fec1, fake 30617911, grid 2b604e32,
select 9480b88d, report e9cda04e, test f4afda1b).

## BO SUNG E1 (2026-11-27 13:45)
- sha256: 5 file khong doi (common 7d121666, exits 8983fec1, fake 30617911, grid 2b604e32, select 9480b88d); report_b4 = 5ba43821,
  test_b4 = 5692693c; SHA256SUMS.txt khop 10/10 file tren dia.
- report_b4.py: doc toan file, chi criteria() doi dung nhu DIFF_E1.txt; build / to_md / main / t20 giu nguyen so voi ban A1 da doc.
  V-b: NONE khong cham duoc nam Y (valid20 rong) => moc 0, tuc V-b(Y) = top-20 kieu > 0; NONE cham duoc => top-20 vs top-20 nhu cu;
  kieu khong cham duoc => V-a, V-b False. Note in "KHONG DCA khong cham duoc nam Y" + trung vi 108 cfg NONE o fold thu (kind_median_test,
  chi mo ta, khong vao tieu chi) = dung ERRATA1 E1. (Note NONE lap lai o ca 4 dong kieu DCA - chi hinh thuc.)
- test_b4.py: test a-h giu nguyen (cung so dong / vi tri ham, moi assert va dung sai trung ban cu); them test i, kiem du nhanh: NONE khong
  cham + kieu > 0 / = 0 / < 0, NONE cham mot nam, NONE cham ca hai (so sanh chat >), kieu khong cham. Chay lai test_b4 all (a-g + i):
  PASS het, sha test g 3f761bef = ban truoc.
- Phan quyet cuoi: CHO RUN. RUN phai doi chieu sha256 day du:
  7d121666b5605d54638c201e92dd0bf0b2b2894335df322438089c5e24d535f6  code/common_b4.py
  8983fec1131ee823392b90d6b04bea49648e9850223267e8937db92fe9065d18  code/exits_b4.py
  30617911a5b603b11124b33ff12c57f1861542a9b4fe95e10f701d443a4cb132  code/fake_b4.py
  2b604e324bd1ed698ad8808f9f6e748141eedb08e13851c1c0788275b90aca0b  code/grid_b4.py
  9480b88d5676eeb05dc92e25a6b3c1d0f27a2aa899191f2332aa18ddc633bed7  code/select_b4.py
  5ba438216f303f8b44cfcdc76e137ec8efaf77c1f13e5d985b9a16625d8f8b66  code/report_b4.py
  5692693c3b294284e912690324d25c0f0458efc5c0279ad9e3d20a2e5af79157  code/test_b4.py
