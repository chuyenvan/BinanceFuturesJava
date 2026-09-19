# GATE vs SELECTOR — Khảo sát & Hướng mới
*Ngày khảo sát: 2026-09-20. Chỉ đọc; không sửa code, không commit, không chạy sim.*

---

## 1. Gate hiện tại: Train trên TARGET gì? Script nào? Fold/cửa sổ?

### Script trainer
- **Trainer tái dựng**: `research/pipeline/g015_net_train.py` (bản gốc `gen_funding_wf_predictions_1m.py` đã mất — xem comment đầu file :1-17)
- Bản gốc g72 (maxFav variant): `research/pipeline/g72_train.py`

### Label / TARGET chính xác
```
y = (retEnd_4h > NET_THR)  với  NET_THR = 0.015
```
Nghĩa là: tại mỗi tick 15m, với mỗi coin, nhãn = **1 nếu return ròng tại END của 4h horizon > 1.5%, else 0**.
- Nguồn: `research/pipeline/g015_net_train.py` dòng 5, hàm `load_labels()` dòng 138-168, cụ thể `yv = (v[keep] > thr)` với `col = "retEnd_4h"`.
- Base rate 4h ≈ 0.185 (g015_net_train.py docstring dòng 7).
- Cột `retEnd_4h` đọc từ protobuf label files `/home/ubuntu/label_15m/funding_label_*.pb`.

### Features (45 cột)
`g015_net_train.py:NF=45` = 40 cột Tool1 (per-coin 15m candle features) + 5 OI: `oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy` (dòng 54).

### Model
`XGBClassifier`, n_estimators=400, max_depth=5, lr=0.05, subsample/colsample=0.8, min_child_weight=20. (`g015_net_train.py` dòng 265-268)

### WFO / Cửa sổ
- **18 cutoffs**: 20220101..20260401 (CUT_DATES, dòng 57-60)
- OOS = 3 tháng kế tiếp mỗi cutoff
- PURGE = 288 steps × 15m = 72h (khớp horizon nhãn 4h, có biên an toàn)
- Điều kiện bỏ fold: `len(train) < 5000` hoặc OOS rỗng
- Pool training: **TẤT CẢ coin × TẤT CẢ 15m ticks** trong khoảng training (không chỉ top-K của S1)

### Output bins
`predwf_G015x26/predict_wf_<YYYYMMDD>.bin` — 10 file, cấu trúc `(ts, symId, p0, p1, p2, p3)` với `p0 = P(retEnd_4h > 1.5%)`. (`g72_train.py` dòng 157-166, struct pack `">qh4f"`)

---

## 2. Selector S1 train trên label gì? Công thức g1lite?

### Script
`research/pipeline/s1_rank.py`

### Label / TARGET chính xác
```
rel     = g1lite - median_tick(g1lite)          # lệch so với trung vị trong tick
rel5    = min(int(rank_pct(rel) * 5), 4)        # ngũ phân vị CROSS-SECTIONAL trong tick (0..4)
```
Nghĩa là: label KHÔNG phải giá trị tuyệt đối — là **thứ hạng tương đối** của coin trong tick đó.
- Nguồn: `research/pipeline/README.md` bảng hyperparameter dòng 101.

### Công thức g1lite
```python
g1lite = if maxFav_72h >= 0.05:
             maxFav_72h - min(0.5 * maxFav_72h, 0.08)   # trailing stop xấp xỉ
         else:
             retEnd_72h
```
- Nguồn: `research/pipeline/ledger.py` dòng 40; `research/pipeline/README.md` dòng 67.
- Horizon: **72h** (khác gate: 4h).
- Giải nghĩa: nếu coin chạy tốt (max favourable >= 5%), g1lite ≈ peak gain sau khi trừ trailing stop ước tính; nếu không, dùng return ở END 72h.

### Features S1 (9 cột từ feat_v2)
`vol_7d, dd_7d, rk_dd_7d, hrs_since_high_7d, ret_3d, rk_ret_3d, ret_14d, ls_global, rk_oi_delta24h`
(`README.md` bảng hyperparameter dòng 107)

