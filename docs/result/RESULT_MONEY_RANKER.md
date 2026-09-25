# RESULT_MONEY_RANKER — CÓ ranker xếp hạng RA TIỀN không? (nhãn (a) rank `retEnd_h` · nhãn (b) PnL thật theo luật thoát)

**Ngày:** 2026-09-25 · **Nhánh:** `module` · **Trạng thái:** ĐO XONG **nhãn (a)** + chấm 2 thước (offline;
**KHÔNG** chạm ONNX/LIVE, **KHÔNG** sim Java, **KHÔNG** chạm 2026/`HoldoutSeal`) · **KHÔNG push**
**Pre-reg:** `docs/prereg/PREREG_MONEY_RANKER.md` (commit `acd6523`, AMEND 1 `0b09c86`) — **chốt TRƯỚC** khi đọc số.
**Code:** `research/pipeline/mr_label_build.py` (nhãn b) · `research/pipeline/g015_net_train_add.py` (+`--label-kind cont`,
`--label-custom`, `--min-train`) · `research/analysis/money_ranker_score.py` (dùng **nguyên**
`model_ruler.tick_metrics` / `summarize` / `delta` / `ci_mean`) · `research/analysis/mr_tables.py`
**Chi phí:** 2 phiên Kaggle GPU (train) + 1 phiên Kaggle CPU (nhãn b) — số cụ thể ở §6.

---

## 0. TRẢ LỜI NGẮN (3 câu bắt buộc)

**1) CÓ tồn tại ranker xếp hạng RA TIỀN không?**
**CÓ — nhưng chỉ ở nghĩa THỐNG KÊ, KHÔNG ở nghĩa KINH TẾ.** Nhãn **(a)** (hồi quy `retEnd_h` liên tục, 45
feature, 16 fold) cho ra thứ tự coin **có kỹ năng tiền theo đúng luật đã chốt §6**: ở `h = 4h`
(`MRA4`) `pacc` **+0,50409`*`** · `ic` **+0,01208`*`** · `dec_mono` **+0,50538`*`**, **ngoài CI** so với
**cả hai** đối chứng (`A45` retrain, `V5` nhiễu) ⇒ **PASS**; ở `h = 72h` (`MRA72`) `pacc` **+0,50374`*`** ·
`ic` **+0,01098`*`** · `dec_mono` **+0,50689`*`** ⇒ **PASS**. Nhưng **lợi thế KINH TẾ thì ~0**: Δ`glift8`/Δ`netm8`
so với **cả hai** đối chứng đều **TRONG CI**, `netm8` vẫn **ÂM** (−0,00769 ở 4h; −0,00612 ở 72h), và mức
lift gross tốt nhất (**+0,311 %/72h**) vẫn **nhỏ hơn phí round-trip 0,8 %**.

**2) Nếu KHÔNG ⇒ ...** **Không áp dụng được** (câu 1 là "có, ở tầng thống kê"). Nhưng câu trả lời *có tính
quyết định* cho "sai ở bước nào" **giữ nguyên như `RESULT_MODEL_RULER` §14**: thứ tự coin **không quy ra
được tiền**. Vòng này **nâng** kết luận đó lên một bậc: **kể cả khi nhãn ĐƯỢC đổi thẳng sang chính đại
lượng tiền** (`retEnd_h` liên tục), tín hiệu tăng thêm **chỉ xuất hiện trên đúng họ chỉ số trùng với mục
tiêu train** (IC/pairwise/decile trên `retEnd`) và **biến mất / đảo dấu** trên mọi chỉ số khác (§3.3).

