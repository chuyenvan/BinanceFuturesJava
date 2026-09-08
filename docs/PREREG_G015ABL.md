# PREREG_G015ABL -- ro soat 45 feature net015, bo dan feature "proxy-thoi-gian" de xem co overfit khong

Viet TRUOC khi chay bat ky fold train nao. Khong sua sau khi thay ket qua.

## 0. Xuat phat -- sua lai tien de truoc khi lam
Yeu cau goc: "ra soat 45 feature cua net015, bo cac feature de overfit nhu date, year, month...".
**Kiem tra thuc te: KHONG co feature nao ten/dang date, year, month trong 45 feature cua net015**
(xem `docs/FEAT40_LOOKAHEAD.md` Cau 2 -- 40/40 feature Tool1 f0..f39 da co cong thuc + file:line,
khong feature nao la lich/calendar; + 5 feature OI la snapshot/ty le, cung khong phai lich).

Rui ro GAN NHAT voi dieu nguoi dung lo ngai, da duoc chinh tai lieu do tu phat hien va gan co
(khong phai suy dien moi cua phien nay):
- **f23 `fundingPersistence`**: dem so ky funding lien tiep cung dau tren lich su **expanding**
  (khong purge duoc vi la ban chat WFO). `FEAT40_LOOKAHEAD.md` Cau 2 muc "2 khoan khong phai
  lookahead nhung phai ghi de khong troi", muc 2: *"no hoat dong nhu mot proxy cho THOI GIAN...
  nen coi la rui ro tong quat hoa, khong phai ro ri"*. Bang chung phan phoi (`FEAT40_LOOKAHEAD.md`
  muc 4.2): mean 22.95 (2022Q1) -> 223.91 (2024Q1), dmean/std = **+3.780** (LON NHAT trong 40 feature).
- Cum lien quan (cung ho funding-expanding-stat, cung do lech phan phoi lon thu 2-3-4 trong bang
  muc 4.2): **f18 `basketFundingAvg`** (+2.935), **f21 `fundingPercentileCoin`** (+2.092),
  **f22 `fundingZCoin`** (+1.409). Ca 3 deu tinh tren thong ke `(-inf, t]` expanding (xem bang Cau 2),
  cung co che voi f23.

Khong feature nao khac trong bang muc 4.2 co do lech phan phoi dang ke (con lai la ty le/rank co
gioi han [0,1] hoac momentum/volatility co tinh dung).

## 1. Thiet ke -- BO DAN, khong bo 1 cuc (theo dung yeu cau)
Train lai **net015 toan bo** (khong phai predict-only -- doi so cot = doi `num_feature`, XGBoost
can train lai) tren **luoi 15 phut goc** (KHONG dung luoi 5 phut, tranh nguy co OOM da gap o
`docs/RESULT_5MGRID.md`). Dung nguyen `research/pipeline/g015_net_train.py` (duong build feature
memory-light da duoc xac minh byte-identical, xem `docs/G3_X26_RECOVERY.md` muc 6.1) + them **1**
tham so moi `--drop-cols` (danh sach chi so cot 0-44, cach nhau dau phay) ap dung **CHI** o buoc
slice `Xtr`/`Xoo` truoc `clf.fit`/`clf.predict_proba` -- khong dung `build_matrix` (giu nguyen
duong doc-Tool1-va-OI da qua leak-audit). Mac dinh `--drop-cols=""` -> hanh vi y het ban goc
(kiem tra hoi quy: chay fold 20240101 voi `--drop-cols=""` phai cho `sha_bin` **giong het**
model_f8 hien co truoc khi tin ket qua Stage 1/2).

