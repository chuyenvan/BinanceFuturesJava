# G015_PROVENANCE — bins predwf_G015_v2 (baseline G015 TAI LAP DUOC)

Sinh luc: 2026-09-04 (Oracle, CPU). Tuan theo `docs/PREREG_G015REBUILD.md` (commit 0449f21).
Day la baseline G015 chinh thuc MOI, thay cho bins deploy cu `claudedata/predwf_G015x26/`
(**khong tai lap duoc** — xem `docs/G015CUT_RESULT.md`). Bins cu KHONG bi xoa/ghi de.

## 0. Ket qua tai lap — byte-identical

Chay 2 lan doc lap (build feature tu input ghim + train 10 fold + ghi bins), 2 thu muc rieng:

| | run1 | run2 |
|---|---|---|
| sha256(xall.f32) (ma tran feature) | `7ab478f6859a3284eaf6fc66b70904afdd216703a9476ac05612127e9d6c50e9` | **giong** |
| rho (pool cand_dev3, 15,442,092 dong) | 0.189910 | 0.189910 (|d|=0) |
| bins 10 fold | sha256 tung fold | **byte-identical 10/10** |
| `spearman(pred_run1, pred_run2)` | 1.00000000 | (max|dp|=0, `np.array_equal`=True) |

=> Dat tieu chi CHINH cua pre-reg (byte-identical), khong phai du phong. **He tai lap duoc.**
rho 0.18991 nam trong CI95 that cua moc cu (`[0.1260, 0.2005]`, `LEAK_L1_REPORT §3.3`).
rho theo nam: 2021 0.2525 (bucket 3,612 dong — khong co y nghia) / 2022 0.1950 / 2023 0.1724 /
2024 0.2119.

## 1. Bins — `/home/ubuntu/predwf_G015_v2/`

Dinh dang deploy: 26 B/rec big-endian `[ts:int64][symId:int16][p4h,p12h,p24h,p72h:float32]`,
slot `p0`=p4h la prediction that, 3 slot con lai NaN (WFO doc `WFO_SEL_HORIZON_IDX=0`).
`score = 1 - P(win)` (engine dao dau). Manifest sha co-located: `predwf_G015_v2/MANIFEST.sha256`.

| File | rec | sha256 |
|---|---|---|
| predict_wf_20220101.bin | 1,123,854 | `aed0732c09e87a068622a78a51d8dd7a02ceb2c547d422cc430a996ab1cdc485` |
| predict_wf_20220401.bin | 1,172,010 | `185a1c6f86278db83c590188db8499574dfd4658cce131a4fc46a4a3af992d5b` |
| predict_wf_20220701.bin | 1,188,418 | `9aab0bbdbb811fbc3e26773ea94c1d0a6e4555f01626450cd24f2c9164f10776` |
| predict_wf_20221001.bin | 1,242,626 | `3a04f8c08c0ea9daaf1d5aae0c926b0dc27d23dd5a2d2d9b198eb3b18c62fafe` |
| predict_wf_20230101.bin | 1,302,607 | `34876b48635882ed2cbc0b37a9e5026ab6797bbbe38cd814f352fc788153725b` |
| predict_wf_20230401.bin | 1,524,605 | `8d27f13a4e4a9d0f13e3129a6d6f46d6fb90d470f7eb0cc22b5cc2ef804d747d` |
| predict_wf_20230701.bin | 1,671,614 | `074748f0a3e22f9947bb5e318cb7282b557efb9a527159dec5442f339cacf998` |
| predict_wf_20231001.bin | 1,912,959 | `92e7bd183b728a90af16e66e7f421fbb4b7de715b08c55119a07414da4d196ee` |
| predict_wf_20240101.bin | 2,140,992 | `dd3fc9a336c4b2d21f60e3422912fd6ff50ff2a26b84c47b43d41c64e008d360` |
| predict_wf_20240401.bin | 2,256,504 | `78f28d28576d0c7f17dba2f399f3655cd58549048995d0f086a5bf7ead15853b` |

So rec tung fold **khop chinh xac** so rec bins S1 (`predwf_map_s1a2`, xem `BINS_MANIFEST.md`) =>
cung khong gian (ts,symId) OOS. 10 fold roi nhau (disjoint), fold dai nhat 91 ngay < 100 =>
khong `LEAK-SUSPECT`.

Sao luu ngoai may: Kaggle dataset PRIVATE `chuyendinh/predwf-g015-v2-bins` (xem
`docs/G015REBUILD_RESULT.md` §6).

## 2. Input duoc ghim — sha256

Bang day du 31 file: `research/analysis/g015rebuild_inputs_sha.json` (commit cung PREREG 0449f21).
Manifest digest: `sha256(inputs_sha.json)=f14844f305c21777864bde2d5130623950853ee6557b56a86260e130b611cdc2`.

| nhom | file | sha256 | bytes |
|---|---|---|---|
| OI (SACH, KHONG rebuild) | `claudedata/oi/oi_percoin_full.bin` | `e3887f63…b305ec` | 4,227,723,300 |
| symbol map | `claudedata/oi/symbol_map.csv` | `3f817551…04eaa` | 11,232 |
| pool cham diem | `g015/pool/pool_dev.parquet` | `713460fc…99262` | 131,401,565 |
| Tool1 14 file DEV | `ds_feat15m/features_2021..2024Q2.t1c.gz` | inputs_sha.json | — |
| label 14 file DEV | `label_15m/funding_label_2021..2024Q2.pb` | inputs_sha.json | — |

## 3. Lenh chinh xac + moi truong

- Script: `research/kaggle/g015cut/../` -> ban dung o job nay: `/home/ubuntu/g015/rebuild.py`
  (ban trong git: `research/analysis/g015_rebuild.py`).
- Lenh: `OUT_DIR=/home/ubuntu/predwf_G015_v2 SCRATCH=<scratch> python3 rebuild.py`.
- Moi truong: python3, xgboost **3.2.0**, numpy/pandas/scipy Oracle; `tree_method="hist"`,
  **CPU** (`n_jobs=4` co dinh), `device` KHONG dat (mac dinh cpu).
- Reader: `/home/ubuntu/sel1m_code/tool1_col.py` (T1C2), `funding_label_pb.py`.
- Thoi gian: 37.2 phut (run1) / 37.9 phut (run2), 4 core.

## 4. Hyperparameter — chot (khop recipe canonical)

Luoi 15m; `y=(maxFav_4h>=0.06)`, `nBars_4h>=16`, KHONG stop-loss; WFO expanding, OOS 3 thang,
purge 72h wall-clock, embargo 0, TZ +7h; 10 cutoff DEV `20220101..20240401`;
XGB `n_estimators=400, max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
min_child_weight=20, scale_pos_weight=(1-pos)/pos, eval_metric=auc, random_state=42`;
45 feature (40 Tool1 + 5 OI, `merge_asof backward tol 2h`).

## 5. Vi sao CPU

GPU (`device=cuda`) khong tai lap theo bit. CPU `hist` voi `nthread=4` co dinh cho ket qua
**byte-identical** giua 2 lan chay (da chung minh §0). Baseline chinh thuc la con so CPU 0.18991.
Bins deploy cu (GPU/khong ro nguon) khong tai lap duoc va da bi loai lam baseline.