**3) So với `45deploy` và có đáng đổi model không?**
Mạnh hơn **có ý nghĩa thống kê**: Δ`ic` **+0,06319`*`** · Δ`pacc` **+0,02196`*`** · Δ`dec_mono` **+0,00945`*`**
(4h, so `45deploy`; tương tự so `A45`/`V5`). **NHƯNG**:
(a) **Δ`glift8` = +0,00016** và **Δ`netm8` = +0,00016` (TRONG CI)`** — tức **không** cải thiện kinh tế;
(b) ở **tầng NHÃN** (`maxFav_4h`) model mới **TỆ HƠN HẲN**: Δ`ic` **−0,32742`*`**, Δ`pacc` **−0,11429`*`**,
Δ`lift8` **−0,18461`*`** (top-8 ≈ 0,061 vs 0,272);
(c) ở **tầng chọn coin nhị phân** `auc8c` = **0,41530** vs **0,60794–0,61443** của đối chứng (top-8 theo
model mới **kém hơn ngẫu nhiên** ở thước này).
⇒ **KHÔNG đáng đổi model.** Kèm **cảnh báo ONNX/LIVE**: đổi sang đầu HỒI QUY là đổi *ngữ nghĩa điểm*
(`P(win)` → *dự báo lợi suất*), phải chỉnh lại `NUM_FEATURES`/`extractFeatures45`, ngưỡng cổng
(`net015 = retEnd_4h > 0,015`) và cách chọn top-8 — **rủi ro cao, lợi ích kinh tế đo được = 0** ⇒ **KHÔNG**.

---

## 1. CÁCH ĐO (đúng pre-reg §2–§7)

- **Nhãn (a) — rank `retEnd_h`:** `y = retEnd_h` (cột **có sẵn** trong `.pb`, `h ∈ {4h,72h}`, `nBars_h ≥ H/15m`).
  Trainer **không có cơ chế rank-label** (không `qid`/`rank:*`) ⇒ đúng điều khoản đã cho: **`y` LIÊN TỤC +
  chấm Spearman-rank**; model = `XGBRegressor(reg:squarederror, rmse)`, **giữ nguyên** 45 feature / 16 fold
  `20220101..20251001` / purge 72h / `seed 42` / `nest 400` / `depth 5` / `lr 0,05` / `subsample 0,8` /
  `colsample 0,8` / `min_child_weight 20` / `hist` / GPU (`scale_pos_weight`+`auc` = N/A với hồi quy).
- **Thước TIỀN:** `y = retEnd_h` (gross; mọi chỉ số thứ tự bất biến với dịch `−0,008`), `netm@K` có trừ phí.
  **Thước NHÃN:** `y = maxFav_4h` (CHẠM). **Chỉ số:** **nguyên** `model_ruler.tick_metrics` (không viết lại).
- **CI:** `stage2_score.block_boot_mean`, `BLOCK_H=72`, `NREP=2000`, `SEED=20260905`; in **cả hai** độ rộng:
  **`*` = ngoài theo `model_ruler.decide` (hệ số 1.21 — CHẶT HƠN)** và **`+` = ngoài theo `inflate(k=2)=1,177410`**
  (§2 pre-reg). **Luật dùng bản CHẶT (1.21)** ⇒ không có chuyện nới ngưỡng.
- **Đối chứng (dùng nguyên, không retrain):** `45deploy` (`claudedata/predwf_G015x26`), `A45`
  (`ruler_bins/g015p2-arm44-gpu/stage2/A45`), `V5`/`V1` (`ruler_bins/g015p2-stage2-featvar-gpu/stage2/*`).
- **4 biến thể (k = 2 nhãn × 2 mức):** `MRA4` = (a) `retEnd_4h` · `MRA72` = (a) `retEnd_72h` ·
  `MRB8`/`MRB32` = (b) PnL thật (pool top-8 / top-32) — xem §6.

## 2. TẦNG NHÃN (a) — ĐÃ TRAIN XONG (2 phiên GPU, 4 biến thể = 2 biến thể nhãn (a))