### Model
`XGBRanker(objective='rank:ndcg', lambdarank_pair_method='topk', lambdarank_num_pair_per_sample=8)`.

### WFO / Cửa sổ
10 folds, cutoffs 20220101..20240401, OOS=3 tháng, PURGE=72h. (`README.md` dòng 103)

---

## 3. Hai cái KHÁC NHAU ở đâu?

| Chiều | Gate G015 | Selector S1 |
|---|---|---|
| **Label** | `retEnd_4h > 0.015` (binary absolute) | `rel5` = ngũ phân vị của `g1lite` (cross-sectional relative) |
| **Horizon** | **4h** | **72h** |
| **Framing** | Tuyệt đối (coin này có lời > 1.5% không?) | Tương đối (coin này rank cao trong tick không?) |
| **Population train** | **Toàn pool** (mọi coin × mọi tick) | Pool đã filter (tick gate mở, label notna) |
| **Mô hình** | XGBClassifier (phân loại P(win)) | XGBRanker (rank:ndcg) |
| **Feature set** | 45 cột (40 Tool1 + 5 OI) | 9 cột từ feat_v2 (hourly) |
| **Scale output** | P(retEnd_4h>1.5%) per coin | Score thô → map lại thành phân phối G015 qua build_map.py |

**Điểm khác mấu chốt** (nhận xét của owner):

1. **Gate nhãn 4h, selector tối ưu 72h**: Gate học "coin nào lời > 1.5% trong 4h?" nhưng S1 chọn "coin nào rank cao theo 72h g1lite?". Hai mục tiêu không khớp horizon.

2. **Gate train trên full pool, S1 chỉ hành động trên top-K**: Gate không biết mình chỉ bảo vệ top-K của S1. Nó học tín hiệu từ toàn bộ pool, không phải từ tập giao dịch thực.

3. **Gate P(win) thuần túy; S1 dùng tín hiệu tương đối**: Cùng một giá trị P(win) của gate có thể tương ứng với coin rank cao hoặc thấp trong tick. Sau khi build_map.py remap, P trở thành proxy cho rank S1 — nhưng calibration của P gốc (net015) không liên quan gì đến 72h g1lite.

---

## 4. predReturn15M / net015 / netEnd — định nghĩa & khác nhau

| Tên | Định nghĩa | Script sinh ra | Khác nhau |
|---|---|---|---|
| `netEnd` | `retEnd_Nh` = return ròng tại END của N-hour horizon (float liên tục) | protobuf label `funding_label*.pb`, đọc qua `ml/lib/funding_label_pb.py` (dòng 96-117) | Continuous |
| `net015` | Binary label `retEnd_4h > 0.015` | `g015_net_train.py` dòng 161: `yv = (v[keep] > thr)` | Binary, gated trên horizon 4h |
| `predReturn15M` | Output của **market-level regression model** (33 features V3FULL: momentum, volatility, market breadth, funding rates, time) dự báo return 15m của **thị trường** (không phải per-coin) | ONNX model `/home/ubuntu/claudedata/wfo_models/fold_N/Model_Regressor_Return15M.onnx`; script: `research/pipeline/h1/h1_p15_repro.py` dòng 28-37; ghi ra `claudedata/wfo_gate_pred.csv` | Market-level, ONNX regressor, 33 features |

**Sự khác biệt quan trọng**: `predReturn15M` ≠ net015. `predReturn15M` là **market gate signal** (thị trường nói chung có tích cực 15m không?), trong khi `net015` là nhãn training của G015 gate per-coin (coin cụ thể có net return > 1.5% sau 4h không?).

### Gate được dùng lúc vào lệnh thế nào?

```
symbolPred  = 1 - p_g015     (= score = THẤP là tốt, sau khi build_map.py remap theo rank S1)
dyn_thr     = MIN_MOMENTUM_15M * max(DYN_MIN, (symbolPred / SCORE_BASE) * DYN_MULT) * GATE_DYN_SCALE
PASS  <=>  !(predReturn15M < dyn_thr)
```

