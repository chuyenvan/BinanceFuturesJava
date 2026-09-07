# PREREG_5MGRID -- train lai S1 + net015 o luoi 5 phut (GPU), thay luoi 15 phut hien hanh

Viet va commit TRUOC khi chay bat ky buoc train/build nao. Khong sua sau khi thay ket qua.
Bat nguon tu yeu cau user: "khong can train chi can predict lai theo luoi 5m" -> phat hien
S1 chi co 1/16 fold co model da luu (con lai chi con output, khong con model) -> user quyet
dinh: "train GPU chay nhanh ma train va pred full di".

## 0. Du lieu goc -- TIN TOT, khong phai xay tu dau
`ds_feat5m` (Tool1 f0-f39, 24 file, 2021-01->2026-07, sinh 2026-08-13) va `ds_label5m`
(funding_label *.pb, cung 24 file, cung ngay sinh) **DA CO SAN, moi, khong mo coi that**.
Kiem doc lap bang `tool1_col.meta()`/`read_tool1()`: `ds_feat5m` 100% `ts%300000==0`,
dung gap 3 lan so dong so voi `ds_feat15m` cung ky (9,167,283 vs 3,057,538 dong quy
2025Q1) -- la du lieu 5 phut THAT, khong phai noi suy tu 15 phut. `wfo_gate_pred.csv`
(gate p15) da o **luoi 1 PHUT** san (2,500,260 dong ~5 nam) -- khong can dong gi vao gate.

## 1. Pham vi -- CAI GI doi, CAI GI KHONG doi
- **Gate p15**: GIU NGUYEN, khong train lai, khong doi luoi. Dung truc tiep
  `wfo_gate_pred.csv` o do phan giai von co (khong downsample ve 15 phut nhu `ledger.py`
  dang lam qua `Q=900000`).
- **`feat_v2.parquet` (9 feature KEEP cua S1)**: GIU NGUYEN, khong rebuild. No tinh tu
  nen gio (`CLOSES_1H.bin`), join vao ledger qua `ts_h=(ts//3600000)*3600000` -- co che
  merge-theo-gio nay hoat dong dung voi BAT KY luoi tick nao (khong can luoi 5 phut cho
  chinh no). He qua PHAI NEU RO: feature S1 van chi moi toi gio, dieu duoc them o 5 phut
  la **bat kip coin nao vua du dieu kien ung vien giua 2 moc 15 phut cu**, KHONG PHAI
  "thong tin moi hon".
- **net015 (value model)**: TRAIN LAI toan bo tren `ds_feat5m` + 5 OI feature (da tu nhien
  5 phut), `GRID_MS=5*60*1000` thay vi 15*60*1000. Feature nay MOI THAT o 5 phut.
- **S1 (selector)**: TRAIN LAI 16 fold WFO tren `cand_dev` MOI (`Q=300000`), lan nay
  **luu model MOI fold** (sua loi thieu cua lan truoc chi luu 1/16 fold).
- **`ENTRY_GRID_MIN` (Java, hien hardcode 15L)**: THAM SO HOA thanh config key
  `SIM_ENTRY_GRID_MIN` (mac dinh 15 -- HANH VI CU KHONG DOI neu khong dat key nay o bat ky
  profile nao khac). Chi doi tren profile luoi-5-phut moi.

## 2. Rui ro / lo hong -- doc TRUOC
1. 🔴 **Day la thay doi CODE (them 1 config key Java) + REFACTOR script train (them
   `device=cuda`, them `--save-model` moi fold, doi nguon du lieu)** -- khac han K12
   (chi doi 1 dong profile). Rui ro hoi quy cao hon nhieu.
2. 🔴 **Chua co doi chung "5 phut" nao tung chay** -- khong the parity-check ket qua CUOI
   voi bat ky so cu nao. Thay vao do BAT BUOC cong parity TRUNG GIAN (muc 3): pipeline moi
   (GPU + save-model + code moi) phai TAI LAP DUNG ket qua 15-phut hien co TRUOC KHI duoc
   tin o 5 phut.
