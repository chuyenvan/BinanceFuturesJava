# PREREG_H1 — phan xu HOLDOUT 2026 (dot DUY NHAT, mot lan, roi niem phong lai)

Viet TRUOC khi chay bat ky sim nao qua 2025-12-31. Khong sua sau khi thay ket qua.
Trang thai: **INPUT chua dung xong** — xem `docs/plan/H1_HOLDOUT_PREP.md`. Pre-reg nay chot
LUAT CHOI de lan chay that khong con cho tuy nghi.

---

## 0. RUI RO — doc TRUOC khi quyet dinh mo seal

1. 🔴 **2026 KHONG phai holdout trinh nguyen o tang gate.** Model gate sinh ra `p15`
   (`wfo_models/fold_*/Model_Regressor_Return15M.onnx`) duoc GHI 2026-08-06, va
   `WFOGateRunner` chay ke hoach fold voi `end=20260701` ngay **2026-08-19** — tuc bo
   feature (33 V3FULL), nhan (`label_oldbasket`), sieu tham so va ca ke hoach fold deu
   duoc CHOT trong luc ket qua 2026 dang nhin thay va dang duoc backtest. Seal chi dat
   ngay **2026-09-01**. Phan "researcher degrees of freedom" nay **khong go lai duoc**.
   => Ket qua 2026 la forward test **co nhiem**, khong phai holdout sach.
2. 🔴 **Fold cuoi TU FIT VAO holdout.** `fold_20` train toi 2026-04-01 roi du bao
   2026Q2 — tuc model cua Q2 da thay Q1 cua chinh holdout. Day la hanh vi WFO/live
   dung chuan, nhung phai ghi ro: sau Q1, holdout khong con "model-naive".
3. 🔴 **Cua so chi 6 THANG, khong phai 8.** Chan cung la feature store gate va Tool1
   (het 2026-07-01), khong phai ticker. Muc 1.
4. 🔴 **~40-45 khoi 72h** => CI rong gap ~2 lan cua so 48 thang. Ket luan phai dua vao
   **RANG BUOC CUNG va DAU**, khong dua vao "co ngoai CI khong".
5. ⚠️ Bins fold 2026 chua co va **nguon G015x26 khong tai lap duoc** — muc 7. Neu buoc
   nay phai dung `g72_train.py` (ho G015_v2) thi ban le trailing 0.29 doi nghia; xem
   `docs/plan/H1_HOLDOUT_PREP.md` muc 4 truoc khi chay.
6. ⚠️ Dia Oracle **11G trong / 194G (95%)**. Dataset WFO ~4.5G. Xoa ngay sau khi chay.

---

## 1. CUA SO — chot 2026-01-01 -> 2026-07-01 (GMT+7), 6 thang, 2 fold

| moc | gia tri |
|---|---|
| bat dau | `1767225600000` = 2026-01-01 00:00 UTC = `HoldoutSeal.SEAL_MS` |
| ket thuc | `1782838800000` = 2026-07-01 00:00 GMT+7 = 2026-06-30 17:00 UTC |
| fold bins | `20260101` (OOS Q1), `20260401` (OOS Q2) — dung 2 fold, span 90d/91d |
| `SIM_END_DATE` | `20260701` |

**Vi sao KHONG di xa hon** (chan cung, do thuc — khong phai chon):

| dau vao | mep | co chan khong |
|---|---|---|
| feature store gate `claudedata/gate_dataset_full.csv.gz` | **1782838800000** (2026-07-01 00:00 GMT+7) | **CHAN** |
| Tool1 `ds_feat15m/features_20260401_to_20260701.t1c.gz` | 2026-07-01 | **CHAN** |
| OI `features_oi_percoin_v1/oi_percoin_20210101_to_20260701.bin.gz` | 2026-07-01 | **CHAN** |
| ticker `tickexport/up26pf/ticker_20260813.bin.gz` | 2026-08-13 | khong chan |
| `label_15m/funding_label_20260701_to_20261001.pb` | 2026-10-01 | khong chan |
| `funding_data` (Aerospike) | 2026-08-05 | khong chan |

=> Ticker toi 2026-08-13 **khong mua them duoc thang nao**: thieu `p15` va thieu feature
Tool1/OI thi khong co bins, khong co gate. **Khong duoc keo `SIM_END_DATE` qua 20260701.**

---

## 2. CONG DAU VAO — phai PASS het truoc khi mo seal

