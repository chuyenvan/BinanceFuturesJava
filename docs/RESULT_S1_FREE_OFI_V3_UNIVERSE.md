# RESULT_S1_FREE_OFI_V3_UNIVERSE — OFI (Binance Vision aggTrades) tren TOAN BO universe (630 symbol), pha confound subset-thanh-khoan

Ket qua THAT cua vong V3, chay theo dung `docs/prereg/PREREG_S1_FREE_OFI_V3_UNIVERSE.md`
(gom **AMENDMENT-A**: doi MAY PUSH Windows → Oracle; KHONG doi feature/harness/fold/CI/
**luat quyet dinh §4.1**/sanity §4.2/pham vi §2/thu tu §8). Khong doi luat sau khi thay so.

- **Commit truoc khi push**: `12119de` (AMENDMENT-A) va `9253024` (tooling override `OFI_V3_OUT`,
  khong doi thiet ke do — chi doi DUONG GHI output).
- **Kernel build**: `chuyendinh/ofi-v3-build-s0..s9` — COMPLETE, `stopped_early=false` ca 10.
- **Kernel train/eval**: `chuyendinh/ofi-v3-train-eval` (version 1, private, `enable_gpu=false`,
  `enable_internet=false`, 11 `kernel_sources`), push TU ORACLE 2026-09-26 ~07:17 (+07),
  COMPLETE 2026-09-26 09:30:41 (+07) ⇒ **~2h13m** (v2 tham chieu 2h25m).

## 1. Build feature — so THAT (10 shard, 630 symbol)

Tu `ofi_build_summary.json` cua tung kernel (doc qua API, khong tai parquet).

| shard | n_sym | sym-thang thu | `n_ok` | `n_skip_404` | `n_err` | `stopped_early` | dong feature | **thoi gian THAT** | uoc §1 |
|---|---|---|---|---|---|---|---|---|---|
| s0 | 60 | 3240 | 1158 | 2082 | 0 | false | 823,654 | **3.078 h** (11079.7s) | 2.359 h |
| s1 | 59 | 3186 | 1155 | 2031 | 0 | false | 818,661 | **3.022 h** (10881.0s) | 2.355 h |
| s2 | 63 | 3402 | 1474 | 1928 | 0 | false | 1,046,320 | **1.157 h** (4164.9s) | 2.355 h |
| s3 | 63 | 3402 | 1414 | 1988 | 0 | false | 1,008,831 | **2.842 h** (10230.0s) | 2.355 h |
| s4 | 64 | 3456 | 1439 | 2017 | 0 | false | 1,026,260 | **2.658 h** (9570.3s) | 2.355 h |
| s5 | 65 | 3510 | 1428 | 2082 | 0 | false | 1,015,236 | **2.407 h** (8664.5s) | 2.359 h |
| s6 | 64 | 3456 | 1578 | 1877 | **1** | false | 1,126,632 | **2.446 h** (8805.3s) | 2.355 h |
| s7 | 64 | 3456 | 1293 | 2163 | 0 | false | 918,677 | **3.064 h** (11031.7s) | 2.355 h |
| s8 | 64 | 3456 | 1307 | 2149 | 0 | false | 928,010 | **2.532 h** (9116.6s) | 2.355 h |
| s9 | 64 | 3456 | 1427 | 2028 | **1** | false | 1,018,003 | **2.395 h** (8621.3s) | 2.355 h |
| **tong** | **630** | **34,020** | **13,673** | **20,345** | **2** | **false** | **9,730,284** | **25.60 h** | 23.58 h |

- **Khong shard nao bi cat** (`stopped_early=false`, max 3.078 h < nguong an toan 3.5 h) ⇒
  **KHONG can kernel "remainder"**.
- `n_err` = **2/34,020 (0,006%)** ≤ nguong 1% (§2) ⇒ chap nhan la missing (NaN). Ca 2 deu la
  `ConnectionResetError(104)`: **SUSHIUSDT 2024-05** (s6) va **HOOKUSDT 2024-09** (s9).
- `n_ok` 13,673 vs 13,674 uoc o §1: lech dung 1 file — nhat quan voi ZKPUSDT (listing loi,
  giu trong universe, build ra 404) da disclose truoc o PREREG §6.6.
- 20,345 404 = 34,020 − 13,673 − 2: dung ban chat symbol niem yet muon (trung binh 21.7
  thang/symbol / 54 thang), KHONG phai loi mang.
