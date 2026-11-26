# PREREG_LEVZ_T2 - DOI DIEM VAO LENH cho he SHORT LEVZ (limit o nhip hoi, cho pha day, cho OI bat dau giam) tren pool goc D0
Chot boi MASTER 2026-11-27 01:30, truoc khi viet code / chay. Khung: PROGRAM_SHORT_LEVZ.md. Ke thua B1 (54f40792 + ADD1 3226e940) va T1
(186f2a5a + ADD1 45f45a5b).

## 0. Boi canh
- Owner 2026-11-27 (nguyen van, bo dau): "he thong dang ranh ko ko chay tiep phai cho toi 9h50 la sao. chay sim duoc short chua".
- Da do, da audit: B1 thoat lenh (WFO top-20 2024 -23,0 %, 2025 +6,1 %), B2 gate, B3 sort bang model (khong dat), T1 ky thuat lenh (khong ho
  nao dat; PART va STATE lam 2024 ~ hoa nhung phu thuoc vai lenh), S2 tin hieu rolling / cat ngang (khong dat). Pool tot nhat van la D0.
- Su that da biet tu giai phau B1: squeeze den CHAM (SL sau trung vi ~23 h); vao ngay (E0) chiu tron nhip tang truoc khi xa.
  => gia thuyet T2: tri hoan / dieu kien hoa diem vao giam duoc lo SL ma khong mat nhip xa.
- Tien nghiem cua MASTER: THAP-TRUNG BINH. E1 (cho z_r <= -2 trong 1 h) da that bai o B0 / B1. Tin hieu goc yeu.

## 1. Du lieu, pool, danh muc
- CHI du lieu < 2026-01-01 UTC. Thu muc moi ~/claude_master/w3/levz_t2/{code,work,out}; khong sua cac thu muc levz_* khac.
- Tin hieu goc: ung vien cand_b1.npz W7_E0, z_min in {2,5 ; 3,0 ; 3,5} (gio tin hieu k, cooldown 72 h nhu B1). K in {3, 5, 10}.
  Danh muc = port.py cua B1 khong sua (1x, phoi nhiem 60 %, phi 0,07 % / chieu, funding that, danh gia close 1 phut, truot SL 0,3 %).
- Gia tham chieu p0 = close 1 phut tai luc tin hieu (dung gia vao cua E0).

## 2. Cac kieu vao (cua so cho W = 48 h ke tu tin hieu; khong khop trong cua so => BO ung vien; chi dung thong tin da co tai phut xet)
- E0   (doi chieu): vao ngay nhu B1.
- EL_b (limit o nhip hoi): dat lenh ban limit tai p0 x (1 + b), b in {1 %, 2 %, 3 %}; khop khi close 1 phut >= muc, gia khop = dung muc;
  phi 0,07 %.
- EB   (cho pha day): L = close gio THAP NHAT cua 24 gio truoc tin hieu; vao tai close GIO dau tien < L (lenh thi truong, truot 0,1 %).
- EO_x (cho OI bat dau giam): tai moi moc gio sau tin hieu, OI doc theo quy uoc tre cua B0 (ban ghi <= moc gio - 10 phut); vao tai close
  gio dau tien ma OI <= (1 - x) x max OI ke tu tin hieu, x in {3 %, 5 %} (lenh thi truong, truot 0,1 %).
=> 6 kieu vao moi + E0. Sau khi vao: thoi gian giu / SL / trailing / funding tinh tu PHUT VAO THAT.
- Cooldown 72 h va viec chiem cho (slot) tinh tu phut vao that; ung vien dang cho khop KHONG chiem cho.

## 3. Thoat lenh
195 bo thoat cua B1 + 8 bo PART + 8 bo STATE cua T1 (dinh nghia va engine T1 khong sua; STATE xet trang thai tu gio vao that) = 211 bo.
Luoi: 7 kieu vao x 3 z x 3 K x 211 = 13 293 cau hinh. Khong gate.

## 4. Thuoc do
Voi tung kieu vao: (i) ti le ung vien duoc khop theo nam; do tre trung vi; (ii) ti le cau hinh co lai + trung vi F1 / F2 / F3 / DEV;
(iii) WFO (select_b1.rule khong sua, hang xom theo ho thoat nhu T1): top-1 va trung vi top-20 nam 2024, 2025, so voi trung vi ca kieu vao;
(iv) PLACEBO THOI DIEM (doi chung chinh, giu cau truc): voi tung kieu vao, moi ung vien DUOC KHOP duoc thay bang vao lenh tai mot phut
ngau nhien deu trong cua so 48 h cua chinh no (lenh thi truong, truot 0,1 %), cung so lenh, cung luoi; 100 luot; thong ke = tong trung vi
top-20 WFO 2024 + 2025; p = (1 + so luot >= that) / 101. Them placebo "cung do tre": vao dung sau do tre cua mot ung vien duoc khop khac
(hoan vi do tre trong cung nam) - mo ta. (v) do tap trung: bo 5 % lenh loi nhat cua top-1 WFO; lenh te nhat; so lenh / nam.

## 5. Tieu chi (chot truoc) cho TUNG kieu vao moi
U-a WFO trung vi top-20 > 0 o CA 2024 va 2025.
U-b ti le cau hinh co lai >= 50 % o ca F1, F2, F3.
U-c placebo thoi diem: p <= 0,05.
U-d cau hinh trung vi co >= 100 lenh trong 2024 + 2025.
U-e top-1 WFO tung nam: bo 5 % lenh loi nhat van > 0.
U-f hon E0 (cung quy trinh T2) ve trung vi top-20 WFO o CA hai nam.
- Du U-a..U-f => "KIEU VAO DAT": dua vao B5 (dong bang). Dat U-a + U-c + U-f => "CO CAI THIEN, CHUA DU". Con lai => "KHONG HON E0".
- Khong kieu nao dat => bao owner so thuc; owner quyet. Khong them kieu vao / doi tham so sau khi thay so.

## 6. Ky luat
prereg -> DEV (agent Opus) -> A1 audit code (agent khac) -> RUN (grid tren Oracle; placebo tren Kaggle qua ~/claude_master/w3/levz_kg neu
nang) -> A1 audit ket qua -> bao owner. Test bat buoc: E0 qua duong T2 tai lap grid_b1 / grid_t1 tuyet doi; ban tham chieu vong for cho
EL / EB / EO (>= 500 ung vien moi kieu); NHAN QUA: quyet dinh vao tai phut m chi dung gia <= m va OI theo quy uoc tre; doi du lieu sau phut
vao khong doi phut vao; placebo dung cung so lenh; du lieu gia co hieu ung cay san => DAT, thuan nhieu => KHONG. Python dung logging.
Khong doc 2026.