| cong | do gi | tieu chi |
|---|---|---|
| **P1** `p15` | tai tao `predReturn15M` cua mot fold DEV tu feature store + ONNX, doi chieu `claudedata/wfo_gate_pred.csv` | **spearman >= 0.999**. Byte-identity bao RIENG (lam tron `%.8f` cua float32 lam ~5-8% dong lech chu so cuoi — khong phai lech mo hinh) |
| **P2** `CLOSES_1H` | dung lai doan 2025-12 bang dung generator goc, doi chieu file hien co | byte-identical |
| **P3** ledger/featv2 | `feat_v2_h1` cat toi 2024-07-01 == `feat_v2.parquet` (9 cot KEEP); `cand_dev_h1` cat toi T1 cu == `cand_dev.parquet` | bang tuyet doi (`equal_nan`), y het X1 G1/G2 |
| **P4** bins | sha256 **16 fold cu** cua `predwf_map_s1a2_h1/` == muc X1 cua `research/pipeline/BINS_MANIFEST.md` (`bins.sha256 = b87762312620f317...`) | 16/16 trung |
| **P5** parity dataset | build dataset voi `SIM_END_DATE=20251231` roi chay `c3_min` => phai ra dung `X1_C3` | **98,523 equity / 2,058 lenh / md5 printDone `d39da2940dfd815f60772f70517750bf`** |

**P5 FAIL => DUNG.** Dataset builder da vo voi bins moi; moi so 2026 sau do vo nghia.

---

## 3. HAI ARM — dung 2, khong bien the

| arm | profile | khac biet |
|---|---|---|
| **`H1_C3`** | `profiles/h1_c3.properties` (= `x1_c3` doi `WFO_FUNDING_PRED_DIR` sang bins H1) | `SELECTOR_ONLY_ENTRY=1`, `DCA_GRID_WEIGHTS=1,0,0,0`, `DCA_GRID_SCALE=1.5` |
| **`H1_C3_FULL`** | `profiles/h1_c3_full.properties` | `SELECTOR_ONLY_ENTRY=0`, `DCA_GRID_WEIGHTS=1,1,3,8`, `DCA_GRID_SCALE=19.5` |

Moi key con lai giong y `x1_c3` / `x1_c3_full` (16 key `c2b_min` + 3 co `SIM_FIX_B1/B2/B3=true`).
Chay TUAN TU tren Oracle, `TICKER_SOURCE=file` (`configs/sim_dev_file.properties`), neo 60395.

**MOT LAN CHAY. Khong grid, khong sweep, khong "thu them mot muc".** Chay xong seal lai.

---

## 4. CHAM DIEM — bang GIONG NHAU cho ca hai arm

Rate muc lenh (tieu chi that): `n`, `win%`, `TSloss%`, `mean(profit|STOP_MARKET_DONE)`,
`mean(profit|STOP_LOSS_DONE)`, `meanP`, `mean(margin)`.
CI = bootstrap **khoi 72h x1.21** (y het X1/X2/X3). Equity/CAGR bao rieng, **khong phai tieu chi**.

### Rang buoc cung (chot truoc, KHONG duoc ha)

| # | rang buoc | ghi chu |
|---|---|---|
| R1 | `maxDD <= 15%` do tu chuoi equity `b+unP` cuoi ngay | X1: C3 −13.31, FULL −12.46 |
| R2 | **khong THANG nao < −8%** | cua so 6 thang => dung THANG, **khong dung nam, khong dung quy** |
| R3 | `UW` (underwater) — **CHI BAO CAO, khong phai rang buoc** | X1 muc 7 da chung minh nguong 120 ngay khong con dat duoc; 6 thang khong do duoc UW co y nghia |

### Cau hoi theo thu tu

1. **CAU CHINH: arm nao VO rang buoc cung (R1, R2)?** Tra loi truoc moi thu khac.
2. **Cau phu: dau cua `mP|SL` (FULL − C3) co khop 48 thang khong?** X1 do duoc
   **+2.278** [+0.629, +4.175] (rate chat luong DUY NHAT ngoai CI tren 48 thang).
   Chi hoi **DAU**, khong hoi do lon — 6 thang khong du power.
3. Bao ca hai arm tren cung mot bang. Khong de cu baseline moi tu ket qua nay.

⚠️ **Ghi truoc**: ~40-45 khoi 72h => CI rong ~2x so voi 48 thang. **Ky vong 0-1 rate ngoai CI.**
"Khong rate nao ngoai CI" la ket qua **null co thong tin**, khong phai that bai cua phep do.

---

## 5. LENH MO SEAL — chinh xac

`HoldoutSeal.java`: `SEAL_MS = 1767225600000`, `UNSEAL_PHRASE = "I_UNDERSTAND_THIS_BURNS_HOLDOUT_2026"`.
Diem chot: `WfoDataset.export` (`trimMap` tren market/pred/funding) va
`SimulatorMarketLevelTicker1MStopLoss.main` (`clampEnd` tren `endTime`), va `SimulatorForcedSeller`.
Thieu env => moi thu tu dong clamp ve 2025-12-31 va log `*** HOLDOUT SEAL ***`.

