# DIAG_RVOL15M — vi sao `rvol15m` gain 34% nhung IC ~0

**Ngay:** 2026-09-24 · **Nhanh:** `module` · **Trang thai:** PRE-REG (chot TRUOC khi do)
**Pham vi:** DEV only — 3 quy `20230101_to_20230401`, `20231001_to_20240101`, `20240401_to_20240701`.
**KHONG doc 2026. KHONG train. KHONG sim. Thuan Python offline.** Khong push.

---

## 0. So da co (khong dien giai lai)

`docs/analysis/EVAL_SELECTOR_FEATURES.md` (commit `025767f`), 18 model fold
`/home/ubuntu/claudedata/predwf_G015/model_f{0..17}_4h.json`:

| # | feature | gain share | rank-IC vs `retEnd_4h` | decile edge |
|---|---|---|---|---|
| 36 | `rvol15m` | **34,09 ± 2,98%** | **−0,0424** [−0,0491, −0,0359] | +1,51bp [−3,21, +6,46] |
| 28 | `distFromHigh24H` | 7,06 ± ? | −0,0161 [−0,0223, −0,0082] | −1,08bp [−5,58, +3,39] |

Cau hoi chu du an: *"rvol15m sao cai nay cao the ma toi nghi no khong nhieu gia tri"*.

---

## 1. TIEN KIEM PROVENANCE NHAN (lam TRUOC khi do — sua gia dinh cua de bai)

De bai ghi: **"Nhan train = `y = (maxFav_4h >= 6%)`"**. Kiem tra bang artifact TRUOC khi do:

- Log kernel goc `/home/ubuntu/claudedata/predwf_G015/selector-15mtr-pred15-net015-gpu.log`
  (2026-08-14, dir chua chinh 18 model dang do):
  - dong 1: `TRACKC train15->pred15 | SEL_GRID=15 PRED_GRID=15 purge=288 FIRST_CUTOFF=20220101 **NET_THR=0.015**`
  - `Label 4h (net): 48724373 rows | **base=0.1849**`
  - `fold 0 4h: train 3730472 ... **pos=0.2699**`
- `scale_pos_weight` trong JSON = **2.70527601**; `1/3.70527601 = 0,269886` ⇒ **khop dung** `pos=0.2699`
  cua fold 0 ⇒ spw duoc tinh tu BASE CUA FOLD (0,2699), KHONG phai tu base 0,1849 toan cuc va KHONG
  phai tu `maxFav_4h>=0.06` (base do = **0,0457** theo `docs/result/G015CUT_RESULT.md` va theo
  `research/pipeline/g015_net_train.py:6`).
- `research/pipeline/g015_net_train.py:5-6,140`: `mode='net'` -> `y = (retEnd_4h > 0.015)` la recipe cua
  `predwf_G015`; `mode='maxfav'` -> `y = (maxFav_4h >= thr)` la recipe cua **`predwf_G015_v2` / g72**.
- `docs/runbooks/AGENT_RUNBOOK.md:306`: "label `retEnd_4h > 0.015` — **DINH CHINH 2026-09-06**, truoc day ghi
  nham `maxFav_4h >= 0.06`". Nhan `maxFav` la cua **model live** (`Funding_Classifier_Final.onnx`,
  "ho maxFav", `AGENT_RUNBOOK.md:250`), khong phai cua 18 model fold dang do.

⇒ **Gia dinh cua de bai (va ghi chu §3 cua `EVAL_SELECTOR_FEATURES.md`) sai ve provenance.**
Vi vay phan B do **CA HAI** nhan, chot truoc:

- **`y_net` = `1[retEnd_4h > 0.015]`** — nhan **THAT** cua 18 model fold dang do (base 0,1849).
- **`y_fav` = `1[maxFav_4h >= 0.06]`** — nhan theo de bai / ho `maxFav` (base 0,0457).
- **`retEnd_4h`** — nhan lien tuc (thuoc do "co xep hang duoc loi nhuan khong").

Khong doi nhan nao; chi ghi lai su that provenance.

---

## 2. Gia thuyet + tieu chi chot TRUOC

