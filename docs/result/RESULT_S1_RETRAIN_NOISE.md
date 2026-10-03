# RESULT — S1_RETRAIN_NOISE: sàn nhiễu retrain S1 ranker (đổi seed) ở tầng sim

**Pre-reg:** `docs/prereg/PREREG_S1_RETRAIN_NOISE.md` (commit `14409eb4`, + A1 `6f767bd6` TRƯỚC khi submit sim arm). DEV ≤ 2025,
16 fold 20220101..20251001. KHÔNG 242/shadow, KHÔNG sửa .java, KHÔNG Java trên Oracle, không fold 2026.
**Code:** `research/analysis/s1_retrain_noise_kernel.py` (kernel train) · `s1_retrain_noise_sim.py` (prep/map/model/sim/score).
Thô: `docs/result/s1_retrain_noise.json` (+ `.parity`). **Kernel:** `chuyendinh/s1-retrain-noise-gpu` (Tesla T4, xgboost 3.2.0,
x86_64) · sim `sim-s1rn-{k42,s7,s13,s21}` + `sim-s1rn-b0ref3`.

---

## 0. ĐỌC TRƯỚC
1. **[ĐO] B0 là realization BÌNH THƯỜNG trên CAGR** (thước chính): z3 = **−0,36** (z4K +0,02). Retrain S1 đúng recipe,
   đổi seed ⇒ CAGR 2022+ chỉ dao động **sd 0,83pp** (33,2 / 33,6 / 34,8 vs B0 33,6). Sàn nhiễu retrain **S1** NHỎ.
2. **[ĐO] Trên Calmar ngày B0 nằm ĐỈNH** (z3 **+2,79**, z4K +2,59, hạng 1/4): Calmar B0 3,35 vs seed 2,78–3,03 (mean 2,94).
   Toàn bộ chênh đến từ maxDD (B0 −10,0% vs seed −11,1..−12,0%; DD MTM phút 2022 −17,7 vs −18,5..−19,1) và UW (87 vs ~117 ngày),
   CAGR không khác. Theo pre-reg đây là thước PHỤ (không đổi kết luận chính), nhưng hệ quả thực: **Calmar 3,35 của B0 lạc
   quan ~0,4** so với kỳ vọng một lần retrain; mốc so cho S1 mới nên là ~2,9, không phải 3,35. Paired meanS−B0 Calmar
   −0,41 CI [−0,75; +0,39] vẫn chứa 0 (nhiễu đường thời gian lớn hơn).
3. **[ĐO] Lệch môi trường nằm trong nhiễu seed:** K42 (seed gốc, Kaggle GPU) − B0 = −0,98pp CAGR < 2·sd3 (1,67). Tầng model:
   MỌI cặp retrain (seed khác, GPU vs CPU, x86 vs aarch64) đều cách nhau như nhau: xs-corr ~0,98, top-16 overlap ~0,89.
4. **[SUY LUẬN] Hệ quả cho LABEL_FIRSTHIT:** sàn CTRL−B0 −6,8pp CAGR ở đó **không đến từ S1** (S1 retrain chỉ ~0,8pp sd) ⇒ đến
   từ phía G015 (retrain G015 + purge 168h + tập giao + GPU, và/hoặc map gốc). Muốn tách cần đo sàn seed G015 riêng.
5. **[ĐO] f0_repro ≠ deploy (A1):** `~/f0_repro/predwf_map_s1a2_x1` (map từ `g015x26_regen`, dùng làm MAP_PARITY ở LABEL_FIRSTHIT)
   KHÁC bins deploy B0 `~/predwf_map_s1a2_x1`; `~/claudedata/predwf_G015x26` gốc đã mất. Vòng này map trên chính bins deploy
   (lũy đẳng, MAP_PARITY mới 16/16, changed 0). Không ảnh hưởng arm FH/CTRL vòng trước, nhưng cổng MAP_PARITY vòng đó
   chỉ chứng minh tái lập f0_repro, không phải deploy.
