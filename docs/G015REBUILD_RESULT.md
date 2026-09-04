# G015REBUILD_RESULT — G015 gio TAI LAP DUOC (Viec 1/3)

PREREG: `docs/PREREG_G015REBUILD.md` @ **0449f21** (commit TRUOC khi train). Ngay: 2026-09-04.
**CHI DEV.** Khong ghi de bins/ledger cu. Khong rebuild OI. Khong cham live/shadow.

**Tuyen bo duy nhat cua Viec 1 (khung NBETS/`power_wall`):** *he gio TAI LAP DUOC; he cu thi khong.*
`rho` cao hon (0.18991 vs moc-cu-khong-tai-lap 0.16752) **KHONG** duoc doc thanh "he tot hon" —
cai thien `rho` khong chuyen thanh cai thien equity do duoc. Moi so equity chi de kiem maxDD + sanity.

## 1. Tai lap 2 lan — BYTE-IDENTICAL (dat tieu chi CHINH)

| | ket qua |
|---|---|
| `sha256(xall.f32)` feature matrix | run1 == run2 (`7ab478f6…c50e9`) => build feature deterministic |
| `rho` (pool 15,442,092 dong) | run1 = run2 = **0.189910**, |d| = 0 |
| bins 10 fold | **byte-identical 10/10** (sha256 tung fold khop) |
| `spearman(run1,run2)` | **1.0** (max|Δp| = 0, `np.array_equal` = True) |
| xgboost | 3.2.0, CPU `hist`, `n_jobs=4`, seed 42 |

=> Vuot ca tieu chi du phong; dat tieu chi **byte-identical**. Bins chinh thuc = run1 ->
`/home/ubuntu/predwf_G015_v2/` (10 file, sha256 o `docs/G015_PROVENANCE.md` §1 va
`predwf_G015_v2/MANIFEST.sha256`). run2 da xoa.

Sanity gia tri: rho 0.18991 nam trong CI95 that cua moc cu `[0.1260, 0.2005]`. rho theo nam
2022 0.1950 / 2023 0.1724 / 2024 0.2119 (bucket 2021 = 3,612 dong, bo qua). Baseline chinh thuc
MOI = **G015_v2, rho 0.18991, byte-reproducible**.

## 2. Input ghim + sha256

Manifest digest `f14844f3…11cdc2` (= sha256 cua `g015rebuild_inputs_sha.json`, ghim ca 31 file).
Then chot: OI SACH `oi_percoin_full.bin` sha `e3887f63…b305ec` (4,227,723,300 B, **KHONG rebuild**);
pool `713460fc…99262`; symbol_map `3f817551…04eaa`; 14 Tool1 + 14 label (bang day du trong json).
Bang chi tiet: `docs/G015_PROVENANCE.md` §2.

## 3. Hieu chuan gate (Buoc C — python, khong java)

Train lai doi phan bo score => admit-rate `dyn_thr` tren `cand_dev3` doi. Do duoc:

| | he so c | SIM_MIN_MOMENTUM_15M | n_admit | admit-rate | chat luong hang admit (mean g1lite) |
|---|---|---|---|---|---|
| p_old (G015 deploy, diem nham) | 1.0 | 0.008 | 30,854 | 0.00200 | 0.10661 |
| G015_v2 (chua hieu chuan) | 1.0 | 0.008 | 95,762 | 0.00620 | 0.12249 |
| **G015_v2 (da hieu chuan)** | **1.75654** | **0.014052** | **30,943** | **0.00200** | 0.14638 |

Sai lech so admit sau hieu chuan = 89/30,854 = 0.29% (<= 5% dung sai da chot). => tham so gate moi:
**`SIM_MIN_MOMENTUM_15M = 0.014052`**. (Chat luong hang admit cao hon o cung diem van hanh, nhung
theo khung NBETS KHONG dien giai thanh "tot hon" — chi la so do dac ta.) File: `g015/gatecal.json`.

## 4. Dong bang C3 tren DEV (Buoc D) — KHONG DAT rang buoc maxDD

`profiles/c3.properties` = `c2b_min` doi **dung 2 thu**: `WFO_FUNDING_PRED_DIR=predwf_G015_v2` va
`SIM_MIN_MOMENTUM_15M=0.014052`. 1 run java DEV (env = C2b run cua `dev_c2.sh`, doi 2 bien do).
Build `wfo_ds_c3`: `md5_pred` **byte-identical** voi `wfo_ds_clean` (gate selector-doc-lap, xac nhan
dung); `md5_funding` doi (funding = G015_v2). Holdout 2026 tu dong seal. Sim hoan tat sach,
0 exception, 911 ngay, RAM 2.9GB, 210s. `wfo_ds_c3` da xoa; khong JVM zombie; dia 16G.

