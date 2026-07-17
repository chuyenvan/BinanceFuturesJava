# SL4H — Label "stop-loss cứng sau 4h" (long-only, bỏ GATE, chỉ SELECTOR)

Thử nghiệm label MỚI cho model chọn coin (selector). Vào lệnh long tại `t`; nếu trong 4h giá
chạm target +n% thì THẮNG (chốt/arm SL), nếu không thì ĐÓNG CỨNG tại mốc 4h. Train 3 model
regressor cho n = 6 / 9 / 15 (%).

> TÁCH BIỆT với CDC n=3 (task 157 `dca-hard-label-157`): mọi thứ ở đây đặt tên `sl4h_n6/n9/n15`,
> id kernel `chuyendinh/sl4h-train-nX`, output `sl4h_nX_results.json`, thư mục
> `orchestrator/kernels_sl4h/`. KHÔNG đụng file/naming của kernel/dataset task 157.

## 1. Định nghĩa label (score — regression, đơn vị %)

Với mỗi anchor `(coin, t)` trên lưới 15m, dùng cột CÓ SẴN trong `funding_label.csv`:

- **HIT**: `maxFav_4h >= n/100` (kèm `nBars_4h >= 16` = đủ cửa sổ 4h) → `score = n`
- **MISS**: `ret4h = retEnd_4h * 100`
  - `ret4h < 0`  → `score = 1.5 * ret4h`  (phạt 1.5× phần âm)
  - `ret4h >= 0` → `score = ret4h`

Model: **XGBRegressor** dự đoán `score` (không phải binary). Params khớp selector chuẩn
(n_estimators=400, max_depth=5, lr=0.05, subsample/colsample=0.8, min_child_weight=20, tree_method=hist).

## 2. x / y đề xuất (lý do bất đối xứng)

- **x = n** (điểm thưởng khi HIT): dùng thẳng target % làm phần thưởng dương. Coin nào target
  cao hơn (n=15) mà HIT thì đáng điểm hơn coin n=6 HIT — score tự phản ánh biên lời kỳ vọng.
- **y = 1.5** (hệ số phạt nhánh âm): đóng cứng tại mốc 4h nghĩa là CẮT LỖ thực tế (không chờ hồi),
  cộng phí/slippage 2 chân → tổn thất tại mốc đó "đau" hơn con số ret thuần. Phạt 1.5× khiến model
  tránh coin dễ tụt sâu trong 4h, đúng tinh thần stop-loss cứng. Ranking nhạy với TỈ LỆ thưởng/phạt
  hơn giá trị tuyệt đối → cố định cấu trúc (x=n, y=1.5), quét n.
- Nhánh MISS dương (`0 <= ret4h < n%`): giữ nguyên `ret4h` (thưởng nhẹ vì vẫn về xanh/hòa), không
  phạt — phân biệt "đóng cứng có lời nhỏ" với "đóng cứng lỗ".

## 3. Dữ liệu — tái dùng 100% pipeline selector (KHÔNG cần export Java mới)

Label tính trực tiếp từ dataset SẴN CÓ; bằng chứng cột (`ExportFundingLabel.java`, header
`tEpochMs,tDate,symbol,{maxFav_H,maxAdv_H,tHitFav_H,tHitAdv_H,retEnd_H,nBars_H}` cho H∈{4h,12h,24h,72h}):

- `maxFav_4h = max(high(τ)/close(t) − 1)` trên τ∈(t,t+4h] — biên thuận lợi cực đại (phân số).
- `retEnd_4h = close(t+4h)/close(t) − 1` — return close-to-close cuối cửa sổ (phân số).
- `nBars_4h` = số nến 15m thực có trong (t,t+4h]; đủ = 16.

**Feature** giống hệt selector: `ff_*.bin` (40 feat f0..f39, record 170B: ts>i8, sym>i2, 40×f4) +
`oi_percoin_full.bin` (5 feat OI, record 30B) merge_asof backward theo `symId` tol 2h.

Dataset Kaggle (đúng như `kaggle_wfo` + `kaggle_dca_hard` đã dùng):
- `chuyendinh/funding-tool1-features` → `ff_*.bin`
- `chuyendinh/funding-oi-percoin` → `oi_percoin_full.bin`
- `chuyendinh/funding-label-full` → `funding_label.csv` + `symbol_map.csv`