- `DYN_MIN = 0.26787f`, `SCORE_BASE = 0.15f`, `DYN_MULT = 1.28760f` — hằng số trong `EntryGate.java` (dòng 44-48)
- `GATE_DYN_SCALE` = nhân thêm vào toàn bộ dynamic threshold (key `SIM_GATE_DYN_SCALE`, default 1.0f) — `EntryGate.java` dòng 58
- `GATE_REGIME_ADAPTIVE = false` (default OFF; khi ON: scale thay đổi theo regime BTC 30d) — dòng 61
- **Nghĩa**: coin có symbolPred THẤP (rank S1 cao) → threshold thấp → thị trường chỉ cần tích cực vừa phải. Coin xấu → threshold cao → chỉ vào khi thị trường rất mạnh.

---

## 5. 4-6 Hướng có thể thử

### Hướng A — "Gate trên top-K của S1" (ý tưởng chính của owner)
**Giả thuyết**: Nếu gate được train trực tiếp trên kết quả thực của tập trade S1 chọn (thay vì full pool), nó sẽ học "tick nào điều kiện market tốt cho NHỮNG TRADE CỤ THỂ đó" thay vì "tick nào tốt cho bất kỳ coin nào".

**Label chính xác**:
```
Tại mỗi tick t (OOS của fold gate):
  top_K_coins = top-K theo score S1 tại tick t (từ pred_s1a2.parquet OOS của fold đó)
  gate_label  = mean(retEnd_4h hoặc retEnd_72h của top_K_coins) > threshold   (hoặc regression)
```
Cần dùng S1 OOS predictions (không dùng S1 train) → không leak.

**Đánh giá**: Pre-reg → train 1 fold OOS → Spearman(gate_pred, mean_top_K_outcome) vs baseline → nếu IC > 0.05 → sim WFO.

**Chi phí**: Cần build lại pipeline 3 bước (1) lấy S1 OOS preds per fold; (2) tính mean outcome top-K; (3) train gate classifier/regressor mới trên label đó. Không cần sim ngay cho probe.

**Rủi ro**: 
- Số tick làm nhãn = số tick gate mở (~8,686 ticks / 48 tháng = ~180 ticks/tháng), ít hơn full pool → model sẽ ít dữ liệu hơn.
- Selection bias: label phụ thuộc vào chất lượng S1, nếu S1 thay đổi gate cần retrain lại.
- Cần cẩn thận purge giữa S1 train và gate train.

**Dữ liệu cần**: `pred_s1a2.parquet` (có sẵn) + `label_15m/*.pb` (có sẵn).

---

### Hướng B — Đổi horizon gate từ 4h → 72h (căn chỉnh với S1)
**Giả thuyết**: Gate và selector cùng horizon 72h → tín hiệu học được nhất quán hơn; gate có thể phân biệt "tick tốt cho 72h" thay vì "tick tốt cho 4h".

**Label chính xác**:
```
y = (retEnd_72h > 0.015)   hoặc y = (maxFav_72h >= 0.05)   trên full pool
```
Variant `net015_72h` đã được chạy probe: `research/analysis/g5_out/g5_summary_net015_72h.json` (base_rate=0.393, 16 folds, không sinh bins — chỉ summary). Chưa có IC/lift so sánh với gate gốc.

**Đánh giá**: So sánh IC(pred_72h, realized_72h) vs IC(pred_4h, realized_4h) trên cùng pool OOS; sau đó sim WFO nếu IC cải thiện.

**Chi phí**: **Thấp nhất** — chỉ đổi `--label-mode net --thr 0.015` + thêm `--label-h 72` vào `g015_net_train.py`, train lại trên CPU/GPU ~30 phút. Build bins + sim.

**Rủi ro**: 
- Horizon 72h → PURGE_STEPS phải tăng lên 288 bước × 15m = 72h (đã đủ) nhưng nên xem xét tăng purge lên 288 bước nếu horizon là 72h để tránh overlap.
- Base rate ~39% (cao hơn net015_4h=18%), mô hình ít cân bằng nhãn hơn → cần điều chỉnh scale_pos_weight.

**Dữ liệu cần**: label files đã có sẵn (`retEnd_72h` trong protobuf).

---

