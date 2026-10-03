# RESULT — SELECTOR_ABLATION: selector S1 LA LEVER cua LONG B0

Pre-reg `docs/prereg/PREREG_SELECTOR_ABLATION.md` (chot 5f357d3f; AMENDMENT A1 0595b855 truoc khi day R/L).
Driver `research/analysis/selector_ablation_driver.py`, sinh diem `research/analysis/selector_ablation_scores.py`,
B0REF `research/analysis/selector_ablation_b0ref.py`. JSON `docs/result/selector_ablation.json` (+ `.parity`).
Kernel = `tools/kaggle_sim.py` HEAD md5 8b60b00a (NOWRITE242) + SA_BLOCK; jar 7368be46 (sim-jar-gdv2); DEV <= 2025.

## Verdict (luat khai truoc §7)
**SELECTOR LA LEVER.** Calmar_MTM(ngay) B0 - mean(R42,R7,R13) = **+3,02 CI95 [+1,38; +6,74]** (k=1, khong inflate),
CAGR **+24,35pp [+13,33; +37,79]**, ROI nam B0 > mean R **4/4 nam** 2022-2025. Moi seed rieng le cung ngoai CI
(B0-R42 Calmar +2,97 [1,31; 6,81], B0-R7 +3,03 [1,38; 6,60], B0-R13 +3,05 [1,40; 7,20]).
**THANH KHOAN KHONG THAY DUOC SELECTOR:** L - B0 Calmar -2,46 [-5,55; -0,91], CAGR -17,9pp [-27,6; -9,7].
L - mean(R): Calmar +0,56 [-0,28; +2,47], CAGR +6,5pp [-3,7; +17,6] (huong tot hon random, CI chua 0).

## Parity
- P0 (`selab-p0`): n 2517, equity 131908, jar 7368be46, bins sha 407e2aba, funding md5 8e57d900 (= bundle) — khop.
  md5 printDone **ff3ce513** != 650c386f: 5 o khac chuoi Float.toString (volume x4, quantity x1), **0 o khac gia tri** float32.
- **B0REF** (B0 thuan, khong SA block, cung dot) md5 **ff3ce513 == P0** => anh Kaggle (JDK) doi giua 01:08 va 07:13;
  duong override bins/funding **byte-identical** voi B0 tren anh hien tai. Cong parity (A1) PASS.
