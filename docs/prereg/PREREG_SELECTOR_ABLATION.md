# PREREG — SELECTOR_ABLATION: selector S1 co phai lever cua LONG B0 khong?

Ngay chot: 2026-10-03 (TRUOC khi day bat ky kernel nao). Nguoi chay: Claude (research engineer, agent).
Bo chot: tai lieu nay + `research/analysis/selector_ablation_scores.py` + `research/analysis/selector_ablation_driver.py`
cung commit. Sau commit KHONG doi arm/thuoc/luat; sai sot ky thuat (crash, parity FAIL) => VOID, khong tune.

## 1. Cau hoi & mau thuan can xu
- AUDIT_LONG_LEVERS (9e645137) §ban do: symbolPred gan nhu khong noi gi ve ket qua lenh (Spearman +0,014; trong tick -0,021).
- Bang chung cu: selector_edge_evidence rank-IC S1-G015 +0,097; placebo P3 +1,56pp/leg.
- Phan xu bang ABLATION TRONG SIM (end-to-end, cung jar/profile/gate/exit/sizing): B0 vs chon coin NGAU NHIEN vs chon theo THANH KHOAN.

## 2. Nen B0 (khoa)
profile `r4_kg0_k16_f015_g155` + override `SIM_GATE_ROLLING_MODE=ratio, SIM_GATE_ROLLING_DAYS=90,
SIM_GATE_ROLLING_PCT=0.999950829, TS_GIVEBACK_RATIO=1.0, SIM_TS_MAX_GAP=0.03, SIM_TS_MAX_GAP_WEAK=0.03`;
jar `sim-jar-gdv2` sha256 7368be46…; bundle `sim-x1-2021-bundle` + moc21 `s3-moc-2021bins`; kernel = `tools/kaggle_sim.py`
HEAD md5 8b60b00a (NOWRITE242 + PREFLIGHT) + 1 khoi chen SA_BLOCK. B0 tham chieu `~/kaggle_sim/out/de-p1`
md5 printDone 650c386f, n 2517, equity 131908. DEV <= 2025-12-31. Khong cham 242/shadow, khong sua .java, khong build.

## 3. Co che sim (doc code, read-only) va cach tach diem selector
- Diem selector: 18 file `predict_wf_<fold>.bin` (26 B/rec `>q h 4f`: ts, symId, p0..p3) -> `s3_funding.py` -> `funding.bin`
  -> `time2SymbolPred[ts]` (symbolPred = 1 - p0, sort tang). Gate p15 = `pred.bin` (predictionMap theo ts, CAP THI TRUONG),
  FILE RIENG => doi diem selector KHONG dung vao p15.
- Moi tick: `selectCands` lay K=16 phan tu symbolPred THAP nhat (SELECTOR_RANK_TOPK=16) -> voi tung coin (bo qua coin dang giu,
  thieu ticker) -> gate G2 ratio: `r = p15 / (max(DYN_MIN, sp/0,15*1,2876) * 1,55)`, PASS <=> r > q_t (phan vi cuon causal
  90 ngay cua chinh r). sp con vao trail tier STRONG/WEAK nhung B0 dat gap 0,03/0,03 => trung tinh. Sizing TIER_FLAT.
- Ablation = HOAN VI bo-4 (p0..p3) giua cac symbol TRONG CUNG ts, giu nguyen (ts,symId), thu tu record, dong NaN, va
  MULTISET gia tri moi ts. He qua: 16 slot top-K nhan DUNG 16 gia tri sp nhu B0 => quyet dinh gate theo slot (p15, sp)
  giu nguyen; CHI danh tinh coin doi. Khac biet con lai chi do duong di (coin dang giu bi skip, thieu ticker, CONC_CAP,
  buffer r). Day la "K16 ngau nhien trong universe co pred tai tick, cung cau truc slot/gate" — sat nhat voi
  "K16 ngau nhien trong tap ung vien qua gate" ma khong sua .java (gate khong phu thuoc coin ngoai gia tri sp).
- Trien khai: kernel sinh lai bins arm TRONG Kaggle (helper nhung base64), assert sha256 == ban Oracle, dung lai funding.bin
  bang `s3_funding.py` (byte-faithful: dry-run P0 ra md5_funding 8e57d900 == bundle), tro `fundingPredDir`/WFO sang ban moi.
  Dataset Kaggle moi CHI cho arm L: `sel-ablation-liq` (liqrank int16). R khong can dataset (tat dinh theo seed).

