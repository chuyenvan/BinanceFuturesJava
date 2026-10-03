# RESULT — SELECTOR_ABLATION_R50: XEP HANG MIN trong top-50 CO GIA TRI (khong chi loc tho)

Pre-reg `docs/prereg/PREREG_SELECTOR_ABLATION_R50.md` (chot e7fe24bd, TRUOC khi day kernel; khong amendment).
Driver `research/analysis/selector_ablation_r50_driver.py`, sinh bins `research/analysis/selector_ablation_topm.py`.
JSON `docs/result/selector_ablation_r50.json` (+ `.parity`). Kernel = `tools/kaggle_sim.py` HEAD md5 8b60b00a (NOWRITE242)
+ SA_BLOCK vong truoc (helper topm); jar 7368be46 (sim-jar-gdv2); DEV <= 2025. Tiep noi SELECTOR_ABLATION (33d8fc17).

## Verdict (luat khai truoc §7, k = 2, CI inflate 1,18)
**R50: XEP HANG MIN CO GIA TRI.** Calmar_MTM(ngay) B0 - mean(R50s42, R50s7) = **+2,38 CI [+0,47; +5,17]**,
CAGR **+14,7pp [+5,5; +24,9]**; ca 2 seed rieng le ngoai CI (s42 +2,38 [0,55; 5,57], s7 +2,37 [0,34; 4,81]).
**R100: XEP HANG MIN CO GIA TRI.** B0 - mean R100 = +2,64 [+0,71; +6,03], CAGR +19,1pp [+8,2; +31,8].
Ket hop (§7): "xep hang min co gia tri; huong = ranking (top-50 -> 16)". Nam (thong tin): B0 > mean R50 o 4/4 nam
2022-2025, B0 > mean R100 4/4. Gia thuyet "gia tri = loc tho, thu tu trong top-50 khong quan trong" (de xuat cuoi
RESULT vong truoc) **BI BAC**: xao thu tu trong top-50 mat ~60% khoang cach CAGR B0 - R16.

## Parity
- B0REF2 (B0 thuan, cung dot): n 2517, equity 131908, jar 7368be46, mapper 863, md5 printDone **ff3ce513** == selab-p0
  (cung anh Kaggle vong truoc => R16 vong truoc dung lai hop le); vs de-p1: 5 o khac chuoi (volume x4, quantity x1),
  **0 o khac gia tri** float32; vs selab-p0: 0 o khac. Cong parity PASS.
- 4 arm R: jar/mapper OK, bins sha trong Kaggle == Oracle (4762a2ec/dff2cefe/35cfbac9/a2d5c63e), src sha 407e2aba;
  funding md5 89ca50dd/0f9359af/7f9f253f/54d49b4b. Sanity bins (truoc commit): xem pre-reg §4 (ok = True).

## Bang toan ky (2021-07..2025-12; Calmar_boot = CAGR/|maxDD MTM ngay| = thuoc luat; Calmar_ph = maxDD MTM phut)
| arm | n | SumPnL | equity | CAGR | ddMTM ph | Calmar_ph | Calmar_boot | UW ngay | win% | ROI/leg PREDICT | SL% | top5 ep | leg mo TB | overlap B0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 (B0REF2) | 2517 | 96 909 | 131 908 | 34,31 | -17,68 | 1,94 | **3,43** | 87 | 85,9 | 3,69 | 14,3 | 36,6 | 3,9 | 100 |
| R50s42 | 2669 | 39 974 | 74 973 | 18,45 | -20,45 | 0,90 | 1,04 | 483 | 83,0 | 3,16 | 17,0 | 44,2 | 4,5 | 11,8 |
| R50s7 | 2656 | 46 700 | 81 699 | 20,74 | -21,25 | 0,98 | 1,05 | 539 | 82,9 | 3,25 | 16,8 | 45,6 | 4,6 | 10,0 |
| **mean R50** (sd) | 2663 | 43 337 (4 756) | 78 336 | 19,60 (1,6) | -20,85 | 0,94 | **1,05** (0,01) | 511 | 82,9 | 3,21 | 16,9 | 44,9 | 4,5 | 10,9 |
| R100s42 | 2871 | 28 344 | 63 344 | 14,10 | -29,14 | 0,48 | 0,68 | 710 | 82,0 | 2,93 | 19,1 | 44,6 | 5,2 | 5,2 |
| R100s7 | 2845 | 34 253 | 69 252 | 16,38 | -24,21 | 0,68 | 0,88 | 705 | 81,3 | 2,90 | 19,4 | 45,6 | 5,2 | 4,5 |
| **mean R100** (sd) | 2858 | 31 299 (4 178) | 66 298 | 15,24 (1,6) | -26,68 | 0,58 | **0,78** (0,14) | 707 | 81,6 | 2,92 | 19,2 | 45,1 | 5,2 | 4,9 |
| R16 vong truoc (mean R42/R7/R13) | 2932 | 18 656 | 53 655 | 9,96 | -31,22 | 0,32 | **0,41** | 761 | 79,8 | 2,73 | 22,2 | 68,2 | 5,7 | 2,1 |