> ⚠️ **Lưu ý semantics** (đã ghi nhận, chấp nhận như task 157): `maxFav_4h` dùng giá **HIGH**
> trong nến, không phải **CLOSE**. Chủ nhân mô tả "max close". HIGH ≥ CLOSE nên HIT hơi rộng hơn
> định nghĩa close thuần — nhưng đây chính là proxy master đã duyệt ở task 157 và HIGH sát với
> "giá đã chạm mốc TP intrabar" hơn (thực tế arm SL/chốt khi chạm). Nếu muốn ĐÚNG close-to-max-close
> phải diff Java exporter thêm cột `maxFavClose_H` — hiện KHÔNG làm (đắt, không cần cho vòng thử này).

## 4. Cách chạy

Mỗi n là 1 kernel độc lập (self-contained), thư mục `orchestrator/kernels_sl4h/sl4h-train-n{6,9,15}/`:
- `run_train.py` — script chính (đọc data → build score → walk-forward → in kết quả).
- `kernel-metadata.json` — id `chuyendinh/sl4h-train-nX`, `enable_internet: true`, 3 dataset_sources trên.

Master (KHÔNG SSH/push từ đây) chạy: `kaggle kernels push -p orchestrator/kernels_sl4h/sl4h-train-n6`
(tương tự n9, n15). Kaggle tự giải nén `.gz→.bin`; script glob đệ quy `/kaggle/input/**/...`.

Biến môi trường (đều có default, không cần set): `N_PCT` (mặc định theo folder), `PEN=1.5`,
`OOS_MONTHS=3`, `FIRST_OOS=202301`, `LAST=202606`, `SEED=42`, `SMOKE=1` (chỉ 1 fold — kiểm luồng nhanh).

## 5. Walk-forward + cách đo (leak-free)

- **Folds**: expanding, OOS_k = [cutoff_k, cutoff_k+3m), trượt 3m KHÔNG chồng lấn (giống TASK-108).
  Train = toàn bộ ts < cutoff − purge; **purge = 4h** (16 bước 15m) giữa train và OOS → chống rò nhãn.
- **LIFT@32 / LIFT@64**: mỗi mốc ts, xếp coin theo `pred`, lấy top-32 / top-64; `LIFT = %HIT(top-k) / base_rate`.
  Chỉ tính các ts có ≥ k coin. Kèm `LIFTk_vs_rand` = %HIT(top-k) / %HIT(random k coin cùng ts, 10 lần seed 42).
- **IC** = Spearman(`pred`, `score`) trên toàn bộ dòng OOS mỗi fold.
- Tổng hợp: median/min/max/std của LIFT32, LIFT64, IC qua các fold; `%fold LIFT32>1`, `%fold IC>0`.

## 6. Cách đọc kết quả

- File JSON: `/kaggle/working/sl4h_n{N}_results.json` (per-fold + summary).
- Dòng grep cuối log: `SL4H_RESULT {json...}` chứa `n_pct, pen, n_fold, LIFT32_med, LIFT64_med,
  IC_med, base_rate_med, pct_fold_LIFT32_gt1, pct_fold_IC_gt0`. Grep: `grep SL4H_RESULT`.
- **Đọc edge**: LIFT32_med > 1 (lý tưởng ≥ 1.5) + IC_med > 0 + `%fold IC>0` cao (≥ 0.7) ⇒ selector
  có tín hiệu ổn định cho label sl4h(n) đó. So 3 n để chọn target % cân bằng base_rate vs LIFT.
- So `hit_top32` với `hit_rand32` (per-fold) để thấy model hơn random bao nhiêu điểm % tuyệt đối.

## 7. Naming — tránh đụng CDC n=3

| Hạng mục | sl4h (n=6/9/15, tài liệu này) | CDC n=3 / task 157 (KHÔNG đụng) |
|---|---|---|
| Thư mục kernel | `orchestrator/kernels_sl4h/sl4h-train-nX/` | `ml/funding_selector/kaggle_dca_hard/` |
| Kernel id | `chuyendinh/sl4h-train-nX` | `chuyendinh/dca-hard-label-157` |
| Script | `run_train.py` | `train.py` |
| Output | `sl4h_nX_results.json` | `task157_result.json` |
| Dòng log | `SL4H_RESULT {...}` | `VERDICT_PRE_REGISTER {...}` |
| Dataset | dùng CHUNG 3 dataset selector (chỉ đọc) | dùng CHUNG 3 dataset selector (chỉ đọc) |


