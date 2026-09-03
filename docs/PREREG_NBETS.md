# PREREG_NBETS — tien dang ky: do DO DAI PHU THUOC that, KIEM PHU, HANG DOC LAP NGANG

Chot luc: 2026-09-03, **TRUOC khi tinh bat ky do dai khoi / do phu / n_eff nao**. Commit cua file
nay PHAI co truoc commit cua `docs/NBETS_RESULT.md`. Neu thu tu nguoc lai => `NBETS_RESULT.md`
bi coi la VOID.

Ly do ton tai: `docs/CI_REAUDIT.md` muc (iii) va `docs/DATA_EXTENT_SURVEY.md` §3 ket luan
"khong the do duoc cai thien 3pp CAGR bang du lieu kha dung". Ca hai ket luan do dung **mot** do
dai khoi da chon **bang lap luan**, khong bang do luong: 21 ngay (tang equity) va 72h (tang tick),
va **khong** he kiem do phu (coverage) cua CI o do dai do. Job nay do lai chinh cai nut do.

Canh bao hanh vi tu ghi truoc: **rut ngan khoi la hanh vi tu phuc vu** (khoi ngan => CI hep =>
de tuyen bo thang, va lam song lai nhieu verdict da dong). Vi vay moi do dai khoi phai qua
**cong kiem phu** o §4 moi duoc dung, va luat chon do dai duoc chot o §3 **truoc** khi thay so.

Pham vi: **CHI DEV (2022-01-01 .. 2024-06-29 cho equity)**. KHONG cham VALIDATION
(2024-07-15..2025-12-31). KHONG cham HOLDOUT 2026. KHONG chay java, KHONG backtest, KHONG train.
Chi doc log/csv co san + tinh python tren CPU. Doc `/home/ubuntu/java/devrun/` la **chi doc**.

---

## 1. NGUON DU LIEU — chot cung

| Nhom | Nguon | Cach doc |
|---|---|---|
| Chuoi equity NGAY | `/home/ubuntu/java/devrun/<TAG>/logs/sim.out` | regex **y het `PREREG_CI.md` §1 / `qret.py:7`**: `Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)`; equity = `b + unP`; giu ban ghi **cuoi cung trong ngay**; 911 ngay `20220101..20240629`; `CAPITAL_START = 35000` |
| Lenh | `/home/ubuntu/java/devrun/<TAG>/storage/printDone.csv` | cot `sym`, `start` (vao, `yyyyMMdd HH:mm`), `end` (ra), `pnl`, `margin`, `time_order` (gio giu, nguyen) |

Loi nhuan ngay: `r_1 = E_1/35000 - 1`, `r_d = E_d/E_{d-1} - 1` (d >= 2) — y het `PREREG_CI` §2.1.

### 1.1 Danh sach run — chot cung, KHONG them/bo sau khi thay ket qua

Chuoi don (do do dai phu thuoc + n_eff):

`C2b` (ung vien chinh), `C2_g015`, `N4_a8s175`, `A6_ts96`, `D1_full_ts`, `A6_ts336`,
`R2_ts120`, `R0_parity`, `R2_ts240`, `S3_ts168`, `S4_ts720`.

Cap ghep (do MDE80 cua hieu):

| ma | A | B | loai thay doi | ho |
|---|---|---|---|---|
| `Q1` | `C2b` | `C2_g015` | selector | — |
| `Q2` | `C2b` | `N4_a8s175` | tham so exit | — |
| `T1` | `A6_ts96` | `A6_ts336` | **time-stop 96h vs 336h** | D1 |
| `T2` | `R2_ts120` | `R2_ts240` | **time-stop 120h vs 240h** | R2 |
| `T3` | `S3_ts168` | `S4_ts720` | **time-stop 168h vs 720h** | S |

Ba **ho time-stop** (cung base trong cung script, chi khac `SIM_LOSER_TIME_STOP_HOURS`) — da
xac minh bang script goc TRUOC khi chot file nay (chi la kiem ton tai, khong phai tinh toan):

- ho **D1** (`/home/ubuntu/java/dev_abl.sh`, base = recipe + `SIM_FUNDING_MARK=true` +
  `DCA_GRID_WEIGHTS=1,0,0,0`): `A6_ts96` (96h) · `D1_full_ts` (168h) · `A6_ts336` (336h).