| arm | nhãn train | fold | n_train/fold | n_oos/fold | `p_mean` (OOS) | phút |
|---|---|---|---|---|---|---|
| **MRA4** | `retEnd_4h` liên tục | 16 (`20220101..20251001`) | 3,73M → 34,9M | 1,12M → 4,52M | +0,00059 … +0,00105 | **43,0** |
| **MRA72** | `retEnd_72h` liên tục | 16 | 3,71M → 34,7M | 1,12M → 4,52M | +0,00972 … +0,01199 | **42,5** |

Model + bins: `/kaggle/working/mr/{MRA4,MRA72}` (kernel `chuyendinh/mr-train-a-gpu`; đã tải về
`/tmp/mrbins/{MRA4,MRA72}`, gồm `model_f*_{4,72}h.json` + `predict_wf_*.bin`). **Không** ghi đè bins deploy.

## 3. BẢNG CHẤM (n_tick = 140.238, 16 fold, `base` = tỉ lệ nhãn nhị phân của tick)

`*` = ngoài CI (1.21, **chặt**) · `+` = ngoài CI (1.1774) · không dấu = trong CI.

### 3.1 THƯỚC TIỀN `h = 4h` — `y = retEnd_4h`

| arm | `ic` | `pacc` | `dec_mono` | `dec_rho` | `glift8` | `netm8` | `auc8` | `lift8` | `base` |
|---|---|---|---|---|---|---|---|---|---|
| **MRA4** | **+0,01208`*`** | **+0,50409`*`** | **+0,50538`*`** | +0,03335`*` | +0,00037`*` | **−0,00769`*`** | 0,42259`*` | +0,02447`*` | 0,17620 |
| 45deploy | −0,05111`*` | +0,48213`*` | +0,49594`*` | −0,02178`*` | +0,00021 | −0,00785`*` | 0,62393`*` | +0,11051`*` | 0,17620 |
| A45 (đối chứng retrain) | −0,05106`*` | +0,48214`*` | +0,49533`*` | −0,02170`*` | +0,00027 | −0,00779`*` | 0,62441`*` | +0,11085`*` | 0,17620 |
| V5 (đối chứng nhiễu) | −0,05186`*` | +0,48182`*` | +0,49591`*` | −0,02157`*` | +0,00007 | −0,00799`*` | 0,61762`*` | +0,10848`*` | 0,17620 |
| V1 | −0,05202`*` | +0,48174`*` | +0,49527`*` | −0,02111`*` | +0,00017 | −0,00789`*` | 0,61887`*` | +0,10910`*` | 0,17620 |

**Δ ghép cặp theo tick (n = 140.238):**

| Δ | `ic` | `pacc` | `dec_mono` | `glift8` | `netm8` |
|---|---|---|---|---|---|
| **MRA4 − 45deploy** | **+0,06319`*`** | **+0,02196`*`** | **+0,00945`*`** | +0,00016 (trong CI) | +0,00016 (trong CI) |
| **MRA4 − A45** | **+0,06314`*`** | **+0,02195`*`** | **+0,01006`*`** | +0,00010 (trong CI) | +0,00010 (trong CI) |
| **MRA4 − V5** | **+0,06394`*`** | **+0,02227`*`** | **+0,00948`*`** | +0,00030 (trong CI) | +0,00030 (trong CI) |

### 3.2 THƯỚC TIỀN `h = 72h` — `y = retEnd_72h`

| arm | `ic` | `pacc` | `dec_mono` | `dec_rho` | `glift8` | `netm8` | `auc8` | `lift8` | `base` |
|---|---|---|---|---|---|---|---|---|---|
| **MRA72** | **+0,01098`*`** | **+0,50374`*`** | **+0,50689`*`** | +0,03884`*` | +0,00311`*` | −0,00612 (CI) | +0,48107`*` | +0,00713 (CI) | 0,38900 |
| 45deploy | −0,08557`*` | +0,47006`*` | +0,48917`*` | −0,05237`*` | +0,00393 (CI) | −0,00531 (CI) | +0,47911`*` | −0,01406 (CI) | 0,38900 |
| A45 | −0,08509`*` | +0,47022`*` | +0,48978`*` | −0,05164`*` | +0,00430 (CI) | −0,00494 (CI) | +0,48075`*` | −0,01289 (CI) | 0,38900 |
| V5 | −0,09495`*` | +0,46659`*` | +0,48762`*` | −0,06394`*` | +0,00318 (CI) | −0,00605 (CI) | +0,47744`*` | −0,01515 (CI) | 0,38900 |

