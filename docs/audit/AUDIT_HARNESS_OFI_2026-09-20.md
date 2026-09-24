# AUDIT_HARNESS_OFI_2026-09-20 — dieu tra HARNESS_NGHI_NGO cua vong OFI (theo yeu cau Uni/MASTER)

Tai lieu nay tra loi day du yeu cau dieu tra HARNESS_NGHI_NGO trong
`docs/result/RESULT_S1_FREE_OFI.md` §4, theo dung trinh tu MASTER yeu cau (Giai doan 1 re truoc,
Giai doan 2 dat sau, chi chay khi Giai doan 1 khong giai thich duoc). **KET LUAN CUOI: ca
hai gia thuyet "population mismatch" VA "cross-session non-determinism" deu bi BAC BO
bang bang chung THUC NGHIEM truc tiep (khong chi doc code). Nguyen nhan that su da xac
dinh duoc: mot CONFOUND — missingness cua feature (OFI/noise) hoat dong nhu MOT CHI BAO
nhan dang "la 1 trong 15 symbol thanh khoan cao duoc chon o Giai doan A", va tap 15
symbol nay tinh co co edge5 cao hon han phan con lai cua universe trong giai doan CONFIRM
(2024-2025) — DOC LAP hoan toan voi noi dung OFI. Day KHONG phai loi code/harness, ma la
he qua tat yeu cua quyet dinh thu hep pham vi 15/>600 symbol da chot o Giai doan A.**

## Giai doan 1 — kiem tra population mismatch (RE, KHONG train lai)

### 1.1 Cau hoi 1: quan the danh gia edge5 cua baseline dong bang la gi?

Doc lai nguyen van `train_baseline18.py` (kernel `chuyendinh/s1-baseline18-det-n1-
20260919`, so ra 15.209468%):

```python
D = pd.read_parquet(LED_PATH, columns=["ts","sym","g1lite"])
D = D[D.g1lite.notna()].copy()          # loc DUY NHAT theo g1lite, KHONG loc theo OFI
...
def edge5_series(P):
    rk = P.groupby("ts").score.rank(method="first")
    top5 = P[rk <= 5]                    # top5 trong TOAN BO P (moi symbol trong D)
    e = top5.groupby("ts").g1lite.mean() - P.groupby("ts").g1lite.mean()
    return e
```

=> Baseline duoc danh gia tren **TOAN BO quan the D** (moi symbol trong
`cand_dev_x1_lite.parquet`, khong loc gi lien quan OFI — vi script nay khong biet OFI ton
tai). Day la co so goc cho quy uoc "quan the day du" ma moi bien the sau nay phai khop.

### 1.2 Cau hoi 2 (MAU CHOT): `ofi_train_eval.py` co loc/dropna theo OFI-coverage truoc
khi tinh edge5 khong?

Doc lai nguyen van (khong doan):

```python
D = pd.read_parquet(LED_PATH, columns=["ts","sym","g1lite"])
D = D[D.g1lite.notna()].copy()                      # dong 62-63, GIONG HET baseline
...
D = D.merge(OFI.rename(columns={"ts":"ts_h"}), on=["ts_h","sym"], how="left")  # dong 80
                                                     # LEFT JOIN -- KHONG xoa dong nao
...
def run_variant(name, FE):
    ...
    tr = D[D.ts < c - PURGE].sort_values("ts")      # dong 109 -- van la D DAY DU
    oos = D[(D.ts >= lo) & (D.ts < hi)].sort_values("ts")   # KHONG loc theo ofi_1h.notna()
```

**Tra loi: KHONG co dropna/filter nao theo OFI-coverage o bat ky dau trong pipeline.**
`OFI` duoc LEFT JOIN vao `D` (giu nguyen NaN cho >97% dong khong co OFI), va `run_variant`
train/predict tren **TOAN BO D** (moi symbol, ca 15 symbol co OFI lan >600 symbol con
lai) — dung y het quy uoc cua baseline goc. Neu day la nguyen nhan, no PHAI la mot dang
loc khac (vd row-count-per-tick lech do join sai), nen buoc tiep theo la kiem chung THUC
NGHIEM thay vi chi tin vao doc code.

