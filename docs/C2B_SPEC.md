# C2b — DAC TA DAY DU (ban viet lai 2026-09-04)

Ban truoc cua file nay ghi `PROFILE_HASH=1bc17b5075511263` / `CONFIG_HASH=28f7c17882b0b339` /
"22 key" va huong dan §10 kiem theo hai hash do. **Ca ba deu da lac hau** — lam theo se ra FAIL
gia. Ban nay do lai truc tiep bang `DumpConfig` ngay 2026-09-04.

## 0. DANH TINH — do lai 2026-09-04

| | gia tri |
|---|---|
| profile **baseline** | `profiles/c2b_min.properties`, **16 key**, `PROFILE_HASH=a2f859b2463108fe` |
| profile lich su | `profiles/c2b.properties`, **23 key**, `PROFILE_HASH=7fd2895a1e7fefe0` |
| `CONFIG_HASH` | **`f79ddd824eafb978`** (c2b va c2b_min) · `4499f72932023a39` (c2c_round) |
| config nen | `configs/sim_dev.properties` |
| bins selector | `predwf_map_s1a2` — 10 file, 403,940,914 B, `sha256_16=0f8721558fbd87ef` |
| runner chuan | `tools/run_c2b_dev.sh` (default da chuyen sang `c2b_min` ngay 2026-09-04) |

**Anh xa hash — phai nho:** `7fd2895a1e7fefe0` (23 key) va `a2f859b2463108fe` (16 key) la
**CUNG MOT hanh vi**, da chung minh **byte-identical** hai lan (`docs/C4_RESULT.md`). 7 key khac
biet gom **5 key khong ai doc** (`DISABLE_PREDICT_SYMBOL`, `HARD_STOP_LOSS_RATE`,
`TIME_STOP_HOURS`, `TS_GAP_CONST`, `TS_MIN_GAP`) va **2 key duoc doc nhung TRO ve hanh vi**
(`NUMBER_ORDER_BUDGET`, `DCA_GRID_LEVELS`).

## 1. LUONG QUYET DINH — va "rang buoc binding" nghia la gi

Moi phut, moi (tick, symbol) ung vien phai qua **bon** cua. Ghi ro cua nao chat, cua nao long:

```
[1] SELECTOR   top-8 theo thu hang S1        -> con 8 coin / tick
[2] GATE t1    tran ung vien 0.32120          -> BI BO QUA (vi TOPK=8 > 0)
[3] GATE t2    pred15m >= dyn_thr             -> tu choi 94.5% phut-ung-vien
[4] VON        can budget de mo lenh          -> tu choi 0 dong
```

Do duoc (`docs/TICKLOG_RESULT.md`, tren tung **phut-ung-vien**):

| cua | ket qua | co chat khong? |
|---|---|---|
| `GATE_REJECT` (cua 3) | **94.5%** | **CHAT — day la cua duy nhat chat** |
| `NO_BUDGET` (cua 4) | **0 dong** | long hoan toan |
| breaker / so lenh dong thoi | `SIM_BREAKER_MODE=OFF`; doi `MAX_CONCURRENT` 40 -> 25 ra `printDone` **trung tung byte** | tro trong sim |

Bang chung phu: he giu **1.83 vi the trung binh**, **62.5% so gio khong giu gi**, max 29 dong
thoi, trong khi tran margin theo `U_MAX` cho phep **21,000** (~20 vi the o ~1,000/lenh).

**"Binding" nghia la:** neu **noi cua 3** thi he vao them lenh; neu **them von** thi he vao
**khong them mot lenh nao**. Do la ly do moi de xuat co gia tri co hoc deu phai di qua gate.

⚠️ **Nhung "binding" KHONG dong nghia "noi ra thi lai hon".** Da thu, va thua:

| phep thu | ket qua |
|---|---|
| `SIM_MIN_MOMENTUM_15M` 0.008 -> 0.006 (`K0_h1a_prof`, nen C2b) | b:**59,580** < 60,390; maxDD **-21.0%** vs -13.1%; 2022 rot +11.6 -> +4.5 |
| `PREDICT_SYMBOL_RATE_MAX` 0.15 -> 0.30 (`H1b`) | b:**47,143**, maxDD **-44.3%**, 2022 **-31.6%** |
| ca hai (`H1c`) | b:**37,145**, maxDD **-51.3%** |
| B4 rolling-percentile gate, 3 bien the | **0/3** vuot nguong, ca 3 diem uoc luong am |
| breaker MARGIN de cuu DD khi noi gate (`BR3`) | DD -21.0 -> **-20.9** — gan nhu khong nhuc nhich |

=> Gate **dang chat VA dang o cho tot** o **muc do lon cua nguong**. Noi nguong = nhap lenh xau
cua rieng 2022. `BR3` cho biet DD do noi gate **khong** den tu mo qua nhieu lenh ma tu **gia chay
nguoc tren lenh da mo** — khong co co che phoi nhiem nao thay duoc **tin hieu regime**.

**Cai CHUA thu, va la cho duy nhat con ly do co hoc:** doi **HINH DANG** cua gate, khong phai do
lon. Hien `dyn_thr` duoc tinh tu `symbolPred` = gia tri P(win) **tuyet doi cua G015x26**, trong khi
**thu hang** lai do **S1** quyet (`build_map.py:28` giu nguyen multiset P(win) per-tick cua G015x26,
chi doi coin theo hang S1). Tuc **nguong dang so voi thang do cua mot model khac**. Hieu chuan
nguong theo **phan vi/thu hang cua chinh S1** la phep **chua ai lam**.

⚠️ Rang buoc do luong: moi thi nghiem gate phai cham o **tang xep hang**. Tang equity thi vo vong
(NBETS: can 14-43 nam DEV cho 3pp). Va `docs/COV_RESULT.md` vua do: tap **gate MO** chi co
**48-67 ngay / 39-52 khoi co du lieu**, `H0` iid cua no **chom truot kiem phu o moi do dai khoi**
=> ke ca khong co phu thuoc nao, bootstrap tren tap nay **cung khong dat 95%**. Muon do gate chac
hon thi phai **them tick gate MO**, khong mua duoc bang doi do dai khoi.

