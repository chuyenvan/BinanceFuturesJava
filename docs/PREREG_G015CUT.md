# PREREG_G015CUT — tien dang ky: BO 5 FEATURE OI khoi G015 co lam kem di khong

Chot luc: 2026-09-03, **TRUOC khi train bat ky bien the nao**. Commit nay phai co truoc moi
commit ket qua. Neu thu tu commit nguoc lai => toan bo ket qua bi coi la VOID.

Pham vi: **CHI DEV**. Pool cham diem = `/home/ubuntu/ledger/cand_dev3.parquet`
(ts 2021-03-31 17:00Z .. 2024-06-30 16:45Z). KHONG cham VALIDATION (2024-07-15..2025-12-31),
KHONG cham HOLDOUT 2026. Khong chay java, khong backtest, **khong rebuild file OI**.

## 0. CAU HOI

`DATA_EXTENT_SURVEY.md` do duoc: rang buoc chat nhat cua viec keo dai du lieu la **metrics
(6 cot sinh 5 feature OI) chi co tu 2021-12-01** cho toan universe, con kline/funding co tu
2020-01. G015 dung 45 feature = 40 Tool1 (`f0..f39`) + 5 OI. Neu **bo 5 feature OI** ma G015
**khong kem di o muc do duoc**, thi DEV keo lui duoc ve 2020-01 (T 2.50 -> 4.50 nam).

Cau phu: 45 feature nay **chua tung bi cat loc** (`feataudit/SELECTOR_FEATURES.md` B.5, E5).
Co bao nhieu **NHOM** feature that su dong gop? Do theo NHOM, khong theo tung feature — vi
`CI_REAUDIT` #10 cho thay CI cua HIEU giua hai model tren cung pool la khoang **+-0.027** o
thang `rho`, nen phep so tung-feature se la "khong do duoc" gan het.

## 1. BAN G015 DUOC TAI LAP — chot cung

- Script goc: `/home/ubuntu/claudedata/gen_funding_wf_predictions_1m.py` (ban THAT da deploy).
- San pham goc dang dung: `/home/ubuntu/claudedata/predwf_G015x26/predict_wf_*.bin`
  (26B `>q h 4f`), cot `p0` = horizon 4h = `p_g015` trong ledger.
- Hyperparameter chot cung, **khong doi**: `SELECTOR_GRID_MIN=15`, label 1 chieu
  `maxFav_4h >= 0.06` (KHONG stop-loss), `nBars_4h >= 16`, WFO expanding, `OOS_MONTHS=3`,
  purge **72h wall-clock**, embargo 0, `TZ_OFFSET_MS = +7h`, XGB
  `n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
  min_child_weight=20, scale_pos_weight=(1-pos)/pos, eval_metric=auc, random_state=42`,
  OI ghep `merge_asof(on=ts, by=symId, direction=backward, tolerance=2h)`.
- Nguon du lieu (Kaggle dataset da co, KHONG upload lai, KHONG rebuild):
  `chuyendinh/funding-tool1-15m` (Tool1 T1C1), `chuyendinh/funding-label-15m` (label .pb),
  `chuyendinh/funding-oi-percoin` (`oi_percoin_full.bin` + `symbol_map.csv`).
- **File OI dung dung ban SACH**: `oi_percoin_full.bin` sha256
  `e3887f63097299655213f8382ca7e473e126ee4d7ddf69a39658942651b305ec`, 4,227,723,300 B
  (khop `OI_FIX_LOG.md` canh bao van hanh). Kernel PHAI log lai sha256 cua file no doc va
  so voi hash nay; lech => VOID. **Khong rebuild file OI** (code repo se tao leak 5 phut).

### 1.1 Hai sai lech co y so voi ban goc — khai bao TRUOC

1. **Chi train 10/16 fold.** Ban goc co 16 cutoff (20220101..20251001). Cutoff >= 20240701
   roi vao VALIDATION => **cam**. Job nay train dung 10 fold DEV:
   `20220101, 20220401, 20220701, 20221001, 20230101, 20230401, 20230701, 20231001,
   20240101, 20240401` (GMT+7). Do dung la tap fold sinh ra 15,442,092 dong co `p_g015`
   trong `cand_dev3.parquet` (`research/pipeline/ledger3.py:26-28` loai 20240701/20241001).
   => moc 0.1675 **do duoc tai lap y nguyen** bang 10 fold nay.
