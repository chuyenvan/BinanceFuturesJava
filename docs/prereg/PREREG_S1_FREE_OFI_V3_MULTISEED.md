# PREREG_S1_FREE_OFI_V3_MULTISEED — OFI V3 (630 symbol): xac nhan multi-seed >= 3 (AGENT_RUNBOOK bay #7)

Chot **TRUOC khi push kernel** va **TRUOC khi doc bat ky so multi-seed nao**. File nay PHAI duoc
commit truoc `docs/RESULT_S1_FREE_OFI_V3_MULTISEED.md`; nguoc lai ket qua VO HIEU.

Ke thua: `docs/prereg/PREREG_S1_FREE_OFI_V3_UNIVERSE.md` (gom **AMENDMENT-A**) + ket qua seed 42
`docs/RESULT_S1_FREE_OFI_V3_UNIVERSE.md` (commit `c5c9faf`). Vong nay **KHONG** doi feature, harness,
fold, CI, pham vi, mask NaN, luat §4.1/§4.2 goc — **CHI doi `random_state` cua XGBoost** (muc 4).

## 0. Vi sao co vong nay (bay #7)

`docs/runbooks/AGENT_RUNBOOK.md` muc 2 bay #7: *"hieu ung phai vuot **CI multi-seed (>= 3 seed)** do
trong **cung moi truong**; chua co CI thi chua duoc ket luan"*. Vong V3 goc moi chay **seed 42**, 1 lan
=> theo §5 PREREG goc, `candidate` CONFIRM Δedge5 **+0,016501** [+0,006199, +0,027633] **CHI LA UNG
VIEN**, khong duoc tich hop/deploy. Vong nay do **nen nhieu seed** trong **CUNG moi truong (Kaggle CPU,
`enable_gpu=false`)** de xem hieu ung co vuot CI multi-seed khong.

## 1. SEED — danh sach CHOT

| nhom | seed | vai tro | duoc coi la bang chung moi? |
|---|---|---|---|
| doi chieu | **42** | tai lap + moc doi chieu (da biet ket qua, da cong bo) | **KHONG** — khai bao RO, khong bao gio dem vao "so seed moi" |
| bang chung CHINH | **43** | moi hoan toan, chua tung chay | CO |
| bang chung CHINH | **44** | moi hoan toan, chua tung chay | CO |
| bang chung CHINH | **45** | moi hoan toan, chua tung chay | CO |

- **K = 3** (so seed MOI, khong tinh seed 42) => **`inflate(K) = sqrt(2 ln 3) = 1,482304`**.
  Moi CI trong vong nay bao quanh tam bang he so nay (thay cho 1,177410 cua vong goc, luc do
  k=2 la so COT MOI). Quy uoc nay chot TRUOC khi thay so.
- Seed 42 tai lap lai trong CHINH vong nay (cung code, cung input, Kaggle CPU) — dung lam
  **kiem tra toan ven moi truong** (§5 C6). Neu seed 42 KHONG tai lap so da cong bo => **DUNG**,
  bao MASTER, KHONG cong bo verdict multi-seed (moi truong da troi).
- Moi seed chay 1 kernel RIENG (4 kernel: s42, s43, s44, s45) de **song song** (tran 5 CPU session
  theo ACCOUNT `chuyendinh`) va tranh rui ro hard limit 12h/kernel. Uoc tinh ~2,2 h/seed (vong goc
  2 h 13 m) => wall ~2,5 h.

## 2. KHONG doi (cung) — CHI doi seed

Giu NGUYEN tuyet doi so voi `ofi_train_eval_v3.py` (commit `9253024`):

1. **Du lieu/feature**: dataset `chuyendinh/s1-featv2-x1-20260919` + 10 kernel build
   `chuyendinh/ofi-v3-build-s0..s9` (COMPLETE tu 2026-09-24, **KHONG push lai**) + frozen baseline
   `chuyendinh/s1-baseline18-det-n1-20260919`. **KHONG** build lai feature, **KHONG** tai aggTrades
   ve Oracle.
2. **3 bien the** trong cung kernel: `baseline_fresh` (KEEP9) · `candidate` (KEEP9 + `ofi_1h` +
   `aggr_buy_ratio_1h`) · `noise_ofi_check` (KEEP9 + `noise_ofi_check`, **CUNG NaN-mask** voi `ofi_1h`).
3. **Model/harness**: XGBRanker rank:ndcg, 300 cay, depth 4, lr 0,05, subsample/colsample 0,8, mcw 50,
   `n_jobs=1`, `hist`, topk/8 cap; `rel5`; purge 72h; `CUTS18`; `assert tr.ts.max() < c`;
   SELECT = fold 0-9 (chi tham khao), **CONFIRM = fold 10-17**; edge5 = top-5 score thap nhat tru
   trung binh tick; rank-IC = spearman(-score, `g1lite`), tick >= 10 dong.
