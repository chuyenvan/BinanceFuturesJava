# COV_RESULT — kiem phu cho nhom TICK / XEP HANG

Tien dang ky: `docs/prereg/PREREG_COV.md` @ **b6de3af** (commit TRUOC khi chay). Chay 2026-09-04
18:33-18:38, Oracle CPU. Script: `research/analysis/cov_run.py` (+ `cov_run2.py` addendum).
Ket qua tho: `/home/ubuntu/cov/{COV.out,COV2.out,cov_meta.json,cov2_meta.json}`.
CHI DEV. Khong train, khong java, khong cham VALIDATION.

## 0. CONG TAI LAP — PASS

| | tai lap | ban ghi cu | lech |
|---|---|---|---|
| B7 rank-IC `S1 - G015` | **+0.09727** | +0.0973 | -0.00003 |
| B8 gate MO `top8 - random8` | **+0.01818** | +0.0182 | -0.00002 |
| B1 `core3 - full9` | -(-0.00154) = **+0.00154** | +0.0015351 (`s1cut_equiv.csv`) | ~0 |

⚠️ `sd_boot` tai lap lech **3-4%** so ban cu (B1 0.00462 vs 0.0047793; B2 0.00926 vs 0.0096243).
Diem uoc luong trung 5 chu so nhung `sd` thi khong — kha nang do ban cu dung trung binh
khong-trong-so theo tick con job nay dung **ty so tong** (y `ci_group_b.py`). Chenh 3-4% khong
doi ket luan nao duoi day, nhung phai ghi.

## 1. HAI HO CHUOI, KHONG PHAI MOT — day la phat hien dau tien

Nhom B khong dong nhat. Do duoc:

| ho | chuoi | n_tick | n_day | `rho1` | VR(L) | phu thuoc |
|---|---|---|---|---|---|---|
| **DAY** | B1 `full9-core3`, B2 `full9-worse2` (pool S1CUT, moi tick >= 10 dong) | 4,595 | **496** | +0.225 / +0.275 | 1.31 -> **2.26** (L=21), **khong bao hoa** | **DUONG, KHONG ngan han** |
| **THUA** | B7 `S1-G015`, B8 `top8-rnd8` (chi tick **gate MO**) | 325 / 465 | **48 / 67** | **-0.209** / -0.033 | tut ve **0.10** / 0.14 | **AM / khong co** |

=> Gia thiet cua `power_wall` ("nhan cua so 72h la phu thuoc DUONG") **dung cho ho DAY va SAI cho
ho THUA**. Hai tru cot B7/B8 nam o ho THUA. Vi vay chung phai duoc kiem **rieng** — `cov_run.py`
hieu chuan `H4` tren B2 nen KHONG mo ta B7/B8; do la ly do co `cov_run2.py`.

Con so dang chu y: chuoi gate MO chi trai tren **48 ngay** (B7) va **67 ngay** (B8) trong ~913 ngay
DEV. Day chinh la `ci_reality` "gate MO: chi 39-52 khoi" hien ra o dang **so khoi CO du lieu**:
39 (B7 @72h) / 52 (B8 @72h).

## 2. DOI CHUNG — cong cu HOP LE va NHAY (dieu kien de doc muc 3)

`N_MC=1000`, `N_BOOT=1000`, `mu=0.02`, dai nhan **[0.92, 0.97]**, sai so MC **0.0069**.

- **`H0` iid**: ho DAY PASS `L=1..14` (0.927-0.939), truot `L=21/30` (0.912/0.898) — **duoi phu vi
  QUA IT KHOI**, dung bay `NBETS G2b` da canh bao. Ho THUA: B8 PASS (0.920-0.934); **B7 chom truot
  o MOI `L`** (0.901-0.919).