- Moi arm: bins_sha khop ban Oracle, funding md5 rieng (R42 710ec5c9, R7 79e26aa2, R13 34e92236, L d0319b87), mapper 863.
- Sanity bins: cung (ts,sym)/multiset/NaN 5/5; 3 seed khac nhau 99,6%; Spearman trong tick vs P0: R ~0,000; L 0,17-0,41;
  L causal (gio cuoi ket thuc <= ts-15'), tai tinh 30/30 khop.

## Bang (toan ky 2021-07..2025-12; Calmar_boot = CAGR/|maxDD MTM ngay|, Calmar_ph = CAGR/|maxDD MTM phut|)
| arm | n | SumPnL | equity | CAGR | ddMTM ph | Calmar_ph | Calmar_boot | UW ngay | win% | ROI/leg PREDICT mean/med | SL% | top5 ep | leg mo TB | overlap B0 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B0 (P0) | 2517 | 96 909 | 131 908 | 34,31 | -17,68 | 1,94 | 3,43 | 87 | 85,9 | 3,69 / 5,50 | 14,3 | 36,6 | 3,9 | 100 |
| R42 | 2870 | 20 600 | 55 600 | 10,84 | -30,52 | 0,36 | 0,45 | 736 | 80,1 | 2,74 / 5,49 | 21,5 | 64,4 | 5,6 | 2,1 |
| R7 | 3016 | 18 667 | 53 666 | 9,97 | -31,25 | 0,32 | 0,40 | 812 | 80,0 | 2,74 / 5,49 | 21,7 | 78,0 | 5,8 | 2,0 |
| R13 | 2911 | 16 701 | 51 700 | 9,06 | -31,90 | 0,28 | 0,38 | 735 | 79,3 | 2,72 / 5,49 | 23,3 | 62,4 | 5,8 | 2,2 |
| mean R (sd) | 2932 (75) | 18 656 (1 950) | 53 655 | 9,96 (0,89) | -31,2 (0,7) | 0,32 (0,04) | 0,41 (0,04) | 761 | 79,8 | 2,73 | 22,2 | 68,2 | 5,7 | 2,1 |
| L (thanh khoan) | 2440 | 34 339 | 69 338 | 16,41 | -21,60 | 0,76 | 0,97 | 487 | 76,5 | 1,70 / 5,00 | 26,0 | 50,7 | 5,2 | 10,1 |
Seed-dispersion R nho (sd Calmar 0,04, CAGR 0,9pp) so voi khoang cach B0-R (24pp) => ket qua khong phu thuoc seed.

## Theo nam (ROI nam equity MTM, %; n | SumPnL)
| nam | B0 | R42 | R7 | R13 | L | B0 - mean R |
|---|---|---|---|---|---|---|
| 2021H2 | 18,5 (434 / 6,5k) | 8,8 | 14,5 | 10,8 | 7,5 | +7,1 |
| 2022 | 11,1 (423 / 4,6k) | -13,7 (-5,2k) | -17,2 (-6,9k) | -16,4 (-6,4k) | -4,0 | **+26,9** |
| 2023 | 54,1 (527 / 24,9k) | 22,4 | 19,4 | 23,5 | 37,5 | **+32,4** |
| 2024 | 43,4 (599 / 30,8k) | 35,7 | 36,4 | 32,8 | 24,7 | **+8,4** |
| 2025 | 29,5 (534 / 30,1k) | 1,9 | -0,6 | -2,8 | 12,0 | **+30,0** |
maxDD MTM phut/nam B0 -11,6/-17,7/-4,3/-10,7/-15,6 vs R ~-15,5/-23,6/-7,2/-12,7/-31,2. L - mean R theo nam: +11,8/+15,7/-10,3/+12,5.

## Co che (doc tu lenh, chi thong tin)
- Overlap tap lenh (sym|phut vao) voi B0: R 2,0-2,2% (Jaccard ~1%), L 10,1% => ablation that su doi coin. Theo level, % lenh
  B0 co trong arm: PREDICT 2,0% (R) / 9,5% (L); **BIG_DOWN 1,2-3,6% (R) / 13,7% (L)**.
- **Sua §8 pre-reg:** BIG_DOWN KHONG doc lap voi selector — thoi diem BIG_DOWN la tin hieu thi truong (248 leg o moi arm),
  nhung 2 coin cua no chon qua `getTopSymbolArray(..., predict2Symbol)` tu CHINH diem selector. Vay "selector" do o day =
  chon K16 PREDICT + chon coin BIG_DOWN (+ DCA_LEVEL1 di theo cum). Uoc theo level (ROI/leg mean, khong phu thuoc size):
  PREDICT B0 3,69 vs R 2,73 (**+0,96pp/leg**), BIG_DOWN 4,82 vs R 3,93 (+0,89pp); SumPnL PREDICT 77,0k vs R ~14,1k,
  BIG_DOWN 11,7k vs ~3,4k, DCA_LEVEL1 8,3k vs ~1,1k.
- Gate: R qua cong NHIEU hon (pass 3149-3861 vs 2223, seen ~ngang) vi coin ngau nhien hiem khi "dang giu" => nhieu ung vien
  toi cong hon; n R +16%. Day la mot phan hanh vi selector (B0 tap trung vao cung coin), khong phai loi sim.
- Rui ro: R win% -6pp (CI ghep cap block-72h loai 0 ca 3 seed, vd R42 [-9,9; -1,7]), SL% +7..9pp, so leg mo dong thoi 5,7 vs 3,9, UW 736-812
  ngay vs 87. Median ROI/leg = nhau (5,5 — tran TP), chenh nam o DUOI LO.
- Ky vong khai truoc: SumPnL B0 - mean R du kien +30..40k; thuc te **+78,3k** (lon hon, mot phan do compounding size theo equity:
  margin TB B0 ~1000 vs R ~360). dROI/leg PREDICT +0,96pp cung bac voi placebo P3 cu +1,56pp/leg. Khong kich hoat dong
  "lever qua rui ro, khong qua ROI" (SumPnL >> +10k), nhung luu y chenh ROI/leg nho; phan lon chenh equity den tu duoi lo + DD.

## Hoa giai voi AUDIT_LONG_LEVERS (Spearman +0,014 / trong tick -0,021)
Audit do tuong quan symbolPred voi ket qua TRONG TAP LENH DA CHON (top-16 + qua gate) — range restriction: trong nhom da loc,
diem gan nhu khong xep hang them duoc. Ablation do gia tri CUA BUOC LOC (universe ~110-510 coin co pred moi tick -> 16). Hai so lieu khong mau
thuan: selector co gia tri lon o tang loc thoat, gan 0 o tang xep hang min trong top-16.

## Han che
1) Sim path-dependence (coin dang giu, CONC_CAP) => R khong giu nguyen so slot (n +16%); Calmar la thuoc khong phu thuoc quy mo.
2) R rut tu TOAN universe co pred tai tick (gom coin moi niem yet / kem thanh khoan) — dung la tap selector duoc phep chon trong
   B0, nhung "random trong top-50" se cho moc thap hon de ket luan ve xep hang min (CHUA chay).
3) L dung quoteVol Aerospike kline_1m_opt (cung nguon ticker bundle), khong doc truc tiep tu ticker Kaggle.
4) Mot DEV duy nhat (2021-07..2025-12), 3 seed; CI block-10d tren duong MTM ngay ghep cap; khong co holdout 2026.
5) Anh Kaggle doi JDK trong ngay: so md5 B0 cu (650c386f) khong con tai lap byte; tham chieu moi = ff3ce513 (B0REF).

## He qua cho huong retrain
- Selector LA lever that: bo selector (=> random) mat ~24pp CAGR, Calmar 3,4 -> 0,4; thanh khoan chi gianh lai ~1/4 khoang cach.
  => huong "selector tot hon" KHONG vo ich; dang retrain tren du lieu sach / label da horizon.
- Nhung gia tri nam o tang loc universe->K (tranh duoi lo, SL% thap, win% cao), khong o xep hang trong top-16 (audit IC ~0).
  => muc tieu retrain/eval nen la: precision tranh lenh lo nang / SL o bien K (vd rank-IC tren TOAN universe, recall cua
  "coin xau" ngoai top-K), va moi model moi phai cham END-TO-END bang chinh ablation nay (B0 vs R lam san), khong chi IC.
- Buoc tiep de xuat (chua pre-reg): R50 = hoan vi CHI trong top-50 moi tick => tach "loc thoat" vs "xep hang min"; neu R50 ~ B0
  thi retrain chi can giu chat luong loc, khong can toi uu thu tu top-16.
