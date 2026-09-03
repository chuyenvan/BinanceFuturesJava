# PREREG_G015REBUILD — tien dang ky: bien G015 thanh model TAI LAP DUOC, ghim provenance

Chot luc: 2026-09-04, **TRUOC khi train bat ky lan nao**. Commit nay phai co truoc moi commit ket
qua (kiem bang timestamp). Day la VIEC VE SINH, **KHONG** phai di tim cai thien.

Pham vi: **CHI DEV**. KHONG cham VALIDATION (2024-07-15..2025-12-31), KHONG cham HOLDOUT 2026.
Khong rebuild file OI. Moi output ra duong dan MOI, khong ghi de bat cu bins/ledger cu nao.

## 0. TAI SAO

`docs/G015CUT_RESULT.md` (commit 516e6eb) do duoc: bins G015 dang deploy
(`claudedata/predwf_G015x26/`) **KHONG tai lap duoc** — code sinh ra chung khong con, va ban export
Tool1 2021 dung luc do da bi xuat lai (16/08). Ban train lai tren CPU/GPU do duoc `rho = 0.18900`
(vs moc-cu-khong-tai-lap 0.16752), nam trong CI95 that cua moc. **Moc 0.1675 coi nhu da mat.**

Muc tieu Viec 1: tao mot baseline G015 **tai lap duoc byte-level (hoac gan byte)**, ghim day du
provenance (input + sha256 + lenh + moi truong), sinh bins deploy MOI ra duong dan moi, va dong bang
mot cau hinh chien luoc C3 tren DEV.

**Khung dien giai bat buoc (theo NBETS / `power_wall`):** tang equity KHONG do duoc cai thien 3pp
bang du lieu kha dung. Vi vay Viec 1 **KHONG** duoc phat bieu "G015 moi tot hon => he tot hon".
`rho` cao hon **khong** chuyen duoc thanh equity cao hon. Viec 1 tuyen bo **dung mot dieu**:
**he gio TAI LAP DUOC; he cu thi khong.** Moi so sanh equity chi dung cho rang buoc maxDD + sanity.

## 1. INPUT DUOC GHIM — sha256 chot cung

Bang sha256 day du 31 file: `inputs_sha.json` (commit CUNG commit nay). Toan bo tap input duoc ghim
boi **manifest digest**:

> `sha256(inputs_sha.json) = f14844f305c21777864bde2d5130623950853ee6557b56a86260e130b611cdc2`

Neu bat ky input nao doi 1 byte, digest doi => phat hien ngay. Cac hash then chot:

| nhom | file | sha256 | bytes |
|---|---|---|---|
| OI (SACH, KHONG rebuild) | `claudedata/oi/oi_percoin_full.bin` | `e3887f63097299655213f8382ca7e473e126ee4d7ddf69a39658942651b305ec` | 4,227,723,300 |
| symbol map | `claudedata/oi/symbol_map.csv` | `3f8175512f385d83619f85793e4f3edef4fcb9989d0e87c471976fbfcc104eaa` | 11,232 |
| pool cham diem | `g015/pool/pool_dev.parquet` | `713460fc926e1fc1a2a2664c70068c6ba966f81e9f913b36d8b5fb2827599262` | 131,401,565 |
| Tool1 (14 file DEV) | `ds_feat15m/features_2021..2024Q2.t1c.gz` | xem `inputs_sha.json` | — |
| label (14 file DEV) | `label_15m/funding_label_2021..2024Q2.pb` | xem `inputs_sha.json` | — |

Reader dung chung: `/home/ubuntu/sel1m_code/tool1_col.py` (T1C2) + `funding_label_pb.py`.

## 2. HYPERPARAMETER + FOLD — chot cung, KHONG doi

Y het recipe canonical (`docs/archive/.../wfo_train_data_recipe_and_golive_gap_2026-08-16.md`, va
`gen_funding_wf_predictions_1m.py`):
- Luoi 15m; label 1 chieu `y = (maxFav_4h >= 0.06)`, `nBars_4h >= 16`; **KHONG stop-loss**.
- WFO expanding, `OOS_MONTHS=3`, purge **72h wall-clock**, embargo 0, `TZ = +7h`.
- 10 fold DEV: cutoff `20220101, 20220401, 20220701, 20221001, 20230101, 20230401, 20230701,
  20231001, 20240101, 20240401` (loai >= 20240701 = VALIDATION).