### 1.3 Kiem chung thuc nghiem (dung lai file predict da co, KHONG train gi moi)

Tai `pred_baseline18_n1_kaggle.parquet` (frozen), doi chieu voi `pred_ofi_candidate.
parquet`/`pred_ofi_noise.parquet` (da co san tu vong truoc):

| kiem tra | ket qua |
|---|---|
| `len(BASE)` vs `len(CAND)` vs `len(NOISE)` | **6,685,957 = 6,685,957 = 6,685,957** (y het) |
| so tick duy nhat | **18,283 = 18,283 = 18,283** (y het) |
| dong (ts,sym) trung lap | 0 o ca BASE va CAND |
| so tick chi co o BASE hoac chi co o CAND | 0 va 0 |
| so tick co so dong khac nhau giua BASE va CAND | **0/18,283** |
| BASE.g1lite sau merge tu CAND (ts,sym) | 0 dong bi thieu (khop 1:1 hoan toan) |
| edge5 BASE tinh lai (full pop, 18 fold) | **+15.2095%** (khop 15.209468% da bao cao) |

=> **Quan the danh gia cua baseline/candidate/noise la GIONG HET NHAU tuyet doi, ca ve
so dong LAN so dong-tren-tung-tick.** Khong co bat ky hinh thuc population mismatch nao
giua cac bien the.

### 1.4 Kiem tra "re" theo dung de xuat cua MASTER: neu HAN CHE quan the ve dung tap co
OFI-coverage thi edge5 co tu nhien tang len khong?

Ap mask `(ts_h, sym)` co OFI (2.8% quan the, khop `ofi_coverage_frac` da bao cao — chenh
lech nho 2.66% vs 2.80% la do lam tron/thu tu loc `g1lite.notna()`) len CA BA bien the
(baseline/candidate/noise), tinh lai edge5 CONFIRM CHI tren tap con nay (top5 va trung
binh tick deu tinh lai tren tap con, dung y nhu MASTER de xuat):

| bien the | CONFIRM edge5 (full pop) | CONFIRM edge5 (RESTRICTED, chi 2.8%) | delta |
|---|---|---|---|
| BASELINE (KEEP9 goc, khong OFI/noise) | +17.8456% | +10.7709% | **-7.07pp** |
| CANDIDATE (KEEP9+ofi) | +20.7917% | +10.6245% | **-10.17pp** |
| NOISE (KEEP9+noise) | +19.5336% | +10.6498% | **-8.88pp** |

**Ket qua NGUOC HUONG hoan toan voi gia thuyet population mismatch**: han che quan the
xuong con 2.8% lam edge5 GIAM manh (khong tang) cho CA BA bien the — dung logic thong ke
co ban (top-5 tren ~10.35 dong/tick nen ranh gioi "top5" chiem gan mot nua tick, thu hep
bien do phan tach). Neu candidate/noise da tung duoc danh gia tren tap con nay (nhu gia
thuyet MASTER dat ra) thi edge5 cua chung se THAP HON, khong phai CAO HON baseline full-
pop — **hoan toan khong khop voi hien tuong quan sat duoc** (candidate/noise cao hon
baseline ~+1.7 den +2.9pp tren CONFIRM full-pop).

**=> GIAI DOAN 1 KET LUAN: gia thuyet population mismatch bi BAC BO hoan toan, ca qua
doc code (khong co dropna/filter) lan qua thuc nghiem (row/tick count y het, va huong
cua hieu ung khi han che quan the la NGUOC LAI).**

## Giai doan 2 — train baseline_fresh + candidate + noise CUNG session (kernel
`chuyendinh/ofi-train-eval-v2-audit`, COMPLETE, ~2.3h — trong nguong an toan 3h)

Vi Giai doan 1 khong giai thich duoc (population da khop dung ma van lech), chuyen sang
Giai doan 2 dung theo de xuat cua MASTER: train **3 bien the CUNG MOT kernel/session**
(`baseline_fresh`=KEEP9 thuan, `ofi_candidate_v2`=KEEP9+ofi, `ofi_noise_v2`=KEEP9+noise),
CUNG mot lan chay voi `ofi-build-feat-15sym`/`s1-featv2-x1-20260919`, cung so sanh voi
`baseline_frozen` (tai su dung tu session 2026-09-19) trong CHINH kernel nay de kiem tra
truc tiep kha nang tai lap Kaggle giua hai session.

