# PREREG — BIG_DOWN THRESHOLD FRAGILITY (tach hang so + quet do nhay, DESCRIPTIVE ONLY)

> **Pre-reg (chot TRUOC khi chay sim).** Branch `module`. KHONG push. DEV 2021-07..2025-12
> (`wfo_ds_x1_2021`, `SIM_END_DATE=20251231`, config `configs/sim_dev_file_2021.properties`).
> Baseline/parity = profile `x1_gs_t170.properties`, artifact `X1_GS_T170_2021/storage/printDone.csv`
> md5 `efb793e2468ca3a7318da0f0ad23d4fc`.

## 0. Muc tieu va BAN CHAT (user chot 2026-09-17)

`docs/AUDIT_BIGDOWN_DEEP.md` (commit `75d1461`) ket luan: nguong `MS_DOWN_BIG_AVG = -0.03157` **KHONG
co giay to ghi cach chon**, co dau vet HPO-tren-DEV-roi-revert (commit `cb50841` day len `-0.05514`
roi `1fbe620` "revert ve cu") => nghi van overfit.

User chot huong **(a) do do nhay/mong manh + (b) don suc vao forward**.

**BAN CHAT CUA PHAN (a): DAY LA DO DO NHAY (fragility), KHONG PHAI TIM WINNER.**

- **KHONG chon nguong nao. KHONG de xuat nguong. KHONG dung ket qua de chon.**
- Muc dich DUY NHAT = do xem **"edge phu thuoc nguong toi dau"**: doi nguong BIG_DOWN mot chut thi
  PnL/rate chat luong/so leg doi bao nhieu, va lieu `-0.03157` co phai la **diem dac biet** khong.
- Ket luan duy nhat duoc phep (muc 6): "edge mong manh hay khong mong manh" + "co bang chung rang
  nguong hien tai la diem dac biet khong" (tra loi BANG SO).

## 1. Su that code (da xac minh, khong doi)

- `MarketBigChangeDetector.getMarketStatus1M` (dong ~179): `rateDownAvg < Configs.MS_DOWN_BIG_AVG`
  => `BIG_DOWN`. Nhanh duy nhat con song.
- `MarketBigChangeDetector.isDcaAlt` (dong ~189-190): **dung CHUNG** `Configs.MS_DOWN_BIG_AVG` cho
  duong DCA: `rateDown15MAvg < MS_DOWN_BIG_AVG || rateDownAvg < MS_DOWN_BIG_AVG / 3`.
- `Configs.MS_DOWN_BIG_AVG = -0.03157f` (dong 392); override qua `SIM_MS_DOWN_BIG_AVG` (dong 657).
- `MS_DOWN_BIG_AVG` la **gene HPO** o 3 noi (reflection `Configs.class.getField("MS_DOWN_BIG_AVG")`):
  `WFORunner:67` (range `-0.055..-0.020`), `StrategyWfoTask:74` (`-0.060..-0.025`),
  `SensitivityTool:69` (`-0.060..-0.020`). => field phai GIU NGUYEN ten de reflection khong chet im lang.

## 2. Co che (tach hang so)

### 2.1 Tach `MS_DOWN_BIG_AVG` thanh 2 duong rieng

- **GIU NGUYEN field `MS_DOWN_BIG_AVG`** cho duong **BIG_DOWN** (`getMarketStatus1M`) — de 3 noi HPO
  reflection o tren khong bi chet im lang.
- **Them field MOI `MS_DOWN_BIG_AVG_DCA`** (default doc tu config `SIM_MS_DOWN_BIG_AVG_DCA`, mac dinh =
  gia tri cu `-0.03157f`).
- **Doi `isDcaAlt` sang dung field moi**: `rateDown15MAvg < Configs.MS_DOWN_BIG_AVG_DCA || rateDownAvg
  < Configs.MS_DOWN_BIG_AVG_DCA / 3`.
- Override nguong BIG_DOWN giu nguyen key **`SIM_MS_DOWN_BIG_AVG`** (da co san) — nay chi con anh huong
  duong BIG_DOWN.

### 2.2 Thay doi CO Y THUC (chi xay ra khi HPO chay; config default thi parity byte-identical)

- Truoc day: HPO gene `MS_DOWN_BIG_AVG` dieu khien **CA BIG_DOWN lan DCA** (qua `isDcaAlt`).
- Sau khi tach: gene `MS_DOWN_BIG_AVG` **chi con anh huong BIG_DOWN**; duong DCA doc tu
  `MS_DOWN_BIG_AVG_DCA` (KHONG nam trong genome HPO nao) => giu gia tri cu khi HPO chay.
- Day la thay doi CO Y THUC cua kha nang search HPO (giam 1 chi do khong gian, ngat coupling BIG_DOWN
  vs DCA), **CHI co hieu luc khi HPO chay**. Voi cau hinh default (`SIM_MS_DOWN_BIG_AVG` va
  `SIM_MS_DOWN_BIG_AVG_DCA` deu khong khai bao => ca 2 = `-0.03157f`) thi `isDcaAlt` ra dung nhu cu
  => `printDone.csv` **byte-identical** `efb793e2...`.

### 2.3 Khong cham gi khac

KHONG sua feature extractor, KHONG sua cac ham khac cua `MarketBigChangeDetector`, KHONG sua gene HPO
khac, KHONG sua sizing/exit/selector. Chi: 1 field moi + 1 dong doc config + doi `isDcaAlt`.

## 3. Luoi quet (4 gia tri MOI + baseline; chot truoc, KHONG them sau khi thay so)

