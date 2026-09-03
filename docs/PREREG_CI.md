# PREREG_CI — tien dang ky phuong phap do KHOANG TIN CAY THAT cho cac verdict cu

Chot luc: 2026-09-03, **TRUOC khi tinh bat ky CI nao**. Commit nay phai co truoc commit cua
`docs/CI_REAUDIT.md`. Neu thu tu commit nguoc lai => toan bo ket qua CI_REAUDIT bi coi la VOID.

Ly do ton tai: `docs/LEAK_L1_REPORT.md` (Cau 2/Cau 3) chung minh moi phat bieu "y nghia thong ke"
trong du an tinh den nay dung **n gia**. Grid mau 15m + nhan `g1lite` cua so 72h => n hieu dung
tren DEV la **302 khoi 72h**, khong phai 15.44M dong. CI that cua spearman G015 la
[0.1260, 0.2005] thay vi +-0.00050 — **rong hon 74 lan**. Diem uoc luong khong doi.
Cung logic do ap cho tang equity: 911 ngay DEV khong phai 911 quan sat doc lap.

Pham vi: **CHI DEV** (2022-01-01 .. 2024-06-29 cho equity; 2021-12-31..2024-06-30 cho pool tick).
KHONG cham VALIDATION (2024-07-15..2025-12-31). KHONG cham HOLDOUT 2026.
Khong chay java, khong backtest, khong train. Chi doc log/parquet co san + tinh python.

---

## 1. NGUON DU LIEU — chot cung

| Nhom | Nguon | Cach doc |
|---|---|---|
| A (equity/CAGR) | `/home/ubuntu/java/devrun/<TAG>/logs/sim.out` | regex **y het `qret.py:7`**: `Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)`; equity = `b + unP` (mark-to-market); giu ban ghi **cuoi cung trong ngay** (`drop_duplicates(keep="last")`) |
| B (xep hang) | `/home/ubuntu/ledger/cand_dev.parquet`, `pred_s1a2.parquet`, `path_labels.parquet` | y het `research/analysis/gate_vs_rank3.py:7-13` (inner-join ts+sym, dropna `g1_replay`) |
| B (H3) | `/home/ubuntu/ledger/h3/` | neu khong co pool OOS doc duoc => ghi "khong du du lieu" |

**CAM dung ban `*_OLDCLAMP.parquet`** (cong thuc gate SAI). Moi so nhom B dung ban da sua.

Da xac nhan truoc khi chot pre-reg (chi la kiem ton tai du lieu, khong phai tinh CI):
20/20 run trong danh sach co `sim.out` voi **dung 911 ngay**, `20220101..20240629`, cung lich
=> ghep cap theo ngay duoc, khong can noi suy.

---

## 2. NHOM A — chuoi loi nhuan NGAY

### 2.1 Bien doi

- `E_d` = equity cuoi ngay d (b+unP), d = 1..911.
- Von goc `CAPITAL_START = 35000` cho MOI run trong danh sach => dinh nghia
  `r_1 = E_1/35000 - 1`, `r_d = E_d/E_{d-1} - 1` cho d >= 2. Duoc **911 loi nhuan ngay**.
- CAGR tu mot chuoi loi nhuan `r`: `CAGR = (prod(1+r))^(365/911) - 1`.
  (Do chieu dai chuoi la co dinh 911 ngay lich trong moi lan resample, so mu khong doi.)

### 2.2 Do dai block — CHOT: chinh = **21 ngay**, kiem tra do ben o **10** va **42 ngay**

Giai thich (chot truoc khi thay ket qua):
- Rang buoc duoi: mot lenh cua C2b song **nhieu ngay** — `SIM_LOSER_TIME_STOP_HOURS=168` (7 ngay)
  la tran cho lenh LO, lenh lai chay trailing arm 7% + giveback nen co the dai hon. Loi nhuan ngay
  vi vay tu tuong quan trong it nhat ~7 ngay. Block **phai** dai hon vong doi lenh => `>= 7`.
- Rang buoc tren: block phai << 911 de con du block ma resample. 42 ngay cho 21 block, da la it.
- Chon **21 ngay (~1 thang)** lam chinh: gap 3 lan tran lenh lo, van con **n_eff ~ 43 block**.
- Yeu cau cua chu du an la ">= 5 ngay"; 21 la **bao thu hon** yeu cau do, co y.
- Kiem tra do ben bat buoc o **10** va **42** ngay. **Khong** chon do dai nao sau khi xem ket qua.

### 2.3 Ghep cap (paired) — bat buoc

Moi so sanh nhom A la **cung mot doan thi truong, cung 911 ngay lich**. Vi vay:

