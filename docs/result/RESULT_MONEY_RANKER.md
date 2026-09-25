# RESULT_MONEY_RANKER — CÓ ranker xếp hạng RA TIỀN không? (nhãn (a) rank `retEnd_h` · nhãn (b) PnL thật theo luật thoát)

**Ngày:** 2026-09-25 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG **cả (a) và (b)** + chấm **2 thước**
(offline; **KHÔNG** chạm ONNX/LIVE, **KHÔNG** chạy Java/sim, **KHÔNG** chạm 2026/`HoldoutSeal`) · **KHÔNG push**
**Pre-reg:** `docs/prereg/PREREG_MONEY_RANKER.md` (commit `acd6523`, AMEND 1 `0b09c86`) — **chốt TRƯỚC** khi đọc số.
**Code:** `research/pipeline/mr_label_build.py` (nhãn b) · `research/pipeline/g015_net_train_add.py`
(+`--label-kind cont`, `--label-custom`, `--min-train`; mặc định = hành vi cũ) · `research/analysis/money_ranker_score.py`
· `research/analysis/mr_pool_score.py` · `research/analysis/mr_tables.py` — chấm bằng **NGUYÊN**
`model_ruler.tick_metrics` / `summarize` / `delta` / `ci_mean` (không viết lại chỉ số nào).
**Chi phí:** 2 phiên Kaggle **GPU** (train) + 1 phiên Kaggle **CPU** (nhãn b) — số đo ở §6.1.

---

## 0. TRẢ LỜI NGẮN (3 câu bắt buộc)

### (1) **CÓ** tồn tại ranker xếp hạng RA TIỀN — nhưng chỉ ở **TẦNG THỐNG KÊ**, không ở **TẦNG KINH TẾ**

| nhãn | biến thể | `pacc` | `ic` | `dec_mono` | luật §6 |
|---|---|---|---|---|---|
| **(a)** rank `retEnd_h` liên tục | `MRA4` (4h) | **+0,50409`*`** | **+0,01208`*`** | **+0,50538`*`** | **PASS** |
| **(a)** | `MRA72` (72h) | **+0,50374`*`** | **+0,01098`*`** | **+0,50689`*`** | **PASS** |
| **(b)** PnL thật theo luật thoát | `MRB8` (pool top-8) | **+0,50473`*`** | **+0,01404`*`** | **+0,50423`*`** | **PASS** |
| **(b)** | `MRB32` (pool top-32) | **+0,50200`*`** | **+0,00592`*`** | **+0,50286`*`** | **PASS** |

Cả 4 biến thể **PASS đúng luật đã chốt trước** (`pacc > 0,5` **VÀ** `ic > 0` **VÀ** `dec_mono > 0,5`, **cả ba
ngoài CI** so với **CẢ HAI** đối chứng `A45` và `V5`), ở **cả bản CHẶT (1.21)** lẫn **bản `inflate(k=2)=1,1774`**.
Đặc biệt **nhãn (b)** còn cho kỹ năng **trong đúng pool ứng viên**: `MRB8` trong top-8 ⇒ `pacc` **0,51565**,
`ic` **+0,04097** (đối chứng cùng pool: `pacc` 0,49477, `ic` −0,01333); **ghép cặp trên giao tick
(`n=16.397`)** Δ`pacc` = **+0,02101`*`**, Δ`ic` = **+0,05459`*`**, Δ`dec_mono` = **+0,00794`*`** vs `45deploy`
(và cùng dấu/độ lớn vs `A45`, `V5`, `V1`) ⇒ **vượt ngoài CI NGAY TRONG pool** (bảng đầy đủ §3.4).

### (2) …nhưng **KINH TẾ = 0** ⇒ câu trả lời dứt khoát cho "sai ở bước nào" **KHÔNG đổi**

- Δ`glift8` và Δ`netm8` của **mọi** biến thể mới so với **mọi** đối chứng đều **TRONG CI**
  (Δ`glift8` = **+0,00016** (a-4h) · **+0,00001** (b-8) · **+0,00000** (b-32); Δ`netm8` = **+0,00016** · **+0,00001** · **+0,00000**).
- `netm8` của **mọi** biến thể vẫn **ÂM**: −0,00769 (a-4h) · −0,00785 (b-8/b-32) · −0,00612 (a-72h) · −0,00762 (b-8/72h).
- **Mức lift gross tốt nhất** của model mới = **+0,00311 / 72h ≈ +0,311 %** < **phí round-trip 0,8 %** ⇒
  **dù có tin, cũng không phủ được chi phí.**