## Tuong phan (paired block-10d, NREP 2000, seed 20260905; CI inflate 1,18 [raw])
| tuong phan | dCalmar_boot | dCAGR pp | dmaxDD ngay pp | dSharpe |
|---|---|---|---|---|
| **B0 - R50** (chinh 1) | **+2,38 [+0,47; +5,17]** ([0,76; 4,74]) | +14,71 [+5,46; +24,87] | +8,68 [-1,53; +10,87] | +0,86 [0,25; 1,45] |
| **B0 - R100** (chinh 2) | **+2,64 [+0,71; +6,03]** ([1,01; 5,51]) | +19,07 [+8,17; +31,79] | +9,61 [-2,06; +10,98] | +1,13 [0,46; 1,80] |
| R100 - R50 | -0,27 [-1,37; +0,14] | -4,36 [-10,30; +0,32] (raw [-9,39; -0,39]) | -0,93 [-3,91; +2,70] | -0,27 [-0,64; 0,05] |
| R50 - R16 | +0,64 [+0,23; +3,24] | +9,64 [+2,40; +18,86] | +5,69 [-0,55; +15,45] | +0,68 [0,16; 1,36] |
| R100 - R16 | +0,37 [+0,16; +2,18] | +5,28 [+1,02; +10,05] | +4,76 [-0,24; +13,99] | +0,41 [0,09; 0,80] |
| B0 - R16 (tai tinh, raw = vong truoc) | +3,02 [+1,09; +7,41] ([1,38; 6,74]) | +24,35 [+11,34; +40,21] | +14,37 | +1,54 |
Phan khoang cach B0 - R16 MAT khi xao trong top-M (frac, CI percentile): **R50 Calmar 0,79 [0,43; 0,87], CAGR 0,60
[0,40; 0,80]**; R100 Calmar 0,88 [0,62; 0,92], CAGR 0,78 [0,66; 0,91].

## Duong cong theo M (K16 cua B0 -> top-50 -> top-100 -> toan universe)
| muc xao thu tu | Calmar_boot | CAGR | Calmar_ph | UW ngay | SL% | ROI/leg PREDICT |
|---|---|---|---|---|---|---|
| khong xao (B0, selector chon top-16) | 3,43 | 34,3 | 1,94 | 87 | 14,3 | 3,69 |
| xao trong top-50 (R50) | 1,05 | 19,6 | 0,94 | 511 | 16,9 | 3,21 |
| xao trong top-100 (R100) | 0,78 | 15,2 | 0,58 | 707 | 19,2 | 2,92 |
| xao toan universe (R16, ~120-430 coin) | 0,41 | 10,0 | 0,32 | 761 | 22,2 | 2,73 |
Don dieu: Calmar 3,43 -> 1,05 -> 0,78 -> 0,41; CAGR 34,3 -> 19,6 -> 15,2 -> 10,0. Chia khoang cach CAGR B0 - R16
(24,4pp): **top-50 -> 16 (xep hang min) ~14,7pp (60%)**, top-100 -> 50 ~4,4pp (18%, CI chua 0 sau inflate),
universe -> 100 ~5,3pp (22%). Theo Calmar, buoc 50 -> 16 chiem ~79%. R100 - R50 khong tach duoc khoi 0 (CI inflate).