### Hướng C — Gate label = g1lite (chính label S1 dùng, full pool)
**Giả thuyết**: Train gate trực tiếp trên g1lite (cùng target với S1 nhưng không cross-sectional) → gate học "tick nào coin sẽ có g1lite cao?". Cả gate và S1 cùng tối ưu một metric.

**Label chính xác**:
```
y = g1lite > median_tick(g1lite)  (binary cross-sectional, giống s1_rank.py nhưng cho gate)
```
Hoặc regression: `y = g1lite` liên tục.

**Đánh giá**: Rank-IC(gate_pred, g1lite) trên OOS pool; so sánh vs G015 gốc theo ledger.py `edge_table()`.

**Chi phí**: Trung bình — thêm g1lite vào label pipeline, train XGBClassifier/Regressor mới, probe IC trước khi sim.

**Rủi ro**: 
- g1lite = f(maxFav_72h) có thể có nhiều NaN trong 2021 (pool không có G015), nhưng ledger đã xử lý.
- Cross-sectional label có thể làm mô hình tập trung vào "tốt hơn bạn cùng tick" thay vì "tốt tuyệt đối" — có thể gây vấn đề khi thị trường đồng loạt xấu.

**Dữ liệu cần**: `cand_dev.parquet` đã có `g1lite` → train trực tiếp.

---

### Hướng D — Market gate `predReturn15M` retrain trên outcome thực của S1 trades
**Giả thuyết**: `predReturn15M` hiện train trên market-level features dự báo return thị trường 15m — nhưng thực ra cần dự báo "tick này có tốt để vào trade S1 không?". Nếu retrain nó với label = mean(g1lite of top-K per tick), nó sẽ học trực tiếp điều đó.

**Label chính xác**:
```
Tại mỗi tick t (có gate mở):
  top_K = top-K coins theo S1 tại tick t
  label_t = mean(g1lite of top_K)  (regression)  hoặc  label_t = mean > 0.03  (binary)
```
Giống hướng A nhưng thay thế **predReturn15M model** thay vì gate bins G015.

**Đánh giá**: IC(new_p15, label_t) vs IC(old_p15, label_t); sau đó gắn vào sim (cần sinh CSV mới thay wfo_gate_pred.csv, thay ONNX model).

**Chi phí**: Cao — phải train ONNX model (WFOGateRunner pipeline), sinh CSV mới, verify byte-identity với phần còn lại của sim.

**Rủi ro**: 
- Thay đổi `predReturn15M` là thay đổi lớn, ảnh hưởng toàn bộ sim; cần parity check kỹ.
- Số tick có label = số tick gate mở (~8k ticks) — ít dữ liệu cho regression/classification.
- 33 features V3FULL không overlap với 45 features G015 → cần cross-feature analysis.

---

### Hướng E — Thay nhãn gate bằng ranking cross-sectional (align framing với S1)
**Giả thuyết**: Cả S1 lẫn gate nếu đều học framing tương đối (cross-sectional) sẽ nhất quán hơn. Gate nên học "tick nào, trong số các coin đủ điều kiện, có điều kiện tốt để vào?".

**Label chính xác**:
```
rel_coin = retEnd_4h - median_tick(retEnd_4h)    (lệch so với trung vị tick)
y = (rel_coin > 0) hoặc quintile rank trong tick
```
Train XGBRanker giống s1_rank.py nhưng dùng features Tool1 + OI (45 cột gate) và group = tick.

**Đánh giá**: OOS rank-IC trong tick; thay vào build_map.py như S1.

**Chi phí**: Trung bình — thay đổi objective sang rank:ndcg, dữ liệu có sẵn.

**Rủi ro**: Mất calibration tuyệt đối (P(win)), không còn dùng được làm threshold scaler cho predReturn15M trực tiếp → cần thiết kế lại cách gate dùng output.

---

### Hướng F — Gộp gate + selector thành một mô hình end-to-end
**Giả thuyết**: Thay vì hai bước (G015 gate → S1 remap), train một mô hình duy nhất dự báo g1lite với toàn bộ features của cả hai (45 Tool1/OI + 9 feat_v2 = 54 cột), rank trong tick = XGBRanker.