- ho **R2** (`/home/ubuntu/java/dev_rob.sh`, base = `map_s1a2_g1` recipe, `run()` mac dinh 168h):
  `R2_ts120` (120h) · `R0_parity` (168h) · `R2_ts240` (240h).
- ho **S** (`/home/ubuntu/java/dev_sl.sh`, base = `SIM_FUNDING_MARK=true`,
  `DCA_GRID_WEIGHTS=1,1,3,8`): `S3_ts168` (168h) · `S4_ts720` (720h).

**Chi 2-3 diem moi ho.** Ghi truoc: **KHONG duoc ve duong xu huong** tu 2-3 diem; chi duoc
bao cao bang so va noi ro la 2-3 diem.

---

## 2. DAI LUONG THONG KE — chot cung

Tren mot cap (A, B) va mot chuoi don:

| ma | dinh nghia | dung o dau |
|---|---|---|
| `dg` | `365 * mean_d( log(1+r_A,d) - log(1+r_B,d) )`, don vi %/nam | **DAI LUONG CHINH cua cong kiem phu** — vi no la ham TUYEN TINH cua chuoi nen co dich (target) xac dinh chinh xac: `365 * mu` |
| `dCAGR` | `(prod(1+r_A))^(365/T) - (prod(1+r_B))^(365/T)`, don vi pp | dai luong cua `PREREG_CI` §2.1 — bao cao **phu**, khong gate (dich chi xac dinh tiem can) |
| `sdCAGR` | `sd` bootstrap cua `CAGR` cua **mot** run | de bao `n_eff` va MDE80 cua chuoi don |
| `MDE80` | `2.80158 * sd_boot` (y het `PREREG_CI` §5, `PAIRED_CALIB` §3) | tra loi Cau 4/Cau 5 |

Bootstrap: **moving-block circular**, ghep `k = ceil(T/L)` khoi cho du `T = 911` ngay, khoi cuoi
bi cat cho khop do dai — **y het `PREREG_CI` §2.3**. Ghep cap: MOT danh sach chi so khoi dung
cho CA HAI run. CI95 = **percentile 2.5 / 97.5**. `N_REP = 2000` cho so lieu that,
`SEED = 20260903` (y het `PREREG_CI` §2.4).

**KHONG bootstrap maxDD** (`PREREG_CI` §2.5).

---

## 3. CAU 1 — LUAT CHON DO DAI KHOI, chot TRUOC khi tinh

### 3.1 Luoi do dai khoi duoc xet

`G = {1, 2, 3, 5, 7, 10, 14, 21, 28, 42, 63}` ngay. (63 ngay => 15 khoi, da la san duoi cua
"con du khoi de resample".)

### 3.2 Estimator 1 (CHINH) — Politis & White (2004) + hieu chinh Patton–Politis–White (2009)

Cong thuc chuan, khong tuy y. Tren chuoi `x_1..x_N` (N = 911):

1. Tu tuong quan mau `rho(k)`, `k = 1..M_max`, voi `M_max = ceil(sqrt(N)) + K_N`,
   `K_N = max(5, ceil(sqrt(log10(N))))`.
2. `m` = so nho nhat sao cho `|rho(k)| < 2*sqrt(log10(N)/N)` voi **moi** `k` trong
   `[m+1, m+K_N]`; neu khong co thi `m = M_max`. Dat `M = min(2*m, M_max)`.
3. Cua so flat-top trapezoid `lam(t) = 1` neu `|t| <= 1/2`; `= 2*(1-|t|)` neu `1/2 < |t| <= 1`;
   `= 0` neu khac.
4. `G_hat = sum_{k=-M..M} lam(k/M) * |k| * R(k)`; `S_hat = sum_{k=-M..M} lam(k/M) * R(k)`
   (voi `R(k)` la tu hiep phuong sai mau, `R(-k) = R(k)`).
5. Circular block bootstrap: `D_CB = (4/3) * S_hat^2`.
   `b_opt = ( 2 * G_hat^2 / D_CB )^(1/3) * N^(1/3)`.
6. Chan tren `b <= ceil(min(3*sqrt(N), N/3))`; chan duoi `b >= 1`. Lam tron len.