---

## 8. VÒNG 1 — kết quả (1-regression reward-penalty): FAIL

4 kernel `sl4h-train-n{3,6,9,15}` chạy xong trên Kaggle. Model đơn XGBRegressor học `score`
(HIT→n ; MISS→1.5×ret nếu âm, ret nếu dương). Đo LIFT@k theo pred-rank + IC(pred,score).

| n | LIFT@32 (median) | IC (median) | Nhận xét |
|---|---|---|---|
| 3  | ~0.67 | dương rất nhẹ | LIFT < 1: top-k theo pred HIT **kém** random |
| 6  | ~0.8x | dương nhẹ | " |
| 9  | ~0.9x | dương nhẹ hơn | " |
| 15 | ~0.96 | dương, cao nhất trong 4 n | vẫn < 1 |

- **LIFT@32 median 0.67–0.96 < 1 ở MỌI n** → selector chọn top-k coin theo pred lại HIT ÍT hơn
  random. IC dương nhẹ và **tăng theo n** nhưng không đủ để ranking có edge dương.
- **Chẩn đoán**: regression đơn học tốt VẾ PHẠT (điểm âm → tránh coin dễ tụt) nhưng MÙ VẾ THƯỞNG
  (không phân biệt coin sắp pump đạt target). Vì phần lớn phương sai của `score` nằm ở nhánh MISS
  (ret liên tục, đa số quanh 0) còn nhánh HIT bị nén về hằng số `n` → model tối ưu RMSE bằng cách
  dự phần âm cho chuẩn, bỏ mặc xác suất chạm target. Ranking theo pred ⇒ ưu tiên "ít âm" chứ không
  phải "dễ pump".
- **CDC độc lập (task-157, n=3)** cùng kết luận, và đo selector cũ dưới **kế toán SL-cứng-4h**:
  PnL/kèo **−1.30%** — **thua cả random −1.22%**. Tức selector cũ không những vô dụng mà còn phản tác dụng.

## 9. VÒNG 2 — thiết kế EV 2-model (`sl4h-ev2-n6`)

Tách bạch vế thưởng và vế phạt thành 2 model, ghép lại bằng **Expected Value** rồi rank theo EV.

- **Model A (classifier)** — `XGBClassifier` dự `P(HIT)`, HIT = `maxFav_4h ≥ n/100` (nBars_4h≥16).
  Đây chính là **vế thưởng** bị vòng 1 bỏ quên: xác suất coin chạm target.
- **Model B (regressor)** — `XGBRegressor` dự `E(ret4h%)` **CHỈ train trên tập MISS**. Đây là **vế phạt**:
  khi không chạm target thì đóng cứng lời/lỗ bao nhiêu. Train riêng trên MISS để B khỏi bị nhiễu bởi
  các mẫu HIT (vốn đã tách sang A).
- **EV mỗi mẫu OOS** = `p·n + (1−p)·1.5·ret4h_pred%`. `ret4h_pred` đơn vị %, âm/dương tự do,
  **không cap** trừ outlier > 3σ thì clip (chống pred B nổ). Rank coin theo EV.
- **Kế toán SL-cứng (số quyết định)**: mỗi kèo HIT → **+n%**; MISS → **ret4h thực %**. PnL/kèo =
  mean trên top-k, so random cùng k (10 lần). Đây là P&L "as-traded" dưới luật đóng cứng 4h.
- **Threshold-gating**: thay vì top-k, chọn mọi mẫu có `p ≥ P*` (P* ∈ {0.3..0.7}) — ít kèo nhưng
  chắc. In n_kèo/quý + PnL/kèo + %HIT mỗi ngưỡng; chọn `best_threshold` = P* có PnL/kèo cao nhất
  trong nhóm còn ≥30 kèo/quý.
- **AUC classifier** (sanity vế thưởng): kỳ vọng > 0.55 thì vế thưởng CÓ tín hiệu học được.
- **Bonus 12h**: nếu `funding_label.csv` có `maxFav_12h/retEnd_12h` (hoặc `_24h`) → lặp toàn bộ eval
  cho horizon SL-cứng-12h cùng kernel (target n=6). Không có → in `NO_12H`.

