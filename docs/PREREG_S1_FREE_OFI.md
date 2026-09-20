# PREREG_S1_FREE_OFI — order-flow-imbalance (OFI) tu Binance Vision aggTrades (mien phi), cho S1

Chot truoc khi tinh bat ky rank-IC/edge5 nao. Commit file nay PHAI dung truoc
`docs/RESULT_S1_FREE_OFI.md`; neu nguoc lai ket qua VO HIEU. Toan bo tinh toan THAT
(tai aggTrades, build feature, train XGBoost, do rank-IC/edge5) chay tren **Kaggle**,
KHONG phai Oracle (theo chi dao MASTER — day la nhiem vu Python/XGBoost thuan, tach
khoi Java sim tren Oracle).

## 0. Boi canh

`docs/PROPOSAL_MICROSTRUCTURE_DATA.md` muc 6 de xuat: `data.binance.vision` bulk
aggTrades da co san MIEN PHI cot `is_buyer_maker` (aggressor flag) cho toan bo universe
futures — nen thu xay feature order-flow-imbalance tu nguon nay TRUOC KHI can nhac mua
L2 order book dat tien. Day la nhiem vu MOI, 2 giai doan tuan tu: **Giai doan A** (khao
sat ky thuat, KHONG phai buoc thong ke) da chay xong — ket qua o muc 1. **Giai doan B**
(pre-reg thong ke, file nay) chot phap vi + luat doc/nguong TRUOC khi tinh so.

## 1. GIAI DOAN A — Khao sat kha thi (da chay, ket qua THAT tren Kaggle)

### 1.1 Kernel A1 — `chuyendinh/ofi-stage-a-survey` (COMPLETE, 862.9s)

Tai thu 28 file (20 daily + 8 monthly) cho 4 symbol (BTCUSDT, ETHUSDT — de biet
worst-case, khong nam trong universe muc tieu; SOLUSDT, ALICEUSDT — CO trong danh sach
60 symbol cua `PROPOSAL_MICROSTRUCTURE_DATA.md` muc 2.1, dai dien thanh khoan cao/thap).
**28/28 tai thanh cong (0 fail)**. Bang trich (day du o `research/pipeline/x1/kaggle_ofi/stage_a_results.json`):

| symbol | 2022-06 monthly (nen) | 2025-06 monthly (nen) | daily 2021-08-15 | daily 2022-06-15 (dinh diem bien dong) | daily 2025-06-15 |
|---|---|---|---|---|---|
| BTCUSDT | 977.6 MB | 407.8 MB | 24.4 MB | 78.7 MB | 8.4 MB |
| ETHUSDT | 855.2 MB | 650.5 MB | 23.3 MB | 73.3 MB | 13.1 MB |
| SOLUSDT | 123.5 MB | 173.8 MB | 7.7 MB | 6.8 MB | 6.0 MB |
| ALICEUSDT | 39.6 MB | 6.4 MB | 4.6 MB | 2.2 MB | 0.16 MB |

**Phat hien quan trong**: kich thuoc DAILY bien dong rat manh theo su kien thi truong
(vd BTCUSDT 2022-06-15 = ngay Celsius khung hoang/tiep noi sup LUNA, gap 3x trung binh
thang do) — mau 1-ngay KHONG dung lam co so ngoai suy dung; phai dung TONG THANG.
Toc do tai (bang thong) do duoc: **3.53GB / 56.9s ≈ 62 MB/s** tong hop — bang thong
KHONG phai nut that. Nut that THAT su la **PARSE**: `pandas.read_csv` tren file BTC
2022-06 (74.36M dong) mat **289.1s** (≈257k dong/s); SOLUSDT 2022-06 (9.19M dong) mat
29.1s (≈317k dong/s) — o toc do nay, ca universe/window day du (uoc ~10 ty dong worst-
case) se mat **~9 gio chi rieng parse**, vuot xa ngan sach.

### 1.2 Kernel A2 — `chuyendinh/ofi-stage-a2-duckdb` (COMPLETE, ~106s)

