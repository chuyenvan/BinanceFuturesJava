# PREREG_T1 — 3 chan C2b hien tai vs "maxfav6" 4h vs "maxfav6" 72h, DI HET TOI SIM

Chot 2026-09-05, **TRUOC khi train bien the nao va truoc khi nhin bat ky so nao**.
Commit nay phai co truoc `docs/T1_LABEL3.md`. CHI DEV (2022-01..2024-06). Khong cham
VALIDATION/HOLDOUT. Khong rebuild OI. Output ra duong MOI.

## 0. Vi sao co job nay

`docs/LABELH_RESULT.md` da so 3 nhan selector nhung **DUNG o rank-IC** — khong sinh bins,
khong chay java, nen chua tra loi duoc "doi nhan co doi KET QUA GIAO DICH khong".
User yeu cau di het luong: **train S1 -> build_map -> sim -> equity + rate**.

Khac biet dinh nghia phai ghi ro TRUOC:
- `LABELH` dung `L4_maxfav` = **ngu phan vi trong tick** cua `maxFav_4h - median_tick`.
- User goi chan nay la **"maxfav6"** = **nhi phan `maxFav_4h >= 0.06`** (dung nghia den ten goi,
  va dung nhan ma **G015x26** dang dung — `AGENT_RUNBOOK §3`).
=> **Hai dinh nghia KHAC NHAU.** Vi vay job nay chay **CA HAI**: ban nhi phan (cau hoi cua user)
va ban ngu phan vi (de noi duoc voi so cu cua `LABELH`). Tong **4 chan**.

## 1. BON CHAN — chot cung, chi khac NHAN

Moi thu con lai **y nguyen** `research/pipeline/s1_rank.py`: 9 feature `KEEP`,
`XGBRanker objective=rank:ndcg n_estimators=300 max_depth=4 lr=0.05 subsample=0.8
colsample_bytree=0.8 min_child_weight=50 n_jobs=4 tree_method=hist random_state=42
lambdarank_pair_method=topk lambdarank_num_pair_per_sample=8`, group = tick,
10 fold cutoff `20220101..20240401`, OOS 3 thang, **purge 72h**, `assert tr.ts.max() < cutoff`,
**KHONG dropna feature** (merge LEFT, de XGBoost tu xu ly NaN — `LABELH SUA DOI 1`).

| ma | relevance | ghi chu |
|---|---|---|
| **`L_g1`** | `rel5` = ngu phan vi trong tick cua `g1lite - median_tick` | = **S1 dang chay**. Cong tai lap + chan parity |
| `L_f4` | **`1{maxFav_4h >= 0.06}`** | "maxfav6" 4h — **cau hoi chinh cua user** |
| `L_f4q` | `rel5` cua `maxFav_4h` | = `L4_maxfav` cua `LABELH` — chi de noi voi so cu |
| `L_f72` | **`1{maxFav_72h >= 0.06}`** | "maxfav6" 72h |

`maxFav_4h` join tu `/home/ubuntu/label_15m/funding_label_202[1-4]*.pb`
(`usecols=[tEpochMs,symbol,maxFav_4h,nBars_4h]`, loc `nBars_4h >= 16`, map symbol->symId qua
`/home/ubuntu/selector_pred_out/symbol_map.csv`) — y het duong join cua
`research/analysis/labelh2.py`. `maxFav_72h` da co san trong `ledger/cand_dev.parquet`.
**Pool ghep cap = pool goc**: `LABELH` da do 1,220,490 dong / 8,642 tick, join khong mat dong.
Neu lan nay join lam MAT dong thi phai bao so mat va coi la ghep cap khong sach.

## 2. CONG REPRO — chan tren, bat buoc, chay TRUOC

Train `L_g1` bang chinh pipeline cua job nay tren **pool goc**, roi
`spearman(score_moi, ledger/pred_s1a2.parquet.score)` tren cac dong chung phai
= **1.000000** (`docs/FS_RESULT.md` + `LABELH PHA A` da dat dung tri nay tren 774,270 dong).
**Truot => DUNG JOB, khong bao cao chan nao, khong submit sim nao.**

## 3. PIPELINE moi chan (ngoai `L_g1`)

1. `s1_rank.py` bien the -> `/home/ubuntu/ledger/pred_t1_<ma>.parquet` (ts,sym,score thap=tot).
2. `research/pipeline/build_map.py` voi nguon gia tri = **G015x26**
   (`/home/ubuntu/claudedata/predwf_G015x26/predict_wf_*.bin`) -> bins moi
   `/home/ubuntu/predwf_t1_<ma>/` — y het cach sinh `predwf_map_s1a2`
   (`research/pipeline/BINS_MANIFEST.md`). Gate giu NGUYEN multiset P(win) trong tung tick.
3. Profile copy tu `profiles/c2b_min.properties`, **chi doi `WFO_FUNDING_PRED_DIR`**
   -> `profiles/t1_<ma>.properties`.
4. `tools.kaggle_sim.submit` (Kaggle CPU, `TICKER_SOURCE=file`), `ks.free_slots()` truoc khi day.

`L_g1` KHONG sinh bins moi: dung thang `predwf_map_s1a2` da co => chan nay la **parity**.

