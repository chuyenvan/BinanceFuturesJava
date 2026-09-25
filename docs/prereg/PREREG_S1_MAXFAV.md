# PREREG_S1_MAXFAV — **ĐỔI NHÃN** của S1 sang họ `maxFav` (`K = 3` nhãn), 1 vòng đối chứng

**Ngày chốt:** 2026-09-25 (viết **TRƯỚC** khi đọc bất kỳ số mới nào của vòng này) · **Nhánh:** `module`
**Trạng thái:** CHỐT — không sửa thiết kế sau khi thấy số (chỉ AMEND bằng commit riêng, ghi rõ sửa *trước
khi đọc số của phần bị sửa*).
**Phạm vi:** DEV only (`2021-12-31 .. 2025-10-08`), **KHÔNG** chạm `2026`/`HoldoutSeal`.
**KHÔNG** chạm ONNX deploy / `NUM_FEATURES` / `extractFeatures45` / đường LIVE. **KHÔNG push.**
**Đây là model MỚI, KHÔNG thay thế model đang chạy.**

---

## 0. CÂU HỎI VÀ 3 CÂU TRẢ LỜI BẮT BUỘC

**Câu hỏi quyết định:** *nhãn train hiện hành `g1lite` (hàm của `maxFav_72h`) — nếu **đổi nhãn** sang
những họ `maxFav` "trần" hơn (liên tục / nhị phân ≥ 0,07 / `maxFav_4h`) trên **CÙNG 45 feature, CÙNG
fold/seed/params** — có làm ra một ranker tốt hơn không? **ở THƯỚC NHÃN** và (quan trọng hơn) **ở
THƯỚC TIỀN**?*

Bắt buộc trả lời cuối cùng:
1. **Đổi nhãn sang `maxFav` có cải thiện THƯỚC NHÃN không?**
2. **Có cải thiện THƯỚC TIỀN không — và có NGOÀI CI so với CẢ HAI đối chứng không?**
3. **Kết luận dứt khoát:** có đáng đổi nhãn trainer / đổi model không (kèm cảnh báo ONNX/LIVE)?

**Bối cảnh đã đo (dùng nguyên số, KHÔNG đo lại — đây là lý do vòng này KHÔNG kỳ vọng có lãi):**
- `RESULT_H72.md` (`130531a`): họ nhãn `maxFav_72h` **RẤT mạnh** ở **THƯỚC NHÃN** (`pacc` 0,596`*`,
  `ic` +0,277`*`, `dec_rho` +0,752`*`) và `g1lite` cũng mạnh (`pacc` 0,556`*`, `ic` +0,167`*`) —
  **nhưng** cùng model S1 trên **THƯỚC TIỀN** `retEnd_72h` chỉ `pacc` **0,46887`*`** / `ic` **−0,08690`*`**
  ⇒ **kỹ năng nhãn ↔ kỹ năng tiền NGƯỢC DẤU**, và `g1lite`/`maxFav` là **nhãn TRAIN của chính S1**
  ⇒ phần "vượt trội" ở thước nhãn là **hiệu ứng mục tiêu train**, không phải thông tin mới.
- `RESULT_PNL_RULER.md` (`acb88bd`): trên **PnL luật thoát** — **0** chỉ số Δ **kinh tế DƯƠNG** ngoài CI.
- `RESULT_MONEY_RANKER.md` (`4a94c36`): đổi nhãn sang `retEnd_h` / PnL thật **PASS ở thước TIỀN**
  (`pacc .502-.505`*) **nhưng kinh tế = 0**; và **tăng NHÃN `maxFav` thì model mới KÉM HƠN HẲN**
  (Δic −0,29`*`…−0,33`*`, Δlift8 −0,21…−0,26`*`, `auc8c` .335/.398/.415 < 0,5) so với đối chứng.
- ⇒ **Mục đích vòng này KHÔNG phải đi tìm lãi.** Mục đích là **đo dứt khoát chênh lệch giữa hai họ nhãn
  trên CÙNG một đường ống train** (`g1lite`-family vs `maxFav`-trần-family) và **chốt trục này**:
  kết luận hiện có = *alpha xếp hạng trên 45 feature = 0* (`RESULT_PNL_RULER.md`).

---

## 1. RÀNG BUỘC (chốt)