6. n = 3 seed: sd thô, CI95 của σ ≈ [0,52; 6,28]×σ̂ ⇒ σ_CAGR ∈ ~[0,43; 5,2]pp. Mọi z/MDE dưới đây là định cỡ, không phải kiểm định.

## 1. Feasibility & cổng hợp lệ
| cổng | kết quả |
|---|---|
| Pipeline S1 | `research/pipeline/x1/run_x1.sh` → `x1_s1_rank.py 2x1` → `pred_s1a2x1` (sha `2618fe1a…` khớp) → `x1_build_map.py s1a2x1`. Tái lập được; seed gốc 42 hard-code; `feat_v2_x1.parquet` gốc đã mất trên Oracle ⇒ dùng Kaggle dataset `s1-featv2-x1-20260919` (KEEP9 + ledger lite) ✓ |
| Kernel | md5 2 file dataset == pre-reg ✓; xgboost **3.2.0** ✓; `assert tr.ts.max()<c` 16/16 fold × 5 arm ✓; ts < 2026 ✓; GPU arm 152–157 s/arm, KC42 CPU 1 000 s |
| Pred vs ORIG | mỗi arm 6 573 909 dòng, join (ts,sym) 100%, số dòng/fold bằng ✓ |
| Cổng K42 | xs-corr K42~ORIG **0,984 ≥ 0,80** ✓ |
| MAP_PARITY (A1) | map(deploy, `pred_s1a2x1`) == deploy md5 **16/16**, changed 0 ✓; sha `moc21+deploy16` == P0 `407e2aba` ✓ |
| Sim | jar `7368be46` ✓, mapper 863 ✓, bins sha trong kernel == Oracle ✓ 4/4; equity 2021-12-31 = 41 486 mọi arm ✓ |
| B0REF3 parity | md5 **ff3ce513** == `selab-p0`, n 2517, eq 131 908, 0 ô khác giá trị ⇒ ảnh Kaggle không đổi, B0 = `selab-p0` ✓ |

## 2. Tầng model (OOS 16 fold vs ORIG = deploy `pred_s1a2x1`)
| arm | xs-corr mean (min fold) | top-16 overlap (min fold) | edge5 g1lite |
|---|---:|---:|---:|
| ORIG (B0) | — | — | 15,42% |
| K42 (seed 42, GPU) | 0,984 (0,941) | 0,897 (0,868) | 15,03% |
| S7 | 0,981 (0,924) | 0,888 (0,849) | 15,91% |
| S13 | 0,983 (0,939) | 0,901 (0,840) | 15,98% |
| S21 | 0,984 (0,945) | 0,907 (0,870) | 15,40% |
| KC42 (seed 42, CPU x86, không sim) | 0,984 (0,928) | 0,895 (0,847) | 15,59% |
Cặp seed với nhau: xs 0,980–0,983, top-16 0,886–0,899 — **bằng** mức arm~ORIG. Đổi seed, đổi GPU/CPU hay đổi kiến trúc đều
cho cùng một độ lệch: ~10% top-16 mỗi tick đổi danh tính. edge5 seed: sd ≈ 0,32pp.

