# PREREG — LABEL_FIRSTHIT: nhãn selector G015 = kết quả lệnh dưới FLAT3 (first-hit +7% / −10%, 168h)

**Ngày:** 2026-10-03 · **Nhánh:** `module` · chốt TRƯỚC khi train/chấm (chỉ đã chạy sinh nhãn + probe cấu trúc, chưa có số model nào).
**Nền:** RESULT_SELECTOR_ABLATION (33d8fc17): selector là lever (+24pp CAGR vs random), giá trị nằm ở tầng LỌC universe→16 (tránh SL/đuôi lỗ: SL% 14 vs 22, median ROI/leg bằng nhau). Nhãn G015 hiện tại `y = retEnd_4h > 0,015` (4h) không khớp cái sim thưởng/phạt (FLAT3: arm +7%, SL −10%, giữ tối đa 168h).
**Giả thuyết:** train G015 trên nhãn first-hit FLAT3 ⇒ top-16 của model tránh coin chạm −10% trước tốt hơn (proxy SL-rate thấp hơn) mà không mất return.

## 0. RỦI RO / CẤU TRÚC BIẾT TRƯỚC (đọc trước)
1. **[ĐO, probe cấu trúc, không phải kết quả] Bins sim = quantile-map s1a2x1**: ở tick có điểm S1 (pool ledger, gate mở), S1 phủ 97,5–100% coin và quyết định THỨ TỰ coin; G015 chỉ giữ PHÂN PHỐI p (→ gate G2). Tick có S1: 15% (fold 20220401), 9% (20240101), 78% (20251001) số tick. Lệnh B0 PREDICT vào ở tick có S1 ≈ 70% (căn tick floor 15'; 49% nếu lùi 1 tick). ⇒ Đổi nhãn G015 chỉ đổi danh tính coin ở ~30% lệnh + đổi hiệu chuẩn/gate cho tất cả. Hiệu ứng sim có thể **bị pha loãng** so với tầng model. Nhãn S1 (rel5 của g1lite 72h) **không đổi** ở vòng này (ngoài phạm vi; ghi làm hướng rẽ).
2. Một seed (42), một máy (Kaggle GPU). Sàn nhiễu retrain đo bằng CTRL vs gốc (xs-corr ~0,94 ở NETTHR).
3. Nhãn 168h chồng lấn mạnh giữa tick liền kề; CI block-72h (theo yêu cầu) **hẹp hơn thật** — báo kèm block-168h làm độ nhạy (không dùng cho cổng).
4. Aerospike `kline_1m_opt` thiếu phút rải rác (vd 2025-06 probe: 279/12 946 phút) và phủ ít symbol ở 2021 (85–127/tháng) ⇒ tập giao nhãn cũ×FH < nhãn cũ; báo tỉ lệ giao theo năm. Phút thiếu = không thể chạm (có thể sót hit).

## 1. Nhãn FH (code: `research/analysis/label_firsthit_build.py`)
- Tick `ts` = lưới 15' UTC (= `tEpochMs` của ds_label15m), toàn universe Aerospike (map `symbol_map.csv`), 2021-01..2025-12.
- **Entry** P = close nến 1m **mở tại ts** (nến kế tick, đóng ts+1').
- **Đường đi**: nến 1m mở tại ts+1' … ts+10080' (168h kể từ close entry), dùng **high/low 1m**.
- **arm** = high ≥ 1,07·P ; **SL** = low ≤ 0,90·P. First-hit theo phút. `y = 1` nếu arm chạm trước; `y = 0` nếu SL trước.
- **Tie** (cùng 1 nến chạm cả hai) ⇒ SL (bi quan), y = 0, `hit = 3` (đếm báo cáo).
- **Không chạm cả hai trong 168h** ⇒ `y = 1[ret168 > 0]`, ret168 = close hợp lệ cuối trong cửa sổ / P − 1.
- Nến **vol ≤ 0 hoặc giá ≤ 0 = không hợp lệ** (phút ma sau delist, DATA_AUDIT 1003) ⇒ bỏ qua (không chạm, không làm close cuối).
- NaN (loại): entry không hợp lệ; không có nến hợp lệ nào sau entry; cửa sổ vượt 2025-12-31 23:59 UTC (KHÔNG đọc 2026).
- Kiểm: mỗi tháng 400 dòng ngẫu nhiên tính lại bằng vòng lặp phút (brute) phải khớp 100% (y, hit, khit). Cột phụ: `hit` (0 none/1 arm/2 SL/3 tie), `khit`, `ret168`.
- **Proxy SL-rate** của 1 dòng = 1[hit ∈ {2,3}].

## 2. Train (Kaggle GPU, `research/analysis/label_firsthit_train.py` = bản sao `g015_net_train.py` md5 a32bb0f7…, chỉ đổi 3 thứ)
- Featureset 45 cột y hệt (Tool1 40 + OI 5 = `fs_v9_31`), XGBClassifier n_est 400, depth 5, lr 0,05, subsample 0,8, colsample 0,8, mcw 20, spw = (1−pos)/pos, hist, device cuda, **seed 42**. 16 fold 20220101..20251001 (OOS 3 tháng/fold). KHÔNG fold 20251231/20260101/20260401.
- **Purge = 672 bước × 15' = 168h cho CẢ HAI arm** (train ts < cutoff − 168h ⇒ cửa sổ nhãn FH kết thúc trước cutoff).
- **Tập dòng = GIAO** (feature Tool1 có) ∧ (nhãn cũ hợp lệ: nBars_4h ≥ 16, retEnd_4h notna) ∧ (nhãn FH hợp lệ). File FH đưa lên Kaggle chỉ gồm ts < 20251001 − 168h (không có nhãn OOS trong kernel).
- **Arm FH**: y = y_FH. **Arm CTRL**: y = 1[retEnd_4h > 0,015] (nhãn cũ), cùng dòng, cùng purge, cùng seed ⇒ sàn nhiễu + tách hiệu ứng nhãn.
- Bins ra (26B/rec, p0 = P(y=1)) cho 16 fold; sau đó map s1a2x1 (`x1_build_map.py s1a2x1`, `X1_G015_DIR` = bins arm, cùng `pred_s1a2x1.parquet`) ⇒ bins sim của arm.
- Tham chiếu: **ORIG** = `predwf_G015x26` raw (bản tái lập `~/f0_repro/g015x26_regen`, 1 ULP) ; **B0** = `~/predwf_map_s1a2_x1` (bins deploy đã map).

## 3. Thước tầng model (script `research/analysis/label_firsthit_score.py`, OOS 16 fold, mọi tick 15', MIN_N 30 coin/tick)
Nhãn đo trên OOS: y_FH, hit, ret168 (file nhãn đầy đủ, chỉ dùng ĐỂ CHẤM) và y_old = 1[retEnd_4h > 0,015] (ds_label15m). Tick có cửa sổ 168h vượt 2025-12-31 bị loại khỏi thước FH.
- **(i) Ma trận rank-IC 2×2** (Spearman per-tick, trung bình theo fold rồi toàn kỳ): score {FH, CTRL} × nhãn {y_FH, y_old}. Kèm ORIG làm sàn.
- **(ii) Top-16/tick** theo p giảm dần (= thứ tự sim dùng), RAW bins của model: tỉ lệ y_FH = 1, mean ret168, **proxy SL-rate**; so FH vs CTRL vs ORIG; theo năm 2022–2025. Bản MAPPED (FH-map, CTRL-map, B0) báo kèm làm thước "gần sim" (không gác cổng — xem §0.1).
- **(iii) xs-rank-corr** per-tick: FH vs ORIG, CTRL vs ORIG (sàn nhiễu), FH vs CTRL.
- **CI**: chênh paired theo tick (FH − CTRL), bootstrap khối 72h (288 tick) trên lưới chung, **NREP 2000, seed 20260905, inflate k = 1** (1 phép thử chính). Độ nhạy: block-168h (chỉ báo).

### Cổng GO-model (khai trước)
**GO-model ⇔** (a) Δ proxy-SL-rate top-16 RAW (FH − CTRL) < 0 với CI95 block-72h **hoàn toàn < 0**, **VÀ** (b) Δ mean ret168 top-16 RAW **không kém**: CI95 block-72h **không nằm hoàn toàn < 0**.
Không GO-model ⇒ DỪNG, không sim. Không tune/đổi nhãn/ngưỡng sau khi thấy số.

## 4. Sim (chỉ khi GO-model) — Kaggle CPU, kernel `tools/kaggle_sim.py` HEAD NOWRITE242, KHÔNG Java trên Oracle
- 2 kernel: **FH** (bins FH-map) và **CTRL** (bins CTRL-map); gate/sizing/exit/profile/jar giữ nguyên B0 (jar 7368be46, profile r4_kg0_k16_f015_g155 + G2 + FLAT3), funding.bin dựng lại bằng `s3_funding.py` như đường SELECTOR_ABLATION; 2 fold 2021H2 = bins B0 ⇒ **cửa sổ so = 2022-01-01..2025-12-30**.
- Parity: mốc B0 ảnh Kaggle hiện tại md5 **ff3ce513** (float32 y hệt 650c386f) — B0 tham chiếu = `selab-p0` (n 2517, eq 131 908). CTRL ≈ B0 trong nhiễu retrain (báo, không gác). Tham chiếu ablation: mean R (R42/R7/R13) của SELECTOR_ABLATION.
- Thước: Calmar_MTM (equity MTM ngày, CAGR/|maxDD|), CAGR, maxDD, SL% (STOP_LOSS_DONE / n), ROI năm.
- **GO-sim ⇔** Calmar_MTM(FH) − Calmar_MTM(CTRL) > 0 với CI95 MTM **paired block-10d** (NREP 2000, seed 20260905, k = 1) hoàn toàn > 0 **VÀ** ROI năm FH > CTRL ở **≥ 3/4 năm** 2022–2025 **VÀ** SL% FH < CTRL.

## 5. Luật
DEV ≤ 2025; KHÔNG fold 2026; KHÔNG 242/shadow; KHÔNG sửa .java/build; train chỉ Kaggle GPU; Python logging; không push bins/nhãn/printDone. Mọi lệch khỏi pre-reg ghi AMENDMENT trước khi xem số liên quan.
