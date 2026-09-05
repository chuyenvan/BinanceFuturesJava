# PREREG_X1 — keo dai cua so do tu 30 thang len 48 thang (2022-01-01 -> 2025-12-31)

Commit TRUOC khi train/chay bat ky thu gi. Khong sua file nay sau khi thay ket qua.
Nhiem vu goc: phan biet `C3` vs `C3_FULL` — `n_eff ~ 908` khoi 72h la tuong chan
(`docs/F4_TIMING.md`). Chi DO DAI LICH SU mua duoc power, do min hon thi khong.

User da quyet: **2024-07 -> 2026-01 (xua la VAL) nhap vao DEV mo rong. Khong con VAL sach.
Validate cuoi cung = forward test.** Khong hoi lai.

---

## 0. RUI RO — doc TRUOC

1. 🔴 **Khong con holdout nao trong 2021-2025.** Sau X1, moi ket luan deu la in-sample
   theo nghia rong. Cai duy nhat con lai la 2026 (`HoldoutSeal.SEAL_MS = 2026-01-01`,
   du lieu pred/gate 2026 da bi XOA khoi Oracle). KHONG duoc mo.
2. 🔴 **Dia con 14G / 194G (93%).** Duong di can ~8.3G tam thoi. Moi buoc phai `df` truoc,
   xoa dataset tam ngay sau khi dung xong. Duoi 5G free thi DUNG.
3. ⚠️ **`n_eff` moi van nho.** 48 thang / 3 ngay = 487 khoi 72h tren truc thoi gian,
   nhung `n_eff` cua bai toan la so khoi CO lenh; xem muc 7.
4. ⚠️ Equity/CAGR **khong phai tieu chi** (`sd(dCAGR)` = 2.57pp, chua do lai cho cua so moi).

---

## 1. KET QUA AUDIT DU LIEU — chan B **KHONG DI**, chi lam chan F

### 1.1 Chan F (forward) 2024-07-01 -> 2025-12-31 — **DI DUOC, khong co blocker**

| dau vao | pham vi do thuc | du cho 2025-12-31? |
|---|---|---|
| `claudedata/wfo_gate_pred.csv` (p15, dinh nghia POOL) | 2021-03-31 17:00 -> **2025-12-31 23:59** (2,500,260 dong) | **VUA DU — het mep** |
| Aerospike `test/ai_pred_market_gate_wfo` | 2,500,260 object = **cung mep** | vua du |
| Tool1 `ds_feat15m/features_*.t1c.gz` (f0..f39) | 2021-01 -> **2026-07** (23 file) | du |
| `label_15m/funding_label_*.pb` | 2021-01 -> **2026-10** (24 file) | du |
| `claudedata/oi/oi_percoin_full.bin` (5 OI feat) | 2021-01-01 -> **2026-06-30**, 140,924,110 rec | du |
| `java/fsrun/CLOSES_1H.bin` (nguon featv2) | 2021-01-01 01:00 -> **2026-01-01 00:00**, 10,322,386 rec | **vua du** |
| `claudedata/predwf_G015x26/predict_wf_*.bin` | **16 fold**, `20220101`..`20251001`, ts 2021-12-31 17:00 -> **2025-12-31 16:45** (GMT+7) | **du, dung 16 fold quarter** |
| ticker `kaggle_data_hpo/daily/ticker_*.bin.gz` | 2021-01-01 -> 2026-07-01 (2,008 file); **1,461/1,461 ngay 2022-01-01..2025-12-31** | du, khong thieu ngay |
| `selector_pred_out/symbol_map.csv` (781 sym) | phu **100%** symbol xuat hien trong bins 2025 (554/554) va label 2025Q4 (554/554) | du |
| `java/exchange_info_pin.json` | 892 symbol, mtime 2026-09-03, la ban dump exchangeInfo (`ClientSingleton`), **KHONG can regenerate** | du |
| `HoldoutSeal.clampEnd` | SEAL = 2026-01-01; `SIM_END_DATE=20251231` **duoi seal** | khong can `HOLDOUT_UNSEAL` |

**Tool1 f0..f39 cho G015 lay tu dau**: file `.t1c.gz` tren dia (`tool1_col.read_tool1`),
KHONG phai Aerospike set. Da phu 2026-07. Day la blocker kha di duoc kiem dau tien — **khong phai blocker.**

**Cai PHAI rebuild** (vi ba artifact trung gian bi ghim tai 2024-07-01):

| artifact | mep hien tai | can |
|---|---|---|
| `featv2/feat_v2.parquet` | `T_END=1719792000000` (2024-07-01), 4,884,420 dong | rebuild toi 2026-01-01 |
| `ledger/cand_dev.parquet` | `T1=2024-07-01`, 1,220,490 dong, max 2024-06-24 | rebuild toi 2026-01-01 |
| `ledger/pred_s1a2.parquet` + `predwf_map_s1a2/` | 10 fold | 16 fold |

