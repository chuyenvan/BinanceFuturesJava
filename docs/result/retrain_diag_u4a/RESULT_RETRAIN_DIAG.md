# RESULT_RETRAIN_DIAG - U4a chan doan tung model (PREREG_RETRAIN_DIAG 436977c1, muc 8 MASTER duyet)
HOLDOUT_UNSEAL_2026_1121 (U4a) + OWNER_DECISION_PILOT_1121 c3a9f01b. Agent, 2026-11-21. Khong du lieu >= 2026-10-01 (nhan: ts + horizon <= S4).
Muc "CO CHE" duoc viet + sha256 ghi vao RETRAIN_DIAG_RUN.progress TRUOC khi tai / mo bat ky output PnL nao cua lane P / S / M.

## CO CHE (khong PnL)
Artefact: out/diag/DCAL.json (rt_dcal.py), out/diag/DGATE_LN.json (rt_dgate.py), out/diag/RULER_v2_result.json (kernel rt-diag-ruler v2,
code ds rt-diag-code; v1 co loi dau score S1 chi o phan D-src perm, phan ruler chinh v1 == v2 byte).

### D-cal (p15 T1 = rt-chain-n26 pred26 c1b00ba9 vs live fold_20 = Lane L pred 64f66a15; cung file pred sim dung; Q1-Q2 la IN-SAMPLE cua T1)
| cua so | so phut | p15 q99,99 T1 / live | ti so | p15 q99,995 ti so | max T1 / live | r-proxy q99,99 ti so | r q99,995 ti so |
|---|---|---|---|---|---|---|---|
| 2026Q1 | 130 560 | 0,04050 / 0,04207 | 0,963 | 0,753 | 0,329 / 0,299 | 0,927 | 0,792 |
| 2026Q2 (DEV cua B1) | 130 080 | 0,02621 / 0,02677 | **0,979** | 0,956 | 0,0504 / 0,0356 | 1,037 | 1,192 |
| 90 ngay truoc S3 | 129 600 | 0,02625 / 0,02679 | 0,980 | 0,955 | 0,0504 / 0,0356 | 1,037 | 1,191 |
| 2026Q3 (OOS) | 132 480 | 0,03253 / 0,02729 | 1,192 | 1,509 | 0,145 / 0,092 | 1,265 | 1,571 |
r-proxy = p15 / (max(0.26787, sp_best/0.15*1.28760) * 1.55), sp_best = 1 - max p0 cua tick 15' (ffill) - MO TA, khong phai bo dem gate that
(gate that tinh r tren tung ung vien). So phut r_T1 > q99,995(r_live) trong cung cua so: Q2 11 vs 7; Q3 27 vs 7.
Doc: tren DEV Q2 (in-sample T1) duoi p15 T1 KHONG nang hon live (0,98); duoi nang len chi o Q3 OOS (1,19 p15 / 1,27 r o q99,99; 1,5 o q99,995).

### D-gate (log sim, chi dong GATE-RATIO; pass / seen)
| lane | 2025Q4 | 2026Q1 | 2026Q2 | 2026Q3 | rho Q3 |
|---|---|---|---|---|---|
| LLL (a1 = s123 cho 2026) | 275 / 2 887 018 (a1), 275 / 2 890 695 (s123) | 103 / ~2 938k | 122 / 3 011 221 | 94 / 3 041 795 | 3,09e-5 |
| NNN (a1 = s123 cho 2026) | = L | = L | = L | 142 / 2 912 910 | 4,87e-5 |
| P, S, M | (bo sung o muc CO CHE-2 sau khi kernel xong; chi dong GATE-RATIO) | | | | |
Q3 hai seed cho so dem gate TRUNG nhau (seed chi doi pred DEV < 2026) -> ve gate, 2 seed ~ 1 mau.

