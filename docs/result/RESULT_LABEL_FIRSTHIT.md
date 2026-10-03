# RESULT — LABEL_FIRSTHIT: nhãn G015 = first-hit FLAT3 (+7% trước −10%, 168h)

**Pre-reg:** `docs/prereg/PREREG_LABEL_FIRSTHIT.md` (commit `a1191ea3`, md5 `6a1458ae…`, chốt TRƯỚC khi train/chấm). DEV ≤ 2025, 16 fold 20220101..20251001, seed 42, purge 168h cả hai arm. KHÔNG 242/shadow, KHÔNG fold 2026, KHÔNG Java trên Oracle.
**Code:** `research/analysis/label_firsthit_build.py` (nhãn) · `label_firsthit_train.py` (trainer = bản sao g015_net_train md5 a32bb0f7 + 3 đổi) · `label_firsthit_kernel.py` (+ `_kernel_tpl.py`) · `label_firsthit_score.py` (chấm model) · `label_firsthit_report.py` · `label_firsthit_sim.py` (sim). Thô: `docs/result/label_firsthit.json`.
**Kernel:** `chuyendinh/label-firsthit-g015-gpu` (Kaggle GPU, FH 44,1' + CTRL 43,1', xgboost 3.4.1) · sim `chuyendinh/sim-fhsim-fh`, `sim-fhsim-ctrl`.

---

## 0. RỦI RO / ĐỌC TRƯỚC
1. **[ĐO] GO-model ĐẠT theo chữ, nhưng cơ chế KHÔNG phải "model học tránh SL".** Top-16 RAW của FH có proxy-SL **0,3636 = đúng bằng trung bình universe (ALL 0,3637)**. Δ −4,6pp so với CTRL đến từ việc **CTRL/ORIG nghiêng vol** (top-16 SL 0,410, cao hơn ngẫu nhiên +4,6pp) còn FH **mất nghiêng vol** (y_old top-16 0,193 ≈ ALL 0,176). IC của FH với CHÍNH nhãn FH = **+0,016**, thấp hơn CTRL (+0,020) — model FH **không** dự báo first-hit theo lát cắt tốt hơn model cũ.
2. **[ĐO] Proxy tầng model mâu thuẫn bằng chứng sim đã có**: SELECTOR_ABLATION — random (R) có SL% sim **22% vs B0 14%**, trong khi ở tầng model "ALL" (≈ random) có proxy-SL **thấp hơn** ORIG. ⇒ proxy-SL mọi tick ≠ SL trong sim (sim chỉ vào ở tick gate mở, có TP/trailing/DCA, S1 quyết thứ tự ~70% lệnh). Kỳ vọng khai trước sim: FH có thể **xấu** đi vì gần-random.
3. FH xếp hạng rất khác gốc: xs-rank-corr FH~ORIG **0,22** (sàn nhiễu retrain CTRL~ORIG **0,929**, khớp NETTHR 0,94). Bản map: FHm~B0 0,32.
4. CI block-72h hẹp hơn thật (nhãn 168h chồng lấn); block-168h cho cùng kết luận (dSL CI [−6,17; −3,11]pp). 2025: dSL không ngoài 0 (−1,8pp, CI [−4,8; +1,1]).
5. Một seed (42), một GPU. Tập train = GIAO nhãn cũ × FH (34,72M / 39,61M dòng nhãn cũ có feature; FH thiếu chủ yếu 2021 do Aerospike chỉ có 85–127 symbol/tháng 2021 và phút thiếu rải rác).

## 1. Cổng hợp lệ
| cổng | kết quả |
|---|---|
| Pre-reg trước số | `a1191ea3` (chỉ đã chạy sinh nhãn + probe cấu trúc map/B0 trước commit) ✓ |
| Nhãn brute-check | 60/60 tháng × 400 dòng ngẫu nhiên: vectorized == vòng lặp phút (y, hit, khit) **0 lệch** ✓ |
| Không đọc 2026 | stream ≤ 2025-12-31 23:59 UTC; tick có cửa sổ 168h vượt ⇒ NaN; file train ts_max 2025-09-23 16:45 UTC (< cutoff 20251001 − 168h) ✓ |
| Trainer | md5 `7bf65f75…` nhúng base64 + assert trong kernel; sha nhãn FH `79003f67…` assert ✓; chỉ link feature/label start < 20260101 ✓ |
| Purge | 672 bước (168h) cả FH và CTRL ✓; CTRL fold 20240101 n_train 14 745 004 (deploy 72h-purge 14 834 006 — khác do purge 168h + giao) |
| Map s1a2x1 | dựng lại map từ ORIG (`g015x26_regen`) bằng cùng lệnh ⇒ md5 16/16 == `~/f0_repro/predwf_map_s1a2_x1` **MAP_PARITY_PASS** ✓ |
| Bins | 16/16 fold mỗi arm, cùng tập (ts,sym) với ORIG/B0 (join inner không rơi dòng) ✓ |