2. **`device="cuda"`** thay vi CPU `tree_method=hist` cua ban goc. GPU va CPU dung sketch khac
   nhau nen cay khong trung tung byte. Day la ly do phai co buoc TAI LAP (§5) — neu `full45`
   khong khop 0.1675 thi moi phep so sau do vo nghia va job DUNG.

## 2. M BIEN THE — DONG BANG, khong them khong bot

Feature index: `f0..f39` = Tool1 (thu tu `ExportFeaturesForPythonTool.convertFeaturesToArray`),
`oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy` = 5 OI (thu tu `OI_NAMES`).

Nhom chia theo `FEAT40_LOOKAHEAD.md` Cau 2:

| nhom | feature | n |
|---|---|---|
| BTC / toan thi truong | f0 f1 f2 f3 f4 f5 | 6 |
| momentum & vi tri gia cua coin | f6 f7 f8 f10 f28 f29 f31 f35 | 8 |
| ky thuat / bien dong | f9 f11 f30 f36 f38 f39 | 6 |
| basket | f12 f13 f14 f15 f16 | 5 |
| funding | f17 .. f25 | 9 |
| volume | f26 f27 f37 | 3 |
| rank cross-sectional | f32 f33 f34 | 3 |
| **OI** | 5 feature OI | 5 |

**M = 9 bien the** (8 phep so hieu, tat ca so voi `full45`):

| # | ten | tap feature | n feat | vai tro |
|---|---|---|---|---|
| 1 | `full45` | 40 Tool1 + 5 OI | 45 | **moc / tai lap** |
| 2 | `no_oi` | 40 Tool1 | 40 | **GIA THUYET CHINH** |
| 3 | `noise46_a` | full45 + 1 cot nhieu iid N(0,1) seed 101 | 46 | **doi chung am A** |
| 4 | `noise46_b` | full45 + 1 cot nhieu iid N(0,1) seed 202 | 46 | **doi chung am B** |
| 5 | `no_funding` | full45 bo f17..f25 | 36 | nhom lon nhat, va la nhom bi anh huong neu keo dai du lieu (f21/f22 la percentile/z expanding) |
| 6 | `no_basket` | full45 bo f12..f16 | 40 | **cung co 5 feature bi bo nhu `no_oi`** => hieu chuan "bo 5 feature nhom khac thi mat bao nhieu" |
| 7 | `no_xsec` | full45 bo f32 f33 f34 | 42 | rank cross-sectional chay tren rank-space 80 symbol o 2020 vs 379 o 2024 => neu khong dong gop thi rui ro keo dai giam |
| 8 | `no_oi_no_xsec` | 37 feature | 37 | tap "san sang 2020" that: bo ca OI lan rank cross-sectional |
| 9 | `oi_only` | 5 OI | 5 | do lieu 5 feature OI mang bao nhieu tin hieu KHI DUNG MOT MINH |

Cot nhieu: `np.random.default_rng(seed).standard_normal(n_rows)` sinh 1 lan theo thu tu dong
cua ma tran feature, dung y nguyen cho moi fold (khong sinh lai moi fold).

**Ngan gian lan chon do dai:** M = 9 dong bang o day. Khong duoc them bien the sau khi thay
ket qua. He so hieu chinh boi so: `k = sqrt(2 * ln M) = sqrt(2 * ln 9) = 2.0957`.
Khoang tin cay bao cao cho MOI phep so la **CI da noi rong**:
`d +- k * sd_boot` (dung k = 2.0957 thay cho 1.96). Noi rong lam **kho** ket luan tuong duong
hon — dung huong bao thu cho cau hoi cua job nay.

## 3. THUOC DO

### 3.1 Chinh — `rho`

`rho = spearman(p_variant, g1lite)` tren **dung 15,442,092 dong** cua `cand_dev3.parquet`
co `p_g015` khong NaN va `g1lite` khong NaN (join theo `(ts, sym)`).
Moc hien tai da tai lap duoc trong job nay truoc khi chot pre-reg (chi la kiem ton tai du lieu):
`rho = 0.16752`, theo nam `2021 0.1807 (n=3612) / 2022 0.1570 / 2023 0.1647 / 2024 0.1985`,
don dieu 20/20 bucket. Neu mot bien the khong phu du 15,442,092 dong => VOID bien the do.