- Ở **tầng NHÃN** (`maxFav_4h`), model mới **TỆ HƠN HẲN**: Δ`ic` **−0,33`*`** (b-8) / **−0,29`*`** … và `auc8c`
  của model (b) chỉ **0,34** vs **0,61** của đối chứng.

**⇒ "Sai ở bước nào": MỤC TIÊU/ĐẶC TRƯNG — không phải mô hình, không phải ngưỡng.** Kể cả khi **đổi hẳn nhãn
sang chính đại lượng tiền** (liên tục **và** PnL thật theo luật thoát), chỉ số **thứ tự** tăng lên **ngoài CI**
trong khi **mọi chỉ số KINH TẾ đứng yên (trong CI)** ⇒ phần tăng thêm là **hiệu ứng khớp mục tiêu train**,
**KHÔNG** phải thông tin mới về tiền.

### (3) So `45deploy` mạnh hơn bao nhiêu — và **có đáng đổi model không? ⇒ KHÔNG**

| Δ vs `45deploy` (thước TIỀN 4h) | `ic` | `pacc` | `dec_mono` | `glift8` | `netm8` |
|---|---|---|---|---|---|
| `MRA4` − 45deploy | **+0,06319`*`** | **+0,02196`*`** | **+0,00945`*`** | +0,00016 (CI) | +0,00016 (CI) |
| `MRB8` − 45deploy | **+0,06542`*`** | **+0,02271`*`** | **+0,00822`*`** | +0,00001 (CI) | +0,00001 (CI) |
| `MRB32` − 45deploy | **+0,05729`*`** | **+0,01998`*`** | **+0,00684`*`** | +0,00000 (CI) | +0,00000 (CI) |

⇒ Mạnh hơn **có ý nghĩa thống kê** ở tầng thứ tự (+0,06 IC, +0,02 `pacc`), **không** mạnh hơn ở tầng kinh tế,
và **yếu hơn hẳn** ở tầng NHÃN + tầng chọn-nhị-phân. **KHÔNG đáng đổi model.**
**Cảnh báo ONNX/LIVE:** đổi sang đầu HỒI QUY là đổi **ngữ nghĩa điểm** (`P(win)` → *dự đoán lợi suất*) ⇒ phải
sửa `NUM_FEATURES`/`extractFeatures45`, **re-calibrate** ngưỡng cổng (`net015 = retEnd_4h > 0,015`) và luật
chọn top-8; rủi ro cao, lợi ích kinh tế đo được = **0** ⇒ **KHÔNG làm**.

---

## 1. CÁCH ĐO (đúng pre-reg §2–§7; 4 biến thể = **k = 2 nhãn** × 2 mức)

- **Nhãn (a):** `y = retEnd_h` liên tục (`.pb`, `nBars_h ≥ H/15m`). Trainer **KHÔNG có cơ chế rank-label**
  (không `qid`/`rank:*`) ⇒ dùng đúng điều khoản đã cho: **`y` liên tục + chấm Spearman-rank**;
  `XGBRegressor(reg:squarederror, rmse)`, giữ nguyên 45 feature / 16 fold / purge 72h / `seed 42` / `nest 400`
  / `depth 5` / `lr 0,05` / `subsample 0,8` / `colsample 0,8` / `min_child_weight 20` / `hist` / GPU
  (`scale_pos_weight` + `eval_metric=auc` = **N/A** với hồi quy, đã khai trong AMEND/docstring).
- **Nhãn (b):** `PnL(t,sym)` = kết quả của **chính `research/exitfit/exit_engine.simulate`** (harness **PARITY
  PASS**) khi vào ở `t`: `entry = close(t)`, **1 leg**, **`pred = None` ⇒ nhánh WEAK `cap = 0,03`** cho **mọi**
  ứng viên (tránh vòng tròn với điểm đang chấm), arm +7 %/HIGH 1m, ratchet, `BLOCK_INTRABAR_LOOKAHEAD`, khớp
  `min(priceSL, open)`, time-stop 168h, `gross = tp/E − 1`, **`net = gross − 0,008`**, **không funding**.
  **Ứng viên:** top-K theo điểm S1 (`pred_s1a2x1.parquet`, score **thấp = tốt**), `K ∈ {8, 32}`, `K = 8 ⊂ K = 32`
  (mô phỏng không phụ thuộc K ⇒ **1 lần chạy**).
- **Thước:** TIỀN `y = retEnd_h`; NHÃN `y = maxFav_4h`. Chỉ số: **nguyên** `model_ruler.tick_metrics`.
  **CI:** `block_boot_mean`, `BLOCK_H=72`, `NREP=2000`, `SEED=20260905`. **`*` = ngoài CI theo hệ số 1.21 (CHẶT
  HƠN — dùng cho LUẬT)**; `+` = ngoài CI theo `inflate(k=2)=1,177410`. Không nới ngưỡng ở đâu.
