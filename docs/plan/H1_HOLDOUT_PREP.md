# H1_HOLDOUT_PREP — dung INPUT cho holdout 2026 (KHONG mo seal, KHONG chay sim 2026)

Pre-reg: `docs/prereg/PREREG_H1.md`. Nhiem vu cua dot nay la **chuan bi dau vao roi DUNG**.
Khong dat `HOLDOUT_UNSEAL`, khong chay sim nao co `SIM_END_DATE > 20251231`,
khong doc/in bat ky outcome 2026 nao. Mo seal la quyet dinh cua user, mot lan.

**Trang thai: 1/5 cong PASS, 2 blocker cung.** Chi tiet duoi day.

---

## 0. TOM TAT — rui ro truoc

| # | viec | trang thai |
|---|---|---|
| 1 | `p15` (`wfo_gate_pred.csv`) cho 2026 | ✅ **XONG** — `claudedata/wfo_gate_pred_2026_H1.csv`, cong P1 **PASS** |
| 2 | `CLOSES_1H.bin` 2026 | 🔴 **BLOCKER** — **khong ton tai generator** o bat ky dau |
| 3 | `featv2` + `cand_dev` toi 2026 | ⛔ chan boi (2) |
| 4 | bins S1 + G015 fold 2026 | 🔴 **BLOCKER thiet ke** — nguon `predwf_G015x26` da bi xoa VA khong tai lap duoc |
| 5 | `BINS_MANIFEST` muc H1 | ⛔ chan boi (4) |
| 6 | parity dataset `SIM_END_DATE=20251231` | ⛔ chan boi (4) |
| 7 | `docs/prereg/PREREG_H1.md` | ✅ **XONG** |

🔴 **Rui ro lon nhat KHONG phai la hai blocker tren, ma la cai nay:**
**2026 khong con la holdout sach o tang gate.** Model gate sinh `p15` duoc ghi
**2026-08-06**, va `WFOGateRunner` chay ke hoach fold voi `end=20260701` ngay
**2026-08-19** — tuc feature/nhan/sieu tham so/ke hoach fold deu duoc chot **trong luc
ket qua 2026 dang nhin thay va dang duoc backtest**. Seal chi dat **2026-09-01**.
Phan nhiem nay khong go lai duoc bang bat ky thao tac du lieu nao.

---

## 1. `p15` SINH TU DAU — va co leak khong

### 1.1 Sinh tu dau: **OUTPUT cua mot model da train**, KHONG phai tinh thuan tu gia

Chuoi: `WFOGateRunner` (Java, `ai_ml/features/export/gate/`) dieu phoi; `ExportGateDataset`
replay Aerospike `market_data_object` -> 33 feature **market-level** V3FULL (1 vector/phut)
+ nhan `label_oldbasket`; moi fold goi `ml/gate/train_gate_fold.py`
(`XGBRegressor` `max_depth=4 n_estimators=150 lr=0.05 subsample=0.8 colsample=0.8
min_child_weight=10 seed=42`) -> ONNX -> `OnnxInferenceManager` predict doan OOS ->
ghi `claudedata/wfo_gate_pred.csv` (`timestamp,predReturn15M,predRisk4H`).
`LoadWfoGatePredTool` nap CSV do vao Aerospike set `ai_pred_market_gate_wfo`.

**`p15` = `predReturn15M` = du bao cua model gate.** Khong phai gia, khong phai momentum tho.

Ke hoach fold (do tu `/home/ubuntu/gate24h_run.log`, chay 2026-08-19): expanding,
`TRAIN_ANCHOR=20210101`, `minTrainMonths=3`, `oosMonths=3`, `end=20260701`, **21 fold**.
Cutoff parse bang `Utils.sdfFile` = **GMT+7**, nen moi moc fold la 00:00 GMT+7 = 17:00 UTC hom truoc.

| fold | train | OOS |
|---|---|---|
| `fold_12` | .. 2024-04-01 | 2024-04-01 -> 2024-07-01 |
| `fold_18` | .. 2025-10-01 | 2025-10-01 -> **2026-01-01** |
| `fold_19` | .. 2026-01-01 | **2026-01-01 -> 2026-04-01** |
| `fold_20` | .. 2026-04-01 | **2026-04-01 -> 2026-07-01** |

### 1.2 Leak — bon phat hien, ghi het