1. Mot lan resample sinh ra **MOT** danh sach chi so ngay (moving-block, **circular**, ghep block
   cho du 911 ngay; block cuoi bi cat cho khop do dai).
2. Danh sach chi so **DUNG Y NGUYEN** cho ca hai run trong cap.
3. Tinh `CAGR_A`, `CAGR_B` tren cung danh sach do, roi lay `d = CAGR_A - CAGR_B`.
4. CI la CI cua **d**, khong bao gio la "hai CI rieng roi xem co chong nhau".

Ly do cam so hai CI rieng: hai chuoi loi nhuan ngay o day tuong quan rat cao (cung selector, cung
thi truong, thuong chi khac 1-2 tham so exit). Bootstrap doc lap se pha tuong quan do va lam
CI cua hieu **rong gia** => bao thu qua muc, se ket luan "khong phan biet duoc" cho ca nhung cap
that su khac nhau.

### 2.4 So lan lap, seed, kieu CI

- `N_REP = 2000` cho moi cap va moi do dai block.
- `SEED = 20260903`. Sinh chi so bang `numpy.random.default_rng(SEED)`, resample **lai tu seed do**
  cho tung (cap, do dai block) de ket qua tai lap duoc doc lap voi thu tu chay.
- CI95 = **phan vi 2.5% va 97.5%** cua phan bo bootstrap cua `d` (percentile, khong BCa —
  ghi ro de khong doi sau).
- Bao cao them: `sd(d)`, `P(d > 0)`, va `n_eff` = so block = `ceil(911 / L)`.

### 2.5 Cai KHONG bootstrap — khai bao truoc

**maxDD KHONG duoc bootstrap.** Moving-block resample pha cau truc duong equity theo thu tu
thoi gian, nen maxDD cua duong gia lap khong con nghia. Moi phat bieu ve maxDD trong CI_REAUDIT
la **so quan sat duoc mot lan**, khong co CI. Ghi ro nhu vay, khong bien no thanh CI gia.
Tuong tu: underwater-days, so quy duong.

---

## 3. NHOM B — chuoi tick / xep hang

### 3.1 Don vi resample — CHOT: **khoi 72h wall-clock**

Ly do: nhan dung de do chat luong xep hang la `g1lite` / `g1_replay`, cua so **72h**
(`featv2/ledger.py.bak:33`). Hai tick cach nhau < 72h chia nhau cung tuong lai =>
khong doc lap. Day dung la don vi ma `LEAK_L1_REPORT.md` §3.3 dung (302 khoi tren DEV).

- `block_id = floor((ts - ts_min) / 72h)`.
- Chinh = **72h**. Kiem tra do ben o **24h** (long hon, se cho CI hep hon — de lo neu ket luan
  phu thuoc do dai) va **168h** (bao thu hon).

### 3.2 Tinh truoc per-tick roi resample block — chinh xac va re

Ca hai thong ke nhom B la **thong ke cong tinh theo tick**:
- rank-IC = trung binh **theo tick** cua `spearman(-score, g1_replay)` tren cac tick co `>= 10` dong
  (nguong 10 va huong `-score` lay y nguyen tu `gate_vs_rank3.py:18-19`; score THAP = TOT).
- `mean g1_replay` cua nhom duoc chon = **trong so theo DONG** (`sum / count`), y nguyen cach
  `gate_vs_rank3.py:37` tinh so goc 0.0431 / 0.0249 / 0.0193.

Vi vay: tinh **mot lan** cho tung tick `(ic_S1, ic_G015, sum_sel, n_sel, block_id)`, roi bootstrap
= resample **block**, gop cac tick trong block duoc chon, tinh lai thong ke. Cach nay cho ket qua
**giong het** bootstrap tho tren dong, nhung khong phai tinh lai spearman 2000 lan.

### 3.3 Ghep cap

Y nhu §2.3: mot lan resample sinh MOT danh sach block; ca hai phuong an dung **cung** danh sach do;
CI la CI cua hieu. Voi #8 (`gate MO top8` vs `random8`) hai nhom nam trong **cung** tick =>
paired la bat buoc. Voi #9 (`gate MO` vs `gate DONG`) hai nhom o cac tick khac nhau nhung **cung
block thoi gian** => resample block dung chung van la paired dung cach (giu tuong quan regime).

### 3.4 Random8 — chot seed truoc

`random8` tai lap y `gate_vs_rank3.py:28-29`: `df.sample(frac=1.0, random_state=0).groupby("ts").head(8)`.
Tap random8 duoc **co dinh mot lan** voi `random_state=0` roi coi nhu du lieu; bootstrap chi
resample block. Khong resample lai random8 moi rep (neu resample lai se tron lan hai nguon
bien dong va khong tra loi duoc cau hoi goc).