## 3. SIM (Kaggle CPU, kaggle_sim HEAD `8b60b00a`, profile r4_kg0_k16_f015_g155 + G2 + FLAT3 — config B0; CHỈ đổi S1)
### Bảng chính — cửa sổ 2022-01-01..2025-12-30 (equity ngày từ 2021-12-31) + toàn kỳ MTM phút
| arm | n | ΣPnL | equity | **CAGR %** | maxDD ngày % | **Calmar ngày** | win % | SL % | CAGR toàn kỳ | DD MTM phút | Calmar phút | UW ngày | lệnh B0 có trong arm |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S7 | 2 091 | 89 118 | 130 604 | 33,23 | −11,98 | 2,78 | 86,3 | 13,58 | 34,01 | −19,08 | 1,78 | 117 | 80,5% |
| S13 | 2 066 | 90 395 | 131 881 | 33,55 | −11,08 | 3,03 | 86,2 | 13,80 | 34,30 | −18,49 | 1,86 | 117 | 82,8% |
| S21 | 2 089 | 95 415 | 136 901 | 34,81 | −11,50 | 3,03 | 86,3 | 13,69 | 35,42 | −18,80 | 1,88 | 117 | 82,4% |
| K42 (môi trường) | 2 087 | 86 589 | 128 075 | 32,58 | −12,23 | 2,66 | 85,9 | 14,09 | 33,43 | −19,53 | 1,71 | 165 | 82,3% |
| **B0** (deploy) | 2 083 | 90 422 | 131 908 | **33,56** | **−10,02** | **3,35** | 86,3 | 13,83 | 34,31 | −17,68 | 1,94 | 87 | 100% |
| mean3 ± sd3 (S7,S13,S21) | 2 082 ± 14 | 91 643 ± 3 328 | | **33,86 ± 0,83** | −11,52 ± 0,45 | **2,94 ± 0,15** | | 13,69 ± 0,11 | 34,58 ± 0,75 | −18,79 ± 0,29 | 1,84 ± 0,05 | 117 ± 0,2 | |
| **z3 của B0** | +0,07 | −0,37 | | **−0,36** | +3,35 | **+2,79** | | +1,29 | −0,36 | +3,77 | +1,90 | (σ≈0) | |
z4K (so 4 điểm Kaggle K42,S7,S13,S21): CAGR **+0,02** (mean 33,54, sd 0,94), Calmar +2,59 (mean 2,87, sd 0,18).
z_pool (B0 trong {B0,S7,S13,S21}): CAGR −0,33 (hạng 2/4), Calmar +1,29 (hạng 1/4; trần cấu tạo ~1,5). Jaccard tập lệnh vs B0 67–71%.

### MTM paired vs B0 (block-10d, NREP 2000, seed 20260905, k=1, cửa sổ 2022+)
| cặp | ΔCAGR pp | CI95 | ΔCalmar ngày | CI95 | ΔmaxDD pp | CI95 |
|---|---:|---|---:|---|---:|---|
| S7 − B0 | −0,33 | [−2,95; +2,55] | −0,58 | [−1,07; +0,52] | −1,96 | [−3,49; +0,54] |
| S13 − B0 | −0,01 | [−2,14; +2,39] | −0,32 | [−0,87; +0,41] | −1,07 | [−2,32; +0,32] |
| S21 − B0 | +1,25 | [−0,99; +3,72] | −0,32 | [−0,65; +0,62] | −1,48 | [−2,42; +0,32] |
| K42 − B0 | −0,98 | [−3,68; +1,73] | −0,69 | [−1,93; +0,08] | −2,22 | [−4,24; +0,02] |
| **meanS − B0** | **+0,30** | **[−1,85; +2,66]** | **−0,41** | **[−0,75; +0,39]** | −1,50 | [−2,62; +0,30] |
| K42 − meanS | −1,29 | [−3,42; +0,70] | −0,28 | [−1,46; +0,10] | −0,72 | [−2,07; +0,18] |
Mọi CI chứa 0. ROI năm (MTM ngày %): 2022 B0 11,1 vs seed 10,1–12,5 · 2023 54,1 vs 53,0–56,7 · 2024 43,4 vs 40,1–42,1 ·
2025 29,5 vs 31,6–34,0 — B0 không trội đều theo năm (thắng 2024, thua 2025).

## 4. MDE80 (pre-reg §4; 2,802 = z0,975 + z0,80; σ = sd3)
| thước (σ) | vsMean = 2,802σ | 1v1 = 2,802√2σ | 2v2 | 3v3 | 5v5 |
|---|---:|---:|---:|---:|---:|
| CAGR 2022+ (σ 0,83pp) | 2,34pp | **3,30pp** | 2,34pp | 1,91pp | 1,48pp |
| Calmar ngày (σ 0,146) | 0,41 | **0,58** | 0,41 | 0,33 | 0,26 |
Công thức m v m: 2,802·σ·√(2/m). Với n = 3, σ thật có thể gấp 0,52–6,28 lần ⇒ MDE1v1 CAGR ∈ ~[1,7; 21]pp (định cỡ thô).
Nguồn nhiễu thứ hai (độc lập): CI bootstrap thời gian paired của một arm vs B0 có nửa-độ-rộng **±2,4–2,7pp CAGR, ±0,5–0,8 Calmar**
— lớn hơn nhiễu seed. Hai nguồn không cộng gộp trong pre-reg; quy tắc thực dụng ở §5.

