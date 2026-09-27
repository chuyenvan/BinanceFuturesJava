# PRE-REG — GOC LECH NGUON p15: GIA THUYET "SCALER THIEU" (chot TRUOC khi do)

Trang thai: **CHOT TRUOC** khi chay phep do dinh luong chinh. Bai nay tra loi: **cai gi lam p15 cua
duong LIVE bi NEN** (=> gate dong bang), va **co phai "thieu scaler" khong**. Tep nay KHONG duoc sua
sau khi nhin so.

## 0. Nguon su that da do (khong do lai)

`docs/result/RESULT_GATE_ROOTCAUSE.md` (`b65a19a`): 2 phan bo p15 **LECH HINH DANG**:
DEV `wfo_ds_x1_2021/pred.bin` (n=2.500.260) p50 **0,545%** / p99 1,308 / max **12,261**;
LIVE 242 (n=8.986) p50 **0,910%** / p99 1,770 / max **2,300**. Than affine `live ~ 0,3305+1,0746·dev`
(du <=0,036pp) nhung **duoi bi cat** (DEV >=2,947%: **2.247** mau vs live **0**; ky vong 8,08; P=3,1e-4).
⇒ nguong gate hien hanh (2,947-3,760%) **ngoai support cua chinh dau vao live** ⇒ `n_pass=0` tat dinh.

## 1. MANH MOI (khoi diem gia thuyet)

Log shadow lap lai moi lan JVM start: `OnnxInferenceManager: ⚠️ Scaler missing …Scaler_Return15M.onnx`
(49 dong, `docs/audit/AUDIT_SHADOW_LIVE_20260926.md`). ⇒ **H1**: duong inference live **thieu/scaler khac**
⇒ feature vao model khong duoc chuan hoa ⇒ output bi NEN.

## 2. HAI GIA THUYET DOI KHANG

- **H1 (scaler):** thieu `Scaler_Return15M.onnx` lam p15 bi NEN (dich nen + cat duoi).
- **H0 (khong phai scaler):** scaler thieu la **co y/khong anh huong**; nen that den tu input khac
  (model khac · pipeline feature khac · nen co y).

## 3. BON NGUYEN NHAN CAN PHAN BIET + TIEU CHI + DU DOAN DO TRUOC

| # | nguyen nhan | du doan DINH LUONG (kiem duoc) | cach phan biet |
|---|---|---|---|
| (i) | **thieu scaler** | chay cung model + cung feature **CO** scaler vs **KHONG** se cho 2 phan bo KHAC nhau; phan bo khop live (max ~2,30) la ban CO/KHONG scaler tuong ung | so sanh `fold20(feature)` vs `fold20(scale(feature))` voi phan bo live |
| (ii) | **model khac** (file live != file sinh bo pred DEV) | `md5` model live khac `md5` model trong `claudedata/wfo_models/fold_*`; chay model live tren feature DEV **khong** tai tao duoc pred.bin | md5 + tai tao |
| (iii) | **pipeline feature khac** (cung model, input khac) | cung model + md5 giong, nhung chay tren feature **ngoai tuyen cua chinh 2026** cho phan bo RONG (max >>2,3) trong khi live HEP | doi chieu feature-store ngoai tuyen vs live |
| (iv) | **nen co y** (clip/chinh quy) | co hang so clip/nen trong code hoac ONNX | doc code (`file:line`) + soi graph ONNX |

**LUAT KET LUAN (chot truoc):**
1. Neu `fold20(scale)` **khop** phan bo live (max ~2,3) va `fold20(raw)` khong ⇒ **H1 dung** ⇒ (i).
2. Neu ca `fold20(raw)` lan `fold20(scale)` deu cho duoi RONG (max >>2,3) ⇒ **H1 SAI** ⇒ loai (i);
   chuyen sang phan biet (ii)/(iii)/(iv).
3. Neu (i) sai va model md5 live == `wfo_models/fold_*` ma chay tren feature ngoai tuyen 2026 van RONG
   trong khi live HEP ⇒ **(iii)** la nguyen nhan con lai kha di (input live khac).
4. Neu tai tao duoc pred.bin bang fold model + feature store ⇒ (ii) loai.
5. (iv) chi duoc ket luan khi tim thay clip/nen trong code hoac graph ONNX.

## 4. BANG CHUNG SE THU THAP (nho, tool output nho)

1. **File ONNX dang dung** (ten, duong dan, md5, mtime) tren **shadow Oracle** + **242** (chi DOC):
   `Model_Regressor_Return15M.onnx` (= gate p15), `S1_MODEL_ONNX`, `NET015_MODEL_ONNX`. Ghi ro **giong nhau khong**.
2. **Scaler**: liet ke MOI `*Scaler*.onnx` trong thu muc model + file code **MONG DOI** (doc
   `OnnxInferenceManager`: ten file, `file:line`, lam gi khi thieu) ⇒ danh sach THIEU. Doi chieu pipeline DEV
   (`train_gate_fold.py`, `WFOGateRunner`).
3. **Do dinh luong:** chay `fold_20` (model live) tren feature DEV **raw** vs **scaled (scaler cu)**, so voi
   phan bo live. Them: phan bo DEV 15-phut (kiem tra "nhip" co giai thich duoc duoi khong).
4. **Bang chung gian tiep** neu khong tai tao duoc: md5 model/shadow-242, thoi diem WARN vs thoi diem doi jar.

## 5. RANH GIOI (CUNG)

- `pred.bin` + `wfo_gate_pred.csv` (<=2025-12-31) = **FIT/doi chieu**; log 2026 (242/shadow) = **CHI CHAN DOAN**.
- **CHI DOC** tren Oracle + 242 (khong restart/sua config/deploy/kill; khong doc key). Do nang ⇒ local (Python nhe).
- **Khong push git**; commit som. **Khong deploy** bat cu thu gi.
- Khong sua code san pham / ONNX / `NUM_FEATURES` / `extractFeatures45` / duong LIVE.

## 6. KET QUA SE GHI O

`docs/result/RESULT_P15_SOURCE.md` (+ `.json`). Muc "bo / sai lech" khai RO.
