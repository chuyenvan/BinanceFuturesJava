# RESULT_S1_FREE_OFI_V3_MULTISEED — OFI V3 (630 symbol): xac nhan MULTI-SEED >= 3 (AGENT_RUNBOOK bay #7)

Ket qua THAT cua vong multi-seed, chay theo dung `docs/prereg/PREREG_S1_FREE_OFI_V3_MULTISEED.md`
(commit `f1ab3a6` = prereg + tooling sinh kernel, `a945faf` = tool phan tich pooled; **chot TRUOC**
khi push kernel va truoc khi doc bat ky so multi-seed nao). Khong doi luat sau khi thay so.

- **Ke thua**: `docs/prereg/PREREG_S1_FREE_OFI_V3_UNIVERSE.md` (gom AMENDMENT-A) + ket qua single-seed
  seed 42 `docs/RESULT_S1_FREE_OFI_V3_UNIVERSE.md` (commit `c5c9faf`).
- **Doi DUY NHAT so voi vong goc**: `random_state` cua XGBoost = seed cua kernel. Feature, dataset,
  10 kernel build (COMPLETE tu 2026-09-24 — **KHONG push lai**, xem §8), harness, fold, mask NaN,
  `NREP 2000`, **bootstrap SEED 20260919** va **noise RNG 20260920** giu NGUYEN.
- **Kernel**: `chuyendinh/ofi-v3-ms-s42` · `-s43` · `-s44` · `-s45` (4 kernel song song, 1 seed/kernel,
  `enable_gpu=false`, `enable_internet=false`, 11 `kernel_sources`). Push TU ORACLE 2026-09-26 ~10:37 (+07).
- **Thoi gian THAT** (tu log kernel): s42 **2 h 30 m** (9.012 s) · s43 **2 h 13 m** (8.008 s) ·
  s44 **2 h 23 m** (8.599 s) · s45 **2 h 14 m** (8.043 s); ca 4 xong trong **~2 h 35 m wall**
  (10:37 → ~13:12 +07). s42 cham hon vong goc (2 h 13 m) vi 4 kernel chay SONG SONG chia CPU.
- **Verdict theo dung luat §3 PREREG: PASS** (multi-seed xac nhan) — nhung **VAN CHI LA UNG VIEN**;
  khong tich hop, khong ONNX/LIVE, khong deploy.

## 1. Bang theo TUNG seed (CONFIRM = fold 10-17; k=3 => `inflate(3)=1,482304`)

Don vi Δedge5: diem phan tram tuyet doi so voi `baseline_fresh` CUNG seed (vd `+0,0165` = **+1,65 pp**);
Δrank-IC: don vi thap phan. CI paired block-bootstrap 72 h, NREP 2000, seed 20260919, **k=3**.
`*` = CI **khong** chua 0.

| seed | vai tro | SELECT Δedge5 (nguong k=2) | **CONFIRM Δedge5** (CI95×1,4823) | verdict | **CONFIRM Δrank-IC** | verdict | **noise CONFIRM Δedge5** | verdict noise |
|---|---|---|---|---|---|---|---|---|
| **42** | moc doi chieu (da biet) | +0,002838 (thr 0,002234 → CO) | **+0,016501** [+0,003423, +0,030408] | **THANG\*** | +0,001955 [−0,000020, +0,003981] | NULL | −0,003057 [−0,017729, +0,010830] | **NULL** |
| **43** | **MOI** | +0,002518 (thr 0,002888 → KHONG) | **+0,020072** [+0,004522, +0,036715] | **THANG\*** | +0,001690 [−0,000557, +0,003998] | NULL | +0,004025 [−0,013576, +0,023033] | **NULL** |
| **44** | **MOI** | −0,000421 (thr 0,002624 → KHONG) | **+0,022420** [−0,000003, +0,047457] | **NULL** (sat nut) | +0,003912 [+0,001128, +0,006833] | **THANG\*** | +0,005125 [−0,008742, +0,019546] | **NULL** |
| **45** | **MOI** | +0,002574 (thr 0,001980 → CO) | **+0,010179** [+0,001243, +0,018931] | **THANG\*** | +0,002135 [+0,000237, +0,004085] | **THANG\*** | −0,001430 [−0,014356, +0,010257] | **NULL** |

