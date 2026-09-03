# NBETS_RESULT — do dai phu thuoc THAT, kiem phu, hang doc lap ngang, va cau tra loi 3pp

Ngay: 2026-09-04. Pham vi: **CHI DEV (2022-01-01 .. 2024-06-29)**. KHONG cham VALIDATION
(2024-07-15..2025-12-31), KHONG cham HOLDOUT 2026. Khong chay java, khong backtest, khong train,
khong tao run moi. `/home/ubuntu/java/devrun/` chi doc.

Tien dang ky: **`docs/PREREG_NBETS.md`, commit `1d103f8`** (2026-09-04T04:27:59+07:00) — chot
**TRUOC** khi tinh bat ky do dai khoi / do phu / n_eff nao. Ban chay:
`/home/ubuntu/nbets/nb_lib.py`, `nb_step1.py` .. `nb_step6.py`; output `step1.out` .. `step6.out`,
`step*.json`.

---

## TRA LOI CHO UNI

1. **Do dai khoi hop le (Politis-White + kiem phu) la 3-10 ngay**, KHONG phai 21: cap exit-param
   `L_valid = 3` ngay, cap selector `L_valid = 10` ngay.
2. **Nhung no lam CI RONG hon, khong hep hon** — vi chuoi loi nhuan ngay **phu thuoc AM**
   (`phi_1` = −0.04 .. −0.29; `VR(L) < 1` voi moi `L > 1`). MDE80 cap exit-param di tu **7.19pp**
   (khoi 21) len **7.66pp** (khoi 3). Nhan xet "khoi ngan => CI hep => de tuyen bo thang" **sai
   dau** o bo du lieu nay.
3. **Cong kiem phu: khoi 21 ngay VA khoi 3 ngay (=72h) deu PASS** (do phu 0.932-0.966 tren
   generator hieu chuan theo chuoi that). Cong cu duoc chung minh nhay: voi phu thuoc **duong**
   span 7 ngay no bat duoi phu o moi `L <= 14` va chi PASS tu `L >= 21`; voi span 21 ngay **khong
   co** do dai khoi nao trong luoi PASS. Bang day du o §2.
4. **`n_eff` = 44 khoi KHONG phai co mau hieu dung.** Do la so **don vi resample**. ESS that cua
   chuoi C2b la **1089-1826 ngay iid tuong duong**, tuc **LON hon** 911. Kiem chung: bootstrap
   iid (`L=1`) cho `sd` **lon hon** khoi 21 (2.866 vs 2.565pp) — neu ESS that la 44 thi ti le phai
   la 4.55, do duoc la **0.895**.
5. **Hang ngang: C2b giu dong thoi trung binh 1.83 vi the (62.5% gio KHONG co vi the nao),
   trung binh 4.88 khi co it nhat 1.** Tuong quan ROI trong ngay `ICC = 0.247`
   => **4.88 vi the ~ 2.49 cuoc**, **30 vi the ~ 3.68 cuoc**, **TRAN tuyet doi 1/ICC = 4.05 cuoc**.
6. **Them symbol: CO giup, nhung bi chan cung.** Toi da (vo han vi the moi thoi diem) chi giam
   `sd` **1.275 lan** => MDE80 7.66 -> 6.01pp o DEV. Khong bao gio hon he so 1.28-1.44.
7. **Rut ngan time-stop: KHONG mua duoc power.** Ba ho, cung do dai khoi: MDE80 giam **5.1%**
   (D1: 336h->96h), **4.1%** (R2: 240h->120h), 14.6% (ho S, degenerate). Nguong luat da chot la
   25%. Do dai khoi do duoc **khong** ty le voi time-stop.
8. **CAU 5: KHONG.** MDE80 san kha thi = **3.78pp** — va o do can dong thoi 6.31 nam du lieu
   (gom ca VAL) + **vo han** vi the moi thoi diem. Kich ban thuc te nhat (6.00 nam, bo 5 feature
   OI, train lai, giu hang ngang hien tai) cho **4.94pp**. Can **10.0-16.3 nam** de dat 3pp.
9. => Moi quyet dinh phai chuyen han ve **tang xep hang** (rank-IC +0.0973 CI [+0.0711,+0.1152];
   gate edge +0.0182 CI [+0.0085,+0.0227], n_eff 39-52 khoi). Tang equity chi con dung cho
   **rang buoc cung** (maxDD) va sanity.
10. Nhan xet khoi diem cua Uni **dung 2/3** (so khoi ~ thoi gian lich; them symbol khong tang so
    khoi) va **sai 1/3** o cho quan trong nhat: so khoi khong phai co mau hieu dung, va rut ngan
    khoi lam CI **rong** ra chu khong hep lai. Chi tiet §8.

---

## 0. TAI LAP KIEM CHUNG (PREREG_NBETS §8.3) — KHOP TUYET DOI

| kiem chung | so cho truoc | do duoc | ket |
|---|---|---|---|
| `C2b` vs `C2_g015`, khoi 21: `d` / CI95 / `sd` | +7.33pp / [−1.72, +15.61] / 4.45pp | **+7.326 / [−1.717, +15.609] / 4.4516** | **KHOP** |
| `A6_ts96` vs `A6_ts336`, khoi 21: MDE80 | 6.437pp | **6.437pp** | **KHOP** |
| `boot_sum` (cumsum) vs `x[idxmat].sum()` (`ci_group_a.py`) | 0 | maxdiff **0.000e+00** o L=3/21/42 | **KHOP** |

Chuoi equity: 11 run, deu **911 ngay** `20220101..20240629`, cung lich.

---

## 1. CAU 1 — DO DAI PHU THUOC THAT (do, khong chon)

Estimator CHINH: **Politis-White (2004) + PPW (2009)** cho circular block bootstrap (`L_PW`).
Kiem cheo: plateau variance-ratio (`L_VR`). Luat chot truoc: `L_est = max(L_PW, L_VR)`.

### 1.1 Chuoi HIEU (cap) — day la chuoi ma CI cua hieu duoc tinh tren