### Tiêu chí PASS (pre-register)

Vòng 2 coi là **có edge** nếu THỎA một trong hai:
1. **PnL/kèo top-32 (median qua fold) > 0 VÀ > random rõ rệt**, hoặc
2. Tồn tại ngưỡng P* cho **PnL/kèo dương với ≥ 30 kèo/quý** (`best_threshold.pnl_per_trade_med > 0`
   và `n_trades_per_fold_med ≥ 30`).

Kèm sanity: `AUC ≥ 0.55` và `LIFT@32 (EV-rank) ≥ 1`. Nếu cả hai tiêu chí PnL đều âm → kết luận
label SL-cứng-4h không có edge dưới feature hiện tại, dừng nhánh này.

- Kernel: `orchestrator/kernels_sl4h/sl4h-ev2-n6/` — id `chuyendinh/sl4h-ev2-n6`, 3 dataset dùng chung,
  `enable_internet: true`. Output: `SL4H_EV2_RESULT {...}` + `sl4h_ev2_n6_results.json`.


---

## 10. VÒNG 3 — EXIT-LAB: "nuôi lệnh đã chạm lãi vs TP cứng" (`exit-lab-4h`)

EV2 (mục 9) đã PASS: `clfP(HIT6%,4h)` AUC **0.743**, gate `P>=0.7` → **+1.74%/kèo** dưới kế toán
**SL-cứng-4h** (HIT→+6% ; MISS→retEnd_4h). Câu hỏi kế: nếu thay luật chốt TP cứng bằng **NUÔI**
(giữ tiếp lệnh nào đã chạm lãi, chỉ cắt cứng 4h lệnh không chạm) thì PnL/kèo có vượt +1.74 không?

### Thiết kế (tái dùng 100% pipeline sl4h-ev2-n6)

Load (ff+OI+label), folds walk-forward expanding, purge=4h, XGB params — **y hệt EV2**. Đầu script
`detect_columns()` in `EXITLAB_COLUMNS [...]`; kỳ vọng có `maxFav_4h/retEnd_4h/nBars_4h + _12h`,
kiểm `_24h/_72h` — thiếu cột nào thì **degrade** (bỏ variant phụ thuộc) và in `EXITLAB_NO_<col>`.

**Model train 1 lần/fold, dùng chung** (đóng hồ sơ vòng-1: in AUC cả 3 ngưỡng):
- `clfP3 = P(maxFav_4h ≥ 3%)`, `clfP6 = P(≥6%)`, `clfP9 = P(≥9%)` — classifier XGB.
- `regLoss = E(retEnd_4h | maxFav_4h < 3%)` — regressor train **chỉ trên tập MISS-3%** (vế phạt).

**5 EXIT VARIANTS** (vector hoá thẳng từ cột label, KHÔNG cần model thêm):

| Variant | PnL/kèo (%) | Ý nghĩa |
|---|---|---|
| E1 | `retEnd_4h*100` | đóng cứng 4h — baseline |
| E2 | `where(hit6, +6, retEnd_4h*100)` | TP cứng +6% — **chính là EV2** |
| E3 | `where(hit3, retEnd_12h*100, retEnd_4h*100)` | nuôi thô 12h |
| E4 | `where(hit3, max(1.0, retEnd_12h*100), retEnd_4h*100)` | nuôi có **sàn +1%** (proxy trailing arm SL) |
| E5 | `where(hit3, retEnd_24h*100, retEnd_4h*100)` | nuôi 24h (nếu cột `_24h` có) |

`hit3 = maxFav_4h≥0.03 & nBars_4h≥16` ; `hit6` tương tự 0.06. Row "nuôi" thiếu đủ cửa sổ
(`nBars_12h<48` / `nBars_24h<96` hoặc NaN) → fallback đóng cứng 4h (không mất kèo, không bịa lãi).

### Gating grid + đo (OOS mỗi fold)

- Gate `G3 = clfP3.p`, `G6 = clfP6.p` với `P* ∈ {0.5,0.6,0.7,0.8}` ; `GEV = p6·6 + (1−p6)·1.5·regLoss·100`
  ngưỡng `GEV > 0`. Với **mỗi (variant × gate × P*)**: `n_kèo/fold`, `PnL/kèo mean`, `hit3_rate`,
  **PnL fold TỆ NHẤT** (tail = min qua fold), so **random cùng n** (5 lần, cùng variant → công bằng).