## 2. SELECTOR — model S1

| | |
|---|---|
| thuat toan | `xgboost.XGBRanker`, `objective=rank:ndcg`, `lambdarank_pair_method=topk`, `lambdarank_num_pair_per_sample=8` |
| tham so | `n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, min_child_weight=50, n_jobs=4, tree_method=hist, random_state=42` |
| group (qid) | `pd.factorize(ts, sort=True)` — **1 tick 15m = 1 nhom** |
| nhan | `rel5 = min(int(rank_pct(rel) * 5), 4)`, `rel = g1lite - median_tick(g1lite)` |
| WFO | 10 cutoff `20220101..20240401` (GMT+7), OOS 3 thang, **purge 72h**, `assert tr.ts.max() < cutoff` |
| output | `score = -pred` => **score THAP = TOT** (`s1_rank.py:50`) |
| moi truong | xgboost 3.2.0, **CPU** — Oracle hoac Kaggle deu duoc (byte-identical, xem §2.4) |

### 2.1 Nhan — doc cho dung

Nhan **khong** phai lai/lo tuyet doi. No la **ngu phan vi TRONG TICK** cua `g1lite` sau khi tru
trung vi cua chinh tick do. Nghia la S1 hoc **"coin nao tot HON cac coin khac cung thoi diem"**,
khong hoc "coin nao se lai". Do la ly do:

- moi phep danh gia S1 phai la **rank-IC theo tick**, khong phai IC gop;
- va la ly do `build_map` chi can **thu hang** cua S1, khong can gia tri.

`g1lite` la nhan trung gian; tuong quan voi ROI that: `g1lite 0.584 > maxFav 0.574 >
g1_replay 0.507` (`AUDIT_APPLIED` A11) — do la ly do giu `g1lite` lam nhan **train**, nhung
**doi thuoc DANH GIA sang `g1_replay`** (§3.3).

### 2.2 Chin feature — cong thuc that

`P_t` = close 1h; `R1` = loi suat 1h; moi rolling deu **lui**. "rank trong tick" =
`rank(axis=1, pct=True)` giua cac coin cung moc gio (`feat_v2_build.py:104-105`).

| # | ten | cong thuc | cua so | nguon |
|---|---|---|---|---|
| 1 | `vol_7d` | `std(R1)`, `min_periods=84` | 168h | `CLOSES_1H.bin` |
| 2 | `dd_7d` | `P_t / max(P,168h) - 1` (<= 0) | 168h | `CLOSES_1H.bin` |
| 3 | `rk_dd_7d` | rank trong tick cua `dd_7d` | 168h + cross-sec | `CLOSES_1H.bin` |
| 4 | `hrs_since_high_7d` | `(168-1-argmax(P,168h))/168` in [0,1] | 168h | `CLOSES_1H.bin` |
| 5 | `ret_3d` | `P_t / P_{t-72h} - 1` | 72h | `CLOSES_1H.bin` |
| 6 | `rk_ret_3d` | rank trong tick cua `ret_3d` | 72h + cross-sec | `CLOSES_1H.bin` |
| 7 | `ret_14d` | `P_t / P_{t-336h} - 1` | 336h | `CLOSES_1H.bin` |
| 8 | `ls_global` | ty le long/short toan cau, asof `<= t`, tol 2h | snapshot | `oi_percoin_full.bin` |
| 9 | `rk_oi_delta24h` | rank trong tick cua `oi(t)/oi(t-24h)-1` | 24h + cross-sec | `oi_percoin_full.bin` |

**Lech thoi gian co y:** feature tinh o **moc GIO**, quyet dinh o **tick 15m**, join bang
`ts_h = (ts//3600000)*3600000` => feature co the **cu toi 45 phut**. Lech theo huong **bao thu**,
khong phai ro ri.

**Chi 3 nguon du lieu**: `CLOSES_1H.bin` (7 feature) va `oi_percoin_full.bin` (2 feature).
Funding **duoc tinh trong `feat_v2.parquet` nhung KHONG feature nao cua S1 dung**.

### 2.3 Quantile-map — cho de nham nhat cua ca he

`build_map.py`: trong **tung tick**, cac coin co score nhan lai **chinh tap gia tri `p` cua
G015x26 trong nhom do**, gan theo thu hang score cua S1. Coin khong co score giu `p` cu.
=> **phan phoi P(win) theo tick GIU NGUYEN cua G015x26**; bins **chi phu thuoc THU HANG** cua S1.
Ti le `changed` = **4.9%**.

Hai he qua that:
1. **S1 quyet ai duoc chon; G015x26 quyet nguong gate cao bao nhieu.** Doi S1 khong doi
   admit-count; doi G015x26 thi doi ca he.
2. `symbolPred` ma exit dung de chia STRONG/WEAK (§5) **la gia tri G015x26**, khong phai diem S1.

### 2.4 Device: CPU o dau cung duoc; GPU chi de quet

Do 2026-09-05, 3 moi truong x 3 seed tren cung mot file da dong bang (hash khop tuyet doi):
`docs/BENCH_DEVICE.md`, script `research/kaggle/bench_device/`.

| cap | per-tick `mean\|dIC\|` | `\|d mean rank-IC\|` | `\|d edge5\|` |
|---|---|---|---|
| Oracle CPU vs **Kaggle CPU** | **0.00000** | **0.00000** | **0.000pp** |
| CPU vs **Kaggle GPU** | 0.02185 | 0.00448 | 0.198pp |
| *nen between-seed (chi CPU)* | *0.01824* | *0.00121* | *0.164pp* |

**Kaggle CPU tai lap Oracle CPU byte-for-byte** (`ic_sha256` trung ca 3 seed, cay dau tien
trung sha256), du khac arch/python/numpy => S1 duoc train o bat ky dau tren CPU. So cu
`0.17040 vs 0.1723` la lech du lieu, khong phai lech may.