| ma | cap | `L_PW` | `L_VR` | `L_est` | `phi_1` | `VR(3)` | `VR(21)` | `VR(63)` |
|---|---|---|---|---|---|---|---|---|
| Q1 | `C2b` vs `C2_g015` (selector) | **10** | 2 | **10** | **−0.293** | 0.665 | 0.637 | 0.665 |
| Q2 | `C2b` vs `N4_a8s175` (exit-param) | **3** | 1 | **3** | −0.041 | 0.947 | 0.786 | 0.520 |
| T1 | `A6_ts96` vs `A6_ts336` | 3 | 2 | 3 | −0.286 | 0.752 | 0.767 | 0.714 |
| T2 | `R2_ts120` vs `R2_ts240` | 7 | 3 | 7 | −0.234 | 0.617 | 0.535 | 0.473 |
| T3 | `S3_ts168` vs `S4_ts720` | 3 | 1 | 3 | −0.057 | 0.931 | 0.566 | 0.359 |

### 1.2 Chuoi DON

| run | `L_PW` | `L_VR` | `phi_1` | `sd` ngay | ESS `= 911/VR(L_VR)` |
|---|---|---|---|---|---|
| `C2b` | 4 | 63* | −0.0845 | 0.00801 | **1826** |
| `C2_g015` | 9 | 14 | −0.2041 | 0.01086 | 1624 |
| `N4_a8s175` | 6 | 42 | −0.1194 | 0.00907 | 1657 |
| `A6_ts96` | 19 | 7 | −0.1837 | 0.00871 | 1553 |
| `D1_full_ts` | 8 | 10 | −0.1887 | 0.00888 | 1602 |
| `A6_ts336` | 8 | 7 | −0.1869 | 0.00899 | 1499 |
| `R2_ts120` | 17 | 42 | −0.1102 | 0.00609 | 1919 |
| `R0_parity` | 5 | 42 | −0.1105 | 0.00608 | 1749 |
| `R2_ts240` | 5 | 10 | −0.1106 | 0.00617 | 1398 |
| `S3_ts168` | 52 | 63* | −0.3428 | 0.00014 | 5311 |
| `S4_ts720` | 15 | 63* | −0.3040 | 0.00015 | 4721 |

Hai run cuoi (`S3`/`S4`, script `dev_sl.sh`) co **margin trung vi 6.1 USDT** (so voi 968.8 cua
`C2b`) — equity di dong 0-4 USDT/ngay, tuc **lam tron so nguyen cua `sim.out` chiem mot phan dang
ke phuong sai**. Do la nguyen nhan co cau cua `phi_1 = −0.34` va cua ESS 4700-5300. Ca ho **S**
(va do do cap **T3**) vi vay la **degenerate ve sizing**; so cua no duoc bao cao nhung **khong
mang thong tin** ve cau hoi cong suat. Ghi ro thay vi am tham bo — danh sach cap da chot o
`PREREG_NBETS` §1.1.

`*` = **luat plateau cua chinh pre-reg nay bi mot khuyet diem**, ghi thang: o `L = 63` (diem cuoi
luoi) cua so kiem `[L, min(4L,63)]` **thu lai thanh mot diem** nen dieu kien lech <= 10% dung
**hien nhien**. Vay `L_VR = 63` cho `C2b` / `S3` / `S4` khong phai "co plateau" ma la "**khong
dat plateau trong luoi**" cong voi fallback. Da khai bao khuyet diem nay thay vi sua luat sau khi
thay ket qua. Huong cua no la **bao thu ve L**, nhung xem §2.3: voi phu thuoc AM thi `L` lon lai
la **anti-conservative ve sd** — nen no khong an toan tu dong, va vi vay cong kiem phu §2 moi la
cai quyet dinh.

### 1.3 Phat hien trung tam cua Cau 1

**Chuoi loi nhuan ngay khong phu thuoc DUONG. No phu thuoc AM (mean-reverting).**
`phi_1` tu −0.041 den −0.343; `VR(L) < 1` voi **moi** `L > 1` tren **moi** chuoi va **moi** cap.

He qua truc tiep, do duoc:

| cap | MDE80 @ L=1 (iid) | @ L=3 | @ L=21 (cu) | @ L=63 |
|---|---|---|---|---|
| Q2 exit-param | 8.029pp | **7.664pp** | **7.186pp** | 5.693pp |
| Q1 selector | 15.443pp | 12.877pp | **12.471pp** | 13.093pp |
| T1 time-stop | 7.588pp | 6.605pp | 6.437pp | 6.430pp |
| T2 time-stop | 5.322pp | 4.095pp | 3.777pp | 3.587pp |

**Rut ngan khoi lam CI RONG ra.** Cai "tu phuc vu" o bo du lieu nay la **keo DAI** khoi, khong
phai rut ngan. Toan bo canh bao hanh vi trong de bai (va trong `PREREG_NBETS` §3.6 do chinh toi
viet) huong **nguoc** voi thuc te. Ghi lai de lan sau khong lap.

---

## 2. CAU 2 — CONG KIEM PHU (COVERAGE). Bang bat buoc

`N_MC = 1000` chuoi tong hop moi o, `N_BOOT = 1000`, `T = 911`, dai luong gate
`dg = 365*mean(d_t)`, dich = `365*mu`. Sai so Monte Carlo cua do phu = **0.69pp**.
Dai chap nhan chot truoc: **[0.92, 0.97]**. `< 0.92` = **DUOI PHU = khoi SAI**.
`rong CI` don vi **%/nam**.

### 2.1 Doi chung co do phu thuoc DA BIET — cong cu duoc chung minh NHAY

| L | n_khoi | `G1` iid (span 1) | `G2a` AR(.3) tau=1.9 | `G2b` AR(.6) tau=4 | `G3a` MA span **7** | `G3b` MA span **21** | `G2c` AR(.9) tau=19 |
|---|---|---|---|---|---|---|---|
| 1 | 911 | **0.948** | 0.849 | 0.690 | 0.562 | 0.318 | 0.368 |
| 2 | 456 | **0.948** | 0.886 | 0.784 | 0.664 | 0.439 | 0.457 |
| 3 | 304 | **0.943** | 0.902 | 0.823 | 0.776 | 0.517 | 0.548 |
| 5 | 183 | **0.944** | 0.917 | 0.903 | 0.830 | 0.629 | 0.622 |
| 7 | 131 | **0.932** | **0.945** | 0.905 | 0.880 | 0.677 | 0.694 |
| 10 | 92 | **0.929** | **0.929** | 0.915 | 0.913 | 0.741 | 0.761 |
| 14 | 66 | **0.949** | **0.949** | **0.922** | 0.909 | 0.830 | 0.820 |
| 21 | 44 | **0.931** | **0.941** | **0.932** | **0.930** | 0.878 | 0.827 |
| 28 | 33 | **0.939** | **0.937** | **0.935** | **0.921** | 0.898 | 0.871 |
| 42 | 22 | 0.917 | **0.929** | **0.935** | **0.937** | 0.917 | 0.884 |
| 63 | 15 | **0.929** | **0.934** | 0.918 | **0.923** | 0.910 | 0.912 |