1. ✅ **Cau truc WFO sach**: train `< cutoff − purge`, predict `[cutoff, cutoff+3m)`;
   `GATE_PURGE_MS = LABEL_HORIZON_MS = 15 phut` (nhan nhin toi +15m). `fold_19` (OOS 2026Q1)
   train **chi toi 2025-12-31** => **KHONG leak** vao Q1.
2. ⚠️ **`fold_20` tu fit vao holdout**: train toi 2026-04-01 roi du bao 2026Q2 — model cua
   Q2 **da thay Q1 cua chinh holdout**. Dung chuan WFO/live, nhung sau Q1 holdout **khong
   con model-naive**. Phai ghi trong bao cao ket qua.
3. 🔴 **Phoi nhiem truoc seal (khong go lai duoc)** — muc 0 o tren. Day la leak that su,
   thuoc loai "researcher degrees of freedom", khong phai leak thoi gian.
4. 🔴 **`predRisk4H` la truong RO RI, nhung DA CHET.**
   - `ExportGateDataset` javadoc: *"KHONG co predRisk4H — truong do la output cua model TINH
     train batch full range (ro ri), da bo khoi pipeline gate."*
   - `AIRejectFilter` dong 103-104: *"chi con nhanh MOM15. Nhanh RISK (DD4H/predRisk4H) da bo
     han 2026-08-08: predRisk4H khong con model dung sau."*
   - Set nguon `ai_pred_market_full_basket_v2` (**2,819,841 object**) **KHONG bi seal dung toi**
     (seal_as.py chi xoa 10 set `ai_pred_market_gate_*` + `gate_dev`) => 2026 cua no con nguyen.
   - => Trong file 2026 moi sinh, `predRisk4H` ghi **0**. Vo hai voi quyet dinh; chi doi byte
     cua cot 3 trong `pred.bin` cho cac dong 2026.
5. ⚠️ **Lo hong seal phat hien duoc**: `/home/ubuntu/claudedata/wfo_gate_pred.csv.bak_20260711_2333`
   (66,413,570 B, 2026-07-11) **khong nam trong `_SEALED_2026_MANIFEST.txt` muc 2** => van con
   nguyen dong 2026 cua doi gate CU. Khong pha ket qua (p15 la INPUT, khong phai outcome),
   nhung nen ghi vao manifest cho sach so.

### 1.3 CONG P1 — tai tao `p15` cua DEV: **PASS theo spearman, KHONG byte-identical**

Cach lam (khong can replay Aerospike): feature store `claudedata/gate_dataset_full.csv.gz`
(do chinh `ExportGateDataset` xuat, **2,889,624 dong, 2021-01-01 -> 2026-07-01 00:00 GMT+7**)
+ ONNX `wfo_models/fold_<k>/` -> `onnxruntime` (CPU) -> doi chieu `wfo_gate_pred.csv`.
Script: `research/pipeline/h1/h1_p15_repro.py`.

| cua so (GMT+7) | fold | n | **spearman** | chuoi `%.8f` trung | dong lech THAT (`\|d\|>1e-6`) |
|---|---|---|---|---|---|
| 2024-04-01 -> 2024-07-01 | 12 | 131,040 | **1.000000** | 128,178 (97.82%) | 46 (0.0351%) |
| 2025-10-01 -> 2026-01-01 | 18 | 132,480 | **1.000000** | 122,872 (92.75%) | 21 (0.0159%) |

**Bao ro cai nao**: cong **spearman >= 0.999 PASS** (dat 1.000000 ca hai fold).
**Byte-identical KHONG dat** (92.75% / 97.82%).

Phan du **khong phai lech mo hinh**: phan bo `|d|` co `p50 = 2.54e-09`, `p90 = 4.77e-09`,
`p99 = 7.72e-09` — dung muc lam tron chu so thu 8 cua `%.8f` tren float32. Chi
**21-46 phut/quy** lech that (`|d| > 1e-6`, max `1.44e-04`), do feature vector cua vai phut
do khac giua ban export CSV (2026-08-08) va ban replay dung sau CSV tham chieu.

⚠️ **BAY DA DINH, ghi lai de khong ai dinh lai**: chay cong nay tren "thang 12 duong lich UTC"
(`[2025-12-01, 2026-01-01)` UTC) voi `fold_18` ra `spearman 0.999764`, `max|d| 4.93e-03` — trong
nhu FAIL. **Sai cua so, khong sai code**: cutoff la 00:00 **GMT+7**, nen 7 gio cuoi cua
2025-12-31 UTC thuoc OOS cua `fold_19`. Lay dung mep fold thi `spearman = 1.000000`.

