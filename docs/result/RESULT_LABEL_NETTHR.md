# RESULT — LABEL_NETTHR (sweep NET_THR cho selector G015, TANG MODEL)

Pre-reg: `docs/prereg/PREREG_LABEL_NETTHR.md` (md5 `277caa6bcd0ae44425894cf72b285302`, commit `1cdacdc2`, chot TRUOC so). DEV <= 2025-12-31, 16 fold (20220101..20251001), seed 42, KHONG fold 2026, KHONG 242/shadow. Tho: `docs/result/label_netthr.json`. Sim: KHONG chay (khong arm nao qua cong, xem §0).

## 0. Ket luan (rui ro truoc)

1. **Khong arm nao qua cong => DUNG, khong sim.** Cong = ΔrankIC duong ngoai 0 (pre-reg) VA lift@8 khong kem (MASTER 09-30). M_010: ΔrankIC +0.00800 (CI infl [+0.00716, +0.00885], 16/16 fold duong) nhung **lift@8 -0.05948 (CI [-0.06762, -0.05126]), AUC -0.01438 => kem co y nghia**. M_020: ΔrankIC -0.00361 (CI [-0.00411, -0.00309], 0/16 fold duong) => khong qua.
2. **Theo chu cua pre-reg rieng ΔrankIC thi M_010 'qua'** (CI > 0, gap ~12x san nhieu 0.0007). Toi khong sim vi dieu kien lift@8 khong kem (MASTER) khong dat va rank-IC vs retEnd_4h AM o moi fold (M_015 -0.05184) nen 'IC tang' = bot am, khong phai 'chon coin loi hon'. Neu MASTER muon sim M_010 theo chu pre-reg thi bins da co (`out_M_010`), can quyet dinh — toi khong tu y.
3. **Cau hoi 'doi NET_THR doi THU HANG hay chi calibration?'**: doi ca hai, nhung theo MOT TRUC. Nhan lo hon (0.010) hoac chat hon (0.020) doi thu hang coin co the do duoc: xs-rank-corr per-tick vs M_015 = M_010 0.912, M_020 0.950 (san nhieu retrain, ORIG vs M_015 = 0.940). M_010 thap hon san ro (16/16 fold ΔIC cung dau) => thu hang doi that; M_020 xs-corr ~ san nhieu (khong tach duoc khoi nhieu bang tuong quan) nhung ΔIC am o 16/16 fold (xem §3), tuc thu hang do duoc theo IC. Huong doi la **danh doi**: NET_THR thap => IC len (bot nghieng ve coin vol cao) nhung lift@8/AUC xuong; NET_THR cao => nguoc lai. Khong arm nao troi hon o CA HAI thuoc do => label-threshold la nut **tradeoff vol-tilt**, khong phai lever ranking mien phi.
4. **'Gate G2 tu bu' CHUA KIEM** (khong sim). Cau nay khong duoc rut ra tu ket qua nay. Chi biet: p_mean gan nhu khong doi (0.453/0.430/0.407, do scale_pos_weight) nhung **p_std doi manh** (0.104/0.126/0.142 cho M_010/M_015/M_020) => phan phoi p va gate rolling ratio co the bi anh huong; can sim de biet.

## 1. Tai lap M_015 (kiem hop le nen)

- Trainer `research/pipeline/g015_net_train.py` md5 `a32bb0f759a884b2cb3cdff7aa1e9297` (nhung nguyen vao kernel, assert md5), xgboost 3.2.0, GPU, seed 42, 16 fold; kernel `chuyendinh/netthr-m015-gpu|m010-gpu|m020-gpu` (dataset `funding-oi-percoin`, `funding-unf15-data`, `sel1m-code`; chi link file feature/label start < 20260101).
- Fold 20240101: n_train 14,834,006 · pos 0.1864 · spw 4.365823 **khop tuyet doi** deploy (G4_RECIPE_C4). Fold dau n_train 3,730,472 khop kernel ablation cu.
- **KHONG the spearman 1.0/fold**: retrain GPU khong byte-identical (runbook §0 rui ro 2; chi predict-tu-model-goc moi 1.0). Thay bang: xs-rank-corr per-tick M_015 vs predwf_G015x26 (deploy) = **0.940** (theo fold 0.84, 0.84, 0.90, 0.92, 0.93, 0.96, 0.98, 0.96, 0.96, 0.96, 0.95, 0.95, 0.95, 0.97, 0.98, 0.98). Day la **san nhieu retrain** de doc moi so sanh ben duoi.
- San nhieu bang so: ORIG − M_015 (CUNG nhan, chi khac retrain): ΔrankIC +0.00066 (CI infl [+0.00014, +0.00120] — 'ngoai 0' du la nhieu thuan, vi CI block-72h khong bao seed/device noise), Δlift@8 -0.00498, ΔAUC -0.00177. **|Δ| <= ~0.0007 (IC) la nhieu.**

