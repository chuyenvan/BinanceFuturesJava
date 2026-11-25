# PREREG_LEVZ2 - tang 2: MO PHONG DANH MUC + TOI UU tren DEV cho he short "cang don bay" (z-score OI + funding), top-K + SL
Chot boi MASTER 2026-11-25 20:57 +0700, TRUOC khi viet simulator va truoc khi chay bat ky cau hinh nao.

## 0. Boi canh va vi tri trong quy trinh
- Tang 1 (PREREG_LEVZ 5e1031bc, result fe9aa386): do su kien, giu co dinh 24 h, KHONG stop / trailing / DCA / chon loc => NO-GO theo luat tang 1.
- Hau kiem 25/11 (chua audit): chon lenh manh nhat + SL 30 % + giu 72 h cho so tot hon o 2024-25, yeu o 2022-23.
- Owner 25/11: "lay top k va sl 30% xem the nao"; "da sim da toi uu gi dau ma fw voi holdout". => Trinh tu DUNG cua du an: (1) sim danh muc
  + toi uu tren DEV, (2) chot MOT cau hinh, (3) HO 2026 mot lan (prereg rieng, owner quyet). File nay la buoc (1)-(2).
- DEV = 2022-01-01..2025-12-31 (khoi dong tu 2021-12). Toan bo DEV duoc dung de TOI UU; khong con ky nao trong DEV duoc goi la "xac nhan".
  KHONG doc 2026 (reader assert ts < 2026-01-01 UTC).
- Da kiem dinh: luoi duoi day = 1 296 cau hinh tren ~600-1 500 su kien => nguy co overfit CAO; vi the co luat chon chot truoc (muc 5) va
  doi chung ngau nhien (muc 6). Ket qua DEV sau toi uu KHONG phai bang chung edge; bang chung chi den tu HO 2026.

## 1. Du lieu
- Tin hieu: dung lai DUNG pipeline tang 1 (code dong bang w3/levz/code, FREEZE.txt): z_oi, z_f, f, z_r theo gio cho W in {14, 7} ngay,
  cung luat nhan qua (OI ts <= t - 10 phut; funding ts <= t - 1 phut), cung universe (qv30 >= 20M, >= 45 ngay, loai stable / chi so), cung san sd.
- Gia de mo phong: nen 1h co HIGH / LOW: /home/ubuntu/java/fsrun/OHLCV_1H_v2.bin (+ manifest; ts_h = gio DONG; 626 symbol; 2021-01..2025-12).
  Kiem cheo bat buoc: close 1h cua store so voi clast cua w3/levz/work/hr_*.parquet (Vision 1m): lech tuong doi <= 1e-3 o >= 99,5 % (coin, gio)
  trong universe; khong dat => DUNG, bao MASTER. Coin / gio khong co trong store => khong vao lenh moi; vi the dang mo thieu gia > 24 h => dong tai
  close cuoi cung co, gan co.
- Funding: funding lake nhu tang 1.

## 2. Co che mo phong (chi SHORT, don bay 1x, vong lap theo gio)
- Von dau 10 000; equity MTM moi gio (vi the short danh gia theo close; DD tinh tren equity MTM theo close VA bao them DD "xau nhat trong gio"
  dung HIGH cho vi the dang mo).
- Ung vien tai gio t (thong tin den het gio t): E0: LEV(t) = z_oi >= z_min VA z_f >= z_min VA f > 0,0001, coin chua co vi the va khong trong
  cooldown. E1: coin co LEV trong 24 h truoc va gio t co z_r <= -2 (lan dau ke tu dot LEV do). Cooldown 72 h moi coin tinh tu luc VAO.
- TOP-K: xep ung vien theo s = min(z_oi, z_f) giam dan (hoa: sym tang dan); vao lan luot cho toi khi so vi the mo = K_max.
- Size moi lenh = equity hien tai x 0,60 / K_max (tong phoi nhiem toi da 60 %). Gia vao = close gio t. Phi + truot: 0,07 % moi chieu (0,14 % khu hoi).
- Thoat (kiem theo thu tu nay trong moi nen gio SAU gio vao; gia dinh xau: trong mot nen, HIGH xay ra TRUOC LOW):
  (a) SL: neu open >= muc stop => thoat tai open; neu high >= stop => thoat tai stop x (1 + 0,005) (truot 0,5 % khi bi squeeze). Muc stop =
      gia vao DAU TIEN x (1 + SL).
  (b) DCA (neu bat): mot lan duy nhat, khi high >= gia vao dau x 1,10 va chua cham SL: them 1 lenh cung size tai gia vao dau x 1,10 (neu tong
      phoi nhiem sau khi them <= 60 %); SL van tinh tu gia vao dau.
  (c) Trailing (neu bat): kich hoat khi low <= gia vao binh quan x (1 - 0,10); muc trail = day thap nhat da thay x (1 + 0,05); trong mot nen:
      kiem trail bang muc cua nen TRUOC (high >= muc trail => thoat tai muc trail x 1,001), sau do moi cap nhat day bang low nen nay.
  (d) Time-stop: het H gio ke tu luc vao => thoat tai close.