### D-ruler (Tang A, nhan Vision Q3; hieu T1 - live ghep cap theo tick; CI bootstrap khoi tuan 2000, seed 20261121)
| model | nhan | chi so | live | T1 | hieu | CI80 | CI95 | ticks / tuan |
|---|---|---|---|---|---|---|---|---|
| p15 | label_oldbasket (1m, ts < S4-1d) | IC Spearman | 0,5089 | 0,5238 | +0,0149 | [+0,0074, +0,0205] | [+0,0044, +0,0240] | 131 040 phut |
| net015 (RAW 0701) | retEnd_4h > 0,015 | AUC/tick | 0,6935 | 0,6957 | +0,0022 | [+0,0016, +0,0028] | [+0,0014, +0,0032] | 8 788 / 14 |
| net015 | " | lift@8 | 0,2230 | 0,2295 | +0,0065 | [+0,0044, +0,0089] | [+0,0032, +0,0100] | |
| net015 | retEnd_4h | rank-IC | -0,0505 | -0,0505 | -0,0001 | [-0,0012, +0,0011] | | |
| S1 (bins A3 0701: L vs lane S, cung multiset) | g1lite 72h / yb = maxFav_72h >= 0,07 | rank-IC | 0,1731 | 0,1749 | +0,0018 | [-0,0009, +0,0043] | [-0,0023, +0,0056] | 8 516 / 13 |
| S1 | " | lift@8 | 0,3602 | 0,3620 | +0,0019 | [-0,0070, +0,0109] | [-0,0107, +0,0158] | |
| S1 | " | precision@8 | 0,7445 | 0,7464 | +0,0019 | (= lift) | | |
| S1 | " | AUC/tick | 0,6630 | 0,6665 | +0,0034 | [+0,0020, +0,0049] | | |
| S1 (phu) | retEnd_4h > 0,015 | lift@8 | 0,1919 | 0,1966 | +0,0047 | [+0,0003, +0,0089] | [-0,0019, +0,0115] | 8 788 / 14 |
p15 tail (mean label | p15 >= q) - mean: q0,99 live 0,00618 / T1 0,00635; q0,999 live 0,01614 / T1 0,01631.
Loai 8 id map 863 co > 1 symbol (843-850). Diem cao = tot (bins p0; S1 order theo A3).

### D-src
(a) lech feature DEV vs Vision (da do, rt-splice K3): feat_v2 doan chong lan 14 118 dong: vol_7d / dd_7d / rk_dd_7d / hrs_since_high_7d / ret_3d /
rk_ret_3d 99,79 % o bang; ret_14d 99,28 %; ls_global 90,14 %; **rk_oi_delta24h 0,21 %** (99,8 % o khac). Gate 33 cot DEV vs Vision 2026H1: 49,3 % o
bang (trung binh cot); Tool1 26,2 %. S1 T1 hoc 45,1 % dong train ts >= S0 bang feature Vision.
(b) permutation trong moi gio qua coin (Q3, g1lite, 4 924 691 dong, cung hoan vi cho 2 model): giam rank-IC / lift@8 khi xao tron nhom:
| nhom | S1 live dIC | S1 live dlift8 | S1 T1 dIC | S1 T1 dlift8 |
|---|---|---|---|---|
| rk_oi_delta24h | -0,0005 | -0,0001 | -0,0007 | +0,0040 |
| rk_dd_7d + rk_ret_3d | +0,0138 | +0,0079 | +0,0130 | -0,0034 |
| ls_global | -0,0002 | +0,0085 | +0,0007 | +0,0041 |
| 5 cot khong-rk con lai | +0,1138 | +0,2226 | +0,1265 | +0,2441 |
(goc: live IC 0,1730 lift8 0,3575; T1 IC 0,1780 lift8 0,3634 tren universe co diem S1 - khong demote A1.) Doc: cot lech nguon rk_oi_delta24h
gan nhu KHONG dong gop thu tu S1 o Q3 cho ca hai model.

### Ap dieu kien CO CHE (P5 da xac nhan)
- B1 [hieu chuan gate]: dieu kien 1 = ti so q99,99 p15 T1 / live tren DEV Q2 >= 1,2 hoac <= 0,83 -> **0,979 -> SAI**. Vi B1 = (1) VA (2), B1
  **KHONG kich hoat** bat ke D-gate lane P. (Mo ta, khong doi ket luan: Q3 OOS 1,192 sat nguong; r-proxy 1,265.)