In dam = PASS (trong [0.92, 0.97]). Ban goc day du (co ca cot rong CI) o
`/home/ubuntu/nbets/step2.out`. `G1` o `L=42` cho 0.917 — thap hon 0.92 khoang **0.4 sai so MC**,
doc la nhieu MC chu khong phai duoi phu that.

**Ba dieu bang nay chung minh:**

1. **Cong cu bat duoc duoi phu.** Voi span phu thuoc **dung 7 ngay** (`G3a`), moi `L <= 14`
   DUOI PHU (0.562 -> 0.909) va chi PASS tu `L >= 21`. Tuc **khoi phai dai ~3 lan span phu
   thuoc**, khong phai bang span. Do la mot luat dinh luong moi, do duoc.
2. **Voi span 21 ngay (`G3b`) hoac AR(.9) (`G2c`) thi KHONG CO do dai khoi nao trong luoi PASS**
   (max 0.917 o `L=42`, va o do chi con 22 khoi). Neu lap luan cua `PREREG_CI` §2.2 dung — "lenh
   song >= 7 ngay nen phu thuoc >= 7 ngay, chon 21 cho an toan" — thi voi span thuc 21 ngay
   **toan bo he thong CI cua du an se vo hieu**, khong chi hep hay rong. Do la mot dieu kien phai
   nhin thay: phan quyet §2.4 duoi day **phu thuoc** vao viec do dai phu thuoc THAT chi 3-10 ngay.
3. **Duoi phu o dau LON cung ton tai**: `G2b` o `L=63` roi ve 0.918 (15 khoi) — hong vi **qua it
   khoi**, khong vi khoi qua ngan. Luoi chi dung duoc den ~42 ngay.

### 2.2 Generator HIEU CHUAN THEO CHUOI THAT (`G4`) — day la cong gate

AR(1) voi `phi` = tu tuong quan tre-1 do tu **chinh chuoi hieu that** cua tung cap, `sd` khop
chuoi that. Do phu `dg` / **rong CI (%/nam)**:

| L | n_khoi | `G4_Q1` (phi −0.29) | `G4_Q2` (phi −0.04) | `G4_T1` (phi −0.29) | `G4_T2` (phi −0.23) | `G4_T3` (phi −0.06) |
|---|---|---|---|---|---|---|
| 1 | 911 | 0.987 / 19.69 bao-thu | **0.962** / 8.75 | 0.990 bao-thu | 0.984 bao-thu | **0.950** / 0.211 |
| 2 | 456 | 0.979 / 16.53 bao-thu | **0.959** / 8.56 | **0.960** / 7.69 | **0.961** / 5.45 | **0.957** / 0.204 |
| 3 | 304 | **0.966** / 16.03 | **0.941** / 8.49 | 0.978 bao-thu | **0.969** / 5.29 | **0.951** / 0.202 |
| 5 | 183 | **0.959** / 15.42 | **0.943** / 8.42 | 0.974 bao-thu | **0.954** / 5.13 | **0.955** / 0.201 |
| 7 | 131 | **0.964** / 15.15 | **0.950** / 8.41 | **0.949** / 7.07 | **0.958** / 5.05 | **0.940** / 0.200 |
| 10 | 92 | **0.960** / 14.89 | **0.955** / 8.41 | **0.940** / 6.95 | **0.947** / 4.99 | **0.949** / 0.199 |
| 14 | 66 | **0.941** / 14.76 | **0.943** / 8.29 | **0.943** / 6.87 | **0.954** / 4.96 | **0.927** / 0.198 |
| **21** | 44 | **0.932** / 14.55 | **0.939** / 8.27 | **0.938** / 6.74 | **0.954** / 4.88 | **0.946** / 0.198 |
| 28 | 33 | **0.932** / 14.38 | **0.942** / 8.21 | **0.936** / 6.70 | **0.948** / 4.82 | **0.936** / 0.196 |
| 42 | 22 | **0.947** / 14.24 | **0.930** / 8.10 | **0.921** / 6.57 | **0.936** / 4.75 | **0.940** / 0.193 |
| 63 | 15 | **0.937** / 13.99 | **0.934** / 7.97 | **0.935** / 6.46 | **0.925** / 4.73 | **0.928** / 0.189 |

**Khong o nao DUOI PHU.** Voi cau truc phu thuoc that (AM, ngan) thu tuc bootstrap cua
`PREREG_CI` phu dung o **moi** do dai khoi tu 1 den 63 ngay; cac o `L <= 5` cua `G4_Q1`/`G4_T1`
la **BAO THU** (do phu 0.974-0.990, CI rong hon can thiet). Chieu bien thien cua cot
`rong CI` la **giam don dieu theo L** o ca 5 cap — dau hieu tuc thi cua phu thuoc AM.

### 2.3 `L_valid` theo luat da chot (`PREREG_NBETS` §3.5)

`L_valid` = `L` nho nhat thoa `L >= L_est` **va** PASS kiem phu tren `G4` cua chinh cap do.

| ma | `L_est` | **`L_valid`** | do phu tai `L_valid` | so khoi | `sd(dCAGR)` | **MDE80** | (so sanh) MDE80 @ L=21 cu |
|---|---|---|---|---|---|---|---|
| **Q2** exit-param | 3 | **3 ngay** | 0.941 | **304** | 2.7355pp | **7.664pp** | 7.186pp |
| **Q1** selector | 10 | **10 ngay** | 0.960 | **92** | 4.8655pp | **13.631pp** | 12.471pp |
| T1 time-stop | 3 | **7 ngay** | 0.949 | 131 | 2.3200pp | **6.500pp** | 6.437pp |
| T2 time-stop | 7 | **7 ngay** | 0.958 | 131 | 1.4612pp | **4.094pp** | 3.777pp |
| T3 (degenerate) | 3 | 3 ngay | 0.951 | 304 | 0.0514pp | 0.144pp | 0.111pp |