- Thoi gian: trung binh 2.56 h/shard (uoc 2.36 h), bien do **1.157 h → 3.078 h** — bien do
  lon hon uoc, nhung **moi shard van duoi nguong 3.5 h** nen thiet ke §8 (5+5, ~7.5 h wall)
  van dung. s2 nhanh bat thuong (1.157 h cho 77.7 GB) — nghi do thong luong mang cua container
  Kaggle khac nhau, KHONG anh huong tinh dung dan cua du lieu.

## 2. Coverage — DIEU KIEN TIEN QUYET §4.1 (chot truoc: `ofi_coverage_frac >= 0.90`)

| | V2 (15 sym) | **V3 (630 sym)** |
|---|---|---|
| `ofi_coverage_frac` (dong pool co `ofi_1h` khong NaN) | 0.026631 (**2,66%**) | **0.951243 (95,12%)** |
| `pool_n_sym` / `n_sym co >=1 dong OFI` | — | **621 / 621** |
| `n_rows_with_ofi` | — | 6,677,851 / 6,685,957 |
| `ofi_n_files` / `ofi_n_rows` / `ofi_n_sym` | 1 / 349,651 / 15 | 10 / 9,730,284 / 630 |

Coverage theo nam: **2021: 0.2515** · 2022: 0.9818 · 2023: 0.9902 · 2024: 0.99988 · 2025: 0.99999.
(2021 thap vi cua so build bat dau 2021-07 con pool `cand_dev_x1_lite` co ca H1-2021 ⇒ NaN —
anh huong chu yeu o SELECT; CONFIRM 2024-2025 gan nhu phu kin.)

**`ofi_coverage_frac = 0.9512 >= 0.90` ⇒ DIEU KIEN TIEN QUYET DAT, KHONG gan nhan
`COVERAGE_KHONG_DAT`.** Mask NaN cua OFI bay gio phu 95,12% pool thay vi 2,66%, va phu thuoc
"Binance Vision co file thang do hay khong" chu khong con la "co phai 1 trong 15 symbol
thanh khoan cao" — dung muc tieu §0 cua PREREG.

## 3. Bang §4.1 — candidate / baseline_fresh / noise control (CONFIRM = fold 10-17)

Don vi Δedge5: diem phan tram tuyet doi cua edge5 so voi `baseline_fresh` (vd `+0.0165` = **+1,65 pp**);
Δrank-IC: don vi thap phan. CI paired block-bootstrap 72h, NREP 2000, SEED 20260919, k=2
(`inflate(2)=1.177410`), 229 block.

| Bien the | SELECT mean Δedge5 | SELECT nguong `inflate(2)*sd_boot` | SELECT vuot? | CONFIRM Δedge5 (CI95×1.1774) | CONFIRM verdict edge5 | CONFIRM Δrank-IC (CI95×1.1774) | CONFIRM verdict rank-IC |
|---|---|---|---|---|---|---|---|
| **candidate** (KEEP9 + `ofi_1h` + `aggr_buy_ratio_1h`) | +0.002838 (+0.284pp) | 0.002234 | **CO** | **+0.016501** [+0.006199, +0.027633] (**+1.65pp** [+0.62, +2.76]) | **THANG** | **+0.001955** [+0.000391, +0.003570] | **THANG** |
| **noise_ofi_check** (doi chung, k=2, cung mask NaN voi `ofi_1h`) | +0.000324 (+0.032pp) | 0.002351 | KHONG | −0.003057 [−0.014792, +0.007893] (−0.31pp) | **NULL** | +0.000882 [−0.000461, +0.002387] | **NULL** |
| **baseline_fresh** vs **baseline_frozen** (k=1, kiem tra phu) | 0.000000 | 0.000000 | — | **0.000000** [0.000000, 0.000000] | NULL (Δ=0 tuyet doi) | +0.0000165 [−0.0000005, +0.0000540] | NULL |

`n_ticks` CONFIRM = **13,914** (edge5) / **13,805** (rank-IC) cho ca 3 bien the — giong het nhau;
`n_oos = 6,685,957` va `n_ticks_all = 18,283` giong het V2.

### 3.1 Bang song song vong cu (15 sym) vs V3 (630 sym)