| chi tieu (qret.py, DEV 2022-01..2024-06) | **C2b** (S1 selector, tham chieu) | **C3** (G015_v2 selector) |
|---|---|---|
| equity 35,000 -> | 60,390 (+72.5%) | 45,287 (+29.4%) |
| **maxDD** | **-13.1%** | **-29.5%** |
| nam 2022 / 2023 / 2024 | +11.6 / +45.4 / +6.3 | **-19.2** / +54.9 / +3.4 |
| quy >= +5% | 6/10 | 5/10 |
| 2 quy lien tiep >= +5% | 4 | 4 |
| underwater dai nhat | 93 ngay | **367 ngay** |

**Rang buoc cung: maxDD >= -15.12%.** C3 = **-29.5% < -15.12%** => **C3 KHONG DONG BANG DUOC.**
- Sanity: PASS (khong sup, khong c, equity duong cuoi ky, hoan tat).
- maxDD: **FAIL** (sau -14.4pp so nguong; sau -16.4pp so C2b).

Dien giai (theo NBETS, khong tuyen bo hon/kem ve equity ngoai rang buoc maxDD): C3 doi **selector**
S1 -> G015_v2 (khong phai C2b tai lap — xem §7 cua PREREG). Selector G015 lam selector da tung do
la kem hon S1 o tang equity/maxDD (`AUDIT_APPLIED`: `C2_g015` maxDD -20.82 vs C2a); C3 xac nhan
lai bang so: G015-lam-selector sup -29.5% trong bear 2022, khong dat san maxDD. => **baseline
tai lap duoc (Buoc A-C) van dung; nhung KHONG dong bang duoc mot chien luoc C3 dung G015_v2 lam
selector.** Neu muon dong bang mot bien the co C2b maxDD, phai giu S1 lam selector (S1 cung can
tai lap-hoa rieng — Viec khac), khong phai G015.

## 5. Ket luan Viec 1

- **DAT:** G015 gio co baseline TAI LAP DUOC byte-identical (`predwf_G015_v2`, rho 0.18991),
  provenance ghim day du, sao luu Kaggle. Moc cu 0.1675 chinh thuc bo (khong tai lap duoc).
- **KHONG DAT:** C3 (G015_v2 lam selector) khong qua rang buoc maxDD -15.12% => khong dong bang
  duoc lam chien luoc. Day la ket qua that, khong phai loi pipeline: no tai xac nhan S1 > G015 o
  tang selector, dung nhu ly do C2b chon S1.
- Khong co tuyen bo equity nao vuot ra ngoai kiem maxDD (khung NBETS).

## 6. Sao luu + tai lap

| thu | vi tri |
|---|---|
| bins chinh thuc | `/home/ubuntu/predwf_G015_v2/` (10 x predict_wf_*.bin + MANIFEST.sha256) |
| sao luu Kaggle PRIVATE | `chuyendinh/predwf-g015-v2-bins` (ready) |
| provenance | `docs/G015_PROVENANCE.md`, `research/analysis/g015rebuild_inputs_sha.json` |
| script rebuild (deterministic) | `research/analysis/g015_rebuild.py` |
| gate calibration | `research/analysis/g015_gatecal.py`, `g015/gatecal.json` |
| profile dong bang (khong dat maxDD) | `profiles/c3.properties` |
| C3 run | `research/analysis/g015_c3run.sh`, log `java/devrun/C3/logs/sim.out` |

## 7. GIA DINH CUA DIEU PHOI BI SAI / CAN DINH CHINH

1. **"G015 cap score cho GATE cua C2b".** C2b THAT (`c2b_min.properties`, `dev_c2.sh`) dung
   `WFO_FUNDING_PRED_DIR=predwf_map_s1a2` = **S1**, khong phai G015. Gate `AIRejectFilter` dung score
   cua selector dang nap = S1. "G015 cap score cho gate" chi ton tai o tang PHAN TICH ledger. Do do
   C3 (thay selector = G015_v2) la mot cau hinh KHAC C2b, va no khong qua maxDD.
2. **"admit-rate top-8 ~0.51% DEV".** Do o tang java (S1 selector + top-K), khong tai lap duoc bang
   python tren `cand_dev3`. Diem van hanh do duoc bang python la p_old 0.200% (dyn_thr). Da hieu
   chuan ve moc do; admit-rate/so lenh THAT o java bao cao nguyen trang (C3 §4).
3. **"train lai la vệ sinh + baseline moi tot hon o rho => nen dung".** Vệ sinh: DUNG. "Tot hon" o
   equity: KHONG do duoc (NBETS); va khi dem G015_v2 ra lam selector (C3) thi maxDD tệ hơn han,
   truot san. => khong nen coi rho 0.18991 la co so de deploy G015 lam selector.
4. **Khung phu:** de bai ngu y co the "dong bang C3" duoc. Thuc te C3 khong qua rang buoc maxDD
   => san pham dong bang duy nhat cua Viec 1 la **baseline bins + provenance**, KHONG phai mot
   profile chien luoc moi.
