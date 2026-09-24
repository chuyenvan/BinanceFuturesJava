# PREREG_S1_FREE_OFI_V3_UNIVERSE — OFI (Binance Vision aggTrades) tren TOAN BO universe, pha confound subset-thanh-khoan

Chot TRUOC khi build bat ky feature that nao va TRUOC khi tinh bat ky rank-IC/edge5 nao.
File nay PHAI duoc commit truoc `docs/RESULT_S1_FREE_OFI_V3_UNIVERSE.md`; nguoc lai ket qua VO HIEU.
Toan bo tinh toan THAT (tai aggTrades, build feature, train XGBoost, do rank-IC/edge5) chay tren
**Kaggle** (account `chuyendinh`), day kernel tu **may Windows** (kaggle CLI 2.2.2, `C:\Users\pc\.kaggle`).
**Oracle KHONG chay bat ky job nao** (shadow-c3 dang LIVE PAPER) — Oracle chi dung de `git commit`
file text (kiem `df -h /` + `systemctl is-active shadow-c3` TRUOC va SAU).

## 0. Boi canh — vi sao co vong V3

- `docs/result/RESULT_S1_FREE_OFI.md` + `docs/audit/AUDIT_HARNESS_OFI_2026-09-20.md`: OFI chi phu **15/>600 symbol**
  (15 symbol chon theo **so lenh gop = thanh khoan cao**). Candidate (+2.95pp CONFIRM edge5) VA noise
  control (+1.69pp) CUNG "THANG" => HARNESS_NGHI_NGO. Audit loai tru population mismatch va
  cross-session drift (baseline_fresh == baseline_frozen, delta = 0 tuyet doi) va xac dinh nguyen nhan:
  **NaN-mask cua feature = chi bao "la 1 trong 15 symbol thanh khoan cao"**, XGBoost hoc huong-mac-dinh
  cho NaN nhu mot symbol-identity feature; 15 symbol nay co edge5 CONFIRM khac phan con lai vi ly do
  KHONG lien quan OFI.
- `ofi_train_eval_v2.py` DA dung noise control voi DUNG NaN-mask cua candidate
  (`D["noise_ofi_check"] = np.where(D.ofi_1h.notna(), noise_vals, np.nan)`) — co che dung, nhung khi
  mask trung subset thanh khoan thi ca hai deu "an ke" confound. Cach sua o vong nay: **khong doi co
  che noise, ma doi PHAM VI de mask khong con tuong quan voi thanh khoan** — build OFI cho TOAN BO
  universe, khi do mask gan nhu phu het pool (chi thieu o gio/thang Binance Vision khong co file).

## 1. Recon mo rong pham vi (Buoc 1, 0-cost, CHI metadata S3 listing — khong tai file, khong tinh so)

Script `research/pipeline/x1/kaggle_ofi_v3/recon_vision_listing.py` (chay tren Windows, 2026-09-24)
liet ke `s3://data.binance.vision/data/futures/um/monthly/aggTrades/` (ten + size file .zip);
`recon_analyze.py` doi chieu voi `symbol_map.csv` (Oracle `/home/ubuntu/selector_pred_out/symbol_map.csv`,
781 symbol, lay ve read-only). Cua so DEV **2021-07 → 2025-12 (54 thang)**, khong mot thang nao cua 2026.

| pham vi | so symbol | symbol-thang (file listed) | MB nen | MB/symbol-thang |
|---|---|---|---|---|
| vong cu OLD15 (thanh khoan cao) | 15 | 486 | 55,955 | 115.1 |
| moi thu muc vision co >=1 thang trong cua so | 759 | 15,178 | 818,011 | 53.9 |
| **symbol_map ∩ vision (co >=1 thang trong cua so)** | **629** | **13,674** | **777,133** | 56.8 |
| (tham khao) symId % 2 == 0 | 318 | 6,838 | 398,944 | — |
| (tham khao) symId % 3 == 0 | 209 | 4,572 | 251,764 | — |

- 1006 thu muc symbol tren vision; 1 listing loi (ZKPUSDT, connection reset); 151/781 symbol trong
  symbol_map co **0 file** trong cua so (niem yet sau 2025-12 hoac khong co tren vision).
- Hieu chinh toc do tu vong cu: **5,667.5s / 55,955 MB = 0.1013 s/MB nen** (da gom ca 324 lan 404 va
  overhead moi file). Toan universe: 777,133 MB × 0.1013 + 404 × 0.3s ≈ **84,800s ≈ 23.6 kernel-gio**.
- Chia 10 shard can bang theo MB (LPT greedy, `make_shards_v3.py` -> `ofi_v3_shards.json`): moi shard
  59-65 symbol, ~77.3-78.2 GB, **uoc 2.35-2.36 gio/shard** (< nguong 3h). 5 slot song song => 2 dot
  ≈ **~5 gio wall** build + ~2.5 gio train/eval ≈ **~7.5 gio** tong => VUA 1 ngay lam viec.