| | V2 — 15 sym (2026-09-20) | **V3 — 630 sym (2026-09-26)** |
|---|---|---|
| `ofi_coverage_frac` | 0.026631 | **0.951243** |
| candidate CONFIRM Δedge5 | +0.02946 [+0.00930, +0.05685] → **THANG\*** | **+0.01650 [+0.00620, +0.02763] → THANG** |
| noise CONFIRM Δedge5 | +0.01688 [+0.00041, +0.03934] → **THANG\*** | **−0.00306 [−0.01479, +0.00789] → NULL** |
| candidate CONFIRM Δrank-IC | +0.000116 [−0.00114, +0.00133] → NULL | **+0.001955 [+0.000391, +0.003570] → THANG** |
| noise CONFIRM Δrank-IC | +0.000136 [−0.00116, +0.00152] → NULL | +0.000882 [−0.000461, +0.002387] → NULL |
| `baseline_fresh` vs `baseline_frozen` | 0.000000 (khop tuyet doi) | **0.000000 (khop tuyet doi, tai lap lan 3)** |
| **Verdict theo §4.1** | **HARNESS_NGHI_NGO** (§4.1b kich hoat) | **THANG** (candidate), noise SACH |

\* verdict rieng cua tung bien the nhung KHONG duoc cong bo o vong cu vi bi loai boi §4.1(b).

Nhan xet (mo ta, KHONG phai tieu chi moi): hieu ung candidate CONFIRM giam tu +2.95pp (V2) xuong
+1.65pp (V3), dung huong voi gia thuyet "phan lon hieu ung V2 den tu confound subset-thanh-khoan"
— nhung day la so sanh GIUA 2 thiet ke khac nhau (khac pham vi, khac mask), KHONG phai phep do
"tach confound" da pre-register, nen chi ghi nhan.

## 4. Sanity §4.2 — **PASS** (tat ca)

| Kiem tra | Ket qua |
|---|---|
| So tick OOS moi fold = baseline | **PASS** — kiem doc lap tren `pred_*.parquet`: `groupby(fold).ts.nunique()` va `.size()` BANG NHAU tuyet doi giua 3 bien the |
| `score` khong NaN/Inf | **PASS** — `(~np.isfinite(score)).sum() == 0` cho ca 3 (assert trong kernel cung PASS) |
| `assert tr.ts.max() < c` (purge 72h) | **PASS** — kernel chay het, khong assertion nao bao loi |
| Tap `ts` OOS candidate/noise == baseline | **PASS** — tap `ts` 3 bien the trung khop tuyet doi (18,283 tick) |
| `len` pred 3 bien the bang nhau | **PASS** — 6,685,957 = 6,685,957 = 6,685,957 |
| `assert` khong co (ts,sym) trung gia tri khac (OFI) | **PASS** — 9,730,284 dong raw = sau exact-dedupe, `n_sym` 630 |
| noise mask trung khop `ofi_1h` notna | **PASS** — `True` (in ra trong log) |
| `fresh_vs_frozen` (k=1) | **PASS/ky vong** — Δedge5 = **0.000000** tuyet doi (nhu vong v2); `baseline_fresh = baseline_frozen = 15.209467887878418%` ⇒ Kaggle tai lap 100% giua 2 session/ngay khac nhau |

## 5. Ap dung luat quyet dinh §4.1 (chot TRUOC khi thay so — khong doi)

- **(a)** SELECT vuot nguong `inflate(2)*sd_boot`: **candidate CO** (+0.002838 ≥ 0.002234);
  **noise KHONG** (+0.000324 < 0.002351). Theo §4.1a day chi la GHI NHAN (xac suat duong tinh
  gia 1 cot ~23.9%), khong phai ket luan.
- **(b)** `noise` CONFIRM edge5 CI **CHUA 0** ([−0.014792, +0.007893]) ⇒ **§4.1b KHONG kich hoat**
  ⇒ **HARNESS_NGHI_NGO_VAN_CON KHONG xay ra**; harness duoc coi la SACH o vong nay, va **KHONG
  phai dung lai / bao MASTER vi ly do ngh ngo harness**.
- **(c)** Vi (b) khong xay ra: **verdict vong nay = verdict CONFIRM edge5 cua candidate = THANG**.
  Rank-IC bao song song: **candidate THANG**, noise NULL — nhat quan, khong mau thuan.
- **Dieu kien tien quyet**: `ofi_coverage_frac = 0.951243 ≥ 0.90` ⇒ DAT.

## 6. Chi tiet tung fold CONFIRM (edge5 OOS THO, chua tru baseline)

