# A1 AUDIT - PREREG_P15_STAB Tang S1 (agent A1, Opus, 2026-11-24)
Doi tuong: RESULT_P15_STAB_S1.md (sha 87db3d8dcdba57d6), out/S1_*.{json,tsv}, code b_*.py, Pha A. Prereg sha 56cf84b0d38edf2d (xac nhan).
Code A1 (doc lap, khong import code RUN): a1/a1_tail.py, a1_fam.py, a1_ic.py, a1_gate.py (dung gate_offline/gsf lam thu vien), a1_j.py.

## VERDICT: PASS-WITH-MINOR
Nhan A1 xac nhan (theo dung luat prereg): E4 KHONG DAT (b: CVN x0.662 > 0.6) ; E8 DAT (a)(b)(c)(d) ; DET KHONG DAT (c': TAIL x1.282, J +0.075).
So lieu RUN tai lap chinh xac (sai lech <= 5e-7). Rui ro chinh la DIEN GIAI (dieu kien (c) mong, J la so lac quan) - xem Loi + Y kien.

## 1. Tuan thu prereg (doc code + mtime)
- Dinh nghia TAIL/J/CVN/CVF/IC/dIC trong b_score/b_build khop prereg muc 3; luat (a)(b)(c)(c')(d) cham dung (b = J VA CVN; DET khong xet (a)(b); (d) tren uoc luong diem).
- D1-D11: hop ly. Bang chung "chot truoc khi tinh": mtime code b_build 17:31:40, b_gate 17:31:58, b_score 17:32:39 < output dau tien (check.json 17:34:56, tail_cvf_rep 17:35:09, S1_result 17:40:12). Dong NOTE dinh chinh nam truoc dong 17:35 trong file append-only. b_report.py sua 17:41:23 (sau so) nhung chi format bao cao, khong tinh. => Khong thay dau hieu chon cach tinh sau khi thay so. Han che: khong co hash/commit cho tung dong progress (chi mtime) - MINOR.
- SEED_PLAN.json mtime 15:01:46 < kernel start 15:03:50 (+07, log kernel). Nhom E4 (8x4) va E8 (4x8) roi nhau thuc su; C0 = 8 seed dau = E8 nhom 1 (chung seed giua HO khac nhau khong anh huong sd trong ho).
## 2. Du lieu / tham so
- 4 kernel: limit_ms=1767225600000, ts_max store 2025-12-31 23:59; 0 Traceback; 782/782 job xgb 3.2.0; train_ts_max lon nhat 2025-09-30 16:44 UTC. Chuoi pred ts max 2025-12-31 16:59 UTC.
- k1 la nhanh DUY NHAT dung 2026H1 (Oracle 15:02, limit 2026-07-01, khong luu pred: khong co thu muc/file 2026 trong out/ va kout/). Xac nhan.
- DET: 68 job, subsample=1, colsample_bytree/bylevel/bynode=1; moi tham so khac trung PROD (max_depth 4, n_est 150, lr 0.05, mcw 10). Luu y: PROD colsample_bylevel/bynode = None (mac dinh 1) => DET chi khac o subsample + colsample_bytree.
- EDGE: train_rows giam dung 1440/ngay, train_ts_max lui dung 1/2/3 ngay (kiem fold 20220101, 20250701; PROD va DET).
## 3. Tai tinh doc lap (A1 vs RUN, median 16 quy)
| ho | TAIL A1 | RUN | CVF A1 | J A1 | CVN A1 | max|d| perq |
| C0_SEED | 0.04076 | 0.04076 | 0.02189 | 0.7106 | 0.1148 | <=5e-7 |
| C0_EDGE | 0.01840 | 0.01840 | 0.01509 | 0.7486 | 0.0883 | <=5e-7 |
| E4_SEED | 0.01984 | 0.01984 | 0.00892 | 0.8541 | 0.0760 | <=5e-7 |
| E8_SEED | 0.01089 | 0.01089 | 0.00485 | 0.8933 | 0.0545 | <=5e-7 |
| E8_EDGE | 0.00905 | 0.00905 | 0.00519 | 0.9331 | 0.0341 | <=5e-7 |
| DET_EDGE | 0.02359 | 0.02359 | 0.01114 | 0.8233 | 0.0779 | <=5e-7 |
- TAIL/CVF: tu pred tho kout, 16 quy, ca 6 ho; float64 vs float32 (D11) khong doi so den 5 chu so.
- IC/dIC (16 quy, nhan label_oldbasket = LABEL mac dinh recipe, 0 NaN): E4 +0.00075 [+0.00047,+0.00108]; E8 +0.00090 [+0.00062,+0.00126]; DET -0.00053 [-0.00182,+0.00059] - trung RUN; bootstrap seed khac cho CI gan nhu nhau. E4/E8 > C0 o 16/16 quy; DET 7/16 (quy te nhat -0.0071).
- GATE: replay doc lap 8 lap (C0 s7,s123,s99; E8 g2,g3; E4 g5; DET e0,e2) x 16 quy: tap su kien (phut,symId) TRUNG KHOP 100% voi outB/gate cua RUN. J/CVN tinh lai bang code A1 tren 28 npz: khop RUN <=5e-7. CVN ddof=1. Khong co cap/quy nao hai tap rong (luat "rong=1" khong anh huong).
## 4. Do vung "E8 DAT"
(a) Bien: TAIL x0.267 (nguong 0.5); J +0.183 (nguong +0.10); CVN x0.475 (0.6); (c) x0.492 (0.6); dIC +0.0009 (>= -0.005). Theo quy E8 tot hon C0: TAIL 16/16 (<=0.5x: 14/16), J 16/16 (>= +0.10: 12/16), CVN 14/16. So C0 bang block seed khac (1001-1024) hoac 32 seed: TAIL E8/C0 = 0.264-0.293 -> (a) vung. E4 (a) mong: E4/C0 block khac 0.481-0.533.
(b) Dieu kien (c) KHONG CAN XUNG: E8_EDGE = 2 lap (e0,e2), C0_EDGE = 4 lap (e0..e3). E[sd mau] = c4(n)*sigma: c4(2)=0.798, c4(4)=0.921 => chuan hoa: 0.492 -> 0.568 (van <0.6, bien 0.03). So khop cap C0 e0/e2 (cung n=2, cung edge): TAIL C0 0.01187 => ti so 0.763 (> 0.6, se TRUOT); E8 tot hon theo quy 12/16, median ti so theo quy 0.70. => (c) dat theo chu luat nhung khong vung.
(c) Giam TAIL vs ly thuyet: ti so theo-quy (median) E8 0.369 ~ 1/sqrt8 = 0.354, E4 0.520 ~ 0.5. Con so 0.267 la ti so cua hai median (+ ~5% lech c4(4) vs c4(8): chuan hoa 0.280). Khong bat thuong; nhom roi doc lap; nhieu seed gan nhu thuan 1/sqrtK (chua thay san).
(d) Replay giu lock/printDone + equity r1-a3-a1 co dinh (0 phut full): bo qua phan hoi duong di (lenh khac -> lock khac -> DCA/U khac -> lan sang lenh sau). Huong: J replay LAC QUAN (uoc luong tren), CVN thap hon sim cho CA C0 va E8. Kiem nhay A1 (bo lock): J C0 0.71->0.87, E8 0.88->0.95 (J phu thuoc manh vao mat na lock, khong bat bien), nhung so su kien khac nhau tuyet doi gan bat bien (C0 61->68, E8 21->22) va ti le E8/C0 ~0.32-0.34 o ca hai che do => uu the TUONG DOI cua E8 vung, muc tuyet doi trong sim chua biet.
(e) So tuyet doi (median theo quy, ~160 su kien pass/quy): moi cap 2 lan train khac nhau (hieu doi xung) C0 = 61 su kien/quy (khoang 16-176), E8 = 21 (3-69), E4 = 29, C0_EDGE 39, E8_EDGE 11. Tuc ~38% vs ~13% so su kien pass/quy bi doi giua hai lan train.
(f) E4 CVN x0.662: tai tinh dung; theo quy median 0.637, chi 7/16 quy <= 0.6x. Khong loi tinh; E4 that su truot.
## 5. Loi
- BLOCKER: khong.
- MAJOR (thiet ke/dien giai, KHONG phai loi tinh cua RUN): (c) so sd 2 lap voi sd 4 lap khac edge-set; so khop n bang C0 e0/e2 -> 0.763 (truot). Khong duoc dien giai E8 "on dinh theo mep cat" la da chung minh; chi "dat theo luat".
- MINOR: (1) gio trong RUN_B.progress go tay sai (da dinh chinh; mtime code xac nhan thu tu). (2) J replay la chi so lac quan (fixed path) - can ghi ro trong RESULT. (3) TAIL dung ti so cua median, khong phai median ti so; nen bao ca hai. (4) dIC bootstrap theo quy coi 16 quy doc lap (bo qua tu tuong quan) - CI hoi hep, khong anh huong (d).
## 6. Y kien A1 (Y KIEN)
- Dung muc: E8 giam manh nhieu seed o duoi p15 va trong tap pass gate (TAIL, J, CVN, theo quy 14-16/16), IC khong giam. E4 o giua; DET khong giup (con te hon C0 o EDGE).
- Qua tay neu noi: "E8 on dinh voi mep cat" (c mong), "retrain E8 cho ~89% lenh giong nhau trong live" (J tu replay fixed-path, chua qua sim), hay E8 "tot hon" ve chat luong (dIC +0.0009 la khong kem, khong phai tot hon).
- S2: (1) dung pred.bin cho tung lap tu CHINH chuoi rep (E8 = mean float64 -> float32), kiem sha + ts khop + p15 cot dung; pool/ledger S1 WFO dung lai theo p15 cua lap (neu pool phu thuoc p15 thi phai dung lai, khong mang pool C0 seed 42). (2) 4 lap/ho: sd ROI tu 4 lap rat on (CV cua sd ~ 0.4); (e) x0.6 co the dat/truot do nhieu - nen bao them so khop theo quy va so lenh khac nhau tuyet doi tu sim. (3) Ghi ro C0-PROD 4 seed la seed nao (de nghi 4 seed dau, roi voi E8 nhom 2-4? C0 seed 42.. trung E8 nhom 1 - khong sao vi khac ho, nhung neu E8 S2 dung nhom 1 thi tranh so sanh cap). (4) Do them J muc lenh thuc (sim) de kiem uoc luong lac quan cua replay. (5) Neu trien khai, can buoc parity k2 cho moi fold (booster gop).
## 7. Khong kiem duoc
- Chua tai lap train (khong kernel/khong Oracle train) - dua vao booster sha parity 12/12 cua RUN (chi doc check.json/log). Khong kiem lai k1/k2 (chi doc log). Khong kiem hop le cong cu gate_offline (dung nhu da hop le M2). Khong co sim nen khong do duoc anh huong phan hoi duong di.