3. ⚠️ **G015x26 bins cu (`predwf_G015x26`) khong dung duoc o 5 phut** (train o
   `GRID_MS=15min`, khong co du lieu tai cac moc 5/10 phut le). Ledger moi se BO cot
   `p_g015` (chi la cot chan doan `gate_dyn_ok`, KHONG duoc `s1_rank.py` dung de train) --
   xac nhan bang code: `s1_rank.py` chi doc `g1lite`/`rel5` tu `cand_dev.parquet`, khong
   doc `p_g015`.
4. ⚠️ **`n` moi se ~3x** (moi tick 15 phut cu -> 3 tick 5 phut) nhung **KHONG PHAI 3x
   thong tin doc lap** -- 2/3 tick moi chia se CUNG gia tri feature S1 (feature moi toi
   gio) voi tick 15-phut lien ke. CI khoi-72h van dung DUNG vi don vi la KHOI THOI GIAN,
   khong phai n lenh -- nhung phai neu ro trong bao cao de khong bi doc nham la "them
   bang chung doc lap x3".
5. ⚠️ Dia Oracle 94% day (13G free luc do 2026-09-07). `ds_feat5m`+`ds_label5m` da chiem
   cho tren dia roi (khong can tai ban them) nhung cac artifact trung gian (`feat_v2` GIU
   nguyen nen khong ton dia moi; `cand_dev_5m.parquet`, `predwf_map_s1a2_5m/` 16 file) can
   dia tam -- uoc ~2-3G, phai xoa sau khi build bins xong.
6. ⚠️ Train tren Kaggle GPU (khong phai Oracle) -- theo dung `docs/BENCH_DEVICE.md`: GPU
   duoc phep cho TRAIN nhung PHAI bao CI da-seed (>=3 seed) khi so sanh hieu ung, KHONG
   dung nguong cu `spearman>=0.999` (da bo). Nhung day la THAY DOI KIEN TRUC (luoi tick),
   khong phai so sanh hieu ung nho -- CI da-seed la PHU, khong phai dieu kien chinh.