### 2.4 PHAN QUYET VE CAC CI CU

- **Khoi 21 ngay (tang equity, `CI_REAUDIT` nhom A): QUA cong kiem phu** (do phu 0.932-0.947).
  Cac CI cu **hop le**, khong bi vo hieu. Nhung chung nam o **ria duoi** cua dai va **hep hon
  4-7%** so voi khoi hop le ngan hon. Tuc: **CI cu hoi HEP QUA, khong phai rong qua.** Moi ket
  luan "khong phan biet duoc" cua `CI_REAUDIT` vi vay **cang chac hon**, khong yeu di. **Khong
  co verdict nao duoc mo lai boi bao cao nay.**
- **Khoi 3 ngay = 72h (do dai ma nhom B / `TICKLOG` dung) cung PASS** o tang **equity**. Nhung
  **canh bao pham vi**: kiem phu o day chay tren **chuoi loi nhuan NGAY cua equity**. No **KHONG**
  chung nhan khoi 72h cho **chuoi tick / xep hang** cua nhom B — do la chuoi khac, cau truc phu
  thuoc khac (nhan `g1lite` cua so 72h la phu thuoc **DUONG** theo thiet ke, khong am). Kiem phu
  cho nhom B **chua duoc lam** va la lo hong con lai (§9).

---

## 3. `n_eff` THAT CUA C2b — ba cach dem KHAC NHAU, khong duoc tron

| cach dem | y nghia | gia tri |
|---|---|---|
| (1) **so don vi resample** = `ceil(911/L)` | so khoi bootstrap. **KHONG phai co mau hieu dung** | `L=3` -> **304** · `L=10` -> 92 · `L=21` -> **44** · `L=63` -> 15 |
| (2) **ESS variance-ratio** = `T * V(1)/V(L)` | so **ngay iid tuong duong** cua chuoi C2b | `L=3` -> **1089** · `L=10` -> 1320 · `L=21` -> **1506** · `L=63` -> **1826** |
| (3) **so CUOC hieu dung** tren ROI tung lenh, `N^2 s^2 / Var(sum)` | bao nhieu cuoc doc lap trong 970 lenh | `L=3` -> **251** · `L=10` -> **298** · `L=21` -> 297 (= **0.31 cuoc / lenh**) |

**Kiem chung so hoc bat buoc doc:** neu co mau hieu dung that la **44** thay vi 911 thi bootstrap
khoi 21 phai cho `sd` **lon hon** bootstrap iid `sqrt(911/44) = 4.55` lan. Do duoc:
`sd(dCAGR, Q2)` = 2.8658pp o `L=1` va 2.5651pp o `L=21` => ti le **0.895**, tuc **nho hon 1**.

> **Con so "n_eff = 44 khoi" trong `CI_REAUDIT` (nhom A) va "304 khoi 72h" trong
> `TICKLOG_RESULT` la SO DON VI RESAMPLE, khong phai co mau hieu dung.** Doc no nhu co mau hieu
> dung la sai **~20-40 lan va sai chieu**. ESS that cua chuoi equity ngay DEV la **>= 911**,
> khong phai 44.

Vay **nut co that o tang equity la gi?** Khong phai `n_eff`. La **do lon cua nhieu ngay**:
`sd` ngay cua chuoi hieu cap Q2 la **0.187%/ngay** => `sd` cua hieu CAGR do tren **1 nam** la
`sqrt(365) * 0.187% = 3.57pp`. Hieu can phat hien la **3pp**. Tuc **ti so tin/nhieu tren 1 nam la
0.84**, va vi `sd` giam theo `1/sqrt(T)` ta can `2.80158/0.84` do sd => **~11 nam**. Do la toan bo
bai toan, phat bieu bang mot dong, khong can khai niem "so khoi".

---

## 4. CAU 3 — HANG DOC LAP THEO CHIEU NGANG

### 4.1 Cung giu dong thoi (dem tren luoi 60 phut, 2022-01-01..2024-06-30)

| run | n lenh | mean | median | p90 | max | mean khi >= 1 | % gio KHONG co vi the | n symbol |
|---|---|---|---|---|---|---|---|---|
| **C2b** | 970 | **1.83** | 0 | 6 | **29** | **4.88** | **62.5%** | 241 |
| `C2_g015` | 1583 | 4.03 | 0 | 10 | 91 | 9.51 | 57.6% | 274 |
| `N4_a8s175` | 974 | 2.16 | 0 | 7 | 34 | 5.24 | 58.7% | 244 |
| `A6_ts96` | 1837 | 3.80 | 1 | 10 | 78 | 6.28 | 39.6% | 274 |
| `D1_full_ts` | 1809 | 4.24 | 1 | 11 | 81 | 6.74 | 37.1% | 274 |
| `A6_ts336` | 1794 | 5.10 | 2 | 13 | 81 | 7.43 | 31.4% | 274 |
| `R2_ts120` | 1128 | 1.24 | 0 | 4 | 28 | 4.45 | 72.2% | 244 |
| `R2_ts240` | 1100 | 1.81 | 0 | 6 | 28 | 4.29 | 57.7% | 244 |

**C2b khong he giu 30 vi the.** No giu **1.83** trung binh va **khong co vi the nao trong 62.5%
so gio**. Con so 30 chi la **max** (dat duoc trong mot vai gio).

### 4.2 Tuong quan trong cohort va so cuoc hieu dung

`x_i = pnl_i / margin_i`. ICC mot chieu (ANOVA), cohort = cung ngay vao lenh (chinh),
kiem do ben cung khoi 72h va cung tuan. `n_eff(k) = k / (1 + (k-1)*ICC)`.