| Δ | `ic` | `pacc` | `dec_mono` | `glift8` | `netm8` |
|---|---|---|---|---|---|
| **MRA72 − 45deploy** | **+0,09655`*`** | **+0,03368`*`** | **+0,01773`*`** | −0,00082 (CI) | −0,00082 (CI) |
| **MRA72 − A45** | **+0,09607`*`** | **+0,03352`*`** | **+0,01711`*`** | −0,00118 (CI) | −0,00118 (CI) |
| **MRA72 − V5** | **+0,10594`*`** | **+0,03714`*`** | **+0,01927`*`** | −0,00007 (CI) | −0,00007 (CI) |

> **Lưu ý ghép cặp (khai báo):** `MRA72` chấm bằng **điểm slot 3** của chính nó với **nhãn 72h** (khớp
> horizon); các đối chứng **không** có điểm slot 3 (`z` = NaN 100 %, `DIAG_SCORE72H.md`) nên được chấm bằng
> **điểm slot 0 × nhãn 72h** (cross-horizon) — **đúng như `RESULT_MODEL_RULER`/`RESULT_H72`.**
> `MRA4` không có điểm slot 3 ⇒ chỉ chấm ở 4h; `MRA72` không có điểm slot 0 ⇒ chỉ chấm ở 72h.

### 3.3 THƯỚC NHÃN (đối chiếu) — `y = maxFav_4h` (CHẠM)

| arm | `ic` | `pacc` | `dec_mono` | `dec_rho` | `glift8` | `netm8` | `auc8` | `lift8` |
|---|---|---|---|---|---|---|---|---|
| **MRA4** | **−0,02927`*`** | **0,49008`*`** | **0,48406`*`** | −0,09757`*` | +0,00649`*` | +0,01587`*` | 0,56377`*` | +0,06107`*` |
| 45deploy | +0,29815`*` | 0,60437`*` | 0,66867`*` | +0,74898`*` | +0,02435`*` | +0,03373`*` | 0,78751`*` | +0,27221`*` |
| A45 | +0,29763`*` | 0,60418`*` | 0,66871`*` | +0,74831`*` | +0,02444`*` | +0,03382`*` | 0,78737`*` | +0,27229`*` |
| V5 | +0,30328`*` | 0,60634`*` | 0,67130`*` | +0,74941`*` | +0,02280`*` | +0,03218`*` | 0,78517`*` | +0,26489`*` |

| Δ (MRA4 −) | `ic` | `pacc` | `dec_mono` | `glift8` | `netm8` | `auc8` | `lift8` |
|---|---|---|---|---|---|---|---|
| 45deploy | **−0,32742`*`** | **−0,11429`*`** | **−0,18461`*`** | −0,01785`*` | −0,01785`*` | **−0,22374`*`** | −0,21114`*` |
| A45 | **−0,32690`*`** | **−0,11410`*`** | **−0,18465`*`** | −0,01795`*` | −0,01795`*` | **−0,22361`*`** | −0,21122`*` |
| V5 | **−0,33255`*`** | **−0,11626`*`** | **−0,18724`*`** | −0,01631`*` | −0,01631`*` | **−0,22141`*`** | −0,20382`*` |