## 2. Tang model — tong 16 fold (mean per-fold; per-timestamp cross-section, MIN_N 30 coin/tick)

Target do co dinh = `retEnd_4h`; win_ref = `retEnd_4h > 0.015` cho lift/AUC. lift@8 = win-rate top-8 theo p / win-rate toan tick. AUC_cs = AUC per-tick (win_ref). spread = mean(retEnd top-8) − mean(retEnd toan tick).

| arm | rank-IC | lift@8 | AUC_cs | spread top8 (4h) | p_mean | p_std | xs-corr vs M_015 |
|---|---:|---:|---:|---:|---:|---:|---:|
| M_015 | -0.05184 | 1.6884 | 0.6698 | +0.00021 | 0.4297 | 0.1259 | — |
| M_010 | -0.04384 | 1.6254 | 0.6554 | +0.00045 | 0.4529 | 0.1041 | 0.912 |
| M_020 | -0.05545 | 1.7079 | 0.6756 | +0.00008 | 0.4067 | 0.1425 | 0.950 |
| ORIG | -0.05119 | 1.6829 | 0.6680 | +0.00021 | 0.4309 | 0.1246 | 0.940 |

(ORIG = predwf_G015x26 deploy, chi tham chieu san nhieu.)

### Delta paired vs M_015 (CI block-72h 2000 rep seed 20260905, inflate k=2 = 1.1774)

| arm | metric | Δ | CI95 raw | CI95 inflate | folds Δ>0 |
|---|---|---:|---|---|---:|
| M_010 | rank-IC | +0.00800 | [+0.00729, +0.00872] | [+0.00716, +0.00885] | 16/16 |
| M_010 | lift@8 | -0.05948 | [-0.06639, -0.05250] | [-0.06762, -0.05126] | 0/16 |
| M_010 | AUC_cs | -0.01438 | [-0.01533, -0.01342] | [-0.01550, -0.01325] | 0/16 |
| M_010 | win-rate top8 | -0.01048 | [-0.01170, -0.00925] | [-0.01192, -0.00904] | 0/16 |
| M_010 | spread top8 | +0.00024 | [+0.00010, +0.00038] | [+0.00007, +0.00041] | 13/16 |
| M_020 | rank-IC | -0.00361 | [-0.00403, -0.00317] | [-0.00411, -0.00309] | 0/16 |
| M_020 | lift@8 | +0.01837 | [+0.01349, +0.02333] | [+0.01263, +0.02421] | 16/16 |
| M_020 | AUC_cs | +0.00588 | [+0.00536, +0.00638] | [+0.00527, +0.00646] | 16/16 |
| M_020 | win-rate top8 | +0.00324 | [+0.00238, +0.00411] | [+0.00223, +0.00427] | 16/16 |
| M_020 | spread top8 | -0.00013 | [-0.00024, -0.00002] | [-0.00026, +0.00000] | 5/16 |

## 3. Theo fold

| fold | IC M_015 | ΔIC M_010 | ΔIC M_020 | lift M_015 | Δlift M_010 | Δlift M_020 | xc M_010 | xc M_020 | xc ORIG |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 20220101 | -0.04907 | +0.01342 | -0.00527 | 1.200 | -0.045 | +0.015 | 0.818 | 0.870 | 0.836 |
| 20220401 | -0.03836 | +0.01580 | -0.00950 | 1.195 | -0.041 | +0.024 | 0.765 | 0.848 | 0.843 |
| 20220701 | -0.04712 | +0.01244 | -0.00462 | 1.325 | -0.050 | +0.042 | 0.856 | 0.918 | 0.902 |
| 20221001 | -0.03930 | +0.00799 | -0.00578 | 1.725 | -0.089 | +0.015 | 0.900 | 0.941 | 0.923 |
| 20230101 | -0.05427 | +0.01040 | -0.00514 | 1.453 | -0.066 | +0.006 | 0.881 | 0.951 | 0.935 |
| 20230401 | -0.06964 | +0.00618 | -0.00248 | 1.983 | -0.100 | +0.011 | 0.948 | 0.969 | 0.961 |
| 20230701 | -0.03218 | +0.00290 | -0.00083 | 2.645 | -0.097 | +0.056 | 0.961 | 0.977 | 0.979 |
| 20231001 | -0.04441 | +0.00562 | -0.00307 | 1.834 | -0.099 | +0.030 | 0.946 | 0.968 | 0.960 |
| 20240101 | -0.06271 | +0.01320 | -0.00524 | 1.673 | -0.082 | +0.030 | 0.897 | 0.951 | 0.957 |
| 20240401 | -0.04632 | +0.00354 | -0.00139 | 1.748 | -0.068 | +0.009 | 0.940 | 0.970 | 0.960 |
| 20240701 | -0.05205 | +0.00335 | -0.00128 | 1.592 | -0.034 | +0.010 | 0.951 | 0.974 | 0.951 |
| 20241001 | -0.06603 | +0.01101 | -0.00413 | 1.409 | -0.028 | +0.000 | 0.911 | 0.953 | 0.946 |
| 20250101 | -0.06754 | +0.00608 | -0.00272 | 1.599 | -0.056 | +0.013 | 0.929 | 0.960 | 0.949 |
| 20250401 | -0.04659 | +0.00419 | -0.00188 | 1.642 | -0.080 | +0.024 | 0.955 | 0.979 | 0.973 |
| 20250701 | -0.05250 | +0.00550 | -0.00266 | 2.048 | -0.060 | +0.013 | 0.971 | 0.985 | 0.981 |
| 20251001 | -0.06139 | +0.00639 | -0.00173 | 1.946 | -0.012 | +0.013 | 0.958 | 0.981 | 0.977 |