Ky hieu ket qua: `L_PW`.

### 3.3 Estimator 2 (KIEM CHEO) — plateau cua variance-ratio

`V(L) = L * var_j( mean(x[j : j+L]) )` tren tat ca `j` (vong tron) — uoc luong phuong sai dai han
`sigma2_inf` khi `L` du lon. Chuan hoa `VR(L) = V(L) / V(1)`.

Luat plateau chot truoc: `L_VR` = gia tri **nho nhat** `L` trong `G` sao cho voi **moi** `L' `
trong `G` voi `L <= L' <= min(4L, 63)`, `|VR(L') / VR(L) - 1| <= 0.10`.
Neu khong co `L` nao thoa => `L_VR = 63` (chan tren cua luoi) va ghi ro "khong dat plateau".

### 3.4 XU LY KHI HAI ESTIMATOR KHONG DONG Y — chot truoc

- `L_est = max(L_PW, L_VR)`, lam tron **len** ve gia tri gan nhat trong `G`.
- Neu `L_PW` va `L_VR` lech hon **2 lan** thi bao cao ca hai va **van dung gia tri LON hon**.
  **KHONG BAO GIO** dung gia tri nho hon. Luat nay chot o day de khong the chon sau.
- Estimator chay tren chuoi nao: tren **chinh chuoi duoc bootstrap**. Voi cap (A,B) => chay tren
  chuoi hieu `d_t = log(1+r_A,t) - log(1+r_B,t)`. Voi chuoi don => chay tren `log(1+r_t)`.
  Neu mot cap co `L_est` khac nhau giua hai chuoi thanh phan thi lay `max`.

### 3.5 Do dai khoi HOP LE (`L_valid`) — dinh nghia chot cung

`L_valid` = gia tri **nho nhat** `L` trong `G` sao ca hai dieu sau dung:

1. `L >= L_est` (§3.4);
2. `L` **QUA CONG KIEM PHU** §4 tren generator `G4` (hieu chuan theo chinh chuoi that do), tuc
   do phu thuc nghiem cua CI95 nam trong dai chot truoc **[0.92, 0.97]**.

Neu khong co `L` nao trong `G` thoa ca hai => ghi "**KHONG CO DO DAI KHOI HOP LE**" va bao cao
do phu tai moi `L`. Khong duoc noi rong dai [0.92, 0.97] sau khi thay ket qua.

### 3.6 Rang buoc chong-tu-phuc-vu (chot truoc)

- Neu `L_valid < 21` ngay (tuc CI cu o tang equity **bao thu qua**): bao cao muc do hep lai bang
  so, nhung **KHONG mo lai bat ky verdict nao** trong `CI_REAUDIT` / `AUDIT_APPLIED` /
  `RUNS_DEV`. Do la quyet dinh cua chu du an, khong phai cua job nay.
- Neu do phu tai `L = 21` (equity) hoac `L = 3` ngay (~72h, tang tick) **duoi 0.92** thi phai ghi
  thang: **CI cu con HEP QUA**, tinh hinh **xau hon** da bao.
- KHONG sua `docs/PREREG_CI.md` hay bat ky `PREREG_*.md` cua nguoi khac.

---

## 4. CAU 2 — CONG KIEM PHU (COVERAGE). Bat buoc, chot toan bo truoc

Nguyen tac: mot do dai khoi chi duoc dung neu, tren du lieu tong hop co **do phu thuoc DA BIET**,
thu tuc bootstrap cua `PREREG_CI` cho **do phu thuc nghiem cua CI95 xap xi 95%**. Khoi cho
**duoi phu** la khoi **SAI**, du CI cua no hep dep.

### 4.1 Cac generator — chot cung

Moi generator sinh **cap** chuoi loi nhuan ngay do dai `T = 911`, dang
`log(1+r_A,t) = mu_A + e_t`, `log(1+r_B,t) = mu_B + f_t`, voi `d_t = (mu_A - mu_B) + (e_t - f_t)`.
Vi dai luong chinh `dg` chi phu thuoc `d_t`, ta sinh truc tiep `d_t = mu + u_t` voi
`mu = 0.0002` (~ +7.3%/nam, cung bac voi cap Q1 that) va `u_t` co cau truc phu thuoc da biet:

| ma | cau truc `u_t` | do dai phu thuoc DA BIET |
|---|---|---|
| `G1` | iid N(0, s2) | 1 ngay |
| `G2a` | AR(1) `phi = 0.3` | thoi gian tich phan `(1+phi)/(1-phi) = 1.86` |
| `G2b` | AR(1) `phi = 0.6` | 4.00 |
| `G2c` | AR(1) `phi = 0.9` | 19.0 |
| `G3a` | MA trung binh deu span **S = 7** ngay | **dung 7 ngay** (cat hoan toan sau 7) |
| `G3b` | MA trung binh deu span **S = 21** ngay | **dung 21 ngay** |
| `G4-<pair>` | AR(1) voi `phi` = tu tuong quan tre-1 **do tu chuoi hieu THAT** cua cap do; `s` chuan hoa cho `sd(u_t)` khop chuoi that | hieu chuan theo du lieu that |

`sd(u_t)` cua `G1..G3` chuan hoa ve `0.01` (1%/ngay) — do lon khong anh huong do phu.

`G3a/G3b` la phep thu **sat nhat**: do dai phu thuoc dung bang `S`, nen do phu phai chuyen tu
"duoi phu" sang "dat" khi `L` vuot `S`. Neu bang do phu KHONG cho hien tuong do thi cong cu sai
va moi so con lai vo gia tri.

### 4.2 Dai luong va DICH (target) — chot cung

- **CHINH (gate)**: `dg = 365 * mean(d_t)`. Dich dung = `365 * mu`. Do phu = ti le lan
  CI95 percentile bootstrap chua `365 * mu`.
- **PHU (bao cao, khong gate)**: `dCAGR` — dich dung dat la
  `exp(365 * mu_A) - exp(365 * mu_B)` voi `mu_A = mu`, `mu_B = 0` (chuoi B khong nhieu). Do phu
  cua no bi lech do **bias cua mot ham loi tren mau huu han**, khong chi do do dai khoi; vi vay no
  **khong** duoc dung de loai/nhan mot do dai khoi.

### 4.3 Thu tuc — chot cung

Voi moi (generator, `L` trong `G`):

1. Sinh `N_MC = 1000` chuoi doc lap (seed `20260903 + 1000*gen_id + L`).
2. Voi moi chuoi: chay **dung** bootstrap cua §2 (moving-block circular, `k = ceil(T/L)`,
   khoi cuoi bi cat, percentile 2.5/97.5) voi `N_BOOT = 1000`.
3. Do phu = ti le CI chua dich. Sai so Monte Carlo cua do phu o 95% voi `N_MC=1000` la
   `sqrt(0.95*0.05/1000) = 0.69pp` => dai [0.92, 0.97] la khoang `+-3.6` sai so MC. Ghi ro.
4. Bao cao **bang bat buoc**: `do dai khoi | do phu | rong CI trung binh`.

`N_BOOT = 1000` (khong 2000) chi cho **kiem phu** — de tiet kiem CPU; so lieu that o §2 van dung
`N_REP = 2000`. Ghi ro o day de khong bi coi la doi tham so sau.

### 4.4 Dai chap nhan — chot cung

**Do phu trong [0.92, 0.97] => PASS.** `< 0.92` => **DUOI PHU = khoi SAI, khong duoc dung**.
`> 0.97` => **BAO THU** (dung duoc nhung phai ghi ro CI rong hon can thiet).

### 4.5 Ap lai len chuoi THAT

Sau khi co bang do phu: ap dung `L_valid` (§3.5) len chuoi that cua `C2b` va cua cac cap §1.1,
bao cao `n_eff` **hop le** = so khoi = `ceil(911 / L_valid)`, cung voi ESS doc lap-hoa
`ESS = T * V(1) / V(L_valid)` (dung `V` cua §3.3) — hai cach dem, bao cao ca hai, khong tron.

---

## 5. CAU 3 — HANG DOC LAP THEO CHIEU NGANG

