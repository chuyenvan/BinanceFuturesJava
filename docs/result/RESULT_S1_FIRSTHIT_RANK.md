# RESULT — S1_FIRSTHIT_RANK: S1 ranker học nhãn first-hit FLAT3 — **NO-GO**

**Pre-reg:** `docs/prereg/PREREG_S1_FIRSTHIT_RANK.md` (commit `c4a77936`, chốt TRƯỚC train; không amendment). DEV ≤ 2025,
16 fold 20220101..20251001. KHÔNG 242/shadow, KHÔNG sửa .java, KHÔNG Java trên Oracle, không fold 2026.
**Code:** `research/analysis/s1_fhrank_prep.py` (nhãn) · `s1_fhrank_kernel.py` (train GPU) · `s1_fhrank_sim.py`
(map/model/sim/score) · `s1_fhrank_diag.py` (cặp xs). Thô: `docs/result/s1_fhrank.json` (+ `.parity`).
**Kernel:** `chuyendinh/s1-fhrank-gpu` (T4, xgboost 3.2.0; FHP 142–149 s/arm, FHL 202–203 s/arm) · sim `sim-fhr-{fhp42,fhp7,fhl42,fhl7}`
+ `sim-fhr-b0ref4`.

---

## 0. ĐỌC TRƯỚC
1. **[ĐO] Đổi nhãn S1 sang first-hit PHÁ giá trị xếp hạng của S1.** Cả 4 arm (2 họ × 2 seed) CAGR 2022+ **16,9–18,3%** vs CTRL
   32,9% vs B0 33,6%; ΔCAGR họ − CTRL **−15,3pp (FHP) / −15,5pp (FHL)**, CI inflate 1,18 hoàn toàn < 0; thua CTRL **4/4 năm**;
   SL% **20,1–20,9%** vs 13,8%. Mất ≈ **104–105%** gap R50 (14,71pp): S1-FH tệ ngang xáo ngẫu nhiên trong top-50.
2. **[ĐO] Nhãn không học được bằng 9 feature này:** IC với CHÍNH y_FH của arm FH (+0,008..+0,026) **thấp hơn** CTRL học rel5
   (+0,042); lift@16 FHP ≈ 0 (−0,001 / +0,004), FHL ≈ CTRL (+0,013 / +0,015 vs +0,014). Model FH **không ổn định theo seed**:
   xs FHP42~FHP7 **0,71**, top-16 overlap 0,40 (CTRL K42~S7: 0,98 / 0,90) ⇒ khớp nhiễu.
3. **[ĐO] Truncation NDCG@16 (FHL) không đổi gì ở sim:** FHL − FHP = −0,25pp CAGR [−2,46; +2,08], Calmar −0,01. Khác thứ tự giữa
   FHL và FHP (xs 0,71/0,81) cỡ bằng khác giữa 2 seed cùng họ ⇒ chỉ là nhiễu.
4. **[ĐO] Proxy tầng model lại ngược dấu sim** (như LABEL_FIRSTHIT): bad@16 (SL-trước trong top-16) của FH 0,386–0,398 ≈ universe
   0,393 < CTRL 0,405, nhưng SL% sim FH **cao hơn** 6–7pp. CTRL/ORIG nghiêng vol; FH bỏ nghiêng đó mà không có tín hiệu thay.
5. **[SUY LUẬN] Vì sao:** IC của ORIG (S1 đang chạy) với y_FH **âm** ở 2023 (−0,049) và 2024 (−0,046) dù sim 2023–24 là năm tốt
   nhất ⇒ thứ S1 bắt được (g1lite: trailing 72h) KHÔNG phải first-hit +7/−10 168h. Nhãn nhị phân ~55% dương, horizon 168h,
   tương quan per-tick với feature ~0 ⇒ LambdaRank học nhiễu. CTRL purge 72h vs FH 169h là giới hạn, nhưng không thể giải thích
   −15pp (sàn retrain S1 sd 0,83pp; purge chỉ bớt ~7 ngày train/fold).

## 1. Nhãn / loss S1 hiện tại & hash
- **S1 hiện tại:** `x1_s1_rank.py 2x1`: **XGBRanker rank:ndcg (LambdaRank), topk 8 cặp/mẫu**, relevance **rel5** = ngũ phân vị
  trong tick của g1lite − median (g1lite 72h: maxFav − min(0,5·maxFav, 8%) nếu maxFav ≥ 5%, else retEnd_72h); 300/4/0,05,
  sub/col 0,8, mcw 50; KEEP9; purge 72h; 16 fold expanding. ⇒ S1 ĐÃ listwise; FHL chỉ khác FHP ở truncation 8 → 16.
