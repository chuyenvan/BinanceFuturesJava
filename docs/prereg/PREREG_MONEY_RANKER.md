# PREREG_MONEY_RANKER — NHÃN = **PnL THẬT theo luật thoát** (+ nhãn rank `retEnd_h`), 1 ranker, chấm bằng **THƯỚC TIỀN**

**Ngày chốt:** 2026-09-25 (viết **TRƯỚC** khi đọc bất kỳ số mới nào của vòng này) · **Nhánh:** `module`
**Trạng thái:** CHỐT — **không sửa thiết kế sau khi thấy kết quả** (chỉ được AMEND bằng commit riêng, ghi rõ
là sửa *trước khi đọc số của phần bị sửa*).
**Phạm vi:** DEV only (`2021-12-31 .. 2025-10-08`), **KHÔNG** chạm `2026`/`HoldoutSeal`.
**KHÔNG** chạm ONNX / `NUM_FEATURES` / `extractFeatures45` / LIVE. **KHÔNG push.**

---

## 0. CÂU HỎI VÀ 3 CÂU TRẢ LỜI BẮT BUỘC

**Câu hỏi quyết định:** *có tồn tại một **ranker XẾP HẠNG RA TIỀN** không?* (tức 45 feature + 16 fold DEV
hiện có, khi nhãn được thay bằng (a) rank `retEnd_h` **hoặc** (b) **PnL thật theo luật thoát**, có cho ra
một thứ tự coin **dự báo được tiền** — `pacc > 0,5` · `ic > 0` · `dec_mono > 0,5`, **ngoài CI** so với
**cả hai đối chứng** — hay không).

Bắt buộc trả lời cuối cùng:
1. **Có tồn tại ranker xếp hạng ra tiền không?** (nhãn (a)? nhãn (b)? hay **cả hai không**?)
2. Nếu **không** ⇒ kết luận dứt khoát: *không có tín hiệu xếp hạng quy ra tiền trong 45 feature hiện có*
   (và đó là câu trả lời cuối cho "sai ở bước nào").
3. Nếu **có** ⇒ so với `45deploy`: mạnh hơn bao nhiêu, và **có đáng đổi model không** (kèm cảnh báo
   ONNX/LIVE).

**Bối cảnh đã đo (không diễn giải lại):** trên **thước TIỀN** (`y = retEnd_h`), **MỌI** arm đã đo đều
`ic < 0`, `pacc < 0,5`, `dec_mono < 0,5`, decile dốc ≈ 0 (`RESULT_MODEL_RULER.md` §14). Ở `h = 72h`, S1
(live ranker) có `pacc 0,5557*` trên **nhãn của nó** (`g1lite`) nhưng `pacc 0,46887*` / `ic −0,08690*`
trên `retEnd_72h` (`RESULT_H72.md` §3) ⇒ **kỹ năng nhãn không chuyển thành kỹ năng tiền, thậm chí NGƯỢC
DẤU**. Vòng này hỏi thẳng: **có nhãn nào (khác nhãn cũ) làm ra kỹ năng tiền không?**

---

## 1. RÀNG BUỘC (chốt)

1. **KHÔNG** `claude-run`/Claude Code.
2. **KHÔNG** chạy Java/sim trên Oracle (đang shadow LIVE).
3. ⚠️ **RAM Oracle**: máy bị coi là **thiếu RAM** ⇒ **mọi bước NẶNG (build nhãn, train) chạy trên KAGGLE
   (CPU/GPU)**; Oracle chỉ làm bước **NHẸ** (đọc/soạn/log/chấm). **Kiểm `free -g` TRƯỚC mỗi bước nặng**;
   nếu RAM Oracle `< 4 GB` thì **cấm** chạy bước nặng trên Oracle.
4. **KHÔNG push.** 5. **DEV only** — không chạm 2026/`HoldoutSeal`.
6. **Không tự tích hợp**, **không nới ngưỡng**, **không đổi luật quyết định** sau khi đọc số.
7. Mọi output tool giữ **THẬT NHỎ** (log ngắn, artifact parquet/bins).

---

## 2. ĐỊNH NGHĨA "KỸ NĂNG TIỀN" VÀ THƯỚC