1. **KHÔNG** `claude-run`/Claude Code.
2. **KHÔNG** chạy Java/sim trên Oracle (đang shadow LIVE).
3. **KHÔNG push git** (commit local — commit **SỚM**).
4. **DEV only** — 16 fold DEV, không chạm 2026/`HoldoutSeal`.
5. **TUYỆT ĐỐI không chạm** ONNX deploy / `NUM_FEATURES` / `extractFeatures45` / đường LIVE.
6. Mọi bước **NẶNG** (train) ⇒ **KAGGLE**; Oracle chỉ bước **NHẸ** (đọc/soạn/log/chấm). Kiểm `free -g`
   trước mỗi bước nặng. **Kaggle không chạy được ⇒ DỪNG và báo rõ**, không tự chạy nặng trên Oracle.
7. Output tool giữ **THẬT NHỎ**.

---

## 2. NHÃN — `K = 3` ỨNG VIÊN (chốt TRƯỚC, không chọn cái đẹp)

Tất cả đọc từ cột **đã có sẵn** trong `/home/ubuntu/label_15m/funding_label_*.pb` (không tính lại từ giá 1m).
Cơ chế: **chỉ THÊM option cho `load_labels`** của trainer (`research/pipeline/g015_net_train_add.py`),
**không phá đường cũ** (`--label-kind bin` mặc định = hành vi byte-identical như trước).

| # | arm | `y` | cờ trainer | objective | ghi chú |
|---|---|---|---|---|---|
| **i** | `MFC72` | **`maxFav_72h` LIÊN TỤC** (CHẠM, gross) | `--label-mode maxfav --label-h 72 --label-kind cont` | `XGBRegressor(reg:squarederror)` | **phép đổi sạch nhất**: thay trực tiếp `g1lite` (= hàm của chính cột này), **cùng 72h** |
| **ii** | `MFB72` | **`(maxFav_72h ≥ 0,07)`** | `--label-mode maxfav --label-h 72 --label-kind bin --thr 0.07` | `XGBClassifier(binary:logistic)` | ngưỡng **0,07 chốt TRƯỚC** vì **trùng đúng `TOUCH = 0,07`** mà `model_ruler` dùng cho thước NHÃN `y1` (+7% hệ số arm) ⇒ nhãn và thước cùng thang |
| **iii** | `MFC4` | `maxFav_4h` LIÊN TỤC | `--label-mode maxfav --label-h 4 --label-kind cont` | `XGBRegressor` | chạy **nếu còn ngân sách**; 4h = horizon phụ (theo `RESULT_H72` §2) |

**Cơ sở dữ liệu (đo 1 file DEV 2025Q1, `nBars_72h ≥ 288`; 3.055.300 dòng):** `maxFav_72h` mean 0,080686 ·
median 0,052800 · `retEnd_72h` mean −0,025098 · `g1lite` mean 0,003454 ·
**base `≥ 0,07` = 0,391497** (≈ gần cân bằng), base `≥ 0,05` = 0,520474.
⇒ Nhãn nhị phân (ii) có `scale_pos_weight = (1−base)/base` **khác hẳn** `retEnd_4h>0,015` (base 0,2699)
— **khai báo**, không phải nới ngưỡng quyết định.

**Multiplicity:** **k = 3** ứng viên (i)(ii)(iii) so với baseline ⇒ **KHÔNG** tính baseline vào k.
Độ rộng "honest" dùng đúng chuẩn hoá repo: `x1_rates.py --k 3` ⇒ `c3_rates.inflate(3)` =
**1,482304** (raw = 1,0; legacy `1,21` in kèm để so số cũ). Không hardcode: hằng số lấy tại thời điểm
chấm bằng chính hàm `c3_rates.inflate(k)`.

---

## 3. TRAIN (chốt — chỉ đổi NHÃN so với đường S1 hiện hành)

| mục | giá trị |
|---|---|
| đặc trưng | **45 cột** (`f0..f39` Tool1 15m + 5 OI) — KHÔNG thêm/bớt |
| fold | **16 fold DEV** `20220101..20251001` (mọi fold `assert ts.max() < cutoff`) |
| purge | `PURGE_STEPS = 288` × 15m = **72h** |
| seed / nest | `42` / `400`; `max_depth 5`, `lr 0,05`, `subsample 0,8`, `colsample_bytree 0,8`, `min_child_weight 20`, `tree_method hist` |
| device | `cuda` (**KAGGLE GPU**; KHÔNG train trên Oracle) |
| điểm OOS | `predict_wf_<cutoff>.bin` ghi vào thư mục **MỚI** (KHÔNG ghi đè bins deploy) |
| runtime code | nhúng base64 **đúng code đã commit** (kernel tự in `sha256` + `mean(y)` để kiểm nhãn) |