- **Đối chứng dùng nguyên (không retrain):** `45deploy`, `A45` (retrain), `V5` (nhiễu), `V1`.
- **Bảng PHỤ §4.2 (bắt buộc theo pre-reg):** chấm **giới hạn trong pool ứng viên** bằng `mr_pool_score.py`
  (cùng chỉ số, cùng CI, chỉ khác tập dòng) — vì model (b) **chỉ thấy pool khi train** ⇒ điểm ngoài pool là **ngoại suy**.

## 2. TRAIN — 4 BIẾN THỂ (2 phiên Kaggle GPU, `mr-train-a-gpu` + `mr-train-b-gpu`)

| arm | nhãn | fold | n_train/fold | n_oos/fold | phút | out |
|---|---|---|---|---|---|---|
| **MRA4** | (a) `retEnd_4h` | 16 | 3,73M → 34,9M | 1,12M → 4,52M | **43,0** | `mr/MRA4` |
| **MRA72** | (a) `retEnd_72h` | 16 | 3,71M → 34,7M | 1,12M → 4,52M | **42,5** | `mr/MRA72` |
| **MRB8** | (b) PnL thật, pool top-8 | **15** (`20220101` = N/A) | 7.376 → 77.255 | 1,17M → 4,52M | **6,6** | `mr/MRB8` |
| **MRB32** | (b) PnL thật, pool top-32 | **15** | 29.504 → 309.018 | 1,17M → 4,52M | **4,4** | `mr/MRB32` |

Fold `20220101` = **N/A cho (b)** vì S1 **không có điểm trước `2021-12-31 17:30`** (đã chốt trước trong §4.2).
Model + bins đã tải về `/tmp/mrbins/{MRA4,MRA72,MRB8,MRB32}` (`model_f*_*.json` + `predict_wf_*.bin`);
**không** ghi đè bins deploy.

## 3. BẢNG CHẤM — THƯỚC TIỀN

`*` = ngoài CI 1.21 (**chặt**, dùng cho LUẬT) · `+` = ngoài CI 1.1774 · không dấu = trong CI.

### 3.1 `h = 4h` — `y = retEnd_4h` (`base` = 0,17620 cho arm 16 fold; 0,17341 cho arm 15 fold)

| arm | `ic` | `pacc` | `dec_mono` | `dec_rho` | `glift8` | `netm8` | `auc8` | `lift8` | n_tick |
|---|---|---|---|---|---|---|---|---|---|
| **MRA4** | **+0,01208`*`** | **+0,50409`*`** | **+0,50538`*`** | +0,03335`*` | +0,00037`*` | −0,00769`*` | 0,42259`*` | +0,02447`*` | 140.238 |
| **MRB8** | **+0,01404`*`** | **+0,50473`*`** | **+0,50423`*`** | +0,02567`*` | +0,00021`*` | −0,00785`*` | 0,34025`*` | +0,00658`*` | 131.598 |
| **MRB32** | **+0,00592`*`** | **+0,50200`*`** | **+0,50286`*`** | +0,01851`*` | +0,00021 (CI) | −0,00785`*` | 0,40476`*` | +0,02289`*` | 131.598 |
| 45deploy | −0,05111`*` | +0,48213`*` | +0,49594`*` | −0,02178`*` | +0,00021 | −0,00785`*` | 0,62393`*` | +0,11051`*` | 140.238 |
| A45 | −0,05106`*` | +0,48214`*` | +0,49533`*` | −0,02170`*` | +0,00027 | −0,00779`*` | 0,62441`*` | +0,11085`*` | 140.238 |
| V5 | −0,05186`*` | +0,48182`*` | +0,49591`*` | −0,02157`*` | +0,00007 | −0,00799`*` | 0,61762`*` | +0,10848`*` | 140.238 |
| V1 | −0,05202`*` | +0,48174`*` | +0,49527`*` | −0,02111`*` | +0,00017 | −0,00789`*` | 0,61887`*` | +0,10910`*` | 140.238 |

Δ ghép cặp theo tick: xem §0-(3) (vs `45deploy`); vs `A45`/`V5` **y hệt về dấu và độ lớn** (`MRB8`: ic +0,06517`*`/+0,06597`*`,
pacc +0,02263`*`/+0,02296`*`, dec_mono +0,00864`*`/+0,00819`*`; `glift8`/`netm8` **trong CI** ở mọi cặp).

### 3.2 `h = 72h` — `y = retEnd_72h` (`base` = 0,38900 / 0,38586)

