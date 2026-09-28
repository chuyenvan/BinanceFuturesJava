# PRE-REG — VI SAO KHONG TAI LAP DUOC STORE FEATURE SINH `pred.bin` (corr 0,762)

Chot TRUOC khi do so moi. Nguon dong luc: `docs/result/RESULT_P15_SOURCE.md` §3.4 + `Claude outputs/AUDIT_20260928_C_edge_coverage.md` §0.5/§254.
Ngay chot: 2026-09-28. Nguoi chot: subagent (khong doi sau khi thay so).
Rang buoc: **CHI DOC** Oracle/242; khong chay Java/sim/WFO tren Oracle; khong cham production/242/ONNX; khong push du lieu; FIT <= 2025-12-31, 2026 chi chan doan; file nho, don ngay.

---

## 0. CAU HOI QUYET DINH

`pred.bin` (bundle `wfo_ds_x1_2021`, set `ai_pred_market_gate_wfo`) co duoc dung lam **chuan hieu chuan** khong,
hay moi nguong DEV phai bi coi la **nghi ngo** vi duoi p15 DEV co the la artifact cua pipeline offline?

## 1. SU THAT DA BIET TRUOC (tu doc, khong phai do moi)

- `RESULT_P15_SOURCE.md` §3.4: chay **ca 21** `~/claudedata/wfo_models/fold_0..20` tren feature **`gate15m_v2_full.csv`** (cua so 2025-10→12) → join voi `pred.bin` chi **corr 0,762**, `mean ratio 1,33`; khong fold nao cho p50 0,900/p99 1,401/max 11,946.
- §3.3: `pred.bin` == `~/claudedata/wfo_gate_pred.csv` (max|Δ| 3,7e-9).
- §1.4: pipeline DEV (`train_gate_fold.py`) train RAW, khong scaler; inference qua `OnnxInferenceManager`.
- `WFOGateRunner` (code, `src/main/java/.../features/export/gate/WFOGateRunner.java`): Pha 1 replay → featureStore RAM **va** CSV; Pha 2 loop per-fold: train Python tren **csvStore** → predict OOS tu featureStore RAM → ghi `outFile` (hoac `outFile_<label>.csv` neu nhieu label qua `GATE_AB_LABELS`).
- Tồn tại **2 store khac nhau** tren dia: `~/claudedata/wfo_feature_store.csv` (166.836 dong, 2021-01→2021-04) va `~/claudedata/gate_ab_full/fs_full.csv` (2.846.462 dong, 2021-01→2026-06). `gate15m_v2_full.csv` (2026-08-29) co **41 cot** trong khi `fs_full.csv` (2026-08-18) co **37 cot** ⇒ **KHONG phai cung file** (kích thước lech 1.109.427.134 vs 1.238.681.360 B), du `RESULT_P15_SOURCE.md` §3 ghi "(= gate_ab_full/fs_full.csv)".
- Tồn tại **2 bo model** khac nhau: `wfo_models/fold_20` md5 `8ec99757…` (= model live p15) va `gate_ab_full/models/label_oldbasket/fold_20` md5 `4ac9a576…`.

## 2. 4 GIA THUYET + CACH PHAN BIET BANG SO

| # | Gia thuyet | Dau hieu so quyet dinh |
|---|---|---|
| **H1** | Khac **FEATURE** (thieu/thua cot, khac thu tu, khac cong thuc) | So tung cot feature giua 2 store tai cung ts: neu `gate15m_v2_full` vs `fs_full` lech o >=1 trong 33 cot → H1 dung. Neu giong het → H1 sai. |
| **H2** | Khac **TIEN XU LY** (scale/normalize/NaN/clip) | Da bac bo o `RESULT_P15_SOURCE` §3.1-3.2 (RAW ca 2 dau; scaler lam NO 8-10x). Neu store goc chua `StandardScaler` → H2 dung. Kiem: grep scaler trong script sinh store. |
| **H3** | Khac **PHAM VI** (symbol set / khoang tg / tan suat bar / universe) | So `min/max ts`, so dong, so ts duy nhat giua store dung de tai lap va store goc (neu xac dinh duoc); so corr **theo tung nam**. Neu corr cao o vai nam va thap o nam khac → H3. |
| **H4** | Khac **DINH NGHIA NHAN** (label/horizon/sign) | `GATE_AB_LABELS`: neu `pred.bin` duoc sinh bang label khac `label_oldbasket` (vd `label_ret15m`, `label_retall15m`) → H4 dung. Kiem: doi chieu `pred.bin` voi tung file `wfo_gate_pred_label_*.csv` (md5/join). |

**Uu tien du doan (chot TRUOC):** nguyen nhan chinh la **H3 (va/hoac H1)** — *tai lap dung SAI STORE*, chang phai store goc bi mat.
Du doan cu the: `pred.bin` == output cua `gate_ab_full/models/label_oldbasket/fold_*` tren `fs_full.csv`
(hoac == mot trong cac `wfo_gate_pred_label_*.csv`), nen neu chay **dung cap (store + model)** thi **corr ≈ 1**.
⇒ **Tien doan: "store goc KHONG mat, chi bi nham"** la ket cuc kha di nhat. Neu corr dung cap van < 0,9 → tien doan SAI, va khi do "store goc mat" duoc xac nhan.

## 3. TIEU CHI KET LUAN (chot truoc)

- **TAI LAP DUOC** ⇔ ton tai cap (store, model) tren dia cho **corr >= 0,99** va **p50/p99/max** khop `pred.bin` (sai so <=1%).
- **TAI LAP DUOC MOT PHAN** ⇔ co cap cho corr trong [0,90, 0,99).
- **KHONG TAI LAP DUOC** ⇔ moi cap thu duoc < 0,90 ⇒ "store goc da mat" duoc xac nhan la **DUNG**.
- **pred.bin la artifact?** Chi ket luan "co" neu chung minh duoc duoi p15 DEV den tu mot buoc offline **khong the xay ra live**
  (vd: label/feature duoc tinh bang thong tin tuong lai ngoai label). Neu khong chung minh duoc ⇒ **KHONG KET LUAN** (giu nghi ngo o muc "chua dong").
- Moi so phai **tach 2025-12-31** (FIT) va **2026 (chan doan)**.

## 4. MUC BO (chot truoc)

- Bo: chay lai replay Java (rang buoc) ⇒ chi dung artifact co san tren dia + Python nhe local.
- Bo: retrain 21 fold (ton thoi gian/CPU Oracle dang chay shadow) — chi dung model da co tren dia; neu thieu thi ghi RO.
- Bo: doc `gate15m_v2_full.csv` toan bo vao RAM (1,2GB, 41 cot) — chi doc cot can thiet bang chunks.