Kiem tra gia thuyet: thay `pandas.read_csv` bang `duckdb.read_csv` + `GROUP BY` (vector
hoa, khong vat hoa dataframe muc tung dong) co nhanh hon dang ke khong. Ket qua tren
CUNG 2 file (BTCUSDT + SOLUSDT, thang 2022-06):

| symbol | download | unzip (ghi CSV ra dia) | duckdb aggregate GROUP BY gio | dong/giay duckdb |
|---|---|---|---|---|
| BTCUSDT 2022-06 | 41.6s | 27.1s | **15.7s** | 4,736,775 |
| SOLUSDT 2022-06 | 6.4s | 3.1s | **2.0s** | 4,591,850 |

**duckdb nhanh hon pandas ~18x** cho buoc aggregate (4.6-4.7 trieu dong/giay vs 257-317k
dong/giay). Tong pipeline (tai + giai nen + aggregate, KHONG giu raw — xoa ngay sau moi
file) quy ra **~0.086-0.093 giay/MB nen** (BTC: 84.4s/977.6MB=0.0863; SOL: 11.5s/123.5MB
=0.0931 — hai diem do gan nhu trung khop, dung lam co so ngoai suy).

### 1.3 Ket luan khao sat + quyet dinh phap vi

- Streaming-through (tai 1 file -> giai nen -> aggregate -> XOA raw ngay) giu dung
  luong 1 file tai mot thoi diem tren dia — **khong bao gio can toi han muc 20GB cua
  `/kaggle/working`** bat ke tong khoi luong tai ve qua toan bo vong lap, vi khong giu
  raw lau dai. Rang buoc dia KHONG phai nut that; **thoi gian** moi la nut that (dung
  duckdb, khong dung pandas o buoc aggregate).
- Universe muc tieu (`PROPOSAL_MICROSTRUCTURE_DATA.md` muc 2.1, 60 symbol) da LOAI 8
  memecoin niem yet muon theo chi dao MASTER: FARTCOIN, PIPPIN, JELLYJELLY, ZEREBRO,
  CHILLGUY, MOODENG, SWARMS, BLESS → con **52 symbol**. Voi ~0.09s/MB va uoc luong kich
  thuoc symbol-thang cho toan bo 52 symbol x 54 thang (2021-07→2025-12) trai tu ~SOLUSDT-
  tier (~150MB/thang, thanh khoan cao) den ~ALICEUSDT-tier (~10-40MB/thang, dang giam
  dan) — **uoc luong tho co the len ~100-370GB, ~3-10 gio single-thread**, VUOT nguong
  an toan 3 gio neu chay tren MOT kernel.
- Ap dung dung luat pre-reg (muc "QUYET DINH PHAM VI" cua brief): **THU HEP con 15
  symbol thanh khoan cao nhat** (theo xep hang so lenh gop trong `PROPOSAL_MICROSTRUCTURE_
  DATA.md` muc 2.1, sau khi loai 8 memecoin niem yet muon), GIU NGUYEN toan bo cua so
  thoi gian 2021-07→2025-12 (54 thang, KHONG cat ngan — vi cat ngan se pha vo tinh nhat
  quan voi 18-fold SELECT/CONFIRM da dung cho KEEP-9/HPO/FEATGRP/NOISE_CAL, va thu hep
  symbol re hon thu hep thoi gian: per-file overhead re, ma per-file THOI GIAN ti le
  THUAN voi KICH THUOC file — giam so symbol giam truc tiep tong MB can tai).
  Ly do chon THU HEP SYMBOL thay vi THU HEP THOI GIAN: chi phi (thoi gian) ti le voi
  TONG SO MB, khong phai TONG SO FILE rieng le (per-file overhead nho, ~0.1-0.5s do o
  Giai doan A) — giam so thang KHONG giam MB/thang cua moi symbol (dinh vao thanh khoan
  von co cua no), trong khi giam so symbol giam THANG DUNG ti le tong MB. Giu du 54 thang
  con giu nguyen 18-fold SELECT(0-9)/CONFIRM(10-17) dung nhu `PREREG_S1_HPO_BAG_FEATGRP.md`
  §0.3 — khong can dieu chinh ti le SELECT/CONFIRM.
