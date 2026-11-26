# PREREG_LEVZ_T1 - cac KY THUAT quan ly lenh cho he SHORT LEVZ (bracket SL/TP theo ti le, stop theo bien dong, chot tung phan, thoat theo
# trang thai, phong ho beta) - chay SONG SONG voi B3
Chot boi MASTER 2026-11-26, truoc khi viet code / chay. Khung: PROGRAM_SHORT_LEVZ.md. Ke thua engine + danh muc + luoi cua B1 (54f40792 +
ADD1 3226e940) va gate cua B2 (da636b28 + ADD1 d1241f48).

## 0. Chi dao owner 2026-11-26 (nguyen van, bo dau)
"ngoai ra nghien cuu sau them xem short co ki thuat gi apply vao tiep. dong thoi 1 huong song song khac la nghien cuu kieu ko phai long only
ma kieu vao co SL/TP theo ti le ay nho ap dung cac filter short cach nay chac ko dca nhung nghien cuu xem co p/a giai phap nao nhe. con cho
them 1 huong nua la xem ngoai sl/tp con phuong an retail trade nao khac nua ko nhe"
Cach hieu cua MASTER (gia dinh, da bao owner): (1) ra soat ky thuat cho lenh short; (2) kieu giao dich "vao lenh co SL va TP theo ti le
R = TP / SL", khong DCA, ap gate / filter cua he short; lam ben SHORT truoc (ha tang san), ben LONG (tin hieu crash-buy) la buoc sau rieng;
(3) cac cach quan ly lenh pho bien khac ngoai SL / TP.

## 1. Danh muc ky thuat da ra soat va quyet dinh (ghi truoc khi co so)
DUA VAO T1 (co ly do co che gan voi diem yeu da do o B1 / B2):
- BRK  bracket SL / TP theo ti le R (yeu cau owner). B1 chua tung co TP.
- VOL  SL / TP tinh theo bien dong cua chinh coin (moi coin bien dong khac nhau; SL % co dinh qua chat voi coin bien dong lon).
- PART chot mot nua tai 1R roi doi stop ve hoa von (giam phu thuoc vao vai lenh thang lon - diem yeu cua trailing o B1).
- STATE thoat khi trang thai "dong long" KET THUC (z_oi hoac z_f ha, funding ve binh thuong) - thoat theo ly do vao lenh thay vi theo gia.
- HEDGE phong ho beta: moi vi the short alt kem long BTC (hoac BTC + ETH) - nham dung nguyen nhan lo 2024 (alt rally ca thi truong).
KHONG dua vao T1 (ghi ly do; co the mo tang sau, phai prereg rieng):
- DCA / nhoi lenh nguoc xu huong va luoi (grid, martingale): voi short, lo khong chan tren; PROGRAM de B4.
- Nhoi theo chieu thang (pyramiding): can engine vi the nhieu leg; de B4.
- Vao lenh bang limit o nhip hoi (sell the rip), xac nhan pha day 24 h, xac nhan OI bat dau giam: la thay doi DIEM VAO, khong phai quan ly
  lenh; de tang T2 neu T1 / B3 co ket qua.
- Du lieu thanh ly / so lenh (order book): khong co trong kho; khong lam.
- Thu funding (carry) lam nguon loi nhuan chinh: he khac han; ngoai pham vi.

## 2. Du lieu, pool, danh muc
- CHI du lieu < 2026-01-01 UTC. Thu muc moi ~/claude_master/w3/levz_t1/{code,work,out}; khong sua levz2 / levz_b1 / levz_b2 / levz_b3.
- Ung vien: cand_b1.npz, W = 7, E0, z_min in {2,5 ; 3,0 ; 3,5}. K in {3, 5, 10}. Danh muc = port.py cua B1 (1x, tong phoi nhiem 60 %, moi
  coin 1 vi the, xep theo s). Phi 0,07 % / chieu, funding that, danh gia tai close 1 phut, truot gia SL 0,3 % nhu B1.
- TP: lenh limit dat san. Khop khi close 1 phut <= muc TP; gia khop = DUNG muc TP (khong truot), phi 0,07 %. (Bo sot cac lan chi rau nen cham
  muc - bao thu.)
- Gate: moi ho chay 2 che do: KHONG gate va G_EW14 (dinh nghia va mat na cua B2, khong sua). G_EW14 la gia thuyet hinh thanh sau khi thay
  2024 => moi so duoi G_EW14 phai mang nhan "gate hau kiem".