**Đọc §3.1–§3.3 — đây là chỗ phải đọc cho đúng:**
1. `MRA4`/`MRA72` **thắng** trên **đúng họ chỉ số trùng với mục tiêu train** (thứ tự trên `retEnd`) và
   **thua đậm** trên mọi thứ khác: **thước NHÃN** (§3.3), **`auc8c`** (§4.1), và **kinh tế top-8** (§4.2).
2. `auc8` của `MRA4` = **0,42259`*`** (< 0,5) trong khi `45deploy` = 0,62393`*` ⇒ theo thước **nhị phân**
   trong top-8, model mới **kém hơn ngẫu nhiên**. `lift8` của `MRA4` = +0,024 vs **+0,111** của `45deploy`.
3. Nghĩa là: *"train thẳng vào đại lượng tiền"* làm điểm số **khớp hơn với đại lượng tiền** (hiển nhiên),
   **không** làm hệ thống chọn được coin tốt hơn ⇒ **hiệu ứng khớp mục tiêu, KHÔNG phải thông tin mới.**

## 4. KIỂM TÍNH HỢP LỆ CỦA THƯỚC VÀ KINH TẾ

### 4.1 `auc8c` (bản AUC@top8 **ĐÚNG** — bản `auc8` có lỗi đếm cặp đã errata) — thước TIỀN 4h

| arm | `auc8c` (CI chặt) |
|---|---|
| **MRA4** | **+0,41530`*`** [0,40650; 0,42456] |
| 45deploy | +0,61394`*` [0,60574; 0,62177] |
| A45 | +0,61443`*` [0,60626; 0,62238] |
| V5 | +0,60794`*` [0,60000; 0,61593] |
| V1 | +0,60914`*` [0,60112; 0,61716] |

⇒ Ở tầng **chọn coin trong top-8**, model mới **kém hơn ngẫu nhiên** (`< 0,5`) và **kém hơn đối chứng ~0,19**.
**Kết luận kinh tế không phụ thuộc chỉ số lỗi `auc8`** — đã kiểm bằng `auc8c`.

### 4.2 Kinh tế top-8 (đã trừ phí `FEE_RT = 0,008`)

- 4h: `netm8` = **−0,00769`*`** (MRA4) vs −0,00779 … −0,00799 (đối chứng) ⇒ **vẫn LỖ**; Δ so đối chứng **+0,00016 (CI)**.
- 72h: `netm8` = −0,00612 (MRA4/MRA72: **trong CI**) vs −0,00494 … −0,00605 ⇒ **vẫn LỖ**; Δ = **−0,00082 (CI)**.
- **Mức lift gross tốt nhất** của model mới: **+0,00311/72h ≈ +0,311 %** < **phí round-trip 0,8 %** ⇒ **dù có
  tin, cũng không phủ được chi phí giao dịch.**

### 4.3 KIỂM ĐỐI CHỨNG (bắt buộc, §6 pre-reg)

| Δ | `ic` | `pacc` | `dec_mono` | `glift8` | `netm8` |
|---|---|---|---|---|---|
| **A45 − 45deploy** (bước *retrain*) — TIỀN 4h | +0,00005 | +0,00001 | −0,00061 | +0,00006 | +0,00006 |
| **V5 − V1** (bước *nhiễu*) — TIỀN 4h | +0,00016 | +0,00007 | +0,00064 | **−0,00010`*`** | **−0,00010`*`** |
| A45 − 45deploy — TIỀN 72h | +0,00048 | +0,00016 | +0,00062 | +0,00037 | +0,00037 |
| V5 − V1 — TIỀN 72h | +0,00074 | +0,00029 | −0,00041 | −0,00055 | −0,00055 |