- Tổng hợp median qua fold. `best` = combo có `n_med ≥ 30` và `pnl_med` cao nhất, kèm `worst_fold_pnl`.

### PLACEBO (chống overfit label)

1 lần chạy: **shuffle** target `hit6` trong TRAIN mỗi fold → fit lại `clfP6` → gate `p≥0.7` →
PnL/kèo (E1) **phải ≈ random**. In `PLACEBO_RESULT {pnl, random}`. Nếu placebo pnl ≫ random ⇒
tín hiệu gate là ảo (rò/overfit) → nghi ngờ toàn bộ kết quả.

### Giả thuyết & tiêu chí PASS (pre-register)

- **Giả thuyết**: `E4 ≥ E3 > E1` (nuôi có sàn ≥ nuôi thô > đóng cứng thô) — cắt đuôi âm khi
  nuôi bằng sàn +1% giữ được phần lớn upside 12h mà chặn kèo tụt ngược.
- **Tiêu chí "nuôi-lãi thắng TP-cứng"**: tồn tại (variant nuôi × gate × P*) với `n_med ≥ 30` và
  `PnL/kèo_med > +1.74` (mốc E2/EV2). Kèm sanity: AUC (p6) ≈ 0.74 giữ nguyên và PLACEBO ≈ random.
- Nếu mọi variant nuôi đều ≤ +1.74 ⇒ TP-cứng-4h (E2) là luật exit tốt nhất dưới feature hiện tại,
  dừng nhánh nuôi.

### Output & cách chạy

- Kernel `orchestrator/kernels_sl4h/exit-lab-4h/` — id `chuyendinh/exit-lab-4h`, `enable_internet:true`,
  3 dataset dùng chung (`funding-tool1-features`, `funding-oi-percoin`, `funding-label-full`).
- Bảng per-variant in thường + dòng cuối `EXITLAB_RESULT {json}` (`columns_found`, `auc:{p3,p6,p9}`,
  `best{variant,gate,pstar,pnl_per_trade_med,n_trades_per_fold_med,hit_rate,worst_fold_pnl}`,
  `table[]` chỉ giữ ô `n_med≥30`, `placebo{pnl,random}`; JSON giữ <2KB, lược ô xấu). File đầy đủ:
  `/kaggle/working/exit_lab_4h_results.json`. Grep: `grep EXITLAB_RESULT` / `grep PLACEBO_RESULT`.


---

## Vòng 3b — 4 phép đo SONG SONG (mở xẻ edge EV2 trước khi lên size)

Chạy 4 kernel độc lập (mỗi cái tự chứa, cùng 3 dataset, `enable_internet:true`). Mỗi kernel in
1 dòng `<TÊN>_RESULT {json <2KB}` để grep. Tiêu chí đọc pre-register ghi ngay dưới từng mục.

### 1. `exit-lab-12h` — dời CỬA SỔ QUYẾT ĐỊNH sang 12h

Như `exit-lab-4h` nhưng quyết định trên cửa sổ 12h: `hit3/hit6` đo trên `maxFav_12h`
(`nBars_12h≥48`), cắt cứng tại 12h (`retEnd_12h`), nuôi tới 24h nếu có cột (`E3` nuôi thô,
`E4` nuôi sàn +1% — dùng `retEnd_24h`; thiếu `_24h` ⇒ chỉ `E1/E2`). `clfP3/P6` train target 12h,
`regLoss=E(retEnd_12h|miss3)`. Gate `G3/G6` (P* ∈ {0.5..0.8}) + `GEV>0`, placebo shuffle `hit6`.
- **Đọc**: so `pnl/keo_med` cửa sổ 12h vs mốc EV2/4h `+1.74`. Nếu mọi combo `n_med≥30` đều ≤ +1.74
  ⇒ chu kỳ quyết định chậm (12h) KHÔNG hơn 4h, giữ 4h. Sanity: AUC(p6) và PLACEBO≈random.
- **Output**: `EXITLAB12H_RESULT {window, auc, best{...}, table[], placebo}`.

### 2. `ev2-n9-cal` — N=9 + CALIBRATION xác suất