| nhan | `SIM_MS_DOWN_BIG_AVG` | ghi chu |
|---|---|---|
| `baseline` | (khong khai bao) | `-0.03157` (default `Configs`, lay tu `X1_GS_T170_2021`) |
| `thr_m025` | `-0.025` | no rong hon (nong hon) — nhieu trigger hon |
| `thr_m028` | `-0.028` | no rong nhe |
| `thr_m036` | `-0.036` | chat hon — it trigger hon |
| `thr_m045` | `-0.045` | chat hon nhieu |

- Ly do chon: **doi xung quanh gia tri dang dung** `-0.03157` (2 ben nong/chat, moi ben 2 muc).
- **KHONG them gia tri nao sau khi thay so.** 5 diem (4 moi + baseline) la QUOTA CO DINH.
- Moi diem = clone `x1_gs_t170.properties` + them dung 1 key `SIM_MS_DOWN_BIG_AVG=<giatri>`.
  `SIM_MS_DOWN_BIG_AVG_DCA` **khong khai bao** o moi diem => duong DCA giu nguyen `-0.03157f`.

## 4. Do gi (moi diem)

### 4.1 Chi so chinh

- `n leg` (tong), `n leg BIG_DOWN`, `PnL BIG_DOWN` (USD).
- **5 rate chat luong TOAN BO leg** (khong chi BIG_DOWN): `win%`, `TSloss%`, `mP|SM`, `mP|SL`, `meanP`.
- CI bootstrap cho 5 rate: **block-72h x1.21, 2000 rep, seed 20260905** (`c3_rates.CI_INFLATE`,
  `BLOCK_H`, `NREP`, `SEED`). Voi moi diem, bao cao CI cua TUNG rate (khong phai diff vs baseline);
  ve thanh **duong cong** theo nguong.
- Rang buoc cung (bar, giong `dca_agg_percoin_score.py` muc CHAN): `maxDD/yr <= 30%`, `UW <= 200 ngay`,
  `quy xau nhat >= -15%`, **khong nam am**, **tap trung 1 coin <= 15% equity**.

### 4.2 Bao cao dang DUONG CONG

- Bang 5 diem x (n leg, n leg BIG_DOWN, PnL BIG_DOWN, 5 rate + CI, maxDD/yr, UW, qmin, conc 1 coin).
- Nhan xet **do nhay** (do doc cua duong cong), **KHONG bao cao "diem tot nhat"**. Khong co cot
  "winner", khong xep hang, khong chon.

## 5. Cang thang voi `docs/B4_RESULT.md` dong 179-180 + ly do ngoai le

`docs/B4_RESULT.md` (dong 179-180) cam: *"KHONG mo them bien the tren cung khong gian (noi cua so,
doi phan vi, doi tan so cap nhat...). Da dung dung 3/3 quota. Them bien the = chon tren nhieu = leak L2."*

**Day la ngoai le CO LY DO, ghi ro truoc khi chay:**

1. **Day la descriptive/fragility, KHONG dung de chon.** Quet 4 nguong khong tao "bien the duoc chon";
   no chi ve hinh dang phu thuoc cua edge vao nguong. Khong co buoc "lay diem nao do".
2. **Khong co ket luan "thang".** Ket luan duy nhat duoc phep la "mong manh / khong mong manh" +
   "nguong hien tai co dac biet khong" (muc 6). Khong so sanh "hon/thua T170" lam quyet dinh.
3. **Bao cao duong cong DAY DU, khong bao cao "diem tot nhat".** Tat ca 5 diem deu duoc bao cao nhu
   nhau; khong co diem nao duoc neu bat lam winner.

Neu ai doc thay quet nay "mo them bien the" => nhan manh: **khong gian o day la THAM SO NGUONG (xem no
doi sao), khong phai tim config toi uu moi.** Khong chon, khong de xuat, khong dat cuoc.

## 6. Ket luan duy nhat duoc phep (chot truoc)

1. **Edge mong manh hay khong:** do doc cua duong cong (PnL BIG_DOWN + meanP + win% theo nguong) va do
   rong CI. Neu doi nguong ~10-40% (tuong doi) ma PnL/rate dao lon ngoai CI => **mong manh**. Neu phang
   trong CI => **khong mong manh** (it nhat trong dai quet).
2. **Nguong hien tai co dac biet khong:** so sanh `-0.03157` voi 2 diem ke `-0.028`/`-0.036` (va 2 diem
   xa). Neu PnL BIG_DOWN / meanP tai `-0.03157` nam NGOAI xu huong don dieu ro rang cua 4 diem quet
   (dinh nho / day cuc bo) => "co dau hieu diem dac biet" (tra loi bang so). Nguoc lai => "khong co bang
   chung no dac biet".

**KHONG duoc:** ket luan "nen chuyen nguong sang X", "nguong Y tot hon", "chon Z".

## 7. Trinh tu

1. Pre-reg (file nay) commit truoc khi chay sim.
2. Code: Configs them field `MS_DOWN_BIG_AVG_DCA` + doc `SIM_MS_DOWN_BIG_AVG_DCA`; doi `isDcaAlt`.
3. Build jar + **CONG PARITY**: khong override => `printDone.csv` byte-identical `efb793e2...`; khac =>
   DUNG, bao parent.
4. Chay baseline (dung lai parity) + 4 diem quet, TUAN TU, 1 slot JVM, `setsid`/background + poll
   (de bi kill 30 phut), artifact `/home/ubuntu/java/devrun/`.
5. Cham theo muc 4 (bang duong cong).
6. Viet `docs/RESULT_BD_THRESHOLD_FRAGILITY.md`.
7. Commit (KHONG push).