⇒ **3 chỉ số LUẬT (`ic`/`pacc`/`dec_mono`) đều ~0 ở CẢ HAI bước kiểm trên CẢ HAI horizon** ⇒ thước **hợp lệ
đúng chỗ dùng để quyết định** (không bắt nhiễu). **Khai báo trung thực:** `glift8`/`netm8` của bước *nhiễu*
ở 4h = **−0,00010`*`** (**ngoài CI**, độ lớn 1e-4 ≈ 0,01 %) — đúng chiều mong đợi (thêm nhiễu làm hại kinh
tế chút ít) và **nhỏ hơn ~10× so với mọi chênh lệch kinh tế đang bàn**; **không** đủ để đảo bất kỳ kết luận nào
ở đây (cả (a) cũng chỉ "PASS thống kê, kinh tế 0").

## 5. LUẬT §6 — KẾT QUẢ TỪNG BIẾN THỂ

| biến thể | `pacc`>0,5 | `ic`>0 | `dec_mono`>0,5 | ngoài CI vs A45 | ngoài CI vs V5 | **PASS** |
|---|---|---|---|---|---|---|
| **MRA4** (`retEnd_4h`, TIỀN 4h) | ✔ (*) | ✔ (*) | ✔ (*) | ✔ ✔ ✔ | ✔ ✔ ✔ | **PASS** |
| **MRA72** (`retEnd_72h`, TIỀN 72h) | ✔ (*) | ✔ (*) | ✔ (*) | ✔ ✔ ✔ | ✔ ✔ ✔ | **PASS** |
| MRB8 (PnL thật, K=8) | — xem §6 | | | | | — |
| MRB32 (PnL thật, K=32) | — xem §6 | | | | | — |

Kết quả **giống nhau ở cả bản CHẶT (1.21) và bản `inflate(k=2)` (1,1774)** ⇒ PASS không do chọn độ rộng.

## 6. NHÃN (b) — PnL THẬT THEO LUẬT THOÁT (trạng thái + chi phí ĐO ĐƯỢC)

- Định nghĩa đã chốt (§4 pre-reg): `entry = close(t)`, **1 leg**, gọi **thẳng**
  `research/exitfit/exit_engine.simulate` (harness PARITY PASS), **`pred = None` ⇒ nhánh WEAK `cap = 0,03`**
  cho **mọi** ứng viên (tránh vòng tròn), `gross = tp/E − 1`, `net = gross − 0,008`, **không funding**.
- Ứng viên: **top-32 theo điểm S1** (`pred_s1a2x1.parquet`) ⇒ 10.369 tick `ts < 2025-09-28`, **331.808 cặp
  (tick, coin)**; `K = 8` là **tập con** (mô phỏng không phụ thuộc K ⇒ chạy 1 lần).
- **Cổng chi phí (§4.3):** 🚧 **CHƯA HOÀN TẤT trong phiên này** — kernel CPU `chuyendinh/mr-labelb-cpu`
  **vẫn đang chạy** khi phiên kết thúc (đã chạy **> 2,7 giờ** tại thời điểm chốt báo cáo; **chưa** có
  `cost_report.json` ⇒ **KHÔNG ghi số chi phí khi chưa đo xong**).
  ⇒ **2 arm `MRB8`/`MRB32` KHÔNG được train trong phiên này** (`mr-train-b-gpu` đã soạn + dựng sẵn, chỉ chờ
  parquet nhãn). Đây là **việc còn nợ**, **không** phải kết quả.
- **Đã kiểm bằng chạy thử NHỎ trên dữ liệu thật** (`mr_label_build.py`, 9 ngày, 64 cặp): engine cho
  `reason ∈ {TRAIL, TS168}`, `OPEN_AT_END = 0`, `hold_min ≈ 4.174` (K=8) / `3.194` (K=32),
  `gross ≈ −0,0215` (K=8) / `+0,0273` (K=32) ⇒ đường ống **chạy đúng**, chỉ còn **tổng thời gian**.
- **Khai báo:** vì (a) **đã PASS**, việc (b) là **xác nhận bằng nhãn vàng**, không còn là điều kiện để trả lời
  câu (1); nó sẽ chốt "nhãn (b) có kỹ năng tiền không" khi kernel trả về.