## 2. QUYET DINH PHAM VI (Buoc 2) — CHOT

- **Universe V3 = moi symbol trong `symbol_map.csv` TRU nhung symbol ma S3 listing xac nhan 0 file
  aggTrades monthly trong 2021-07..2025-12** => **630 symbol** (629 co file + ZKPUSDT giu lai vi listing
  loi — build loop se tu 404 neu khong co). Quy tac CO HOC, **KHONG loc theo thanh khoan/volume/edge**;
  15 symbol cu la tap con. Danh sach day du + 151 symbol bi loai o `ofi_v3_shards.json`.
- Ly do chon "toan bo" thay vi quy tac co hoc (symId % k): toan bo KHA THI trong ngan sach (~7.5h,
  10 kernel ≤ 2.4h uoc tinh), va la lua chon SACH NHAT — mask "co OFI" khi do chi phu thuoc viec
  Binance Vision co file, gan nhu khong phu thuoc thanh khoan. KHONG dung "top-N tiep theo".
- Moi kernel shard: `OFI_SAFETY_LIMIT_SEC = 3.5h` (y vong cu). Neu shard `stopped_early=true`: chay
  **MOT** kernel "remainder" (cung code, `gen_kernels_v3.py --remainder`) cho dung `symbols_not_completed`;
  `ofi_train_eval_v3.py` tu bo cac symId chua hoan tat khoi shard bi cat (doc `symids_not_completed`)
  => khong trung lap. Day la HOAN TAT pham vi da chot, khong phai doi pham vi. Sau 1 vong remainder
  van chua du => DUNG, bao MASTER, KHONG train tren pham vi thieu.
- Loi mang/HTTP khac 404 (`n_err`): tong ≤ 1% so symbol-thang listed (≤ 136) => chap nhan la missing
  (NaN), liet ke trong RESULT. > 1% => DUNG, bao MASTER.

## 3. Feature (Y HET `docs/prereg/PREREG_S1_FREE_OFI.md` §2 — khong doi mot chu)

Nguon monthly `.../aggTrades/<SYM>/<SYM>-aggTrades-<YYYY-MM>.zip`; `ofi_1h = (buy-sell)/(buy+sell)`,
`aggr_buy_ratio_1h = buy/(buy+sell)` voi buy = quantity khi `is_buyer_maker=false`, sell khi `true`,
gio `floor(transact_time/3600000)*3600000`, NaN khi buy+sell=0. Gia tri THO moi gio (khong smooth).
**k = 2**, `inflate(2) = sqrt(2 ln 2) = 1.177410`. Code: `ofi_build_feat_v3.py` = `ofi_build_feat.py`
voi query duckdb/cong thuc/NaN rule Y HET; khac DUY NHAT: danh sach symbol tu shard, logging thay print,
`con.close()`, xoa CSV giai nen neu loi giua chung, summary them shard/symbols_not_completed.

## 4. Harness (Y HET `ofi_train_eval_v2.py` — `ofi_train_eval_v3.py` sinh CO HOC bang `gen_train_v3.py`)

- Du lieu: dataset `chuyendinh/s1-featv2-x1-20260919` (`cand_dev_x1_lite.parquet`, `feat_v2_x1_keep9.parquet`),
  baseline frozen `pred_baseline18_n1_kaggle.parquet` (kernel `chuyendinh/s1-baseline18-det-n1-20260919`,
  15.209468%), OFI = ghep 10 file `ofi_feat_x1.parquet` cua kernel `chuyendinh/ofi-v3-build-s0..s9`
  (+ remainder neu co), drop dong trung y het, `assert` khong co (ts,sym) trung voi gia tri khac.
- 3 bien the train TRONG CUNG kernel: `baseline_fresh` (KEEP9), `candidate` (KEEP9 + ofi_1h +
  aggr_buy_ratio_1h), `noise` (KEEP9 + `noise_ofi_check`). XGBRanker rank:ndcg, 300 cay, depth 4,
  lr 0.05, subsample/colsample 0.8, mcw 50, **n_jobs=1**, hist, seed 42, topk/8 cap. `rel5`, purge 72h,
  CUTS18, `assert tr.ts.max() < c`.
- **Noise control**: `noise_ofi_check = default_rng(20260920).random(len(D), float32)` dat NaN o **DUNG
  cac dong ofi_1h NaN cua pham vi MOI** (`np.where(D.ofi_1h.notna(), noise, nan)`), `assert` mask trung
  khop tuyet doi. k = 2.
- Metric: edge5 OOS (top-5 theo score thap = tot, tru trung binh tick), rank-IC phu (spearman(-score,
  g1lite), tick >= 10 dong). CI paired block-bootstrap 72h, NREP 2000, SEED 20260919, CI quanh tam
  × inflate(k). SELECT = fold 0-9 (2021Q3-2023Q4, CHI tham khao), **CONFIRM = fold 10-17 (2024Q1-2025Q4)
  = cong quyet dinh duy nhat**.