**Kiểm nhãn tại chỗ (bắt buộc in trong log kernel):** `Label 72h (maxfav ... ): N rows | mean=...`
— với (i) mean phải **≈ +0,08** (không phải ≈ 0 như `retEnd_72h` < 0) ⇒ chứng minh nhãn đúng là
`maxFav_72h`; với (ii) mean phải **≈ 0,39** (không phải 0,2699 của `retEnd_4h`).

**Đối chứng — dùng NGUYÊN, KHÔNG retrain lại:**
`45deploy` = `/home/ubuntu/claudedata/predwf_G015x26` · `A45` = `ruler_bins/g015p2-arm44-gpu/stage2/A45`
· `V5`, `V1` = `ruler_bins/g015p2-stage2-featvar-gpu/stage2/*` (**bước retrain** = `A45`; **bước nhiễu** = `V5`).
**`S1 deploy` (bối cảnh):** điểm live ranker đã có = `/home/ubuntu/ledger/pred_s1a2x1.parquet`
(`score` THẤP = TỐT, 6.573.909 dòng) — in kèm như **mốc đã deploy**, **không** phải đối chứng retrain.

---

## 4. THƯỚC, CHỈ SỐ, CI (chốt)

Hai thước, dùng **NGUYÊN** `research/analysis/model_ruler.tick_metrics` (không viết lại chỉ số):

- **THƯỚC NHÃN:** `y = g1lite` (hàm `maxFav_72h` như `RESULT_H72`) · `y = maxFav_72h` (CHẠM).
- **THƯỚC TIỀN:** `y = retEnd_72h` (**gross**; `netm8` tự trừ phí 0,008 trong `tick_metrics`).
  Nếu file `/tmp/mrout/mrout/label_b_pnl.parquet` **còn** ⇒ chấm thêm **`y = PnL luật thoát`**
  (`RESULT_MONEY_RANKER` §4, 309.024 dòng) bằng `research/analysis/mr_pnl_score.py`.
  **Nếu file KHÔNG còn ⇒ ghi RÕ vào RESULT và BỎ mục này, KHÔNG build lại.**

Chỉ số in **bắt buộc:** `ic` · `pacc` · `dec_mono` · `dec_rho` · `glift8` · `netm8` · `auc8c`
(+ `auc8`, `lift8`, `base`, `n_tick`). Mốc vô dụng: `pacc`/`dec_mono`/`auc8c` = 0,5; `ic`/`glift8`/`netm8` = 0.

**CI:** `stage2_score.block_boot_mean`, `BLOCK_H = 72`, `NREP = 2000`, `SEED = 20260905`;
độ rộng quyết định = **raw + honest `inflate(k = 3)` = 1,482304**. "`*`" = **ngoài CẢ HAI** độ rộng.
Slot điểm: arm `72h` ghi/lấy **slot 3**, arm `4h` **slot 0** — khai báo rõ từng bảng.

**Kiểm tính hợp lệ của thước (bắt buộc in):** `Δ(A45 − 45deploy)` và `Δ(V5 − V1)` phải **~ 0**
(không ngoài CI) ở **cả hai** thước; nếu KHÔNG ~ 0 ⇒ thước đang bắt nhiễu ⇒ mọi kết luận GO hạ xuống
"không kết luận".

---

## 5. LUẬT QUYẾT ĐỊNH (chốt TRƯỚC — không nới ngưỡng)

**(A) "Cải thiện THƯỚC NHÃN"** = arm mới **vượt CẢ HAI đối chứng** (`A45` và `V5`) **ngoài CI** ở
`Δic > 0` **và** `Δpacc > 0` **và** `Δdec_mono > 0`.

**(B) "Cải thiện THƯỚC TIỀN"** = arm mới **vượt CẢ HAI đối chứng** (`A45` và `V5`) **ngoài CI** ở
**`Δglift8 > 0`** **và** **`Δnetm8 > 0`**, **VÀ** `netm8` tuyệt đối **> 0** (không chỉ "bớt âm").
Chỉ số KHÔNG tính được ⇒ **KHÔNG** tính là PASS. `45deploy` và `S1 deploy` là **bảng bắt buộc** nhưng
**không** là điều kiện (khác nhãn/khác họ model/khác device).

**Không** dùng (A) làm bằng chứng cho (B). Nếu chỉ (A) đạt và (B) không ⇒ ghi rõ: đó là **khớp mục
tiêu train**, **không phải thông tin mới**, và **KHÔNG đổi model**.

---

## 6. THỨ TỰ ƯU TIÊN (chốt TRƯỚC)