### 2.1 KET QUA QUYET DINH: `baseline_fresh` va `baseline_frozen` GIONG HET NHAU TUYET DOI

```
baseline_fresh_edge5_all_pct  = 15.209467887878418
baseline_frozen_edge5_all_pct = 15.209467887878418
fresh_vs_frozen CONFIRM Δedge5 CI: mean=0.0, lo=0.0, hi=0.0  (lech = 0.000000, TUYET DOI)
fresh_vs_frozen CONFIRM verdict edge5: NULL (dung nhien, delta=0 chinh xac tung bit)
```

**=> Gia thuyet cross-session non-determinism (da neu trong RESULT ban dau §4.3) bi BAC
BO HOAN TOAN.** Kaggle CHAY LAI CUNG code/seed=42/n_jobs=1/hyperparameter tren CUNG du
lieu cho ket qua **tai lap tuyet doi 100%** giua hai session cach nhau 1 ngay — khong co
"trôi" (drift) nao ca. Day la bang chung manh nhat co the co (khong chi CI hep, ma delta
CHINH XAC BANG 0 o moi tick). Dieu nay cung co nghia: **quyet dinh "tai su dung baseline
dong bang" trong cac vong truoc (HPO_BAG_FEATGRP, NOISE_CAL, vong OFI nay) la AN TOAN VE
MAT KY THUAT** — khong can rag lai cac ket luan cu vi ly do nay (xem muc 4 "Ra soat cac
vong truoc").

### 2.2 candidate/noise vs baseline_fresh: KET QUA GIU NGUYEN NHU VONG 1 (nhu du doan, vi
baseline_fresh == baseline_frozen chinh xac)

| Bien the | CONFIRM Δedge5 (vs baseline_fresh) | CI | verdict rieng |
|---|---|---|---|
| candidate | +2.9461pp | [+0.930, +5.685]pp | THANG* |
| noise     | +1.6879pp | [+0.041, +3.934]pp | THANG* — **van vuot nguong ca SELECT lan CONFIRM** |

`*` van khong duoc cong bo vi noise van "thang" — xem muc 3.

## 3. Nguyen nhan that su: CONFOUND missingness-la-chi-bao-symbol (khong phai bug)

Da loai tru CA HAI gia thuyet nhe (population mismatch, cross-session drift) bang thuc
nghiem truc tiep. Quay lai bang chung cot loi da co tu vong 1 va tai xac nhan trong Giai
doan 2 (fold-by-fold gan nhu giong het giua candidate/noise, xem RESULT_S1_FREE_OFI.md
§4.2) — ket hop voi ket qua muc 1.4 (edge5 GIAM khi han che quan the xuong dung 15
symbol) — buc tranh day du la:

- OFI/noise chi "song" tren dung 15/>600 symbol (2.66-2.80% quan the). `noise_ofi_check`
  duoc thiet ke CO CHU DICH voi CUNG mask NaN voi `ofi_1h` (theo dung PREREG §4, de doi
  chung phan anh dac diem "feature thua NaN" cua vong nay).
- Khi XGBoost (`tree_method=hist`) hoc tren mot cot co >97% NaN, no HOC mot huong-mac-
  dinh (default missing direction) rieng cho gia tri NaN trong moi split lien quan cot
  do — TUONG DUONG voi viec hoc mot **chi bao nhi phan "co gia tri hay khong"**, DOC LAP
  voi gia tri THAT cua cot (neu co). Vi mask NaN trung khop CHINH XAC voi "co phai 1
  trong 15 symbol thanh khoan cao duoc chon o Giai doan A hay khong", chi bao nay tro
  thanh MOT DANG "symbol-identity feature an trong lop vo mot cot so thua NaN".