## 3. Cac ho (luoi co dinh)
- BRK: SL s in {3, 5, 8, 12, 15, 20 %}; TP = R x s, R in {0,5 ; 1 ; 1,5 ; 2 ; 3}; H in {24, 72, 168} h (het H thi dong tai close). 90 bo.
- VOL: don vi u = sd loi suat log theo gio cua 168 h truoc gio vao x can(24) (chi du lieu truoc gio vao); SL = a x u, a in {1 ; 1,5 ; 2 ; 3},
  san 2 %, tran 50 %; TP = R x SL, R in {1, 2, 3, khong TP}; H in {24, 72, 168}. 48 bo.
- PART: SL s in {5, 8, 12, 15 %}; tai loi +s dong 50 % vi the (limit, khop nhu TP) va doi stop phan con lai ve gia vao; phan con lai TP tai
  3 x s hoac het H in {72, 168}. 8 bo.
- STATE: thoat tai close gio dau tien ma (z_oi < z_out HOAC z_f < z_out HOAC f <= 0,01 % / 8h), z_out in {0, 1} (bang tin hieu W7, chi dung
  gia tri da chot cua gio do); SL in {15, 30 %} luon bat; tran H in {168, 720}. 8 bo.
- HEDGE (lop phu tren danh muc): voi moi bo thoat cua BRK va 3 bo tham chieu B1 (xi cua cfg 4107; exit_2024 = xi 170; exit_2025 = xi 72 cua
  B3), them vi the LONG bang h x tong notional short dang mo, can lai moi gio; cong cu in {BTC ; 50 % BTC + 50 % ETH}; h in {0,5 ; 1,0}.
  De tong phoi nhiem (short + long) van <= 60 % equity: co lenh short = equity x 0,60 / ((1 + h) x K). Phi 0,07 % tren luong can lai,
  funding that cua chan long.
Moi ho x 3 z x 3 K x 2 che do gate. Tong so cau hinh phai duoc dem va ghi trong bao cao (so do thu).

## 4. Thuoc do (giong B1 / B2 de so duoc)
Voi tung ho va tung che do gate: (i) ti le cau hinh co lai va trung vi loi nhuan o F1 (2022-23), F2 (2024), F3 (2025), DEV; trung vi maxDD;
(ii) WFO: chon theo cac fold < Y bang luat chon cua B1 (select_b1, khong sua) -> ket qua nam Y cho top-1 va trung vi top-20, so voi trung vi
ca ho, Y in {2024, 2025}; duoi G_EW14 neu khong du cau hinh hop le de chon cho 2024 thi ghi "khong cham duoc 2024"; (iii) doi chung ngau nhien
dung nghia nhu B1 (max qua luoi cua ho, 100 luot, lop W7 E0 z 3,0); (iv) do tap trung: bo 5 % lenh loi nhat; lenh te nhat; so lenh / nam;
(v) dong moc B1 (da audit): WFO 2024 top-20 trung vi -23,0 %, 2025 +6,1 %; ti le co lai 64 % / 20 % / 84 %.

## 5. Tieu chi (chot truoc) cho TUNG ho, che do KHONG gate
T-a WFO 2024 trung vi top-20 > 0 VA WFO 2025 trung vi top-20 > 0.
T-b ti le cau hinh co lai >= 50 % o CA F1, F2, F3.
T-c doi chung ngau nhien: p <= 0,05.
T-d cau hinh trung vi cua ho co >= 100 lenh trong 2024 + 2025.
T-e voi top-1 WFO cua tung nam: bo 5 % lenh loi nhat van > 0.
- Du T-a..T-e => "HO DAT": dua vao B5 (toi uu gop). Dat T-a nhung thieu muc khac => "CO CAI THIEN, CHUA DU". Con lai => "KHONG HON B1".
- Ket qua duoi G_EW14 chi mo ta (gate hau kiem, it lenh), khong dung de ket luan "DAT".
- Khong ho nao dat => bao owner so thuc; owner quyet. Khong them ho / doi luoi sau khi thay so (muon them => prereg T2).

## 6. Ky luat
prereg -> DEV (agent Opus) -> A1 audit code (agent khac) -> RUN -> A1 audit ket qua -> MASTER tu kiem >= 3 so -> bao owner. Test bat buoc:
voi tham so trung nhau, engine T1 phai tai lap bang thoat B1 (vi du BRK khong TP = B1 khong trailing cung SL / H); TP / PART / STATE / VOL co
ban tham chieu doc lap viet cham de doi chieu >= 500 lenh; HEDGE voi h = 0 phai trung danh muc B1 tung so; khong nhin truoc (u cua VOL,
STATE chi dung gio da chot). Viec nang qua flock oracle_heavy.lock. Python dung logging. Khong doc 2026.