- **15 symbol chot** (top-15 theo so lenh gop 2 backtest trong `PROPOSAL_MICROSTRUCTURE_
  DATA.md` muc 2.1, sau khi bo 8 memecoin niem yet muon, DUNG THU TU bang do — khong tu
  chon lai theo tieu chi khac): `AIAUSDT, PEOPLEUSDT, UNFIUSDT, ALCHUSDT, MASKUSDT,
  MYXUSDT, BLZUSDT, ALICEUSDT, COAIUSDT, EVAAUSDT, RSRUSDT, 1000PEPEUSDT, WIFUSDT,
  CHRUSDT, SOLUSDT` (symId tren Oracle theo thu tu: 525,113,77,360,101,462,53,85,531,
  544,48,166,226,83,49 — xac nhan ca 15 co trong `selector_pred_out/symbol_map.csv`).
  **Luu y da biet truoc**: mot so symId cao (525,531,544,462,360,367-style) tuc la niem
  yet TUONG DOI MUON trong lich su san — nhung KHONG bi loai (khac 8 memecoin bi loai
  tuong minh o tren) vi khong nam trong danh sach 8 cai MASTER neu dich danh; hau qua
  KY THUAT: nhung thang truoc ngay niem yet se tra ve HTTP 404 (fail nhanh, ~0.1-0.3s,
  KHONG ton thoi gian tai/parse dang ke) — tu no LAM GIAM tong khoi luong thuc te can
  xu ly so voi gia dinh "day du lich su" (bao thu ve mat thoi gian), nhung cung dong
  nghia OFI feature cua nhung symbol nay chi phu mot phan cua so 54 thang (disclose o
  muc 5 nhu mot gioi han da biet, khong phai loi).
- **Nguong dung an toan cho Giai doan B**: kernel build feature tu dat gioi han
  `OFI_SAFETY_LIMIT_SEC=3.5h` (12,600s) — neu vuot, dung giua chung SAU khi hoan tat file
  dang xu ly, ghi checkpoint da co, bao cao ro trong `RESULT_S1_FREE_OFI.md` la
  KHONG hoan tat toan bo 15x54, KHONG suy dien ket qua tu tap con neu bi cat ngang giua
  chung (chi dung khi hoan tat DAY DU 15 symbol x 54 thang, hoac neu bi cat thi bao cao
  ro pham vi thuc te da xu ly va KHONG tinh rank-IC/edge5 tren pham vi khong nhat quan
  voi 18-fold da dinh nghia).
- Uoc tinh thoi gian ky vong voi phap vi 15 symbol (dung duckdb, monthly bundle):
  15 x 54 = 810 file. Neu trung binh ~60-100MB/symbol-thang (uoc tho, giua muc
  SOLUSDT-tier va ALICEUSDT-tier, DA tinh den viec nhieu thang se la 404 nhanh do niem
  yet muon) => tong ~50-80GB => ~4,300-7,400s (~1.2-2.1 gio) cho buoc tai+build feature,
  **duoi nguong an toan 3.5h va gan voi muc tieu <3h cua brief**. Day la UOC TINH, so
  THAT se duoc ghi lai trong `RESULT_S1_FREE_OFI.md` tu `ofi_build_summary.json`.

## 2. Dinh nghia feature (chot truoc khi build)

- Nguon: `data.binance.vision/data/futures/um/monthly/aggTrades/<SYMBOL>/<SYMBOL>-aggTrades-<YYYY-MM>.zip`
  (KHONG dung daily — qua nhieu file cho cung tong MB, per-file overhead cong don khong
  can thiet; da xac nhan cau truc thu muc that o Giai doan A, khong doan URL).