| fold | cutoff | ticks | `baseline_fresh` | **candidate** | **noise** |
|---|---|---|---|---|---|
| 10 | 2024-01-01 | 814 | +8.438% | +8.409% | +8.480% |
| 11 | 2024-04-01 | 346 | +4.259% | +4.277% | +4.730% |
| 12 | 2024-07-01 | 291 | +8.995% | **+9.836%** | +9.393% |
| 13 | 2024-10-01 | 809 | +8.536% | **+11.015%** | +10.013% |
| 14 | 2025-01-01 | 1167 | +14.412% | **+14.872%** | +14.259% |
| 15 | 2025-04-01 | 1483 | +8.776% | **+9.493%** | +9.258% |
| 16 | 2025-07-01 | 2095 | +15.862% | **+18.421%** | +15.613% |
| 17 | 2025-10-01 | 6909 | +24.226% | **+26.218%** | +23.389% |

candidate > `baseline_fresh` o **7/8** fold CONFIRM (duy nhat fold 10 nguoc −0.03pp), khong co pattern "fold nao cung thang" nhu vong cu; noise dao dau (5 tang / 3 giam). Day la khac biet
DINH TINH so voi V2 (V2: candidate va noise dinh nhau tung fold, chenh lech trong [−0.94, +2.36]pp
khong co huong he thong — xem RESULT V2 muc 4.2).

## 7. Tra loi dut khoat 3 cau hoi

**(a) Confound "mask = symbol-thanh-khoan" da bi PHA chua? — DA, bang 3 bang chung doc lap:**
  1. `ofi_coverage_frac` tu **0.0266 → 0.9512**; mask NaN khong con nhan dien mot nhom symbol nho
     (621/621 symbol trong pool deu co OFI).
  2. `noise_ofi_check` (cung mask, gia tri ngau nhien) tu **THANG\*** (V2) → **NULL tren CA SELECT
     va CONFIRM** (V3): cot nhieu khong con "an ke" hieu ung subset.
  3. Hieu ung candidate giam tu +2.95pp → +1.65pp khi mo pham vi ra toan universe — dung huong
     "mot phan hieu ung cu la confound".
  ⇒ Thiet ke sua cua §0 PREREG (doi PHAM VI, khong doi co che noise) **da lam dung viec no phai lam**.

**(b) `candidate` co thang `noise control` NGOAI CI khong? — Cau tra loi theo DUNG luat da chot:
§4.1b KHONG kich hoat** (noise CONFIRM edge5 CI **chua 0**), nen khong co HARNESS_NGHI_NGO_VAN_CON
va verdict candidate duoc cong bo. Thong tin mo ta THEM (KHONG phai phep thu da pre-register, KHONG
dung de ket luan): khoang cach tam candidate − noise = **+1.96pp**, nhung 2 CI **CO chong lan nhau**
([+0.0062, +0.0276] vs [−0.0148, +0.0079]) ⇒ **KHONG duoc phep noi "ngoai CI"**. Ket luan dung phai
dua tren candidate-vs-`baseline_fresh` (§4.1), khong dua tren so sanh truc tiep candidate-vs-noise.

**(c) Ket luan + buoc tiep theo §5:** verdict = **candidate THANG** (CI khong chua 0, mean > 0) tren
CONFIRM edge5 VA rank-IC, voi noise control SACH va coverage dat. **NHUNG day CHI LA UNG VIEN**:
theo §5 PREREG, ket qua single seed (42) / 1 lan chay chinh **khong du** — theo AGENT_RUNBOOK bay #7,
hieu ung phai **vuot CI multi-seed (>= 3 seed)** truoc khi tin; can **pre-reg RIENG**, **KHONG tich
hop, KHONG deploy**. Executor KHONG tuyen bo GO/NO-GO tong; RESULT chi bao so + verdict tung tieu chi.

## 8. Muc nao BO + ly do (trung thuc ve pham vi thuc thi)

