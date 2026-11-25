# A1_LEVZ2_SIM_V2 - audit vong 2 (ADDENDUM2 c10a681b), 2026-11-25. Khong sua code DEV, khong commit, khong bao loi nhuan.
sha: sim.py 874e561f, rand.py 8927aa4b, grid.py 41554e65 (khop SHA256SUMS.txt); select.py 00a491e8, sig.py, px.py khong doi (mtime 21:10/21:15).

## VERDICT: PASS - duoc chay `grid && select && rand` (lenh README).

## 1. Doc code (khong con ban sao cu trong sandbox => doc lai toan bo run() + rand.py + grid.py, doi chieu ban v1 da audit)
- G2 sim.py nhanh thoat: open >= stop => SL tai open, khong DCA; nguoc lai DCA (neu chua DCA, khong trail-hit, high >= 1,10 p0, tran cho phep)
  ROI moi kiem high >= stop tren khoi luong moi. Dung chu. (open >= 1,10 p0 nhung < stop: van DCA tai 1,10 p0 nhu CHOICES2 #14 - G2 khong noi,
  giu quy tac cu, bao thu.)
- G3: thit = trail da kich hoat va high >= muc nen truoc => khong DCA; thoat trail. SL van uu tien neu high >= stop cung nen (nhu v1).
- G5: grid.check_acct assert DEV/F1/F2/F3. G1: rand.episode_starts gop gio ung vien cach nhau <= 72 h (noi chuoi), dem theo thang gio bat dau.
- Phan con lai (hang so, candidates, vao lenh, equity, maxDD, metrics, select) giong v1. Khong thay doi khac.

## 2. Tinh lai doc lap (refsim2.py = refsim + G2/G3)
c1/c2/c3/c4 fold 2024 + c1 toan DEV: lenh/gio ra/ly do/DCA trung 100 % (320/81/71/99/584); PnL <= 2e-15 x notional; equity, maxDD <= 3e-15.
Luu y: tren du lieu that c2/c4 khong co ca DCA-roi-SL cung nen (moi lan cham DCA o nen SL deu bi tran 60 % chan) => nhanh G2 chi duoc kiem
bang test tong hop. Look-ahead that 12/12 van dat.

## 3. rand G1 tren c1 (W14 E0 z2.5), chi dem
617 dot that (DEV), so dot moi thang = so diem rut moi thang: 48/48 thang khop (A1 tu dem doc lap cung ra 617). 50 luot rut: so dot hieu dung
(sau khi gop trung coin <= 72 h) TB 598,8 (592-607) => thieu ~3,0 %. Muc nho, khong can xu ly (neu muon: rut lai diem trung coin trong 72 h).

## 4. Test
DEV 52/52 PASS. Ca pha A1 19/19 PASS (17 cu, cap nhat ky vong G1/G2/G3 + 2 ca moi: DCA bi tran chan roi SL; open tren muc DCA duoi stop).
Artefact: a1/{refsim2.py,cmp2.py,brk2.py,rchk.py,patch2.py}, a1/out/v2*.
