# RESULT — GOC LECH NGUON p15: GIA THUYET "SCALER THIEU" (BAC BO)

Pre-reg chot TRUOC: `docs/prereg/PREREG_P15_SOURCE.md` (`47ffcff`). Test tren: Oracle shadow + 242
(**chi DOC**), local Python (nhe) tren artifact DEV. **Khong deploy, khong push git.** 2026 **chi chan doan**.

**KET LUAN MOT CAU:** **KHONG phai thieu scaler.** WARN `OnnxInferenceManager: ⚠️ Scaler missing
…Scaler_Return15M.onnx` la **CO Y** (deploy 2026-08-17: gate live = XGBoost WFO `fold_20`, train **RAW**,
khong scaler) va **ap scaler se NO output ~8-10 lan** (p50 7,6-8,8% so voi live 0,91%) — tuc **nguoc huong
"nen"**. "Scaler thieu" la **red herring**. Nguyen nhan con lai nam o **input/feature cua duong live khac
nguon DEV** (muc 4).

---

## 1. VIEC 1 — KIEM KE FILE (chi DOC)

### 1.1 Model gate p15 (`FILE_AI_PREDICTIONS=../storage/ai_ml_data/ai_models_reg_v3`)

| file | shadow Oracle | 242 | giong? |
|---|---|---|---|
| `Model_Regressor_Return15M.onnx` | md5 **`8ec9975726270782692bfe00b39bd37f`**, 144.774 B, mtime 2026-09-06 14:48 | md5 **`8ec9975726270782692bfe00b39bd37f`**, 144.774 B, mtime 2026-08-17 16:27 | **GIONG (byte-identical)** |

md5 nay **== `~/claudedata/wfo_models/fold_20/Model_Regressor_Return15M.onnx`** (mtime 2026-08-06) ⇒
model p15 dang chay **chinh la fold_20** (WFO XGBoost, cutoff 2025-10). `sha256` khop o ca 2 host.

### 1.2 Model khac (VIEC 1 yeu cau) — KHAC nhau giua shadow va 242

| key | shadow Oracle | 242 | giong? |
|---|---|---|---|
| `S1_MODEL_ONNX` | `/home/ubuntu/s1_model/s1a2x1_cut20251001.onnx` md5 `afaa2828…` | `/home/chuyennd/java/storage/c3_models/s1a2x1_cut20251231.onnx` md5 `511add62…` | **KHAC** |
| `NET015_MODEL_ONNX` | (khong khai) → default `/home/ubuntu/g3x26/g015x26_f15_cut20251001.onnx` md5 `a39dbe9a…` | `…/c3_models/g015x26_f15_cut20251231.onnx` md5 `e65e683b…` | **KHAC** |

⇒ selector (S1) va thang gia tri (net015) **khac nhau** giua 2 host, **nhung model gate p15 (sinh ra p15) thi
GIONG**. Ca 2 host deu cho p15 bi nen (max 2,300%) ⇒ nen **khong** den tu selector/net015.

### 1.3 Scaler — DANH SACH THIEU

`OnnxInferenceManager.SinglePredictor` (xem §2) **MONG DOI** `Scaler_<cleanTarget>.onnx` cho **moi** target.
Trong `ai_models_reg_v3` cua ca 2 host:

| target | file scaler mong doi | shadow | 242 |
|---|---|---|---|
| futureReturn15M (p15) | `Scaler_Return15M.onnx` | **THIEU** | **THIEU** (chi con `.disabled_wfo` + `.bak_gatewfo_20260817`, 564 B) |
| futureReturn1H | `Scaler_Return1H.onnx` | co | co |
| futureReturn4H | `Scaler_Return4H.onnx` | co | co |
| futureReturn24H | `Scaler_Return24H.onnx` | co | co |
| maxDrawdownNext4H | `Scaler_maxDrawdown4H.onnx` | co | co |
| maxDrawdownNext24H | `Scaler_maxDrawdown24H.onnx` | co | co |

### 1.4 Pipeline DEV (research) — **cung KHONG dung scaler**

- `ml/gate/train_gate_fold.py` (va `ml/training/…`, `~/java/simulator/…`) dong 7 nguyen van:
  *"KHÔNG scaler (XGBoost bất biến scale; OnnxInferenceManager chạy raw)"*. `model.fit(Xtr,ytr)` tren feature RAW;
  khong co `StandardScaler`/`transform` nao (grep `scaler|StandardScaler|transform` → 0 dong ngoai comment).