| run | cohort | J | N | ICC | `n_eff(k=mean|>=1)` | `n_eff(k=30)` | **TRAN `1/ICC`** |
|---|---|---|---|---|---|---|---|
| **C2b** | ngay | 101 | 952 | **+0.2468** | **2.49** (k=4.88) | **3.68** | **4.05** |
| **C2b** | 72h | 79 | 959 | +0.2506 | 2.47 | 3.63 | 3.99 |
| **C2b** | tuan | 62 | 964 | +0.1618 | 3.00 | 5.27 | 6.18 |
| `C2_g015` | ngay | 110 | 1566 | +0.2670 | 2.91 (k=9.51) | 3.43 | 3.75 |
| `A6_ts96` | ngay | 111 | 1822 | +0.2423 | 2.76 (k=6.28) | 3.74 | 4.13 |
| `R2_ts120` | ngay | 107 | 1108 | +0.1743 | 2.78 (k=4.45) | 4.96 | 5.74 |

**ICC = 0.16 - 0.27 o TAT CA 11 run va ca 3 dinh nghia cohort.** Rat on dinh.

### 4.3 TRA LOI BANG SO CHO "THEM SYMBOL CO MUA DUOC GI KHONG"

> **30 vi the dong thoi = 3.68 cuoc doc lap. Vo han vi the dong thoi = 4.05 cuoc.**
> C2b hien tai (4.88 vi the khi co vi the) = **2.49 cuoc**.

- Tang tu 4.88 len 30 vi the (gap **6.1 lan** so vi the) mua duoc `3.68/2.49` = **1.48 lan**
  so cuoc => `sd` giam **`sqrt(1.48) = 1.22` lan** => MDE80 cap exit-param 7.664 -> **6.31pp**.
- Tang len **vo han** vi the mua duoc **1.63 lan** so cuoc => `sd` giam **1.275 lan** =>
  MDE80 -> **6.01pp**.
- Do nhay theo dinh nghia cohort: he so giam `sd` toi da = **1.275** (cohort ngay), **1.270**
  (72h), **1.436** (tuan). Ngay ca so lac quan nhat (1.436) chi dua MDE80 ve **5.34pp** o DEV.

=> **De bai doan gan dung nhung chua du xau: "30 vi the ~ 2-3 cuoc" — do duoc la 3.68 cuoc, va
tran cung la 4.05.** Nhan xet "thay them symbol khong mua duoc gi" **khong hoan toan dung**: no
mua duoc mot he so **1.22-1.28** ve `sd`. Do la **that** nhung **khong doi dau bai** (can he so
2.5).

### 4.4 Kiem cheo bang quan sat (co gioi han, da ghi truoc)

Hoi quy `log(sdCAGR)` theo `log(N_lenh)` tren 11 chuoi don (`L=21`): `beta = -2.94`
(se 2.01, CI95 [−6.88, +1.01]), `r = −0.44`. **Vo dung**: he so bi keo hoan toan boi hai run
degenerate ho **S** (`sd` 0.08pp vi margin trung vi 6.1 USDT). Bo hai run do thi con 9 diem va
**quan he bien mat** (`C2b` N=970 sd=9.67 · `A6_ts96` N=1837 sd=8.81 · `C2_g015` N=1583 sd=11.47
· `R2_ts120` N=1128 sd=6.28). Ket luan dung tu muc nay: **`sd(CAGR)` khong phai la ham cua so
lenh** — no la ham cua **muc phoi nhiem/sizing** cua tung cau hinh. Day dung nhu canh bao
"khong phai thi nghiem co doi chung" da ghi trong `PREREG_NBETS` §5.4.

---

## 5. CAU 4 — RUT NGAN TIME-STOP CO TANG `n_eff` KHONG

Ba **ho** run cung base, chi khac `SIM_LOSER_TIME_STOP_HOURS` (xac minh tu script goc:
`dev_abl.sh`, `dev_rob.sh`, `dev_sl.sh`).

### 5.1 Bang chinh — time-stop x do dai khoi x so khoi x MDE80

| ho | run | TS (h) | gio giu that: median / p90 | `L_PW` | `L_VR` | `L_est` | so khoi | `sd(CAGR)` @ `L_est` | **MDE80** @ `L_est` |
|---|---|---|---|---|---|---|---|---|---|
| D1 | `A6_ts96` | **96** | 19 / 96 | 19 | 7 | 21 | 44 | 8.810pp | 24.681pp |
| D1 | `D1_full_ts` | **168** | 20 / 168 | 8 | 10 | 10 | 92 | 9.469pp | 26.528pp |
| D1 | `A6_ts336` | **336** | 20 / 203 | 8 | 7 | 10 | 92 | 9.779pp | 27.397pp |
| R2 | `R2_ts120` | **120** | 4 / 120 | 17 | 42 | 42 | 22 | 5.916pp | 16.573pp |
| R2 | `R0_parity` | **168** | 4 / 166 | 5 | 42 | 42 | 22 | 6.173pp | 17.295pp |
| R2 | `R2_ts240` | **240** | 4 / 169 | 5 | 10 | 10 | 92 | 7.094pp | 19.874pp |
| S* | `S3_ts168` | **168** | 19 / 168 | 52 | 63* | 63 | 15 | 0.072pp | 0.201pp |
| S* | `S4_ts720` | **720** | 20 / 203 | 15 | 63* | 63 | 15 | 0.083pp | 0.232pp |

`L_est` khac nhau giua cac run trong cung ho lam bang tren **khong so sanh sach duoc**. So sanh
sach = **cung mot do dai khoi**:

| ho | MDE80 @ **L = 7 ngay** (cung khoi) | giam toi da trong ho | luat da chot |
|---|---|---|---|
| **D1** | TS96 = **26.42pp** · TS168 = 27.29pp · TS336 = **27.84pp** | **5.1%** | can > 25% |
| **R2** | TS120 = **19.59pp** · TS168 = 20.13pp · TS240 = **20.44pp** | **4.1%** | can > 25% |
| S* | TS168 = 0.27pp · TS720 = 0.31pp | 14.6% | (degenerate) |

Cap ghep trong ho (hieu, `L_valid`): `T1` (96h vs 336h) MDE80 = **6.500pp**;
`T2` (120h vs 240h) MDE80 = **4.094pp**.

### 5.2 Phan quyet theo luat chot truoc (`PREREG_NBETS` §6)

