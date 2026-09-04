# PREREG_COV — tien dang ky: KIEM PHU cho nhom TICK / XEP HANG (nhom B)

Chot luc: 2026-09-04, **TRUOC khi tinh bat ky do phu / L_valid nao**. Commit file nay phai co
truoc commit ket qua (`docs/COV_RESULT.md`); thu tu nguoc => ket qua VOID.

Pham vi: **CHI DEV**. Khong train lai, khong chay java, khong cham VALIDATION/HOLDOUT, khong
rebuild OI. Job nay **khong sinh alpha** — no chi noi **duoc phep tuyen bo bao nhieu** tu cac CI
da co.

## 0. LO HONG DUOC BIT — chinh NBETS tu khai

`NBETS_RESULT.md:212-214`: cong kiem phu cua NBETS chay tren **chuoi loi nhuan NGAY cua equity**;
no **KHONG chung nhan** khoi 72h cho **chuoi tick / xep hang** cua nhom B, vi do la chuoi khac va
nhan `g1lite` cua so 72h la phu thuoc **DUONG theo thiet ke** (khong am nhu chuoi equity).
`NBETS_RESULT.md:490`: "**Kiem phu cho nhom B chua ai lam.**"

Vi sao phai bit TRUOC C1/C2: nhom B la **thuoc do duy nhat con song** sau NBETS (tang equity da
chet). Neu khoi 72h **duoi phu** o nhom B thi moi `sd_boot` cua nhom B dang **qua nho** => moi CI
dang **qua hep** => cac verdict dua tren no phai doc lai. Do la **thuoc** cua C1 (cat feature) va
C2 (gate) — do bang thuoc chua kiem thi ket qua khong dung duoc.

## 1. BON CHUOI DUOC KIEM — chot cung

Don vi resample: **khoi wall-clock**, `block_id = floor((ts - ts_min) / L)`, y `PREREG_CI §3`.
(Tick khong deu — pool da qua gate, ~5 tick/ngay tren 4595 tick / ~913 ngay — nen khoi phai theo
**thoi gian**, khong theo so tick.)

| ma | chuoi hieu `d_t` | nguon | so hien tai | vi sao kiem |
|---|---|---|---|---|
| **B1** | `repl_full9 - repl_core3` | `feataudit/tick_stats_s1cut.csv` | `d=+0.0015351`, `sd_boot=0.0047793` | verdict tuong duong cua S1CUT dua tren no |
| **B2** | `repl_full9 - repl_worse2` | cung tren | `d=-0.0269319`, `sd_boot=0.0096243` | **DOI CHUNG CONG SUAT** cua S1CUT. Neu no mat kha nang phat hien => **toan bo S1CUT VOID** |
| **B3** | rank-IC `S1 - G015` | `research/analysis/ci_group_b.py` | `d=+0.0973`, CI `[+0.0711,+0.1152]` | tru cot 1/2 cua "edge song o tang xep hang" |
| **B4** | gate MO `top8 - random8` | `research/analysis/gate_vs_rank3.py`, `random8` dong bang `df.sample(frac=1.0, random_state=0).groupby("ts").head(8)` | `d=+0.0182`, CI `[+0.0085,+0.0227]` | tru cot 2/2. **De vo nhat** (xem §4.2) |

B3/B4 phai tai lap **dung con so cu** truoc khi kiem phu; lech => bao va DUNG (khong bao L_valid).

## 2. BUOC 1 — DO do dai phu thuoc THAT cua chuoi nhom B (do, KHONG chon)

- ACF cua `d_t` theo **do tre wall-clock** (gom theo ngay), lag 1..30 ngay.
- Variance-ratio `VR(L)` cho `L in {1, 3, 7, 9, 14, 21, 30}` ngay, tren tong khoi wall-clock.
- Politis-White block length tu dong => `L_est`.
- Bao cao **so khoi** o tung `L` (o `L=3` ky vong ~248 khoi da biet; o `L=21` chi ~43).

### 2.1 DU DOAN GHI TRUOC (de khong the noi hau nghiem)

Nhan la cua so **72h** => ky vong phu thuoc **DUONG voi span ~3 ngay**. NBETS da do duoc quy luat
cua chinh cong cu nay: voi span phu thuoc dung 7 ngay, **moi `L <= 14` DUOI PHU** va chi PASS tu
`L >= 21`, tuc **khoi phai dai ~3 lan span** (`NBETS_RESULT:157-159`). Ap vao span 3 ngay =>
**du doan `L_valid` ~ 9 ngay, va khoi 72h (L=3) DUOI PHU.**
Neu ket qua ra `L_valid = 3` (72h da du) thi day la du doan SAI va phai ghi ro la sai.

## 3. BUOC 2 — CONG KIEM PHU. Chot toan bo truoc

Mo phong `NBETS §4`:
- **Generator `H4`**: hieu chuan theo ACF do duoc cua chinh chuoi `d_t` that, tiem mot muc trung
  binh **`mu` da biet**. Dai luong kiem = trung binh chuoi (khong quy nam — day la rank-IC,
  khong phai CAGR). **Dich (target) = `mu`.**
- **Doi chung bat buoc PASS (neu truot => cong cu vo hieu, DUNG job):**
  - `H0` iid => PASS o **moi** `L`.
  - `H3` phu thuoc DUONG span **dung 3 ngay** => phai **DUOI PHU voi `L < 9`** va PASS tu
    `L >= 9`. Day la phep tai hien quy luat "3 lan span" o dung thang do cua nhom B. Neu `H3`
    PASS ngay tai `L=3` thi cong cu **khong nhay** o thang do nay => khong duoc ket luan gi.