### 3.5 So lan lap, seed

`N_REP = 2000`, `SEED = 20260903`, CI95 percentile — y nhu §2.4.
(Bao cao leak dung 400 rep; 2000 chi lam CI muot hon, khong doi diem uoc luong.)

---

## 4. BA PHAN LOAI — dinh nghia chot cung

Cho moi verdict cu, so voi **CI95 cua HIEU** (`d`), va voi `s_old` = dau ma verdict cu ngu y
(vi du "S1 thang G015" => `s_old = +1` cho `d = S1 - G015`):

| Phan loai | Dieu kien |
|---|---|
| **SONG** | CI95 cua `d` **khong chua 0** o **CA BA** do dai block da chot (§2.2 / §3.1), **va** dau cua `d` khop `s_old` |
| **KHONG PHAN BIET DUOC** | CI95 cua `d` **chua 0** o do dai block chinh, **hoac** khong chua 0 o block chinh nhung chua 0 o mot trong hai do dai kiem tra |
| **DAO CHIEU** | CI95 cua `d` khong chua 0 o ca ba do dai, **nhung** dau cua `d` **nguoc** `s_old` |

Yeu cau "khong chua 0 o ca ba do dai block" la **co y bao thu**, va duoc chot **truoc** khi tinh.
Muc dich: khong cho phep chon do dai block nao cho ra ket luan mong muon.

**VOID khac THUA.** Mot cap ma hai run **giong het nhau tung byte** (`d = 0` theo dinh nghia,
khong phai theo do luong) thi ghi **VOID — nut tro**, KHONG bootstrap, KHONG goi la "khong phan
biet duoc" (cach goi do ngu y co bien dong ma ta khong do noi; that ra khong co bien dong nao).
Ap cho: K1_conc25 / K2_conc20 vs K0_h1a_prof; BR2_both vs BR1_margin.

---

## 5. CAU HOI CONG SUAT (cho muc HE QUA (iii)) — cong thuc chot truoc

`CAGR ~ (365/T) * sum(log(1+r))` => `sd(CAGR_hieu)` ty le **`1/sqrt(T)`** voi T = so ngay
(so block ty le T khi do dai block co dinh).

Goi `s_dev` = `sd` bootstrap cua hieu CAGR do duoc tren DEV (T_dev = 911 ngay = 2.494 nam),
do dai block chinh 21 ngay.

Yeu cau phat hien mot cai thien that `delta = 3pp` CAGR voi kiem dinh 2 phia alpha=0.05 va
**cong suat 80%**:

```
s_can  = delta / (z_{0.975} + z_{0.80}) = 0.03 / (1.95996 + 0.84162) = 0.03 / 2.80158
T_can  = T_dev * (s_dev / s_can)^2          [ngay]
nam_can = T_can / 365
```

Bao cao them moc **cong suat 50%** (`s_can = delta / 1.95996`) de thay san duoi.
Ghi ro gia dinh: cau tra loi nay gia dinh **cung che do thi truong** va **sd khong doi theo
thoi gian** — mot gia dinh manh va gan nhu chac chan **lac quan** (DEV 2022-2024 co 1 bear + 1
bull; them nam khong bao dam them thong tin cung chat luong). Do la san duoi cua nhu cau du lieu,
khong phai du bao.

---

## 6. THU TU THUC HIEN — bat buoc

1. Commit file nay. **Ghi lai commit hash.**
2. Chi sau do moi chay script tinh CI (`/home/ubuntu/ci/*.py`, se commit vao `research/analysis/`).
3. Tai lap diem uoc luong cu truoc (sanity: 60390 / 51903 / 0.0431 / ...). Neu khong tai lap duoc
   thi **dung**, ghi "khong tai lap duoc" — khong duoc doi phuong phap cho khop.
4. Viet `docs/CI_REAUDIT.md` theo dung 3 phan loai o §4.

## 7. NHUNG GI PRE-REG NAY KHONG LAM

- Khong sua diem uoc luong nao. CI khong doi diem.
- Khong mo lai nhanh nao. Ket luan "nam trong nhieu" la **de nghi mo lai**, quyet dinh mo hay
  khong la cua chu du an (co danh doi: mo lai = them n_trials = them rui ro L2 selection).
- Khong tra loi cau leak `f0..f39` (van mo, xem `LEAK_L1_REPORT.md` muc "CON LAI CHUA DONG").
- Khong cham `docs/PREREG_GS.md`, `/home/ubuntu/gs/`, `research/kaggle/gsearch/*`.
