# RESULT — BIG_DOWN THRESHOLD FRAGILITY (tach hang so + quet do nhay, DESCRIPTIVE ONLY)

> **Ket qua (da chay sim + cham).** Branch `module`. KHONG push. DEV 2021-07..2025-12
> (`wfo_ds_x1_2021`, `SIM_END_DATE=20251231`). Pre-reg: `docs/PREREG_BD_THRESHOLD_FRAGILITY.md`
> (commit `61cf533`). Code: commit `720afe0`. **KHONG chon nguong, KHONG de xuat nguong.**

## 0. Tom tat mot dong

**Edge BIG_DOWN mong manh theo nguong.** PnL BIG_DOWN dao **2x** (8,323 -> 16,254 USD) trong 4
diem quet, va **nguong hien tai `-0.03157` la diem PnL CAO NHAT** (local max) — do doc giam don dieu
o ca hai phia. **Day la bang chung (bang so) rang nguong hien tai la "diem dac biet", nhat quan voi
nghi van overfit cua `AUDIT_BIGDOWN_DEEP`.** Nhung o tang "toan bo leg" cac rate chat luong lai
**ON DINH** (nam trong CI) — fragility chi nam o dong gop BIG_DOWN (so leg x PnL/leg), khong nam o
chat luong tung leg noi chung.

## 1. Parity

| run | md5 printDone.csv | ghi chu |
|---|---|---|
| BD_THR_PARITY (khong override) | `efb793e2468ca3a7318da0f0ad23d4fc` | byte-identical ✓ (n=1089) |

Tach hang so (`MS_DOWN_BIG_AVG_DCA` moi + doi `isDcaAlt`) khong doi hanh vi khi default => parity
byte-identical. Override nguong BIG_DOWN qua key `SIM_MS_DOWN_BIG_AVG` (da co san); duong DCA giu
nguyen `-0.03157f` (key `SIM_MS_DOWN_BIG_AVG_DCA` khong khai bao o moi diem).

## 2. Bang duong cong do nhay (5 diem)

### 2.1 So leg + PnL BIG_DOWN

| nguong `SIM_MS_DOWN_BIG_AVG` | n leg | n BIG_DOWN | PnL BIG_DOWN (USD) | PnL / leg BD |
|---|---|---|---|---|
| `-0.025` (no rong) | 1169 | 378 | 11,413 | 30.2 |
| `-0.028` | 1130 | 310 | 15,188 | 49.0 |
| **`-0.03157` (baseline)** | **1089** | **248** | **16,254** | **65.5** |
| `-0.036` | 1062 | 204 | 12,525 | 61.4 |
| `-0.045` (chat) | 1015 | 128 | 8,323 | 65.0 |

Nhan xet (doc mo ta, khong chon):

- **`-0.03157` la local max cua PnL BIG_DOWN.** Tat ca 4 diem quet deu THAP hon baseline: noi rong
  (-0.028/-0.025) thi NHIEU leg hon nhung PnL GIAI (15,188 / 11,413); chat (-0.036/-0.045) thi it leg
  hon va PnL giam (12,525 / 8,323).
- **PnL/leg BD giu nguyen (~61-65.5) khi chat hoac giu nguong, nhung SAP khi noi rong:** 65.5
  (baseline) -> 49.0 (-0.028) -> 30.2 (-0.025). Noi nguong = nap them cac trigger "dep hon" (chat
  luong thap), pha loang edge.
- => `-0.03157` nam dung **knee** cua duong PnL/leg: la nguong noi nhat van giu PnL/leg ~65.5.

### 2.2 5 rate chat luong TOAN BO leg (profit/leg) + CI bootstrap (block-72h x1.21, 2000 rep, seed 20260905)

| nguong | win% [CI] | TSloss% [CI] | mP\|SM [CI] | mP\|SL [CI] | meanP [CI] |
|---|---|---|---|---|---|
| `-0.025` | 87.51 [84.77, 90.69] | 10.69 [7.91, 14.01] | 7.57 [6.33, 8.86] | -17.02 [-19.89, -14.33] | 4.94 [3.43, 6.34] |
| `-0.028` | 87.79 [84.96, 90.86] | 10.27 [7.74, 13.21] | 7.55 [6.37, 8.76] | -16.96 [-20.34, -13.94] | 5.04 [3.59, 6.43] |
| **`-0.03157`** | **88.25 [85.43, 91.31]** | **9.73 [6.95, 12.89]** | **7.64 [6.43, 8.91]** | **-16.99 [-20.15, -13.84]** | **5.24 [3.73, 6.67]** |
| `-0.036` | 88.04 [85.18, 91.29] | 9.70 [6.91, 12.83] | 7.66 [6.37, 9.03] | -17.33 [-20.74, -14.31] | 5.24 [3.65, 6.73] |
| `-0.045` | 88.08 [85.19, 91.26] | 9.66 [6.82, 12.87] | 7.69 [6.33, 9.10] | -16.89 [-20.16, -13.72] | 5.31 [3.63, 6.93] |