- **`H3` span DUNG 3 ngay**: ho DAY **duoi phu `L<=5`** (0.782/0.898/0.900) va **PASS tu `L=7`**
  (0.927-0.928) => **tai hien dung quy luat "khoi ~3 lan span"** cua `NBETS_RESULT:157-159` o thang
  do nhom B. **Cong cu duoc chung minh NHAY.** Ho THUA: B7 PASS het (chuoi qua nho de span 3 ngay
  kip an), B8 **truot het** (0.872-0.906).

=> Doi chung dat yeu cau §3 cua pre-reg. Doc tiep duoc.

## 3. KET QUA `H4` (cau truc THAT) — do phu theo `L`

| `L` (ngay) | ho DAY (hc tren B2) | B7 | B8 |
|---|---|---|---|
| 1 | 0.848 | **0.945** | 0.914 |
| **3 (=72h)** | **0.896** | **0.941** | **0.914** |
| 5 | 0.909 | 0.937 | 0.905 |
| 7 | 0.901 | 0.931 | 0.897 |
| 9 | 0.909 | 0.930 | 0.895 |
| 14 | 0.908 | 0.933 | 0.892 |
| 21 | 0.903 | 0.927 | 0.894 |
| 30 | 0.910 | — | — |

- **Ho DAY: DUOI PHU o MOI `L` => KHONG CO `L_valid`.** Do phu bao hoa quanh 0.90-0.91 va
  **khong cai thien khi keo dai khoi**, khop voi VR **tang khong bao hoa** (1.31 -> 2.26): phu thuoc
  o day **khong phai ngan han**, nen keo dai khoi khong chua duoc — ma keo dai them thi het khoi
  (`H0` da truot tu `L=21`). **Bi ep tu hai phia.**
- **B7: PASS o MOI `L`, ke ca `L=3`.** => **khoi 72h HOP LE cho B7.**
- **B8: 0.914 o `L=3`**, tuc **thieu 0.006 so nguong 0.92** trong khi sai so MC la **0.0069**
  => **KHONG phan biet duoc voi PASS**. Ghi la **BIEN**, khong phai truot dut khoat.

### 3.1 Tu kiem noi bo — mot canh bao ve do phan giai
Voi B7, hieu chuan cho `var_latent = 0`, nen `H4` va `H0` **la cung mot generator ve toan hoc**
(chi khac vi tri trong luong rng). Chung ra **0.919 vs 0.945** o `L=1` — lech 2.6pp, khoang
**2.3 sigma**. => Sai so MC thuc te o `N_MC=1000` **rong hon** `0.0069` danh nghia. Vi vay
"B7 PASS" phai doc la **khong phan biet duoc voi hop le**, chu khong phai chung nhan sach.
Muon sach thi phai `N_MC` lon hon + dung **common random numbers** giua cac generator.

## 4. HE SO HIEU CHINH VA 4 CON SO — bao cao theo §4 cua pre-reg

`f = 1.96 / Phi^-1((1+do_phu)/2)` suy tu do phu tai `L=3` (dai luong **dan xuat**, khong phai
tieu chi da chot):

| ma | `d` | `sd(72h)` | `d/sd` | do phu | `f` | `d/sd` sau hieu chinh | con loai tru 0? |
|---|---|---|---|---|---|---|---|
| **B7** | +0.09727 | 0.01104 | 8.81 | 0.941 | **1.00** | **8.81** | **CO** |
| **B8** | +0.01818 | 0.00357 | 5.09 | 0.914 | **1.14** | **4.46** | **CO** |
| **B2** (doi chung cong suat S1CUT) | +0.02693 | 0.00926 | 2.91 | 0.896 | **1.21** | **2.41** | **CO** |
| B1 (`core3` vs `full9`) | -0.00154 | 0.00462 | 0.33 | 0.896 | 1.21 | 0.28 | khong (nhu cu) |

## 5. BA DU DOAN GHI TRUOC — CA BA SAI. Ghi ro.

Pre-reg §2.1 va §4.2 da chot truoc, va ket qua **bac ca ba**:

1. **"`L_valid` ~ 9 ngay, khoi 72h duoi phu"** — SAI o ca hai huong. Ho THUA: **72h da hop le**.
   Ho DAY: **khong co `L_valid` NAO** (te hon du doan, khong phai nhe hon).
2. **"B4/B8 (edge gate) la thu de vo nhat, se thoi loai tru 0"** — **SAI**. `f` that chi 1.14
   (khong phai ~3), `d/sd` con **4.46**. **Tru cot 2/2 SONG.**
3. **"B2 chet keo theo toan bo S1CUT thanh VOID"** — **SAI**. `f=1.21` cho `d/sd = 2.41 > 1.96`
   => **doi chung cong suat VAN phan biet duoc** => **S1CUT KHONG bi VOID.**

Ly do du doan sai, ghi de lan sau khong lap: toi suy `f ~ 3` tu quy luat "khoi phai ~3 lan span"
cua NBETS, nhung **do dai khoi va do rong CI la hai chuyen khac nhau**. Do phu 0.90 chi ung voi
`f = 1.21`; muon `f = 3` thi do phu phai sut xuong ~0.50. Quy luat "3 lan span" noi ve **`L` can
thiet**, khong noi ve **he so gian `sd`**.

## 6. HE QUA — cai gi doi, cai gi khong

1. **Hai tru cot cua `selector_edge_evidence` / `power_wall` GIU NGUYEN.** B7 `+0.0973`
   CI `[+0.0711,+0.1152]` va B8 `+0.0182` deu con loai tru 0 sau hieu chinh. **Khong phai rut cau
   nao.** Quyet dinh "chuyen han ve tang xep hang" van co co so.
2. **`S1CUT` KHONG bi VOID** — doi chung cong suat song. Nhung `sd_boot` cua ho DAY **bi hieu
   thieu ~21%**, nen moi `sd`/`CI`/`delta_M` cua `S1CUT_*` phai nhan `f = 1.21` khi bao cao.
3. **Verdict "khong bo cat nao dat tuong duong" KHONG DOI** — va day la diem then chot: tieu chi
   cua `PREREG_S1CUT` la `chan_duoi_CI > -1.7941*sd_boot`, tuc **thuan ty le voi `sd`**, nen nhan
   `sd` voi bat ky `f` nao cung **khong doi ket luan**. Loi thiet ke bien (ghi o
   `s1cut_status.md`) van la van de duy nhat cua S1CUT, va kiem phu **khong** chua duoc no.
4. **Rang buoc that cua nhom B khong phai do dai khoi ma la CO MAU.** Chuoi gate MO chi co
   **48/67 ngay** va **39/52 khoi co du lieu**; `H0` iid cua B7 chom truot o moi `L`. Tuc ke ca khi
   khong co phu thuoc nao, bootstrap tren tap nay **cung khong dat 95%**. Khong the mua bang cach
   doi do dai khoi — chi bang **them tick gate MO** (tuc them du lieu / noi gate).
5. **Cho ho DAY (pool S1CUT), block-bootstrap 72h la thuoc SAI ve nguyen tac** (khong `L_valid`).
   Moi phep so tuong lai o pool nay nen bao cao kem `f` do duoc, hoac doi sang phuong phap khac
   (vd bootstrap ngoai vi/subsampling co hieu chinh), va **khong** duoc trinh bay CI 72h nhu la
   chuan.

## 7. Cai job nay KHONG lam

- Khong tao/pha edge nao. Khong train, khong java, khong VALIDATION.
- Khong chung nhan xap xi frozen-rank Pearson (`PREREG_G015CUT §4`) — van de khac.
- Khong sua verdict nhom A (equity, khoi 21 ngay da qua kiem phu o NBETS).
- **Chua** sua cac con so `sd` da cong bo trong `S1CUT`/`selector_edge_evidence` — chi neu he so
  `f` de nhan. Viec sua tai lieu cu de lan sau, tranh sua-nhieu-cho-mot-luc.