4. **CI**: paired block-bootstrap block 72h, **NREP 2000**, **bootstrap SEED 20260919** (CO DINH —
   de moi seed duoc so sanh tren CUNG mot lich resample, tuc paired theo seed).
5. **Noise RNG**: `default_rng(20260920)` **CO DINH** cho moi seed (cung gia tri nhieu, cung mask;
   chi model seed doi) — de phep kiem "noise NULL" la phep kiem SACH ve nhieu, khong bi lan voi
   doi gia tri nhieu.
6. **Doi DUY NHAT**: `random_state` cua `make_model` = seed cua kernel (42/43/44/45). Khong doi
   bat ky tham so nao khac; khong doi hyperparameter, khong sweep.

**Thay doi OUTPUT-ONLY (khong doi bat ky tinh toan/so nao):** moi kernel ghi them 1 file nho
`ms_diffs_s<seed>.parquet` = chuoi diff THEO TICK (`candidate`-`baseline_fresh` va
`noise`-`baseline_fresh`, cho edge5 va rank-IC, + `fold`) — CHI de tinh **pooled CI** tren Oracle
bang dung ham `block_ci_diff` (NREP 2000, seed 20260919). Day thuan tuy la **duong ghi output**,
tuong tu tinh than AMENDMENT-A; khong cham thuat toan/feature/harness.

## 3. LUAT QUYET DINH (chot TRUOC, dinh luong)

Ky hieu: `S = {43, 44, 45}`. Voi moi `s in S`:
- `d5(s)` = CONFIRM mean Δedge5 cua `candidate` vs `baseline_fresh` (cung seed s); `CI5(s)` = CI
  block-72h NREP 2000 seed 20260919 × `inflate(3)`.
- `dIC(s)`, `CIIC(s)` = tuong tu cho Δrank-IC.
- `n5(s)`, `CIn5(s)` = tuong tu cho `noise_ofi_check` vs `baseline_fresh`.

Tieu chi:

- **(C1) NOISE PHAI NULL o MOI seed** (ke ca 42): `CIn5(s)` **chua 0** voi moi `s in {42,43,44,45}`.
  - Neu **bat ky** seed nao co `CIn5(s)` **KHONG chua 0** => **HARNESS NGHI NGO** (cung tinh than
    §4.1b goc mo rong sang multi-seed): **KHONG cong bo verdict**, bao MASTER, **KHONG** chay them.
- **(C2) POOLED**: `d5_pool` = trung binh THEO TICK cua `d5(s)` tren `s in S` (3 seed dung CHUNG tap
  tick/fold — tap OOS co dinh boi CUTS18), roi ap dung **CUNG** `block_ci_diff` (block 72h, NREP 2000,
  seed 20260919, k=3). Yeu cau: `mean > 0` **VA** CI khong chua 0.
- **(C3) NHAT QUAN THEO SEED**: (i) **>= 2/3** seed moi co `d5(s) > 0`; (ii) **>= 2/3** seed moi co
  `CI5(s)` khong chua 0. Bao CA HAI con so, khong chi bao 1.
- **(C4) RANK-IC song song**: bao `dIC(s)`, `CIIC(s)` tung seed + `dIC_pool` + CI pooled. Neu
  edge5 PASS ma rank-IC pooled khong chua 0 theo huong nguoc => bao **MAU THUAN** (ghi ro, khong
  xoa); neu rank-IC pooled khong chua 0 cung chieu => cuong hoa.
- **(C5) SANITY §4.2 o MOI seed**: so tick OOS moi fold = baseline cung seed; `score` khong NaN/Inf;
  `assert tr.ts.max() < c` (purge 72h) khong bao loi; tap `ts` OOS cua `candidate`/`noise` ==
  `baseline_fresh`; `len` pred 3 bien the bang nhau; mask `noise_ofi_check.notna() == ofi_1h.notna()`.
  Fail bat ky muc nao => DUNG.
- **(C6) TOAN VEN MOI TRUONG (seed 42 tai lap)**: kernel s42 phai tai lap so da cong bo:
  `candidate_vs_fresh.confirm_edge5_ci.mean == +0,016500961035490036` (dung |lech| <= 1e-9),
  `confirm_rankic_ci.mean == +0,0019546861051446362`, `baseline_fresh_edge5_all_pct ==
  15,209467887878418`, `fresh_vs_frozen` Δ = **0 tuyet doi**. Neu lech => moi truong/input da troi
  => **DUNG**, bao MASTER, KHONG cong bo verdict.

### 3.1 VERDICT (chot truoc)

