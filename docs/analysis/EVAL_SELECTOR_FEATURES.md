# EVAL_SELECTOR_FEATURES — đánh giá từng feature của selector S1 (45 cột)

**Ngày:** 2026-09-24 · **Chi nhánh:** `module` · **Trạng thái:** DESCRIPTIVE (đo, không train lại, không sim)
**Phạm vi dữ liệu:** DEV only — 3 quý `20230101_to_20230401`, `20231001_to_20240101`,
`20240401_to_20240701` (5.455.290 dòng, 26.124 tick, 167/234/270 symbol). **Không đọc 2026.**
**Nguồn trung gian (không tính lại từ đầu):** `/tmp/evfeat/{analyze,analyze2,analyze3,nanpass,varcheck}.py`
+ `joined.parquet`, `rank_ic.csv`, `decile_edge.csv`, `corr45.csv`, `clusters.json`, `pairs.json`,
`nanpass.log`, `varcheck.log`, `run{,2,3}.log`; `/tmp/feats.json`, `/tmp/imp_{gain,cover,weight,share_norm}.npy`.

Mục tiêu: (a) xác định **số feature thật**, (b) đo **importance / rank-IC / decile edge / đám trùng lặp /
độ ổn định**, (c) đối chiếu **soát rò rỉ** đã có, (d) chốt **3 nhóm NGẮT CHẮC / CÂN NHẮC / GIỮ** bằng số.
Không train, không sim, không sửa Java, không push.

---

## 0. Số feature THẬT = **45** (đúng 45, không phải 40)

| Nguồn | Bằng chứng | Kết quả |
|---|---|---|
| Java (sinh Tool1) | `src/main/java/com/binance/chuyennd/ai_ml/features/export/fundingv2/ExportFeaturesForPythonTool.java:407-427` — `convertFeaturesToArray`, comment `#1..#40` | **40** feature `f0..f39`, đúng thứ tự |
| Java (OI, tool riêng) | `.../fundingv2/ExportFundingOiPerCoin.java:104-129` (+ comment `:410` "…KHÔNG nằm trong `.t1c.gz` này") | **5** feature `#41..#45`, merge ở train theo `(ts,coin)` |
| ONNX đang LIVE | `shadow_c3/storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx` — `onnx.load`: `graph.input=[('input',[0,45])]`, `1` node, `opset ai.onnx.ml v1`, `metadata_props = {}` (RỖNG) | **45** cột vào; ONNX **không** chứa tên feature → xác nhận số, không xác nhận tên |
| Model fold (S1) | `/home/ubuntu/claudedata/predwf_G015/model_f{0..17}_4h.json` — `learner_model_param.num_feature = 45`, `objective = binary:logistic`, `scale_pos_weight=2.70527601`, `feature_names = None` | **45** cột; 18 fold |
| Ma trận đo | `corr45.csv` = 45×45; `/tmp/feats.json` = 45 tên | **45** |

Vì `feature_names = None` ở cả ONNX lẫn model JSON, **ánh xạ index → tên dùng thứ tự Java** (`f0..f39`
= `convertFeaturesToArray`; index 40..44 = `oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy`).
Thứ tự này được `FEAT40_LOOKAHEAD.md` CÂU 1 xác nhận khớp 1-1 với `FEAT` của
`gen_funding_wf_predictions_1m.py:70` và với `SelectorOnnxInferenceManager.extractFeatures45`
(`ai_ml/onnx/funding/SelectorOnnxInferenceManager.java:56-76`) ⇒ không lệch train/serve về thứ tự cột.

**Kết luận: 45 feature thật, khớp expectation. Không ép về 40, không có feature "ma".**

---

## 1. Bảng 45 feature — nguồn · công thức/cửa sổ · causal?

Nguồn công thức: `docs/experiment/FEAT40_LOOKAHEAD.md` §CÂU 2 (bảng 40/40, có `file:line`) và §CÂU 3 (5 feature OI).
Cột **causal?** = "feature có dùng dữ liệu sau thời điểm quyết định `t_dec` hay không" theo soát đã có.

Quy ước: `t` = mốc nến 1m đóng; `t_dec` = thời điểm ra quyết định. 11 feature có dùng nến **tại `t`**
(f11, f16, f26, f37, f38, f39 và các close/high/low của f0..f10, f28, f29, f35) là **hợp lệ** theo quy ước
bar-close vì nhãn gốc neo vào close của **chính** nến đó (`ExportFundingLabel.java:429-431,751-752,732-733`).