- B2 [lech nguon S1]: dieu kien 1 = S1 T1 kem live (lift@8 thap hon, CI80 khong chua 0) -> hieu +0,0019, CI80 [-0,0070, +0,0109] chua 0, khong
  kem -> **SAI**; dieu kien 2 (rk_* lech > 50 %) DUNG cho rk_oi_delta24h (rk_dd_7d / rk_ret_3d thi khong). B2 **KHONG kich hoat**.
- B3 [net015]: T1 kem live (AUC thap hon, CI80 khong chua 0)? -> hieu AUC +0,0022, CI80 [+0,0016, +0,0028] (T1 TOT hon) -> **SAI** ->
  theo B3 "nguoc lai lam moi".
- Ket luan co che (truoc PnL lane): khong model T1 nao kem model live tren thuoc Tang A (p15 IC +0,015, net015 AUC +0,002, S1 lift@8 +0,002 ns);
  thay doi co che lon nhat la thang duoi p15 o Q3 OOS (pass gate Q3 +51 %), nhung quy tac B1 (do tren DEV Q2) khong bat duoc vi duoi T1 chi nang
  len ngoai mau. Mau thuan van ban cay: B3 "nguoc lai lam moi" vs B5 "khong nhanh nao kich hoat -> giu ca 3 model live" -> de MASTER (xem muc QUYET
  DINH sau STOP-D2); agent khong tu chon.

### CO CHE-2: D-gate lane P / S / M (chi dong GATE-RATIO cua log sim; viet TRUOC khi cham PnL lane)
Kiem chung khong-PnL rt_lchk.py (fork rt_nchk): 6/6 PASS (jar cc0f9d11, mapper / funding snapshot, bins26 = DATA26 lane, pred n 393 120 NaN 0,
market / profile / overrides / bins DEV == L, printDone end < 2026-07-01 TRUNG Lane L theo thu tu (P 3 866 dong a1), Update <= 06-30 trung).
| lane | 2026Q2 | 2026Q3 pass / seen | rho Q3 | pass / pass_L - 1 |
|---|---|---|---|---|
| LLL | 122 / 3 011 221 | 94 / 3 041 795 | 3,09e-5 | 0 |
| P (p15 T1) | = L | 127 / 2 962 350 | 4,29e-5 | **+0,35** |
| S (S1 T1) | = L | 93 / 3 035 472 | 3,06e-5 | -0,01 |
| M (net015 T1) | = L | 108 / 2 994 359 | 3,61e-5 | +0,15 |
| NNN | = L | 142 / 2 912 910 | 4,87e-5 | +0,51 |
(a1 == s123 cho moi so dem 2026.) B1 dieu kien 2 (|pass_P / pass_L - 1| >= 0,25) DUNG (0,35) nhung dieu kien 1 SAI (0,979) -> B1 van KHONG kich hoat.
Doc co che: thang p15 T1 giai thich phan lon tang pass (+33 / +48), net015 T1 (qua factor sp) them +14; S1 khong doi gate.