Du lieu: `printDone.csv` cua `C2b` (970 lenh). **`pos.bin` cua `TickDecisionLog` KHONG co** duoi
`/home/ubuntu/java/devrun/` — da kiem truoc khi chot file nay: `C2b_TLON/storage/` chi co
`BalanceIndex.data`, `OrderTestDone.data`, `printDone.csv`, va `find` tren toan `/home/ubuntu/java`
khong ra `pos.bin` / `tick.bin` / `*.bin.gz`. Thu muc `/home/ubuntu/tick/` bi **CAM** boi gioi han
cung cua job nay. => khong the dung pho tri rieng cua ma tran tuong quan **duong loi nhuan
mark-to-market** giua cac vi the. Ghi truoc: neu tim thay `pos.bin` o cho duoc phep doc thi van
uu tien cach pho tri rieng; neu khong thi dung ba cach duoi, va **noi ro han che**.

### 5.1 Do CUNG GIU DONG THOI (dem, khong mo hinh)

Luoi 60 phut tren `20220101..20240630`; `n_active(t)` = so lenh co `start <= t < end`.
Bao cao: `mean`, `median`, `p90`, `max`, va `mean | n_active >= 1`. Do la cau tra loi cho
"giu dong thoi trung binh bao nhieu vi the".

### 5.2 Tuong quan trong cohort => so cuoc hieu dung (cach CHINH khi khong co `pos.bin`)

`x_i = pnl_i / margin_i` (ROI tung lenh). Cohort = nhom lenh co `start` trong **cung mot ngay
lich** (chinh), kiem do ben o **cung khoi 72h** va **cung tuan**.

`rho_bar` = ICC mot chieu (one-way random effects) uoc luong bang ANOVA:
`rho = (MSB - MSW) / (MSB + (k0 - 1) * MSW)` voi `k0` = co cohort hieu dung
`k0 = (N - sum(k_j^2)/N) / (J - 1)`, chi dung cohort `k_j >= 2`. Neu `rho < 0` thi ghi `rho = 0`
va noi ro (khong am hoa).

So cuoc hieu dung o mot thoi diem giu `k` vi the: **`n_eff(k) = k / (1 + (k-1) * rho_bar)`**.
Bao cao cho `k` = `mean` va `p90` cua §5.1, va cho `k = 30` (con so gia dinh trong de bai).

### 5.3 So cuoc hieu dung TOAN CUC (kiem cheo, khong phu thuoc cohort)

`n_eff_bets = N^2 * s2 / Var(sum_i x_i)` voi `s2` = phuong sai mau cua `x_i` va `Var(sum)` do bang
**block bootstrap o `L_valid`** tren chuoi tong ROI theo ngay. Bao cao `N / n_eff_bets`
= "bao nhieu lenh moi duoc mot cuoc doc lap".

### 5.4 THEM SYMBOL / THEM LENH CO TANG n_eff KHONG — phep thu truc tiep

Cac run trong §1.1 phu **cung 911 ngay lich** nhung co so lenh rat khac nhau
(`C2b` 970 · `R2_ts120` 1128 · `A6_ts96` 1837 ...). Neu `n_eff` bi chi phoi boi **so lenh** thi
`sd(CAGR)` phai giam theo `1/sqrt(N_lenh)`; neu bi chi phoi boi **thoi gian lich** thi `sd` gan
nhu khong lien quan `N_lenh`.

Chot truoc: hoi quy `log(sdCAGR)` theo `log(N_lenh)` tren 11 chuoi don cua §1.1, bao cao do doc
`beta` va CI cua no. **Du doan ghi truoc**: neu nhan xet cua chu du an dung thi `beta ~ 0`
(khong phai `-0.5`). Ghi truoc canh bao: 11 run **khong** khac nhau chi o so lenh => day la
**bang chung quan sat, khong phai thi nghiem co doi chung**; phai doc kem canh bao do.

---

## 6. CAU 4 — TIME-STOP CO MUA DUOC n_eff KHONG

Voi moi run trong ba ho time-stop (§1.1), bao cao bang:

`time-stop (h) | median/p90 gio giu that (cot time_order) | L_PW | L_VR | L_valid | so khoi = ceil(911/L_valid) | sdCAGR | MDE80 (pp)`

va cho ba cap `T1/T2/T3`: `L_valid` cua chuoi hieu, so khoi, `sd(dg)`, `MDE80(dg)`.