## 4. Cong (pre-reg + dieu kien MASTER)

| arm | ΔrankIC CI infl > 0 (pre-reg) | > san nhieu 0.0007 | lift@8 khong kem | QUA CONG SIM |
|---|---|---|---|---|
| M_010 | CO ([+0.00716, +0.00885]) | CO | **KHONG** (Δ -0.05948, CI [-0.06762, -0.05126]) | **KHONG** |
| M_020 | KHONG ([-0.00411, -0.00309]) | — | co (Δ +0.01837) | **KHONG** |

## 5. Rui ro / gioi han

1. **Mot seed, mot may (GPU)**. CI block-72h chi bao bien dong thoi gian, KHONG bao bien dong retrain. San nhieu do duoc (ORIG vs M_015) ΔIC 0.0007, xs-corr 0.94. ΔIC cua M_010 (0.0080) gap ~12x san; nhung Δlift/AUC cua M_010 va M_020 nen doc voi cung san (ΔAUC ORIG −0.0018 vs M_010 −0.0144: gap ~8x).
2. **rank-IC vs retEnd_4h AM moi fold** (ca deploy). Model chon coin de vuot +1.5% (vol cao) — lift@8 ~1.69 nhung spread return top-8 chi ~+2bp/4h. rank-IC theo retEnd la proxy yeu cho viec selector lam; ΔIC>0 o M_010 co the chi la bot nghieng vol. Dinh nghia lift@8/AUC/spread do toi (script `netthr_metrics.py`) chot theo pre-reg 'lift@8 (top-8 admit), AUC' voi win_ref co dinh 0.015 — pre-reg khong ghi cong thuc chi tiet, day la dien giai.
3. spread top-8 return tang o M_010 (+0.00024, CI infl [+0.00007, +0.00041]) nhung la ~2.4bp/4h, cung bac voi nhieu economics — khong dung de chung minh loi ich.
4. **Khong sim** => khong biet ΔIC/Δlift co chuyen thanh §9 khong, va gate rolling G2 co tu hieu chinh khong. Ket luan 'label-thr khong phai lever' chi o TANG MODEL, mot seed.
5. Base rate nhan toan DEV tren Kaggle = 0.1885 (pre-reg ghi 0.1849, kha nang gom 2026); khong anh huong (n_train fold 20240101 khop tuyet doi).
6. Provenance: chain kernel (`~/claude_master/0930_netthr`) da dung san truoc khi toi vao (khong ro nguoi tao); toi da review (md5 trainer, fold list, symlink chi <20260101, THR/ARM tung kernel) truoc khi dung. Dataset `funding-unf15-data` khong doc truc tiep, nhung khop n_train/pos/spw voi deploy nen chap nhan.

## 6. Viec treo

- MASTER quyet: (a) chap nhan verdict 'khong sim'; hoac (b) sim M_010 theo chu pre-reg (bins `out_M_010` neu con; da xoa se phai tai lai kernel `chuyendinh/netthr-m010-gpu`); hoac (c) them seed (M_015 s43 + M_010 s43) de dong san nhieu — can amendment pre-reg truoc.
- Neu muon do 'thu hang vs vol-tilt' ro hon: doi target do (vd. quantile-return rank, hoac IC vs |ret|/vol) — ngoai pham vi pre-reg.

## 7. File / job

- Kaggle kernels COMPLETE, khong con job chay: `chuyendinh/netthr-m015-gpu`, `netthr-m010-gpu`, `netthr-m020-gpu`.
- Ma: `research/analysis/netthr/` (`netthr_metrics.py`, `netthr_build_kernel.py`, `netthr_kernel_template.py`, `netthr_chain.sh`, `netthr_show.py`, `netthr_make_result.py`). Tho: `docs/result/label_netthr.json`.
- Bins goc (16 fold x 3 arm) o `~/claude_master/0930_netthr/out_M_0xx` — da don sau commit (xem tin nhan).