- Cot dung: `price` (cot 2, KHONG dung truc tiep cho OFI — chi `quantity` va
  `is_buyer_maker`), `quantity` (cot 3, don vi = so luong coin, KHONG phai USDT notional),
  `transact_time` (cot 6, ms epoch), `is_buyer_maker` (cot 7, boolean).
- **Y nghia `is_buyer_maker`** (theo tai lieu Binance API cho aggTrade stream, field `m`:
  "Is the buyer the market maker?"; DUNG THEO CACH DIEN GIAI DA GHI SAN TRONG BRIEF NHIEM
  VU, khop voi quy uoc chuan cua Binance — moi truong sandbox cua agent nay KHONG co
  egress toi `data.binance.vision`/tai lieu Binance ngoai Kaggle nen khong the tu fetch
  lai trang docs API de doi chieu them; neu MASTER/Uni co nghi ngo, day la diem DUY NHAT
  can xac minh doc lap truoc khi tin RESULT):
  - `is_buyer_maker = true`: nguoi mua la market maker (dung lenh cho san) => nguoi BAN
    la nguoi chu dong khop lenh (taker sell) => day la **lenh ban chu dong**.
  - `is_buyer_maker = false`: nguoi mua la taker (chu dong khop) => **lenh mua chu dong**.
  - Kiem tra hop ly (Giai doan A): `aggressive_buy_ratio_sample` do tren BTC/ETH/SOL
    (thi truong thanh khoan, ca ngay) dao dong quanh **0.494-0.511** — can bang mua/ban
    xap xi 50/50 nhu ky vong cho san lon, KHONG bac bo (nhung khong PHAN BIET duoc chieu
    dinh nghia vi doi xung — chi la sanity check ve do lon, khong phai ve chieu dau).
- **OFI_1h** (moi gio, moi symbol, tu CHINH cac lenh trong gio do — KHONG rolling/smooth
  qua nhieu gio, xem giai thich lua chon o duoi):
  `ofi_1h[ts_h, sym] = (buy_vol - sell_vol) / (buy_vol + sell_vol)`
  voi `buy_vol = sum(quantity where is_buyer_maker=false)`,
  `sell_vol = sum(quantity where is_buyer_maker=true)`, `ts_h = floor(transact_time/3600000)*3600000`.
  Neu `buy_vol+sell_vol=0` (khong co lenh nao trong gio do, vd chua niem yet/da delist) =>
  `NaN` (missing — XGBoost `tree_method=hist` tu dinh tuyen missing value, khong impute).
- **aggr_buy_ratio_1h**: `= buy_vol / (buy_vol + sell_vol)`. NaN cung dieu kien tren.
- **Lua chon "khong rolling/smooth"**: brief nhiem vu vua goi day la "OFI_1h" (gia tri
  DUY NHAT moi gio, khop luoi `feat_v2_x1.parquet`) vua goi la "dang rolling" o cong thuc
  `inflate(k)`. Hai cach doc: (a) gia tri THO moi gio, hoac (b) trung binh truot nhieu
  gio/ngay cua gia tri tho. Chon **(a) — gia tri THO, khong smooth** vi day la cach doc
  SAT VAN BAN cong thuc nhat (`OFI_1h = (...) trong gio do`, khong nhac cua so nao khac),
  va vi chon mot cua so smoothing (bao nhieu gio/ngay?) se la MOT sieu tham so KHONG duoc
  chi dinh trong brief — them no vao se la mot bac tu-do chua duoc dang ky, vi pham ky
  luat "khong tune sau khi thay so". Neu vong nay NULL va MASTER/Uni muon thu ban
  rolling-smoothed, do PHAI la mot pre-reg RIENG (them tham so cua so lam k tang, hoac
  dinh nghia thanh mot nhanh rieng), khong duoc lam ngam trong vong nay.
- **k = 2** (ofi_1h + aggr_buy_ratio_1h, cung mot nhom them vao KEEP-9 mot luc, giong
  cau truc P3-featgrp cua `PREREG_S1_HPO_BAG_FEATGRP.md`). `inflate(2) = sqrt(2*ln2)
  = 1.17741...`.