**GPU** (`device="cuda"`) khong tuong duong: `Cover` lech 31/31 node (RNG lay mau khac),
`Split` lech 11/31 (quantile sketch khac). Per-tick va `edge5` van nam trong nhieu seed,
nhung `mean rank-IC` lech **x3.7** nen seed cua CPU va GPU tu no nhieu gap **4.8 lan**.
=> GPU chi dung de QUET, **ca phep so phai cung tren GPU**, bao cao kem **CI >= 3 seed**.

**Cong `spearman >= 0.999` da bo.** Do lai dung thong ke do tren 774,270 dong OOS:
CPU-vs-GPU cung seed = **0.9813**, CPU seed42-vs-seed43 (cung may, cung device) = **0.9817**.
Doi device ton dung bang doi seed; nguong 0.999 loai ca viec re-seed mo hinh, nen no khong
phai bang chung ve moi truong. Thay bang **CI multi-seed do trong cung moi truong**.
Van giu: khong ghep so tu hai moi truong trong mot so sanh; parity/byte-identity phai chay
tren dung device sinh ra neo; Java sim o lai Oracle (data host + neo 60390).

## 3. BANG CHUNG VE BO FEATURE — feature nao that su ganh

Nguon: `/home/ubuntu/feataudit/SELECTOR_FEATURES.md` (2026-09-03), tai lap S1 truoc khi do
(spearman(pred moi, deploy) = **1.0000** tren 774,270 dong, `edge5 = +6.8043%` vs goc +6.80%).
`n_eff = 248 khoi 72h`. **YYY** = CI loai tru 0 o ca 3 do dai khoi; **nnn** = chua 0 o ca 3.

### 3.1 Ranker chi nhin thay 7 tin hieu, khong phai 9

Tuong quan hang **TRONG TICK** (`c2_corr_within_tick.csv`):

| cap | rho trong tick | ban chat |
|---|---|---|
| `dd_7d` – `rk_dd_7d` | **+1.000** | **dong nhat TOAN HOC** (`rk_*` duoc dinh nghia la rank cua `*`) |
| `ret_3d` – `rk_ret_3d` | **+1.000** | **dong nhat TOAN HOC** |

Cay XGBoost chia theo nguong **tuyet doi** nen ban tho (`dd_7d = -0.35`) van mang thong tin
**giua cac tick** ("ca thi truong dang sut bao nhieu") ma ban rank khong co. Nhung o **tang xep
hang trong tick** thi chi mot trong hai co tac dung.

### 3.2 Permutation importance theo NHOM (bang quyet dinh that)

Tron ca nhom cung luc de tranh hieu ung che lap. Hai thuoc do:
`g1lite` (nhan train) va `g1_replay` (mo phong **dung luat exit G1**).

| nhom | dIC vs `g1lite` | YYY? | dIC vs `g1_replay` | YYY? |
|---|---|---|---|---|
| **`dd_7d` + `rk_dd_7d`** | **+0.0520** | **YYY** | **+0.0183** | **YYY** |
| **`ret_14d`** | **+0.0323** | **YYY** | **+0.0122** | **YYY** |
| `vol_7d` | +0.0244 | YYY | **+0.0009** [-0.0064,+0.0079] | **nnn** |
| `ret_3d` + `rk_ret_3d` | +0.0059 | YYY (be) | **-0.0050** [-0.0096,-0.0006] | **YYY, AM** |
| **ca 2 feature OI** | +0.0036 | nnn | +0.0002 | nnn |
| `hrs_since_high_7d` | -0.0002 | nnn | -0.0001 | nnn |

**Doc:** dung **HAI** khoi tin hieu dong gop tren ca hai thuoc — **drawdown 7 ngay** va
**`ret_14d`**. `vol_7d` chi giup **doan dung nhan**, chua chung minh giup kiem tien.
**Cap momentum 3 ngay LAM HAI** tren thuoc sat thuc te. **Ca hai feature OI khong phan biet duoc
khoi 0** — truoc ca khi tinh viec chung dang bi ro ri 5 phut.

### 3.3 Ket luan dao chieu khi doi outcome — ly do phai doi thuoc

| outcome | S1 (9 feat) | G015 | `vol_7d` tho | S1 - `vol_7d` (CI72) | doc |
|---|---|---|---|---|---|
| `maxFav_72h` | 0.2458 | 0.1638 | **0.2959** | **-0.0502** [-0.0651,-0.0363] YYY | `vol_7d` thang |
| `g1lite` (nhan train) | 0.1723 | 0.1009 | **0.1933** | **-0.0210** [-0.0374,-0.0045] YYY | `vol_7d` thang |
| `g1_replay` (exit that) | **0.0418** | 0.0208 | 0.0315 | +0.0103 [-0.0037,+0.0248] nnn | ngang nhau |
| `retEnd_72h` (lai cuoi ky) | **-0.0177** | -0.0207 | **-0.0405** | **+0.0228** [+0.0044,+0.0410] YYY | **S1 thang** |

Ba dieu nay phai ghi thang:
1. **Xep coin theo dung MOT feature `vol_7d` tho con hon model 9 feature** tren `g1lite`
   (-0.0210, YYY) va `maxFav_72h` (-0.0502, YYY). `g1lite` **thuong bien do**.
2. Cai 9 feature lam tot hon `vol_7d` **khong** phai "chon coin bat manh" ma la
   **"chon coin khong quay dau"** — dung cho `retEnd_72h`, va dung cho noi exit trailing kiem tien.
   Khop sim that: doi chung `vol_7d` chay ra **b:41,876** vs S1 **b:50,891**.
3. **Khong model nao xep hang duoc `retEnd_72h`** (S1 -0.0177, CI chua 0). Toan bo edge selector
   nam o **hinh dang duong gia**, khong o loi suat cuoi ky.

### 3.4 Tran cua bo feature — du dia con lai KHONG o model