### 1.4 DA SINH — dau vao 2026 (INPUT, khong phai outcome)

Script `research/pipeline/h1/h1_p15_gen.py`. Dung dung hai model da co, **khong train lai,
khong replay**.

| | |
|---|---|
| File | `/home/ubuntu/claudedata/wfo_gate_pred_2026_H1.csv` |
| Byte | 9,366,623 |
| sha256 | `4cc62c14f95fc74aa9f2cd7c2794a30291b0fdabf0dfceec81ae1edda162fdae` |
| So dong | **260,183** |
| `ts` | `1767225600000` .. `1782838800000` (2026-01-01 00:00 UTC -> 2026-07-01 00:00 GMT+7) |
| Nguon | `fold_19` cho `ts < 1774976400000`; `fold_20` cho phan con lai |
| `predRisk4H` | ghi `0.00000000` (muc 1.2 diem 4) |
| dong/thang | 2026-01 44,640 · 02 40,320 · 03 44,640 · 04 43,200 · 05 44,640 · 06 42,743 |

**Doi chieu doc lap**: `_SEALED_2026_MANIFEST.txt` muc 2 ghi `wfo_gate_pred.csv truoc=2,760,443
sau=2,500,261` => doan bi cat = **260,182** dong. Ban tai sinh co **260,183** dong (hon 1 vi lay
ca dong bien `1782838800000`). Khop.

⚠️ 2026-06 thieu **457 phut** so voi 43,200 — la gap co san trong feature store, khong phai loi
sinh. Ghi lai de khong ai tuong dataset thung.

**CHUA nap vao Aerospike.** Nap la thao tac ghi lai vao kho da niem phong — de user lam mot lan
cung luc mo seal (lenh o muc 7).

---

## 2. CONG P1 vs cac cong con lai

| cong | trang thai | ghi chu |
|---|---|---|
| **P1** `p15` | ✅ **PASS** (spearman 1.000000; byte-identity 92.75-97.82%) | muc 1.3 |
| **P2** `CLOSES_1H` | 🔴 **KHONG CHAY DUOC** | muc 3 |
| **P3** ledger/featv2 | ⛔ **CHUA CHAY** — chan boi P2 | muc 4 |
| **P4** bins 16 fold cu | ⛔ **CHUA CHAY** — chan boi P2 va muc 5 | |
| **P5** parity dataset 20251231 | ⛔ **CHUA CHAY** — can bins moi | |

---

## 3. 🔴 BLOCKER 1 — `CLOSES_1H.bin` KHONG CO GENERATOR

`/home/ubuntu/java/fsrun/CLOSES_1H.bin` — 144,513,404 B, ban ghi 14 byte
`[ts:>i8][symId:>i2][close:>f4]`, 10,322,386 rec, **2021-01-01 01:00 -> 2026-01-01 00:00**,
mtime **2026-09-02 05:46** (= trong lan chay seal, nhung **khong duoc ghi vao
`_SEALED_2026_MANIFEST.txt`** — them mot lo hong so sach).

**Da tim het:** `grep` toan van tren toan bo `/home/ubuntu` (moi loai file, tru blob du lieu)
+ `git grep -i` + `git log -S"CLOSES_1H" --all`. **Moi file khop deu la READER**:
`feat_v2_build.py`, `x1_feat_v2_build.py`, `path_labels.py`, `fs_dl.py`, `fs_build*.py`,
`fs_survey*.py`, `e0_exit_cf.py`, `hold_to_die.py`, `dev_eval.py`, `sel_diag.py`,
`fund_true2.py`, cac `.sh` chan doan. **Khong co file nao GHI ra no.**
`ExportMarketCloseSeries.java` **khong phai** — no xuat CSV `ts,btc_close,eth_close` 15m cho
BTC/ETH, khac hoan toan schema.

⚠️ **De bai gia dinh "dung `CLOSES_1H` 2026 tu ticker" — gia dinh nay MAU THUAN voi neo da do**:
`docs/prereg/PREREG_FS.md` muc 0 va `docs/result/FS_RESULT.md` muc 0.1 do duoc
`CLOSES_1H.bin[t] == close cua kline co open_time = t − 1h`, sai so tuong doi max
**4.14e-08** (BTCUSDT 2022-03, n=743) va **3.59e-08** (ETHUSDT 2023-08, n=743), doi chieu voi
**kline 1h Binance Vision**; gia thuyet nguoc (`open_time == t`) lech **4.6e-02**.
=> Nguon goc la **kline 1h**, KHONG phai ticker 1m. Dung lai tu ticker 1m se ra mot chuoi
KHAC va cong P2 se bat duoc.