1. **(i) `MFC72`** — 2. **(ii) `MFB72`** — 3. **(iii) `MFC4`**.
Cạn ngân sách ⇒ dừng **đúng thứ tự này**, ghi rõ **mục nào bỏ + lý do** (Kaggle không chạy được = dừng
và báo, KHÔNG lách sang Oracle).

---

## 7. KHAI BÁO TRƯỚC — ĐIỂM MÙ / RỦI RO

1. **`maxFav` là nhãn ĐƯỜNG ĐI (chạm trần)** ⇒ kỳ vọng **mạnh ở thước NHÃN** gần như **theo định nghĩa**;
   không được đọc là "tìm ra thông tin mới".
2. `g1lite` = `maxFav_72h` **cắt trần** (`− min(0,5·maxFav; 0,08)`, pha `retEnd_72h` khi `< 0,05`)
   ⇒ (i) và nhãn deploy **khác nhau ở phần ĐUÔI/cắt trần**, không khác nguồn dữ liệu.
3. `MFC4` đổi **cả horizon** ⇒ không so trực tiếp như (i); chỉ báo cáo.
4. `reg:squarederror` trên `maxFav` (đuôi dày) có thể bị chi phối bởi đuôi — **khai báo**, không đổi loss giữa đường.
5. `MFB72` đổi **cả objective** (`binary:logistic`) và `scale_pos_weight` ⇒ Δ có thể đến từ **objective**, không thuần nhãn.
6. **`45deploy` là artifact cũ** (device `cuda`, 18 cutoff) ⇒ mọi so sánh phải kèm `A45` (mốc retrain cùng buổi).
7. `netm8` của `tick_metrics` trừ **0,008** phí; **không** trừ funding; `retEnd_72h` là **gross**.
8. Bins của mọi model 45-feature có `z` (slot 12h/24h) = NaN 100% ⇒ **chỉ** slot được ghi mới có điểm.

## 8. DỰ ĐOÁN KHAI TRƯỚC (kiểm độ trung thực — KHÔNG dùng để chọn nhãn)

- **Q1.** (A) với `MFC72`: `Δic` vs `A45`/`V5` **> 0 ngoài CI** là **có thể** (nhãn chạm dễ "ăn" hơn).
- **Q2.** (A) với `MFB72`: khả năng **PASS** nhưng **yếu hơn** `MFC72` (nhị phân mất thông tin biên độ).
- **Q3.** (B) **KHÔNG đạt ở bất kỳ arm nào**: `Δglift8`/`Δnetm8` **trong CI**, `netm8` **vẫn âm**
  (dự đoán −0,006…−0,010). Kỳ vọng gốc: **NULL ở thước TIỀN** — đúng như `RESULT_H72`/`RESULT_MONEY_RANKER`.
- **Q4.** Trên thước **NHÃN** `g1lite`, các arm `maxFav` **KHÔNG** vượt S1/`A45` một cách hệ thống (nhãn train khác).
- **Q5.** `Δ(A45 − 45deploy)` và `Δ(V5 − V1)` **~ 0** ở cả hai thước (thước hợp lệ).

## 9. NẾU ≈ 0 Ở MỌI THƯỚC — PHÁT BIỂU CUỐI

*Trên 45 feature hiện có, đổi nhãn KHÔNG tạo ra alpha xếp hạng quy ra tiền*: cả nhãn **`g1lite`**
(đang deploy), nhãn **`retEnd_h`**, nhãn **PnL luật thoát**, và **họ `maxFav` trần** đều cho
`Δ` **trong CI** ở thước TIỀN với `netm8 < 0`. ⇒ **Bước sai là MỤC TIÊU/ĐẶC TRƯNG**, không phải nhãn,
không phải ngưỡng, không phải mô hình. **Đây là BƯỚC CUỐI của trục "đổi nhãn"** — vòng sau chỉ nên đi
vào **cơ chế rank** (`rank:pairwise`/`lambdarank` với `qid`) và **feature mới**, không tinh chỉnh
hyperparam/ngưỡng của 45 feature hiện có.

## 10. ĐIỀU KHÔNG LÀM TRONG VÒNG NÀY

1. KHÔNG chạm ONNX deploy / `NUM_FEATURES` / `extractFeatures45` / LIVE / `2026` / `HoldoutSeal`.
2. KHÔNG tự tích hợp, KHÔNG đổi ngưỡng, KHÔNG đổi luật quyết định sau khi đọc số.
3. KHÔNG retrain lại đối chứng (`45deploy`, `A45`, `V5`, `V1`).
4. KHÔNG build lại nhãn PnL nếu file không còn (ghi rõ và bỏ).
5. KHÔNG chạy bước nặng trên Oracle khi Kaggle không chạy được (dừng + báo).