- **Don dieu: CO** — MDE80 giam khi time-stop ngan lai o **ca 3** ho (2/3 khong degenerate).
- **Muc giam > 25%: KHONG** — do duoc 5.1% (D1) va 4.1% (R2).
- => **"Rut ngan time-stop KHONG mua duoc power."**

### 5.3 Va do dai phu thuoc **khong** ty le voi time-stop

Day la phep do truc tiep cho gia thiet cua de bai:

| ho | TS 96/120 | TS 168 | TS 240/336 |
|---|---|---|---|
| `L_PW` ho D1 | 19 | 8 | 8 |
| `L_PW` ho R2 | 17 | 5 | 5 |
| `L_VR` ho D1 | 7 | 10 | 7 |
| `L_VR` ho R2 | 42 | 42 | 10 |

**Khong co quan he.** Neu gia thiet "phu thuoc bi chi phoi boi thoi gian giu lenh" dung thi
`L_PW` phai **tang** theo time-stop; do duoc no **giam** (19 -> 8 va 17 -> 5), tuc nguoc chieu.
Ly do co cau, do duoc: **median gio giu that chi 4-20 gio**, khong phai 96-336 gio — time-stop la
**tran cho duoi phan phoi**, nen doi tran khong doi phan than cua phan phoi thoi gian giu.
Voi **2-3 diem moi ho** thi day la ba lan quan sat, **khong ve duong xu huong** (dung luat §6).

---

## 6. CAU 5 — CO CAU HINH NAO DO DUOC 3pp KHONG

Neo (theo `PREREG_NBETS` §7): cap **de nhat** `Q2` (chi doi tham so exit),
`sd_dev = 2.7355pp` o `L_valid = 3` ngay (do dai khoi **da qua cong kiem phu**),
`T_dev = 2.4959` nam, `MDE80 = z * sd * sqrt(T_dev/T) / f_ngang`, `z = 2.80158`.

| kich ban du lieu | T (nam) | hang ngang **nguyen trang** (k=4.88) | hang ngang **k=30** | hang ngang **TRAN** (k vo han) |
|---|---|---|---|---|
| DEV hien tai | 2.50 | **7.66 pp** | 6.31 pp | 6.01 pp |
| lui 2021-12, giu 5 feature OI | 2.58 | 7.54 pp | 6.21 pp | 5.91 pp |
| DEV + VAL gop (**tieu thu VAL lam du lieu do**) | 3.96 | 6.08 pp | 5.01 pp | 4.77 pp |
| lui 2020-01, **BO 5 feature OI + train lai** | 4.50 | 5.71 pp | 4.70 pp | 4.48 pp |
| **TOI DA co the co**: 2020-01..2025-12 gop | 6.00 | 4.94 pp | 4.07 pp | **3.88 pp** |
| toi da + 2019-09 qua REST (khong thuc te) | 6.31 | 4.82 pp | 3.97 pp | **3.78 pp** |

**MDE80 san kha thi = 3.78 pp** (va o day "kha thi" da rat rong tay: 6.31 nam gom ca VAL, bo 5
feature OI, train lai tu dau, **va** gia dinh giu **vo han** vi the moi thoi diem).

So nam can de dat 3pp:

| hang ngang | so nam can |
|---|---|
| nguyen trang (k = 4.88) | **16.3 nam** |
| k = 30 vi the/thoi diem | **11.0 nam** |
| k vo han (TRAN `1/ICC` cohort-ngay) | **10.0 nam** |
| k vo han, `ICC` cohort-tuan (lac quan nhat) | **7.9 nam** |

Cho cap **kho hon** (`Q1`, doi selector, `L_valid = 10`): MDE80 = **13.63pp** o DEV, **10.82pp**
o 3.96 nam, **8.79pp** o 6.00 nam — cach 3pp **gap 3 lan**.

### TRA LOI DUT KHOAT: **KHONG**

**Khong co cau hinh nao do duoc mot cai thien 3pp CAGR bang du lieu kha dung.** MDE80 san kha
thi la **3.78pp** (va **4.94pp** o kich ban thuc te nhat: 6 nam du lieu, hang ngang nhu hien
tai), cho cap so sanh **de nhat**. Cap doi selector — dung loai cap ma du an thuc su muon phan
biet — con cach **gap 3 lan**.

Ba lever da duoc do het va khong lever nao du:

| lever | he so tot nhat ve `sd` | ghi chu |
|---|---|---|
| do dai khoi (Cau 1+2) | **0.94** = lam **XAU** di 6% | phu thuoc AM: khoi hop le ngan hon => CI **rong** hon. **Da nam trong** neo 7.66pp, khong nhan tiep vao tich |
| hang ngang / them symbol (Cau 3) | **1.28** (toi da 1.44) | chan cung boi `1/ICC = 4.05` cuoc |
| thoi gian du lieu (`DATA_EXTENT_SURVEY`) | **1.55** (2.50 -> 6.00 nam) | doi lai: bo 5 feature OI + train lai + tieu thu VAL |
| rut time-stop (Cau 4) | **1.02** | do duoc 4-5%, duoi nguong 25% |
| **tich BA lever con lai** | **2.02** = 1.28 x 1.55 x 1.02 | can **2.55** de tu 7.66pp ve 3pp. `7.664/2.024 = 3.79pp` — khop san do duoc 3.78pp |

Thieu he so **1.26 ve `sd`** = thieu **1.6 lan ve thoi gian** ngay ca khi gop **tat ca** lever
cung luc, ke ca cac lever khong thuc hien duoc (vo han vi the) va khong duoc phep (tieu thu VAL
lam du lieu do se **pha chuc nang out-of-sample cua VAL** — khi do khong con tap nao de xac nhan).

### He qua bat buoc

**Moi thi nghiem o tang equity tu nay la vo ich neu muc dich la PHAN BIET hai cau hinh.** Tang
equity chi con hai vai tro hop le:
1. **rang buoc cung** (`maxDD <= 15%`, khong nam am, chi phi stress) — quan sat mot lan, khong
   can CI (`PREREG_CI` §2.5 da cam bootstrap `maxDD`);
2. **sanity ha nguon** — kiem mot cau hinh khong sup, khong xep hang finalist.