## LANE (PnL MO TA; cham SAU khi muc CO CHE / CO CHE-2 da ghi + sha)
Cong cu: rt_lane.py (du lieu = to hop artefact da co, hard link + sha), rt_lsim.py (fork rt_nsim, RT_LANE), rt_lchk.py (12/12 PASS),
rt_score_lane.py (dinh nghia SCORE_DEFS_L5 qua rt_score_n.lane(); selftest L:=L -> delta 0, ROI L 3,1216 %). out/score/score_lanes_U4a.json
sha256 b68867510f8b0c60e0e57df56bc2e5aaa618318d6ab97e62cc7653472be12ea6. Seed a1, s123 (P1); hai seed lech <= 0,0006 pp moi lane.
Lane chu hoa = model T1: P = p15, S = S1, M = net015.
| lane | ROI D5 Q3 % | SigmaPnL Q3 | n lenh (start Q3) | chung voi L | PnL chung | PnL chi-o-lane | PnL lenh L bi mat | maxDD Q3 | pass gate Q3 |
|---|---|---|---|---|---|---|---|---|---|
| LLL | +3,122 | +5 039 | 110 | 110 | +7 696 | 0 | 0 | -1,48 % | 94 |
| P | -0,386 | -624 | 145 | 56 | +3 717 | -1 684 | +3 853 | -2,15 % | 127 |
| S | +2,630 | +4 246 | 110 | 79 | +4 100 | +2 803 | +3 639 | -1,73 % | 93 |
| M | +0,757 | +1 223 | 124 | 79 | +6 017 | -2 137 | +1 387 | -1,78 % | 108 |
| PS | -0,889 | -1 435 | 147 | 46 | +2 385 | -1 162 | +5 384 | -2,92 % | 128 |
| PM | **-9,493** | -15 324 | 164 | 34 | +2 811 | -15 478 | +4 063 | -9,97 % | 142 |
| SM | +0,690 | +1 114 | 125 | 65 | +6 840 | -3 069 | +789 | -1,76 % | 108 |
| NNN | -6,443 | -10 400 | 164 | 35 | +3 681 | -11 424 | +3 587 | -7,45 % | 142 |
Theo thang (n start / SigmaPnL theo end; trung binh 2 seed):
| lane | 07 | 08 | 09 | 07-01..07-09 | 07-10..09-30 |
|---|---|---|---|---|---|
| LLL | 2 / -4 630 | 75 / +6 687 | 33 / +2 982 | 2 / -4 630 | 108 / +9 669 |
| P | 14 / -4 555 | 74 / +2 662 | 57 / +1 269 | 4 / -5 693 | 141 / +5 069 |
| S | 2 / -4 630 | 75 / +8 133 | 33 / +743 | 2 / -4 630 | 108 / +8 876 |
| M | 2 / -4 630 | 77 / +4 199 | 45 / +1 654 | 2 / -4 630 | 122 / +5 853 |
| PS | 15 / -5 872 | 75 / +4 809 | 57 / -371 | 5 / -6 956 | 142 / +5 521 |
| PM | 12 / -8 581 | 74 / -7 679 | 78 / +937 | 4 / -6 155 | 160 / -9 169 |
| SM | 2 / -4 630 | 80 / +6 617 | 43 / -873 | 2 / -4 630 | 123 / +5 744 |
| NNN | 11 / -5 423 | 76 / -5 673 | 77 / +696 | 4 / -5 817 | 160 / -4 583 |

### Quy ket 2.4 (ghi truoc)
Delta_tot = NNN - LLL = -9,564 pp. Delta_P = -3,508 (36,7 %), Delta_S = -0,491 (5,1 %), Delta_M = -2,364 (24,7 %); tuong tac = -3,201 pp.
**Khong model don nao dat nguong 50 %** -> "tuong tac / khong quy ket" theo 2.4 -> P2: chay lane cap.
Mo ta lane cap (KHONG phai luat 2.4): tuong tac cap (X+Y - X - Y + L): PS -0,01, **PM -6,74**, SM +0,42 pp. Shapley 3 model (8 lane):
P -5,84, M -4,48, S +0,76 pp (tong -9,56). PM (S1 live) = -9,49 % con te hon NNN; S1 T1 trong NNN bu +3,05 pp so voi PM.
Doc co che + PnL: thua lo do TUONG TAC p15 T1 x net015 T1 tai GATE (pass Q3: P 127, M 108, PM 142 = NNN; lenh chi-o-lane PM -15 478),
khong do chat luong xep hang (Tang A: ca 3 model T1 >= live).