Tran = xep theo `g1lite` **that** (oracle) roi lay top-5 => `edge5 = +38.34%`.

| model | edge5 `g1lite` | % tran bat duoc | CI |
|---|---|---|---|
| **S1 (9 feature)** | +6.80% | **17.8%** | [13.1%, 22.4%] |
| S1 bo `hrs_since_high` (8) | +6.92% | 18.0% | [13.3%, 22.6%] |
| S1 bo them `dd_7d` (7) | +6.94% | 18.1% | [13.1%, 22.9%] |
| G015 (45 feature) | +4.55% | 11.9% | — |
| **doi chung: xep theo `vol_7d` tho** | **+7.59%** | **19.8%** | [14.1%, 25.0%] |
| random | +0.14% | 0.4% | — |

=> Khoang trong 80% tro len **khong phai du dia cua model tren bo feature nay** — vi mot feature
duy nhat da dat xap xi cung muc. No la du dia cua **thong tin moi**.

### 3.5 Train lai voi bo nho hon — da do

| model | feature | rank-IC `g1lite` | rank-IC `g1_replay` | edge5 `g1lite` | edge5 `g1_replay` |
|---|---|---|---|---|---|
| **du 9** (dang chay) | 9 | 0.1723 | 0.0418 | 6.80% | 1.24% |
| `no_oi` | 7 | 0.1731 | 0.0407 | **7.49%** | **1.43%** |
| `core4` | 4 | 0.1712 | 0.0410 | 7.16% | 1.41% |

Hieu so voi bo 9 (ghep cap): `no_oi` va `core4` **khong phan biet duoc** o **ca 4 chi tieu**;
MDE80 ~1.0pp edge5 => loai tru duoc kha nang "bo OI lam mat hon 1pp edge5".
**Model 4 feature khong phan biet duoc voi model 9 feature.**

Cap nhat 2026-09-04 (`docs/S1CUT_*`, `/home/ubuntu/feataudit/s1cut_*`): do lai voi 5 bo cat
(`no_oi7, core5, core4, core3, noret3_5`) + doi chung cong suat `worse2`:
**khong bo nao phan biet duoc la kem hon**, `core3`/`core4` diem uoc luong **cao hon** full9 tren
`g1_replay`; doi chung `worse2` (2 feature) ra kem **phan biet duoc** (`d=-0.0269`) => phep do
**co cong suat**. ⚠️ Tieu chi "tuong duong" cua `PREREG_S1CUT` neo bien vao `sd_boot`
(`1.7941*sd`) trong khi nua do rong CI la `1.96*sd` => **phep kiem tu chan**, chi PASS khi
`d > +0.166*sd`. Loi thiet ke bien, khong phai ket luan ve feature.
⚠️ `docs/COV_RESULT.md`: `sd_boot` cua ho chuoi nay **hieu thieu ~21%** => nhan `f = 1.21`.
Nhung vi tieu chi thuan ty le voi `sd`, verdict "khong bo nao dat tuong duong" **khong doi**.

### 3.6 Rui ro ro ri OI — cham CA HAI model

Cot `create_time` cua file metrics Binance **doi nghia tu 2024-03-04**. **File dang dung
`oi_percoin_full.bin` thi SACH** (phep dich +5m da ap khi build; taker nhan qua 450/450 mau).
Nhung **code repo `VisionMetricsClient.parseDay` lay nguyen `create_time`** => **moi lan rebuild
OI bang code hien tai SE dua leak 5 phut vao du lieu**. Patch bat buoc: `docs/OI_FIX_LOG.md` §5.

Trong do luong cua S1 (`FAUD2.out`): **872/4,595 tick OOS = 19.0%** thuoc vung `ts >= 2024-03-04`.
Tach sach/nhiem:

| feature | dIC tap SACH (3,723 tick) | dIC tap NHIEM (872 tick) |
|---|---|---|
| `rk_dd_7d` | +0.0531 | +0.0424 | (on dinh, khong lien quan OI) |
| `ret_14d` | +0.0324 | +0.0349 | (on dinh) |
| **`ls_global`** | **+0.0010** [-0.0065,+0.0082] | **+0.0133** [+0.0055,+0.0232] |
| `rk_oi_delta24h` | +0.00065 | +0.00024 | (~0 ca hai) |

=> **Dong gop duy nhat do duoc cua `ls_global` chi ton tai o vung bi ro ri.** Cach doc bao thu:
**chua co bang chung nao rang hai feature OI mang tin hieu that cho S1.**

**He qua van hanh:** khi OI duoc sua thi `feat_v2.parquet` phai build lai => S1 train lai =>
`pred_s1a2.parquet` va `predwf_map_s1a2/` **doi** => **moi so C2b doi**. Sua OI khong chi tac dong
G015; no buoc tai sinh ca edge dang chay.

## 4. GATE — hai tang

### 4.1 Tang 1: tran ung vien — BI BO QUA voi C2b
```java
float maxThres = PREDICT_SYMBOL_RATE_MAX_THRESHOLD * AI_DYNAMIC_MAX;  // 0.15*2.14135 = 0.32120
if (SELECTOR_RANK_TOPK > 0) { chon k coin score thap nhat; }   // BO QUA maxThres
else                        { chon nPass coin dau; }           // cutoff tuyet doi
```
`AI_DYNAMIC_MAX` lam viec **o day** — no la **TRAN UNG VIEN**, **khong** phai tran clamp cua nguong.
Voi `TOPK=8` tang nay bi bo qua: coin score > 0.32120 **van co the duoc chon**, chi la sau do gan
nhu chac chan bi tang 2 chan.

### 4.2 Tang 2: nguong dong — cua chat that
```java
float scaleFactor = (symbolPred / PREDICT_SYMBOL_RATE_MAX_THRESHOLD) * AI_DYNAMIC_MULTIPLIER;
scaleFactor = Math.max(AI_DYNAMIC_MIN, scaleFactor);     // CHI SAN, KHONG CO TRAN
float dynamic_15M = MIN_MOMENTUM_15M * scaleFactor;      // 0.008 * scaleFactor
admit <=> pred15m >= dynamic_15M
```
Kem mot **early-hard-gate**: `pred15M < MIN_MOMENTUM_15M && symbolPred > 0.15` => REJECT ngay.

