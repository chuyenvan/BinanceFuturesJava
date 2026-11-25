# MASTER_NOTE LEVZ2 tang B0 (ban do tho) - 2026-11-25 22:00 +0700
Prereg 278725ae + ADDENDUM1 f6157c87 + ADDENDUM2 c10a681b; khung PROGRAM_SHORT_LEVZ. Simulator nen gio (sim.py 874e561f) A1 PASS (khop ban tham
chieu doc lap ~1e-15, khong look-ahead). Luoi 1 296 cau hinh chay 21:48-21:51. Audit ket qua: A1_LEVZ2_B0.md (moi so cua MASTER duoc xac nhan).

## So chinh (IN-SAMPLE toan DEV 2022-2025; KHONG phai ky vong)
- 69 / 1 296 cau hinh hop le (lai ca 3 fold, >= 30 lenh / fold, DD <= 30 %). Loi nhuan > 0: DEV 54,6 % cau hinh; 2022-23 61,0 %; 2024 18,9 %;
  2025 77,1 %; ca 3 fold 8,1 %. DEV_ret trung vi +2,2 %.
- Cau hinh chon theo luat (759): W7, E0, z_min 3,0, K3, SL 15 %, H24, trailing bat, DCA bat: 294 lenh, +102,4 % (CAGR 19,3 %), maxDD 24,2 %,
  fold +21,1 / +21,6 / +37,9 %, thang 64 %, phoi nhiem TB 3,1 %. Ban DCA tat (758): CAGR 15,7 %, DD 19,7 %.
- CANH BAO (A1): 15 lenh tot nhat (5 %) tao 142 % lai rong - bo di thi LO; thang 2025-11 chiem 87 % lai; top 5 coin 93 %; toan bo lai nam o
  nhanh trailing 10 % / 5 % tren nen GIO (trail +26,9k, SL -21,4k, time +4,9k); cao nguyen 6/9 rat mong.
- KHONG co tinh ben giua cac nam: Spearman diem fold F1-F2 +0,12; F2-F3 -0,58; F1-F3 -0,12. WFO: chon theo 2022-23 -> 2024: top-1 +7,6 %
  nhung top-20 trung vi -9,0 % (40 % duong); chon theo 2022-24 -> 2025: top-1 +14,3 % nhung top-20 trung vi -5,6 % (toan luoi +18,8 %).
- Doi chung ngau nhien: p_rand = 0,000 bi thien lech chon loc (so cau hinh TOT NHAT cua 1 296 voi luot ngau nhien cua 1 bo thoat). Duoc noi:
  voi cung bo thoat, tin hieu E0 tot hon short ngau nhien (6/18 cau hinh E0 vuot moi luot ngau nhien; ngau nhien DEV trung vi -33 %). Lai
  khong den tu beta (tuong quan PnL ngay voi EW alt -0,11; short EW cung phoi nhiem -14 %).
- Ban do tham so (trung vi DEV_ret theo gia tri): W7 > W14; K nho > K lon; z_min 3,0-3,5 > 2,5; H 24-72 > 168; SL 50 % > 15-30 %; trailing bat
  hoi hon tat; DCA khong khac (va gan nhu bi tran 60 % chan).

## Ket luan B0
Chua co bang chung edge ben. Co manh moi: (i) tin hieu vao tot hon ngau nhien khi cung bo thoat; (ii) phan lai nam o TRAILING => B1 (engine nen
1 phut, trailing arm 3-10 %, giu dai, SL luon bat) la phep kiem quyet dinh; neu trailing tren nen 1 phut khong giu duoc lai => ap luat dung som
(PROGRAM muc 5). Khong duoc noi: "co edge", "CAGR 19 % la ky vong", "DCA / trailing giup ich", "san sang holdout".