`sl4h-ev2` với `N_PCT=9`. Sau khi fit clf trên train-core (80% đầu theo ts), fit
`IsotonicRegression` trên train-tail (20% cuối, out-of-fit → không rò rỉ) ánh xạ `p_raw→hit`.
So gating theo `p-raw` vs `p-calibrated`, P* ∈ {0.5,0.6,0.7,0.8}; in cả 2 bảng.
- **Đọc**: N=9 khó hơn (base_rate thấp) → `p_raw` dễ over-confident, ngưỡng P* thô lệch.
  Nếu `best_cal` cho `pnl/keo` cao hơn hoặc `n_trades` ổn định hơn ở cùng P* ⇒ calibrate đáng dùng
  khi đẩy target lên. Nếu 2 bảng ~ nhau ⇒ ranking p đã đủ, không cần calibrate.
- **Output**: `EV2N9CAL_RESULT {n_pct, auc, best_raw{...}, best_cal{...}}`.

### 3. `dual-gate-sizing` — gate KÉP + phân bổ vốn theo EV

n=6, 4h. Gate kép: `p6≥P*` **AND** `regLoss_pred%≥L*` (L* ∈ {−1,−2,−3, không-lọc}) — grid P*×L*:
`n_kèo`, `PnL/kèo`, `hit6`, `worst-fold`. Sizing (trên tập `p6≥0.7`): `size=clip(EV,0.5..2.0)`
chuẩn hoá mean=1 trong fold → so equal-size; báo **tổng PnL/quý** cả 2 (median qua fold).
- **Đọc**: (a) thêm chặn `regLoss` có cắt kèo xấu nâng `PnL/kèo` mà `n_med` vẫn ≥30 không? Best
  gate kép vs EV2 `+1.74`. (b) EV-weighted `ev_total` > `equal_total` ⇒ size theo EV có giá trị;
  nếu ≤ ⇒ equal-size đủ tốt, khỏi phức tạp hoá.
- **Output**: `DUALGATE_RESULT {auc, best_gate{...}, sizing{equal_total_med, ev_weighted_total_med,...}, table[]}`.

### 4. `edge-anatomy` — mổ xẻ edge theo thời gian & feature

n=6, 4h, gate `p6≥0.7` cố định. In đủ 14 dòng per-fold (quý): `PnL/kèo`, `n_kèo`, `hit6`, `AUC`;
gom regime thô `2023H1 / 2023H2 / 2024 / 2025 / 2026` → trung bình nhóm; XGB
`feature_importances_` top-15 (map index `f0..f39` + 5 OI) trung bình qua fold; đếm fold ÂM.
- **Đọc**: `folds_neg` + `worst_fold` cho biết median `+1.74` có che regime nào lỗ; nếu edge dồn
  vào 1-2 regime bull ⇒ nghi phụ thuộc chế độ thị trường. Top-features cho biết OI hay feature f*
  dẫn dắt (định hướng cắt/giữ feature vòng sau).
- **Output**: `ANATOMY_RESULT {folds_neg, worst_fold{label,pnl}, regime_summary, top_features[15]}`.

> Tổng: 4 phép đo trả lời độc lập 4 câu — cửa sổ quyết định (12h?), calibration (đáng khi N cao?),
> gate-kép+sizing (cắt đuôi & phân bổ vốn?), độ bền edge (regime & feature). Đọc xong mới quyết
> nhánh nào lên production sizing; bất kỳ dấu hiệu edge dồn 1 regime hoặc placebo ≫ random ⇒ dừng.


---

## 11. VÒNG 3 + 3b — KẾT QUẢ (đọc tay 2026-07-17; 2 watcher runner chết, đã pipe_stop)

### exit-lab-4h — NUÔI-CÓ-SÀN THẮNG TP CỨNG (proxy)
AUC p3/p6/p9 = 0.694/0.743/0.786. Best: **E4×G6 P*=0.7 → +8.82%/kèo, 78 kèo/quý, hit3 87%,
worst-fold +4.34 (không fold âm)**. Thứ tự đúng giả thuyết: E4 (+8.82) > E3 (+3.11) > E1 (+2.12),
mốc E2/EV2 = +1.74. ⚠️ PLACEBO_RESULT = null (không chạy được) — sanity chính CHƯA có.