1. **BO VIEC 1 + VIEC 2 (push lai 5+5 kernel build) — LY DO: da xong TRUOC do.** Khi bat dau phien
   nay, `kaggle kernels list` cho thay **ca 10 kernel `ofi-v3-build-s0..s9` DA TON TAI va status
   `complete`** (lastRun 2026-09-24 00:46→05:15, tuc TRUOC khi AMENDMENT-A duoc commit 26/09;
   theo ban goc cua PREREG thi may push khi do la Windows), voi output
   day du. Da **kiem chung doc lap** (khong tin status suong): doc `ofi_build_summary.json` + log cua
   ca 10 qua API ⇒ 630/630 symbol hoan tat, `stopped_early=false`, `n_err` 2, so dong feature
   9,730,284, ts 2021-07-01→2025-12-31; va **`kaggle kernels pull` s0 cho ra code TRUNG KHOP** voi
   template hien tai (khac DUY NHAT 1 dong comment duong dan `docs/` → `docs/prereg/`). ⇒ Push lai
   se ton **~12,8 h (5 kernel) → ~25,6 h (ca 10 kernel) CPU quota** cho **ket qua y het** (du lieu tai
   ve la tat dinh), va co nguy co cham tran 5 session — khong co gia tri khoa hoc. **Khong co bat ky so quyet dinh
   nao (rank-IC/edge5) duoc doc truoc**: AMENDMENT-A noi "chua ton tai bat ky ket qua V3 nao", dieu
   do VAN dung theo nghia §4.1 (chua ai tinh rank-IC/edge5 V3); thu da ton tai chi la INPUT
   (feature parquet + build summary), khong phai ket qua.
2. **BO kernel "remainder"** — khong shard nao `stopped_early` (§1), nen §2 khong kich hoat.
3. **BO `make_shards_v3.py` / `recon_*.py`** — khong chay lai: `ofi_v3_shards.json` da co va khop
   (da doi chieu so symbol tung shard khi sinh kernel).
4. **KHONG cham tran 5 CPU session dong thoi** — truoc khi push da kiem 6 kernel moi nhat cua
   account `chuyendinh`: tat ca `complete` (khong co session nao dang chay) ⇒ chi **1 slot** duoc
   dung (`ofi-v3-train-eval`). Khong gap `Maximum batch CPU session count of 5`.
5. **KHONG push git** (commit tai cho, xem §10). **KHONG chay Java/sim tren Oracle**; **KHONG tai
   aggTrades ve Oracle** (kernel Kaggle tu tai); `systemctl is-active shadow-c3` duoc kiem TRUOC va
   SAU moi dot push (khong dung cham production). Tai ve Oracle chi **~145 MB output nho**
   (1 json + 3 pred parquet + log) de kiem chung doc lap, **don parquet ngay sau khi dung**.

## 9. Gioi han (khong over-claim)

1. Single seed (42), 1 lan chay chinh — khong sweep (dung §6.3 PREREG).
2. Rank-IC chi tren `g1lite` (khong co `g1_replay`).
3. `is_buyer_maker` dien giai ke thua tu PREREG goc §2, khong xac minh doc lap lai.
4. 2021 chi phu 0.2515 (window build bat dau 2021-07) — chu yeu anh huong SELECT (chi tham khao).
5. 2 symbol-thang loi mang (SUSHIUSDT 2024-05, HOOKUSDT 2024-09) ⇒ NaN, ≤ 1% theo §2.
6. Verdict THANG o day KHONG duoc doc la "OFI co tac dung that" — chi la ung vien vuot CI o
   single-seed; multi-seed la dieu kien tin (AGENT_RUNBOOK bay #7).

## 10. File / artifact

- `docs/prereg/PREREG_S1_FREE_OFI_V3_UNIVERSE.md` (AMENDMENT-A, commit `12119de`).
- `research/pipeline/x1/kaggle_ofi_v3/gen_kernels_v3.py`, `gen_train_v3.py` (commit `9253024` —
  them override `OFI_V3_OUT`; mac dinh Windows giu nguyen).
- Kernel build: `chuyendinh/ofi-v3-build-s0..s9` (COMPLETE, `stopped_early=false`).
- Kernel train/eval: `chuyendinh/ofi-v3-train-eval` v1 (COMPLETE 2h13m).
- `ofi_result_v3.json` (so that day du, nguon cua §2/§3/§4/§5/§6) — tai ve Oracle tai
  `/home/ubuntu/ofi_v3/out/` (cung `.log` 35,953 byte). Pred `pred_baseline_fresh.parquet`,
  `pred_ofi_candidate_v2.parquet`, `pred_ofi_noise_v2.parquet` dung de kiem tra §4.2 doc lap.
- `docs/result/RESULT_S1_FREE_OFI.md` + `docs/audit/AUDIT_HARNESS_OFI_2026-09-20.md` — doi chieu V2.
