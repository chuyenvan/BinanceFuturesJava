# PREREG — SELECTOR_ABLATION_R50: gia tri selector nam o LOC THO (universe -> top-M) hay XEP HANG MIN (top-M -> 16)?

Ngay chot: 2026-10-03 (TRUOC khi day bat ky kernel nao cua vong nay). Nguoi chay: Claude (research engineer, agent).
Bo chot: tai lieu nay + `research/analysis/selector_ablation_topm.py` + `research/analysis/selector_ablation_r50_driver.py`
cung commit. Tiep noi SELECTOR_ABLATION (pre-reg 5f357d3f, A1 0595b855, result 33d8fc17). Sau commit KHONG doi
arm/thuoc/luat; sai sot ky thuat (crash, parity FAIL, sha lech) => VOID, khong tune.

## 1. Cau hoi
Vong truoc: B0 >> R16 (hoan vi diem selector tren TOAN universe co pred moi tick): Calmar_MTM ngay 3,43 vs mean 0,41,
B0 - meanR = +3,02 CI [+1,38; +6,74], CAGR +24,4pp [+13,3; +37,8]. Audit IC trong tap da chon (top-16 + gate) ~0.
Cau hoi: gia tri do nam o tang LOC THO (universe ~100-500 coin -> top-50/100) hay XEP HANG MIN (top-50 -> 16)?
Thiet ke: giu nguyen TAP coin top-M cua B0 moi tick, chi xao THU TU ben trong top-M => top-16 = tap con ngau nhien cua
top-M B0. Neu R50 ~ B0 => xep hang trong top-50 khong mang gia tri; neu R50 << B0 => xep hang min co gia tri.

## 2. Nen B0 (khoa, y vong truoc)
profile `r4_kg0_k16_f015_g155` + override `SIM_GATE_ROLLING_MODE=ratio, SIM_GATE_ROLLING_DAYS=90,
SIM_GATE_ROLLING_PCT=0.999950829, TS_GIVEBACK_RATIO=1.0, SIM_TS_MAX_GAP=0.03, SIM_TS_MAX_GAP_WEAK=0.03`;
jar `sim-jar-gdv2` sha256 7368be46…; bundle `sim-x1-2021-bundle` + moc21 `s3-moc-2021bins`; kernel = `tools/kaggle_sim.py`
HEAD md5 8b60b00a (NOWRITE242 + PREFLIGHT). DEV <= 2025-12-31. Khong cham 242/shadow, khong sua .java, khong build,
khong Java sim tren Oracle.

## 3. Dinh nghia top-M (doc code, read-only)
- `WfoDataset.buildFundingFromWfFiles:248` / `s3_funding.py:92`: score = float32(1) - p0 (p0 = P(win) horizon 0);
  dong p0 NaN bi bo. `preprocessFundingData`: sort score TANG. `selectCands`: K=16 phan tu DAU = score THAP nhat
  = **p0 CAO nhat** (= symbolPred = 1 - p0 THAP nhat).
- **Dinh chinh brief:** brief giao viec ghi "p0 thap nhat = symbolPred cao nhat" — NGUOC voi code (va voi
  `LiveBuildMapTest`: "coin rank 1 nhan P(win) LON nhat => symbolPred THAP nhat"). Pre-reg theo CODE, dung tinh than
  "dung tieu chi sim chon": top-M = M dong p0 CAO nhat.
- BIG_DOWN: `getTopSymbolArray` duyet `TreeMap<score, sym>` TANG (bo coin locked / thieu ticker) lay coin dau => cung
  dung thu tu diem (RESULT vong truoc da sua §8). => R_M xao ca chon coin BIG_DOWN trong top-M. DCA_LEVEL1 di theo cum.
- top-M(ts) = M dong p0 hop le co score THAP nhat trong ts, the: thu tu record (tie o bien rat hiem, xem §4 sanity).
  Neu so dong hop le n_ts <= M thi top-M = ca universe => tai tick do R_M == R16 (hoan vi toan bo).