### exit-lab-12h — cửa sổ 12h tương đương/hơn, tần suất ×15
Best: E4×G6 P*=0.8 → +9.30%/kèo, 142 kèo/quý, worst +3.17; P*=0.7 → +8.58%/kèo, **1152 kèo/quý**,
worst +2.25. AUC p6(12h)=0.690. ⚠️ Placebo cũng null.

### ev2-n9-cal — n=9 KÉM n=6; calibration không giúp
AUC 0.783 nhưng best_raw P*=0.6 chỉ +1.19%/kèo (n=72.5, hit 50%); best_cal +0.88 < raw.
→ CHỐT n=6, bỏ isotonic.

### dual-gate-sizing — gate kép KHÔNG đáng
Best kép P*=0.6 & L*=-3: +2.07%/kèo nhưng n giảm 78→43.5 và worst-fold TỆ hơn (-2.00 vs -0.32
của single P*=0.7). Sizing: ev_weighted_total 111.2 vs equal 42.7/quý — NHƯNG per_trade_med 2 cột
trùng nhau 1.7428 → nghi bug tính, verify code trước khi tin.

### edge-anatomy — CỜ ĐỎ LỚN NHẤT: edge decay theo thời gian
14 fold, chỉ 1 fold âm (2026-01, -0.32) NHƯNG PnL/kèo theo regime: 2023H1 +5.31 (5.5 kèo/fold),
2023H2 +2.01 (19), 2024 +2.87 (58), 2025 +0.71 (566), **2026 -0.14 (856)**. n kèo tăng ngược chiều
edge → median-fold +1.74 bị chi phối bởi fold ít kèo; **trade-weighted ≈ +0.51%/kèo, sau phí 0.2%
còn ~+0.3%**. Feature tập trung: f36 = 0.403 + f10 = 0.162 (57% importance ở 2 feature).
⚠️ 2026: hit6_mean 0.741 mà pnl_mean -0.14 → mâu thuẫn nội bộ, cần mổ per-fold trước khi tin số 2026.

### KẾT LUẬN VÒNG 3/3b
1. Exit "nuôi có sàn +1%" (E4) >> TP cứng — đúng hướng; 12h giải TOO_FEW_TRADES.
2. E4 là PROXY floor lạc quan (max(1.0, retEnd_12h) cho mọi kèo hit3 — trailing thật không ăn
   trọn retEnd): +8.8/+9.3 KHÔNG phải as-traded → phải xác nhận bằng sim Java 3-state + WFO (mục 1+3).
3. Việc phải làm trước khi tin edge: (a) fix + chạy lại placebo; (b) mổ per-fold 2025-2026;
   (c) tra nghĩa f36/f10.


### 11b. Mổ per-fold + nghĩa feature (đo 2026-07-17, log edge-anatomy)

Per-fold (gate p6≥0.7, kế toán EV2): median 14 fold = ĐÚNG +1.74 (khớp EV2 — cùng kế toán).
2025: +2.21 (n=512), +0.12 (195), +0.58 (620), +0.84 (3100); 2026: **−0.32 (845), +0.04 (867)**.
→ 2026 flat/âm là THẬT (không phải lỗi đo). **Trade-weighted toàn kỳ = +0.72%/kèo** (Σn·pnl/Σn
= 4648/6435), sau phí 0.2% còn ~+0.5% — thấp hơn nhiều median +1.74 vì fold ít-kèo (2023) kéo median.
Chú ý: hit6 2026 vẫn 72-76% nhưng PnL ≈ 0 → suy ra miss trung bình 2026 rất sâu (~−17%/miss theo
kế toán hit→+6): coin gate chọn 2026 là pump-candidate nhưng khi trượt thì trượt nặng. Cần feature/
gate chặn đuôi miss (regLoss, mục dual-gate) hoặc chấp nhận sizing nhỏ regime này.

Feature mapping (FundingMarketFeatures.java, # = 0-based = f index):
- **f36 = ret15m** (return 15 phút gần, microstructure TASK-038) — importance 0.403
- **f10 = rsi1H** — importance 0.162
→ 57% edge từ momentum-ngắn + RSI: model bắt pump ĐANG diễn ra. Rủi ro: (a) decay khi cấu trúc
thị trường đổi (đúng pattern 2026?); (b) nhạy slippage/latency — vào lệnh khi coin đã chạy 15';
sim Java phải mô phỏng entry trễ 1 nến để khỏi lạc quan.