| arm | `ic` | `pacc` | `dec_mono` | `dec_rho` | `glift8` | `netm8` | `auc8` | `lift8` | n_tick |
|---|---|---|---|---|---|---|---|---|---|
| **MRA72** | **+0,01098`*`** | **+0,50374`*`** | **+0,50689`*`** | +0,03884`*` | +0,00311`*` | −0,00612 (CI) | +0,48107`*` | +0,00713 (CI) | 140.237 |
| **MRB8** | **+0,02639`*`** | **+0,50889`*`** | **+0,50952`*`** | +0,05792`*` | +0,00164 (CI) | −0,00762`*` | +0,47243`*` | +0,01047`*` | 131.597 |
| **MRB32** | **+0,01747`*`** | **+0,50589`*`** | **+0,50783`*`** | +0,05353`*` | +0,00181 (CI) | −0,00745`*` | +0,47680`*` | +0,00554 (CI) | 131.597 |
| 45deploy | −0,08557`*` | +0,47006`*` | +0,48917`*` | −0,05237`*` | +0,00393 (CI) | −0,00531 (CI) | +0,47911`*` | −0,01406 (CI) | 140.237 |
| A45 | −0,08509`*` | +0,47022`*` | +0,48978`*` | −0,05164`*` | +0,00430 (CI) | −0,00494 (CI) | +0,48075`*` | −0,01289 (CI) | 140.237 |
| V5 | −0,09495`*` | +0,46659`*` | +0,48762`*` | −0,06394`*` | +0,00318 (CI) | −0,00605 (CI) | +0,47744`*` | −0,01515 (CI) | 140.237 |

Δ vs `45deploy`: `MRB8` ic **+0,11154`*`** · pacc **+0,03872`*`** · dec_mono **+0,01995`*`** (glift8 −0,00266 CI) ·
`MRB32` ic **+0,10261`*`** · pacc **+0,03572`*`** · dec_mono **+0,01826`*`** (glift8 −0,00249 CI) ·
`MRA72` ic **+0,09655`*`** · pacc **+0,03368`*`** · dec_mono **+0,01773`*`** (glift8 −0,00082 CI).

> **Ghép cặp (khai báo):** `MRA72` chấm bằng **điểm slot 3** × **nhãn 72h**; các đối chứng **không** có điểm
> slot 3 (`z` = NaN 100 %, `DIAG_SCORE72H.md`) nên chấm **slot 0 × nhãn 72h** (cross-horizon) — **đúng như
> `RESULT_MODEL_RULER`/`RESULT_H72`**, **không** phải cùng điều kiện. `MRB8`/`MRB32`/`MRA4` chỉ có slot 0.

### 3.3 THƯỚC NHÃN (đối chiếu) — `y = maxFav_4h` (CHẠM) — **model mới TỆ HƠN HẲN**

| arm | `ic` | `pacc` | `dec_mono` | `glift8` | `netm8` | `auc8` | `lift8` |
|---|---|---|---|---|---|---|---|
| **MRA4** | −0,02927`*` | 0,49008`*` | 0,48406`*` | +0,00649`*` | +0,01587`*` | 0,56377`*` | +0,06107`*` |
| **MRB8** | −0,02752`*` | 0,49078`*` | 0,48004`*` | +0,00105`*` | +0,01034`*` | 0,48424`*` | +0,01097`*` |
| **MRB32** | +0,00441 (CI) | 0,50150`*` | 0,50311`*` | +0,00404`*` | +0,01333`*` | 0,55629`*` | +0,05291`*` |
| 45deploy | +0,29815`*` | 0,60437`*` | 0,66867`*` | +0,02435`*` | +0,03373`*` | 0,78751`*` | +0,27221`*` |
| A45 | +0,29763`*` | 0,60418`*` | 0,66871`*` | +0,02444`*` | +0,03382`*` | 0,78737`*` | +0,27229`*` |
| V5 | +0,30328`*` | 0,60634`*` | 0,67130`*` | +0,02280`*` | +0,03218`*` | 0,78517`*` | +0,26489`*` |

Δ (`MRB8 − 45deploy`): ic **−0,33204`*`** · pacc **−0,11589`*`** · dec_mono **−0,19389`*`** · glift8 −0,02434`*` ·
netm8 −0,02434`*` · auc8 **−0,31051`*`** · lift8 −0,26124`*`. (`MRB32` và `MRA4` cùng dấu, cùng độ lớn.)

### 3.4 BẢNG PHỤ (§4.2 pre-reg) — chấm **TRONG POOL ỨNG VIÊN** (n_tick = số tick S1 có điểm)