- **Thước TIỀN:** `y = retEnd_h` (cột **có sẵn** trong `funding_label_*.pb`, `h ∈ {4h, 72h}`, `nBars_h ≥
  H/15m`). Ghi rõ quy ước: `retEnd_h` là **gross**; mọi chỉ số *thứ tự* của thước (`ic`, `pacc`,
  `dec_mono`, `dec_rho`, `glift@K`) **bất biến** với phép dịch hằng số `− FEE_RT` (`FEE_RT = 0,008`);
  riêng `netm@K` **có** trừ phí (do `model_ruler.tick_metrics` trừ). ⇒ "nhãn `retEnd_h` net" và
  "`retEnd_h` gross" cho **cùng** thứ hạng trong tick.
- **Thước NHÃN (đối chiếu):** `maxFav_h` (CHẠM, `max(high(τ)/close(t) − 1)` trên `(t, t+h]`) — **cùng
  thước mà `RESULT_MODEL_RULER`/`RESULT_H72` dùng để nói "có kỹ năng"**. Không trộn thước.
- **Chỉ số:** dùng **NGUYÊN** `research/analysis/model_ruler.tick_metrics` (không viết lại): `ic`,
  `pacc`, `dec_mono`, `dec_rho`, `glift8/12/16`, `netm8/12/16`, `auc8`, `lift8/12/16`, `base`.
  - `pacc`/`dec_mono`/`auc8` có **mốc vô dụng = 0,5**; `ic`/`dec_rho`/`glift`/`netm` có **mốc vô dụng = 0**.
- **CI:** `stage2_score.block_boot_mean`, `BLOCK_H = 72`, `NREP = 2000`, `SEED = 20260905`,
  `inflate(k = 2)` (`c3_rates`) = **1,177410**. "`*`" = **ngoài CẢ HAI** độ rộng (raw + honest-inflated),
  đúng hàm `model_ruler.decide`.
- **K (multiplicity):** **k = 2 nhãn** (a) và (b) là **hai phép kiểm chính**; trong mỗi nhãn có 2 biến thể
  (`h ∈ {4h,72h}` cho (a); `K ∈ {8,32}` cho (b)) ⇒ **4 biến thể**, dùng `inflate(k = 2)` như đã chốt và
  **kêu tên đủ 4** (không chọn cái đẹp). `K_SEL = 8` (số coin hệ thống vào) và `K = 32` (tập train rộng)
  là hai **mức của cùng một trục**, không phải hai câu hỏi độc lập.

---

## 3. NHÃN (a) — RANK `retEnd_h` (rẻ, chạy trước)

- `y` = **`retEnd_h`** theo **từng tick**, `h ∈ {4h, 72h}`.
- **Cơ chế nhãn:** trainer hiện tại (`research/pipeline/g015_net_train_add.py`) **chỉ** có nhãn **nhị phân**
  (`y = (retEnd_h > thr)` / `(maxFav_h ≥ thr)`); **KHÔNG có cơ chế rank-label** (không `qid`, không
  `objective="rank:*"`). ⇒ Áp dụng đúng điều khoản đã cho: **dùng `y` LIÊN TỤC + chấm bằng Spearman-rank**.
- **Cụ thể:** `--label-kind cont` (**mới**, mặc định `bin` = hành vi cũ byte-identical) ⇒ `y = retEnd_h`
  (float32), bỏ lọc hai lớp; model = **`xgboost.XGBRegressor(objective="reg:squarederror",
  eval_metric="rmse")`**, mọi hyperparam/fold/seed/purge **giữ NGUYÊN** bản nhị phân trừ những thứ gắn với
  phân lớp (`scale_pos_weight`, `eval_metric="auc"` — khai báo là **N/A** với hồi quy).
- **KHÔNG** thử `rank:pairwise` trong vòng này (một vòng = một cơ chế; nếu (a) NULL thì cơ chế rank có thể
  là biến thể vòng sau — ghi ở §10).

## 4. NHÃN (b) — **GOLD: PnL THẬT THEO LUẬT THOÁT** (đắt, chạy sau)

### 4.1 Định nghĩa (chốt)

`PnL(t, sym)` = kết quả của **chính state machine thoát** của `research/exitfit/exit_engine.py`
(tái hiện đúng `devrun/X1_GS_T170_2021` — **PARITY PASS**, `RESULT_EXIT_FIT.md` §1) nếu **vào lệnh ở `t`**:

- **Entry:** `E = close(t)` — giá **đóng** của nến 1m tại đúng phút `t` (t = tick lưới 15m).
- **1 leg duy nhất** (không DCA/merge) ⇒ không có đường merge, không dùng `qty`/`level`.
- **Phễu thoát (nguyên văn engine):** arm khi `high ≥ E × 1,07` (đỉnh = **HIGH** nến 1m); sau arm
  `SL = normalizeFloor(E × (1 + trailRate))`; `trailRate = round(peak − gap, 0,005)`;
  `gap = min(peak × 0,5, cap)`; ratchet **liên tục**; bất biến **SL > entry**;
  `BLOCK_INTRABAR_LOOKAHEAD` (không khớp nội nến — khớp từ nến sau); khớp giá `min(priceSL, open)`;
  **loser time-stop 168h** (`priceSL == null` và `t − t0 > 168h`) khớp `min(open, close)`;
  delist guard (im lặng > 2 ngày ⇒ đóng tại `lastPrice`); còn mở cuối cửa sổ ⇒ `OPEN_AT_END`.
- **`cap` (hằng số gap):** dùng **nhánh WEAK `TS_MAX_GAP_WEAK = 0,03`** cho **MỌI** ứng viên, tức chạy
  engine với `pred = None` (theo `gap_p0`: `pred is None ⇒ CAP_WEAK`). **Lý do + khai báo:** bản thật
  chọn WEAK/STRONG **theo `symbolPred`** — mà `symbolPred` chính là điểm của ranker đang được đánh giá ⇒
  dùng nó sẽ **vòng tròn**. ⇒ Nhãn (b) là **bản BẢO THỦ** (gap trần 3%), **không phải bản sao 1:1 của
  lệnh LIVE**; khác biệt này **khai báo trước** và **áp đều** cho mọi ứng viên/đối chứng.
- **PnL:** `gross(t, sym) = tp/E − 1`; **`net = gross − 0,008`** (`RATE_FEE 0,002 + SLIPPAGE 0,003 × 2`,
  khớp `model_ruler.FEE_RT`). **KHÔNG trừ funding** (`funding` trong `printDone.csv` là của lệnh cũ, không
  suy ra được cho entry tùy ý; khai báo trước). **Nhãn train = `net`** (bất biến thứ tự với `gross`);
  parquet lưu **cả** `gross` để chấm bằng `tick_metrics` (để `netm8` tự trừ phí, không trừ hai lần).
- **Nguồn giá 1m:** `ticker_YYYYMMDD.bin(.gz)` — cùng nguồn sim (`TICKER_SOURCE=file`), đọc bằng
  `research/analysis/jbin.py`. **Cửa sổ trước = 168h**; nến nào thiếu thì **bỏ qua** (như sim).

### 4.2 Tập ứng viên (chốt trước)

**Top-K theo điểm S1 mỗi tick** — `K ∈ {8, 32}` — trên nguồn **có sẵn**
`/home/ubuntu/ledger/pred_s1a2x1.parquet` (6.573.909 dòng `(ts, sym, score)`, `score` **THẤP = TỐT**,
walk-forward 16 fold, `ts` 2021-12-31 17:30 → 2025-12-31 16:45).
- `K = 8` = **đúng cái hệ thống vào** (K_SEL của ruler). `K = 32` = rộng hơn để **train**.
- **Phủ fold (khai báo TRƯỚC):** S1 **không có điểm trước `2021-12-31 17:30`** ⇒ fold `20220101`
  (`tr_cut = 2021-12-29`) có **0 dòng train** ⇒ **`fold 20220101 = N/A` cho nhãn (b)**; nhãn (b) train trên
  **15 fold** `20220401..20251001`. Vì so sánh phải ghép cặp, **bảng TIỀN chính của cả 4 biến thể mới +
  đối chứng sẽ in ở CẢ HAI tập fold** (16 fold và 15 fold) để thấy rõ tập nào.
- **Nhãn (b) chỉ có ở ứng viên** ⇒ ranker (b) **chỉ thấy ~top-32/379 coin mỗi tick khi train**. Hệ quả
  **khai báo trước**: điểm của model (b) trên coin **ngoài** pool là **ngoại suy**; do đó ngoài bảng chính
  (mọi coin, có điểm), in **thêm bảng PHỤ giới hạn trong pool ứng viên** (`rank trong pool`) — bảng chính
  vẫn là bảng quyết định (để so được với mọi số cũ).
- **Hiện vật nhãn (b) build vòng này** = **CHỈ để train ranker (b)**; **KHÔNG** dùng để suy ra PnL của hệ
  thống (không phải equity, không phải kết quả live).

### 4.3 CỔNG CHI PHÍ (chốt TRƯỚC — đo rồi mới làm tiếp)