- `WFOGateRunner.predictOOSToFile()` (`:216-221`) cung dung `new OnnxInferenceManager(modelDir)` → duong predict DEV
  **cung la OnnxInferenceManager**; cac `wfo_models/fold_k/` **chi co model, khong co scaler** ⇒ DEV cung chay RAW.

⇒ **Ca DEV lan LIVE deu chay RAW (khong scaler)**. `Scaler_Return15M.onnx` (564 B) la scaler cua model **CU** reg_v3
(neural-net 189 MB), **khong** dung cho `fold_20`.

---

## 2. VIEC 2 — CODE INFERENCE (`file:line`)

`src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/OnnxInferenceManager.java`

- `:103` ten file: `scalerFileName = "Scaler_" + prefix + cleanTarget + ".onnx"` → voi Regressor: `Scaler_Return15M.onnx`.
- `:107-112` **neu file ton tai** → `createSession(scaler)`; **neu khong** → `LOG.warn("⚠️ Scaler missing: {}", scalerPath)` va `scaler` = `null`.
- `:134-138` khi `scaler != null`: `runModel(scaler, rawFeatures)` → `inputForModel = scaledOutput[0]`; **neu `scaler == null`** → `inputForModel = rawFeatures` (di thang RAW vao model, khong mac dinh/khong bu).
- `:45` model p15 = `SinglePredictor(modelDir,"futureReturn15M","Regressor")`; `predictAll()` (`:48-61`) dung
  `extractFeaturesV3Full` (33 feat) cho ca p15 lan risk4H.

⇒ **Khi thieu scaler: bo qua scale, feed RAW.** Feature bi anh huong: **tat ca 33 feat cua `Return15M`** (chinh cai
sinh `p15`). He qua dinh luong phu thuoc: RAW co dung la cai model mong doi khong (coi §3).

---

## 3. VIEC 3 — DO DINH LUONG (phan quyet dinh)

Chay `fold_20` (ONNX) bang `onnxruntime` local tren feature DEV. Nguon feature: `claudedata/gate15m_v2_full.csv`
(= `gate_ab_full/fs_full.csv`, 2.846.462 dong 2021-01→2026-06) va `claudedata/wfo_feature_store.csv`
(166.836 dong 2021-01→2021-04). Scaler cu lay tu `Scaler_Return15M.onnx.disabled_wfo` (242, 564 B; 1 node `Scaler`,
`Y=(X-offset)*scale`, 33 feat; `scale` 31→669).

### 3.1 **PHEP THU QUYET DINH: `fold_20(raw)` vs `fold_20(scaled)` vs LIVE**

| phan bo | n | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| `fold_20` RAW (feature 2021) | 166.836 | **0,724** | 1,167 | 1,894 | **21,14** |
| `fold_20` **SCALED** (feature 2021) | 166.836 | **8,770** | 17,035 | 21,650 | **66,86** |
| `fold_20` RAW (feature 2025-10→2026-06) | 349.921 | **1,097** | 1,646 | 2,285 | **64,21** |
| `fold_20` **SCALED** (feature 2025-10→2026-06) | 349.921 | **7,612** | 22,306 | 34,057 | **76,62** |
| **LIVE 242 (2026)** | 8.986 | **0,910** | 1,380 | 1,770 | **2,300** |

⇒ **Ca RAW lan SCALED deu KHONG khop live.** `SCALED` cho phan bo **RONG gap 8-10 lan** (p50 7,6-8,8% >>
live 0,91%). Vay **"thieu scaler" khong the gay "nen"**: neu live **co** scaler thi output da **no**, khong phai
hep. **H1 (thieu scaler ⇒ nen) BAC BO** (theo dung luat §3.2 cua pre-reg).

### 3.2 Kiem "nhip": 15 phut co giai thich duoi bi cat khong? — **KHONG**

`pred.bin` 1-phut vs subsample luoi 15-phut (`t % 900000 == 0`):

| tap | n | p50 | p99 | p99,9 | max | # ≥2,947% |
|---|---|---|---|---|---|---|
| DEV full 1-phut (2021-03→2025-12) | 2.500.260 | 0,545 | 1,308 | 2,818 | **12,261** | 2.248 |
| DEV full @15-phut | 166.684 | 0,549 | 1,321 | 2,871 | **11,126** | 158 |
| DEV 2025-10→12 1-phut (cua so fold_20) | 132.465 | 0,900 | 1,401 | 3,510 | **11,946** | 150 |
| DEV 2025-10→12 **@15-phut** | 8.831 | **0,915** | 1,415 | 3,390 | **10,315** | **10** |
| **LIVE 242** | 8.986 | **0,910** | 1,770 | 1,960 | **2,300** | **0** |
| **SHADOW** | 609 | 0,930 | 1,490 | 2,300 | **2,300** | **0** |