Nhan xet: **ca 5 rate cua ca 5 diem deu OVERLAP trong CI.** O tang "toan bo leg" (khong tach BIG_DOWN),
chat luong tung leg **KHONG doi co y nghia** theo nguong. Fragility chi hien o muc 2.1 (PnL BIG_DOWN),
khong hien o chat luong leg noi chung.

### 2.3 Rang buoc cung (bar)

| nguong | maxDD/yr% | UW (ngay) | quy xau nhat% | nam am | tap trung 1 coin% | verdict |
|---|---|---|---|---|---|---|
| `-0.025` | -11.79 | 92 | -1.8 | khong | 9.49 | PASS |
| `-0.028` | -11.34 | 88 | -0.9 | khong | 9.79 | PASS |
| **`-0.03157`** | **-11.84** | **92** | **-0.9** | **khong** | **9.77** | **PASS** |
| `-0.036` | -11.84 | 92 | -1.4 | khong | 9.77 | PASS |
| `-0.045` | -12.08 | 88 | 0.0 | khong | 9.77 | PASS |

Nhan xet: ca 5 diem deu PASS, va cac rang buoc **gan nhu bat bien** (maxDD -11.3..-12.1, UW 88-92,
tap trung 9.5-9.8). Nguong BIG_DOWN khong phai nut kiem soat rui ro.

## 3. Ket luan (duy nhat duoc phep, theo pre-reg muc 6)

1. **Edge mong manh hay khong?** — **MONG MANH.** PnL BIG_DOWN dao **~2x** (8,323 -> 16,254 USD)
   trong dai quet doi xung quanh nguong hien tai. Do doc o phia NOI RONG rat dung dung: PnL/leg BD
   sap tu 65.5 -> 30.2 khi noi nguong 10-25% (tuong doi).
2. **Nguong hien tai co dac biet khong?** — **CO, bang so.** `-0.03157` la diem PnL BIG_DOWN CAO
   NHAT trong 5 diem, voi do doc giam DON DIEU o ca hai phia (khong phai noise ngau nhien xung quanh
   mot mat phang). No nam dung knee cua duong PnL/leg (nguong noi nhat van giu chat luong ~65.5/leg).
   Day **nhat quan voi** (khong phai chung minh) gia thuyet overfit cua `AUDIT_BIGDOWN_DEEP`: mot
   nguong duoc chon bang cach nhin DEV se co xu huong nam o dinh PnL nhu vay.

**KHONG ket luan "nen chuyen nguong sang X", KHONG "nguong Y tot hon", KHONG chon.** Muc dich duy
nhat da dat: do duoc edge phu thuoc nguong toi dau, va tra loi cau "nguong hien tai co dac biet
khong" bang so.

## 4. Gioi han (ghi ro, khong vo tron)

- **5 diem quet (4 moi + baseline), khong them sau khi thay so.** Day la descriptive, khong phai
  tim kiem toi uu. Khong co CI cua PnL BIG_DOWN (PnL/leg BD la so mot-lan-quan-sat, khong co
  bootstrap CI) — do doc cua PnL/leg o muc 2.1 la mo ta, chua kiem y nghia thong ke.
- **CI chi cho 5 rate "toan bo leg"** (muc 2.2); PnL BIG_DOWN va n BIG_DOWN khong co CI o dot nay.
- **Mau su kien BIG_DOWN van mong** (128-378 leg trong 4.5 nam; baseline 248 leg/56 ngay) — moi
  thong ke o muc BIG_DOWN deu mong, nhat quan `AUDIT_BIGDOWN_DEEP` muc 5.

## 5. Trang thai code + artifact

| thu | gia tri |
|---|---|
| commit pre-reg | `61cf533` |
| commit code (tach hang so) | `720afe0` |
| jar | `target/binance-java-sdk-1.2.4.jar` (rebuild) |
| parity run | `/home/ubuntu/java/devrun/BD_THR_PARITY` (md5 `efb793e2...`) |
| 4 diem quet | `/home/ubuntu/java/devrun/thr_m025|m028|m036|m045` |
| score script | `research/analysis/bd_threshold_fragility_score.py` |

md5 tung diem quet: `thr_m025=df9f6f2f...` (1169 leg), `thr_m028=60c7bcaf...` (1130),
`thr_m036=cbfb063f...` (1062), `thr_m045=94132a72...` (1015).