**Hai duong di (user chon, khong phai agent chon):**

- **(a) Viet lai generator tu Vision 1h kline** — dung nguon da chung minh. `research/featsearch/fs_dl.py`
  da co san phan tai Vision kline 1h theo thang; chi can dump ra dung schema 14 byte + dung
  `symId` cua `selector_pred_out/symbol_map.csv`. **Cong P2 = dung lai 2025-12 phai byte-identical
  voi file hien co** — day chinh la phep thu quyet dinh duong nay dung hay sai.
- **(b) Dung Aerospike `kline_1m_opt` gop len 1h** — nhanh hon nhung gan nhu chac chan **KHONG**
  byte-identical (khac nguon, khac lam tron). Neu chon duong nay thi **ca 16 fold cu cung phai
  dung lai** => mat neo `C3`/`X1_C3` => vi pham chinh muc dich cua H1.

**=> Khuyen nghi: duong (a). Neu P2 khong PASS thi H1 khong duoc chay.**

---

## 4. ⛔ ledger + featv2 (CHUA CHAY — chan boi muc 3)

Cong thuc tai dung y X1 (`research/pipeline/x1/`), chi doi ten va mep:

```bash
CUTS18="20220101 20220401 20220701 20221001 20230101 20230401 20230701 20231001 \
        20240101 20240401 20240701 20241001 20250101 20250401 20250701 20251001 \
        20260101 20260401"
env X1_T1=2026-07-01 X1_CUTS="$CUTS18" X1_LNAME=cand_dev_h1 X1_LBGLOB='202[1-6]' \
    python3 -u x1_ledger.py build
```

⚠️ **Bay glob nhan** (X1 muc 12.4): ban goc `research/pipeline/ledger.py` co
`funding_label_202[1-4]*.pb`; ban X1 tham so hoa thanh `X1_LBGLOB` va X1 chay voi `202[1-5]`.
**H1 phai dat `202[1-6]`** — neu khong se **lang le thieu toan bo 2026** ma khong bao loi.
Kiem bat buoc sau khi build: `cand_dev_h1.ts.max()` phai >= 2026-06-30.

Dau vao con thieu cho 2026: `CLOSES_1H` (muc 3) va OI. OI 2026 **co** o
`/home/ubuntu/java/simulator/features_oi_percoin_v1/oi_percoin_20210101_to_20260701.bin.gz`
(3,210,547,898 B) nhung ban giai nen `claudedata/oi/oi_percoin_full.bin` (4,227,723,300 B) la
**ban cu bi ghim sha256** trong `g72_train.py` (`SHA_OI = e3887f63...`). Giai nen ban 2026
can them ~4.3G — dia con **11G** => lam duoc nhung phai xoa ngay sau do, va phai noi long
assert sha trong `g72_train.py` (co y, ghi ro trong provenance).

---

## 5. 🔴 BLOCKER 2 — bins fold 2026 lay P(win) tu dau

`build_map.py` **giu nguyen multiset P(win) cua `predwf_G015x26` trong tung tick**, chi gan lai
gia tri nao cho coin nao theo thu hang S1. Nhung:

- fold `20260101` va `20260401` cua `predwf_G015x26` **DA BI XOA** (`_SEALED_2026_MANIFEST.txt`
  muc 1 liet ke `predwf_G015x26/predict_wf_20260101.bin` va `.../predict_wf_20260401.bin`).
  Tren dia chi con **16 fold** `20220101..20251001`.
- `predwf_G015x26` **KHONG tai lap duoc** — mat training export (`docs/result/G015CUT_RESULT.md`;
  X1 muc 1.3a va muc 12.1 ghi day la no ky thuat single-point-of-failure).
- Train moi bang `g72_train.py` cho ra **ho `predwf_G015_v2`**, hieu chuan P(win) KHAC.