## 4. Arm (khoa)
| arm | M | seed | bins sha256 (18 file, sort ten) | out |
|---|---|---|---|---|
| B0REF2 (= B0) | — | — | goc 407e2aba… (khong SA block, cau hinh y selab-b0ref) | `~/kaggle_sim/out/selab-b0ref2` |
| R50s42 | 50 | 42 | 4762a2ecb59cde99… | `selab-r50s42` |
| R50s7 | 50 | 7 | dff2cefe4d6a92c9… | `selab-r50s7` |
| R100s42 | 100 | 42 | 35cfbac92ecf8f7d… | `selab-r100s42` |
| R100s7 | 100 | 7 | a2d5c63efa30107d… | `selab-r100s7` |
Hoan vi (`selector_ablation_topm.transform_topm`): moi file, rut u = rng.random(n) cho MOI dong (rng =
np.random.default_rng(seed) xuyen 18 file sort ten); key = ts neu dong thuoc top-M, nguoc lai -1-idx (tu anh xa);
src = lexsort(u, key), dst = lexsort(idx, key); bo-4 (p0..p3) cua src gan cho dst. He qua: dong ngoai top-M
byte-identical; tap coin top-M moi ts giu nguyen; 16 slot PREDICT nhan DUNG 16 gia tri sp nhu B0 (gate theo slot giu
nguyen), chi doi danh tinh coin => top-16 = tap con ngau nhien cua top-M B0.
Tham chieu (KHONG vao luat): R16 = mean(R42, R7, R13) vong truoc (`selab-r42/-r7/-r13`, hoan vi toan universe).

Sanity (da chay TRUOC commit, `~/claude_master/1003/sa50/sanity.json`, ok = True): src sha == 407e2aba; ca 4 arm x 18
file: cung (ts,sym), multiset bo-4 moi ts, vi tri NaN, ngoai top-M byte-identical; lech tap top-M chi o tie bien
(R50: 12/8 dong tren 17 ts tie; R100: 16/16 dong tren 25 ts tie — trong 157 908 ts); % dong top doi p0: R50 ~98,0%,
R100 ~99,0% (~1 - 1/M); s42 vs s7 khac 98,0% (M50) / 99,0% (M100); Spearman trong top-M vs P0 (3 file mau) |rho| <= 0,0033.
Universe (so dong p0 hop le / ts, trung vi [q05; q95]): 2021H2 121 [110; 127], 2022 134 [129; 142], 2023 182 [141; 228],
2024 259 [236; 322], 2025 434 [346; 525]; % tick n_ts <= 50: 0,0006%; <= 100: 0,023% (gan nhu khong tick nao R_M == R16).
M/universe trung vi: M50 = 41/37/27/19/12%, M100 = 83/75/55/39/23% (2021..2025) => R100 rat gan R16 o 2021-2022.

## 5. Trinh tu & cong parity
1) Commit pre-reg nay (bins da sinh + sanity PASS truoc commit — chi la dau vao, chua co ket qua sim nao).
2) Day CUNG DOT 5 kernel: B0REF2 + R50s42 + R50s7 + R100s42 + R100s7. Kernel R = SA_BLOCK vong truoc (khong doi) voi
   helper `selector_ablation_topm.py` (import duoi ten SAS): sinh bins TRONG Kaggle, assert sha256 == ban Oracle va
   src sha == 407e2aba, dung lai funding.bin bang `s3_funding.py`, tro fundingPredDir sang ban moi.
3) Parity PASS <=> B0REF2: n == 2517 VA round(equity) == 131908 VA jar 7368be46 VA mapper >= 800 VA printDone giong
   de-p1 TUNG O theo gia tri float32 (`printdone_valeq`, nhu vong truoc). md5 printDone GHI LAI: ky vong ff3ce513
   (== selab-p0, cung anh Kaggle vong truoc); 650c386f cung chap nhan (anh cu) — ghi ro anh nao. Moi R: jar, mapper,
   bins_ok (sha == Oracle), src sha == 407e2aba. FAIL => VOID ca vong, khong cham.
4) B0 cua thuoc = B0REF2 (cung dot voi R). R16 (tham chieu) dung lai neu md5 B0REF2 == md5 selab-p0; neu khac anh:
   van bao cao R16 nhung ghi "khac anh Kaggle".