- Hash: lite ledger `2cc8381e…`, keep9 `1aa3b974…`, **yfh_x1 `99c1e2ee…`** (Kaggle `s1-fhrank-yfh-20261003`), kernel code
  md5 `552a866a…`; bins sha FHP42 `15ad367d…` FHP7 `5debf3a2…` FHL42 `f016c578…` FHL7 `1244087a…` (== trong kernel sim ✓);
  printDone md5 FHP42 `64c188fa`, FHP7 `6d1db13f`, FHL42 `f028f94b`, FHL7 `23234fa3`; CTRL K42 `65dfcb41`, S7 `3f178341`.
- **Coverage nhãn** (ghép nhãn FH tại ts + 15', probe căn chỉnh 0,962 vs 0,941 ở lệch 0): 97,19% toàn bộ (2022–24 ~100%, 2025
  96,40%; 94% phần thiếu ở 12/2025 do cửa sổ 168h vượt DEV). Train bỏ dòng thiếu nhãn: fold cuối **1 401 / 3 413 511 (0,04%)**.

## 2. Cổng hợp lệ
| cổng | kết quả |
|---|---|
| Pre-reg trước train | `c4a77936` (trước đó chỉ chạy: probe căn chỉnh, sinh `yfh_x1`, MAP_PARITY, tầng model ORIG/K42/S7) ✓ |
| Kernel | md5 3 file dataset ✓; xgboost 3.2.0 ✓; purge 169h, assert `tr.ts.max() < cut − 168h` 16/16 × 4 arm ✓ |
| Pred | mỗi arm 6 573 909 dòng, join (ts,sym) == ORIG 100%, số dòng/fold bằng ✓; map đổi 18,2% dòng bins (≈ CTRL) |
| MAP_PARITY | map(deploy, pred_s1a2x1) == deploy md5 16/16, changed 0 ✓ |
| Sim | jar 7368be46 ✓, mapper 863 ✓, bins sha trong kernel == Oracle 4/4 ✓; equity 2021-12-31 = 41 486 mọi arm ✓ |
| **B0REF4** | md5 **ff3ce513** == selab-p0, n 2517, eq 131 908, 0 ô khác ⇒ ảnh Kaggle không đổi; B0 = selab-p0, CTRL (s1rn) dùng được ✓ |
| Code chấm model | xs K42~ORIG 0,984 / top-16 0,897, S7 0,981 / 0,888 == S1_RETRAIN_NOISE ✓ |

## 3. Tầng model (OOS 16 fold, trung bình per-tick; CHỈ báo cáo)
| arm | IC vs y_FH | IC vs g1lite | **lift@16** | y_FH top-16 | y_FH 17–50 | bad@16 | NDCG@16 | xs vs ORIG | top-16 ∩ ORIG |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ORIG (B0) | +0,041 | +0,171 | +0,0154 | 0,592 | 0,581 | 0,405 | 0,597 | — | — |
| CTRL K42 / S7 | +0,042 / +0,042 | +0,172 / +0,172 | +0,0137 / +0,0146 | 0,591 | 0,582 | 0,405 | 0,597 | 0,984 / 0,981 | 0,897 / 0,888 |
| FHP42 / FHP7 | +0,008 / +0,024 | +0,019 / +0,046 | −0,0008 / +0,0035 | 0,554 / 0,569 | 0,559 / 0,570 | 0,392 / 0,398 | 0,564 / 0,578 | 0,096 / 0,198 | 0,201 / 0,250 |
| FHL42 / FHL7 | +0,015 / +0,026 | +0,024 / +0,038 | +0,0134 / +0,0154 | 0,574 / 0,581 | 0,565 / 0,570 | 0,392 / 0,386 | 0,584 / 0,589 | 0,137 / 0,176 | 0,150 / 0,230 |
Universe (ALL): y_FH 0,548, bad 0,393. Theo năm (IC vs y_FH, 2022/23/24/25): ORIG +0,030/−0,049/−0,046/+0,065 · FHP42
+0,032/+0,017/+0,012/+0,001 · FHL7 +0,038/+0,019/+0,024/+0,023. Lift@16 theo năm ORIG +0,022/+0,011/−0,022/+0,022 · FHL42
+0,016/−0,004/−0,002/+0,017 · FHL7 +0,006/−0,003/+0,006/+0,021. Cặp (diag): FHP42~FHP7 xs 0,708 / top-16 0,396; FHL42~FHL7
0,827 / 0,542; FHL42~FHP42 0,711 / 0,382; FHL7~FHP7 0,814 / 0,541; K42~S7 0,982 / 0,897.
Đọc: FH arms gần như trực giao với S1 cũ (xs 0,10–0,20), dự báo chính y_FH KÉM hơn CTRL, và không ổn định theo seed.