- Kiem tra phu (khong phai phep thu moi): `fresh_vs_frozen` (k=1) — ky vong delta = 0 tuyet doi nhu
  vong v2. Neu ≠ 0: ghi la bat thuong sanity, moi phep so van dung `baseline_fresh`, bao MASTER.
- Mo ta (KHONG phai tieu chi, KHONG tinh edge5 them): `ofi_coverage_frac`, coverage theo nam,
  so symbol trong pool co >= 1 dong OFI.

### 4.1 Luat quyet dinh (chot truoc, KHONG doi sau khi thay so) — Y HET PREREG goc §4/§4.1

- Tung bien the (so voi `baseline_fresh`, CONFIRM, k=2): **THANG** = mean>0 VA CI khong chua 0;
  **THUA** = mean<0 VA CI khong chua 0; con lai **NULL**. Ap rieng cho edge5 va rank-IC.
- (a) SELECT exceed cua noise: chi ghi nhan (xac suat duong tinh gia 1 cot ~23.9% o nguong 1.1774).
- (b) **Noise CONFIRM edge5 CI khong chua 0 => HARNESS_NGHI_NGO_VAN_CON** — khong cong bo verdict cho
  candidate; nghia la confound KHONG chi do subset thanh khoan; DUNG, bao MASTER, khong chay them.
- (c) Neu (b) khong xay ra: verdict vong nay = verdict CONFIRM edge5 cua candidate. Rank-IC bao song song.
- **Dieu kien tien quyet pha confound (chot truoc)**: `ofi_coverage_frac >= 0.90`. Neu < 0.90 => gan nhan
  `COVERAGE_KHONG_DAT` ben canh moi verdict (mask van co the mang thong tin subset), bao MASTER.

### 4.2 Sanity (dung neu fail — y vong cu)

So tick OOS moi fold = baseline; score khong NaN/Inf; `assert tr.ts.max() < c`; tap ts OOS candidate/noise
== baseline; `len` pred 3 bien the bang nhau (vong cu 6,685,957 dong, 18,283 tick).

## 5. Neu FAIL / neu ket qua ra sao — viec lam tiep (chot truoc)

- (b) xay ra: bao cao HARNESS_NGHI_NGO_VAN_CON + so lieu, KHONG chay bien the them, cho MASTER.
- Candidate NULL/THUA (noise sach): bao cao; OFI tho 1h k=2 KHONG co bang chung o universe day du.
  KHONG thu smoothing/cua so khac trong vong nay (moi bien the = pre-reg rieng, k tang).
- Candidate THANG (noise sach): CHI la ung vien — single seed 42; theo AGENT_RUNBOOK bay #7 hieu ung
  phai vuot CI multi-seed (>=3 seed) truoc khi tin; can pre-reg rieng, KHONG tich hop, KHONG deploy.
- Executor KHONG tuyen bo GO/NO-GO tong; RESULT chi bao so + verdict tung tieu chi.

## 6. Gioi han biet TRUOC

1. `is_buyer_maker` dien giai ke thua (PREREG goc §2), khong xac minh doc lap lai.
2. Rank-IC chi tren `g1lite` (dataset Kaggle rut gon, khong co g1_replay).
3. Single seed (42), 1 lan chay chinh — khong sweep.
4. NaN con lai (thang vision thieu file, gio 0 lenh) CO THE van tuong quan nhe voi thanh khoan thap;
   bao cao coverage theo nam de MASTER danh gia.
5. Train kernel ~2.3h o v2; feature day dac hon co the cham hon (Kaggle hard limit 12h, khong phai rui ro cat).
6. ZKPUSDT listing loi — giu trong universe, build tu 404 neu khong co file.

## 7. Ngoai pham vi

Du lieu 2026 / >2025-12, doi nhan/fold/hyperparameter, smoothing OFI, them symbol ngoai symbol_map,
chay bat ky job nao tren Oracle, cham 242, git push.

## 8. Thu tu

1. Commit file nay + `research/pipeline/x1/kaggle_ofi_v3/` (script, shard map) len Oracle branch `module` — TRUOC khi push kernel.
2. Push 5 kernel build (s0-s4), khi xong push s5-s9 (toi da 5 slot tong).
3. Kiem 10 `ofi_build_summary.json` theo §2 (stopped_early / n_err). Remainder neu can (toi da 1 vong).
4. Push `chuyendinh/ofi-v3-train-eval`; lay `ofi_result_v3.json`.
5. Viet `docs/RESULT_S1_FREE_OFI_V3_UNIVERSE.md` (bang song song vong cu 15 sym vs V3), commit, khong push.