```bash
export HOLDOUT_UNSEAL=I_UNDERSTAND_THIS_BURNS_HOLDOUT_2026
```

Lenh day du: `docs/plan/H1_HOLDOUT_PREP.md` muc 7. Log PHAI co dong
`!!!!!!!! HOLDOUT_UNSEAL DUNG ... LAN NAY TINH VAO LEDGER HOLDOUT. !!!!!!!!`
o CA hai cho (export dataset + sim). Khong thay dong do = seal chua mo = so ra la 2025, vut di.

Sau khi chay xong: `unset HOLDOUT_UNSEAL`, ghi ket qua vao `docs/H1_RESULT.md`, va
ghi vao ledger holdout la **da tieu mot lan duy nhat**.

---

## 6. DU DOAN GHI TRUOC (cua agent chuan bi, 2026-09-06)

Ghi de sau nay cham duoc minh sai o dau — y het X1 muc 10.2.

| # | du doan | co so |
|---|---|---|
| 1 | `H1_C3` co **n = 380-520 lenh** trong 6 thang | 2025 = 784 lenh/nam va universe con no; 6 thang ~ 400-500 |
| 2 | `win%` **82-86%**, `TSloss%` **14-17%** — tuc **KHONG xau di** | X1 muc 10.2: hai rate nay on dinh xuyen 4 nam (83.3/88.6/85.7/84.7) |
| 3 | `mean(profit\|SL)` **−24 den −34** (xau hon 48 thang) | X1 muc 10.3: do sau lenh thua dang dan sau (−15.52 → −28.94 tu 2024 sang 2025) |
| 4 | `mP\|SL` cua FULL − C3 mang **dau DUONG** — xac suat ~65%; **ngoai CI ~25%** | X1: +2.278 tren 48 thang; 6 thang CI rong ~2x |
| 5 | **R1 (maxDD <= 15%)**: `H1_C3` PASS ~60%, `H1_C3_FULL` PASS ~65% | X1: −13.31 / −12.46, cach tran 15% khong nhieu |
| 6 | **R2 (khong thang nao < −8%)**: it nhat MOT arm VO — xac suat ~45% | quy xau nhat cua X1 la −4.75; nhung do la QUY, thang le bien dong lon hon |
| 7 | So rate chat luong ngoai CI: **0 hoac 1** | n_eff ~40-45 khoi |
| 8 | DCA leg 2+ cua FULL **duong** trong 2026H1 | X1 muc 6: duong o 2022 (+2,758) va 2025 (+4,813); 2025 la regime gan nhat |

Toi **khong** du doan equity/CAGR (khong phai tieu chi, `sd(dCAGR)` cua cua so 6 thang chua co so do).

---

## 7. HAI DIEU CHUA GIAI QUYET — phai chot TRUOC khi chay

1. 🔴 **`CLOSES_1H.bin` khong co generator.** Toan bo file tren dia va trong git deu la
   READER. File hien co het 2026-01-01 00:00. Khong dung lai duoc => `feat_v2` va
   `cand_dev` khong mo rong duoc sang 2026 => khong co bins => khong co H1.
   Chi tiet + hai duong di: `docs/plan/H1_HOLDOUT_PREP.md` muc 3.
2. 🔴 **Bins fold 2026 phai lay P(win) tu dau?** `build_map.py` ap thu hang S1 len
   multiset P(win) cua `predwf_G015x26`; fold `20260101`/`20260401` cua bo do **da bi
   xoa** (seal manifest muc 1) va `predwf_G015x26` **khong tai lap duoc**
   (`docs/result/G015CUT_RESULT.md`, X1 muc 1.3a). Train moi bang `g72_train.py` = ho
   **G015_v2**, hieu chuan KHAC. Ban le trailing `symbolPred <= 0.29` la nguong
   **TUYET DOI** tren chinh P(win) do, va X3 muc 3 do duoc cac gia tri trong mot tick
   bam rat sat nhau (0.3547/0.3586/0.3613) => doi hieu chuan se doi `%STRONG` cua 2026
   vi mot ly do **khong lien quan gi den 2026**.
   => **Truoc khi chay H1 phai lam phep do hieu chuan (chi DEV, hop le)**: train
   `g72_train.py` tai cutoff `20251001` roi so phan phoi P(win) va `%<=0.29` voi
   `predwf_G015x26/predict_wf_20251001.bin`. Lech => H1 **khong duoc chay** tren bins
   tron nguon; phai dua len user quyet.

**Ca hai deu la quyet dinh cua user, khong phai cua agent.**