Chạy **1 fold trên KAGGLE**, in `wall-time/fold` + `RAM peak`. Luật:
- **> 2 giờ/fold** (hoặc ước tính tổng > **1 phiên** Kaggle, tức > 8h) ⇒ **DỪNG**, ghi rõ **KHÔNG làm
  tiếp**, **fallback về (a)**. Không cố, không cắt tham số để lách cổng.
- Nếu **lọt cổng** ⇒ build nhãn (b) cho **15 fold** (mọi tick `ts < 2025-10-01`, đủ cho `tr_cut` của mọi
  fold), ghi parquet `(ts, symId, gross, E, tp, exit_ts, reason, hold_min, n_arm)`.

## 5. TRAIN (chung cho (a) và (b))

| mục | giá trị |
|---|---|
| đặc trưng | **45 cột** (`f0..f39` Tool1 15m + 5 OI) — **KHÔNG** thêm/bớt |
| fold | **16 fold** `20220101..20251001` (nhãn (a)); **15 fold** (nhãn (b), xem §4.2) |
| purge | `PURGE_STEPS = 288` × 15m = **72h**; `assert ts_max < cutoff` mỗi fold |
| seed / nest | `42` / `400`; `max_depth 5`, `lr 0,05`, `subsample 0,8`, `colsample_bytree 0,8`, `min_child_weight 20`, `tree_method hist` |
| objective | `reg:squarederror` (hồi quy trên `y` liên tục) |
| device | `cuda` (Kaggle GPU) — **KHÔNG** chạy Oracle |
| điểm OOS | ghi `predict_wf_<cutoff>.bin` (26 B/rec) vào thư mục **MỚI**; **KHÔNG** ghi đè bins deploy |
| đối chứng | `45deploy` (`claudedata/predwf_G015x26`), `A45` (`ruler_bins/g015p2-arm44-gpu/stage2/A45`), `V5`, `V1` (`ruler_bins/g015p2-stage2-featvar-gpu/stage2/*`) — **dùng nguyên, không retrain lại** |

## 6. LUẬT QUYẾT ĐỊNH (chốt TRƯỚC — "có kỹ năng tiền")

Một biến thể được gọi là **CÓ KỸ NĂNG TIỀN** khi **cả ba** điều đúng **trên thước TIỀN**:

1. `pacc > 0,5`, **VÀ**
2. `ic > 0`, **VÀ**
3. `dec_mono > 0,5`,

và **cả ba** phải **ngoài CI** (raw + inflated) so với **CẢ HAI đối chứng** = **`A45`** (bước *retrain*) và
**`V5`** (bước *nhiễu*). So với **`45deploy`** là **bảng bắt buộc** nhưng **không** là điều kiện (vì
`45deploy` train bằng device/nhãn khác).

**Kiểm tính hợp lệ của chính thước (bắt buộc in):** `Δ(A45 − 45deploy)` và `Δ(V5 − V1)` phải **~ 0**
(không ngoài CI); nếu **không** ~ 0 thì **thước đang bắt nhiễu** ⇒ mọi kết luận GO phải hạ xuống
"không kết luận".
**Không nới ngưỡng.** Chỉ số **không tính được** ⇒ **KHÔNG** tính là PASS.

**Bảng bắt buộc in (mỗi biến thể × mỗi thước):** `ic` · `pacc` · `dec_mono` · `dec_rho` · `glift8` ·
`netm8` (+ `auc8`, `lift8`, `base`, `n_tick`), `*` = ngoài CI.

## 7. THỨ TỰ ƯU TIÊN (chốt TRƯỚC — không chọn cái đẹp)

1. **(a) `h = 4h`** (rẻ nhất, chạy ngay) 2. **(a) `h = 72h`** 3. **(b) `K = 8`** 4. **(b) `K = 32`**
Nếu cạn ngân sách ⇒ dừng **theo đúng thứ tự này** và **ghi rõ mục nào bỏ + lý do**.

## 8. KHAI BÁO TRƯỚC — ĐIỂM MÙ / RỦI RO (để không bị đọc thành "phát hiện")

1. **Pool bias (§4.2):** ranker (b) train trên ~8% pool ⇒ điểm ngoài pool là ngoại suy.
2. **Nhánh WEAK gap cho MỌI ứng viên (§4.1):** thoát bảo thủ hơn bản LIVE dùng `pred`.
3. **Không funding.**
4. **`K = 8` vs `K = 32`** là 2 mức của cùng trục ⇒ không tính là 2 bằng chứng độc lập.
5. **Nhãn (b) không phải equity của hệ thống** (1 leg, không DCA, không gate/funding/sizing).
6. **Nhiều tick vẫn có `y` rất dày đuôi** (retEnd và PnL đều lệch mạnh) ⇒ `reg:squarederror` có thể bị
   chi phối bởi đuôi; **khai báo**, không đổi loss giữa đường.