Hai doc quan trong:
1. **THAN khop khi so cung cua so + cung nhip:** DEV `2025-10→12 @15'` p50 = **0,915** ≈ live **0,910**. Phan
   "than affine `live~0,33+1,07·dev`" o `RESULT_GATE_ROOTCAUSE` la **artifact cua viec so 2026 voi CA 2021-2025**
   (2021-2022 keo p50 xuong 0,545) — **khong phai** bang chung model bi nen.
2. **DUOI van lech va khong do nhip:** DEV `2025-10→12 @15'` con **max 10,3%** va **10 mau ≥2,947%**; live **0**.
   ⇒ khac biet con lai **chi o duoi tren**, khong do cadence, khong do model file (giong), khong do scaler (§3.1).
3. Bang chung phu: `fold_20` RAW tren feature ngoai tuyen 2026 tu `gate15m_v2_full.csv` cho **max 64,2%** /
   0,29% mau ≥2,947% (630/217.456) ⇒ neu input live **giong** export ngoai tuyen thi live da co duoi rong. Live
   max 2,3% ⇒ **input live KHAC**.

### 3.3 Xac nhan nguon bo pred DEV

`wfo_ds_x1_2021/pred.bin` (n=2.500.260) **== `~/claudedata/wfo_gate_pred.csv`** den do chinh xac float
(`max|Δ| = 3,7e-9`, ts trung khit). Nguon: `WFOGateRunner` → `OnnxInferenceManager` per-fold (theo
`RESULT_GATEFEAT.md` §Stage0: "19/19 fold PASS spearman ≥ 0,999997" khi dung **model goc + store**).

### 3.4 Thu tai tao `pred.bin` bang `wfo_models/fold_*` — **KHONG tai tao duoc**

Chay **ca 21** `fold_0…fold_20` tren feature `2025-10→12`: p50 chay tu 0,748 (fold_0) → 1,630 (fold_5);
**khong** fold nao cho p50 ≈ 0,900 + p99 1,401 + max 11,946 nhu `pred.bin`. Do chinh xac join voi
`gate15m_v2_full.csv` chi **corr 0,762**, `mean ratio 1,33`. ⇒ **store feature ngoai tuyen hien co KHONG phai**
store da dung de sinh `pred.bin`; **khong the khoanh vung (ii) vs (iii) chi bang artifact con lai** (khai RO o §5).

---

## 4. VIEC 4 — KET LUAN + DE XUAT (KHONG deploy)

### (1) Nguyen nhan goc (1 trong 4) + bang chung

- **(i) thieu scaler — BAC BO.** `Scaler_Return15M.onnx` thieu la **CO Y** (`docs/archive/…/v1_live_deploy_gate_wfo_2026-08-17.md`:
  *"phải BỎ scaler"* vi fold_20 an RAW; WARN la "xác nhận feed RAW"); `train_gate_fold.py:7` train RAW; do dinh luong
  §3.1: **ap scaler ⇒ output NO 8-10 lan** (p50 7,6-8,8% vs live 0,91%), **nguoc** huong "nen".
- **(iv) nen co y — khong co bang chung.** `grep` code `DetectEntrySignal2TradeNormal`/`EntryGate`/`OnnxInferenceManager`:
  **khong** co clip/cap tren `return15M`; ONNX gate la `TreeEnsembleRegressor` thuan.
- **(ii) model khac / (iii) pipeline feature khac — con lai; nghieng ve (iii).** Model file p15 **giong** shadow↔242
  va == fold_20 ⇒ khong phai "model khac" giua 2 host. Nhung `fold_20` cho duoi RONG tren feature ngoai tuyen 2026
  (max 30-64%) trong khi live HEP (max 2,3%) ⇒ khac biet nam o **INPUT cua duong live** (iii). Khong the huy (ii)
  100% vi store goc cua `pred.bin` khong con (§3.4).

### (2) Khong phai scaler ⇒ **KHONG duoc them scaler lai**; sua o NGUON