## 4. SIM — cửa sổ 2022-01-01..2025-12-30 (equity ngày từ 2021-12-31), config B0, CHỈ đổi bins S1
| arm | n | ΣPnL | CAGR % | maxDD ngày % | Calmar ngày | win % | SL % | UW ngày (phút, toàn kỳ) | DD MTM phút | overlap lệnh B0 / Jaccard |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| FHP42 | 1 992 | 39 703 | 18,29 | −19,09 | 0,96 | 80,5 | 20,38 | 333 | −26,7 | 37,2% / 23,4% |
| FHP7 | 1 961 | 36 235 | 17,01 | −19,62 | 0,87 | 80,9 | 19,79 | 349 | −27,8 | 36,3% / 22,9% |
| **FHP (mean)** | 1 977 | 37 969 | **17,65** | −19,36 | **0,91** | 80,7 | **20,08** | 341 | −27,3 | 36,8% |
| FHL42 | 2 009 | 35 910 | 16,88 | −19,89 | 0,85 | 80,4 | 21,25 | 421 | −29,8 | 34,0% / 20,8% |
| FHL7 | 1 950 | 38 685 | 17,92 | −18,84 | 0,95 | 79,7 | 20,62 | 420 | −26,9 | 34,4% / 21,5% |
| **FHL (mean)** | 1 980 | 37 297 | **17,40** | −19,36 | **0,90** | 80,0 | **20,93** | 421 | −28,3 | 34,2% |
| K42 / S7 | 2 087 / 2 091 | 86 589 / 89 118 | 32,58 / 33,23 | −12,23 / −11,98 | 2,66 / 2,77 | 85,9 / 86,3 | 14,09 / 13,58 | 165 / 117 | −19,5 / −19,1 | 82,3% / 80,5% |
| **CTRL (mean)** | 2 089 | 87 853 | **32,90** | −12,10 | **2,72** | 86,1 | **13,83** | 141 | −19,3 | 81,4% |
| **B0** | 2 083 | 90 422 | **33,56** | −10,02 | **3,35** | 86,3 | 13,83 | 87 | −17,7 | 100% |

## 5. Chênh paired (block-10d, NREP 2000, seed 20260905, k = 2 ⇒ CI inflate 1,18), cửa sổ 2022+
| cặp | ΔCAGR pp [CI infl] | ΔmaxDD pp [CI infl] | ΔCalmar ngày [CI infl] |
|---|---|---|---|
| **FHP − CTRL** | **−15,26 [−25,49; −7,21]** | −7,25 [−8,88; +0,90] | **−1,81 [−7,02; −0,58]** |
| **FHL − CTRL** | **−15,50 [−25,50; −7,28]** | −7,26 [−8,56; +1,03] | **−1,82 [−7,82; −0,56]** |
| FHL − FHP | −0,25 [−2,46; +2,08] | −0,00 [−1,62; +1,98] | −0,01 [−0,58; +0,30] |
| FHP − B0 | −15,91 [−26,10; −7,66] | −9,34 [−11,66; +0,48] | −2,44 [−7,54; −0,81] |
| FHL − B0 | −16,16 [−25,73; −7,82] | −9,35 [−10,89; +0,57] | −2,45 [−7,79; −0,82] |
| CTRL − B0 (sàn) | −0,66 [−3,50; +2,21] | −2,09 [−4,13; +0,64] | −0,63 [−1,35; +0,35] |
Từng arm vs CTRL: FHP42 −14,61, FHP7 −15,90, FHL42 −16,02, FHL7 −14,99pp CAGR — mọi CI < 0.
**Ablation end-to-end:** frac gap R50 = ΔCAGR(họ − CTRL) / 14,71 = **−1,04 (FHP) / −1,05 (FHL)** ⇒ không lấy lại phần nào của
khoảng cách top-50 → 16, ngược lại mất trọn nó (CAGR 2022+ ~17,5% ≈ mức R50 19,6% toàn kỳ / R16 ~10%).

### ROI năm (equity MTM ngày, %)
| năm | FHP | FHL | CTRL | B0 | FHP − CTRL | FHL − CTRL |
|---|---:|---:|---:|---:|---:|---:|
| 2022 | −6,2 | −6,7 | 10,8 | 11,1 | −17,0 | −17,5 |
| 2023 | 41,1 | 37,2 | 55,1 | 54,1 | −14,0 | −17,9 |
| 2024 | 25,6 | 26,9 | 40,4 | 43,4 | −14,8 | −13,4 |
| 2025 | 15,2 | 17,0 | 29,3 | 29,5 | −14,0 | −12,3 |

