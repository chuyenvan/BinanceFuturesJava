# PREREG S1_K24 — cải tiến selector S1 trong khung vận hành K24 (chốt TRƯỚC mọi tính toán)

Ngày: 2026-10-04 (GMT+7). Agent thực thi theo brief MASTER (thiết kế/luật do MASTER chốt; agent KHÔNG đổi arm/luật sau khi thấy số).
Ràng buộc: 0 sửa `.java`/build · 0 Java sim trên Oracle (sim chỉ Kaggle, kernel `tools/kaggle_sim.py` HEAD md5 `8b60b00a…` NOWRITE242, ≤ 2 kernel song song) · 0 chạm 242/shadow_c3 · DEV ≤ 2025-12-31, 2026 niêm phong · train S1 trên Oracle CPU (lock `~/claude_master/1002/oracle_heavy.lock`, RAM ≤ 8G).

## 0. Khung (owner, KHÔNG phải luật c1)
- **K24 = khung vận hành mục tiêu** theo **quyết định owner 2026-10-04** vì mục tiêu n 500→700/năm (RESULT_N700: A1 B0@K24 n ≈ 732/năm, ΔCAGR +3,08, ΔPnL +12,9k CI raw [+2,0k; +24,0k], chỉ trượt c1 inflate). Đây là quyết định owner theo mục tiêu n, **không** qua luật c1. Đề xuất amendment A.6 ghi cùng commit vào `docs/runbooks/RISK_APPETITE.md`.
- Hệ quả: mọi so sánh selector từ vòng này dùng nền **CTRL4@K24** (TB 4 seed KEEP9), không dùng B0@K16.

## 1. Giả thuyết
- **H1:** objective `ndcg@8` lệch với K24 — XGBRanker `lambdarank_pair_method="topk"`, `lambdarank_num_pair_per_sample=8` chỉ học phân biệt top-8; dải hạng 17–24 gần như không được huấn luyện. Đổi sang **ndcg@24** (`num_pair_per_sample=24`) + relevance mịn **rel10** (decile trong tick) sẽ tăng PnL ở dải mới.
- **H2:** lợi ích GEOM ở K24 (A3−A1 = +0,54 pp CAGR vs B0@K24, 1 seed) nhỏ hơn ở K16 (+2,3) — cần 2 seed để biết là pha loãng hay nhiễu.

## 2. Arm CỐ ĐỊNH (k = 3 biến thể GO: ARM-A/B/C; inflate half-width × √(2 ln 3) = **1,4823**)
| arm | định nghĩa | run Kaggle (tag) | bins |
|---|---|---|---|
| **CTRL4@K24** (nền) | 4 seed KEEP9 recipe s1a2x1 (K42/S7/S13/S21, train Kaggle GPU vòng S1_RETRAIN_NOISE), chỉ sim lại với TOPK=24. Nền = **TB 4 seed** | `s1k24-k42`, `s1k24-s7`, `s1k24-s13`, `s1k24-s21` | dataset `s1rn-bins-{k42,s7,s13,s21}`; sha256_concat(map16+moc21) K42 `fad7a45a…`, S7 `44fa768f…`, S13 `c8dc4ef6…`, S21 `db80c79a…` |
| **ARM-A GEOM@K24** | KEEP9+GEOM9 recipe vòng S1_FEAT_GEOM; arm = TB 2 seed: g42 = `n700-a3` (có sẵn) + g7 (mới) | `n700-a3` + `s1k24-g7` | G42 `6171f2cc…` (geom-bins-g42), G7 `a687bf2b…` (geom-bins-g7) |
| **ARM-B OBJ24** | KEEP9, ndcg@24 + rel10, seed 42/7, train Oracle CPU | `s1k24-b42`, `s1k24-b7` | dataset mới `s1k24-bins-{b42,b7}` (sha ghi ở G1, trước sim) |
| **ARM-C OBJ24+GEOM** | KEEP9+GEOM9 (18 cột), ndcg@24 + rel10, seed 42/7, train Oracle CPU | `s1k24-c42`, `s1k24-c7` | dataset mới `s1k24-bins-{c42,c7}` |
| tham chiếu (không arm) | B0@K24 = `n700-a1` (md5 `d9abf35f`); GEOM g42@K24 = `n700-a3` (md5 `69c55e70`) | có sẵn | deploy `407e2aba` / G42 |
- Tổng **9 kernel mới** (4 CTRL + 1 g7 + 2 B + 2 C). KHÔNG chạy B0REF (A1 đã tái lập ảnh, chain ff3ce513). KHÔNG thêm arm; G2 funding/OFI để vòng S1_V2.
- Cấu hình sim mọi run: profile `r4_kg0_k16_f015_g155` + B0OV (SIM_GATE_ROLLING_MODE=ratio, DAYS=90, PCT=0.999950829, TS_GIVEBACK_RATIO=1.0, SIM_TS_MAX_GAP=0.03, SIM_TS_MAX_GAP_WEAK=0.03) + **`SELECTOR_RANK_TOPK=24`** (khoá giống n700 A1/A3); template `label_firsthit_sim.template()` (đường sim s1rn/geom/n700-A3), jar `sim-jar-gdv2` sha `7368be46…`, bundle `sim-x1-2021-bundle` + wfo-ticker, moc21 `s3-moc-2021bins`, sim_end_date 20251231, xmx 22g, `code_sha` = commit pre-reg này.