## 4. Arm (khoa)
| arm | bins selector | out |
|---|---|---|
| P0 | bins goc (sha256 407e2aba…) — PARITY | `~/kaggle_sim/out/selab-p0` |
| R42 / R7 / R13 | hoan vi ngau nhien bo-4 trong ts, `np.random.default_rng(seed)`, file sort ten | `selab-r42/-r7/-r13` |
| L | gia tri p0 GIAM dan (kem p1..p3 cung dong) gan cho symbol theo quoteVol 24h GIAM dan (the: symId tang) | `selab-liq` |
quoteVol 24h (L) = tong quoteVol 1m cac gio UTC tron [F-24h, F), F = floor_gio(ts) <= ts => CAUSAL. Nguon: Aerospike
`test.kline_1m_opt` (cung nguon dung ticker bundle). Symbol khong co qv => qv 0 => cuoi hang.
Sanity bat buoc truoc khi day R/L (`selector_ablation_scores.py sanity`): cung tap (ts,sym) + multiset moi ts + vi tri NaN;
3 seed khac nhau (>50% p0 doi); L: p0 khong tang theo hang thanh khoan; tai tinh doc lap 30 dong qv24 tu parquet gio, gio
cuoi + 1h <= ts.

## 5. Trinh tu & cong parity
1) Commit pre-reg nay. 2) Day P0. PASS <=> md5 printDone == 650c386f VA n == 2517 VA round(equity) == 131908 VA jar sha
7368be46 VA bins_sha == 407e2aba VA funding md5 == 8e57d900 (bundle). FAIL => VOID ca nghien cuu, khong day R/L.
3) PASS => day R42, R7, R13, L song song theo quota. Moi arm phai: bins_sha == ban Oracle, jar dung, symbol_mapper >= 800.

## 6. Thuoc (khoa)
(i) Loi suat ngay MTM (equity = balance + unrealized, dong cuoi ngay sim.out), GHEP CAP theo ngay voi B0; moving-block
bootstrap block 10 ngay, NREP 2000, seed 20260905, cung chi so khoi cho moi arm. Thong ke: CAGR, maxDD (MTM ngay),
Calmar_MTM = CAGR/|maxDD|, Sharpe ngay. Tuong phan: B0 - mean(R42,R7,R13) (tinh trong tung replicate), B0 - tung R,
L - B0, L - mean(R). CI 95% percentile. k = 1 phep thu chinh (B0 - mean R gop 3 seed) => KHONG inflate (ci_infl == ci_raw).
Bo sung (thong tin): Calmar voi maxDD MTM PHUT (R.run_mtm), exposure (% ngay co leg mo, so leg mo TB).
(ii) SumPnL, n, win%, ROI/leg mean & median, SL-rate (STOP_LOSS_DONE %), top-5 episode share.
(iii) Theo nam 2021H2..2025: ROI nam (equity MTM), n, SumPnL, win%.
(iv) Overlap tap lenh voi B0: % lenh B0 (sym|phut vao) co trong arm; Jaccard.
Seed-dispersion: mean +- sd qua 3 seed R cho moi thuoc.

## 7. Luat doc (khai TRUOC)
- **SELECTOR LA LEVER** <=> CI95 cua [Calmar_MTM(B0) - mean_R Calmar_MTM] > 0 (can duoi > 0) VA ROI nam B0 > mean(R)
  o >= 3/4 nam 2022-2025.
- **SELECTOR CHET** <=> CI95 do chua 0 VA |CAGR(B0) - mean_R CAGR| < 3pp.
- Con lai => CHUA KET LUAN (bao cao huong + do lon, khong nang cap).
- Thanh khoan: neu Calmar_MTM(L) >= Calmar_MTM(B0) (obs) => "THANH KHOAN DU THAY SELECTOR" (kem CI L - B0).
- Ky vong khai truoc: placebo P3 cu +1,56pp/leg => neu selector that, dROI/leg ~ +1,5pp, SumPnL B0 - R ~ +30..40k.
  Neu SumPnL B0 - mean R < +10k ma luat LEVER van dat => ghi ro "lever qua rui ro/thoi diem, khong qua ROI/leg".
- He qua da hen: LEVER => dang retrain selector tren du lieu sach / label da horizon. CHET => dong moi huong
  "model selector tot hon" cho LONG B0. L >= B0 => thay selector bang luat thanh khoan (re, it rui ro model).

## 8. Han che biet truoc
Sim co path-dependence (coin dang giu, CONC_CAP 15%) nen R khong hoan toan "cung slot". BIG_DOWN/DCA_LEVEL1 khong qua
selector => phan chung giua cac arm (lam loang hieu ung; bao cao overlap theo level). 3 seed => sai so mean(R) do
hoan vi duoc bao cao bang sd qua seed, khong gop vao CI bootstrap.
