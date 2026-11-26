# PREREG_LEVZ_B2 - tang B2 cua PROGRAM_SHORT_LEVZ: GATE theo che do thi truong + FILTER cap coin (theo luat, chua ML)
Chot boi MASTER 2026-11-26 12:30 +0700, TRUOC khi viet code B2 va truoc khi chay bat ky phuong an gate / filter nao.

## 0. Boi canh
- B1 (prereg 54f40792 + ADD1 3226e940; engine A1 PASS-WITH-MINOR): luoi 7 020 cau hinh da chay 2026-11-26 12:06. MASTER DA THAY (chua audit ket
  qua, doi chung ngau nhien con chay): 600 cau hinh lai ca 3 fold; ti le cau hinh co lai F1 64 %, F2 (2024) 20 %, F3 84 %; WFO: chon theo F1
  -> 2024 top-1 -36 %, top-20 trung vi -23 %; chon theo F1+F2 -> 2025 top-1 +11 %, top-20 trung vi +6 % (toan luoi +15 %); tuong quan hang
  diem fold F2-F3 = -0,49. => Tieu chi "DI TIEP B2" cua B1 KHONG dat; luat dung som: MASTER khuyen dung.
- Owner 2026-11-26 (truoc khi co so B1): "cho agent chay song song short di. kaggle ranh ma. oracle cung dung it" => owner quyet DI TIEP.
- Vi the B2 nham dung cho hong da thay: nam 2024 (alt tang manh) short thua tren dien rong. Gia thuyet co che: chi nen short khi thi truong
  alt KHONG trong xu huong tang. Vi gia thuyet nay sinh ra SAU khi thay so B1, ket qua B2 tren DEV la in-sample ve mat chon gia thuyet;
  bang chung that chi den tu HO 2026.

## 1. Du lieu va chuoi cap thi truong (nhan qua: tai gio t chi dung nen gio da dong <= t; chi < 2026-01-01 UTC)
- Dung lai tin hieu, universe, bang exits (195 bo thoat) va tang danh muc cua B1 (w3/levz_b1) - KHONG doi engine.
- EWr_n(t) = trung binh deu, tren universe tai t, cua close(t) / close(t - n ngay) - 1, n in {3, 7, 14}.
- BTCdev_n(t) = close_BTCUSDT(t) / trung binh close gio cua n ngay truoc (khong gom t) - 1, n in {7, 20}.
- BR(t) = ti le coin universe co LEV (z_oi >= 2,5 VA z_f >= 2,5 VA f > 0,0001, W = 7) it nhat mot gio trong 24 h truoc; BRmed(t) = trung vi
  BR tren 90 ngay truoc (khong gom t; can >= 80 % mau).
- Cap coin tai t: qv30 (ngay truoc), tuoi niem yet, r24(t) = close(t) / close(t - 24 h) - 1, f(t).

## 2. Phuong an (12 phuong an DON, khong to hop; moi phuong an chi chan ung vien VAO moi - khong dong vi the dang mo)
GATE (chi nhan ung vien tai gio t neu): G_EW3: EWr_3 <= 0; G_EW7: EWr_7 <= 0; G_EW14: EWr_14 <= 0; G_BTC7: BTCdev_7 <= 0; G_BTC20: BTCdev_20
<= 0; G_BRhi: BR >= BRmed; G_BRlo: BR < BRmed.
FILTER (chi nhan coin neu): F_LIQ50: qv30 >= 50M; F_AGE90: niem yet >= 90 ngay; F_NOPUMP: r24 < +20 %; F_PUMP: r24 >= +10 %; F_FHI: f >= 0,0003.
Thieu du lieu de tinh dieu kien => KHONG nhan ung vien (bat loi).

## 3. Phep do (moi phuong an O x TOAN BO 7 020 cau hinh B1, ghep cap voi ban goc khong gate)
Theo tung fold F1 / F2 / F3 va DEV: loi nhuan, maxDD xau nhat, so lenh. Bao cho moi O: trung vi loi nhuan va ti le cau hinh co lai tung fold;
trung vi cua (loi nhuan co O - loi nhuan goc) va ti le cau hinh duoc cai thien tung fold; ti le so lenh con lai; so cau hinh hop le (luat B1);
WFO top-1 / top-20 (luat B1 + ADD1) khi co O; ti le thoi gian gate mo theo nam (voi GATE).

## 4. Tieu chi "phuong an CO TAC DUNG" (phai dat TAT CA)
(a) F2 (2024): ti le cau hinh co lai >= 50 % VA trung vi loi nhuan >= 0.
(b) F1 va F3: trung vi loi nhuan khong kem ban goc qua 2 diem %; ti le cau hinh co lai khong thap hon ban goc qua 10 diem %.
(c) So lenh con lai (trung vi qua cau hinh) >= 50 % ban goc o MOI fold.
(d) WFO khi co O: trung vi top-20 > 0 o CA 2024 va 2025.
(e) Doi chung gia duoc (placebo), chi chay cho phuong an da dat (a)-(d): 500 lan; GATE: dich vong chuoi gate mot do lech ngau nhien >= 30
    ngay (giu nguyen ti le mo va cau truc cum); FILTER: hoan vi nhan coin giua cac coin trong cung thang (giu ti le bi loai). Tren mau co dinh
    300 cau hinh (rut 1 lan, seed ghi trong code, phan tang theo W x kieu vao x z_min). Thong ke = ti le cau hinh co lai o F2. p = ti le
    placebo >= gia tri that. Dat neu p <= 0,05 / 12 (Bonferroni cho 12 phuong an).

## 5. Ket luan cho phep
- Co >= 1 phuong an dat (a)-(e): "B2 CO UNG VIEN" - buoc sau (prereg rieng): dong bang he = B1 + phuong an do (uu tien phuong an don gian
  nhat neu nhieu cai dat), kiem lai R1-R7 cua PROGRAM muc 4; dat thi de nghi owner HO 2026.
- Khong phuong an nao dat: "B2 KHONG CUU DUOC" - MASTER bao owner so thuc; khuyen nghi DUNG chuong trinh short (khong lam B3 ML tren nen
  khong on dinh), owner quyet. Khong thu to hop / nguong khac de vot.
- Du the nao cung khong goi so DEV la ky vong; khong trien khai.

## 6. Thi hanh
Python offline tren Oracle, thu muc ~/claude_master/w3/levz_b2/ (import code B1, khong sua w3/levz_b1); logging; flock oracle_heavy.lock cho viec
nang, toi da 3 tien trinh, dia Oracle chi con ~15 GB => khong tao file > 1 GB. Trinh tu: DEV (chuoi gate nhan qua + lop loc ung vien + luoi + bao
cao + placebo + test: nhan qua, khong look-ahead, gate tat = ket qua B1 trung tuyet doi) -> A1 audit (agent khac) -> RUN -> A1 audit ket qua ->
MASTER tu kiem >= 3 so -> bao owner.