Nguong **TANG DON DIEU theo score** (`DumpConfig derived.*`, do lai 2026-09-04):

| score | nguong | ghi chu |
|---|---|---|
| <= 0.0312 | **0.214%** | san (`AI_DYNAMIC_MIN`) |
| 0.0500 | 0.343% | |
| 0.1500 | 1.030% | |
| 0.2494 | 1.713% | (day la con so tung bi ghi nham thanh "nguong HANG SO") |
| 0.3000 | **2.060%** | |
| 0.3212 | **2.206%** | tran ung vien => nguong CAO NHAT co the |

**Dinh chinh (loi GHI CHEP, khong phai hai ban code):** ban ghi cu noi
`clamp(score/0.15*1.2876, 0.26787, 2.14135)` cham tran tu score 0.2494 => nguong **hang** 1.713%.
**SAI.** Cau `Math.min(..., AI_DYNAMIC_MAX)` tung ton tai nhung bi co `OFF_FLAT_HARD` (luon true)
vo hieu hoa, va ngay 2026-09-03 **ca cau clamp lan co da bi xoa han**. Ban ghi kia sai **san tu
dau**, khong phai "code da doi".

### 4.3 Thanh phan hang duoc admit (dinh nghia B — khop C2b vi TOPK=8 bo tang 1)

| dai score | so dong | `g1lite` TB | ti le duoc admit | nguong TB |
|---|---|---:|---:|---:|
| <0.10 | 1,171 | +9.18% | 99.66% | 0.574% |
| 0.10-0.20 | 28,288 | +8.54% | 54.86% | 1.145% |
| 0.20-0.2494 | 51,161 | +6.54% | 13.70% | 1.568% |
| 0.2494-0.3212 | 229,137 | +6.10% | **2.011%** | 2.009% |
| >0.3212 | **15,132,335** | +1.30% | **0.017%** | 4.168% |

Tong: `admit_rate = 0.1998%`, `g1lite | admit = +0.1066` (pool mean +0.01399).
**88.55% hang duoc admit co score < 0.30.** Va chi **2.006% pool** co score <= 0.32120 —
he chay tren **duoi cuc trai** cua phan phoi score.

Ba dinh nghia "admit" khac nhau, phai noi ro dung cai nao:
(A) cong thuc SAI co tran: 0.3116% / +0.0910 — **da nghi huu**.
(B) cong thuc DUNG, chi tang 2: **0.1998% / +0.1066** — **so dung de doi chieu C2b**.
(C) cong thuc DUNG + ap ca tran tang 1 (chi dung khi `TOPK<=0`): 0.1833% / +0.1115.
Ca (B) va (C) deu la **proxy**: chung khong mo phong buoc cat top-8 theo rank moi tick.

## 5. EXIT — phan quyet dinh P&L

| key | gia tri | vai tro |
|---|---|---|
| `SIM_RATE_PROFIT_STOP_MARKET` | 0.07 | **ARM**: chi khi lai dinh > 7% moi dat SL lan dau |
| `SIM_TS_GIVEBACK` | 1 | ratchet **LIEN TUC** (dead-zone da go) |
| `TS_GIVEBACK_RATIO` | 0.5 | nha mot nua lai dinh |
| `TS_MAX_GAP` / `TS_MAX_GAP_WEAK` | 0.08 / 0.03 | tran khoang nha: STRONG / WEAK |
| `TS_PNOPUMP_WEAK_THR` | 0.29 | `symbolPred > 0.29` => nhanh WEAK |
| `SIM_LOSER_TIME_STOP_HOURS` | 168 | lenh **chua arm** bi cat sau 7 ngay |
| `TRAIL_PEAK_MODE` | high | dinh do bang **high** cua nen |

```
maxGap = (symbolPred > 0.29) ? TS_MAX_GAP_WEAK(0.03) : TS_MAX_GAP(0.08)
gap    = min(peak * TS_GIVEBACK_RATIO, maxGap)        // FLOOR=false
SL     = round((peak - gap)/0.005) * 0.005
```
Tai diem arm 7%: **STRONG khoa +3.5%**, **WEAK khoa +4.0%** (tran nha 3% < 3.5%). Ca hai **tren**
chi phi round-trip 1.0% — day la ly do C2b song qua stress chi phi.

### 5.1 🔴 KHONG CO STOP-LOSS TRUOC KHI ARM — dinh chinh quan trong

`DumpConfig`: `derived.pre_arm_stop = KHONG co SL cung truoc khi arm - loi ra duy nhat la
time-stop 168h`. Va `HARD_STOP_LOSS_RATE=0`, `TIME_STOP_HOURS=0` **la 2 trong 5 key KHONG AI DOC**
(do bang `CONFIG_STRICT=1` ngay 2026-09-04). `PHASE1 A2c` cung do duoc: SL 0.03 **khong he duoc
model deployed doc**.

=> **`STOP_LOSS_DONE` (15% lenh) KHONG phai cat lo theo gia. Do la time-stop 7 ngay.**
Khop du lieu: moi lenh `STOP_LOSS_DONE` giu **chan 7 ngay**.

=> Muc **-19% (DEV) / -25% (VAL)** la **lo khong duoc quan ly tai moc 7 ngay**, bat ke gia da di
bao xa. Do giai thich vi sao VAL sau hon: universe no **155 -> 563 coin/gio** thi 7 ngay troi tu do
di xa hon.

=> Don con lai o tang exit la `SIM_LOSER_TIME_STOP_HOURS` (**co** trong profile) hoac **them mot
stop truoc arm** — **khong** phai sua `HARD_STOP_LOSS_RATE`.

### 5.2 Hinh dang P&L do duoc