### 3.2 Phu 1 — tinh don dieu

`mono20` = ty le buoc tang trong 20 bucket `qcut` cua `p` theo `mean(g1lite)` (y `lpm.py:mono20`).
`full45` phai ra 20/20 (= 1.00). Nguong cho bien the: **>= 0.95 (19/20)**.

### 3.3 Phu 2 — admit-rate + chat luong hang admit (thuoc do VAN HANH)

Day la thuoc do quan trong hon `rho` toan pool, vi G015 chi cap `score` cho GATE:
`score = 1 - p`, `dyn_thr = MIN_MOMENTUM_15M * max(AI_DYNAMIC_MIN, score/RATE_MAX*MULT)`,
`admit <=> p15 >= dyn_thr` (chi co can duoi, `research/analysis/gate_cfg.py`).
Hang so c2b chot cung: `MIN_MOMENTUM_15M=0.008, AI_DYNAMIC_MIN=0.26787, MULT=1.2876,
RATE_MAX=0.15`, khong co tran.

Do tren `full45` (moc, da tai lap): `n_admit = 30,854`, `admit_rate = 0.00200`,
`quality = mean(g1lite | admit) = 0.10661` so voi `pool mean = 0.01399`.

Bao cao 2 dang, ca hai chot truoc:
- **(a) native**: `admit_rate` va `quality` tai nguong that cua tung bien the.
- **(b) ghep so luong (matched-count)**: nhan `dyn_thr` cua bien the voi mot he so `c` tim mot
  lan tren toan pool sao cho `n_admit(c) = n_admit(full45)` (tim bang bisection, sai so <= 0.5%
  so dong), roi so `quality`. Bat buoc co (b) vi (a) tron lan hai thu: xep hang tot hon va
  **thang do tuyet doi cua p bi troi**. `c` duoc **dong bang** truoc bootstrap (y logic
  `PREREG_CI` section 3.4 dong bang `random8`).

### 3.4 Cai KHONG do

Khong tinh CAGR, khong maxDD, khong backtest. Moi phat bieu ve tang equity nam ngoai job nay.

## 4. CI — block-bootstrap, ghep cap

Theo `PREREG_CI.md` section 3:
- Don vi resample = **khoi 72h wall-clock**: `block_id = floor((ts - ts_min) / 72h)`.
  Chinh **72h**; kiem do ben **24h** va **168h**.
- `N_REP = 2000`, `SEED = 20260903`, `rng = numpy.random.default_rng(SEED)` khoi tao lai tu seed
  do cho tung (thuoc do, do dai block) => khong phu thuoc thu tu chay.
- **Ghep cap bat buoc**: moi rep sinh MOT danh sach khoi; danh sach do dung cho CA `full45` va
  bien the; CI la CI cua **HIEU** `d`. Cam so hai CI rieng.
- CI95 = phan vi 2.5 / 97.5 (percentile). Bao cao thanh `d +- k*sd_boot` (§2) lam khoang quyet dinh,
  va bao cao ca CI percentile tho de doi chieu.