## 2. Feasibility (bước 1)
- Tập train G015 = **toàn universe lưới 15'** (Tool1 ∩ ds_label15m; fold 20240101 ~14,8M dòng), không phải cand_dev_x1. `.pb` chỉ có maxFav/maxAdv/retEnd theo horizon ⇒ không có thứ tự chạm ⇒ phải stream 1m.
- Sinh nhãn: stream Aerospike `kline_1m_opt` theo tháng UTC + 10 080' fwd, sparse-table range-max + binary lifting (first-hit O(log)), 3 proc, **36 phút** cho 60 tháng 2021-01..2025-12 ⇒ **giữ tick 15'** (không cần giảm). Lock Oracle `oracle_heavy.lock` giữ suốt job.
- **[ĐO] cấu trúc bins sim (probe trước pre-reg):** map s1a2x1 ⇒ ở tick có S1 (9–78% tick theo fold), S1 phủ 97,5–100% coin và quyết thứ tự; ~70% lệnh B0 PREDICT vào ở tick có S1. Nhãn G015 chỉ đổi danh tính coin ở phần còn lại + hiệu chuẩn p (gate G2).

## 3. Nhãn FH sinh được (39 593 151 dòng, toàn universe Aerospike)
| năm | n | y=1 | proxy SL (SL/tie trước) | tie | không chạm 168h |
|---|---:|---:|---:|---:|---:|
| 2021 | 3 842 542 | 0,596 | 0,386 | 7e-6 | 0,028 |
| 2022 | 4 797 280 | 0,512 | 0,394 | 6e-7 | 0,146 |
| 2023 | 6 484 468 | 0,566 | 0,271 | 0 | 0,247 |
| 2024 | 9 554 752 | 0,560 | 0,373 | 1e-6 | 0,109 |
| 2025 | 14 914 109 | 0,524 | 0,405 | 9e-5 | 0,107 |
Train (giao): 34 717 220 dòng ở fold cuối; base y_FH 0,554 vs y_old 0,189. pos FH theo fold 0,541–0,598; CTRL 0,184–0,271.

## 4. Tầng model (OOS 16 fold, 139 599 tick, MIN_N 30)
### (i) Ma trận rank-IC (mean per-tick, mean 16 fold)
| score \ nhãn | y_FH | y_old (retEnd_4h>0,015) |
|---|---:|---:|
| **FH** | **+0,0161** | +0,0280 |
| **CTRL** | +0,0195 | **+0,1378** |
| ORIG (deploy raw) | +0,0213 | +0,1364 |
| FHm / CTRLm / B0 (map) | +0,0194 / +0,0192 / +0,0208 | +0,0409 / +0,1375 / +0,1362 |
IC FH|y_FH theo fold dao động −0,011..+0,061, 14/16 dương; CTRL|y_FH −0,058..+0,119, 9/16 dương. **Không arm nào có IC đáng kể với y_FH** — nhãn first-hit 168h gần như không dự báo được theo lát cắt bằng 45 feature này.

### (iii) xs-rank-corr per-tick (mean)
FH~ORIG **0,220** · CTRL~ORIG **0,929** (sàn nhiễu) · FH~CTRL 0,223 · FHm~B0 0,321 · CTRLm~B0 0,943.

### (ii) Top-16/tick theo p (RAW) — proxy SL / mean ret168 / tỉ lệ y_FH
| năm | FH SL | CTRL SL | ORIG SL | ALL SL | FH ret | CTRL ret | ORIG ret | ALL ret | FH yFH | CTRL yFH | ALL yFH |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 0,399 | 0,428 | 0,425 | 0,397 | −2,04% | −2,49% | −2,52% | −2,24% | 0,510 | 0,525 | 0,513 |
| 2023 | 0,283 | 0,370 | 0,368 | 0,275 | +2,15% | +1,56% | +1,60% | +1,66% | 0,589 | 0,582 | 0,566 |
| 2024 | 0,368 | 0,419 | 0,417 | 0,376 | +1,15% | +1,22% | +1,29% | +1,13% | 0,563 | 0,569 | 0,558 |
| 2025 | 0,405 | 0,424 | 0,423 | 0,408 | +0,21% | +0,68% | +0,81% | −1,76% | 0,549 | 0,573 | 0,524 |
| **toàn kỳ** | **0,364** | **0,410** | 0,408 | 0,364 | +0,37% | +0,24% | +0,29% | −0,30% | 0,553 | 0,562 | 0,540 |
Bản MAP (gần sim): FHm SL 0,366 / ret +0,54% · CTRLm 0,410 / +0,19% · B0 0,408 / +0,22%.