| co che | DEV | VAL |
|---|---|---|
| `STOP_MARKET_DONE` (trailing chot lai) | 823 lenh (85%), TB **+7%**, tong +54,368 | 908 (85%), TB **+6%**, tong +49,996 |
| `STOP_LOSS_DONE` (= time-stop 168h) | 147 lenh (15%), TB **-19%**, tong -28,977 | 155 (15%), TB **-25%**, tong -37,314 |

Ky vong/lenh: DEV `0.85(+7) + 0.15(-19) = +3.10%` -> VAL `0.85(+6) + 0.15(-25) = +1.35%`
=> **-56%**. Cung winrate 85%, cung tan suat cat 15% => **toan bo sut nam o DO SAU moi lan cat**.

### 5.3 Ban le STRONG/WEAK nam giua dai van hanh — cho mong

`TS_PNOPUMP_WEAK_THR = 0.29` chia nhanh trailing, ma **88.55% hang duoc admit co score < 0.30**.
Mot dich nho cua phan phoi score se **lat hang loat lenh** giua STRONG (tran nha 8%, khoa +3.5%)
va WEAK (tran 3%, khoa +4.0%). Va `symbolPred` dung de so voi 0.29 la **gia tri G015x26 da
quantile-map**, **khong** phai diem S1 (§2.3) — tuc ban le exit dang so voi thang do cua model
khac. Tham so nay **khong duoc profile ghim** (§8).

## 6. SIZING — dinh chinh: sim va live dung HAI cong thuc khac nhau

Ban truoc cua file nay trinh `BASE_BUDGET = CAPITAL_START / NUMBER_ORDER_BUDGET = 35000/50 = 700`
nhu co so size. **Do la duong LIVE (`BudgetManager`), KHONG phai sim.**

`DumpConfig derived.*`:
```
sim:  budget = equity * F_BASE(0.0300) * (1 - U/U_MAX(0.600)) / ladder(1.00) * DCA_GRID_SCALE(1.500)
      => max tai U=0 la 1,575.00 (= 4.5% equity);  tran margin tai U_MAX = 21,000.00
live: base_budget = 700.00 (CAPITAL_START 35000 / NUMBER_ORDER_BUDGET 50)
```
Do duoc trong sim: margin/lenh TB **971**, min **197**, max **1,575** — con so 1,575 khop **dung**
cong thuc sim, xac nhan sim di duong `F_BASE`.

⚠️ **`F_BASE` va `U_MAX` — hai tham so dieu khien toan bo sizing cua sim — KHONG nam trong
profile** (§8).

## 7. DCA · CHI PHI · BREAKER

- **DCA tat hoan toan:** `DCA_GRID_ENABLED=true` nhung `DCA_GRID_WEIGHTS=1,0,0,0` => chi leg dau,
  dung het budget, khong nhoi bao gio. `DCA_GRID_LEVELS=-0.50,-0.75,-0.90` chi la so trang tri.
- **Chi phi:** `RATE_FEE=0.002` x2 + `SLIPPAGE_RATE=0.003` x2 => **round-trip 1.0%**.
  `SIM_APPLY_FUNDING=true` + `SIM_FUNDING_MARK=true` (mark theo notional).
- **Breaker:** `SIM_BREAKER_MODE=OFF`. `MAX_CONCURRENT` **tro trong sim** (doi 40->25 ra byte
  giong het). ⚠️ **Pham vi: CHI sim, CHI dataset DEV do.** Tren duong **LIVE** con mot circuit
  breaker theo **MAT DO mo lenh, DOC LAP voi `BREAKER_MODE`** — no **VAN BAT** ke ca khi OFF
  (`MarketBigChangeDetector`, khoi "KILL-SWITCH AN TOAN - KHONG XOA"). Ba nguong la **HANG SO
  trong code**: `BURST_BASE=40`, `DENSITY_SUSTAIN=10.0`, `DENSITY_ALPHA=0.6`,
  `CIRCUIT_DANGER_RATIO=0.7`, `CIRCUIT_LOOKBACK_MINUTES=4`.
  **Dung suy tu "MAX_CONCURRENT tro" ra "live khong co gioi han mat do".**

## 8. 🔴 THAM SO DIEU KHIEN P&L NHUNG KHONG NAM TRONG PROFILE

Day la lo hong nghiem trong nhat cua co che ghim hien tai: cac tham so duoi day la **default
hardcode / MUTABLE**, nen **KHONG vao `PROFILE_HASH`**. Doi chung thi hanh vi doi ma hash khong doi.

| param | gia tri | dieu khien |
|---|---|---|
| **`AI_DYNAMIC_MULTIPLIER`** | 1.2876 | **do doc nguong gate** |
| **`AI_DYNAMIC_MIN`** | 0.26787 | **san nguong gate** |
| `AI_DYNAMIC_MAX` | 2.14135 | tran ung vien (tro voi TOPK=8, **khong** tro neu TOPK<=0) |
| `PREDICT_SYMBOL_RATE_MAX_THRESHOLD` | 0.15 | mau so cong thuc gate |
| **`F_BASE`** | 0.03 | **size sim** |
| **`U_MAX`** | 0.6 | **throttle size theo utilization** |
| `RATE_FEE` / `SLIPPAGE_RATE` | 0.002 / 0.003 | chi phi 1% round-trip |
| `TS_MAX_GAP` / `TS_MAX_GAP_WEAK` | 0.08 / 0.03 | tran nha trailing |
| **`TS_PNOPUMP_WEAK_THR`** | 0.29 | **ranh STRONG/WEAK** (§5.3) |
| `NUMBER_ENTRY_EACH_SIGNAL` | 2 | |
| `number_order_budget` | 50 | (duong live) |
| `BLOCK_INTRABAR_LOOKAHEAD` | true | chan lookahead trong nen |
| `TRAIL_PEAK_MODE` | high | dinh theo high |

**Gate la rang buoc binding cua ca he (94.5%), ma hai tham so quyet dinh nguong cua no
(`AI_DYNAMIC_MULTIPLIER`, `AI_DYNAMIC_MIN`) lai khong duoc profile ghim.**

