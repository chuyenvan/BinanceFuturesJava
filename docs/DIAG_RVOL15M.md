# DIAG_RVOL15M — vi sao `rvol15m` gain 34% nhung IC ~0

**Ngay:** 2026-09-24 · **Nhanh:** `module` · **Trang thai:** PRE-REG (chot TRUOC khi do)
**Pham vi:** DEV only — 3 quy `20230101_to_20230401`, `20231001_to_20240101`, `20240401_to_20240701`.
**KHONG doc 2026. KHONG train. KHONG sim. Thuan Python offline.** Khong push.

---

## 0. So da co (khong dien giai lai)

`docs/EVAL_SELECTOR_FEATURES.md` (commit `025767f`), 18 model fold
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
  phai tu `maxFav_4h>=0.06` (base do = **0,0457** theo `docs/G015CUT_RESULT.md` va theo
  `research/pipeline/g015_net_train.py:6`).
- `research/pipeline/g015_net_train.py:5-6,140`: `mode='net'` -> `y = (retEnd_4h > 0.015)` la recipe cua
  `predwf_G015`; `mode='maxfav'` -> `y = (maxFav_4h >= thr)` la recipe cua **`predwf_G015_v2` / g72**.
- `docs/AGENT_RUNBOOK.md:306`: "label `retEnd_4h > 0.015` — **DINH CHINH 2026-09-06**, truoc day ghi
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

## 4. KET QUA

_(dien sau khi do — phan tren la pre-reg chot truoc, khong sua)_
