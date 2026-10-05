# PREREG S1_FEAT_GEOM — hình học intraday (HIGH/LOW) cho S1 ranker s1a2x1 — chốt TRƯỚC đo

Ngày 2026-10-03. Vòng CUỐI của hướng cải thiện S1 ranker cho B0 = G2+FLAT3. Nếu NO-GO ⇒ **ĐÓNG hướng feature S1 trên DEV**.
Bối cảnh: selector là lever (+24pp vs random, 33d8fc17), giá trị nằm ở ranking top-50→16 (b7fedef4). S1 = XGBRanker rank:ndcg,
relevance rel5 (ngũ phân vị g1lite − median tick, 72h), 9 feature KEEP9 chỉ từ close 1h. Đã NULL trên S1 (KHÔNG lặp): OI/LS/taker (OI12),
rel-strength/funding/long-horizon (FEATGRP), 15 feature microstructure/dollar-volume (FS), OFI, HPO, bagging, nhãn maxfav/first-hit
(06818fa6). **Chưa thử: hình học intraday từ HIGH/LOW** (S1 chỉ thấy close). Sàn nhiễu (f0b9d8e6): sd seed CAGR 0,83pp, MDE80 1v1
≈ +3,3pp CAGR / +0,6 Calmar ⇒ CTRL cùng đợt = K42 + S7 (Kaggle GPU, xgboost 3.2.0).

## 1. Store OHLC 1h mới (dữ liệu, không phải giả thuyết)
- File MỚI `/home/ubuntu/java/fsrun/OHLCV_1H_v2.bin` + manifest `OHLCV_1H_v2.manifest.json` (copy vào `data/meta/OHLCV_1H_v2_MANIFEST.json`).
  Không ghi đè/xoá file nào có sẵn. Script `research/analysis/s1_geom_store.py` (stage `month` → `merge`).
- Nguồn: Aerospike `test.kline_1m_opt`, 1 lượt stream theo tháng (hàm `stream` của `short_v3_r1_fade.py`, field 5 = quoteVol USDT),
  phút 2021-01-01 00:00 → 2025-12-31 23:59 UTC. Nến giờ [h, h+1h): **ts_h = h + 1h (giờ ĐÓNG, cùng quy ước CLOSES_1H)**,
  open = O phút hữu hạn đầu, high = max H, low = min L, close = C phút hữu hạn cuối, quoteVol = ΣV.
- Symbol: 627 symbol của `data/meta/symbol_lineage_v2.csv` (symId theo `symbol_map.csv`); STABLE bị `stream` loại.
  **Lineage v2**: bỏ giờ có h > floor_h(last_real_ts) (đuôi settle) và h < floor_h(first_real_ts) (đầu settle) — đúng luật F_TAIL/F_HEAD của v2.
- Format 30 B/rec big-endian `[ts_h:i8][symId:i2][open,high,low,close,quoteVol:f4]`, sort (ts_h, symId).
- Ước dung lượng: probe 4 ngày ⇒ phủ Aerospike ⊇ v2 (78/136/262/588 sym), ~10–11M rec ⇒ ~0,33 GB (thấp hơn ước 27M×24 B=0,65 GB). Disk trống 9,3 GB.
- **Cổng sanity (FAIL ⇒ dừng)**: S1 close store == close CLOSES_1H_v2 (float32, tuyệt đối) 100 % trên mẫu 30 sym × 24h liên tiếp
  (rng 20260905, chỉ ô v2 hữu hạn); S2 high ≥ max(open, close) và low ≤ min(open, close) trên TOÀN bộ rec. Thông tin: phủ (ts,sym) v2 ⊂ store, rec/năm.

## 2. Nhóm GEOM (9 cột) + noise — causal tại ts_h, chỉ dùng nến có ts ≤ ts_h
Tính trên lưới giờ đầy đủ của store (giờ thiếu = NaN, KHÔNG ffill), rolling theo hàng giờ, cửa sổ kết thúc tại ts_h (gồm nến hiện tại),
min_periods = n/2 (như builder): high24/low24 = max/min high/low 24h; high7d/low7d 168h.
1. pos24 = (close − low24)/(high24 − low24) (NaN nếu high24 = low24); 2. pos7d tương tự 168h;
3. dist_high24 = close/high24 − 1; 4. dist_low24 = close/low24 − 1;
5. atr_ratio = ATR24/ATR168, ATR = mean TR 1h, TR = max(high−low, |high−close₋₁|, |low−close₋₁|) (close₋₁ thiếu ⇒ high−low);
6. range7d = (high7d − low7d)/close;
7–9. rk_pos24, rk_dist_low24, rk_atr_ratio = rank-percentile cross-sectional trong giờ (trên sym có giá trị hữu hạn của store).
10. **noise** = N(0,1), `np.random.default_rng(20260905).standard_normal(n)` theo thứ tự dòng của bảng feature (đối chứng).
Ghép vào dòng (ts, sym) của feat_v2_x1 (ts = ts_h CLOSES v1); ledger ghép theo ts_h = floor(ts/1h)·1h như KEEP9. Kiểm: unit test chuỗi
tổng hợp, CAUSALITY 200 mẫu (cắt chuỗi tại t, tính lại == bảng), range (pos∈[0,1], dist_high ≤ 0, dist_low ≥ 0, rank∈(0,1]), phủ trên ledger.
Script `research/analysis/s1_geom_feat.py` (stage `keep9` → `geom` → `dsup`).