⚠️ **Trong pool top-8, `lift8`/`glift8`/`auc8` là SUY BIẾN** (top-8 = **toàn bộ** pool ⇒ `prec8 = base`,
`glift8 = 0` theo cấu trúc; `auc8` còn bị lỗi đếm cặp > 1) ⇒ **chỉ đọc `ic`/`pacc`/`dec_mono`/`dec_rho`/`netm8`**.
Đối chứng ở pool top-8 có `n_tick = 17.349` vs `MRB8` 16.397 (thiếu fold `20220101`) ⇒ so sánh ghép cặp
phải lấy **giao tick** (cột `n_tick_common` ở bảng Δ).

| pool | arm | `ic` | `pacc` | `dec_mono` | `dec_rho` | `glift8` | `netm8` | `lift8` | n_tick |
|---|---|---|---|---|---|---|---|---|---|
| top-8 | **MRB32** (train pool 32, chấm pool 8) | **+0,04963`*`** | **+0,51891`*`** | **+0,50755`*`** | +0,04963`*` | +0,00000 (suy biến) | −0,00612`*` | +0,00000 (suy biến) | 16.397 |
| top-8 | **MRB8** | **+0,04097`*`** | **+0,51565`*`** | **+0,50625`*`** | +0,04094`*` | +0,00000 (suy biến) | **−0,00612`*`** | +0,00000 (suy biến) | 16.397 |
| top-8 | 45deploy | −0,01333 (CI) | 0,49477`*` | 0,49863`*` | −0,01335 (CI) | +0,00000 (suy biến) | −0,00621`*` | +0,00000 | 17.349 |
| top-8 | A45 | −0,01357 (CI) | 0,49485`*` | 0,49885`*` | −0,01360 (CI) | +0,00000 | −0,00621`*` | +0,00000 | 17.349 |
| top-8 | V5 | −0,00484 (CI) | 0,49808`*` | 0,49802`*` | −0,00482 (CI) | +0,00000 | −0,00621`*` | +0,00000 | 17.349 |
| top-8 | V1 | −0,00722 (CI) | 0,49703`*` | 0,49834`*` | −0,00723 (CI) | +0,00000 | −0,00621`*` | +0,00000 | 17.349 |
| top-32 | **MRB8** (train pool 8, chấm pool 32) | **+0,03123`*`** | **+0,51073`*`** | **+0,50606`*`** | +0,04532`*` | +0,00157`*` | −0,00489`*` | +0,00730`*` | 16.397 |
| top-32 | **MRB32** | **+0,03152`*`** | **+0,51082`*`** | **+0,50689`*`** | +0,04979`*` | +0,00172`*` | **−0,00475`*`** | +0,01134`*` | 16.397 |
| top-32 | 45deploy | −0,02575`*` | 0,49081`*` | 0,49754`*` | −0,02616`*` | +0,00050 (CI) | −0,00603`*` | +0,03563`*` | 17.349 |
| top-32 | A45 | −0,02459`*` | 0,49115`*` | 0,49753`*` | −0,02586`*` | +0,00041 (CI) | −0,00612`*` | +0,03496`*` | 17.349 |
| top-32 | V5 | −0,01591`*` | 0,49410`*` | 0,49747`*` | −0,01616 (CI) | +0,00029 (CI) | −0,00624`*` | +0,03197`*` | 17.349 |
| top-32 | V1 | −0,01513`*` | 0,49435`*` | 0,49645`*` | −0,01484 (CI) | +0,00044 (CI) | −0,00609`*` | +0,03220`*` | 17.349 |

**Đọc:** trong đúng pool mà model (b) **được train**, kỹ năng **rõ hơn** ở bảng chính
(`pacc` 0,5157 (MRB8, top-8) — **+0,0209 so đối chứng cùng pool**; `ic` +0,0410 vs −0,0133; `dec_mono` 0,5063 vs 0,4986),
**nhưng vẫn chỉ ở tầng thứ tự**. Pool top-32: `MRB32` **nhỉnh hơn đối chứng cả ở KINH TẾ** trong pool
(`glift8` +0,00172 vs +0,00050; `netm8` −0,00475 vs −0,00603) — nhưng 2 chênh lệch này **nhỏ (≈ 1e-3)**,
phải đọc `n_tick_common` + CI ghép cặp ở bảng Δ trước khi nói gì thêm.

**Δ ghép cặp TRONG POOL (giao tick, `n_tick_common` = 16.397 ≈ 3,7 năm):**