## 6. Thuoc (khoa, nhu vong truoc)
(i) Loi suat ngay MTM (equity daily, b+unP) GHEP CAP theo ngay voi B0; moving-block bootstrap block 10 ngay, NREP 2000,
seed 20260905, cung chi so khoi cho moi arm (`selector_ablation_driver.daily_boot`). Thong ke: CAGR, maxDD MTM ngay,
Calmar_MTM = CAGR/|maxDD|, Sharpe ngay. Tuong phan CHINH (k = 2): **B0 - mean(R50s42, R50s7)** va
**B0 - mean(R100s42, R100s7)** (mean tinh trong tung replicate). CI 95% percentile, INFLATE 1,18 quanh diem
(lo' = d - 1,18*(d - lo), hi' = d + 1,18*(hi - d)). Phu (thong tin, cung inflate): B0 - tung seed, R100 - R50,
R50 - R16, R100 - R16, B0 - R16; phan khoang cach giai thich frac_M = (Calmar_B0 - Calmar_RM)/(Calmar_B0 - Calmar_R16)
(+ CAGR), CI percentile tren replicate co mau so > 0.
(ii) SumPnL, n, win%, ROI/leg mean & median, SL-rate (TSloss% nhu vong truoc), UW ngay, Calmar MTM phut (R.run_mtm),
top-5 episode share, exposure. (iii) Theo nam 2021H2..2025: ROI nam (equity MTM), n, SumPnL, win%.
(iv) Overlap tap lenh voi B0 (sym|phut vao; theo level PREDICT/BIG_DOWN/DCA). (v) rate CI block-72h (R.ci_pair) — thong tin.
Seed-dispersion: mean +- sd qua 2 seed moi M.

## 7. Luat doc (khai TRUOC) — ap cho tung M (R50 = phep thu CHINH; R100 = diem duong cong)
d = Calmar_MTM(B0) - mean Calmar_MTM(R_M), CI inflate 1,18; dCAGR = CAGR(B0) - mean CAGR(R_M):
- **XEP HANG MIN CO GIA TRI** <=> CI_lo > 0.
- **XEP HANG MIN CO HAI** <=> CI_hi < 0 (random trong top-M tot hon B0).
- **LOC THO** <=> CI chua 0 VA |dCAGR| < 3pp.
- Con lai (CI chua 0 nhung |dCAGR| >= 3pp) => **CHUA KET LUAN** (bao cao huong + do lon, khong nang cap).
Ket hop (dien giai khai truoc):
- R50 LOC THO & R100 LOC THO => "gia tri = LOC THO universe -> 100; xep hang trong top-100 khong quan trong";
  huong = tranh duoi (coin ngoai top-100).
- R50 LOC THO (R100 khac) => "gia tri = LOC THO, xep hang trong top-50 khong quan trong"; huong = chat luong loc
  universe -> 50 (tranh duoi lo).
- R50 XEP HANG MIN CO GIA TRI => "xep hang min co gia tri"; huong = ranking (top-50 -> 16).
- R50 CO HAI => thu tu top-16 hien tai la nhieu/hai.  R50 CHUA KET LUAN => khong nang cap; bao cao frac_50.
Nam (thong tin, KHONG vao luat): so nam 2022-2025 co ROI B0 > mean R_M.
Ky vong khai truoc (khong vao luat): audit IC trong tap da chon ~0 nghieng ve LOC THO o M = 50. Universe nho o
2021-2022 (xem §4) => R100 gan R16 o cac nam do; duong cong Calmar theo M (16 -> 50 -> 100 -> universe) doc kem bang %
tick co n_ts <= M.
He qua hen truoc cho LABEL_FIRSTHIT / retrain: LOC THO => nhan/feature nham tang "universe -> top-M" (recall coin
xau / duoi lo, rank-IC TOAN universe, precision o bien M), KHONG toi uu thu tu top-16. XEP HANG => nham ranking
trong top-M (IC trong top-50, loss listwise). Moi model moi phai cham END-TO-END bang chinh ablation nay.

## 8. Han che biet truoc
- Power: CI B0 - R16 vong truoc rong ([1,38; 6,74] voi d 3,02); luat LOC THO doi them |dCAGR| < 3pp nen CI rong khong
  tu dong thanh LOC THO.
- 2 seed/M; R50s42 & R100s42 (va s7) dung CHUNG day ngau nhien u (common random numbers) => R50 va R100 khong doc lap.
- Path-dependence sim (coin dang giu, CONC_CAP 15%) => so slot khong giu tuyet doi; Calmar la thuoc khong phu thuoc
  quy mo. R_M khong do gia tri cua buoc "chon top-16 tu top-M" o M khac (chi 2 diem M).
- R16 tu dot kernel vong truoc (cung anh neu md5 khop). Mot DEV duy nhat (2021-07..2025-12), khong holdout 2026.