7. 18G+ compute tren Kaggle (16 fold S1 x GPU + 16-18 fold net015 x GPU) -- uoc thoi
   gian dua tren G015/S1 lan truoc (~30'/model o G5) x 2 mo hinh x ~16 fold GPU nhanh hon
   CPU dang ke -- se do that va bao lai, KHONG cam ket truoc con so gio.

## 3. Thiet ke -- cac buoc theo thu tu, MOI buoc co cong rieng

### Buoc A -- cong PARITY pipeline moi o luoi 15 phut (BAT BUOC truoc, khong duoc bo qua)
Chay LAI `ledger.py build` (Q=900000 khong doi) + `s1_rank.py` (them `device=cuda`,
`--save-model` moi fold) + `g015x26_train.py` (them `device=cuda`, GRID_MS khong doi) +
`build_map.py` tren Kaggle GPU. So sanh output voi ban CPU cu:
- S1: spearman rank-IC per-fold >= 0.98 (nguong seed-noise da do o `BENCH_DEVICE.md`,
  KHONG dung `spearman>=0.999` da bo).
- net015: lap lai chinh cong da dung o `G3_X26_RECOVERY`/`G015_RECIPE` (so p(win) tren
  tap OOS, spearman + top-8 overlap).
- bins moi (`predwf_map_s1a2_15m_gpu`) chay qua `run_x1_sim.sh`-style, PHAI byte-identical
  hoac gan-nhu voi `X1_C3_FULL_PARITY` da co (`docs/K12_RESULT.md`: equity 111,428,
  n=2,266). Sai lech ngoai nhieu seed-noise da biet => DUNG, dieu tra, KHONG chay 5 phut.

### Buoc B -- luoi 5 phut that
Chi sau khi Buoc A PASS:
1. `ledger.py build` voi `Q=300000`, nguon nhan `ds_label5m` thay `label_15m`, BO merge
   `p_g015` (khong can, xem muc 2.3).
2. `g015x26_train.py` voi `GRID_MS=5*60*1000`, doc `ds_feat5m` thay `ds_feat15m`, GPU,
   train du 16-18 fold WFO nhu cu, luu MOI fold.
3. `s1_rank.py` tren `cand_dev` moi (5 phut), GPU, luu MOI fold (16 file model).
4. `build_map.py` dung 2 bo model moi -> `predwf_map_s1a2_5m/` (16 file, luoi 5 phut).
5. Java: them config key `SIM_ENTRY_GRID_MIN` (mac dinh 15, KHONG doi hanh vi khi khong
   dat) tai `DetectEntrySignal2TradeNormal.java:842`. Build jar tren repo Windows (bat
   buoc, vi `PrivateConfig` that). Profile moi: `x1_c3_full_5m.properties` = ban sao
   `x1_c3_full.properties` + `WFO_FUNDING_PRED_DIR=.../predwf_map_s1a2_5m` +
   `SIM_ENTRY_GRID_MIN=5`. `SELECTOR_RANK_TOPK=8` GIU NGUYEN (dung yeu cau: K=8 luoi 5m).
6. Chay sim (`ExportWfoDataset` + `SimulatorMarketLevelTicker1MStopLoss`) nhu quy trinh
   `run_x1_sim.sh`, dataset build rieng (`wfo_ds_5m`), XOA NGAY sau khi cham diem.

## 4. Tieu chi -- rate + CI khoi 72h x1.21 (giu khung PREREG_X1/K12)
So `X1_C3_FULL_5M` (K=8, luoi 5 phut) voi `X1_C3_FULL_PARITY` (K=8, luoi 15 phut, so cu
111,428/2,266 hoac ban chay lai o Buoc A neu can doi chung sat jar/code-sha):
`TSloss%` . `win%` . `mean(profit|SM)` . `mean(profit|SL)` . `meanP`. Tren TOAN cua so VA
tung nam. `n` la bien KIEM SOAT (se ~x3 nhu neu o muc 2.4, KHONG dung lam bang chung).
CI: bootstrap khoi 72h x1.21.

## 5. Rang buoc cung -- SO VOI K=8/15-phut (khong dung so tuyet doi cu, giu logic K12 muc 5)
- `maxDD` khong vuot qua +3pp tuyet doi so voi doi chung, tung nam
- `underwater` khong dai hon +30 ngay so voi doi chung, tung nam
- khong nam nao am (ca hai arm)
- khong quy nao vi pham -5% MOI ma doi chung khong co

## 6. Quy tac quyet dinh -- chot TRUOC khi thay so
Luoi 5 phut thay luoi 15 phut lam mac dinh C3_FULL CHI KHI:
1. Buoc A (cong parity pipeline moi) PASS -- khong PASS thi KHONG duoc doc Buoc B; VA
2. thang >=2 rate cung huong ngoai CI tren toan cua so; VA
3. PASS toan bo rang buoc cung muc 5 o MOI nam.
Khong dat (1) => DUNG TOAN BO, bao cao loi pipeline, khong suy dien gi ve luoi 5 phut.
Khong dat (2) hoac (3) (nhung (1) PASS) => NULL, giu luoi 15 phut, nhung GIU LAI cong cu
(script GPU + `SIM_ENTRY_GRID_MIN`) vi da xac nhan dung, chi ket luan "luoi 5 phut khong
sinh loi tai thoi diem nay" -- khong xoa code.

## 7. Equity -- khong phai tieu chi, bao rieng

## 8. Pham vi
DEV only (`SIM_END_DATE=20251231`). Khong dung 2026 (`HoldoutSeal`). Gate p15 KHONG doi.