### Cay quyet dinh (muc 3) - ap co hoc
- B1: KHONG kich hoat (dk 1: ti so q99,99 DEV Q2 = 0,979; dk 2 dung 0,35).
- B2: KHONG kich hoat (S1 T1 khong kem; rk_oi_delta24h lech nhung khong dong gop).
- B3: KHONG kich hoat (net015 T1 AUC tot hon) -> van ban B3: "nguoc lai lam moi".
- B4 (nhat quan co che vs PnL): p15 - co che "khong can hieu chuan" (B1 SAI) nhung PnL: P la dong gop lon nhat (don 36,7 %, Shapley 61 %, cap
  PM -6,74) -> MAU THUAN -> "khong ket luan" -> giu p15 live. net015 - co che "lam moi" (B3) nhung PnL: M hai (don -2,36, Shapley -4,48, qua cap
  PM) -> MAU THUAN -> giu net015 live. S1 - co che "duoc lam moi" (B2 SAI), PnL Delta_S -0,49 (5 %), Shapley +0,76 -> khong mau thuan dang ke.
- B5: "khong nhanh nao (B1-B3) kich hoat -> giu ca 3 model live, khong U4b".
- KET QUA co hoc: hai cach doc van ban cay cho ket qua KHAC nhau (agent khong tu chon):
  (A) doc B5 theo chu: khong B1/B2/B3 kich hoat -> **B5: giu ca 3 model live, khong co ung vien U4b**.
  (B) ap tung model qua B1-B4: p15 live, net015 live (B4), S1 lam moi -> ung vien "S1 T2 (train toi 2026-09-30, recipe RETRAIN) + p15 / net015
      live" (= lane S kieu; Q3 lane S -0,49 pp vs L, ruler S1 +0,002 ns).
- Khong cong thuc nao co thanh phan "hieu chuan gate" (B1 khong kich hoat; P4 chi lam sau B1).

### Gioi han
- Q3 da bi nhin lan 3 (HO4, Lane N, U4a) -> moi ket luan la CHAN DOAN. 2 seed cho so dem gate / lenh 2026 GAN TRUNG (sd ~ 0,0003 pp) -> ve Q3,
  1 mau; khong co sai so lay mau giua seed; CI chi co o ruler (bootstrap tuan, 13-14 tuan).
- D-cal do tren file pred sim (nguon feature Vision cho 2026), Q1-Q2 la IN-SAMPLE cua T1 -> duoi T1 tren Q2 co the bi "nen" boi in-sample; quy tac
  B1 (ghi truoc) vi vay KHONG nhin thay dich chuyen duoi xay ra ngoai mau (Q3 1,19-1,51). Day la diem yeu thiet ke cua B1, khong sua sau khi thay.
- r-proxy D-cal khong phai bo dem gate that (gate tinh r tren tung ung vien). D-ruler S1 dung nhan g1lite 72h (dinh nghia x1_ledger) + Y1 touch;
  lift@8 = prec8 - base (khong phai ti so). Loai 8 id map 863 trung symbol.
- Tuong tac PM / Shapley la MO TA (khong ghi truoc trong 2.4). Lenh cap / gate pass theo quy chi tu log tong.
- Lane PnL theo dinh nghia SCORE_DEFS_L5 (SigmaPnL theo end; n theo start) -> "PnL chung / chi-o-lane" (theo start Q3) khong cong ra SigmaPnL.

### De MASTER quyet (STOP-D2)
1. Chon cach doc cay: (A) B5 giu 3 model live (khong U4b) hay (B) ung vien S1-only -> U4b. Agent nghieng (A): bang chung S1 T1 tot hon = 0
   (ruler CI chua 0; lane S -0,49 pp), U4b cong suat thap khong phan biet duoc; (B) chi co gia tri "tap duot quy trinh lam moi".
2. Phat hien chinh cho thiet ke sau: thua lo T1 = tuong tac thang diem p15 x net015 tai gate rolling (pass +51 %), KHONG do ranker; B1 do tren
   DEV in-sample khong bat duoc. Neu muon lam moi p15 / net015 ve sau can prereg MOI cho do "dich thang ngoai mau" (vd fit T1 cat S3-90d, do duoi
   tren 90 ngay OOS truoc S3) va thanh phan quantile-map gate (P4) - KHONG lam o luot nay.
3. Don dep: out/lane/{p,s,m,ps,pm,sm}/ds (hard link; S / M 0701 140 MB moi cai), RAW_N tai lai 140 MB - giu toi khi MASTER chot.
