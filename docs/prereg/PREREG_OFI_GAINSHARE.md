# PREREG_OFI_GAINSHARE — do gain-share 2 cot OFI trong `candidate` (dong so OFI)

Chot **TRUOC khi push kernel** va **TRUOC khi doc bat ky so gain/importance nao**. File nay PHAI duoc
commit truoc `docs/result/RESULT_OFI_GAINSHARE.md`; nguoc lai ket qua VO HIEU.

Ke thua (dung tin, KHONG do lai): `docs/RESULT_S1_FREE_OFI_V3_UNIVERSE.md` (`c5c9faf`),
multi-seed `34d50c7` (Δedge5 pooled +1,76pp*, noise NULL 4/4 seed), `docs/result/RESULT_OFI_MONEY.md`
(`96a08e5`: tang tien = 0).

## 0. Cau hoi va muc dich (day la vong DONG SO, khong phai vong cuu)

`candidate` = KEEP9 + `ofi_1h` + `aggr_buy_ratio_1h` xep hang sang **universe MAJOR**
(top-8 = BNB/1000SHIB/XTZ/DOT/SFP/XRP/1INCH/ADA), trong khi S1 (45 cot) KHONG chon major.
Gia thuyet: 2 cot OFI **AP DAO cay** (split in-sample), giong dang bay **gain-share** da gap voi
`rvol15m` (**34,09%** gain, `docs/analysis/EVAL_SELECTOR_FEATURES.md:110`, gap 4,8x feature hang 2).

Muc dich: **do cho ro** de dong so OFI — KHONG phai tim cach cuu.

## 1. VIEC 1 — artifact co san? KET QUA: **KHONG**

Da kiem bang so (khong doan):
- `chuyendinh/ofi-v3-ms-s43` (va s42/s44/s45): output CHI co `ofi_result_v3_ms_s43.json`,
  `ms_diffs_s43.parquet`, `pred_baseline_fresh.parquet`, `pred_ofi_candidate_v2.parquet`,
  `pred_ofi_noise_v2.parquet`. **Khong** co model `.json`, **khong** co gain/importance.
- `chuyendinh/ofi-v3-train-eval`: tuong tu (result json + 3 pred parquet).
- `ofi_train_eval_v3.py` / `ofi_train_eval_v3_ms.py`: **khong** goi `save_model`, `get_score`,
  `feature_importances_`, va **khong** ghi model ra dia.

⇒ **Khong co artifact gain san ⇒ buoc sang VIEC 2 (push kernel tinh).** (Ghi chu: JSON model cua
XGBoost cung KHONG luu `gain`; neu co model thi van phai `Booster.get_score(...)` — o day con khong
co model.)

## 2. VIEC 2 — kernel do gain-share (CPU, output NHO)

Kernel moi: **`chuyendinh/ofi-v3-gainshare-s43`** (`enable_gpu=false`, `enable_internet=false`).

`kernel_sources` + `dataset_sources`: **Y HET** `chuyendinh/ofi-v3-ms-s43` (10 build shard + dataset
`chuyendinh/s1-featv2-x1-20260919` + frozen baseline `chuyendinh/s1-baseline18-det-n1-20260919`).
**KHONG** build lai feature, **KHONG** tai aggTrades ve Oracle, **KHONG** chay Java/sim.

Code = **CO HOC tu `ofi_train_eval_v3_ms.py`** (seed 43). **GIU NGUYEN tuyet doi**:
du lieu/join/NaN-mask, `make_model` (rank:ndcg, 300 cay, depth 4, lr 0,05, sub/col 0,8, mcw 50,
`n_jobs=1`, `hist`, topk/8), `rel5`, purge 72h, `CUTS18`, `assert tr.ts.max() < c`,
`MS_SEED=43`, `SEED=20260919`, noise RNG `20260920`. Chi **BO** phan CI/noise-control (khong dung
o vong nay) va **THEM** phan do importance — **khong** doi bat ky tham so model/fold nao.