### 1.2 Chan B (backward) 2021-07-01 -> 2021-12-31 — **KHONG DI. Ly do cung, khong phai "kho".**

Recipe `D1_DATA_AUDIT §B` doi **cat 2 OI feature khoi S1 KEEP** (con 7) vi OI chi co
1 coin/thang toi 2021-11. Nhung `KEEP` la tham so **TOAN CUC** cua `s1_rank.py`: doi no thi
**MOI fold doi**, ke ca 10 fold 2022-2024.

=> Bins `predwf_map_s1a2` fold cu se **KHONG con byte-identical**, nen:
- **cong parity noi bo cua X1 (X1_C3 cat toi 2024-06-30 == C3 = 68,278 / 961) FAIL theo dinh nghia**;
- so 2022-2024 moi **khong con so sanh duoc** voi `C3`/`C3_FULL` — tuc mat chinh cai neo
  ma nhiem vu nay dung de phan biet 2 the.

Khong the vua co chan B (7 feature) vua giu cong parity (9 feature). Hai cai loai tru nhau.

Cong voi 2 ly do phu (deu do thuc, khong phai suy doan):
- **G015 co 5 OI feature, va OI THUC SU bat dau 2021-12** (D1 §A.5: 242 cung khong co
  2021-01..2021-11; khong copy ve duoc). Fold `20210701` se train tren ma tran 45 cot ma
  5 cot ~100% NaN, roi cham OOS 2021Q3 cung ~100% NaN. XGBoost **nhan** NaN, nhung day la
  **dut gay cau truc ma tran feature**, khong phai dich phan bo: model fold 2021 khong cung
  ho uoc luong voi 15 fold con lai. Ghep chung vao mot bang "rate theo nam" la sai.
- Loi ich nho: 6 thang / 54 = 11% do dai, va la 6 thang **it tick nhat** (`D1 §B.0`:
  2021-07 chi 13,200 dong ledger, 2021-08 10,163 — so voi 2022-01 tro di hang tram nghin).

**=> Cua so X1 = 48 thang: 2022-01-01 -> 2025-12-31.** Chan B bi bo, ghi ro o day, khong ep.

### 1.3 Sai lech co y so voi de bai — **G015_v2 KHONG duoc dung lam nguon cua bins X1**

De bai yeu cau bins moi sinh tu `g72_train.py` (= `predwf_G015_v2`, tai lap byte-identical).
Nhung **`build_map.py` doc `claudedata/predwf_G015x26/`**, va bins dang deploy
(`predwf_map_s1a2`, sinh ra C3 = 68,278) chinh la **S1-rank ap len phan phoi P(win) cua
G015x26**, KHONG phai cua G015_v2. Do thuc: `predwf_map_s1a2/*.bin` co so ban ghi va kich
thuoc trung khop tung file voi `predwf_G015x26/*.bin`.

=> Neu doi nguon sang `predwf_G015_v2`, **10 bins fold cu doi** => cong byte-identical FAIL
va `C3` khong con la neo. Vi vay:

- **X1 dung `predwf_G015x26` lam nguon cho CA 16 fold.** Nhat quan giua fold cu va fold moi,
  giu duoc ca hai cong.
- **No ky thuat duoc ghi nhan, KHONG duoc giau**: `predwf_G015x26` la bins **khong tai lap
  duoc** (`docs/G015CUT_RESULT.md`). Muon chuyen sang G015_v2 thi phai **do lai TOAN BO
  baseline** (C3 se doi so) — do la mot job khac, khong phai job nay.
- `g72_train.py` (G015_v2) **khong duoc dung trong X1**; do do khong ton 7.2G scratch
  `xall.f32` va vai gio CPU. Ghi ro de nguoi sau khong tuong X1 da tai lap G015.

### 1.4 Sai lech co y thu hai — **chay 2 arm tren Oracle + `TICKER_SOURCE=file`, khong phai Kaggle**

De bai yeu cau 2 arm chay song song tren Kaggle. Nhung theo `KAGGLE_SIM §6`, bins **khong di
qua duong Kaggle**: kernel chi chay sim tren **dataset DA BUILD**. Nen duong Kaggle doi hoi
upload dataset moi (~4.2G) + ticker 2024h2/2025 (~3.6G) = ~7.8G bang thong, chi de doi lay
~15 phut wall-clock.