- XGB: `n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
  min_child_weight=20, scale_pos_weight=(1-pos)/pos, eval_metric=auc, random_state=42`,
  `tree_method="hist"`, **device CPU** (`n_jobs=4` co dinh).
- 45 feature: 40 Tool1 (`f0..f39`) + 5 OI (`oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy`),
  ghep `merge_asof(on=ts, by=symId, backward, tol=2h)`.
- Bins ra dinh dang deploy: `>q h 4f` (26 B/rec), slot `p0` = 4h, 3 slot con lai NaN.

**Vi sao CPU chu khong GPU:** GPU (`device=cuda`) khong tai lap duoc theo bit (da do o Viec truoc;
XGBRanker/hist tren GPU dung sketch phu thuoc thu tu song song). CPU `hist` voi `nthread` co dinh la
duong deterministic. Baseline chinh thuc la con so **CPU**.

## 3. TIEU CHI "TAI LAP THANH CONG" — chot truoc

Chay **2 lan doc lap** (`run1`, `run2`), moi lan chay TRON pipeline (build feature tu input ghim +
train 10 fold + ghi bins), ra 2 thu muc rieng. THANH CONG khi:

1. **Chinh (nham toi):** bins **byte-identical** — `sha256(predict_wf_<c>.bin)` cua run1 == run2 o
   **ca 10 fold**. (CPU `hist` nthread co dinh ky vong dat dieu nay.)
2. **Du phong (neu khong byte-identical):** `spearman(pred_run1, pred_run2)` tren pool **>= 0.999999**
   VA `|rho_run1 - rho_run2| <= 1e-4` VA `p_mean` moi fold lech `<= 1e-5`. Ghi ro la "gan-byte,
   khong byte-identical" va nguyen nhan (FP reduction da luong).
3. **Sanity gia tri:** `rho(run1)` nam trong CI95 that cua moc (`[0.1260, 0.2005]` cua
   `LEAK_L1_REPORT §3.3`). Day KHONG phai pass/fail ve gia tri chinh xac — no chi chan sai pipeline.

**Neu (1) va (2) DEU truot => DUNG, bao "khong tai lap duoc", KHONG deploy.** Khong duoc thay mot
model khong tai lap duoc bang mot model khong tai lap duoc.

Bins chinh thuc = run1 -> `/home/ubuntu/predwf_G015_v2/`. run2 ra thu muc tam, so xong thi xoa.

## 4. HIEU CHUAN LAI GATE — python, 1 chieu, chot truoc

Train lai doi phan bo score => admit-rate doi (da do: full45 0.613% vs p_old 0.200% tren cand_dev3
voi cung `dyn_thr`). Bươc nay tim mot **he so tuyen tinh** tren `SIM_MIN_MOMENTUM_15M` (dyn_thr ty le
tuyen tinh voi no) sao cho admit-rate cua G015_v2 tren `cand_dev3` **quay ve dung diem van hanh cua
G015 deploy**.

- **Diem nham (chot truoc):** so dong admit = so admit cua **p_old (G015 deploy) tren cand_dev3** =
  **30,854 dong (0.200%)**, do bang cong thuc gate that (`research/analysis/gate_cfg.py`:
  `dyn_thr = SIM_MIN_MOMENTUM_15M * max(0.26787, score/0.15*1.28760)`, chi co can duoi;
  `score = 1 - p`; admit <=> `p15 >= dyn_thr`).
- **Dung sai:** `|n_admit(G015_v2) - 30,854| <= 5%` (bisection tren he so).
- Ket qua = `SIM_MIN_MOMENTUM_15M_moi = 0.008 * c`. Bao cao `c`, admit-rate truoc/sau, va chat luong
  hang admit (`mean g1lite`) truoc/sau.