**Doi DUY NHAT (additive, khong cham so cu):**
1. Sau moi `m.fit(...)`, goi `m.get_score(importance_type='gain')`, `'weight'`, `'cover'`
   tren **cung model da fit** => gain/weight/cover **theo TUNG fold (18 fold)** cho:
   - `candidate` (`KEEP9 + ofi_1h + aggr_buy_ratio_1h`, 11 cot),
   - `baseline_fresh` (KEEP9, 9 cot).
   Chuan hoa **share% theo tung fold** (moi fold cong dung 100%).
2. **Permutation importance tren OOS** (chi cho `candidate`, de tranh ket luan chi tu gain in-sample):
   voi moi fold, giu nguyen model, (a) predict OOS nhu thuong => `edge5_true`; (b) `ofi_1h` hoan vi
   ngau nhien trong OOS (RNG co dinh `20260920`, **5 lan lap/fold**) => `edge5_perm`; (c) tuong tu cho
   `aggr_buy_ratio_1h`. Bao `delta_edge5 = mean(edge5_perm) - edge5_true` (don vi: diem %).
   **KHONG refit** (giu dung phan phoi OOS, chi pha thong tin 1 cot).

Output (moi file **< 50 KB**):
- `ofi_gainshare_s43.json`: per-fold gain/weight/cover (3 chi so x 2 bien the) + mean/sd + rank,
  + bang permutation theo fold.
- `ofi_gainshare_perfold.parquet` (phang, vai chuc dong) neu can ve.

## 3. NGUONG "AP DAO" — chot TRUOC, dinh luong

Goi `g(f)` = gain share TB qua 18 fold cua feature `f` trong `candidate`;
`g1_base` = gain share TB cua feature hang 1 (theo gain) trong `baseline_fresh`.

**DAT "AP DAO"** khi VA CHI khi:
- `max(g(ofi_1h), g(aggr_buy_ratio_1h)) >= 30,0%` (neo `rvol15m` 34,09%), **HOAC**
- `max(g(ofi_1h), g(aggr_buy_ratio_1h)) >= 3 x g1_base` (ap dao tuong doi so voi baseline).

**KHONG DAT** neu ca hai deu khong thoa.

Bao kem (mo ta, khong phai tieu chi): hang cua `ofi_1h`/`aggr_buy_ratio_1h` theo gain; so fold 2 cot
OFI nam top-3; `g1_base` va hạng 1 cua baseline (de dat canh 34,09% cua `rvol15m`); doi chieu nhanh
`weight`/`cover` (neu `cover` cua OFI lon nhung `gain` nho => khong ap dao).

## 4. LUAT KET LUAN (chot TRUOC)

- `C1` (gain in-sample): neu §3 DAT => ghi ro day la **CO CHE chia nhanh in-sample**, **KHONG** phai
  alpha; dan chieu `rvol15m` 34,09% lam moc lich su cua cung dang bay.
- `C2` (permutation OOS): neu `delta_edge5` cua 2 cot OFI **nho** (<= 0,5 lan bien do nhieu giua fold,
  va khong doi dau he thong lon hon 0,5x) trong khi gain in-sample lon => **xac nhan** ket luan co che
  (khong co gia tri OOS tuong ung). Neu **nguoc lai** (OOS giam manh) => gain in-sample **co** tuong ung
  gia tri OOS, phai bao rieng va KHONG duoc ket luan "chi la co che".
- `C3` (dong so OFI): ket luan cuoi = co dung "tang selector (+1,76pp), khong ra tien, VA co/khong dau
  hieu feature ap dao cay" hay khong — noi ro DAT/KHONG o (1), co che o (2), va (3).
- Neu kernel **FAIL/khong ra so** => **KHONG** cong bo verdict, bao MASTER. Khong suy dien tu gain cua
  model S1 45 cot (do la feature set KHAC).

## 5. Rang buoc

Khong `claude-run`; khong Java/sim tren Oracle; khong push git (commit SOM, KHONG push);
`df -h /` dung 93% nen output tool giu **THAT NHO**; uoc tinh kernel ~1,5-2 h (36 lan fit, khong GPU).