7. **Fold 0 N/A cho (b)** (§4.2).
8. **`45deploy` là artifact cũ** (device `cuda`, 18 cutoff) ⇒ mọi so sánh phải kèm `A45` (mốc retrain
   cùng buổi) — đúng như `PREREG_STAGE2_FEATVAR §6`.
9. **Bằng chứng tiền để NULL:** nếu (a) và (b) đều NULL thì **không** đi tìm nhãn thứ 3 trong vòng này.

## 9. DỰ ĐOÁN KHAI TRƯỚC (để kiểm độ trung thực, KHÔNG dùng để chọn nhãn)

- **Q1.** Nhãn (a) `h = 4h`: `ic ≈ 0` (|ic| < 0,02), `pacc ≈ 0,5`; nhiều khả năng **âm** (theo `§14`
  của `RESULT_MODEL_RULER`). → dự đoán **NULL**.
- **Q2.** Nhãn (a) `h = 72h`: `|ic|` nhỏ, `pacc < 0,5` thiên âm (theo `RESULT_H72` §3). → **NULL**.
- **Q3.** Nhãn (b): `ic > 0` **không** đạt đồng thời `pacc > 0,5` — dự đoán **NULL**; nếu có, `glift8 > 0`
  nhưng **nhỏ** (|glift8| < 0,005).
- **Q4.** `Δ(A45 − 45deploy)` và `Δ(V5 − V1)` **~ 0** ở mọi chỉ số chính (thước hợp lệ).
- **Q5.** Nhãn (b) `K = 32` cho CI **hẹp hơn** `K = 8` (nhiều dòng train hơn) nhưng **cùng dấu**.
- **Q6.** Cổng chi phí: nhãn (b) **lọt** (dự đoán ~10–40 phút cho toàn bộ 15 fold, vì parse 1 ngày 1m ≈
  1,6 s và chỉ cần ~1.390 file).

## 10. NẾU (a) VÀ (b) ĐỀU NULL — PHÁT BIỂU CUỐI

*Không có tín hiệu xếp hạng quy ra tiền trong 45 feature hiện có*: cả nhãn **nhị phân cũ**, cả **rank liên
tục `retEnd_h`**, cả **PnL thật theo luật thoát** đều không tạo được thứ tự coin dự báo được tiền ⇒ **bước
sai là MỤC TIÊU/ĐẶC TRƯNG**, không phải mô hình hay ngưỡng. Vòng sau (khi owner yêu cầu) chỉ nên đi vào
(1) **cơ chế rank** (`rank:pairwise`/`lambdarank` với `qid`) và (2) **feature mới** — **không** tinh chỉnh
hyperparam của 45 feature hiện có.

---

## AMEND 1 (2026-09-25, TRƯỚC khi push kernel train nhãn (b) — chưa đọc số nào của (b))

**Chỉ 1 điều, thuần KỸ THUẬT, không đổi luật/khoa học:** thêm cờ `--min-train` (mặc định **5000** = hành vi cũ)
cho guard `len(train) >= 5000` của trainer, và 2 arm nhãn (b) chạy với `--min-train 2000`.
Lý do: pool ứng viên của (b) chỉ ~top-32/255 coin mỗi tick ⇒ fold ĐẦU (`20220401`, cửa sổ ~88 ngày)
chỉ có ~5,3k dòng train — sát ngưỡng guard cũ ⇒ rủi ro **lỗi hạ tầng**, không phải lỗi khoa học.
Guard này **KHÔNG phải ngưỡng quyết định**; mọi ngưỡng của LUẬT §6 **giữ nguyên**.

**Ghi nhận kèm (đã kiểm bằng lập luận dtype, không retrain):** `train_rows` nay trả nhãn `float64` thay vì
`int8`; với nhãn nhị phân giá trị vẫn `0,0/1,0` và XGBoost nhận `float32` nội bộ ⇒ đường `bin` **giữ nguyên
hành vi**. `--min-train` mặc định 5000 ⇒ các arm (a) (kernel đã push trước AMEND này, không truyền cờ)
hành vi không đổi.
