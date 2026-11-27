# PREREG_X3_1127 - ba huong dao tiep chay song song (B4 DCA cho short; CMB2 ghep long + short khong nhin truoc; LLV loc lenh LONG theo trang
# thai don bay). Chot boi MASTER 2026-11-27 11:30, truoc khi viet code / tinh so. CHI du lieu < 2026-01-01 UTC.
Owner 2026-11-27 (nguyen van, bo dau): "1h30p nua reset quota => con huong nao dao duoc dao tiep di nhe. nho la master define ro ra cho agent
chay song song nha". Boi canh: short LEVZ da qua B1, B2, B3, T1, S2 (khong dat), T2 dang chay; forex 4 nghien cuu khong dat.

## PHAN A - B4: DCA cho lenh SHORT (tang cuoi cua PROGRAM_SHORT_LEVZ; tien nghiem THAP: nhoi lenh nguoc xu huong voi short)
A1. Pool: cand_b1.npz W7_E0, z_min {2,5 ; 3,0 ; 3,5}; K {3, 5, 10}; danh muc port.py B1 (1x, phoi nhiem 60 %, phi 0,07 % / chieu, funding
    that, danh gia close 1 phut, truot SL 0,3 %). Thu muc ~/claude_master/w3/levz_b4/{code,work,out}.
A2. DCA: ngan sach mot cho (slot) = equity x 0,60 / K duoc GIU TRON tu luc vao (leg chua khop de von nhan roi - khong tang don bay).
    n_add in {1, 2} leg them; moi leg = ngan sach / (1 + n_add); leg them thu j khop (limit, dung muc, phi 0,07 %) khi close 1 phut >=
    gia vao dau x (1 + a x j), a in {5 %, 10 %}. Gia von = trung binh theo khoi luong cac leg da khop.
A3. SL (luon bat) tinh tu GIA VON: s in {15 %, 30 %}; dong toan bo. Thoat: {trailing arm 5 % / gap 3 %; trailing arm 10 % / gap 5 %} tinh
    tu gia von, hoac STATE (z_out = 0, dinh nghia T1); giu toi da H in {72, 168} h ke tu leg dau.
A4. Luoi: 4 kieu DCA + 1 KHONG DCA (doi chieu, cung thoat) = 5 x SL 2 x thoat 3 x H 2 = 60 bo x 3 z x 3 K = 540 cau hinh. Khong gate.
A5. Thuoc do nhu T1 (ti le co lai F1 / F2 / F3; WFO select_b1.rule top-1 + trung vi top-20 nam 2024, 2025 theo TUNG kieu DCA; bo 5 % lenh
    loi nhat; lenh te nhat / muc lo toi da mot cho). Doi chung CHINH = ban KHONG DCA cung thoat.
A6. Tieu chi cho tung kieu DCA: V-a WFO trung vi top-20 > 0 ca 2024 va 2025; V-b hon ban KHONG DCA (cung quy trinh) o ca hai nam;
    V-c >= 50 % cau hinh co lai o F1, F2, F3; V-d top-1 WFO tung nam: bo 5 % lenh loi nhat van > 0; V-e lo te nhat cua mot cho <= 1,5 x s
    x ngan sach cho. Du het => "DCA DAT"; V-a + V-b => "CO CAI THIEN"; con lai => "KHONG HON KHONG-DCA".
A7. Test bat buoc: n_add = 0 tai lap bang thoat T1 / B1 tuong ung tuyet doi; tham chieu vong for cho DCA (>= 500 lenh); nhan qua; so sach
    (tong PnL = thay doi equity; von giu tron). Khoa --real I_HAVE_A1_PASS. DEV -> A1 -> RUN -> A1 ket qua.

## PHAN B - CMB2: ghep he LONG (DEV) voi short chon KHONG nhin truoc tu T1 (MO TA - khong phai tieu chi trien khai)
B1. Long: 4 ledger DEV ~/claude_master/w3/p15_stab/s2/k/{c0s42,c0s7,c0s123,c0s13}/storage/printDone.csv (gio sim = UTC+7), equity MTM theo
    GIO nhu phan tich levz_an (tai dung code ~/claude_master/w3/levz_an/, da qua A1_AN).
B2. Short: voi nam Y in {2024, 2025}: cau hinh top-1 WFO (chon tren fold < Y bang select_b1.rule, lay tu ket qua T1 da audit) cua ho STATE
    va cua ho PART (khong gate) - hai bien the CMB-STATE, CMB-PART; nam 2022-2023: KHONG co short (khong co fold de chon). Them doi chieu
    in-sample (dan nhan): cau hinh DEV tot nhat cua tung ho.
B3. Ghep m = 1 tren cung equity (short dung tran phoi nhiem 60 % rieng nhu levz_an; bao gross dinh). Bao cho tung seed: CAGR, maxDD MTM
    theo gio, Calmar, loi suat tung nam 2022..2025 cua: long rieng; long + CMB-STATE; long + CMB-PART; so gio hai he cung co vi the; so
    lenh short trung coin dang long.
B4. Duoc ket luan: "ghep khong-nhin-truoc lam Calmar tang / giam bao nhieu o tung seed". KHONG duoc: goi do la ky vong; de nghi trien khai.

## PHAN C - LLV: lenh LONG cua he hien tai co kem di khi coin dang "dong long" khong? (MO TA co kiem dinh chot truoc)
C1. Du lieu: 4 ledger long DEV tren (moi dong = mot leg; gop thanh CUM = cung coin, cac leg noi tiep / chong thoi gian cho toi khi dong
    het); loi suat cum = tong PnL / tong von da vao; gio vao leg dau doi sang UTC. Dac trung TAI GIO VAO (nhan qua, tu levz2/work/
    sig_W7.parquet + inputs.npz, quy uoc tre OI nhu levz): z_oi, z_f, f, doi24 (thay doi ln OI 24 h), LEV24 = coin o trang thai D0
    (z_oi >= 2,5, z_f >= 2,5, f > 0,01 %) tai bat ky gio nao trong 24 h truoc khi vao.
C2. Bon gia thuyet chot truoc (mot phia): H1 cum co LEV24 = 1 co loi suat THAP hon cum con lai; H2 cum co z_oi <= -1 (OI da xa) CAO hon;
    H3 cum co f < 0 CAO hon; H4 cum co doi24 thuoc ngu phan vi thap nhat (tinh trong cung nam, cung seed) CAO hon.
C3. Kiem dinh: chenh lech trung binh loi suat cum (nhom - phan con lai) theo nam 2022..2025 x seed; "NHAT QUAN" = dung dau o >= 3 / 4 nam
    trong >= 3 / 4 seed; p hoan vi theo KHOI THANG (>= 2 000 luot, gop 4 seed bang trung binh) <= 0,0125 (Bonferroni 4 gia thuyet).
    Bao: so cum moi nhom / nam, % cum bi anh huong, PnL thay doi neu BO cac cum nhom xau (uoc tho, bo qua phan hoi slot - ghi ro).
C4. Ket luan: gia thuyet nao NHAT QUAN + p dat => "CO MANH MOI" => buoc ke (ngoai pham vi file nay): prereg mot gate + sim Java tren
    Kaggle. Khong thi "KHONG CO MANH MOI". Khong them gia thuyet / nguong sau khi thay so.