## 6. VERDICT theo luật pre-reg §7
| điều kiện | FHP | FHL |
|---|---|---|
| 1. ΔCAGR vs CTRL ≥ +3,3pp | **KHÔNG** (−15,26) | **KHÔNG** (−15,50) |
| 2. ΔCalmar vs CTRL, CI infl > 0 | **KHÔNG** ([−7,02; −0,58], hoàn toàn < 0) | **KHÔNG** ([−7,82; −0,56]) |
| 3. ≥ 3/4 năm dương vs CTRL | **KHÔNG** (0/4) | **KHÔNG** (0/4) |
| 4. SL% ≤ CTRL | **KHÔNG** (20,08 vs 13,83) | **KHÔNG** (20,93 vs 13,83) |
| 5. ΔCAGR vs B0 CI không dưới 0 | **KHÔNG** ([−26,10; −7,66]) | **KHÔNG** ([−25,73; −7,82]) |
**S1_FIRSTHIT_RANK: NO-GO** — 0/5 điều kiện cho cả hai họ; không phải "chưa đọc được" mà là **xấu đi có ý nghĩa** (CI ngoài 0).
Kỳ vọng khai trước (~25% GO, +3,7pp) sai dấu.

## 7. Vì sao NO-GO (theo §8 pre-reg)
- **Nhãn không học được — CÓ.** IC_yFH FH (0,008–0,026) < CTRL 0,042; lift@16 FHP +0,001 (≤ CTRL + 0,005), FHL +0,014 ≈ CTRL.
  Học trực tiếp y_FH cho tín hiệu thứ tự y_FH KÉM hơn học rel5 (g1lite) — g1lite liên tục 5 mức mang thông tin hơn nhãn nhị
  phân 168h nhiễu; model FH bất ổn theo seed (xs 0,71) ⇒ khớp nhiễu.
- **Listwise không đổi thứ tự — CÓ về hiệu ứng** (sim FHL − FHP ≈ 0, CI chứa 0); theo chữ ngưỡng xs FHL~FHP ≥ 0,95 KHÔNG đạt
  (0,71/0,81) nhưng khoảng cách đó bằng khoảng cách seed-seed ⇒ nhiễu, không phải thứ tự mới có giá trị.
- **Lệch hướng — CÓ:** FHL lift@16 ≈ CTRL và bad@16 thấp hơn, nhưng sim tệ hơn 15pp ⇒ thước tầng model theo y_FH (lift/bad/NDCG)
  KHÔNG dự báo sim; thước đúng hướng là IC vs g1lite (0,02–0,05 vs 0,17) và xs vs ORIG (0,1–0,2).
- **Nhiễu — KHÔNG:** Δ −15pp ≫ MDE 3,3pp và ≫ sàn retrain (sd 0,83pp); 4/4 seed-arm đều âm.

## 8. Chặn / rủi ro / hệ quả
1. Giới hạn đã khai: purge CTRL 72h vs FH 169h, và nhãn FH ghép lệch +15' — cả hai không thể tạo −15pp; không đổi kết luận.
2. **Hướng first-hit FLAT3 (+7/−10, 168h) làm nhãn selector đã thất bại ở cả G015 (LABEL_FIRSTHIT) lẫn S1 (vòng này)** ⇒ đóng hướng
   "nhãn first-hit thay nhãn S1/G015". g1lite (trailing 72h) khớp cơ chế thoát của sim hơn first-hit; IC ORIG vs y_FH âm ở
   2023–24 mà sim vẫn tốt nhất ⇒ y_FH không phải đại lượng sim thưởng.
3. Hệ quả cho B0: "lần thử cải thiện có cơ sở số duy nhất còn lại" cho S1 không cải thiện; giá trị top-50 → 16 vẫn nằm ở S1 hiện tại.
   Nếu còn đào: chỉ thay đổi CÙNG nhãn g1lite (vd. truncation 16 với rel5 — chưa đo, kỳ vọng nhỏ vì FHL − FHP ≈ 0) hoặc feature mới;
   mọi lever S1 < ~3pp CAGR không đọc được trên DEV.
4. 2 seed/họ; CTRL từ đợt trước (ảnh Kaggle xác nhận không đổi bằng B0REF4).

## 9. Artifact
Oracle `~/claude_master/1003/fhr/`: `kds/yfh_x1.parquet`, `coverage.json`, `kout/pred_{FHP42,FHP7,FHL42,FHL7}.parquet` + `summary.json` +
log kernel, `pred/` (symlink `~/ledger/pred_s1a2x1fhr*`), `map_*` (bins), `map_parity.json`, `model_score.json`, `model_pairs.json`,
`sim_sha256.json`, `sim_mtm.json`, `chain*.log`, `score.log`. Kaggle: dataset `s1-fhrank-yfh-20261003`, `fhr-bins-*`; kernel
`s1-fhrank-gpu`, `sim-fhr-*`. Không push bins/nhãn/printDone.