### H1 (do bang so) — "gain cao vi nhan la nguong tuyet doi"
Phat bieu lai cho dung provenance (2 nhanh):
- **H1a:** `rvol15m` co AUC cao voi nhan **`y_fav`** (nhanh cham nguong tuyet doi) nhung IC ~0 voi `retEnd_4h`.
- **H1b:** voi nhan **THAT** `y_net` (= nguong tren **return**), AUC phai **cung dau va cung do lon
  ~ IC** (khong "cao ma IC 0"), vi `y_net` la ham don dieu cua `retEnd_4h`.

**Chot truoc:**
- **H1a DUYET** ⇔ `AUC(y_fav) >= 0,60` **va** `|IC vs retEnd_4h| <= 0,05` (CI95 phu ~0 hoac am).
- **H1a BI BAC** neu `AUC(y_fav) < 0,55`.
- **H1b DUYET** ⇔ `|AUC(y_net) − 0,5| <= 0,03` (tuc AUC ~ 0,5 theo huong IC ~ 0) **trong khi** `gain share = 34%`.
- Khong co vung mo: giua hai nguong ghi "khong du bang chung".

### H2 (do bang so) — "bien thien phan lon la THEO THOI GIAN, khong phai GIUA CAC COIN cung tick"
Phan ra phuong sai tren panel: `SST = SSW (trong-tick, giua coin) + SSB (giua tick, theo thoi gian)`.
`within_share = SSW/SST` (bo NaN theo tung feature).

**Chot truoc:**
- **H2 DUYET** ⇔ `within_share(f36 rvol15m) < min(within_share)` cua **ca 4** doi chieu
  (`#10 f10 distFromLow24H`, `#40 oi_delta24h`, `#35 f35 ret15m`, `#41 oi_z`).
- **H2 DUYET MANH** ⇔ nho hon `0,5 × min` doi chieu.
- **H2 KHONG duoc du lieu ung ho** neu `within_share(f36) >= min` doi chieu.

---

## 3. Cach do (chot truoc)

**Du lieu:** `/tmp/evfeat/joined.parquet` (5.454.290 dong, 26.124 tick, 3 quy DEV; inner-join da co o
`025767f`) + cot `maxFav_4h` **cung file label pb** do `retEnd_4h` lay ra
(`/home/ubuntu/label_15m/funding_label_*_to_*.pb`), khoa `(tEpochMs, symbol) -> (ts, symId)` qua
`symbol_map.csv`. Khong lay lai feature, khong sinh lai label.

**A. Phan ra phuong sai.** Voi tung feature: `SST=Σ(x−x̄)²`, `SSW=Σ_t Σ_{i∈t}(x_ti−x̄_t)²`,
`within_share=SSW/SST`. Tick `n_t=1` dong gop 0 vao SSW (bao luon so tick nhu vay). 5 feature:
`f36` + 4 doi chieu. Bao kem: median coin/tick, `between_share=1−within_share`.

**B. Hai nhan.** Tren tung tick (chi tick `n_t >= 10`):
- `AUC` cua feature vs nhan nhi phan (Mann-Whitney; tick phai co ≥1 pos va ≥1 neg) cho `y_net` va `y_fav`.
- `rank-IC` (Spearman cross-section) vs `retEnd_4h`.
- Trung binh qua tick + CI block-bootstrap **khoi 72h, 400 rep, seed 20260924** (cung thong so
  `025767f` de so duoc). Bao them gia tri pooled (khong dung lam ket luan) va base rate tung nhan.
- Do cho **ca hai** `f36 rvol15m` va `#28 f28 distFromHigh24H` (feature hang 2).
- **Sanity check bat buoc:** `IC(f36)` o day phai tai lap `−0,0424` cua `rank_ic.csv`; neu lech > 0,002
  thi DUNG, bao lai pipeline.
- Phu: decile trong tick -> `P(y=1|D10) − P(y=1|D1)` (pp) cho ca hai nhan.

**C. NaN / coverage.** `%NaN` cua `f36` toan panel + lon nhat theo symbol + so symbol co NaN>0;
`frac tick` ma `f36` la hang so trong tick; va kiem "dinh danh symbol" theo bai hoc
`AUDIT_HARNESS_OFI_2026-09-20.md` (NaN-mask vo tinh lam symbol identity) — neu `%NaN = 0` tren moi
symbol thi **khong the** lam identity bang duong NaN; bao them do trai per-symbol (p5–p95 cua mean
theo symbol) de lam bang chung dinh luong.