- Merge vao pool: dung DUNG khoa `(ts_h, sym)` nhu moi feature khac trong `load_D()`/
  `x1_s1_rank.py` (`ts_h = (ts//H)*H`, `sym` = symId nguyen theo `symbol_map.csv`).
  Voi >600 symbol trong pool ma chi 15 co OFI, **>97% dong se co OFI_1h/aggr_buy_ratio_1h
  = NaN** — day la HE QUA TRUC TIEP cua quyet dinh thu hep pham vi (muc 1.3), KHONG phai
  loi; XGBoost hist xu ly missing tu nhien nhung do THONG TIN cua feature nay chi "song"
  o mot lat cat nho cua pool, ky vong hieu ung (neu co) se yeu hon mot phien ban co du
  universe — ghi ro trong RESULT nhu mot gioi han cua vong nay, khong phai bang chung
  chong lai gia thuyet OFI neu ket qua NULL.

## 3. Du lieu / script / moi truong (Kaggle)

| | |
|---|---|
| Noi chay | Kaggle CPU, kernel rieng, `enable_internet=true` |
| Build feature | `research/pipeline/x1/kaggle_ofi/ofi_build_feat.py` (tu chua, khong dataset input, chi internet) |
| Train/danh gia | `research/pipeline/x1/kaggle_ofi/ofi_train_eval.py` (tu chua, dataset input
  `chuyendinh/s1-featv2-x1-20260919` — CHINH file `cand_dev_x1_lite.parquet` +
  `feat_v2_x1_keep9.parquet` da dung cho vong DETERMINISM/HPO tren Kaggle — cong voi
  file OFI vua build, upload nhu mot dataset moi hoac dinh kem qua kernel-output) |
| Baseline | **TAI SU DUNG** `pred_baseline18_n1_kaggle.parquet` (edge5 = **15.209468%**,
  kernel `chuyendinh/s1-baseline18-det-n1-20260919`, COMPLETE, KEEP9, seed 42, **n_jobs=1**,
  `docs/RESULT_S1_DETERMINISM.md`) — KHONG train lai, va **TUYET DOI KHONG doi chieu voi
  baseline Oracle** (15.012825%, khac kien truc CPU aarch64 vs x86_64, lech +0.197pp
  KHONG loai duoc bang cau hinh — `docs/RESULT_S1_DETERMINISM.md` muc 4-5). |
| Hyperparameter | Y HET baseline: `XGBRanker(objective="rank:ndcg", n_estimators=300,
  max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
  min_child_weight=50, n_jobs=1, tree_method="hist", random_state=42,
  lambdarank_pair_method="topk", lambdarank_num_pair_per_sample=8)` — **n_jobs=1 bat
  buoc** (khop dung recipe cua baseline da chot, tranh them mot truc bien thien khac
  ngoai feature). |
| Nhan / purge / fold | Y HET `x1_s1_rank.py`/`s1_hpo_bag_featgrp.py`: `rel5` = ngu phan
  vi trong tick cua `g1lite - median_tick`, purge 72h, `CUTS18` (18 fold, 2021Q3→2025Q4),
  `assert tr.ts.max() < c` giu nguyen. |
| Rank-IC phu | Chi tren **`g1lite`** (KHONG co `g1_replay`/`path_labels.parquet` trong
  dataset Kaggle rut gon `s1-featv2-x1-20260919`) — do la gioi han cua bo du lieu Kaggle
  hien co, disclose ro, khong anh huong phan quyet chinh (edge5). |

## 4. Harness do luong (TAI SU DUNG nguyen ham tu `research/analysis/s1_hpo_bag_featgrp.py`,
KHONG sang tao phuong phap do moi — port sang ban Kaggle tu chua nhu
`kaggle_kernel_det/train_baseline18.py` da lam)

- **Metric chinh — edge5 OOS**: `e[ts] = mean(g1lite | rank_trong_tick(score)<=5) -
  mean(g1lite | toan tick)`, `score` THAP = TOT (dung quy uoc `x1_s1_rank.py`).