- `N_MC = 1000` lan lap, `N_BOOT = 1000` trong moi lan (tiet kiem CPU, y `PREREG_NBETS §4`).
  Seed `20260904`, `numpy.random.default_rng`.
- **Dai nhan chot truoc: do phu thuoc `[0.92, 0.97]`.** `< 0.92` = **DUOI PHU = khoi SAI**.
  `> 0.97` = **BAO THU** (CI rong hon can) — khong phai loi, phai ghi. Bao cao sai so MC.
- **`L_valid`** = `L` **nho nhat** thoa `L >= L_est` **VA** PASS kiem phu tren `H4`.
  Bao cao **toan bo luoi `L`** de thay ca duoi phu o dau LON do qua it khoi
  (NBETS `G2b` o `L=63` roi ve 0.918 voi 15 khoi).

## 4. BUOC 3 — BAO CAO LAI 4 SO O `L_valid`. Luat quyet dinh chot NGAY BAY GIO

Tieu chi duy nhat: **CI95 tai `L_valid` co con loai tru 0 hay khong** (ghep cap, percentile).
Bao cao them he so `f = sd_boot(L_valid) / sd_boot(72h)`.

### 4.1 Do nhay tinh TRUOC tu so hien tai (so hoc, chua chay gi)

| ma | `d` | `sd` hien tai | `d/sd` | con loai tru 0 khi `sd` x3? |
|---|---|---|---|---|
| B3 | +0.0973 | ~0.01125 | **8.65** | **CO** (8.65/3 = 2.88 > 1.96) |
| B4 | +0.0182 | ~0.00362 | **5.03** | **KHONG** (5.03/3 = 1.68 < 1.96) |
| B2 | -0.0269 | 0.0096243 | **2.80** | **KHONG** (2.80/3 = 0.93) |
| B1 | +0.0015 | 0.0047793 | 0.32 | da khong loai tru 0 |

### 4.2 Ba he qua duoc ghi TRUOC, khong duoc doc lai sau

1. **B3 (edge xep hang cua S1) du doan SONG** ngay ca khi `sd` gian 3 lan. Neu no CHET thi day la
   ket qua nang hon moi thu job nay du kien, phai bao ngay.
2. **B4 (edge gate) la thu de vo nhat.** Neu `L_valid >= 9` va `f >= ~1.7` thi
   `gate top8-random8 = +0.0182` **thoi loai tru 0** => mot trong hai tru cot cua
   `selector_edge_evidence` / `power_wall` phai bi **rut**, va C2 (gate) mat co so dinh luong.
3. **B2 la cai chet keo theo nhieu nhat.** Doi chung cong suat cua S1CUT chi con `d/sd = 2.80`;
   `f >= 1.43` la no thoi phan biet duoc => theo dung pre-reg cua S1CUT ("neu doi chung khong
   phan biet duoc => phep do vo hieu, DUNG"), **toan bo S1CUT tro thanh VOID** va C1 phai do lai
   voi khoi `L_valid`. Ghi truoc de khong ai bi ep doc theo huong de chiu hon.

## 5. Cai job nay KHONG lam

- Khong tao va khong pha edge. `L_valid > 3` **khong** nghia la S1 kem hon — no chi noi **CI phai
  rong hon**, tuc **duoc tuyen bo it hon**.
- Khong train lai, khong sinh bins, khong chay java, khong cham VALIDATION/HOLDOUT.
- Khong chung nhan phep **xap xi frozen-rank Pearson** cua `PREREG_G015CUT §4` (van de khac).
- Khong sua verdict nao cua nhom A (tang equity) — khoi 21 ngay da qua kiem phu roi.

## 6. Bay phai ghi

1. **Duoi phu o `L` LON vi qua it khoi** (NBETS `G2b`): `L=21` chi ~43 khoi, `L=30` ~30 khoi.
   Phai phan biet "duoi phu vi phu thuoc" voi "duoi phu vi it khoi".
2. **Tick khong deu.** 4595 tick / ~913 ngay ~ 5 tick/ngay, va so tick moi khoi **khong** bang
   nhau. Khoi theo wall-clock la dung, nhung `sd` se chiu anh huong cua khoi rong/vang.
3. **`H4` la generator, khong phai su that.** Do phu do duoc la do phu **tren generator da hieu
   chuan**, khong phai bao dam tren chuoi that. Do la ly do `H0`/`H3` phai PASS truoc.
4. **`f` khong nhat thiet la `sqrt(L_valid/3)`.** Phai DO, khong duoc suy ra.
5. Ket qua "PASS o `L=3`" cung la ket qua co gia tri (du doan §2.1 sai) — khong duoc coi la
   that bai cua job.

## 7. THU TU BAT BUOC

1. Commit file nay, ghi hash.
2. Tai lap B3/B4 dung so cu. Lech => DUNG.
3. Do `L_est`, ACF, VR (§2).
4. Doi chung `H0` + `H3` (§3). Truot => DUNG, bao "cong cu vo hieu o thang do nhom B".
5. Kiem phu `H4` tren luoi `L` => `L_valid`.
6. Bao cao lai B1-B4 tai `L_valid` theo §4, ke ca khi ket luan lam mat verdict cu.
7. `docs/COV_RESULT.md` + commit. KHONG push.