- Funding: tai moi ky thanh toan vi the dang mo nhan rate x notional (rate > 0 => short nhan). Huy niem yet: nhu muc 1.

## 3. Luoi tham so (CO DINH, 2 x 2 x 3 x 3 x 3 x 3 x 2 x 2 = 1 296 cau hinh; khong them, khong bot)
W in {14, 7} ngay; kieu vao in {E0, E1}; z_min in {2,5 ; 3,0 ; 3,5}; K_max in {3, 5, 10}; SL in {15 %, 30 %, 50 %}; H in {24, 72, 168} gio;
trailing in {tat, bat (10 % / 5 %)}; DCA in {tat, bat (+10 %, 1 lan)}.

## 4. Thuoc do moi cau hinh
Toan DEV va tung fold: so lenh, ti le thang, lai rong TB / lenh, lenh te nhat, CAGR, maxDD (MTM close; MTM xau-nhat-trong-gio), Calmar, Sharpe
ngay, phoi nhiem TB, ti le lenh thoat theo tung ly do (SL / trail / time), funding nhan, PnL theo nam.
Fold: F1 = 2022-01..2023-12 (2022 gan nhu khong co su kien), F2 = 2024, F3 = 2025. Moi fold chay doc lap tu von 10 000.

## 5. Luat CHON cau hinh (chot truoc; ap dung may moc)
- Hop le: >= 30 lenh o MOI fold VA loi nhuan rong > 0 o CA 3 fold VA maxDD (xau-nhat-trong-gio) toan DEV <= 30 %.
- Xep hang cau hinh hop le theo diem = MIN qua 3 fold cua (loi nhuan fold / maxDD fold) (maximin).
- Dieu kien cao nguyen: xet cau hinh hang cao nhat; cac "hang xom" = doi dung MOT tham so sang gia tri ke ben trong luoi; neu < 60 % hang xom
  co loi nhuan > 0 o ca 3 fold => loai, xet cau hinh ke tiep. Cau hinh dau tien qua duoc = CAU HINH CHON. Khong co => "KHONG CO CAU HINH".
- Bao cao bat buoc: ti le cau hinh hop le / 1 296; phan phoi diem; top 20; anh huong bien tung tham so (trung vi diem theo tung gia tri).

## 6. Doi chung ngau nhien (cho CAU HINH CHON)
500 lan: giu nguyen moi co che thoat / size / K_max cua cau hinh chon, thay tap ung vien bang ung vien NGAU NHIEN: moi thang, so (coin, gio)
ung vien bang dung so ung vien that cua thang do, rut deu tu universe cua thang; diem s ngau nhien. p_rand = ti le lan ngau nhien co diem
(muc 5) >= cau hinh chon. (Tra loi: lai den tu TIN HIEU hay tu "short alt + co che thoat".)

## 7. Ket luan cho phep
- "DU DIEU KIEN DI HO 2026": co CAU HINH CHON VA p_rand <= 0,05 VA toan DEV: CAGR > 0, Calmar >= 0,5.
- Nguoc lai: "KHONG DI HO" - dong ho LEVZ (khong mo rong luoi, khong doi luat chon).
- Du dieu kien cung KHONG phai GO trien khai: buoc sau = prereg HO 2026 (01-09/2026, dung MOT lan, cau hinh dong bang, nen 1m co high tu
  Kaggle vz-kline1m-2026) - owner quyet. Sau HO moi ban toi von / ghep voi he long / engine SELL trong jar.

## 8. Thi hanh
Python offline tren Oracle (logging, khong print), thu muc ~/claude_master/w3/levz2/. KHONG Java / sim Kaggle / 242. Viec nang:
mkdir -p ~/claude_master/locks && flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 <cmd> (khong long flock; RAM trong >= 4000 MB;
dia >= 15 GB; toi da 3 tien trinh song song). Trinh tu: DEV viet simulator + test don vi (tung co che thoat, funding, phi, top-K, cooldown, tran
phoi nhiem, bat bien ke toan: tong PnL lenh = thay doi equity) -> A1 audit simulator (agent KHAC) TRUOC khi chay luoi -> RUN luoi + muc 5, 6 ->
A1 audit ket qua -> MASTER tu kiem >= 3 so -> bao owner. Khong gui owner so chua audit.