| pool | Δ | `ic` | `pacc` | `dec_mono` | `dec_rho` | `glift8` | `netm8` |
|---|---|---|---|---|---|---|---|
| top-8 | MRB8 − 45deploy | **+0,05459`*`** | **+0,02101`*`** | **+0,00794`*`** | +0,05458`*` | +0,00000 (suy biến) | +0,00000 (suy biến) |
| top-8 | MRB32 − 45deploy | **+0,06325`*`** | **+0,02428`*`** | **+0,00925`*`** | +0,06327`*` | +0,00000 (suy biến) | +0,00000 (suy biến) |
| top-32 | MRB8 − 45deploy | **+0,05786`*`** | **+0,02024`*`** | **+0,00905`*`** | +0,07283`*` | +0,00105 (CI) | +0,00105 (CI) |
| top-32 | MRB32 − 45deploy | **+0,05815`*`** | **+0,02034`*`** | **+0,00988`*`** | +0,07730`*` | +0,00120 (CI) | +0,00120 (CI) |

(các cặp vs `A45`/`V5`/`V1` **cùng dấu, cùng độ lớn**, `glift8`/`netm8` **luôn trong CI**).
⇒ **Ngay TRONG pool ứng viên**: kỹ năng THỨ TỰ **vượt cả 4 đối chứng ngoài CI**, nhưng lợi thế KINH TẾ
(≈**+0,12 %/trade**, gross) **trong CI** — và **0,12 % < 0,8 % phí**. **Cùng một hình ở mọi tầng.**

## 4. LUẬT §6 — KẾT QUẢ TỪNG BIẾN THỂ (đúng luật đã chốt, không nới)

| biến thể | thước | `pacc`>0,5 | `ic`>0 | `dec_mono`>0,5 | ngoài CI vs `A45` | ngoài CI vs `V5` | **PASS** |
|---|---|---|---|---|---|---|---|
| `MRA4` | TIỀN 4h | ✔`*` | ✔`*` | ✔`*` | ✔ ✔ ✔ | ✔ ✔ ✔ | **PASS** |
| `MRB8` | TIỀN 4h | ✔`*` | ✔`*` | ✔`*` | ✔ ✔ ✔ | ✔ ✔ ✔ | **PASS** |
| `MRB32` | TIỀN 4h | ✔`*` | ✔`*` | ✔`*` | ✔ ✔ ✔ | ✔ ✔ ✔ | **PASS** |
| `MRA72` | TIỀN 72h | ✔`*` | ✔`*` | ✔`*` | ✔ ✔ ✔ | ✔ ✔ ✔ | **PASS** |
| `MRB8` | TIỀN 72h | ✔`*` | ✔`*` | ✔`*` | ✔ ✔ ✔ | ✔ ✔ ✔ | **PASS** |
| `MRB32` | TIỀN 72h | ✔`*` | ✔`*` | ✔`*` | ✔ ✔ ✔ | ✔ ✔ ✔ | **PASS** |

Kết quả **giống nhau ở CẢ HAI độ rộng CI** ⇒ PASS **không** do chọn độ rộng. **Không nới ngưỡng nào.**

## 5. KIỂM TÍNH HỢP LỆ CỦA THƯỚC + KINH TẾ + `auc8c`

### 5.1 Đối chứng (bắt buộc, §6 pre-reg) — thước **hợp lệ ở 3 chỉ số LUẬT**

| Δ | `ic` | `pacc` | `dec_mono` | `glift8` | `netm8` |
|---|---|---|---|---|---|
| **A45 − 45deploy** (bước *retrain*) — TIỀN 4h | +0,00005 | +0,00001 | −0,00061 | +0,00006 | +0,00006 |
| **V5 − V1** (bước *nhiễu*) — TIỀN 4h | +0,00016 | +0,00007 | +0,00064 | **−0,00010`*`** | **−0,00010`*`** |
| A45 − 45deploy — TIỀN 72h | +0,00048 | +0,00016 | +0,00062 | +0,00037 | +0,00037 |
| V5 − V1 — TIỀN 72h | +0,00074 | +0,00029 | −0,00041 | −0,00055 | −0,00055 |

⇒ **3 chỉ số LUẬT ~0 ở CẢ HAI bước, CẢ HAI horizon** ⇒ thước hợp lệ đúng chỗ dùng để quyết định.
🔶 **Khai báo trung thực:** `glift8`/`netm8` của bước *nhiễu* ở 4h = **−0,00010`*`** (**ngoài CI**, độ lớn
1e-4 ≈ 0,01 %, đúng chiều mong đợi: thêm nhiễu hại kinh tế chút ít) — **nhỏ hơn ~10×** mọi chênh lệch kinh tế
đang bàn và **không** đảo kết luận nào.