**D. Thuoc do quyet dinh (chot truoc).**
- **Thuoc CUA SELECTOR** = `rank-IC` cross-section **trong tick** + `top-8 hit` (proxy:
  `precision@8` = `|top8(feature) ∩ top8(retEnd_4h)| / 8`, tick `n_t >= 16`, bao `lift = precision/(8/n_t)`).
- **KHONG dung `gain`** lam thuoc de cat/giu feature: `gain` la **tong gain chia tach tren tap TRAIN**
  (in-sample, uu tien feature lien tuc/nhieu diem chia), khong phai suc manh du doan ngoai mau.
- **De xuat CAT `rvol15m`** ⇔ `CI95 rank-IC` (vs `y_net` va vs `retEnd_4h`) chua 0 hoac am **VA**
  `lift@8 <= 1,0`. Nguoc lai: **khong du can cu cat tu du lieu offline** — van phai lam **drop-one
  retrain + sim** (ngoai pham vi phien nay) moi chot duoc dong gop bien.
- **De xuat DOI NHAN** (chi de xuat, KHONG tu lam) neu `AUC(y_fav)` cao ma `IC(retEnd)` ~0.

**Ngoai pham vi (khong lam):** khong retrain, khong drop-one, khong sim, khong cham 2026, khong push.

---

## 4. KET QUA (do 2026-09-24, offline; script `/tmp/rvol15m/diag.py`, log `/tmp/rvol15m/out.log`)

Panel do: **5.454.290 dong · 26.124 tick · 275 symbol** · median **218 coin/tick** (p05 140 / p95 260,
0 tick `n_t=1`). `maxFav_4h` merge tu **cung** file label pb, **notna = 1,0000** (0 dong thieu).
Base rate: **`y_net` = 0,1731** · **`y_fav` = 0,0343**.

**Sanity pipeline (chot truoc):** `IC(f36)` o day = **−0,0421**, tai lap `rank_ic.csv` **−0,0424**
(lech 0,0003 < 0,002) ⇒ PASS. Gain share doc lai truc tiep tu 18 model JSON: `f36` **34,09%**
(khop `025767f`), roi `f28` 7,06 / `f40` 5,74 / `f10` 3,78 ⇒ hang y het.

### A. Phan ra phuong sai — **H2**

`within_share` = phan phuong sai **trong-tick (giua cac coin cung tick)**; `between_share` = theo thoi gian.

| # | feature | NaN% | **within_share** | between_share | sd(x) toan panel | sd(mean theo tick) |
|---|---|---|---|---|---|---|
| 36 | **rvol15m** | 0,0000 | **0,5536** | 0,4464 | 0,00100 | 0,00070 |
| 10 | distFromLow24H | 0,0000 | 0,6299 | 0,3701 | 0,0483 | 0,0289 |
| 40 | oi_delta24h | 0,3236 | 0,9278 | 0,0722 | 0,2184 | 0,0585 |
| 35 | ret15m | 0,0000 | 0,4899 | 0,5101 | 0,0061 | 0,0043 |
| 41 | oi_z | 0,0856 | 0,8956 | 0,1044 | 1,0935 | 0,3380 |

`min(4 doi chieu) = 0,4899` **(f35 ret15m)** < `within_share(f36) = 0,5536`

> **H2 SAI (du lieu KHONG ung ho).** `rvol15m` **khong** "bien thien chu yeu theo thoi gian":
> **55,4%** phuong sai cua no nam **TRONG tick** (giua cac coin) — nhieu hon ca `f35 ret15m` (49,0%).
> Robustness (khong trong pre-reg): lap lai tren `asinh(x)` -> `f36` 0,5536 · `f35` 0,4897 · `f10` 0,6228
> ⇒ **ket luan khong doi** (khong phai do duoi/outlier vol).
> He qua: "vo dung cho cross-section rank" **khong** the giai thich bang phuong sai; phai giai thich bang
> **huong** cua tin hieu (muc B).