### CI paired theo tick (FH − CTRL, RAW; NREP 2000, seed 20260905, k=1)
| thước | Δ | CI95 block-72h | CI95 block-168h | theo năm 2022 / 2023 / 2024 / 2025 (b72) |
|---|---:|---|---|---|
| proxy SL | **−4,63pp** | **[−5,76; −3,38]** | [−6,17; −3,11] | −2,9 [−4,7;−1,1] / −8,6 [−10,6;−6,6] / −5,1 [−7,8;−2,3] / −1,8 [−4,8;+1,1] |
| ret168 | +0,13pp | [−0,68; +0,86] | [−0,81; +0,92] | +0,45 / +0,59 / −0,07 / −0,47 (đều chứa 0) |
| y_FH | −0,95pp | [−2,10; +0,13] | [−2,41; +0,55] | |
Sàn nhiễu CTRL − ORIG: SL +0,17pp [+0,07; +0,28], ret −0,05pp — rất nhỏ so với Δ FH. Bản MAP FHm − CTRLm: SL −4,40pp [−5,51; −3,26], ret +0,35pp [−0,17; +0,86].

### Cổng GO-model (pre-reg §3)
(a) ΔSL CI95 b72 hoàn toàn < 0: **CÓ** · (b) Δret168 CI không hoàn toàn < 0: **CÓ** ⇒ **GO-model = ĐẠT (theo chữ)** ⇒ chạy sim theo pre-reg. Cảnh báo §0.1–0.2 khai TRƯỚC khi xem số sim: FH ≈ "bỏ nghiêng vol", không phải "học tránh SL"; kỳ vọng sim xấu đi.

## 5. SIM (Kaggle CPU, `tools/kaggle_sim.py` HEAD NOWRITE242 md5 8b60b00a, jar 7368be46, profile r4_kg0_k16_f015_g155 + G2 + FLAT3)
Cổng: jar ✓, mapper 863 ✓, bins sha trong kernel == Oracle (FH `65c99d1d…`, CTRL `bf830db2…`; B0 dựng lại `407e2aba` == P0 SELECTOR_ABLATION ✓), funding.bin dựng lại (FH `12b12668…`, CTRL `8145923c…`). B0 = `selab-p0` (md5 **ff3ce513**, n 2517, eq 131 908; ảnh Kaggle hôm nay xác nhận lại bằng B0REF2 của vòng R50 cùng md5). Prefix 2021H2 dùng chung bins B0 ⇒ equity 2021-12-31 = 41 486 cả 3 arm (so sạch).

### Bảng chính — cửa sổ 2022-01-01..2025-12-30 (equity ngày từ 2021-12-31; lệnh vào ≥ 2022)
| arm | n | ΣPnL | equity cuối | CAGR % | maxDD MTM ngày % | **Calmar_MTM ngày** | win % | SL % | overlap lệnh B0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **FH** | 2 045 | 43 527 | 85 013 | 19,66 | −9,79 | **2,01** | 81,5 | **19,1** | 42,4% |
| **CTRL** | 2 196 | 65 429 | 106 915 | 26,72 | −17,66 | **1,51** | 84,2 | **16,0** | 68,1% |
| B0 (deploy) | 2 083 | 90 422 | 131 908 | 33,56 | −10,02 | 3,35 | 86,3 | 13,8 | 100% |
Toàn kỳ (MTM phút, như SELECTOR_ABLATION): FH CAGR 21,8 / DD −20,0 / Calmar 1,09 / UW 248 ngày · CTRL 28,2 / −23,7 / 1,19 / 286 · B0 34,3 / −17,7 / 1,94 / 87. Tham chiếu random R16 (SELECTOR_ABLATION): Calmar 0,41, CAGR ~10, SL 22%.

### Chênh paired (block-10d, NREP 2000, seed 20260905, k=1), cửa sổ 2022+
| cặp | ΔCalmar_MTM ngày | CI95 | ΔCAGR pp | CI95 |
|---|---:|---|---:|---|
| **FH − CTRL** | **+0,50** | **[−5,47; +2,17]** | −7,06 | [−19,53; +6,63] |
| FH − B0 | −1,34 | [−8,28; +0,68] | −13,90 | [−25,30; −2,32] |
| **CTRL − B0 (sàn retrain)** | **−1,84** | **[−4,39; −0,39]** | **−6,84** | **[−13,41; −1,14]** |