### 5.2 `auc8c` (AUC@top8 **ĐÚNG**; bản `auc8` có lỗi đếm cặp đã errata) + KINH TẾ — TIỀN 4h

| arm | `auc8c` | `netm8` | `glift8` |
|---|---|---|---|
| **MRA4** | **0,41530`*`** | −0,00769 | +0,00037 |
| **MRB8** | **0,33488`*`** | −0,00785 | +0,00021 |
| **MRB32** | **0,39823`*`** | −0,00785 | +0,00021 |
| 45deploy | 0,61394`*` | −0,00785 | +0,00021 |
| A45 | 0,61443`*` | −0,00779 | +0,00027 |
| V5 | 0,60794`*` | −0,00799 | +0,00007 |

⇒ Ở tầng **chọn coin vào top-8**, **mọi** model mới **kém ngẫu nhiên** (`auc8c < 0,5`) và **kém đối chứng ~0,21–0,28**.
**Kinh tế theo top-8 vì thế không thể tốt hơn** — kết luận **không** phụ thuộc chỉ số lỗi `auc8`.

## 6. NHÃN (b) — PnL THẬT THEO LUẬT THOÁT

### 6.1 Cổng chi phí §4.3 — **ĐÓNG: PASS** (đo được, `cost_report.json` của kernel `mr-labelb-cpu`)

| chỉ số | giá trị |
|---|---|
| **Thời gian khoảng-fold ĐẦU** (`i00_20220401`) | **12,5 phút** (ngưỡng cổng = **120**) ⇒ **PASS** |
| Tổng build **15 fold** | **165,7 phút** (1 phiên CPU Kaggle) |
| Per-interval | 4,3 → 25,6 phút (tăng theo số coin/tick) |
| RAM đỉnh | **7,86 GB** |
| Ngày 1m đã parse | **1.438** ngày (9 dataset `wfo-ticker-*`), **0 ngày thiếu** |
| Mô phỏng engine | **309.024** cặp `(tick, coin)`, `noentry = 0` |
| `OPEN_AT_END` | **113** (0,037 %) — cắt cuối cửa sổ, **đã loại khỏi nhãn** |
| Engine | gọi **thẳng** `research/exitfit/exit_engine.simulate` — **không** chạy Java/sim ở đâu |

**Khai báo điểm chưa hoàn hảo:** do chia khối 90 ngày, **8 ngày cuối của khối 1 trong mỗi interval bị BỎ** ⇒ thiếu
**~22,8k / 331,8k ≈ 6,9 %** cặp nhãn, **rải rác 15 chỗ** (không dồn một phía). Đã kiểm: fold đầu `K=8` vẫn còn
**7.376 dòng** ≫ guard 2.000 ⇒ **không** ảnh hưởng kết luận, nhưng **có** làm nhẹ tập train.

### 6.2 Thống kê nhãn vàng

| pool | dòng nhãn | `hold_min` TB | `gross` TB | **`net` TB** | lý do thoát |
|---|---|---|---|---|---|
| **K = 8** | 77.256 | 3.267 (54h) | **+0,01201** | **+0,00401** | TRAIL 61.003 · TS168 16.189 · OPEN_AT_END 64 |
| **K = 32** | 309.024 | 3.729 (62h) | **+0,01268** | **+0,00468** | TRAIL 234.704 · TS168 74.207 · OPEN_AT_END 113 |

**Đọc cho đúng (rất dễ đọc sai):** kỳ vọng **TUYỆT ĐỐI** của pool dương (~**+0,40 %** net/trade ở top-8),
nhưng (i) đó là kỳ vọng của **CHIẾN LƯỢC** arm+7 %/gap-3 %/time-stop-168h trên **nhóm coin S1 chọn**, **KHÔNG**
phải kỹ năng xếp hạng; (ii) **top-8 KHÔNG tốt hơn top-32** (+0,401 % vs +0,468 %) ⇒ thứ tự S1 **không** cộng
thêm giá trị; (iii) nhãn (b) dùng **nhánh WEAK gap 3 %**, **không funding** ⇒ **KHÔNG** phải PnL của LIVE.

## 7. KHAI BÁO TRUNG THỰC — **KHÔNG** ĐƯỢC NÓI GÌ TỪ BẢNG TRÊN

1. **KHÔNG** được nói "có ranker kiếm được tiền": `netm8` **âm** ở mọi biến thể/horizon; Δ`glift8`/Δ`netm8`
   so đối chứng **TRONG CI**; gross lift tốt nhất **+0,311 %/72h < 0,8 % phí**.
