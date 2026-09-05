# PREREG_T2 — luong DAY DU (big_down + DCA) x selector C2b vs selector cu

Viet TRUOC khi chay, commit TRUOC khi chay, **khong sua sau khi thay so**. Null co tinh thong tin.
DEV 2022-01-01..2024-06-30 (`SIM_END_DATE=20240630`). **Khong chay VAL.**
jar `target/binance-java-sdk-1.2.4.jar`, code `acd9469`.
Khao sat co hoc day du: `docs/T2_FULLFLOW.md muc 1` (viet truoc pre-reg nay).

## 0. RUI RO / LO HONG — doc truoc khi doc so

1. **Leg BIG_DOWN BO QUA gate AI** (`Simulator...:817`). Gate la thanh phan load-bearing da
   chung minh (`RUNBOOK muc 4`). Bat BIG_DOWN = mo mot cua vao lenh **khong qua gate**, dung
   luc thi truong sap. Neu ket qua xau, do la giai thich co hoc san co — khong duoc coi la
   "selector kem".
2. **`NUMBER_ENTRY_EACH_SIGNAL=2` va `MS_DOWN_BIG_AVG=-0.03157` la hardcode Java**, khong nam
   trong profile nao. Bat BIG_DOWN hoi sinh ca hai. T2 **khong quet** chung; moi so o day gan
   voi dung hai gia tri do.
3. **`T2_full_old` khac `T2_full_c2b` o HAI bien**: bins (`predwf_G015_v2` vs `predwf_map_s1a2`)
   **va** gate calib (`SIM_MIN_MOMENTUM_15M` 0.014052 vs 0.008). Hieu chuan gate la bat buoc vi
   `symbolPred` cua hai bins khong cung thang do (`C2B_SPEC muc 2.3`); khong hieu chuan thi phep
   so bien thanh "doi selector + doi tan suat". Ghi nhan la sai lech co y.
4. **DCA doi `mean(margin)`** (`W1_SWEEP muc 7`: 971 -> 497 khi tong trong so giu 1.0). Moi cai
   thien maxDD/underwater cua chan co DCA **co the chi la size nho hon**. Sizing **khong do duoc
   tren DEV** (`RUNBOOK muc 4`). Bat buoc bao kem `total margin deployed` va `mean(margin)`.
5. `E[max nhieu]` equity voi N=4: `2.57 * sqrt(2 ln 4)` = **4.28pp CAGR**. Equity bao muc rieng,
   dan nhan "khong phai tieu chi".
6. **Khong de cu ung vien baseline moi tu batch nay.** Day la phep tra loi mot cau hoi cua user,
   khong phai vong tuyen chon.

## 1. Bon chan (toi da 4 run, quyet dinh truoc)

| tag | profile | bins | gate | `SELECTOR_ONLY_ENTRY` | `DCA_GRID_WEIGHTS` | dataset |
|---|---|---|---|---|---|---|
| `T2_c2b_ref` | `c2b_min` | `predwf_map_s1a2` | 0.008 | 1 (BIG_DOWN tat) | `1,0,0,0` (DCA tat) | `wfo_ds_clean` |
| `T2_full_c2b` | `t2_full_c2b` | `predwf_map_s1a2` | 0.008 | **0** | **`1,1,3,8`** | `wfo_ds_clean` |
| `T2_full_c2b_noDCA` | `t2_full_nodca` | `predwf_map_s1a2` | 0.008 | **0** | `1,0,0,0` | `wfo_ds_clean` |
| `T2_full_old` | `t2_full_old` | **`predwf_G015_v2`** | **0.014052** | **0** | **`1,1,3,8`** | `wfo_ds_t2old` (build rieng) |

- `T2_c2b_ref` **la neo parity**: phai ra `b:60390`, `970` lenh, md5 `printDone.csv` =
  `8f7afdfb27b15f5b6d4c886700def93c`. Lech => DUNG batch, khong doc tiep.
- `wfo_ds_clean` da co san va `manifest.txt` ghi `fundingPredDir=/home/ubuntu/predwf_map_s1a2`
  => dung chung cho 3 chan dau (bay #13: bins chi anh huong luc `ExportWfoDataset`).
- `wfo_ds_t2old` build rieng cho `T2_full_old`, **`rm -rf` ngay sau khi sim xong** (dia 14G free).
- Sim chay **tren Oracle** (1 slot JVM, tuan tu). Khong day Kaggle: 3/4 chan can dataset da build
  san o Oracle, chan thu 4 doi bins nen Kaggle vo hieu (bay #13) — day len se ton them mot vong
  `dataset_create_version` 1.7GB ma khong nhanh hon.

## 2. PRIMARY — rate (tieu chi quyet dinh)

Do tren `storage/printDone.csv` cua tung chan:

1. `TSloss%` = ti le lenh dong bang `STOP_LOSS_DONE` (= time-stop 168h)
2. `win%`
3. `mean(profit | STOP_MARKET_DONE)`
4. `mean(profit | STOP_LOSS_DONE)`
5. `n` (so lenh)
6. `mean(margin)`
7. **`total margin deployed`** (= sum margin) — de tach confound sizing
8. **phan bo status day du**: liet ke MOI gia tri status xuat hien, khong gia dinh chi co
   `STOP_MARKET_DONE`/`STOP_LOSS_DONE` (luong day du co the sinh status khac)

## 3. Rang buoc cung (loai truc tiep, khong thuong luong)

`maxDD <= 15%` · `underwater <= 120 ngay` · khong nam am · khong quy < -5% · `n >= 600`.

## 4. Quy tac quyet dinh (viet truoc)

- **Cau hoi cua user** = so `T2_full_c2b` **voi** `T2_full_old`: cung luong, chi khac selector.
- `T2_c2b_ref` chi lam **tham chieu**, khong phai doi thu.
- `T2_full_c2b_noDCA` chi de **tach dong gop** BIG_DOWN vs DCA.
- **"KHAC nhau"** khi **>= 2 rate PRIMARY lech CUNG HUONG va ngoai CI bootstrap khoi 72h x1.21**
  (cung cong da dung o T1). Duoi nguong do = **KHONG PHAN BIET DUOC**, bao null.
- Mot chan **FAIL rang buoc cung** thi bi loai bat ke rate — nhung van bao day du rate cua no.
- **Khong chon chan nao theo equity.**

## 5. Ket qua co the co va da chuan bi cach doc

- `T2_full_*` co n lon hon nhieu `T2_c2b_ref` (D0_full lich su: 1688 lenh vs 970) => moi so sanh
  rate phai la **rate**, khong phai tong.
- Neu `T2_full_c2b` ~ `T2_full_old` tren rate: ket luan la **selector khong phan biet duoc trong
  luong day du** — khop voi `RUNBOOK muc 4` ("selector ladder CHUA THIET LAP") va `CI_REAUDIT #5`.
- Neu ca hai FAIL rang buoc cung: ket luan la **luong day du khong dung duoc tren DEV o cau hinh
  hien tai**, va cau hoi selector tro thanh vo nghia trong khung do.

## 6. Ha tang / ve sinh

1 slot JVM (`pgrep java` rong truoc moi run), `df -h /` > 5G truoc khi build, `rm -rf $DS` sau
`T2_full_old`. Khong dung `SIM_*` env kem `TRADING_PROFILE` (bay #2). Cham diem bang
`research/analysis/qret_ladder.py`, `/home/ubuntu/java/fsrun/qret.py`, `/home/ubuntu/java/fsrun/ev.sh`.