**Quyet dinh phai chuyen han ve tang xep hang**, noi da co bang chung **song** voi `n_eff` chi
39-52 khoi 72h: rank-IC `+0.0973` CI95 `[+0.0711, +0.1152]` (`CI_REAUDIT` #7) va gate edge
`+0.0182` CI95 `[+0.0085, +0.0227]` (#8). Ly do dinh luong cho su bat doi xung nay khong phai
"nhieu khoi hon" — la **do lon nhieu tren mot quan sat**: nhom B do 3,030-36,183 ket qua rieng le
voi nhieu nho tren tung ket qua, nhom A do **mot** duong equity co `sd` ngay 0.19-0.8%.

---

## 7. NHAN XET KHOI DIEM CUA CHU DU AN — DUNG CHO NAO, SAI CHO NAO

### 7.1 DUNG (do duoc, khong phan bien)

1. **"So khoi 72h ~ thoi gian lich / 72h"**: 911 ngay / 3 = 303.67 -> **304 khoi**. Dung chinh
   xac. So khoi la **ham cua lich**, khong phai cua so lenh.
2. **"Them symbol khong tang so KHOI"**: dung — lenh trong cung cua so 72h nam cung mot khoi.
   Do duoc: `A6_ts96` co 1837 lenh (gap 1.9 lan `C2b`) nhung van dung **304** khoi 72h /
   911 ngay lich.
3. **"Khuyen nghi trong `CI_REAUDIT` §5 (muc HE QUA 4b) va `PREREG_GS` §12.4 can sua"**: dung,
   nhung **khong** vi ly do "them symbol la ao". Ly do dung la: them symbol mua duoc **1.22-1.28
   lan** ve `sd` chu khong phai `sqrt(6)` = 2.45 lan nhu cach doc "them 6 lan so cuoc". Con so
   dung de ghi vao hai file do la **tran `1/ICC` = 4.05 cuoc doc lap moi thoi diem**.

### 7.2 SAI (va day la cho quan trong nhat)

1. **"Nut co la SO KHOI DOC LAP"** — **sai**. So khoi la don vi resample, khong phai co mau hieu
   dung. ESS that cua chuoi equity ngay la **1089-1826 ngay iid tuong duong** (**> 911**), va
   bootstrap iid cho `sd` **lon hon** bootstrap khoi 21 (ti le 0.895, khong phai 4.55). Nut co
   that la **bien do nhieu ngay** (0.187%/ngay tren chuoi hieu cap exit-param) so voi **do lon
   cua hieu ung** (3pp/nam). Hai cach phat bieu dan den hai ke hoach hanh dong **khac nhau**:
   "tang so cuoc doc lap" (theo cach doc sai) vs "giam bien do nhieu hoac doi dai luong do"
   (theo cach doc dung).
2. **"Neu phu thuoc that ngan hon 72h thi khoi 72h la qua bao thu va `n_eff` that lon hon"** —
   **sai dau**. Do duoc: phu thuoc la **AM**, `VR(L) < 1` voi moi `L > 1`. Khoi **ngan hon** cho
   CI **RONG hon** (Q2: 7.19pp o khoi 21 -> 7.66pp o khoi 3). Rut ngan khoi la hanh vi
   **tu trung phat**, khong phai tu phuc vu. Toan bo canh bao hanh vi trong de bai (va trong
   `PREREG_NBETS` §3.6 do chinh toi viet theo de bai) **huong nguoc thuc te**.
3. **"Neu ta giu N vi the ma chung tuong quan rat cao (crypto di theo BTC) thi N vi the chi dang
   vai cuoc"** — **dung ve co che, nhung tien de sai ve N**. `C2b` **khong** giu 30 vi the: no
   giu **1.83** trung binh va **62.5% so gio khong giu gi**. Cau hoi "30 vi the dang bao nhieu
   cuoc" la cau hoi ve mot cau hinh **khong ton tai**; cau tra loi (3.68) la mot **tran cho tuong
   lai**, khong phai chan doan hien tai. Chan doan hien tai la: **4.88 vi the = 2.49 cuoc**, va
   con **62.5% thoi gian von khong lam gi**.

### 7.3 Mot lever de bai KHONG neu ma so lieu chi ra

**62.5% so gio C2b khong co vi the nao** va `NO_BUDGET = 0` tren ca DEV (`TICKLOG_RESULT` §5:
von chua bao gio la rang buoc; rang buoc binding la gate MOM15 chiem 94.5% `GATE_REJECT`).
Tuc gioi han hien tai **khong** phai so symbol hay von — la **do chat cua gate**. Day la lever
duy nhat trong bang co khong gian lon chua duoc do, **va no khong thuoc pham vi job nay**
(do no doi hoi run moi => theo gioi han cung, toi **dung va bao** thay vi chay).

---

## 8. GHI CHU CHO CAC PRE-REG CUA NGUOI KHAC (KHONG SUA FILE CUA HO)

1. **`PREREG_CI.md` §2.2** — lap luan chon khoi 21 ngay ("lenh song >= 7 ngay nen tu tuong quan
   >= 7 ngay; block phai dai hon vong doi lenh") **khong duoc du lieu ho tro**: (a) median gio
   giu that la **4-20 gio**, khong phai 168; (b) tu tuong quan do duoc la **AM**, nen "block phai
   dai hon vong doi lenh" khong phai dieu kien dung huong. Ket luan cua `CI_REAUDIT` **khong
   doi** (khoi 21 PASS kiem phu), nhung **ly do** chon 21 nen ghi lai. De nghi, khong sua.
2. **`PREREG_CI.md` §2.4 / `CI_REAUDIT`** — cot ghi `n_eff` nen doi ten thanh **`n_khoi`**
   (so don vi resample). Chu `n_eff` dang bi doc thanh co mau hieu dung o `CI_REAUDIT` HE QUA (iii)
   muc 4 va o `TICKLOG_RESULT` §4.2/§6.3.
3. **`TICKLOG_RESULT` §6.3** — cau "**Nut co la SO KHOI DOC LAP (304 khoi 72h)**" nen sua thanh
   "nut co la bien do nhieu tren mot duong equity duy nhat". Ket luan **khong doi** (tang tan so
   lay mau khong mua duoc gi — dieu do van dung va da chung minh bang dong nhat telescope).
4. **`CI_REAUDIT` HE QUA (iii) muc 4b va `PREREG_GS` §12.4** — "tang so cuoc doc lap" nen di kem
   con so **tran `1/ICC` = 4.05 cuoc moi thoi diem** va he so `sd` toi da **1.28**, de khong ai
   ky vong `sqrt(N)`.
5. **Kiem phu cho nhom B chua ai lam.** Bao cao nay chi kiem phu tren chuoi equity ngay. Khoi
   72h cua nhom B (rank-IC, `g1_replay`) co cau truc phu thuoc **DUONG theo thiet ke** (nhan cua
   so 72h). Theo bang §2.1, voi phu thuoc duong span S thi khoi phai **~3S** moi PASS =>
   **khoi 72h cho nhan cua so 72h co the DUOI PHU**, va neu vay thi CI cua #7/#8 dang **hep qua**.
   Day la lo hong con mo va la **de nghi cho mot job sau** (can it nhat luoi khoi 216h/360h +
   generator co span 72h da biet). Toi **khong** tu mo rong pham vi.

---

## 9. KHUYET DIEM CUA CHINH BAO CAO NAY (ghi thang, khong giau)

1. **Luat plateau variance-ratio cua `PREREG_NBETS` §3.3 co lo o diem cuoi luoi** (§1.2 `*`):
   cua so kiem `[L, min(4L,63)]` thu ve mot diem khi `L = 63`, nen `L_VR = 63` doc ra "plateau"
   trong khi thuc te la "khong dat plateau". Da khai bao thay vi sua luat sau khi thay ket qua.
   Anh huong: chi len ba chuoi DON (`C2b`, `S3`, `S4`); **khong** len bat ky `L_valid` nao cua
   nam cap (cap dung `L_PW` lam rang buoc trong ca 5 truong hop).
2. **Ho `S` (cap `T3`) la degenerate ve sizing** (margin trung vi **6.1 USDT** vs 968.8 cua
   `C2b`; equity di 0-4 USDT/ngay nen **lam tron so nguyen cua `sim.out`** chiem phan dang ke
   phuong sai). Danh sach cap da chot truoc nen `T3` van duoc bao cao, nhung no **khong mang
   thong tin**. Luat "2/3 ho" cua §6 vi vay duoc doc tren hai ho khong degenerate (D1, R2), va
   ca hai cho cung ket qua => phan quyet khong phu thuoc vao viec co tinh `T3` hay khong.
3. **`pos.bin` cua `TickDecisionLog` khong doc duoc** (khong ton tai duoi `/home/ubuntu/java/`;
   `/home/ubuntu/tick/` bi cam). Vi vay Cau 3 **khong** dung pho tri rieng cua ma tran tuong quan
   duong loi nhuan mark-to-market giua cac vi the, ma dung **ICC ANOVA tren ROI cuoi cung cua
   tung lenh**. Han che: ICC do tuong quan **ket qua**, khong do tuong quan **duong di**; hai so
   nay co the khac. Neu `pos.bin` duoc mo, nen do lai bang participation-ratio cua pho tri rieng
   va doi chieu voi `ICC = 0.247`.
4. **Kiem phu chay `N_BOOT = 1000`** (so lieu that dung 2000) — da khai bao truoc o
   `PREREG_NBETS` §4.3, khong phai doi tham so sau.
5. **Hai generator bo sung `X_ar-.3` / `X_ar-.6` (AR(1) AM) KHONG duoc tien dang ky.** Chung
   duoc them **sau khi** do thay chuoi that phu thuoc am, va **khong duoc dung de gate** bat ky
   `L_valid` nao (gate chi dung `G4`, da pre-reg). Ket qua cua chung: PASS tu `L >= 2` (`phi=-0.3`)
   va tu `L >= 7` (`phi=-0.6`); truoc do la **BAO THU**, khong bao gio duoi phu — nhat quan voi
   `G4`.
6. **Suy dien "hang ngang -> `sd`" la mo hinh, khong phai do truc tiep.** Cong thuc
   `sd_tong ~ 1/sqrt(n_eff(k))` dung **neu** `ICC` giu nguyen khi tang `k`. Neu `ICC` **tang**
   theo `k` (them symbol nghia la them coin tuong quan hon voi phan con lai) thi loi ich con
   **nho hon** 1.28. Huong sai so nay lam ket luan **KHONG** cang chac.
7. **`MDE80(T) ~ 1/sqrt(T)` gia dinh cung che do thi truong** — gia dinh **lac quan**, y nhu
   `PREREG_CI` §5 da ghi. `DATA_EXTENT_SURVEY` §5 da do rang 2020-2021 la che do khac han
   (vol 76-81% vs 42-64%, mot ngay −40%). Huong sai so nay cung lam ket luan **KHONG** cang chac.

---

## 10. BAO CAO NAY **KHONG** LAM

- **Khong sua diem uoc luong nao**, khong mo lai / dong nhanh nao. `C2b` van `b:60390` /
  CAGR +24.43% / maxDD −13.12.
- **Khong sua `PREREG_CI.md`**, `PREREG_GS.md`, `PREREG_PAIRED.md`, `PREREG_TICKLOG.md`,
  `CI_REAUDIT.md`, `TICKLOG_RESULT.md`, `PAIRED_CALIB.md`, `DATA_EXTENT_SURVEY.md`. Moi de nghi
  sua nam o §8 cua **file nay**.
- **Khong chay java / backtest / train / tao run moi.** Khong bootstrap `maxDD`.
- **Khong cham VALIDATION / HOLDOUT.** Moi so tu DEV. Cot "T = 3.96 / 6.00 / 6.31 nam" trong §6
  la **tinh toan cong suat gia dinh**, khong phai mot phep do nao da chay tren VAL.
- **Khong kiem phu cho nhom B** (tang tick / xep hang) — xem §8.5, day la lo hong con mo.
- Khong cham `/home/ubuntu/gs/`, `/home/ubuntu/fs/`, `/home/ubuntu/g015/`, `/home/ubuntu/tick/`,
  `/home/ubuntu/feataudit/`, `/home/ubuntu/oifix/`. Khong submit Kaggle. Khong `git push`.