### 3b. HAI SAI LECH SO VOI CHI DAN, khai bao TRUOC khi chay
1. **Bins moi di trong 3 dataset Kaggle RIENG** (`chuyendinh/bins-t1-f4`, `bins-t1-f4q`,
   `bins-t1-f72`), **khong** `dataset_create_version` vao `sim-c2b-bundle`. Ly do: bundle la
   layout PHANG, ba bo bins moi trung TEN file `predict_wf_*.bin` voi bins parity; doi ten thi
   `WfoDataset.readWfPredDir` (`name.startsWith("predict_wf_")`) khong con thay. Tach dataset
   giu `sim-c2b-bundle` **khong doi mot byte** => neo parity 60395 khong bi dong toi,
   va chi upload 3x386MB thay vi upload lai 3.5GB.
2. **`tools/kaggle_sim.py` them tham so `bins_ds`** (mac dinh `None` = hanh vi CU y nguyen):
   khi co, kernel them dataset do vao `dataset_sources` va lay `WFO_FUNDING_PRED_DIR` tu
   **dung** mount do (`/kaggle/input/<slug>/`). Chan parity chay duong mac dinh, khong qua
   nhanh moi.

## 4. NEO PARITY

`TICKER_SOURCE=file` => neo **60395** / **970 lenh** / md5 `printDone.csv`
`910f1aa6f76b5e6797d97a31a7ea5f5a` (`docs/KAGGLE_SIM.md §1`).
Chan `L_g1` phai trung ca ba. **Truot => bao va DUNG**, khong doc rate cua chan nao.

## 5. EQUITY KHONG PHAI TIEU CHI

N = **4** run => `E[max nhieu]` CAGR = `2.57 * sqrt(2 ln 4)` = **4.3pp**.
Equity/CAGR bao cao trong **muc rieng**, dan nhan **"khong phai tieu chi"**.

## 6. TIEU CHI PRIMARY = RATE (chot truoc khi thay so)

Tu `printDone.csv`, dung `research/analysis/w1_rates.py`:

| rate | y nghia |
|---|---|
| `TSloss%` | ti le lenh thoat bang `STOP_LOSS_DONE` (= time-stop 168h) |
| `win%` | ti le `profit > 0` |
| `mean(profit \| STOP_MARKET_DONE)` | chat luong nhanh chot lai |
| `mean(profit \| STOP_LOSS_DONE)` | do sau kenh mat tien lon nhat |

Kem **rank-IC / edge5 OOS** cua tung S1 variant (do bang chinh harness `s1_rank.py`),
CI **block-bootstrap khoi 72h** (kem 24h/168h do ben), **ghep cap** (cung danh sach khoi cho
moi chan), 2000 rep, seed **20260905**, percentile 2.5/97.5 **CUA HIEU**, nhan he so duoi phu
**f = 1.21** (`docs/COV_RESULT.md`).

🔴 **KHONG CO TIEU CHI TRUNG LAP VE CHAN TROI** — ghi lai nguyen van canh bao cua `PREREG_LABELH §3`.
Bao cao rank-IC vs **ca ba** outcome va dan nhan thien vi cua tung cai:

| outcome | thien vi chan |
|---|---|
| `g1lite` (72h) | `L_g1` |
| `maxFav_4h` | `L_f4`, `L_f4q` |
| `maxFav_72h` | `L_f72` |

Cam tuyen bo "nhan X tot hon" chi vi X thang tren outcome cung ho voi X.

## 7. RANG BUOC CUNG

`maxDD <= 15%`, underwater `<= 120` ngay, **khong nam am**, **khong quy < -5%**.
Chan vi pham => LOAI, khong xet tiep du rate co dep.

## 8. QUY TAC QUYET DINH — chot truoc khi thay so

Mot chan duoc coi la **KHAC C2b** khi **it nhat 2 trong 4 rate PRIMARY lech CUNG HUONG
va NAM NGOAI CI** (CI cua rate lay bang bootstrap khoi 72h tren tap lenh, ghep cap theo tick,
f=1.21). Khong dat => **"KHONG PHAN BIET DUOC"** — day la cau tra loi hop le va phai noi thang.
**KHONG duoc viet "hon mot chut" / "nhinh hon" / "co ve tot hon".**

## 9. CAM

Khong VAL. Khong push. **Khong GPU cho train** (CPU byte-identical giua Kaggle va Oracle;
GPU tu no nhieu gap 4.8 lan — `docs/BENCH_DEVICE.md`). Khong xoa file cua user.
Khong ghi de `predwf_map_s1a2/`, `ledger/pred_s1a2.parquet`, `featv2/feat_v2.parquet`,
`claudedata/predwf_G015x26/`, `sim-c2b-bundle`. Khong doi pre-reg sau khi thay so.
Python dung `logging`. Kiem `ks.free_slots()` truoc moi lan submit.

## 10. THU TU

1. Commit file nay. 2. Cong REPRO §2 — truot thi dung.
3. Train 4 chan tren pool ghep cap, ghi per-tick IC + edge5.
4. Bootstrap §6. 5. build_map 3 chan moi + profile. 6. Upload 3 dataset bins.
7. `free_slots` roi submit 4 sim. 8. Parity §4 — truot thi dung.
9. Rate §6 + rang buoc §7 + phan quyet §8. 10. `docs/T1_LABEL3.md` + `docs/QUEUE.md` + commit.
