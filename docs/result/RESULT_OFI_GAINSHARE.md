# RESULT_OFI_GAINSHARE — gain-share 2 cot OFI trong `candidate` (DONG SO OFI)

Theo `docs/prereg/PREREG_OFI_GAINSHARE.md` (commit `f08da90`, chot TRUOC khi push kernel va truoc khi
doc bat ky so gain nao).

**Verdict vong do:** **KHONG AP DAO** (nguong chot truoc KHONG DAT) — gia thuyet "2 cot OFI ap dao cay"
bi **BAC BO**.

## 0. Cach do (khong train lai harness, khong doi model/fold)

- **VIEC 1 (artifact co san?) = KHONG.** Kiem bang so: `chuyendinh/ofi-v3-ms-s43` (va s42/s44/s45) va
  `chuyendinh/ofi-v3-train-eval` chi xuat `*_result*.json` + `pred_*.parquet`; `ofi_train_eval_v3*.py`
  **khong** goi `save_model`/`get_score`/`feature_importances_`. ⇒ khong co gain san, phai tinh.
- **VIEC 2 (push kernel) = CO.** Kernel **`chuyendinh/ofi-v3-gainshare-s43`** (CPU, `enable_gpu=false`,
  `enable_internet=false`), code **CO HOC tu `ofi_train_eval_v3_ms.py`** (seed 43): **GIU NGUYEN**
  du lieu/join/NaN-mask/`make_model`/purge 72h/`CUTS18`/`assert` leak.
  - **Push 26/09 09:15:33 UTC · COMPLETE ~11:02 UTC · runtime 6.098 s (~1 h 41 m 40 s).**
  - Them DUY NHAT: `m.get_score('gain'|'weight'|'cover')` tren **chinh model da fit** ⇒ gain/weight/cover
    **theo TUNG fold** cho `candidate` (KEEP9 + `ofi_1h` + `aggr_buy_ratio_1h`, 11 cot) va
    `baseline_fresh` (KEEP9, 9 cot); + **permutation importance tren OOS** (hoan vi TRONG TUNG tick,
    5 lan/fold, RNG co dinh 20260920, **khong refit**) cho 2 cot OFI.
  - Output nho: `docs/result/ofi_gainshare.json` (33 KB) + `docs/result/ofi_gainshare_perfold.parquet`.
- **Kiem hop le (bat buoc):** chay lai **dung** harness seed 43 ⇒ **tai lap BYTE-MUC so da cong bo**:
  18/18 fold × 2 bien the, `max|dev|` cua edge5 so voi log `chuyendinh/ofi-v3-ms-s43` =
  **0,0005 pp** (dung bang nguong lam tron 3 chu so cua log) ⇒ cung moi truong, so dang tin.
  Coverage OFI 0,9512 (630 sym, 9.730.284 dong) — khop vong goc.

## 1. KET QUA — gain share (% gain, chuan hoa theo tung fold, TB ± sd qua 18 fold)

| # | Feature | gain share TB ± sd | hang | weight TB | cover TB | top3/18 |
|---|---|---|---|---|---|---|
| — | **`ofi_1h`** | **5,37 ± 1,86** | **7/11** | 147,2 | 6.509,8 | **0** |
| — | **`aggr_buy_ratio_1h`** | **4,53 ± 1,58** | **8/11** | 49,7 | 7.291,2 | **0** |
| — | **2 cot OFI HOP** | **9,89 ± 3,37** (min 0,00 · max 16,13) | — | — | — | — |
| 1 | `ret_14d` (candidate) | 19,35 ± 3,09 | 1/11 | 653,5 | 12.107,7 | — |
| 2 | `rk_dd_7d` | 19,04 ± 2,43 | 2/11 | 452,3 | 10.068,0 | — |
| 3 | `rk_ret_3d` | 16,25 ± 4,55 | 3/11 | 358,9 | 7.441,1 | — |
| 1' | **`rk_ret_3d` (baseline_fresh)** | **22,31 ± 6,51** | **1/9** | 366,9 | 7.067,5 | — |
| 2' | `rk_dd_7d` (baseline) | 20,15 ± 2,41 | 2/9 | 458,9 | 9.392,9 | — |
| 3' | `ret_14d` (baseline) | 16,95 ± 4,05 | 3/9 | 705,1 | 11.695,2 | — |
| moc | **`rvol15m`** (lich su, `EVAL_SELECTOR_FEATURES.md:110`, feature set 45 cot KHAC) | **34,09** | 1/45 | 238,0 | — | 18/18 |

- Doi chieu "feature hang 1 cua baseline": `g1_base` = **22,31%** (feature co gain share TB cao nhat,
  `rk_ret_3d`); neu doc theo "per-fold top-1" thi TB = **25,67 ± 4,15%**. Ca hai cach doc deu cho
  ket qua nhu nhau o muc 3.