| # | Tên | Nguồn | Công thức / cửa sổ | Causal? |
|---|---|---|---|---|
| 0 | btcMomentum1H | Tool1 `f0` | `close_BTC(t)/close_BTC(t-60m)-1`, `[t-60m,t]` | CÓ (sạch, `FDCM:489,577-580; HM:427-437`) |
| 1 | btcMomentum4H | Tool1 `f1` | idem, 240m | CÓ (sạch) |
| 2 | btcMomentum24H | Tool1 `f2` | idem, 1440m | CÓ (sạch) |
| 3 | btcDominance | Tool1 `f3` | `vol_BTC(t)/sum vol(t)`, `{t}` | CÓ (sạch) ⚠ survivorship `diedSymbol` (`MBCD:63`, `MDIG:63`) |
| 4 | marketBreadthStrength | Tool1 `f4` | `#(close>open tại t)/#valid`, `{t}` | CÓ (sạch) ⚠ survivorship |
| 5 | rateDown15MAvg | Tool1 `f5` | `avg top-100 (close(t)/max15m-1)`, `[t-14m,t]` | CÓ (sạch) ⚠ survivorship |
| 6 | momentum1H | Tool1 `f6` | `close(t)/close(t-60m)-1` | CÓ (sạch) |
| 7 | momentum4H | Tool1 `f7` | idem, 240m | CÓ (sạch) |
| 8 | momentum24H | Tool1 `f8` | idem, 1440m | CÓ (sạch) |
| 9 | rsi1H | Tool1 `f9` | RSI14 trên 14 nến 1m, `[t-14m,t]` | CÓ (sạch) |
| 10 | distFromLow24H | Tool1 `f10` | `(close(t)-low24)/low24` | CÓ (sạch) |
| 11 | volatilityShock | Tool1 `f11` | `(high(t)-low(t))/avgRange20`, `{t}`+`[t-21m,t-1]` | CÓ (sạch, nến `t` hợp lệ) |
| 12 | basketMomentum15M | Tool1 `f12` | `avg_basket getReturn(15)` | CÓ (sạch) |
| 13 | basketMomentum1H | Tool1 `f13` | `avg_basket getReturn(60)` | CÓ (sạch) |
| 14 | basketMomentum24H | Tool1 `f14` | `avg_basket getReturn(1440)` | CÓ (sạch) |
| 15 | basketRsi14 | Tool1 `f15` | `avg_basket RSI14` | CÓ (sạch) |
| 16 | basketVolSpike | Tool1 `f16` | `avg_basket vol(t)/avgVol20` | CÓ (sạch, volume nến `t` hợp lệ) |
| 17 | coinFundingRate | Tool1 `f17` | funding settlement gần nhất `<= t` (`floorEntry`) | CÓ (sạch, `FFM:119`) |
| 18 | basketFundingAvg | Tool1 `f18` | `avg_basket` của f17 | CÓ (sạch) |
| 19 | fundingRateAvg24H | Tool1 `f19` | avg `floorEntry` tại `t-0,4,8,12,16,20,24h` | CÓ (sạch) |
| 20 | fundingRateTrend | Tool1 `f20` | `f17 - f19` | CÓ (sạch) |
| 21 | fundingPercentileCoin | Tool1 `f21` | percentile funding hiện tại trong **toàn lịch sử `<= t`** (expanding) | CÓ (sạch) ⚠ trôi theo lịch |
| 22 | fundingZCoin | Tool1 `f22` | z-score trên cùng tập expanding `<= t` | CÓ (sạch) ⚠ trôi theo lịch |
| 23 | fundingPersistence | Tool1 `f23` | số kỳ liên tiếp cùng dấu, quét lùi từ kỳ `<= t` | CÓ (sạch) ⚠ **proxy thời gian** (mean 22.95→223.91 giữa 2022Q1→2024Q1) |
| 24 | fundingSum24h | Tool1 `f24` | `sum` funding settle trong `(t-24h, t]` | CÓ (sạch) |
| 25 | fundingAbs | Tool1 `f25` | `abs(funding kỳ <= t)` | CÓ (sạch) |
| 26 | volumeZCoin | Tool1 `f26` | `(vol(t)-mean20_truoc)/std20_truoc` (bỏ nến `t` khỏi mean/std) | CÓ (sạch, volume nến `t` hợp lệ) |
| 27 | volumeTrend | Tool1 `f27` | `avgVol5/avgVol60` (đều bỏ nến `t`) | CÓ (sạch) |
| 28 | distFromHigh24H | Tool1 `f28` | `(high24-close(t))/high24` | CÓ (sạch) |
| 29 | rangePosition24H | Tool1 `f29` | `(close(t)-low24)/(high24-low24)` | CÓ (sạch) |
| 30 | atrSqueeze | Tool1 `f30` | `avgRange14/avgRange100` (bỏ nến `t`) | CÓ (sạch) |
| 31 | relStrengthBtc24H | Tool1 `f31` | `f8 - f2` | CÓ (sạch) |
| 32 | fundingRankCS | Tool1 `f32` | rank-percentile f17 giữa các coin **cùng mốc `t`** | CÓ (sạch, `EFP:447-468`) |
| 33 | volumeZRankCS | Tool1 `f33` | rank-percentile f26 cùng mốc `t` | CÓ (sạch) |
| 34 | momentumRankCS | Tool1 `f34` | rank-percentile f8 cùng mốc `t` | CÓ (sạch) |
| 35 | ret15m | Tool1 `f35` | `close(t)/close(t-15m)-1` | CÓ (sạch, `FDCM:472`) |
| 36 | rvol15m | Tool1 `f36` | `std` của return giữa 15 nến gần nhất | CÓ (sạch, `FDCM:473; HM:442-460`) |
| 37 | volumeZ5m | Tool1 `f37` | `sumVol5/(avgVol20*5)` | CÓ (sạch, volume nến `t` hợp lệ) |
| 38 | closePosRange15m | Tool1 `f38` | `(close(t)-low15)/(high15-low15)` | CÓ (sạch, high/low nến `t` hợp lệ) |
| 39 | wickRatio15m | Tool1 `f39` | `avg (high-max(open,close))/(high-low)` trên 15 nến | CÓ (sạch, `FDCM:482`) |
| 40 | oi_delta24h | OI tool `#41` | `oi(t)/oi(t-24h)-1`, `ExportFundingOiPerCoin.java:104-107` | **CHƯA ĐÓNG** (xem §5) |
| 41 | oi_z | OI tool `#42` | OI z-score **expanding no-leak** (comment `:18`), `:85` | **CHƯA ĐÓNG** |
| 42 | ls_global | OI tool `#43` | long/short ratio global (Binance metrics) | **CHƯA ĐÓNG** |
| 43 | ls_toptrader | OI tool `#44` | long/short ratio top traders | **CHƯA ĐÓNG** |
| 44 | taker_buy | OI tool `#45` | `takerBuyRatio r/(1+r)`, `:117-124` | **File deploy sạch**; nguồn Vision thô có đổi nghĩa `create_time` 2024-03-04 |

