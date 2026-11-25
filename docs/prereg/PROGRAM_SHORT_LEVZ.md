# PROGRAM_SHORT_LEVZ - chuong trinh dung he SHORT "cang don bay" toi muc SAN SANG HOLDOUT 2026
Chot boi MASTER 2026-11-25 21:24 +0700. Van ban khung; moi tang co prereg rieng (khong gian tim + luat chon) commit TRUOC khi chay tang do.

## 0. Chi dao owner 2026-11-25 (nguyen van, bo dau)
"lam chuan chi. them gate them sort nhu s1 cho buy them dca them filter. dca co the ko uu tien .... lam min ra toi doan san sang holdout
2026 pass 2026 moi tinh tiep. buy cang giu cang giam thi co khi short cu keep nhung luon co sl la ok traling cung can lam ki co the la 3%
arm luon ko phai 7%"

## 1. Kien truc muc tieu (soi guong he long c3)
GATE (thi truong co cho short khong) -> POOL ung vien rong (trang thai dong long theo z-score OI + funding) -> FILTER (thanh khoan, tuoi niem
yet, muc funding ...) -> SORT (model xep hang kieu S1) -> QUOTA top-K -> vao lenh -> THOAT (LUON co SL; giu dai; trailing lam ky, arm tu 3 %)
-> DCA (cuoi cung, khong uu tien).

## 2. Cac tang (tat ca chi tren DEV: du lieu < 2026-01-01 UTC; khoi dong 2021-12)
- B0 BAN DO THO: luoi PREREG_LEVZ2 (1 296 cau hinh, simulator nen gio) - chi de biet tham so nao quan trong. Khong ket luan.
- B1 THOAT LENH: engine thoat theo NEN 1 PHUT (danh gia stop / trailing tai close 1m - dung cach bot se lam; bai hoc R-LIVE D1/D2: sim phai
  cung co che voi live). SL luon bat. Giu: 72 h / 168 h / 336 h / khong gioi han (tran 30 ngay). Trailing: arm 3 / 5 / 7 / 10 % x gap 2 / 3 / 5 %
  + tat. Truot gia stop chot truoc.
- B2 FILTER + GATE theo luat: thanh khoan, tuoi niem yet, muc f, OI notional; gate cap thi truong (do rong trang thai dong long, xu huong BTC / alt EW).
- B3 SORT kieu S1: pool rong (nguong z thap hon de co >= vai nghin ung vien), feature nhan qua, nhan = loi nhuan lenh short theo co che thoat da
  chon o B1, train walk-forward, chon top-K theo diem. Truoc khi train: do so ung vien moi nam; < 300 ung vien / nam train => KHONG lam B3.
- B4 DCA (chi khi B1-B3 da duong; khong uu tien).
- B5 DONG BANG: code + tham so + model (sha256) -> PREREG_LEVZ_HO.

## 3. Thuoc do trung thuc tren DEV
- Moi tang bao HAI so: (i) toi uu tren toan DEV (in-sample; KHONG dung lam ky vong); (ii) WFO-OOS: voi nam kiem Y in {2023, 2024, 2025}, MOI
  lua chon (tham so thoat, filter, gate, model) chi dung du lieu < Y; ghep 3 nam = uoc luong trung thuc. 2022 chi dung de train / chon.
- Doi chung: "short ngau nhien cung co che thoat / size" (>= 500 lan) cho cau hinh WFO.
- So do thu cong don: dem so cau hinh da thu moi tang; bao DSR tai luc dong bang.
- Phi 0,07 % / chieu, funding that, don bay 1x, tran phoi nhiem 60 %, DD tinh theo equity MTM xau nhat trong nen.

## 4. Tieu chi "SAN SANG HOLDOUT" (chot ngay bay gio; khong noi sau khi thay so)
Tren WFO-OOS 2023-2025 cua he da dong bang: (R1) loi nhuan rong > 0 o >= 2/3 nam VA tong 3 nam > 0; (R2) Calmar tong >= 1,0 va maxDD <= 25 %;
(R3) >= 150 lenh OOS; (R4) thang doi chung ngau nhien: p <= 0,05; (R5) cao nguyen: >= 60 % cau hinh lan can (doi 1 tham so 1 nac) cung duong
tren WFO-OOS; (R6) bo 5 % lenh tot nhat van > 0; (R7) lenh te nhat <= 1,5 x muc SL (co che SL thuc su chan duoc duoi).
Dat het => MASTER de nghi owner dung HO 2026 (01-09/2026, MOT lan, he dong bang, nen 1m co high / low tu Kaggle vz-kline1m-2026; tieu chi
pass HO chot trong PREREG_LEVZ_HO truoc khi mo du lieu). Khong dat => bao owner so thuc + khuyen nghi dung; owner quyet.

## 5. Luat dung som
Sau B1 + B2: neu WFO-OOS <= 0 hoac thua doi chung ngau nhien => MASTER bao owner va khuyen nghi dung truoc khi lam B3 (ML tren tin hieu goc
bang 0 chi khop nhieu). Owner quyet di tiep hay khong.

## 6. Ngoai pham vi cho toi khi HO dat
Phan bo von, ghep voi he long, engine SELL trong jar, live.

## 7. Ky luat
Moi tang: prereg -> DEV (agent) -> A1 audit code (agent khac) -> RUN -> A1 audit ket qua -> MASTER tu kiem >= 3 so -> bao owner. Khong doc 2026.
Khong gui owner so chua audit. Python offline tren Oracle, viec nang qua flock oracle_heavy.lock.