🔴 **Hau qua khong hien nhien**: ban le trailing `symbolPred <= 0.29 -> STRONG (cap 0.08)` la
nguong **TUYET DOI** dat tren chinh gia tri P(win) do, va X3 muc 3 do duoc cac gia tri trong
MOT tick bam rat sat nhau (vd `0.3547 / 0.3586 / 0.3613`). Doi hieu chuan mot chut la
`%STRONG` cua 2026 doi — **vi mot ly do khong lien quan gi den 2026**. Tuc dung 16 fold cu
(G015x26) ghep 2 fold moi (G015_v2) se lam nhiem dung cai tang dang duoc do.

**Phep do bat buoc TRUOC khi chay H1 (chi DEV, hoan toan hop le, khong cham 2026):**

```bash
# train lai G015 tai cutoff DEV cuoi cung roi so hieu chuan voi ban x26 tuong ung
OUT_DIR=/home/ubuntu/g015_calchk G015_NJOBS=4 python3 research/pipeline/g72_train.py
# so: quantile cua P(win) va ty le <= 0.29, giua
#   /home/ubuntu/g015_calchk/predict_wf_20251001.bin
#   /home/ubuntu/claudedata/predwf_G015x26/predict_wf_20251001.bin
```

Lech dang ke => **H1 khong duoc chay tren bins tron nguon**; phai dua len user.

⚠️ `g72_train.py` con ghim cung: `CUT_DATES` chi 10 cutoff (het `20240401`),
`TS_HI = 2024-07-01`, `t1_files()` loc `< "20240701"`, `assert sha256(OI) == SHA_OI`.
Muon dung cho 2026 phai tham so hoa **y het cach X1 da lam** — ban sao trong
`research/pipeline/h1/`, khong sua ban goc (giu kha nang tai lap).

---

## 6. MOC CUOI 2026 KHA DUNG — **2026-07-01 00:00 GMT+7**, 6 thang, 2 fold

| dau vao | mep thuc do | chan? |
|---|---|---|
| feature store gate `gate_dataset_full.csv.gz` | `1782838800000` = 2026-07-01 00:00 GMT+7 | **CHAN** |
| Tool1 `ds_feat15m/features_20260401_to_20260701.t1c.gz` | 2026-07-01 | **CHAN** |
| OI `oi_percoin_20210101_to_20260701.bin.gz` | 2026-07-01 | **CHAN** |
| ticker `tickexport/up26pf/` (227 file, 3.2G) | `ticker_20260813.bin.gz` | khong |
| `label_15m/funding_label_20260701_to_20261001.pb` (25 file) | 2026-10-01 | khong |
| `funding_data` Aerospike (`docs/D1_DATA_AUDIT`) | 2026-08-05 | khong |
| `market_data_object` Aerospike | 2,947,861 obj | khong |

=> **Fold thu ba `20260701` KHONG lam duoc.** Ticker toi 2026-08-13 khong mua them thang nao
vi thieu `p15` + Tool1 + OI. `SIM_END_DATE=20260701`, **khong duoc keo xa hon**.

---

## 7. LENH MO SEAL — chinh xac, de user chay (CHUA CHAY)

`HoldoutSeal.java`: `SEAL_MS = 1767225600000` (2026-01-01 UTC);
`UNSEAL_PHRASE = "I_UNDERSTAND_THIS_BURNS_HOLDOUT_2026"`; doc qua `System.getenv("HOLDOUT_UNSEAL")`.
Diem chot: `WfoDataset.export` (`trimMap` market/pred/funding), `SimulatorMarketLevelTicker1MStopLoss.main`
(`clampEnd`), `SimulatorForcedSeller`.