- **Stage 0 (`G015ABL0`, CONTROL -- BAT BUOC, phat hien SAU KHI viet ban dau cua file nay)**:
  retrain FULL 45 feature (`--drop-cols=""`), CUNG seed=42, CUNG may Kaggle GPU, CUNG script
  `g015_net_train.py` dung cho Stage 1/2. **Ly do bat buoc**: doi chieu `docs/G4_RECIPE_C4.md`
  muc 2 -- ban retrain-f8 (tai dung, seed 42, GPU) vs model GOC (san xuat, trainer da mat) chi
  dat `spearman = 0.985997`, **nam DUNG BANG** nen nhieu tu chinh su khac biet SEED tren CUNG may
  (0.984931, "s42 vs s43"). Tuc la: **ban retrain-lai-tu-dau, du khong doi feature nao, DA TU NHIEN
  lech khoi model san xuat mot khoang bang dung nen nhieu multi-seed cua chinh XGBoost**
  (subsample=0.8, colsample_bytree=0.8 -- ngau nhien theo thiet ke). Neu so Stage1/2 THANG voi
  `X1_C3_FULL_PARITY` (xay tren model GOC), khong the biet hieu ung do BO FEATURE hay do
  RETRAIN-NOISE von co. **Theo dung tien le da lap `docs/BENCH_DEVICE.md` muc 7.4** ("hieu ung phai
  vuot CI multi-seed do trong CUNG moi truong"): phai co doi chung retrain CUNG moi truong.
  => **Stage 1 va Stage 2 so VOI Stage 0 (khong so truc tiep voi X1_C3_FULL_PARITY)**.
  `X1_C3_FULL_PARITY` chi dung phu de bao cao Stage 0 tu no lech bao nhieu (thong tin nen, khong
  phai tieu chi quyet dinh).
- **Stage 1** (`G015ABL1`): bo rieng `f23` (chi so cot 23) -> 44 feature, CUNG seed/moi truong voi
  Stage 0. Day la buoc bo dau tien, it nhat, co bang chung manh nhat (do lech phan phoi lon nhat +
  da duoc chinh tai lieu goi ten la "time proxy").
- **Stage 2** (`G015ABL2`, CHI chay neu Stage 1 khong gay hong nghiem trong -- xem muc 3): bo them
  ca cum `f18, f21, f22` cung f23 -> 41 feature, cung Stage 0/1.
- Khong bo further sau Stage 2 trong pre-reg nay; neu Stage 2 co tin hieu ro rang can dieu tra them
  thi viet pre-reg moi, khong tune tiep tren pre-reg nay.

## 2. Quy trinh moi stage
1. Train 18 fold (`--fold all --device cuda`) tren Kaggle GPU (dataset da co san: `funding-tool1-15m`,
   `funding-label-15m`, `funding-oi-percoin`, `sel1m-code` -- khong upload lai). Uoc thoi gian ~52
   phut/stage (dua tren log kernel goc `selector-15mtr-pred15-net015-gpu.log`: 3108s cho 18 fold).
   Stage 0/1/2 chay TUAN TU (1 kernel GPU tai 1 thoi diem theo quota Kaggle) -> tong ~2.6 gio GPU
   + 3 lan chay downstream (build_map + sim), moi lan ~15-20 phut Oracle.
2. Pull 18 file `predict_wf_<cutoff>.bin` + `net_train_summary.json` ve Oracle.
3. `x1_build_map.py` KHONG doi (S1 selector khong doi -- chi net015 doi), tro `X1_G015_DIR` toi
   thu muc bins moi cua stage, dung LAI S1 15-phut goc (`predwf_map_s1a2_x1`) lam nen combine.
4. Profile moi: sao chep `x1_c3_full.properties`, doi DUY NHAT
   `WFO_FUNDING_PRED_DIR=.../predwf_map_s1a2_x1_ablN`.
5. `ExportWfoDataset` + `SimulatorMarketLevelTicker1MStopLoss` (luoi 15 phut, `TICKER_SOURCE=file`
   khop `X1_C3_FULL_PARITY`) -> `X1_C3_G015ABL1` / `X1_C3_G015ABL2`.
6. `research/analysis/x1_rates.py X1_C3_FULL_PARITY X1_C3_G015ABLn` -- **doi chung y het** dung cho
   K12 va 5MGRID (equity 111,428 / n=2,266 / maxDD -12.46% / UW 227 ngay).
7. Xoa dataset WFO tam ngay sau khi cham diem xong (dia Oracle dang cang, hien ~9GB free).

## 3. Tieu chi -- dung KHUNG da dung cho K12/5MGRID (khong doi lai)
- Toan cua so 48 thang VA tung nam: rate + CI khoi-72h x1.21 (5 rate: n(kiem soat), win%,
  TSloss%, mP|SM, mP|SL, meanP, mMargin(kiem soat)).
- Rang buoc cung §5 kieu K12/5MGRID (so RELATIVE voi X1_C3_FULL_PARITY, tung nam): maxDD khong
  qua +3pp, underwater khong qua +30 ngay, khong nam nao am, khong quy nao vi pham -5% ma doi
  chung khong vi pham.
- **Quy tac quyet dinh moi stage (so VOI Stage 0, khong so voi X1_C3_FULL_PARITY)**: thang >=2
  rate cung huong ngoai CI toan cua so VA pass toan bo rang buoc cung moi nam (Stage N so Stage 0)
  => bo feature do THAY THE Stage 0 lam net015 moi. Khong dat => NULL, giu Stage 0 (= 45-feature,
  ban retrain moi nhat) hoac model san xuat hien hanh (tuy quyet dinh rieng), GIU LAI model/code
  cua stage do (khong xoa) de tham khao, khong suy dien them.
- **Cong hoi quy Stage 0 (thay the "sha_bin giong het" da SAI o ban dau)**: fold 20240101 cua
  Stage 0 so voi `model_f8_4h.json` san xuat qua spearman -- ky vong roi vao dai **[0.98, 0.99]**
  (khop nen nhieu multi-seed da do o `docs/G4_RECIPE_C4.md` muc 2: 0.984931-0.986678). Ngoai dai
  nay (vd < 0.97) => nghi ngo patch `--drop-cols` hoac moi truong Kaggle da doi, DUNG dieu tra
  truoc khi tin Stage 1/2.
- **Dieu kien dung som Stage 2**: neu Stage 1 vi pham rang buoc cung (so Stage 0) o >=3/4 nam
  (nang hon ca 5MGRID) HOAC hong cong hoi quy Stage 0 -> DUNG, bao cao loi, khong chay Stage 2.

## 4. Rui ro / luu y
1. Model goc `claudedata/predwf_G015/model_f{0..17}_4h.json` (18 file, dang dung san xuat) **KHONG
   duoc ghi de**. Moi stage ghi vao thu muc rieng (`g4/net015_ablN_out/`).
2. `--drop-cols` chi doi INPUT cua XGBoost, khong doi nhan/split/purge -- giu nguyen toan bo phan
   da qua leak-audit trong `FEAT40_LOOKAHEAD.md`.
3. S1 (selector) khong doi trong thi nghiem nay -- chi co net015 (value model) bi ablate. Neu ket
   qua NULL o ca 2 stage, khong ket luan gi ve S1.
4. Day la retrain THAT (khong phai predict-only nhu 5MGRID) nen KHONG co rui ro OOM kieu 5-phut
   (van luoi 15 phut, duong build_matrix nguyen ven da chay on tren Kaggle GPU nhieu lan).
5. Equity/CAGR khong phai tieu chi (luat cung AGENT_RUNBOOK #3).