- **Metric phu — rank-IC**: `spearmanr(-score, g1lite)` moi tick co `>=10` dong.
- **CI — paired block-bootstrap khoi 72h**: `block_id = ts // (72*3600000)`, `NREP=2000`,
  `SEED=20260919`, `numpy.random.default_rng(SEED)` — dung lai CHINH XAC seed/tham so cua
  cac vong truoc (KHONG seed rieng theo ung vien).
- **inflate(k) = sqrt(2*ln k)** neu k>=2 (`k=2` cho ca candidate va noise control — xem
  muc 2). Ap quanh tam: `c=(lo_raw+hi_raw)/2, h=(hi_raw-lo_raw)/2`, CI = `[c-h*inflate,
  c+h*inflate]`.
- **THANG**: `mean>0` VA CI khong chua 0. **THUA**: `mean<0` VA CI khong chua 0.
  Con lai: **NULL**.
- **Nested SELECT(fold 0-9, 2021Q3→2023Q4)/CONFIRM(fold 10-17, 2024Q1→2025Q4)**: SELECT
  chi de tham khao (theo bai hoc `docs/PREREG_S1_NOISE_CAL.md` — SELECT la
  DIAGNOSTIC-ONLY, khong phai cong dung); **CONFIRM la cong quyet dinh duy nhat**.
  Vi chi co MOT nhom ung vien (k=2, khong phai nhieu ung vien can chon loc), "de cu"
  SELECT = chinh no (giong cau truc P2 cua `PREREG_S1_HPO_BAG_FEATGRP.md` khi k=1);
  khong co buoc chon loc giua nhieu bien the.
- **Doi chung nhieu (bat buoc)**: **1 cot nhieu moi** `noise_ofi_check` =
  `np.random.default_rng(20260920).random(n, dtype=float32)` tren dung tap dong
  `(ts_h, sym)` cua OFI feature (moi cho universe 15 symbol — merge NaN cho phan con lai
  cua pool, GIONG HET cach OFI that duoc merge, de doi chung phan anh dung dac diem
  "feature thua NaN" cua vong nay). Them vao KEEP9 lam feature thu 10, chay CUNG toan bo
  pipeline, tinh CI voi **k=2** (khop k cua candidate that — dung ngau nhien mot ngung
  khac sai muc dich doi chung).

### 4.1 Luat quyet dinh (chot truoc, KHONG doi sau khi thay so)