- **Nhat quan theo seed (C3)**: Δedge5 **duong o 3/3 seed moi** (va o ca seed 42);
  **2/3 seed moi co CI khong chua 0** (43, 45; seed 44 NULL vi `lo = −0,000003` = −0,0003 pp, sat 0).
  Δrank-IC **duong o 3/3 seed moi**, **2/3 seed moi co CI khong chua 0** (44, 45; 43 NULL).
- SELECT chi de **tham khao** (dung §4 cua PREREG goc: SELECT = fold 0-9, khong phai cong quyet dinh).

## 2. Pooled (3 seed MOI: 43+44+45, trung binh THEO TICK roi ap dung DUNG `block_ci_diff` k=3)

`n_ticks` CONFIRM **13.914** (edge5) / **13.805** (rank-IC), **229 block** (giong het vong goc);
`n_ticks` SELECT 4.369 / 251 block.

| metric (pooled 43/44/45) | mean | **CI95×1,4823** | verdict |
|---|---|---|---|
| **Δedge5 CONFIRM** | **+0,017557 (+1,76 pp)** | **[+0,005009, +0,031524]** | **THANG\*** |
| **Δrank-IC CONFIRM** | **+0,002579** | **[+0,000569, +0,004666]** | **THANG\*** |
| noise Δedge5 CONFIRM | +0,002574 | [−0,005349, +0,010797] | **NULL** |
| noise Δrank-IC CONFIRM | +0,000246 | [−0,001333, +0,001880] | **NULL** |
| (tham khao) Δedge5 SELECT | +0,001557 | [−0,001230, +0,004150] | NULL |

Pooled Δedge5 **+1,76 pp** nam trong khoang cua single-seed 42 (+1,65 pp) va cac seed moi
(+1,02 … +2,24 pp) — khong co seed nao "keo" ket qua.

## 3. Noise control — PHAI NULL: **DAT o MOI seed** (C1)

`noise_ofi_check` (cung NaN-mask voi `ofi_1h`) NULL o **ca 4/4 seed** (CI CONFIRM chua 0) va NULL ca khi
pooled. ⇒ **§4.1b mo rong KHONG kich hoat**: khong co HARNESS_NGHI_NGO, verdict duoc cong bo.

## 4. Sanity §4.2 + (C6) toan ven moi truong — **PASS**

| Kiem tra | Ket qua |
|---|---|
| `n_oos` = `len(pred)` 3 bien the BANG NHAU | **PASS** — 6.685.957 = 6.685.957 = 6.685.957 o **ca 4 seed** |
| So tick OOS / tick CONFIRM | **PASS** — 18.283 / 13.914 (13.805 rank-IC) **giong het nhau o ca 4 seed** va giong vong goc |
| Tap `ts` OOS candidate/noise == baseline_fresh | **PASS** — chieu dai chuoi diff = **18.283 dong, 0 NaN** (edge5) o ca 4 seed; rank-IC 109 NaN **giong het nhau** (tick < 10 dong) |
| `score` khong NaN/Inf | **PASS** — `assert` trong kernel chay het ca 4 seed |
| `assert tr.ts.max() < c` (purge 72 h) | **PASS** — khong `AssertionError` nao trong ca 4 log |
| noise mask == `ofi_1h.notna()` | **PASS** — log `noise_ofi_check coverage matches ofi_1h: True` o ca 4 seed |
| Input dong nhat | **PASS** — 10 file OFI, 9.730.284 dong (sau exact-dedupe), 630 symbol, coverage **0,95124**, coverage-theo-nam giong het o ca 4 seed |
| **(C6) seed 42 tai lap so da cong bo** | **PASS — 0,0 tuyet doi**: Δedge5 +0,016500961035490036; Δrank-IC +0,0019546861051446362; `baseline_fresh` = 15,209467887878418 %; `fresh_vs_frozen` max\|Δ\| = **0,0** |
| Doi chieu cheo so cua kernel vs chuoi diff da xuat | **PASS** — mean tinh lai tu parquet khop json (≤ 1e-12) o ca 4 seed |