## 3. Train ARM-B/C (Oracle CPU aarch64, xgboost 3.2.0) — script `research/analysis/s1k24_train.py`
- Recipe = `research/pipeline/x1/x1_s1_rank.py 2x1` nguyên văn (ledger `~/ledger/cand_dev_x1.parquet` lọc g1lite notna; rel = g1lite − median tick; rk = rank pct method first; join feature theo giờ; 16 fold quý 20220101…20251001, train `ts < cut − 72h`, OOS 3 tháng; XGBRanker rank:ndcg, n_estimators 300, max_depth 4, lr 0,05, subsample 0,8, colsample 0,8, min_child_weight 50, n_jobs 4, hist, CPU; score = −pred). Feature KEEP9 từ `~/s1hpo/kaggle_ds/feat_v2_x1_keep9.parquet` (md5 `1aa3b974`, = dataset s1-featv2-x1-20260919; cổng KEEP9 vòng GEOM 0 ô lệch bit); GEOM9 từ `geom_x1.parquet` md5 `6903e178`.
- CHỈ đổi qua CLI: `--topk` (num_pair_per_sample, mặc định 8), `--rel` (5 = quintile `min(floor(rk·5),4)`, 10 = decile `min(floor(rk·10),9)`), `--seed` (mặc định 42), `--feats` (keep9 | keep9geom). Bỏ phần shuffle/IC chẩn đoán (không ảnh hưởng model chính).
- ARM-B: `--topk 24 --rel 10 --feats keep9 --seed {42,7}`; ARM-C: `--topk 24 --rel 10 --feats keep9geom --seed {42,7}`.
- Rủi ro khai trước: CTRL4/GEOM train Kaggle GPU, ARM-B/C train Oracle CPU ⇒ lệch môi trường (đo ở S1_RETRAIN_NOISE: GPU↔CPU ≈ cỡ đổi seed, xs-corr ~0,98). Đối chứng cùng môi trường (CHỈ BÁO CÁO): **ARM-B42 − A1** (A1 = B0@K24 = model CPU seed 42 KEEP9 ndcg@8 rel5 — chính đường mặc định G0).

## 4. Cổng trước sim (trượt G0/G1 ⇒ DỪNG, báo MASTER)
- **G0 (đường mặc định không đổi):** `s1k24_train.py` cấu hình mặc định (topk 8, rel 5, seed 42, keep9) ⇒ pred phải **trùng giá trị tuyệt đối** `~/ledger/pred_s1a2x1.parquet` (sha256 file `2618fe1a…`): cùng số dòng, cùng thứ tự, ts/sym/score bằng bit. Ghi md5/sha file mới (byte-identical file chỉ là thông tin). Nếu G0 FAIL ở mức giá trị nhưng xs-corr ≥ 0,999 và top-16 overlap ≥ 0,99 ⇒ vẫn DỪNG báo MASTER (không tự nới).
- **G1 MAP_PARITY:** (a) `x1_build_map.py s1a2x1` trên `pred_s1a2x1` với `X1_G015_DIR` = bins deploy `~/predwf_map_s1a2_x1` ⇒ md5 16/16 == deploy; (b) tái sinh map G42 từ `geom/kout/pred_G42.parquet` ⇒ sha256_concat(map16+moc21) == `6171f2cc…` (chứng minh đường map tái lập); (c) mỗi bins mới B/C: 16 file, mỗi file cùng số dòng + (ts,sym) cùng thứ tự với deploy, multiset p0 theo tick == deploy, tỷ lệ "có score" ≈ 0,77 (± 0,01 so deploy-check); sha256_concat ghi vào `~/claude_master/1004/s1k24/sim_sha256.json` và JSON kết quả trước khi submit.
- **G2 (C0 offline, KHÔNG chặn sim, chỉ ghi):** định nghĩa khai trước — trên OOS 16 fold, mỗi tick ledger (ts gate-open) có ≥ 25 ứng viên: xếp hạng theo score tăng (method first); **edge@24 = mean(g1lite của hạng 1–24) − mean(g1lite cả tick)**; trung bình đều theo tick; báo thêm edge@8, edge@16, edge **dải 17–24** (mean g1lite hạng 17–24 − mean tick) và theo năm. **Δedge@24** = arm − CTRL cùng seed (B42−K42, B7−S7, C42−K42, C7−S7; thêm C−G cùng seed chỉ báo cáo); G2 ĐẠT cho arm nếu TB 2 seed Δedge@24 > 0. CI block-72h NREP 2000 seed 20260905 chỉ báo cáo.
- Parity từng run sim (trước khi chấm): jar sha == `7368be46…`, symbol_mapper ≥ 800, `sel.bins_ok` True và bins_sha256 == sha khai, `prof_run.properties` có `SELECTOR_RANK_TOPK=24`, n/eq/md5 printDone ghi lại; run nào trượt ⇒ VOID run đó (không thay thế bằng run khác).

