# RESULT — VI SAO KHONG TAI LAP DUOC STORE FEATURE SINH `pred.bin` (corr 0,762)

Pre-reg chot TRUOC: `docs/prereg/PREREG_PREDBIN_REPRO.md` (chot 2026-09-28, truoc moi phep do moi).
**CHI DOC** Oracle/242; khong chay Java/sim/WFO tren Oracle; khong cham production/242/ONNX; khong push du lieu.
FIT `<= 2025-12-31`; **2026 chi chan doan**. Moi phep do la **Python nhe local** tren artifact co san.
Nguon dong luc: `RESULT_P15_SOURCE.md` §3.4 + `Claude outputs/AUDIT_20260928_C_edge_coverage.md` §0.5/§254.

**KET LUAN MOT CAU:** **Store goc KHONG mat — `pred.bin` TAI LAP DUOC.** Con so "corr 0,762" trong
`RESULT_P15_SOURCE` §3.4 **khong phai** ket qua cua phep tai lap per-fold dung cach, ma la **corr cao nhat
cua 1 model dong bang (frozen) ap sai cua so**. Khi **retrain** per-fold dung hyperparam tai lieu tren chinh
store con tren dia, `pred.bin` duoc tai lap **19/19 fold** (pearson 0,9918–0,99786; spearman 0,9847–0,99812;
p50 khop toi 1e-5; duoi DEV cung tai lap). Nguyen nhan goc **KHONG** thuoc H1/H2/H4 (feature/tien xu ly/nhan),
ma la **H3-dang provenance: bo file `.onnx` dong bang tren dia KHONG phai the he model da sinh `pred.bin`**.
⇒ Duoc phep dung `pred.bin` lam chuan **cho DEV**, nhung **KHONG** duoc dung lam chuan hieu chuan cho LIVE
(ly do khac, giu nguyen: nguon feature live khac nguon DEV).

---

## 1. VIEC 1 — "STORE GOC" LA GI (bang chung)

### 1.1 `pred.bin` goc

| thuoc tinh | gia tri (do lai, read-only) |
|---|---|
| path | `/home/ubuntu/wfo_ds_x1_2021/pred.bin` (byte-identical: `/home/ubuntu/simbundle/pred.bin`, `/home/ubuntu/simbundle_x1_t170/pred.bin`) |
| md5 | **`5dd6bb4c3f98d89d58770005c0001526`** = `md5_pred` trong `manifest.txt` cua bundle ✔ |
| kich thuoc / so dong | 40.004.164 B = 4 + 2.500.260 × 16 ⇒ **n = 2.500.260** |
| dinh dang | big-endian, tu mo ta: `[count:int32]` roi count × `[ts:int64][predReturn15M:float32][predRisk4H:float32]` (`WfoDataset.F_PRED`, `DataOutputStream`) |
| khoang thoi gian | **2021-04-01 00:00 → 2025-12-31 23:59 (+07)**, luoi **1 phut lien tuc** (diff = 60.000 ms cho ca 2.500.259 buoc, **0 trung lap**, 100% ts % 60000 == 0) |
| phan bo (FIT) | p50 **0,545%** · p99 **1,308%** · max **12,261%** (khop `RESULT_GATE_ROOTCAUSE` §1.1 dong `S_dev`) |
| cot 2 (`predRisk4H`) | lay tu set **CU** `ai_pred_market_full_basket_v2` (model TINH train batch toan dai — tai lieu `model_quality_wfo_20260704.md` ghi ro **KHONG leak-free**) |

### 1.2 Sinh boi ai