- **(a) Doc chung SELECT**: neu `noise_ofi_check` vuot nguong `inflate(2)*sd_boot` tren
  SELECT — **KHONG dung lai** (bai hoc `PREREG_S1_NOISE_CAL.md`: mau nho SELECT co ty le
  duong tinh gia dang ke cho MOT cot nhiep don le, o day `inflate(2)=1.1774` tuong duong
  nguong hai phia chi ~76.1% (`2*(1-Φ(1.1774))≈23.9%` xac suat bat False Positive cho MOT
  cot ngau nhien) — cao hon ca truong hop k=3 da do o NOISE_CAL (~13.8%). Vi vay SELECT
  exceed o day CANG khong duoc dung lam cong dung; chi ghi nhan de tham khao.
- **(b) Doc chung CONFIRM (cong that su)**: neu CI cua `noise_ofi_check` tren CONFIRM
  (k=2) KHONG chua 0 (tuc "exceed" o cua so quyet dinh) => **coi la harness dang nghi
  ngo** (leak/loi purge/loi join) — KHONG cong bo phan quyet THANG cho candidate that du
  no co PASS rieng, ghi ro canh bao va **DUNG dieu tra truoc khi viet RESULT ket luan**
  (khac NOISE_CAL vi o day chi co 1 cot nhieu, khong du de uoc luong ty le False Positive
  nhu 5-cot — bat ky exceed nao tren CONFIRM voi chi 1 mau deu phai duoc dieu tra nghiem
  tuc hon la coi nhu "chuyen binh thuong").
- **(c) Neu (b) khong xay ra**: phan quyet cuoi cung cua vong nay = phan quyet CONFIRM
  cua candidate that (`KEEP9 + ofi_1h + aggr_buy_ratio_1h`) theo edge5 (muc THANG/NULL/
  THUA §4). Rank-IC (g1lite) bao cao song song, khong phai luat quyet dinh.

### 4.2 Sanity bat buoc (dung neu fail)

- So tick OOS moi fold = baseline (cung `D`, cung cutoff).
- `score` khong NaN/Inf.
- `assert tr.ts.max() < c` giu nguyen moi fold.
- Tap `ts` OOS cua candidate/noise TRUNG TUYET DOI voi tap `ts` cua baseline
  (`set(P.ts.unique()) == set(baseline.ts.unique())`).

## 5. Gioi han/deviaton da biet TRUOC (disclose som, khong phai bao chua sau khi thay so)

1. OFI/aggr_buy_ratio chi phu **15/>600 symbol** trong pool (>97% dong = NaN cho 2 cot
   nay) — hieu ung neu co se bi PHA LOANG boi cach tinh edge5/rank-IC tren toan pool
   (bao gom ca cac tick ma top-5 khong co coin nao trong 15 symbol nay).
2. Trong 15 symbol, mot vai symbol niem yet TUONG DOI MUON (symId cao) => chi co du
   lieu OFI cho MOT PHAN cua 54 thang (nhung thang truoc niem yet = 404, tu dong bo qua).
3. `is_buyer_maker` duoc dien giai THEO DUNG van ban brief nhiem vu (khop quy uoc chuan
   Binance da biet), nhung KHONG the tu xac minh doc lap qua fetch tai lieu Binance API
   tu moi truong chay agent nay (khong co egress toi domain lien quan ngoai Kaggle) —
   day la mot gia dinh ke thua, khong phai da tu kiem chung lai tu dau trong vong nay.
4. OFI_1h/aggr_buy_ratio_1h la GIA TRI THO moi gio (khong smooth/rolling) — xem ly do
   lua chon o muc 2.
5. Rank-IC phu chi do tren `g1lite`, khong co `g1_replay` (gioi han dataset Kaggle rut
   gon).
6. Baseline Kaggle dung la ban **n_jobs=1** (15.209468%) — candidate/noise cung phai
   `n_jobs=1` de nhat quan; **KHONG duoc doi chieu bat ky so nao trong vong nay voi
   baseline Oracle** (15.012825% hoac 15.41% 16-fold rieng).

## 6. Ngoai pham vi (khong lam trong vong nay)

Doi nhan (`g1lite`, `rel5`), doi 18-fold cutoff, GPU, sim Java, sinh bins/dataset moi
cho production, cham du lieu 2026, tune/doi cong thuc OFI sau khi thay so, mo rong len
>15 symbol hoac >54 thang sau khi thay ket qua SELECT/CONFIRM, git push, ssh 242.

## 7. Thu tu thuc hien

1. Push kernel build feature (`ofi_build_feat.py`, an toan-dung 3.5h) — GIAI DOAN B
   (file nay) da commit truoc buoc nay.
2. Kiem `ofi_build_summary.json`: neu `stopped_early=true`, dung lai, bao cao pham vi
   thuc te trong RESULT, KHONG tinh rank-IC/edge5 tren pham vi khong khop 18-fold day du.
3. Upload `ofi_feat_x1.parquet` len Kaggle (dataset moi hoac dinh kem).
4. Chay `ofi_train_eval.py`: baseline (tai su dung, khong train lai) + candidate (1 lan
   train 18-fold) + noise (1 lan train 18-fold), n_jobs=1, seed=42.
5. Tinh harness muc 4, xuat `ofi_result.json`.
6. Ap luat quyet dinh muc 4.1. Viet `docs/RESULT_S1_FREE_OFI.md`.
7. Commit ca hai file docs + code (`research/pipeline/x1/kaggle_ofi/`) len Oracle,
   branch `module`, KHONG push.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01UoVRjusfNM2USSVNKQrm7z