## Theo nam (ROI nam equity MTM, %; B0 - mean arm)
| nam | B0 | mean R50 | mean R100 | mean R16 | B0-R50 | B0-R100 | B0-R16 | frac R50 (=(B0-R50)/(B0-R16)) | M50/universe |
|---|---|---|---|---|---|---|---|---|---|
| 2021H2 | 18,5 | 15,9 | 14,7 | 11,4 | +2,6 | +3,8 | +7,2 | 0,36 | 41% |
| 2022 | 11,1 | -7,2 | -11,3 | -15,8 | **+18,3** | +22,4 | +26,9 | 0,68 | 37% |
| 2023 | 54,1 | 27,2 | 23,7 | 21,8 | **+27,0** | +30,5 | +32,4 | 0,83 | 27% |
| 2024 | 43,4 | 37,0 | 36,6 | 35,0 | +6,4 | +6,8 | +8,4 | 0,76 | 19% |
| 2025 | 29,5 | 19,5 | 10,3 | -0,5 | +10,0 | +19,2 | +30,0 | **0,33** | 12% |
maxDD MTM phut/nam: B0 -11,6/-17,7/-4,3/-10,7/-15,6; R50 ~-15,3/-20,4/-6,1/-11,5/-20,3; R100 ~-14,8/-20,6/-5,8/-11,3/-26,7.
Quan sat (post-hoc, thong tin, KHONG vao luat): 2025 (universe ~434, top-50 = 12% universe) R50 chi mat 1/3 khoang cach
— o do loc thoat universe -> 50 da mang 2/3 gia tri; 2022-2023 (universe 134-182, top-50 = 27-37%) xep hang trong top-50
mang 68-83%. => gia tri nam o **do sau dau bang** (~top 5-12% universe = 16 coin), khong o moc M tuyet doi; M = 50 la
"loc thoat" yeu khi universe nho. Chua kiem bang thuoc tien dang ky (chi 1 DEV, 5 nam).

## Co che (doc tu lenh, thong tin)
- Overlap tap lenh (sym|phut vao) voi B0: R50 10,9% (PREDICT 11,2/9,9%, BIG_DOWN 12,1/6,5%), R100 4,9%, R16 2,1% =>
  ablation that su doi coin; tap top-M giu nguyen nhung top-16 la tap con ngau nhien.
- Theo level (ROI/leg mean, khong phu thuoc size): PREDICT B0 3,69 | R50 3,16/3,25 | R100 2,93/2,90 | R16 2,73;
  BIG_DOWN B0 4,82 | R50 3,99/4,47 | R100 4,37/4,43 | R16 ~3,93. SumPnL PREDICT 77,0k | R50 30,7/35,9k | R100 20,7/25,6k
  | R16 ~14,1k (chenh SumPnL khuech dai boi compounding: margin PREDICT TB B0 999 vs R50 ~540, R100 ~420, R16 ~356).
- Median ROI/leg = 5,5 o moi arm (tran TP) => chenh nam o DUOI LO va DD: SL% 14,3 -> 16,9 -> 19,2 -> 22,2; win%
  85,9 -> 82,9 -> 81,6 -> 79,8; UW 87 -> 511 -> 707 -> 761 ngay; leg mo dong thoi 3,9 -> 4,5 -> 5,2 -> 5,7.
- Rate CI ghep cap block-72h (thong tin): R50 win% -2,9pp [-6,3; +0,3] / [-6,1; +0,0], SL% +2,7 [-0,6; +6,2] / +2,5
  [-0,4; +5,6] — o muc leg CHUA tach khoi 0 tung seed; R100s42 SL% +4,7 [+0,8; +9,0]. Tin hieu o muc danh muc (Calmar/
  DD/UW) manh hon muc leg — tich luy qua thoi gian + kich thuoc.
