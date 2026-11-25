# DEV_LEVZ2 - bao cao agent DEV (simulator + test), PREREG_LEVZ2 @278725ae. 2026-11-25. CHUA AUDIT, CHUA CHAY LUOI.

## S1 - tai lap tap dot tang 1 tu bang tin hieu: PASS 100 %
sig.py IMPORT levz.Data('2025-12') + levz.signals (khong viet lai). Tu work/sig_W*.parquet ap levz.episodes (z>2.5 ca hai, f>1e-4, cooldown 72h)
+ levz.e1_entry, t0 >= 2022-01-01, so voi events KP+XN: A1 634/634, A3 757/757 (sym,t0); A2 462/462, A4 536/536 (sym,t0,te); 0 le hai phia.
(work/s1.json; chay lai sau khi sua guard sys.path: van PASS.)

## S2 - gia store vs panel Vision: PASS
Quy uoc xac dinh bang du lieu: store t (gio DONG) == panel h + 1h: 99.999 % (4 744 683 / 4 744 733) lech <= 1e-3 trong universe
(q99 5e-8; max 0.51 tai 1 vai diem). Quy uoc store t == h: chi 10.6 % => loai. Phu: 99.09 % (sym, gio) universe co nen store; phan thieu => khong vao lenh.

## Test: 46/46 PASS (test/test_sim.py, du lieu tong hop, ky vong tinh tay; test/test_report.json)
SL cham / gap open / uu tien SL hon time-stop; nen vao khong kiem; time-stop; trailing kich hoat / khong / gap / cap nhat day sau kiem / SL truoc trail;
DCA co / bi tran chan (1 vi the, 2 vi the) / khong khi SL / SL tu gia dau; funding duong / am / cua so vao-ra / khong nhan o nen thoat trong nen /
notional theo close; phi; top-K + pha hoa; cooldown 72 (72 chan, 73 vao); khong vao lai khi dang mo; cho trong cung gio; size theo equity hien tai;
thieu gia > 24h; thieu nen o time-stop; eod; khong vao o gio cuoi; equity xau-nhat-trong-gio; maxDD; ung vien E0 / E1; 1 296 cau hinh;
hop le / maximin / hang xom / cao nguyen (tu choi -> ke tiep, 60 % dung bien, KHONG CO CAU HINH); rut ngau nhien (so dem, seed).
Bat bien ke toan (4 seed x trail x DCA x K, du lieu ngau nhien co gap + funding): max |sum PnL - (equity cuoi - 10 000)| <= 1e-6 (thuc te ~1e-10);
smoke that: 1.6e-11. Khong look-ahead: doi gia/funding/ung vien sau t => lenh, equity den t trung tuyet doi. Tat dinh: 2 lan trung.

## Toc do
Smoke that: 0.05 s/lan, run_all (DEV+3 fold) 0.10 s. Bench tong hop kich thuoc that (35 808 x 631, ~5 400 ung vien): 0.40-1.73 s/cau hinh
(nang nhat K10 H168 trail+DCA). => luoi ~10 phut, ngau nhien ~5 phut tren 3 tien trinh.

## Smoke that (W14 E0 z2.5 K10 SL50 H24, khong trail/DCA, toan DEV) - cau hinh that DUY NHAT da chay
584 lenh (F1 160 / F2 320 / F3 104); thoat: time 565, SL 17 (2.9 %), time_sub 1, eod 1. Doi chieu A1 (634 events) theo (sym, te): 542 trung.
- 92 chi tang 1: 64 top-K day (10 vi the dang mo), 25 top-K cat trong cung gio, 2 khong co nen store tai te, 1 coin vua vao <= 72h truoc (chuoi lech).
- 42 chi sim: deu la "chuoi lech" - dot tang 1 cung coin trong 72h truoc khong duoc vao (top-K) nen sim vao o gio LEV sau.
- 523 lenh trung thoat time: gross sim - gross_24 tang 1: TB -0.012 %, median |.| 0.20 %, q95 |.| 1.15 %, max 3.2 % (gia store close nen gio vs
  close nen 1m sau 1 phut o ca 2 dau). 17 SL trung: 15 co MAE_close tang 1 >= 50 %; 2 cham SL bang HIGH trong gio (MAE_close la can duoi).
(out/smoke.json, smoke_diag.json, smoke_trades/equity/vs_A1.parquet)

## CHOICES2 + CAN MASTER QUYET: xem CHOICES2.md (23 muc + A-D).

## sha256: SHA256SUMS.txt

## A1 can soi
1. Thu tu trong buoc gio + quy tac funding vao/ra (CHOICES2 10-12). 2. Dinh nghia E1 (8, A). 3. DCA tran + gia (14). 4. trailing gap (15).
5. maxDD worst va peak (19). 6. Quy uoc gio S2 / gia vao (1-2). 7. Pool ngau nhien (23). 8. guard sys.path vi code/select.py trung ten module chuan.

## KHONG kiem duoc
- Khong chay cau hinh that nao khac smoke => hanh vi E1 / trail / DCA / K3-5 / H72-168 tren du lieu that chi kiem bang test tong hop.
- Thu tu that trong nen gio (gia dinh HIGH truoc LOW theo prereg). Truot thuc te. Gia mark cho funding (dung close nen).
- grid.py / rand.py chua chay end-to-end tren du lieu that (chi ham loi duoc test); select.py chi test tren luoi gia.
