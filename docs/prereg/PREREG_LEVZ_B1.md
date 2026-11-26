# PREREG_LEVZ_B1 - tang B1 cua PROGRAM_SHORT_LEVZ: THOAT LENH lam ky tren NEN 1 PHUT (SL luon bat, giu dai, trailing arm tu 3 %)
Chot boi MASTER 2026-11-26 11:15 +0700, TRUOC khi viet engine va truoc khi chay bat ky cau hinh B1 nao.
Da biet (B0, nen gio, in-sample - docs/result/levz2/MASTER_NOTE_B0_1125.md): lai cua cau hinh tot nhat nam o nhanh trailing 10 % / 5 %; thu hang
cau hinh dao giua 2024 va 2025; WFO top-20 am. B1 la phep kiem QUYET DINH cua chuong trinh (PROGRAM muc 5).
Chi dao owner: "short cu keep nhung luon co sl ... trailing cung can lam ki co the la 3% arm luon ko phai 7%"; DCA khong uu tien => B1 TAT DCA.

## 1. Du lieu (chi < 2026-01-01 UTC; reader assert)
- Tin hieu: bang gio cua B0 (w3/levz2/work/sig_W14.parquet, sig_W7.parquet - sinh tu code tang 1 dong bang, da audit).
- Gia 1 phut: ~/claude_master/res1109/r1_s1/kl/kline1m-YYYY-MM.parquet (chi ts, sym, close; phu ~100 % universe). Phut thieu => giu gia cuoi;
  thieu lien tuc > 24 h => dong tai close cuoi cung, gan co.
- Funding: funding lake nhu B0.

## 2. Engine thoat (danh gia tai CLOSE moi nen 1 phut - dung cach bot tu danh gia gia; khong dung lenh stop nam tren san)
- Vao: tin hieu tai gio t => vao tai close cua nen 1m co open_time = t (tre 1 phut, nhu tang 1). p0 = gia vao.
- Moi phut sau phut vao, theo thu tu: (a) SL: close >= p0 x (1 + SL) => thoat tai close x (1 + 0,003) (lenh thi truong luc bi squeeze);
  (b) trailing (neu bat): kich hoat khi close <= p0 x (1 - arm); day = min close ke tu luc kich hoat; close >= day x (1 + gap) => thoat tai
  close x (1 + 0,001); kich hoat va thoat khong xay ra trong cung mot phut; (c) time-stop: du H gio => thoat tai close.
- Phi 0,07 % moi chieu tren notional; funding theo ky thanh toan trong luc giu (rate > 0 => short nhan). Khong DCA.
- Tang danh muc: GIU NGUYEN nhu B0 (top-K theo s = min(z_oi, z_f), size = equity x 0,60 / K_max, cooldown 72 h tu luc vao, von 10 000, 1x, E0 / E1
  theo ADDENDUM1 diem A); quyet dinh vao moi gio; vi the thoat giua gio thi cho trong tu gio ke tiep. Equity MTM moi gio theo close; maxDD "xau
  nhat" dung max close 1m trong gio cho vi the dang mo.

## 3. Luoi (CO DINH; 2 x 2 x 3 x 3 x 3 x 5 x 13 = 7 020 cau hinh)
W in {14, 7}; vao in {E0, E1}; z_min in {2,5 ; 3,0 ; 3,5}; K_max in {3, 5, 10}; SL in {15 %, 30 %, 50 %}; H in {24, 72, 168, 336, 720} gio
(720 = "giu toi da 30 ngay"); trailing in {tat} + {arm 3, 5, 7, 10 %} x {gap 2, 3, 5 %}.

## 4. Thuoc do va bao cao (moi cau hinh: toan DEV + fold F1 2022-23, F2 2024, F3 2025, moi fold tu von 10 000 - nhu B0 muc 4)
Bao cao bat buoc:
(i) IN-SAMPLE: so cau hinh hop le (>= 30 lenh / fold, lai ca 3 fold, maxDD xau nhat <= 30 %), cau hinh chon theo luat maximin + cao nguyen
    (>= 60 % hang xom doi 1 tham so 1 nac cung lai ca 3 fold), top 20, anh huong bien tung tham so.
(ii) WFO-OOS (so DANG TIN): nam Y = 2024: chon cau hinh theo luat tren CHI bang F1 => ket qua F2; nam Y = 2025: chon bang F1 + F2 => ket qua F3.
    Bao top-1 VA trung vi / ti le duong cua top-20 theo luat chon. (2023 khong lam OOS duoc vi 2022 gan nhu khong co su kien - lech so voi
    PROGRAM muc 3, ghi nhan; tieu chi R1 doc la: lai o CA HAI nam 2024 va 2025.)
(iii) Tinh ben: tuong quan hang diem fold giua cac cau hinh (F1-F2, F2-F3, F1-F3); ti le cau hinh lai tung fold.
(iv) Phan ra cau hinh chon va WFO top-1: theo ly do thoat (SL / trailing / time), dong gop top 5 % lenh, theo thang, theo coin, funding, lenh te
    nhat so voi muc SL, tuong quan voi EW alt.
(v) Doi chieu B0: cung tham so 759 / 758 (W7 E0 z3,0 K3 SL15 H24) voi trailing 10 % / 5 % tren engine 1 phut - lai con khong.
(vi) Doi chung ngau nhien DUNG NGHIA: >= 100 lan; moi lan thay ung vien bang ung vien ngau nhien (so DOT moi thang = so dot that cua lop
    (W, kieu vao, z_min) tuong ung, rut deu tu universe cua thang - ADDENDUM2 G1) roi chay TOAN BO luoi thoat; thong ke = diem cao nhat qua
    luoi (maximin) va so cau hinh hop le. p_max = ti le lan ngau nhien co diem cao nhat >= diem cao nhat that. Neu khong kip tinh toan thi
    giam con luoi thoat x K cua lop (W7, E0) va (W14, E0) - ghi ro.

## 5. Ket luan cho phep sau B1
- "DI TIEP B2": WFO-OOS top-1 lai o CA 2024 va 2025 VA trung vi top-20 WFO > 0 o ca hai nam VA p_max <= 0,05.
- Nguoc lai: ap luat dung som (PROGRAM muc 5): MASTER bao owner so thuc va KHUYEN DUNG truoc B2 / B3; owner quyet.
- Du ket qua nao cung KHONG phai GO trien khai / holdout; khong goi so in-sample la ky vong.

## 6. Thi hanh
Python offline tren Oracle (logging; numpy vector hoa: tinh truoc duong gia 1m toi 30 ngay cho moi (ung vien, gio vao) roi tinh moi cau hinh
thoat; khong pandas trong vong lap), thu muc ~/claude_master/w3/levz_b1/. Viec nang qua flock oracle_heavy.lock (khong long), toi da 3 tien
trinh, RAM trong >= 4000 MB, dia >= 15 GB, work <= 10 GB. Trinh tu: DEV viet engine + test (tinh tay tung co che; bat bien ke toan; khong
look-ahead; doi chieu engine 1m voi sim nen gio B0 tren cau hinh KHONG trailing: so lenh / ly do thoat phai gan nhau, giai thich lech) ->
A1 audit (agent khac, co ban tham chieu doc lap) TRUOC khi chay luoi -> RUN -> A1 audit ket qua -> MASTER tu kiem >= 3 so -> bao owner.