---

## 2. Importance — 18 model fold S1 (`model_f0..f17_4h.json`), gain/cover/weight

- **Nguồn:** `/home/ubuntu/claudedata/predwf_G015/model_f{0..17}_4h.json` (mtime 2026-08-14, kernel
  `chuyendinh/selector-15mtr-pred15-net015-gpu`) — **model đã train, KHÔNG train lại** trong phiên này.
  Đọc bằng `xgboost.Booster.load_model` + `get_score('gain'|'cover'|'weight')`, map index 0..44 theo thứ tự Java.
- `weight` = số lần feature được dùng để split; `gain` = tổng gain; `cover` = tổng số dòng phủ.
  `share%` = gain chuẩn hoá **theo từng fold** (mỗi fold cộng đúng 100%).
- `top10/18` = số fold feature nằm trong top-10 theo gain.
- ⚠ Chưa có file ánh xạ fold → cutoff (18 model, 16 bin `predict_wf_*`), nên "độ ổn định" ở đây =
  **qua 18 model fold**, không gắn được với mốc lịch cụ thể. Chưa xác minh mapping này.

**Top-10 theo gain (mean ± sd qua 18 fold):**

| Hạng | # | Tên | gain mean ± sd | share% | weight | top10/18 |
|---|---|---|---|---|---|---|
| 1 | 36 | rvol15m | 37.977 ± 19.504 | **34,09** | 238,0 | 18 |
| 2 | 28 | distFromHigh24H | 8.354 ± 5.375 | 7,06 | 287,9 | 18 |
| 3 | 40 | oi_delta24h | 5.977 ± 3.226 | 5,74 | 139,4 | 17 |
| 4 | 10 | distFromLow24H | 4.395 ± 2.515 | 3,78 | 377,8 | 18 |
| 5 | 31 | relStrengthBtc24H | 3.632 ± 4.106 | 2,64 | 106,3 | 8 |
| 6 | 35 | ret15m | 3.225 ± 2.693 | 2,56 | 37,1 | 11 |
| 7 | 29 | rangePosition24H | 2.852 ± 2.472 | 2,16 | 77,9 | 9 |
| 8 | 44 | taker_buy | 2.679 ± 1.191 | 2,65 | 156,9 | 12 |
| 9 | 7 | momentum4H | 2.384 ± 1.427 | 2,02 | 173,5 | 13 |
| 10 | 6 | momentum1H | 2.039 ± 2.405 | 1,50 | 72,9 | 6 |

**Bottom-5 theo gain:** #33 `volumeZRankCS` (112 ± 153; share 0,09%; weight 2,4) · #26 `volumeZCoin`
(223 ± 186; 0,20%; weight 5,2) · #34 `momentumRankCS` (409 ± 209) · #27 `volumeTrend` (453 ± 237) ·
#37 `volumeZ5m` (461 ± 399). Hai feature **bằng 0 gain ở ≥1 fold**: #26 và #33.