- Gate: pass B0 2223, R50 2471/2591, R100 2972/2867, R16 3149-3861 — coin ngau nhien it "dang giu" => nhieu ung vien toi
  cong hon; n R50 +6%, R100 +14%. Hanh vi selector (B0 tap trung vao cung coin), khong phai loi sim.
- Seed-dispersion: R50 rat nho (Calmar_boot sd 0,008, CAGR sd 1,6pp); R100 lon hon (sd 0,14).

## Hoa giai voi AUDIT_LONG_LEVERS & RESULT vong truoc
- Audit (Spearman symbolPred vs ket qua TRONG tap da chon top-16 + gate ~0) va R50 >> khong mau thuan: audit do thu tu
  BEN TRONG 16 coin da chon; R50 do gia tri cua CAT 16 tu 50 (hang 1-16 vs 17-50). Dien giai: diem phan biet duoc
  "dau bang" voi phan con lai cua top-50, nhung khong xep hang them duoc trong 16 coin dau (range restriction).
- RESULT vong truoc ket: "gia tri o tang loc universe -> K, khong o xep hang trong top-16" — van dung, nhung de xuat
  "neu R50 ~ B0 thi retrain chi can giu chat luong loc" bi BAC: R50 << B0. Tang quan trong nhat la ranh gioi top-16
  trong top-50 (~60% CAGR, ~79% Calmar), phan loc universe -> 50 chiem ~40% CAGR.

## He qua cho LABEL_FIRSTHIT / retrain selector (goi y, chua pre-reg)
- Nhan/feature phai nham **chat luong DAU BANG**: phan biet hang 1-16 voi hang 17-50 (va 51-100) trong cung tick —
  khong phai IC trong top-16 (~0, khong co gia tri de toi uu), cung khong chi "tranh duoi" universe -> 50.
- Thuoc eval offline de xuat (truoc khi chay sim): (a) lift ket qua top-16 vs hang 17-50 cua chinh model trong tick
  (ROI/leg first-hit, SL-rate, ty le leg lo nang); (b) precision@16 cua "leg xau" (SL/first-hit thua) trong top-50;
  (c) rank-IC tren top-100 (khong toan universe, khong trong top-16). Loss nen la ranking/listwise co trong so dau bang
  (vd LambdaRank/NDCG@16 trong tick) hon la pointwise tren toan universe.
- Vi do sau dau bang theo % universe (2025: 16/434 ~4%) quan trong hon M tuyet doi, nhan nen chuan hoa theo hang
  trong tick (quantile), va eval tach nam (2022-2023 universe nho vs 2025 universe lon).
- Moi model moi phai cham END-TO-END bang ablation nay (B0 vs R50 vs R16 lam san, cung bootstrap) — IC khong du.

## Han che
1) Mot DEV (2021-07..2025-12), 2 seed/M; R50 & R100 dung chung day ngau nhien (common random numbers) => R100 - R50
   khong doc lap; CI rong (B0 - R50 Calmar [0,47; 5,17]) — huong chac chan, do lon khong chinh xac.
2) Path-dependence sim (coin dang giu, CONC_CAP) => n R +6..14%; Calmar khong phu thuoc quy mo nhung SumPnL bi compounding.
3) R16 tu dot kernel vong truoc (cung anh Kaggle, md5 B0REF2 == selab-p0 ff3ce513) — khong cung dot nhung cung anh.
4) BIG_DOWN cung chon coin qua diem => "xep hang min" do o day gom ca chon 2 coin BIG_DOWN (+ DCA_LEVEL1 theo cum);
   PREDICT van chiem phan lon chenh (SumPnL PREDICT 77,0k vs ~33k).
5) Quan sat "do sau theo % universe" la post-hoc, chua kiem; khong co holdout 2026.