```bash
R=/home/ubuntu/src/BinanceFuturesJava
JAR=$R/target/binance-java-sdk-1.2.4.jar
B=/home/ubuntu/java/devrun
P=$R/profiles
DS=/home/ubuntu/wfo_ds_h1
CFGF=$R/configs/sim_dev_file.properties
TICK=/home/ubuntu/java/simulator/kaggle_data_hpo

# --- 0) DIEU KIEN: 5 cong PREREG_H1 muc 2 PASS, pgrep java rong, df >= 8G ---

# --- 1) nap p15 2026 vao set gate (mot lan) ---
java -cp $JAR com.binance.chuyennd.ai_ml.features.export.gate.LoadWfoGatePredTool \
     /home/ubuntu/claudedata/wfo_gate_pred_2026_H1.csv ai_pred_market_gate_wfo

# --- 2) MO SEAL ---
export HOLDOUT_UNSEAL=I_UNDERSTAND_THIS_BURNS_HOLDOUT_2026

# --- 3) build dataset (PHAI thay dong "HOLDOUT_UNSEAL DUNG" trong log) ---
cd $B && cp -f $CFGF $B/config.properties
env TRADING_PROFILE=$P/h1_c3.properties WFO_SET_PRED=ai_pred_market_gate_wfo \
    WFO_SEL_HORIZON_IDX=0 WFO_CODE_SHA=$(cd $R && git rev-parse --short HEAD) \
    java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
    com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset $DS > $B/logs/h1_build.out 2>&1
grep -aE 'HOLDOUT_UNSEAL DUNG|HOLDOUT SEAL|EXPORT xong|Exception' $B/logs/h1_build.out | tail
grep -E "foldCount|maxFoldSpan|marketRange|leakFreeFrom|binsSha256|Count=" $DS/manifest.txt

# --- 4) hai arm, TUAN TU, SIM_END_DATE=20260701 ---
for T in H1_C3 H1_C3_FULL; do
  case $T in H1_C3) PROF=$P/h1_c3.properties;; *) PROF=$P/h1_c3_full.properties;; esac
  D=$B/$T; mkdir -p $D/storage $D/logs; cd $D
  cp -f $CFGF config.properties; rm -f storage/*; ln -sfn $TICK kaggle_data_hpo
  env WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20260701 \
      EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json TRADING_PROFILE=$PROF \
      java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx16g -cp $JAR \
      com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss > logs/sim.out 2>&1
  grep -a 'HOLDOUT_UNSEAL DUNG' logs/sim.out | head -1     # KHONG co dong nay => so ra la 2025, VUT DI
  grep -a 'done:' logs/sim.out | tail -1
  wc -l storage/printDone.csv; md5sum storage/printDone.csv
  cd $B
done

# --- 5) cham diem, don dep, NIEM PHONG LAI ---
python3 $R/research/analysis/x1_rates.py H1_C3 H1_C3_FULL
python3 $R/research/analysis/qret_ladder.py H1_C3 H1_C3_FULL
rm -rf $DS
unset HOLDOUT_UNSEAL
```

**Mot lan chay. Khong bien the. Seal lai ngay sau do**, va ghi vao ledger holdout la da tieu.

---

## 8. ARTIFACT DOT NAY

| duong dan | noi dung |
|---|---|
| `research/pipeline/h1/h1_p15_repro.py` | cong P1 — tai tao `p15` mot fold DEV, doi chieu `wfo_gate_pred.csv` |
| `research/pipeline/h1/h1_p15_gen.py` | sinh `p15` 2026 tu `fold_19`/`fold_20` (khong train, khong replay) |
| `/home/ubuntu/claudedata/wfo_gate_pred_2026_H1.csv` | 260,183 dong, sha256 `4cc62c14f95f...` (khong commit — 9.4 MB du lieu) |
| `docs/prereg/PREREG_H1.md` | pre-reg 2 arm, cua so, tieu chi, du doan ghi truoc |
| `docs/plan/H1_HOLDOUT_PREP.md` | file nay |

## 9. NO KY THUAT PHAT HIEN TRONG DOT NAY

1. 🔴 `CLOSES_1H.bin` **khong co generator** o bat ky dau — muc 3. Mot dau vao load-bearing
   cua toan bo `featv2` ma khong ai dung lai duoc.
2. 🔴 `predwf_G015x26` fold 2026 da xoa + khong tai lap => bins H1 phai tron nguon — muc 5.
3. ⚠️ `wfo_gate_pred.csv.bak_20260711_2333` **khong nam trong seal manifest** => con nguyen
   dong 2026 cua doi gate cu.
4. ⚠️ `CLOSES_1H.bin` bi cat trong lan chay seal (mtime 2026-09-02 05:46) nhung **khong duoc
   ghi vao manifest**.
5. ⚠️ `claudedata/wfo_feature_store.csv` **hong**: 166,835 dong, chi toi 2021-04-26, dong cuoi
   cut giua chung (4 truong). Ban dung duoc la `gate_dataset_full.csv.gz`.
6. ⚠️ `g72_train.py` ghim cung 10 cutoff / `TS_HI=2024-07-01` / loc Tool1 `<20240701` /
   assert sha OI — phai tham so hoa truoc khi dung cho 2026.
7. ⚠️ Cutoff fold gate la **GMT+7**, khong phai UTC. Cat cua so bang lich UTC se lay nham
   7 gio cuoi nam sang fold sau (muc 1.3).