## 3. Cổng tái lập KEEP9 (FAIL ⇒ dừng)
`/home/ubuntu/featv2/` đã mất. Chạy lại builder có sẵn `research/pipeline/x1/x1_feat_v2_build.py` (X1_NAME=feat_v2_x1,
X1_T_END=1767225600000 = 2026-01-01, CLOSES_1H.bin v1 + funding + oi_percoin_full.bin), CHỈ đổi thư mục ra và lưu (ts, sym, KEEP9)
→ float32 (như `make_reduced.py`). So với `~/s1hpo/kaggle_ds/feat_v2_x1_keep9.parquet` (md5 1aa3b974): tập (ts,sym) trùng hết
và **byte-identical trên 1M dòng mẫu** (rng 20260905) — lệch 1 ô ⇒ dừng. Train dùng đúng file keep9 md5 1aa3b974 (= CTRL) + file GEOM.

## 4. Arm (k = 2) — Kaggle GPU, recipe 2x1 y hệt CTRL
Kernel `s1-geom-gpu` (pattern `s1_retrain_noise_kernel.py`): ledger cand_dev_x1_lite (g1lite), rel5, purge 72h, 16 fold quý 2022Q1–2025Q4,
XGBRanker rank:ndcg 300/4/0,05, subsample 0,8, colsample 0,8, mcw 50, topk 8, device cuda, xgboost 3.2.0. CHỈ đổi tập feature:
- **G** = KEEP9 + GEOM(9) (18 cột); **GN** = KEEP9 + GEOM(9) + noise (19 cột). Seed {42, 7} ⇒ G42, G7, GN42, GN7.
- Ghi importance (gain, total_gain, weight) mỗi fold. CTRL = K42 + S7 của S1_RETRAIN_NOISE (cùng recipe, cùng GPU).

## 5. Tầng model (OOS 16 fold, CHỈ báo cáo)
edge5 g1lite (top-5 − tick mean, %), rank-IC (−score) vs rel5, lift@16 = g1lite top-16 − hạng 17–50, xs-rank-corr & overlap top-16 vs ORIG
(pred_s1a2x1), importance gain trung bình 16 fold của 9 GEOM + noise vs KEEP9. CONFIRM theo `s1_hpo_bag_featgrp.py`: Δedge5 (G, GN vs CTRL,
trung bình seed theo tick) block-72h NREP 2000 seed 20260905, k=2 ⇒ inflate 1,18, SELECT = fold 0–7, CONFIRM = fold 8–15; noise_cal = GN − G.

## 6. Sim (Kaggle, kernel `tools/kaggle_sim.py` HEAD NOWRITE242) — đường S1_FIRSTHIT_RANK y hệt
MAP_PARITY 16/16 trước; map s1a2x1 của pred arm trên bins DEPLOY `~/predwf_map_s1a2_x1` (A1 của f0b9d8e6); 4 kernel G42, G7, GN42, GN7 + B0REF5 cùng đợt
(parity md5 ff3ce513, n 2517, eq 131908; FAIL ⇒ B0 = B0REF5). Thước MTM ngày cửa sổ 2022-01-01..2025-12-30, paired vs CTRL (gộp K42+S7)
và vs B0, block-10d NREP 2000 seed 20260905, inflate k=2 → 1,18; ΣPnL, n, SL%, win%, UW, ROI theo năm, overlap lệnh B0, frac gap = ΔCAGR/14,71 (R50).

## 7. Luật GO (chốt) — arm G, trung bình 2 seed
GO ⇔ **c1** ΔCAGR(G − CTRL) ≥ +3,3pp VÀ **c2** CI inflate ΔCalmar(G − CTRL) cận dưới > 0 VÀ **c3** ≥ 3/4 năm 2022–25 ROI(G) − ROI(CTRL) > 0
VÀ **c4** SL%(G) ≤ SL%(CTRL) VÀ **c5** importance gain của noise (GN, TB 2 seed) < min importance gain KEEP9 (GN).
GN là đối chứng: GN ≈ G ⇒ model không khớp nhiễu; noise gain cao (≥ min KEEP9) ⇒ cảnh báo harness, c5 FAIL. Không tune sau khi thấy kết quả.
Kỳ vọng khai trước: **P(GO) ≈ 15–20 %**. NO-GO ⇒ đóng hướng feature S1 trên DEV.

## 8. Ràng buộc
Không chạm 242/shadow; không sửa .java, không build; không Java sim trên Oracle; DEV ≤ 2025; không push bins/feature/printDone;
lock `oracle_heavy.lock` cho bước nặng; giữ ≥ 3 GB disk trống, dọn cache của vòng này (giữ OHLCV_1H_v2 + manifest).