## 5. Thước (cố định, theo §9 A.3/A.4/A.5)
- **Chính:** equity MTM ngày (b+unP, `reset_rule_score.load_daily`), cửa sổ 2022-01-01…2025-12-30 (rebase 2021-12-31); bootstrap **ghép cặp block-10d, NREP 2000, seed 20260905** (`selector_ablation_driver.daily_boot`, cùng chỉ số khối cho mọi run). Arm/nền nhiều seed: Δmetric = TB(metric các seed arm) − TB(metric 4 seed CTRL4), cùng replicate (như meanS ở S1_RETRAIN_NOISE).
- Báo: **ΔCAGR22**, **ΔPnL** (ΣPnL thực hiện theo ngày đóng, TB seed, cùng khối bootstrap — như `n700_driver.pnl_boot`), CI raw + **inflate 1,4823**; theo năm 2022/23/24/25 (ROI equity compound + ΣPnL + n + maxDD MTM năm) và theo quý (ΣPnL đóng lệnh, TB seed).
- maxDD/UW = MTM phút (`R.run_mtm`, legacy cost). Calmar22 = CAGR22 / |maxDD MTM phút 2022+| từng run; arm = TB seed.
- win%/SL%/ROI-lệnh, n/năm (lệnh đóng 2022–25 / 4), overlap tập lệnh vs CTRL: chỉ báo cáo.

## 6. Luật GO cho từng arm (vs CTRL4@K24; tất cả phải đạt C1–C4)
- **C1:** ΔCAGR22 > 0 và cận dưới CI-inflate (k=3) > 0.
- **C2:** maxDD MTM phút ≥ −40 % (toàn kỳ và 2022+) ở **mọi** seed của arm.
- **C3:** Calmar22(arm) ≥ 0,90 × Calmar22(CTRL4@K24).
- **C4:** ≥ 3/4 năm (2022–2025) ΔROI năm (TB seed arm − TB CTRL4) ≥ 0.
- **C5 (báo cáo, không chặn):** ΔROI gộp 2022–24 (∏(1+ROI năm) arm − CTRL4) ≥ 0 — kiểm lợi ích không chỉ đến từ 2025.
- Phụ, chỉ báo cáo: ARM-B42 − A1 (cùng môi trường), ARM-A − A1, A1 − CTRL4 (B0@K24 vs nền retrain), từng seed vs CTRL4.
- KHÔNG tune sau khi thấy số; mọi phân tích ngoài mục này = "chỉ báo cáo". Run VOID ⇒ arm thiếu seed được báo nhưng không GO.

## 7. Kỳ vọng khai trước
| arm | ΔCAGR22 kỳ vọng | ghi chú |
|---|---|---|
| ARM-A | **+1,0 pp** | GEOM pha loãng ở K24 |
| ARM-B | **+1,5 pp** | suy đoán, chưa có bằng chứng |
| ARM-C | **+2,5 pp** | |
MDE80 ước ~3,5–4 pp (CI raw nửa-độ-rộng ~2,5 pp × 1,48) ⇒ P(GO) mỗi arm ~25–35 %. Kết cục khả dĩ nhất: **dương dưới ngưỡng**.

## 8. STEP 0 — chẩn đoán dải hạng (trước sim, chỉ dữ liệu có sẵn; diễn giải, KHÔNG đổi arm)
- Run: `n700-a1` (B0@K24), `n700-a3` (GEOM g42@K24), `n700-b0ref` (B0@K16, value-identical selab-p0/de-p1 ff3ce513), `geom-g42` (G42@K16).
- Join hạng S1 tại entry (cách R50 `selector_ablation_topm.rank_in_ts`: score = float32(1) − p0 tăng, hoà theo thứ tự record): lệnh (sym+USDT → symId qua `claudedata/oi/symbol_map.csv`, start GMT+7 → UTC ms) ↔ tick bins 15' gần nhất ≤ entry có sym; kiểm join bằng |(1−p0) − symbolPred| < 1e-6. Bins: deploy (moc21 + `~/predwf_map_s1a2_x1`) cho B0; G42 tái sinh (G1-b) cho GEOM.
- Bảng: PnL/lệnh (USDT), ΣPnL, ROI/lệnh %, win%, n theo dải hạng 1–8 / 9–16 / 17–24 / >24, theo năm, theo level; tập lệnh "mới ở K24" (khóa sym|start|level#cumcount có ở A1 không có ở B0@K16): ΣPnL, theo năm, phân phối hạng; A3 vs A1 từng dải. Xuất `docs/audit/RANKBAND_K24_20261004.md` + `.json`.

## 9. Artifact dự kiến
`research/analysis/s1k24_train.py` (train + G0 + G2), `research/analysis/s1k24_driver.py` (step0/map/upload/submit/parity/score), `docs/result/RESULT_S1_K24.md` + `docs/result/s1k24.json`. Oracle: `~/claude_master/1004/s1k24/`. Không push bins/pred/printDone.