`KAGGLE_SIM §1` da do thuc: **Kaggle == Oracle + `TICKER_SOURCE=file` byte-for-byte**
(md5 `printDone.csv` trung). Ma `C3` (= `C3_BASE`, md5 `38be0cb3195984e1000e61d9cdef54da`)
va `C3_FULL` (md5 `85083e4612d7879e53ba4947c20954b7`) deu chay tren **Kaggle**, tuc duong `file`.

=> X1 chay 2 arm **tuan tu tren Oracle voi `TICKER_SOURCE=file`** (neo 60395, dung ho voi C3).
Oracle dang rong (`pgrep java` = rong, 4 core / 23G RAM). Uoc 2 x ~12 phut.
Neu Oracle ban hoac dia khong du, moi quay lai duong Kaggle.

---

## 2. PROVENANCE + CONG BYTE-IDENTICAL (chay TRUOC khi cham diem)

Moi artifact X1 sinh boi `research/pipeline/x1/*.py` = ban SAO cua script goc, chi THEM
tham so hoa qua env (mac dinh = hanh vi cu). Seed 42, CPU, `n_jobs=4`, xgboost cua Oracle.
Artifact cu **KHONG bi ghi de** (duong dan moi co hau to `_x1`).

| # | artifact X1 | script | cong (phai PASS truoc khi di tiep) |
|---|---|---|---|
| G1 | `featv2/feat_v2_x1.parquet` | `x1_feat_v2_build.py` (`T_END=2026-01-01`) | 9 cot KEEP cua S1, moi dong `ts <= 2024-07-01`: **bang tuyet doi** `feat_v2.parquet` (so sanh theo (ts,sym), `equal_nan`) |
| G2 | `ledger/cand_dev_x1.parquet` | `x1_ledger.py` (`T1=2026-01-01`) | moi dong `ts < 2024-07-01`: **byte-identical** `cand_dev.parquet` (cung thu tu, cung gia tri) |
| G3 | `ledger/pred_s1a2x1.parquet` | `x1_s1_rank.py` (16 cutoff) | 10 fold cu: `score` **bang tuyet doi** `pred_s1a2.parquet` (774,270 dong) |
| G4 | `predwf_map_s1a2_x1/` (16 bin) | `x1_build_map.py` | 10 bin cu: **sha256 trung** bang `BINS_MANIFEST.md` muc 2 |
| G5 | dataset `wfo_ds_x1` | `ExportWfoDataset` | `manifest.txt`: `foldCount=16`, `maxFoldSpanDays<=91`, `md5` 10 file cu trung manifest cu |

**Bat ky cong nao FAIL => DUNG, khong chay sim, bao cao cho nao lech.**

sha256 tung bin moi ghi vao `research/pipeline/BINS_MANIFEST.md` (them muc "X1 — 16 fold").

Cutoff S1 + map (16 fold, quarter-aligned):
`20220101 20220401 20220701 20221001 20230101 20230401 20230701 20231001`
`20240101 20240401 20240701 20241001 20250101 20250401 20250701 20251001`

`s1_rank.py` co 2 cho phu thuoc SO fold: `if i in (0,5,9)` (shuffle control) va log theo nam.
X1 dat shuffle control tai `(0, 7, 15)` va them cot 2025 vao log. **Hai cho nay khong anh
huong `pred` cua fold khac** (shuffle control train model rieng `m2`, khong ghi vao `preds`),
nen G3 van la cong hop le. Neu chung anh huong => G3 se FAIL va ta se biet.

---

## 3. HAI ARM

| arm | profile | khac `c3_min` | `SIM_END_DATE` |
|---|---|---|---|
| `X1_C3` | `profiles/x1_c3.properties` | chi `WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2_x1` | `20251231` |
| `X1_C3_FULL` | `profiles/x1_c3_full.properties` | + `SELECTOR_ONLY_ENTRY=0`, `DCA_GRID_WEIGHTS=1,1,3,8`, `DCA_GRID_SCALE=19.5` | `20251231` |

`TIME_RUN=20220101` (khong doi, trong `configs/sim_dev.properties`). `TICKER_SOURCE=file`.
`EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json`. Jar hien tai cua HEAD.

### 3.1 CONG PARITY NOI BO (bat buoc, truoc khi doc bat ky so nao)

`printDone.csv` cua `X1_C3` **cat toi `end <= 2024-06-30`** phai trung `C3_BASE/printDone.csv`
(961 lenh, md5 `38be0cb3195984e1000e61d9cdef54da`) **tung byte**; tuong tu `X1_C3_FULL` vs
`C3_FULL` (1,059 lenh, md5 `85083e4612d7879e53ba4947c20954b7`).
Ly do phai trung: bins 10 fold cu khong doi + sim tien theo thoi gian + trang thai tai moi
tick chi phu thuoc qua khu. **Khong trung => DUNG**, khong duoc "giai thich" cho lech.

---

## 4. TIEU CHI — rate + CI khoi 72h x1.21