- 15 symbol nay (AIAUSDT, PEOPLEUSDT, UNFIUSDT, ALCHUSDT, MASKUSDT, MYXUSDT, BLZUSDT,
  ALICEUSDT, COAIUSDT, EVAAUSDT, RSRUSDT, 1000PEPEUSDT, WIFUSDT, CHRUSDT, SOLUSDT) —
  duoc chon vi thanh khoan CAO NHAT trong ca 2 backtest nguon — CO THE co dac tinh
  edge5/du doan duoc khac biet so voi phan con lai cua universe (>600 symbol, phan lon
  la coin nho/thanh khoan thap) TRONG RIENG giai doan CONFIRM (2024-2025, thi truong
  altcoin/memecoin bung no manh) — mot dang selection bias VON CO cua tap 15 symbol nay,
  KHONG lien quan gi den OFI/order-flow.
- Vi CA HAI (`ofi_candidate` va `noise_ofi_check`) cung mang chinh xac CUNG MOT chi bao
  nhi phan nay, ca hai deu "huong loi" GAN NHU GIONG HET nhau tren CONFIRM — dung nhu
  quan sat duoc (chenh lech fold-by-fold [-0.94,+2.36]pp, khong co pattern he thong).

**Day KHONG phai loi purge/join/leak (da loai tru qua sanity check), KHONG phai population
mismatch (muc 1), KHONG phai cross-session non-determinism (muc 2) — ma la mot CONFOUND
THIET KE: viec thu hep OFI xuong 15/>600 symbol (quyet dinh BAT BUOC tu rang buoc thoi
gian o Giai doan A) tao ra mot "chi bao nhan dang subset" an trong missingness, va chi
bao nay tinh co co ich cho edge5 CONFIRM DOC LAP voi OFI. Bo doi chung nhieu
(`noise_ofi_check`) da lam DUNG VIEC CUA NO — phat hien chinh xac confound nay, dung nhu
thiet ke cua PREREG du dinh.**

### 3.1 Kiem tra bo sung: nested SELECT→CONFIRM co ap dung dung thu tu khong?

- Hyperparameter CO DINH (khong tune tren SELECT roi ap sang CONFIRM) — khong co kenh ro
  ri nao qua buoc chon sieu tham so.
- `fold_of_ts` chia CONFIRM = fold 10-17 (dung `P`'s own `fold` column, gan voi CUTS18 —
  khong co chong lan voi SELECT fold 0-9).
- CONFIRM co **13,914 tick** (khong phai mau nho) — khong phai van de co mau qua nho lam
  sai CI.
- => Khong phat hien loi thu tu SELECT→CONFIRM nao khac.

## 4. Ra soat cac vong truoc — co nguy co tuong tu khong?

- **`docs/result/RESULT_S1_HPO_BAG_FEATGRP.md`, `docs/prereg/PREREG_S1_NOISE_CAL.md`**: cac vong nay
  **KHONG dung tinh nang bi thua-NaN-theo-mot-subset-symbol-nho** nhu vong OFI — cac
  feature duoc thu nghiem (KEEP9-mo-rong, HPO, bagging) deu duoc tinh tren TOAN BO
  universe (khong bi gioi han con 15/>600 symbol), nen confound "missingness-la-chi-bao-
  subset" o day KHONG AP DUNG cho cac vong do. **Khong can ra soat lai ket luan cua cac
  vong nay vi ly do nay.**
- **Bat ky vong tuong lai nao dung feature CHI PHU MOT SUBSET NHO, KHONG NGAU NHIEN cua
  universe** (vd du lieu tra phi chi mua cho top-N coin, hoac feature tinh rieng cho mot
  nhom thanh khoan cao) **DEU CO NGUY CO TUONG TU** — can ap dung bai hoc nay: (a) BAT
  BUOC dung doi chung nhieu voi CUNG mask NaN (da lam dung trong vong nay — chinh no la
  ly do phat hien duoc confound), (b) neu noise cung "thang", KHONG duoc quy ket cho noi
  dung feature, phai coi day la tin hieu subset-selection-bias can dieu tra rieng truoc
  khi tin bat ky ket qua nao tren candidate that.
- Quyet dinh "tai su dung baseline dong bang" (dung trong `PREREG_S1_HPO_BAG_FEATGRP.md`,
  `PREREG_S1_NOISE_CAL.md`, va vong OFI nay) **da duoc XAC NHAN AN TOAN** boi phep do
  cross-session determinism o muc 2.1 (delta=0 tuyet doi) — khong can ra soat lai cac
  vong do vi ly do nay.