2. **KHÔNG** được nói model mới "tốt hơn" nói chung: nó **tệ hơn hẳn** ở thước NHÃN (§3.3) và ở `auc8c` (§5.2).
3. **KHÔNG** được gọi `MRA72` là "rank 4h" hay `MRA4/MRB*` là "rank 72h": slot/horizon đã ghi rõ ở §3.2.
4. `K = 8` vs `K = 32` là **2 mức của cùng một trục**, không phải 2 bằng chứng độc lập (**k = 2 = 2 NHÃN**).
5. Nhãn (b) là **bản bảo thủ** (WEAK gap, không funding, 1 leg, không DCA/gate/sizing) — **KHÔNG** phải equity.
6. Model (b) **chỉ thấy pool khi train** ⇒ điểm ngoài pool là **ngoại suy**; bảng §3 là bảng **QUYẾT ĐỊNH**
   (mọi coin), bảng §3.4 là **đối chiếu công bằng trong pool**.
7. `glift8`/`netm8` của bước kiểm *nhiễu* ở 4h **ngoài CI** (1e-4) — đã khai §5.1.
8. **Deviation hạ tầng (đã khai trong AMEND 1):** `train_rows` trả nhãn `float64` thay `int8`; với nhãn nhị phân
   giá trị vẫn 0,0/1,0 và XGBoost nhận `float32` nội bộ ⇒ đường `bin` **giữ nguyên hành vi** (kiểm bằng dtype,
   **không** retrain lại để so byte). Vòng này **không** retrain đường `bin`.
9. **Chưa làm:** chấm `MRA*`/`MRB*` trên `retEnd_12h/24h`; `rank:pairwise`/`lambdarank` (cơ chế rank) — để vòng sau.

## 8. VIỆC BỎ + LÝ DO (theo thứ tự ưu tiên đã chốt §7)

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | (a) `h = 4h` | ✅ XONG (43,0 phút GPU) | — |
| 2 | (a) `h = 72h` | ✅ XONG (42,5 phút GPU) | — |
| 3 | (b) `K = 8` | ✅ XONG (nhãn 165,7 phút CPU + train 6,6 phút) | cổng §4.3 PASS (fold đầu 12,5 phút ≪ 120) |
| 4 | (b) `K = 32` | ✅ XONG (train 4,4 phút; dùng lại 1 lần build nhãn) | `K=8 ⊂ K=32` |
| 5 | chấm thêm `12h/24h` | ⛔ BỎ | ngoài thứ tự ưu tiên đã chốt; không đổi câu trả lời (mọi horizon cho cùng hình: thứ tự tăng, kinh tế đứng yên) |
| 6 | `rank:pairwise`/`lambdarank` | ⛔ BỎ | pre-reg §3 nói rõ vòng này 1 cơ chế (hồi quy); dành vòng sau |

**Không** nới ngưỡng · **không** tự tích hợp · **không** chạm ONNX/LIVE/2026 · **không** push.

## 9. KẾT LUẬN CUỐI + KHUYẾN NGHỊ

1. **Có** tín hiệu xếp hạng quy ra tiền **ở tầng thống kê**: cả **2 nhãn độc lập** ((a) rank liên tục, (b) PnL
   thật theo luật thoát) đều tạo ranker **PASS luật §6** và **vượt `45deploy` + cả 2 đối chứng ngoài CI** ở
   `ic`/`pacc`/`dec_mono`; nhãn (b) còn vượt **trong pool ứng viên** (`pacc` 0,5157 vs 0,4948).
2. **Nhưng KHÔNG có lợi thế KINH TẾ**: Δ`glift8`/Δ`netm8` so đối chứng **trong CI**, `netm8` **âm** ở mọi
   biến thể, lift gross tốt nhất **+0,311 %/72h < 0,8 % phí**, và skill **đảo chiều/tan biến** trên thước NHÃN
   và `auc8c`. ⇒ Phần tăng thêm là **khớp mục tiêu train**, không phải thông tin mới.
3. **"Sai ở bước nào" (câu trả lời cuối):** **MỤC TIÊU/ĐẶC TRƯNG.** Đổi nhãn sang chính đại lượng tiền
   (2 cách khác nhau) **không** tạo ra kỹ năng tiền ở tầng chọn coin.
4. **GIỮ `45deploy`** (45 feature, nhãn nhị phân `retEnd_4h > 0,015`). **Không** đổi sang đầu hồi quy — rủi ro
   ONNX/LIVE cao, lợi ích đo được = 0.
5. Vòng sau chỉ nên đi vào **(i) feature mới**, **(ii) cơ chế rank (`rank:pairwise`/`lambdarank`)**, hoặc
   **(iii) cấu trúc chọn top-K** — **không** tinh chỉnh loss/hyperparam của 45 feature hiện có.
