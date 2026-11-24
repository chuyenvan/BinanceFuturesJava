# PREREG_P15_STAB - tim cach train / suy luan p15 ON DINH giua cac lan retrain (khong doi jar, khong doi model live)
MASTER, 2026-11-24 14:30 (+07). Owner 24/11: "model train khong on dinh kieu nay rat nguy hiem => tap trung tim giai phap cho on dinh ; chua doi jar,
model de nguyen, ke hoach pilot giu nguyen". Viet TRUOC khi chay. Can cu: docs/result/retrain_root/MASTER_CONCLUSION_RETRAIN_ROOT_1124.md (1dd5e393).

## 0. Van de
Duoi cuc tri cua p15 (thu quyet dinh gate q0,99995 va DCA >= 0,008) doi manh khi chi doi seed train (recipe PROD: subsample / colsample 0,8) hoac doi mep cut
vai tram dong ; moi lan retrain = mot lan "rut" khac ve so lenh / tap lenh. Muc tieu: mot quy trinh tao p15 ma (i) on dinh giua cac lan lap lai,
(ii) khong kem ve chat luong, (iii) trien khai duoc ma KHONG can doi code jar (1 file model).

## 1. Du lieu
CHI DEV: ts < 2026-01-01 00:00 UTC (loc + assert truoc khi nap). Khong 2026, khong PnL 2026, khong gi >= 2026-10-01. Feature: gate_dataset_full.csv (a1c78e2f).
Quy danh gia: 2022Q1..2025Q4 (16 quy, co bins A3 cho replay gate) ; fold p15 train = cac fold sinh ra cac quy do (va fold truoc neu can bo dem 90 ngay).

## 2. Ung vien (co dinh ; khong them sau khi thay so)
Recipe goc PROD = train_gate_fold.py b41c9159 goi nhu rt_p15_train.py (mep +07 - 15').
- C0  : 1 model PROD, 1 seed (hien trang).
- E4  : trung binh cong diem cua 4 model PROD khac seed.
- E8  : trung binh cong diem cua 8 model PROD khac seed.
- DET : 1 model PROD voi subsample = 1, colsample_* = 1 (khong con ngau nhien theo seed) ; moi tham so khac giu nguyen.
Lan lap (replicate): ho SEED = cac seed / nhom seed ROI NHAU (32 seed moi fold: C0 dung 8 seed dau ; E4 = 8 nhom roi ; E8 = 4 nhom roi ; DET khong co ho SEED).
Ho EDGE = cung seed, cat bot 1 / 2 / 3 ngay cuoi tap train (C0 seed 42 ; DET ; E8 nhom 1 chi voi -2 ngay + goc).
Kiem cong cu: (k1) PROD seed 42 cut 2026-07-01 tai lap booster T1 sha 71e82572 TREN MOI TRUONG CHAY (neu chay Kaggle: pearson pred tren mau DEV >= 0,9999 so voi ban
Oracle la du) ; (k2) E8 gop thanh MOT booster (noi cay, chia la cho K, xu ly base_score) cho pred == trung binh thanh vien (max|d| <= 1e-6) - chung minh trien khai
1 file model kha thi. k1 khong dat => DUNG. k2 khong dat => van do, nhung ghi "trien khai can doi code".

## 3. Tang S1 - do on dinh (khong sim, khong PnL)
Voi moi quy Q va moi ung vien X, tren pred WFO cua X:
- TAIL(X, ho) = trung vi theo quy cua sd (giua cac lan lap trong ho) cua log q99,995(p15) ; bao them q99,99.
- GATE: replay gate offline (cong cu da hop le o RETRAIN_ROOT M2 ; kiem lai hop le voi chuoi C0 seed 42: khong can khop log sim, chi can chay duoc tren 16 quy) cho
  TUNG lan lap (chuoi pred day du cua lan lap do). J(X, ho) = trung vi theo quy cua Jaccard trung binh cap giua cac tap su kien pass (muc (phut, coin) neu cong cu
  xuat duoc, neu khong thi muc phut - chon TRUOC khi tinh, ghi ro) ; CVN(X, ho) = trung vi theo quy cua sd / mean so pass.
- DCA: CVF(X, ho) = trung vi theo quy cua sd / mean cua frac(p15 >= 0,008).
- RULER: IC Spearman(p15, nhan train cua recipe) theo quy, trung binh cac lan lap ; dIC(X) = trung binh theo quy cua IC(X) - IC(C0), CI95 bootstrap theo quy.
Dat S1 (ghi truoc) - X thuoc {E4, E8}:  (a) TAIL(X, SEED) <= 0,5 x TAIL(C0, SEED) ; (b) J(X, SEED) >= J(C0, SEED) + 0,10 VA CVN(X, SEED) <= 0,6 x CVN(C0, SEED) ;
  (c) [chi E8] TAIL(E8, EDGE) <= 0,6 x TAIL(C0, EDGE) ; (d) dIC(X) >= -0,005.
  DET: (c') TAIL(DET, EDGE) <= 0,6 x TAIL(C0, EDGE) VA J(DET, EDGE) >= J(C0, EDGE) + 0,10 ; (d) dIC >= -0,005. (DET khong xet (a)(b).)
Bao day du ca cac chi so khong dung de cham (CVF, q99,99, theo tung quy). Khong ung vien nao dat => ket luan "ensemble / bo sampling KHONG du" ; bao owner ; khong sang S2.

## 4. Tang S2 - kiem PnL DEV (sim Kaggle ; CHI cho ung vien dat S1 ; chay sau khi S1 da ghi + audit)
Lane: p15 = ung vien ; net015 + S1 giu WFO (pool / ledger S1 dung lai theo p15 nhu rt_lane) ; profile K24 + skipFull nhu baseline. Lan lap: C0-PROD 4 seed ;
E4 / E8: 4 nhom roi ; DET: goc + 3 EDGE. Scorer / MTM nhu baseline (ROI D5 theo quy ; CAGR22, maxDD qua gvz_mtm, missing = 0).
Dat S2 (ghi truoc): (e) DISP(X) = trung vi theo quy cua sd (giua lan lap) ROI quy <= 0,6 x DISP(C0) ; (f) khong kem: CAGR22 trung binh X - C0 >= -1,5 pp VA maxDD
  trung binh khong sau hon qua 2,0 pp. Luc thong ke thap (4 lan lap) - ghi ro ; khong doc (f) la "tot hon".
Nhieu ung vien dat S2 => chon theo thu tu CO DINH (don gian truoc): DET, roi E4, roi E8.

## 5. Sau S2 (KHONG nam trong prereg nay)
Ung vien duoc chon => prereg rieng: holdout + parity + cach dua vao live (1 file model gop) ; owner quyet. Truoc do KHONG doi model / jar live.
Chua xet: net015 (P(win) khong hieu chuan, train GPU khong tat dinh) va nguong DCA tuyet doi 0,008 - viec tiep theo, prereg rieng.

## 6. Quy trinh
Train nhieu model: Kaggle CPU (dataset gate-dataset-full) hoac Oracle duoi flock oracle_heavy.lock (khong long ; khong chay luc R-LIVE). Agent RUN ; agent A1 KHAC kiem
doc lap (tai tinh >= 5 so, kiem assert du lieu, kiem k1 / k2). Ket qua: docs/result/p15_stab/. Khong sua nguong / ung vien sau khi thay so ; sai cong cu => errata, bao ca hai luot.