- **PASS** (multi-seed xac nhan) <=> (C1) **VA** (C2) **VA** (C3) **VA** (C5) **VA** (C6).
- **FAIL — HARNESS_NGHI_NGO** neu (C1) truot.
- **FAIL — dong truc OFI** neu (C1) sach nhung (C2) hoac (C3) truot. Bao ro muc nao truot:
  - `C2` truot (pooled CI chua 0): hieu ung seed-42 khong tai lap duoc tren 3 seed moi => **dong
    truc OFI** (OFI tho 1h, k=3, universe 630 — KHONG co bang chung multi-seed). Neu pooled mean
    <= 0 => dong truc theo nghia "khong co hieu ung duong".
  - `C3` truot (chi 1/3 seed duong, hoac chi 1/3 seed co CI khong chua 0): hieu ung **KHONG ON DINH
    theo seed** => dong truc OFI nhu ket luan vong nay; ghi ro so seed duong/CI-khac-0.
- **LUU Y ve "(C2)+(C3)"**: neu pooled CI khong chua 0 NHUNG chi 1/3 seed co CI rieng khong chua 0
  (hieu ung tap trung o 1 seed) => **KHONG duoc cong bo PASS**; bao "khong on dinh theo seed".
- Executor **KHONG** tuyen bo GO/NO-GO tong; RESULT chi bao so + verdict theo dung luat nay.

## 4. Hieu chinh 1 muc cua de bai (chot TRUOC, khong phai sua luat sau khi thay so)

De bai vong nay ghi *"`baseline_fresh` vs `baseline_frozen` = 0 o MOI seed"*. Muc nay **bat kha thi
ve mat logic** theo thiet ke da chot: `baseline_frozen` la parquet CO DINH (train seed 42, session
2026-09-19); `baseline_fresh` duoc train LAI trong moi kernel voi `random_state` = seed cua kernel.
Vay:

- **seed 42**: `baseline_fresh` vs `baseline_frozen` **PHAI = 0 tuyet doi** (kiem tra determinism
  cross-session) — day la yeu cau goc, giu nguyen (§3 C6).
- **seed 43/44/45**: `!= 0` **LA DUONG NHIEN** (khac model seed). Do luong nay duoc bao cao nhu
  **"nen nhieu seed"** (seed-noise floor) va la thong tin MO TA, **KHONG** phai tieu chi pass/fail.
  Ky vong: |Δ| nho hon nhieu so voi hieu ung (`d5`), de hieu ung khong bi nhan chim trong nhieu seed.

Muc dich cua de bai (khong ghep so tu 2 moi truong, khong de drift lam gia hieu ung) duoc bao dam
day du boi **C6** (seed 42 tai lap byte-muc) + **C5** (sanity moi seed) + nguyen tac "cung moi truong
Kaggle CPU". Hieu chinh nay chot TRUOC khi chay/chua doc bat ky so multi-seed nao.

## 5. Rang buoc Oracle (khong doi)

- **KHONG chay Java/sim tren Oracle**; shadow-c3 dang LIVE PAPER => khong cham production.
- **KHONG tai aggTrades ve Oracle**; `df -h /` da dung 93% (16G trong) => chi tai output NHO
  (json + log + `ms_diffs_s<seed>.parquet` vai tram KB/kernel), **don ngay** sau khi dung.
- Kiem `df -h /` + `free -g` + `systemctl is-active shadow-c3` TRUOC/SAU moi dot push.
- Tran **5 CPU session dong thoi** theo ACCOUNT => 4 kernel song song la an toan (da kiem khong
  co session nao dang chay truoc khi push).
- **KHONG push git** (commit tai cho). **KHONG tich hop, KHONG ONNX/LIVE** (2 cot moi = 47 cot =
  dung duong LIVE, can owner duyet rieng).

## 6. Ngoai pham vi

Smoothing OFI / cua so khac / doi hyperparameter / doi fold / doi pham vi universe / du lieu 2026 /
chay bat ky job nao tren Oracle ngoai 3 lenh kiem tra tai nguyen / `git push` / tich hop / deploy.

## 7. Thu tu

1. Commit file nay + tooling sinh kernel multi-seed — **TRUOC** khi push kernel.
2. Push 4 kernel `chuyendinh/ofi-v3-ms-s42|s43|s44|s45` (song song, <= 5 slot).
3. Theo doi bang background + `process poll` timeout dai (**KHONG** tight loop, **KHONG** `pgrep -af`).
4. Tai `ofi_result_v3_ms_s<seed>.json` + `ms_diffs_s<seed>.parquet` + log (output nho), tinh pooled CI
   bang dung `block_ci_diff` (NREP 2000, seed 20260919, k=3).
5. Viet `docs/RESULT_S1_FREE_OFI_V3_MULTISEED.md` theo dung §3, commit, **khong push**.