**Label chính xác**:
```
rel5 = quintile(g1lite - median_tick(g1lite)) trong tick  [y như S1 hiện tại]
Features = union(45 cols Gate, 9 cols S1)  = 54 cols hourly + 15m features
```

**Đánh giá**: OOS rank-IC, edge5 vs current S1 baseline; sim.

**Chi phí**: Cao — feature engineering mới (merge hourly feat_v2 với 15m Tool1), train mới hoàn toàn.

**Rủi ro**: 
- Feature set lớn hơn → nguy cơ overfit cao hơn.
- Mất market-level gate (predReturn15M) → không còn tầng lọc thị trường.
- Nếu thất bại, mất nhiều thời gian compute.

---

## 6. Xếp hạng theo (giá trị kỳ vọng / chi phí / rủi ro)

| Hạng | Hướng | Giá trị | Chi phí | Rủi ro | Nên làm trước? |
|---|---|---|---|---|---|
| 1 | **B (horizon 72h)** | Trung bình | Thấp | Thấp | ✅ Làm đầu tiên — đổi 1 param, đã có probe (g5_summary_net015_72h.json), không thay kiến trúc |
| 2 | **A (top-K outcome)** | Cao | Trung bình | Trung bình | ✅ Làm thứ hai — ý chính của owner, trực tiếp fix population mismatch |
| 3 | **C (g1lite full pool)** | Trung bình | Trung bình | Thấp | Làm sau A nếu A không đủ |
| 4 | **E (cross-sectional gate)** | Trung bình | Trung bình | Trung bình | Cần thiết kế lại cách dùng output |
| 5 | **D (retrain p15 model)** | Cao | Cao | Cao | Để sau — thay đổi lớn, cần B/A xác nhận hướng trước |
| 6 | **F (gộp gate + selector)** | Cao (nếu thành) | Cao | Cao | Cuối — phá vỡ kiến trúc hai tầng |

**Đề xuất sequence**:
1. **B** → probe nhanh (không cần sim, chỉ IC/lift trên pool): xem net015_72h có IC > net015_4h không → nếu có, sinh bins và sim
2. **A** → pre-reg → lấy S1 OOS preds per fold, tính mean(top-K outcome) per tick, train gate mới, probe IC → sim nếu pass
3. Sau khi biết kết quả B + A, mới quyết định có đi C/D/E/F không

---

## 7. Cái gì CHƯA XÁC ĐỊNH được từ repo

1. **IC thực của gate G015 hiện tại vs label g1lite**: `g5_proxy.py` có chạy phân tích này (`BASE = "net015_4h"`) nhưng kết quả chỉ có trong `/home/ubuntu/g5/proxy_table.csv` trên Oracle — không có trong repo. Không biết mức baseline IC hiện tại.

2. **Số tick gate mở thực tế theo S1 OOS**: `admit_rate.py` đã đo `RESULT B5: DEV 0.51% / VAL 0.71%` nhưng chỉ với K=8, không rõ số tuyệt đối tick có đủ dữ liệu để làm label cho hướng A/D.

3. **Calibration của G015 bins sau build_map.py remap**: Sau khi S1 remap, P values trong `predwf_map_s1a2` có còn calibrated không? Nếu không, `dyn_thr` formula trong EntryGate dùng uncalibrated P → gate threshold có thể lệch. Chưa có file nào trong repo kiểm tra điều này.

4. **`g5_summary_net015_72h.json` không có sha_bin**: Bins 72h chưa được sinh → chưa có sim kết quả. Chỉ là summary train, chưa rõ IC/lift.

5. **"label_oldbasket" trong `gate_dataset_full.csv.gz`**: `score_cycle.py` dùng `label_oldbasket` làm "realized" cho gate IC — chưa rõ định nghĩa chính xác của `label_oldbasket` (có thể là basket return 15m, không phải top-K outcome). Không có định nghĩa trong repo Git (nằm trong Java `ExportGateDataset`).

---

*File này chỉ là phân tích khảo sát. Mọi thay đổi code, commit, chạy sim cần pre-reg riêng.*