`profiles/c2c_round.properties` **CO** khai `SIM_AI_DYNAMIC_MULTIPLIER/MIN/MAX` => chuyen baseline
sang no **bit luon lo hong nay**. Do la ly do manh hon ca chuyen "lam tron so".
(Do 2026-09-04: `c2c_round` ra b:**59,846** = dung moc RND2 => 3 key **duoc doc that**;
hieu voi C2b nam trong nhieu, CI [-0.63,+1.46]pp.)

## 9. PARAM TRO — bi co khac tat

`Configs.java` co ~121 field; voi C2b chi **18-20** thuc su tac dong P&L.

| bi tat boi | thanh tro |
|---|---|
| `SELECTOR_ONLY_ENTRY=1` | `MS_UP_*`, `MS_DOWN_*`, `PREDICT_SYMBOL_RATE_UP/DOWN_*`, `DCA_LOSS_BIG_*`, `DCA_TIME_BIG_*` |
| `SELECTOR_RANK_TOPK=8` | tran ung vien tang 1 |
| `DCA_GRID_WEIGHTS=1,0,0,0` | `DCA_GRID_LEVELS/L1/STEP/LEGS/W_RATIO/SCALAR`, `DCA_TIER_*`, `TS_CARRY_SL_ON_DCA` |
| `TS_GIVEBACK_MODE=1` | `TS_PROFIT_MULTIPLIER` (5.21847), `TS_GAP_CONST` |
| `TS_GIVEBACK_FLOOR=false` | `TS_MIN_GAP` |
| `BREAKER_MODE=OFF` (chi sim) | `MAX_CONCURRENT_ORDERS`, `DENSITY_*`, `CIRCUIT_*`, `BREAKER_MARGIN_HALT`, `BREAKER_CLUSTER_DD_MAX` — **khong "tro" ma KHONG CON CONSUMER trong sim** (`5f40a90` xoa co che) |

**Da bi XOA khoi code (khong phai "tro"):** `ENABLE_SHORT` / `CONF_SIZE_*` / `SIZE_MULT`
(`5f40a90` xoa `SimulatorMarketLevelInvertedSelector.java` 555 dong + test). Chung la **ten khong
con consumer**. **Da chet han trong engine:** `TS_DYNAMIC_K` (0.29774),
`TS_WEAK_MOMENTUM_THRES` (khong xuat hien o dau trong `src/main`).

## 10. CAC HUONG DA THU — va ket qua

### 10.1 Lich su bo feature: doi DUNG MOT lan

| ban | feature | nhan | thuat toan | sim (b:) |
|---|---|---|---|---|
| V2 | **40** (37 + 3 nhieu) | `maxFav_72h >= 0.06` | XGBClassifier | 32,956 |
| V3 | **9** | `maxFav_72h/vol_7d > median` trong tick | XGBClassifier | 38,471 |
| **S1 (a2)** | **9, y nguyen V3** | `rel5` ngu phan vi trong tick | **XGBRanker** | **50,891** — dang chay |

⇒ **Bo feature chi doi MOT lan (40 -> 9).** Moi cai thien sau do den tu **nhan** va **thuat toan**.
⚠️ Cap 32,956 vs 38,471 **chua tung co CI**; `sd` cua hieu CAGR giua hai selector la **4.45pp**
⇒ *"cat 40 xuong 9 da giup"* la phat bieu **chua duoc chung minh**, chi la "khong te di ma don gian hon".
⚠️ Bon quy tac cat `R1-R4` nam o `PROCESS_LOG.md` — file **khong ton tai** va **chua tung vao git**
⇒ **ly do cat tung feature khong tai lap duoc**. Thay the: forward-test `FS_RESULT` 0/16 (§10.3).

### 10.2 Hyperparameter S1: chua tung HPO — va do la TIN TOT

Ke thua nguyen tu nhanh `fav72`/`cs72`; `grep optuna` tren `featv2/` va `research/` = **0 hit**;
cau hinh giong tung tham so trong **7** script bien the. Do ben theo seed: seed 1 / 7 ra
b:58,483 / 59,406 vs 59,471 => on dinh.
=> So phep thu o tang hyperparameter ~= **1** ⇒ theo `E[max] ~ sd*sqrt(2 ln N)`, **khong co phan
thuong nhieu nao** de lo. Rui ro chon-tren-nhieu cua S1 **khong** o hyperparameter; no o
(a) **mot** quyet dinh cat 40->9 va (b) chuoi so sanh o tang nhan/pool.

### 10.3 Da thu va THUA / khong phan biet duoc