**(C6) la bang chung toan ven manh**: cung code/input moi truong Kaggle CPU tai lap **byte-muc** so
single-seed da cong bo ⇒ 3 seed moi do trong CUNG moi truong (dung bay #7), khong ghep 2 moi truong.

### 4.1 `baseline_fresh` vs `baseline_frozen` theo tung seed (hieu chinh da chot TRUOC o PREREG §4)

| seed | `baseline_fresh` edge5 TOAN BO (% thô) | `baseline_frozen` (% thô) | `fresh_vs_frozen` Δedge5 CONFIRM |
|---|---|---|---|
| 42 | **15,209467887878418** | 15,209467887878418 | **0,000000 (tuyet doi)** |
| 43 | 14,840036392211914 | 15,209467887878418 | −0,004350 |
| 44 | 15,052899360656738 | 15,209467887878418 | −0,002404 |
| 45 | 15,171668052673340 | 15,209467887878418 | −0,000347 |

`baseline_frozen` la parquet CO DINH (train seed 42, session 2026-09-19). Yeu cau "fresh == frozen = 0"
**chi dat o seed 42** (kiem tra determinism cross-session, da PASS tuyet doi). O seed 43/44/45 `!= 0` la
**DUONG NHIEN** (khac model seed) — duoc bao cao nhu **NEN NHIEU SEED**, khong phai tieu chi pass/fail.
**Nen nhieu seed do duoc**: \|Δ CONFIRM\| <= **0,44 pp** (toan bo OOS: 0,37 pp), tuc hieu ung pooled
**+1,76 pp ~ 4 lan nen nhieu** — khong bi nhan chim trong nhieu seed.

## 5. Ap dung luat quyet dinh §3 PREREG (chot TRUOC, khong doi)

| Tieu chi | Ket qua |
|---|---|
| **(C1)** noise NULL o MOI seed (42/43/44/45) | **DAT** — 4/4 NULL ⇒ khong HARNESS_NGHI_NGO |
| **(C2)** pooled (43/44/45, theo tick) mean > 0 VA CI khong chua 0 | **DAT** — +0,017557 [+0,005009, +0,031524] |
| **(C3)** >= 2/3 seed moi co Δ > 0 VA >= 2/3 seed moi co CI khong chua 0 | **DAT** — 3/3 duong; 2/3 CI khong chua 0 (edge5) va 2/3 (rank-IC) |
| **(C4)** rank-IC song song | pooled Δrank-IC **THANG** (+0,002579 [+0,000569, +0,004666]) — khong mau thuan |
| **(C5)** sanity §4.2 o moi seed | **DAT** (§4) |
| **(C6)** seed 42 tai lap byte-muc | **DAT** (§4, Δ = 0,0 tuyet doi) |
| **VERDICT** | **PASS (multi-seed xac nhan) — VAN CHI LA UNG VIEN**, khong tich hop/deploy |

## 6. Ghi chu TRUNG THUC (khong over-claim)

1. **k=3 vs k=2**: vong nay chot `inflate(3)=1,482304` (K = so seed MOI). Do CI rong hon, **Δrank-IC
   cua seed 42 tro thanh NULL** o k=3 ([−0,000020, +0,003981]), trong khi ban da cong bo (k=2) la THANG
   ([+0,000391, +0,003570]). Moi verdict trong file nay dung **k=3** nhu da chot; so k=2 giu nguyen o
   `RESULT_S1_FREE_OFI_V3_UNIVERSE.md`. Pooled rank-IC **THANG** o k=3.
2. **Seed 44 sat nut**: Δedge5 +2,24 pp (cao nhat) nhung `lo = −0,000003` (−0,0003 pp) ⇒ NULL theo luat
   (§4.1: CI chua 0 = NULL). Khong duoc doc la "thua"; cung khong duoc keo vao C3(ii).
3. **SELECT**: `noise` vuot nguong SELECT o seed 44 (`+0,003722` ≥ 0,002569) — theo §4.1a SELECT chi la
   **GHI NHAN** (xac suat duong tinh gia 1 cot ~23,9% o nguong 1,1774), khong phai cong quyet dinh;
   `candidate` vuot SELECT o seed 42/45, khong vuot o 43/44. SELECT khong tham gia verdict.
4. **Sanity doc lap mot phan**: `n_oos`/tick-set/coverage/doc-lap-kernel duoc kiem tren **json + log +
   `ms_diffs_s<seed>.parquet`** (output nho). **KHONG** tai `pred_*.parquet` (~145 MB/seed) ve Oracle de
   khong cham dia (`df /` 93%) ⇒ khong co phep kiem lai pred tu file pred nhu vong goc; bu lai co
   (C6) tai lap byte-muc + doi chieu cheo mean(json vs diff) ≤ 1e-12.
5. `fresh_vs_frozen` o seed 43/44/45 la so MO TA (nen nhieu seed), khong phai tieu chi.
6. Verdict PASS o day KHONG duoc doc la "OFI co tac dung that / da GO": day la ket qua **4 seed** (3 moi +
   1 tai lap) trong 1 cua so du lieu; chua co out-of-sample thoi gian moi, chua qua LIVE, va 2 cot moi
   = 47 cot = **dung duong LIVE** ⇒ can owner duyet rieng.

## 7. Muc nao BO + ly do

1. **KHONG push lai 10 kernel build** — da COMPLETE tu 2026-09-24 voi output day du (da kiem chung o
   vong truoc: 630/630 symbol, `stopped_early=false`, 9.730.284 dong); push lai ton ~25,6 h quota cho
   ket qua y het. Ca 4 kernel multi-seed doc truc tiep 10 output do qua `kernel_sources`.
2. **KHONG gop 4 seed vao 1 kernel** — tinh truoc 4 × ~2,2 h = ~8,8 h, sat hard limit 12 h/kernel va
   mat toan bo ket qua neu bi cat; tach 4 kernel chay song song (~2 h 35 m wall), 4 slot <= tran 5.
3. **KHONG tai `pred_*.parquet`** (~145 MB/seed): chi tai json + log + `ms_diffs` (tổng **3,6 MB**), xoa
   file lon ngay; `df -h /` truoc 16 G → sau 15 G free.
4. **KHONG chay gi tren Oracle ngoai** 3 lenh kiem (`df -h /`, `free -g`, `systemctl is-active shadow-c3`)
   + `kaggle` CLI + script phan tich numpy/pandas (khong Java/sim, khong cham shadow-c3 LIVE).
5. **KHONG chay them bien the/smoothing** — ngoai pham vi; moi bien the = pre-reg rieng, k tang.

## 8. Gioi han (khong over-claim)

1. 4 seed (1 moc + 3 moi), 1 lan chay moi seed — khong sweep hyperparameter/fold.
2. Rank-IC chi tren `g1lite` (khong co `g1_replay`), nhu vong goc.
3. `is_buyer_maker` dien giai ke thua PREREG goc §2, khong xac minh doc lap lai.
4. 2021 chi phu 0,2515 (window build bat dau 2021-07) — chu yeu anh huong SELECT (chi tham khao).
5. 2 symbol-thang loi mang (SUSHIUSDT 2024-05, HOOKUSDT 2024-09) => NaN, <= 1% theo §2 (ke thua).
6. Nen nhieu seed do o day (<= 0,44 pp) la cua CHINH XGBoost tren dev set nay; khong dai dien cho
   nen nhieu cua moi truong LIVE.

## 9. File / artifact

- Pre-reg: `docs/prereg/PREREG_S1_FREE_OFI_V3_MULTISEED.md` (commit `f1ab3a6`).
- Tooling: `research/pipeline/x1/kaggle_ofi_v3/gen_multiseed_v3.py` (`f1ab3a6`),
  `ms_pool_analyze.py` (`a945faf`).
- Kernel: `chuyendinh/ofi-v3-ms-s42|s43|s44|s45` (COMPLETE).
- Output nho tren Oracle: `/home/ubuntu/ofi_v3/ms/outALL/` (4 json + 4 `ms_diffs_s*.parquet` + 4 log,
  3,6 MB) va `summary_ms.json` (23 KB) + `summary_ms_checks.json` — nguon cua §1-§5.