**Luat doc chot truoc:** ket luan "rut ngan time-stop mua duoc power" chi duoc phat bieu neu
`MDE80` giam **don dieu** theo time-stop trong **it nhat 2 trong 3 ho** VA muc giam
`> 25%` giua diem thap nhat va cao nhat cua ho. Nguoc lai ghi "khong mua duoc". Voi 2-3 diem moi
ho, **khong ve duong xu huong, khong ngoai suy**.

---

## 7. CAU 5 — BANG KICH BAN VA LUAT TRA LOI

Bang: `thoi gian du lieu T (nam) x L_valid x hang ngang` -> `MDE80` tot nhat kha thi, dung dung
cong thuc da chot o `PREREG_CI` §5 / `DATA_EXTENT_SURVEY` §3:
`MDE80(T) = 2.80158 * sd_dev * sqrt(T_dev / T)`, `T_dev = 2.4941` nam, **`sd_dev` do lai o
`L_valid`** thay vi o 21 ngay.

Cac gia tri `T` xet (lay y nguyen `DATA_EXTENT_SURVEY` §3): 2.50 (DEV nay) · 2.58 (lui 2021-12) ·
3.96 (DEV+VAL) · 4.50 (lui 2020-01, bo OI) · 6.00 (toi da co the co) · 6.31.

**Luat tra loi chot truoc:**

- **CO** neu ton tai mot o trong bang voi `MDE80 <= 3.0 pp` **va** o do khong doi hoi
  (a) pha seal HOLDOUT, (b) du lieu khong ton tai theo `DATA_EXTENT_SURVEY`, hoac (c) mot khoi
  KHONG qua cong kiem phu §4. Phai neu ro cau hinh va chi phi.
- **KHONG** neu moi o kha thi co `MDE80 > 3.0 pp`. Phai neu `MDE80` san kha thi.
- **KHONG KET LUAN DUOC** neu cong kiem phu §4 that bai o moi do dai khoi (khong co `L_valid`),
  hoac neu thieu mot phep do da liet ke. Phai neu ro thieu cai gi.

Loai cap so sanh duoc dung cho phan quyet **CO/KHONG**: cap **de nhat** (`Q2` tham so exit) —
dung y `DATA_EXTENT_SURVEY` §3 ("cho cap so sanh de nhat"). Neu ke ca cap de nhat khong dat 3pp
thi cap kho hon cang khong dat.

---

## 8. THU TU THUC HIEN — bat buoc

1. Commit file nay. **Ghi lai commit hash.**
2. Chi sau do moi chay script (`/home/ubuntu/nbets/*.py`).
3. Tai lap kiem chung TRUOC khi doc so moi: (a) `sd(hieu CAGR)` cap `C2b` vs `C2_g015` o khoi
   21 ngay phai ra **4.45pp** va `d = +7.33pp`, CI `[-1.72, +15.61]` (`CI_REAUDIT` #1,
   `PAIRED_CALIB` §1.2); (b) `MDE80` cua cap `A6_ts96`/`A6_ts336` o tang equity khoi 21 ngay phai
   ra **6.437pp** (`PAIRED_CALIB` §3). Neu khong tai lap duoc => **DUNG**, ghi "khong tai lap
   duoc", khong doi phuong phap cho khop.
4. Chay cong kiem phu §4 **truoc** khi bao cao bat ky `L_valid` nao.
5. Viet `docs/NBETS_RESULT.md`, mo dau bang muc "TRA LOI CHO UNI" 8-10 dong.

---

## 9. NHUNG GI PRE-REG NAY KHONG LAM

- Khong sua diem uoc luong nao. Khong sua `docs/PREREG_*.md` cua nguoi khac (ke ca `PREREG_CI.md`;
  neu thay no can sua thi ghi vao `NBETS_RESULT.md`).
- Khong mo lai / khong dong nhanh nao. Khong quyet thay chu du an.
- Khong chay java / backtest / train. Khong tao run moi. Neu ket luan doi hoi mot run moi thi
  **DUNG va bao**, khong tu chay.
- Khong cham `/home/ubuntu/gs/`, `/home/ubuntu/fs/`, `/home/ubuntu/g015/`, `/home/ubuntu/tick/`,
  `/home/ubuntu/feataudit/`, `/home/ubuntu/oifix/`. Khong submit kernel Kaggle. Khong `git push`.
- Khong tra loi cau leak `f0..f39`.
- Khong bootstrap `maxDD`.