### ROI năm (equity MTM ngày, %)
| năm | FH | CTRL | B0 | FH − CTRL |
|---|---:|---:|---:|---:|
| 2022 | 22,0 | 1,0 | 11,1 | **+21,0** |
| 2023 | 21,0 | 46,8 | 54,1 | −25,8 |
| 2024 | 18,2 | 40,3 | 43,4 | −22,2 |
| 2025 | 17,5 | 23,9 | 29,5 | −6,4 |

### Cổng GO-sim (pre-reg §4)
ΔCalmar CI > 0: **KHÔNG** (chứa 0) · ≥3/4 năm FH > CTRL: **KHÔNG (1/4)** · SL% FH < CTRL: **KHÔNG (19,1 vs 16,0)** ⇒ **GO-sim = FAIL.**

## 6. VERDICT
**LABEL_FIRSTHIT: KHÔNG GO.** GO-model đạt theo chữ (ΔSL top-16 −4,6pp ngoài CI, ret không kém) nhưng **không chuyển sang sim**: SL% sim của FH **cao hơn** CTRL (+3,1pp) và B0 (+5,3pp), CAGR thấp hơn CTRL 7pp (CI chứa 0) và thấp hơn B0 13,9pp (CI ngoài 0), thua CTRL 3/4 năm. Calmar ngày FH cao hơn CTRL chỉ nhờ maxDD nhỏ (năm 2022 gấu: FH +22% vs CTRL +1%) — không phải lever; CI rộng chứa 0.
**Cơ chế (đọc từ số, mức suy luận):** nhãn first-hit 168h gần như không dự báo được theo lát cắt (IC ~0,02 cho cả hai model) ⇒ model FH bỏ nghiêng vol của G015 cũ mà không thay bằng tín hiệu chọn coin nào ⇒ gần-random ở ~30% lệnh mà G015 quyết danh tính (overlap B0 chỉ 42%) + đổi phân phối p cho gate G2. Proxy-SL tầng model (mọi tick, hold 168h, không TP/trailing) **ngược dấu** với SL% sim — như đã cảnh báo trước sim (§0.2).

## 7. CÁI GÌ CHẶN / RỦI RO CHO VÒNG SAU
1. **[ĐO] Sàn nhiễu retrain trong sim LỚN:** CTRL (cùng nhãn cũ, chỉ khác purge 168h + tập giao −12% dòng + xgboost 3.4.1 GPU) thua B0 deploy **−1,84 Calmar [−4,39; −0,39], −6,8pp CAGR [−13,4; −1,1]**, dù xs-corr tầng model 0,93 (≈ sàn NETTHR). ⇒ Mọi so sánh "selector retrain vs B0 deploy" bị nhiễu ~7pp CAGR; B0 có thể là một lần rút may mắn hoặc nhạy với purge/tập dòng. **Phải so arm-vs-CTRL cùng đợt, và cần ≥2 seed/CTRL** trước khi kết luận lever tầng G015.
2. Proxy tầng model cho SL không đáng tin: cần proxy **điều kiện theo tick gate mở + exit FLAT3 thật** (hoặc đi thẳng sim) cho vòng nhãn kế.
3. Coin identity ở ~70% lệnh B0 do **S1** (nhãn rel5 của g1lite 72h) — nhãn first-hit nên thử trên **S1 ranker** (đúng tầng lọc), không phải G015. Vòng R50 (b7fedef4) cũng chỉ ra giá trị nằm ở xếp hạng đầu bảng (hạng 1–16 vs 17–50) — nhãn/tiêu chí đánh giá nên là ranking trong top-50, không phải IC toàn universe.
4. Một seed; Aerospike thiếu symbol 2021 (giao 87,6% nhãn cũ); CI block-72h tầng model hẹp hơn thật.

## 8. Artifact
Oracle `~/claude_master/1003/fh/`: `labels/fh_YYYYMM.parquet` (60 tháng + meta), `fh_all.parquet`, `out_FH|out_CTRL` (bins raw), `map_FH|map_CTRL` (bins map), `label_firsthit_model.json`, `top16_ticks.parquet`, `sim_score.json`, `sim_mtm.json`, `report.md`, log. Kaggle: dataset `fh-label-firsthit` (nhãn train, sha 79003f67…), `fh-sim-bins-fh|ctrl`; kernel `label-firsthit-g015-gpu`, `sim-fhsim-fh|ctrl`. Không push bins/nhãn/printDone.