- **Tuyet doi khong** `mv Scaler_Return15M.onnx.disabled_wfo → Scaler_Return15M.onnx` / khoi phuc `.bak_gatewfo_20260817`:
  se day p15 len 7-20%, pha gate + risk (theo §3.1). Khong co "fix file" don gian nao o day.
- **Viec dung:** lam cho **nguon p15 cua duong live** khop nguon DEV: (a) capture **vector 33 feature live** tai tick
  (read-only, them 1 dong log) va **diff tung feature** voi export ngoai tuyen tren cung cua so; (b) neu lech ⇒ sua
  pipeline feature live; (c) sau khi khop, **khong** hieu chuan lai ngay — do lai 2 phan bo truoc.
- Deploy: **khong co gi de owner duyet trong bai nay** (khong deploy). Rollback: khong ap dung (khong doi gi).

### (3) Buoc tiep (cu the, read-only)

1. Them log feature 33-chieu cua `extractFeaturesV3Full` moi tick (hoac 1 lan/ngay) tren shadow → diff voi
   `gate15m_v2_full.csv` o cung timestamp/che do. Day la **phep thu quyet dinh** de chot (iii) vs (ii).
2. Neu feature live khop export ma output van hep ⇒ nghi (ii): doi chieu jar/sha cua duong predict + store goc cua `pred.bin`.

### (4) Tac dong len quyet dinh

- **Gate se KHONG tu "qua" tro lai** cho toi khi nguon live duoc sua: `thr` = 2,947-3,760% nam **ngoai support**
  cua p15 live (max 2,300%). `n_pass=0` la **tat dinh** (khong phai xui).
- **CANH BAO LON:** vi **nguon live khac nguon DEV** (khong chi lech scale), **MOI nguong hieu chuan lai tren DEV deu
  VO HIEU voi live** — ke ca hieu chuan phan vi/`c` (dung nhu `RESULT_GATE_ROOTCAUSE` §4.4 da canh bao). Hieu chuan
  lai **chi co y nghia SAU khi** nguon khop. Khong hieu chuan truoc.

### Muc bo / ly do (khai RO)

- **Bo:** khong chay Java/sim tren Oracle (rang buoc). Cac phep do la **Python nhe local** tren artifact co san.
- **Bo:** khong retrain lai 21 fold gate — **thieu store goc** (xem §3.4); `RESULT_GATEFEAT` §Stage0 da chung minh
  19/19 fold parity, khong lap lai.
- **Bo:** khong **fetch** vector feature live (live **khong** ghi feature ra file; muon co phai doi code/log + owner
  duyet) ⇒ day la **han che**, ghi ro, va la **buoc tiep**.
- **Bo (xap xi):** doi chieu bang feature-store ngoai tuyen (`gate15m_v2_full.csv`) — **khong phai** store goc (do do
  corr chi 0,76). Moi ket luan dinh luong dua tren cac phep **khong phu thuoc store**: phan bo `pred.bin`/live, hieu
  ung scaler, hieu ung cadence, md5.
- 2026 **chi doc de chan doan**; moi tham so fit deu nam `<= 2025-12-31` (bai nay khong fit them).

---

## 5. BANG CHUNG THO (tai lap, output nho)

```bash
# md5 model gate p15 (chi doc)
md5sum /home/ubuntu/shadow_c3/storage/ai_ml_data/ai_models_reg_v3/Model_Regressor_Return15M.onnx   # 8ec9975726270782692bfe00b39bd37f
ssh -p 2222 -i ~/.ssh/id_rsa_chuyennd root@103.157.218.242 \
  'md5sum /home/chuyennd/java/storage/ai_ml_data/ai_models_reg_v3/Model_Regressor_Return15M.onnx' # 8ec9975726270782692bfe00b39bd37f
ls -la /home/chuyennd/java/storage/ai_ml_data/ai_models_reg_v3/            # Scaler_Return15M.onnx.disabled_wfo (564B)
md5sum /home/ubuntu/claudedata/wfo_models/fold_20/Model_Regressor_Return15M.onnx                    # 8ec9975726270782692bfe00b39bd37f
# hieu ung scaler + cadence + pred.bin==wfo_gate_pred.csv: /tmp/p15probe/probe.py, /tmp/p15probe/*.npy
grep -n "Scaler missing\|if (scaler != null)\|inputForModel = rawFeatures" \
  /home/ubuntu/src/BinanceFuturesJava/src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/OnnxInferenceManager.java
```

**So nguon JSON:** `docs/result/RESULT_P15_SOURCE.json`.