| huong | ket qua |
|---|---|
| **Them 16 feature moi** (5 nhom chua tung co trong S1: microstructure, drawdown, thanh khoan, carry) | **0/16 vuot nguong** `sqrt(2 ln 16)=2.3548 sd`. Lead tot nhat `fs_wick_up_7d` +0.00433 (46% nguong). **3 ung vien co HAI do duoc**, `fs_body_ratio_7d` -0.00580 YYY. Doi chung nhieu PASS |
| **Nhom thanh khoan** (dollar-volume) — tung duoc `SELECTOR_FEATURES §E4` de xuat la "lo trong duy nhat duoc ghi ten" | **DA THU va TRUOT het**: `fs_dvol_7d` +0.00261, `fs_dvol_ratio` +0.00235, `fs_trdsize_7d` +0.00101, `fs_amihud_7d` -0.00090 — khong cai nao vuot nguong ⇒ **E4 da chet** |
| Them `p_g015` lam feature thu 10 cua S1 (`s1b2`) | **+6.42%** vs `s1a2` +6.80% ⇒ **xau di** |
| Feature "trang thai thi truong" gop tu feature coin (B6) | chi `p15`: OOS **+0.0532**; `p15` + 14 dai luong gop: **-0.1467**. Chi 3/14 giu dau qua 3 nam ⇒ **te di han** |
| Dung **gain importance** de giu/bo feature | Dan sai: gain xep `rk_ret_3d` **hang 1** trong khi dIC cua no ~ 0 |
| Doi selector sang G015_v2 (C3) | maxDD **-29.5%** < -15.12% ⇒ **truot rang buoc cung**; tai xac nhan S1 > G015 o tang selector |
| Quet tham so 15 chieu (GS wave-1, Sobol 256 diem) | **0/5 finalist** vuot nguong ⇒ phan quyet **(b)**. Phan ra phuong sai: 3 chieu manh nhat (`SIM_F_BASE` 0.50, `RATE_PROFIT_STOP_MARKET` 0.45, `DCA_GRID_SCALE` 0.28) **deu la truc size/don bay**; `SELECTOR_RANK_TOPK` hang 6/15 ⇒ **gia thuyet "HPO che chieu tin hieu" BI BAC** |
| Noi gate (`MIN_MOMENTUM` 0.006 / `RATE_MAX` 0.30 / ca hai) | b:59,580 / 47,143 / 37,145 — maxDD -21.0 / -44.3 / -51.3 ⇒ **truc chet** |
| B4 rolling-percentile gate | **0/3**, ca 3 diem uoc luong am, bear 2022 ca 3 am |
| Circuit breaker MARGIN/BOTH | equity 60,272 vs 60,390, DD khong doi ⇒ gan nhu khong bind |
| Log quyet dinh tung tick de mua power | MDE80 tang tick 3.400 vs equity 4.023 ⇒ **0.845 = khong cai thien** |
| Time-stop 96/168/336h | MDE80 26.42/27.29/27.84pp — giam toi da 5.1% < nguong 25% |
| Lui du lieu giu OI | metrics chi tu 2021-12-01 ⇒ chi lui them **31 ngay** (+3.4%) |

### 10.4 Cai CHUA thu (theo bang chung, xep theo ly do co hoc)

1. **Hieu chuan gate theo THU HANG cua S1** thay vi theo gia tri `p` cua G015x26 (§1, §2.3).
2. **Bo `vol_7d`** — feature duy nhat co **mau thuan noi bo**: YYY tren `g1lite` nhung **0** tren
   `g1_replay`; doi chung "xep theo `vol_7d` thuan" **thang** S1 o `g1lite` nhung **thua nang** o
   sim that (41,876 vs 50,891). Chua ai train S1 **khong co** `vol_7d`. Chi phi ~5 phut.
3. **HPO cho S1** — chua tung lam (§10.2).
4. **Them mot stop TRUOC arm**, hoac `LOSER_TIME_STOP_HOURS` khac 168 (§5.1).
5. **Cat feature G015 theo NHOM** — 45 feature chua tung bi cat loc; nhung phai **sua OI truoc**.
6. **Nguon du lieu moi**: order book / trade-by-trade / cross-exchange — chieu duy nhat chua thu
   sau khi `FS_RESULT` da dong nhom gia/volume/funding luoi gio.

## 11. KET QUA

**DEV** (2022-01 -> 2024-06, 970 lenh): equity 35,000 -> **60,390** · CAGR **24.48%** ·
maxDD **-13.12%** · Sharpe(quy) 1.99 · underwater 93 ngay · quy duong 8/10 · quy >= +5% 6/10 ·
2022 +11.6 / 2023 +45.4 / 2024H1 +6.3 · khong nam nao am.
⚠️ maxDD -13.1% xay ra trong **2022Q2 la quy CO LAI** (+1,350, winrate 85.6%, lo chua dong sau
nhat -5,888) — DD den tu **lenh dang mo**, khong tu quy thua. Ban dung PnL da dong **khong thay
duoc** cho nay (do la ly do `qret.py` phai dung equity mark-to-market).

**VALIDATION** (2024-07 -> 2025-12, 1,063 lenh, **cham lan thu 5**): equity -> **47,681** ·
CAGR **23.60%** · maxDD **-7.28%** · Sharpe(quy) 1.33 · underwater **234 ngay** · quy duong 4/6.
⚠️ 2024Q4 (+7,347) + 2025Q1 (+4,133) = **90.5%** toan bo lai; ba quy cuoi cong lai **+1.5%** trong
9 thang. ⚠️ 2025Q4: nhieu lenh nhat (**338**, gap 6 lan 2025Q3), dong thoi cao nhat (30), maxDD
sau nhat VAL — ma PnL **-385**.

⚠️ **Do tin cay:** hieu CAGR DEV **khong dung lam tieu chi duoc** — can **14-43 nam** DEV moi phan
biet 3pp (`CI_REAUDIT`, `NBETS_RESULT`). Chi **2/18** verdict cu con song, ca hai o **tang xep hang**.
`docs/COV_RESULT.md` (2026-09-04) da chung nhan: rank-IC `S1-G015 = +0.0973` CI [+0.0711,+0.1152]
**qua kiem phu** (do phu 0.941 @72h), va gate `top8-random8 = +0.0182` **con loai tru 0** sau hieu
chinh (`f=1.14`, `d/sd = 4.46`). **Hai tru cot nay dung; cac so equity thi khong.**

## 12. TAI LAP
```bash
cp -f configs/sim_dev.properties $RUNDIR/config.properties
TRADING_PROFILE=profiles/c2b_min.properties \
  WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20240630 \
  EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json \
  java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
  com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss
```
Ban chuan: `tools/run_c2b_dev.sh` (co cong byte-identity vs baseline **60390**).
Kiem cau hinh: `java -cp $JAR com.binance.chuyennd.tradecore.DumpConfig`
=> phai thay `PROFILE_HASH=a2f859b2463108fe`, `CONFIG_HASH=f79ddd824eafb978`.
Kiem cong thuc gate: `python3 research/analysis/gate_cfg.py`.

⚠️ **`rc` cua sim KHONG dung duoc lam tin hieu thanh cong** — sim in `rc=1` du run hoan tat va
byte-identical. Tieu chi phai la `done:` + `b:` + byte-identity / `qret.py`.
