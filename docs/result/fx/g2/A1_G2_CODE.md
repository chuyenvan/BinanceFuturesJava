# A1_G2_CODE - audit doc lap code FX G2 (TSMOM + loc REER) - 2026-11-27
Khong tinh loi suat / Sharpe that; khong doc >= 2020; khong sua code.

## KET LUAN: PASS-WITH-MINOR (khong co loi CHAN)
sha256 khop: load_g2 3dbf69fa...f346c, sim_g2 04ed2970...3f1, eval_g2 5841a9cc...8285, test_g2 498f2928...c46c;
g1 import: load_g1 f466ace5...fe99c, sim_g1 a99ff7aa...4e7, eval_g1 61efccfa...ded (= ban audit vong 2 G1).

## 1. Doi chieu prereg + CHOT MASTER (doc code)
12 cau hinh (sim_g2.py:18-30); tin hieu tai T = dong cuoi thang, khop T+1 (86, 156); s(L) = dau log(Pf[T]/Pf[T(m-L)]), C = dau trung binh (92-100);
nghich dao vol 63 ngay, gross 1 (34-40, 54-65, 152); loc doi xung REER(m-1) vs TB m-60..m-1 (43-51, 103-107); universe = G1 (lai suat m-1 dong
tien + USD) + gia hop le tai T (load_g2.py:67-80); carry lai suat m-1, chi phi MAX(3 pip,3 bp)/EURUSD 0,8 pip, margin 1 %, x2 qua engine G1 da audit;
TRAIN 1975-2005 / WFO 2006-2019 (eval_g2.py:19-25); chon bang Sharpe TRAIN, hoa F0<V10<V20, L12<L3<L1<C (43-47); dich vong tung dong tien
k in [12, n-12], N 1000, p = (1+n_ge)/(N+1) (63-73, 101-112); D1-D6 (50-60); [in-sample] trong report. Cutoff o FRED, OECD, REER (load_g2.py:38-41),
khoa token trong ham (check_real) + CLI. Test goc tren ban copy: a-h PASS, fails=0.

## 2. Tu kiem doc lap tren du lieu that <= 2019 (code rieng, csv tu parse; chi vi the)
142 thang (moi thang 2/6/10 tu 1975 + 1974-12, 1985-09, 1992-08/09, 2008-09, 2015-01, 2019-11) x 4 cau hinh (L1-F0, L12-F0, C-V10, L3-V20)
= 568 thang-cau hinh: trong so lech 0 (|lech| <= 1e-9); T, dong khop (T+1) va universe khop ca 142 thang. Loc thuc su hoat dong: C-V10 155 chan bi
loc, L3-V20 9 chan. Vi du 2008-10 L12-F0: long JPY, short 8 dong con lai (nghich dao vol).

## 3. So sach tinh tay (tong hop: GBP, AUD, CAD; L1-V20; REER GBP 125 tu 2000-01)
3 thang cuoi: AUD -0,378 -> +0,381 -> -0,569 -> +0,555 (dao chieu), CAD dao chieu, GBP bi loc tu tin hieu 2000-02 (REER m-1 = 125 > 1,2 x TB).
Trong so + ngay khop (T+1) cua ban tay = sim; equity cuoi tay 0,990445882505 = sim (lech 1e-15). sum|w| = 1 moi lan; gross toi da 1,018 (troi giu so don vi).

## 4. Mutant (16, tren ban copy)
BAT 12: N01 REER thang m; N02 vol dung T+1; N03 khop cung ngay T; N04 loc mot phia; N05 trong so deu; N06 chon bang WFO; N07 dich vong -> iid;
N09 x2 khong nhan; N11 bo cutoff REER; N12 cua so REER m-61..m-2; N13 D5 luon dung; N15 kmin 0.
LOT 4: N08 p khong +1 (goi trong evaluate, eval_g2.py:112 - test e chi kiem ham p_value); N10 L12 dung 11 thang; N14 lookback dung gia T+1
(NHIN TRUOC); N16 universe bo dieu kien gia tai T. Code hien tai DUNG ca 4 diem (doi chieu muc 2 se bat N10/N14/N16), nhung test khong bao ve.

## 5. Loi NHO
NHO-1 test gap (test_g2.py:114-148, 234-272): them (a) test tay tin hieu tren gia tong hop co buoc nhay dung ngay T+1 (bat N14) va L12 phan biet 11/12
thang (N10); (b) probe test b dat DUNG ngay T; (c) universe thieu gia tai T (N16); (d) evaluate voi Sharpe gia de assert p = (1+n_ge)/(N+1).
NHO-2 R4 ghi "khong co gia tai T(m-L) => khong vi the" nhung code dung Pf ffill (sim_g2.py:94) - sua tai lieu (anh huong khong dang ke; gap <= 3 ngay).
NHO-3 carry lai suat m-1 co dinh thang giu (ke thua G1 C4) - nhu G1 K5, co the bao kem mo ta.

## 6. REER m-1
DATA_REPORT_2: gia tri 2026-10 da co trong file ngay 2026-11-25 => do tre cong bo < 1 thang, REER(m-1) co truoc cuoi thang m: KHONG nhin truoc
theo lich cong bo hien tai. Rui ro con lai (thap-trung binh, chi anh huong loc): (i) khong co vintage - lich su da sua (trong so, nam goc);
(ii) AU, NZ co CPI theo quy => REER thang gan nhat dung CPI noi suy / uoc, sau duoc sua; (iii) REER narrow truoc 1990s la chuoi BIS dung lai
ve sau. Nguong 10-20 % so voi TB 60 thang it nhay voi sua nho. De nghi: bao kem MO TA ban REER m-2 (ngoai tieu chi).

## 7. CHOICES R1-R12
R1 import G1 da audit: OK. R2/R3 khop prereg. R5 vol gom T: khong nhin truoc vi khop T+1. R6 TB gom m-1: dung prereg. R7 thu tu hoa: hop ly.
R8 p so voi ban chay rieng WFO (cung diem xuat phat voi luot dich vong) - DUNG cach so sanh; D1 dung lat WFO cua lan chay day du; hai so khac
nhau do vi the dau ky - bao ca hai (da co). Dich vong o thang ngoai universe: bo vi the (WFO ca 9 dong tien deu trong universe nen khong anh huong).
N 1000 = prereg. R9-R11 mo ta. R12: PnL that 2008-10 de A1-results.

## CHUA kiem
metrics (ke thua G1 da kiem), doi chung iid / mua-giu, report_md.