- `candidate` hang 1 = `ret_14d` 19,35% (per-fold top-1 TB 22,10 ± 2,13%) — **doi hang so voi baseline**
  (baseline hang 1 la `rk_ret_3d`). 2 cot OFI **khong** phai cot "tru".
- **`cover`/`weight` khong cuu duoc ket luan:** OFI dung it hon nhieu (weight 147,2 / 49,7 so voi
  653,5 cua `ret_14d`); cover cung thap hon cot hang 1.
- **Bang theo TUNG fold** (2 cot OFI + permutation; `d_edge5` am = pha cot lam edge5 OOS **TUT** ⇒ cot
  CO gia tri OOS):

| fold | cutoff | `ofi_1h` % | `aggr` % | hop % | top1 candidate (%) | top1 baseline (%) | d_edge5 `ofi_1h` | d_edge5 `aggr` |
|---|---|---|---|---|---|---|---|---|
| 0 | 20210701 | 0,00 | 0,00 | 0,00 | ret_14d (23,17) | rk_dd_7d (21,44) | +0,000 | +0,000 |
| 1 | 20211001 | 8,45 | 7,68 | 16,13 | ret_14d (21,50) | ret_14d (23,08) | +0,004 | +0,065 |
| 2 | 20220101 | 8,17 | 6,07 | 14,24 | ret_14d (22,40) | ret_14d (23,79) | −0,067 | +0,011 |
| 3 | 20220401 | 7,55 | 6,18 | 13,73 | ret_14d (21,44) | rk_dd_7d (21,28) | −0,027 | +0,022 |
| 4 | 20220701 | 5,74 | 5,62 | 11,35 | ret_14d (22,20) | rk_dd_7d (22,65) | +0,002 | −0,017 |
| 5 | 20221001 | 6,06 | 4,57 | 10,63 | ret_14d (22,84) | rk_dd_7d (21,48) | +0,039 | +0,046 |
| 6 | 20230101 | 5,55 | 3,87 | 9,42 | rk_dd_7d (21,29) | rk_dd_7d (20,71) | −0,068 | −0,150 |
| 7 | 20230401 | 6,65 | 5,16 | 11,81 | rk_dd_7d (20,02) | rk_ret_3d (27,56) | −0,197 | −0,235 |
| 8 | 20230701 | 5,04 | 5,35 | 10,40 | rk_dd_7d (20,38) | rk_ret_3d (25,54) | −0,053 | −0,029 |
| 9 | 20231001 | 5,75 | 4,50 | 10,26 | ret_14d (21,15) | rk_ret_3d (23,82) | −0,266 | −0,431 |
| 10 | 20240101 | 5,57 | 4,70 | 10,26 | rk_dd_7d (20,40) | rk_ret_3d (27,30) | +0,170 | +0,128 |
| 11 | 20240401 | 4,94 | 3,65 | 8,59 | ret_14d (19,13) | rk_ret_3d (26,96) | −0,168 | −0,028 |
| 12 | 20240701 | 4,35 | 3,80 | 8,15 | ret_14d (20,68) | rk_ret_3d (25,94) | −0,146 | −0,080 |
| 13 | 20241001 | 5,01 | 4,87 | 9,88 | rk_ret_3d (21,49) | rk_ret_3d (33,96) | −0,795 | +0,165 |
| 14 | 20250101 | 4,89 | 3,75 | 8,64 | rk_ret_3d (23,69) | rk_ret_3d (32,38) | −0,236 | −0,070 |
| 15 | 20250401 | 4,64 | 3,51 | 8,15 | rk_ret_3d (24,82) | rk_ret_3d (24,98) | −0,284 | −0,001 |
| 16 | 20250701 | 4,39 | 3,48 | 7,88 | vol_7d (22,70) | vol_7d (25,32) | −0,401 | −0,418 |
| 17 | 20251001 | 3,83 | 4,70 | 8,53 | vol_7d (28,54) | vol_7d (33,91) | −1,172 | −1,129 |
| **TB** | | **5,37** | **4,53** | **9,89** | **22,10** | **25,67** | **−0,204** | **−0,120** |
| **sd** | | 1,86 | 1,58 | 3,37 | 2,13 | 4,15 | 0,322 | 0,299 |

- Fold 0 (2021) OFI **khong duoc dung** (share 0,00) — dung voi coverage OFI nam 2021 chi 25,2%.

## 2. NGUONG "AP DAO" (chot truoc) — **KHONG DAT**

| Tieu chi (chot truoc, §3 prereg) | Nguong | Thuc do | Ket qua |
|---|---|---|---|
| `max(gain share 2 cot OFI) >= 30,0%` (neo `rvol15m` 34,09%) | ≥ 30,0% | **5,37%** | **KHONG** |
| `max(gain share 2 cot OFI) >= 3 x g1_base` | ≥ 66,94% (3×22,31) | **5,37%** | **KHONG** |
| (doc lap) `>= 3 x` per-fold top-1 baseline | ≥ 77,02% (3×25,67) | **5,37%** | **KHONG** |
| mo ta: 2 cot OFI vao top-3 | — | **0/18 fold** | — |