### B. Hai nhan — **H1** (per-tick; IC tren toan bo 26.124 tick, AUC tren tick co ≥2 pos va ≥2 neg: 24.762 tick,
`n_t >= 10`; CI block-72h 400 rep seed 20260924)

| feature | IC vs `retEnd_4h` | **AUC vs `y_net`** (nhan THAT) | **AUC vs `y_fav`** (`maxFav>=6%`) | D10−D1 `P(y_net)` | D10−D1 `P(y_fav)` | prec@8 | **lift@8** |
|---|---|---|---|---|---|---|---|
| **36 rvol15m** | **−0,0421** [−0,0492, −0,0358] | **0,6523** [0,6448, 0,6594] | **0,7796** [0,7714, 0,7875] | **+14,39pp** | **+10,98pp** | 0,158 | **4,12** [3,93, 4,33] |
| 28 distFromHigh24H | −0,0163 [−0,0231, −0,0089] | 0,5778 [0,5703, 0,5852] | 0,6016 [0,5897, 0,6137] | +7,43pp | +3,89pp | 0,117 | 3,00 [2,85, 3,18] |

Pooled (chi de tham chieu, khong ket luan): AUC `f36` = 0,6232 (`y_net`) / 0,7552 (`y_fav`);
`f28` = 0,5791 / 0,6008.

> **H1a DUYET**: `AUC(y_fav) = 0,7796 >= 0,60` **va** `|IC vs retEnd| = 0,0421 <= 0,05` ⇒ nhanh **cham
> nguong tuyet doi** duoc `rvol15m` du doan rat tot, trong khi lien he **rank** voi loi nhuan ~0.
> **H1b BI BAC**: `|AUC(y_net) − 0,5| = 0,152 > 0,03` — nhan **THAT** cung co AUC **0,652** (CI khong chua 0,5),
> khong he ~0,5. Tuc `rvol15m` **co tin hieu that** cho nhan dang train; 34% gain khong phai rac.
> **H1 (ban de bai) SAI o tien de**: nhan train khong phai `maxFav_4h>=6%` (xem §1) — chinh ghi chu §3 cua
> `EVAL_SELECTOR_FEATURES.md` cung sai o cho nay.

**Post-hoc (NGOAI pre-reg, ghi ro la do sau khi doc bang A/B):** do them 2 thuoc de giai thich
*AUC 0,65 ma IC ~0*:

| do luong (per-tick) | f36 rvol15m | f28 di doi chieu |
|---|---|---|
| AUC vs `retEnd_4h < −1,5%` (duoi THUA) | **0,7264** [0,7187, 0,7344] — **cao hon** duoi thang | 0,6059 [0,5973, 0,6151] |
| IC vs **`|retEnd_4h|`** (do LON) | **+0,2449** [+0,2369, +0,2516] | +0,1482 [+0,1390, +0,1561] |
| lift@8 theo `top8(retEnd)` | 4,12 [3,93, 4,33] | 3,00 [2,85, 3,18] |
| lift@8 theo **`bot8(retEnd)`** (nhoi THUA) | **5,80** [5,54, 6,10] — **cao hon nhoi THANG** | 3,79 [3,56, 4,04] |

⇒ `rvol15m` do **DO LON bien dong** (bien do), **khong do DAU**: no nang ca xac suat cham +1,5% lan
−1,5%, va manh hon o duoi. Day moi la co che that cua "gain 34% ma IC ~0".

### C. NaN / coverage — "dinh danh symbol"

- `NaN(f36) = 0` tren **5.454.290/5.454.290** dong (**0,0000%**); **0/275 symbol** co ≥1 NaN;
  khong co tick nao thieu `f36` (coverage/tick thap nhat 50,55% la do universe tick, khong do feature).
- ⇒ **KHONG co "dinh danh symbol" bang NaN-mask** (bai hoc `AUDIT_HARNESS_OFI_2026-09-20.md` khong ap dung).
- Bang chung dinh luong bo sung: `mean(f36)` theo symbol p05 0,0009 / p50 0,0013 / p95 0,0021,
  `sd(giua symbol) = 0,0004` **<** `sd(trong tick, trung binh) = 0,0007` ⇒ bien thien **trong-tick lon hon**
  bien thien giua symbol ⇒ khong phai bien gia theo coin.