**Xap xi tinh `rho` trong bootstrap (chot truoc):** rank `p` va `g1lite` **MOT LAN** tren toan
pool (average rank), sau do moi rep tinh **Pearson cua rank da dong bang** bang tong du thong ke
theo khoi (`n, Sx, Sy, Sxx, Syy, Sxy`). Ly do: 2000 rep x spearman tren 15.4M dong la khong kha
thi. `CI_REAUDIT` section B (kiem chung #10) da dung dung cach xap xi kieu nay va doi chieu voi
bootstrap tho. **Bat buoc kiem chung lai o job nay**: chay lai 200 rep bang cach tinh spearman
THAT tren dong resample, va so `sd`. Lech `sd` > 20% => xap xi bi loai, phai bao "khong do duoc".

Admit quality la ty so tong (`sum(g1lite | admit) / n_admit`) => bootstrap theo khoi bang tong du
thong ke `(n_admit_b, sum_b)`, chinh xac tuyet doi (khong xap xi).

## 5. DIEU KIEN CHOT — quyet dinh TRUOC khi thay so

### 5.1 Cong tai lap (chan tren cua moi thu)

**PASS** neu `|rho(full45) - 0.1675| <= 0.010`.
**MARGINAL** neu `<= 0.019` (= 1 sd cua muc `rho`, `CI_REAUDIT` do `sd(rho_G015) = 0.01901`):
bao cao nhung ghi ro co lech.
**FAIL => DUNG JOB**, bao "khong tai lap duoc", khong bao cao bien the nao.

### 5.2 Doi chung am (bat buoc, chan thu hai)

Voi ca `noise46_a` va `noise46_b`: `|d_rho| < 0.010` **VA** CI noi rong cua `d_rho` **chua 0**.
Neu mot trong hai co tac dung do duoc => **pipeline do SAI, DUNG, sua**.
`max(|d_rho(noise_a)|, |d_rho(noise_b)|)` duoc dung lam **san nhieu quy trinh**: moi hieu nho hon
san nay khong duoc goi la "co that" bat ke CI.

### 5.3 "BO DUOC 5 FEATURE OI" — hop dong tuong duong

Le tuong duong (non-inferiority margin), chot truoc:
- `Delta_rho = 0.010` tren `rho`.
- `Delta_adm = 0.0050` tuyet doi tren `quality` (mean `g1lite` hang admit), o dang **ghep so luong**.

Giai thich chon so:
- `Delta_rho = 0.010` = **6.0%** cua moc 0.1675. No nho hon **do rong theo nam** cua chinh thuoc
  do (0.1570..0.1985, bien do 0.0415) => mot dich 0.010 nam trong bien dong ma van hanh khong
  bao gio phan biet duoc. No cung nho hon nhieu `+-0.027` (nua do rong CI hieu giua hai model
  khac nhau, `CI_REAUDIT` #10) => **chi chung minh duoc khi phep ghep cap that su hoat dong**;
  do la mot phep kiem chinh phuong phap, khong phai ke ho.
- `Delta_adm = 0.0050` chon theo `CI_REAUDIT` #8: toan bo gia tri xep hang da chung minh duoc o
  cua gate la `g1_replay` top8 - random8 = **+0.0182, CI [+0.0085, +0.0227]**. `0.0050` = **59%**
  cua chan duoi dang tin nhat (0.0085) — nghia la muc dung sai nay **khong the am tham an het**
  phan edge da chung minh. Chat hon (vd 0.002) thi voi `n_admit` chi 30,854 dong se khong bao gio
  do duoc; long hon (vd 0.01) thi cho phep mat hon nua edge => 0.0050 la diem can bang chot truoc.
- Bang bien do bo sung bat buoc bao cao (khong doi quyet dinh chinh):
  `Delta_rho in {0.005, 0.010, 0.020}` — de nguoi doc thay ket luan phu thuoc le the nao.

**BO DUOC** khi va chi khi **TAT CA** dung:
- (A) `d_rho = rho(no_oi) - rho(full45)`: **chan duoi cua CI noi rong** (`d - 2.0957*sd_boot`)
  **> -0.010**, o **CA BA** do dai khoi 24h / 72h / 168h.
- (B) `mono20(no_oi) >= 0.95` va `rho(no_oi) > 0` o ca 4 bucket nam.
- (C) `d_adm` (ghep so luong): chan duoi CI noi rong **> -0.0050**; VA `admit_rate` native cua
  `no_oi` nam trong `[0.001, 0.004]` (= 0.5x .. 2x cua 0.00200). Ra ngoai bang do khong phai
  "kem" nhung co nghia la **thang do `p` bi troi** => gate phai hieu chuan lai, va do la mot chi
  phi phai bao cao ro, khong duoc bo qua.
- (D) doi chung am §5.2 PASS.
- (E) cong tai lap §5.1 PASS.

**KHONG BO DUOC** khi CI noi rong cua `d_rho` nam **hoan toan duoi** `-0.010` (o do dai khoi
chinh 72h) hoac `d_adm` nam hoan toan duoi `-0.0050`.

**KHONG KET LUAN DUOC** trong moi truong hop con lai. **Dac biet**: neu
`2.0957 * sd_boot >= 0.010` thi khoang qua rong de chung nhan tuong duong **bat ke diem uoc luong
la bao nhieu** — ket qua la "KHONG KET LUAN DUOC", **KHONG** phai "bo duoc".

## 6. CAM BAY PHAI GHI — doc truoc khi doc ket qua

1. **Day la phep kiem TUONG DUONG, khong phai kiem khac biet.** "CI chua 0" o phep kiem khac biet
   nghia la "khong chung minh duoc co khac nhau" — no **KHONG** dong nghia "giong nhau". Muon noi
   "khong kem di" phai chi ra CI **nam tron** trong `(-Delta, +inf)`. Vi vay **CI hep la DIEU KIEN**
   de ket luan co nghia. CI rong => "khong ket luan duoc". Day la cam bay so 1 va da lam sai o
   nhieu cho trong repo nay (xem `CI_REAUDIT` muc "Verdict cu co phai sua").
2. **Bo feature KHAC keo dai du lieu.** Chung minh `no_oi ~ full45` tren **2022-2024** KHONG
   chung minh model 40 feature train tren **2020-2024** se tot. Keo lui doi thang ba thu nua:
   (i) universe 80 symbol (2020) vs 379 (2024) => f3/f4/f5/f32/f33/f34 doi rank-space;
   (ii) f21/f22 (`fundingPercentileCoin`, `fundingZCoin`) la percentile/z **expanding** => them
   2020-2021 doi **phan phoi tham chieu** cua chinh 2 feature do cho toan bo giai doan sau;
   (iii) che do 2020-2021 (vol 76-81%, 1 ngay -40%, funding p99 +15.85bp) chua tung co trong DEV.
   `DATA_EXTENT_SURVEY` muc 4 da do ba thu nay. Ket luan cua job nay chi la **dieu kien can**
   (bo OI khong mat gi tren doan co OI), khong phai dieu kien du.
3. **`rho` toan pool khong phai thuoc do van hanh.** Gate chi admit **0.200%** pool. Mot bien the
   co the giu `rho` ma xep sai o dung vung nguong. Do la ly do co §3.3, va la ly do
   `d_adm` co quyen phu quyet doc lap voi `d_rho`.
4. **`n_admit` chi 30,854 dong tren ~300 khoi 72h** => `sd_boot` cua `d_adm` se lon. Rat co the
   dieu kien (C) roi vao "khong ket luan duoc" ngay ca khi (A) dat. Neu vay phai bao cao dung nhu
   vay, khong duoc ket luan bang (A) mot minh.
5. **Doi chung am khong the ra "d = 0 chinh xac".** `colsample_bytree=0.8` nghia la them 1 cot
   nhieu **co doi** cay duoc sinh. Do la co y: `d(noise)` do dung **san nhieu cua quy trinh**.
6. **Xap xi frozen-rank** (§4) phai duoc kiem chung; neu khong khop bootstrap tho thi khong duoc
   dung. Ghi ro neu phai bo.
7. **Boi so:** k = 2.0957 ap cho **moi** phep so bao cao. Khong duoc bao cao mot phep so nao voi
   1.96 roi goi la "SONG".

## 7. THU TU THUC HIEN — bat buoc

1. Commit file nay. Ghi lai commit hash.
2. Chi sau do moi chay train (Kaggle GPU, 1 slot, `g015-*`).
3. Tai lap `full45` truoc (§5.1). FAIL => dung, bao.
4. Doi chung am (§5.2). FAIL => dung, sua pipeline.
5. Chay 6 bien the con lai. Moi diem ket qua ghi 1 dong jsonl + `fsync` ngay.
6. Tinh CI (§4), bao cao theo §5.
7. Neu `no_oi` dat: tinh `MDE80` voi `T = 4.5` nam bang cong thuc **da chot** o
   `DATA_EXTENT_SURVEY` muc 3 (`MDE80(T) = z * sd_dev * sqrt(T_dev/T)`, `z = 2.80158`,
   `T_dev = 2.4941` nam), va neu ro he qua cho **S1** (S1 cung co 2 feature OI —
   `oi_delta24h` rank + `ls_global`; `feataudit` do la khong dong gop).

## 8. NHUNG GI PRE-REG NAY KHONG LAM

- Khong rebuild file OI, khong sua `VisionMetricsClient`, khong tai them du lieu.
- Khong ghi de `predwf_G015*`, `predwf_map_s1a2/`, `ledger/pred_s1a2.parquet`,
  `featv2/feat_v2.parquet`. Output ra `/home/ubuntu/g015/`.
- Khong train S1, khong sinh lai bins, khong chay backtest => khong phat bieu gi ve CAGR.
- Khong quyet dinh co keo dai du lieu hay khong. Job nay chi tra loi **dieu kien can**.
- Khong sua `docs/PREREG_*.md` cua nguoi khac.