- **Lam ro (giai thich, khong doi tieu chi):** con so "top-8 ~0.51% DEV" ma dieu phoi neu la admit-rate
  do o **tang java** cua C2b (selector THAT cua C2b la S1 `predwf_map_s1a2`, KHONG phai G015 — xem §7).
  Python khong tai lap duoc 0.51% do vi khong co score S1 trong `cand_dev3`. Diem nham 0.200% la
  diem van hanh cua chinh dong ho G015 (p_old), la moc like-for-like duy nhat do duoc bang python.
  Admit-rate/so lenh THAT cua C3 se do o tang java (§5) va bao cao nguyen trang.

## 5. DONG BANG C3 TREN DEV — tieu chi chot truoc

- `profiles/c3.properties` = ban sao `c2b_min.properties`, **chi doi 2 thu**:
  `WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_G015_v2` va `SIM_MIN_MOMENTUM_15M` (gia tri hieu chuan §4).
  Moi tham so exit/sizing/funding giu Y NGUYEN c2b.
- Chay **1 run java tren DEV** (slot java ranh, da kiem `pgrep java` rong). Tan dung `market.bin`
  + `pred.bin` (GATE, selector-doc-lap) tu dataset da co; chi rebuild lop `funding.bin` tu bins
  G015_v2 (qua `ExportWfoDataset` voi `WFO_FUNDING_PRED_DIR` moi). Cham bang `qret.py`.
- **Tieu chi (chot truoc, chi kiem 2 dieu — KHONG phai "hon C2b"):**
  1. **maxDD C3 >= -15.12%** (rang buoc cung). `<-15.12%` => C3 KHONG dong bang duoc, ghi ro.
  2. **Sanity:** run hoan tat, khong NaN/khong sup/khong chay; equity duong o cuoi; bao cao
     so quy duong + underwater.
- **Cam:** neu CAGR(C3) khac C2b thi ghi kem "khac biet nam trong nhieu tang equity (NBETS,
  `power_wall`), KHONG phai bang chung hon/kem". Chi maxDD + sanity duoc dung de quyet dinh dong bang.

## 6. THU TU + GIOI HAN

1. Commit file nay + `inputs_sha.json`. Ghi commit hash.
2. Chay `run1`, `run2`, so (§3). Truot => dung.
3. Sinh `predwf_G015_v2` = run1; `G015_PROVENANCE.md` + manifest sha canh bins.
4. Hieu chuan gate (§4).
5. Dong bang C3 (§5). Kiem `df -h /` truoc; `wfo_ds_*` xoa ngay sau run; xuong duoi 6G thi DUNG + don.
6. Backup bins len Kaggle dataset PRIVATE. Ghi `docs/G015REBUILD_RESULT.md`. Cap nhat project memory.

Giói hạn cứng: chi DEV; KHONG ghi de `predwf_map_s1a2/`, `ledger/pred_s1a2.parquet`,
`featv2/feat_v2.parquet`, hay bins G015 deploy cu; KHONG rebuild OI; KHONG cham live/shadow (242
read-only); KHONG submit kernel Kaggle train (GPU cam cho rankIC — backup dataset thi duoc);
khong cham `/home/ubuntu/{gs,fs,tick,nbets}/`; khong de JVM zombie; Java SLF4J, Python logging.

## 7. GIA DINH CUA DIEU PHOI CO THE SAI — ghi truoc de khong troi

- **"G015 cap score cho GATE cua C2b".** C2b THAT (`profiles/c2b_min.properties`,
  `java/dev_c2.sh`) dat `WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2` = **S1**, khong phai G015.
  Gate `AIRejectFilter` dung score cua selector dang nap = **S1**. Vai tro "G015 cap score cho gate"
  chi ton tai o tang PHAN TICH ledger (`ledger3.py` dung `p_g015`), khong phai o C2b java dang chay.
  => C3 (thay `WFO_FUNDING_PRED_DIR` = G015_v2) bien G015_v2 thanh selector THAT cho ca rank lan gate.
  C3 vi vay la "C2b nhung doi selector S1 -> G015_v2", mot cau hinh KHAC C2b o tang selector, khong
  phai "C2b tai lap". Se bao cao dung nhu vay.
- **"admit-rate top-8 ~0.51% DEV".** Do o tang java (S1 selector + top-K), khong tai lap duoc bang
  python tren cand_dev3. Xem §4.