**Nhận xét bằng số:** `rvol15m` một mình chiếm **34,09%** gain — gấp **4,8×** feature hạng 2; nhóm
price-structure 24H (#10, #28, #29, #31) + momentum (#6,#7,#8) chiếm phần lớn phần còn lại. 5 feature OI
chiếm tổng ~13,0% share. Nhóm volume per-coin (#26,#27,#33,#37) gần như **không được dùng**.

Bảng đầy đủ 45 dòng (importance + rank-IC + decile edge + cluster) ở **§4**.

---

## 3. rank-IC và decile edge (đo mới, DEV 3 quý)

**Phương pháp** (`/tmp/evfeat/analyze2.py`, `/tmp/evfeat/analyze3.py`):
- `rank-IC` = Spearman cross-section **trong từng tick** giữa feature và nhãn `retEnd_4h`
  (`/home/ubuntu/label_15m/funding_label_*.pb`, khớp exact `(symId, ts)`), lấy trung bình qua tick.
- `decile edge` = `mean(retEnd_4h | decile 10) − mean(retEnd_4h | decile 1)` theo decile trong tick.
- CI = block-bootstrap khối **72h**, **400 rep**, seed 20260924. **Chưa áp `inflate x1.21`** (khác chuẩn
  `RESULT_TREND_RANK_IC.md` dùng 2000 rep + x1.21) ⇒ CI ở đây **hẹp hơn thực**; dùng để xếp hạng nội bộ,
  không dùng làm căn cứ duy nhất.
- Nhãn `retEnd_4h` **không phải** nhãn train của selector (`y = (maxFav_4h >= 6%)`). Vì vậy IC ở đây đo
  "feature có xếp hạng được lợi nhuận 4h không", **không** phải "feature có giúp model phân loại WIN không".

**Hai phát hiện phương pháp luận (phải đọc trước khi dùng bảng):**

1. **12 feature KHÔNG có phương sai cross-section** — đo bằng `frac_tick_constant` (`varcheck.log`):
   `f0,f1,f2,f3,f4,f5,f12,f13,f14,f15,f16,f18` ≈ **0,9992** số tick là hằng số trong tick (f4 0,9994;
   f5 0,9993). Đây đúng là **nhóm market/basket-level** (BTC momentum, dominance, breadth, rateDown,
   basket momentum/RSI/volSpike, basketFundingAvg) — mỗi tick mọi coin dùng **cùng một giá trị**.
   Hệ quả số học: `n_tick` của chúng chỉ **17–25** (không phải 26.124), `decile_edge.csv` để trống
   (`n_tick=0`). ⇒ **rank-IC/decile của 12 feature này VÔ NGHĨA**, không được trích như bằng chứng
   "yếu"; muốn đánh giá phải dùng IC chuỗi thời gian (panel), **chưa làm trong phiên này**.
2. `n_tick` của 33 feature còn lại = **26.118–26.124** (đủ lớn); `oi_delta24h` 26.118.

**Kết quả định lượng chính (33 feature đo được):**

- `|rank-IC|` **lớn nhất cũng chỉ 0,0431** (`f10 distFromLow24H`, CI `[-0,0500,-0,0361]`);
  tiếp theo `f36 rvol15m` −0,0424, `oi_z` −0,0305, `ls_toptrader` **+0,0271**, `f7` −0,0269,
  `f34` −0,0236, `f31` −0,0220, `ls_global` **+0,0216**. So sánh: rank-IC của **chính selector** trên
  4h là ~**0,21–0,29** (`wfo_selector_results.json`) ⇒ tín hiệu **đơn biến** của từng feature kém
  **~1 bậc độ lớn** so với model gộp. Đây là kỳ vọng của bài toán đa biến, không phải lỗi.
- **decile edge kinh tế ≈ 0:** toàn bộ 33 edge nằm trong `[-4,9bp, +3,3bp]` trên lợi nhuận 4h; chỉ
  **2 feature** có CI không chứa 0 — `f35 ret15m` (−1,73bp `[-3,21,-0,05]`) và `ls_global`
  (−4,94bp `[-9,77,-0,76]`) — cả hai đều **nhỏ hơn chi phí giao dịch**. ⇒ không feature nào tự nó
  tạo edge tradable khi đứng riêng.
- **Dấu IC đáng chú ý (ngược trực giác "mua cái mạnh"):** momentum các khung (`f6,f7,f8,f31,f34`),
  `f10 distFromLow24H` đều có IC **âm** (coin đã tăng/lệch khỏi đáy 24H → lợi nhuận 4h sau **thấp hơn**);
  `ls_toptrader/ls_global` có IC **dương** mạnh nhất trong nhóm tín hiệu (top-trader
  long/short cao → lợi nhuận cao hơn) — **khác dấu** so với `maxFav_72h` trong `IC_STAB.out`
  (`ls_toptrader −0,1059`), do khác nhãn và khác khung thời gian. Không dùng chéo hai bảng.

---

## 4. Bảng đầy đủ 45 feature (importance + rank-IC + edge + cluster)

| # | tên | gain mean ± sd | share% mean ± sd | weight | top10/18 | rank-IC [CI95] | hit | decile edge (bp) [CI95] | clu |
|---|---|---|---|---|---|---|---|---|---|
| 0 | btcMomentum1H | 666 ± 208 | 0.74 ± 0.29 | 361.4 | 0 | +0.0042 [-0.0240, +0.0296] | 0.48 | — | 0 |
| 1 | btcMomentum4H | 1068 ± 331 | 1.17 ± 0.42 | 788.0 | 0 | +0.0038 [-0.0269, +0.0304] | 0.60 | — | 1 |
| 2 | btcMomentum24H | 1571 ± 674 | 1.60 ± 0.38 | 1257.7 | 0 | -0.0190 [-0.0462, +0.0107] | 0.40 | — | 2 |
| 3 | btcDominance | 785 ± 251 | 0.87 ± 0.36 | 372.0 | 0 | +0.0074 [-0.0246, +0.0347] | 0.56 | — | 3 |
| 4 | marketBreadthStrength | 642 ± 267 | 0.68 ± 0.24 | 277.9 | 0 | -0.0207 [-0.0536, +0.0118] | 0.47 | — | 4 |
| 5 | rateDown15MAvg | 1463 ± 758 | 1.39 ± 0.30 | 332.9 | 2 | -0.0126 [-0.0401, +0.0184] | 0.41 | — | 5 |
| 6 | momentum1H | 2039 ± 2405 | 1.50 ± 1.05 | 72.9 | 4 | -0.0208 [-0.0257, -0.0168] | 0.43 | -1.21bp [-4.12, +2.09] | 6 |
| 7 | momentum4H | 2384 ± 1427 | 2.02 ± 0.41 | 173.5 | 13 | -0.0269 [-0.0335, -0.0200] | 0.42 | +0.29bp [-3.84, +4.29] | 7 |
| 8 | momentum24H | 2011 ± 954 | 2.30 ± 1.24 | 90.3 | 10 | -0.0210 [-0.0286, -0.0127] | 0.44 | +3.26bp [-1.88, +8.50] | 8 |
| 9 | rsi1H | 557 ± 299 | 0.50 ± 0.05 | 71.9 | 0 | -0.0093 [-0.0113, -0.0069] | 0.46 | -0.31bp [-1.61, +0.97] | 9 |
| 10 | distFromLow24H | 4395 ± 2515 | 3.78 ± 0.62 | 377.8 | 18 | -0.0431 [-0.0500, -0.0361] | 0.38 | +2.84bp [-2.34, +7.92] | 10 |
| 11 | volatilityShock | 556 ± 313 | 0.49 ± 0.07 | 43.4 | 0 | +0.0033 [+0.0015, +0.0050] | 0.51 | +0.21bp [-0.91, +1.13] | 11 |
| 12 | basketMomentum15M | 781 ± 419 | 0.75 ± 0.15 | 207.4 | 0 | -0.0170 [-0.0473, +0.0104] | 0.56 | — | 12 |
| 13 | basketMomentum1H | 1051 ± 491 | 1.03 ± 0.19 | 355.5 | 0 | -0.0213 [-0.0503, +0.0038] | 0.36 | — | 13 |
| 14 | basketMomentum24H | 1386 ± 434 | 1.54 ± 0.58 | 1134.9 | 5 | +0.0006 [-0.0279, +0.0322] | 0.48 | — | 14 |
| 15 | basketRsi14 | 540 ± 207 | 0.58 ± 0.21 | 227.3 | 0 | -0.0100 [-0.0361, +0.0169] | 0.48 | — | 12 |
| 16 | basketVolSpike | 496 ± 178 | 0.55 ± 0.22 | 274.3 | 0 | +0.0002 [-0.0296, +0.0310] | 0.44 | — | 15 |
| 17 | coinFundingRate | 1612 ± 594 | 1.67 ± 0.41 | 257.9 | 5 | +0.0082 [+0.0045, +0.0125] | 0.54 | +1.57bp [-7.53, +11.29] | 16 |
| 18 | basketFundingAvg | 1421 ± 461 | 1.56 ± 0.57 | 2106.7 | 5 | +0.0020 [-0.0272, +0.0301] | 0.52 | — | 17 |
| 19 | fundingRateAvg24H | 1295 ± 688 | 1.28 ± 0.37 | 161.6 | 0 | +0.0092 [+0.0046, +0.0135] | 0.54 | +3.80bp [-2.19, +9.61] | 18 |
| 20 | fundingRateTrend | 1388 ± 755 | 1.30 ± 0.20 | 169.7 | 0 | -0.0018 [-0.0058, +0.0017] | 0.48 | -1.37bp [-4.46, +1.41] | 19 |
| 21 | fundingPercentileCoin | 895 ± 459 | 0.85 ± 0.14 | 91.9 | 0 | +0.0067 [+0.0024, +0.0107] | 0.52 | -0.49bp [-3.94, +3.48] | 16 |
| 22 | fundingZCoin | 887 ± 283 | 0.96 ± 0.32 | 86.2 | 0 | -0.0038 [-0.0087, +0.0011] | 0.48 | -1.42bp [-5.19, +2.77] | 20 |
| 23 | fundingPersistence | 563 ± 241 | 0.59 ± 0.20 | 172.2 | 0 | +0.0089 [+0.0051, +0.0129] | 0.54 | +0.98bp [-2.83, +4.75] | 21 |
| 24 | fundingSum24h | 1338 ± 578 | 1.35 ± 0.33 | 285.6 | 1 | +0.0033 [-0.0010, +0.0078] | 0.52 | -0.24bp [-7.63, +8.70] | 18 |
| 25 | fundingAbs | 1139 ± 505 | 1.21 ± 0.47 | 106.4 | 0 | -0.0050 [-0.0085, -0.0014] | 0.48 | -4.37bp [-10.11, +0.79] | 22 |
| 26 | volumeZCoin | 223 ± 186 | 0.20 ± 0.14 | 5.2 | 0 | +0.0003 [-0.0010, +0.0016] | 0.50 | -0.51bp [-1.30, +0.37] | 23 |
| 27 | volumeTrend | 453 ± 237 | 0.44 ± 0.10 | 38.8 | 0 | -0.0043 [-0.0054, -0.0031] | 0.48 | +0.27bp [-0.68, +1.13] | 24 |
| 28 | distFromHigh24H | 8354 ± 5375 | 7.06 ± 1.42 | 287.9 | 18 | -0.0161 [-0.0223, -0.0082] | 0.46 | -1.08bp [-5.58, +3.39] | 25 |
| 29 | rangePosition24H | 2852 ± 2472 | 2.16 ± 1.08 | 77.9 | 9 | -0.0122 [-0.0201, -0.0057] | 0.47 | +2.97bp [-1.23, +6.91] | 26 |
| 30 | atrSqueeze | 1818 ± 1270 | 1.47 ± 0.40 | 184.9 | 7 | -0.0042 [-0.0061, -0.0023] | 0.48 | -0.73bp [-1.90, +0.61] | 27 |
| 31 | relStrengthBtc24H | 3632 ± 4106 | 2.64 ± 1.81 | 106.3 | 8 | -0.0220 [-0.0284, -0.0151] | 0.44 | +3.26bp [-1.79, +8.40] | 8 |
| 32 | fundingRankCS | 1410 ± 532 | 1.53 ± 0.57 | 425.0 | 3 | +0.0050 [+0.0000, +0.0098] | 0.53 | +1.58bp [-8.26, +11.57] | 28 |
| 33 | volumeZRankCS | 112 ± 153 | 0.09 ± 0.10 | 2.4 | 0 | +0.0003 [-0.0013, +0.0018] | 0.50 | -0.51bp [-1.43, +0.44] | 23 |
| 34 | momentumRankCS | 409 ± 209 | 0.41 ± 0.14 | 65.3 | 0 | -0.0236 [-0.0312, -0.0155] | 0.44 | +3.26bp [-1.34, +7.98] | 29 |
| 35 | ret15m | 3225 ± 2693 | 2.56 ± 1.55 | 37.1 | 11 | -0.0128 [-0.0150, -0.0103] | 0.45 | -1.73bp [-3.21, -0.05] | 9 |
| 36 | rvol15m | 37977 ± 19504 | 34.09 ± 2.98 | 238.0 | 18 | -0.0424 [-0.0491, -0.0359] | 0.39 | +1.51bp [-3.21, +6.46] | 30 |
| 37 | volumeZ5m | 461 ± 399 | 0.38 ± 0.14 | 22.2 | 0 | -0.0012 [-0.0020, -0.0004] | 0.49 | -0.31bp [-0.92, +0.20] | 31 |
| 38 | closePosRange15m | 546 ± 379 | 0.44 ± 0.13 | 33.0 | 0 | -0.0032 [-0.0052, -0.0015] | 0.48 | +1.02bp [-0.05, +2.17] | 9 |
| 39 | wickRatio15m | 1654 ± 1315 | 1.21 ± 0.62 | 43.9 | 2 | -0.0134 [-0.0154, -0.0113] | 0.44 | -0.91bp [-2.28, +0.49] | 32 |
| 40 | oi_delta24h | 5977 ± 3226 | 5.74 ± 2.82 | 139.4 | 17 | -0.0111 [-0.0168, -0.0054] | 0.46 | -0.30bp [-4.88, +4.08] | 33 |
| 41 | oi_z | 1828 ± 658 | 2.02 ± 0.91 | 191.4 | 7 | -0.0305 [-0.0357, -0.0251] | 0.39 | +0.21bp [-3.55, +3.98] | 34 |
| 42 | ls_global | 1514 ± 551 | 1.58 ± 0.45 | 183.8 | 5 | +0.0216 [+0.0157, +0.0274] | 0.58 | -4.94bp [-9.77, -0.76] | 35 |
| 43 | ls_toptrader | 934 ± 266 | 1.05 ± 0.44 | 219.1 | 0 | +0.0271 [+0.0210, +0.0334] | 0.60 | -3.59bp [-8.75, +1.24] | 35 |
| 44 | taker_buy | 2679 ± 1191 | 2.65 ± 1.16 | 156.9 | 12 | -0.0017 [-0.0030, -0.0004] | 0.49 | -0.00bp [-0.65, +0.63] | 36 |

Đọc bảng: `gain`/`share%`/`wt` = mean qua 18 fold; `top10/18` = số fold vào top-10 gain;
`rank-IC [CI95]` 400 rep khối 72h; `edge` = decile 10 − decile 1 (bp, trên `retEnd_4h`);
`hit` = tỉ lệ tick có IC > 0; `clu` = id đám trùng lặp (§5).

---

## 5. Đám trùng lặp (|rho| ≥ 0,8) và độ ổn định

**Phương pháp:** Spearman trên mẫu 250.000 dòng của `joined.parquet`, gom đám tham lam theo
`|rho| >= 0,8` (`analyze3.py`, `clusters.json`, `pairs.json`).

- **37 đám**: **30 đám đơn** + **7 đám có ≥2 feature** (phủ 15 feature).
- **8 cặp mạnh** vượt ngưỡng:

| Cặp | rho | Diễn giải | Hệ quả |
|---|---|---|---|
| `f9 rsi1H` – `f35 ret15m` | **0,899** | RSI 1H ≈ hàm của return 15m | cắt được 1 trong 3 (#9/#35/#38) |
| `f9 rsi1H` – `f38 closePosRange15m` | 0,832 | idem | |
| `f12 basketMomentum15M` – `f15 basketRsi14` | **0,922** | basket RSI ≈ basket momentum | cắt được 1 |
| `f8 momentum24H` – `f31 relStrengthBtc24H` | 0,824 | `f31 = f8 − f2` (định nghĩa) | **không** cắt được cả hai |
| `f17 coinFundingRate` – `f21 fundingPercentileCoin` | 0,800 | percentile lịch sử của chính funding | ứng viên cắt f21 |
| `f19 fundingRateAvg24H` – `f24 fundingSum24h` | 0,811 | cùng cửa sổ 24h | ứng viên cắt 1 |
| `f26 volumeZCoin` – `f33 volumeZRankCS` | 0,814 | rank của chính nó | cả hai đều vô dụng |
| `ls_global` – `ls_toptrader` | **0,932** | 2 nguồn LS gần trùng | ứng viên cắt 1, nhưng **ls_toptrader có \|IC\| lớn nhất** trong nhóm dương |

**Ổn định qua 18 fold (importance):**
- Rất ổn định (`top10` ở ≥13/18 fold): `rvol15m` 18/18, `distFromHigh24H` 18/18, `distFromLow24H` 18/18,
  `oi_delta24h` 17/18, `momentum4H` 13/18.
- **DAO ĐỘNG** (share CV ≥ 0,45 ⇒ không nên dùng để "đo lường" tầm quan trọng chính xác):
  `volumeZRankCS` CV 1,13 · `momentum1H` 0,70 · `relStrengthBtc24H` 0,68 · `volumeZCoin` 0,68 ·
  `ret15m` 0,61 · `momentum24H` 0,54 · `wickRatio15m` 0,51 · `rangePosition24H` 0,50 ·
  `oi_delta24h` 0,49 · `oi_z` 0,45.
- **Ổn định theo năm** (cửa sổ đo tách rời nhau nên importance chỉ đo qua fold model): chưa đo được
  theo năm vì thiếu mapping fold→cutoff (§2). `retEnd_4h` nền: mean −0,00024 / std 0,0355 / `>1,5%`
  = 20,7% (`nanpass.log`) — nền đủ để IC nhỏ vẫn có thể nhất quán.

**NaN:** tỉ lệ NaN thấp — cao nhất `f22` 0,58%, `f21` 0,52%, `f23..f25` ~0,49%, `oi_delta24h` 0,32%;
33 feature còn lại ≤0,01%. Không có feature nào bị NaN hệ thống. **Lưu ý cho ablation:** mask NaN của
candidate phải dùng lại **đúng** mask này (bài học `RESULT_S1_FREE_OFI.md`).

**Feature nghi LEAK / phải ghi đè (theo `docs/experiment/FEAT40_LOOKAHEAD.md`, không đo lại ở đây):**
1. `taker_buy` (#44): nguồn Vision thô đổi nghĩa `create_time` từ 2024-03-04 (cuối→đầu cửa sổ 5m)
   ⇒ leak 5 phút **ở nguồn thô**; **file triển khai `claudedata/oi/oi_percoin_full.bin` đã SẠCH**
   (DINH CHINH #2: 450/450 mẫu khớp cửa sổ đóng, 0/140.924.110 dòng sai lưới ts). Còn tồn: **train/serve
   skew trên đường LIVE** nếu bật forward ingest ⇒ phải dịch `+5m` chỉ cho `takerlongshortRatio`.
2. 4 feature OI còn lại (`oi_delta24h`, `oi_z`, `ls_global`, `ls_toptrader`): **chưa có bằng chứng hai
   chiều** — nếu mốc 2024-03-04 là đổi nghĩa cho **cả file** thì cả 5 feature OI đều lệch 5 phút.
   Đây là **lỗ hổng mở lớn nhất** (mục "CÒN LẠI CHƯA ĐÓNG" #1 của FEAT40_LOOKAHEAD).
3. `f21/f22` (percentile/z expanding) và `f23 fundingPersistence` (proxy thời gian, mean 22,95→223,91):
   **không phải leak**, nhưng là **rủi ro tổng quát hoá/dịch phân phối** giữa các fold — ưu tiên kiểm
   trong ablation.
4. `f3/f4/f5`: **survivorship** qua `Constants.diedSymbol` (`MBCD:63`, `MDIG:63`) — thiên lệch đã biết,
   **chưa đo lại**.

---

## 6. ⭐ Ba nhóm: NGẮT CHẮC / CÂN NHẮC / GIỮ

**Luật phân nhóm (chốt trước, chỉ dùng số ở §2):** share = `share%` gain trung bình 18 fold.

- **NGẮT CHẮC** nếu `share < 0,40%` (bị model **gần như không dùng**), **HOẶC** `share < 0,65%` **VÀ**
  nằm trong đám `|rho| ≥ 0,8` với partner có share ≥ 2,5× (**vừa yếu vừa bị thay thế**).
- **CÂN NHẮC** nếu `0,40% ≤ share < 1,30%` (có thể có tín hiệu nhưng model dùng ít / trùng một phần /
  đo không được bằng cross-section).
- **GIỮ** nếu `share ≥ 1,30%`.

Kết quả: **NGẮT CHẮC 5 · CÂN NHẮC 18 · GIỮ 22** (5+18+22 = 45).

### 6.1 NGẮT CHẮC — **5 feature**

| # | Tên | Lý do bằng số |
|---|---|---|
| 33 | volumeZRankCS | share **0,09%** (thấp nhất 45), weight 2,4, top10 0/18, **gain = 0 ở ≥1 fold**; rho 0,814 với #26 (cùng vô dụng) ⇒ cắt hẳn |
| 26 | volumeZCoin | share **0,20%**, weight 5,2, **gain = 0 ở ≥1 fold**; partner #33 ⇒ giữ nhiều nhất 1 trong 2, và cả 2 đều dưới ngưỡng |
| 37 | volumeZ5m | share **0,38%**, weight 22,2, top10 0/18; rank-IC −0,0012 (CI sát 0), edge −0,31bp **[−0,92,+0,20]** (CI chứa 0) ⇒ không có tín hiệu độc lập |
| 38 | closePosRange15m | share **0,44%** nhưng **rho 0,83 với #35 ret15m (share 2,56% = 5,8×)** ⇒ bị thay thế; rank-IC −0,0032 (≈0) |
| 9 | rsi1H | share **0,50%** nhưng **rho 0,90 với #35 ret15m (5,1×)** ⇒ bị thay thế; edge −0,31bp CI chứa 0 |

### 6.2 CÂN NHẮC — **18 feature** (đưa vào vòng ablation để PHÂN XỬ, không cắt trước)

| # | Tên | share% | Vì sao CÂN NHẮC chứ không NGẮT |
|---|---|---|---|
| 34 | momentumRankCS | 0,41 | model dùng ít nhưng rank-IC −0,0236 **CI không chứa 0** ⇒ có tín hiệu, không "rác" |
| 27 | volumeTrend | 0,44 | singleton (không trùng ≥0,8), rank-IC −0,0043 CI không chứa 0 (rất nhỏ) |
| 11 | volatilityShock | 0,49 | singleton; rank-IC +0,0033 CI không chứa 0; edge CI chứa 0 ⇒ biên |
| 16 | basketVolSpike | 0,55 | **cross-section hằng số** ⇒ không đo được; cùng họ basket → cắt cả họ là rủi ro |
| 15 | basketRsi14 | 0,58 | **hằng số cross-section**; rho 0,92 với #12 (0,75%) — chỉ cắt được 1 trong 2 |
| 23 | fundingPersistence | 0,59 | rank-IC +0,0089 CI không chứa 0 (tín hiệu thật) **nhưng là proxy thời gian** ⇒ nghi overfit |
| 4 | marketBreadthStrength | 0,68 | **hằng số cross-section** + survivorship trong cách dựng ⇒ chưa kết luận được |
| 0 | btcMomentum1H | 0,74 | **hằng số cross-section**; trùng khái niệm với #1/#2 (BTC momentum khung khác) |
| 12 | basketMomentum15M | 0,75 | **hằng số cross-section**; rho 0,92 với #15 |
| 21 | fundingPercentileCoin | 0,85 | rho 0,80 với #17 (1,67% = 2,0×) + expanding-history ⇒ ứng viên cắt nhưng only-just dưới 2,5× |
| 3 | btcDominance | 0,87 | **hằng số cross-section** + survivorship |
| 22 | fundingZCoin | 0,96 | expanding z ⇒ dịch phân phối giữa fold; rank-IC −0,0038 (CI chứa 0) |
| 13 | basketMomentum1H | 1,03 | **hằng số cross-section**; cửa sổ trùng #12/#14 |
| 43 | ls_toptrader | 1,05 | rho 0,932 với #42 (1,58%) — **nhưng \|rank-IC\| = 0,0271 lớn nhất nhóm dương** ⇒ chỉ cắt 1 trong 2 và phải đo |
| 1 | btcMomentum4H | 1,17 | **hằng số cross-section**; weight 788 (cao) nhưng share thấp ⇒ tín hiệu nằm ở tương tác |
| 25 | fundingAbs | 1,21 | rank-IC −0,0050 CI không chứa 0; edge −4,37bp CI chứa 0 ⇒ biên |
| 39 | wickRatio15m | 1,21 | singleton; rank-IC −0,0134 CI không chứa 0 (ổn định) ⇒ nghiêng GIỮ |
| 19 | fundingRateAvg24H | 1,28 | rho 0,811 với #24 (1,35%) — hai feature gần trùng, tổng 2,63% |

### 6.3 GIỮ — **22 feature** (share ≥ 1,30%; cắt là rủi ro cao)

`20 fundingRateTrend` 1,30 · `24 fundingSum24h` 1,35 · `5 rateDown15MAvg` 1,39 · `30 atrSqueeze` 1,47 ·
`6 momentum1H` 1,50 · `32 fundingRankCS` 1,53 · `14 basketMomentum24H` 1,54 · `18 basketFundingAvg` 1,56 ·
`42 ls_global` 1,58 · `2 btcMomentum24H` 1,60 · `17 coinFundingRate` 1,67 · `7 momentum4H` 2,02 ·
`41 oi_z` 2,02 · `29 rangePosition24H` 2,16 · `8 momentum24H` 2,30 · `35 ret15m` 2,56 ·
`31 relStrengthBtc24H` 2,64 · `44 taker_buy` 2,65 · `10 distFromLow24H` 3,78 · `40 oi_delta24h` 5,74 ·
`28 distFromHigh24H` 7,06 · `36 rvol15m` **34,09**.

Ghi chú GIỮ: `taker_buy` (#44) giữ vì share 2,65% **nhưng** kèm điều kiện phải đóng lỗ hổng nguồn OI
(§5); `f31 relStrengthBtc24H` giữ dù share dao động mạnh (CV 0,68) vì gain hạng 5.

---

## 7. Những gì KHÔNG đọc được / giới hạn của phiên này

1. **12 feature market/basket-level** (`f0..f5`, `f12..f16`, `f18`): không có rank-IC/decile hợp lệ
   (hằng số trong tick). Cần IC panel (chuỗi thời gian) để phân xử — **chưa làm**.
2. **Mapping fold → cutoff** của 18 model: không có file manifest → không gắn được importance với mốc lịch.
3. **Không có feature name trong artifact** (ONNX `metadata_props` rỗng, model JSON `feature_names=None`);
   ánh xạ index→tên dựa trên code Java + `FEAT40_LOOKAHEAD.md` CÂU 1 (khớp 1-1), không dựa trên artifact.
4. **CI ở §3 dùng 400 rep, không `inflate x1.21`**, khối 72h, seed 20260924 → **không** cùng chuẩn với
   `c3_rates.py`/`x1_rates.py`. Không dùng các CI này để tuyên bố PASS/FAIL.
5. **Nhãn đo (`retEnd_4h`) khác nhãn train (`maxFav_4h ≥ 6%`)** ⇒ IC thấp ở §3 **không** phủ định
   đóng góp của feature trong model.
6. **Chưa đo** `delta score` khi bỏ feature, chưa train lại, chưa sim (đúng ràng buộc phiên).
7. Nguồn `imp_*.npy`: script sinh **không được lưu lại** trên đĩa (đã grep `/tmp`, `/home/ubuntu/**/*.py`,
   `~/.bash_history` — không còn); provenance được truy lại từ transcript phiên trước: 18 file
   `model_f*_4h.json` như mô tả §2. Nếu cần tái lập: `xgboost.Booster.load_model` + `get_score(...)`
   cho 18 file đó (thao tác nhẹ, không train).

---

## ĐÍNH CHÍNH (2026-09-24) — NHÃN TRAIN ghi ở §3 là SAI

§3 (mục "Phương pháp") ghi nhãn train của selector là `y = (maxFav_4h >= 6%)` — **SAI**.

**Nhãn THẬT = `y = (retEnd_4h > 0.015)`**, base rate **0,1849**. Xác nhận 3 cách độc lập
(`docs/PREP_STAGE2_TRAIN.md`, commit `2231738`): log gốc của kernel train + đếm lại từ `.pb`
+ `scale_pos_weight` fold0 `2.70527601` ⇒ tỷ lệ dương **0,2699**.

Nhãn `maxFav >= 0,06` là của **họ `G015_v2` / model LIVE ONNX** — **KHÁC** với S1 dùng trong
nghiên cứu (spearman giữa 2 họ ≈ **0,854**). ⇒ Hai việc khác nhau, **không dùng chéo**.

Các kết luận ở §3 (rank-IC/decile theo `retEnd_4h`) vẫn đúng **với tư cách thước đo lợi nhuận 4h**,
nhưng **không** phải thước của nhãn train — đọc §3 phải nhớ điều này.