## 7. KHAI BÁO TRUNG THỰC — NHỮNG GÌ **KHÔNG** ĐƯỢC NÓI TỪ BẢNG TRÊN

1. **KHÔNG** được nói "có ranker kiếm được tiền": `netm8` **âm** ở cả 2 horizon, Δ kinh tế so đối chứng **trong CI**,
   gross lift tốt nhất **+0,311 %/72h < 0,8 % phí**.
2. **KHÔNG** được nói model mới "tốt hơn" nói chung: nó **tệ hơn hẳn** ở thước NHÃN (§3.3) và ở `auc8c` (§4.1).
3. **KHÔNG** được gọi `MRA4`/`MRA72` là "rank 72h/4h": `MRA72` chấm bằng **điểm slot 3 × nhãn 72h**;
   đối chứng chấm **cross-horizon** (§3.2) — đúng như các vòng trước, **không** phải cùng điều kiện.
4. `K = 8` vs `K = 32` là 2 mức của **cùng một trục**, không phải 2 bằng chứng độc lập (k = 2 = 2 nhãn).
5. Nhãn (b) là **bản bảo thủ** (WEAK gap 3 %, không funding, 1 leg, không DCA/gate/sizing) — **KHÔNG** phải
   equity của hệ thống.
6. `glift8`/`netm8` của bước kiểm *nhiễu* ở 4h **ngoài CI** (1e-4) — đã khai ở §4.3.
7. **Deviation hạ tầng (khai báo):** `train_rows` nay trả nhãn `float64` thay `int8`; với nhãn nhị phân giá
   trị vẫn 0,0/1,0 và XGBoost nhận `float32` nội bộ ⇒ đường `bin` **giữ nguyên hành vi** (kiểm bằng dtype,
   **không** retrain lại để so byte). Vòng này **không** retrain đường `bin` nên không ảnh hưởng số nào.
8. **Việc còn nợ:** nhãn (b) + 2 arm `MRB8`/`MRB32` (§6); chưa chấm `MRA*` trên `retEnd_12h/24h`.

## 8. VIỆC NÀO BỎ + LÝ DO (theo đúng thứ tự ưu tiên đã chốt §7)

| # | việc | trạng thái | lý do |
|---|---|---|---|
| 1 | (a) `h = 4h` train đủ 16 fold | ✅ **XONG** (43,0 phút) | — |
| 2 | (a) `h = 72h` train đủ 16 fold | ✅ **XONG** (42,5 phút) | — |
| 3 | (b) `K = 8` | ⛔ **BỎ trong phiên này** | nhãn (b) **chưa build xong** (kernel CPU còn chạy > 2,7 h) ⇒ **cổng chi phí không đóng được**; đúng §4.3 "không cố, không cắt tham số để lách cổng" |
| 4 | (b) `K = 32` | ⛔ **BỎ** (cùng lý do #3) | pool top-32 cần nhãn (b); `K=8 ⊂ K=32` nên cả hai cùng bị chặn |

**Không** nới ngưỡng, **không** tự tích hợp, **không** chạm ONNX/LIVE/2026, **không** push.

## 9. KHUYẾN NGHỊ (chỉ đọc-được, không tự làm)

1. **GIỮ `45deploy` (45 feature, nhãn nhị phân `retEnd_4h>0,015`).** Không đổi sang đầu hồi quy.
2. Nếu muốn cải thiện **kinh tế** (không phải IC), vòng sau phải đi vào **feature mới** hoặc **cấu trúc
   chọn top-K** — **không** tinh chỉnh loss/hyperparam của 45 feature hiện có, vì vòng này đã chứng minh
   "khớp mục tiêu" chỉ làm đẹp chỉ số, không làm ra tiền.
3. Việc **còn nợ**: đóng cổng chi phí nhãn (b) rồi train `MRB8`/`MRB32` (kernel đã dựng sẵn).
