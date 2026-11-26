# A1_G3_RESULT - audit KET QUA G3 (du lieu that <= 2019-12-31), 2026-11-27
## KET LUAN: XAC NHAN "KHONG DAT" (dung). Nhung p ngau nhien 0,004 / 0,002 / 0,014 KHONG phai bang chung tin hieu (doi chung C21 thien lech).
sha: code 5/5 khop ban audit vong 2; eval_g3.md b901ccee...c98ad, eval_g3.json c487af54...b8de98 khop.
## 1. Tinh lai doc lap (z, ngay vao, tranche, so sach cua A1; KHONG goi simulate/evaluate cua DEV)
Ca 12 cau hinh: TRAIN Sharpe/ann, WFO Sharpe/ann/maxDD/so lenh, x2 khop report den 4 chu so. Trich cau hinh chon:
| nhom | chieu (TRAIN W52H4 H_TD mean ngay) | chon | WFO Sharpe | ann | maxDD | lenh | x2 ann | D8 W52H4 WFO mean |
| LevFunds | H_ND (-2,29e-5) | W156_H4 | -0,3789 | -0,0061 | 0,0781 | 441 | -0,0084 | -2,06e-5 (F) |
| AssetMgr | H_TD (+2,87e-5) | W52_H4 | -0,2706 | -0,0053 | 0,0708 | 743 | -0,0092 | -2,10e-5 (F) |
| NonComm  | H_ND (-1,95e-5) | W52_H4 | -0,2348 | -0,0070 | 0,1580 | 1269 | -0,0104 | -2,79e-5 (F) |
| gop 2013-19 | | | -0,6038 | -0,0058 | 0,0480 | 1788 | | |
Luat: CHIEU = dau trung binh TRAIN cua W52/H4 H_TD; CAU HINH bao cao (D1..) = Sharpe TRAIN cao nhat trong 4 theo chieu da chon - dung prereg muc 4.
LevFunds chon W156_H4 vi TRAIN Sharpe 0,2986 cao nhat; D8 van do W52/H4 - dung prereg. D9 dat ca 3. Chu y: chieu TRAIN dua tren trung binh ~2e-5/ngay (~0,5 %/nam) = gan nhu hoa.
## 2. Vi sao Sharpe am ma p nho
p tinh dung chieu ((1 + #ngau nhien >= that)/(N+1)); A1 tai lap: p 0,007 / 0,007 / 0,914 (150 luot), gop 0,013. Nhung doi chung C21 THIEN LECH:
luot ngau nhien (H_ND) co ann -1,48 % / -1,05 % vs that -0,70 % / -0,61 %, vol thap hon (0,019 vs 0,030). Nguyen nhan: (a) giu ti le dau CUA CA NAM roi rai
len tuan bat ky => dat vi the H_ND (nguoc dau co) ca TRUOC khi cuc tri xuat hien, ma vi the dau co di theo gia => lo nguoc xu huong co he thong;
(b) tin hieu rai rac => vol thap => cung chi phi thi Sharpe am hon. Doi chung dich vong K4 (giu cum + trinh tu): p = 0,758 / 0,557 / 0,607, gop 0,764 (DEV);
A1 tai lap 0,735 / 0,556 / 0,576, gop 0,728. => D2 "True" la ao; khong anh huong ket luan vi D1, D4, D6, D7, D8 deu F.
## 3. J6 thang 2008-10, NonComm W52 (chon H_ND, H4)
EUR z: 09-02 -2,11; 09-09 -1,80; 09-16 -2,15; 09-23 -1,65 (lenh -1 -> H_ND = LONG EUR, w=+0,0357); 09-30..10-28 |z|<1,5 => khong lenh moi.
GBP z: -1,81; -1,65; -1,93; -1,89 tuong tu (long GBP). 4 phan moi dong tien mo 09-09..09-30, dong 10-07..10-28.
PnL thang 10 (ty le von): EUR -0,8527 %, GBP -0,7257 %: vong lap tay tung phan = so sach A1 = sim DEV (lech 0). Hop ly (USD tang manh 10/2008).
## 4. Hop le
Max ngay px / COT = 2019-12-31, lai suat 2019-12-01; khong co ngay > 2019-12-31. Phan WFO vao 2006-01-03..2019-12-31; TRAIN/WFO tach theo ngay vao + ep dong.
## 5. Mo ta cho MASTER (NGOAI tieu chi, [mo ta])
- Gop truoc phi (gia + swap, WFO): LevFunds W156H4 -0,37 %/nam (Sharpe -0,23); AssetMgr W52H4 -0,13 % (-0,07); NonComm W52H4 -0,37 % (-0,12).
  => tin hieu ~0 den hoi am, khong chi am vi phi. Phi + bien ~0,3-0,4 %/nam la phan lon cua muc lo rong.
- Dao chieu tren WFO (KHONG de xuat): cau hinh chon -> LevFunds +0,14 %/nam (Sh 0,09), AssetMgr -0,26 % (-0,13), NonComm +0,03 % (0,01). 12 cau hinh
  dao chieu: 5 duong, 7 am, |Sharpe| <= 0,36 => dau KHONG on dinh, khong co tin hieu theo chieu nao.
- Muc phoi nhiem rat nho (w = 1/(N*H), chi tuan cuc tri) => ann_ret tinh theo von ~0,5 %/nam; Sharpe la thuoc do dung.
## 6. Duoc / khong duoc noi voi owner
DUOC: "G3 KHONG DAT tren WFO (2006/2013-2019): ca 3 nhom va gop Sharpe sau phi am (-0,23 den -0,60), 0/12 cau hinh WFO duong, chieu chon tren TRAIN
khong giu dau; A1 tinh lai doc lap khop." "Truoc phi tin hieu ~0." HOLDOUT chua mo, khong nen mo (khong dat).
KHONG DUOC: noi "co y nghia thong ke" / dan p 0,004 / 0,002 / 0,014 (doi chung thien lech; p dich vong 0,56-0,76); noi "dao chieu thi co loi" (lua chon
sau khi xem ket qua, dau khong on dinh); dan so TRAIN khong kem [in-sample].
## Chua kiem
Lich cong bo ngoai exceptions; tinh dai dien cua lai suat OECD cho swap.