### D. KET LUAN + DE XUAT

**(1) H1:** dung o **co che** (nhan nguong ⇒ AUC cao), **sai o tien de** (nhan that = `retEnd_4h > 0,015`,
khong phai `maxFav_4h>=6%`), va **sai o phan "nhan that thi AUC ~0,5"** (that ra 0,652).
Tin hieu **co that**, nhung la tin hieu **bien do/fat-tail**, khong phai tin hieu **xep hang co dau**.
**(2) H2:** **SAI** — 55,4% phuong sai nam trong-tick, nhieu hon doi chieu `f35` (49,0%).
**(3) Co nen cat `rvol15m`?** Theo tieu chi chot truoc: **KHONG du can cu de cat tu du lieu offline.**
Tieu chi cat ("CI95 rank-IC am/chua 0 **VA** lift@8 <= 1,0") **khong thoa** — `lift@8 = 4,12 [3,93, 4,33]`.
Hai thuoc cua selector **MAU THUAN**: `rank-IC` cross-section noi "bo" (am, CI khong chua 0) con
`top-8 hit` noi "giu" (lift 4,12) — cung mot feature, hai ket luan nguoc, vi no chon coin **fat-tail**
(ca duoi thang 4,12 lan duoi thua 5,80 deu > 1).

> ⚠️ **THUOC NAO PHAI DO:** neu cat feature thi **bat buoc** do bang thuoc **CUA SELECTOR**
> (**rank-IC cross-section trong tick** + **top-8 hit / lift@8**), tren **dung nhan** dang train —
> **KHONG duoc dung `gain`**. Ly do bang so: `gain` la tong gain chia tach **in-sample tren tap TRAIN**,
> thuong feature lien tuc/nhieu diem chia (f36 dung o **18/18 fold**, `top10/18 = 18`) — no **khong** do
> suc manh du doan ngoai mau, va o day con **cung ton tai** voi mot tin hieu that (AUC 0,65) =>
> "gain 34%" **khong** phai nhan xet "vo dung", cung **khong** phai bang chung "nen giu".
> Quyet dinh cuoi cung: **drop-one retrain + sim** (ngoai pham vi phien nay). Du doan cu the de test:
> bo `rvol15m` => **admit tang** (it coin duoi thua duoc chon hon) nhung **expectancy/top-8 win giam**;
> ket qua phu thuoc **EXIT** (given nhom fat-tail), nen khong the chot offline.

**(4) De xuat DOI NHAN (chi de xuat — KHONG tu lam):** vi `rvol15m` chi do **bien do**:
- Neu muc tieu la xep hang coin theo **loi nhuan co dau**, nhan `retEnd_4h > thr` (dang dung) la **nhan dau**
  dung huong; van de la **feature** nay manh o do-lon chu khong o dau, nen khong nen ky vong no tu no tao order.
- Dang can nhac: (a) them **thanh phan phat rui ro duoi** (vi du tach tin hieu thanh 2 kenh: `rvol` cho bien do,
  momentum/funding cho dau) thay vi de 1 feature vua duoc gain cao vua am IC; (b) neu doi nhan gia thuyet
  sang dang **cham nguong 2 phia** (`|retEnd_4h|` / barrier 2 chieu) thi phai la **quyet dinh cua chu du an**
  kem pre-reg va sim — **khong** doi nhan trong phien nay.

**(5) Sua so sai:** `docs/analysis/EVAL_SELECTOR_FEATURES.md` §3 ghi "Nhan `retEnd_4h` **khong phai** nhan train cua
selector (`y = (maxFav_4h >= 6%)`)" — **SAI**; nhan that cua `predwf_G015/model_f*_4h.json` la
`retEnd_4h > 0,015` (`docs/runbooks/AGENT_RUNBOOK.md:306`). Khong sua file do trong phien nay (chi 1 file duoc commit).

### Pham vi / khong lam

Khong train, khong drop-one, khong sim, khong sua Java/feature, khong doc 2026, **khong push**.
1 file commit: `docs/diag/DIAG_RVOL15M.md`.