## 5. VERDICT
**S1_RETRAIN_NOISE: B0 LÀ REALIZATION BÌNH THƯỜNG trên CAGR** (z3 −0,36, |z| < 1; z4K +0,02). Sàn nhiễu retrain S1 ở tầng sim
**nhỏ**: sd CAGR 0,83pp, mọi seed nằm trong [32,6; 34,8]% so với B0 33,6%, mọi paired CI chứa 0. Lệch môi trường (K42) nằm
trong nhiễu seed. **Phụ (Calmar ngày): B0 ở đỉnh, z3 +2,79 ⇒ theo luật = "may mắn" trên Calmar** — do một maxDD 2022 nông
hơn (−10,0 vs −11,5 trung bình) chứ không do lợi nhuận; mốc Calmar thực của recipe S1 ≈ 2,9 (không phải 3,35).
**Cải thiện S1 phải vượt bao nhiêu để đọc được trên DEV:**
- So 1 run S1 mới vs 1 run CTRL cùng đợt: **ΔCAGR ≳ +3,3pp** (MDE80 seed) VÀ paired CI vs CTRL > 0 (nửa-độ-rộng ~2,5pp) ⇒ thực
  tế cần ~**+3–4pp CAGR** hoặc **ΔCalmar ≳ +0,6**; dưới mức đó là nhiễu.
- 3 seed mỗi arm: ngưỡng seed xuống ~1,9pp CAGR / 0,33 Calmar — nhưng CI thời gian (~±2,5pp) vẫn chặn ⇒ lever S1 < ~2,5pp
  CAGR **không đọc được** trên DEV 2022–2025 bằng thước sim hiện tại.
- So với B0 deploy được (K42 không lệch ngoài nhiễu), nhưng **Calmar phải so với ~2,9 (mean retrain), không phải 3,35**.
- Theo R50, xáo trong top-50 mất ~14,7pp CAGR — tức tín hiệu ranking đầu bảng lớn gấp ~4× MDE; sàn retrain S1 không phải rào cản
  cho cải thiện cỡ đó, chỉ chặn cải thiện nhỏ.

## 6. Chặn / rủi ro vòng sau
1. n = 3 seed (§0.6). Nếu cần σ chặt hơn: thêm seed là vòng pre-reg riêng (chi phí ~2,5' GPU/seed + 1 sim ~30').
2. Sàn retrain **G015** (−6,8pp ở LABEL_FIRSTHIT) vẫn chưa tách seed vs purge/tập giao/map; vòng G015 nào cũng cần CTRL cùng đợt.
3. Bins deploy là nguồn G015 duy nhất còn (G015x26 gốc mất; `g015x26_regen` ≠ deploy) — mọi vòng đổi S1 nên map trên bins deploy
   như A1.
4. UW/maxDD là thước của MỘT tập đỉnh–đáy (2022), nhạy với realization; ưu tiên CAGR + paired CI làm thước chính cho S1.

## 7. Artifact
Oracle `~/claude_master/1003/s1rn/`: `kout/pred_{K42,S7,S13,S21,KC42}.parquet` + `summary.json` + log kernel, `pred/` (pred tạm,
symlink `~/ledger/pred_s1a2x1rn*`), `map_{K42,S7,S13,S21}/` (bins), `model_score.json`, `sim_mtm.json`, `sim_sha256.json`,
`map_parity.json`, `chain.log`, `score.log`. Kaggle: dataset `s1rn-bins-{k42,s7,s13,s21}`; kernel `s1-retrain-noise-gpu`,
`sim-s1rn-*`. Không push bins/pred/printDone.