## 3. TRA LOI (1)(2)(3)

**(1) 2 cot OFI co "ap dao cay" khong? — KHONG.**
Gain share TB: `ofi_1h` **5,37% ± 1,86** (hang **7/11**), `aggr_buy_ratio_1h` **4,53% ± 1,58**
(hang **8/11**); hop 2 cot **9,89% ± 3,37**. Khong fold nao (0/18) 2 cot OFI vao top-3; ca hai deu
**thap hon nhieu** cot hang 1 cua chinh `candidate` (`ret_14d` 19,35%) va cua `baseline_fresh`
(`rk_ret_3d` 22,31%). So voi moc **`rvol15m` 34,09%** (feature hang 1 chiem 1/3 gain, gap 4,8x hang 2):
hai cot OFI **khong** o cung dang — chung chi ~10% gain, **kem ca `vol_7d` (10,53%)**.

**(2) Co phai "co che chia nhanh in-sample" thuan? — KHONG hanh xu nhu vay, nhung cung KHONG phai alpha.**
Vi nguong (1) **khong dat**, luan diem "co che chia nhanh in-sample" (C1) **khong kich hoat**. Kiem
cheo **permutation tren OOS** (khong refit): pha `ofi_1h` lam edge5 OOS **tut** trung binh
**−0,204 pp ± 0,322** (13/18 fold am); pha `aggr_buy_ratio_1h` **−0,120 pp ± 0,299** (11/18 fold am)
⇒ 2 cot OFI **co** dong gop nho nhung **co that** tren OOS (tong ~**+0,32 pp edge5**), khong phai
thuan co che in-sample. Muc dong gop nay **nho** so voi hieu ung tang selector (+1,76 pp pooled) —
nhat quan voi "tin hieu tang selector THUC NHUNG NHO", khong phai "feature troi".
⚠ Dan chieu `rvol15m`: 34,09% gain nhung **KHONG** co so OOS tuong ung o day ⇒ moc lich su chi de
dat canh; **khong** dung de suy ra OFI "cung bay" — so do **khong** ung ho dieu do.

**(3) Ket luan dong so OFI — dung 2/3 ve, SAI 1 ve.**
- ✅ "tang selector (+1,76 pp)": **dung** (`34d50c7`, khong do lai).
- ✅ "khong ra tien": **dung** (`docs/result/RESULT_OFI_MONEY.md`, `96a08e5`).
- ❌ "**co dau hieu feature ap dao cay**": **SAI** — gain share 2 cot OFI **5,37% + 4,53%** (hang 7-8/11,
  **0/18 fold top-3**), cach xa nguong 30% / 3×baseline (66,94%). `candidate` hang 1 van la
  `ret_14d` 19,35%; 2 cot OFI dung it hon `vol_7d`. ⇒ **Khong co bang chung** rang viec `candidate`
  xep hang sang **universe MAJOR** la do **mot cot OFI ap dao**; neu co dich chuyen thi no den tu
  **tai phan bo lai trong 9 cot KEEP9** (hang 1 doi tu `rk_ret_3d` 22,31% sang `ret_14d` 19,35%),
  khong phai tu 2 cot OFI. Khong over-claim: day la **mo ta phan bo gain**, khong phai bang chung
  nhan qua ve co che xep hang major.

## 4. Muc bo / gioi han

- Chi **1 seed (43)** cho phan gain/permutation (multi-seed da co o `34d50c7` cho hieu ung edge5);
  gain share la dai luong **in-sample cua tung fold**, khong phai uoc luong hieu ung nhan qua.
- `rvol15m` la feature cua **feature set 45 cot KHAC** (S1) ⇒ chi so sanh **dat canh**, khong dong nhat.
- Khong do lai phan "hang universe major" (da co B1 o `96a08e5`: 100% top-K nam ngoai P32) — vong nay
  chi do **gain share** va **permutation OOS**; cau (3) phan major chi la **doi chieu lai**, khong do moi.
- Khong chay Java/sim, khong claude-run, khong push git. Kernel moi: `chuyendinh/ofi-v3-gainshare-s43`.

## 5. Artefact

- `docs/result/ofi_gainshare.json` (sha256 `f3db2578141cf954…`) — per-fold gain/weight/cover (2 bien the)
  + mean/sd/min/max + rank + permutation theo fold.
- `docs/result/ofi_gainshare_perfold.parquet` (sha256 `383e8d2901e5fcfd…`) — ban phang per-fold (36 dong).
- Kernel: `chuyendinh/ofi-v3-gainshare-s43` (COMPLETE, runtime ~1 h 41 m 40 s CPU).
