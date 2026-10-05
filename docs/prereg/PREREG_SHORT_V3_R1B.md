# PREREG_SHORT_V3_R1B — SELECTOR tại phút trigger (model nhỏ trên 10 991 trigger R1)

Ngày 2026-10-02 · research engineer (agent) dưới MASTER Claude · nguồn: `docs/research/PROGRAM_SHORT_V3.md` ADDENDUM 1 §R1b (commit `df2ce308`).
Tái dùng per-trade R1 (`3fea4f50`, script `research/analysis/short_v3_r1_fade.py`). Chốt TRƯỚC khi đo. Sau khi thấy số: KHÔNG đổi gì trong file này;
ý tưởng mới chỉ vào mục "amend cho vòng sau" của RESULT.

## 1. Chép nguyên ADDENDUM 1 §R1b
### R1b — SELECTOR tại phút trigger (model tier + per-trade net), tái dùng per-trade R1 (`~/claude_master/1002/r1_cache/`)
Tập: đúng n = 10 991 trigger của R1 (không đổi trigger). Target: `net_B24` (ô B24 của R1) — chính; `net_B12` phụ (báo cáo).
Feature tại t (chỉ dùng ≤ t), KHÓA danh sách (bỏ feature nếu dữ liệu không có, ghi rõ, không thay bằng feature khác):
  f1 `r60`; f2 `r15` (close_t/close_{t-15}−1); f3 `ext24 = close_t/close_{t-1440}−1`; f4 `volratio = W0/M` của volclimax; f5 `wick = (high_t − close_t)/(high_t − low_t)` của nến t (nếu có H/L);
  f6 `fund_now` (rate kỳ hiện hành/dự kiến tại t, dấu: rate<0 ⇒ short trả); f7 `fund_sign` (= f6<0); f8 `dOI_60` (OI_t/OI_{t-60}−1 từ derivs_store nếu có độ phân giải ≤5'); f9 `takerLS` (long/short ratio nếu có);
  f10 `tier` (tercile quoteVol 30d); f11 `listing_age` (ngày từ listing_day, cap 365); f12 `btc_bull` (BTC>SMA50 ngày); f13 `btc_r60` (BTC 60' cùng lúc); f14 `n_trig_day` (số trigger khác trong 24h trước — đo "ngày sập/pump toàn thị trường").
Model: LightGBM (nếu không có thì sklearn HistGradientBoosting) hồi quy `net_B24`, tham số CỐ ĐỊNH (num_leaves 15, lr 0,05, 300 cây, min_child 100, feature_fraction 0,8, seed 20260905) — KHÔNG tune.
WFO theo NỬA NĂM: fold h ∈ {2023H1, 2023H2, 2024H1, 2024H2, 2025H1, 2025H2}: train trên mọi trigger có exit kết thúc trước đầu h − 72h, test h. (2022 chỉ train.)
Chấm (trên ghép 6 fold OOS): rank-IC(score, net_B24) theo fold; net tercile-TOP vs ALL; SL-rate tercile-top; theo năm; CI block-72h NREP 2000 seed 20260905 trên tercile-top, raw và inflate k=2 (B24 chính + B12 phụ) = 1,18; stress: net tercile-top − 0,10% (slippage spike) ; đối chứng: permutation (xáo nhãn 1 lần seed 20260905) ⇒ IC phải ≈ 0.
Báo thêm: importance; net theo decile score; ablation KHÓA 3 nhóm (bỏ f6–f9 "crowding"; bỏ f10–f14 "context"; chỉ f1–f5 "giá/vol") — chỉ báo cáo, không chọn.
GO-R1b ⇔ tất cả: rank-IC OOS > +0,05 và dương ≥5/6 fold; net tercile-top (B24) > 0 ngoài CI raw & inflate; ≥3/4 năm (2023–2025 + 2022-không-tính ⇒ 3/3); SL-rate tercile-top ≤ 25%; stress −0,10% vẫn > 0 ở điểm ước lượng; permutation IC ∈ [−0,02;+0,02].
GO ⇒ Pha kế: sim SỔ short (vốn, size, đồng thời, MTM phút) + đo slippage thật tại spike từ 1m volume; rồi engine.

## 2. Tập và nhãn (tái lập R1)
- Nguồn: `~/claude_master/1002/r1_cache/trades_r1.csv` (đầu ra `report` của R1; cooldown 24h đã áp) + `cand_YYYYMM.parquet` (c_t, cf60, maxprev).
- Nhãn chính `y24 = S_B24_net`; phụ `y12 = S_B12_net` (net = gross − 0,00112 + funding settle thực, đúng R1). Lý do exit `S_B24_r` (1 = SL).
- entry_ms = (t+2)·60000 − 1 (close phút t+1); exit_ms = (k+1)·60000 − 1 với k = cột `_k` (phút exit tuyệt đối). Năm = năm UTC của entry_ms.
- **Sanity tái lập (phải PASS trước khi đo):** n = 10 991; mean(S_B24_net) = +0,170% ± 0,005pp (R1: +0,170%); mean(S_B12_net) khớp R1 +0,101% ± 0,005pp.

## 3. Feature — nguồn, cách tính, GIỮ/BỎ (khoá TRƯỚC đo; quyết định GIỮ/BỎ dựa trên dữ liệu có sẵn, không trên kết quả)
Quy ước thời gian: phút t = phút trigger (giờ mở, UTC); close phút t biết tại T_t = (t+1)·60000 − 1 ms. Mọi nguồn phải có mốc ≤ T_t (assert theo từng dòng).
Đọc 1m: Aerospike `test.kline_1m_opt` (key TZ+7 như R1), CHỈ các phút cần (t, t−15, t−60, t−1440 + lùi tối đa 60' nếu coin thiếu bản ghi), không stream lại.
`Cf[x]` = close của bản ghi gần nhất ≤ x trong 60' lùi (≈ forward-fill của R1; thiếu > 60' ⇒ NaN).

| f | tên | cách tính / nguồn | trạng thái |
|---|---|---|---|
| f1 | r60 | cột `r60` của trades_r1.csv (= C[t]/Cf[t−60] − 1, R1) | GIỮ |
| f2 | r15 | C[t]/Cf[t−15] − 1, Aerospike 1m | GIỮ |
| f3 | ext24 | C[t]/Cf[t−1440] − 1, Aerospike 1m | GIỮ |
| f4 | volratio | W0/Mnen (cột trades_r1.csv, = volclimax R1) | GIỮ |
| f5 | wick | (H_t − C_t)/(H_t − L_t) nến t (field H,L,C của `kline_1m_opt`); H_t = L_t ⇒ NaN | GIỮ |
| f6 | fund_now | **PROXY TRỄ**: `/tmp/fund_cache.npz` chỉ có rate ĐÃ settle (fundingTime thật), không có predicted/premium index cho DEV ⇒ rate của sự kiện settle GẦN NHẤT có fundingTime ≤ T_t. Coin không có sự kiện ≤ T_t ⇒ NaN | GIỮ (proxy trễ, ghi rõ) |
| f7 | fund_sign | 1 nếu f6 < 0, 0 nếu f6 ≥ 0, NaN nếu f6 NaN | GIỮ (theo f6) |
| f8 | dOI_60 | derivs_store chỉ từ 2026-09. Nguồn OI DEV duy nhất: `claudedata/oi/oi_percoin_full.bin` (5m) có `oi_delta24h`, `oi_z` — **KHÔNG có OI thô** (RESULT_OI_STUDY §2, RESULT_PUMPDUMP_OHLCV) ⇒ không tính được OI_t/OI_{t−60} hay dOI_1h. Không thay bằng oi_delta24h/oi_z | **BỎ** |
| f9 | takerLS | `oi_percoin_full.bin` cột `taker_buy` = tỉ lệ KL taker-buy ∈ [0,1] trên cửa sổ 5m (ratio buy/sell = tb/(1−tb), đơn điệu ⇒ cây dùng tb trực tiếp, tương đương). Mốc: file ghi cửa sổ đã đóng [ts−5m, ts); **bảo thủ thêm 1 slot**: dùng dòng có ts ≤ (t+1)·60000 − 300000 gần nhất (lùi tối đa 12 slot = 1h, nếu không ⇒ NaN). Coverage 2022 thủng (01–04 ≈ 1–4%) ⇒ NaN, model xử lý NaN gốc | GIỮ |
| f10 | tier | cột `tier` R1 (tercile qv30 = mean quoteVol ngày d−30..d−1, xếp hạng toàn universe ngày d): NHO 0 / VUA 1 / LON 2 / NA ⇒ NaN | GIỮ |
| f11 | listing_age | listing_day = min(ngày đầu có dữ liệu trong `CLOSES_1H.bin` theo `eday` của R2, ngày đầu `nmin>0` trong cache `p0a_cache/qv`); age = min(365, (t·60000 − listing_day·86400000)/86400000) ngày; assert age ≥ 0. Coin niêm yết trước khi file bắt đầu ⇒ age bị chặn dưới bởi đầu file (thường đã chạm cap 365) | GIỮ |
| f12 | btc_bull | cột `regime` R1 (BTC close ngày d−1 > SMA50 d−50..d−1): BULL 1 / BEAR 0 / NA ⇒ NaN | GIỮ |
| f13 | btc_r60 | BTCUSDT: C[t]/Cf[t−60] − 1, Aerospike 1m cùng bản ghi phút | GIỮ |
| f14 | n_trig_day | số trigger KHÁC trong tập 10 991 có t' ∈ [t−1440, t−1] (trigger đã biết trước phút t) | GIỮ |

⇒ Bộ chính = **13 feature** (f1–f7, f9–f14); **BỎ f8**. Kiểm khớp dữ liệu (sanity): C[t] đọc lại = `c_t` cand parquet và Cf[t−60] = `cf60`
(lệch tương đối < 1e-6) trên ≥ 99,5% trigger; nếu không ⇒ DỪNG, không đo.

## 4. Model (LightGBM KHÔNG có trên Oracle ⇒ sklearn 1.7.2 `HistGradientBoostingRegressor`, tham số CỐ ĐỊNH)
`loss='squared_error', learning_rate=0.05, max_iter=300, max_leaf_nodes=15, min_samples_leaf=100, l2_regularization=0.0,
max_features=0.8, early_stopping=False, max_bins=255, random_state=20260905`.
Ánh xạ: num_leaves→max_leaf_nodes, 300 cây→max_iter, min_child→min_samples_leaf, feature_fraction 0,8→max_features 0,8 (sklearn chọn
ngẫu nhiên 80% feature ở MỖI nút thay vì mỗi cây — khác nhỏ, ghi nhận). **early_stopping=False bắt buộc** (mặc định 'auto' tự bật khi n>10 000
và cắt validation nội bộ). NaN xử lý gốc (không impute). Không chuẩn hoá, không trọng số. KHÔNG tune, không early-stopping theo test.
Hai model độc lập cùng tham số: M24 học `y24` (chính, GO); M12 học `y12` (phụ, chỉ báo cáo, dùng cùng fold/feature).

## 5. WFO nửa năm + purge 72h
Fold h ∈ {2023H1, 2023H2, 2024H1, 2024H2, 2025H1, 2025H2}, start_h = 01-01 / 07-01 00:00 UTC, end_h = start_{h+1} (2025H2 tới 2026-01-01).
Test_h = trigger có entry_ms ∈ [start_h, end_h). Train_h = trigger có max(exit_ms B24, exit_ms B12) < start_h − 72h (gồm 2022; mở rộng dần).
Assert mỗi fold: max exit_ms(train) < start_h − 72h; giao train ∩ test = ∅; mỗi trigger 2023–2025 thuộc đúng 1 fold test.

## 6. Chấm (OOS ghép 6 fold)
- **rank-IC fold** = Spearman(score, y24) trong test_h. **IC_OOS (chính) = trung bình 6 IC fold**; báo thêm IC pooled (Spearman trên ghép 6 fold).
- **Tercile theo fold:** trong mỗi test_h, xếp hạng score (rank 'first') ⇒ TOP = 1/3 score cao nhất, MID, BOT (chỉ dùng phân phối score
  của fold, không dùng nhãn; ghi giới hạn: live cần ngưỡng causal). Decile tương tự (10 nhóm theo fold) ⇒ net theo decile pooled.
- Với TOP (và báo MID/BOT/ALL-OOS): n, net mean, median, win%, SL-rate (`S_B24_r==1`), theo năm 2023/2024/2025,
  CI block 72h (block = floor(entry_ms/72h), Σsum/Σcount, NREP 2000, seed 20260905, phân vị 2,5/97,5) raw; inflate = nửa-độ-rộng × **1,18** (k=2).
- Stress: net_TOP − 0,10% (điểm ước lượng).
- B12 phụ: cùng bảng với M12/`y12` (không vào luật GO).
- **Permutation:** π = `default_rng(20260905).permutation(n)`; y24_perm = y24[π] (xáo trên toàn 10 991, 1 lần); chạy LẠI nguyên WFO (cùng
  feature, cùng tham số) học y24_perm ⇒ IC_perm = trung bình 6 Spearman(score_perm, y24_perm) trong test. Báo thêm Spearman(score_perm, y24 thật).
- **Importance:** `sklearn.inspection.permutation_importance` trên test_h mỗi fold, scorer = Spearman IC, n_repeats=5, random_state=20260905;
  báo trung bình độ giảm IC qua 6 fold (M24).
- **Ablation KHÓA (chỉ báo cáo):** A1 bỏ f6–f9 (crowding: f6,f7,f9 vì f8 đã BỎ); A2 bỏ f10–f14; A3 chỉ f1–f5. Mỗi biến thể: IC fold, IC_OOS,
  số fold dương, net TOP, SL TOP.

## 7. Luật GO-R1b (cơ học, M24 / y24) — GO ⇔ TẤT CẢ
- C1: IC_OOS > +0,05 VÀ IC > 0 ở ≥ 5/6 fold.
- C2: net TOP > 0 VÀ CI raw lo > 0 VÀ CI inflate(1,18) lo > 0.
- C3: net TOP > 0 ở cả 3 năm 2023, 2024, 2025 (2022 chỉ train, không tính).
- C4: SL-rate TOP ≤ 25%.
- C5: net TOP − 0,10% > 0 (điểm ước lượng).
- C6: IC_perm ∈ [−0,02; +0,02].
Thiếu 1 điều kiện ⇒ NO-GO. Không đổi tham số/feature/fold/ngưỡng sau khi thấy số.

## 8. Sanity bắt buộc (PASS trước khi báo số)
(S1) n = 10 991; mean y24 = +0,170% ± 0,005pp; mean y12 = +0,101% ± 0,005pp. (S2) Đọc lại Aerospike: C[t] khớp `c_t`, Cf[t−60] khớp `cf60`
(lệch tương đối < 1e-6) ≥ 99,5% trigger. (S3) Causality assert theo dòng: phút nguồn 1m ≤ t; ts OI ≤ (t+1)·60000 − 300000; fundingTime f6 ≤ T_t;
listing_day ≤ ngày(t); f14 chỉ đếm t' ≤ t−1. (S4) Fold không rò (mục 5). (S5) Model tất định: chạy M24 fold 2023H1 hai lần ⇒ dự báo trùng khít.

## 9. Giới hạn đã biết / ngoài phạm vi
f6 là proxy trễ (tới 8h) của funding hiện hành; f8 BỎ; f9 bảo thủ trễ 5–10'. Slippage tại spike chưa mô hình (net là CẬN TRÊN, như R1).
Tercile theo phân phối score của chính fold (không nhãn). n ~1 100–3 000/fold ⇒ IC fold nhiễu ±0,03–0,06.
Script: `research/analysis/short_v3_r1b_selector.py` → `docs/result/RESULT_SHORT_V3_R1B.json` + `.md`; feature/score per-trade ở `~/claude_master/1002/r1_cache/`.