Tren TOAN cua so 2022-01..2025-12 **VA** tach rieng tung nam 2022 / 2023 / 2024 / 2025:

`TSloss%` · `win%` · `mean(profit|SM)` · `mean(profit|SL)` · `mean(margin)` ·
so leg DCA theo nam · **PnL cua leg 2+ theo nam** · `n`.

CI: bootstrap khoi 72h, nhan **1.21** (he so `docs/PREREG_CI.md` / `F4_TIMING.md`).
`n` va `mean(margin)` la bien **KIEM SOAT/co hoc**, khong dung lam bang chung chat luong.

## 5. RANG BUOC CUNG — tren TUNG nam (2022, 2023, 2024, 2025)

- `maxDD <= 15%` (do tu chuoi equity `b+unP` cuoi ngay, KHONG dung `unProfitMin/35000`)
- `underwater <= 120 ngay`
- khong nam nao am
- khong quy nao `< -5%`

`C3` da sat `-4.8%` o 2024Q2. Neu 2025 vi pham => **BAO CAO, KHONG TUNE.**

## 6. QUY TAC QUYET DINH — chot TRUOC khi thay so

`C3_FULL` duoc nhan lam baseline **chi khi ca 3 dieu sau dung**:

1. thang `C3` **>= 2 rate cung huong, ngoai CI**, tren toan cua so 48 thang; **VA**
2. DCA co **PnL leg 2+ duong o >= 2 nam KHAC NHAU** (khong chi 2022); **VA**
3. PASS toan bo rang buoc cung muc 5 o **moi** nam.

Neu DCA chi duong o 2022 => ket luan **"an FTX mot lan"**, **GIU `C3`**.
Neu (1) dat ma (2) khong dat => giu `C3`, ghi ro rate nao thang.
Null co tinh thong tin — bao cao null.

## 7. `n_eff` va equity — bao rieng, dan nhan

- `n_eff` cu = **908** khoi 72h. X1 se bao `n_eff` moi = so khoi 72h CO it nhat 1 lenh
  trong 2022-01..2025-12, va ty le `sqrt(n_eff_moi / 908)` = he so thu hep CI ky vong.
- Equity/CAGR/maxDD **bao rieng, dan nhan "khong phai tieu chi"**. `sd(dCAGR)` chua do cho
  cua so moi — se ghi "khong tim thay so do", khong tai su dung 2.57pp cua cua so cu.

## 8. DU DOAN GHI TRUOC (bat buoc, de kiem chinh minh)

Ghi 2026-09-05, truoc khi co bat ky so nao cua 2024H2-2025:

1. **`C3` KHONG giu duoc `TSloss ~15%` / `win ~85%` trong 2025.** Toi doan `TSloss%` 2025
   **xau hon** 2022-2024, khoang **17-21%**, va `win%` **81-84%**. Ly do co hoc, khong phai
   linh cam: universe no **gap ~2.2 lan** trong dung giai doan nay (coin co gia trong
   `CLOSES_1H`: 265 @2024-07 -> **591 @2025-12**), trong khi `SELECTOR_RANK_TOPK=8` **khong
   doi** => ty le duoc chon tut tu ~3.0% xuong ~1.4% pool, va phan duoi cua pool (coin moi
   niem yet, lich su ngan, `age_days` nho) **chua tung co trong train fold cu**.
2. **`n` (so lenh) cua `X1_C3` tang manh o 2025** — doan **>= 1.5 lan** so lenh/nam cua 2024,
   vi pool rong hon va gate `p15` khong phu thuoc universe size.
3. **DCA cua `C3_FULL` se KHONG duong o 2023 va 2024.** Doan no duong o **2022** (FTX) va
   **co the** o 2025 neu 2025 co mot quy sap; neu 2025 khong sap thi ket qua se la
   "duong 1/4 nam" => theo muc 6 => **GIU `C3`**. Toi dat xac suat `C3_FULL` duoc nhan
   lam baseline **~30%**.
4. **Rang buoc cung**: doan `C3` **PASS** 2022/2023/2024 va **rui ro nhat o 2025Q1**
   (chu ky sap 2025-02) — kha nang co mot quy `< -5%` la ~40%.
5. `n_eff` moi doan roi vao **1,300-1,600** khoi 72h => CI hep lai chi ~**1.2-1.3 lan**,
   KHONG du de bien mot hieu ung 1-rate thanh 2-rate. Tuc: **X1 co the van tra ve null**,
   va do la ket qua hop le.

## 9. CAM

Khong push. Khong xoa file cua user (dataset tam do X1 tu tao thi xoa). Khong GPU.
Khong tune sau khi thay so. Python dung `logging`. Khong doan — blocker thi DUNG dung cho.