Chuoi (code, `src/main/java/...`):
1. `features/export/gate/ExportGateDataset.java` (`replayToCsv`) — replay Aerospike, xuat **store feature**
   (`~/claudedata/gate_dataset_full.csv.gz`) bang `ComprehensiveMarketFeatureExtractor` (Java) + label
   `label_oldbasket` (max upside 15' cua ro `findPotentialLosers`).
2. `features/export/gate/WFOGateRunner.java` — 21 fold **expanding** (anchor 2021-01-01, minTrain 3 thang,
   OOS = step = 3 thang) → moi fold goi `ml/gate/train_gate_fold.py` (XGBRegressor depth4/n150/lr0,05/
   sub0,8/col0,8/mcw10/seed42, **purge 15 phut**, **KHONG scaler**) → predict OOS bang `OnnxInferenceManager`
   → ghi **`wfo_gate_pred.csv`**.
3. `LoadWfoGatePredTool` nap CSV → Aerospike set **`ai_pred_market_gate_wfo`** (manifest bundle:
   `sourcePredSet=ai_pred_market_gate_wfo`, `codeGitSha=e57fd3d` — co trong git history).
4. `WfoDataset.export` (chay 2026-09-12 15:59, `leakFreeFrom=2021-07-01`) → `pred.bin`.

**Xac nhan doc lap nguon CSV:** `pred.bin` **≡** `~/claudedata/wfo_gate_pred.csv`
(md5 `b160a018b912ffdd61b6409d1208dad3`, == `gate_push_ds/wfo_gate_pred.csv`): n = 2.500.260,
join **2.500.260/2.500.260**, **exact (|Δ| < 1e-7) = 100,0000%**, **corr = 1,00000**, corr theo nam = 1,0 ca 5 nam.

### 1.3 "Store goc" con tren dia — **4 ban, NOI DUNG FEATURE GIONG HET**

| file | mtime | ghi chu |
|---|---|---|
| `~/claudedata/gate_dataset_full.csv.gz` | 2026-08-08 | store chuan cua harness `gate_feat_study` / `h1_p15_repro.py` |
| `~/claudedata/gate_ab_full/fs_full.csv` | 2026-08-18 | store cua run WFOGateRunner 17-18/08 (`full.log`) |
| `~/claudedata/gate15m_v2_full.csv` | 2026-08-29 | **nhieu hon 4 cot label**; `RESULT_P15_SOURCE` §3 ghi "(= fs_full.csv)" |
| `~/claudedata/gate_ab_full2/fs_full2.csv` | 2026-08-18 | ban A/B label `retall*` |

**Phep do quyet dinh (cua so 2025Q4, 132.480 dong noi):** so **ca 33 feature** tung cap → `max|ΔF| = 0.000e+00`
voi **ca 3 ban con lai**. ⇒ **Chi co DUY NHAT 1 noi dung store**; khac biet giua cac file **chi o cot label**
(khong phai feature). ⇒ **H1 (khac feature giua cac store) = SAI**; va khong ton tai "store thu 5" nao khac
(tim `find` toan `/home/ubuntu` (chi con `wfo_feature_store.csv` 166.836 dong, 2021-01..04 — artifact CU khac).
Luu y: `wfo_feature_store.csv` (2021 only) **khong phai** store sinh `pred.bin`.

### 1.4 Bang chung "no da mat" — da kiem gi, ket qua ra sao

- `RESULT_P15_SOURCE.md` §3.4: chay 21 `wfo_models/fold_*` tren feature 2025-10→12 ⇒ "corr 0,762, mean ratio 1,33";
  **khong fold nao** cho p50 0,900 + p99 1,401 + max 11,946 ⇒ ket luan "store goc da mat, khong khoanh vung duoc".
- Tai kiem tra lai (read-only, phan nay): **khong thieu file nao**. Cai "bi mat" khong phai store ma la
  **the he model `.onnx`** (muc 2.3). Khong co backup store nao khac can tim.

---

## 2. VIEC 2 — TAI LAP LAI + DO NGUYEN NHAN

### 2.1 Tai lap bang model DONG BANG (dung nhu §3.4) → **THAT BAI (va giai ma duoc con so 0,762)**

| cap (store, model dir) | cua so | pearson | p50 model | p50 `pred.bin` |
|---|---|---|---|---|
| `gate_dataset_full.csv.gz` + `wfo_models/fold_18` | 2025Q4 | **0,681** | 1,354% | 0,900% |
| `gate_ab_full/fs_full.csv` + `wfo_models/fold_18` | 2025Q4 | **0,681** | 1,354% | 0,900% |
| `gate_ab_full2/fs_full2.csv` + `wfo_models/fold_18` | 2025Q4 | **0,681** | 1,354% | 0,900% |
| `gate_ab_full/models/label_oldbasket/fold_18` | 2025Q4 | **0,681** | 1,354% | 0,900% |
| **quet ca 21 model `wfo_models`**, chon corr cao nhat | 2025Q4 | **fold_20 = 0,76214** | 1,122% | 0,900% |

⇒ **con so 0,762 trong `RESULT_P15_SOURCE` §3.4 = corr cua `fold_20` (model cuoi, train toi 2026-04) ap LEN
cua so 2025Q4** — tuc model **in-sample** voi chinh cua so do, va van chi 0,762. Phep tai lap **per-fold dung
cach** (fold_18 cho cua so 2025Q4) chi **0,681**. Kiem chung cheo: doc ghi "p50 chay tu 0,748 (fold_0)" —
do lai **0,7479%** ⇒ *cung mot store, cung mot bo model*; chi cach ghep la khac.
Duoi 21 model **khong fold nao** ≥ 0,77 ⇒ khong phai loi lech chi so fold (fold index offset).

### 2.2 PHEP THU QUYET DINH: **RETRAIN** per-fold tren store con tren dia → **TAI LAP DUOC**

Dung dung hyperparam tai lieu (`ml/gate/train_gate_fold.py`), purge 15', 33 feature V3FULL, label `label_oldbasket`,
predict OOS tung fold, ghep chuoi 19 fold DEV → so voi `pred.bin`:

| fold | cua so OOS | n | pearson | spearman | p50 repro / `pred.bin` | max repro / `pred.bin` |
|---|---|---|---|---|---|---|
| 0 | 2021Q2 | 131.040 | 0,99578 | 0,987172 | 0,007251 / 0,007243 | 0,1094 / 0,1027 |
| 1 | 2021Q3 | 132.480 | 0,99232 | 0,988608 | 0,005194 / 0,005286 | 0,0916 / 0,0898 |
| 2 | 2021Q4 | 132.480 | 0,99563 | 0,992239 | 0,005493 / 0,005480 | 0,1170 / **0,1226** |
| 3 | 2022Q1 | 129.600 | 0,99406 | 0,990381 | 0,006216 / 0,006240 | 0,0379 / 0,0387 |
| 4 | 2022Q2 | 131.040 | 0,99571 | 0,995890 | 0,005481 / 0,005476 | 0,0818 / 0,0727 |
| 5 | 2022Q3 | 132.480 | 0,99182 | 0,991761 | 0,004939 / 0,004946 | 0,0513 / 0,0493 |
| 6 | 2022Q4 | 132.480 | 0,99528 | 0,984659 | 0,003781 / 0,003801 | 0,0858 / 0,0719 |
| 7 | 2023Q1 | 129.600 | 0,99679 | 0,996141 | 0,004603 / 0,004580 | 0,0377 / 0,0376 |
| 8 | 2023Q2 | 131.040 | 0,99605 | 0,995601 | 0,003925 / 0,003876 | 0,0667 / 0,0727 |
| 9 | 2023Q3 | 132.480 | 0,99589 | 0,994428 | 0,003365 / 0,003359 | 0,0851 / 0,0858 |
| 10 | 2023Q4 | 132.480 | 0,99757 | 0,997550 | 0,004783 / 0,004767 | 0,0774 / 0,0753 |
| 11 | 2024Q1 | 131.040 | 0,99689 | 0,998121 | 0,005698 / 0,005715 | 0,0845 / 0,0895 |
| 12 | 2024Q2 | 131.040 | 0,99728 | 0,997201 | 0,004985 / 0,004988 | 0,0801 / 0,0736 |
| 13 | 2024Q3 | 132.480 | 0,99719 | 0,997423 | 0,004694 / 0,004698 | 0,0784 / 0,0754 |
| 14 | 2024Q4 | 132.480 | 0,99786 | 0,998442 | 0,005680 / 0,005705 | 0,0460 / 0,0469 |
| 15 | 2025Q1 | 129.600 | 0,99599 | 0,996516 | 0,006156 / 0,006160 | 0,0536 / 0,0486 |
| 16 | 2025Q2 | 131.040 | 0,99592 | 0,996493 | 0,006536 / 0,006554 | 0,0267 / 0,0263 |
| 17 | 2025Q3 | 132.480 | 0,99641 | 0,996671 | 0,006940 / 0,006891 | 0,0662 / 0,0556 |
| 18 | 2025Q4 (cat 31/12) | 132.480 | 0,99347 | 0,995254 | 0,009000 / 0,009004 | 0,1169 / **0,1195** |

**Corr THEO NAM** (cua so fold nam tron trong 1 nam):

| nam | fold | pearson per fold | spearman per fold |
|---|---|---|---|
| 2021 | 0,1,2 | 0,99578 · 0,99232 · 0,99563 | 0,9872 · 0,9886 · 0,9922 |
| 2022 | 3,4,5,6 | 0,99406 · 0,99571 · 0,99182 · 0,99528 | 0,9904 · 0,9959 · 0,9918 · 0,9847 |
| 2023 | 7,8,9,10 | 0,99679 · 0,99605 · 0,99589 · 0,99757 | 0,9961 · 0,9956 · 0,9944 · 0,9976 |
| 2024 | 11,12,13,14 | 0,99689 · 0,99728 · 0,99719 · 0,99786 | 0,9981 · 0,9972 · 0,9974 · 0,9984 |
| 2025 | 15,16,17,18 | 0,99599 · 0,99592 · 0,99641 · 0,99347 | 0,9965 · 0,9965 · 0,9967 · 0,9953 |

⇒ **19/19 fold pearson ≥ 0,9918 · 19/19 spearman ≥ 0,9847**; **p50 khop toi 1e-5**; p99 lech ≤ 1,2%;
max (1 quan sat / 132k dong) lech 1–20% = nhieu cuc tri, khong he thong.
Theo tieu chi pre-reg (`corr >= 0,99` + p50/p99/max khop ≤1%) ⇒ **TAI LAP DUOC**.
So sanh doc lap: chinh `RESULT_GATEFEAT` **Stage 0** (retrain 33 feature tren cung `gate_dataset_full.csv.gz`)
cung bao spearman **0,997792** vs p15 goc — *khop* voi ket qua nay (0,9847–0,9981).

### 2.3 Phan biet H1–H4: bang so

| gia thuyet | ket qua | bang chung |
|---|---|---|
| **H1 khac FEATURE** | **BAC BO** | 4 store co 33 feature **bit-identical** (`max|ΔF| = 0`); retrain tren chinh store do ⇒ khop `pred.bin` |
| **H2 khac TIEN XU LY** | **BAC BO** | khong scaler o bat ky dau (`ExportGateDataset`/`train_gate_fold.py`/`WFOGateRunner`/`OnnxInferenceManager` deu RAW); ONNX = `TreeEnsembleRegressor` thuan. Khop lai §3.1-3.2 `RESULT_P15_SOURCE` |
| **H3 khac PHAM VI** | **XAC NHAN (dang PROVENANCE)** | *khong* phai symbol/universe/khoang tg: **4 store feature-giong nhau**, cua so/dong khop. Cai lech la **the he model**: `wfo_models/fold_k` (06/08) va `gate_ab_full/models/label_*/fold_k` (18/08) cho du doan **GIONG HET NHAU** (pearson/p50 trung khop 5 chu so, du md5 khac) ⇒ ca 2 deu la "ban retrain", **khong phai** the he san xuat sinh `pred.bin` |
| **H4 khac NHAN** | **BAC BO** | corr `pred.bin` voi cac label khac: `label_ret15m` 0,428 · `label_ret60m` 0,442 · `label_retall15m` 0,407 · `label_retall60m` 0,422 · `v4v5/ret15m` 0,421 · `v4v5/ret60m` 0,480 (theo nam `label_ret15m` cao nhat cung chi 0,61) — **khong** o muc nao la `pred.bin`. `pred.bin` thuoc the he `label_oldbasket`: `gate_ab_full/wfo_gate_pred_label_oldbasket.csv` vs `pred.bin` **corr 0,999914, 89,5% dong |Δ|<1e-7, max|Δ| 4,2e-3** |

### 2.4 Phan KHOP / phan LECH (noi ro, khong suy dien)

- **Khop:** toan bo **than** phan bo (p1..p99; p50 khop 1e-5..1e-6), **theo ca 5 nam**, va **ca duoi** (max
  cua cua so fold 2: 0,1170 vs 0,1226; fold 18: 0,1169 vs 0,1195) ⇒ duoi DEV la **tinh chat that** cua
  (store + model), khong phai artifact "lam tay".
- **Lech (con lai, ghi RO):** (a) nhieu retrain XGBoost lam corr dung o ~0,99 chu khong phai 1,0
  (khong the dat bit-exactly neu khong co model goc); (b) **cuc tri max tung cua so** lech 1–20% do 1 quan sat;
  (c) **khong xac dinh duoc** bo `.onnx` dong bang thuoc the he nao (khong co log/sha cua lan export do) —
  **day la khoang trong provenance that su**, xem §4.
- **Khong lam duoc (ghi RO):** khong chay lai `WFOGateRunner` (can Aerospike 226 + nhieu gio + rang buoc
  "khong chay Java tren Oracle") ⇒ khong the doi chieu bit-exact duong ong goc; va live **khong ghi** vector
  33 feature ra file ⇒ khong do duoc chenh live-vs-DEV trong phien nay.

---

## 3. VIEC 3 — TAC DONG

### (1) NHUNG KET LUAN PHU THUOC `pred.bin` (cot p15) — va con dung duoc khong

| ket luan / tai lieu | cach dung `pred.bin` | con dung duoc? |
|---|---|---|
| `RESULT_GATE_ROOTCAUSE` (`S_dev` 2.500.260 dong, p50 0,545/max 12,26) | phan bo goc de so voi live | **CON** (phan bo do lai y nguyen); nhung ket luan "khong map duoc bang 1 thua so" van dung, **nguyen nhan la nguon live, khong phai store** |
| `RESULT_GATE_RECAL` (nguong phan vi cuon `thr`) | chuoi p15 cua sim | **CON** cho DEV; **VO HIEU voi live** nhu cu (live max 2,30% < moi `thr` 2,9–3,8%) |
| `RESULT_GATEFEAT` (bo/thay 33 feature, config 27f `GF27`) | p15 cua tung chu trinh + doi chieu p15 goc | **CON** (va nay **manh hon**: doi chieu p15 goc la doi chieu duoc, khong phai "do corr 0,76") |
| `RESULT_P15_SOURCE` §3.4 "store goc da mat" | — | **SAI — PHAI SUA** (muc 5) |
| Toan bo sim DEV tren `wfo_ds_x1_2021` (+ copy trong `simbundle*`): KEEPLEG0/T170, `RESULT_BD_*`, `RESULT_BOOK*`, `RESULT_CAP70_FEE06`, `RESULT_2X_HALFSIZE`, `RESULT_5MGRID`, `RESULT_CONCENTRATION_SAFETYCAP`, `RESULT_STAGE3_SIM` (P3) | `pred.bin` = dau vao gate (75,4% lenh qua gate) | **CON** — khong phai xay tren artifact khong tai lap duoc. **Nhung** tinh **chuyen duoc sang LIVE** van **chua** duoc chung minh (muc (3)) |
| Bat ky ket luan nao dung `predRisk4H` (brake/dyn risk, `HARD_RISK_LIMIT_4H`) | cot 2 cua `pred.bin` | **CANH BAO (khong doi)**: cot nay tu set **CU** `ai_pred_market_full_basket_v2`, tai lieu da ghi **KHONG leak-free** (model tinh train toi ~19/12/2025) ⇒ vung < 2025-12 la **in-sample lac quan**. Day la ro ri **co san trong pred.bin**, doc lap voi p15 |

### (2) NHUNG KET LUAN **KHONG** PHU THUOC (an toan)

- Selector/S1: rank-IC, SEL_*, `RESULT_S1_OI12` (dung p15 chi 1 dong dan chieu), S1 free-OFI.
- OFI: `RESULT_OFI_MONEY`, `RESULT_OFI_GAINSHARE` (ledger/sim), OFI reorient.
- Tail/robustness do tu **ledger + sim exit**: `RESULT_TAIL50_RULER_REDUNDANCY`, `RESULT_TAIL_ROBUST_RULERS`,
  `RESULT_TAIL_LEVER`, `RESULT_CROWDED_LONG`, `RESULT_CLOSE_BIGGAP`, toan bo nhom C4/B4/COV tu ledger.
- `RESULT_CAP70_FEE06` (bang chung grep: khong tham chieu `pred.bin`/p15 — do tu sim+ledger).
⇒ Neu `pred.bin` co van de, **nhom nay khong bi anh huong**.

### (3) Duoi p15 DEV co phai artifact khong? — **TRA LOI BANG SO**

- Duoi DEV **tai lap duoc** tu store + dung cong thuc train: fold 2 max **0,1170** vs `pred.bin` **0,1226**;
  fold 18 **0,1169** vs **0,1195**; p99 tung fold khop ≤1,2%. ⇒ **Khong co bang chung** nao cho thay duoi DEV
  duoc "lam ra" bang mot buoc offline khong the xay ra live. Gia thuyet "duoi DEV la artifact ⇒ live cat duoi la
  HANH VI DUNG" **khong duoc ung ho boi du lieu nay** (no khong bat nguon tu "store bi mat / pipeline tay").
- **Nhung** dieu nay **KHONG** chung minh nguoc lai: van chua giai thich duoc vi sao live **khong** co duoi
  (live max 2,30% vs DEV cung quy 11,95%). Sau khi loai "store mat", nguyen nhan con lai **duy nhat** la:
  **input 33 feature cua duong live khac store DEV** (nghi pham VTS + funding, theo `26e4b3f`/`PASS1`) —
  va day la **lo chua dong**, khong duoc phep ket luan "nguong gate moi la cai SAI".

---

## 4. VIEC 4 — DE XUAT

1. **Dong khoang trong provenance (re nhat, lam ngay duoc):** freeze dinh nghia tai lap duoc:
   `sha256(gate_dataset_full.csv.gz)` + `sha256(ml/gate/train_gate_fold.py)` + hyperparam + bang fold
   (anchor 2021-01-01, minTrain 3m, OOS 3m, purge 15m, V3FULL 33 thu tu) ghi vao `PIPELINE_PROVENANCE.md`
   va vao `manifest.txt` khi export. Tu nay "tai lap p15" = (store sha + script sha + retrain) ⇒ **corr ≥ 0,99**
   la dat; khong bao gio lai dung bo `.onnx` dong bang lam chuan.
2. **Bo/vo hieu hoa "chuan dong bang" `wfo_models/fold_*` + `gate_ab_full/models/label_*/fold_*`:**
   chung khong tai lap `pred.bin` (0,68) va **khong biet thuoc the he nao** ⇒ de nham. Neu can freeze model,
   phai kem md5 + the store sha da train.
3. **Sua `RESULT_P15_SOURCE` §3.4 + Audit C §0.5/§254:** doi ket luan "store goc da mat / khong tai lap duoc"
   thanh "**tai lap duoc bang retrain; con so 0,762 la corr cua model dong bang ap sai cua so**".
4. **Neu muon bo han `pred.bin`:** duoc, nhung **khong giai quyet duoc gi** — hieu chuan lai tu nguon live
   van bat kha thi voi du lieu 2026 hien co (n = 8.986; max 2,30% < moi ung vien `thr`). Viec **dung** phai lam
   truoc la **do lai nguon feature live** (buoc (1) cua `RESULT_P15_SOURCE` §4.3).
5. **40 feature Tool1 "opaque" — CO LIEN QUAN KHONG?** **Khong truc tiep**: do la feature cua **Tool1/S1
   selector** (`ExportTool1Master.java` + `ml/lib/tool1_col.py`), khac hoan toan 33 feature gate
   (`ComprehensiveMarketFeatureExtractor`). Nhung **cung lop rui ro** (khong doc duoc noi tinh feature) va
   `LEAK_L1_REPORT.md` §"CON LAI" muc 1 tu ghi la **lo hong leak duy nhat con mo**. De xuat dong: (a) ghi
   cong thuc/cua so thoi gian cua `f0..f39`; (b) regen 1 fold + so md5 de chot provenance; (c) neu khong
   doc duoc noi tinh ⇒ thay bang extractor da verify. **Khong** lien quan den ket luan o bai nay.
6. **Neu khong lam duoc o phien nay, can gi:** (a) **khong** can backup store nao nua (store da co + da
   chung minh tai lap duoc); (b) can **1 lan dump 33 feature live** tren shadow (read-only, them 1 dong log —
   can owner duyet) de dong not chenh live-vs-DEV; (c) can log/sha cua lan export ONNX (06/08 & 18/08) neu
   muon biet chinh xac bo `.onnx` dong bang thuoc the he nao.

---

## 5. MUC BO / LY DO (khai RO)

- **Bo:** chay `WFOGateRunner`/Java/sim tren Oracle (rang buoc + shadow dang chay) ⇒ chi **retrain Python nhe**
  tren store co san; he qua: khong bit-exact, nhung **du de ket luan** (0,99 vs 0,68).
- **Bo:** retrain lai **21 fold dong bang** de thay the model cu — khong can (da co 19 fold retrain).
- **Bo:** doc toan bo `gate15m_v2_full.csv` (1,24 GB, 42 cot) — chi doc 33 cot can thiet; cac store lon chi doc
  **1 lan/cua so** (2025Q4) cho phep so feature.
- **Bo (khai RO):** khong xac dinh duoc **the he** cua bo `.onnx` dong bang (thieu log/sha) — ghi la khoang
  trong, khong suy dien.
- 2026: **khong** dung de fit/chon tham so nao; `pred.bin` ket thuc 2025-12-31 23:59 nen bai nay khong nhin 2026.

## 6. BANG CHUNG THO (tai lap, output nho)

```bash
# dinh dang + thong ke pred.bin (big-endian!)
python3 - <<'P'
import struct,numpy as np
raw=open("/home/ubuntu/wfo_ds_x1_2021/pred.bin","rb").read(); n=struct.unpack(">i",raw[:4])[0]
a=np.frombuffer(raw[4:4+n*16],dtype=np.dtype([("ts",">i8"),("p15",">f4"),("risk",">f4")])).astype([("ts","<i8"),("p15","<f4"),("risk","<f4")])
print(n,pd.to_datetime(a["ts"].min(),unit="ms"),pd.to_datetime(a["ts"].max(),unit="ms"),np.percentile(a["p15"],50))
P   # 2500260 2021-04-01 2025-12-31 23:59  0.005452
md5sum /home/ubuntu/wfo_ds_x1_2021/pred.bin            # 5dd6bb4c3f98d89d58770005c0001526 == manifest
md5sum /home/ubuntu/claudedata/wfo_gate_pred.csv       # b160a018b912ffdd61b6409d1208dad3 (== gate_push_ds/)
md5sum /home/ubuntu/claudedata/gate_ab_full/models/label_oldbasket/fold_20/*.onnx  # 4ac9a576… != wfo_models 8ec99757…
# scripts: /tmp/pbrepro/s1_identify.py s2_repro.py s3_gatedataset.py s4_pin.py s5_scan.py
#          s6_fresh.py s7*.py s8_foldscan.py s9_gen.py s10_storediff.py  (ket qua: /tmp/pbrepro/*.csv|json)
```