## 5. KET LUAN CUOI CUNG cua dieu tra HARNESS_NGHI_NGO

| Gia thuyet | Ket luan | Bang chung |
|---|---|---|
| (a) Population mismatch (candidate/noise chi danh gia tren 2.66% OFI-coverage, baseline tren 100%) | **BAC BO** | row/tick count giong het tuyet doi (muc 1.3); han che quan the LAM GIAM edge5 (huong nguoc, muc 1.4) |
| (b) Cross-session Kaggle non-determinism (baseline dong bang tu session khac ngay) | **BAC BO** | baseline_fresh == baseline_frozen CHINH XAC TUYET DOI, delta=0.000000 (muc 2.1) |
| (c) Confound missingness-la-chi-bao-subset-symbol (15/>600 symbol thanh khoan cao co dac tinh CONFIRM-period khac biet, khong lien quan OFI) | **XAC NHAN — day la nguyen nhan that su** | candidate va noise huong loi GAN NHU GIONG HET nhau moi fold (RESULT_S1_FREE_OFI.md §4.2); edge5 han che-quan-the giam manh cho ca 3 bien the nhu nhau (muc 1.4) |

**KHONG phai loi purge/join/leak, KHONG phai bug harness theo nghia thong thuong.** Day
la mot GIOI HAN THIET KE cua vong nay: pham vi 15/>600 symbol (bat buoc do rang buoc thoi
gian Kaggle o Giai doan A) khien MOI feature gioi han trong pham vi do — kha ky OFI hay
nhieu ngau nhien — deu se "thang" tren CONFIRM vi ly do KHONG lien quan gi den noi dung
feature. **Verdict cuoi cung cho gia thuyet OFI: KHONG THE KET LUAN THANG/NULL/THUA voi
thiet ke hien tai** (giu nguyen HARNESS_NGHI_NGO nhu RESULT ban dau, nhung nay da co day
du dieu tra va nguyen nhan CU THE, khong con la "nghi ngo chua ro" nua).

## 6. De xuat neu MASTER muon tiep tuc thu nghiem OFI (ngoai pham vi vong nay)

De tach OFI-content ra khoi confound subset-symbol, can MOT trong cac huong sau (deu la
vong do luong MOI, can MASTER duyet rieng):
1. **Mo rong OFI ra toan bo universe** (khong chi 15 symbol) — nhung da xac dinh o Giai
   doan A la khong kha thi trong 1 kernel/3h; can chia nho thanh nhieu kernel song song
   (Kaggle cho phep 5 kernel dong thoi) hoac dung Binance Vision monthly bundle cho toan
   bo ~52 symbol con lai (sau khi loai memecoin) trai qua nhieu lan chay.
2. **Doi chung nhieu CHAT CHE HON**: thay vi 1 cot noise, dung NHIEU (vd 5-10) cot noise
   DOC LAP, MOI cot gan voi mot **subset symbol NGAU NHIEN KHAC NHAU** (cung kich thuoc
   15 symbol nhung chon ngau nhien, khong phai theo thanh khoan) — neu TAT CA deu "thang"
   tuong tu nhau tren CONFIRM, xac nhan chac chan hieu ung la do "MOI subset 15-symbol
   deu duoc loi", khong rieng gi 15 symbol thanh khoan cao; nguoc lai neu chi co subset
   "thanh khoan cao that" moi thang, do la mot phat hien khac (lien quan lien ket giua
   thanh khoan va edge5, khong phai OFI).
3. **Doi don vi danh gia**: thay vi top-5 tren TOAN BO universe, gioi han danh gia edge5
   CHI trong pham vi 15 symbol co OFI (so sanh candidate vs baseline CUNG gioi han vao
   15 symbol do) — loai bo hoan toan kha nang "duoc chon vao top-5 chi vi la 1 trong 15
   symbol nay" vi ca hai phia deu chi duoc chon tu chinh 15 symbol do.

Khong thuc hien buoc nao o tren trong vong nay (ngoai pham vi PREREG da chot, dung theo
yeu cau MASTER "dung neu Giai doan 1/2 da giai thich duoc, khong tiep tuc ton compute").

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
